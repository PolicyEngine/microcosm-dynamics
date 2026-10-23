"""Divorced-spouse care months on invented statutory-conformance cases.

Verification class: statutory conformance. No population, behavioral or
forecast claim. Current care uses RS 00615.010/.201A.2; initial-month care
history outside that settled monthly surface is explicitly refused.
"""

from dataclasses import replace
from fractions import Fraction as F

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import source_text, ssa_params

PARAMS = ssa_params()
NOW = g.YearMonth(2026, 1)


def _state(built=False, pia=F(1000), maximum=F(1500)):
    if built:
        return g.record_state(
            g.WorkerRecord(g.FamilyKind.RETIREMENT, 2020, pia), PARAMS
        )
    return g.RecordState(
        g.FamilyKind.RETIREMENT,
        pia,
        maximum,
        worker=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, pia),
    )


def _family(state, members):
    return g.family_benefits(
        state, members, payment_month=NOW, params=PARAMS, standalone=True
    )


def _divorce(care="c", *, own_months=36, months=0, own_first=True, **extra):
    return g.Beneficiary(
        "d",
        g.Role.DIVORCED_SPOUSE,
        birth_year=1962,
        own_benefit=g.OwnBenefit(
            g.OwnBenefitKind.OLD_AGE,
            F(200),
            reduction_months=own_months,
            birth_year=1962,
        ),
        own_benefit_first=own_first,
        reduction_months=months,
        child_in_care=care,
        **extra,
    )


@pytest.mark.parametrize("built", [False, True])
@pytest.mark.parametrize("months", [0, 36])
@pytest.mark.parametrize("own_first", [False, True])
def test_review_divorced_current_care_pays_340_in_both_entry_styles(
    built, months, own_first
):
    result = _family(
        _state(built),
        [
            _divorce(months=months, own_first=own_first),
            g.Beneficiary("c", g.Role.CHILD),
        ],
    )
    row = result.by_id()["d"]
    assert row.own_benefit == 160
    assert row.original_benefit == row.age_adjusted_rate == 500
    assert row.auxiliary_payable == row.whole_dollar_auxiliary == 340
    assert not row.subject_to_family_maximum
    assert row.counted_against_maximum == 0
    assert result.worker_benefit == 1000
    assert result.by_id()["c"].auxiliary_payable == 500
    assert result.record_total == result.record_total_whole_dollars == 1840


@pytest.mark.parametrize(
    "own_months,own,auxiliary",
    [
        (0, F(200), F(300)),
        (1, F("198.80"), F("301.20")),
        (36, F(160), F(340)),
        (60, F(140), F(360)),
    ],
)
def test_review_divorced_care_offsets_the_reduced_own_rib(
    own_months, own, auxiliary
):
    result = _family(
        _state(),
        [_divorce(own_months=own_months), g.Beneficiary("c", g.Role.CHILD)],
    )
    row = result.by_id()["d"]
    assert row.own_benefit == own
    assert row.auxiliary_payable == auxiliary
    assert row.own_benefit + row.auxiliary_payable == 500


def test_review_divorced_care_minimized_dime_counterexample():
    spouse = g.Beneficiary(
        "d",
        g.Role.DIVORCED_SPOUSE,
        own_benefit=g.OwnBenefit(
            g.OwnBenefitKind.OLD_AGE, F("0.10"), reduction_months=1
        ),
        own_benefit_first=True,
        child_in_care="c",
    )
    result = _family(
        _state(pia=F("0.30"), maximum=F("0.40")),
        [spouse, g.Beneficiary("c", g.Role.CHILD)],
    )
    assert result.by_id()["d"].own_benefit == 0
    assert result.by_id()["d"].auxiliary_payable == F("0.10")
    assert result.record_total == F("0.50")
    assert result.record_total_whole_dollars == 0


@pytest.mark.parametrize("months,expected", [(0, F(300)), (36, F(225))])
def test_review_aged_divorced_spouse_without_care_keeps_method_c(
    months, expected
):
    spouse = _divorce(
        False, months=months, first_entitlement_child_in_care=False
    )
    result = _family(_state(), [spouse, g.Beneficiary("c", g.Role.CHILD)])
    assert result.by_id()["d"].auxiliary_payable == expected
    assert result.record_total == 1500 + expected


@pytest.mark.parametrize("built", [False, True])
@pytest.mark.parametrize("initial", [None, True])
def test_review_divorced_care_history_has_named_weighted_refusal(
    built, initial
):
    spouse = _divorce(False, first_entitlement_child_in_care=initial)
    outcome = g.evaluate_family(
        "care-history",
        F(7, 3),
        lambda: _family(_state(built), [spouse]),
    )
    assert not outcome.supported
    assert outcome.unsupported.reason.value == "divorced_spouse_care_history"
    counts = g.count_family_outcomes([outcome])
    assert counts.rows == counts.unsupported_rows == 1
    assert counts.weight == counts.unsupported_weight == F(7, 3)
    assert counts.unsupported_by_reason == {
        outcome.unsupported.reason: (1, F(7, 3))
    }
    for aggregate in (g.weighted_record_total, g.weighted_mean_record_total):
        with pytest.raises(g.FamilyTargetBlocked):
            aggregate([outcome])


