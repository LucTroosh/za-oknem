"""Parser tests.

FIXTURE, not a recorded live response: built only from fields confirmed by the
official docs (open-meteo.com/en/docs/air-quality-api: `hourly.time` + one parallel
array per variable, `hourly_units`, variables `*_pollen` in grains/m3,
`utc_offset_seconds`). The exact unit string and null-vs-0 behaviour outside the
pollen season are NOT verified live - see ADR-020.
"""

from copy import deepcopy
from datetime import UTC, datetime

import pytest

from app.connectors.open_meteo_pollen.parser import (
    MODEL,
    SOURCE_ID,
    OpenMeteoPollenParseError,
    normalize,
)

FETCHED_AT = datetime(2026, 5, 4, 7, 12, tzinfo=UTC)
UNIT = "grains/m³"
VARS = ("alder_pollen", "birch_pollen", "grass_pollen", "mugwort_pollen", "ragweed_pollen")

PAYLOAD = {  # FIXTURE (docs-derived)
    "latitude": 50.4,
    "longitude": 16.6,
    "utc_offset_seconds": 0,
    "timezone": "UTC",
    "hourly_units": {"time": "iso8601", **dict.fromkeys(VARS, UNIT)},
    "hourly": {
        "time": ["2026-05-04T00:00", "2026-05-04T01:00", "2026-05-04T02:00"],
        "alder_pollen": [0.0, 0.4, None],
        "birch_pollen": [12.5, 13.0, 14.25],
        "grass_pollen": [None, None, None],
        "mugwort_pollen": [0.0, 0.0, 0.0],
        "ragweed_pollen": [None, 1, 2],
    },
}


def _normalize(payload=PAYLOAD):
    return normalize(geo_area_id=7, payload=payload, fetched_at=FETCHED_AT)


def test_one_record_per_hour_with_all_five_species():
    records = _normalize()
    assert len(records) == 3
    r = records[1]
    assert (r["alder"], r["birch"], r["grass"], r["mugwort"], r["ragweed"]) == (
        0.4,
        13.0,
        None,
        0.0,
        1.0,
    )
    assert r["unit"] == UNIT
    assert r["valid_at"] == datetime(2026, 5, 4, 1, tzinfo=UTC)
    assert r["model"] == MODEL == "cams_europe"
    assert r["source_id"] == SOURCE_ID
    assert r["geo_area_id"] == 7
    assert r["fetched_at"] == FETCHED_AT


def test_null_stays_null_and_zero_stays_zero():
    records = _normalize()
    assert records[2]["alder"] is None  # no value from the model
    assert records[0]["alder"] == 0.0  # a real modelled zero
    assert all(r["grass"] is None for r in records)


def test_reference_time_is_bucketed_to_the_24h_cycle_and_ids_are_stable():
    a = _normalize()
    b = normalize(
        geo_area_id=7, payload=PAYLOAD, fetched_at=datetime(2026, 5, 4, 23, 59, tzinfo=UTC)
    )
    assert a[0]["forecast_reference_time"] == datetime(2026, 5, 4, tzinfo=UTC)
    # same run day -> same ids (idempotent re-ingest); next day -> new ids
    assert [r["source_record_id"] for r in a] == [r["source_record_id"] for r in b]
    c = normalize(geo_area_id=7, payload=PAYLOAD, fetched_at=datetime(2026, 5, 5, 7, 0, tzinfo=UTC))
    assert c[0]["source_record_id"] != a[0]["source_record_id"]


@pytest.mark.parametrize("missing", ["hourly", "hourly_units"])
def test_missing_block_raises(missing):
    bad = deepcopy(PAYLOAD)
    del bad[missing]
    with pytest.raises(OpenMeteoPollenParseError):
        _normalize(bad)


def test_missing_species_raises():
    bad = deepcopy(PAYLOAD)
    del bad["hourly"]["ragweed_pollen"]
    with pytest.raises(OpenMeteoPollenParseError):
        _normalize(bad)


