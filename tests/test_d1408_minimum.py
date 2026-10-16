"""Invented checks of the d1408 Track M diagnostic's accounting.

Verification class: labelled diagnostic method checks. No local PSID or
retained result is loaded, and no population conclusion is admitted.
"""

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from tests.track_b_gross_benefit_support import ssa_params


@pytest.fixture(scope="module")
def minimum():
    root = Path(__file__).resolve().parents[1]
    old_path = list(sys.path)
    sys.path.insert(0, str(root / "scripts"))
    try:
        spec = importlib.util.spec_from_file_location(
            "d1408_minimum_test_module", root / "scripts/d1408_minimum.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path[:] = old_path


@given(
    birth=st.integers(1913, 1960),
    age=st.integers(62, 87),
    basis=st.sampled_from(("old_age", "disability", "death")),
)
@settings(deadline=None)
def test_whole_year_months_and_basis_exclusion(minimum, birth, age, basis):
    params = ssa_params()
    record = SimpleNamespace(
        birth_year=birth, window_year=birth + age, basis=basis
    )
    months = minimum.late_months(record, params)
    assert months == age * 12 - params.fra_months(birth)
    records = SimpleNamespace(workers={"invented_worker": record})
    expected = basis == "old_age" and 1917 <= birth <= 1942 and months > 48
    assert bool(minimum.flagged_records(records, params)) == expected
    unsupported = basis == "old_age" and birth < 1917 and months > 0
    assert (
        bool(minimum.flagged_records(records, params, unsupported=True))
        == unsupported
    )


def test_track_m_keeps_delay_after_age_70_for_flagging(minimum):
    record = SimpleNamespace(
        birth_year=1937, window_year=2008, basis="old_age"
    )
    assert minimum.late_months(record, ssa_params()) == 72
    records = SimpleNamespace(workers={"invented_worker": record})
    assert minimum.flagged_records(records, ssa_params()) == {
        "invented_worker"
    }


@given(n=st.integers(0, 30), repeated=st.integers(1, 5))
@settings(deadline=None)
def test_dependents_deduplicate_and_ignore_input_order(minimum, n, repeated):
    people = tuple(
        SimpleNamespace(
            person_id=str(index),
            own_record_id="invented_worker" if index % 2 == 0 else None,
            links=tuple(
                SimpleNamespace(worker_record_id="invented_worker")
                for _ in range(repeated)
            ),
        )
        for index in range(n)
    )
    expected = {str(index) for index in range(n)}
    left = SimpleNamespace(persons=people)
    right = SimpleNamespace(persons=tuple(reversed(people)))
    assert minimum.dependent_people(left, {"invented_worker"}) == expected
    assert minimum.dependent_people(right, {"invented_worker"}) == expected
    assert minimum.dependent_people(left, {"different_worker"}) == set()


@given(n=st.integers(1, 20), worker_n=st.integers(1, 20))
@example(n=10, worker_n=9)
@settings(deadline=None)
def test_weight_accounting_and_worker_cell_suppression(minimum, n, worker_n):
    worker_n = min(worker_n, n)
    workers = {
        str(index): SimpleNamespace(ms5_in_scope=False)
        for index in range(worker_n)
    }
    people = tuple(
        SimpleNamespace(
            person_id=str(index),
            own_record_id=str(index % worker_n),
            links=(),
            weight=1.0,
            paid_own_worker_benefit=True,
        )
        for index in range(n)
    )
    inputs = SimpleNamespace(persons=people, workers=workers)
    group = minimum.usage_groups(inputs, set(workers), n)[
        "all_flagged_evaluations"
    ]
    if n < 10 or worker_n < 10:
        assert set(group.values()) == {"<10"}
    else:
        assert group["people"] == n
        assert group["worker_records"] == worker_n
        assert group["weight"] == n
        assert group["admitted_weight_share"] == 1.0
        assert group["worker_records_associated_beneficiary_weight"] == n
    reversed_inputs = SimpleNamespace(
        persons=tuple(reversed(people)), workers=workers
    )
    assert (
        minimum.usage_groups(reversed_inputs, set(workers), n)[
            "all_flagged_evaluations"
        ]
        == group
    )


@given(owners=st.integers(10, 20), linked=st.integers(1, 9))
@settings(deadline=None)
def test_complementary_suppression_protects_linked_subgroup(
    minimum, owners, linked
):
    workers = {
        str(index): SimpleNamespace(ms5_in_scope=False)
        for index in range(owners)
    }
    people = tuple(
        SimpleNamespace(
            person_id=str(index),
            own_record_id=str(index),
            links=(),
            weight=1.0,
            paid_own_worker_benefit=True,
        )
        for index in range(owners)
    ) + tuple(
        SimpleNamespace(
            person_id=str(owners + index),
            own_record_id=None,
            links=(SimpleNamespace(worker_record_id="0", kind="spouse"),),
            weight=1.0,
            paid_own_worker_benefit=False,
        )
        for index in range(linked)
    )
    groups = minimum.usage_groups(
        SimpleNamespace(persons=people, workers=workers),
        set(workers),
        owners + linked,
    )
    assert groups["all_flagged_evaluations"]["people"] == owners + linked
    assert groups["linked_auxiliary_basis"]["people"] == "<10"
    assert set(groups["admitted_flagged_worker_owners"].values()) == {
        "suppressed_complementary"
    }
    result = {
        "readings": {
            "scored": {"supported": {"all": {"people": owners}}},
            "d430_sensitivity": {
                "supported_flagged_worker_people": owners + linked,
                "supported": {"all": {"people": owners + linked}},
                "rows": {
                    "MS0": {
                        "supported_positive_survivor_payment": {
                            "2": {"people": owners + linked}
                        },
                        "model_headline_changes": 0.0,
                    }
                },
            },
        },
        "method": {},
    }
    left = set(range(owners))
    right = set(range(owners + linked))
    minimum.protect_reading_overlap(result, left, right, left, right)
    assert result["readings"]["scored"]["supported"]["all"]["people"] == owners
    sensitivity = result["readings"]["d430_sensitivity"]
    assert (
        sensitivity["supported_flagged_worker_people"]
        == "suppressed_complementary"
    )
    assert (
        sensitivity["supported"]["all"]["people"] == "suppressed_complementary"
    )
    assert sensitivity["rows"]["MS0"]["model_headline_changes"] == 0.0


def _evaluation(n, moved):
    return SimpleNamespace(
        rows=pd.DataFrame(
            {
                "weight": [1.0] * n,
                "sex": ["male"] * n,
                **{
                    f"receives_{option}": [index < moved for index in range(n)]
                    for option in (2, 3, 4, 5)
                },
            }
        )
    )


@given(moved=st.integers(0, 20))
@settings(deadline=None)
def test_exact_share_path_and_small_change_suppression(minimum, moved):
    legacy = _evaluation(20, 0)
    statutory = _evaluation(20, moved)
    # Empty women cells are outside the test's deliberately single-sex
    # universe. Populate both sexes so every actual diagnostic cell exists.
    for evaluated in (legacy, statutory):
        added = evaluated.rows.copy()
        added["sex"] = "female"
        evaluated.rows = pd.concat([evaluated.rows, added], ignore_index=True)
    reference = {
        "cells": [
            {
                "option": int(key.split("/")[0].split("_")[1]),
                "row": key.split("/")[1],
                **value,
            }
            for key, value in minimum.shares(legacy).items()
        ]
    }
    checks, changes = minimum.share_changes(legacy, statutory, reference)
    assert all(check["exact_match"] for check in checks.values())
    for cell in ("men", "women"):
        change = changes[f"option_2/{cell}"]
        assert change["change_in_admitted_people"] == 0
        assert change["change_in_admitted_weight"] == 0
        if 0 < moved < 10:
            assert change["changed_receiving_people"] == "<10"
            assert change["supported_subset_change_percentage_points"] == "<10"
            assert (
                change["supported_subset_change_in_weight_receiving"] == "<10"
            )
            assert (
                change["supported_subset_change_in_receiving_people"] == "<10"
            )
        else:
            assert change["changed_receiving_people"] == moved
            assert (
                change["supported_subset_change_percentage_points"]
                == moved * 5.0
            )
            assert (
                change["supported_subset_change_in_weight_receiving"] == moved
            )
            assert (
                change["supported_subset_change_in_receiving_people"] == moved
            )


@given(own=st.integers(0, 1000), deceased=st.integers(0, 1000))
@settings(deadline=None)
def test_strict_survivor_flow_matches_original_positive_excess(
    minimum, own, deceased
):
    params = ssa_params()
    people = tuple(
        SimpleNamespace(
            person_id=str(index),
            weight=1.0,
            own_record_id=f"own_{index}",
            own_claim_factor=1.0,
            paid_own_worker_benefit=True,
            links=(
                SimpleNamespace(
                    kind="survivor",
                    worker_record_id=f"dead_{index}",
                    months_early=0,
                    worker_claim_factor=1.26,
                ),
            ),
        )
        for index in range(10)
    )
    outcomes = {
        key: SimpleNamespace(
            outcomes={
                option: SimpleNamespace(option_pia=value)
                for option in (2, 3, 4, 5)
            }
        )
        for index in range(10)
        for key, value in ((f"own_{index}", own), (f"dead_{index}", deceased))
    }
    flows = minimum.positive_survivor_flows(
        SimpleNamespace(persons=people),
        SimpleNamespace(workers=outcomes),
        params,
        {f"dead_{index}" for index in range(10)},
    )
    expected = 10 if deceased * 1.26 > own else 0
    assert all(group["people"] == expected for group in flows.values())
    assert all(group["worker_records"] == expected for group in flows.values())
