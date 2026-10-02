"""Tests for GET /api/v1/weather/latest: freshness thresholds and response shaping.

Same fake-session approach as test_air.py (Postgres DISTINCT ON, SQLite can't
compile it) — but this endpoint issues two execute() calls (snapshots, then
geo_areas), so the fake session returns queued results in call order.
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.v1.weather import (
    FRESH_MAX_AGE,
    RECENT_MAX_AGE,
    WeatherForecastResponse,
    WeatherLatestResponse,
    freshness,
)
from app.db import get_db
from app.main import app
from app.models import Forecast, GeoArea, WeatherSnapshot


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, *result_sets):
        self._queue = list(result_sets)

    def execute(self, _stmt):
        return _FakeResult(self._queue.pop(0))


def _client(snapshot_rows: list[WeatherSnapshot], geo_areas: list[GeoArea]) -> TestClient:
    def _override():
        yield _FakeSession(snapshot_rows, geo_areas)

    app.dependency_overrides[get_db] = _override
    return TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.pop(get_db, None)


def _area(**overrides) -> GeoArea:
    defaults = {
        "id": 1,
        "slug": "klodzko",
        "name": "Kłodzko",
        "latitude": 50.43,
        "longitude": 16.65,
    }
    defaults.update(overrides)
    return GeoArea(**defaults)


def _snapshot(**overrides) -> WeatherSnapshot:
    defaults = {
        "source_id": "open_meteo",
        "source_record_id": "rec-1",
        "geo_area_id": 1,
        "param_code": "temperature_2m",
        "value": 12.3,
        "unit": "°C",
        "observed_at": datetime.now(UTC),
        "fetched_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return WeatherSnapshot(**defaults)


# --- freshness() thresholds --------------------------------------------------


def test_freshness_within_fresh_threshold():
    assert freshness(datetime.now(UTC) - (FRESH_MAX_AGE - timedelta(minutes=1))) == "FRESH"


def test_freshness_just_past_fresh_threshold_is_recent():
    assert freshness(datetime.now(UTC) - (FRESH_MAX_AGE + timedelta(minutes=1))) == "RECENT"


def test_freshness_just_past_recent_threshold_is_stale():
    assert freshness(datetime.now(UTC) - (RECENT_MAX_AGE + timedelta(minutes=1))) == "STALE"


# --- GET /api/v1/weather/latest ----------------------------------------------


def test_latest_weather_returns_empty_list_when_no_rows():
    client = _client([], [])

    response = client.get("/api/v1/weather/latest")

    assert response.status_code == 200
    assert response.json() == {"areas": []}


def test_latest_weather_groups_params_by_geo_area():
    now = datetime.now(UTC)
    rows = [
        _snapshot(param_code="temperature_2m", value=12.3, unit="°C", observed_at=now),
        _snapshot(param_code="wind_speed_10m", value=5.2, unit="km/h", observed_at=now),
    ]
    client = _client(rows, [_area()])

    body = client.get("/api/v1/weather/latest").json()

    # observed_at fields are asserted separately via fromisoformat(): now that they're
    # typed datetime (Codex review), Pydantic's JSON encoding uses a "Z" suffix, not
    # Python's own isoformat() "+00:00" — comparing as parsed datetimes instead of raw
    # strings checks the actual timestamp value without hardcoding a wire format.
    area = body["areas"][0]
    assert datetime.fromisoformat(area["observed_at"]) == now
    assert datetime.fromisoformat(area["params"]["temperature_2m"]["observed_at"]) == now
    assert datetime.fromisoformat(area["params"]["wind_speed_10m"]["observed_at"]) == now
    for param in area["params"].values():
        del param["observed_at"]
    del area["observed_at"]
    assert body == {
        "areas": [
            {
                "geo_area_id": 1,
                "slug": "klodzko",
                "name": "Kłodzko",
                "latitude": 50.43,
                "longitude": 16.65,
                "freshness": "FRESH",
                "params": {
                    "temperature_2m": {
                        "value": 12.3,
                        "unit": "°C",
                        "freshness": "FRESH",
                    },
                    "wind_speed_10m": {
                        "value": 5.2,
                        "unit": "km/h",
                        "freshness": "FRESH",
                    },
                },
                "source": "open_meteo",
            }
        ]
    }


def test_latest_weather_marks_old_reading_stale():
    row = _snapshot(observed_at=datetime.now(UTC) - timedelta(hours=10))
    client = _client([row], [_area()])

    body = client.get("/api/v1/weather/latest").json()

    assert body["areas"][0]["freshness"] == "STALE"


def test_latest_weather_reports_per_param_freshness_independently():
    # Codex review: a fresh `current` param and a stale hourly-derived one (TASK-5.4)
    # must not both be reported as FRESH just because the object-level `freshness`
    # takes the max observed_at across params - each param needs its own status.
    fresh_row = _snapshot(
        param_code="temperature_2m", observed_at=datetime.now(UTC), source_record_id="fresh"
    )
    stale_row = _snapshot(
        param_code="uv_index",
        observed_at=datetime.now(UTC) - timedelta(hours=10),
        source_record_id="stale",
    )
    client = _client([fresh_row, stale_row], [_area()])

    body = client.get("/api/v1/weather/latest").json()

    params = body["areas"][0]["params"]
    assert params["temperature_2m"]["freshness"] == "FRESH"
    assert params["uv_index"]["freshness"] == "STALE"
    # Object-level freshness is a rough "most recent of any param" summary, not
    # authoritative per param - documented as such, not removed.
    assert body["areas"][0]["freshness"] == "FRESH"


def test_latest_weather_skips_snapshot_for_deleted_geo_area():
    row = _snapshot(geo_area_id=999)
    client = _client([row], [_area()])  # area id=1, snapshot references id=999

    body = client.get("/api/v1/weather/latest").json()

    assert body == {"areas": []}


def test_latest_weather_handles_multiple_areas():
    rows = [
        _snapshot(geo_area_id=1, source_record_id="a"),
        _snapshot(geo_area_id=2, source_record_id="b"),
    ]
    areas = [_area(id=1, slug="klodzko"), _area(id=2, slug="warszawa", name="Warszawa")]
    client = _client(rows, areas)

    body = client.get("/api/v1/weather/latest").json()

    assert {a["slug"] for a in body["areas"]} == {"klodzko", "warszawa"}


# --- GET /api/v1/weather/forecast (ADR-010) ----------------------------------


def _forecast(**overrides) -> Forecast:
    now = datetime.now(UTC)
    valid_from = overrides.get("valid_from", now.replace(hour=0, minute=0, second=0, microsecond=0))
    defaults = {
        "source_id": "open_meteo",
        "source_record_id": "rec-1",
        "geo_area_id": 1,
        "param_code": "temperature_2m_max",
        "value": 18.5,
        "unit": "°C",
        "model": "auto",
        "forecast_reference_time": now,
        "valid_from": valid_from,
        "valid_until": valid_from + timedelta(days=1),  # overridden below if caller passed one
        "fetched_at": now,
    }
    defaults.update(overrides)
    return Forecast(**defaults)


def test_weather_forecast_returns_empty_list_when_no_rows():
    client = _client([], [])

    response = client.get("/api/v1/weather/forecast")

    assert response.status_code == 200
    assert response.json() == {"areas": []}


def test_weather_forecast_groups_by_area_and_day():
    day1 = datetime(2026, 9, 29, tzinfo=UTC)
    day2 = datetime(2026, 9, 30, tzinfo=UTC)
    rows = [
        _forecast(param_code="temperature_2m_max", value=18.5, valid_from=day1),
        _forecast(param_code="temperature_2m_min", value=9.2, valid_from=day1),
        _forecast(param_code="temperature_2m_max", value=19.1, valid_from=day2),
    ]
    client = _client(rows, [_area()])

    body = client.get("/api/v1/weather/forecast").json()

    assert len(body["areas"]) == 1
    area = body["areas"][0]
    assert area["slug"] == "klodzko"
    assert area["model"] == "auto"
    assert len(area["days"]) == 2
    assert datetime.fromisoformat(area["days"][0]["valid_from"]) == day1
    assert area["days"][0]["params"] == {
        "temperature_2m_max": {"value": 18.5, "unit": "°C"},
        "temperature_2m_min": {"value": 9.2, "unit": "°C"},
    }
    assert area["days"][1]["params"] == {"temperature_2m_max": {"value": 19.1, "unit": "°C"}}


def test_weather_forecast_reports_freshness_from_fetched_at():
    row = _forecast(fetched_at=datetime.now(UTC))
    client = _client([row], [_area()])

    area = client.get("/api/v1/weather/forecast").json()["areas"][0]

    assert area["freshness"] == "FRESH"
    assert datetime.fromisoformat(area["fetched_at"]) == row.fetched_at


def test_weather_forecast_marks_stale_when_fetched_at_old():
    row = _forecast(fetched_at=datetime.now(UTC) - timedelta(hours=10))
    client = _client([row], [_area()])

    area = client.get("/api/v1/weather/forecast").json()["areas"][0]

    assert area["freshness"] == "STALE"


def test_weather_forecast_freshness_uses_fetched_at_not_bucketed_reference_time():
    """ADR-010 buckets forecast_reference_time down to the 3h cycle start, so a
    fetch at 14:59 stores forecast_reference_time=12:00 — up to ~3h "older"
    than the real fetch. Freshness must be based on the real fetched_at, not
    that bucketed value, or a just-fetched forecast could read as RECENT/STALE."""
    row = _forecast(
        fetched_at=datetime.now(UTC),
        forecast_reference_time=datetime.now(UTC) - timedelta(hours=2, minutes=59),
    )
    client = _client([row], [_area()])

    area = client.get("/api/v1/weather/forecast").json()["areas"][0]

    assert area["freshness"] == "FRESH"


def test_weather_forecast_skips_row_for_deleted_geo_area():
    row = _forecast(geo_area_id=999)
    client = _client([row], [_area()])  # area id=1, forecast references id=999

    body = client.get("/api/v1/weather/forecast").json()

    assert body == {"areas": []}


def test_weather_forecast_days_are_sorted_ascending():
    day1 = datetime(2026, 9, 29, tzinfo=UTC)
    day2 = datetime(2026, 9, 30, tzinfo=UTC)
    day3 = datetime(2026, 10, 1, tzinfo=UTC)
    # Deliberately out of order - the endpoint must sort, not trust query order.
    rows = [
        _forecast(valid_from=day3),
        _forecast(valid_from=day1),
        _forecast(valid_from=day2),
    ]
    client = _client(rows, [_area()])

    body = client.get("/api/v1/weather/forecast").json()

    valid_froms = [datetime.fromisoformat(d["valid_from"]) for d in body["areas"][0]["days"]]
    assert valid_froms == [day1, day2, day3]


# --- response models (TASK-API-2: response_model actually enforces a shape) ---


def test_weather_latest_response_rejects_missing_required_field():
    with pytest.raises(ValidationError):
        WeatherLatestResponse.model_validate(
            {
                "areas": [
                    {
                        "geo_area_id": 1,
                        "slug": "klodzko",
                        # name missing
                        "latitude": 50.43,
                        "longitude": 16.65,
                        "observed_at": "2026-09-29T12:00:00+00:00",
                        "freshness": "FRESH",
                        "params": {},
                        "source": "open_meteo",
                    }
                ]
            }
        )


def test_weather_latest_response_source_is_provider_neutral():
    # ADR-022: `source` is a plain source_id, so swapping the weather provider does not
    # change the client contract (it used to be Literal["open_meteo"]).
    response = WeatherLatestResponse.model_validate(
        {
            "areas": [
                {
                    "geo_area_id": 1,
                    "slug": "klodzko",
                    "name": "Kłodzko",
                    "latitude": 50.43,
                    "longitude": 16.65,
                    "observed_at": "2026-09-29T12:00:00+00:00",
                    "freshness": "FRESH",
                    "params": {},
                    "source": "met_norway",
                }
            ]
        }
    )
    assert response.areas[0].source == "met_norway"


def test_weather_latest_response_rejects_invalid_observed_at():
    # Codex review: valid_from/valid_until/forecast_reference_time/observed_at/
    # fetched_at were plain `str` — the OpenAPI schema and this response_model
    # accepted any string. Now typed `datetime`, so garbage is actually rejected.
    with pytest.raises(ValidationError):
        WeatherLatestResponse.model_validate(
            {
                "areas": [
                    {
                        "geo_area_id": 1,
                        "slug": "klodzko",
                        "name": "Kłodzko",
                        "latitude": 50.43,
                        "longitude": 16.65,
                        "observed_at": "invalid",
                        "freshness": "FRESH",
                        "params": {},
                        "source": "open_meteo",
                    }
                ]
            }
        )


def test_weather_forecast_response_rejects_missing_required_field():
    with pytest.raises(ValidationError):
        WeatherForecastResponse.model_validate(
            {
                "areas": [
                    {
                        "geo_area_id": 1,
                        "slug": "klodzko",
                        "name": "Kłodzko",
                        "latitude": 50.43,
                        "longitude": 16.65,
                        "model": "auto",
                        "fetched_at": "2026-09-29T12:00:00+00:00",
                        "freshness": "FRESH",
                        # days missing
                        "source": "open_meteo",
                    }
                ]
            }
        )


# --- forecasts_by_area against a real (SQLite) session: one RUN per period (Codex, PR #89) ---
# The query no longer uses Postgres DISTINCT ON, so it runs here for real.


def _run_row(db, area_id, ref, param, value, *, valid_from, granularity="daily", **kw):
    span = timedelta(days=1) if granularity == "daily" else timedelta(hours=1)
    db.add(
        Forecast(
            source_id="open_meteo",
            source_record_id=f"{granularity}:{area_id}:{param}:{valid_from}:{ref}",
            geo_area_id=area_id,
            param_code=param,
            value=value,
            unit="u",
            model="auto",
            forecast_reference_time=ref,
            valid_from=valid_from,
            valid_until=valid_from + span,
            fetched_at=ref,
            granularity=granularity,
            **kw,
        )
    )


def _area_in(db) -> GeoArea:
    area = GeoArea(slug="k", name="K", latitude=50.4, longitude=16.6)
    db.add(area)
    db.commit()
    return area


def test_forecasts_by_area_takes_all_params_from_the_newest_run_only(db_session, monkeypatch):
    from app.api.v1.weather import forecasts_by_area

    monkeypatch.setattr("app.api.v1.weather.freshness", lambda _dt: "FRESH")  # SQLite is naive
    area = _area_in(db_session)
    day = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    old, new = datetime.now(UTC) - timedelta(hours=6), datetime.now(UTC) - timedelta(hours=3)
    # old run supplied the optional probability; the new run (null from the model) did not.
    for param, value in (("temperature_2m_max", 18.0), ("precipitation_sum", 70.0)):
        _run_row(db_session, area.id, old, param, value, valid_from=day)
    _run_row(db_session, area.id, new, "temperature_2m_max", 19.5, valid_from=day)
    db_session.commit()

    result = forecasts_by_area(db_session)[area.id]

    assert [d["params"] for d in result["days"]] == [
        {"temperature_2m_max": {"value": 19.5, "unit": "u"}}  # no stale probability alongside
    ]


def test_forecasts_by_area_hours_and_days_are_independent_runs(db_session, monkeypatch):
    from app.api.v1.weather import forecasts_by_area

    monkeypatch.setattr("app.api.v1.weather.freshness", lambda _dt: "FRESH")
    area = _area_in(db_session)
    now = datetime.now(UTC)
    midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    ref = now - timedelta(hours=1)
    _run_row(db_session, area.id, ref, "weather_code", 3.0, valid_from=midnight)
    _run_row(
        db_session, area.id, ref, "weather_code", 61.0, valid_from=midnight, granularity="hourly"
    )
    db_session.commit()

    only_days = forecasts_by_area(db_session)[area.id]
    both = forecasts_by_area(db_session, hourly=True)[area.id]

    assert only_days["hours"] == []  # hourly rows are not even loaded without hourly=True
    assert [d["params"]["weather_code"]["value"] for d in both["days"]] == [3.0]
    assert [h["params"]["weather_code"]["value"] for h in both["hours"]] == [61.0]
    assert both["hours"][0]["valid_until"] - both["hours"][0]["valid_from"] == timedelta(hours=1)
