"""Tests for app/rate_budget.py: daily call counter + 70% threshold alert
(ADR-001/ADR-003/ADR-004). Uses the real SQLite db_session fixture (plain ORM,
no Postgres-only SQL - portable, unlike the DISTINCT ON endpoints)."""

import logging
from datetime import date

from app.models import SourceFetchCounter
from app.rate_budget import check_daily_budget, record_fetch_call


def test_record_fetch_call_starts_at_one(db_session):
    count = record_fetch_call(db_session, "open_meteo", today=date(2026, 9, 29))
    assert count == 1
    assert db_session.query(SourceFetchCounter).count() == 1


def test_record_fetch_call_increments_same_day(db_session):
    today = date(2026, 9, 29)
    record_fetch_call(db_session, "open_meteo", today=today)
    record_fetch_call(db_session, "open_meteo", today=today)
    count = record_fetch_call(db_session, "open_meteo", today=today)

    assert count == 3
    assert db_session.query(SourceFetchCounter).count() == 1  # one row, not three


def test_record_fetch_call_separate_row_per_day(db_session):
    record_fetch_call(db_session, "open_meteo", today=date(2026, 9, 28))
    count_day2 = record_fetch_call(db_session, "open_meteo", today=date(2026, 9, 29))

    assert count_day2 == 1  # yesterday's count doesn't carry over
    assert db_session.query(SourceFetchCounter).count() == 2


def test_record_fetch_call_separate_row_per_source(db_session):
    today = date(2026, 9, 29)
    record_fetch_call(db_session, "open_meteo", today=today)
    count = record_fetch_call(db_session, "gios", today=today)

    assert count == 1  # a different source_id doesn't share open_meteo's counter
    assert db_session.query(SourceFetchCounter).count() == 2


def test_check_daily_budget_logs_warning_at_threshold(caplog):
    with caplog.at_level(logging.WARNING):
        check_daily_budget("open_meteo", count=7000, daily_limit=10_000)
    assert any("70" in r.message or "7000" in r.message for r in caplog.records)


def test_check_daily_budget_silent_below_threshold(caplog):
    with caplog.at_level(logging.WARNING):
        check_daily_budget("open_meteo", count=6999, daily_limit=10_000)
    assert caplog.records == []


def test_check_daily_budget_logs_above_threshold(caplog):
    with caplog.at_level(logging.WARNING):
        check_daily_budget("open_meteo", count=9500, daily_limit=10_000)
    assert len(caplog.records) == 1
