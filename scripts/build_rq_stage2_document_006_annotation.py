#!/usr/bin/env python3
"""Build and validate the stage-2 nonauthority annotation for document 6.

The reviewer-authored source specification is deliberately candidate-free.  The
builder authenticates and slices the complete PDF-derived page domain first and
only then opens the stage-1 candidate artifact to construct the two provenance
relations required by ``docs/analysis/rq_stage2_protocol.md``.
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

DOCUMENT_SOURCE_POSITION = 6
SCHEMA_VERSION = "rq_stage2_document_annotation_nonauthority.v1"
REVIEW_SCHEMA_VERSION = "rq_stage2_document_source_review.v1"
STATUS = "sealed_complete_nonauthority_document_annotation"
AUTHORITY_KIND = "document_local_source_annotation_nonauthority"
CANONICALIZATION = source_tools.CANONICALIZATION
FLOW_ROOT = "questionnaire-flow:root"

ANNOTATION_ROOT = ROOT / "docs" / "analysis" / "rq_stage2_annotations"
REVIEW_PATH = ANNOTATION_ROOT / "document_006_q70_source_review_v1.json"
OUTPUT_PATH = ANNOTATION_ROOT / "document_006_q70_annotation_v1.json"
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
FORBIDDEN_GLOBAL_ID_PREFIXES = (
    "psid-job-slot:",
    "psid-component-slot:",
    "psid-node-alias:",
    "psid-questionnaire-relationship:",
)
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
NOTE_KEYS = (
    "candidate_row_kind",
    "candidate_id",
    "note_code",
    "note",
)

RASTER_REASON = "raster_visible_text_absent"
EMITTED_PATH_CONSEQUENCE = (
    "emitted_with_all_resolving_extraction_authority_paths"
)
WITHHELD_PATH_CONSEQUENCE = "withheld_no_resolving_extraction_authority_path"
VISUAL_FIDELITY_NOTE_CODE = "attributable_garbled_exact_bytes_retained"
VISUAL_FIDELITY_NOTE = (
    "The visible printed atom has an attributable partial or garbled pinned "
    "UTF-8 slice; the exact slice, offsets, and hash are retained without "
    "visual repair."
)

BRANCH_EXCEPTION_KEYS = (
    "disposition",
    "source_document_id",
    "questionnaire_page_id",
    "interview_wave",
    "page_number",
    "page_text_utf8_sha256",
    "exception_index_on_page",
    "visible_label_description",
    "approximate_raster_location",
    "authority_text_statement",
)
DEPENDENT_ATOM_KEYS = (
    "reason",
    "source_document_id",
    "questionnaire_page_id",
    "interview_wave",
    "page_number",
    "page_text_utf8_sha256",
    "utf8_byte_start",
    "utf8_byte_end",
    "occurrence_kind",
    "matched_text",
    "matched_utf8_sha256",
    "blocking_exception_keys",
    "emitted_questionnaire_occurrence_ids",
    "path_consequence",
)
PAGE_CENSUS_KEYS = (
    "questionnaire_page_id",
    "source_document_id",
    "interview_wave",
    "page_number",
    "page_text_utf8_sha256",
    "branch_exception_count",
    "branch_exception_keys",
    "dependent_atom_count",
    "dependent_atom_keys",
)
RASTER_SIDECAR_KEYS = (
    "schema_version",
    "authority_kind",
    "document_completeness_claim",
    "closed_gap_disposition",
    "closed_gap_reason",
    "branch_exception_count",
    "dependent_atom_count",
    "branch_exception_records",
    "dependent_atom_consequence_records",
    "page_census_rows",
    "later_assembly_consequence",
    "status",
)
RASTER_SEAL_KEYS = (
    "raster_only_branch_exception_count",
    "raster_only_branch_exception_keyset_sha256",
    "raster_only_branch_exception_domain_sha256",
    "raster_only_dependent_atom_consequence_count",
    "raster_only_dependent_atom_consequence_keyset_sha256",
    "raster_only_dependent_atom_consequence_domain_sha256",
    "raster_only_page_census_count",
    "raster_only_page_census_keyset_sha256",
    "raster_only_page_census_domain_sha256",
    "raster_only_incompleteness_census_sha256",
)
LEGACY_FLAT_SEAL_KEYS = (
    "whole_document_locator_count",
    "whole_document_locator_domain_sha256",
    "questionnaire_page_count",
    "questionnaire_page_keyset_sha256",
    "questionnaire_page_domain_sha256",
    "empty_occurrence_page_count",
    "questionnaire_occurrence_count",
    "questionnaire_occurrence_counts_by_kind",
    "questionnaire_occurrence_keyset_sha256",
    "questionnaire_occurrence_domain_sha256",
    "flow_branch_count",
    "flow_branch_domain_sha256",
    "local_anchor_classification_count",
    "local_anchor_classification_domain_sha256",
    "local_repeat_alias_evidence_count",
    "local_repeat_alias_evidence_domain_sha256",
    "candidate_disposition_count",
    "candidate_disposition_domain_sha256",
    "candidate_adjudication_census_by_kind",
    "output_adjudication_count",
    "output_adjudication_domain_sha256",
    "output_adjudication_census_by_kind",
    "adjudication_note_count",
    "adjudication_note_domain_sha256",
    "page_review_count",
    "whole_document_review_complete",
    "candidate_domain_exact_cover",
    "output_domain_exact_cover",
    "global_ids_assigned",
    "authority_status",
)
LEGACY_AFFECTED_TOP_LEVEL_KEYS = (
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
    "raster_only_incompleteness_census",
    "output_adjudication_rows",
    "seal",
    "nonauthority_statement",
    "integrity",
    "status",
)

EXCEPTION_DEFINITIONS = (
    (7, 0, "D1: 3. RETIRED", "page 7; item D1; response box 3"),
    (
        7,
        1,
        "D1: 3. PERMANENTLY DISABLED",
        "page 7; item D1; response box 4",
    ),
    (7, 2, "D1: 4. HOUSEWIFE", "page 7; item D1; response box 5"),
    (7, 3, "D1: 5. STUDENT", "page 7; item D1; response box 6"),
    (8, 0, "D20: 1. YES", "page 8; item D20; response box 1"),
    (8, 1, "D22: 1. YES", "page 8; item D22; response box 1"),
    (8, 2, "D22: 5. NO", "page 8; item D22; response box 2"),
    (9, 0, "D24: 1. YES", "page 9; item D24; response box 1"),
    (15, 0, "F1: 1. YES", "page 15; item F1; response box 1"),
    (15, 1, "F1: 5. NO", "page 15; item F1; response box 2"),
    (16, 0, "G1: 1. MARRIED", "page 16; item G1; response box 1"),
    (16, 1, "G1: 2. SINGLE", "page 16; item G1; response box 2"),
    (16, 2, "G1: 3. WIDOWED", "page 16; item G1; response box 3"),
    (16, 3, "G1: 4. DIVORCED", "page 16; item G1; response box 4"),
    (16, 4, "G1: 5. SEPARATED", "page 16; item G1; response box 5"),
    (16, 5, "G2: 1. YES", "page 16; item G2; response box 1"),
)


def _atom_coordinates(
    page_number: int, start: int, end: int, *kinds: str
) -> tuple[tuple[int, int, int, str], ...]:
    return tuple((page_number, start, end, kind) for kind in kinds)


DEPENDENCY_GROUP_SPECS = (
    (
        "d1_inactive_to_section_f",
        ((7, 0), (7, 1), (7, 2), (7, 3)),
        EMITTED_PATH_CONSEQUENCE,
        (
            *_atom_coordinates(15, 180, 308, "flow_branch_label"),
            *_atom_coordinates(
                15, 316, 389, "context_anchor", "field_purpose_prompt"
            ),
            *_atom_coordinates(15, 362, 366, "role_anchor"),
        ),
    ),
    (
        "d21_after_d20_yes",
        ((8, 0),),
        WITHHELD_PATH_CONSEQUENCE,
        (
            *_atom_coordinates(8, 2290, 2325, "remuneration_component_anchor"),
            *_atom_coordinates(8, 2397, 2421, "field_purpose_prompt"),
        ),
    ),
    (
        "d23_after_d20_yes_and_d22_yes",
        ((8, 0), (8, 1)),
        WITHHELD_PATH_CONSEQUENCE,
        _atom_coordinates(
            8,
            2735,
            2847,
            "remuneration_component_anchor",
            "field_purpose_prompt",
        ),
    ),
    (
        "d25_through_d29_after_d24_yes",
        ((9, 0),),
        WITHHELD_PATH_CONSEQUENCE,
        (
            *_atom_coordinates(
                9, 395, 416, "context_anchor", "field_purpose_prompt"
            ),
            *_atom_coordinates(9, 452, 471, "field_purpose_prompt"),
            *_atom_coordinates(
                9,
                506,
                578,
                "remuneration_component_anchor",
                "field_purpose_prompt",
            ),
            *_atom_coordinates(
                9, 614, 680, "context_anchor", "field_purpose_prompt"
            ),
            *_atom_coordinates(
                9, 732, 809, "context_anchor", "field_purpose_prompt"
            ),
        ),
    ),
    (
        "f3_through_f5_after_f1_yes",
        ((7, 0), (7, 1), (7, 2), (7, 3), (15, 0)),
        WITHHELD_PATH_CONSEQUENCE,
        (
            *_atom_coordinates(
                15, 795, 883, "context_anchor", "field_purpose_prompt"
            ),
            *_atom_coordinates(15, 871, 881, "job_anchor"),
            *_atom_coordinates(
                15, 1017, 1064, "context_anchor", "field_purpose_prompt"
            ),
            *_atom_coordinates(
                15, 1085, 1144, "context_anchor", "field_purpose_prompt"
            ),
        ),
    ),
    (
        "g1_nonmarried_exit",
        ((16, 1), (16, 2), (16, 3), (16, 4)),
        WITHHELD_PATH_CONSEQUENCE,
        _atom_coordinates(16, 928, 950, "flow_branch_label"),
    ),
    (
        "g2_married_screen",
        ((16, 0),),
        WITHHELD_PATH_CONSEQUENCE,
        (
            *_atom_coordinates(16, 965, 1002, "repeat_or_alias_instruction"),
            *_atom_coordinates(16, 984, 988, "role_anchor"),
            *_atom_coordinates(16, 991, 1001, "job_anchor"),
            *_atom_coordinates(16, 1009, 1062, "field_purpose_prompt"),
            *_atom_coordinates(16, 1027, 1031, "role_anchor"),
            *_atom_coordinates(16, 1098, 1128, "flow_branch_label"),
        ),
    ),
    (
        "g3_through_g5_after_g2_yes",
        ((16, 0), (16, 5)),
        WITHHELD_PATH_CONSEQUENCE,
        (
            *_atom_coordinates(
                16, 1361, 1390, "context_anchor", "field_purpose_prompt"
            ),
            *_atom_coordinates(16, 1383, 1386, "role_anchor"),
            *_atom_coordinates(
                16, 1423, 1469, "context_anchor", "field_purpose_prompt"
            ),
            *_atom_coordinates(
                16, 1500, 1589, "context_anchor", "field_purpose_prompt"
            ),
        ),
    ),
)


def _dependency_index() -> dict[tuple[int, int, int, str], dict[str, Any]]:
    result: dict[tuple[int, int, int, str], dict[str, Any]] = {}
    for (
        group_name,
        blockers,
        consequence,
        coordinates,
    ) in DEPENDENCY_GROUP_SPECS:
        for coordinate in coordinates:
            if coordinate in result:
                raise ValueError("raster dependency coordinate is duplicated")
            result[coordinate] = {
                "group_name": group_name,
                "blocking_exception_refs": blockers,
                "path_consequence": consequence,
            }
    if (
        len(result) != 38
        or sum(
            row["path_consequence"] == EMITTED_PATH_CONSEQUENCE
            for row in result.values()
        )
        != 4
        or Counter(coordinate[0] for coordinate in result)
        != Counter({8: 4, 9: 9, 15: 11, 16: 14})
    ):
        raise ValueError("raster dependency adjudication census drift")
    return result


DEPENDENCY_BY_COORDINATE = _dependency_index()


def _ordinary_member_key(
    page_number: int, start: int, end: int
) -> tuple[int, ...]:
    return (1, page_number, 1, start, end)


def _exception_member_key(
    page_number: int, exception_index: int
) -> tuple[int, ...]:
    return (1, page_number, 0, exception_index)


def _prefilter_layout(
    paths: Sequence[Sequence[tuple[int, ...]]],
) -> tuple[int, tuple[int, ...]]:
    ordered = sorted(tuple(path) for path in paths)
    if len(ordered) != len(set(ordered)):
        raise ValueError("duplicate complete pre-filter path")
    emitted_ordinals = tuple(
        ordinal
        for ordinal, path in enumerate(ordered)
        if not any(len(member) == 4 and member[2] == 0 for member in path)
    )
    return len(ordered), emitted_ordinals


_ROOT_MEMBER_KEY = (0,)
_SEC_D_MEMBER_KEY = _ordinary_member_key(7, 225, 253)
_D1_OTHER_MEMBER_KEY = _ordinary_member_key(7, 719, 722)
_D1_TO_F1_MEMBER_KEY = _ordinary_member_key(7, 1101, 1116)
_SEC_G_MEMBER_KEY = _ordinary_member_key(16, 633, 725)
_SECTION_F_COMPLETE_PATHS = (
    *(
        (_ROOT_MEMBER_KEY, _SEC_D_MEMBER_KEY, _exception_member_key(7, index))
        for index in range(4)
    ),
    (
        _ROOT_MEMBER_KEY,
        _SEC_D_MEMBER_KEY,
        _D1_OTHER_MEMBER_KEY,
        _D1_TO_F1_MEMBER_KEY,
    ),
)
_G1_NONMARRIED_COMPLETE_PATHS = tuple(
    (_ROOT_MEMBER_KEY, _SEC_G_MEMBER_KEY, _exception_member_key(16, index))
    for index in range(1, 5)
)
_SECTION_F_LAYOUT = _prefilter_layout(_SECTION_F_COMPLETE_PATHS)
_G1_NONMARRIED_LAYOUT = _prefilter_layout(_G1_NONMARRIED_COMPLETE_PATHS)
if _SECTION_F_LAYOUT != (5, (4,)) or _G1_NONMARRIED_LAYOUT != (4, ()):
    raise ValueError("pre-filter comparator fixture drift")

PREFILTER_FLOW_LAYOUT_BY_COORDINATE = {
    (15, 180, 308, "flow_branch_label"): _SECTION_F_LAYOUT,
    (16, 928, 950, "flow_branch_label"): _G1_NONMARRIED_LAYOUT,
}

VISUAL_FIDELITY_COORDINATES = (
    *_atom_coordinates(7, 225, 253, "flow_branch_label"),
    *_atom_coordinates(7, 527, 610, "flow_branch_label"),
    *_atom_coordinates(7, 626, 640, "flow_branch_label"),
    *_atom_coordinates(7, 719, 722, "flow_branch_label"),
    *_atom_coordinates(7, 1101, 1116, "flow_branch_label"),
    *_atom_coordinates(7, 1525, 1535, "flow_branch_label"),
    *_atom_coordinates(7, 1544, 1568, "flow_branch_label"),
    *_atom_coordinates(7, 1597, 1606, "flow_branch_label"),
    *_atom_coordinates(7, 1750, 1789, "flow_branch_label"),
    *_atom_coordinates(8, 148, 152, "flow_branch_label"),
    *_atom_coordinates(8, 237, 241, "flow_branch_label"),
    *_atom_coordinates(8, 508, 514, "flow_branch_label"),
    *_atom_coordinates(8, 583, 587, "flow_branch_label"),
    *_atom_coordinates(8, 792, 796, "flow_branch_label"),
    *_atom_coordinates(8, 1012, 1016, "flow_branch_label"),
    *_atom_coordinates(8, 2073, 2077, "flow_branch_label"),
    *_atom_coordinates(9, 318, 334, "flow_branch_label"),
    *_atom_coordinates(12, 108, 236, "flow_branch_label"),
    *_atom_coordinates(15, 180, 308, "flow_branch_label"),
    *_atom_coordinates(16, 633, 725, "flow_branch_label"),
    *_atom_coordinates(16, 1098, 1128, "flow_branch_label"),
    *_atom_coordinates(21, 233, 254, "flow_branch_label"),
    *_atom_coordinates(21, 498, 515, "flow_branch_label"),
    *_atom_coordinates(21, 544, 566, "flow_branch_label"),
    *_atom_coordinates(21, 1420, 1426, "flow_branch_label"),
    *_atom_coordinates(21, 1446, 1464, "flow_branch_label"),
    *_atom_coordinates(21, 1647, 1668, "flow_branch_label"),
    *_atom_coordinates(21, 1699, 1713, "flow_branch_label"),
    *_atom_coordinates(21, 1821, 1825, "flow_branch_label"),
    *_atom_coordinates(21, 1969, 1979, "flow_branch_label"),
)
if (
    len(VISUAL_FIDELITY_COORDINATES) != 30
    or len(set(VISUAL_FIDELITY_COORDINATES)) != 30
):
    raise ValueError("visual-fidelity coordinate domain drift")

# Correction 2 requires each diagnostic to reuse exactly one existing
# nonaccepted candidate-note row.  This is a diagnostic-only bijection: the
# carrier rows do not become semantic evidence and their candidate keys remain
# unchanged.  Exact or overlapping same-page candidates are used where one
# exists; otherwise an unused correction carrier from the same printed item or
# screen is pinned here after whole-page adjudication.  The latter associations
# are enumerated below rather than inferred from proximity.
VISUAL_FIDELITY_NOTE_TARGETS = {
    (7, 225, 253, "flow_branch_label"): (
        "occurrence",
        "rq-candidate-occurrence:8852c4c2aa3564fe4583ee7e867e8c839aab858b473434fe367ba73304bef394",
    ),
    (7, 527, 610, "flow_branch_label"): (
        "occurrence",
        "rq-candidate-occurrence:da1a46165341a69a7f1ddec3d565af6442f7b91034e6ca6821789cee79d2433f",
    ),
    (7, 626, 640, "flow_branch_label"): (
        "flow_path",
        "rq-candidate-flow-path:01aaee7f1508f4021d1330ace2ef5990d545fa3c2286345a0b2485ac9f51964b",
    ),
    (7, 719, 722, "flow_branch_label"): (
        "occurrence",
        "rq-candidate-occurrence:ac4d7c0883ce330b10133f02ee05922780db6ef8801ca0dccd4367d1f44194ad",
    ),
    (7, 1101, 1116, "flow_branch_label"): (
        "flow_path",
        "rq-candidate-flow-path:7ffd8bc99ff35bdd411e21e8e28414b67dff7d1ba9f4d8aee7fcb74b5ebe67fe",
    ),
    (7, 1525, 1535, "flow_branch_label"): (
        "occurrence",
        "rq-candidate-occurrence:883685bca426310041f433d5eaa424abc47c644df04d3d90d96f45053d9c586b",
    ),
    (7, 1544, 1568, "flow_branch_label"): (
        "flow_path",
        "rq-candidate-flow-path:0baef04a89981fd6964acf100d2931e3e4bc09750cd246300a18910dcf444a54",
    ),
    (7, 1597, 1606, "flow_branch_label"): (
        "flow_path",
        "rq-candidate-flow-path:2f9fc34edb07fbab6e4190ce7939725601086b59c7d34ea2109f121d1dd027c0",
    ),
    (7, 1750, 1789, "flow_branch_label"): (
        "occurrence",
        "rq-candidate-occurrence:ba5b5a1501b90611a4d8d4ce1b94c8dac3fea0ef9dd9befa3a4977cd7cc2916a",
    ),
    (8, 148, 152, "flow_branch_label"): (
        "occurrence",
        "rq-candidate-occurrence:19ae883323b3eeb833795b38a82a36ab84e3194a0237e14010fab8b5dd197128",
    ),
    (8, 237, 241, "flow_branch_label"): (
        "occurrence",
        "rq-candidate-occurrence:8fc2110ef9517f2e4b2ae2324403b3b7634e8aea0cda34ebe6c16e4f00602b27",
    ),
    (8, 508, 514, "flow_branch_label"): (
        "occurrence",
        "rq-candidate-occurrence:50555b90e80cbce2c13e3375afe5937ef7678f066518a57430ebac1011a66e86",
    ),
    (8, 583, 587, "flow_branch_label"): (
        "occurrence",
        "rq-candidate-occurrence:d54fec0fd376142a4108f497c01f1f9ec9a38442d0c2bcac14ee51cb34b7642d",
    ),
    (8, 792, 796, "flow_branch_label"): (
        "occurrence",
        "rq-candidate-occurrence:60e0f903aca59b0b55b56cade462b9f30b9cae249f1def3efd880c112100ffe1",
    ),
    (8, 1012, 1016, "flow_branch_label"): (
        "occurrence",
        "rq-candidate-occurrence:9b89366701f29fa1500227d46d9899a261b8db432494e1b1bc34974c17e5ed97",
    ),
    (8, 2073, 2077, "flow_branch_label"): (
        "occurrence",
        "rq-candidate-occurrence:4f7d75f453a696a442f9a53d99ecfe8b0afca4f91c26e7098c39f82fc3520f6e",
    ),
    (9, 318, 334, "flow_branch_label"): (
        "occurrence",
        "rq-candidate-occurrence:99831b183d0545f7071181ca3c78661debafd7e64ca079a7a1bab85eb450fb84",
    ),
    (12, 108, 236, "flow_branch_label"): (
        "occurrence",
        "rq-candidate-occurrence:d95a70206136deea8d5c179674c0fab047965b6b021251d90b5231e83b5b75c1",
    ),
    (15, 180, 308, "flow_branch_label"): (
        "occurrence",
        "rq-candidate-occurrence:c851087c2020ddacd2fa3499dd7ffa7f1c336f663bac1378b0e4f1c65bcef62a",
    ),
    (16, 633, 725, "flow_branch_label"): (
        "occurrence",
        "rq-candidate-occurrence:1eac1d532e6b8bc02baa196ae64fed2aef6eb7fe3286b74c065f29faeb8d8453",
    ),
    (16, 1098, 1128, "flow_branch_label"): (
        "occurrence",
        "rq-candidate-occurrence:cb1d996541e2966c4fdba9e43f24bf13ead88a2e6e4611c699fbe64fe209a070",
    ),
    (21, 233, 254, "flow_branch_label"): (
        "occurrence",
        "rq-candidate-occurrence:b59efdb2fa37010c9fe419e2e31313bab0f1c5da846a161c09ebdf1b9a31168c",
    ),
    (21, 498, 515, "flow_branch_label"): (
        "occurrence",
        "rq-candidate-occurrence:16925b17c3b1400a7432fd5d2c5e68dc2dd0fe64e6f5264eb71cc37f52a45569",
    ),
    (21, 544, 566, "flow_branch_label"): (
        "occurrence",
        "rq-candidate-occurrence:c66b061c3a78d8ee7db58c60e451a5ae76fde45f059ca71f4725a0a212df1cfd",
    ),
    (21, 1420, 1426, "flow_branch_label"): (
        "occurrence",
        "rq-candidate-occurrence:7e00a9b075a2c1bb29f5a4c8a3cab4efb871a7d1181f14e2d761cd80e376c3b2",
    ),
    (21, 1446, 1464, "flow_branch_label"): (
        "flow_path",
        "rq-candidate-flow-path:b96a7cf9586a415f7a8b1945b9165b6de351e50e9d65bb098abc78453eaef402",
    ),
    (21, 1647, 1668, "flow_branch_label"): (
        "occurrence",
        "rq-candidate-occurrence:745b30a2f5fa5b43ebf10211495dbd6d045edc37214122b5016d3ac376b71017",
    ),
    (21, 1699, 1713, "flow_branch_label"): (
        "occurrence",
        "rq-candidate-occurrence:851bdd3beb8d34f76b269031caf0a1fc740cad5686ac52daf8450988ce0d9d90",
    ),
    (21, 1821, 1825, "flow_branch_label"): (
        "flow_path",
        "rq-candidate-flow-path:7bbe158b6f48780e66237f708526ebe2d9b212ae5566e5a9c126ece9ecbc6314",
    ),
    (21, 1969, 1979, "flow_branch_label"): (
        "flow_path",
        "rq-candidate-flow-path:5e86c73d1f51e60f75c585d81c4540f4d708022cf5a68f0a518073b79a4f6c52",
    ),
}
VISUAL_FIDELITY_NOTE_KEYS = frozenset(VISUAL_FIDELITY_NOTE_TARGETS.values())
VISUAL_FIDELITY_OCCURRENCE_CANDIDATE_IDS = frozenset(
    candidate_id
    for row_kind, candidate_id in VISUAL_FIDELITY_NOTE_KEYS
    if row_kind == "occurrence"
)
if (
    tuple(VISUAL_FIDELITY_NOTE_TARGETS) != VISUAL_FIDELITY_COORDINATES
    or len(VISUAL_FIDELITY_NOTE_KEYS) != 30
):
    raise ValueError("visual-fidelity diagnostic binding domain drift")

VISUAL_FIDELITY_INDIRECT_RATIONALES = {
    (7, 225, 253, "flow_branch_label"): "same Section D opening D1 screen",
    (
        7,
        527,
        610,
        "flow_branch_label",
    ): "same D1 status prompt and response screen",
    (
        7,
        626,
        640,
        "flow_branch_label",
    ): "same D1 response stack candidate path",
    (7, 1101, 1116, "flow_branch_label"): "same D1 OTHER route candidate path",
    (7, 1525, 1535, "flow_branch_label"): "same D3-D4 printed screen",
    (
        7,
        1544,
        1568,
        "flow_branch_label",
    ): "same D3-D4 printed screen candidate path",
    (
        7,
        1597,
        1606,
        "flow_branch_label",
    ): "same D3-D4 printed screen candidate path",
    (
        8,
        2073,
        2077,
        "flow_branch_label",
    ): "same D20 question and response screen",
    (
        9,
        318,
        334,
        "flow_branch_label",
    ): "same D24 question and response screen",
    (16, 633, 725, "flow_branch_label"): "same Section G opening G1 screen",
    (21, 233, 254, "flow_branch_label"): "same Section H opening H1 screen",
    (
        21,
        1821,
        1825,
        "flow_branch_label",
    ): "same H6 response stack candidate path",
    (
        21,
        1969,
        1979,
        "flow_branch_label",
    ): "same H6 response stack candidate path",
}
if len(VISUAL_FIDELITY_INDIRECT_RATIONALES) != 13:
    raise ValueError("visual-fidelity indirect binding rationale drift")

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


def _json_exact_equal(left: Any, right: Any) -> bool:
    """Compare JSON values without Python's bool/int/float coercion."""

    return _canonical_bytes(left) == _canonical_bytes(right)


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


