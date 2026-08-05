"""Always-runnable checks for compact R_Q era preparation seals."""

from __future__ import annotations

import copy
import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_rq_stage3_era_seal as builder  # noqa: E402

ERA_ID = "wave1968_ry1968_1974_early_totals"
ERA_PATH = builder.era_output_path(ERA_ID)
ERA_2_ID = "ry1975_1977_spouse_concept_seam"
ERA_2_PATH = builder.era_output_path(ERA_2_ID)
ERA_3_ID = "ry1978_1992_pre_er_totals"
ERA_3_PATH = builder.era_output_path(ERA_3_ID)
ERA_4_ID = "ry1993_2001_er_transition"
ERA_4_PATH = builder.era_output_path(ERA_4_ID)
ERA_5_ID = "ry2002_2014_modern_bc_de"
ERA_5_PATH = builder.era_output_path(ERA_5_ID)
ERA_6_ID = "ry2015_2022_exclusion_lineage"
ERA_6_PATH = builder.era_output_path(ERA_6_ID)
EXPECTED_RAW_SHA256 = (
    "bcc3c542bc7e8410e025e4a3aa23ea0bb42da5b579d0c4d346746a9632911a44"
)
EXPECTED_CONTENT_SHA256 = (
    "b07906b0a0f62b2be2a0e3f5d68c5b10bd6f1b1d51d8b13d747603b47980d69a"
)
EXPECTED_INPUT_DOMAIN_SHA256 = (
    "a2036a8115cf35b8ed53c38275b385cf0cd8638f336c04231d083d0fae0ce40c"
)
EXPECTED_INPUT_KEYSET_SHA256 = (
    "4445ff182c45f4fe5bf7624a9cf147b453873e22aac6ba422a9e2ce5cb380634"
)
EXPECTED_ROW_SEAL_DOMAIN_SHA256 = (
    "ef659b290c2e9d5a38d19db7fbe1f16960cc9754a723a38ff23c5f879e4823bc"
)
EXPECTED_ERA_2_RAW_SHA256 = (
    "5a954d5148706378df938231378a81af8f3412024e86c0ee9b1a4aec52f423aa"
)
EXPECTED_ERA_2_CONTENT_SHA256 = (
    "3ac7136e2c8917b6ea0e1321f4a9f2dc6d8305d01f998d2bc4eddb009361413c"
)
EXPECTED_ERA_2_INPUT_KEYSET_SHA256 = (
    "c49b940390be4302579a8780cf76f6e77c5451770f160b8ebb84d13e1738ce9c"
)
EXPECTED_ERA_2_INPUT_DOMAIN_SHA256 = (
    "871a44fa503d4b5ae26f6fdda981d6b2acae758fe37e384b90c48faa8495f27e"
)
EXPECTED_ERA_2_ROW_SEAL_DOMAIN_SHA256 = (
    "f32423b910a57720dcd8ca15664bcb6fe070fa2350d3698e5442585b33756561"
)
EXPECTED_ERA_3_RAW_SHA256 = (
    "59ae2e095e079b16b91c1cf5138803939f7b65f951e3fff6b4f789d428c1dde2"
)
EXPECTED_ERA_3_CONTENT_SHA256 = (
    "f1a80b78800acb7ce8e53f3db8422a9ccaad88673c924ae03420045201be0ee7"
)
EXPECTED_ERA_3_INPUT_KEYSET_SHA256 = (
    "12e6037fa8b1b781b04373471f32d32cbf3e43f20d609d39b255f95c4f34d066"
)
EXPECTED_ERA_3_INPUT_DOMAIN_SHA256 = (
    "09e6c2e65180e70237a90eac6e67a9e010cf6d79e0a53bb35994cc3b90a5b477"
)
EXPECTED_ERA_3_ROW_SEAL_DOMAIN_SHA256 = (
    "4c692ec6ff0554e639ed5ba61f6ac947a799e2e15fe3f85ba09de8279cee8fb0"
)
EXPECTED_ERA_4_RAW_SHA256 = (
    "a58044964bea7bef6c71b28f5f408f658da17eb18e1563c213d4102c84654e9e"
)
EXPECTED_ERA_4_CONTENT_SHA256 = (
    "a4d07990c2066e1e8362dc5339c5fca21bd5b96534781c5a8fe08e7a1dd4a291"
)
EXPECTED_ERA_4_INPUT_KEYSET_SHA256 = (
    "946ef6461b4c67f62dce1d2a79dc64a35f45ab234ca90bdfb115815a2c7224f1"
)
EXPECTED_ERA_4_INPUT_DOMAIN_SHA256 = (
    "72003c0ef143f954dcf76d5fb7eaf312030d141d0101990d0af7c49ab3fb71fd"
)
EXPECTED_ERA_4_ROW_SEAL_DOMAIN_SHA256 = (
    "58ac802c0a171dd328cd32afab72b12c1b8cdc2a2aeca39be23af05f12c2c422"
)
EXPECTED_ERA_5_RAW_SHA256 = (
    "221c28d010cb92a4566910515a9cbd0b342503452de9b9c8e1c223b6bf06cdc1"
)
EXPECTED_ERA_5_CONTENT_SHA256 = (
    "c180fd79d9b89b5018d883ae0e4835913e994e5c11d2645ae1af63b8721c6a18"
)
EXPECTED_ERA_5_INPUT_KEYSET_SHA256 = (
    "67c89573c269fb4ab3928ffa431dae12c8e3dfdfe834d8b68b7507a9f5c4a154"
)
EXPECTED_ERA_5_INPUT_DOMAIN_SHA256 = (
    "88b806bfeea8eb074a3b2f4194d709f09599a89cf10dfdb07d7ca6e77ab1b420"
)
EXPECTED_ERA_5_ROW_SEAL_DOMAIN_SHA256 = (
    "addf336072ecda37a111ee4cb56d76caaabaeb4f0e0f40eec130df6ecbd42f8f"
)
EXPECTED_ERA_6_RAW_SHA256 = (
    "3238516e70d8283fa7172308432e5bb1b4f710a06c758bdb51618aca627b1bd9"
)
EXPECTED_ERA_6_CONTENT_SHA256 = (
    "cc38de5e0875f054a97b9b0c93d4a215d4b5616758e04fb58b6b55f91686c7e6"
)
EXPECTED_ERA_6_INPUT_KEYSET_SHA256 = (
    "6e87da87c8e42bbe45f22cc5198e86e232dd4ce1b417ae9c967c3b98c669ac85"
)
EXPECTED_ERA_6_INPUT_DOMAIN_SHA256 = (
    "3d3c53e996ccb6670de679e93da3349bea5a5a0790644d1d6bf02c77327fd27b"
)
EXPECTED_ERA_6_ROW_SEAL_DOMAIN_SHA256 = (
    "64172558bd87ea110d46a34e8b43b50312d5463a46b266ce677eed4d1bd042d1"
)


