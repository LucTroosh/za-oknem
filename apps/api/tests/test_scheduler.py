"""Tests for the loop-based scheduler (ADR-007/ADR-008): interval gating and the
explicit opt-in for GIOS_STATION_IDS. ingest_* themselves are already covered
by the connectors' own ingest tests - only the scheduling wiring is new here."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import app.scheduler as scheduler
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

    def test_skips_areas_without_active_weather_polling(self, monkeypatch, db_session):
        # ADR-019: imported gminas exist for geo-matching only; polling them all would
        # exceed the Open-Meteo daily budget.
        _make_area(db_session, "klodzko")
        inactive = _make_area(db_session, "teryt-0208023")
        inactive.weather_polling_active = False
        db_session.commit()
        monkeypatch.setattr(scheduler, "SessionLocal", lambda: db_session)
        mock = MagicMock()
        monkeypatch.setattr(scheduler, "ingest_geo_area", mock)

        scheduler.run_open_meteo()

        assert [c.args[0].slug for c in mock.call_args_list] == ["klodzko"]


class TestRunGios:
    def test_skips_when_no_station_ids_configured(self, monkeypatch):
        monkeypatch.delenv("GIOS_STATION_IDS", raising=False)
        find_stations_mock = MagicMock()
        monkeypatch.setattr(scheduler.gios_client, "find_stations", find_stations_mock)

        scheduler.run_gios()

        find_stations_mock.assert_not_called()

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
        ingest_mock.assert_called_once_with(station, db_session)


class TestRunImgwHydro:
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
            "run_gios": MagicMock(),
            "run_imgw_hydro": MagicMock(),
            "run_imgw_warningshydro": MagicMock(),
            "run_raw_retention": MagicMock(),
        }
        for name, mock in mocks.items():
            monkeypatch.setattr(scheduler, name, mock)
        monkeypatch.setattr(scheduler.time, "sleep", MagicMock())
        monkeypatch.setattr(scheduler, "_record_run", MagicMock())
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
