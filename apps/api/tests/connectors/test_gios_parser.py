"""Tests for the GIOŚ parser using a payload shaped per documented API schema.

NOT captured from a live response (see docs/data/source-registry.md — this sandbox
had no network route to api.gios.gov.pl). If the real API differs, these tests will
pass but production will fail loudly (parser raises GiosParseError, not silent wrong
data) — that failure is the signal to update this fixture, not evidence of a bug here.
"""

from datetime import datetime

import pytest

from app.connectors.gios.parser import (
    GIOS_TZ,
    GiosParseError,
    find_pm25_sensor,
    latest_value,
    normalize,
)

STATION = {
    "id": 114,
    "stationName": "Warszawa-Marszałkowska",
    "gegrLat": "52.223278",
    "gegrLon": "21.058628",
}

SENSORS = [
    {"id": 642, "stationId": 114, "param": {"paramFormula": "PM10", "paramCode": "PM10"}},
    {"id": 643, "stationId": 114, "param": {"paramFormula": "PM2.5", "paramCode": "PM2.5"}},
]

SENSOR_DATA = {
    "key": "PM2.5",
    "values": [
        {"date": "2026-09-28 14:00:00", "value": None},
        {"date": "2026-09-28 13:00:00", "value": 12.34},
        {"date": "2026-09-28 15:00:00", "value": 18.5},  # out of order on purpose
    ],
}


def test_find_pm25_sensor_picks_correct_one():
    sensor = find_pm25_sensor(SENSORS)
    assert sensor is not None
    assert sensor["id"] == 643


def test_find_pm25_sensor_returns_none_when_absent():
    assert find_pm25_sensor([SENSORS[0]]) is None


def test_latest_value_skips_nulls_and_picks_max_by_date():
    result = latest_value(SENSOR_DATA)
    assert result == (datetime(2026, 9, 28, 15, 0, 0, tzinfo=GIOS_TZ), 18.5)


def test_latest_value_returns_none_when_all_null():
    assert latest_value({"values": [{"date": "2026-09-28 14:00:00", "value": None}]}) is None


def test_normalize_maps_fields_correctly():
    sensor = find_pm25_sensor(SENSORS)
    observed_at = datetime(2026, 9, 28, 15, 0, 0, tzinfo=GIOS_TZ)
    record = normalize(
        station=STATION,
        sensor=sensor,
        observed_at=observed_at,
        value=18.5,
        fetched_at=datetime(2026, 9, 28, 15, 5, 0, tzinfo=GIOS_TZ),
    )
    assert record["station_id"] == "114"
    assert record["param_code"] == "PM2.5"
    assert record["value"] == 18.5
    assert record["source_record_id"] == f"643:{observed_at.isoformat()}"


def test_normalize_rejects_bad_coordinates():
    bad_station = {**STATION, "gegrLat": "200.0"}
    with pytest.raises(GiosParseError):
        normalize(
            station=bad_station,
            sensor=SENSORS[1],
            observed_at=datetime(2026, 9, 28, 15, 0, 0, tzinfo=GIOS_TZ),
            value=18.5,
            fetched_at=datetime(2026, 9, 28, 15, 5, 0, tzinfo=GIOS_TZ),
        )
