"""ADR-012: source_status upsert + source-level freshness (rule #8)."""

from datetime import UTC, datetime, timedelta

from app.api.v1.alerts import freshness as alerts_freshness
from app.models import SourceStatus
from app.source_status import record_source_run, source_freshness


def test_never_fetched_source_is_unavailable(db_session):
    assert source_freshness(db_session, "imgw_warningshydro", alerts_freshness) == {
        "freshness": "UNAVAILABLE",
        "last_success_at": None,
    }


def test_only_failed_runs_stay_unavailable(db_session):
    record_source_run(db_session, "imgw_warningshydro", success=False, error="down")

    result = source_freshness(db_session, "imgw_warningshydro", alerts_freshness)

    assert result["freshness"] == "UNAVAILABLE"
    assert db_session.get(SourceStatus, "imgw_warningshydro").last_error == "down"


def test_recent_success_is_fresh(db_session):
    record_source_run(db_session, "imgw_warningshydro", success=True)

    result = source_freshness(db_session, "imgw_warningshydro", alerts_freshness)

    assert result["freshness"] == "FRESH"
    assert result["last_success_at"] is not None


def test_failure_after_success_keeps_last_success(db_session):
    record_source_run(db_session, "imgw_warningshydro", success=True)
    first = db_session.get(SourceStatus, "imgw_warningshydro").last_success_at

    record_source_run(db_session, "imgw_warningshydro", success=False, error="x" * 2000)

    row = db_session.get(SourceStatus, "imgw_warningshydro")
    assert row.last_success_at == first
    assert len(row.last_error) == 500
    assert db_session.query(SourceStatus).count() == 1


def test_old_success_is_stale(db_session):
    db_session.add(
        SourceStatus(
            source_id="imgw_warningshydro",
            last_attempt_at=datetime.now(UTC),
            last_success_at=datetime.now(UTC) - timedelta(hours=12),
        )
    )
    db_session.commit()

    result = source_freshness(db_session, "imgw_warningshydro", alerts_freshness)

    assert result["freshness"] == "STALE"


def test_out_of_order_older_result_does_not_overwrite_newer(db_session):
    # Codex review: a writer that computed its timestamp earlier and committed
    # later must not move status backward (e.g. older success over newer failure).
    t_new = datetime.now(UTC)
    t_old = t_new - timedelta(seconds=30)
    record_source_run(db_session, "imgw_warningshydro", success=False, error="down", now=t_new)

    record_source_run(db_session, "imgw_warningshydro", success=True, now=t_old)

    row = db_session.get(SourceStatus, "imgw_warningshydro")
    assert row.last_success_at is None
    assert row.last_error == "down"
    assert source_freshness(db_session, "imgw_warningshydro", alerts_freshness)["freshness"] == (
        "UNAVAILABLE"
    )


def test_newer_result_still_applies(db_session):
    t_old = datetime.now(UTC) - timedelta(seconds=30)
    record_source_run(db_session, "imgw_warningshydro", success=False, error="down", now=t_old)

    record_source_run(db_session, "imgw_warningshydro", success=True)

    row = db_session.get(SourceStatus, "imgw_warningshydro")
    assert row.last_success_at is not None
    assert row.last_error is None


def test_future_success_is_not_fresh(db_session):
    # Clock skew on another host must not make a source look permanently FRESH.
    future = datetime.now(UTC) + timedelta(hours=2)
    record_source_run(db_session, "imgw_warningshydro", success=True, now=future)

    result = source_freshness(db_session, "imgw_warningshydro", alerts_freshness)

    assert result["freshness"] == "STALE"


def test_future_dated_row_does_not_block_a_real_run(db_session):
    future = datetime.now(UTC) + timedelta(hours=2)
    record_source_run(db_session, "imgw_warningshydro", success=True, now=future)

    record_source_run(db_session, "imgw_warningshydro", success=False, error="down")

    row = db_session.get(SourceStatus, "imgw_warningshydro")
    assert row.last_error == "down"
