"""Tests for Settings: defaults and env-var overrides (rule #3 - no secrets in
repo, only env vars, so this is the one thing worth pinning down)."""

import pytest

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


def test_open_meteo_defaults_are_the_free_hosts_without_key():
    settings = Settings(_env_file=None)

    assert settings.open_meteo_forecast_base_url == "https://api.open-meteo.com/v1/forecast"
    assert (
        settings.open_meteo_air_quality_base_url
        == "https://air-quality-api.open-meteo.com/v1/air-quality"
    )
    assert settings.open_meteo_api_key is None


def test_open_meteo_commercial_plan_is_env_only(monkeypatch):
    monkeypatch.setenv(
        "OPEN_METEO_FORECAST_BASE_URL", "https://customer-api.open-meteo.com/v1/forecast"
    )
    monkeypatch.setenv(
        "OPEN_METEO_AIR_QUALITY_BASE_URL",
        "https://customer-air-quality-api.open-meteo.com/v1/air-quality",
    )
    monkeypatch.setenv("OPEN_METEO_API_KEY", "k-123")

    settings = Settings(_env_file=None)

    assert settings.open_meteo_forecast_base_url.startswith("https://customer-api.")
    assert settings.open_meteo_air_quality_base_url.startswith("https://customer-air-quality-api.")
    assert settings.open_meteo_api_key == "k-123"


def test_api_key_is_not_in_repr_and_blank_means_none(monkeypatch):
    monkeypatch.setenv("OPEN_METEO_API_KEY", "  s3cret-key  ")
    settings = Settings(_env_file=None)
    assert settings.open_meteo_api_key == "s3cret-key"
    assert "s3cret-key" not in repr(settings)

    monkeypatch.setenv("OPEN_METEO_API_KEY", "   ")
    assert Settings(_env_file=None).open_meteo_api_key is None


def test_empty_base_url_env_means_default(monkeypatch):
    monkeypatch.setenv("OPEN_METEO_FORECAST_BASE_URL", "")
    monkeypatch.setenv("OPEN_METEO_AIR_QUALITY_BASE_URL", "  ")
    settings = Settings(_env_file=None)
    assert settings.open_meteo_forecast_base_url == "https://api.open-meteo.com/v1/forecast"
    assert "air-quality-api.open-meteo.com" in settings.open_meteo_air_quality_base_url


def test_key_requires_https_urls(monkeypatch):
    monkeypatch.setenv("OPEN_METEO_API_KEY", "k")
    monkeypatch.setenv(
        "OPEN_METEO_FORECAST_BASE_URL", "http://customer-api.open-meteo.com/v1/forecast"
    )
    with pytest.raises(ValueError):
        Settings(_env_file=None)


def test_daily_call_limit_setting(monkeypatch):
    assert Settings(_env_file=None).open_meteo_daily_call_limit == 10_000
    monkeypatch.setenv("OPEN_METEO_DAILY_CALL_LIMIT", "1000000")
    assert Settings(_env_file=None).open_meteo_daily_call_limit == 1_000_000


def test_warns_once_when_key_set_with_non_customer_host(monkeypatch, caplog):
    from app import config

    monkeypatch.setattr(config.settings, "open_meteo_api_key", "k-secret")
    with caplog.at_level("WARNING", logger="app.config"):
        config.warn_if_open_meteo_host_unusual()
    assert "customer-" in caplog.text and "k-secret" not in caplog.text

    caplog.clear()
    monkeypatch.setattr(config.settings, "open_meteo_api_key", None)
    config.warn_if_open_meteo_host_unusual()
    assert not caplog.text
