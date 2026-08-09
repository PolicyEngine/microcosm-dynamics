"""Publish Amendment 13's operative tier-2 repair overlays and era seals.

The execution-law validator is the sole source of the repair objects.  This
publisher writes each of the fourteen document overlays and each of the six
successor-era seals as a separate canonical JSON artifact so that the two
enacted first-add commits remain distinguishable.  It emits no authority,
certification, Q5 input, or production output.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from contextlib import ExitStack
from pathlib import Path
from typing import Any, NamedTuple
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import validate_amendment13_execution_law as a13  # noqa: E402


class PublicationError(RuntimeError):
    """Raised when the operative repair publication fails closed."""


TIER2_ROOT_RELATIVE = Path("docs/analysis/amendment_12_rq_catalog_tier2")
TIER2_ROOT = ROOT / TIER2_ROOT_RELATIVE
OVERLAY_DIRECTORY = Path("amendment_13_repair_overlays_v1")
SEAL_DIRECTORY = Path("amendment_13_successor_era_seals_v1")
ARTIFACT_SELECTIONS = ("overlays", "seals", "all")

OVERLAY_POSITIONS = (
    7,
    10,
    11,
    12,
    13,
    15,
    17,
    19,
    36,
    52,
    56,
    58,
    66,
    70,
)
EXPECTED_REPAIR_COUNTS_BY_DOCUMENT = {
    7: 2,
    10: 1,
    11: 1,
    12: 1,
    13: 1,
    15: 2,
    17: 3,
    19: 2,
    36: 9,
    52: 5,
    56: 11,
    58: 3,
    66: 3,
    70: 2,
}
EXPECTED_ERA_REPAIR_PROJECTION = (8, 5, 9, 19, 5, 0)
SUCCESSOR_DOMAINS = (
    "semantically_incompatible_local_proof_successor_rows",
    "incomplete_fragment_terminal_successor_rows",
    "composed_fragment_successor_rows",
    "doc036_aggregate_domain_successor_rows",
)

ORDERED_CEREMONY_REMOTE_REF = (
    "refs/heads/ceremony-archive/a12-tier2-r03-ordered"
)
ORDERED_CEREMONY_LOCAL_REF = (
    "refs/remotes/origin/ceremony-archive/a12-tier2-r03-ordered"
)
ORDERED_CEREMONY_BASE_COMMIT = "ace88cda0e588f1b847552a31787cc69324d8646"
ORDERED_CEREMONY_RECEIPT_COMMIT = "cbc44fe1642106e1bfecee869de1b9c61f832756"
ORDERED_CEREMONY_OVERLAY_COMMIT = "c6091f06955a3dd8e554f38833fe2eb43e7b08e0"
ORDERED_CEREMONY_SEAL_COMMIT = "44c6641aa0ec57036a54e0988a5f18b50a15e50c"
ORDERED_CEREMONY_EVIDENCE_COMMIT = "ba4bd4a734dc5ddd835bb7374bf5a37c12a190ae"
ORDERED_CEREMONY_RECEIPT_TREE = "321991ced87fe19d0c14e4642aaf44eaf17ca26b"
ORDERED_CEREMONY_OVERLAY_TREE = "0fed299d439203d959c7a9b1812e4856671db951"
ORDERED_CEREMONY_SEAL_TREE = "4b6233a9583d8cb90a46bc85b1840ce5b4ebe0de"
ORDERED_CEREMONY_TREE_OID = "507e7062cac23b08a397dd5e959d1ff7d1827bc4"
TIER2_SQUASH_COMMIT = "a352e66284b60997210c634bb427141e7e523a75"

RECEIPT_PATH = TIER2_ROOT_RELATIVE / "fix5_rederivation_confirmation_v1.json"
TARGETED_SWEEP_PATH = (
    TIER2_ROOT_RELATIVE
    / "targeted_sweeps"
    / "admission_rule_targeted_sweeps_v1.json"
)
ORDERED_OVERLAY_PATHS = tuple(
    TIER2_ROOT_RELATIVE
    / OVERLAY_DIRECTORY
    / f"document_{position:03d}_repair_overlay_v1.json"
    for position in OVERLAY_POSITIONS
)
ORDERED_SEAL_PATHS = tuple(
    TIER2_ROOT_RELATIVE
    / SEAL_DIRECTORY
    / f"era_{position:02d}_successor_seal_v1.json"
    for position in range(1, 7)
)

ORDERED_CEREMONY_CHANGED_PATHS = {
    "receipt": (("A", RECEIPT_PATH.as_posix()),),
    "overlays": (
        *(("A", path.as_posix()) for path in ORDERED_OVERLAY_PATHS),
        ("A", "scripts/build_amendment13_tier2_repairs.py"),
        ("A", "tests/test_build_amendment13_tier2_repairs.py"),
    ),
    "seals": tuple(("A", path.as_posix()) for path in ORDERED_SEAL_PATHS),
    "evidence": (
        ("A", TARGETED_SWEEP_PATH.as_posix()),
        ("A", "scripts/build_amendment12_tier2_targeted_sweeps.py"),
        ("A", "tests/test_build_amendment12_tier2_targeted_sweeps.py"),
        ("M", "tests/tier_counts.json"),
    ),
}
ORDERED_CEREMONY_ATTESTATION = {
    "remote_ref": ORDERED_CEREMONY_REMOTE_REF,
    "local_ref": ORDERED_CEREMONY_LOCAL_REF,
    "tree_oid": ORDERED_CEREMONY_TREE_OID,
    "squash_commit": TIER2_SQUASH_COMMIT,
    "stages": (
        {
            "role": "receipt",
            "commit": ORDERED_CEREMONY_RECEIPT_COMMIT,
            "parent": ORDERED_CEREMONY_BASE_COMMIT,
            "tree_oid": ORDERED_CEREMONY_RECEIPT_TREE,
            "changed_paths": ORDERED_CEREMONY_CHANGED_PATHS["receipt"],
        },
        {
            "role": "overlays",
            "commit": ORDERED_CEREMONY_OVERLAY_COMMIT,
            "parent": ORDERED_CEREMONY_RECEIPT_COMMIT,
            "tree_oid": ORDERED_CEREMONY_OVERLAY_TREE,
            "changed_paths": ORDERED_CEREMONY_CHANGED_PATHS["overlays"],
        },
        {
            "role": "seals",
            "commit": ORDERED_CEREMONY_SEAL_COMMIT,
            "parent": ORDERED_CEREMONY_OVERLAY_COMMIT,
            "tree_oid": ORDERED_CEREMONY_SEAL_TREE,
            "changed_paths": ORDERED_CEREMONY_CHANGED_PATHS["seals"],
        },
        {
            "role": "evidence",
            "commit": ORDERED_CEREMONY_EVIDENCE_COMMIT,
            "parent": ORDERED_CEREMONY_SEAL_COMMIT,
            "tree_oid": ORDERED_CEREMONY_TREE_OID,
            "changed_paths": ORDERED_CEREMONY_CHANGED_PATHS["evidence"],
        },
    ),
}
ORDERED_ARTIFACT_COMMIT_BY_PATH = {
    RECEIPT_PATH: ORDERED_CEREMONY_RECEIPT_COMMIT,
    **{
        path: ORDERED_CEREMONY_OVERLAY_COMMIT for path in ORDERED_OVERLAY_PATHS
    },
    **{path: ORDERED_CEREMONY_SEAL_COMMIT for path in ORDERED_SEAL_PATHS},
    TARGETED_SWEEP_PATH: ORDERED_CEREMONY_EVIDENCE_COMMIT,
}
ORDERED_ARTIFACT_PATH_DOMAIN_SHA256 = (
    "504159116708ee4d5e2cc8abec130ca8679d22cce928dca42af12be305361c17"
)
SQUASH_CHANGED_PATHS = tuple(
    sorted(
        changed_path
        for stage in ORDERED_CEREMONY_ATTESTATION["stages"]
        for changed_path in stage["changed_paths"]
    )
)

A15_EXPECTED_MUTATIONS = (
    "ordered_history_attestation_identity_forged",
    "ordered_history_attestation_order_forged",
    "ordered_history_attestation_tree_identity_forged",
    "ordered_history_archive_ref_absent_or_unfetchable",
    "ordered_history_first_add_exception_reused",
    "tier2_certification_schema_keyset_drift",
    "tier2_certification_reconstruction_disagreement",
    "tier2_certification_referee_implementation_reused",
    "tier2_certification_forbidden_emission_forged",
    "tier2_certification_raw_byte_attestation_forged",
    "ceremony_topology_bound_squash_selected",
)
A15_MUTATION_DOMAIN_SHA256 = (
    "285f4f349d27099b64053f88f5292890392fd547643b083410c30f0c5b93b1c8"
)
A12_MUTATION_COUNT = 71
A12_MUTATION_DOMAIN_SHA256 = (
    "89ff204fad60051c82ea2b3a9e1c95243a5576ae720ecaad1a97174fb71871c8"
)
A13_A14_MUTATION_COUNT = 18
A13_A14_MUTATION_DOMAIN_SHA256 = (
    "03495fb62524cc9b5877fd7baf085b9d69a441a4fcbadc9cf1a29ee35d2f06d3"
)
COMPLETE_MUTATION_COUNT = 100
COMPLETE_MUTATION_DOMAIN_SHA256 = (
    "fe2efd7b96c24b7cbd3c6ce350d44906eb5a88b8b35ee77565c1b133cbf1f3e3"
)
MUTATION_CENSUS_STATUS = "pass_all_expected_mutations_rejected"


class MutationBinding(NamedTuple):
    """Bind one named attack to its exact rejecting gate and error."""

    name: str
    prepare: Callable[[], MutationPreparation]
    gate: Callable[..., Any]
    expected_exception: type[Exception]
    expected_message: str


class MutationPreparation(NamedTuple):
    """Hold bound gate arguments and already-entered mutation contexts."""

    arguments: tuple[Any, ...]
    contexts: ExitStack


CERTIFICATION_SCHEMA_VERSION = (
    "amendment_12_tier2_source_hierarchy_certification.v1"
)
CERTIFICATION_ARTIFACT_ID_PREFIX = "a12-tier2-source-hierarchy-certification:"
CERTIFICATION_ARTIFACT_ROLE = (
    "pre_q5_source_only_tier2_certification_nonauthority"
)
CERTIFICATION_STATUS = "pass_a12_t2_r05_source_hierarchy_certification"
CERTIFICATION_PATH = Path(
    "docs/analysis/amendment_12_rq_catalog_tier2/certification/"
    "source_hierarchy_certification_v1.json"
)
CERTIFICATION_BUILDER_PATH = (
    "scripts/build_amendment12_tier2_source_hierarchy_certification.py"
)
CERTIFICATION_VALIDATOR_PATH = (
    "scripts/validate_amendment12_tier2_source_hierarchy_certification.py"
)
CERTIFICATION_BUILDER_FUNCTION = "build_certification"
CERTIFICATION_RECONSTRUCTION_FUNCTION = "reconstruct_source_hierarchy_member"
CERTIFICATION_VALIDATOR_FUNCTION = "validate_committed_certification"
CERTIFICATION_RECONSTRUCTION_DEPENDENCY_POLICY = (
    "self_contained_single_file_stdlib_only_no_shared_reconstruction_v1"
)
CERTIFICATION_TOP_LEVEL_KEYS = frozenset(
    {
        "artifact_id",
        "artifact_role",
        "gate_results",
        "git_order_attestation",
        "integrity",
        "lifecycle",
        "mutation_census",
        "ratification_binding",
        "reconstruction_rows",
        "schema_version",
        "source_build_identity",
        "source_hierarchy_member_identity",
        "status",
    }
)
CERTIFICATION_RATIFICATION_KEYS = frozenset(
    {
        "amendment_number",
        "closure_byte_size",
        "closure_path",
        "closure_raw_sha256",
        "design_blob_oid",
        "design_byte_size",
        "design_path",
        "design_raw_sha256",
        "design_revision",
        "ratification_commit",
        "ratification_commit_sole_parent",
    }
)
CERTIFICATION_SOURCE_BUILD_KEYS = frozenset(
    {
        "questionnaire_document_count",
        "questionnaire_document_domain_sha256",
        "questionnaire_document_keyset_sha256",
        "source_document_count",
        "source_document_domain_sha256",
        "source_document_keyset_sha256",
        "tier2_build_input_domain_sha256",
    }
)
CERTIFICATION_MEMBER_KEYS = frozenset(
    {
        "authority_kind",
        "canonical_byte_size",
        "canonicalization",
        "member_name",
        "raw_sha256",
        "status",
    }
)
CERTIFICATION_RECONSTRUCTION_KEYS = frozenset(
    {
        "implementation_blob_oid",
        "implementation_byte_size",
        "implementation_dependency_paths",
        "implementation_dependency_policy",
        "implementation_mode",
        "implementation_path",
        "implementation_raw_sha256",
        "member_canonical_byte_size",
        "member_raw_sha256",
        "reconstruction_id",
        "status",
        "tier2_build_input_domain_sha256",
    }
)
CERTIFICATION_LIFECYCLE = {
    "actual_consumer_projection_emitted": False,
    "authority_emitted": False,
    "certification_emitted": True,
    "full_g17_c01_row_emitted": False,
    "nonauthority": True,
    "next_required_gate": "A12-T2-R06",
    "production_output_emitted": False,
    "q5_first_add_performed": False,
    "q5_input_emitted": False,
    "source_only_evidence_emitted": True,
}
CERTIFICATION_GATE_IDS = tuple(
    f"A12-T2-R0{position}" for position in range(1, 6)
)
CERTIFICATION_RECONSTRUCTION_IDS = ("R04X-7F2A", "R04X-C91D")
CERTIFICATION_RECONSTRUCTION_PATHS = (
    CERTIFICATION_BUILDER_PATH,
    CERTIFICATION_VALIDATOR_PATH,
)
CERTIFICATION_GIT_ATTESTATION = {
    "archive_ref": ORDERED_CEREMONY_REMOTE_REF,
    "archive_tip_commit": ORDERED_CEREMONY_EVIDENCE_COMMIT,
    "attestation_id": "a15-ordered-tier2-history:v1",
    "source_commit": "19fa24c161e800e004320f0c10e81bce8831af68",
    "source_tree_oid": "e35f9cd65017ece46de2f0c0dbc57f4321c0b8d4",
    "squash_commit": TIER2_SQUASH_COMMIT,
    "tree_oid": ORDERED_CEREMONY_TREE_OID,
}
CERTIFICATION_SOURCE_COUNTS_AND_DOMAINS = {
    "questionnaire_document_count": 81,
    "questionnaire_document_domain_sha256": (
        "b06139b147391d06b4f90a8f28de472a936ec08b3e9eb37001a5a70e2b3c3543"
    ),
    "questionnaire_document_keyset_sha256": (
        "3326c9ba70b7f83f19b0ea934630d26ced73f230be1628cb74031d17160cb1a5"
    ),
    "source_document_count": 257,
    "source_document_domain_sha256": (
        "9d7a98db7c2889eba150f70935f492aebbc41cd521e4139dc1ec886ecd9945ce"
    ),
    "source_document_keyset_sha256": (
        "8b7cad855b791c5cd7d235a74d4a0f1ecc7511dc0458db11d6b04c1b6af2c36a"
    ),
}

TOPOLOGY_BOUND_REQUIREMENT_CODES = (
    "premerge_commit_reachability",
    "first_or_last_add_identity",
    "exact_parent_or_changed_path_domain",
    "strict_or_equal_ancestry_order",
)
BLOB_TREE_BOUND_REQUIREMENT_CODES = (
    "path_mode_blob_byte_hash",
    "resulting_tree_identity",
    "document_only_postmerge_closure",
)
CEREMONY_MERGE_MODES = frozenset({"no_fast_forward_merge_commit", "squash"})


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PublicationError(message)


def _require_exact_keys(
    value: Mapping[str, Any], expected: frozenset[str], label: str
) -> None:
    actual = frozenset(value)
    _require(
        actual == expected,
        f"{label} keyset drift; missing={sorted(expected - actual)!r}, "
        f"extra={sorted(actual - expected)!r}",
    )


def _is_lower_hex(value: Any, length: int) -> bool:
    return (
        isinstance(value, str)
        and len(value) == length
        and all(character in "0123456789abcdef" for character in value)
    )


def _certification_payload_sha256(value: Mapping[str, Any]) -> str:
    payload = {
        key: value[key]
        for key in value
        if key not in {"artifact_id", "integrity"}
    }
    return hashlib.sha256(a13.canonical_json_bytes(payload)).hexdigest()


def _mutation_domain_sha256(names: Sequence[str]) -> str:
    """Hash one exact ordered mutation-name array."""

    return hashlib.sha256(a13.canonical_json_bytes(list(names))).hexdigest()


def _expected_mutation_census() -> dict[str, Any]:
    """Return the fixed target census used only as an execution comparator."""

    components = (
        (
            "amendment_12_historical",
            A12_MUTATION_COUNT,
            A12_MUTATION_DOMAIN_SHA256,
        ),
        (
            "amendments_13_14_inherited",
            A13_A14_MUTATION_COUNT,
            A13_A14_MUTATION_DOMAIN_SHA256,
        ),
        (
            "amendment_15",
            len(A15_EXPECTED_MUTATIONS),
            A15_MUTATION_DOMAIN_SHA256,
        ),
    )
    return {
        "components": [
            {
                "component_id": component_id,
                "expected_count": count,
                "expected_domain_sha256": digest,
                "rejected_count": count,
                "rejected_domain_sha256": digest,
                "status": MUTATION_CENSUS_STATUS,
            }
            for component_id, count, digest in components
        ],
        "expected_count": COMPLETE_MUTATION_COUNT,
        "expected_domain_sha256": COMPLETE_MUTATION_DOMAIN_SHA256,
        "rejected_count": COMPLETE_MUTATION_COUNT,
        "rejected_domain_sha256": COMPLETE_MUTATION_DOMAIN_SHA256,
        "status": MUTATION_CENSUS_STATUS,
    }


def _component_mutation_census(
    component_id: str,
    rejected_names: Sequence[str],
    *,
    expected_count: int,
    expected_domain_sha256: str,
) -> dict[str, Any]:
    """Fail closed unless one runner returned its exact ordered domain."""

    names = tuple(rejected_names)
    _require(
        all(isinstance(name, str) and name for name in names),
        f"{component_id} mutation census contains a non-name",
    )
    digest = _mutation_domain_sha256(names)
    _require(
        len(names) == expected_count
        and len(set(names)) == expected_count
        and digest == expected_domain_sha256,
        f"{component_id} mutation census drift: count={len(names)}, "
        f"unique={len(set(names))}, domain={digest}",
    )
    return {
        "component_id": component_id,
        "expected_count": expected_count,
        "expected_domain_sha256": expected_domain_sha256,
        "rejected_count": len(names),
        "rejected_domain_sha256": digest,
        "status": MUTATION_CENSUS_STATUS,
    }


def _execute_a12_mutation_tests() -> tuple[str, ...]:
    """Load, validate, and attack the committed Amendment-12 bundle."""

    bundle = a13.a12.load_committed_bundle()
    a13.a12.validate_bundle(bundle)
    return tuple(a13.a12.run_mutation_tests(bundle))


def _repin_synthetic_certification(value: dict[str, Any]) -> None:
    digest = _certification_payload_sha256(value)
    value["artifact_id"] = CERTIFICATION_ARTIFACT_ID_PREFIX + digest
    value["integrity"] = {
        "canonicalization": (
            "python-json-sort-keys-compact-ascii-no-nan-lf-v1"
        ),
        "payload_sha256": digest,
    }


def _build_a15_attack_certificate_candidate() -> dict[str, Any]:
    """Build the nonemitting structural baseline attacked inside the runner."""

    member_sha = "1" * 64
    input_sha = "2" * 64
    value: dict[str, Any] = {
        "artifact_id": "",
        "artifact_role": CERTIFICATION_ARTIFACT_ROLE,
        "gate_results": [
            {"gate_id": gate_id, "status": "pass"}
            for gate_id in CERTIFICATION_GATE_IDS
        ],
        "git_order_attestation": copy.deepcopy(CERTIFICATION_GIT_ATTESTATION),
        "integrity": {},
        "lifecycle": copy.deepcopy(CERTIFICATION_LIFECYCLE),
        "mutation_census": _expected_mutation_census(),
        "ratification_binding": {
            "amendment_number": 15,
            "closure_byte_size": 1_000,
            "closure_path": (
                "docs/analysis/amendment_15_ratification/closure_v1.json"
            ),
            "closure_raw_sha256": "3" * 64,
            "design_blob_oid": "4" * 40,
            "design_byte_size": 4_000_000,
            "design_path": "docs/design/covered_earnings_correction.md",
            "design_raw_sha256": "5" * 64,
            "design_revision": 17,
            "ratification_commit": "6" * 40,
            "ratification_commit_sole_parent": "7" * 40,
        },
        "reconstruction_rows": [
            {
                "implementation_blob_oid": "8" * 40,
                "implementation_byte_size": 10_000,
                "implementation_dependency_paths": [
                    CERTIFICATION_RECONSTRUCTION_PATHS[0]
                ],
                "implementation_dependency_policy": (
                    CERTIFICATION_RECONSTRUCTION_DEPENDENCY_POLICY
                ),
                "implementation_mode": "100644",
                "implementation_path": CERTIFICATION_RECONSTRUCTION_PATHS[0],
                "implementation_raw_sha256": "8" * 64,
                "member_canonical_byte_size": 123_456,
                "member_raw_sha256": member_sha,
                "reconstruction_id": CERTIFICATION_RECONSTRUCTION_IDS[0],
                "status": "pass_independent_source_reconstruction",
                "tier2_build_input_domain_sha256": input_sha,
            },
            {
                "implementation_blob_oid": "9" * 40,
                "implementation_byte_size": 11_000,
                "implementation_dependency_paths": [
                    CERTIFICATION_RECONSTRUCTION_PATHS[1]
                ],
                "implementation_dependency_policy": (
                    CERTIFICATION_RECONSTRUCTION_DEPENDENCY_POLICY
                ),
                "implementation_mode": "100644",
                "implementation_path": CERTIFICATION_RECONSTRUCTION_PATHS[1],
                "implementation_raw_sha256": "9" * 64,
                "member_canonical_byte_size": 123_456,
                "member_raw_sha256": member_sha,
                "reconstruction_id": CERTIFICATION_RECONSTRUCTION_IDS[1],
                "status": "pass_independent_source_reconstruction",
                "tier2_build_input_domain_sha256": input_sha,
            },
        ],
        "schema_version": CERTIFICATION_SCHEMA_VERSION,
        "source_build_identity": {
            **CERTIFICATION_SOURCE_COUNTS_AND_DOMAINS,
            "tier2_build_input_domain_sha256": input_sha,
        },
        "source_hierarchy_member_identity": {
            "authority_kind": "prospective_g17_c01_source_member_pre_q5",
            "canonical_byte_size": 123_456,
            "canonicalization": (
                "python-json-sort-keys-compact-ascii-no-nan-lf-v1"
            ),
            "member_name": "hierarchy_annotation_authority",
            "raw_sha256": member_sha,
            "status": "pass",
        },
        "status": CERTIFICATION_STATUS,
    }
    _repin_synthetic_certification(value)
    return value


def _activate_mutation_preparation(
    arguments: tuple[Any, ...],
    *contexts: Any,
) -> MutationPreparation:
    """Enter every fault-injection context before the rejection catcher."""

    stack = ExitStack()
    try:
        for context in contexts:
            stack.enter_context(context)
    except Exception:
        stack.close()
        raise
    return MutationPreparation(arguments, stack)


def _prepare_attestation_identity_mutation() -> MutationPreparation:
    candidate = copy.deepcopy(ORDERED_CEREMONY_ATTESTATION)
    candidate["stages"][1]["commit"] = TIER2_SQUASH_COMMIT
    return _activate_mutation_preparation((candidate,))


def _prepare_attestation_order_mutation() -> MutationPreparation:
    return _activate_mutation_preparation(
        (),
        mock.patch.object(
            sys.modules[__name__],
            "_is_strict_ancestor",
            return_value=False,
        ),
    )


def _prepare_attestation_tree_mutation() -> MutationPreparation:
    candidate = copy.deepcopy(ORDERED_CEREMONY_ATTESTATION)
    candidate["tree_oid"] = "0" * 40
    return _activate_mutation_preparation((candidate,))


def _prepare_absent_archive_mutation() -> MutationPreparation:
    original = _run_git

    def absent_ref(repo_root: Path, *arguments: str):
        if arguments[:3] == ("show-ref", "--verify", "--hash"):
            return subprocess.CompletedProcess(
                arguments,
                1,
                stdout=b"",
                stderr=b"absent archive ref",
            )
        return original(repo_root, *arguments)

    return _activate_mutation_preparation(
        (),
        mock.patch.object(sys.modules[__name__], "_run_git", absent_ref),
    )


def _prepare_exception_reuse_mutation() -> MutationPreparation:
    return _activate_mutation_preparation(
        (
            Path("scripts/build_amendment13_tier2_repairs.py"),
            TIER2_SQUASH_COMMIT,
            {
                "stage_commits": {
                    stage["role"]: stage["commit"]
                    for stage in ORDERED_CEREMONY_ATTESTATION["stages"]
                }
            },
        )
    )


def _prepare_schema_keyset_mutation() -> MutationPreparation:
    candidate = _build_a15_attack_certificate_candidate()
    candidate.pop("status")
    return _activate_mutation_preparation((candidate,))


def _prepare_reconstruction_disagreement_mutation() -> MutationPreparation:
    candidate = _build_a15_attack_certificate_candidate()
    candidate["reconstruction_rows"][1]["member_raw_sha256"] = "a" * 64
    _repin_synthetic_certification(candidate)
    return _activate_mutation_preparation(
        (
            candidate["reconstruction_rows"],
            candidate["source_hierarchy_member_identity"],
            candidate["source_build_identity"],
        )
    )


def _prepare_reused_referee_mutation() -> MutationPreparation:
    candidate = _build_a15_attack_certificate_candidate()
    left, right = candidate["reconstruction_rows"]
    right["implementation_blob_oid"] = left["implementation_blob_oid"]
    right["implementation_raw_sha256"] = left["implementation_raw_sha256"]
    _repin_synthetic_certification(candidate)
    return _activate_mutation_preparation(
        (
            candidate["reconstruction_rows"],
            candidate["source_hierarchy_member_identity"],
            candidate["source_build_identity"],
        )
    )


def _prepare_forbidden_emission_mutation() -> MutationPreparation:
    candidate = _build_a15_attack_certificate_candidate()
    candidate["lifecycle"]["authority_emitted"] = True
    _repin_synthetic_certification(candidate)
    return _activate_mutation_preparation((candidate["lifecycle"],))


def _prepare_raw_attestation_mutation() -> MutationPreparation:
    candidate = _build_a15_attack_certificate_candidate()
    candidate["artifact_id"] = CERTIFICATION_ARTIFACT_ID_PREFIX + "f" * 64
    return _activate_mutation_preparation((candidate,))


def _prepare_topology_squash_mutation() -> MutationPreparation:
    return _activate_mutation_preparation(
        (["first_or_last_add_identity"], "squash")
    )


def _gate_ordered_attestation(candidate: Mapping[str, Any]) -> None:
    _validate_ordered_ceremony_attestation(
        repo_root=ROOT,
        attestation=candidate,
    )


def _gate_ordered_attestation_order() -> None:
    validate_ordered_ceremony_attestation()


def _gate_absent_archive_ref() -> None:
    validate_ordered_ceremony_attestation()


def _gate_first_add_exception_reuse(
    relative_path: Path,
    observed_first_add: str,
    attestation: Mapping[str, Any],
) -> None:
    _attested_order_commit_for_squashed_first_add(
        relative_path,
        observed_first_add,
        attestation,
    )


def _gate_topology_merge_mode(
    requirement_codes: Sequence[str], merge_mode: str
) -> None:
    validate_ceremony_merge_mode(requirement_codes, merge_mode)


def _execute_amendment15_mutation(binding: MutationBinding) -> str:
    """Prepare outside the rejection scope, then call the bound real gate."""

    try:
        prepared = binding.prepare()
    except Exception as error:
        raise PublicationError(
            f"mutation setup failed before bound gate {binding.gate.__name__}: "
            f"{binding.name}: {type(error).__name__}: {error}"
        ) from error

    expected_error = None
    wrong_error = None
    try:
        try:
            binding.gate(*prepared.arguments)
        except binding.expected_exception as error:
            expected_error = error
        except Exception as error:
            wrong_error = error
    finally:
        try:
            prepared.contexts.close()
        except Exception as error:
            raise PublicationError(
                f"mutation teardown failed after bound gate "
                f"{binding.gate.__name__}: {binding.name}: "
                f"{type(error).__name__}: {error}"
            ) from error

    if wrong_error is not None:
        raise PublicationError(
            f"mutation {binding.name} raised wrong exception at bound gate "
            f"{binding.gate.__name__}: {type(wrong_error).__name__}: "
            f"{wrong_error}"
        ) from wrong_error
    if expected_error is None:
        raise PublicationError(
            f"mutation survived bound gate {binding.gate.__name__}: "
            f"{binding.name}"
        )
    _require(
        binding.expected_message in str(expected_error),
        f"mutation {binding.name} hit wrong bound gate "
        f"{binding.gate.__name__}: {expected_error}",
    )
    return binding.name


def _execute_complete_mutation_names() -> (
    tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...]]
):
    """Execute every default inherited and A15 runner for this call."""

    a12_names = _execute_a12_mutation_tests()
    law = a13.build_execution_law()
    a13.validate_execution_law(law)
    a13_names = tuple(a13.run_mutation_tests(law))
    a14_names = tuple(a13.run_enforcement_mutation_tests(law))
    a15_names = run_amendment15_mutation_tests()
    return a12_names, a13_names, a14_names, a15_names


def _compose_complete_mutation_census(
    outputs: Sequence[Sequence[str]],
) -> dict[str, Any]:
    """Private fault-injection seam over already executed runner outputs."""

    _require(
        len(outputs) == 4,
        "complete mutation runner component domain drift",
    )
    a12_names, a13_names, a14_names, a15_names = (
        tuple(names) for names in outputs
    )

    _require(
        a13_names == a13.A13_EXPECTED_MUTATIONS,
        "Amendment-13 seven-mutation runner output drift",
    )
    _require(
        a14_names == a13.A13_ENFORCEMENT_EXPECTED_MUTATIONS,
        "Amendment-14 eleven-mutation runner output drift",
    )
    _require(
        a15_names == A15_EXPECTED_MUTATIONS,
        "Amendment-15 eleven-mutation runner output drift",
    )
    inherited_names = (*a13_names, *a14_names)
    components = [
        _component_mutation_census(
            "amendment_12_historical",
            a12_names,
            expected_count=A12_MUTATION_COUNT,
            expected_domain_sha256=A12_MUTATION_DOMAIN_SHA256,
        ),
        _component_mutation_census(
            "amendments_13_14_inherited",
            inherited_names,
            expected_count=A13_A14_MUTATION_COUNT,
            expected_domain_sha256=A13_A14_MUTATION_DOMAIN_SHA256,
        ),
        _component_mutation_census(
            "amendment_15",
            a15_names,
            expected_count=len(A15_EXPECTED_MUTATIONS),
            expected_domain_sha256=A15_MUTATION_DOMAIN_SHA256,
        ),
    ]
    all_names = (*a12_names, *inherited_names, *a15_names)
    aggregate_digest = _mutation_domain_sha256(all_names)
    _require(
        len(all_names) == COMPLETE_MUTATION_COUNT
        and len(set(all_names)) == COMPLETE_MUTATION_COUNT
        and aggregate_digest == COMPLETE_MUTATION_DOMAIN_SHA256,
        "complete mutation census drift: "
        f"count={len(all_names)}, unique={len(set(all_names))}, "
        f"domain={aggregate_digest}",
    )
    census = {
        "components": components,
        "expected_count": COMPLETE_MUTATION_COUNT,
        "expected_domain_sha256": COMPLETE_MUTATION_DOMAIN_SHA256,
        "rejected_count": len(all_names),
        "rejected_domain_sha256": aggregate_digest,
        "status": MUTATION_CENSUS_STATUS,
    }
    _require(
        census == _expected_mutation_census(),
        "execution-derived mutation census disagrees with the exact target",
    )
    return census


def run_complete_mutation_census() -> dict[str, Any]:
    """Execute and authenticate the exact ordered 71 + 18 + 11 census."""

    return _compose_complete_mutation_census(
        _execute_complete_mutation_names()
    )


def _validate_certification_top_level(value: Mapping[str, Any]) -> None:
    """Validate only the certificate's top-level schema and fixed codes."""

    _require_exact_keys(
        value, CERTIFICATION_TOP_LEVEL_KEYS, "tier-2 certification"
    )
    _require(
        value["schema_version"] == CERTIFICATION_SCHEMA_VERSION
        and value["artifact_role"] == CERTIFICATION_ARTIFACT_ROLE
        and value["status"] == CERTIFICATION_STATUS,
        "tier-2 certification fixed code drift",
    )


