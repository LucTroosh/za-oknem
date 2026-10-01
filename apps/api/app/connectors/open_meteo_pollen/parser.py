"""Parse / validate / normalize an Open-Meteo Air Quality payload (pollen) into
PollenSnapshot-ready dicts (ADR-020).

Shape per official docs (hourly.time + one parallel array per variable, hourly_units),
NOT confirmed against a live sample in this sandbox (see client.py). Fails loudly on
anything unexpected rather than guessing (rule #10/#15).
"""

import math
from datetime import UTC, datetime
from typing import Any

from app.connectors.open_meteo_pollen.client import DOMAIN, HOURLY_PARAMS

SOURCE_ID = "open_meteo_pollen"

# API variable -> PollenSnapshot column (Master Plan §6: olcha, brzoza, trawy, bylica,
# ambrozja). Order follows HOURLY_PARAMS.
SPECIES_BY_VARIABLE = {
    "alder_pollen": "alder",
    "birch_pollen": "birch",
    "grass_pollen": "grass",
    "mugwort_pollen": "mugwort",
    "ragweed_pollen": "ragweed",
}
assert list(SPECIES_BY_VARIABLE) == HOURLY_PARAMS.split(",")

# CAMS Europe is produced once a day (ADR-004/ADR-020); forecast_reference_time is our
# fetch instant bucketed to that 24h cycle - Open-Meteo does not expose the model run
# time (same documented approximation as ADR-010).
MODEL = DOMAIN
REFERENCE_CYCLE_HOURS = 24

# Stored with every raw fetch (ADR-014). Bump when parse/normalize output changes
# (including the set of requested variables).
PARSER_VERSION = "1"


class OpenMeteoPollenParseError(Exception):
    """Raised when a payload doesn't match the expected shape."""


def _value(raw: Any, variable: str, time: str) -> float | None:
    if raw is None:
        return None  # model gave no value (e.g. outside the pollen season) - NOT zero
    if isinstance(raw, bool) or not isinstance(raw, int | float):
        raise OpenMeteoPollenParseError(f"{variable} at {time}: not a number: {raw!r}")
    if not math.isfinite(raw) or raw < 0:
        raise OpenMeteoPollenParseError(f"{variable} at {time}: impossible value {raw!r}")
    return float(raw)


def normalize(
    *,
    geo_area_id: int,
    payload: dict[str, Any],
    fetched_at: datetime,
) -> list[dict[str, Any]]:
    """One PollenSnapshot-ready dict per hourly slot, all five species in it.
    Raises OpenMeteoPollenParseError on a malformed payload."""
    try:
        if payload.get("utc_offset_seconds", 0) != 0:
            raise ValueError(
                f"expected UTC (timezone=UTC requested), got {payload.get('timezone')!r}"
            )
        hourly = payload["hourly"]
        units = payload["hourly_units"]
        times = hourly["time"]
        if not isinstance(times, list) or not times:
            raise TypeError("hourly.time must be a non-empty list")
        series: dict[str, list[Any]] = {}
        for variable in SPECIES_BY_VARIABLE:
            values = hourly[variable]
            if not isinstance(values, list) or len(values) != len(times):
                raise TypeError(f"hourly[{variable!r}] must be a list of length {len(times)}")
            series[variable] = values
        unit_values = {str(units[variable]) for variable in SPECIES_BY_VARIABLE}
        if len(unit_values) != 1:
            raise ValueError(f"species units differ: {sorted(unit_values)}")
        unit = unit_values.pop()
        valid_times = [
            datetime.fromisoformat(str(t)).replace(tzinfo=UTC) for t in times
        ]  # timezone=UTC requested, so the naive stamps ARE UTC
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise OpenMeteoPollenParseError(f"malformed pollen payload: {exc}") from exc

    reference = fetched_at.replace(
        hour=(fetched_at.hour // REFERENCE_CYCLE_HOURS) * REFERENCE_CYCLE_HOURS,
        minute=0,
        second=0,
        microsecond=0,
    )
    records: list[dict[str, Any]] = []
    for i, valid_at in enumerate(valid_times):
        species = {
            column: _value(series[variable][i], variable, str(times[i]))
            for variable, column in SPECIES_BY_VARIABLE.items()
        }
        records.append(
            {
                "source_id": SOURCE_ID,
                "source_record_id": (
                    f"{geo_area_id}:{valid_at.isoformat()}:{reference.isoformat()}"
                ),
                "geo_area_id": geo_area_id,
                **species,
                "unit": unit,
                "model": MODEL,
                "forecast_reference_time": reference,
                "valid_at": valid_at,
                "fetched_at": fetched_at,
            }
        )
    return records
