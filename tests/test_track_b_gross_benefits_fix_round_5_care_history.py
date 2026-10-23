"""Care-history settlement on invented statutory-conformance cases.

Verification class: statutory conformance. No population, behavioral or
forecast claim. Initial-care history refuses only if the auxiliary
payable can differ (202(k)(3)(A); RS 00615.010/.201A.2).
"""

from dataclasses import replace
from fractions import Fraction as F

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import source_text, ssa_params

PARAMS = ssa_params()
NOW = g.YearMonth(2026, 1)


def _state(built=False, pia=F("1.10")):
    if built:
        return g.record_state(
            g.WorkerRecord(g.FamilyKind.RETIREMENT, 2020, pia), PARAMS
        )
    return g.RecordState(
        g.FamilyKind.RETIREMENT,
        pia,
        g.floor_dime(pia * F(3, 2)),
        worker=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, pia),
    )


def _family(state, members):
    return g.family_benefits(
        state, members, payment_month=NOW, params=PARAMS, standalone=True
    )


def _review_spouse(initial):
    return g.Beneficiary(
        "d",
        g.Role.DIVORCED_SPOUSE,
        birth_year=1943,
        own_benefit=g.OwnBenefit(
            g.OwnBenefitKind.OLD_AGE,
            F("0.50"),
            reduction_months=36,
            delayed_credit_months=48,
            birth_year=1943,
        ),
        own_benefit_first=True,
        child_in_care=False,
        first_entitlement_child_in_care=initial,
    )


@pytest.mark.parametrize("built", [False, True])
@pytest.mark.parametrize("entry", ["family", "household", "evaluated"])
@pytest.mark.parametrize("initial", [None, False, True])
def test_review_zero_payable_care_history_is_supported(built, entry, initial):
    state = _state(built)
    spouse = _review_spouse(initial)
    if entry == "household":
        result = g.household_benefits(
            {"worker": g.HouseholdRecord("worker", state, [spouse])},
            payment_month=NOW,
            params=PARAMS,
        ).records["worker"]
    elif entry == "evaluated":
        outcome = g.evaluate_family(
            "zero-payable", F(7, 3), lambda: _family(state, [spouse])
        )
        assert outcome.supported
        counts = g.count_family_outcomes([outcome])
        assert counts.rows == counts.supported_rows == 1
        assert counts.weight == counts.supported_weight == F(7, 3)
        assert counts.unsupported_rows == counts.unsupported_weight == 0
        result = outcome.benefits
    else:
        result = _family(state, [spouse])
    row = result.by_id()["d"]
    assert row.original_benefit == row.own_benefit == F("0.50")
    assert row.age_adjusted_rate == F("0.40")
    assert row.auxiliary_payable == row.whole_dollar_auxiliary == 0
    assert result.record_total == F("1.10")
    assert result.record_total_whole_dollars == 1
    if initial is not False:
        assert row.note == (
            "care history does not affect auxiliary payable; "
            "age_adjusted_rate displays the ordinary diagnostic rate "
            "2/5; the care-exempt rate is 1/2"
        )


def test_review_zero_payable_care_history_follows_captured_zero_floor():
    assert "shall be reduced, but not below zero" in source_text(
        "ssa_act_202_215"
    )


@pytest.mark.parametrize("initial", [None, False, True])
def test_review_minimized_care_history_zero_after_auxiliary_age_reduction(
    initial,
):
    spouse = g.Beneficiary(
        "d",
        g.Role.DIVORCED_SPOUSE,
        own_benefit=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F("0.10")),
        own_benefit_first=False,
        reduction_months=1,
        child_in_care=False,
        first_entitlement_child_in_care=initial,
    )
    row = _family(_state(pia=F("0.30")), [spouse]).by_id()["d"]
    assert row.original_benefit == row.own_benefit == F("0.10")
    assert row.age_adjusted_rate == row.auxiliary_payable == 0
    assert row.whole_dollar_auxiliary == 0
    if initial is not False:
        assert row.note == (
            "care history does not affect auxiliary payable; "
            "age_adjusted_rate displays the ordinary diagnostic rate "
            "0; the care-exempt rate is 1/10"
        )


