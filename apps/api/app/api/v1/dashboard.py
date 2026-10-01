import logging
from collections.abc import Callable, Sequence
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.air_index import air_index
from app.alert_geo import filter_alerts_for_area
from app.api.v1.air import RECENT_MAX_AGE as air_recent_max_age
from app.api.v1.air import AirIndex, AirParam
from app.api.v1.air import freshness as air_freshness
from app.api.v1.alerts import AlertOut, SourceStatusOut, alerts_source_status, current_alerts
from app.api.v1.pollen import PollenValues, latest_pollen, pollen_block
from app.api.v1.pollen import freshness as pollen_freshness
from app.api.v1.weather import RECENT_MAX_AGE as weather_recent_max_age
from app.api.v1.weather import WeatherParam, forecasts_by_area
from app.api.v1.weather import freshness as weather_freshness
from app.connectors.gios.discovery import assignment_candidates, catalog_points
from app.connectors.open_meteo_pollen.parser import SOURCE_ID as POLLEN_SOURCE_ID
from app.db import get_db
from app.geo import REGIONAL_MAX_KM, classify_air_coverage, coverage_radius_km, select_stations
from app.models import GeoArea, Measurement, WeatherSnapshot
from app.outdoor import USABLE_FRESHNESS, OutdoorInputs, Reading, evaluate
from app.source_status import source_freshness

logger = logging.getLogger(__name__)

router = APIRouter()

# TASK-7.1: source transparency (Master Plan Principle 2) - attribution text is
# copied verbatim from docs/data/source-registry.md, not reworded here. Only two
# sources feed this endpoint today, so a constant beats a lookup table (YAGNI).
AIR_SOURCE_ID = "gios"  # source_status rows are keyed by the connector's source_id
WEATHER_SOURCE_ID = "open_meteo"
GIOS_ATTRIBUTION = "Dane: Główny Inspektorat Ochrony Środowiska (GIOŚ)"
OPEN_METEO_ATTRIBUTION = "Weather data by Open-Meteo.com (CC BY 4.0)"
# source-registry.md (imgw_hydro, same terms for imgw_warnings*): verbatim, required.
IMGW_ATTRIBUTION = (
    "Źródłem pochodzenia danych jest Instytut Meteorologii i Gospodarki Wodnej"
    " – Państwowy Instytut Badawczy"
)

# ADR-029: weather/pollen come from model grids (Open-Meteo, CAMS), not from a sensor in the
# place - said explicitly, so a village never looks like it has its own weather station.
GRID_DESCRIPTION = (
    "Prognoza i stan pogody oraz pyłki to wartości modelu dla najbliższego punktu siatki, "
    "nie pomiar w tej miejscowości."
)

# TASK-7.7 / ADR-016: the engine does no unit conversion, so the caller only feeds it
# values whose stored unit is EXACTLY the expected one (strings as our connectors
# store them: Open-Meteo `*_units`, GIOŚ parser). Anything else is dropped (-> missing[]),
# never converted "by eye". Keys = OutdoorInputs fields.
_OUTDOOR_WEATHER_UNITS = {
    "temperature_2m": "°C",
    "apparent_temperature": "°C",
    "precipitation": "mm",
    "wind_speed_10m": "km/h",
    "wind_gusts_10m": "km/h",
    "uv_index": "",
    "visibility": "m",
}
_OUTDOOR_AIR = {"PM2.5": ("pm25", "µg/m³"), "PM10": ("pm10", "µg/m³")}  # param_code -> field


# TASK-2.1: explicit response contract of /dashboard/latest (OpenAPI -> TS types in
# packages/api-contract, ADR-024). Mirrors EXACTLY what the endpoint returned as a bare
# dict: every field is required (a "no data" block is `null`, never an absent key) and
# timestamps stay ISO strings as built below. Reuses the per-endpoint models where the
# shape is identical. FastAPI validates every response against it, so a shape drift
# 500s instead of silently reaching mobile - and pydantic drops unknown keys, so a new
# field must be added here (tests/test_dashboard_contract.py guards both).
# Rule #1: a degraded SOURCE is expressed inside the shape (`pollen.freshness`
# UNAVAILABLE, empty `alerts.items`, `source_status`), it never makes the shape invalid.
Freshness3 = Literal["FRESH", "RECENT", "STALE"]
SourceFreshness = Literal["FRESH", "RECENT", "STALE", "UNAVAILABLE"]


