"""Tests for imgw_warningshydro.ingest: store/dedupe/failure-isolation/
reconciliation, using the SQLite db_session fixture."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from app.connectors.imgw_warningshydro import client, ingest
from app.connectors.imgw_warningshydro.parser import ImgwWarningsHydroParseError
from app.models import Alert

WARNING = {
    "opublikowano": "2026-05-17 08:45:07",
    "stopień": "-1",
    "data_od": "2026-05-17 08:45:56",
    "data_do": "9999-12-31 23:59:59",
    "prawdopodobieństwo": "90",
    "numer": "31",
    "biuro": "Biuro Prognoz Hydrologicznych we Wrocławiu",
    "zdarzenie": "Susza hydrologiczna",
    "przebieg": "opis",
    "komentarz": "komentarz",
    "obszary": [{"wojewodztwo": "wielkopolskie", "opis": "x", "kod_zlewni": ["Z1"]}],
}


def test_ingest_warning_stores_new_alert(db_session):
    stored = ingest.ingest_warning(WARNING, db_session, fetched_at=datetime.now(UTC))

    assert stored is True
    assert db_session.query(Alert).count() == 1


def test_ingest_warning_skips_duplicate(db_session):
    ingest.ingest_warning(WARNING, db_session, fetched_at=datetime.now(UTC))
    stored_again = ingest.ingest_warning(WARNING, db_session, fetched_at=datetime.now(UTC))

    assert stored_again is False
    assert db_session.query(Alert).count() == 1


def test_ingest_warning_isolates_parse_failure(db_session, monkeypatch):
    monkeypatch.setattr(
        ingest, "normalize", MagicMock(side_effect=ImgwWarningsHydroParseError("boom"))
    )
    stored = ingest.ingest_warning(WARNING, db_session, fetched_at=datetime.now(UTC))

    assert stored is False
    assert db_session.query(Alert).count() == 0


def test_ingest_warning_isolates_non_dict_entry(db_session):
    # Codex review (PR #37): the old code called warning.get(...) unconditionally
    # in the error-log path, which crashed on a non-dict feed entry instead of
    # skipping it (rule #1).
    stored = ingest.ingest_warning("not-a-dict", db_session, fetched_at=datetime.now(UTC))

    assert stored is False
    assert db_session.query(Alert).count() == 0


class TestIngestBatch:
    def test_expires_alert_no_longer_reported(self, db_session):
        # Codex review (PR #37): a withdrawn warning must not keep reporting as
        # active until its original valid_until (year 9999 for drought) - rule #10.
        first_fetch = datetime.now(UTC)
        ingest.ingest_batch([WARNING], db_session, fetched_at=first_fetch)

        second_fetch = first_fetch + timedelta(hours=1)
        ingest.ingest_batch([], db_session, fetched_at=second_fetch)  # IMGW withdrew it

        alert = db_session.query(Alert).filter_by(external_id="31").one()
        assert alert.valid_until == second_fetch

    def test_keeps_alert_still_in_the_latest_snapshot(self, db_session):
        first_fetch = datetime.now(UTC)
        ingest.ingest_batch([WARNING], db_session, fetched_at=first_fetch)

        second_fetch = first_fetch + timedelta(hours=1)
        ingest.ingest_batch([WARNING], db_session, fetched_at=second_fetch)

        alert = db_session.query(Alert).filter_by(external_id="31").one()
        assert alert.valid_until.year == 9999  # untouched - still reported as active

    def test_refreshes_alert_that_reappears_after_being_expired(self, db_session):
        # Codex review (PR #37): _store() used to no-op on a dedup hit, so a
        # warning closed out by a previous withdrawal round stayed hidden under
        # its stale valid_until even once IMGW reported it active again.
        first_fetch = datetime.now(UTC)
        ingest.ingest_batch([WARNING], db_session, fetched_at=first_fetch)
        second_fetch = first_fetch + timedelta(hours=1)
        ingest.ingest_batch([], db_session, fetched_at=second_fetch)  # withdrawn

        third_fetch = second_fetch + timedelta(hours=1)
        ingest.ingest_batch([WARNING], db_session, fetched_at=third_fetch)  # reappears

        alert = db_session.query(Alert).filter_by(external_id="31").one()
        assert alert.valid_until.year == 9999  # back to the source's real value
        assert alert.fetched_at == third_fetch

    def test_skips_reconciliation_when_snapshot_is_partially_malformed(self, db_session):
        # Codex review (PR #37): a batch that failed to parse in part can't be
        # trusted to say who's gone - reconciling against it would wrongly expire
        # a still-valid alert that just happened to fail this round (rule #10).
        first_fetch = datetime.now(UTC)
        ingest.ingest_batch([WARNING], db_session, fetched_at=first_fetch)

        second_fetch = first_fetch + timedelta(hours=1)
        broken = {k: v for k, v in WARNING.items() if k != "biuro"}
        stored, expired, rejected = ingest.ingest_batch(
            [broken], db_session, fetched_at=second_fetch
        )

        assert expired == 0
        assert rejected == 1  # reported so the scheduler won't mark success (ADR-012)
        alert = db_session.query(Alert).filter_by(external_id="31").one()
        assert alert.valid_until.year == 9999  # left alone, not wrongly expired


class TestMain:
    def test_ingests_every_fetched_warning(self, monkeypatch, db_session):
        monkeypatch.setattr(client, "fetch_warnings", MagicMock(return_value=[WARNING]))
        monkeypatch.setattr(ingest, "SessionLocal", lambda: db_session)

        ingest.main()

        assert db_session.query(Alert).count() == 1

    def test_no_active_warnings_stores_nothing(self, monkeypatch, db_session):
        monkeypatch.setattr(
            client, "fetch_warnings", MagicMock(return_value={"message": "Brak ostrzeżeń"})
        )
        monkeypatch.setattr(ingest, "SessionLocal", lambda: db_session)

        ingest.main()

        assert db_session.query(Alert).count() == 0

    def test_one_bad_warning_does_not_abort_the_rest(self, monkeypatch, db_session):
        bad = {k: v for k, v in WARNING.items() if k != "biuro"}
        bad["numer"] = "999"
        monkeypatch.setattr(client, "fetch_warnings", MagicMock(return_value=[bad, WARNING]))
        monkeypatch.setattr(ingest, "SessionLocal", lambda: db_session)

        ingest.main()

        assert db_session.query(Alert).count() == 1
