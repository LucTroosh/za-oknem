"""Tests for parser.py: shape validation + normalization into WeatherSnapshot dicts."""

from datetime import UTC, datetime

import pytest

from app.connectors.open_meteo.parser import PARAM_CODES, OpenMeteoParseError, normalize

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
