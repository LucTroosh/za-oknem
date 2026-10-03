"""GIOŚ open-data client (ADR-032 pkt 9): the real envelope rules and the bounded retry. The bodies
below are the ones recorded on 2026-10-03 in docs/data/gios/evidence/. httpx.get is mocked: no
network (rule: connector isolation)."""

import json
from unittest.mock import MagicMock

import httpx
import pytest

from app.config import settings
from app.gios_open import client as gc
from app.gios_open.errors import (
    GiosOpenContractError,
    GiosOpenSourceError,
    GiosOpenTransportError,
)

# --- recorded bodies ---------------------------------------------------------------------------
BLAD_200 = {
    "wynik": {
        "idZdarzenia": "756aef9b-8829-434f-9e3d-18979a70b7d5",
        "status": "BLAD",
        "data": "2026-10-03T10:23:54",
        "blad": {"kod": "400", "opis": "Parametr wojewodztwo ma niepoprawną wartość"},
    }
}
NOISE_OK = {
    "dane": {
        "liczbaRekordow": 1,
        "strona": [
            {
                "kodPunktuPomiarowego": "D_24_001020_001",
                "miejscowosc": "Żyglin",
                "coordWgs84X": 18.948417,
                "coordWgs84Y": 50.484861,
                "wynikPomiaru": 64.5,
            }
        ],
    },
    "wynik": {"idZdarzenia": "ee76458e", "status": "SUKCES", "data": "2026-10-03T10:25:05"},
}
EMPTY_OBSERVED = {
    "dane": {"liczbaRekordow": 0},
    "wynik": {"idZdarzenia": "2bf943c4", "status": "SUKCES", "data": "2026-10-03T10:23:55"},
}


class TestParseEnvelope:
    def test_blad_with_http_200_is_a_source_error_not_an_empty_result(self):
        with pytest.raises(GiosOpenSourceError) as exc:
            gc.parse_envelope(BLAD_200)
        assert exc.value.code == "400"
        assert "wojewodztwo" in (exc.value.description or "")
        assert exc.value.event_id == "756aef9b-8829-434f-9e3d-18979a70b7d5"

    def test_records_and_reported_count(self):
        page = gc.parse_envelope(NOISE_OK)
        assert [r["miejscowosc"] for r in page.records] == ["Żyglin"]
        assert page.reported_count == 1
        assert page.empty_observed is False
        assert page.event_id == "ee76458e"

    def test_sukces_with_zero_and_no_strona_is_an_observed_empty_result(self):
        page = gc.parse_envelope(EMPTY_OBSERVED)
        assert page.records == []
        assert page.empty_observed is True
        assert page.reported_count == 0

    def test_empty_strona_list_is_also_empty(self):
        body = {"dane": {"strona": [], "liczbaRekordow": 0}, "wynik": {"status": "SUKCES"}}
        assert gc.parse_envelope(body).empty_observed is True

    def test_reported_count_is_not_a_total(self):
        # Live: liczbaRekordow equalled the page size. We keep it as reported, nothing more.
        body = {
            "dane": {"strona": [{"a": 1}], "liczbaRekordow": 999},
            "wynik": {"status": "SUKCES"},
        }
        page = gc.parse_envelope(body)
        assert len(page.records) == 1 and page.reported_count == 999

    @pytest.mark.parametrize(
        "body",
        [
            {"wynik": {"status": "SUKCES"}},  # no `dane`
            {"dane": {}, "wynik": {"status": "SUKCES"}},  # no strona, no count
            {
                "dane": {"liczbaRekordow": 3},
                "wynik": {"status": "SUKCES"},
            },  # claims rows, none sent
            {"dane": {"strona": "x"}, "wynik": {"status": "SUKCES"}},
            {"dane": {"strona": [1]}, "wynik": {"status": "SUKCES"}},
            {"dane": {"strona": []}, "wynik": {"status": "WARIANT"}},  # unknown status
            {"dane": {"strona": []}},  # no envelope
            [],
            "text",
        ],
    )
    def test_anything_else_is_a_contract_error(self, body):
        with pytest.raises(GiosOpenContractError):
            gc.parse_envelope(body)

    def test_geojson_variant_without_wynik(self):
        body = {"features": [{"type": "Feature"}], "liczbaRekordow": 1}
        page = gc.parse_envelope(body)
        assert page.records == [{"type": "Feature"}]

    def test_bool_is_not_a_count(self):
        body = {
            "dane": {"strona": [{"a": 1}], "liczbaRekordow": True},
            "wynik": {"status": "SUKCES"},
        }
        assert gc.parse_envelope(body).reported_count is None


# --- transport ---------------------------------------------------------------------------------
def _resp(body=None, status=200, headers=None):
    r = MagicMock()
    r.status_code = status
    r.headers = headers or {}
    if isinstance(body, Exception):
        r.json.side_effect = body
    else:
        r.json.return_value = body
    return r


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "gios_open_max_retries", 2)
    sleeps: list[float] = []
    limiter = MagicMock()
    c = gc.GiosOpenClient("halas", limiter=limiter, sleeper=sleeps.append, rng=lambda: 0.5)
    c.sleeps = sleeps
    c.limiter_mock = limiter
    return c


