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


def test_record_fetch_call_units_param_increments_by_that_amount(db_session):
    # Codex review [P1]: a single Open-Meteo request bills more than 1 unit once it
    # covers >10 variables (ADR-003) - callers must be able to record that.
    today = date(2026, 9, 29)
    count = record_fetch_call(db_session, "open_meteo", units=2, today=today)
    assert count == 2
    count = record_fetch_call(db_session, "open_meteo", units=2, today=today)
    assert count == 4


def test_record_fetch_call_returns_what_is_actually_persisted(db_session):
    # Regression guard for the read-modify-write race (Codex review [P2]): the
    # returned count must come from the same atomic UPDATE...RETURNING as what's
    # persisted, not an in-Python object mutated before commit.
    today = date(2026, 9, 29)
    record_fetch_call(db_session, "open_meteo", today=today)
    record_fetch_call(db_session, "open_meteo", today=today)
    persisted = (
        db_session.query(SourceFetchCounter).filter_by(source_id="open_meteo", day=today).one()
    )
    assert persisted.count == 2


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
