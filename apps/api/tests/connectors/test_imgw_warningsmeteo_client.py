"""Tests for the IMGW meteo-warnings HTTP client: retry only (shape handling
lives in parser.py - the client passes the raw payload through as-is)."""

from unittest.mock import MagicMock

import httpx
import pytest

from app.connectors.imgw_warningsmeteo import client


def _ok_response(payload) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = payload
    return resp


def test_fetch_warnings_returns_payload_on_success(monkeypatch):
    monkeypatch.setattr(client.httpx, "get", MagicMock(return_value=_ok_response([{"a": 1}])))
    assert client.fetch_warnings() == [{"a": 1}]


def test_fetch_warnings_passes_through_message_dict(monkeypatch):
    monkeypatch.setattr(
        client.httpx,
        "get",
        MagicMock(return_value=_ok_response({"message": "Brak ostrzeżeń meteorologicznych"})),
    )
    assert client.fetch_warnings() == {"message": "Brak ostrzeżeń meteorologicznych"}


def test_fetch_warnings_retries_once_then_succeeds(monkeypatch):
    attempts = [httpx.RequestError("boom"), _ok_response([])]

    def fake_get(*args, **kwargs):
        result = attempts.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(client.httpx, "get", fake_get)
    assert client.fetch_warnings() == []


def test_fetch_warnings_raises_after_exhausting_retry(monkeypatch):
    monkeypatch.setattr(client.httpx, "get", MagicMock(side_effect=httpx.RequestError("boom")))
    with pytest.raises(client.ImgwWarningsMeteoApiError):
        client.fetch_warnings()
