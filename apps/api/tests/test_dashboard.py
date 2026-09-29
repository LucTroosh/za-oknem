"""Tests for GET /api/v1/dashboard/latest: nearest-station join (ADR-006).

Same fake-session approach as test_air.py/test_weather.py (Postgres DISTINCT ON,
SQLite can't compile it). Three execute() calls in order: geo_areas, stations,
weather snapshots.
"""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app
from app.models import GeoArea, Measurement, WeatherSnapshot

KLODZKO = {
    "id": 1,
    "slug": "klodzko",
    "name": "Kłodzko",
    "latitude": 50.433493,
    "longitude": 16.65366,
}
WARSZAWA = {
    "id": 2,
    "slug": "warszawa",
    "name": "Warszawa",
    "latitude": 52.2297,
    "longitude": 21.0122,
}


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, *result_sets):
        self._queue = list(result_sets)

    def execute(self, _stmt):
        return _FakeResult(self._queue.pop(0))


def _client(areas, stations, weather_rows) -> TestClient:
    def _override():
        yield _FakeSession(areas, stations, weather_rows)

    app.dependency_overrides[get_db] = _override
    return TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.pop(get_db, None)


def _station(**overrides) -> Measurement:
    defaults = {
        "source_id": "gios",
        "source_record_id": "rec-1",
        "station_id": "38",
        "station_name": "Kłodzko, ul. Szkolna",
        "latitude": 50.433493,
        "longitude": 16.65366,
        "param_code": "PM2.5",
        "value": 11.5,
        "unit": "µg/m³",
        "observed_at": datetime.now(UTC),
        "fetched_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return Measurement(**defaults)


def _weather(**overrides) -> WeatherSnapshot:
    defaults = {
        "source_id": "open_meteo",
        "source_record_id": "rec-1",
        "geo_area_id": 1,
        "param_code": "temperature_2m",
        "value": 12.3,
        "unit": "°C",
        "observed_at": datetime.now(UTC),
        "fetched_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return WeatherSnapshot(**defaults)


def test_dashboard_empty_when_no_geo_areas():
    client = _client([], [], [])
    body = client.get("/api/v1/dashboard/latest").json()
    assert body == {"areas": []}


def test_dashboard_matches_station_within_threshold():
    client = _client([GeoArea(**KLODZKO)], [_station()], [_weather()])

    body = client.get("/api/v1/dashboard/latest").json()

    area = body["areas"][0]
    assert area["slug"] == "klodzko"
    assert area["air"]["station_id"] == "38"
    assert area["air"]["distance_km"] == 0.0
    assert area["air"]["params"]["PM2.5"]["value"] == 11.5
    assert area["weather"]["params"]["temperature_2m"]["value"] == 12.3


def test_dashboard_no_air_when_nearest_station_too_far():
    # Warszawa is ~362km from the only station (Kłodzko) - well past the 50km
    # threshold, so no fake match should be attached.
    client = _client([GeoArea(**WARSZAWA)], [_station()], [])

    body = client.get("/api/v1/dashboard/latest").json()

    assert body["areas"][0]["air"] is None


def test_dashboard_no_air_when_no_stations_at_all():
    client = _client([GeoArea(**KLODZKO)], [], [])

    body = client.get("/api/v1/dashboard/latest").json()

    assert body["areas"][0]["air"] is None


def test_dashboard_no_weather_when_no_snapshots():
    client = _client([GeoArea(**KLODZKO)], [], [])

    body = client.get("/api/v1/dashboard/latest").json()

    assert body["areas"][0]["weather"] is None


def test_dashboard_picks_nearest_of_multiple_stations():
    far_station = _station(
        station_id="99", latitude=52.2297, longitude=21.0122, source_record_id="b"
    )
    near_station = _station(station_id="38", source_record_id="a")
    client = _client([GeoArea(**KLODZKO)], [far_station, near_station], [])

    body = client.get("/api/v1/dashboard/latest").json()

    assert body["areas"][0]["air"]["station_id"] == "38"


def test_dashboard_marks_stale_air_reading():
    old = _station(observed_at=datetime.now(UTC) - timedelta(hours=10))
    client = _client([GeoArea(**KLODZKO)], [old], [])

    body = client.get("/api/v1/dashboard/latest").json()

    assert body["areas"][0]["air"]["params"]["PM2.5"]["freshness"] == "STALE"


def test_dashboard_groups_multiple_params_for_nearest_station():
    pm25 = _station(param_code="PM2.5", value=11.5, source_record_id="a")
    no2 = _station(param_code="NO2", value=8.0, unit="µg/m³", source_record_id="b")
    client = _client([GeoArea(**KLODZKO)], [pm25, no2], [])

    body = client.get("/api/v1/dashboard/latest").json()

    params = body["areas"][0]["air"]["params"]
    assert set(params) == {"PM2.5", "NO2"}
    assert params["NO2"]["value"] == 8.0
