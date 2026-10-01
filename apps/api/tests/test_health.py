"""Tests for GET /api/v1/health and /api/v1/health/ready."""

from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app


def _yield_dep(session):
    """A real generator dependency: FastAPI (newer versions) hands a plain callable's
    iterator to the endpoint instead of iterating it."""

    def _dep():
        yield session

    return _dep


def teardown_function() -> None:
    app.dependency_overrides.pop(get_db, None)


def test_health_returns_ok():
    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_ready_returns_ok_when_db_reachable():
    class _OkSession:
        def execute(self, _stmt):
            return None

    app.dependency_overrides[get_db] = _yield_dep(_OkSession())
    client = TestClient(app)

    response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_ready_returns_503_when_db_unreachable():
    class _BrokenSession:
        def execute(self, _stmt):
            raise ConnectionError("boom")

    app.dependency_overrides[get_db] = _yield_dep(_BrokenSession())
    client = TestClient(app)

    response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert "database unavailable" in response.json()["detail"]
