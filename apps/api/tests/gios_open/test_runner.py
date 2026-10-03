"""The runner (ADR-032 pkt 8): complete pass -> atomic promotion; ANY failure leaves the previous
snapshot active and untouched, records the failed run, and does not poison the next run."""

from datetime import UTC, datetime, timedelta

import pytest

from app import provenance
from app.gios_open import snapshots as sn
from app.gios_open.client import Page
from app.gios_open.errors import GiosOpenSourceError, SnapshotLockedError
from app.gios_open.runner import ingest_snapshot
from app.models import DatasetSnapshot, SourceFetch, SourceStatus

NOW = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)
FILT = {"kategoria": "Droga"}
SRC, OP = "gios_noise", "pomiar"


def page(records, raw=None):
    return Page(
        records=records,
        reported_count=len(records),
        empty_observed=not records,
        event_id=None,
        raw=raw or {"dane": {"strona": records}},
    )


class Store:
    """A connector's `store`: remembers what it was asked to write (rows live under the snapshot)"""

    def __init__(self, reject=0, fail_on_page=None):
        self.rows: dict[int, list[dict]] = {}
        self.reject = reject
        self.fail_on_page = fail_on_page
        self.pages = 0
        self.discarded: list[int] = []

    def __call__(self, db, snapshot, records):
        self.pages += 1
        if self.fail_on_page == self.pages:
            raise RuntimeError("store exploded")
        self.rows.setdefault(snapshot.id, []).extend(records)
        return self.reject

    def discard(self, db, snapshot_id):
        self.discarded.append(snapshot_id)
        self.rows.pop(snapshot_id, None)


def run(db, pages, store, *, now=NOW, discard=True):
    return ingest_snapshot(
        db,
        source_id=SRC,
        operation=OP,
        filters=FILT,
        endpoint="https://dane.gios.gov.pl/api/halas/v1/x?kategoria=Droga",
        pages=pages,
        store=store,
        discard=store.discard if discard else None,
        parser_version="t1",
        now=now,
    )


def good_pages():
    yield 0, page([{"id": "a", "v": 1}, {"id": "b", "v": 2}])
    yield 1, page([{"id": "c", "v": 3}])


def failing_pages():
    yield 0, page([{"id": "n1"}])
    raise GiosOpenSourceError("400", "boom")


def active(db):
    return sn.active_snapshot(db, SRC, OP, FILT)


def test_complete_pass_is_promoted_with_counts_provenance_and_source_status(db_session):
    store = Store()
    result = run(db_session, good_pages(), store)
    snap = active(db_session)
    assert (result.snapshot_id, result.record_count, result.page_count, result.rejected_count) == (
        snap.id,
        3,
        2,
        0,
    )
    assert snap.status == sn.ACTIVE and snap.checksum and snap.schema_hash
    assert [r["id"] for r in store.rows[snap.id]] == ["a", "b", "c"]
    fetch = db_session.get(SourceFetch, snap.source_fetch_id)
    assert fetch.source_id == SRC and fetch.validation_status == provenance.VALID
    assert (
        fetch.payload["records"] == 3
        and fetch.payload["pages"] == 2
        and fetch.payload["filters"] == FILT
    )
    status = db_session.get(SourceStatus, SRC)
    assert status.last_success_at is not None and status.last_error is None


def test_rejected_records_make_the_fetch_partial_not_the_run_failed(db_session):
    result = run(db_session, good_pages(), Store(reject=1))
    assert result.rejected_count == 2  # 1 per page
    snap = active(db_session)
    assert db_session.get(SourceFetch, snap.source_fetch_id).validation_status == provenance.PARTIAL


def test_a_failure_midway_keeps_the_previous_snapshot_and_discards_the_partial_rows(db_session):
    first_store = Store()
    first = run(db_session, good_pages(), first_store)

    store = Store()
    with pytest.raises(GiosOpenSourceError):
        run(db_session, failing_pages(), store, now=NOW + timedelta(days=1))

    assert active(db_session).id == first.snapshot_id  # untouched
    assert first_store.rows[first.snapshot_id]  # and so are its rows
    failed = db_session.query(DatasetSnapshot).filter_by(status=sn.FAILED).one()
    assert "GiosOpenSourceError" in failed.error
    assert store.discarded == [failed.id] and failed.id not in store.rows
    status = db_session.get(SourceStatus, SRC)
    assert "GiosOpenSourceError" in status.last_error


def test_a_store_failure_is_treated_the_same_way(db_session):
    first = run(db_session, good_pages(), Store())
    with pytest.raises(RuntimeError):
        run(db_session, good_pages(), Store(fail_on_page=2), now=NOW + timedelta(days=1))
    assert active(db_session).id == first.snapshot_id


def test_the_run_after_a_failure_works_crash_and_resume(db_session):
    with pytest.raises(GiosOpenSourceError):
        run(db_session, failing_pages(), Store())
    assert active(db_session) is None  # nothing was promoted
    result = run(db_session, good_pages(), Store(), now=NOW + timedelta(hours=1))
    assert active(db_session).id == result.snapshot_id


def test_a_run_locked_out_by_another_run_records_nothing_and_changes_nothing(db_session):
    first = run(db_session, good_pages(), Store())
    sn.begin_snapshot(
        db_session, source_id=SRC, operation="other", filters=None, now=NOW
    )  # someone else is running
    before = db_session.get(SourceStatus, SRC).last_attempt_at
    with pytest.raises(SnapshotLockedError):
        run(db_session, good_pages(), Store(), now=NOW + timedelta(minutes=1))
    assert active(db_session).id == first.snapshot_id
    assert db_session.get(SourceStatus, SRC).last_attempt_at == before  # not a source failure


def test_an_empty_complete_pass_is_a_valid_empty_snapshot(db_session):
    result = run(db_session, iter([]), Store())
    snap = active(db_session)
    assert (result.record_count, result.page_count) == (0, 0)
    assert snap.status == sn.ACTIVE and snap.checksum is None and snap.schema_hash is None


def test_failing_cleanup_does_not_mask_the_original_error(db_session):
    store = Store()

    def bad_discard(db, snapshot_id):
        raise RuntimeError("cleanup failed")

    store.discard = bad_discard
    with pytest.raises(GiosOpenSourceError):
        run(db_session, failing_pages(), store)
    assert db_session.query(DatasetSnapshot).filter_by(status=sn.FAILED).count() == 1


def test_schema_hash_changes_when_the_record_fields_change(db_session):
    a = run(db_session, iter([(0, page([{"id": 1, "v": 1}]))]), Store())
    b = run(
        db_session,
        iter([(0, page([{"id": 1, "v": 1, "new": 2}]))]),
        Store(),
        now=NOW + timedelta(days=1),
    )
    hash_a = db_session.get(DatasetSnapshot, a.snapshot_id).schema_hash
    assert hash_a != db_session.get(DatasetSnapshot, b.snapshot_id).schema_hash
