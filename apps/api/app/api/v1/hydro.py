from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.alerts import SourceStatusOut
from app.api.v1.dashboard import IMGW_ATTRIBUTION
from app.config import settings
from app.connectors.imgw_hydro.parser import (
    ALARM_LEVEL_PARAM,
    WARNING_LEVEL_PARAM,
    WATER_LEVEL_PARAM,
)
from app.db import get_db
from app.models import Measurement
from app.source_status import source_freshness

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


# TASK-API-3: response_model - same reasoning as TASK-API-1/API-2. Mirrors the
# existing dict shape exactly - no API change.
class HydroStation(BaseModel):
    station_id: str
    station_name: str
    latitude: float
    longitude: float
    water_level_cm: float
    warning_level_cm: float | None
    alarm_level_cm: float | None
    status: Literal["NORMAL", "WARNING", "ALARM", "UNKNOWN"]
    unit: str
    observed_at: str
    freshness: Literal["FRESH", "RECENT", "STALE"]
    source: Literal["imgw_hydro"]


class HydroLatestResponse(BaseModel):
    publication_enabled: bool = True
    stations: list[HydroStation]
    # TASK-7.2: source transparency (verbatim from source-registry.md) and ADR-012
    # source-level freshness, so a client can tell "no stations in alarm" from
    # "IMGW hydro hasn't been fetched successfully for hours".
    attribution: str
    source_status: SourceStatusOut


@router.get("/hydro/latest", response_model=HydroLatestResponse)
def latest_hydro(db: Session = Depends(get_db)) -> dict:
    """Reads only from our own DB (rule #14) - never calls IMGW on request.
    Data arrives via `python -m app.connectors.imgw_hydro.ingest` or the scheduler."""
    if not settings.imgw_hydro_publication_enabled:
        return {
            "stations": [],
            "publication_enabled": False,
            "attribution": IMGW_ATTRIBUTION,
            "source_status": {"freshness": "UNAVAILABLE", "last_success_at": None},
        }
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

    return {
        "stations": stations,
        "attribution": IMGW_ATTRIBUTION,
        "source_status": source_freshness(db, "imgw_hydro", freshness),
    }
