"""Outdoor Interpretation Engine (TASK-7.6, ADR-016, Master Plan §52).

Pure, deterministic function: readings in -> GOOD / MODERATE / POOR / UNKNOWN +
machine-readable reasons out. No DB, no I/O, no clock, no LLM (rule #10, §52/§53).
Wiring into /dashboard is TASK-7.7; the UI card is TASK-7.8.

Rule of the game (ADR-016):
  * worst factor wins (max over all evaluated rules);
  * a missing/STALE/UNAVAILABLE/non-finite input is never silently GOOD: if the
    rules that *could* be evaluated all say GOOD but a core factor group is
    unusable, the verdict is UNKNOWN. A MODERATE/POOR verdict from the available
    factors stands regardless of what is missing (bad news is not cancelled by
    absent data). Everything unusable is reported in `missing`.

Expected units (Open-Meteo defaults, GIOŚ): degC, mm, km/h, UV index, m, ug/m3, WMO code.

THRESHOLDS: every number lives in RULES below and is labelled either with a
verified source (+ verification date) or as a PRODUCT DECISION "do kalibracji" —
a product choice, not a scientific fact.
"""

import math
import operator
from collections.abc import Callable
from dataclasses import dataclass
from enum import IntEnum, StrEnum

from app.air_index import BANDS

# Freshness values (rule #8) that may feed a verdict. STALE / UNAVAILABLE /
# anything else is treated as missing.
USABLE_FRESHNESS = frozenset({"FRESH", "RECENT"})


class Rating(StrEnum):
    GOOD = "GOOD"
    MODERATE = "MODERATE"
    POOR = "POOR"
    UNKNOWN = "UNKNOWN"


class Level(IntEnum):
    GOOD = 0
    MODERATE = 1
    POOR = 2


# Severity order used for the "worsening an input never improves the result"
# property: UNKNOWN (cannot confirm GOOD) is worse than GOOD, better than a
# confirmed MODERATE.
SEVERITY = {Rating.GOOD: 0, Rating.UNKNOWN: 1, Rating.MODERATE: 2, Rating.POOR: 3}

_CMP: dict[str, Callable[[float, float], bool]] = {
    "gt": operator.gt,
    "gte": operator.ge,
    "lt": operator.lt,
    "lte": operator.le,
}


@dataclass(frozen=True)
class Reading:
    value: float
    freshness: str = "FRESH"


@dataclass(frozen=True)
class OutdoorInputs:
    """Field names = Open-Meteo param codes (+ pm25/pm10 for GIOŚ PM2.5/PM10)."""

    temperature_2m: Reading | None = None
    apparent_temperature: Reading | None = None
    precipitation: Reading | None = None
    wind_speed_10m: Reading | None = None
    wind_gusts_10m: Reading | None = None
    uv_index: Reading | None = None
    visibility: Reading | None = None
    pm25: Reading | None = None
    pm10: Reading | None = None
    no2: Reading | None = None
    o3: Reading | None = None
    weather_code: Reading | None = None  # WMO code (Open-Meteo `current`), unit "wmo code"


@dataclass(frozen=True)
class Rule:
    code: str  # machine code shown to UI/tests
    group: str  # factor group; a core group with no usable input blocks GOOD
    param: str  # OutdoorInputs field
    comparison: str  # gt | gte | lt | lte — "value <comparison> threshold" = worse
    moderate: float | None  # None = the rule has no MODERATE band (POOR only, e.g. STORM)
    poor: float
    unit: str
    core: bool
    basis: str  # where the numbers come from (see ADR-016)


# ponytail: hand-written rule table, not a rules DSL — add TASK-12.4 sensitivity
# by passing a modified `rules` tuple to evaluate(); not implemented here.

