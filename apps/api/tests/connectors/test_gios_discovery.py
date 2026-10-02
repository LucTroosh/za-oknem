"""GIOŚ station catalog cache + area -> station assignment (ADR-025). The client is
mocked with the real `station/findAll` shape (Polish keys, coordinates as strings);
no live network."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from app.connectors.gios import client, discovery
from app.connectors.gios.parser import GiosParseError
from app.models import GeoArea, GiosStation, SourceFetch


def _st(sid, lat, lon, name="Stacja") -> dict:
    return {
        "Identyfikator stacji": sid,
        "Nazwa stacji": f"{name} {sid}",
        "WGS84 φ N": str(lat),
        "WGS84 λ E": str(lon),
        "Nazwa miasta": "Kłodzko",
    }


CATALOG = [_st(38, 50.433493, 16.65366), _st(114, 52.2297, 21.0122), _st(7, 50.0, 19.9)]


def _fetch(monkeypatch, stations):
    mock = MagicMock(return_value=stations)
    monkeypatch.setattr(client, "fetch_all_stations", mock)
    return mock


def _area(db, slug, lat, lon, active=True):
    db.add(
        GeoArea(slug=slug, name=slug, latitude=lat, longitude=lon, weather_polling_active=active)
    )
    db.commit()


def test_discover_stores_catalog_with_provenance(monkeypatch, db_session):
    _fetch(monkeypatch, CATALOG)
    now = datetime(2026, 10, 1, 12, tzinfo=UTC)

    assert discovery.discover_stations(db_session, now=now) == 3

    row = db_session.query(GiosStation).filter_by(station_id="38").one()
    assert (row.station_name, row.latitude, row.longitude) == ("Stacja 38", 50.433493, 16.65366)
    assert row.raw["Nazwa miasta"] == "Kłodzko"
    fetch = db_session.get(SourceFetch, row.source_fetch_id)
    assert fetch.source_id == "gios" and fetch.endpoint.endswith("/station/findAll")
    assert fetch.validation_status == "valid"


def test_discover_is_idempotent_updates_and_drops_unlisted(monkeypatch, db_session):
    _fetch(monkeypatch, CATALOG)
    discovery.discover_stations(db_session)
    _fetch(monkeypatch, [_st(38, 50.5, 16.7, name="Nowa"), _st(114, 52.2297, 21.0122)])

    discovery.discover_stations(db_session)

    rows = {r.station_id: r for r in db_session.query(GiosStation)}
    assert set(rows) == {"38", "114"}  # 7 no longer listed -> never assigned again
    assert rows["38"].station_name == "Nowa 38" and rows["38"].latitude == 50.5


def test_discover_rejects_bad_station_but_keeps_listed_old_row(monkeypatch, db_session):
    _fetch(monkeypatch, CATALOG)
    discovery.discover_stations(db_session)
    broken = {"Identyfikator stacji": 38, "Nazwa stacji": "x", "WGS84 φ N": "oops"}
    _fetch(monkeypatch, [broken, _st(114, 52.2297, 21.0122), _st(7, 91, 19.9)])  # 7: lat > 90

    discovery.discover_stations(db_session)

    rows = {r.station_id: r for r in db_session.query(GiosStation)}
    assert set(rows) == {"38", "7", "114"}  # listed-but-invalid keep the previous row
    assert rows["38"].latitude == 50.433493
    last = db_session.query(SourceFetch).order_by(SourceFetch.id.desc()).first()
    assert last.validation_status == "partial"


def test_discover_with_no_valid_station_raises_and_changes_nothing(monkeypatch, db_session):
    _fetch(monkeypatch, CATALOG)
    discovery.discover_stations(db_session)
    _fetch(monkeypatch, [{"Identyfikator stacji": 1}])

    with pytest.raises(GiosParseError):
        discovery.discover_stations(db_session)

    assert db_session.query(GiosStation).count() == 3
    assert db_session.query(SourceFetch).order_by(
        SourceFetch.id.desc()
    ).first().validation_status == ("invalid")


@pytest.fixture(autouse=True)
def _reset_backoff():
    discovery._last_failed_refresh = None
    yield
    discovery._last_failed_refresh = None


def test_ensure_catalog_refreshes_at_most_daily(monkeypatch, db_session):
    fetch = _fetch(monkeypatch, CATALOG)
    now = datetime(2026, 10, 1, 12, tzinfo=UTC)

    assert discovery.ensure_catalog(db_session, now=now) is True  # empty -> discover
    assert discovery.ensure_catalog(db_session, now=now + timedelta(hours=23)) is False
    assert fetch.call_count == 1
    assert discovery.ensure_catalog(db_session, now=now + timedelta(hours=25)) is True
    assert fetch.call_count == 2


def test_ensure_catalog_failure_uses_cache_but_raises_without_one(monkeypatch, db_session):
    monkeypatch.setattr(
        client, "fetch_all_stations", MagicMock(side_effect=client.GiosApiError("403"))
    )
    with pytest.raises(client.GiosApiError):
        discovery.ensure_catalog(db_session)  # nothing cached -> real failure

    _fetch(monkeypatch, CATALOG)
    now = datetime(2026, 10, 1, 12, tzinfo=UTC)
    discovery.ensure_catalog(db_session, now=now)
    monkeypatch.setattr(
        client, "fetch_all_stations", MagicMock(side_effect=client.GiosApiError("403"))
    )

    assert discovery.ensure_catalog(db_session, now=now + timedelta(days=3)) is False  # rule #1


def test_assigned_station_ids_nearest_per_active_area_deduplicated(monkeypatch, db_session):
    _fetch(monkeypatch, CATALOG)
    discovery.discover_stations(db_session)
    _area(db_session, "klodzko", 50.433493, 16.65366)
    _area(db_session, "klodzko-2", 50.45, 16.66)  # same nearest station -> one id
    _area(db_session, "warszawa", 52.23, 21.01)
    _area(db_session, "szczecin", 53.43, 14.55)  # nothing within 100 km -> no data
    _area(db_session, "inactive-krakow", 50.06, 19.94, active=False)  # not polled

    assert discovery.assigned_station_ids(db_session) == ["114", "38"]


def test_assigned_station_ids_covers_recent_place_refused_weather_polling(monkeypatch, db_session):
    # Open-Meteo capacity says no, air is still polled; an expired place (old request) is not.
    _fetch(monkeypatch, CATALOG)
    discovery.discover_stations(db_session)
    now = datetime.now(UTC)
    for slug, lat, lon, age in [("place-1", 50.433493, 16.65366, 1), ("place-2", 52.23, 21.01, 30)]:
        db_session.add(
            GeoArea(
                slug=slug, name=slug, latitude=lat, longitude=lon, place_id=int(slug[-1]),
                weather_polling_active=False, last_requested_at=now - timedelta(days=age),
            )
        )  # fmt: skip
    db_session.commit()

    assert discovery.assigned_station_ids(db_session) == ["38"]


def test_assigned_station_ids_reaches_the_regional_band(monkeypatch, db_session):
    # ADR-029: a station 50-100 km away is polled (so the regional band has data); one more
    # than 100 km away is not.
    _fetch(monkeypatch, [_st(71, 50.93, 16.65366), _st(72, 51.40, 16.65366)])  # ~55 / ~107 km
    discovery.discover_stations(db_session)
    _area(db_session, "klodzko", 50.433493, 16.65366)

    assert discovery.assigned_station_ids(db_session) == ["71"]  # 72 is out of range

    _area(db_session, "north", 52.2, 16.65366)  # ~89 km from 72, ~145 km from 71
    assert discovery.assigned_station_ids(db_session) == ["71", "72"]


def test_assigned_station_ids_is_stable_and_empty_without_catalog(monkeypatch, db_session):
    _area(db_session, "klodzko", 50.433493, 16.65366)
    assert discovery.assigned_station_ids(db_session) == []

    _fetch(monkeypatch, [_st(2, 50.5, 16.7), _st(10, 50.5, 16.7)])  # exact tie
    discovery.discover_stations(db_session)
    first = discovery.assigned_station_ids(db_session)

    # both are within the per-area fallback count; the order is stable (sorted ids)
    assert first == ["10", "2"] == discovery.assigned_station_ids(db_session)


def test_assigned_station_ids_polls_only_the_nearest_few_per_area(monkeypatch, db_session):
    _area(db_session, "klodzko", 50.433493, 16.65366)
    _fetch(monkeypatch, [_st(i, 50.43 + i * 0.01, 16.65) for i in range(1, 7)])
    discovery.discover_stations(db_session)

    assert len(discovery.assigned_station_ids(db_session)) == discovery.AIR_STATIONS_PER_AREA


def test_stations_by_id_returns_raw_dicts_in_requested_order(monkeypatch, db_session):
    _fetch(monkeypatch, CATALOG)
    discovery.discover_stations(db_session)

    got = discovery.stations_by_id(db_session, ["114", "38", "missing"])

    assert [s["Identyfikator stacji"] for s in got] == [114, 38]


def test_assignment_candidates_use_catalog_coordinates_and_drop_unlisted(monkeypatch, db_session):
    monkeypatch.delenv("GIOS_STATION_IDS", raising=False)
    measured = {sid: {"latitude": 1.0, "longitude": 2.0} for sid in ("38", "114", "gone", "env")}
    legacy = discovery.assignment_candidates(db_session, measured)
    assert len(legacy) == 4 and ("gone", 1.0, 2.0) in legacy  # no catalog -> no filtering

    _fetch(monkeypatch, CATALOG)
    discovery.discover_stations(db_session)
    monkeypatch.setenv("GIOS_STATION_IDS", "env,114")

    got = discovery.assignment_candidates(db_session, measured)

    assert sorted(got) == [
        ("114", 1.0, 2.0),  # override wins even though catalogued (catalog row may be stale)
        ("38", 50.433493, 16.65366),  # catalog coordinates, not the measured 1.0/2.0
        ("env", 1.0, 2.0),  # explicit override outside the catalog keeps measured coords
    ]


@pytest.mark.parametrize("bad_id", [None, "", "  ", True])
def test_discover_rejects_null_or_empty_station_id(monkeypatch, db_session, bad_id):
    _fetch(
        monkeypatch, [{**_st(1, 50.0, 16.0), "Identyfikator stacji": bad_id}, _st(38, 50.4, 16.6)]
    )

    assert discovery.discover_stations(db_session) == 1

    assert [r.station_id for r in db_session.query(GiosStation)] == ["38"]


def test_polling_expected_covers_env_assignment_and_empty_catalog_bootstrap(
    monkeypatch, db_session
):
    monkeypatch.delenv("GIOS_STATION_IDS", raising=False)
    assert discovery.polling_expected(db_session) is False  # nothing to serve

    _area(db_session, "szczecin", 53.43, 14.55)
    assert discovery.polling_expected(db_session) is True  # empty catalog, active area

    _fetch(monkeypatch, CATALOG)
    discovery.discover_stations(db_session)
    assert discovery.polling_expected(db_session) is False  # catalog known, nothing in range

    _area(db_session, "klodzko", 50.433493, 16.65366)
    assert discovery.polling_expected(db_session) is True

    monkeypatch.setenv("GIOS_STATION_IDS", "1")
    assert discovery.polling_expected(db_session) is True


def test_failed_refresh_with_cache_backs_off_for_a_day_then_retries(monkeypatch, db_session):
    _fetch(monkeypatch, CATALOG)
    now = datetime(2026, 10, 1, 12, tzinfo=UTC)
    discovery.ensure_catalog(db_session, now=now)
    failing = MagicMock(side_effect=client.GiosApiError("403"))
    monkeypatch.setattr(client, "fetch_all_stations", failing)

    late = now + timedelta(days=2)
    assert discovery.ensure_catalog(db_session, now=late) is False  # attempt 1 fails
    assert discovery.ensure_catalog(db_session, now=late + timedelta(hours=1)) is False
    assert discovery.ensure_catalog(db_session, now=late + timedelta(hours=23)) is False
    assert failing.call_count == 1  # no hourly re-walk during the outage

    assert discovery.ensure_catalog(db_session, now=late + timedelta(hours=25)) is False
    assert failing.call_count == 2  # one retry per day

    _fetch(monkeypatch, CATALOG)
    assert discovery.ensure_catalog(db_session, now=late + timedelta(hours=50)) is True


def test_failed_refresh_without_cache_is_retried_every_run(monkeypatch, db_session):
    failing = MagicMock(side_effect=client.GiosApiError("403"))
    monkeypatch.setattr(client, "fetch_all_stations", failing)
    now = datetime(2026, 10, 1, 12, tzinfo=UTC)

    for hours in (0, 1):
        with pytest.raises(client.GiosApiError):
            discovery.ensure_catalog(db_session, now=now + timedelta(hours=hours))

    assert failing.call_count == 2


@pytest.mark.parametrize("bad", ["NaN", "inf", "-inf"])
def test_discover_rejects_non_finite_coordinates(monkeypatch, db_session, bad):
    _fetch(monkeypatch, [{**_st(1, 50.0, 16.0), "WGS84 φ N": bad}, _st(38, 50.4, 16.6)])

    assert discovery.discover_stations(db_session) == 1


def test_discover_does_not_prune_when_catalog_suddenly_shrinks_a_lot(monkeypatch, db_session):
    _fetch(monkeypatch, CATALOG)
    discovery.discover_stations(db_session)
    _fetch(monkeypatch, [CATALOG[0]])  # 1 of 3 left, e.g. a truncated page walk

    discovery.discover_stations(db_session)

    assert db_session.query(GiosStation).count() == 3


def test_malformed_catalog_shape_keeps_the_cache(monkeypatch, db_session):
    _fetch(monkeypatch, CATALOG)
    now = datetime(2026, 10, 1, 12, tzinfo=UTC)
    discovery.ensure_catalog(db_session, now=now)
    monkeypatch.setattr(client, "fetch_all_stations", MagicMock(side_effect=TypeError("None")))

    assert discovery.ensure_catalog(db_session, now=now + timedelta(days=2)) is False
    assert db_session.query(GiosStation).count() == 3


def test_unmeasured_override_station_is_a_candidate_other_catalog_ones_are_not(
    monkeypatch, db_session
):
    _fetch(monkeypatch, CATALOG)
    discovery.discover_stations(db_session)
    monkeypatch.setenv("GIOS_STATION_IDS", "38")

    ids = [p[0] for p in discovery.assignment_candidates(db_session, {}, unmeasured=True)]

    assert ids == ["38"]


def test_unmeasured_catalog_stations_are_not_candidates_under_an_env_override(
    monkeypatch, db_session
):
    _fetch(monkeypatch, CATALOG)
    discovery.discover_stations(db_session)
    monkeypatch.setenv("GIOS_STATION_IDS", "38")
    measured = {"38": {"latitude": 50.433493, "longitude": 16.65366}}

    ids = [p[0] for p in discovery.assignment_candidates(db_session, measured, unmeasured=True)]

    assert ids == ["38"]
