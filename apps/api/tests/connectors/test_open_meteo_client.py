"""Tests for the Open-Meteo HTTP client (client.py): retry + error wrapping.
httpx.get is mocked throughout — no live network (rule #7)."""

from unittest.mock import MagicMock

import httpx
import pytest

from app.connectors.open_meteo import client


def _ok_response(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = payload
    return resp


def test_fetch_weather_returns_json_on_success(monkeypatch):
    monkeypatch.setattr(client.httpx, "get", MagicMock(return_value=_ok_response({"ok": True})))
    assert client.fetch_weather(50.43, 16.65) == {"ok": True}


def test_fetch_weather_retries_once_then_succeeds(monkeypatch):
    attempts = [httpx.RequestError("boom"), _ok_response({"ok": True})]

    def _get(*a, **k):
        outcome = attempts.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(client.httpx, "get", MagicMock(side_effect=_get))
    assert client.fetch_weather(50.43, 16.65) == {"ok": True}


def test_fetch_weather_raises_after_two_failures(monkeypatch):
    monkeypatch.setattr(
        client.httpx, "get", MagicMock(side_effect=httpx.RequestError("still broken"))
    )
    with pytest.raises(client.OpenMeteoApiError):
        client.fetch_weather(50.43, 16.65)


def test_fetch_weather_passes_coordinates_and_params(monkeypatch):
    mock_get = MagicMock(return_value=_ok_response({"ok": True}))
    monkeypatch.setattr(client.httpx, "get", mock_get)
    client.fetch_weather(50.43, 16.65)
    _, kwargs = mock_get.call_args
    assert kwargs["params"]["latitude"] == 50.43
    assert kwargs["params"]["longitude"] == 16.65
    assert kwargs["params"]["current"] == client.CURRENT_PARAMS
    assert kwargs["params"]["hourly"] == client.HOURLY_PARAMS
    assert kwargs["params"]["daily"] == client.DAILY_PARAMS


def test_fetch_weather_fires_on_attempt_once_per_real_request(monkeypatch):
    monkeypatch.setattr(client.httpx, "get", MagicMock(return_value=_ok_response({"ok": True})))
    calls = []
    client.fetch_weather(50.43, 16.65, on_attempt=lambda: calls.append(1))
    assert len(calls) == 1


def test_fetch_weather_fires_on_attempt_for_every_attempt_even_on_final_failure(monkeypatch):
    monkeypatch.setattr(
        client.httpx, "get", MagicMock(side_effect=httpx.RequestError("still broken"))
    )
    calls = []
    with pytest.raises(client.OpenMeteoApiError):
        client.fetch_weather(50.43, 16.65, on_attempt=lambda: calls.append(1))
    assert len(calls) == 2


def test_fetch_weather_fires_on_attempt_before_the_request_goes_out(monkeypatch):
    # Codex review [P1]: a reservation made before the request, not after it
    # returns - a crash mid-request must not lose the counter update for an
    # attempt Open-Meteo may already have processed (and billed).
    order = []

    def _fake_get(*_a, **_k):
        order.append("request")
        return _ok_response({"ok": True})

    monkeypatch.setattr(client.httpx, "get", MagicMock(side_effect=_fake_get))
    client.fetch_weather(50.43, 16.65, on_attempt=lambda: order.append("on_attempt"))
    assert order == ["on_attempt", "request"]
