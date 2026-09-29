from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.imgw_hydro.parser import (
    ALARM_LEVEL_PARAM,
    WARNING_LEVEL_PARAM,
    WATER_LEVEL_PARAM,
)
from app.db import get_db
from app.models import Measurement

router = APIRouter()

_THRESHOLD_PARAMS = (WARNING_LEVEL_PARAM, ALARM_LEVEL_PARAM)

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


def compute_status(value: float, warning: float | None, alarm: float | None) -> str:
    """NORMAL/WARNING/ALARM by comparing the observed water level against IMGW's
    own published per-station thresholds (rule #10: a numeric comparison of two
    officially published numbers, not an interpretation or a guess). UNKNOWN when
    the station has no thresholds defined - confirmed live for some stations
    (e.g. lake gauges), not a data gap on our side."""
    if warning is None and alarm is None:
        return "UNKNOWN"
    if alarm is not None and value >= alarm:
        return "ALARM"
    if warning is not None and value >= warning:
        return "WARNING"
    return "NORMAL"


@router.get("/hydro/latest")
def latest_hydro(db: Session = Depends(get_db)) -> dict:
    """Reads only from our own DB (rule #14) - never calls IMGW on request.
    Data arrives via `python -m app.connectors.imgw_hydro.ingest` or the scheduler."""
    stmt = (
        select(Measurement)
        .where(Measurement.param_code.in_((WATER_LEVEL_PARAM, *_THRESHOLD_PARAMS)))
        .distinct(Measurement.station_id, Measurement.param_code)
        .order_by(Measurement.station_id, Measurement.param_code, Measurement.observed_at.desc())
    )
    rows = db.execute(stmt).scalars().all()

    by_station: dict[str, dict[str, Measurement]] = {}
    for row in rows:
        by_station.setdefault(row.station_id, {})[row.param_code] = row

    stations = []
    for by_param in by_station.values():
        level_row = by_param.get(WATER_LEVEL_PARAM)
        if level_row is None:
            continue  # thresholds with no current reading for this station - not shown
        warning_row = by_param.get(WARNING_LEVEL_PARAM)
        alarm_row = by_param.get(ALARM_LEVEL_PARAM)
        # No extra staleness check needed here: ingest.py upserts/deletes each
        # threshold's single row every run, so whatever's stored IS the current
        # IMGW-reported value (or absent if withdrawn) - see parser.py/ingest.py.
        warning_value = warning_row.value if warning_row else None
        alarm_value = alarm_row.value if alarm_row else None
        stations.append(
            {
                "station_id": level_row.station_id,
                "station_name": level_row.station_name,
                "latitude": level_row.latitude,
                "longitude": level_row.longitude,
                "water_level_cm": level_row.value,
                "warning_level_cm": warning_value,
                "alarm_level_cm": alarm_value,
                "status": compute_status(level_row.value, warning_value, alarm_value),
                "unit": level_row.unit,
                "observed_at": level_row.observed_at.isoformat(),
                "freshness": freshness(level_row.observed_at),
                "source": "imgw_hydro",
            }
        )

    return {"stations": stations}
