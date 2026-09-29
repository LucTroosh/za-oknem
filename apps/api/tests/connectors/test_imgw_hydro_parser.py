"""Tests for imgw_hydro.parser.normalize(): field mapping, null-reading skip,
and the deliberate absence of a negative-value rejection (unlike GIOŚ's PM2.5
check - stan_wody can legitimately be negative, see parser.py's comment)."""

from datetime import UTC, datetime

import pytest

from app.connectors.imgw_hydro.parser import (
    ALARM_LEVEL_PARAM,
    WARNING_LEVEL_PARAM,
    WATER_LEVEL_PARAM,
    ImgwHydroParseError,
    normalize,
)

STATION = {
    "id_stacji": "151140030",
    "stacja": "Przewoźniki",
    "rzeka": "Skroda",
    "lat": "51.5253",
    "lon": "14.8217",
    "stan_wody": "225",
    "stan_wody_data_pomiaru": "2026-09-27 21:20:00",
    "stan_ostrzegawczy": "300",
    "stan_alarmowy": "340",
}


def test_normalize_maps_fields_correctly():
    records = normalize(STATION, fetched_at=datetime.now(UTC))
    record = records[0]

    assert record["source_id"] == "imgw_hydro"
    assert record["station_id"] == "151140030"
    assert record["station_name"] == "Przewoźniki (Skroda)"
    assert record["latitude"] == 51.5253
    assert record["longitude"] == 14.8217
    assert record["param_code"] == "water_level_cm"
    assert record["value"] == 225.0
    assert record["unit"] == "cm"


def test_normalize_includes_warning_and_alarm_thresholds_when_defined():
    records = normalize(STATION, fetched_at=datetime.now(UTC))

    by_param = {r["param_code"]: r for r in records}
    assert len(records) == 3
    assert by_param[WARNING_LEVEL_PARAM]["value"] == 300.0
    assert by_param[ALARM_LEVEL_PARAM]["value"] == 340.0
    # source_record_id must be unique per param_code, not just per station+time
    assert len({r["source_record_id"] for r in records}) == 3


def test_normalize_omits_thresholds_when_null():
    """Confirmed live: some stations (e.g. lake gauges) have no defined
    warning/alarm threshold - null, not an error."""
    station = {**STATION, "stan_ostrzegawczy": None, "stan_alarmowy": None}
    records = normalize(station, fetched_at=datetime.now(UTC))

    assert len(records) == 1
    assert records[0]["param_code"] == WATER_LEVEL_PARAM


def test_normalize_raises_on_malformed_threshold():
    station = {**STATION, "stan_ostrzegawczy": "not-a-number"}
    with pytest.raises(ImgwHydroParseError):
        normalize(station, fetched_at=datetime.now(UTC))


def test_param_codes_fit_the_varchar20_column():
    """Measurement.param_code is VARCHAR(20) (models.py) - SQLite doesn't enforce
    this, so it must be checked explicitly (Codex review, PR #42: PostgreSQL
    would reject water_level_warning_cm at 22 chars, silently after the
    water-level record for that station was already committed)."""
    for param_code in (WATER_LEVEL_PARAM, WARNING_LEVEL_PARAM, ALARM_LEVEL_PARAM):
        assert len(param_code) <= 20, param_code


def test_normalize_returns_none_when_no_current_reading():
    station = {**STATION, "stan_wody": None}
    assert normalize(station, fetched_at=datetime.now(UTC)) is None


def test_normalize_returns_none_when_no_reading_timestamp():
    station = {**STATION, "stan_wody_data_pomiaru": None}
    assert normalize(station, fetched_at=datetime.now(UTC)) is None


def test_normalize_accepts_negative_water_level():
    """Unlike PM2.5, a negative stan_wody is physically valid (below the local
    gauge-zero reference) - must not be rejected."""
    station = {**STATION, "stan_wody": "-5"}
    records = normalize(station, fetched_at=datetime.now(UTC))
    assert records[0]["value"] == -5.0


def test_normalize_raises_on_missing_field():
    station = {k: v for k, v in STATION.items() if k != "lat"}
    with pytest.raises(ImgwHydroParseError):
        normalize(station, fetched_at=datetime.now(UTC))


def test_normalize_raises_on_out_of_range_coordinates():
    station = {**STATION, "lat": "999"}
    with pytest.raises(ImgwHydroParseError):
        normalize(station, fetched_at=datetime.now(UTC))
