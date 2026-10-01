from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.alerts import SourceStatusOut
from app.connectors.open_meteo_pollen.parser import SOURCE_ID, SPECIES_BY_VARIABLE
from app.db import get_db
from app.models import GeoArea, PollenSnapshot
from app.source_status import MAX_CLOCK_SKEW, source_freshness

router = APIRouter()

# CAMS Europe is produced once a day (ADR-004, source-registry.md `open_meteo_pollen`),
# fetched once a day (24h). Thresholds are ~1.3x / ~2.7x that cycle - the same ratios
# weather uses for its 3h cycle (4h / 8h). Measured from fetched_at, not from the
# model's valid_at (a forecast's valid_at is in the future by design).
FRESH_MAX_AGE = timedelta(hours=32)
RECENT_MAX_AGE = timedelta(hours=64)

# Verbatim from docs/data/source-registry.md `open_meteo_pollen` (ADR-020): the CAMS
# ENSEMBLE data provider and Open-Meteo must both be credited.
SOURCE = "open_meteo_pollen"
ATTRIBUTION = (
    "Pollen forecast: Copernicus Atmosphere Monitoring Service (CAMS) European "
    "air quality forecast, via Open-Meteo.com (CC BY 4.0). Contains modified "
    "Copernicus Atmosphere Monitoring Service information."
)
SPECIES = tuple(SPECIES_BY_VARIABLE.values())  # alder, birch, grass, mugwort, ragweed


def freshness(fetched_at: datetime) -> str:
    age = datetime.now(UTC) - fetched_at
    if age < -MAX_CLOCK_SKEW:  # fetched "in the future" can't be verified (ADR-012): fail safe
        return "STALE"
    if age <= FRESH_MAX_AGE:
        return "FRESH"
    if age <= RECENT_MAX_AGE:
        return "RECENT"
    return "STALE"


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)  # SQLite returns naive datetimes


class PollenValues(BaseModel):
    """grains/m3 per MVP species (Master Plan §6). null = the model gave no value
    (typically outside the pollen season) - NEVER 0 standing in for "no data"."""

    alder: float | None  # olcha
    birch: float | None  # brzoza
    grass: float | None  # trawy
    mugwort: float | None  # bylica
    ragweed: float | None  # ambrozja


class PollenDay(BaseModel):
    date: date  # UTC calendar day
    max: PollenValues  # highest hourly modelled value that day, per species


class PollenArea(BaseModel):
    geo_area_id: int
    slug: str
    name: str
    latitude: float
    longitude: float
    # Rule #7: this is a MODEL FORECAST (CAMS), not a pollen-trap measurement.
    kind: Literal["model_forecast"]
    model: str
    unit: str
    # Approximation (Open-Meteo does not expose the run time): our fetch instant
    # bucketed to the model's 24h cycle.
    forecast_reference_time: datetime
    fetched_at: datetime
    freshness: Literal["FRESH", "RECENT", "STALE"]
    # Hourly slot served as "now" and its values; null when the stored run no longer
    # covers the current hour (scheduler stalled > ~4 days).
    valid_at: datetime | None
    current: PollenValues | None
    days: list[PollenDay]


class PollenLatestResponse(BaseModel):
    areas: list[PollenArea]
    source: str
    attribution: str
    # ADR-012: an empty `areas` or a STALE area must be told apart from "source silent".
    source_status: SourceStatusOut


def _values(row: PollenSnapshot) -> dict[str, float | None]:
    return {s: getattr(row, s) for s in SPECIES}


def _day_max(rows: list[PollenSnapshot]) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for s in SPECIES:
        present = [v for v in (getattr(r, s) for r in rows) if v is not None]
        out[s] = max(present) if present else None
    return out


