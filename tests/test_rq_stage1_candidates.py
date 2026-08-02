"""Always-runnable validation for committed R_Q stage-1 candidates."""

from __future__ import annotations

import copy
import hashlib
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
INDEX_PATH = (
    ROOT / "docs" / "analysis" / "rq_stage1_candidates" / "index_v1.json"
)
CANONICAL_Q5_PATH = (
    ROOT
    / "data"
    / "external"
    / "psid_questionnaire_slot_closure_evidence_v1.json"
)
EXPECTED_INDEX_RAW_SHA256 = (
    "a90dfea13cdd74a7d612acdee76c91d6c9e2fd2ed9f9a6befc6a99d9f773a446"
)
EXPECTED_INDEX_CONTENT_SHA256 = (
    "ed80f518b0d2150b9d2c2f4d2e94ca517fc40d1dcd5e29a0c75833d40e86be64"
)
EXPECTED_REPLAY_TOOL_SHA256 = (
    "76a6ae27dda399b5a2576849ae7e2b068b3743c30d4ecc9450746de083f927af"
)
EXPECTED_CANDIDATE_TOOL_SHA256 = (
    "b8b33f2d95eb75b14330848609eb75868ff7d735cafa444a527b1861da9e524d"
)
EXPECTED_GLOBAL_COUNTS = {
    "flow_branch_label": 54_424,
    "role_anchor": 33_992,
    "job_anchor": 22_396,
    "remuneration_component_anchor": 9_280,
    "role_total_anchor": 534,
    "farm_aggregate_anchor": 1_917,
    "business_aggregate_anchor": 6_285,
    "context_anchor": 16_225,
    "field_purpose_prompt": 85_678,
    "repeat_or_alias_instruction": 4_180,
}
EXPECTED_ERA_TOTALS = (
    (
        "wave1968_ry1968_1974_early_totals",
        16,
        842,
        15_594,
        8_993,
        5_512,
    ),
    (
        "ry1975_1977_spouse_concept_seam",
        6,
        408,
        7_581,
        3_356,
        2_740,
    ),
    (
        "ry1978_1992_pre_er_totals",
        29,
        3_349,
        70_698,
        23_928,
        32_906,
    ),
    (
        "ry1993_2001_er_transition",
        12,
        1_622,
        38_939,
        16_613,
        17_422,
    ),
    (
        "ry2002_2014_modern_bc_de",
        14,
        2_337,
        59_164,
        42_427,
        22_035,
    ),
    (
        "ry2015_2022_exclusion_lineage",
        4,
        1_632,
        42_935,
        38_070,
        10_014,
    ),
)

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_rq_stage1_candidates as builder  # noqa: E402


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _index() -> dict:
    value = builder.source_tools.strict_parse_document(
        INDEX_PATH.read_bytes(), "committed R_Q candidate index"
    )
    assert isinstance(value, dict)
    return value


def _reseal(value: dict) -> None:
    value["integrity"]["content_sha256"] = builder._content_sha256(value)


@pytest.fixture(scope="module")
def replay_artifact() -> dict:
    return builder.load_source_replay()


@pytest.fixture(scope="module")
def candidate_index(replay_artifact: dict) -> dict:
    value = _index()
    builder.validate_candidate_index(value, replay_artifact)
    return value


