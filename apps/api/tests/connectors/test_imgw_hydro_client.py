"""Tests for the IMGW hydro HTTP client: retry and response-shape guard.
httpx.get is mocked - no live network."""

from unittest.mock import MagicMock

import httpx
import pytest

from app.connectors.imgw_hydro import client


def _ok_response(payload) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = payload
    return resp


def test_fetch_stations_returns_list_on_success(monkeypatch):
    monkeypatch.setattr(client.httpx, "get", MagicMock(return_value=_ok_response([{"id": 1}])))
    assert client.fetch_stations() == [{"id": 1}]


def test_fetch_stations_retries_once_then_succeeds(monkeypatch):
    attempts = [httpx.RequestError("boom"), _ok_response([{"id": 1}])]

    def fake_get(*args, **kwargs):
        result = attempts.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(client.httpx, "get", fake_get)
    assert client.fetch_stations() == [{"id": 1}]


def test_fetch_stations_raises_after_exhausting_retry(monkeypatch):
    monkeypatch.setattr(client.httpx, "get", MagicMock(side_effect=httpx.RequestError("boom")))
    with pytest.raises(client.ImgwHydroApiError):
        client.fetch_stations()


def test_fetch_stations_rejects_non_list_shape(monkeypatch):
    # warningsmeteo's known "empty" shape is {"message": "..."} - guard against
    # this endpoint ever doing the same instead of silently misreading it as data.
    monkeypatch.setattr(client.httpx, "get", MagicMock(return_value=_ok_response({"message": "x"})))
    with pytest.raises(client.ImgwHydroApiError):
        client.fetch_stations()
