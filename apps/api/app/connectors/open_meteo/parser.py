"""Parse / validate / normalize raw Open-Meteo JSON into WeatherSnapshot-ready dicts.

Shape per official docs (open-meteo.com/en/docs), NOT confirmed against a live
sample in this sandbox (see client.py / source-registry.md). Fails loudly on any
unexpected shape rather than guessing (same lesson as the GIOŚ connector).
"""

from datetime import UTC, datetime
from typing import Any

from app.connectors.open_meteo.client import CURRENT_PARAMS

PARAM_CODES = CURRENT_PARAMS.split(",")


class OpenMeteoParseError(Exception):
    """Raised when an Open-Meteo payload doesn't match the expected shape."""


def normalize(
    *,
    geo_area_id: int,
    payload: dict[str, Any],
    fetched_at: datetime,
) -> list[dict[str, Any]]:
    """One WeatherSnapshot-ready dict per requested current-weather param.
    Raises OpenMeteoParseError on anything missing (rule #1: a bad payload for one
    geo_area must not silently produce wrong readings or crash the whole ingest run
    — ingest.py is what isolates that failure per geo_area, this just refuses to
    guess)."""
    try:
        current = payload["current"]
        units = payload["current_units"]
        # timezone=UTC was requested explicitly in client.py, so this naive
        # timestamp IS UTC wall-clock time.
        observed_at = datetime.fromisoformat(current["time"]).replace(tzinfo=UTC)
    except (KeyError, TypeError, ValueError) as exc:
        raise OpenMeteoParseError(f"malformed current-weather payload: {exc}") from exc

    snapshots = []
    for param_code in PARAM_CODES:
        try:
            value = float(current[param_code])
            unit = str(units[param_code])
        except (KeyError, TypeError, ValueError) as exc:
            raise OpenMeteoParseError(f"missing/invalid param {param_code!r}: {exc}") from exc

        snapshots.append(
            {
                "source_id": "open_meteo",
                "source_record_id": f"{geo_area_id}:{param_code}:{observed_at.isoformat()}",
                "geo_area_id": geo_area_id,
                "param_code": param_code,
                "value": value,
                "unit": unit,
                "observed_at": observed_at,
                "fetched_at": fetched_at,
            }
        )
    return snapshots
