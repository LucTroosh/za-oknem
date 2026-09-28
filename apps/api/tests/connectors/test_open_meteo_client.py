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


def test_fetch_current_returns_json_on_success(monkeypatch):
    monkeypatch.setattr(client.httpx, "get", MagicMock(return_value=_ok_response({"ok": True})))
    assert client.fetch_current(50.43, 16.65) == {"ok": True}


def test_fetch_current_retries_once_then_succeeds(monkeypatch):
    attempts = [httpx.RequestError("boom"), _ok_response({"ok": True})]
    monkeypatch.setattr(client.httpx, "get", MagicMock(side_effect=lambda *a, **k: attempts.pop(0)))
    assert client.fetch_current(50.43, 16.65) == {"ok": True}


def test_fetch_current_raises_after_two_failures(monkeypatch):
    monkeypatch.setattr(
        client.httpx, "get", MagicMock(side_effect=httpx.RequestError("still broken"))
    )
    with pytest.raises(client.OpenMeteoApiError):
        client.fetch_current(50.43, 16.65)


def test_fetch_current_passes_coordinates_and_params(monkeypatch):
    mock_get = MagicMock(return_value=_ok_response({"ok": True}))
    monkeypatch.setattr(client.httpx, "get", mock_get)
    client.fetch_current(50.43, 16.65)
    _, kwargs = mock_get.call_args
    assert kwargs["params"]["latitude"] == 50.43
    assert kwargs["params"]["longitude"] == 16.65
    assert kwargs["params"]["current"] == client.CURRENT_PARAMS
