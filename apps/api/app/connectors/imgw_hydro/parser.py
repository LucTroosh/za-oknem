"""Parse / validate / normalize raw IMGW hydro station records into
Measurement-ready dicts. Field names verified against a live response 2026-09-29
(see ADR-008) - Polish keys, values are strings (including lat/lon and the water
level itself), nulls used for missing readings.

stan_ostrzegawczy/stan_alarmowy (warning/alarm water-level thresholds) verified
live 2026-09-29 in the same payload as stan_wody - officially published per
station, not derived or guessed (rule #10: this is a numeric comparison against
IMGW's own published reference values, not an interpretation). Also verified
live: both can be null for a station (e.g. lake gauges with no defined
threshold) - not an error, just "no threshold for this station".
"""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

WATER_LEVEL_PARAM = "water_level_cm"
WARNING_LEVEL_PARAM = "water_level_warn_cm"
ALARM_LEVEL_PARAM = "water_level_alarm_cm"
WATER_LEVEL_UNIT = "cm"
# Not independently verified against a live cross-check with a known UTC offset
# event (unlike GIOŚ's live-verified Europe/Warsaw) - assumed on the strength of
# being the same institute publishing in the same convention. Revisit if a live
# comparison ever shows otherwise (ADR-008).
IMGW_TZ = ZoneInfo("Europe/Warsaw")


class ImgwHydroParseError(Exception):
    """Raised when a station record doesn't match the expected shape."""


def normalize(
    station: dict[str, Any], *, fetched_at: datetime
) -> list[dict[str, Any]] | None:
    """Returns 1-3 Measurement-ready dicts (water level, plus warning/alarm
    thresholds when the station has them defined), or None if this station has
    no current reading (stan_wody/stan_wody_data_pomiaru is null - common, not
    an error; rule #1 means skip it, don't fail the whole ingest run over one
    dry station)."""
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

    base = {
        "source_id": "imgw_hydro",
        "station_id": station_id,
        "station_name": station_name,
        "latitude": latitude,
        "longitude": longitude,
        "unit": WATER_LEVEL_UNIT,
        "observed_at": observed_at,
        "fetched_at": fetched_at,
    }

    def _record(param_code: str, param_value: float) -> dict[str, Any]:
        return {
            **base,
            "source_record_id": f"{station_id}:{param_code}:{observed_at.isoformat()}",
            "param_code": param_code,
            "value": param_value,
        }

    records = [_record(WATER_LEVEL_PARAM, value)]
    for param_code, raw_key in (
        (WARNING_LEVEL_PARAM, "stan_ostrzegawczy"),
        (ALARM_LEVEL_PARAM, "stan_alarmowy"),
    ):
        raw_threshold = station.get(raw_key)
        if raw_threshold is None:
            continue  # no threshold defined for this station - not an error
        try:
            threshold_value = float(raw_threshold)
        except (TypeError, ValueError) as exc:
            raise ImgwHydroParseError(
                f"station {station_id} has malformed {raw_key}: {exc}"
            ) from exc
        records.append(_record(param_code, threshold_value))
    return records
