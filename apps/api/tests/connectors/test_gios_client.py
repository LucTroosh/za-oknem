"""Tests for the GIOŚ HTTP client (client.py): retry, rate-limit throttling,
pagination and response-shape guards. httpx.get is mocked throughout — no
live network, matching the connector isolation contract (rule #7)."""

from unittest.mock import MagicMock

import httpx
import pytest

from app.connectors.gios import client


@pytest.fixture(autouse=True)
def reset_throttle_state():
    """_last_list_call_at is module-level global state — leaking it across
    tests would make results depend on run order. Reset before every test."""
    client._last_list_call_at = 0.0
    yield


def _ok_response(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = payload
    return resp


# --- _get: retry ------------------------------------------------------------


def test_get_returns_json_on_success(monkeypatch):
    monkeypatch.setattr(client.httpx, "get", MagicMock(return_value=_ok_response({"ok": True})))
    assert client._get("/whatever") == {"ok": True}


def test_get_retries_once_then_succeeds(monkeypatch):
    attempts = [httpx.RequestError("boom"), _ok_response({"ok": True})]

    def fake_get(*args, **kwargs):
        result = attempts.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(client.httpx, "get", fake_get)
    assert client._get("/whatever") == {"ok": True}


def test_get_raises_gios_api_error_after_exhausting_retry(monkeypatch):
    monkeypatch.setattr(client.httpx, "get", MagicMock(side_effect=httpx.RequestError("boom")))
    with pytest.raises(client.GiosApiError):
        client._get("/whatever")


def test_get_throttles_every_attempt_including_retry(monkeypatch):
    """Codex review on PR #3 flagged that the retry attempt itself must also be
    throttled, not just the first try — regression guard for that fix."""
    monkeypatch.setattr(client.httpx, "get", MagicMock(side_effect=httpx.RequestError("boom")))
    throttle = MagicMock()
    monkeypatch.setattr(client, "_throttle_list_endpoint", throttle)

    with pytest.raises(client.GiosApiError):
        client._get("/whatever", throttle=True)

    assert throttle.call_count == 2  # one per attempt


# --- _throttle_list_endpoint --------------------------------------------------


def test_throttle_sleeps_when_called_too_soon(monkeypatch):
    monkeypatch.setattr(client, "_last_list_call_at", 1000.0)
    monkeypatch.setattr(client.time, "monotonic", MagicMock(side_effect=[1010.0, 1010.0]))
    sleep = MagicMock()
    monkeypatch.setattr(client.time, "sleep", sleep)

    client._throttle_list_endpoint()

    sleep.assert_called_once()
    assert sleep.call_args[0][0] == pytest.approx(20.0)


def test_throttle_does_not_sleep_when_enough_time_passed(monkeypatch):
    monkeypatch.setattr(client, "_last_list_call_at", 1000.0)
    monkeypatch.setattr(client.time, "monotonic", MagicMock(side_effect=[1035.0, 1035.0]))
    sleep = MagicMock()
    monkeypatch.setattr(client.time, "sleep", sleep)

    client._throttle_list_endpoint()

    sleep.assert_not_called()


# --- pagination / lookup -----------------------------------------------------


def _page(stations: list[dict], total_pages: int) -> dict:
    return {"Lista stacji pomiarowych": stations, "totalPages": total_pages}


def test_fetch_all_stations_walks_every_page(monkeypatch):
    pages = [_page([{"Identyfikator stacji": 1}], 2), _page([{"Identyfikator stacji": 2}], 2)]
    monkeypatch.setattr(client, "fetch_station_page", MagicMock(side_effect=pages))

    result = client.fetch_all_stations()

    assert [s["Identyfikator stacji"] for s in result] == [1, 2]


def test_iter_station_pages_raises_gios_api_error_on_unexpected_shape(monkeypatch):
    monkeypatch.setattr(
        client, "fetch_station_page", MagicMock(return_value={"totalPages": 1})
    )
    with pytest.raises(client.GiosApiError):
        list(client._iter_station_pages())


def test_find_stations_stops_as_soon_as_all_ids_found(monkeypatch):
    """Finding known stations shouldn't pay for walking the whole (rate-limited)
    catalog — must stop after the page containing all wanted ids."""
    page_1 = _page(
        [{"Identyfikator stacji": 1}, {"Identyfikator stacji": 2}], total_pages=5
    )
    fetch = MagicMock(return_value=page_1)
    monkeypatch.setattr(client, "fetch_station_page", fetch)

    found = client.find_stations({"1", "2"})

    assert {s["Identyfikator stacji"] for s in found} == {1, 2}
    assert fetch.call_count == 1


# --- sensors / data -----------------------------------------------------------


def test_fetch_sensors_returns_list(monkeypatch):
    monkeypatch.setattr(
        client,
        "_get",
        MagicMock(return_value={"Lista stanowisk pomiarowych dla podanej stacji": [{"id": 1}]}),
    )
    assert client.fetch_sensors("38") == [{"id": 1}]


def test_fetch_sensors_raises_gios_api_error_on_unexpected_shape(monkeypatch):
    monkeypatch.setattr(client, "_get", MagicMock(return_value={}))
    with pytest.raises(client.GiosApiError):
        client.fetch_sensors("38")


def test_fetch_sensor_data_passes_through(monkeypatch):
    monkeypatch.setattr(client, "_get", MagicMock(return_value={"data": "raw"}))
    assert client.fetch_sensor_data("25988") == {"data": "raw"}
