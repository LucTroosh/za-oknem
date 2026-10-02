"""Tests for imgw_hydro.ingest: store/skip/dedupe/failure-isolation, using the
SQLite db_session fixture."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from app import provenance
from app.connectors.imgw_hydro import client, ingest
from app.connectors.imgw_hydro.parser import PARSER_VERSION, ImgwHydroParseError
from app.models import Measurement, SourceFetch, SourceStatus

STATION = {
    "id_stacji": "151140030",
    "stacja": "Przewoźniki",
    "rzeka": "Skroda",
    "lat": "51.5253",
    "lon": "14.8217",
    "stan_wody": "225",
    "stan_wody_data_pomiaru": "2026-09-27 21:20:00",
    # IMGW always includes these keys, null when a station has no threshold
    # (e.g. lake gauges) - verified live, see parser.py. A station missing the
    # keys entirely is a different, malformed case (see test_imgw_hydro_parser.py).
    "stan_ostrzegawczy": None,
    "stan_alarmowy": None,
}


def test_ingest_station_stores_new_reading(db_session):
    stored = ingest.ingest_station(STATION, db_session, fetched_at=datetime.now(UTC))

    assert stored == 1
    assert db_session.query(Measurement).count() == 1


def test_ingest_station_stores_thresholds_too(db_session):
    station = {**STATION, "stan_ostrzegawczy": "300", "stan_alarmowy": "340"}
    stored = ingest.ingest_station(station, db_session, fetched_at=datetime.now(UTC))

    assert stored == 3
    assert db_session.query(Measurement).count() == 3


def test_ingest_station_skips_duplicate(db_session):
    ingest.ingest_station(STATION, db_session, fetched_at=datetime.now(UTC))
    stored_again = ingest.ingest_station(STATION, db_session, fetched_at=datetime.now(UTC))

    assert stored_again == 0
    assert db_session.query(Measurement).count() == 1


def test_ingest_station_skips_when_no_current_reading(db_session):
    station = {**STATION, "stan_wody": None}
    stored = ingest.ingest_station(station, db_session, fetched_at=datetime.now(UTC))

    assert stored == 0
    assert db_session.query(Measurement).count() == 0


def test_ingest_station_isolates_parse_failure(db_session, monkeypatch):
    monkeypatch.setattr(ingest, "normalize", MagicMock(side_effect=ImgwHydroParseError("boom")))
    stored = ingest.ingest_station(STATION, db_session, fetched_at=datetime.now(UTC))

    assert stored == 0
    assert db_session.query(Measurement).count() == 0


def test_ingest_station_updates_threshold_even_without_a_new_water_reading(db_session):
    """A station can keep the same stan_wody_data_pomiaru (stalled reading) while
    its threshold changes - thresholds are upserted by their own stable identity,
    not gated on a new water-level observed_at (Codex review, PR #42 round 3:
    the earlier observed_at-matching approach would have silently kept the old
    threshold value in this exact case)."""
    station = {**STATION, "stan_ostrzegawczy": "300"}
    ingest.ingest_station(station, db_session, fetched_at=datetime.now(UTC))

    changed_station = {**station, "stan_ostrzegawczy": "310"}
    stored = ingest.ingest_station(changed_station, db_session, fetched_at=datetime.now(UTC))

    assert stored == 1  # the threshold changed; the water level didn't
    row = db_session.query(Measurement).filter_by(param_code="water_level_warn_cm").one()
    assert row.value == 310.0


def test_ingest_station_deletes_threshold_when_withdrawn(db_session):
    """IMGW can stop reporting a threshold for a station (goes null) even while
    the same water-level reading persists - the stored row must be removed, not
    left behind as a stale "latest" value."""
    station = {**STATION, "stan_ostrzegawczy": "300"}
    ingest.ingest_station(station, db_session, fetched_at=datetime.now(UTC))
    assert db_session.query(Measurement).filter_by(param_code="water_level_warn_cm").count() == 1

    withdrawn_station = {**station, "stan_ostrzegawczy": None}
    ingest.ingest_station(withdrawn_station, db_session, fetched_at=datetime.now(UTC))

    assert db_session.query(Measurement).filter_by(param_code="water_level_warn_cm").count() == 0


def test_ingest_station_reconciles_threshold_even_when_water_reading_stops(db_session):
    """A station can stop reporting stan_wody entirely (goes null) while its
    threshold keeps changing or gets withdrawn. Thresholds must still be
    reconciled in that case - an earlier version of normalize() returned None
    outright for a null water reading, which skipped threshold handling
    entirely too (Codex review, PR #42 round 4)."""
    station = {**STATION, "stan_ostrzegawczy": "300"}
    ingest.ingest_station(station, db_session, fetched_at=datetime.now(UTC))
    assert db_session.query(Measurement).filter_by(param_code="water_level_warn_cm").count() == 1

    stalled_station = {**station, "stan_wody": None, "stan_ostrzegawczy": None}
    ingest.ingest_station(stalled_station, db_session, fetched_at=datetime.now(UTC))

    assert db_session.query(Measurement).filter_by(param_code="water_level_warn_cm").count() == 0


class TestProvenance:
    """ADR-014: one raw fetch per IMGW response; every stored row points at it."""

    def test_snapshot_records_raw_payload_and_links_every_row(self, db_session):
        station = {**STATION, "stan_ostrzegawczy": "300", "stan_alarmowy": "340"}
        stations = [station]

        stored, rejected = ingest.ingest_snapshot(
            stations, db_session, fetched_at=datetime.now(UTC)
        )

        assert (stored, rejected) == (3, 0)
        fetch = db_session.query(SourceFetch).one()
        assert fetch.source_id == "imgw_hydro"
        assert fetch.endpoint == client.URL
        assert fetch.payload == stations
        assert fetch.parser_version == PARSER_VERSION
        assert fetch.validation_status == provenance.VALID
        assert {m.source_fetch_id for m in db_session.query(Measurement).all()} == {fetch.id}

    def test_partial_snapshot_when_a_station_is_malformed(self, db_session):
        bad = {**STATION, "id_stacji": "999", "lat": "not-a-number"}

        stored, rejected = ingest.ingest_snapshot(
            [bad, STATION], db_session, fetched_at=datetime.now(UTC)
        )

        assert (stored, rejected) == (1, 1)
        assert db_session.query(SourceFetch).one().validation_status == provenance.PARTIAL

    def test_all_stations_malformed_is_invalid_but_payload_kept(self, db_session):
        bad = {**STATION, "lat": "not-a-number"}

        ingest.ingest_snapshot([bad], db_session, fetched_at=datetime.now(UTC))

        fetch = db_session.query(SourceFetch).one()
        assert fetch.validation_status == provenance.INVALID
        assert fetch.payload == [bad]

    def test_threshold_upsert_moves_link_to_the_latest_fetch(self, db_session):
        first = {**STATION, "stan_ostrzegawczy": "300"}
        changed = {**STATION, "stan_ostrzegawczy": "310"}
        ingest.ingest_snapshot([first], db_session, fetched_at=datetime.now(UTC))
        ingest.ingest_snapshot([changed], db_session, fetched_at=datetime.now(UTC))

        latest = db_session.query(SourceFetch).order_by(SourceFetch.id.desc()).first()
        threshold = db_session.query(Measurement).filter_by(param_code="water_level_warn_cm").one()
        assert threshold.value == 310.0
        assert threshold.source_fetch_id == latest.id

    def test_provenance_failure_does_not_block_rows(self, db_session, monkeypatch):
        monkeypatch.setattr(provenance, "record_fetch", MagicMock(return_value=None))

        stored, _ = ingest.ingest_snapshot([STATION], db_session, fetched_at=datetime.now(UTC))

        assert stored == 1
        assert db_session.query(Measurement).one().source_fetch_id is None

    def test_ingest_station_without_fetch_id_leaves_link_null(self, db_session):
        ingest.ingest_station(STATION, db_session, fetched_at=datetime.now(UTC))

        assert db_session.query(Measurement).one().source_fetch_id is None


class TestMain:
    def test_ingests_every_fetched_station(self, monkeypatch, db_session):
        monkeypatch.setattr(client, "fetch_stations", MagicMock(return_value=[STATION]))
        monkeypatch.setattr(ingest, "SessionLocal", lambda: db_session)

        ingest.main()

        assert db_session.query(Measurement).count() == 1

    def test_one_bad_station_does_not_abort_the_rest(self, monkeypatch, db_session):
        other = {**STATION, "id_stacji": "999", "lat": "not-a-number"}
        monkeypatch.setattr(client, "fetch_stations", MagicMock(return_value=[other, STATION]))
        monkeypatch.setattr(ingest, "SessionLocal", lambda: db_session)

        with pytest.raises(RuntimeError, match="1/2 failed"):
            ingest.main()  # 50% rejected is over the 2% bound; valid rows still stored

        assert db_session.query(Measurement).count() == 1

    def test_one_rejected_station_in_a_large_snapshot_is_still_a_success(
        self, monkeypatch, db_session, caplog
    ):
        stations = [{**STATION, "id_stacji": str(i)} for i in range(100)]
        stations.append({**STATION, "id_stacji": "BAD", "lat": "not-a-number"})
        monkeypatch.setattr(client, "fetch_stations", MagicMock(return_value=stations))
        monkeypatch.setattr(ingest, "SessionLocal", lambda: db_session)

        ingest.main()

        assert db_session.get(SourceStatus, "imgw_hydro").last_success_at is not None
        assert "BAD" in caplog.text  # rejected ids are logged on every run

    def test_success_is_recorded_in_source_status(self, monkeypatch, db_session):
        # ADR-012: CLI-only operators must still get a FRESH /hydro source_status.
        monkeypatch.setattr(client, "fetch_stations", MagicMock(return_value=[STATION]))
        monkeypatch.setattr(ingest, "SessionLocal", lambda: db_session)

        ingest.main()

        assert db_session.get(SourceStatus, "imgw_hydro").last_success_at is not None

    def test_all_stations_malformed_is_a_failed_run(self, monkeypatch, db_session):
        bad = {**STATION, "lat": "not-a-number"}
        monkeypatch.setattr(client, "fetch_stations", MagicMock(return_value=[bad]))
        monkeypatch.setattr(ingest, "SessionLocal", lambda: db_session)

        with pytest.raises(RuntimeError):
            ingest.main()

        status = db_session.get(SourceStatus, "imgw_hydro")
        assert status.last_success_at is None and "1/1 failed" in status.last_error

    def test_fetch_failure_is_recorded_and_reraised(self, monkeypatch, db_session):
        monkeypatch.setattr(client, "fetch_stations", MagicMock(side_effect=RuntimeError("down")))
        monkeypatch.setattr(ingest, "SessionLocal", lambda: db_session)

        with pytest.raises(RuntimeError):
            ingest.main()

        status = db_session.get(SourceStatus, "imgw_hydro")
        assert status.last_success_at is None
        assert status.last_error == "RuntimeError: down"
