"""Tests for ingest_station(): skip logic, idempotent dedupe, and the
one-broken-station-must-not-abort-the-run guarantee (rule #1). client.* calls
are mocked — no live network — and Measurement is stored in a real (SQLite)
session so dedupe is verified against actual DB state, not a mock."""

from unittest.mock import MagicMock

from app.connectors.gios import client, ingest
from app.connectors.gios.parser import GiosParseError
from app.models import Measurement

STATION = {
    "Identyfikator stacji": 38,
    "Nazwa stacji": "Kłodzko, ul. Szkolna",
    "WGS84 φ N": "50.433493",
    "WGS84 λ E": "16.65366",
}
SENSORS = [{"Identyfikator stanowiska": 25988, "Wskaźnik - wzór": "PM2.5"}]
SENSOR_DATA = {"Lista danych pomiarowych": [{"Data": "2026-09-28 18:00:00", "Wartość": 8.2}]}


def test_ingest_station_stores_new_reading(monkeypatch, db_session):
    monkeypatch.setattr(client, "fetch_sensors", MagicMock(return_value=SENSORS))
    monkeypatch.setattr(client, "fetch_sensor_data", MagicMock(return_value=SENSOR_DATA))

    stored = ingest.ingest_station(STATION, db_session)

    assert stored is True
    rows = db_session.query(Measurement).all()
    assert len(rows) == 1
    assert rows[0].station_id == "38"
    assert rows[0].value == 8.2


def test_ingest_station_skips_when_no_pm25_sensor(monkeypatch, db_session):
    only_pm10 = [{"Identyfikator stanowiska": 1, "Wskaźnik - wzór": "PM10"}]
    monkeypatch.setattr(client, "fetch_sensors", MagicMock(return_value=only_pm10))

    stored = ingest.ingest_station(STATION, db_session)

    assert stored is False
    assert db_session.query(Measurement).count() == 0


def test_ingest_station_skips_when_no_recent_values(monkeypatch, db_session):
    monkeypatch.setattr(client, "fetch_sensors", MagicMock(return_value=SENSORS))
    monkeypatch.setattr(
        client, "fetch_sensor_data", MagicMock(return_value={"Lista danych pomiarowych": []})
    )

    stored = ingest.ingest_station(STATION, db_session)

    assert stored is False
    assert db_session.query(Measurement).count() == 0


def test_ingest_station_skips_duplicate_reading(monkeypatch, db_session):
    monkeypatch.setattr(client, "fetch_sensors", MagicMock(return_value=SENSORS))
    monkeypatch.setattr(client, "fetch_sensor_data", MagicMock(return_value=SENSOR_DATA))

    first = ingest.ingest_station(STATION, db_session)
    second = ingest.ingest_station(STATION, db_session)

    assert first is True
    assert second is False
    assert db_session.query(Measurement).count() == 1


def test_ingest_station_isolates_api_failure(monkeypatch, db_session):
    """rule #1: one broken station must not raise past ingest_station()."""
    monkeypatch.setattr(
        client, "fetch_sensors", MagicMock(side_effect=client.GiosApiError("station offline"))
    )

    stored = ingest.ingest_station(STATION, db_session)

    assert stored is False
    assert db_session.query(Measurement).count() == 0


def test_ingest_station_isolates_parse_failure(monkeypatch, db_session):
    monkeypatch.setattr(client, "fetch_sensors", MagicMock(return_value=SENSORS))
    monkeypatch.setattr(
        client, "fetch_sensor_data", MagicMock(side_effect=GiosParseError("bad shape"))
    )

    stored = ingest.ingest_station(STATION, db_session)

    assert stored is False
    assert db_session.query(Measurement).count() == 0
