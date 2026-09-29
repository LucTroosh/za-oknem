"""Tests for ingest_station(): skip logic, idempotent dedupe, and the
one-broken-station-must-not-abort-the-run guarantee (rule #1). client.* calls
are mocked — no live network — and Measurement is stored in a real (SQLite)
session so dedupe is verified against actual DB state, not a mock."""

import sys
from unittest.mock import MagicMock

import pytest

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


class TestMain:
    """main(): argparse wiring only - ingest_station itself is covered above,
    so here we just verify main() calls it with the right stations and handles
    the --list / no-args paths without touching a real DB or network."""

    def test_list_prints_stations_and_exits_without_touching_db(
        self, monkeypatch, capsys
    ):
        monkeypatch.setattr(sys, "argv", ["ingest", "--list"])
        page = {
            "Lista stacji pomiarowych": [{"Identyfikator stacji": 38, "Nazwa stacji": "Kłodzko"}],
            "totalPages": 15,
        }
        monkeypatch.setattr(client, "fetch_station_page", MagicMock(return_value=page))
        session_local = MagicMock()
        monkeypatch.setattr(ingest, "SessionLocal", session_local)

        ingest.main()

        assert "38: Kłodzko" in capsys.readouterr().out
        session_local.assert_not_called()

    def test_no_station_id_exits_with_error(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["ingest"])

        with pytest.raises(SystemExit) as exc_info:
            ingest.main()

        assert exc_info.value.code == 1
        assert "No --station-id given" in capsys.readouterr().err

    def test_station_id_ingests_each_matched_station(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["ingest", "--station-id", "38", "--station-id", "42"])
        monkeypatch.setattr(client, "find_stations", MagicMock(return_value=[STATION, STATION]))
        fake_db = MagicMock()
        monkeypatch.setattr(ingest, "SessionLocal", lambda: fake_db)
        ingest_station_mock = MagicMock()
        monkeypatch.setattr(ingest, "ingest_station", ingest_station_mock)

        ingest.main()

        assert ingest_station_mock.call_count == 2
        fake_db.close.assert_called_once()
