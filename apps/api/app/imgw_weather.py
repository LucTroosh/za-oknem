"""DB-only observation selection. No averaging or substitution of unlike variables."""

import math
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.geo import haversine_km
from app.models import GeoArea, ImgwWeatherStation, Measurement, SourceStatus, WeatherSnapshot

IMGW_ATTRIBUTION = (
    "Źródłem pochodzenia danych jest Instytut Meteorologii i Gospodarki Wodnej"
    " – Państwowy Instytut Badawczy"
)
IMGW_TRANSFORMATION = (
    "Dane Instytutu Meteorologii i Gospodarki Wodnej – Państwowego Instytutu"
    " Badawczego zostały przetworzone"
)
UNITS = {"temperature_2m": "°C", "relative_humidity_2m": "%"}


def utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def freshness(value: datetime, *, now: datetime | None = None) -> str:
    age = (now or datetime.now(UTC)) - utc(value)
    if age < -timedelta(minutes=5):
        return "STALE"
    return "FRESH" if age <= timedelta(minutes=30) else "STALE"


def publication_allowed() -> bool:
    return bool(
        settings.imgw_observations_publication_enabled
        and settings.imgw_weather_timezone
        and settings.imgw_weather_semantics_verified
    )


def observations(db: Session, area: GeoArea) -> list[dict]:
    if not publication_allowed():
        return []
    now = datetime.now(UTC)
    rank = (
        select(
            Measurement.id,
            func.row_number()
            .over(
                partition_by=(
                    Measurement.source_id,
                    Measurement.station_id,
                    Measurement.param_code,
                ),
                order_by=(Measurement.observed_at.desc(), Measurement.id.asc()),
            )
            .label("rank"),
        )
        .where(
            Measurement.source_id.in_(("imgw_meteo", "imgw_synop")),
            Measurement.observed_at <= now + timedelta(minutes=5),
        )
        .subquery()
    )
    rows = db.scalars(
        select(Measurement).join(rank, Measurement.id == rank.c.id).where(rank.c.rank == 1)
    ).all()
    catalogs = {
        (s.source_id, s.station_id): s for s in db.scalars(select(ImgwWeatherStation)).all()
    }
    statuses = {
        s.source_id: s
        for s in db.scalars(
            select(SourceStatus).where(SourceStatus.source_id.in_(("imgw_meteo", "imgw_synop")))
        ).all()
    }
    groups: dict[tuple[str, str], dict] = {}
    for row in rows:
        station = catalogs.get((row.source_id, row.station_id))
        if station is None or station.latitude is None or station.longitude is None:
            continue
        distance = haversine_km(area.latitude, area.longitude, station.latitude, station.longitude)
        if distance > settings.imgw_observation_max_distance_km or not math.isfinite(row.value):
            continue
        key = (row.source_id, row.station_id)
        if key not in groups:
            status = statuses.get(row.source_id)
            healthy = bool(
                status
                and status.last_success_at
                and not status.last_error
                and timedelta(minutes=-5)
                <= datetime.now(UTC) - utc(status.last_success_at)
                <= timedelta(minutes=30)
            )
            groups[key] = {
                "source": row.source_id,
                "station_id": station.station_id,
                "station_name": station.name,
                "distance_km": round(distance, 2),
                "elevation_m": station.elevation_m,
                "retrieval_status": "ok" if healthy else "degraded",
                "params": {},
            }
        groups[key]["params"][row.param_code] = {
            "value": row.value,
            "unit": row.unit,
            "observed_at": utc(row.observed_at).isoformat(),
            "fetched_at": utc(row.fetched_at).isoformat(),
            "freshness": freshness(row.observed_at),
            "source": row.source_id,
            "source_type": "observation",
            "station_id": row.station_id,
            "station_name": row.station_name,
            "distance_km": round(distance, 2),
        }
    return sorted(groups.values(), key=lambda s: (s["distance_km"], s["source"], s["station_id"]))


def selected_weather(db: Session, area: GeoArea) -> dict:
    # Keep the model contract intact. New consumers use this additive selection block.
    now = datetime.now(UTC)
    rank = (
        select(
            WeatherSnapshot.id,
            func.row_number()
            .over(
                partition_by=WeatherSnapshot.param_code,
                order_by=(WeatherSnapshot.observed_at.desc(), WeatherSnapshot.id.asc()),
            )
            .label("rank"),
        )
        .where(
            WeatherSnapshot.geo_area_id == area.id,
            WeatherSnapshot.source_id == "open_meteo",
            WeatherSnapshot.observed_at <= now + timedelta(minutes=5),
        )
        .subquery()
    )
    params = {
        r.param_code: {
            "value": r.value,
            "unit": r.unit,
            "observed_at": utc(r.observed_at).isoformat(),
            "fetched_at": utc(r.fetched_at).isoformat(),
            "freshness": "FRESH"
            if now - utc(r.observed_at) <= timedelta(hours=4)
            else "RECENT"
            if now - utc(r.observed_at) <= timedelta(hours=8)
            else "STALE",
            "source": "open_meteo",
            "source_type": "forecast",
            "station_id": None,
            "station_name": None,
            "distance_km": None,
            "selection_reason": "model_fallback",
            "fallback_reason": "imgw_unavailable",
        }
        for r in db.scalars(
            select(WeatherSnapshot)
            .join(rank, WeatherSnapshot.id == rank.c.id)
            .where(rank.c.rank == 1)
        ).all()
        if math.isfinite(r.value)
    }
    nearby = observations(db, area)
    altitude = settings.imgw_area_elevations_m.get(area.id)
    candidates: dict[str, list[dict]] = {}
    for station in nearby:
        if station["retrieval_status"] != "ok":
            continue
        if (
            altitude is None
            or station["elevation_m"] is None
            or abs(altitude - station["elevation_m"]) > 150
        ):
            continue
        for code, value in station["params"].items():
            if code in UNITS and value["unit"] == UNITS[code] and value["freshness"] == "FRESH":
                candidates.setdefault(code, []).append(value)
    for code, values in candidates.items():
        params[code] = {
            **values[0],
            "selection_reason": "imgw_fresh_representative",
            "fallback_reason": None,
        }
    return {
        "geo_area_id": area.id,
        "params": params,
        "observations": nearby,
        "publication_enabled": publication_allowed(),
        "attribution": IMGW_ATTRIBUTION,
        "transformation_notice": IMGW_TRANSFORMATION,
    }