def _validate_certification_ratification(
    ratification: Mapping[str, Any],
) -> None:
    """Validate only the ratification-binding invariant."""

    _require(
        isinstance(ratification, Mapping),
        "tier-2 certification ratification binding is not an object",
    )
    _require_exact_keys(
        ratification,
        CERTIFICATION_RATIFICATION_KEYS,
        "tier-2 certification ratification binding",
    )
    _require(
        type(ratification["amendment_number"]) is int
        and ratification["amendment_number"] == 15
        and type(ratification["design_revision"]) is int
        and ratification["design_revision"] == 17
        and ratification["design_path"]
        == "docs/design/covered_earnings_correction.md"
        and ratification["closure_path"]
        == "docs/analysis/amendment_15_ratification/closure_v1.json"
        and type(ratification["closure_byte_size"]) is int
        and ratification["closure_byte_size"] > 0
        and type(ratification["design_byte_size"]) is int
        and ratification["design_byte_size"] > 3_836_294
        and _is_lower_hex(ratification["closure_raw_sha256"], 64)
        and _is_lower_hex(ratification["design_blob_oid"], 40)
        and _is_lower_hex(ratification["design_raw_sha256"], 64)
        and _is_lower_hex(ratification["ratification_commit"], 40)
        and _is_lower_hex(ratification["ratification_commit_sole_parent"], 40),
        "tier-2 certification ratification binding drift",
    )


