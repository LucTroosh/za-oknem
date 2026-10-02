"""GET /places, GET /places/{id}, POST /places/{id}/activate (ADR-029): search contract,
validation without input echo, idempotent activation, capacity/budget outcomes, per-IP
limit on switching polling on. Real SQLite session shared across threads (StaticPool)."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.places as places
from app.db import Base, get_db
from app.main import app
from app.models import GeoArea, Place
from app.places import normalize_name
from app.rate_limit import place_activations

NOW = datetime(2026, 10, 1, tzinfo=UTC)


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    seed = factory()
    for pid, name, pop, lat in [
        (1, "Łódź", 768755, 51.75),
        (2, "Łódź Mała", 12, 50.0),
        (3, "Nowa Wieś", None, 50.1),
        (4, "Nowa Wieś", 310, 52.9),
    ]:
        seed.add(
            Place(
                id=pid,
                name=name,
                normalized_name=normalize_name(name),
                kind="PPL",
                admin1_code="74",
                admin1_name="Łódź Voivodeship",
                admin2_code=None,
                latitude=lat,
                longitude=19.4,
                population=pop,
                source="geonames_pl",
                source_record_id=str(pid),
                imported_at=NOW,
            )  # fmt: skip
        )
    seed.commit()
    seed.close()

    def _db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _db
    place_activations.reset()
    c = TestClient(app)
    c.factory = factory  # type: ignore[attr-defined]
    yield c
    app.dependency_overrides.pop(get_db, None)
    place_activations.reset()
    engine.dispose()


def test_search_finds_any_locality_by_diacritic_free_prefix(client):
    resp = client.get("/api/v1/places", params={"q": "lodz"})

    assert resp.status_code == 200
    body = resp.json()
    assert [p["name"] for p in body["places"]] == ["Łódź", "Łódź Mała"]
    first = body["places"][0]
    assert first["place_id"] == 1 and first["kind"] == "PPL" and first["population"] == 768755
    assert first["label"] == "Łódź, woj. łódzkie"
    assert set(first) == {
        "place_id", "name", "label", "kind", "admin1_code", "admin2_code", "latitude", "longitude",
        "population",
    }  # fmt: skip
    assert "GeoNames" in body["attribution"] and "CC BY 4.0" in body["attribution"]
    assert resp.headers["cache-control"] == "public, max-age=300"


def test_search_namesakes_sorted_by_population_and_limit_applies(client):
    resp = client.get("/api/v1/places", params={"q": "nowa wies", "limit": 1})

    assert [p["place_id"] for p in resp.json()["places"]] == [4]


def test_search_without_match_is_an_empty_list_not_an_error(client):
    resp = client.get("/api/v1/places", params={"q": "zzzz"})

    assert resp.status_code == 200 and resp.json()["places"] == []


@pytest.mark.parametrize(
    "params",
    [{}, {"q": "a"}, {"q": "x" * 101}, {"q": "ab", "limit": 0}, {"q": "ab", "limit": 21}],
)
def test_search_validation_is_422_without_echoing_the_input(client, params):
    resp = client.get("/api/v1/places", params=params)

    assert resp.status_code == 422
    for err in resp.json()["detail"]:
        assert "input" not in err and "ctx" not in err


def test_search_does_not_log_the_query(client, caplog):
    caplog.set_level("DEBUG")

    client.get("/api/v1/places", params={"q": "sekretnemiasto"})

    # (httpx's own client log of the test transport is not the app's)
    app_logs = [r.getMessage() for r in caplog.records if r.name.startswith("app")]
    assert app_logs and not any("sekretnemiasto" in m for m in app_logs)


def test_get_place_never_creates_or_refreshes_an_area(client):
    resp = client.get("/api/v1/places/1")

    assert resp.status_code == 200
    body = resp.json()
    assert body["place"]["name"] == "Łódź" and body["area"] is None
    assert body["polling"] == "inactive"
    with client.factory() as db:
        assert db.query(GeoArea).count() == 0


def test_unknown_or_invalid_place_id(client):
    assert client.get("/api/v1/places/999").status_code == 404
    assert client.post("/api/v1/places/999/activate").status_code == 404
    assert client.get("/api/v1/places/0").status_code == 422
    assert client.post("/api/v1/places/abc/activate").status_code == 422


def test_activate_creates_the_area_and_is_idempotent(client):
    first = client.post("/api/v1/places/1/activate")
    second = client.post("/api/v1/places/1/activate")

    assert first.status_code == second.status_code == 200
    body = first.json()
    assert body["polling"] == "active"
    area = body["area"]
    assert area["name"] == "Łódź" and area["weather_polling_active"] is True
    assert area["teryt_code"] is None
    assert second.json()["area"]["geo_area_id"] == area["geo_area_id"]
    with client.factory() as db:
        assert db.query(GeoArea).count() == 1
    state = client.get("/api/v1/places/1").json()
    assert state["polling"] == "active" and state["area"]["geo_area_id"] == area["geo_area_id"]


def test_activate_at_capacity_returns_an_inactive_area_not_an_error(client, monkeypatch):
    monkeypatch.setattr(places, "max_active_areas", lambda: 0)

    resp = client.post("/api/v1/places/2/activate")

    assert resp.status_code == 200
    body = resp.json()
    assert body["polling"] == "capacity_reached"
    assert body["area"]["weather_polling_active"] is False
    # `/dashboard/latest?geo_area_id=` for such an area = "no data collected here" (ADR-026).


def test_switching_polling_on_is_rate_limited_per_ip_but_refreshing_is_not(client, monkeypatch):
    monkeypatch.setattr(places, "max_active_areas", lambda: 1000)
    with client.factory() as db:
        for pid in range(10, 22):
            db.add(
                Place(
                    id=pid,
                    name=f"Miejsce{pid}",
                    normalized_name=f"miejsce{pid}",
                    kind="PPL",
                    latitude=52.0,
                    longitude=21.0,
                    source="geonames_pl",
                    source_record_id=str(pid),
                    imported_at=NOW,
                )  # fmt: skip
            )
        db.commit()

    codes = [client.post(f"/api/v1/places/{pid}/activate").status_code for pid in range(10, 21)]

    assert codes == [200] * 10 + [429]
    # an already active area may be refreshed any number of times (the app does it on open)
    assert all(client.post("/api/v1/places/10/activate").status_code == 200 for _ in range(15))


def test_activating_a_place_does_not_change_the_default_lists(client):
    from app.models import PollenSnapshot

    with client.factory() as db:
        seed = GeoArea(slug="klodzko", name="Kłodzko", latitude=50.4, longitude=16.6,
                       weather_polling_active=True)  # fmt: skip
        db.add(seed)
        db.commit()
    client.post("/api/v1/places/1/activate")
    with client.factory() as db:
        for area in db.query(GeoArea).all():
            db.add(
                PollenSnapshot(
                    source_id="open_meteo_pollen",
                    source_record_id=f"p{area.id}",
                    geo_area_id=area.id,
                    unit="grains/m3",
                    model="cams_europe",
                    forecast_reference_time=NOW,
                    valid_at=NOW,
                    fetched_at=NOW,
                )  # fmt: skip
            )
        db.commit()

    areas = client.get("/api/v1/areas").json()["areas"]
    pollen = client.get("/api/v1/pollen/latest").json()["areas"]

    assert [a["slug"] for a in areas] == ["klodzko"]
    assert [a["slug"] for a in pollen] == ["klodzko"]
    with client.factory() as db:
        place_area = db.query(GeoArea).filter(GeoArea.place_id.is_not(None)).one()
    from app.api.v1.pollen import latest_pollen

    with client.factory() as db:
        assert [a["slug"] for a in latest_pollen(db, place_area.id)] == [place_area.slug]


def test_failed_activation_gives_the_rate_limit_slot_back(client, monkeypatch):
    from sqlalchemy.exc import OperationalError

    def boom(*a, **k):
        raise OperationalError("x", {}, Exception("db"))

    monkeypatch.setattr(places, "max_active_areas", lambda: 1000)
    monkeypatch.setattr("app.api.v1.places.activate_place", boom)
    for _ in range(12):  # more than the 10/h limit: all 503, none 429
        assert client.post("/api/v1/places/1/activate").status_code == 503


def test_database_failure_on_lookup_is_503_not_500(client, monkeypatch):
    from sqlalchemy.exc import OperationalError

    def boom(*a, **k):
        raise OperationalError("x", {}, Exception("db"))

    monkeypatch.setattr("app.api.v1.places._get_place", boom)

    assert client.get("/api/v1/places/1").status_code == 503
    assert client.post("/api/v1/places/1/activate").status_code == 503


def test_nearest_returns_the_closest_place_with_distance(client):
    # fixture places sit on lon 19.4: Łódź 51.75, Łódź Mała 50.0, Nowa Wieś 50.1 / 52.9
    resp = client.post("/api/v1/places/nearest", json={"latitude": 51.76, "longitude": 19.4})

    body = resp.json()
    assert resp.status_code == 200
    assert body["status"] == "found" and body["place"]["name"] == "Łódź"
    assert 0.9 < body["distance_km"] < 1.4
    assert resp.headers["cache-control"] == "no-store"
    assert "GeoNames" in body["attribution"]


def test_nearest_is_out_of_range_never_a_far_guess(client):
    resp = client.post("/api/v1/places/nearest", json={"latitude": 54.5, "longitude": 19.4})

    assert resp.json() == {
        "status": "out_of_range",
        "place": None,
        "distance_km": None,
        "attribution": resp.json()["attribution"],
    }


def test_nearest_rejects_invalid_coordinates(client):
    assert (
        client.post("/api/v1/places/nearest", json={"latitude": 91, "longitude": 0}).status_code
        == 422
    )
    assert client.post("/api/v1/places/nearest", json={"latitude": 51}).status_code == 422