@pytest.fixture(scope="module")
def artifact_audit(replay_artifact: dict, candidate_index: dict) -> dict:
    """Validate all 81 artifacts once while retaining only aggregate state."""

    counts: Counter[str] = Counter()
    page_count = 0
    empty_page_count = 0
    flow_count = 0
    anchor_count = 0
    document_rows: list[tuple[int, str, int, int]] = []
    for identity in candidate_index["document_candidate_manifest_rows"]:
        artifact = builder._read_candidate_artifact(identity, replay_artifact)
        manifest = artifact["candidate_manifest"]
        page_rows = artifact["candidate_page_rows"]
        occurrences = artifact["candidate_occurrence_rows"]
        flow_rows = artifact["candidate_flow_path_rows"]
        anchor_rows = artifact["candidate_anchor_classification_rows"]

        assert manifest == builder._candidate_manifest(
            artifact["document_source_row"],
            page_rows,
            occurrences,
            flow_rows,
            anchor_rows,
        )
        assert artifact["candidate_nonselection_law"] == (
            builder.CANDIDATE_NONSELECTION_LAW
        )
        assert artifact["status"] == builder.STATUS
        assert artifact["artifact_id"].startswith(
            "rq-stage1-document-candidates:"
        )
        assert artifact["whole_document_locator_candidate"][
            "candidate_locator_id"
        ].startswith("rq-candidate-whole-document:")
        assert (
            artifact["whole_document_locator_candidate"]["adjudication_status"]
            == builder.ADJUDICATION_STATUS
        )
        assert [row["page_number"] for row in page_rows] == list(
            range(1, manifest["page_count"] + 1)
        )
        assert all(
            row["candidate_page_id"].startswith("rq-candidate-page:")
            and row["candidate_status"] == builder.ADJUDICATION_STATUS
            for row in page_rows
        )
        assert all(
            row["candidate_occurrence_id"].startswith(
                "rq-candidate-occurrence:"
            )
            and row["adjudication_status"] == builder.ADJUDICATION_STATUS
            and row["occurrence_kind_candidate"] in builder.OCCURRENCE_KINDS
            for row in occurrences
        )
        assert all(
            row["candidate_flow_path_id"].startswith("rq-candidate-flow-path:")
            and row["candidate_branch_id"].startswith(
                "rq-candidate-flow-branch:"
            )
            and row["adjudication_status"] == builder.ADJUDICATION_STATUS
            for row in flow_rows
        )
        assert all(
            row["candidate_anchor_classification_id"].startswith(
                "rq-candidate-anchor-classification:"
            )
            and row["canonical_node_id"] is None
            and row["adjudication_status"] == builder.ADJUDICATION_STATUS
            for row in anchor_rows
        )
        assert not any(
            key in artifact
            for key in (
                "questionnaire_occurrence_rows",
                "flow_branch_rows",
                "global_relationship_rows",
                "hierarchy_rows",
            )
        )

        counts.update(manifest["candidate_occurrence_counts_by_kind"])
        page_count += manifest["page_count"]
        empty_page_count += manifest["empty_candidate_page_count"]
        flow_count += manifest["candidate_flow_path_count"]
        anchor_count += manifest["candidate_anchor_classification_count"]
        document_rows.append(
            (
                identity["document_source_position"],
                identity["source_document_id"],
                manifest["interview_wave"],
                manifest["page_count"],
            )
        )
    return {
        "counts": {kind: counts[kind] for kind in builder.OCCURRENCE_KINDS},
        "page_count": page_count,
        "empty_page_count": empty_page_count,
        "flow_count": flow_count,
        "anchor_count": anchor_count,
        "document_rows": document_rows,
    }


def test_candidate_index_is_canonical_sha_pinned_and_tooling_pinned(
    candidate_index: dict,
):
    raw = INDEX_PATH.read_bytes()
    assert len(raw) == 102_418
    assert raw == builder.source_tools.canonical_json_bytes(candidate_index)
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_INDEX_RAW_SHA256
    assert candidate_index["integrity"]["content_sha256"] == (
        EXPECTED_INDEX_CONTENT_SHA256
    )
    assert _sha256(ROOT / "scripts" / "build_rq_stage1_source_replay.py") == (
        EXPECTED_REPLAY_TOOL_SHA256
    )
    assert _sha256(ROOT / "scripts" / "build_rq_stage1_candidates.py") == (
        EXPECTED_CANDIDATE_TOOL_SHA256
    )


def test_batch_manifests_exact_cover_nine_fixed_batches(
    replay_artifact: dict, candidate_index: dict
):
    expected_positions: list[int] = []
    for index_row in candidate_index["batch_manifest_rows"]:
        batch_index = index_row["batch_index"]
        raw, manifest = builder._read_batch_manifest(
            batch_index, replay_artifact
        )
        assert len(raw) == index_row["byte_size"]
        assert hashlib.sha256(raw).hexdigest() == index_row["raw_sha256"]
        assert manifest["integrity"]["content_sha256"] == (
            index_row["content_sha256"]
        )
        assert manifest["candidate_nonselection_law"] == (
            builder.CANDIDATE_NONSELECTION_LAW
        )
        expected_positions.extend(
            row["document_source_position"]
            for row in manifest["document_artifact_rows"]
        )
    assert expected_positions == list(range(1, 82))