# --- Verified cut-points: European AQI hourly bands, EEA
# https://airindex.eea.europa.eu/AQI/index.html (verified 2026-09-30):
#   PM2.5: Good 0-5, Fair 6-15, Moderate 16-50, Poor 51-90, ...
#   PM10:  Good 0-15, Fair 16-45, Moderate 46-120, Poor 121-195, ...
# The cut-points are EEA's; mapping "Good+Fair -> GOOD, Moderate -> MODERATE,
# Poor and worse -> POOR" for outdoor exercise is a PRODUCT DECISION. (PM2.5 15 /
# PM10 45 equal the WHO 2021 24h AQG, confirmed only secondarily via
# https://www.iqair.com/newsroom/2021-who-air-quality-guidelines on 2026-09-30.)
_EEA = (
    "EEA European AQI (hourly), verified 2026-09-30; GOOD/MODERATE/POOR mapping = product decision"
)
# --- Verified category edges: Global Solar UV Index (WHO/WMO/UNEP/ICNIRP)
# https://www.icnirp.org/en/applications/uv-index/index.html (verified 2026-09-30):
# Low 0-2, Moderate 3-5, High 6-7, Very high 8-10, Extreme 11+. Mapping
# High -> MODERATE, Very high+ -> POOR is a PRODUCT DECISION; values are not
# rounded to integers like the official index (simplification).
_UV = "WHO UV index edges (High=6, Very high=8), verified 2026-09-30; mapping = product decision"
# --- Verified class edges: Beaufort scale (km/h) — force 5 "fresh breeze" 29-38,
# force 6 "strong breeze" 39-49, force 7 50-61, force 8 62-74
# https://en.wikipedia.org/wiki/Beaufort_scale (verified 2026-09-30).
# Mapping to outdoor comfort is a PRODUCT DECISION; Beaufort describes sustained
# wind, so using force 7/8 edges for GUSTS is an orientation only.
_BFT = "Beaufort class edges, verified 2026-09-30; mapping to outdoor comfort = product decision"
# --- Verified code meaning: Open-Meteo docs, WMO weather interpretation codes
# https://open-meteo.com/en/docs (verified 2026-10-02): 95 Thunderstorm, 96 Thunderstorm
# with slight hail, 99 Thunderstorm with heavy hail.
# Any thunderstorm code (>= 95) -> POOR is a PRODUCT DECISION (no MODERATE band).
_WMO = "Open-Meteo WMO codes 95/96/99 = thunderstorm, verified 2026-10-02; POOR = product decision"
# --- Everything else: PRODUCT DECISION, do kalibracji (no source verified).
_PD = "PRODUCT DECISION - do kalibracji, no verified source"

_THERMAL = [
    Rule(f"{code}", "thermal", param, cmp, mod, poor, "°C", True, _PD)
    for param in ("apparent_temperature", "temperature_2m")
    for code, cmp, mod, poor in (("HEAT", "gte", 27.0, 32.0), ("COLD", "lte", 0.0, -10.0))
]

RULES: tuple[Rule, ...] = (
    # Cut-points come from air_index.BANDS (one table, ADR-015): MODERATE above the upper
    # edge of Fair, POOR above the upper edge of Moderate (= EAQI Poor starts).
    Rule(
        "PM25_HIGH", "air", "pm25", "gt", BANDS["PM2.5"][1], BANDS["PM2.5"][2], "µg/m³", True, _EEA
    ),
    Rule("PM10_HIGH", "air", "pm10", "gt", BANDS["PM10"][1], BANDS["PM10"][2], "µg/m³", True, _EEA),
    # NO2 / O3 are OPTIONAL groups (ADR-016 addendum): many GIOŚ stations have no such
    # sensor, and a missing optional sensor must not turn every verdict into UNKNOWN.
    Rule("NO2_HIGH", "no2", "no2", "gt", BANDS["NO2"][1], BANDS["NO2"][2], "µg/m³", False, _EEA),
    Rule("O3_HIGH", "o3", "o3", "gt", BANDS["O3"][1], BANDS["O3"][2], "µg/m³", False, _EEA),
    Rule("PRECIPITATION", "precipitation", "precipitation", "gte", 0.1, 2.5, "mm", True, _PD),
    Rule("WIND_STRONG", "wind", "wind_speed_10m", "gte", 29.0, 39.0, "km/h", True, _BFT),
    Rule("GUSTS_STRONG", "gusts", "wind_gusts_10m", "gte", 50.0, 62.0, "km/h", False, _BFT),
    Rule("UV_HIGH", "uv", "uv_index", "gte", 6.0, 8.0, "", False, _UV),
    Rule("LOW_VISIBILITY", "visibility", "visibility", "lt", 5000.0, 1000.0, "m", False, _PD),
    Rule("STORM", "storm", "weather_code", "gte", None, 95.0, "wmo code", False, _WMO),
    *_THERMAL,
)


