"""Pollen calendar (ADR-023): data-file validation, active/upcoming selection at boundary
dates, the endpoint contract, and no network access. No DB involved (static reference data)."""

import json
import socket
from datetime import date

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.pollen_calendar import (
    DATA_FILE,
    UPCOMING_DAYS,
    PollenCalendar,
    load_calendar,
    point_end,
    point_of,
    select,
)

client = TestClient(app)


def _active(d: date) -> dict[str, str]:
    return {a.key: a.phase for a in select(load_calendar(), d)[0]}


def _upcoming(d: date) -> dict[str, int]:
    return {u.key: u.days_until for u in select(load_calendar(), d)[1]}


# --- data file -------------------------------------------------------------------------


def test_data_file_valid_and_every_taxon_has_source():
    cal = load_calendar()
    assert cal.kind == "seasonal_calendar" and cal.valid_for_region == "PL"
    assert cal.attribution and cal.disclaimer and cal.reviewed_at
    keys = [t.key for t in cal.taxa]
    assert len(keys) == len(set(keys))
    for t in cal.taxa:
        assert t.source_ids and all(s in cal.sources for s in t.source_ids)


def test_keys_consistent_with_pollen_snapshots():
    from app.api.v1.pollen import SPECIES

    keys = {t.key for t in load_calendar().taxa} | {n.key for n in load_calendar().not_covered}
    # every MVP species is either covered with the SAME key or explicitly listed as not covered
    assert set(SPECIES) <= keys


def _raw() -> dict:
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def test_validation_rejects_bad_data():
    raw = _raw()
    raw["taxa"][0]["season"] = {"start": [5, 1], "end": [2, 1]}  # reversed / wraps year
    with pytest.raises(ValidationError):
        PollenCalendar.model_validate(raw)

    raw = _raw()
    raw["taxa"][0]["peak"] = {"start": [12, 1], "end": [12, 2]}  # peak outside season
    with pytest.raises(ValidationError):
        PollenCalendar.model_validate(raw)

    raw = _raw()
    raw["taxa"][0]["season"]["start"] = [13, 1]  # bad month
    with pytest.raises(ValidationError):
        PollenCalendar.model_validate(raw)

    raw = _raw()
    raw["taxa"][1]["key"] = raw["taxa"][0]["key"]  # duplicate key
    with pytest.raises(ValidationError):
        PollenCalendar.model_validate(raw)

    raw = _raw()
    raw["taxa"][0]["source_ids"] = []  # no source
    with pytest.raises(ValidationError):
        PollenCalendar.model_validate(raw)

    raw = _raw()
    raw["taxa"][0]["source_ids"] = ["nope"]  # unknown source
    with pytest.raises(ValidationError):
        PollenCalendar.model_validate(raw)


# --- decades ---------------------------------------------------------------------------


def test_point_of_decades():
    assert point_of(date(2026, 1, 1)) == (1, 1)
    assert point_of(date(2026, 3, 10)) == (3, 1)
    assert point_of(date(2026, 3, 11)) == (3, 2)
    assert point_of(date(2026, 3, 20)) == (3, 2)
    assert point_of(date(2026, 3, 21)) == (3, 3)
    assert point_of(date(2026, 3, 31)) == (3, 3)  # day 31 stays in decade 3
    assert point_of(date(2028, 2, 29)) == (2, 3)  # leap day
    assert point_of(date(2026, 12, 31)) == (12, 3)


def test_point_end_handles_short_months_and_leap_year():
    assert point_end(2027, (2, 3)) == date(2027, 2, 28)
    assert point_end(2028, (2, 3)) == date(2028, 2, 29)
    assert point_end(2026, (4, 1)) == date(2026, 4, 10)
    assert point_end(2026, (3, 3)) == date(2026, 3, 31)


# --- selection at boundaries -----------------------------------------------------------


def test_new_year_nothing_active_nothing_upcoming():
    assert _active(date(2026, 1, 1)) == {}
    assert _upcoming(date(2026, 1, 1)) == {}  # earliest start is mid-February (> 30 days)


def test_late_january_upcoming_spans_into_february():
    up = _upcoming(date(2026, 1, 20))  # hazel/alder start 11 Feb = 22 days
    assert up == {"hazel": 22, "alder": 22}


def test_year_end_nothing_active_and_next_year_starts_beyond_horizon():
    assert _active(date(2026, 12, 31)) == {}
    assert _upcoming(date(2026, 12, 31)) == {}


