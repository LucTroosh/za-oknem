"""Tests for GET /api/v1/dashboard/latest: nearest-station join (ADR-006).

Same fake-session approach as test_air.py/test_weather.py (Postgres DISTINCT ON,
SQLite can't compile it). Three execute() calls in order: geo_areas, stations,
weather snapshots.
"""

from datetime import UTC, datetime, timedelta

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

KLODZKO = {
    "id": 1,
    "slug": "klodzko",
    "name": "Kłodzko",
    "latitude": 50.433493,
    "longitude": 16.65366,
}
WARSZAWA = {
    "id": 2,
    "slug": "warszawa",
    "name": "Warszawa",
    "latitude": 52.2297,
    "longitude": 21.0122,
}


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, *result_sets, status_rows=None):
        self._queue = list(result_sets)
        self._status_rows = status_rows or {}

    def execute(self, _stmt):
        return _FakeResult(self._queue.pop(0))

    def rollback(self):
        pass

    def get(self, _model, key):
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
) -> TestClient:
    # Query order in dashboard_latest(): areas, stations, GIOŚ catalog ids (ADR-025; empty =
    # no catalog yet), weather, forecasts, alerts, then pollen snapshots (+ geo_areas when
    # there are snapshots).
    def _override():
        sets = [areas, stations, list(catalog), weather_rows, list(forecast_rows)]
        sets.append(list(alert_rows))
        rows, pollen_areas = pollen
        sets += [rows, pollen_areas] if rows else [rows]
        yield _FakeSession(*sets, status_rows=status_rows)

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
    assert "alerts" not in body["areas"][0]  # never presented as local


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


def test_dashboard_station_just_beyond_limit_is_not_assigned():
    # ~55 km north of Kłodzko: the only station exists, but past MAX_MATCH_DISTANCE_KM.
    client = _client([GeoArea(**KLODZKO)], [_station(latitude=50.93)], [])

    assert client.get("/api/v1/dashboard/latest").json()["areas"][0]["air"] is None


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
    # catalog says the station moved ~60 km away -> out of range, same as polling decides.
    moved = _station(station_id="38")
    client = _client([GeoArea(**KLODZKO)], [moved], [], catalog=[_cat("38", 50.97, 16.65)])

    assert client.get("/api/v1/dashboard/latest").json()["areas"][0]["air"] is None


def test_dashboard_env_override_station_outside_catalog_keeps_measured_coordinates(monkeypatch):
    monkeypatch.setenv("GIOS_STATION_IDS", "38")
    only_env = _station(station_id="38")
    client = _client([GeoArea(**KLODZKO)], [only_env], [], catalog=[_cat("40", 52.0, 21.0)])

    assert client.get("/api/v1/dashboard/latest").json()["areas"][0]["air"]["station_id"] == "38"
