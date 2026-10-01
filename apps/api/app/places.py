"""Places registry logic (ADR-029): name normalisation, prefix search, activation of a place
as a polled area, idle expiry. Pure helpers + small DB functions; no external calls (rule #14).
"""

import re
import unicodedata
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.connectors.open_meteo.ingest import ESTIMATED_BILLABLE_UNITS_PER_CALL
from app.connectors.open_meteo_pollen.ingest import UNITS_PER_CALL as POLLEN_UNITS_PER_CALL
from app.models import GeoArea, Place, SourceFetchCounter
from app.rate_budget import ALERT_THRESHOLD_PCT

SEARCH_MIN_CHARS = 2
SEARCH_MAX_LIMIT = 20

# Letters that NFKD does not decompose; casefold already turns ß into "ss".
_FOLD = str.maketrans({"ł": "l", "đ": "d", "ø": "o", "æ": "ae", "œ": "oe"})
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalize_name(name: str) -> str:
    """Lowercase, diacritics folded, everything but [a-z0-9] collapsed to single spaces:
    "Łódź" -> "lodz", "Bielsko-Biała" -> "bielsko biala". The same function normalises the
    stored name (import) and the query (search), so prefix matching is deterministic."""
    folded = unicodedata.normalize("NFKD", name.casefold().translate(_FOLD))
    stripped = "".join(c for c in folded if not unicodedata.combining(c))
    return _NON_ALNUM.sub(" ", stripped).strip()


# GeoNames' English voivodeship names (admin1CodesASCII.txt, verified on the real file) ->
# the official Polish adjective used in "woj. śląskie". Unknown name = shown as GeoNames has it.
VOIVODESHIP_PL = {
    "Lower Silesia": "dolnośląskie",
    "Kujawsko-Pomorskie": "kujawsko-pomorskie",
    "Lublin": "lubelskie",
    "Lubusz": "lubuskie",
    "Łódź Voivodeship": "łódzkie",
    "Lesser Poland": "małopolskie",
    "Mazovia": "mazowieckie",
    "Opole Voivodeship": "opolskie",
    "Subcarpathia": "podkarpackie",
    "Podlasie": "podlaskie",
    "Pomerania": "pomorskie",
    "Silesia": "śląskie",
    "Świętokrzyskie": "świętokrzyskie",
    "Warmia-Masuria": "warmińsko-mazurskie",
    "Greater Poland": "wielkopolskie",
    "West Pomerania": "zachodniopomorskie",
}


def place_label(place: Place) -> str:
    """Readable disambiguation: "Nowa Wieś, pow. gliwicki, woj. śląskie". A powiat named like
    the place (city with powiat rights) is not repeated; missing names are left out."""
    parts = [place.name]
    a2 = place.admin2_name
    if a2 and a2 != place.name:
        parts.append("pow. " + a2.removeprefix("Powiat "))
    if place.admin1_name:
        parts.append("woj. " + VOIVODESHIP_PL.get(place.admin1_name, place.admin1_name))
    return ", ".join(parts)


