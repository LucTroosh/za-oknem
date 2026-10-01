"""Tests for the loop-based scheduler (ADR-007/ADR-008): interval gating and the
explicit opt-in for GIOS_STATION_IDS. ingest_* themselves are already covered
by the connectors' own ingest tests - only the scheduling wiring is new here."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

import app.scheduler as scheduler
from app.connectors.open_meteo_pollen import client as pollen_client
from app.models import Alert, GeoArea, SourceFetch


def _make_area(db, slug="klodzko") -> GeoArea:
    area = GeoArea(slug=slug, name=slug, latitude=50.43, longitude=16.65)
    db.add(area)
    db.commit()
    return area


class TestRunOpenMeteo:
    def test_ingests_every_geo_area(self, monkeypatch, db_session):
        _make_area(db_session, "klodzko")
        _make_area(db_session, "warszawa")
        monkeypatch.setattr(scheduler, "SessionLocal", lambda: db_session)
        mock = MagicMock()
        monkeypatch.setattr(scheduler, "ingest_geo_area", mock)

        scheduler.run_open_meteo()

        assert mock.call_count == 2

    def test_all_areas_failing_raises_so_it_is_not_recorded_as_success(
        self, monkeypatch, db_session
    ):
        import pytest

        _make_area(db_session, "klodzko")
        _make_area(db_session, "warszawa")
        monkeypatch.setattr(scheduler, "SessionLocal", lambda: db_session)
        monkeypatch.setattr(scheduler, "ingest_geo_area", MagicMock(return_value=None))

        with pytest.raises(RuntimeError, match="2/2 failed"):
            scheduler.run_open_meteo()

    def test_partial_failure_is_still_a_run(self, monkeypatch, db_session):
        _make_area(db_session, "klodzko")
        _make_area(db_session, "warszawa")
        monkeypatch.setattr(scheduler, "SessionLocal", lambda: db_session)
        monkeypatch.setattr(scheduler, "ingest_geo_area", MagicMock(side_effect=[None, 3]))

        scheduler.run_open_meteo()  # no raise

    def test_no_geo_areas_is_a_skip_not_a_success(self, monkeypatch, db_session):
        monkeypatch.setattr(scheduler, "SessionLocal", lambda: db_session)
        record = MagicMock()
        monkeypatch.setattr(scheduler, "_record_run", record)

        scheduler._run_job_safely("open_meteo", scheduler.run_open_meteo)

        record.assert_not_called()

    def test_failure_message_carries_last_cause(self, monkeypatch, db_session):
        import pytest

        _make_area(db_session)
        monkeypatch.setattr(scheduler, "SessionLocal", lambda: db_session)

        def failing(_area, _db, errors):
            errors.append("OpenMeteoApiError: HTTP 429")

        monkeypatch.setattr(scheduler, "ingest_geo_area", failing)

        with pytest.raises(RuntimeError, match="last cause: OpenMeteoApiError: HTTP 429"):
            scheduler.run_open_meteo()

    def test_zero_new_rows_is_success_not_failure(self, monkeypatch, db_session):
        _make_area(db_session)
        monkeypatch.setattr(scheduler, "SessionLocal", lambda: db_session)
        monkeypatch.setattr(scheduler, "ingest_geo_area", MagicMock(return_value=0))

        scheduler.run_open_meteo()  # fetched, nothing new: no raise

    def test_skips_areas_without_active_weather_polling(self, monkeypatch, db_session):
        # ADR-019: imported gminas exist for geo-matching only; polling them all would
        # exceed the Open-Meteo daily budget.
        _make_area(db_session, "klodzko")
        inactive = _make_area(db_session, "teryt-9999901")
        inactive.weather_polling_active = False
        db_session.commit()
        monkeypatch.setattr(scheduler, "SessionLocal", lambda: db_session)
        mock = MagicMock()
        monkeypatch.setattr(scheduler, "ingest_geo_area", mock)

        scheduler.run_open_meteo()

        assert [c.args[0].slug for c in mock.call_args_list] == ["klodzko"]


class TestRunOpenMeteoPollen:
    def test_ingests_every_geo_area_and_reports_success(self, monkeypatch, db_session):
        _make_area(db_session, "klodzko")
        _make_area(db_session, "warszawa")
        monkeypatch.setattr(scheduler, "SessionLocal", lambda: db_session)
        monkeypatch.setattr(db_session, "close", lambda: None)
        mock = MagicMock(return_value=True)
        monkeypatch.setattr(scheduler, "ingest_pollen_areas", mock)

        assert scheduler.run_open_meteo_pollen() is True

        (areas, db), _ = mock.call_args
        assert len(areas) == 2 and db is db_session

    def test_skips_areas_without_active_polling(self, monkeypatch, db_session):
        # ADR-019/ADR-001 option C: never fan out over every imported gmina.
        _make_area(db_session, "klodzko")
        inactive = _make_area(db_session, "teryt-9999901")
        inactive.weather_polling_active = False
        db_session.commit()
        monkeypatch.setattr(scheduler, "SessionLocal", lambda: db_session)
        monkeypatch.setattr(db_session, "close", lambda: None)
        mock = MagicMock(return_value=True)
        monkeypatch.setattr(scheduler, "ingest_pollen_areas", mock)

        scheduler.run_open_meteo_pollen()

        (areas, _db), _ = mock.call_args
        assert [a.slug for a in areas] == ["klodzko"]

    def test_no_geo_areas_is_skipped_not_a_success(self, monkeypatch, db_session):
        monkeypatch.setattr(scheduler, "SessionLocal", lambda: db_session)
        monkeypatch.setattr(db_session, "close", lambda: None)
        record = MagicMock()
        monkeypatch.setattr(scheduler, "_record_run", record)

        scheduler._run_job_safely("open_meteo_pollen", scheduler.run_open_meteo_pollen)

        record.assert_not_called()  # ADR-012: nothing fetched -> nothing recorded

    def test_total_failure_is_recorded_as_failure(self, monkeypatch, db_session):
        _make_area(db_session)
        monkeypatch.setattr(scheduler, "SessionLocal", lambda: db_session)
        monkeypatch.setattr(db_session, "close", lambda: None)
        monkeypatch.setattr(
            pollen_client,
            "fetch_pollen",
            MagicMock(side_effect=pollen_client.OpenMeteoPollenApiError("down")),
        )
        record = MagicMock()
        monkeypatch.setattr(scheduler, "_record_run", record)

        scheduler._run_job_safely("open_meteo_pollen", scheduler.run_open_meteo_pollen)

        assert record.call_args.kwargs["success"] is False
        assert "all 1 geo_area" in record.call_args.kwargs["error"]


class TestRunGios:
    def test_skips_when_no_station_ids_configured(self, monkeypatch):
        monkeypatch.delenv("GIOS_STATION_IDS", raising=False)
        find_stations_mock = MagicMock()
        monkeypatch.setattr(scheduler.gios_client, "find_stations", find_stations_mock)

        scheduler.run_gios()

        find_stations_mock.assert_not_called()

    def test_no_matching_station_raises_so_it_is_not_recorded_as_success(
        self, monkeypatch, db_session
    ):
        import pytest

        monkeypatch.setenv("GIOS_STATION_IDS", "999")
        monkeypatch.setattr(scheduler, "SessionLocal", lambda: db_session)
        monkeypatch.setattr(scheduler.gios_client, "find_stations", MagicMock(return_value=[]))

        with pytest.raises(RuntimeError, match="1/1 failed"):
            scheduler.run_gios()

    def test_all_stations_failing_raises(self, monkeypatch, db_session):
        import pytest

        monkeypatch.setenv("GIOS_STATION_IDS", "38,42")
        monkeypatch.setattr(scheduler, "SessionLocal", lambda: db_session)
        stations = [{"Identyfikator stacji": 38}, {"Identyfikator stacji": 42}]
        find = MagicMock(return_value=stations)
        monkeypatch.setattr(scheduler.gios_client, "find_stations", find)
        monkeypatch.setattr(scheduler, "ingest_station", MagicMock(return_value=None))

        with pytest.raises(RuntimeError, match="2/2 failed"):
            scheduler.run_gios()

    def test_unmatched_configured_ids_count_as_failures(self, monkeypatch, db_session):
        import pytest

        monkeypatch.setenv("GIOS_STATION_IDS", "38,42,43")
        monkeypatch.setattr(scheduler, "SessionLocal", lambda: db_session)
        find = MagicMock(return_value=[{"Identyfikator stacji": 38}])  # 42, 43 not in catalog
        monkeypatch.setattr(scheduler.gios_client, "find_stations", find)
        monkeypatch.setattr(scheduler, "ingest_station", MagicMock(return_value=1))

        with pytest.raises(RuntimeError, match="2/3 failed; last cause: station id"):
            scheduler.run_gios()

    def test_one_unmatched_of_three_is_still_a_run(self, monkeypatch, db_session):
        monkeypatch.setenv("GIOS_STATION_IDS", "38,42,43")
        monkeypatch.setattr(scheduler, "SessionLocal", lambda: db_session)
        stations = [{"Identyfikator stacji": 38}, {"Identyfikator stacji": 42}]
        monkeypatch.setattr(
            scheduler.gios_client, "find_stations", MagicMock(return_value=stations)
        )
        monkeypatch.setattr(scheduler, "ingest_station", MagicMock(return_value=1))

        assert scheduler.run_gios() is True

    def test_partial_station_failure_is_still_a_run(self, monkeypatch, db_session):
        monkeypatch.setenv("GIOS_STATION_IDS", "38,42")
        monkeypatch.setattr(scheduler, "SessionLocal", lambda: db_session)
        stations = [{"Identyfikator stacji": 38}, {"Identyfikator stacji": 42}]
        find = MagicMock(return_value=stations)
        monkeypatch.setattr(scheduler.gios_client, "find_stations", find)
        monkeypatch.setattr(scheduler, "ingest_station", MagicMock(side_effect=[None, 0]))

        assert scheduler.run_gios() is True

    def test_ingests_configured_stations(self, monkeypatch, db_session):
        monkeypatch.setenv("GIOS_STATION_IDS", "38, 42")
        monkeypatch.setattr(scheduler, "SessionLocal", lambda: db_session)
        station = {"Identyfikator stacji": 38}
        monkeypatch.setattr(
            scheduler.gios_client, "find_stations", MagicMock(return_value=[station])
        )
        ingest_mock = MagicMock()
        monkeypatch.setattr(scheduler, "ingest_station", ingest_mock)

        scheduler.run_gios()

        scheduler.gios_client.find_stations.assert_called_once_with({"38", "42"})
        ingest_mock.assert_called_once()
        assert ingest_mock.call_args.args[:2] == (station, db_session)


class TestRunImgwHydro:
    def _stations(self, good, bad=0):
        base = {
            "id_stacji": "1", "stacja": "S", "rzeka": "R", "lat": "51.5", "lon": "14.8",
            "stan_wody": "225", "stan_wody_data_pomiaru": "2026-09-27 21:20:00",
            "stan_ostrzegawczy": None, "stan_alarmowy": None,
        }  # fmt: skip
        stations = [{**base, "id_stacji": str(i)} for i in range(good)]
        return stations + [{**base, "id_stacji": f"bad{i}", "lat": "x"} for i in range(bad)]

    def _run(self, monkeypatch, db_session, stations):
        monkeypatch.setattr(scheduler, "SessionLocal", lambda: db_session)
        monkeypatch.setattr(
            scheduler.imgw_hydro_client, "fetch_stations", MagicMock(return_value=stations)
        )
        scheduler.run_imgw_hydro()  # real ingest_snapshot

    def test_one_bad_station_in_many_is_a_success(self, monkeypatch, db_session, caplog):
        self._run(monkeypatch, db_session, self._stations(99, bad=1))
        assert "bad0" in caplog.text  # ids of rejected stations logged every run

    def test_rejected_over_the_bound_is_a_failure(self, monkeypatch, db_session):
        with pytest.raises(RuntimeError, match="3/100 failed"):
            self._run(monkeypatch, db_session, self._stations(97, bad=3))

    def test_every_station_rejected_is_a_failure(self, monkeypatch, db_session):
        with pytest.raises(RuntimeError, match="1/1 failed"):
            self._run(monkeypatch, db_session, self._stations(0, bad=1))

    def test_empty_response_is_a_failure(self, monkeypatch, db_session):
        with pytest.raises(RuntimeError, match="nothing returned"):
            self._run(monkeypatch, db_session, [])

    def test_ingests_whole_response_as_one_snapshot_no_gating(self, monkeypatch, db_session):
        # Unlike GIOS, no env var gate - one call already returns every station,
        # deterministic (ADR-008). ADR-014: the whole response is one raw fetch.
        monkeypatch.setattr(scheduler, "SessionLocal", lambda: db_session)
        stations = [{"id_stacji": "1"}, {"id_stacji": "2"}]
        monkeypatch.setattr(
            scheduler.imgw_hydro_client, "fetch_stations", MagicMock(return_value=stations)
        )
        snapshot_mock = MagicMock(return_value=(0, 0))
        monkeypatch.setattr(scheduler, "ingest_hydro_snapshot", snapshot_mock)

        scheduler.run_imgw_hydro()

        snapshot_mock.assert_called_once()
        args, kwargs = snapshot_mock.call_args
        assert args == (stations, db_session)
        # fetched_at is one timestamp for the whole batch.
        assert kwargs["fetched_at"].tzinfo == UTC


class TestRunImgwWarningsHydro:
    def test_ingests_every_warning_and_keeps_the_raw_payload(self, monkeypatch, db_session):
        monkeypatch.setattr(scheduler, "SessionLocal", lambda: db_session)
        raw = [{"numer": "1"}, {"numer": "2"}]
        monkeypatch.setattr(
            scheduler.imgw_warnings_client, "fetch_warnings", MagicMock(return_value=raw)
        )
        raw_mock = MagicMock(return_value=(0, 0, 0))
        monkeypatch.setattr(scheduler, "ingest_raw", raw_mock)

        scheduler.run_imgw_warningshydro()

        raw_mock.assert_called_once()
        args, kwargs = raw_mock.call_args
        assert args == (raw, db_session)
        assert "fetched_at" in kwargs

    def test_empty_message_shape_ingests_nothing(self, monkeypatch, db_session):
        monkeypatch.setattr(scheduler, "SessionLocal", lambda: db_session)
        monkeypatch.setattr(
            scheduler.imgw_warnings_client,
            "fetch_warnings",
            MagicMock(return_value={"message": "Brak"}),
        )

        scheduler.run_imgw_warningshydro()  # real ingest_raw, SQLite session

        assert db_session.query(Alert).count() == 0
        fetch = db_session.query(SourceFetch).one()
        assert fetch.payload == {"message": "Brak"}
        assert fetch.validation_status == "valid"


class TestRunImgwWarningsHydroIncomplete:
    def test_incomplete_snapshot_raises_so_it_is_not_recorded_as_success(
        self, monkeypatch, db_session
    ):
        # ADR-012 / Codex P1: a rejected warning may be the active one - the run
        # must not refresh last_success_at (false all-clear on the client).
        monkeypatch.setattr(scheduler, "SessionLocal", lambda: db_session)
        monkeypatch.setattr(
            scheduler.imgw_warnings_client, "fetch_warnings", MagicMock(return_value=[{}])
        )
        monkeypatch.setattr(scheduler, "ingest_raw", MagicMock(return_value=(0, 0, 1)))
        record = MagicMock()
        monkeypatch.setattr(scheduler, "_record_run", record)

        scheduler._run_job_safely("imgw_warningshydro", scheduler.run_imgw_warningshydro)

        assert record.call_args.kwargs["success"] is False
        assert "snapshot incomplete" in record.call_args.kwargs["error"]


class TestRunRawRetention:
    def test_purges_expired_payloads(self, monkeypatch, db_session):
        monkeypatch.setattr(scheduler, "SessionLocal", lambda: db_session)
        old = datetime.now(UTC) - timedelta(days=60)
        db_session.add(
            SourceFetch(
                source_id="gios",
                endpoint="x",
                fetched_at=old,
                parser_version="1",
                validation_status="valid",
                payload={"a": 1},
            )
        )
        db_session.commit()

        scheduler.run_raw_retention()

        assert db_session.query(SourceFetch).one().payload is None

    def test_failure_does_not_record_source_status_or_raise(self, monkeypatch):
        # Housekeeping is not a data source: no source_status row (ADR-012), and
        # like every job it must not take the scheduler down (rule #1).
        record = MagicMock()
        monkeypatch.setattr(scheduler, "_record_run", record)
        monkeypatch.setattr(scheduler, "SessionLocal", MagicMock(side_effect=RuntimeError("db")))

        scheduler._run_job_safely("raw_retention", scheduler.run_raw_retention, track_status=False)

        record.assert_not_called()


class TestMain:
    def _mock_all_jobs(self, monkeypatch):
        mocks = {
            "run_open_meteo": MagicMock(),
            "run_open_meteo_pollen": MagicMock(),
            "run_gios": MagicMock(),
            "run_imgw_hydro": MagicMock(),
            "run_imgw_warningshydro": MagicMock(),
            "run_raw_retention": MagicMock(),
        }
        for name, mock in mocks.items():
            monkeypatch.setattr(scheduler, name, mock)
        monkeypatch.setattr(scheduler.time, "sleep", MagicMock())
        monkeypatch.setattr(scheduler, "_record_run", MagicMock())
        monkeypatch.setattr(scheduler, "_check_source_health", MagicMock())
        return mocks

    def test_first_iteration_runs_every_job(self, monkeypatch):
        mocks = self._mock_all_jobs(monkeypatch)

        scheduler.main(iterations=1)

        for mock in mocks.values():
            mock.assert_called_once()

    def test_second_iteration_skips_jobs_before_interval_elapses(self, monkeypatch):
        mocks = self._mock_all_jobs(monkeypatch)
        # Same monotonic value every call - no interval has elapsed since "last".
        monkeypatch.setattr(scheduler.time, "monotonic", lambda: 1000.0)

        scheduler.main(iterations=2)

        for mock in mocks.values():
            mock.assert_called_once()

    def test_third_iteration_reruns_gios_after_its_interval(self, monkeypatch):
        mocks = self._mock_all_jobs(monkeypatch)
        # 0s, then just past the 1h GIOS interval - open_meteo's 3h interval hasn't
        # elapsed yet, so this isolates the per-job gating (not just "run again").
        ticks = iter([0.0, scheduler.GIOS_INTERVAL_SECONDS + 1])
        monkeypatch.setattr(scheduler.time, "monotonic", lambda: next(ticks))

        scheduler.main(iterations=2)

        assert mocks["run_gios"].call_count == 2
        assert mocks["run_open_meteo"].call_count == 1
        assert mocks["run_open_meteo_pollen"].call_count == 1

    def test_pollen_runs_once_per_24h_cycle_not_more_often(self, monkeypatch):
        # ADR-004/ADR-020: CAMS Europe publishes once a day - 23h later is too early,
        # 24h later is the next cycle.
        mocks = self._mock_all_jobs(monkeypatch)
        day = 24 * 60 * 60
        ticks = iter([0.0, day - 3600, day])
        monkeypatch.setattr(scheduler.time, "monotonic", lambda: next(ticks))

        scheduler.main(iterations=3)

        assert day == scheduler.OPEN_METEO_POLLEN_INTERVAL_SECONDS
        assert mocks["run_open_meteo_pollen"].call_count == 2

    def test_one_job_failing_does_not_abort_the_others(self, monkeypatch):
        # Codex review (PR #37): an unhandled connector failure used to propagate
        # out of main() and kill the whole scheduler loop - rule #1 says one
        # broken source must not take the rest down with it.
        mocks = self._mock_all_jobs(monkeypatch)
        mocks["run_gios"].side_effect = RuntimeError("IMGW/GIOS unreachable")

        scheduler.main(iterations=1)

        for mock in mocks.values():
            mock.assert_called_once()


class TestSourceStatusRecording:
    """ADR-012: each job run is recorded so an empty list can be told apart from
    a source we couldn't fetch."""

    def test_successful_job_records_success(self, monkeypatch):
        record = MagicMock()
        monkeypatch.setattr(scheduler, "_record_run", record)

        scheduler._run_job_safely("imgw_warningshydro", lambda: None)

        record.assert_called_once_with("imgw_warningshydro", success=True)

    def test_failing_job_records_failure_with_error(self, monkeypatch):
        record = MagicMock()
        monkeypatch.setattr(scheduler, "_record_run", record)

        def _boom():
            raise RuntimeError("IMGW down")

        scheduler._run_job_safely("imgw_warningshydro", _boom)

        record.assert_called_once_with(
            "imgw_warningshydro", success=False, error="RuntimeError: IMGW down"
        )

    def test_skipped_job_records_nothing(self, monkeypatch):
        record = MagicMock()
        monkeypatch.setattr(scheduler, "_record_run", record)
        monkeypatch.delenv("GIOS_STATION_IDS", raising=False)

        scheduler._run_job_safely("gios", scheduler.run_gios)

        record.assert_not_called()

    def test_recording_failure_does_not_raise(self, monkeypatch):
        # rule #1: a DB hiccup while recording must not crash the scheduler.
        def _broken_session():
            raise RuntimeError("db down")

        monkeypatch.setattr(scheduler, "SessionLocal", _broken_session)

        scheduler._record_run("imgw_warningshydro", success=True)  # no exception


