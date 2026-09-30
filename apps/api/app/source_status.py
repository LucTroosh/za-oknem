"""Source-level freshness (ADR-012): record each scheduler run and turn the last
successful one into FRESH/RECENT/STALE/UNAVAILABLE (rule #8)."""

from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.models import SourceStatus

MAX_ERROR_LENGTH = 500


def record_source_run(
    db: Session, source_id: str, *, success: bool, error: str | None = None
) -> None:
    """Atomic upsert (INSERT ... ON CONFLICT DO UPDATE). The scheduler AND the
    manual CLI ingest both record runs (ADR-012), so two writers can race on the
    first insert or interleave updates - a get-then-add would raise
    IntegrityError or lose one run's outcome (Codex review). Postgres in
    production, SQLite in tests: both support ON CONFLICT with the same API."""
    now = datetime.now(UTC)
    values = {"source_id": source_id, "last_attempt_at": now}
    updates = {"last_attempt_at": now}
    if success:
        values |= {"last_success_at": now, "last_error": None}
        updates |= {"last_success_at": now, "last_error": None}
    else:
        values["last_error"] = updates["last_error"] = (error or "")[:MAX_ERROR_LENGTH]
    insert = pg_insert if db.get_bind().dialect.name == "postgresql" else sqlite_insert
    stmt = insert(SourceStatus).values(**values)
    db.execute(stmt.on_conflict_do_update(index_elements=["source_id"], set_=updates))
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
