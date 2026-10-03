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
from app.models import Alert, GeoArea, SourceStatus


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, rows, statuses=None, areas=None):
        self._rows = rows
        self._statuses = statuses or {}
        self._areas = areas or {}

    def execute(self, _stmt):
        return _FakeResult(self._rows)

    def get(self, model, key):
        if model is GeoArea:
            return self._areas.get(key)
        return self._statuses.get(key)


def _client_with_rows(rows: list[Alert], statuses=None, areas=None) -> TestClient:
    def _override():
        yield _FakeSession(rows, statuses, areas)

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
            "geo_match": None,
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
    "geo_match": None,
}


_VALID_SOURCE_STATUS = {
    "imgw_warningshydro": {"freshness": "FRESH", "last_success_at": "2026-09-29T12:00:00+00:00"}
}


def _envelope(alert: dict) -> dict:
    # Valid source_status everywhere, so rejection tests fail on the alert field
    # they target, not on a missing envelope key.
    return {"alerts": [alert], "source_status": _VALID_SOURCE_STATUS}


def test_alerts_latest_response_accepts_the_real_shape():
    AlertsLatestResponse.model_validate(_envelope(_VALID_ALERT_OUT))


def test_alerts_latest_response_rejects_missing_required_field():
    bad = {**_VALID_ALERT_OUT}
    del bad["event_type"]
    with pytest.raises(ValidationError):
        AlertsLatestResponse.model_validate(_envelope(bad))


def test_alerts_latest_response_accepts_null_comment_and_probability():
    """comment/probability_pct are genuinely nullable in the DB model (not every
    source reports them) - must not be tightened into required fields."""
    row = {**_VALID_ALERT_OUT, "comment": None, "probability_pct": None}
    AlertsLatestResponse.model_validate(_envelope(row))


def test_alerts_latest_response_rejects_unknown_freshness():
    bad = {**_VALID_ALERT_OUT, "freshness": "ANCIENT"}
    with pytest.raises(ValidationError):
        AlertsLatestResponse.model_validate(_envelope(bad))


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


def test_alerts_latest_response_rejects_unknown_source_freshness():
    with pytest.raises(ValidationError):
        AlertsLatestResponse.model_validate(
            {
                "alerts": [],
                "source_status": {
                    "imgw_warningshydro": {"freshness": "MAYBE", "last_success_at": None}
                },
            }
        )


# --- ?geo_area_id= (ADR-013): deterministic TERYT-prefix matching --------------------

_WIELKOPOLSKIE = _alert(external_id="w", areas=[{"wojewodztwo": "wielkopolskie"}])
_DOLNOSLASKIE = _alert(external_id="d", areas=[{"wojewodztwo": "dolnośląskie"}])


def _area(teryt: str | None) -> dict:
    return {7: GeoArea(id=7, slug="x", name="X", latitude=0.0, longitude=0.0, teryt_code=teryt)}


def _matched(teryt: str | None, rows: list[Alert]) -> list[tuple[str, str | None]]:
    client = _client_with_rows(rows, areas=_area(teryt))
    body = client.get("/api/v1/alerts/latest?geo_area_id=7").json()
    return [(a["external_id"], a["geo_match"]) for a in body["alerts"]]


def test_area_in_alerted_voivodeship_matches():
    # gmina 3064011 (Poznań) lies in wielkopolskie (30); 0201011 is under dolnośląskie (02)
    rows = [_WIELKOPOLSKIE, _DOLNOSLASKIE]
    assert _matched("3064011", rows) == [("w", "voivodeship")]
    assert _matched("0201011", rows) == [("d", "voivodeship")]


def test_area_outside_every_alerted_voivodeship_gets_nothing():
    assert _matched("1465011", [_WIELKOPOLSKIE, _DOLNOSLASKIE]) == []  # Warszawa, mazowieckie


def test_alert_listing_several_voivodeships_matches_any_of_them():
    row = _alert(external_id="m", areas=[{"wojewodztwo": "opolskie"}, {"wojewodztwo": "Śląskie "}])
    assert _matched("2469011", [row]) == [("m", "voivodeship")]  # name case/space-insensitive
    assert _matched("1465011", [row]) == []


def test_unmappable_alert_area_is_shown_as_unresolved_never_hidden():
    # rule #10: safety data we cannot place stays visible, flagged - not silently dropped
    row = _alert(external_id="u", areas=[{"wojewodztwo": "Kraina Deszczowców"}])
    assert _matched("1465011", [row]) == [("u", "unresolved")]
    assert _matched("1465011", [_alert(external_id="e", areas=[])]) == [("e", "unresolved")]


def test_partly_unresolved_alert_still_matches_by_its_resolved_voivodeship():
    row = _alert(external_id="p", areas=[{"wojewodztwo": "?"}, {"wojewodztwo": "wielkopolskie"}])
    assert _matched("3064011", [row]) == [("p", "voivodeship")]
    assert _matched("1465011", [row]) == [("p", "unresolved")]  # the "?" part could be anywhere


def test_area_without_teryt_gets_every_alert_flagged_unresolved():
    # seed city not yet linked to an imported boundary (ADR-019): we cannot decide
    rows = [_WIELKOPOLSKIE, _DOLNOSLASKIE]
    assert _matched(None, rows) == [("w", "unresolved"), ("d", "unresolved")]


def test_unknown_area_is_404():
    client = _client_with_rows([_WIELKOPOLSKIE], areas={})
    assert client.get("/api/v1/alerts/latest?geo_area_id=999").status_code == 404


def test_without_geo_area_id_the_list_stays_national_and_unmatched():
    client = _client_with_rows([_WIELKOPOLSKIE, _DOLNOSLASKIE])
    body = client.get("/api/v1/alerts/latest").json()
    assert [(a["external_id"], a["geo_match"]) for a in body["alerts"]] == [
        ("w", None),
        ("d", None),
    ]


@pytest.fixture(autouse=True)
def _legacy_hydro_publication(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "imgw_hydro_publication_enabled", True)
