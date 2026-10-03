"""Behavioral tests of gated IMGW observations/selection and atomic warnings."""

import copy
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.alert_geo import filter_alerts_for_area
from app.api.v1.alerts import alerts_source_status, current_alerts
from app.config import Settings, settings
from app.connectors.imgw_warningsmeteo.ingest import ingest_raw as ingest_warnings
from app.connectors.imgw_warningsmeteo.parser import ImgwWarningsMeteoParseError
from app.connectors.imgw_weather.ingest import ingest_raw
from app.connectors.imgw_weather.parser import normalize, number, source_time
from app.db import Base, get_db
from app.imgw_weather import selected_weather
from app.main import app
from app.models import Alert, GeoArea, ImgwWeatherStation, Measurement, SourceFetch, WeatherSnapshot
from app.source_status import record_source_run

EVIDENCE = Path(__file__).resolve().parents[3] / "docs/data/imgw/evidence"
NOW = datetime.now(UTC)


def station(now=NOW):
    row = next(
        r
        for r in json.loads((EVIDENCE / "meteo.json").read_text())
        if r["temperatura_powietrza"] is not None and r["wilgotnosc_wzgledna"] is not None
    )
    row = copy.deepcopy(row)
    for key in row:
        if key.endswith("_data") and row[key] is not None:
            row[key] = now.strftime("%Y-%m-%d %H:%M:%S")
    row["wiatr_poryw_10min"] = "8"
    row["wiatr_poryw_10min_data"] = (now - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
    row["opad_10min"] = "0"
    row["opad_10min_data"] = now.strftime("%Y-%m-%d %H:%M:%S")
    return row


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture
def gates(monkeypatch):
    monkeypatch.setattr(settings, "imgw_weather_timezone", "UTC")
    monkeypatch.setattr(settings, "imgw_warnings_timezone", "Europe/Warsaw")
    monkeypatch.setattr(settings, "imgw_weather_semantics_verified", True)
    monkeypatch.setattr(settings, "imgw_observations_publication_enabled", True)
    monkeypatch.setattr(settings, "imgw_warnings_enabled", True)
    monkeypatch.setattr(settings, "imgw_hydro_publication_enabled", False)


def area_and_readings(db, monkeypatch):
    raw = station()
    area = GeoArea(
        id=1, slug="test", name="Test", latitude=float(raw["lat"]), longitude=float(raw["lon"])
    )
    db.add(area)
    db.commit()
    ingest_raw([raw], "meteo", db, fetched_at=NOW)
    record_source_run(db, "imgw_meteo", success=True, now=NOW)
    monkeypatch.setattr(settings, "imgw_area_elevations_m", {1: float(raw["wysokosc_npm"])})
    for code, value, unit in [
        ("temperature_2m", 2, "°C"),
        ("relative_humidity_2m", 3, "%"),
        ("precipitation", 4, "mm"),
    ]:
        db.add(
            WeatherSnapshot(
                source_id="open_meteo",
                source_record_id=code,
                geo_area_id=1,
                param_code=code,
                value=value,
                unit=unit,
                observed_at=NOW,
                fetched_at=NOW,
            )
        )
    db.commit()
    return area, raw


def test_flags_start_disabled():
    defaults = Settings(_env_file=None)
    assert not defaults.imgw_observations_enabled
    assert not defaults.imgw_observations_publication_enabled
    assert not defaults.imgw_warnings_enabled
    assert not defaults.imgw_hydro_publication_enabled
    assert defaults.imgw_weather_timezone is None


@pytest.mark.parametrize("value,expected", [("0", 0), (None, None), ("", None)])
def test_null_is_not_zero(value, expected):
    assert number(value) == expected


@pytest.mark.parametrize("value", [True, "nan", "inf", {}])
def test_bad_numbers_rejected(value):
    with pytest.raises(ValueError):
        number(value)


@pytest.mark.parametrize(
    "value,timezone",
    [
        ("2026-10-25 02:30:00", "Europe/Warsaw"),
        ("2026-03-29 02:30:00", "Europe/Warsaw"),
        ("2026-10-03 19:00:00", None),
    ],
)
def test_unknown_or_ambiguous_time_rejected(value, timezone):
    with pytest.raises(ValueError):
        source_time(value, timezone)


def test_real_fixture_has_parameter_times_and_station_coordinates(gates):
    row = station()
    catalog, values, issues = normalize(row, "meteo", fetched_at=NOW, timezone="UTC")
    assert not issues
    assert catalog["latitude"] == float(row["lat"])
    params = {v["param_code"]: v for v in values}
    assert params["precip_10min_mm"]["value"] == 0
    assert params["wind_gust_10min_ms"]["observed_at"] < params["temperature_2m"]["observed_at"]
    assert "wind_gusts_10m" not in params  # maximum/gust semantics stay separate


def test_synop_without_geometry_never_fabricates_measurement(gates, db_session):
    rows = json.loads((EVIDENCE / "synop.json").read_text())[:1]
    assert ingest_raw(rows, "synop", db_session, fetched_at=NOW) == 0
    assert db_session.get(ImgwWeatherStation, ("imgw_synop", rows[0]["id_stacji"])).latitude is None
    assert db_session.scalar(select(func.count()).select_from(Measurement)) == 0


def test_selection_is_per_param_and_model_fills_unlike_precip(gates, db_session, monkeypatch):
    area, raw = area_and_readings(db_session, monkeypatch)
    result = selected_weather(db_session, area)
    assert result["params"]["temperature_2m"]["source"] == "imgw_meteo"
    assert result["params"]["relative_humidity_2m"]["source"] == "imgw_meteo"
    assert result["params"]["precipitation"]["source"] == "open_meteo"
    assert result["observations"][0]["params"]["wind_gust_10min_ms"]["freshness"] == "STALE"
    # Same selection is reachable through our own DB-only API.
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        body = TestClient(app).get("/api/v1/weather/selected?geo_area_id=1").json()
        assert body["params"]["temperature_2m"]["value"] == float(raw["temperatura_powietrza"])
        assert TestClient(app).get("/api/v1/weather/selected?geo_area_id=999").status_code == 404
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.parametrize(
    "reason",
    ["stale", "distance", "elevation", "height_unknown", "failed_source", "disabled", "units"],
)
def test_ineligible_observation_falls_back(gates, db_session, monkeypatch, reason):
    area, _ = area_and_readings(db_session, monkeypatch)
    if reason == "stale":
        for r in db_session.scalars(select(Measurement)).all():
            r.observed_at = NOW - timedelta(hours=2)
    elif reason == "distance":
        area.latitude += 1
    elif reason == "elevation":
        monkeypatch.setattr(settings, "imgw_area_elevations_m", {1: 3000})
    elif reason == "height_unknown":
        monkeypatch.setattr(settings, "imgw_area_elevations_m", {})
    elif reason == "failed_source":
        record_source_run(
            db_session, "imgw_meteo", success=False, error="network", now=NOW + timedelta(seconds=1)
        )
    elif reason == "disabled":
        monkeypatch.setattr(settings, "imgw_weather_semantics_verified", False)
    elif reason == "units":
        for r in db_session.scalars(select(Measurement)).all():
            r.unit = "K"
    db_session.commit()
    assert selected_weather(db_session, area)["params"]["temperature_2m"]["source"] == "open_meteo"


def test_bad_snapshot_preserves_good_rows(gates, db_session, monkeypatch):
    area, raw = area_and_readings(db_session, monkeypatch)
    bad = copy.deepcopy(raw)
    bad.pop("temperatura_powietrza")
    with pytest.raises(ValueError):
        ingest_raw([bad], "meteo", db_session, fetched_at=NOW + timedelta(minutes=1))
    assert selected_weather(db_session, area)["params"]["temperature_2m"]["source"] == "imgw_meteo"
    assert (
        db_session.scalars(select(SourceFetch).order_by(SourceFetch.id.desc()))
        .first()
        .validation_status
        == "invalid"
    )


def test_dedup_is_idempotent(gates, db_session, monkeypatch):
    _, raw = area_and_readings(db_session, monkeypatch)
    before = db_session.scalar(select(func.count()).select_from(Measurement))
    ingest_raw([raw], "meteo", db_session, fetched_at=NOW + timedelta(seconds=1))
    assert db_session.scalar(select(func.count()).select_from(Measurement)) == before


def warning():
    raw = json.loads((EVIDENCE / "warningsmeteo.json").read_text())[0]
    return copy.deepcopy(raw)


def test_real_warning_codes_match_county_exactly(gates, db_session):
    ingest_warnings([warning()], db_session, fetched_at=NOW)
    items = current_alerts(db_session)
    assert items[0]["severity_raw"] == "1"
    assert filter_alerts_for_area(items, "0201011")[0]["geo_match"] == "county"
    assert filter_alerts_for_area(items, "0201")[0]["geo_match"] == "county"
    assert filter_alerts_for_area(items, "9999011") == []
    assert filter_alerts_for_area(items, "02")[0]["geo_match"] == "unresolved"
    assert filter_alerts_for_area(items, None)[0]["geo_match"] == "unresolved"


def test_malformed_warning_does_not_withdraw_good_warning(gates, db_session):
    ingest_warnings([warning()], db_session, fetched_at=NOW)
    bad = warning()
    bad.pop("tresc")
    with pytest.raises(ImgwWarningsMeteoParseError):
        ingest_warnings([bad], db_session, fetched_at=NOW + timedelta(minutes=1))
    assert len(current_alerts(db_session)) == 1
    with pytest.raises(ImgwWarningsMeteoParseError):
        ingest_warnings({"message": "error"}, db_session, fetched_at=NOW + timedelta(minutes=1))
    assert len(current_alerts(db_session)) == 1


def test_valid_empty_snapshot_withdraws_warning(gates, db_session):
    ingest_warnings([warning()], db_session, fetched_at=NOW)
    later = NOW + timedelta(minutes=1)
    ingest_warnings({"message": "Brak ostrzeżeń meteorologicznych"}, db_session, fetched_at=later)
    assert db_session.scalars(select(Alert)).first().valid_until.replace(tzinfo=UTC) == later


def test_disabled_publication_never_claims_all_clear(db_session, monkeypatch):
    monkeypatch.setattr(settings, "imgw_hydro_publication_enabled", False)
    monkeypatch.setattr(settings, "imgw_warnings_enabled", False)
    assert current_alerts(db_session) == []
    assert alerts_source_status(db_session)["imgw_warningsmeteo"]["freshness"] == "UNAVAILABLE"
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        hydro = TestClient(app).get("/api/v1/hydro/latest").json()
        assert hydro["stations"] == [] and hydro["source_status"]["freshness"] == "UNAVAILABLE"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_empty_success_then_failure_cannot_confirm_no_alerts(gates, db_session):
    record_source_run(db_session, "imgw_warningsmeteo", success=True, now=NOW)
    assert alerts_source_status(db_session)["imgw_warningsmeteo"]["freshness"] == "FRESH"
    record_source_run(
        db_session,
        "imgw_warningsmeteo",
        success=False,
        error="timeout",
        now=NOW + timedelta(seconds=1),
    )
    status = alerts_source_status(db_session)["imgw_warningsmeteo"]
    assert status["freshness"] == "STALE"
    assert status["last_success_at"] is not None


def test_full_real_meteo_fixture_isolates_one_invalid_station(gates, db_session):
    raw = json.loads((EVIDENCE / "meteo.json").read_text())
    capture = datetime.fromisoformat(
        json.loads((EVIDENCE / "manifest.json").read_text())["captured_at"]
    )
    # UTC is a test hypothesis; this test does not approve the API timezone.
    count = ingest_raw(raw, "meteo", db_session, fetched_at=capture)
    assert count > 2000
    assert db_session.scalar(select(func.count()).select_from(ImgwWeatherStation)) == len(raw) - 1
    assert db_session.scalars(select(SourceFetch)).first().validation_status == "partial"


def test_duplicate_id_with_invalid_coordinates_rejects_even_large_batch(gates, db_session):
    raw = [dict(station(), kod_stacji=str(900000000 + i)) for i in range(50)]
    bad = dict(raw[0], lat=None)
    with pytest.raises(ValueError, match="incomplete"):
        ingest_raw([*raw, bad], "meteo", db_session, fetched_at=NOW)
    assert db_session.scalar(select(func.count()).select_from(Measurement)) == 0
    assert db_session.scalar(select(func.count()).select_from(ImgwWeatherStation)) == 0
