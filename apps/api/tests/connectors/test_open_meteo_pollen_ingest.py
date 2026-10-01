"""Ingest tests (SQLite db_session): store/dedupe/failure isolation, provenance,
budget counter, total-failure signalling, CLI. Payload is the docs-derived fixture
from the parser tests."""

import sys
from copy import deepcopy
from datetime import UTC, datetime
from unittest.mock import MagicMock

import httpx
import pytest

from app import provenance
from app.connectors.open_meteo_pollen import client, ingest
from app.connectors.open_meteo_pollen.parser import PARSER_VERSION
from app.models import GeoArea, PollenSnapshot, SourceFetch, SourceFetchCounter, SourceStatus

UNIT = "grains/m³"
VARS = ("alder_pollen", "birch_pollen", "grass_pollen", "mugwort_pollen", "ragweed_pollen")
# FIXTURE (docs-derived, same as the parser tests) - not a recorded live response.
PAYLOAD = {
    "utc_offset_seconds": 0,
    "timezone": "UTC",
    "hourly_units": {"time": "iso8601", **dict.fromkeys(VARS, UNIT)},
    "hourly": {
        "time": ["2026-05-04T00:00", "2026-05-04T01:00", "2026-05-04T02:00"],
        "alder_pollen": [0.0, 0.4, None],
        "birch_pollen": [12.5, 13.0, 14.25],
        "grass_pollen": [None, None, None],
        "mugwort_pollen": [0.0, 0.0, 0.0],
        "ragweed_pollen": [None, 1, 2],
    },
}
HOURS = len(PAYLOAD["hourly"]["time"])


def _area(db, slug="klodzko") -> GeoArea:
    area = GeoArea(slug=slug, name=slug, latitude=50.43, longitude=16.65)
    db.add(area)
    db.commit()
    db.refresh(area)
    return area


def _patch_fetch(monkeypatch, result):
    mock = (
        MagicMock(side_effect=result)
        if isinstance(result, Exception)
        else MagicMock(return_value=result)
    )
    monkeypatch.setattr(client, "fetch_pollen", mock)
    return mock


def test_stores_one_row_per_hour_with_explicit_nulls(db_session, monkeypatch):
    area = _area(db_session)
    _patch_fetch(monkeypatch, PAYLOAD)

    assert ingest.ingest_geo_area(area, db_session) is True

    rows = db_session.query(PollenSnapshot).order_by(PollenSnapshot.valid_at).all()
    assert len(rows) == HOURS
    assert rows[0].alder == 0.0 and rows[0].grass is None
    assert rows[2].birch == 14.25 and rows[2].alder is None


def test_rerun_same_cycle_is_idempotent(db_session, monkeypatch):
    area = _area(db_session)
    _patch_fetch(monkeypatch, PAYLOAD)

    ingest.ingest_geo_area(area, db_session)
    assert ingest.ingest_geo_area(area, db_session) is True  # success, nothing new

    assert db_session.query(PollenSnapshot).count() == HOURS


def test_later_fetch_same_day_replaces_values_and_adds_new_hours(db_session, monkeypatch):
    """Codex: a fetch before the morning CAMS update followed by one after it lands on
    the same UTC-day bucket - the newer numbers must win, not be discarded."""
    area = _area(db_session)
    _patch_fetch(monkeypatch, PAYLOAD)
    ingest.ingest_geo_area(area, db_session)

    updated = deepcopy(PAYLOAD)
    updated["hourly"]["time"].append("2026-05-04T03:00")
    for variable in VARS:
        updated["hourly"][variable] = [*updated["hourly"][variable], 1.0]
    updated["hourly"]["birch_pollen"][0] = 99.0
    updated["hourly"]["grass_pollen"][0] = 7.0  # was null
    _patch_fetch(monkeypatch, updated)
    assert ingest.ingest_geo_area(area, db_session) is True

    rows = db_session.query(PollenSnapshot).order_by(PollenSnapshot.valid_at).all()
    assert len(rows) == HOURS + 1
    assert rows[0].birch == 99.0 and rows[0].grass == 7.0
    assert {r.fetched_at for r in rows[:HOURS]} == {rows[HOURS].fetched_at}