def test_review_divorced_unknown_current_care_is_a_named_refusal():
    outcome = g.evaluate_family(
        "unknown-current-care",
        F(5, 2),
        lambda: _family(
            _state(),
            [
                _divorce(None, first_entitlement_child_in_care=False),
                g.Beneficiary("c", g.Role.CHILD),
            ],
        ),
    )
    assert not outcome.supported
    assert (
        outcome.unsupported.reason.value
        == "divorced_spouse_child_in_care_unknown"
    )
    assert g.count_family_outcomes([outcome]).unsupported_weight == F(5, 2)


@pytest.mark.parametrize("care", [True, "", "missing", "d"])
def test_review_invalid_divorced_care_precedes_record_refusal(care):
    state = replace(
        _state(), conditions={g.RecordCondition.NON_AIME_FORMULA_PIA}
    )
    with pytest.raises(g.InvalidFamilyInput, match="child_in_care"):
        _family(state, [_divorce(care)])


@pytest.mark.parametrize(
    "source,quote",
    [
        (
            "poms_rs_00615_010",
            "A spouse's benefit is not reduced for any month in which the spouse or divorced spouse has an entitled child in care.",
        ),
        (
            "poms_rs_00615_010",
            "If the entitled child was in care in the MOET, a divorced spouse's benefit remains unreduced after the child's benefit terminates.",
        ),
        (
            "poms_rs_00615_201",
            "When RIB entitlement is involved, for months with a child-in-care, the amount payable as a spouse will always be the difference between the unreduced spouse benefit and the reduced RIB rate.",
        ),
        (
            "poms_rs_00615_201",
            "For all months before FRA for a divorced spouse if they had an entitled child of the NH in care in the first month that they were entitled to benefits as a divorced spouse.",
        ),
    ],
)
def test_review_divorced_care_rules_are_quoted_from_the_captures(
    source, quote
):
    assert quote in source_text(source)


