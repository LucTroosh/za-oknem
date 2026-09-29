"""Tests for parser.py: shape validation + normalization into WeatherSnapshot /
Forecast dicts (ADR-010)."""

from datetime import UTC, datetime

import pytest

from app.connectors.open_meteo.parser import (
    FORECAST_PARAM_CODES,
    PARAM_CODES,
    OpenMeteoParseError,
    normalize,
    normalize_forecast,
)

VALID_PAYLOAD = {
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


def test_normalize_returns_one_record_per_param():
    records = normalize(geo_area_id=1, payload=VALID_PAYLOAD, fetched_at=datetime.now(UTC))
    assert len(records) == len(PARAM_CODES)
    codes = {r["param_code"] for r in records}
    assert codes == set(PARAM_CODES)


def test_normalize_sets_utc_observed_at():
    records = normalize(geo_area_id=1, payload=VALID_PAYLOAD, fetched_at=datetime.now(UTC))
    assert records[0]["observed_at"] == datetime(2026, 9, 28, 18, 0, tzinfo=UTC)


def test_normalize_builds_idempotent_source_record_id():
    records = normalize(geo_area_id=7, payload=VALID_PAYLOAD, fetched_at=datetime.now(UTC))
    temp = next(r for r in records if r["param_code"] == "temperature_2m")
    assert temp["source_record_id"] == "7:temperature_2m:2026-09-28T18:00:00+00:00"
    assert temp["source_id"] == "open_meteo"
    assert temp["geo_area_id"] == 7


def test_normalize_raises_on_missing_current_block():
    with pytest.raises(OpenMeteoParseError):
        normalize(geo_area_id=1, payload={}, fetched_at=datetime.now(UTC))


def test_normalize_raises_on_missing_param():
    bad = {
        "current": {"time": "2026-09-28T18:00", "temperature_2m": 12.3},
        "current_units": {"temperature_2m": "°C"},
    }
    with pytest.raises(OpenMeteoParseError):
        normalize(geo_area_id=1, payload=bad, fetched_at=datetime.now(UTC))


# --- normalize_forecast() (ADR-010) ------------------------------------------


def test_normalize_forecast_returns_one_record_per_param_per_day():
    records = normalize_forecast(geo_area_id=1, payload=VALID_PAYLOAD, fetched_at=datetime.now(UTC))
    assert len(records) == len(FORECAST_PARAM_CODES) * 2  # 2 days in VALID_PAYLOAD
    codes = {r["param_code"] for r in records}
    assert codes == set(FORECAST_PARAM_CODES)


def test_normalize_forecast_sets_valid_from_and_until():
    records = normalize_forecast(geo_area_id=1, payload=VALID_PAYLOAD, fetched_at=datetime.now(UTC))
    day1 = next(r for r in records if r["valid_from"] == datetime(2026, 9, 28, tzinfo=UTC))
    assert day1["valid_until"] == datetime(2026, 9, 29, tzinfo=UTC)


def test_normalize_forecast_bucket_reference_time_to_3h_cycle():
    fetched_at = datetime(2026, 9, 28, 14, 37, 12, tzinfo=UTC)  # mid-cycle, not on a 3h boundary
    records = normalize_forecast(geo_area_id=1, payload=VALID_PAYLOAD, fetched_at=fetched_at)
    assert records[0]["forecast_reference_time"] == datetime(2026, 9, 28, 12, 0, 0, tzinfo=UTC)


def test_normalize_forecast_two_fetches_in_same_cycle_get_same_source_record_id():
    """The whole point of bucketing (ADR-010): reruns within one 3h window must
    be idempotent, not produce a new row every time."""
    t1 = datetime(2026, 9, 28, 12, 1, tzinfo=UTC)
    t2 = datetime(2026, 9, 28, 14, 59, tzinfo=UTC)
    r1 = normalize_forecast(geo_area_id=1, payload=VALID_PAYLOAD, fetched_at=t1)
    r2 = normalize_forecast(geo_area_id=1, payload=VALID_PAYLOAD, fetched_at=t2)
    assert {r["source_record_id"] for r in r1} == {r["source_record_id"] for r in r2}


def test_normalize_forecast_different_cycles_get_different_source_record_id():
    t1 = datetime(2026, 9, 28, 11, 59, tzinfo=UTC)
    t2 = datetime(2026, 9, 28, 12, 1, tzinfo=UTC)  # next 3h bucket
    r1 = normalize_forecast(geo_area_id=1, payload=VALID_PAYLOAD, fetched_at=t1)
    r2 = normalize_forecast(geo_area_id=1, payload=VALID_PAYLOAD, fetched_at=t2)
    assert {r["source_record_id"] for r in r1}.isdisjoint({r["source_record_id"] for r in r2})


def test_normalize_forecast_model_is_open_meteo_default():
    records = normalize_forecast(geo_area_id=1, payload=VALID_PAYLOAD, fetched_at=datetime.now(UTC))
    assert records[0]["model"] == "auto"


def test_normalize_forecast_raises_on_missing_daily_block():
    with pytest.raises(OpenMeteoParseError):
        normalize_forecast(geo_area_id=1, payload={}, fetched_at=datetime.now(UTC))


def test_normalize_forecast_raises_on_malformed_date():
    bad = {
        "daily": {"time": ["not-a-date"], "temperature_2m_max": [18.5]},
        "daily_units": {"temperature_2m_max": "°C"},
    }
    with pytest.raises(OpenMeteoParseError):
        normalize_forecast(geo_area_id=1, payload=bad, fetched_at=datetime.now(UTC))


def test_normalize_forecast_raises_on_missing_param_for_a_day():
    bad = {
        "daily": {"time": ["2026-09-28"], "temperature_2m_max": [18.5]},  # missing other params
        "daily_units": {"temperature_2m_max": "°C"},
    }
    with pytest.raises(OpenMeteoParseError):
        normalize_forecast(geo_area_id=1, payload=bad, fetched_at=datetime.now(UTC))


def test_normalize_forecast_does_not_fail_when_current_block_is_absent():
    """normalize_forecast() only needs `daily`/`daily_units` - a payload that has
    a broken `current` block but a valid `daily` block must still parse
    (ADR-010: current and forecast failures are isolated from each other)."""
    payload = {k: v for k, v in VALID_PAYLOAD.items() if not k.startswith("current")}
    records = normalize_forecast(geo_area_id=1, payload=payload, fetched_at=datetime.now(UTC))
    assert len(records) == len(FORECAST_PARAM_CODES) * 2