@pytest.fixture(scope="module")
def era_inputs() -> builder.EraInputs:
    return builder.load_era_inputs(ERA_ID)


@pytest.fixture(scope="module")
def rebuilt(era_inputs: builder.EraInputs) -> dict:
    return builder.build_era_seal(ERA_ID, era_inputs)


@pytest.fixture(scope="module")
def era_2_inputs() -> builder.EraInputs:
    return builder.load_era_inputs(ERA_2_ID)


@pytest.fixture(scope="module")
def era_2_rebuilt(era_2_inputs: builder.EraInputs) -> dict:
    return builder.build_era_seal(ERA_2_ID, era_2_inputs)


@pytest.fixture(scope="module")
def era_3_inputs() -> builder.EraInputs:
    return builder.load_era_inputs(ERA_3_ID)


@pytest.fixture(scope="module")
def era_3_rebuilt(era_3_inputs: builder.EraInputs) -> dict:
    return builder.build_era_seal(ERA_3_ID, era_3_inputs)


@pytest.fixture(scope="module")
def era_4_inputs() -> builder.EraInputs:
    return builder.load_era_inputs(ERA_4_ID)


@pytest.fixture(scope="module")
def era_4_rebuilt(era_4_inputs: builder.EraInputs) -> dict:
    return builder.build_era_seal(ERA_4_ID, era_4_inputs)


@pytest.fixture(scope="module")
def era_5_inputs() -> builder.EraInputs:
    return builder.load_era_inputs(ERA_5_ID)


@pytest.fixture(scope="module")
def era_5_rebuilt(era_5_inputs: builder.EraInputs) -> dict:
    return builder.build_era_seal(ERA_5_ID, era_5_inputs)


@pytest.fixture(scope="module")
def era_6_inputs() -> builder.EraInputs:
    return builder.load_era_inputs(ERA_6_ID)


