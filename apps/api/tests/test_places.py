"""Places registry logic (ADR-029): normalisation, prefix search, activation policy
(capacity / budget), idle expiry. SQLite session; PostGIS is not involved."""

from datetime import UTC, datetime, timedelta

import pytest

import app.places as places
from app import scheduler
from app.connectors.open_meteo.ingest import ESTIMATED_BILLABLE_UNITS_PER_CALL
from app.models import GeoArea, Place, SourceFetchCounter
from app.places import (
    activate_place,
    expire_idle_areas,
    max_active_areas,
    normalize_name,
    place_label,
    search_places,
)

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Łódź", "lodz"),
        ("Bielsko-Biała", "bielsko biala"),
        ("  Nowy   Sącz ", "nowy sacz"),
        ("Świnoujście", "swinoujscie"),
        ("Żółć", "zolc"),
        ("St. O'Brien", "st o brien"),
        ("Gdańsk", "gdansk"),
        ("%_", ""),
        ("", ""),
    ],
)
def test_normalize_name(raw, expected):
    assert normalize_name(raw) == expected


def _place(db, name, *, pid=None, pop=None, lat=52.0, lon=21.0):
    p = Place(
        id=pid, name=name, normalized_name=normalize_name(name), kind="PPL", latitude=lat,
        longitude=lon, population=pop, source="geonames_pl",
        source_record_id=f"g{name}{pop}{lat}", imported_at=NOW,
    )  # fmt: skip
    db.add(p)
    db.commit()
    return p


def test_search_is_prefix_diacritics_insensitive_and_not_infix(db_session):
    _place(db_session, "Łódź", pop=700000)
    _place(db_session, "Nowa Łódź Mała")  # "lodz" occurs inside, not as a prefix

    assert [p.name for p in search_places(db_session, "LODZ", 10)] == ["Łódź"]
    assert [p.name for p in search_places(db_session, "łó", 10)] == ["Łódź"]
    assert search_places(db_session, "odz", 10) == []


def test_search_order_exact_match_then_population_then_name(db_session):
    _place(db_session, "Kalisz Pomorski", pop=4000)
    _place(db_session, "Kalisz", pop=100000)
    _place(db_session, "Kalisz", pop=900, lat=51.0)
    _place(db_session, "Kaliska", pop=9000000)  # biggest, but not an exact match

    names = [(p.name, p.population) for p in search_places(db_session, "kalisz", 10)]

    assert names == [
        ("Kalisz", 100000), ("Kalisz", 900), ("Kalisz Pomorski", 4000),
    ]  # fmt: skip
    # "kalis" is a prefix of everything, none exact: pure population order
    assert [p.name for p in search_places(db_session, "kalis", 10)][0] == "Kaliska"


def test_search_limit_and_degenerate_queries(db_session):
    for i in range(5):
        _place(db_session, f"Wola {i}")

    assert len(search_places(db_session, "wola", 3)) == 3
    assert search_places(db_session, "w", 10) == []  # < 2 characters
    assert search_places(db_session, "%%", 10) == []  # wildcard chars are not patterns
    assert search_places(db_session, "  ", 10) == []


def test_search_ties_are_deterministic(db_session):
    a = _place(db_session, "Brzeziny", lat=51.0)
    b = _place(db_session, "Brzeziny", lat=52.0)

    ids = [p.id for p in search_places(db_session, "brzez", 10)]

    assert ids == sorted([a.id, b.id])


# --- activation ------------------------------------------------------------------------


def test_activate_creates_the_area_once_and_starts_polling(db_session):
    place = _place(db_session, "Szklarska Poręba", lat=50.83, lon=15.52)

    area, polling = activate_place(db_session, place, now=NOW)
    again, polling2 = activate_place(db_session, place, now=NOW + timedelta(days=1))

    assert polling == polling2 == "active"
    assert again.id == area.id and db_session.query(GeoArea).count() == 1
    assert (area.slug, area.name, area.place_id) == (f"place-{place.id}", place.name, place.id)
    assert (area.latitude, area.longitude) == (50.83, 15.52)
    assert area.weather_polling_active is True
    assert area.last_requested_at.replace(tzinfo=UTC) == NOW + timedelta(days=1)  # refreshed


def test_activate_at_capacity_keeps_the_area_inactive_not_an_error(db_session, monkeypatch):
    monkeypatch.setattr(places, "max_active_areas", lambda: 1)
    db_session.add(GeoArea(slug="seed", name="Seed", latitude=1, longitude=1))  # counts: active
    db_session.commit()
    place = _place(db_session, "Wieś")

    area, polling = activate_place(db_session, place, now=NOW)

    assert polling == "capacity_reached"
    assert area.weather_polling_active is False and area.place_id == place.id
    assert area.last_requested_at is not None


