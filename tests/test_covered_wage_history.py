"""Invented source observations only; no benefit or population calculation."""

import json
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from populace_dynamics.covered_wage_history import (
    CoveredWageHistory,
    CoveredWageObservation,
    SourceAmount,
)
from populace_dynamics.forward_earnings_history import ForwardEarningsHistory
from populace_dynamics.person_identity import PersonIdentity, PersonIdentityMap


def history():
    mapping = PersonIdentityMap.from_identities(
        [PersonIdentity("uint64", 2**64 - 1), PersonIdentity("string", "001")]
    )
    frame = pd.DataFrame(
        {
            "person_id": [0, 1],
            "year": [2014, 2014],
            "earnings": np.array([0.1, 0.0], dtype=np.float64),
            "earnings_domain": [True, False],
        }
    )
    first = ForwardEarningsHistory.start(
        mapping,
        frame,
        realization_id="invented-career-1",
        generator_digest="a" * 64,
        source_contract_digest="b" * 64,
        lineage_digest="c" * 64,
        unit="XTS",
        price_basis="nominal",
    )
    frame["year"] = 2015
    return first.append(frame, lineage_digest="d" * 64)


def bundle(forward=None):
    return CoveredWageHistory(
        history() if forward is None else forward,
        "e" * 64,
        (
            CoveredWageObservation(
                0, 2014, SourceAmount("decimal", "0.00"), None, "f" * 64
            ),
            CoveredWageObservation(
                1, 2014, None, "coverage_unresolved", "1" * 64
            ),
            CoveredWageObservation(
                0, 2015, None, "source_field_unavailable", "2" * 64
            ),
            CoveredWageObservation(
                1,
                2015,
                SourceAmount("uint64", "9007199254740993"),
                None,
                "3" * 64,
            ),
        ),
    )


def test_known_zero_unknown_and_independent_source_domain_remain_distinct():
    wages = bundle()
    assert [r.amount_state for r in wages.observations] == [
        "known_zero",
        "unavailable",
        "unavailable",
        "known_amount",
    ]
    # Independent covered-wage evidence is permitted for a person outside the
    # forward generator's domain; its control zero is never copied or inferred.
    person = PersonIdentity("uint64", 2**64 - 1)
    assert wages.history.for_person(person)[1].amount_hex is None
    assert (
        wages.for_person(person)[1].amount.serialization == "9007199254740993"
    )
    assert wages.history.coverage_status == "not_materialized"
    assert wages.history.source_registry_status == "registration_required"


@pytest.mark.parametrize(
    "kind,value",
    [
        ("uint64", "9007199254740993"),
        ("decimal", "123456789012345678901234567890.0100"),
        ("binary64", (0.1).hex()),
        ("binary64", (-0.0).hex()),
    ],
)
def test_source_representation_round_trips_without_rounding(kind, value):
    wages = bundle()
    row = replace(wages.observations[0], amount=SourceAmount(kind, value))
    wages = replace(wages, observations=(row,) + wages.observations[1:])
    restored = CoveredWageHistory.from_json(
        wages.to_json(), history=wages.history, expected_digest=wages.digest
    )
    assert restored == wages
    assert restored.observations[0].amount.serialization == value
    assert restored.to_json() == wages.to_json()


def test_decimal_scale_is_source_identity_and_row_order_is_not():
    wages = bundle()
    assert (
        replace(wages, observations=wages.observations[::-1]).digest
        == wages.digest
    )
    row = replace(wages.observations[0], amount=SourceAmount("decimal", "0.0"))
    assert (
        replace(wages, observations=(row,) + wages.observations[1:]).digest
        != wages.digest
    )


@pytest.mark.parametrize(
    "kind,value",
    [
        ("uint64", True),
        ("uint64", 1),
        ("uint64", "01"),
        ("uint64", "-1"),
        ("decimal", "NaN"),
        ("decimal", "Infinity"),
        ("decimal", "1e3"),
        ("decimal", "-0.01"),
        ("decimal", " 1.00"),
        ("decimal", "01.00"),
        ("binary64", "nan"),
        ("binary64", float("inf").hex()),
        ("binary64", (-1.0).hex()),
        ("binary64", "0x1p+0"),
        ("unknown", "0"),
    ],
)
def test_ambiguous_or_negative_source_amount_refuses(kind, value):
    with pytest.raises(ValueError):
        SourceAmount(kind, value)


