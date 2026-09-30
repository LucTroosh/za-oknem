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