@dataclass(frozen=True)
class Reason:
    code: str
    param: str
    value: float
    threshold: float
    comparison: str
    unit: str
    level: Rating  # MODERATE or POOR


@dataclass(frozen=True)
class Missing:
    group: str
    params: tuple[str, ...]
    status: str  # MISSING (None) | STALE (not FRESH/RECENT) | INVALID (NaN/inf)
    core: bool
    # True = no usable input left in the group (a core group then blocks GOOD);
    # False = an alternative is still usable (e.g. pm25 ok, pm10 absent): reported only.
    blocking: bool = True


@dataclass(frozen=True)
class OutdoorResult:
    rating: Rating
    reasons: tuple[Reason, ...]
    missing: tuple[Missing, ...]


def _usable(reading: Reading | None) -> tuple[float | None, str]:
    """(value, status) — value is None unless status == 'OK'."""
    if reading is None:
        return None, "MISSING"
    if reading.freshness not in USABLE_FRESHNESS:
        return None, "STALE"
    if isinstance(reading.value, bool) or not math.isfinite(reading.value):
        return None, "INVALID"
    return float(reading.value), "OK"


def evaluate(inputs: OutdoorInputs, rules: tuple[Rule, ...] = RULES) -> OutdoorResult:
    hits: list[tuple[int, Reason]] = []  # (rule index, reason) for stable ordering
    worst = Level.GOOD
    group_ok: dict[str, bool] = {}
    group_info: dict[str, tuple[set[str], set[str], bool]] = {}  # params, statuses, core

    for idx, rule in enumerate(rules):
        value, status = _usable(getattr(inputs, rule.param))
        params, statuses, _ = group_info.setdefault(rule.group, (set(), set(), rule.core))
        group_ok.setdefault(rule.group, False)
        if value is None:
            params.add(rule.param)
            statuses.add(status)
            continue
        group_ok[rule.group] = True
        cmp = _CMP[rule.comparison]
        if cmp(value, rule.poor):
            level, threshold = Level.POOR, rule.poor
        elif rule.moderate is not None and cmp(value, rule.moderate):
            level, threshold = Level.MODERATE, rule.moderate
        else:
            continue
        worst = max(worst, level)
        hits.append(
            (
                idx,
                Reason(
                    rule.code,
                    rule.param,
                    value,
                    threshold,
                    rule.comparison,
                    rule.unit,
                    Rating(level.name),
                ),
            )
        )

    # POOR first, then rule-table order: deterministic regardless of input order.
    reasons = tuple(r for _, r in sorted(hits, key=lambda h: (-SEVERITY[h[1].level], h[0])))
    missing = tuple(
        Missing(
            group,
            tuple(sorted(params)),
            "STALE" if "STALE" in statuses else "INVALID" if "INVALID" in statuses else "MISSING",
            core,
            not group_ok[group],
        )
        for group, (params, statuses, core) in group_info.items()
        if params
    )

    if worst is Level.GOOD:
        rating = Rating.UNKNOWN if any(m.core and m.blocking for m in missing) else Rating.GOOD
    else:
        rating = Rating(worst.name)
    return OutdoorResult(rating, reasons, missing)
