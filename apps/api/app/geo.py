"""Deterministic geo matching (rule #9, never "na oko").

Two distinct methods, deliberately not mixed (BACKLOG TASK-6.2, ADR-019):
- `haversine_km`: nearest station/point (ADR-006) - for data geography.
- `resolve_gmina`: point-in-polygon - the ONLY method for administrative membership.
"""

import math
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points, in kilometers."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


@dataclass(frozen=True)
class ResolvedArea:
    geo_area_id: int
    teryt_code: str
    slug: str
    name: str


# ST_Covers (not ST_Contains): a point exactly on a boundary belongs to the polygon, so
# it is never "nowhere". A point on a shared border is covered by both neighbours; the
# ORDER BY makes that pick deterministic (lowest TERYT code) instead of planner-dependent.
# Holes (enclaves) are not covered by the surrounding gmina; outside every polygon
# (e.g. outside Poland) there is NO match - never a "nearest" fallback.
_RESOLVE_SQL = text(
    """
    SELECT id, teryt_code, slug, name
    FROM geo_areas
    WHERE boundary IS NOT NULL
      AND ST_Covers(boundary, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
    ORDER BY teryt_code, id
    LIMIT 1
    """
)


def resolve_gmina(db: Session, latitude: float, longitude: float) -> ResolvedArea | None:
    """lat/lon -> the gmina whose boundary covers the point, or None. PostgreSQL+PostGIS
    only. Never logs or stores the coordinates (ADR-002)."""
    row = db.execute(_RESOLVE_SQL, {"lat": latitude, "lon": longitude}).first()
    if row is None:
        return None
    return ResolvedArea(geo_area_id=row.id, teryt_code=row.teryt_code, slug=row.slug, name=row.name)
