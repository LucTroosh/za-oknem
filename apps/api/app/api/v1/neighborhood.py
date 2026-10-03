"""GET /api/v1/neighborhood - "Twoja okolica" (ADR-032): historical / long-term / register data
for a location. DB only (rule #14). Nothing here is an alert (rule #7)."""

import logging
from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import GeoArea
from app.neighborhood import build_noise_section, failed_noise_section

logger = logging.getLogger(__name__)
router = APIRouter()


class SourcePeriod(BaseModel):
    from_: date = Field(alias="from")
    to: date
    precision: Literal["date", "year", "range", "unknown"]

    model_config = {"populate_by_name": True}


class NoiseMeasurementOut(BaseModel):
    period_of_day: str
    value_db: float
    exceedance_db: float | None


class NoiseItemOut(BaseModel):
    category: Literal["Droga", "Lotnisko", "Przemysł", "Kolej"]
    point_code: str
    locality: str | None
    gmina: str | None
    voivodeship: str
    distance_km: float
    period_from: date
    period_to: date
    purpose: str | None
    measurements: list[NoiseMeasurementOut]


class NoiseSectionOut(BaseModel):
    id: Literal["noise"]
    data_kind: Literal["historical_measurement"]
    title: str
    availability: Literal[
        "available", "no_coverage", "no_records", "unavailable", "pending_verification"
    ]
    # Whether OUR import works - not data freshness (historical data has no freshness).
    retrieval_status: Literal["ok", "degraded", "none"]
    message: str | None
    source_period: SourcePeriod | None
    fetched_at: datetime | None
    attribution: str
    source_url: str
    license_url: str
    limitations: list[str]
    search_radius_km: float
    items: list[NoiseItemOut]


class NeighborhoodOut(BaseModel):
    geo_area_id: int
    area_name: str
    enabled: (
        bool  # false: no section is switched on in this deployment (the client hides the entry)
    )
    sections: list[NoiseSectionOut]


@router.get("/neighborhood", response_model=NeighborhoodOut, response_model_by_alias=True)
def get_neighborhood(
    geo_area_id: int = Query(ge=1), db: Session = Depends(get_db)
) -> NeighborhoodOut:
    area = db.get(GeoArea, geo_area_id)
    if area is None:
        raise HTTPException(status_code=404, detail="Unknown geo_area_id")
    sections: list[dict] = []
    if settings.neighborhood_noise_enabled:
        max_km = settings.neighborhood_noise_max_km
        try:
            sections.append(build_noise_section(db, area.latitude, area.longitude, max_km))
        except Exception:  # one section must not take the response down (rule #1)
            logger.exception("neighborhood noise section failed")
            sections.append(failed_noise_section(max_km))
    return NeighborhoodOut(
        geo_area_id=area.id,
        area_name=area.name,
        enabled=bool(sections),
        sections=sections,
    )
