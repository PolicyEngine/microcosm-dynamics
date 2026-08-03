#!/usr/bin/env python3
"""Seal the R_Q stage-2 annotation for document_source_position 5.

The document is `documentation/capture1/fam1970_QxQs.pdf` (wave 1970, 91
pages).  This tool is a nonauthority lane builder under the committed
protocol in `docs/analysis/rq_stage2_protocol.md`: it emits one sealed
document shard and no Q5, era seal, global catalog, alias, `R_Q`, hierarchy,
slot, inventory, or legal-registry artifact.

Build order, which is also the candidate-nonselection order:

1. Reproduce the pinned raw and content identities of the stage-1 source
   replay and the global candidate index.
2. Reproduce the document identity and every page digest independently from
   the registered PDF under the pinned Poppler derivation.
3. Read the reviewer-authored source review, which was written against the
   exact page bytes without reading any candidate artifact.
4. Derive the whole-document locator, page rows, occurrence rows, flow branch
   rows, local anchor classifications, and repeat/alias evidence.
5. Only then read the candidate artifact, and exact-disposition every
   candidate row against the derived output.

No candidate auto-promotes: every emitted row carries an explicit
adjudication and every candidate carries an explicit disposition.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import build_global_q5_intermediate_evidence as source_tools  # noqa: E402

from populace_dynamics.data import (  # noqa: E402
    psid_questionnaire_inventory as questionnaire_inventory,
)

DOCUMENT_SOURCE_POSITION = 5
SCHEMA_VERSION = "rq_stage2_document_annotation_nonauthority.v1"
REVIEW_SCHEMA_VERSION = "rq_stage2_document_source_review.v1"
STATUS = "sealed_complete_nonauthority_document_annotation"
AUTHORITY_KIND = "document_local_source_annotation_nonauthority"
CANONICALIZATION = source_tools.CANONICALIZATION
FLOW_ROOT = "questionnaire-flow:root"

CANONICAL_SOURCE_PATH = "documentation/capture1/fam1970_QxQs.pdf"
INTERVIEW_WAVE = 1970
PAGE_COUNT = 91

ANNOTATION_ROOT = ROOT / "docs" / "analysis" / "rq_stage2_annotations"
REVIEW_PATH = (
    ANNOTATION_ROOT / "document_005_fam1970_QxQs_source_review_v1.json"
)
OUTPUT_PATH = ANNOTATION_ROOT / "document_005_fam1970_QxQs_annotation_v1.json"
CAPTURE_ROOT = Path.home() / "PolicyEngine" / "psid-data"

SOURCE_REPLAY_PATH = (
    ROOT / "docs" / "analysis" / "rq_stage1_evidence" / "source_replay_v1.json"
)
CANDIDATE_INDEX_PATH = (
    ROOT / "docs" / "analysis" / "rq_stage1_candidates" / "index_v1.json"
)
SOURCE_REPLAY_RAW_SHA256 = (
    "f2f676db3f9180b85af1977253fb8c10ff7fd60494e1597212b922dfc0f5920a"
)
SOURCE_REPLAY_CONTENT_SHA256 = (
    "48e259ddf4c9eb60b7f9fdfd73b2576255400a7cdf19e4115d41bcf5bad3e8cc"
)
CANDIDATE_INDEX_RAW_SHA256 = (
    "a90dfea13cdd74a7d612acdee76c91d6c9e2fd2ed9f9a6befc6a99d9f773a446"
)
CANDIDATE_INDEX_CONTENT_SHA256 = (
    "ed80f518b0d2150b9d2c2f4d2e94ca517fc40d1dcd5e29a0c75833d40e86be64"
)

OCCURRENCE_KINDS = (
    "flow_branch_label",
    "role_anchor",
    "job_anchor",
    "remuneration_component_anchor",
    "role_total_anchor",
    "farm_aggregate_anchor",
    "business_aggregate_anchor",
    "context_anchor",
    "field_purpose_prompt",
    "repeat_or_alias_instruction",
)
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
ROLE_CLASSIFICATIONS = {"head_or_reference_person", "spouse_or_partner"}
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
DISPOSITIONS = ("accepted", "modified", "split", "rejected")
ADJUDICATION_ACTIONS = (
    "candidate_accepted",
    "candidate_modified",
    "candidate_split",
    "manual_add",
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
    "flow_branch_paths",
)
FLOW_BRANCH_KEYS = (
    "flow_branch_id",
    "parent_flow_branch_id",
    "source_occurrence_id",
    "branch_path",
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


# ---------------------------------------------------------------------------
# canonical helpers
# ---------------------------------------------------------------------------
def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return source_tools.canonical_json_bytes(value)


def _canonical_digest(value: Any) -> str:
    return source_tools._canonical_digest(value)


def _content_sha256(value: Mapping[str, Any]) -> str:
    return source_tools._content_sha256(value)


def _strict_json(path: Path, label: str) -> dict[str, Any]:
    return source_tools.strict_parse_document(path.read_bytes(), label)


def _expect_keys(
    value: Mapping[str, Any], expected: Sequence[str], label: str
) -> None:
    if tuple(value) != tuple(expected):
        raise ValueError(f"{label} keyset or key order drift")


# ---------------------------------------------------------------------------
# pinned stage-1 inputs
# ---------------------------------------------------------------------------
def _pinned_inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    replay_raw = SOURCE_REPLAY_PATH.read_bytes()
    index_raw = CANDIDATE_INDEX_PATH.read_bytes()
    if _sha256(replay_raw) != SOURCE_REPLAY_RAW_SHA256:
        raise ValueError("stage-1 source replay raw identity drift")
    if _sha256(index_raw) != CANDIDATE_INDEX_RAW_SHA256:
        raise ValueError("stage-1 candidate index raw identity drift")
    replay = source_tools.strict_parse_document(replay_raw, "source replay")
    index = source_tools.strict_parse_document(index_raw, "candidate index")
    if _content_sha256(replay) != SOURCE_REPLAY_CONTENT_SHA256:
        raise ValueError("stage-1 source replay content identity drift")
    if _content_sha256(index) != CANDIDATE_INDEX_CONTENT_SHA256:
        raise ValueError("stage-1 candidate index content identity drift")
    return replay, index


def _document_identity(
    replay: Mapping[str, Any], index: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    documents = replay["source_document_replay"]["questionnaire_documents"]
    matches = [
        row
        for row in documents
        if row["canonical_source_path"] == CANONICAL_SOURCE_PATH
    ]
    if len(matches) != 1:
        raise ValueError("document identity is not a singleton in the replay")
    document = matches[0]
    if document["interview_waves"] != [INTERVIEW_WAVE]:
        raise ValueError("document wave is not the expected singleton")
    if document["document_role"] != "questionnaire_flow":
        raise ValueError("document role drift")

    manifests = [
        row
        for row in index["document_candidate_manifest_rows"]
        if row["document_source_position"] == DOCUMENT_SOURCE_POSITION
    ]
    if len(manifests) != 1:
        raise ValueError("candidate manifest row is not a singleton")
    manifest = manifests[0]
    for key, expected in (
        ("canonical_source_path", CANONICAL_SOURCE_PATH),
        ("interview_wave", INTERVIEW_WAVE),
        ("page_count", PAGE_COUNT),
        ("source_document_id", document["source_document_id"]),
    ):
        if manifest[key] != expected:
            raise ValueError(f"candidate manifest {key} drift")

    pages = [
        row
        for row in replay["questionnaire_page_replay"][
            "questionnaire_page_rows"
        ]
        if row["source_document_id"] == document["source_document_id"]
    ]
    pages.sort(key=lambda row: row["page_number"])
    if len(pages) != PAGE_COUNT:
        raise ValueError("replayed page count drift")
    if [row["page_number"] for row in pages] != list(range(1, PAGE_COUNT + 1)):
        raise ValueError("replayed page numbering drift")
    return document, manifest, pages


def _extract_page_texts(
    document: Mapping[str, Any], replayed_pages: Sequence[Mapping[str, Any]]
) -> list[str]:
    """Re-derive the page text independently under the pinned derivation."""
    pdf_path = CAPTURE_ROOT / document["canonical_source_path"]
    raw = pdf_path.read_bytes()
    if len(raw) != document["byte_size"] or _sha256(raw) != document["sha256"]:
        raise ValueError("registered PDF identity drift")
    pages = questionnaire_inventory._pdftotext_pages(pdf_path)
    if len(pages) != PAGE_COUNT:
        raise ValueError("re-derived page count drift")
    for page_text, replayed in zip(pages, replayed_pages, strict=True):
        encoded = page_text.encode("utf-8")
        if _sha256(encoded) != replayed["page_text_utf8_sha256"]:
            raise ValueError(
                f"page {replayed['page_number']} digest does not reproduce"
            )
        if len(encoded) != replayed["page_text_utf8_size_bytes"]:
            raise ValueError(
                f"page {replayed['page_number']} byte size does not reproduce"
            )
    return pages


# ---------------------------------------------------------------------------
# reviewer source review
# ---------------------------------------------------------------------------
def _load_review() -> dict[str, Any]:
    review = _strict_json(REVIEW_PATH, "source review")
    if set(review) != REVIEW_TOP_LEVEL_KEYS:
        raise ValueError("source review keyset drift")
    if review["schema_version"] != REVIEW_SCHEMA_VERSION:
        raise ValueError("source review schema drift")
    if review["document_source_position"] != DOCUMENT_SOURCE_POSITION:
        raise ValueError("source review document drift")
    if review["status"] != "complete":
        raise ValueError("source review is not complete")
    if review["review_method"]["global_ids_assigned"] is not False:
        raise ValueError("source review claims global IDs")
    if _content_sha256(review) != review["integrity"]["content_sha256"]:
        raise ValueError("source review content identity drift")
    return review


def _utf8_slice(page_text: str, start: int, end: int) -> tuple[bytes, str]:
    raw = page_text.encode("utf-8")
    if not 0 <= start < end <= len(raw):
        raise ValueError("occurrence span outside the page byte domain")
    chunk = raw[start:end]
    try:
        text = chunk.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:  # pragma: no cover - guarded by law
        raise ValueError("occurrence span is not character aligned") from error
    if not text:
        raise ValueError("occurrence span is empty")
    return chunk, text


def validate_review(review: Mapping[str, Any], pages: Sequence[str]) -> None:
    """Every review row must resolve against the exact page bytes."""
    page_rows = review["page_review_rows"]
    if len(page_rows) != PAGE_COUNT:
        raise ValueError("review page cover is incomplete")
    for position, row in enumerate(page_rows, 1):
        if row["page_number"] != position:
            raise ValueError("review page rows are out of order")
        if row["review_status"] != "complete":
            raise ValueError(f"page {position} review is not complete")
        if row["whole_page_review_complete"] is not True:
            raise ValueError(f"page {position} whole-page review not complete")
        if row["page_text_utf8_sha256"] != _sha256(
            pages[position - 1].encode("utf-8")
        ):
            raise ValueError(f"page {position} review digest drift")

    seen: set[str] = set()
    coordinates: set[tuple[int, int, int, str]] = set()
    for spec in review["occurrence_specs"]:
        if spec["occurrence_kind"] not in KIND_ORDER:
            raise ValueError("review occurrence kind is not a section 19 kind")
        page_number = spec["page_number"]
        if not 1 <= page_number <= PAGE_COUNT:
            raise ValueError("review occurrence page out of domain")
        _utf8_slice(
            pages[page_number - 1],
            spec["utf8_byte_start"],
            spec["utf8_byte_end"],
        )
        if spec["review_occurrence_id"] in seen:
            raise ValueError("duplicate review occurrence id")
        seen.add(spec["review_occurrence_id"])
        key = (
            page_number,
            spec["utf8_byte_start"],
            spec["utf8_byte_end"],
            spec["occurrence_kind"],
        )
        if key in coordinates:
            raise ValueError("duplicate review occurrence coordinate")
        coordinates.add(key)
        if not spec["parent_review_branch_paths"]:
            raise ValueError("review occurrence has no parent path array")
        for path in spec["parent_review_branch_paths"]:
            for element in path:
                if element not in seen and element not in {
                    other["review_occurrence_id"]
                    for other in review["occurrence_specs"]
                }:
                    raise ValueError(
                        "review branch path references an unknown atom"
                    )

    labels = {
        spec["review_occurrence_id"]
        for spec in review["occurrence_specs"]
        if spec["occurrence_kind"] == "flow_branch_label"
    }
    for spec in review["occurrence_specs"]:
        for path in spec["parent_review_branch_paths"]:
            for element in path:
                if element not in labels:
                    raise ValueError(
                        "branch path element is not a branch label"
                    )
        if spec["occurrence_kind"] == "flow_branch_label":
            if len(spec["parent_review_branch_paths"]) != 1:
                raise ValueError(
                    "a branch label must carry exactly one parent path"
                )

    anchors = {
        spec["review_occurrence_id"]: spec
        for spec in review["occurrence_specs"]
        if spec["occurrence_kind"] in ANCHOR_KINDS
    }
    if len(review["local_anchor_specs"]) != len(anchors):
        raise ValueError("local anchor specs do not exact-cover anchor atoms")
    for spec in review["local_anchor_specs"]:
        source = anchors.get(spec["review_occurrence_id"])
        if source is None:
            raise ValueError("local anchor spec has no anchor atom")
        kind = source["occurrence_kind"]
        if kind == "role_anchor":
            if spec["node_domain"] != "role":
                raise ValueError("role anchor domain drift")
            if spec["classification"] not in ROLE_CLASSIFICATIONS:
                raise ValueError(
                    "role classification is not a section 19 role"
                )
        else:
            domain, classification = ANCHOR_CLASSIFICATION[kind]
            if (spec["node_domain"], spec["classification"]) != (
                domain,
                classification,
            ):
                raise ValueError(f"{kind} classification drift")
        if spec["classification_status"] != "provisional_document_local":
            raise ValueError("local anchor status drift")

    repeats = {
        spec["review_occurrence_id"]
        for spec in review["occurrence_specs"]
        if spec["occurrence_kind"] == "repeat_or_alias_instruction"
    }
    if {
        spec["review_occurrence_id"] for spec in review["repeat_alias_specs"]
    } != repeats:
        raise ValueError("repeat/alias specs do not exact-cover repeat atoms")
    for spec in review["repeat_alias_specs"]:
        if spec["relation"] not in ALIAS_RELATIONS:
            raise ValueError("alias relation is not a section 19 relation")
        if not spec["evidence_review_occurrence_ids"]:
            raise ValueError("alias evidence array is empty")


# ---------------------------------------------------------------------------
# derived rows
# ---------------------------------------------------------------------------
def _locator(document: Mapping[str, Any]) -> dict[str, Any]:
    size = document["byte_size"]
    digest = document["sha256"]
    locator_id = "psid-whole-document:" + _canonical_digest(
        [document["source_document_id"], INTERVIEW_WAVE, digest, size]
    )
    row = {
        "locator_id": locator_id,
        "source_document_id": document["source_document_id"],
        "interview_wave": INTERVIEW_WAVE,
        "filename": Path(CANONICAL_SOURCE_PATH).name,
        "location_type": "whole_document_exact_file_range",
        "byte_start": 0,
        "byte_end": size,
        "size_bytes": size,
        "full_file_sha256": digest,
        "range_sha256": digest,
        "pdf_page_domain": "all_pages_and_flow_branches",
    }
    _expect_keys(row, LOCATOR_KEYS, "whole document locator")
    if row["location_type"] != "whole_document_exact_file_range":
        raise ValueError("locator type drift")
    if row["byte_start"] != 0 or row["byte_end"] != row["size_bytes"]:
        raise ValueError("locator range is not the whole file")
    if row["range_sha256"] != row["full_file_sha256"]:
        raise ValueError("locator range digest drift")
    if row["pdf_page_domain"] != "all_pages_and_flow_branches":
        raise ValueError("locator page domain drift")
    return row


def _occurrence_locator_sha256(
    document_id: str,
    page_number: int,
    start: int,
    end: int,
    index: int,
    ordinal: int,
    kind: str,
) -> str:
    return _canonical_digest(
        [
            document_id,
            CANONICAL_SOURCE_PATH,
            "questionnaire_page_utf8_span",
            [
                INTERVIEW_WAVE,
                page_number,
                start,
                end,
                index,
                ordinal,
                kind,
            ],
        ]
    )


def _path_sort_key(path: Sequence[str]) -> tuple[bytes, ...]:
    return tuple(element.encode("utf-8") for element in path)


def _build_occurrences_and_branches(
    review: Mapping[str, Any],
    pages: Sequence[str],
    document: Mapping[str, Any],
    locator: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, str]]:
    """Derive occurrence rows then branch rows, resolving review-local IDs."""
    document_id = document["source_document_id"]
    specs = sorted(
        review["occurrence_specs"],
        key=lambda spec: (
            spec["page_number"],
            spec["utf8_byte_start"],
            spec["utf8_byte_end"],
            KIND_ORDER[spec["occurrence_kind"]],
        ),
    )
    by_page: dict[int, list[dict[str, Any]]] = {}
    for spec in specs:
        by_page.setdefault(spec["page_number"], []).append(spec)

    # Pass 1: assign the within-page index, which the ID preimage needs.
    index_of: dict[str, int] = {}
    for _page_number, page_specs in by_page.items():
        for position, spec in enumerate(page_specs):
            index_of[spec["review_occurrence_id"]] = position

    # Pass 2: branch IDs.  A branch label's own ID depends on its parent path,
    # so labels are resolved in source order and every parent already exists.
    branch_id_of: dict[str, str] = {}
    occurrence_id_of: dict[str, str] = {}
    spec_by_id = {spec["review_occurrence_id"]: spec for spec in specs}

    def resolve_path(review_path: Sequence[str]) -> list[str]:
        return [FLOW_ROOT] + [branch_id_of[element] for element in review_path]

    occurrences: list[dict[str, Any]] = []
    branches: list[dict[str, Any]] = []
    for spec in specs:
        page_number = spec["page_number"]
        start, end = spec["utf8_byte_start"], spec["utf8_byte_end"]
        kind = spec["occurrence_kind"]
        chunk, text = _utf8_slice(pages[page_number - 1], start, end)
        index = index_of[spec["review_occurrence_id"]]
        ordinal = 0
        paths = [
            resolve_path(path) for path in spec["parent_review_branch_paths"]
        ]
        paths.sort(key=_path_sort_key)
        locator_digest = _occurrence_locator_sha256(
            document_id, page_number, start, end, index, ordinal, kind
        )
        values = [
            document_id,
            locator["locator_id"],
            locator_digest,
            INTERVIEW_WAVE,
            page_number,
            start,
            end,
            index,
            ordinal,
            kind,
            text,
            _sha256(chunk),
            paths,
        ]
        occurrence_id = "psid-questionnaire-occurrence:" + _canonical_digest(
            values
        )
        row = {
            "questionnaire_occurrence_id": occurrence_id,
            "source_document_id": document_id,
            "source_locator_id": locator["locator_id"],
            "source_locator_sha256": locator_digest,
            "interview_wave": INTERVIEW_WAVE,
            "page_number": page_number,
            "utf8_byte_start": start,
            "utf8_byte_end": end,
            "occurrence_index_on_page": index,
            "semantic_ordinal_at_span": ordinal,
            "occurrence_kind": kind,
            "matched_text": text,
            "matched_utf8_sha256": _sha256(chunk),
            "flow_branch_paths": paths,
        }
        _expect_keys(row, OCCURRENCE_KEYS, "occurrence row")
        occurrences.append(row)
        occurrence_id_of[spec["review_occurrence_id"]] = occurrence_id

        if kind == "flow_branch_label":
            parent_path = paths[0]
            parent_id = parent_path[-1]
            branch_id = "questionnaire-flow:" + _canonical_digest(
                [parent_id, INTERVIEW_WAVE, occurrence_id]
            )
            branch_id_of[spec["review_occurrence_id"]] = branch_id
            branch_row = {
                "flow_branch_id": branch_id,
                "parent_flow_branch_id": parent_id,
                "source_occurrence_id": occurrence_id,
                "branch_path": [*parent_path, branch_id],
                "interview_wave": INTERVIEW_WAVE,
                "source_locator_id": locator["locator_id"],
                "page_number": page_number,
                "occurrence_index_on_page": index,
                "branch_label": text,
                "branch_label_sha256": _sha256(chunk),
            }
            _expect_keys(branch_row, FLOW_BRANCH_KEYS, "flow branch row")
            branches.append(branch_row)

    del spec_by_id
    return occurrences, branches, occurrence_id_of


def _page_rows(
    pages: Sequence[str],
    occurrences: Sequence[Mapping[str, Any]],
    document: Mapping[str, Any],
    locator: Mapping[str, Any],
) -> list[dict[str, Any]]:
    by_page: dict[int, list[str]] = {}
    for row in occurrences:
        by_page.setdefault(row["page_number"], []).append(
            row["questionnaire_occurrence_id"]
        )
    rows: list[dict[str, Any]] = []
    for page_number, page_text in enumerate(pages, 1):
        digest = _sha256(page_text.encode("utf-8"))
        page_id = "psid-questionnaire-page:" + _canonical_digest(
            [
                document["source_document_id"],
                INTERVIEW_WAVE,
                page_number,
                digest,
            ]
        )
        row = {
            "questionnaire_page_id": page_id,
            "source_document_id": document["source_document_id"],
            "source_locator_id": locator["locator_id"],
            "interview_wave": INTERVIEW_WAVE,
            "page_number": page_number,
            "page_text_utf8_sha256": digest,
            "questionnaire_occurrence_ids": by_page.get(page_number, []),
            "annotation_status": "complete",
        }
        _expect_keys(row, PAGE_KEYS, "page row")
        rows.append(row)
    return rows


def _local_anchor_rows(
    review: Mapping[str, Any],
    occurrences: Sequence[Mapping[str, Any]],
    occurrence_id_of: Mapping[str, str],
) -> list[dict[str, Any]]:
    by_id = {row["questionnaire_occurrence_id"]: row for row in occurrences}
    order = {
        row["questionnaire_occurrence_id"]: position
        for position, row in enumerate(occurrences)
    }
    rows: list[dict[str, Any]] = []
    for spec in review["local_anchor_specs"]:
        occurrence_id = occurrence_id_of[spec["review_occurrence_id"]]
        occurrence = by_id[occurrence_id]
        label = occurrence["matched_text"]
        row = {
            "local_anchor_classification_id": (
                "rq-local-anchor-classification:"
                + _canonical_digest(
                    [
                        occurrence_id,
                        spec["node_domain"],
                        spec["classification"],
                    ]
                )
            ),
            "source_occurrence_id": occurrence_id,
            "occurrence_kind": occurrence["occurrence_kind"],
            "node_domain": spec["node_domain"],
            "classification": spec["classification"],
            "printed_identifier": spec["printed_identifier"],
            "exact_label": label,
            "exact_label_sha256": _sha256(label.encode("utf-8")),
            "parent_source_occurrence_ids": [
                occurrence_id_of[element]
                for element in spec["parent_review_occurrence_ids"]
            ],
            "classification_status": spec["classification_status"],
        }
        _expect_keys(row, LOCAL_ANCHOR_KEYS, "local anchor row")
        rows.append(row)
    rows.sort(key=lambda row: order[row["source_occurrence_id"]])
    return rows


def _local_repeat_rows(
    review: Mapping[str, Any],
    occurrences: Sequence[Mapping[str, Any]],
    occurrence_id_of: Mapping[str, str],
) -> list[dict[str, Any]]:
    order = {
        row["questionnaire_occurrence_id"]: position
        for position, row in enumerate(occurrences)
    }
    rows: list[dict[str, Any]] = []
    for spec in review["repeat_alias_specs"]:
        occurrence_id = occurrence_id_of[spec["review_occurrence_id"]]
        evidence = [
            occurrence_id_of[element]
            for element in spec["evidence_review_occurrence_ids"]
        ]
        evidence.sort(key=lambda element: order[element])
        row = {
            "local_repeat_alias_evidence_id": (
                "rq-local-repeat-alias-evidence:"
                + _canonical_digest([occurrence_id, spec["relation"]])
            ),
            "source_occurrence_id": occurrence_id,
            "relation": spec["relation"],
            "alias_anchor_source_occurrence_ids": [
                occurrence_id_of[element]
                for element in spec["alias_anchor_review_occurrence_ids"]
            ],
            "canonical_anchor_source_occurrence_ids": [
                occurrence_id_of[element]
                for element in spec["canonical_anchor_review_occurrence_ids"]
            ],
            "evidence_occurrence_ids": evidence,
            "target_scope": spec["target_scope"],
            "resolution_status": spec["resolution_status"],
        }
        _expect_keys(row, LOCAL_REPEAT_KEYS, "local repeat/alias row")
        rows.append(row)
    rows.sort(key=lambda row: order[row["source_occurrence_id"]])
    return rows


# ---------------------------------------------------------------------------
# candidate adjudication
# ---------------------------------------------------------------------------
def _load_candidates(manifest: Mapping[str, Any]) -> dict[str, Any]:
    path = ROOT / manifest["path"]
    raw = path.read_bytes()
    if _sha256(raw) != manifest["raw_sha256"]:
        raise ValueError("candidate artifact raw identity drift")
    candidates = source_tools.strict_parse_document(raw, "candidate artifact")
    if _content_sha256(candidates) != manifest["content_sha256"]:
        raise ValueError("candidate artifact content identity drift")
    if candidates["document_source_position"] != DOCUMENT_SOURCE_POSITION:
        raise ValueError("candidate artifact document drift")
    if candidates["status"] != "unadjudicated_nonauthority_candidates":
        raise ValueError("candidate artifact status drift")
    law = candidates["candidate_nonselection_law"]
    if law["auto_promotion_permitted"] is not False:
        raise ValueError("candidate artifact claims auto promotion")
    return candidates


def _disposition_row(
    row_kind: str, candidate_id: str, disposition: str, row_ids: Sequence[str]
) -> dict[str, Any]:
    if disposition not in DISPOSITIONS:
        raise ValueError("unknown candidate disposition")
    row = {
        "candidate_row_kind": row_kind,
        "candidate_id": candidate_id,
        "disposition": disposition,
        "stage2_row_ids": list(row_ids),
        "adjudication_status": "complete",
    }
    _expect_keys(row, CANDIDATE_DISPOSITION_KEYS, "candidate disposition row")
    return row


def _adjudication_row(
    row_kind: str, row_id: str, candidate_ids: Sequence[str], action: str
) -> dict[str, Any]:
    if action not in ADJUDICATION_ACTIONS:
        raise ValueError("unknown adjudication action")
    if action == "manual_add" and candidate_ids:
        raise ValueError("a manual addition cannot project any candidate")
    if action != "manual_add" and not candidate_ids:
        raise ValueError(
            "a candidate-derived row needs a candidate projection"
        )
    row = {
        "stage2_row_kind": row_kind,
        "stage2_row_id": row_id,
        "source_candidate_ids": list(candidate_ids),
        "adjudication_action": action,
        "whole_page_review_complete": True,
        "source_span_verified": True,
        "adjudication_status": "complete",
    }
    _expect_keys(row, OUTPUT_ADJUDICATION_KEYS, "output adjudication row")
    return row


def _adjudicate(
    candidates: Mapping[str, Any],
    locator: Mapping[str, Any],
    page_rows: Sequence[Mapping[str, Any]],
    occurrences: Sequence[Mapping[str, Any]],
    branches: Sequence[Mapping[str, Any]],
    anchors: Sequence[Mapping[str, Any]],
    repeats: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Exact-disposition every candidate, then adjudicate every output row."""
    dispositions: list[dict[str, Any]] = []
    claims: dict[str, list[str]] = {}
    strongest: dict[str, str] = {}

    def claim(row_id: str, candidate_id: str, disposition: str) -> None:
        claims.setdefault(row_id, []).append(candidate_id)
        rank = {"accepted": 3, "split": 2, "modified": 1}
        current = strongest.get(row_id)
        if current is None or rank[disposition] > rank[current]:
            strongest[row_id] = disposition

    # --- whole-document locator -------------------------------------------
    locator_candidate = candidates["whole_document_locator_candidate"]
    locator_matches = (
        locator_candidate["source_document_id"]
        == locator["source_document_id"]
        and locator_candidate["interview_wave"] == locator["interview_wave"]
        and locator_candidate["byte_start"] == locator["byte_start"]
        and locator_candidate["byte_end"] == locator["byte_end"]
        and locator_candidate["size_bytes"] == locator["size_bytes"]
        and locator_candidate["full_file_sha256"]
        == locator["full_file_sha256"]
        and locator_candidate["range_sha256"] == locator["range_sha256"]
        and locator_candidate["filename"] == locator["filename"]
        and locator_candidate["location_type_candidate"]
        == locator["location_type"]
        and locator_candidate["pdf_page_domain_candidate"]
        == locator["pdf_page_domain"]
    )
    if not locator_matches:
        raise ValueError("locator candidate contradicts the derived locator")
    dispositions.append(
        _disposition_row(
            "whole_document_locator",
            locator_candidate["candidate_locator_id"],
            "accepted",
            [locator["locator_id"]],
        )
    )
    claim(
        locator["locator_id"],
        locator_candidate["candidate_locator_id"],
        "accepted",
    )

    # --- pages -------------------------------------------------------------
    page_by_number = {row["page_number"]: row for row in page_rows}
    for candidate in candidates["candidate_page_rows"]:
        derived = page_by_number[candidate["page_number"]]
        if (
            candidate["page_text_utf8_sha256"]
            != derived["page_text_utf8_sha256"]
        ):
            raise ValueError("page candidate digest contradicts the replay")
        dispositions.append(
            _disposition_row(
                "page",
                candidate["candidate_page_id"],
                "accepted",
                [derived["questionnaire_page_id"]],
            )
        )
        claim(
            derived["questionnaire_page_id"],
            candidate["candidate_page_id"],
            "accepted",
        )

    # --- occurrences -------------------------------------------------------
    by_page: dict[int, list[Mapping[str, Any]]] = {}
    for row in occurrences:
        by_page.setdefault(row["page_number"], []).append(row)
    exact: dict[tuple[int, int, int, str], Mapping[str, Any]] = {
        (
            row["page_number"],
            row["utf8_byte_start"],
            row["utf8_byte_end"],
            row["occurrence_kind"],
        ): row
        for row in occurrences
    }
    occurrence_disposition: dict[str, tuple[str, list[str]]] = {}
    for candidate in candidates["candidate_occurrence_rows"]:
        page_number = candidate["page_number"]
        start = candidate["utf8_byte_start"]
        end = candidate["utf8_byte_end"]
        kind = candidate["occurrence_kind_candidate"]
        candidate_id = candidate["candidate_occurrence_id"]
        key = (page_number, start, end, kind)
        if key in exact:
            row = exact[key]
            disposition, row_ids = "accepted", [
                row["questionnaire_occurrence_id"]
            ]
        else:
            contained = [
                row
                for row in by_page.get(page_number, [])
                if row["occurrence_kind"] == kind
                and start <= row["utf8_byte_start"]
                and row["utf8_byte_end"] <= end
            ]
            if len(contained) >= 2:
                disposition = "split"
                row_ids = [
                    row["questionnaire_occurrence_id"] for row in contained
                ]
            elif len(contained) == 1:
                disposition = "modified"
                row_ids = [contained[0]["questionnaire_occurrence_id"]]
            else:
                overlapping = [
                    row
                    for row in by_page.get(page_number, [])
                    if row["occurrence_kind"] == kind
                    and row["utf8_byte_start"] < end
                    and start < row["utf8_byte_end"]
                ]
                if len(overlapping) >= 2:
                    disposition = "split"
                    row_ids = [
                        row["questionnaire_occurrence_id"]
                        for row in overlapping
                    ]
                elif len(overlapping) == 1:
                    disposition = "modified"
                    row_ids = [overlapping[0]["questionnaire_occurrence_id"]]
                else:
                    disposition, row_ids = "rejected", []
        occurrence_disposition[candidate_id] = (disposition, row_ids)
        dispositions.append(
            _disposition_row("occurrence", candidate_id, disposition, row_ids)
        )
        for row_id in row_ids:
            claim(row_id, candidate_id, disposition)

    # --- flow paths --------------------------------------------------------
    branch_by_occurrence = {
        row["source_occurrence_id"]: row for row in branches
    }
    for candidate in candidates["candidate_flow_path_rows"]:
        candidate_id = candidate["candidate_flow_path_id"]
        source = candidate["source_candidate_occurrence_id"]
        derived = occurrence_disposition.get(source, ("rejected", []))[1]
        matched = [
            branch_by_occurrence[row_id]
            for row_id in derived
            if row_id in branch_by_occurrence
        ]
        if not matched:
            dispositions.append(
                _disposition_row("flow_path", candidate_id, "rejected", [])
            )
            continue
        if len(matched) >= 2:
            disposition = "split"
        else:
            candidate_depth = len(candidate["candidate_branch_path"])
            disposition = (
                "accepted"
                if candidate_depth == len(matched[0]["branch_path"])
                else "modified"
            )
        row_ids = [row["flow_branch_id"] for row in matched]
        dispositions.append(
            _disposition_row("flow_path", candidate_id, disposition, row_ids)
        )
        for row_id in row_ids:
            claim(row_id, candidate_id, disposition)

    # --- anchor classifications -------------------------------------------
    anchor_by_occurrence = {
        row["source_occurrence_id"]: row for row in anchors
    }
    for candidate in candidates["candidate_anchor_classification_rows"]:
        candidate_id = candidate["candidate_anchor_classification_id"]
        source = candidate["source_candidate_occurrence_id"]
        derived = occurrence_disposition.get(source, ("rejected", []))[1]
        matched = [
            anchor_by_occurrence[row_id]
            for row_id in derived
            if row_id in anchor_by_occurrence
        ]
        if not matched:
            dispositions.append(
                _disposition_row(
                    "anchor_classification", candidate_id, "rejected", []
                )
            )
            continue
        if len(matched) >= 2:
            disposition = "split"
        else:
            same = (
                candidate["node_domain_candidate"] == matched[0]["node_domain"]
                and candidate["classification_candidate"]
                == matched[0]["classification"]
            )
            disposition = "accepted" if same else "modified"
        row_ids = [row["local_anchor_classification_id"] for row in matched]
        dispositions.append(
            _disposition_row(
                "anchor_classification", candidate_id, disposition, row_ids
            )
        )
        for row_id in row_ids:
            claim(row_id, candidate_id, disposition)

    # --- output adjudication ----------------------------------------------
    action_of = {
        "accepted": "candidate_accepted",
        "split": "candidate_split",
        "modified": "candidate_modified",
    }
    adjudications: list[dict[str, Any]] = []

    def emit(row_kind: str, row_id: str) -> None:
        candidate_ids = claims.get(row_id, [])
        action = (
            action_of[strongest[row_id]] if candidate_ids else "manual_add"
        )
        adjudications.append(
            _adjudication_row(row_kind, row_id, candidate_ids, action)
        )

    emit("whole_document_locator", locator["locator_id"])
    for row in page_rows:
        emit("page", row["questionnaire_page_id"])
    for row in occurrences:
        emit("occurrence", row["questionnaire_occurrence_id"])
    for row in branches:
        emit("flow_branch", row["flow_branch_id"])
    for row in anchors:
        emit(
            "local_anchor_classification",
            row["local_anchor_classification_id"],
        )
    for row in repeats:
        emit(
            "local_repeat_alias_evidence",
            row["local_repeat_alias_evidence_id"],
        )
    return dispositions, adjudications


