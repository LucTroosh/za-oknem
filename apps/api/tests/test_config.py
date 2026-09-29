"""Tests for Settings: defaults and env-var overrides (rule #3 - no secrets in
repo, only env vars, so this is the one thing worth pinning down)."""

from app.config import Settings


def test_settings_defaults():
    settings = Settings(_env_file=None)

    assert settings.database_url == "postgresql+psycopg://postgres:postgres@localhost:5432/za_oknem"
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.cors_origins == ["http://localhost:8081", "http://localhost:19006"]


def test_settings_reads_env_override(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@db:5432/other")
    monkeypatch.setenv("REDIS_URL", "redis://cache:6379/1")

    settings = Settings(_env_file=None)

    assert settings.database_url == "postgresql+psycopg://u:p@db:5432/other"
    assert settings.redis_url == "redis://cache:6379/1"


def test_settings_ignores_unknown_env_vars(monkeypatch):
    # model_config has extra="ignore" - an unrelated env var must not raise.
    monkeypatch.setenv("SOME_UNRELATED_VAR", "whatever")

    Settings(_env_file=None)
