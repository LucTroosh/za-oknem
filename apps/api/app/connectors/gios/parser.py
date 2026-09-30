"""Parse / validate / normalize raw GIOŚ JSON into Measurement-ready dicts.

Field names below were verified against a LIVE response 2026-09-28 (see
docs/data/source-registry.md) — the real API is JSON-LD with Polish keys, not the
English camelCase shape this file originally (wrongly) assumed before we had network
access to test it against the live service.
"""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

# TASK-4.1: full MVP parameter set (Master Plan §4), not just the PM2.5 vertical
# slice (§108). Units are metadata we supply, not read off the API response — per
# GIOŚ's own API docs (https://powietrze.gios.gov.pl/pjp/content/api), ALL params
# incl. CO are returned in µg/m³ through the API; GIOŚ's mg/m³ CO convention only
# applies to their map/mobile-app display, not this API. Codex review caught this
# (originally mislabeled CO as mg/m³, a 1000x display error) — verified against
# the live docs, not guessed.
PM25_FORMULA = "PM2.5"  # kept for backwards-compat call sites/tests
PARAM_UNITS: dict[str, str] = {
    "PM2.5": "µg/m³",
    "PM10": "µg/m³",
    "NO2": "µg/m³",
    "SO2": "µg/m³",
    "O3": "µg/m³",
    "CO": "µg/m³",
    "C6H6": "µg/m³",
}
PM25_UNIT = PARAM_UNITS[PM25_FORMULA]
# GIOŚ timestamps are naive local Polish time, not UTC — converting them to UTC-aware
# datetimes here (instead of leaving them naive, or wrongly treating them as UTC) is
# what makes the freshness comparison in app/api/v1/air.py correct.
GIOS_TZ = ZoneInfo("Europe/Warsaw")


class GiosParseError(Exception):
    """Raised when a GIOŚ payload doesn't match the expected shape."""


def find_sensor(sensors: list[dict[str, Any]], formula: str) -> dict[str, Any] | None:
    """Find the sensor for one param code (GIOŚ 'Wskaźnik - wzór', e.g. 'PM2.5', 'NO2')."""
    for sensor in sensors:
        if sensor.get("Wskaźnik - wzór") == formula:
            return sensor
    return None


def find_pm25_sensor(sensors: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Backwards-compat wrapper — prefer find_sensor(sensors, formula) for new code."""
    return find_sensor(sensors, PM25_FORMULA)


def latest_value(data: dict[str, Any]) -> tuple[datetime, float] | None:
    """Pick the most recent non-null reading. Don't assume the API returns values
    pre-sorted — find the max by timestamp explicitly."""
    values = data.get("Lista danych pomiarowych")
    if not isinstance(values, list):
        raise GiosParseError(f"expected 'Lista danych pomiarowych' list, got: {type(values)!r}")

    readings: list[tuple[datetime, float]] = []
    for entry in values:
        if entry.get("Wartość") is None:
            continue
        try:
            observed_at = datetime.strptime(entry["Data"], "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=GIOS_TZ
            )
            readings.append((observed_at, float(entry["Wartość"])))
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
        station_id = str(station["Identyfikator stacji"])
        station_name = str(station["Nazwa stacji"])
        latitude = float(station["WGS84 φ N"])
        longitude = float(station["WGS84 λ E"])
        sensor_id = str(sensor["Identyfikator stanowiska"])
        param_code = str(sensor["Wskaźnik - wzór"])
    except (KeyError, TypeError, ValueError) as exc:
        raise GiosParseError(f"malformed station/sensor payload: {exc}") from exc

    try:
        unit = PARAM_UNITS[param_code]
    except KeyError as exc:
        raise GiosParseError(f"sensor {sensor_id}: unknown param code {param_code!r}") from exc

    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise GiosParseError(f"station {station_id} has out-of-range coordinates")
    if value < 0:
        raise GiosParseError(f"sensor {sensor_id} ({param_code}) has negative value: {value}")

    return {
        "source_id": "gios",
        "source_record_id": f"{sensor_id}:{observed_at.isoformat()}",
        "station_id": station_id,
        "station_name": station_name,
        "latitude": latitude,
        "longitude": longitude,
        "param_code": param_code,
        "value": value,
        "unit": unit,
        "observed_at": observed_at,
        "fetched_at": fetched_at,
    }
