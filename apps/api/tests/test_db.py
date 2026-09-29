"""Tests for get_db: session lifecycle (always closed, even on error)."""

from unittest.mock import MagicMock

import pytest

import app.db as db_module
from app.db import get_db


def test_get_db_yields_a_session_and_closes_it(monkeypatch):
    fake_session = MagicMock()
    monkeypatch.setattr(db_module, "SessionLocal", lambda: fake_session)

    gen = get_db()
    yielded = next(gen)
    assert yielded is fake_session
    fake_session.close.assert_not_called()

    # Exhaust the generator the way FastAPI's dependency teardown does.
    next(gen, None)
    fake_session.close.assert_called_once()


def test_get_db_closes_session_even_if_caller_raises(monkeypatch):
    fake_session = MagicMock()
    monkeypatch.setattr(db_module, "SessionLocal", lambda: fake_session)

    gen = get_db()
    next(gen)
    # get_db has no except clause, only finally - it closes then re-raises,
    # same as FastAPI's dependency teardown on a request that errors.
    with pytest.raises(ValueError, match="boom"):
        gen.throw(ValueError("boom"))

    fake_session.close.assert_called_once()
