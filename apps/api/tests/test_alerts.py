"""Tests for GET /api/v1/alerts/latest: fake-session pattern (real query uses a
>= comparison SQLite handles fine, but stays consistent with the other domain
endpoints so a future filter change doesn't need a different test style)."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.v1.alerts import AlertsLatestResponse
from app.db import get_db
from app.main import app
from app.models import Alert, SourceStatus


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


def _client_with_rows(rows: list[Alert], statuses=None) -> TestClient:
    def _override():
        yield _FakeSession(rows, statuses)

    app.dependency_overrides[get_db] = _override
    return TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.pop(get_db, None)


def _alert(**overrides) -> Alert:
    now = datetime.now(UTC)
    defaults = {
        "source_id": "imgw_warningshydro",
        "source_record_id": "31:2026-05-17T08:45:07+02:00",
        "external_id": "31",
        "event_type": "Susza hydrologiczna",
        "severity_raw": "-1",
        "probability_pct": 90.0,
        "issuing_office": "Biuro Prognoz Hydrologicznych we Wrocławiu",
        "description": "opis",
        "comment": "komentarz",
        "areas": [{"wojewodztwo": "wielkopolskie"}],
        "valid_from": now - timedelta(hours=1),
        "valid_until": now + timedelta(days=1),
        "published_at": now - timedelta(hours=1),
        "fetched_at": now,
    }
    defaults.update(overrides)
    return Alert(**defaults)


def test_latest_alerts_returns_empty_list_when_no_rows():
    client = _client_with_rows([])

    response = client.get("/api/v1/alerts/latest")

    assert response.status_code == 200
    assert response.json() == {
        "alerts": [],
        "source_status": {
            "imgw_warningshydro": {"freshness": "UNAVAILABLE", "last_success_at": None}
        },
    }


def test_latest_alerts_shapes_response_from_rows():
    row = _alert()
    client = _client_with_rows([row])

    body = client.get("/api/v1/alerts/latest").json()

    assert body["alerts"] == [
        {
            "external_id": "31",
            "source": "imgw_warningshydro",
            "event_type": "Susza hydrologiczna",
            "severity_raw": "-1",
            "probability_pct": 90.0,
            "issuing_office": "Biuro Prognoz Hydrologicznych we Wrocławiu",
            "description": "opis",
            "comment": "komentarz",
            "areas": [{"wojewodztwo": "wielkopolskie"}],
            "valid_from": row.valid_from.isoformat(),
            "valid_until": row.valid_until.isoformat(),
            "published_at": row.published_at.isoformat(),
            "fetched_at": row.fetched_at.isoformat(),
            "freshness": "FRESH",
        }
    ]


def test_latest_alerts_marks_stale_fetch_as_stale():
    # rule #8: an alert's own valid_until can read year 9999 (drought) - staleness
    # must come from how long ago we last confirmed it via fetched_at instead.
    row = _alert(fetched_at=datetime.now(UTC) - timedelta(hours=12))
    client = _client_with_rows([row])

    body = client.get("/api/v1/alerts/latest").json()

    assert body["alerts"][0]["freshness"] == "STALE"


# --- AlertsLatestResponse (TASK-API-4: response_model enforces a shape) -------

_VALID_ALERT_OUT = {
    "external_id": "31",
    "source": "imgw_warningshydro",
    "event_type": "Susza hydrologiczna",
    "severity_raw": "-1",
    "probability_pct": 90.0,
    "issuing_office": "Biuro Prognoz Hydrologicznych we Wrocławiu",
    "description": "opis",
    "comment": "komentarz",
    "areas": [{"wojewodztwo": "wielkopolskie"}],
    "valid_from": "2026-09-29T12:00:00+00:00",
    "valid_until": "2026-09-30T12:00:00+00:00",
    "published_at": "2026-09-29T11:00:00+00:00",
    "fetched_at": "2026-09-29T12:00:00+00:00",
    "freshness": "FRESH",
}


def test_alerts_latest_response_accepts_the_real_shape():
    AlertsLatestResponse.model_validate(
        {
            "alerts": [_VALID_ALERT_OUT],
            "source_status": {
                "imgw_warningshydro": {
                    "freshness": "FRESH",
                    "last_success_at": "2026-09-29T12:00:00+00:00",
                }
            },
        }
    )


def test_alerts_latest_response_rejects_missing_required_field():
    bad = {**_VALID_ALERT_OUT}
    del bad["event_type"]
    with pytest.raises(ValidationError):
        AlertsLatestResponse.model_validate({"alerts": [bad]})


def test_alerts_latest_response_accepts_null_comment_and_probability():
    """comment/probability_pct are genuinely nullable in the DB model (not every
    source reports them) - must not be tightened into required fields."""
    row = {**_VALID_ALERT_OUT, "comment": None, "probability_pct": None}
    AlertsLatestResponse.model_validate({"alerts": [row]})


def test_alerts_latest_response_rejects_unknown_freshness():
    bad = {**_VALID_ALERT_OUT, "freshness": "ANCIENT"}
    with pytest.raises(ValidationError):
        AlertsLatestResponse.model_validate({"alerts": [bad]})


# --- source_status (ADR-012) --------------------------------------------------


def test_empty_alerts_with_recent_successful_fetch_is_confirmed_zero():
    status = SourceStatus(
        source_id="imgw_warningshydro",
        last_attempt_at=datetime.now(UTC),
        last_success_at=datetime.now(UTC),
    )
    client = _client_with_rows([], {"imgw_warningshydro": status})

    body = client.get("/api/v1/alerts/latest").json()

    assert body["alerts"] == []
    assert body["source_status"]["imgw_warningshydro"]["freshness"] == "FRESH"


def test_empty_alerts_with_old_last_success_is_stale_not_all_clear():
    status = SourceStatus(
        source_id="imgw_warningshydro",
        last_attempt_at=datetime.now(UTC),
        last_success_at=datetime.now(UTC) - timedelta(hours=12),
    )
    client = _client_with_rows([], {"imgw_warningshydro": status})

    body = client.get("/api/v1/alerts/latest").json()

    assert body["source_status"]["imgw_warningshydro"]["freshness"] == "STALE"