def test_year_rollover_uses_next_year_start():
    # Pretend a taxon starts 11 Jan: from 20 Dec the next start is in the NEXT year.
    raw = _raw()
    t = raw["taxa"][0]
    t["season"] = {"start": [1, 2], "end": [3, 1]}
    t["peak"] = {"start": [2, 1], "end": [2, 2]}
    cal = PollenCalendar.model_validate(raw)
    up = {u.key: u.days_until for u in select(cal, date(2026, 12, 20))[1]}
    assert up[t["key"]] == 22  # 20 Dec -> 11 Jan


def test_decade_boundaries():
    # hazel season 2/2 .. 4/1 (11 Feb .. 10 Apr)
    assert "hazel" not in _active(date(2026, 2, 10))
    assert _upcoming(date(2026, 2, 10))["hazel"] == 1
    assert _active(date(2026, 2, 11))["hazel"] == "start"
    assert _active(date(2026, 4, 10))["hazel"] == "end"
    assert "hazel" not in _active(date(2026, 4, 11))


def test_phase_start_peak_end():
    # hazel peak 1 Mar .. 31 Mar
    assert _active(date(2026, 2, 28))["hazel"] == "start"
    assert _active(date(2026, 3, 1))["hazel"] == "peak"
    assert _active(date(2026, 3, 31))["hazel"] == "peak"
    assert _active(date(2026, 4, 1))["hazel"] == "end"


def test_leap_day():
    on = select(load_calendar(), date(2028, 2, 29))
    assert {a.key for a in on[0]} == {"hazel", "alder"}
    hazel = next(a for a in on[0] if a.key == "hazel")
    assert hazel.season_start == date(2028, 2, 11)
    assert {a.key for a in select(load_calendar(), date(2028, 2, 28))[0]} == {"hazel", "alder"}
    assert "mugwort" in _upcoming(date(2028, 6, 25))  # leap year does not shift July starts


def test_active_taxon_not_in_upcoming_and_upcoming_within_horizon():
    for month in range(1, 13):
        d = date(2026, month, 15)
        active, upcoming = select(load_calendar(), d)
        assert not {a.key for a in active} & {u.key for u in upcoming}
        assert all(0 < u.days_until <= UPCOMING_DAYS for u in upcoming)
        assert [u.days_until for u in upcoming] == sorted(u.days_until for u in upcoming)


def test_mid_august_mugwort_peak():
    assert _active(date(2026, 8, 5))["mugwort"] == "peak"
    assert _active(date(2026, 8, 25))["mugwort"] == "end"


# --- endpoint --------------------------------------------------------------------------


def test_endpoint_explicit_date():
    r = client.get("/api/v1/pollen/calendar", params={"date": "2026-03-15"})
    assert r.status_code == 200
    body = r.json()
    assert body["kind"] == "seasonal_calendar"
    assert body["date"] == "2026-03-15"
    assert {a["key"] for a in body["active"]} == {"hazel", "alder"}
    assert all(a["peak"] for a in body["active"]) and all(
        a["phase"] == "peak" for a in body["active"]
    )
    up = {u["key"]: u["days_until"] for u in body["upcoming"]}
    assert up["birch"] == 17  # starts 1 Apr
    assert [u["days_until"] for u in body["upcoming"]] == sorted(up.values())
    assert body["attribution"] and body["disclaimer"] and body["reviewed_at"]
    assert body["upcoming_within_days"] == UPCOMING_DAYS
    assert body["not_covered"]
    assert all(s in body["sources"] for a in body["active"] for s in a["source_ids"])


def test_endpoint_default_date_is_today_in_warsaw(monkeypatch):
    import app.api.v1.pollen_calendar as mod

    class FakeDatetime:
        @staticmethod
        def now(tz):
            from datetime import datetime

            return datetime(2026, 12, 31, 23, 30, tzinfo=tz)  # 31 Dec UTC 23:30 = 1 Jan Warsaw

    monkeypatch.setattr(mod, "datetime", FakeDatetime)
    r = client.get("/api/v1/pollen/calendar")
    assert r.status_code == 200
    assert r.json()["date"] == "2027-01-01"


@pytest.mark.parametrize(
    "bad", ["2026-02-30", "2026-13-01", "abc", "26-01-01", "1999-01-01", "2101-01-01"]
)
def test_endpoint_bad_date_422(bad):
    assert client.get("/api/v1/pollen/calendar", params={"date": bad}).status_code == 422


def test_endpoint_makes_no_network_calls(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "create_connection", boom)
    monkeypatch.setattr(socket.socket, "connect", boom)
    assert client.get("/api/v1/pollen/calendar", params={"date": "2026-07-20"}).status_code == 200
