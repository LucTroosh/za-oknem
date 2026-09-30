"""Parser tests on SYNTHETIC fixtures (squares near Kłodzko) - not real PRG data."""

import json

import pytest

from app.connectors.prg_gminy.parser import PrgParseError, parse_feature_collection


def _square(lon0=16.0, lat0=50.0, size=0.1):
    return [
        [
            [lon0, lat0],
            [lon0 + size, lat0],
            [lon0 + size, lat0 + size],
            [lon0, lat0 + size],
            [lon0, lat0],
        ]
    ]


def _feature(code="9999901", name="Synth A", geometry=None, **extra_props):
    if geometry is None:
        geometry = {"type": "Polygon", "coordinates": _square()}
    props = {"JPT_KOD_JE": code, "JPT_NAZWA_": name, **extra_props}
    return {"type": "Feature", "properties": props, "geometry": geometry}


def _fc(*features):
    return {"type": "FeatureCollection", "features": list(features)}


def test_valid_polygon_is_normalised_to_multipolygon():
    records, rejected = parse_feature_collection(_fc(_feature()))
    assert rejected == []
    assert len(records) == 1 and records[0].teryt_code == "9999901"
    geom = json.loads(records[0].geometry_json)
    assert geom["type"] == "MultiPolygon" and len(geom["coordinates"]) == 1


def test_z_coordinates_are_dropped():
    ring = [[x, y, 100.0] for x, y in _square()[0]]
    feature = _feature(geometry={"type": "Polygon", "coordinates": [ring]})
    records, _ = parse_feature_collection(_fc(feature))
    assert all(len(p) == 2 for p in json.loads(records[0].geometry_json)["coordinates"][0][0])


def test_custom_field_names():
    feature = {
        "type": "Feature",
        "properties": {"kod": "9999901", "nazwa": "X"},
        "geometry": {"type": "Polygon", "coordinates": _square()},
    }
    records, rejected = parse_feature_collection(
        _fc(feature), teryt_field="kod", name_field="nazwa"
    )
    assert len(records) == 1 and rejected == []


@pytest.mark.parametrize(
    "bad",
    [
        _feature(code="123456"),  # 6 digits
        _feature(code=1234567),  # number, not string
        _feature(code=None),
        _feature(name=""),
        _feature(geometry={"type": "Point", "coordinates": [16.0, 50.0]}),
        _feature(geometry=None) | {"geometry": None},
        # EPSG:2180 metres, i.e. forgot to reproject
        _feature(geometry={"type": "Polygon", "coordinates": _square(300000.0, 400000.0, 1000)}),
        # open ring
        _feature(geometry={"type": "Polygon", "coordinates": [_square()[0][:-1] + [[16.0, 50.5]]]}),
        # NaN coordinate
        _feature(
            geometry={
                "type": "Polygon",
                "coordinates": [[[float("nan"), 50.0], [16.1, 50.0], [16.1, 50.1], [16.0, 50.1]]],
            }
        ),
    ],
)
def test_bad_feature_is_rejected_but_good_one_survives(bad):
    records, rejected = parse_feature_collection(_fc(bad, _feature(code="9999902")))
    assert [r.teryt_code for r in records] == ["9999902"]
    assert len(rejected) == 1


def test_duplicate_teryt_code_rejected():
    records, rejected = parse_feature_collection(_fc(_feature(), _feature(name="Synth dup")))
    assert len(records) == 1
    assert "duplicate" in rejected[0]


@pytest.mark.parametrize("doc", [[], {"type": "Feature"}, _fc(), "x"])
def test_unusable_document_raises(doc):
    with pytest.raises(PrgParseError):
        parse_feature_collection(doc)