def _validate_certification_source(source: Mapping[str, Any]) -> None:
    """Validate only the source-build identity invariant."""

    _require(
        isinstance(source, Mapping),
        "tier-2 certification source build identity is not an object",
    )
    _require_exact_keys(
        source,
        CERTIFICATION_SOURCE_BUILD_KEYS,
        "tier-2 certification source build identity",
    )
    _require(
        type(source["questionnaire_document_count"]) is int
        and type(source["source_document_count"]) is int
        and all(
            source[key] == expected
            for key, expected in CERTIFICATION_SOURCE_COUNTS_AND_DOMAINS.items()
        )
        and _is_lower_hex(source["tier2_build_input_domain_sha256"], 64),
        "tier-2 certification source build identity drift",
    )


def _validate_certification_member(member: Mapping[str, Any]) -> None:
    """Validate only the reconstructed member identity invariant."""

    _require(
        isinstance(member, Mapping),
        "tier-2 certification member identity is not an object",
    )
    _require_exact_keys(
        member,
        CERTIFICATION_MEMBER_KEYS,
        "tier-2 certification member identity",
    )
    _require(
        member["authority_kind"] == "prospective_g17_c01_source_member_pre_q5"
        and member["canonicalization"]
        == "python-json-sort-keys-compact-ascii-no-nan-lf-v1"
        and member["member_name"] == "hierarchy_annotation_authority"
        and member["status"] == "pass"
        and type(member["canonical_byte_size"]) is int
        and member["canonical_byte_size"] > 0
        and _is_lower_hex(member["raw_sha256"], 64),
        "tier-2 certification member identity drift",
    )


