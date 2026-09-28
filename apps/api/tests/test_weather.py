"""Tests for GET /api/v1/weather/latest: freshness thresholds and response shaping.

Same fake-session approach as test_air.py (Postgres DISTINCT ON, SQLite can't
compile it) — but this endpoint issues two execute() calls (snapshots, then
geo_areas), so the fake session returns queued results in call order.
"""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.api.v1.weather import FRESH_MAX_AGE, RECENT_MAX_AGE, freshness
from app.db import get_db
from app.main import app
from app.models import GeoArea, WeatherSnapshot


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


def _client(snapshot_rows: list[WeatherSnapshot], geo_areas: list[GeoArea]) -> TestClient:
    def _override():
        yield _FakeSession(snapshot_rows, geo_areas)

    app.dependency_overrides[get_db] = _override
    return TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.pop(get_db, None)


def _area(**overrides) -> GeoArea:
    defaults = {"id": 1, "slug": "klodzko", "name": "Kłodzko", "latitude": 50.43, "longitude": 16.65}
    defaults.update(overrides)
    return GeoArea(**defaults)


def _snapshot(**overrides) -> WeatherSnapshot:
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


# --- freshness() thresholds --------------------------------------------------


def test_freshness_within_fresh_threshold():
    assert freshness(datetime.now(UTC) - (FRESH_MAX_AGE - timedelta(minutes=1))) == "FRESH"


def test_freshness_just_past_fresh_threshold_is_recent():
    assert freshness(datetime.now(UTC) - (FRESH_MAX_AGE + timedelta(minutes=1))) == "RECENT"


def test_freshness_just_past_recent_threshold_is_stale():
    assert freshness(datetime.now(UTC) - (RECENT_MAX_AGE + timedelta(minutes=1))) == "STALE"


# --- GET /api/v1/weather/latest ----------------------------------------------


def test_latest_weather_returns_empty_list_when_no_rows():
    client = _client([], [])

    response = client.get("/api/v1/weather/latest")

    assert response.status_code == 200
    assert response.json() == {"areas": []}


def test_latest_weather_groups_params_by_geo_area():
    now = datetime.now(UTC)
    rows = [
        _snapshot(param_code="temperature_2m", value=12.3, unit="°C", observed_at=now),
        _snapshot(param_code="wind_speed_10m", value=5.2, unit="km/h", observed_at=now),
    ]
    client = _client(rows, [_area()])

    body = client.get("/api/v1/weather/latest").json()

    assert body == {
        "areas": [
            {
                "geo_area_id": 1,
                "slug": "klodzko",
                "name": "Kłodzko",
                "latitude": 50.43,
                "longitude": 16.65,
                "observed_at": now.isoformat(),
                "freshness": "FRESH",
                "params": {
                    "temperature_2m": {"value": 12.3, "unit": "°C"},
                    "wind_speed_10m": {"value": 5.2, "unit": "km/h"},
                },
                "source": "open_meteo",
            }
        ]
    }


def test_latest_weather_marks_old_reading_stale():
    row = _snapshot(observed_at=datetime.now(UTC) - timedelta(hours=10))
    client = _client([row], [_area()])

    body = client.get("/api/v1/weather/latest").json()

    assert body["areas"][0]["freshness"] == "STALE"


def test_latest_weather_skips_snapshot_for_deleted_geo_area():
    row = _snapshot(geo_area_id=999)
    client = _client([row], [_area()])  # area id=1, snapshot references id=999

    body = client.get("/api/v1/weather/latest").json()

    assert body == {"areas": []}


def test_latest_weather_handles_multiple_areas():
    rows = [
        _snapshot(geo_area_id=1, source_record_id="a"),
        _snapshot(geo_area_id=2, source_record_id="b"),
    ]
    areas = [_area(id=1, slug="klodzko"), _area(id=2, slug="warszawa", name="Warszawa")]
    client = _client(rows, areas)

    body = client.get("/api/v1/weather/latest").json()

    assert {a["slug"] for a in body["areas"]} == {"klodzko", "warszawa"}
