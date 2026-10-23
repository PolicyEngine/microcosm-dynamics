"""Computed grace evidence provenance; statutory conformance, invented only."""

import copy
import pickle
from dataclasses import fields, replace

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import ret_grace as grace
from populace_dynamics.track_b import ret_ledger as r
from populace_dynamics.track_b._provenance import _computed, _result_values
from tests.test_track_b_ret_ledger import (
    PARAMS,
    YEAR,
    beneficiary,
    record,
)


def decision():
    month = grace.GraceMonth(
        {grace.BenefitType.RIB}, {grace.BenefitType.RIB}, True
    )
    return grace.grace_year(YEAR, grace.GraceYearState(), [month] * 12)


def values(value):
    return {field.name: getattr(value, field.name) for field in fields(value)}


def forged(value):
    result = object.__new__(type(value))
    for name, item in values(value).items():
        object.__setattr__(result, name, item)
    return result


@pytest.mark.parametrize(
    "operation", ["construct", "replace", "copy", "deepcopy"]
)
def test_grace_decision_rejects_public_construction_and_copy(operation):
    result = decision()
    operations = {
        "construct": lambda: type(result)(**values(result)),
        "replace": lambda: replace(result),
        "copy": lambda: copy.copy(result),
        "deepcopy": lambda: copy.deepcopy(result),
    }
    with pytest.raises(r.InvalidFamilyInput):
        operations[operation]()


@pytest.mark.parametrize("field", ["grace", "estimated_grace"])
@pytest.mark.parametrize("tamper", ["unsealed", "altered", "nested"])
@pytest.mark.parametrize("admission", ["beneficiary", "record", "ledger"])
def test_every_ret_admission_rejects_invalid_grace_evidence(
    field, tamper, admission
):
    result = decision()
    member = (
        beneficiary(**{field: result}) if admission != "beneficiary" else None
    )
    case = record(member) if admission == "ledger" else None
    if case is not None:
        # Record construction detaches declarations; attack the admitted copy.
        member = case.beneficiaries[0]
    if tamper == "unsealed":
        result = forged(result)
        if member is not None:
            object.__setattr__(member, field, result)
    elif tamper == "altered":
        object.__setattr__(result, "applies", False)
    else:
        object.__setattr__(result.next_state, "last_met_year", YEAR - 1)
    with pytest.raises(r.InvalidFamilyInput):
        if admission == "beneficiary":
            beneficiary(**{field: result})
        elif admission == "record":
            record(member)
        else:
            r.apply_ret_year(case, PARAMS)
    if admission == "ledger":
        object.__setattr__(case, "foreign_work", True)
        with pytest.raises(r.InvalidFamilyInput):
            r.apply_ret_year(case, PARAMS)


def test_grace_private_capability_revalidates_nested_state_and_identities():
    result = decision()
    with pytest.raises(r.InvalidFamilyInput):
        pickle.dumps(result)
    restored = result
    assert (
        r.apply_ret_year(record(beneficiary(grace=restored)), PARAMS).year
        == YEAR
    )
    # Private capability exercises seal-time validation; persistence is forbidden.
    cls, fields = type(result), _result_values(result)
    invalid_state = replace(result.next_state)
    object.__setattr__(invalid_state, "had_entitlement", False)
    fields["next_state"] = invalid_state
    with pytest.raises(r.InvalidFamilyInput):
        _computed(cls, **fields)
    # Private capability exercises seal-time validation; persistence is forbidden.
    cls, fields = type(result), _result_values(result)
    fields["next_state"] = replace(result.next_state, last_met_year=YEAR - 1)
    with pytest.raises(r.InvalidFamilyInput):
        _computed(cls, **fields)


@settings(max_examples=20, deadline=None)
@given(st.integers(1, 12), st.sampled_from(["grace", "estimated_grace"]))
def test_grace_pickle_rejection_and_recomputation_preserve_money(month, field):
    months = [
        grace.GraceMonth(
            {grace.BenefitType.RIB}, {grace.BenefitType.RIB}, m == month
        )
        for m in range(1, 13)
    ]
    result = grace.grace_year(YEAR, grace.GraceYearState(), months)
    for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
        with pytest.raises(r.InvalidFamilyInput):
            pickle.dumps(result, protocol=protocol)
    restored = grace.grace_year(YEAR, grace.GraceYearState(), months)
    assert result == restored
    first = r.apply_ret_year(record(beneficiary(**{field: result})), PARAMS)
    second = r.apply_ret_year(record(beneficiary(**{field: restored})), PARAMS)
    assert first == second
    object.__setattr__(restored, "protected_months", frozenset())
    with pytest.raises(r.InvalidFamilyInput):
        beneficiary(**{field: restored})
