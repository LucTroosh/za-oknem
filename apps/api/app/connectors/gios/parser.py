"""Parse / validate / normalize raw GIOŚ JSON into Measurement-ready dicts.

Field names below (stationName, gegrLat/gegrLon, param.paramFormula, values[].date/value)
are based on the documented, stable shape of this API — NOT verified against a live
response in this environment. If real data doesn't match, this will raise KeyError/
ValueError loudly (never silently return wrong data) — see Source Registry note.
"""

from datetime import datetime
from typing import Any

PM25_FORMULA = "PM2.5"
PM25_UNIT = "µg/m³"


class GiosParseError(Exception):
    """Raised when a GIOŚ payload doesn't match the expected shape."""


def find_pm25_sensor(sensors: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Vertical slice scope (Master Plan §108): PM2.5 only, not the full parameter set."""
    for sensor in sensors:
        param = sensor.get("param", {})
        if param.get("paramFormula") == PM25_FORMULA:
            return sensor
    return None


def latest_value(data: dict[str, Any]) -> tuple[datetime, float] | None:
    """Pick the most recent non-null reading. Don't assume the API returns values
    pre-sorted — find the max by timestamp explicitly."""
    values = data.get("values")
    if not isinstance(values, list):
        raise GiosParseError(f"expected 'values' list, got: {type(values)!r}")

    readings: list[tuple[datetime, float]] = []
    for entry in values:
        if entry.get("value") is None:
            continue
        try:
            observed_at = datetime.strptime(entry["date"], "%Y-%m-%d %H:%M:%S")
            readings.append((observed_at, float(entry["value"])))
        except (KeyError, ValueError, TypeError) as exc:
            raise GiosParseError(f"malformed value entry {entry!r}: {exc}") from exc

    if not readings:
        return None
    return max(readings, key=lambda r: r[0])


def normalize(
    *,
    station: dict[str, Any],
    sensor: dict[str, Any],
    observed_at: datetime,
    value: float,
    fetched_at: datetime,
) -> dict[str, Any]:
    """Validate required fields are present and sane, then map to Measurement columns.
    Raises GiosParseError on anything missing/out of range — a bad station must not
    silently produce a wrong reading (rule #1: one broken source, isolated failure)."""
    try:
        station_id = str(station["id"])
        station_name = str(station["stationName"])
        latitude = float(station["gegrLat"])
        longitude = float(station["gegrLon"])
        sensor_id = str(sensor["id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise GiosParseError(f"malformed station/sensor payload: {exc}") from exc

    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise GiosParseError(f"station {station_id} has out-of-range coordinates")
    if value < 0:
        raise GiosParseError(f"sensor {sensor_id} has negative PM2.5 value: {value}")

    return {
        "source_id": "gios",
        "source_record_id": f"{sensor_id}:{observed_at.isoformat()}",
        "station_id": station_id,
        "station_name": station_name,
        "latitude": latitude,
        "longitude": longitude,
        "param_code": PM25_FORMULA,
        "value": value,
        "unit": PM25_UNIT,
        "observed_at": observed_at,
        "fetched_at": fetched_at,
    }
