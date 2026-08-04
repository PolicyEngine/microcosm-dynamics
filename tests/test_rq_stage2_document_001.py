"""Independent validation of the sealed R_Q document-1 annotation.

Every row assertion below is re-derived from ``fam1968_QxQs.pdf`` through the
pinned Poppler derivation rather than from the builder's in-memory value, so
the committed shard is checked against the source bytes and not against the
code that wrote it.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
CAPTURE_ROOT = (
    Path("~/PolicyEngine/psid-data").expanduser()
    / "documentation"
    / "capture1"
)
SOURCE_PDF = CAPTURE_ROOT / "fam1968_QxQs.pdf"
ANNOTATION_PATH = (
    ROOT
    / "docs"
    / "analysis"
    / "rq_stage2_annotations"
    / "document_001_fam1968_QxQs_annotation_v1.json"
)
REVIEW_PATH = (
    ROOT
    / "docs"
    / "analysis"
    / "rq_stage2_annotations"
    / "document_001_fam1968_QxQs_source_review_v1.json"
)

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_rq_stage2_document_001_annotation as annotation  # noqa: E402

DOCUMENT_SOURCE_POSITION = 1
INTERVIEW_WAVE = 1968
PAGE_COUNT = 50
FILE_SIZE = 19_043_891
FILE_SHA256 = (
    "0689bde3c02bd054cb5b2a25bf8f6cf8a10d26465d669e6c2000ac39daf7a055"
)
OCCURRENCE_KINDS = annotation.OCCURRENCE_KINDS
FORBIDDEN_ID_PREFIXES = (
    "psid-job-slot:",
    "psid-component-slot:",
    "psid-node-alias:",
    "psid-questionnaire-relationship:",
)
ANNOTATED_PAGES = {
    13,
    14,
    15,
    18,
    19,
    20,
    21,
    22,
    23,
    24,
    25,
    26,
    27,
    28,
    32,
    44,
}


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture(scope="module")
def sealed() -> dict:
    return json.loads(ANNOTATION_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def review() -> dict:
    return json.loads(REVIEW_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def page_texts() -> list[str]:
    if not SOURCE_PDF.is_file():
        pytest.skip("PSID questionnaire capture is not staged")
    result = subprocess.run(
        ["pdftotext", "-layout", "-enc", "UTF-8", str(SOURCE_PDF), "-"],
        check=True,
        capture_output=True,
    )
    pages = result.stdout.decode("utf-8", errors="strict").split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    return pages


def test_source_bytes_and_page_domain_reproduce(page_texts: list[str]) -> None:
    raw = SOURCE_PDF.read_bytes()
    assert len(raw) == FILE_SIZE
    assert _sha256(raw) == FILE_SHA256
    assert len(page_texts) == PAGE_COUNT


def test_whole_document_locator_obeys_every_equation(sealed: dict) -> None:
    locator = sealed["whole_document_locator"]
    assert set(locator) == set(annotation.LOCATOR_KEYS)
    assert locator["location_type"] == "whole_document_exact_file_range"
    assert locator["byte_start"] == 0
    assert locator["byte_end"] == locator["size_bytes"] == FILE_SIZE
    assert (
        locator["range_sha256"] == locator["full_file_sha256"] == FILE_SHA256
    )
    assert locator["pdf_page_domain"] == "all_pages_and_flow_branches"
    assert locator["interview_wave"] == INTERVIEW_WAVE
    assert locator["filename"] == "fam1968_QxQs.pdf"
    assert locator["locator_id"] == "psid-whole-document:" + (
        annotation._canonical_digest(
            [
                locator["source_document_id"],
                locator["interview_wave"],
                locator["full_file_sha256"],
                locator["size_bytes"],
            ]
        )
    )


def test_page_rows_exact_cover_the_replayed_domain(
    sealed: dict, page_texts: list[str]
) -> None:
    rows = sealed["questionnaire_page_rows"]
    assert len(rows) == PAGE_COUNT
    locator_id = sealed["whole_document_locator"]["locator_id"]
    document_id = sealed["whole_document_locator"]["source_document_id"]
    for position, row in enumerate(rows, start=1):
        assert set(row) == set(annotation.PAGE_KEYS)
        assert row["page_number"] == position
        assert not isinstance(row["page_number"], bool)
        assert row["source_document_id"] == document_id
        assert row["source_locator_id"] == locator_id
        assert row["interview_wave"] == INTERVIEW_WAVE
        assert row["annotation_status"] == "complete"
        assert row["page_text_utf8_sha256"] == _sha256(
            page_texts[position - 1].encode("utf-8")
        )
        assert row["questionnaire_page_id"] == "psid-questionnaire-page:" + (
            annotation._canonical_digest(
                [
                    document_id,
                    INTERVIEW_WAVE,
                    row["page_number"],
                    row["page_text_utf8_sha256"],
                ]
            )
        )
    assert len({row["questionnaire_page_id"] for row in rows}) == PAGE_COUNT


def test_empty_occurrence_pages_are_still_emitted(sealed: dict) -> None:
    rows = sealed["questionnaire_page_rows"]
    populated = {
        row["page_number"]
        for row in rows
        if row["questionnaire_occurrence_ids"]
    }
    assert populated == ANNOTATED_PAGES
    empty = [row for row in rows if not row["questionnaire_occurrence_ids"]]
    assert len(empty) == PAGE_COUNT - len(ANNOTATED_PAGES)
    assert not rows[1]["questionnaire_occurrence_ids"]
    assert not rows[33]["questionnaire_occurrence_ids"]


def test_every_occurrence_slice_and_id_recomputes(
    sealed: dict, page_texts: list[str]
) -> None:
    document_id = sealed["whole_document_locator"]["source_document_id"]
    locator_id = sealed["whole_document_locator"]["locator_id"]
    canonical_path = sealed["document_source_row"]["canonical_source_path"]
    for row in sealed["questionnaire_occurrence_rows"]:
        assert set(row) == set(annotation.OCCURRENCE_KEYS)
        assert row["occurrence_kind"] in OCCURRENCE_KINDS
        assert row["source_document_id"] == document_id
        assert row["source_locator_id"] == locator_id
        assert row["interview_wave"] == INTERVIEW_WAVE
        start, end = row["utf8_byte_start"], row["utf8_byte_end"]
        assert 0 <= start < end
        raw = page_texts[row["page_number"] - 1].encode("utf-8")[start:end]
        assert raw.decode("utf-8") == row["matched_text"]
        assert row["matched_text"]
        assert _sha256(raw) == row["matched_utf8_sha256"]
        assert row["source_locator_sha256"] == annotation._canonical_digest(
            [
                document_id,
                canonical_path,
                "questionnaire_page_utf8_span",
                [
                    INTERVIEW_WAVE,
                    row["page_number"],
                    start,
                    end,
                    row["occurrence_index_on_page"],
                    row["semantic_ordinal_at_span"],
                    row["occurrence_kind"],
                ],
            ]
        )
        remaining = [row[key] for key in annotation.OCCURRENCE_KEYS[1:]]
        assert row[
            "questionnaire_occurrence_id"
        ] == "psid-questionnaire-occurrence:" + (
            annotation._canonical_digest(remaining)
        )


def test_within_page_ordering_indices_and_projections(sealed: dict) -> None:
    kind_order = {kind: n for n, kind in enumerate(OCCURRENCE_KINDS)}
    by_page: dict[int, list[dict]] = {}
    for row in sealed["questionnaire_occurrence_rows"]:
        by_page.setdefault(row["page_number"], []).append(row)
    pages = {r["page_number"]: r for r in sealed["questionnaire_page_rows"]}
    for page_number, rows in by_page.items():
        keys = [
            (
                r["utf8_byte_start"],
                r["utf8_byte_end"],
                kind_order[r["occurrence_kind"]],
                r["semantic_ordinal_at_span"],
            )
            for r in rows
        ]
        assert keys == sorted(keys)
        assert [r["occurrence_index_on_page"] for r in rows] == list(
            range(len(rows))
        )
        assert pages[page_number]["questionnaire_occurrence_ids"] == [
            r["questionnaire_occurrence_id"] for r in rows
        ]


def test_atomic_span_kind_uniqueness_and_lawful_ordinals(sealed: dict) -> None:
    seen: Counter = Counter()
    for row in sealed["questionnaire_occurrence_rows"]:
        coordinate = (
            row["page_number"],
            row["utf8_byte_start"],
            row["utf8_byte_end"],
            row["occurrence_kind"],
        )
        seen[coordinate] += 1
        if row["occurrence_kind"] != "flow_branch_label":
            assert row["semantic_ordinal_at_span"] == 0
    for coordinate, count in seen.items():
        if count != 1:
            assert coordinate[3] == "flow_branch_label"
    ordinals: dict[tuple, list[int]] = {}
    for row in sealed["questionnaire_occurrence_rows"]:
        coordinate = (
            row["page_number"],
            row["utf8_byte_start"],
            row["utf8_byte_end"],
            row["occurrence_kind"],
        )
        ordinals.setdefault(coordinate, []).append(
            row["semantic_ordinal_at_span"]
        )
    for values in ordinals.values():
        assert values == list(range(len(values)))
    assert len(
        {
            (
                row["page_number"],
                row["utf8_byte_start"],
                row["utf8_byte_end"],
                row["occurrence_kind"],
                row["semantic_ordinal_at_span"],
            )
            for row in sealed["questionnaire_occurrence_rows"]
        }
    ) == len(sealed["questionnaire_occurrence_rows"])


def test_shared_questions_carry_complete_status_paths(sealed: dict) -> None:
    branches = {
        row["branch_label"]: row["flow_branch_id"]
        for row in sealed["flow_branch_rows"]
    }
    occurrences = sealed["questionnaire_occurrence_rows"]

    def one(page: int, prefix: str) -> dict:
        rows = [
            row
            for row in occurrences
            if row["page_number"] == page
            and row["occurrence_kind"] == "context_anchor"
            and row["matched_text"].startswith(prefix)
        ]
        assert len(rows) == 1
        return rows[0]

    occupation = one(14, "F2(Gl,H2)")
    prior_job = one(15, "F7")
    employer_count = one(15, "FlO")
    assert {path[-1] for path in occupation["flow_branch_paths"]} == {
        branches["Working now or laid off only temporarily:"],
        branches["Unemployed:"],
        branches["Retired, Housewife, or Student:"],
    }
    expected_two = {
        branches["Working now or laid off only temporarily:"],
        branches["Unemployed:"],
    }
    assert {
        path[-1] for path in prior_job["flow_branch_paths"]
    } == expected_two
    assert {
        path[-1] for path in employer_count["flow_branch_paths"]
    } == expected_two
    for row in (occupation, prior_job, employer_count):
        assert all(
            path[0] == annotation.FLOW_ROOT
            for path in row["flow_branch_paths"]
        )
        encoded = [
            [node.encode("utf-8") for node in path]
            for path in row["flow_branch_paths"]
        ]
        assert encoded == sorted(encoded)


def test_flow_branch_rows_obey_ancestry_and_cycle_laws(sealed: dict) -> None:
    occurrences = {
        r["questionnaire_occurrence_id"]: r
        for r in sealed["questionnaire_occurrence_rows"]
    }
    order = {
        r["questionnaire_occurrence_id"]: n
        for n, r in enumerate(sealed["questionnaire_occurrence_rows"])
    }
    branches = sealed["flow_branch_rows"]
    labels = [
        r
        for r in sealed["questionnaire_occurrence_rows"]
        if r["occurrence_kind"] == "flow_branch_label"
    ]
    assert len(branches) == len(labels)
    by_id: dict[str, dict] = {}
    for row in branches:
        assert set(row) == set(annotation.FLOW_BRANCH_KEYS)
        source = occurrences[row["source_occurrence_id"]]
        assert source["occurrence_kind"] == "flow_branch_label"
        assert (
            row["interview_wave"] == source["interview_wave"] == INTERVIEW_WAVE
        )
        assert row["page_number"] == source["page_number"]
        assert (
            row["occurrence_index_on_page"]
            == source["occurrence_index_on_page"]
        )
        assert row["source_locator_id"] == source["source_locator_id"]
        assert row["branch_label"] == source["matched_text"]
        assert row["branch_label_sha256"] == source["matched_utf8_sha256"]
        assert len(source["flow_branch_paths"]) == 1
        assert row["branch_path"] == [
            *source["flow_branch_paths"][0],
            row["flow_branch_id"],
        ]
        assert row["flow_branch_id"] == "questionnaire-flow:" + (
            annotation._canonical_digest(
                [
                    row["parent_flow_branch_id"],
                    row["interview_wave"],
                    row["source_occurrence_id"],
                ]
            )
        )
        if row["parent_flow_branch_id"] != annotation.FLOW_ROOT:
            parent = by_id[row["parent_flow_branch_id"]]
            assert (
                order[parent["source_occurrence_id"]]
                < order[row["source_occurrence_id"]]
            )
        assert len(set(row["branch_path"])) == len(row["branch_path"])
        by_id[row["flow_branch_id"]] = row
    assert len(by_id) == len(branches)
    assert len({r["source_occurrence_id"] for r in branches}) == len(branches)
    assert len({tuple(r["branch_path"]) for r in branches}) == len(branches)


def test_every_occurrence_path_resolves_and_is_ordered(sealed: dict) -> None:
    resolved = {annotation.FLOW_ROOT} | {
        r["flow_branch_id"] for r in sealed["flow_branch_rows"]
    }
    lawful = {(annotation.FLOW_ROOT,)} | {
        tuple(r["branch_path"]) for r in sealed["flow_branch_rows"]
    }
    for row in sealed["questionnaire_occurrence_rows"]:
        paths = row["flow_branch_paths"]
        assert paths and all(paths)
        for path in paths:
            assert all(node in resolved for node in path)
            assert tuple(path) in lawful
        encoded = [[node.encode("utf-8") for node in p] for p in paths]
        assert encoded == sorted(encoded)
        assert len({tuple(p) for p in paths}) == len(paths)


def test_local_anchor_and_repeat_rows_stay_document_local(
    sealed: dict,
) -> None:
    occurrences = {
        r["questionnaire_occurrence_id"]: r
        for r in sealed["questionnaire_occurrence_rows"]
    }
    anchor_kinds = {
        "role_anchor",
        "job_anchor",
        "remuneration_component_anchor",
        "role_total_anchor",
        "farm_aggregate_anchor",
        "business_aggregate_anchor",
        "context_anchor",
    }
    component_kinds = {"remuneration_component_anchor", "context_anchor"}
    parent_kinds = {
        "job_anchor",
        "role_total_anchor",
        "farm_aggregate_anchor",
        "business_aggregate_anchor",
    }
    anchors = sealed["local_anchor_classification_rows"]
    anchor_by_source_id = {row["source_occurrence_id"]: row for row in anchors}
    covered = []
    for row in anchors:
        assert set(row) == set(annotation.LOCAL_ANCHOR_KEYS)
        source = occurrences[row["source_occurrence_id"]]
        assert source["occurrence_kind"] in anchor_kinds
        assert row["occurrence_kind"] == source["occurrence_kind"]
        assert row["exact_label"] == source["matched_text"]
        assert row["exact_label_sha256"] == source["matched_utf8_sha256"]
        assert row["classification_status"] == "provisional_document_local"
        if source["occurrence_kind"] == "role_anchor":
            assert row["node_domain"] == "role"
            assert row["classification"] in {
                "head_or_reference_person",
                "spouse_or_partner",
            }
        else:
            assert (
                row["node_domain"],
                row["classification"],
            ) == annotation.ANCHOR_CLASSIFICATION[source["occurrence_kind"]]
        if source["occurrence_kind"] not in component_kinds:
            assert row["parent_source_occurrence_ids"] == []
        if source["occurrence_kind"] == "remuneration_component_anchor":
            assert len(row["parent_source_occurrence_ids"]) == 1
        if source["occurrence_kind"] == "context_anchor":
            assert len(row["parent_source_occurrence_ids"]) <= 1
        for parent_id in row["parent_source_occurrence_ids"]:
            assert occurrences[parent_id]["occurrence_kind"] in parent_kinds
        covered.append(row["source_occurrence_id"])
    assert sorted(covered) == sorted(
        r["questionnaire_occurrence_id"]
        for r in sealed["questionnaire_occurrence_rows"]
        if r["occurrence_kind"] in anchor_kinds
    )

    repeats = sealed["local_repeat_alias_evidence_rows"]
    instruction_ids = [
        r["questionnaire_occurrence_id"]
        for r in sealed["questionnaire_occurrence_rows"]
        if r["occurrence_kind"] == "repeat_or_alias_instruction"
    ]
    assert {
        row["source_occurrence_id"]
        for row in repeats
        if occurrences[row["source_occurrence_id"]]["occurrence_kind"]
        == "repeat_or_alias_instruction"
    } == set(instruction_ids)
    occurrence_order = {
        row["questionnaire_occurrence_id"]: position
        for position, row in enumerate(sealed["questionnaire_occurrence_rows"])
    }
    alias_parents = {item: item for item in anchor_by_source_id}

    def alias_root(item: str) -> str:
        while alias_parents[item] != item:
            item = alias_parents[item]
        return item

    for row in repeats:
        assert set(row) == set(annotation.LOCAL_REPEAT_KEYS)
        assert row["relation"] in annotation.ALIAS_RELATIONS
        assert row["source_occurrence_id"] in row["evidence_occurrence_ids"]
        alias_ids = row["alias_anchor_source_occurrence_ids"]
        canonical_ids = row["canonical_anchor_source_occurrence_ids"]
        evidence_ids = row["evidence_occurrence_ids"]
        assert row["target_scope"] == "document_local"
        assert not set(alias_ids) & set(canonical_ids)
        assert set(alias_ids + canonical_ids) <= set(evidence_ids)
        anchor_evidence_ids = [
            item for item in evidence_ids if item in anchor_by_source_id
        ]
        if (
            row["resolution_status"]
            == "document_local_source_evidence_complete"
        ):
            assert len(alias_ids) == 1
            assert len(canonical_ids) == 1
            classified_endpoint_ids = alias_ids + canonical_ids
            assert all(
                occurrences[item]["occurrence_kind"]
                in annotation.ALIAS_ANCHOR_KINDS
                for item in classified_endpoint_ids
            )
            parent_vectors = [
                anchor_by_source_id[item]["parent_source_occurrence_ids"]
                for item in classified_endpoint_ids
            ]
            assert all(
                len(vector) == len(parent_vectors[0])
                and all(
                    alias_root(left) == alias_root(right)
                    for left, right in zip(
                        parent_vectors[0], vector, strict=True
                    )
                )
                for vector in parent_vectors[1:]
            )
        else:
            assert row["resolution_status"] == (
                annotation.COMPOSITE_CROSS_REFERENCE_RESOLUTION
            )
            assert row["relation"] == "explicit_cross_reference"
            assert alias_ids == []
            assert canonical_ids == []
            source = occurrences[row["source_occurrence_id"]]
            same_span_context_ids = {
                item
                for item in anchor_evidence_ids
                if occurrences[item]["occurrence_kind"] == "context_anchor"
                and (
                    occurrences[item]["page_number"],
                    occurrences[item]["utf8_byte_start"],
                    occurrences[item]["utf8_byte_end"],
                )
                == (
                    source["page_number"],
                    source["utf8_byte_start"],
                    source["utf8_byte_end"],
                )
            }
            assert len(same_span_context_ids) == 1
            assert len(set(anchor_evidence_ids) - same_span_context_ids) >= 2
            classified_endpoint_ids = anchor_evidence_ids
        endpoint_classifications = {
            (
                anchor_by_source_id[item]["node_domain"],
                anchor_by_source_id[item]["classification"],
            )
            for item in classified_endpoint_ids
        }
        assert len(endpoint_classifications) == 1
        if alias_ids:
            assert endpoint_classifications == {
                (
                    anchor_by_source_id[alias_ids[0]]["node_domain"],
                    anchor_by_source_id[alias_ids[0]]["classification"],
                )
            }
        else:
            assert endpoint_classifications == {
                ("component_slot", "source_context")
            }
        for ids in (alias_ids, canonical_ids, evidence_ids):
            assert ids == sorted(ids, key=occurrence_order.__getitem__)
        for evidence_id in row["evidence_occurrence_ids"]:
            assert occurrences[evidence_id]["occurrence_kind"] in (
                anchor_kinds | {"repeat_or_alias_instruction"}
            )
        if (
            row["resolution_status"]
            == "document_local_source_evidence_complete"
        ):
            alias_root_id = alias_root(alias_ids[0])
            canonical_root_id = alias_root(canonical_ids[0])
            alias_parents[alias_root_id] = canonical_root_id

    def anchor(page: int, kind: str, text: str) -> dict:
        rows = [
            row
            for row in anchors
            if occurrences[row["source_occurrence_id"]]["page_number"] == page
            and occurrences[row["source_occurrence_id"]]["occurrence_kind"]
            == kind
            and occurrences[row["source_occurrence_id"]]["matched_text"]
            == text
        ]
        assert len(rows) == 1
        return rows[0]

    def parent_texts(row: dict) -> list[str]:
        return [
            occurrences[parent_id]["matched_text"]
            for parent_id in row["parent_source_occurrence_ids"]
        ]

    assert anchor(14, "role_anchor", "Head")["printed_identifier"] == (
        "F2(Gl,H2)"
    )
    assert (
        anchor(20, "context_anchor", "Gl    See F2")["printed_identifier"]
        == "Gl"
    )
    assert anchor(22, "job_anchor", "occupation")["printed_identifier"] == (
        "Hl-2"
    )
    assert (
        anchor(
            26,
            "business_aggregate_anchor",
            "How much was your family's share\n         of the total income from the business in 1967 - that is, the amount         (\n         you took out plus any profits you left in?",
        )["printed_identifier"]
        == "J7"
    )
    assert (
        anchor(27, "farm_aggregate_anchor", "farming or market gardening")[
            "printed_identifier"
        ]
        == "Jllb"
    )
    assert {
        (
            occurrences[row["source_occurrence_id"]]["page_number"],
            occurrences[row["source_occurrence_id"]]["matched_text"],
        )
        for row in anchors
        if row["printed_identifier"] is None
    } == {(22, "WIFE")}

    assert parent_texts(
        anchor(
            15,
            "context_anchor",
            "F8    Would you say your present job is be t ter than th e one you had before?",
        )
    ) == ["present job"]
    assert parent_texts(
        anchor(
            15,
            "context_anchor",
            "F9    Does it pay more than the previous job?",
        )
    ) == ["present job"]
    assert parent_texts(
        anchor(
            25,
            "context_anchor",
            "J6   Is it a corporation or an unincorporated business, or do you have\n     an interest in both kinds?",
        )
    )[0].startswith("J5   Did you (Rand Family) own a business")
    assert parent_texts(
        anchor(
            26,
            "remuneration_component_anchor",
            "J9,-10   In additon to this, did you have any income from bonuses, overtime\n         or commissions? How much was that?",
        )
    )[0].startswith("J8     How much did you (Head) receive")
    assert parent_texts(
        anchor(
            27,
            "remuneration_component_anchor",
            "Jl,la   Did you (Head) receive · any other income in 1967 from a professional\n        practice or trade?",
        )
    ) == ["professional\n        practice or trade"]

    main_job_anchors = [
        row
        for row in anchors
        if occurrences[row["source_occurrence_id"]]["occurrence_kind"]
        == "job_anchor"
        and occurrences[row["source_occurrence_id"]]["matched_text"]
        == "main job"
    ]
    assert [row["printed_identifier"] for row in main_job_anchors] == [
        "F34",
        "F36",
        "F37",
        "F38,40",
        "F41",
    ]

    f7 = [
        row
        for row in occurrences.values()
        if row["page_number"] == 15
        and row["occurrence_kind"] == "context_anchor"
        and row["matched_text"].startswith("F7")
    ]
    assert len(f7) == 1
    assert (f7[0]["utf8_byte_start"], f7[0]["utf8_byte_end"]) == (769, 886)
    assert f7[0]["matched_text"].endswith("\n     GS")
    assert f7[0]["matched_utf8_sha256"] == (
        "0d7456547d20530827d2b36528d2203908319bb5817dea424a2a893e938ede1b"
    )

    h1 = anchor(
        22,
        "context_anchor",
        "Hl-2        During the last year (1967) did you do any work for money?",
    )
    h2 = anchor(
        22,
        "context_anchor",
        "What\n             kind of work did you do when you worked? (What was your occupation?)",
    )
    assert parent_texts(h1) == []
    assert parent_texts(h2) == ["occupation"]
    assert (
        occurrences[h1["source_occurrence_id"]]["utf8_byte_start"],
        occurrences[h1["source_occurrence_id"]]["utf8_byte_end"],
    ) == (89, 159)
    assert (
        occurrences[h2["source_occurrence_id"]]["utf8_byte_start"],
        occurrences[h2["source_occurrence_id"]]["utf8_byte_end"],
    ) == (160, 246)

    purpose_rows = [
        row
        for row in sealed["questionnaire_occurrence_rows"]
        if row["occurrence_kind"] == "field_purpose_prompt"
    ]
    purpose_by_page = {
        page: [row for row in purpose_rows if row["page_number"] == page]
        for page in (13, 14, 15)
    }
    assert {
        (row["utf8_byte_start"], row["utf8_byte_end"])
        for row in purpose_by_page[13]
    } >= {(1519, 1902), (1937, 2306), (2362, 2818)}
    page_14_split = [
        row
        for row in purpose_by_page[14]
        if row["utf8_byte_start"] in {207, 1272, 1411}
    ]
    assert [
        (row["utf8_byte_start"], row["utf8_byte_end"]) for row in page_14_split
    ] == [(207, 1259), (1272, 1398), (1411, 1782)]
    branch_ids = {
        row["branch_label"]: row["flow_branch_id"]
        for row in sealed["flow_branch_rows"]
    }
    working = branch_ids["Working now or laid off only temporarily:"]
    unemployed = branch_ids["Unemployed:"]
    retired = branch_ids["Retired, Housewife, or Student:"]
    assert [
        {path[-1] for path in row["flow_branch_paths"]}
        for row in page_14_split
    ] == [
        {working, unemployed, retired},
        {unemployed, retired},
        {working, unemployed, retired},
    ]
    assert any(
        row["utf8_byte_start"] == 898 and row["utf8_byte_end"] == 1306
        for row in purpose_by_page[15]
    )

    repeat_source_ids = sorted(
        {
            row["source_occurrence_id"]
            for row in repeats
            if occurrences[row["source_occurrence_id"]]["occurrence_kind"]
            == "repeat_or_alias_instruction"
        },
        key=occurrence_order.__getitem__,
    )
    repeat_sources = [
        occurrences[source_id] for source_id in repeat_source_ids
    ]
    page_22_repeat = [
        row for row in repeat_sources if row["page_number"] == 22
    ]
    assert [row["matched_text"] for row in page_22_repeat] == [
        "See F2 for a suitable reply to the occupation question.",
        "H3-4        See F36-41, remembering that our objective is the number of hours\n             that R actually worked in 1967.",
    ]
    assert [
        (row["utf8_byte_start"], row["utf8_byte_end"])
        for row in page_22_repeat
    ] == [
        (257, 312),
        (548, 670),
    ]
    see_f2_source_id = next(
        row["questionnaire_occurrence_id"]
        for row in page_22_repeat
        if row["utf8_byte_start"] == 257
    )
    see_f2_facts = [
        row
        for row in repeats
        if row["source_occurrence_id"] == see_f2_source_id
    ]
    assert len(see_f2_facts) == 2
    assert {
        (
            occurrences[row["alias_anchor_source_occurrence_ids"][0]][
                "matched_text"
            ],
            occurrences[row["canonical_anchor_source_occurrence_ids"][0]][
                "matched_text"
            ],
        )
        for row in see_f2_facts
    } == {
        ("occupation", "main occupation"),
        (
            "What\n             kind of work did you do when you worked? (What was your occupation?)",
            "F2(Gl,H2)   What is your main occupation? What do you do when you work?\n            What kind of work did you do when you worked?",
        ),
    }
    composite_rows = [
        row
        for row in repeats
        if row["resolution_status"]
        == annotation.COMPOSITE_CROSS_REFERENCE_RESOLUTION
    ]
    assert len(composite_rows) == 4
    expected_target_identifiers = {
        "G2-4    See F36~41": ["F36", "F37", "F38,40", "F41"],
        "H3-4        See F36-41, remembering that our objective is the number of hours\n             that R actually worked in 1967.": [
            "F36",
            "F37",
            "F38,40",
            "F41",
        ],
        "I 9-10   See Fl-2.": ["Fl", "F2(Gl,H2)"],
        "I 11-12      See F36 -41.": ["F36", "F37", "F38,40", "F41"],
    }
    for row in composite_rows:
        source = occurrences[row["source_occurrence_id"]]
        target_ids = [
            item
            for item in row["evidence_occurrence_ids"]
            if item in anchor_by_source_id
            and not (
                occurrences[item]["page_number"] == source["page_number"]
                and occurrences[item]["utf8_byte_start"]
                == source["utf8_byte_start"]
                and occurrences[item]["utf8_byte_end"]
                == source["utf8_byte_end"]
            )
        ]
        assert [
            anchor_by_source_id[item]["printed_identifier"]
            for item in target_ids
        ] == expected_target_identifiers[source["matched_text"]]
    assert not any(row["page_number"] in {26, 28} for row in repeat_sources)
    page_28_purpose = [
        row
        for row in sealed["questionnaire_occurrence_rows"]
        if row["page_number"] == 28
        and row["occurrence_kind"] == "field_purpose_prompt"
    ]
    assert len(page_28_purpose) == 1
    assert page_28_purpose[0]["matched_text"].endswith(
        "salary he paid himself should be entered under J8."
    )
    page_27_purpose = [
        row
        for row in sealed["questionnaire_occurrence_rows"]
        if row["page_number"] == 27
        and row["occurrence_kind"] == "field_purpose_prompt"
        and row["matched_text"].startswith(
            "If farming is R's primary occupation"
        )
    ]
    assert len(page_27_purpose) == 1
    assert (
        page_27_purpose[0]["utf8_byte_start"],
        page_27_purpose[0]["utf8_byte_end"],
    ) == (958, 1348)
    assert page_27_purpose[0]["matched_text"].endswith("however .")
    assert not any(
        row["page_number"] in {24, 27}
        and (
            row["matched_text"].startswith(
                "We pick up farming as a secondary source"
            )
            or row["matched_text"].startswith(
                "If farming is R's primary occupation"
            )
        )
        for row in repeat_sources
    )
    page_24_farm_purpose = [
        row
        for row in sealed["questionnaire_occurrence_rows"]
        if row["page_number"] == 24
        and row["occurrence_kind"] == "field_purpose_prompt"
        and row["matched_text"].startswith(
            "We pick up farming as a secondary source"
        )
    ]
    assert len(page_24_farm_purpose) == 1
    assert (
        page_24_farm_purpose[0]["utf8_byte_start"],
        page_24_farm_purpose[0]["utf8_byte_end"],
    ) == (1856, 1939)
    exact_label_aliases = [
        row
        for row in repeats
        if row["relation"] == "same_printed_identifier_and_exact_label"
    ]
    assert len(exact_label_aliases) == 1
    exact_label_alias = exact_label_aliases[0]
    assert (
        occurrences[exact_label_alias["source_occurrence_id"]]["matched_text"]
        == "head"
    )
    assert [
        occurrences[item]["matched_text"]
        for item in exact_label_alias["evidence_occurrence_ids"]
    ] == ["head", "head"]


def test_candidate_disposition_relation_exact_covers_the_domain(
    sealed: dict,
) -> None:
    candidates = json.loads(
        (ROOT / sealed["candidate_artifact_identity"]["path"]).read_text(
            encoding="utf-8"
        )
    )
    expected = [
        (
            "whole_document_locator",
            candidates["whole_document_locator_candidate"][
                "candidate_locator_id"
            ],
        ),
        *[
            ("page", row["candidate_page_id"])
            for row in candidates["candidate_page_rows"]
        ],
        *[
            ("occurrence", row["candidate_occurrence_id"])
            for row in candidates["candidate_occurrence_rows"]
        ],
        *[
            ("flow_path", row["candidate_flow_path_id"])
            for row in candidates["candidate_flow_path_rows"]
        ],
        *[
            (
                "anchor_classification",
                row["candidate_anchor_classification_id"],
            )
            for row in candidates["candidate_anchor_classification_rows"]
        ],
    ]
    rows = sealed["candidate_disposition_rows"]
    assert [
        (row["candidate_row_kind"], row["candidate_id"]) for row in rows
    ] == expected
    output_ids = {
        annotation._stage2_id(row_kind, row)
        for row_kind, row in annotation._all_output_rows(sealed)
    }
    for row in rows:
        assert set(row) == set(annotation.CANDIDATE_DISPOSITION_KEYS)
        assert row["adjudication_status"] == "complete"
        assert row["disposition"] in {
            "accepted",
            "modified",
            "split",
            "rejected",
        }
        assert set(row["stage2_row_ids"]) <= output_ids
        if row["disposition"] == "rejected":
            assert row["stage2_row_ids"] == []
        elif row["disposition"] == "split":
            assert len(row["stage2_row_ids"]) >= 2
        else:
            assert len(row["stage2_row_ids"]) == 1

    notes = {
        row["candidate_id"]: row
        for row in sealed["adjudication_note_rows"]
        if row["candidate_row_kind"] == "occurrence"
    }
    assert (
        notes[
            "rq-candidate-occurrence:331e8733ab058b567e8ca294d7c27a171414f28822550a761905513e00fa74bb"
        ]["note_code"]
        == "all_family_pay_in_kind_outside_fixed_role_job_domain"
    )
    assert notes[
        "rq-candidate-occurrence:03715b39aecda2dc896cc237f3858eb784210b904100a843a290b8184ac24998"
    ]["note_code"] == (
        "nonemployment_housing_or_home-production_false_positive"
    )


def test_output_adjudication_relation_exact_covers_every_row(
    sealed: dict,
) -> None:
    expected = [
        (row_kind, annotation._stage2_id(row_kind, row))
        for row_kind, row in annotation._all_output_rows(sealed)
    ]
    rows = sealed["output_adjudication_rows"]
    assert sorted(
        (row["stage2_row_kind"], row["stage2_row_id"]) for row in rows
    ) == sorted(expected)
    candidate_ids = {
        row["candidate_id"] for row in sealed["candidate_disposition_rows"]
    }
    for row in rows:
        assert set(row) == set(annotation.OUTPUT_ADJUDICATION_KEYS)
        assert row["adjudication_status"] == "complete"
        assert row["whole_page_review_complete"] is True
        assert row["source_span_verified"] is True
        assert row["adjudication_action"] in {
            "candidate_accepted",
            "candidate_modified",
            "candidate_split",
            "manual_add",
        }
        assert set(row["source_candidate_ids"]) <= candidate_ids
        if row["adjudication_action"] == "manual_add":
            assert row["source_candidate_ids"] == []
        else:
            assert row["source_candidate_ids"]


def test_two_adjudication_relations_agree_in_both_directions(
    sealed: dict,
) -> None:
    forward: dict[str, set[str]] = {}
    for row in sealed["candidate_disposition_rows"]:
        for output_id in row["stage2_row_ids"]:
            forward.setdefault(output_id, set()).add(row["candidate_id"])
    backward: dict[str, set[str]] = {}
    for row in sealed["output_adjudication_rows"]:
        if row["source_candidate_ids"]:
            backward[row["stage2_row_id"]] = set(row["source_candidate_ids"])
    assert forward == backward


def test_whole_page_review_covers_every_page(
    sealed: dict, review: dict, page_texts: list[str]
) -> None:
    rows = review["page_review_rows"]
    assert len(rows) == PAGE_COUNT
    for position, row in enumerate(rows, start=1):
        assert row["page_number"] == position
        assert row["whole_page_review_complete"] is True
        assert row["review_status"] == "complete"
        assert row["review_note"]
        assert row["page_text_utf8_sha256"] == _sha256(
            page_texts[position - 1].encode("utf-8")
        )
    assert review["review_method"]["global_ids_assigned"] is False
    assert (
        review["review_method"]["whole_page_review"]
        == "all_50_pages_including_empty_occurrence_pages"
    )
    assert sealed["seal"]["page_review_count"] == PAGE_COUNT
    assert sealed["seal"]["whole_document_review_complete"] is True


def test_shard_states_nonauthority_and_emits_no_global_id(
    sealed: dict,
) -> None:
    assert sealed["status"] == (
        "sealed_complete_nonauthority_document_annotation"
    )
    assert sealed["authority_kind"] == (
        "document_local_source_annotation_nonauthority"
    )
    assert sealed["document_source_position"] == DOCUMENT_SOURCE_POSITION
    statement = sealed["nonauthority_statement"]
    assert statement["status"] == "nonauthority"
    assert statement["one_document_only"] is True
    assert not any(
        statement[key]
        for key in statement
        if key not in {"status", "one_document_only"}
    )
    blob = json.dumps(sealed, sort_keys=True)
    for prefix in FORBIDDEN_ID_PREFIXES:
        assert prefix not in blob
    assert sealed["seal"]["global_ids_assigned"] is False
    assert sealed["seal"]["authority_status"] == "nonauthority"


def test_committed_artifacts_reproduce_and_mutations_fail_closed() -> None:
    if not SOURCE_PDF.is_file():
        pytest.skip("PSID questionnaire capture is not staged")
    for script in (
        "author_rq_stage2_document_001_source_review.py",
        "build_rq_stage2_document_001_annotation.py",
    ):
        command = [sys.executable, str(SCRIPTS / script), "--check"]
        if script.startswith("build_"):
            command.append("--mutation-tests")
        result = subprocess.run(command, cwd=ROOT, capture_output=True)
        assert result.returncode == 0, result.stderr.decode("utf-8")
