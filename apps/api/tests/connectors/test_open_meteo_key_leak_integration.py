"""ADR-022 integration: the API key travels through the REAL client code and an httpx
MockTransport (so httpx builds the real URL and the real HTTPStatusError), and must not
reach source_fetches.endpoint, source_status.last_error or the exception text - for
both connectors, on success and on failure."""

import json

import httpx
import pytest

from app import scheduler
from app.config import settings
from app.connectors.open_meteo import ingest as weather_ingest
from app.connectors.open_meteo_pollen import ingest as pollen_ingest
from app.models import GeoArea, SourceFetch, SourceStatus

from .test_open_meteo_ingest import PAYLOAD as WEATHER_PAYLOAD
from .test_open_meteo_pollen_ingest import PAYLOAD as POLLEN_PAYLOAD

KEY = "LEAKCHECK-KEY-98765"
HOSTS = {
    "open_meteo_forecast_base_url": "https://customer-api.open-meteo.com/v1/forecast",
    "open_meteo_air_quality_base_url": "https://customer-air-quality-api.open-meteo.com/v1/air-quality",
}


@pytest.fixture
def keyed(monkeypatch, db_session):
    monkeypatch.setattr(settings, "open_meteo_api_key", KEY)
    for attr, url in HOSTS.items():
        monkeypatch.setattr(settings, attr, url)
    monkeypatch.setattr(scheduler, "SessionLocal", lambda: db_session)
    area = GeoArea(slug="klodzko", name="Kłodzko", latitude=50.43, longitude=16.65)
    db_session.add(area)
    db_session.commit()
    db_session.refresh(area)
    return area


def _transport(monkeypatch, handler):
    """httpx.get -> a Client over MockTransport: real URL building + real raise_for_status."""
    seen: list[httpx.Request] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    def _get(url, *, params=None, timeout=None):
        with httpx.Client(transport=httpx.MockTransport(_handler)) as c:
            return c.get(url, params=params, timeout=timeout)

    monkeypatch.setattr(httpx, "get", _get)
    return seen


def _all_text(db) -> str:
    rows = [(f.endpoint, json.dumps(f.payload)) for f in db.query(SourceFetch).all()] + [
        (s.last_error or "",) for s in db.query(SourceStatus).all()
    ]
    return repr(rows)


def test_pollen_success_sends_key_but_stores_none(db_session, monkeypatch, keyed):
    seen = _transport(monkeypatch, lambda r: httpx.Response(200, json=POLLEN_PAYLOAD))

    assert pollen_ingest.ingest_geo_area(keyed, db_session) is True

    assert seen[0].url.params["apikey"] == KEY  # the request really carried it
    assert seen[0].url.host == "customer-air-quality-api.open-meteo.com"
    fetch = db_session.query(SourceFetch).one()
    assert fetch.endpoint.startswith(HOSTS["open_meteo_air_quality_base_url"])
    assert KEY not in _all_text(db_session)


def test_weather_success_sends_key_but_stores_none(db_session, monkeypatch, keyed):
    seen = _transport(monkeypatch, lambda r: httpx.Response(200, json=WEATHER_PAYLOAD))

    assert weather_ingest.ingest_geo_area(keyed, db_session) is not None

    assert seen[0].url.params["apikey"] == KEY
    assert seen[0].url.host == "customer-api.open-meteo.com"
    fetch = db_session.query(SourceFetch).one()
    assert fetch.endpoint.startswith(HOSTS["open_meteo_forecast_base_url"])
    assert KEY not in _all_text(db_session)


@pytest.mark.parametrize(
    "job_name, job",
    [
        ("open_meteo", scheduler.run_open_meteo),
        ("open_meteo_pollen", scheduler.run_open_meteo_pollen),
    ],
)
def test_failure_keeps_key_out_of_last_error_and_logs(
    db_session, monkeypatch, keyed, caplog, job_name, job
):
    seen = _transport(monkeypatch, lambda r: httpx.Response(401, json={"reason": "bad key"}))

    with caplog.at_level("DEBUG"):
        scheduler._run_job_safely(job_name, job)

    assert len(seen) == 1  # 401 is not retried
    status = db_session.get(SourceStatus, job_name)
    assert status is not None and status.last_error
    assert KEY not in _all_text(db_session)
    assert KEY not in caplog.text  # includes the traceback logged by logger.exception
