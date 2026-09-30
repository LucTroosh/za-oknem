"""Tests for GET /api/v1/dashboard/latest: nearest-station join (ADR-006).

Same fake-session approach as test_air.py/test_weather.py (Postgres DISTINCT ON,
SQLite can't compile it). Three execute() calls in order: geo_areas, stations,
weather snapshots.
"""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app
from app.models import Alert, GeoArea, Measurement, WeatherSnapshot

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


def _client(areas, stations, weather_rows, alert_rows=()) -> TestClient:
    def _override():
        yield _FakeSession(areas, stations, weather_rows, list(alert_rows))

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
    assert body["areas"] == []


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


def test_dashboard_air_has_source_transparency_fields():
    # TASK-7.1 (Master Plan Principle 2): source+observed_at+freshness together,
    # attribution text verbatim from source-registry.md.
    client = _client([GeoArea(**KLODZKO)], [_station()], [])

    body = client.get("/api/v1/dashboard/latest").json()

    air = body["areas"][0]["air"]
    assert air["source"] == "gios"
    assert air["attribution"] == "Dane: Główny Inspektorat Ochrony Środowiska (GIOŚ)"
    assert air["observed_at"] == air["params"]["PM2.5"]["observed_at"]


def test_dashboard_weather_has_source_transparency_fields():
    client = _client([GeoArea(**KLODZKO)], [], [_weather()])

    body = client.get("/api/v1/dashboard/latest").json()

    weather = body["areas"][0]["weather"]
    assert weather["source"] == "open_meteo"
    assert weather["attribution"] == "Weather data by Open-Meteo.com (CC BY 4.0)"


def test_dashboard_groups_multiple_params_for_nearest_station():
    pm25 = _station(param_code="PM2.5", value=11.5, source_record_id="a")
    no2 = _station(param_code="NO2", value=8.0, unit="µg/m³", source_record_id="b")
    client = _client([GeoArea(**KLODZKO)], [pm25, no2], [])

    body = client.get("/api/v1/dashboard/latest").json()

    params = body["areas"][0]["air"]["params"]
    assert set(params) == {"PM2.5", "NO2"}
    assert params["NO2"]["value"] == 8.0


def test_dashboard_station_query_filters_by_gios_source():
    # Codex review: `measurements` is shared with imgw_hydro (water_level_cm) —
    # without this filter the nearest-station join could match a river gauge
    # instead of an air station. _FakeSession ignores the stmt entirely, so this
    # inspects the station query's WHERE clause directly (not the full DISTINCT
    # ON select, which is Postgres-dialect-only and needs a real dialect to compile).
    captured = {}

    class _CapturingSession:
        def __init__(self):
            self._call = 0

        def execute(self, stmt):
            self._call += 1
            if self._call == 2:  # areas, then stations, then weather
                captured["where"] = str(
                    stmt.whereclause.compile(compile_kwargs={"literal_binds": True})
                )
            return _FakeResult([])

    def _override():
        yield _CapturingSession()

    app.dependency_overrides[get_db] = _override
    try:
        client = TestClient(app)
        client.get("/api/v1/dashboard/latest")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert "source_id" in captured["where"] and "gios" in captured["where"]


def _alert_row(**overrides) -> Alert:
    now = datetime.now(UTC)
    defaults = {
        "source_id": "imgw_warningshydro",
        "source_record_id": "a-1",
        "external_id": "1/2026",
        "event_type": "Susza hydrologiczna",
        "severity_raw": "-1",
        "probability_pct": None,
        "issuing_office": "Biuro Prognoz Hydrologicznych we Wrocławiu",
        "description": "opis",
        "comment": None,
        "areas": [{"wojewodztwo": "wielkopolskie"}],
        "valid_from": now - timedelta(days=1),
        "valid_until": now + timedelta(days=1),
        "published_at": now - timedelta(days=1),
        "fetched_at": now,
    }
    defaults.update(overrides)
    return Alert(**defaults)


def test_dashboard_includes_national_alerts_block():
    # TASK-7.2: alerts in the aggregate (§55), explicitly national until TASK-9.5.
    client = _client([GeoArea(**KLODZKO)], [], [], [_alert_row()])

    body = client.get("/api/v1/dashboard/latest").json()

    assert body["alerts"]["scope"] == "national"
    assert body["alerts"]["source"] == "imgw"
    assert body["alerts"]["attribution"].startswith("Źródłem pochodzenia danych jest Instytut")
    assert [a["event_type"] for a in body["alerts"]["items"]] == ["Susza hydrologiczna"]
    assert body["alerts"]["items"][0]["freshness"] == "FRESH"
    assert "alerts" not in body["areas"][0]  # never presented as local


def test_dashboard_alerts_items_empty_when_no_alerts():
    client = _client([GeoArea(**KLODZKO)], [], [])

    assert client.get("/api/v1/dashboard/latest").json()["alerts"]["items"] == []