def _validate_certification_reconstructions(
    rows: Sequence[Mapping[str, Any]],
    member: Mapping[str, Any],
    source: Mapping[str, Any],
) -> None:
    """Validate only the two-referee reconstruction invariant."""

    _require(
        isinstance(rows, list) and len(rows) == 2,
        "tier-2 certification requires exactly two reconstructions",
    )
    for row in rows:
        _require(
            isinstance(row, Mapping),
            "tier-2 certification reconstruction row is not an object",
        )
        _require_exact_keys(
            row,
            CERTIFICATION_RECONSTRUCTION_KEYS,
            "tier-2 certification reconstruction row",
        )
        _require(
            row["implementation_mode"] == "100644"
            and row["implementation_dependency_paths"]
            == [row["implementation_path"]]
            and row["implementation_dependency_policy"]
            == CERTIFICATION_RECONSTRUCTION_DEPENDENCY_POLICY
            and row["status"] == "pass_independent_source_reconstruction"
            and type(row["implementation_byte_size"]) is int
            and row["implementation_byte_size"] > 0
            and type(row["member_canonical_byte_size"]) is int
            and row["member_canonical_byte_size"] > 0
            and _is_lower_hex(row["implementation_blob_oid"], 40)
            and _is_lower_hex(row["implementation_raw_sha256"], 64),
            "tier-2 certification reconstruction implementation drift",
        )
    _require(
        tuple(row["reconstruction_id"] for row in rows)
        == CERTIFICATION_RECONSTRUCTION_IDS
        and tuple(row["implementation_path"] for row in rows)
        == CERTIFICATION_RECONSTRUCTION_PATHS
        and len({row["implementation_blob_oid"] for row in rows}) == 2
        and len({row["implementation_raw_sha256"] for row in rows}) == 2,
        "tier-2 certification referee implementations are not distinct",
    )
    _require(
        all(
            row["member_canonical_byte_size"] == member["canonical_byte_size"]
            and row["member_raw_sha256"] == member["raw_sha256"]
            and row["tier2_build_input_domain_sha256"]
            == source["tier2_build_input_domain_sha256"]
            for row in rows
        ),
        "tier-2 certification reconstruction disagreement",
    )


def _validate_certification_gates(
    gates: Sequence[Mapping[str, Any]],
) -> None:
    """Validate only the ordered five-gate result invariant."""

    _require(
        isinstance(gates, list)
        and all(isinstance(row, Mapping) for row in gates)
        and [row.get("gate_id") for row in gates]
        == list(CERTIFICATION_GATE_IDS),
        "tier-2 certification gate domain or order drift",
    )
    for row in gates:
        _require(
            isinstance(row, Mapping)
            and set(row) == {"gate_id", "status"}
            and row["status"] == "pass",
            "tier-2 certification gate result drift",
        )


def _validate_certification_git_attestation(
    attestation: Mapping[str, Any],
) -> None:
    """Validate only the bound Git-order attestation invariant."""

    _require(
        attestation == CERTIFICATION_GIT_ATTESTATION,
        "tier-2 certification Git-order attestation drift",
    )


def _validate_certification_lifecycle(lifecycle: Mapping[str, Any]) -> None:
    """Validate only the nonauthority lifecycle-stop invariant."""

    lifecycle_boolean_keys = {
        key
        for key, expected in CERTIFICATION_LIFECYCLE.items()
        if type(expected) is bool
    }
    _require(
        isinstance(lifecycle, Mapping)
        and all(
            type(lifecycle.get(key)) is bool for key in lifecycle_boolean_keys
        )
        and type(lifecycle.get("next_required_gate")) is str
        and lifecycle == CERTIFICATION_LIFECYCLE,
        "tier-2 certification forbidden emission or lifecycle drift",
    )


