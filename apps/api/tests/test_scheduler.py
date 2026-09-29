"""Tests for the loop-based scheduler (ADR-007): interval gating and the
explicit opt-in for GIOS_STATION_IDS. ingest_* themselves are already covered
by the connectors' own ingest tests - only the scheduling wiring is new here."""

from unittest.mock import MagicMock

import app.scheduler as scheduler
from app.models import GeoArea


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


class TestMain:
    def test_first_iteration_runs_both_jobs(self, monkeypatch):
        open_meteo_mock = MagicMock()
        gios_mock = MagicMock()
        monkeypatch.setattr(scheduler, "run_open_meteo", open_meteo_mock)
        monkeypatch.setattr(scheduler, "run_gios", gios_mock)
        monkeypatch.setattr(scheduler.time, "sleep", MagicMock())

        scheduler.main(iterations=1)

        open_meteo_mock.assert_called_once()
        gios_mock.assert_called_once()

    def test_second_iteration_skips_jobs_before_interval_elapses(self, monkeypatch):
        open_meteo_mock = MagicMock()
        gios_mock = MagicMock()
        monkeypatch.setattr(scheduler, "run_open_meteo", open_meteo_mock)
        monkeypatch.setattr(scheduler, "run_gios", gios_mock)
        monkeypatch.setattr(scheduler.time, "sleep", MagicMock())
        # Same monotonic value every call - no interval has elapsed since "last".
        monkeypatch.setattr(scheduler.time, "monotonic", lambda: 1000.0)

        scheduler.main(iterations=2)

        open_meteo_mock.assert_called_once()
        gios_mock.assert_called_once()

    def test_third_iteration_reruns_gios_after_its_interval(self, monkeypatch):
        gios_mock = MagicMock()
        monkeypatch.setattr(scheduler, "run_open_meteo", MagicMock())
        monkeypatch.setattr(scheduler, "run_gios", gios_mock)
        monkeypatch.setattr(scheduler.time, "sleep", MagicMock())
        # 0s, then just past the 1h GIOS interval - open_meteo's 3h interval hasn't
        # elapsed yet, so this isolates the per-job gating (not just "run again").
        ticks = iter([0.0, scheduler.GIOS_INTERVAL_SECONDS + 1])
        monkeypatch.setattr(scheduler.time, "monotonic", lambda: next(ticks))

        scheduler.main(iterations=2)

        assert gios_mock.call_count == 2
