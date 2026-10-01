"""GeoNames PL dump -> place records: parse + validate + normalize (ADR-029).

Input is the tab-separated GeoNames country file (`PL.txt`, 19 columns, UTF-8) that the
operator downloads and hands to the importer; this connector never fetches anything, so
there is no `client.py` (same model as prg_gminy). Column order is the documented GeoNames
`geoname` table; NOT verified against a live file in this environment (egress blocked) -
hence strict column-count validation instead of guessing.
"""

import math
from collections.abc import Iterable
from dataclasses import dataclass, field

from app.connectors.prg_gminy.parser import POLAND_BBOX
from app.places import normalize_name

SOURCE_ID = "geonames_pl"
PARSER_VERSION = "geonames-pl-1"
COLUMNS = 19
MAX_NAME_LENGTH = 200

# Populated places a person lives in or would pick: PPL (place), PPLA..PPLA4 (seats of
# administrative divisions), PPLC (capital), PPLL (locality). Excluded: PPLH/PPLW/PPLQ
# (historical / destroyed / abandoned), PPLX (city sections - duplicate noise), PPLF/PPLG.
ALLOWED_FEATURE_CODES = frozenset({"PPL", "PPLA", "PPLA2", "PPLA3", "PPLA4", "PPLC", "PPLL"})


class PlacesParseError(ValueError):
    """The whole input is unusable (no valid place at all)."""


@dataclass(frozen=True)
class PlaceRecord:
    source_record_id: str  # geonameid
    name: str
    normalized_name: str
    kind: str  # GeoNames feature code
    admin1_code: str | None
    admin2_code: str | None
    latitude: float
    longitude: float
    population: int | None


@dataclass
class ParseResult:
    records: list[PlaceRecord] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)  # human-readable reasons
    skipped: int = 0  # valid lines that are not places we import (other class/code/country)


def _parse_line(line: str) -> PlaceRecord | None:
    """None = not a place we import (skipped); ValueError = malformed (rejected)."""
    cols = line.rstrip("\r\n").split("\t")
    if len(cols) != COLUMNS:
        raise ValueError(f"expected {COLUMNS} columns, got {len(cols)}")
    geonameid, name, _ascii, _alt, lat_s, lon_s, fclass, fcode, country = cols[:9]
    admin1, admin2 = cols[10], cols[11]
    population_s = cols[14]
    if country != "PL" or fclass != "P" or fcode not in ALLOWED_FEATURE_CODES:
        return None
    if not geonameid.isdigit():
        raise ValueError("geonameid is not numeric")
    name = name.strip()
    if not name or len(name) > MAX_NAME_LENGTH:
        raise ValueError("name empty or too long")
    normalized = normalize_name(name)
    if not normalized:
        raise ValueError("name has no latin letters/digits")
    try:
        lat, lon = float(lat_s), float(lon_s)
    except ValueError:
        raise ValueError("non-numeric coordinates") from None
    lon_min, lat_min, lon_max, lat_max = POLAND_BBOX
    if not (math.isfinite(lat) and math.isfinite(lon)):
        raise ValueError("non-finite coordinates")
    if not (lon_min <= lon <= lon_max and lat_min <= lat <= lat_max):
        raise ValueError("coordinates outside Poland bbox")
    population = int(population_s) if population_s.isdigit() else None
    return PlaceRecord(
        source_record_id=geonameid,
        name=name,
        normalized_name=normalized,
        kind=fcode,
        admin1_code=admin1.strip() or None,
        admin2_code=admin2.strip() or None,
        latitude=lat,
        longitude=lon,
        population=population,
    )


def parse_lines(lines: Iterable[str]) -> ParseResult:
    """One bad line never sinks the rest (rule #1); a duplicate geonameid keeps the first
    line and rejects the rest. Raises PlacesParseError when nothing valid came out."""
    result = ParseResult()
    seen: set[str] = set()
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            rec = _parse_line(line)
            if rec is not None and rec.source_record_id in seen:
                raise ValueError("duplicate geonameid")
        except ValueError as exc:
            result.rejected.append(f"line {number}: {exc}")
            continue
        if rec is None:
            result.skipped += 1
            continue
        seen.add(rec.source_record_id)
        result.records.append(rec)
    if not result.records:
        raise PlacesParseError("no valid places in the input")
    return result
