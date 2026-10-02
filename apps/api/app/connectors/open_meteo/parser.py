"""Parse / validate / normalize raw Open-Meteo JSON into WeatherSnapshot-ready dicts.

Shape per official docs (open-meteo.com/en/docs), NOT confirmed against a live
sample in this sandbox (see client.py / source-registry.md). Fails loudly on any
unexpected shape rather than guessing (same lesson as the GIOŚ connector).
"""

import math
from datetime import UTC, datetime, timedelta
from typing import Any

from app.connectors.open_meteo.client import (
    CURRENT_PARAMS,
    DAILY_PARAMS_CORE,
    DAILY_PARAMS_OPTIONAL,
    HOURLY_FORECAST_HOURS,
    HOURLY_FORECAST_PARAMS,
    HOURLY_PARAMS,
)

PARAM_CODES = CURRENT_PARAMS.split(",")
# Core daily params are strict (one missing value fails the block, ADR-010); the optional
# ones (probability max, UV max) are skipped when the model does not provide them (ADR-030).
FORECAST_PARAM_CODES = DAILY_PARAMS_CORE.split(",")
OPTIONAL_FORECAST_PARAM_CODES = DAILY_PARAMS_OPTIONAL.split(",")
HOURLY_PARAM_CODES = HOURLY_PARAMS.split(",")
HOURLY_FORECAST_PARAM_CODES = HOURLY_FORECAST_PARAMS.split(",")

# Open-Meteo's own documented default `models` value when none is requested
# (ADR-010) - not an invented label.
DEFAULT_MODEL = "auto"

# Real fetch cadence for this connector (ADR-004) - forecast_reference_time is
# bucketed to this, not the raw fetch instant. See ADR-010 for why.
FETCH_CYCLE_HOURS = 3


# Stored with every raw fetch (ADR-014). Bump when parse/normalize output changes
# (including the set of requested fields), so old payloads stay interpretable.
PARSER_VERSION = "2"  # 2: hourly forecast + optional daily params (ADR-030)


class OpenMeteoParseError(Exception):
    """Raised when an Open-Meteo payload doesn't match the expected shape."""


def _finite(value: Any) -> float | None:
    """float(value) when it is a real finite number (not bool/None/str/NaN), else None."""
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        return None
    return float(value)


