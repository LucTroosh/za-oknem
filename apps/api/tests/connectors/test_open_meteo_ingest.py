"""Tests for ingest.py: store/skip/failure-isolation, using the SQLite db_session
fixture (plain ORM queries here, no Postgres-specific SQL — unlike air.py)."""

import sys
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from app.connectors.open_meteo import client, ingest
from app.connectors.open_meteo.parser import FORECAST_PARAM_CODES, PARAM_CODES
from app.models import Forecast, GeoArea, SourceFetchCounter, WeatherSnapshot

CURRENT_BLOCK = {
    "current": {
        "time": "2026-09-28T18:00",
        "temperature_2m": 12.3,
        "relative_humidity_2m": 80,
        "apparent_temperature": 10.1,
        "pressure_msl": 1013.2,
        "cloud_cover": 75,
        "precipitation": 0.2,
        "rain": 0.2,
        "snowfall": 0.0,
        "wind_speed_10m": 5.2,
        "wind_direction_10m": 210,
        "wind_gusts_10m": 9.4,
        "weather_code": 3,
    },
    "current_units": {
        "temperature_2m": "°C",
        "relative_humidity_2m": "%",
        "apparent_temperature": "°C",
        "pressure_msl": "hPa",
        "cloud_cover": "%",
        "precipitation": "mm",
        "rain": "mm",
        "snowfall": "cm",
        "wind_speed_10m": "km/h",
        "wind_direction_10m": "°",
        "wind_gusts_10m": "km/h",
        "weather_code": "wmo code",
    },
}
DAILY_BLOCK = {
    "daily": {
        "time": ["2026-09-28", "2026-09-29"],
        "temperature_2m_max": [18.5, 19.1],
        "temperature_2m_min": [9.2, 8.7],
        "precipitation_sum": [0.0, 1.2],
        "weather_code": [1, 61],
    },
    "daily_units": {
        "temperature_2m_max": "°C",
        "temperature_2m_min": "°C",
        "precipitation_sum": "mm",
        "weather_code": "wmo code",
    },
}
PAYLOAD = {**CURRENT_BLOCK, **DAILY_BLOCK}
PARAM_COUNT = len(PARAM_CODES)
FORECAST_COUNT = len(FORECAST_PARAM_CODES) * 2  # 2 days in DAILY_BLOCK


def _make_area(db) -> GeoArea:
    area = GeoArea(slug="klodzko", name="Kłodzko", latitude=50.43, longitude=16.65)
    db.add(area)
    db.commit()
    db.refresh(area)
    return area


def test_ingest_geo_area_stores_current_and_forecast(db_session, monkeypatch):
    area = _make_area(db_session)
    monkeypatch.setattr(client, "fetch_weather", MagicMock(return_value=PAYLOAD))

    stored = ingest.ingest_geo_area(area, db_session)

    assert stored == PARAM_COUNT + FORECAST_COUNT
    assert db_session.query(WeatherSnapshot).count() == PARAM_COUNT
    assert db_session.query(Forecast).count() == FORECAST_COUNT


def test_ingest_geo_area_skips_duplicate(db_session, monkeypatch):
    area = _make_area(db_session)
    monkeypatch.setattr(client, "fetch_weather", MagicMock(return_value=PAYLOAD))

    ingest.ingest_geo_area(area, db_session)
    stored_again = ingest.ingest_geo_area(area, db_session)

    assert stored_again == 0
    assert db_session.query(WeatherSnapshot).count() == PARAM_COUNT
    assert db_session.query(Forecast).count() == FORECAST_COUNT


def test_ingest_geo_area_isolates_api_failure(db_session, monkeypatch):
    area = _make_area(db_session)
    monkeypatch.setattr(
        client, "fetch_weather", MagicMock(side_effect=client.OpenMeteoApiError("boom"))
    )

    stored = ingest.ingest_geo_area(area, db_session)

    assert stored == 0
    assert db_session.query(WeatherSnapshot).count() == 0
    assert db_session.query(Forecast).count() == 0


def test_ingest_geo_area_isolates_parse_failure(db_session, monkeypatch):
    area = _make_area(db_session)
    monkeypatch.setattr(client, "fetch_weather", MagicMock(return_value={"bad": "shape"}))

    stored = ingest.ingest_geo_area(area, db_session)

    assert stored == 0
    assert db_session.query(WeatherSnapshot).count() == 0
    assert db_session.query(Forecast).count() == 0


def test_ingest_geo_area_stores_forecast_even_when_current_block_is_broken(db_session, monkeypatch):
    """ADR-010: current and forecast parsing are isolated - a broken `current`
    block must not cost us an otherwise-valid `daily` forecast."""
    area = _make_area(db_session)
    broken = {"current": {"bad": "shape"}, **DAILY_BLOCK}
    monkeypatch.setattr(client, "fetch_weather", MagicMock(return_value=broken))

    stored = ingest.ingest_geo_area(area, db_session)

    assert stored == FORECAST_COUNT
    assert db_session.query(WeatherSnapshot).count() == 0
    assert db_session.query(Forecast).count() == FORECAST_COUNT


def test_ingest_geo_area_stores_current_even_when_daily_block_is_broken(db_session, monkeypatch):
    area = _make_area(db_session)
    broken = {**CURRENT_BLOCK, "daily": {"bad": "shape"}}
    monkeypatch.setattr(client, "fetch_weather", MagicMock(return_value=broken))

    stored = ingest.ingest_geo_area(area, db_session)

    assert stored == PARAM_COUNT
    assert db_session.query(WeatherSnapshot).count() == PARAM_COUNT
    assert db_session.query(Forecast).count() == 0