def test_length_mismatch_raises():
    bad = deepcopy(PAYLOAD)
    bad["hourly"]["birch_pollen"] = [1.0]
    with pytest.raises(OpenMeteoPollenParseError):
        _normalize(bad)


@pytest.mark.parametrize("value", ["12", True, -1.0, float("inf"), float("nan")])
def test_impossible_values_raise(value):
    bad = deepcopy(PAYLOAD)
    bad["hourly"]["birch_pollen"][0] = value
    with pytest.raises(OpenMeteoPollenParseError):
        _normalize(bad)


def test_missing_utc_offset_raises_not_defaulted_to_utc():
    bad = deepcopy(PAYLOAD)
    del bad["utc_offset_seconds"]
    with pytest.raises(OpenMeteoPollenParseError):
        _normalize(bad)


def test_duplicate_timestamps_raise():
    bad = deepcopy(PAYLOAD)
    bad["hourly"]["time"][1] = bad["hourly"]["time"][0]
    with pytest.raises(OpenMeteoPollenParseError, match="duplicate"):
        _normalize(bad)


@pytest.mark.parametrize("stamp", ["2026-05-04T01:00+02:00", "2026-05-04T01:00Z"])
def test_timestamps_with_an_offset_raise_instead_of_being_relabelled(stamp):
    bad = deepcopy(PAYLOAD)
    bad["hourly"]["time"][1] = stamp
    with pytest.raises(OpenMeteoPollenParseError, match="offset"):
        _normalize(bad)


@pytest.mark.parametrize("stamp", ["2026-05-04", 20260504, "20260504T0100", None, 1777852800])
def test_non_hourly_timestamp_shapes_raise_instead_of_becoming_midnight(stamp):
    bad = deepcopy(PAYLOAD)
    bad["hourly"]["time"][1] = stamp
    with pytest.raises(OpenMeteoPollenParseError):
        _normalize(bad)


@pytest.mark.parametrize("stamp", ["2026-05-04T01:30", "2026-05-04T01:00:30"])
def test_timestamps_not_aligned_to_the_hour_raise(stamp):
    bad = deepcopy(PAYLOAD)
    bad["hourly"]["time"][1] = stamp
    with pytest.raises(OpenMeteoPollenParseError, match="aligned"):
        _normalize(bad)


def test_oversized_integer_is_a_parse_error_not_an_overflow():
    bad = deepcopy(PAYLOAD)
    bad["hourly"]["birch_pollen"][0] = 10**309
    with pytest.raises(OpenMeteoPollenParseError):
        _normalize(bad)


@pytest.mark.parametrize("unit", [None, "", "  ", 5])
def test_non_string_or_empty_units_raise(unit):
    bad = deepcopy(PAYLOAD)
    for variable in VARS:
        bad["hourly_units"][variable] = unit
    with pytest.raises(OpenMeteoPollenParseError):
        _normalize(bad)


def test_differing_units_raise():
    bad = deepcopy(PAYLOAD)
    bad["hourly_units"]["birch_pollen"] = "other"
    with pytest.raises(OpenMeteoPollenParseError):
        _normalize(bad)


def test_non_utc_offset_raises():
    bad = deepcopy(PAYLOAD)
    bad["utc_offset_seconds"] = 7200
    with pytest.raises(OpenMeteoPollenParseError):
        _normalize(bad)


def test_bad_timestamp_and_empty_times_raise():
    bad = deepcopy(PAYLOAD)
    bad["hourly"]["time"][0] = "not-a-time"
    with pytest.raises(OpenMeteoPollenParseError):
        _normalize(bad)
    empty = deepcopy(PAYLOAD)
    for k in ("time", *VARS):
        empty["hourly"][k] = []
    with pytest.raises(OpenMeteoPollenParseError):
        _normalize(empty)


def test_non_dict_payload_raises_parse_error():
    with pytest.raises(OpenMeteoPollenParseError):
        _normalize([1, 2])  # type: ignore[arg-type]
