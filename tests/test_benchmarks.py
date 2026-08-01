"""Schema, alarm, reproduction, and drift tests for benchmark artifacts."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import multiprocessing
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS = ROOT / "benchmarks"
REGISTRY_PATH = BENCHMARKS / "registry.json"
HISTORY_PATH = BENCHMARKS / "history.jsonl"
RUN_MANIFEST_PATH = BENCHMARKS / "run_manifest.jsonl"
WALL_PATH = BENCHMARKS / "wall.md"
MERGED_MATRIX_SHA256 = (
    "b102e6fe9cda44462a6f198f876d3cbf2a11827974d8aa447fcc2e152e336183"
)

# The explicit runs path also assigns this module to the artifact test tier.
SEED_RUN_PATH = ROOT / "runs" / "first_estimates_v1.json"
SEED_RUN_SHA256 = (
    "719604ca4364e7cdef2293329ed0beb0e011e5d4d1c34f0e508c8f2fd9932977"
)
RUN_MANIFEST_SEED_PREFIX_SHA256 = (
    "b8cacb139ce67ed1bf5ba1509d4ca9f995d6d5e032ddfa4cb4ec565ba220f82c"
)
NON_CERTIFIED_RUN_PATH = ROOT / "runs" / "claiming_reference_v1.json"
NON_CERTIFIED_RUN_SHA256 = (
    "ae80d5c2281a15759948fae3e1f7ed3adbd7127d6a243518ff21196b00b99da9"
)
REGISTRY_SHA256 = (
    "3355f6686d67eb39793fb790327010c21ee852704968c627f0d851c6dd7d1726"
)
HISTORY_SEED_PREFIX_SHA256 = (
    "61b8233b430c80c68a26cd5c1cbda8cb71ed8ef2631d96d0d4b7424f2f430d31"
)
CURRENT_HISTORY_SHA256 = (
    "61b8233b430c80c68a26cd5c1cbda8cb71ed8ef2631d96d0d4b7424f2f430d31"
)
WALL_SHA256 = (
    "88658e92030aaf7003ef19a5d5ec33748ea170e2daf3e146ae34d465f4628281"
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
    "preliminary_source": 0,
    "unverified_source": 20,
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


def load_wall_builder():
    """Load the wall builder with its sibling schema import available."""

    path = BENCHMARKS / "build_wall.py"
    spec = importlib.util.spec_from_file_location(
        "benchmark_wall_builder", path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    previous_schema = sys.modules.get("schema")
    sys.path.insert(0, str(BENCHMARKS))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(BENCHMARKS))
        if previous_schema is None:
            sys.modules.pop("schema", None)
        else:
            sys.modules["schema"] = previous_schema
    return module


def load_append_history():
    """Load the append tool with its sibling schema import available."""

    path = BENCHMARKS / "append_history.py"
    spec = importlib.util.spec_from_file_location(
        "benchmark_append_history", path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    previous_schema = sys.modules.get("schema")
    sys.path.insert(0, str(BENCHMARKS))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(BENCHMARKS))
        if previous_schema is None:
            sys.modules.pop("schema", None)
        else:
            sys.modules["schema"] = previous_schema
    return module


def git_blob(revision: str, relative_path: str) -> bytes:
    """Read one committed blob without changing the worktree.

    A path absent at the revision (the harness's first-add commit, or a
    CI merge ref whose first parent predates benchmarks/) reads as empty
    bytes: a first add is a pure append.
    """

    result = subprocess.run(
        ["git", "show", f"{revision}:{relative_path}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace")
        if (
            "does not exist" in stderr
            or "exists on disk, but not in" in stderr
        ):
            return b""
        raise subprocess.CalledProcessError(
            result.returncode, result.args, result.stdout, result.stderr
        )
    return result.stdout


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
    run_sha: str | None = None,
) -> tuple[Path, Path]:
    """Write a canonical synthetic next-run record set for append tests."""

    schema = load_schema()
    registry, registry_raw = schema.load_registry()
    history, _ = schema.load_history()
    latest = schema.latest_records(history)
    if run_artifact is None:
        run_artifact = NON_CERTIFIED_RUN_PATH
    if run_sha is None:
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


def _check_manifest_git_bindings(tmp_path: Path) -> None:
    """Regress index preflight, HEAD binding, and literal path identity."""

    schema = load_schema()
    repo = tmp_path / "artifact-git-repo"
    runs = repo / "runs"
    runs.mkdir(parents=True)
    wildcard_dir = repo / "wild"
    wildcard_dir.mkdir()

    def git(*arguments: str) -> None:
        subprocess.run(
            ["git", *arguments],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        )

    def entry(path: Path) -> dict[str, str]:
        return {
            "artifact_path": path.relative_to(repo).as_posix(),
            "evaluated_at_run": hashlib.sha256(path.read_bytes()).hexdigest(),
        }

    git("init", "--quiet")
    modified = runs / "modified.json"
    victim = wildcard_dir / "victim.json"
    modified.write_bytes(b'{"evaluation":"committed"}\n')
    victim.write_bytes(b'{"evaluation":"literal-victim"}\n')
    git(
        "--literal-pathspecs",
        "add",
        "--",
        "runs/modified.json",
        "wild/victim.json",
    )
    git(
        "-c",
        "user.name=Benchmark Test",
        "-c",
        "user.email=benchmark@example.test",
        "commit",
        "--quiet",
        "-m",
        "seed artifacts",
    )
    schema.validate_manifest_artifact(entry(modified), repo)

    modified.write_bytes(b'{"evaluation":"staged-modification"}\n')
    git("--literal-pathspecs", "add", "--", "runs/modified.json")
    schema.validate_index_manifest_artifact(entry(modified), repo)
    with pytest.raises(AssertionError, match="differs from HEAD"):
        schema.validate_manifest_artifact(entry(modified), repo)

    staged_new = runs / "staged-new.json"
    staged_new.write_bytes(b'{"evaluation":"staged-new"}\n')
    git("--literal-pathspecs", "add", "--", "runs/staged-new.json")
    schema.validate_index_manifest_artifact(entry(staged_new), repo)
    with pytest.raises(AssertionError, match="not committed at HEAD"):
        schema.validate_manifest_artifact(entry(staged_new), repo)

    literal_wildcard = wildcard_dir / "*.json"
    literal_wildcard.write_bytes(victim.read_bytes())
    with pytest.raises(AssertionError, match="not tracked in the Git index"):
        schema.validate_index_manifest_artifact(entry(literal_wildcard), repo)

    # A Git symlink blob whose target text equals the target's bytes must
    # not impersonate a regular committed evaluation artifact.
    target = runs / "target"
    target.write_bytes(b"target")
    link = runs / "link.json"
    link.symlink_to("target")
    git("--literal-pathspecs", "add", "--", "runs/target", "runs/link.json")
    git(
        "-c",
        "user.name=Benchmark Test",
        "-c",
        "user.email=benchmark@example.test",
        "commit",
        "--quiet",
        "-m",
        "symlink artifacts",
    )
    link_entry = {
        "artifact_path": "runs/link.json",
        "evaluated_at_run": hashlib.sha256(b"target").hexdigest(),
    }
    with pytest.raises(AssertionError, match="symlink component"):
        schema.validate_index_manifest_artifact(link_entry, repo)
    with pytest.raises(AssertionError, match="symlink component"):
        schema.validate_manifest_artifact(link_entry, repo)
    # Defense in depth: even with the worktree link replaced by a regular
    # file carrying the same bytes, the staged/committed 120000 mode fails.
    link.unlink()
    link.write_bytes(b"target")
    with pytest.raises(
        AssertionError, match="not a regular (staged|committed) file"
    ):
        schema.validate_index_manifest_artifact(link_entry, repo)
    with pytest.raises(
        AssertionError, match="not a regular (staged|committed) file"
    ):
        schema.validate_manifest_artifact(link_entry, repo)


def _check_append_rollback_isolation(tmp_path: Path) -> None:
    """Ensure a failed second appender cannot erase the first append."""

    append_history = load_append_history()
    manifest_path = tmp_path / "concurrent-manifest.jsonl"
    history_path = tmp_path / "concurrent-history.jsonl"
    manifest_seed = b'{"seed":"manifest"}\n'
    history_seed = b'{"seed":"history"}\n'
    first_manifest = b'{"append":"first-manifest"}\n'
    first_history = b'{"append":"first-history"}\n'
    second_manifest = b'{"append":"second-manifest"}\n'
    second_history = b'{"append":"second-history"}\n'
    manifest_path.write_bytes(manifest_seed)
    history_path.write_bytes(history_seed)

    context = multiprocessing.get_context("fork")
    first_locked = context.Event()
    second_waiting = context.Event()

    def configure_paths() -> None:
        append_history.RUN_MANIFEST_PATH = manifest_path
        append_history.HISTORY_PATH = history_path

    def first_worker() -> None:
        configure_paths()

        def validate_candidate(_path: Path, _artifact: Path):
            first_locked.set()
            if not second_waiting.wait(10):
                raise TimeoutError("second appender never reached its lock")
            return first_history, first_manifest

        append_history.validate_candidate = validate_candidate
        append_history.load_history = lambda **_kwargs: None
        append_history.append(Path("unused"), Path("unused"))

    def second_worker() -> None:
        configure_paths()
        real_flock = append_history.fcntl.flock
        signaled = False

        def tracked_flock(descriptor: int, operation: int):
            nonlocal signaled
            if operation == append_history.fcntl.LOCK_EX and not signaled:
                signaled = True
                second_waiting.set()
            return real_flock(descriptor, operation)

        def validate_candidate(_path: Path, _artifact: Path):
            return second_history, second_manifest

        def fail_after_write(**_kwargs):
            raise RuntimeError("injected post-write failure")

        append_history.fcntl.flock = tracked_flock
        append_history.validate_candidate = validate_candidate
        append_history.load_history = fail_after_write
        try:
            append_history.append(Path("unused"), Path("unused"))
        except RuntimeError as error:
            if str(error) == "injected post-write failure":
                return
            raise
        raise AssertionError("second appender did not reach injected failure")

    first = context.Process(target=first_worker)
    second = context.Process(target=second_worker)
    first.start()
    assert first_locked.wait(10), "first appender never acquired both locks"
    second.start()
    for process in (first, second):
        process.join(15)
        if process.is_alive():
            process.terminate()
            process.join(5)
        assert process.exitcode == 0

    assert manifest_path.read_bytes() == manifest_seed + first_manifest
    assert history_path.read_bytes() == history_seed + first_history


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
    _check_benchmark_migration_round_trip()


def _check_benchmark_migration_round_trip():
    """Exercise the merged-matrix lossless migration regression."""

    schema = load_schema()
    registry, _ = schema.load_registry()
    history, _ = schema.load_history()
    seed_records = history[:SEED_ROW_COUNT]
    reconstructed = schema.reconstruct_legacy_matrix(registry, seed_records)
    assert (
        hashlib.sha256(schema.canonical_json_bytes(reconstructed)).hexdigest()
        == MERGED_MATRIX_SHA256
    )

    entries = {entry["row_id"]: entry for entry in registry["entries"]}
    assert (
        entries["cbo.taxable_payroll.trajectory_2015_100"][
            "published_metadata"
        ]["underlying_published_values_withheld_from_comparison"]
        == "Dollar levels are retained only as frozen extraction inputs to "
        "calculate the allowed index; they are not reported as a comparison."
    )
    wish_metadata = entries["wish.hr4289.employee_rate.share_of_payroll"][
        "published_metadata"
    ]
    assert wish_metadata["legislative_status"] == (
        "introduced and referred; not enacted"
    )
    assert wish_metadata["companion_parameters"] == {
        "combined_employee_employer_rate_percent": 0.6,
        "combined_rate_print_status": (
            "derived as 0.3 + 0.3; not separately printed"
        ),
        "self_employment_rate_percent": 0.6,
        "separate_employer_rate_percent": 0.3,
    }
    assert (
        len(
            registry["migration_context"]["certification_context"]["m6"][
                "not_certified"
            ]
        )
        == 11
    )

    future_cases = (
        (
            "ssa.adjusted_taxable_payroll_per_covered_worker",
            "future.publisher.verified.metric",
        ),
        (
            "dynasim.mermin.price_indexing.all",
            "future.publisher.unverified.metric",
        ),
    )
    for template_id, future_id in future_cases:
        grown_registry = copy.deepcopy(registry)
        future_entry = copy.deepcopy(
            next(
                entry
                for entry in grown_registry["entries"]
                if entry["row_id"] == template_id
            )
        )
        future_entry["row_id"] = future_id
        future_entry["spec_revisions"] = []
        if future_entry["verification_class"] == "reported_not_verified":
            provenance = future_entry["source_pin"][
                "reported_value_provenance"
            ]
            provenance["publisher_capture_status"] = (
                "publisher_capture_unavailable"
            )
            for locator in future_entry["source_pin"]["exact_locators"]:
                locator["capture_status"] = (
                    "Publisher-controlled bytes are not currently available."
                )
                locator.pop("unmanifested_corroborating_copy")
        grown_registry["entries"].append(future_entry)
        grown_registry["row_count"] += 1
        grown_registry["tier_counts"][future_entry["tier"]] += 1
        grown_registry["gap_class_counts"][future_entry["gap_class"]] += 1
        future_record = copy.deepcopy(
            next(
                record
                for record in seed_records
                if record["row_id"] == template_id
            )
        )
        future_record["row_id"] = future_id

        schema.validate_registry(grown_registry)
        grown_reconstruction = schema.reconstruct_legacy_matrix(
            grown_registry, [*seed_records, future_record]
        )
        assert (
            hashlib.sha256(
                schema.canonical_json_bytes(grown_reconstruction)
            ).hexdigest()
            == MERGED_MATRIX_SHA256
        )


def test__benchmark_history__reproduces_frozen_seed_prefix():
    schema = load_schema()
    registry, registry_raw = schema.load_registry()
    history, history_raw = schema.load_history()
    manifest, manifest_raw = schema.load_run_manifest()
    prefix = b"".join(history_raw.splitlines(keepends=True)[:SEED_ROW_COUNT])
    seed = history[:SEED_ROW_COUNT]

    assert sha256(SEED_RUN_PATH) == SEED_RUN_SHA256
    assert hashlib.sha256(registry_raw).hexdigest() == REGISTRY_SHA256
    assert hashlib.sha256(prefix).hexdigest() == HISTORY_SEED_PREFIX_SHA256
    assert hashlib.sha256(history_raw).hexdigest() == CURRENT_HISTORY_SHA256
    assert (
        hashlib.sha256(manifest_raw.splitlines(keepends=True)[0]).hexdigest()
        == RUN_MANIFEST_SEED_PREFIX_SHA256
    )
    assert len(history) >= SEED_ROW_COUNT
    assert [record["row_id"] for record in seed] == [
        entry["row_id"] for entry in registry["entries"][:SEED_ROW_COUNT]
    ]
    assert {record["evaluated_at_run"] for record in seed} == {SEED_RUN_SHA256}
    assert {record["registry_sha"] for record in seed} == {REGISTRY_SHA256}
    assert Counter(record["gap_class"] for record in seed) == {
        key: value for key, value in GAP_COUNTS.items() if value
    }
    assert manifest[0] == {
        "artifact_path": "runs/first_estimates_v1.json",
        "evaluated_at_run": SEED_RUN_SHA256,
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


def _check_unverified_history_binding():
    """Exercise current-history gap-class binding."""

    schema = load_schema()
    registry, registry_raw = schema.load_registry()
    history, _ = schema.load_history()
    laundered = copy.deepcopy(history)
    mermin = next(
        record for record in laundered if ".mermin." in record["row_id"]
    )
    mermin["gap_class"] = "preliminary_source"

    with pytest.raises(AssertionError, match="gap class disagrees"):
        schema.validate_history_against_registry(
            laundered,
            registry,
            hashlib.sha256(registry_raw).hexdigest(),
        )


def _check_future_label_evidence_binding():
    """Exercise future label consistency and evidence binding."""

    schema = load_schema()
    registry, registry_raw = schema.load_registry()
    history, _ = schema.load_history()
    registry_sha = hashlib.sha256(registry_raw).hexdigest()

    inconsistent_array = copy.deepcopy(history)
    inconsistent_array[0]["label_state"][
        "ratified_fitting_free_exact_label_array"
    ] = ["future-label"]
    with pytest.raises(AssertionError, match="inconsistent ratified label"):
        schema.validate_history(inconsistent_array)

    inconsistent_locator = copy.deepcopy(history)
    inconsistent_locator[0]["label_state"][
        "ratified_array_locator"
    ] = "docs/design/future.md §1"
    with pytest.raises(AssertionError, match="inconsistent ratified-array"):
        schema.validate_history(inconsistent_locator)

    inconsistent_activation = copy.deepcopy(history)
    inconsistent_activation[0]["label_state"][
        "ratified_array_activation_asserted_by_this_matrix"
    ] = True
    with pytest.raises(AssertionError, match="inconsistent label activation"):
        schema.validate_history(inconsistent_activation)

    unsupported_mutations = (
        (
            "ratified_fitting_free_exact_label_array",
            ["future-label"],
            "ratified label array disagrees",
        ),
        (
            "ratified_array_locator",
            "docs/design/future.md §1",
            "ratified-array locator disagrees",
        ),
        (
            "ratified_array_activation_asserted_by_this_matrix",
            True,
            "activation claim disagrees",
        ),
        (
            "population_alignment_claim",
            True,
            "population-alignment claim disagrees",
        ),
        (
            "individual_administrative_truth_claim",
            True,
            "individual-administrative-truth claim disagrees",
        ),
    )
    for field, value, message in unsupported_mutations:
        unsupported = copy.deepcopy(history)
        for record in unsupported:
            record["label_state"][field] = value
        schema.validate_history(unsupported)
        with pytest.raises(AssertionError, match=message):
            schema.validate_history_against_registry(
                unsupported,
                registry,
                registry_sha,
            )

    false_embedded_claim = copy.deepcopy(history)
    false_embedded_claim[0]["label_state"][
        "source_artifact_embedded_labels"
    ] = ["future-label"]
    with pytest.raises(AssertionError, match="source-artifact label claim"):
        schema.validate_history_against_registry(
            false_embedded_claim,
            registry,
            registry_sha,
        )


def _check_future_label_rendering():
    """Exercise future label-diversity rendering from history."""

    schema = load_schema()
    history, _ = schema.load_history()
    future = copy.deepcopy(history[:3])
    future[0]["label_state"]["source_artifact_embedded_labels"] = ["future-a"]
    future[1]["label_state"]["source_artifact_embedded_labels"] = ["future-b"]
    future[2]["label_state"]["source_artifact_embedded_labels"] = None
    for record in future:
        record["label_state"][
            "ratified_array_activation_asserted_by_this_matrix"
        ] = True
    wall_builder = load_wall_builder()
    rendered = wall_builder.render_honest_labels(future)

    assert '`["future-a"]` (1 row)' in rendered
    assert '`["future-b"]` (1 row)' in rendered
    assert "Rows with no embedded label array: 1." in rendered
    assert "this evaluation asserts that its activation event" in rendered


def test__benchmark_registry__retains_source_and_verification_drift_laws(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
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
    assert all(entry["gap_class"] == "unverified_source" for entry in reported)

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

    laundered = copy.deepcopy(reported[0])
    laundered["gap_class"] = "preliminary_source"
    with pytest.raises(AssertionError, match="must use unverified_source"):
        schema.validate_registry_entry(laundered)

    unmarked_preliminary = copy.deepcopy(
        next(
            entry for entry in verified if entry["row_id"].startswith("wish.")
        )
    )
    unmarked_preliminary["gap_class"] = "preliminary_source"
    with pytest.raises(AssertionError, match="structured preliminary status"):
        schema.validate_registry_entry(unmarked_preliminary)

    marked_preliminary = copy.deepcopy(
        next(
            entry
            for entry in verified
            if entry["row_id"] == "ssa.reported_taxable_earnings_per_worker"
        )
    )
    marked_preliminary["gap_class"] = "preliminary_source"
    schema.validate_registry_entry(marked_preliminary)

    monkeypatch.setattr(schema, "ROOT", tmp_path)
    preliminary_cases = (
        (
            "missing",
            {},
            "Publisher marks this value preliminary.",
            "publisher status marker is missing",
        ),
        (
            "false",
            {"source_status": False},
            "Publisher marks this value preliminary.",
            "publisher status marker is invalid",
        ),
        (
            "negated",
            {"source_status": "historical"},
            "final; explicitly not preliminary",
            "structured preliminary status",
        ),
    )
    for name, observation, prose_status, message in preliminary_cases:
        evidence_path = tmp_path / f"{name}.json"
        evidence_raw = schema.canonical_json_bytes(
            {"observations": [observation]}
        )
        evidence_path.write_bytes(evidence_raw)
        extraction = {
            "json_pointer": "/observations",
            "path": evidence_path.name,
            "sha256": hashlib.sha256(evidence_raw).hexdigest(),
        }
        candidate = copy.deepcopy(marked_preliminary)
        locator = copy.deepcopy(candidate["source_pin"]["exact_locators"][0])
        locator["committed_extraction"] = extraction
        locator["source_status"] = prose_status
        candidate["source_pin"] = {
            "artifacts": [{"pin_type": "committed_extraction", **extraction}],
            "exact_locators": [locator],
            "reported_value_provenance": None,
        }
        with pytest.raises(AssertionError, match=message):
            schema.validate_registry_entry(candidate)
    _check_unverified_history_binding()


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
    previous_registry_raw = prior_committed_blob(REGISTRY_PATH)
    if previous_registry_raw:
        previous_registry = json.loads(previous_registry_raw)
        schema.validate_append_mostly_registry(previous_registry, registry)

    previous_history = prior_committed_blob(HISTORY_PATH)
    current_history = HISTORY_PATH.read_bytes()
    schema.validate_append_only_history(previous_history, current_history)
    # Truncating the current history is a violation against any baseline,
    # including the empty first-add parent a CI merge ref presents.
    with pytest.raises(AssertionError, match="history is append-only"):
        schema.validate_append_only_history(
            current_history, current_history[:-1]
        )

    previous_manifest = prior_committed_blob(RUN_MANIFEST_PATH)
    current_manifest = RUN_MANIFEST_PATH.read_bytes()
    schema.validate_append_only_run_manifest(
        previous_manifest, current_manifest
    )
    with pytest.raises(AssertionError, match="run manifest is append-only"):
        schema.validate_append_only_run_manifest(
            current_manifest, current_manifest[:-1]
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
    new_entry["published_metadata"] = {}
    new_entry["spec_revisions"] = []
    appended["entries"].append(new_entry)
    appended["row_count"] += 1
    appended["tier_counts"][new_entry["tier"]] += 1
    appended["gap_class_counts"][new_entry["gap_class"]] += 1
    schema.validate_append_mostly_registry(registry, appended)


def test__benchmark_append_checker__fails_closed_and_never_mutates(tmp_path):
    before = {
        HISTORY_PATH: HISTORY_PATH.read_bytes(),
        RUN_MANIFEST_PATH: RUN_MANIFEST_PATH.read_bytes(),
    }

    valid, valid_run = write_candidate(tmp_path, "valid")
    assert valid_run == NON_CERTIFIED_RUN_PATH
    assert sha256(valid_run) == NON_CERTIFIED_RUN_SHA256
    assert json.loads(valid_run.read_text())["reported_not_gated"] is True
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

    for private_key, value in (
        ("_foo", "fabricated"),
        ("_byte_start", 0),
        ("_byte_end", 1),
    ):
        private_key_candidate, private_key_run = write_candidate(
            tmp_path,
            private_key.removeprefix("_"),
            mutate=lambda records, key=private_key, injected=value: records[
                0
            ].__setitem__(key, injected),
        )
        result = run_append_check(private_key_candidate, private_key_run)
        assert result.returncode != 0
        assert "history line 1 keys have drifted" in result.stderr

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

    fabricated_label_note, fabricated_label_note_run = write_candidate(
        tmp_path,
        "fabricated_label_note",
        mutate=lambda records: records[0]["label_state"].__setitem__(
            "source_artifact_label_note", "Fabricated evidence narrative."
        ),
    )
    result = run_append_check(fabricated_label_note, fabricated_label_note_run)
    assert result.returncode != 0
    assert "label note disagrees with registered evidence" in result.stderr

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

    missing_artifact = ROOT / "runs" / ".missing-benchmark-evaluation.json"
    missing, _ = write_candidate(
        tmp_path,
        "missing_artifact",
        run_artifact=missing_artifact,
        run_sha=NON_CERTIFIED_RUN_SHA256,
    )
    result = run_append_check(missing, missing_artifact)
    assert result.returncode != 0
    assert "missing immutable evaluation artifact" in result.stderr

    untracked_artifact = BENCHMARKS / ".untracked-evaluation-artifact.json"
    assert not untracked_artifact.exists()
    try:
        untracked_artifact.write_text('{"evaluation":"untracked"}\n')
        untracked, _ = write_candidate(
            tmp_path,
            "untracked_artifact",
            run_artifact=untracked_artifact,
        )
        result = run_append_check(untracked, untracked_artifact)
        assert result.returncode != 0
        assert "not tracked in the Git index" in result.stderr
    finally:
        untracked_artifact.unlink(missing_ok=True)

    escaping_artifact = tmp_path / "path-escaping-evaluation.json"
    escaping_artifact.write_text('{"evaluation":"outside repository"}\n')
    escaping, _ = write_candidate(
        tmp_path,
        "path_escaping_artifact",
        run_artifact=escaping_artifact,
    )
    result = run_append_check(escaping, escaping_artifact)
    assert result.returncode != 0
    assert "path escapes repository" in result.stderr

    hash_mismatch, _ = write_candidate(
        tmp_path,
        "hash_mismatch",
        run_artifact=NON_CERTIFIED_RUN_PATH,
        run_sha="0" * 64,
    )
    result = run_append_check(hash_mismatch, NON_CERTIFIED_RUN_PATH)
    assert result.returncode != 0
    assert "artifact SHA mismatch" in result.stderr

    schema = load_schema()
    history, _ = schema.load_history()
    manifest, _ = schema.load_run_manifest()
    direct_records, _ = schema.load_history(valid)
    with pytest.raises(
        AssertionError, match="run manifest must match history"
    ):
        schema.validate_history_run_artifacts(
            history + direct_records,
            manifest,
        )

    _check_manifest_git_bindings(tmp_path)
    _check_append_rollback_isolation(tmp_path)
    assert {path: path.read_bytes() for path in before} == before


def test__benchmark_builders__check_without_mutating_artifacts():
    before = {
        REGISTRY_PATH: REGISTRY_PATH.read_bytes(),
        HISTORY_PATH: HISTORY_PATH.read_bytes(),
        RUN_MANIFEST_PATH: RUN_MANIFEST_PATH.read_bytes(),
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
    assert (
        '`["frame-relative", "pre-alignment", "labor-income proxy"]` '
        "(10 rows)" in wall
    )
    assert "Rows with no embedded label array: 32." in wall
    assert "certified run set" not in wall
    assert "http://" not in wall and "https://" not in wall
    assert "`preliminary_source` | 0" in wall
    assert "`unverified_source` | 20" in wall
    assert "`unexplained` | 0" in wall
    _check_future_label_evidence_binding()
    _check_future_label_rendering()
