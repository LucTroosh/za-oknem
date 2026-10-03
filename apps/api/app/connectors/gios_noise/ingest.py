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
import math
import sys
from collections import Counter
from collections.abc import Iterator
from datetime import date

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.config import settings
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
from app.gios_open.paging import PAGE_PARAM, SIZE_PARAM, iter_pages
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


def _duplicate_detail(first: dict, dup: dict) -> str:
    """Tells a verbatim republished record from a different one sharing the natural key (which
    would mean the key is too coarse): `identical` or `differs: <fields>`."""
    fields = sorted(k for k in set(first) | set(dup) if first.get(k) != dup.get(k))
    return "identical" if not fields else "differs: " + ", ".join(fields)


def _differing_fields(first: dict, dup: dict) -> list[str]:
    return sorted(k for k in set(first) | set(dup) if first.get(k) != dup.get(k))


class NoiseStore:
    """The runner's `store` callback for one combination: normalizes a page, quarantines what does
    not fit, folds duplicates, refuses records that contradict the request filters.

    The source publishes some measurements twice, differing only in `przekroczenie` (live,
    2026-10-03: 78 of 208k; one copy usually null, the other a number). Null is the absence of
    information, so the number completes the row; two different numbers contradict each other, so
    the row keeps the measurement and states no exceedance. First-come-wins would let page order
    decide what the user sees."""

    def __init__(self, category: str, voivodeship: str):
        self.category = category
        self.voivodeship = voivodeship
        # natural key -> (the row accepted first, its raw record)
        self._rows: dict[str, tuple[NoiseMeasurement, dict]] = {}
        self._conflict: set[str] = set()  # keys whose copies disagree on przekroczenie

    def _fold_duplicate(self, key: str, raw: dict, exceedance: float | None) -> str:
        row, first_raw = self._rows[key]
        if _differing_fields(first_raw, raw) != ["przekroczenie"]:
            return _duplicate_detail(first_raw, raw)
        mine = row.exceedance_db
        if key in self._conflict:
            return "conflict: przekroczenie"
        if mine == exceedance:
            return "identical"
        if mine is None:
            row.exceedance_db = exceedance
            return "merged: przekroczenie taken from this copy"
        if exceedance is None:
            return "merged: przekroczenie kept, this copy had none"
        self._conflict.add(key)
        row.exceedance_db = None
        return f"conflict: przekroczenie {mine} vs {exceedance}"

    def __call__(self, db: Session, snapshot: DatasetSnapshot, records: list[dict]) -> int:
        rejected = 0
        for raw in records:
            try:
                record = normalize(raw)
                if record.category != self.category or record.voivodeship != self.voivodeship:
                    raise RecordRejected(
                        "filter_mismatch", f"{record.category}/{record.voivodeship}"
                    )
                if record.natural_key in self._rows:
                    detail = self._fold_duplicate(record.natural_key, raw, record.exceedance_db)
                    raise RecordRejected("duplicate_record", detail)
            except RecordRejected as exc:
                snapshots.quarantine(db, snapshot, reason=exc.reason, raw=raw, detail=exc.detail)
                rejected += 1
                continue
            row = NoiseMeasurement(
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
            self._rows[record.natural_key] = (row, raw)
            db.add(row)
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


def count_combination(
    client: GiosOpenClient, category: str, voivodeship: str, date_from: date, date_to: date
) -> dict:
    """ONE request (page size 1): how many records the source reports for this combination.
    `liczbaRekordow` was seen to be the total for Droga x SLASKIE; for every other combination this
    is the source's own claim until an import confirms it, so the result is an estimate."""
    filters = request_filters(category, voivodeship, date_from, date_to)
    page = client.get_page(PATH, {**filters, PAGE_PARAM: 0, SIZE_PARAM: 1})
    reported = 0 if page.empty_observed else page.reported_count
    pages = None if reported is None else math.ceil(reported / settings.gios_open_page_size)
    return {"records_reported": reported, "pages": pages}


def count_summary(results: list[dict]) -> dict:
    """Totals and a time estimate: every page, plus the final empty page of each non-empty
    combination, at one request per `gios_open_min_interval_seconds`."""
    ok = [r for r in results if r["status"] == "ok" and r["records_reported"] is not None]
    pages = sum(r["pages"] for r in ok)
    requests = pages + sum(1 for r in ok if r["pages"])
    return {
        "combinations": results,
        "total_records": sum(r["records_reported"] for r in ok),
        "total_pages": pages,
        "estimated_minutes": round(requests * settings.gios_open_min_interval_seconds / 60, 1),
        "note": "estimate: records as reported by the source, not yet confirmed by an import",
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
    count_only: bool = False,
) -> list[dict]:
    """One result dict per combination; a failing combination is reported, the others continue."""
    results: list[dict] = []
    total = len(categories) * len(voivodeships)
    for category in categories:
        for voivodeship in voivodeships:
            filters = request_filters(category, voivodeship, date_from, date_to)
            row: dict = {"category": category, "voivodeship": voivodeship}
            try:
                if count_only:
                    assert client is not None
                    row.update(count_combination(client, category, voivodeship, date_from, date_to))
                    row["status"] = "ok"
                    results.append(row)
                    logger.info(
                        "[%d/%d] %s %s: %s", len(results), total, category, voivodeship, row
                    )
                    continue
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
            logger.info(
                "[%d/%d] %s %s: %s (records=%s pages=%s)",
                len(results), total, category, voivodeship,  # fmt: skip
                row["status"], row.get("records"), row.get("pages"),
            )  # fmt: skip
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
        "--count-only",
        action="store_true",
        help="ONE request per combination: how many records/pages and how long an import takes",
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
    if args.count_only and (args.file or args.validate_only):
        parser.error("--count-only cannot be combined with --file or --validate-only")

    db = None if args.validate_only or args.count_only else SessionLocal()
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
            count_only=args.count_only,
        )
    except SnapshotLockedError as exc:
        print(f"{exc}", file=sys.stderr)
        sys.exit(2)
    finally:
        if db is not None:
            db.close()
    output = count_summary(results) if args.count_only else results
    print(json.dumps(output, ensure_ascii=False, indent=2, default=str))
    failed = [r for r in results if r["status"] != "ok"]
    if failed:
        print(f"{len(failed)} of {len(results)} combinations FAILED", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
