"""Daily outbound-call counter + 70%-threshold alert per source (TASK-13.0a:
ADR-001/ADR-003/ADR-004 require this, no task in the queue implemented it yet).

Not a general rate limiter - GIOŚ's per-minute throttling (client.py) is a
separate, already-solved problem. This is specifically the *daily* budget
ADR-003 calls out for Open-Meteo (10 000/day, alert at 70%), in a shape any
other source with a documented daily cap can reuse.
"""

import logging
from datetime import UTC, date, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import SourceFetchCounter

logger = logging.getLogger(__name__)

ALERT_THRESHOLD_PCT = 0.7


def record_fetch_call(db: Session, source_id: str, *, today: date | None = None) -> int:
    """Increment today's call count for `source_id` and return the new total.
    One row per (source_id, day) - same read-then-write-with-retry pattern as
    ingest.py's _store_if_new() for the concurrent-insert race, since this
    isn't Postgres-dialect-only code (portable across the SQLite test fixture
    too, unlike the DISTINCT ON queries elsewhere)."""
    today = today or datetime.now(UTC).date()
    row = db.query(SourceFetchCounter).filter_by(source_id=source_id, day=today).first()
    if row is None:
        row = SourceFetchCounter(source_id=source_id, day=today, count=0)
        db.add(row)
    row.count += 1
    try:
        db.commit()
    except IntegrityError:
        db.rollback()  # race: another process inserted this (source_id, day) first
        row = db.query(SourceFetchCounter).filter_by(source_id=source_id, day=today).first()
        row.count += 1
        db.commit()
    return row.count


def check_daily_budget(source_id: str, count: int, daily_limit: int) -> None:
    """Log a warning once the day's call count reaches ALERT_THRESHOLD_PCT of
    daily_limit (ADR-003's "alert przy 70% dziennego limitu"). No monitoring
    service exists yet (TASK-13.2, blocked on an external account) - a log
    line an operator can grep/alert on is the honest MVP version, not a no-op
    until that task lands."""
    threshold = daily_limit * ALERT_THRESHOLD_PCT
    if count >= threshold:
        logger.warning(
            "source %s: daily call budget at %s/%s (%.0f%% >= %.0f%% ADR-003 threshold)",
            source_id,
            count,
            daily_limit,
            100 * count / daily_limit,
            100 * ALERT_THRESHOLD_PCT,
        )