@pytest.fixture(scope="module")
def era_6_rebuilt(era_6_inputs: builder.EraInputs) -> dict:
    return builder.build_era_seal(ERA_6_ID, era_6_inputs)


def _annotation_replay_pages(
    inputs: builder.EraInputs, annotation: builder.AnnotationInput
) -> list[dict]:
    source_document_id = annotation.document["source_document_id"]
    return [
        row
        for row in inputs.replay["questionnaire_page_replay"][
            "questionnaire_page_rows"
        ]
        if row["source_document_id"] == source_document_id
    ]


def _verify_source_mutation(
    inputs: builder.EraInputs,
    annotation: builder.AnnotationInput,
    mutation: dict,
) -> None:
    raw = builder.canonical_json_bytes(mutation)
    builder._verify_annotation(
        annotation.path,
        raw,
        mutation,
        annotation.document,
        mutation["document_source_position"],
        _annotation_replay_pages(inputs, annotation),
        builder.stage1_candidates.source_replay_identity(),
        inputs.index_identity,
    )


def test_strict_json_and_canonicalization_fail_closed() -> None:
    assert builder.canonical_json_bytes({"b": 2, "a": 1}) == (
        b'{"a":1,"b":2}\n'
    )
    assert builder.strict_parse_document(b'{"a":1}\n', "fixture") == {"a": 1}
    with pytest.raises(ValueError):
        builder.canonical_json_bytes({"a": float("nan")})
    for raw in (
        b'{"a":1,"a":2}\n',
        b'{"a":NaN}\n',
        b'{"a":Infinity}\n',
        b'{"a":1e10000}\n',
        b'{"a":0.10000000000000001}\n',
        b'\xef\xbb\xbf{"a":1}\n',
        b"\xff",
    ):
        with pytest.raises(ValueError, match="uniquely parseable JSON"):
            builder.strict_parse_document(raw, "fixture")


@pytest.mark.parametrize("era_id", builder.SEALED_ERA_IDS)
def test_each_committed_era_reproduces_and_validator_passes(
    era_id: str,
) -> None:
    inputs = builder.load_era_inputs(era_id)
    rebuilt_value = builder.build_era_seal(era_id, inputs)
    path = builder.era_output_path(era_id)
    raw = path.read_bytes()
    committed = builder.strict_parse_document(raw, f"committed {era_id}")
    assert isinstance(committed, dict)
    assert raw == builder.canonical_json_bytes(committed)
    assert raw == builder.canonical_json_bytes(rebuilt_value)
    builder.validate_era_seal(committed, inputs)


def test_era_1_pins_counts_keysets_and_row_domains(rebuilt: dict) -> None:
    assert rebuilt["interview_waves"] == list(range(1968, 1976))
    assert rebuilt["document_source_positions"] == list(range(1, 17))
    assert rebuilt["document_annotation_input_count"] == 16
    assert rebuilt["document_annotation_input_keyset_sha256"] == (
        EXPECTED_INPUT_KEYSET_SHA256
    )
    assert rebuilt["document_annotation_input_domain_sha256"] == (
        EXPECTED_INPUT_DOMAIN_SHA256
    )
    assert {
        key: rebuilt[key]
        for key in builder.PINNED_ANNOTATION_INPUT_SEALS[ERA_ID]
    } == builder.PINNED_ANNOTATION_INPUT_SEALS[ERA_ID]
    assert rebuilt["row_domain_seal_count"] == 5
    assert rebuilt["row_domain_seal_domain_sha256"] == (
        EXPECTED_ROW_SEAL_DOMAIN_SHA256
    )
    assert rebuilt["row_domain_seal_rows"] == list(
        builder.PINNED_ROW_DOMAIN_SEALS[ERA_ID]
    )
    seals = {row["row_domain"]: row for row in rebuilt["row_domain_seal_rows"]}
    assert seals["document_source_rows"]["row_count"] == 16
    assert seals["questionnaire_page_rows"]["row_count"] == 842
    assert seals["questionnaire_occurrence_rows"]["row_count"] == 5_621
    assert seals["flow_branch_rows"]["row_count"] == 1_531


