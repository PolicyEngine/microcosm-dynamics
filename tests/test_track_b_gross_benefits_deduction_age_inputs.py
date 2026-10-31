"""Statutory conformance: derive spouse no-care age from supplied facts.

Act 203(c)(2), 20 CFR 404.421(a), RS 00615.003/.010; invented inputs only.
No population, behavioral or forecast claim.
"""

from dataclasses import replace

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from tests.test_track_b_gross_benefits_deductions_fix_round_2 import (
    MONTH,
    PARAMS,
    compute,
    retirement,
)


@pytest.mark.parametrize("household", (False, True))
@pytest.mark.parametrize("own_cohort", (False, True))
@given(cohort=st.integers(1960, 1980))
@settings(max_examples=8, deadline=None)
def test_supplied_younger_cohort_needs_no_age_attestation(
    household, own_cohort, cohort
):
    state, members = retirement(children=0, reduction=0)
    member = replace(members[0], birth_year=cohort)
    if own_cohort:
        member = replace(
            member,
            birth_year=None,
            own_benefit_first=True,
            own_benefit=g.OwnBenefit(
                g.OwnBenefitKind.DISABILITY, 1, birth_year=cohort
            ),
        )
    event = g.BenefitDeduction(g.DeductionReason.NO_CHILD_IN_CARE)
    result = compute(state, (member,), {"B": event}, household)
    family = result.records["record"] if household else result
    assert family.by_id()["B"].auxiliary_payable == 0
    explicit = replace(event, under_full_retirement_age=True)
    assert compute(state, (member,), {"B": explicit}, household) == result


@pytest.mark.parametrize("household", (False, True))
@pytest.mark.parametrize("attestation", (None, False, True))
@given(cohort=st.integers(1930, 1950))
@settings(max_examples=8, deadline=None)
def test_supplied_older_cohort_is_input_error_before_household_refusal(
    household, attestation, cohort
):
    state, members = retirement(children=0, reduction=0)
    member = replace(members[0], birth_year=cohort)
    event = g.BenefitDeduction(
        g.DeductionReason.NO_CHILD_IN_CARE,
        under_full_retirement_age=attestation,
    )
    state = replace(
        state, conditions={g.RecordCondition.ADMINISTRATIVE_FINALITY}
    )
    outcomes = []
    with pytest.raises(g.InvalidFamilyInput):
        outcomes.append(
            g.evaluate_family(
                "age",
                3,
                lambda: compute(state, (member,), {"B": event}, household),
            )
        )
    assert g.count_family_outcomes(outcomes).rows == 0


@pytest.mark.parametrize(
    "offset,expected_under",
    ((-1, True), (0, None), (10, None), (11, False)),
)
@pytest.mark.parametrize("attestation", (None, False, True))
@given(cohort=st.integers(1938, 1960))
@example(cohort=1958)
@settings(max_examples=8, deadline=None)
def test_cohort_fra_interval_uses_attestation_only_when_needed(
    offset, expected_under, attestation, cohort
):
    # Cohort 1958 has FRA 66y8m: earliest September 2024, latest August 2025.
    state, members = retirement(children=0, reduction=0)
    member = replace(members[0], birth_year=cohort)
    # Independent statutory FRA schedule, in months (Act 216(l)).
    fra = (
        780 + 2 * (cohort - 1937)
        if cohort <= 1942
        else 792 if cohort <= 1954 else 792 + 2 * (cohort - 1954)
    )
    year, month = divmod(cohort * 12 + fra + offset, 12)
    payment = g.YearMonth(year, month + 1)
    event = g.BenefitDeduction(
        g.DeductionReason.NO_CHILD_IN_CARE,
        under_full_retirement_age=attestation,
    )
    kwargs = dict(
        payment_month=payment,
        params=PARAMS,
        deductions={"B": event},
        households={},
        standalone=True,
    )
    if (
        expected_under is False
        or attestation is False
        or (expected_under is None and attestation is None)
    ):
        with pytest.raises(g.InvalidFamilyInput):
            g.family_benefits_after_deductions(state, (member,), **kwargs)
    else:
        result = g.family_benefits_after_deductions(state, (member,), **kwargs)
        assert result.by_id()["B"].auxiliary_payable == 0


@pytest.mark.parametrize("reverse", (False, True))
@given(reduction=st.integers(1, 60))
@example(reduction=60)
@settings(max_examples=8, deadline=None)
def test_each_household_entitlement_checks_no_care_age_before_refusal(
    reverse, reduction
):
    state, members = retirement(children=0, reduction=reduction)
    reduced = members[0]
    unreduced = replace(reduced, reduction_months=0)
    entries = [
        ("a", g.HouseholdRecord("worker-a", state, (reduced,))),
        ("b", g.HouseholdRecord("worker-b", state, (unreduced,))),
    ]
    records = dict(reversed(entries) if reverse else entries)
    with pytest.raises(g.InvalidFamilyInput, match="age-reduced"):
        g.household_benefits_after_deductions(
            records,
            payment_month=MONTH,
            params=PARAMS,
            deductions={
                "B": g.BenefitDeduction(
                    g.DeductionReason.NO_CHILD_IN_CARE,
                    under_full_retirement_age=True,
                )
            },
            households={},
        )


@given(credits=st.integers(1, 12))
@example(credits=1)
@settings(max_examples=8, deadline=None)
def test_supplied_delayed_credits_exclude_no_care_even_inside_cohort_interval(
    credits,
):
    state, members = retirement(children=0, reduction=0)
    member = replace(
        members[0],
        birth_year=1958,
        own_benefit_first=True,
        own_benefit=g.OwnBenefit(
            g.OwnBenefitKind.OLD_AGE,
            1,
            birth_year=1958,
            delayed_credit_months=credits,
        ),
    )
    with pytest.raises(g.InvalidFamilyInput, match="post-FRA credits"):
        g.family_benefits_after_deductions(
            state,
            (member,),
            payment_month=g.YearMonth(2025, 2),
            params=PARAMS,
            standalone=True,
            households={},
            deductions={
                "B": g.BenefitDeduction(
                    g.DeductionReason.NO_CHILD_IN_CARE,
                    under_full_retirement_age=True,
                )
            },
        )