@settings(max_examples=150, deadline=None, derandomize=True)
@example(11, 46, 36, 48, 0, True, None, F(7, 3))
@example(3, 34, 0, 0, 1, False, True, F(1, 10))
@given(
    pia_dimes=st.integers(1, 20000),
    own_fraction=st.integers(0, 49),
    own_months=st.integers(0, 48),
    delayed_months=st.integers(0, 48),
    auxiliary_months=st.integers(0, 48),
    own_first=st.booleans(),
    initial=st.one_of(st.none(), st.just(True)),
    weight=st.fractions(min_value=F(1, 10), max_value=10),
)
def test_property_care_history_refuses_exactly_when_payables_differ(
    pia_dimes,
    own_fraction,
    own_months,
    delayed_months,
    auxiliary_months,
    own_first,
    initial,
    weight,
):
    pia = F(pia_dimes, 10)
    state = _state(pia=pia)
    spouse = g.Beneficiary(
        "d",
        g.Role.DIVORCED_SPOUSE,
        birth_year=1943,
        own_benefit=g.OwnBenefit(
            g.OwnBenefitKind.OLD_AGE,
            F(pia_dimes * own_fraction // 100, 10),
            reduction_months=own_months,
            delayed_credit_months=delayed_months,
            birth_year=1943,
        ),
        own_benefit_first=own_first,
        reduction_months=auxiliary_months,
        child_in_care=False,
        first_entitlement_child_in_care=False,
    )
    ordinary_family = _family(state, [spouse])
    ordinary = ordinary_family.by_id()["d"]
    care = _family(
        state,
        [
            replace(spouse, child_in_care="c"),
            g.Beneficiary("c", g.Role.CHILD),
        ],
    ).by_id()["d"]
    outcome = g.evaluate_family(
        "history",
        weight,
        lambda: _family(
            state,
            [replace(spouse, first_entitlement_child_in_care=initial)],
        ),
    )
    differs = ordinary.auxiliary_payable != care.auxiliary_payable
    assert outcome.supported is not differs
    counts = g.count_family_outcomes([outcome])
    assert counts.rows == 1
    assert counts.weight == weight
    if differs:
        assert outcome.unsupported.reason is (
            g.UnsupportedReason.DIVORCED_SPOUSE_CARE_HISTORY
        )
        assert counts.unsupported_rows == 1
        assert counts.unsupported_weight == weight
        assert counts.unsupported_by_reason == {
            g.UnsupportedReason.DIVORCED_SPOUSE_CARE_HISTORY: (1, weight)
        }
    else:
        row = outcome.benefits.by_id()["d"]
        assert row.auxiliary_payable == ordinary.auxiliary_payable
        assert row.own_benefit == ordinary.own_benefit
        assert row.age_adjusted_rate == ordinary.age_adjusted_rate
        assert not row.subject_to_family_maximum
        assert row.counted_against_maximum == 0
        assert outcome.benefits.record_total == ordinary_family.record_total
        assert outcome.benefits.record_total_whole_dollars == (
            ordinary_family.record_total_whole_dollars
        )
        assert g.savings_clause_total(outcome.benefits) == (
            g.savings_clause_total(ordinary_family)
        )
        assert counts.unsupported_rows == counts.unsupported_weight == 0
        if ordinary.age_adjusted_rate != care.age_adjusted_rate:
            assert row.note == (
                "care history does not affect auxiliary payable; "
                "age_adjusted_rate displays the ordinary diagnostic rate "
                f"{ordinary.age_adjusted_rate}; the care-exempt rate is "
                f"{care.age_adjusted_rate}"
            )
