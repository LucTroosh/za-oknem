"""Tests for imgw_hydro.parser.normalize(): field mapping, null-reading skip,
and the deliberate absence of a negative-value rejection (unlike GIOŚ's PM2.5
check - stan_wody can legitimately be negative, see parser.py's comment)."""

from datetime import UTC, datetime

import pytest

from app.connectors.imgw_hydro.parser import (
    ALARM_LEVEL_PARAM,
    WARNING_LEVEL_PARAM,
    WATER_LEVEL_PARAM,
    ImgwHydroParseError,
    normalize,
)

STATION = {
    "id_stacji": "151140030",
    "stacja": "Przewoźniki",
    "rzeka": "Skroda",
    "lat": "51.5253",
    "lon": "14.8217",
    "stan_wody": "225",
    "stan_wody_data_pomiaru": "2026-09-27 21:20:00",
    "stan_ostrzegawczy": "300",
    "stan_alarmowy": "340",
}


def test_normalize_maps_level_fields_correctly():
    result = normalize(STATION, fetched_at=datetime.now(UTC))
    level = result["level"]

    assert level["source_id"] == "imgw_hydro"
    assert level["station_id"] == "151140030"
    assert level["station_name"] == "Przewoźniki (Skroda)"
    assert level["latitude"] == 51.5253
    assert level["longitude"] == 14.8217
    assert level["param_code"] == WATER_LEVEL_PARAM
    assert level["value"] == 225.0
    assert level["unit"] == "cm"


def test_normalize_level_source_record_id_format_is_stable():
    """Must stay exactly {station_id}:{observed_at} - already-stored rows use
    this format, and changing it duplicates every reading on next deploy
    instead of recognizing it as already seen (Codex review, PR #42 round 4:
    an earlier version added a param_code segment here, unnecessarily, since
    thresholds already have their own distinct id scheme)."""
    result = normalize(STATION, fetched_at=datetime.now(UTC))
    level = result["level"]

    assert level["source_record_id"] == f"151140030:{level['observed_at'].isoformat()}"


def test_normalize_includes_thresholds_when_defined():
    result = normalize(STATION, fetched_at=datetime.now(UTC))
    thresholds = result["thresholds"]

    assert thresholds[WARNING_LEVEL_PARAM]["value"] == 300.0
    assert thresholds[ALARM_LEVEL_PARAM]["value"] == 340.0
    # stable identity - no timestamp component, unlike the water-level record
    assert thresholds[WARNING_LEVEL_PARAM]["source_record_id"] == "151140030:water_level_warn_cm"


def test_normalize_thresholds_use_fetched_at_not_stan_wody_timestamp():
    """Thresholds have no timestamp of their own in the source - they're tied to
    our own fetch clock, decoupled from stan_wody's reading cycle (see module
    docstring; Codex review PR #42 round 3)."""
    fetched_at = datetime.now(UTC)
    result = normalize(STATION, fetched_at=fetched_at)

    assert result["thresholds"][WARNING_LEVEL_PARAM]["observed_at"] == fetched_at
    assert result["level"]["observed_at"] != fetched_at


def test_normalize_marks_threshold_for_deletion_when_null():
    """Confirmed live: some stations (e.g. lake gauges) have no defined
    warning/alarm threshold - null, not an error. value=None signals ingest.py
    to delete any previously stored row for it."""
    station = {**STATION, "stan_ostrzegawczy": None, "stan_alarmowy": None}
    result = normalize(station, fetched_at=datetime.now(UTC))

    assert result["thresholds"][WARNING_LEVEL_PARAM] == {
        "source_record_id": "151140030:water_level_warn_cm",
        "value": None,
    }
    assert result["thresholds"][ALARM_LEVEL_PARAM]["value"] is None


def test_normalize_raises_on_malformed_threshold():
    station = {**STATION, "stan_ostrzegawczy": "not-a-number"}
    with pytest.raises(ImgwHydroParseError):
        normalize(station, fetched_at=datetime.now(UTC))


def test_normalize_raises_when_threshold_key_is_missing_entirely():
    """A key present with value null is a real withdrawal (see
    test_normalize_marks_threshold_for_deletion_when_null); a key that's MISSING
    from the payload is a malformed/partial fetch, not a withdrawal - treating it
    the same would let one glitchy response silently erase every stored threshold
    (Codex review, PR #42 round 5)."""
    station = {k: v for k, v in STATION.items() if k != "stan_ostrzegawczy"}
    with pytest.raises(ImgwHydroParseError):
        normalize(station, fetched_at=datetime.now(UTC))


def test_param_codes_fit_the_varchar20_column():
    """Measurement.param_code is VARCHAR(20) (models.py) - SQLite doesn't enforce
    this, so it must be checked explicitly (Codex review, PR #42: PostgreSQL
    would reject water_level_warning_cm at 22 chars, silently after the
    water-level record for that station was already committed)."""
    for param_code in (WATER_LEVEL_PARAM, WARNING_LEVEL_PARAM, ALARM_LEVEL_PARAM):
        assert len(param_code) <= 20, param_code


def test_normalize_returns_no_level_when_no_current_reading():
    """level is None, but thresholds are still parsed and returned - a stalled
    station's threshold must still be reconciled (Codex review, PR #42 round 4:
    an earlier version returned None outright and skipped thresholds too)."""
    station = {**STATION, "stan_wody": None}
    result = normalize(station, fetched_at=datetime.now(UTC))

    assert result["level"] is None
    assert result["thresholds"][WARNING_LEVEL_PARAM]["value"] == 300.0


def test_normalize_returns_no_level_when_no_reading_timestamp():
    station = {**STATION, "stan_wody_data_pomiaru": None}
    result = normalize(station, fetched_at=datetime.now(UTC))

    assert result["level"] is None
    assert result["thresholds"][ALARM_LEVEL_PARAM]["value"] == 340.0


def test_normalize_accepts_negative_water_level():
    """Unlike PM2.5, a negative stan_wody is physically valid (below the local
    gauge-zero reference) - must not be rejected."""
    station = {**STATION, "stan_wody": "-5"}
    result = normalize(station, fetched_at=datetime.now(UTC))
    assert result["level"]["value"] == -5.0


def test_normalize_raises_on_missing_field():
    station = {k: v for k, v in STATION.items() if k != "lat"}
    with pytest.raises(ImgwHydroParseError):
        normalize(station, fetched_at=datetime.now(UTC))


def test_normalize_raises_on_out_of_range_coordinates():
    station = {**STATION, "lat": "999"}
    with pytest.raises(ImgwHydroParseError):
        normalize(station, fetched_at=datetime.now(UTC))


@pytest.mark.parametrize("key", ["stan_wody", "stan_ostrzegawczy", "stan_alarmowy"])
@pytest.mark.parametrize("value", ["nan", "inf", "-inf"])
def test_nonfinite_values_rejected(key, value):
    with pytest.raises(ImgwHydroParseError):
        normalize({**STATION, key: value}, fetched_at=datetime.now(UTC))
