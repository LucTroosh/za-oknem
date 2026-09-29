"""Parse / validate / normalize raw Open-Meteo JSON into WeatherSnapshot-ready dicts.

Shape per official docs (open-meteo.com/en/docs), NOT confirmed against a live
sample in this sandbox (see client.py / source-registry.md). Fails loudly on any
unexpected shape rather than guessing (same lesson as the GIOŚ connector).
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from app.connectors.open_meteo.client import CURRENT_PARAMS, DAILY_PARAMS

PARAM_CODES = CURRENT_PARAMS.split(",")
FORECAST_PARAM_CODES = DAILY_PARAMS.split(",")

# Open-Meteo's own documented default `models` value when none is requested
# (ADR-010) - not an invented label.
DEFAULT_MODEL = "auto"

# Real fetch cadence for this connector (ADR-004) - forecast_reference_time is
# bucketed to this, not the raw fetch instant. See ADR-010 for why.
FETCH_CYCLE_HOURS = 3


class OpenMeteoParseError(Exception):
    """Raised when an Open-Meteo payload doesn't match the expected shape."""


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
                    f"daily[{param_code!r}] must be a list of length {len(days)}, "
                    f"got {series!r}"
                )
    except (KeyError, TypeError) as exc:
        raise OpenMeteoParseError(f"malformed daily-forecast payload: {exc}") from exc

    reference_hour = (fetched_at.hour // FETCH_CYCLE_HOURS) * FETCH_CYCLE_HOURS
    forecast_reference_time = fetched_at.replace(
        hour=reference_hour, minute=0, second=0, microsecond=0
    )

    records = []
    for day_index, day_str in enumerate(days):
        try:
            valid_from = datetime.strptime(day_str, "%Y-%m-%d").replace(tzinfo=UTC)
        except (TypeError, ValueError) as exc:
            raise OpenMeteoParseError(f"malformed forecast date {day_str!r}: {exc}") from exc
        valid_until = valid_from + timedelta(days=1)

        for param_code in FORECAST_PARAM_CODES:
            try:
                value = float(daily[param_code][day_index])
                unit = str(units[param_code])
            except (KeyError, TypeError, ValueError, IndexError) as exc:
                raise OpenMeteoParseError(
                    f"missing/invalid daily param {param_code!r} for {day_str!r}: {exc}"
                ) from exc

            records.append(
                {
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
                    "valid_until": valid_until,
                    "fetched_at": fetched_at,
                }
            )
    return records
