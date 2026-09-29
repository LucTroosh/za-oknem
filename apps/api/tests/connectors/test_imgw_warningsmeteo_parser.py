"""Tests for imgw_warningsmeteo.parser: only the verified top-level shape
dispatch - normalize() doesn't exist yet, see parser.py's module docstring."""

import pytest

from app.connectors.imgw_warningsmeteo.parser import (
    ImgwWarningsMeteoParseError,
    parse_warnings,
)


def test_returns_list_as_is():
    warning = {"id": "1"}
    assert parse_warnings([warning]) == [warning]


def test_treats_message_dict_as_zero_warnings():
    assert parse_warnings({"message": "Brak ostrzeżeń meteorologicznych"}) == []


def test_raises_on_unrecognized_dict_shape():
    with pytest.raises(ImgwWarningsMeteoParseError):
        parse_warnings({"unexpected": "shape"})


def test_raises_on_a_different_message_text():
    # Codex review (PR #38): only the exact confirmed "no warnings" text counts
    # as empty - any other message (rate-limit notice, service diagnostic) must
    # fail loud, not be silently read as zero active warnings (rule #10).
    with pytest.raises(ImgwWarningsMeteoParseError):
        parse_warnings({"message": "Rate limit exceeded"})


def test_raises_on_the_right_message_with_an_extra_field():
    # Codex review (PR #38): the verified shape is the single-key dict exactly -
    # an extra field alongside the right text (e.g. a diagnostic "error" flag)
    # must still fail loud, not be read as a valid empty snapshot (rule #10).
    with pytest.raises(ImgwWarningsMeteoParseError):
        parse_warnings({"message": "Brak ostrzeżeń meteorologicznych", "error": "stale"})


def test_raises_on_unrecognized_type():
    with pytest.raises(ImgwWarningsMeteoParseError):
        parse_warnings("not a list or dict")
