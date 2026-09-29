from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Forecast, GeoArea, WeatherSnapshot

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


# TASK-API-2: response_model - same reasoning as TASK-API-1 (air.py). Mirrors the
# existing dict shapes exactly - no API change.
class WeatherParam(BaseModel):
    value: float
    unit: str


# Separate from WeatherParam (Codex review, cross-referenced from PR#50): a stale
# hourly-derived param (dew_point/visibility/uv_index, TASK-5.4) can silently share
# a fresh `current` param's object-level freshness, since WeatherArea.freshness below
# is only max(observed_at) across all params. /weather/latest needs each param's own
# observed_at+freshness to catch that; /weather/forecast's ForecastDay.params has no
# per-param observation time (forecast rows have valid_from/valid_until instead), so
# it keeps the plain WeatherParam shape.
class WeatherLatestParam(BaseModel):
    value: float
    unit: str
    observed_at: datetime
    freshness: Literal["FRESH", "RECENT", "STALE"]


class WeatherArea(BaseModel):
    geo_area_id: int
    slug: str
    name: str
    latitude: float
    longitude: float
    # Rough "most recent of any param" summary, not authoritative per param — see
    # WeatherLatestParam.freshness for the real per-param status.
    observed_at: datetime
    freshness: Literal["FRESH", "RECENT", "STALE"]
    params: dict[str, WeatherLatestParam]
    source: Literal["open_meteo"]


class WeatherLatestResponse(BaseModel):
    areas: list[WeatherArea]


class ForecastDay(BaseModel):
    valid_from: datetime
    valid_until: datetime
    forecast_reference_time: datetime
    params: dict[str, WeatherParam]


class ForecastArea(BaseModel):
    geo_area_id: int
    slug: str
    name: str
    latitude: float
    longitude: float
    model: str
    fetched_at: datetime
    freshness: Literal["FRESH", "RECENT", "STALE"]
    days: list[ForecastDay]
    source: Literal["open_meteo"]


class WeatherForecastResponse(BaseModel):
    areas: list[ForecastArea]


@router.get("/weather/latest", response_model=WeatherLatestResponse)
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
                "observed_at": latest_observed_at,
                "freshness": freshness(latest_observed_at),
                "params": {
                    p.param_code: {
                        "value": p.value,
                        "unit": p.unit,
                        "observed_at": p.observed_at,
                        "freshness": freshness(p.observed_at),
                    }
                    for p in params
                },
                "source": "open_meteo",
            }
        )

    return {"areas": areas}


@router.get("/weather/forecast", response_model=WeatherForecastResponse)
def weather_forecast(db: Session = Depends(get_db)) -> dict:
    """Reads only from our own DB (rule #14). `forecasts` is append-only
    (ADR-010) - several ingest runs can each hold a prediction for the same
    future day, so this picks the freshest one per (geo_area, day, param) via
    ORDER BY forecast_reference_time DESC, same DISTINCT ON idiom as
    latest_weather(). Only days that haven't passed yet are returned."""
    now = datetime.now(UTC)
    stmt = (
        select(Forecast)
        .where(Forecast.valid_until > now)
        .distinct(Forecast.geo_area_id, Forecast.valid_from, Forecast.param_code)
        .order_by(
            Forecast.geo_area_id,
            Forecast.valid_from,
            Forecast.param_code,
            Forecast.forecast_reference_time.desc(),
        )
    )
    rows = db.execute(stmt).scalars().all()

    if not rows:
        return {"areas": []}

    areas_by_id = {a.id: a for a in db.execute(select(GeoArea)).scalars().all()}

    by_area_days: dict[int, dict[datetime, list[Forecast]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        by_area_days[row.geo_area_id][row.valid_from].append(row)

    areas = []
    for geo_area_id, days_map in by_area_days.items():
        area = areas_by_id.get(geo_area_id)
        if area is None:
            continue  # orphaned forecast (deleted geo_area) - skip, don't fabricate

        days = []
        model = None
        latest_fetched_at = None
        for valid_from in sorted(days_map):
            day_rows = days_map[valid_from]
            model = day_rows[0].model
            day_fetched_at = max(r.fetched_at for r in day_rows)
            if latest_fetched_at is None or day_fetched_at > latest_fetched_at:
                latest_fetched_at = day_fetched_at
            days.append(
                {
                    "valid_from": valid_from,
                    "valid_until": day_rows[0].valid_until,
                    "forecast_reference_time": max(r.forecast_reference_time for r in day_rows),
                    "params": {r.param_code: {"value": r.value, "unit": r.unit} for r in day_rows},
                }
            )

        # Freshness reflects how recently we actually fetched (rule #8), using the
        # real fetched_at — not forecast_reference_time, which is deliberately
        # rounded down to the 3h bucket (ADR-010) and would report a fetch done
        # at :59 as up to 3h older than it really is. Not to be confused with
        # valid_until, which only says the forecast period hasn't ended yet — a
        # stalled scheduler still serves old-but-not-expired rows.
        areas.append(
            {
                "geo_area_id": area.id,
                "slug": area.slug,
                "name": area.name,
                "latitude": area.latitude,
                "longitude": area.longitude,
                "model": model,
                "fetched_at": latest_fetched_at,
                "freshness": freshness(latest_fetched_at),
                "days": days,
                "source": "open_meteo",
            }
        )

    return {"areas": areas}
