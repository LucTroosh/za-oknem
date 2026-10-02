import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import get_db
from app.geo import METHOD_NEAREST_AREA, METHOD_POINT_IN_POLYGON, nearest_area, resolve_gmina
from app.models import GeoArea

router = APIRouter()
logger = logging.getLogger(__name__)


class GeoResolveRequest(BaseModel):
    # Finite and in range; NaN/inf must never reach the SQL point constructor.
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)


class ResolvedGeoArea(BaseModel):
    geo_area_id: int
    teryt_code: str
    slug: str
    name: str


class GeoResolveResponse(BaseModel):
    # None = the point is in no imported gmina (outside Poland, or boundaries not
    # imported yet). Deliberately not a 404 and never a "nearest gmina" guess.
    area: ResolvedGeoArea | None


@router.post("/geo/resolve", response_model=GeoResolveResponse)
def geo_resolve(body: GeoResolveRequest, db: Session = Depends(get_db)) -> GeoResolveResponse:
    """lat/lon -> gmina by point-in-polygon (TASK-6.2, ADR-019).

    POST body, not query string, so coordinates never appear in access logs (ADR-002).
    Nothing here logs or stores the point; the response carries the gmina only and does
    not echo the coordinates back."""
    try:
        resolved = resolve_gmina(db, body.latitude, body.longitude)
    except SQLAlchemyError:
        # Constant message, no exc_info: the driver error would carry the coordinates (ADR-002).
        logger.error("geo resolve failed: database error (details withheld, ADR-002)")
        raise HTTPException(status_code=503, detail="Geo resolver unavailable") from None
    if resolved is None:
        return GeoResolveResponse(area=None)
    return GeoResolveResponse(
        area=ResolvedGeoArea(
            geo_area_id=resolved.geo_area_id,
            teryt_code=resolved.teryt_code,
            slug=resolved.slug,
            name=resolved.name,
        )
    )


class AreaOut(BaseModel):
    geo_area_id: int
    slug: str
    name: str
    teryt_code: str | None
    latitude: float
    longitude: float
    # False = nobody collects data for this area; `/dashboard/latest?geo_area_id=` says so.
    weather_polling_active: bool


class AreasResponse(BaseModel):
    areas: list[AreaOut]


def _area_out(a: GeoArea) -> AreaOut:
    return AreaOut(
        geo_area_id=a.id,
        slug=a.slug,
        name=a.name,
        teryt_code=a.teryt_code,
        latitude=a.latitude,
        longitude=a.longitude,
        weather_polling_active=bool(a.weather_polling_active),
    )


@router.get("/areas", response_model=AreasResponse)
def list_areas(
    response: Response,
    active_only: bool = True,
    limit: int = Query(3000, ge=1, le=5000),
    db: Session = Depends(get_db),
) -> AreasResponse:
    """Areas the app can show, for picking a city from a list (TASK-6.2(8), ADR-026).
    Default = actively polled areas only (what `/dashboard/latest` lists without a
    parameter); `active_only=false` adds imported gminas nobody polls.
    ponytail: `limit` only bounds the response (~2.5k gminas fit); search/pagination is
    TASK-12.2's picker. The list changes rarely, so clients/CDN may cache it 5 min."""
    response.headers["Cache-Control"] = "public, max-age=300"
    stmt = select(GeoArea).where(GeoArea.place_id.is_(None))  # places: /places, ADR-029
    stmt = stmt.order_by(GeoArea.name, GeoArea.id).limit(limit)
    if active_only:
        stmt = stmt.where(GeoArea.weather_polling_active.is_(True))
    return AreasResponse(areas=[_area_out(a) for a in db.execute(stmt).scalars().all()])


class GeoLocateResponse(BaseModel):
    # resolved: `area` + how it was assigned. out_of_range: no gmina covers the point and no
    # active area lies within NEAREST_AREA_MAX_KM - `area` null, the client says "outside
    # coverage" (never a far-away guess).
    status: Literal["resolved", "out_of_range"]
    area: AreaOut | None
    assignment_method: Literal["point_in_polygon", "nearest_area"] | None
    # Only for `nearest_area`: how far the area centre is from the point (km, 1 decimal).
    distance_km: float | None


@router.post("/geo/locate", response_model=GeoLocateResponse)
def geo_locate(body: GeoResolveRequest, db: Session = Depends(get_db)) -> GeoLocateResponse:
    """lat/lon -> the area to open the dashboard for (TASK-6.2(8), ADR-026).

    1. point-in-polygon gmina (ADR-019) - also when it has no active polling (the
       dashboard then says "no data here"; the client may activate it, TASK-12.2);
    2. only when NO gmina covers the point (outside Poland / boundaries not imported):
       nearest ACTIVE area within NEAREST_AREA_MAX_KM, disclosed as `nearest_area`;
    3. else `out_of_range`.
    POST body, nothing logged/stored/echoed (ADR-002, like /geo/resolve)."""
    try:
        resolved = resolve_gmina(db, body.latitude, body.longitude)
        if resolved is not None:
            area = db.get(GeoArea, resolved.geo_area_id)
            if area is not None:
                return GeoLocateResponse(
                    status="resolved",
                    area=_area_out(area),
                    assignment_method=METHOD_POINT_IN_POLYGON,
                    distance_km=None,
                )
        active = db.execute(
            select(GeoArea).where(
                GeoArea.weather_polling_active.is_(True), GeoArea.place_id.is_(None)
            )
        )
        by_id = {a.id: a for a in active.scalars().all()}
    except SQLAlchemyError:
        # Constant message, no exc_info: the driver error would carry the coordinates (ADR-002).
        logger.error("geo locate failed: database error (details withheld, ADR-002)")
        raise HTTPException(status_code=503, detail="Geo resolver unavailable") from None
    near = nearest_area(
        body.latitude, body.longitude, ((i, a.latitude, a.longitude) for i, a in by_id.items())
    )
    if near is None:
        return GeoLocateResponse(
            status="out_of_range", area=None, assignment_method=None, distance_km=None
        )
    return GeoLocateResponse(
        status="resolved",
        area=_area_out(by_id[near[0]]),
        assignment_method=METHOD_NEAREST_AREA,
        distance_km=round(near[1], 1),
    )
