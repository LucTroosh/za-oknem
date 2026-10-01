import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.v1.geo import AreaOut, _area_out
from app.db import get_db
from app.models import Place
from app.places import (
    SEARCH_MAX_LIMIT,
    SEARCH_MIN_CHARS,
    activate_place,
    area_for_place,
    search_places,
)
from app.rate_limit import limit_place_activations

router = APIRouter()
logger = logging.getLogger(__name__)

# CC BY 4.0 (source-registry `geonames_pl`): credit required wherever places are shown.
PLACES_ATTRIBUTION = "Place names and coordinates: GeoNames (geonames.org, CC BY 4.0)"


class PlaceOut(BaseModel):
    place_id: int
    name: str
    # GeoNames feature code (PPL, PPLA, PPLC, ...); admin codes are GeoNames' own, not TERYT.
    kind: str
    admin1_code: str | None
    admin2_code: str | None
    latitude: float
    longitude: float
    population: int | None


class PlacesResponse(BaseModel):
    places: list[PlaceOut]
    attribution: str


def _place_out(p: Place) -> PlaceOut:
    return PlaceOut(
        place_id=p.id,
        name=p.name,
        kind=p.kind,
        admin1_code=p.admin1_code,
        admin2_code=p.admin2_code,
        latitude=p.latitude,
        longitude=p.longitude,
        population=p.population,
    )


@router.get("/places", response_model=PlacesResponse)
def list_places(
    response: Response,
    q: str = Query(min_length=SEARCH_MIN_CHARS, max_length=100),
    limit: int = Query(10, ge=1, le=SEARCH_MAX_LIMIT),
    db: Session = Depends(get_db),
) -> PlacesResponse:
    """Search the places registry by name prefix, diacritics-insensitive (ADR-029): any
    locality in Poland, not only cities with a station. Exact match first, then by
    population. Reads only our own DB (rule #14); the app itself never logs `q` (only the path)."""
    response.headers["Cache-Control"] = "public, max-age=300"
    try:
        found = search_places(db, q, limit)
    except SQLAlchemyError:
        logger.error("places search failed: database error (details withheld)")
        raise HTTPException(status_code=503, detail="Places unavailable") from None
    return PlacesResponse(places=[_place_out(p) for p in found], attribution=PLACES_ATTRIBUTION)


class PlaceAreaResponse(BaseModel):
    place: PlaceOut
    # None until someone activated the place (GET never creates it).
    area: AreaOut | None
    # active = polled; inactive = known but not polled (expired / never activated);
    # capacity_reached / budget_exhausted = activation refused (ADR-029): the dashboard for
    # the area then shows weather/pollen UNAVAILABLE ("no data collected here").
    polling: Literal["active", "inactive", "capacity_reached", "budget_exhausted"]
    attribution: str


_PLACE_ID = Path(ge=1, le=2_147_483_647)


def _get_place(db: Session, place_id: int) -> Place:
    place = db.get(Place, place_id)
    if place is None:
        raise HTTPException(status_code=404, detail="place not found")
    return place


@router.get("/places/{place_id}", response_model=PlaceAreaResponse)
def get_place(place_id: int = _PLACE_ID, db: Session = Depends(get_db)) -> PlaceAreaResponse:
    """A place and the state of its area. Read-only: never creates or refreshes the area
    (the id is public and enumerable, so a read must not keep polling alive, ADR-026)."""
    place = _get_place(db, place_id)
    area = area_for_place(db, place_id)
    return PlaceAreaResponse(
        place=_place_out(place),
        area=_area_out(area) if area else None,
        polling="active" if area and area.weather_polling_active else "inactive",
        attribution=PLACES_ATTRIBUTION,
    )


@router.post("/places/{place_id}/activate", response_model=PlaceAreaResponse)
def activate(
    request: Request, place_id: int = _PLACE_ID, db: Session = Depends(get_db)
) -> PlaceAreaResponse:
    """Choose a place: create its area on first use and (re)start collecting data for it
    (ADR-029). Idempotent; refreshes the idle-expiry clock - the client calls it when the
    user selects the place and when the app opens with it selected. Data arrives with the
    scheduler (first fetch within minutes, not the 3 h cycle), never on this request
    (rule #14). No user data is sent or stored: the area is a public resource (rule #11).
    Switching polling on is rate-limited per IP; refreshing an already active area is not."""
    place = _get_place(db, place_id)
    existing = area_for_place(db, place_id)
    if existing is None or not existing.weather_polling_active:
        limit_place_activations(request)
    try:
        area, polling = activate_place(db, place)
    except SQLAlchemyError:
        logger.error("place activation failed: database error (details withheld)")
        db.rollback()
        raise HTTPException(status_code=503, detail="Places unavailable") from None
    return PlaceAreaResponse(
        place=_place_out(place),
        area=_area_out(area),
        polling=polling,
        attribution=PLACES_ATTRIBUTION,
    )
