"""TASK-7.6 / ADR-016: Outdoor Interpretation Engine.

Pure-function tests, no DB/fixtures. No pytest.mark.parametrize on purpose: loops
keep this file runnable by a bare `python3` loop too (sandbox without PyPI).
"""

import itertools
import math
from dataclasses import fields, replace

from app.outdoor import (
    RULES,
    SEVERITY,
    OutdoorInputs,
    Rating,
    Reading,
    evaluate,
)

# Everything present and comfortable.
GOOD_VALUES = {
    "temperature_2m": 15.0,
    "apparent_temperature": 14.0,
    "precipitation": 0.0,
    "wind_speed_10m": 10.0,
    "wind_gusts_10m": 20.0,
    "uv_index": 2.0,
    "visibility": 20000.0,
    "pm25": 8.0,
    "pm10": 20.0,
}


def make(**overrides) -> OutdoorInputs:
    values = {**GOOD_VALUES, **overrides}
    return OutdoorInputs(**{k: None if v is None else Reading(v) for k, v in values.items()})


def codes(result):
    return [(r.code, r.param, r.level) for r in result.reasons]


def test_all_good():
    result = evaluate(make())
    assert result.rating is Rating.GOOD
    assert result.reasons == ()
    assert result.missing == ()


def test_threshold_boundaries_just_below_at_and_above():
    """Generic check over the whole rule table: each edge flips exactly where the
    rule's comparison says, and never earlier."""
    eps = 1e-6
    for rule in RULES:
        sign = 1 if rule.comparison in ("gt", "gte") else -1  # worsening direction
        inclusive = rule.comparison in ("gte", "lte")

        def own_level(value, rule=rule):
            res = evaluate(make(**{rule.param: value}))
            hit = [r.level for r in res.reasons if r.code == rule.code and r.param == rule.param]
            return hit[0] if hit else None

        for edge, level, below in (
            (rule.moderate, Rating.MODERATE, None),
            (rule.poor, Rating.POOR, Rating.MODERATE),
        ):
            assert own_level(edge - sign * eps) == below, (rule.code, rule.param, edge)
            assert own_level(edge + sign * eps) == level, (rule.code, rule.param, edge)
            assert (own_level(edge) == level) is inclusive or own_level(edge) == below


def test_exact_edges_inclusive_vs_exclusive():
    # PM uses strict ">" (EEA integer bands, continuous values): 15.0 is still GOOD.
    assert evaluate(make(pm25=15.0)).rating is Rating.GOOD
    assert evaluate(make(pm25=15.1)).rating is Rating.MODERATE
    assert evaluate(make(pm25=50.0)).rating is Rating.MODERATE
    assert evaluate(make(pm25=50.1)).rating is Rating.POOR
    assert evaluate(make(pm10=45.0)).rating is Rating.GOOD
    assert evaluate(make(pm10=45.1)).rating is Rating.MODERATE
    assert evaluate(make(pm10=120.0)).rating is Rating.MODERATE
    assert evaluate(make(pm10=120.1)).rating is Rating.POOR
    # UV: Beaufort/WHO edges are inclusive lower bounds.
    assert evaluate(make(uv_index=5.9)).rating is Rating.GOOD
    assert evaluate(make(uv_index=6.0)).rating is Rating.MODERATE
    assert evaluate(make(uv_index=8.0)).rating is Rating.POOR
    assert evaluate(make(wind_speed_10m=28.9)).rating is Rating.GOOD
    assert evaluate(make(wind_speed_10m=29.0)).rating is Rating.MODERATE
    assert evaluate(make(wind_speed_10m=39.0)).rating is Rating.POOR
    # Visibility: lower is worse, strict "<".
    assert evaluate(make(visibility=5000.0)).rating is Rating.GOOD
    assert evaluate(make(visibility=4999.0)).rating is Rating.MODERATE
    assert evaluate(make(visibility=1000.0)).rating is Rating.MODERATE
    assert evaluate(make(visibility=999.0)).rating is Rating.POOR
    # Two-sided temperature.
    assert evaluate(make(apparent_temperature=26.9)).rating is Rating.GOOD
    assert evaluate(make(apparent_temperature=27.0)).rating is Rating.MODERATE
    assert evaluate(make(apparent_temperature=32.0)).rating is Rating.POOR
    assert evaluate(make(apparent_temperature=0.1)).rating is Rating.GOOD
    assert evaluate(make(apparent_temperature=0.0)).rating is Rating.MODERATE
    assert evaluate(make(apparent_temperature=-10.0)).rating is Rating.POOR
    # Any measurable rain is not GOOD.
    assert evaluate(make(precipitation=0.0)).rating is Rating.GOOD
    assert evaluate(make(precipitation=0.1)).rating is Rating.MODERATE
    assert evaluate(make(precipitation=2.5)).rating is Rating.POOR