# ---------------------------------------------------------------------------
# seal
# ---------------------------------------------------------------------------
def _identity(path: Path, schema_version: str) -> dict[str, Any]:
    raw = path.read_bytes()
    value = source_tools.strict_parse_document(raw, str(path))
    return {
        "byte_size": len(raw),
        "content_sha256": value["integrity"]["content_sha256"],
        "path": str(path.relative_to(ROOT)),
        "raw_sha256": _sha256(raw),
        "schema_version": schema_version,
    }


def _census(
    rows: Sequence[Mapping[str, Any]],
    kind_key: str,
    value_key: str,
    kinds: Sequence[str],
    values: Sequence[str],
) -> dict[str, Any]:
    census: dict[str, dict[str, int]] = {
        kind: {value: 0 for value in values} for kind in kinds
    }
    for row in rows:
        census[row[kind_key]][row[value_key]] += 1
    return census


def _seal(
    locator: Mapping[str, Any],
    page_rows: Sequence[Mapping[str, Any]],
    occurrences: Sequence[Mapping[str, Any]],
    branches: Sequence[Mapping[str, Any]],
    anchors: Sequence[Mapping[str, Any]],
    repeats: Sequence[Mapping[str, Any]],
    dispositions: Sequence[Mapping[str, Any]],
    adjudications: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    counts_by_kind = {kind: 0 for kind in OCCURRENCE_KINDS}
    for row in occurrences:
        counts_by_kind[row["occurrence_kind"]] += 1
    return {
        "authority_status": "nonauthority",
        "candidate_adjudication_census_by_kind": _census(
            dispositions,
            "candidate_row_kind",
            "disposition",
            CANDIDATE_ROW_KINDS,
            DISPOSITIONS,
        ),
        "candidate_disposition_count": len(dispositions),
        "candidate_disposition_domain_sha256": _canonical_digest(
            list(dispositions)
        ),
        "candidate_domain_exact_cover": True,
        "empty_occurrence_page_count": sum(
            1 for row in page_rows if not row["questionnaire_occurrence_ids"]
        ),
        "flow_branch_count": len(branches),
        "flow_branch_domain_sha256": _canonical_digest(list(branches)),
        "global_ids_assigned": False,
        "local_anchor_classification_count": len(anchors),
        "local_anchor_classification_domain_sha256": _canonical_digest(
            list(anchors)
        ),
        "local_repeat_alias_evidence_count": len(repeats),
        "local_repeat_alias_evidence_domain_sha256": _canonical_digest(
            list(repeats)
        ),
        "output_adjudication_census_by_kind": _census(
            adjudications,
            "stage2_row_kind",
            "adjudication_action",
            STAGE2_ROW_KINDS,
            ADJUDICATION_ACTIONS,
        ),
        "output_adjudication_count": len(adjudications),
        "output_adjudication_domain_sha256": _canonical_digest(
            list(adjudications)
        ),
        "output_domain_exact_cover": True,
        "page_review_count": len(page_rows),
        "questionnaire_occurrence_count": len(occurrences),
        "questionnaire_occurrence_counts_by_kind": counts_by_kind,
        "questionnaire_occurrence_domain_sha256": _canonical_digest(
            list(occurrences)
        ),
        "questionnaire_occurrence_keyset_sha256": _canonical_digest(
            [row["questionnaire_occurrence_id"] for row in occurrences]
        ),
        "questionnaire_page_count": len(page_rows),
        "questionnaire_page_domain_sha256": _canonical_digest(list(page_rows)),
        "questionnaire_page_keyset_sha256": _canonical_digest(
            [row["questionnaire_page_id"] for row in page_rows]
        ),
        "whole_document_locator_id": locator["locator_id"],
    }


def build_annotation() -> dict[str, Any]:
    replay, index = _pinned_inputs()
    document, manifest, replayed_pages = _document_identity(replay, index)
    pages = _extract_page_texts(document, replayed_pages)

    review = _load_review()
    if review["source_document_id"] != document["source_document_id"]:
        raise ValueError("source review document identity drift")
    validate_review(review, pages)

    locator = _locator(document)
    occurrences, branches, occurrence_id_of = _build_occurrences_and_branches(
        review, pages, document, locator
    )
    page_rows = _page_rows(pages, occurrences, document, locator)
    anchors = _local_anchor_rows(review, occurrences, occurrence_id_of)
    repeats = _local_repeat_rows(review, occurrences, occurrence_id_of)

    candidates = _load_candidates(manifest)
    dispositions, adjudications = _adjudicate(
        candidates, locator, page_rows, occurrences, branches, anchors, repeats
    )

    value = {
        "artifact_id": "",
        "authority_kind": AUTHORITY_KIND,
        "candidate_artifact_identity": {
            "byte_size": manifest["byte_size"],
            "candidate_payload_sha256": manifest["candidate_payload_sha256"],
            "content_sha256": manifest["content_sha256"],
            "path": manifest["path"],
            "raw_sha256": manifest["raw_sha256"],
            "schema_version": candidates["schema_version"],
        },
        "candidate_disposition_rows": dispositions,
        "candidate_index_identity": _identity(
            CANDIDATE_INDEX_PATH, index["schema_version"]
        ),
        "document_source_position": DOCUMENT_SOURCE_POSITION,
        "document_source_row": copy.deepcopy(dict(document)),
        "flow_branch_rows": branches,
        "integrity": {
            "canonicalization": CANONICALIZATION,
            "content_sha256": "0" * 64,
        },
        "local_anchor_classification_rows": anchors,
        "local_repeat_alias_evidence_rows": repeats,
        "nonauthority_statement": {
            "era_seal_emitted": False,
            "global_alias_resolution_emitted": False,
            "global_catalog_emitted": False,
            "hierarchy_emitted": False,
            "legal_registry_read": False,
            "one_document_only": True,
            "q5_emitted": False,
            "r_q_emitted": False,
            "slot_or_inventory_emitted": False,
            "status": "nonauthority",
        },
        "output_adjudication_rows": adjudications,
        "questionnaire_occurrence_rows": occurrences,
        "questionnaire_page_rows": page_rows,
        "schema_version": SCHEMA_VERSION,
        "seal": _seal(
            locator,
            page_rows,
            occurrences,
            branches,
            anchors,
            repeats,
            dispositions,
            adjudications,
        ),
        "source_replay_identity": _identity(
            SOURCE_REPLAY_PATH, replay["schema_version"]
        ),
        "source_review_identity": {
            "byte_size": REVIEW_PATH.stat().st_size,
            "content_sha256": review["integrity"]["content_sha256"],
            "path": str(REVIEW_PATH.relative_to(ROOT)),
            "raw_sha256": _sha256(REVIEW_PATH.read_bytes()),
            "review_id": review["review_id"],
            "schema_version": review["schema_version"],
        },
        "status": STATUS,
        "whole_document_locator": locator,
    }
    value["artifact_id"] = (
        "rq-stage2-document-annotation:"
        + _canonical_digest(
            {
                key: item
                for key, item in value.items()
                if key not in ("artifact_id", "integrity")
            }
        )
    )
    value["integrity"]["content_sha256"] = _content_sha256(value)
    validate_annotation(value, pages)
    return value


# ---------------------------------------------------------------------------
# validation
# ---------------------------------------------------------------------------
def _path_is_prefix(prefix: Sequence[str], path: Sequence[str]) -> bool:
    return len(prefix) <= len(path) and list(prefix) == list(
        path[: len(prefix)]
    )


def branch_compatible(
    occurrences: Sequence[Mapping[str, Any]],
    resolved_paths: Sequence[Sequence[str]],
) -> bool:
    """Section 19's existential prefix law; no witness path is serialized."""
    if not occurrences:
        raise ValueError(
            "branch compatibility needs a nonempty occurrence set"
        )
    for resolved in resolved_paths:
        if all(
            any(
                _path_is_prefix(path, resolved)
                for path in row["flow_branch_paths"]
            )
            for row in occurrences
        ):
            return True
    return False


def validate_annotation(
    value: Mapping[str, Any], pages: Sequence[str]
) -> None:
    if value["schema_version"] != SCHEMA_VERSION:
        raise ValueError("annotation schema drift")
    if value["status"] != STATUS:
        raise ValueError("annotation status drift")
    if value["authority_kind"] != AUTHORITY_KIND:
        raise ValueError("annotation authority drift")
    statement = value["nonauthority_statement"]
    for key in (
        "era_seal_emitted",
        "global_alias_resolution_emitted",
        "global_catalog_emitted",
        "hierarchy_emitted",
        "legal_registry_read",
        "q5_emitted",
        "r_q_emitted",
        "slot_or_inventory_emitted",
    ):
        if statement[key] is not False:
            raise ValueError(f"nonauthority statement drift for {key}")
    if statement["one_document_only"] is not True:
        raise ValueError("annotation seals more than one document")

    locator = value["whole_document_locator"]
    _expect_keys(locator, LOCATOR_KEYS, "whole document locator")
    if (
        locator["byte_start"] != 0
        or locator["byte_end"] != locator["size_bytes"]
    ):
        raise ValueError("locator whole-file equation failure")
    if locator["range_sha256"] != locator["full_file_sha256"]:
        raise ValueError("locator digest equation failure")
    if locator["location_type"] != "whole_document_exact_file_range":
        raise ValueError("locator type equation failure")
    if locator["pdf_page_domain"] != "all_pages_and_flow_branches":
        raise ValueError("locator page-domain equation failure")
    expected_locator = "psid-whole-document:" + _canonical_digest(
        [
            locator["source_document_id"],
            locator["interview_wave"],
            locator["full_file_sha256"],
            locator["size_bytes"],
        ]
    )
    if locator["locator_id"] != expected_locator:
        raise ValueError("locator ID preimage failure")

    page_rows = value["questionnaire_page_rows"]
    if len(page_rows) != PAGE_COUNT:
        raise ValueError("page cover is incomplete")
    seen_pages: set[int] = set()
    for position, row in enumerate(page_rows, 1):
        _expect_keys(row, PAGE_KEYS, "page row")
        if row["page_number"] != position:
            raise ValueError("page rows are not in page-number order")
        if isinstance(row["page_number"], bool) or row["page_number"] < 1:
            raise ValueError("page number is not a positive integer")
        if row["page_number"] in seen_pages:
            raise ValueError("duplicate page coordinate")
        seen_pages.add(row["page_number"])
        if row["annotation_status"] != "complete":
            raise ValueError("page annotation status drift")
        if row["source_locator_id"] != locator["locator_id"]:
            raise ValueError("page locator does not resolve the shard")
        if row["page_text_utf8_sha256"] != _sha256(
            pages[position - 1].encode("utf-8")
        ):
            raise ValueError("page digest does not reproduce")
        expected_page = "psid-questionnaire-page:" + _canonical_digest(
            [
                row["source_document_id"],
                row["interview_wave"],
                row["page_number"],
                row["page_text_utf8_sha256"],
            ]
        )
        if row["questionnaire_page_id"] != expected_page:
            raise ValueError("page ID preimage failure")

    occurrences = value["questionnaire_occurrence_rows"]
    by_page: dict[int, list[Mapping[str, Any]]] = {}
    coordinates: set[tuple[int, int, int, str, int]] = set()
    identifiers: set[str] = set()
    locator_digests: set[str] = set()
    for row in occurrences:
        _expect_keys(row, OCCURRENCE_KEYS, "occurrence row")
        if row["occurrence_kind"] not in KIND_ORDER:
            raise ValueError("occurrence kind is not a section 19 kind")
        page_number = row["page_number"]
        chunk, text = _utf8_slice(
            pages[page_number - 1],
            row["utf8_byte_start"],
            row["utf8_byte_end"],
        )
        if row["matched_text"] != text:
            raise ValueError("matched text is not the exact printed slice")
        if row["matched_utf8_sha256"] != _sha256(chunk):
            raise ValueError("matched text digest failure")
        if row["source_locator_id"] != locator["locator_id"]:
            raise ValueError("occurrence locator does not resolve the shard")
        if row["source_document_id"] != locator["source_document_id"]:
            raise ValueError("occurrence document drift")
        if row["interview_wave"] != locator["interview_wave"]:
            raise ValueError("occurrence wave drift")
        key = (
            page_number,
            row["utf8_byte_start"],
            row["utf8_byte_end"],
            row["occurrence_kind"],
            row["semantic_ordinal_at_span"],
        )
        if key in coordinates:
            raise ValueError("duplicate occurrence coordinate")
        coordinates.add(key)
        if row["questionnaire_occurrence_id"] in identifiers:
            raise ValueError("duplicate occurrence ID")
        identifiers.add(row["questionnaire_occurrence_id"])
        if row["source_locator_sha256"] in locator_digests:
            raise ValueError("duplicate occurrence locator digest")
        locator_digests.add(row["source_locator_sha256"])
        if row["occurrence_kind"] != "flow_branch_label":
            if row["semantic_ordinal_at_span"] != 0:
                raise ValueError("atomic occurrence ordinal must be zero")
        expected_digest = _occurrence_locator_sha256(
            row["source_document_id"],
            page_number,
            row["utf8_byte_start"],
            row["utf8_byte_end"],
            row["occurrence_index_on_page"],
            row["semantic_ordinal_at_span"],
            row["occurrence_kind"],
        )
        if row["source_locator_sha256"] != expected_digest:
            raise ValueError("occurrence locator digest preimage failure")
        expected_id = "psid-questionnaire-occurrence:" + _canonical_digest(
            [row[key_name] for key_name in OCCURRENCE_KEYS[1:]]
        )
        if row["questionnaire_occurrence_id"] != expected_id:
            raise ValueError("occurrence ID preimage failure")
        if not row["flow_branch_paths"]:
            raise ValueError("occurrence has an empty path array")
        for path in row["flow_branch_paths"]:
            if not path or path[0] != FLOW_ROOT:
                raise ValueError("path does not start at the flow root")
        ordered = sorted(row["flow_branch_paths"], key=_path_sort_key)
        if ordered != row["flow_branch_paths"]:
            raise ValueError("branch paths are not in branch-path order")
        by_page.setdefault(page_number, []).append(row)

    for page_number, rows in by_page.items():
        expected = sorted(
            rows,
            key=lambda row: (
                row["utf8_byte_start"],
                row["utf8_byte_end"],
                KIND_ORDER[row["occurrence_kind"]],
                row["semantic_ordinal_at_span"],
            ),
        )
        if [row["questionnaire_occurrence_id"] for row in rows] != [
            row["questionnaire_occurrence_id"] for row in expected
        ]:
            raise ValueError(f"page {page_number} occurrence order failure")
        for position, row in enumerate(expected):
            if row["occurrence_index_on_page"] != position:
                raise ValueError(
                    f"page {page_number} occurrence index failure"
                )
        page_row = page_rows[page_number - 1]
        if page_row["questionnaire_occurrence_ids"] != [
            row["questionnaire_occurrence_id"] for row in expected
        ]:
            raise ValueError(
                f"page {page_number} occurrence projection failure"
            )
    for row in page_rows:
        if (
            row["page_number"] not in by_page
            and row["questionnaire_occurrence_ids"]
        ):
            raise ValueError("empty page carries occurrence IDs")

    _validate_flow(value)
    _validate_local_rows(value)
    _validate_adjudication(value)

    seal = value["seal"]
    if seal["questionnaire_page_count"] != len(page_rows):
        raise ValueError("seal page count drift")
    if seal["questionnaire_occurrence_count"] != len(occurrences):
        raise ValueError("seal occurrence count drift")
    if seal["questionnaire_occurrence_domain_sha256"] != _canonical_digest(
        list(occurrences)
    ):
        raise ValueError("seal occurrence domain digest drift")
    if seal["questionnaire_page_domain_sha256"] != _canonical_digest(
        list(page_rows)
    ):
        raise ValueError("seal page domain digest drift")
    if seal["flow_branch_domain_sha256"] != _canonical_digest(
        list(value["flow_branch_rows"])
    ):
        raise ValueError("seal flow branch domain digest drift")
    if seal["candidate_disposition_domain_sha256"] != _canonical_digest(
        list(value["candidate_disposition_rows"])
    ):
        raise ValueError("seal candidate disposition digest drift")
    if seal["output_adjudication_domain_sha256"] != _canonical_digest(
        list(value["output_adjudication_rows"])
    ):
        raise ValueError("seal output adjudication digest drift")
    if seal["global_ids_assigned"] is not False:
        raise ValueError("seal claims global IDs")
    if seal["authority_status"] != "nonauthority":
        raise ValueError("seal authority drift")
    if _contains_global_id(value):
        raise ValueError("annotation emits a final global node ID")


def _contains_global_id(value: Any) -> bool:
    forbidden = (
        "psid-job-slot:",
        "psid-component-slot:",
        "psid-node-alias:",
        "psid-questionnaire-relationship:",
    )
    if isinstance(value, str):
        return any(value.startswith(prefix) for prefix in forbidden)
    if isinstance(value, Mapping):
        return any(_contains_global_id(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_global_id(item) for item in value)
    return False


def _validate_flow(value: Mapping[str, Any]) -> None:
    branches = value["flow_branch_rows"]
    occurrences = {
        row["questionnaire_occurrence_id"]: row
        for row in value["questionnaire_occurrence_rows"]
    }
    order = {
        row["questionnaire_occurrence_id"]: position
        for position, row in enumerate(value["questionnaire_occurrence_rows"])
    }
    labels = [
        row
        for row in value["questionnaire_occurrence_rows"]
        if row["occurrence_kind"] == "flow_branch_label"
    ]
    if len(branches) != len(labels):
        raise ValueError("branch rows are not one-to-one with branch labels")
    by_id: dict[str, Mapping[str, Any]] = {}
    seen_sources: set[str] = set()
    seen_paths: set[tuple[str, ...]] = set()
    previous = -1
    for row in branches:
        _expect_keys(row, FLOW_BRANCH_KEYS, "flow branch row")
        source = occurrences.get(row["source_occurrence_id"])
        if source is None:
            raise ValueError("branch row source occurrence is unlocatable")
        if source["occurrence_kind"] != "flow_branch_label":
            raise ValueError("branch row source is not a branch label")
        if row["source_occurrence_id"] in seen_sources:
            raise ValueError("duplicate branch label row")
        seen_sources.add(row["source_occurrence_id"])
        position = order[row["source_occurrence_id"]]
        if position <= previous:
            raise ValueError("branch rows are not in source-occurrence order")
        previous = position
        for key in (
            "interview_wave",
            "source_locator_id",
            "page_number",
            "occurrence_index_on_page",
        ):
            if row[key] != source[key]:
                raise ValueError(
                    f"branch row {key} does not deep-equal source"
                )
        if row["branch_label"] != source["matched_text"]:
            raise ValueError("branch label is not the exact matched text")
        if row["branch_label_sha256"] != source["matched_utf8_sha256"]:
            raise ValueError("branch label digest drift")
        parent = row["parent_flow_branch_id"]
        if parent != FLOW_ROOT:
            parent_row = by_id.get(parent)
            if parent_row is None:
                raise ValueError("branch parent is unresolved or later")
            if parent_row["interview_wave"] != row["interview_wave"]:
                raise ValueError("branch parent crosses waves")
        expected_id = "questionnaire-flow:" + _canonical_digest(
            [parent, row["interview_wave"], row["source_occurrence_id"]]
        )
        if row["flow_branch_id"] != expected_id:
            raise ValueError("branch ID preimage failure")
        if len(source["flow_branch_paths"]) != 1:
            raise ValueError(
                "a branch label must carry exactly one parent path"
            )
        expected_path = [
            *source["flow_branch_paths"][0],
            row["flow_branch_id"],
        ]
        if row["branch_path"] != expected_path:
            raise ValueError(
                "branch path is not the parent path plus the branch"
            )
        if row["branch_path"][-2] != parent:
            raise ValueError("branch path does not extend its parent")
        key = tuple(row["branch_path"])
        if key in seen_paths:
            raise ValueError("duplicate branch path")
        seen_paths.add(key)
        by_id[row["flow_branch_id"]] = row

    # cycle rejection: every path must terminate at the root without repeats
    for row in branches:
        seen: set[str] = set()
        cursor = row["flow_branch_id"]
        while cursor != FLOW_ROOT:
            if cursor in seen:
                raise ValueError("cycle in branch ancestry")
            seen.add(cursor)
            cursor = by_id[cursor]["parent_flow_branch_id"]

    resolved = {tuple(row["branch_path"]) for row in branches}
    for row in value["questionnaire_occurrence_rows"]:
        for path in row["flow_branch_paths"]:
            if path == [FLOW_ROOT]:
                continue
            if tuple(path) not in resolved:
                raise ValueError(
                    "occurrence path is outside the resolved domain"
                )


def _validate_local_rows(value: Mapping[str, Any]) -> None:
    occurrences = {
        row["questionnaire_occurrence_id"]: row
        for row in value["questionnaire_occurrence_rows"]
    }
    anchors = value["local_anchor_classification_rows"]
    anchor_atoms = {
        row["questionnaire_occurrence_id"]
        for row in value["questionnaire_occurrence_rows"]
        if row["occurrence_kind"] in ANCHOR_KINDS
    }
    if {row["source_occurrence_id"] for row in anchors} != anchor_atoms:
        raise ValueError("local anchors do not exact-cover the anchor atoms")
    if len(anchors) != len(anchor_atoms):
        raise ValueError("local anchor rows are not one-to-one with atoms")
    for row in anchors:
        _expect_keys(row, LOCAL_ANCHOR_KEYS, "local anchor row")
        source = occurrences[row["source_occurrence_id"]]
        if row["occurrence_kind"] != source["occurrence_kind"]:
            raise ValueError("local anchor kind drift")
        if row["exact_label"] != source["matched_text"]:
            raise ValueError(
                "local anchor label is not the exact printed text"
            )
        if row["exact_label_sha256"] != _sha256(
            row["exact_label"].encode("utf-8")
        ):
            raise ValueError("local anchor label digest drift")
        if row["classification_status"] != "provisional_document_local":
            raise ValueError("local anchor status drift")
        if source["occurrence_kind"] == "role_anchor":
            if row["node_domain"] != "role":
                raise ValueError("role anchor domain drift")
            if row["classification"] not in ROLE_CLASSIFICATIONS:
                raise ValueError("role classification drift")
        else:
            domain, classification = ANCHOR_CLASSIFICATION[
                source["occurrence_kind"]
            ]
            if (row["node_domain"], row["classification"]) != (
                domain,
                classification,
            ):
                raise ValueError("anchor classification drift")

    repeats = value["local_repeat_alias_evidence_rows"]
    repeat_atoms = {
        row["questionnaire_occurrence_id"]
        for row in value["questionnaire_occurrence_rows"]
        if row["occurrence_kind"] == "repeat_or_alias_instruction"
    }
    if {row["source_occurrence_id"] for row in repeats} != repeat_atoms:
        raise ValueError("repeat/alias rows do not consume every instruction")
    for row in repeats:
        _expect_keys(row, LOCAL_REPEAT_KEYS, "local repeat/alias row")
        if row["relation"] not in ALIAS_RELATIONS:
            raise ValueError("alias relation drift")
        if not row["evidence_occurrence_ids"]:
            raise ValueError("alias evidence is empty")
        if row["source_occurrence_id"] not in row["evidence_occurrence_ids"]:
            raise ValueError("alias evidence omits its own instruction")
        for element in row["evidence_occurrence_ids"]:
            if element not in occurrences:
                raise ValueError("alias evidence references an unknown atom")
        if row["resolution_status"] != "deferred_to_global_assembly":
            raise ValueError("alias resolution status drift")


def _validate_adjudication(value: Mapping[str, Any]) -> None:
    dispositions = value["candidate_disposition_rows"]
    adjudications = value["output_adjudication_rows"]
    candidate_ids: set[str] = set()
    named: dict[str, list[str]] = {}
    for row in dispositions:
        _expect_keys(
            row, CANDIDATE_DISPOSITION_KEYS, "candidate disposition row"
        )
        if row["candidate_row_kind"] not in CANDIDATE_ROW_KINDS:
            raise ValueError("candidate row kind drift")
        if row["disposition"] not in DISPOSITIONS:
            raise ValueError("candidate disposition drift")
        if row["adjudication_status"] != "complete":
            raise ValueError("candidate disposition is not complete")
        if row["candidate_id"] in candidate_ids:
            raise ValueError("duplicate candidate disposition")
        candidate_ids.add(row["candidate_id"])
        count = len(row["stage2_row_ids"])
        if row["disposition"] in ("accepted", "modified") and count != 1:
            raise ValueError("accepted/modified candidate must name one row")
        if row["disposition"] == "split" and count < 2:
            raise ValueError("split candidate must name at least two rows")
        if row["disposition"] == "rejected" and count != 0:
            raise ValueError("rejected candidate must name no row")
        for row_id in row["stage2_row_ids"]:
            named.setdefault(row_id, []).append(row["candidate_id"])

    emitted: set[str] = set()
    for row in adjudications:
        _expect_keys(row, OUTPUT_ADJUDICATION_KEYS, "output adjudication row")
        if row["stage2_row_kind"] not in STAGE2_ROW_KINDS:
            raise ValueError("stage2 row kind drift")
        if row["adjudication_action"] not in ADJUDICATION_ACTIONS:
            raise ValueError("adjudication action drift")
        if row["adjudication_status"] != "complete":
            raise ValueError("output adjudication is not complete")
        if row["stage2_row_id"] in emitted:
            raise ValueError("duplicate output adjudication")
        emitted.add(row["stage2_row_id"])
        if row["whole_page_review_complete"] is not True:
            raise ValueError("output adjudication without whole-page review")
        if row["source_span_verified"] is not True:
            raise ValueError("output adjudication without verified span")
        expected = named.get(row["stage2_row_id"], [])
        if row["source_candidate_ids"] != expected:
            raise ValueError(
                "candidate projection disagrees with dispositions"
            )
        if row["adjudication_action"] == "manual_add" and expected:
            raise ValueError("manual addition projects a candidate")
        if row["adjudication_action"] != "manual_add" and not expected:
            raise ValueError("candidate-derived row without a projection")

    all_rows = (
        [value["whole_document_locator"]["locator_id"]]
        + [
            row["questionnaire_page_id"]
            for row in value["questionnaire_page_rows"]
        ]
        + [
            row["questionnaire_occurrence_id"]
            for row in value["questionnaire_occurrence_rows"]
        ]
        + [row["flow_branch_id"] for row in value["flow_branch_rows"]]
        + [
            row["local_anchor_classification_id"]
            for row in value["local_anchor_classification_rows"]
        ]
        + [
            row["local_repeat_alias_evidence_id"]
            for row in value["local_repeat_alias_evidence_rows"]
        ]
    )
    if emitted != set(all_rows):
        raise ValueError("output adjudication does not exact-cover every row")
    if len(all_rows) != len(set(all_rows)):
        raise ValueError("duplicate emitted row identifier")
    if set(named) - emitted:
        raise ValueError("a disposition names a row that was never emitted")


# ---------------------------------------------------------------------------
# mutation tests
# ---------------------------------------------------------------------------
def _mutations(value: Mapping[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    out: list[tuple[str, dict[str, Any]]] = []

    def mutate(label: str, apply) -> None:
        broken = copy.deepcopy(dict(value))
        apply(broken)
        out.append((label, broken))

    def drop_page(broken: dict[str, Any]) -> None:
        broken["questionnaire_page_rows"] = broken["questionnaire_page_rows"][
            :-1
        ]

    def reorder_pages(broken: dict[str, Any]) -> None:
        rows = broken["questionnaire_page_rows"]
        rows[0], rows[1] = rows[1], rows[0]

    def bad_span(broken: dict[str, Any]) -> None:
        broken["questionnaire_occurrence_rows"][0]["utf8_byte_end"] += 1

    def bad_hash(broken: dict[str, Any]) -> None:
        broken["questionnaire_occurrence_rows"][0]["matched_utf8_sha256"] = (
            "0" * 64
        )

    def bad_id(broken: dict[str, Any]) -> None:
        broken["questionnaire_occurrence_rows"][0][
            "questionnaire_occurrence_id"
        ] = ("psid-questionnaire-occurrence:" + "0" * 64)

    def bad_ordinal(broken: dict[str, Any]) -> None:
        for row in broken["questionnaire_occurrence_rows"]:
            if row["occurrence_kind"] != "flow_branch_label":
                row["semantic_ordinal_at_span"] = 1
                return

    def duplicate_atom(broken: dict[str, Any]) -> None:
        rows = broken["questionnaire_occurrence_rows"]
        rows.append(copy.deepcopy(rows[0]))

    def later_parent(broken: dict[str, Any]) -> None:
        rows = broken["flow_branch_rows"]
        rows[0]["parent_flow_branch_id"] = rows[-1]["flow_branch_id"]

    def cyclic_parent(broken: dict[str, Any]) -> None:
        rows = broken["flow_branch_rows"]
        rows[0]["parent_flow_branch_id"] = rows[0]["flow_branch_id"]

    def omit_label(broken: dict[str, Any]) -> None:
        broken["flow_branch_rows"] = broken["flow_branch_rows"][:-1]

    def duplicate_label(broken: dict[str, Any]) -> None:
        rows = broken["flow_branch_rows"]
        rows.append(copy.deepcopy(rows[0]))

    def selected_subset(broken: dict[str, Any]) -> None:
        for row in broken["questionnaire_occurrence_rows"]:
            if row["flow_branch_paths"] != [[FLOW_ROOT]]:
                row["flow_branch_paths"] = [[FLOW_ROOT]]
                return

    def inferred_alias(broken: dict[str, Any]) -> None:
        broken["local_anchor_classification_rows"][0]["exact_label"] = "HEAD"

    def omit_disposition(broken: dict[str, Any]) -> None:
        broken["candidate_disposition_rows"] = broken[
            "candidate_disposition_rows"
        ][:-1]

    def unadjudicated_output(broken: dict[str, Any]) -> None:
        broken["output_adjudication_rows"] = broken[
            "output_adjudication_rows"
        ][:-1]

    def forged_manual_add(broken: dict[str, Any]) -> None:
        for row in broken["output_adjudication_rows"]:
            if row["adjudication_action"] != "manual_add":
                row["adjudication_action"] = "manual_add"
                return

    def global_id(broken: dict[str, Any]) -> None:
        broken["local_anchor_classification_rows"][0][
            "local_anchor_classification_id"
        ] = ("psid-component-slot:" + "0" * 64)

    for label, apply in (
        ("missing page", drop_page),
        ("reordered pages", reorder_pages),
        ("bad occurrence span", bad_span),
        ("bad occurrence hash", bad_hash),
        ("bad occurrence ID", bad_id),
        ("illegal semantic ordinal", bad_ordinal),
        ("duplicate atom", duplicate_atom),
        ("later branch parent", later_parent),
        ("cyclic branch parent", cyclic_parent),
        ("omitted branch label", omit_label),
        ("duplicate branch label", duplicate_label),
        ("selected path subset", selected_subset),
        ("inferred alias label", inferred_alias),
        ("omitted candidate disposition", omit_disposition),
        ("unadjudicated output", unadjudicated_output),
        ("forged manual addition", forged_manual_add),
        ("final global node ID", global_id),
    ):
        mutate(label, apply)
    return out


def run_mutation_tests(value: Mapping[str, Any], pages: Sequence[str]) -> int:
    failures = 0
    for label, broken in _mutations(value):
        try:
            validate_annotation(broken, pages)
        except Exception:  # noqa: BLE001 - a rejection is the pass condition
            continue
        print(f"MUTATION NOT REJECTED: {label}")
        failures += 1
    return failures


def _page_texts_for_validation() -> list[str]:
    replay, index = _pinned_inputs()
    document, _manifest, replayed_pages = _document_identity(replay, index)
    return _extract_page_texts(document, replayed_pages)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate the committed artifact instead of rewriting it",
    )
    args = parser.parse_args()

    value = build_annotation()
    raw = _canonical_bytes(value)
    if args.check:
        if not OUTPUT_PATH.exists():
            print(f"missing artifact: {OUTPUT_PATH}")
            return 1
        if OUTPUT_PATH.read_bytes() != raw:
            print(f"artifact does not reproduce: {OUTPUT_PATH}")
            return 1
    else:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_bytes(raw)

    pages = _page_texts_for_validation()
    failures = run_mutation_tests(value, pages)
    seal = value["seal"]
    print(
        f"document              {DOCUMENT_SOURCE_POSITION} {CANONICAL_SOURCE_PATH}"
    )
    print(f"pages                 {seal['questionnaire_page_count']}")
    print(f"empty-occurrence pages{seal['empty_occurrence_page_count']:>4}")
    print(f"occurrences           {seal['questionnaire_occurrence_count']}")
    print(f"flow branches         {seal['flow_branch_count']}")
    print(f"local anchors         {seal['local_anchor_classification_count']}")
    print(f"repeat/alias evidence {seal['local_repeat_alias_evidence_count']}")
    print(f"candidate dispositions{seal['candidate_disposition_count']:>5}")
    print(f"output adjudications  {seal['output_adjudication_count']}")
    print(f"mutation failures     {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
