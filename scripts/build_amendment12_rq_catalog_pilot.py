#!/usr/bin/env python3
"""Build Amendment 12's nonauthority R_Q catalog-law pilot artifacts.

The source corpus is the exact Git tree at ``SOURCE_COMMIT``.  This builder
reads the six pinned era seals first, verifies every selected annotation blob
against the identities carried by those seals, and adapts the three sealed
stage-2 handoff shapes without changing source text.  It emits only pilot and
targeted-sweep evidence.  It never emits Q5, a global catalog, R_Q, hierarchy,
slot, inventory, registry, receipt, or production authority.
"""

from __future__ import annotations

import argparse
import copy
import decimal
import hashlib
import json
import math
import os
import subprocess
import tempfile
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "docs" / "analysis" / "amendment_12_rq_catalog_pilot"
DESIGN_PATH = ROOT / "docs" / "design" / "covered_earnings_correction.md"

SOURCE_COMMIT = "19fa24c161e800e004320f0c10e81bce8831af68"
SOURCE_BRANCH_LABEL = "claude/ce-global-q5-extraction"
DESIGN_PREFIX_BYTES = 3_557_513
DESIGN_PREFIX_SHA256 = (
    "b06e64e314645300458b6e1c72df23c9bd5090b376f676d1e492312135782d87"
)
CANONICALIZATION = "python-json-sort-keys-compact-ascii-no-nan-lf-v1"
PINNED_SWEEP_DOMAIN_SHA256 = {
    "role_exact_label_class": (
        "9c2f36a9a4cdc9fde3d790b71498234efde5b17235b9a5023ca4c772ad633e8d"
    ),
    "outside_domain_repeat_shape": (
        "baf5475e21ef404b911a7d7ec6328771caa01961d185f684a3ed63c4fdd8c48a"
    ),
    "component_parent_shape_keyset": (
        "b1aaad10fac7e3a6eb35edabd99c079137404109f0b912f8726446965a1d0524"
    ),
    "component_parent_shape": (
        "22506ce5d02d6ceee9fc1a51aee25949c5b91cf218355396910ebe8faf53c7a0"
    ),
    "parent_source_witness_keyset": (
        "e6cc0d564a407a3375975c5522180ad6ec871b3fdd410680b31690f7b24651a9"
    ),
    "parent_source_witness": (
        "a89a54310e86cd3d08c40d9fb9cedc9f25dd0069780ecc4e94f8ef596843ebd1"
    ),
}

ROLE_HEAD = "head_or_reference_person"
ROLE_SPOUSE = "spouse_or_partner"
ROLE_ORDER = (ROLE_HEAD, ROLE_SPOUSE)
ROLE_CANONICALS = {
    ROLE_HEAD: (
        "psid-questionnaire-occurrence:"
        "4226e8c05e9d4cb91c5a1586731d6815c96268cadaebf51b2733c3daf499eda4"
    ),
    ROLE_SPOUSE: (
        "psid-questionnaire-occurrence:"
        "b59425917fcfdf5d07adbb4341b86cb4d57d161d3de5fffa5c8338bc16ca63a1"
    ),
}

COMPONENT_KINDS = (
    "source_context",
    "source_remuneration_component",
)
AGGREGATE_CLASSIFICATIONS = (
    "source_role_total",
    "source_farm_aggregate",
    "source_business_aggregate",
)
AGGREGATE_OCCURRENCE_KINDS = (
    "role_total_anchor",
    "farm_aggregate_anchor",
    "business_aggregate_anchor",
)
AGGREGATE_CLASSIFICATION_TO_KIND = {
    "source_role_total": "role_total_anchor",
    "source_farm_aggregate": "farm_aggregate_anchor",
    "source_business_aggregate": "business_aggregate_anchor",
}
ALLOWED_REPEAT_RELATIONS = (
    "explicit_repeat_instruction",
    "explicit_cross_reference",
)
ALLOWED_LOCAL_EVIDENCE_RELATIONS = (
    *ALLOWED_REPEAT_RELATIONS,
    "same_printed_identifier_and_exact_label",
)

PARENT_KIND_TO_CATEGORY = {
    "job_anchor": "source_job",
    "role_total_anchor": "role_total_sentinel",
    "farm_aggregate_anchor": "farm_aggregate_sentinel",
    "business_aggregate_anchor": "business_aggregate_sentinel",
}
INELIGIBLE_PARENT_CATEGORY = {
    "role_anchor": "ineligible_role_anchor",
    "context_anchor": "ineligible_context_anchor",
    "remuneration_component_anchor": (
        "ineligible_remuneration_component_anchor"
    ),
}

PILOT_POSITIONS = (
    1,
    2,
    3,
    9,
    14,
    18,
    23,
    33,
    36,
    40,
    53,
    56,
    58,
    65,
    66,
    78,
)
CONTROL_POSITIONS = (3, 18, 23, 53, 65, 78)
PILOT_TAGS = {
    1: ("role_canonical_and_J8_head_witness",),
    2: ("null_identifier_she_role_witness",),
    3: ("era_1_control",),
    9: ("zero_parent_component_witness",),
    14: ("q74_outside_domain_repeat_carrier",),
    18: ("era_2_control",),
    23: ("era_3_control",),
    33: ("multi_parent_component_witness",),
    36: ("aggregate_as_component_slot_seal_defect",),
    40: ("q87_outside_domain_repeat_carrier",),
    53: ("era_4_local_edge_schema_control",),
    56: ("fam1996_outside_domain_repeat_carrier",),
    58: ("fam1997_outside_domain_repeat_carrier",),
    65: ("era_5_control",),
    66: ("fam2005_outside_domain_repeat_carrier",),
    78: ("era_6_control",),
}

ERA_SEALS = (
    {
        "era_id": "wave1968_ry1968_1974_early_totals",
        "era_order_position": 1,
        "positions": tuple(range(1, 17)),
        "seal_commit": "a75151c42e4612a92de7946e2dbc835914f1bb0d",
        "path": (
            "docs/analysis/rq_stage3_era_seals/"
            "wave1968_ry1968_1974_early_totals_preparation_seal_v1.json"
        ),
        "byte_size": 14_480,
        "raw_sha256": (
            "bcc3c542bc7e8410e025e4a3aa23ea0bb42da5b579d0c4d346746a9632911a44"
        ),
        "content_sha256": (
            "b07906b0a0f62b2be2a0e3f5d68c5b10bd6f1b1d51d8b13d747603b47980d69a"
        ),
    },
    {
        "era_id": "ry1975_1977_spouse_concept_seam",
        "era_order_position": 2,
        "positions": tuple(range(17, 23)),
        "seal_commit": "9758ca7c013b144eb319ffe97f75b5817670603f",
        "path": (
            "docs/analysis/rq_stage3_era_seals/"
            "ry1975_1977_spouse_concept_seam_preparation_seal_v1.json"
        ),
        "byte_size": 7_883,
        "raw_sha256": (
            "5a954d5148706378df938231378a81af8f3412024e86c0ee9b1a4aec52f423aa"
        ),
        "content_sha256": (
            "3ac7136e2c8917b6ea0e1321f4a9f2dc6d8305d01f998d2bc4eddb009361413c"
        ),
    },
    {
        "era_id": "ry1978_1992_pre_er_totals",
        "era_order_position": 3,
        "positions": tuple(range(23, 52)),
        "seal_commit": "e06dd4498dfc7a3b2a2f259f4da2977bea94b949",
        "path": (
            "docs/analysis/rq_stage3_era_seals/"
            "ry1978_1992_pre_er_totals_preparation_seal_v1.json"
        ),
        "byte_size": 23_106,
        "raw_sha256": (
            "59ae2e095e079b16b91c1cf5138803939f7b65f951e3fff6b4f789d428c1dde2"
        ),
        "content_sha256": (
            "f1a80b78800acb7ce8e53f3db8422a9ccaad88673c924ae03420045201be0ee7"
        ),
    },
    {
        "era_id": "ry1993_2001_er_transition",
        "era_order_position": 4,
        "positions": tuple(range(52, 64)),
        "seal_commit": "b5dc849d8f82f54b46697808444517f26e4015c6",
        "path": (
            "docs/analysis/rq_stage3_era_seals/"
            "ry1993_2001_er_transition_preparation_seal_v1.json"
        ),
        "byte_size": 11_863,
        "raw_sha256": (
            "a58044964bea7bef6c71b28f5f408f658da17eb18e1563c213d4102c84654e9e"
        ),
        "content_sha256": (
            "a4d07990c2066e1e8362dc5339c5fca21bd5b96534781c5a8fe08e7a1dd4a291"
        ),
    },
    {
        "era_id": "ry2002_2014_modern_bc_de",
        "era_order_position": 5,
        "positions": tuple(range(64, 78)),
        "seal_commit": "872a27878a8beaab22c9871775416396ac3425d5",
        "path": (
            "docs/analysis/rq_stage3_era_seals/"
            "ry2002_2014_modern_bc_de_preparation_seal_v1.json"
        ),
        "byte_size": 13_171,
        "raw_sha256": (
            "221c28d010cb92a4566910515a9cbd0b342503452de9b9c8e1c223b6bf06cdc1"
        ),
        "content_sha256": (
            "c180fd79d9b89b5018d883ae0e4835913e994e5c11d2645ae1af63b8721c6a18"
        ),
    },
    {
        "era_id": "ry2015_2022_exclusion_lineage",
        "era_order_position": 6,
        "positions": tuple(range(78, 82)),
        "seal_commit": SOURCE_COMMIT,
        "path": (
            "docs/analysis/rq_stage3_era_seals/"
            "ry2015_2022_exclusion_lineage_preparation_seal_v1.json"
        ),
        "byte_size": 6_574,
        "raw_sha256": (
            "3238516e70d8283fa7172308432e5bb1b4f710a06c758bdb51618aca627b1bd9"
        ),
        "content_sha256": (
            "cc38de5e0875f054a97b9b0c93d4a215d4b5616758e04fb58b6b55f91686c7e6"
        ),
    },
)

OUTPUT_FILENAMES = {
    "slice": "pilot_slice_manifest_v1.json",
    "sweeps": "corpus_exhaustive_targeted_sweeps_v1.json",
    "predecessor": "predecessor_defect_adjudication_v1.json",
    "role": "role_assignment_pilot_v1.json",
    "repeat": "outside_domain_repeat_disposition_pilot_v1.json",
    "component": "component_parent_disposition_pilot_v1.json",
    "gate": "pilot_gate_result_v1.json",
}


class BuildError(RuntimeError):
    """Raised when a source or artifact law fails closed."""


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    """Return the campaign's terminal-LF canonical strict JSON bytes."""
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("ascii")


def _reject_constant(value: str) -> None:
    raise BuildError(f"non-finite JSON constant: {value}")


