"""Fail-closed validators for the standing benchmark artifacts."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path, PurePosixPath
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REGISTRY_PATH = HERE / "registry.json"
HISTORY_PATH = HERE / "history.jsonl"
RUN_MANIFEST_PATH = HERE / "run_manifest.jsonl"

TIERS = (
    "admin_truth",
    "model_triangulation",
    "statutory_parameter",
)
GAP_CLASSES = (
    "label_mismatch",
    "frame_no_alignment",
    "concept_mismatch",
    "module_missing",
    "small_cell",
    "preliminary_source",
    "unverified_source",
    "unexplained",
)
COMPARISON_SCOPES = ("ratio", "share", "trajectory", "ordering")
MATRIX_DISPLAY = (
    "frame-relative proxy covered-earnings; no population alignment"
)
LEGACY_COMPARISON_SCOPES = (
    "ratio",
    "share",
    "trajectory",
    "ordering",
    "distributional_incidence",
    "distributional_share",
    "age_trajectory",
)
LEGACY_MATRIX_SHA256 = (
    "b102e6fe9cda44462a6f198f876d3cbf2a11827974d8aa447fcc2e152e336183"
)
LEGACY_ROW_IDS = (
    "ssa.reported_taxable_earnings_per_worker",
    "ssa.adjusted_taxable_payroll_per_covered_worker",
    "ssa.gross_contributions_per_worker",
    "ssa.net_payroll_tax_contributions_per_covered_worker",
    "ssa.retired_worker_beneficiaries_per_worker",
    "ssa.retired_worker_awards_per_worker",
    "ssa.retired_worker_benefits_per_reported_taxable_earnings",
    "cbo.taxable_payroll.trajectory_2015_100",
    "cbo.tax_revenue.share_of_taxable_payroll",
    "dynasim.favreault_steuerle.package1b.married.male.lose_ge_5",
    "dynasim.favreault_steuerle.package1b.married.male.gain_ge_5",
    "dynasim.favreault_steuerle.package1b.married.female.lose_ge_5",
    "dynasim.favreault_steuerle.package1b.married.female.gain_ge_5",
    "dynasim.favreault_steuerle.package1b.married.female.gain_ge_20",
    "dynasim.favreault_steuerle.package1b.divorced.male.lose_ge_5",
    "dynasim.favreault_steuerle.package1b.divorced.male.gain_ge_5",
    "dynasim.favreault_steuerle.package1b.divorced.female.gain_ge_5",
    "dynasim.favreault_steuerle.package1b.widowed.male.lose_ge_20",
    "dynasim.favreault_steuerle.package1b.widowed.male.lose_ge_5",
    "dynasim.favreault_steuerle.package1b.widowed.female.lose_ge_20",
    "dynasim.favreault_steuerle.package1b.widowed.female.lose_ge_5",
    "dynasim.mermin.price_indexing.all",
    "dynasim.mermin.ppi.generated.q1",
    "dynasim.mermin.ppi.generated.q2",
    "dynasim.mermin.ppi.generated.q3",
    "dynasim.mermin.ppi.generated.q4",
    "dynasim.mermin.ppi.generated.q5",
    "dynasim.mermin.ppi.real_shared.q1",
    "dynasim.mermin.ppi.real_shared.q2",
    "dynasim.mermin.ppi.real_shared.q3",
    "dynasim.mermin.ppi.real_shared.q4",
    "dynasim.mermin.ppi.real_shared.q5",
    "dynasim.mermin.nra70.q1",
    "dynasim.mermin.nra70.q2",
    "dynasim.mermin.nra70.q3",
    "dynasim.mermin.nra70.q4",
    "dynasim.mermin.nra70.q5",
    "dynasim.mermin.nra70.all",
    "dynasim.mermin.cola_minus_0_4pp.age_62_67",
    "dynasim.mermin.cola_minus_0_4pp.age_80_85",
    "dynasim.mermin.four_reform_cost_ordering",
    "wish.hr4289.employee_rate.share_of_payroll",
)
LEGACY_MERMIN_ROW_IDS = frozenset(
    row_id for row_id in LEGACY_ROW_IDS if ".mermin." in row_id
)
PUBLISHER_SOURCE_STATUSES = frozenset(
    {"estimated_allocation", "historical", "preliminary"}
)
HISTORY_SEED_MIGRATIONS = {
    (
        "40ed82ee5ad01b6b36364de2310d45757a8a7dbb5c8f3274e83c46b7f8d514e4",
        "04bf81ffdbe73d8c47bcc8e7e9fb277f1e8fe126373d441f304f72c0f536f954",
    ),
    (
        "04bf81ffdbe73d8c47bcc8e7e9fb277f1e8fe126373d441f304f72c0f536f954",
        "8bf5ee2d519efa225702b30dc38ddefc4a100845d8196d2cf1eb055a058ff1ae",
    ),
    (
        "8bf5ee2d519efa225702b30dc38ddefc4a100845d8196d2cf1eb055a058ff1ae",
        "61b8233b430c80c68a26cd5c1cbda8cb71ed8ef2631d96d0d4b7424f2f430d31",
    ),
}

REGISTRY_KEYS = {
    "allowed_comparison_scopes",
    "canonicalization",
    "deferred_comparisons",
    "entries",
    "external_capture_review",
    "gap_class_counts",
    "gap_classes",
    "honesty_frame",
    "inputs",
    "migration_context",
    "purpose",
    "registry_change_law",
    "row_count",
    "schema_version",
    "seed_evaluation",
    "tier_counts",
    "tiers",
    "validation_only_law",
}
ENTRY_KEYS = {
    "comparison_scope",
    "concept_mismatch",
    "evidential_status",
    "external_reference",
    "gap_class",
    "gap_closure_condition",
    "gap_note",
    "legacy_comparison_scope",
    "our_side_artifact",
    "published_formula",
    "published_metadata",
    "published_unit",
    "quantity",
    "row_id",
    "source_pin",
    "spec_revisions",
    "tier",
    "verification_class",
}
HISTORY_KEYS = {
    "deviation",
    "evaluated_at_run",
    "gap_class",
    "gap_note",
    "label_state",
    "our",
    "published",
    "registry_sha",
    "row_id",
}
HISTORY_OFFSET_KEYS = {"_byte_end", "_byte_start"}
RUN_MANIFEST_KEYS = {"artifact_path", "evaluated_at_run"}
LABEL_STATE_KEYS = {
    "individual_administrative_truth_claim",
    "matrix_display",
    "population_alignment_claim",
    "ratified_array_activation_asserted_by_this_matrix",
    "ratified_array_locator",
    "ratified_fitting_free_exact_label_array",
    "source_artifact_embedded_labels",
    "source_artifact_label_note",
}
REVISION_KEYS = {"changed_fields", "note", "revision"}
IMMUTABLE_REGISTRY_KEYS = {
    "allowed_comparison_scopes",
    "canonicalization",
    "gap_classes",
    "honesty_frame",
    "migration_context",
    "purpose",
    "registry_change_law",
    "schema_version",
    "seed_evaluation",
    "tiers",
    "validation_only_law",
}


def sha256_bytes(raw: bytes) -> str:
    """Return the lowercase SHA-256 digest of bytes."""

    return hashlib.sha256(raw).hexdigest()


def is_sha256(value: Any) -> bool:
    """Return whether value is exactly one lowercase SHA-256 digest."""

    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return value == value.lower()


def require(condition: bool, message: str) -> None:
    """Raise an alarm that remains active under optimized Python."""

    if not condition:
        raise AssertionError(message)


def legacy_registry_entries(registry: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the frozen row prefix migrated from the merged #352 matrix."""

    entries = registry.get("entries")
    require(
        isinstance(entries, list) and len(entries) >= len(LEGACY_ROW_IDS),
        "registry is missing the frozen legacy row prefix",
    )
    prefix = entries[: len(LEGACY_ROW_IDS)]
    require(
        tuple(entry.get("row_id") for entry in prefix) == LEGACY_ROW_IDS,
        "frozen legacy row prefix has drifted",
    )
    return prefix


def is_one_sentence(value: Any) -> bool:
    """Return whether value is one nonempty, terminally punctuated sentence."""

    if not isinstance(value, str):
        return False
    text = value.strip()
    if not text or not any(character.isalnum() for character in text):
        return False
    boundaries = re.findall(r"[.!?](?=\s|$)", text)
    return len(boundaries) == 1 and text[-1] in ".!?"


