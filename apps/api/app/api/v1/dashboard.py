import logging
from dataclasses import asdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.air_index import air_index
from app.api.v1.air import RECENT_MAX_AGE as air_recent_max_age
from app.api.v1.air import freshness as air_freshness
from app.api.v1.alerts import alerts_source_status, current_alerts
from app.api.v1.pollen import freshness as pollen_freshness
from app.api.v1.pollen import latest_pollen, pollen_block
from app.api.v1.weather import RECENT_MAX_AGE as weather_recent_max_age
from app.api.v1.weather import forecasts_by_area
from app.api.v1.weather import freshness as weather_freshness
from app.connectors.gios.discovery import current_station_ids
from app.connectors.open_meteo_pollen.parser import SOURCE_ID as POLLEN_SOURCE_ID
from app.db import get_db
from app.geo import select_stations
from app.models import GeoArea, Measurement, WeatherSnapshot
from app.outdoor import USABLE_FRESHNESS, OutdoorInputs, Reading, evaluate
from app.source_status import source_freshness

logger = logging.getLogger(__name__)

router = APIRouter()

# TASK-7.1: source transparency (Master Plan Principle 2) - attribution text is
# copied verbatim from docs/data/source-registry.md, not reworded here. Only two
# sources feed this endpoint today, so a constant beats a lookup table (YAGNI).
GIOS_ATTRIBUTION = "Dane: Główny Inspektorat Ochrony Środowiska (GIOŚ)"
OPEN_METEO_ATTRIBUTION = "Weather data by Open-Meteo.com (CC BY 4.0)"
# source-registry.md (imgw_hydro, same terms for imgw_warnings*): verbatim, required.
IMGW_ATTRIBUTION = (
    "Źródłem pochodzenia danych jest Instytut Meteorologii i Gospodarki Wodnej"
    " – Państwowy Instytut Badawczy"
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


@router.get("/dashboard/latest")
def dashboard_latest(db: Session = Depends(get_db)) -> dict:
    """Combined per-location view: weather (per geo_area, always) + nearest GIOŚ
    station's full param set (only within MAX_MATCH_DISTANCE_KM - ADR-006
    nearest-station join, not a general geo engine). Reads only from our own DB
    (rule #14); the join happens in Python - three small independent result sets,
    not worth a cross-table SQL join.

    TASK-4.1: nearest station now carries every ingested param (PM2.5/PM10/NO2/
    SO2/O3/CO/C6H6), not just PM2.5 — same `params` dict shape as /air/latest."""
    # ADR-019: imported gminas (geo-matching only) must not fan out here until TASK-6.2(8)
    # narrows the dashboard to a chosen location - only actively polled areas are listed.
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
    allowed = current_station_ids(db)  # ADR-024: never assign a station dropped by GIOŚ
    if allowed is not None:
        stations = {k: v for k, v in stations.items() if k in allowed}
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
    for snapshot in db.execute(weather_stmt).scalars().all():
        weather_by_area.setdefault(snapshot.geo_area_id, []).append(snapshot)

    # TASK-5.5: forecast was only reachable via /weather/forecast, which nothing
    # consumed - the user never saw it. Same helper, so both show one prediction.
    forecasts = forecasts_by_area(db)

    areas_out = []
    for area in areas:
        # ADR-006/ADR-024: deterministic nearest station within MAX_MATCH_DISTANCE_KM
        # (geo.select_stations); none in range = no air block, never a farther fallback.
        match = next(
            iter(
                select_stations(
                    area.latitude,
                    area.longitude,
                    [(s["station_id"], s["latitude"], s["longitude"]) for s in stations_list],
                )
            ),
            None,
        )

        air = None
        if match is not None:
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
                "forecast": _forecast_block(forecasts.get(area.id)),
                "outdoor": _outdoor_block(air["params"] if air else {}, weather_params),
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
        "items": current_alerts(db),
        # ADR-012: an empty `items` only means "no alerts" when every source here
        # is FRESH/RECENT - otherwise the source is silent, not confirming zero.
        "source_status": alerts_source_status(db),
    }

    # TASK-8.9 / ADR-020: computed LAST and isolated (rule #1) - a failing pollen read or
    # block build must not take the rest of the dashboard down; it degrades to UNAVAILABLE.
    try:
        pollen_by_area = {p["geo_area_id"]: p for p in latest_pollen(db)}
        pollen_status = source_freshness(db, POLLEN_SOURCE_ID, pollen_freshness)
        for out in areas_out:
            out["pollen"] = pollen_block(pollen_by_area.get(out["geo_area_id"]), pollen_status)
    except Exception:
        logger.exception("dashboard: pollen block failed")
        db.rollback()  # a failed statement leaves a Postgres transaction aborted
        down = {"freshness": "UNAVAILABLE", "last_success_at": None}
        for out in areas_out:
            out["pollen"] = pollen_block(None, down)

    return {"areas": areas_out, "alerts": alerts}


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
