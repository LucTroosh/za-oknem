"""Tests for imgw_hydro.ingest: store/skip/dedupe/failure-isolation, using the
SQLite db_session fixture."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from app.connectors.imgw_hydro import client, ingest
from app.connectors.imgw_hydro.parser import ImgwHydroParseError
from app.models import Measurement

STATION = {
    "id_stacji": "151140030",
    "stacja": "Przewoźniki",
    "rzeka": "Skroda",
    "lat": "51.5253",
    "lon": "14.8217",
    "stan_wody": "225",
    "stan_wody_data_pomiaru": "2026-09-27 21:20:00",
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
    monkeypatch.setattr(
        ingest, "normalize", MagicMock(side_effect=ImgwHydroParseError("boom"))
    )
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
    row = (
        db_session.query(Measurement)
        .filter_by(param_code="water_level_warn_cm")
        .one()
    )
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


class TestMain:
    def test_ingests_every_fetched_station(self, monkeypatch, db_session):
        monkeypatch.setattr(client, "fetch_stations", MagicMock(return_value=[STATION]))
        monkeypatch.setattr(ingest, "SessionLocal", lambda: db_session)

        ingest.main()

        assert db_session.query(Measurement).count() == 1

    def test_one_bad_station_does_not_abort_the_rest(self, monkeypatch, db_session):
        other = {**STATION, "id_stacji": "999", "lat": "not-a-number"}
        monkeypatch.setattr(
            client, "fetch_stations", MagicMock(return_value=[other, STATION])
        )
        monkeypatch.setattr(ingest, "SessionLocal", lambda: db_session)

        ingest.main()

        assert db_session.query(Measurement).count() == 1
