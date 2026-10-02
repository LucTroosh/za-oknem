"""Tests for haversine_km: known-distance sanity checks."""

import pytest

from app.geo import haversine_km


def test_haversine_same_point_is_zero():
    assert haversine_km(50.43, 16.65, 50.43, 16.65) == 0.0


def test_haversine_klodzko_to_warszawa_is_roughly_correct():
    # Kłodzko (50.433493, 16.65366) -> Warszawa (52.2297, 21.0122).
    # Computed value (verified with this exact function): ~362.65 km. Range, not
    # an exact pin, to allow for float rounding without over-fitting the test.
    distance = haversine_km(50.433493, 16.65366, 52.2297, 21.0122)
    assert 355 < distance < 370


def test_haversine_is_symmetric():
    a = haversine_km(50.43, 16.65, 52.23, 21.01)
    b = haversine_km(52.23, 21.01, 50.43, 16.65)
    assert a == b


# --- select_stations (ADR-025): pure, deterministic area -> station choice ------------

from app.geo import MAX_MATCH_DISTANCE_KM, select_stations  # noqa: E402

KLODZKO = (50.433493, 16.65366)


def test_select_stations_nearest_within_limit_with_distance_and_method():
    stations = [("far", 52.2297, 21.0122), ("38", 50.44, 16.66), ("40", 50.50, 16.70)]

    [match] = select_stations(*KLODZKO, stations)

    assert match.station_id == "38"
    assert 0 < match.distance_km < 2
    assert match.method == "nearest_station"


def test_select_stations_none_in_range_is_empty_not_nearest_fallback():
    # Warszawa is ~360 km from Kłodzko: the "nearest" exists but is out of the limit.
    assert select_stations(*KLODZKO, [("w", 52.2297, 21.0122)]) == []
    assert select_stations(*KLODZKO, []) == []


def test_select_stations_limit_is_inclusive_and_exact():
    station = ("38", 50.60, 16.65366)
    exact = haversine_km(*KLODZKO, station[1], station[2])

    assert select_stations(*KLODZKO, [station], max_km=exact) != []
    assert select_stations(*KLODZKO, [station], max_km=exact - 0.0004) == []  # not rounded in
    assert MAX_MATCH_DISTANCE_KM == 50.0


def test_select_stations_tie_break_is_station_id_independent_of_input_order():
    # Same coordinates = identical distance: numeric id order (9 < 10), not insertion order.
    a, b = ("10", 50.5, 16.7), ("9", 50.5, 16.7)

    assert select_stations(*KLODZKO, [a, b])[0].station_id == "9"
    assert select_stations(*KLODZKO, [b, a])[0].station_id == "9"
    assert select_stations(*KLODZKO, [("x1", 50.5, 16.7), a])[0].station_id == "10"


def test_select_stations_limit_returns_ranked_prefix():
    stations = [("3", 50.60, 16.65), ("1", 50.44, 16.65), ("2", 50.50, 16.65)]

    assert [m.station_id for m in select_stations(*KLODZKO, stations, limit=2)] == ["1", "2"]


def test_select_stations_is_deterministic_on_repeat():
    stations = [("1", 50.5, 16.7), ("2", 50.5, 16.7), ("3", 50.51, 16.7)]

    assert select_stations(*KLODZKO, stations) == select_stations(*KLODZKO, stations)


# --- ADR-029: air coverage ladder ---------------------------------------------------------

from app.geo import (  # noqa: E402
    EXACT_MAX_KM,
    NEARBY_MAX_KM,
    REGIONAL_MAX_KM,
    classify_air_coverage,
    coverage_radius_km,
)

_KM_PER_DEG_LAT = 111.19492664455873  # 2*pi*6371/360, the radius haversine_km uses


@pytest.mark.parametrize(
    ("km", "level"),
    [
        (0.0, "exact"),
        (10.0, "exact"),  # inclusive bounds
        (10.04, "exact"),  # rounded to the 0.1 km clients see
        (10.06, "nearby"),
        (49.9, "nearby"),
        (50.0, "nearby"),
        (50.04, "nearby"),
        (50.06, "regional"),
        (99.9, "regional"),
        (100.0, "regional"),
        (100.04, "regional"),
        (100.06, "none"),
        (100.1, "none"),
        (None, "none"),
    ],
)
def test_classify_air_coverage_boundaries(km, level):
    assert classify_air_coverage(km) == level


def test_coverage_constants_and_radii():
    assert (EXACT_MAX_KM, NEARBY_MAX_KM, REGIONAL_MAX_KM) == (10.0, 50.0, 100.0)
    assert NEARBY_MAX_KM == MAX_MATCH_DISTANCE_KM  # ADR-006/025 limit is the "nearby" edge
    assert [coverage_radius_km(c) for c in ("exact", "nearby", "regional", "none")] == [
        10,
        50,
        100,
        None,
    ]


@pytest.mark.parametrize(
    ("km", "level"),
    [(49.9, "nearby"), (50.0, "nearby"), (99.9, "regional"), (100.1, None)],
)
def test_select_stations_plus_classification_end_to_end(km, level):
    lat0, lon0 = KLODZKO
    station = ("s", lat0 + km / _KM_PER_DEG_LAT, lon0)  # due north, `km` away

    matches = select_stations(lat0, lon0, [station], max_km=REGIONAL_MAX_KM)

    if level is None:
        assert matches == []  # beyond 100 km: no station at all -> coverage none
        assert classify_air_coverage(None) == "none"
    else:
        assert classify_air_coverage(matches[0].distance_km) == level
