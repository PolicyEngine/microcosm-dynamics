"""Independent validation of the sealed R_Q document-24 annotation.

The assertions re-derive authority rows from q79.pdf and independently check
the Amendment-1 raster-only sidecar. The sidecar is diagnostic sealed
nonauthority metadata: its raster-visible labels never become source spans,
authority IDs, flow nodes, or output-adjudication rows.
"""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
CAPTURE_ROOT = (
    Path("~/PolicyEngine/psid-data").expanduser()
    / "documentation"
    / "capture1"
)
SOURCE_PDF = CAPTURE_ROOT / "q79.pdf"
ANNOTATION_PATH = (
    ROOT
    / "docs"
    / "analysis"
    / "rq_stage2_annotations"
    / "document_024_q79_annotation_v1.json"
)

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_rq_stage2_document_024_annotation as annotation  # noqa: E402

DOCUMENT_SOURCE_POSITION = 24
INTERVIEW_WAVE = 1979
PAGE_COUNT = 59
FILE_SIZE = 2_245_142
FILE_SHA256 = (
    "90ed7cf538816125b845c03a82a74204a0a5fad4a75f94663f3c53699e26f2dc"
)
SOURCE_DOCUMENT_ID = (
    "psid-source-document:"
    "259691036d7daf2228e1f58f37835d49927464fcfcfe2b769886528e5d5bac65"
)
EXPECTED_DEPENDENT_ATOM_COUNT = 177
EXPECTED_DEPENDENT_PAGE_COUNTS = {
    12: 34,
    13: 7,
    20: 20,
    27: 13,
    28: 26,
    29: 8,
    30: 21,
    39: 21,
    40: 16,
    42: 11,
}
EXPECTED_BRANCH_PAGE_COUNTS = {8: 1, 12: 5, 22: 2, 39: 2}

