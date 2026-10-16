"""G fix-round regressions for cohort periods and historical DRC protection.

Verification class: statutory conformance. Invented families and the captured
RS 00615.712 example admit no population, behavioral or forecast claim.
"""

from dataclasses import replace
from datetime import date
from fractions import Fraction as F

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import source_text, ssa_params

PARAMS = ssa_params()
NOW = g.YearMonth(2030, 1)
BOUNDARY_COHORTS = (
    (1939, 60),
    (1940, 62),
    (1941, 64),
    (1942, 66),
    (1943, 68),
    (1944, 70),
    (1945, 72),
    (1956, 72),
    (1957, 74),
    (1958, 76),
    (1959, 78),
    (1960, 80),
    (1961, 82),
    (1962, 84),
)


def _family(state, members=(), month=NOW):
    return g.family_benefits(
        state, members, payment_month=month, params=PARAMS, standalone=True
    )


def _state(prebuilt, pia=F(1000), refused=False):
    conditions = (
        {g.RecordCondition.WORKERS_COMPENSATION_OFFSET} if refused else set()
    )
    if prebuilt:
        return g.RecordState(
            g.FamilyKind.SURVIVOR,
            pia,
            pia * F(3, 2),
            conditions=conditions,
        )
    return g.record_state(
        g.WorkerRecord(
            g.FamilyKind.SURVIVOR, 2020, pia, conditions=conditions
        ),
        PARAMS,
    )


@pytest.mark.parametrize("prebuilt", [False, True])
@pytest.mark.parametrize(
    "pia,months,period", [(F("21.80"), 1, 63), (F(1000), 60, 84)]
)
def test_review_boundary_widow_counterexamples_are_invalid(
    prebuilt, pia, months, period
):
    with pytest.raises(g.InvalidFamilyInput, match="cohort"):
        widow = g.Beneficiary(
            "w",
            g.Role.WIDOW,
            birth_year=1940,
            reduction_months=months,
            reduction_period_months=period,
            child_in_care=False,
        )
        _family(_state(prebuilt, pia), [widow])


@pytest.mark.parametrize("cohort,period", BOUNDARY_COHORTS)
@pytest.mark.parametrize("prebuilt", [False, True])
def test_review_every_boundary_cohort_rejects_excess_months_before_refusal(
    cohort, period, prebuilt
):
    assert g.widow_reduction_period_months(date(cohort, 1, 2)) == period
    with pytest.raises(g.InvalidFamilyInput):
        widow = g.Beneficiary(
            "w",
            g.Role.WIDOW,
            birth_year=cohort,
            reduction_months=period + 1,
            reduction_period_months=min(period + 2, 84),
            child_in_care=False,
        )
        _family(_state(prebuilt, refused=True), [widow])


@given(st.sampled_from(BOUNDARY_COHORTS), st.integers(60, 84), st.booleans())
@settings(deadline=None)
def test_property_widow_cohort_fixes_exact_period_in_both_entry_styles(
    cohort_period, supplied, prebuilt
):
    cohort, expected = cohort_period
    state = _state(prebuilt)
    if prebuilt:
        # Invented snapshot: no beneficiary was entitled in May 1978.
        state = replace(state, widow_drc_savings_clause=False)

    def compute():
        widow = g.Beneficiary(
            "w",
            g.Role.WIDOW,
            birth_year=cohort,
            reduction_months=1,
            reduction_period_months=supplied,
            child_in_care=False,
        )
        return _family(state, [widow])

    if supplied == expected:
        result = compute()
        assert result.by_id()["w"].auxiliary_payable == g.survivor_age_reduced(
            state.pia, 1, expected, PARAMS
        )
    else:
        with pytest.raises(g.InvalidFamilyInput, match="cohort"):
            compute()


@given(st.sampled_from(BOUNDARY_COHORTS), st.integers(0, 90), st.booleans())
@settings(deadline=None)
def test_property_widow_cohort_bounds_months_and_matches_exact_primitive(
    cohort_period, months, prebuilt
):
    cohort, period = cohort_period
    state = _state(prebuilt)
    if prebuilt:
        state = replace(state, widow_drc_savings_clause=False)

    def compute():
        widow = g.Beneficiary(
            "w",
            g.Role.WIDOW,
            birth_year=cohort,
            reduction_months=months,
            reduction_period_months=period,
            child_in_care=False,
        )
        return _family(state, [widow])

    if months > period:
        with pytest.raises(g.InvalidFamilyInput):
            compute()
    else:
        result = compute()
        expected = g.survivor_age_reduced(state.pia, months, period, PARAMS)
        assert result.by_id()["w"].auxiliary_payable == expected
        assert result.record_total_whole_dollars == g.whole_dollars(expected)


