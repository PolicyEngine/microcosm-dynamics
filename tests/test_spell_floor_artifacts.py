"""Pin the three Workstream A floor artifacts (#212, pre-IC3)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

RUNS = Path(__file__).resolve().parents[1] / "runs"
ROOT = RUNS.parent

ARTIFACTS = {
    "sipp_spell_floors_v1.json": "0110366a37a46fcc12b9a5665f3e6d5ea4c99fd2cabc4bf8cfc3fa8719890faf",
    "tenure_floors_v1.json": "afbbb9ba38e0c69e78d94bd854c064dfae980f398092904b87b59a526a78e015",
    "sipp_e8_e9_floors_v1.json": "28515717e83824056708a491b2702089cb439d5369deaff480f391c6f8862aa2",
}
BUILDERS = {
    "scripts/build_sipp_spell_floors.py": "e869208f039a4005b78ffe27502f414f5e01775f64c64e89ffcad6effd838ffb",
    "scripts/build_tenure_floors.py": "a4b0434196d5e3713c6ebed3302364fb60ec24e72bb82b039eef8d3bccc6d9eb",
    "scripts/build_sipp_e8_e9_floors.py": "214d8a32afacb86396151fccfa19bd76c5cfce1bddc35fd75508cbfab6d9d45b",
}


@pytest.fixture(scope="module")
def spells() -> dict:
    return json.loads((RUNS / "sipp_spell_floors_v1.json").read_text())


@pytest.fixture(scope="module")
def tenure() -> dict:
    return json.loads((RUNS / "tenure_floors_v1.json").read_text())


@pytest.fixture(scope="module")
def e8e9() -> dict:
    return json.loads((RUNS / "sipp_e8_e9_floors_v1.json").read_text())


def test_all_carry_prelock_status_and_correct_scale_gap(spells, tenure, e8e9):
    for artifact in (spells, tenure, e8e9):
        assert artifact["version"] == "v1"
        assert "pinning event, not a ratification" in artifact["status"]
        assert "RECORDED GAP" in artifact["deployment_scale_note"]
        assert "1.58x" in artifact["deployment_scale_note"]
        assert (
            "ANTI-conservative (too tight)"
            in artifact["deployment_scale_note"]
        )
        assert "RECORDED_NOT_SATISFIED" in artifact["deployment_scale_note"]
        assert artifact["promotion_integrity"][
            "source_input_sha256_status"
        ].startswith("BLOCKED_STRICT_STAGING")


def test_artifact_builder_and_sidecar_pins():
    for relative, expected in ARTIFACTS.items():
        assert (
            hashlib.sha256((RUNS / relative).read_bytes()).hexdigest()
            == expected
        )
        sidecar = json.loads(
            (RUNS / relative.replace(".json", ".env.json")).read_text()
        )
        assert (
            sidecar["status"] == "PROMOTION_ONLY_NOT_MEASUREMENT_ENVIRONMENT"
        )
        assert sidecar["measurement_environment"] == "UNAVAILABLE_NOT_RECORDED"
    for relative, expected in BUILDERS.items():
        assert (
            hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            == expected
        )


def test_e4_e5_pinned_values(spells):
    e4 = spells["e4_retention_by_age_sex"]["16_24|sex1"]
    assert e4["rate"] == 0.9897
    assert e4["floor_abs_log_ratio_mean"] == 0.00182
    e5 = spells["e5_runs_by_age"]["45_54"]
    assert e5["full_year_run_share"] == 0.8671
    assert spells["seam_caveat"]


def test_tenure_pinned_values_and_heaping(tenure):
    cell = tenure["by_year"]["2024"]["35_44"]
    assert cell["p50"] == 5.0
    assert cell["floor_abs_gap_years"]["p50"]["mean"] == 0.0
    assert cell["floor_ecdf_max_gap"]["mean"] > 0
    assert "exactly zero" in tenure["heaping_caveat"]


def test_e8_e9_pinned_values(e8e9):
    assert "seeds 0-19" in e8e9["method"]
    assert "ESTIMAND NOTE" in e8e9["source"]
    mix = e8e9["e9_transitions"]["transition_rates"]
    assert mix["stay"] == 0.977
    assert mix["j2j"] == 0.0035
    stay = e8e9["e9_transitions"]["earnings_change"]["stay"]
    assert stay["median_log_change"] == 0.0
    assert "heaps at exactly 0" in e8e9["stay_median_heaping_caveat"]
    assert (
        "FOLLOW_UP_REQUIRED"
        in e8e9["promotion_integrity"]["e9_distinct_person_count_status"]
    )
    builder = (ROOT / "scripts/build_sipp_e8_e9_floors.py").read_text()
    assert '"persons_unweighted": int(cell["person_id"].nunique())' in builder
    e8 = e8e9["e8_nonemployment_by_age"]["16_24"]
    assert e8["any_nonemp_share"] == pytest.approx(0.4145, abs=0.001)
