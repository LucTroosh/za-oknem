import math
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
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
from app.models import GeoArea, Measurement, SourceStatus
from app.neighborhood import haversine_km
from app.source_status import source_freshness

router = APIRouter()

_THRESHOLD_PARAMS = (WARNING_LEVEL_PARAM, ALARM_LEVEL_PARAM)

# ADR-008: update cadence isn't documented by IMGW - 1h is a starting assumption
# (matches GIOŚ, same government-data domain), not a verified cycle. Revisit once
# real observed timestamps show the actual interval.
FRESH_MAX_AGE = timedelta(hours=2)
RECENT_MAX_AGE = timedelta(hours=6)


def freshness(observed_at: datetime) -> str:
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=UTC)
    age = datetime.now(UTC) - observed_at
    if age < -timedelta(minutes=5):
        return "STALE"
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
    if any(v is not None and not math.isfinite(v) for v in (value, warning, alarm)):
        return "UNKNOWN"
    if warning is not None and alarm is not None and warning > alarm:
        return "UNKNOWN"
    if alarm is not None and value >= alarm:
        return "ALARM"
    if warning is not None and value >= warning:
        return "WARNING"
    return "NORMAL" if warning is not None else "UNKNOWN"


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
    distance_km: float | None = None
    fetched_at: str | None = None


class HydroLatestResponse(BaseModel):
    publication_enabled: bool = True
    scope: Literal["national", "nearby"] = "national"
    search_radius_km: float | None = None
    stations: list[HydroStation]
    # TASK-7.2: source transparency (verbatim from source-registry.md) and ADR-012
    # source-level freshness, so a client can tell "no stations in alarm" from
    # "IMGW hydro hasn't been fetched successfully for hours".
    attribution: str
    source_status: SourceStatusOut


@router.get("/hydro/latest", response_model=HydroLatestResponse)
def latest_hydro(
    db: Session = Depends(get_db),
    geo_area_id: int | None = Query(default=None, ge=1, le=2**31 - 1),
    max_distance_km: float = Query(default=50, gt=0, le=100),
) -> dict:
    """Reads only from our own DB (rule #14) - never calls IMGW on request.
    Data arrives via `python -m app.connectors.imgw_hydro.ingest` or the scheduler."""
    area = db.get(GeoArea, geo_area_id) if geo_area_id is not None else None
    if geo_area_id is not None and area is None:
        raise HTTPException(status_code=404, detail="Unknown geo_area_id")
    scope = {
        "scope": "nearby" if area else "national",
        "search_radius_km": max_distance_km if area else None,
    }
    if not settings.imgw_hydro_publication_enabled:
        return {
            **scope,
            "stations": [],
            "publication_enabled": False,
            "attribution": IMGW_ATTRIBUTION,
            "source_status": {"freshness": "UNAVAILABLE", "last_success_at": None},
        }
    # One latest value per station/parameter, portable to PostgreSQL and SQLite.
    latest = (
        select(
            Measurement.id,
            func.row_number()
            .over(
                partition_by=(Measurement.station_id, Measurement.param_code),
                order_by=(Measurement.observed_at.desc(), Measurement.id.desc()),
            )
            .label("rank"),
        )
        .where(
            Measurement.source_id == "imgw_hydro",
            Measurement.param_code.in_((WATER_LEVEL_PARAM, *_THRESHOLD_PARAMS)),
            Measurement.observed_at <= datetime.now(UTC) + timedelta(minutes=5),
        )
        .subquery()
    )
    stmt = select(Measurement).join(latest, latest.c.id == Measurement.id).where(latest.c.rank == 1)
    rows = db.execute(stmt).scalars().all()

    by_station: dict[str, dict[str, Measurement]] = {}
    for row in rows:
        by_station.setdefault(row.station_id, {})[row.param_code] = row

    stations = []
    for by_param in by_station.values():
        level_row = by_param.get(WATER_LEVEL_PARAM)
        if level_row is None or not math.isfinite(level_row.value):
            continue  # thresholds with no current reading for this station - not shown
        if not (math.isfinite(level_row.latitude) and math.isfinite(level_row.longitude)):
            continue
        if not (-90 <= level_row.latitude <= 90 and -180 <= level_row.longitude <= 180):
            continue
        distance = (
            haversine_km(area.latitude, area.longitude, level_row.latitude, level_row.longitude)
            if area
            else None
        )
        if distance is not None and distance > max_distance_km:
            continue
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
                "distance_km": round(distance, 1) if distance is not None else None,
                "fetched_at": level_row.fetched_at.isoformat(),
            }
        )

    stations.sort(key=lambda s: (s["distance_km"] or 0, s["station_id"]))
    source_status = source_freshness(db, "imgw_hydro", freshness)
    status_row = db.get(SourceStatus, "imgw_hydro")
    if (
        status_row is not None
        and status_row.last_error
        and source_status["freshness"] != "UNAVAILABLE"
    ):
        source_status["freshness"] = "STALE"
    return {
        **scope,
        "stations": stations,
        "attribution": IMGW_ATTRIBUTION,
        "source_status": source_status,
    }
