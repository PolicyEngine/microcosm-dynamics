"""Schema, alarm, reproduction, and drift tests for benchmark artifacts."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
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
CURRENT_HISTORY_SHA256 = (
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


def git_blob(revision: str, relative_path: str) -> bytes:
    """Read one committed blob without changing the worktree."""

    return subprocess.run(
        ["git", "show", f"{revision}:{relative_path}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout


def prior_committed_blob(path: Path) -> bytes:
    """Return the blob immediately before the current working artifact."""

    relative_path = path.relative_to(ROOT).as_posix()
    head = git_blob("HEAD", relative_path)
    if head != path.read_bytes():
        return head
    return git_blob("HEAD^", relative_path)


def write_candidate(
    tmp_path: Path,
    name: str,
    *,
    mutate=None,
    run_artifact: Path | None = None,
) -> tuple[Path, Path]:
    """Write a canonical synthetic next-run record set for append tests."""

    schema = load_schema()
    registry, registry_raw = schema.load_registry()
    history, _ = schema.load_history()
    latest = schema.latest_records(history)
    if run_artifact is None:
        run_artifact = tmp_path / f"{name}.run.json"
        run_artifact.write_bytes(
            f'{{"certified_test_run":"{name}"}}\n'.encode()
        )
    run_sha = sha256(run_artifact)
    registry_sha = hashlib.sha256(registry_raw).hexdigest()
    records = []
    for entry in registry["entries"]:
        record = copy.deepcopy(latest[entry["row_id"]])
        record["evaluated_at_run"] = run_sha
        record["registry_sha"] = registry_sha
        records.append(record)
    if mutate is not None:
        mutate(records)
    candidate = tmp_path / f"{name}.jsonl"
    candidate.write_bytes(
        b"".join(schema.canonical_jsonl_line(record) for record in records)
    )
    return candidate, run_artifact


def run_append_check(
    candidate: Path, run_artifact: Path, *, optimized: bool = False
) -> subprocess.CompletedProcess:
    """Run the public append checker and retain diagnostics."""

    command = [sys.executable]
    if optimized:
        command.append("-O")
    command.extend(
        [
            str(BENCHMARKS / "append_history.py"),
            str(candidate),
            "--run-artifact",
            str(run_artifact),
            "--check",
        ]
    )
    return subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


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
    seed = history[:SEED_ROW_COUNT]

    assert sha256(SEED_RUN_PATH) == SEED_RUN_SHA256
    assert hashlib.sha256(registry_raw).hexdigest() == REGISTRY_SHA256
    assert hashlib.sha256(prefix).hexdigest() == HISTORY_SEED_PREFIX_SHA256
    assert hashlib.sha256(history_raw).hexdigest() == CURRENT_HISTORY_SHA256
    assert len(history) >= SEED_ROW_COUNT
    assert [record["row_id"] for record in seed] == [
        entry["row_id"] for entry in registry["entries"][:SEED_ROW_COUNT]
    ]
    assert {record["evaluated_at_run"] for record in seed} == {SEED_RUN_SHA256}
    assert {record["registry_sha"] for record in seed} == {REGISTRY_SHA256}
    assert Counter(record["gap_class"] for record in seed) == {
        key: value for key, value in GAP_COUNTS.items() if value
    }


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

    multiple_sentences = [copy.deepcopy(history[0])]
    multiple_sentences[0]["gap_note"] = "One sentence. Another sentence."
    with pytest.raises(AssertionError, match="one sentence"):
        schema.validate_history(multiple_sentences)

    invalid_measurement = [copy.deepcopy(history[0])]
    invalid_measurement[0]["our"]["value"] = "invented"
    with pytest.raises(AssertionError, match="invalid our value"):
        schema.validate_history(invalid_measurement)

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

    for entry in verified:
        assert entry["source_pin"]["reported_value_provenance"] is None
        for locator in entry["source_pin"]["exact_locators"]:
            assert "capture_status" not in locator
            assert "unmanifested_corroborating_copy" not in locator


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


def test__benchmark_registry_and_history__are_append_only_across_commits():
    schema = load_schema()
    registry, _ = schema.load_registry()
    previous_registry = json.loads(prior_committed_blob(REGISTRY_PATH))
    schema.validate_append_mostly_registry(previous_registry, registry)

    previous_history = prior_committed_blob(HISTORY_PATH)
    current_history = HISTORY_PATH.read_bytes()
    schema.validate_append_only_history(previous_history, current_history)
    with pytest.raises(AssertionError, match="history is append-only"):
        schema.validate_append_only_history(
            previous_history, current_history[:-1]
        )

    silent_source_change = copy.deepcopy(registry)
    silent_source_change["entries"][0]["source_pin"]["exact_locators"][0][
        "page"
    ] = "corrected HTML locator"
    with pytest.raises(AssertionError, match="needs one appended revision"):
        schema.validate_append_mostly_registry(registry, silent_source_change)

    revised = copy.deepcopy(silent_source_change)
    revised["entries"][0]["spec_revisions"].append(
        {
            "changed_fields": ["/source_pin/exact_locators/0/page"],
            "note": "Corrected the exact published page locator.",
            "revision": 1,
        }
    )
    schema.validate_append_mostly_registry(registry, revised)

    false_revision = copy.deepcopy(revised)
    false_revision["entries"][0]["spec_revisions"][0]["changed_fields"] = [
        "/quantity"
    ]
    with pytest.raises(AssertionError, match="omits a changed field"):
        schema.validate_append_mostly_registry(registry, false_revision)

    reordered = copy.deepcopy(registry)
    reordered["entries"][0:2] = reversed(reordered["entries"][0:2])
    with pytest.raises(AssertionError, match="removed, reordered, or renamed"):
        schema.validate_append_mostly_registry(registry, reordered)

    law_change = copy.deepcopy(registry)
    law_change["validation_only_law"] += " Changed."
    with pytest.raises(AssertionError, match="immutable registry law"):
        schema.validate_append_mostly_registry(registry, law_change)

    appended = copy.deepcopy(registry)
    new_entry = copy.deepcopy(appended["entries"][-1])
    new_entry["row_id"] = "wish.future_statutory_parameter"
    new_entry["spec_revisions"] = []
    appended["entries"].append(new_entry)
    appended["row_count"] += 1
    appended["tier_counts"][new_entry["tier"]] += 1
    appended["gap_class_counts"][new_entry["gap_class"]] += 1
    schema.validate_append_mostly_registry(registry, appended)


def test__benchmark_append_checker__fails_closed_and_never_mutates(tmp_path):
    before = HISTORY_PATH.read_bytes()

    valid, valid_run = write_candidate(tmp_path, "valid")
    result = run_append_check(valid, valid_run)
    assert result.returncode == 0, result.stderr

    wrong_order, wrong_order_run = write_candidate(
        tmp_path,
        "wrong_order",
        mutate=lambda records: records.__setitem__(
            slice(0, 2), reversed(records[0:2])
        ),
    )
    result = run_append_check(wrong_order, wrong_order_run)
    assert result.returncode != 0
    assert "registry order" in result.stderr

    registry_mismatch, registry_mismatch_run = write_candidate(
        tmp_path,
        "registry_mismatch",
        mutate=lambda records: [
            record.__setitem__("registry_sha", "0" * 64) for record in records
        ],
    )
    result = run_append_check(registry_mismatch, registry_mismatch_run)
    assert result.returncode != 0
    assert "does not match registry.json" in result.stderr

    unexplained, unexplained_run = write_candidate(
        tmp_path,
        "unexplained",
        mutate=lambda records: records[0].__setitem__(
            "gap_class", "unexplained"
        ),
    )
    result = run_append_check(unexplained, unexplained_run, optimized=True)
    assert result.returncode != 0
    assert "unexplained benchmark gap" in result.stderr

    unit_mismatch, unit_mismatch_run = write_candidate(
        tmp_path,
        "unit_mismatch",
        mutate=lambda records: records[0]["our"].__setitem__(
            "unit", "invented unit"
        ),
    )
    result = run_append_check(unit_mismatch, unit_mismatch_run)
    assert result.returncode != 0
    assert "our unit does not match" in result.stderr

    published_drift, published_drift_run = write_candidate(
        tmp_path,
        "published_drift",
        mutate=lambda records: records[9]["published"].__setitem__(
            "value", records[9]["published"]["value"] + 1
        ),
    )
    result = run_append_check(published_drift, published_drift_run)
    assert result.returncode != 0
    assert "published value moved" in result.stderr

    reused, _ = write_candidate(tmp_path, "reused", run_artifact=SEED_RUN_PATH)
    result = run_append_check(reused, SEED_RUN_PATH)
    assert result.returncode != 0
    assert "run SHA already exists" in result.stderr

    wrong_artifact = tmp_path / "wrong-artifact.json"
    wrong_artifact.write_text('{"wrong":true}\n')
    result = run_append_check(valid, wrong_artifact)
    assert result.returncode != 0
    assert "does not match the run artifact SHA" in result.stderr

    assert HISTORY_PATH.read_bytes() == before


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
            [sys.executable, "-O", str(builder), mode],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    assert {path: path.read_bytes() for path in before} == before


def test__benchmark_wall__is_self_contained_complete_and_seeded():
    schema = load_schema()
    history, _ = schema.load_history()
    records_by_row = {}
    for record in history:
        records_by_row.setdefault(record["row_id"], []).append(record)
    expected_trends = Counter()
    for records in records_by_row.values():
        if len(records) == 1:
            expected_trends["n/a"] += 1
        elif records[-1]["deviation"] == records[-2]["deviation"]:
            expected_trends["unchanged"] += 1
        else:
            expected_trends["changed"] += 1

    wall_raw = WALL_PATH.read_bytes()
    wall = wall_raw.decode("utf-8")

    assert hashlib.sha256(wall_raw).hexdigest() == WALL_SHA256
    for trend in ("n/a", "changed", "unchanged"):
        assert wall.count(f"| {trend} |") == expected_trends[trend]
    assert "## Admin Truth" in wall
    assert "## Model Triangulation" in wall
    assert "## Statutory Parameter" in wall
    assert "## Gap ledger" in wall
    assert (
        '`["frame-relative", "pre-alignment", "labor-income proxy"]`' in wall
    )
    assert "http://" not in wall and "https://" not in wall
    assert "`unexplained` | 0" in wall