def test_ingest_geo_area_commits_forecast_batch_atomically(db_session, monkeypatch):
    """Codex finding on PR #46: forecast rows for all days/params of one fetch
    must land in a single commit, not one commit per row - otherwise an
    interruption mid-batch could leave /weather/forecast combining one day's
    fresh reference_time with another's stale one."""
    area = _make_area(db_session)
    monkeypatch.setattr(client, "fetch_weather", MagicMock(return_value=PAYLOAD))
    commit_calls = []
    real_commit = db_session.commit

    def _counting_commit():
        commit_calls.append(1)
        real_commit()

    monkeypatch.setattr(db_session, "commit", _counting_commit)

    ingest.ingest_geo_area(area, db_session)

    # 1 commit for the forecast batch + PARAM_COUNT commits for current-weather
    # snapshots (those stay one-per-row, per Codex's explicit request).
    assert len(commit_calls) == PARAM_COUNT + 1
    assert db_session.query(Forecast).count() == FORECAST_COUNT


def test_ingest_geo_area_fetched_at_is_recent(db_session, monkeypatch):
    area = _make_area(db_session)
    monkeypatch.setattr(client, "fetch_weather", MagicMock(return_value=PAYLOAD))

    ingest.ingest_geo_area(area, db_session)

    row = db_session.query(WeatherSnapshot).first()
    assert (datetime.now(UTC) - row.fetched_at).total_seconds() < 5


class TestMain:
    """main(): argparse + --slug filtering wiring, using the real SQLite
    db_session so GeoArea.slug.in_() filtering is exercised for real (not a
    mocked query chain). ingest_geo_area itself is covered above."""

    def test_no_matching_geo_areas_exits_with_error(self, monkeypatch, capsys, db_session):
        monkeypatch.setattr(sys, "argv", ["ingest"])
        monkeypatch.setattr(ingest, "SessionLocal", lambda: db_session)

        with pytest.raises(SystemExit) as exc_info:
            ingest.main()

        assert exc_info.value.code == 1
        assert "No matching geo_areas found" in capsys.readouterr().err

    def test_ingests_every_area_when_no_slug_given(self, monkeypatch, db_session):
        _make_area(db_session)
        monkeypatch.setattr(sys, "argv", ["ingest"])
        monkeypatch.setattr(ingest, "SessionLocal", lambda: db_session)
        ingest_mock = MagicMock()
        monkeypatch.setattr(ingest, "ingest_geo_area", ingest_mock)

        ingest.main()

        assert ingest_mock.call_count == 1

    def test_slug_filters_to_matching_areas_only(self, monkeypatch, db_session):
        _make_area(db_session)  # slug="klodzko"
        other = GeoArea(slug="warszawa", name="Warszawa", latitude=52.23, longitude=21.01)
        db_session.add(other)
        db_session.commit()
        monkeypatch.setattr(sys, "argv", ["ingest", "--slug", "warszawa"])
        monkeypatch.setattr(ingest, "SessionLocal", lambda: db_session)
        ingest_mock = MagicMock()
        monkeypatch.setattr(ingest, "ingest_geo_area", ingest_mock)

        ingest.main()

        assert ingest_mock.call_count == 1
        assert ingest_mock.call_args[0][0].slug == "warszawa"


def test_ingest_geo_area_records_a_daily_fetch_call(db_session, monkeypatch):
    """ADR-001/ADR-003/ADR-004: a successful HTTP call counts against the source's
    daily budget, regardless of what parsing does with the payload. Fires
    on_attempt itself (mocking client.fetch_weather bypasses its real retry loop,
    which is what actually calls on_attempt) - matches one real attempt
    succeeding immediately, and bills ESTIMATED_BILLABLE_UNITS_PER_CALL, not 1."""
    area = _make_area(db_session)

    def _fake_fetch_weather(_lat, _lon, *, on_attempt=None):
        if on_attempt:
            on_attempt()
        return PAYLOAD

    monkeypatch.setattr(client, "fetch_weather", _fake_fetch_weather)

    ingest.ingest_geo_area(area, db_session)

    counter = db_session.query(SourceFetchCounter).filter_by(source_id="open_meteo").first()
    assert counter is not None
    assert counter.count == ingest.ESTIMATED_BILLABLE_UNITS_PER_CALL


def test_ingest_geo_area_records_every_attempt_even_on_final_failure(db_session, monkeypatch):
    """Codex review [P2]: the previous version recorded 0 calls when
    client.fetch_weather ultimately raised, even though its internal retry loop
    made 2 real HTTP attempts against Open-Meteo. on_attempt now fires once per
    real attempt regardless of outcome - simulated here as 2 failed attempts
    (fetch_weather's own retry count) before the final raise."""
    area = _make_area(db_session)

    def _fake_fetch_weather(_lat, _lon, *, on_attempt=None):
        if on_attempt:
            on_attempt()
            on_attempt()
        raise client.OpenMeteoApiError("boom")

    monkeypatch.setattr(client, "fetch_weather", _fake_fetch_weather)

    ingest.ingest_geo_area(area, db_session)

    counter = db_session.query(SourceFetchCounter).filter_by(source_id="open_meteo").first()
    assert counter is not None
    assert counter.count == 2 * ingest.ESTIMATED_BILLABLE_UNITS_PER_CALL
