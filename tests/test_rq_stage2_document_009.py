"""Independent validation of the sealed R_Q document-9 annotation.

Every row assertion below is re-derived from ``fam1972_QxQs.pdf`` through the
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
SOURCE_PDF = CAPTURE_ROOT / "fam1972_QxQs.pdf"
ANNOTATION_PATH = (
    ROOT
    / "docs"
    / "analysis"
    / "rq_stage2_annotations"
    / "document_009_fam1972_QxQs_annotation_v1.json"
)
REVIEW_PATH = (
    ROOT
    / "docs"
    / "analysis"
    / "rq_stage2_annotations"
    / "document_009_fam1972_QxQs_source_review_v1.json"
)

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_rq_stage2_document_009_annotation as annotation  # noqa: E402

DOCUMENT_SOURCE_POSITION = 9
INTERVIEW_WAVE = 1972
PAGE_COUNT = 103
FILE_SIZE = 26_299_526
FILE_SHA256 = (
    "a8db4c8732c8386f0d783ee80e8411b61144938946f5d2cdc5bcc4df2176c84f"
)
OCCURRENCE_KINDS = annotation.OCCURRENCE_KINDS
FORBIDDEN_ID_PREFIXES = (
    "psid-job-slot:",
    "psid-component-slot:",
    "psid-node-alias:",
    "psid-questionnaire-relationship:",
)
ANNOTATED_PAGES = {
    15,
    16,
    17,
    18,
    19,
    20,
    21,
    22,
    23,
    26,
    27,
    28,
    29,
    32,
    33,
    34,
    35,
    36,
    37,
    38,
    39,
    40,
    48,
    49,
    50,
    51,
    52,
    53,
    54,
    55,
    56,
    57,
    58,
    59,
    60,
    61,
    63,
    64,
    65,
    89,
    90,
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
    assert locator["filename"] == "fam1972_QxQs.pdf"
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


def test_multi_parent_branch_label_splits_by_parent_path(
    sealed: dict,
) -> None:
    """The printed F7 entry label resolves from F2-yes and from F6-yes."""

    rows = [
        row
        for row in sealed["questionnaire_occurrence_rows"]
        if row["occurrence_kind"] == "flow_branch_label"
        and row["matched_text"] == "(IF YES TO F2 OR TO F6)"
    ]
    assert [row["semantic_ordinal_at_span"] for row in rows] == [0, 1]
    assert {row["page_number"] for row in rows} == {34}
    assert all(len(row["flow_branch_paths"]) == 1 for row in rows)
    parents = [row["flow_branch_paths"][0] for row in rows]
    assert parents[0] != parents[1]
    encoded = [[node.encode("utf-8") for node in path] for path in parents]
    assert encoded == sorted(encoded)
    gated = [
        row
        for row in sealed["questionnaire_occurrence_rows"]
        if len(row["flow_branch_paths"]) > 1
    ]
    assert gated
    branch_by_source = {
        row["source_occurrence_id"]: row for row in sealed["flow_branch_rows"]
    }
    emitted = {
        tuple(
            branch_by_source[row["questionnaire_occurrence_id"]]["branch_path"]
        )
        for row in rows
    }
    for row in gated:
        assert {tuple(path) for path in row["flow_branch_paths"]} == emitted


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
    assert sorted(r["source_occurrence_id"] for r in repeats) == sorted(
        instruction_ids
    )
    for row in repeats:
        assert set(row) == set(annotation.LOCAL_REPEAT_KEYS)
        assert row["relation"] in annotation.ALIAS_RELATIONS
        assert row["source_occurrence_id"] in row["evidence_occurrence_ids"]
        assert row["target_scope"] in {
            "document_local",
            "cross_document",
            "unresolved",
        }
        assert row["resolution_status"] in {
            "document_local_source_evidence_complete",
            "preserved_for_global_resolution",
        }
        for evidence_id in row["evidence_occurrence_ids"]:
            assert occurrences[evidence_id]["occurrence_kind"] in (
                anchor_kinds | {"repeat_or_alias_instruction"}
            )


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
        == "all_103_pages_including_empty_occurrence_pages"
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
        "author_rq_stage2_document_009_source_review.py",
        "build_rq_stage2_document_009_annotation.py",
    ):
        command = [sys.executable, str(SCRIPTS / script), "--check"]
        if script.startswith("build_"):
            command.append("--mutation-tests")
        result = subprocess.run(command, cwd=ROOT, capture_output=True)
        assert result.returncode == 0, result.stderr.decode("utf-8")
