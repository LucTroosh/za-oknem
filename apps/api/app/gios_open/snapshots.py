"""Snapshot lifecycle for the GIOŚ open-data datasets (ADR-032 pkt 8, GIOS-02).

staging -> active (atomic promotion, previous active -> superseded) or staging -> failed. The
"one staging snapshot per service" lock is a partial unique index, so a second worker's INSERT
fails in the database (SnapshotLockedError), not in a racy SELECT. A crashed run leaves a stale
staging row: it is taken over only after `gios_open_lock_ttl_minutes`.
"""

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.gios_open.errors import SnapshotLockedError
from app.models import DatasetSnapshot, IngestQuarantine

logger = logging.getLogger(__name__)

STAGING = "staging"
ACTIVE = "active"
SUPERSEDED = "superseded"
FAILED = "failed"
MAX_ERROR_LENGTH = 500


def filters_key(filters: dict[str, Any] | None) -> str:
    """Canonical text of the request filters: same filters -> same key, whatever the order."""
    key = json.dumps(filters or {}, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    if len(key) > 500:
        raise ValueError("filters too long for a snapshot key")
    return key


def begin_snapshot(
    db: Session,
    *,
    source_id: str,
    operation: str,
    filters: dict[str, Any] | None,
    now: datetime | None = None,
) -> DatasetSnapshot:
    """Starts a staging snapshot, or raises SnapshotLockedError when another run of the service is
    in progress. A stale staging row (older than the lock TTL) is closed as failed first."""
    now = now or datetime.now(UTC)
    ttl = timedelta(minutes=settings.gios_open_lock_ttl_minutes)
    stale = (
        db.execute(
            select(DatasetSnapshot).where(
                DatasetSnapshot.source_id == source_id, DatasetSnapshot.status == STAGING
            )
        )
        .scalars()
        .all()
    )
    for row in stale:
        started = row.started_at if row.started_at.tzinfo else row.started_at.replace(tzinfo=UTC)
        if now - started > ttl:
            row.status = FAILED
            row.completed_at = now
            row.error = "stale lock: the run did not finish within the lock TTL"
            logger.warning("took over a stale staging snapshot %s of %s", row.id, source_id)
    db.flush()
    snapshot = DatasetSnapshot(
        source_id=source_id,
        operation=operation,
        filters_key=filters_key(filters),
        status=STAGING,
        started_at=now,
    )
    db.add(snapshot)
    try:
        db.commit()
    except IntegrityError as exc:  # the staging unique index: someone else holds the lock
        db.rollback()
        raise SnapshotLockedError(f"another {source_id} run is in progress") from exc
    return snapshot


def promote(
    db: Session,
    snapshot: DatasetSnapshot,
    *,
    record_count: int,
    page_count: int,
    rejected_count: int,
    checksum: str | None,
    schema_hash: str | None,
    source_fetch_id: int | None = None,
    now: datetime | None = None,
) -> None:
    """staging -> active, and the previous active snapshot of the same dataset -> superseded, in ONE
    transaction. If it cannot commit, nothing changes (the previous snapshot stays active)."""
    now = now or datetime.now(UTC)
    try:
        db.execute(
            update(DatasetSnapshot)
            .where(
                DatasetSnapshot.source_id == snapshot.source_id,
                DatasetSnapshot.operation == snapshot.operation,
                DatasetSnapshot.filters_key == snapshot.filters_key,
                DatasetSnapshot.status == ACTIVE,
            )
            .values(status=SUPERSEDED)
        )
        snapshot.status = ACTIVE
        snapshot.completed_at = now
        snapshot.record_count = record_count
        snapshot.page_count = page_count
        snapshot.rejected_count = rejected_count
        snapshot.checksum = checksum
        snapshot.schema_hash = schema_hash
        snapshot.source_fetch_id = source_fetch_id
        db.commit()
    except Exception:
        db.rollback()
        raise


def fail(
    db: Session, snapshot: DatasetSnapshot, error: str, *, now: datetime | None = None
) -> None:
    """staging -> failed. The previous active snapshot is not touched."""
    snapshot.status = FAILED
    snapshot.completed_at = now or datetime.now(UTC)
    snapshot.error = error[:MAX_ERROR_LENGTH]
    db.commit()


def active_snapshot(
    db: Session, source_id: str, operation: str, filters: dict[str, Any] | None
) -> DatasetSnapshot | None:
    return db.execute(
        select(DatasetSnapshot).where(
            DatasetSnapshot.source_id == source_id,
            DatasetSnapshot.operation == operation,
            DatasetSnapshot.filters_key == filters_key(filters),
            DatasetSnapshot.status == ACTIVE,
        )
    ).scalar_one_or_none()


def quarantine(
    db: Session,
    snapshot: DatasetSnapshot,
    *,
    reason: str,
    raw: Any,
    detail: str | None = None,
    now: datetime | None = None,
) -> None:
    """Keeps a rejected record raw, with the reason (the batch carries on)."""
    db.add(
        IngestQuarantine(
            snapshot_id=snapshot.id,
            source_id=snapshot.source_id,
            operation=snapshot.operation,
            reason=reason[:100],
            detail=detail,
            raw=raw,
            created_at=now or datetime.now(UTC),
        )
    )
