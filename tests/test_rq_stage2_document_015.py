"""Independent validation of the sealed R_Q document-15 annotation.

Every row assertion below is re-derived from ``fam1975_QxQs.pdf`` through the
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
SOURCE_PDF = CAPTURE_ROOT / "fam1975_QxQs.pdf"
ANNOTATION_PATH = (
    ROOT
    / "docs"
    / "analysis"
    / "rq_stage2_annotations"
    / "document_015_fam1975_QxQs_annotation_v1.json"
)

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_rq_stage2_document_015_annotation as annotation  # noqa: E402

DOCUMENT_SOURCE_POSITION = 15
INTERVIEW_WAVE = 1975
PAGE_COUNT = 74
FILE_SIZE = 21_042_075
FILE_SHA256 = (
    "13c2298541d1488dcdf05cbf005fa2b0e46365506bcd3abbca10bb9e70d23410"
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
    assert locator["filename"] == "fam1975_QxQs.pdf"
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


RETAINED_PAGES = frozenset(
    (
        16,
        20,
        22,
        24,
        25,
        28,
        29,
        32,
        33,
        34,
        35,
        38,
        39,
        40,
        42,
        43,
        44,
        48,
        49,
        62,
        64,
        65,
        68,
        69,
    )
)


def test_empty_occurrence_pages_are_still_emitted(sealed: dict) -> None:
    rows = sealed["questionnaire_page_rows"]
    empty = [r for r in rows if not r["questionnaire_occurrence_ids"]]
    assert len(empty) == PAGE_COUNT - len(RETAINED_PAGES)
    assert {
        r["page_number"] for r in rows if r["questionnaire_occurrence_ids"]
    } == set(RETAINED_PAGES)
    # Printed screens and explicit objectives-sheet cross-references are
    # retained; all 50 other pages remain explicit empty-occurrence rows.
    assert len(empty) == 50


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
    branches = sealed["flow_branch_rows"]
    by_id = {row["flow_branch_id"]: row for row in branches}

    def parent_labels(page: int, label: str) -> Counter[str]:
        return Counter(
            (
                "ROOT"
                if row["parent_flow_branch_id"] == annotation.FLOW_ROOT
                else by_id[row["parent_flow_branch_id"]]["branch_label"]
            )
            for row in branches
            if row["page_number"] == page and row["branch_label"] == label
        )

    def parent_labels_starting(page: int, prefix: str) -> Counter[str]:
        return Counter(
            (
                "ROOT"
                if row["parent_flow_branch_id"] == annotation.FLOW_ROOT
                else by_id[row["parent_flow_branch_id"]]["branch_label"]
            )
            for row in branches
            if row["page_number"] == page
            and row["branch_label"].startswith(prefix)
        )

    occurrences = sealed["questionnaire_occurrence_rows"]

    def terminal_path_labels(page: int, kind: str, text: str) -> set[str]:
        rows = [
            row
            for row in occurrences
            if row["page_number"] == page
            and row["occurrence_kind"] == kind
            and row["matched_text"] == text
        ]
        assert len(rows) == 1
        return {
            (
                "ROOT"
                if path[-1] == annotation.FLOW_ROOT
                else by_id[path[-1]]["branch_label"]
            )
            for path in rows[0]["flow_branch_paths"]
        }

    assert parent_labels(20, "(TURN TO PAGE 9, D24)") == Counter(
        {"3. SA£-fE": 1, "1 . BETTER": 1, "5 . HORSE": 1}
    )
    assert terminal_path_labels(
        20, "field_purpose_prompt", "D23 .       Why is that?"
    ) == {"1 . BETTER", "5 . HORSE"}

    assert terminal_path_labels(
        22, "context_anchor", "D26 .     How much vacation did you take?"
    ) == {"IL YES"}
    assert terminal_path_labels(
        22, "context_anchor", "D28.      How much did you miss?"
    ) == {"I 1. YES"}
    assert terminal_path_labels(
        22, "context_anchor", "DJO.      How much work did you miss?"
    ) == {"I 1. YES"}
    assert terminal_path_labels(
        22,
        "context_anchor",
        "D35 .   How many hours did that overtime amount to in 1974? - ; - - - , -",
    ) == {"( ] YES"}

    assert parent_labels_starting(28, "(TURN TO         .") == Counter(
        {"I 00. NONE l": 1}
    )
    assert parent_labels(38, "(GO TO I-IS)") == Counter(
        {"5. NOT A FARMER OR RANCHER": 1}
    )
    assert parent_labels(38, "(GO TO I-18)") == Counter(
        {"1.   CORPORATION": 1}
    )
    assert terminal_path_labels(
        42,
        "field_purpose_prompt",
        "I HlO . How much was that? $___________________",
    ) == {"[ ] YES"}

    assert parent_labels_starting(48, "(TURN TO\n") == Counter(
        {"[ ] NO WIFE IN FU OR FU HAS FE~~LE HEAD": 1}
    )
    assert terminal_path_labels(
        48,
        "context_anchor",
        "H25 .     Was it income from wages, salary, a business, or what?",
    ) == {"[ ] YES"}
    assert terminal_path_labels(
        48,
        "remuneration_component_anchor",
        "H26 .     How much was it before deductions?",
    ) == {"[ ] YES"}

    assert parent_labels(62, "(TURN TO PAGE E_~) Hl)") == Counter(
        {
            "5 . FU HAS SAME WIFE AS IN 1974": 1,
            "OR FU HAS NO WIFE": 1,
            "OR FU HAS FEHALE HEAD": 1,
        }
    )
    assert parent_labels_starting(62, "(TURN TO\n") == Counter(
        {"i 00 . NONE I": 1, "ALL I": 1}
    )
    assert parent_labels(64, "(TURN TO PAGE 3 OF COVER SHEET)") == Counter(
        {"5 . THIS FU HAS THE SA}fE HEAD AS IN 1974": 1}
    )
    assert parent_labels(64, "(GO TO M6).") == Counter({"0. NEVER WORKED": 1})
    assert parent_labels(68, "(GO TO M29)") == Counter(
        {"00. NONE I": 1, "AL_L": 1}
    )


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
        "all_74_pages_including_empty_occurrence_pages"
    )
    assert review["review_method"]["global_ids_assigned"] is False
    assert review["status"] == "complete"
    assert review["integrity"]["content_sha256"] == (
        annotation._content_sha256(review)
    )


def test_document_015_retained_and_rejected_boundaries(
    sealed: dict,
) -> None:
    rows = sealed["questionnaire_occurrence_rows"]
    by_page = {
        page: [row for row in rows if row["page_number"] == page]
        for page in range(1, PAGE_COUNT + 1)
    }
    assert {page for page, page_rows in by_page.items() if page_rows} == set(
        RETAINED_PAGES
    )

    # Housing, transport, counterfactual labor-supply, commuting, food,
    # other-member income, health, education, and observation pages stay out.
    rejected_pages = (
        set(range(1, 16))
        | {17, 18, 19, 21, 23, 26, 27, 30, 31, 36, 37, 41, 45, 46, 47}
        | set(range(50, 62))
        | {63, 66, 67}
        | set(range(70, 75))
    )
    assert rejected_pages == set(range(1, PAGE_COUNT + 1)) - set(
        RETAINED_PAGES
    )
    assert all(not by_page[page] for page in rejected_pages)

    # Objectives pages contribute only independently located, explicit
    # repeat/cross-reference instructions.
    objectives_with_evidence = {
        25,
        29,
        33,
        35,
        39,
        40,
        43,
        44,
        49,
        65,
        69,
    }
    assert all(
        {row["occurrence_kind"] for row in by_page[page]}
        == {"repeat_or_alias_instruction"}
        for page in objectives_with_evidence
    )

    counts = Counter(row["occurrence_kind"] for row in rows)
    assert counts["role_total_anchor"] == 0
    assert counts["farm_aggregate_anchor"] == 1
    assert counts["business_aggregate_anchor"] == 1

    aggregates = {
        (row["occurrence_kind"], row["page_number"], row["matched_text"])
        for row in rows
        if row["occurrence_kind"]
        in {"farm_aggregate_anchor", "business_aggregate_anchor"}
    }
    assert aggregates == {
        ("farm_aggregate_anchor", 38, "net income from farming"),
        ("business_aggregate_anchor", 38, "unincorporated business"),
    }

    jobs = {
        (row["page_number"], row["matched_text"])
        for row in rows
        if row["occurrence_kind"] == "job_anchor"
    }
    assert jobs == {
        (16, "present job"),
        (20, "this job"),
        (20, "the job you had before"),
        (22, "main job"),
        (24, "extra jobs"),
        (28, "job"),
        (28, "last job"),
        (32, "job"),
        (64, "first full time regular job"),
    }

    component_pages = {
        row["page_number"]
        for row in rows
        if row["occurrence_kind"] == "remuneration_component_anchor"
    }
    assert component_pages == {24, 28, 32, 38, 42, 48}
    assert any(
        row["page_number"] == 24
        and row["occurrence_kind"] == "remuneration_component_anchor"
        and row["matched_text"].startswith("v~at    is your hourly wage rate")
        for row in rows
    )
    assert any(
        row["page_number"] == 48
        and row["occurrence_kind"] == "remuneration_component_anchor"
        and row["matched_text"]
        == "H26 .     How much was it before deductions?"
        for row in rows
    )

    # Clear hyphenated item identifiers are preserved rather than dropped by
    # the local source parser.
    anchor_by_occurrence = {
        row["source_occurrence_id"]: row
        for row in sealed["local_anchor_classification_rows"]
    }
    hyphenated = {
        anchor_by_occurrence[row["questionnaire_occurrence_id"]][
            "printed_identifier"
        ]
        for row in by_page[38]
        if row["occurrence_kind"] in annotation.ANCHOR_KINDS
        and row["matched_text"].startswith(
            ("I-12", "I-13", "I-16", "I-17", "I-18")
        )
    }
    assert hyphenated == {"I-12", "I-13", "I-16", "I-17", "I-18"}

    # The document-local parser preserves exact OCR tokens, including a
    # lowercase OCR digit substitution and M26's printed-text H26 error.
    expected_spaced_identifiers = {
        (20, "this job"): "Dl8",
        (
            24,
            "D44.    About how much did you make per hour at this? $                  per hour",
        ): "D44",
        (
            68,
            "H26.    How many years have you (HEAD) worked since you were 18?",
        ): "H26",
    }
    for (
        page,
        text,
    ), expected_identifier in expected_spaced_identifiers.items():
        matching = [
            row
            for row in by_page[page]
            if row["matched_text"] == text
            and row["occurrence_kind"] in annotation.ANCHOR_KINDS
        ]
        assert len(matching) == 1
        assert (
            anchor_by_occurrence[matching[0]["questionnaire_occurrence_id"]][
                "printed_identifier"
            ]
            == expected_identifier
        )

    present_job = next(
        row
        for row in by_page[16]
        if row["occurrence_kind"] == "job_anchor"
        and row["matched_text"] == "present job"
    )
    present_job_children = {
        anchor_by_occurrence[row["questionnaire_occurrence_id"]]["exact_label"]
        for row in by_page[16]
        if row["occurrence_kind"] == "context_anchor"
        and present_job["questionnaire_occurrence_id"]
        in anchor_by_occurrence[row["questionnaire_occurrence_id"]][
            "parent_source_occurrence_ids"
        ]
    }
    assert len(present_job_children) == 7
    assert {label.splitlines()[0] for label in present_job_children} == {
        "!)2 .    What is your mai n occupation?                           (What sor t of work do you do?)",
        "D4.      What kind of bu s iness is t h at in ?",
        "DS .     Do you work for someone else, yo ur se lf , or what?",
        "Federal, State or",
        "inc orp or ated?",
        "Dll .     Is your busine ss",
        "St:~lte or 1ucal Government?",
    }

    repeat_texts = {
        (row["page_number"], row["matched_text"])
        for row in rows
        if row["occurrence_kind"] == "repeat_or_alias_instruction"
    }
    assert any(
        page == 33 and "(see 02-03)" in text for page, text in repeat_texts
    )
    assert (
        48,
        "Hl9.    INTERVIEWER:        REFER TO Hllf and CHECK ONE .",
    ) in repeat_texts

    assert any(
        row["page_number"] == 34
        and row["occurrence_kind"] == "field_purpose_prompt"
        and row["matched_text"].startswith("Gl .   Are you married")
        for row in rows
    )
    assert any(
        row["page_number"] == 64
        and row["occurrence_kind"] == "flow_branch_label"
        and row["matched_text"] == "SECTION M:   NEW HEAD"
        for row in rows
    )
    assert {
        row["matched_text"]
        for row in by_page[42]
        if row["occurrence_kind"] == "remuneration_component_anchor"
    } >= {"b) farming or market gardening,", "roomers or boarders?"}

    # Page 42 retains work-income sources only; asset/transfer categories do
    # not masquerade as remuneration components.
    page_42_nonflow = " ".join(
        row["matched_text"].lower()
        for row in by_page[42]
        if row["occurrence_kind"]
        in {"remuneration_component_anchor", "context_anchor"}
    )
    for rejected_term in ("dividends", "interest", "trust funds", "alimony"):
        assert rejected_term not in page_42_nonflow

    nonflow = " ".join(
        row["matched_text"]
        for row in rows
        if row["occurrence_kind"]
        not in {"flow_branch_label", "repeat_or_alias_instruction"}
    )
    for excluded_prompt in (
        "Dl4.        Do you supervise",
        "Gll . About how much time",
        "M29.    Do you have a physical",
    ):
        assert excluded_prompt not in nonflow


def test_seal_census_matches_emitted_rows(sealed: dict) -> None:
    seal = sealed["seal"]
    assert seal["whole_document_review_complete"] is True
    assert seal["candidate_domain_exact_cover"] is True
    assert seal["output_domain_exact_cover"] is True
    assert seal["global_ids_assigned"] is False
    assert seal["questionnaire_page_count"] == PAGE_COUNT
    assert seal["empty_occurrence_page_count"] == (
        PAGE_COUNT - len(RETAINED_PAGES)
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