@settings(max_examples=75, deadline=None, derandomize=True)
@given(
    pia_dimes=st.integers(3, 20000),
    own_fraction=st.integers(0, 49),
    own_months=st.integers(0, 60),
    months=st.integers(0, 60),
    first=st.booleans(),
    children=st.integers(1, 4),
)
def test_property_divorced_care_offset_outside_maximum_and_money_invariants(
    pia_dimes, own_fraction, own_months, months, first, children
):
    pia = F(pia_dimes, 10)
    own_pia = F(pia_dimes * own_fraction // 100, 10)
    own = g.OwnBenefit(
        g.OwnBenefitKind.OLD_AGE, own_pia, reduction_months=own_months
    )
    spouse = g.Beneficiary(
        "d",
        g.Role.DIVORCED_SPOUSE,
        own_benefit=own,
        own_benefit_first=first,
        reduction_months=months,
        child_in_care="c0",
    )
    child_rows = [
        g.Beneficiary(f"c{i}", g.Role.CHILD) for i in range(children)
    ]
    state = _state(pia=pia, maximum=g.floor_dime(pia * F(3, 2)))
    baseline = _family(state, child_rows)
    result = _family(state, [spouse, *child_rows])
    row = result.by_id()["d"]
    expected_own = g.own_monthly_benefit(own, PARAMS)[1]
    expected = max(F(0), g.floor_dime(pia / 2) - expected_own)
    assert row.auxiliary_payable == expected
    assert 0 <= expected <= row.original_benefit
    assert (expected * 10).denominator == 1
    assert not row.subject_to_family_maximum
    assert row.counted_against_maximum == 0
    assert (
        result.subject_total == baseline.subject_total <= state.family_maximum
    )
    for child in child_rows:
        assert (
            result.by_id()[child.beneficiary_id]
            == baseline.by_id()[child.beneficiary_id]
        )
    assert result.record_total == baseline.record_total + expected
    assert (
        result.record_total_whole_dollars
        == baseline.record_total_whole_dollars + int(expected)
    )
    assert result == _family(state, [spouse, *child_rows])
    assert (
        result.by_id()
        == _family(state, [*reversed(child_rows), spouse]).by_id()
    )
    assert (
        row
        == _family(
            state,
            [
                replace(
                    spouse, reduction_months=0, own_benefit_first=not first
                ),
                *child_rows,
            ],
        ).by_id()["d"]
    )


@settings(max_examples=35, deadline=None, derandomize=True)
@given(
    weight=st.fractions(min_value=F(1, 10), max_value=10),
    initial=st.one_of(st.none(), st.just(True)),
    current_unknown=st.booleans(),
)
def test_property_divorced_history_refusal_retains_every_weight(
    weight, initial, current_unknown
):
    outcome = g.evaluate_family(
        "history",
        weight,
        lambda: _family(
            _state(),
            [
                _divorce(
                    None if current_unknown else False,
                    first_entitlement_child_in_care=initial,
                ),
                g.Beneficiary("c", g.Role.CHILD),
            ],
        ),
    )
    counts = g.count_family_outcomes([outcome])
    assert counts.rows == counts.unsupported_rows == 1
    assert counts.weight == counts.unsupported_weight == weight
    assert outcome.unsupported.reason.value == (
        "divorced_spouse_child_in_care_unknown"
        if current_unknown
        else "divorced_spouse_care_history"
    )
    assert counts.unsupported_by_reason == {
        outcome.unsupported.reason: (1, weight)
    }
    for aggregate in (g.weighted_record_total, g.weighted_mean_record_total):
        with pytest.raises(g.FamilyTargetBlocked):
            aggregate([outcome])


@pytest.mark.parametrize("built", [False, True])
def test_review_divorced_current_care_needs_no_rib_chronology(built):
    spouse = _divorce(own_first=None, months=36)
    row = _family(
        _state(built), [spouse, g.Beneficiary("c", g.Role.CHILD)]
    ).by_id()["d"]
    assert row.own_benefit == 160
    assert row.auxiliary_payable == 340


def test_review_divorced_current_care_without_own_benefit_pays_full_ob():
    spouse = g.Beneficiary(
        "d", g.Role.DIVORCED_SPOUSE, reduction_months=36, child_in_care="c"
    )
    result = _family(_state(), [spouse, g.Beneficiary("c", g.Role.CHILD)])
    assert result.by_id()["d"].auxiliary_payable == 500
    assert result.by_id()["d"].own_benefit is None
    assert result.record_total == 2000


@pytest.mark.parametrize("initial", [None, False, True])
def test_review_no_reduction_needs_no_care_history_to_settle_money(initial):
    spouse = g.Beneficiary(
        "d", g.Role.DIVORCED_SPOUSE, first_entitlement_child_in_care=initial
    )
    assert _family(_state(), [spouse]).by_id()["d"].auxiliary_payable == 500


@pytest.mark.parametrize("initial", [0, 1, "c", "", (), []])
def test_review_invalid_initial_care_history_is_input_error(initial):
    with pytest.raises(
        g.InvalidFamilyInput, match="first_entitlement_child_in_care"
    ):
        _divorce(False, first_entitlement_child_in_care=initial)


@pytest.mark.parametrize("role", [g.Role.SPOUSE, g.Role.CHILD, g.Role.WIDOW])
def test_review_initial_divorced_care_history_on_other_role_is_input_error(
    role,
):
    with pytest.raises(
        g.InvalidFamilyInput, match="first_entitlement_child_in_care"
    ):
        g.Beneficiary("b", role, first_entitlement_child_in_care=False)


@settings(max_examples=50, deadline=None, derandomize=True)
@given(
    pia=st.integers(1, 3000),
    own_percent=st.integers(0, 49),
    months=st.integers(0, 60),
    first=st.one_of(st.none(), st.booleans()),
)
def test_property_divorced_care_matches_shared_spouse_and_built_record_surfaces(
    pia, own_percent, months, first
):
    own = g.OwnBenefit(
        g.OwnBenefitKind.OLD_AGE,
        F(pia * own_percent // 100),
        reduction_months=months,
    )
    spouse = g.Beneficiary(
        "d",
        g.Role.DIVORCED_SPOUSE,
        own_benefit=own,
        own_benefit_first=first,
        child_in_care="c",
    )
    built = _state(True, pia=F(pia))
    direct = _state(pia=F(pia), maximum=built.family_maximum)
    members = [spouse, g.Beneficiary("c", g.Role.CHILD)]
    built_result = _family(built, members)
    direct_result = _family(direct, members)
    assert built_result.by_id() == direct_result.by_id()
    assert built_result.record_total == direct_result.record_total
    # With no other auxiliary the ordinary care spouse has the full OB.
    # This is the shared semantic surface; divorced status alone changes
    # maximum participation when other beneficiaries make it bind.
    care_spouse = g.Beneficiary(
        "d", g.Role.SPOUSE_CHILD_IN_CARE, own_benefit=own
    )
    shared = _family(direct, [care_spouse]).by_id()["d"]
    row = direct_result.by_id()["d"]
    assert row.age_adjusted_rate == shared.age_adjusted_rate
    assert row.auxiliary_payable == shared.auxiliary_payable
    assert row.own_benefit == shared.own_benefit


@settings(max_examples=35, deadline=None, derandomize=True)
@given(index=st.integers(0, 10000), bad_history=st.integers())
def test_property_divorced_care_input_errors_precede_coverage_refusals(
    index, bad_history
):
    state = replace(
        _state(), conditions={g.RecordCondition.NON_AIME_FORMULA_PIA}
    )
    with pytest.raises(g.InvalidFamilyInput, match="child_in_care"):
        _family(state, [_divorce(f"absent-{index}")])
    with pytest.raises(
        g.InvalidFamilyInput, match="first_entitlement_child_in_care"
    ):
        _family(
            state,
            [_divorce(False, first_entitlement_child_in_care=bad_history)],
        )
