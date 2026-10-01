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
    source: str  # provider-neutral source_id (ADR-022)


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
    source: str  # provider-neutral source_id (ADR-022)


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

    grouped: dict[int, list[WeatherSnapshot]] = defaultdict(list)
    for row in rows:
        grouped[row.geo_area_id].append(row)

    # Only the areas that actually have snapshots - never every imported gmina (ADR-019).
    area_stmt = select(GeoArea).where(GeoArea.id.in_(list(grouped)))
    areas_by_id = {a.id: a for a in db.execute(area_stmt).scalars().all()}

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
                # Rough summary only ("most recent of any param") — NOT authoritative
                # per param. `current` params (temperature etc.) refresh every ingest
                # cycle, but the `hourly`-derived ones (dew_point/visibility/uv_index,
                # TASK-5.4) can silently stay stale for cycles when that part of the
                # payload fails while `current` still succeeds (rule #1 isolation) —
                # the max() here would then report this object as FRESH even though
                # some params are actually STALE. Use params.<code>.freshness for the
                # real per-param status (Codex review). Passed as a datetime, not
                # .isoformat() — WeatherArea.observed_at is typed `datetime` (PR#52,
                # Codex review), Pydantic serializes it to an ISO 8601 JSON string.
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


def forecasts_by_area(db: Session, geo_area_id: int | None = None) -> dict[int, dict]:
    """Latest non-expired forecast per geo_area: {geo_area_id: {model, fetched_at,
    freshness, days}}. Shared by /weather/forecast and /dashboard/latest (TASK-5.5)
    so both present the same prediction. `forecasts` is append-only (ADR-010) -
    several ingest runs can each hold a prediction for the same future day, so
    this picks the freshest one per (geo_area, day, param) via ORDER BY
    forecast_reference_time DESC. Only days that haven't passed yet. `geo_area_id`
    narrows the read to one area (TASK-6.2(8))."""
    now = datetime.now(UTC)
    where = [Forecast.valid_until > now]
    if geo_area_id is not None:
        where.append(Forecast.geo_area_id == geo_area_id)
    stmt = (
        select(Forecast)
        .where(*where)
        .distinct(Forecast.geo_area_id, Forecast.valid_from, Forecast.param_code)
        .order_by(
            Forecast.geo_area_id,
            Forecast.valid_from,
            Forecast.param_code,
            Forecast.forecast_reference_time.desc(),
        )
    )
    by_area_days: dict[int, dict[datetime, list[Forecast]]] = defaultdict(lambda: defaultdict(list))
    for row in db.execute(stmt).scalars().all():
        by_area_days[row.geo_area_id][row.valid_from].append(row)

    result = {}
    for geo_area_id, days_map in by_area_days.items():
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
        if latest_fetched_at is None:
            continue  # no day rows (cannot happen: days_map entries are non-empty)
        result[geo_area_id] = {
            "model": model,
            "fetched_at": latest_fetched_at,
            "freshness": freshness(latest_fetched_at),
            "days": days,
        }
    return result


@router.get("/weather/forecast", response_model=WeatherForecastResponse)
def weather_forecast(db: Session = Depends(get_db)) -> dict:
    """Reads only from our own DB (rule #14). See forecasts_by_area()."""
    forecasts = forecasts_by_area(db)
    if not forecasts:
        return {"areas": []}

    area_stmt = select(GeoArea).where(GeoArea.id.in_(list(forecasts)))
    areas_by_id = {a.id: a for a in db.execute(area_stmt).scalars().all()}
    areas = []
    for geo_area_id, forecast in forecasts.items():
        area = areas_by_id.get(geo_area_id)
        if area is None:
            continue  # orphaned forecast (deleted geo_area) - skip, don't fabricate
        areas.append(
            {
                "geo_area_id": area.id,
                "slug": area.slug,
                "name": area.name,
                "latitude": area.latitude,
                "longitude": area.longitude,
                **forecast,
                "source": "open_meteo",
            }
        )
    return {"areas": areas}
