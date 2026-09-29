"""Tests for imgw_hydro.ingest: store/skip/dedupe/failure-isolation, using the
SQLite db_session fixture."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from app.connectors.imgw_hydro import client, ingest
from app.connectors.imgw_hydro.parser import ImgwHydroParseError
from app.models import Measurement

STATION = {
    "id_stacji": "151140030",
    "stacja": "Przewoźniki",
    "rzeka": "Skroda",
    "lat": "51.5253",
    "lon": "14.8217",
    "stan_wody": "225",
    "stan_wody_data_pomiaru": "2026-09-27 21:20:00",
}


def test_ingest_station_stores_new_reading(db_session):
    stored = ingest.ingest_station(STATION, db_session, fetched_at=datetime.now(UTC))

    assert stored == 1
    assert db_session.query(Measurement).count() == 1


def test_ingest_station_stores_thresholds_too(db_session):
    station = {**STATION, "stan_ostrzegawczy": "300", "stan_alarmowy": "340"}
    stored = ingest.ingest_station(station, db_session, fetched_at=datetime.now(UTC))

    assert stored == 3
    assert db_session.query(Measurement).count() == 3


def test_ingest_station_skips_duplicate(db_session):
    ingest.ingest_station(STATION, db_session, fetched_at=datetime.now(UTC))
    stored_again = ingest.ingest_station(STATION, db_session, fetched_at=datetime.now(UTC))

    assert stored_again == 0
    assert db_session.query(Measurement).count() == 1


def test_ingest_station_skips_when_no_current_reading(db_session):
    station = {**STATION, "stan_wody": None}
    stored = ingest.ingest_station(station, db_session, fetched_at=datetime.now(UTC))

    assert stored == 0
    assert db_session.query(Measurement).count() == 0


def test_ingest_station_isolates_parse_failure(db_session, monkeypatch):
    monkeypatch.setattr(
        ingest, "normalize", MagicMock(side_effect=ImgwHydroParseError("boom"))
    )
    stored = ingest.ingest_station(STATION, db_session, fetched_at=datetime.now(UTC))

    assert stored == 0
    assert db_session.query(Measurement).count() == 0


class TestMain:
    def test_ingests_every_fetched_station(self, monkeypatch, db_session):
        monkeypatch.setattr(client, "fetch_stations", MagicMock(return_value=[STATION]))
        monkeypatch.setattr(ingest, "SessionLocal", lambda: db_session)

        ingest.main()

        assert db_session.query(Measurement).count() == 1

    def test_one_bad_station_does_not_abort_the_rest(self, monkeypatch, db_session):
        other = {**STATION, "id_stacji": "999", "lat": "not-a-number"}
        monkeypatch.setattr(
            client, "fetch_stations", MagicMock(return_value=[other, STATION])
        )
        monkeypatch.setattr(ingest, "SessionLocal", lambda: db_session)

        ingest.main()

        assert db_session.query(Measurement).count() == 1