def latest_pollen(db: Session, geo_area_id: int | None = None) -> list[dict]:
    """Newest forecast run per geo_area, reduced to the current hour + per-day maxima.
    Plain portable SQL (no DISTINCT ON). Reads only our DB (rule #14).
    `geo_area_id` narrows it to one area (TASK-6.2(8))."""
    newest_stmt = select(
        PollenSnapshot.geo_area_id,
        func.max(PollenSnapshot.forecast_reference_time).label("ref"),
    )
    if geo_area_id is not None:
        newest_stmt = newest_stmt.where(PollenSnapshot.geo_area_id == geo_area_id)
    newest = newest_stmt.group_by(PollenSnapshot.geo_area_id).subquery()
    rows = (
        db.execute(
            select(PollenSnapshot)
            .join(
                newest,
                (PollenSnapshot.geo_area_id == newest.c.geo_area_id)
                & (PollenSnapshot.forecast_reference_time == newest.c.ref),
            )
            .order_by(PollenSnapshot.geo_area_id, PollenSnapshot.valid_at)
        )
        .scalars()
        .all()
    )
    if not rows:
        return []

    by_area: dict[int, list[PollenSnapshot]] = defaultdict(list)
    for r in rows:
        by_area[r.geo_area_id].append(r)

    areas_by_id = {
        a.id: a
        for a in db.execute(select(GeoArea).where(GeoArea.id.in_(list(by_area)))).scalars().all()
    }

    now = datetime.now(UTC)
    slot = now.replace(minute=0, second=0, microsecond=0)
    result = []
    for geo_area_id, area_rows in by_area.items():
        area = areas_by_id.get(geo_area_id)
        if area is None:
            continue  # orphaned snapshot (deleted geo_area) - skip, don't fabricate
        current_row = next((r for r in area_rows if _utc(r.valid_at) == slot), None)
        by_day: dict[date, list[PollenSnapshot]] = defaultdict(list)
        for r in area_rows:
            if _utc(r.valid_at).date() >= now.date():
                by_day[_utc(r.valid_at).date()].append(r)
        fetched_at = _utc(max(r.fetched_at for r in area_rows))
        first = area_rows[0]
        result.append(
            {
                "geo_area_id": area.id,
                "slug": area.slug,
                "name": area.name,
                "latitude": area.latitude,
                "longitude": area.longitude,
                "kind": "model_forecast",
                "model": first.model,
                "unit": first.unit,
                "forecast_reference_time": _utc(first.forecast_reference_time),
                "fetched_at": fetched_at,
                "freshness": freshness(fetched_at),
                "valid_at": slot if current_row else None,
                "current": _values(current_row) if current_row else None,
                "days": [{"date": d, "max": _day_max(rs)} for d, rs in sorted(by_day.items())],
            }
        )
    return result


def pollen_block(area: dict | None, source_status: dict) -> dict:
    """Per-area `pollen` block of /dashboard/latest (TASK-8.9). Same fields as one
    /pollen/latest area (ADR-020 verbatim: kind/model/unit/forecast_reference_time/
    fetched_at/freshness) + source/attribution/source_status. No snapshot for the area ->
    freshness UNAVAILABLE and null values (never 0, never a guess)."""
    head = {"source": SOURCE, "attribution": ATTRIBUTION, "kind": "model_forecast"}
    if area is None:
        return {
            **head,
            "model": None,
            "unit": None,
            "forecast_reference_time": None,
            "fetched_at": None,
            "freshness": "UNAVAILABLE",
            "valid_at": None,
            "current": None,
            "days": [],
            "source_status": source_status,
        }
    drop = {"geo_area_id", "slug", "name", "latitude", "longitude", "kind"}  # per-area id / head
    rest = {k: v for k, v in area.items() if k not in drop}
    return {**head, **rest, "source_status": source_status}


@router.get("/pollen/latest", response_model=PollenLatestResponse)
def pollen_latest(db: Session = Depends(get_db)) -> dict:
    """Reads only from our own DB (rule #14) - never calls Open-Meteo/CAMS on request.
    Data arrives via the scheduler (once a day) or
    `python -m app.connectors.open_meteo_pollen.ingest`. No geo-filtering to the
    user's location yet - same as /weather/latest (Geo Engine, TASK-6.x)."""
    return {
        "areas": latest_pollen(db),
        "source": SOURCE,
        "attribution": ATTRIBUTION,
        "source_status": source_freshness(db, SOURCE_ID, freshness),
    }
