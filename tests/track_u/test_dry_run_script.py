"""The Track U dry run (plan item U9) on INVENTED data.

Runs ``scripts/track_u_dry_run.py`` into a temporary directory.  The
cohort and the thresholds are INVENTED; the life tables, the SSI capture
and the SSA snapshot the diagnostics read are the committed files under
``data/external``.  No PSID file and no comparator value is read.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from populace_dynamics.estimates import adjusted_poverty as ap
from populace_dynamics.uniform_cut_track_u import DRY_RUN_HEADER

ROOT = Path(__file__).resolve().parents[2]
COMMITTED = ROOT / "data" / "external"


def _script():
    path = ROOT / "scripts" / "track_u_dry_run.py"
    spec = importlib.util.spec_from_file_location("_track_u_dry_run", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def output(tmp_path_factory) -> Path:
    directory = tmp_path_factory.mktemp("track_u_dry_run")
    assert _script().main(["--output-dir", str(directory)]) == 0
    return directory


def test_the_dry_run_is_headed_invented(output):
    result = json.loads((output / "result.json").read_text())
    assert (
        result["header"]
        == DRY_RUN_HEADER
        == ("INVENTED DATA - NOT A COMPARISON")
    )
    text = (output / "RESULTS.md").read_text()
    assert text.splitlines()[0] == f"# {DRY_RUN_HEADER}"
    assert result["data_provenance"] == ap.INVENTED
    assert result["labels"][0].startswith("INVENTED DATA")
    assert result["cohort_provenance"]["kind"] == "invented"
    assert result["parameters"]["thresholds"]["kind"] == "invented"
    assert "not Census values" in result["parameters"]["thresholds"]["label"]
    assert "psid_files" not in json.dumps(result["cohort_provenance"])
    assert result["psid_files_sha256"] == {}


def test_the_dry_run_uses_the_committed_parameters(output):
    result = json.loads((output / "result.json").read_text())
    assert (COMMITTED / "track_u_ssi_parameters.json").is_file()
    assert result["parameters"]["ssi"]["sha256"] == ap.SSI_PARAMETERS_SHA256
    assert result["parameters"]["life_tables"]["nchs_2000"]["sha256"] == (
        ap.NCHS_2000_SHA256
    )


def test_the_dry_run_checks_hold(output):
    checks = json.loads((output / "result.json").read_text())["checks"]
    assert checks["specification_rows"]["rows_equal_the_block"]
    blocked = checks["blocked_waves_as_staged_today"]
    assert blocked["income_rows_without_allow_blocked"]["refused"]
    assert (
        blocked["left_out_with_allow_blocked"]["wealth_supplement_not_staged"]
        > 0
    )
    fallback = blocked["fallback_rule"]
    assert fallback["headline"]["row"] == "U0-F"
    assert fallback["row_status"]["U0-F"] == "computed"
    assert fallback["row_status"]["U0"] == "blocked"
    assert set(fallback["blocked_counts"]) == {
        row
        for row, status in fallback["row_status"].items()
        if status == "blocked"
    }
    assert checks["registered_guard_refuses_invented_inputs"]["refused"]
    assert checks["census_thresholds_not_captured"]["error"] == (
        "ThresholdsNotCapturedError"
    )
    for identities in checks["invented_family_income_reconciliation"].values():
        for counts in identities.values():
            assert counts["n_exact"] == counts["n_families"]


def test_every_built_row_is_tabulated(output):
    result = json.loads((output / "result.json").read_text())
    statuses = {row: entry["status"] for row, entry in result["rows"].items()}
    assert statuses.pop("U7") == "not_built"
    assert set(statuses.values()) == {"computed"}
    assert result["headline"]["row"] == "U0"
    text = (output / "RESULTS.md").read_text()
    assert "Headline row U0" in text and "full sample design" in text
    assert "`design_se_domain` = `full_sample_design`" in text