class TestCheckSourceHealth:
    def test_logs_transition_once_across_ticks(self, monkeypatch, db_session, caplog):
        monkeypatch.setattr(scheduler, "SessionLocal", lambda: db_session)
        monkeypatch.setenv("GIOS_STATION_IDS", "1")
        _make_area(db_session)
        state: dict[str, str] = {}

        scheduler._check_source_health(state)
        scheduler._check_source_health(state)

        # Nothing ever fetched -> every source UNAVAILABLE, logged once each.
        errors = [
            r for r in caplog.records if r.name == "app.source_health" and r.levelname == "ERROR"
        ]
        assert len(errors) == 4
        assert set(state.values()) == {"UNAVAILABLE"}

    def test_open_meteo_without_geo_areas_is_not_monitored(self, monkeypatch, db_session):
        monkeypatch.setattr(scheduler, "SessionLocal", lambda: db_session)
        state: dict[str, str] = {}

        scheduler._check_source_health(state)

        assert "open_meteo" not in state

    def test_state_is_replaced_so_a_disabled_source_loses_its_cache(self, monkeypatch, db_session):
        monkeypatch.setattr(scheduler, "SessionLocal", lambda: db_session)
        monkeypatch.delenv("GIOS_STATION_IDS", raising=False)
        state = {"open_meteo": "UNAVAILABLE", "gios": "STALE"}  # both now unmonitored

        scheduler._check_source_health(state)

        assert "open_meteo" not in state and "gios" not in state

    def test_skips_gios_when_not_configured(self, monkeypatch, db_session):
        monkeypatch.setattr(scheduler, "SessionLocal", lambda: db_session)
        monkeypatch.delenv("GIOS_STATION_IDS", raising=False)
        state: dict[str, str] = {}

        scheduler._check_source_health(state)

        assert "gios" not in state

    def test_close_failure_does_not_escape(self, monkeypatch):
        session = MagicMock()
        session.close.side_effect = RuntimeError("dead conn")
        monkeypatch.setattr(scheduler, "SessionLocal", lambda: session)
        monkeypatch.setattr(scheduler, "collect_source_health", MagicMock(return_value=[]))

        scheduler._check_source_health({})

    def test_never_raises(self, monkeypatch):
        monkeypatch.setattr(scheduler, "SessionLocal", MagicMock(side_effect=RuntimeError("db")))

        scheduler._check_source_health({})
