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
    Data arrives via `python -m app.connectors.gios.ingest` (manual for now, Phase 4).

    TASK-4.1: full MVP param set (PM2.5/PM10/NO2/SO2/O3/CO/C6H6), not just PM2.5 —
    each station now returns a `params` dict keyed by param code instead of a single
    top-level `pm25` field."""
    # Latest reading per (station, param): one query, no N+1 — distinct on
    # (station_id, param_code) ordered by observed_at desc is the standard Postgres
    # idiom for "latest per group", extended to two grouping columns.
    #
    # ponytail: newer SQLAlchemy (2.1+) deprecates this expression-based .distinct()
    # in favor of sqlalchemy.dialects.postgresql.distinct_on(), but the exact new
    # API shape wasn't reliably verifiable from docs at the time of writing (worth
    # confirming against the real changelog, not guessing, before switching — same
    # lesson as the GIOŚ connector). Still correct and fully covered by tests, just
    # noisy in pytest output. Upgrade when SQLAlchemy actually removes the old form.
    # source_id filter: `measurements` is shared with other connectors (e.g.
    # imgw_hydro's water_level_cm) — without it this query would also return
    # river-gauge rows here, labeled as GIOŚ air stations (Codex review).
    stmt = (
        select(Measurement)
        .where(Measurement.source_id == "gios")
        .distinct(Measurement.station_id, Measurement.param_code)
        .order_by(Measurement.station_id, Measurement.param_code, Measurement.observed_at.desc())
    )
    rows = db.execute(stmt).scalars().all()

    if not rows:
        # no data != zero (Principle §43) — empty list, not fabricated 0s
        return {"stations": []}

    stations: dict[str, dict] = {}
    for row in rows:
        station = stations.setdefault(
            row.station_id,
            {
                "station_id": row.station_id,
                "station_name": row.station_name,
                "latitude": row.latitude,
                "longitude": row.longitude,
                "params": {},
                "source": "gios",
            },
        )
        station["params"][row.param_code] = {
            "value": row.value,
            "unit": row.unit,
            "observed_at": row.observed_at.isoformat(),
            "freshness": freshness(row.observed_at),
        }

    return {"stations": list(stations.values())}
