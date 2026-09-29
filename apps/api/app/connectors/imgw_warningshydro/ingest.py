"""Orchestrates one IMGW hydro-warnings ingest run: fetch -> parse -> validate ->
store. One call returns every active warning - no per-station loop.

    docker compose exec api python -m app.connectors.imgw_warningshydro.ingest
"""

import logging
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError

from app.connectors.imgw_warningshydro import client
from app.connectors.imgw_warningshydro.parser import (
    ImgwWarningsHydroParseError,
    normalize,
    parse_warnings,
)
from app.db import SessionLocal
from app.models import Alert

logger = logging.getLogger(__name__)


def ingest_warning(warning: dict, db, *, fetched_at: datetime) -> bool:
    """Returns True if a new alert was stored. One bad record must not abort the
    run for the rest (rule #1)."""
    try:
        record = normalize(warning, fetched_at=fetched_at)
    except ImgwWarningsHydroParseError as exc:
        numer = warning.get("numer")
        logger.warning("warning %s: FAILED (%s), skipping - see rule #1", numer, exc)
        return False

    exists = (
        db.query(Alert)
        .filter_by(source_id=record["source_id"], source_record_id=record["source_record_id"])
        .first()
    )
    if exists:
        return False

    db.add(Alert(**record))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()  # race with another ingest run - fine, alert exists now
        return False
    logger.info(
        "alert %s: %s (%s)",
        record["external_id"],
        record["event_type"],
        record["severity_raw"],
    )
    return True


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    warnings = parse_warnings(client.fetch_warnings())
    fetched_at = datetime.now(UTC)

    db = SessionLocal()
    try:
        stored = sum(ingest_warning(w, db, fetched_at=fetched_at) for w in warnings)
    finally:
        db.close()
    logger.info("imgw_warningshydro: stored %s/%s new alerts", stored, len(warnings))


if __name__ == "__main__":
    main()
