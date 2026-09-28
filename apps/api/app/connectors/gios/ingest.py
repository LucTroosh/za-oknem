"""Orchestrates one GIOŚ ingest run: fetch -> parse -> validate -> normalize -> store.

Deliberately manual/on-demand for this vertical slice (Phase 4) — the real scheduler
(who runs this, how often) is Phase 5 work per the roadmap, and per ADR-004 we don't
guess a polling frequency before it's verified. Run it yourself for now:

    docker compose exec api python -m app.connectors.gios.ingest --list
    docker compose exec api python -m app.connectors.gios.ingest --station-id 114
"""

import argparse
import sys
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError

from app.connectors.gios import client
from app.connectors.gios.parser import GiosParseError, find_pm25_sensor, latest_value, normalize
from app.db import SessionLocal
from app.models import Measurement


def ingest_station(station: dict, db) -> bool:
    """Returns True if a new PM2.5 reading was stored. One station's failure is
    logged and skipped — it must not abort ingestion for the rest (rule #1)."""
    station_id = station.get("id")
    try:
        sensors = client.fetch_sensors(str(station_id))
        sensor = find_pm25_sensor(sensors)
        if sensor is None:
            print(f"station {station_id}: no PM2.5 sensor, skipping")
            return False

        data = client.fetch_sensor_data(str(sensor["id"]))
        result = latest_value(data)
        if result is None:
            print(f"station {station_id}: no recent PM2.5 values, skipping")
            return False

        observed_at, value = result
        record = normalize(
            station=station,
            sensor=sensor,
            observed_at=observed_at,
            value=value,
            fetched_at=datetime.now(UTC),
        )
    except (client.GiosApiError, GiosParseError) as exc:
        print(f"station {station_id}: FAILED ({exc}), skipping — see rule #1", file=sys.stderr)
        return False

    exists = (
        db.query(Measurement)
        .filter_by(source_id=record["source_id"], source_record_id=record["source_record_id"])
        .first()
    )
    if exists:
        print(f"station {station_id}: reading already stored, skipping")
        return False

    db.add(Measurement(**record))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()  # race with another ingest run — fine, reading exists now
        return False
    print(f"station {station_id} ({record['station_name']}): PM2.5 = {value} {record['unit']}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="One-off GIOŚ PM2.5 ingest — vertical slice, Master Plan §108."
    )
    parser.add_argument("--station-id", action="append", dest="station_ids", default=[])
    parser.add_argument(
        "--list", action="store_true", help="list stations and exit, fetch nothing else"
    )
    args = parser.parse_args()

    stations = client.fetch_all_stations()

    if args.list:
        for s in stations[:20]:
            print(f"{s['id']}: {s['stationName']}")
        print(f"... {len(stations)} stations total. Re-run with --station-id <id>.")
        return

    if not args.station_ids:
        print("No --station-id given. Run with --list first to pick one.", file=sys.stderr)
        sys.exit(1)

    wanted = {str(sid) for sid in args.station_ids}
    matched = [s for s in stations if str(s["id"]) in wanted]

    db = SessionLocal()
    try:
        for station in matched:
            ingest_station(station, db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