def is_repo_relative_path(value: Any) -> bool:
    """Return whether value is one normalized repository-relative path."""

    if not isinstance(value, str) or not value or "\\" in value:
        return False
    path = PurePosixPath(value)
    return (
        not path.is_absolute()
        and bool(path.parts)
        and value == path.as_posix()
        and ".." not in path.parts
        and "." not in path.parts
    )


def is_repo_relative_json_path(value: Any) -> bool:
    """Return whether value is one normalized repository-relative JSON path."""

    return (
        isinstance(value, str)
        and value.endswith(".json")
        and is_repo_relative_path(value)
    )


def is_json_pointer(value: Any) -> bool:
    """Return whether value is the root marker or an absolute JSON pointer."""

    return isinstance(value, str) and (value == "/" or value.startswith("/"))


def is_measurement_value(value: Any) -> bool:
    """Reject empty or nonnumeric measurements while permitting orderings."""

    if isinstance(value, bool) or value is None:
        return False
    if isinstance(value, (int, float)):
        return math.isfinite(value)
    if not isinstance(value, list) or not value:
        return False
    if all(isinstance(item, str) and item.strip() for item in value):
        return len(value) == len(set(value))
    return all(
        isinstance(item, dict) and item and any_numeric_leaf(item)
        for item in value
    )


def any_numeric_leaf(value: Any) -> bool:
    """Return whether a JSON-like value contains a finite numeric leaf."""

    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return math.isfinite(value)
    if isinstance(value, dict):
        return any(any_numeric_leaf(item) for item in value.values())
    if isinstance(value, list):
        return any(any_numeric_leaf(item) for item in value)
    return False


def is_label_array(value: Any) -> bool:
    """Return whether value is one nonempty exact label array."""

    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and item.strip() for item in value)
        and len(value) == len(set(value))
    )


