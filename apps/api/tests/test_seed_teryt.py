"""Seed TERYT codes (migration 0016): the data, not the SQL (the SQL is exercised by the Postgres
migration job). Pure checks that keep the table honest and prove the point of the migration."""

import importlib.util
from pathlib import Path

from app.alert_geo import VOIVODESHIP_TERYT, match_alert

_MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations" / "versions"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, _MIGRATIONS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


m16 = _load("0016_seed_teryt_codes")
m03 = _load("0003_geo_areas")


def test_every_seed_city_has_a_code_and_nothing_else_does():
    seeded = {row["slug"] for row in m03._SEED_AREAS}
    assert set(m16.SEED_TERYT) == seeded


def test_codes_are_7_digit_gmina_codes_in_a_known_voivodeship():
    codes = list(m16.SEED_TERYT.values())
    assert len(set(codes)) == len(codes)  # UNIQUE constraint
    for code in codes:
        assert len(code) == 7 and code.isdigit()
        assert code[:2] in VOIVODESHIP_TERYT.values()


def test_each_seed_sits_in_its_expected_voivodeship():
    expected = {
        "klodzko": "dolnośląskie",
        "wroclaw": "dolnośląskie",
        "krakow": "małopolskie",
        "warszawa": "mazowieckie",
        "gdansk": "pomorskie",
        "poznan": "wielkopolskie",
        "lodz": "łódzkie",
    }
    for slug, voivodeship in expected.items():
        assert m16.SEED_TERYT[slug][:2] == VOIVODESHIP_TERYT[voivodeship], slug


def test_wroclaw_gets_dolnoslaskie_warnings_and_not_pomorskie_ones():
    wroclaw = m16.SEED_TERYT["wroclaw"]
    assert match_alert([{"wojewodztwo": "dolnośląskie"}], wroclaw) == "voivodeship"
    assert match_alert([{"wojewodztwo": "pomorskie"}], wroclaw) is None
    # an alert we cannot map stays visible and flagged (rule #10)
    assert match_alert([{"wojewodztwo": "???"}], wroclaw) == "unresolved"
    assert match_alert([], wroclaw) == "unresolved"
