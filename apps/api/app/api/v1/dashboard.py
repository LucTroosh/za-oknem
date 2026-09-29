from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.air import freshness as air_freshness
from app.api.v1.weather import freshness as weather_freshness
from app.db import get_db
from app.geo import haversine_km
from app.models import GeoArea, Measurement, WeatherSnapshot

router = APIRouter()

# ADR-006: nearest-station join threshold - deliberately conservative so we never
# fake a match between locations that aren't actually close together.
MAX_MATCH_DISTANCE_KM = 50.0


@router.get("/dashboard/latest")
def dashboard_latest(db: Session = Depends(get_db)) -> dict:
    """Combined per-location view: weather (per geo_area, always) + nearest GIOŚ
    station's full param set (only within MAX_MATCH_DISTANCE_KM - ADR-006
    nearest-station join, not a general geo engine). Reads only from our own DB
    (rule #14); the join happens in Python - three small independent result sets,
    not worth a cross-table SQL join.

    TASK-4.1: nearest station now carries every ingested param (PM2.5/PM10/NO2/
    SO2/O3/CO/C6H6), not just PM2.5 — same `params` dict shape as /air/latest."""
    areas = db.execute(select(GeoArea)).scalars().all()

    station_stmt = (
        select(Measurement)
        .distinct(Measurement.station_id, Measurement.param_code)
        .order_by(Measurement.station_id, Measurement.param_code, Measurement.observed_at.desc())
    )
    stations: dict[str, dict] = {}
    for row in db.execute(station_stmt).scalars().all():
        station = stations.setdefault(
            row.station_id,
            {
                "station_id": row.station_id,
                "station_name": row.station_name,
                "latitude": row.latitude,
                "longitude": row.longitude,
                "params": {},
            },
        )
        station["params"][row.param_code] = {
            "value": row.value,
            "unit": row.unit,
            "observed_at": row.observed_at.isoformat(),
            "freshness": air_freshness(row.observed_at),
        }
    stations_list = list(stations.values())

    weather_stmt = (
        select(WeatherSnapshot)
        .distinct(WeatherSnapshot.geo_area_id, WeatherSnapshot.param_code)
        .order_by(
            WeatherSnapshot.geo_area_id,
            WeatherSnapshot.param_code,
            WeatherSnapshot.observed_at.desc(),
        )
    )
    weather_by_area: dict[int, list[WeatherSnapshot]] = {}
    for row in db.execute(weather_stmt).scalars().all():
        weather_by_area.setdefault(row.geo_area_id, []).append(row)

    areas_out = []
    for area in areas:
        nearest, nearest_km = None, None
        for station in stations_list:
            km = haversine_km(
                area.latitude, area.longitude, station["latitude"], station["longitude"]
            )
            if nearest_km is None or km < nearest_km:
                nearest, nearest_km = station, km

        air = None
        if nearest is not None and nearest_km is not None and nearest_km <= MAX_MATCH_DISTANCE_KM:
            air = {
                "station_id": nearest["station_id"],
                "station_name": nearest["station_name"],
                "params": nearest["params"],
                "distance_km": round(nearest_km, 1),
            }

        params = weather_by_area.get(area.id, [])
        weather = None
        if params:
            latest_observed_at = max(p.observed_at for p in params)
            weather = {
                "observed_at": latest_observed_at.isoformat(),
                "freshness": weather_freshness(latest_observed_at),
                "params": {p.param_code: {"value": p.value, "unit": p.unit} for p in params},
            }

        areas_out.append(
            {
                "geo_area_id": area.id,
                "slug": area.slug,
                "name": area.name,
                "latitude": area.latitude,
                "longitude": area.longitude,
                "air": air,
                "weather": weather,
            }
        )

    return {"areas": areas_out}