@pytest.mark.parametrize(
    "pia,months,payable,whole",
    [(F("21.80"), 1, F("21.60"), 21), (F(1000), 60, F("724.10"), 724)],
)
def test_review_1940_cohort_legal_period_pays_exact_counterexample_reference(
    pia, months, payable, whole
):
    widow = g.Beneficiary(
        "w",
        g.Role.WIDOW,
        birth_year=1940,
        reduction_months=months,
        reduction_period_months=62,
        child_in_care=False,
    )
    result = _family(_state(False, pia), [widow])
    assert result.by_id()["w"].auxiliary_payable == payable
    assert result.record_total_whole_dollars == whole


@pytest.mark.parametrize("maximum", [F(700), F("704.20")])
def test_review_712_unattested_master_record_refuses_published_case(maximum):
    state = g.RecordState(g.FamilyKind.SURVIVOR, F(400), maximum)
    members = [
        g.Beneficiary(
            "w",
            g.Role.WIDOW,
            original_benefit_basis=F(410),
            child_in_care=False,
        ),
        g.Beneficiary("c", g.Role.CHILD),
    ]
    with pytest.raises(g.FamilyConfigurationUnsupported) as exc:
        _family(state, members, g.YearMonth(2000, 3))
    assert (
        exc.value.reason
        is g.UnsupportedReason.WIDOW_DRC_SAVINGS_CLAUSE_HISTORY_UNKNOWN
    )


@pytest.mark.parametrize("maximum", [F(700), F("704.20")])
@pytest.mark.parametrize("declaration", ["record", "beneficiary"])
def test_review_712_protected_child_refuses_both_published_maxima(
    maximum, declaration
):
    state = g.RecordState(
        g.FamilyKind.SURVIVOR,
        F(400),
        maximum,
        widow_drc_savings_clause=declaration == "record",
    )
    conditions = (
        {g.BeneficiaryCondition.WIDOW_DRC_SAVINGS_CLAUSE}
        if declaration == "beneficiary"
        else set()
    )
    members = [
        g.Beneficiary(
            "w",
            g.Role.WIDOW,
            original_benefit_basis=F(410),
            child_in_care=False,
        ),
        g.Beneficiary("c", g.Role.CHILD, conditions=conditions),
    ]
    outcome = g.evaluate_family(
        "published-712",
        F(3, 2),
        lambda: _family(state, members, g.YearMonth(2000, 3)),
    )
    assert not outcome.supported
    reason = g.UnsupportedReason.WIDOW_DRC_SAVINGS_CLAUSE
    assert outcome.unsupported.reason is reason
    counts = g.count_family_outcomes([outcome])
    assert (counts.rows, counts.weight) == (1, F(3, 2))
    assert counts.unsupported_by_reason == {reason: (1, F(3, 2))}


def test_review_712_worked_example_figures_are_quoted_from_the_capture():
    text = source_text("poms_rs_00615_712")
    for literal in (
        "In 3/00",
        "$400",
        "$700",
        "since 3/78",
        "$300",
        "$10",
        "$410",
        "$710",
        "$700/$710",
        "404.20",
        "295.70",
        "$400.00",
        "$704.20",
    ):
        assert literal in text
    for quote in (
        "The only criterion for this to apply is entitlement for the specific month of 5/78.",
        "Entitlement before or after 5/78 is immaterial.",
        "Because the child was entitled for 5/78, the child is protected by the savings clause and the child's rate will remain at $300.",
    ):
        assert quote in text
    ordinary_widow = g.floor_dime(F(410) * F(700, 710))
    ordinary_child = g.floor_dime(F(300) * F(700, 710))
    assert ordinary_widow == F("404.20")
    assert ordinary_child == F("295.70")
    # Reproduce the published protection independently; G refuses it.
    protected_child = F(300)
    assert ordinary_widow + protected_child == F("704.20")
    assert (
        g.whole_dollars(ordinary_widow) + g.whole_dollars(protected_child)
        == 704
    )