def _require_nonbool_int(value: Any, label: str, minimum: int = 0) -> None:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{label} is not a lawful non-boolean integer")


def _validate_numeric_types(value: Mapping[str, Any]) -> None:
    """Enforce exact JSON integer types for every affected numeric field."""

    _require_nonbool_int(
        value["document_source_position"], "document source position", 1
    )
    locator = value["whole_document_locator"]
    for key, minimum in (
        ("interview_wave", 0),
        ("byte_start", 0),
        ("byte_end", 1),
        ("size_bytes", 1),
    ):
        _require_nonbool_int(locator[key], f"locator {key}", minimum)
    for page in value["questionnaire_page_rows"]:
        _require_nonbool_int(page["interview_wave"], "page interview wave")
        _require_nonbool_int(page["page_number"], "page number", 1)
    for occurrence in value["questionnaire_occurrence_rows"]:
        for key, minimum in (
            ("interview_wave", 0),
            ("page_number", 1),
            ("utf8_byte_start", 0),
            ("utf8_byte_end", 1),
            ("occurrence_index_on_page", 0),
            ("semantic_ordinal_at_span", 0),
        ):
            _require_nonbool_int(occurrence[key], f"occurrence {key}", minimum)
    for branch in value["flow_branch_rows"]:
        for key, minimum in (
            ("interview_wave", 0),
            ("page_number", 1),
            ("occurrence_index_on_page", 0),
        ):
            _require_nonbool_int(branch[key], f"flow branch {key}", minimum)

    sidecar = value["raster_only_incompleteness_census"]
    _require_nonbool_int(
        sidecar["branch_exception_count"],
        "raster branch exception count",
        1,
    )
    _require_nonbool_int(
        sidecar["dependent_atom_count"], "raster dependent atom count"
    )
    for record in sidecar["branch_exception_records"]:
        for key, minimum in (
            ("interview_wave", 0),
            ("page_number", 1),
            ("exception_index_on_page", 0),
        ):
            _require_nonbool_int(
                record[key], f"branch exception {key}", minimum
            )
    for record in sidecar["dependent_atom_consequence_records"]:
        for key, minimum in (
            ("interview_wave", 0),
            ("page_number", 1),
            ("utf8_byte_start", 0),
            ("utf8_byte_end", 1),
        ):
            _require_nonbool_int(record[key], f"dependent atom {key}", minimum)
        for blocker in record["blocking_exception_keys"]:
            if len(blocker) != 2:
                raise ValueError("blocking exception key shape drift")
            _require_nonbool_int(blocker[1], "blocking exception key index")
    for row in sidecar["page_census_rows"]:
        for key, minimum in (
            ("interview_wave", 0),
            ("page_number", 1),
            ("branch_exception_count", 0),
            ("dependent_atom_count", 0),
        ):
            _require_nonbool_int(row[key], f"page census {key}", minimum)
        for exception_key in row["branch_exception_keys"]:
            if len(exception_key) != 2:
                raise ValueError("page exception key shape drift")
            _require_nonbool_int(exception_key[1], "page exception key index")
        for dependent_key in row["dependent_atom_keys"]:
            if len(dependent_key) != 4:
                raise ValueError("page dependent key shape drift")
            _require_nonbool_int(
                dependent_key[1], "page dependent key byte start"
            )
            _require_nonbool_int(
                dependent_key[2], "page dependent key byte end", 1
            )
    seal = value["seal"]
    for key in (
        "whole_document_locator_count",
        "questionnaire_page_count",
        "empty_occurrence_page_count",
        "questionnaire_occurrence_count",
        "flow_branch_count",
        "local_anchor_classification_count",
        "local_repeat_alias_evidence_count",
        "candidate_disposition_count",
        "output_adjudication_count",
        "adjudication_note_count",
        "page_review_count",
        "raster_only_branch_exception_count",
        "raster_only_dependent_atom_consequence_count",
        "raster_only_page_census_count",
    ):
        _require_nonbool_int(seal[key], f"seal {key}")


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
        raise ValueError("document 6 candidate-index resolution drift")
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
        raise ValueError("document 6 Poppler version drift")
    page_texts = questionnaire_inventory._pdftotext_pages(source_path)
    expected = [
        row
        for row in replay["questionnaire_page_replay"][
            "questionnaire_page_rows"
        ]
        if row["source_document_id"] == document["source_document_id"]
    ]
    if len(page_texts) != 30 or len(page_texts) != len(expected):
        raise ValueError("document 6 page denominator drift")
    for page_text, page_row in zip(page_texts, expected, strict=True):
        page_bytes = page_text.encode("utf-8")
        if (
            len(page_bytes) != page_row["page_text_utf8_size_bytes"]
            or _sha256(page_bytes) != page_row["page_text_utf8_sha256"]
        ):
            raise ValueError("document 6 page replay drift")
    return page_texts


