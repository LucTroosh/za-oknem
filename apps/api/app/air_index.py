"""European Air Quality Index (EAQI, EEA) computed from our own GIOŚ measurements
(TASK-4.2, ADR-015).

Pure and deterministic: no DB, no I/O, no clock, no LLM (rule #10). The index is DERIVED
(rule #7: not a Measurement) and never a safety source.

Methodology (EEA, hourly index, 6 bands per pollutant; overall = the WORST sub-index):
  * https://airindex.eea.europa.eu/AQI/index.html (verified 2026-09-30)
  * ETC HE Report 2024/17 "EEA's revision of the European air quality index bands",
    v1, 3 Jul 2025, DOI 10.5281/zenodo.15781195 (verified 2026-09-30):
    https://www.eionet.europa.eu/etcs/etc-he/products/etc-he-products/etc-he-reports/etc-he-report-2024-17-eeas-revision-of-the-european-air-quality-index-bands/@@download/file/ETC%20HE%20Report%202024-17_Gonzalez%20Ortiz.pdf
  Both sources give identical bands, in ug/m3, 1-hour reference time, all five pollutants.

Two implementation choices that the EEA sources do NOT spell out (documented in ADR-015):
  * BOUNDARY: EEA lists integer bands ("Good 0-5, Fair 6-15"). Our values are decimals, so a
    band is "value <= upper edge"; anything above the edge is the next band (5.0 Good,
    5.01 Fair). Right-closed like GIOŚ's own convention; never rounds a value into a
    better band.
  * MINIMUM SET: EEA requires PM + NO2 (traffic) or PM + NO2 + O3 (background/industrial).
    We do not know the station type, so we require the stricter one. Without it a
    Good/Fair result is "no index" (an absent pollutant could be worse); a Moderate or
    worse result stands as a lower bound, flagged `complete=False`.
CO and C6H6 (benzene) are not part of the EAQI: they are shown as plain values only.
"""

import math
from collections.abc import Mapping
from datetime import datetime, timedelta
from enum import IntEnum
from typing import Any

# Freshness values (rule #8) that may feed the index; same set as outdoor.py.
USABLE_FRESHNESS = frozenset({"FRESH", "RECENT"})
# The only unit the EEA bands are defined in; GIOŚ stores exactly this (parser.py).
UNIT = "µg/m³"


class Level(IntEnum):
    GOOD = 0
    FAIR = 1
    MODERATE = 2
    POOR = 3
    VERY_POOR = 4
    EXTREMELY_POOR = 5


# Upper edges (inclusive) of Good, Fair, Moderate, Poor, Very poor; above the last edge =
# Extremely poor. Keys = GIOŚ param codes (Measurement.param_code).
BANDS: dict[str, tuple[float, float, float, float, float]] = {
    "PM2.5": (5, 15, 50, 90, 140),
    "PM10": (15, 45, 120, 195, 270),
    "NO2": (10, 25, 60, 100, 150),
    "O3": (60, 100, 120, 160, 180),
    "SO2": (20, 40, 125, 190, 275),
}
# EAQI needs a PM value (either) plus these.
_PM = ("PM2.5", "PM10")
_REQUIRED_OTHER = ("NO2", "O3")


def level_for(param: str, value: float) -> Level:
    """Sub-index of one value. Raises KeyError for a param the EAQI does not index."""
    for level, edge in zip(Level, BANDS[param], strict=False):
        if value <= edge:
            return level
    return Level.EXTREMELY_POOR


def _usable(p: Mapping[str, Any] | None) -> tuple[float | None, str]:
    """(value, status); value is None unless status == 'OK'. A unit other than ug/m3 is
    dropped, never converted (status UNIT)."""
    if p is None:
        return None, "MISSING"
    if p.get("freshness") not in USABLE_FRESHNESS:
        return None, "STALE"
    if p.get("unit") != UNIT:
        return None, "UNIT"
    v = p.get("value")
    # Concentrations are >= 0; NaN/inf/bool/negative is an instrument or parse fault.
    if isinstance(v, bool) or not isinstance(v, int | float) or not math.isfinite(v) or v < 0:
        return None, "INVALID"
    return float(v), "OK"


def air_index(params: Mapping[str, Mapping[str, Any]], recent_max_age: timedelta) -> dict:
    """EAQI block from the `params` dicts the endpoints already build (value, unit,
    observed_at, freshness per GIOŚ param code).

    Returns `level` (Level name, or None = "no index"), `complete` (EEA minimum set met),
    `params` (sub-index per usable indexed param), `dominant` (params at the overall level),
    `missing` (every indexed param without a usable input -> MISSING|STALE|UNIT|INVALID;
    informational, `complete` says whether it matters) and `valid_until` (ISO time at
    which the earliest contributing input turns STALE; None without any). Extra params
    (CO, C6H6) are ignored here."""
    sub: dict[str, Level] = {}
    missing: dict[str, str] = {}
    expires: list[datetime] = []
    for code in BANDS:
        value, status = _usable(params.get(code))
        if value is None:
            missing[code] = status
            continue
        sub[code] = level_for(code, value)
        expires.append(datetime.fromisoformat(params[code]["observed_at"]) + recent_max_age)

    worst = max(sub.values()) if sub else None
    complete = any(c in sub for c in _PM) and all(c in sub for c in _REQUIRED_OTHER)
    # Incomplete + Good/Fair: a missing pollutant could be worse -> no index, never GOOD.
    level = worst if worst is not None and (complete or worst >= Level.MODERATE) else None
    return {
        "level": level.name if level is not None else None,
        "complete": complete,
        "params": {c: lv.name for c, lv in sub.items()},
        "dominant": [c for c, lv in sub.items() if level is not None and lv == level],
        "missing": missing,
        "valid_until": min(expires).isoformat() if expires and level is not None else None,
    }
