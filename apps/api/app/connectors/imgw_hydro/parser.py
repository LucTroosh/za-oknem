"""Parse / validate / normalize raw IMGW hydro station records into
Measurement-ready dicts. Field names verified against a live response 2026-09-29
(see ADR-008) - Polish keys, values are strings (including lat/lon and the water
level itself), nulls used for missing readings.
"""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

WATER_LEVEL_PARAM = "water_level_cm"
WATER_LEVEL_UNIT = "cm"
# Not independently verified against a live cross-check with a known UTC offset
# event (unlike GIOŚ's live-verified Europe/Warsaw) - assumed on the strength of
# being the same institute publishing in the same convention. Revisit if a live
# comparison ever shows otherwise (ADR-008).
IMGW_TZ = ZoneInfo("Europe/Warsaw")


class ImgwHydroParseError(Exception):
    """Raised when a station record doesn't match the expected shape."""


def normalize(station: dict[str, Any], *, fetched_at: datetime) -> dict[str, Any] | None:
    """Returns a Measurement-ready dict, or None if this station has no current
    reading (stan_wody/stan_wody_data_pomiaru is null - common, not an error;
    rule #1 means skip it, don't fail the whole ingest run over one dry station)."""
    if station.get("stan_wody") is None or station.get("stan_wody_data_pomiaru") is None:
        return None

    try:
        station_id = str(station["id_stacji"])
        station_name = f"{station['stacja']} ({station['rzeka']})"
        latitude = float(station["lat"])
        longitude = float(station["lon"])
        value = float(station["stan_wody"])
        observed_at = datetime.strptime(
            station["stan_wody_data_pomiaru"], "%Y-%m-%d %H:%M:%S"
        ).replace(tzinfo=IMGW_TZ)
    except (KeyError, TypeError, ValueError) as exc:
        raise ImgwHydroParseError(f"malformed station payload: {exc}") from exc

    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ImgwHydroParseError(f"station {station_id} has out-of-range coordinates")
    # No value < 0 rejection here (unlike GIOŚ's PM2.5 check) - unlike air quality,
    # a negative stan_wody is physically valid: it's measured relative to a local
    # gauge-zero reference ("rzędna zera wodowskazu"), and low-flow rivers do drop
    # below it. Rejecting negatives here would silently drop real, valid readings.

    return {
        "source_id": "imgw_hydro",
        "source_record_id": f"{station_id}:{observed_at.isoformat()}",
        "station_id": station_id,
        "station_name": station_name,
        "latitude": latitude,
        "longitude": longitude,
        "param_code": WATER_LEVEL_PARAM,
        "value": value,
        "unit": WATER_LEVEL_UNIT,
        "observed_at": observed_at,
        "fetched_at": fetched_at,
    }
