"""Parser tests.

FIXTURE, not a recorded live response: built only from fields confirmed by the
official docs (open-meteo.com/en/docs/air-quality-api: `hourly.time` + one parallel
array per variable, `hourly_units`, variables `*_pollen` in grains/m3,
`utc_offset_seconds`). The exact unit string and null-vs-0 behaviour outside the
pollen season are NOT verified live - see ADR-020.
"""

from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest

from app.connectors.open_meteo_pollen.parser import (
    MODEL,
    SOURCE_ID,
    OpenMeteoPollenParseError,
    normalize,
)

FETCHED_AT = datetime(2026, 5, 4, 7, 12, tzinfo=UTC)
HOUR = FETCHED_AT.replace(minute=0)  # the fetch hour: every fixture slot is relative to it


def _stamp(hours_from_fetch_hour: int) -> str:
    return (HOUR + timedelta(hours=hours_from_fetch_hour)).strftime("%Y-%m-%dT%H:%M")


UNIT = "grains/m³"
VARS = ("alder_pollen", "birch_pollen", "grass_pollen", "mugwort_pollen", "ragweed_pollen")

PAYLOAD = {  # FIXTURE (docs-derived)
    "latitude": 50.4,
    "longitude": 16.6,
    "utc_offset_seconds": 0,
    "timezone": "UTC",
    "hourly_units": {"time": "iso8601", **dict.fromkeys(VARS, UNIT)},
    "hourly": {
        "time": [_stamp(-1), _stamp(0), _stamp(1)],
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
    assert r["valid_at"] == HOUR
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
    b = normalize(geo_area_id=7, payload=PAYLOAD, fetched_at=HOUR.replace(minute=59))
    assert a[0]["forecast_reference_time"] == datetime(2026, 5, 4, tzinfo=UTC)
    # same run day -> same ids (idempotent re-ingest); next day -> new ids
    assert [r["source_record_id"] for r in a] == [r["source_record_id"] for r in b]
    next_day = HOUR + timedelta(days=1)
    c_payload = deepcopy(PAYLOAD)
    c_payload["hourly"]["time"] = [
        (next_day + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M") for h in (-1, 0, 1)
    ]
    c = normalize(geo_area_id=7, payload=c_payload, fetched_at=next_day)
    assert c[0]["source_record_id"] != a[0]["source_record_id"]


@pytest.mark.parametrize("missing", ["hourly", "hourly_units"])
def test_missing_block_raises(missing):
    bad = deepcopy(PAYLOAD)
    del bad[missing]
    with pytest.raises(OpenMeteoPollenParseError):
        _normalize(bad)


def test_series_must_cover_the_fetch_hour():
    for hours in ([-9, -8, -7], [2, 3, 4], [-30, -29, -28]):  # all stale / all future-only
        bad = deepcopy(PAYLOAD)
        bad["hourly"]["time"] = [_stamp(h) for h in hours]
        with pytest.raises(OpenMeteoPollenParseError, match="cover"):
            _normalize(bad)


def test_the_exact_fetch_hour_slot_is_required_not_just_a_nearby_one():
    # only the previous hour (+ future hours, slot omitted) would replace the previous bucket
    # and leave `current` null until the next daily run
    for hours in ([-3, -2, -1], [-1, 1, 2]):
        bad = deepcopy(PAYLOAD)
        bad["hourly"]["time"] = [_stamp(h) for h in hours]
        with pytest.raises(OpenMeteoPollenParseError, match="cover"):
            _normalize(bad)
    # fetched_at late in the fetch hour is still that hour
    assert len(normalize(geo_area_id=7, payload=PAYLOAD, fetched_at=HOUR.replace(minute=59))) == 3
    # a series that ended before the fetch hour no longer qualifies
    with pytest.raises(OpenMeteoPollenParseError, match="cover"):
        normalize(geo_area_id=7, payload=PAYLOAD, fetched_at=HOUR + timedelta(hours=2))


def test_all_null_series_covering_the_fetch_hour_is_valid_out_of_season():
    quiet = deepcopy(PAYLOAD)
    for variable in VARS:
        quiet["hourly"][variable] = [None, None, None]
    records = _normalize(quiet)
    assert len(records) == 3
    assert all(
        r[s] is None for r in records for s in ("alder", "birch", "grass", "mugwort", "ragweed")
    )


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


@pytest.mark.parametrize("stamp", [f"{_stamp(0)}+02:00", f"{_stamp(0)}Z"])
def test_timestamps_with_an_offset_raise_instead_of_being_relabelled(stamp):
    bad = deepcopy(PAYLOAD)
    bad["hourly"]["time"][1] = stamp
    with pytest.raises(OpenMeteoPollenParseError, match="offset"):
        _normalize(bad)


@pytest.mark.parametrize(
    "stamp", [HOUR.strftime("%Y-%m-%d"), 20260504, "20260504T0700", None, 1777852800]
)
def test_non_hourly_timestamp_shapes_raise_instead_of_becoming_midnight(stamp):
    bad = deepcopy(PAYLOAD)
    bad["hourly"]["time"][1] = stamp
    with pytest.raises(OpenMeteoPollenParseError):
        _normalize(bad)


@pytest.mark.parametrize("stamp", [f"{_stamp(0)[:-2]}30", f"{_stamp(0)}:30"])
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


def test_unit_wider_than_the_column_raises_instead_of_failing_in_postgres():
    bad = deepcopy(PAYLOAD)
    for variable in VARS:
        bad["hourly_units"][variable] = "x" * 21
    with pytest.raises(OpenMeteoPollenParseError, match="longer"):
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
