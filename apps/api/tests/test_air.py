"""Tests for GET /api/v1/air/latest: freshness thresholds and response shaping.

The query in air.py uses Postgres' DISTINCT ON (rule #2: Postgres is the source
of truth) — SQLite can't compile that, so this suite fakes the DB session's
execute() to test the Python-level logic (row -> dict, freshness computation,
empty-list handling) instead of the SQL itself. The query was already verified
against a live Postgres end-to-end (README's manual smoke test, and the live
physical-device run) — this suite doesn't re-prove the SQL, only the code
around it.
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.v1.air import FRESH_MAX_AGE, RECENT_MAX_AGE, AirLatestResponse, freshness
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


def _measurement(**overrides) -> Measurement:
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


# --- freshness() thresholds --------------------------------------------------
# Margins (1 min) instead of exact boundaries — freshness() calls datetime.now()
# internally, so an exact-boundary test would be flaky by the execution gap.


def test_freshness_within_fresh_threshold():
    assert freshness(datetime.now(UTC) - (FRESH_MAX_AGE - timedelta(minutes=1))) == "FRESH"


def test_freshness_just_past_fresh_threshold_is_recent():
    assert freshness(datetime.now(UTC) - (FRESH_MAX_AGE + timedelta(minutes=1))) == "RECENT"


def test_freshness_within_recent_threshold():
    assert freshness(datetime.now(UTC) - (RECENT_MAX_AGE - timedelta(minutes=1))) == "RECENT"


def test_freshness_just_past_recent_threshold_is_stale():
    assert freshness(datetime.now(UTC) - (RECENT_MAX_AGE + timedelta(minutes=1))) == "STALE"


# --- GET /api/v1/air/latest ---------------------------------------------------


def test_latest_air_quality_returns_empty_list_when_no_rows():
    client = _client_with_rows([])

    response = client.get("/api/v1/air/latest")

    assert response.status_code == 200
    assert response.json() == {"stations": []}


def test_latest_air_quality_shapes_response_from_rows():
    row = _measurement(observed_at=datetime.now(UTC))
    client = _client_with_rows([row])

    body = client.get("/api/v1/air/latest").json()

    assert body == {
        "stations": [
            {
                "station_id": "38",
                "station_name": "Kłodzko, ul. Szkolna",
                "latitude": 50.433493,
                "longitude": 16.65366,
                "params": {
                    "PM2.5": {
                        "value": 11.5,
                        "unit": "µg/m³",
                        "observed_at": row.observed_at.isoformat(),
                        "freshness": "FRESH",
                    }
                },
                "source": "gios",
            }
        ]
    }


def test_latest_air_quality_marks_old_reading_stale():
    row = _measurement(observed_at=datetime.now(UTC) - timedelta(hours=10))
    client = _client_with_rows([row])

    body = client.get("/api/v1/air/latest").json()

    assert body["stations"][0]["params"]["PM2.5"]["freshness"] == "STALE"


def test_latest_air_quality_handles_multiple_stations():
    rows = [
        _measurement(station_id="38", source_record_id="a"),
        _measurement(station_id="99", station_name="Other station", source_record_id="b"),
    ]
    client = _client_with_rows(rows)

    body = client.get("/api/v1/air/latest").json()

    assert {s["station_id"] for s in body["stations"]} == {"38", "99"}


def test_latest_air_quality_groups_multiple_params_per_station():
    rows = [
        _measurement(param_code="PM2.5", value=11.5, source_record_id="a"),
        _measurement(param_code="PM10", value=20.0, unit="µg/m³", source_record_id="b"),
        _measurement(param_code="CO", value=0.3, unit="µg/m³", source_record_id="c"),
    ]
    client = _client_with_rows(rows)

    body = client.get("/api/v1/air/latest").json()

    assert len(body["stations"]) == 1
    params = body["stations"][0]["params"]
    assert set(params) == {"PM2.5", "PM10", "CO"}
    assert params["CO"]["value"] == 0.3
    assert params["CO"]["unit"] == "µg/m³"


def test_latest_air_quality_query_filters_by_gios_source():
    # Codex review: `measurements` is shared with imgw_hydro (water_level_cm) —
    # a regression here would silently show river gauges as air stations.
    # FakeSession ignores the stmt's WHERE clause (no real Postgres here), so this
    # inspects the WHERE clause directly rather than round-tripping through rows.
    # (Only the whereclause is compiled, not the full DISTINCT ON select, which is
    # Postgres-dialect-only and can't compile with the generic/default dialect.)
    from app.db import get_db
    from app.main import app

    captured = {}

    class _CapturingSession:
        def execute(self, stmt):
            captured["where"] = str(
                stmt.whereclause.compile(compile_kwargs={"literal_binds": True})
            )
            return _FakeResult([])

    app.dependency_overrides[get_db] = lambda: iter([_CapturingSession()])
    try:
        client = TestClient(app)
        client.get("/api/v1/air/latest")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert "source_id" in captured["where"] and "gios" in captured["where"]


# --- AirLatestResponse (TASK-API-1: response_model actually enforces a shape) --


def test_air_latest_response_accepts_the_real_shape():
    AirLatestResponse.model_validate(
        {
            "stations": [
                {
                    "station_id": "38",
                    "station_name": "Kłodzko, ul. Szkolna",
                    "latitude": 50.43,
                    "longitude": 16.65,
                    "params": {
                        "PM2.5": {
                            "value": 11.5,
                            "unit": "µg/m³",
                            "observed_at": "2026-09-29T12:00:00+00:00",
                            "freshness": "FRESH",
                        }
                    },
                    "source": "gios",
                }
            ]
        }
    )


def test_air_latest_response_rejects_missing_required_field():
    """Proves response_model actually enforces the shape, not just documents
    it - a station missing `station_name` must fail validation, not silently
    serialize with a null/absent key."""
    with pytest.raises(ValidationError):
        AirLatestResponse.model_validate(
            {
                "stations": [
                    {
                        "station_id": "38",
                        # station_name missing
                        "latitude": 50.43,
                        "longitude": 16.65,
                        "params": {},
                        "source": "gios",
                    }
                ]
            }
        )


def test_air_latest_response_rejects_unknown_source():
    """`source` is a closed Literal["gios"] - a typo or a future second source
    reusing this model without updating it must fail loudly, not pass through."""
    with pytest.raises(ValidationError):
        AirLatestResponse.model_validate(
            {
                "stations": [
                    {
                        "station_id": "38",
                        "station_name": "Kłodzko",
                        "latitude": 50.43,
                        "longitude": 16.65,
                        "params": {},
                        "source": "not_gios",
                    }
                ]
            }
        )