class DashboardWeatherParam(AirParam):
    """Same fields as an air param: value/unit + the param's OWN observed_at/freshness."""


class DashboardAir(BaseModel):
    station_id: str
    station_name: str
    source: Literal["gios"]
    attribution: str
    observed_at: str  # newest of the station's params - a summary, see params[*]
    params: dict[str, AirParam]
    index: AirIndex
    distance_km: float
    assignment_method: str  # ADR-025: how the station was assigned to the area
    # ADR-029: how far-away the station is, explicitly. `regional` (50-100 km) is a far-away
    # station: shown with its distance, but NOT used for the outdoor verdict.
    coverage: Literal["exact", "nearby", "regional"]
    coverage_radius_km: int
    source_status: SourceStatusOut  # TASK-7.3 / ADR-012: the GIOŚ source, not this station


class DashboardWeather(BaseModel):
    source: Literal["open_meteo"]
    attribution: str
    observed_at: str  # newest of any param - a summary, see params[*]
    freshness: Freshness3
    params: dict[str, DashboardWeatherParam]
    source_status: SourceStatusOut  # TASK-7.3 / ADR-012: the Open-Meteo source


class DashboardForecastDay(BaseModel):
    valid_from: str
    valid_until: str
    params: dict[str, WeatherParam]


class DashboardForecast(BaseModel):
    source: Literal["open_meteo"]
    attribution: str
    fetched_at: str
    freshness: Freshness3
    days: list[DashboardForecastDay]


class OutdoorReasonOut(BaseModel):
    code: str
    param: str
    value: float
    threshold: float
    comparison: Literal["gt", "gte", "lt", "lte"]
    unit: str
    level: Literal["MODERATE", "POOR"]


class OutdoorMissingOut(BaseModel):
    group: str
    params: list[str]
    status: Literal["MISSING", "STALE", "INVALID"]
    core: bool
    blocking: bool


class DashboardOutdoor(BaseModel):
    level: Literal["GOOD", "MODERATE", "POOR", "UNKNOWN"]
    reasons: list[OutdoorReasonOut]
    missing: list[OutdoorMissingOut]
    valid_until: str | None


class DashboardPollenDay(BaseModel):
    date: str  # UTC calendar day, YYYY-MM-DD
    max: PollenValues


class DashboardPollen(BaseModel):
    """One /pollen/latest area + source fields (TASK-8.9). UNAVAILABLE = no snapshot for
    the area (or the whole block failed): null values, never 0."""

    source: str
    attribution: str
    kind: Literal["model_forecast"]
    model: str | None
    unit: str | None
    forecast_reference_time: str | None
    fetched_at: str | None
    freshness: SourceFreshness
    valid_at: str | None
    current: PollenValues | None
    days: list[DashboardPollenDay]
    source_status: SourceStatusOut


class DashboardCoverage(BaseModel):
    """What the area's numbers represent (ADR-029): never imply a measurement in the place
    itself when it is a station kilometres away or a model grid."""

    # exact <=10 km | nearby <=50 | regional <=100 | none = no GIOŚ station within 100 km
    # (air UNAVAILABLE, never "good"). The distance/name live in `air`.
    air: Literal["exact", "nearby", "regional", "none"]
    air_radius_km: int | None
    # Weather and pollen are model-grid values for the point, not measurements in the place.
    weather: Literal["grid"]
    pollen: Literal["grid"]
    grid_description: str


class DashboardArea(BaseModel):
    geo_area_id: int
    slug: str
    name: str
    latitude: float
    longitude: float
    # TASK-6.2(8): False = nobody polls this area (an imported gmina nobody activated), so
    # the null/UNAVAILABLE blocks below mean "no data collected here", not a broken source.
    weather_polling_active: bool
    air: DashboardAir | None
    weather: DashboardWeather | None
    forecast: DashboardForecast | None
    outdoor: DashboardOutdoor
    pollen: DashboardPollen
    coverage: DashboardCoverage
    # ADR-013: the part of the national `alerts.items` that applies to THIS area (TERYT
    # prefix match, `geo_match` says how). Additive; `alerts` stays the national list.
    local_alerts: list[AlertOut]


