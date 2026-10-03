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

Thresholds are modeled differently from the water-level reading: stan_wody is a
genuine time series (a new observed_at each real reading, append-only, dedup by
source_record_id). A threshold is closer to slowly-changing reference config -
IMGW gives no "threshold last changed at" timestamp, and it can change or
disappear independently of whether the station has produced a new stan_wody
reading. Tying threshold currency to stan_wody's observed_at (an earlier version
of this file did) breaks for a stalled station: same observed_at reused forever
would make a removed/changed threshold look permanently "current". So each
threshold gets its own stable identity (station+param, no timestamp) and its
own clock (our fetched_at, not the source's stan_wody timestamp) - see
ingest.py's upsert/delete handling, which is the actual current-state gate.
"""

import math
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

WATER_LEVEL_PARAM = "water_level_cm"
WARNING_LEVEL_PARAM = "water_level_warn_cm"
ALARM_LEVEL_PARAM = "water_level_alarm_cm"
WATER_LEVEL_UNIT = "cm"
THRESHOLD_PARAMS = (WARNING_LEVEL_PARAM, ALARM_LEVEL_PARAM)
# Not independently verified against a live cross-check with a known UTC offset
# event (unlike GIOŚ's live-verified Europe/Warsaw) - assumed on the strength of
# being the same institute publishing in the same convention. Revisit if a live
# comparison ever shows otherwise (ADR-008).
IMGW_TZ = ZoneInfo("Europe/Warsaw")


# Stored with every raw fetch (ADR-014). Bump when parse/normalize output changes
# (including the set of requested fields), so old payloads stay interpretable.
PARSER_VERSION = "2"


class ImgwHydroParseError(Exception):
    """Raised when a station record doesn't match the expected shape."""


def normalize(station: dict[str, Any], *, fetched_at: datetime) -> dict[str, Any]:
    """Returns {"station_id", "station_name", "level": <insert-only Measurement
    dict, or None if this station has no current stan_wody reading - common,
    not an error>, "thresholds": {param_code: <upsert-ready Measurement dict
    with value=None meaning "not currently defined - delete any stored row">}}.

    Thresholds are parsed and returned regardless of whether stan_wody itself
    is present: a station that has temporarily stopped reporting its water
    level can still have its threshold change or get withdrawn, and that must
    still be reconciled (rule #1's isolation is about one BROKEN station, not
    about skipping unrelated fields just because one field is legitimately
    absent - Codex review, PR #42 round 4). Only a genuinely malformed station
    (bad id/name/coordinates) raises and is skipped entirely."""
    try:
        station_id = str(station["id_stacji"])
        station_name = f"{station['stacja']} ({station['rzeka']})"
        latitude = float(station["lat"])
        longitude = float(station["lon"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ImgwHydroParseError(f"malformed station payload: {exc}") from exc

    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ImgwHydroParseError(f"station {station_id} has out-of-range coordinates")

    level_record = None
    if station.get("stan_wody") is not None and station.get("stan_wody_data_pomiaru") is not None:
        try:
            value = float(station["stan_wody"])
            observed_at = datetime.strptime(
                station["stan_wody_data_pomiaru"], "%Y-%m-%d %H:%M:%S"
            ).replace(tzinfo=IMGW_TZ)
        except (TypeError, ValueError) as exc:
            raise ImgwHydroParseError(f"malformed station payload: {exc}") from exc
        if not math.isfinite(value):
            raise ImgwHydroParseError(f"station {station_id} has nonfinite stan_wody")
        # No value < 0 rejection here (unlike GIOŚ's PM2.5 check) - unlike air
        # quality, a negative stan_wody is physically valid: it's measured
        # relative to a local gauge-zero reference ("rzędna zera wodowskazu"),
        # and low-flow rivers do drop below it. Rejecting negatives here would
        # silently drop real, valid readings.
        level_record = {
            "source_id": "imgw_hydro",
            # Unchanged format from before thresholds existed (rule #40
            # idempotency) - a param_code segment isn't needed for uniqueness
            # (threshold ids use a completely different scheme, see _threshold
            # below) and would silently duplicate every already-stored reading
            # on first deploy of this change (Codex review, PR #42 round 4).
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

    def _threshold(param_code: str, raw_key: str) -> dict[str, Any]:
        # Stable identity (no timestamp) - ingest.py upserts/deletes this exact
        # row every run rather than inserting a new one each time.
        source_record_id = f"{station_id}:{param_code}"
        # A key that's PRESENT with value null is IMGW telling us "no threshold
        # for this station" - a real withdrawal, delete any stored row (see
        # test_normalize_marks_threshold_for_deletion_when_null). A key that's
        # MISSING entirely is a malformed/partial payload, not a withdrawal -
        # treating it the same would let one glitchy fetch silently erase every
        # threshold in the DB (Codex review, PR #42 round 5).
        if raw_key not in station:
            raise ImgwHydroParseError(f"station {station_id} is missing {raw_key}")
        raw_value = station[raw_key]
        if raw_value is None:
            return {"source_record_id": source_record_id, "value": None}
        try:
            threshold_value = float(raw_value)
        except (TypeError, ValueError) as exc:
            raise ImgwHydroParseError(
                f"station {station_id} has malformed {raw_key}: {exc}"
            ) from exc
        if not math.isfinite(threshold_value):
            raise ImgwHydroParseError(f"station {station_id} has nonfinite {raw_key}")
        return {
            "source_id": "imgw_hydro",
            "source_record_id": source_record_id,
            "station_id": station_id,
            "station_name": station_name,
            "latitude": latitude,
            "longitude": longitude,
            "param_code": param_code,
            "value": threshold_value,
            "unit": WATER_LEVEL_UNIT,
            "observed_at": fetched_at,  # our own clock, not stan_wody's - see module docstring
            "fetched_at": fetched_at,
        }

    return {
        "station_id": station_id,
        "station_name": station_name,
        "level": level_record,
        "thresholds": {
            WARNING_LEVEL_PARAM: _threshold(WARNING_LEVEL_PARAM, "stan_ostrzegawczy"),
            ALARM_LEVEL_PARAM: _threshold(ALARM_LEVEL_PARAM, "stan_alarmowy"),
        },
    }
