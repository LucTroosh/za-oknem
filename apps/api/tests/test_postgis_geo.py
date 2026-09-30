"""Point-in-polygon + importer against a REAL PostGIS database (ADR-019, rule #9).

Geometry can't run on the SQLite unit-test engine, so these tests use DATABASE_URL (the
CI service is postgis/postgis:16-3.4, migrated to head before pytest) and SKIP when no
PostGIS database with the 0011 schema is reachable. The importer commits per record, so
the session runs on a SAVEPOINT inside an outer transaction that is always rolled back:
synthetic squares under fake TERYT codes 99999xx, in an area with no seeded city, and
nothing left behind.
"""

import json

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config import settings
from app.connectors.prg_gminy.ingest import import_records, retire_missing
from app.connectors.prg_gminy.parser import parse_feature_collection
from app.geo import resolve_gmina

pytestmark = pytest.mark.postgis


@pytest.fixture
def pg():
    try:
        engine = create_engine(settings.database_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT postgis_version()"))
            conn.execute(text("SELECT teryt_code, boundary FROM geo_areas LIMIT 0"))
    except Exception as exc:
        pytest.skip(f"no PostGIS database with migration 0011 available: {type(exc).__name__}")
    conn = engine.connect()
    outer = conn.begin()
    session = Session(bind=conn, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        outer.rollback()
        conn.close()
        engine.dispose()


def _ring(lon0, lat0, lon1, lat1):
    return [[lon0, lat0], [lon1, lat0], [lon1, lat1], [lon0, lat1], [lon0, lat0]]


def _feature(code, name, *rings):
    return {
        "type": "Feature",
        "properties": {"JPT_KOD_JE": code, "JPT_NAZWA_": name},
        "geometry": {"type": "Polygon", "coordinates": list(rings)},
    }


# SYNTHETIC, south-east Poland, clear of every seeded city. A and B share the border
# lon=22.5; C has a hole that is filled by D (an enclave gmina).
A = _feature("9999901", "Synth A", _ring(22.0, 49.6, 22.5, 49.9))
B = _feature("9999902", "Synth B", _ring(22.5, 49.6, 23.0, 49.9))
C = _feature("9999903", "Synth C", _ring(23.1, 49.5, 23.9, 50.3), _ring(23.4, 49.8, 23.6, 50.0))
D = _feature("9999904", "Synth D", _ring(23.4, 49.8, 23.6, 50.0))


def _load(pg, *features):
    records, rejected = parse_feature_collection(
        {"type": "FeatureCollection", "features": list(features)}
    )
    assert rejected == []
    report = import_records(records, pg)
    assert report.rejected == []
    return report


def _code(pg, lat, lon):
    area = resolve_gmina(pg, lat, lon)
    return area.teryt_code if area else None


def test_point_inside_resolves(pg):
    _load(pg, A, B)
    assert _code(pg, 49.75, 22.25) == "9999901"
    assert _code(pg, 49.75, 22.75) == "9999902"


def test_point_on_shared_border_is_deterministic_lowest_teryt(pg):
    _load(pg, A, B)
    assert {_code(pg, 49.75, 22.5) for _ in range(5)} == {"9999901"}


def test_point_in_hole_belongs_to_enclave_not_surrounding_gmina(pg):
    _load(pg, C, D)
    assert _code(pg, 49.9, 23.5) == "9999904"
    assert _code(pg, 49.6, 23.2) == "9999903"


def test_hole_without_enclave_has_no_match(pg):
    _load(pg, C)
    assert _code(pg, 49.9, 23.5) is None


def test_outside_polygons_is_no_match_not_nearest(pg):
    _load(pg, A)
    # 0.001 deg outside A's west border: a "nearest" method would return A; we must not.
    assert _code(pg, 49.75, 21.999) is None
    assert _code(pg, 52.52, 13.405) is None


def test_reimport_is_idempotent(pg):
    first = _load(pg, A)
    second = _load(pg, A)
    assert (first.inserted, second.inserted, second.updated) == (1, 0, 1)
    count = pg.execute(text("SELECT count(*) FROM geo_areas WHERE teryt_code='9999901'")).scalar()
    assert count == 1


def test_new_gmina_is_geo_matching_only(pg):
    _load(pg, A)
    row = pg.execute(
        text(
            "SELECT weather_polling_active, slug, ST_Covers(boundary, "
            "ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)) "
            "FROM geo_areas WHERE teryt_code='9999901'"
        )
    ).one()
    assert row == (False, "teryt-9999901", True)  # representative point lies inside


def test_seeded_city_inside_polygon_adopts_teryt_and_keeps_id_and_polling(pg):
    pg.execute(
        text(
            "INSERT INTO geo_areas (slug, name, latitude, longitude) "
            "VALUES ('synth-seed', 'Synth Seed', 49.75, 22.25)"
        )
    )
    seed_id = pg.execute(text("SELECT id FROM geo_areas WHERE slug='synth-seed'")).scalar()
    report = _load(pg, A)
    assert (report.adopted_seeds, report.inserted) == (1, 0)
    row = pg.execute(
        text("SELECT teryt_code, weather_polling_active FROM geo_areas WHERE id=:i"),
        {"i": seed_id},
    ).one()
    assert row == ("9999901", True)
    assert resolve_gmina(pg, 49.75, 22.25).geo_area_id == seed_id


def test_invalid_self_intersecting_polygon_is_repaired(pg):
    bowtie = [[22.0, 49.6], [22.2, 49.8], [22.2, 49.6], [22.0, 49.8], [22.0, 49.6]]
    records, _ = parse_feature_collection(
        {"type": "FeatureCollection", "features": [_feature("9999905", "Synth bowtie", bowtie)]}
    )
    report = import_records(records, pg)
    assert report.repaired == 1 and report.rejected == []
    assert _code(pg, 49.7, 22.05) == "9999905"


def test_seed_with_obsolete_code_is_readopted_by_new_code(pg):
    pg.execute(
        text(
            "INSERT INTO geo_areas (slug, name, latitude, longitude, teryt_code) "
            "VALUES ('synth-seed', 'Synth Seed', 49.75, 22.25, '9999950')"
        )
    )
    seed_id = pg.execute(text("SELECT id FROM geo_areas WHERE slug='synth-seed'")).scalar()
    report = _load(pg, A)  # snapshot no longer contains 9999950
    assert (report.adopted_seeds, report.inserted) == (1, 0)
    row = pg.execute(
        text("SELECT teryt_code, weather_polling_active FROM geo_areas WHERE id=:i"),
        {"i": seed_id},
    ).one()
    assert row == ("9999901", True)


def test_reimport_refreshes_name(pg):
    _load(pg, A)
    renamed = _feature("9999901", "Synth A renamed", _ring(22.0, 49.6, 22.5, 49.9))
    _load(pg, renamed)
    assert resolve_gmina(pg, 49.75, 22.25).name == "Synth A renamed"


def test_retire_missing_clears_obsolete_boundary_only(pg):
    _load(pg, A, B)
    assert retire_missing(["9999901"], pg) == 1
    assert _code(pg, 49.75, 22.75) is None  # B retired: resolver must not return it
    assert _code(pg, 49.75, 22.25) == "9999901"
    with pytest.raises(ValueError):
        retire_missing([], pg)


def test_geojson_roundtrip_sanity():
    # guards the fixtures themselves (plain json, no DB)
    assert json.loads(json.dumps(A))["geometry"]["type"] == "Polygon"
