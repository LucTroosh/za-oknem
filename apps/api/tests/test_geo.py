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
