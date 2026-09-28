"""Tests for ingest.py: store/skip/failure-isolation, using the SQLite db_session
fixture (plain ORM queries here, no Postgres-specific SQL — unlike air.py)."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from app.connectors.open_meteo import client, ingest
from app.models import GeoArea, WeatherSnapshot

PAYLOAD = {
    "current": {
        "time": "2026-09-28T18:00",
        "temperature_2m": 12.3,
        "relative_humidity_2m": 80,
        "wind_speed_10m": 5.2,
        "weather_code": 3,
    },
    "current_units": {
        "temperature_2m": "°C",
        "relative_humidity_2m": "%",
        "wind_speed_10m": "km/h",
        "weather_code": "wmo code",
    },
}


def _make_area(db) -> GeoArea:
    area = GeoArea(slug="klodzko", name="Kłodzko", latitude=50.43, longitude=16.65)
    db.add(area)
    db.commit()
    db.refresh(area)
    return area


def test_ingest_geo_area_stores_all_params(db_session, monkeypatch):
    area = _make_area(db_session)
    monkeypatch.setattr(client, "fetch_current", MagicMock(return_value=PAYLOAD))

    stored = ingest.ingest_geo_area(area, db_session)

    assert stored == 4
    assert db_session.query(WeatherSnapshot).count() == 4


def test_ingest_geo_area_skips_duplicate(db_session, monkeypatch):
    area = _make_area(db_session)
    monkeypatch.setattr(client, "fetch_current", MagicMock(return_value=PAYLOAD))

    ingest.ingest_geo_area(area, db_session)
    stored_again = ingest.ingest_geo_area(area, db_session)

    assert stored_again == 0
    assert db_session.query(WeatherSnapshot).count() == 4


def test_ingest_geo_area_isolates_api_failure(db_session, monkeypatch):
    area = _make_area(db_session)
    monkeypatch.setattr(
        client, "fetch_current", MagicMock(side_effect=client.OpenMeteoApiError("boom"))
    )

    stored = ingest.ingest_geo_area(area, db_session)

    assert stored == 0
    assert db_session.query(WeatherSnapshot).count() == 0


def test_ingest_geo_area_isolates_parse_failure(db_session, monkeypatch):
    area = _make_area(db_session)
    monkeypatch.setattr(client, "fetch_current", MagicMock(return_value={"bad": "shape"}))

    stored = ingest.ingest_geo_area(area, db_session)

    assert stored == 0
    assert db_session.query(WeatherSnapshot).count() == 0


def test_ingest_geo_area_fetched_at_is_recent(db_session, monkeypatch):
    area = _make_area(db_session)
    monkeypatch.setattr(client, "fetch_current", MagicMock(return_value=PAYLOAD))

    ingest.ingest_geo_area(area, db_session)

    row = db_session.query(WeatherSnapshot).first()
    assert (datetime.now(UTC) - row.fetched_at).total_seconds() < 5
