from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.imgw_weather import selected_weather
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


def _seed_area_ids():
    """Areas of the default lists: seed/PRG, never user-chosen places (ADR-029)."""
    return select(GeoArea.id).where(GeoArea.place_id.is_(None))


@router.get("/weather/latest", response_model=WeatherLatestResponse)
def latest_weather(db: Session = Depends(get_db)) -> dict:
    """Reads only from our own DB (rule #14) — never calls Open-Meteo on request.
    Data arrives via `python -m app.connectors.open_meteo.ingest` (manual for now)."""
    # Latest reading per (geo_area, param) — same DISTINCT ON idiom as air.py.
    stmt = (
        select(WeatherSnapshot)
        .where(WeatherSnapshot.geo_area_id.in_(_seed_area_ids()))  # not place areas (ADR-029)
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
    # Default lists exclude user-chosen place areas (ADR-029): those only via an explicit id.
    area_stmt = select(GeoArea).where(GeoArea.id.in_(list(grouped)), GeoArea.place_id.is_(None))
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


def forecasts_by_area(
    db: Session, geo_area_id: int | None = None, *, hourly: bool = False
) -> dict[int, dict]:
    """Latest non-expired forecast per geo_area: {geo_area_id: {model, fetched_at,
    freshness, days, hours}}. Shared by /weather/forecast and /dashboard/latest (TASK-5.5)
    so both present the same prediction. `forecasts` is append-only (ADR-010) -
    several ingest runs can each hold a prediction for the same future day, so
    this picks the freshest run per (geo_area, granularity, period) and returns all
    params of that one run. Only periods that haven't ended yet. `geo_area_id`
    narrows the read to one area (TASK-6.2(8)).

    ADR-030: `hours` (granularity "hourly") are loaded ONLY with `hourly=True` and stay a
    separate list - never mixed into `days`, even though both carry `weather_code`.
    `fetched_at` is the OLDER of the newest fetch of days and of hours: when one of the two
    blocks stopped refreshing, the block must not look fresher than its older part (rule #8)."""
    now = datetime.now(UTC)
    where = [Forecast.valid_until > now]
    if not hourly:
        where.append(Forecast.granularity == "daily")
    if geo_area_id is not None:
        where.append(Forecast.geo_area_id == geo_area_id)
    else:  # default list: filter before loading, place areas keep history after expiry
        where.append(Forecast.geo_area_id.in_(_seed_area_ids()))
    # ONE model run per (area, granularity, period): the newest forecast_reference_time, and
    # all of that run's params - not "the newest row per param". An optional param (daily
    # probability/UV max) that a newer run did not supply must not be filled in from an
    # older run and shown under the newer run's reference time / fetched_at (Codex, PR #89).
    latest_run = (
        select(
            Forecast.geo_area_id,
            Forecast.granularity,
            Forecast.valid_from,
            func.max(Forecast.forecast_reference_time).label("run"),
        )
        .where(*where)
        .group_by(Forecast.geo_area_id, Forecast.granularity, Forecast.valid_from)
        .subquery()
    )
    stmt = (
        select(Forecast)
        .join(
            latest_run,
            and_(
                Forecast.geo_area_id == latest_run.c.geo_area_id,
                Forecast.granularity == latest_run.c.granularity,
                Forecast.valid_from == latest_run.c.valid_from,
                Forecast.forecast_reference_time == latest_run.c.run,
            ),
        )
        .order_by(
            Forecast.geo_area_id,
            Forecast.granularity,
            Forecast.valid_from,
            Forecast.param_code,
        )
    )
    # (area, "days" | "hours") -> {valid_from -> rows}. Rows predating ADR-030 / built
    # without the column read as daily.
    grouped: dict[tuple[int, str], dict[datetime, list[Forecast]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row in db.execute(stmt).scalars().all():
        kind = "hours" if row.granularity == "hourly" else "days"
        grouped[(row.geo_area_id, kind)][row.valid_from].append(row)

    result = {}
    for area_id in sorted({area for area, _ in grouped}):
        model = None
        newest: list[datetime] = []  # newest fetched_at of days / of hours (present ones)
        periods: dict[str, list[dict]] = {"days": [], "hours": []}
        for kind in ("days", "hours"):
            periods_map = grouped.get((area_id, kind), {})
            latest_fetched_at = None
            for valid_from in sorted(periods_map):
                rows = periods_map[valid_from]
                model = model or rows[0].model
                fetched = max(r.fetched_at for r in rows)
                if latest_fetched_at is None or fetched > latest_fetched_at:
                    latest_fetched_at = fetched
                period = {
                    "valid_from": valid_from,
                    "valid_until": rows[0].valid_until,
                    "params": {r.param_code: {"value": r.value, "unit": r.unit} for r in rows},
                }
                if kind == "days":
                    period["forecast_reference_time"] = max(r.forecast_reference_time for r in rows)
                periods[kind].append(period)
            if latest_fetched_at is not None:
                newest.append(latest_fetched_at)
        # Freshness reflects how recently we actually fetched (rule #8), using the
        # real fetched_at — not forecast_reference_time, which is deliberately
        # rounded down to the 3h bucket (ADR-010) and would report a fetch done
        # at :59 as up to 3h older than it really is. Not to be confused with
        # valid_until, which only says the forecast period hasn't ended yet — a
        # stalled scheduler still serves old-but-not-expired rows.
        if not newest:
            continue  # no rows (cannot happen: grouped entries are non-empty)
        fetched_at = min(newest)
        result[area_id] = {
            "model": model,
            "fetched_at": fetched_at,
            "freshness": freshness(fetched_at),
            "days": periods["days"],
            "hours": periods["hours"],
        }
    return result


@router.get("/weather/forecast", response_model=WeatherForecastResponse)
def weather_forecast(db: Session = Depends(get_db)) -> dict:
    """Reads only from our own DB (rule #14). See forecasts_by_area()."""
    forecasts = forecasts_by_area(db)
    if not forecasts:
        return {"areas": []}

    area_stmt = select(GeoArea).where(
        GeoArea.id.in_(list(forecasts)),
        GeoArea.place_id.is_(None),  # ADR-029
    )
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


class SelectedWeatherParam(BaseModel):
    value: float
    unit: str
    observed_at: str
    fetched_at: str
    freshness: Literal["FRESH", "RECENT", "STALE"]
    source: str
    source_type: Literal["observation", "forecast"]
    station_id: str | None
    station_name: str | None
    distance_km: float | None
    selection_reason: str | None = None
    fallback_reason: str | None = None


class WeatherObservationStation(BaseModel):
    source: str
    station_id: str
    station_name: str
    distance_km: float
    elevation_m: float | None
    retrieval_status: Literal["ok", "degraded"]
    params: dict[str, SelectedWeatherParam]


class SelectedWeatherResponse(BaseModel):
    geo_area_id: int
    params: dict[str, SelectedWeatherParam]
    observations: list[WeatherObservationStation]
    publication_enabled: bool
    attribution: str
    transformation_notice: str


@router.get("/weather/selected", response_model=SelectedWeatherResponse)
def weather_selected(
    geo_area_id: int = Query(..., ge=1, le=2_147_483_647), db: Session = Depends(get_db)
) -> dict:
    area = db.get(GeoArea, geo_area_id)
    if area is None:
        raise HTTPException(404, "Unknown geo_area_id")
    return selected_weather(db, area)
