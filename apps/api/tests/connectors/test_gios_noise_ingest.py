"""GIOŚ noise import (ADR-032, GIOS-04): snapshot per category x voivodeship, quarantine, CLI."""

import json
import pathlib
from datetime import date

import pytest

from app.connectors.gios_noise import ingest as ing
from app.gios_open import snapshots as sn
from app.gios_open.client import Page
from app.gios_open.errors import GiosOpenSourceError, SnapshotLockedError
from app.gios_open.paging import PAGE_PARAM
from app.models import DatasetSnapshot, IngestQuarantine, NoiseMeasurement, SourceStatus

from .test_gios_noise_parser import LIVE

D_FROM, D_TO = date(2024, 1, 1), date(2024, 12, 31)


def rec(code="D_1", pora="Dzień 16h", value=60.0, **extra):
    return {**LIVE, "kodPunktuPomiarowego": code, "pora": pora, "wynikPomiaru": value, **extra}


def page(records):
    raw = {
        "dane": {"strona": records, "liczbaRekordow": len(records)},
        "wynik": {"status": "SUKCES"},
    }
    return Page(
        records=records,
        reported_count=len(records),
        empty_observed=not records,
        event_id=None,
        raw=raw,
    )


class FakeHalas:
    """data[(category, voivodeship)] = list of pages (lists of records); after them: empty."""

    service = "halas"

    def __init__(self, data, *, fail=()):
        self.data, self.fail, self.calls = data, set(fail), []

    def url(self, path):
        return f"https://dane.gios.gov.pl/api/halas{path}"

    def get_page(self, path, params):
        key = (params["kategoria"], params["wojewodztwo"])
        self.calls.append((key, params[PAGE_PARAM]))
        if key in self.fail:
            raise GiosOpenSourceError("400", "boom")
        pages = self.data.get(key, [])
        n = params[PAGE_PARAM]
        return page(pages[n] if n < len(pages) else [])


def run(db, client, *, cats=("Droga",), vois=("ŚLĄSKIE",), validate_only=False, file=None):
    return ing.run(
        db=db, client=client, categories=list(cats), voivodeships=list(vois),
        date_from=D_FROM, date_to=D_TO, validate_only=validate_only, file=file,
    )  # fmt: skip


def rows(db):
    return (
        db.query(NoiseMeasurement)
        .order_by(NoiseMeasurement.point_code, NoiseMeasurement.period_label)
        .all()
    )


def test_a_complete_import_publishes_a_snapshot_with_typed_rows(db_session):
    client = FakeHalas(
        {("Droga", "ŚLĄSKIE"): [[rec("D_1"), rec("D_1", pora="Noc 8h", value=55.5)], [rec("D_2")]]}
    )
    (res,) = run(db_session, client)
    assert res["status"] == "ok" and (res["records"], res["pages"], res["rejected"]) == (3, 2, 0)
    snap = sn.active_snapshot(
        db_session,
        "gios_noise",
        ing.OPERATION,
        ing.request_filters("Droga", "ŚLĄSKIE", D_FROM, D_TO),
    )
    assert snap and snap.record_count == 3
    assert [(r.point_code, r.period_label, r.value_db) for r in rows(db_session)] == [
        ("D_1", "Dzień 16h", 60.0), ("D_1", "Noc 8h", 55.5), ("D_2", "Dzień 16h", 60.0)
    ]  # fmt: skip
    assert all(r.snapshot_id == snap.id and r.raw["kategoria"] == "Droga" for r in rows(db_session))
    assert db_session.get(SourceStatus, "gios_noise").last_success_at is not None


def test_records_that_do_not_fit_are_quarantined_not_repaired_and_do_not_fail_the_batch(db_session):
    bad_value = rec("D_2", wynikPomiaru="64,5")
    swapped = rec("D_3", coordWgs84X=50.48, coordWgs84Y=18.94)
    wrong_cat = rec("D_4", kategoria="Kolej")  # contradicts the request filter
    dup = rec("D_1")
    client = FakeHalas({("Droga", "ŚLĄSKIE"): [[rec("D_1"), bad_value, swapped], [wrong_cat, dup]]})
    (res,) = run(db_session, client)
    assert res["status"] == "ok" and res["records"] == 5 and res["rejected"] == 4
    assert [r.point_code for r in rows(db_session)] == ["D_1"]
    reasons = sorted(q.reason for q in db_session.query(IngestQuarantine))
    assert reasons == ["coords_swapped", "duplicate_record", "filter_mismatch", "value_not_number"]
    q = db_session.query(IngestQuarantine).filter_by(reason="value_not_number").one()
    assert q.raw["wynikPomiaru"] == "64,5" and q.source_id == "gios_noise"  # raw kept as received


def test_a_second_import_supersedes_the_first_and_keeps_the_old_rows_for_rollback(db_session):
    run(db_session, FakeHalas({("Droga", "ŚLĄSKIE"): [[rec("D_1", value=60.0)]]}))
    run(db_session, FakeHalas({("Droga", "ŚLĄSKIE"): [[rec("D_1", value=61.0)]]}))
    snaps = db_session.query(DatasetSnapshot).order_by(DatasetSnapshot.id).all()
    assert [s.status for s in snaps] == [sn.SUPERSEDED, sn.ACTIVE]
    active = [r.value_db for r in rows(db_session) if r.snapshot_id == snaps[1].id]
    assert active == [61.0] and len(rows(db_session)) == 2


