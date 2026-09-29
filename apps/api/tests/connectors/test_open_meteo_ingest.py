"""Tests for ingest.py: store/skip/failure-isolation, using the SQLite db_session
fixture (plain ORM queries here, no Postgres-specific SQL — unlike air.py)."""

import sys
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

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


class TestMain:
    """main(): argparse + --slug filtering wiring, using the real SQLite
    db_session so GeoArea.slug.in_() filtering is exercised for real (not a
    mocked query chain). ingest_geo_area itself is covered above."""

    def test_no_matching_geo_areas_exits_with_error(self, monkeypatch, capsys, db_session):
        monkeypatch.setattr(sys, "argv", ["ingest"])
        monkeypatch.setattr(ingest, "SessionLocal", lambda: db_session)

        with pytest.raises(SystemExit) as exc_info:
            ingest.main()

        assert exc_info.value.code == 1
        assert "No matching geo_areas found" in capsys.readouterr().err

    def test_ingests_every_area_when_no_slug_given(self, monkeypatch, db_session):
        _make_area(db_session)
        monkeypatch.setattr(sys, "argv", ["ingest"])
        monkeypatch.setattr(ingest, "SessionLocal", lambda: db_session)
        ingest_mock = MagicMock()
        monkeypatch.setattr(ingest, "ingest_geo_area", ingest_mock)

        ingest.main()

        assert ingest_mock.call_count == 1

    def test_slug_filters_to_matching_areas_only(self, monkeypatch, db_session):
        _make_area(db_session)  # slug="klodzko"
        other = GeoArea(slug="warszawa", name="Warszawa", latitude=52.23, longitude=21.01)
        db_session.add(other)
        db_session.commit()
        monkeypatch.setattr(sys, "argv", ["ingest", "--slug", "warszawa"])
        monkeypatch.setattr(ingest, "SessionLocal", lambda: db_session)
        ingest_mock = MagicMock()
        monkeypatch.setattr(ingest, "ingest_geo_area", ingest_mock)

        ingest.main()

        assert ingest_mock.call_count == 1
        assert ingest_mock.call_args[0][0].slug == "warszawa"
