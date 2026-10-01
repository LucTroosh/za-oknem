"""Shared test fixtures.

Models use plain String/Float/DateTime columns (plus one PostGIS column, below), so
SQLite-in-memory is a fine, zero-setup stand-in for the unit tests.

GeoArea.boundary (PostGIS geometry, ADR-019) degrades to TEXT on SQLite (see
app/geometry.py), so these tests never exercise geometry. Point-in-polygon and the
importer are tested in tests/test_postgis_geo.py against a real PostGIS database
(skipped when none is reachable; CI provides one).
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
