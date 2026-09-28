from collections import defaultdict
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import GeoArea, WeatherSnapshot

router = APIRouter()

# Open-Meteo (ICON model) refreshes every 3h (ADR-004, source-registry.md) — thresholds
# sized off that real cycle, not guessed: FRESH within one cycle, RECENT within ~2.5.
FRESH_MAX_AGE = timedelta(hours=4)
RECENT_MAX_AGE = timedelta(hours=8)


def freshness(observed_at: datetime) -> str:
    age = datetime.now(UTC) - observed_at
    if age <= FRESH_MAX_AGE:
        return "FRESH"
    if age <= RECENT_MAX_AGE:
        return "RECENT"
    return "STALE"


@router.get("/weather/latest")
def latest_weather(db: Session = Depends(get_db)) -> dict:
    """Reads only from our own DB (rule #14) — never calls Open-Meteo on request.
    Data arrives via `python -m app.connectors.open_meteo.ingest` (manual for now)."""
    # Latest reading per (geo_area, param) — same DISTINCT ON idiom as air.py.
    stmt = (
        select(WeatherSnapshot)
        .distinct(WeatherSnapshot.geo_area_id, WeatherSnapshot.param_code)
        .order_by(
            WeatherSnapshot.geo_area_id,
            WeatherSnapshot.param_code,
            WeatherSnapshot.observed_at.desc(),
        )
    )
    rows = db.execute(stmt).scalars().all()

    if not rows:
        return {"areas": []}

    areas_by_id = {a.id: a for a in db.execute(select(GeoArea)).scalars().all()}

    grouped: dict[int, list[WeatherSnapshot]] = defaultdict(list)
    for row in rows:
        grouped[row.geo_area_id].append(row)

    areas = []
    for geo_area_id, params in grouped.items():
        area = areas_by_id.get(geo_area_id)
        if area is None:
            continue  # orphaned snapshot (deleted geo_area) - skip, don't fabricate
        latest_observed_at = max(p.observed_at for p in params)
        areas.append(
            {
                "geo_area_id": area.id,
                "slug": area.slug,
                "name": area.name,
                "latitude": area.latitude,
                "longitude": area.longitude,
                "observed_at": latest_observed_at.isoformat(),
                "freshness": freshness(latest_observed_at),
                "params": {p.param_code: {"value": p.value, "unit": p.unit} for p in params},
                "source": "open_meteo",
            }
        )

    return {"areas": areas}