def _reference_time(fetched_at: datetime) -> datetime:
    """Our fetch time bucketed down to the real fetch cycle (ADR-010)."""
    reference_hour = (fetched_at.hour // FETCH_CYCLE_HOURS) * FETCH_CYCLE_HOURS
    return fetched_at.replace(hour=reference_hour, minute=0, second=0, microsecond=0)


def normalize(
    *,
    geo_area_id: int,
    payload: dict[str, Any],
    fetched_at: datetime,
) -> list[dict[str, Any]]:
    """One WeatherSnapshot-ready dict per requested current-weather param.
    Raises OpenMeteoParseError on anything missing (rule #1: a bad payload for one
    geo_area must not silently produce wrong readings or crash the whole ingest run
    — ingest.py is what isolates that failure per geo_area, this just refuses to
    guess)."""
    try:
        current = payload["current"]
        units = payload["current_units"]
        # timezone=UTC was requested explicitly in client.py, so this naive
        # timestamp IS UTC wall-clock time.
        observed_at = datetime.fromisoformat(current["time"]).replace(tzinfo=UTC)
    except (KeyError, TypeError, ValueError) as exc:
        raise OpenMeteoParseError(f"malformed current-weather payload: {exc}") from exc

    snapshots = []
    for param_code in PARAM_CODES:
        try:
            value = float(current[param_code])
            unit = str(units[param_code])
        except (KeyError, TypeError, ValueError) as exc:
            raise OpenMeteoParseError(f"missing/invalid param {param_code!r}: {exc}") from exc

        snapshots.append(
            {
                "source_id": "open_meteo",
                "source_record_id": f"{geo_area_id}:{param_code}:{observed_at.isoformat()}",
                "geo_area_id": geo_area_id,
                "param_code": param_code,
                "value": value,
                "unit": unit,
                "observed_at": observed_at,
                "fetched_at": fetched_at,
            }
        )
    return snapshots


def normalize_hourly_current(
    *,
    geo_area_id: int,
    payload: dict[str, Any],
    fetched_at: datetime,
) -> list[dict[str, Any]]:
    """One WeatherSnapshot-ready dict per requested `hourly` param (TASK-5.4:
    dew point, visibility, UV index — Open-Meteo only documents these under
    `hourly`, not `current`), picking the entry for the hour `current` falls
    in. `observed_at` is that hourly slot's own timestamp (not `current`'s,
    which can be a few minutes into the hour) - it's the truthful time the
    value represents.

    Kept independent of normalize()'s `current` parsing (own try/except in
    ingest.py) so a problem here doesn't cost the already-proven current
    fields, same isolation as normalize_forecast() (rule #1, TASK-5.3)."""
    try:
        current_time = datetime.fromisoformat(payload["current"]["time"]).replace(tzinfo=UTC)
        hourly = payload["hourly"]
        units = payload["hourly_units"]
        hours = hourly["time"]
        if not isinstance(hours, list):
            raise TypeError(f"hourly.time must be a list, got {type(hours).__name__}")
    except (KeyError, TypeError, ValueError) as exc:
        raise OpenMeteoParseError(f"malformed hourly payload: {exc}") from exc

    slot = current_time.replace(minute=0, second=0, microsecond=0)
    slot_str = slot.strftime("%Y-%m-%dT%H:%M")
    try:
        hour_index = hours.index(slot_str)
    except ValueError as exc:
        raise OpenMeteoParseError(
            f"no hourly.time entry for current hour {slot_str!r}: {exc}"
        ) from exc

    snapshots = []
    for param_code in HOURLY_PARAM_CODES:
        try:
            value = float(hourly[param_code][hour_index])
            unit = str(units[param_code])
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise OpenMeteoParseError(
                f"missing/invalid hourly param {param_code!r}: {exc}"
            ) from exc

        snapshots.append(
            {
                "source_id": "open_meteo",
                "source_record_id": f"{geo_area_id}:{param_code}:{slot.isoformat()}",
                "geo_area_id": geo_area_id,
                "param_code": param_code,
                "value": value,
                "unit": unit,
                "observed_at": slot,
                "fetched_at": fetched_at,
            }
        )
    return snapshots


def normalize_forecast(
    *,
    geo_area_id: int,
    payload: dict[str, Any],
    fetched_at: datetime,
) -> list[dict[str, Any]]:
    """One Forecast-ready dict per requested daily param per forecast day
    (ADR-010, Master Plan §30 - never a Measurement/WeatherSnapshot, rule #7).

    Raises OpenMeteoParseError on a malformed `daily` block - kept independent
    of normalize()'s `current` parsing so a problem in one block doesn't cost
    the other its otherwise-valid data (rule #1, same lesson as TASK-9.3:
    isolate the actual failure, don't let it swallow unrelated good data)."""
    try:
        daily = payload["daily"]
        units = payload["daily_units"]
        days = daily["time"]
        if not isinstance(days, list):
            raise TypeError(f"daily.time must be a list, got {type(days).__name__}")
        for param_code in FORECAST_PARAM_CODES:
            series = daily[param_code]
            if not isinstance(series, list) or len(series) != len(days):
                raise TypeError(
                    f"daily[{param_code!r}] must be a list of length {len(days)}, got {series!r}"
                )
    except (KeyError, TypeError) as exc:
        raise OpenMeteoParseError(f"malformed daily-forecast payload: {exc}") from exc

    forecast_reference_time = _reference_time(fetched_at)

    def _daily_record(
        geo_area_id: int, param_code: str, value: float, unit: str, valid_from: datetime
    ) -> dict[str, Any]:
        return {
            "source_id": "open_meteo",
            "source_record_id": (
                f"{geo_area_id}:{param_code}:{valid_from.isoformat()}:"
                f"{forecast_reference_time.isoformat()}"
            ),
            "geo_area_id": geo_area_id,
            "param_code": param_code,
            "value": value,
            "unit": unit,
            "model": DEFAULT_MODEL,
            "forecast_reference_time": forecast_reference_time,
            "valid_from": valid_from,
            "valid_until": valid_from + timedelta(days=1),
            "fetched_at": fetched_at,
        }

    records = []
    for day_index, day_str in enumerate(days):
        try:
            valid_from = datetime.strptime(day_str, "%Y-%m-%d").replace(tzinfo=UTC)
        except (TypeError, ValueError) as exc:
            raise OpenMeteoParseError(f"malformed forecast date {day_str!r}: {exc}") from exc

        for param_code in FORECAST_PARAM_CODES:
            try:
                value = float(daily[param_code][day_index])
                unit = str(units[param_code])
            except (KeyError, TypeError, ValueError, IndexError) as exc:
                raise OpenMeteoParseError(
                    f"missing/invalid daily param {param_code!r} for {day_str!r}: {exc}"
                ) from exc

            records.append(_daily_record(geo_area_id, param_code, value, unit, valid_from))

        for param_code in OPTIONAL_FORECAST_PARAM_CODES:
            # ADR-030: absent series / null value / no unit = this param is skipped for this
            # day; it never costs the core params above (rule #1).
            series = daily.get(param_code)
            if not isinstance(series, list) or len(series) != len(days):
                continue
            value = _finite(series[day_index])
            unit = units.get(param_code)
            if value is None or not isinstance(unit, str):
                continue
            records.append(_daily_record(geo_area_id, param_code, value, unit, valid_from))
    return records


def normalize_hourly_forecast(
    *,
    geo_area_id: int,
    payload: dict[str, Any],
    fetched_at: datetime,
) -> list[dict[str, Any]]:
    """One Forecast-ready dict (granularity "hourly", ADR-030) per forecast param per hour,
    for the HOURLY_FORECAST_HOURS hours starting at the hour `current` falls in (that
    hour's slot is part of the request's whole-day `hourly` arrays; the earlier hours of
    today are dropped, they are not a forecast). Never a Measurement (rule #7).

    Only the SHAPE of the block is strict (no `hourly`/`hourly_units`/`time` list = raises,
    the other blocks are unaffected, rule #1). A missing series, a missing unit, a null /
    non-finite value or an unparsable time loses just that value - one null hour must not
    cost the other 47 hours or the other params. Raises when not a single value is usable,
    so an empty block is a failed block (provenance/source status), not a quiet success."""
    try:
        hourly = payload["hourly"]
        units = payload["hourly_units"]
        times = hourly["time"]
        if not isinstance(times, list) or not isinstance(units, dict):
            raise TypeError("hourly.time must be a list and hourly_units an object")
    except (KeyError, TypeError) as exc:
        raise OpenMeteoParseError(f"malformed hourly-forecast payload: {exc}") from exc

    # Window start = the hour of the payload's own `current` (deterministic for a payload);
    # an unreadable `current` falls back to our fetch time.
    try:
        anchor = datetime.fromisoformat(payload["current"]["time"]).replace(tzinfo=UTC)
    except (KeyError, TypeError, ValueError):
        anchor = fetched_at
    start = anchor.replace(minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=HOURLY_FORECAST_HOURS)
    reference = _reference_time(fetched_at)

    slots: list[datetime | None] = []
    for raw in times:
        try:
            slots.append(datetime.strptime(raw, "%Y-%m-%dT%H:%M").replace(tzinfo=UTC))
        except (TypeError, ValueError):
            slots.append(None)  # that hour is skipped for every param

    records = []
    for param_code in HOURLY_FORECAST_PARAM_CODES:
        series = hourly.get(param_code)
        unit = units.get(param_code)
        if not isinstance(series, list) or len(series) != len(times) or not isinstance(unit, str):
            continue  # cannot align this param with `time`: skip it entirely
        for slot, raw_value in zip(slots, series, strict=True):
            value = _finite(raw_value)
            if slot is None or value is None or not start <= slot < end:
                continue
            records.append(
                {
                    "source_id": "open_meteo",
                    "source_record_id": (
                        f"hourly:{geo_area_id}:{param_code}:{slot.isoformat()}:"
                        f"{reference.isoformat()}"
                    ),
                    "geo_area_id": geo_area_id,
                    "param_code": param_code,
                    "value": value,
                    "unit": unit,
                    "model": DEFAULT_MODEL,
                    "forecast_reference_time": reference,
                    "valid_from": slot,
                    "valid_until": slot + timedelta(hours=1),
                    "fetched_at": fetched_at,
                    "granularity": "hourly",
                }
            )
    if not records:
        raise OpenMeteoParseError("hourly forecast: no usable values in the forecast window")
    return records
