"""GET /api/v1/neighborhood (ADR-032): noise section from our DB - availability states, nearest
point per category, no freshness on historical data, isolation of a failing section."""

from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import neighborhood as nb
from app.config import settings
from app.connectors.gios_noise.ingest import OPERATION, request_filters
from app.connectors.gios_noise.parser import CATEGORIES, VOIVODESHIPS
from app.db import Base, get_db
from app.gios_open import snapshots as sn
from app.main import app
from app.models import GeoArea, NoiseMeasurement, SourceStatus

AREA = (50.2, 18.9)  # near Gliwice


@pytest.fixture
def db_session():
    """Real SQLite shared with the TestClient's worker thread (the default fixture is not)."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def area(db_session):
    a = GeoArea(slug="gliwice", name="Gliwice", latitude=AREA[0], longitude=AREA[1])
    db_session.add(a)
    db_session.commit()
    return a


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setattr(settings, "neighborhood_noise_enabled", True)
    monkeypatch.setattr(settings, "neighborhood_noise_max_km", 10.0)


def snapshot(db, category, voivodeship="ŚLĄSKIE"):
    filters = request_filters(category, voivodeship, date(2024, 1, 1), date(2024, 12, 31))
    snap = sn.begin_snapshot(db, source_id="gios_noise", operation=OPERATION, filters=filters)
    db.flush()
    sn.promote(
        db, snap, record_count=0, page_count=1, rejected_count=0, checksum=None, schema_hash=None
    )
    return snap


def point(
    db,
    snap,
    code,
    lat,
    lon,
    *,
    category="Droga",
    pora="Dzień 16h",
    value=60.0,
    d_to=date(2024, 11, 10),
):
    db.add(NoiseMeasurement(
        snapshot_id=snap.id, natural_key=f"{code}-{pora}-{d_to}-{value}", point_code=code,
        category=category, voivodeship="ŚLĄSKIE", locality="Test", latitude=lat, longitude=lon,
        period_label=pora, date_from=date(2024, 5, 10), date_to=d_to, value_db=value, raw={},
    ))  # fmt: skip
    db.commit()


def status(db, ok=True):
    now = datetime.now(UTC)
    db.merge(
        SourceStatus(
            source_id="gios_noise", last_attempt_at=now, last_success_at=now if ok else None
        )
    )
    db.commit()


def section(client, area):
    r = client.get("/api/v1/neighborhood", params={"geo_area_id": area.id})
    assert r.status_code == 200
    return r.json()


def test_unknown_area_is_404(client, enabled):
    assert client.get("/api/v1/neighborhood", params={"geo_area_id": 999}).status_code == 404


def test_flag_off_reports_disabled_and_no_sections(client, area):
    body = section(client, area)
    assert body["enabled"] is False and body["sections"] == []


def test_enabled_but_nothing_imported_is_unavailable_not_empty(client, area, enabled):
    s = section(client, area)["sections"][0]
    assert (
        s["availability"] == "unavailable" and s["retrieval_status"] == "none" and s["items"] == []
    )


def test_nearest_point_per_category_with_newest_period_and_attribution(
    db_session, client, area, enabled
):
    road = snapshot(db_session, "Droga")
    point(db_session, road, "FAR", 50.25, 18.95)
    point(db_session, road, "NEAR", 50.21, 18.91, d_to=date(2023, 11, 10), value=70.0)
    point(db_session, road, "NEAR", 50.21, 18.91, d_to=date(2024, 11, 10), value=64.5)
    point(
        db_session, road, "NEAR", 50.21, 18.91, pora="Noc 8h", d_to=date(2024, 11, 10), value=55.0
    )
    point(db_session, road, "OUT", 51.5, 18.9)  # > 10 km
    status(db_session)
    body = section(client, area)
    s = body["sections"][0]
    assert body["enabled"] is True and s["availability"] == "available"
    (item,) = s["items"]
    assert item["point_code"] == "NEAR" and item["category"] == "Droga" and item["distance_km"] < 3
    assert [(m["period_of_day"], m["value_db"]) for m in item["measurements"]] == [
        ("Dzień 16h", 64.5),
        ("Noc 8h", 55.0),
    ]
    assert s["source_period"] == {"from": "2024-05-10", "to": "2024-11-10", "precision": "date"}
    assert "freshness" not in s and s["data_kind"] == "historical_measurement"
    assert "CC BY 4.0" in s["attribution"] and "przetworzone przez Za Oknem" in s["attribution"]
    assert "2024-05-10" in s["attribution"] and s["retrieval_status"] == "ok"
    assert s["license_url"].startswith("https://creativecommons.org")


def test_distinct_categories_are_listed_separately(db_session, client, area, enabled):
    point(db_session, snapshot(db_session, "Droga"), "R1", 50.21, 18.91)
    point(db_session, snapshot(db_session, "Kolej"), "K1", 50.19, 18.89, category="Kolej")
    status(db_session)
    items = section(client, area)["sections"][0]["items"]
    assert [i["category"] for i in items] == ["Droga", "Kolej"]


def test_partial_import_without_a_nearby_point_is_unavailable_not_no_coverage(
    db_session, client, area, enabled
):
    snapshot(db_session, "Droga")
    status(db_session)
    assert section(client, area)["sections"][0]["availability"] == "unavailable"


def test_complete_import_without_a_nearby_point_is_no_coverage(db_session, client, area, enabled):
    for c in CATEGORIES:
        for v in VOIVODESHIPS:
            snapshot(db_session, c, v)
    status(db_session)
    s = section(client, area)["sections"][0]
    assert s["availability"] == "no_coverage" and "10 km" in s["message"] and s["items"] == []


def test_a_failed_latest_attempt_is_degraded_while_old_data_is_still_served(
    db_session, client, area, enabled
):
    point(db_session, snapshot(db_session, "Droga"), "NEAR", 50.21, 18.91)
    db_session.add(
        SourceStatus(
            source_id="gios_noise",
            last_attempt_at=datetime(2026, 10, 3, tzinfo=UTC),
            last_success_at=datetime(2026, 9, 1, tzinfo=UTC),
        )
    )
    db_session.commit()
    s = section(client, area)["sections"][0]
    assert s["retrieval_status"] == "degraded" and s["availability"] == "available"
    assert s["fetched_at"].startswith("2026-09-01")  # the old fetch time, never "now"


def test_a_crashing_section_does_not_break_the_response(client, area, enabled, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("db gone")

    monkeypatch.setattr("app.api.v1.neighborhood.build_noise_section", boom)
    r = client.get("/api/v1/neighborhood", params={"geo_area_id": area.id})
    assert r.status_code == 200
    s = r.json()["sections"][0]
    assert s["availability"] == "unavailable" and "db gone" not in r.text


def test_haversine_known_distance():
    assert nb.haversine_km(50.0, 19.0, 50.0, 19.0) == 0
    assert 111.0 < nb.haversine_km(50.0, 19.0, 51.0, 19.0) < 111.4
