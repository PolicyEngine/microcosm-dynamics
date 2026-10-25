"""Public declarations reject malformed fields at construction.

Verification class: statutory conformance on invented cases only. These
checks admit no population, behavioral or forecast claim.
"""

from dataclasses import fields, is_dataclass, replace
from fractions import Fraction as F

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import computed_refusal, ssa_params

PARAMS = ssa_params()
MONTH = g.YearMonth(2023, 12)


def _result():
    return g.family_benefits(
        g.RecordState(
            g.FamilyKind.SURVIVOR,
            F(0),
            F(0),
            widow_drc_savings_clause=False,
        ),
        [g.Beneficiary("child", g.Role.CHILD)],
        payment_month=MONTH,
        params=PARAMS,
        standalone=True,
    )


def test_wrong_enum_refusal_rejected_before_outcome_or_denominator():
    outcomes = []
    with pytest.raises(g.InvalidFamilyInput):
        outcomes.append(
            g.FamilyOutcome(
                "bad",
                F(7, 3),
                None,
                g.FamilyConfigurationUnsupported(
                    g.BeneficiaryCondition.GOVERNMENT_PENSION_OFFSET,
                    "wrong enum class",
                ),
            )
        )
    assert g.count_family_outcomes(outcomes).rows == 0


@pytest.mark.parametrize(
    "field,value", [("beneficiaries", None), ("record_total", F(-1))]
)
def test_review_result_corruption_rejected_at_replace(field, value):
    result = _result()
    with pytest.raises(g.InvalidFamilyInput):
        replace(result, **{field: value})


def _declarations():
    result = _result()
    own = g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(0))
    state = g.RecordState(g.FamilyKind.RETIREMENT, F(0), F(0), own)
    outcome = g.evaluate_family("valid", F(1), lambda: result)
    return {
        "YearMonth": MONTH,
        "StatutoryRates": g.statutory_rates(PARAMS),
        "OwnBenefit": own,
        "Beneficiary": g.Beneficiary("child", g.Role.CHILD),
        "WorkerRecord": g.WorkerRecord(g.FamilyKind.RETIREMENT, 2023, F(0)),
        "RecordState": state,
        "HouseholdRecord": g.HouseholdRecord("worker", state),
        "BeneficiaryBenefit": result.beneficiaries[0],
        "FamilyBenefits": result,
        "HouseholdBenefits": g.household_benefits(
            {"worker": g.HouseholdRecord("worker", state)},
            payment_month=MONTH,
            params=PARAMS,
        ),
        "FamilyOutcome": outcome,
        "FamilyDenominator": g.count_family_outcomes([outcome]),
    }


DECLARATIONS = _declarations()
FIELDS = tuple(
    (name, field.name)
    for name, value in DECLARATIONS.items()
    for field in fields(value)
)


def test_all_exported_dataclass_fields_have_constructor_coverage():
    public_dataclasses = {
        name for name in g.__all__ if is_dataclass(getattr(g, name))
    }
    assert set(DECLARATIONS) == public_dataclasses
    assert len(FIELDS) == sum(len(fields(v)) for v in DECLARATIONS.values())


@pytest.mark.parametrize("name,field", FIELDS)
def test_each_public_dataclass_field_rejects_an_object(name, field):
    with pytest.raises(g.InvalidFamilyInput):
        replace(DECLARATIONS[name], **{field: object()})


@settings(max_examples=160, deadline=None)
@given(st.sampled_from(FIELDS), st.sampled_from([True, -1, float("inf")]))
def test_constructor_corruption_is_an_input_error(case, corrupt):
    name, field = case
    if corrupt is True and field in {
        "entitled",
        "subject_to_family_maximum",
        "family_maximum_binding",
        "redistribution_applied",
        "widow_drc_savings_clause",
        "own_benefit_first",
        "first_entitlement_child_in_care",
    }:
        return
    # Negative values are meaningful text/numbers only when admitted by the
    # declared field; none of these public declarations accepts a negative.
    with pytest.raises(g.InvalidFamilyInput):
        replace(DECLARATIONS[name], **{field: corrupt})