@given(
    st.sampled_from([None, True]), st.integers(1, 30000), st.integers(1, 20)
)
@settings(deadline=None)
def test_property_712_refusals_preserve_denominators_and_input_priority(
    history, dimes, weight
):
    pia = F(dimes, 10)
    state = g.RecordState(
        g.FamilyKind.SURVIVOR,
        pia,
        pia * 2,
        widow_drc_savings_clause=history,
    )
    child = g.Beneficiary("c", g.Role.CHILD)
    reason = (
        g.UnsupportedReason.WIDOW_DRC_SAVINGS_CLAUSE
        if history
        else g.UnsupportedReason.WIDOW_DRC_SAVINGS_CLAUSE_HISTORY_UNKNOWN
    )
    with pytest.raises(g.InvalidFamilyInput, match="unique"):
        g.evaluate_family(
            "invalid", weight, lambda: _family(state, [child, child])
        )
    outcomes = [
        g.evaluate_family("refused", weight, lambda: _family(state, [child]))
    ]
    counts = g.count_family_outcomes(outcomes)
    assert counts.unsupported_by_reason == {reason: (1, F(weight))}
    assert (counts.rows, counts.weight) == (1, F(weight))
    with pytest.raises(g.FamilyTargetBlocked):
        g.weighted_record_total(outcomes)


@pytest.mark.parametrize("prebuilt", [False, True])
def test_review_712_modern_eligibility_does_not_hide_known_prior_dib(prebuilt):
    fields = dict(first_dib_entitlement=g.YearMonth(1978, 5))
    state = (
        g.RecordState(
            g.FamilyKind.SURVIVOR,
            F(400),
            F(700),
            eligibility_year=1985,
            **fields,
        )
        if prebuilt
        else g.record_state(
            g.WorkerRecord(g.FamilyKind.SURVIVOR, 1985, F(400), **fields),
            PARAMS,
        )
    )
    members = [
        g.Beneficiary(
            "w",
            g.Role.WIDOW,
            original_benefit_basis=F(410),
            child_in_care=False,
        ),
        g.Beneficiary("c", g.Role.CHILD),
    ]
    with pytest.raises(g.FamilyConfigurationUnsupported) as exc:
        _family(state, members)
    assert (
        exc.value.reason
        is g.UnsupportedReason.WIDOW_DRC_SAVINGS_CLAUSE_HISTORY_UNKNOWN
    )


def test_review_712_prior_dib_eligibility_rule_is_quoted_from_capture():
    text = source_text("poms_rs_00615_736")
    assert (
        "Prior DIB entitlement more than 12 months before the current "
        "eligibility or death - new eligibility after 1978." in text
    )
    assert (
        "The bend point formula applicable in the year of current "
        "eligibility is applied to the PIA in effect in the last month "
        "of prior DIB entitlement." in text
    )


@given(st.integers(1970, 1980), st.integers(1, 12), st.booleans())
@settings(deadline=None)
def test_property_712_prior_dib_history_matches_both_construction_styles(
    year, month, prebuilt
):
    first_dib = g.YearMonth(year, month)
    state = (
        g.RecordState(
            g.FamilyKind.SURVIVOR,
            F(400),
            F(700),
            eligibility_year=1985,
            first_dib_entitlement=first_dib,
        )
        if prebuilt
        else g.record_state(
            g.WorkerRecord(
                g.FamilyKind.SURVIVOR,
                1985,
                F(400),
                first_dib_entitlement=first_dib,
            ),
            PARAMS,
        )
    )
    members = [g.Beneficiary("c", g.Role.CHILD)]
    if first_dib <= g.YearMonth(1978, 5):
        with pytest.raises(g.FamilyConfigurationUnsupported) as exc:
            _family(state, members)
        assert (
            exc.value.reason
            is g.UnsupportedReason.WIDOW_DRC_SAVINGS_CLAUSE_HISTORY_UNKNOWN
        )
    else:
        assert _family(state, members).record_total == 300
    assert (
        _family(
            replace(state, widow_drc_savings_clause=False), members
        ).record_total
        == 300
    )


def test_review_712_modern_eligibility_without_known_earlier_dib():
    state = g.RecordState(
        g.FamilyKind.SURVIVOR,
        F(400),
        F(700),
        eligibility_year=2020,
    )
    assert (
        _family(state, [g.Beneficiary("c", g.Role.CHILD)]).record_total == 300
    )
