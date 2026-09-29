"""Daily outbound-call counter + 70%-threshold alert per source (TASK-13.0a:
ADR-001/ADR-003/ADR-004 require this, no task in the queue implemented it yet).

Not a general rate limiter - GIOŚ's per-minute throttling (client.py) is a
separate, already-solved problem. This is specifically the *daily* budget
ADR-003 calls out for Open-Meteo (10 000/day, alert at 70%), in a shape any
other source with a documented daily cap can reuse.
"""

import logging
from datetime import UTC, date, datetime

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import SourceFetchCounter

logger = logging.getLogger(__name__)

ALERT_THRESHOLD_PCT = 0.7


def record_fetch_call(
    db: Session, source_id: str, *, units: int = 1, today: date | None = None
) -> int:
    """Increment today's call count for `source_id` by `units` and return the new
    total. One row per (source_id, day).

    Atomic `UPDATE ... SET count = count + :units RETURNING count` (Codex review
    [P2]) - the previous "read row.count, add units, commit()" pattern loses
    updates under concurrent ingest runs: two processes can both read count=N,
    each independently compute N+units, and whichever commits second overwrites
    the first's increment instead of stacking on top of it. The UPDATE is atomic
    at the row level regardless of how many processes race on it; RETURNING avoids
    a second round-trip (and the tiny window a separate SELECT-after-UPDATE would
    still leave). Postgres always supports RETURNING; the SQLite test fixture does
    too since 3.35 (this sandbox has 3.45)."""
    today = today or datetime.now(UTC).date()
    result = db.execute(
        update(SourceFetchCounter)
        .where(SourceFetchCounter.source_id == source_id, SourceFetchCounter.day == today)
        .values(count=SourceFetchCounter.count + units)
        .returning(SourceFetchCounter.count)
    )
    new_count = result.scalar_one_or_none()
    if new_count is None:
        # First call today for this source - nothing for the UPDATE above to match.
        try:
            db.add(SourceFetchCounter(source_id=source_id, day=today, count=units))
            db.commit()
            return units
        except IntegrityError:
            db.rollback()  # race: another process inserted this (source_id, day) first
            result = db.execute(
                update(SourceFetchCounter)
                .where(SourceFetchCounter.source_id == source_id, SourceFetchCounter.day == today)
                .values(count=SourceFetchCounter.count + units)
                .returning(SourceFetchCounter.count)
            )
            new_count = result.scalar_one()
    db.commit()
    return new_count


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