@pytest.mark.parametrize(
    "name,field,value",
    [
        ("OwnBenefit", "reduction_months", 61),
        ("WorkerRecord", "worker_reduction_months", 61),
        ("YearMonth", "month", 13),
        ("YearMonth", "year", 10000),
        ("StatutoryRates", "spouse_share", F(2)),
        ("StatutoryRates", "worker_bracket_months", 0),
        ("FamilyDenominator", "rows", -1),
        (
            "FamilyDenominator",
            "unsupported_by_reason",
            {g.Role.CHILD: (1, F(1))},
        ),
        (
            "FamilyDenominator",
            "unsupported_by_reason",
            {g.UnsupportedReason.SAVINGS_CLAUSE: (True, F(1))},
        ),
    ],
)
def test_public_constructor_ranges_and_nested_enum_types(name, field, value):
    with pytest.raises(g.InvalidFamilyInput):
        replace(DECLARATIONS[name], **{field: value})


@pytest.mark.parametrize(
    "field", ["reason", "detail", "beneficiary_id", "record_id"]
)
def test_refusal_validates_every_field(field):
    values = dict(
        reason=g.UnsupportedReason.GOVERNMENT_PENSION_OFFSET,
        detail="declared condition",
        beneficiary_id="person",
        record_id="worker",
    )
    values[field] = object()
    with pytest.raises(g.InvalidFamilyInput):
        g.FamilyConfigurationUnsupported(**values)


def test_nested_results_and_refusals_are_revalidated_at_construction():
    result = _result()
    bad_row = _result().beneficiaries[0]
    object.__setattr__(bad_row, "role", g.FamilyKind.SURVIVOR)
    with pytest.raises(g.InvalidFamilyInput):
        replace(result, beneficiaries=(bad_row,))
    object.__setattr__(result, "record_total", F(-1))
    with pytest.raises(g.InvalidFamilyInput):
        g.FamilyOutcome("bad", F(7, 3), result, None)
    refusal = computed_refusal(g.UnsupportedReason.GOVERNMENT_PENSION_OFFSET)
    object.__setattr__(
        refusal, "reason", g.BeneficiaryCondition.GOVERNMENT_PENSION_OFFSET
    )
    with pytest.raises(g.InvalidFamilyInput):
        g.FamilyOutcome("bad", F(7, 3), None, refusal)


@settings(max_examples=20, deadline=None)
@given(
    st.lists(
        st.text(alphabet="abcxyz", min_size=1, max_size=5),
        min_size=1,
        max_size=5,
        unique=True,
    )
)
def test_result_mappings_are_immutable_snapshots(keys):
    records = {
        key: g.HouseholdRecord(
            key,
            g.RecordState(
                g.FamilyKind.SURVIVOR,
                F(0),
                F(0),
                widow_drc_savings_clause=False,
            ),
        )
        for key in keys
    }
    household = g.household_benefits(
        records, payment_month=MONTH, params=PARAMS
    )
    records.clear()
    assert set(household.records) == set(keys)
    with pytest.raises(TypeError):
        household.records["other"] = _result()

    def refused():
        raise computed_refusal(g.UnsupportedReason.SAVINGS_CLAUSE)

    outcomes = [g.evaluate_family(key, F(1), refused) for key in keys]
    denominator = g.count_family_outcomes(outcomes)
    outcomes.clear()
    assert denominator.rows == denominator.unsupported_rows == len(keys)
    assert denominator.weight == denominator.unsupported_weight == len(keys)
    assert set(denominator.unsupported_by_reason) == {
        g.UnsupportedReason.SAVINGS_CLAUSE
    }
    with pytest.raises(TypeError):
        denominator.unsupported_by_reason[
            g.UnsupportedReason.SAVINGS_CLAUSE
        ] = (
            0,
            F(0),
        )


@settings(max_examples=50, deadline=None)
@given(st.integers(min_value=1, max_value=1000))
def test_result_and_denominator_total_identities_reject_positive_corruption(
    amount,
):
    result = _result()
    denominator = g.count_family_outcomes(
        [g.evaluate_family("valid", F(1), lambda: result)]
    )
    for name, value in (
        ("record_total", F(amount)),
        ("record_total_whole_dollars", amount),
        ("subject_total", F(amount)),
    ):
        with pytest.raises(g.InvalidFamilyInput):
            replace(result, **{name: value})
    for name, value in (("rows", 1 + amount), ("weight", F(1 + amount))):
        with pytest.raises(g.InvalidFamilyInput):
            replace(denominator, **{name: value})
    with pytest.raises(g.InvalidFamilyInput):
        replace(
            denominator,
            unsupported_by_reason={
                g.UnsupportedReason.SAVINGS_CLAUSE: (amount, F(amount))
            },
        )
