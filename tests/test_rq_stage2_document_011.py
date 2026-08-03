"""Independent validation of the sealed R_Q document-11 annotation.

Every row assertion below is re-derived from ``fam1973_QxQs.pdf`` through the
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
SOURCE_PDF = CAPTURE_ROOT / "fam1973_QxQs.pdf"
ANNOTATION_PATH = (
    ROOT
    / "docs"
    / "analysis"
    / "rq_stage2_annotations"
    / "document_011_fam1973_QxQs_annotation_v1.json"
)

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_rq_stage2_document_011_annotation as annotation  # noqa: E402

DOCUMENT_SOURCE_POSITION = 11
INTERVIEW_WAVE = 1973
PAGE_COUNT = 68
FILE_SIZE = 15_303_757
FILE_SHA256 = (
    "c5b2e9fc943906e8b2c3cce87fefae1cf283ff285437bd4f1b791e0fcc215934"
)
OCCURRENCE_KINDS = annotation.OCCURRENCE_KINDS
FORBIDDEN_ID_PREFIXES = (
    "psid-job-slot:",
    "psid-component-slot:",
    "psid-node-alias:",
    "psid-questionnaire-relationship:",
)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture(scope="module")
def sealed() -> dict:
    return json.loads(ANNOTATION_PATH.read_text(encoding="utf-8"))


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
    assert locator["filename"] == "fam1973_QxQs.pdf"
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


KNOWN_EMPTY_PAGES = (
    frozenset(range(1, 9))
    | {16, 28, 31, 32, 33, 34, 35, 36, 40}
    | frozenset(range(59, 69))
)
KNOWN_INSTRUMENT_PAGES = frozenset(
    {9, 13, 15, 17, 19, 21, 23, 25, 27, 29, 37, 41, 47, 49, 51, 53, 55, 57}
)


def test_empty_occurrence_pages_are_still_emitted(sealed: dict) -> None:
    rows = sealed["questionnaire_page_rows"]
    empty = [r for r in rows if not r["questionnaire_occurrence_ids"]]
    empty_pages = {r["page_number"] for r in empty}
    populated_pages = {
        r["page_number"] for r in rows if r["questionnaire_occurrence_ids"]
    }
    assert empty_pages == KNOWN_EMPTY_PAGES
    assert KNOWN_INSTRUMENT_PAGES <= populated_pages
    assert empty_pages | populated_pages == set(range(1, PAGE_COUNT + 1))
    assert empty_pages.isdisjoint(populated_pages)
    assert len(empty) == sealed["seal"]["empty_occurrence_page_count"]


def test_every_occurrence_slice_and_id_recomputes(
    sealed: dict, page_texts: list[str]
) -> None:
    document_id = sealed["whole_document_locator"]["source_document_id"]
    locator_id = sealed["whole_document_locator"]["locator_id"]
    for row in sealed["questionnaire_occurrence_rows"]:
        assert set(row) == set(annotation.OCCURRENCE_KEYS)
        assert row["occurrence_kind"] in OCCURRENCE_KINDS
        assert row["source_document_id"] == document_id
        assert row["source_locator_id"] == locator_id
        assert row["interview_wave"] == INTERVIEW_WAVE
        start, end = row["utf8_byte_start"], row["utf8_byte_end"]
        assert 0 <= start < end
        raw = page_texts[row["page_number"] - 1].encode("utf-8")[start:end]
        assert raw.decode("utf-8", errors="strict") == row["matched_text"]
        assert row["matched_text"] != ""
        assert _sha256(raw) == row["matched_utf8_sha256"]
        assert row["questionnaire_occurrence_id"] == (
            "psid-questionnaire-occurrence:"
            + annotation._canonical_digest(
                [row[key] for key in annotation.OCCURRENCE_KEYS[1:]]
            )
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


def test_atomic_span_kind_ordinals_are_unique_and_contiguous(
    sealed: dict,
) -> None:
    ordinals_by_coordinate: dict[tuple[int, int, int, str], set[int]] = {}
    for row in sealed["questionnaire_occurrence_rows"]:
        coordinate = (
            row["page_number"],
            row["utf8_byte_start"],
            row["utf8_byte_end"],
            row["occurrence_kind"],
        )
        ordinal = row["semantic_ordinal_at_span"]
        seen = ordinals_by_coordinate.setdefault(coordinate, set())
        assert ordinal not in seen
        seen.add(ordinal)
        if row["occurrence_kind"] != "flow_branch_label":
            assert ordinal == 0
    for coordinate, ordinals in ordinals_by_coordinate.items():
        if coordinate[-1] == "flow_branch_label":
            assert ordinals == set(range(len(ordinals)))
        else:
            assert ordinals == {0}
    multiparent = [
        row
        for row in sealed["questionnaire_occurrence_rows"]
        if row["matched_text"] == "(IF YES TO F2 OR TO F6)"
    ]
    assert len(multiparent) == 2
    assert {row["semantic_ordinal_at_span"] for row in multiparent} == {0, 1}
    assert (
        len({tuple(row["flow_branch_paths"][0]) for row in multiparent}) == 2
    )


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
    paths_by_id = {
        r["flow_branch_id"]: r["branch_path"]
        for r in sealed["flow_branch_rows"]
    }
    lawful = {(annotation.FLOW_ROOT,)} | {
        tuple(p) for p in paths_by_id.values()
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


def test_terminal_answer_routes_keep_exact_parent_ancestry(
    sealed: dict,
) -> None:
    """Terminal arrows retain the exact previously emitted parent path."""

    occurrences = {
        row["questionnaire_occurrence_id"]: row
        for row in sealed["questionnaire_occurrence_rows"]
    }
    terminal = [
        row
        for row in sealed["flow_branch_rows"]
        if "GO TO" in row["branch_label"].upper()
        or "TURN TO" in row["branch_label"].upper()
    ]
    assert terminal
    for row in terminal:
        source = occurrences[row["source_occurrence_id"]]
        assert len(source["flow_branch_paths"]) == 1
        parent_path = source["flow_branch_paths"][0]
        assert parent_path
        assert row["parent_flow_branch_id"] == parent_path[-1]
        assert row["parent_flow_branch_id"] != annotation.FLOW_ROOT


def test_local_anchor_and_repeat_rows_stay_document_local(
    sealed: dict,
) -> None:
    occurrences = {
        r["questionnaire_occurrence_id"]: r
        for r in sealed["questionnaire_occurrence_rows"]
    }
    anchors = sealed["local_anchor_classification_rows"]
    anchor_kinds = {
        r["occurrence_kind"]
        for r in sealed["questionnaire_occurrence_rows"]
        if r["occurrence_kind"] in annotation.ANCHOR_KINDS
    }
    assert anchor_kinds
    assert len(anchors) == sum(
        1
        for r in sealed["questionnaire_occurrence_rows"]
        if r["occurrence_kind"] in annotation.ANCHOR_KINDS
    )
    for row in anchors:
        assert set(row) == set(annotation.LOCAL_ANCHOR_KEYS)
        assert row["classification_status"] == "provisional_document_local"
        source = occurrences[row["source_occurrence_id"]]
        assert row["occurrence_kind"] == source["occurrence_kind"]
        assert row["exact_label"] == source["matched_text"]
        assert row["exact_label_sha256"] == source["matched_utf8_sha256"]
        if row["node_domain"] == "role":
            assert row["classification"] in annotation.ROLE_CLASSIFICATIONS

    repeats = sealed["local_repeat_alias_evidence_rows"]
    instructions = [
        r
        for r in sealed["questionnaire_occurrence_rows"]
        if r["occurrence_kind"] == "repeat_or_alias_instruction"
    ]
    assert len(repeats) == len(instructions)
    consumed: set[str] = set()
    for row in repeats:
        assert set(row) == set(annotation.LOCAL_REPEAT_KEYS)
        assert row["relation"] in annotation.ALIAS_RELATIONS
        assert row["source_occurrence_id"] in row["evidence_occurrence_ids"]
        assert row["evidence_occurrence_ids"]
        consumed.add(row["source_occurrence_id"])
    assert consumed == {r["questionnaire_occurrence_id"] for r in instructions}


def test_source_review_is_complete_sealed_input(
    sealed: dict, page_texts: list[str]
) -> None:
    review = json.loads(annotation.REVIEW_PATH.read_text(encoding="utf-8"))
    inputs = annotation._inputs()
    assert inputs[5] == review
    annotation.validate_review(review, inputs[2], page_texts)
    assert review["document_source_position"] == DOCUMENT_SOURCE_POSITION
    assert review["source_document_id"] == (
        sealed["whole_document_locator"]["source_document_id"]
    )
    assert review["review_method"]["whole_page_review"] == (
        "all_68_pages_including_empty_occurrence_pages"
    )
    assert review["review_method"]["global_ids_assigned"] is False
    assert review["status"] == "complete"
    assert review["integrity"]["content_sha256"] == (
        annotation._content_sha256(review)
    )


def test_document_011_retained_and_rejected_boundaries(
    sealed: dict, page_texts: list[str]
) -> None:
    rows = sealed["questionnaire_occurrence_rows"]
    by_page = {
        page: [row for row in rows if row["page_number"] == page]
        for page in range(1, PAGE_COUNT + 1)
    }
    populated = {page for page, page_rows in by_page.items() if page_rows}
    assert KNOWN_EMPTY_PAGES.isdisjoint(populated)
    assert KNOWN_INSTRUMENT_PAGES <= populated

    # Transportation, housing, housework/food, education, health, and
    # observation prose can contain employment-like words but remains outside
    # R_Q. The explicit empty-page boundary makes those false positives fail.
    assert all(not by_page[page] for page in KNOWN_EMPTY_PAGES)

    counts = Counter(row["occurrence_kind"] for row in rows)
    assert counts["role_total_anchor"] == 4
    assert counts["farm_aggregate_anchor"] >= 3
    assert counts["business_aggregate_anchor"] >= 3
    aggregates = {
        (row["occurrence_kind"], row["page_number"], row["matched_text"])
        for row in rows
        if row["occurrence_kind"]
        in {"farm_aggregate_anchor", "business_aggregate_anchor"}
    }
    assert {
        ("farm_aggregate_anchor", 37, "net income from farming"),
        ("business_aggregate_anchor", 37, "unincorporated business"),
    } <= aggregates
    wife_total_objective = [
        row
        for row in by_page[48]
        if (row["utf8_byte_start"], row["utf8_byte_end"]) == (936, 1307)
    ]
    assert {row["occurrence_kind"] for row in wife_total_objective} == {
        "role_total_anchor",
        "field_purpose_prompt",
        "repeat_or_alias_instruction",
    }

    # The core questionnaire job anchors actually parent local source fields;
    # objective-sheet job anchors may instead preserve exact scope evidence.
    parent_ids = {
        parent_id
        for row in sealed["local_anchor_classification_rows"]
        for parent_id in row["parent_source_occurrence_ids"]
    }
    core_parent_texts = {
        row["matched_text"]
        for row in rows
        if row["questionnaire_occurrence_id"] in parent_ids
        and row["occurrence_kind"] == "job_anchor"
    }
    assert {
        "present jop",
        "main job",
        "extra jobs",
        "last job",
        "job do you have in mind",
        "(OCCUPATION)",
        "first full time regular job",
    } <= core_parent_texts

    # D26 is an additional-duty probe within the current D25 job, not an
    # instruction to repeat a job inventory.
    d26_rows = [
        row
        for row in by_page[17]
        if (row["utf8_byte_start"], row["utf8_byte_end"]) == (347, 366)
    ]
    assert {row["occurrence_kind"] for row in d26_rows} == {
        "context_anchor",
        "field_purpose_prompt",
    }
    assert {row["matched_text"] for row in d26_rows} == {"D26. Anything else?"}

    # Page 53 changes from the income schedule to support, background, and
    # union questions at H36. Nothing at or after that exact boundary belongs
    # in this document's R_Q annotation.
    page_53_raw = page_texts[52].encode("utf-8")
    h36_start = page_53_raw.index(b"H36.")
    assert by_page[53]
    assert all(row["utf8_byte_end"] <= h36_start for row in by_page[53])

    # H21's full printed condition is the branch atom. A later incomplete H11
    # parenthetical fragment is deliberately not promoted to a branch label.
    h21_exit = [
        row
        for row in by_page[49]
        if (row["utf8_byte_start"], row["utf8_byte_end"]) == (278, 325)
    ]
    assert len(h21_exit) == 1
    assert h21_exit[0]["occurrence_kind"] == "flow_branch_label"
    assert h21_exit[0]["matched_text"] == (
        "IF NO SUCH PEOPLE,\n        TURN TO H32, PAGE 20"
    )
    assert not any(
        row["matched_text"].startswith('(IF "YES" TO ANY') for row in rows
    )
    assert [
        row["matched_text"]
        for row in by_page[49]
        if row["occurrence_kind"] == "role_anchor"
        and (row["utf8_byte_start"], row["utf8_byte_end"]) == (359, 375)
    ] == ["RELATION TO HEAD"]
    h21_objective = [
        row
        for row in by_page[50]
        if (row["utf8_byte_start"], row["utf8_byte_end"]) == (40, 727)
    ]
    assert {row["occurrence_kind"] for row in h21_objective} == {
        "context_anchor",
        "field_purpose_prompt",
        "repeat_or_alias_instruction",
    }
    h21_repeat = next(
        row
        for row in h21_objective
        if row["occurrence_kind"] == "repeat_or_alias_instruction"
    )
    h21_repeat_evidence = next(
        row
        for row in sealed["local_repeat_alias_evidence_rows"]
        if row["source_occurrence_id"]
        == h21_repeat["questionnaire_occurrence_id"]
    )
    assert len(h21_repeat_evidence["alias_anchor_source_occurrence_ids"]) == 1
    assert (
        len(h21_repeat_evidence["canonical_anchor_source_occurrence_ids"]) == 1
    )
    occurrence_by_id = {
        row["questionnaire_occurrence_id"]: row for row in rows
    }
    h21_alias = occurrence_by_id[
        h21_repeat_evidence["alias_anchor_source_occurrence_ids"][0]
    ]
    h21_canonical = occurrence_by_id[
        h21_repeat_evidence["canonical_anchor_source_occurrence_ids"][0]
    ]
    assert (
        h21_alias["page_number"],
        h21_alias["utf8_byte_start"],
        h21_alias["utf8_byte_end"],
    ) == (50, 40, 727)
    assert (
        h21_canonical["page_number"],
        h21_canonical["utf8_byte_start"],
        h21_canonical["utf8_byte_end"],
    ) == (49, 59, 387)

    # Page 51 is a row-major three-person grid. Each printed amount cell is a
    # distinct source atom and its H29 path remains in the matching column.
    amount_rows = [
        row
        for row in by_page[51]
        if row["occurrence_kind"] == "remuneration_component_anchor"
    ]
    assert {
        (row["utf8_byte_start"], row["utf8_byte_end"]) for row in amount_rows
    } == {
        (843, 881),
        (918, 927),
        (964, 971),
        (2512, 2550),
        (2558, 2595),
        (2607, 2641),
    }
    first_amounts = sorted(
        amount_rows[:3], key=lambda row: row["utf8_byte_start"]
    )
    second_amounts = sorted(
        amount_rows[3:], key=lambda row: row["utf8_byte_start"]
    )
    for first, second in zip(first_amounts, second_amounts, strict=True):
        first_path = first["flow_branch_paths"][0]
        second_path = second["flow_branch_paths"][0]
        assert second_path[: len(first_path)] == first_path
    grid_repeat = [
        row
        for row in by_page[51]
        if row["occurrence_kind"] == "repeat_or_alias_instruction"
    ]
    assert [
        (row["utf8_byte_start"], row["utf8_byte_end"]) for row in grid_repeat
    ] == [(330, 837), (1980, 2241)]
    assert [len(row["flow_branch_paths"]) for row in grid_repeat] == [1, 3]

    # H33 has three distinct relationship columns and an exact instruction to
    # administer the retained H22-H31 schedule to those additional members.
    relation_coordinates = {(248, 264), (281, 297), (308, 324)}
    for coordinate in relation_coordinates:
        relation_rows = [
            row
            for row in by_page[53]
            if (row["utf8_byte_start"], row["utf8_byte_end"]) == coordinate
        ]
        assert {row["occurrence_kind"] for row in relation_rows} == {
            "role_anchor",
            "context_anchor",
            "field_purpose_prompt",
        }
        assert {row["matched_text"] for row in relation_rows} == {
            "RELATION TO HEAD"
        }
    h33_repeat = next(
        row
        for row in by_page[53]
        if row["occurrence_kind"] == "repeat_or_alias_instruction"
        and (row["utf8_byte_start"], row["utf8_byte_end"]) == (358, 414)
    )
    repeat_evidence = next(
        row
        for row in sealed["local_repeat_alias_evidence_rows"]
        if row["source_occurrence_id"]
        == h33_repeat["questionnaire_occurrence_id"]
    )
    assert len(repeat_evidence["alias_anchor_source_occurrence_ids"]) == 13
    assert repeat_evidence["canonical_anchor_source_occurrence_ids"] == []
    linked_schedule = {
        occurrence_by_id[occurrence_id]["utf8_byte_start"]
        for occurrence_id in repeat_evidence[
            "alias_anchor_source_occurrence_ids"
        ]
    }
    assert {
        397,
        756,
        841,
        860,
        878,
        1130,
        1237,
        1259,
        1423,
        1556,
        1611,
        2044,
        2159,
    } <= linked_schedule

    # K1 carries its instrument-side new-head role atom. K3's objective block
    # then defines which father supplies the retained occupation field.
    assert [
        row["matched_text"]
        for row in by_page[55]
        if row["occurrence_kind"] == "role_anchor"
        and (row["utf8_byte_start"], row["utf8_byte_end"]) == (1277, 1281)
    ] == ["HEAD"]
    k3_scope = [
        row
        for row in by_page[58]
        if (row["utf8_byte_start"], row["utf8_byte_end"]) == (60, 224)
    ]
    assert {row["occurrence_kind"] for row in k3_scope} == {
        "context_anchor",
        "field_purpose_prompt",
    }
    assert all(
        "not living with his father" in row["matched_text"] for row in k3_scope
    )

    # The H11 source inventory deliberately retains nonwork sources as
    # classification boundaries.  The known false-positive work domains do
    # not enter any occurrence kind.
    all_occurrence_text = " ".join(row["matched_text"].lower() for row in rows)
    for rejected_term in (
        "child care",
        "housework",
        "belong to a labor union",
    ):
        assert rejected_term not in all_occurrence_text


def test_seal_census_matches_emitted_rows(sealed: dict) -> None:
    seal = sealed["seal"]
    assert seal["whole_document_review_complete"] is True
    assert seal["candidate_domain_exact_cover"] is True
    assert seal["output_domain_exact_cover"] is True
    assert seal["global_ids_assigned"] is False
    assert seal["questionnaire_page_count"] == PAGE_COUNT
    assert seal["empty_occurrence_page_count"] == sum(
        not row["questionnaire_occurrence_ids"]
        for row in sealed["questionnaire_page_rows"]
    )
    assert seal["questionnaire_occurrence_count"] == len(
        sealed["questionnaire_occurrence_rows"]
    )
    assert seal["flow_branch_count"] == len(sealed["flow_branch_rows"])
    assert seal["local_anchor_classification_count"] == len(
        sealed["local_anchor_classification_rows"]
    )
    assert seal["local_repeat_alias_evidence_count"] == len(
        sealed["local_repeat_alias_evidence_rows"]
    )
    assert seal["candidate_disposition_count"] == len(
        sealed["candidate_disposition_rows"]
    )
    assert seal["output_adjudication_count"] == len(
        sealed["output_adjudication_rows"]
    )


def test_candidate_disposition_relation_exact_covers_the_domain(
    sealed: dict,
) -> None:
    rows = sealed["candidate_disposition_rows"]
    index = json.loads(
        (
            ROOT
            / "docs"
            / "analysis"
            / "rq_stage1_candidates"
            / "index_v1.json"
        ).read_text(encoding="utf-8")
    )
    manifest = next(
        row
        for row in index["document_candidate_manifest_rows"]
        if row["document_source_position"] == DOCUMENT_SOURCE_POSITION
    )
    assert manifest["page_count"] == PAGE_COUNT
    expected_by_kind = {
        "whole_document_locator": 1,
        "page": PAGE_COUNT,
        "occurrence": manifest["candidate_occurrence_count"],
        "flow_path": manifest["candidate_flow_path_count"],
        "anchor_classification": manifest[
            "candidate_anchor_classification_count"
        ],
    }
    assert Counter(r["candidate_row_kind"] for r in rows) == expected_by_kind
    expected = sum(expected_by_kind.values())
    assert len(rows) == expected
    assert len({r["candidate_id"] for r in rows}) == expected
    output_ids = {
        r["stage2_row_id"] for r in sealed["output_adjudication_rows"]
    }
    for row in rows:
        assert set(row) == set(annotation.CANDIDATE_DISPOSITION_KEYS)
        assert row["candidate_row_kind"] in annotation.CANDIDATE_ROW_KINDS
        assert row["adjudication_status"] == "complete"
        named = row["stage2_row_ids"]
        if row["disposition"] in {"accepted", "modified"}:
            assert len(named) == 1
        elif row["disposition"] == "split":
            assert len(named) >= 2
        else:
            assert row["disposition"] == "rejected"
            assert named == []
        assert set(named) <= output_ids


def test_output_adjudication_relation_exact_covers_every_row(
    sealed: dict,
) -> None:
    emitted = (
        1
        + len(sealed["questionnaire_page_rows"])
        + len(sealed["questionnaire_occurrence_rows"])
        + len(sealed["flow_branch_rows"])
        + len(sealed["local_anchor_classification_rows"])
        + len(sealed["local_repeat_alias_evidence_rows"])
    )
    rows = sealed["output_adjudication_rows"]
    assert len(rows) == emitted
    assert len({r["stage2_row_id"] for r in rows}) == emitted
    candidate_ids = {
        r["candidate_id"] for r in sealed["candidate_disposition_rows"]
    }
    for row in rows:
        assert set(row) == set(annotation.OUTPUT_ADJUDICATION_KEYS)
        assert row["adjudication_status"] == "complete"
        assert row["stage2_row_kind"] in annotation.STAGE2_ROW_KINDS
        assert set(row["source_candidate_ids"]) <= candidate_ids
        if row["adjudication_action"] == "manual_add":
            assert row["source_candidate_ids"] == []
            assert row["whole_page_review_complete"] is True
            assert row["source_span_verified"] is True
        else:
            assert row["source_candidate_ids"]


def test_two_adjudication_relations_agree_in_both_directions(
    sealed: dict,
) -> None:
    forward: set[tuple[str, str]] = set()
    for row in sealed["candidate_disposition_rows"]:
        for stage2_row_id in row["stage2_row_ids"]:
            forward.add((row["candidate_id"], stage2_row_id))
    backward: set[tuple[str, str]] = set()
    for row in sealed["output_adjudication_rows"]:
        for candidate_id in row["source_candidate_ids"]:
            backward.add((candidate_id, row["stage2_row_id"]))
    assert forward == backward


def test_whole_page_review_covers_every_page(sealed: dict) -> None:
    review = json.loads(annotation.REVIEW_PATH.read_text(encoding="utf-8"))
    rows = review["page_review_rows"]
    assert len(rows) == PAGE_COUNT
    assert [r["page_number"] for r in rows] == list(range(1, PAGE_COUNT + 1))
    for row in rows:
        assert row["whole_page_review_complete"] is True
        assert row["review_status"] == "complete"
        assert row["review_note"].strip()


def test_shard_states_nonauthority_and_emits_no_global_id(
    sealed: dict,
) -> None:
    assert (
        sealed["status"] == "sealed_complete_nonauthority_document_annotation"
    )
    assert sealed["authority_kind"] == (
        "document_local_source_annotation_nonauthority"
    )
    assert sealed["document_source_position"] == DOCUMENT_SOURCE_POSITION
    raw = ANNOTATION_PATH.read_text(encoding="utf-8")
    # Collect first, then assert on the small list: asserting ``token not in
    # raw`` directly makes pytest introspect a multi-megabyte string on
    # failure, which stalls the run instead of reporting the offending token.
    found = [
        token
        for token in (
            *FORBIDDEN_ID_PREFIXES,
            "questionnaire_slot_id",
            "global_relationship_rows",
        )
        if token in raw
    ]
    assert found == []


def test_rebuilt_rows_carry_the_displayed_member_order() -> None:
    """The sealed file is canonical JSON, so member order is checked here.

    Canonicalisation sorts object members, which is why the file-level
    assertions above compare keysets.  The displayed-order law of the
    protocol applies to the constructed rows, so it is asserted against the
    rebuilt in-memory value.
    """

    if not SOURCE_PDF.is_file():
        pytest.skip("PSID questionnaire capture is not staged")
    rebuilt = annotation.build_annotation(*annotation._inputs())
    assert list(rebuilt["whole_document_locator"]) == list(
        annotation.LOCATOR_KEYS
    )
    for name, keys in (
        ("questionnaire_page_rows", annotation.PAGE_KEYS),
        ("questionnaire_occurrence_rows", annotation.OCCURRENCE_KEYS),
        ("flow_branch_rows", annotation.FLOW_BRANCH_KEYS),
        ("local_anchor_classification_rows", annotation.LOCAL_ANCHOR_KEYS),
        ("local_repeat_alias_evidence_rows", annotation.LOCAL_REPEAT_KEYS),
        (
            "candidate_disposition_rows",
            annotation.CANDIDATE_DISPOSITION_KEYS,
        ),
        ("output_adjudication_rows", annotation.OUTPUT_ADJUDICATION_KEYS),
    ):
        for row in rebuilt[name]:
            assert list(row) == list(keys)


def test_committed_artifacts_reproduce_and_mutations_fail_closed() -> None:
    if not SOURCE_PDF.is_file():
        pytest.skip("PSID questionnaire capture is not staged")
    inputs = annotation._inputs()
    rebuilt = annotation.build_annotation(*inputs)
    assert annotation._canonical_bytes(rebuilt) == (
        ANNOTATION_PATH.read_bytes()
    )
    annotation.validate_annotation(rebuilt, *inputs)
    annotation.run_mutation_tests(rebuilt, inputs)
