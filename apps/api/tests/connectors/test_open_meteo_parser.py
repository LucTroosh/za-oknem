"""Tests for parser.py: shape validation + normalization into WeatherSnapshot /
Forecast dicts (ADR-010)."""

import math
from datetime import UTC, datetime, timedelta

import pytest

from app.connectors.open_meteo.parser import (
    FORECAST_PARAM_CODES,
    HOURLY_FORECAST_PARAM_CODES,
    HOURLY_PARAM_CODES,
    OPTIONAL_FORECAST_PARAM_CODES,
    PARAM_CODES,
    OpenMeteoParseError,
    normalize,
    normalize_forecast,
    normalize_hourly_current,
    normalize_hourly_forecast,
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
    "hourly": {
        "time": ["2026-09-28T17:00", "2026-09-28T18:00", "2026-09-28T19:00"],
        "dew_point_2m": [8.1, 8.4, 8.6],
        "visibility": [24140.0, 22000.0, 20500.0],
        "uv_index": [0.0, 0.2, 0.1],
    },
    "hourly_units": {
        "dew_point_2m": "°C",
        "visibility": "m",
        "uv_index": "",
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


# --- normalize_hourly_current() (TASK-5.4) -----------------------------------


def test_normalize_hourly_current_returns_one_record_per_param():
    records = normalize_hourly_current(
        geo_area_id=1, payload=VALID_PAYLOAD, fetched_at=datetime.now(UTC)
    )
    assert len(records) == len(HOURLY_PARAM_CODES)
    assert {r["param_code"] for r in records} == set(HOURLY_PARAM_CODES)


def test_normalize_hourly_current_picks_the_matching_hour():
    records = normalize_hourly_current(
        geo_area_id=1, payload=VALID_PAYLOAD, fetched_at=datetime.now(UTC)
    )
    dew_point = next(r for r in records if r["param_code"] == "dew_point_2m")
    # index 1 in VALID_PAYLOAD's hourly arrays (17:00, [18:00], 19:00), not the
    # neighboring hours - proves it doesn't just take hourly[0].
    assert dew_point["value"] == 8.4
    assert dew_point["observed_at"] == datetime(2026, 9, 28, 18, 0, tzinfo=UTC)


def test_normalize_hourly_current_floors_current_time_to_the_hour():
    """`current.time` can be a few minutes into the hour (Open-Meteo's current
    conditions aren't always on the hour); the hourly slot it maps to must still
    be the hour it falls in, not fail to match."""
    payload = {**VALID_PAYLOAD, "current": {**VALID_PAYLOAD["current"], "time": "2026-09-28T18:47"}}
    records = normalize_hourly_current(geo_area_id=1, payload=payload, fetched_at=datetime.now(UTC))
    dew_point = next(r for r in records if r["param_code"] == "dew_point_2m")
    assert dew_point["value"] == 8.4
    assert dew_point["observed_at"] == datetime(2026, 9, 28, 18, 0, tzinfo=UTC)


def test_normalize_hourly_current_builds_idempotent_source_record_id():
    records = normalize_hourly_current(
        geo_area_id=7, payload=VALID_PAYLOAD, fetched_at=datetime.now(UTC)
    )
    dew_point = next(r for r in records if r["param_code"] == "dew_point_2m")
    assert dew_point["source_record_id"] == "7:dew_point_2m:2026-09-28T18:00:00+00:00"
    assert dew_point["source_id"] == "open_meteo"


def test_normalize_hourly_current_raises_on_missing_hourly_block():
    payload = {k: v for k, v in VALID_PAYLOAD.items() if not k.startswith("hourly")}
    with pytest.raises(OpenMeteoParseError):
        normalize_hourly_current(geo_area_id=1, payload=payload, fetched_at=datetime.now(UTC))


def test_normalize_hourly_current_raises_when_current_hour_not_in_hourly_time():
    payload = {
        **VALID_PAYLOAD,
        "current": {**VALID_PAYLOAD["current"], "time": "2026-09-29T03:00"},
    }
    with pytest.raises(OpenMeteoParseError):
        normalize_hourly_current(geo_area_id=1, payload=payload, fetched_at=datetime.now(UTC))


def test_normalize_hourly_current_raises_on_missing_param():
    bad = {
        "current": VALID_PAYLOAD["current"],
        "hourly": {"time": ["2026-09-28T18:00"]},
        "hourly_units": {},
    }
    with pytest.raises(OpenMeteoParseError):
        normalize_hourly_current(geo_area_id=1, payload=bad, fetched_at=datetime.now(UTC))


def test_normalize_hourly_current_does_not_need_daily_block():
    """Isolated from normalize_forecast() (rule #1, TASK-5.4) - a payload with a
    broken `daily` block but valid `current`/`hourly` must still parse."""
    payload = {k: v for k, v in VALID_PAYLOAD.items() if not k.startswith("daily")}
    records = normalize_hourly_current(geo_area_id=1, payload=payload, fetched_at=datetime.now(UTC))
    assert len(records) == len(HOURLY_PARAM_CODES)


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


def test_normalize_forecast_raises_on_non_list_daily_time():
    """`enumerate()` on a non-iterable `daily.time` (e.g. None from a malformed
    payload) must not escape as a raw TypeError — that would bypass ingest.py's
    per-block isolation (rule #1) and abort the whole ingest run."""
    bad = {
        "daily": {"time": None, "temperature_2m_max": [18.5]},
        "daily_units": {"temperature_2m_max": "°C"},
    }
    with pytest.raises(OpenMeteoParseError):
        normalize_forecast(geo_area_id=1, payload=bad, fetched_at=datetime.now(UTC))


def test_normalize_forecast_raises_on_non_list_daily_param_value():
    """A malformed response with a string instead of an array for a daily param
    (e.g. "18.5" for a single day) would otherwise index into the string's
    characters instead of raising - must be rejected as a shape error."""
    bad = {
        "daily": {
            "time": ["2026-09-28"],
            "temperature_2m_max": "18.5",
            "temperature_2m_min": [9.2],
            "precipitation_sum": [0.0],
            "weather_code": [1],
        },
        "daily_units": {
            "temperature_2m_max": "°C",
            "temperature_2m_min": "°C",
            "precipitation_sum": "mm",
            "weather_code": "wmo code",
        },
    }
    with pytest.raises(OpenMeteoParseError):
        normalize_forecast(geo_area_id=1, payload=bad, fetched_at=datetime.now(UTC))


def test_normalize_forecast_raises_on_daily_param_length_mismatch():
    bad = {
        "daily": {
            "time": ["2026-09-28", "2026-09-29"],
            "temperature_2m_max": [18.5],  # only 1 value for 2 days
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
    with pytest.raises(OpenMeteoParseError):
        normalize_forecast(geo_area_id=1, payload=bad, fetched_at=datetime.now(UTC))


def test_normalize_forecast_does_not_fail_when_current_block_is_absent():
    """normalize_forecast() only needs `daily`/`daily_units` - a payload that has
    a broken `current` block but a valid `daily` block must still parse
    (ADR-010: current and forecast failures are isolated from each other)."""
    payload = {k: v for k, v in VALID_PAYLOAD.items() if not k.startswith("current")}
    records = normalize_forecast(geo_area_id=1, payload=payload, fetched_at=datetime.now(UTC))
    assert len(records) == len(FORECAST_PARAM_CODES) * 2


# --- ADR-030: optional daily params + hourly forecast ----------------------------------

FETCHED = datetime(2026, 9, 28, 18, 20, tzinfo=UTC)  # same hour as VALID_PAYLOAD["current"]
HOURLY_UNITS = {
    "temperature_2m": "°C",
    "apparent_temperature": "°C",
    "precipitation": "mm",
    "precipitation_probability": "%",
    "wind_speed_10m": "km/h",
    "wind_gusts_10m": "km/h",
    "uv_index": "",
    "weather_code": "wmo code",
    "visibility": "m",
}


def _hourly_payload(hours: int = 72, start: str = "2026-09-28T00:00", **overrides) -> dict:
    """`hours` hourly values per forecast param starting at `start` (whole days, like the
    real request); `current` is 2026-09-28T18:00."""
    first = datetime.fromisoformat(start)
    times = [(first + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(hours)]
    series = {code: [float(i) for i in range(hours)] for code in HOURLY_FORECAST_PARAM_CODES}
    series.update(overrides)
    return {
        "current": VALID_PAYLOAD["current"],
        "hourly": {"time": times, **series},
        "hourly_units": dict(HOURLY_UNITS),
    }


def _hourly(payload: dict, **kwargs) -> list[dict]:
    return normalize_hourly_forecast(geo_area_id=3, payload=payload, fetched_at=FETCHED, **kwargs)


def test_hourly_forecast_window_is_48_hours_from_the_current_hour():
    records = _hourly(_hourly_payload())
    starts = sorted({r["valid_from"] for r in records})
    assert len(starts) == 48
    assert starts[0] == datetime(2026, 9, 28, 18, 0, tzinfo=UTC)  # the earlier hours are gone
    assert starts[-1] == datetime(2026, 9, 30, 17, 0, tzinfo=UTC)
    assert len(records) == 48 * len(HOURLY_FORECAST_PARAM_CODES)


def test_hourly_forecast_record_shape_and_idempotent_ids():
    records = _hourly(_hourly_payload())
    wind = next(r for r in records if r["param_code"] == "wind_gusts_10m")
    assert wind["granularity"] == "hourly"
    assert wind["valid_until"] - wind["valid_from"] == timedelta(hours=1)
    assert wind["unit"] == "km/h" and wind["model"] == "auto" and wind["geo_area_id"] == 3
    assert wind["forecast_reference_time"] == datetime(2026, 9, 28, 18, 0, tzinfo=UTC)
    assert wind["fetched_at"] == FETCHED
    # Same run twice -> same ids; and never equal to a daily id (weather_code at 00:00).
    again = _hourly(_hourly_payload())
    assert [r["source_record_id"] for r in records] == [r["source_record_id"] for r in again]
    assert len({r["source_record_id"] for r in records}) == len(records)
    assert all(r["source_record_id"].startswith("hourly:3:") for r in records)


def test_hourly_forecast_id_cannot_collide_with_a_daily_id():
    payload = {**VALID_PAYLOAD, **_hourly_payload(start="2026-09-28T00:00")}
    daily = {
        r["source_record_id"]
        for r in normalize_forecast(geo_area_id=3, payload=payload, fetched_at=FETCHED)
    }
    hourly = {r["source_record_id"] for r in _hourly(payload)}
    assert daily.isdisjoint(hourly)


def test_hourly_forecast_a_null_hour_costs_only_that_value():
    precip = [float(i) for i in range(72)]
    precip[20] = None  # 2026-09-28T20:00
    records = _hourly(_hourly_payload(precipitation_probability=precip))
    by_param = {}
    for r in records:
        by_param.setdefault(r["param_code"], []).append(r["valid_from"])
    assert len(by_param["precipitation_probability"]) == 47
    assert datetime(2026, 9, 28, 20, 0, tzinfo=UTC) not in by_param["precipitation_probability"]
    assert len(by_param["temperature_2m"]) == 48  # other params untouched


def test_hourly_forecast_nan_bool_and_string_values_are_skipped():
    values = [float(i) for i in range(72)]
    values[18], values[19], values[20] = math.nan, True, "12"
    records = _hourly(_hourly_payload(temperature_2m=values))
    temps = [r for r in records if r["param_code"] == "temperature_2m"]
    assert len(temps) == 45


def test_hourly_forecast_missing_series_or_unit_skips_only_that_param():
    payload = _hourly_payload()
    del payload["hourly"]["precipitation_probability"]  # e.g. the model has no probability
    del payload["hourly_units"]["visibility"]
    codes = {r["param_code"] for r in _hourly(payload)}
    assert codes == set(HOURLY_FORECAST_PARAM_CODES) - {"precipitation_probability", "visibility"}


def test_hourly_forecast_length_mismatch_skips_that_param():
    payload = _hourly_payload(temperature_2m=[1.0, 2.0])  # cannot be aligned with `time`
    assert "temperature_2m" not in {r["param_code"] for r in _hourly(payload)}


def test_hourly_forecast_bad_time_entry_skips_that_hour_only():
    payload = _hourly_payload()
    payload["hourly"]["time"][25] = "not-a-time"  # 2026-09-29T01:00
    starts = {r["valid_from"] for r in _hourly(payload)}
    assert len(starts) == 47 and datetime(2026, 9, 29, 1, 0, tzinfo=UTC) not in starts


def test_hourly_forecast_raises_on_malformed_block_or_nothing_usable():
    for bad in (
        {},
        {"hourly": {"time": "x"}, "hourly_units": {}},
        {"hourly": {}, "hourly_units": {}},
    ):
        with pytest.raises(OpenMeteoParseError):
            _hourly(bad)
    all_null = _hourly_payload(**{c: [None] * 72 for c in HOURLY_FORECAST_PARAM_CODES})
    with pytest.raises(OpenMeteoParseError):
        _hourly(all_null)
    past_only = _hourly_payload(hours=10)  # 00:00-09:00, window starts at 18:00
    with pytest.raises(OpenMeteoParseError):
        _hourly(past_only)


def test_hourly_forecast_without_current_block_falls_back_to_fetch_time():
    payload = {k: v for k, v in _hourly_payload().items() if k != "current"}
    starts = sorted({r["valid_from"] for r in _hourly(payload)})
    assert starts[0] == datetime(2026, 9, 28, 18, 0, tzinfo=UTC)  # floor(FETCHED)


def test_hourly_forecast_needs_neither_current_values_nor_daily_block():
    payload = _hourly_payload()
    payload["current"] = {"time": "2026-09-28T18:00"}  # no values at all
    assert _hourly(payload)


def _daily_with_optional(prob, uv_max) -> dict:
    payload = {**VALID_PAYLOAD}
    payload["daily"] = {
        **VALID_PAYLOAD["daily"],
        "precipitation_probability_max": prob,
        "uv_index_max": uv_max,
    }
    payload["daily_units"] = {
        **VALID_PAYLOAD["daily_units"],
        "precipitation_probability_max": "%",
        "uv_index_max": "",
    }
    return payload


def test_daily_optional_params_are_stored_when_present():
    payload = _daily_with_optional([80, 10], [4.5, 3.0])
    records = normalize_forecast(geo_area_id=1, payload=payload, fetched_at=FETCHED)
    assert len(records) == (len(FORECAST_PARAM_CODES) + len(OPTIONAL_FORECAST_PARAM_CODES)) * 2
    prob = [r for r in records if r["param_code"] == "precipitation_probability_max"]
    assert [(r["value"], r["unit"]) for r in prob] == [(80.0, "%"), (10.0, "%")]
    assert all("granularity" not in r for r in records)  # daily = the column default


def test_daily_optional_null_or_absent_never_fails_the_core_params():
    # null for a day, whole series absent, and a unit missing: only the optional value is lost
    payload = _daily_with_optional([None, 10], [4.5, 3.0])
    del payload["daily_units"]["uv_index_max"]
    records = normalize_forecast(geo_area_id=1, payload=payload, fetched_at=FETCHED)
    optional = [r for r in records if r["param_code"] in OPTIONAL_FORECAST_PARAM_CODES]
    assert [(r["param_code"], r["value"]) for r in optional] == [
        ("precipitation_probability_max", 10.0)
    ]
    assert len([r for r in records if r["param_code"] in FORECAST_PARAM_CODES]) == 4 * 2
    # payload from before ADR-030 (no optional keys at all) still parses
    assert len(normalize_forecast(geo_area_id=1, payload=VALID_PAYLOAD, fetched_at=FETCHED)) == 8


def test_daily_core_params_stay_strict():
    payload = _daily_with_optional([80, 10], [4.5, 3.0])
    payload["daily"]["temperature_2m_max"] = [18.5, None]
    with pytest.raises(OpenMeteoParseError):
        normalize_forecast(geo_area_id=1, payload=payload, fetched_at=FETCHED)


def test_hourly_forecast_window_cuts_exactly_48_hours_from_a_7_day_response():
    # forecast_days=7 -> 168 hourly values per param from midnight (the real request)
    records = _hourly(_hourly_payload(hours=168))
    starts = sorted({r["valid_from"] for r in records})
    assert len(starts) == 48
    assert starts[0] == datetime(2026, 9, 28, 18, 0, tzinfo=UTC)
    assert starts[-1] == datetime(2026, 9, 30, 17, 0, tzinfo=UTC)
    assert len(records) == 48 * len(HOURLY_FORECAST_PARAM_CODES)


def test_hourly_forecast_unreadable_current_time_falls_back_to_fetch_time():
    for bad in ("garbage", None, 12):
        payload = _hourly_payload()
        payload["current"] = {"time": bad}
        starts = sorted({r["valid_from"] for r in _hourly(payload)})
        assert starts[0] == datetime(2026, 9, 28, 18, 0, tzinfo=UTC)  # floor(FETCHED)
        assert len(starts) == 48