def test_era_2_pins_exact_counts_identities_and_row_domains(
    era_2_rebuilt: dict,
) -> None:
    assert era_2_rebuilt["interview_waves"] == [1976, 1977, 1978]
    assert era_2_rebuilt["document_source_positions"] == list(range(17, 23))
    assert era_2_rebuilt["document_annotation_input_count"] == 6
    assert era_2_rebuilt["document_annotation_input_keyset_sha256"] == (
        EXPECTED_ERA_2_INPUT_KEYSET_SHA256
    )
    assert era_2_rebuilt["document_annotation_input_domain_sha256"] == (
        EXPECTED_ERA_2_INPUT_DOMAIN_SHA256
    )
    assert {
        key: era_2_rebuilt[key]
        for key in builder.PINNED_ANNOTATION_INPUT_SEALS[ERA_2_ID]
    } == builder.PINNED_ANNOTATION_INPUT_SEALS[ERA_2_ID]
    assert era_2_rebuilt["row_domain_seal_count"] == 5
    assert era_2_rebuilt["row_domain_seal_domain_sha256"] == (
        EXPECTED_ERA_2_ROW_SEAL_DOMAIN_SHA256
    )
    assert era_2_rebuilt["row_domain_seal_rows"] == list(
        builder.PINNED_ROW_DOMAIN_SEALS[ERA_2_ID]
    )
    seals = {
        row["row_domain"]: row for row in era_2_rebuilt["row_domain_seal_rows"]
    }
    assert seals["document_source_rows"]["row_count"] == 6
    assert seals["questionnaire_page_rows"]["row_count"] == 408
    assert seals["questionnaire_occurrence_rows"]["row_count"] == 2_388
    assert seals["flow_branch_rows"]["row_count"] == 690

    raw = ERA_2_PATH.read_bytes()
    assert len(raw) == 7_883
    assert len(raw) < builder.MAX_COMMITTED_FILE_BYTES
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_ERA_2_RAW_SHA256
    assert era_2_rebuilt["integrity"]["content_sha256"] == (
        EXPECTED_ERA_2_CONTENT_SHA256
    )
    assert era_2_rebuilt["nonauthority_statement"] == (
        builder.NONAUTHORITY_STATEMENT
    )
    assert builder.FORBIDDEN_EMISSION_KEYS.isdisjoint(era_2_rebuilt)


def test_era_3_pins_exact_counts_identities_and_row_domains(
    era_3_rebuilt: dict,
) -> None:
    assert era_3_rebuilt["interview_waves"] == list(range(1979, 1994))
    assert era_3_rebuilt["document_source_positions"] == list(range(23, 52))
    assert era_3_rebuilt["document_annotation_input_count"] == 29
    assert era_3_rebuilt["document_annotation_input_keyset_sha256"] == (
        EXPECTED_ERA_3_INPUT_KEYSET_SHA256
    )
    assert era_3_rebuilt["document_annotation_input_domain_sha256"] == (
        EXPECTED_ERA_3_INPUT_DOMAIN_SHA256
    )
    assert {
        key: era_3_rebuilt[key]
        for key in builder.PINNED_ANNOTATION_INPUT_SEALS[ERA_3_ID]
    } == builder.PINNED_ANNOTATION_INPUT_SEALS[ERA_3_ID]
    assert era_3_rebuilt["row_domain_seal_count"] == 5
    assert era_3_rebuilt["row_domain_seal_domain_sha256"] == (
        EXPECTED_ERA_3_ROW_SEAL_DOMAIN_SHA256
    )
    assert era_3_rebuilt["row_domain_seal_rows"] == list(
        builder.PINNED_ROW_DOMAIN_SEALS[ERA_3_ID]
    )
    seals = {
        row["row_domain"]: row for row in era_3_rebuilt["row_domain_seal_rows"]
    }
    assert seals["document_source_rows"]["row_count"] == 29
    assert seals["questionnaire_page_rows"]["row_count"] == 3_349
    assert seals["questionnaire_occurrence_rows"]["row_count"] == 43_818
    assert seals["flow_branch_rows"]["row_count"] == 16_063

    raw = ERA_3_PATH.read_bytes()
    assert len(raw) == 23_106
    assert len(raw) < builder.MAX_COMMITTED_FILE_BYTES
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_ERA_3_RAW_SHA256
    assert era_3_rebuilt["integrity"]["content_sha256"] == (
        EXPECTED_ERA_3_CONTENT_SHA256
    )
    assert era_3_rebuilt["nonauthority_statement"] == (
        builder.NONAUTHORITY_STATEMENT
    )
    assert builder.FORBIDDEN_EMISSION_KEYS.isdisjoint(era_3_rebuilt)
    assert b"raster_only_incompleteness_census" not in raw


