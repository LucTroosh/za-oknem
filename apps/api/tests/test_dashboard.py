"""Tests for GET /api/v1/dashboard/latest: nearest-station join (ADR-006).

Same fake-session approach as test_air.py/test_weather.py (Postgres DISTINCT ON,
SQLite can't compile it). Three execute() calls in order: geo_areas, stations,
weather snapshots.
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.api.v1.pollen import ATTRIBUTION, pollen_block
from app.db import get_db
from app.main import app
from app.models import (
    Alert,
    Forecast,
    GeoArea,
    Measurement,
    PollenSnapshot,
    SourceStatus,
    WeatherSnapshot,
)
from app.source_status import source_freshness

KLODZKO = {
    "id": 1,
    "slug": "klodzko",
    "name": "Kłodzko",
    "latitude": 50.433493,
    "longitude": 16.65366,
    "weather_polling_active": True,
}
WARSZAWA = {
    "id": 2,
    "slug": "warszawa",
    "name": "Warszawa",
    "latitude": 52.2297,
    "longitude": 21.0122,
    "weather_polling_active": True,
}


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, *result_sets, status_rows=None, geo_areas=()):
        self._queue = list(result_sets)
        self._geo_areas = {a.id: a for a in geo_areas}
        self._status_rows = status_rows or {}

    def execute(self, _stmt):
        return _FakeResult(self._queue.pop(0))

    def rollback(self):
        pass

    def get(self, model, key):
        if model is GeoArea:  # ?geo_area_id= lookup (TASK-6.2(8))
            return self._geo_areas.get(key)
        # No source_status rows unless a test supplies one -> UNAVAILABLE (ADR-012).
        return self._status_rows.get(key)


def _client(
    areas,
    stations,
    weather_rows,
    forecast_rows=(),
    alert_rows=(),
    pollen=([], []),
    status_rows=None,
    catalog=(),
    lookup=(),
) -> TestClient:
    # Query order in dashboard_latest(): areas, stations, GIOŚ catalog ids (ADR-025; empty =
    # no catalog yet), weather, forecasts, alerts, then pollen snapshots (+ geo_areas when
    # there are snapshots).
    def _override():
        sets = [] if lookup else [areas]  # ?geo_area_id= reads the area via db.get
        sets += [stations, list(catalog), weather_rows, list(forecast_rows)]
        sets.append(list(alert_rows))
        rows, pollen_areas = pollen
        sets += [rows, pollen_areas] if rows else [rows]
        yield _FakeSession(*sets, status_rows=status_rows, geo_areas=lookup)

    app.dependency_overrides[get_db] = _override
    return TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.pop(get_db, None)


def _station(**overrides) -> Measurement:
    defaults = {
        "source_id": "gios",
        "source_record_id": "rec-1",
        "station_id": "38",
        "station_name": "Kłodzko, ul. Szkolna",
        "latitude": 50.433493,
        "longitude": 16.65366,
        "param_code": "PM2.5",
        "value": 11.5,
        "unit": "µg/m³",
        "observed_at": datetime.now(UTC),
        "fetched_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return Measurement(**defaults)


def _weather(**overrides) -> WeatherSnapshot:
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


def test_dashboard_empty_when_no_geo_areas():
    client = _client([], [], [])
    body = client.get("/api/v1/dashboard/latest").json()
    assert body["areas"] == []


def test_dashboard_matches_station_within_threshold():
    client = _client([GeoArea(**KLODZKO)], [_station()], [_weather()])

    body = client.get("/api/v1/dashboard/latest").json()

    area = body["areas"][0]
    assert area["slug"] == "klodzko"
    assert area["air"]["station_id"] == "38"
    assert area["air"]["distance_km"] == 0.0
    assert area["air"]["params"]["PM2.5"]["value"] == 11.5
    assert area["weather"]["params"]["temperature_2m"]["value"] == 12.3


def test_dashboard_no_air_when_nearest_station_too_far():
    # Warszawa is ~362km from the only station (Kłodzko) - well past the 50km
    # threshold, so no fake match should be attached.
    client = _client([GeoArea(**WARSZAWA)], [_station()], [])

    body = client.get("/api/v1/dashboard/latest").json()

    assert body["areas"][0]["air"] is None


def test_dashboard_no_air_when_no_stations_at_all():
    client = _client([GeoArea(**KLODZKO)], [], [])

    body = client.get("/api/v1/dashboard/latest").json()

    assert body["areas"][0]["air"] is None


def test_dashboard_no_weather_when_no_snapshots():
    client = _client([GeoArea(**KLODZKO)], [], [])

    body = client.get("/api/v1/dashboard/latest").json()

    assert body["areas"][0]["weather"] is None


def test_dashboard_picks_nearest_of_multiple_stations():
    far_station = _station(
        station_id="99", latitude=52.2297, longitude=21.0122, source_record_id="b"
    )
    near_station = _station(station_id="38", source_record_id="a")
    client = _client([GeoArea(**KLODZKO)], [far_station, near_station], [])

    body = client.get("/api/v1/dashboard/latest").json()

    assert body["areas"][0]["air"]["station_id"] == "38"


def test_dashboard_marks_stale_air_reading():
    old = _station(observed_at=datetime.now(UTC) - timedelta(hours=10))
    client = _client([GeoArea(**KLODZKO)], [old], [])

    body = client.get("/api/v1/dashboard/latest").json()

    assert body["areas"][0]["air"]["params"]["PM2.5"]["freshness"] == "STALE"


def test_dashboard_air_has_source_transparency_fields():
    # TASK-7.1 (Master Plan Principle 2): source+observed_at+freshness together,
    # attribution text verbatim from source-registry.md.
    client = _client([GeoArea(**KLODZKO)], [_station()], [])

    body = client.get("/api/v1/dashboard/latest").json()

    air = body["areas"][0]["air"]
    assert air["source"] == "gios"
    assert air["attribution"] == "Dane: Główny Inspektorat Ochrony Środowiska (GIOŚ)"
    assert air["observed_at"] == air["params"]["PM2.5"]["observed_at"]


def test_dashboard_weather_has_source_transparency_fields():
    client = _client([GeoArea(**KLODZKO)], [], [_weather()])

    body = client.get("/api/v1/dashboard/latest").json()

    weather = body["areas"][0]["weather"]
    assert weather["source"] == "open_meteo"
    assert weather["attribution"] == "Weather data by Open-Meteo.com (CC BY 4.0)"


def test_dashboard_groups_multiple_params_for_nearest_station():
    pm25 = _station(param_code="PM2.5", value=11.5, source_record_id="a")
    no2 = _station(param_code="NO2", value=8.0, unit="µg/m³", source_record_id="b")
    client = _client([GeoArea(**KLODZKO)], [pm25, no2], [])

    body = client.get("/api/v1/dashboard/latest").json()

    params = body["areas"][0]["air"]["params"]
    assert set(params) == {"PM2.5", "NO2"}
    assert params["NO2"]["value"] == 8.0


def test_dashboard_station_query_filters_by_gios_source():
    # Codex review: `measurements` is shared with imgw_hydro (water_level_cm) —
    # without this filter the nearest-station join could match a river gauge
    # instead of an air station. _FakeSession ignores the stmt entirely, so this
    # inspects the station query's WHERE clause directly (not the full DISTINCT
    # ON select, which is Postgres-dialect-only and needs a real dialect to compile).
    captured = {}

    class _CapturingSession:
        def __init__(self):
            self._call = 0

        def execute(self, stmt):
            self._call += 1
            if self._call == 2:  # areas, then stations, then weather
                captured["where"] = str(
                    stmt.whereclause.compile(compile_kwargs={"literal_binds": True})
                )
            return _FakeResult([])

        def get(self, _model, _key):
            return None

    def _override():
        yield _CapturingSession()

    app.dependency_overrides[get_db] = _override
    try:
        client = TestClient(app)
        client.get("/api/v1/dashboard/latest")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert "source_id" in captured["where"] and "gios" in captured["where"]


def test_dashboard_weather_reports_per_param_freshness():
    # Codex P1 (PR #50): a stale hourly-derived param must not inherit the fresh
    # object-level status of `current` params.
    now = datetime.now(UTC)
    rows = [
        _weather(param_code="temperature_2m", observed_at=now, source_record_id="fresh"),
        _weather(
            param_code="uv_index",
            observed_at=now - timedelta(hours=10),
            source_record_id="stale",
        ),
    ]
    client = _client([GeoArea(**KLODZKO)], [], rows)

    weather = client.get("/api/v1/dashboard/latest").json()["areas"][0]["weather"]

    assert weather["freshness"] == "FRESH"
    assert weather["params"]["temperature_2m"]["freshness"] == "FRESH"
    assert weather["params"]["uv_index"]["freshness"] == "STALE"
    assert datetime.fromisoformat(weather["params"]["uv_index"]["observed_at"]) == now - timedelta(
        hours=10
    )


def _forecast(**overrides) -> Forecast:
    now = datetime.now(UTC)
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    defaults = {
        "source_id": "open_meteo",
        "source_record_id": "fc-1",
        "geo_area_id": 1,
        "param_code": "temperature_2m_max",
        "value": 18.5,
        "unit": "°C",
        "model": "auto",
        "forecast_reference_time": now,
        "valid_from": day,
        "valid_until": day + timedelta(days=1),
        "fetched_at": now,
    }
    defaults.update(overrides)
    return Forecast(**defaults)


def test_dashboard_includes_forecast_with_source_transparency():
    # TASK-5.5: forecast reaches the user via the dashboard aggregate.
    day2 = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    rows = [
        _forecast(param_code="temperature_2m_max", value=18.5),
        _forecast(param_code="temperature_2m_min", value=9.2, source_record_id="fc-2"),
        _forecast(valid_from=day2, valid_until=day2 + timedelta(days=1), source_record_id="fc-3"),
    ]
    client = _client([GeoArea(**KLODZKO)], [], [], rows)

    forecast = client.get("/api/v1/dashboard/latest").json()["areas"][0]["forecast"]

    assert forecast["source"] == "open_meteo"
    assert forecast["attribution"] == "Weather data by Open-Meteo.com (CC BY 4.0)"
    assert forecast["freshness"] == "FRESH"
    assert len(forecast["days"]) == 2
    assert forecast["days"][0]["params"]["temperature_2m_min"] == {"value": 9.2, "unit": "°C"}


def test_dashboard_forecast_null_when_no_forecast_rows():
    client = _client([GeoArea(**KLODZKO)], [], [])

    assert client.get("/api/v1/dashboard/latest").json()["areas"][0]["forecast"] is None


def _alert_row(**overrides) -> Alert:
    now = datetime.now(UTC)
    defaults = {
        "source_id": "imgw_warningshydro",
        "source_record_id": "a-1",
        "external_id": "1/2026",
        "event_type": "Susza hydrologiczna",
        "severity_raw": "-1",
        "probability_pct": None,
        "issuing_office": "Biuro Prognoz Hydrologicznych we Wrocławiu",
        "description": "opis",
        "comment": None,
        "areas": [{"wojewodztwo": "wielkopolskie"}],
        "valid_from": now - timedelta(days=1),
        "valid_until": now + timedelta(days=1),
        "published_at": now - timedelta(days=1),
        "fetched_at": now,
    }
    defaults.update(overrides)
    return Alert(**defaults)


def test_dashboard_includes_national_alerts_block():
    # TASK-7.2: alerts in the aggregate (§55), explicitly national until TASK-9.5.
    client = _client([GeoArea(**KLODZKO)], [], [], alert_rows=[_alert_row()])

    body = client.get("/api/v1/dashboard/latest").json()

    assert body["alerts"]["scope"] == "national"
    assert body["alerts"]["source"] == "imgw"
    assert body["alerts"]["attribution"].startswith("Źródłem pochodzenia danych jest Instytut")
    assert [a["event_type"] for a in body["alerts"]["items"]] == ["Susza hydrologiczna"]
    assert body["alerts"]["items"][0]["freshness"] == "FRESH"
    assert body["alerts"]["source_status"]["imgw_warningshydro"]["freshness"] == "UNAVAILABLE"
    # KLODZKO has no TERYT: the alert is flagged "unresolved", never presented as a match
    assert [a["geo_match"] for a in body["areas"][0]["local_alerts"]] == ["unresolved"]


def test_dashboard_local_alerts_are_matched_per_area_by_teryt():
    # ADR-013: national `alerts` stays unfiltered; each area gets only what applies to it.
    poznan = GeoArea(id=3, slug="poznan", name="Poznań", latitude=52.4, longitude=16.9)
    poznan.teryt_code = "3064011"  # wielkopolskie
    warszawa = GeoArea(**WARSZAWA)
    warszawa.teryt_code = "1465011"  # mazowieckie
    unlinked = GeoArea(**KLODZKO)  # no TERYT yet -> cannot be decided
    client = _client([poznan, warszawa, unlinked], [], [], alert_rows=[_alert_row()])

    body = client.get("/api/v1/dashboard/latest").json()

    local = {
        a["slug"]: [(x["geo_match"], x["description"]) for x in a["local_alerts"]]
        for a in body["areas"]
    }
    assert local == {
        "poznan": [("voivodeship", "opis")],
        "warszawa": [],
        "klodzko": [("unresolved", "opis")],
    }
    assert len(body["alerts"]["items"]) == 1  # national list untouched
    assert body["alerts"]["items"][0]["geo_match"] is None


def test_dashboard_alerts_items_empty_when_no_alerts():
    client = _client([GeoArea(**KLODZKO)], [], [])

    assert client.get("/api/v1/dashboard/latest").json()["alerts"]["items"] == []


# TASK-7.7 / ADR-016: `outdoor` per area, computed from the rows already loaded
# (no extra query - the fake session queue would run dry otherwise).
_GOOD_WEATHER = {
    "temperature_2m": (15.0, "°C"),
    "apparent_temperature": (14.0, "°C"),
    "precipitation": (0.0, "mm"),
    "wind_speed_10m": (10.0, "km/h"),
    "wind_gusts_10m": (20.0, "km/h"),
    "uv_index": (2.0, ""),
    "visibility": (20000.0, "m"),
    "weather_code": (3.0, "wmo code"),
}


def _outdoor_weather(age_hours: dict | None = None, **overrides) -> list[WeatherSnapshot]:
    now = datetime.now(UTC)
    values = {**_GOOD_WEATHER, **overrides}
    return [
        _weather(
            param_code=code,
            value=value,
            unit=unit,
            observed_at=now - timedelta(hours=(age_hours or {}).get(code, 0)),
            source_record_id=code,
        )
        for code, (value, unit) in values.items()
    ]


def _outdoor_air(**units) -> list[Measurement]:
    return [
        _station(param_code="PM2.5", value=8.0, unit=units.get("PM2.5", "µg/m³")),
        _station(
            param_code="PM10",
            value=20.0,
            unit=units.get("PM10", "µg/m³"),
            source_record_id="rec-2",
        ),
        _station(
            param_code="NO2",
            value=10.0,
            unit=units.get("NO2", "µg/m³"),
            source_record_id="rec-3",
        ),
        _station(
            param_code="O3",
            value=50.0,
            unit=units.get("O3", "µg/m³"),
            source_record_id="rec-4",
        ),
    ]


def _outdoor(stations, weather) -> dict:
    client = _client([GeoArea(**KLODZKO)], stations, weather)
    return client.get("/api/v1/dashboard/latest").json()["areas"][0]["outdoor"]


def test_dashboard_outdoor_good_with_full_fresh_inputs():
    outdoor = _outdoor(_outdoor_air(), _outdoor_weather())

    assert outdoor["level"] == "GOOD"
    assert outdoor["reasons"] == []
    assert outdoor["missing"] == []


def test_dashboard_outdoor_valid_until_is_earliest_input_expiry():
    # Codex (PR #68): a verdict judged from a 5h-old (RECENT, air bound 6h) reading is
    # valid for about one more hour, not for a fixed hour after the response arrives.
    now = datetime.now(UTC)
    air = _outdoor_air()
    for row in air:
        row.observed_at = now - timedelta(hours=5)

    outdoor = _outdoor(air, _outdoor_weather())

    assert outdoor["level"] == "GOOD"
    valid_until = datetime.fromisoformat(outdoor["valid_until"])
    assert now + timedelta(hours=1) <= valid_until <= datetime.now(UTC) + timedelta(hours=1)


def test_dashboard_outdoor_valid_until_ignores_stale_inputs_and_is_null_without_any():
    # A STALE input doesn't feed the verdict, so it can't set its expiry either.
    outdoor = _outdoor([], _outdoor_weather(age_hours={"wind_speed_10m": 10}))
    assert datetime.fromisoformat(outdoor["valid_until"]) > datetime.now(UTC)

    assert _outdoor([], [])["valid_until"] is None


def test_dashboard_outdoor_reason_payload_comes_verbatim_from_engine():
    outdoor = _outdoor(_outdoor_air(), _outdoor_weather(precipitation=(3.0, "mm")))

    assert outdoor["level"] == "POOR"
    assert outdoor["reasons"] == [
        {
            "code": "PRECIPITATION",
            "param": "precipitation",
            "value": 3.0,
            "threshold": 2.5,
            "comparison": "gte",
            "unit": "mm",
            "level": "POOR",
        }
    ]


def test_dashboard_outdoor_unit_mismatch_is_dropped_not_converted():
    # A PM2.5 of 80 in a different unit must neither count as 80 ug/m3 (-> POOR) nor
    # be converted by us: dropped, and with PM10 also off-unit the air group is
    # unusable -> UNKNOWN + missing[].
    air = _outdoor_air(**{"PM2.5": "mg/m³", "PM10": "mg/m³"})
    air[0].value = 80.0
    outdoor = _outdoor(air, _outdoor_weather())

    assert outdoor["level"] == "UNKNOWN"
    assert outdoor["reasons"] == []
    assert [m["group"] for m in outdoor["missing"]] == ["air"]
    assert outdoor["missing"][0]["params"] == ["pm10", "pm25"]
    assert outdoor["missing"][0]["blocking"] is True


def test_dashboard_outdoor_no2_o3_and_storm_feed_the_verdict():
    air = _outdoor_air()
    air[2].value = 70.0  # NO2 > 60 -> POOR
    air[3].value = 110.0  # O3 > 100 -> MODERATE
    outdoor = _outdoor(air, _outdoor_weather(weather_code=(96.0, "wmo code")))

    assert outdoor["level"] == "POOR"
    assert [(r["code"], r["level"]) for r in outdoor["reasons"]] == [
        ("NO2_HIGH", "POOR"),
        ("STORM", "POOR"),
        ("O3_HIGH", "MODERATE"),
    ]


def test_dashboard_outdoor_station_without_no2_o3_is_still_good_but_reported():
    air = _outdoor_air()[:2]  # PM only, as at many GIOŚ stations
    outdoor = _outdoor(air, _outdoor_weather())

    assert outdoor["level"] == "GOOD"
    assert [(m["group"], m["core"], m["blocking"]) for m in outdoor["missing"]] == [
        ("no2", False, True),
        ("o3", False, True),
    ]


def test_dashboard_outdoor_no2_o3_in_a_foreign_unit_are_dropped_not_converted():
    air = _outdoor_air(**{"NO2": "mg/m³", "O3": "mg/m³"})
    air[2].value = 500.0
    outdoor = _outdoor(air, _outdoor_weather())

    assert outdoor["level"] == "GOOD" and outdoor["reasons"] == []
    assert {m["group"] for m in outdoor["missing"]} == {"no2", "o3"}


def test_dashboard_outdoor_one_pm_param_is_enough_but_absence_reported():
    air = _outdoor_air(**{"PM10": "mg/m³"})
    outdoor = _outdoor(air, _outdoor_weather())

    assert outdoor["level"] == "GOOD"
    assert outdoor["missing"] == [
        {"group": "air", "params": ["pm10"], "status": "MISSING", "core": True, "blocking": False}
    ]


def test_dashboard_outdoor_stale_input_is_not_used_and_blocks_good():
    # Wind is 10h old -> STALE (8h weather bound): a calm-looking value must not
    # produce a confident GOOD (rule #8).
    outdoor = _outdoor(_outdoor_air(), _outdoor_weather(age_hours={"wind_speed_10m": 10}))

    assert outdoor["level"] == "UNKNOWN"
    wind = [m for m in outdoor["missing"] if m["group"] == "wind"]
    assert wind == [
        {
            "group": "wind",
            "params": ["wind_speed_10m"],
            "status": "STALE",
            "core": True,
            "blocking": True,
        }
    ]


def test_dashboard_outdoor_unknown_without_any_data():
    outdoor = _outdoor([], [])

    assert outdoor["level"] == "UNKNOWN"
    assert outdoor["reasons"] == []
    assert {m["group"] for m in outdoor["missing"]} >= {"air", "thermal", "wind", "precipitation"}


# --- TASK-4.2: European AQI in the air block ---------------------------------


def _eaqi_rows(**values) -> list[Measurement]:
    base = {"PM2.5": 3.0, "PM10": 10.0, "NO2": 5.0, "O3": 40.0, "SO2": 10.0}
    base.update(values)
    return [_station(param_code=c, value=v, source_record_id=c) for c, v in base.items()]


def test_dashboard_air_index_uses_loaded_params_and_is_worst_subindex():
    client = _client([GeoArea(**KLODZKO)], _eaqi_rows(O3=130.0), [])

    index = client.get("/api/v1/dashboard/latest").json()["areas"][0]["air"]["index"]

    assert index["level"] == "POOR" and index["complete"] is True
    assert index["dominant"] == ["O3"]
    assert index["params"]["PM2.5"] == "GOOD"


def test_dashboard_air_index_is_no_index_without_minimum_set():
    client = _client([GeoArea(**KLODZKO)], [_station()], [])  # PM2.5 alone

    index = client.get("/api/v1/dashboard/latest").json()["areas"][0]["air"]["index"]

    assert index["level"] is None and index["complete"] is False
    assert {"NO2", "O3"} <= set(index["missing"])


def test_dashboard_lists_only_actively_polled_areas():
    """ADR-019: imported gminas (weather_polling_active=false) must not fan out into the
    dashboard. FakeSession ignores statements, so assert on the compiled area query."""
    statements = []

    class _Recording(_FakeSession):
        def execute(self, stmt):
            statements.append(stmt)
            return super().execute(stmt)

    def _override():
        yield _Recording([GeoArea(**KLODZKO)], [], [], [], [], [])

    app.dependency_overrides[get_db] = _override
    assert TestClient(app).get("/api/v1/dashboard/latest").status_code == 200

    area_sql = str(statements[0].compile())
    assert "geo_areas.weather_polling_active IS" in area_sql


def _pollen_row(hours_old: float = 1, **species) -> PollenSnapshot:
    now = datetime.now(UTC)
    slot = now.replace(minute=0, second=0, microsecond=0)
    fetched = now - timedelta(hours=hours_old)
    return PollenSnapshot(
        source_id="open_meteo_pollen",
        source_record_id="1:x",
        geo_area_id=1,
        unit="grains/m³",
        model="cams_europe",
        forecast_reference_time=fetched.replace(hour=0, minute=0, second=0, microsecond=0),
        valid_at=slot,
        fetched_at=fetched,
        **species,
    )


def _pollen_ok_status(hours_old: float = 1) -> dict:
    last = datetime.now(UTC) - timedelta(hours=hours_old)
    return {"open_meteo_pollen": SourceStatus(source_id="open_meteo_pollen", last_success_at=last)}


def _pollen_body(**kw) -> dict:
    client = _client([GeoArea(**KLODZKO)], [], [], **kw)
    return client.get("/api/v1/dashboard/latest").json()["areas"][0]["pollen"]


def test_dashboard_pollen_is_model_forecast_with_adr020_fields_and_nulls_kept():
    row = _pollen_row(birch=12.5, alder=0.0)  # grass/mugwort/ragweed: no model value
    pollen = _pollen_body(pollen=([row], [GeoArea(**KLODZKO)]), status_rows=_pollen_ok_status())

    assert pollen["kind"] == "model_forecast"
    assert pollen["source"] == "open_meteo_pollen"
    assert pollen["model"] == "cams_europe" and pollen["unit"] == "grains/m³"
    assert pollen["freshness"] == "FRESH"
    assert pollen["source_status"]["freshness"] == "FRESH"
    assert pollen["forecast_reference_time"] and pollen["fetched_at"] and pollen["valid_at"]
    assert pollen["current"] == {
        "alder": 0.0,  # modelled zero stays 0
        "birch": 12.5,
        "grass": None,  # missing stays null, never 0
        "mugwort": None,
        "ragweed": None,
    }
    assert pollen["days"][0]["max"]["birch"] == 12.5
    assert pollen["attribution"] == ATTRIBUTION


def test_dashboard_pollen_unavailable_without_snapshot():
    pollen = _pollen_body(pollen=([], []))

    assert pollen["freshness"] == "UNAVAILABLE"
    assert pollen["source_status"] == {"freshness": "UNAVAILABLE", "last_success_at": None}
    assert pollen["current"] is None and pollen["days"] == []
    assert pollen["kind"] == "model_forecast"


def test_dashboard_pollen_old_snapshot_is_stale():
    row = _pollen_row(hours_old=100, birch=5.0)
    pollen = _pollen_body(
        pollen=([row], [GeoArea(**KLODZKO)]), status_rows=_pollen_ok_status(hours_old=100)
    )

    assert pollen["freshness"] == "STALE"
    assert pollen["source_status"]["freshness"] == "STALE"


def _assert_pollen_degraded_rest_intact(client, caplog):
    resp = client.get("/api/v1/dashboard/latest")

    assert resp.status_code == 200
    body = resp.json()
    area = body["areas"][0]
    assert area["air"]["station_id"] == "38"
    assert area["weather"]["params"]["temperature_2m"]["value"] == 12.3
    assert area["pollen"]["freshness"] == "UNAVAILABLE"
    assert area["pollen"]["source_status"] == {"freshness": "UNAVAILABLE", "last_success_at": None}
    assert area["pollen"]["current"] is None
    assert body["alerts"]["scope"] == "national"
    assert "dashboard: pollen block failed" in caplog.text


def test_dashboard_pollen_read_failure_is_isolated_and_logged(monkeypatch, caplog):
    def boom(_db):
        raise RuntimeError("pollen read down")

    monkeypatch.setattr("app.api.v1.dashboard.latest_pollen", boom)
    client = _client([GeoArea(**KLODZKO)], [_station()], [_weather()])
    _assert_pollen_degraded_rest_intact(client, caplog)


def test_dashboard_pollen_block_build_failure_is_isolated_and_logged(monkeypatch, caplog):
    real = pollen_block
    calls = {"n": 0}

    def once(area, status):  # the first call (normal path) breaks; the fallback works
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("block build broke")
        return real(area, status)

    monkeypatch.setattr("app.api.v1.dashboard.pollen_block", once)
    client = _client([GeoArea(**KLODZKO)], [_station()], [_weather()])
    _assert_pollen_degraded_rest_intact(client, caplog)


def test_dashboard_air_has_assignment_provenance():
    # ADR-025: station id + distance + method tell where the area's air data comes from.
    near = _station(station_id="38", latitude=50.45, longitude=16.66)
    client = _client([GeoArea(**KLODZKO)], [near], [])

    air = client.get("/api/v1/dashboard/latest").json()["areas"][0]["air"]

    assert air["station_id"] == "38"
    assert air["assignment_method"] == "nearest_station"
    assert 0 < air["distance_km"] < 5


def test_dashboard_tie_between_stations_picks_lowest_id_regardless_of_row_order():
    a = _station(station_id="10", source_record_id="a", latitude=50.5, longitude=16.7)
    b = _station(station_id="9", source_record_id="b", latitude=50.5, longitude=16.7)

    for rows in ([a, b], [b, a]):
        client = _client([GeoArea(**KLODZKO)], rows, [])
        air = client.get("/api/v1/dashboard/latest").json()["areas"][0]["air"]
        assert air["station_id"] == "9"


def test_dashboard_station_beyond_100_km_is_not_assigned_and_coverage_is_none():
    # ~107 km north of Kłodzko: past REGIONAL_MAX_KM (ADR-029) -> no air, coverage none.
    client = _client([GeoArea(**KLODZKO)], [_station(latitude=51.40)], [])

    area = client.get("/api/v1/dashboard/latest").json()["areas"][0]

    assert area["air"] is None
    assert area["coverage"]["air"] == "none"
    assert area["coverage"]["air_radius_km"] is None


@pytest.mark.parametrize(
    ("station_lat", "level", "radius"),
    [(50.45, "exact", 10), (50.70, "nearby", 50), (50.93, "regional", 100)],  # ~2 / 30 / 55 km
)
def test_dashboard_air_coverage_levels_are_explicit(station_lat, level, radius):
    client = _client([GeoArea(**KLODZKO)], [_station(latitude=station_lat)], [])

    area = client.get("/api/v1/dashboard/latest").json()["areas"][0]

    assert area["air"]["coverage"] == level
    assert area["air"]["coverage_radius_km"] == radius
    assert area["coverage"]["air"] == level
    assert area["coverage"]["air_radius_km"] == radius
    assert area["air"]["station_name"] and area["air"]["distance_km"] > 0


def test_dashboard_weather_and_pollen_are_described_as_grid():
    cov = (
        _client([GeoArea(**KLODZKO)], [], [])
        .get("/api/v1/dashboard/latest")
        .json()["areas"][0]["coverage"]
    )

    assert cov["weather"] == "grid" and cov["pollen"] == "grid"
    assert "nie pomiar" in cov["grid_description"]


def test_dashboard_regional_air_is_shown_but_never_feeds_the_outdoor_verdict():
    # ADR-029: perfect PM values from a station 55 km away must not make "Na dwór" GOOD.
    far_air = [
        _station(latitude=50.93, param_code="PM2.5", value=8.0),
        _station(latitude=50.93, param_code="PM10", value=20.0, source_record_id="rec-2"),
    ]
    client = _client([GeoArea(**KLODZKO)], far_air, _outdoor_weather())

    area = client.get("/api/v1/dashboard/latest").json()["areas"][0]

    assert area["air"]["coverage"] == "regional"
    assert set(area["air"]["params"]) == {"PM2.5", "PM10"}  # still disclosed
    assert area["outdoor"]["level"] == "UNKNOWN"
    # air (core) blocks GOOD; the optional NO2/O3 groups are reported but never block.
    assert [m["group"] for m in area["outdoor"]["missing"] if m["blocking"] and m["core"]] == [
        "air"
    ]
    assert {m["group"] for m in area["outdoor"]["missing"]} == {"air", "no2", "o3"}


def test_dashboard_regional_air_does_not_hide_a_bad_weather_verdict():
    far_air = [_station(latitude=50.93, param_code="PM2.5", value=8.0)]
    weather = _outdoor_weather(precipitation=(3.0, "mm"))
    client = _client([GeoArea(**KLODZKO)], far_air, weather)

    outdoor = client.get("/api/v1/dashboard/latest").json()["areas"][0]["outdoor"]

    assert outdoor["level"] == "POOR"


def test_dashboard_nearby_air_still_feeds_the_outdoor_verdict():
    near_air = _outdoor_air()
    for row in near_air:
        row.latitude = 50.70  # ~30 km: nearby, unchanged behaviour
    outdoor = _outdoor(near_air, _outdoor_weather())

    assert outdoor["level"] == "GOOD"


def _cat(sid, lat, lon):
    from app.models import GiosStation

    return GiosStation(
        station_id=sid,
        station_name="s",
        latitude=lat,
        longitude=lon,
        raw={},
        fetched_at=datetime.now(UTC),
    )


def test_dashboard_never_assigns_a_station_dropped_from_the_catalog():
    # Station 38 is nearest but no longer in the GIOŚ catalog (its old measurements stay):
    # the area must use the live catalog station 40, not the retired one.
    retired = _station(station_id="38", source_record_id="a")
    live = _station(station_id="40", source_record_id="b", latitude=50.5, longitude=16.7)
    client = _client(
        [GeoArea(**KLODZKO)],
        [retired, live],
        [],
        catalog=[_cat("40", 50.5, 16.7), _cat("41", 50.9, 16.7)],
    )

    air = client.get("/api/v1/dashboard/latest").json()["areas"][0]["air"]

    assert air["station_id"] == "40"


def test_dashboard_uses_catalog_coordinates_not_the_stale_measured_ones():
    # Measurements still carry the old position (50.43, 16.65 = on top of the area); the
    # catalog says the station moved ~119 km away -> out of range, same as polling decides.
    moved = _station(station_id="38")
    client = _client([GeoArea(**KLODZKO)], [moved], [], catalog=[_cat("38", 51.5, 16.65)])

    assert client.get("/api/v1/dashboard/latest").json()["areas"][0]["air"] is None


def test_dashboard_env_override_station_outside_catalog_keeps_measured_coordinates(monkeypatch):
    monkeypatch.setenv("GIOS_STATION_IDS", "38")
    only_env = _station(station_id="38")
    client = _client([GeoArea(**KLODZKO)], [only_env], [], catalog=[_cat("40", 52.0, 21.0)])

    assert client.get("/api/v1/dashboard/latest").json()["areas"][0]["air"]["station_id"] == "38"


def _status(source_id: str, hours_old: float | None) -> dict:
    last = None if hours_old is None else datetime.now(UTC) - timedelta(hours=hours_old)
    return {source_id: SourceStatus(source_id=source_id, last_success_at=last)}


def _air_weather(status_rows=None) -> dict:
    client = _client([GeoArea(**KLODZKO)], [_station()], [_weather()], status_rows=status_rows)
    return client.get("/api/v1/dashboard/latest").json()["areas"][0]


def test_dashboard_air_and_weather_source_status_fresh():
    rows = _status("gios", 0.5) | _status("open_meteo", 1)
    area = _air_weather(rows)

    assert area["air"]["source_status"]["freshness"] == "FRESH"
    assert area["weather"]["source_status"]["freshness"] == "FRESH"
    assert area["air"]["source_status"]["last_success_at"]


def test_dashboard_source_status_unavailable_without_a_run_row():
    # Data rows exist (e.g. ingested before ADR-012) but the source never recorded a success.
    area = _air_weather()
    unavailable = {"freshness": "UNAVAILABLE", "last_success_at": None}

    assert area["air"]["source_status"] == unavailable
    assert area["weather"]["source_status"] == unavailable


def test_dashboard_source_status_stale_uses_each_domains_own_thresholds():
    # 7h: past air's RECENT bound (6h) but within weather's (8h).
    area = _air_weather(_status("gios", 7) | _status("open_meteo", 7))

    assert area["air"]["source_status"]["freshness"] == "STALE"
    assert area["weather"]["source_status"]["freshness"] == "RECENT"
    # Row labels stay row-based: a fresh row under a stale source is the client's call.
    assert area["air"]["params"]["PM2.5"]["freshness"] == "FRESH"


def test_dashboard_source_status_never_succeeded_row_is_unavailable():
    area = _air_weather(_status("gios", None) | _status("open_meteo", None))

    assert area["air"]["source_status"]["freshness"] == "UNAVAILABLE"
    assert area["weather"]["source_status"]["freshness"] == "UNAVAILABLE"


def test_dashboard_source_status_success_from_the_future_reads_stale():
    # MAX_CLOCK_SKEW guard (ADR-012): an unverifiable future success is never FRESH.
    area = _air_weather(_status("gios", -2) | _status("open_meteo", -2))

    assert area["air"]["source_status"]["freshness"] == "STALE"
    assert area["weather"]["source_status"]["freshness"] == "STALE"


def test_dashboard_source_status_failure_is_isolated_and_logged(monkeypatch, caplog):
    real = source_freshness

    def flaky(db, source_id, freshness):
        if source_id in ("gios", "open_meteo"):
            raise RuntimeError("status table down")
        return real(db, source_id, freshness)

    monkeypatch.setattr("app.api.v1.dashboard.source_freshness", flaky)
    client = _client([GeoArea(**KLODZKO)], [_station()], [_weather()])

    resp = client.get("/api/v1/dashboard/latest")

    assert resp.status_code == 200
    body = resp.json()
    area = body["areas"][0]
    down = {"freshness": "UNAVAILABLE", "last_success_at": None}
    assert area["air"]["source_status"] == down
    assert area["weather"]["source_status"] == down
    assert area["air"]["params"]["PM2.5"]["value"] == 11.5  # data blocks untouched
    assert area["weather"]["params"]["temperature_2m"]["value"] == 12.3
    assert body["alerts"]["scope"] == "national"
    assert "dashboard: source_status for gios failed" in caplog.text


def test_dashboard_top_level_source_status_survives_null_blocks():
    # No station / no snapshot -> air and weather are null, yet the client can still tell
    # a source that never succeeded from a healthy one with nothing applicable.
    rows = _status("gios", 1)  # open_meteo has no row
    client = _client([GeoArea(**KLODZKO)], [], [], status_rows=rows)

    body = client.get("/api/v1/dashboard/latest").json()

    assert body["areas"][0]["air"] is None and body["areas"][0]["weather"] is None
    assert body["source_status"]["air"]["freshness"] == "FRESH"
    assert body["source_status"]["weather"] == {"freshness": "UNAVAILABLE", "last_success_at": None}


# --- ?geo_area_id= (TASK-6.2(8), ADR-026) ----------------------------------------------


def test_dashboard_geo_area_id_narrows_to_that_area():
    klodzko, warszawa = GeoArea(**KLODZKO), GeoArea(**WARSZAWA)
    client = _client([], [_station()], [_weather()], lookup=[klodzko, warszawa])

    body = client.get("/api/v1/dashboard/latest?geo_area_id=1").json()

    assert [a["geo_area_id"] for a in body["areas"]] == [1]
    area = body["areas"][0]
    assert area["weather_polling_active"] is True
    assert area["air"]["station_id"] == "38" and area["weather"] is not None
    assert body["alerts"]["scope"] == "national"  # semantics unchanged


def test_dashboard_geo_area_id_unknown_is_404():
    client = _client([], [], [], lookup=[GeoArea(**KLODZKO)])
    assert client.get("/api/v1/dashboard/latest?geo_area_id=99").status_code == 404


def test_dashboard_without_param_lists_polled_areas_as_before():
    client = _client([GeoArea(**KLODZKO), GeoArea(**WARSZAWA)], [], [])
    body = client.get("/api/v1/dashboard/latest").json()
    assert [a["geo_area_id"] for a in body["areas"]] == [1, 2]


def test_dashboard_inactive_area_is_explicit_no_data():
    # An imported gmina nobody polls: still answerable and flagged. weather/forecast/pollen
    # are empty; air comes from a catalog station within 50 km (select_stations works for any
    # area, honest + useful); outdoor from that air alone must NOT be GOOD (core groups missing).
    gmina = GeoArea(**{**KLODZKO, "id": 7, "slug": "x", "weather_polling_active": False})
    client = _client([], _outdoor_air(), [], lookup=[gmina])

    area = client.get("/api/v1/dashboard/latest?geo_area_id=7").json()["areas"][0]

    assert area["weather_polling_active"] is False
    assert area["air"]["station_id"] == "38"
    assert area["weather"] is None and area["forecast"] is None
    assert area["outdoor"]["level"] == "UNKNOWN"
    assert {m["group"] for m in area["outdoor"]["missing"] if m["blocking"]} >= {"thermal"}
    assert area["pollen"]["freshness"] == "UNAVAILABLE" and area["pollen"]["current"] is None


def test_dashboard_inactive_area_without_station_has_every_block_empty():
    gmina = GeoArea(**{**KLODZKO, "id": 7, "slug": "x", "weather_polling_active": False})
    area = (
        _client([], [], [], lookup=[gmina]).get("/api/v1/dashboard/latest?geo_area_id=7").json()
    )["areas"][0]
    assert area["air"] is None and area["weather"] is None and area["outdoor"]["level"] == "UNKNOWN"


@pytest.mark.parametrize("path", ["dashboard/latest", "alerts/latest", "air/latest"])
@pytest.mark.parametrize("value", ["0", "-1", "2147483648", "abc"])
def test_geo_area_id_is_range_checked_422(path, value):
    client = _client([], [], [], lookup=[GeoArea(**KLODZKO)])
    assert client.get(f"/api/v1/{path}?geo_area_id={value}").status_code == 422


def test_dashboard_geo_area_id_not_int_is_422():
    client = _client([], [], [], lookup=[GeoArea(**KLODZKO)])
    assert client.get("/api/v1/dashboard/latest?geo_area_id=abc").status_code == 422


def test_dashboard_coverage_follows_the_catalog_even_before_the_first_measurement():
    # Nearest catalog station (~2 km) has no measurement yet; a measured one sits ~55 km away.
    # Polling assigned the near one, so: no air block, coverage "exact" - not the far station.
    far = _station(station_id="40", latitude=50.93)
    client = _client(
        [GeoArea(**KLODZKO)],
        [far],
        [],
        catalog=[_cat("41", 50.45, 16.65), _cat("40", 50.93, 16.65)],
    )

    area = client.get("/api/v1/dashboard/latest").json()["areas"][0]

    assert area["air"] is None
    assert area["coverage"]["air"] == "exact"


def test_default_area_list_excludes_user_chosen_places(monkeypatch):
    # ADR-029: one user activating a place must not change everyone's default dashboard.
    seen = []
    original = _FakeSession.execute

    def spy(self, stmt):
        seen.append(str(stmt))
        return original(self, stmt)

    monkeypatch.setattr(_FakeSession, "execute", spy)
    _client([GeoArea(**KLODZKO)], [], []).get("/api/v1/dashboard/latest")

    assert "place_id IS NULL" in seen[0] and "weather_polling_active" in seen[0]


def test_weather_query_is_scoped_to_the_listed_areas(monkeypatch):
    seen = []
    original = _FakeSession.execute

    def spy(self, stmt):
        seen.append(str(stmt))
        return original(self, stmt)

    monkeypatch.setattr(_FakeSession, "execute", spy)
    _client([GeoArea(**KLODZKO)], [], []).get("/api/v1/dashboard/latest")

    weather = next(q for q in seen if "FROM weather_snapshots" in q)
    assert "weather_snapshots.geo_area_id IN" in weather
