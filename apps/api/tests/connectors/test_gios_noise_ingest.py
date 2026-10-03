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


def test_a_duplicate_says_whether_it_is_identical_or_differs_in_which_fields(db_session):
    same = rec("D_1")
    other = rec("D_1", przekroczenie=1.5, miejscowosc="Inna")  # same natural key, other fields
    client = FakeHalas({("Droga", "ŚLĄSKIE"): [[rec("D_1"), same, other]]})
    run(db_session, client)
    details = sorted(
        q.detail for q in db_session.query(IngestQuarantine).filter_by(reason="duplicate_record")
    )
    assert details == ["differs: miejscowosc, przekroczenie", "identical"]


def test_a_null_result_is_a_missing_value_not_a_type_error(db_session):
    client = FakeHalas({("Droga", "ŚLĄSKIE"): [[rec("D_1"), rec("D_2", wynikPomiaru=None)]]})
    run(db_session, client)
    assert [q.reason for q in db_session.query(IngestQuarantine)] == ["value_missing"]


class CountingHalas:
    """Answers a page-size-1 request with the source's total, like the live API (one request)."""

    service = "halas"

    def __init__(self, totals):
        self.totals, self.calls = totals, []

    def get_page(self, path, params):
        key = (params["kategoria"], params["wojewodztwo"])
        self.calls.append(params)
        if key not in self.totals:
            raise GiosOpenSourceError("400", "boom")
        total = self.totals[key]
        records = [rec("D_1")] if total else []
        return Page(
            records=records, reported_count=total, empty_observed=not total, event_id=None, raw={}
        )


def test_count_only_makes_one_small_request_per_combination_and_estimates_the_time(db_session):
    client = CountingHalas(
        {("Droga", "ŚLĄSKIE"): 4415, ("Droga", "OPOLSKIE"): 0, ("Kolej", "ŚLĄSKIE"): 51}
    )
    results = ing.run(
        db=None, client=client, categories=["Droga", "Kolej"], voivodeships=["ŚLĄSKIE", "OPOLSKIE"],
        date_from=D_FROM, date_to=D_TO, validate_only=False, count_only=True,
    )  # fmt: skip
    by_key = {(r["category"], r["voivodeship"]): r for r in results}
    assert len(client.calls) == 4 and all(c["liczbaElementowNaStronie"] == 1 for c in client.calls)
    assert (
        by_key[("Droga", "ŚLĄSKIE")]["records_reported"] == 4415
        and by_key[("Droga", "ŚLĄSKIE")]["pages"] == 89
    )
    assert (
        by_key[("Droga", "OPOLSKIE")]["records_reported"] == 0
        and by_key[("Droga", "OPOLSKIE")]["pages"] == 0
    )
    assert (
        by_key[("Kolej", "OPOLSKIE")]["status"] == "failed"
    )  # one failing combination does not stop the rest
    summary = ing.count_summary(results)
    assert summary["total_records"] == 4466 and summary["total_pages"] == 91  # 89 + 0 + 2
    # (89 + 2) pages + the final empty page of each non-empty combination (2), 5 s each
    assert summary["estimated_minutes"] == round((91 + 2) * 5 / 60, 1)
    assert db_session.query(DatasetSnapshot).count() == 0  # nothing written


def _exceedance_after(db_session, *copies):
    """Imports the copies of ONE measurement (same natural key, differing only in przekroczenie)."""
    client = FakeHalas({("Droga", "ŚLĄSKIE"): [[rec("D_1", przekroczenie=c) for c in copies]]})
    run(db_session, client)
    (row,) = rows(db_session)
    details = [q.detail for q in db_session.query(IngestQuarantine).order_by(IngestQuarantine.id)]
    return row.exceedance_db, details


def test_a_null_exceedance_copy_is_completed_by_the_copy_that_has_a_number(db_session):
    value, details = _exceedance_after(db_session, None, 0.5)
    assert value == 0.5 and details == ["merged: przekroczenie taken from this copy"]


def test_page_order_does_not_change_the_result(db_session):
    first, _ = _exceedance_after(db_session, 0.5, None)
    assert first == 0.5  # the number wins whichever copy came first


def test_zero_is_kept_over_null_it_is_a_statement_of_the_source(db_session):
    value, details = _exceedance_after(db_session, 0, None)
    assert value == 0.0 and details == ["merged: przekroczenie kept, this copy had none"]


def test_two_different_numbers_leave_the_measurement_without_an_exceedance(db_session):
    value, details = _exceedance_after(db_session, 0.6, 0.5)
    assert value is None and details == ["conflict: przekroczenie 0.6 vs 0.5"]


def test_a_third_copy_cannot_resolve_a_conflict(db_session):
    value, details = _exceedance_after(db_session, 0.6, 0.5, 0.7)
    assert value is None and details[-1] == "conflict: przekroczenie"


def test_a_copy_that_differs_in_other_fields_does_not_touch_the_exceedance(db_session):
    client = FakeHalas(
        {
            ("Droga", "ŚLĄSKIE"): [
                [rec("D_1", przekroczenie=None), rec("D_1", przekroczenie=2.0, powiat="inny")]
            ]
        }
    )
    run(db_session, client)
    (row,) = rows(db_session)
    assert row.exceedance_db is None  # not merged: it is not the same record
    (q,) = db_session.query(IngestQuarantine).all()
    assert q.detail == "differs: powiat, przekroczenie"
