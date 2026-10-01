"""Import the GeoNames PL places dump into `places` (ADR-029). Operator-run, from a LOCAL file
(`PL.txt`, or the `PL.zip` as downloaded - its `PL.txt` member is read). Path from `--file`
or the GEONAMES_PL_FILE env var; the repo contains no data. Idempotent: re-running the same
file changes nothing; a newer file updates rows in place (keyed by geonameid).

    docker compose exec api python -m app.connectors.geonames_places.ingest --file /data/PL.zip
    ... --validate-only   # parse + report, no database access

Places missing from a newer file are NOT deleted (geo_areas may reference them, ADR-029).
Attribution (CC BY 4.0, GeoNames) is required wherever places are shown - source-registry.
"""

import argparse
import logging
import os
import sys
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import provenance
from app.connectors.geonames_places.parser import (
    PARSER_VERSION,
    SOURCE_ID,
    ParseResult,
    PlaceRecord,
    PlacesParseError,
    parse_lines,
)
from app.db import SessionLocal
from app.models import Place

logger = logging.getLogger(__name__)

CHUNK = 1000
ZIP_MEMBER = "PL.txt"
_FIELDS = (
    "name",
    "normalized_name",
    "kind",
    "admin1_code",
    "admin2_code",
    "latitude",
    "longitude",
    "population",
)


def read_lines(path: Path) -> Iterator[str]:
    """Lines of the dump: plain text, or the PL.txt member of a zip."""
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as zf, zf.open(ZIP_MEMBER) as raw:
            for line in raw:
                yield line.decode("utf-8")
    else:
        with path.open(encoding="utf-8") as fh:
            yield from fh


@dataclass
class ImportReport:
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    failed: int = 0  # records in chunks the database refused


def import_records(
    records: list[PlaceRecord], db: Session, *, imported_at: datetime | None = None
) -> ImportReport:
    imported_at = imported_at or datetime.now(UTC)
    report = ImportReport()
    for start in range(0, len(records), CHUNK):
        chunk = records[start : start + CHUNK]
        try:
            existing = {
                p.source_record_id: p
                for p in db.execute(
                    select(Place).where(
                        Place.source == SOURCE_ID,
                        Place.source_record_id.in_([r.source_record_id for r in chunk]),
                    )
                )
                .scalars()
                .all()
            }
            counts = ImportReport()
            for rec in chunk:
                row = existing.get(rec.source_record_id)
                if row is None:
                    db.add(
                        Place(
                            source=SOURCE_ID,
                            source_record_id=rec.source_record_id,
                            imported_at=imported_at,
                            **{f: getattr(rec, f) for f in _FIELDS},
                        )
                    )
                    counts.inserted += 1
                elif any(getattr(row, f) != getattr(rec, f) for f in _FIELDS):
                    for f in _FIELDS:
                        setattr(row, f, getattr(rec, f))
                    row.imported_at = imported_at
                    counts.updated += 1
                else:
                    counts.unchanged += 1
            db.commit()
        except Exception:  # rule #1: one bad chunk must not abort the rest
            db.rollback()
            logger.exception("places import: chunk at record %s failed", start)
            report.failed += len(chunk)
            continue
        report.inserted += counts.inserted
        report.updated += counts.updated
        report.unchanged += counts.unchanged
    return report


def load(path: Path) -> ParseResult:
    return parse_lines(read_lines(path))


def main() -> None:
    parser = argparse.ArgumentParser(description="Import GeoNames PL places (ADR-029).")
    parser.add_argument("--file", type=Path, default=os.environ.get("GEONAMES_PL_FILE"))
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if args.file is None:
        parser.error("--file (or GEONAMES_PL_FILE) is required")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    try:
        parsed = load(Path(args.file))
    except (OSError, KeyError, zipfile.BadZipFile, UnicodeDecodeError, PlacesParseError) as exc:
        print(f"Unusable input file: {exc}", file=sys.stderr)
        sys.exit(1)
    total = len(parsed.records) + len(parsed.rejected)
    print(
        f"parsed: {len(parsed.records)} valid, {len(parsed.rejected)} rejected, "
        f"{parsed.skipped} skipped (not an imported place type)"
    )
    for reason in parsed.rejected[:50]:
        print(f"REJECTED {reason}", file=sys.stderr)
    if args.validate_only:
        return
    db = SessionLocal()
    try:
        fetch_id = provenance.record_fetch(
            db,
            source_id=SOURCE_ID,
            endpoint=f"file:{Path(args.file).name}",
            payload=None,  # large; the operator keeps the source file
            fetched_at=datetime.now(UTC),
            parser_version=PARSER_VERSION,
        )
        report = import_records(parsed.records, db)
        provenance.set_validation_status(
            db, fetch_id, provenance.batch_status(total, len(parsed.rejected) + report.failed)
        )
    finally:
        db.close()
    print(
        f"inserted={report.inserted} updated={report.updated} "
        f"unchanged={report.unchanged} failed={report.failed}"
    )
    if report.failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