def test_later_fetch_same_day_drops_hours_the_newer_payload_omits(db_session, monkeypatch):
    area = _area(db_session)
    other = _area(db_session, "warszawa")
    _patch_fetch(monkeypatch, PAYLOAD)
    ingest.ingest_geo_area(area, db_session)
    ingest.ingest_geo_area(other, db_session)

    shorter = deepcopy(PAYLOAD)
    shorter["hourly"]["time"] = shorter["hourly"]["time"][:1]
    for variable in VARS:
        shorter["hourly"][variable] = shorter["hourly"][variable][:1]
    _patch_fetch(monkeypatch, shorter)
    assert ingest.ingest_geo_area(area, db_session) is True

    mine = db_session.query(PollenSnapshot).filter_by(geo_area_id=area.id).count()
    theirs = db_session.query(PollenSnapshot).filter_by(geo_area_id=other.id).count()
    assert (mine, theirs) == (1, HOURS)  # other areas' rows untouched


def test_fetch_failure_is_isolated(db_session, monkeypatch):
    area = _area(db_session)
    _patch_fetch(monkeypatch, client.OpenMeteoPollenApiError("boom"))

    assert ingest.ingest_geo_area(area, db_session) is False
    assert db_session.query(PollenSnapshot).count() == 0
    assert db_session.query(SourceFetch).count() == 0


def test_parse_failure_keeps_payload_as_invalid(db_session, monkeypatch):
    area = _area(db_session)
    bad = {"bad": "shape"}
    _patch_fetch(monkeypatch, bad)

    assert ingest.ingest_geo_area(area, db_session) is False

    fetch = db_session.query(SourceFetch).one()
    assert fetch.payload == bad
    assert fetch.validation_status == provenance.INVALID
    assert db_session.query(PollenSnapshot).count() == 0


class TestProvenance:
    def test_rows_link_to_the_raw_fetch(self, db_session, monkeypatch):
        area = _area(db_session)
        _patch_fetch(monkeypatch, PAYLOAD)

        ingest.ingest_geo_area(area, db_session)

        fetch = db_session.query(SourceFetch).one()
        assert fetch.source_id == "open_meteo_pollen"
        assert fetch.endpoint.startswith(client.BASE_URL)
        assert "latitude=50.43" in fetch.endpoint
        assert fetch.payload == PAYLOAD
        assert fetch.parser_version == PARSER_VERSION
        assert fetch.validation_status == provenance.VALID
        assert {r.source_fetch_id for r in db_session.query(PollenSnapshot)} == {fetch.id}

    def test_refetch_in_the_same_bucket_relinks_to_the_newer_payload(self, db_session, monkeypatch):
        area = _area(db_session)
        _patch_fetch(monkeypatch, PAYLOAD)

        ingest.ingest_geo_area(area, db_session)
        ingest.ingest_geo_area(area, db_session)

        newest = db_session.query(SourceFetch).order_by(SourceFetch.id.desc()).first()
        assert {r.source_fetch_id for r in db_session.query(PollenSnapshot)} == {newest.id}

    def test_payload_survives_a_parser_crash_as_pending(self, db_session, monkeypatch):
        area = _area(db_session)
        _patch_fetch(monkeypatch, PAYLOAD)
        monkeypatch.setattr(ingest, "normalize", MagicMock(side_effect=RuntimeError("bug")))

        with pytest.raises(RuntimeError):
            ingest.ingest_geo_area(area, db_session)

        fetch = db_session.query(SourceFetch).one()
        assert fetch.payload == PAYLOAD
        assert fetch.validation_status == provenance.PENDING

    def test_provenance_failure_does_not_block_rows(self, db_session, monkeypatch):
        area = _area(db_session)
        _patch_fetch(monkeypatch, PAYLOAD)
        monkeypatch.setattr(provenance, "record_fetch", MagicMock(return_value=None))

        assert ingest.ingest_geo_area(area, db_session) is True
        assert {r.source_fetch_id for r in db_session.query(PollenSnapshot)} == {None}


