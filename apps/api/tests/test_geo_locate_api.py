"""GET /areas and POST /geo/locate (TASK-6.2(8), ADR-026): the assignment ladder
point-in-polygon -> nearest ACTIVE area within the limit -> out_of_range, plus the ADR-002
privacy constraints shared with /geo/resolve."""

import logging

import pytest
from fastapi.testclient import TestClient

import app.api.v1.geo as geo_api
from app.db import get_db
from app.geo import NEAREST_AREA_MAX_KM, ResolvedArea, haversine_km, nearest_area
from app.main import app
from app.models import GeoArea

KLODZKO = GeoArea(
    id=1, slug="klodzko", name="Kłodzko", latitude=50.433493, longitude=16.65366,
    teryt_code="9999901", weather_polling_active=True,
)  # fmt: skip
WARSZAWA = GeoArea(
    id=2, slug="warszawa", name="Warszawa", latitude=52.2297, longitude=21.0122,
    teryt_code=None, weather_polling_active=True,
)  # fmt: skip
GMINA = GeoArea(
    id=9, slug="x", name="Gmina X", latitude=50.0, longitude=19.0,
    teryt_code="9999909", weather_polling_active=False,
)  # fmt: skip


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _Session:
    """execute() = the active areas (or all, when the test asks), get() = by id."""

    def __init__(self, areas):
        self.areas = areas

    def execute(self, stmt):
        only_active = bool(stmt._where_criteria)  # the only WHERE ever added is "active"
        rows = [a for a in self.areas if a.weather_polling_active or not only_active]
        return _Rows(rows)

    def get(self, _model, key):
        return next((a for a in self.areas if a.id == key), None)


def _client(monkeypatch, resolved, areas=(KLODZKO, WARSZAWA, GMINA)):
    calls = []

    def _fake(_db, lat, lon):
        calls.append((lat, lon))
        return resolved

    monkeypatch.setattr(geo_api, "resolve_gmina", _fake)

    def _dep():
        yield _Session(list(areas))

    app.dependency_overrides[get_db] = _dep
    return TestClient(app), calls


def teardown_function() -> None:
    app.dependency_overrides.pop(get_db, None)


def _locate(client, lat, lon):
    r = client.post("/api/v1/geo/locate", json={"latitude": lat, "longitude": lon})
    assert r.status_code == 200
    return r.json()


def test_areas_lists_active_by_default_and_all_on_request(monkeypatch):
    client, _ = _client(monkeypatch, None)
    default = client.get("/api/v1/areas").json()["areas"]
    assert [a["geo_area_id"] for a in default] == [1, 2]
    assert default[0] == {
        "geo_area_id": 1, "slug": "klodzko", "name": "Kłodzko", "teryt_code": "9999901",
        "latitude": 50.433493, "longitude": 16.65366, "weather_polling_active": True,
    }  # fmt: skip
    assert default[1]["teryt_code"] is None
    everything = client.get("/api/v1/areas?active_only=false").json()["areas"]
    assert [a["geo_area_id"] for a in everything] == [1, 2, 9]
    assert everything[2]["weather_polling_active"] is False


def test_locate_point_in_polygon_wins(monkeypatch):
    resolved = ResolvedArea(geo_area_id=1, teryt_code="9999901", slug="klodzko", name="Kłodzko")
    client, _ = _client(monkeypatch, resolved)
    body = _locate(client, 50.43, 16.65)
    assert body["status"] == "resolved" and body["assignment_method"] == "point_in_polygon"
    assert body["area"]["geo_area_id"] == 1 and body["distance_km"] is None


def test_locate_resolved_inactive_gmina_is_not_replaced_by_a_nearby_active_one(monkeypatch):
    # The administrative answer stays the answer (ADR-019); the flag tells the client the
    # dashboard will say "no data here".
    resolved = ResolvedArea(geo_area_id=9, teryt_code="9999909", slug="x", name="Gmina X")
    client, _ = _client(monkeypatch, resolved)
    body = _locate(client, 50.0, 19.0)
    assert body["assignment_method"] == "point_in_polygon"
    assert body["area"]["geo_area_id"] == 9 and body["area"]["weather_polling_active"] is False