def test_activate_when_budget_is_nearly_spent_does_not_add_load(db_session):
    db_session.add(SourceFetchCounter(source_id="open_meteo", day=NOW.date(), count=9_000))
    db_session.commit()
    place = _place(db_session, "Wieś")

    area, polling = activate_place(db_session, place, now=NOW)

    assert polling == "budget_exhausted" and area.weather_polling_active is False

    # yesterday's counter is irrelevant
    other = _place(db_session, "Inna", lat=51.0)
    db_session.query(SourceFetchCounter).update({"day": NOW.date() - timedelta(days=1)})
    db_session.commit()
    assert activate_place(db_session, other, now=NOW)[1] == "active"


def test_already_active_area_stays_active_even_when_over_capacity(db_session, monkeypatch):
    place = _place(db_session, "Wieś")
    activate_place(db_session, place, now=NOW)
    monkeypatch.setattr(places, "max_active_areas", lambda: 0)

    area, polling = activate_place(db_session, place, now=NOW + timedelta(hours=1))

    assert polling == "active" and area.weather_polling_active is True  # a refresh, not new load


def test_max_active_areas_follows_the_budget_formula():
    per_area = 8 * ESTIMATED_BILLABLE_UNITS_PER_CALL + 1  # 8 weather + 1 pollen call/day
    assert max_active_areas(10_000) == int(0.7 * 10_000 // per_area)
    assert max_active_areas(1_000_000) > max_active_areas(10_000) * 90  # plan upgrade = env only
    assert max_active_areas(1) == 0


def test_cycle_constants_match_the_scheduler():
    day = 24 * 60 * 60
    assert day / scheduler.OPEN_METEO_INTERVAL_SECONDS == places.WEATHER_CALLS_PER_AREA_PER_DAY
    assert (
        day / scheduler.OPEN_METEO_POLLEN_INTERVAL_SECONDS == places.POLLEN_CALLS_PER_AREA_PER_DAY
    )


# --- idle expiry -----------------------------------------------------------------------


def _area(db, slug, *, place_id=None, requested=None, active=True):
    a = GeoArea(
        slug=slug, name=slug, latitude=52, longitude=21, place_id=place_id,
        last_requested_at=requested, weather_polling_active=active,
    )  # fmt: skip
    db.add(a)
    db.commit()
    return a


def test_expire_idle_areas_only_touches_stale_place_areas(db_session):
    p1, p2, p3, p4 = (_place(db_session, f"P{i}", lat=50 + i / 10) for i in range(4))
    ttl = timedelta(days=7)
    stale = _area(db_session, "stale", place_id=p1.id, requested=NOW - ttl - timedelta(hours=1))
    edge = _area(db_session, "edge", place_id=p2.id, requested=NOW - ttl)  # exactly TTL: kept
    fresh = _area(db_session, "fresh", place_id=p3.id, requested=NOW - timedelta(days=1))
    never = _area(db_session, "never", place_id=p4.id, requested=None)
    seed = _area(db_session, "seed-city")  # no place_id: never expires here
    off = _area(db_session, "off", requested=None, active=False)

    expired = expire_idle_areas(db_session, now=NOW, ttl_days=7)
    for a in (stale, edge, fresh, never, seed, off):
        db_session.refresh(a)

    assert expired == 2
    assert [a.weather_polling_active for a in (stale, edge, fresh, never, seed, off)] == [
        False, True, True, False, True, False,
    ]  # fmt: skip


def test_expired_area_can_be_activated_again(db_session):
    place = _place(db_session, "Wieś")
    area, _ = activate_place(db_session, place, now=NOW - timedelta(days=30))
    assert expire_idle_areas(db_session, now=NOW, ttl_days=7) == 1

    again, polling = activate_place(db_session, place, now=NOW)

    assert polling == "active" and again.id == area.id


@pytest.mark.parametrize(
    ("name", "a1", "a2", "label"),
    [
        ("Nowa Wieś", "Silesia", "Powiat gliwicki", "Nowa Wieś, pow. gliwicki, woj. śląskie"),
        ("Gliwice", "Silesia", "Gliwice", "Gliwice, woj. śląskie"),  # city powiat not repeated
        ("Łódź", "Łódź Voivodeship", None, "Łódź, woj. łódzkie"),
        ("Wieś", "Lublin", "Powiat lubelski", "Wieś, pow. lubelski, woj. lubelskie"),
        ("Wieś", "Nowa Kraina", None, "Wieś, woj. Nowa Kraina"),  # unknown: as GeoNames has it
        ("Wieś", None, None, "Wieś"),
    ],
)
def test_place_label(name, a1, a2, label):
    p = Place(name=name, admin1_name=a1, admin2_name=a2)

    assert place_label(p) == label


def test_every_geonames_voivodeship_has_a_polish_name():
    assert len(places.VOIVODESHIP_PL) == 16
