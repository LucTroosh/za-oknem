from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.geo import resolve_gmina

router = APIRouter()


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
    resolved = resolve_gmina(db, body.latitude, body.longitude)
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
