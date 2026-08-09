#!/usr/bin/env python3
"""Build the Amendment-12 tier-2 admission-rule targeted sweeps.

This builder starts from a fresh, in-memory reconstruction of all 81 pinned
source documents and the operative Amendment-13/14 execution template.  It
emits one nonauthority corpus-certification artifact only after all six
successor-era seals exist as committed, byte-exact files.  It emits no
catalog authority, certification, Q5 input, or production output.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_amendment12_rq_catalog_pilot as a12  # noqa: E402
import validate_amendment13_execution_law as a13  # noqa: E402

DEFAULT_OUTPUT_ROOT = (
    ROOT
    / "docs"
    / "analysis"
    / "amendment_12_rq_catalog_tier2"
    / "targeted_sweeps"
)
DEFAULT_SUCCESSOR_SEAL_ROOT = (
    ROOT
    / "docs"
    / "analysis"
    / "amendment_12_rq_catalog_tier2"
    / "amendment_13_successor_era_seals_v1"
)
OUTPUT_FILENAME = "admission_rule_targeted_sweeps_v1.json"

SCHEMA_VERSION = "amendment_12_tier2_admission_rule_targeted_sweeps.v1"
ARTIFACT_ID_PREFIX = "a12-tier2-targeted-sweeps:"
AUTHORITY_KIND = "amendment_12_tier_2_targeted_sweeps_nonauthority"
STATUS = "pass_corpus_exhaustive_targeted_sweeps_nonauthority"
CANONICALIZATION = a12.CANONICALIZATION

PAIRWISE_APPROVAL_DECISIONS = frozenset(
    {
        "approved_pairwise_decomposition",
        "approved_pairwise_typed_projection",
    }
)
ALIAS_APPROVAL_DECISIONS = frozenset(
    {
        "approved_single_pair",
        *PAIRWISE_APPROVAL_DECISIONS,
    }
)
ALL_LEDGER_DECISIONS = ALIAS_APPROVAL_DECISIONS | {"disclosed_stop"}

TOP_LEVEL_KEYS = frozenset(
    {
        "schema_version",
        "artifact_id",
        "authority_kind",
        "tier",
        "status",
        "source_rebuild",
        "successor_seal_bindings",
        "successor_seal_binding_count",
        "successor_seal_binding_domain_sha256",
        "document_positions_swept",
        "document_count",
        "document_position_domain_sha256",
        "lifecycle",
        "continuation_admission_rule_sweep",
        "pairwise_decomposition_admission_rule_sweep",
        "semantic_ledger_alias_gate_sweep",
        "unexplained_targeted_hit_count",
        "integrity",
    }
)
LIFECYCLE = {
    "nonauthority": True,
    "authority_emitted": False,
    "certification_emitted": False,
    "q5_input_emitted": False,
    "production_output_emitted": False,
}


class SweepError(RuntimeError):
    """Raised when a tier-2 targeted-sweep invariant fails closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SweepError(message)


def _require_exact_keys(
    value: Mapping[str, Any], expected: frozenset[str], label: str
) -> None:
    actual = frozenset(value)
    _require(
        actual == expected,
        f"{label}: keyset drift; missing={sorted(expected - actual)!r}, "
        f"extra={sorted(actual - expected)!r}",
    )


def canonical_bytes(value: Any) -> bytes:
    """Return strict, compact, sorted ASCII JSON with one terminal LF."""
    return a12.canonical_bytes(value)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _domain_sha(rows: Sequence[Any]) -> str:
    return _sha256(canonical_bytes(list(rows)))


def _keyset_sha(ids: Sequence[str]) -> str:
    return _sha256(canonical_bytes(list(ids)))


def _portable_path(path: Path, fallback_root: Path) -> str:
    resolved = path.resolve()
    if resolved.is_relative_to(ROOT):
        return resolved.relative_to(ROOT).as_posix()
    return resolved.relative_to(fallback_root.resolve()).as_posix()


def _git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "--no-replace-objects", *args],
        cwd=ROOT,
        check=check,
        capture_output=True,
        text=True,
    )


def _first_add_commit(path: Path) -> str:
    _require(
        path.resolve().is_relative_to(ROOT),
        f"committed seal path is outside repository: {path}",
    )
    relative = path.resolve().relative_to(ROOT).as_posix()
    tracked = _git("ls-files", "--error-unmatch", "--", relative, check=False)
    _require(
        tracked.returncode == 0, f"successor seal is not committed: {relative}"
    )
    history = _git(
        "log",
        "--diff-filter=A",
        "--format=%H",
        "--reverse",
        "--",
        relative,
    ).stdout.splitlines()
    _require(
        len(history) == 1,
        f"successor seal first-add is not unique: {relative}",
    )
    commit = history[0]
    _require(
        len(commit) == 40
        and all(character in "0123456789abcdef" for character in commit),
        f"invalid successor seal first-add commit: {relative}",
    )
    reachable = _git(
        "merge-base", "--is-ancestor", commit, "HEAD", check=False
    )
    _require(
        reachable.returncode == 0,
        f"successor seal first-add is not reachable from HEAD: {relative}",
    )
    return commit


def _require_strict_ancestor(
    ancestor: str, descendant: str, label: str
) -> None:
    _require(ancestor != descendant, f"{label}: commits are not strict")
    result = _git(
        "merge-base", "--is-ancestor", ancestor, descendant, check=False
    )
    _require(result.returncode == 0, f"{label}: ancestry check failed")


