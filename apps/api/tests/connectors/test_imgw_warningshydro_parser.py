"""Tests for imgw_warningshydro.parser: the defensive "empty" shape handling
(ADR-009) and normalize()'s field mapping, including that severity is never
reinterpreted."""

from datetime import UTC, datetime

import pytest

from app.connectors.imgw_warningshydro.parser import (
    ImgwWarningsHydroParseError,
    normalize,
    parse_warnings,
)

WARNING = {
    "opublikowano": "2026-05-17 08:45:07",
    "stopień": "-1",
    "data_od": "2026-05-17 08:45:56",
    "data_do": "9999-12-31 23:59:59",
    "prawdopodobieństwo": "90",
    "numer": "31",
    "biuro": "Biuro Prognoz Hydrologicznych we Wrocławiu",
    "zdarzenie": "Susza hydrologiczna",
    "przebieg": "W związku z występującymi niskimi przepływami...",
    "komentarz": "Ostrzeżenie wydawane jest w sytuacji...",
    "obszary": [
        {
            "wojewodztwo": "wielkopolskie",
            "opis": "wielkopolskie, Kanał Mosinski, susza",
            "kod_zlewni": ["Z_P_WP_1856"],
        }
    ],
}


class TestParseWarnings:
    def test_returns_list_as_is(self):
        assert parse_warnings([WARNING]) == [WARNING]

    def test_treats_message_dict_as_zero_warnings(self):
        assert parse_warnings({"message": "Brak ostrzeżeń"}) == []

    def test_raises_on_unrecognized_dict_shape(self):
        with pytest.raises(ImgwWarningsHydroParseError):
            parse_warnings({"unexpected": "shape"})

    def test_raises_on_unrecognized_type(self):
        with pytest.raises(ImgwWarningsHydroParseError):
            parse_warnings("not a list or dict")


class TestNormalize:
    def test_maps_fields_without_reinterpreting_severity(self):
        record = normalize(WARNING, fetched_at=datetime.now(UTC))

        assert record["source_id"] == "imgw_warningshydro"
        assert record["external_id"] == "31"
        assert record["event_type"] == "Susza hydrologiczna"
        assert record["severity_raw"] == "-1"  # not parsed as an int, not clamped
        assert record["probability_pct"] == 90.0
        assert record["areas"] == WARNING["obszary"]
        assert record["valid_until"].year == 9999

    def test_probability_none_when_absent(self):
        warning = {k: v for k, v in WARNING.items() if k != "prawdopodobieństwo"}
        record = normalize(warning, fetched_at=datetime.now(UTC))
        assert record["probability_pct"] is None

    def test_comment_none_when_absent(self):
        warning = {**WARNING, "komentarz": None}
        record = normalize(warning, fetched_at=datetime.now(UTC))
        assert record["comment"] is None

    def test_raises_on_missing_required_field(self):
        warning = {k: v for k, v in WARNING.items() if k != "zdarzenie"}
        with pytest.raises(ImgwWarningsHydroParseError):
            normalize(warning, fetched_at=datetime.now(UTC))

    def test_raises_on_null_required_field(self):
        # Codex review (PR #37): str(None) used to silently become the literal
        # text "None" instead of failing (rule #1/#10).
        warning = {**WARNING, "zdarzenie": None}
        with pytest.raises(ImgwWarningsHydroParseError):
            normalize(warning, fetched_at=datetime.now(UTC))

    def test_raises_when_areas_is_not_a_list(self):
        warning = {**WARNING, "obszary": "not-a-list"}
        with pytest.raises(ImgwWarningsHydroParseError):
            normalize(warning, fetched_at=datetime.now(UTC))