def _finite_exact_float(token: str) -> float:
    value = float(token)
    if not math.isfinite(value):
        raise BuildError(f"non-finite JSON number: {token}")
    if decimal.Decimal(token) != decimal.Decimal(str(value)):
        raise BuildError(f"inexact JSON number: {token}")
    return value


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BuildError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_json_loads(raw: bytes, label: str) -> Any:
    """Parse one UTF-8 strict JSON value and reject duplicate members."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise BuildError(f"{label}: invalid UTF-8") from error
    try:
        if text.startswith("\ufeff"):
            raise BuildError(f"{label}: leading BOM")
        return json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
            parse_float=_finite_exact_float,
        )
    except (
        BuildError,
        json.JSONDecodeError,
        OverflowError,
        RecursionError,
        decimal.DecimalException,
    ) as error:
        raise BuildError(f"{label}: invalid strict JSON") from error


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise BuildError(message)


def _require_int(value: Any, label: str) -> int:
    _require(
        isinstance(value, int) and not isinstance(value, bool),
        f"{label}: expected JSON integer",
    )
    return value


def _require_exact_keys(
    value: Mapping[str, Any],
    expected: frozenset[str],
    label: str,
) -> None:
    actual = frozenset(value)
    _require(
        actual == expected,
        f"{label}: keyset drift; missing={sorted(expected - actual)!r}, "
        f"extra={sorted(actual - expected)!r}",
    )


def _row_id(prefix: str, preimage: Sequence[Any]) -> str:
    return prefix + _sha256(canonical_bytes(list(preimage)))


def _domain_sha(rows: Sequence[Any]) -> str:
    return _sha256(canonical_bytes(list(rows)))


def _keyset_sha(ids: Sequence[str]) -> str:
    return _sha256(canonical_bytes(list(ids)))


def _artifact(
    schema_version: str,
    id_prefix: str,
    authority_kind: str,
    body: Mapping[str, Any],
) -> dict[str, Any]:
    payload = {
        "schema_version": schema_version,
        "authority_kind": authority_kind,
        **copy.deepcopy(dict(body)),
    }
    payload_sha = _sha256(canonical_bytes(payload))
    return {
        "schema_version": schema_version,
        "artifact_id": id_prefix + payload_sha,
        "authority_kind": authority_kind,
        **copy.deepcopy(dict(body)),
        "integrity": {
            "canonicalization": CANONICALIZATION,
            "payload_sha256": payload_sha,
        },
    }


def _validate_artifact_envelope(
    artifact: Mapping[str, Any],
    schema_version: str,
    id_prefix: str,
    authority_kind: str,
) -> None:
    _require(artifact.get("schema_version") == schema_version, "bad schema")
    _require(
        artifact.get("authority_kind") == authority_kind,
        "bad authority_kind",
    )
    artifact_id = artifact.get("artifact_id")
    _require(
        isinstance(artifact_id, str) and artifact_id.startswith(id_prefix),
        "bad artifact_id",
    )
    integrity = artifact.get("integrity")
    _require(isinstance(integrity, dict), "missing integrity")
    _require(
        integrity.get("canonicalization") == CANONICALIZATION,
        "bad canonicalization",
    )
    payload = {
        key: copy.deepcopy(value)
        for key, value in artifact.items()
        if key not in {"artifact_id", "integrity"}
    }
    digest = _sha256(canonical_bytes(payload))
    _require(integrity.get("payload_sha256") == digest, "bad payload hash")
    _require(artifact_id == id_prefix + digest, "bad artifact ID digest")


def _nonauthority_statement() -> dict[str, Any]:
    return {
        "authority_admitted": False,
        "catalog_certified": False,
        "global_catalog_emitted": False,
        "hierarchy_emitted": False,
        "inventory_emitted": False,
        "legal_registry_emitted": False,
        "pilot_only": True,
        "q5_emitted": False,
        "r_q_emitted": False,
        "slot_emitted": False,
        "status": "PILOT_NONAUTHORITY",
        "wall_row_emitted": False,
    }


def _validate_design_prefix() -> dict[str, Any]:
    raw = DESIGN_PATH.read_bytes()
    _require(
        len(raw) >= DESIGN_PREFIX_BYTES,
        "revision-13 design prefix is truncated",
    )
    prefix = raw[:DESIGN_PREFIX_BYTES]
    _require(
        _sha256(prefix) == DESIGN_PREFIX_SHA256,
        "revision-13 design prefix drifted",
    )
    return {
        "path": "docs/design/covered_earnings_correction.md",
        "byte_size": DESIGN_PREFIX_BYTES,
        "sha256": DESIGN_PREFIX_SHA256,
        "identity_scope": "immutable_revision_13_prefix",
    }


class SourceReader:
    """Read exact files from either the pinned Git tree or a verified root."""

    def __init__(self, source_root: Path | None) -> None:
        self.source_root = source_root.resolve() if source_root else None
        if self.source_root is None:
            command = ["git", "cat-file", "-e", f"{SOURCE_COMMIT}^{{commit}}"]
            result = subprocess.run(
                command,
                cwd=ROOT,
                check=False,
                capture_output=True,
            )
            _require(
                result.returncode == 0,
                f"pinned source commit unavailable: {SOURCE_COMMIT}",
            )
        else:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.source_root,
                check=True,
                capture_output=True,
                text=True,
            )
            _require(
                result.stdout.strip() == SOURCE_COMMIT,
                "source root is not at the pinned corpus commit",
            )

    def read(self, path: str) -> bytes:
        if self.source_root is not None:
            candidate = (self.source_root / path).resolve()
            _require(
                candidate.is_relative_to(self.source_root),
                f"source path escaped root: {path}",
            )
            return candidate.read_bytes()
        result = subprocess.run(
            ["git", "show", f"{SOURCE_COMMIT}:{path}"],
            cwd=ROOT,
            check=False,
            capture_output=True,
        )
        _require(result.returncode == 0, f"missing pinned source path: {path}")
        return result.stdout


@dataclass(frozen=True)
class NormalizedDocument:
    position: int
    era_id: str
    annotation_path: str
    annotation_identity: dict[str, Any]
    source_document_id: str
    schema_version: str
    page_count: int
    occurrence_count: int
    flow_count: int
    field_purpose_count: int
    repeat_occurrence_ids: tuple[str, ...]
    anchor_rows: tuple[dict[str, Any], ...]
    evidence_rows: tuple[dict[str, Any], ...]


def _classification(row: Mapping[str, Any]) -> str:
    value = row.get("classification", row.get("local_classification"))
    _require(isinstance(value, str) and value, "missing classification")
    return value


def _evidence_id(row: Mapping[str, Any]) -> str:
    for key in (
        "local_repeat_alias_evidence_id",
        "local_repeat_evidence_id",
        "local_repeat_or_alias_evidence_id",
    ):
        value = row.get(key)
        if value is not None:
            _require(isinstance(value, str) and value, "bad evidence ID")
            return value
    raise BuildError("missing local evidence ID")


def _evidence_relation(row: Mapping[str, Any]) -> str:
    value = row.get("relation", row.get("alias_relation"))
    _require(value in ALLOWED_LOCAL_EVIDENCE_RELATIONS, "bad repeat relation")
    return value


def _endpoint_ids(
    row: Mapping[str, Any],
    local_id_to_occurrence: Mapping[str, str],
) -> tuple[list[str], list[str]]:
    if "alias_anchor_source_occurrence_ids" in row:
        return (
            list(row["alias_anchor_source_occurrence_ids"]),
            list(row["canonical_anchor_source_occurrence_ids"]),
        )
    if "alias_anchor_occurrence_id" in row:
        alias = row["alias_anchor_occurrence_id"]
        canonical = row["referenced_anchor_occurrence_id"]
        return (
            [] if alias is None else [alias],
            [] if canonical is None else [canonical],
        )
    alias_local = row["alias_local_anchor_id"]
    canonical_local = row["canonical_local_anchor_id"]
    return (
        [] if alias_local is None else [local_id_to_occurrence[alias_local]],
        (
            []
            if canonical_local is None
            else [local_id_to_occurrence[canonical_local]]
        ),
    )


def _source_instruction_ids(row: Mapping[str, Any]) -> list[str]:
    if "source_instruction_occurrence_ids" in row:
        return list(row["source_instruction_occurrence_ids"])
    value = row.get("source_occurrence_id")
    return [] if value is None else [value]


def _occurrence_catalog_domain(kind: str) -> str:
    if kind == "role_anchor":
        return "role"
    if kind == "job_anchor":
        return "job_slot"
    if kind in {"context_anchor", "remuneration_component_anchor"}:
        return "component_slot"
    if kind in AGGREGATE_OCCURRENCE_KINDS:
        return "aggregate"
    return f"outside_catalog:{kind}"


def _normalize_document(
    raw: bytes,
    input_identity: Mapping[str, Any],
    era_id: str,
) -> NormalizedDocument:
    path = input_identity["annotation_path"]
    _require(len(raw) == input_identity["byte_size"], f"{path}: size drift")
    _require(
        _sha256(raw) == input_identity["raw_sha256"],
        f"{path}: raw SHA-256 drift",
    )
    data = strict_json_loads(raw, path)
    _require(isinstance(data, dict), f"{path}: top level is not object")
    position = _require_int(data.get("document_source_position"), path)
    _require(
        position == input_identity["document_source_position"],
        f"{path}: source position drift",
    )
    _require(
        data.get("schema_version") == input_identity["schema_version"],
        f"{path}: schema drift",
    )
    _require(
        data.get("artifact_id") == input_identity["artifact_id"],
        f"{path}: artifact ID drift",
    )
    source_row = data["document_source_row"]
    source_document_id = source_row["source_document_id"]
    _require(
        source_document_id == input_identity["source_document_id"],
        f"{path}: source document drift",
    )

    occurrences = data["questionnaire_occurrence_rows"]
    occurrence_by_id = {
        row["questionnaire_occurrence_id"]: row for row in occurrences
    }
    _require(
        len(occurrence_by_id) == len(occurrences),
        f"{path}: duplicate occurrence ID",
    )
    anchors = data["local_anchor_classification_rows"]
    local_id_to_occurrence = {
        row["local_anchor_classification_id"]: row["source_occurrence_id"]
        for row in anchors
    }
    _require(
        len(local_id_to_occurrence) == len(anchors),
        f"{path}: duplicate local anchor ID",
    )

    normalized_anchors: list[dict[str, Any]] = []
    anchor_by_occurrence: dict[str, dict[str, Any]] = {}
    for source_row_index, row in enumerate(anchors):
        occurrence_id = row["source_occurrence_id"]
        _require(
            occurrence_id in occurrence_by_id,
            f"{path}: anchor occurrence is missing",
        )
        occurrence = occurrence_by_id[occurrence_id]
        raw_parent_ids = row.get(
            "parent_source_occurrence_ids",
            row.get(
                "parent_anchor_occurrence_ids",
                row.get("parent_local_anchor_ids", []),
            ),
        )
        parent_ids = [
            local_id_to_occurrence.get(parent_id, parent_id)
            for parent_id in raw_parent_ids
        ]
        for parent_id in parent_ids:
            _require(
                parent_id in occurrence_by_id,
                f"{path}: parent occurrence is missing",
            )
        normalized = {
            "source_row_index": source_row_index,
            "local_anchor_classification_id": row[
                "local_anchor_classification_id"
            ],
            "source_occurrence_id": occurrence_id,
            "node_domain": row["node_domain"],
            "classification": _classification(row),
            "occurrence_kind": occurrence["occurrence_kind"],
            "printed_identifier": row.get("printed_identifier"),
            "exact_label": row.get("exact_label"),
            "exact_label_sha256": row.get("exact_label_sha256"),
            "occurrence_matched_text": occurrence["matched_text"],
            "occurrence_matched_utf8_sha256": occurrence[
                "matched_utf8_sha256"
            ],
            "parent_occurrence_ids": parent_ids,
            "parent_occurrence_kinds": [
                occurrence_by_id[parent_id]["occurrence_kind"]
                for parent_id in parent_ids
            ],
        }
        _require(
            occurrence_id not in anchor_by_occurrence,
            f"{path}: occurrence has duplicate anchor classification",
        )
        normalized_anchors.append(normalized)
        anchor_by_occurrence[occurrence_id] = normalized

    evidence_input = data.get(
        "local_repeat_alias_evidence_rows",
        data.get("local_repeat_or_alias_evidence_rows", []),
    )
    normalized_evidence: list[dict[str, Any]] = []
    for source_row_index, row in enumerate(evidence_input):
        aliases, canonicals = _endpoint_ids(row, local_id_to_occurrence)
        endpoint_ids = [*aliases, *canonicals]
        endpoint_rows = [
            anchor_by_occurrence.get(value) for value in endpoint_ids
        ]
        _require(
            all(value is not None for value in endpoint_rows),
            f"{path}: local proof endpoint is not a classified anchor",
        )
        concrete_rows = [value for value in endpoint_rows if value is not None]
        occurrence_kinds = [
            value["occurrence_kind"] for value in concrete_rows
        ]
        raw_node_domains = [value["node_domain"] for value in concrete_rows]
        classifications = [value["classification"] for value in concrete_rows]
        catalog_domains = [
            _occurrence_catalog_domain(kind) for kind in occurrence_kinds
        ]
        flags = {
            "touches_noncatalog_aggregate_endpoint": any(
                kind in AGGREGATE_OCCURRENCE_KINDS for kind in occurrence_kinds
            ),
            "occurrence_derived_domain_crossing": (
                len(set(catalog_domains)) > 1
            ),
            "raw_node_domain_crossing": len(set(raw_node_domains)) > 1,
            "context_remuneration_mix": {
                "context_anchor",
                "remuneration_component_anchor",
            }.issubset(set(occurrence_kinds)),
            "head_spouse_mix": {
                ROLE_HEAD,
                ROLE_SPOUSE,
            }.issubset(set(classifications)),
        }
        flags["corrected_catalog_domain_crossing"] = flags[
            "occurrence_derived_domain_crossing"
        ]
        instructions = _source_instruction_ids(row)
        evidence_ids = list(row["evidence_occurrence_ids"])
        _require(
            all(value in occurrence_by_id for value in evidence_ids),
            f"{path}: evidence occurrence is missing",
        )
        normalized_evidence.append(
            {
                "source_row_index": source_row_index,
                "local_evidence_id": _evidence_id(row),
                "relation": _evidence_relation(row),
                "handoff_status": row.get(
                    "handoff_status", row.get("resolution_status")
                ),
                "source_instruction_occurrence_ids": instructions,
                "alias_anchor_occurrence_ids": aliases,
                "canonical_anchor_occurrence_ids": canonicals,
                "evidence_occurrence_ids": evidence_ids,
                "unresolved_target_reference": row.get(
                    "unresolved_target_reference"
                ),
                "endpoint_occurrence_kinds": occurrence_kinds,
                "endpoint_raw_node_domains": raw_node_domains,
                "endpoint_classifications": classifications,
                "defect_flags": flags,
            }
        )

    field_purpose_count = sum(
        row["occurrence_kind"] == "field_purpose_prompt" for row in occurrences
    )
    repeat_ids = tuple(
        row["questionnaire_occurrence_id"]
        for row in occurrences
        if row["occurrence_kind"] == "repeat_or_alias_instruction"
    )
    identity = {
        "annotation_path": path,
        "artifact_id": input_identity["artifact_id"],
        "schema_version": input_identity["schema_version"],
        "source_document_id": source_document_id,
        "document_source_position": position,
        "byte_size": len(raw),
        "raw_sha256": _sha256(raw),
        "content_sha256": input_identity["content_sha256"],
    }
    return NormalizedDocument(
        position=position,
        era_id=era_id,
        annotation_path=path,
        annotation_identity=identity,
        source_document_id=source_document_id,
        schema_version=data["schema_version"],
        page_count=len(data["questionnaire_page_rows"]),
        occurrence_count=len(occurrences),
        flow_count=len(data["flow_branch_rows"]),
        field_purpose_count=field_purpose_count,
        repeat_occurrence_ids=repeat_ids,
        anchor_rows=tuple(normalized_anchors),
        evidence_rows=tuple(normalized_evidence),
    )


def _load_documents(
    reader: SourceReader,
) -> tuple[list[NormalizedDocument], dict[str, Any]]:
    annotation_inputs: list[tuple[dict[str, Any], str]] = []
    seal_identity_rows: list[dict[str, Any]] = []
    protocol_identity: dict[str, Any] | None = None
    seen_positions: list[int] = []
    for expected in ERA_SEALS:
        raw = reader.read(expected["path"])
        _require(len(raw) == expected["byte_size"], "era seal size drift")
        _require(
            _sha256(raw) == expected["raw_sha256"],
            "era seal raw SHA-256 drift",
        )
        seal = strict_json_loads(raw, expected["path"])
        _require(seal["era_id"] == expected["era_id"], "era ID drift")
        _require(
            seal["era_order_position"] == expected["era_order_position"],
            "era order drift",
        )
        positions = tuple(seal["document_source_positions"])
        _require(positions == expected["positions"], "era positions drift")
        _require(
            seal["integrity"]["content_sha256"] == expected["content_sha256"],
            "era seal content SHA-256 drift",
        )
        rows = seal["document_annotation_input_rows"]
        _require(len(rows) == len(positions), "era input count drift")
        _require(
            [row["document_source_position"] for row in rows]
            == list(positions),
            "era input order drift",
        )
        annotation_inputs.extend((row, expected["era_id"]) for row in rows)
        seen_positions.extend(positions)
        current_protocol = seal["stage2_protocol_identity"]
        if protocol_identity is None:
            protocol_identity = current_protocol
        else:
            _require(
                protocol_identity == current_protocol,
                "era seals disagree on stage-2 protocol identity",
            )
        seal_identity_rows.append(
            {
                "era_id": expected["era_id"],
                "era_order_position": expected["era_order_position"],
                "document_source_positions": list(positions),
                "seal_commit": expected["seal_commit"],
                "path": expected["path"],
                "byte_size": len(raw),
                "raw_sha256": _sha256(raw),
                "content_sha256": expected["content_sha256"],
            }
        )
    _require(seen_positions == list(range(1, 82)), "incomplete corpus")
    _require(len(annotation_inputs) == 81, "annotation input count drift")

    documents = [
        _normalize_document(reader.read(row["annotation_path"]), row, era_id)
        for row, era_id in annotation_inputs
    ]
    _require(
        [document.position for document in documents] == list(range(1, 82)),
        "normalized document order drift",
    )
    source_identity = {
        "source_branch_label": SOURCE_BRANCH_LABEL,
        "source_commit": SOURCE_COMMIT,
        "document_count": 81,
        "stage2_protocol_identity": protocol_identity,
        "era_seal_rows": seal_identity_rows,
        "era_seal_count": len(seal_identity_rows),
        "era_seal_domain_sha256": _domain_sha(seal_identity_rows),
    }
    return documents, source_identity


def _source_component_rows(
    document: NormalizedDocument,
) -> list[dict[str, Any]]:
    return [
        row
        for row in document.anchor_rows
        if row["classification"] in COMPONENT_KINDS
    ]


def _role_anchor_rows(
    document: NormalizedDocument,
) -> list[dict[str, Any]]:
    return [
        row for row in document.anchor_rows if row["node_domain"] == "role"
    ]


def _parent_candidate_rows(
    component_kind: str,
    parent_ids: Sequence[str],
    parent_kinds: Sequence[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for parent_id, occurrence_kind in zip(
        parent_ids, parent_kinds, strict=True
    ):
        if occurrence_kind in PARENT_KIND_TO_CATEGORY:
            category = PARENT_KIND_TO_CATEGORY[occurrence_kind]
            eligible = True
            reason = None
            if category == "source_job":
                slot_kind = (
                    "context_only"
                    if component_kind == "source_context"
                    else "remuneration_component"
                )
            else:
                slot_kind = category.removesuffix("_sentinel")
        else:
            category = INELIGIBLE_PARENT_CATEGORY.get(
                occurrence_kind, f"ineligible_{occurrence_kind}"
            )
            eligible = False
            reason = "parent_occurrence_kind_outside_allowed_equations"
            slot_kind = None
        rows.append(
            {
                "parent_occurrence_id": parent_id,
                "parent_occurrence_kind": occurrence_kind,
                "parent_category": category,
                "eligible_parent": eligible,
                "derived_slot_kind": slot_kind,
                "ineligibility_reason": reason,
            }
        )
    return rows


def _component_shape_row(
    document: NormalizedDocument,
    anchor: Mapping[str, Any],
) -> dict[str, Any]:
    candidates = _parent_candidate_rows(
        anchor["classification"],
        anchor["parent_occurrence_ids"],
        anchor["parent_occurrence_kinds"],
    )
    raw_count = len(candidates)
    eligible_count = sum(row["eligible_parent"] for row in candidates)
    if raw_count == 0:
        disposition = "zero_parent_terminal_disposition"
    elif raw_count == 1 and eligible_count == 1:
        disposition = "unique_parent_assignment"
    elif raw_count == 1:
        disposition = "zero_lawful_parent_terminal_disposition"
    else:
        disposition = "multi_parent_ambiguity_no_selection"
    categories = [row["parent_category"] for row in candidates]
    occurrence_id = anchor["source_occurrence_id"]
    resolution_id = _row_id(
        "a12-component-parent-resolution:",
        [
            document.source_document_id,
            occurrence_id,
            anchor["classification"],
            disposition,
            candidates,
        ],
    )
    return {
        "component_parent_resolution_id": resolution_id,
        "document_source_position": document.position,
        "source_document_id": document.source_document_id,
        "source_classification_id": anchor["local_anchor_classification_id"],
        "component_anchor_occurrence_id": occurrence_id,
        "component_kind": anchor["classification"],
        "serialized_parent_cardinality": raw_count,
        "eligible_parent_cardinality": eligible_count,
        "parent_candidate_rows": candidates,
        "parent_candidate_count": raw_count,
        "parent_candidate_domain_sha256": _domain_sha(candidates),
        "raw_parent_category_ambiguity": (
            raw_count > 1 and len(set(categories)) > 1
        ),
        "eligible_parent_category_ambiguity": (
            len(
                {
                    row["parent_category"]
                    for row in candidates
                    if row["eligible_parent"]
                }
            )
            > 1
        ),
        "eligible_ineligible_mixed_ambiguity": (
            raw_count > 1
            and any(row["eligible_parent"] for row in candidates)
            and any(not row["eligible_parent"] for row in candidates)
        ),
        "disposition": disposition,
        "forced_parent_selection": False,
        "tier_2_unique_parent_arm_eligible": (
            disposition == "unique_parent_assignment"
        ),
        "r_q_relationship_emitted": False,
        "status": "recorded_nonauthority_shape",
    }


TIER2_FIXTURE_MEMBER_KEYS = frozenset(
    {"component_anchor_occurrence_id", "parent_candidate_rows"}
)
TIER2_FIXTURE_CANDIDATE_KEYS = frozenset(
    {
        "source_parent_occurrence_id",
        "resolved_canonical_parent_node_id",
        "eligible_parent",
        "derived_slot_kind",
        "support_proof_id",
    }
)


def fold_component_class_fixture(
    component_kind: str,
    member_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Execute the prospective tier-2 class fold on synthetic source rows.

    This fixture mints no catalog, relationship, or authority identity.  It
    makes the class-level cardinality and no-selection law executable before
    ratification.  Callers remain responsible for proving that the supplied
    members and candidates exact-cover the pinned source domain.
    """
    _require(
        component_kind in COMPONENT_KINDS, "tier-2 fixture component kind"
    )
    _require(bool(member_rows), "tier-2 fixture empty component class")
    member_ids: list[str] = []
    raw_counts: list[int] = []
    all_candidates: list[Mapping[str, Any]] = []
    for member in member_rows:
        _require_exact_keys(
            member, TIER2_FIXTURE_MEMBER_KEYS, "tier-2 fixture member"
        )
        member_id = _require_string(
            member["component_anchor_occurrence_id"],
            "tier-2 fixture member occurrence",
        )
        member_ids.append(member_id)
        candidates = member["parent_candidate_rows"]
        _require(isinstance(candidates, list), "tier-2 fixture candidates")
        source_parent_ids: list[str] = []
        for candidate in candidates:
            _require_exact_keys(
                candidate,
                TIER2_FIXTURE_CANDIDATE_KEYS,
                "tier-2 fixture candidate",
            )
            source_parent_ids.append(
                _require_string(
                    candidate["source_parent_occurrence_id"],
                    "tier-2 fixture source parent",
                )
            )
            _require_boolean(
                candidate["eligible_parent"],
                "tier-2 fixture candidate eligibility",
            )
            _require_string(
                candidate["support_proof_id"],
                "tier-2 fixture support proof",
            )
            if candidate["eligible_parent"]:
                _require_string(
                    candidate["resolved_canonical_parent_node_id"],
                    "tier-2 fixture canonical parent",
                )
                _require_string(
                    candidate["derived_slot_kind"],
                    "tier-2 fixture slot kind",
                )
            else:
                _require(
                    candidate["resolved_canonical_parent_node_id"] is None
                    and candidate["derived_slot_kind"] is None,
                    "tier-2 fixture ineligible candidate resolved",
                )
        _require(
            len(set(source_parent_ids)) == len(source_parent_ids),
            "tier-2 fixture duplicate source parent",
        )
        raw_counts.append(len(candidates))
        all_candidates.extend(candidates)
    _require(
        len(set(member_ids)) == len(member_ids),
        "tier-2 fixture duplicate class member",
    )

    eligible_candidates = [
        candidate
        for candidate in all_candidates
        if candidate["eligible_parent"]
    ]
    canonical_parent_ids = list(
        dict.fromkeys(
            candidate["resolved_canonical_parent_node_id"]
            for candidate in eligible_candidates
        )
    )
    slot_kinds = list(
        dict.fromkeys(
            candidate["derived_slot_kind"] for candidate in eligible_candidates
        )
    )
    if all(count == 0 for count in raw_counts):
        disposition = "zero_parent_terminal_disposition"
    elif any(count > 1 for count in raw_counts):
        disposition = "multi_parent_ambiguity_no_selection"
    elif (
        all(count == 1 for count in raw_counts)
        and len(eligible_candidates) == len(member_rows)
        and len(canonical_parent_ids) == 1
        and len(slot_kinds) == 1
    ):
        disposition = "unique_parent_assignment"
    elif not eligible_candidates:
        disposition = "zero_lawful_parent_terminal_disposition"
    else:
        disposition = "multi_parent_ambiguity_no_selection"

    unique = disposition == "unique_parent_assignment"
    return {
        "component_kind": component_kind,
        "member_occurrence_ids": member_ids,
        "member_count": len(member_ids),
        "member_raw_parent_cardinalities": raw_counts,
        "raw_parent_candidate_count": len(all_candidates),
        "eligible_parent_candidate_count": len(eligible_candidates),
        "resolved_canonical_parent_node_ids": canonical_parent_ids,
        "resolved_slot_kinds": slot_kinds,
        "disposition": disposition,
        "unique_parent_node_id": canonical_parent_ids[0] if unique else None,
        "unique_slot_kind": slot_kinds[0] if unique else None,
        "forced_parent_selection": False,
        "tier_2_relationship_arm_eligible": unique,
        "r_q_relationship_emitted": False,
        "status": "prospective_fixture_nonauthority",
    }


