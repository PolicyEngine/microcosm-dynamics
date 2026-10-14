"""Invented publication checks; no real-data reader or artifact is used."""

from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from hypothesis import given
from hypothesis import strategies as st

from scripts import d1408_diagnostic as diagnostic
from scripts.d1408_common import aggregate_group
from scripts.d1408_diagnostic import (
    EXPECTED_ARTIFACTS,
    validate_projection_publication,
    validate_publication,
    validate_result_scope,
)

# Independent authority fixture: the six results named in ruling d1408.
AUTHORIZED_ARTIFACTS = (
    "runs/first_estimates_v1.json",
    "runs/replication_urban2010_cola_v1.json",
    "runs/replication_urban2010_fra68_v1.json",
    "runs/replication_urban2006_minimum_benefit_v1.json",
    "runs/replication_r7_sharing_v1.json",
    "runs/replication_cost_ordering_v1.json",
)


@given(st.permutations(AUTHORIZED_ARTIFACTS))
def test_result_scope_accepts_authorized_permutations_without_mutation(order):
    original = [{"artifact": artifact} for artifact in order]
    snapshot = [dict(result) for result in original]
    assert EXPECTED_ARTIFACTS == frozenset(AUTHORIZED_ARTIFACTS)
    validate_result_scope(original)
    validate_result_scope(original)
    validate_result_scope(list(reversed(original)))
    assert original == snapshot


@given(
    order=st.permutations(AUTHORIZED_ARTIFACTS),
    positions=st.sampled_from(
        [
            (left, right)
            for left in range(6)
            for right in range(6)
            if left != right
        ]
    ),
)
def test_result_scope_rejects_duplicate_replacing_required_result(
    order, positions
):
    duplicate, replacement = positions
    artifacts = list(order)
    artifacts[replacement] = artifacts[duplicate]
    with pytest.raises(ValueError):
        validate_result_scope(
            [{"artifact": artifact} for artifact in artifacts]
        )


@given(
    st.lists(st.sampled_from(AUTHORIZED_ARTIFACTS), unique=True, max_size=5)
)
def test_result_scope_rejects_every_incomplete_authorized_subset(artifacts):
    with pytest.raises(ValueError):
        validate_result_scope(
            [{"artifact": artifact} for artifact in artifacts]
        )


@given(
    completed=st.booleans(),
    deleted=st.booleans(),
    method=st.sampled_from((None, "", " ", "Invented private-set audit")),
    absent=st.booleans(),
    reverse=st.booleans(),
)
def test_assembly_requires_completed_projection_privacy_audit(
    completed, deleted, method, absent, reverse
):
    projections = [
        {
            "artifact": artifact,
            "cross_result_publication_audit": {
                "completed": completed,
                "temporary_memberships_deleted": deleted,
                "method": method,
            },
        }
        for artifact in AUTHORIZED_ARTIFACTS[1:3]
    ]
    if absent:
        projections[0].pop("cross_result_publication_audit")
    if reverse:
        projections.reverse()
    ready = completed and deleted and bool(method and method.strip())
    if ready and not absent:
        validate_projection_publication(projections)
        validate_projection_publication(projections)
    else:
        with pytest.raises(ValueError):
            validate_projection_publication(projections)
    with pytest.raises(ValueError):
        validate_projection_publication(projections[:1])

    by_artifact = {result["artifact"]: result for result in projections}
    parts = {
        "first-estimates-aggregate.json": {
            "artifact": AUTHORIZED_ARTIFACTS[0]
        },
        "minimum-aggregate.json": {"artifact": AUTHORIZED_ARTIFACTS[3]},
        "sharing-aggregate.json": {
            "results": [
                {"artifact": artifact} for artifact in AUTHORIZED_ARTIFACTS[4:]
            ]
        },
        "cola-aggregate.json": by_artifact[AUTHORIZED_ARTIFACTS[1]],
        "fra68-aggregate.json": by_artifact[AUTHORIZED_ARTIFACTS[2]],
    }

    class InventedAggregateDirectory:
        def __truediv__(self, name):
            return SimpleNamespace(
                is_file=lambda: True,
                read_text=lambda: json.dumps(parts[name]),
            )

    publications = []
    with (
        patch.object(diagnostic, "SCRATCH", InventedAggregateDirectory()),
        patch.object(
            diagnostic,
            "DESTINATION",
            SimpleNamespace(write_text=publications.append),
        ),
    ):
        if ready and not absent:
            document = diagnostic.assemble()
            assert len(document["results"]) == 6
            assert len(publications) == 1
            commands = []

            def capture_command(argv, **_kwargs):
                commands.append(argv)

            with (
                patch.object(
                    diagnostic,
                    "PSID_ROOT",
                    SimpleNamespace(is_dir=lambda: True),
                ),
                patch.object(diagnostic.subprocess, "run", capture_command),
                patch.object(sys, "argv", ["d1408_diagnostic.py"]),
            ):
                diagnostic.main()
            assert commands[-1][-1] == "publication"
            assert commands[-1][-2].endswith("scripts/d1408_projection.py")
            assert len(publications) == 2
        else:
            with pytest.raises(ValueError):
                diagnostic.assemble()
            assert publications == []


@given(
    count=st.integers(1, 9),
    field=st.sampled_from(
        (
            "people",
            "affected_people",
            "changed_receiving_people",
            "supported_flagged_worker_people",
        )
    ),
)
def test_publication_rejects_unsuppressed_small_people(count, field):
    with pytest.raises(ValueError):
        validate_publication({"counts": {field: count}})


@given(
    value=st.floats(0, 1000, allow_nan=False, allow_infinity=False),
    field=st.sampled_from(
        (
            "weight",
            "admitted_weight_share",
            "supported_subset_change_percentage_points",
        )
    ),
)
def test_publication_rejects_partial_small_cell_suppression(value, field):
    with pytest.raises(ValueError):
        validate_publication({"people": "<10", field: value})


@given(st.one_of(st.just(0), st.integers(10, 100000)))
def test_publication_accepts_scalar_aggregate_record_count(count):
    validate_publication({"records": count})


@given(st.integers(1, 9))
def test_publication_accepts_complete_small_cell_suppression(count):
    group = aggregate_group(
        range(count),
        range(count),
        {person: 1.0 for person in range(count)},
        10,
    )
    assert all(value == "<10" for value in group.values())
    group["supported_subset_change_percentage_points"] = "<10"
    validate_publication(group)


@given(
    st.sampled_from(
        (
            "person_id",
            "person_ids",
            "worker_record_id",
            "record_id",
            "individual_amount",
            "microdata",
        )
    )
)
def test_publication_rejects_nested_identifier_fields(field):
    with pytest.raises(ValueError):
        validate_publication({"result": {"nested": {field: None}}})


@pytest.mark.parametrize("records", [[1], {"id": 1}, [{"monthly_payment": 1}]])
@given(st.integers(0, 8))
def test_publication_rejects_record_collections(records, depth):
    payload = {"records": records}
    for _ in range(depth):
        payload = {"nested": [payload]}
    with pytest.raises(ValueError):
        validate_publication(payload)


@given(
    count=st.integers(10, 1000),
    weight=st.floats(0, 100000, allow_nan=False, allow_infinity=False),
)
def test_suppressed_changes_keep_public_admitted_denominator(count, weight):
    validate_publication(
        {
            "admitted_people": count,
            "admitted_weight": weight,
            "changed_receiving_people": "<10",
            "supported_subset_change_percentage_points": "<10",
            "supported_subset_change_in_weight_receiving": "<10",
        }
    )
