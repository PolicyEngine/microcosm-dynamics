"""Pin the three Workstream A floor artifacts (#212, pre-IC3)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

RUNS = Path(__file__).resolve().parents[1] / "runs"
ROOT = RUNS.parent

ARTIFACTS = {
    "sipp_spell_floors_v1.json": "500b68034c9a301eb823e1d8f7584cf6c7654bf536247827353b0941d1d026ae",
    "tenure_floors_v1.json": "08e67e5d362bbd0c1703c85fdb40624de094561f385eceb6d0a9eea4772cc6ff",
    "sipp_e8_e9_floors_v1.json": "b360f04fc785eeb11c8e77e4128bdb8a98d31501a11f048fa2df4e86b1f7e059",
}
BUILDERS = {
    "scripts/build_sipp_spell_floors.py": "8ce7e41a9af71767672c39f7933ccde3c2eeaa0aa4f7044c5113f7430439d1dc",
    "scripts/build_tenure_floors.py": "593237bfbba31e77183a8d38bf07ae6ad77eb9392abd323ce71aecdc3e6dfb9e",
    "scripts/build_sipp_e8_e9_floors.py": "3b2209de9b10cf680f5a074ea0c56077b03ebda68a4a614f2e20f0d0c2455272",
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
        assert "promotion_integrity" not in artifact


def test_artifact_builder_and_sidecar_pins():
    for relative, expected in ARTIFACTS.items():
        assert (
            hashlib.sha256((RUNS / relative).read_bytes()).hexdigest()
            == expected
        )
        sidecar = json.loads(
            (RUNS / relative.replace(".json", ".env.json")).read_text()
        )
        assert sidecar["status"] == "MEASUREMENT_ENVIRONMENT"
        environment = sidecar["environment"]
        assert environment["python"]
        assert environment["numpy"]
        assert environment["pandas"]
        assert environment["platform"]
    for relative, expected in BUILDERS.items():
        assert (
            hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            == expected
        )


def test_source_input_sidecars_match_artifacts(spells, tenure, e8e9):
    sipp_inputs = json.loads(
        (RUNS / "sipp_spell_floors_v1.inputs.json").read_text()
    )
    e8e9_inputs = json.loads(
        (RUNS / "sipp_e8_e9_floors_v1.inputs.json").read_text()
    )
    for artifact, sidecar in (
        (spells, sipp_inputs),
        (e8e9, e8e9_inputs),
    ):
        assert sidecar["status"] == "SOURCE_INPUT_DIGESTS"
        assert sidecar["staged_input"]["path"] == artifact["source_input"][
            "path"
        ]
        assert sidecar["staged_input"]["sha256"] == artifact["source_input"][
            "sha256"
        ]
        assert sidecar["staged_input"]["bytes"] > 0
        official = sidecar["official_source"]
        assert official["url"].startswith("https://www2.census.gov/")
        assert official["archive_member"] == "pu2023.csv"
        _assert_sha256(official["archive_sha256"])
        assert official["archive_bytes"] > 0

    tenure_inputs = json.loads(
        (RUNS / "tenure_floors_v1.inputs.json").read_text()
    )
    assert tenure_inputs["status"] == "SOURCE_INPUT_DIGESTS"
    for artifact_input, sidecar_input in zip(
        tenure["source_inputs"],
        tenure_inputs["source_inputs"],
        strict=True,
    ):
        assert sidecar_input["path"] == artifact_input["path"]
        assert sidecar_input["sha256"] == artifact_input["sha256"]
        assert sidecar_input["bytes"] > 0
        assert sidecar_input["official_url"].startswith(
            "https://www2.census.gov/"
        )
        assert "/supp/" in sidecar_input["official_url"]


def _assert_sha256(value: str) -> None:
    assert len(value) == 64
    int(value, 16)


def test_exact_source_input_digests_are_recorded(spells, tenure, e8e9):
    assert spells["source_input"] == e8e9["source_input"]
    assert spells["source_input"]["path"] == "pu2023.csv.gz"
    _assert_sha256(spells["source_input"]["sha256"])

    assert [item["year"] for item in tenure["source_inputs"]] == [
        "2020",
        "2022",
        "2024",
    ]
    assert [item["path"] for item in tenure["source_inputs"]] == [
        "jan20pub.csv",
        "jan22pub.csv",
        "jan24pub.csv",
    ]
    for item in tenure["source_inputs"]:
        _assert_sha256(item["sha256"])


def test_sipp_builder_uses_reader_path_resolver():
    builder = (ROOT / "scripts/build_sipp_spell_floors.py").read_text()
    assert "sipp_jobs._resolve_pu_path(" in builder
    assert "sipp_jobs._resolve_person_path(" not in builder


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
        e8e9["e9_transitions"]["earnings_change"]["stay"][
            "persons_unweighted"
        ]
        == 16286
    )
    assert (
        e8e9["e9_transitions"]["earnings_change"]["j2j"][
            "persons_unweighted"
        ]
        == 524
    )
    builder = (ROOT / "scripts/build_sipp_e8_e9_floors.py").read_text()
    assert '"persons_unweighted": int(cell["person_id"].nunique())' in builder
    e8 = e8e9["e8_nonemployment_by_age"]["16_24"]
    assert e8["any_nonemp_share"] == pytest.approx(0.4145, abs=0.001)