def _script(monkeypatch, outcomes):
    calls = MagicMock()

    def fake_get(url, params=None, timeout=None):
        calls(url, params, timeout)
        out = outcomes.pop(0)
        if isinstance(out, Exception):
            raise out
        return out

    monkeypatch.setattr(gc.httpx, "get", fake_get)
    return calls


def test_url_and_params_and_timeouts(client, monkeypatch):
    calls = _script(monkeypatch, [_resp(NOISE_OK)])
    client.get_page("/v1/pomiar-halasu-w-srodowisku", {"kategoria": "Droga"})
    url, params, timeout = calls.call_args.args
    assert url == "https://dane.gios.gov.pl/api/halas/v1/pomiar-halasu-w-srodowisku"
    assert params == {"kategoria": "Droga"}
    assert timeout.connect == 5.0 and timeout.read == 20.0


def test_blad_is_not_retried(client, monkeypatch):
    calls = _script(monkeypatch, [_resp(BLAD_200)])
    with pytest.raises(GiosOpenSourceError):
        client.get_page("/x")
    assert calls.call_count == 1  # a validation error would only repeat
    assert client.sleeps == []


def test_timeout_is_retried_at_most_twice_after_the_first_attempt(client, monkeypatch):
    calls = _script(monkeypatch, [httpx.ReadTimeout("t")] * 3)
    with pytest.raises(GiosOpenTransportError):
        client.get_page("/x")
    assert calls.call_count == 3  # 1 + 2 retries, never infinite (rule #5)
    assert client.limiter_mock.wait.call_count == 3  # every attempt takes a limiter slot
    assert client.sleeps == [1.5, 2.5]  # 1s, 2s backoff + 0.5 jitter


def test_recovers_after_a_transient_failure(client, monkeypatch):
    _script(monkeypatch, [httpx.ConnectError("x"), _resp(None, 503), _resp(NOISE_OK)])
    assert len(client.get_page("/x").records) == 1


def test_retry_after_is_honoured_and_capped(client, monkeypatch):
    _script(
        monkeypatch,
        [
            _resp(None, 429, {"Retry-After": "7"}),
            _resp(None, 429, {"Retry-After": "9999"}),
            _resp(NOISE_OK),
        ],
    )
    client.get_page("/x")
    assert client.sleeps == [7.5, 60.5]


@pytest.mark.parametrize("status", [400, 401, 403, 404, 500])
def test_other_http_errors_are_not_retried(client, monkeypatch, status):
    calls = _script(monkeypatch, [_resp(None, status)])
    with pytest.raises(GiosOpenTransportError):
        client.get_page("/x")
    assert calls.call_count == 1


def test_non_json_body_is_a_contract_error_not_retried(client, monkeypatch):
    calls = _script(monkeypatch, [_resp(ValueError("no json"))])
    with pytest.raises(GiosOpenContractError):
        client.get_page("/x")
    assert calls.call_count == 1


def test_zero_retries_means_one_attempt(client, monkeypatch):
    monkeypatch.setattr(settings, "gios_open_max_retries", 0)
    calls = _script(monkeypatch, [httpx.ReadTimeout("t")])
    with pytest.raises(GiosOpenTransportError):
        client.get_page("/x")
    assert calls.call_count == 1


class TestLimiter:
    def test_spaces_calls_by_the_minimum_interval(self):
        now = [100.0]
        slept: list[float] = []
        lim = gc.MinIntervalLimiter(
            5.0,
            clock=lambda: now[0],
            sleeper=lambda s: (slept.append(s), now.__setitem__(0, now[0] + s)),
        )
        lim.wait()  # first call never waits
        now[0] += 2.0
        lim.wait()
        now[0] += 10.0
        lim.wait()  # already past the interval
        assert slept == [3.0]

    def test_one_shared_limiter_per_service(self):
        gc._LIMITERS.clear()
        assert gc.limiter_for("halas") is gc.limiter_for("halas")
        assert gc.limiter_for("halas") is not gc.limiter_for("prtr")
        gc._LIMITERS.clear()


def test_recorded_evidence_files_parse_the_way_the_docs_claim():
    """The evidence in docs/data/gios/ is what this client is built on: keep them in sync."""
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[4] / "docs" / "data" / "gios" / "evidence"
    outcomes = {}
    for f in sorted(root.glob("*.json")):
        body = json.loads(json.loads(f.read_text())["body"])
        try:
            outcomes[f.stem] = gc.parse_envelope(body).empty_observed
        except GiosOpenSourceError:
            outcomes[f.stem] = "BLAD"
    assert outcomes["halas"] == "BLAD"  # lowercase voivodeship
    assert outcomes["halas-second"] is False
    assert outcomes["wody-powierzchniowe"] is True  # observed empty
    assert outcomes["wody-powierzchniowe-second"] == "BLAD"  # missing required jcwpNazwa
    assert outcomes["wody-podziemne"] == "BLAD"  # missing required river basin / JCWPd filter
    assert (
        outcomes["prtr"] is False
        and outcomes["nec"] is False
        and outcomes["powazne-awarie"] is False
    )
