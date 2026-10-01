"""TASK-13.1: per-source health report, error sanitizing, transition logging."""

import logging
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import GeoArea, SourceFetchCounter, SourceStatus
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


def test_fallback_entry_keeps_monitored_flag(db_session, monkeypatch):
    import app.source_health as sh

    db_session.add(GeoArea(slug="k", name="k", latitude=50.0, longitude=16.0))
    db_session.commit()

    monkeypatch.delenv("GIOS_STATION_IDS", raising=False)
    monkeypatch.setattr(sh, "_source_health", MagicMock(side_effect=RuntimeError("db gone")))

    report = collect_source_health(db_session)
    by_id = _by_id(report)

    assert by_id["gios"]["monitored"] is False
    assert by_id["open_meteo"]["monitored"] is True
    assert log_health_transitions(report, {}).keys() == set(SOURCES) - {"gios"}


def test_sanitize_error_strips_query_secrets_and_truncates():
    raw = (
        "ConnectionError: HTTPSConnectionPool: url: /v1?apikey=SECRET123&x=1 "
        "Authorization: Bearer abc.def token=xyz"
    )

    out = sanitize_error(raw)

    assert "SECRET123" not in out and "abc.def" not in out and "xyz" not in out
    assert out.startswith("ConnectionError: HTTPSConnectionPool")
    assert sanitize_error("HTTP 429 from https://u:p@host/x?a=b rate limited") == (
        "HTTP 429 from https://[redacted]@host/x rate limited"
    )
    assert len(sanitize_error("x " * 1000)) == 200


@pytest.mark.parametrize(
    "raw",
    [
        "KeyError: 'current'",
        "HTTP 401 Unauthorized",
        "RuntimeError: Open-Meteo: 2/3 failed; last cause: KeyError: 'current'",
        "GIOS: 0/5 failed",
        "keyboard layout error",
    ],
)
def test_sanitize_error_keeps_diagnostics(raw):
    assert sanitize_error(raw) == raw


def test_sanitize_error_masks_ips_hosts_and_opaque_tokens():
    out = sanitize_error("could not connect to server at 10.0.3.7, port 5432 or db.internal:5432")
    assert "10.0.3.7" not in out and "db.internal" not in out
    v6 = sanitize_error(
        "connection to [fd00::12]:5432 failed; also fe80::1 and 2001:db8:0:0:0:0:0:1"
    )
    assert "fd00" not in v6 and "fe80" not in v6 and "2001:db8" not in v6
    assert sanitize_error("failed at 2026-09-30 12:30:00 on Foo::bar") == (
        "failed at 2026-09-30 12:30:00 on Foo::bar"
    )
    assert "sk-abcdef123456" not in sanitize_error("rejected sk-abcdef123456 by upstream")


@pytest.mark.parametrize(
    "raw,secret",
    [
        ('{"token": "abc123"}', "abc123"),
        ("failed access_token=abc123", "abc123"),
        ("client_secret=xyz789 rejected", "xyz789"),
        ("header x_api_key: k9k9k9", "k9k9k9"),
        ("https://user:pw0rd@host/x unreachable", "pw0rd"),
        ("password is wrong, key=abc777", "abc777"),
        ("Authorization: Bearer tok.en.val", "tok.en.val"),
        ("Authorization: Basic dXNlcjpwYXNz", "dXNlcjpwYXNz"),
        ("Proxy-Authorization: Token t0k3n9", "t0k3n9"),
        ('password="correct horse battery staple"', "battery"),
        ('password="correct horse battery staple', "battery"),
        ("secret='alpha beta gamma", "gamma"),
        ('{"client_secret": "alpha beta gamma"}', "gamma"),
        ("Authorization header: Basic dXNlcjpwYXNz", "dXNlcjpwYXNz"),
        ("API key value: sk-live-777", "sk-live-777"),
        ("password is hunter2", "hunter2"),
        ("the key was abc123xyz", "abc123xyz"),
        ("private key is s3cr3tval", "s3cr3tval"),
        ("pwd=hunter9", "hunter9"),
        ("passphrase: open sesame", "sesame"),
        ("key: topsecretval", "topsecretval"),
        ("Authentication: Bearer secret123", "secret123"),
        ("auth_header='Bearer secret456'", "secret456"),
        ("retry with Bearer abc789 failed", "abc789"),
        (
            "Authorization: AWS4-HMAC-SHA256 Credential=AKID123/x, SignedHeaders=host, "
            "Signature=SIG456",
            "SIG456",
        ),
    ],
)
def test_sanitize_error_redacts_credential_shapes(raw, secret):
    assert secret not in sanitize_error(raw)


