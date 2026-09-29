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


def test_raises_on_unrecognized_type():
    with pytest.raises(ImgwWarningsMeteoParseError):
        parse_warnings("not a list or dict")
