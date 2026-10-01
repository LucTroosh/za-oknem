"""Tests for POST/DELETE /api/v1/devices (ADR-017, TASK-10.1). Real SQLite session
(StaticPool: TestClient runs sync endpoints in another thread, and a plain in-memory
SQLite gives every thread its own empty database)."""

import logging
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import Device
from app.rate_limit import RateLimiter, device_writes

TOKEN = "ExponentPushToken[abcdefghijklmnopqrstuv]"
TOKEN2 = "ExpoPushToken[zzzzzzzzzzzzzzzzzzzzzz]"


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine)

    def _override():
        session = maker()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override
    device_writes.reset()
    c = TestClient(app)
    c.maker = maker  # type: ignore[attr-defined]
    yield c
    app.dependency_overrides.pop(get_db, None)
    device_writes.reset()
    engine.dispose()


def _body(**overrides):
    body = {"installation_id": str(uuid.uuid4()), "platform": "android", "push_token": TOKEN}
    body.update(overrides)
    return body


def _register(client, **overrides):
    body = _body(**overrides)
    return body, client.post("/api/v1/devices", json=body)


def _row(client, installation_id) -> Device:
    with client.maker() as s:
        return s.execute(
            select(Device).where(Device.installation_id == installation_id)
        ).scalar_one()


def test_register_creates_device_and_returns_secret_once(client):
    body, r = _register(client, observed_area_code="0208011", app_version="1.0.0")
    assert r.status_code == 201
    data = r.json()
    assert data["push_registered"] is True
    assert data["observed_area_code"] == "0208011"
    assert data["active"] is True
    assert len(data["device_secret"]) >= 40
    assert r.headers["cache-control"] == "no-store"
    assert "push_token" not in data
    row = _row(client, body["installation_id"])
    assert row.push_token == TOKEN
    # only the hash is stored
    assert row.secret_hash != data["device_secret"]
    assert len(row.secret_hash) == 64


def test_register_again_with_secret_is_idempotent_update(client):
    body, r = _register(client)
    secret = r.json()["device_secret"]
    h = {"X-Device-Secret": secret}
    r2 = client.post("/api/v1/devices", json=body, headers=h)
    assert r2.status_code == 200
    assert r2.json()["device_secret"] is None
    with client.maker() as s:
        assert len(s.execute(select(Device)).scalars().all()) == 1


def test_update_token_and_area_partial_fields(client):
    body, r = _register(client, observed_area_code="0208011")
    h = {"X-Device-Secret": r.json()["device_secret"]}
    # token refresh only: omitted observed_area_code stays
    r2 = client.post(
        "/api/v1/devices",
        json={
            "installation_id": body["installation_id"],
            "platform": "android",
            "push_token": TOKEN2,
        },
        headers=h,
    )
    assert r2.status_code == 200
    row = _row(client, body["installation_id"])
    assert row.push_token == TOKEN2
    assert row.observed_area_code == "0208011"
    # explicit null clears the token
    client.post(
        "/api/v1/devices",
        json={
            "installation_id": body["installation_id"],
            "platform": "android",
            "push_token": None,
        },
        headers=h,
    )
    assert _row(client, body["installation_id"]).push_token is None


def test_existing_device_without_or_with_wrong_secret_is_403_and_unchanged(client):
    body, _ = _register(client)
    for headers in ({}, {"X-Device-Secret": "wrong"}):
        r = client.post("/api/v1/devices", json={**body, "push_token": TOKEN2}, headers=headers)
        assert r.status_code == 403
        assert "device_secret" not in r.text
    assert _row(client, body["installation_id"]).push_token == TOKEN


def test_token_moves_to_new_installation(client):
    old, _ = _register(client)
    new, r = _register(client)  # same TOKEN, reinstall -> new installation_id
    assert r.status_code == 201
    assert _row(client, old["installation_id"]).push_token is None
    assert _row(client, new["installation_id"]).push_token == TOKEN