def test_locate_falls_back_to_nearest_active_area_and_discloses_it(monkeypatch):
    client, _ = _client(monkeypatch, None)
    # ~11 km north of Kłodzko centre; GMINA (inactive) is nearer to nothing here.
    body = _locate(client, 50.53, 16.65366)
    assert body["status"] == "resolved" and body["assignment_method"] == "nearest_area"
    assert body["area"]["geo_area_id"] == 1
    assert body["distance_km"] == pytest.approx(10.7, abs=0.1)


def test_locate_never_falls_back_to_an_inactive_area(monkeypatch):
    client, _ = _client(monkeypatch, None)
    body = _locate(client, 50.0, 19.0)  # exactly on inactive GMINA, no active area near
    assert body == {
        "status": "out_of_range", "area": None, "assignment_method": None, "distance_km": None,
    }  # fmt: skip


def test_locate_out_of_range_outside_poland(monkeypatch):
    client, _ = _client(monkeypatch, None)
    assert _locate(client, 52.52, 13.4)["status"] == "out_of_range"  # Berlin


def _north_of(area, km):
    """A point `km` due north of the area centre (lat offset is exact on a meridian)."""
    return area.latitude + km / 111.19492664455873, area.longitude  # = 2*pi*R/360


def test_nearest_area_limit_is_inclusive_and_boundary_exact():
    areas = [(1, KLODZKO.latitude, KLODZKO.longitude)]
    lat, lon = _north_of(KLODZKO, 24.9)
    assert nearest_area(lat, lon, areas) is not None
    lat, lon = _north_of(KLODZKO, 25.1)
    assert nearest_area(lat, lon, areas) is None
    # exactly at the limit (distance computed by the same function): inclusive
    lat, lon = _north_of(KLODZKO, 25.0)
    d = haversine_km(lat, lon, KLODZKO.latitude, KLODZKO.longitude)
    assert nearest_area(lat, lon, areas, max_km=d) is not None
    assert nearest_area(lat, lon, areas, max_km=d - 1e-6) is None
    assert NEAREST_AREA_MAX_KM == 25.0


def test_nearest_area_tie_breaks_by_lowest_id_regardless_of_order():
    # Two areas symmetric around the point (same latitude, equal lon offset).
    a, b = (10, 50.0, 16.0), (2, 50.0, 16.2)
    point = (50.0, 16.1)
    assert nearest_area(*point, [a, b])[0] == 2
    assert nearest_area(*point, [b, a])[0] == 2


def test_nearest_area_ids_compare_numerically_not_as_text():
    pts = [(10, 50.0, 16.0), (9, 50.0, 16.2)]
    assert nearest_area(50.0, 16.1, pts)[0] == 9  # "10" < "9" as text, 9 < 10 as ids


@pytest.mark.parametrize(
    "body",
    [{"latitude": 91, "longitude": 16}, {"latitude": 50}, {"latitude": 50, "longitude": "x"}],
)
def test_locate_invalid_input_is_422(monkeypatch, body):
    client, calls = _client(monkeypatch, None)
    assert client.post("/api/v1/geo/locate", json=body).status_code == 422
    assert calls == []


def test_locate_get_is_405(monkeypatch):
    client, _ = _client(monkeypatch, None)
    assert client.get("/api/v1/geo/locate?latitude=50&longitude=16").status_code == 405


def test_locate_does_not_log_or_echo_coordinates(monkeypatch, caplog):
    client, _ = _client(monkeypatch, None)
    with caplog.at_level(logging.DEBUG):
        r = client.post("/api/v1/geo/locate", json={"latitude": 50.123456, "longitude": 16.654321})
    assert r.status_code == 200
    for text in (caplog.text, r.text):
        assert "50.123456" not in text and "16.654321" not in text


def test_locate_database_error_is_503_and_leaks_no_coordinates(monkeypatch, caplog):
    from sqlalchemy.exc import OperationalError

    def _boom(_db, lat, lon):
        raise OperationalError("SELECT ...", {"lat": lat, "lon": lon}, Exception("db down"))

    monkeypatch.setattr(geo_api, "resolve_gmina", _boom)

    def _dep():
        yield None

    app.dependency_overrides[get_db] = _dep
    client = TestClient(app, raise_server_exceptions=False)
    with caplog.at_level(logging.DEBUG):
        r = client.post("/api/v1/geo/locate", json={"latitude": 50.123456, "longitude": 16.654321})
    assert r.status_code == 503
    assert "50.123456" not in caplog.text and "16.654321" not in caplog.text + r.text
