"""GET /api/v1/air/history (GIOS-03b): the last hours of one parameter at the area's air station,
from our DB only. Hourly measurements; holes are reported, never interpolated; "no station" and
"no data" are different answers."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.air import GAP_AFTER, history_gaps
from app.db import Base, get_db
from app.main import app
from app.models import GeoArea, Measurement

AREA = (50.3, 18.7)  # Gliwice-ish
NEAR = (50.31, 18.68)  # ~2 km away


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def area(db_session):
    a = GeoArea(slug="gliwice", name="Gliwice", latitude=AREA[0], longitude=AREA[1])
    db_session.add(a)
    db_session.commit()
    return a


def hours_ago(h: float) -> datetime:
    return datetime.now(UTC).replace(microsecond=0) - timedelta(hours=h)


def reading(db, hours, value, *, param="PM2.5", station="114", pos=NEAR, source="gios", sensor="1"):
    when = hours_ago(hours)
    db.add(Measurement(
        source_id=source,
        source_record_id=f"{source}:{station}:{sensor}:{param}:{when.isoformat()}",
        station_id=station, station_name=f"Stacja {station}", latitude=pos[0], longitude=pos[1],
        param_code=param, value=value, unit="µg/m³", observed_at=when, fetched_at=when,
    ))  # fmt: skip
    db.commit()


def history(client, area, **params):
    r = client.get("/api/v1/air/history", params={"geo_area_id": area.id, **params})
    assert r.status_code == 200, r.text
    return r.json()


def test_the_last_hours_come_back_oldest_first_with_the_station_and_its_distance(
    db_session, client, area
):
    for h, v in [(4, 10.0), (3, 12.5), (2, 14.0), (1, 13.0), (0.2, 11.5)]:
        reading(db_session, h, v)
    body = history(client, area, hours=24)
    assert body["kind"] == "measurement_history" and body["availability"] == "available"
    assert [p["value"] for p in body["points"]] == [10.0, 12.5, 14.0, 13.0, 11.5]
    assert body["unit"] == "µg/m³" and body["param"] == "PM2.5" and body["interval_minutes"] == 60
    st = body["station"]
    assert st["station_id"] == "114" and st["station_name"] == "Stacja 114"
    assert st["coverage"] == "exact" and st["distance_km"] < 5
    assert body["gaps"] == []
    assert (
        body["latest_freshness"] == "FRESH"
        and body["latest_observed_at"] == body["points"][-1]["observed_at"]
    )
    assert body["attribution"] == "Źródło danych: GIOŚ - EKOINFONET"


def test_a_missing_hour_is_a_reported_gap_not_an_interpolated_line(db_session, client, area):
    for h in (6, 5, 2, 1):  # 4 and 3 never arrived
        reading(db_session, h, 10.0)
    body = history(client, area)
    assert len(body["points"]) == 4  # nothing invented between 5 h and 2 h ago
    (gap,) = body["gaps"]
    assert gap["missing_hours"] == 2
    assert (
        gap["after"] == body["points"][1]["observed_at"]
        and gap["before"] == body["points"][2]["observed_at"]
    )


def test_the_window_cuts_older_readings(db_session, client, area):
    for h in (30, 5, 1):
        reading(db_session, h, 9.0)
    assert len(history(client, area, hours=24)["points"]) == 2
    assert len(history(client, area, hours=3)["points"]) == 1


def test_only_the_requested_parameter_and_only_gios_readings_count(db_session, client, area):
    reading(db_session, 2, 10.0, param="PM2.5")
    reading(db_session, 2, 33.0, param="PM10")
    reading(db_session, 1, 99.0, source="imgw_hydro")  # a river gauge is not an air reading
    assert [p["value"] for p in history(client, area, param="PM2.5")["points"]] == [10.0]
    assert [p["value"] for p in history(client, area, param="PM10")["points"]] == [33.0]


def test_a_parameter_the_station_does_not_report_is_no_data_not_a_zero(db_session, client, area):
    reading(db_session, 2, 10.0, param="PM2.5")
    body = history(client, area, param="O3")
    assert body["availability"] == "no_data" and body["points"] == [] and body["gaps"] == []
    assert body["station"]["station_id"] == "114"  # the station is known, it just has no O3
    assert body["latest_observed_at"] is None and body["latest_freshness"] is None


def test_without_any_station_in_range_the_answer_is_no_station(db_session, client, area):
    assert history(client, area)["availability"] == "no_station"  # nothing ingested at all
    reading(db_session, 1, 10.0, station="9", pos=(52.2, 21.0))  # Warsaw: > 100 km away
    body = history(client, area)
    assert body["availability"] == "no_station" and body["station"] is None and body["points"] == []


def test_two_sensors_of_one_parameter_do_not_double_a_point(db_session, client, area):
    reading(db_session, 2, 10.0, sensor="1")
    reading(db_session, 2, 99.0, sensor="2")  # same station, same hour, another sensor
    assert len(history(client, area)["points"]) == 1


def test_an_old_last_reading_says_so(db_session, client, area):
    reading(db_session, 20, 10.0)
    body = history(client, area, hours=48)
    assert body["latest_freshness"] == "STALE"  # shown as old, never as current


def test_unknown_area_is_404_and_bad_parameters_are_rejected(client, area):
    assert client.get("/api/v1/air/history", params={"geo_area_id": 99999}).status_code == 404
    for bad in ({"param": "XYZ"}, {"hours": 0}, {"hours": 169}):
        r = client.get("/api/v1/air/history", params={"geo_area_id": area.id, **bad})
        assert r.status_code == 422, bad
    assert client.get("/api/v1/air/history").status_code == 422  # the area is required


def test_history_gaps_threshold_and_size():
    t0 = datetime(2026, 10, 3, 10, tzinfo=UTC)
    even = [t0 + timedelta(hours=i) for i in range(4)]
    assert history_gaps(even) == []
    assert history_gaps([t0, t0 + GAP_AFTER]) == []  # exactly 1.5 intervals is not yet a gap
    (g,) = history_gaps([t0, t0 + timedelta(hours=3)])
    assert g["missing_hours"] == 2
