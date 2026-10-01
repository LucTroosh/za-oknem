"""prg_gminy CLI + pure helpers, no database (PostGIS behaviour: tests/test_postgis_geo.py)."""

import json
import sys
from unittest.mock import MagicMock

import pytest

from app.connectors.prg_gminy import ingest


def _write(tmp_path, features):
    path = tmp_path / "gminy.geojson"
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
    return str(path)


def _feature(code="9999901"):
    ring = [[16.0, 54.9], [16.5, 54.9], [16.5, 55.0], [16.0, 55.0], [16.0, 54.9]]
    return {
        "type": "Feature",
        "properties": {"JPT_KOD_JE": code, "JPT_NAZWA_": "Synth"},
        "geometry": {"type": "Polygon", "coordinates": [ring]},
    }


def _run(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["ingest", *argv])
    with pytest.raises(SystemExit) as exc:
        ingest.main()
    return exc.value.code


@pytest.mark.parametrize(
    "flags",
    [["--force-retire"], ["--dry-run"], ["--validate-only", "--retire-missing"]],
)
def test_conflicting_flags_are_argument_errors(monkeypatch, tmp_path, flags):
    assert _run(monkeypatch, "--file", _write(tmp_path, [_feature()]), *flags) == 2


def test_validate_only_ok_touches_no_database(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(ingest, "SessionLocal", MagicMock(side_effect=AssertionError("db used")))
    monkeypatch.setattr(
        sys, "argv", ["ingest", "--file", _write(tmp_path, [_feature()]), "--validate-only"]
    )
    ingest.main()  # exit code 0 = returns normally
    assert "1 valid, 0 rejected" in capsys.readouterr().out


def test_validate_only_with_rejected_record_exits_1(monkeypatch, tmp_path):
    bad = _feature("123")
    code = _run(monkeypatch, "--file", _write(tmp_path, [_feature(), bad]), "--validate-only")
    assert code == 1


def test_unusable_file_exits_1(monkeypatch, tmp_path):
    path = tmp_path / "x.geojson"
    path.write_text("not json")
    assert _run(monkeypatch, "--file", str(path)) == 1


def test_retire_refusal_exits_1_before_importing_anything(monkeypatch, tmp_path):
    monkeypatch.setattr(ingest, "SessionLocal", MagicMock())
    monkeypatch.setattr(ingest, "plan_retire", MagicMock(side_effect=ValueError("looks partial")))
    imported = MagicMock()
    monkeypatch.setattr(ingest, "import_records", imported)

    code = _run(monkeypatch, "--file", _write(tmp_path, [_feature()]), "--retire-missing")

    assert code == 1
    imported.assert_not_called()


def test_dry_run_reports_plan_and_imports_nothing(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(ingest, "SessionLocal", MagicMock())
    monkeypatch.setattr(ingest, "plan_retire", MagicMock(return_value=7))
    imported = MagicMock()
    monkeypatch.setattr(ingest, "import_records", imported)
    monkeypatch.setattr(
        sys,
        "argv",
        ["ingest", "--file", _write(tmp_path, [_feature()]), "--retire-missing", "--dry-run"],
    )

    ingest.main()

    assert "7 gmina(s) would lose their boundary" in capsys.readouterr().out
    imported.assert_not_called()


def test_repair_drift_check():
    ingest.check_repair_drift(None)  # original had no area: not comparable
    ingest.check_repair_drift(1.005)
    with pytest.raises(ValueError, match="changed the area"):
        ingest.check_repair_drift(0.9)
