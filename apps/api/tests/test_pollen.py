"""Tests for GET /api/v1/pollen/latest: newest-run selection, current-hour pick, per-day
maxima, explicit nulls, freshness thresholds, source_status and attribution.

Uses a real SQLite session behind the TestClient (StaticPool + check_same_thread=False:
the sync endpoint runs in a worker thread, and a plain :memory: engine would hand that
thread an empty database). The endpoint deliberately avoids Postgres-only SQL.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.pollen import (
    ATTRIBUTION,
    FRESH_MAX_AGE,
    RECENT_MAX_AGE,
    SOURCE,
    freshness,
    latest_pollen,
    pollen_block,
)
from app.db import Base, get_db
from app.main import app
from app.models import GeoArea, PollenSnapshot
from app.source_status import record_source_run, source_freshness

NOW = datetime.now(UTC)
SLOT = NOW.replace(minute=0, second=0, microsecond=0)
REGISTRY = Path(__file__).resolve().parents[3] / "docs" / "data" / "source-registry.md"


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    app.dependency_overrides[get_db] = lambda: session
    try:
        yield session
    finally:
        app.dependency_overrides.pop(get_db, None)
        session.close()
        engine.dispose()


def _area(db, id=1, slug="klodzko") -> GeoArea:
    area = GeoArea(id=id, slug=slug, name=slug.title(), latitude=50.43, longitude=16.65)
    db.add(area)
    db.commit()
    return area


def _row(db, *, hours_from_now=0, ref=None, fetched_at=None, area_id=1, **species):
    ref = ref or NOW.replace(hour=0, minute=0, second=0, microsecond=0)
    valid_at = SLOT + timedelta(hours=hours_from_now)
    db.add(
        PollenSnapshot(
            source_id="open_meteo_pollen",
            source_record_id=f"{area_id}:{valid_at.isoformat()}:{ref.isoformat()}",
            geo_area_id=area_id,
            alder=species.get("alder"),
            birch=species.get("birch"),
            grass=species.get("grass"),
            mugwort=species.get("mugwort"),
            ragweed=species.get("ragweed"),
            unit="grains/m³",
            model="cams_europe",
            forecast_reference_time=ref,
            valid_at=valid_at,
            fetched_at=fetched_at or NOW,
        )
    )
    db.commit()


def _get() -> dict:
    resp = TestClient(app).get("/api/v1/pollen/latest")
    assert resp.status_code == 200
    return resp.json()


def test_empty_db_is_unavailable_not_a_clean_bill(db):
    body = _get()
    assert body["areas"] == []
    assert body["source_status"] == {"freshness": "UNAVAILABLE", "last_success_at": None}


def test_source_and_attribution_are_verbatim_from_the_registry(db):
    body = _get()
    assert body["source"] == SOURCE == "open_meteo_pollen"
    assert body["attribution"] == ATTRIBUTION
    assert ATTRIBUTION in REGISTRY.read_text(encoding="utf-8")


def test_current_hour_values_model_label_and_explicit_nulls(db):
    _area(db)
    _row(db, alder=0.0, birch=12.5, ragweed=3.0)  # grass/mugwort: no model value
    body = _get()

    (area,) = body["areas"]
    assert area["slug"] == "klodzko"
    assert area["kind"] == "model_forecast"  # never presented as a measurement (rule #7)
    assert area["model"] == "cams_europe"
    assert area["unit"] == "grains/m³"
    assert area["freshness"] == "FRESH"
    assert datetime.fromisoformat(area["valid_at"].replace("Z", "+00:00")) == SLOT
    assert area["current"] == {
        "alder": 0.0,  # a real modelled zero stays 0
        "birch": 12.5,
        "grass": None,  # missing stays null, never 0
        "mugwort": None,
        "ragweed": 3.0,
    }


def test_all_species_null_is_null_not_zero(db):
    _area(db)
    _row(db)
    (area,) = _get()["areas"]
    assert set(area["current"]) == {"alder", "birch", "grass", "mugwort", "ragweed"}
    assert all(v is None for v in area["current"].values())
    assert all(v is None for v in area["days"][0]["max"].values())


def test_newest_run_wins_over_older_run(db):
    _area(db)
    old_ref = NOW.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    new_ref = old_ref + timedelta(days=1)
    _row(db, ref=old_ref, birch=1.0)
    _row(db, ref=new_ref, birch=99.0)
    (area,) = _get()["areas"]
    assert area["current"]["birch"] == 99.0


def test_days_carry_the_daily_maximum_per_species(db):
    _area(db)
    same_day = 1 if SLOT.hour < 23 else -1  # keep both rows on the current UTC day
    _row(db, hours_from_now=0, birch=5.0, grass=None)
    _row(db, hours_from_now=same_day, birch=9.0, grass=2.0)
    _row(db, hours_from_now=30, birch=7.0)  # always a later UTC day
    (area,) = _get()["areas"]
    first_day, later_day = area["days"][0], area["days"][-1]
    assert first_day["date"] == SLOT.date().isoformat()
    assert first_day["max"]["birch"] == 9.0
    assert first_day["max"]["grass"] == 2.0
    assert later_day["max"]["birch"] == 7.0
    assert later_day["max"]["grass"] is None
    assert [d["date"] for d in area["days"]] == sorted(d["date"] for d in area["days"])


def test_run_not_covering_the_current_hour_has_no_current_and_reads_stale(db):
    _area(db)
    old_fetch = NOW - timedelta(days=6)
    _row(
        db,
        hours_from_now=-120,
        ref=old_fetch.replace(hour=0, minute=0, second=0, microsecond=0),
        fetched_at=old_fetch,
        birch=50.0,
    )
    (area,) = _get()["areas"]
    assert area["current"] is None
    assert area["valid_at"] is None
    assert area["freshness"] == "STALE"  # from fetched_at, not from future-dated valid_at
    assert area["days"] == []


def test_orphaned_snapshot_is_skipped(db):
    _row(db, area_id=42, birch=1.0)  # no such geo_area
    assert _get()["areas"] == []


def test_areas_are_independent(db):
    _area(db, 1, "klodzko")
    _area(db, 2, "warszawa")
    _row(db, area_id=1, birch=1.0)
    _row(db, area_id=2, birch=2.0)
    by_slug = {a["slug"]: a for a in _get()["areas"]}
    assert by_slug["klodzko"]["current"]["birch"] == 1.0
    assert by_slug["warszawa"]["current"]["birch"] == 2.0


def test_source_status_reflects_the_last_successful_run(db):
    record_source_run(db, "open_meteo_pollen", success=True)
    status = _get()["source_status"]
    assert status["freshness"] == "FRESH"
    assert status["last_success_at"] is not None


def test_failed_only_source_stays_unavailable(db):
    record_source_run(db, "open_meteo_pollen", success=False, error="down")
    assert _get()["source_status"]["freshness"] == "UNAVAILABLE"


def test_dashboard_block_end_to_end_on_a_real_db(db):
    """TASK-8.9: pollen_block(latest_pollen, source_freshness) - the exact composition the
    dashboard uses - on SQLite (the dashboard's own DISTINCT ON queries are Postgres-only)."""
    _area(db)
    _area(db, id=2, slug="bez-pylkow")  # no snapshots -> not in latest_pollen
    _row(db, birch=12.5)
    record_source_run(db, "open_meteo_pollen", success=True)
    by_area = {a["geo_area_id"]: a for a in latest_pollen(db)}
    status = source_freshness(db, "open_meteo_pollen", freshness)

    block = pollen_block(by_area[1], status)
    assert block["kind"] == "model_forecast" and block["attribution"] == ATTRIBUTION
    assert block["freshness"] == "FRESH" and block["source_status"]["freshness"] == "FRESH"
    assert block["current"]["birch"] == 12.5 and block["current"]["grass"] is None
    assert "slug" not in block and "geo_area_id" not in block

    empty = pollen_block(by_area.get(2), status)
    assert empty["freshness"] == "UNAVAILABLE" and empty["current"] is None
    assert empty["days"] == [] and empty["kind"] == "model_forecast"


class TestFreshness:
    def test_fetched_at_in_the_future_beyond_clock_skew_is_stale(self):
        assert freshness(datetime.now(UTC) + timedelta(hours=1)) == "STALE"
        assert freshness(datetime.now(UTC) + timedelta(minutes=1)) == "FRESH"

    def test_thresholds_follow_the_24h_model_cycle(self):
        assert timedelta(hours=32) == FRESH_MAX_AGE
        assert timedelta(hours=64) == RECENT_MAX_AGE

    @pytest.mark.parametrize(
        ("age", "expected"),
        [
            (timedelta(hours=1), "FRESH"),
            (FRESH_MAX_AGE - timedelta(minutes=1), "FRESH"),
            (FRESH_MAX_AGE + timedelta(minutes=1), "RECENT"),
            (RECENT_MAX_AGE - timedelta(minutes=1), "RECENT"),
            (RECENT_MAX_AGE + timedelta(minutes=1), "STALE"),
        ],
    )
    def test_boundaries(self, age, expected):
        assert freshness(datetime.now(UTC) - age) == expected
