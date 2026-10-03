"""Snapshot lifecycle (ADR-032 pkt 8): staging -> active atomically, one run per service, a failed
or crashed run never touches the previous snapshot."""

from datetime import UTC, datetime, timedelta

import pytest

from app.config import settings
from app.gios_open import snapshots as sn
from app.gios_open.errors import SnapshotLockedError, SnapshotLostError
from app.models import DatasetSnapshot

NOW = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)
FILT = {"kategoria": "Droga", "wojewodztwo": "ŚLĄSKIE"}


def begin(db, source="gios_noise", op="pomiar", filters=FILT, now=NOW):
    return sn.begin_snapshot(db, source_id=source, operation=op, filters=filters, now=now)


def promote(db, snap, **kw):
    sn.promote(
        db,
        snap,
        record_count=1,
        page_count=1,
        rejected_count=0,
        checksum="c",
        schema_hash="s",
        **kw,
    )


def statuses(db):
    return sorted((s.id, s.status) for s in db.query(DatasetSnapshot))


def test_filters_key_is_canonical():
    assert (
        sn.filters_key({"b": 1, "a": "ż"})
        == sn.filters_key({"a": "ż", "b": 1})
        == '{"a":"ż","b":1}'
    )
    assert sn.filters_key(None) == "{}"
    with pytest.raises(ValueError):
        sn.filters_key({"k": "x" * 600})


def test_begin_creates_a_staging_snapshot_invisible_to_readers(db_session):
    snap = begin(db_session)
    assert snap.status == sn.STAGING
    assert sn.active_snapshot(db_session, "gios_noise", "pomiar", FILT) is None


def test_a_second_run_of_the_same_service_is_locked_out_by_the_database(db_session):
    begin(db_session)
    with pytest.raises(SnapshotLockedError):
        begin(db_session, op="other-operation")  # concurrency is 1 per SERVICE, not per operation
    assert [s for _, s in statuses(db_session)] == [sn.STAGING]


def test_other_services_are_independent(db_session):
    begin(db_session, source="gios_noise")
    begin(db_session, source="gios_prtr")
    assert len(statuses(db_session)) == 2


def test_the_lock_is_released_by_promotion_and_by_failure(db_session):
    a = begin(db_session)
    promote(db_session, a)
    b = begin(db_session)  # promotion released the lock
    sn.fail(db_session, b, "boom")
    c = begin(db_session)  # failure released it too
    assert c.status == sn.STAGING


def test_a_crashed_run_is_taken_over_only_after_the_lock_ttl(db_session, monkeypatch):
    monkeypatch.setattr(settings, "gios_open_lock_ttl_minutes", 60)
    dead = begin(db_session, now=NOW)
    with pytest.raises(SnapshotLockedError):
        begin(db_session, now=NOW + timedelta(minutes=59))
    fresh = begin(db_session, now=NOW + timedelta(minutes=61))
    db_session.refresh(dead)
    assert dead.status == sn.FAILED and "stale lock" in dead.error
    assert fresh.status == sn.STAGING


def test_promotion_makes_the_new_snapshot_active_and_supersedes_the_old_one(db_session):
    first = begin(db_session)
    promote(db_session, first)
    second = begin(db_session, now=NOW + timedelta(days=1))
    promote(db_session, second)
    db_session.refresh(first)
    assert (first.status, second.status) == (sn.SUPERSEDED, sn.ACTIVE)
    assert sn.active_snapshot(db_session, "gios_noise", "pomiar", FILT).id == second.id
    assert second.completed_at is not None and second.record_count == 1 and second.checksum == "c"


def test_different_filters_have_their_own_active_snapshot(db_session):
    a = begin(db_session, filters={"wojewodztwo": "ŚLĄSKIE"})
    promote(db_session, a)
    b = begin(db_session, filters={"wojewodztwo": "OPOLSKIE"})
    promote(db_session, b)
    assert {s for _, s in statuses(db_session)} == {sn.ACTIVE}
    assert (
        sn.active_snapshot(db_session, "gios_noise", "pomiar", {"wojewodztwo": "OPOLSKIE"}).id
        == b.id
    )


def test_a_failed_promotion_leaves_the_previous_snapshot_active(db_session, monkeypatch):
    first = begin(db_session)
    promote(db_session, first)
    second = begin(db_session, now=NOW + timedelta(days=1))
    real_commit = db_session.commit

    def failing_commit():
        raise RuntimeError("disk full")

    monkeypatch.setattr(db_session, "commit", failing_commit)
    with pytest.raises(RuntimeError):
        promote(db_session, second)
    monkeypatch.setattr(db_session, "commit", real_commit)
    assert sn.active_snapshot(db_session, "gios_noise", "pomiar", FILT).id == first.id
    db_session.refresh(second)
    assert second.status == sn.STAGING  # nothing was half-applied


def test_fail_keeps_the_previous_snapshot_and_truncates_the_error(db_session):
    first = begin(db_session)
    promote(db_session, first)
    second = begin(db_session)
    sn.fail(db_session, second, "x" * 2000)
    db_session.refresh(second)
    assert second.status == sn.FAILED and len(second.error) == sn.MAX_ERROR_LENGTH
    assert sn.active_snapshot(db_session, "gios_noise", "pomiar", FILT).id == first.id


def test_quarantine_keeps_the_raw_record_with_the_reason(db_session):
    snap = begin(db_session)
    sn.quarantine(
        db_session, snap, reason="unknown_enum", raw={"pora": "Dzień 17h"}, detail="pora", now=NOW
    )
    db_session.commit()
    row = db_session.query(sn.IngestQuarantine).one()
    assert (row.snapshot_id, row.source_id, row.reason, row.raw) == (
        snap.id,
        "gios_noise",
        "unknown_enum",
        {"pora": "Dzień 17h"},
    )


def test_a_worker_that_outlived_its_lease_cannot_promote(db_session, monkeypatch):
    monkeypatch.setattr(settings, "gios_open_lock_ttl_minutes", 60)
    slow = begin(db_session, now=NOW)
    newer = begin(db_session, now=NOW + timedelta(minutes=61))  # took the lock over
    with pytest.raises(SnapshotLostError):
        promote(db_session, slow)
    assert sn.active_snapshot(db_session, "gios_noise", "pomiar", FILT) is None  # nothing published
    promote(db_session, newer)
    assert sn.active_snapshot(db_session, "gios_noise", "pomiar", FILT).id == newer.id


def test_a_late_worker_never_supersedes_a_newer_snapshot(db_session, monkeypatch):
    monkeypatch.setattr(settings, "gios_open_lock_ttl_minutes", 60)
    slow = begin(db_session, now=NOW)
    newer = begin(db_session, now=NOW + timedelta(minutes=61))
    promote(db_session, newer)  # the replacement finishes first
    with pytest.raises(SnapshotLostError):
        promote(db_session, slow)  # the original finishes later with OLDER data
    assert sn.active_snapshot(db_session, "gios_noise", "pomiar", FILT).id == newer.id
    db_session.refresh(slow)
    assert slow.status == sn.FAILED


def test_fail_leaves_a_snapshot_that_is_no_longer_staging_alone(db_session):
    snap = begin(db_session)
    promote(db_session, snap)
    sn.fail(db_session, snap, "late error from the same run")
    db_session.refresh(snap)
    assert snap.status == sn.ACTIVE and snap.error is None
