"""GIOŚ station catalog cache + area -> station assignment (ADR-024). The client is
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
    _area(db_session, "szczecin", 53.43, 14.55)  # nothing within 50 km -> no data
    _area(db_session, "inactive-krakow", 50.06, 19.94, active=False)  # not polled

    assert discovery.assigned_station_ids(db_session) == ["114", "38"]


def test_assigned_station_ids_is_stable_and_empty_without_catalog(monkeypatch, db_session):
    _area(db_session, "klodzko", 50.433493, 16.65366)
    assert discovery.assigned_station_ids(db_session) == []

    _fetch(monkeypatch, [_st(2, 50.5, 16.7), _st(10, 50.5, 16.7)])  # exact tie
    discovery.discover_stations(db_session)
    first = discovery.assigned_station_ids(db_session)

    assert first == ["2"] == discovery.assigned_station_ids(db_session)


def test_stations_by_id_returns_raw_dicts_in_requested_order(monkeypatch, db_session):
    _fetch(monkeypatch, CATALOG)
    discovery.discover_stations(db_session)

    got = discovery.stations_by_id(db_session, ["114", "38", "missing"])

    assert [s["Identyfikator stacji"] for s in got] == [114, 38]
