"""Import gmina boundaries (PRG) + TERYT codes into geo_areas (TASK-6.2, ADR-019).

Operator-run, from a LOCAL GeoJSON file in EPSG:4326 (see the task doc for how to make
one from the official PRG download; the repo contains no data). Idempotent: re-running
the same file changes nothing but `boundary` of existing rows.

    docker compose exec api python -m app.connectors.prg_gminy.ingest --file /data/gminy.geojson
    ... --validate-only   # parse + report, no database access

Per record, in this order:
1. row with this TERYT code exists      -> update its boundary;
2. a seeded city (no TERYT yet) lies inside the polygon (point-in-polygon, never by
   name) -> that row adopts the TERYT code + boundary, keeping its id/slug so its
   weather history stays attached;
3. otherwise                             -> insert a new row with weather_polling_active
   = false (geo-matching only; polling is opt-in, BACKLOG TASK-6.2 (4)).
"""

import argparse
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import text

from app import provenance
from app.connectors.prg_gminy.parser import (
    DEFAULT_NAME_FIELD,
    DEFAULT_TERYT_FIELD,
    PARSER_VERSION,
    GminaRecord,
    PrgParseError,
    parse_feature_collection,
)
from app.db import SessionLocal

logger = logging.getLogger(__name__)

SOURCE_ID = "prg_gminy"

# PostGIS repairs invalid rings (PRG data is not guaranteed valid), keeps only polygons,
# and normalises to a MultiPolygon. The result is computed once per record and passed on
# as hex EWKB so the three statements below share one exact geometry.
_PREPARE_SQL = text(
    """
    SELECT ST_AsHEXEWKB(ST_Multi(ST_CollectionExtract(ST_MakeValid(g), 3))) AS hex,
           ST_IsEmpty(ST_CollectionExtract(ST_MakeValid(g), 3)) AS is_empty,
           ST_IsValid(g) AS was_valid
    FROM (SELECT ST_SetSRID(ST_GeomFromGeoJSON(CAST(:geojson AS text)), 4326) AS g) t
    """
)
_GEOM = "ST_GeomFromEWKB(decode(CAST(:hex AS text), 'hex'))"
_UPDATE_SQL = text(f"UPDATE geo_areas SET boundary = {_GEOM} WHERE teryt_code = :code")
_ADOPT_SQL = text(
    f"""
    UPDATE geo_areas SET teryt_code = :code, boundary = {_GEOM}
    WHERE teryt_code IS NULL
      AND ST_Covers({_GEOM}, ST_SetSRID(ST_MakePoint(longitude, latitude), 4326))
    """
)
_INSERT_SQL = text(
    f"""
    INSERT INTO geo_areas
        (slug, name, latitude, longitude, teryt_code, boundary, weather_polling_active)
    SELECT CAST(:slug AS text), CAST(:name AS text),
           ST_Y(ST_PointOnSurface(g.geom)), ST_X(ST_PointOnSurface(g.geom)),
           CAST(:code AS text), g.geom, false
    FROM (SELECT {_GEOM} AS geom) g
    """
)


@dataclass
class ImportReport:
    inserted: int = 0
    updated: int = 0
    adopted_seeds: int = 0
    repaired: int = 0  # boundaries PostGIS had to make valid
    rejected: list[str] = field(default_factory=list)


def import_records(records: list[GminaRecord], db) -> ImportReport:
    report = ImportReport()
    for rec in records:
        try:
            prepared = db.execute(_PREPARE_SQL, {"geojson": rec.geometry_json}).one()
            if prepared.is_empty:
                raise ValueError("no polygon left after validation")
            params = {"hex": prepared.hex, "code": rec.teryt_code}
            if db.execute(_UPDATE_SQL, params).rowcount:
                report.updated += 1
            elif db.execute(_ADOPT_SQL, params).rowcount:
                report.adopted_seeds += 1
            else:
                db.execute(
                    _INSERT_SQL,
                    {**params, "slug": f"teryt-{rec.teryt_code}", "name": rec.name},
                )
                report.inserted += 1
            db.commit()
            if not prepared.was_valid:
                report.repaired += 1
        except Exception as exc:  # one gmina must not abort the rest (rule #1)
            db.rollback()
            report.rejected.append(f"{rec.teryt_code} ({rec.name}): {type(exc).__name__}: {exc}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Import PRG gmina boundaries (TASK-6.2).")
    parser.add_argument("--file", required=True, type=Path, help="GeoJSON, EPSG:4326")
    parser.add_argument("--teryt-field", default=DEFAULT_TERYT_FIELD)
    parser.add_argument("--name-field", default=DEFAULT_NAME_FIELD)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    try:
        doc = json.loads(args.file.read_text(encoding="utf-8"))
        records, rejected = parse_feature_collection(
            doc, teryt_field=args.teryt_field, name_field=args.name_field
        )
    except (OSError, ValueError, PrgParseError) as exc:  # json errors are ValueError
        print(f"Unusable input file: {exc}", file=sys.stderr)
        sys.exit(1)

    total = len(records) + len(rejected)
    print(f"parsed: {len(records)} valid, {len(rejected)} rejected of {total} features")
    report = ImportReport(rejected=list(rejected))
    if not args.validate_only:
        db = SessionLocal()
        try:
            fetch_id = provenance.record_fetch(
                db,
                source_id=SOURCE_ID,
                endpoint=f"file:{args.file.name}",
                payload=None,  # tens of MB; the operator keeps the source file
                fetched_at=datetime.now(UTC),
                parser_version=PARSER_VERSION,
            )
            db_report = import_records(records, db)
            report.inserted, report.updated = db_report.inserted, db_report.updated
            report.adopted_seeds, report.repaired = db_report.adopted_seeds, db_report.repaired
            report.rejected += db_report.rejected
            provenance.set_validation_status(
                db, fetch_id, provenance.batch_status(total, len(report.rejected))
            )
        finally:
            db.close()
        print(
            f"inserted={report.inserted} updated={report.updated} "
            f"adopted_seeds={report.adopted_seeds} repaired={report.repaired}"
        )
    for line in report.rejected:
        print(f"REJECTED {line}", file=sys.stderr)
    if report.rejected:
        sys.exit(1)


if __name__ == "__main__":
    main()
