"""Source-level freshness (ADR-012): record each scheduler run and turn the last
successful one into FRESH/RECENT/STALE/UNAVAILABLE (rule #8)."""

from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models import SourceStatus

MAX_ERROR_LENGTH = 500


def record_source_run(
    db: Session, source_id: str, *, success: bool, error: str | None = None
) -> None:
    """Upsert this source's row. ponytail: get-then-add, safe because ADR-007 runs
    a single scheduler process; switch to INSERT ... ON CONFLICT if that changes."""
    now = datetime.now(UTC)
    row = db.get(SourceStatus, source_id)
    if row is None:
        row = SourceStatus(source_id=source_id, last_attempt_at=now)
        db.add(row)
    row.last_attempt_at = now
    if success:
        row.last_success_at = now
        row.last_error = None
    else:
        row.last_error = (error or "")[:MAX_ERROR_LENGTH]
    db.commit()


def source_freshness(db: Session, source_id: str, freshness: Callable[[datetime], str]) -> dict:
    """`freshness` is the domain's own threshold function (ADR-004), applied to
    the last successful fetch. No successful fetch ever -> UNAVAILABLE."""
    row = db.get(SourceStatus, source_id)
    if row is None or row.last_success_at is None:
        return {"freshness": "UNAVAILABLE", "last_success_at": None}
    last = row.last_success_at
    if last.tzinfo is None:  # SQLite returns naive datetimes; Postgres keeps tz.
        last = last.replace(tzinfo=UTC)
    return {"freshness": freshness(last), "last_success_at": last.isoformat()}
