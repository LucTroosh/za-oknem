from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Measurement

router = APIRouter()

# Thresholds for freshness status (Principle 3 / §42). PM2.5 station data updates
# roughly hourly in practice — not yet verified via ADR-004, conservative for now.
FRESH_MAX_AGE = timedelta(hours=2)
RECENT_MAX_AGE = timedelta(hours=6)


def freshness(observed_at: datetime) -> str:
    age = datetime.now(UTC) - observed_at
    if age <= FRESH_MAX_AGE:
        return "FRESH"
    if age <= RECENT_MAX_AGE:
        return "RECENT"
    return "STALE"


@router.get("/air/latest")
def latest_air_quality(db: Session = Depends(get_db)) -> dict:
    """Reads only from our own DB (rule #14) — never calls GIOŚ on request.
    Data arrives via `python -m app.connectors.gios.ingest` (manual for now, Phase 4)."""
    # Latest reading per station: one query, no N+1 — distinct on station_id ordered
    # by observed_at desc is the standard Postgres idiom for "latest per group".
    #
    # ponytail: newer SQLAlchemy (2.1+) deprecates this expression-based .distinct()
    # in favor of sqlalchemy.dialects.postgresql.distinct_on(), but the exact new
    # API shape wasn't reliably verifiable from docs at the time of writing (worth
    # confirming against the real changelog, not guessing, before switching — same
    # lesson as the GIOŚ connector). Still correct and fully covered by tests, just
    # noisy in pytest output. Upgrade when SQLAlchemy actually removes the old form.
    stmt = (
        select(Measurement)
        .where(Measurement.param_code == "PM2.5")
        .distinct(Measurement.station_id)
        .order_by(Measurement.station_id, Measurement.observed_at.desc())
    )
    rows = db.execute(stmt).scalars().all()

    if not rows:
        # no data != zero (Principle §43) — empty list, not fabricated 0s
        return {"stations": []}

    return {
        "stations": [
            {
                "station_id": row.station_id,
                "station_name": row.station_name,
                "latitude": row.latitude,
                "longitude": row.longitude,
                "pm25": row.value,
                "unit": row.unit,
                "observed_at": row.observed_at.isoformat(),
                "freshness": freshness(row.observed_at),
                "source": "gios",
            }
            for row in rows
        ]
    }
