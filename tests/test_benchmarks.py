"""Schema, alarm, reproduction, and drift tests for benchmark artifacts."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS = ROOT / "benchmarks"
REGISTRY_PATH = BENCHMARKS / "registry.json"
HISTORY_PATH = BENCHMARKS / "history.jsonl"
WALL_PATH = BENCHMARKS / "wall.md"

# The explicit runs path also assigns this module to the artifact test tier.
SEED_RUN_PATH = ROOT / "runs" / "first_estimates_v1.json"
SEED_RUN_SHA256 = (
    "719604ca4364e7cdef2293329ed0beb0e011e5d4d1c34f0e508c8f2fd9932977"
)
REGISTRY_SHA256 = (
    "05da7dbd3e8c247eb4cec2c321ebbf9b934f08576d96548b924a30e68d062977"
)
HISTORY_SEED_PREFIX_SHA256 = (
    "40ed82ee5ad01b6b36364de2310d45757a8a7dbb5c8f3274e83c46b7f8d514e4"
)
WALL_SHA256 = (
    "67d150694c9d0188477f335f248917ca82a6a1ea64235e342cc116f82d387449"
)
SEED_ROW_COUNT = 42
TIER_COUNTS = {
    "admin_truth": 7,
    "model_triangulation": 34,
    "statutory_parameter": 1,
}
GAP_COUNTS = {
    "label_mismatch": 3,
    "frame_no_alignment": 1,
    "concept_mismatch": 17,
    "module_missing": 1,
    "small_cell": 0,
    "preliminary_source": 20,
    "unexplained": 0,
}
UNMANIFESTED_MERMIN_SHA256 = (
    "88934782c267fb0d7f08106ef930a19866c41c89504d04ad7a6d77d454d034ae"
)
DERIVED_DYNASIM_ROW_IDS = {
    "dynasim.favreault_steuerle.package1b.married.male.lose_ge_5",
    "dynasim.favreault_steuerle.package1b.married.male.gain_ge_5",
    "dynasim.favreault_steuerle.package1b.married.female.lose_ge_5",
    "dynasim.favreault_steuerle.package1b.married.female.gain_ge_5",
    "dynasim.favreault_steuerle.package1b.divorced.male.lose_ge_5",
    "dynasim.favreault_steuerle.package1b.divorced.male.gain_ge_5",
    "dynasim.favreault_steuerle.package1b.divorced.female.gain_ge_5",
    "dynasim.favreault_steuerle.package1b.widowed.male.lose_ge_5",
    "dynasim.favreault_steuerle.package1b.widowed.female.lose_ge_5",
    "dynasim.mermin.four_reform_cost_ordering",
}


def sha256(path: Path) -> str:
    """Hash one committed artifact."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_schema():
    """Load the benchmark validator without making benchmarks a package."""

    path = BENCHMARKS / "schema.py"
    spec = importlib.util.spec_from_file_location("benchmark_schema", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test__benchmark_registry__has_strict_schema_tiers_and_gap_census():
    schema = load_schema()
    registry, raw = schema.load_registry()

    assert hashlib.sha256(raw).hexdigest() == REGISTRY_SHA256
    assert registry["row_count"] == SEED_ROW_COUNT
    assert registry["tier_counts"] == TIER_COUNTS
    assert registry["gap_class_counts"] == GAP_COUNTS
    assert Counter(entry["tier"] for entry in registry["entries"]) == (
        TIER_COUNTS
    )
    assert Counter(entry["gap_class"] for entry in registry["entries"]) == {
        key: value for key, value in GAP_COUNTS.items() if value
    }
    assert all(entry["spec_revisions"] == [] for entry in registry["entries"])
    assert all(
        set(entry["comparison_scope"])
        <= {"ratio", "share", "trajectory", "ordering"}
        for entry in registry["entries"]
    )


def test__benchmark_history__reproduces_frozen_seed_prefix():
    schema = load_schema()
    registry, registry_raw = schema.load_registry()
    history, history_raw = schema.load_history()
    prefix = b"".join(history_raw.splitlines(keepends=True)[:SEED_ROW_COUNT])

    assert sha256(SEED_RUN_PATH) == SEED_RUN_SHA256
    assert hashlib.sha256(registry_raw).hexdigest() == REGISTRY_SHA256
    assert hashlib.sha256(prefix).hexdigest() == HISTORY_SEED_PREFIX_SHA256
    assert len(history) == SEED_ROW_COUNT
    assert [record["row_id"] for record in history] == [
        entry["row_id"] for entry in registry["entries"]
    ]
    assert {record["evaluated_at_run"] for record in history} == {
        SEED_RUN_SHA256
    }
    assert {record["registry_sha"] for record in history} == {REGISTRY_SHA256}
    assert [record["gap_class"] for record in history] == [
        entry["gap_class"] for entry in registry["entries"]
    ]


def test__benchmark_history__unexplained_or_unnoted_gap_alarms():
    schema = load_schema()
    history, _ = schema.load_history()

    unexplained = [copy.deepcopy(history[0])]
    unexplained[0]["gap_class"] = "unexplained"
    with pytest.raises(AssertionError, match="unexplained benchmark gap"):
        schema.validate_history(unexplained)

    missing_note = [copy.deepcopy(history[0])]
    missing_note[0]["gap_note"] = ""
    with pytest.raises(AssertionError, match="missing gap note"):
        schema.validate_history(missing_note)

    reused_run = [copy.deepcopy(history[0]), copy.deepcopy(history[0])]
    with pytest.raises(AssertionError, match="row/run SHA reused"):
        schema.validate_history(reused_run)


def test__benchmark_registry__retains_source_and_verification_drift_laws():
    schema = load_schema()
    registry, _ = schema.load_registry()
    entries = registry["entries"]

    verified = [
        entry for entry in entries if entry["verification_class"] == "verified"
    ]
    reported = [
        entry
        for entry in entries
        if entry["verification_class"] == "reported_not_verified"
    ]
    assert len(verified) == 22
    assert len(reported) == 20
    assert not any(".mermin." in entry["row_id"] for entry in verified)

    for entry in entries:
        pointer = entry["our_side_artifact"]["artifact_pointer"]
        assert sha256(ROOT / pointer["path"]) == pointer["sha256"]
        for artifact in entry["source_pin"]["artifacts"]:
            if artifact["pin_type"] == "committed_extraction":
                assert sha256(ROOT / artifact["path"]) == artifact["sha256"]
            else:
                assert artifact["size_bytes"] > 0

    for entry in reported:
        provenance = entry["source_pin"]["reported_value_provenance"]
        assert provenance["classification"] == "reported_not_verified"
        assert all(
            artifact["pin_type"] == "committed_extraction"
            for artifact in entry["source_pin"]["artifacts"]
        )
        for locator in entry["source_pin"]["exact_locators"]:
            assert "missing after REFRESH" in locator["capture_status"]
            corroboration = locator["unmanifested_corroborating_copy"]
            assert corroboration["sha256"] == UNMANIFESTED_MERMIN_SHA256
            assert corroboration["manifested"] is False
            assert corroboration["accepted_as_verified_source"] is False


def test__benchmark_registry__retains_exact_dynasim_locators():
    schema = load_schema()
    registry, _ = schema.load_registry()
    dynasim = [
        entry
        for entry in registry["entries"]
        if entry["external_reference"].startswith("DYNASIM")
    ]
    assert len(dynasim) == 32

    derived_ids = set()
    for entry in dynasim:
        for locator in entry["source_pin"]["exact_locators"]:
            assert locator["row_path"]
            assert locator["column_path"]
            assert locator["row_path"] != "All"
            if locator.get("derivation"):
                derived_ids.add(entry["row_id"])
    assert derived_ids == DERIVED_DYNASIM_ROW_IDS


def test__benchmark_builders__check_without_mutating_artifacts():
    before = {
        REGISTRY_PATH: REGISTRY_PATH.read_bytes(),
        HISTORY_PATH: HISTORY_PATH.read_bytes(),
        WALL_PATH: WALL_PATH.read_bytes(),
    }
    builders = (
        (BENCHMARKS / "build_registry.py", "--check"),
        (BENCHMARKS / "build_history.py", "--check"),
        (BENCHMARKS / "build_wall.py", "--check"),
    )
    for builder, mode in builders:
        subprocess.run(
            [sys.executable, str(builder), mode],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    assert {path: path.read_bytes() for path in before} == before


def test__benchmark_wall__is_self_contained_complete_and_seeded():
    wall_raw = WALL_PATH.read_bytes()
    wall = wall_raw.decode("utf-8")

    assert hashlib.sha256(wall_raw).hexdigest() == WALL_SHA256
    assert wall.count("| n/a |") == SEED_ROW_COUNT
    assert "## Admin Truth" in wall
    assert "## Model Triangulation" in wall
    assert "## Statutory Parameter" in wall
    assert "## Gap ledger" in wall
    assert (
        '`["frame-relative", "pre-alignment", "labor-income proxy"]`' in wall
    )
    assert "http://" not in wall and "https://" not in wall
    assert "`unexplained` | 0" in wall