def test_worst_factor_wins_and_reason_has_full_payload():
    result = evaluate(make(pm25=20.0, wind_speed_10m=45.0, uv_index=6.5))
    assert result.rating is Rating.POOR
    wind = result.reasons[0]
    assert (wind.code, wind.param, wind.value, wind.threshold) == (
        "WIND_STRONG",
        "wind_speed_10m",
        45.0,
        39.0,
    )
    assert (wind.comparison, wind.unit, wind.level) == ("gte", "km/h", Rating.POOR)


def test_moderate_factors_do_not_add_up_to_poor():
    result = evaluate(make(pm25=20.0, uv_index=6.5, precipitation=0.5))
    assert result.rating is Rating.MODERATE
    assert len(result.reasons) == 3


def test_reasons_order_is_deterministic_poor_first_then_rule_order():
    result = evaluate(make(uv_index=6.5, pm10=130.0, pm25=20.0, precipitation=0.5))
    assert codes(result) == [
        ("PM10_HIGH", "pm10", Rating.POOR),
        ("PM25_HIGH", "pm25", Rating.MODERATE),
        ("PRECIPITATION", "precipitation", Rating.MODERATE),
        ("UV_HIGH", "uv_index", Rating.MODERATE),
    ]
    # Same inputs, repeated: identical output (no hidden state).
    inputs = make(uv_index=6.5, pm10=130.0, pm25=20.0, precipitation=0.5)
    assert evaluate(inputs) == evaluate(inputs)


def test_cold_and_heat_codes_for_both_temperature_params():
    cold = evaluate(make(apparent_temperature=-12.0, temperature_2m=-5.0))
    assert cold.rating is Rating.POOR
    assert ("COLD", "apparent_temperature", Rating.POOR) in codes(cold)
    assert ("COLD", "temperature_2m", Rating.MODERATE) in codes(cold)
    heat = evaluate(make(apparent_temperature=33.0, temperature_2m=28.0))
    assert ("HEAT", "apparent_temperature", Rating.POOR) in codes(heat)


def test_no_inputs_is_unknown_not_good():
    result = evaluate(OutdoorInputs())
    assert result.rating is Rating.UNKNOWN
    assert {m.group for m in result.missing if m.core} == {
        "air",
        "precipitation",
        "wind",
        "thermal",
    }


def test_missing_core_factor_blocks_good():
    for core_fields, group in (
        (("pm25", "pm10"), "air"),
        (("precipitation",), "precipitation"),
        (("wind_speed_10m",), "wind"),
        (("temperature_2m", "apparent_temperature"), "thermal"),
    ):
        result = evaluate(make(**dict.fromkeys(core_fields)))
        assert result.rating is Rating.UNKNOWN, group
        assert [(m.group, m.status, m.core) for m in result.missing] == [(group, "MISSING", True)]


def test_one_of_two_alternatives_is_enough_for_a_group():
    assert evaluate(make(pm10=None)).rating is Rating.GOOD
    assert evaluate(make(pm25=None)).rating is Rating.GOOD
    assert evaluate(make(apparent_temperature=None)).rating is Rating.GOOD
    assert evaluate(make(temperature_2m=None)).rating is Rating.GOOD


def test_missing_optional_factor_is_good_but_reported():
    result = evaluate(make(uv_index=None, visibility=None, wind_gusts_10m=None))
    assert result.rating is Rating.GOOD
    assert {(m.group, m.core) for m in result.missing} == {
        ("uv", False),
        ("visibility", False),
        ("gusts", False),
    }


def test_bad_available_factor_stands_even_with_core_missing():
    result = evaluate(make(pm25=None, pm10=None, wind_speed_10m=45.0))
    assert result.rating is Rating.POOR
    assert [m.group for m in result.missing] == ["air"]
    result = evaluate(make(pm25=None, pm10=None, uv_index=7.0))
    assert result.rating is Rating.MODERATE