def test_era_4_pins_exact_counts_identities_and_row_domains(
    era_4_rebuilt: dict,
) -> None:
    assert era_4_rebuilt["interview_waves"] == [
        1994,
        1995,
        1996,
        1997,
        1999,
        2001,
    ]
    assert era_4_rebuilt["document_source_positions"] == list(range(52, 64))
    assert era_4_rebuilt["document_annotation_input_count"] == 12
    assert era_4_rebuilt["document_annotation_input_keyset_sha256"] == (
        EXPECTED_ERA_4_INPUT_KEYSET_SHA256
    )
    assert era_4_rebuilt["document_annotation_input_domain_sha256"] == (
        EXPECTED_ERA_4_INPUT_DOMAIN_SHA256
    )
    assert {
        key: era_4_rebuilt[key]
        for key in builder.PINNED_ANNOTATION_INPUT_SEALS[ERA_4_ID]
    } == builder.PINNED_ANNOTATION_INPUT_SEALS[ERA_4_ID]
    assert era_4_rebuilt["row_domain_seal_count"] == 5
    assert era_4_rebuilt["row_domain_seal_domain_sha256"] == (
        EXPECTED_ERA_4_ROW_SEAL_DOMAIN_SHA256
    )
    assert era_4_rebuilt["row_domain_seal_rows"] == list(
        builder.PINNED_ROW_DOMAIN_SEALS[ERA_4_ID]
    )
    seals = {
        row["row_domain"]: row for row in era_4_rebuilt["row_domain_seal_rows"]
    }
    assert seals["document_source_rows"]["row_count"] == 12
    assert seals["questionnaire_page_rows"]["row_count"] == 1_622
    assert seals["questionnaire_occurrence_rows"]["row_count"] == 41_209
    assert seals["flow_branch_rows"]["row_count"] == 23_335

    raw = ERA_4_PATH.read_bytes()
    assert len(raw) == 11_863
    assert len(raw) < builder.MAX_COMMITTED_FILE_BYTES
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_ERA_4_RAW_SHA256
    assert era_4_rebuilt["integrity"]["content_sha256"] == (
        EXPECTED_ERA_4_CONTENT_SHA256
    )
    assert era_4_rebuilt["nonauthority_statement"] == (
        builder.NONAUTHORITY_STATEMENT
    )
    assert builder.FORBIDDEN_EMISSION_KEYS.isdisjoint(era_4_rebuilt)


def test_era_5_pins_exact_counts_identities_and_row_domains(
    era_5_rebuilt: dict,
) -> None:
    assert era_5_rebuilt["interview_waves"] == [
        2003,
        2005,
        2007,
        2009,
        2011,
        2013,
        2015,
    ]
    assert era_5_rebuilt["document_source_positions"] == list(range(64, 78))
    assert era_5_rebuilt["document_annotation_input_count"] == 14
    assert era_5_rebuilt["document_annotation_input_keyset_sha256"] == (
        EXPECTED_ERA_5_INPUT_KEYSET_SHA256
    )
    assert era_5_rebuilt["document_annotation_input_domain_sha256"] == (
        EXPECTED_ERA_5_INPUT_DOMAIN_SHA256
    )
    assert {
        key: era_5_rebuilt[key]
        for key in builder.PINNED_ANNOTATION_INPUT_SEALS[ERA_5_ID]
    } == builder.PINNED_ANNOTATION_INPUT_SEALS[ERA_5_ID]
    assert era_5_rebuilt["row_domain_seal_count"] == 5
    assert era_5_rebuilt["row_domain_seal_domain_sha256"] == (
        EXPECTED_ERA_5_ROW_SEAL_DOMAIN_SHA256
    )
    assert era_5_rebuilt["row_domain_seal_rows"] == list(
        builder.PINNED_ROW_DOMAIN_SEALS[ERA_5_ID]
    )
    seals = {
        row["row_domain"]: row for row in era_5_rebuilt["row_domain_seal_rows"]
    }
    assert seals["document_source_rows"]["row_count"] == 14
    assert seals["questionnaire_page_rows"]["row_count"] == 2_337
    assert seals["questionnaire_occurrence_rows"]["row_count"] == 18_838
    assert seals["flow_branch_rows"]["row_count"] == 3_435

    raw = ERA_5_PATH.read_bytes()
    assert len(raw) == 13_171
    assert len(raw) < builder.MAX_COMMITTED_FILE_BYTES
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_ERA_5_RAW_SHA256
    assert era_5_rebuilt["integrity"]["content_sha256"] == (
        EXPECTED_ERA_5_CONTENT_SHA256
    )
    assert era_5_rebuilt["nonauthority_statement"] == (
        builder.NONAUTHORITY_STATEMENT
    )
    assert builder.FORBIDDEN_EMISSION_KEYS.isdisjoint(era_5_rebuilt)


