"""Tests for imgw_hydro.parser.normalize(): field mapping, null-reading skip,
and the deliberate absence of a negative-value rejection (unlike GIOŚ's PM2.5
check - stan_wody can legitimately be negative, see parser.py's comment)."""

from datetime import UTC, datetime

import pytest

from app.connectors.imgw_hydro.parser import ImgwHydroParseError, normalize

STATION = {
    "id_stacji": "151140030",
    "stacja": "Przewoźniki",
    "rzeka": "Skroda",
    "lat": "51.5253",
    "lon": "14.8217",
    "stan_wody": "225",
    "stan_wody_data_pomiaru": "2026-09-27 21:20:00",
}


def test_normalize_maps_fields_correctly():
    record = normalize(STATION, fetched_at=datetime.now(UTC))

    assert record["source_id"] == "imgw_hydro"
    assert record["station_id"] == "151140030"
    assert record["station_name"] == "Przewoźniki (Skroda)"
    assert record["latitude"] == 51.5253
    assert record["longitude"] == 14.8217
    assert record["param_code"] == "water_level_cm"
    assert record["value"] == 225.0
    assert record["unit"] == "cm"


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
    record = normalize(station, fetched_at=datetime.now(UTC))
    assert record["value"] == -5.0


def test_normalize_raises_on_missing_field():
    station = {k: v for k, v in STATION.items() if k != "lat"}
    with pytest.raises(ImgwHydroParseError):
        normalize(station, fetched_at=datetime.now(UTC))


def test_normalize_raises_on_out_of_range_coordinates():
    station = {**STATION, "lat": "999"}
    with pytest.raises(ImgwHydroParseError):
        normalize(station, fetched_at=datetime.now(UTC))
