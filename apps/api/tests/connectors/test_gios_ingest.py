"""Tests for ingest_station(): skip logic, idempotent dedupe, and the
one-broken-station-must-not-abort-the-run guarantee (rule #1). client.* calls
are mocked — no live network — and Measurement is stored in a real (SQLite)
session so dedupe is verified against actual DB state, not a mock."""

import sys
from unittest.mock import MagicMock

import pytest

from app import provenance
from app.connectors.gios import client, ingest
from app.connectors.gios.parser import PARSER_VERSION, GiosParseError
from app.models import Measurement, SourceFetch

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

    assert stored == 1  # only PM2.5 has a sensor in SENSORS; other params skip
    rows = db_session.query(Measurement).all()
    assert len(rows) == 1
    assert rows[0].station_id == "38"
    assert rows[0].value == 8.2


def test_ingest_station_stores_one_reading_per_available_sensor(monkeypatch, db_session):
    sensors = [
        {"Identyfikator stanowiska": 25988, "Wskaźnik - wzór": "PM2.5"},
        {"Identyfikator stanowiska": 1, "Wskaźnik - wzór": "PM10"},
        {"Identyfikator stanowiska": 2, "Wskaźnik - wzór": "NO2"},
    ]
    monkeypatch.setattr(client, "fetch_sensors", MagicMock(return_value=sensors))
    monkeypatch.setattr(client, "fetch_sensor_data", MagicMock(return_value=SENSOR_DATA))

    stored = ingest.ingest_station(STATION, db_session)

    assert stored == 3
    assert {r.param_code for r in db_session.query(Measurement).all()} == {"PM2.5", "PM10", "NO2"}


def test_ingest_station_skips_params_with_no_sensor(monkeypatch, db_session):
    only_pm10 = [{"Identyfikator stanowiska": 1, "Wskaźnik - wzór": "PM10"}]
    monkeypatch.setattr(client, "fetch_sensors", MagicMock(return_value=only_pm10))
    monkeypatch.setattr(client, "fetch_sensor_data", MagicMock(return_value=SENSOR_DATA))

    stored = ingest.ingest_station(STATION, db_session)

    assert stored == 1
    assert db_session.query(Measurement).one().param_code == "PM10"


def test_ingest_station_skips_when_no_recent_values(monkeypatch, db_session):
    monkeypatch.setattr(client, "fetch_sensors", MagicMock(return_value=SENSORS))
    monkeypatch.setattr(
        client, "fetch_sensor_data", MagicMock(return_value={"Lista danych pomiarowych": []})
    )

    stored = ingest.ingest_station(STATION, db_session)

    assert stored == 0
    assert db_session.query(Measurement).count() == 0


def test_ingest_station_skips_duplicate_reading(monkeypatch, db_session):
    monkeypatch.setattr(client, "fetch_sensors", MagicMock(return_value=SENSORS))
    monkeypatch.setattr(client, "fetch_sensor_data", MagicMock(return_value=SENSOR_DATA))

    first = ingest.ingest_station(STATION, db_session)
    second = ingest.ingest_station(STATION, db_session)

    assert first == 1
    assert second == 0
    assert db_session.query(Measurement).count() == 1


def test_ingest_station_isolates_api_failure(monkeypatch, db_session):
    """rule #1: one broken station must not raise past ingest_station()."""
    monkeypatch.setattr(
        client, "fetch_sensors", MagicMock(side_effect=client.GiosApiError("station offline"))
    )

    stored = ingest.ingest_station(STATION, db_session)

    assert stored == 0
    assert db_session.query(Measurement).count() == 0


def test_ingest_station_isolates_parse_failure_per_param(monkeypatch, db_session):
    """One param's malformed data (fetch_sensor_data raising) must not skip the
    others — rule #1 isolation now applies per-param, not just per-station."""
    monkeypatch.setattr(client, "fetch_sensors", MagicMock(return_value=SENSORS))
    monkeypatch.setattr(
        client, "fetch_sensor_data", MagicMock(side_effect=GiosParseError("bad shape"))
    )

    stored = ingest.ingest_station(STATION, db_session)

    assert stored == 0
    assert db_session.query(Measurement).count() == 0


