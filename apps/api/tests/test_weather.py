"""Tests for GET /api/v1/weather/latest: freshness thresholds and response shaping.

Same fake-session approach as test_air.py (Postgres DISTINCT ON, SQLite can't
compile it) — but this endpoint issues two execute() calls (snapshots, then
geo_areas), so the fake session returns queued results in call order.
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.v1.weather import (
    FRESH_MAX_AGE,
    RECENT_MAX_AGE,
    WeatherForecastResponse,
    WeatherLatestResponse,
    freshness,
)
from app.db import get_db
from app.main import app
from app.models import Forecast, GeoArea, WeatherSnapshot


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, *result_sets):
        self._queue = list(result_sets)

    def execute(self, _stmt):
        return _FakeResult(self._queue.pop(0))


def _client(snapshot_rows: list[WeatherSnapshot], geo_areas: list[GeoArea]) -> TestClient:
    def _override():
        yield _FakeSession(snapshot_rows, geo_areas)

    app.dependency_overrides[get_db] = _override
    return TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.pop(get_db, None)


def _area(**overrides) -> GeoArea:
    defaults = {
        "id": 1,
        "slug": "klodzko",
        "name": "Kłodzko",
        "latitude": 50.43,
        "longitude": 16.65,
    }
    defaults.update(overrides)
    return GeoArea(**defaults)


def _snapshot(**overrides) -> WeatherSnapshot:
    defaults = {
        "source_id": "open_meteo",
        "source_record_id": "rec-1",
        "geo_area_id": 1,
        "param_code": "temperature_2m",
        "value": 12.3,
        "unit": "°C",
        "observed_at": datetime.now(UTC),
        "fetched_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return WeatherSnapshot(**defaults)


# --- freshness() thresholds --------------------------------------------------


def test_freshness_within_fresh_threshold():
    assert freshness(datetime.now(UTC) - (FRESH_MAX_AGE - timedelta(minutes=1))) == "FRESH"


def test_freshness_just_past_fresh_threshold_is_recent():
    assert freshness(datetime.now(UTC) - (FRESH_MAX_AGE + timedelta(minutes=1))) == "RECENT"


def test_freshness_just_past_recent_threshold_is_stale():
    assert freshness(datetime.now(UTC) - (RECENT_MAX_AGE + timedelta(minutes=1))) == "STALE"


# --- GET /api/v1/weather/latest ----------------------------------------------


def test_latest_weather_returns_empty_list_when_no_rows():
    client = _client([], [])

    response = client.get("/api/v1/weather/latest")

    assert response.status_code == 200
    assert response.json() == {"areas": []}


def test_latest_weather_groups_params_by_geo_area():
    now = datetime.now(UTC)
    rows = [
        _snapshot(param_code="temperature_2m", value=12.3, unit="°C", observed_at=now),
        _snapshot(param_code="wind_speed_10m", value=5.2, unit="km/h", observed_at=now),
    ]
    client = _client(rows, [_area()])

    body = client.get("/api/v1/weather/latest").json()

    assert body == {
        "areas": [
            {
                "geo_area_id": 1,
                "slug": "klodzko",
                "name": "Kłodzko",
                "latitude": 50.43,
                "longitude": 16.65,
                "observed_at": now.isoformat(),
                "freshness": "FRESH",
                "params": {
                    "temperature_2m": {
                        "value": 12.3,
                        "unit": "°C",
                        "observed_at": now.isoformat(),
                        "freshness": "FRESH",
                    },
                    "wind_speed_10m": {
                        "value": 5.2,
                        "unit": "km/h",
                        "observed_at": now.isoformat(),
                        "freshness": "FRESH",
                    },
                },
                "source": "open_meteo",
            }
        ]
    }


def test_latest_weather_reports_per_param_freshness_independently():
    # Codex review (cross-referenced from PR#50): a fresh param and a stale one for
    # the same area must not both inherit the object-level max(observed_at) status.
    fresh_row = _snapshot(
        param_code="temperature_2m", observed_at=datetime.now(UTC), source_record_id="fresh"
    )
    stale_row = _snapshot(
        param_code="uv_index",
        observed_at=datetime.now(UTC) - timedelta(hours=10),
        source_record_id="stale",
    )
    client = _client([fresh_row, stale_row], [_area()])

    body = client.get("/api/v1/weather/latest").json()

    params = body["areas"][0]["params"]
    assert params["temperature_2m"]["freshness"] == "FRESH"
    assert params["uv_index"]["freshness"] == "STALE"
    assert body["areas"][0]["freshness"] == "FRESH"


def test_latest_weather_marks_old_reading_stale():
    row = _snapshot(observed_at=datetime.now(UTC) - timedelta(hours=10))
    client = _client([row], [_area()])

    body = client.get("/api/v1/weather/latest").json()

    assert body["areas"][0]["freshness"] == "STALE"


def test_latest_weather_skips_snapshot_for_deleted_geo_area():
    row = _snapshot(geo_area_id=999)
    client = _client([row], [_area()])  # area id=1, snapshot references id=999

    body = client.get("/api/v1/weather/latest").json()

    assert body == {"areas": []}


def test_latest_weather_handles_multiple_areas():
    rows = [
        _snapshot(geo_area_id=1, source_record_id="a"),
        _snapshot(geo_area_id=2, source_record_id="b"),
    ]
    areas = [_area(id=1, slug="klodzko"), _area(id=2, slug="warszawa", name="Warszawa")]
    client = _client(rows, areas)

    body = client.get("/api/v1/weather/latest").json()

    assert {a["slug"] for a in body["areas"]} == {"klodzko", "warszawa"}


# --- GET /api/v1/weather/forecast (ADR-010) ----------------------------------


def _forecast(**overrides) -> Forecast:
    now = datetime.now(UTC)
    valid_from = overrides.get("valid_from", now.replace(hour=0, minute=0, second=0, microsecond=0))
    defaults = {
        "source_id": "open_meteo",
        "source_record_id": "rec-1",
        "geo_area_id": 1,
        "param_code": "temperature_2m_max",
        "value": 18.5,
        "unit": "°C",
        "model": "auto",
        "forecast_reference_time": now,
        "valid_from": valid_from,
        "valid_until": valid_from + timedelta(days=1),  # overridden below if caller passed one
        "fetched_at": now,
    }
    defaults.update(overrides)
    return Forecast(**defaults)


def test_weather_forecast_returns_empty_list_when_no_rows():
    client = _client([], [])

    response = client.get("/api/v1/weather/forecast")

    assert response.status_code == 200
    assert response.json() == {"areas": []}


def test_weather_forecast_groups_by_area_and_day():
    day1 = datetime(2026, 9, 29, tzinfo=UTC)
    day2 = datetime(2026, 9, 30, tzinfo=UTC)
    rows = [
        _forecast(param_code="temperature_2m_max", value=18.5, valid_from=day1),
        _forecast(param_code="temperature_2m_min", value=9.2, valid_from=day1),
        _forecast(param_code="temperature_2m_max", value=19.1, valid_from=day2),
    ]
    client = _client(rows, [_area()])

    body = client.get("/api/v1/weather/forecast").json()

    assert len(body["areas"]) == 1
    area = body["areas"][0]
    assert area["slug"] == "klodzko"
    assert area["model"] == "auto"
    assert len(area["days"]) == 2
    assert area["days"][0]["valid_from"] == day1.isoformat()
    assert area["days"][0]["params"] == {
        "temperature_2m_max": {"value": 18.5, "unit": "°C"},
        "temperature_2m_min": {"value": 9.2, "unit": "°C"},
    }
    assert area["days"][1]["params"] == {"temperature_2m_max": {"value": 19.1, "unit": "°C"}}


def test_weather_forecast_reports_freshness_from_fetched_at():
    row = _forecast(fetched_at=datetime.now(UTC))
    client = _client([row], [_area()])

    area = client.get("/api/v1/weather/forecast").json()["areas"][0]

    assert area["freshness"] == "FRESH"
    assert area["fetched_at"] == row.fetched_at.isoformat()


def test_weather_forecast_marks_stale_when_fetched_at_old():
    row = _forecast(fetched_at=datetime.now(UTC) - timedelta(hours=10))
    client = _client([row], [_area()])

    area = client.get("/api/v1/weather/forecast").json()["areas"][0]

    assert area["freshness"] == "STALE"


def test_weather_forecast_freshness_uses_fetched_at_not_bucketed_reference_time():
    """ADR-010 buckets forecast_reference_time down to the 3h cycle start, so a
    fetch at 14:59 stores forecast_reference_time=12:00 — up to ~3h "older"
    than the real fetch. Freshness must be based on the real fetched_at, not
    that bucketed value, or a just-fetched forecast could read as RECENT/STALE."""
    row = _forecast(
        fetched_at=datetime.now(UTC),
        forecast_reference_time=datetime.now(UTC) - timedelta(hours=2, minutes=59),
    )
    client = _client([row], [_area()])

    area = client.get("/api/v1/weather/forecast").json()["areas"][0]

    assert area["freshness"] == "FRESH"


def test_weather_forecast_skips_row_for_deleted_geo_area():
    row = _forecast(geo_area_id=999)
    client = _client([row], [_area()])  # area id=1, forecast references id=999

    body = client.get("/api/v1/weather/forecast").json()

    assert body == {"areas": []}


def test_weather_forecast_days_are_sorted_ascending():
    day1 = datetime(2026, 9, 29, tzinfo=UTC)
    day2 = datetime(2026, 9, 30, tzinfo=UTC)
    day3 = datetime(2026, 10, 1, tzinfo=UTC)
    # Deliberately out of order - the endpoint must sort, not trust query order.
    rows = [
        _forecast(valid_from=day3),
        _forecast(valid_from=day1),
        _forecast(valid_from=day2),
    ]
    client = _client(rows, [_area()])

    body = client.get("/api/v1/weather/forecast").json()

    valid_froms = [d["valid_from"] for d in body["areas"][0]["days"]]
    assert valid_froms == [day1.isoformat(), day2.isoformat(), day3.isoformat()]


# --- response models (TASK-API-2: response_model actually enforces a shape) ---


def test_weather_latest_response_rejects_missing_required_field():
    with pytest.raises(ValidationError):
        WeatherLatestResponse.model_validate(
            {
                "areas": [
                    {
                        "geo_area_id": 1,
                        "slug": "klodzko",
                        # name missing
                        "latitude": 50.43,
                        "longitude": 16.65,
                        "observed_at": "2026-09-29T12:00:00+00:00",
                        "freshness": "FRESH",
                        "params": {},
                        "source": "open_meteo",
                    }
                ]
            }
        )


def test_weather_latest_response_rejects_unknown_source():
    with pytest.raises(ValidationError):
        WeatherLatestResponse.model_validate(
            {
                "areas": [
                    {
                        "geo_area_id": 1,
                        "slug": "klodzko",
                        "name": "Kłodzko",
                        "latitude": 50.43,
                        "longitude": 16.65,
                        "observed_at": "2026-09-29T12:00:00+00:00",
                        "freshness": "FRESH",
                        "params": {},
                        "source": "not_open_meteo",
                    }
                ]
            }
        )


def test_weather_forecast_response_rejects_missing_required_field():
    with pytest.raises(ValidationError):
        WeatherForecastResponse.model_validate(
            {
                "areas": [
                    {
                        "geo_area_id": 1,
                        "slug": "klodzko",
                        "name": "Kłodzko",
                        "latitude": 50.43,
                        "longitude": 16.65,
                        "model": "auto",
                        "fetched_at": "2026-09-29T12:00:00+00:00",
                        "freshness": "FRESH",
                        # days missing
                        "source": "open_meteo",
                    }
                ]
            }
        )
