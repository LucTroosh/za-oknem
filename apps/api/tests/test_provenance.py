"""ADR-014: raw payload recording, validation status, best-effort failure mode and
retention. SQLite stand-in for Postgres - JSONB is a dialect variant of JSON, so
the same model works in both."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from app import provenance
from app.models import Measurement, SourceFetch

NOW = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)


def _fetch(db, source_id="gios", age_days=0, payload=None) -> SourceFetch:
    row = SourceFetch(
        source_id=source_id,
        endpoint="https://example.test/x",
        fetched_at=NOW - timedelta(days=age_days),
        parser_version="1",
        validation_status=provenance.VALID,
        payload={"k": age_days} if payload is None else payload,
    )
    db.add(row)
    db.commit()
    return row


class TestRecordFetch:
    def test_stores_payload_and_metadata(self, db_session):
        payload = [{"id": 1, "nested": {"a": [1, 2]}}]

        fetch_id = provenance.record_fetch(
            db_session,
            source_id="imgw_hydro",
            endpoint="https://example.test/hydro",
            payload=payload,
            fetched_at=NOW,
            parser_version="7",
        )

        row = db_session.get(SourceFetch, fetch_id)
        assert row.source_id == "imgw_hydro"
        assert row.endpoint == "https://example.test/hydro"
        assert row.payload == payload
        assert row.parser_version == "7"
        assert row.validation_status == provenance.PENDING

    def test_json_null_body_is_not_confused_with_a_purged_payload(self, db_session):
        # A source answering with a JSON `null` body: stored as the JSON literal,
        # while SQL NULL is reserved for "purged by retention".
        provenance.record_fetch(
            db_session,
            source_id="s",
            endpoint="e",
            payload=None,
            fetched_at=NOW,
            parser_version="1",
        )

        is_sql_null = db_session.execute(
            text("SELECT payload IS NULL FROM source_fetches")
        ).scalar_one()
        assert not is_sql_null

    def test_set_validation_status_updates_the_row(self, db_session):
        fetch_id = provenance.record_fetch(
            db_session, source_id="s", endpoint="e", payload={}, fetched_at=NOW, parser_version="1"
        )

        provenance.set_validation_status(db_session, fetch_id, provenance.PARTIAL)

        assert db_session.get(SourceFetch, fetch_id).validation_status == provenance.PARTIAL

    def test_set_validation_status_ignores_failed_record(self, db_session):
        provenance.set_validation_status(db_session, None, provenance.VALID)  # no exception

    def test_write_failure_returns_none_and_session_stays_usable(self, db_session, monkeypatch):
        # rule #1: an audit-table failure must not break the ingest around it.
        def _boom(*_a, **_kw):
            raise RuntimeError("db hiccup")

        monkeypatch.setattr(db_session, "flush", _boom)

        fetch_id = provenance.record_fetch(
            db_session, source_id="s", endpoint="e", payload={}, fetched_at=NOW, parser_version="1"
        )

        assert fetch_id is None
        monkeypatch.undo()
        assert db_session.query(SourceFetch).count() == 0  # session still works

    def test_normalized_row_can_reference_the_fetch(self, db_session):
        fetch = _fetch(db_session)
        db_session.add(
            Measurement(
                source_id="gios",
                source_record_id="r1",
                station_id="1",
                station_name="s",
                latitude=50.0,
                longitude=16.0,
                param_code="PM2.5",
                value=1.0,
                unit="ug/m3",
                observed_at=NOW,
                fetched_at=NOW,
                source_fetch_id=fetch.id,
            )
        )
        db_session.commit()

        assert db_session.query(Measurement).one().source_fetch_id == fetch.id

    def test_fk_is_nullable_for_old_rows(self, db_session):
        db_session.add(
            Measurement(
                source_id="gios",
                source_record_id="r1",
                station_id="1",
                station_name="s",
                latitude=50.0,
                longitude=16.0,
                param_code="PM2.5",
                value=1.0,
                unit="ug/m3",
                observed_at=NOW,
                fetched_at=NOW,
            )
        )
        db_session.commit()

        assert db_session.query(Measurement).one().source_fetch_id is None


class TestBatchStatus:
    def test_statuses(self):
        assert provenance.batch_status(5, 0) == provenance.VALID
        assert provenance.batch_status(0, 0) == provenance.VALID
        assert provenance.batch_status(5, 2) == provenance.PARTIAL
        assert provenance.batch_status(5, 5) == provenance.INVALID


class TestPurgeExpiredPayloads:
    def test_purges_only_payloads_past_their_sources_window(self, db_session):
        old_gios = _fetch(db_session, "gios", age_days=15)  # window 14
        young_gios = _fetch(db_session, "gios", age_days=13)
        old_meteo = _fetch(db_session, "open_meteo", age_days=8)  # window 7
        young_warn = _fetch(db_session, "imgw_warningshydro", age_days=29)  # window 30
        old_warn = _fetch(db_session, "imgw_warningshydro", age_days=31)

        purged = provenance.purge_expired_payloads(db_session, now=NOW)

        assert purged == 3
        payload = {r.id: r.payload for r in db_session.query(SourceFetch).all()}
        assert payload[old_gios.id] is None
        assert payload[old_meteo.id] is None
        assert payload[old_warn.id] is None
        assert payload[young_gios.id] is not None
        assert payload[young_warn.id] is not None

    def test_unlisted_source_gets_the_shortest_window(self, db_session):
        old = _fetch(db_session, "future_source", age_days=8)
        young = _fetch(db_session, "future_source", age_days=6)

        provenance.purge_expired_payloads(db_session, now=NOW)

        assert db_session.get(SourceFetch, old.id).payload is None
        assert db_session.get(SourceFetch, young.id).payload is not None

    def test_keeps_metadata_rows_and_fk_links(self, db_session):
        old = _fetch(db_session, "gios", age_days=40)
        db_session.add(
            Measurement(
                source_id="gios",
                source_record_id="r1",
                station_id="1",
                station_name="s",
                latitude=50.0,
                longitude=16.0,
                param_code="PM2.5",
                value=1.0,
                unit="ug/m3",
                observed_at=NOW,
                fetched_at=NOW,
                source_fetch_id=old.id,
            )
        )
        db_session.commit()

        provenance.purge_expired_payloads(db_session, now=NOW)

        kept = db_session.get(SourceFetch, old.id)
        assert kept.payload is None
        assert kept.endpoint == "https://example.test/x"
        assert kept.validation_status == provenance.VALID
        assert db_session.query(Measurement).one().source_fetch_id == old.id

    def test_purged_payload_is_sql_null_not_json_null(self, db_session):
        # null() (not Python None): a JSON literal 'null' would make
        # `payload IS NOT NULL` true forever and re-purge the row on every run.
        _fetch(db_session, "gios", age_days=40)
        provenance.purge_expired_payloads(db_session, now=NOW)

        is_sql_null = db_session.execute(
            text("SELECT payload IS NULL FROM source_fetches")
        ).scalar_one()
        assert is_sql_null
        assert provenance.purge_expired_payloads(db_session, now=NOW) == 0