def _validate_certification_mutation_census(
    mutation: Mapping[str, Any],
    executed_census: Mapping[str, Any],
) -> None:
    """Validate only the serialized-versus-executed census invariant."""

    _require(
        isinstance(mutation, Mapping),
        "tier-2 certification mutation census is not an object",
    )
    _require_exact_keys(
        mutation,
        frozenset(
            {
                "components",
                "expected_count",
                "expected_domain_sha256",
                "rejected_count",
                "rejected_domain_sha256",
                "status",
            }
        ),
        "tier-2 certification mutation census",
    )
    components = mutation["components"]
    _require(
        isinstance(components, list) and len(components) == 3,
        "tier-2 certification mutation component domain drift",
    )
    component_keys = frozenset(
        {
            "component_id",
            "expected_count",
            "expected_domain_sha256",
            "rejected_count",
            "rejected_domain_sha256",
            "status",
        }
    )
    for component in components:
        _require(
            isinstance(component, Mapping),
            "tier-2 certification mutation component is not an object",
        )
        _require_exact_keys(
            component,
            component_keys,
            "tier-2 certification mutation component",
        )
        _require(
            type(component["expected_count"]) is int
            and type(component["rejected_count"]) is int
            and _is_lower_hex(component["expected_domain_sha256"], 64)
            and _is_lower_hex(component["rejected_domain_sha256"], 64)
            and component["status"] == MUTATION_CENSUS_STATUS,
            "tier-2 certification mutation component value drift",
        )
    _require(
        type(mutation["expected_count"]) is int
        and type(mutation["rejected_count"]) is int
        and _is_lower_hex(mutation["expected_domain_sha256"], 64)
        and _is_lower_hex(mutation["rejected_domain_sha256"], 64)
        and mutation["status"] == MUTATION_CENSUS_STATUS,
        "tier-2 certification aggregate mutation census value drift",
    )
    _require(
        mutation == executed_census
        and mutation == _expected_mutation_census(),
        "tier-2 certification execution-derived mutation census drift",
    )


def _validate_certification_integrity(value: Mapping[str, Any]) -> None:
    """Validate only the payload and artifact-identity invariant."""

    integrity = value["integrity"]
    _require(
        isinstance(integrity, Mapping)
        and set(integrity) == {"canonicalization", "payload_sha256"}
        and integrity["canonicalization"]
        == "python-json-sort-keys-compact-ascii-no-nan-lf-v1"
        and _is_lower_hex(integrity["payload_sha256"], 64),
        "tier-2 certification integrity drift",
    )
    payload_sha256 = _certification_payload_sha256(value)
    _require(
        integrity["payload_sha256"] == payload_sha256
        and value["artifact_id"]
        == CERTIFICATION_ARTIFACT_ID_PREFIX + payload_sha256,
        "tier-2 certification raw-byte payload attestation drift",
    )


def _create_amendment15_mutation_runner() -> (
    tuple[tuple[MutationBinding, ...], Callable[[], tuple[str, ...]]]
):
    """Capture the fixed callables and bind them to the enacted design."""

    fixed_bindings = (
        MutationBinding(
            "ordered_history_attestation_identity_forged",
            _prepare_attestation_identity_mutation,
            _gate_ordered_attestation,
            PublicationError,
            "overlays commit identity drift",
        ),
        MutationBinding(
            "ordered_history_attestation_order_forged",
            _prepare_attestation_order_mutation,
            _gate_ordered_attestation_order,
            PublicationError,
            "strict-ancestor chain drift",
        ),
        MutationBinding(
            "ordered_history_attestation_tree_identity_forged",
            _prepare_attestation_tree_mutation,
            _gate_ordered_attestation,
            PublicationError,
            "tree identity drift",
        ),
        MutationBinding(
            "ordered_history_archive_ref_absent_or_unfetchable",
            _prepare_absent_archive_mutation,
            _gate_absent_archive_ref,
            PublicationError,
            "archive ref is absent or was not fetched",
        ),
        MutationBinding(
            "ordered_history_first_add_exception_reused",
            _prepare_exception_reuse_mutation,
            _gate_first_add_exception_reuse,
            PublicationError,
            "cannot reuse the tier-2 squash exception",
        ),
        MutationBinding(
            "tier2_certification_schema_keyset_drift",
            _prepare_schema_keyset_mutation,
            _validate_certification_top_level,
            PublicationError,
            "keyset drift",
        ),
        MutationBinding(
            "tier2_certification_reconstruction_disagreement",
            _prepare_reconstruction_disagreement_mutation,
            _validate_certification_reconstructions,
            PublicationError,
            "reconstruction disagreement",
        ),
        MutationBinding(
            "tier2_certification_referee_implementation_reused",
            _prepare_reused_referee_mutation,
            _validate_certification_reconstructions,
            PublicationError,
            "not distinct",
        ),
        MutationBinding(
            "tier2_certification_forbidden_emission_forged",
            _prepare_forbidden_emission_mutation,
            _validate_certification_lifecycle,
            PublicationError,
            "forbidden emission or lifecycle drift",
        ),
        MutationBinding(
            "tier2_certification_raw_byte_attestation_forged",
            _prepare_raw_attestation_mutation,
            _validate_certification_integrity,
            PublicationError,
            "raw-byte payload attestation drift",
        ),
        MutationBinding(
            "ceremony_topology_bound_squash_selected",
            _prepare_topology_squash_mutation,
            _gate_topology_merge_mode,
            PublicationError,
            "requires a no-fast-forward merge commit",
        ),
    )
    fixed_projection = tuple(
        (
            binding.name,
            binding.prepare.__name__,
            binding.gate.__name__,
            binding.expected_exception.__name__,
            binding.expected_message,
        )
        for binding in fixed_bindings
    )
    validate_document_projection = a13._validate_document_semantic_projection
    design_path = ROOT / a13.DESIGN_PATH
    execute_mutation = _execute_amendment15_mutation
    mutation_domain_sha256 = A15_MUTATION_DOMAIN_SHA256

    def run_amendment15_mutation_tests() -> tuple[str, ...]:
        """Execute the immutable design-verified Amendment-15 bindings."""

        try:
            document_projection = validate_document_projection(
                design_path.read_bytes(),
                {},
            )
            enacted_rows = document_projection["amendment15"][
                "mutation_bindings"
            ]
            enacted_projection = tuple(
                (
                    row["name"],
                    row["prepare"],
                    row["gate"],
                    row["expected_exception"],
                    row["expected_message"],
                )
                for row in enacted_rows
            )
        except Exception as error:
            raise PublicationError(
                "Amendment-15 enacted mutation binding specification could "
                f"not be verified: {type(error).__name__}: {error}"
            ) from error

        _require(
            all(
                type(value) is str
                for row in enacted_projection
                for value in row
            )
            and enacted_projection == fixed_projection,
            "Amendment-15 mutation binding specification drift",
        )
        enacted_names = tuple(row[0] for row in enacted_projection)
        _require(
            hashlib.sha256(
                a13.canonical_json_bytes(list(enacted_names))
            ).hexdigest()
            == mutation_domain_sha256,
            "Amendment-15 mutation binding name domain drift",
        )
        rejected = tuple(execute_mutation(row) for row in fixed_bindings)
        _require(
            rejected == enacted_names,
            "Amendment-15 rejected mutation census drift",
        )
        return rejected

    return fixed_bindings, run_amendment15_mutation_tests


A15_MUTATION_BINDINGS, run_amendment15_mutation_tests = (
    _create_amendment15_mutation_runner()
)
_run_amendment15_mutation_bindings = run_amendment15_mutation_tests
del _create_amendment15_mutation_runner


def validate_tier2_certification_contract(value: Mapping[str, Any]) -> None:
    """Execute all 100 attacks, then validate the bound certificate schema."""

    executed_census = run_complete_mutation_census()
    _validate_certification_top_level(value)
    _validate_certification_ratification(value["ratification_binding"])
    _validate_certification_source(value["source_build_identity"])
    _validate_certification_member(value["source_hierarchy_member_identity"])
    _validate_certification_reconstructions(
        value["reconstruction_rows"],
        value["source_hierarchy_member_identity"],
        value["source_build_identity"],
    )
    _validate_certification_gates(value["gate_results"])
    _validate_certification_git_attestation(value["git_order_attestation"])
    _validate_certification_lifecycle(value["lifecycle"])
    _validate_certification_mutation_census(
        value["mutation_census"],
        executed_census,
    )
    _validate_certification_integrity(value)


def validate_ceremony_merge_mode(
    requirement_codes: Sequence[str], merge_mode: str
) -> None:
    """Enforce the testable Amendment-15 merge-mode decision table."""

    codes = tuple(requirement_codes)
    ordered_known = (
        TOPOLOGY_BOUND_REQUIREMENT_CODES + BLOB_TREE_BOUND_REQUIREMENT_CODES
    )
    known = set(ordered_known)
    _require(codes, "ceremony merge-mode classification is empty")
    _require(
        len(codes) == len(set(codes)) and set(codes) <= known,
        "ceremony merge-mode classification is duplicate or unknown",
    )
    _require(
        codes == tuple(code for code in ordered_known if code in set(codes)),
        "ceremony merge-mode classification order drift",
    )
    _require(
        merge_mode in CEREMONY_MERGE_MODES,
        "ceremony merge mode is unknown or ancestry-rewriting",
    )
    if set(codes) & set(TOPOLOGY_BOUND_REQUIREMENT_CODES):
        _require(
            merge_mode == "no_fast_forward_merge_commit",
            "topology-bound ceremony requires a no-fast-forward merge commit",
        )
    if merge_mode == "squash":
        _require(
            set(codes) <= set(BLOB_TREE_BOUND_REQUIREMENT_CODES),
            "squash selected for a non-blob-bound ceremony",
        )


def overlay_relative_path(position: int) -> Path:
    """Return the fixed path for one exact document overlay."""

    return OVERLAY_DIRECTORY / (
        f"document_{position:03d}_repair_overlay_v1.json"
    )