def test_era_6_pins_exact_counts_identities_and_row_domains(
    era_6_rebuilt: dict,
) -> None:
    assert era_6_rebuilt["interview_waves"] == [2017, 2019, 2021, 2023]
    assert era_6_rebuilt["document_source_positions"] == list(range(78, 82))
    assert era_6_rebuilt["document_annotation_input_count"] == 4
    assert era_6_rebuilt["document_annotation_input_keyset_sha256"] == (
        EXPECTED_ERA_6_INPUT_KEYSET_SHA256
    )
    assert era_6_rebuilt["document_annotation_input_domain_sha256"] == (
        EXPECTED_ERA_6_INPUT_DOMAIN_SHA256
    )
    assert {
        key: era_6_rebuilt[key]
        for key in builder.PINNED_ANNOTATION_INPUT_SEALS[ERA_6_ID]
    } == builder.PINNED_ANNOTATION_INPUT_SEALS[ERA_6_ID]
    assert era_6_rebuilt["row_domain_seal_count"] == 5
    assert era_6_rebuilt["row_domain_seal_domain_sha256"] == (
        EXPECTED_ERA_6_ROW_SEAL_DOMAIN_SHA256
    )
    assert era_6_rebuilt["row_domain_seal_rows"] == list(
        builder.PINNED_ROW_DOMAIN_SEALS[ERA_6_ID]
    )
    seals = {
        row["row_domain"]: row for row in era_6_rebuilt["row_domain_seal_rows"]
    }
    assert seals["document_source_rows"]["row_count"] == 4
    assert seals["questionnaire_page_rows"]["row_count"] == 1_632
    assert seals["questionnaire_occurrence_rows"]["row_count"] == 11_275
    assert seals["flow_branch_rows"]["row_count"] == 3_768

    raw = ERA_6_PATH.read_bytes()
    assert len(raw) == 6_574
    assert len(raw) < builder.MAX_COMMITTED_FILE_BYTES
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_ERA_6_RAW_SHA256
    assert era_6_rebuilt["integrity"]["content_sha256"] == (
        EXPECTED_ERA_6_CONTENT_SHA256
    )
    assert era_6_rebuilt["nonauthority_statement"] == (
        builder.NONAUTHORITY_STATEMENT
    )
    assert builder.FORBIDDEN_EMISSION_KEYS.isdisjoint(era_6_rebuilt)


def test_era_1_artifact_is_small_canonical_and_nonauthority(
    rebuilt: dict,
) -> None:
    raw = ERA_PATH.read_bytes()
    assert len(raw) == 14_480
    assert len(raw) < builder.MAX_COMMITTED_FILE_BYTES
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_RAW_SHA256
    assert rebuilt["integrity"]["content_sha256"] == EXPECTED_CONTENT_SHA256
    assert rebuilt["nonauthority_statement"] == (
        builder.NONAUTHORITY_STATEMENT
    )
    assert builder.FORBIDDEN_EMISSION_KEYS.isdisjoint(rebuilt)
    assert b"raster_only_incompleteness_census" not in raw
    assert all(
        prefix.encode() not in raw
        for prefix in builder.FORBIDDEN_GLOBAL_ID_PREFIXES
    )


def test_mixed_stage_2_families_and_raster_sidecars_are_input_only(
    era_inputs: builder.EraInputs, rebuilt: dict
) -> None:
    assert {
        annotation.value["schema_version"]
        for annotation in era_inputs.annotations
    } == {
        builder.LEGACY_SCHEMA,
        builder.MODERN_SCHEMA,
        builder.LOCAL_EDGE_SCHEMA,
    }
    sidecar_positions = {
        annotation.value["document_source_position"]
        for annotation in era_inputs.annotations
        if "raster_only_incompleteness_census" in annotation.value
    }
    assert sidecar_positions == {6, 10, 12}
    assert all(
        set(row) == builder.ANNOTATION_INPUT_KEYS
        for row in rebuilt["document_annotation_input_rows"]
    )
    assert all(
        "raster_only_incompleteness_census" not in row
        for row in rebuilt["document_annotation_input_rows"]
    )
    local = next(
        annotation
        for annotation in era_inputs.annotations
        if annotation.value["document_source_position"] == 12
    )
    assert all(
        "parent_flow_occurrence_ids" in row and "flow_branch_paths" not in row
        for row in local.value["questionnaire_occurrence_rows"]
    )
    assert all(
        "parent_flow_branch_ids" in row and "branch_path" not in row
        for row in local.value["flow_branch_rows"]
    )