class TestBudget:
    def test_counts_against_the_shared_open_meteo_counter(self, db_session, monkeypatch):
        area = _area(db_session)
        real_get = MagicMock(return_value=MagicMock(json=lambda: PAYLOAD))
        monkeypatch.setattr(client.httpx, "get", real_get)

        ingest.ingest_geo_area(area, db_session)

        row = db_session.query(SourceFetchCounter).one()
        assert row.source_id == "open_meteo"
        assert row.count == ingest.UNITS_PER_CALL == 1

    def test_retry_counts_every_real_attempt(self, db_session, monkeypatch):
        area = _area(db_session)
        monkeypatch.setattr(client.httpx, "get", MagicMock(side_effect=httpx.RequestError("down")))

        assert ingest.ingest_geo_area(area, db_session) is False
        assert db_session.query(SourceFetchCounter).one().count == 2


class TestIngestAreas:
    def test_no_areas_is_not_a_success(self, db_session):
        assert ingest.ingest_areas([], db_session) is None

    def test_total_failure_raises(self, db_session, monkeypatch):
        areas = [_area(db_session, "a"), _area(db_session, "b")]
        _patch_fetch(monkeypatch, client.OpenMeteoPollenApiError("down"))
        with pytest.raises(RuntimeError, match="all 2"):
            ingest.ingest_areas(areas, db_session)

    def test_all_payloads_rejected_is_total_failure(self, db_session, monkeypatch):
        areas = [_area(db_session)]
        _patch_fetch(monkeypatch, {"bad": "shape"})
        with pytest.raises(RuntimeError):
            ingest.ingest_areas(areas, db_session)

    def test_partial_failure_is_success_and_isolated(self, db_session, monkeypatch):
        good, bad = _area(db_session, "good"), _area(db_session, "bad")
        results = iter([client.OpenMeteoPollenApiError("x"), PAYLOAD])

        def _fetch(lat, lon, on_attempt=None):
            r = next(results)
            if isinstance(r, Exception):
                raise r
            return r

        monkeypatch.setattr(client, "fetch_pollen", _fetch)

        assert ingest.ingest_areas([bad, good], db_session) is True
        assert {r.geo_area_id for r in db_session.query(PollenSnapshot)} == {good.id}


class TestMain:
    def test_no_matching_areas_exits(self, monkeypatch, capsys, db_session):
        monkeypatch.setattr(sys, "argv", ["ingest"])
        monkeypatch.setattr(ingest, "SessionLocal", lambda: db_session)
        with pytest.raises(SystemExit) as exc:
            ingest.main()
        assert exc.value.code == 1

    def test_success_records_source_status(self, monkeypatch, db_session):
        _area(db_session)
        monkeypatch.setattr(sys, "argv", ["ingest"])
        monkeypatch.setattr(ingest, "SessionLocal", lambda: db_session)
        monkeypatch.setattr(db_session, "close", lambda: None)
        _patch_fetch(monkeypatch, PAYLOAD)

        ingest.main()

        status = db_session.get(SourceStatus, "open_meteo_pollen")
        assert status.last_success_at is not None and status.last_error is None

    def test_total_failure_records_failure_and_raises(self, monkeypatch, db_session):
        _area(db_session)
        monkeypatch.setattr(sys, "argv", ["ingest"])
        monkeypatch.setattr(ingest, "SessionLocal", lambda: db_session)
        monkeypatch.setattr(db_session, "close", lambda: None)
        _patch_fetch(monkeypatch, client.OpenMeteoPollenApiError("down"))

        with pytest.raises(RuntimeError):
            ingest.main()

        status = db_session.get(SourceStatus, "open_meteo_pollen")
        assert status.last_success_at is None
        assert "RuntimeError" in status.last_error


def test_fetched_at_is_recent(db_session, monkeypatch):
    area = _area(db_session)
    _patch_fetch(monkeypatch, PAYLOAD)
    ingest.ingest_geo_area(area, db_session)
    row = db_session.query(PollenSnapshot).first()
    fetched = row.fetched_at.replace(tzinfo=UTC)
    assert (datetime.now(UTC) - fetched).total_seconds() < 5
