"""Tests for GET /api/v1/hydro/latest: same fake-session pattern as test_air.py
(DISTINCT ON isn't SQLite-compatible - see that file's docstring for why)."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.api.v1.hydro import FRESH_MAX_AGE, RECENT_MAX_AGE, freshness
from app.db import get_db
from app.main import app
from app.models import Measurement


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, rows):
        self._rows = rows

    def execute(self, _stmt):
        return _FakeResult(self._rows)


def _client_with_rows(rows: list[Measurement]) -> TestClient:
    def _override():
        yield _FakeSession(rows)

    app.dependency_overrides[get_db] = _override
    return TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.pop(get_db, None)


def _reading(**overrides) -> Measurement:
    defaults = {
        "source_id": "imgw_hydro",
        "source_record_id": "rec-1",
        "station_id": "151140030",
        "station_name": "Przewoźniki (Skroda)",
        "latitude": 51.5253,
        "longitude": 14.8217,
        "param_code": "water_level_cm",
        "value": 225.0,
        "unit": "cm",
        "observed_at": datetime.now(UTC),
        "fetched_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return Measurement(**defaults)


def test_freshness_within_fresh_threshold():
    assert freshness(datetime.now(UTC) - (FRESH_MAX_AGE - timedelta(minutes=1))) == "FRESH"


def test_freshness_just_past_recent_threshold_is_stale():
    assert freshness(datetime.now(UTC) - (RECENT_MAX_AGE + timedelta(minutes=1))) == "STALE"


def test_latest_hydro_returns_empty_list_when_no_rows():
    client = _client_with_rows([])

    response = client.get("/api/v1/hydro/latest")

    assert response.status_code == 200
    assert response.json() == {"stations": []}


def test_latest_hydro_shapes_response_from_rows():
    row = _reading(observed_at=datetime.now(UTC))
    client = _client_with_rows([row])

    body = client.get("/api/v1/hydro/latest").json()

    assert body == {
        "stations": [
            {
                "station_id": "151140030",
                "station_name": "Przewoźniki (Skroda)",
                "latitude": 51.5253,
                "longitude": 14.8217,
                "water_level_cm": 225.0,
                "unit": "cm",
                "observed_at": row.observed_at.isoformat(),
                "freshness": "FRESH",
                "source": "imgw_hydro",
            }
        ]
    }
