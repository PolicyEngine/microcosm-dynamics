"""Independent validation of the sealed R_Q document-3 annotation.

Every row assertion below is re-derived from ``fam1969_QxQs.pdf`` through the
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
SOURCE_PDF = CAPTURE_ROOT / "fam1969_QxQs.pdf"
ANNOTATION_PATH = (
    ROOT
    / "docs"
    / "analysis"
    / "rq_stage2_annotations"
    / "document_003_fam1969_QxQs_annotation_v1.json"
)

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_rq_stage2_document_003_annotation as annotation  # noqa: E402

DOCUMENT_SOURCE_POSITION = 3
INTERVIEW_WAVE = 1969
PAGE_COUNT = 47
FILE_SIZE = 19_003_206
FILE_SHA256 = (
    "54106e94319c099e7a7272622965b345eae74b3001035c295500ea1db33f8138"
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
    assert locator["filename"] == "fam1969_QxQs.pdf"
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
    frozenset(range(1, 6))
    | {7}
    | frozenset(range(13, 16))
    | frozenset(range(20, 24))
    | frozenset(range(28, 31))
    | frozenset(range(32, 45))
    | {46, 47}
)
KNOWN_INSTRUMENT_PAGES = frozenset(
    {6, 8, 9, 10, 11, 12, 16, 17, 18, 19, 24, 25, 26, 27, 31, 45}
)


def test_empty_occurrence_pages_are_still_emitted(sealed: dict) -> None:
    rows = sealed["questionnaire_page_rows"]
    empty = [r for r in rows if not r["questionnaire_occurrence_ids"]]
    empty_pages = {r["page_number"] for r in empty}
    populated_pages = {
        r["page_number"] for r in rows if r["questionnaire_occurrence_ids"]
    }
    assert KNOWN_EMPTY_PAGES == empty_pages
    assert KNOWN_INSTRUMENT_PAGES == populated_pages
    assert empty_pages | populated_pages == set(range(1, PAGE_COUNT + 1))
    assert empty_pages.isdisjoint(populated_pages)
    assert len(empty) == sealed["seal"]["empty_occurrence_page_count"]


def test_every_occurrence_slice_and_id_recomputes(
    sealed: dict, page_texts: list[str]
) -> None:
    document_id = sealed["whole_document_locator"]["source_document_id"]
    locator_id = sealed["whole_document_locator"]["locator_id"]
    canonical_source_path = sealed["document_source_row"][
        "canonical_source_path"
    ]
    locator_digests = set()
    occurrence_ids = set()
    coordinates = set()
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
        expected_locator_digest = annotation._canonical_digest(
            [
                document_id,
                canonical_source_path,
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
        assert row["source_locator_sha256"] == expected_locator_digest
        assert row["questionnaire_occurrence_id"] == (
            "psid-questionnaire-occurrence:"
            + annotation._canonical_digest(
                [row[key] for key in annotation.OCCURRENCE_KEYS[1:]]
            )
        )
        coordinate = (
            document_id,
            row["page_number"],
            start,
            end,
            row["occurrence_kind"],
            row["semantic_ordinal_at_span"],
        )
        assert expected_locator_digest not in locator_digests
        assert row["questionnaire_occurrence_id"] not in occurrence_ids
        assert coordinate not in coordinates
        locator_digests.add(expected_locator_digest)
        occurrence_ids.add(row["questionnaire_occurrence_id"])
        coordinates.add(coordinate)


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
    for label in ("(FOR UNINCORPORATED BUSINESSES)",):
        multiparent = [
            row
            for row in sealed["questionnaire_occurrence_rows"]
            if row["matched_text"] == label
        ]
        assert len(multiparent) == 2
        assert {row["semantic_ordinal_at_span"] for row in multiparent} == {
            0,
            1,
        }
        assert (
            len({tuple(row["flow_branch_paths"][0]) for row in multiparent})
            == 2
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


def test_terminal_routes_keep_exact_parent_ancestry(
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
        if "SKIP TO" in row["branch_label"].upper()
        or "OMITTED" in row["branch_label"].upper()
        or "NEED NOT BE ASKED" in row["branch_label"].upper()
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
    instruction_ids = {r["questionnaire_occurrence_id"] for r in instructions}
    same_identifier_rows = [
        row
        for row in repeats
        if row["relation"] == "same_printed_identifier_and_exact_label"
    ]
    assert len(repeats) == len(instructions) + 1
    assert len(same_identifier_rows) == 1
    consumed: set[str] = set()
    for row in repeats:
        assert set(row) == set(annotation.LOCAL_REPEAT_KEYS)
        assert row["relation"] in annotation.ALIAS_RELATIONS
        assert row["source_occurrence_id"] in row["evidence_occurrence_ids"]
        assert row["evidence_occurrence_ids"]
        if row["relation"] != "same_printed_identifier_and_exact_label":
            assert row["source_occurrence_id"] in instruction_ids
            consumed.add(row["source_occurrence_id"])
    assert consumed == instruction_ids


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
        "all_47_pages_including_empty_occurrence_pages"
    )
    assert review["review_method"]["global_ids_assigned"] is False
    assert review["status"] == "complete"
    assert review["integrity"]["content_sha256"] == (
        annotation._content_sha256(review)
    )


def test_document_003_flow_identifier_repeat_and_purpose_regressions(
    sealed: dict,
) -> None:
    occurrences = sealed["questionnaire_occurrence_rows"]
    branches = sealed["flow_branch_rows"]
    branch_paths = {
        row["branch_label"]: row["branch_path"] for row in branches
    }
    occupation_paths = sorted(
        [
            branch_paths["working\n          now"],
            branch_paths["looking for work"],
            branch_paths["retired, a housewife, or what?"],
        ],
        key=lambda path: tuple(item.encode("utf-8") for item in path),
    )
    occupation_purposes = [
        row
        for row in occurrences
        if row["occurrence_kind"] == "field_purpose_prompt"
        and (
            row["matched_text"].startswith(
                "Again, remember these questions refer to the head"
            )
            or row["matched_text"].startswith(
                "4.   Other particularly unacceptable answers"
            )
        )
    ]
    assert len(occupation_purposes) == 2
    assert all(
        row["flow_branch_paths"] == occupation_paths
        for row in occupation_purposes
    )

    working_path = branch_paths["working\n          now"]
    looking_path = branch_paths["looking for work"]
    unemployment_purposes = [
        row
        for row in occurrences
        if row["occurrence_kind"] == "field_purpose_prompt"
        and (
            row["matched_text"].startswith(
                "Unemployment here technically means completely without work."
            )
            or row["matched_text"].startswith(
                "For heads who are currently employed"
            )
        )
    ]
    assert len(unemployment_purposes) == 2
    common_unemployment = next(
        row
        for row in unemployment_purposes
        if row["matched_text"].startswith("Unemployment here technically")
    )
    employed_only = next(
        row
        for row in unemployment_purposes
        if row["matched_text"].startswith(
            "For heads who are currently employed"
        )
    )
    assert sorted(
        common_unemployment["flow_branch_paths"],
        key=lambda path: tuple(item.encode("utf-8") for item in path),
    ) == sorted(
        [working_path, looking_path],
        key=lambda path: tuple(item.encode("utf-8") for item in path),
    )
    assert employed_only["flow_branch_paths"] == [working_path]

    anchors = sealed["local_anchor_classification_rows"]
    assert len(anchors) == 52
    assert all(row["printed_identifier"] is not None for row in anchors)

    def identifiers(page: int, kind: str, text: str) -> set[str]:
        return {
            row["printed_identifier"]
            for row in anchors
            if row["occurrence_kind"] == kind
            and row["exact_label"].find(text) >= 0
            and next(
                occurrence["page_number"]
                for occurrence in occurrences
                if occurrence["questionnaire_occurrence_id"]
                == row["source_occurrence_id"]
            )
            == page
        }

    assert identifiers(
        6, "remuneration_component_anchor", "work in return"
    ) == {"Cl3-14"}
    assert identifiers(8, "job_anchor", "main occupation") == {"D2, El,"}
    assert identifiers(10, "context_anchor", "anyone else") == {"Dl2,Dl3,"}
    assert identifiers(12, "context_anchor", "this extra job") == {"D24, D25"}
    assert identifiers(25, "business_aggregate_anchor", "total income") == {
        "H7"
    }
    assert identifiers(
        26, "remuneration_component_anchor", "professional"
    ) == {"Hlla"}
    assert identifiers(45, "role_anchor", "head") == {"M2."}

    repeat_occurrences = {
        " ".join(row["matched_text"].split()): row
        for row in occurrences
        if row["occurrence_kind"] == "repeat_or_alias_instruction"
    }
    required_repeats = {
        'In this question , as in D2 , we would like complete enough informa- tion to enable us to code occupation: "I\'m a hospital orderly" is good; "I work at the hospital" is not.',
        "These questions are roughly equivalent to Dl0-17 and those instructions apply.",
        "If he does give you separate figures for salary and other business profits, write them both down, with ident ification, and add.",
        "If R has already included some or all of his income from these sources in HS, just note that there is no need to separate it. This question is included only as a check in case this sort of thing has been left out of the H8 figure.",
    }
    assert required_repeats <= set(repeat_occurrences)
    farming_cross_reference = repeat_occurrences[
        "We pick up farming as a secondary source of income in Hllb for non-farmers ."
    ]
    assert farming_cross_reference["flow_branch_paths"] == [
        branch_paths["Not a farmer or rancher"]
    ]

    amount_period = [
        row
        for row in occurrences
        if row["occurrence_kind"] == "field_purpose_prompt"
        and row["matched_text"].startswith(
            "Hlla    (IN ANSWERING QUESTIONS Hlla-llk"
        )
    ]
    assert len(amount_period) == 1
    assert (
        "WEEKLY, MONTHLY, ANNUAL, OR WHAT" in amount_period[0]["matched_text"]
    )

    same_identifier = [
        row
        for row in sealed["local_repeat_alias_evidence_rows"]
        if row["relation"] == "same_printed_identifier_and_exact_label"
    ]
    assert len(same_identifier) == 1
    assert len(same_identifier[0]["alias_anchor_source_occurrence_ids"]) == 1
    assert (
        len(same_identifier[0]["canonical_anchor_source_occurrence_ids"]) == 1
    )


def test_document_003_retained_and_rejected_boundaries(
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

    # Transportation, housing, housework/food, education, health, and generic
    # observation prose can contain employment-like words but remains outside
    # R_Q. The exact empty-page boundary makes those false positives fail.
    assert all(not by_page[page] for page in KNOWN_EMPTY_PAGES)

    counts = Counter(row["occurrence_kind"] for row in rows)
    assert counts["role_total_anchor"] == 2
    assert counts["farm_aggregate_anchor"] == 4
    assert counts["business_aggregate_anchor"] == 2
    aggregates = [
        row
        for row in rows
        if row["occurrence_kind"]
        in {"farm_aggregate_anchor", "business_aggregate_anchor"}
    ]
    assert {row["page_number"] for row in aggregates} == {24, 25, 27}
    aggregate_text = " ".join(row["matched_text"] for row in aggregates)
    for expected in (
        "total receipts from farming",
        "total operating expenses",
        "ne t income",
        "own a business",
        "total income from the business",
        "farming or market gardening",
    ):
        assert expected in aggregate_text

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
        "main occupation",
        "this job",
        "the job you had before",
        "main job",
        "extra jobs",
        "work for money",
    } <= core_parent_texts

    # Stop at the exact boundaries before prospective labor-supply and spouse-
    # commute prose. Pages 14 and 15 are rejected in full above.
    for page_number, boundary in (
        (
            12,
            b"D26-30   This sequence is intended to answer three basic questions",
        ),
        (17, b"Ell-19   See D31-38"),
        (18, b"F6       What kind of job do you have in mind?"),
        (19, b"G6-7    How much time does it take her to get to work"),
    ):
        raw = page_texts[page_number - 1].encode("utf-8")
        boundary_start = raw.index(boundary)
        assert by_page[page_number]
        assert all(
            row["utf8_byte_end"] <= boundary_start
            for row in by_page[page_number]
        )
    assert {
        (row["occurrence_kind"], row["matched_text"]) for row in by_page[16]
    } == {("repeat_or_alias_instruction", "E6   See D6")}

    remuneration = {
        row["matched_text"]
        for row in rows
        if row["occurrence_kind"] == "remuneration_component_anchor"
    }
    normalized_remuneration = {" ".join(text.split()) for text in remuneration}
    assert len(remuneration) == 5
    assert any(
        "work in return for your housing" in text
        for text in normalized_remuneration
    )
    assert any(
        "rent for if it was rented" in text for text in normalized_remuneration
    )
    assert any(
        "How much did you make per hour at this?" in text
        for text in normalized_remuneration
    )
    assert any("bonuses, overtime" in text for text in normalized_remuneration)
    assert any(
        "professional practice or trade" in text
        for text in normalized_remuneration
    )

    page_45_roles = {
        row["matched_text"]
        for row in by_page[45]
        if row["occurrence_kind"] == "role_anchor"
    }
    assert page_45_roles == {"head"}
    assert (
        sum(row["occurrence_kind"] == "role_anchor" for row in by_page[45])
        == 2
    )

    # Known false-positive nonemployment domains do not enter any occurrence.
    all_occurrence_text = " ".join(row["matched_text"].lower() for row in rows)
    for rejected_term in (
        "housework",
        "belong to a labor union",
        "annual cost of the journey to work",
        "dividends, interest, rent, trust funds, or royalties",
        "how much do you hope to earn",
        "how much would a job have to pay",
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


def test_accepted_anchor_candidates_keep_complete_parent_projection(
    sealed: dict,
) -> None:
    """A rejected candidate parent cannot disappear into exact acceptance."""

    candidate_path = ROOT / sealed["candidate_artifact_identity"]["path"]
    candidates = json.loads(candidate_path.read_text(encoding="utf-8"))
    dispositions = {
        row["candidate_id"]: row
        for row in sealed["candidate_disposition_rows"]
    }
    output_anchors = {
        row["local_anchor_classification_id"]: row
        for row in sealed["local_anchor_classification_rows"]
    }
    retained_with_rejected_parent = 0
    for candidate in candidates["candidate_anchor_classification_rows"]:
        disposition = dispositions[
            candidate["candidate_anchor_classification_id"]
        ]
        parent_dispositions = [
            dispositions[parent_candidate_id]
            for parent_candidate_id in candidate["parent_anchor_candidate_ids"]
        ]
        if disposition["stage2_row_ids"] and any(
            row["disposition"] == "rejected" for row in parent_dispositions
        ):
            retained_with_rejected_parent += 1
            assert disposition["disposition"] == "modified"
        if disposition["disposition"] != "accepted":
            continue
        assert len(disposition["stage2_row_ids"]) == 1
        output = output_anchors[disposition["stage2_row_ids"][0]]
        mapped_parent_ids = []
        for parent_candidate_id in candidate["parent_anchor_candidate_ids"]:
            parent_disposition = dispositions[parent_candidate_id]
            assert parent_disposition["disposition"] != "rejected"
            assert parent_disposition["stage2_row_ids"]
            mapped_parent_ids.extend(parent_disposition["stage2_row_ids"])
        assert mapped_parent_ids == output["parent_source_occurrence_ids"]
    assert retained_with_rejected_parent >= 4


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
