"""TASK-2.1: /dashboard/latest has an explicit response_model (DashboardResponse).

The model must reflect EXACTLY what the endpoint built before it had one: pydantic drops
unknown keys and coerces types, so each scenario compares the HTTP body with the raw dict
the endpoint function returns (jsonable_encoder = what FastAPI sent for the bare dict). Any
key the model forgot, or any value it changed, shows up as a diff here.
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.encoders import jsonable_encoder
from test_dashboard import (
    KLODZKO,
    WARSZAWA,
    _alert_row,
    _client,
    _forecast,
    _outdoor_air,
    _outdoor_weather,
    _pollen_ok_status,
    _pollen_row,
    _station,
    _weather,
    teardown_function,  # noqa: F401  (pytest hook: removes the get_db override)
)

from app.api.v1.dashboard import dashboard_latest
from app.db import get_db
from app.main import app
from app.models import GeoArea


def _both(client) -> tuple[dict, dict]:
    """(raw dict from the endpoint function, JSON body served over HTTP)."""
    raw = dashboard_latest(next(app.dependency_overrides[get_db]()))
    resp = client.get("/api/v1/dashboard/latest")
    assert resp.status_code == 200
    return jsonable_encoder(raw), resp.json()


def _fresh_client():
    area = GeoArea(**KLODZKO)
    return _client(
        [area],
        _outdoor_air(),
        _outdoor_weather(),
        forecast_rows=[
            _forecast(param_code="temperature_2m_max", value=18.5),
            _forecast(param_code="temperature_2m_min", value=9.2, source_record_id="fc-2"),
        ],
        alert_rows=[_alert_row()],
        pollen=([_pollen_row(birch=12.5, alder=0.0)], [area]),
        status_rows=_pollen_ok_status(),
    )


def test_all_fresh_body_equals_endpoint_dict():
    raw, body = _both(_fresh_client())
    assert body == raw
    area = body["areas"][0]
    assert area["air"]["station_id"] == "38"
    assert area["weather"]["freshness"] == "FRESH"
    assert area["forecast"]["days"] and area["pollen"]["freshness"] == "FRESH"
    assert body["alerts"]["items"][0]["areas"] == [{"wojewodztwo": "wielkopolskie"}]


def test_no_data_blocks_stay_null_not_absent():
    raw, body = _both(_client([GeoArea(**KLODZKO), GeoArea(**WARSZAWA)], [], []))
    assert body == raw
    for area in body["areas"]:
        assert area["air"] is None and area["weather"] is None and area["forecast"] is None
        assert area["outdoor"]["level"] == "UNKNOWN" and area["outdoor"]["valid_until"] is None
        assert area["pollen"]["freshness"] == "UNAVAILABLE" and area["pollen"]["current"] is None
    assert body["alerts"]["items"] == []
    assert body["alerts"]["source_status"]["imgw_warningshydro"]["freshness"] == "UNAVAILABLE"


def test_no_areas():
    raw, body = _both(_client([], [], []))
    assert body == raw and body["areas"] == []


def test_stale_data_body_equals_endpoint_dict():
    old = datetime.now(UTC) - timedelta(hours=100)
    area = GeoArea(**KLODZKO)
    client = _client(
        [area],
        [_station(observed_at=old)],
        [_weather(observed_at=old)],
        pollen=([_pollen_row(hours_old=100, birch=5.0)], [area]),
        status_rows=_pollen_ok_status(hours_old=100),
    )
    raw, body = _both(client)
    assert body == raw
    area_out = body["areas"][0]
    assert area_out["air"]["params"]["PM2.5"]["freshness"] == "STALE"
    assert area_out["weather"]["freshness"] == "STALE"
    assert area_out["pollen"]["freshness"] == "STALE"


def test_pollen_failure_keeps_the_contract_valid(monkeypatch):
    def boom(_db):
        raise RuntimeError("pollen read down")

    monkeypatch.setattr("app.api.v1.dashboard.latest_pollen", boom)
    raw, body = _both(_client([GeoArea(**KLODZKO)], _outdoor_air(), _outdoor_weather()))
    assert body == raw
    area = body["areas"][0]
    assert area["pollen"]["freshness"] == "UNAVAILABLE" and area["pollen"]["days"] == []
    assert area["air"] is not None and area["weather"] is not None  # other blocks intact


def test_openapi_documents_every_dashboard_block():
    schema = app.openapi()
    ref = schema["paths"]["/api/v1/dashboard/latest"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    assert ref == "#/components/schemas/DashboardResponse"
    comps = schema["components"]["schemas"]
    assert set(comps["DashboardResponse"]["properties"]) == {"areas", "alerts"}
    area = comps["DashboardArea"]
    expected = {"geo_area_id", "slug", "name", "latitude", "longitude"}
    expected |= {"air", "weather", "forecast", "outdoor", "pollen"}
    assert set(area["properties"]) == expected
    assert set(area["required"]) == expected  # null = "no data", never an absent key
    assert set(comps["DashboardAlerts"]["properties"]) == {
        "scope",
        "source",
        "attribution",
        "items",
        "source_status",
    }
    # UNAVAILABLE must stay representable for a failed pollen block (rule #1).
    assert "UNAVAILABLE" in comps["DashboardPollen"]["properties"]["freshness"]["enum"]


@pytest.mark.parametrize("name", ["DashboardAir", "DashboardWeather", "DashboardForecast"])
def test_source_blocks_carry_attribution(name):
    assert "attribution" in app.openapi()["components"]["schemas"][name]["properties"]
