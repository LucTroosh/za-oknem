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
from app.models import Measurement, SourceFetch, SourceStatus

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

    assert stored is None  # fetch failed: distinct from 0 = nothing new (TASK-13.1)
    assert db_session.query(Measurement).count() == 0


def test_ingest_station_without_any_monitored_sensor_returns_none(monkeypatch, db_session):
    monkeypatch.setattr(client, "fetch_sensors", MagicMock(return_value=[]))
    errors: list[str] = []

    assert ingest.ingest_station(STATION, db_session, errors) is None
    assert "no monitored sensors" in errors[-1]


def test_ingest_station_all_params_failing_returns_none(monkeypatch, db_session):
    """TASK-13.1: 429 on every sensor fetch is an outage, not "0 new readings"."""
    monkeypatch.setattr(client, "fetch_sensors", MagicMock(return_value=SENSORS))
    monkeypatch.setattr(
        client, "fetch_sensor_data", MagicMock(side_effect=client.GiosApiError("429"))
    )
    errors: list[str] = []

    assert ingest.ingest_station(STATION, db_session, errors) is None
    assert errors and "429" in errors[-1]


def test_ingest_station_partial_param_failure_is_not_a_failed_station(monkeypatch, db_session):
    two = [*SENSORS, {"Identyfikator stanowiska": 25989, "Wskaźnik - wzór": "PM10"}]
    monkeypatch.setattr(client, "fetch_sensors", MagicMock(return_value=two))
    monkeypatch.setattr(
        client,
        "fetch_sensor_data",
        MagicMock(side_effect=[client.GiosApiError("429"), SENSOR_DATA]),
    )

    assert ingest.ingest_station(STATION, db_session) is not None


def test_ingest_station_isolates_parse_failure_per_param(monkeypatch, db_session):
    """One param's malformed data (fetch_sensor_data raising) must not skip the
    others — rule #1 isolation now applies per-param, not just per-station."""
    monkeypatch.setattr(client, "fetch_sensors", MagicMock(return_value=SENSORS))
    monkeypatch.setattr(
        client, "fetch_sensor_data", MagicMock(side_effect=GiosParseError("bad shape"))
    )

    stored = ingest.ingest_station(STATION, db_session)

    assert stored is None  # the only attempted param failed: failed station
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
        assert fetch.endpoint.endswith("/data/getData/25988?size=100")  # the request that was made
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

        assert stored is None  # only attempted param failed: failed station (TASK-13.1)
        fetch = db_session.query(SourceFetch).one()
        assert fetch.payload == bad
        assert fetch.validation_status == provenance.INVALID

    def test_payload_survives_an_unexpected_parser_crash_as_pending(self, monkeypatch, db_session):
        monkeypatch.setattr(client, "fetch_sensors", MagicMock(return_value=SENSORS))
        monkeypatch.setattr(client, "fetch_sensor_data", MagicMock(return_value=SENSOR_DATA))
        monkeypatch.setattr(ingest, "parse_values", MagicMock(side_effect=RuntimeError("bug")))

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

    def test_list_prints_stations_and_exits_without_touching_db(self, monkeypatch, capsys):
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

    def test_cli_subset_run_does_not_record_source_status(self, monkeypatch, db_session):
        monkeypatch.setenv("GIOS_STATION_IDS", "38,42")
        monkeypatch.setattr(sys, "argv", ["ingest", "--station-id", "38"])
        monkeypatch.setattr(client, "find_stations", MagicMock(return_value=[STATION]))
        monkeypatch.setattr(ingest, "SessionLocal", lambda: db_session)
        monkeypatch.setattr(ingest, "ingest_station", MagicMock(return_value=0))

        ingest.main()

        assert db_session.get(SourceStatus, "gios") is None

    def test_cli_records_source_status(self, monkeypatch, db_session):
        monkeypatch.setenv("GIOS_STATION_IDS", "38")
        monkeypatch.setattr(sys, "argv", ["ingest", "--station-id", "38"])
        monkeypatch.setattr(client, "find_stations", MagicMock(return_value=[STATION]))
        monkeypatch.setattr(ingest, "SessionLocal", lambda: db_session)
        monkeypatch.setattr(ingest, "ingest_station", MagicMock(return_value=0))

        ingest.main()

        assert db_session.get(SourceStatus, "gios").last_success_at is not None

    def test_cli_records_failure_when_station_catalog_is_unavailable(self, monkeypatch, db_session):
        monkeypatch.setenv("GIOS_STATION_IDS", "38")
        monkeypatch.setattr(sys, "argv", ["ingest", "--station-id", "38"])
        monkeypatch.setattr(
            client, "find_stations", MagicMock(side_effect=client.GiosApiError("catalog down"))
        )
        monkeypatch.setattr(ingest, "SessionLocal", lambda: db_session)

        with pytest.raises(client.GiosApiError):
            ingest.main()

        row = db_session.get(SourceStatus, "gios")
        assert row.last_success_at is None and "catalog down" in row.last_error

    def test_cli_records_failure_and_raises_when_every_station_failed(
        self, monkeypatch, db_session
    ):
        monkeypatch.setenv("GIOS_STATION_IDS", "38")
        monkeypatch.setattr(sys, "argv", ["ingest", "--station-id", "38"])
        monkeypatch.setattr(client, "find_stations", MagicMock(return_value=[STATION]))
        monkeypatch.setattr(ingest, "SessionLocal", lambda: db_session)

        def failing(_station, _db, errors):
            errors.append("GiosApiError: 429")

        monkeypatch.setattr(ingest, "ingest_station", failing)

        with pytest.raises(RuntimeError):
            ingest.main()

        row = db_session.get(SourceStatus, "gios")
        assert row.last_success_at is None and "429" in row.last_error