class DashboardAlerts(BaseModel):
    scope: Literal["national"]
    source: str
    attribution: str
    items: list[AlertOut]
    source_status: dict[str, SourceStatusOut]


class DashboardSourceStatus(BaseModel):
    """Per source, outside the nullable per-area blocks (`air`/`weather` are null without a
    station/snapshot - "never succeeded" must stay distinguishable there)."""

    air: SourceStatusOut
    weather: SourceStatusOut


class DashboardResponse(BaseModel):
    areas: list[DashboardArea]
    alerts: DashboardAlerts
    source_status: DashboardSourceStatus


@router.get("/dashboard/latest", response_model=DashboardResponse)
def dashboard_latest(
    geo_area_id: int | None = Query(None, ge=1, le=2_147_483_647), db: Session = Depends(get_db)
) -> dict:
    """Combined per-location view: weather (per geo_area, always) + nearest GIOŚ
    station's full param set (within REGIONAL_MAX_KM, classified by ADR-029 `coverage`;
    ADR-006 nearest-station join, not a general geo engine). Reads only from our own DB
    (rule #14); the join happens in Python - three small independent result sets,
    not worth a cross-table SQL join.

    TASK-4.1: nearest station now carries every ingested param (PM2.5/PM10/NO2/
    SO2/O3/CO/C6H6), not just PM2.5 — same `params` dict shape as /air/latest.

    TASK-6.2(8) / ADR-026: `?geo_area_id=N` narrows `areas` to that one area (any known
    area, also one without active polling - it then carries `weather_polling_active=false`
    and empty blocks instead of vanishing); unknown id = 404. Without it: the actively
    polled areas, as before (imported gminas must not fan out into ~2.5k areas)."""
    areas: Sequence[GeoArea]
    if geo_area_id is not None:
        chosen = db.get(GeoArea, geo_area_id)
        if chosen is None:
            raise HTTPException(status_code=404, detail="geo_area not found")
        areas = [chosen]
    else:
        area_stmt = select(GeoArea).where(GeoArea.weather_polling_active.is_(True))
        areas = db.execute(area_stmt).scalars().all()

    # source_id filter: `measurements` is shared with other connectors (e.g.
    # imgw_hydro's water_level_cm) — without it the nearest-station join could
    # match a river gauge instead of an air station (Codex review).
    station_stmt = (
        select(Measurement)
        .where(Measurement.source_id == "gios")
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
    # ADR-025: catalog is the authority for who may be assigned and where they are.
    # Geography (coverage) comes from the whole catalog; the `air` block only from stations
    # that already have measurements. A nearer station without data is not skipped.
    points = list(
        {
            sid: (sid, lat, lon)
            for sid, lat, lon in catalog_points(db) + assignment_candidates(db, stations)
        }.values()
    )

    weather_stmt = select(WeatherSnapshot)
    if geo_area_id is not None:
        weather_stmt = weather_stmt.where(WeatherSnapshot.geo_area_id == geo_area_id)
    weather_stmt = weather_stmt.distinct(
        WeatherSnapshot.geo_area_id, WeatherSnapshot.param_code
    ).order_by(
        WeatherSnapshot.geo_area_id,
        WeatherSnapshot.param_code,
        WeatherSnapshot.observed_at.desc(),
    )
    weather_by_area: dict[int, list[WeatherSnapshot]] = {}
    for snapshot in db.execute(weather_stmt).scalars().all():
        weather_by_area.setdefault(snapshot.geo_area_id, []).append(snapshot)

    # TASK-5.5: forecast was only reachable via /weather/forecast, which nothing
    # consumed - the user never saw it. Same helper, so both show one prediction.
    forecasts = forecasts_by_area(db, geo_area_id)

    # TASK-7.3 / ADR-012: source-level status for air and weather, like hydro/pollen.
    # Isolated (rule #1): a failing read degrades these blocks to UNAVAILABLE instead of
    # failing the dashboard. Computed once per request, shared by every area.
    air_status = _source_status(db, AIR_SOURCE_ID, air_freshness)
    weather_status = _source_status(db, WEATHER_SOURCE_ID, weather_freshness)

    # Read once: the national list feeds both `alerts` and each area's `local_alerts`.
    national_alerts = current_alerts(db)

    areas_out = []
    for area in areas:
        # ADR-006/ADR-025/ADR-029: deterministic nearest station within REGIONAL_MAX_KM
        # (geo.select_stations), classified exact/nearby/regional; none in range = no air
        # block (coverage "none"), never a farther fallback.
        match = next(
            iter(select_stations(area.latitude, area.longitude, points, max_km=REGIONAL_MAX_KM)),
            None,
        )
        air_coverage = classify_air_coverage(match.distance_km if match else None)

        air = None
        if match is not None and air_coverage != "none" and match.station_id in stations:
            nearest = stations[match.station_id]
            # source+observed_at+freshness together, not source alone (Principle 2 /
            # TASK-7.1) - observed_at here is the latest across this station's params,
            # same aggregation weather already does below.
            air_observed_at = max(p["observed_at"] for p in nearest["params"].values())
            air = {
                "station_id": nearest["station_id"],
                "station_name": nearest["station_name"],
                "source": "gios",
                "attribution": GIOS_ATTRIBUTION,
                "observed_at": air_observed_at,
                "params": nearest["params"],
                # ADR-015: EAQI from the params already loaded (no extra query, rule #14).
                "index": air_index(nearest["params"], air_recent_max_age),
                "distance_km": round(match.distance_km, 1),
                "assignment_method": match.method,
                "coverage": air_coverage,
                "coverage_radius_km": coverage_radius_km(air_coverage),
                "source_status": air_status,
            }

        params = weather_by_area.get(area.id, [])
        weather = None
        weather_params: dict[str, dict] = {}
        if params:
            latest_observed_at = max(p.observed_at for p in params)
            weather_params = {
                p.param_code: {
                    "value": p.value,
                    "unit": p.unit,
                    "observed_at": p.observed_at.isoformat(),
                    "freshness": weather_freshness(p.observed_at),
                }
                for p in params
            }
            weather = {
                "source": "open_meteo",
                "attribution": OPEN_METEO_ATTRIBUTION,
                "observed_at": latest_observed_at.isoformat(),
                "freshness": weather_freshness(latest_observed_at),
                # Per-param observed_at/freshness (Codex P1 on PR #50, also applies here):
                # hourly-derived params (dew point/visibility/UV) can stay stale for
                # cycles while `current` keeps refreshing, so the object-level max()
                # above must not be the only freshness a client sees.
                "params": weather_params,
                "source_status": weather_status,
            }

        areas_out.append(
            {
                "geo_area_id": area.id,
                "slug": area.slug,
                "name": area.name,
                "latitude": area.latitude,
                "longitude": area.longitude,
                "weather_polling_active": bool(area.weather_polling_active),
                "air": air,
                "weather": weather,
                "forecast": _forecast_block(forecasts.get(area.id)),
                # ADR-029: a far-away (regional) station must not decide "Na dwór" - the
                # engine then has no air input and cannot return GOOD (air is a core group).
                "outdoor": _outdoor_block(
                    air["params"] if air and air_coverage != "regional" else {}, weather_params
                ),
                "coverage": {
                    "air": air_coverage,
                    "air_radius_km": coverage_radius_km(air_coverage),
                    "weather": "grid",
                    "pollen": "grid",
                    "grid_description": GRID_DESCRIPTION,
                },
                "local_alerts": filter_alerts_for_area(national_alerts, area.teryt_code),
            }
        )

    # TASK-7.2 / §55: alerts belong in the aggregate. Top-level and explicitly
    # scope="national", NOT copied into each area - until TASK-9.5 adds geo
    # matching these are unfiltered for the whole country, and putting them
    # under an area would present another region's alert as local.
    alerts = {
        "scope": "national",
        "source": "imgw",
        "attribution": IMGW_ATTRIBUTION,
        "items": national_alerts,
        # ADR-012: an empty `items` only means "no alerts" when every source here
        # is FRESH/RECENT - otherwise the source is silent, not confirming zero.
        "source_status": alerts_source_status(db),
    }

    # TASK-8.9 / ADR-020: computed LAST and isolated (rule #1) - a failing pollen read or
    # block build must not take the rest of the dashboard down; it degrades to UNAVAILABLE.
    try:
        pollen_by_area = {p["geo_area_id"]: p for p in latest_pollen(db, geo_area_id)}
        pollen_status = source_freshness(db, POLLEN_SOURCE_ID, pollen_freshness)
        for out in areas_out:
            area_pollen = pollen_by_area.get(out["geo_area_id"])
            out["pollen"] = _json(pollen_block(area_pollen, pollen_status))
    except Exception:
        logger.exception("dashboard: pollen block failed")
        db.rollback()  # a failed statement leaves a Postgres transaction aborted
        down = {"freshness": "UNAVAILABLE", "last_success_at": None}
        for out in areas_out:
            out["pollen"] = _json(pollen_block(None, down))

    # Outside the nullable per-area blocks too: `air`/`weather` are null when there is no
    # station nearby / no snapshot, and "source never succeeded" must stay distinguishable
    # from "healthy source, nothing applicable" there (Codex review).
    source_status = {"air": air_status, "weather": weather_status}
    return {"areas": areas_out, "alerts": alerts, "source_status": source_status}


def _source_status(db: Session, source_id: str, freshness: Callable[[datetime], str]) -> dict:
    try:
        return source_freshness(db, source_id, freshness)
    except Exception:
        logger.exception("dashboard: source_status for %s failed", source_id)
        db.rollback()  # a failed statement leaves a Postgres transaction aborted
        return {"freshness": "UNAVAILABLE", "last_success_at": None}


def _json(block: dict) -> dict:
    """pollen_block carries datetime/date objects (shared with /pollen/latest); the rest of
    this payload is ISO strings, so convert exactly like FastAPI did for the bare dict
    (isoformat) - keeps the JSON byte-identical (a datetime field would emit `Z`)."""
    return jsonable_encoder(block)


def _reading(
    param: dict | None, unit: str, recent_max_age: timedelta, expires: list[datetime]
) -> Reading | None:
    if param is None or param["unit"] != unit:
        return None
    if param["freshness"] in USABLE_FRESHNESS:
        # Last instant this input is still RECENT - after it the engine would drop it.
        expires.append(datetime.fromisoformat(param["observed_at"]) + recent_max_age)
    return Reading(param["value"], param["freshness"])


def _outdoor_block(air_params: dict, weather_params: dict) -> dict:
    """ADR-016 engine verdict from the rows already loaded above (no extra query,
    rule #14). DERIVED value (rule #10: deterministic rules, never a safety source);
    verbatim from the engine, nothing is classified again here.

    `valid_until` = earliest moment a usable input turns STALE: the verdict was judged
    at request time, and a screen that stays open must not keep asserting it past that
    (rule #8). None when no input fed the verdict (UNKNOWN)."""
    expires: list[datetime] = []
    fields = {
        f: _reading(weather_params.get(f), unit, weather_recent_max_age, expires)
        for f, unit in _OUTDOOR_WEATHER_UNITS.items()
    }
    for code, (field, unit) in _OUTDOOR_AIR.items():
        fields[field] = _reading(air_params.get(code), unit, air_recent_max_age, expires)
    result = evaluate(OutdoorInputs(**fields))
    return {
        "level": result.rating.value,
        "reasons": [{**asdict(r), "level": r.level.value} for r in result.reasons],
        "missing": [{**asdict(m), "params": list(m.params)} for m in result.missing],
        "valid_until": min(expires).isoformat() if expires else None,
    }


def _forecast_block(forecast: dict | None) -> dict | None:
    """Source transparency (Principle 2) like the other blocks: source +
    attribution + when we fetched it + freshness, never a bare number."""
    if forecast is None:
        return None
    return {
        "source": "open_meteo",
        "attribution": OPEN_METEO_ATTRIBUTION,
        "fetched_at": forecast["fetched_at"].isoformat(),
        "freshness": forecast["freshness"],
        "days": [
            {
                "valid_from": day["valid_from"].isoformat(),
                "valid_until": day["valid_until"].isoformat(),
                "params": day["params"],
            }
            for day in forecast["days"]
        ],
    }
