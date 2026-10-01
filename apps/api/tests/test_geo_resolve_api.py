"""POST /api/v1/geo/resolve: contract, validation and the ADR-002 privacy constraint.
The point-in-polygon SQL itself is covered by tests/test_postgis_geo.py."""

import logging

import pytest
from fastapi.testclient import TestClient

import app.api.v1.geo as geo_api
from app.db import get_db
from app.geo import ResolvedArea
from app.main import app


def _client(monkeypatch, result):
    calls = []

    def _fake(_db, lat, lon):
        calls.append((lat, lon))
        return result

    monkeypatch.setattr(geo_api, "resolve_gmina", _fake)
    app.dependency_overrides[get_db] = lambda: iter([None])
    return TestClient(app), calls


def teardown_function() -> None:
    app.dependency_overrides.pop(get_db, None)


def test_match_returns_area_without_echoing_coordinates(monkeypatch):
    area = ResolvedArea(geo_area_id=3, teryt_code="9999901", slug="klodzko", name="Kłodzko")
    client, calls = _client(monkeypatch, area)

    r = client.post("/api/v1/geo/resolve", json={"latitude": 50.4335, "longitude": 16.6537})

    assert r.status_code == 200
    assert r.json() == {
        "area": {"geo_area_id": 3, "teryt_code": "9999901", "slug": "klodzko", "name": "Kłodzko"}
    }
    assert calls == [(50.4335, 16.6537)]
    assert "50.4335" not in r.text and "16.6537" not in r.text


def test_no_match_is_200_with_null_area(monkeypatch):
    client, _ = _client(monkeypatch, None)
    r = client.post("/api/v1/geo/resolve", json={"latitude": 52.52, "longitude": 13.4})
    assert r.status_code == 200
    assert r.json() == {"area": None}


@pytest.mark.parametrize(
    "body",
    [
        {"latitude": 91, "longitude": 16},
        {"latitude": 50, "longitude": 181},
        {"latitude": 50},
        {"latitude": "x", "longitude": 16},
    ],
)
def test_invalid_input_is_422_and_never_reaches_resolver(monkeypatch, body):
    client, calls = _client(monkeypatch, None)
    assert client.post("/api/v1/geo/resolve", json=body).status_code == 422
    assert calls == []


def test_get_with_query_string_is_not_supported(monkeypatch):
    # ADR-002: coordinates must not travel in a query string (access logs).
    client, _ = _client(monkeypatch, None)
    assert client.get("/api/v1/geo/resolve?latitude=50&longitude=16").status_code == 405


def test_coordinates_are_not_logged(monkeypatch, caplog):
    client, _ = _client(monkeypatch, None)
    with caplog.at_level(logging.DEBUG):
        client.post("/api/v1/geo/resolve", json={"latitude": 50.123456, "longitude": 16.654321})
    assert "50.123456" not in caplog.text and "16.654321" not in caplog.text


def test_database_error_is_503_and_leaks_no_coordinates(monkeypatch, caplog):
    from sqlalchemy.exc import OperationalError

    def _boom(_db, lat, lon):
        raise OperationalError("SELECT ...", {"lat": lat, "lon": lon}, Exception("db down"))

    monkeypatch.setattr(geo_api, "resolve_gmina", _boom)
    app.dependency_overrides[get_db] = lambda: iter([None])
    client = TestClient(app, raise_server_exceptions=False)

    with caplog.at_level(logging.DEBUG):
        r = client.post("/api/v1/geo/resolve", json={"latitude": 50.123456, "longitude": 16.654321})

    assert r.status_code == 503
    assert "50.123456" not in caplog.text and "16.654321" not in caplog.text
    assert "50.123456" not in r.text


def test_422_does_not_echo_coordinates(monkeypatch):
    client, _ = _client(monkeypatch, None)
    r = client.post("/api/v1/geo/resolve", json={"latitude": 91.234567, "longitude": 16})
    assert r.status_code == 422
    assert "91.234567" not in r.text
