"""Real SQL query checks: local scope, source isolation and latest selection."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.db import Base, get_db
from app.main import app
from app.models import GeoArea, Measurement


@pytest.fixture
def local_client(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    monkeypatch.setattr(settings, "imgw_hydro_publication_enabled", True)
    with Session(engine) as db:
        db.add(GeoArea(id=1, slug="gliwice", name="Gliwice", latitude=50.3, longitude=18.7))
        db.commit()
        app.dependency_overrides[get_db] = lambda: db
        with TestClient(app) as client:
            yield client, db
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()


def add(db, sid, *, lon=18.7, source="imgw_hydro", age=0, value=100):
    now = datetime.now(UTC)
    db.add(
        Measurement(
            source_id=source,
            source_record_id=f"{sid}:{age}:{source}",
            station_id=sid,
            station_name=f"Stacja {sid} (rzeka)",
            latitude=50.3,
            longitude=lon,
            param_code="water_level_cm",
            value=value,
            unit="cm",
            observed_at=now - timedelta(hours=age),
            fetched_at=now,
        )
    )
    db.commit()


def test_nearby_uses_latest_own_source_and_exact_radius(local_client):
    client, db = local_client
    add(db, "near", age=1, value=90)
    add(db, "near", value=110)
    add(db, "near", age=-1, value=999)  # future is not a current observation
    add(db, "near", source="other", value=800)
    add(db, "far", lon=20)
    body = client.get("/api/v1/hydro/latest?geo_area_id=1&max_distance_km=10").json()
    assert body["scope"] == "nearby"
    assert body["search_radius_km"] == 10
    assert len(body["stations"]) == 1
    station = body["stations"][0]
    assert station["station_id"] == "near"
    assert station["water_level_cm"] == 110
    assert station["distance_km"] == 0
    assert station["status"] == "UNKNOWN"
    national = client.get("/api/v1/hydro/latest").json()
    assert len(national["stations"]) == 2
    assert national["scope"] == "national"


def test_unknown_area_and_radius_validation(local_client):
    client, _ = local_client
    assert client.get("/api/v1/hydro/latest?geo_area_id=999").status_code == 404
    for query in [
        "geo_area_id=0",
        "max_distance_km=0",
        "max_distance_km=101",
        "max_distance_km=nan",
    ]:
        assert client.get(f"/api/v1/hydro/latest?{query}").status_code == 422


def test_disabled_local_scope_does_not_publish(local_client, monkeypatch):
    client, db = local_client
    add(db, "near")
    monkeypatch.setattr(settings, "imgw_hydro_publication_enabled", False)
    body = client.get("/api/v1/hydro/latest?geo_area_id=1").json()
    assert body["publication_enabled"] is False
    assert body["scope"] == "nearby"
    assert body["stations"] == []
