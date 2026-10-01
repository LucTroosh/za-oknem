"""PRG gmina boundaries: parse + validate a GeoJSON FeatureCollection (TASK-6.2, ADR-019).

The input is a local file the operator prepares from the official PRG download
(docs/tasks/TASK-6.2-geo-engine-foundation.md) - this connector never fetches anything,
so there is no `client.py`. Pure Python, no geometry library: it checks structure and
plausibility; real geometric validity is repaired by PostGIS at import time.
"""

import json
import math
import re
from dataclasses import dataclass
from typing import Any

PARSER_VERSION = "prg-gminy-1"

# Attribute names of the PRG gmina layer. NOT verified against a real file in this repo's
# environment (download blocked) - hence overridable on the CLI, never silently guessed.
DEFAULT_TERYT_FIELD = "JPT_KOD_JE"
DEFAULT_NAME_FIELD = "JPT_NAZWA_"

# Loose bounding box of Poland in EPSG:4326 (lon_min, lat_min, lon_max, lat_max). Its job
# is to catch a file still in EPSG:2180 (values in the hundreds of thousands) or with
# swapped axes - not to police the border.
POLAND_BBOX = (13.9, 48.8, 24.3, 55.1)

_TERYT_RE = re.compile(r"^\d{7}$")
MAX_NAME_LENGTH = 200


class Rejection(str):
    """Human-readable rejection reason that also remembers the feature's TERYT code (if it
    had a string one), so a rejected record's code still counts as 'present in the file'."""

    code: str | None = None


class PrgParseError(ValueError):
    """The whole document is unusable (not a FeatureCollection, no features)."""


@dataclass(frozen=True)
class GminaRecord:
    teryt_code: str
    name: str
    geometry_json: str  # 2D MultiPolygon GeoJSON, lon/lat


def _clean_ring(ring: Any) -> list[list[float]]:
    if not isinstance(ring, list) or len(ring) < 4:
        raise ValueError("ring needs at least 4 positions")
    out = []
    for pos in ring:
        if not isinstance(pos, list) or len(pos) < 2:
            raise ValueError("position needs [lon, lat]")
        lon, lat = pos[0], pos[1]
        if isinstance(lon, bool) or isinstance(lat, bool):
            raise ValueError("non-numeric coordinate")
        if not isinstance(lon, int | float) or not isinstance(lat, int | float):
            raise ValueError("non-numeric coordinate")
        if not (math.isfinite(lon) and math.isfinite(lat)):
            raise ValueError("non-finite coordinate")
        lon_min, lat_min, lon_max, lat_max = POLAND_BBOX
        if not (lon_min <= lon <= lon_max and lat_min <= lat <= lat_max):
            raise ValueError(f"coordinate outside Poland bbox (EPSG:4326 lon/lat expected): {pos}")
        out.append([float(lon), float(lat)])
    if out[0] != out[-1]:
        raise ValueError("ring is not closed")
    return out


def _to_multipolygon(geometry: Any) -> dict:
    if not isinstance(geometry, dict):
        raise ValueError("missing geometry")
    kind, coords = geometry.get("type"), geometry.get("coordinates")
    if kind == "Polygon":
        polygons = [coords]
    elif kind == "MultiPolygon":
        polygons = coords
    else:
        raise ValueError(f"unsupported geometry type {kind!r}")
    if not isinstance(polygons, list) or not polygons:
        raise ValueError("empty geometry")
    cleaned = []
    for polygon in polygons:
        if not isinstance(polygon, list) or not polygon:
            raise ValueError("polygon without rings")
        cleaned.append([_clean_ring(r) for r in polygon])
    return {"type": "MultiPolygon", "coordinates": cleaned}


def parse_feature_collection(
    doc: Any,
    *,
    teryt_field: str = DEFAULT_TERYT_FIELD,
    name_field: str = DEFAULT_NAME_FIELD,
) -> tuple[list[GminaRecord], list[Rejection]]:
    """Returns (valid records, human-readable rejection reasons). One bad feature never
    sinks the rest (rule #1); an unusable document raises PrgParseError."""
    if not isinstance(doc, dict) or doc.get("type") != "FeatureCollection":
        raise PrgParseError("expected a GeoJSON FeatureCollection")
    features = doc.get("features")
    if not isinstance(features, list) or not features:
        raise PrgParseError("FeatureCollection has no features")

    records: list[GminaRecord] = []
    rejected: list[Rejection] = []
    seen: set[str] = set()
    for index, feature in enumerate(features):
        props = feature.get("properties") if isinstance(feature, dict) else None
        code = props.get(teryt_field) if isinstance(props, dict) else None
        label = f"feature #{index} ({code!r})"
        try:
            if not isinstance(code, str) or not _TERYT_RE.match(code):
                raise ValueError(f"{teryt_field} must be a 7-digit TERYT string")
            name = props.get(name_field) if isinstance(props, dict) else None
            if not isinstance(name, str) or not name.strip():
                raise ValueError(f"{name_field} missing")
            if len(name.strip()) > MAX_NAME_LENGTH:
                raise ValueError(f"{name_field} too long")
            if code in seen:
                raise ValueError("duplicate TERYT code")
            geometry = _to_multipolygon(feature.get("geometry"))
        except ValueError as exc:
            reason = Rejection(f"{label}: {exc}")
            reason.code = code if isinstance(code, str) else None
            rejected.append(reason)
            continue
        seen.add(code)
        records.append(GminaRecord(code, name.strip(), json.dumps(geometry)))
    return records, rejected
