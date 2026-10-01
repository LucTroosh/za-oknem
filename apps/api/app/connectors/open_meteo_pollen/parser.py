"""Parse / validate / normalize an Open-Meteo Air Quality payload (pollen) into
PollenSnapshot-ready dicts (ADR-020).

Shape per official docs (hourly.time + one parallel array per variable, hourly_units),
NOT confirmed against a live sample in this sandbox (see client.py). Fails loudly on
anything unexpected rather than guessing (rule #10/#15).
"""

import math
import re
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


# Docs: `timeformat=iso8601` (default) gives "YYYY-MM-DDTHH:MM". Anything else (date-only,
# numeric basic-ISO, unixtime) is a schema change, not a midnight slot.
_HOUR_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?(?P<offset>Z|[+-]\d{2}(?::?\d{2})?)?$"
)


def _parse_hour(raw: Any) -> datetime:
    """A naive wall-clock stamp in the requested timezone (UTC) -> aware UTC datetime."""
    if not isinstance(raw, str) or (match := _HOUR_RE.match(raw)) is None:
        raise ValueError(f"hourly.time entry is not an ISO 8601 date-time: {raw!r}")
    if match.group("offset"):
        # An explicit offset would be relabelled, not converted - reject instead.
        raise ValueError(f"hourly.time must be naive UTC timestamps, got an offset: {raw!r}")
    return datetime.fromisoformat(raw).replace(tzinfo=UTC)


def _value(raw: Any, variable: str, time: str) -> float | None:
    if raw is None:
        return None  # model gave no value (e.g. outside the pollen season) - NOT zero
    if isinstance(raw, bool) or not isinstance(raw, int | float):
        raise OpenMeteoPollenParseError(f"{variable} at {time}: not a number: {raw!r}")
    try:
        value = float(raw)  # OverflowError for ints beyond float range (e.g. 10**309)
    except OverflowError as exc:
        raise OpenMeteoPollenParseError(f"{variable} at {time}: value out of range") from exc
    if not math.isfinite(value) or value < 0:
        raise OpenMeteoPollenParseError(f"{variable} at {time}: impossible value {raw!r}")
    return value


def normalize(
    *,
    geo_area_id: int,
    payload: dict[str, Any],
    fetched_at: datetime,
) -> list[dict[str, Any]]:
    """One PollenSnapshot-ready dict per hourly slot, all five species in it.
    Raises OpenMeteoPollenParseError on a malformed payload."""
    try:
        # Required, not defaulted: the naive timestamps below are only UTC if the
        # source says so (a missing field is a schema change, not "UTC").
        if payload["utc_offset_seconds"] != 0:
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
        raw_units = [units[variable] for variable in SPECIES_BY_VARIABLE]
        if not all(isinstance(u, str) and u.strip() for u in raw_units):
            raise ValueError(f"species units must be non-empty strings, got {raw_units!r}")
        unit_values = set(raw_units)
        if len(unit_values) != 1:
            raise ValueError(f"species units differ: {sorted(unit_values)}")
        unit = unit_values.pop()
        valid_times = [_parse_hour(t) for t in times]
        if len(set(valid_times)) != len(valid_times):
            # Would collide on source_record_id and be silently swallowed as a "race".
            raise ValueError("hourly.time contains duplicate timestamps")
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
