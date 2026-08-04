"""Independent checks for the sealed document-6 stage-2 annotation."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SOURCE_PDF = (
    Path("~/PolicyEngine/psid-data").expanduser()
    / "documentation"
    / "capture1"
    / "q70.pdf"
)
ANNOTATION_PATH = (
    ROOT
    / "docs"
    / "analysis"
    / "rq_stage2_annotations"
    / "document_006_q70_annotation_v1.json"
)
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_rq_stage2_document_006_annotation as annotation  # noqa: E402

PAGE_COUNT = 30
INTERVIEW_WAVE = 1970
FILE_SIZE = 1_461_206
FILE_SHA256 = (
    "8365c8580a7a35d0522eb4019b3069dd2cd7f95c9082d102b06037b6995bba20"
)
EXPECTED_EXCEPTIONS = (
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
EXPECTED_FIDELITY_BINDINGS = (
    (
        7,
        225,
        253,
        "occurrence",
        "rq-candidate-occurrence:8852c4c2aa3564fe4583ee7e867e8c839aab858b473434fe367ba73304bef394",
    ),
    (
        7,
        527,
        610,
        "occurrence",
        "rq-candidate-occurrence:da1a46165341a69a7f1ddec3d565af6442f7b91034e6ca6821789cee79d2433f",
    ),
    (
        7,
        626,
        640,
        "flow_path",
        "rq-candidate-flow-path:01aaee7f1508f4021d1330ace2ef5990d545fa3c2286345a0b2485ac9f51964b",
    ),
    (
        7,
        719,
        722,
        "occurrence",
        "rq-candidate-occurrence:ac4d7c0883ce330b10133f02ee05922780db6ef8801ca0dccd4367d1f44194ad",
    ),
    (
        7,
        1101,
        1116,
        "flow_path",
        "rq-candidate-flow-path:7ffd8bc99ff35bdd411e21e8e28414b67dff7d1ba9f4d8aee7fcb74b5ebe67fe",
    ),
    (
        7,
        1525,
        1535,
        "occurrence",
        "rq-candidate-occurrence:883685bca426310041f433d5eaa424abc47c644df04d3d90d96f45053d9c586b",
    ),
    (
        7,
        1544,
        1568,
        "flow_path",
        "rq-candidate-flow-path:0baef04a89981fd6964acf100d2931e3e4bc09750cd246300a18910dcf444a54",
    ),
    (
        7,
        1597,
        1606,
        "flow_path",
        "rq-candidate-flow-path:2f9fc34edb07fbab6e4190ce7939725601086b59c7d34ea2109f121d1dd027c0",
    ),
    (
        7,
        1750,
        1789,
        "occurrence",
        "rq-candidate-occurrence:ba5b5a1501b90611a4d8d4ce1b94c8dac3fea0ef9dd9befa3a4977cd7cc2916a",
    ),
    (
        8,
        148,
        152,
        "occurrence",
        "rq-candidate-occurrence:19ae883323b3eeb833795b38a82a36ab84e3194a0237e14010fab8b5dd197128",
    ),
    (
        8,
        237,
        241,
        "occurrence",
        "rq-candidate-occurrence:8fc2110ef9517f2e4b2ae2324403b3b7634e8aea0cda34ebe6c16e4f00602b27",
    ),
    (
        8,
        508,
        514,
        "occurrence",
        "rq-candidate-occurrence:50555b90e80cbce2c13e3375afe5937ef7678f066518a57430ebac1011a66e86",
    ),
    (
        8,
        583,
        587,
        "occurrence",
        "rq-candidate-occurrence:d54fec0fd376142a4108f497c01f1f9ec9a38442d0c2bcac14ee51cb34b7642d",
    ),
    (
        8,
        792,
        796,
        "occurrence",
        "rq-candidate-occurrence:60e0f903aca59b0b55b56cade462b9f30b9cae249f1def3efd880c112100ffe1",
    ),
    (
        8,
        1012,
        1016,
        "occurrence",
        "rq-candidate-occurrence:9b89366701f29fa1500227d46d9899a261b8db432494e1b1bc34974c17e5ed97",
    ),
    (
        8,
        2073,
        2077,
        "occurrence",
        "rq-candidate-occurrence:4f7d75f453a696a442f9a53d99ecfe8b0afca4f91c26e7098c39f82fc3520f6e",
    ),
    (
        9,
        318,
        334,
        "occurrence",
        "rq-candidate-occurrence:99831b183d0545f7071181ca3c78661debafd7e64ca079a7a1bab85eb450fb84",
    ),
    (
        12,
        108,
        236,
        "occurrence",
        "rq-candidate-occurrence:d95a70206136deea8d5c179674c0fab047965b6b021251d90b5231e83b5b75c1",
    ),
    (
        15,
        180,
        308,
        "occurrence",
        "rq-candidate-occurrence:c851087c2020ddacd2fa3499dd7ffa7f1c336f663bac1378b0e4f1c65bcef62a",
    ),
    (
        16,
        633,
        725,
        "occurrence",
        "rq-candidate-occurrence:1eac1d532e6b8bc02baa196ae64fed2aef6eb7fe3286b74c065f29faeb8d8453",
    ),
    (
        16,
        1098,
        1128,
        "occurrence",
        "rq-candidate-occurrence:cb1d996541e2966c4fdba9e43f24bf13ead88a2e6e4611c699fbe64fe209a070",
    ),
    (
        21,
        233,
        254,
        "occurrence",
        "rq-candidate-occurrence:b59efdb2fa37010c9fe419e2e31313bab0f1c5da846a161c09ebdf1b9a31168c",
    ),
    (
        21,
        498,
        515,
        "occurrence",
        "rq-candidate-occurrence:16925b17c3b1400a7432fd5d2c5e68dc2dd0fe64e6f5264eb71cc37f52a45569",
    ),
    (
        21,
        544,
        566,
        "occurrence",
        "rq-candidate-occurrence:c66b061c3a78d8ee7db58c60e451a5ae76fde45f059ca71f4725a0a212df1cfd",
    ),
    (
        21,
        1420,
        1426,
        "occurrence",
        "rq-candidate-occurrence:7e00a9b075a2c1bb29f5a4c8a3cab4efb871a7d1181f14e2d761cd80e376c3b2",
    ),
    (
        21,
        1446,
        1464,
        "flow_path",
        "rq-candidate-flow-path:b96a7cf9586a415f7a8b1945b9165b6de351e50e9d65bb098abc78453eaef402",
    ),
    (
        21,
        1647,
        1668,
        "occurrence",
        "rq-candidate-occurrence:745b30a2f5fa5b43ebf10211495dbd6d045edc37214122b5016d3ac376b71017",
    ),
    (
        21,
        1699,
        1713,
        "occurrence",
        "rq-candidate-occurrence:851bdd3beb8d34f76b269031caf0a1fc740cad5686ac52daf8450988ce0d9d90",
    ),
    (
        21,
        1821,
        1825,
        "flow_path",
        "rq-candidate-flow-path:7bbe158b6f48780e66237f708526ebe2d9b212ae5566e5a9c126ece9ecbc6314",
    ),
    (
        21,
        1969,
        1979,
        "flow_path",
        "rq-candidate-flow-path:5e86c73d1f51e60f75c585d81c4540f4d708022cf5a68f0a518073b79a4f6c52",
    ),
)
EXPECTED_INDIRECT_FIDELITY_RATIONALES = {
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
    (7, 1544, 1568, "flow_branch_label"): (
        "same D3-D4 printed screen candidate path"
    ),
    (7, 1597, 1606, "flow_branch_label"): (
        "same D3-D4 printed screen candidate path"
    ),
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
    (21, 1821, 1825, "flow_branch_label"): (
        "same H6 response stack candidate path"
    ),
    (21, 1969, 1979, "flow_branch_label"): (
        "same H6 response stack candidate path"
    ),
}


def _coords(page: int, start: int, end: int, *kinds: str) -> set[tuple]:
    return {(page, start, end, kind) for kind in kinds}


EXPECTED_DEPENDENCY_GROUPS = (
    (
        ((7, 0), (7, 1), (7, 2), (7, 3)),
        annotation.EMITTED_PATH_CONSEQUENCE,
        {
            *_coords(15, 180, 308, "flow_branch_label"),
            *_coords(15, 316, 389, "context_anchor", "field_purpose_prompt"),
            *_coords(15, 362, 366, "role_anchor"),
        },
    ),
    (
        ((8, 0),),
        annotation.WITHHELD_PATH_CONSEQUENCE,
        {
            *_coords(8, 2290, 2325, "remuneration_component_anchor"),
            *_coords(8, 2397, 2421, "field_purpose_prompt"),
        },
    ),
    (
        ((8, 0), (8, 1)),
        annotation.WITHHELD_PATH_CONSEQUENCE,
        _coords(
            8,
            2735,
            2847,
            "remuneration_component_anchor",
            "field_purpose_prompt",
        ),
    ),
    (
        ((9, 0),),
        annotation.WITHHELD_PATH_CONSEQUENCE,
        {
            *_coords(9, 395, 416, "context_anchor", "field_purpose_prompt"),
            *_coords(9, 452, 471, "field_purpose_prompt"),
            *_coords(
                9,
                506,
                578,
                "remuneration_component_anchor",
                "field_purpose_prompt",
            ),
            *_coords(9, 614, 680, "context_anchor", "field_purpose_prompt"),
            *_coords(9, 732, 809, "context_anchor", "field_purpose_prompt"),
        },
    ),
    (
        ((7, 0), (7, 1), (7, 2), (7, 3), (15, 0)),
        annotation.WITHHELD_PATH_CONSEQUENCE,
        {
            *_coords(15, 795, 883, "context_anchor", "field_purpose_prompt"),
            *_coords(15, 871, 881, "job_anchor"),
            *_coords(15, 1017, 1064, "context_anchor", "field_purpose_prompt"),
            *_coords(15, 1085, 1144, "context_anchor", "field_purpose_prompt"),
        },
    ),
    (
        ((16, 1), (16, 2), (16, 3), (16, 4)),
        annotation.WITHHELD_PATH_CONSEQUENCE,
        _coords(16, 928, 950, "flow_branch_label"),
    ),
    (
        ((16, 0),),
        annotation.WITHHELD_PATH_CONSEQUENCE,
        {
            *_coords(16, 965, 1002, "repeat_or_alias_instruction"),
            *_coords(16, 984, 988, "role_anchor"),
            *_coords(16, 991, 1001, "job_anchor"),
            *_coords(16, 1009, 1062, "field_purpose_prompt"),
            *_coords(16, 1027, 1031, "role_anchor"),
            *_coords(16, 1098, 1128, "flow_branch_label"),
        },
    ),
    (
        ((16, 0), (16, 5)),
        annotation.WITHHELD_PATH_CONSEQUENCE,
        {
            *_coords(16, 1361, 1390, "context_anchor", "field_purpose_prompt"),
            *_coords(16, 1383, 1386, "role_anchor"),
            *_coords(16, 1423, 1469, "context_anchor", "field_purpose_prompt"),
            *_coords(16, 1500, 1589, "context_anchor", "field_purpose_prompt"),
        },
    ),
)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _atom(row: dict[str, Any]) -> tuple[int, int, int, str]:
    return (
        row["page_number"],
        row["utf8_byte_start"],
        row["utf8_byte_end"],
        row["occurrence_kind"],
    )


@pytest.fixture(scope="module")
def sealed() -> dict[str, Any]:
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


def test_source_and_page_census_exact_cover(
    sealed: dict[str, Any], page_texts: list[str]
) -> None:
    raw = SOURCE_PDF.read_bytes()
    assert len(raw) == FILE_SIZE
    assert _sha256(raw) == FILE_SHA256
    assert len(page_texts) == PAGE_COUNT
    pages = sealed["questionnaire_page_rows"]
    census = sealed["raster_only_incompleteness_census"]["page_census_rows"]
    assert len(pages) == len(census) == PAGE_COUNT
    assert [row["page_number"] for row in pages] == list(range(1, 31))
    assert [row["page_number"] for row in census] == list(range(1, 31))
    for page, row, text in zip(pages, census, page_texts, strict=True):
        assert page["page_text_utf8_sha256"] == _sha256(text.encode())
        assert [row[key] for key in annotation.PAGE_CENSUS_KEYS[:5]] == [
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
    assert [
        (
            r["page_number"],
            r["branch_exception_count"],
            r["dependent_atom_count"],
        )
        for r in census
        if r["branch_exception_count"] or r["dependent_atom_count"]
    ] == [(7, 4, 0), (8, 3, 4), (9, 1, 9), (15, 2, 11), (16, 6, 14)]
    sidecar = sealed["raster_only_incompleteness_census"]
    assert sum(row["branch_exception_count"] for row in census) == 16
    assert sum(row["dependent_atom_count"] for row in census) == 38
    assert [key for row in census for key in row["branch_exception_keys"]] == [
        [record["questionnaire_page_id"], record["exception_index_on_page"]]
        for record in sidecar["branch_exception_records"]
    ]
    assert [key for row in census for key in row["dependent_atom_keys"]] == [
        [
            record["questionnaire_page_id"],
            record["utf8_byte_start"],
            record["utf8_byte_end"],
            record["occurrence_kind"],
        ]
        for record in sidecar["dependent_atom_consequence_records"]
    ]


def test_exception_domain_and_canonical_strings_are_exact(
    sealed: dict[str, Any],
) -> None:
    sidecar = sealed["raster_only_incompleteness_census"]
    assert sidecar["document_completeness_claim"] == (
        "complete-under-extraction-authority with 16 raster-only exceptions"
    )
    assert sidecar["branch_exception_count"] == 16
    assert [
        (
            row["page_number"],
            row["exception_index_on_page"],
            row["visible_label_description"],
            row["approximate_raster_location"],
        )
        for row in sidecar["branch_exception_records"]
    ] == list(EXPECTED_EXCEPTIONS)
    assert all(
        row["disposition"] == annotation.RASTER_REASON
        and row["authority_text_statement"]
        == "no_label_level_span_or_hash_emitted"
        for row in sidecar["branch_exception_records"]
    )


def test_dependent_atoms_have_all_and_only_blockers_and_exact_slices(
    sealed: dict[str, Any], page_texts: list[str]
) -> None:
    sidecar = sealed["raster_only_incompleteness_census"]
    records = sidecar["dependent_atom_consequence_records"]
    assert sidecar["dependent_atom_count"] == len(records) == 38
    assert Counter(row["path_consequence"] for row in records) == {
        annotation.EMITTED_PATH_CONSEQUENCE: 4,
        annotation.WITHHELD_PATH_CONSEQUENCE: 34,
    }
    assert Counter(len(row["blocking_exception_keys"]) for row in records) == {
        1: 17,
        2: 9,
        4: 5,
        5: 7,
    }
    page_ids = {
        row["page_number"]: row["questionnaire_page_id"]
        for row in sealed["questionnaire_page_rows"]
    }
    expected: dict[tuple, tuple[list[list[Any]], str]] = {}
    for blockers, consequence, atoms in EXPECTED_DEPENDENCY_GROUPS:
        keys = [[page_ids[page], index] for page, index in blockers]
        for atom in atoms:
            assert atom not in expected
            expected[atom] = (keys, consequence)
    assert len(expected) == 38
    emitted_by_atom: dict[tuple, list[str]] = defaultdict(list)
    for row in sealed["questionnaire_occurrence_rows"]:
        emitted_by_atom[_atom(row)].append(row["questionnaire_occurrence_id"])
    assert {_atom(row) for row in records} == set(expected)
    for row in records:
        atom = _atom(row)
        blockers, consequence = expected[atom]
        raw = page_texts[row["page_number"] - 1].encode()[
            row["utf8_byte_start"] : row["utf8_byte_end"]
        ]
        assert row["matched_text"] == raw.decode()
        assert row["matched_utf8_sha256"] == _sha256(raw)
        assert row["blocking_exception_keys"] == blockers
        assert row["path_consequence"] == consequence
        assert row[
            "emitted_questionnaire_occurrence_ids"
        ] == emitted_by_atom.get(atom, [])


def test_sparse_positions_are_frozen_before_filtering(
    sealed: dict[str, Any],
) -> None:
    by_atom: dict[tuple, list[dict[str, Any]]] = defaultdict(list)
    by_page: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in sealed["questionnaire_occurrence_rows"]:
        by_atom[_atom(row)].append(row)
        by_page[row["page_number"]].append(row)
    lower_route = by_atom[(7, 1101, 1116, "flow_branch_label")]
    assert [
        (r["semantic_ordinal_at_span"], r["occurrence_index_on_page"])
        for r in lower_route
    ] == [(0, 10)]
    section_f = by_atom[(15, 180, 308, "flow_branch_label")]
    assert [
        (r["semantic_ordinal_at_span"], r["occurrence_index_on_page"])
        for r in section_f
    ] == [(4, 4)]
    assert [r["occurrence_index_on_page"] for r in by_page[15]] == [4, 5, 6, 7]
    assert [r["occurrence_index_on_page"] for r in by_page[16]] == [0]
    page8_indices = {r["occurrence_index_on_page"] for r in by_page[8]}
    assert page8_indices.isdisjoint({131, 133, 135, 136})
    assert {
        (r["utf8_byte_start"], r["occurrence_index_on_page"])
        for r in by_page[8]
        if r["occurrence_index_on_page"] in {132, 134}
    } == {(2345, 132), (2452, 134)}
    assert {r["occurrence_index_on_page"] for r in by_page[9]} == set(
        range(14)
    )


def test_fidelity_diagnostic_is_exactly_the_thirty_atom_domain(
    sealed: dict[str, Any], page_texts: list[str]
) -> None:
    notes = sealed["adjudication_note_rows"]
    diagnostic = {
        (row["candidate_row_kind"], row["candidate_id"]): row
        for row in notes
        if row["note_code"] == annotation.VISUAL_FIDELITY_NOTE_CODE
        or row["note"] == annotation.VISUAL_FIDELITY_NOTE
    }
    assert set(diagnostic) == annotation.VISUAL_FIDELITY_NOTE_KEYS
    assert len(diagnostic) == len(annotation.VISUAL_FIDELITY_COORDINATES) == 30
    assert (
        tuple(
            (
                coordinate[0],
                coordinate[1],
                coordinate[2],
                *annotation.VISUAL_FIDELITY_NOTE_TARGETS[coordinate],
            )
            for coordinate in annotation.VISUAL_FIDELITY_COORDINATES
        )
        == EXPECTED_FIDELITY_BINDINGS
    )
    assert (
        annotation.VISUAL_FIDELITY_INDIRECT_RATIONALES
        == EXPECTED_INDIRECT_FIDELITY_RATIONALES
    )
    assert all(
        row["note_code"] == annotation.VISUAL_FIDELITY_NOTE_CODE
        and row["note"] == annotation.VISUAL_FIDELITY_NOTE
        for row in diagnostic.values()
    )
    source_rows = {
        _atom(row): row for row in sealed["questionnaire_occurrence_rows"]
    }
    source_rows.update(
        {
            _atom(row): row
            for row in sealed["raster_only_incompleteness_census"][
                "dependent_atom_consequence_records"
            ]
        }
    )
    for coordinate in annotation.VISUAL_FIDELITY_COORDINATES:
        row = source_rows[coordinate]
        raw = page_texts[coordinate[0] - 1].encode()[
            coordinate[1] : coordinate[2]
        ]
        assert row["matched_text"] == raw.decode()
        assert row["matched_utf8_sha256"] == _sha256(raw)


def test_legacy_shape_counts_and_flat_forty_key_seal(
    sealed: dict[str, Any],
) -> None:
    assert set(sealed) == set(annotation.LEGACY_AFFECTED_TOP_LEVEL_KEYS)
    assert len(sealed) == 23
    assert len(sealed["seal"]) == 40
    assert set(sealed["seal"]) == set(
        (*annotation.LEGACY_FLAT_SEAL_KEYS, *annotation.RASTER_SEAL_KEYS)
    )
    assert len(sealed["questionnaire_occurrence_rows"]) == 263
    assert len(sealed["flow_branch_rows"]) == 166
    assert len(sealed["local_anchor_classification_rows"]) == 55
    assert sealed["local_repeat_alias_evidence_rows"] == []
    assert len(sealed["output_adjudication_rows"]) == 515
    sidecar = sealed["raster_only_incompleteness_census"]
    expected_raster_seal = annotation._raster_seal_fields(sidecar)
    assert {
        key: sealed["seal"][key] for key in annotation.RASTER_SEAL_KEYS
    } == expected_raster_seal


def test_committed_artifacts_reproduce_and_validator_passes(
    sealed: dict[str, Any],
) -> None:
    inputs = annotation._inputs()
    rebuilt = annotation.build_annotation(*inputs)
    assert annotation._canonical_bytes(sealed) == annotation._canonical_bytes(
        rebuilt
    )
    assert tuple(rebuilt) == annotation.LEGACY_AFFECTED_TOP_LEVEL_KEYS
    assert tuple(rebuilt["raster_only_incompleteness_census"]) == (
        annotation.RASTER_SIDECAR_KEYS
    )
    assert tuple(rebuilt["seal"]) == (
        *annotation.LEGACY_FLAT_SEAL_KEYS,
        *annotation.RASTER_SEAL_KEYS,
    )
    annotation.validate_annotation(sealed, *inputs)


def test_mutation_inventory_covers_ratified_failure_modes(
    sealed: dict[str, Any],
) -> None:
    names = {name for name, _mutate in annotation._mutation_specs(sealed)}
    assert {
        "missing_sidecar_member",
        "extra_sidecar_member",
        "reordered_sidecar_members",
        "missing_branch_exception",
        "missing_dependent_atom",
        "missing_census_page",
        "missing_page_exception_key",
        "missing_page_dependent_key",
        "reordered_blocking_exception_keys",
        "bad_dependent_exact_slice",
        "dense_section_f_semantic_ordinal",
        "dense_section_f_occurrence_index",
        "boolean_section_f_semantic_ordinal",
        "float_section_f_occurrence_index",
        "bad_visual_fidelity_note_code",
        "bad_visual_fidelity_note_text",
        "missing_raster_seal_member",
    } <= names


def test_validator_rejects_fully_resealed_omitted_blocker(
    sealed: dict[str, Any],
) -> None:
    inputs = annotation._inputs()
    mutation = copy.deepcopy(sealed)
    sidecar = mutation["raster_only_incompleteness_census"]
    target = next(
        record
        for record in sidecar["dependent_atom_consequence_records"]
        if len(record["blocking_exception_keys"]) > 1
    )
    target["blocking_exception_keys"].pop()
    mutation["seal"].update(annotation._raster_seal_fields(sidecar))
    mutation["integrity"]["content_sha256"] = annotation._content_sha256(
        mutation
    )
    with pytest.raises(ValueError):
        annotation.validate_annotation(mutation, *inputs)


def test_author_builder_checks_and_mutations_pass() -> None:
    subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "author_rq_stage2_document_006_source_review.py"),
            "--check",
        ],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "build_rq_stage2_document_006_annotation.py"),
            "--check",
            "--mutation-tests",
        ],
        cwd=ROOT,
        check=True,
    )
