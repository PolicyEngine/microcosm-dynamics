#!/usr/bin/env python3
"""Build and validate the stage-2 nonauthority annotation for document 60.

The reviewer-authored source specification is deliberately candidate-free.  The
builder authenticates and slices the complete PDF-derived page domain first and
only then opens the stage-1 candidate artifact to construct the two provenance
relations required by ``docs/analysis/rq_stage2_protocol.md``.

The task-level artifact-scale law supersedes the protocol's legacy serialized
root-to-leaf path products.  This shard stores only direct parent occurrence
edges and reconstructs ancestry transiently while validating the flow DAG.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_global_q5_intermediate_evidence as source_tools  # noqa: E402
import build_rq_stage1_candidates as stage1_candidates  # noqa: E402

from populace_dynamics.data import (  # noqa: E402
    psid_questionnaire_inventory as questionnaire_inventory,
)

DOCUMENT_SOURCE_POSITION = 60
SCHEMA_VERSION = "rq_stage2_document_annotation_local_edges_nonauthority.v1"
REVIEW_SCHEMA_VERSION = "rq_stage2_document_source_review_local_edges.v1"
STATUS = "sealed_complete_nonauthority_document_annotation"
AUTHORITY_KIND = "document_local_source_annotation_nonauthority"
CANONICALIZATION = source_tools.CANONICALIZATION
FLOW_ROOT = "questionnaire-flow:root"
FORBIDDEN_PARENT_PATH_MARKER = "#parent" "-path-"
MAX_COMMITTED_FILE_BYTES = 50 * 1024 * 1024

ANNOTATION_ROOT = ROOT / "docs" / "analysis" / "rq_stage2_annotations"
REVIEW_PATH = (
    ANNOTATION_ROOT / "document_060_fam1999_QxQs_source_review_v1.json"
)
OUTPUT_PATH = ANNOTATION_ROOT / "document_060_fam1999_QxQs_annotation_v1.json"
CAPTURE_ROOT = (
    Path("~/PolicyEngine/psid-data").expanduser()
    / "documentation"
    / "capture1"
)

OCCURRENCE_KINDS = stage1_candidates.OCCURRENCE_KINDS
KIND_ORDER = {kind: position for position, kind in enumerate(OCCURRENCE_KINDS)}
ANCHOR_KINDS = {
    "role_anchor",
    "job_anchor",
    "remuneration_component_anchor",
    "role_total_anchor",
    "farm_aggregate_anchor",
    "business_aggregate_anchor",
    "context_anchor",
}
ANCHOR_CLASSIFICATION = {
    "job_anchor": ("job_slot", "source_job"),
    "remuneration_component_anchor": (
        "component_slot",
        "source_remuneration_component",
    ),
    "role_total_anchor": ("aggregate", "role_total"),
    "farm_aggregate_anchor": ("aggregate", "farm_aggregate"),
    "business_aggregate_anchor": ("aggregate", "business_aggregate"),
    "context_anchor": ("component_slot", "source_context"),
}
ROLE_CLASSIFICATIONS = {
    "head_or_reference_person",
    "spouse_or_partner",
}
ALIAS_RELATIONS = {
    "explicit_repeat_instruction",
    "explicit_cross_reference",
    "same_printed_identifier_and_exact_label",
}
CANDIDATE_ROW_KINDS = (
    "whole_document_locator",
    "page",
    "occurrence",
    "flow_path",
    "anchor_classification",
)
STAGE2_ROW_KINDS = (
    "whole_document_locator",
    "page",
    "occurrence",
    "flow_branch",
    "local_anchor_classification",
    "local_repeat_alias_evidence",
)

LOCATOR_KEYS = (
    "locator_id",
    "source_document_id",
    "interview_wave",
    "filename",
    "location_type",
    "byte_start",
    "byte_end",
    "size_bytes",
    "full_file_sha256",
    "range_sha256",
    "pdf_page_domain",
)
PAGE_KEYS = (
    "questionnaire_page_id",
    "source_document_id",
    "source_locator_id",
    "interview_wave",
    "page_number",
    "page_text_utf8_sha256",
    "questionnaire_occurrence_ids",
    "annotation_status",
)
OCCURRENCE_KEYS = (
    "questionnaire_occurrence_id",
    "source_document_id",
    "source_locator_id",
    "source_locator_sha256",
    "interview_wave",
    "page_number",
    "utf8_byte_start",
    "utf8_byte_end",
    "occurrence_index_on_page",
    "semantic_ordinal_at_span",
    "occurrence_kind",
    "matched_text",
    "matched_utf8_sha256",
    "parent_flow_occurrence_ids",
)
FLOW_BRANCH_KEYS = (
    "flow_branch_id",
    "parent_flow_branch_ids",
    "parent_source_occurrence_ids",
    "source_occurrence_id",
    "interview_wave",
    "source_locator_id",
    "page_number",
    "occurrence_index_on_page",
    "branch_label",
    "branch_label_sha256",
)
CANDIDATE_DISPOSITION_KEYS = (
    "candidate_row_kind",
    "candidate_id",
    "disposition",
    "stage2_row_ids",
    "adjudication_status",
)
OUTPUT_ADJUDICATION_KEYS = (
    "stage2_row_kind",
    "stage2_row_id",
    "source_candidate_ids",
    "adjudication_action",
    "whole_page_review_complete",
    "source_span_verified",
    "adjudication_status",
)
LOCAL_ANCHOR_KEYS = (
    "local_anchor_classification_id",
    "source_occurrence_id",
    "occurrence_kind",
    "node_domain",
    "classification",
    "printed_identifier",
    "exact_label",
    "exact_label_sha256",
    "parent_source_occurrence_ids",
    "classification_status",
)
LOCAL_REPEAT_KEYS = (
    "local_repeat_alias_evidence_id",
    "source_occurrence_id",
    "relation",
    "alias_anchor_source_occurrence_ids",
    "canonical_anchor_source_occurrence_ids",
    "evidence_occurrence_ids",
    "target_scope",
    "resolution_status",
)
NOTE_KEYS = (
    "candidate_row_kind",
    "candidate_id",
    "note_code",
    "note",
)

REVIEW_TOP_LEVEL_KEYS = {
    "schema_version",
    "review_id",
    "authority_kind",
    "document_source_position",
    "source_document_id",
    "review_method",
    "page_review_rows",
    "occurrence_specs",
    "local_anchor_specs",
    "repeat_alias_specs",
    "integrity",
    "status",
}


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return source_tools.canonical_json_bytes(value)


def _canonical_digest(value: Any) -> str:
    return _sha256(_canonical_bytes(value))


def _content_sha256(value: Mapping[str, Any]) -> str:
    copied = copy.deepcopy(value)
    copied["integrity"]["content_sha256"] = "0" * 64
    return _canonical_digest(copied)


def _expect_keys(
    value: Mapping[str, Any], keys: Sequence[str] | set[str], label: str
) -> None:
    if isinstance(keys, set):
        valid = set(value) == keys
    else:
        # Rows are constructed in the protocol's displayed order.  Sealed JSON
        # is canonicalized with lexicographically sorted object members, so a
        # parsed committed row lawfully has that canonical member order.
        actual = tuple(value)
        expected = tuple(keys)
        valid = actual in {expected, tuple(sorted(expected))}
    if not valid:
        raise ValueError(f"{label} keyset drift")


def _strict_json(path: Path, label: str) -> dict[str, Any]:
    value = source_tools.strict_parse_document(path.read_bytes(), label)
    if not isinstance(value, dict):
        raise ValueError(f"{label} is not an object")
    return value


def _source_replay_and_index() -> tuple[dict[str, Any], dict[str, Any]]:
    replay = stage1_candidates.load_source_replay()
    index_raw = stage1_candidates.INDEX_PATH.read_bytes()
    index = source_tools.strict_parse_document(
        index_raw, "R_Q candidate index"
    )
    if not isinstance(index, dict):
        raise ValueError("R_Q candidate index is not an object")
    stage1_candidates.validate_candidate_index(index, replay)
    if _sha256(index_raw) != (
        "a90dfea13cdd74a7d612acdee76c91d6c9e2fd2ed9f9a6befc6a99d9f773a446"
    ) or index["integrity"]["content_sha256"] != (
        "ed80f518b0d2150b9d2c2f4d2e94ca517fc40d1dcd5e29a0c75833d40e86be64"
    ):
        raise ValueError("R_Q candidate index sealed identity drift")
    return replay, index


def _document_identity(
    replay: Mapping[str, Any], index: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    document = copy.deepcopy(
        replay["source_document_replay"]["questionnaire_documents"][
            DOCUMENT_SOURCE_POSITION - 1
        ]
    )
    identity = index["document_candidate_manifest_rows"][
        DOCUMENT_SOURCE_POSITION - 1
    ]
    if (
        identity["document_source_position"] != DOCUMENT_SOURCE_POSITION
        or identity["source_document_id"] != document["source_document_id"]
    ):
        raise ValueError("document 60 candidate-index resolution drift")
    return document, copy.deepcopy(identity)


def _extract_page_texts(
    document: Mapping[str, Any], replay: Mapping[str, Any]
) -> list[str]:
    source_path = CAPTURE_ROOT / Path(document["canonical_source_path"]).name
    source_tools._verified_file(
        source_path,
        document["byte_size"],
        document["sha256"],
        document["source_document_id"],
    )
    if questionnaire_inventory._pdftotext_version() != "26.04.0":
        raise ValueError("document 60 Poppler version drift")
    page_texts = questionnaire_inventory._pdftotext_pages(source_path)
    expected = [
        row
        for row in replay["questionnaire_page_replay"][
            "questionnaire_page_rows"
        ]
        if row["source_document_id"] == document["source_document_id"]
    ]
    if len(page_texts) != 15 or len(page_texts) != len(expected):
        raise ValueError("document 60 page denominator drift")
    for page_text, page_row in zip(page_texts, expected, strict=True):
        page_bytes = page_text.encode("utf-8")
        if (
            len(page_bytes) != page_row["page_text_utf8_size_bytes"]
            or _sha256(page_bytes) != page_row["page_text_utf8_sha256"]
        ):
            raise ValueError("document 60 page replay drift")
    return page_texts


def _load_review(
    document: Mapping[str, Any], page_texts: Sequence[str]
) -> dict[str, Any]:
    if REVIEW_PATH.stat().st_size >= MAX_COMMITTED_FILE_BYTES:
        raise ValueError("document 60 source review exceeds artifact-size law")
    review = _strict_json(REVIEW_PATH, "document 60 source review")
    validate_review(review, document, page_texts)
    return review


def _load_candidates(
    replay: Mapping[str, Any],
    identity: Mapping[str, Any],
    page_texts: Sequence[str],
) -> dict[str, Any]:
    path = ROOT / identity["path"]
    raw = path.read_bytes()
    if (
        len(raw) != identity["byte_size"]
        or _sha256(raw) != identity["raw_sha256"]
    ):
        raise ValueError("document 60 candidate raw identity drift")
    value = source_tools.strict_parse_document(raw, "document 60 candidates")
    if not isinstance(value, dict):
        raise ValueError("document 60 candidates are not an object")
    stage1_candidates.validate_document_candidates(value, replay, page_texts)
    if (
        value["integrity"]["content_sha256"] != identity["content_sha256"]
        or value["candidate_manifest"]["candidate_payload_sha256"]
        != identity["candidate_payload_sha256"]
    ):
        raise ValueError("document 60 candidate content identity drift")
    return value


def _utf8_slice(page_text: str, start: int, end: int) -> tuple[bytes, str]:
    page_bytes = page_text.encode("utf-8")
    if (
        not isinstance(start, int)
        or isinstance(start, bool)
        or not isinstance(end, int)
        or isinstance(end, bool)
        or not 0 <= start < end <= len(page_bytes)
    ):
        raise ValueError("review occurrence span is outside page bytes")
    try:
        matched = page_bytes[start:end].decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ValueError("review occurrence is not UTF-8 aligned") from error
    if not matched:
        raise ValueError("review occurrence is empty")
    return page_bytes[start:end], matched


def _source_printed_identifier(page_text: str, byte_start: int) -> str | None:
    for line in stage1_candidates._physical_lines(page_text):
        line_byte_start = len(page_text[: line["start"]].encode("utf-8"))
        line_byte_end = len(page_text[: line["end"]].encode("utf-8"))
        if line_byte_start <= byte_start < line_byte_end:
            return stage1_candidates._printed_identifier(line["text"])
    raise ValueError(
        "source review occurrence does not resolve to a physical line"
    )


def validate_review(
    review: Mapping[str, Any],
    document: Mapping[str, Any],
    page_texts: Sequence[str],
) -> None:
    if _contains_forbidden_path_product(review):
        raise ValueError("source review serialized a full path product")
    _expect_keys(review, REVIEW_TOP_LEVEL_KEYS, "source review")
    expected_review_id = "rq-stage2-source-review:" + _canonical_digest(
        [document["source_document_id"], DOCUMENT_SOURCE_POSITION]
    )
    if (
        review["schema_version"] != REVIEW_SCHEMA_VERSION
        or review["review_id"] != expected_review_id
        or review["authority_kind"]
        != "reviewer_authored_source_bytes_only_nonauthority"
        or review["document_source_position"] != DOCUMENT_SOURCE_POSITION
        or review["source_document_id"] != document["source_document_id"]
        or review["status"] != "complete"
        or review["integrity"]
        != {
            "canonicalization": CANONICALIZATION,
            "content_sha256": _content_sha256(review),
        }
    ):
        raise ValueError("source review identity drift")
    method = review["review_method"]
    _expect_keys(
        method,
        (
            "source_rows_derived_from_page_bytes",
            "whole_page_review",
            "span_granularity",
            "candidate_nonselection",
            "flow_parent_representation",
            "flow_edge_order",
            "global_ids_assigned",
        ),
        "source review method",
    )
    if method != {
        "source_rows_derived_from_page_bytes": True,
        "whole_page_review": "all_15_pages_including_empty_occurrence_pages",
        "span_granularity": "exact_utf8_lexeme_physical_line_or_source_block",
        "candidate_nonselection": "candidates_joined_only_after_source_rows_complete",
        "flow_parent_representation": "direct_parent_occurrence_ids_no_path_products",
        "flow_edge_order": "logical_dag_may_reference_later_extracted_labels",
        "global_ids_assigned": False,
    }:
        raise ValueError("source review method drift")

    page_rows = review["page_review_rows"]
    if len(page_rows) != len(page_texts):
        raise ValueError("source review page cover drift")
    for page_number, (row, page_text) in enumerate(
        zip(page_rows, page_texts, strict=True), start=1
    ):
        _expect_keys(
            row,
            (
                "page_number",
                "page_text_utf8_sha256",
                "whole_page_review_complete",
                "review_status",
                "review_note",
            ),
            "source review page row",
        )
        if (
            row["page_number"] != page_number
            or row["page_text_utf8_sha256"]
            != _sha256(page_text.encode("utf-8"))
            or row["whole_page_review_complete"] is not True
            or row["review_status"] != "complete"
            or not isinstance(row["review_note"], str)
            or not row["review_note"]
        ):
            raise ValueError("source review page row drift")

    occurrence_specs = review["occurrence_specs"]
    review_ids: set[str] = set()
    spec_by_id: dict[str, Mapping[str, Any]] = {}
    review_specs_by_page_kind: dict[
        tuple[int, str], list[Mapping[str, Any]]
    ] = defaultdict(list)
    last_order: tuple[Any, ...] | None = None
    for spec in occurrence_specs:
        _expect_keys(
            spec,
            (
                "review_occurrence_id",
                "page_number",
                "utf8_byte_start",
                "utf8_byte_end",
                "occurrence_kind",
                "parent_review_occurrence_ids",
                "review_note",
            ),
            "source review occurrence spec",
        )
        page_number = spec["page_number"]
        start = spec["utf8_byte_start"]
        end = spec["utf8_byte_end"]
        if (
            not isinstance(page_number, int)
            or isinstance(page_number, bool)
            or not 1 <= page_number <= len(page_texts)
            or not isinstance(start, int)
            or isinstance(start, bool)
            or not isinstance(end, int)
            or isinstance(end, bool)
            or spec["occurrence_kind"] not in KIND_ORDER
            or not isinstance(spec["review_note"], str)
            or not spec["review_note"]
        ):
            raise ValueError("source review occurrence metadata drift")
        matched_bytes, _matched_text = _utf8_slice(
            page_texts[page_number - 1],
            start,
            end,
        )
        expected_id = "rq-review-occurrence:" + _canonical_digest(
            [
                document["source_document_id"],
                page_number,
                spec["utf8_byte_start"],
                spec["utf8_byte_end"],
                spec["occurrence_kind"],
                _sha256(matched_bytes),
            ]
        )
        parents = spec["parent_review_occurrence_ids"]
        if (
            not isinstance(parents, list)
            or any(not isinstance(parent, str) for parent in parents)
            or len(parents) != len(set(parents))
            or spec["review_occurrence_id"] in parents
            or any(
                FORBIDDEN_PARENT_PATH_MARKER in parent for parent in parents
            )
        ):
            raise ValueError("source review local parent-edge domain drift")
        order = (
            page_number,
            spec["utf8_byte_start"],
            spec["utf8_byte_end"],
            KIND_ORDER[spec["occurrence_kind"]],
            spec["review_occurrence_id"],
        )
        if (
            spec["review_occurrence_id"] != expected_id
            or expected_id in review_ids
            or last_order is not None
            and order <= last_order
        ):
            raise ValueError("source review occurrence order or ID drift")
        review_ids.add(expected_id)
        spec_by_id[expected_id] = spec
        review_specs_by_page_kind[
            (page_number, spec["occurrence_kind"])
        ].append(spec)
        last_order = order
    # Preserve one independently reviewed semantic atom at each same-kind
    # interval. Different occurrence kinds may lawfully share source bytes.
    for same_kind_specs in review_specs_by_page_kind.values():
        for position, left in enumerate(same_kind_specs):
            for right in same_kind_specs[position + 1 :]:
                if right["utf8_byte_start"] >= left["utf8_byte_end"]:
                    break
                raise ValueError(
                    "document 60 source review has partially overlapping "
                    "same-kind atoms"
                )
    occurrence_counts_by_page = Counter(
        spec["page_number"] for spec in occurrence_specs
    )
    for row in page_rows:
        expected_note = (
            "Exact Poppler page bytes reviewed in full for all ten "
            f"occurrence kinds; {occurrence_counts_by_page[row['page_number']]} "
            "retained atoms."
        )
        if row["review_note"] != expected_note:
            raise ValueError("source review page occurrence census drift")
    occurrence_order = {
        spec["review_occurrence_id"]: position
        for position, spec in enumerate(occurrence_specs)
    }
    for spec in occurrence_specs:
        parents = spec["parent_review_occurrence_ids"]
        if any(
            parent not in spec_by_id
            or spec_by_id[parent]["occurrence_kind"] != "flow_branch_label"
            for parent in parents
        ):
            raise ValueError("source review has unresolved nonbranch parent")
        if parents != sorted(parents, key=occurrence_order.__getitem__):
            raise ValueError(
                "source review local parents are out of source order"
            )
    unresolved_flow_ids = {
        spec["review_occurrence_id"]
        for spec in occurrence_specs
        if spec["occurrence_kind"] == "flow_branch_label"
    }
    resolved_flow_ids: set[str] = set()
    while unresolved_flow_ids:
        newly_resolved = {
            review_id
            for review_id in unresolved_flow_ids
            if set(spec_by_id[review_id]["parent_review_occurrence_ids"])
            <= resolved_flow_ids
        }
        if not newly_resolved:
            raise ValueError("source review flow graph has a cycle")
        resolved_flow_ids.update(newly_resolved)
        unresolved_flow_ids.difference_update(newly_resolved)

    anchor_specs = review["local_anchor_specs"]
    anchor_covered: set[str] = set()
    for row in anchor_specs:
        _expect_keys(
            row,
            (
                "review_occurrence_id",
                "node_domain",
                "classification",
                "printed_identifier",
                "parent_review_occurrence_ids",
                "parent_resolution_note",
                "classification_status",
            ),
            "source review anchor spec",
        )
        occurrence = spec_by_id.get(row["review_occurrence_id"])
        expected_classification = None
        if occurrence is not None:
            kind = occurrence["occurrence_kind"]
            if kind == "role_anchor":
                _matched_bytes, matched_text = _utf8_slice(
                    page_texts[occurrence["page_number"] - 1],
                    occurrence["utf8_byte_start"],
                    occurrence["utf8_byte_end"],
                )
                expected_classification = (
                    "role",
                    stage1_candidates._role_classification(matched_text),
                )
            else:
                expected_classification = ANCHOR_CLASSIFICATION.get(kind)
        if (
            occurrence is None
            or occurrence["occurrence_kind"] not in ANCHOR_KINDS
        ):
            raise ValueError("source review anchor occurrence drift")
        if row["review_occurrence_id"] in anchor_covered:
            raise ValueError("source review anchor duplicated")
        if (
            expected_classification
            != (row["node_domain"], row["classification"])
            or row["printed_identifier"]
            != _source_printed_identifier(
                page_texts[occurrence["page_number"] - 1],
                occurrence["utf8_byte_start"],
            )
            or row["classification_status"] != "provisional_document_local"
            or len(row["parent_review_occurrence_ids"])
            != len(set(row["parent_review_occurrence_ids"]))
            or row["review_occurrence_id"]
            in row["parent_review_occurrence_ids"]
            or not isinstance(row["parent_resolution_note"], str)
            or not row["parent_resolution_note"]
        ):
            raise ValueError("source review anchor status drift")
        if any(
            parent not in review_ids
            or spec_by_id[parent]["occurrence_kind"] not in ANCHOR_KINDS
            for parent in row["parent_review_occurrence_ids"]
        ):
            raise ValueError("source review anchor parent drift")
        component_kinds = {
            "remuneration_component_anchor",
            "context_anchor",
        }
        parent_kinds = {
            "job_anchor",
            "role_total_anchor",
            "farm_aggregate_anchor",
            "business_aggregate_anchor",
        }
        if (
            occurrence["occurrence_kind"] not in component_kinds
            and row["parent_review_occurrence_ids"]
            or any(
                spec_by_id[parent]["occurrence_kind"] not in parent_kinds
                for parent in row["parent_review_occurrence_ids"]
            )
        ):
            raise ValueError("source review anchor parent kind drift")
        anchor_covered.add(row["review_occurrence_id"])
    if anchor_covered != {
        spec["review_occurrence_id"]
        for spec in occurrence_specs
        if spec["occurrence_kind"] in ANCHOR_KINDS
    }:
        raise ValueError("source review anchor exact cover drift")

    repeat_specs = review["repeat_alias_specs"]
    repeat_covered: set[str] = set()
    for row in repeat_specs:
        _expect_keys(
            row,
            (
                "review_occurrence_id",
                "relation",
                "alias_anchor_review_occurrence_ids",
                "canonical_anchor_review_occurrence_ids",
                "evidence_review_occurrence_ids",
                "target_scope",
                "resolution_status",
            ),
            "source review repeat spec",
        )
        occurrence = spec_by_id.get(row["review_occurrence_id"])
        alias_ids = row["alias_anchor_review_occurrence_ids"]
        canonical_ids = row["canonical_anchor_review_occurrence_ids"]
        evidence = row["evidence_review_occurrence_ids"]
        if (
            occurrence is None
            or occurrence["occurrence_kind"] != "repeat_or_alias_instruction"
            or row["review_occurrence_id"] in repeat_covered
            or row["relation"] not in ALIAS_RELATIONS
            or not all(
                isinstance(items, list)
                for items in (alias_ids, canonical_ids, evidence)
            )
            or any(
                len(items) != len(set(items))
                for items in (alias_ids, canonical_ids, evidence)
            )
            or set(alias_ids) & set(canonical_ids)
            or any(
                item not in review_ids
                or spec_by_id[item]["occurrence_kind"] not in ANCHOR_KINDS
                for item in [*alias_ids, *canonical_ids]
            )
            or row["review_occurrence_id"] not in evidence
            or any(
                item not in review_ids
                or spec_by_id[item]["occurrence_kind"]
                not in {*ANCHOR_KINDS, "repeat_or_alias_instruction"}
                for item in evidence
            )
            or not {*alias_ids, *canonical_ids}.issubset(evidence)
            or any(
                items != sorted(items, key=lambda item: occurrence_order[item])
                for items in (alias_ids, canonical_ids, evidence)
            )
            or row["target_scope"]
            not in {"document_local", "cross_document", "unresolved"}
            or row["resolution_status"]
            not in {
                "document_local_source_evidence_complete",
                "preserved_for_global_resolution",
            }
            or row["target_scope"] != "document_local"
            and canonical_ids
            or row["resolution_status"]
            == "document_local_source_evidence_complete"
            and (
                row["target_scope"] != "document_local"
                or not alias_ids
                or not canonical_ids
            )
            or canonical_ids
            and row["resolution_status"]
            != "document_local_source_evidence_complete"
            or row["relation"] == "same_printed_identifier_and_exact_label"
            and (not alias_ids or len(canonical_ids) != 1)
        ):
            raise ValueError("source review repeat evidence drift")
        if row["relation"] == "same_printed_identifier_and_exact_label":
            compared_specs = [
                spec_by_id[item] for item in [*canonical_ids, *alias_ids]
            ]
            compared_labels = []
            compared_printed_identifiers = []
            anchor_by_review_id = {
                item["review_occurrence_id"]: item for item in anchor_specs
            }
            for compared in compared_specs:
                _raw, label = _utf8_slice(
                    page_texts[compared["page_number"] - 1],
                    compared["utf8_byte_start"],
                    compared["utf8_byte_end"],
                )
                compared_labels.append(label)
                compared_printed_identifiers.append(
                    anchor_by_review_id[compared["review_occurrence_id"]][
                        "printed_identifier"
                    ]
                )
            if (
                len(set(compared_labels)) != 1
                or len(set(compared_printed_identifiers)) != 1
                or compared_printed_identifiers[0] is None
            ):
                raise ValueError(
                    "source review printed-identifier alias drift"
                )
        repeat_covered.add(row["review_occurrence_id"])
    if repeat_covered != {
        spec["review_occurrence_id"]
        for spec in occurrence_specs
        if spec["occurrence_kind"] == "repeat_or_alias_instruction"
    }:
        raise ValueError("source review repeat exact cover drift")


def _locator(document: Mapping[str, Any]) -> dict[str, Any]:
    wave = document["interview_waves"][0]
    locator_id = "psid-whole-document:" + _canonical_digest(
        [
            document["source_document_id"],
            wave,
            document["sha256"],
            document["byte_size"],
        ]
    )
    return dict(
        zip(
            LOCATOR_KEYS,
            (
                locator_id,
                document["source_document_id"],
                wave,
                Path(document["canonical_source_path"]).name,
                "whole_document_exact_file_range",
                0,
                document["byte_size"],
                document["byte_size"],
                document["sha256"],
                document["sha256"],
                "all_pages_and_flow_branches",
            ),
            strict=True,
        )
    )


def _occurrence_locator_sha256(
    document: Mapping[str, Any], skeleton: Mapping[str, Any]
) -> str:
    return _canonical_digest(
        [
            document["source_document_id"],
            document["canonical_source_path"],
            "questionnaire_page_utf8_span",
            [
                document["interview_waves"][0],
                skeleton["page_number"],
                skeleton["utf8_byte_start"],
                skeleton["utf8_byte_end"],
                skeleton["occurrence_index_on_page"],
                skeleton["semantic_ordinal_at_span"],
                skeleton["occurrence_kind"],
            ],
        ]
    )


def _occurrence_row(
    document: Mapping[str, Any],
    locator_id: str,
    skeleton: Mapping[str, Any],
    parent_occurrence_ids: Sequence[str],
) -> dict[str, Any]:
    remaining = (
        document["source_document_id"],
        locator_id,
        _occurrence_locator_sha256(document, skeleton),
        document["interview_waves"][0],
        skeleton["page_number"],
        skeleton["utf8_byte_start"],
        skeleton["utf8_byte_end"],
        skeleton["occurrence_index_on_page"],
        skeleton["semantic_ordinal_at_span"],
        skeleton["occurrence_kind"],
        skeleton["matched_text"],
        skeleton["matched_utf8_sha256"],
        list(parent_occurrence_ids),
    )
    occurrence_id = "psid-questionnaire-occurrence:" + _canonical_digest(
        list(remaining)
    )
    return dict(
        zip(
            OCCURRENCE_KEYS,
            (occurrence_id, *remaining),
            strict=True,
        )
    )


def _build_occurrences_and_branches(
    document: Mapping[str, Any],
    page_texts: Sequence[str],
    review: Mapping[str, Any],
    locator_id: str,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, list[str]],
    dict[str, list[str]],
]:
    branches: list[dict[str, Any]] = []
    occurrence_by_review_id: dict[str, dict[str, Any]] = {}
    branch_by_source_occurrence_id: dict[str, dict[str, Any]] = {}
    next_occurrence_index_by_page: dict[int, int] = defaultdict(int)
    prepared_specs: list[tuple[Mapping[str, Any], bytes, str, int]] = []
    occurrence_by_coordinate: dict[tuple[int, int], dict[str, Any]] = {}

    # Reserve every same-page index in source order before resolving edges.
    # Questionnaire diagrams can print a child response before all of its
    # logical parents, so source ordering and DAG ordering are independent.
    for spec in review["occurrence_specs"]:
        page_number = spec["page_number"]
        matched_bytes, matched_text = _utf8_slice(
            page_texts[page_number - 1],
            spec["utf8_byte_start"],
            spec["utf8_byte_end"],
        )
        occurrence_index = next_occurrence_index_by_page[page_number]
        next_occurrence_index_by_page[page_number] += 1
        prepared_specs.append(
            (spec, matched_bytes, matched_text, occurrence_index)
        )

    def skeleton(
        spec: Mapping[str, Any],
        matched_bytes: bytes,
        matched_text: str,
        occurrence_index: int,
    ) -> dict[str, Any]:
        return {
            "page_number": spec["page_number"],
            "utf8_byte_start": spec["utf8_byte_start"],
            "utf8_byte_end": spec["utf8_byte_end"],
            "occurrence_index_on_page": occurrence_index,
            "semantic_ordinal_at_span": 0,
            "occurrence_kind": spec["occurrence_kind"],
            "matched_text": matched_text,
            "matched_utf8_sha256": _sha256(matched_bytes),
        }

    def resolve_parent_occurrence_ids(
        spec: Mapping[str, Any],
    ) -> list[str]:
        result: list[str] = []
        for parent_review_id in spec["parent_review_occurrence_ids"]:
            parent = occurrence_by_review_id.get(parent_review_id)
            if parent is None:
                raise ValueError("source review parent occurrence unresolved")
            result.append(parent["questionnaire_occurrence_id"])
        return result

    # Resolve branch labels in logical topological order. One printed label
    # remains one occurrence and one branch even when it has several direct
    # incoming edges; no route products are materialized.
    pending_flow_specs = [
        prepared
        for prepared in prepared_specs
        if prepared[0]["occurrence_kind"] == "flow_branch_label"
    ]
    while pending_flow_specs:
        ready_flow_specs = [
            prepared
            for prepared in pending_flow_specs
            if all(
                parent in occurrence_by_review_id
                for parent in prepared[0]["parent_review_occurrence_ids"]
            )
        ]
        if not ready_flow_specs:
            raise ValueError("source review flow graph has a cycle")
        for (
            spec,
            matched_bytes,
            matched_text,
            occurrence_index,
        ) in ready_flow_specs:
            parent_occurrence_ids = resolve_parent_occurrence_ids(spec)
            occurrence = _occurrence_row(
                document,
                locator_id,
                skeleton(spec, matched_bytes, matched_text, occurrence_index),
                parent_occurrence_ids,
            )
            review_id = spec["review_occurrence_id"]
            occurrence_by_review_id[review_id] = occurrence
            occurrence_by_coordinate[
                (spec["page_number"], occurrence_index)
            ] = occurrence
            parent_branch_ids = (
                [FLOW_ROOT]
                if not parent_occurrence_ids
                else [
                    branch_by_source_occurrence_id[parent_id]["flow_branch_id"]
                    for parent_id in parent_occurrence_ids
                ]
            )
            branch_id = "questionnaire-flow:" + _canonical_digest(
                [
                    parent_branch_ids,
                    document["interview_waves"][0],
                    occurrence["questionnaire_occurrence_id"],
                ]
            )
            branch = dict(
                zip(
                    FLOW_BRANCH_KEYS,
                    (
                        branch_id,
                        parent_branch_ids,
                        parent_occurrence_ids,
                        occurrence["questionnaire_occurrence_id"],
                        document["interview_waves"][0],
                        locator_id,
                        occurrence["page_number"],
                        occurrence["occurrence_index_on_page"],
                        occurrence["matched_text"],
                        occurrence["matched_utf8_sha256"],
                    ),
                    strict=True,
                )
            )
            branches.append(branch)
            branch_by_source_occurrence_id[
                occurrence["questionnaire_occurrence_id"]
            ] = branch
        ready_ids = {
            prepared[0]["review_occurrence_id"]
            for prepared in ready_flow_specs
        }
        pending_flow_specs = [
            prepared
            for prepared in pending_flow_specs
            if prepared[0]["review_occurrence_id"] not in ready_ids
        ]

    # Now all route labels exist, including later printed routes to a reused
    # screen. Emit every non-flow atom once with direct parents only.
    for spec, matched_bytes, matched_text, occurrence_index in prepared_specs:
        if spec["occurrence_kind"] == "flow_branch_label":
            continue
        parent_occurrence_ids = resolve_parent_occurrence_ids(spec)
        occurrence = _occurrence_row(
            document,
            locator_id,
            skeleton(spec, matched_bytes, matched_text, occurrence_index),
            parent_occurrence_ids,
        )
        occurrence_by_review_id[spec["review_occurrence_id"]] = occurrence
        occurrence_by_coordinate[(spec["page_number"], occurrence_index)] = (
            occurrence
        )

    occurrences = [
        occurrence_by_coordinate[coordinate]
        for coordinate in sorted(occurrence_by_coordinate)
    ]
    occurrence_position = {
        occurrence["questionnaire_occurrence_id"]: position
        for position, occurrence in enumerate(occurrences)
    }
    branches.sort(
        key=lambda branch: occurrence_position[branch["source_occurrence_id"]]
    )
    return (
        occurrences,
        branches,
        {
            review_id: [row["questionnaire_occurrence_id"]]
            for review_id, row in occurrence_by_review_id.items()
        },
        {
            review_id: [
                branch_by_source_occurrence_id[
                    occurrence["questionnaire_occurrence_id"]
                ]["flow_branch_id"]
            ]
            for review_id, occurrence in occurrence_by_review_id.items()
            if occurrence["occurrence_kind"] == "flow_branch_label"
        },
    )


def _group_rows(
    rows: Sequence[Mapping[str, Any]], key: str
) -> dict[Any, list[Mapping[str, Any]]]:
    result: dict[Any, list[Mapping[str, Any]]] = {}
    for row in rows:
        result.setdefault(row[key], []).append(row)
    return result


def _page_rows(
    document: Mapping[str, Any],
    page_texts: Sequence[str],
    locator_id: str,
    occurrences: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    occurrences_by_page = _group_rows(occurrences, "page_number")
    rows: list[dict[str, Any]] = []
    wave = document["interview_waves"][0]
    for page_number, page_text in enumerate(page_texts, start=1):
        page_digest = _sha256(page_text.encode("utf-8"))
        page_id = "psid-questionnaire-page:" + _canonical_digest(
            [document["source_document_id"], wave, page_number, page_digest]
        )
        rows.append(
            dict(
                zip(
                    PAGE_KEYS,
                    (
                        page_id,
                        document["source_document_id"],
                        locator_id,
                        wave,
                        page_number,
                        page_digest,
                        [
                            row["questionnaire_occurrence_id"]
                            for row in occurrences_by_page.get(page_number, [])
                        ],
                        "complete",
                    ),
                    strict=True,
                )
            )
        )
    return rows


def _local_anchor_rows(
    review: Mapping[str, Any],
    occurrences: Sequence[Mapping[str, Any]],
    occurrence_ids_by_review_id: Mapping[str, Sequence[str]],
) -> list[dict[str, Any]]:
    occurrence_by_id = {
        row["questionnaire_occurrence_id"]: row for row in occurrences
    }
    result: list[dict[str, Any]] = []
    for spec in review["local_anchor_specs"]:
        output_ids = occurrence_ids_by_review_id[spec["review_occurrence_id"]]
        if len(output_ids) != 1:
            raise ValueError("local anchor occurrence does not resolve once")
        occurrence = occurrence_by_id[output_ids[0]]
        parents: list[str] = []
        for parent_review_id in spec["parent_review_occurrence_ids"]:
            parents.extend(occurrence_ids_by_review_id[parent_review_id])
        values = (
            occurrence["questionnaire_occurrence_id"],
            occurrence["occurrence_kind"],
            spec["node_domain"],
            spec["classification"],
            spec["printed_identifier"],
            occurrence["matched_text"],
            occurrence["matched_utf8_sha256"],
            parents,
            spec["classification_status"],
        )
        local_id = "rq-local-anchor-classification:" + _canonical_digest(
            list(values)
        )
        result.append(
            dict(
                zip(
                    LOCAL_ANCHOR_KEYS,
                    (local_id, *values),
                    strict=True,
                )
            )
        )
    return result


def _local_repeat_rows(
    review: Mapping[str, Any],
    occurrence_ids_by_review_id: Mapping[str, Sequence[str]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []

    def resolve(review_ids: Sequence[str]) -> list[str]:
        values: list[str] = []
        for review_id in review_ids:
            values.extend(occurrence_ids_by_review_id[review_id])
        return values

    for spec in review["repeat_alias_specs"]:
        source_ids = resolve([spec["review_occurrence_id"]])
        if len(source_ids) != 1:
            raise ValueError("repeat evidence source does not resolve once")
        values = (
            source_ids[0],
            spec["relation"],
            resolve(spec["alias_anchor_review_occurrence_ids"]),
            resolve(spec["canonical_anchor_review_occurrence_ids"]),
            resolve(spec["evidence_review_occurrence_ids"]),
            spec["target_scope"],
            spec["resolution_status"],
        )
        local_id = "rq-local-repeat-alias-evidence:" + _canonical_digest(
            list(values)
        )
        result.append(
            dict(
                zip(
                    LOCAL_REPEAT_KEYS,
                    (local_id, *values),
                    strict=True,
                )
            )
        )
    return result


def _candidate_id(row_kind: str, row: Mapping[str, Any]) -> str:
    key = {
        "whole_document_locator": "candidate_locator_id",
        "page": "candidate_page_id",
        "occurrence": "candidate_occurrence_id",
        "flow_path": "candidate_flow_path_id",
        "anchor_classification": "candidate_anchor_classification_id",
    }[row_kind]
    return row[key]


def _stage2_id(row_kind: str, row: Mapping[str, Any]) -> str:
    key = {
        "whole_document_locator": "locator_id",
        "page": "questionnaire_page_id",
        "occurrence": "questionnaire_occurrence_id",
        "flow_branch": "flow_branch_id",
        "local_anchor_classification": "local_anchor_classification_id",
        "local_repeat_alias_evidence": "local_repeat_alias_evidence_id",
    }[row_kind]
    return row[key]


def _candidate_disposition_row(
    row_kind: str,
    candidate_id: str,
    disposition: str,
    stage2_row_ids: Sequence[str],
) -> dict[str, Any]:
    return dict(
        zip(
            CANDIDATE_DISPOSITION_KEYS,
            (
                row_kind,
                candidate_id,
                disposition,
                list(stage2_row_ids),
                "complete",
            ),
            strict=True,
        )
    )


def _output_adjudication_row(
    row_kind: str,
    stage2_row_id: str,
    candidate_ids: Sequence[str],
    action: str,
) -> dict[str, Any]:
    return dict(
        zip(
            OUTPUT_ADJUDICATION_KEYS,
            (
                row_kind,
                stage2_row_id,
                list(candidate_ids),
                action,
                True,
                True,
                "complete",
            ),
            strict=True,
        )
    )


def _note_row(
    row_kind: str, candidate_id: str, note_code: str, note: str
) -> dict[str, Any]:
    return dict(
        zip(
            NOTE_KEYS,
            (row_kind, candidate_id, note_code, note),
            strict=True,
        )
    )


def _match_candidate_occurrences(
    candidate_rows: Sequence[Mapping[str, Any]],
    occurrences: Sequence[Mapping[str, Any]],
) -> tuple[
    dict[str, list[str]],
    dict[str, list[str]],
    dict[str, str],
]:
    """Join candidates only after the reviewer-authored source rows exist."""

    candidate_to_outputs: dict[str, list[str]] = {}
    output_to_candidates: dict[str, list[str]] = defaultdict(list)
    candidate_disposition: dict[str, str] = {}
    candidate_order = {
        row["candidate_occurrence_id"]: position
        for position, row in enumerate(candidate_rows)
    }

    candidates_by_coordinate: dict[tuple[Any, ...], Mapping[str, Any]] = {}
    for candidate in candidate_rows:
        coordinate = (
            candidate["page_number"],
            candidate["utf8_byte_start"],
            candidate["utf8_byte_end"],
            candidate["occurrence_kind_candidate"],
        )
        candidates_by_coordinate[coordinate] = candidate
    outputs_by_coordinate: dict[tuple[Any, ...], list[Mapping[str, Any]]] = (
        defaultdict(list)
    )
    outputs_by_page_kind: dict[tuple[int, str], list[Mapping[str, Any]]] = (
        defaultdict(list)
    )
    for output in occurrences:
        outputs_by_coordinate[
            (
                output["page_number"],
                output["utf8_byte_start"],
                output["utf8_byte_end"],
                output["occurrence_kind"],
            )
        ].append(output)
        outputs_by_page_kind[
            (output["page_number"], output["occurrence_kind"])
        ].append(output)
    for coordinate, coordinate_outputs in outputs_by_coordinate.items():
        candidate = candidates_by_coordinate.get(coordinate)
        if candidate is None:
            continue
        candidate_id = candidate["candidate_occurrence_id"]
        output_ids = [
            output["questionnaire_occurrence_id"]
            for output in coordinate_outputs
        ]
        candidate_to_outputs[candidate_id] = output_ids
        candidate_disposition[candidate_id] = (
            "accepted" if len(output_ids) == 1 else "split"
        )
        for output_id in output_ids:
            output_to_candidates[output_id].append(candidate_id)

    unmatched_candidates = [
        row
        for row in candidate_rows
        if row["candidate_occurrence_id"] not in candidate_to_outputs
    ]
    for candidate in unmatched_candidates:
        candidate_id = candidate["candidate_occurrence_id"]
        overlaps = [
            output
            for output in outputs_by_page_kind[
                (
                    candidate["page_number"],
                    candidate["occurrence_kind_candidate"],
                )
            ]
            if output["utf8_byte_start"] < candidate["utf8_byte_end"]
            and candidate["utf8_byte_start"] < output["utf8_byte_end"]
        ]
        overlaps.sort(
            key=lambda row: (
                row["utf8_byte_start"],
                row["utf8_byte_end"],
                row["semantic_ordinal_at_span"],
            )
        )
        if not overlaps:
            candidate_to_outputs[candidate_id] = []
            candidate_disposition[candidate_id] = "rejected"
            continue
        output_ids = [row["questionnaire_occurrence_id"] for row in overlaps]
        disposition = "split" if len(output_ids) > 1 else "modified"
        candidate_to_outputs[candidate_id] = output_ids
        candidate_disposition[candidate_id] = disposition
        for output_id in output_ids:
            output_to_candidates[output_id].append(candidate_id)

    for candidate_ids in output_to_candidates.values():
        candidate_ids.sort(key=candidate_order.__getitem__)

    return (
        candidate_to_outputs,
        dict(output_to_candidates),
        candidate_disposition,
    )


def _translated_candidate_parent_occurrence_ids(
    candidate_flow: Mapping[str, Any],
    candidate_branch_source: Mapping[str, str],
    candidate_occurrence_outputs: Mapping[str, Sequence[str]],
    branches_by_source_occurrence_id: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    translated: list[str] = []
    for candidate_branch_id in candidate_flow["candidate_parent_path"][1:]:
        source_candidate_id = candidate_branch_source.get(candidate_branch_id)
        if source_candidate_id is None:
            return []
        output_occurrence_ids = candidate_occurrence_outputs.get(
            source_candidate_id, []
        )
        candidate_parent_ids = [
            output_id
            for output_id in output_occurrence_ids
            if output_id in branches_by_source_occurrence_id
        ]
        if not candidate_parent_ids:
            return []
        translated.extend(candidate_parent_ids)
    return list(dict.fromkeys(translated))


def _adjudicate(
    candidates: Mapping[str, Any],
    locator: Mapping[str, Any],
    pages: Sequence[Mapping[str, Any]],
    occurrences: Sequence[Mapping[str, Any]],
    branches: Sequence[Mapping[str, Any]],
    local_anchors: Sequence[Mapping[str, Any]],
    local_repeats: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    dispositions: list[dict[str, Any]] = []
    output_adjudications: list[dict[str, Any]] = []
    notes: list[dict[str, Any]] = []

    locator_candidate = candidates["whole_document_locator_candidate"]
    locator_candidate_id = locator_candidate["candidate_locator_id"]
    dispositions.append(
        _candidate_disposition_row(
            "whole_document_locator",
            locator_candidate_id,
            "accepted",
            [locator["locator_id"]],
        )
    )
    output_adjudications.append(
        _output_adjudication_row(
            "whole_document_locator",
            locator["locator_id"],
            [locator_candidate_id],
            "candidate_accepted",
        )
    )

    for candidate_page, page in zip(
        candidates["candidate_page_rows"], pages, strict=True
    ):
        candidate_id = candidate_page["candidate_page_id"]
        dispositions.append(
            _candidate_disposition_row(
                "page",
                candidate_id,
                "accepted",
                [page["questionnaire_page_id"]],
            )
        )
        output_adjudications.append(
            _output_adjudication_row(
                "page",
                page["questionnaire_page_id"],
                [candidate_id],
                "candidate_accepted",
            )
        )

    (
        candidate_occurrence_outputs,
        output_occurrence_candidates,
        occurrence_candidate_disposition,
    ) = _match_candidate_occurrences(
        candidates["candidate_occurrence_rows"], occurrences
    )
    for candidate in candidates["candidate_occurrence_rows"]:
        candidate_id = candidate["candidate_occurrence_id"]
        disposition = occurrence_candidate_disposition[candidate_id]
        output_ids = candidate_occurrence_outputs[candidate_id]
        dispositions.append(
            _candidate_disposition_row(
                "occurrence", candidate_id, disposition, output_ids
            )
        )
        if disposition == "rejected":
            notes.append(
                _note_row(
                    "occurrence",
                    candidate_id,
                    "semantic_false_positive_after_whole_page_review",
                    (
                        f"Page {candidate['page_number']} source review rejected "
                        f"the {candidate['occurrence_kind_candidate']} candidate; "
                        "the exact slice does not express that document-local "
                        "section-19 occurrence kind."
                    ),
                )
            )
        elif disposition in {"modified", "split"}:
            notes.append(
                _note_row(
                    "occurrence",
                    candidate_id,
                    "source_occurrence_corrected_after_whole_page_review",
                    (
                        f"Page {candidate['page_number']} source review replaced "
                        f"or semantically split candidate span "
                        f"{candidate['utf8_byte_start']}:"
                        f"{candidate['utf8_byte_end']} into {len(output_ids)} "
                        "independently verified stage-2 occurrence row(s)."
                    ),
                )
            )
    for occurrence in occurrences:
        output_id = occurrence["questionnaire_occurrence_id"]
        candidate_ids = output_occurrence_candidates.get(output_id, [])
        if not candidate_ids:
            action = "manual_add"
        else:
            dispositions_for_output = {
                occurrence_candidate_disposition[candidate_id]
                for candidate_id in candidate_ids
            }
            if dispositions_for_output == {"accepted"}:
                action = "candidate_accepted"
            elif "split" in dispositions_for_output:
                action = "candidate_split"
            else:
                action = "candidate_modified"
        output_adjudications.append(
            _output_adjudication_row(
                "occurrence", output_id, candidate_ids, action
            )
        )

    branches_by_source_occurrence_id = {
        row["source_occurrence_id"]: row for row in branches
    }
    candidate_branch_source = {
        row["candidate_branch_id"]: row["source_candidate_occurrence_id"]
        for row in candidates["candidate_flow_path_rows"]
    }
    flow_candidates_by_source: dict[str, list[Mapping[str, Any]]] = (
        defaultdict(list)
    )
    for row in candidates["candidate_flow_path_rows"]:
        flow_candidates_by_source[
            row["source_candidate_occurrence_id"]
        ].append(row)
    flow_candidate_order = {
        row["candidate_flow_path_id"]: position
        for position, row in enumerate(candidates["candidate_flow_path_rows"])
    }
    flow_candidate_to_branches: dict[str, list[str]] = defaultdict(list)
    # Overlapping occurrence candidates can project distinct flow candidates
    # onto the same retained branch, so provenance is many-to-many here.
    flow_branch_to_candidates: dict[str, list[str]] = defaultdict(list)
    flow_assignment_is_exact: dict[tuple[str, str], bool] = {}
    for (
        candidate_occurrence_id,
        flow_candidates,
    ) in flow_candidates_by_source.items():
        output_occurrence_ids = candidate_occurrence_outputs.get(
            candidate_occurrence_id, []
        )
        output_branches = [
            branches_by_source_occurrence_id[output_id]
            for output_id in output_occurrence_ids
            if output_id in branches_by_source_occurrence_id
        ]
        for candidate in flow_candidates:
            translated_parent_ids = (
                _translated_candidate_parent_occurrence_ids(
                    candidate,
                    candidate_branch_source,
                    candidate_occurrence_outputs,
                    branches_by_source_occurrence_id,
                )
            )
            candidate_is_root = candidate["candidate_parent_path"] == [
                stage1_candidates.FLOW_ROOT_ID
            ]
            matching = [
                branch["flow_branch_id"]
                for branch in output_branches
                if (
                    candidate_is_root
                    and not branch["parent_source_occurrence_ids"]
                    or not candidate_is_root
                    and any(
                        parent_id in branch["parent_source_occurrence_ids"]
                        for parent_id in translated_parent_ids
                    )
                )
            ]
            candidate_id = candidate["candidate_flow_path_id"]
            for branch_id in matching:
                flow_candidate_to_branches[candidate_id].append(branch_id)
                flow_branch_to_candidates[branch_id].append(candidate_id)
                branch = next(
                    row
                    for row in output_branches
                    if row["flow_branch_id"] == branch_id
                )
                flow_assignment_is_exact[(candidate_id, branch_id)] = (
                    candidate_is_root
                    and not branch["parent_source_occurrence_ids"]
                    or not candidate_is_root
                    and translated_parent_ids
                    == branch["parent_source_occurrence_ids"]
                )

        # If none of the machine parent alternatives reproduces a retained
        # label's complete local edge set, attach that label to its one
        # root-fallback candidate as a modified candidate. This preserves the
        # candidate source edge without pretending its proposed ancestry was
        # accepted.
        claimed_branch_ids = {
            branch_id
            for candidate in flow_candidates
            for branch_id in flow_candidate_to_branches[
                candidate["candidate_flow_path_id"]
            ]
        }
        fallback = next(
            (
                candidate
                for candidate in flow_candidates
                if candidate["basis_rule_id"] == "root_fallback_v1"
                and not flow_candidate_to_branches[
                    candidate["candidate_flow_path_id"]
                ]
            ),
            None,
        )
        if fallback is not None:
            candidate_id = fallback["candidate_flow_path_id"]
            for branch in output_branches:
                branch_id = branch["flow_branch_id"]
                if branch_id in claimed_branch_ids:
                    continue
                flow_candidate_to_branches[candidate_id].append(branch_id)
                flow_branch_to_candidates[branch_id].append(candidate_id)
                flow_assignment_is_exact[(candidate_id, branch_id)] = False

    flow_candidate_disposition: dict[str, str] = {}
    for candidate in candidates["candidate_flow_path_rows"]:
        candidate_id = candidate["candidate_flow_path_id"]
        output_ids = flow_candidate_to_branches[candidate_id]
        if len(output_ids) > 1:
            disposition = "split"
        elif len(output_ids) == 1:
            source_disposition = occurrence_candidate_disposition.get(
                candidate["source_candidate_occurrence_id"]
            )
            disposition = (
                "accepted"
                if flow_assignment_is_exact[(candidate_id, output_ids[0])]
                and source_disposition == "accepted"
                else "modified"
            )
        else:
            disposition = "rejected"
        flow_candidate_disposition[candidate_id] = disposition
        dispositions.append(
            _candidate_disposition_row(
                "flow_path", candidate_id, disposition, output_ids
            )
        )
        if disposition == "rejected":
            notes.append(
                _note_row(
                    "flow_path",
                    candidate_id,
                    "candidate_edge_not_selected_by_source_ancestry",
                    "The complete source review rejected this candidate parent edge or its source label.",
                )
            )
        elif disposition in {"modified", "split"}:
            notes.append(
                _note_row(
                    "flow_path",
                    candidate_id,
                    "candidate_edge_corrected_to_resolved_stage2_ancestry",
                    "The source label was retained with independently resolved direct-parent stage-2 ancestry.",
                )
            )
    for branch in branches:
        branch_id = branch["flow_branch_id"]
        candidate_ids = flow_branch_to_candidates.get(branch_id, [])
        candidate_ids.sort(key=flow_candidate_order.__getitem__)
        if not candidate_ids:
            action = "manual_add"
        else:
            dispositions_for_output = {
                flow_candidate_disposition[candidate_id]
                for candidate_id in candidate_ids
            }
            if dispositions_for_output == {"accepted"}:
                action = "candidate_accepted"
            elif "split" in dispositions_for_output:
                action = "candidate_split"
            else:
                action = "candidate_modified"
        output_adjudications.append(
            _output_adjudication_row(
                "flow_branch", branch_id, candidate_ids, action
            )
        )

    local_anchor_by_occurrence = {
        row["source_occurrence_id"]: row for row in local_anchors
    }
    anchor_candidate_disposition: dict[str, str] = {}
    output_anchor_candidates: dict[str, list[str]] = defaultdict(list)
    for candidate in candidates["candidate_anchor_classification_rows"]:
        candidate_id = candidate["candidate_anchor_classification_id"]
        occurrence_output_ids = candidate_occurrence_outputs.get(
            candidate["source_candidate_occurrence_id"], []
        )
        output_rows = [
            local_anchor_by_occurrence[output_id]
            for output_id in occurrence_output_ids
            if output_id in local_anchor_by_occurrence
        ]
        if not output_rows:
            disposition = "rejected"
            output_ids: list[str] = []
        else:
            mapped_parent_ids: list[str] = []
            for parent_candidate_id in candidate[
                "parent_anchor_candidate_ids"
            ]:
                mapped_parent_ids.extend(
                    candidate_occurrence_outputs.get(parent_candidate_id, [])
                )
            output_ids = [
                output["local_anchor_classification_id"]
                for output in output_rows
            ]
            if len(output_rows) > 1:
                disposition = "split"
            else:
                output = output_rows[0]
                exact = (
                    candidate["node_domain_candidate"] == output["node_domain"]
                    and candidate["classification_candidate"]
                    == output["classification"]
                    and candidate["printed_identifier_candidate"]
                    == output["printed_identifier"]
                    and candidate["exact_label_sha256"]
                    == output["exact_label_sha256"]
                    and mapped_parent_ids
                    == output["parent_source_occurrence_ids"]
                )
                disposition = "accepted" if exact else "modified"
            for output_id in output_ids:
                output_anchor_candidates[output_id].append(candidate_id)
        anchor_candidate_disposition[candidate_id] = disposition
        dispositions.append(
            _candidate_disposition_row(
                "anchor_classification", candidate_id, disposition, output_ids
            )
        )
        if disposition == "rejected":
            notes.append(
                _note_row(
                    "anchor_classification",
                    candidate_id,
                    "anchor_candidate_rejected_with_source_occurrence",
                    "The candidate anchor classification has no retained source-local anchor occurrence.",
                )
            )
        elif disposition in {"modified", "split"}:
            notes.append(
                _note_row(
                    "anchor_classification",
                    candidate_id,
                    "anchor_classification_corrected_from_source_context",
                    "The source-local classification, printed identifier, or parent evidence differs from the machine candidate.",
                )
            )
    for anchor in local_anchors:
        output_id = anchor["local_anchor_classification_id"]
        candidate_ids = output_anchor_candidates.get(output_id, [])
        if not candidate_ids:
            action = "manual_add"
        elif any(
            anchor_candidate_disposition[candidate_id] == "split"
            for candidate_id in candidate_ids
        ):
            action = "candidate_split"
        elif all(
            anchor_candidate_disposition[candidate_id] == "accepted"
            for candidate_id in candidate_ids
        ):
            action = "candidate_accepted"
        else:
            action = "candidate_modified"
        output_adjudications.append(
            _output_adjudication_row(
                "local_anchor_classification",
                output_id,
                candidate_ids,
                action,
            )
        )

    for repeat in local_repeats:
        output_adjudications.append(
            _output_adjudication_row(
                "local_repeat_alias_evidence",
                repeat["local_repeat_alias_evidence_id"],
                [],
                "manual_add",
            )
        )

    return dispositions, output_adjudications, notes


def _identity_from_path(
    path: Path, value: Mapping[str, Any]
) -> dict[str, Any]:
    raw = path.read_bytes()
    return {
        "path": str(path.relative_to(ROOT)),
        "schema_version": value["schema_version"],
        "byte_size": len(raw),
        "raw_sha256": _sha256(raw),
        "content_sha256": value["integrity"]["content_sha256"],
    }


def _seal(
    locator: Mapping[str, Any],
    pages: Sequence[Mapping[str, Any]],
    occurrences: Sequence[Mapping[str, Any]],
    branches: Sequence[Mapping[str, Any]],
    local_anchors: Sequence[Mapping[str, Any]],
    local_repeats: Sequence[Mapping[str, Any]],
    dispositions: Sequence[Mapping[str, Any]],
    output_adjudications: Sequence[Mapping[str, Any]],
    notes: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    kind_counts = Counter(row["occurrence_kind"] for row in occurrences)
    candidate_census: dict[str, dict[str, int]] = {}
    for row_kind in CANDIDATE_ROW_KINDS:
        counts = Counter(
            row["disposition"]
            for row in dispositions
            if row["candidate_row_kind"] == row_kind
        )
        candidate_census[row_kind] = {
            disposition: counts[disposition]
            for disposition in ("accepted", "modified", "split", "rejected")
        }
    output_census: dict[str, dict[str, int]] = {}
    for row_kind in STAGE2_ROW_KINDS:
        counts = Counter(
            row["adjudication_action"]
            for row in output_adjudications
            if row["stage2_row_kind"] == row_kind
        )
        output_census[row_kind] = {
            action: counts[action]
            for action in (
                "candidate_accepted",
                "candidate_modified",
                "candidate_split",
                "manual_add",
            )
        }
    return {
        "whole_document_locator_count": 1,
        "whole_document_locator_domain_sha256": _canonical_digest([locator]),
        "questionnaire_page_count": len(pages),
        "questionnaire_page_keyset_sha256": _canonical_digest(
            [row["questionnaire_page_id"] for row in pages]
        ),
        "questionnaire_page_domain_sha256": _canonical_digest(list(pages)),
        "empty_occurrence_page_count": sum(
            not row["questionnaire_occurrence_ids"] for row in pages
        ),
        "questionnaire_occurrence_count": len(occurrences),
        "questionnaire_occurrence_counts_by_kind": {
            kind: kind_counts[kind] for kind in OCCURRENCE_KINDS
        },
        "questionnaire_occurrence_keyset_sha256": _canonical_digest(
            [row["questionnaire_occurrence_id"] for row in occurrences]
        ),
        "questionnaire_occurrence_domain_sha256": _canonical_digest(
            list(occurrences)
        ),
        "flow_branch_count": len(branches),
        "flow_branch_domain_sha256": _canonical_digest(list(branches)),
        "flow_parent_representation": (
            "direct_parent_occurrence_ids_no_path_products"
        ),
        "flow_edge_order": "logical_dag_may_reference_later_extracted_labels",
        "serialized_path_product_count": 0,
        "local_anchor_classification_count": len(local_anchors),
        "local_anchor_classification_domain_sha256": _canonical_digest(
            list(local_anchors)
        ),
        "local_repeat_alias_evidence_count": len(local_repeats),
        "local_repeat_alias_evidence_domain_sha256": _canonical_digest(
            list(local_repeats)
        ),
        "candidate_disposition_count": len(dispositions),
        "candidate_disposition_domain_sha256": _canonical_digest(
            list(dispositions)
        ),
        "candidate_adjudication_census_by_kind": candidate_census,
        "output_adjudication_count": len(output_adjudications),
        "output_adjudication_domain_sha256": _canonical_digest(
            list(output_adjudications)
        ),
        "output_adjudication_census_by_kind": output_census,
        "adjudication_note_count": len(notes),
        "adjudication_note_domain_sha256": _canonical_digest(list(notes)),
        "page_review_count": len(pages),
        "whole_document_review_complete": True,
        "candidate_domain_exact_cover": True,
        "output_domain_exact_cover": True,
        "global_ids_assigned": False,
        "authority_status": "nonauthority",
    }


def build_annotation(
    replay: Mapping[str, Any],
    index: Mapping[str, Any],
    document: Mapping[str, Any],
    candidate_identity: Mapping[str, Any],
    page_texts: Sequence[str],
    review: Mapping[str, Any],
    candidates: Mapping[str, Any],
) -> dict[str, Any]:
    locator = _locator(document)
    (
        occurrences,
        branches,
        occurrence_ids_by_review_id,
        _branch_ids_by_review_id,
    ) = _build_occurrences_and_branches(
        document, page_texts, review, locator["locator_id"]
    )
    pages = _page_rows(
        document, page_texts, locator["locator_id"], occurrences
    )
    local_anchors = _local_anchor_rows(
        review, occurrences, occurrence_ids_by_review_id
    )
    local_repeats = _local_repeat_rows(review, occurrence_ids_by_review_id)
    dispositions, output_adjudications, notes = _adjudicate(
        candidates,
        locator,
        pages,
        occurrences,
        branches,
        local_anchors,
        local_repeats,
    )
    seal = _seal(
        locator,
        pages,
        occurrences,
        branches,
        local_anchors,
        local_repeats,
        dispositions,
        output_adjudications,
        notes,
    )
    candidate_artifact_identity = {
        "path": candidate_identity["path"],
        "schema_version": candidates["schema_version"],
        "byte_size": candidate_identity["byte_size"],
        "raw_sha256": candidate_identity["raw_sha256"],
        "content_sha256": candidate_identity["content_sha256"],
        "candidate_payload_sha256": candidate_identity[
            "candidate_payload_sha256"
        ],
    }
    review_identity = _identity_from_path(REVIEW_PATH, review)
    artifact_id = "rq-stage2-document-annotation:" + _canonical_digest(
        [
            document["source_document_id"],
            DOCUMENT_SOURCE_POSITION,
            review_identity["content_sha256"],
        ]
    )
    value: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": artifact_id,
        "authority_kind": AUTHORITY_KIND,
        "source_replay_identity": stage1_candidates.source_replay_identity(),
        "candidate_index_identity": {
            "path": str(stage1_candidates.INDEX_PATH.relative_to(ROOT)),
            "schema_version": index["schema_version"],
            "byte_size": stage1_candidates.INDEX_PATH.stat().st_size,
            "raw_sha256": _sha256(stage1_candidates.INDEX_PATH.read_bytes()),
            "content_sha256": index["integrity"]["content_sha256"],
        },
        "candidate_artifact_identity": candidate_artifact_identity,
        "source_review_identity": review_identity,
        "document_source_position": DOCUMENT_SOURCE_POSITION,
        "document_source_row": copy.deepcopy(document),
        "whole_document_locator": locator,
        "questionnaire_page_rows": pages,
        "questionnaire_occurrence_rows": occurrences,
        "flow_branch_rows": branches,
        "local_anchor_classification_rows": local_anchors,
        "local_repeat_alias_evidence_rows": local_repeats,
        "candidate_disposition_rows": dispositions,
        "adjudication_note_rows": notes,
        "output_adjudication_rows": output_adjudications,
        "seal": seal,
        "nonauthority_statement": {
            "status": "nonauthority",
            "one_document_only": True,
            "q5_emitted": False,
            "era_seal_emitted": False,
            "global_catalog_emitted": False,
            "global_alias_resolution_emitted": False,
            "r_q_emitted": False,
            "hierarchy_emitted": False,
            "slot_or_inventory_emitted": False,
            "legal_registry_read": False,
        },
        "integrity": {
            "canonicalization": CANONICALIZATION,
            "content_sha256": "0" * 64,
        },
        "status": STATUS,
    }
    value["integrity"]["content_sha256"] = _content_sha256(value)
    validate_annotation(
        value,
        replay,
        index,
        document,
        candidate_identity,
        page_texts,
        review,
        candidates,
    )
    return value


def _all_output_rows(
    value: Mapping[str, Any],
) -> list[tuple[str, Mapping[str, Any]]]:
    return [
        ("whole_document_locator", value["whole_document_locator"]),
        *[("page", row) for row in value["questionnaire_page_rows"]],
        *[
            ("occurrence", row)
            for row in value["questionnaire_occurrence_rows"]
        ],
        *[("flow_branch", row) for row in value["flow_branch_rows"]],
        *[
            ("local_anchor_classification", row)
            for row in value["local_anchor_classification_rows"]
        ],
        *[
            ("local_repeat_alias_evidence", row)
            for row in value["local_repeat_alias_evidence_rows"]
        ],
    ]


def _validate_adjudication_relations(
    value: Mapping[str, Any], candidates: Mapping[str, Any]
) -> None:
    candidate_rows = [
        (
            "whole_document_locator",
            candidates["whole_document_locator_candidate"],
        ),
        *[("page", row) for row in candidates["candidate_page_rows"]],
        *[
            ("occurrence", row)
            for row in candidates["candidate_occurrence_rows"]
        ],
        *[
            ("flow_path", row)
            for row in candidates["candidate_flow_path_rows"]
        ],
        *[
            ("anchor_classification", row)
            for row in candidates["candidate_anchor_classification_rows"]
        ],
    ]
    expected_candidate_domain = [
        (row_kind, _candidate_id(row_kind, row))
        for row_kind, row in candidate_rows
    ]
    dispositions = value["candidate_disposition_rows"]
    if len(dispositions) != len(expected_candidate_domain):
        raise ValueError("candidate disposition count drift")
    disposition_by_key: dict[tuple[str, str], Mapping[str, Any]] = {}
    for expected_key, row in zip(
        expected_candidate_domain, dispositions, strict=True
    ):
        _expect_keys(row, CANDIDATE_DISPOSITION_KEYS, "candidate disposition")
        key = (row["candidate_row_kind"], row["candidate_id"])
        if (
            key != expected_key
            or key in disposition_by_key
            or row["candidate_row_kind"] not in CANDIDATE_ROW_KINDS
            or row["disposition"]
            not in {"accepted", "modified", "split", "rejected"}
            or row["adjudication_status"] != "complete"
        ):
            raise ValueError("candidate disposition domain drift")
        output_count = len(row["stage2_row_ids"])
        if (
            row["disposition"] in {"accepted", "modified"}
            and output_count != 1
            or row["disposition"] == "split"
            and output_count < 2
            or row["disposition"] == "rejected"
            and output_count != 0
        ):
            raise ValueError("candidate disposition cardinality drift")
        disposition_by_key[key] = row

    expected_output_domain = [
        (row_kind, _stage2_id(row_kind, row))
        for row_kind, row in _all_output_rows(value)
    ]
    output_adjudications = value["output_adjudication_rows"]
    if len(output_adjudications) != len(expected_output_domain):
        raise ValueError("output adjudication count drift")
    output_by_key: dict[tuple[str, str], Mapping[str, Any]] = {}
    for expected_key, row in zip(
        expected_output_domain, output_adjudications, strict=True
    ):
        _expect_keys(row, OUTPUT_ADJUDICATION_KEYS, "output adjudication")
        key = (row["stage2_row_kind"], row["stage2_row_id"])
        if (
            key != expected_key
            or key in output_by_key
            or row["stage2_row_kind"] not in STAGE2_ROW_KINDS
            or row["adjudication_action"]
            not in {
                "candidate_accepted",
                "candidate_modified",
                "candidate_split",
                "manual_add",
            }
            or row["whole_page_review_complete"] is not True
            or row["source_span_verified"] is not True
            or row["adjudication_status"] != "complete"
            or row["adjudication_action"] == "manual_add"
            and row["source_candidate_ids"]
            or row["adjudication_action"] != "manual_add"
            and not row["source_candidate_ids"]
        ):
            raise ValueError("output adjudication domain drift")
        output_by_key[key] = row

    output_id_to_key = {
        stage2_id: (row_kind, stage2_id)
        for row_kind, stage2_id in expected_output_domain
    }
    candidate_id_to_key = {
        candidate_id: (row_kind, candidate_id)
        for row_kind, candidate_id in expected_candidate_domain
    }
    for key, disposition in disposition_by_key.items():
        for output_id in disposition["stage2_row_ids"]:
            output_key = output_id_to_key.get(output_id)
            if output_key is None:
                raise ValueError("candidate disposition output unresolved")
            output = output_by_key[output_key]
            if key[1] not in output["source_candidate_ids"]:
                raise ValueError(
                    "candidate/output adjudication reverse edge missing"
                )
    for output_key, output in output_by_key.items():
        for candidate_id in output["source_candidate_ids"]:
            candidate_key = candidate_id_to_key.get(candidate_id)
            if candidate_key is None:
                raise ValueError("output adjudication candidate unresolved")
            if (
                output_key[1]
                not in disposition_by_key[candidate_key]["stage2_row_ids"]
            ):
                raise ValueError(
                    "output/candidate adjudication reverse edge missing"
                )

    # Reconstruct the occurrence candidate projection independently of the
    # adjudication helper. Each output names every intersecting same-kind
    # candidate in committed input order; merged and split spans therefore
    # cannot silently lose provenance while still satisfying reverse edges.
    occurrence_outputs = value["questionnaire_occurrence_rows"]
    exact_outputs: dict[tuple[Any, ...], list[Mapping[str, Any]]] = (
        defaultdict(list)
    )
    page_kind_outputs: dict[tuple[int, str], list[Mapping[str, Any]]] = (
        defaultdict(list)
    )
    for output in occurrence_outputs:
        exact_outputs[
            (
                output["page_number"],
                output["utf8_byte_start"],
                output["utf8_byte_end"],
                output["occurrence_kind"],
            )
        ].append(output)
        page_kind_outputs[
            (output["page_number"], output["occurrence_kind"])
        ].append(output)

    expected_output_candidates: dict[str, list[str]] = defaultdict(list)
    expected_occurrence_dispositions: dict[str, str] = {}
    for candidate in candidates["candidate_occurrence_rows"]:
        candidate_id = candidate["candidate_occurrence_id"]
        coordinate = (
            candidate["page_number"],
            candidate["utf8_byte_start"],
            candidate["utf8_byte_end"],
            candidate["occurrence_kind_candidate"],
        )
        matches = list(exact_outputs.get(coordinate, []))
        exact = bool(matches)
        if not matches:
            matches = [
                output
                for output in page_kind_outputs.get(
                    (
                        candidate["page_number"],
                        candidate["occurrence_kind_candidate"],
                    ),
                    [],
                )
                if output["utf8_byte_start"] < candidate["utf8_byte_end"]
                and candidate["utf8_byte_start"] < output["utf8_byte_end"]
            ]
        output_ids = [
            output["questionnaire_occurrence_id"] for output in matches
        ]
        if not output_ids:
            expected_disposition = "rejected"
        elif exact and len(output_ids) == 1:
            expected_disposition = "accepted"
        elif len(output_ids) > 1:
            expected_disposition = "split"
        else:
            expected_disposition = "modified"
        expected_occurrence_dispositions[candidate_id] = expected_disposition
        actual = disposition_by_key[("occurrence", candidate_id)]
        if (
            actual["disposition"] != expected_disposition
            or actual["stage2_row_ids"] != output_ids
        ):
            raise ValueError(
                "occurrence candidate projection incomplete or out of order"
            )
        for output_id in output_ids:
            expected_output_candidates[output_id].append(candidate_id)

    for output in occurrence_outputs:
        output_id = output["questionnaire_occurrence_id"]
        candidate_ids = expected_output_candidates.get(output_id, [])
        actual = output_by_key[("occurrence", output_id)]
        expected_action = (
            "manual_add"
            if not candidate_ids
            else (
                "candidate_split"
                if any(
                    expected_occurrence_dispositions[candidate_id] == "split"
                    for candidate_id in candidate_ids
                )
                else (
                    "candidate_accepted"
                    if all(
                        expected_occurrence_dispositions[candidate_id]
                        == "accepted"
                        for candidate_id in candidate_ids
                    )
                    else "candidate_modified"
                )
            )
        )
        if (
            actual["source_candidate_ids"] != candidate_ids
            or actual["adjudication_action"] != expected_action
        ):
            raise ValueError(
                "occurrence output candidate projection incomplete or out of order"
            )

    nonaccepted_keys = [
        key
        for key, row in disposition_by_key.items()
        if row["disposition"] != "accepted"
    ]
    notes = value["adjudication_note_rows"]
    if len(notes) != len(nonaccepted_keys):
        raise ValueError("adjudication note count drift")
    for expected_key, row in zip(nonaccepted_keys, notes, strict=True):
        _expect_keys(row, NOTE_KEYS, "adjudication note")
        if (
            (row["candidate_row_kind"], row["candidate_id"]) != expected_key
            or not row["note_code"]
            or not row["note"]
        ):
            raise ValueError("adjudication note domain drift")


def _topologically_order_branches(
    branches: Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    branch_by_id: dict[str, Mapping[str, Any]] = {}
    source_position: dict[str, int] = {}
    for position, branch in enumerate(branches):
        branch_id = branch["flow_branch_id"]
        if branch_id in branch_by_id:
            raise ValueError("duplicate flow branch ID")
        branch_by_id[branch_id] = branch
        source_position[branch_id] = position

    children: dict[str, list[str]] = defaultdict(list)
    indegree: dict[str, int] = {}
    for branch_id, branch in branch_by_id.items():
        parent_ids = branch["parent_flow_branch_ids"]
        if (
            not isinstance(parent_ids, list)
            or not parent_ids
            or len(parent_ids) != len(set(parent_ids))
            or FLOW_ROOT in parent_ids
            and parent_ids != [FLOW_ROOT]
            or any(
                parent_id != FLOW_ROOT and parent_id not in branch_by_id
                for parent_id in parent_ids
            )
        ):
            raise ValueError("flow branch parent domain drift")
        nonroot_parents = [
            parent_id for parent_id in parent_ids if parent_id != FLOW_ROOT
        ]
        indegree[branch_id] = len(nonroot_parents)
        for parent_id in nonroot_parents:
            children[parent_id].append(branch_id)

    ready = sorted(
        (branch_id for branch_id, degree in indegree.items() if degree == 0),
        key=source_position.__getitem__,
    )
    ordered_ids: list[str] = []
    while ready:
        branch_id = ready.pop(0)
        ordered_ids.append(branch_id)
        for child_id in children[branch_id]:
            indegree[child_id] -= 1
            if indegree[child_id] == 0:
                ready.append(child_id)
        ready.sort(key=source_position.__getitem__)
    if len(ordered_ids) != len(branches):
        raise ValueError("flow branch graph has a cycle")
    return [branch_by_id[branch_id] for branch_id in ordered_ids]


def _validate_flow_laws(value: Mapping[str, Any]) -> None:
    occurrences = value["questionnaire_occurrence_rows"]
    branches = value["flow_branch_rows"]
    occurrence_by_id = {
        row["questionnaire_occurrence_id"]: row for row in occurrences
    }
    branch_by_id: dict[str, Mapping[str, Any]] = {}
    branch_by_occurrence: dict[str, Mapping[str, Any]] = {}
    occurrence_position = {
        row["questionnaire_occurrence_id"]: position
        for position, row in enumerate(occurrences)
    }
    same_span_rows: dict[tuple[Any, ...], list[Mapping[str, Any]]] = (
        defaultdict(list)
    )
    for occurrence in occurrences:
        same_span_rows[
            (
                occurrence["source_document_id"],
                occurrence["page_number"],
                occurrence["utf8_byte_start"],
                occurrence["utf8_byte_end"],
                occurrence["occurrence_kind"],
            )
        ].append(occurrence)
    for same_span in same_span_rows.values():
        if (
            len(same_span) != 1
            or same_span[0]["semantic_ordinal_at_span"] != 0
        ):
            raise ValueError("local-edge occurrence atom or ordinal drift")

    last_branch_occurrence_position = -1
    for branch in branches:
        _expect_keys(branch, FLOW_BRANCH_KEYS, "flow branch")
        occurrence = occurrence_by_id.get(branch["source_occurrence_id"])
        if (
            occurrence is None
            or occurrence["occurrence_kind"] != "flow_branch_label"
            or branch["flow_branch_id"] in branch_by_id
            or branch["source_occurrence_id"] in branch_by_occurrence
            or branch["interview_wave"] != occurrence["interview_wave"]
            or branch["source_locator_id"] != occurrence["source_locator_id"]
            or branch["page_number"] != occurrence["page_number"]
            or branch["occurrence_index_on_page"]
            != occurrence["occurrence_index_on_page"]
            or branch["branch_label"] != occurrence["matched_text"]
            or branch["branch_label_sha256"]
            != occurrence["matched_utf8_sha256"]
            or occurrence_position[branch["source_occurrence_id"]]
            <= last_branch_occurrence_position
        ):
            raise ValueError("flow branch local ancestry or identity drift")
        last_branch_occurrence_position = occurrence_position[
            branch["source_occurrence_id"]
        ]
        branch_by_id[branch["flow_branch_id"]] = branch
        branch_by_occurrence[branch["source_occurrence_id"]] = branch
    flow_label_ids = {
        row["questionnaire_occurrence_id"]
        for row in occurrences
        if row["occurrence_kind"] == "flow_branch_label"
    }
    if set(branch_by_occurrence) != flow_label_ids:
        raise ValueError("flow label/branch one-to-one cover drift")
    for branch in branches:
        occurrence = occurrence_by_id[branch["source_occurrence_id"]]
        parent_occurrence_ids = branch["parent_source_occurrence_ids"]
        expected_parent_branch_ids = (
            [FLOW_ROOT]
            if not parent_occurrence_ids
            else [
                branch_by_occurrence[parent_id]["flow_branch_id"]
                for parent_id in parent_occurrence_ids
                if parent_id in branch_by_occurrence
            ]
        )
        expected_id = "questionnaire-flow:" + _canonical_digest(
            [
                branch["parent_flow_branch_ids"],
                branch["interview_wave"],
                branch["source_occurrence_id"],
            ]
        )
        if (
            branch["flow_branch_id"] != expected_id
            or parent_occurrence_ids
            != occurrence["parent_flow_occurrence_ids"]
            or len(parent_occurrence_ids) != len(set(parent_occurrence_ids))
            or branch["parent_flow_branch_ids"] != expected_parent_branch_ids
            or any(
                parent_id not in branch_by_occurrence
                for parent_id in parent_occurrence_ids
            )
        ):
            raise ValueError("flow branch local ancestry or identity drift")
    _topologically_order_branches(branches)
    for occurrence in occurrences:
        parents = occurrence["parent_flow_occurrence_ids"]
        if (
            not isinstance(parents, list)
            or len(parents) != len(set(parents))
            or any(
                FORBIDDEN_PARENT_PATH_MARKER in parent for parent in parents
            )
            or any(parent not in branch_by_occurrence for parent in parents)
            or parents != sorted(parents, key=occurrence_position.__getitem__)
        ):
            raise ValueError("occurrence local parent-edge drift")


def _branch_compatible(
    occurrences: Sequence[Mapping[str, Any]],
    branches: Sequence[Mapping[str, Any]],
) -> bool:
    """Return existential single-path compatibility from the local flow DAG."""

    if (
        not occurrences
        or len({row["interview_wave"] for row in occurrences}) != 1
    ):
        return False
    branch_id_by_occurrence = {
        branch["source_occurrence_id"]: branch["flow_branch_id"]
        for branch in branches
    }
    bits_at_branch: dict[str, int] = defaultdict(int)
    for bit_index, occurrence in enumerate(occurrences):
        parent_occurrence_ids = occurrence["parent_flow_occurrence_ids"]
        allowed_branch_ids = (
            [FLOW_ROOT]
            if not parent_occurrence_ids
            else [
                branch_id_by_occurrence[parent_id]
                for parent_id in parent_occurrence_ids
            ]
        )
        for branch_id in allowed_branch_ids:
            bits_at_branch[branch_id] |= 1 << bit_index

    # Each mask represents one realizable route prefix. Incoming alternatives
    # contribute separate masks: never union masks from mutually exclusive
    # parents at a merge. Inclusion-maximal masks are sufficient because any
    # future suffix available to a subset is also available to its superset.
    full_mask = (1 << len(occurrences)) - 1
    masks_by_branch: dict[str, frozenset[int]] = {
        FLOW_ROOT: frozenset({bits_at_branch[FLOW_ROOT]})
    }
    if full_mask in masks_by_branch[FLOW_ROOT]:
        return True
    for branch in _topologically_order_branches(branches):
        branch_id = branch["flow_branch_id"]
        parent_ids = branch["parent_flow_branch_ids"]
        if branch_id in masks_by_branch or any(
            parent_id not in masks_by_branch for parent_id in parent_ids
        ):
            raise ValueError("flow branch is duplicate, unresolved, or later")
        candidate_masks = {
            parent_mask | bits_at_branch[branch_id]
            for parent_id in parent_ids
            for parent_mask in masks_by_branch[parent_id]
        }
        maximal_masks = frozenset(
            candidate
            for candidate in candidate_masks
            if not any(
                candidate != other and candidate | other == other
                for other in candidate_masks
            )
        )
        masks_by_branch[branch_id] = maximal_masks
        if full_mask in maximal_masks:
            return True
    return False


def _validate_compatibility_predicate() -> None:
    left_occurrence = "occurrence:left"
    right_occurrence = "occurrence:right"
    left_child_occurrence = "occurrence:left-child"
    merge_occurrence = "occurrence:merge"
    branches = [
        {
            # Deliberately source-earlier than its logical parents: doc60's
            # interleaved B3/D3 diagrams require lawful forward references.
            "flow_branch_id": "questionnaire-flow:merge",
            "parent_flow_branch_ids": [
                "questionnaire-flow:left",
                "questionnaire-flow:right",
            ],
            "source_occurrence_id": merge_occurrence,
        },
        {
            "flow_branch_id": "questionnaire-flow:left",
            "parent_flow_branch_ids": [FLOW_ROOT],
            "source_occurrence_id": left_occurrence,
        },
        {
            "flow_branch_id": "questionnaire-flow:right",
            "parent_flow_branch_ids": [FLOW_ROOT],
            "source_occurrence_id": right_occurrence,
        },
        {
            "flow_branch_id": "questionnaire-flow:left-child",
            "parent_flow_branch_ids": ["questionnaire-flow:left"],
            "source_occurrence_id": left_child_occurrence,
        },
    ]
    root_row = {"interview_wave": 1994, "parent_flow_occurrence_ids": []}
    left_or_right = {
        "interview_wave": 1994,
        "parent_flow_occurrence_ids": [left_occurrence, right_occurrence],
    }
    left_row = {
        "interview_wave": 1994,
        "parent_flow_occurrence_ids": [left_occurrence],
    }
    right_row = {
        "interview_wave": 1994,
        "parent_flow_occurrence_ids": [right_occurrence],
    }
    merge_row = {
        "interview_wave": 1994,
        "parent_flow_occurrence_ids": [merge_occurrence],
    }
    other_wave = {
        "interview_wave": 1993,
        "parent_flow_occurrence_ids": [left_occurrence],
    }
    if (
        not _branch_compatible([root_row, left_row], branches)
        or not _branch_compatible([left_or_right, left_row], branches)
        or not _branch_compatible([left_row, merge_row], branches)
        or not _branch_compatible([right_row, merge_row], branches)
        or _branch_compatible([left_row, right_row], branches)
        or _branch_compatible([left_row, right_row, merge_row], branches)
        or _branch_compatible([left_row, other_wave], branches)
    ):
        raise ValueError("branch compatibility predicate drift")


def _validate_local_anchor_laws(value: Mapping[str, Any]) -> None:
    occurrence_by_id = {
        row["questionnaire_occurrence_id"]: row
        for row in value["questionnaire_occurrence_rows"]
    }
    component_kinds = {
        "remuneration_component_anchor",
        "context_anchor",
    }
    parent_kinds = {
        "job_anchor",
        "role_total_anchor",
        "farm_aggregate_anchor",
        "business_aggregate_anchor",
    }
    for anchor in value["local_anchor_classification_rows"]:
        source = occurrence_by_id.get(anchor["source_occurrence_id"])
        parents = [
            occurrence_by_id.get(parent_id)
            for parent_id in anchor["parent_source_occurrence_ids"]
        ]
        if (
            source is None
            or any(parent is None for parent in parents)
            or source["occurrence_kind"] not in ANCHOR_KINDS
            or source["occurrence_kind"] not in component_kinds
            and parents
            or any(
                parent["occurrence_kind"] not in parent_kinds
                for parent in parents
            )
            or parents
            and not _branch_compatible(
                [source, *parents],
                value["flow_branch_rows"],
            )
        ):
            raise ValueError("local anchor parent or path compatibility drift")


def _contains_witness_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            "witness" in key.casefold() or _contains_witness_key(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_witness_key(child) for child in value)
    return False


def _contains_forbidden_path_product(value: Any) -> bool:
    if isinstance(value, Mapping):
        forbidden_keys = {"branch_" + "path", "flow_branch_" + "paths"}
        return any(
            key in forbidden_keys or _contains_forbidden_path_product(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_forbidden_path_product(child) for child in value)
    return isinstance(value, str) and FORBIDDEN_PARENT_PATH_MARKER in value


def validate_annotation(
    value: Mapping[str, Any],
    replay: Mapping[str, Any],
    index: Mapping[str, Any],
    document: Mapping[str, Any],
    candidate_identity: Mapping[str, Any],
    page_texts: Sequence[str],
    review: Mapping[str, Any],
    candidates: Mapping[str, Any],
) -> None:
    expected_top_level = {
        "schema_version",
        "artifact_id",
        "authority_kind",
        "source_replay_identity",
        "candidate_index_identity",
        "candidate_artifact_identity",
        "source_review_identity",
        "document_source_position",
        "document_source_row",
        "whole_document_locator",
        "questionnaire_page_rows",
        "questionnaire_occurrence_rows",
        "flow_branch_rows",
        "local_anchor_classification_rows",
        "local_repeat_alias_evidence_rows",
        "candidate_disposition_rows",
        "adjudication_note_rows",
        "output_adjudication_rows",
        "seal",
        "nonauthority_statement",
        "integrity",
        "status",
    }
    _expect_keys(value, expected_top_level, "document annotation")
    if (
        value["schema_version"] != SCHEMA_VERSION
        or value["authority_kind"] != AUTHORITY_KIND
        or value["document_source_position"] != DOCUMENT_SOURCE_POSITION
        or value["document_source_row"] != document
        or value["source_replay_identity"]
        != stage1_candidates.source_replay_identity()
        or value["status"] != STATUS
        or value["integrity"]
        != {
            "canonicalization": CANONICALIZATION,
            "content_sha256": _content_sha256(value),
        }
        or value["nonauthority_statement"]
        != {
            "status": "nonauthority",
            "one_document_only": True,
            "q5_emitted": False,
            "era_seal_emitted": False,
            "global_catalog_emitted": False,
            "global_alias_resolution_emitted": False,
            "r_q_emitted": False,
            "hierarchy_emitted": False,
            "slot_or_inventory_emitted": False,
            "legal_registry_read": False,
        }
    ):
        raise ValueError("document annotation identity or nonauthority drift")

    locator = _locator(document)
    (
        occurrences,
        branches,
        occurrence_ids_by_review_id,
        _branch_ids_by_review_id,
    ) = _build_occurrences_and_branches(
        document, page_texts, review, locator["locator_id"]
    )
    pages = _page_rows(
        document, page_texts, locator["locator_id"], occurrences
    )
    local_anchors = _local_anchor_rows(
        review, occurrences, occurrence_ids_by_review_id
    )
    local_repeats = _local_repeat_rows(review, occurrence_ids_by_review_id)
    dispositions, output_adjudications, notes = _adjudicate(
        candidates,
        locator,
        pages,
        occurrences,
        branches,
        local_anchors,
        local_repeats,
    )
    expected_arrays = (
        ("whole_document_locator", locator),
        ("questionnaire_page_rows", pages),
        ("questionnaire_occurrence_rows", occurrences),
        ("flow_branch_rows", branches),
        ("local_anchor_classification_rows", local_anchors),
        ("local_repeat_alias_evidence_rows", local_repeats),
        ("candidate_disposition_rows", dispositions),
        ("adjudication_note_rows", notes),
        ("output_adjudication_rows", output_adjudications),
    )
    for key, expected in expected_arrays:
        if value[key] != expected:
            raise ValueError(f"document annotation {key} drift")
    expected_artifact_id = (
        "rq-stage2-document-annotation:"
        + _canonical_digest(
            [
                document["source_document_id"],
                DOCUMENT_SOURCE_POSITION,
                review["integrity"]["content_sha256"],
            ]
        )
    )
    expected_candidate_index_identity = {
        "path": str(stage1_candidates.INDEX_PATH.relative_to(ROOT)),
        "schema_version": index["schema_version"],
        "byte_size": stage1_candidates.INDEX_PATH.stat().st_size,
        "raw_sha256": _sha256(stage1_candidates.INDEX_PATH.read_bytes()),
        "content_sha256": index["integrity"]["content_sha256"],
    }
    expected_candidate_artifact_identity = {
        "path": candidate_identity["path"],
        "schema_version": candidates["schema_version"],
        "byte_size": candidate_identity["byte_size"],
        "raw_sha256": candidate_identity["raw_sha256"],
        "content_sha256": candidate_identity["content_sha256"],
        "candidate_payload_sha256": candidate_identity[
            "candidate_payload_sha256"
        ],
    }
    expected_review_identity = _identity_from_path(REVIEW_PATH, review)
    expected_seal = _seal(
        locator,
        pages,
        occurrences,
        branches,
        local_anchors,
        local_repeats,
        dispositions,
        output_adjudications,
        notes,
    )
    if (
        value["artifact_id"] != expected_artifact_id
        or value["candidate_index_identity"]
        != expected_candidate_index_identity
        or value["candidate_artifact_identity"]
        != expected_candidate_artifact_identity
        or value["source_review_identity"] != expected_review_identity
        or value["seal"] != expected_seal
    ):
        raise ValueError("document annotation artifact ID or seal drift")

    for row in value["questionnaire_page_rows"]:
        _expect_keys(row, PAGE_KEYS, "questionnaire page")
    for row in value["questionnaire_occurrence_rows"]:
        _expect_keys(row, OCCURRENCE_KEYS, "questionnaire occurrence")
    for row in value["flow_branch_rows"]:
        _expect_keys(row, FLOW_BRANCH_KEYS, "flow branch")
    for row in value["local_anchor_classification_rows"]:
        _expect_keys(row, LOCAL_ANCHOR_KEYS, "local anchor")
        if row["local_anchor_classification_id"].startswith(
            ("psid-job-slot:", "psid-component-slot:", "psid-node-alias:")
        ):
            raise ValueError("local anchor emitted a global ID")
    for row in value["local_repeat_alias_evidence_rows"]:
        _expect_keys(row, LOCAL_REPEAT_KEYS, "local repeat evidence")
        if row["relation"] not in ALIAS_RELATIONS:
            raise ValueError("local repeat inferred an alias relation")
    _validate_compatibility_predicate()
    _validate_flow_laws(value)
    _validate_local_anchor_laws(value)
    if _contains_witness_key(value):
        raise ValueError("compatibility witness was serialized")
    if _contains_forbidden_path_product(value):
        raise ValueError(
            "full path product or composite path ID was serialized"
        )
    _validate_adjudication_relations(value, candidates)


def _inputs() -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    list[str],
    dict[str, Any],
    dict[str, Any],
]:
    replay, index = _source_replay_and_index()
    document, candidate_identity = _document_identity(replay, index)
    page_texts = _extract_page_texts(document, replay)
    review = _load_review(document, page_texts)
    locator = _locator(document)
    (
        occurrences,
        branches,
        occurrence_ids_by_review_id,
        _branch_ids_by_review_id,
    ) = _build_occurrences_and_branches(
        document, page_texts, review, locator["locator_id"]
    )
    _page_rows(document, page_texts, locator["locator_id"], occurrences)
    local_anchors = _local_anchor_rows(
        review, occurrences, occurrence_ids_by_review_id
    )
    _local_repeat_rows(review, occurrence_ids_by_review_id)
    candidate_free_projection = {
        "questionnaire_occurrence_rows": occurrences,
        "flow_branch_rows": branches,
        "local_anchor_classification_rows": local_anchors,
    }
    _validate_flow_laws(candidate_free_projection)
    _validate_local_anchor_laws(candidate_free_projection)
    # Candidate bytes are intentionally not opened until the complete source
    # projection has validated against every page and every local relationship.
    candidates = _load_candidates(replay, candidate_identity, page_texts)
    return (
        replay,
        index,
        document,
        candidate_identity,
        page_texts,
        review,
        candidates,
    )


def _mutation_specs(value: Mapping[str, Any]) -> list[tuple[str, Any]]:
    mutations: list[tuple[str, Any]] = []

    def add(name: str, mutate: Any) -> None:
        mutations.append((name, mutate))

    def select_parent_edge_subset(row: dict[str, Any]) -> None:
        for occurrence in row["questionnaire_occurrence_rows"]:
            if len(occurrence["parent_flow_occurrence_ids"]) > 1:
                occurrence["parent_flow_occurrence_ids"] = occurrence[
                    "parent_flow_occurrence_ids"
                ][:-1]
                return
        raise ValueError("mutation fixture has no multi-parent occurrence")

    def set_mismatched_branch_parent(row: dict[str, Any]) -> None:
        first = row["flow_branch_rows"][0]
        later = row["flow_branch_rows"][-1]
        first["parent_source_occurrence_ids"] = [later["source_occurrence_id"]]
        first["parent_flow_branch_ids"] = [later["flow_branch_id"]]

    def set_cyclic_parent(row: dict[str, Any]) -> None:
        first = row["flow_branch_rows"][0]
        first["parent_source_occurrence_ids"] = [first["source_occurrence_id"]]
        first["parent_flow_branch_ids"] = [first["flow_branch_id"]]

    add("missing_page", lambda row: row["questionnaire_page_rows"].pop())
    add(
        "reordered_page",
        lambda row: row["questionnaire_page_rows"].__setitem__(
            slice(0, 2), list(reversed(row["questionnaire_page_rows"][:2]))
        ),
    )
    add(
        "bad_span",
        lambda row: row["questionnaire_occurrence_rows"][0].__setitem__(
            "utf8_byte_end",
            row["questionnaire_occurrence_rows"][0]["utf8_byte_end"] + 1,
        ),
    )
    add(
        "bad_hash",
        lambda row: row["questionnaire_occurrence_rows"][0].__setitem__(
            "matched_utf8_sha256", "0" * 64
        ),
    )
    add(
        "bad_id",
        lambda row: row["questionnaire_occurrence_rows"][0].__setitem__(
            "questionnaire_occurrence_id",
            "psid-questionnaire-occurrence:" + "0" * 64,
        ),
    )
    add(
        "illegal_ordinal",
        lambda row: row["questionnaire_occurrence_rows"][0].__setitem__(
            "semantic_ordinal_at_span", 1
        ),
    )
    add(
        "duplicate_atom",
        lambda row: row["questionnaire_occurrence_rows"].insert(
            1, copy.deepcopy(row["questionnaire_occurrence_rows"][0])
        ),
    )
    add(
        "reordered_occurrence_members",
        lambda row: row["questionnaire_occurrence_rows"].__setitem__(
            0,
            dict(
                reversed(list(row["questionnaire_occurrence_rows"][0].items()))
            ),
        ),
    )
    if value["flow_branch_rows"]:
        add(
            "unresolved_branch",
            lambda row: row["flow_branch_rows"][0].__setitem__(
                "parent_flow_branch_ids", ["questionnaire-flow:" + "f" * 64]
            ),
        )
        add("mismatched_branch_parent", set_mismatched_branch_parent)
        add("cyclic_branch", set_cyclic_parent)
        add("omitted_label", lambda row: row["flow_branch_rows"].pop())
        add(
            "duplicate_label",
            lambda row: row["flow_branch_rows"].append(
                copy.deepcopy(row["flow_branch_rows"][0])
            ),
        )
        add(
            "selected_parent_edge_subset",
            select_parent_edge_subset,
        )
    if value["local_repeat_alias_evidence_rows"]:
        add(
            "inferred_alias",
            lambda row: row["local_repeat_alias_evidence_rows"][0].__setitem__(
                "relation", "inferred_synonym"
            ),
        )
    add(
        "omitted_candidate_disposition",
        lambda row: row["candidate_disposition_rows"].pop(),
    )
    add(
        "unadjudicated_output",
        lambda row: row["output_adjudication_rows"][0].__setitem__(
            "adjudication_status", "pending"
        ),
    )
    return mutations


def run_mutation_tests(
    value: Mapping[str, Any],
    inputs: tuple[
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
        list[str],
        dict[str, Any],
        dict[str, Any],
    ],
) -> None:
    document = inputs[2]
    page_texts = inputs[4]
    review_mutation = copy.deepcopy(inputs[5])
    nested_spec: dict[str, Any] | None = None
    for source_spec in review_mutation["occurrence_specs"]:
        is_root_flow_label = (
            source_spec["occurrence_kind"] == "flow_branch_label"
            and source_spec["parent_review_occurrence_ids"] == []
        )
        if not is_root_flow_label:
            continue
        for nested_start in range(
            source_spec["utf8_byte_start"] + 1,
            source_spec["utf8_byte_end"],
        ):
            try:
                nested_bytes, _nested_text = _utf8_slice(
                    page_texts[source_spec["page_number"] - 1],
                    nested_start,
                    source_spec["utf8_byte_end"],
                )
            except ValueError:
                continue
            nested_spec = copy.deepcopy(source_spec)
            nested_spec["utf8_byte_start"] = nested_start
            nested_spec["review_occurrence_id"] = (
                "rq-review-occurrence:"
                + _canonical_digest(
                    [
                        document["source_document_id"],
                        nested_spec["page_number"],
                        nested_spec["utf8_byte_start"],
                        nested_spec["utf8_byte_end"],
                        nested_spec["occurrence_kind"],
                        _sha256(nested_bytes),
                    ]
                )
            )
            nested_spec["review_note"] = (
                "Mutation-only nested detector hit that must be rejected."
            )
            break
        if nested_spec is not None:
            break
    if nested_spec is None:
        raise ValueError("review-overlap mutation fixture is unavailable")
    review_mutation["occurrence_specs"].append(nested_spec)
    review_mutation["occurrence_specs"].sort(
        key=lambda row: (
            row["page_number"],
            row["utf8_byte_start"],
            row["utf8_byte_end"],
            KIND_ORDER[row["occurrence_kind"]],
            row["review_occurrence_id"],
        )
    )
    review_mutation["integrity"]["content_sha256"] = _content_sha256(
        review_mutation
    )
    try:
        validate_review(review_mutation, document, page_texts)
    except ValueError as error:
        if "partially overlapping same-kind atoms" not in str(error):
            raise ValueError(
                "review-overlap mutation failed for the wrong reason"
            ) from error
    else:
        raise ValueError("mutation was not rejected: nested_review_atom")

    for name, mutate in _mutation_specs(value):
        mutation = copy.deepcopy(value)
        mutate(mutation)
        mutation["integrity"]["content_sha256"] = _content_sha256(mutation)
        try:
            validate_annotation(mutation, *inputs)
        except ValueError:
            continue
        raise ValueError(f"mutation was not rejected: {name}")


def _write_or_check(path: Path, raw: bytes, check: bool) -> None:
    if len(raw) >= MAX_COMMITTED_FILE_BYTES:
        raise ValueError(f"stage-2 artifact exceeds size law: {path.name}")
    if check:
        if not path.is_file() or path.read_bytes() != raw:
            raise ValueError(
                f"stage-2 artifact drift: {path.relative_to(ROOT)}"
            )
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--mutation-tests", action="store_true")
    args = parser.parse_args()
    inputs = _inputs()
    value = build_annotation(*inputs)
    if args.mutation_tests:
        run_mutation_tests(value, inputs)
    _write_or_check(OUTPUT_PATH, _canonical_bytes(value), args.check)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
