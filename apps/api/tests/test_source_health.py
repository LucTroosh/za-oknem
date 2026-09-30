"""TASK-13.1: per-source health report, error sanitizing, transition logging."""

import logging
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app
from app.models import SourceFetchCounter, SourceStatus
from app.source_health import (
    SOURCES,
    collect_source_health,
    log_health_transitions,
    sanitize_error,
)
from app.source_status import record_source_run


def _by_id(report):
    return {e["source_id"]: e for e in report}


def _set_success(db, source_id, age):
    now = datetime.now(UTC)
    db.add(SourceStatus(source_id=source_id, last_attempt_at=now, last_success_at=now - age))
    db.commit()


def test_reports_every_known_source_unavailable_when_never_fetched(db_session):
    report = collect_source_health(db_session)

    assert [e["source_id"] for e in report] == list(SOURCES)
    assert {e["freshness"] for e in report} == {"UNAVAILABLE"}
    assert all(e["last_success_at"] is None for e in report)


def test_failed_runs_only_stay_unavailable_and_expose_sanitized_error(db_session):
    record_source_run(db_session, "gios", success=False, error="ConnectionError: boom")

    entry = _by_id(collect_source_health(db_session))["gios"]

    assert entry["freshness"] == "UNAVAILABLE"
    assert entry["last_error"] == "ConnectionError: boom"
    assert entry["last_attempt_at"] is not None


def test_thresholds_are_per_source_from_their_domain(db_session):
    # 5h: past open_meteo's 4h FRESH (3h ICON cycle) yet within its 8h RECENT, and
    # RECENT for hourly gios (2h/6h). 7h: STALE for hourly hydro (6h RECENT limit).
    _set_success(db_session, "open_meteo", timedelta(hours=5))
    _set_success(db_session, "gios", timedelta(hours=5))
    _set_success(db_session, "imgw_hydro", timedelta(hours=7))
    _set_success(db_session, "imgw_warningshydro", timedelta(minutes=30))

    states = {e["source_id"]: e["freshness"] for e in collect_source_health(db_session)}

    assert states == {
        "open_meteo": "RECENT",
        "gios": "RECENT",
        "imgw_hydro": "STALE",
        "imgw_warningshydro": "FRESH",
    }


def test_daily_budget_only_for_sources_with_a_documented_limit(db_session):
    db_session.add(
        SourceFetchCounter(source_id="open_meteo", day=datetime.now(UTC).date(), count=2500)
    )
    db_session.commit()

    by_id = _by_id(collect_source_health(db_session))

    assert by_id["open_meteo"]["daily_budget"] == {"used": 2500, "limit": 10000, "used_pct": 25.0}
    assert by_id["gios"]["daily_budget"] is None


def test_budget_zero_when_no_calls_today(db_session):
    entry = _by_id(collect_source_health(db_session))["open_meteo"]

    assert entry["daily_budget"]["used"] == 0


def test_one_broken_source_does_not_break_the_report(db_session, monkeypatch):
    import app.source_health as sh

    real = sh._source_health

    def flaky(db, source_id, spec, today):
        if source_id == "gios":
            raise RuntimeError("boom")
        return real(db, source_id, spec, today)

    monkeypatch.setattr(sh, "_source_health", flaky)
    _set_success(db_session, "imgw_hydro", timedelta(minutes=1))

    by_id = _by_id(collect_source_health(db_session))

    assert by_id["gios"]["freshness"] == "UNAVAILABLE"
    assert by_id["gios"]["last_error"] == "health evaluation failed"
    assert by_id["imgw_hydro"]["freshness"] == "FRESH"


def test_rollback_failure_still_yields_full_report(db_session, monkeypatch):
    import app.source_health as sh

    monkeypatch.setattr(sh, "_source_health", MagicMock(side_effect=RuntimeError("db gone")))
    monkeypatch.setattr(db_session, "rollback", MagicMock(side_effect=RuntimeError("dead conn")))

    report = collect_source_health(db_session)

    assert [e["source_id"] for e in report] == list(SOURCES)
    assert {e["freshness"] for e in report} == {"UNAVAILABLE"}


def test_sanitize_error_strips_query_secrets_and_truncates():
    raw = (
        "ConnectionError: HTTPSConnectionPool: url: /v1?apikey=SECRET123&x=1 "
        "Authorization: Bearer abc.def token=xyz"
    )

    out = sanitize_error(raw)

    assert "SECRET123" not in out and "abc.def" not in out and "xyz" not in out
    assert "ConnectionError" in out
    assert len(sanitize_error("x" * 1000)) == 200
    assert sanitize_error(None) is None and sanitize_error("") is None


def _entry(source_id, state):
    return {"source_id": source_id, "freshness": state, "last_success_at": None, "last_error": "e"}


def test_transitions_log_once_per_state_change(caplog):
    caplog.set_level(logging.INFO, logger="app.source_health")

    state = log_health_transitions([_entry("gios", "FRESH")], {})
    assert caplog.records == []  # healthy first observation: silent

    state = log_health_transitions([_entry("gios", "STALE")], state)
    state = log_health_transitions([_entry("gios", "STALE")], state)  # next tick: no spam
    assert [r.levelno for r in caplog.records] == [logging.WARNING]

    state = log_health_transitions([_entry("gios", "UNAVAILABLE")], state)
    assert caplog.records[-1].levelno == logging.ERROR

    state = log_health_transitions([_entry("gios", "FRESH")], state)
    assert caplog.records[-1].levelno == logging.INFO and "recovered" in caplog.text
    assert len(caplog.records) == 3
    assert state == {"gios": "FRESH"}


def test_already_bad_source_is_logged_once_on_first_observation(caplog):
    log_health_transitions([_entry("imgw_hydro", "UNAVAILABLE")], {})

    assert [r.levelno for r in caplog.records] == [logging.ERROR]


def test_endpoint_reports_sources_and_leaves_liveness_alone(monkeypatch):
    # Logic is covered above on a real session; here only the wiring/contract
    # (a SQLite :memory: session can't cross TestClient's worker thread).
    import app.api.v1.health as health_module

    canned = [
        {
            "source_id": "gios",
            "freshness": "STALE",
            "last_attempt_at": "2026-09-30T10:00:00+00:00",
            "last_success_at": "2026-09-30T02:00:00+00:00",
            "last_error": "ConnectionError: boom",
            "daily_budget": None,
        },
        {
            "source_id": "open_meteo",
            "freshness": "FRESH",
            "last_attempt_at": None,
            "last_success_at": None,
            "last_error": None,
            "daily_budget": {"used": 5, "limit": 10, "used_pct": 50.0},
        },
    ]
    monkeypatch.setattr(health_module, "collect_source_health", lambda db: canned)
    app.dependency_overrides[get_db] = lambda: iter([object()])
    try:
        client = TestClient(app)
        response = client.get("/api/v1/health/sources")
        liveness = client.get("/api/v1/health")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert liveness.json() == {"status": "ok"}
    assert response.status_code == 200
    body = response.json()
    assert body["sources"] == canned
    assert "generated_at" in body
