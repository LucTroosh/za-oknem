"""Tests for imgw_warningshydro.ingest: store/dedupe/failure-isolation, using
the SQLite db_session fixture."""

from datetime import UTC, datetime
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
