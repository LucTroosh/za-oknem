"""\"Twoja okolica\" section builders (ADR-032). Read only from our DB (rule #14).

Historical noise measurements are NOT live data and NOT alerts (rule #7): no freshness, no
thresholds, no advice. A section says where the data comes from, which period it covers and what
it applies to; "no data" and "failure" are different `availability` values.
"""

import json
import math
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.gios_noise.ingest import OPERATION
from app.connectors.gios_noise.parser import CATEGORIES, SOURCE_ID, VOIVODESHIPS
from app.gios_open.snapshots import ACTIVE
from app.models import DatasetSnapshot, NoiseMeasurement, SourceStatus

LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
SOURCE_URL = "https://dane.gios.gov.pl"
EARTH_RADIUS_KM = 6371.0088
KM_PER_DEGREE = 111.2

NOISE_LIMITATIONS = [
    "Dane historyczne z pomiarów w wybranych punktach — nie opisują hałasu teraz.",
    "Punkt pomiarowy może być w pewnej odległości od wybranej lokalizacji.",
]


@dataclass(frozen=True)
class Coverage:
    # Every category x voivodeship has an active import spanning the configured date range.
    complete: bool
    snapshot_ids: list[int]
    period: tuple[date, date] | None  # widest range the active imports were requested for


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (
        math.sin((p2 - p1) / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def noise_coverage(db: Session, cover_from: date, cover_to: date) -> Coverage:
    snaps = db.execute(
        select(DatasetSnapshot).where(
            DatasetSnapshot.source_id == SOURCE_ID,
            DatasetSnapshot.operation == OPERATION,
            DatasetSnapshot.status == ACTIVE,
        )
    ).scalars()
    ids: list[int] = []
    covered: set[tuple[str, str]] = set()
    lows: list[date] = []
    highs: list[date] = []
    for s in snaps:
        ids.append(s.id)
        try:
            f = json.loads(s.filters_key)
            start, end = date.fromisoformat(f["dataOd"]), date.fromisoformat(f["dataDo"])
            key = (f["kategoria"], f["wojewodztwo"])
        except (ValueError, KeyError, TypeError):
            continue
        lows.append(start)
        highs.append(end)
        if start <= cover_from and end >= cover_to:  # a narrower import proves nothing
            covered.add(key)
    complete = all((c, v) in covered for c in CATEGORIES for v in VOIVODESHIPS)
    period = (min(lows), max(highs)) if lows else None
    return Coverage(complete=complete, snapshot_ids=ids, period=period)


def attribution(period: tuple[date, date] | None, fetched_at: datetime | None) -> str:
    text = (
        "Źródło danych: GIOŚ · CC BY 4.0. Dane zostały uporządkowane i przetworzone przez Za Oknem."
    )
    if period:
        text += f" Okres danych: {period[0].isoformat()} – {period[1].isoformat()}."
    if fetched_at:
        text += f" Pobrano: {fetched_at.date().isoformat()}."
    return text


def retrieval(db: Session) -> tuple[str, datetime | None]:
    """ok = last import succeeded; degraded = it served data but the latest attempt failed;
    none = never imported. NOT freshness: old measurements stay old however recently fetched."""
    row = db.get(SourceStatus, SOURCE_ID)
    if row is None or row.last_success_at is None:
        return "none", None
    ok_at = row.last_success_at
    if ok_at.tzinfo is None:
        ok_at = ok_at.replace(tzinfo=UTC)
    attempt = row.last_attempt_at
    if attempt.tzinfo is None:
        attempt = attempt.replace(tzinfo=UTC)
    return ("ok" if attempt <= ok_at else "degraded"), ok_at


def nearest_noise(
    db: Session, snapshot_ids: list[int], lat: float, lon: float, max_km: float
) -> list[dict]:
    """Nearest point per category within max_km (deterministic: distance, then point code), with
    the measurements of that point's newest period."""
    if not snapshot_ids:
        return []
    dlat = max_km / KM_PER_DEGREE
    dlon = max_km / (KM_PER_DEGREE * max(math.cos(math.radians(lat)), 0.01))
    rows = (
        db.execute(
            select(NoiseMeasurement).where(
                NoiseMeasurement.snapshot_id.in_(snapshot_ids),
                NoiseMeasurement.latitude.between(lat - dlat, lat + dlat),
                NoiseMeasurement.longitude.between(lon - dlon, lon + dlon),
            )
        )
        .scalars()
        .all()
    )
    # The same measurement can sit in two overlapping imports: count it once.
    rows = list({r.natural_key: r for r in rows}.values())
    best: dict[str, tuple[float, str]] = {}
    for r in rows:
        d = haversine_km(lat, lon, r.latitude, r.longitude)
        if d <= max_km and (r.category not in best or (d, r.point_code) < best[r.category]):
            best[r.category] = (d, r.point_code)
    items: list[dict] = []
    for category in CATEGORIES:
        if category not in best:
            continue
        distance, code = best[category]
        mine = [r for r in rows if r.category == category and r.point_code == code]
        newest = max(r.date_to for r in mine)
        latest = sorted((r for r in mine if r.date_to == newest), key=lambda r: r.period_label)
        first = latest[0]
        items.append(
            {
                "category": category,
                "point_code": code,
                "locality": first.locality,
                "gmina": first.gmina,
                "voivodeship": first.voivodeship,
                "distance_km": round(distance, 1),
                "period_from": min(r.date_from for r in latest),
                "period_to": newest,
                "purpose": first.purpose,
                "measurements": [
                    {
                        "period_of_day": r.period_label,
                        "value_db": r.value_db,
                        "exceedance_db": r.exceedance_db,
                    }
                    for r in latest
                ],
            }
        )
    return items


def build_noise_section(
    db: Session, lat: float, lon: float, max_km: float, cover_from: date, cover_to: date
) -> dict:
    status, fetched_at = retrieval(db)
    coverage = noise_coverage(db, cover_from, cover_to)
    items = (
        nearest_noise(db, coverage.snapshot_ids, lat, lon, max_km) if coverage.snapshot_ids else []
    )
    period = (
        (min(i["period_from"] for i in items), max(i["period_to"] for i in items))
        if items
        else None
    )
    if items:
        availability, message = "available", None
    elif not coverage.snapshot_ids:
        availability = "unavailable"
        message = "Dane o hałasie nie zostały jeszcze pobrane."
    elif coverage.complete:
        availability = "no_coverage"
        years = f"{coverage.period[0].year}–{coverage.period[1].year}" if coverage.period else ""
        message = (
            f"Brak punktów pomiaru hałasu w promieniu {max_km:g} km od wybranej lokalizacji"
            f" w danych GIOŚ z lat {years}."
        )
    else:  # a partial / narrower import cannot prove that nothing is nearby
        availability = "unavailable"
        message = "Dane o hałasie zostały pobrane tylko częściowo."
    return {
        "id": "noise",
        "data_kind": "historical_measurement",
        "title": "Hałas",
        "availability": availability,
        "retrieval_status": status,
        "message": message,
        "source_period": (
            {"from": period[0], "to": period[1], "precision": "date"} if period else None
        ),
        "fetched_at": fetched_at,
        "attribution": attribution(period, fetched_at),
        "source_url": SOURCE_URL,
        "license_url": LICENSE_URL,
        "limitations": NOISE_LIMITATIONS,
        "search_radius_km": max_km,
        "items": items,
    }


def failed_noise_section(max_km: float) -> dict:
    """A builder error must not break the whole response (rule #1)."""
    return {
        "id": "noise",
        "data_kind": "historical_measurement",
        "title": "Hałas",
        "availability": "unavailable",
        "retrieval_status": "none",
        "message": "Nie udało się odczytać danych o hałasie.",
        "source_period": None,
        "fetched_at": None,
        "attribution": attribution(None, None),
        "source_url": SOURCE_URL,
        "license_url": LICENSE_URL,
        "limitations": NOISE_LIMITATIONS,
        "search_radius_km": max_km,
        "items": [],
    }
