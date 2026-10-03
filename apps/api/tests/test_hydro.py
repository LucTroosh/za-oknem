"""Tests for GET /api/v1/hydro/latest: same fake-session pattern as test_air.py
(DISTINCT ON isn't SQLite-compatible - see that file's docstring for why)."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.v1.dashboard import IMGW_ATTRIBUTION
from app.api.v1.hydro import (
    FRESH_MAX_AGE,
    RECENT_MAX_AGE,
    HydroLatestResponse,
    compute_status,
    freshness,
)
from app.db import get_db
from app.main import app
from app.models import Measurement, SourceStatus


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, rows, statuses=None):
        self._rows = rows
        self._statuses = statuses or {}

    def execute(self, _stmt):
        return _FakeResult(self._rows)

    def get(self, _model, key):
        return self._statuses.get(key)


def _client_with_rows(rows: list[Measurement], statuses=None) -> TestClient:
    def _override():
        yield _FakeSession(rows, statuses)

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
    body = response.json()
    assert body["stations"] == []
    # Never fetched -> UNAVAILABLE, so a client can't read [] as "all clear".
    assert body["source_status"] == {"freshness": "UNAVAILABLE", "last_success_at": None}


def test_latest_hydro_shapes_response_from_rows():
    """No threshold rows for this station - status is UNKNOWN, not NORMAL,
    because we have no published threshold to compare against (rule #10)."""
    row = _reading(observed_at=datetime.now(UTC))
    client = _client_with_rows([row])

    body = client.get("/api/v1/hydro/latest").json()

    assert body["attribution"] == IMGW_ATTRIBUTION
    assert body.pop("source_status")["freshness"] == "UNAVAILABLE"
    del body["attribution"]
    assert body.pop("publication_enabled") is True
    assert body == {
        "stations": [
            {
                "station_id": "151140030",
                "station_name": "Przewoźniki (Skroda)",
                "latitude": 51.5253,
                "longitude": 14.8217,
                "water_level_cm": 225.0,
                "warning_level_cm": None,
                "alarm_level_cm": None,
                "status": "UNKNOWN",
                "unit": "cm",
                "observed_at": row.observed_at.isoformat(),
                "freshness": "FRESH",
                "source": "imgw_hydro",
            }
        ]
    }


def test_latest_hydro_includes_thresholds_and_status():
    observed_at = datetime.now(UTC)
    rows = [
        _reading(observed_at=observed_at, param_code="water_level_warn_cm", value=300.0),
        _reading(observed_at=observed_at, param_code="water_level_alarm_cm", value=340.0),
        _reading(observed_at=observed_at, value=225.0),
    ]
    client = _client_with_rows(rows)

    body = client.get("/api/v1/hydro/latest").json()

    station = body["stations"][0]
    assert station["warning_level_cm"] == 300.0
    assert station["alarm_level_cm"] == 340.0
    assert station["status"] == "NORMAL"


def test_latest_hydro_ignores_threshold_only_station():
    """A station with thresholds stored but no current water-level reading must
    not appear (matches the pre-existing "no reading = not shown" behaviour)."""
    row = _reading(param_code="water_level_warn_cm", value=300.0)
    client = _client_with_rows([row])

    body = client.get("/api/v1/hydro/latest").json()

    assert body["stations"] == []


def test_latest_hydro_uses_threshold_even_when_older_than_the_reading():
    """A threshold's own observed_at (our fetch clock, per parser.py) can lag
    behind the water level's (the source's own reading clock) - that's expected,
    not staleness. ingest.py's upsert/delete keeps exactly one row per threshold,
    always reflecting IMGW's current value, so the endpoint trusts it as-is
    without comparing timestamps across param codes (Codex review, PR #42
    round 3 - the earlier observed_at-equality gate was itself the bug)."""
    earlier = datetime.now(UTC) - timedelta(hours=3)
    now = datetime.now(UTC)
    rows = [
        _reading(observed_at=earlier, param_code="water_level_warn_cm", value=300.0),
        _reading(observed_at=now, value=225.0),
    ]
    client = _client_with_rows(rows)

    body = client.get("/api/v1/hydro/latest").json()

    station = body["stations"][0]
    assert station["warning_level_cm"] == 300.0
    assert station["status"] == "NORMAL"


def test_compute_status_normal_below_warning():
    assert compute_status(100.0, warning=300.0, alarm=340.0) == "NORMAL"


def test_compute_status_warning_at_threshold():
    assert compute_status(300.0, warning=300.0, alarm=340.0) == "WARNING"


def test_compute_status_alarm_at_threshold():
    assert compute_status(340.0, warning=300.0, alarm=340.0) == "ALARM"


def test_compute_status_unknown_without_thresholds():
    assert compute_status(225.0, warning=None, alarm=None) == "UNKNOWN"


# --- source_status (ADR-012) --------------------------------------------------


def _status(last_success_hours_ago: float) -> SourceStatus:
    now = datetime.now(UTC)
    return SourceStatus(
        source_id="imgw_hydro",
        last_attempt_at=now,
        last_success_at=now - timedelta(hours=last_success_hours_ago),
    )


def test_hydro_source_status_fresh_after_recent_successful_fetch():
    client = _client_with_rows([_reading()], {"imgw_hydro": _status(0.5)})

    body = client.get("/api/v1/hydro/latest").json()

    assert body["source_status"]["freshness"] == "FRESH"


def test_hydro_source_status_stale_after_old_last_success():
    client = _client_with_rows([], {"imgw_hydro": _status(12)})

    body = client.get("/api/v1/hydro/latest").json()

    assert body["source_status"]["freshness"] == "STALE"


def test_hydro_latest_response_requires_attribution_and_source_status():
    with pytest.raises(ValidationError):
        HydroLatestResponse.model_validate({"stations": []})


# --- HydroLatestResponse (TASK-API-3: response_model enforces a shape) --------


def test_hydro_latest_response_rejects_missing_required_field():
    with pytest.raises(ValidationError):
        HydroLatestResponse.model_validate(
            {
                "stations": [
                    {
                        "station_id": "150190130",
                        # station_name missing
                        "latitude": 50.43,
                        "longitude": 16.65,
                        "water_level_cm": 120.0,
                        "warning_level_cm": None,
                        "alarm_level_cm": None,
                        "status": "UNKNOWN",
                        "unit": "cm",
                        "observed_at": "2026-09-29T12:00:00+00:00",
                        "freshness": "FRESH",
                        "source": "imgw_hydro",
                    }
                ]
            }
        )


def test_hydro_latest_response_rejects_unknown_status():
    with pytest.raises(ValidationError):
        HydroLatestResponse.model_validate(
            {
                "stations": [
                    {
                        "station_id": "150190130",
                        "station_name": "Test",
                        "latitude": 50.43,
                        "longitude": 16.65,
                        "water_level_cm": 120.0,
                        "warning_level_cm": None,
                        "alarm_level_cm": None,
                        "status": "not_a_real_status",
                        "unit": "cm",
                        "observed_at": "2026-09-29T12:00:00+00:00",
                        "freshness": "FRESH",
                        "source": "imgw_hydro",
                    }
                ]
            }
        )


@pytest.fixture(autouse=True)
def _legacy_hydro_publication(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "imgw_hydro_publication_enabled", True)