WINDOW = {
    "Lista danych pomiarowych": [
        {"Data": "2026-09-28 18:00:00", "Wartość": 8.2},
        {"Data": "2026-09-28 17:00:00", "Wartość": None},
        {"Data": "2026-09-28 16:00:00", "Wartość": 7.1},
        {"Data": "2026-09-28 15:00:00", "Wartość": 6.0},
    ]
}


class TestWholeWindow:
    """The response carries the last hours, not one reading: all of it is stored."""

    def _run(self, monkeypatch, db_session, data):
        monkeypatch.setattr(client, "fetch_sensors", MagicMock(return_value=SENSORS))
        fetch = MagicMock(return_value=data)
        monkeypatch.setattr(client, "fetch_sensor_data", fetch)
        return ingest.ingest_station(STATION, db_session), fetch

    def test_every_non_null_value_is_stored_and_asked_for_in_one_request(
        self, monkeypatch, db_session
    ):
        stored, fetch = self._run(monkeypatch, db_session, WINDOW)

        assert stored == 1  # params with something new, as before
        rows = db_session.query(Measurement).order_by(Measurement.observed_at).all()
        assert [r.value for r in rows] == [6.0, 7.1, 8.2]  # the null hour is not a zero
        assert (
            fetch.call_count == 1
            and fetch.call_args.kwargs["size"] == ingest.settings.gios_data_size
        )
        assert {r.source_fetch_id for r in rows} == {db_session.query(SourceFetch).one().id}

    def test_source_record_id_keeps_the_format_older_rows_already_use(
        self, monkeypatch, db_session
    ):
        self._run(monkeypatch, db_session, SENSOR_DATA)
        row = db_session.query(Measurement).one()
        assert row.source_record_id == "25988:2026-09-28T18:00:00+02:00"

    def test_a_missed_run_is_filled_in_by_the_next_one(self, monkeypatch, db_session):
        self._run(monkeypatch, db_session, SENSOR_DATA)  # only the 18:00 reading is known
        stored, _ = self._run(monkeypatch, db_session, WINDOW)

        assert stored == 1
        assert db_session.query(Measurement).count() == 3  # 15:00, 16:00 added, 18:00 not doubled

    def test_nothing_new_in_the_window_stores_nothing(self, monkeypatch, db_session):
        self._run(monkeypatch, db_session, WINDOW)
        stored, _ = self._run(monkeypatch, db_session, WINDOW)
        assert stored == 0 and db_session.query(Measurement).count() == 3

    def test_an_older_invalid_value_does_not_hold_back_the_rest(self, monkeypatch, db_session):
        data = {
            "Lista danych pomiarowych": [
                {"Data": "2026-09-28 18:00:00", "Wartość": 8.2},
                {"Data": "2026-09-28 17:00:00", "Wartość": -3.0},  # negative: rejected by normalize
                {"Data": "2026-09-28 16:00:00", "Wartość": 7.1},
            ]
        }
        stored, _ = self._run(monkeypatch, db_session, data)
        assert stored == 1
        assert sorted(r.value for r in db_session.query(Measurement)) == [7.1, 8.2]

    def test_an_invalid_newest_value_is_still_a_failed_run(self, monkeypatch, db_session):
        data = {
            "Lista danych pomiarowych": [
                {"Data": "2026-09-28 18:00:00", "Wartość": -3.0},
                {"Data": "2026-09-28 17:00:00", "Wartość": 7.1},
            ]
        }
        stored, _ = self._run(monkeypatch, db_session, data)
        assert stored is None  # the only attempted param failed
        assert db_session.query(Measurement).count() == 0
        assert db_session.query(SourceFetch).one().validation_status == provenance.INVALID

    def test_both_copies_of_the_hour_the_clocks_go_back_are_stored(self, monkeypatch, db_session):
        data = {
            "Lista danych pomiarowych": [
                {"Data": "2026-10-25 03:00:00", "Wartość": 4.0},
                {"Data": "2026-10-25 02:00:00", "Wartość": 3.0},
                {"Data": "2026-10-25 02:00:00", "Wartość": 2.0},
            ]
        }
        self._run(monkeypatch, db_session, data)
        assert sorted(r.value for r in db_session.query(Measurement)) == [2.0, 3.0, 4.0]

    def test_a_race_with_another_run_is_retried_once(self, monkeypatch, db_session):
        from sqlalchemy.exc import IntegrityError

        real_commit = db_session.commit
        calls = {"n": 0}

        def flaky_commit():
            calls["n"] += 1
            if calls["n"] == 1:
                raise IntegrityError("insert", {}, Exception("duplicate"))
            return real_commit()

        monkeypatch.setattr(db_session, "commit", flaky_commit)
        stored, _ = self._run(monkeypatch, db_session, WINDOW)
        assert stored == 1 and db_session.query(Measurement).count() == 3