def search_places(db: Session, q: str, limit: int) -> list[Place]:
    """Prefix search on the normalised name. Order: exact match first, then population
    (desc, unknown = 0), then name and id so ties are deterministic. A query that
    normalises to < SEARCH_MIN_CHARS characters matches nothing."""
    nq = normalize_name(q)
    if len(nq) < SEARCH_MIN_CHARS:
        return []
    stmt = (
        select(Place)
        .where(Place.normalized_name.like(nq + "%"))  # nq is [a-z0-9 ] only: no wildcards
        .order_by(
            (Place.normalized_name == nq).desc(),
            func.coalesce(Place.population, 0).desc(),
            Place.name,
            Place.id,
        )
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


# --- activation of a place as a polled area (ADR-029) ---------------------------------

Polling = Literal["active", "capacity_reached", "budget_exhausted"]

# ADR-004/ADR-020: one weather fetch per 3 h (8/day), one pollen fetch per day. A test pins
# the 8 to the scheduler interval.
WEATHER_CALLS_PER_AREA_PER_DAY = 8
POLLEN_CALLS_PER_AREA_PER_DAY = 1
# New activations are refused once today's Open-Meteo units reach this share of the daily
# limit (above the 70% alert of ADR-003, below exhaustion).
BUDGET_REFUSE_PCT = 0.9


def max_active_areas(daily_limit: int | None = None) -> int:
    """How many areas may be polled at once so the steady-state load stays within the
    ADR-003 70% alert: floor(0.7 * limit / units spent per area per day)."""
    limit = settings.open_meteo_daily_call_limit if daily_limit is None else daily_limit
    per_area_per_day = (
        WEATHER_CALLS_PER_AREA_PER_DAY * ESTIMATED_BILLABLE_UNITS_PER_CALL
        + POLLEN_CALLS_PER_AREA_PER_DAY * POLLEN_UNITS_PER_CALL
    )
    return int(ALERT_THRESHOLD_PCT * limit // per_area_per_day)


def _budget_exhausted(db: Session, today: date) -> bool:
    used = db.execute(
        select(SourceFetchCounter.count).where(
            SourceFetchCounter.source_id == "open_meteo", SourceFetchCounter.day == today
        )
    ).scalar_one_or_none()
    return used is not None and used >= BUDGET_REFUSE_PCT * settings.open_meteo_daily_call_limit


def area_for_place(db: Session, place_id: int) -> GeoArea | None:
    return db.execute(select(GeoArea).where(GeoArea.place_id == place_id)).scalar_one_or_none()


def activate_place(
    db: Session, place: Place, *, now: datetime | None = None
) -> tuple[GeoArea, Polling]:
    """Create (once) the geo_area of a place, refresh its `last_requested_at`, and switch
    polling on when capacity and today's budget allow. At capacity / over budget the area
    still exists, inactive: the dashboard shows weather/pollen UNAVAILABLE for it, never an
    error (rule #1). Returns the area and why polling is (not) active.
    ponytail: the capacity check is not atomic - concurrent activations can overshoot the
    cap by a few areas; tighten with a row lock if that ever matters."""
    now = now or datetime.now(UTC)
    area = area_for_place(db, place.id)
    if area is None:
        area = GeoArea(
            slug=f"place-{place.id}",
            name=place.name,
            latitude=place.latitude,
            longitude=place.longitude,
            weather_polling_active=False,
            place_id=place.id,
        )
        db.add(area)
        try:
            db.flush()
        except IntegrityError:  # a concurrent request created it first
            db.rollback()
            area = area_for_place(db, place.id)
            if area is None:
                raise
    area.last_requested_at = now
    # A later GeoNames import may have corrected the place: keep the copied fields in step,
    # or polling / station assignment would keep using the stale coordinates.
    area.name, area.latitude, area.longitude = place.name, place.latitude, place.longitude
    if area.weather_polling_active:
        polling: Polling = "active"
    elif _budget_exhausted(db, now.date()):
        polling = "budget_exhausted"
    else:
        active = db.execute(
            select(func.count())
            .select_from(GeoArea)
            .where(GeoArea.weather_polling_active.is_(True))
        ).scalar_one()
        if active >= max_active_areas():
            polling = "capacity_reached"
        else:
            area.weather_polling_active = True
            polling = "active"
    db.commit()
    return area, polling


def expire_idle_areas(
    db: Session, *, now: datetime | None = None, ttl_days: int | None = None
) -> int:
    """Stop polling place-based areas not re-activated for `ttl_days` (default
    PLACE_ACTIVATION_TTL_DAYS). Seeded cities and gminas (place_id NULL) never expire here.
    Rows and their history stay: the dashboard shows them as STALE, not gone (ADR-026)."""
    now = now or datetime.now(UTC)
    cutoff = now - timedelta(days=ttl_days or settings.place_activation_ttl_days)
    result = db.execute(
        update(GeoArea)
        .where(
            GeoArea.place_id.is_not(None),
            GeoArea.weather_polling_active.is_(True),
            or_(GeoArea.last_requested_at.is_(None), GeoArea.last_requested_at < cutoff),
        )
        .values(weather_polling_active=False)
        .returning(GeoArea.id)
    )
    expired = len(result.all())
    db.commit()
    return expired
