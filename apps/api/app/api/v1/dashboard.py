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
    station's PM2.5 (only within MAX_MATCH_DISTANCE_KM - ADR-006 nearest-station
    join, not a general geo engine). Reads only from our own DB (rule #14); the
    join happens in Python - three small independent result sets, not worth a
    cross-table SQL join."""
    areas = db.execute(select(GeoArea)).scalars().all()

    station_stmt = (
        select(Measurement)
        .where(Measurement.param_code == "PM2.5")
        .distinct(Measurement.station_id)
        .order_by(Measurement.station_id, Measurement.observed_at.desc())
    )
    stations = db.execute(station_stmt).scalars().all()

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
        for station in stations:
            km = haversine_km(area.latitude, area.longitude, station.latitude, station.longitude)
            if nearest_km is None or km < nearest_km:
                nearest, nearest_km = station, km

        air = None
        if nearest is not None and nearest_km is not None and nearest_km <= MAX_MATCH_DISTANCE_KM:
            air = {
                "station_id": nearest.station_id,
                "station_name": nearest.station_name,
                "pm25": nearest.value,
                "unit": nearest.unit,
                "observed_at": nearest.observed_at.isoformat(),
                "freshness": air_freshness(nearest.observed_at),
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