@pytest.mark.parametrize(
    "token",
    [
        "abc",
        "ExponentPushToken[]",
        "ExponentPushToken[a b]",
        "OtherPushToken[abc]",
        "ExponentPushToken[abc]x",
        "ExponentPushToken[" + "a" * 300 + "]",
    ],
)
def test_bad_push_token_is_422(client, token):
    _, r = _register(client, push_token=token)
    assert r.status_code == 422


@pytest.mark.parametrize(
    "overrides",
    [
        {"installation_id": "short"},
        {"installation_id": "x" * 65},
        {"installation_id": "a" * 31 + "!"},
        {"platform": "windows"},
        {"observed_area_code": "abc"},
        {"observed_area_code": "123"},
        {"observed_area_code": "12345678"},
        {"app_version": "1" * 33},
        {"latitude": 50.43, "longitude": 16.65},
    ],
)
def test_invalid_fields_are_422(client, overrides):
    _, r = _register(client, **overrides)
    assert r.status_code == 422


def test_registration_without_push_token_is_allowed(client):
    body = {"installation_id": str(uuid.uuid4()), "platform": "ios"}
    r = client.post("/api/v1/devices", json=body)
    assert r.status_code == 201
    assert r.json()["push_registered"] is False


def test_delete_deactivates_and_is_idempotent(client):
    body, r = _register(client, observed_area_code="0208011")
    h = {"X-Device-Secret": r.json()["device_secret"]}
    url = f"/api/v1/devices/{body['installation_id']}"
    assert client.delete(url, headers=h).status_code == 204
    assert client.delete(url, headers=h).status_code == 204
    row = _row(client, body["installation_id"])
    assert row.active is False
    assert row.push_token is None
    assert row.observed_area_code is None
    # the same installation may register again with its secret
    r2 = client.post("/api/v1/devices", json=body, headers=h)
    assert r2.status_code == 200
    assert r2.json()["active"] is True


def test_delete_foreign_or_unknown_device_is_indistinguishable_404(client):
    body, _ = _register(client)
    foreign = client.delete(
        f"/api/v1/devices/{body['installation_id']}", headers={"X-Device-Secret": "nope"}
    )
    nosecret = client.delete(f"/api/v1/devices/{body['installation_id']}")
    unknown = client.delete(f"/api/v1/devices/{uuid.uuid4()}", headers={"X-Device-Secret": "nope"})
    assert foreign.status_code == nosecret.status_code == unknown.status_code == 404
    assert foreign.json() == unknown.json()
    assert _row(client, body["installation_id"]).active is True


def test_secret_and_token_never_logged(client, caplog):
    with caplog.at_level(logging.DEBUG):
        body, r = _register(client)
        secret = r.json()["device_secret"]
        client.delete(
            f"/api/v1/devices/{body['installation_id']}", headers={"X-Device-Secret": secret}
        )
    assert secret not in caplog.text
    assert TOKEN not in caplog.text


def test_rate_limit_returns_429_with_retry_after(client, monkeypatch):
    monkeypatch.setattr(device_writes, "limit", 2)
    assert _register(client)[1].status_code == 201
    assert _register(client)[1].status_code == 201
    _, r = _register(client)
    assert r.status_code == 429
    assert int(r.headers["retry-after"]) >= 1


def test_rate_limiter_window_expires_and_keys_are_independent(monkeypatch):
    now = [100.0]
    monkeypatch.setattr("app.rate_limit.time.monotonic", lambda: now[0])
    limiter = RateLimiter(limit=1, window_seconds=10)
    limiter.check("a")
    limiter.check("b")
    with pytest.raises(Exception) as exc:
        limiter.check("a")
    assert exc.value.status_code == 429  # type: ignore[attr-defined]
    now[0] += 10.1
    limiter.check("a")


def test_rate_limiter_key_count_stays_bounded(monkeypatch):
    monkeypatch.setattr("app.rate_limit.MAX_KEYS", 5)
    limiter = RateLimiter(limit=10, window_seconds=60)
    for i in range(50):
        limiter.check(f"ip{i}")
    assert len(limiter._hits) <= 5