def test_source_outer_schema_and_raster_sidecar_fail_closed(
    era_inputs: builder.EraInputs,
) -> None:
    first = era_inputs.annotations[0]
    q5_mutation = copy.deepcopy(first.value)
    q5_mutation["q5_rows"] = []
    q5_mutation["integrity"]["content_sha256"] = (
        builder._annotation_content_sha256(q5_mutation)
    )
    with pytest.raises(ValueError, match="keyset drift"):
        _verify_source_mutation(era_inputs, first, q5_mutation)

    identity_mutation = copy.deepcopy(first.value)
    identity_mutation["source_replay_identity"].pop("byte_size")
    identity_mutation["integrity"]["content_sha256"] = (
        builder._annotation_content_sha256(identity_mutation)
    )
    with pytest.raises(ValueError, match="replay identity drift"):
        _verify_source_mutation(era_inputs, first, identity_mutation)

    sidecar_input = next(
        annotation
        for annotation in era_inputs.annotations
        if annotation.value["document_source_position"] == 6
    )
    for omit_nested_key in (False, True):
        mutation = copy.deepcopy(sidecar_input.value)
        sidecar = mutation["raster_only_incompleteness_census"]
        exceptions = sidecar["branch_exception_records"]
        if omit_nested_key:
            exceptions[0].pop("authority_text_statement")
        else:
            exceptions[0]["visible_label_description"] += " forged"
        seal = mutation["seal"]
        seal["raster_only_branch_exception_keyset_sha256"] = (
            builder._stream_array_digest(
                [
                    [
                        row["questionnaire_page_id"],
                        row["exception_index_on_page"],
                    ]
                    for row in exceptions
                ]
            )
        )
        seal["raster_only_branch_exception_domain_sha256"] = (
            builder._stream_array_digest(exceptions)
        )
        seal["raster_only_incompleteness_census_sha256"] = (
            builder._canonical_digest(sidecar)
        )
        mutation["integrity"]["content_sha256"] = (
            builder._annotation_content_sha256(mutation)
        )
        with pytest.raises(ValueError):
            _verify_source_mutation(era_inputs, sidecar_input, mutation)


def test_legacy_full_coordinate_order_is_independent_of_sparse_indices(
    era_inputs: builder.EraInputs,
) -> None:
    rows = copy.deepcopy(
        era_inputs.annotations[0].value["questionnaire_occurrence_rows"]
    )
    index = next(
        index
        for index, (left, right) in enumerate(
            zip(rows, rows[1:], strict=False)
        )
        if (
            left["page_number"],
            left["utf8_byte_start"],
            left["utf8_byte_end"],
        )
        == (
            right["page_number"],
            right["utf8_byte_start"],
            right["utf8_byte_end"],
        )
    )
    sparse_indices = sorted(
        [
            rows[index]["occurrence_index_on_page"],
            rows[index + 1]["occurrence_index_on_page"],
        ]
    )
    rows[index], rows[index + 1] = rows[index + 1], rows[index]
    rows[index]["occurrence_index_on_page"] = sparse_indices[0]
    rows[index + 1]["occurrence_index_on_page"] = sparse_indices[1]
    with pytest.raises(ValueError, match="source order drift"):
        builder._verify_occurrence_source_order(rows)


