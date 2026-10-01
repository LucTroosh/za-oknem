"""TASK-4.2 / ADR-015: EAQI (EEA) from GIOŚ measurements. Pure tests, no pytest
features (loops, no parametrize) so a bare `python3` loop can run them too."""

from datetime import UTC, datetime, timedelta

from app.air_index import BANDS, UNIT, Level, air_index, level_for

RECENT = timedelta(hours=6)
NOW = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)

# EEA table, transcribed 2026-09-30 from airindex.eea.europa.eu (upper edges of the first
# five bands). Duplicated on purpose: a typo in BANDS must fail here.
EEA = {
    "PM2.5": (5, 15, 50, 90, 140),
    "PM10": (15, 45, 120, 195, 270),
    "NO2": (10, 25, 60, 100, 150),
    "O3": (60, 100, 120, 160, 180),
    "SO2": (20, 40, 125, 190, 275),
}
GOOD = {"PM2.5": 3, "PM10": 10, "NO2": 5, "O3": 40, "SO2": 10}


def _p(value, unit=UNIT, freshness="FRESH", age_h=0.5):
    return {
        "value": value,
        "unit": unit,
        "freshness": freshness,
        "observed_at": (NOW - timedelta(hours=age_h)).isoformat(),
    }


def _params(**over):
    base = {k: _p(v) for k, v in GOOD.items()}
    for k, v in over.items():
        code = k.replace("PM25", "PM2.5")
        if v is None:
            base.pop(code, None)
        else:
            base[code] = v if isinstance(v, dict) else _p(v)
    return base


def test_bands_match_eea_table():
    assert BANDS == EEA


def test_boundaries_every_pollutant_below_at_above():
    for code, edges in EEA.items():
        for i, edge in enumerate(edges):
            assert level_for(code, edge - 0.01) == Level(i), (code, edge)
            assert level_for(code, edge) == Level(i), (code, edge)  # right-closed
            assert level_for(code, edge + 0.01) == Level(i + 1), (code, edge)
        assert level_for(code, edges[-1] + 1000) == Level.EXTREMELY_POOR
        assert level_for(code, 0) == Level.GOOD


def test_monotonic_per_pollutant():
    for code in EEA:
        prev = Level.GOOD
        for tenth in range(0, 4000):
            lv = level_for(code, tenth / 10)
            assert lv >= prev
            prev = lv


def test_overall_is_worst_and_dominant_listed():
    r = air_index(_params(PM10=130, SO2=30), RECENT)  # PM10 130 -> Poor, SO2 30 -> Fair
    assert r["level"] == "POOR" and r["complete"] is True
    assert r["dominant"] == ["PM10"]
    assert r["params"]["SO2"] == "FAIR" and r["params"]["PM2.5"] == "GOOD"
    assert r["missing"] == {}


def test_good_when_complete_and_all_good():
    r = air_index(_params(), RECENT)
    assert r["level"] == "GOOD" and r["complete"] is True
    assert set(r["dominant"]) == set(GOOD)


def test_one_pm_is_enough_but_absence_is_reported():
    r = air_index(_params(PM10=None), RECENT)
    assert r["level"] == "GOOD" and r["complete"] is True
    assert r["missing"] == {"PM10": "MISSING"}
    r = air_index(_params(PM25=None), RECENT)
    assert r["complete"] is True and r["missing"] == {"PM2.5": "MISSING"}


def test_no_index_when_minimum_set_missing_and_result_good_or_fair():
    for gone in ("NO2", "O3"):
        r = air_index(_params(**{gone: None}), RECENT)
        assert r["level"] is None and r["complete"] is False, gone
        assert r["missing"] == {gone: "MISSING"} and r["dominant"] == []
        assert r["valid_until"] is None
    r = air_index(_params(PM10=None, PM25=None), RECENT)
    assert r["level"] is None
    assert set(r["missing"]) == {"PM2.5", "PM10"}
    # Fair is still not enough to claim an index without the full set.
    assert air_index(_params(O3=None, SO2=30), RECENT)["level"] is None


def test_bad_news_stands_as_lower_bound_when_incomplete():
    r = air_index(_params(O3=None, PM10=130), RECENT)
    assert r["level"] == "POOR" and r["complete"] is False
    assert r["dominant"] == ["PM10"]


def test_stale_input_is_missing_not_used():
    r = air_index(_params(PM10=_p(300, freshness="STALE")), RECENT)
    assert r["missing"] == {"PM10": "STALE"}
    # PM2.5 still covers PM; the stale 300 is ignored
    assert r["level"] == "GOOD" and r["complete"] is True
    r = air_index(_params(NO2=_p(5, freshness="STALE")), RECENT)
    assert r["level"] is None and r["missing"]["NO2"] == "STALE"
    # UNAVAILABLE or any other label is unusable too.
    assert air_index(_params(NO2=_p(5, freshness="UNAVAILABLE")), RECENT)["level"] is None


def test_wrong_unit_dropped_not_converted():
    r = air_index(_params(NO2=_p(0.005, unit="mg/m³")), RECENT)
    assert r["level"] is None and r["missing"]["NO2"] == "UNIT"


def test_invalid_values_dropped():
    for bad in (float("nan"), float("inf"), -1.0, True, None, "5"):
        r = air_index(_params(NO2=_p(bad)), RECENT)
        assert r["level"] is None and r["missing"]["NO2"] == "INVALID", bad


def test_co_and_benzene_ignored():
    p = _params()
    p["CO"] = _p(9_999_999)
    p["C6H6"] = _p(9_999)
    r = air_index(p, RECENT)
    assert r["level"] == "GOOD" and "CO" not in r["params"] and "C6H6" not in r["missing"]


def test_empty_params():
    r = air_index({}, RECENT)
    assert r["level"] is None and r["complete"] is False and r["valid_until"] is None
    assert set(r["missing"]) == set(BANDS) and r["params"] == {}


def test_valid_until_is_earliest_contributing_expiry():
    p = _params(PM10=_p(10, age_h=5))  # oldest input: expires 1 h after NOW
    r = air_index(p, RECENT)
    assert r["valid_until"] == (NOW - timedelta(hours=5) + RECENT).isoformat()


def test_worsening_one_input_never_improves_overall():
    order = {None: -1, **{lv.name: lv.value for lv in Level}}
    grid = (0, 4, 5, 6, 40, 100, 400)
    for code in EEA:
        for base in (None, *grid):
            prev = None
            for v in grid:
                p = _params(**{code.replace("PM2.5", "PM25"): v})
                if base is not None:
                    p["SO2"] = _p(base)
                cur = order[air_index(p, RECENT)["level"]]
                if prev is not None:
                    assert cur >= prev, (code, base, v)
                prev = cur


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("ok")