def _load_review(
    document: Mapping[str, Any], page_texts: Sequence[str]
) -> dict[str, Any]:
    review = _strict_json(REVIEW_PATH, "document 6 source review")
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
        raise ValueError("document 6 candidate raw identity drift")
    value = source_tools.strict_parse_document(raw, "document 6 candidates")
    if not isinstance(value, dict):
        raise ValueError("document 6 candidates are not an object")
    stage1_candidates.validate_document_candidates(value, replay, page_texts)
    if (
        value["integrity"]["content_sha256"] != identity["content_sha256"]
        or value["candidate_manifest"]["candidate_payload_sha256"]
        != identity["candidate_payload_sha256"]
    ):
        raise ValueError("document 6 candidate content identity drift")
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


def _review_branch_ref(
    review_occurrence_id: str,
    parent_review_path: Sequence[str],
    path_count: int,
) -> str:
    """Address one semantic branch when one printed label has many parents."""

    if path_count == 1:
        return review_occurrence_id
    return (
        f"{review_occurrence_id}#parent-path-"
        f"{_canonical_digest(list(parent_review_path))}"
    )


def _source_printed_identifier(
    page_text: str, byte_start: int, matched_text: str | None = None
) -> str | None:
    """Resolve the printed identifier an anchor's own bytes carry.

    The questionnaire scan renders two or three instrument columns onto one physical
    line, so a purely line-scoped lookup would attribute the leftmost
    column's printed identifier to every column on that line.  A span that
    begins inside its line therefore carries only an identifier it prints
    itself; a span that begins at the line start keeps the line lookup.
    """

    for line in stage1_candidates._physical_lines(page_text):
        line_byte_start = len(page_text[: line["start"]].encode("utf-8"))
        line_byte_end = len(page_text[: line["end"]].encode("utf-8"))
        if line_byte_start <= byte_start < line_byte_end:
            if matched_text is not None and byte_start > line_byte_start:
                return stage1_candidates._printed_identifier(matched_text)
            return stage1_candidates._printed_identifier(line["text"])
    raise ValueError(
        "source review occurrence does not resolve to a physical line"
    )


def _validate_alias_relation(relation: Any) -> None:
    """Reject inferred aliases even when a document has no alias rows."""

    if not isinstance(relation, str) or relation not in ALIAS_RELATIONS:
        raise ValueError("local repeat inferred an alias relation")


