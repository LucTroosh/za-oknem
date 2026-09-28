"""Shared test fixtures.

Measurement (app/models.py) doesn't use any Postgres/PostGIS-specific column
types yet — plain String/Float/DateTime — so SQLite-in-memory is a fine,
zero-setup stand-in for tests. No Postgres service needed in CI for this.

ponytail: if a model ever needs a PostGIS type (geography/geometry), this
fixture must become a real Postgres test service instead — SQLite can't
represent that. Not needed yet.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