def test_document_manifests_exact_cover_replay_documents_and_pages(
    replay_artifact: dict, artifact_audit: dict
):
    replay_documents = replay_artifact["source_document_replay"][
        "questionnaire_documents"
    ]
    replay_page_counts = {
        row["source_document_id"]: row["page_count"]
        for row in replay_artifact["questionnaire_page_replay"][
            "document_page_rows"
        ]
    }
    assert artifact_audit["document_rows"] == [
        (
            position,
            document["source_document_id"],
            document["interview_waves"][0],
            replay_page_counts[document["source_document_id"]],
        )
        for position, document in enumerate(replay_documents, start=1)
    ]
    assert artifact_audit["page_count"] == 10_190
    assert artifact_audit["empty_page_count"] > 0


def test_all_ten_occurrence_candidate_kinds_recompute_exact_global_census(
    artifact_audit: dict,
):
    assert artifact_audit["counts"] == EXPECTED_GLOBAL_COUNTS
    assert sum(artifact_audit["counts"].values()) == 234_911


def test_flow_and_anchor_candidate_covers_recompute_exactly(
    artifact_audit: dict, candidate_index: dict
):
    assert artifact_audit["flow_count"] == 133_387
    assert artifact_audit["anchor_count"] == 90_629
    assert (
        artifact_audit["flow_count"]
        == candidate_index["candidate_flow_path_count"]
    )
    assert (
        artifact_audit["anchor_count"]
        == candidate_index["candidate_anchor_classification_count"]
    )


def test_global_and_per_era_candidate_census_is_exact(
    candidate_index: dict,
):
    assert candidate_index["candidate_occurrence_counts_by_kind"] == (
        EXPECTED_GLOBAL_COUNTS
    )
    assert [
        (
            row["era_id"],
            row["questionnaire_document_count"],
            row["questionnaire_page_count"],
            row["candidate_occurrence_count"],
            row["candidate_flow_path_count"],
            row["candidate_anchor_classification_count"],
        )
        for row in candidate_index["era_candidate_census_rows"]
    ] == list(EXPECTED_ERA_TOTALS)
    for row in candidate_index["era_candidate_census_rows"]:
        assert row["candidate_occurrence_count"] == sum(
            row["candidate_occurrence_counts_by_kind"].values()
        )


def test_candidate_nonselection_holds_and_q5_remains_absent(
    artifact_audit: dict, candidate_index: dict
):
    assert artifact_audit["page_count"] == 10_190
    assert candidate_index["candidate_nonselection_law"] == (
        builder.CANDIDATE_NONSELECTION_LAW
    )
    assert candidate_index["status"] == builder.INDEX_STATUS
    assert candidate_index["candidate_nonselection_law"] == {
        "authority_kind": "candidate_only_nonauthority",
        "candidate_selected_source_denominator": False,
        "auto_promotion_permitted": False,
        "stage2_rows_emitted": False,
        "adjudication_required_for_every_stage2_row": True,
        "zero_candidate_page_proves_zero_canonical_occurrences": False,
        "final_global_node_ids_assigned": False,
        "status": "pass",
    }
    assert not CANONICAL_Q5_PATH.exists()


def test_validators_reject_resealed_promotion_and_census_mutations(
    replay_artifact: dict, candidate_index: dict
):
    promoted = copy.deepcopy(candidate_index)
    promoted["candidate_nonselection_law"]["auto_promotion_permitted"] = True
    _reseal(promoted)
    with pytest.raises(ValueError, match="global candidate index drift"):
        builder.validate_candidate_index(promoted, replay_artifact)

    false_era = copy.deepcopy(candidate_index)
    false_era["era_candidate_census_rows"][0][
        "candidate_occurrence_count"
    ] += 1
    false_era["era_candidate_census_domain_sha256"] = (
        builder._canonical_digest(false_era["era_candidate_census_rows"])
    )
    _reseal(false_era)
    with pytest.raises(ValueError, match="global candidate index drift"):
        builder.validate_candidate_index(false_era, replay_artifact)

    first_identity = candidate_index["document_candidate_manifest_rows"][0]
    first = builder._read_candidate_artifact(first_identity, replay_artifact)
    first["candidate_nonselection_law"]["auto_promotion_permitted"] = True
    _reseal(first)
    with pytest.raises(ValueError, match="identity or law drift"):
        builder.validate_document_candidates(first, replay_artifact)