def validate_review(
    review: Mapping[str, Any],
    document: Mapping[str, Any],
    page_texts: Sequence[str],
) -> None:
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
            "global_ids_assigned",
        ),
        "source review method",
    )
    if method != {
        "source_rows_derived_from_page_bytes": True,
        "whole_page_review": "all_30_pages_including_empty_occurrence_pages",
        "span_granularity": "exact_utf8_lexeme_physical_line_or_source_block",
        "candidate_nonselection": "candidates_joined_only_after_source_rows_complete",
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
                "parent_review_branch_paths",
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
        paths = spec["parent_review_branch_paths"]
        if (
            not isinstance(paths, list)
            or not paths
            or any(not isinstance(path, list) for path in paths)
        ):
            raise ValueError("source review path domain drift")
        if len(paths) != len({tuple(path) for path in paths}):
            raise ValueError("source review duplicate applicable path")
        if spec["occurrence_kind"] == "flow_branch_label":
            if any(
                path and path[-1] == spec["review_occurrence_id"]
                for path in paths
            ):
                raise ValueError("source review branch cycle")
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
        last_order = order
    branch_specs = [
        spec
        for spec in occurrence_specs
        if spec["occurrence_kind"] == "flow_branch_label"
    ]
    branch_ref_to_spec: dict[str, tuple[Mapping[str, Any], int]] = {}
    for spec in branch_specs:
        review_id = spec["review_occurrence_id"]
        path_count = len(spec["parent_review_branch_paths"])
        for parent_review_path in spec["parent_review_branch_paths"]:
            branch_ref = _review_branch_ref(
                review_id, parent_review_path, path_count
            )
            branch_ref_to_spec[branch_ref] = (
                spec,
                spec["parent_review_branch_paths"].index(parent_review_path),
            )
    occurrence_order = {
        spec["review_occurrence_id"]: position
        for position, spec in enumerate(occurrence_specs)
    }
    for spec in occurrence_specs:
        for path in spec["parent_review_branch_paths"]:
            if any(
                branch_ref not in branch_ref_to_spec for branch_ref in path
            ):
                raise ValueError("source review path has unresolved branch")
            if spec["occurrence_kind"] == "flow_branch_label" and any(
                occurrence_order[
                    branch_ref_to_spec[branch_ref][0]["review_occurrence_id"]
                ]
                >= occurrence_order[spec["review_occurrence_id"]]
                for branch_ref in path
            ):
                raise ValueError("source review path has later branch")
            expected_prefix: list[str] = []
            for branch_ref in path:
                branch_spec, semantic_ordinal = branch_ref_to_spec[branch_ref]
                if (
                    branch_spec["parent_review_branch_paths"][semantic_ordinal]
                    != expected_prefix
                ):
                    raise ValueError("source review branch ancestry drift")
                expected_prefix = [*expected_prefix, branch_ref]

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
        anchor_matched_text: str | None = None
        if occurrence is not None:
            kind = occurrence["occurrence_kind"]
            _matched_bytes, anchor_matched_text = _utf8_slice(
                page_texts[occurrence["page_number"] - 1],
                occurrence["utf8_byte_start"],
                occurrence["utf8_byte_end"],
            )
            if kind == "role_anchor":
                expected_classification = (
                    "role",
                    stage1_candidates._role_classification(
                        anchor_matched_text
                    ),
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
                anchor_matched_text,
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
        _validate_alias_relation(row["relation"])
        occurrence = spec_by_id.get(row["review_occurrence_id"])
        alias_ids = row["alias_anchor_review_occurrence_ids"]
        canonical_ids = row["canonical_anchor_review_occurrence_ids"]
        evidence = row["evidence_review_occurrence_ids"]
        if (
            occurrence is None
            or occurrence["occurrence_kind"] != "repeat_or_alias_instruction"
            or row["review_occurrence_id"] in repeat_covered
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
    flow_paths: Sequence[Sequence[str]],
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
        [list(path) for path in flow_paths],
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


def _path_sort_key(path: Sequence[str]) -> tuple[bytes, ...]:
    return tuple(item.encode("utf-8") for item in path)


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
    final_branch_path_by_review_ref: dict[str, list[str]] = {}
    output_occurrence_ids_by_review_id: dict[str, list[str]] = defaultdict(
        list
    )
    output_branch_ids_by_review_id: dict[str, list[str]] = defaultdict(list)
    next_occurrence_index_by_page: dict[int, int] = defaultdict(int)
    prepared_specs: list[tuple[Mapping[str, Any], bytes, str, int]] = []
    occurrence_by_coordinate: dict[tuple[int, int], dict[str, Any]] = {}

    # Reserve every same-page index in source order before resolving paths.
    # A non-flow occurrence may lawfully reuse a screen reached by a routing
    # instruction printed later, while every branch label's own parent remains
    # earlier.  Reserving first breaks that source-layout dependency without
    # changing any occurrence index or ID preimage.
    for spec in review["occurrence_specs"]:
        page_number = spec["page_number"]
        matched_bytes, matched_text = _utf8_slice(
            page_texts[page_number - 1],
            spec["utf8_byte_start"],
            spec["utf8_byte_end"],
        )
        base_index = next_occurrence_index_by_page[page_number]
        coordinate = (
            page_number,
            spec["utf8_byte_start"],
            spec["utf8_byte_end"],
            spec["occurrence_kind"],
        )
        layout = PREFILTER_FLOW_LAYOUT_BY_COORDINATE.get(coordinate)
        dependency = DEPENDENCY_BY_COORDINATE.get(coordinate)
        if spec["occurrence_kind"] != "flow_branch_label":
            prefilter_count = 1
        elif layout is not None:
            prefilter_count = layout[0]
        elif (
            dependency is not None
            and dependency["path_consequence"] == WITHHELD_PATH_CONSEQUENCE
        ):
            prefilter_count = max(1, len(spec["parent_review_branch_paths"]))
        else:
            prefilter_count = len(spec["parent_review_branch_paths"])
        next_occurrence_index_by_page[page_number] += prefilter_count
        prepared_specs.append((spec, matched_bytes, matched_text, base_index))

    def resolve_path_rows(
        spec: Mapping[str, Any], *, sort_output_paths: bool = True
    ) -> list[tuple[list[str], list[str]]]:
        resolved_path_rows: list[tuple[list[str], list[str]]] = []
        for review_path in spec["parent_review_branch_paths"]:
            path = [FLOW_ROOT]
            for review_branch_ref in review_path:
                resolved = final_branch_path_by_review_ref.get(
                    review_branch_ref
                )
                if resolved is None or resolved[:-1] != path:
                    raise ValueError(
                        "source review branch path does not resolve"
                    )
                path = list(resolved)
            resolved_path_rows.append((path, review_path))
        if sort_output_paths:
            resolved_path_rows.sort(key=lambda row: _path_sort_key(row[0]))
        translated_paths = [row[0] for row in resolved_path_rows]
        if len(translated_paths) != len(
            {tuple(path) for path in translated_paths}
        ):
            raise ValueError("translated occurrence paths are duplicated")
        return resolved_path_rows

    # First resolve and emit only branch-label occurrences.  Their parent
    # branches are source-earlier, so this pass constructs the complete branch
    # reference map used by reused non-flow screens in the second pass.
    for spec, matched_bytes, matched_text, base_index in prepared_specs:
        if spec["occurrence_kind"] != "flow_branch_label":
            continue
        page_number = spec["page_number"]
        coordinate = (
            page_number,
            spec["utf8_byte_start"],
            spec["utf8_byte_end"],
            spec["occurrence_kind"],
        )
        dependency = DEPENDENCY_BY_COORDINATE.get(coordinate)
        if (
            dependency is not None
            and dependency["path_consequence"] == WITHHELD_PATH_CONSEQUENCE
        ):
            continue
        layout = PREFILTER_FLOW_LAYOUT_BY_COORDINATE.get(coordinate)
        resolved_path_rows = resolve_path_rows(
            spec, sort_output_paths=layout is None
        )
        semantic_ordinals = (
            tuple(range(len(resolved_path_rows)))
            if layout is None
            else layout[1]
        )
        if len(semantic_ordinals) != len(resolved_path_rows):
            raise ValueError("pre-filter resolving path projection drift")
        for semantic_ordinal, (
            parent_path,
            source_review_path,
        ) in zip(semantic_ordinals, resolved_path_rows, strict=True):
            skeleton = {
                "page_number": page_number,
                "utf8_byte_start": spec["utf8_byte_start"],
                "utf8_byte_end": spec["utf8_byte_end"],
                "occurrence_index_on_page": base_index + semantic_ordinal,
                "semantic_ordinal_at_span": semantic_ordinal,
                "occurrence_kind": spec["occurrence_kind"],
                "matched_text": matched_text,
                "matched_utf8_sha256": _sha256(matched_bytes),
            }
            occurrence = _occurrence_row(
                document, locator_id, skeleton, [parent_path]
            )
            occurrence_by_coordinate[
                (page_number, base_index + semantic_ordinal)
            ] = occurrence
            review_id = spec["review_occurrence_id"]
            output_occurrence_ids_by_review_id[review_id].append(
                occurrence["questionnaire_occurrence_id"]
            )
            parent_branch_id = parent_path[-1]
            branch_id = "questionnaire-flow:" + _canonical_digest(
                [
                    parent_branch_id,
                    document["interview_waves"][0],
                    occurrence["questionnaire_occurrence_id"],
                ]
            )
            branch_path = [*parent_path, branch_id]
            branch = dict(
                zip(
                    FLOW_BRANCH_KEYS,
                    (
                        branch_id,
                        parent_branch_id,
                        occurrence["questionnaire_occurrence_id"],
                        branch_path,
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
            output_branch_ids_by_review_id[review_id].append(branch_id)
            branch_ref = _review_branch_ref(
                review_id,
                source_review_path,
                len(spec["parent_review_branch_paths"]),
            )
            final_branch_path_by_review_ref[branch_ref] = branch_path

    # Now every branch reference exists, including later printed routes to a
    # reused screen.  Emit each non-flow atom once with its complete path set.
    for spec, matched_bytes, matched_text, base_index in prepared_specs:
        if spec["occurrence_kind"] == "flow_branch_label":
            continue
        page_number = spec["page_number"]
        coordinate = (
            page_number,
            spec["utf8_byte_start"],
            spec["utf8_byte_end"],
            spec["occurrence_kind"],
        )
        dependency = DEPENDENCY_BY_COORDINATE.get(coordinate)
        if (
            dependency is not None
            and dependency["path_consequence"] == WITHHELD_PATH_CONSEQUENCE
        ):
            continue
        resolved_path_rows = resolve_path_rows(spec)
        translated_paths = [row[0] for row in resolved_path_rows]
        skeleton = {
            "page_number": page_number,
            "utf8_byte_start": spec["utf8_byte_start"],
            "utf8_byte_end": spec["utf8_byte_end"],
            "occurrence_index_on_page": base_index,
            "semantic_ordinal_at_span": 0,
            "occurrence_kind": spec["occurrence_kind"],
            "matched_text": matched_text,
            "matched_utf8_sha256": _sha256(matched_bytes),
        }
        occurrence = _occurrence_row(
            document, locator_id, skeleton, translated_paths
        )
        occurrence_by_coordinate[(page_number, base_index)] = occurrence
        output_occurrence_ids_by_review_id[
            spec["review_occurrence_id"]
        ].append(occurrence["questionnaire_occurrence_id"])

    occurrences = [
        occurrence_by_coordinate[coordinate]
        for coordinate in sorted(occurrence_by_coordinate)
    ]
    return (
        occurrences,
        branches,
        dict(output_occurrence_ids_by_review_id),
        dict(output_branch_ids_by_review_id),
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


def _raster_only_incompleteness_census(
    document: Mapping[str, Any],
    page_texts: Sequence[str],
    pages: Sequence[Mapping[str, Any]],
    review: Mapping[str, Any],
    occurrence_ids_by_review_id: Mapping[str, Sequence[str]],
) -> dict[str, Any]:
    """Construct the ratified, sealed nonauthority census from source facts."""

    page_by_number = {row["page_number"]: row for row in pages}
    if list(page_by_number) != list(range(1, len(page_texts) + 1)):
        raise ValueError("raster census page domain drift")

    exception_records: list[dict[str, Any]] = []
    exception_key_by_ref: dict[tuple[int, int], list[Any]] = {}
    for (
        page_number,
        exception_index,
        description,
        location,
    ) in EXCEPTION_DEFINITIONS:
        page = page_by_number[page_number]
        record = dict(
            zip(
                BRANCH_EXCEPTION_KEYS,
                (
                    RASTER_REASON,
                    document["source_document_id"],
                    page["questionnaire_page_id"],
                    document["interview_waves"][0],
                    page_number,
                    page["page_text_utf8_sha256"],
                    exception_index,
                    description,
                    location,
                    "no_label_level_span_or_hash_emitted",
                ),
                strict=True,
            )
        )
        exception_records.append(record)
        exception_key_by_ref[(page_number, exception_index)] = [
            page["questionnaire_page_id"],
            exception_index,
        ]

    dependent_records: list[dict[str, Any]] = []
    seen_coordinates: set[tuple[int, int, int, str]] = set()
    for spec in review["occurrence_specs"]:
        coordinate = (
            spec["page_number"],
            spec["utf8_byte_start"],
            spec["utf8_byte_end"],
            spec["occurrence_kind"],
        )
        dependency = DEPENDENCY_BY_COORDINATE.get(coordinate)
        if dependency is None:
            continue
        if coordinate in seen_coordinates:
            raise ValueError("raster dependent atom coordinate duplicated")
        seen_coordinates.add(coordinate)
        page_number, start, end, occurrence_kind = coordinate
        page = page_by_number[page_number]
        matched_bytes, matched_text = _utf8_slice(
            page_texts[page_number - 1], start, end
        )
        emitted_ids = list(
            occurrence_ids_by_review_id.get(spec["review_occurrence_id"], ())
        )
        path_consequence = dependency["path_consequence"]
        if (
            path_consequence == EMITTED_PATH_CONSEQUENCE
            and not emitted_ids
            or path_consequence == WITHHELD_PATH_CONSEQUENCE
            and emitted_ids
        ):
            raise ValueError("raster dependent output projection drift")
        dependent_records.append(
            dict(
                zip(
                    DEPENDENT_ATOM_KEYS,
                    (
                        RASTER_REASON,
                        document["source_document_id"],
                        page["questionnaire_page_id"],
                        document["interview_waves"][0],
                        page_number,
                        page["page_text_utf8_sha256"],
                        start,
                        end,
                        occurrence_kind,
                        matched_text,
                        _sha256(matched_bytes),
                        [
                            exception_key_by_ref[exception_ref]
                            for exception_ref in dependency[
                                "blocking_exception_refs"
                            ]
                        ],
                        emitted_ids,
                        path_consequence,
                    ),
                    strict=True,
                )
            )
        )
    if seen_coordinates != set(DEPENDENCY_BY_COORDINATE):
        raise ValueError("raster dependent atom domain is not exact-covered")

    branch_keys_by_page: dict[int, list[list[Any]]] = defaultdict(list)
    for record in exception_records:
        branch_keys_by_page[record["page_number"]].append(
            [
                record["questionnaire_page_id"],
                record["exception_index_on_page"],
            ]
        )
    dependent_keys_by_page: dict[int, list[list[Any]]] = defaultdict(list)
    for record in dependent_records:
        dependent_keys_by_page[record["page_number"]].append(
            [
                record["questionnaire_page_id"],
                record["utf8_byte_start"],
                record["utf8_byte_end"],
                record["occurrence_kind"],
            ]
        )

    page_census_rows: list[dict[str, Any]] = []
    for page in pages:
        page_number = page["page_number"]
        branch_keys = branch_keys_by_page.get(page_number, [])
        dependent_keys = dependent_keys_by_page.get(page_number, [])
        page_census_rows.append(
            dict(
                zip(
                    PAGE_CENSUS_KEYS,
                    (
                        page["questionnaire_page_id"],
                        page["source_document_id"],
                        page["interview_wave"],
                        page_number,
                        page["page_text_utf8_sha256"],
                        len(branch_keys),
                        branch_keys,
                        len(dependent_keys),
                        dependent_keys,
                    ),
                    strict=True,
                )
            )
        )

    if len(exception_records) != 16 or len(dependent_records) != 38:
        raise ValueError("raster census N/M drift")
    return dict(
        zip(
            RASTER_SIDECAR_KEYS,
            (
                "rq_stage2_raster_only_incompleteness_census_nonauthority.v1",
                "sealed_nonauthority_sidecar",
                "complete-under-extraction-authority with 16 raster-only exceptions",
                "CLOSED GAP",
                RASTER_REASON,
                len(exception_records),
                len(dependent_records),
                exception_records,
                dependent_records,
                page_census_rows,
                "fail_or_withhold_exhaustive_flow_outputs_without_global_gap_rows_nodes_or_ids",
                "complete",
            ),
            strict=True,
        )
    )


def _raster_seal_fields(sidecar: Mapping[str, Any]) -> dict[str, Any]:
    branch_records = sidecar["branch_exception_records"]
    dependent_records = sidecar["dependent_atom_consequence_records"]
    page_rows = sidecar["page_census_rows"]
    branch_keys = [
        [row["questionnaire_page_id"], row["exception_index_on_page"]]
        for row in branch_records
    ]
    dependent_keys = [
        [
            row["questionnaire_page_id"],
            row["utf8_byte_start"],
            row["utf8_byte_end"],
            row["occurrence_kind"],
        ]
        for row in dependent_records
    ]
    page_keys = [[row["questionnaire_page_id"]] for row in page_rows]
    return dict(
        zip(
            RASTER_SEAL_KEYS,
            (
                len(branch_records),
                _canonical_digest(branch_keys),
                _canonical_digest(list(branch_records)),
                len(dependent_records),
                _canonical_digest(dependent_keys),
                _canonical_digest(list(dependent_records)),
                len(page_rows),
                _canonical_digest(page_keys),
                _canonical_digest(list(page_rows)),
                _canonical_digest(sidecar),
            ),
            strict=True,
        )
    )


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
        output_ids = occurrence_ids_by_review_id.get(
            spec["review_occurrence_id"], ()
        )
        if not output_ids:
            continue
        if len(output_ids) != 1:
            raise ValueError(
                "local anchor cannot resolve a multi-parent label"
            )
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
            values.extend(occurrence_ids_by_review_id.get(review_id, ()))
        return values

    for spec in review["repeat_alias_specs"]:
        source_ids = resolve([spec["review_occurrence_id"]])
        if not source_ids:
            continue
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


def _apply_visual_fidelity_notes(notes: list[dict[str, Any]]) -> None:
    note_by_key = {
        (row["candidate_row_kind"], row["candidate_id"]): row for row in notes
    }
    if len(note_by_key) != len(notes):
        raise ValueError("adjudication note candidate domain duplicated")
    missing = VISUAL_FIDELITY_NOTE_KEYS - set(note_by_key)
    if missing:
        raise ValueError("visual-fidelity diagnostic has no existing note")
    for key in VISUAL_FIDELITY_NOTE_KEYS:
        row = note_by_key[key]
        row["note_code"] = VISUAL_FIDELITY_NOTE_CODE
        row["note"] = VISUAL_FIDELITY_NOTE
    actual = {
        key
        for key, row in note_by_key.items()
        if row["note_code"] == VISUAL_FIDELITY_NOTE_CODE
        or row["note"] == VISUAL_FIDELITY_NOTE
    }
    if actual != VISUAL_FIDELITY_NOTE_KEYS:
        raise ValueError("visual-fidelity diagnostic domain drift")


def _validate_visual_fidelity_note_targets(
    candidates: Mapping[str, Any],
) -> None:
    occurrence_by_id = {
        row["candidate_occurrence_id"]: row
        for row in candidates["candidate_occurrence_rows"]
    }
    flow_by_id = {
        row["candidate_flow_path_id"]: row
        for row in candidates["candidate_flow_path_rows"]
    }
    indirect: set[tuple[int, int, int, str]] = set()
    for target, (
        row_kind,
        candidate_id,
    ) in VISUAL_FIDELITY_NOTE_TARGETS.items():
        if row_kind == "occurrence":
            carrier = occurrence_by_id.get(candidate_id)
        elif row_kind == "flow_path":
            flow = flow_by_id.get(candidate_id)
            carrier = (
                None
                if flow is None
                else occurrence_by_id.get(
                    flow["source_candidate_occurrence_id"]
                )
            )
        else:
            raise ValueError("visual-fidelity carrier kind drift")
        if carrier is None or carrier["page_number"] != target[0]:
            raise ValueError("visual-fidelity carrier page mapping drift")
        overlaps = (
            carrier["utf8_byte_start"] < target[2]
            and target[1] < carrier["utf8_byte_end"]
        )
        if not overlaps:
            indirect.add(target)
    if indirect != set(VISUAL_FIDELITY_INDIRECT_RATIONALES) or any(
        not reason for reason in VISUAL_FIDELITY_INDIRECT_RATIONALES.values()
    ):
        raise ValueError("visual-fidelity indirect carrier domain drift")


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


def _translated_candidate_parent_paths(
    candidate_flow: Mapping[str, Any],
    candidate_branch_source: Mapping[str, str],
    candidate_occurrence_outputs: Mapping[str, Sequence[str]],
    branches_by_source_occurrence_id: Mapping[
        str, Sequence[Mapping[str, Any]]
    ],
) -> list[list[str]]:
    translated_paths = [[FLOW_ROOT]]
    for candidate_branch_id in candidate_flow["candidate_parent_path"][1:]:
        source_candidate_id = candidate_branch_source.get(candidate_branch_id)
        if source_candidate_id is None:
            return []
        output_occurrence_ids = candidate_occurrence_outputs.get(
            source_candidate_id, []
        )
        candidate_branches = [
            branch
            for output_id in output_occurrence_ids
            for branch in branches_by_source_occurrence_id.get(output_id, [])
        ]
        next_paths: list[list[str]] = []
        for translated in translated_paths:
            next_paths.extend(
                list(branch["branch_path"])
                for branch in candidate_branches
                if branch["branch_path"][:-1] == translated
            )
        translated_paths = next_paths
        if not translated_paths:
            return []
    return translated_paths


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

    _validate_visual_fidelity_note_targets(candidates)

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
    for candidate_id in VISUAL_FIDELITY_OCCURRENCE_CANDIDATE_IDS:
        if occurrence_candidate_disposition.get(candidate_id) == "accepted":
            occurrence_candidate_disposition[candidate_id] = "modified"
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
            note_code = "semantic_false_positive_after_whole_page_review"
            note = (
                f"Page {candidate['page_number']} source review rejected "
                f"the {candidate['occurrence_kind_candidate']} candidate; "
                "the exact slice does not enter that document-local "
                "section-19 occurrence-kind projection."
            )
            notes.append(
                _note_row(
                    "occurrence",
                    candidate_id,
                    note_code,
                    note,
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

    branches_by_source_occurrence_id: dict[str, list[Mapping[str, Any]]] = (
        defaultdict(list)
    )
    for row in branches:
        branches_by_source_occurrence_id[row["source_occurrence_id"]].append(
            row
        )
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
            branch
            for output_id in output_occurrence_ids
            for branch in branches_by_source_occurrence_id.get(output_id, [])
        ]
        unclaimed_branch_ids = {
            branch["flow_branch_id"] for branch in output_branches
        }
        # Prefer a candidate whose complete source ancestry translates exactly.
        # A single candidate path may legitimately split into several semantic
        # branch rows when one printed label applies on several complete paths.
        for candidate in flow_candidates:
            translated_parent_paths = _translated_candidate_parent_paths(
                candidate,
                candidate_branch_source,
                candidate_occurrence_outputs,
                branches_by_source_occurrence_id,
            )
            matching = [
                branch["flow_branch_id"]
                for branch in output_branches
                if branch["flow_branch_id"] in unclaimed_branch_ids
                and branch["branch_path"][:-1] in translated_parent_paths
            ]
            candidate_id = candidate["candidate_flow_path_id"]
            for branch_id in matching:
                flow_candidate_to_branches[candidate_id].append(branch_id)
                flow_branch_to_candidates[branch_id].append(candidate_id)
                flow_assignment_is_exact[(candidate_id, branch_id)] = True
                unclaimed_branch_ids.remove(branch_id)

        # A root-fallback candidate is source evidence for any retained labels
        # left after exact ancestry matching, but its path must be corrected.
        fallback = next(
            (
                row
                for row in flow_candidates
                if row["basis_rule_id"] == "root_fallback_v1"
                and not flow_candidate_to_branches[
                    row["candidate_flow_path_id"]
                ]
            ),
            None,
        )
        if fallback is not None:
            candidate_id = fallback["candidate_flow_path_id"]
            for branch_id in [
                branch["flow_branch_id"]
                for branch in output_branches
                if branch["flow_branch_id"] in unclaimed_branch_ids
            ]:
                flow_candidate_to_branches[candidate_id].append(branch_id)
                flow_branch_to_candidates[branch_id].append(candidate_id)
                flow_assignment_is_exact[(candidate_id, branch_id)] = False
            unclaimed_branch_ids.clear()

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
                    "candidate_path_not_selected_by_source_ancestry",
                    "The complete source review rejected this alternative path or its source label.",
                )
            )
        elif disposition in {"modified", "split"}:
            notes.append(
                _note_row(
                    "flow_path",
                    candidate_id,
                    "candidate_path_corrected_to_resolved_stage2_ancestry",
                    "The source label was retained with independently resolved stage-2 branch ancestry and semantic path multiplicity.",
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

    _apply_visual_fidelity_notes(notes)
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
    sidecar: Mapping[str, Any],
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
    result = {
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
    result.update(_raster_seal_fields(sidecar))
    return result


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
    sidecar = _raster_only_incompleteness_census(
        document,
        page_texts,
        pages,
        review,
        occurrence_ids_by_review_id,
    )
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
        sidecar,
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
        "raster_only_incompleteness_census": sidecar,
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
        if (
            expected_disposition == "accepted"
            and candidate_id in VISUAL_FIDELITY_OCCURRENCE_CANDIDATE_IDS
        ):
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
    diagnostic_rows = {
        (row["candidate_row_kind"], row["candidate_id"]): row
        for row in notes
        if row["note_code"] == VISUAL_FIDELITY_NOTE_CODE
        or row["note"] == VISUAL_FIDELITY_NOTE
    }
    if set(diagnostic_rows) != VISUAL_FIDELITY_NOTE_KEYS:
        raise ValueError("visual-fidelity diagnostic exact domain drift")
    if any(
        row["note_code"] != VISUAL_FIDELITY_NOTE_CODE
        or row["note"] != VISUAL_FIDELITY_NOTE
        for row in diagnostic_rows.values()
    ):
        raise ValueError("visual-fidelity diagnostic text drift")


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
        ordinals = [row["semantic_ordinal_at_span"] for row in same_span]
        first = same_span[0]
        coordinate = (
            first["page_number"],
            first["utf8_byte_start"],
            first["utf8_byte_end"],
            first["occurrence_kind"],
        )
        layout = PREFILTER_FLOW_LAYOUT_BY_COORDINATE.get(coordinate)
        expected_ordinals = (
            list(range(len(same_span))) if layout is None else list(layout[1])
        )
        if len(same_span) == 1 and ordinals == expected_ordinals:
            continue
        if any(len(row["flow_branch_paths"]) != 1 for row in same_span):
            raise ValueError("multi-parent label semantic path-count drift")
        parent_paths = [row["flow_branch_paths"][0] for row in same_span]
        if (
            any(
                row["occurrence_kind"] != "flow_branch_label"
                for row in same_span
            )
            or ordinals != expected_ordinals
            or layout is None
            and parent_paths != sorted(parent_paths, key=_path_sort_key)
        ):
            raise ValueError("multi-parent label semantic ordinal drift")
    resolved_paths: set[tuple[str, ...]] = {(FLOW_ROOT,)}
    last_branch_occurrence_position = -1
    for branch in branches:
        _expect_keys(branch, FLOW_BRANCH_KEYS, "flow branch")
        occurrence = occurrence_by_id.get(branch["source_occurrence_id"])
        parent_path = branch["branch_path"][:-1]
        expected_id = (
            None
            if occurrence is None
            else "questionnaire-flow:"
            + _canonical_digest(
                [
                    branch["parent_flow_branch_id"],
                    branch["interview_wave"],
                    branch["source_occurrence_id"],
                ]
            )
        )
        if (
            occurrence is None
            or occurrence["occurrence_kind"] != "flow_branch_label"
            or branch["flow_branch_id"] != expected_id
            or branch["flow_branch_id"] in branch_by_id
            or branch["source_occurrence_id"] in branch_by_occurrence
            or tuple(parent_path) not in resolved_paths
            or parent_path[-1] != branch["parent_flow_branch_id"]
            or branch["branch_path"]
            != [*occurrence["flow_branch_paths"][0], branch["flow_branch_id"]]
            or branch["interview_wave"] != occurrence["interview_wave"]
            or branch["source_locator_id"] != occurrence["source_locator_id"]
            or branch["page_number"] != occurrence["page_number"]
            or branch["occurrence_index_on_page"]
            != occurrence["occurrence_index_on_page"]
            or branch["branch_label"] != occurrence["matched_text"]
            or branch["branch_label_sha256"]
            != occurrence["matched_utf8_sha256"]
            or branch["flow_branch_id"] in parent_path
            or occurrence_position[branch["source_occurrence_id"]]
            <= last_branch_occurrence_position
        ):
            raise ValueError("flow branch ancestry or identity drift")
        last_branch_occurrence_position = occurrence_position[
            branch["source_occurrence_id"]
        ]
        branch_by_id[branch["flow_branch_id"]] = branch
        branch_by_occurrence[branch["source_occurrence_id"]] = branch
        resolved_paths.add(tuple(branch["branch_path"]))
    flow_label_ids = {
        row["questionnaire_occurrence_id"]
        for row in occurrences
        if row["occurrence_kind"] == "flow_branch_label"
    }
    if set(branch_by_occurrence) != flow_label_ids:
        raise ValueError("flow label/branch one-to-one cover drift")
    for occurrence in occurrences:
        paths = occurrence["flow_branch_paths"]
        if (
            not paths
            or paths != sorted(paths, key=_path_sort_key)
            or len(paths) != len({tuple(path) for path in paths})
            or any(tuple(path) not in resolved_paths for path in paths)
            or occurrence["occurrence_kind"] == "flow_branch_label"
            and len(paths) != 1
        ):
            raise ValueError("occurrence flow path drift")
        for path in paths:
            previous_position = -1
            for branch_id in path[1:]:
                branch = branch_by_id.get(branch_id)
                if branch is None:
                    raise ValueError("occurrence flow path unresolved")
                position = occurrence_position[branch["source_occurrence_id"]]
                if position <= previous_position:
                    raise ValueError("occurrence flow path cycle")
                previous_position = position


def _path_is_prefix(prefix: Sequence[str], path: Sequence[str]) -> bool:
    return len(prefix) <= len(path) and list(prefix) == list(
        path[: len(prefix)]
    )


def _branch_compatible(
    occurrences: Sequence[Mapping[str, Any]],
    resolved_paths: Sequence[Sequence[str]],
) -> bool:
    """Return only the section-19 existential compatibility Boolean."""

    if (
        not occurrences
        or len({row["interview_wave"] for row in occurrences}) != 1
    ):
        return False
    return any(
        all(
            any(
                _path_is_prefix(occurrence_path, possible_path)
                for occurrence_path in occurrence["flow_branch_paths"]
            )
            for occurrence in occurrences
        )
        for possible_path in resolved_paths
    )


def _validate_compatibility_predicate() -> None:
    root = [FLOW_ROOT]
    left = [FLOW_ROOT, "questionnaire-flow:left"]
    right = [FLOW_ROOT, "questionnaire-flow:right"]
    left_child = [*left, "questionnaire-flow:left-child"]
    domain = [root, left, left_child, right]
    root_row = {"interview_wave": 1970, "flow_branch_paths": [root]}
    left_or_right = {
        "interview_wave": 1970,
        "flow_branch_paths": [left, right],
    }
    left_row = {"interview_wave": 1970, "flow_branch_paths": [left]}
    right_row = {"interview_wave": 1970, "flow_branch_paths": [right]}
    other_wave = {"interview_wave": 1971, "flow_branch_paths": [left]}
    if (
        not _branch_compatible([root_row, left_row], domain)
        or not _branch_compatible([left_or_right, left_row], domain)
        or _branch_compatible([left_row, right_row], domain)
        or _branch_compatible([left_row, other_wave], domain)
    ):
        raise ValueError("branch compatibility predicate drift")


def _validate_local_anchor_laws(value: Mapping[str, Any]) -> None:
    occurrence_by_id = {
        row["questionnaire_occurrence_id"]: row
        for row in value["questionnaire_occurrence_rows"]
    }
    resolved_paths = [
        [FLOW_ROOT],
        *[row["branch_path"] for row in value["flow_branch_rows"]],
    ]
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
            and not _branch_compatible([source, *parents], resolved_paths)
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


def _contains_forbidden_global_id(value: Any) -> bool:
    if isinstance(value, str):
        return value.startswith(FORBIDDEN_GLOBAL_ID_PREFIXES)
    if isinstance(value, Mapping):
        return any(
            _contains_forbidden_global_id(key)
            or _contains_forbidden_global_id(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_forbidden_global_id(child) for child in value)
    return False


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
    _expect_keys(value, LEGACY_AFFECTED_TOP_LEVEL_KEYS, "document annotation")
    _expect_keys(
        value["seal"],
        (*LEGACY_FLAT_SEAL_KEYS, *RASTER_SEAL_KEYS),
        "document annotation seal",
    )
    _validate_numeric_types(value)
    if (
        value["schema_version"] != SCHEMA_VERSION
        or value["authority_kind"] != AUTHORITY_KIND
        or value["document_source_position"] != DOCUMENT_SOURCE_POSITION
        or not _json_exact_equal(value["document_source_row"], document)
        or not _json_exact_equal(
            value["source_replay_identity"],
            stage1_candidates.source_replay_identity(),
        )
        or value["status"] != STATUS
        or not _json_exact_equal(
            value["integrity"],
            {
                "canonicalization": CANONICALIZATION,
                "content_sha256": _content_sha256(value),
            },
        )
        or not _json_exact_equal(
            value["nonauthority_statement"],
            {
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
        )
    ):
        raise ValueError("document annotation identity or nonauthority drift")
    if _contains_forbidden_global_id(value):
        raise ValueError("document annotation emitted a forbidden global ID")

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
    sidecar = _raster_only_incompleteness_census(
        document,
        page_texts,
        pages,
        review,
        occurrence_ids_by_review_id,
    )
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
        ("raster_only_incompleteness_census", sidecar),
        ("output_adjudication_rows", output_adjudications),
    )
    for key, expected in expected_arrays:
        if not _json_exact_equal(value[key], expected):
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
        sidecar,
    )
    if (
        value["artifact_id"] != expected_artifact_id
        or not _json_exact_equal(
            value["candidate_index_identity"],
            expected_candidate_index_identity,
        )
        or not _json_exact_equal(
            value["candidate_artifact_identity"],
            expected_candidate_artifact_identity,
        )
        or not _json_exact_equal(
            value["source_review_identity"], expected_review_identity
        )
        or not _json_exact_equal(value["seal"], expected_seal)
    ):
        raise ValueError("document annotation artifact ID or seal drift")

    submitted_sidecar = value["raster_only_incompleteness_census"]
    _expect_keys(submitted_sidecar, RASTER_SIDECAR_KEYS, "raster sidecar")
    for row in submitted_sidecar["branch_exception_records"]:
        _expect_keys(row, BRANCH_EXCEPTION_KEYS, "raster branch exception")
    for row in submitted_sidecar["dependent_atom_consequence_records"]:
        _expect_keys(row, DEPENDENT_ATOM_KEYS, "raster dependent atom")
    for row in submitted_sidecar["page_census_rows"]:
        _expect_keys(row, PAGE_CENSUS_KEYS, "raster page census")
    submitted_raster_seal = {
        key: value["seal"][key] for key in RASTER_SEAL_KEYS
    }
    if not _json_exact_equal(
        submitted_raster_seal, _raster_seal_fields(submitted_sidecar)
    ):
        raise ValueError("submitted raster sidecar seal drift")

    for row in value["questionnaire_page_rows"]:
        _expect_keys(row, PAGE_KEYS, "questionnaire page")
    for row in value["questionnaire_occurrence_rows"]:
        _expect_keys(row, OCCURRENCE_KEYS, "questionnaire occurrence")
    for row in value["flow_branch_rows"]:
        _expect_keys(row, FLOW_BRANCH_KEYS, "flow branch")
    for row in value["local_anchor_classification_rows"]:
        _expect_keys(row, LOCAL_ANCHOR_KEYS, "local anchor")
    for row in value["local_repeat_alias_evidence_rows"]:
        _expect_keys(row, LOCAL_REPEAT_KEYS, "local repeat evidence")
        _validate_alias_relation(row["relation"])
    _validate_compatibility_predicate()
    _validate_flow_laws(value)
    _validate_local_anchor_laws(value)
    if _contains_witness_key(value):
        raise ValueError("compatibility witness was serialized")
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

    def select_path_subset(row: dict[str, Any]) -> None:
        """Replace a lawful path set with a proper subset of itself.

        Prefer a true multi-path occurrence when the source review contains
        one; otherwise truncate a conditional occurrence to the bare root.
        Either mutation removes part of the reviewed path evidence and must
        be rejected.
        """

        for occurrence in row["questionnaire_occurrence_rows"]:
            if len(occurrence["flow_branch_paths"]) > 1:
                occurrence["flow_branch_paths"] = occurrence[
                    "flow_branch_paths"
                ][:-1]
                return
        for occurrence in row["questionnaire_occurrence_rows"]:
            paths = occurrence["flow_branch_paths"]
            if len(paths) == 1 and len(paths[0]) > 1:
                occurrence["flow_branch_paths"] = [paths[0][:1]]
                return
        raise ValueError("mutation fixture has no conditional occurrence")

    def reverse_members(row: dict[str, Any], key: str) -> None:
        row[key] = dict(reversed(list(row[key].items())))

    def reverse_first_record_members(row: dict[str, Any], domain: str) -> None:
        sidecar = row["raster_only_incompleteness_census"]
        sidecar[domain][0] = dict(reversed(list(sidecar[domain][0].items())))

    def mutate_first_emitted_projection(row: dict[str, Any]) -> None:
        records = row["raster_only_incompleteness_census"][
            "dependent_atom_consequence_records"
        ]
        target = next(
            record
            for record in records
            if record["emitted_questionnaire_occurrence_ids"]
        )
        target["emitted_questionnaire_occurrence_ids"].pop()

    def mutate_first_blocking_order(row: dict[str, Any]) -> None:
        records = row["raster_only_incompleteness_census"][
            "dependent_atom_consequence_records"
        ]
        target = next(
            record
            for record in records
            if len(record["blocking_exception_keys"]) > 1
        )
        target["blocking_exception_keys"].reverse()

    def section_f_occurrence(row: dict[str, Any]) -> dict[str, Any]:
        return next(
            occurrence
            for occurrence in row["questionnaire_occurrence_rows"]
            if occurrence["page_number"] == 15
            and occurrence["utf8_byte_start"] == 180
            and occurrence["utf8_byte_end"] == 308
            and occurrence["occurrence_kind"] == "flow_branch_label"
        )

    def add_extra_branch_exception(row: dict[str, Any]) -> None:
        records = row["raster_only_incompleteness_census"][
            "branch_exception_records"
        ]
        extra = copy.deepcopy(records[-1])
        extra["exception_index_on_page"] += 1
        records.append(extra)

    def add_extra_dependent_atom(row: dict[str, Any]) -> None:
        records = row["raster_only_incompleteness_census"][
            "dependent_atom_consequence_records"
        ]
        extra = copy.deepcopy(records[-1])
        extra["utf8_byte_end"] += 1
        records.append(extra)

    def add_extra_census_page(row: dict[str, Any]) -> None:
        records = row["raster_only_incompleteness_census"]["page_census_rows"]
        extra = copy.deepcopy(records[-1])
        extra["questionnaire_page_id"] = "psid-questionnaire-page:extra"
        extra["page_number"] += 1
        records.append(extra)

    def add_root_as_branch_row(row: dict[str, Any]) -> None:
        root_row = copy.deepcopy(row["flow_branch_rows"][0])
        root_row["flow_branch_id"] = FLOW_ROOT
        root_row["parent_flow_branch_id"] = FLOW_ROOT
        root_row["branch_path"] = [FLOW_ROOT]
        row["flow_branch_rows"].insert(0, root_row)

    def visual_note(row: dict[str, Any]) -> dict[str, Any]:
        return next(
            note
            for note in row["adjudication_note_rows"]
            if note["note_code"] == VISUAL_FIDELITY_NOTE_CODE
        )

    def emitted_visual_occurrence(row: dict[str, Any]) -> dict[str, Any]:
        targets = set(VISUAL_FIDELITY_COORDINATES)
        return next(
            occurrence
            for occurrence in row["questionnaire_occurrence_rows"]
            if (
                occurrence["page_number"],
                occurrence["utf8_byte_start"],
                occurrence["utf8_byte_end"],
                occurrence["occurrence_kind"],
            )
            in targets
        )

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
                "parent_flow_branch_id", "questionnaire-flow:" + "f" * 64
            ),
        )
        add(
            "later_parent",
            lambda row: row["flow_branch_rows"][0].__setitem__(
                "parent_flow_branch_id",
                row["flow_branch_rows"][-1]["flow_branch_id"],
            ),
        )
        add(
            "cyclic_branch",
            lambda row: row["flow_branch_rows"][0]["branch_path"].append(
                row["flow_branch_rows"][0]["flow_branch_id"]
            ),
        )
        add("omitted_label", lambda row: row["flow_branch_rows"].pop())
        add(
            "duplicate_label",
            lambda row: row["flow_branch_rows"].append(
                copy.deepcopy(row["flow_branch_rows"][0])
            ),
        )
        add(
            "selected_path_subset",
            select_path_subset,
        )
        add("root_sentinel_as_branch_row", add_root_as_branch_row)
    if value["local_repeat_alias_evidence_rows"]:
        add(
            "inferred_alias",
            lambda row: row["local_repeat_alias_evidence_rows"][0].__setitem__(
                "relation", "inferred_synonym"
            ),
        )
    if value["local_anchor_classification_rows"]:
        add(
            "forbidden_global_relationship_id",
            lambda row: row["local_anchor_classification_rows"][0].__setitem__(
                "local_anchor_classification_id",
                "psid-questionnaire-relationship:" + "0" * 64,
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
    add(
        "missing_outer_sidecar",
        lambda row: row.pop("raster_only_incompleteness_census"),
    )
    add(
        "missing_sidecar_member",
        lambda row: row["raster_only_incompleteness_census"].pop("status"),
    )
    add(
        "extra_sidecar_member",
        lambda row: row["raster_only_incompleteness_census"].__setitem__(
            "extra", None
        ),
    )
    add(
        "reordered_sidecar_members",
        lambda row: reverse_members(row, "raster_only_incompleteness_census"),
    )
    add(
        "missing_branch_exception",
        lambda row: row["raster_only_incompleteness_census"][
            "branch_exception_records"
        ].pop(),
    )
    add(
        "duplicate_branch_exception",
        lambda row: row["raster_only_incompleteness_census"][
            "branch_exception_records"
        ].append(
            copy.deepcopy(
                row["raster_only_incompleteness_census"][
                    "branch_exception_records"
                ][0]
            )
        ),
    )
    add("extra_branch_exception", add_extra_branch_exception)
    add(
        "reordered_branch_exceptions",
        lambda row: row["raster_only_incompleteness_census"][
            "branch_exception_records"
        ].__setitem__(
            slice(0, 2),
            list(
                reversed(
                    row["raster_only_incompleteness_census"][
                        "branch_exception_records"
                    ][:2]
                )
            ),
        ),
    )
    add(
        "reordered_branch_exception_members",
        lambda row: reverse_first_record_members(
            row, "branch_exception_records"
        ),
    )
    add(
        "missing_dependent_atom",
        lambda row: row["raster_only_incompleteness_census"][
            "dependent_atom_consequence_records"
        ].pop(),
    )
    add(
        "duplicate_dependent_atom",
        lambda row: row["raster_only_incompleteness_census"][
            "dependent_atom_consequence_records"
        ].append(
            copy.deepcopy(
                row["raster_only_incompleteness_census"][
                    "dependent_atom_consequence_records"
                ][0]
            )
        ),
    )
    add("extra_dependent_atom", add_extra_dependent_atom)
    add(
        "reordered_dependent_atoms",
        lambda row: row["raster_only_incompleteness_census"][
            "dependent_atom_consequence_records"
        ].__setitem__(
            slice(0, 2),
            list(
                reversed(
                    row["raster_only_incompleteness_census"][
                        "dependent_atom_consequence_records"
                    ][:2]
                )
            ),
        ),
    )
    add(
        "reordered_dependent_atom_members",
        lambda row: reverse_first_record_members(
            row, "dependent_atom_consequence_records"
        ),
    )
    add(
        "missing_census_page",
        lambda row: row["raster_only_incompleteness_census"][
            "page_census_rows"
        ].pop(),
    )
    add(
        "duplicate_census_page",
        lambda row: row["raster_only_incompleteness_census"][
            "page_census_rows"
        ].append(
            copy.deepcopy(
                row["raster_only_incompleteness_census"]["page_census_rows"][0]
            )
        ),
    )
    add("extra_census_page", add_extra_census_page)
    add(
        "reordered_census_pages",
        lambda row: row["raster_only_incompleteness_census"][
            "page_census_rows"
        ].__setitem__(
            slice(0, 2),
            list(
                reversed(
                    row["raster_only_incompleteness_census"][
                        "page_census_rows"
                    ][:2]
                )
            ),
        ),
    )
    add(
        "reordered_census_page_members",
        lambda row: reverse_first_record_members(row, "page_census_rows"),
    )
    add(
        "missing_page_exception_key",
        lambda row: row["raster_only_incompleteness_census"][
            "page_census_rows"
        ][6]["branch_exception_keys"].pop(),
    )
    add(
        "missing_page_dependent_key",
        lambda row: row["raster_only_incompleteness_census"][
            "page_census_rows"
        ][7]["dependent_atom_keys"].pop(),
    )
    add(
        "bad_census_page_identity",
        lambda row: row["raster_only_incompleteness_census"][
            "page_census_rows"
        ][0].__setitem__("questionnaire_page_id", "bad-page-id"),
    )
    add(
        "bad_census_page_text_hash",
        lambda row: row["raster_only_incompleteness_census"][
            "page_census_rows"
        ][0].__setitem__("page_text_utf8_sha256", "0" * 64),
    )
    add(
        "bad_dependent_exact_slice",
        lambda row: row["raster_only_incompleteness_census"][
            "dependent_atom_consequence_records"
        ][0].__setitem__("matched_text", "repaired transcription"),
    )
    add("incomplete_emitted_projection", mutate_first_emitted_projection)
    add(
        "false_census_claim",
        lambda row: row["raster_only_incompleteness_census"].__setitem__(
            "document_completeness_claim",
            "complete-under-extraction-authority with 15 raster-only exceptions",
        ),
    )
    add(
        "bad_census_reason",
        lambda row: row["raster_only_incompleteness_census"].__setitem__(
            "closed_gap_reason", "other"
        ),
    )
    add(
        "bad_path_consequence",
        lambda row: row["raster_only_incompleteness_census"][
            "dependent_atom_consequence_records"
        ][0].__setitem__("path_consequence", EMITTED_PATH_CONSEQUENCE),
    )
    add("reordered_blocking_exception_keys", mutate_first_blocking_order)
    add(
        "dense_section_f_semantic_ordinal",
        lambda row: section_f_occurrence(row).__setitem__(
            "semantic_ordinal_at_span", 0
        ),
    )
    add(
        "dense_section_f_occurrence_index",
        lambda row: section_f_occurrence(row).__setitem__(
            "occurrence_index_on_page", 0
        ),
    )
    add(
        "boolean_section_f_semantic_ordinal",
        lambda row: section_f_occurrence(row).__setitem__(
            "semantic_ordinal_at_span", True
        ),
    )
    add(
        "float_section_f_occurrence_index",
        lambda row: section_f_occurrence(row).__setitem__(
            "occurrence_index_on_page", 4.0
        ),
    )
    add(
        "float_branch_exception_count",
        lambda row: row["raster_only_incompleteness_census"].__setitem__(
            "branch_exception_count", 16.0
        ),
    )
    add(
        "boolean_exception_index",
        lambda row: row["raster_only_incompleteness_census"][
            "branch_exception_records"
        ][1].__setitem__("exception_index_on_page", True),
    )
    add(
        "boolean_page_census_count",
        lambda row: row["raster_only_incompleteness_census"][
            "page_census_rows"
        ][15].__setitem__("branch_exception_count", True),
    )
    add(
        "float_raster_seal_count",
        lambda row: row["seal"].__setitem__(
            "raster_only_dependent_atom_consequence_count", 38.0
        ),
    )
    add(
        "bad_visual_fidelity_note_code",
        lambda row: visual_note(row).__setitem__("note_code", "other"),
    )
    add(
        "bad_visual_fidelity_note_text",
        lambda row: visual_note(row).__setitem__("note", "visual repair"),
    )
    add(
        "repaired_visual_fidelity_occurrence",
        lambda row: emitted_visual_occurrence(row).__setitem__(
            "matched_text", "repaired transcription"
        ),
    )
    add(
        "bad_raster_keyset_digest",
        lambda row: row["seal"].__setitem__(
            "raster_only_branch_exception_keyset_sha256", "0" * 64
        ),
    )
    add(
        "bad_raster_domain_digest",
        lambda row: row["seal"].__setitem__(
            "raster_only_dependent_atom_consequence_domain_sha256", "0" * 64
        ),
    )
    add(
        "bad_raster_sidecar_digest",
        lambda row: row["seal"].__setitem__(
            "raster_only_incompleteness_census_sha256", "0" * 64
        ),
    )
    add(
        "missing_raster_seal_member",
        lambda row: row["seal"].pop(RASTER_SEAL_KEYS[-1]),
    )
    add(
        "reordered_flat_seal_members", lambda row: reverse_members(row, "seal")
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
    try:
        source_tools.strict_parse_document(
            b'{"duplicate":1,"duplicate":2}\n',
            "duplicate-sidecar-member mutation",
        )
    except ValueError:
        pass
    else:
        raise ValueError("mutation was not rejected: duplicate_object_member")

    try:
        _validate_alias_relation("inferred_synonym")
    except ValueError:
        pass
    else:
        raise ValueError(
            "mutation was not rejected: inferred_alias_zero_domain"
        )

    def assert_rejected(
        name: str,
        mutation: dict[str, Any],
        *,
        recompute_artifact_digest: bool = True,
    ) -> None:
        if recompute_artifact_digest:
            mutation["integrity"]["content_sha256"] = _content_sha256(mutation)
        try:
            validate_annotation(mutation, *inputs)
        except ValueError:
            return
        raise ValueError(f"mutation was not rejected: {name}")

    def run_resealed_sidecar_mutation(name: str, mutate: Any) -> None:
        """Mutate metadata, then faithfully reseal every enclosing domain."""

        mutation = copy.deepcopy(value)
        sidecar = mutation["raster_only_incompleteness_census"]
        mutate(sidecar)
        sidecar["branch_exception_count"] = len(
            sidecar["branch_exception_records"]
        )
        sidecar["dependent_atom_count"] = len(
            sidecar["dependent_atom_consequence_records"]
        )
        for page_row in sidecar["page_census_rows"]:
            page_row["branch_exception_count"] = len(
                page_row["branch_exception_keys"]
            )
            page_row["dependent_atom_count"] = len(
                page_row["dependent_atom_keys"]
            )
        mutation["seal"].update(_raster_seal_fields(sidecar))
        assert_rejected(name, mutation)

    def multi_blocker_record(sidecar: Mapping[str, Any]) -> dict[str, Any]:
        return next(
            record
            for record in sidecar["dependent_atom_consequence_records"]
            if len(record["blocking_exception_keys"]) > 1
        )

    def omit_blocker(sidecar: dict[str, Any]) -> None:
        multi_blocker_record(sidecar)["blocking_exception_keys"].pop()

    def add_blocker(sidecar: dict[str, Any]) -> None:
        target = multi_blocker_record(sidecar)
        existing = {tuple(key) for key in target["blocking_exception_keys"]}
        donor = next(
            [
                record["questionnaire_page_id"],
                record["exception_index_on_page"],
            ]
            for record in sidecar["branch_exception_records"]
            if (
                record["questionnaire_page_id"],
                record["exception_index_on_page"],
            )
            not in existing
        )
        target["blocking_exception_keys"].append(donor)

    def duplicate_blocker(sidecar: dict[str, Any]) -> None:
        keys = multi_blocker_record(sidecar)["blocking_exception_keys"]
        keys.append(copy.deepcopy(keys[0]))

    def reorder_blockers(sidecar: dict[str, Any]) -> None:
        multi_blocker_record(sidecar)["blocking_exception_keys"].reverse()

    for name, mutate in (
        ("omitted_blocking_key_fully_resealed", omit_blocker),
        ("extra_blocking_key_fully_resealed", add_blocker),
        ("duplicate_blocking_key_fully_resealed", duplicate_blocker),
        ("reordered_blocking_keys_fully_resealed", reorder_blockers),
    ):
        run_resealed_sidecar_mutation(name, mutate)

    def page_census_row(
        sidecar: Mapping[str, Any], page_number: int
    ) -> dict[str, Any]:
        return next(
            row
            for row in sidecar["page_census_rows"]
            if row["page_number"] == page_number
        )

    def page_key_mutator(domain: str, action: str) -> Any:
        source_page = 7 if domain == "branch_exception_keys" else 15
        donor_page = 8

        def mutate(sidecar: dict[str, Any]) -> None:
            keys = page_census_row(sidecar, source_page)[domain]
            donor_keys = page_census_row(sidecar, donor_page)[domain]
            if action == "missing":
                keys.pop()
            elif action == "extra":
                keys.append(copy.deepcopy(donor_keys[0]))
            elif action == "duplicate":
                keys.append(copy.deepcopy(keys[0]))
            elif action == "reordered":
                keys.reverse()
            else:
                raise ValueError("page-key mutation action drift")

        return mutate

    for domain in ("branch_exception_keys", "dependent_atom_keys"):
        label = "branch" if domain == "branch_exception_keys" else "dependent"
        for action in ("missing", "extra", "duplicate", "reordered"):
            run_resealed_sidecar_mutation(
                f"{action}_{label}_page_key_fully_resealed",
                page_key_mutator(domain, action),
            )

    page_texts = inputs[4]
    review = inputs[5]
    dependent_coordinates = set(DEPENDENCY_BY_COORDINATE)
    donor_spec = next(
        spec
        for spec in review["occurrence_specs"]
        if spec["page_number"] == 8
        and spec["occurrence_kind"] == "field_purpose_prompt"
        and (
            spec["page_number"],
            spec["utf8_byte_start"],
            spec["utf8_byte_end"],
            spec["occurrence_kind"],
        )
        not in dependent_coordinates
    )
    donor_bytes, donor_text = _utf8_slice(
        page_texts[7],
        donor_spec["utf8_byte_start"],
        donor_spec["utf8_byte_end"],
    )

    def reuse_another_instance_bytes(sidecar: dict[str, Any]) -> None:
        target = next(
            record
            for record in sidecar["dependent_atom_consequence_records"]
            if record["page_number"] == 8
            and record["occurrence_kind"] == "field_purpose_prompt"
        )
        old_key = [
            target["questionnaire_page_id"],
            target["utf8_byte_start"],
            target["utf8_byte_end"],
            target["occurrence_kind"],
        ]
        target["utf8_byte_start"] = donor_spec["utf8_byte_start"]
        target["utf8_byte_end"] = donor_spec["utf8_byte_end"]
        target["matched_text"] = donor_text
        target["matched_utf8_sha256"] = _sha256(donor_bytes)
        new_key = [
            target["questionnaire_page_id"],
            target["utf8_byte_start"],
            target["utf8_byte_end"],
            target["occurrence_kind"],
        ]
        keys = page_census_row(sidecar, 8)["dependent_atom_keys"]
        keys[keys.index(old_key)] = new_key

    run_resealed_sidecar_mutation(
        "another_printed_instance_bytes_fully_resealed",
        reuse_another_instance_bytes,
    )

    bad_artifact_digest = copy.deepcopy(value)
    bad_artifact_digest["integrity"]["content_sha256"] = "0" * 64
    assert_rejected(
        "bad_artifact_digest",
        bad_artifact_digest,
        recompute_artifact_digest=False,
    )

    for name, mutate in _mutation_specs(value):
        mutation = copy.deepcopy(value)
        mutate(mutation)
        assert_rejected(name, mutation)


def _write_or_check(path: Path, raw: bytes, check: bool) -> None:
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