def test_health_session_close_failure_is_swallowed(monkeypatch):
    import app.api.v1.health as health_module

    session = MagicMock()
    session.close.side_effect = RuntimeError("dead conn")
    monkeypatch.setattr(health_module, "SessionLocal", lambda: session)

    gen = health_module.get_db_guarded()
    assert next(gen) is session
    with pytest.raises(StopIteration):
        next(gen)  # teardown ran, close() failure did not propagate


def test_sanitize_error_is_fast_on_pathological_input():
    import time

    start = time.monotonic()
    sanitize_error("-" * 200_000 + "key")
    assert time.monotonic() - start < 1
    assert sanitize_error(None) is None and sanitize_error("") is None


def _entry(source_id, state, monitored=True):
    return {
        "source_id": source_id,
        "freshness": state,
        "last_success_at": None,
        "last_error": "e",
        "monitored": monitored,
    }


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


def test_run_failure_reason_policy():
    from app.source_status import run_failure_reason as reason

    assert reason(0, 0, max_failed_fraction=0.02) == "nothing returned"
    assert reason(1, 1, max_failed_fraction=0.5) == "1/1 failed"  # no success at all
    assert reason(100, 2, max_failed_fraction=0.02) is None
    assert reason(100, 3, max_failed_fraction=0.02) == "3/100 failed"
    assert reason(4, 2, max_failed_fraction=0.5) is None  # small sets: only a majority fails


def test_unmonitored_source_is_never_logged(caplog):
    state = log_health_transitions([_entry("gios", "UNAVAILABLE", monitored=False)], {})

    assert caplog.records == [] and state == {}


def test_gios_without_station_ids_is_reported_unmonitored(db_session, monkeypatch):
    monkeypatch.delenv("GIOS_STATION_IDS", raising=False)
    by_id = _by_id(collect_source_health(db_session))
    assert by_id["gios"]["monitored"] is False and by_id["open_meteo"]["monitored"] is False
    db_session.add(GeoArea(slug="k", name="k", latitude=50.0, longitude=16.0))
    db_session.commit()
    assert _by_id(collect_source_health(db_session))["open_meteo"]["monitored"] is True

    monkeypatch.setenv("GIOS_STATION_IDS", " \t\n ,  ")  # same parsing as the scheduler
    assert _by_id(collect_source_health(db_session))["gios"]["monitored"] is False

    monkeypatch.setenv("GIOS_STATION_IDS", "38")
    assert _by_id(collect_source_health(db_session))["gios"]["monitored"] is True


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
            "monitored": True,
        },
        {
            "source_id": "open_meteo",
            "freshness": "FRESH",
            "last_attempt_at": None,
            "last_success_at": None,
            "last_error": None,
            "daily_budget": {"used": 5, "limit": 10, "used_pct": 50.0},
            "monitored": True,
        },
    ]
    monkeypatch.setattr(health_module, "collect_source_health", lambda db: canned)
    app.dependency_overrides[health_module.get_db_guarded] = lambda: iter([object()])
    try:
        client = TestClient(app)
        response = client.get("/api/v1/health/sources")
        liveness = client.get("/api/v1/health")
    finally:
        app.dependency_overrides.pop(health_module.get_db_guarded, None)

    assert liveness.json() == {"status": "ok"}
    assert response.status_code == 200
    body = response.json()
    assert body["sources"] == canned
    assert "generated_at" in body
