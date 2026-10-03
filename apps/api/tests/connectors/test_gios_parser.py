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
    all_values,
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


def _data(*entries):
    return {"Lista danych pomiarowych": [{"Data": d, "Wartość": v} for d, v in entries]}


def test_all_values_returns_every_non_null_reading_oldest_first():
    # the API lists newest first; null hours are skipped, not turned into zeros
    data = _data(
        ("2026-09-28 19:00:00", 7.0),
        ("2026-09-28 18:00:00", None),
        ("2026-09-28 17:00:00", 6.8),
    )
    assert [(t.hour, v) for t, v in all_values(data)] == [(17, 6.8), (19, 7.0)]


def test_all_values_of_an_empty_or_all_null_payload_is_empty():
    assert all_values({"Lista danych pomiarowych": []}) == []
    assert all_values(_data(("2026-09-28 14:00:00", None))) == []


def test_all_values_rejects_a_changed_shape():
    with pytest.raises(GiosParseError):
        all_values({"unexpected": "shape"})
    with pytest.raises(GiosParseError):
        all_values(_data(("not a date", 5.0)))
    with pytest.raises(GiosParseError):
        all_values(_data(("2026-09-28 14:00:00", "abc")))


def _utc_hours(readings):
    from datetime import UTC

    return [(t.astimezone(UTC).strftime("%d %H:%M"), v) for t, v in readings]


def test_the_hour_the_clocks_go_back_is_two_different_instants_newest_first():
    # 2026-10-25: 03:00 CEST -> 02:00 CET, so local 02:00 happens twice. Newest first: the first
    # 02:00 is the later one (CET = 01:00 UTC), the second the earlier (CEST = 00:00 UTC).
    data = _data(
        ("2026-10-25 03:00:00", 4.0),
        ("2026-10-25 02:00:00", 3.0),
        ("2026-10-25 02:00:00", 2.0),
        ("2026-10-25 01:00:00", 1.0),
    )
    assert _utc_hours(all_values(data)) == [
        ("24 23:00", 1.0),
        ("25 00:00", 2.0),
        ("25 01:00", 3.0),
        ("25 02:00", 4.0),
    ]


def test_the_same_hour_read_from_an_oldest_first_list_gives_the_same_instants():
    data = _data(
        ("2026-10-25 01:00:00", 1.0),
        ("2026-10-25 02:00:00", 2.0),
        ("2026-10-25 02:00:00", 3.0),
        ("2026-10-25 03:00:00", 4.0),
    )
    assert _utc_hours(all_values(data)) == [
        ("24 23:00", 1.0),
        ("25 00:00", 2.0),
        ("25 01:00", 3.0),
        ("25 02:00", 4.0),
    ]


def test_a_null_twin_keeps_the_other_copy_on_the_right_side_of_the_change():
    data = _data(
        ("2026-10-25 03:00:00", 4.0),
        ("2026-10-25 02:00:00", 3.0),
        ("2026-10-25 02:00:00", None),
    )
    assert _utc_hours(all_values(data)) == [("25 01:00", 3.0), ("25 02:00", 4.0)]


def test_a_lone_ambiguous_hour_is_read_as_before_summer_time():
    # its twin is missing: nothing in the payload says which one it is; unchanged old behaviour
    assert _utc_hours(all_values(_data(("2026-10-25 02:00:00", 2.0)))) == [("25 00:00", 2.0)]


def test_source_record_ids_for_ordinary_hours_keep_their_old_format():
    ((t, _v),) = all_values(_data(("2026-09-28 18:00:00", 8.2)))
    assert t.isoformat() == "2026-09-28T18:00:00+02:00"
