"""Parser/normalizer for GIOŚ noise measurements (`halas` `pomiar-halasu-w-srodowisku`, ADR-032).

Field names, types and the coordinate order come from the recorded live sample (2026-10-03,
docs/data/gios/evidence/halas-second.json): `coordWgs84X` is the LONGITUDE and `coordWgs84Y` the
LATITUDE; `dataOd`/`dataDo` carry a full datetime with an offset although the spec says "date"
(we keep the calendar day the source states); `wynikPomiaru` is a number in dB; `przekroczenie` is a
number or null. Nothing is guessed: a record that does not fit is rejected with a reason (the
connector quarantines it) instead of being repaired.
"""

import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import date
from typing import Any

SOURCE_ID = "gios_noise"
PARSER_VERSION = "1"

CATEGORIES = ("Droga", "Lotnisko", "Przemysł", "Kolej")
VOIVODESHIPS = (
    "DOLNOŚLĄSKIE",
    "KUJAWSKO-POMORSKIE",
    "LUBELSKIE",
    "LUBUSKIE",
    "ŁÓDZKIE",
    "MAŁOPOLSKIE",
    "MAZOWIECKIE",
    "OPOLSKIE",
    "PODKARPACKIE",
    "PODLASKIE",
    "POMORSKIE",
    "ŚLĄSKIE",
    "ŚWIĘTOKRZYSKIE",
    "WARMIŃSKO-MAZURSKIE",
    "WIELKOPOLSKIE",
    "ZACHODNIOPOMORSKIE",
)

# Poland with a small margin (lat 49.0-54.84, lon 14.12-24.15): a coordinate outside this is a data
# error (projected / swapped / wrong country), never "close enough".
LAT_RANGE = (48.8, 55.1)
LON_RANGE = (13.9, 24.4)

_DAY = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")


class RecordRejected(Exception):
    """The record cannot be accepted as it is; `reason` is a short stable quarantine code."""

    def __init__(self, reason: str, detail: str | None = None):
        self.reason = reason
        self.detail = detail
        super().__init__(f"{reason}: {detail}" if detail else reason)


@dataclass(frozen=True)
class NoiseRecord:
    natural_key: str
    point_code: str
    category: str
    voivodeship: str
    powiat: str | None
    gmina: str | None
    locality: str | None
    latitude: float
    longitude: float
    period_label: str
    purpose: str | None
    date_from: date
    date_to: date
    value_db: float
    exceedance_db: float | None


def _number(x: Any) -> float | None:
    if isinstance(x, bool) or not isinstance(x, int | float):
        return None
    value = float(x)
    return value if math.isfinite(value) else None


def _text(x: Any, limit: int) -> str | None:
    return x.strip()[:limit] or None if isinstance(x, str) else None


def _day(x: Any, field: str) -> date:
    match = _DAY.match(x) if isinstance(x, str) else None
    if not match:
        raise RecordRejected("bad_date", f"{field}={x!r}")
    try:
        return date(int(match[1]), int(match[2]), int(match[3]))
    except ValueError as exc:
        raise RecordRejected("bad_date", f"{field}={x!r}") from exc


def natural_key(raw: dict) -> str:
    """Identity of a measurement: point, category, time of day, period, purpose and value. A
    point has several measurements (day/night, years), so the point code alone is not it."""
    parts = [
        raw.get("kodPunktuPomiarowego"),
        raw.get("kategoria"),
        raw.get("pora"),
        raw.get("dataOd"),
        raw.get("dataDo"),
        raw.get("celPomiaru"),
        raw.get("wynikPomiaru"),
    ]
    blob = json.dumps(parts, ensure_ascii=False, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode()).hexdigest()


def normalize(raw: dict) -> NoiseRecord:
    """Raises RecordRejected for anything that does not fit the verified shape."""
    code = _text(raw.get("kodPunktuPomiarowego"), 32)
    if code is None:
        raise RecordRejected("missing_point_code")
    category = raw.get("kategoria")
    if category not in CATEGORIES:
        raise RecordRejected("unknown_category", repr(category))
    voivodeship = raw.get("wojewodztwo")
    if voivodeship not in VOIVODESHIPS:
        raise RecordRejected("unknown_voivodeship", repr(voivodeship))
    lon, lat = _number(raw.get("coordWgs84X")), _number(raw.get("coordWgs84Y"))
    if lon is None or lat is None:
        raise RecordRejected(
            "bad_coordinates", f"X={raw.get('coordWgs84X')!r} Y={raw.get('coordWgs84Y')!r}"
        )
    if LAT_RANGE[0] <= lon <= LAT_RANGE[1] and LON_RANGE[0] <= lat <= LON_RANGE[1]:
        raise RecordRejected("coords_swapped", f"X={lon} Y={lat}")  # not repaired: reported
    if not (LAT_RANGE[0] <= lat <= LAT_RANGE[1] and LON_RANGE[0] <= lon <= LON_RANGE[1]):
        raise RecordRejected("coords_outside_poland", f"X={lon} Y={lat}")
    value = _number(raw.get("wynikPomiaru"))
    if value is None:
        raise RecordRejected("value_not_number", repr(raw.get("wynikPomiaru")))
    exceed_raw = raw.get("przekroczenie")
    exceedance = _number(exceed_raw)
    if exceed_raw is not None and exceedance is None:
        raise RecordRejected("exceedance_not_number", repr(exceed_raw))
    label = _text(raw.get("pora"), 255)
    if label is None:
        raise RecordRejected("missing_period_of_day")
    date_from, date_to = _day(raw.get("dataOd"), "dataOd"), _day(raw.get("dataDo"), "dataDo")
    if date_from > date_to:
        raise RecordRejected("date_order", f"{date_from} > {date_to}")
    return NoiseRecord(
        natural_key=natural_key(raw),
        point_code=code,
        category=category,
        voivodeship=voivodeship,
        powiat=_text(raw.get("powiat"), 60),
        gmina=_text(raw.get("gmina"), 100),
        locality=_text(raw.get("miejscowosc"), 120),
        latitude=lat,
        longitude=lon,
        period_label=label,
        purpose=_text(raw.get("celPomiaru"), 500),
        date_from=date_from,
        date_to=date_to,
        value_db=value,
        exceedance_db=exceedance,
    )