def test_ingest_station_isolates_malformed_sensor_missing_id(monkeypatch, db_session):
    """Codex review: a sensor dict missing "Identyfikator stanowiska" raised a
    bare KeyError from _ingest_param, uncaught, aborting every remaining param
    for the station instead of just skipping this one (rule #1 isolation)."""
    sensors = [
        {"Wskaźnik - wzór": "PM2.5"},  # malformed: no "Identyfikator stanowiska"
        {"Identyfikator stanowiska": 2, "Wskaźnik - wzór": "PM10"},
    ]
    monkeypatch.setattr(client, "fetch_sensors", MagicMock(return_value=sensors))
    monkeypatch.setattr(client, "fetch_sensor_data", MagicMock(return_value=SENSOR_DATA))

    stored = ingest.ingest_station(STATION, db_session)

    assert stored == 1
    assert db_session.query(Measurement).one().param_code == "PM10"


class TestProvenance:
    """ADR-014: every stored reading points at the raw getData payload that produced it."""

    def test_measurement_links_to_its_raw_fetch(self, monkeypatch, db_session):
        monkeypatch.setattr(client, "fetch_sensors", MagicMock(return_value=SENSORS))
        monkeypatch.setattr(client, "fetch_sensor_data", MagicMock(return_value=SENSOR_DATA))

        ingest.ingest_station(STATION, db_session)

        fetch = db_session.query(SourceFetch).one()
        assert db_session.query(Measurement).one().source_fetch_id == fetch.id
        assert fetch.source_id == "gios"
        assert fetch.endpoint.endswith("/data/getData/25988")
        assert fetch.payload == SENSOR_DATA
        assert fetch.parser_version == PARSER_VERSION
        assert fetch.validation_status == provenance.VALID

    def test_each_param_gets_its_own_fetch(self, monkeypatch, db_session):
        sensors = [
            {"Identyfikator stanowiska": 1, "Wskaźnik - wzór": "PM10"},
            {"Identyfikator stanowiska": 2, "Wskaźnik - wzór": "NO2"},
        ]
        monkeypatch.setattr(client, "fetch_sensors", MagicMock(return_value=sensors))
        monkeypatch.setattr(client, "fetch_sensor_data", MagicMock(return_value=SENSOR_DATA))

        ingest.ingest_station(STATION, db_session)

        ids = {m.source_fetch_id for m in db_session.query(Measurement).all()}
        assert len(ids) == 2
        assert db_session.query(SourceFetch).count() == 2

    def test_unparseable_payload_is_kept_as_invalid(self, monkeypatch, db_session):
        # The case raw payloads exist for: the source changed its shape.
        bad = {"unexpected": "shape"}
        monkeypatch.setattr(client, "fetch_sensors", MagicMock(return_value=SENSORS))
        monkeypatch.setattr(client, "fetch_sensor_data", MagicMock(return_value=bad))

        stored = ingest.ingest_station(STATION, db_session)

        assert stored == 0
        fetch = db_session.query(SourceFetch).one()
        assert fetch.payload == bad
        assert fetch.validation_status == provenance.INVALID

    def test_payload_survives_an_unexpected_parser_crash_as_pending(self, monkeypatch, db_session):
        monkeypatch.setattr(client, "fetch_sensors", MagicMock(return_value=SENSORS))
        monkeypatch.setattr(client, "fetch_sensor_data", MagicMock(return_value=SENSOR_DATA))
        monkeypatch.setattr(ingest, "latest_value", MagicMock(side_effect=RuntimeError("bug")))

        with pytest.raises(RuntimeError):
            ingest.ingest_station(STATION, db_session)

        fetch = db_session.query(SourceFetch).one()
        assert fetch.payload == SENSOR_DATA
        assert fetch.validation_status == provenance.PENDING

    def test_provenance_failure_does_not_block_the_reading(self, monkeypatch, db_session):
        # Rule #1: best-effort audit - the value is stored, link is NULL.
        monkeypatch.setattr(client, "fetch_sensors", MagicMock(return_value=SENSORS))
        monkeypatch.setattr(client, "fetch_sensor_data", MagicMock(return_value=SENSOR_DATA))
        monkeypatch.setattr(provenance, "record_fetch", MagicMock(return_value=None))

        stored = ingest.ingest_station(STATION, db_session)

        assert stored == 1
        assert db_session.query(Measurement).one().source_fetch_id is None


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
