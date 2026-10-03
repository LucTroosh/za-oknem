"""Provider's Polish index: source labels/times retained, never translated to EAQI."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import provenance
from app.connectors.gios import client
from app.connectors.gios.parser import GIOS_TZ, GiosParseError
from app.models import GiosProviderIndex

logger = logging.getLogger(__name__)
PARAMS = ("SO2", "NO2", "PM10", "PM2.5", "O3")
PARSER_VERSION = "gios-index-1"


class ProviderIndexValue(BaseModel):
    level: Literal[0, 1, 2, 3, 4, 5] | None
    label: str | None
    observed_at: str | None
    calculated_at: str | None


class ProviderIndexPayload(BaseModel):
    index: ProviderIndexValue
    params: dict[str, ProviderIndexValue]
    status: bool | None
    critical_pollutant: Literal["PYL", "OZON"] | None


def _time(raw: object, fetched_at: datetime) -> str | None:
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise GiosParseError("index timestamp is not a string")
    try:
        naive = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
    except ValueError as exc:
        raise GiosParseError("invalid index timestamp") from exc
    time = naive.replace(tzinfo=GIOS_TZ)
    # Source gives local wall time without offset: cannot resolve a repeated/nonexistent hour.
    if time.utcoffset() != naive.replace(tzinfo=GIOS_TZ, fold=1).utcoffset():
        raise GiosParseError("ambiguous/nonexistent index timestamp")
    if time > fetched_at + timedelta(minutes=5):
        raise GiosParseError("future index timestamp")
    return time.astimezone(UTC).isoformat()


def parse_index(data: dict, station_id: str, fetched_at: datetime) -> ProviderIndexPayload:
    row = data.get("AqIndex")
    if not isinstance(row, dict) or str(row.get("Identyfikator stacji pomiarowej")) != station_id:
        raise GiosParseError("index station/shape mismatch")
    if "Status indeksu ogólnego dla stacji pomiarowej" not in row:
        raise GiosParseError("missing index status")

    def value(param: str | None = None) -> ProviderIndexValue:
        suffix = f" dla wskaźnika {param}" if param else ""
        label_key = (
            f"Nazwa kategorii indeksu dla wskażnika {param}" if param else "Nazwa kategorii indeksu"
        )
        observed_key = (
            "Data danych źródłowych, z których policzono wartość indeksu "
            f"dla wskaźnika {param or 'st'}"
        )
        required = [
            f"Wartość indeksu{suffix}",
            label_key,
            observed_key,
            f"Data wykonania obliczeń indeksu{suffix}",
        ]
        if any(key not in row for key in required):
            raise GiosParseError("missing index fields (not explicit null)")
        level = row.get(f"Wartość indeksu{suffix}")
        if level is not None and (type(level) is not int or level not in range(-1, 6)):
            raise GiosParseError("unknown index category")
        # The typo 'wskażnika' is in the published schema AND real response.
        label = row[label_key]
        if label is not None and (not isinstance(label, str) or not label.strip()):
            raise GiosParseError("invalid index label")
        observed = _time(row[observed_key], fetched_at)
        calculated = _time(row.get(f"Data wykonania obliczeń indeksu{suffix}"), fetched_at)
        if level not in (None, -1) and (label is None or observed is None or calculated is None):
            raise GiosParseError("index category without label/source dates")
        if observed and calculated and observed > calculated:
            raise GiosParseError("index calculated before source data")
        return ProviderIndexValue.model_validate(
            {
                "level": None if level == -1 else level,
                "label": label,
                "observed_at": observed,
                "calculated_at": calculated,
            }
        )

    status = row.get("Status indeksu ogólnego dla stacji pomiarowej")
    critical = row.get("Kod zanieczyszczenia krytycznego")
    if status is not None and type(status) is not bool:
        raise GiosParseError("invalid index status")
    if critical not in (None, "PYL", "OZON"):
        raise GiosParseError("unknown critical pollutant")
    return ProviderIndexPayload(
        index=value(),
        params={p: value(p) for p in PARAMS},
        status=status,
        critical_pollutant=critical,
    )


def ingest_index(station_id: str, db: Session) -> bool:
    """Failure retains the previous successful snapshot, separately from measurements."""
    now = datetime.now(UTC)
    fetch_id = None
    try:
        raw = client.fetch_index(station_id)
        fetch_id = provenance.record_fetch(
            db,
            source_id="gios",
            payload=raw,
            fetched_at=now,
            endpoint=f"{client.BASE_URL}/aqindex/getIndex/{station_id}",
            parser_version=PARSER_VERSION,
        )
        parsed = parse_index(raw, station_id, now)
        provenance.set_validation_status(db, fetch_id, provenance.VALID)
        row = db.get(GiosProviderIndex, station_id) or GiosProviderIndex(station_id=station_id)
        row.payload, row.fetched_at, row.source_fetch_id = parsed.model_dump(), now, fetch_id
        row.last_attempt_at, row.last_attempt_succeeded = now, True
        db.add(row)
        db.commit()
        return True
    except Exception:
        db.rollback()
        provenance.set_validation_status(db, fetch_id, provenance.INVALID)
        logger.exception("GIOŚ provider index failed for station %s", station_id)
        # An index/storage outage cannot roll back already committed pollutant readings.
        try:
            row = db.get(GiosProviderIndex, station_id) or GiosProviderIndex(station_id=station_id)
            row.last_attempt_at, row.last_attempt_succeeded = now, False
            db.add(row)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("could not record index failure for station %s", station_id)
        return False
