"""GIOŚ noise parser (ADR-032, GIOS-04); accepted record = the live one from halas-second.json."""

from datetime import date

import pytest

from app.connectors.gios_noise import parser as p

LIVE = {
    "kodPunktuPomiarowego": "D_24_001020_001",
    "kategoria": "Droga",
    "wojewodztwo": "ŚLĄSKIE",
    "powiat": "tarnogórski",
    "gmina": "Miasteczko Śląskie (gmina miejska)",
    "miejscowosc": "Żyglin",
    "coordWgs84X": 18.948417,
    "coordWgs84Y": 50.484861,
    "pora": "Dzień 16h",
    "celPomiaru": "Państwowy monitoring środowiska, art. 26 Poś",
    "dataOd": "2024-05-10T08:00:00.000+02:00",
    "dataDo": "2024-11-10T07:00:00.000+01:00",
    "wynikPomiaru": 64.5,
    "przekroczenie": 0,
}


def reject(**changes):
    with pytest.raises(p.RecordRejected) as exc:
        p.normalize({**LIVE, **changes})
    return exc.value.reason


def test_the_live_record_is_accepted_with_the_verified_coordinate_order():
    r = p.normalize(LIVE)
    assert (r.point_code, r.category, r.voivodeship, r.locality) == (
        "D_24_001020_001",
        "Droga",
        "ŚLĄSKIE",
        "Żyglin",
    )
    assert (r.latitude, r.longitude) == (50.484861, 18.948417)  # Y = latitude, X = longitude
    assert (r.period_label, r.value_db, r.exceedance_db) == ("Dzień 16h", 64.5, 0.0)
    assert (r.date_from, r.date_to) == (date(2024, 5, 10), date(2024, 11, 10))  # the days as stated
    assert r.purpose == "Państwowy monitoring środowiska, art. 26 Poś"


def test_missing_exceedance_is_none_not_zero():
    assert p.normalize({**LIVE, "przekroczenie": None}).exceedance_db is None
    raw = {k: v for k, v in LIVE.items() if k != "przekroczenie"}
    assert p.normalize(raw).exceedance_db is None


def test_optional_text_fields_may_be_absent():
    raw = {
        k: v for k, v in LIVE.items() if k not in ("powiat", "gmina", "miejscowosc", "celPomiaru")
    }
    r = p.normalize(raw)
    assert (r.powiat, r.gmina, r.locality, r.purpose) == (None, None, None, None)


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"kodPunktuPomiarowego": None}, "missing_point_code"),
        ({"kodPunktuPomiarowego": "  "}, "missing_point_code"),
        ({"kategoria": "Metro"}, "unknown_category"),
        (
            {"wojewodztwo": "śląskie"},
            "unknown_voivodeship",
        ),  # lowercase: not the enum the API wants
        ({"coordWgs84X": None}, "bad_coordinates"),
        ({"coordWgs84Y": "50.48"}, "bad_coordinates"),
        ({"coordWgs84X": True}, "bad_coordinates"),
        ({"coordWgs84X": float("nan")}, "bad_coordinates"),
        ({"coordWgs84X": 50.484861, "coordWgs84Y": 18.948417}, "coords_swapped"),
        ({"coordWgs84X": 185897.4, "coordWgs84Y": 678640.9}, "coords_outside_poland"),  # projected
        ({"coordWgs84X": 2.35, "coordWgs84Y": 48.85}, "coords_outside_poland"),  # Paris
        ({"wynikPomiaru": "64,5"}, "value_not_number"),  # a string is never read as a number
        ({"wynikPomiaru": None}, "value_missing"),  # the source gave no result for this slot
        ({"wynikPomiaru": False}, "value_not_number"),
        ({"przekroczenie": "TAK"}, "exceedance_not_number"),
        ({"pora": None}, "missing_period_of_day"),
        ({"pora": " "}, "missing_period_of_day"),
        ({"dataOd": "10.05.2024"}, "bad_date"),
        ({"dataDo": "2024-13-40T00:00:00"}, "bad_date"),
        ({"dataOd": None}, "bad_date"),
        ({"dataOd": "2024-12-01", "dataDo": "2024-01-01"}, "date_order"),
    ],
)
def test_records_that_do_not_fit_are_rejected_with_a_reason(changes, reason):
    assert reject(**changes) == reason


def test_natural_key_is_stable_and_distinguishes_measurements_of_one_point():
    base = p.natural_key(LIVE)
    assert base == p.natural_key(dict(LIVE))
    assert base != p.natural_key({**LIVE, "pora": "Noc 8h"})  # day vs night at the same point
    assert base != p.natural_key({**LIVE, "dataOd": "2023-05-10T08:00:00.000+02:00"})
    assert base != p.natural_key({**LIVE, "wynikPomiaru": 64.6})
    assert len(base) == 64


def test_every_voivodeship_the_api_accepts_is_listed_in_capitals():
    assert len(p.VOIVODESHIPS) == 16 and all(v == v.upper() for v in p.VOIVODESHIPS)
    assert set(p.CATEGORIES) == {"Droga", "Lotnisko", "Przemysł", "Kolej"}