def _role_classes(
    documents: Sequence[NormalizedDocument],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    grouped: dict[str, dict[str, Any]] = {}
    observed_first: list[str] = []
    for document in documents:
        for anchor in _role_anchor_rows(document):
            label = anchor["exact_label"]
            _require(isinstance(label, str) and label, "empty role label")
            label_sha = _sha256(label.encode("utf-8"))
            _require(
                label == anchor["occurrence_matched_text"],
                "role exact label differs from occurrence bytes",
            )
            _require(
                label_sha == anchor["occurrence_matched_utf8_sha256"],
                "role exact label digest differs from occurrence digest",
            )
            stored_sha = anchor["exact_label_sha256"]
            _require(
                stored_sha is None or stored_sha == label_sha,
                "stored role label digest drift",
            )
            role = anchor["classification"]
            _require(role in ROLE_ORDER, "unknown role classification")
            if label not in grouped:
                grouped[label] = {
                    "roles": set(),
                    "members": [],
                    "label_sha": label_sha,
                }
                observed_first.append(label)
            grouped[label]["roles"].add(role)
            grouped[label]["members"].append(anchor["source_occurrence_id"])
    class_rows: list[dict[str, Any]] = []
    by_label: dict[str, dict[str, Any]] = {}
    for label in observed_first:
        value = grouped[label]
        _require(
            len(value["roles"]) == 1,
            f"role exact-label class crosses roles: {label!r}",
        )
        role = next(iter(value["roles"]))
        members = value["members"]
        class_id = _row_id(
            "a12-role-exact-label-class:",
            [role, value["label_sha"]],
        )
        row = {
            "role_label_class_id": class_id,
            "role": role,
            "exact_label": label,
            "exact_label_sha256": value["label_sha"],
            "member_occurrence_ids": members,
            "member_count": len(members),
            "member_keyset_sha256": _keyset_sha(members),
            "occurrence_equivalence_claimed": False,
            "alias_class_claimed": False,
            "status": "role_membership_class_only",
        }
        class_rows.append(row)
        by_label[label] = row
    return class_rows, by_label


def _role_assignment_rows(
    documents: Sequence[NormalizedDocument],
    classes_by_label: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    canonical_ids = set(ROLE_CANONICALS.values())
    for document in documents:
        for anchor in _role_anchor_rows(document):
            occurrence_id = anchor["source_occurrence_id"]
            if occurrence_id in canonical_ids:
                continue
            label = anchor["exact_label"]
            role = anchor["classification"]
            class_row = classes_by_label[label]
            _require(class_row["role"] == role, "role class mismatch")
            assignment_id = _row_id(
                "a12-pilot-role-assignment:",
                [
                    document.source_document_id,
                    occurrence_id,
                    role,
                    class_row["role_label_class_id"],
                    "exact_label_class_role_assignment_non_alias",
                ],
            )
            rows.append(
                {
                    "role_assignment_id": assignment_id,
                    "document_source_position": document.position,
                    "source_document_id": document.source_document_id,
                    "source_classification_id": anchor[
                        "local_anchor_classification_id"
                    ],
                    "role_anchor_occurrence_id": occurrence_id,
                    "assigned_role": role,
                    "printed_identifier": anchor["printed_identifier"],
                    "exact_label": label,
                    "exact_label_sha256": class_row["exact_label_sha256"],
                    "role_label_class_id": class_row["role_label_class_id"],
                    "proof_form": (
                        "exact_label_class_role_assignment_non_alias"
                    ),
                    "alias_admitted_by_assignment": False,
                    "occurrence_equivalence_claimed": False,
                    "status": "assigned_noncanonical_role_anchor",
                }
            )
    return rows


def _outside_repeat_rows(
    documents: Sequence[NormalizedDocument],
) -> list[dict[str, Any]]:
    all_instruction_to_evidence: defaultdict[str, list[str]] = defaultdict(
        list
    )
    all_endpoint_ids: set[str] = set()
    candidates: list[tuple[NormalizedDocument, dict[str, Any]]] = []
    for document in documents:
        for evidence in document.evidence_rows:
            for instruction_id in evidence[
                "source_instruction_occurrence_ids"
            ]:
                all_instruction_to_evidence[instruction_id].append(
                    evidence["local_evidence_id"]
                )
            all_endpoint_ids.update(evidence["alias_anchor_occurrence_ids"])
            all_endpoint_ids.update(
                evidence["canonical_anchor_occurrence_ids"]
            )
            if (
                evidence["handoff_status"]
                == "local_target_outside_rq_annotation_domain"
            ):
                candidates.append((document, evidence))
    rows: list[dict[str, Any]] = []
    for document, evidence in candidates:
        instructions = evidence["source_instruction_occurrence_ids"]
        _require(len(instructions) == 1, "outside repeat is not singleton")
        instruction_id = instructions[0]
        _require(
            not evidence["alias_anchor_occurrence_ids"]
            and not evidence["canonical_anchor_occurrence_ids"],
            "outside repeat has an alias endpoint",
        )
        _require(
            evidence["evidence_occurrence_ids"] == [instruction_id],
            "outside repeat evidence is not singleton self-evidence",
        )
        unresolved = evidence["unresolved_target_reference"]
        _require(isinstance(unresolved, dict) and unresolved, "empty target")
        _require(
            len(all_instruction_to_evidence[instruction_id]) == 1,
            "outside repeat occurs in another local evidence row",
        )
        _require(
            instruction_id not in all_endpoint_ids,
            "outside repeat occurs as an alias endpoint",
        )
        disposition_id = _row_id(
            "a12-outside-rq-repeat-disposition:",
            [
                document.source_document_id,
                instruction_id,
                evidence["local_evidence_id"],
                evidence["relation"],
                unresolved,
            ],
        )
        rows.append(
            {
                "outside_domain_repeat_disposition_id": disposition_id,
                "document_source_position": document.position,
                "source_document_id": document.source_document_id,
                "source_local_evidence_id": evidence["local_evidence_id"],
                "source_instruction_occurrence_id": instruction_id,
                "relation": evidence["relation"],
                "handoff_status": evidence["handoff_status"],
                "evidence_occurrence_ids": [instruction_id],
                "unresolved_target_reference": unresolved,
                "terminal_disposition": (
                    "outside_r_q_domain_no_alias_admitted"
                ),
                "alias_anchor_occurrence_id": None,
                "referenced_anchor_occurrence_id": None,
                "alias_admitted": False,
                "occurrence_equivalence_claimed": False,
                "universal_repeat_coverage_arm_satisfied": True,
                "status": "terminal_nonauthority_disposition",
            }
        )
    return rows


def _proof_defect_rows(
    documents: Sequence[NormalizedDocument],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for document in documents:
        for evidence in document.evidence_rows:
            if not evidence["alias_anchor_occurrence_ids"]:
                continue
            if not evidence["canonical_anchor_occurrence_ids"]:
                continue
            flags = evidence["defect_flags"]
            if not any(flags.values()):
                continue
            row_id = _row_id(
                "a12-predecessor-local-proof-adjudication:",
                [
                    document.source_document_id,
                    evidence["local_evidence_id"],
                    flags,
                    "predecessor_seal_defect",
                ],
            )
            rows.append(
                {
                    "predecessor_adjudication_id": row_id,
                    "document_source_position": document.position,
                    "source_document_id": document.source_document_id,
                    "source_local_evidence_id": evidence["local_evidence_id"],
                    "relation": evidence["relation"],
                    "source_instruction_occurrence_ids": evidence[
                        "source_instruction_occurrence_ids"
                    ],
                    "alias_anchor_occurrence_ids": evidence[
                        "alias_anchor_occurrence_ids"
                    ],
                    "canonical_anchor_occurrence_ids": evidence[
                        "canonical_anchor_occurrence_ids"
                    ],
                    "evidence_occurrence_ids": evidence[
                        "evidence_occurrence_ids"
                    ],
                    "endpoint_occurrence_kinds": evidence[
                        "endpoint_occurrence_kinds"
                    ],
                    "endpoint_raw_node_domains": evidence[
                        "endpoint_raw_node_domains"
                    ],
                    "endpoint_classifications": evidence[
                        "endpoint_classifications"
                    ],
                    "defect_flags": flags,
                    "disposition": "predecessor_seal_defect",
                    "law_gap_admitted": False,
                    "alias_admitted": False,
                    "required_action": (
                        "readjudicate_source_row_and_reseal_before_tier_2"
                    ),
                    "adjudicative_rationale": (
                        "incompatible_endpoint_claim_cannot_be_admitted_as_"
                        "alias_law_reseal_required"
                    ),
                    "status": "blocked_predecessor_row",
                }
            )
    return rows


def _doc036_defect_rows(
    documents: Sequence[NormalizedDocument],
) -> list[dict[str, Any]]:
    document = next(value for value in documents if value.position == 36)
    rows: list[dict[str, Any]] = []
    for anchor in document.anchor_rows:
        if anchor["classification"] not in AGGREGATE_CLASSIFICATIONS:
            continue
        if anchor["node_domain"] != "component_slot":
            continue
        _require(
            anchor["occurrence_kind"] in AGGREGATE_OCCURRENCE_KINDS,
            "doc036 aggregate classification lacks aggregate occurrence",
        )
        row_id = _row_id(
            "a12-predecessor-doc036-aggregate-adjudication:",
            [
                document.source_document_id,
                anchor["local_anchor_classification_id"],
                anchor["source_occurrence_id"],
                anchor["classification"],
                "predecessor_seal_defect",
            ],
        )
        rows.append(
            {
                "predecessor_adjudication_id": row_id,
                "document_source_position": document.position,
                "source_document_id": document.source_document_id,
                "source_classification_id": anchor[
                    "local_anchor_classification_id"
                ],
                "source_occurrence_id": anchor["source_occurrence_id"],
                "source_classification": anchor["classification"],
                "occurrence_kind": anchor["occurrence_kind"],
                "serialized_node_domain": anchor["node_domain"],
                "correct_node_domain": "aggregate",
                "disposition": "predecessor_seal_defect",
                "law_gap_admitted": False,
                "component_slot_admitted": False,
                "required_action": (
                    "reseal_document_036_with_aggregate_anchor_domain"
                ),
                "adjudicative_rationale": (
                    "aggregate_occurrence_kind_controls_node_domain_"
                    "reseal_required"
                ),
                "status": "blocked_predecessor_row",
            }
        )
    return rows


def _compatible_direct_proof(evidence: Mapping[str, Any]) -> bool:
    return bool(
        evidence["alias_anchor_occurrence_ids"]
        and evidence["canonical_anchor_occurrence_ids"]
        and not any(evidence["defect_flags"].values())
    )


def _pilot_census(documents: Sequence[NormalizedDocument]) -> dict[str, Any]:
    classification_counts: Counter[str] = Counter()
    occurrence_kind_counts: Counter[str] = Counter()
    evidence_shape_counts: Counter[str] = Counter()
    valid_instruction_ids: set[str] = set()
    incompatible_instruction_ids: set[str] = set()
    outside_instruction_ids: set[str] = set()
    repeat_ids: set[str] = set()
    for document in documents:
        repeat_ids.update(document.repeat_occurrence_ids)
        for anchor in document.anchor_rows:
            classification_counts[anchor["classification"]] += 1
            occurrence_kind_counts[anchor["occurrence_kind"]] += 1
        for evidence in document.evidence_rows:
            has_alias = bool(evidence["alias_anchor_occurrence_ids"])
            has_canonical = bool(evidence["canonical_anchor_occurrence_ids"])
            if has_alias and has_canonical:
                evidence_shape_counts["both_endpoints"] += 1
            elif has_alias or has_canonical:
                evidence_shape_counts["partial_endpoints"] += 1
            else:
                evidence_shape_counts["no_endpoints"] += 1
            instructions = set(evidence["source_instruction_occurrence_ids"])
            if _compatible_direct_proof(evidence):
                valid_instruction_ids.update(instructions)
            elif has_alias and has_canonical:
                incompatible_instruction_ids.update(instructions)
            if (
                evidence["handoff_status"]
                == "local_target_outside_rq_annotation_domain"
            ):
                outside_instruction_ids.update(instructions)
    valid_instruction_ids &= repeat_ids
    incompatible_instruction_ids &= repeat_ids
    outside_instruction_ids &= repeat_ids
    otherwise_unresolved = repeat_ids - (
        valid_instruction_ids
        | incompatible_instruction_ids
        | outside_instruction_ids
    )
    component_raw_cardinality: Counter[str] = Counter()
    component_dispositions: Counter[str] = Counter()
    raw_cross_category = 0
    eligible_cross_category = 0
    eligible_ineligible_mixed = 0
    invalid_parent_references = 0
    component_total = 0
    for document in documents:
        for anchor in _source_component_rows(document):
            shape = _component_shape_row(document, anchor)
            component_total += 1
            raw_count = shape["serialized_parent_cardinality"]
            raw_label = (
                "zero"
                if raw_count == 0
                else "one" if raw_count == 1 else "multiple"
            )
            component_raw_cardinality[raw_label] += 1
            component_dispositions[shape["disposition"]] += 1
            raw_cross_category += int(shape["raw_parent_category_ambiguity"])
            eligible_cross_category += int(
                shape["eligible_parent_category_ambiguity"]
            )
            eligible_ineligible_mixed += int(
                shape["eligible_ineligible_mixed_ambiguity"]
            )
            invalid_parent_references += sum(
                not row["eligible_parent"]
                for row in shape["parent_candidate_rows"]
            )
    role_total = (
        classification_counts[ROLE_HEAD] + classification_counts[ROLE_SPOUSE]
    )
    aggregate_total = sum(
        occurrence_kind_counts[value] for value in AGGREGATE_OCCURRENCE_KINDS
    )
    return {
        "document_count": len(documents),
        "questionnaire_page_count": sum(
            value.page_count for value in documents
        ),
        "questionnaire_occurrence_count": sum(
            value.occurrence_count for value in documents
        ),
        "flow_branch_count": sum(value.flow_count for value in documents),
        "local_anchor_count": sum(
            len(value.anchor_rows) for value in documents
        ),
        "field_purpose_count": sum(
            value.field_purpose_count for value in documents
        ),
        "role_anchor_count": role_total,
        "head_role_anchor_count": classification_counts[ROLE_HEAD],
        "spouse_role_anchor_count": classification_counts[ROLE_SPOUSE],
        "job_anchor_count": classification_counts["source_job"],
        "source_component_anchor_count": component_total,
        "source_context_anchor_count": classification_counts["source_context"],
        "source_remuneration_anchor_count": classification_counts[
            "source_remuneration_component"
        ],
        "aggregate_anchor_count": aggregate_total,
        "repeat_occurrence_count": len(repeat_ids),
        "local_evidence_row_count": sum(
            len(value.evidence_rows) for value in documents
        ),
        "local_evidence_shape_counts": dict(
            sorted(evidence_shape_counts.items())
        ),
        "valid_direct_proof_instruction_count": len(valid_instruction_ids),
        "outside_domain_instruction_count": len(outside_instruction_ids),
        "incompatible_proof_instruction_count": len(
            incompatible_instruction_ids
        ),
        "valid_and_incompatible_instruction_overlap_count": len(
            valid_instruction_ids & incompatible_instruction_ids
        ),
        "otherwise_unresolved_instruction_count": len(otherwise_unresolved),
        "serialized_component_parent_cardinality": {
            key: component_raw_cardinality[key]
            for key in ("zero", "one", "multiple")
        },
        "component_parent_disposition_counts": dict(
            sorted(component_dispositions.items())
        ),
        "raw_cross_category_multi_parent_count": raw_cross_category,
        "eligible_cross_category_multi_parent_count": (
            eligible_cross_category
        ),
        "eligible_ineligible_mixed_multi_parent_count": (
            eligible_ineligible_mixed
        ),
        "ineligible_parent_reference_count": invalid_parent_references,
    }


def _build_bundle(
    documents: Sequence[NormalizedDocument],
    source_identity: Mapping[str, Any],
    design_prefix_identity: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    pilot_documents = [
        document
        for document in documents
        if document.position in PILOT_POSITIONS
    ]
    _require(
        tuple(document.position for document in pilot_documents)
        == PILOT_POSITIONS,
        "pilot membership drift",
    )
    pilot_rows: list[dict[str, Any]] = []
    for document in pilot_documents:
        pilot_rows.append(
            {
                "document_source_position": document.position,
                "era_id": document.era_id,
                "annotation_path": document.annotation_path,
                "source_document_id": document.source_document_id,
                "schema_version": document.schema_version,
                "annotation_byte_size": document.annotation_identity[
                    "byte_size"
                ],
                "annotation_raw_sha256": document.annotation_identity[
                    "raw_sha256"
                ],
                "annotation_content_sha256": document.annotation_identity[
                    "content_sha256"
                ],
                "pilot_role": (
                    "clean_era_control"
                    if document.position in CONTROL_POSITIONS
                    else "charter_pathology_carrier"
                ),
                "selection_tags": list(PILOT_TAGS[document.position]),
            }
        )
    pilot_census = _pilot_census(pilot_documents)
    pilot_annotation_bytes = sum(
        row["annotation_byte_size"] for row in pilot_rows
    )
    slice_artifact = _artifact(
        "amendment_12_rq_catalog_pilot_slice_manifest.v1",
        "a12-rq-pilot-slice:",
        "amendment_12_tier_1_pilot_nonauthority",
        {
            "tier": 1,
            "design_prefix_identity": design_prefix_identity,
            "source_corpus_identity": source_identity,
            "control_selection_rule": (
                "earliest_source_order_noncarrier_in_each_era_with_zero_"
                "outside_domain_rows_zero_defective_populated_proof_rows_"
                "and_zero_aggregate_kind_component_slot_rows"
            ),
            "pilot_document_rows": pilot_rows,
            "pilot_document_count": len(pilot_rows),
            "pilot_document_positions": list(PILOT_POSITIONS),
            "pilot_document_position_domain_sha256": _domain_sha(
                list(PILOT_POSITIONS)
            ),
            "pilot_annotation_raw_byte_count": pilot_annotation_bytes,
            "pilot_census": pilot_census,
            "nonauthority_statement": _nonauthority_statement(),
            "status": "pass_pilot_slice_fixed_nonauthority",
        },
    )

    all_role_classes, role_class_by_label = _role_classes(documents)
    full_component_shapes = [
        _component_shape_row(document, anchor)
        for document in documents
        for anchor in _source_component_rows(document)
    ]
    source_anchor_index = {
        (document.position, anchor["source_occurrence_id"]): (
            document,
            anchor,
        )
        for document in documents
        for anchor in document.anchor_rows
    }
    parent_source_witness_rows: list[dict[str, Any]] = []
    seen_parent_source_keys: set[tuple[int, str]] = set()
    for shape in full_component_shapes:
        for candidate in shape["parent_candidate_rows"]:
            source_key = (
                shape["document_source_position"],
                candidate["parent_occurrence_id"],
            )
            _require(
                source_key in source_anchor_index,
                "component parent is absent from the pinned source anchor domain",
            )
            document, source_anchor = source_anchor_index[source_key]
            _require(
                source_anchor["occurrence_kind"]
                == candidate["parent_occurrence_kind"],
                "component parent kind differs from pinned source anchor",
            )
            if source_key in seen_parent_source_keys:
                continue
            seen_parent_source_keys.add(source_key)
            witness_id = _row_id(
                "a12-parent-source-witness:",
                [
                    document.source_document_id,
                    source_anchor["local_anchor_classification_id"],
                    source_anchor["source_occurrence_id"],
                    source_anchor["occurrence_kind"],
                ],
            )
            parent_source_witness_rows.append(
                {
                    "parent_source_witness_id": witness_id,
                    "document_source_position": document.position,
                    "source_document_id": document.source_document_id,
                    "source_classification_id": source_anchor[
                        "local_anchor_classification_id"
                    ],
                    "parent_occurrence_id": source_anchor[
                        "source_occurrence_id"
                    ],
                    "parent_occurrence_kind": source_anchor["occurrence_kind"],
                    "parent_classification": source_anchor["classification"],
                    "status": "pinned_source_parent_witness",
                }
            )
    full_outside_rows = _outside_repeat_rows(documents)
    raw_cardinality = Counter()
    disposition_counts = Counter()
    invalid_parent_refs = 0
    for row in full_component_shapes:
        raw_count = row["serialized_parent_cardinality"]
        raw_cardinality[
            (
                "zero"
                if raw_count == 0
                else "one" if raw_count == 1 else "multiple"
            )
        ] += 1
        disposition_counts[row["disposition"]] += 1
        invalid_parent_refs += sum(
            not value["eligible_parent"]
            for value in row["parent_candidate_rows"]
        )
    sweep_artifact = _artifact(
        "amendment_12_rq_catalog_corpus_exhaustive_targeted_sweeps.v1",
        "a12-rq-corpus-sweeps:",
        "amendment_12_corpus_exhaustive_shape_sweeps_nonauthority",
        {
            "tier": 1,
            "source_corpus_identity": source_identity,
            "document_positions_swept": list(range(1, 82)),
            "document_count": 81,
            "role_exact_label_class_rows": all_role_classes,
            "role_exact_label_class_count": len(all_role_classes),
            "role_exact_label_class_domain_sha256": _domain_sha(
                all_role_classes
            ),
            "role_anchor_count": sum(
                row["member_count"] for row in all_role_classes
            ),
            "role_noncanonical_assignment_reach_count": (
                sum(row["member_count"] for row in all_role_classes) - 2
            ),
            "role_cross_classification_label_count": 0,
            "role_unreached_anchor_rows": [],
            "role_unreached_anchor_count": 0,
            "outside_domain_repeat_shape_rows": full_outside_rows,
            "outside_domain_repeat_shape_count": len(full_outside_rows),
            "outside_domain_repeat_shape_domain_sha256": _domain_sha(
                full_outside_rows
            ),
            "component_parent_shape_rows": full_component_shapes,
            "component_parent_shape_count": len(full_component_shapes),
            "component_parent_shape_keyset_sha256": _keyset_sha(
                [
                    row["component_parent_resolution_id"]
                    for row in full_component_shapes
                ]
            ),
            "component_parent_shape_domain_sha256": _domain_sha(
                full_component_shapes
            ),
            "parent_source_witness_rows": parent_source_witness_rows,
            "parent_source_witness_count": len(parent_source_witness_rows),
            "parent_source_witness_keyset_sha256": _keyset_sha(
                [
                    row["parent_source_witness_id"]
                    for row in parent_source_witness_rows
                ]
            ),
            "parent_source_witness_domain_sha256": _domain_sha(
                parent_source_witness_rows
            ),
            "serialized_parent_cardinality_counts": {
                key: raw_cardinality[key]
                for key in ("zero", "one", "multiple")
            },
            "component_parent_disposition_counts": dict(
                sorted(disposition_counts.items())
            ),
            "raw_cross_category_multi_parent_count": sum(
                row["raw_parent_category_ambiguity"]
                for row in full_component_shapes
            ),
            "eligible_cross_category_multi_parent_count": sum(
                row["eligible_parent_category_ambiguity"]
                for row in full_component_shapes
            ),
            "eligible_ineligible_mixed_multi_parent_count": sum(
                row["eligible_ineligible_mixed_ambiguity"]
                for row in full_component_shapes
            ),
            "ineligible_parent_reference_count": invalid_parent_refs,
            "nonauthority_statement": _nonauthority_statement(),
            "status": "pass_corpus_exhaustive_targeted_sweeps_nonauthority",
        },
    )

    proof_defects = _proof_defect_rows(documents)
    doc036_defects = _doc036_defect_rows(documents)
    predecessor_artifact = _artifact(
        "amendment_12_rq_catalog_predecessor_defect_adjudication.v1",
        "a12-rq-predecessor-adjudication:",
        "amendment_12_predecessor_seal_defect_sweep_nonauthority",
        {
            "tier": 1,
            "source_corpus_identity": source_identity,
            "doc036_aggregate_component_slot_rows": doc036_defects,
            "doc036_aggregate_component_slot_count": len(doc036_defects),
            "doc036_aggregate_component_slot_domain_sha256": _domain_sha(
                doc036_defects
            ),
            "defective_populated_local_proof_rows": proof_defects,
            "defective_populated_local_proof_count": len(proof_defects),
            "defective_populated_local_proof_keyset_sha256": _keyset_sha(
                [row["source_local_evidence_id"] for row in proof_defects]
            ),
            "defective_populated_local_proof_domain_sha256": _domain_sha(
                proof_defects
            ),
            "defect_category_counts": {
                key: sum(row["defect_flags"][key] for row in proof_defects)
                for key in (
                    "touches_noncatalog_aggregate_endpoint",
                    "occurrence_derived_domain_crossing",
                    "corrected_catalog_domain_crossing",
                    "raw_node_domain_crossing",
                    "context_remuneration_mix",
                    "head_spouse_mix",
                )
            },
            "seal_defect_disposition_count": len(doc036_defects)
            + len(proof_defects),
            "law_gap_disposition_count": 0,
            "tier_2_precondition": (
                "all_50_rows_readjudicated_and_resealed_before_certification"
            ),
            "adjudication_rule": (
                "incompatible_predecessor_endpoint_or_node_domain_claims_"
                "remain_seal_defects_and_cannot_create_catalog_law"
            ),
            "nonauthority_statement": _nonauthority_statement(),
            "status": "pass_adjudication_with_predecessor_reseal_required",
        },
    )

    pilot_role_classes: list[dict[str, Any]] = []
    pilot_member_ids = {
        anchor["source_occurrence_id"]
        for document in pilot_documents
        for anchor in _role_anchor_rows(document)
    }
    for row in all_role_classes:
        members = [
            value
            for value in row["member_occurrence_ids"]
            if value in pilot_member_ids
        ]
        if not members:
            continue
        projected = copy.deepcopy(row)
        projected["member_occurrence_ids"] = members
        projected["member_count"] = len(members)
        projected["member_keyset_sha256"] = _keyset_sha(members)
        pilot_role_classes.append(projected)
    role_assignments = _role_assignment_rows(
        pilot_documents, role_class_by_label
    )
    role_artifact = _artifact(
        "amendment_12_rq_catalog_role_assignment_pilot.v1",
        "a12-rq-role-pilot:",
        "amendment_12_tier_1_role_assignment_pilot_nonauthority",
        {
            "tier": 1,
            "source_slice_artifact_id": slice_artifact["artifact_id"],
            "corpus_sweep_artifact_id": sweep_artifact["artifact_id"],
            "canonical_role_occurrence_ids": ROLE_CANONICALS,
            "role_label_class_rows": pilot_role_classes,
            "role_label_class_count": len(pilot_role_classes),
            "role_label_class_domain_sha256": _domain_sha(pilot_role_classes),
            "role_assignment_rows": role_assignments,
            "role_assignment_count": len(role_assignments),
            "role_assignment_keyset_sha256": _keyset_sha(
                [row["role_assignment_id"] for row in role_assignments]
            ),
            "role_assignment_domain_sha256": _domain_sha(role_assignments),
            "unassigned_role_anchor_rows": [],
            "unassigned_role_anchor_count": 0,
            "nonauthority_statement": _nonauthority_statement(),
            "status": "pass_role_assignment_law_pilot_nonauthority",
        },
    )

    pilot_outside_rows = _outside_repeat_rows(pilot_documents)
    repeat_artifact = _artifact(
        "amendment_12_rq_catalog_outside_domain_repeat_pilot.v1",
        "a12-rq-repeat-pilot:",
        "amendment_12_tier_1_repeat_disposition_pilot_nonauthority",
        {
            "tier": 1,
            "source_slice_artifact_id": slice_artifact["artifact_id"],
            "corpus_sweep_artifact_id": sweep_artifact["artifact_id"],
            "outside_domain_repeat_disposition_rows": pilot_outside_rows,
            "outside_domain_repeat_disposition_count": len(pilot_outside_rows),
            "outside_domain_repeat_disposition_keyset_sha256": _keyset_sha(
                [
                    row["outside_domain_repeat_disposition_id"]
                    for row in pilot_outside_rows
                ]
            ),
            "outside_domain_repeat_disposition_domain_sha256": _domain_sha(
                pilot_outside_rows
            ),
            "relation_counts": dict(
                sorted(
                    Counter(
                        row["relation"] for row in pilot_outside_rows
                    ).items()
                )
            ),
            "document_counts": {
                str(key): value
                for key, value in sorted(
                    Counter(
                        row["document_source_position"]
                        for row in pilot_outside_rows
                    ).items()
                )
            },
            "nonauthority_statement": _nonauthority_statement(),
            "status": "pass_outside_domain_repeat_law_pilot_nonauthority",
        },
    )

    pilot_component_shapes = [
        _component_shape_row(document, anchor)
        for document in pilot_documents
        for anchor in _source_component_rows(document)
    ]
    zero_rows = [
        row
        for row in pilot_component_shapes
        if row["disposition"]
        in {
            "zero_parent_terminal_disposition",
            "zero_lawful_parent_terminal_disposition",
        }
    ]
    unique_rows = [
        row
        for row in pilot_component_shapes
        if row["disposition"] == "unique_parent_assignment"
    ]
    ambiguity_rows = [
        row
        for row in pilot_component_shapes
        if row["disposition"] == "multi_parent_ambiguity_no_selection"
    ]
    component_artifact = _artifact(
        "amendment_12_rq_catalog_component_parent_pilot.v1",
        "a12-rq-component-pilot:",
        "amendment_12_tier_1_component_parent_pilot_nonauthority",
        {
            "tier": 1,
            "source_slice_artifact_id": slice_artifact["artifact_id"],
            "corpus_sweep_artifact_id": sweep_artifact["artifact_id"],
            "zero_parent_disposition_rows": zero_rows,
            "zero_parent_disposition_count": len(zero_rows),
            "zero_parent_disposition_domain_sha256": _domain_sha(zero_rows),
            "unique_parent_assignment_rows": unique_rows,
            "unique_parent_assignment_count": len(unique_rows),
            "unique_parent_assignment_domain_sha256": _domain_sha(unique_rows),
            "multi_parent_ambiguity_rows": ambiguity_rows,
            "multi_parent_ambiguity_count": len(ambiguity_rows),
            "multi_parent_ambiguity_domain_sha256": _domain_sha(
                ambiguity_rows
            ),
            "complete_component_resolution_count": len(pilot_component_shapes),
            "complete_component_resolution_keyset_sha256": _keyset_sha(
                [
                    row["component_parent_resolution_id"]
                    for row in [*zero_rows, *unique_rows, *ambiguity_rows]
                ]
            ),
            "complete_component_resolution_domain_sha256": _domain_sha(
                [*zero_rows, *unique_rows, *ambiguity_rows]
            ),
            "serialized_parent_cardinality_counts": pilot_census[
                "serialized_component_parent_cardinality"
            ],
            "raw_cross_category_multi_parent_count": pilot_census[
                "raw_cross_category_multi_parent_count"
            ],
            "eligible_cross_category_multi_parent_count": pilot_census[
                "eligible_cross_category_multi_parent_count"
            ],
            "eligible_ineligible_mixed_multi_parent_count": pilot_census[
                "eligible_ineligible_mixed_multi_parent_count"
            ],
            "ineligible_parent_reference_count": pilot_census[
                "ineligible_parent_reference_count"
            ],
            "nonauthority_statement": _nonauthority_statement(),
            "status": "pass_component_parent_law_pilot_nonauthority",
        },
    )

    preliminary = {
        "slice": slice_artifact,
        "sweeps": sweep_artifact,
        "predecessor": predecessor_artifact,
        "role": role_artifact,
        "repeat": repeat_artifact,
        "component": component_artifact,
    }
    artifact_identity_rows = []
    for key, artifact in preliminary.items():
        raw = canonical_bytes(artifact)
        artifact_identity_rows.append(
            {
                "artifact_role": key,
                "path": (
                    "docs/analysis/amendment_12_rq_catalog_pilot/"
                    + OUTPUT_FILENAMES[key]
                ),
                "schema_version": artifact["schema_version"],
                "artifact_id": artifact["artifact_id"],
                "byte_size": len(raw),
                "raw_sha256": _sha256(raw),
            }
        )
    gate_artifact = _artifact(
        "amendment_12_rq_catalog_pilot_gate_result.v1",
        "a12-rq-pilot-gate:",
        "amendment_12_tier_1_pilot_gate_result_nonauthority",
        {
            "tier": 1,
            "design_prefix_identity": design_prefix_identity,
            "source_slice_artifact_id": slice_artifact["artifact_id"],
            "artifact_identity_rows": artifact_identity_rows,
            "artifact_identity_count": len(artifact_identity_rows),
            "artifact_identity_domain_sha256": _domain_sha(
                artifact_identity_rows
            ),
            "pilot_census": pilot_census,
            "role_law_status": "pass",
            "outside_domain_repeat_law_status": "pass",
            "component_parent_law_status": "pass",
            "predecessor_input_status": "reseal_required_before_tier_2",
            "overall_repeat_catalog_coverage_status": (
                "fail_closed_unresolved_rows_remain"
            ),
            "pilot_law_shape_status": "pass",
            "tier_2_protocol_status": (
                "not_started_requires_ratification_and_predecessor_reseals"
            ),
            "certification_status": "PILOT_NONAUTHORITY_CERTIFIES_NOTHING",
            "nonauthority_statement": _nonauthority_statement(),
            "status": "pass_law_shapes_only_nonauthority",
        },
    )
    return {**preliminary, "gate": gate_artifact}


ARTIFACT_SPECS = {
    "slice": (
        "amendment_12_rq_catalog_pilot_slice_manifest.v1",
        "a12-rq-pilot-slice:",
        "amendment_12_tier_1_pilot_nonauthority",
    ),
    "sweeps": (
        "amendment_12_rq_catalog_corpus_exhaustive_targeted_sweeps.v1",
        "a12-rq-corpus-sweeps:",
        "amendment_12_corpus_exhaustive_shape_sweeps_nonauthority",
    ),
    "predecessor": (
        "amendment_12_rq_catalog_predecessor_defect_adjudication.v1",
        "a12-rq-predecessor-adjudication:",
        "amendment_12_predecessor_seal_defect_sweep_nonauthority",
    ),
    "role": (
        "amendment_12_rq_catalog_role_assignment_pilot.v1",
        "a12-rq-role-pilot:",
        "amendment_12_tier_1_role_assignment_pilot_nonauthority",
    ),
    "repeat": (
        "amendment_12_rq_catalog_outside_domain_repeat_pilot.v1",
        "a12-rq-repeat-pilot:",
        "amendment_12_tier_1_repeat_disposition_pilot_nonauthority",
    ),
    "component": (
        "amendment_12_rq_catalog_component_parent_pilot.v1",
        "a12-rq-component-pilot:",
        "amendment_12_tier_1_component_parent_pilot_nonauthority",
    ),
    "gate": (
        "amendment_12_rq_catalog_pilot_gate_result.v1",
        "a12-rq-pilot-gate:",
        "amendment_12_tier_1_pilot_gate_result_nonauthority",
    ),
}

_ENVELOPE_KEYS = {
    "schema_version",
    "artifact_id",
    "authority_kind",
    "integrity",
}
ARTIFACT_TOP_LEVEL_KEYS = {
    "slice": frozenset(
        _ENVELOPE_KEYS
        | {
            "tier",
            "design_prefix_identity",
            "source_corpus_identity",
            "control_selection_rule",
            "pilot_document_rows",
            "pilot_document_count",
            "pilot_document_positions",
            "pilot_document_position_domain_sha256",
            "pilot_annotation_raw_byte_count",
            "pilot_census",
            "nonauthority_statement",
            "status",
        }
    ),
    "sweeps": frozenset(
        _ENVELOPE_KEYS
        | {
            "tier",
            "source_corpus_identity",
            "document_positions_swept",
            "document_count",
            "role_exact_label_class_rows",
            "role_exact_label_class_count",
            "role_exact_label_class_domain_sha256",
            "role_anchor_count",
            "role_noncanonical_assignment_reach_count",
            "role_cross_classification_label_count",
            "role_unreached_anchor_rows",
            "role_unreached_anchor_count",
            "outside_domain_repeat_shape_rows",
            "outside_domain_repeat_shape_count",
            "outside_domain_repeat_shape_domain_sha256",
            "component_parent_shape_rows",
            "component_parent_shape_count",
            "component_parent_shape_keyset_sha256",
            "component_parent_shape_domain_sha256",
            "parent_source_witness_rows",
            "parent_source_witness_count",
            "parent_source_witness_keyset_sha256",
            "parent_source_witness_domain_sha256",
            "serialized_parent_cardinality_counts",
            "component_parent_disposition_counts",
            "raw_cross_category_multi_parent_count",
            "eligible_cross_category_multi_parent_count",
            "eligible_ineligible_mixed_multi_parent_count",
            "ineligible_parent_reference_count",
            "nonauthority_statement",
            "status",
        }
    ),
    "predecessor": frozenset(
        _ENVELOPE_KEYS
        | {
            "tier",
            "source_corpus_identity",
            "doc036_aggregate_component_slot_rows",
            "doc036_aggregate_component_slot_count",
            "doc036_aggregate_component_slot_domain_sha256",
            "defective_populated_local_proof_rows",
            "defective_populated_local_proof_count",
            "defective_populated_local_proof_keyset_sha256",
            "defective_populated_local_proof_domain_sha256",
            "defect_category_counts",
            "seal_defect_disposition_count",
            "law_gap_disposition_count",
            "tier_2_precondition",
            "adjudication_rule",
            "nonauthority_statement",
            "status",
        }
    ),
    "role": frozenset(
        _ENVELOPE_KEYS
        | {
            "tier",
            "source_slice_artifact_id",
            "corpus_sweep_artifact_id",
            "canonical_role_occurrence_ids",
            "role_label_class_rows",
            "role_label_class_count",
            "role_label_class_domain_sha256",
            "role_assignment_rows",
            "role_assignment_count",
            "role_assignment_keyset_sha256",
            "role_assignment_domain_sha256",
            "unassigned_role_anchor_rows",
            "unassigned_role_anchor_count",
            "nonauthority_statement",
            "status",
        }
    ),
    "repeat": frozenset(
        _ENVELOPE_KEYS
        | {
            "tier",
            "source_slice_artifact_id",
            "corpus_sweep_artifact_id",
            "outside_domain_repeat_disposition_rows",
            "outside_domain_repeat_disposition_count",
            "outside_domain_repeat_disposition_keyset_sha256",
            "outside_domain_repeat_disposition_domain_sha256",
            "relation_counts",
            "document_counts",
            "nonauthority_statement",
            "status",
        }
    ),
    "component": frozenset(
        _ENVELOPE_KEYS
        | {
            "tier",
            "source_slice_artifact_id",
            "corpus_sweep_artifact_id",
            "zero_parent_disposition_rows",
            "zero_parent_disposition_count",
            "zero_parent_disposition_domain_sha256",
            "unique_parent_assignment_rows",
            "unique_parent_assignment_count",
            "unique_parent_assignment_domain_sha256",
            "multi_parent_ambiguity_rows",
            "multi_parent_ambiguity_count",
            "multi_parent_ambiguity_domain_sha256",
            "complete_component_resolution_count",
            "complete_component_resolution_keyset_sha256",
            "complete_component_resolution_domain_sha256",
            "serialized_parent_cardinality_counts",
            "raw_cross_category_multi_parent_count",
            "eligible_cross_category_multi_parent_count",
            "eligible_ineligible_mixed_multi_parent_count",
            "ineligible_parent_reference_count",
            "nonauthority_statement",
            "status",
        }
    ),
    "gate": frozenset(
        _ENVELOPE_KEYS
        | {
            "tier",
            "design_prefix_identity",
            "source_slice_artifact_id",
            "artifact_identity_rows",
            "artifact_identity_count",
            "artifact_identity_domain_sha256",
            "pilot_census",
            "role_law_status",
            "outside_domain_repeat_law_status",
            "component_parent_law_status",
            "predecessor_input_status",
            "overall_repeat_catalog_coverage_status",
            "pilot_law_shape_status",
            "tier_2_protocol_status",
            "certification_status",
            "nonauthority_statement",
            "status",
        }
    ),
}

PILOT_DOCUMENT_ROW_KEYS = frozenset(
    {
        "document_source_position",
        "era_id",
        "annotation_path",
        "source_document_id",
        "schema_version",
        "annotation_byte_size",
        "annotation_raw_sha256",
        "annotation_content_sha256",
        "pilot_role",
        "selection_tags",
    }
)
ROLE_CLASS_ROW_KEYS = frozenset(
    {
        "role_label_class_id",
        "role",
        "exact_label",
        "exact_label_sha256",
        "member_occurrence_ids",
        "member_count",
        "member_keyset_sha256",
        "occurrence_equivalence_claimed",
        "alias_class_claimed",
        "status",
    }
)
ROLE_ASSIGNMENT_ROW_KEYS = frozenset(
    {
        "role_assignment_id",
        "document_source_position",
        "source_document_id",
        "source_classification_id",
        "role_anchor_occurrence_id",
        "assigned_role",
        "printed_identifier",
        "exact_label",
        "exact_label_sha256",
        "role_label_class_id",
        "proof_form",
        "alias_admitted_by_assignment",
        "occurrence_equivalence_claimed",
        "status",
    }
)
OUTSIDE_REPEAT_ROW_KEYS = frozenset(
    {
        "outside_domain_repeat_disposition_id",
        "document_source_position",
        "source_document_id",
        "source_local_evidence_id",
        "source_instruction_occurrence_id",
        "relation",
        "handoff_status",
        "evidence_occurrence_ids",
        "unresolved_target_reference",
        "terminal_disposition",
        "alias_anchor_occurrence_id",
        "referenced_anchor_occurrence_id",
        "alias_admitted",
        "occurrence_equivalence_claimed",
        "universal_repeat_coverage_arm_satisfied",
        "status",
    }
)
PARENT_CANDIDATE_ROW_KEYS = frozenset(
    {
        "parent_occurrence_id",
        "parent_occurrence_kind",
        "parent_category",
        "eligible_parent",
        "derived_slot_kind",
        "ineligibility_reason",
    }
)
COMPONENT_SHAPE_ROW_KEYS = frozenset(
    {
        "component_parent_resolution_id",
        "document_source_position",
        "source_document_id",
        "source_classification_id",
        "component_anchor_occurrence_id",
        "component_kind",
        "serialized_parent_cardinality",
        "eligible_parent_cardinality",
        "parent_candidate_rows",
        "parent_candidate_count",
        "parent_candidate_domain_sha256",
        "raw_parent_category_ambiguity",
        "eligible_parent_category_ambiguity",
        "eligible_ineligible_mixed_ambiguity",
        "disposition",
        "forced_parent_selection",
        "tier_2_unique_parent_arm_eligible",
        "r_q_relationship_emitted",
        "status",
    }
)
DOC036_DEFECT_ROW_KEYS = frozenset(
    {
        "predecessor_adjudication_id",
        "document_source_position",
        "source_document_id",
        "source_classification_id",
        "source_occurrence_id",
        "source_classification",
        "occurrence_kind",
        "serialized_node_domain",
        "correct_node_domain",
        "disposition",
        "law_gap_admitted",
        "component_slot_admitted",
        "required_action",
        "adjudicative_rationale",
        "status",
    }
)
PROOF_DEFECT_ROW_KEYS = frozenset(
    {
        "predecessor_adjudication_id",
        "document_source_position",
        "source_document_id",
        "source_local_evidence_id",
        "relation",
        "source_instruction_occurrence_ids",
        "alias_anchor_occurrence_ids",
        "canonical_anchor_occurrence_ids",
        "evidence_occurrence_ids",
        "endpoint_occurrence_kinds",
        "endpoint_raw_node_domains",
        "endpoint_classifications",
        "defect_flags",
        "disposition",
        "law_gap_admitted",
        "alias_admitted",
        "required_action",
        "adjudicative_rationale",
        "status",
    }
)
ARTIFACT_IDENTITY_ROW_KEYS = frozenset(
    {
        "artifact_role",
        "path",
        "schema_version",
        "artifact_id",
        "byte_size",
        "raw_sha256",
    }
)

PARENT_SOURCE_WITNESS_ROW_KEYS = frozenset(
    {
        "parent_source_witness_id",
        "document_source_position",
        "source_document_id",
        "source_classification_id",
        "parent_occurrence_id",
        "parent_occurrence_kind",
        "parent_classification",
        "status",
    }
)
UNRESOLVED_TARGET_REFERENCE_KEYS = frozenset(
    {
        "matched_text",
        "matched_utf8_sha256",
        "page_number",
        "utf8_byte_start",
        "utf8_byte_end",
    }
)
DEFECT_FLAG_KEYS = frozenset(
    {
        "touches_noncatalog_aggregate_endpoint",
        "occurrence_derived_domain_crossing",
        "corrected_catalog_domain_crossing",
        "raw_node_domain_crossing",
        "context_remuneration_mix",
        "head_spouse_mix",
    }
)
DESIGN_PREFIX_IDENTITY_KEYS = frozenset(
    {"path", "byte_size", "sha256", "identity_scope"}
)
SOURCE_CORPUS_IDENTITY_KEYS = frozenset(
    {
        "source_branch_label",
        "source_commit",
        "document_count",
        "stage2_protocol_identity",
        "era_seal_rows",
        "era_seal_count",
        "era_seal_domain_sha256",
    }
)
STAGE2_PROTOCOL_IDENTITY_KEYS = frozenset({"path", "byte_size", "raw_sha256"})
ERA_SEAL_IDENTITY_ROW_KEYS = frozenset(
    {
        "era_id",
        "era_order_position",
        "document_source_positions",
        "seal_commit",
        "path",
        "byte_size",
        "raw_sha256",
        "content_sha256",
    }
)


def _validate_nonauthority(value: Any) -> None:
    _require(value == _nonauthority_statement(), "nonauthority drift")


def _validate_source_corpus_identity(value: Mapping[str, Any]) -> None:
    label = "source corpus identity"
    _require_exact_keys(value, SOURCE_CORPUS_IDENTITY_KEYS, label)
    _require(
        value["source_branch_label"] == SOURCE_BRANCH_LABEL, f"{label}: branch"
    )
    _require(value["source_commit"] == SOURCE_COMMIT, f"{label}: commit")
    _require(value["document_count"] == 81, f"{label}: document count")
    protocol = value["stage2_protocol_identity"]
    _require(isinstance(protocol, dict), f"{label}: protocol")
    _require_exact_keys(
        protocol, STAGE2_PROTOCOL_IDENTITY_KEYS, f"{label}: protocol"
    )
    _require(
        protocol
        == {
            "path": "docs/analysis/rq_stage2_protocol.md",
            "byte_size": 59_048,
            "raw_sha256": (
                "313234c381045f155b0acf9e0b35fd7818aa60e905e1a9934d2c4b5bec816bd7"
            ),
        },
        f"{label}: protocol identity",
    )
    seal_rows = value["era_seal_rows"]
    _require(isinstance(seal_rows, list), f"{label}: era seals")
    _require(
        value["era_seal_count"] == len(seal_rows) == 6, f"{label}: seal count"
    )
    _require(
        value["era_seal_domain_sha256"] == _domain_sha(seal_rows),
        f"{label}: seal digest",
    )
    for row, expected in zip(seal_rows, ERA_SEALS, strict=True):
        _require_exact_keys(
            row, ERA_SEAL_IDENTITY_ROW_KEYS, f"{label}: era seal"
        )
        expected_row = {
            "era_id": expected["era_id"],
            "era_order_position": expected["era_order_position"],
            "document_source_positions": list(expected["positions"]),
            "seal_commit": expected["seal_commit"],
            "path": expected["path"],
            "byte_size": expected["byte_size"],
            "raw_sha256": expected["raw_sha256"],
            "content_sha256": expected["content_sha256"],
        }
        _require(row == expected_row, f"{label}: era seal identity")


def _validate_row_digests(
    artifact: Mapping[str, Any],
    row_key: str,
    count_key: str,
    domain_key: str,
) -> list[dict[str, Any]]:
    rows = artifact[row_key]
    _require(isinstance(rows, list), f"{row_key}: not array")
    count = _require_int(artifact[count_key], count_key)
    _require(count == len(rows), f"{count_key}: drift")
    _require(artifact[domain_key] == _domain_sha(rows), f"{domain_key}: drift")
    return rows


def _require_string(value: Any, label: str) -> str:
    _require(
        isinstance(value, str) and value != "", f"{label}: expected string"
    )
    return value


def _require_boolean(value: Any, label: str) -> bool:
    _require(isinstance(value, bool), f"{label}: expected boolean")
    return value


def _validate_role_class_row(row: Mapping[str, Any], label: str) -> None:
    _require_exact_keys(row, ROLE_CLASS_ROW_KEYS, label)
    role = row["role"]
    _require(role in ROLE_ORDER, f"{label}: unknown role")
    exact_label = _require_string(row["exact_label"], f"{label}: exact label")
    label_sha = _sha256(exact_label.encode("utf-8"))
    _require(row["exact_label_sha256"] == label_sha, f"{label}: label digest")
    _require(
        row["role_label_class_id"]
        == _row_id("a12-role-exact-label-class:", [role, label_sha]),
        f"{label}: class ID",
    )
    members = row["member_occurrence_ids"]
    _require(isinstance(members, list) and members, f"{label}: empty members")
    _require(
        all(
            isinstance(value, str)
            and value.startswith("psid-questionnaire-occurrence:")
            for value in members
        ),
        f"{label}: invalid member ID",
    )
    _require(len(set(members)) == len(members), f"{label}: duplicate member")
    _require_int(row["member_count"], f"{label}: member count")
    _require(row["member_count"] == len(members), f"{label}: member count")
    _require(
        row["member_keyset_sha256"] == _keyset_sha(members),
        f"{label}: member digest",
    )
    _require(
        row["occurrence_equivalence_claimed"] is False,
        f"{label}: occurrence equivalence claimed",
    )
    _require(
        row["alias_class_claimed"] is False,
        f"{label}: alias class claimed",
    )
    _require(
        row["status"] == "role_membership_class_only",
        f"{label}: status",
    )


def _validate_role_assignment_row(
    row: Mapping[str, Any],
    class_by_id: Mapping[str, Mapping[str, Any]],
) -> None:
    label = "role assignment row"
    _require_exact_keys(row, ROLE_ASSIGNMENT_ROW_KEYS, label)
    role = row["assigned_role"]
    _require(role in ROLE_ORDER, f"{label}: unknown assigned role")
    class_id = row["role_label_class_id"]
    _require(class_id in class_by_id, f"{label}: dangling role class")
    class_row = class_by_id[class_id]
    _require(
        role == class_row["role"], f"{label}: assigned role/class mismatch"
    )
    _require(
        row["exact_label"] == class_row["exact_label"],
        f"{label}: exact label/class mismatch",
    )
    _require(
        row["exact_label_sha256"] == class_row["exact_label_sha256"],
        f"{label}: label digest/class mismatch",
    )
    occurrence_id = _require_string(
        row["role_anchor_occurrence_id"], f"{label}: occurrence ID"
    )
    _require(
        occurrence_id in class_row["member_occurrence_ids"],
        f"{label}: occurrence absent from role class",
    )
    _require(
        row["proof_form"] == "exact_label_class_role_assignment_non_alias",
        f"{label}: proof form",
    )
    _require(
        row["alias_admitted_by_assignment"] is False,
        f"{label}: alias admitted",
    )
    _require(
        row["occurrence_equivalence_claimed"] is False,
        f"{label}: occurrence equivalence claimed",
    )
    _require(
        row["status"] == "assigned_noncanonical_role_anchor",
        f"{label}: status",
    )
    _require(
        row["role_assignment_id"]
        == _row_id(
            "a12-pilot-role-assignment:",
            [
                row["source_document_id"],
                occurrence_id,
                role,
                class_id,
                row["proof_form"],
            ],
        ),
        f"{label}: assignment ID",
    )
    printed_identifier = row["printed_identifier"]
    _require(
        printed_identifier is None or isinstance(printed_identifier, str),
        f"{label}: printed identifier",
    )


def _validate_outside_repeat_row(row: Mapping[str, Any], label: str) -> None:
    _require_exact_keys(row, OUTSIDE_REPEAT_ROW_KEYS, label)
    instruction_id = _require_string(
        row["source_instruction_occurrence_id"], f"{label}: instruction"
    )
    _require(row["relation"] in ALLOWED_REPEAT_RELATIONS, f"{label}: relation")
    _require(
        row["handoff_status"] == "local_target_outside_rq_annotation_domain",
        f"{label}: handoff status",
    )
    _require(
        row["evidence_occurrence_ids"] == [instruction_id],
        f"{label}: evidence is not singleton self",
    )
    unresolved = row["unresolved_target_reference"]
    _require(isinstance(unresolved, dict), f"{label}: unresolved target")
    _require_exact_keys(
        unresolved,
        UNRESOLVED_TARGET_REFERENCE_KEYS,
        f"{label}: unresolved target",
    )
    matched_text = _require_string(
        unresolved["matched_text"], f"{label}: unresolved matched text"
    )
    _require(
        unresolved["matched_utf8_sha256"]
        == _sha256(matched_text.encode("utf-8")),
        f"{label}: unresolved text digest",
    )
    page_number = _require_int(unresolved["page_number"], f"{label}: page")
    byte_start = _require_int(
        unresolved["utf8_byte_start"], f"{label}: byte start"
    )
    byte_end = _require_int(unresolved["utf8_byte_end"], f"{label}: byte end")
    _require(page_number > 0 and 0 <= byte_start < byte_end, f"{label}: span")
    _require(
        byte_end - byte_start == len(matched_text.encode("utf-8")),
        f"{label}: span length",
    )
    _require(
        row["terminal_disposition"] == "outside_r_q_domain_no_alias_admitted",
        f"{label}: terminal disposition",
    )
    _require(row["alias_anchor_occurrence_id"] is None, f"{label}: alias")
    _require(
        row["referenced_anchor_occurrence_id"] is None,
        f"{label}: referenced anchor",
    )
    _require(row["alias_admitted"] is False, f"{label}: alias admitted")
    _require(
        row["occurrence_equivalence_claimed"] is False,
        f"{label}: occurrence equivalence claimed",
    )
    _require(
        row["universal_repeat_coverage_arm_satisfied"] is True,
        f"{label}: universal arm",
    )
    _require(
        row["status"] == "terminal_nonauthority_disposition",
        f"{label}: status",
    )
    _require(
        row["outside_domain_repeat_disposition_id"]
        == _row_id(
            "a12-outside-rq-repeat-disposition:",
            [
                row["source_document_id"],
                instruction_id,
                row["source_local_evidence_id"],
                row["relation"],
                unresolved,
            ],
        ),
        f"{label}: disposition ID",
    )


def _validate_parent_source_witness_row(row: Mapping[str, Any]) -> None:
    label = "parent source witness row"
    _require_exact_keys(row, PARENT_SOURCE_WITNESS_ROW_KEYS, label)
    _require_int(row["document_source_position"], f"{label}: position")
    _require(
        row["parent_occurrence_kind"]
        in {*PARENT_KIND_TO_CATEGORY, *INELIGIBLE_PARENT_CATEGORY},
        f"{label}: occurrence kind",
    )
    _require(
        row["status"] == "pinned_source_parent_witness",
        f"{label}: status",
    )
    _require(
        row["parent_source_witness_id"]
        == _row_id(
            "a12-parent-source-witness:",
            [
                row["source_document_id"],
                row["source_classification_id"],
                row["parent_occurrence_id"],
                row["parent_occurrence_kind"],
            ],
        ),
        f"{label}: witness ID",
    )


def _validate_parent_candidate_row(
    component_kind: str,
    document_source_position: int,
    candidate: Mapping[str, Any],
    source_witness_by_key: Mapping[tuple[int, str], Mapping[str, Any]],
) -> None:
    label = "parent candidate row"
    _require_exact_keys(candidate, PARENT_CANDIDATE_ROW_KEYS, label)
    occurrence_kind = candidate["parent_occurrence_kind"]
    _require(
        occurrence_kind
        in {*PARENT_KIND_TO_CATEGORY, *INELIGIBLE_PARENT_CATEGORY},
        f"{label}: unsupported occurrence kind",
    )
    source_key = (document_source_position, candidate["parent_occurrence_id"])
    _require(
        source_key in source_witness_by_key, f"{label}: no source witness"
    )
    _require(
        source_witness_by_key[source_key]["parent_occurrence_kind"]
        == occurrence_kind,
        f"{label}: source witness kind mismatch",
    )
    if occurrence_kind in PARENT_KIND_TO_CATEGORY:
        expected_category = PARENT_KIND_TO_CATEGORY[occurrence_kind]
        expected_slot = (
            "context_only"
            if expected_category == "source_job"
            and component_kind == "source_context"
            else (
                "remuneration_component"
                if expected_category == "source_job"
                else expected_category.removesuffix("_sentinel")
            )
        )
        _require(candidate["eligible_parent"] is True, f"{label}: eligibility")
        _require(
            candidate["parent_category"] == expected_category,
            f"{label}: category equation",
        )
        _require(
            candidate["derived_slot_kind"] == expected_slot,
            f"{label}: derived slot equation",
        )
        _require(
            candidate["ineligibility_reason"] is None,
            f"{label}: eligible reason",
        )
    else:
        _require(
            candidate["eligible_parent"] is False, f"{label}: eligibility"
        )
        _require(
            candidate["parent_category"]
            == INELIGIBLE_PARENT_CATEGORY[occurrence_kind],
            f"{label}: ineligible category equation",
        )
        _require(candidate["derived_slot_kind"] is None, f"{label}: slot")
        _require(
            candidate["ineligibility_reason"]
            == "parent_occurrence_kind_outside_allowed_equations",
            f"{label}: ineligibility reason",
        )


def _validate_component_shape_row(
    row: Mapping[str, Any],
    source_witness_by_key: Mapping[tuple[int, str], Mapping[str, Any]],
    label: str,
) -> None:
    _require_exact_keys(row, COMPONENT_SHAPE_ROW_KEYS, label)
    component_kind = row["component_kind"]
    _require(component_kind in COMPONENT_KINDS, f"{label}: component kind")
    position = _require_int(
        row["document_source_position"], f"{label}: source position"
    )
    candidates = row["parent_candidate_rows"]
    _require(isinstance(candidates, list), f"{label}: candidates")
    for candidate in candidates:
        _require(isinstance(candidate, dict), f"{label}: candidate object")
        _validate_parent_candidate_row(
            component_kind, position, candidate, source_witness_by_key
        )
    parent_ids = [
        candidate["parent_occurrence_id"] for candidate in candidates
    ]
    _require(
        len(set(parent_ids)) == len(parent_ids), f"{label}: duplicate parent"
    )
    raw_count = len(candidates)
    eligible_count = sum(
        candidate["eligible_parent"] for candidate in candidates
    )
    _require(
        row["serialized_parent_cardinality"] == raw_count,
        f"{label}: serialized cardinality",
    )
    _require(row["parent_candidate_count"] == raw_count, f"{label}: count")
    _require(
        row["eligible_parent_cardinality"] == eligible_count,
        f"{label}: eligible cardinality",
    )
    _require(
        row["parent_candidate_domain_sha256"] == _domain_sha(candidates),
        f"{label}: candidate domain",
    )
    expected_disposition = (
        "zero_parent_terminal_disposition"
        if raw_count == 0
        else (
            "unique_parent_assignment"
            if raw_count == 1 and eligible_count == 1
            else (
                "zero_lawful_parent_terminal_disposition"
                if raw_count == 1
                else "multi_parent_ambiguity_no_selection"
            )
        )
    )
    _require(
        row["disposition"] == expected_disposition,
        f"{label}: disposition equation",
    )
    categories = {candidate["parent_category"] for candidate in candidates}
    eligible_categories = {
        candidate["parent_category"]
        for candidate in candidates
        if candidate["eligible_parent"]
    }
    expected_raw_cross = raw_count > 1 and len(categories) > 1
    expected_eligible_cross = len(eligible_categories) > 1
    expected_mixed = (
        raw_count > 1
        and any(candidate["eligible_parent"] for candidate in candidates)
        and any(not candidate["eligible_parent"] for candidate in candidates)
    )
    _require(
        row["raw_parent_category_ambiguity"] is expected_raw_cross,
        f"{label}: raw category ambiguity",
    )
    _require(
        row["eligible_parent_category_ambiguity"] is expected_eligible_cross,
        f"{label}: eligible category ambiguity",
    )
    _require(
        row["eligible_ineligible_mixed_ambiguity"] is expected_mixed,
        f"{label}: eligible/ineligible ambiguity",
    )
    _require(
        row["forced_parent_selection"] is False, f"{label}: forced parent"
    )
    _require(
        row["tier_2_unique_parent_arm_eligible"]
        is (expected_disposition == "unique_parent_assignment"),
        f"{label}: tier-2 unique-parent arm",
    )
    _require(
        row["r_q_relationship_emitted"] is False,
        f"{label}: pilot emitted R_Q",
    )
    _require(
        row["status"] == "recorded_nonauthority_shape",
        f"{label}: status",
    )
    _require(
        row["component_parent_resolution_id"]
        == _row_id(
            "a12-component-parent-resolution:",
            [
                row["source_document_id"],
                row["component_anchor_occurrence_id"],
                component_kind,
                expected_disposition,
                candidates,
            ],
        ),
        f"{label}: resolution ID",
    )


def _validate_doc036_defect_row(row: Mapping[str, Any]) -> None:
    label = "doc036 defect row"
    _require_exact_keys(row, DOC036_DEFECT_ROW_KEYS, label)
    _require(row["document_source_position"] == 36, f"{label}: position")
    expected_kind = AGGREGATE_CLASSIFICATION_TO_KIND.get(
        row["source_classification"]
    )
    _require(expected_kind == row["occurrence_kind"], f"{label}: kind")
    _require(
        row["serialized_node_domain"] == "component_slot",
        f"{label}: raw domain",
    )
    _require(
        row["correct_node_domain"] == "aggregate", f"{label}: corrected domain"
    )
    _require(
        row["disposition"] == "predecessor_seal_defect",
        f"{label}: disposition",
    )
    _require(row["law_gap_admitted"] is False, f"{label}: law gap admitted")
    _require(
        row["component_slot_admitted"] is False,
        f"{label}: component slot admitted",
    )
    _require(
        row["required_action"]
        == "reseal_document_036_with_aggregate_anchor_domain",
        f"{label}: required action",
    )
    _require(
        row["adjudicative_rationale"]
        == "aggregate_occurrence_kind_controls_node_domain_reseal_required",
        f"{label}: rationale",
    )
    _require(row["status"] == "blocked_predecessor_row", f"{label}: status")
    _require(
        row["predecessor_adjudication_id"]
        == _row_id(
            "a12-predecessor-doc036-aggregate-adjudication:",
            [
                row["source_document_id"],
                row["source_classification_id"],
                row["source_occurrence_id"],
                row["source_classification"],
                row["disposition"],
            ],
        ),
        f"{label}: adjudication ID",
    )


def _validate_proof_defect_row(row: Mapping[str, Any]) -> None:
    label = "proof defect row"
    _require_exact_keys(row, PROOF_DEFECT_ROW_KEYS, label)
    _require(
        row["relation"] in ALLOWED_LOCAL_EVIDENCE_RELATIONS,
        f"{label}: relation",
    )
    aliases = row["alias_anchor_occurrence_ids"]
    canonicals = row["canonical_anchor_occurrence_ids"]
    endpoint_kinds = row["endpoint_occurrence_kinds"]
    raw_domains = row["endpoint_raw_node_domains"]
    classifications = row["endpoint_classifications"]
    _require(isinstance(aliases, list) and aliases, f"{label}: aliases")
    _require(
        isinstance(canonicals, list) and canonicals, f"{label}: canonicals"
    )
    endpoint_count = len(aliases) + len(canonicals)
    _require(
        len(endpoint_kinds)
        == len(raw_domains)
        == len(classifications)
        == endpoint_count,
        f"{label}: endpoint projections",
    )
    expected_flags = {
        "touches_noncatalog_aggregate_endpoint": any(
            kind in AGGREGATE_OCCURRENCE_KINDS for kind in endpoint_kinds
        ),
        "occurrence_derived_domain_crossing": len(
            {_occurrence_catalog_domain(kind) for kind in endpoint_kinds}
        )
        > 1,
        "raw_node_domain_crossing": len(set(raw_domains)) > 1,
        "context_remuneration_mix": {
            "context_anchor",
            "remuneration_component_anchor",
        }.issubset(set(endpoint_kinds)),
        "head_spouse_mix": {ROLE_HEAD, ROLE_SPOUSE}.issubset(
            set(classifications)
        ),
    }
    expected_flags["corrected_catalog_domain_crossing"] = expected_flags[
        "occurrence_derived_domain_crossing"
    ]
    flags = row["defect_flags"]
    _require(isinstance(flags, dict), f"{label}: defect flags")
    _require_exact_keys(flags, DEFECT_FLAG_KEYS, f"{label}: defect flags")
    _require(flags == expected_flags, f"{label}: defect flag equations")
    _require(any(flags.values()), f"{label}: no defect")
    _require(
        row["disposition"] == "predecessor_seal_defect",
        f"{label}: disposition",
    )
    _require(row["law_gap_admitted"] is False, f"{label}: law gap admitted")
    _require(row["alias_admitted"] is False, f"{label}: alias admitted")
    _require(
        row["required_action"]
        == "readjudicate_source_row_and_reseal_before_tier_2",
        f"{label}: required action",
    )
    _require(
        row["adjudicative_rationale"]
        == "incompatible_endpoint_claim_cannot_be_admitted_as_alias_law_reseal_required",
        f"{label}: rationale",
    )
    _require(row["status"] == "blocked_predecessor_row", f"{label}: status")
    _require(
        row["predecessor_adjudication_id"]
        == _row_id(
            "a12-predecessor-local-proof-adjudication:",
            [
                row["source_document_id"],
                row["source_local_evidence_id"],
                flags,
                row["disposition"],
            ],
        ),
        f"{label}: adjudication ID",
    )


def validate_bundle(bundle: Mapping[str, Mapping[str, Any]]) -> None:
    """Validate a complete generated or committed pilot bundle."""
    _require(set(bundle) == set(OUTPUT_FILENAMES), "artifact bundle drift")
    for key, artifact in bundle.items():
        _require_exact_keys(
            artifact,
            ARTIFACT_TOP_LEVEL_KEYS[key],
            f"{key} artifact",
        )
        _validate_artifact_envelope(artifact, *ARTIFACT_SPECS[key])
        _validate_nonauthority(artifact["nonauthority_statement"])

    slice_artifact = bundle["slice"]
    _require_int(slice_artifact["tier"], "slice tier")
    _require(slice_artifact["tier"] == 1, "slice tier drift")
    design_identity = slice_artifact["design_prefix_identity"]
    _require(isinstance(design_identity, dict), "design prefix identity")
    _require_exact_keys(
        design_identity, DESIGN_PREFIX_IDENTITY_KEYS, "design prefix identity"
    )
    _require(
        design_identity
        == {
            "path": "docs/design/covered_earnings_correction.md",
            "byte_size": DESIGN_PREFIX_BYTES,
            "sha256": DESIGN_PREFIX_SHA256,
            "identity_scope": "immutable_revision_13_prefix",
        },
        "design prefix identity drift",
    )
    _validate_source_corpus_identity(slice_artifact["source_corpus_identity"])
    _require(
        slice_artifact["control_selection_rule"]
        == "earliest_source_order_noncarrier_in_each_era_with_zero_"
        "outside_domain_rows_zero_defective_populated_proof_rows_"
        "and_zero_aggregate_kind_component_slot_rows",
        "pilot control-selection rule drift",
    )
    _require(
        tuple(slice_artifact["pilot_document_positions"]) == PILOT_POSITIONS,
        "pilot positions drift",
    )
    pilot_rows = slice_artifact["pilot_document_rows"]
    _require(len(pilot_rows) == 16, "pilot document count drift")
    for row in pilot_rows:
        _require_exact_keys(row, PILOT_DOCUMENT_ROW_KEYS, "pilot document row")
        position = row["document_source_position"]
        _require(
            row["selection_tags"] == list(PILOT_TAGS[position]),
            "pilot tag drift",
        )
        _require(
            row["pilot_role"]
            == (
                "clean_era_control"
                if position in CONTROL_POSITIONS
                else "charter_pathology_carrier"
            ),
            "pilot role drift",
        )
    _require(
        [row["document_source_position"] for row in pilot_rows]
        == list(PILOT_POSITIONS),
        "pilot document order drift",
    )
    _require(
        slice_artifact["pilot_document_count"] == len(pilot_rows),
        "pilot document count mismatch",
    )
    _require(
        slice_artifact["pilot_document_position_domain_sha256"]
        == _domain_sha(list(PILOT_POSITIONS)),
        "pilot position digest drift",
    )
    _require(
        slice_artifact["pilot_annotation_raw_byte_count"]
        == sum(row["annotation_byte_size"] for row in pilot_rows),
        "pilot byte count drift",
    )
    _require(
        {
            row["document_source_position"]
            for row in pilot_rows
            if row["pilot_role"] == "clean_era_control"
        }
        == set(CONTROL_POSITIONS),
        "control membership drift",
    )

    census = slice_artifact["pilot_census"]
    expected_census = {
        "document_count": 16,
        "questionnaire_page_count": 1_571,
        "questionnaire_occurrence_count": 13_219,
        "flow_branch_count": 3_480,
        "local_anchor_count": 6_123,
        "field_purpose_count": 3_240,
        "role_anchor_count": 949,
        "head_role_anchor_count": 530,
        "spouse_role_anchor_count": 419,
        "job_anchor_count": 1_534,
        "source_component_anchor_count": 3_095,
        "source_context_anchor_count": 2_247,
        "source_remuneration_anchor_count": 848,
        "aggregate_anchor_count": 545,
        "repeat_occurrence_count": 376,
        "local_evidence_row_count": 418,
        "valid_direct_proof_instruction_count": 106,
        "outside_domain_instruction_count": 34,
        "incompatible_proof_instruction_count": 9,
        "valid_and_incompatible_instruction_overlap_count": 1,
        "otherwise_unresolved_instruction_count": 228,
        "raw_cross_category_multi_parent_count": 86,
        "eligible_cross_category_multi_parent_count": 86,
        "eligible_ineligible_mixed_multi_parent_count": 0,
        "ineligible_parent_reference_count": 22,
    }
    for key, expected in expected_census.items():
        _require(census[key] == expected, f"pilot census drift: {key}")
    _require(
        census["local_evidence_shape_counts"]
        == {
            "both_endpoints": 156,
            "no_endpoints": 254,
            "partial_endpoints": 8,
        },
        "pilot evidence-shape census drift",
    )
    _require(
        census["serialized_component_parent_cardinality"]
        == {"zero": 1_466, "one": 1_329, "multiple": 300},
        "pilot raw parent census drift",
    )

    sweep = bundle["sweeps"]
    _require(
        sweep["document_positions_swept"] == list(range(1, 82))
        and sweep["document_count"] == 81,
        "corpus sweep document domain drift",
    )
    role_classes = _validate_row_digests(
        sweep,
        "role_exact_label_class_rows",
        "role_exact_label_class_count",
        "role_exact_label_class_domain_sha256",
    )
    _require(len(role_classes) == 273, "role class count drift")
    _require(
        sum(row["member_count"] for row in role_classes) == 10_521,
        "role sweep member count drift",
    )
    _require(
        sum(row["role"] == ROLE_HEAD for row in role_classes) == 86,
        "head label class count drift",
    )
    _require(
        sum(row["role"] == ROLE_SPOUSE for row in role_classes) == 187,
        "spouse label class count drift",
    )
    for row in role_classes:
        _validate_role_class_row(row, "role sweep class row")
    _require(
        len({row["exact_label"] for row in role_classes}) == len(role_classes),
        "role sweep duplicate exact-label class",
    )
    sweep_role_member_ids = [
        member
        for row in role_classes
        for member in row["member_occurrence_ids"]
    ]
    _require(
        len(set(sweep_role_member_ids)) == len(sweep_role_member_ids),
        "role sweep member occurs in multiple classes",
    )
    _require(
        sweep["role_anchor_count"] == len(sweep_role_member_ids),
        "role sweep anchor count drift",
    )
    _require(
        sweep["role_noncanonical_assignment_reach_count"]
        == len(sweep_role_member_ids) - len(ROLE_CANONICALS),
        "role sweep noncanonical reach drift",
    )
    _require(
        sweep["role_cross_classification_label_count"] == 0,
        "role sweep cross-classification label",
    )
    _require(sweep["role_unreached_anchor_rows"] == [], "unreached roles")
    _require(sweep["role_unreached_anchor_count"] == 0, "unreached count")
    _require(
        sweep["role_exact_label_class_domain_sha256"]
        == PINNED_SWEEP_DOMAIN_SHA256["role_exact_label_class"],
        "role sweep pinned source projection drift",
    )

    sweep_repeat_rows = _validate_row_digests(
        sweep,
        "outside_domain_repeat_shape_rows",
        "outside_domain_repeat_shape_count",
        "outside_domain_repeat_shape_domain_sha256",
    )
    _require(len(sweep_repeat_rows) == 34, "outside repeat sweep drift")
    for row in sweep_repeat_rows:
        _validate_outside_repeat_row(row, "repeat sweep row")
    _require(
        sweep["outside_domain_repeat_shape_domain_sha256"]
        == PINNED_SWEEP_DOMAIN_SHA256["outside_domain_repeat_shape"],
        "repeat sweep pinned source projection drift",
    )

    parent_source_witness_rows = _validate_row_digests(
        sweep,
        "parent_source_witness_rows",
        "parent_source_witness_count",
        "parent_source_witness_domain_sha256",
    )
    for row in parent_source_witness_rows:
        _validate_parent_source_witness_row(row)
    _require(
        sweep["parent_source_witness_keyset_sha256"]
        == _keyset_sha(
            [
                row["parent_source_witness_id"]
                for row in parent_source_witness_rows
            ]
        ),
        "parent source witness keyset drift",
    )
    _require(
        sweep["parent_source_witness_keyset_sha256"]
        == PINNED_SWEEP_DOMAIN_SHA256["parent_source_witness_keyset"]
        and sweep["parent_source_witness_domain_sha256"]
        == PINNED_SWEEP_DOMAIN_SHA256["parent_source_witness"],
        "parent witness pinned source projection drift",
    )
    source_witness_by_key = {
        (row["document_source_position"], row["parent_occurrence_id"]): row
        for row in parent_source_witness_rows
    }
    _require(
        len(source_witness_by_key) == len(parent_source_witness_rows),
        "duplicate parent source witness",
    )

    component_shapes = _validate_row_digests(
        sweep,
        "component_parent_shape_rows",
        "component_parent_shape_count",
        "component_parent_shape_domain_sha256",
    )
    _require(len(component_shapes) == 21_283, "component sweep count drift")
    for row in component_shapes:
        _validate_component_shape_row(
            row, source_witness_by_key, "component sweep row"
        )
    _require(
        sweep["component_parent_shape_keyset_sha256"]
        == _keyset_sha(
            [row["component_parent_resolution_id"] for row in component_shapes]
        ),
        "component sweep keyset drift",
    )
    _require(
        sweep["component_parent_shape_keyset_sha256"]
        == PINNED_SWEEP_DOMAIN_SHA256["component_parent_shape_keyset"]
        and sweep["component_parent_shape_domain_sha256"]
        == PINNED_SWEEP_DOMAIN_SHA256["component_parent_shape"],
        "component sweep pinned source projection drift",
    )
    _require(
        sweep["serialized_parent_cardinality_counts"]
        == {"zero": 10_664, "one": 8_809, "multiple": 1_810},
        "full raw parent census drift",
    )
    _require(
        sweep["component_parent_disposition_counts"]
        == {
            "multi_parent_ambiguity_no_selection": 1_810,
            "unique_parent_assignment": 8_779,
            "zero_lawful_parent_terminal_disposition": 30,
            "zero_parent_terminal_disposition": 10_664,
        },
        "full parent disposition census drift",
    )
    referenced_parent_source_keys = {
        (row["document_source_position"], candidate["parent_occurrence_id"])
        for row in component_shapes
        for candidate in row["parent_candidate_rows"]
    }
    _require(
        referenced_parent_source_keys == set(source_witness_by_key),
        "parent source witness coverage drift",
    )
    _require(
        sweep["raw_cross_category_multi_parent_count"] == 466,
        "raw cross-category parent census drift",
    )
    _require(
        sweep["eligible_cross_category_multi_parent_count"] == 462,
        "eligible cross-category parent census drift",
    )
    _require(
        sweep["eligible_ineligible_mixed_multi_parent_count"] == 4,
        "eligible/ineligible parent census drift",
    )
    _require(
        sweep["ineligible_parent_reference_count"] == 34,
        "ineligible parent census drift",
    )

    predecessor = bundle["predecessor"]
    doc036_rows = _validate_row_digests(
        predecessor,
        "doc036_aggregate_component_slot_rows",
        "doc036_aggregate_component_slot_count",
        "doc036_aggregate_component_slot_domain_sha256",
    )
    proof_defects = _validate_row_digests(
        predecessor,
        "defective_populated_local_proof_rows",
        "defective_populated_local_proof_count",
        "defective_populated_local_proof_domain_sha256",
    )
    _require(len(doc036_rows) == 8, "doc036 defect count drift")
    _require(len(proof_defects) == 42, "proof defect count drift")
    for row in doc036_rows:
        _validate_doc036_defect_row(row)
    for row in proof_defects:
        _validate_proof_defect_row(row)
    _require(
        predecessor["defective_populated_local_proof_keyset_sha256"]
        == _keyset_sha(
            [row["source_local_evidence_id"] for row in proof_defects]
        ),
        "proof defect keyset drift",
    )
    _require(
        predecessor["law_gap_disposition_count"] == 0,
        "predecessor law gap was admitted",
    )
    _require(
        predecessor["seal_defect_disposition_count"] == 50,
        "predecessor seal defect count drift",
    )
    _require(
        predecessor["adjudication_rule"]
        == "incompatible_predecessor_endpoint_or_node_domain_claims_"
        "remain_seal_defects_and_cannot_create_catalog_law",
        "predecessor adjudication rule drift",
    )
    _require(
        all(
            row["disposition"] == "predecessor_seal_defect"
            for row in [*doc036_rows, *proof_defects]
        ),
        "predecessor disposition drift",
    )
    _require(
        predecessor["defect_category_counts"]
        == {
            "touches_noncatalog_aggregate_endpoint": 28,
            "occurrence_derived_domain_crossing": 19,
            "corrected_catalog_domain_crossing": 19,
            "raw_node_domain_crossing": 18,
            "context_remuneration_mix": 15,
            "head_spouse_mix": 4,
        },
        "predecessor category census drift",
    )

    role = bundle["role"]
    pilot_role_classes = _validate_row_digests(
        role,
        "role_label_class_rows",
        "role_label_class_count",
        "role_label_class_domain_sha256",
    )
    _require(len(pilot_role_classes) == 69, "pilot role class count drift")
    for row in pilot_role_classes:
        _validate_role_class_row(row, "pilot role class row")
    pilot_class_by_id = {
        row["role_label_class_id"]: row for row in pilot_role_classes
    }
    _require(
        len(pilot_class_by_id) == len(pilot_role_classes),
        "duplicate pilot role class ID",
    )
    assignments = _validate_row_digests(
        role,
        "role_assignment_rows",
        "role_assignment_count",
        "role_assignment_domain_sha256",
    )
    _require(len(assignments) == 947, "pilot role assignment count drift")
    for row in assignments:
        _validate_role_assignment_row(row, pilot_class_by_id)
    _require(
        role["role_assignment_keyset_sha256"]
        == _keyset_sha([row["role_assignment_id"] for row in assignments]),
        "role assignment keyset drift",
    )
    _require(
        len({row["role_anchor_occurrence_id"] for row in assignments})
        == len(assignments),
        "duplicate role assignment",
    )
    pilot_members = {
        member
        for row in pilot_role_classes
        for member in row["member_occurrence_ids"]
    }
    assignment_members = {
        row["role_anchor_occurrence_id"] for row in assignments
    }
    canonical_ids = set(role["canonical_role_occurrence_ids"].values())
    _require(
        role["canonical_role_occurrence_ids"] == ROLE_CANONICALS,
        "canonical role identities drift",
    )
    _require(
        assignment_members == pilot_members - canonical_ids,
        "pilot role class members are not assigned exactly once",
    )
    _require(
        canonical_ids <= pilot_members
        and not (canonical_ids & assignment_members),
        "canonical role partition drift",
    )
    full_class_by_id = {
        row["role_label_class_id"]: row for row in role_classes
    }
    for pilot_class in pilot_role_classes:
        class_id = pilot_class["role_label_class_id"]
        _require(
            class_id in full_class_by_id, "pilot role class absent from sweep"
        )
        full_class = full_class_by_id[class_id]
        _require(
            pilot_class["role"] == full_class["role"]
            and pilot_class["exact_label"] == full_class["exact_label"]
            and set(pilot_class["member_occurrence_ids"])
            <= set(full_class["member_occurrence_ids"]),
            "pilot role class is not a sweep projection",
        )
    _require(role["unassigned_role_anchor_rows"] == [], "unassigned roles")
    _require(role["unassigned_role_anchor_count"] == 0, "unassigned count")

    repeat = bundle["repeat"]
    repeat_rows = _validate_row_digests(
        repeat,
        "outside_domain_repeat_disposition_rows",
        "outside_domain_repeat_disposition_count",
        "outside_domain_repeat_disposition_domain_sha256",
    )
    _require(len(repeat_rows) == 34, "pilot repeat count drift")
    _require(
        repeat["relation_counts"]
        == {
            "explicit_cross_reference": 17,
            "explicit_repeat_instruction": 17,
        },
        "repeat relation census drift",
    )
    _require(
        repeat["document_counts"]
        == {"14": 2, "40": 22, "56": 5, "58": 4, "66": 1},
        "repeat document census drift",
    )
    for row in repeat_rows:
        _validate_outside_repeat_row(row, "repeat pilot row")
    _require(
        repeat["outside_domain_repeat_disposition_keyset_sha256"]
        == _keyset_sha(
            [
                row["outside_domain_repeat_disposition_id"]
                for row in repeat_rows
            ]
        ),
        "repeat pilot keyset drift",
    )
    _require(
        repeat_rows == sweep_repeat_rows,
        "pilot outside-domain repeat rows differ from exhaustive sweep",
    )

    component = bundle["component"]
    zero_rows = _validate_row_digests(
        component,
        "zero_parent_disposition_rows",
        "zero_parent_disposition_count",
        "zero_parent_disposition_domain_sha256",
    )
    unique_rows = _validate_row_digests(
        component,
        "unique_parent_assignment_rows",
        "unique_parent_assignment_count",
        "unique_parent_assignment_domain_sha256",
    )
    ambiguity_rows = _validate_row_digests(
        component,
        "multi_parent_ambiguity_rows",
        "multi_parent_ambiguity_count",
        "multi_parent_ambiguity_domain_sha256",
    )
    _require(len(zero_rows) == 1_488, "pilot zero-parent count drift")
    _require(len(unique_rows) == 1_307, "pilot unique-parent count drift")
    _require(len(ambiguity_rows) == 300, "pilot ambiguity count drift")
    all_component_rows = [*zero_rows, *unique_rows, *ambiguity_rows]
    for row in all_component_rows:
        _validate_component_shape_row(
            row, source_witness_by_key, "component pilot row"
        )
    _require(
        component["complete_component_resolution_count"]
        == len(all_component_rows)
        == 3_095,
        "pilot component partition drift",
    )
    _require(
        len(
            {
                row["component_anchor_occurrence_id"]
                for row in all_component_rows
            }
        )
        == len(all_component_rows),
        "duplicate component resolution",
    )
    _require(
        component["complete_component_resolution_keyset_sha256"]
        == _keyset_sha(
            [
                row["component_parent_resolution_id"]
                for row in all_component_rows
            ]
        ),
        "pilot component complete keyset drift",
    )
    _require(
        component["complete_component_resolution_domain_sha256"]
        == _domain_sha(all_component_rows),
        "pilot component complete domain drift",
    )
    for row in zero_rows:
        _require(
            row["disposition"]
            in {
                "zero_parent_terminal_disposition",
                "zero_lawful_parent_terminal_disposition",
            },
            "zero disposition drift",
        )
    for row in unique_rows:
        _require(
            row["disposition"] == "unique_parent_assignment",
            "unique partition disposition drift",
        )
    for row in ambiguity_rows:
        _require(
            row["disposition"] == "multi_parent_ambiguity_no_selection",
            "ambiguity partition disposition drift",
        )
    pilot_component_by_id = {
        row["component_parent_resolution_id"]: row
        for row in all_component_rows
    }
    expected_pilot_component_rows = [
        row
        for row in component_shapes
        if row["document_source_position"] in PILOT_POSITIONS
    ]
    _require(
        pilot_component_by_id
        == {
            row["component_parent_resolution_id"]: row
            for row in expected_pilot_component_rows
        },
        "pilot component rows differ from exhaustive sweep projection",
    )
    _require(
        component["serialized_parent_cardinality_counts"]
        == {"zero": 1_466, "one": 1_329, "multiple": 300},
        "pilot component raw census drift",
    )
    _require(
        component["raw_cross_category_multi_parent_count"] == 86
        and component["eligible_cross_category_multi_parent_count"] == 86
        and component["eligible_ineligible_mixed_multi_parent_count"] == 0,
        "pilot component ambiguity census drift",
    )
    _require(
        component["ineligible_parent_reference_count"] == 22,
        "pilot component ineligible-parent census drift",
    )

    gate = bundle["gate"]
    expected_statuses = {
        "slice": "pass_pilot_slice_fixed_nonauthority",
        "sweeps": "pass_corpus_exhaustive_targeted_sweeps_nonauthority",
        "predecessor": "pass_adjudication_with_predecessor_reseal_required",
        "role": "pass_role_assignment_law_pilot_nonauthority",
        "repeat": "pass_outside_domain_repeat_law_pilot_nonauthority",
        "component": "pass_component_parent_law_pilot_nonauthority",
        "gate": "pass_law_shapes_only_nonauthority",
    }
    _require(
        all(
            bundle[key]["status"] == status
            for key, status in expected_statuses.items()
        ),
        "artifact status drift",
    )
    _require(
        all(bundle[key]["tier"] == 1 for key in OUTPUT_FILENAMES),
        "artifact tier drift",
    )
    _require(
        sweep["source_corpus_identity"]
        == slice_artifact["source_corpus_identity"]
        == predecessor["source_corpus_identity"],
        "source corpus identity linkage drift",
    )
    _require(
        all(
            bundle[key]["source_slice_artifact_id"]
            == slice_artifact["artifact_id"]
            for key in ("role", "repeat", "component")
        ),
        "pilot slice artifact linkage drift",
    )
    _require(
        all(
            bundle[key]["corpus_sweep_artifact_id"] == sweep["artifact_id"]
            for key in ("role", "repeat", "component")
        ),
        "corpus sweep artifact linkage drift",
    )
    _require(
        gate["source_slice_artifact_id"] == slice_artifact["artifact_id"],
        "gate slice linkage drift",
    )
    _require(
        gate["design_prefix_identity"]
        == slice_artifact["design_prefix_identity"],
        "gate design-prefix linkage drift",
    )
    _require(gate["pilot_census"] == census, "gate pilot census drift")
    _require(
        gate["certification_status"] == "PILOT_NONAUTHORITY_CERTIFIES_NOTHING",
        "pilot claims certification",
    )
    _require(gate["pilot_law_shape_status"] == "pass", "pilot law status")
    _require(
        gate["overall_repeat_catalog_coverage_status"]
        == "fail_closed_unresolved_rows_remain",
        "pilot falsely claims universal catalog coverage",
    )
    _require(gate["role_law_status"] == "pass", "gate role status")
    _require(
        gate["outside_domain_repeat_law_status"] == "pass",
        "gate repeat status",
    )
    _require(
        gate["component_parent_law_status"] == "pass",
        "gate component status",
    )
    _require(
        gate["predecessor_input_status"] == "reseal_required_before_tier_2",
        "gate predecessor status",
    )
    _require(
        gate["tier_2_protocol_status"]
        == "not_started_requires_ratification_and_predecessor_reseals",
        "gate tier-2 status",
    )
    _require(
        gate["status"] == "pass_law_shapes_only_nonauthority",
        "gate status drift",
    )
    identity_rows = gate["artifact_identity_rows"]
    _require(len(identity_rows) == 6, "gate identity count drift")
    _require(
        gate["artifact_identity_count"] == len(identity_rows),
        "gate identity count mismatch",
    )
    _require(
        gate["artifact_identity_domain_sha256"] == _domain_sha(identity_rows),
        "gate identity digest drift",
    )
    expected_identity_roles = [
        "slice",
        "sweeps",
        "predecessor",
        "role",
        "repeat",
        "component",
    ]
    _require(
        [row["artifact_role"] for row in identity_rows]
        == expected_identity_roles,
        "gate identity role partition drift",
    )
    for identity in identity_rows:
        _require_exact_keys(
            identity,
            ARTIFACT_IDENTITY_ROW_KEYS,
            "gate artifact identity row",
        )
        key = identity["artifact_role"]
        raw = canonical_bytes(bundle[key])
        _require(identity["byte_size"] == len(raw), "gate artifact size drift")
        _require(identity["raw_sha256"] == _sha256(raw), "gate raw hash drift")
        _require(
            identity["artifact_id"] == bundle[key]["artifact_id"],
            "gate artifact ID drift",
        )
        _require(
            identity["path"]
            == "docs/analysis/amendment_12_rq_catalog_pilot/"
            + OUTPUT_FILENAMES[key],
            "gate artifact path drift",
        )
        _require(
            identity["schema_version"] == ARTIFACT_SPECS[key][0],
            "gate artifact schema drift",
        )


def _reseal_artifact(artifact: Mapping[str, Any]) -> dict[str, Any]:
    schema = artifact["schema_version"]
    authority_kind = artifact["authority_kind"]
    id_prefix = artifact["artifact_id"].rsplit(":", 1)[0] + ":"
    body = {
        key: copy.deepcopy(value)
        for key, value in artifact.items()
        if key
        not in {
            "schema_version",
            "artifact_id",
            "authority_kind",
            "integrity",
        }
    }
    return _artifact(schema, id_prefix, authority_kind, body)


def _repin_mutated_bundle(
    value: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Repin all nonsemantic identities after an adversarial mutation."""
    bundle = copy.deepcopy(dict(value))

    for artifact_key, class_row_key in (
        ("sweeps", "role_exact_label_class_rows"),
        ("role", "role_label_class_rows"),
    ):
        for row in bundle[artifact_key][class_row_key]:
            row["exact_label_sha256"] = _sha256(
                row["exact_label"].encode("utf-8")
            )
            row["role_label_class_id"] = _row_id(
                "a12-role-exact-label-class:",
                [row["role"], row["exact_label_sha256"]],
            )
            row["member_count"] = len(row["member_occurrence_ids"])
            row["member_keyset_sha256"] = _keyset_sha(
                row["member_occurrence_ids"]
            )
    for row in bundle["role"]["role_assignment_rows"]:
        row["role_assignment_id"] = _row_id(
            "a12-pilot-role-assignment:",
            [
                row["source_document_id"],
                row["role_anchor_occurrence_id"],
                row["assigned_role"],
                row["role_label_class_id"],
                row["proof_form"],
            ],
        )

    for artifact_key, row_key in (
        ("sweeps", "outside_domain_repeat_shape_rows"),
        ("repeat", "outside_domain_repeat_disposition_rows"),
    ):
        for row in bundle[artifact_key][row_key]:
            row["outside_domain_repeat_disposition_id"] = _row_id(
                "a12-outside-rq-repeat-disposition:",
                [
                    row["source_document_id"],
                    row["source_instruction_occurrence_id"],
                    row["source_local_evidence_id"],
                    row["relation"],
                    row["unresolved_target_reference"],
                ],
            )

    component_row_groups = (
        bundle["sweeps"]["component_parent_shape_rows"],
        bundle["component"]["zero_parent_disposition_rows"],
        bundle["component"]["unique_parent_assignment_rows"],
        bundle["component"]["multi_parent_ambiguity_rows"],
    )
    for rows in component_row_groups:
        for row in rows:
            candidates = row["parent_candidate_rows"]
            row["parent_candidate_count"] = len(candidates)
            row["serialized_parent_cardinality"] = len(candidates)
            row["eligible_parent_cardinality"] = sum(
                candidate["eligible_parent"] for candidate in candidates
            )
            row["parent_candidate_domain_sha256"] = _domain_sha(candidates)
            row["component_parent_resolution_id"] = _row_id(
                "a12-component-parent-resolution:",
                [
                    row["source_document_id"],
                    row["component_anchor_occurrence_id"],
                    row["component_kind"],
                    row["disposition"],
                    candidates,
                ],
            )

    for row in bundle["sweeps"]["parent_source_witness_rows"]:
        row["parent_source_witness_id"] = _row_id(
            "a12-parent-source-witness:",
            [
                row["source_document_id"],
                row["source_classification_id"],
                row["parent_occurrence_id"],
                row["parent_occurrence_kind"],
            ],
        )
    for row in bundle["predecessor"]["doc036_aggregate_component_slot_rows"]:
        row["predecessor_adjudication_id"] = _row_id(
            "a12-predecessor-doc036-aggregate-adjudication:",
            [
                row["source_document_id"],
                row["source_classification_id"],
                row["source_occurrence_id"],
                row["source_classification"],
                row["disposition"],
            ],
        )
    for row in bundle["predecessor"]["defective_populated_local_proof_rows"]:
        row["predecessor_adjudication_id"] = _row_id(
            "a12-predecessor-local-proof-adjudication:",
            [
                row["source_document_id"],
                row["source_local_evidence_id"],
                row["defect_flags"],
                row["disposition"],
            ],
        )

    slice_artifact = bundle["slice"]
    pilot_rows = slice_artifact["pilot_document_rows"]
    slice_artifact["pilot_document_count"] = len(pilot_rows)
    slice_artifact["pilot_document_positions"] = [
        row["document_source_position"] for row in pilot_rows
    ]
    slice_artifact["pilot_document_position_domain_sha256"] = _domain_sha(
        slice_artifact["pilot_document_positions"]
    )
    slice_artifact["pilot_annotation_raw_byte_count"] = sum(
        row["annotation_byte_size"] for row in pilot_rows
    )

    sweep = bundle["sweeps"]
    role_classes = sweep["role_exact_label_class_rows"]
    sweep["role_exact_label_class_count"] = len(role_classes)
    sweep["role_exact_label_class_domain_sha256"] = _domain_sha(role_classes)
    sweep["role_anchor_count"] = sum(
        row["member_count"] for row in role_classes
    )
    sweep["role_noncanonical_assignment_reach_count"] = max(
        0, sweep["role_anchor_count"] - len(ROLE_CANONICALS)
    )
    sweep["role_unreached_anchor_count"] = len(
        sweep["role_unreached_anchor_rows"]
    )
    sweep_repeats = sweep["outside_domain_repeat_shape_rows"]
    sweep["outside_domain_repeat_shape_count"] = len(sweep_repeats)
    sweep["outside_domain_repeat_shape_domain_sha256"] = _domain_sha(
        sweep_repeats
    )
    component_shapes = sweep["component_parent_shape_rows"]
    sweep["component_parent_shape_count"] = len(component_shapes)
    sweep["component_parent_shape_keyset_sha256"] = _keyset_sha(
        [row["component_parent_resolution_id"] for row in component_shapes]
    )
    sweep["component_parent_shape_domain_sha256"] = _domain_sha(
        component_shapes
    )
    raw_cardinality = Counter(
        (
            "zero"
            if row["serialized_parent_cardinality"] == 0
            else (
                "one"
                if row["serialized_parent_cardinality"] == 1
                else "multiple"
            )
        )
        for row in component_shapes
    )
    sweep["serialized_parent_cardinality_counts"] = {
        key: raw_cardinality[key] for key in ("zero", "one", "multiple")
    }
    sweep["component_parent_disposition_counts"] = dict(
        sorted(Counter(row["disposition"] for row in component_shapes).items())
    )
    sweep["raw_cross_category_multi_parent_count"] = sum(
        row["raw_parent_category_ambiguity"] for row in component_shapes
    )
    sweep["eligible_cross_category_multi_parent_count"] = sum(
        row["eligible_parent_category_ambiguity"] for row in component_shapes
    )
    sweep["eligible_ineligible_mixed_multi_parent_count"] = sum(
        row["eligible_ineligible_mixed_ambiguity"] for row in component_shapes
    )
    sweep["ineligible_parent_reference_count"] = sum(
        candidate["eligible_parent"] is False
        for row in component_shapes
        for candidate in row["parent_candidate_rows"]
    )
    source_witnesses = sweep["parent_source_witness_rows"]
    sweep["parent_source_witness_count"] = len(source_witnesses)
    sweep["parent_source_witness_keyset_sha256"] = _keyset_sha(
        [row["parent_source_witness_id"] for row in source_witnesses]
    )
    sweep["parent_source_witness_domain_sha256"] = _domain_sha(
        source_witnesses
    )

    predecessor = bundle["predecessor"]
    doc036_rows = predecessor["doc036_aggregate_component_slot_rows"]
    proof_rows = predecessor["defective_populated_local_proof_rows"]
    predecessor["doc036_aggregate_component_slot_count"] = len(doc036_rows)
    predecessor["doc036_aggregate_component_slot_domain_sha256"] = _domain_sha(
        doc036_rows
    )
    predecessor["defective_populated_local_proof_count"] = len(proof_rows)
    predecessor["defective_populated_local_proof_keyset_sha256"] = _keyset_sha(
        [row["source_local_evidence_id"] for row in proof_rows]
    )
    predecessor["defective_populated_local_proof_domain_sha256"] = _domain_sha(
        proof_rows
    )
    predecessor["defect_category_counts"] = {
        key: sum(row["defect_flags"][key] for row in proof_rows)
        for key in DEFECT_FLAG_KEYS
    }
    all_predecessor_rows = [*doc036_rows, *proof_rows]
    predecessor["seal_defect_disposition_count"] = sum(
        row["disposition"] == "predecessor_seal_defect"
        for row in all_predecessor_rows
    )
    predecessor["law_gap_disposition_count"] = sum(
        row["law_gap_admitted"] or row["disposition"] == "law_gap"
        for row in all_predecessor_rows
    )

    role = bundle["role"]
    pilot_classes = role["role_label_class_rows"]
    assignments = role["role_assignment_rows"]
    role["role_label_class_count"] = len(pilot_classes)
    role["role_label_class_domain_sha256"] = _domain_sha(pilot_classes)
    role["role_assignment_count"] = len(assignments)
    role["role_assignment_keyset_sha256"] = _keyset_sha(
        [row["role_assignment_id"] for row in assignments]
    )
    role["role_assignment_domain_sha256"] = _domain_sha(assignments)
    role["unassigned_role_anchor_count"] = len(
        role["unassigned_role_anchor_rows"]
    )

    repeat = bundle["repeat"]
    repeat_rows = repeat["outside_domain_repeat_disposition_rows"]
    repeat["outside_domain_repeat_disposition_count"] = len(repeat_rows)
    repeat["outside_domain_repeat_disposition_keyset_sha256"] = _keyset_sha(
        [row["outside_domain_repeat_disposition_id"] for row in repeat_rows]
    )
    repeat["outside_domain_repeat_disposition_domain_sha256"] = _domain_sha(
        repeat_rows
    )
    repeat["relation_counts"] = dict(
        sorted(Counter(row["relation"] for row in repeat_rows).items())
    )
    repeat["document_counts"] = {
        str(key): count
        for key, count in sorted(
            Counter(
                row["document_source_position"] for row in repeat_rows
            ).items()
        )
    }

    component = bundle["component"]
    component_groups = (
        (
            "zero_parent_disposition_rows",
            "zero_parent_disposition_count",
            "zero_parent_disposition_domain_sha256",
        ),
        (
            "unique_parent_assignment_rows",
            "unique_parent_assignment_count",
            "unique_parent_assignment_domain_sha256",
        ),
        (
            "multi_parent_ambiguity_rows",
            "multi_parent_ambiguity_count",
            "multi_parent_ambiguity_domain_sha256",
        ),
    )
    complete_rows: list[dict[str, Any]] = []
    for row_key, count_key, domain_key in component_groups:
        rows = component[row_key]
        component[count_key] = len(rows)
        component[domain_key] = _domain_sha(rows)
        complete_rows.extend(rows)
    component["complete_component_resolution_count"] = len(complete_rows)
    component["complete_component_resolution_keyset_sha256"] = _keyset_sha(
        [row["component_parent_resolution_id"] for row in complete_rows]
    )
    component["complete_component_resolution_domain_sha256"] = _domain_sha(
        complete_rows
    )

    bundle["slice"] = _reseal_artifact(slice_artifact)
    bundle["sweeps"] = _reseal_artifact(sweep)
    bundle["predecessor"] = _reseal_artifact(predecessor)
    for key in ("role", "repeat", "component"):
        bundle[key]["source_slice_artifact_id"] = bundle["slice"][
            "artifact_id"
        ]
        bundle[key]["corpus_sweep_artifact_id"] = bundle["sweeps"][
            "artifact_id"
        ]
        bundle[key] = _reseal_artifact(bundle[key])

    gate = bundle["gate"]
    gate["source_slice_artifact_id"] = bundle["slice"]["artifact_id"]
    gate["design_prefix_identity"] = bundle["slice"]["design_prefix_identity"]
    gate["pilot_census"] = bundle["slice"]["pilot_census"]
    gate["artifact_identity_rows"] = [
        {
            "artifact_role": key,
            "path": (
                "docs/analysis/amendment_12_rq_catalog_pilot/"
                + OUTPUT_FILENAMES[key]
            ),
            "schema_version": bundle[key]["schema_version"],
            "artifact_id": bundle[key]["artifact_id"],
            "byte_size": len(canonical_bytes(bundle[key])),
            "raw_sha256": _sha256(canonical_bytes(bundle[key])),
        }
        for key in (
            "slice",
            "sweeps",
            "predecessor",
            "role",
            "repeat",
            "component",
        )
    ]
    gate["artifact_identity_count"] = len(gate["artifact_identity_rows"])
    gate["artifact_identity_domain_sha256"] = _domain_sha(
        gate["artifact_identity_rows"]
    )
    bundle["gate"] = _reseal_artifact(gate)
    return bundle


def run_mutation_tests(
    original: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    """Require coherently repinned law-level mutations to fail semantically."""
    mutations: list[tuple[str, Any, str]] = []

    def add(name: str, mutate: Any, expected_error: str) -> None:
        mutations.append((name, mutate, expected_error))

    def forge_parent_and_source_witness(value: dict[str, Any]) -> None:
        pilot_row = value["component"]["unique_parent_assignment_rows"][0]
        position = pilot_row["document_source_position"]
        old_id = pilot_row["parent_candidate_rows"][0]["parent_occurrence_id"]
        new_id = "psid-questionnaire-occurrence:coherent-source-forgery"
        row_groups = [
            value["sweeps"]["component_parent_shape_rows"],
            value["component"]["zero_parent_disposition_rows"],
            value["component"]["unique_parent_assignment_rows"],
            value["component"]["multi_parent_ambiguity_rows"],
        ]
        for rows in row_groups:
            for row in rows:
                if row["document_source_position"] != position:
                    continue
                for candidate in row["parent_candidate_rows"]:
                    if candidate["parent_occurrence_id"] == old_id:
                        candidate["parent_occurrence_id"] = new_id
        witness = next(
            row
            for row in value["sweeps"]["parent_source_witness_rows"]
            if row["document_source_position"] == position
            and row["parent_occurrence_id"] == old_id
        )
        witness["parent_occurrence_id"] = new_id

    def forge_nonpilot_component_anchor(value: dict[str, Any]) -> None:
        row = next(
            item
            for item in value["sweeps"]["component_parent_shape_rows"]
            if item["document_source_position"] not in PILOT_POSITIONS
        )
        row["component_anchor_occurrence_id"] = (
            "psid-questionnaire-occurrence:coherent-component-forgery"
        )

    def forge_nonpilot_role_member(value: dict[str, Any]) -> None:
        pilot_members = {
            member
            for row in value["role"]["role_label_class_rows"]
            for member in row["member_occurrence_ids"]
        }
        row = next(
            item
            for item in value["sweeps"]["role_exact_label_class_rows"]
            if any(
                member not in pilot_members
                for member in item["member_occurrence_ids"]
            )
        )
        index = next(
            index
            for index, member in enumerate(row["member_occurrence_ids"])
            if member not in pilot_members
        )
        row["member_occurrence_ids"][
            index
        ] = "psid-questionnaire-occurrence:coherent-role-forgery"

    def forge_outside_target_bytes(value: dict[str, Any]) -> None:
        for artifact_key, row_key in (
            ("sweeps", "outside_domain_repeat_shape_rows"),
            ("repeat", "outside_domain_repeat_disposition_rows"),
        ):
            unresolved = value[artifact_key][row_key][0][
                "unresolved_target_reference"
            ]
            forged = "X" * len(unresolved["matched_text"].encode("utf-8"))
            unresolved["matched_text"] = forged
            unresolved["matched_utf8_sha256"] = _sha256(forged.encode("utf-8"))

    add(
        "pilot_slice_reordered",
        lambda value: value["slice"]["pilot_document_rows"].reverse(),
        "pilot positions drift",
    )
    add(
        "pilot_claims_q5",
        lambda value: value["slice"]["nonauthority_statement"].__setitem__(
            "q5_emitted", True
        ),
        "nonauthority drift",
    )
    add(
        "role_assignment_omitted",
        lambda value: value["role"]["role_assignment_rows"].pop(),
        "pilot role assignment count drift",
    )
    add(
        "role_assignment_role_flipped",
        lambda value: value["role"]["role_assignment_rows"][0].__setitem__(
            "assigned_role", ROLE_SPOUSE
        ),
        "assigned role/class mismatch",
    )
    add(
        "role_assignment_class_invented",
        lambda value: value["role"]["role_assignment_rows"][0].__setitem__(
            "role_label_class_id", "a12-role-exact-label-class:invented"
        ),
        "dangling role class",
    )
    add(
        "role_assignment_alias_admitted",
        lambda value: value["role"]["role_assignment_rows"][0].__setitem__(
            "alias_admitted_by_assignment", True
        ),
        "alias admitted",
    )
    add(
        "role_assignment_equivalence_claimed",
        lambda value: value["role"]["role_assignment_rows"][0].__setitem__(
            "occurrence_equivalence_claimed", True
        ),
        "occurrence equivalence claimed",
    )
    add(
        "role_sweep_class_omitted",
        lambda value: value["sweeps"]["role_exact_label_class_rows"].pop(),
        "role class count drift",
    )
    add(
        "role_sweep_alias_class_claimed",
        lambda value: value["sweeps"]["role_exact_label_class_rows"][
            0
        ].__setitem__("alias_class_claimed", True),
        "alias class claimed",
    )
    add(
        "role_sweep_source_member_forged",
        forge_nonpilot_role_member,
        "role sweep pinned source projection drift",
    )
    add(
        "outside_repeat_target_emptied",
        lambda value: value["repeat"][
            "outside_domain_repeat_disposition_rows"
        ][0].__setitem__("unresolved_target_reference", {}),
        "unresolved target: keyset drift",
    )
    add(
        "outside_repeat_terminal_changed",
        lambda value: value["repeat"][
            "outside_domain_repeat_disposition_rows"
        ][0].__setitem__("terminal_disposition", "admit_alias"),
        "terminal disposition",
    )
    add(
        "outside_repeat_universal_arm_false",
        lambda value: value["repeat"][
            "outside_domain_repeat_disposition_rows"
        ][0].__setitem__("universal_repeat_coverage_arm_satisfied", False),
        "universal arm",
    )
    add(
        "outside_repeat_alias_admitted",
        lambda value: value["repeat"][
            "outside_domain_repeat_disposition_rows"
        ][0].__setitem__("alias_admitted", True),
        "alias admitted",
    )
    add(
        "outside_repeat_evidence_not_singleton",
        lambda value: value["repeat"][
            "outside_domain_repeat_disposition_rows"
        ][0]["evidence_occurrence_ids"].append(
            "psid-questionnaire-occurrence:invented"
        ),
        "evidence is not singleton self",
    )
    add(
        "outside_repeat_source_target_forged",
        forge_outside_target_bytes,
        "repeat sweep pinned source projection drift",
    )
    add(
        "zero_parent_emits_rq",
        lambda value: value["component"]["zero_parent_disposition_rows"][
            0
        ].__setitem__("r_q_relationship_emitted", True),
        "pilot emitted R_Q",
    )
    add(
        "unique_parent_forced",
        lambda value: value["component"]["unique_parent_assignment_rows"][
            0
        ].__setitem__("forced_parent_selection", True),
        "forced parent",
    )
    add(
        "unique_parent_derived_slot_invented",
        lambda value: value["component"]["unique_parent_assignment_rows"][0][
            "parent_candidate_rows"
        ][0].__setitem__("derived_slot_kind", "invented_slot"),
        "derived slot equation",
    )
    add(
        "unique_parent_source_invented",
        lambda value: value["component"]["unique_parent_assignment_rows"][0][
            "parent_candidate_rows"
        ][0].__setitem__(
            "parent_occurrence_id", "psid-questionnaire-occurrence:invented"
        ),
        "no source witness",
    )
    add(
        "parent_and_source_witness_forged",
        forge_parent_and_source_witness,
        "parent witness pinned source projection drift",
    )
    add(
        "ambiguity_forced_parent",
        lambda value: value["component"]["multi_parent_ambiguity_rows"][
            0
        ].__setitem__("forced_parent_selection", True),
        "forced parent",
    )
    add(
        "ambiguity_emits_rq",
        lambda value: value["component"]["multi_parent_ambiguity_rows"][
            0
        ].__setitem__("r_q_relationship_emitted", True),
        "pilot emitted R_Q",
    )
    add(
        "component_sweep_row_omitted",
        lambda value: value["sweeps"]["component_parent_shape_rows"].pop(),
        "component sweep count drift",
    )
    add(
        "component_sweep_source_anchor_forged",
        forge_nonpilot_component_anchor,
        "component sweep pinned source projection drift",
    )
    add(
        "component_row_extra_key",
        lambda value: value["component"]["zero_parent_disposition_rows"][
            0
        ].__setitem__("invented_key", True),
        "component pilot row: keyset drift",
    )
    add(
        "doc036_law_gap_admitted",
        lambda value: value["predecessor"][
            "doc036_aggregate_component_slot_rows"
        ][0].__setitem__("law_gap_admitted", True),
        "law gap admitted",
    )
    add(
        "doc036_component_slot_admitted",
        lambda value: value["predecessor"][
            "doc036_aggregate_component_slot_rows"
        ][0].__setitem__("component_slot_admitted", True),
        "component slot admitted",
    )
    add(
        "proof_defect_lawified",
        lambda value: value["predecessor"][
            "defective_populated_local_proof_rows"
        ][0].__setitem__("disposition", "law_gap"),
        "disposition",
    )
    add(
        "proof_defect_action_removed",
        lambda value: value["predecessor"][
            "defective_populated_local_proof_rows"
        ][0].__setitem__("required_action", "do_nothing"),
        "required action",
    )
    add(
        "proof_defect_row_omitted",
        lambda value: value["predecessor"][
            "defective_populated_local_proof_rows"
        ].pop(),
        "proof defect count drift",
    )
    add(
        "gate_claims_certification",
        lambda value: value["gate"].__setitem__(
            "certification_status", "certified"
        ),
        "pilot claims certification",
    )
    add(
        "gate_claims_repeat_coverage",
        lambda value: value["gate"].__setitem__(
            "overall_repeat_catalog_coverage_status", "pass"
        ),
        "pilot falsely claims universal catalog coverage",
    )

    rejected: list[str] = []
    for name, mutation, expected_error in mutations:
        candidate = copy.deepcopy(dict(original))
        mutation(candidate)
        candidate = _repin_mutated_bundle(candidate)
        try:
            validate_bundle(candidate)
        except BuildError as error:
            _require(
                expected_error in str(error),
                f"mutation {name} hit wrong gate: {error}",
            )
            rejected.append(name)
        else:
            raise BuildError(f"mutation survived validation: {name}")
    return rejected


def _artifact_paths(output_root: Path) -> dict[str, Path]:
    return {
        key: output_root / filename
        for key, filename in OUTPUT_FILENAMES.items()
    }


def load_committed_bundle(
    output_root: Path = OUTPUT_ROOT,
) -> dict[str, dict[str, Any]]:
    bundle: dict[str, dict[str, Any]] = {}
    for key, path in _artifact_paths(output_root).items():
        raw = path.read_bytes()
        value = strict_json_loads(raw, str(path))
        _require(isinstance(value, dict), f"{path}: not object")
        _require(raw == canonical_bytes(value), f"{path}: noncanonical bytes")
        bundle[key] = value
    return bundle


@dataclass(frozen=True)
class _DestinationBackup:
    label: str
    destination: Path
    path: Path | None


def _fsync_directory(path: Path) -> None:
    descriptor = -1
    try:
        descriptor = os.open(path, os.O_RDONLY)
        os.fsync(descriptor)
    except OSError as error:
        raise BuildError(
            f"cannot fsync output directory {path}: {error}"
        ) from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _preflight_output_paths(paths: Mapping[str, Path]) -> None:
    resolved: dict[Path, str] = {}
    inodes: dict[tuple[int, int], str] = {}
    for label, path in paths.items():
        target = path.resolve(strict=False)
        _require(
            target not in resolved,
            f"output path collision: {label} aliases {resolved.get(target)}",
        )
        resolved[target] = label
        try:
            status = os.lstat(path)
        except FileNotFoundError:
            continue
        except OSError as error:
            raise BuildError(
                f"cannot inspect output {path}: {error}"
            ) from error
        _require(not path.is_symlink(), f"output path is a symlink: {path}")
        identity = (status.st_dev, status.st_ino)
        _require(
            identity not in inodes,
            f"output inode collision: {label} aliases {inodes.get(identity)}",
        )
        inodes[identity] = label


def _stage_output(label: str, destination: Path, raw: bytes) -> Path:
    descriptor = -1
    staged: Path | None = None
    valid = False
    try:
        descriptor, raw_path = tempfile.mkstemp(
            dir=destination.parent,
            prefix=f".{destination.name}.a12-stage-",
        )
        staged = Path(raw_path)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        _require(
            staged.read_bytes() == raw, f"staged output mismatch: {label}"
        )
        valid = True
        return staged
    except BuildError:
        raise
    except OSError as error:
        raise BuildError(f"cannot stage output {label}: {error}") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if staged is not None and not valid:
            staged.unlink(missing_ok=True)


def _backup_destination(label: str, destination: Path) -> _DestinationBackup:
    if not destination.exists():
        return _DestinationBackup(label, destination, None)
    descriptor = -1
    backup: Path | None = None
    valid = False
    try:
        descriptor, raw_path = tempfile.mkstemp(
            dir=destination.parent,
            prefix=f".{destination.name}.a12-backup-",
        )
        os.close(descriptor)
        descriptor = -1
        backup = Path(raw_path)
        backup.unlink()
        os.link(destination, backup, follow_symlinks=False)
        valid = True
        return _DestinationBackup(label, destination, backup)
    except OSError as error:
        raise BuildError(f"cannot back up output {label}: {error}") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if backup is not None and not valid:
            backup.unlink(missing_ok=True)


def _restore_destination(backup: _DestinationBackup) -> None:
    if backup.path is None:
        backup.destination.unlink(missing_ok=True)
        return
    descriptor, raw_path = tempfile.mkstemp(
        dir=backup.destination.parent,
        prefix=f".{backup.destination.name}.a12-restore-",
    )
    os.close(descriptor)
    restore = Path(raw_path)
    try:
        restore.unlink()
        os.link(backup.path, restore, follow_symlinks=False)
        os.replace(restore, backup.destination)
    finally:
        restore.unlink(missing_ok=True)


def _write_bundle(
    bundle: Mapping[str, Mapping[str, Any]],
    output_root: Path,
) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    paths = _artifact_paths(output_root)
    _preflight_output_paths(paths)
    staged: list[tuple[str, Path, Path, bytes]] = []
    backups: list[_DestinationBackup] = []
    commit_succeeded = False
    rollback_succeeded = False
    try:
        for key, destination in paths.items():
            raw = canonical_bytes(bundle[key])
            temporary = _stage_output(key, destination, raw)
            staged.append((key, destination, temporary, raw))
        for key, destination, _temporary, _raw in staged:
            backups.append(_backup_destination(key, destination))
        for _key, destination, temporary, _raw in staged:
            os.replace(temporary, destination)
        for key, destination, _temporary, expected in staged:
            _require(
                destination.read_bytes() == expected,
                f"published output mismatch: {key}",
            )
        _fsync_directory(output_root)
        commit_succeeded = True
    except Exception as commit_error:
        rollback_errors: list[str] = []
        for backup in backups:
            try:
                _restore_destination(backup)
            except Exception as rollback_error:
                rollback_errors.append(f"{backup.label}: {rollback_error}")
        try:
            _fsync_directory(output_root)
        except BuildError as rollback_error:
            rollback_errors.append(str(rollback_error))
        rollback_succeeded = not rollback_errors
        if rollback_errors:
            raise BuildError(
                "output transaction failed and rollback is incomplete; "
                + "; ".join(rollback_errors)
            ) from commit_error
        raise BuildError(
            "output transaction failed; all prior destinations restored"
        ) from commit_error
    finally:
        for _key, _destination, temporary, _raw in staged:
            temporary.unlink(missing_ok=True)
        if commit_succeeded or rollback_succeeded:
            for backup in backups:
                if backup.path is not None:
                    backup.path.unlink(missing_ok=True)


def _check_bundle(
    expected: Mapping[str, Mapping[str, Any]],
    output_root: Path,
) -> None:
    actual = load_committed_bundle(output_root)
    validate_bundle(actual)
    for key in OUTPUT_FILENAMES:
        expected_raw = canonical_bytes(expected[key])
        actual_raw = canonical_bytes(actual[key])
        _require(expected_raw == actual_raw, f"artifact drift: {key}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root",
        type=Path,
        help=(
            "optional clean worktree at the pinned source commit; all read "
            "bytes are still checked against the era-seal identities"
        ),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=OUTPUT_ROOT,
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--mutation-tests", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    design_prefix = _validate_design_prefix()
    if args.mutation_tests and not args.check:
        bundle = load_committed_bundle(args.output_root)
        validate_bundle(bundle)
    else:
        reader = SourceReader(args.source_root)
        documents, source_identity = _load_documents(reader)
        bundle = _build_bundle(documents, source_identity, design_prefix)
        validate_bundle(bundle)
        if args.check:
            _check_bundle(bundle, args.output_root)
        else:
            _write_bundle(bundle, args.output_root)
    mutation_names: list[str] = []
    if args.mutation_tests:
        mutation_names = run_mutation_tests(bundle)
    result = {
        "artifact_count": len(bundle),
        "check": bool(args.check),
        "mutation_test_count": len(mutation_names),
        "mutation_tests": mutation_names,
        "source_commit": SOURCE_COMMIT,
        "status": "pass",
    }
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