def test_expired_keys_are_dropped_without_reaching_the_cap(monkeypatch):
    now = [100.0]
    monkeypatch.setattr("app.rate_limit.time.monotonic", lambda: now[0])
    limiter = RateLimiter(limit=5, window_seconds=10)
    limiter.check("one-off-ip")
    now[0] += 11
    limiter.check("other")
    assert "one-off-ip" not in limiter._hits


def test_flush_integrity_error_is_409_not_500(client, monkeypatch):
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.orm import Session

    def boom(self, *a, **k):
        if self.new:  # only the INSERT of the new Device, not the empty autoflush
            raise IntegrityError("stmt", {}, Exception("dup"))

    monkeypatch.setattr(Session, "flush", boom)
    _, r = _register(client)
    assert r.status_code == 409


class _PgError(Exception):
    def __init__(self, sqlstate):
        self.sqlstate = sqlstate


def _patch_flush_operational_error(monkeypatch, orig):
    from sqlalchemy.exc import OperationalError
    from sqlalchemy.orm import Session

    def boom(self, *a, **k):
        if self.new:
            raise OperationalError("stmt", {}, orig)

    monkeypatch.setattr(Session, "flush", boom)


@pytest.mark.parametrize("sqlstate", ["40P01", "40001"])
def test_deadlock_or_serialization_failure_is_409(client, monkeypatch, sqlstate):
    _patch_flush_operational_error(monkeypatch, _PgError(sqlstate))
    assert _register(client)[1].status_code == 409


@pytest.mark.parametrize("orig", [_PgError("08006"), _PgError(None), Exception("timeout")])
def test_other_operational_error_is_not_409(client, monkeypatch, orig):
    _patch_flush_operational_error(monkeypatch, orig)
    c = TestClient(app, raise_server_exceptions=False)
    r = c.post("/api/v1/devices", json=_body())
    assert r.status_code == 500


def test_wrong_secret_does_not_steal_third_devices_token(client):
    third, _ = _register(client, push_token=TOKEN2)
    victim, _ = _register(client, push_token=TOKEN)
    r = client.post(
        "/api/v1/devices", json={**victim, "push_token": TOKEN2}, headers={"X-Device-Secret": "x"}
    )
    assert r.status_code == 403
    assert _row(client, third["installation_id"]).push_token == TOKEN2
    assert _row(client, victim["installation_id"]).push_token == TOKEN


def test_null_token_keeps_observed_area(client):
    body, r = _register(client, observed_area_code="0208011")
    client.post(
        "/api/v1/devices",
        json={
            "installation_id": body["installation_id"],
            "platform": "android",
            "push_token": None,
        },
        headers={"X-Device-Secret": r.json()["device_secret"]},
    )
    row = _row(client, body["installation_id"])
    assert row.push_token is None
    assert row.observed_area_code == "0208011"


def test_reactivation_after_delete_applies_new_fields(client):
    body, r = _register(client, observed_area_code="0208011")
    h = {"X-Device-Secret": r.json()["device_secret"]}
    client.delete(f"/api/v1/devices/{body['installation_id']}", headers=h)
    r2 = client.post(
        "/api/v1/devices",
        json={**body, "push_token": TOKEN2, "observed_area_code": "1465011", "platform": "ios"},
        headers=h,
    )
    assert r2.status_code == 200
    row = _row(client, body["installation_id"])
    assert (row.active, row.push_token, row.observed_area_code, row.platform) == (
        True,
        TOKEN2,
        "1465011",
        "ios",
    )


def test_delete_rate_limit_has_retry_after(client, monkeypatch):
    monkeypatch.setattr(device_writes, "limit", 1)
    r = client.delete(f"/api/v1/devices/{uuid.uuid4()}")
    assert r.status_code == 404
    r = client.delete(f"/api/v1/devices/{uuid.uuid4()}")
    assert r.status_code == 429
    assert int(r.headers["retry-after"]) >= 1
