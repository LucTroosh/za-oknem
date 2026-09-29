from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.imgw_hydro.parser import WATER_LEVEL_PARAM
from app.db import get_db
from app.models import Measurement

router = APIRouter()

# ADR-008: update cadence isn't documented by IMGW - 1h is a starting assumption
# (matches GIOŚ, same government-data domain), not a verified cycle. Revisit once
# real observed timestamps show the actual interval.
FRESH_MAX_AGE = timedelta(hours=2)
RECENT_MAX_AGE = timedelta(hours=6)


def freshness(observed_at: datetime) -> str:
    age = datetime.now(UTC) - observed_at
    if age <= FRESH_MAX_AGE:
        return "FRESH"
    if age <= RECENT_MAX_AGE:
        return "RECENT"
    return "STALE"


@router.get("/hydro/latest")
def latest_hydro(db: Session = Depends(get_db)) -> dict:
    """Reads only from our own DB (rule #14) - never calls IMGW on request.
    Data arrives via `python -m app.connectors.imgw_hydro.ingest` or the scheduler."""
    stmt = (
        select(Measurement)
        .where(Measurement.param_code == WATER_LEVEL_PARAM)
        .distinct(Measurement.station_id)
        .order_by(Measurement.station_id, Measurement.observed_at.desc())
    )
    rows = db.execute(stmt).scalars().all()

    if not rows:
        return {"stations": []}

    return {
        "stations": [
            {
                "station_id": row.station_id,
                "station_name": row.station_name,
                "latitude": row.latitude,
                "longitude": row.longitude,
                "water_level_cm": row.value,
                "unit": row.unit,
                "observed_at": row.observed_at.isoformat(),
                "freshness": freshness(row.observed_at),
                "source": "imgw_hydro",
            }
            for row in rows
        ]
    }