class TestPartialAndUnusableEntries:
    def _run(self, monkeypatch, db_session, data):
        monkeypatch.setattr(client, "fetch_sensors", MagicMock(return_value=SENSORS))
        monkeypatch.setattr(client, "fetch_sensor_data", MagicMock(return_value=data))
        return ingest.ingest_station(STATION, db_session)

    def test_a_clean_window_is_valid(self, monkeypatch, db_session):
        self._run(monkeypatch, db_session, WINDOW)
        assert db_session.query(SourceFetch).one().validation_status == provenance.VALID

    def test_rejected_older_entries_make_the_fetch_partial_not_valid(self, monkeypatch, db_session):
        data = {
            "Lista danych pomiarowych": [
                {"Data": "2026-09-28 18:00:00", "Wartość": 8.2},
                {"Data": "2026-09-28 17:00:00", "Wartość": "abc"},  # unparseable
                {"Data": "2026-09-28 16:00:00", "Wartość": -3.0},  # fails normalize
                {"Data": "2026-09-28 15:00:00", "Wartość": 6.0},
            ]
        }
        stored = self._run(monkeypatch, db_session, data)
        assert stored == 1
        assert sorted(r.value for r in db_session.query(Measurement)) == [6.0, 8.2]
        assert db_session.query(SourceFetch).one().validation_status == provenance.PARTIAL

    def test_an_unreadable_newest_entry_fails_the_run_even_with_good_older_ones(
        self, monkeypatch, db_session
    ):
        data = {
            "Lista danych pomiarowych": [
                {"Data": "2026-09-28 18:00:00", "Wartość": "abc"},
                {"Data": "2026-09-28 17:00:00", "Wartość": 7.1},
            ]
        }
        stored = self._run(monkeypatch, db_session, data)
        assert stored is None and db_session.query(Measurement).count() == 0
        assert db_session.query(SourceFetch).one().validation_status == provenance.INVALID

    def test_a_payload_with_no_usable_value_is_a_failed_run(self, monkeypatch, db_session):
        data = {"Lista danych pomiarowych": [{"Data": "2026-09-28 18:00:00", "Wartość": "abc"}]}
        assert self._run(monkeypatch, db_session, data) is None