def seal_relative_path(era_order_position: int) -> Path:
    """Return the fixed path for one exact successor-era seal."""

    return SEAL_DIRECTORY / (
        f"era_{era_order_position:02d}_successor_seal_v1.json"
    )


def _overlay_successors(overlay: Mapping[str, Any]) -> list[Any]:
    return [row for key in SUCCESSOR_DOMAINS for row in overlay[key]]


def _require_no_authority(value: Any, label: str) -> None:
    """Reject authority-like output anywhere in a published repair row."""

    if isinstance(value, Mapping):
        for key, member in value.items():
            if key == "authority_kind":
                _require(
                    member == "PROSPECTIVE_NONAUTHORITY",
                    f"{label} emits authority",
                )
            if key in {
                "authority_emitted",
                "certification_emitted",
                "q5_input_emitted",
                "production_output_emitted",
            }:
                _require(member is False, f"{label} emits forbidden output")
            _require_no_authority(member, label)
    elif isinstance(value, list):
        for member in value:
            _require_no_authority(member, label)


def validate_publication_law(law: Mapping[str, Any]) -> None:
    """Enforce the publication-level census and cross-file coherence."""

    _require(
        law["status"] == a13.RATIFICATION_BOUND_TEMPLATE_STATUS,
        "publication is not bound to the operative ratification closure",
    )
    _require(
        law["authority_emitted"] is False
        and law["certification_emitted"] is False,
        "execution law emits authority or certification",
    )
    integrity = law["integrity"]
    _require(
        (
            integrity["incompatible_proof_count"],
            integrity["incomplete_fragment_count"],
            integrity["composed_fragment_count"],
            integrity["doc036_aggregate_domain_count"],
            integrity["repair_count"],
            integrity["supersession_count"],
            integrity["overlay_count"],
            integrity["successor_era_seal_count"],
        )
        == (28, 8, 2, 8, 46, 46, 14, 6),
        "operative repair census is not 28 + 8 + 2 + 8 = 46",
    )

    overlays = law["repair_overlay_rows"]
    _require(
        tuple(row["document_source_position"] for row in overlays)
        == OVERLAY_POSITIONS,
        "repair overlay document domain or order drift",
    )
    counts_by_document = {
        row["document_source_position"]: len(_overlay_successors(row))
        for row in overlays
    }
    _require(
        counts_by_document == EXPECTED_REPAIR_COUNTS_BY_DOCUMENT,
        "per-document repair census drift",
    )
    all_successor_ids: list[str] = []
    all_supersession_successor_ids: list[str] = []
    for overlay in overlays:
        successors = _overlay_successors(overlay)
        edges = overlay["predecessor_supersession_rows"]
        _require(
            len(successors) == len(edges),
            "overlay does not contain one supersession edge per successor",
        )
        _require(
            overlay["predecessor_source_rows_retained"] is True
            and overlay["predecessor_source_row_erasure_permitted"] is False,
            "overlay violates append-only predecessor retention",
        )
        all_successor_ids.extend(row["successor_row_id"] for row in successors)
        all_supersession_successor_ids.extend(
            row["successor_row_id"] for row in edges
        )
        _require_no_authority(
            overlay,
            f"document {overlay['document_source_position']:03d} overlay",
        )
    _require(
        len(all_successor_ids) == 46
        and Counter(all_successor_ids)
        == Counter(all_supersession_successor_ids)
        == Counter({row_id: 1 for row_id in all_successor_ids}),
        "the overlays do not reconcile to 46 unique one-to-one repairs",
    )

    overlay_by_id = {row["repair_overlay_id"]: row for row in overlays}
    era_by_document_position = {
        row["document_source_position"]: row["predecessor_era_id"]
        for row in overlays
    }
    top_level_successors = [
        row for key in SUCCESSOR_DOMAINS for row in law[key]
    ]
    top_level_edges = law["predecessor_supersession_rows"]
    seals = law["successor_era_seal_rows"]
    _require(
        tuple(row["era_order_position"] for row in seals)
        == tuple(range(1, 7)),
        "successor-era seal domain or order drift",
    )
    _require(
        tuple(len(row["successor_row_ids"]) for row in seals)
        == EXPECTED_ERA_REPAIR_PROJECTION,
        "successor-era repair projection is not 8/5/9/19/5/0",
    )
    for seal in seals:
        era_id = seal["era_id"]
        era_overlays = [
            row for row in overlays if row["predecessor_era_id"] == era_id
        ]
        expected_overlay_ids = [
            row["repair_overlay_id"] for row in era_overlays
        ]
        expected_successor_ids = [
            row["successor_row_id"]
            for row in top_level_successors
            if era_by_document_position[row["document_source_position"]]
            == era_id
        ]
        expected_edge_ids = [
            row["supersession_row_id"]
            for row in top_level_edges
            if era_by_document_position[row["document_source_position"]]
            == era_id
        ]
        _require(
            seal["repair_overlay_ids"] == expected_overlay_ids
            and seal["successor_row_ids"] == expected_successor_ids
            and seal["supersession_row_ids"] == expected_edge_ids,
            f"era {seal['era_order_position']} seal projection drift",
        )
        _require(
            all(row_id in overlay_by_id for row_id in expected_overlay_ids),
            "successor-era seal references an unknown overlay",
        )
        _require_no_authority(
            seal, f"era {seal['era_order_position']} successor seal"
        )
    empty_era = seals[-1]
    _require(
        empty_era["repair_overlay_ids"] == []
        and empty_era["successor_row_ids"] == []
        and empty_era["supersession_row_ids"] == []
        and set(empty_era["repair_counts"].values()) == {0},
        "era 6 is not the enacted empty-but-sealed era",
    )


def build_artifact_values() -> (
    tuple[dict[str, Any], dict[Path, dict[str, Any]]]
):
    """Reconstruct and project the exact operative publication objects."""

    law = a13.build_ratification_bound_execution_template()
    validate_publication_law(law)
    values: dict[Path, dict[str, Any]] = {}
    for overlay in law["repair_overlay_rows"]:
        path = overlay_relative_path(overlay["document_source_position"])
        _require(path not in values, f"duplicate artifact path: {path}")
        values[path] = overlay
    for seal in law["successor_era_seal_rows"]:
        path = seal_relative_path(seal["era_order_position"])
        _require(path not in values, f"duplicate artifact path: {path}")
        values[path] = seal
    _require(len(values) == 20, "publication does not contain 20 artifacts")
    return law, values


def render_artifact_values(
    values: Mapping[Path, Mapping[str, Any]],
) -> dict[Path, bytes]:
    """Render exact rows with the execution law's canonical JSON codec."""

    return {
        path: a13.canonical_json_bytes(value) for path, value in values.items()
    }


def _selected_paths(values: Mapping[Path, Any], artifacts: str) -> set[Path]:
    _require(
        artifacts in ARTIFACT_SELECTIONS,
        f"unknown artifact selection: {artifacts}",
    )
    return {
        path
        for path in values
        if artifacts == "all"
        or (artifacts == "overlays" and path.parent == OVERLAY_DIRECTORY)
        or (artifacts == "seals" and path.parent == SEAL_DIRECTORY)
    }


def validate_artifact_bundle(
    actual: Mapping[Path, bytes],
    expected_values: Mapping[Path, Mapping[str, Any]],
    *,
    artifacts: str,
) -> None:
    """Require exact paths, strict canonical bytes, and deep equality."""

    expected_paths = _selected_paths(expected_values, artifacts)
    _require(
        set(actual) == expected_paths,
        f"{artifacts} artifact path domain drift",
    )
    for path in sorted(expected_paths):
        raw = actual[path]
        try:
            value = a13._strict_canonical_json(raw, path.as_posix())
        except a13.LawError as error:
            raise PublicationError(str(error)) from error
        _require(
            value == expected_values[path],
            f"{path.as_posix()} differs from the operative reconstruction",
        )
        _require(
            raw == a13.canonical_json_bytes(expected_values[path]),
            f"{path.as_posix()} has noncanonical or unequal bytes",
        )
        _require_no_authority(value, path.as_posix())


def read_artifact_bundle(
    output_root: Path,
    expected_values: Mapping[Path, Mapping[str, Any]],
    *,
    artifacts: str,
) -> dict[Path, bytes]:
    """Read exactly one selected artifact domain from disk."""

    selected = _selected_paths(expected_values, artifacts)
    directories = {path.parent for path in selected}
    actual: dict[Path, bytes] = {}
    for relative_directory in directories:
        directory = output_root / relative_directory
        if not directory.exists():
            continue
        _require(
            directory.is_dir(),
            f"artifact directory is not a directory: {directory}",
        )
        for candidate in directory.iterdir():
            _require(
                candidate.is_file() and not candidate.is_symlink(),
                f"unexpected non-file artifact entry: {candidate}",
            )
            actual[relative_directory / candidate.name] = (
                candidate.read_bytes()
            )
    return actual


def _require_no_unexpected_entries(
    output_root: Path,
    expected_values: Mapping[Path, Mapping[str, Any]],
    *,
    artifacts: str,
) -> None:
    selected = _selected_paths(expected_values, artifacts)
    expected_by_directory = {
        directory: {path.name for path in selected if path.parent == directory}
        for directory in {path.parent for path in selected}
    }
    for relative_directory, expected_names in expected_by_directory.items():
        directory = output_root / relative_directory
        if not directory.exists():
            continue
        _require(
            directory.is_dir(),
            f"artifact path is not a directory: {directory}",
        )
        actual_names = {entry.name for entry in directory.iterdir()}
        _require(
            actual_names <= expected_names,
            f"unexpected entries in {directory}",
        )


def write_artifact_bundle(
    output_root: Path,
    expected_values: Mapping[Path, Mapping[str, Any]],
    *,
    artifacts: str,
) -> dict[Path, bytes]:
    """Write one selected exact domain without deleting any artifact."""

    _require_no_unexpected_entries(
        output_root, expected_values, artifacts=artifacts
    )
    rendered = render_artifact_values(expected_values)
    selected = _selected_paths(expected_values, artifacts)
    for relative_path in sorted(selected):
        target = output_root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(rendered[relative_path])
    actual = read_artifact_bundle(
        output_root, expected_values, artifacts=artifacts
    )
    validate_artifact_bundle(actual, expected_values, artifacts=artifacts)
    return actual


