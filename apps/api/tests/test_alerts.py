"""Tests for GET /api/v1/alerts/latest: fake-session pattern (real query uses a
>= comparison SQLite handles fine, but stays consistent with the other domain
endpoints so a future filter change doesn't need a different test style)."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app
from app.models import Alert


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


def _client_with_rows(rows: list[Alert]) -> TestClient:
    def _override():
        yield _FakeSession(rows)

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
    assert response.json() == {"alerts": []}


def test_latest_alerts_shapes_response_from_rows():
    row = _alert()
    client = _client_with_rows([row])

    body = client.get("/api/v1/alerts/latest").json()

    assert body == {
        "alerts": [
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
            }
        ]
    }
