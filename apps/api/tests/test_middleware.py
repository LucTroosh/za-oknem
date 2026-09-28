"""Tests for RequestLoggingMiddleware: one structured log line per request."""

import logging

from fastapi.testclient import TestClient

from app.main import app


def test_request_logging_middleware_logs_method_path_status(caplog):
    client = TestClient(app)

    with caplog.at_level(logging.INFO, logger="app.request"):
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert len(caplog.records) == 1
    message = caplog.records[0].message
    assert "method=GET" in message
    assert "path=/api/v1/health" in message
    assert "status=200" in message
    assert "duration_ms=" in message
