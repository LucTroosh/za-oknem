"""Tests for haversine_km: known-distance sanity checks."""

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
    exact = round(haversine_km(*KLODZKO, station[1], station[2]), 3)

    assert select_stations(*KLODZKO, [station], max_km=exact) != []
    assert select_stations(*KLODZKO, [station], max_km=exact - 0.01) == []
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