def _source_rebuild(
    source_root: Path | None,
) -> tuple[list[a12.NormalizedDocument], dict[str, dict[str, Any]]]:
    """Rebuild and validate all eight A12 artifacts without reading outputs."""
    reader = a12.SourceReader(source_root)
    documents, source_identity = a12._load_documents(reader)
    bundle = a12._build_bundle(
        documents,
        source_identity,
        a12._validate_design_prefix(),
    )
    a12.validate_bundle(bundle)
    _require(
        [document.position for document in documents] == list(range(1, 82)),
        "fresh source rebuild did not cover all 81 documents",
    )
    return documents, bundle


def _source_rebuild_identity(
    documents: Sequence[a12.NormalizedDocument],
    bundle: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    artifact_rows = []
    for role in a12.OUTPUT_FILENAMES:
        artifact = bundle[role]
        raw = canonical_bytes(artifact)
        artifact_rows.append(
            {
                "artifact_role": role,
                "schema_version": artifact["schema_version"],
                "artifact_id": artifact["artifact_id"],
                "canonical_byte_size": len(raw),
                "canonical_sha256": _sha256(raw),
                "payload_sha256": artifact["integrity"]["payload_sha256"],
            }
        )
    positions = [document.position for document in documents]
    return {
        "fresh_in_memory_rebuild": True,
        "committed_tier1_artifacts_used_as_expected_evidence": False,
        "source_commit": a12.SOURCE_COMMIT,
        "document_count": len(documents),
        "document_positions": positions,
        "document_position_domain_sha256": _domain_sha(positions),
        "rebuilt_bundle_artifact_rows": artifact_rows,
        "rebuilt_bundle_artifact_count": len(artifact_rows),
        "rebuilt_bundle_artifact_domain_sha256": _domain_sha(artifact_rows),
    }


def _load_successor_seal_bindings(
    execution_law: Mapping[str, Any],
    seal_root: Path,
    *,
    verify_git: bool,
) -> list[dict[str, Any]]:
    expected_rows = execution_law["successor_era_seal_rows"]
    _require(
        len(expected_rows) == 6, "operative law does not have six era seals"
    )
    expected_paths = [
        seal_root
        / f"era_{row['era_order_position']:02d}_successor_seal_v1.json"
        for row in expected_rows
    ]
    _require(
        seal_root.is_dir(),
        f"successor seal directory does not exist: {seal_root}",
    )
    actual_json_paths = sorted(seal_root.glob("*.json"))
    _require(
        actual_json_paths == expected_paths,
        "successor seal directory must contain exactly the six enacted paths",
    )

    bindings: list[dict[str, Any]] = []
    for expected, path in zip(expected_rows, expected_paths, strict=True):
        raw = path.read_bytes()
        value = a12.strict_json_loads(raw, str(path))
        _require(
            isinstance(value, dict), f"successor seal is not an object: {path}"
        )
        _require(
            raw == canonical_bytes(value),
            f"noncanonical successor seal: {path}",
        )
        _require(
            value == expected,
            f"successor seal differs from operative law: {path}",
        )
        first_add_commit = _first_add_commit(path) if verify_git else None
        bindings.append(
            {
                "era_order_position": expected["era_order_position"],
                "era_id": expected["era_id"],
                "path": _portable_path(path, seal_root),
                "byte_size": len(raw),
                "raw_sha256": _sha256(raw),
                "successor_era_seal_id": expected["successor_era_seal_id"],
                "first_add_commit": first_add_commit,
            }
        )
    return bindings


def _continuation_rows(
    ledger_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in ledger_rows:
        citation = row["continuation_composition_citation"]
        if citation is None:
            continue
        rows.append(
            {
                "document_source_position": row["document_source_position"],
                "predecessor_evidence_id": row["source_local_evidence_id"],
                "semantic_alias_evidence_adjudication_id": row[
                    "semantic_alias_evidence_adjudication_id"
                ],
                "leading_occurrence_id": citation["leading_occurrence_id"],
                "continuation_occurrence_id": citation[
                    "continuation_occurrence_id"
                ],
                "round_five_continuation_restoration": row[
                    "round_five_continuation_restoration"
                ],
                "continuation_composition_citation": copy.deepcopy(citation),
            }
        )
    return rows


def _build_continuation_sweep(
    ledger_rows: Sequence[Mapping[str, Any]], execution_law: Mapping[str, Any]
) -> dict[str, Any]:
    a12_rows = _continuation_rows(ledger_rows)
    projection = [
        [
            row["document_source_position"],
            row["predecessor_evidence_id"],
            row["leading_occurrence_id"],
            row["continuation_occurrence_id"],
        ]
        for row in a12_rows
    ]
    enacted_projection = execution_law["amendment12_continuation_domain"][
        "continuation_projection_rows"
    ]
    _require(
        projection == enacted_projection,
        "fresh A12 continuation citations differ from the operative projection",
    )

    disclosures = copy.deepcopy(
        execution_law["incomplete_fragment_terminal_successor_rows"]
    )
    compositions = copy.deepcopy(
        execution_law["composed_fragment_successor_rows"]
    )
    fragment_specs = list(a13.FRAGMENT_SPECS)
    spec_ids = [row[1] for row in fragment_specs]
    successors = [*disclosures, *compositions]
    _require(
        [row["predecessor_row_id"] for row in successors] == spec_ids,
        "operative fragment successor order differs from enacted source specs",
    )
    new_instruction_ids = [row[2] for row in fragment_specs]
    a12_evidence_ids = [row["predecessor_evidence_id"] for row in a12_rows]
    a12_instruction_ids = [
        row["continuation_occurrence_id"] for row in a12_rows
    ]
    predecessor_disjoint = not set(a12_evidence_ids) & set(spec_ids)
    instruction_disjoint = not set(a12_instruction_ids) & set(
        new_instruction_ids
    )
    _require(predecessor_disjoint, "A12 and A13 predecessor domains overlap")
    _require(instruction_disjoint, "A12 and A13 instruction domains overlap")

    targeted_count = len(a12_rows) + len(disclosures) + len(compositions)
    return {
        "rule_name": "a12_continuation",
        "document_positions_scanned": list(range(1, 82)),
        "document_count": 81,
        "a12_continuation_citation_rows": a12_rows,
        "a12_continuation_citation_count": len(a12_rows),
        "a12_continuation_citation_keyset_sha256": _keyset_sha(
            [
                row["semantic_alias_evidence_adjudication_id"]
                for row in a12_rows
            ]
        ),
        "a12_continuation_citation_domain_sha256": _domain_sha(a12_rows),
        "a13_terminal_disclosure_successor_rows": disclosures,
        "a13_terminal_disclosure_successor_count": len(disclosures),
        "a13_terminal_disclosure_successor_keyset_sha256": _keyset_sha(
            [row["successor_row_id"] for row in disclosures]
        ),
        "a13_terminal_disclosure_successor_domain_sha256": _domain_sha(
            disclosures
        ),
        "a13_exact_g75_composition_successor_rows": compositions,
        "a13_exact_g75_composition_successor_count": len(compositions),
        "a13_exact_g75_composition_successor_keyset_sha256": _keyset_sha(
            [row["successor_row_id"] for row in compositions]
        ),
        "a13_exact_g75_composition_successor_domain_sha256": _domain_sha(
            compositions
        ),
        "a13_new_fragment_instruction_occurrence_ids": new_instruction_ids,
        "a13_new_fragment_instruction_domain_sha256": _domain_sha(
            new_instruction_ids
        ),
        "predecessor_domains_disjoint": predecessor_disjoint,
        "instruction_domains_disjoint": instruction_disjoint,
        "targeted_hit_count": targeted_count,
        "adjudicated_hit_count": targeted_count,
        "unexplained_targeted_hit_rows": [],
        "unexplained_targeted_hit_count": 0,
        "status": "pass_a12_continuation_and_a13_fragment_dispositions",
    }


def _is_pairwise_candidate(row: Mapping[str, Any]) -> bool:
    return (
        row["decision"] in PAIRWISE_APPROVAL_DECISIONS
        or row["composite_stop_citation"] is not None
    )


def _build_pairwise_sweep(
    ledger_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    candidates = [
        copy.deepcopy(row)
        for row in ledger_rows
        if _is_pairwise_candidate(row)
    ]
    approved_pair_rows = [
        copy.deepcopy(pair)
        for row in candidates
        if row["decision"] in PAIRWISE_APPROVAL_DECISIONS
        for pair in row["approved_pair_rows"]
    ]
    typed_rows = [
        row
        for row in approved_pair_rows
        if row["pair_kind"] == "typed_instruction_import_projection"
    ]
    stop_rows = [
        row for row in candidates if row["composite_stop_citation"] is not None
    ]
    _require(
        all(
            row["decision"] == "disclosed_stop"
            and row["approved_pair_count"] == 0
            and row["approved_pair_rows"] == []
            for row in stop_rows
        ),
        "composite STOP candidate was not terminally adjudicated",
    )
    _require(
        all(
            row["typed_projection_union_prohibited"] is True
            and row["class_closure_eligible"] is False
            and row["composite_typed_projection_pair_id"] is not None
            for row in typed_rows
        ),
        "typed projection admitted an occurrence union",
    )
    candidate_ids = [
        row["semantic_alias_evidence_adjudication_id"] for row in candidates
    ]
    _require(
        len(candidate_ids) == len(set(candidate_ids)),
        "duplicate pairwise candidate",
    )
    return {
        "rule_name": "pairwise_decomposition",
        "document_positions_scanned": list(range(1, 82)),
        "document_count": 81,
        "candidate_adjudication_rows": candidates,
        "candidate_adjudication_count": len(candidates),
        "candidate_adjudication_keyset_sha256": _keyset_sha(candidate_ids),
        "candidate_adjudication_domain_sha256": _domain_sha(candidates),
        "candidate_decision_counts": dict(
            sorted(Counter(row["decision"] for row in candidates).items())
        ),
        "approved_pair_rows": approved_pair_rows,
        "approved_pair_count": len(approved_pair_rows),
        "approved_pair_keyset_sha256": _keyset_sha(
            [
                row["semantic_alias_pair_adjudication_id"]
                for row in approved_pair_rows
            ]
        ),
        "approved_pair_domain_sha256": _domain_sha(approved_pair_rows),
        "typed_projection_pair_count": len(typed_rows),
        "typed_projection_pair_domain_sha256": _domain_sha(typed_rows),
        "composite_stop_adjudication_count": len(stop_rows),
        "composite_stop_adjudication_domain_sha256": _domain_sha(stop_rows),
        "every_candidate_adjudicated": True,
        "occurrence_union_constructed": False,
        "occurrence_union_rows": [],
        "unexplained_targeted_hit_rows": [],
        "unexplained_targeted_hit_count": 0,
        "status": "pass_pairwise_decomposition_without_occurrence_union",
    }


def _structural_filter_projection_rows(
    structural_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "document_source_position": row["document_source_position"],
            "source_instruction_occurrence_id": row[
                "source_instruction_occurrence_id"
            ],
            "source_local_evidence_ids": copy.deepcopy(
                row["source_local_evidence_ids"]
            ),
            "structural_candidate_satisfied": row[
                "structural_candidate_satisfied"
            ],
            "semantic_alias_ledger_member": row[
                "semantic_alias_ledger_member"
            ],
            "semantic_alias_adjudication_id": row[
                "semantic_alias_adjudication_id"
            ],
            "valid_alias_arm_evidence_ids": copy.deepcopy(
                row["valid_alias_arm_evidence_ids"]
            ),
            "rejected_source_local_evidence_ids": copy.deepcopy(
                row["rejected_source_local_evidence_ids"]
            ),
            "repeat_coverage_disposition": row["repeat_coverage_disposition"],
        }
        for row in structural_rows
    ]


def _build_semantic_gate_sweep(
    sweep: Mapping[str, Any], execution_law: Mapping[str, Any]
) -> dict[str, Any]:
    ledger_rows = copy.deepcopy(
        sweep["alias_evidence_semantic_adjudication_rows"]
    )
    ledger_ids = [
        row["semantic_alias_evidence_adjudication_id"] for row in ledger_rows
    ]
    _require(
        len(ledger_ids) == len(set(ledger_ids)),
        "duplicate semantic-ledger row",
    )
    _require(
        {row["decision"] for row in ledger_rows} <= ALL_LEDGER_DECISIONS,
        "unknown semantic-ledger decision",
    )
    approved_evidence_ids = [
        row["source_local_evidence_id"]
        for row in ledger_rows
        if row["decision"] in ALIAS_APPROVAL_DECISIONS
    ]
    _require(
        len(approved_evidence_ids) == len(set(approved_evidence_ids)),
        "duplicate approved alias evidence",
    )
    approved_set = set(approved_evidence_ids)

    structural_rows = _structural_filter_projection_rows(
        sweep["in_domain_component_cross_reference_sweep_rows"]
    )
    structural_alias_ids = sorted(
        {
            evidence_id
            for row in structural_rows
            for evidence_id in row["valid_alias_arm_evidence_ids"]
        }
    )
    structural_only = sorted(set(structural_alias_ids) - approved_set)
    _require(
        not structural_only,
        "structural predicate admitted alias evidence absent from semantic ledger",
    )
    _require(
        all(
            not row["valid_alias_arm_evidence_ids"]
            or row["semantic_alias_ledger_member"] is True
            for row in structural_rows
        ),
        "structural predicate bypassed the semantic ledger",
    )

    repaired_rows = copy.deepcopy(
        [
            *execution_law[
                "semantically_incompatible_local_proof_successor_rows"
            ],
            *execution_law["incomplete_fragment_terminal_successor_rows"],
            *execution_law["composed_fragment_successor_rows"],
        ]
    )
    _require(
        all(
            row["successor_payload"]["alias_admitted"] is False
            and row["successor_payload"]["occurrence_equivalence_admitted"]
            is False
            and row["successor_payload"]["repeat_coverage_arm_admitted"]
            is False
            for row in repaired_rows
        ),
        "repaired proof/fragment successor admitted an alias or coverage arm",
    )
    repaired_predecessor_ids = [
        row["predecessor_row_id"] for row in repaired_rows
    ]
    law_gap_ids = copy.deepcopy(
        execution_law["untouched_law_gap_predecessor_ids"]
    )
    _require(
        not set(repaired_predecessor_ids) & set(law_gap_ids),
        "untouched law gap appeared in repaired successor domain",
    )
    _require(
        not set(law_gap_ids) & set(approved_evidence_ids),
        "untouched law gap appeared in alias-admission domain",
    )

    return {
        "rule_name": "semantic_ledger_alias_gate",
        "document_positions_scanned": list(range(1, 82)),
        "document_count": 81,
        "semantic_ledger_adjudication_rows": ledger_rows,
        "semantic_ledger_adjudication_count": len(ledger_rows),
        "semantic_ledger_adjudication_keyset_sha256": _keyset_sha(ledger_ids),
        "semantic_ledger_adjudication_domain_sha256": _domain_sha(ledger_rows),
        "semantic_ledger_decision_counts": dict(
            sorted(Counter(row["decision"] for row in ledger_rows).items())
        ),
        "semantic_approved_alias_evidence_ids": approved_evidence_ids,
        "semantic_approved_alias_evidence_count": len(approved_evidence_ids),
        "semantic_approved_alias_evidence_domain_sha256": _domain_sha(
            approved_evidence_ids
        ),
        "structural_filter_projection_rows": structural_rows,
        "structural_filter_projection_count": len(structural_rows),
        "structural_filter_projection_domain_sha256": _domain_sha(
            structural_rows
        ),
        "structural_valid_alias_evidence_ids": structural_alias_ids,
        "structural_valid_alias_evidence_count": len(structural_alias_ids),
        "structural_valid_alias_evidence_domain_sha256": _domain_sha(
            structural_alias_ids
        ),
        "alias_admissions_from_semantic_ledger_only": True,
        "structural_predicates_filter_only": True,
        "structural_only_alias_admission_rows": structural_only,
        "structural_only_alias_admission_count": len(structural_only),
        "repaired_nonalias_successor_rows": repaired_rows,
        "repaired_nonalias_successor_count": len(repaired_rows),
        "repaired_nonalias_successor_keyset_sha256": _keyset_sha(
            [row["successor_row_id"] for row in repaired_rows]
        ),
        "repaired_nonalias_successor_domain_sha256": _domain_sha(
            repaired_rows
        ),
        "untouched_law_gap_predecessor_ids": law_gap_ids,
        "untouched_law_gap_predecessor_count": len(law_gap_ids),
        "untouched_law_gap_predecessor_domain_sha256": _domain_sha(
            law_gap_ids
        ),
        "repaired_and_law_gap_domains_disjoint": True,
        "unexplained_targeted_hit_rows": [],
        "unexplained_targeted_hit_count": 0,
        "status": "pass_semantic_ledger_sole_alias_gate",
    }


def _artifact(payload: Mapping[str, Any]) -> dict[str, Any]:
    body = copy.deepcopy(dict(payload))
    digest = _sha256(canonical_bytes(body))
    return {
        **body,
        "artifact_id": ARTIFACT_ID_PREFIX + digest,
        "integrity": {
            "canonicalization": CANONICALIZATION,
            "payload_sha256": digest,
        },
    }


def build_artifact(
    *,
    source_root: Path | None = None,
    seal_root: Path = DEFAULT_SUCCESSOR_SEAL_ROOT,
    verify_git: bool = True,
) -> dict[str, Any]:
    """Build one source-derived, ratification-bound targeted-sweep object."""
    documents, bundle = _source_rebuild(source_root)
    execution_law = a13.build_ratification_bound_execution_template()
    sweep = bundle["sweeps"]
    ledger_rows = sweep["alias_evidence_semantic_adjudication_rows"]
    seal_bindings = _load_successor_seal_bindings(
        execution_law, seal_root, verify_git=verify_git
    )
    document_positions = [document.position for document in documents]
    continuation = _build_continuation_sweep(ledger_rows, execution_law)
    pairwise = _build_pairwise_sweep(ledger_rows)
    semantic = _build_semantic_gate_sweep(sweep, execution_law)
    unexplained_count = sum(
        value["unexplained_targeted_hit_count"]
        for value in (continuation, pairwise, semantic)
    )
    artifact = _artifact(
        {
            "schema_version": SCHEMA_VERSION,
            "authority_kind": AUTHORITY_KIND,
            "tier": 2,
            "status": STATUS,
            "source_rebuild": _source_rebuild_identity(documents, bundle),
            "successor_seal_bindings": seal_bindings,
            "successor_seal_binding_count": len(seal_bindings),
            "successor_seal_binding_domain_sha256": _domain_sha(seal_bindings),
            "document_positions_swept": document_positions,
            "document_count": len(document_positions),
            "document_position_domain_sha256": _domain_sha(document_positions),
            "lifecycle": copy.deepcopy(LIFECYCLE),
            "continuation_admission_rule_sweep": continuation,
            "pairwise_decomposition_admission_rule_sweep": pairwise,
            "semantic_ledger_alias_gate_sweep": semantic,
            "unexplained_targeted_hit_count": unexplained_count,
        }
    )
    validate_artifact(artifact)
    return artifact


def _validate_count_and_domain(
    value: Mapping[str, Any], rows_key: str, count_key: str, digest_key: str
) -> list[Any]:
    rows = value[rows_key]
    _require(isinstance(rows, list), f"{rows_key} is not an array")
    _require(value[count_key] == len(rows), f"{rows_key} count drift")
    _require(
        value[digest_key] == _domain_sha(rows), f"{rows_key} digest drift"
    )
    return rows


def validate_artifact(artifact: Mapping[str, Any]) -> None:
    """Validate the artifact envelope and all three admission-rule sweeps."""
    _require_exact_keys(artifact, TOP_LEVEL_KEYS, "targeted-sweep artifact")
    _require(artifact["schema_version"] == SCHEMA_VERSION, "schema drift")
    _require(
        artifact["authority_kind"] == AUTHORITY_KIND, "authority kind drift"
    )
    _require(artifact["tier"] == 2, "tier drift")
    _require(artifact["status"] == STATUS, "status drift")
    _require(artifact["lifecycle"] == LIFECYCLE, "lifecycle authority drift")
    positions = artifact["document_positions_swept"]
    _require(
        positions == list(range(1, 82)), "document sweep is not exact 1..81"
    )
    _require(
        artifact["document_count"] == len(positions) == 81,
        "document count drift",
    )
    _require(
        artifact["document_position_domain_sha256"] == _domain_sha(positions),
        "document position digest drift",
    )

    integrity = artifact["integrity"]
    _require_exact_keys(
        integrity,
        frozenset({"canonicalization", "payload_sha256"}),
        "artifact integrity",
    )
    payload = {
        key: copy.deepcopy(value)
        for key, value in artifact.items()
        if key not in {"artifact_id", "integrity"}
    }
    digest = _sha256(canonical_bytes(payload))
    _require(
        integrity["canonicalization"] == CANONICALIZATION,
        "canonicalization drift",
    )
    _require(
        integrity["payload_sha256"] == digest, "artifact payload digest drift"
    )
    _require(
        artifact["artifact_id"] == ARTIFACT_ID_PREFIX + digest,
        "artifact ID drift",
    )

    source = artifact["source_rebuild"]
    _require(
        source["fresh_in_memory_rebuild"] is True,
        "source was not freshly rebuilt",
    )
    _require(
        source["committed_tier1_artifacts_used_as_expected_evidence"] is False,
        "tier-1 output was promoted to expected evidence",
    )
    _require(
        source["document_positions"] == positions, "source position drift"
    )
    _require(source["document_count"] == 81, "source document count drift")
    _require(
        source["document_position_domain_sha256"] == _domain_sha(positions),
        "source document digest drift",
    )
    rebuilt_rows = source["rebuilt_bundle_artifact_rows"]
    _require(
        source["rebuilt_bundle_artifact_count"] == len(rebuilt_rows),
        "bundle count drift",
    )
    _require(
        source["rebuilt_bundle_artifact_domain_sha256"]
        == _domain_sha(rebuilt_rows),
        "bundle identity domain drift",
    )

    seals = artifact["successor_seal_bindings"]
    _require(
        artifact["successor_seal_binding_count"] == len(seals) == 6,
        "seal count drift",
    )
    _require(
        artifact["successor_seal_binding_domain_sha256"] == _domain_sha(seals),
        "seal binding digest drift",
    )
    _require(
        [row["era_order_position"] for row in seals] == list(range(1, 7)),
        "successor seal order drift",
    )
    _require(
        len({row["successor_era_seal_id"] for row in seals}) == 6,
        "duplicate successor seal identity",
    )

    named_sweeps = (
        (
            artifact["continuation_admission_rule_sweep"],
            "a12_continuation",
        ),
        (
            artifact["pairwise_decomposition_admission_rule_sweep"],
            "pairwise_decomposition",
        ),
        (
            artifact["semantic_ledger_alias_gate_sweep"],
            "semantic_ledger_alias_gate",
        ),
    )
    for named_sweep, rule_name in named_sweeps:
        _require(
            named_sweep["rule_name"] == rule_name,
            f"{rule_name}: rule-name drift",
        )
        _require(
            named_sweep["document_positions_scanned"] == positions
            and named_sweep["document_count"] == 81,
            f"{rule_name}: incomplete document scan",
        )

    continuation = artifact["continuation_admission_rule_sweep"]
    _require(
        continuation["status"]
        == "pass_a12_continuation_and_a13_fragment_dispositions",
        "continuation sweep status drift",
    )
    a12_rows = _validate_count_and_domain(
        continuation,
        "a12_continuation_citation_rows",
        "a12_continuation_citation_count",
        "a12_continuation_citation_domain_sha256",
    )
    disclosures = _validate_count_and_domain(
        continuation,
        "a13_terminal_disclosure_successor_rows",
        "a13_terminal_disclosure_successor_count",
        "a13_terminal_disclosure_successor_domain_sha256",
    )
    compositions = _validate_count_and_domain(
        continuation,
        "a13_exact_g75_composition_successor_rows",
        "a13_exact_g75_composition_successor_count",
        "a13_exact_g75_composition_successor_domain_sha256",
    )
    _require(
        len(a12_rows) == 5
        and len(disclosures) == 8
        and len(compositions) == 2,
        "continuation/fragment census drift",
    )
    _require(
        continuation["a12_continuation_citation_keyset_sha256"]
        == _keyset_sha(
            [
                row["semantic_alias_evidence_adjudication_id"]
                for row in a12_rows
            ]
        ),
        "A12 continuation citation keyset drift",
    )
    _require(
        continuation["a13_terminal_disclosure_successor_keyset_sha256"]
        == _keyset_sha([row["successor_row_id"] for row in disclosures]),
        "terminal disclosure successor keyset drift",
    )
    _require(
        continuation["a13_exact_g75_composition_successor_keyset_sha256"]
        == _keyset_sha([row["successor_row_id"] for row in compositions]),
        "G75 composition successor keyset drift",
    )
    new_instruction_ids = continuation[
        "a13_new_fragment_instruction_occurrence_ids"
    ]
    _require(
        continuation["a13_new_fragment_instruction_domain_sha256"]
        == _domain_sha(new_instruction_ids)
        and len(new_instruction_ids) == len(disclosures) + len(compositions),
        "new-fragment instruction domain drift",
    )
    _require(
        continuation["predecessor_domains_disjoint"] is True
        and continuation["instruction_domains_disjoint"] is True,
        "A12/A13 continuation disjointness drift",
    )
    _require(
        continuation["targeted_hit_count"]
        == continuation["adjudicated_hit_count"]
        == len(a12_rows) + len(disclosures) + len(compositions),
        "continuation targeted-hit coverage drift",
    )
    _require(
        continuation["unexplained_targeted_hit_rows"] == []
        and continuation["unexplained_targeted_hit_count"] == 0,
        "unexplained continuation hit",
    )
    _require(
        all(
            row["successor_payload"]["alias_admitted"] is False
            and row["successor_payload"]["occurrence_equivalence_admitted"]
            is False
            and row["successor_payload"]["repeat_coverage_arm_admitted"]
            is False
            for row in [*disclosures, *compositions]
        ),
        "fragment successor admitted alias authority",
    )

    pairwise = artifact["pairwise_decomposition_admission_rule_sweep"]
    _require(
        pairwise["status"]
        == "pass_pairwise_decomposition_without_occurrence_union",
        "pairwise sweep status drift",
    )
    candidates = _validate_count_and_domain(
        pairwise,
        "candidate_adjudication_rows",
        "candidate_adjudication_count",
        "candidate_adjudication_domain_sha256",
    )
    pairs = _validate_count_and_domain(
        pairwise,
        "approved_pair_rows",
        "approved_pair_count",
        "approved_pair_domain_sha256",
    )
    expected_pairs = [
        pair
        for row in candidates
        if row["decision"] in PAIRWISE_APPROVAL_DECISIONS
        for pair in row["approved_pair_rows"]
    ]
    _require(
        pairs == expected_pairs,
        "approved pair rows were not preserved exactly",
    )
    candidate_ids = [
        row["semantic_alias_evidence_adjudication_id"] for row in candidates
    ]
    _require(
        pairwise["candidate_adjudication_keyset_sha256"]
        == _keyset_sha(candidate_ids),
        "pairwise candidate keyset drift",
    )
    _require(
        pairwise["candidate_decision_counts"]
        == dict(
            sorted(Counter(row["decision"] for row in candidates).items())
        ),
        "pairwise decision census drift",
    )
    _require(
        pairwise["approved_pair_keyset_sha256"]
        == _keyset_sha(
            [row["semantic_alias_pair_adjudication_id"] for row in pairs]
        ),
        "approved pair keyset drift",
    )
    _require(
        all(_is_pairwise_candidate(row) for row in candidates),
        "noncandidate in pairwise sweep",
    )
    _require(
        pairwise["every_candidate_adjudicated"] is True,
        "pairwise candidate unadjudicated",
    )
    typed_rows = [
        row
        for row in pairs
        if row["pair_kind"] == "typed_instruction_import_projection"
    ]
    _require(
        pairwise["typed_projection_pair_count"] == len(typed_rows)
        and pairwise["typed_projection_pair_domain_sha256"]
        == _domain_sha(typed_rows),
        "typed projection domain drift",
    )
    _require(
        all(
            row["typed_projection_union_prohibited"] is True
            and row["class_closure_eligible"] is False
            for row in typed_rows
        ),
        "typed projection occurrence union admitted",
    )
    stop_rows = [
        row for row in candidates if row["composite_stop_citation"] is not None
    ]
    _require(
        pairwise["composite_stop_adjudication_count"] == len(stop_rows)
        and pairwise["composite_stop_adjudication_domain_sha256"]
        == _domain_sha(stop_rows),
        "composite STOP domain drift",
    )
    _require(
        pairwise["occurrence_union_constructed"] is False
        and pairwise["occurrence_union_rows"] == [],
        "occurrence union constructed",
    )
    _require(
        pairwise["unexplained_targeted_hit_rows"] == []
        and pairwise["unexplained_targeted_hit_count"] == 0,
        "unexplained pairwise hit",
    )

    semantic = artifact["semantic_ledger_alias_gate_sweep"]
    _require(
        semantic["status"] == "pass_semantic_ledger_sole_alias_gate",
        "semantic-ledger sweep status drift",
    )
    ledger_rows = _validate_count_and_domain(
        semantic,
        "semantic_ledger_adjudication_rows",
        "semantic_ledger_adjudication_count",
        "semantic_ledger_adjudication_domain_sha256",
    )
    _require(
        len(ledger_rows) == 265,
        "semantic ledger does not contain all adjudications",
    )
    ledger_ids = [
        row["semantic_alias_evidence_adjudication_id"] for row in ledger_rows
    ]
    _require(
        semantic["semantic_ledger_adjudication_keyset_sha256"]
        == _keyset_sha(ledger_ids),
        "semantic-ledger keyset drift",
    )
    _require(
        semantic["semantic_ledger_decision_counts"]
        == dict(
            sorted(Counter(row["decision"] for row in ledger_rows).items())
        ),
        "semantic-ledger decision census drift",
    )
    approved_ids = [
        row["source_local_evidence_id"]
        for row in ledger_rows
        if row["decision"] in ALIAS_APPROVAL_DECISIONS
    ]
    _require(
        semantic["semantic_approved_alias_evidence_ids"] == approved_ids
        and semantic["semantic_approved_alias_evidence_count"]
        == len(approved_ids)
        and semantic["semantic_approved_alias_evidence_domain_sha256"]
        == _domain_sha(approved_ids),
        "semantic-approved alias evidence drift",
    )
    structural = _validate_count_and_domain(
        semantic,
        "structural_filter_projection_rows",
        "structural_filter_projection_count",
        "structural_filter_projection_domain_sha256",
    )
    structural_ids = sorted(
        {
            evidence_id
            for row in structural
            for evidence_id in row["valid_alias_arm_evidence_ids"]
        }
    )
    _require(
        semantic["structural_valid_alias_evidence_ids"] == structural_ids
        and semantic["structural_valid_alias_evidence_count"]
        == len(structural_ids)
        and semantic["structural_valid_alias_evidence_domain_sha256"]
        == _domain_sha(structural_ids),
        "structural filter evidence domain drift",
    )
    _require(
        set(structural_ids) <= set(approved_ids),
        "structural-only alias admission",
    )
    _require(
        semantic["alias_admissions_from_semantic_ledger_only"] is True
        and semantic["structural_predicates_filter_only"] is True
        and semantic["structural_only_alias_admission_rows"] == []
        and semantic["structural_only_alias_admission_count"] == 0,
        "semantic ledger is not the sole alias gate",
    )
    repaired = _validate_count_and_domain(
        semantic,
        "repaired_nonalias_successor_rows",
        "repaired_nonalias_successor_count",
        "repaired_nonalias_successor_domain_sha256",
    )
    _require(
        len(repaired) == 38, "proof/fragment repaired nonalias census drift"
    )
    _require(
        semantic["repaired_nonalias_successor_keyset_sha256"]
        == _keyset_sha([row["successor_row_id"] for row in repaired]),
        "repaired nonalias successor keyset drift",
    )
    _require(
        repaired[28:36] == disclosures and repaired[36:] == compositions,
        "repaired fragment successors differ between admission sweeps",
    )
    _require(
        all(
            row["successor_kind"] == "semantically_incompatible_local_proof"
            and row["successor_payload"]["terminal_status"]
            == a13.PROOF_TERMINAL_STATUS
            for row in repaired[:28]
        )
        and all(
            row["successor_kind"] == "incomplete_fragment_terminal_disclosure"
            and row["successor_payload"]["terminal_status"]
            == a13.INCOMPLETE_FRAGMENT_STATUS
            for row in repaired[28:36]
        )
        and all(
            row["successor_kind"] == "composed_fragment_complete_instruction"
            and row["successor_payload"]["terminal_status"]
            == a13.COMPOSED_FRAGMENT_STATUS
            for row in repaired[36:]
        ),
        "repaired proof/fragment disposition or terminal status drift",
    )
    _require(
        all(
            row["successor_payload"]["alias_admitted"] is False
            and row["successor_payload"]["occurrence_equivalence_admitted"]
            is False
            and row["successor_payload"]["repeat_coverage_arm_admitted"]
            is False
            for row in repaired
        ),
        "repaired proof/fragment successor admitted alias authority",
    )
    law_gaps = semantic["untouched_law_gap_predecessor_ids"]
    _require(
        semantic["untouched_law_gap_predecessor_count"] == len(law_gaps) == 14
        and semantic["untouched_law_gap_predecessor_domain_sha256"]
        == _domain_sha(law_gaps),
        "untouched law-gap domain drift",
    )
    _require(
        not {row["predecessor_row_id"] for row in repaired} & set(law_gaps)
        and semantic["repaired_and_law_gap_domains_disjoint"] is True,
        "law gap was repaired or reclassified",
    )
    _require(
        not set(law_gaps) & set(approved_ids),
        "law gap was reclassified as an alias admission",
    )
    _require(
        semantic["unexplained_targeted_hit_rows"] == []
        and semantic["unexplained_targeted_hit_count"] == 0,
        "unexplained semantic-gate hit",
    )
    unexplained = sum(
        row["unexplained_targeted_hit_count"]
        for row in (continuation, pairwise, semantic)
    )
    _require(
        artifact["unexplained_targeted_hit_count"] == unexplained == 0,
        "top-level unexplained targeted hit",
    )


def _load_artifact(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    value = a12.strict_json_loads(raw, str(path))
    _require(
        isinstance(value, dict), "targeted sweep artifact is not an object"
    )
    _require(
        raw == canonical_bytes(value),
        "targeted sweep artifact is noncanonical",
    )
    validate_artifact(value)
    return value


def _write_artifact(artifact: Mapping[str, Any], output_root: Path) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    destination = output_root / OUTPUT_FILENAME
    raw = canonical_bytes(artifact)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{OUTPUT_FILENAME}.", dir=output_root
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def _check_git_order(artifact: Mapping[str, Any], output_path: Path) -> None:
    evidence_commit = _first_add_commit(output_path)
    head = _git("rev-parse", "HEAD").stdout.strip()
    for row in artifact["successor_seal_bindings"]:
        commit = row["first_add_commit"]
        _require(
            isinstance(commit, str), "seal first-add commit was not bound"
        )
        _require_strict_ancestor(
            commit,
            evidence_commit,
            f"seal {row['era_order_position']} before sweep evidence",
        )
        _require_strict_ancestor(
            commit,
            head,
            f"seal {row['era_order_position']} before check HEAD",
        )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument(
        "--seal-root", type=Path, default=DEFAULT_SUCCESSOR_SEAL_ROOT
    )
    parser.add_argument(
        "--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT
    )
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    expected = build_artifact(
        source_root=args.source_root,
        seal_root=args.seal_root,
        verify_git=True,
    )
    output_path = args.output_root / OUTPUT_FILENAME
    if args.check:
        actual = _load_artifact(output_path)
        _require(
            canonical_bytes(actual) == canonical_bytes(expected),
            "committed targeted sweep differs from fresh reconstruction",
        )
        _check_git_order(actual, output_path)
    else:
        output_path = _write_artifact(expected, args.output_root)
    print(
        json.dumps(
            {
                "artifact_id": expected["artifact_id"],
                "check": bool(args.check),
                "document_count": expected["document_count"],
                "output_path": _portable_path(output_path, args.output_root),
                "successor_seal_count": expected[
                    "successor_seal_binding_count"
                ],
                "unexplained_targeted_hit_count": expected[
                    "unexplained_targeted_hit_count"
                ],
                "status": "pass",
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
