"""ADR-022: Open-Meteo endpoints + API key come from config; the key never reaches
provenance, exception text or logs. Covers both connectors (weather, pollen)."""

import logging
from unittest.mock import MagicMock

import httpx
import pytest

from app.config import settings
from app.connectors.open_meteo import client as weather_client
from app.connectors.open_meteo_pollen import client as pollen_client
from app.redact import redact
from app.source_health import sanitize_error

KEY = "SECRETKEY123"
FREE_FORECAST = "https://api.open-meteo.com/v1/forecast"
FREE_AIR = "https://air-quality-api.open-meteo.com/v1/air-quality"
PAID_FORECAST = "https://customer-api.open-meteo.com/v1/forecast"
PAID_AIR = "https://customer-air-quality-api.open-meteo.com/v1/air-quality"

CONNECTORS = [
    pytest.param(lambda: weather_client.fetch_weather(50.4, 16.6), weather_client,
                 weather_client.OpenMeteoApiError, "open_meteo_forecast_base_url",
                 FREE_FORECAST, PAID_FORECAST, id="weather"),
    pytest.param(lambda: pollen_client.fetch_pollen(50.4, 16.6), pollen_client,
                 pollen_client.OpenMeteoPollenApiError, "open_meteo_air_quality_base_url",
                 FREE_AIR, PAID_AIR, id="pollen"),
]  # fmt: skip


def _ok() -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"ok": True}
    return resp


@pytest.mark.parametrize("call, client, err, attr, free, paid", CONNECTORS)
def test_default_config_uses_free_host_and_sends_no_key(
    monkeypatch, call, client, err, attr, free, paid
):
    monkeypatch.setattr(settings, "open_meteo_api_key", None)
    mock_get = MagicMock(return_value=_ok())
    monkeypatch.setattr(client.httpx, "get", mock_get)

    call()

    assert mock_get.call_args.args[0] == free
    assert "apikey" not in mock_get.call_args.kwargs["params"]
    assert client.base_url() == free


@pytest.mark.parametrize("call, client, err, attr, free, paid", CONNECTORS)
def test_env_config_switches_host_and_adds_apikey_param(
    monkeypatch, call, client, err, attr, free, paid
):
    monkeypatch.setattr(settings, attr, paid)
    monkeypatch.setattr(settings, "open_meteo_api_key", KEY)
    mock_get = MagicMock(return_value=_ok())
    monkeypatch.setattr(client.httpx, "get", mock_get)

    call()

    assert mock_get.call_args.args[0] == paid
    assert mock_get.call_args.kwargs["params"]["apikey"] == KEY
    assert client.base_url() == paid  # what provenance records: host only, no key


@pytest.mark.parametrize("call, client, err, attr, free, paid", CONNECTORS)
def test_httpx_error_with_url_is_masked_and_not_chained(
    monkeypatch, call, client, err, attr, free, paid
):
    monkeypatch.setattr(settings, "open_meteo_api_key", KEY)
    leaky = httpx.HTTPStatusError(
        f"Client error '401 Unauthorized' for url '{paid}?latitude=50.4&apikey={KEY}'",
        request=httpx.Request("GET", f"{paid}?apikey={KEY}"),
        response=httpx.Response(401),
    )
    monkeypatch.setattr(client.httpx, "get", MagicMock(side_effect=leaky))

    with pytest.raises(err) as info:
        call()

    assert KEY not in str(info.value)
    assert "apikey=[redacted]" in str(info.value)
    assert info.value.__cause__ is None  # the original exception (with the URL) is dropped
    assert info.value.__suppress_context__


def test_redact_masks_param_and_literal_key(monkeypatch):
    monkeypatch.setattr(settings, "open_meteo_api_key", KEY)

    assert KEY not in redact(f"x ?a=1&apikey={KEY}&b=2 and bare {KEY}")
    assert redact("APIKEY=whatever&x=1") == "APIKEY=[redacted]&x=1"
    assert redact("no secrets here") == "no secrets here"


def test_httpx_request_log_is_masked(monkeypatch, caplog):
    monkeypatch.setattr(settings, "open_meteo_api_key", KEY)
    with caplog.at_level(logging.INFO, logger="httpx"):
        logging.getLogger("httpx").info(
            'HTTP Request: %s %s "%s"',
            "GET",
            f"{PAID_FORECAST}?apikey={KEY}&x=1",
            "HTTP/1.1 200 OK",
        )

    assert KEY not in caplog.text
    assert "apikey=[redacted]" in caplog.text


def test_source_health_sanitizer_masks_apikey_in_last_error():
    raw = f"OpenMeteoApiError: GET {PAID_FORECAST} failed: for url x&apikey={KEY}&y=1 (HTTP 401)"

    assert KEY not in (sanitize_error(raw) or "")
    assert KEY not in (sanitize_error(f"url {PAID_FORECAST}?apikey={KEY}") or "")
