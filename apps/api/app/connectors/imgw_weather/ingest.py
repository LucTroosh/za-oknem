"""Atomic national observation batches. Last good data survives an invalid snapshot."""

import argparse
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app import provenance
from app.config import settings
from app.connectors.imgw_weather import client
from app.connectors.imgw_weather.client import job_lock
from app.connectors.imgw_weather.parser import PARSER_VERSION, normalize
from app.db import SessionLocal
from app.models import ImgwWeatherStation, Measurement
from app.source_status import record_source_run

logger = logging.getLogger(__name__)


def ingest_raw(raw: object, dataset: str, db: Session, *, fetched_at: datetime) -> int:
    source = "imgw_" + dataset
    fetch_id = provenance.record_fetch(
        db,
        source_id=source,
        endpoint=client.BASE + dataset,
        payload=raw,
        fetched_at=fetched_at,
        parser_version=PARSER_VERSION,
    )
    try:
        if not isinstance(raw, list) or not raw or any(not isinstance(r, dict) for r in raw):
            raise ValueError("expected nonempty station list")
        parsed, errors, seen = [], [], set()
        failed_rows = 0
        duplicate = False
        for row in raw:
            try:
                sid = row.get("id_stacji" if dataset == "synop" else "kod_stacji")
                if isinstance(sid, str) and sid.isdigit():
                    if sid in seen:
                        duplicate = True
                        raise ValueError("duplicate station")
                    seen.add(sid)
                station, values, issues = normalize(
                    row, dataset, fetched_at=fetched_at, timezone=settings.imgw_weather_timezone
                )
                parsed.append((station, values))
                errors.extend(issues)
                if any(not e.endswith("station coordinates pending") for e in issues):
                    failed_rows += 1
            except ValueError as exc:
                errors.append(str(exc))
                failed_rows += 1
        # Reject incomplete contracts, but SYNOP's documented missing geometry is expected.
        critical = [e for e in errors if not e.endswith("station coordinates pending")]
        if duplicate or failed_rows / len(raw) > 0.02 or not parsed:
            raise ValueError(f"incomplete {dataset} snapshot: {len(critical)} errors")
        if critical:
            logger.warning(
                "IMGW %s: %s/%s damaged stations; raw fetch %s retained",
                dataset,
                failed_rows,
                len(raw),
                fetch_id,
            )
        catalogs = {
            row.station_id: row
            for row in db.scalars(
                select(ImgwWeatherStation).where(ImgwWeatherStation.source_id == source)
            ).all()
        }
        wanted = [r["source_record_id"] for _, values in parsed for r in values]
        existing_ids = (
            set(
                db.scalars(
                    select(Measurement.source_record_id).where(
                        Measurement.source_id == source, Measurement.source_record_id.in_(wanted)
                    )
                ).all()
            )
            if wanted
            else set()
        )
        for station, values in parsed:
            catalog = catalogs.get(station["station_id"])
            if catalog and _utc(catalog.fetched_at) > fetched_at:
                raise ValueError("older snapshot cannot replace catalog")
            if catalog is None:
                catalog = ImgwWeatherStation(**station, fetched_at=fetched_at)
                db.add(catalog)
            else:
                for key, value in station.items():
                    setattr(catalog, key, value)
                catalog.fetched_at = fetched_at
            for record in values:
                if record["source_record_id"] not in existing_ids:
                    db.add(Measurement(**record, source_fetch_id=fetch_id))
        # Only our observations; GIOŚ and hydro retention are unaffected.
        db.execute(
            delete(Measurement).where(
                Measurement.source_id == source,
                Measurement.observed_at < fetched_at - timedelta(days=90),
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        provenance.set_validation_status(db, fetch_id, provenance.INVALID)
        raise
    provenance.set_validation_status(
        db, fetch_id, provenance.PARTIAL if errors else provenance.VALID
    )
    return sum(len(values) for _, values in parsed)


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def run(dataset: str) -> bool:
    if not settings.imgw_observations_enabled:
        return False
    db = SessionLocal()
    try:
        with job_lock(db, "imgw_" + dataset) as acquired:
            if not acquired:
                return False
            try:
                total = ingest_raw(client.fetch(dataset), dataset, db, fetched_at=datetime.now(UTC))
                record_source_run(db, "imgw_" + dataset, success=True)
                logger.info("IMGW %s: %s observations", dataset, total)
            except Exception as exc:
                db.rollback()
                record_source_run(db, "imgw_" + dataset, success=False, error=str(exc))
                raise
    finally:
        db.close()
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=("synop", "meteo"), required=True)
    args = parser.parse_args()
    if not run(args.dataset):
        raise SystemExit("IMGW observations disabled; verify source gates before enabling")


if __name__ == "__main__":
    main()
