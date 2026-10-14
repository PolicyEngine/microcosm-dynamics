"""RS 00615.340 child-in-care regressions on invented monthly families.

Verification class: statutory conformance. Captured rule examples and
invented amounts admit no population, behavioral or forecast claim.
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


def _family(state, members, month=NOW):
    return g.family_benefits(
        state, members, payment_month=month, params=PARAMS, standalone=True
    )


def _state(pia=F(1000), maximum=F(1750)):
    return g.RecordState(
        g.FamilyKind.SURVIVOR,
        pia,
        maximum,
        widow_drc_savings_clause=False,
    )


def _widow(care, *, role=g.Role.WIDOW, months=60, period=60, **extra):
    return g.Beneficiary(
        "w",
        role,
        birth_year=1935 if period == 60 else 1941,
        reduction_months=months,
        reduction_period_months=period,
        child_in_care=care,
        **extra,
    )


@pytest.mark.parametrize("care,expected", [("c", F(750)), (False, F(715))])
def test_review_child_in_care_counterexample_pays_750_or_715(care, expected):
    result = _family(
        _state(), [_widow(care), g.Beneficiary("c", g.Role.CHILD)]
    )
    assert result.by_id()["w"].auxiliary_payable == expected
    assert result.by_id()["c"].auxiliary_payable == 750
    assert result.record_total == expected + 750
    assert result.record_total_whole_dollars == int(expected) + 750


@pytest.mark.parametrize("built", [False, True])
def test_review_unknown_widow_care_is_refused_in_both_entry_styles(built):
    state = (
        g.record_state(
            g.WorkerRecord(g.FamilyKind.SURVIVOR, 2020, 1000), PARAMS
        )
        if built
        else _state()
    )
    widow = g.Beneficiary(
        "w", g.Role.WIDOW, reduction_months=60, reduction_period_months=60
    )
    outcome = g.evaluate_family(
        "unknown-care",
        F(7, 3),
        lambda: _family(state, [widow, g.Beneficiary("c", g.Role.CHILD)]),
    )
    assert not outcome.supported
    assert outcome.unsupported.reason.value == "widow_child_in_care_unknown"
    counts = g.count_family_outcomes([outcome])
    assert counts.rows == counts.unsupported_rows == 1
    assert counts.weight == counts.unsupported_weight == F(7, 3)
    with pytest.raises(g.FamilyTargetBlocked):
        g.weighted_mean_record_total([outcome])


@pytest.mark.parametrize("care", [True, "", 1, (), "missing", "w", "p"])
def test_review_care_requires_named_entitled_child_before_coverage_refusal(
    care,
):
    state = replace(
        _state(), conditions={g.RecordCondition.WORKERS_COMPENSATION_OFFSET}
    )
    with pytest.raises(g.InvalidFamilyInput, match="child_in_care"):
        _family(
            state,
            [_widow(care), g.Beneficiary("p", g.Role.PARENT)],
        )


def test_review_care_child_must_be_on_same_household_record():
    with pytest.raises(g.InvalidFamilyInput, match="child_in_care"):
        g.household_benefits(
            {
                "one": g.HouseholdRecord("dead-one", _state(), (_widow("c"),)),
                "two": g.HouseholdRecord(
                    "dead-two", _state(), (g.Beneficiary("c", g.Role.CHILD),)
                ),
            },
            payment_month=NOW,
            params=PARAMS,
        )


@pytest.mark.parametrize(
    "role", [g.Role.WIDOW, g.Role.SURVIVING_DIVORCED_SPOUSE]
)
@pytest.mark.parametrize("months,expected", [(64, F(750)), (16, F("928.70"))])
def test_review_340_two_examples_as_exact_monthly_amounts(
    role, months, expected
):
    members = [
        _widow("c", role=role, months=months, period=64),
        g.Beneficiary("c", g.Role.CHILD),
    ]
    result = _family(
        _state(),
        members,
        g.YearMonth(2005, 1 if months == 64 else 7),
    )
    assert result.by_id()["w"].auxiliary_payable == expected
    assert result.by_id()["w"].whole_dollar_auxiliary == int(expected)
    if months == 16:
        # The capture says "about 92.9%": exact .301 reduction and the
        # upward dime rounding give 92.87% for this invented $1,000 PIA.
        assert expected / 10 == F("92.87")
        ordinary = _family(
            _state(),
            [replace(members[0], child_in_care=False), members[1]],
            g.YearMonth(2005, 7),
        )
        assert result.by_id()["w"] == ordinary.by_id()["w"]


@pytest.mark.parametrize(
    "quote",
    [
        "reduced to 71.5% of the PIA because of the 64 RF.",
        "From 1/2005 through 6/2005 they have an entitled child-in-care.",
        "those months is raised to 75% of the PIA.",
        "In 7/2005 they no longer have a child-in-care",
        "Their RF is therefore 58 beginning at FRA.",
        "Their RF is 16 and after age reduction they receive about "
        "92.9% of the PIA.",
        "This policy applies to benefits payable 1/73 and later.",
        "At FRA attainment the widow(er) is granted an ARF to remove all "
        "months the increase was applied.",
    ],
)
def test_review_340_example_figures_and_rules_are_verbatim_in_capture(quote):
    assert quote in source_text("poms_rs_00615_340")


def test_review_340_increased_amount_applies_january_through_june_only():
    children = [g.Beneficiary("c", g.Role.CHILD)]
    widow = _widow("c", months=64, period=64)
    for month in range(1, 7):
        assert (
            _family(_state(), [widow, *children], g.YearMonth(2005, month))
            .by_id()["w"]
            .auxiliary_payable
            == 750
        )
    july = _family(
        _state(),
        [replace(widow, child_in_care=False), *children],
        g.YearMonth(2005, 7),
    )
    assert july.by_id()["w"].auxiliary_payable == 715


def test_review_care_floor_is_mother_father_rate_after_binding_maximum():
    children = [g.Beneficiary(f"c{i}", g.Role.CHILD) for i in range(2)]
    result = _family(_state(), [_widow("c0"), *children])
    assert result.by_id()["w"].standard_rate == 700
    assert result.by_id()["w"].auxiliary_payable == F("583.30")
    assert result.by_id()["c0"].auxiliary_payable == 525
    assert result.by_id()["c1"].auxiliary_payable == 525
    assert result.record_total == F("1633.30")


def test_review_care_floor_preserves_dual_offset_and_parisi_pool():
    own = g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(200), birth_year=1935)
    children = [g.Beneficiary(f"c{i}", g.Role.CHILD) for i in range(2)]
    result = _family(_state(), [_widow("c0", own_benefit=own), *children])
    mother = _family(
        _state(),
        [g.Beneficiary("w", g.Role.MOTHER_FATHER, own_benefit=own), *children],
    )
    assert result.redistribution_applied
    assert (
        result.by_id()["w"].auxiliary_payable
        == mother.by_id()["w"].auxiliary_payable
    )
    assert result.by_id()["w"].auxiliary_payable == F("383.30")
    assert result.record_total <= result.family_maximum


def test_review_care_floor_preserves_surviving_divorced_maximum_exception():
    children = [g.Beneficiary(f"c{i}", g.Role.CHILD) for i in range(3)]
    widow = _widow("c0", role=g.Role.SURVIVING_DIVORCED_SPOUSE)
    result = _family(_state(), [widow, *children])
    ordinary = _family(
        _state(), [replace(widow, child_in_care=False), *children]
    )
    row = result.by_id()["w"]
    assert row.auxiliary_payable == 715
    assert not row.subject_to_family_maximum
    assert row.counted_against_maximum == 0
    assert result.subject_total == ordinary.subject_total == F("1749.90")
    for child in children:
        assert (
            result.by_id()[child.beneficiary_id]
            == ordinary.by_id()[child.beneficiary_id]
        )


def test_review_care_floor_applies_to_disabled_widow_fixed_reduction():
    widow = g.Beneficiary("w", g.Role.DISABLED_WIDOW, child_in_care="c")
    result = _family(_state(), [widow, g.Beneficiary("c", g.Role.CHILD)])
    ordinary = _family(
        _state(),
        [
            replace(widow, child_in_care=False),
            g.Beneficiary("c", g.Role.CHILD),
        ],
    )
    assert result.by_id()["w"].auxiliary_payable == 750
    assert ordinary.by_id()["w"].auxiliary_payable == 715


def test_review_minimal_care_floor_whole_dollar_counterexample():
    widow = _widow("c")
    child = g.Beneficiary("c", g.Role.CHILD)
    result = _family(_state(F("2.70"), F("4.70")), [widow, child])
    ordinary = _family(
        _state(F("2.70"), F("4.70")),
        [replace(widow, child_in_care=False), child],
    )
    assert result.by_id()["w"].auxiliary_payable == 2
    assert result.by_id()["w"].whole_dollar_auxiliary == 2
    assert ordinary.by_id()["w"].auxiliary_payable == F("1.90")
    assert ordinary.by_id()["w"].whole_dollar_auxiliary == 1


def test_review_no_entitled_child_has_no_unknown_care_refusal():
    result = _family(_state(), [_widow(None)])
    assert result.by_id()["w"].auxiliary_payable == 715


@pytest.mark.parametrize("care", [False, "c"])
def test_review_care_input_on_nonwidow_is_invalid(care):
    with pytest.raises(g.InvalidFamilyInput, match="child_in_care"):
        g.Beneficiary("c", g.Role.CHILD, child_in_care=care)


def test_review_child_in_care_before_january_1973_is_outside_payment_scope():
    outcome = g.evaluate_family(
        "before-care-rule",
        F(3, 2),
        lambda: _family(
            _state(),
            [_widow("c"), g.Beneficiary("c", g.Role.CHILD)],
            g.YearMonth(1972, 12),
        ),
    )
    assert not outcome.supported
    assert outcome.unsupported.reason is (
        g.UnsupportedReason.PAYMENT_MONTH_BEFORE_1983
    )
    counts = g.count_family_outcomes([outcome])
    assert counts.rows == counts.unsupported_rows == 1
    assert counts.weight == counts.unsupported_weight == F(3, 2)


def test_review_malformed_care_reference_precedes_historical_payment_refusal():
    with pytest.raises(g.InvalidFamilyInput, match="child_in_care"):
        _family(_state(), [_widow("absent")], g.YearMonth(1972, 12))


@settings(max_examples=75, deadline=None, derandomize=True)
@given(
    units=st.integers(1, 300),
    child_count=st.integers(1, 5),
    months=st.integers(0, 60),
    maximum_share=st.sampled_from([F(3, 2), F(7, 4), F(2)]),
)
def test_property_care_floor_matches_mother_father_and_preserves_money_invariants(
    units,
    child_count,
    months,
    maximum_share,
):
    pia = F(20 * units)
    state = _state(pia, pia * maximum_share)
    children = [
        g.Beneficiary(f"c{i}", g.Role.CHILD) for i in range(child_count)
    ]
    widow = _widow("c0", months=months)
    result = _family(state, [widow, *children])
    ordinary = _family(state, [replace(widow, child_in_care=False), *children])
    mother = _family(
        state, [g.Beneficiary("w", g.Role.MOTHER_FATHER), *children]
    )
    assert result.by_id()["w"].auxiliary_payable == max(
        ordinary.by_id()["w"].auxiliary_payable,
        mother.by_id()["w"].auxiliary_payable,
    )
    for child in children:
        assert (
            result.by_id()[child.beneficiary_id]
            == ordinary.by_id()[child.beneficiary_id]
        )
    assert result.record_total == sum(
        b.auxiliary_payable for b in result.beneficiaries
    )
    assert result.record_total_whole_dollars == sum(
        b.whole_dollar_auxiliary for b in result.beneficiaries
    )
    assert result.record_total <= state.family_maximum
    assert result.subject_total <= state.family_maximum
    assert all(
        (b.auxiliary_payable * 10).denominator == 1
        for b in result.beneficiaries
    )
    assert all(
        0 <= b.auxiliary_payable <= b.family_maximum_rate
        for b in result.beneficiaries
    )
    assert result == _family(state, [widow, *children])
    assert (
        result.by_id() == _family(state, [*reversed(children), widow]).by_id()
    )


@settings(max_examples=60, deadline=None, derandomize=True)
@given(
    units=st.integers(1, 300),
    child_count=st.integers(1, 5),
    first_months=st.integers(0, 60),
    additional_months=st.integers(0, 60),
    low_share=st.sampled_from([F(3, 2), F(7, 4), F(2)]),
)
def test_property_care_payment_is_monotone_in_maximum_and_reduction_months(
    units,
    child_count,
    first_months,
    additional_months,
    low_share,
):
    pia = F(20 * units)
    state = _state(pia, pia * low_share)
    children = [
        g.Beneficiary(f"c{i}", g.Role.CHILD) for i in range(child_count)
    ]
    widow = _widow("c0", months=first_months)
    result = _family(state, [widow, *children])
    later_reduction = _family(
        state,
        [
            replace(
                widow,
                reduction_months=min(60, first_months + additional_months),
            ),
            *children,
        ],
    )
    larger_maximum = _family(
        replace(state, family_maximum=pia * 2), [widow, *children]
    )
    assert (
        later_reduction.by_id()["w"].auxiliary_payable
        <= result.by_id()["w"].auxiliary_payable
        <= larger_maximum.by_id()["w"].auxiliary_payable
    )


@settings(max_examples=35, deadline=None, derandomize=True)
@given(
    weight=st.fractions(min_value=F(1, 10), max_value=10),
    reverse=st.booleans(),
)
def test_property_unknown_care_refusal_preserves_weights_and_blocks_aggregates(
    weight,
    reverse,
):
    members = [_widow(None), g.Beneficiary("c", g.Role.CHILD)]
    if reverse:
        members.reverse()
    outcome = g.evaluate_family(
        "care-unknown", weight, lambda: _family(_state(), members)
    )
    assert not outcome.supported
    counts = g.count_family_outcomes([outcome])
    assert counts.rows == counts.unsupported_rows == 1
    assert counts.weight == counts.unsupported_weight == weight
    assert counts.unsupported_by_reason == {
        outcome.unsupported.reason: (1, weight)
    }
    for aggregate in (g.weighted_record_total, g.weighted_mean_record_total):
        with pytest.raises(g.FamilyTargetBlocked):
            aggregate([outcome])