def _run_git(
    repo_root: Path,
    *arguments: str,
) -> subprocess.CompletedProcess[bytes]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("GIT_")
    }
    environment["GIT_NO_REPLACE_OBJECTS"] = "1"
    return subprocess.run(
        ["git", "--no-replace-objects", *arguments],
        cwd=repo_root,
        check=False,
        capture_output=True,
        env=environment,
    )


def _git_output(repo_root: Path, *arguments: str) -> bytes:
    result = _run_git(repo_root, *arguments)
    _require(
        result.returncode == 0,
        f"git command failed: {' '.join(arguments)}",
    )
    return result.stdout


def _first_add_commits(
    repo_root: Path,
    relative_path: Path,
    *,
    revision: str = "HEAD",
) -> tuple[str, ...]:
    result = _run_git(
        repo_root,
        "log",
        "--full-history",
        "--diff-filter=A",
        "--format=%H",
        revision,
        "--",
        relative_path.as_posix(),
    )
    _require(
        result.returncode == 0, f"cannot inspect first-add for {relative_path}"
    )
    commits = tuple(result.stdout.decode("ascii").splitlines())
    _require(
        len(commits) <= 1,
        f"{relative_path.as_posix()} has more than one first-add commit",
    )
    _require(
        all(
            len(commit) == 40
            and all(character in "0123456789abcdef" for character in commit)
            for commit in commits
        ),
        f"{relative_path.as_posix()} has an invalid first-add commit",
    )
    return commits


def _first_add_commit(repo_root: Path, relative_path: Path) -> str | None:
    commits = _first_add_commits(repo_root, relative_path)
    return commits[0] if commits else None


def _require_exact_single_parent_commit(repo_root: Path, commit: str) -> str:
    resolved = (
        _git_output(repo_root, "rev-parse", "--verify", f"{commit}^{{commit}}")
        .decode("ascii")
        .strip()
    )
    _require(resolved == commit, f"{commit} is not an exact commit object")
    commit_line = (
        _git_output(repo_root, "rev-list", "--parents", "-n", "1", commit)
        .decode("ascii")
        .split()
    )
    _require(len(commit_line) == 2, f"{commit} is not a single-parent commit")
    return commit_line[1]


def _commit_tree(repo_root: Path, commit: str) -> str:
    return (
        _git_output(repo_root, "rev-parse", "--verify", f"{commit}^{{tree}}")
        .decode("ascii")
        .strip()
    )


def _changed_path_domain(
    repo_root: Path, commit: str
) -> tuple[tuple[str, str], ...]:
    raw = _git_output(
        repo_root,
        "diff-tree",
        "--no-commit-id",
        "--name-status",
        "-r",
        commit,
    )
    rows: list[tuple[str, str]] = []
    for line in raw.decode("utf-8").splitlines():
        fields = line.split("\t")
        _require(
            len(fields) == 2 and fields[0] in {"A", "M"},
            f"unsupported changed-path row at {commit}: {line}",
        )
        rows.append((fields[0], fields[1]))
    return tuple(sorted(rows))


def _validate_ordered_ceremony_attestation(
    *,
    repo_root: Path,
    attestation: Mapping[str, Any],
) -> dict[str, Any]:
    """Private injectable core for the ordered-history mutation tests."""

    _require(
        set(attestation)
        == {"remote_ref", "local_ref", "tree_oid", "squash_commit", "stages"},
        "ordered ceremony attestation keyset drift",
    )
    _require(
        attestation["remote_ref"] == ORDERED_CEREMONY_REMOTE_REF,
        "ordered ceremony remote ref identity drift",
    )
    _require(
        attestation["local_ref"] == ORDERED_CEREMONY_LOCAL_REF,
        "ordered ceremony local ref identity drift",
    )
    _require(
        attestation["tree_oid"] == ORDERED_CEREMONY_TREE_OID,
        "ordered ceremony tree identity drift",
    )
    _require(
        attestation["squash_commit"] == TIER2_SQUASH_COMMIT,
        "ordered ceremony squash identity drift",
    )
    path_domain_sha256 = hashlib.sha256(
        a13.canonical_json_bytes(
            sorted(path.as_posix() for path in ORDERED_ARTIFACT_COMMIT_BY_PATH)
        )
    ).hexdigest()
    _require(
        len(ORDERED_ARTIFACT_COMMIT_BY_PATH) == 22
        and path_domain_sha256 == ORDERED_ARTIFACT_PATH_DOMAIN_SHA256,
        "ordered ceremony artifact path domain drift",
    )

    ref_result = _run_git(
        repo_root,
        "show-ref",
        "--verify",
        "--hash",
        ORDERED_CEREMONY_LOCAL_REF,
    )
    _require(
        ref_result.returncode == 0,
        "ordered ceremony archive ref is absent or was not fetched",
    )
    ref_tip = ref_result.stdout.decode("ascii").strip()
    _require(
        ref_tip == ORDERED_CEREMONY_EVIDENCE_COMMIT,
        "ordered ceremony archive ref resolves to the wrong tip",
    )

    expected_stages = ORDERED_CEREMONY_ATTESTATION["stages"]
    stages = attestation["stages"]
    _require(
        isinstance(stages, (tuple, list)) and len(stages) == 4,
        "ordered ceremony stage domain drift",
    )
    resolved: dict[str, str] = {}
    for stage, expected in zip(stages, expected_stages, strict=True):
        _require(
            set(stage)
            == {"role", "commit", "parent", "tree_oid", "changed_paths"},
            "ordered ceremony stage keyset drift",
        )
        role = stage["role"]
        _require(role == expected["role"], "ordered ceremony role order drift")
        _require(
            stage["commit"] == expected["commit"],
            f"ordered ceremony {role} commit identity drift",
        )
        _require(
            stage["parent"] == expected["parent"],
            f"ordered ceremony {role} parent identity drift",
        )
        _require(
            stage["tree_oid"] == expected["tree_oid"],
            f"ordered ceremony {role} tree identity drift",
        )
        _require(
            tuple(stage["changed_paths"]) == expected["changed_paths"],
            f"ordered ceremony {role} changed-path attestation drift",
        )
        parent = _require_exact_single_parent_commit(
            repo_root, stage["commit"]
        )
        _require(
            parent == stage["parent"],
            f"ordered ceremony {role} actual parent drift",
        )
        _require(
            _commit_tree(repo_root, stage["commit"]) == stage["tree_oid"],
            f"ordered ceremony {role} actual tree drift",
        )
        _require(
            _changed_path_domain(repo_root, stage["commit"])
            == tuple(sorted(stage["changed_paths"])),
            f"ordered ceremony {role} actual changed-path domain drift",
        )
        resolved[role] = stage["commit"]

    ordered_pairs = (
        (resolved["receipt"], resolved["overlays"]),
        (resolved["overlays"], resolved["seals"]),
        (resolved["seals"], resolved["evidence"]),
    )
    _require(
        all(
            _is_strict_ancestor(repo_root, earlier, later)
            for earlier, later in ordered_pairs
        ),
        "ordered ceremony strict-ancestor chain drift",
    )

    squash_parent = _require_exact_single_parent_commit(
        repo_root, TIER2_SQUASH_COMMIT
    )
    _require(
        squash_parent == ORDERED_CEREMONY_BASE_COMMIT,
        "tier-2 squash parent identity drift",
    )
    _require(
        _changed_path_domain(repo_root, TIER2_SQUASH_COMMIT)
        == SQUASH_CHANGED_PATHS,
        "tier-2 squash changed-path domain drift",
    )
    _require(
        _commit_tree(repo_root, resolved["evidence"])
        == _commit_tree(repo_root, TIER2_SQUASH_COMMIT)
        == ORDERED_CEREMONY_TREE_OID,
        "ordered ceremony and squash tree identity mismatch",
    )

    for path, ordered_commit in ORDERED_ARTIFACT_COMMIT_BY_PATH.items():
        archive_adds = _first_add_commits(
            repo_root,
            path,
            revision=ORDERED_CEREMONY_LOCAL_REF,
        )
        _require(
            archive_adds == (ordered_commit,),
            f"ordered ceremony first-add drift for {path.as_posix()}",
        )
        head_adds = _first_add_commits(repo_root, path)
        _require(
            head_adds == (TIER2_SQUASH_COMMIT,),
            f"tier-2 squash exception is unavailable for {path.as_posix()}",
        )
        ordered_raw = _git_output(
            repo_root, "show", f"{ordered_commit}:{path.as_posix()}"
        )
        squash_raw = _git_output(
            repo_root, "show", f"{TIER2_SQUASH_COMMIT}:{path.as_posix()}"
        )
        head_raw = _git_output(repo_root, "show", f"HEAD:{path.as_posix()}")
        _require(
            ordered_raw == squash_raw == head_raw,
            f"ordered/squash/HEAD blob mismatch for {path.as_posix()}",
        )
        expected_tree_entry = (
            f"100644 blob {a13._git_blob_oid(ordered_raw)}\t{path.as_posix()}"
        )
        for revision in (ordered_commit, TIER2_SQUASH_COMMIT, "HEAD"):
            actual_tree_entry = (
                _git_output(
                    repo_root,
                    "ls-tree",
                    revision,
                    "--",
                    path.as_posix(),
                )
                .decode("utf-8")
                .strip()
            )
            _require(
                actual_tree_entry == expected_tree_entry,
                f"ordered artifact mode/blob drift at {revision}: "
                f"{path.as_posix()}",
            )

    return {
        "archive_ref": ORDERED_CEREMONY_LOCAL_REF,
        "archive_tip_commit": ref_tip,
        "tree_oid": ORDERED_CEREMONY_TREE_OID,
        "squash_commit": TIER2_SQUASH_COMMIT,
        "stage_commits": resolved,
    }


