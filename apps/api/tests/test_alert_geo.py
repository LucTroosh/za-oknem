"""ADR-013: pure alert -> area matching (rule #9). Boundary codes for woj/powiat/gmina."""

import pytest

from app.alert_geo import (
    VOIVODESHIP_TERYT,
    alert_voivodeship_codes,
    filter_alerts_for_area,
    match_alert,
    teryt_covers,
)


def test_voivodeship_table_is_the_16_official_terc_codes():
    assert sorted(VOIVODESHIP_TERYT.values()) == [f"{n:02d}" for n in range(2, 33, 2)]
    assert len(VOIVODESHIP_TERYT) == 16


@pytest.mark.parametrize(
    ("unit", "area", "expected"),
    [
        ("14", "1465011", True),  # woj prefix of a gmina
        ("1465", "1465011", True),  # powiat prefix
        ("1465011", "1465011", True),  # gmina == gmina
        ("1465012", "1465011", False),  # sibling gmina (other rodzaj digit)
        ("1466", "1465011", False),  # other powiat
        ("12", "1465011", False),  # other woj
        ("1", "1465011", False),  # not a TERYT level: never a loose prefix
        ("146", "1465011", False),
        ("14650", "1465011", False),
        ("", "1465011", False),
        ("14", "", False),
        ("1a", "1465011", False),
        ("14", "14x5011", False),
    ],
)
def test_teryt_covers_boundaries(unit, area, expected):
    assert teryt_covers(unit, area) is expected


def test_alert_codes_resolve_names_and_flag_the_rest():
    assert alert_voivodeship_codes([{"wojewodztwo": "łódzkie"}]) == ({"10"}, False)
    assert alert_voivodeship_codes([{"wojewodztwo": "łódzkie"}, {"opis": "x"}]) == ({"10"}, True)
    assert alert_voivodeship_codes([]) == (set(), True)
    assert alert_voivodeship_codes(None) == (set(), True)
    assert alert_voivodeship_codes(["lubelskie", 3, {"wojewodztwo": None}]) == (set(), True)


def test_match_alert_cases():
    woj = [{"wojewodztwo": "mazowieckie"}]
    assert match_alert(woj, "1465011") == "voivodeship"
    assert match_alert(woj, "3064011") is None
    assert match_alert(woj, None) == "unresolved"
    assert match_alert([], "1465011") == "unresolved"


def test_filter_is_idempotent_and_keeps_order_and_source_text():
    alerts = [
        {"external_id": "1", "areas": [{"wojewodztwo": "mazowieckie"}], "description": "oryginał"},
        {"external_id": "2", "areas": [{"wojewodztwo": "opolskie"}], "description": "inny"},
    ]
    once = filter_alerts_for_area(alerts, "1465011")
    assert [a["external_id"] for a in once] == ["1"]
    assert once[0]["description"] == "oryginał"  # rule #10: source text untouched
    assert filter_alerts_for_area(once, "1465011") == once
    assert "geo_match" not in alerts[0]  # input not mutated
