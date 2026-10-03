"""Publish/reconcile only a fully valid national warning snapshot (ADR-034)."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import provenance
from app.config import settings
from app.connectors.imgw_warningsmeteo import client
from app.connectors.imgw_warningsmeteo.parser import normalize, parse_warnings
from app.connectors.imgw_weather.client import job_lock
from app.db import SessionLocal
from app.models import Alert
from app.source_status import record_source_run

PARSER_VERSION = "imgw-meteo-warning-1"
SOURCE = "imgw_warningsmeteo"


def ingest_raw(raw: object, db: Session, *, fetched_at: datetime) -> int:
    fetch_id = provenance.record_fetch(
        db,
        source_id=SOURCE,
        endpoint=client.URL,
        payload=raw,
        fetched_at=fetched_at,
        parser_version=PARSER_VERSION,
    )
    try:
        records = [
            normalize(w, fetched_at=fetched_at, timezone=settings.imgw_warnings_timezone)
            for w in parse_warnings(raw)
        ]
        if len({r["external_id"] for r in records}) != len(records):
            raise ValueError("duplicate warning id")
        existing = {
            a.source_record_id: a
            for a in db.scalars(select(Alert).where(Alert.source_id == SOURCE)).all()
        }
        if any(
            (a.fetched_at if a.fetched_at.tzinfo else a.fetched_at.replace(tzinfo=UTC)) > fetched_at
            for a in existing.values()
        ):
            raise ValueError("older warning snapshot")
        active = {r["external_id"] for r in records}
        for record in records:
            row = existing.get(record["source_record_id"])
            if row is None:
                db.add(Alert(**record, source_fetch_id=fetch_id))
            else:
                for key, value in record.items():
                    setattr(row, key, value)
                row.source_fetch_id = fetch_id
        for key, row in existing.items():
            end = row.valid_until if row.valid_until.tzinfo else row.valid_until.replace(tzinfo=UTC)
            if key not in active and end > fetched_at:
                row.valid_until = fetched_at
                row.source_fetch_id = fetch_id
                row.fetched_at = fetched_at
        db.commit()
    except Exception:
        db.rollback()
        provenance.set_validation_status(db, fetch_id, provenance.INVALID)
        raise
    provenance.set_validation_status(db, fetch_id, provenance.VALID)
    return len(records)


def run() -> bool:
    if not settings.imgw_warnings_enabled or not settings.imgw_warnings_timezone:
        return False
    db = SessionLocal()
    try:
        with job_lock(db, SOURCE) as acquired:
            if not acquired:
                return False
            try:
                ingest_raw(client.fetch_warnings(), db, fetched_at=datetime.now(UTC))
                record_source_run(db, SOURCE, success=True)
            except Exception as exc:
                db.rollback()
                record_source_run(db, SOURCE, success=False, error=str(exc))
                raise
    finally:
        db.close()
    return True


if __name__ == "__main__":
    if not run():
        raise SystemExit("IMGW warnings disabled; source timezone must be verified")