def test_stale_and_unavailable_inputs_are_not_used():
    for freshness in ("STALE", "UNAVAILABLE", "garbage", ""):
        inputs = replace(make(), pm25=Reading(200.0, freshness), pm10=None)
        result = evaluate(inputs)
        # The stale 200 ug/m3 must not produce POOR, and GOOD is not confirmed.
        assert result.rating is Rating.UNKNOWN
        assert [(m.group, m.params, m.status) for m in result.missing] == [
            ("air", ("pm10", "pm25"), "STALE")
        ]
    for freshness in ("FRESH", "RECENT"):
        inputs = replace(make(), pm25=Reading(200.0, freshness))
        assert evaluate(inputs).rating is Rating.POOR


def test_non_finite_values_are_invalid_not_good():
    for bad in (math.nan, math.inf, -math.inf):
        result = evaluate(make(wind_speed_10m=bad))
        assert result.rating is Rating.UNKNOWN
        assert [(m.group, m.status) for m in result.missing] == [("wind", "INVALID")]


def test_no_side_effects_on_inputs():
    inputs = make(pm25=20.0, wind_speed_10m=45.0)
    snapshot = repr(inputs)
    evaluate(inputs)
    assert repr(inputs) == snapshot  # frozen dataclasses; repr unchanged


def test_every_rule_is_documented_and_well_formed():
    input_fields = {f.name for f in fields(OutdoorInputs)}
    for rule in RULES:
        assert rule.param in input_fields
        assert rule.basis
        assert rule.comparison in ("gt", "gte", "lt", "lte")
        higher_is_worse = rule.comparison in ("gt", "gte")
        # poor is strictly worse than moderate in the rule's own direction
        assert (rule.poor > rule.moderate) if higher_is_worse else (rule.poor < rule.moderate)
    # Nothing claims an official source without a date.
    for rule in RULES:
        if "PRODUCT DECISION" not in rule.basis:
            assert "verified 2026-09-30" in rule.basis


def test_monotonicity_worsening_any_input_never_improves_the_result():
    # Grid per field, ordered from best to worst (in the rule's direction).
    grid = {
        "temperature_2m": [15.0, 5.0, 0.0, -3.0, -10.0, -20.0],
        "apparent_temperature": [14.0, 26.0, 27.0, 31.9, 32.0, 40.0],
        "precipitation": [0.0, 0.05, 0.1, 1.0, 2.5, 10.0],
        "wind_speed_10m": [0.0, 28.9, 29.0, 38.9, 39.0, 80.0],
        "wind_gusts_10m": [0.0, 49.9, 50.0, 61.9, 62.0, 120.0],
        "uv_index": [0.0, 5.9, 6.0, 7.9, 8.0, 12.0],
        "visibility": [24000.0, 5000.0, 4999.0, 1000.0, 999.0, 50.0],
        "pm25": [0.0, 15.0, 15.1, 50.0, 50.1, 300.0],
        "pm10": [0.0, 45.0, 45.1, 120.0, 120.1, 500.0],
    }
    base_variants = (
        GOOD_VALUES,
        {**GOOD_VALUES, "pm25": None, "pm10": None},  # UNKNOWN baseline (core missing)
        {**GOOD_VALUES, "uv_index": 6.5, "wind_speed_10m": 30.0},  # MODERATE baseline
    )
    for base in base_variants:
        for param, values in grid.items():
            if base.get(param) is None and param in ("pm25", "pm10"):
                continue  # keep the missing baseline missing
            ratings = [SEVERITY[evaluate(make(**{**base, param: v})).rating] for v in values]
            assert ratings == sorted(ratings), (param, base, ratings)
    # Pairwise combinations of the two worst-most steps too.
    params = list(grid)
    for a, b in itertools.combinations(params, 2):
        for i, j in itertools.product(range(len(grid[a])), range(len(grid[b]))):
            cur = make(**{a: grid[a][i], b: grid[b][j]})
            for da, db in ((1, 0), (0, 1)):
                if i + da < len(grid[a]) and j + db < len(grid[b]):
                    worse = make(**{a: grid[a][i + da], b: grid[b][j + db]})
                    assert SEVERITY[evaluate(worse).rating] >= SEVERITY[evaluate(cur).rating]
