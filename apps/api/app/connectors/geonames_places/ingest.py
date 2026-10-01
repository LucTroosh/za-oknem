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
import tempfile
import time
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import provenance
from app.connectors.geonames_places.parser import (
    PARSER_VERSION,
    SOURCE_ID,
    ParseResult,
    PlaceRecord,
    PlacesParseError,
    attach_admin_names,
    parse_admin_names,
    parse_lines,
)
from app.db import SessionLocal
from app.models import Place

logger = logging.getLogger(__name__)

CHUNK = 1000
ZIP_MEMBER = "PL.txt"
_FIELDS = (
    "admin1_name",
    "admin2_name",
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
                # A refresh without the admin files must not wipe enriched names.
                changed = [
                    f
                    for f in _FIELDS
                    if not (
                        f.startswith("admin") and f.endswith("_name") and getattr(rec, f) is None
                    )
                ]
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
                elif any(getattr(row, f) != getattr(rec, f) for f in changed):
                    for f in changed:
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


DEFAULT_BASE_URL = "https://download.geonames.org/export/dump/"
DOWNLOAD_FILES = ("PL.zip", "admin1CodesASCII.txt", "admin2Codes.txt")
DOWNLOAD_TIMEOUT_SECONDS = 120.0
DOWNLOAD_ATTEMPTS = 3  # bounded retry (rule #5)


def download(
    dest: Path, *, base_url: str | None = None, sleep=time.sleep, transport=None
) -> dict[str, Path]:
    """Fetch the GeoNames files into `dest` (operator-run, never on a user request, #14).
    Base URL from GEONAMES_BASE_URL (default: the public dump). Each file: timeout, at most
    DOWNLOAD_ATTEMPTS tries with growing pauses; 4xx (except 429) is not retried."""
    base = (base_url or os.environ.get("GEONAMES_BASE_URL") or DEFAULT_BASE_URL).rstrip("/") + "/"
    out: dict[str, Path] = {}
    with httpx.Client(
        timeout=DOWNLOAD_TIMEOUT_SECONDS, follow_redirects=True, transport=transport
    ) as http:
        for name in DOWNLOAD_FILES:
            for attempt in range(1, DOWNLOAD_ATTEMPTS + 1):
                try:
                    resp = http.get(base + name)
                    resp.raise_for_status()
                    break
                except httpx.HTTPError as exc:
                    status = getattr(getattr(exc, "response", None), "status_code", None)
                    fatal = status is not None and 400 <= status < 500 and status != 429
                    if fatal or attempt == DOWNLOAD_ATTEMPTS:
                        raise RuntimeError(
                            f"download of {name} failed: {type(exc).__name__}"
                        ) from None
                    sleep(2.0 * attempt)
            (dest / name).write_bytes(resp.content)
            out[name] = dest / name
    return out


def load(path: Path, admin1: Path | None = None, admin2: Path | None = None) -> ParseResult:
    """Parse the dump; with the admin name files, records also carry voivodeship/powiat names."""
    result = parse_lines(read_lines(path))
    if admin1 or admin2:

        def names(p: Path | None) -> dict[str, str]:
            return parse_admin_names(p.read_text(encoding="utf-8").splitlines()) if p else {}

        result.records = attach_admin_names(result.records, names(admin1), names(admin2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Import GeoNames PL places (ADR-029).")
    parser.add_argument("--file", type=Path, default=os.environ.get("GEONAMES_PL_FILE"))
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument(
        "--download",
        action="store_true",
        help="fetch the dump + admin name files first (GEONAMES_BASE_URL), into a temp dir",
    )
    parser.add_argument("--admin1-file", type=Path, default=os.environ.get("GEONAMES_ADMIN1_FILE"))
    parser.add_argument("--admin2-file", type=Path, default=os.environ.get("GEONAMES_ADMIN2_FILE"))
    parser.add_argument("--sample", action="append", default=[], help="print records by name")
    args = parser.parse_args()
    if args.download and args.file:
        parser.error("--download and --file are mutually exclusive")
    if args.file is None and not args.download:
        parser.error("--file (or GEONAMES_PL_FILE) or --download is required")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    with tempfile.TemporaryDirectory(prefix="geonames-") as tmp:
        try:
            if args.download:
                files = download(Path(tmp))
                parsed = load(
                    files["PL.zip"], files["admin1CodesASCII.txt"], files["admin2Codes.txt"]
                )
            else:
                parsed = load(Path(args.file), args.admin1_file, args.admin2_file)
        except (
            OSError,
            KeyError,
            zipfile.BadZipFile,
            UnicodeDecodeError,
            PlacesParseError,
            RuntimeError,
        ) as exc:
            print(f"Unusable input: {exc}", file=sys.stderr)
            sys.exit(1)
        _run(args, parsed)


def _run(args, parsed: ParseResult) -> None:
    total = len(parsed.records) + len(parsed.rejected)
    print(
        f"parsed: {len(parsed.records)} valid, {len(parsed.rejected)} rejected, "
        f"{parsed.skipped} skipped (not an imported place type)"
    )
    for reason in parsed.rejected[:50]:
        print(f"REJECTED {reason}", file=sys.stderr)
    for wanted in args.sample:
        for rec in [r for r in parsed.records if r.name == wanted][:5]:
            print(f"SAMPLE {rec}")
    if args.validate_only:
        return
    db = SessionLocal()
    try:
        fetch_id = provenance.record_fetch(
            db,
            source_id=SOURCE_ID,
            endpoint="download" if args.download else f"file:{Path(args.file).name}",
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
