"""GIOŚ noise measurements import (ADR-032, GIOS-04): manual, a snapshot per category x voivodeship.

No scheduler: the publication cycle is UNKNOWN (source-registry, rule #16 exception in ADR-032),
so an operator runs this after GIOŚ publishes new data:

    docker compose exec api python -m app.connectors.gios_noise.ingest --year 2024 --validate-only
    docker compose exec api python -m app.connectors.gios_noise.ingest --year 2024

`--validate-only` fetches and checks everything, writes nothing and prints what it saw: it is the
live check that moves the operation from IMPLEMENTABLE to APPROVED
(docs/data/gios/07-operation-gates.md, 08-operator-probe.md). The data is visible to the API only
after a snapshot is promoted (a complete pass).

Each category x voivodeship is its own snapshot: a failed combination (source error, loop,
timeout) leaves its previous snapshot active and never blocks the others (rule #1). Records that
do not fit the verified shape are quarantined with a reason, never repaired.
"""

import argparse
import json
import logging
import sys
from collections import Counter
from collections.abc import Iterator
from datetime import date

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.connectors.gios_noise.parser import (
    CATEGORIES,
    PARSER_VERSION,
    SOURCE_ID,
    VOIVODESHIPS,
    RecordRejected,
    normalize,
)
from app.db import SessionLocal
from app.gios_open import snapshots
from app.gios_open.client import GiosOpenClient, Page, parse_envelope
from app.gios_open.errors import GiosOpenError, SnapshotLockedError
from app.gios_open.paging import iter_pages
from app.gios_open.runner import ingest_snapshot
from app.models import DatasetSnapshot, NoiseMeasurement

logger = logging.getLogger(__name__)

SERVICE = "halas"
OPERATION = "pomiar-halasu-w-srodowisku"
PATH = f"/v1/{OPERATION}"


def request_filters(category: str, voivodeship: str, date_from: date, date_to: date) -> dict:
    """The four parameters the live API requires (docs/data/gios/07-operation-gates.md)."""
    return {
        "kategoria": category,
        "wojewodztwo": voivodeship,
        "dataOd": date_from.isoformat(),
        "dataDo": date_to.isoformat(),
    }


class NoiseStore:
    """The runner's `store` callback for one combination: normalizes a page, quarantines what does
    not fit, skips duplicates, refuses records that contradict the request filters."""

    def __init__(self, category: str, voivodeship: str):
        self.category = category
        self.voivodeship = voivodeship
        self._seen: set[str] = set()

    def __call__(self, db: Session, snapshot: DatasetSnapshot, records: list[dict]) -> int:
        rejected = 0
        for raw in records:
            try:
                record = normalize(raw)
                if record.category != self.category or record.voivodeship != self.voivodeship:
                    raise RecordRejected(
                        "filter_mismatch", f"{record.category}/{record.voivodeship}"
                    )
                if record.natural_key in self._seen:
                    raise RecordRejected("duplicate_record")
            except RecordRejected as exc:
                snapshots.quarantine(db, snapshot, reason=exc.reason, raw=raw, detail=exc.detail)
                rejected += 1
                continue
            self._seen.add(record.natural_key)
            db.add(
                NoiseMeasurement(
                    snapshot_id=snapshot.id,
                    natural_key=record.natural_key,
                    point_code=record.point_code,
                    category=record.category,
                    voivodeship=record.voivodeship,
                    powiat=record.powiat,
                    gmina=record.gmina,
                    locality=record.locality,
                    latitude=record.latitude,
                    longitude=record.longitude,
                    period_label=record.period_label,
                    purpose=record.purpose,
                    date_from=record.date_from,
                    date_to=record.date_to,
                    value_db=record.value_db,
                    exceedance_db=record.exceedance_db,
                    raw=raw,
                )
            )
        return rejected

    @staticmethod
    def discard(db: Session, snapshot_id: int) -> None:
        db.execute(delete(NoiseMeasurement).where(NoiseMeasurement.snapshot_id == snapshot_id))