EXPECTED_ANNOTATION_KEYS = (
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
EXPECTED_RASTER_SIDECAR_KEYS = (
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
EXPECTED_RASTER_EXCEPTION_KEYS = (
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
EXPECTED_RASTER_DEPENDENT_KEYS = (
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
EXPECTED_RASTER_PAGE_CENSUS_KEYS = (
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
EXPECTED_SEAL_KEYS = (
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
EXPECTED_EXCEPTION_SPECS = (
    (
        8,
        0,
        "C1: TURN TO P. 20, SECTION E",
        "page 8; item C1; right-side direct route from response boxes 4 through 7",
    ),
    (
        12,
        0,
        "C30: 1. SALARIED",
        "page 12; item C30; left response box",
    ),
    (
        12,
        1,
        "C30: 3. PAID BY HOUR",
        "page 12; item C30; center response box",
    ),
    (
        12,
        2,
        "C30: 7. OTHER",
        "page 12; item C30; right response box",
    ),
    (
        12,
        3,
        "C38: 1. YES",
        "page 12; item C38; left response box",
    ),
    (
        12,
        4,
        "C38: 5. NO",
        "page 12; item C38; right response box",
    ),
    (
        22,
        0,
        "F2: TURN TO P. 27, SECTION G",
        "page 22; item F2; direct route below response box 3",
    ),
    (
        22,
        1,
        "F2: TURN TO P. 30, SECTION H",
        "page 22; item F2; right-side direct route from response boxes 4 through 7",
    ),
    (
        39,
        0,
        "K1: 1. HEAD IS FARMER, OR RANCHER",
        "page 39; item K1; upper response row",
    ),
    (
        39,
        1,
        "K1: 5. HEAD IS NOT A FARMER OR RANCHER → GO TO K5",
        "page 39; item K1; lower response row",
    ),
)
FORBIDDEN_ID_PREFIXES = (
    "psid-job-slot:",
    "psid-component-slot:",
    "psid-node-alias:",
    "psid-questionnaire-relationship:",
)


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_digest(value: Any) -> str:
    return _sha256(_canonical_bytes(value))


def _content_sha256(value: Mapping[str, Any]) -> str:
    copied = copy.deepcopy(value)
    copied["integrity"]["content_sha256"] = "0" * 64
    return _canonical_digest(copied)


def _atom(row: Mapping[str, Any]) -> tuple[int, int, int, str]:
    return (
        row["page_number"],
        row["utf8_byte_start"],
        row["utf8_byte_end"],
        row["occurrence_kind"],
    )


def _contains_key_fragment(value: Any, fragment: str) -> bool:
    if isinstance(value, Mapping):
        return any(
            fragment.casefold() in str(key).casefold()
            or _contains_key_fragment(child, fragment)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_key_fragment(child, fragment) for child in value)
    return False


@pytest.fixture(scope="module")
def sealed() -> dict[str, Any]:
    return json.loads(ANNOTATION_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def review() -> dict[str, Any]:
    return json.loads(annotation.REVIEW_PATH.read_text(encoding="utf-8"))


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


@pytest.fixture(scope="module")
def inputs_and_rebuilt() -> tuple[tuple[Any, ...], dict[str, Any]]:
    if not SOURCE_PDF.is_file():
        pytest.skip("PSID questionnaire capture is not staged")
    inputs = annotation._inputs()
    return inputs, annotation.build_annotation(*inputs)


def test_source_bytes_and_page_domain_reproduce(page_texts: list[str]) -> None:
    raw = SOURCE_PDF.read_bytes()
    assert len(raw) == FILE_SIZE
    assert _sha256(raw) == FILE_SHA256
    assert len(page_texts) == PAGE_COUNT


def test_whole_document_locator_obeys_every_equation(sealed: dict) -> None:
    locator = sealed["whole_document_locator"]
    assert set(locator) == set(annotation.LOCATOR_KEYS)
    assert locator["source_document_id"] == SOURCE_DOCUMENT_ID
    assert locator["location_type"] == "whole_document_exact_file_range"
    assert locator["byte_start"] == 0
    assert locator["byte_end"] == locator["size_bytes"] == FILE_SIZE
    assert (
        locator["range_sha256"] == locator["full_file_sha256"] == FILE_SHA256
    )
    assert locator["pdf_page_domain"] == "all_pages_and_flow_branches"
    assert locator["interview_wave"] == INTERVIEW_WAVE
    assert locator["filename"] == "q79.pdf"
    assert locator["locator_id"] == "psid-whole-document:" + _canonical_digest(
        [SOURCE_DOCUMENT_ID, INTERVIEW_WAVE, FILE_SHA256, FILE_SIZE]
    )


def test_page_rows_exact_cover_the_replayed_domain(
    sealed: dict, page_texts: list[str]
) -> None:
    rows = sealed["questionnaire_page_rows"]
    locator_id = sealed["whole_document_locator"]["locator_id"]
    assert len(rows) == PAGE_COUNT
    assert len({row["questionnaire_page_id"] for row in rows}) == PAGE_COUNT
    for page_number, row in enumerate(rows, start=1):
        page_hash = _sha256(page_texts[page_number - 1].encode("utf-8"))
        assert set(row) == set(annotation.PAGE_KEYS)
        assert row["page_number"] == page_number
        assert not isinstance(row["page_number"], bool)
        assert row["source_document_id"] == SOURCE_DOCUMENT_ID
        assert row["source_locator_id"] == locator_id
        assert row["interview_wave"] == INTERVIEW_WAVE
        assert row["page_text_utf8_sha256"] == page_hash
        assert row["annotation_status"] == "complete"
        assert row["questionnaire_page_id"] == (
            "psid-questionnaire-page:"
            + _canonical_digest(
                [SOURCE_DOCUMENT_ID, INTERVIEW_WAVE, page_number, page_hash]
            )
        )


def test_page_occurrence_projections_include_empty_pages(sealed: dict) -> None:
    occurrences_by_page: dict[int, list[str]] = defaultdict(list)
    for occurrence in sealed["questionnaire_occurrence_rows"]:
        occurrences_by_page[occurrence["page_number"]].append(
            occurrence["questionnaire_occurrence_id"]
        )
    for page in sealed["questionnaire_page_rows"]:
        assert (
            page["questionnaire_occurrence_ids"]
            == occurrences_by_page[page["page_number"]]
        )
    empty_count = sum(
        not page["questionnaire_occurrence_ids"]
        for page in sealed["questionnaire_page_rows"]
    )
    assert sealed["seal"]["empty_occurrence_page_count"] == empty_count


def test_every_occurrence_slice_hash_and_id_recomputes(
    sealed: dict, page_texts: list[str]
) -> None:
    locator = sealed["whole_document_locator"]
    for row in sealed["questionnaire_occurrence_rows"]:
        assert set(row) == set(annotation.OCCURRENCE_KEYS)
        assert row["source_document_id"] == SOURCE_DOCUMENT_ID
        assert row["source_locator_id"] == locator["locator_id"]
        assert row["source_locator_sha256"] == _canonical_digest(
            [
                SOURCE_DOCUMENT_ID,
                "documentation/capture1/q79.pdf",
                "questionnaire_page_utf8_span",
                [
                    INTERVIEW_WAVE,
                    row["page_number"],
                    row["utf8_byte_start"],
                    row["utf8_byte_end"],
                    row["occurrence_index_on_page"],
                    row["semantic_ordinal_at_span"],
                    row["occurrence_kind"],
                ],
            ]
        )
        assert row["interview_wave"] == INTERVIEW_WAVE
        assert row["occurrence_kind"] in annotation.OCCURRENCE_KINDS
        start = row["utf8_byte_start"]
        end = row["utf8_byte_end"]
        assert 0 <= start < end
        raw = page_texts[row["page_number"] - 1].encode("utf-8")[start:end]
        assert raw.decode("utf-8", errors="strict") == row["matched_text"]
        assert row["matched_text"]
        assert _sha256(raw) == row["matched_utf8_sha256"]
        assert row["questionnaire_occurrence_id"] == (
            "psid-questionnaire-occurrence:"
            + _canonical_digest(
                [row[key] for key in annotation.OCCURRENCE_KEYS[1:]]
            )
        )


def test_occurrence_source_order_and_atomic_uniqueness(sealed: dict) -> None:
    by_page: dict[int, list[dict[str, Any]]] = defaultdict(list)
    by_atom: dict[tuple[int, int, int, str], list[dict[str, Any]]] = (
        defaultdict(list)
    )
    for row in sealed["questionnaire_occurrence_rows"]:
        by_page[row["page_number"]].append(row)
        by_atom[_atom(row)].append(row)
    for rows in by_page.values():
        source_order = [
            (
                row["utf8_byte_start"],
                row["utf8_byte_end"],
                annotation.KIND_ORDER[row["occurrence_kind"]],
                row["semantic_ordinal_at_span"],
            )
            for row in rows
        ]
        assert source_order == sorted(source_order)
        indices = [row["occurrence_index_on_page"] for row in rows]
        assert indices == sorted(set(indices))
    for atom, rows in by_atom.items():
        ordinals = [row["semantic_ordinal_at_span"] for row in rows]
        if atom[-1] == "flow_branch_label":
            assert ordinals == sorted(set(ordinals))
            assert all(len(row["flow_branch_paths"]) == 1 for row in rows)
        else:
            assert len(rows) == 1
            assert ordinals == [0]


def test_dependent_adjudication_pins_exact_counts_and_all_only_unions(
    review: dict,
) -> None:
    assert annotation.EXPECTED_DEPENDENT_ATOM_COUNT == (
        EXPECTED_DEPENDENT_ATOM_COUNT
    )
    assert annotation.EXPECTED_DEPENDENT_PAGE_COUNTS == (
        EXPECTED_DEPENDENT_PAGE_COUNTS
    )
    specs = annotation.DEPENDENT_ATOM_SPECS
    assert len(specs) == EXPECTED_DEPENDENT_ATOM_COUNT
    assert Counter(spec["atom"][0] for spec in specs) == Counter(
        EXPECTED_DEPENDENT_PAGE_COUNTS
    )
    expected_order = sorted(
        (spec["atom"] for spec in specs),
        key=lambda atom: (
            atom[0],
            atom[1],
            atom[2],
            annotation.KIND_ORDER[atom[3]],
        ),
    )
    assert [spec["atom"] for spec in specs] == expected_order

    review_by_atom = {_atom(row): row for row in review["occurrence_specs"]}
    exception_order = {
        (page, index): ordinal
        for ordinal, (page, index, _description, _location) in enumerate(
            EXPECTED_EXCEPTION_SPECS
        )
    }
    ordinary_branches = {
        (row["page_number"], row["utf8_byte_start"], row["utf8_byte_end"])
        for row in review["occurrence_specs"]
        if row["occurrence_kind"] == "flow_branch_label"
    }
    for spec in specs:
        assert set(spec) == {
            "atom",
            "blocking_exception_keys",
            "blocked_parent_paths",
            "withheld",
        }
        source = review_by_atom[spec["atom"]]
        assert spec["blocked_parent_paths"]
        assert spec["withheld"] == (source["parent_review_branch_paths"] == [])
        derived_union: set[tuple[int, int]] = set()
        comparator_paths: list[tuple[tuple[int, ...], ...]] = []
        for path in spec["blocked_parent_paths"]:
            assert isinstance(path, tuple) and path
            comparator_key: list[tuple[int, ...]] = [(0,)]
            for member in path:
                if member[0] == "exception":
                    key = (member[1], member[2])
                    assert len(member) == 3 and key in exception_order
                    derived_union.add(key)
                    comparator_key.append((1, member[1], 0, member[2]))
                else:
                    assert member[0] == "ordinary" and len(member) == 4
                    assert member[1:] in ordinary_branches
                    comparator_key.append(
                        (1, member[1], 1, member[2], member[3])
                    )
            comparator_paths.append(tuple(comparator_key))
        assert len(comparator_paths) == len(set(comparator_paths))
        assert spec["blocking_exception_keys"] == tuple(
            sorted(derived_union, key=exception_order.__getitem__)
        )


def test_frozen_prefilter_indices_and_semantic_ordinals_use_comparator(
    sealed: dict, review: dict
) -> None:
    dependencies = {
        spec["atom"]: spec for spec in annotation.DEPENDENT_ATOM_SPECS
    }
    occurrences = sealed["questionnaire_occurrence_rows"]
    occurrences_by_atom: dict[
        tuple[int, int, int, str], list[dict[str, Any]]
    ] = defaultdict(list)
    for occurrence in occurrences:
        occurrences_by_atom[_atom(occurrence)].append(occurrence)
    occurrence_by_id = {
        row["questionnaire_occurrence_id"]: row for row in occurrences
    }
    branch_by_id = {
        row["flow_branch_id"]: row for row in sealed["flow_branch_rows"]
    }

    member_key_by_review_ref: dict[str, tuple[int, ...]] = {}
    for source in review["occurrence_specs"]:
        if source["occurrence_kind"] != "flow_branch_label":
            continue
        paths = source["parent_review_branch_paths"]
        for path in paths:
            review_ref = annotation._review_branch_ref(
                source["review_occurrence_id"], path, len(paths)
            )
            member_key_by_review_ref[review_ref] = (
                1,
                source["page_number"],
                1,
                source["utf8_byte_start"],
                source["utf8_byte_end"],
            )

    def review_path_key(path: Sequence[str]) -> tuple[tuple[int, ...], ...]:
        return ((0,), *(member_key_by_review_ref[item] for item in path))

    def blocked_path_key(
        path: Sequence[Sequence[Any]],
    ) -> tuple[tuple[int, ...], ...]:
        result: list[tuple[int, ...]] = [(0,)]
        for member in path:
            if member[0] == "exception":
                result.append((1, member[1], 0, member[2]))
            else:
                result.append((1, member[1], 1, member[2], member[3]))
        return tuple(result)

    def emitted_path_key(path: Sequence[str]) -> tuple[tuple[int, ...], ...]:
        assert path[0] == annotation.FLOW_ROOT
        result: list[tuple[int, ...]] = [(0,)]
        for branch_id in path[1:]:
            source = occurrence_by_id[
                branch_by_id[branch_id]["source_occurrence_id"]
            ]
            result.append(
                (
                    1,
                    source["page_number"],
                    1,
                    source["utf8_byte_start"],
                    source["utf8_byte_end"],
                )
            )
        return tuple(result)

    next_prefilter_index: dict[int, int] = defaultdict(int)
    sparse_ordinal_atoms: set[tuple[int, int, int, str]] = set()
    for source in review["occurrence_specs"]:
        atom = _atom(source)
        dependency = dependencies.get(atom)
        withheld = dependency is not None and dependency["withheld"]
        resolving_paths = (
            [] if withheld else source["parent_review_branch_paths"]
        )
        base_index = next_prefilter_index[source["page_number"]]
        emitted = occurrences_by_atom.get(atom, [])
        if source["occurrence_kind"] == "flow_branch_label":
            blocked_keys = (
                []
                if dependency is None
                else [
                    blocked_path_key(path)
                    for path in dependency["blocked_parent_paths"]
                ]
            )
            resolving_keys = [
                review_path_key(path) for path in resolving_paths
            ]
            complete_keys = sorted([*blocked_keys, *resolving_keys])
            assert complete_keys
            assert len(complete_keys) == len(set(complete_keys))
            ordinal_by_key = {
                key: ordinal for ordinal, key in enumerate(complete_keys)
            }
            assert len(emitted) == len(resolving_paths)
            actual_ordinals: list[int] = []
            for row in emitted:
                assert len(row["flow_branch_paths"]) == 1
                path_key = emitted_path_key(row["flow_branch_paths"][0])
                assert path_key in resolving_keys
                expected_ordinal = ordinal_by_key[path_key]
                actual_ordinals.append(row["semantic_ordinal_at_span"])
                assert row["semantic_ordinal_at_span"] == expected_ordinal
                assert row["occurrence_index_on_page"] == (
                    base_index + expected_ordinal
                )
            assert actual_ordinals == sorted(actual_ordinals)
            if actual_ordinals != list(range(len(actual_ordinals))):
                sparse_ordinal_atoms.add(atom)
            prefilter_count = len(complete_keys)
        else:
            prefilter_count = 1
            assert len(emitted) == (0 if withheld else 1)
            if emitted:
                row = emitted[0]
                assert row["semantic_ordinal_at_span"] == 0
                assert row["occurrence_index_on_page"] == base_index
                assert {
                    emitted_path_key(path) for path in row["flow_branch_paths"]
                } == {review_path_key(path) for path in resolving_paths}
        next_prefilter_index[source["page_number"]] += prefilter_count

    emitted_indices_by_page: dict[int, list[int]] = defaultdict(list)
    for occurrence in occurrences:
        emitted_indices_by_page[occurrence["page_number"]].append(
            occurrence["occurrence_index_on_page"]
        )
    sparse_index_pages = {
        page
        for page, indices in emitted_indices_by_page.items()
        if indices != list(range(len(indices)))
    }
    assert sparse_index_pages
    assert sparse_ordinal_atoms
    assert sparse_index_pages <= set(EXPECTED_DEPENDENT_PAGE_COUNTS)


def test_flow_branch_rows_obey_ancestry_identity_and_cycle_laws(
    sealed: dict,
) -> None:
    occurrence_rows = sealed["questionnaire_occurrence_rows"]
    occurrences = {
        row["questionnaire_occurrence_id"]: row for row in occurrence_rows
    }
    occurrence_order = {
        row["questionnaire_occurrence_id"]: position
        for position, row in enumerate(occurrence_rows)
    }
    labels = [
        row
        for row in occurrence_rows
        if row["occurrence_kind"] == "flow_branch_label"
    ]
    branches = sealed["flow_branch_rows"]
    assert len(branches) == len(labels)
    branch_by_id: dict[str, dict[str, Any]] = {}
    for row in branches:
        assert set(row) == set(annotation.FLOW_BRANCH_KEYS)
        source = occurrences[row["source_occurrence_id"]]
        assert source["occurrence_kind"] == "flow_branch_label"
        assert (
            row["interview_wave"] == source["interview_wave"] == INTERVIEW_WAVE
        )
        assert row["source_locator_id"] == source["source_locator_id"]
        assert row["page_number"] == source["page_number"]
        assert (
            row["occurrence_index_on_page"]
            == source["occurrence_index_on_page"]
        )
        assert row["branch_label"] == source["matched_text"]
        assert row["branch_label_sha256"] == source["matched_utf8_sha256"]
        assert row["branch_path"] == [
            *source["flow_branch_paths"][0],
            row["flow_branch_id"],
        ]
        assert row["flow_branch_id"] == (
            "questionnaire-flow:"
            + _canonical_digest(
                [
                    row["parent_flow_branch_id"],
                    row["interview_wave"],
                    row["source_occurrence_id"],
                ]
            )
        )
        if row["parent_flow_branch_id"] != annotation.FLOW_ROOT:
            parent = branch_by_id[row["parent_flow_branch_id"]]
            assert (
                occurrence_order[parent["source_occurrence_id"]]
                < (occurrence_order[row["source_occurrence_id"]])
            )
        assert len(row["branch_path"]) == len(set(row["branch_path"]))
        branch_by_id[row["flow_branch_id"]] = row
    assert len(branch_by_id) == len(branches)
    assert len({row["source_occurrence_id"] for row in branches}) == len(
        branches
    )


def test_every_occurrence_path_resolves_and_is_canonical(sealed: dict) -> None:
    lawful_paths = {(annotation.FLOW_ROOT,)} | {
        tuple(row["branch_path"]) for row in sealed["flow_branch_rows"]
    }
    resolved_nodes = {annotation.FLOW_ROOT} | {
        row["flow_branch_id"] for row in sealed["flow_branch_rows"]
    }
    for row in sealed["questionnaire_occurrence_rows"]:
        paths = row["flow_branch_paths"]
        assert paths and all(paths)
        assert len(paths) == len({tuple(path) for path in paths})
        assert paths == sorted(
            paths,
            key=lambda path: tuple(node.encode("utf-8") for node in path),
        )
        for path in paths:
            assert tuple(path) in lawful_paths
            assert set(path) <= resolved_nodes


def test_local_anchor_and_repeat_rows_stay_document_local(
    sealed: dict,
) -> None:
    occurrences = {
        row["questionnaire_occurrence_id"]: row
        for row in sealed["questionnaire_occurrence_rows"]
    }
    anchors = sealed["local_anchor_classification_rows"]
    expected_anchor_ids = {
        row["questionnaire_occurrence_id"]
        for row in occurrences.values()
        if row["occurrence_kind"] in annotation.ANCHOR_KINDS
    }
    assert {row["source_occurrence_id"] for row in anchors} == (
        expected_anchor_ids
    )
    for row in anchors:
        assert set(row) == set(annotation.LOCAL_ANCHOR_KEYS)
        source = occurrences[row["source_occurrence_id"]]
        assert row["occurrence_kind"] == source["occurrence_kind"]
        assert row["exact_label"] == source["matched_text"]
        assert row["exact_label_sha256"] == source["matched_utf8_sha256"]
        assert row["classification_status"] == "provisional_document_local"
        if row["node_domain"] == "role":
            assert row["classification"] in annotation.ROLE_CLASSIFICATIONS

    repeats = sealed["local_repeat_alias_evidence_rows"]
    expected_repeat_ids = {
        row["questionnaire_occurrence_id"]
        for row in occurrences.values()
        if row["occurrence_kind"] == "repeat_or_alias_instruction"
    }
    assert {row["source_occurrence_id"] for row in repeats} == (
        expected_repeat_ids
    )
    for row in repeats:
        assert set(row) == set(annotation.LOCAL_REPEAT_KEYS)
        assert row["relation"] in annotation.ALIAS_RELATIONS
        assert row["source_occurrence_id"] in row["evidence_occurrence_ids"]
        assert row["evidence_occurrence_ids"]


def test_candidate_disposition_relation_exact_covers_domain(
    sealed: dict,
) -> None:
    index = json.loads(annotation.stage1_candidates.INDEX_PATH.read_text())
    manifest = next(
        row
        for row in index["document_candidate_manifest_rows"]
        if row["document_source_position"] == DOCUMENT_SOURCE_POSITION
    )
    expected_by_kind = {
        "whole_document_locator": 1,
        "page": PAGE_COUNT,
        "occurrence": manifest["candidate_occurrence_count"],
        "flow_path": manifest["candidate_flow_path_count"],
        "anchor_classification": manifest[
            "candidate_anchor_classification_count"
        ],
    }
    rows = sealed["candidate_disposition_rows"]
    assert (
        Counter(row["candidate_row_kind"] for row in rows) == expected_by_kind
    )
    assert len(rows) == sum(expected_by_kind.values())
    assert len({row["candidate_id"] for row in rows}) == len(rows)
    output_ids = {
        row["stage2_row_id"] for row in sealed["output_adjudication_rows"]
    }
    for row in rows:
        assert set(row) == set(annotation.CANDIDATE_DISPOSITION_KEYS)
        assert row["adjudication_status"] == "complete"
        if row["disposition"] in {"accepted", "modified"}:
            assert len(row["stage2_row_ids"]) == 1
        elif row["disposition"] == "split":
            assert len(row["stage2_row_ids"]) >= 2
        else:
            assert row["disposition"] == "rejected"
            assert row["stage2_row_ids"] == []
        assert set(row["stage2_row_ids"]) <= output_ids


def test_output_adjudication_exact_cover_excludes_sidecar(
    sealed: dict,
) -> None:
    emitted_by_kind = {
        "whole_document_locator": [
            sealed["whole_document_locator"]["locator_id"]
        ],
        "page": [
            row["questionnaire_page_id"]
            for row in sealed["questionnaire_page_rows"]
        ],
        "occurrence": [
            row["questionnaire_occurrence_id"]
            for row in sealed["questionnaire_occurrence_rows"]
        ],
        "flow_branch": [
            row["flow_branch_id"] for row in sealed["flow_branch_rows"]
        ],
        "local_anchor_classification": [
            row["local_anchor_classification_id"]
            for row in sealed["local_anchor_classification_rows"]
        ],
        "local_repeat_alias_evidence": [
            row["local_repeat_alias_evidence_id"]
            for row in sealed["local_repeat_alias_evidence_rows"]
        ],
    }
    expected = {
        (row_kind, row_id)
        for row_kind, row_ids in emitted_by_kind.items()
        for row_id in row_ids
    }
    rows = sealed["output_adjudication_rows"]
    assert {
        (row["stage2_row_kind"], row["stage2_row_id"]) for row in rows
    } == expected
    assert len({row["stage2_row_id"] for row in rows}) == len(rows)
    candidate_ids = {
        row["candidate_id"] for row in sealed["candidate_disposition_rows"]
    }
    for row in rows:
        assert set(row) == set(annotation.OUTPUT_ADJUDICATION_KEYS)
        assert row["stage2_row_kind"] in annotation.STAGE2_ROW_KINDS
        assert row["adjudication_status"] == "complete"
        assert set(row["source_candidate_ids"]) <= candidate_ids
        if row["adjudication_action"] == "manual_add":
            assert row["source_candidate_ids"] == []
            assert row["whole_page_review_complete"] is True
            assert row["source_span_verified"] is True
        else:
            assert row["source_candidate_ids"]
    assert "raster_only_incompleteness_census" not in {
        row["stage2_row_kind"] for row in rows
    }


def test_two_adjudication_relations_agree_in_both_directions(
    sealed: dict,
) -> None:
    forward = {
        (row["candidate_id"], stage2_id)
        for row in sealed["candidate_disposition_rows"]
        for stage2_id in row["stage2_row_ids"]
    }
    backward = {
        (candidate_id, row["stage2_row_id"])
        for row in sealed["output_adjudication_rows"]
        for candidate_id in row["source_candidate_ids"]
    }
    assert forward == backward


def test_whole_page_source_review_is_complete(review: dict) -> None:
    rows = review["page_review_rows"]
    assert len(rows) == PAGE_COUNT
    assert [row["page_number"] for row in rows] == list(
        range(1, PAGE_COUNT + 1)
    )
    for row in rows:
        assert row["whole_page_review_complete"] is True
        assert row["review_status"] == "complete"
        assert row["review_note"].strip()


def test_legacy_outer_shape_claim_and_nonauthority_are_exact(
    sealed: dict,
) -> None:
    assert len(EXPECTED_ANNOTATION_KEYS) == 23
    assert annotation.ANNOTATION_KEYS == EXPECTED_ANNOTATION_KEYS
    assert set(sealed) == set(EXPECTED_ANNOTATION_KEYS)
    assert sealed["schema_version"] == (
        "rq_stage2_document_annotation_nonauthority.v1"
    )
    assert sealed["authority_kind"] == (
        "document_local_source_annotation_nonauthority"
    )
    assert sealed["document_source_position"] == DOCUMENT_SOURCE_POSITION
    assert sealed["status"] == (
        "sealed_complete_nonauthority_document_annotation"
    )
    assert sealed["nonauthority_statement"] == {
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
    claim = (
        "complete-under-extraction-authority with 10 raster-only exceptions"
    )
    assert (
        sealed["raster_only_incompleteness_census"][
            "document_completeness_claim"
        ]
        == claim
    )
    raw = ANNOTATION_PATH.read_text(encoding="utf-8")
    assert raw.count(claim) == 1
    assert _canonical_bytes(sealed) == ANNOTATION_PATH.read_bytes()
    assert sealed["integrity"] == {
        "canonicalization": (
            "python-json-sort-keys-compact-ascii-no-nan-lf-v1"
        ),
        "content_sha256": _content_sha256(sealed),
    }
    assert not _contains_key_fragment(sealed, "witness")
    for prefix in FORBIDDEN_ID_PREFIXES:
        assert prefix not in raw


def test_raster_exception_records_have_exact_diagnostic_strings(
    sealed: dict,
) -> None:
    sidecar = sealed["raster_only_incompleteness_census"]
    assert set(sidecar) == set(EXPECTED_RASTER_SIDECAR_KEYS)
    assert sidecar["schema_version"] == (
        "rq_stage2_raster_only_incompleteness_census_nonauthority.v1"
    )
    assert sidecar["authority_kind"] == "sealed_nonauthority_sidecar"
    assert sidecar["closed_gap_disposition"] == "CLOSED GAP"
    assert sidecar["closed_gap_reason"] == "raster_visible_text_absent"
    assert sidecar["branch_exception_count"] == 10
    assert sidecar["dependent_atom_count"] == EXPECTED_DEPENDENT_ATOM_COUNT
    assert sidecar["later_assembly_consequence"] == (
        "fail_or_withhold_exhaustive_flow_outputs_without_global_gap_rows_nodes_or_ids"
    )
    assert sidecar["status"] == "complete"

    pages = {
        row["page_number"]: row for row in sealed["questionnaire_page_rows"]
    }
    records = sidecar["branch_exception_records"]
    assert [
        (
            row["page_number"],
            row["exception_index_on_page"],
            row["visible_label_description"],
            row["approximate_raster_location"],
        )
        for row in records
    ] == list(EXPECTED_EXCEPTION_SPECS)
    authority_labels = {
        row["matched_text"] for row in sealed["questionnaire_occurrence_rows"]
    } | {row["branch_label"] for row in sealed["flow_branch_rows"]}
    for row in records:
        page = pages[row["page_number"]]
        assert set(row) == set(EXPECTED_RASTER_EXCEPTION_KEYS)
        assert row["disposition"] == "raster_visible_text_absent"
        assert row["source_document_id"] == SOURCE_DOCUMENT_ID
        assert row["questionnaire_page_id"] == page["questionnaire_page_id"]
        assert row["interview_wave"] == INTERVIEW_WAVE
        assert row["page_text_utf8_sha256"] == page["page_text_utf8_sha256"]
        assert row["authority_text_statement"] == (
            "no_label_level_span_or_hash_emitted"
        )
        assert row["visible_label_description"] not in authority_labels


def test_dependent_records_preserve_exact_slices_unions_and_projection(
    sealed: dict, page_texts: list[str]
) -> None:
    sidecar = sealed["raster_only_incompleteness_census"]
    records = sidecar["dependent_atom_consequence_records"]
    specs = {spec["atom"]: spec for spec in annotation.DEPENDENT_ATOM_SPECS}
    pages = {
        row["page_number"]: row for row in sealed["questionnaire_page_rows"]
    }
    occurrences_by_atom: dict[
        tuple[int, int, int, str], list[dict[str, Any]]
    ] = defaultdict(list)
    for occurrence in sealed["questionnaire_occurrence_rows"]:
        occurrences_by_atom[_atom(occurrence)].append(occurrence)
    assert len(records) == len(specs) == EXPECTED_DEPENDENT_ATOM_COUNT
    assert [_atom(row) for row in records] == list(specs)
    for row in records:
        atom = _atom(row)
        spec = specs[atom]
        page = pages[row["page_number"]]
        assert set(row) == set(EXPECTED_RASTER_DEPENDENT_KEYS)
        assert row["reason"] == "raster_visible_text_absent"
        assert row["source_document_id"] == SOURCE_DOCUMENT_ID
        assert row["questionnaire_page_id"] == page["questionnaire_page_id"]
        assert row["interview_wave"] == INTERVIEW_WAVE
        assert row["page_text_utf8_sha256"] == page["page_text_utf8_sha256"]
        raw = page_texts[row["page_number"] - 1].encode("utf-8")[
            row["utf8_byte_start"] : row["utf8_byte_end"]
        ]
        assert raw.decode("utf-8", errors="strict") == row["matched_text"]
        assert _sha256(raw) == row["matched_utf8_sha256"]
        assert row["blocking_exception_keys"] == [
            [
                pages[page_number]["questionnaire_page_id"],
                exception_index,
            ]
            for page_number, exception_index in spec["blocking_exception_keys"]
        ]
        emitted = sorted(
            occurrences_by_atom.get(atom, []),
            key=lambda occurrence: occurrence["occurrence_index_on_page"],
        )
        emitted_ids = [
            occurrence["questionnaire_occurrence_id"] for occurrence in emitted
        ]
        assert row["emitted_questionnaire_occurrence_ids"] == emitted_ids
        assert spec["withheld"] == (emitted_ids == [])
        assert row["path_consequence"] == (
            "emitted_with_all_resolving_extraction_authority_paths"
            if emitted_ids
            else "withheld_no_resolving_extraction_authority_path"
        )


def test_page_census_exactly_projects_both_sidecar_domains(
    sealed: dict,
) -> None:
    sidecar = sealed["raster_only_incompleteness_census"]
    pages = sealed["questionnaire_page_rows"]
    census = sidecar["page_census_rows"]
    assert len(census) == len(pages) == PAGE_COUNT
    assert [row["page_number"] for row in census] == list(
        range(1, PAGE_COUNT + 1)
    )
    assert {
        row["page_number"]: row["branch_exception_count"]
        for row in census
        if row["branch_exception_count"]
    } == EXPECTED_BRANCH_PAGE_COUNTS
    assert {
        row["page_number"]: row["dependent_atom_count"]
        for row in census
        if row["dependent_atom_count"]
    } == EXPECTED_DEPENDENT_PAGE_COUNTS

    projected_branch_keys: list[list[Any]] = []
    projected_dependent_keys: list[list[Any]] = []
    for page, row in zip(pages, census, strict=True):
        assert set(row) == set(EXPECTED_RASTER_PAGE_CENSUS_KEYS)
        assert [row[key] for key in EXPECTED_RASTER_PAGE_CENSUS_KEYS[:5]] == [
            page["questionnaire_page_id"],
            page["source_document_id"],
            page["interview_wave"],
            page["page_number"],
            page["page_text_utf8_sha256"],
        ]
        assert row["branch_exception_count"] == len(
            row["branch_exception_keys"]
        )
        assert row["dependent_atom_count"] == len(row["dependent_atom_keys"])
        projected_branch_keys.extend(row["branch_exception_keys"])
        projected_dependent_keys.extend(row["dependent_atom_keys"])
    assert projected_branch_keys == [
        [row["questionnaire_page_id"], row["exception_index_on_page"]]
        for row in sidecar["branch_exception_records"]
    ]
    assert projected_dependent_keys == [
        [
            row["questionnaire_page_id"],
            row["utf8_byte_start"],
            row["utf8_byte_end"],
            row["occurrence_kind"],
        ]
        for row in sidecar["dependent_atom_consequence_records"]
    ]


def test_flat_forty_key_seal_recomputes_every_count_and_digest(
    sealed: dict,
) -> None:
    locator = sealed["whole_document_locator"]
    pages = sealed["questionnaire_page_rows"]
    occurrences = sealed["questionnaire_occurrence_rows"]
    branches = sealed["flow_branch_rows"]
    anchors = sealed["local_anchor_classification_rows"]
    repeats = sealed["local_repeat_alias_evidence_rows"]
    dispositions = sealed["candidate_disposition_rows"]
    outputs = sealed["output_adjudication_rows"]
    notes = sealed["adjudication_note_rows"]
    sidecar = sealed["raster_only_incompleteness_census"]
    exceptions = sidecar["branch_exception_records"]
    dependents = sidecar["dependent_atom_consequence_records"]
    census = sidecar["page_census_rows"]

    kind_counts = Counter(row["occurrence_kind"] for row in occurrences)
    candidate_census = {
        row_kind: {
            disposition: sum(
                row["candidate_row_kind"] == row_kind
                and row["disposition"] == disposition
                for row in dispositions
            )
            for disposition in (
                "accepted",
                "modified",
                "split",
                "rejected",
            )
        }
        for row_kind in annotation.CANDIDATE_ROW_KINDS
    }
    output_census = {
        row_kind: {
            action: sum(
                row["stage2_row_kind"] == row_kind
                and row["adjudication_action"] == action
                for row in outputs
            )
            for action in (
                "candidate_accepted",
                "candidate_modified",
                "candidate_split",
                "manual_add",
            )
        }
        for row_kind in annotation.STAGE2_ROW_KINDS
    }
    expected = {
        "whole_document_locator_count": 1,
        "whole_document_locator_domain_sha256": _canonical_digest([locator]),
        "questionnaire_page_count": len(pages),
        "questionnaire_page_keyset_sha256": _canonical_digest(
            [row["questionnaire_page_id"] for row in pages]
        ),
        "questionnaire_page_domain_sha256": _canonical_digest(pages),
        "empty_occurrence_page_count": sum(
            not row["questionnaire_occurrence_ids"] for row in pages
        ),
        "questionnaire_occurrence_count": len(occurrences),
        "questionnaire_occurrence_counts_by_kind": {
            kind: kind_counts[kind] for kind in annotation.OCCURRENCE_KINDS
        },
        "questionnaire_occurrence_keyset_sha256": _canonical_digest(
            [row["questionnaire_occurrence_id"] for row in occurrences]
        ),
        "questionnaire_occurrence_domain_sha256": _canonical_digest(
            occurrences
        ),
        "flow_branch_count": len(branches),
        "flow_branch_domain_sha256": _canonical_digest(branches),
        "local_anchor_classification_count": len(anchors),
        "local_anchor_classification_domain_sha256": _canonical_digest(
            anchors
        ),
        "local_repeat_alias_evidence_count": len(repeats),
        "local_repeat_alias_evidence_domain_sha256": _canonical_digest(
            repeats
        ),
        "candidate_disposition_count": len(dispositions),
        "candidate_disposition_domain_sha256": _canonical_digest(dispositions),
        "candidate_adjudication_census_by_kind": candidate_census,
        "output_adjudication_count": len(outputs),
        "output_adjudication_domain_sha256": _canonical_digest(outputs),
        "output_adjudication_census_by_kind": output_census,
        "adjudication_note_count": len(notes),
        "adjudication_note_domain_sha256": _canonical_digest(notes),
        "page_review_count": len(pages),
        "whole_document_review_complete": True,
        "candidate_domain_exact_cover": True,
        "output_domain_exact_cover": True,
        "global_ids_assigned": False,
        "authority_status": "nonauthority",
        "raster_only_branch_exception_count": len(exceptions),
        "raster_only_branch_exception_keyset_sha256": _canonical_digest(
            [
                [
                    row["questionnaire_page_id"],
                    row["exception_index_on_page"],
                ]
                for row in exceptions
            ]
        ),
        "raster_only_branch_exception_domain_sha256": _canonical_digest(
            exceptions
        ),
        "raster_only_dependent_atom_consequence_count": len(dependents),
        "raster_only_dependent_atom_consequence_keyset_sha256": (
            _canonical_digest(
                [
                    [
                        row["questionnaire_page_id"],
                        row["utf8_byte_start"],
                        row["utf8_byte_end"],
                        row["occurrence_kind"],
                    ]
                    for row in dependents
                ]
            )
        ),
        "raster_only_dependent_atom_consequence_domain_sha256": (
            _canonical_digest(dependents)
        ),
        "raster_only_page_census_count": len(census),
        "raster_only_page_census_keyset_sha256": _canonical_digest(
            [[row["questionnaire_page_id"]] for row in census]
        ),
        "raster_only_page_census_domain_sha256": _canonical_digest(census),
        "raster_only_incompleteness_census_sha256": _canonical_digest(sidecar),
    }
    assert len(EXPECTED_SEAL_KEYS) == 40
    assert annotation.SEAL_KEYS == EXPECTED_SEAL_KEYS
    assert set(sealed["seal"]) == set(EXPECTED_SEAL_KEYS)
    assert sealed["seal"] == expected


def test_rebuilt_rows_carry_every_displayed_member_order(
    inputs_and_rebuilt: tuple[tuple[Any, ...], dict[str, Any]],
) -> None:
    _inputs, rebuilt = inputs_and_rebuilt
    assert tuple(rebuilt) == EXPECTED_ANNOTATION_KEYS
    assert tuple(rebuilt["whole_document_locator"]) == annotation.LOCATOR_KEYS
    for name, keys in (
        ("questionnaire_page_rows", annotation.PAGE_KEYS),
        ("questionnaire_occurrence_rows", annotation.OCCURRENCE_KEYS),
        ("flow_branch_rows", annotation.FLOW_BRANCH_KEYS),
        (
            "local_anchor_classification_rows",
            annotation.LOCAL_ANCHOR_KEYS,
        ),
        (
            "local_repeat_alias_evidence_rows",
            annotation.LOCAL_REPEAT_KEYS,
        ),
        (
            "candidate_disposition_rows",
            annotation.CANDIDATE_DISPOSITION_KEYS,
        ),
        ("adjudication_note_rows", annotation.NOTE_KEYS),
        (
            "output_adjudication_rows",
            annotation.OUTPUT_ADJUDICATION_KEYS,
        ),
    ):
        for row in rebuilt[name]:
            assert tuple(row) == keys
    sidecar = rebuilt["raster_only_incompleteness_census"]
    assert tuple(sidecar) == EXPECTED_RASTER_SIDECAR_KEYS
    assert all(
        tuple(row) == EXPECTED_RASTER_EXCEPTION_KEYS
        for row in sidecar["branch_exception_records"]
    )
    assert all(
        tuple(row) == EXPECTED_RASTER_DEPENDENT_KEYS
        for row in sidecar["dependent_atom_consequence_records"]
    )
    assert all(
        tuple(row) == EXPECTED_RASTER_PAGE_CENSUS_KEYS
        for row in sidecar["page_census_rows"]
    )
    assert tuple(rebuilt["seal"]) == EXPECTED_SEAL_KEYS
    assert (
        EXPECTED_ANNOTATION_KEYS.index("raster_only_incompleteness_census")
        == EXPECTED_ANNOTATION_KEYS.index("adjudication_note_rows") + 1
    )


def test_committed_artifacts_reproduce_and_validator_passes(
    inputs_and_rebuilt: tuple[tuple[Any, ...], dict[str, Any]],
) -> None:
    inputs, rebuilt = inputs_and_rebuilt
    assert _canonical_bytes(rebuilt) == ANNOTATION_PATH.read_bytes()
    annotation.validate_annotation(rebuilt, *inputs)


def test_mutation_inventory_covers_amendment_and_omitted_key(
    sealed: dict,
) -> None:
    mutation_names = [
        name for name, _mutate in annotation._mutation_specs(sealed)
    ]
    assert len(mutation_names) == len(set(mutation_names))
    assert {
        "missing_raster_sidecar",
        "extra_raster_sidecar_member",
        "missing_raster_sidecar_member",
        "reordered_raster_sidecar_members",
        "missing_raster_exception_record",
        "extra_raster_exception_record",
        "reordered_raster_exception_records",
        "missing_raster_dependent_record",
        "extra_raster_dependent_record",
        "reordered_raster_dependent_records",
        "inexact_raster_dependent_slice",
        "reused_other_occurrence_bytes",
        "incomplete_emitted_id_projection",
        "root_as_emitted_row",
        "false_raster_completeness_claim",
        "omitted_blocking_key_fully_rehashed",
        "extra_blocking_key",
        "duplicate_blocking_key",
        "reordered_blocking_keys",
        "missing_raster_page_census_row",
        "extra_page_branch_key",
        "missing_page_branch_key",
        "extra_page_dependent_key",
        "missing_page_dependent_key",
        "stale_raster_keyset_digest",
        "stale_raster_domain_digest",
        "stale_raster_sidecar_digest",
        "missing_raster_seal_member",
        "extra_raster_seal_member",
        "reordered_raster_seal_members",
        "dense_semantic_ordinal",
        "dense_occurrence_index",
    } <= set(mutation_names)


def test_author_and_builder_check_commands_and_mutations_pass() -> None:
    if not SOURCE_PDF.is_file():
        pytest.skip("PSID questionnaire capture is not staged")
    commands = (
        [
            sys.executable,
            str(SCRIPTS / "author_rq_stage2_document_024_source_review.py"),
            "--check",
        ],
        [
            sys.executable,
            str(SCRIPTS / "build_rq_stage2_document_024_annotation.py"),
            "--check",
            "--mutation-tests",
        ],
    )
    for command in commands:
        subprocess.run(command, cwd=ROOT, check=True, capture_output=True)
