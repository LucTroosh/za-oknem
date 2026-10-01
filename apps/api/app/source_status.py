"""Source-level freshness (ADR-012): record each scheduler run and turn the last
successful one into FRESH/RECENT/STALE/UNAVAILABLE (rule #8)."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.models import SourceStatus

MAX_ERROR_LENGTH = 500
# Hosts writing source_status (scheduler, manual CLI) are expected to be
# NTP-synced. A success dated further ahead than this, as seen by the reading
# process, is not trusted and reads STALE (fail safe, never falsely FRESH).
MAX_CLOCK_SKEW = timedelta(minutes=5)


def record_source_run(
    db: Session,
    source_id: str,
    *,
    success: bool,
    error: str | None = None,
    now: datetime | None = None,
) -> None:
    """Atomic upsert (INSERT ... ON CONFLICT DO UPDATE). The scheduler AND the
    manual CLI ingest both record runs (ADR-012), so two writers can race on the
    first insert or interleave updates - a get-then-add would raise
    IntegrityError or lose one run's outcome (Codex review). Postgres in
    production, SQLite in tests: both support ON CONFLICT with the same API.

    The update applies only if this run's attempt is not older than the stored
    one: a writer that computed `now` earlier and paused could otherwise move
    timestamps backward or replace a newer failure with an older success
    (Codex review). A late older result is dropped - at worst the source turns
    STALE sooner, never falsely FRESH. The guard compares only the writers'
    own timestamps: judging "future" against one host's clock would let a slow
    host's reading of a valid row defeat the guard (Codex review). `now` is
    injectable for tests."""
    now = now or datetime.now(UTC)
    values = {"source_id": source_id, "last_attempt_at": now}
    updates = {"last_attempt_at": now}
    if success:
        values |= {"last_success_at": now, "last_error": None}
        updates |= {"last_success_at": now, "last_error": None}
    else:
        values["last_error"] = updates["last_error"] = (error or "")[:MAX_ERROR_LENGTH]
    insert = pg_insert if db.get_bind().dialect.name == "postgresql" else sqlite_insert
    stmt = insert(SourceStatus).values(**values)
    db.execute(
        stmt.on_conflict_do_update(
            index_elements=["source_id"],
            set_=updates,
            where=SourceStatus.last_attempt_at <= stmt.excluded.last_attempt_at,
        )
    )
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
    if last > datetime.now(UTC) + MAX_CLOCK_SKEW:  # future success can't be verified
        return {"freshness": "STALE", "last_success_at": last.isoformat()}
    return {"freshness": freshness(last), "last_success_at": last.isoformat()}


# Share of failed elements (stations/areas) tolerated in one run. Small fixed sets
# (a few Open-Meteo areas, configured GIOS stations): only a failing majority is an
# outage. Large sets (IMGW hydro, ~900 stations) set their own tight bound, so one
# permanently broken record cannot keep the whole source STALE forever (rule #1).
SMALL_SET_MAX_FAILED_FRACTION = 0.5


def run_failure_reason(total: int, failed: int, *, max_failed_fraction: float) -> str | None:
    """Shared policy for jobs that isolate errors per element (TASK-13.1): the run is
    a failure when nothing came back, no element succeeded, or more than
    `max_failed_fraction` failed; otherwise a (partial) success. None = acceptable."""
    if total == 0:
        return "nothing returned"
    if failed >= total or failed / total > max_failed_fraction:
        return f"{failed}/{total} failed"
    return None