def test_era_3_mixed_family_and_fail_closed_scope(
    era_3_inputs: builder.EraInputs,
) -> None:
    by_position = {
        annotation.value["document_source_position"]: annotation
        for annotation in era_3_inputs.annotations
    }
    declared = by_position[34]
    shard = by_position[36]
    assert builder._modern_annotation_family(declared.value) == (
        "declared_scope"
    )
    assert builder._modern_annotation_family(shard.value) == "shard"
    scope = declared.value["document_local_annotation_scope"]
    assert scope["annotated_page_domain"] == [5]
    assert len(declared.value["questionnaire_occurrence_rows"]) == 88
    assert [
        row["annotation_status"]
        for row in declared.value["questionnaire_page_rows"]
    ].count("declared_domain_deferred") == 46

    replay_pages = _annotation_replay_pages(era_3_inputs, declared)
    for mutation_kind in ("omitted_statement", "boolean_page", "widened"):
        mutation = copy.deepcopy(declared.value)
        mutated_scope = mutation["document_local_annotation_scope"]
        if mutation_kind == "omitted_statement":
            mutated_scope["recorded_unresolved_interpretations"][0].pop(
                "statement"
            )
        elif mutation_kind == "boolean_page":
            mutated_scope["annotated_page_domain"] = [True, 5]
        else:
            mutated_scope["annotated_page_domain"] = [1, 5]
        with pytest.raises(ValueError):
            builder._declared_scope_annotated_pages(mutation, replay_pages)


def test_local_parent_order_and_flow_edge_literal_fail_closed(
    era_3_inputs: builder.EraInputs,
) -> None:
    local = next(
        annotation
        for annotation in era_3_inputs.annotations
        if annotation.value["document_source_position"] == 31
    )
    value = local.value
    occurrence_by_id = {
        row["questionnaire_occurrence_id"]: row
        for row in value["questionnaire_occurrence_rows"]
    }
    branch_by_occurrence = {
        row["source_occurrence_id"]: row for row in value["flow_branch_rows"]
    }
    target_id = next(
        occurrence_id
        for occurrence_id, row in occurrence_by_id.items()
        if len(row["parent_flow_occurrence_ids"]) >= 2
    )
    mutation = copy.deepcopy(occurrence_by_id)
    mutation[target_id]["parent_flow_occurrence_ids"].reverse()
    with pytest.raises(ValueError, match="parent source order drift"):
        builder._verify_local_occurrence_parent_order(
            mutation,
            branch_by_occurrence,
            "logical_dag_may_reference_later_extracted_labels",
        )

    literal_mutation = copy.deepcopy(value)
    literal_mutation["seal"][
        "flow_edge_order"
    ] = "direct_parents_precede_children_in_source_order"
    with pytest.raises(ValueError, match="path product"):
        builder._verify_flow(literal_mutation, occurrence_by_id)


def test_mutation_inventory_covers_omitted_keys_and_forbidden_outputs(
    rebuilt: dict,
) -> None:
    names = [
        name for name, _mutate, _reseal in builder._mutation_specs(rebuilt)
    ]
    assert len(names) == len(set(names))
    assert {
        "omitted_input_key_fully_rehashed",
        "omitted_row_domain_seal_key_fully_rehashed",
        "missing_document_input_fully_rehashed",
        "adjacent_era_document_substitution_fully_rehashed",
        "wave_domain_drift_fully_rehashed",
        "document_position_domain_drift_fully_rehashed",
        "row_count_drift_fully_rehashed",
        "row_keyset_drift_fully_rehashed",
        "row_domain_digest_drift_fully_rehashed",
        "forbidden_hierarchy_emission_fully_rehashed",
        "q5_claim_fully_rehashed",
    } <= set(names)


def test_fully_rehashed_omitted_nested_keys_still_fail_source_led_validation(
    era_inputs: builder.EraInputs, rebuilt: dict
) -> None:
    for domain, key in (
        ("document_annotation_input_rows", "raw_sha256"),
        ("row_domain_seal_rows", "row_domain_sha256"),
    ):
        mutation = copy.deepcopy(rebuilt)
        mutation[domain][0].pop(key)
        builder._reseal_mutation(mutation)
        assert mutation["integrity"]["content_sha256"] == (
            builder._content_sha256(mutation)
        )
        with pytest.raises(ValueError):
            builder.validate_era_seal(mutation, era_inputs)


@pytest.mark.parametrize("era_id", builder.SEALED_ERA_IDS)
def test_all_landed_era_mutations_fail_closed(era_id: str) -> None:
    inputs = builder.load_era_inputs(era_id)
    builder.run_mutation_tests(builder.build_era_seal(era_id, inputs), inputs)


@pytest.mark.parametrize("era_id", builder.SEALED_ERA_IDS)
def test_builder_check_and_mutation_command_passes(era_id: str) -> None:
    subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "build_rq_stage3_era_seal.py"),
            "--era",
            era_id,
            "--check",
            "--mutation-tests",
        ],
        cwd=ROOT,
        check=True,
    )
