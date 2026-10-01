"""Tests for the Open-Meteo pollen client: request shape, retry, on_attempt.
httpx.get is mocked - no live network."""

from unittest.mock import MagicMock

import httpx
import pytest

from app.connectors.open_meteo_pollen import client


def _ok(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = payload
    return resp


def test_returns_json_and_sends_documented_params(monkeypatch):
    mock_get = MagicMock(return_value=_ok({"ok": True}))
    monkeypatch.setattr(client.httpx, "get", mock_get)

    assert client.fetch_pollen(50.43, 16.65) == {"ok": True}

    args, kwargs = mock_get.call_args
    assert args[0] == "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = kwargs["params"]
    assert params["latitude"] == 50.43
    assert params["longitude"] == 16.65
    # Exactly the five MVP species (Master Plan §6), European domain, UTC, timeout set.
    assert params["hourly"].split(",") == [
        "alder_pollen",
        "birch_pollen",
        "grass_pollen",
        "mugwort_pollen",
        "ragweed_pollen",
    ]
    assert params["domains"] == "cams_europe"
    assert params["forecast_days"] == 4
    assert params["timezone"] == "UTC"
    assert kwargs["timeout"] is client.TIMEOUT


def test_retries_once_then_succeeds(monkeypatch):
    attempts = [httpx.RequestError("boom"), _ok({"ok": True})]
    monkeypatch.setattr(client.httpx, "get", MagicMock(side_effect=lambda *a, **k: attempts.pop(0)))
    assert client.fetch_pollen(50.43, 16.65) == {"ok": True}


def test_raises_after_two_failures_not_forever(monkeypatch):
    mock_get = MagicMock(side_effect=httpx.RequestError("down"))
    monkeypatch.setattr(client.httpx, "get", mock_get)
    with pytest.raises(client.OpenMeteoPollenApiError):
        client.fetch_pollen(50.43, 16.65)
    assert mock_get.call_count == 2  # rule #5: bounded retry


def test_non_json_body_is_wrapped(monkeypatch):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.side_effect = ValueError("not json")
    monkeypatch.setattr(client.httpx, "get", MagicMock(return_value=resp))
    with pytest.raises(client.OpenMeteoPollenApiError):
        client.fetch_pollen(50.43, 16.65)


def test_on_attempt_fires_before_each_real_request(monkeypatch):
    order: list[str] = []

    def _get(*_a, **_k):
        order.append("request")
        raise httpx.RequestError("down")

    monkeypatch.setattr(client.httpx, "get", MagicMock(side_effect=_get))
    with pytest.raises(client.OpenMeteoPollenApiError):
        client.fetch_pollen(50.43, 16.65, on_attempt=lambda: order.append("attempt"))
    assert order == ["attempt", "request", "attempt", "request"]