def evidence_bound_label_note(
    labels: list[str] | None, legacy_labels: list[str]
) -> str:
    """Derive immutable prose from one pinned artifact's exact label result."""

    if labels is None:
        return "This report-only module artifact embeds no label array."
    if labels == legacy_labels:
        return (
            "The entry-8 and entry-10 artifacts embed the legacy proxy array."
        )
    encoded = json.dumps(
        labels, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return f"The source artifact embeds the exact label array {encoded}."


def label_state_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize and consistency-check one evaluation block's label states."""

    require(bool(records), "label-state summary requires records")
    states = [record["label_state"] for record in records]
    ratified_arrays = {
        json.dumps(
            state["ratified_fitting_free_exact_label_array"], sort_keys=True
        )
        for state in states
    }
    require(
        len(ratified_arrays) == 1,
        "evaluation block has inconsistent ratified label arrays",
    )
    locators = {state["ratified_array_locator"] for state in states}
    require(
        len(locators) == 1,
        "evaluation block has inconsistent ratified-array locators",
    )
    claim_keys = (
        "ratified_array_activation_asserted_by_this_matrix",
        "population_alignment_claim",
        "individual_administrative_truth_claim",
    )
    claims = {tuple(state[key] for key in claim_keys) for state in states}
    require(
        len(claims) == 1,
        "evaluation block has inconsistent label activation claims",
    )
    displays = {state["matrix_display"] for state in states}
    require(
        len(displays) == 1,
        "evaluation block has inconsistent label displays",
    )

    embedded_counts = Counter(
        json.dumps(state["source_artifact_embedded_labels"], sort_keys=True)
        for state in states
        if state["source_artifact_embedded_labels"] is not None
    )
    embedded_arrays = [
        {
            "labels": json.loads(identity),
            "row_count": embedded_counts[identity],
        }
        for identity in sorted(embedded_counts)
    ]
    activation, population, individual = next(iter(claims))
    return {
        "embedded_arrays": embedded_arrays,
        "individual_administrative_truth_claim": individual,
        "matrix_display": next(iter(displays)),
        "no_array_count": sum(
            state["source_artifact_embedded_labels"] is None
            for state in states
        ),
        "population_alignment_claim": population,
        "ratified_array_activation_asserted_by_this_matrix": activation,
        "ratified_array_locator": next(iter(locators)),
        "ratified_fitting_free_exact_label_array": json.loads(
            next(iter(ratified_arrays))
        ),
    }


def embedded_label_arrays(value: Any) -> list[list[str]]:
    """Collect exact arrays stored under `labels` keys in one artifact."""

    arrays = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "labels" and is_label_array(child):
                arrays.append(child)
            arrays.extend(embedded_label_arrays(child))
    elif isinstance(value, list):
        for child in value:
            arrays.extend(embedded_label_arrays(child))
    return arrays


def validate_registered_label_evidence(
    records: list[dict[str, Any]],
    registry: dict[str, Any],
    root: Path = ROOT,
) -> None:
    """Bind one current evaluation's label claims to registered evidence."""

    summary = label_state_summary(records)
    honesty = registry["honesty_frame"]
    registered = registry["migration_context"]["wish_financing_stub"]["our"][
        "label_state"
    ]
    registered_expectations = {
        "individual_administrative_truth_claim": False,
        "matrix_display": MATRIX_DISPLAY,
        "population_alignment_claim": honesty["population_alignment_claim"],
        "ratified_array_activation_asserted_by_this_matrix": honesty[
            "ratified_array_activation_asserted_by_this_matrix"
        ],
        "ratified_array_locator": honesty["ratified_array_locator"],
        "ratified_fitting_free_exact_label_array": honesty[
            "ratified_fitting_free_exact_label_array"
        ],
    }
    require(
        all(
            registered[key] == expected
            for key, expected in registered_expectations.items()
        ),
        "registered label evidence disagrees with the honesty frame",
    )
    legacy_labels = registered["source_artifact_embedded_labels"]
    require(
        is_label_array(legacy_labels)
        and registered["source_artifact_label_note"]
        == evidence_bound_label_note(legacy_labels, legacy_labels),
        "registered source-artifact label note disagrees with its array",
    )
    evidence_messages = {
        "individual_administrative_truth_claim": (
            "individual-administrative-truth claim disagrees with registered "
            "evidence"
        ),
        "matrix_display": "label display disagrees with registered evidence",
        "population_alignment_claim": (
            "population-alignment claim disagrees with registered evidence"
        ),
        "ratified_array_activation_asserted_by_this_matrix": (
            "activation claim disagrees with registered evidence"
        ),
        "ratified_array_locator": (
            "ratified-array locator disagrees with registered evidence"
        ),
        "ratified_fitting_free_exact_label_array": (
            "ratified label array disagrees with registered evidence"
        ),
    }
    for key, message in evidence_messages.items():
        require(summary[key] == registered[key], message)

    root = root.resolve()
    entries_by_id = {entry["row_id"]: entry for entry in registry["entries"]}
    artifact_labels: dict[Path, list[str] | None] = {}
    for record in records:
        row_id = record["row_id"]
        pointer = entries_by_id[row_id]["our_side_artifact"][
            "artifact_pointer"
        ]
        relative_path = pointer["path"]
        path = (root / relative_path).resolve()
        require(
            path.is_relative_to(root),
            f"label-evidence path escapes repository: {row_id}",
        )
        if path not in artifact_labels:
            raw = path.read_bytes()
            require(
                sha256_bytes(raw) == pointer["sha256"],
                f"label-evidence artifact SHA drift: {row_id}",
            )
            arrays = embedded_label_arrays(json.loads(raw))
            identities = {
                json.dumps(array, sort_keys=True) for array in arrays
            }
            require(
                len(identities) <= 1,
                f"model-side artifact has ambiguous embedded label arrays: "
                f"{relative_path}",
            )
            artifact_labels[path] = (
                json.loads(next(iter(identities))) if identities else None
            )
        require(
            record["label_state"]["source_artifact_embedded_labels"]
            == artifact_labels[path],
            "source-artifact label claim disagrees with registered evidence: "
            f"{row_id}",
        )
        require(
            record["label_state"]["source_artifact_label_note"]
            == evidence_bound_label_note(artifact_labels[path], legacy_labels),
            "source-artifact label note disagrees with registered evidence: "
            f"{row_id}",
        )


def canonical_json_bytes(value: Any) -> bytes:
    """Render canonical pretty JSON used by registry.json."""

    return (
        json.dumps(
            value,
            sort_keys=True,
            indent=2,
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def canonical_jsonl_line(value: Any) -> bytes:
    """Render one compact, sorted, canonical JSONL object."""

    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def load_run_manifest(
    path: Path = RUN_MANIFEST_PATH,
) -> tuple[list[dict[str, Any]], bytes]:
    """Load the canonical append-only evaluation-artifact manifest."""

    raw = path.read_bytes()
    require(
        bool(raw) and raw.endswith(b"\n"),
        "run manifest must be nonempty and LF-terminated",
    )
    entries = []
    for line_number, line in enumerate(raw.splitlines(keepends=True), 1):
        require(
            line not in {b"\n", b"\r\n"}, f"blank manifest line {line_number}"
        )
        entry = json.loads(line)
        require(
            line == canonical_jsonl_line(entry),
            f"run manifest line {line_number} is not canonical sorted JSON",
        )
        entries.append(entry)
    validate_run_manifest(entries)
    return entries, raw


def validate_run_manifest(entries: list[dict[str, Any]]) -> None:
    """Validate run-manifest shape, order-independent identities, and paths."""

    require(bool(entries), "run manifest must contain at least one entry")
    run_shas = set()
    artifact_paths = set()
    for entry in entries:
        require(
            isinstance(entry, dict) and set(entry) == RUN_MANIFEST_KEYS,
            "run manifest entry keys have drifted",
        )
        run_sha = entry["evaluated_at_run"]
        artifact_path = entry["artifact_path"]
        require(is_sha256(run_sha), "invalid manifested evaluation run SHA")
        require(
            is_repo_relative_path(artifact_path),
            f"evaluation artifact path escapes or is not normalized: {artifact_path}",
        )
        require(
            run_sha not in run_shas, f"duplicate manifested run SHA: {run_sha}"
        )
        require(
            artifact_path not in artifact_paths,
            f"evaluation artifact path is reused: {artifact_path}",
        )
        run_shas.add(run_sha)
        artifact_paths.add(artifact_path)


def repo_relative_artifact_path(path: Path, root: Path = ROOT) -> str:
    """Normalize an existing caller path to a confined repository path."""

    root = root.resolve()
    resolved = path.resolve()
    require(
        resolved.is_relative_to(root),
        f"evaluation artifact path escapes repository: {path}",
    )
    relative = resolved.relative_to(root).as_posix()
    require(
        is_repo_relative_path(relative),
        f"evaluation artifact path is not normalized: {relative}",
    )
    return relative


def manifest_artifact_bytes(
    entry: dict[str, Any], root: Path = ROOT
) -> tuple[Path, str, bytes]:
    """Return one confined artifact's path, relative path, and hashed bytes."""

    validate_run_manifest([entry])
    root = root.resolve()
    relative = entry["artifact_path"]
    path = (root / relative).resolve()
    require(
        path.is_relative_to(root),
        f"evaluation artifact path escapes repository: {relative}",
    )
    require(
        path.is_file(), f"missing immutable evaluation artifact: {relative}"
    )
    require(
        sha256_bytes(raw := path.read_bytes()) == entry["evaluated_at_run"],
        f"immutable evaluation artifact SHA mismatch: {relative}",
    )
    return root, relative, raw


def literal_git_record(
    result: subprocess.CompletedProcess[bytes],
    relative: str,
    *,
    source: str,
) -> tuple[list[bytes], bytes]:
    """Parse exactly one NUL-delimited literal-path Git record."""

    missing_message = (
        f"immutable evaluation artifact is not committed at HEAD: {relative}"
        if source == "HEAD"
        else f"immutable evaluation artifact is not present in {source}: {relative}"
    )
    require(
        result.returncode == 0,
        missing_message,
    )
    records = result.stdout.split(b"\0")
    if records and records[-1] == b"":
        records.pop()
    require(
        len(records) == 1,
        (
            f"immutable evaluation artifact is not committed at HEAD as "
            f"exactly one literal path: {relative}"
            if source == "HEAD"
            else f"{source} must return exactly one immutable artifact path: "
            f"{relative}"
        ),
    )
    metadata, separator, returned_path = records[0].partition(b"\t")
    require(
        separator == b"\t" and returned_path == os.fsencode(relative),
        f"{source} returned a different immutable artifact path: {relative}",
    )
    return metadata.split(), returned_path


def require_git_blob_bytes(
    root: Path,
    object_id: bytes,
    raw: bytes,
    relative: str,
    *,
    source: str,
) -> None:
    """Require one selected Git blob to equal the artifact's worktree bytes."""

    try:
        object_name = object_id.decode("ascii")
    except UnicodeDecodeError:
        object_name = ""
    require(bool(object_name), f"invalid {source} blob ID: {relative}")
    blob = subprocess.run(
        ["git", "cat-file", "blob", object_name],
        cwd=root,
        check=False,
        capture_output=True,
    )
    require(
        blob.returncode == 0 and blob.stdout == raw,
        f"immutable evaluation artifact differs from {source}: {relative}",
    )


def validate_index_manifest_artifact(
    entry: dict[str, Any], root: Path = ROOT
) -> None:
    """Bind one append candidate's worktree bytes to its staged Git blob."""

    root, relative, raw = manifest_artifact_bytes(entry, root)
    tracked = subprocess.run(
        [
            "git",
            "--literal-pathspecs",
            "ls-files",
            "--stage",
            "-z",
            "--error-unmatch",
            "--",
            relative,
        ],
        cwd=root,
        check=False,
        capture_output=True,
    )
    if tracked.returncode != 0:
        raise AssertionError(
            "immutable evaluation artifact is not tracked in the Git index: "
            f"{relative}"
        )
    index_fields, _ = literal_git_record(tracked, relative, source="Git index")
    require(
        len(index_fields) == 3 and index_fields[2] == b"0",
        f"immutable evaluation artifact has an unresolved Git index state: {relative}",
    )
    require_git_blob_bytes(
        root,
        index_fields[1],
        raw,
        relative,
        source="Git index",
    )


def validate_manifest_artifact(
    entry: dict[str, Any], root: Path = ROOT, *, require_git: bool = True
) -> None:
    """Bind one manifested artifact to its committed blob at HEAD."""

    root, relative, raw = manifest_artifact_bytes(entry, root)
    if not require_git:
        return
    committed = subprocess.run(
        [
            "git",
            "--literal-pathspecs",
            "ls-tree",
            "--full-tree",
            "-z",
            "HEAD",
            "--",
            relative,
        ],
        cwd=root,
        check=False,
        capture_output=True,
    )
    head_fields, _ = literal_git_record(committed, relative, source="HEAD")
    require(
        len(head_fields) == 3 and head_fields[1] == b"blob",
        f"immutable evaluation artifact is not a blob at HEAD: {relative}",
    )
    require_git_blob_bytes(
        root,
        head_fields[2],
        raw,
        relative,
        source="HEAD",
    )


def validate_history_run_artifacts(
    records: list[dict[str, Any]],
    manifest: list[dict[str, Any]],
    root: Path = ROOT,
    *,
    require_git: bool = True,
) -> None:
    """Bind every history run SHA to one immutable repository artifact."""

    validate_history(records)
    validate_run_manifest(manifest)
    history_run_order = []
    seen = set()
    for record in records:
        run_sha = record["evaluated_at_run"]
        if run_sha not in seen:
            history_run_order.append(run_sha)
            seen.add(run_sha)
    manifest_run_order = [entry["evaluated_at_run"] for entry in manifest]
    require(
        manifest_run_order == history_run_order,
        "run manifest must match history run identities in first-occurrence order",
    )
    for entry in manifest:
        validate_manifest_artifact(entry, root, require_git=require_git)


def validate_seed_run_manifest(
    manifest: list[dict[str, Any]], registry: dict[str, Any]
) -> None:
    """Bind the first manifest entry to the registered seed evaluation."""

    seed = registry["seed_evaluation"]
    pointer = seed["artifact_pointer"]
    require(
        manifest[0]
        == {
            "artifact_path": pointer["path"],
            "evaluated_at_run": seed["evaluated_at_run"],
        }
        and pointer["sha256"] == seed["evaluated_at_run"],
        "seed evaluation and run manifest disagree",
    )


def resolve_json_pointer(document: Any, pointer: str) -> Any:
    """Resolve the registry's slash-rooted JSON pointer convention."""

    if pointer == "/":
        return document
    current = document
    for encoded_token in pointer[1:].split("/"):
        token = encoded_token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            current = current[int(token)]
        else:
            current = current[token]
    return current


def pinned_publisher_statuses(
    locator: dict[str, Any], row_id: str
) -> tuple[str, ...]:
    """Read closed publisher statuses from an accepted pinned extraction."""

    extraction = locator["committed_extraction"]
    relative_path = extraction["path"]
    root = ROOT.resolve()
    path = (root / relative_path).resolve()
    require(
        path.is_relative_to(root),
        f"publisher-status path escapes repository: {row_id}",
    )
    require(path.is_file(), f"missing publisher-status evidence: {row_id}")
    raw = path.read_bytes()
    require(
        sha256_bytes(raw) == extraction["sha256"],
        f"publisher-status evidence SHA drift: {row_id}",
    )
    observations = resolve_json_pointer(
        json.loads(raw), extraction["json_pointer"]
    )
    require(
        isinstance(observations, list) and observations,
        f"publisher-status evidence is not an observation array: {row_id}",
    )
    statuses = []
    for observation in observations:
        require(
            isinstance(observation, dict) and "source_status" in observation,
            f"publisher status marker is missing: {row_id}",
        )
        status = observation["source_status"]
        require(
            isinstance(status, str) and status in PUBLISHER_SOURCE_STATUSES,
            f"publisher status marker is invalid: {row_id}",
        )
        statuses.append(status)
    return tuple(statuses)


def validate_registry_artifacts(
    registry: dict[str, Any], root: Path = ROOT
) -> None:
    """Verify every committed pointer against confined repository bytes."""

    root = root.resolve()
    pointers = []
    for entry in registry["entries"]:
        pointers.append(entry["our_side_artifact"]["artifact_pointer"])
        pointers.extend(
            artifact
            for artifact in entry["source_pin"]["artifacts"]
            if artifact["pin_type"] == "committed_extraction"
        )
    pointers.extend(committed_json_pointers(registry["migration_context"]))

    parsed_documents: dict[Path, Any] = {}
    for pointer in pointers:
        relative_path = pointer["path"]
        require(
            is_repo_relative_json_path(relative_path),
            f"artifact path escapes or is not JSON: {relative_path}",
        )
        path = (root / relative_path).resolve()
        require(
            path.is_relative_to(root),
            f"artifact path escapes repository: {relative_path}",
        )
        require(path.is_file(), f"missing committed artifact: {relative_path}")
        raw = path.read_bytes()
        require(
            sha256_bytes(raw) == pointer["sha256"],
            f"committed artifact SHA drift: {relative_path}",
        )
        if path not in parsed_documents:
            parsed_documents[path] = json.loads(raw)
        try:
            resolve_json_pointer(
                parsed_documents[path], pointer["json_pointer"]
            )
        except (IndexError, KeyError, TypeError, ValueError) as error:
            raise AssertionError(
                f"unresolvable JSON pointer in {relative_path}: "
                f"{pointer['json_pointer']}"
            ) from error


def committed_json_pointers(value: Any) -> list[dict[str, str]]:
    """Collect exact committed-JSON pointers nested in migration metadata."""

    if isinstance(value, dict):
        pointers = []
        if set(value) == {"json_pointer", "path", "sha256"}:
            pointers.append(value)
        for child in value.values():
            pointers.extend(committed_json_pointers(child))
        return pointers
    if isinstance(value, list):
        pointers = []
        for child in value:
            pointers.extend(committed_json_pointers(child))
        return pointers
    return []


def load_registry(path: Path = REGISTRY_PATH) -> tuple[dict[str, Any], bytes]:
    """Load registry bytes while retaining their hash identity."""

    raw = path.read_bytes()
    registry = json.loads(raw)
    if raw != canonical_json_bytes(registry):
        raise AssertionError("registry.json is not canonical sorted JSON")
    validate_registry(registry)
    validate_registry_artifacts(registry)
    return registry, raw


def load_history(
    path: Path = HISTORY_PATH,
    *,
    require_git: bool = True,
) -> tuple[list[dict[str, Any]], bytes]:
    """Load and validate canonical history records in append order."""

    raw = path.read_bytes()
    if not raw or not raw.endswith(b"\n"):
        raise AssertionError(
            "history.jsonl must be nonempty and LF-terminated"
        )
    records = []
    offset = 0
    for line_number, line in enumerate(raw.splitlines(keepends=True), 1):
        if line in {b"\n", b"\r\n"}:
            raise AssertionError(f"blank history line {line_number}")
        record = json.loads(line)
        require(
            isinstance(record, dict) and set(record) == HISTORY_KEYS,
            f"history line {line_number} keys have drifted",
        )
        if line != canonical_jsonl_line(record):
            raise AssertionError(
                f"history line {line_number} is not canonical sorted JSON"
            )
        record["_byte_start"] = offset
        offset += len(line)
        record["_byte_end"] = offset
        records.append(record)
    validate_history(records)
    for record in records:
        del record["_byte_start"]
        del record["_byte_end"]
    if path.resolve() == HISTORY_PATH.resolve():
        manifest, _ = load_run_manifest()
        validate_history_run_artifacts(
            records, manifest, require_git=require_git
        )
        registry, _ = load_registry()
        validate_seed_run_manifest(manifest, registry)
    return records, raw


def validate_migration_context(
    context: dict[str, Any], registry: dict[str, Any]
) -> None:
    """Validate the exact metadata retained from the merged #352 matrix."""

    require(
        isinstance(context, dict)
        and set(context)
        == {
            "available_series_inventory",
            "certification_context",
            "honest_gaps",
            "reported_not_verified_partition",
            "source_matrix",
            "wish_financing_stub",
        },
        "migration context keys have drifted",
    )
    source = context["source_matrix"]
    require(
        source
        == {
            "canonicalization": registry["canonicalization"],
            "path_at_merge": "analysis/validation-matrix/matrix.json",
            "purpose": (
                "Frame-relative comparison of ratios, shares, trajectories, "
                "and orderings against published SSA, CBO, DYNASIM, and WISH "
                "statutory quantities; never national dollar levels"
            ),
            "schema_version": "cross_model_validation_matrix.v2",
            "sha256": LEGACY_MATRIX_SHA256,
        },
        "merged matrix identity has drifted",
    )
    inventory = context["available_series_inventory"]
    require(
        isinstance(inventory, dict)
        and set(inventory)
        == {
            "counts",
            "diagnostics",
            "entry10_comparisons",
            "projection",
            "source",
            "tables",
        },
        "available-series inventory has drifted",
    )
    certification = context["certification_context"]
    require(
        isinstance(certification, dict)
        and set(certification)
        == {"entry8_first_estimates", "m6", "ppi_gate1_generator"},
        "certification context keys have drifted",
    )
    noncertified = certification["m6"].get("not_certified")
    require(
        isinstance(noncertified, list)
        and len(noncertified) == 11
        and all(
            isinstance(item, dict)
            and set(item) == {"detail", "margin"}
            and isinstance(item["detail"], str)
            and item["detail"].strip()
            and isinstance(item["margin"], str)
            and item["margin"].strip()
            for item in noncertified
        )
        and len({item["margin"] for item in noncertified}) == 11,
        "certification context must retain eleven non-certified margins",
    )
    honest_gaps = context["honest_gaps"]
    require(
        isinstance(honest_gaps, list)
        and len(honest_gaps) == 8
        and all(is_one_sentence(item) for item in honest_gaps),
        "honest-gaps migration context has drifted",
    )
    partition = context["reported_not_verified_partition"]
    legacy_entries = legacy_registry_entries(registry)
    legacy_reported_ids = frozenset(
        entry["row_id"]
        for entry in legacy_entries
        if entry["verification_class"] == "reported_not_verified"
    )
    require(
        isinstance(partition, dict)
        and set(partition) == {"reason", "row_count"}
        and isinstance(partition["reason"], str)
        and partition["reason"].strip()
        and partition["row_count"]
        == sum(
            entry["verification_class"] == "reported_not_verified"
            for entry in legacy_entries
        ),
        "Mermin partition metadata has drifted",
    )
    require(
        legacy_reported_ids == LEGACY_MERMIN_ROW_IDS,
        "Mermin partition row IDs have drifted",
    )
    wish = context["wish_financing_stub"]
    require(
        isinstance(wish, dict)
        and set(wish)
        == {
            "concept_mismatch",
            "our",
            "published",
            "quantity",
            "source_needed",
            "status",
        }
        and wish["published"]["employee_rate_percent"] == 0.3
        and wish["published"]["employer_rate_percent"] == 0.3
        and wish["published"]["combined_wage_rate_percent"] == 0.6
        and wish["published"]["self_employment_rate_percent"] == 0.6,
        "WISH financing stub has drifted",
    )


def validate_registry(registry: dict[str, Any]) -> None:
    """Validate exact registry shape, enums, pins, and synchronized counts."""

    require(set(registry) == REGISTRY_KEYS, "registry keys have drifted")
    require(
        registry["schema_version"] == "standing_benchmark_registry.v4",
        "unsupported benchmark registry schema",
    )
    require(
        registry["allowed_comparison_scopes"] == list(COMPARISON_SCOPES),
        "comparison-scope enum has drifted",
    )
    require(set(registry["tiers"]) == set(TIERS), "tier enum has drifted")
    require(
        set(registry["gap_classes"]) == set(GAP_CLASSES),
        "gap-class enum has drifted",
    )
    require(
        all(
            isinstance(definition, dict)
            and set(definition) == {"closure_condition", "definition"}
            and isinstance(definition["closure_condition"], str)
            and definition["closure_condition"].strip()
            for definition in registry["gap_classes"].values()
        ),
        "every gap class needs a closure condition",
    )
    require(
        "never normative"
        in registry["tiers"]["model_triangulation"]["gap_law"],
        "model-triangulation gaps must remain nonnormative",
    )
    validate_migration_context(registry["migration_context"], registry)

    entries = registry["entries"]
    require(isinstance(entries, list) and entries, "registry needs entries")
    require(
        registry["row_count"] == len(entries),
        "registry row_count is not synchronized",
    )
    row_ids = [entry["row_id"] for entry in entries]
    require(len(row_ids) == len(set(row_ids)), "duplicate benchmark row_id")

    tier_counts = Counter()
    gap_counts = Counter()
    for entry in entries:
        validate_registry_entry(entry)
        tier_counts[entry["tier"]] += 1
        gap_counts[entry["gap_class"]] += 1

    reviewed_captures = {
        json.dumps(
            {
                "filename": capture["filename"],
                "pin_type": "sha_manifested_capture",
                "sha256": capture["sha256"],
                "size_bytes": capture["size_bytes"],
                "url": capture["url"],
            },
            sort_keys=True,
        )
        for capture in registry["external_capture_review"]["captures"].values()
    }
    registered_captures = {
        json.dumps(artifact, sort_keys=True)
        for entry in entries
        for artifact in entry["source_pin"]["artifacts"]
        if artifact["pin_type"] == "sha_manifested_capture"
    }
    require(
        registered_captures <= reviewed_captures,
        "source capture is absent from the reviewed external manifest",
    )

    require(
        registry["tier_counts"] == {tier: tier_counts[tier] for tier in TIERS},
        "registry tier_counts are not synchronized",
    )
    require(
        registry["gap_class_counts"]
        == {gap_class: gap_counts[gap_class] for gap_class in GAP_CLASSES},
        "registry gap_class_counts are not synchronized",
    )


def validate_registry_entry(entry: dict[str, Any]) -> None:
    """Validate one append-mostly benchmark specification."""

    require(set(entry) == ENTRY_KEYS, "benchmark entry keys have drifted")
    row_id = entry["row_id"]
    require(isinstance(row_id, str) and row_id.strip(), "missing row_id")
    require(
        isinstance(entry["quantity"], str) and entry["quantity"].strip(),
        f"missing quantity: {row_id}",
    )
    require(entry["tier"] in TIERS, f"invalid tier: {row_id}")
    require(
        entry["gap_class"] in GAP_CLASSES,
        f"invalid gap class: {row_id}",
    )
    require(
        entry["gap_class"] != "unexplained",
        f"unexplained benchmark gap: {row_id}",
    )
    require(
        is_one_sentence(entry["gap_note"]),
        f"gap note must be one sentence: {row_id}",
    )
    require(
        isinstance(entry["gap_closure_condition"], str)
        and entry["gap_closure_condition"].strip(),
        f"missing gap closure condition: {row_id}",
    )
    require(
        entry["verification_class"] in {"verified", "reported_not_verified"},
        f"invalid verification class: {row_id}",
    )
    require(
        entry["verification_class"] != "reported_not_verified"
        or entry["gap_class"] == "unverified_source",
        f"reported-not-verified row must use unverified_source: {row_id}",
    )
    require(
        entry["gap_class"] != "unverified_source"
        or entry["verification_class"] == "reported_not_verified",
        f"unverified_source row must be reported-not-verified: {row_id}",
    )
    require(
        isinstance(entry["comparison_scope"], list)
        and entry["comparison_scope"],
        f"missing comparison scope: {row_id}",
    )
    require(
        len(entry["comparison_scope"]) == len(set(entry["comparison_scope"])),
        f"duplicate comparison scope: {row_id}",
    )
    require(
        set(entry["comparison_scope"]) <= set(COMPARISON_SCOPES),
        f"invalid comparison scope: {row_id}",
    )
    legacy_scope = entry["legacy_comparison_scope"]
    require(
        isinstance(legacy_scope, list)
        and legacy_scope
        and len(legacy_scope) == len(set(legacy_scope))
        and set(legacy_scope) <= set(LEGACY_COMPARISON_SCOPES),
        f"invalid legacy comparison scope: {row_id}",
    )
    normalized_legacy_scope = []
    for scope in legacy_scope:
        if scope in {"distributional_incidence", "distributional_share"}:
            continue
        normalized = "trajectory" if scope == "age_trajectory" else scope
        if normalized not in normalized_legacy_scope:
            normalized_legacy_scope.append(normalized)
    require(
        normalized_legacy_scope == entry["comparison_scope"],
        f"legacy and normalized comparison scopes disagree: {row_id}",
    )

    published_metadata = entry["published_metadata"]
    require(
        isinstance(published_metadata, dict)
        and set(published_metadata)
        <= {
            "underlying_published_values_withheld_from_comparison",
            "legislative_status",
            "companion_parameters",
        },
        f"invalid published metadata: {row_id}",
    )
    if row_id == "cbo.taxable_payroll.trajectory_2015_100":
        require(
            set(published_metadata)
            == {"underlying_published_values_withheld_from_comparison"},
            f"missing CBO withheld-values safeguard: {row_id}",
        )
    elif row_id == "wish.hr4289.employee_rate.share_of_payroll":
        require(
            set(published_metadata)
            == {"companion_parameters", "legislative_status"},
            f"missing WISH published metadata: {row_id}",
        )
        companion = published_metadata["companion_parameters"]
        require(
            companion
            == {
                "combined_employee_employer_rate_percent": 0.6,
                "combined_rate_print_status": (
                    "derived as 0.3 + 0.3; not separately printed"
                ),
                "self_employment_rate_percent": 0.6,
                "separate_employer_rate_percent": 0.3,
            },
            f"WISH companion parameters have drifted: {row_id}",
        )
    else:
        require(
            not published_metadata,
            f"unexpected row-specific published metadata: {row_id}",
        )

    our_side = entry["our_side_artifact"]
    require(
        isinstance(our_side, dict)
        and isinstance(our_side.get("unit"), str)
        and our_side["unit"].strip(),
        f"invalid our-side artifact spec: {row_id}",
    )
    our_pointer = our_side["artifact_pointer"]
    require(
        set(our_pointer) == {"json_pointer", "path", "sha256"},
        f"invalid our-side artifact pointer: {row_id}",
    )
    require(
        is_sha256(our_pointer["sha256"]), f"invalid artifact SHA: {row_id}"
    )
    require(
        is_repo_relative_json_path(our_pointer["path"]),
        f"our-side artifact must be JSON: {row_id}",
    )
    require(
        is_json_pointer(our_pointer["json_pointer"]),
        f"invalid our-side JSON pointer: {row_id}",
    )

    source_pin = entry["source_pin"]
    require(
        set(source_pin)
        == {"artifacts", "exact_locators", "reported_value_provenance"},
        f"invalid source pin: {row_id}",
    )
    require(source_pin["artifacts"], f"missing source artifact: {row_id}")
    require(source_pin["exact_locators"], f"missing exact locator: {row_id}")
    artifact_identities = set()
    for artifact in source_pin["artifacts"]:
        require(
            artifact["pin_type"]
            in {"committed_extraction", "sha_manifested_capture"},
            f"invalid source pin type: {row_id}",
        )
        require(is_sha256(artifact["sha256"]), f"invalid source SHA: {row_id}")
        if artifact["pin_type"] == "committed_extraction":
            require(
                set(artifact)
                == {"json_pointer", "path", "pin_type", "sha256"},
                f"invalid committed extraction shape: {row_id}",
            )
            require(
                is_repo_relative_json_path(artifact["path"]),
                f"invalid extraction path: {row_id}",
            )
            require(
                is_json_pointer(artifact["json_pointer"]),
                f"invalid extraction JSON pointer: {row_id}",
            )
        else:
            require(
                set(artifact)
                == {"filename", "pin_type", "sha256", "size_bytes", "url"},
                f"invalid external capture shape: {row_id}",
            )
            require(
                bool(artifact["filename"]), f"missing capture file: {row_id}"
            )
            require(bool(artifact["url"]), f"missing capture URL: {row_id}")
            require(
                artifact["size_bytes"] > 0, f"empty source capture: {row_id}"
            )
        artifact_identities.add(json.dumps(artifact, sort_keys=True))
    require(
        len(artifact_identities) == len(source_pin["artifacts"]),
        f"duplicate source artifact: {row_id}",
    )

    locators = source_pin["exact_locators"]
    require(
        len({json.dumps(locator, sort_keys=True) for locator in locators})
        == len(locators),
        f"duplicate exact locator: {row_id}",
    )
    coordinate_families = (
        {"column_header_path", "row_locator"},
        {"observation_range", "sheet"},
        {"column_path", "row_path"},
        {"provision", "section"},
    )
    used_artifacts = set()
    for locator in locators:
        require(
            bool(locator["document"]), f"missing source document: {row_id}"
        )
        require(bool(locator.get("page")), f"missing source page: {row_id}")
        require(bool(locator["table"]), f"missing source table: {row_id}")
        matched_families = [
            family
            for family in coordinate_families
            if family <= set(locator)
            and all(bool(locator[field]) for field in family)
        ]
        require(
            len(matched_families) == 1,
            f"locator needs one exact coordinate family: {row_id}",
        )

    if entry["verification_class"] == "verified":
        require(
            source_pin["reported_value_provenance"] is None,
            f"verified row cannot retain reported provenance: {row_id}",
        )
        for locator in locators:
            accepted = {
                "committed_extraction",
                "reviewed_external_capture",
            } & set(locator)
            require(
                len(accepted) == 1,
                f"verified locator needs one accepted source: {row_id}",
            )
            require(
                "capture_status" not in locator
                and "unmanifested_corroborating_copy" not in locator,
                f"verified locator cannot retain provisional markers: {row_id}",
            )
            if "committed_extraction" in locator:
                normalized = {
                    "pin_type": "committed_extraction",
                    **locator["committed_extraction"],
                }
            else:
                normalized = {
                    "pin_type": "sha_manifested_capture",
                    **locator["reviewed_external_capture"],
                }
            identity = json.dumps(normalized, sort_keys=True)
            require(
                identity in artifact_identities,
                f"locator source is absent from source artifacts: {row_id}",
            )
            used_artifacts.add(identity)
    else:
        provenance = source_pin["reported_value_provenance"]
        require(
            isinstance(provenance, dict)
            and set(provenance)
            == {
                "classification",
                "numeric_source",
                "numeric_source_note",
                "publisher_capture_status",
            }
            and provenance["classification"] == "reported_not_verified",
            f"unverified provenance class mismatch: {row_id}",
        )
        require(
            isinstance(provenance["numeric_source_note"], str)
            and provenance["numeric_source_note"].strip()
            and isinstance(provenance["publisher_capture_status"], str)
            and provenance["publisher_capture_status"].strip(),
            f"unverified provenance needs source evidence: {row_id}",
        )
        numeric_source = provenance["numeric_source"]
        require(
            set(numeric_source) == {"json_pointer", "path", "sha256"},
            f"invalid reported numeric source: {row_id}",
        )
        normalized_numeric_source = {
            "pin_type": "committed_extraction",
            **numeric_source,
        }
        numeric_identity = json.dumps(
            normalized_numeric_source, sort_keys=True
        )
        require(
            numeric_identity in artifact_identities,
            f"reported numeric source is absent from source artifacts: {row_id}",
        )
        used_artifacts.add(numeric_identity)
        for locator in locators:
            require(
                not {
                    "committed_extraction",
                    "reviewed_external_capture",
                }
                & set(locator),
                f"unverified locator cannot name an accepted source: {row_id}",
            )
            require(
                isinstance(locator.get("capture_status"), str)
                and locator["capture_status"].strip(),
                f"unverified locator needs capture status: {row_id}",
            )
            if row_id in LEGACY_MERMIN_ROW_IDS:
                require(
                    "missing after REFRESH" in locator["capture_status"],
                    f"Mermin locator needs refresh capture status: {row_id}",
                )
                require(
                    "unmanifested_corroborating_copy" in locator,
                    f"Mermin locator needs corroboration metadata: {row_id}",
                )
            if "unmanifested_corroborating_copy" in locator:
                corroboration = locator["unmanifested_corroborating_copy"]
                require(
                    set(corroboration)
                    == {
                        "accepted_as_verified_source",
                        "manifested",
                        "scope",
                        "sha256",
                    }
                    and is_sha256(corroboration["sha256"]),
                    f"invalid unmanifested corroboration: {row_id}",
                )
                require(
                    corroboration["manifested"] is False,
                    f"unverified corroboration cannot be manifested: {row_id}",
                )
                require(
                    corroboration["accepted_as_verified_source"] is False,
                    f"corroboration cannot verify source: {row_id}",
                )

    require(
        used_artifacts == artifact_identities,
        f"source artifacts and exact locators are not one-to-one: {row_id}",
    )
    if entry["gap_class"] == "preliminary_source":
        publisher_statuses = tuple(
            status
            for locator in locators
            if "committed_extraction" in locator
            for status in pinned_publisher_statuses(locator, row_id)
        )
        require(
            entry["verification_class"] == "verified"
            and "preliminary" in publisher_statuses,
            "preliminary_source requires accepted pinned publisher data "
            f"with structured preliminary status: {row_id}",
        )

    revisions = entry["spec_revisions"]
    require(isinstance(revisions, list), f"invalid spec revisions: {row_id}")
    for expected_revision, revision in enumerate(revisions, 1):
        require(
            set(revision) == REVISION_KEYS, f"invalid revision keys: {row_id}"
        )
        require(
            revision["revision"] == expected_revision,
            f"nonsequential spec revision: {row_id}",
        )
        require(
            is_one_sentence(revision["note"]),
            f"revision note must be one sentence: {row_id}",
        )
        require(
            isinstance(revision["changed_fields"], list)
            and revision["changed_fields"]
            and len(revision["changed_fields"])
            == len(set(revision["changed_fields"]))
            and all(
                isinstance(field, str)
                and field.startswith("/")
                and field not in {"/row_id", "/spec_revisions"}
                and not field.startswith("/spec_revisions/")
                for field in revision["changed_fields"]
            ),
            f"invalid changed_fields: {row_id}",
        )


def escaped_pointer_token(value: Any) -> str:
    """Encode one mapping key or list index as a JSON Pointer token."""

    return str(value).replace("~", "~0").replace("/", "~1")


def json_diff_paths(old: Any, new: Any, path: str = "") -> set[str]:
    """Return the precise JSON Pointer leaves that differ."""

    if type(old) is not type(new):
        return {path or "/"}
    if isinstance(old, dict):
        differences = set()
        for key in set(old) | set(new):
            child = f"{path}/{escaped_pointer_token(key)}"
            if key not in old or key not in new:
                differences.add(child)
            else:
                differences |= json_diff_paths(old[key], new[key], child)
        return differences
    if isinstance(old, list):
        differences = set()
        for index in range(max(len(old), len(new))):
            child = f"{path}/{index}"
            if index >= len(old) or index >= len(new):
                differences.add(child)
            else:
                differences |= json_diff_paths(old[index], new[index], child)
        return differences
    return set() if old == new else {path or "/"}


def validate_append_mostly_registry(
    previous: dict[str, Any], current: dict[str, Any]
) -> None:
    """Enforce row order and revision notes across registry generations."""

    if (
        previous.get("schema_version") == "standing_benchmark_registry.v1"
        and current.get("schema_version") == "standing_benchmark_registry.v2"
    ):
        validate_registry(current)
        legacy_projection = deepcopy(current)
        legacy_projection.pop("migration_context")
        legacy_projection["schema_version"] = "standing_benchmark_registry.v1"
        for entry in legacy_projection["entries"]:
            entry.pop("legacy_comparison_scope")
            entry.pop("published_metadata")
        require(
            legacy_projection == previous,
            "v1-to-v2 migration changed pre-existing registry fields",
        )
        return

    if (
        previous.get("schema_version") == "standing_benchmark_registry.v2"
        and current.get("schema_version") == "standing_benchmark_registry.v3"
    ):
        validate_registry(current)
        legacy_projection = deepcopy(current)
        legacy_projection["schema_version"] = "standing_benchmark_registry.v2"
        legacy_projection["gap_classes"].pop("unverified_source")
        legacy_projection["gap_classes"]["preliminary_source"] = {
            "closure_condition": (
                "Closes when a final, provenance-pinned publisher source "
                "verifies the exact registered locator."
            ),
            "definition": (
                "The published value is preliminary or lacks an accepted "
                "publisher-controlled capture."
            ),
        }
        legacy_projection["gap_class_counts"].pop("unverified_source")
        legacy_projection["gap_class_counts"]["preliminary_source"] = 20
        for entry in legacy_projection["entries"]:
            if entry["verification_class"] == "reported_not_verified":
                entry["gap_class"] = "preliminary_source"
                entry["gap_closure_condition"] = legacy_projection[
                    "gap_classes"
                ]["preliminary_source"]["closure_condition"]
        require(
            legacy_projection == previous,
            "v2-to-v3 migration changed fields outside the source taxonomy",
        )
        return

    if (
        previous.get("schema_version") == "standing_benchmark_registry.v3"
        and current.get("schema_version") == "standing_benchmark_registry.v4"
    ):
        validate_registry(current)
        legacy_projection = deepcopy(current)
        legacy_projection["schema_version"] = "standing_benchmark_registry.v3"
        legacy_projection["tiers"]["admin_truth"][
            "gap_law"
        ] = "Gaps are errors expected to shrink over certified runs."
        legacy_projection["gap_classes"]["module_missing"][
            "closure_condition"
        ] = "Closes when a certified artifact supplies the missing modeled module and comparable output."
        for entry in legacy_projection["entries"]:
            if entry["gap_class"] == "module_missing":
                entry["gap_closure_condition"] = legacy_projection[
                    "gap_classes"
                ]["module_missing"]["closure_condition"]
        require(
            legacy_projection == previous,
            "v3-to-v4 migration changed fields outside artifact terminology",
        )
        return

    validate_registry(previous)
    previous_entries = previous["entries"]
    current_entries = current.get("entries")
    if isinstance(current_entries, list) and all(
        isinstance(entry, dict) and "row_id" in entry
        for entry in current_entries
    ):
        previous_ids = [entry["row_id"] for entry in previous_entries]
        current_ids = [entry["row_id"] for entry in current_entries]
        require(
            current_ids[: len(previous_ids)] == previous_ids,
            "existing benchmark rows cannot be removed, reordered, or renamed",
        )
    validate_registry(current)
    for key in IMMUTABLE_REGISTRY_KEYS:
        require(
            current[key] == previous[key],
            f"immutable registry law changed without a schema migration: {key}",
        )
    current_entries = current["entries"]
    previous_ids = [entry["row_id"] for entry in previous_entries]
    current_ids = [entry["row_id"] for entry in current_entries]
    require(
        current_ids[: len(previous_ids)] == previous_ids,
        "existing benchmark rows cannot be removed, reordered, or renamed",
    )
    for old, new in zip(previous_entries, current_entries, strict=False):
        old_revisions = old["spec_revisions"]
        new_revisions = new["spec_revisions"]
        require(
            new_revisions[: len(old_revisions)] == old_revisions,
            f"spec revision history was rewritten: {old['row_id']}",
        )
        old_spec = {
            key: value for key, value in old.items() if key != "spec_revisions"
        }
        new_spec = {
            key: value for key, value in new.items() if key != "spec_revisions"
        }
        actual_changes = json_diff_paths(old_spec, new_spec)
        if not actual_changes:
            require(
                new_revisions == old_revisions,
                f"revision note without a spec change: {old['row_id']}",
            )
            continue
        require(
            len(new_revisions) == len(old_revisions) + 1,
            f"changed spec needs one appended revision note: {old['row_id']}",
        )
        declared_changes = new_revisions[-1]["changed_fields"]
        for actual in actual_changes:
            require(
                any(
                    actual == declared or actual.startswith(f"{declared}/")
                    for declared in declared_changes
                ),
                f"spec revision omits a changed field: {old['row_id']}",
            )
        for declared in declared_changes:
            require(
                any(
                    actual == declared or actual.startswith(f"{declared}/")
                    for actual in actual_changes
                ),
                f"spec revision names an unchanged field: {old['row_id']}",
            )
    for entry in current_entries[len(previous_entries) :]:
        require(
            entry["spec_revisions"] == [],
            f"new benchmark row must start without revisions: {entry['row_id']}",
        )


def validate_history(records: list[dict[str, Any]]) -> None:
    """Validate record sets and enforce the unexplained-gap alarm."""

    require(bool(records), "history must contain at least one record")
    sets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    run_registry_shas: dict[str, set[str]] = defaultdict(set)
    seen_row_runs = set()
    for record in records:
        record_keys = set(record) if isinstance(record, dict) else set()
        require(
            record_keys == HISTORY_KEYS
            or record_keys == HISTORY_KEYS | HISTORY_OFFSET_KEYS,
            "history record keys have drifted",
        )
        if record_keys == HISTORY_KEYS | HISTORY_OFFSET_KEYS:
            require(
                type(record["_byte_start"]) is int
                and type(record["_byte_end"]) is int
                and 0 <= record["_byte_start"] < record["_byte_end"],
                "invalid history byte offsets",
            )
        require(
            is_sha256(record["evaluated_at_run"]), "invalid evaluation run SHA"
        )
        require(
            is_sha256(record["registry_sha"]), "invalid history registry SHA"
        )
        require(
            isinstance(record["row_id"], str) and record["row_id"],
            "history record is missing row_id",
        )
        row_id = record["row_id"]
        require(
            record["gap_class"] in GAP_CLASSES, f"invalid gap class: {row_id}"
        )
        require(
            record["gap_class"] != "unexplained",
            f"unexplained benchmark gap: {row_id}",
        )
        require(
            isinstance(record["gap_note"], str) and record["gap_note"].strip(),
            f"missing gap note: {row_id}",
        )
        require(
            is_one_sentence(record["gap_note"]),
            f"gap note must be one sentence: {row_id}",
        )
        require(
            set(record["our"]) == {"unit", "value"}
            and isinstance(record["our"]["unit"], str)
            and record["our"]["unit"].strip()
            and is_measurement_value(record["our"]["value"]),
            f"invalid our value: {row_id}",
        )
        require(
            set(record["published"]) == {"unit", "value"}
            and isinstance(record["published"]["unit"], str)
            and record["published"]["unit"].strip()
            and is_measurement_value(record["published"]["value"]),
            f"invalid published value: {row_id}",
        )
        require(
            isinstance(record["deviation"], dict)
            and record["deviation"]
            and any_numeric_leaf(record["deviation"]),
            f"missing deviation: {row_id}",
        )
        require(
            isinstance(record["label_state"], dict)
            and set(record["label_state"]) == LABEL_STATE_KEYS,
            f"invalid label state: {row_id}",
        )
        label_state = record["label_state"]
        require(
            all(
                isinstance(label_state[key], bool)
                for key in (
                    "individual_administrative_truth_claim",
                    "population_alignment_claim",
                    "ratified_array_activation_asserted_by_this_matrix",
                )
            )
            and isinstance(label_state["matrix_display"], str)
            and label_state["matrix_display"].strip()
            and isinstance(label_state["ratified_array_locator"], str)
            and label_state["ratified_array_locator"].strip()
            and is_label_array(
                label_state["ratified_fitting_free_exact_label_array"]
            )
            and (
                label_state["source_artifact_embedded_labels"] is None
                or is_label_array(
                    label_state["source_artifact_embedded_labels"]
                )
            )
            and isinstance(label_state["source_artifact_label_note"], str)
            and label_state["source_artifact_label_note"].strip(),
            f"invalid honest-label fields: {row_id}",
        )

        row_run = (record["row_id"], record["evaluated_at_run"])
        require(
            row_run not in seen_row_runs,
            "row/run SHA reused; any deviation movement without a new run SHA "
            "is a drift finding",
        )
        seen_row_runs.add(row_run)
        sets[(record["evaluated_at_run"], record["registry_sha"])].append(
            record
        )
        run_registry_shas[record["evaluated_at_run"]].add(
            record["registry_sha"]
        )

    require(
        all(len(shas) == 1 for shas in run_registry_shas.values()),
        "one run SHA cannot be reused against multiple registries",
    )

    for record_set in sets.values():
        label_state_summary(record_set)
        offset_states = [
            "_byte_start" in record and "_byte_end" in record
            for record in record_set
        ]
        require(
            all(offset_states) or not any(offset_states),
            "history byte offsets must be present for every record or none",
        )
        if not any(offset_states):
            continue
        byte_starts = [record["_byte_start"] for record in record_set]
        byte_ends = [record["_byte_end"] for record in record_set]
        require(
            max(byte_ends) - min(byte_starts)
            == sum(
                end - start
                for start, end in zip(byte_starts, byte_ends, strict=True)
            ),
            "each evaluation record set must be contiguous",
        )


def validate_history_against_registry(
    records: list[dict[str, Any]],
    registry: dict[str, Any],
    registry_sha: str,
) -> None:
    """Check each historical block against the append-mostly row prefix."""

    validate_history(records)
    validate_registry(registry)
    row_order = [entry["row_id"] for entry in registry["entries"]]
    entries_by_id = {entry["row_id"]: entry for entry in registry["entries"]}
    record_sets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(
        list
    )
    for record in records:
        record_sets[
            (record["evaluated_at_run"], record["registry_sha"])
        ].append(record)
    for (_, set_registry_sha), record_set in record_sets.items():
        record_ids = [record["row_id"] for record in record_set]
        require(
            record_ids == row_order[: len(record_ids)],
            "evaluation record set must follow a complete registry prefix",
        )
        if set_registry_sha == registry_sha:
            require(
                record_ids == row_order,
                "current-registry evaluation must contain every active row",
            )
            for record in record_set:
                entry = entries_by_id[record["row_id"]]
                require(
                    record["gap_class"] == entry["gap_class"],
                    f"history gap class disagrees with registry: {record['row_id']}",
                )
                require(
                    record["gap_note"] == entry["gap_note"],
                    f"history gap note disagrees with registry: {record['row_id']}",
                )
            validate_registered_label_evidence(record_set, registry)


def reconstruct_legacy_matrix(
    registry: dict[str, Any], seed_records: list[dict[str, Any]]
) -> dict[str, Any]:
    """Reconstruct the merged #352 matrix from standing-harness artifacts."""

    validate_registry(registry)
    legacy_entries = legacy_registry_entries(registry)
    legacy_seed_records = seed_records[: len(LEGACY_ROW_IDS)]
    require(
        tuple(record.get("row_id") for record in legacy_seed_records)
        == LEGACY_ROW_IDS,
        "legacy reconstruction needs the exact frozen seed row prefix",
    )
    seed_by_id = {record["row_id"]: record for record in legacy_seed_records}
    require(
        len(seed_by_id) == len(legacy_seed_records),
        "legacy reconstruction received duplicate seed rows",
    )

    reconstructed_rows = []
    for entry in legacy_entries:
        row_id = entry["row_id"]
        require(row_id in seed_by_id, f"legacy seed row is missing: {row_id}")
        record = seed_by_id[row_id]
        our = {
            "label_state": deepcopy(record["label_state"]),
            "source": deepcopy(entry["our_side_artifact"]["artifact_pointer"]),
            "unit": record["our"]["unit"],
            "value": deepcopy(record["our"]["value"]),
        }
        formula = entry["our_side_artifact"].get("formula")
        if formula is not None:
            our["formula"] = formula
        for key in ("comparison_note", "provenance_status"):
            if key in entry["our_side_artifact"]:
                our[key] = entry["our_side_artifact"][key]

        published = {
            "source_locators": deepcopy(entry["source_pin"]["exact_locators"]),
            "unit": record["published"]["unit"],
            "value": deepcopy(record["published"]["value"]),
        }
        if entry["published_formula"] is not None:
            published["formula"] = entry["published_formula"]
        provenance = entry["source_pin"]["reported_value_provenance"]
        if provenance is not None:
            published["provenance"] = deepcopy(provenance)
        published.update(deepcopy(entry["published_metadata"]))

        reconstructed_rows.append(
            {
                "comparison_scope": deepcopy(entry["legacy_comparison_scope"]),
                "concept_mismatch": deepcopy(entry["concept_mismatch"]),
                "deviation": deepcopy(record["deviation"]),
                "evidential_status": entry["evidential_status"],
                "external_model": entry["external_reference"],
                "our": our,
                "published": published,
                "quantity": entry["quantity"],
                "row_id": row_id,
                "verification_class": entry["verification_class"],
            }
        )

    verified = [
        row
        for row in reconstructed_rows
        if row["verification_class"] == "verified"
    ]
    reported = [
        row
        for row in reconstructed_rows
        if row["verification_class"] == "reported_not_verified"
    ]
    context = registry["migration_context"]
    source = context["source_matrix"]
    partition = context["reported_not_verified_partition"]
    return {
        "available_series_inventory": deepcopy(
            context["available_series_inventory"]
        ),
        "blocked_comparisons": deepcopy(registry["deferred_comparisons"]),
        "canonicalization": source["canonicalization"],
        "certification_context": deepcopy(context["certification_context"]),
        "external_capture_review": deepcopy(
            registry["external_capture_review"]
        ),
        "honest_gaps": deepcopy(context["honest_gaps"]),
        "honesty_frame": deepcopy(registry["honesty_frame"]),
        "inputs": deepcopy(registry["inputs"]),
        "purpose": source["purpose"],
        "reported_not_verified": {
            "reason": partition["reason"],
            "row_count": partition["row_count"],
            "rows": reported,
        },
        "row_count": len(verified),
        "rows": verified,
        "schema_version": source["schema_version"],
        "total_row_count": len(reconstructed_rows),
        "wish_financing_stub": deepcopy(context["wish_financing_stub"]),
    }


def validate_append_only_history(
    previous_raw: bytes, current_raw: bytes
) -> None:
    """Reject every rewrite, reorder, or truncation of committed history."""

    if current_raw.startswith(previous_raw):
        return
    migration = (sha256_bytes(previous_raw), sha256_bytes(current_raw))
    require(
        migration in HISTORY_SEED_MIGRATIONS,
        "history is append-only; prior committed bytes must remain a prefix",
    )


def validate_append_only_run_manifest(
    previous_raw: bytes, current_raw: bytes
) -> None:
    """Reject every rewrite, reorder, or truncation of the run manifest."""

    require(
        current_raw.startswith(previous_raw),
        "run manifest is append-only; prior committed bytes must remain a prefix",
    )


def latest_records(
    records: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Return the last appended record for each row."""

    latest = {}
    for record in records:
        latest[record["row_id"]] = record
    return latest