def pages_from_file(path: str) -> Iterator[tuple[int, Page]]:
    """Pages from a local JSON file: one envelope body or a list of them (as saved from the API).
    Empty pages are skipped, like the live pager stops at them."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    bodies = data if isinstance(data, list) else [data]
    for number, body in enumerate(bodies):
        page = parse_envelope(body)
        if page.records:
            yield number, page


def import_combination(
    db: Session,
    pages: Iterator[tuple[int, Page]],
    *,
    category: str,
    voivodeship: str,
    date_from: date,
    date_to: date,
    endpoint: str,
) -> dict:
    store = NoiseStore(category, voivodeship)
    result = ingest_snapshot(
        db,
        source_id=SOURCE_ID,
        operation=OPERATION,
        filters=request_filters(category, voivodeship, date_from, date_to),
        endpoint=endpoint,
        pages=pages,
        store=store,
        discard=store.discard,
        parser_version=PARSER_VERSION,
    )
    return {
        "records": result.record_count,
        "pages": result.page_count,
        "rejected": result.rejected_count,
    }


def validate_combination(
    pages: Iterator[tuple[int, Page]], category: str, voivodeship: str
) -> dict:
    """Same checks as the import, nothing written."""
    records = page_count = 0
    reasons: Counter[str] = Counter()
    seen: set[str] = set()
    dates: list[date] = []
    for _n, page in pages:
        page_count += 1
        for raw in page.records:
            records += 1
            try:
                rec = normalize(raw)
                if rec.category != category or rec.voivodeship != voivodeship:
                    raise RecordRejected("filter_mismatch")
                if rec.natural_key in seen:
                    raise RecordRejected("duplicate_record")
            except RecordRejected as exc:
                reasons[exc.reason] += 1
                continue
            seen.add(rec.natural_key)
            dates += [rec.date_from, rec.date_to]
    return {
        "records": records,
        "pages": page_count,
        "accepted": len(seen),
        "rejected": dict(reasons),
        "period": [min(dates).isoformat(), max(dates).isoformat()] if dates else None,
    }


def run(
    *,
    db: Session | None,
    client: GiosOpenClient | None,
    categories: list[str],
    voivodeships: list[str],
    date_from: date,
    date_to: date,
    validate_only: bool,
    file: str | None = None,
) -> list[dict]:
    """One result dict per combination; a failing combination is reported, the others continue."""
    results: list[dict] = []
    for category in categories:
        for voivodeship in voivodeships:
            filters = request_filters(category, voivodeship, date_from, date_to)
            row: dict = {"category": category, "voivodeship": voivodeship}
            try:
                if file:
                    pages = pages_from_file(file)
                else:
                    assert client is not None
                    pages = iter_pages(client, PATH, filters)
                source = client.url(PATH) if client else file
                endpoint = f"{source}?{json.dumps(filters, ensure_ascii=False)}"
                if validate_only:
                    row.update(validate_combination(pages, category, voivodeship))
                else:
                    assert db is not None
                    row.update(
                        import_combination(
                            db,
                            pages,
                            category=category,
                            voivodeship=voivodeship,
                            date_from=date_from,
                            date_to=date_to,
                            endpoint=endpoint,
                        )
                    )
                row["status"] = "ok"
            except SnapshotLockedError:
                raise  # another import is running: not a per-combination problem, stop
            except GiosOpenError as exc:
                row.update(status="failed", error=f"{type(exc).__name__}: {exc}")
            results.append(row)
    return results


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="GIOŚ noise measurements import (ADR-032).")
    parser.add_argument("--year", type=int, help="whole calendar year (dataOd/dataDo)")
    parser.add_argument("--date-from", type=date.fromisoformat)
    parser.add_argument("--date-to", type=date.fromisoformat)
    parser.add_argument("--voivodeship", action="append", choices=VOIVODESHIPS, help="default: all")
    parser.add_argument("--category", action="append", choices=CATEGORIES, help="default: all")
    parser.add_argument(
        "--validate-only", action="store_true", help="fetch and check, write nothing"
    )
    parser.add_argument(
        "--file",
        help="import saved API response(s) from a JSON file (needs exactly one "
        "--category and one --voivodeship)",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if args.year:
        date_from, date_to = date(args.year, 1, 1), date(args.year, 12, 31)
    elif args.date_from and args.date_to:
        date_from, date_to = args.date_from, args.date_to
    else:
        parser.error("give --year or both --date-from and --date-to")
    categories = args.category or list(CATEGORIES)
    voivodeships = args.voivodeship or list(VOIVODESHIPS)
    if args.file and (len(categories) != 1 or len(voivodeships) != 1):
        parser.error("--file needs exactly one --category and one --voivodeship")

    db = None if args.validate_only else SessionLocal()
    try:
        results = run(
            db=db,
            client=None if args.file else GiosOpenClient(SERVICE),
            categories=categories,
            voivodeships=voivodeships,
            date_from=date_from,
            date_to=date_to,
            validate_only=args.validate_only,
            file=args.file,
        )
    except SnapshotLockedError as exc:
        print(f"{exc}", file=sys.stderr)
        sys.exit(2)
    finally:
        if db is not None:
            db.close()
    print(json.dumps(results, ensure_ascii=False, indent=2, default=str))
    failed = [r for r in results if r["status"] != "ok"]
    if failed:
        print(f"{len(failed)} of {len(results)} combinations FAILED", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
