"""GeoNames PL places connector (ADR-029): parse/validate/normalize, idempotent import,
CLI. A tiny hand-made fixture in the real 19-column GeoNames layout - no network, no data
file in the repo."""

import sys
import zipfile
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from app.connectors.geonames_places import ingest
from app.connectors.geonames_places.parser import (
    SOURCE_ID,
    PlacesParseError,
    parse_lines,
)
from app.models import Place
from app.places import search_places


def _line(
    gid, name, lat, lon, *, fclass="P", fcode="PPL", country="PL", pop="0", a1="72", a2="1001"
):
    cols = [
        str(gid), name, name, "", str(lat), str(lon), fclass, fcode, country, "",
        a1, a2, "", "", pop, "", "", "Europe/Warsaw", "2024-01-01",
    ]  # fmt: skip
    return "\t".join(cols) + "\n"


FIXTURE = [
    _line(3093133, "Łódź", 51.75, 19.4667, fcode="PPLA", pop="768755", a1="74", a2="1061"),
    _line(3095237, "Kłodzko", 50.4348, 16.6614, fcode="PPLA3", pop="27000", a1="72"),
    _line(7530001, "Nowa Wieś", 50.1, 17.2, pop="0", a1="76"),
    _line(7530002, "Nowa Wieś", 52.9, 20.1, pop="310", a1="78"),
    _line(7530003, "Stara Wieś", 52.0, 21.0, fcode="PPLL"),
    _line(9990001, "Rzeka", 52.0, 21.0, fclass="H", fcode="STM"),  # not a place -> skipped
    _line(9990002, "Berlin", 52.52, 13.405, country="DE", fcode="PPLC"),  # not PL -> skipped
    _line(9990003, "Stara Osada", 52.0, 21.0, fcode="PPLH"),  # historical -> skipped
]


def test_parse_keeps_polish_populated_places_and_counts_the_rest_as_skipped():
    result = parse_lines(FIXTURE)

    assert [r.name for r in result.records] == [
        "Łódź", "Kłodzko", "Nowa Wieś", "Nowa Wieś", "Stara Wieś",
    ]  # fmt: skip
    assert result.skipped == 3 and result.rejected == []
    lodz = result.records[0]
    assert (lodz.source_record_id, lodz.normalized_name, lodz.kind) == ("3093133", "lodz", "PPLA")
    assert (lodz.admin1_code, lodz.admin2_code, lodz.population) == ("74", "1061", 768755)
    assert result.records[2].population == 0  # known zero stays 0 (not None)


@pytest.mark.parametrize(
    "line",
    [
        "too\tfew\tcolumns\n",
        _line("x1", "Bad id", 52.0, 21.0),
        _line(1, "", 52.0, 21.0),
        _line(2, "日本", 52.0, 21.0),  # nothing left after normalisation
        _line(3, "Nan", "nan", 21.0),
        _line(4, "Abc", "abc", 21.0),
        _line(5, "Far", 10.0, 21.0),  # outside the Poland bbox (lat/lon swapped files too)
        _line(6, "x" * 201, 52.0, 21.0),
    ],
)
def test_malformed_lines_are_rejected_not_fatal(line):
    result = parse_lines([line, _line(9, "Dobra", 52.0, 21.0)])

    assert [r.name for r in result.records] == ["Dobra"]
    assert len(result.rejected) == 1 and result.rejected[0].startswith("line 1:")


def test_duplicate_geonameid_keeps_the_first_line():
    result = parse_lines([_line(1, "Pierwsza", 52.0, 21.0), _line(1, "Druga", 52.1, 21.1)])

    assert [r.name for r in result.records] == ["Pierwsza"]
    assert "duplicate geonameid" in result.rejected[0]


def test_input_without_any_valid_place_is_an_error():
    with pytest.raises(PlacesParseError):
        parse_lines([_line(9990001, "Rzeka", 52.0, 21.0, fclass="H", fcode="STM")])


def test_import_inserts_then_is_idempotent_then_updates(db_session):
    records = parse_lines(FIXTURE).records
    t1 = datetime(2026, 10, 1, tzinfo=UTC)

    first = ingest.import_records(records, db_session, imported_at=t1)
    again = ingest.import_records(records, db_session, imported_at=t1)

    assert (first.inserted, first.updated, first.unchanged) == (5, 0, 0)
    assert (again.inserted, again.updated, again.unchanged) == (0, 0, 5)
    assert db_session.query(Place).count() == 5

    changed = parse_lines([_line(3095237, "Kłodzko", 50.4348, 16.6614, fcode="PPLA3", pop="28000")])
    third = ingest.import_records(changed.records, db_session)

    assert (third.inserted, third.updated) == (0, 1)
    row = db_session.query(Place).filter_by(source_record_id="3095237").one()
    assert row.population == 28000 and row.source == SOURCE_ID


def test_import_then_search_end_to_end(db_session):
    ingest.import_records(parse_lines(FIXTURE).records, db_session)

    assert [p.name for p in search_places(db_session, "lodz", 5)] == ["Łódź"]
    assert [p.name for p in search_places(db_session, "klod", 5)] == ["Kłodzko"]
    # two namesakes: the more populated one first (distinguishable by coordinates/admin)
    nowa = search_places(db_session, "nowa wies", 5)
    assert [p.population for p in nowa] == [310, 0]


def test_read_lines_from_plain_file_and_zip(tmp_path):
    txt = tmp_path / "PL.txt"
    txt.write_text("".join(FIXTURE), encoding="utf-8")
    z = tmp_path / "PL.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("PL.txt", "".join(FIXTURE))
        zf.writestr("readme.txt", "ignored")

    assert ingest.load(txt).records == ingest.load(z).records
    assert len(ingest.load(z).records) == 5


def _run(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["ingest", *argv])
    with pytest.raises(SystemExit) as exc:
        ingest.main()
    return exc.value.code


def test_cli_validate_only_touches_no_database(monkeypatch, tmp_path, capsys):
    path = tmp_path / "PL.txt"
    path.write_text("".join(FIXTURE), encoding="utf-8")
    monkeypatch.setattr(ingest, "SessionLocal", MagicMock(side_effect=AssertionError("db used")))
    monkeypatch.setattr(sys, "argv", ["ingest", "--file", str(path), "--validate-only"])

    ingest.main()

    assert "5 valid, 0 rejected, 3 skipped" in capsys.readouterr().out


def test_cli_unusable_file_exits_1_and_missing_file_arg_is_an_error(monkeypatch, tmp_path):
    bad = tmp_path / "PL.txt"
    bad.write_text("garbage\n", encoding="utf-8")
    monkeypatch.delenv("GEONAMES_PL_FILE", raising=False)

    assert _run(monkeypatch, "--file", str(bad), "--validate-only") == 1
    assert _run(monkeypatch, "--file", str(tmp_path / "missing.txt")) == 1
    assert _run(monkeypatch) == 2  # no --file and no env


def test_cli_reads_the_path_from_the_environment(monkeypatch, tmp_path, capsys):
    path = tmp_path / "PL.txt"
    path.write_text("".join(FIXTURE), encoding="utf-8")
    monkeypatch.setenv("GEONAMES_PL_FILE", str(path))
    monkeypatch.setattr(sys, "argv", ["ingest", "--validate-only"])

    ingest.main()

    assert "5 valid" in capsys.readouterr().out
