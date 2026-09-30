"""Tests for the GIOŚ parser using a payload shaped per a LIVE response.

Captured 2026-09-28 against api.gios.gov.pl (station 38 "Kłodzko, ul. Szkolna",
sensor 25988, PM2.5) — see docs/data/source-registry.md. Field names are the real
Polish JSON-LD keys, not a guess.
"""

from datetime import datetime

import pytest

from app.connectors.gios.parser import (
    GIOS_TZ,
    GiosParseError,
    find_pm25_sensor,
    find_sensor,
    latest_value,
    normalize,
)

STATION = {
    "Identyfikator stacji": 38,
    "Kod stacji": "DsKlodzSzkol",
    "Nazwa stacji": "Kłodzko, ul. Szkolna",
    "WGS84 φ N": "50.433493",
    "WGS84 λ E": "16.653660",
    "Identyfikator miasta": 368,
    "Nazwa miasta": "Kłodzko",
    "Gmina": "Kłodzko",
    "Powiat": "kłodzki",
    "Województwo": "DOLNOŚLĄSKIE",
    "Ulica": "ul. Szkolna 8",
}

SENSORS = [
    {
        "Identyfikator stanowiska": 25987,
        "Identyfikator stacji": 38,
        "Wskaźnik": "pył zawieszony PM10",
        "Wskaźnik - wzór": "PM10",
        "Wskaźnik - kod": "PM10",
        "Id wskaźnika": 3,
    },
    {
        "Identyfikator stanowiska": 25988,
        "Identyfikator stacji": 38,
        "Wskaźnik": "pył zawieszony PM2.5",
        "Wskaźnik - wzór": "PM2.5",
        "Wskaźnik - kod": "PM2.5",
        "Id wskaźnika": 69,
    },
]

SENSOR_DATA = {
    "Lista danych pomiarowych": [
        {"Kod stanowiska": "DsKlodzSzkol-PM2.5-1g", "Data": "2026-09-28 19:00:00", "Wartość": None},
        {"Kod stanowiska": "DsKlodzSzkol-PM2.5-1g", "Data": "2026-09-28 17:00:00", "Wartość": 6.8},
        # out of order on purpose — real data is descending, but the parser must not
        # assume that
        {"Kod stanowiska": "DsKlodzSzkol-PM2.5-1g", "Data": "2026-09-28 18:00:00", "Wartość": 8.2},
    ]
}


def test_find_pm25_sensor_picks_correct_one():
    sensor = find_pm25_sensor(SENSORS)
    assert sensor is not None
    assert sensor["Identyfikator stanowiska"] == 25988


def test_find_pm25_sensor_returns_none_when_absent():
    assert find_pm25_sensor([SENSORS[0]]) is None


def test_find_sensor_picks_by_formula():
    sensor = find_sensor(SENSORS, "PM10")
    assert sensor is not None
    assert sensor["Identyfikator stanowiska"] == 25987


def test_find_sensor_returns_none_when_absent():
    assert find_sensor(SENSORS, "NO2") is None


def test_latest_value_skips_nulls_and_picks_max_by_date():
    result = latest_value(SENSOR_DATA)
    assert result == (datetime(2026, 9, 28, 18, 0, 0, tzinfo=GIOS_TZ), 8.2)


def test_latest_value_returns_none_when_all_null():
    data = {"Lista danych pomiarowych": [{"Data": "2026-09-28 14:00:00", "Wartość": None}]}
    assert latest_value(data) is None


def test_normalize_maps_fields_correctly():
    sensor = find_pm25_sensor(SENSORS)
    observed_at = datetime(2026, 9, 28, 18, 0, 0, tzinfo=GIOS_TZ)
    record = normalize(
        station=STATION,
        sensor=sensor,
        observed_at=observed_at,
        value=8.2,
        fetched_at=datetime(2026, 9, 28, 18, 5, 0, tzinfo=GIOS_TZ),
    )
    assert record["station_id"] == "38"
    assert record["station_name"] == "Kłodzko, ul. Szkolna"
    assert record["param_code"] == "PM2.5"
    assert record["value"] == 8.2
    assert record["source_record_id"] == f"25988:{observed_at.isoformat()}"


def test_normalize_rejects_bad_coordinates():
    bad_station = {**STATION, "WGS84 φ N": "200.0"}
    with pytest.raises(GiosParseError):
        normalize(
            station=bad_station,
            sensor=SENSORS[1],
            observed_at=datetime(2026, 9, 28, 18, 0, 0, tzinfo=GIOS_TZ),
            value=8.2,
            fetched_at=datetime(2026, 9, 28, 18, 5, 0, tzinfo=GIOS_TZ),
        )


def test_normalize_uses_param_specific_unit():
    sensor = find_sensor(SENSORS, "PM10")
    record = normalize(
        station=STATION,
        sensor=sensor,
        observed_at=datetime(2026, 9, 28, 18, 0, 0, tzinfo=GIOS_TZ),
        value=15.0,
        fetched_at=datetime(2026, 9, 28, 18, 5, 0, tzinfo=GIOS_TZ),
    )
    assert record["param_code"] == "PM10"
    assert record["unit"] == "µg/m³"


def test_normalize_keeps_co_in_micrograms():
    # Codex review: GIOŚ's API docs (powietrze.gios.gov.pl/pjp/content/api) state
    # ALL params incl. CO are returned in µg/m³ — the mg/m³ convention is only for
    # GIOŚ's own map/app display, not this API. Mislabeling this as mg/m³ was a
    # 1000x display error.
    record = normalize(
        station=STATION,
        sensor={"Identyfikator stanowiska": 1, "Wskaźnik - wzór": "CO"},
        observed_at=datetime(2026, 9, 28, 18, 0, 0, tzinfo=GIOS_TZ),
        value=350.0,
        fetched_at=datetime(2026, 9, 28, 18, 5, 0, tzinfo=GIOS_TZ),
    )
    assert record["unit"] == "µg/m³"
    assert record["value"] == 350.0


def test_normalize_rejects_unknown_param_code():
    unknown_sensor = {"Identyfikator stanowiska": 999, "Wskaźnik - wzór": "XYZ"}
    with pytest.raises(GiosParseError):
        normalize(
            station=STATION,
            sensor=unknown_sensor,
            observed_at=datetime(2026, 9, 28, 18, 0, 0, tzinfo=GIOS_TZ),
            value=1.0,
            fetched_at=datetime(2026, 9, 28, 18, 5, 0, tzinfo=GIOS_TZ),
        )
