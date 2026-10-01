"""Point-in-polygon + importer against a REAL PostGIS database (ADR-019, rule #9).

Geometry can't run on the SQLite unit-test engine, so these tests use DATABASE_URL (the
CI service is postgis/postgis:16-3.4, migrated to head before pytest) and SKIP when no
PostGIS database with the 0011 schema is reachable. The importer commits per record, so
the session runs on a SAVEPOINT inside an outer transaction that is always rolled back:
synthetic squares under fake TERYT codes 99999xx, placed in the Baltic Sea (no real
gmina or seeded city there, so they can't collide with a real import), nothing left
behind. CI sets REQUIRE_POSTGIS=1: unavailable PostGIS then FAILS instead of skipping.
"""

import json
import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config import settings
from app.connectors.prg_gminy.ingest import import_records, plan_retire, retire_missing
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
        if os.environ.get("REQUIRE_POSTGIS") == "1":  # CI: a skip would hide the suite
            pytest.fail(f"PostGIS database required but unavailable: {type(exc).__name__}")
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


# SYNTHETIC, open Baltic Sea (lat ~55, lon 16-18). A and B share the border lon=16.5;
# C has a hole that is filled by D (an enclave gmina).
A = _feature("9999901", "Synth A", _ring(16.0, 54.9, 16.5, 55.0))
B = _feature("9999902", "Synth B", _ring(16.5, 54.9, 17.0, 55.0))
C = _feature("9999903", "Synth C", _ring(17.1, 54.9, 17.9, 55.1), _ring(17.4, 54.98, 17.6, 55.02))
D = _feature("9999904", "Synth D", _ring(17.4, 54.98, 17.6, 55.02))


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
    assert _code(pg, 54.95, 16.25) == "9999901"
    assert _code(pg, 54.95, 16.75) == "9999902"


def test_point_on_shared_border_is_deterministic_lowest_teryt(pg):
    _load(pg, A, B)
    assert {_code(pg, 54.95, 16.5) for _ in range(5)} == {"9999901"}


def test_point_in_hole_belongs_to_enclave_not_surrounding_gmina(pg):
    _load(pg, C, D)
    assert _code(pg, 55.0, 17.5) == "9999904"
    assert _code(pg, 54.92, 17.2) == "9999903"


def test_hole_without_enclave_has_no_match(pg):
    _load(pg, C)
    assert _code(pg, 55.0, 17.5) is None


def test_outside_polygons_is_no_match_not_nearest(pg):
    _load(pg, A)
    # 0.001 deg outside A's west border: a "nearest" method would return A; we must not.
    assert _code(pg, 54.95, 15.999) is None
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
            "VALUES ('synth-seed', 'Synth Seed', 54.95, 16.25)"
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
    assert resolve_gmina(pg, 54.95, 16.25).geo_area_id == seed_id


def test_invalid_self_intersecting_polygon_is_repaired(pg):
    bowtie = [[16.0, 54.9], [16.2, 55.0], [16.2, 54.9], [16.0, 55.0], [16.0, 54.9]]
    records, _ = parse_feature_collection(
        {"type": "FeatureCollection", "features": [_feature("9999905", "Synth bowtie", bowtie)]}
    )
    report = import_records(records, pg)
    assert report.repaired == 1 and report.rejected == []
    assert _code(pg, 54.95, 16.05) == "9999905"