@pytest.mark.parametrize(
    "change",
    [
        {"amount": None},
        {"missing_reason": "coverage_unresolved"},
        {"source_digest": ""},
        {"year": True},
        {"dynamics_person_key": 0.0},
    ],
)
def test_observation_requires_exact_identity_amount_state_and_provenance(
    change,
):
    with pytest.raises(ValueError):
        replace(bundle().observations[0], **change)


def test_dense_envelope_cannot_shrink_or_expand_silently():
    wages = bundle()
    invalid = [
        wages.observations[:-1],
        wages.observations[:2],
        wages.observations + (wages.observations[0],),
        (replace(wages.observations[0], year=2016),) + wages.observations[1:],
        (replace(wages.observations[0], dynamics_person_key=2),)
        + wages.observations[1:],
    ]
    for rows in invalid:
        with pytest.raises(ValueError):
            replace(wages, observations=rows)


@pytest.mark.parametrize(
    "field,value",
    [
        ("realization_id", "another-draw"),
        ("unit", "USD"),
        ("generator_digest", "0" * 64),
        ("source_contract_digest", "0" * 64),
    ],
)
def test_loading_refuses_rebinding_to_different_forward_history(field, value):
    wages = bundle()
    with pytest.raises(ValueError, match="history"):
        CoveredWageHistory.from_json(
            wages.to_json(), history=replace(wages.history, **{field: value})
        )


def test_loading_revalidates_envelope_metadata_and_expected_digest():
    wages = bundle()
    for mutation in (
        "missing_row",
        "unknown_field",
        "row_unknown_field",
        "history_digest",
        "unit",
    ):
        doc = json.loads(wages.to_json())
        if mutation == "missing_row":
            doc["observations"].pop()
        elif mutation == "unknown_field":
            doc["accepted"] = True
        elif mutation == "row_unknown_field":
            doc["observations"][0]["accepted"] = True
        else:
            doc[mutation] = "0" * 64
        with pytest.raises(ValueError):
            CoveredWageHistory.from_json(
                json.dumps(doc), history=wages.history
            )
    with pytest.raises(ValueError, match="digest"):
        CoveredWageHistory.from_json(
            wages.to_json(), history=wages.history, expected_digest="0" * 64
        )


def test_duplicate_json_members_and_nonfinite_constants_refuse():
    wages = bundle()
    duplicate = wages.to_json().replace(
        '"schema":', '"schema":"duplicate","schema":'
    )
    nonfinite = wages.to_json().replace(
        '"serialization":"0.00"', '"serialization":NaN'
    )
    for text in (duplicate, nonfinite):
        with pytest.raises(ValueError):
            CoveredWageHistory.from_json(text, history=wages.history)


def test_attaching_wages_does_not_change_labor_history_or_produce_policy_input():
    forward = history()
    before = forward.to_json()
    wages = bundle(forward)
    assert forward.to_json() == before
    assert wages.history is forward
    doc = json.loads(wages.to_json())
    assert doc["concept"] == "source_reported_uncapped_employee_wages_covered"
    assert "creditable_earnings" not in doc


@pytest.mark.parametrize("kind,bound", [("int64", 2**63), ("uint64", 2**64)])
def test_integer_source_range_is_preserved(kind, bound):
    assert SourceAmount(kind, str(bound - 1)).serialization == str(bound - 1)
    with pytest.raises(ValueError):
        SourceAmount(kind, str(bound))


def test_missing_coordinates_and_decimal_signed_zero_preserve_source_state():
    wages = bundle()
    assert wages.missing_coordinates == ((1, 2014), (0, 2015))
    source = SourceAmount("decimal", "-0.00")
    assert source.is_zero
    assert source.serialization == "-0.00"
    with pytest.raises(ValueError):
        replace(wages.observations[1], missing_reason="guess")


def test_same_private_keys_do_not_permit_a_different_identity_map():
    wages = bundle()
    another = PersonIdentityMap.from_identities(
        [PersonIdentity("string", "002"), PersonIdentity("uint64", 2**64 - 1)]
    )
    different = replace(wages.history, identity_map=another)
    with pytest.raises(ValueError, match="history"):
        CoveredWageHistory.from_json(wages.to_json(), history=different)
