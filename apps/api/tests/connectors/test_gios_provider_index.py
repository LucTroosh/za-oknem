import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.api.v1.air import ProviderIndexResponse, provider_index
from app.config import settings
from app.connectors.gios import client
from app.connectors.gios.parser import GiosParseError
from app.connectors.gios.provider_index import ingest_index, parse_index
from app.models import GeoArea, GiosProviderIndex, Measurement

EVIDENCE = Path(__file__).resolve().parents[4] / "docs/data/gios/evidence/air-live/index-52.json"


def payload():
    return json.loads(EVIDENCE.read_text())


def test_real_index_preserves_source_scale_labels_and_dates_and_rejects_invalid_data():
    partial = json.loads((EVIDENCE.parent / "index-11.json").read_text())
    parsed_partial = parse_index(partial, "11", datetime(2026, 10, 4, tzinfo=UTC))
    assert parsed_partial.params["PM2.5"].level is None
    raw = payload()
    data = parse_index(raw, "52", datetime(2026, 10, 4, tzinfo=UTC))
    assert data.index.level == raw["AqIndex"]["Wartość indeksu"]
    assert data.index.label == raw["AqIndex"]["Nazwa kategorii indeksu"]
    assert data.index.observed_at.endswith("+00:00")
    assert data.index.observed_at < data.index.calculated_at
    assert set(data.params) == {"SO2", "NO2", "PM10", "PM2.5", "O3"}
    for key, value in [
        ("Wartość indeksu", 99),
        ("Wartość indeksu", True),
        ("Data wykonania obliczeń indeksu", "2026-10-25 02:00:00"),
        ("Nazwa kategorii indeksu", None),
        ("Identyfikator stacji pomiarowej", 53),
    ]:
        bad = deepcopy(raw)
        bad["AqIndex"][key] = value
        with pytest.raises(GiosParseError):
            parse_index(bad, "52", datetime(2026, 10, 26, tzinfo=UTC))


def test_failure_keeps_snapshot_no_index_clears_it_and_api_ages_source_time(
    monkeypatch, db_session
):
    monkeypatch.setattr(settings, "gios_provider_index_enabled", True)
    monkeypatch.setattr(client, "fetch_index", lambda sid: payload())
    area = GeoArea(slug="test", name="Test", latitude=50, longitude=19)
    now = datetime.now(UTC)
    db_session.add(area)
    db_session.add(
        Measurement(
            source_id="gios",
            source_record_id="52:one",
            station_id="52",
            station_name="Test station",
            latitude=50,
            longitude=19,
            param_code="PM2.5",
            value=10,
            unit="µg/m³",
            observed_at=now - timedelta(hours=1),
            fetched_at=now,
        )
    )
    db_session.commit()
    assert ingest_index("52", db_session)
    row = db_session.get(GiosProviderIndex, "52")
    original = deepcopy(row.payload)
    # A fresh fetch must not rejuvenate a stale input timestamp.
    original["index"]["observed_at"] = (now - timedelta(hours=8)).isoformat()
    row.payload = original
    db_session.commit()
    body = ProviderIndexResponse.model_validate(provider_index(area.id, db_session))
    assert body.availability == "available" and body.freshness == "STALE"

    def fail(sid):
        raise client.GiosApiError("offline")

    monkeypatch.setattr(client, "fetch_index", fail)
    assert not ingest_index("52", db_session)
    body = ProviderIndexResponse.model_validate(provider_index(area.id, db_session))
    assert body.retrieval_status == "degraded" and row.payload == original
    monkeypatch.setattr(
        client, "fetch_index", lambda sid: {"AqIndex": {"Identyfikator stacji pomiarowej": 52}}
    )
    assert not ingest_index("52", db_session)
    assert row.payload == original and row.last_attempt_succeeded is False
    empty = payload()
    empty["AqIndex"]["Wartość indeksu"] = None
    empty["AqIndex"]["Status indeksu ogólnego dla stacji pomiarowej"] = False
    monkeypatch.setattr(client, "fetch_index", lambda sid: empty)
    assert ingest_index("52", db_session)
    body = ProviderIndexResponse.model_validate(provider_index(area.id, db_session))
    assert body.availability == "no_index" and body.freshness == "UNAVAILABLE"
    assert body.data.index.level is None and body.retrieval_status == "ok"
    monkeypatch.setattr(settings, "gios_provider_index_enabled", False)
    assert provider_index(area.id, db_session)["availability"] == "disabled"