def test_a_failing_combination_is_reported_and_leaves_its_previous_snapshot_and_the_others(
    db_session,
):
    first = {
        ("Droga", "ŚLĄSKIE"): [[rec("D_1")]],
        ("Droga", "OPOLSKIE"): [[rec("O_1", wojewodztwo="OPOLSKIE")]],
    }
    run(db_session, FakeHalas(first), vois=("ŚLĄSKIE", "OPOLSKIE"))
    before = {r.point_code for r in rows(db_session)}

    results = run(
        db_session, FakeHalas(first, fail=[("Droga", "ŚLĄSKIE")]), vois=("ŚLĄSKIE", "OPOLSKIE")
    )
    by_voi = {r["voivodeship"]: r for r in results}
    assert (
        by_voi["ŚLĄSKIE"]["status"] == "failed"
        and "GiosOpenSourceError" in by_voi["ŚLĄSKIE"]["error"]
    )
    assert by_voi["OPOLSKIE"]["status"] == "ok"  # rule #1: one failure does not stop the rest
    filt = ing.request_filters("Droga", "ŚLĄSKIE", D_FROM, D_TO)
    assert (
        sn.active_snapshot(db_session, "gios_noise", ing.OPERATION, filt) is not None
    )  # still serves
    assert {r.point_code for r in rows(db_session) if r.point_code == "D_1"} <= before


def test_a_failure_midway_does_not_leave_partial_rows(db_session):
    class Breaks(FakeHalas):
        def get_page(self, path, params):
            if params[PAGE_PARAM] == 1:
                raise GiosOpenSourceError("500", "down")
            return super().get_page(path, params)

    client = Breaks({("Droga", "ŚLĄSKIE"): [[rec("D_1")], [rec("D_2")]]})
    (res,) = run(db_session, client)
    assert res["status"] == "failed"
    assert rows(db_session) == []  # the first page's rows were discarded with the failed snapshot
    assert db_session.query(DatasetSnapshot).one().status == sn.FAILED


def test_validate_only_writes_nothing_and_reports_what_it_saw(db_session):
    client = FakeHalas(
        {
            ("Droga", "ŚLĄSKIE"): [
                [rec("D_1"), rec("D_2", wynikPomiaru="x")],
                [
                    rec(
                        "D_3",
                        dataOd="2024-02-01T00:00:00+01:00",
                        dataDo="2024-03-01T00:00:00+01:00",
                    )
                ],
            ]
        }
    )
    (res,) = run(db_session, client, validate_only=True)
    assert res["status"] == "ok" and (res["records"], res["accepted"], res["pages"]) == (3, 2, 2)
    assert res["rejected"] == {"value_not_number": 1} and res["period"] == [
        "2024-02-01",
        "2024-11-10",
    ]
    assert db_session.query(DatasetSnapshot).count() == 0 and rows(db_session) == []
    assert db_session.query(IngestQuarantine).count() == 0


def test_every_combination_is_its_own_request_set(db_session):
    client = FakeHalas({})
    results = run(db_session, client, cats=("Droga", "Kolej"), vois=("ŚLĄSKIE", "OPOLSKIE"))
    assert len(results) == 4 and all(r["status"] == "ok" and r["records"] == 0 for r in results)
    assert {k for k, _ in client.calls} == {
        ("Droga", "ŚLĄSKIE"),
        ("Droga", "OPOLSKIE"),
        ("Kolej", "ŚLĄSKIE"),
        ("Kolej", "OPOLSKIE"),
    }
    assert (
        db_session.query(DatasetSnapshot).filter_by(status=sn.ACTIVE).count() == 4
    )  # empty is a valid snapshot


def test_another_running_import_stops_the_whole_run(db_session):
    sn.begin_snapshot(db_session, source_id="gios_noise", operation="x", filters=None)
    with pytest.raises(SnapshotLockedError):
        run(db_session, FakeHalas({}))


def test_import_from_the_recorded_live_response_file(db_session, tmp_path):
    evidence = (
        pathlib.Path(__file__).resolve().parents[4]
        / "docs"
        / "data"
        / "gios"
        / "evidence"
        / "halas-second.json"
    )
    body = json.loads(json.loads(evidence.read_text())["body"])
    empty = {"dane": {"liczbaRekordow": 0}, "wynik": {"status": "SUKCES"}}
    f = tmp_path / "halas.json"
    f.write_text(json.dumps([body, empty]), encoding="utf-8")
    (res,) = run(db_session, None, file=str(f))
    assert res["status"] == "ok" and res["records"] == 1
    (row,) = rows(db_session)
    assert (row.locality, row.value_db, row.latitude, row.longitude) == (
        "Żyglin",
        64.5,
        50.484861,
        18.948417,
    )


def test_cli_validate_only_and_failure_exit_codes(db_session, tmp_path, monkeypatch, capsys):
    f = tmp_path / "h.json"
    f.write_text(json.dumps([{"dane": {"strona": [rec("D_1")]}, "wynik": {"status": "SUKCES"}}]))
    argv = ["--year", "2024", "--category", "Droga", "--voivodeship", "ŚLĄSKIE", "--file", str(f)]
    monkeypatch.setattr(ing, "SessionLocal", lambda: db_session)
    ing.main([*argv, "--validate-only"])
    assert json.loads(capsys.readouterr().out)[0]["accepted"] == 1 and rows(db_session) == []
    ing.main(argv)
    assert len(rows(db_session)) == 1
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps([{"wynik": {"status": "BLAD", "blad": {"kod": "400", "opis": "x"}}}]))
    with pytest.raises(SystemExit) as exc:
        ing.main(
            [
                "--year",
                "2024",
                "--category",
                "Droga",
                "--voivodeship",
                "ŚLĄSKIE",
                "--file",
                str(bad),
            ]
        )
    assert exc.value.code == 1


def test_cli_requires_a_period_and_a_single_combination_for_a_file(capsys):
    with pytest.raises(SystemExit):
        ing.main([])
    with pytest.raises(SystemExit):
        ing.main(["--year", "2024", "--file", "x.json"])  # all combinations: ambiguous for one file
