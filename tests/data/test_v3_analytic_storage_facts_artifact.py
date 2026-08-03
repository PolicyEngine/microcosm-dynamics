"""Pin the committed §22.4.5 storage-fact artifact.

The artifact is the source-derived measurement that A8-R04 consumes.  These
tests re-run the vector against the committed counts and re-derive every
identity the artifact asserts about itself, so a silent edit of any count,
digest, or arithmetic result fails here without needing the PSID corpus.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from populace_dynamics.data import psid_amendment8_vectors as a8
from populace_dynamics.data.psid_source_compiler import canonical_sha256

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_PATH = REPO_ROOT / "runs/v3_analytic_storage_facts_v1.json"
ARTIFACT_BYTES = 5_264
ARTIFACT_SHA256 = (
    "2cfb95702fbe547f4f0726d352c9879ea4d9767459be743ba9a579c7f476eafb"
)


def _artifact() -> dict[str, object]:
    return json.loads(ARTIFACT_PATH.read_bytes())


def test_artifact_is_byte_stable() -> None:
    raw = ARTIFACT_PATH.read_bytes()
    assert len(raw) == ARTIFACT_BYTES
    assert hashlib.sha256(raw).hexdigest() == ARTIFACT_SHA256
    assert raw.endswith(b"\n")
    payload = json.loads(raw)
    assert raw == (
        json.dumps(payload, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    )


def test_self_declared_facts_digest_recomputes() -> None:
    payload = _artifact()
    declared = payload.pop("facts_sha256")
    assert canonical_sha256(payload) == declared


def test_committed_counts_reproduce_the_ratified_census() -> None:
    payload = _artifact()
    assert payload["denominator_sha256"] == (
        "7e497f20e05cbdad384daece86d4aa08b16587b83cb6290193b6fdc28705b764"
    )
    assert payload["count_array_sha256"] == (
        "421105abb63991c3cc1d14d15c98ff68803f7e50dd992107fd797a01ec346624"
    )
    assert payload["ordered_assignment_sha256"] == (
        "5c9020ad92ced4916dd1152f0ce06cc276878a0ca312cd34f9d25c3c3977e72e"
    )
    assert payload["failure_reason_rows_sha256"] == (
        "66a88e6f1138c738892eeb80af22458d57c11a8033315ceba591534ce6908324"
    )


def test_committed_counts_reproduce_the_a8_r04_fact_table() -> None:
    payload = _artifact()
    decomposition = tuple(
        (
            row["derivation_status"],
            row["field_count"],
            row["numeric_range_entry_count"],
            row["logical_source_range_member_count"],
        )
        for row in payload["status_decomposition_rows"]
    )
    assert decomposition == a8.R04_STATUS_DECOMPOSITION
    facts = a8.StorageFacts(
        status_decomposition=decomposition,
        total_members=payload["complete_member_count"],
        explicit_members=payload["explicit_arm_member_count"],
        analytic_members=payload["analytic_arm_member_count"],
        analytic_renderable_members=payload[
            "analytic_arm_renderable_member_count"
        ],
        analytic_unrenderable_members=payload[
            "analytic_arm_unrenderable_member_count"
        ],
        analytic_renderable_containers=payload[
            "analytic_arm_renderable_container_count"
        ],
        analytic_unrenderable_containers=payload[
            "analytic_arm_unrenderable_container_count"
        ],
        arm_ambiguous_renderable_members=payload[
            "arm_ambiguous_renderable_member_count"
        ],
    )
    result = a8.a8_r04(facts)
    assert result["status"] == "pass"
    assert result["row_floor_bytes"] == 266_728_784_621_000
    assert payload["a8_r04_result"] == result


def test_committed_partition_shape_is_consistent() -> None:
    payload = _artifact()
    assert payload["complete_field_count"] == 19_903
    assert payload["complete_range_entry_count"] == 33_786
    assert payload["range_partition_row_count"] == 33_786
    containers = (
        payload["explicit_arm_container_count"]
        + payload["analytic_arm_renderable_container_count"]
        + payload["analytic_arm_unrenderable_container_count"]
    )
    # Every range entry contributes exactly one renderable and one
    # unrenderable relation value, and each takes exactly one threshold arm.
    assert containers == 2 * payload["range_partition_row_count"]
    assert (
        payload["analytic_arm_renderable_container_count"]
        + payload["analytic_arm_unrenderable_container_count"]
        == a8.R04_ANALYTIC_CONTAINERS
    )
    intervals = (
        payload["analytic_arm_renderable_interval_count"]
        + payload["analytic_arm_unrenderable_interval_count"]
    )
    assert intervals == payload["analytic_arm_interval_count"]
    # The analytic arm is lossless but vastly smaller than its expansion.
    assert intervals < payload["analytic_arm_member_count"]


def test_all_four_committed_vectors_passed() -> None:
    payload = _artifact()
    results = payload["amendment_8_vector_results"]
    assert [row["vector_id"] for row in results] == [
        "A8-R01",
        "A8-R02",
        "A8-R03",
        "A8-R04",
    ]
    assert all(row["status"] == "pass" for row in results)
    assert payload["amendment_8_vector_identity"] == (
        a8.a8_vector_relation_identity()
    )