def validate_ordered_ceremony_attestation(
    *, repo_root: Path = ROOT
) -> dict[str, Any]:
    """Authenticate only the enacted archived tier-2 ceremony."""

    return _validate_ordered_ceremony_attestation(
        repo_root=repo_root,
        attestation=ORDERED_CEREMONY_ATTESTATION,
    )


def _attested_order_commit_for_squashed_first_add(
    relative_path: Path,
    observed_first_add: str,
    attestation: Mapping[str, Any],
) -> str:
    """Map one exact collapsed artifact to its archived ordering event."""

    _require(
        relative_path in ORDERED_ARTIFACT_COMMIT_BY_PATH,
        f"path cannot reuse the tier-2 squash exception: {relative_path}",
    )
    _require(
        observed_first_add == TIER2_SQUASH_COMMIT,
        f"tier-2 squash exception commit drift for {relative_path}",
    )
    expected = ORDERED_ARTIFACT_COMMIT_BY_PATH[relative_path]
    _require(
        expected in attestation["stage_commits"].values(),
        f"ordered ceremony does not bind {relative_path}",
    )
    return expected


def _is_strict_ancestor(
    repo_root: Path, ancestor: str, descendant: str
) -> bool:
    if ancestor == descendant:
        return False
    result = _run_git(
        repo_root, "merge-base", "--is-ancestor", ancestor, descendant
    )
    _require(
        result.returncode in {0, 1},
        "git could not evaluate strict commit ancestry",
    )
    return result.returncode == 0


def _validate_first_add_relationships(
    *,
    governing_commit: str,
    overlay_commits: Mapping[int, str | None],
    seal_commits: Mapping[int, str | None],
    overlay_era_positions: Mapping[int, int],
    strict_ancestor: Callable[[str, str], bool],
    required: str = "none",
) -> str:
    """Validate the enacted commit ordering from resolved first-adds."""

    _require(required in {"none", "overlays", "all"}, "invalid required stage")
    present_overlays = {value for value in overlay_commits.values() if value}
    present_seals = {value for value in seal_commits.values() if value}
    if present_overlays:
        _require(
            all(overlay_commits.values()) and len(present_overlays) == 1,
            "the fourteen overlays are not one complete first-add batch",
        )
        overlay_commit = next(iter(present_overlays))
        _require(
            strict_ancestor(governing_commit, overlay_commit),
            "the governing Amendment-13 ratification is not a strict ancestor "
            "of the overlay first-add batch",
        )
    if present_seals:
        _require(
            all(seal_commits.values()) and len(present_seals) == 1,
            "the six seals are not one complete first-add batch",
        )
        _require(
            all(overlay_commits.values()),
            "a seal was first-added before every overlay",
        )
        for position, overlay_commit in overlay_commits.items():
            seal_commit = seal_commits[overlay_era_positions[position]]
            _require(
                overlay_commit is not None
                and seal_commit is not None
                and strict_ancestor(overlay_commit, seal_commit),
                "an overlay first-add is not a strict ancestor of its era seal",
            )
    if required in {"overlays", "all"}:
        _require(
            all(overlay_commits.values()), "overlay batch is not committed"
        )
    if required == "all":
        _require(all(seal_commits.values()), "seal batch is not committed")
    if present_seals:
        return "seals_committed"
    if present_overlays:
        return "overlays_committed"
    return "prospective"


def validate_git_publication_order(
    law: Mapping[str, Any],
    expected_values: Mapping[Path, Mapping[str, Any]],
    *,
    repo_root: Path = ROOT,
    required: str = "none",
) -> dict[str, Any]:
    """Validate first-add bytes, commit shape, and strict ancestry."""

    governing_commit = law["governing_amendment13_ratification_identity"][
        "ratification_commit"
    ]
    overlay_commits: dict[int, str | None] = {}
    seal_commits: dict[int, str | None] = {}
    overlay_era_positions: dict[int, int] = {}
    era_position_by_id = {
        row["era_id"]: row["era_order_position"]
        for row in law["successor_era_seal_rows"]
    }
    for overlay in law["repair_overlay_rows"]:
        position = overlay["document_source_position"]
        path = TIER2_ROOT_RELATIVE / overlay_relative_path(position)
        overlay_commits[position] = _first_add_commit(repo_root, path)
        overlay_era_positions[position] = era_position_by_id[
            overlay["predecessor_era_id"]
        ]
    for seal in law["successor_era_seal_rows"]:
        era_position = seal["era_order_position"]
        path = TIER2_ROOT_RELATIVE / seal_relative_path(era_position)
        seal_commits[era_position] = _first_add_commit(repo_root, path)

    path_commit_pairs = [
        (
            TIER2_ROOT_RELATIVE / overlay_relative_path(position),
            commit,
        )
        for position, commit in overlay_commits.items()
    ] + [
        (TIER2_ROOT_RELATIVE / seal_relative_path(position), commit)
        for position, commit in seal_commits.items()
    ]
    for path, commit in path_commit_pairs:
        if commit is None:
            continue
        _require_exact_single_parent_commit(repo_root, commit)
        relative_to_tier2 = path.relative_to(TIER2_ROOT_RELATIVE)
        expected_raw = a13.canonical_json_bytes(
            expected_values[relative_to_tier2]
        )
        first_add_raw = _git_output(
            repo_root, "show", f"{commit}:{path.as_posix()}"
        )
        head_raw = _git_output(repo_root, "show", f"HEAD:{path.as_posix()}")
        _require(
            first_add_raw == expected_raw and head_raw == expected_raw,
            f"{path.as_posix()} differs at first-add or HEAD",
        )

    attested_history: dict[str, Any] | None = None
    order_overlay_commits = dict(overlay_commits)
    order_seal_commits = dict(seal_commits)
    observed_commits = {
        commit
        for commit in (*overlay_commits.values(), *seal_commits.values())
        if commit is not None
    }
    if observed_commits == {TIER2_SQUASH_COMMIT}:
        attested_history = validate_ordered_ceremony_attestation(
            repo_root=repo_root
        )
        order_overlay_commits = {
            position: (
                _attested_order_commit_for_squashed_first_add(
                    TIER2_ROOT_RELATIVE / overlay_relative_path(position),
                    commit,
                    attested_history,
                )
                if commit is not None
                else None
            )
            for position, commit in overlay_commits.items()
        }
        order_seal_commits = {
            position: (
                _attested_order_commit_for_squashed_first_add(
                    TIER2_ROOT_RELATIVE / seal_relative_path(position),
                    commit,
                    attested_history,
                )
                if commit is not None
                else None
            )
            for position, commit in seal_commits.items()
        }
    else:
        _require(
            TIER2_SQUASH_COMMIT not in observed_commits,
            "partial reuse of the tier-2 squash exception",
        )

    status = _validate_first_add_relationships(
        governing_commit=governing_commit,
        overlay_commits=order_overlay_commits,
        seal_commits=order_seal_commits,
        overlay_era_positions=overlay_era_positions,
        strict_ancestor=lambda ancestor, descendant: _is_strict_ancestor(
            repo_root, ancestor, descendant
        ),
        required=required,
    )
    return {
        "status": status,
        "governing_amendment13_ratification_commit": governing_commit,
        "overlay_first_add_commits": overlay_commits,
        "seal_first_add_commits": seal_commits,
        "ordering_basis": (
            "ordered_ceremony_branch_attestation_v1"
            if attested_history is not None
            else "live_head_first_adds"
        ),
        "attested_overlay_order_commit": (
            attested_history["stage_commits"]["overlays"]
            if attested_history is not None
            else None
        ),
        "attested_seal_order_commit": (
            attested_history["stage_commits"]["seals"]
            if attested_history is not None
            else None
        ),
        "attested_evidence_order_commit": (
            attested_history["stage_commits"]["evidence"]
            if attested_history is not None
            else None
        ),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifacts",
        choices=ARTIFACT_SELECTIONS,
        default="all",
        help="artifact domain to write or check (default: all)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare existing artifacts instead of writing them",
    )
    parser.add_argument(
        "--require-committed",
        action="store_true",
        help="also require the selected first-add batch(es) in HEAD",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=TIER2_ROOT,
        help="artifact root (default: the committed tier-2 directory)",
    )
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    parser = _parser()
    options = parser.parse_args(arguments)
    output_root = options.output_root.resolve()
    is_repository_publication = output_root == TIER2_ROOT.resolve()
    if options.require_committed and not is_repository_publication:
        parser.error("--require-committed requires the repository output root")

    try:
        law, expected_values = build_artifact_values()
        required = "none"
        if options.require_committed:
            required = "overlays" if options.artifacts == "overlays" else "all"
        if options.artifacts == "seals" and not options.require_committed:
            required = "overlays"
        if is_repository_publication:
            order = validate_git_publication_order(
                law,
                expected_values,
                required=(
                    "overlays"
                    if not options.check and options.artifacts == "all"
                    else required
                ),
            )
        else:
            order = {"status": "external_output_root_not_git_checked"}

        if options.check:
            actual = read_artifact_bundle(
                output_root,
                expected_values,
                artifacts=options.artifacts,
            )
            validate_artifact_bundle(
                actual,
                expected_values,
                artifacts=options.artifacts,
            )
        else:
            if options.require_committed:
                raise PublicationError(
                    "--require-committed is only meaningful with --check"
                )
            if options.artifacts in {"seals", "all"}:
                _require(
                    order["status"]
                    in {"overlays_committed", "seals_committed"},
                    "commit the complete overlay batch before writing seals",
                )
            actual = write_artifact_bundle(
                output_root,
                expected_values,
                artifacts=options.artifacts,
            )
        print(
            json.dumps(
                {
                    "status": "PASS",
                    "mode": "check" if options.check else "write",
                    "artifacts": options.artifacts,
                    "artifact_count": len(actual),
                    "repair_count": 46,
                    "supersession_count": 46,
                    "era_projection": list(EXPECTED_ERA_REPAIR_PROJECTION),
                    "git_publication_status": order["status"],
                    "authority_emitted": False,
                    "certification_emitted": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
    except PublicationError as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
