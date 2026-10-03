"""Runs one complete pass into a staging snapshot and promotes it (ADR-032 pkt 8, GIOS-02).

The connector supplies the pages (`paging.iter_pages`) and a `store` callback that writes its own
typed rows under the staging snapshot; this module owns everything that must be identical for every
dataset: the per-service lock, per-page commits, completeness, provenance, atomic promotion,
`source_status` (ADR-012) and the guarantee that a failure leaves the previous snapshot active.
"""

import hashlib
import json
import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app import provenance
from app.gios_open import snapshots
from app.gios_open.client import Page
from app.gios_open.paging import page_hash
from app.models import DatasetSnapshot
from app.source_status import record_source_run

logger = logging.getLogger(__name__)

# Writes one page of records under the staging snapshot; returns how many it quarantined (rejected).
StoreFn = Callable[[Session, DatasetSnapshot, list[dict]], int]
# Removes the rows a failed staging snapshot wrote (invisible anyway: readers join `active`).
DiscardFn = Callable[[Session, int], None]


@dataclass(frozen=True)
class IngestResult:
    snapshot_id: int
    record_count: int
    page_count: int
    rejected_count: int


def _schema_hash(keys: set[str]) -> str:
    return hashlib.sha256(json.dumps(sorted(keys)).encode()).hexdigest()


def ingest_snapshot(
    db: Session,
    *,
    source_id: str,
    operation: str,
    filters: dict | None,
    endpoint: str,
    pages: Iterable[tuple[int, Page]],
    store: StoreFn,
    discard: DiscardFn | None = None,
    parser_version: str,
    now: datetime | None = None,
) -> IngestResult:
    """Raises SnapshotLockedError when another run of the service is in progress (nothing recorded:
    that is not a source failure). Any other failure marks the snapshot failed, records the failed
    run in source_status and re-raises; the previous active snapshot is untouched."""
    snapshot = snapshots.begin_snapshot(
        db, source_id=source_id, operation=operation, filters=filters, now=now
    )
    records = page_count = rejected = 0
    checksum = hashlib.sha256()
    keys: set[str] = set()
    first_raw: dict | None = None
    try:
        for _number, page in pages:
            rejected += store(db, snapshot, page.records) or 0
            db.commit()  # per page: memory stays bounded, rows stay invisible until promotion
            records += len(page.records)
            page_count += 1
            checksum.update(page_hash(page.records).encode())
            for record in page.records:
                keys.update(record)
            first_raw = first_raw or page.raw
        # Only a generator that finished (a confirmed empty page, see paging) gets here.
        fetched_at = now or datetime.now(UTC)
        fetch_id = provenance.record_fetch(
            db,
            source_id=source_id,
            endpoint=endpoint[:500],
            payload={
                "operation": operation,
                "filters": filters or {},
                "pages": page_count,
                "records": records,
                "rejected": rejected,
                "checksum": checksum.hexdigest() if page_count else None,
                "first_page": first_raw,
            },
            fetched_at=fetched_at,
            parser_version=parser_version,
        )
        snapshots.promote(
            db,
            snapshot,
            record_count=records,
            page_count=page_count,
            rejected_count=rejected,
            checksum=checksum.hexdigest() if page_count else None,
            schema_hash=_schema_hash(keys) if keys else None,
            source_fetch_id=fetch_id,
            now=fetched_at,
        )
        provenance.set_validation_status(db, fetch_id, provenance.batch_status(records, rejected))
        record_source_run(db, source_id, success=True)
        return IngestResult(snapshot.id, records, page_count, rejected)
    except Exception as exc:
        db.rollback()
        if discard is not None:
            try:
                discard(db, snapshot.id)
                db.commit()
            except Exception:
                db.rollback()
                logger.exception("could not discard the rows of failed snapshot %s", snapshot.id)
        reason = f"{type(exc).__name__}: {exc}"
        snapshots.fail(db, snapshot, reason)
        record_source_run(db, source_id, success=False, error=reason)
        raise