def test_seed_with_obsolete_code_is_readopted_by_new_code(pg):
    pg.execute(
        text(
            "INSERT INTO geo_areas (slug, name, latitude, longitude, teryt_code) "
            "VALUES ('synth-seed', 'Synth Seed', 54.95, 16.25, '9999950')"
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
    renamed = _feature("9999901", "Synth A renamed", _ring(16.0, 54.9, 16.5, 55.0))
    _load(pg, renamed)
    assert resolve_gmina(pg, 54.95, 16.25).name == "Synth A renamed"


def _seed(pg, slug, lat, lon):
    pg.execute(
        text("INSERT INTO geo_areas (slug, name, latitude, longitude) VALUES (:s, :s, :lat, :lon)"),
        {"s": slug, "lat": lat, "lon": lon},
    )
    return pg.execute(text("SELECT id FROM geo_areas WHERE slug=:s"), {"s": slug}).scalar()


def test_update_recomputes_representative_point_of_imported_row(pg):
    _load(pg, A)
    moved = _feature("9999901", "Synth A", _ring(17.1, 54.9, 17.5, 55.0))
    _load(pg, moved)
    inside = pg.execute(
        text(
            "SELECT ST_Covers(boundary, ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)), "
            "longitude FROM geo_areas WHERE teryt_code='9999901'"
        )
    ).one()
    assert inside[0] is True and inside[1] > 17.0


def test_update_keeps_seed_coordinates(pg):
    seed_id = _seed(pg, "synth-seed", 54.95, 16.25)
    _load(pg, A)
    _load(pg, _feature("9999901", "Synth A", _ring(16.0, 54.9, 16.6, 55.0)))
    row = pg.execute(
        text("SELECT latitude, longitude FROM geo_areas WHERE id=:i"), {"i": seed_id}
    ).one()
    assert row == (54.95, 16.25)


def test_seed_never_steals_a_code_held_by_another_row(pg):
    _load(pg, A)  # creates row teryt-9999901
    seed_id = _seed(pg, "synth-seed", 54.95, 16.25)
    report = _load(pg, A)
    assert report.adopted_seeds == 0 and len(report.seed_conflicts) == 1
    code = pg.execute(text("SELECT teryt_code FROM geo_areas WHERE id=:i"), {"i": seed_id})
    assert code.scalar() is None


def test_two_seeds_in_one_gmina_lowest_id_adopts_other_is_reported(pg):
    first = _seed(pg, "synth-seed-1", 54.95, 16.25)
    _seed(pg, "synth-seed-2", 54.96, 16.26)
    report = _load(pg, A)  # _load asserts no rejected record (no UNIQUE violation)
    assert (report.adopted_seeds, len(report.seed_conflicts)) == (1, 1)
    code = pg.execute(text("SELECT teryt_code FROM geo_areas WHERE id=:i"), {"i": first})
    assert code.scalar() == "9999901"


def test_retire_missing_clears_obsolete_boundary_only(pg):
    _load(pg, A, B)
    assert retire_missing(["9999901"], pg, force=True) == 1
    assert _code(pg, 54.95, 16.75) is None  # B retired: resolver must not return it
    assert _code(pg, 54.95, 16.25) == "9999901"
    with pytest.raises(ValueError):
        retire_missing([], pg, force=True)


def test_retire_refuses_partial_snapshot_without_force(pg):
    _load(pg, A, B)
    with pytest.raises(ValueError, match="looks partial"):
        retire_missing(["9999901"], pg)
    assert plan_retire(["9999901"], pg, force=True) == 1  # dry-run count, nothing changed
    assert _code(pg, 54.95, 16.75) == "9999902"


def test_retire_refuses_large_fraction_even_for_big_snapshot(pg):
    _load(pg, A, B)
    big = [f"{9000000 + i}" for i in range(2000)]  # complete-looking but shares no code
    with pytest.raises(ValueError, match="would retire"):
        retire_missing(big, pg)


def test_rejected_code_still_protects_seed_from_readoption(pg):
    pg.execute(
        text(
            "INSERT INTO geo_areas (slug, name, latitude, longitude, teryt_code) "
            "VALUES ('synth-seed', 'Synth Seed', 54.95, 16.25, '9999950')"
        )
    )
    records, _ = parse_feature_collection({"type": "FeatureCollection", "features": [A]})
    # 9999950 was in the file but rejected (bad geometry): it must not look "gone".
    report = import_records(records, pg, extra_codes=["9999950"])
    assert report.adopted_seeds == 0 and report.inserted == 1


def test_geojson_roundtrip_sanity():
    # guards the fixtures themselves (plain json, no DB)
    assert json.loads(json.dumps(A))["geometry"]["type"] == "Polygon"
