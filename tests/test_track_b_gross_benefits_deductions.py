"""Statutory conformance for 203(a)(4) on invented and published cases.

No population, behavioral or forecast claim. GN 02603.050C-D fixes the
formula; GN 02603.060 and RS 02501.130/.160 supply payment examples.
"""

from dataclasses import fields, replace
from fractions import Fraction as F

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import source_text, ssa_params

PARAMS = ssa_params()
MONTH = g.YearMonth(2024, 1)


def survivor(pia=F("300.40"), maximum=F("548.40"), children=3, dual=False):
    state = g.RecordState(
        g.FamilyKind.SURVIVOR, pia, maximum, widow_drc_savings_clause=False
    )
    members = [g.Beneficiary("E", g.Role.MOTHER_FATHER)]
    members += [
        g.Beneficiary(
            f"C{i}",
            g.Role.CHILD,
            own_benefit=(
                g.OwnBenefit(g.OwnBenefitKind.DISABILITY, F(280))
                if dual and i == 2
                else None
            ),
        )
        for i in range(1, children + 1)
    ]
    return state, tuple(members)


def compute(state, members, deductions=None, households=None, **kwargs):
    return g.family_benefits_after_deductions(
        state,
        members,
        payment_month=MONTH,
        params=PARAMS,
        deductions={} if deductions is None else deductions,
        households={} if households is None else households,
        standalone=True,
        **kwargs,
    )


def amounts(result):
    return {
        row.beneficiary_id: row.auxiliary_payable
        for row in result.beneficiaries
    }


@pytest.mark.parametrize(
    "children,deductee,payable,expected",
    [
        (
            3,
            "E",
            F(0),
            {
                "E": F(0),
                "C1": F("182.80"),
                "C2": F("182.80"),
                "C3": F("182.80"),
            },
        ),
        (2, "C2", F(0), {"E": F("225.30"), "C1": F("225.30"), "C2": F(0)}),
        (
            3,
            "E",
            F("37.20"),
            {
                "E": F("37.20"),
                "C1": F("170.40"),
                "C2": F("170.40"),
                "C3": F("170.40"),
            },
        ),
    ],
)
def test_gn_02603_060_permanent_examples(
    children, deductee, payable, expected
):
    state, members = survivor(children=children)
    result = compute(
        state,
        members,
        {
            deductee: g.BenefitDeduction(
                g.DeductionReason.OWN_EARNINGS_TEST, payable
            )
        },
    )
    assert amounts(result) == expected
    if children == 2:
        narrative = "That is $548.40 divided by 2 individuals = 225.30."
        assert narrative in source_text("poms_gn_02603_060")
        # A.2's narrative omits the OB cap; its displayed formula settles
        # the actual quotient and cap separately.
        assert F("548.40") / 2 == F("274.20")
        assert min(F("274.20"), F("225.30")) == F("225.30")
    assert {
        r.beneficiary_id: r.whole_dollar_auxiliary
        for r in result.beneficiaries
    } == {k: int(v) for k, v in expected.items()}


@pytest.mark.parametrize(
    "dual,expected",
    [
        (
            False,
            {
                "E": F(0),
                "C1": F("137.10"),
                "C2": F("182.80"),
                "C3": F("182.80"),
            },
        ),
        (True, {"E": F(0), "C1": F("182.80"), "C2": F(0), "C3": F("225.30")}),
    ],
)
def test_gn_02603_060_temporary_examples(dual, expected):
    state, members = survivor(dual=dual)
    event = g.BenefitDeduction(
        g.DeductionReason.OWN_EARNINGS_TEST, permanent=False
    )
    households = {"E": "one", "C1": "two", "C2": "one", "C3": "one"}
    assert (
        amounts(compute(state, members, {"E": event}, households)) == expected
    )
    permanent = compute(
        state, members, {"E": replace(event, permanent=True)}, households
    )
    assert amounts(permanent)["C1"] == F("225.30" if dual else "182.80")


@pytest.mark.parametrize(
    "payable,permanent,expected",
    [
        (F(0), False, {"E": F(99), "C1": F(99), "C2": F(132), "C3": F(0)}),
        (F(39), False, {"E": F(99), "C1": F(99), "C2": F(119), "C3": F(39)}),
        (F(0), True, {"E": F(132), "C1": F(132), "C2": F(132), "C3": F(0)}),
        (F(39), True, {"E": F(119), "C1": F(119), "C2": F(119), "C3": F(39)}),
    ],
)
def test_rs_02501_160_separate_households(payable, permanent, expected):
    state, members = survivor(F("213.10"), F(396))
    event = g.BenefitDeduction(
        g.DeductionReason.OWN_EARNINGS_TEST, payable, permanent
    )
    households = {"E": "one", "C1": "one", "C2": "two", "C3": "two"}
    result = compute(state, members, {"C3": event}, households)
    assert amounts(result) == expected
    # The undated source OB rounds upward; modern G dime floors. Equal
    # shares make every published actual payment identical without an override.
    assert result.beneficiaries[0].original_benefit == F("159.80")
    assert "$159.90" in source_text("poms_rs_02501_160")


def test_rs_02501_130_no_child_in_care():
    assert "Their spouse (age 55)" in source_text("poms_rs_02501_130")
    state = g.RecordState(
        g.FamilyKind.RETIREMENT,
        F("242.30"),
        F("409.40"),
        worker=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F("242.30")),
    )
    members = (
        g.Beneficiary("B", g.Role.SPOUSE_CHILD_IN_CARE),
        g.Beneficiary("C1", g.Role.CHILD),
        g.Beneficiary("C2", g.Role.CHILD),
    )
    event = g.BenefitDeduction(
        g.DeductionReason.NO_CHILD_IN_CARE, under_full_retirement_age=True
    )
    result = compute(state, members, {"B": event})
    assert amounts(result) == {"B": F(0), "C1": F("83.50"), "C2": F("83.50")}
    assert result.beneficiaries[0].original_benefit == F("121.10")
    assert "$121.20" in source_text("poms_rs_02501_130")


@given(pia=st.integers(1, 20000), count=st.integers(1, 5), dual=st.booleans())
@settings(max_examples=50, deadline=None)
def test_no_deductions_is_exact_family_and_household_differential(
    pia, count, dual
):
    state, members = survivor(F(pia), F(pia * 3, 2), count, dual)
    old = g.family_benefits(
        state, members, payment_month=MONTH, params=PARAMS, standalone=True
    )
    assert compute(state, members) == old
    records = {"record": g.HouseholdRecord("worker", state, members)}
    assert g.household_benefits_after_deductions(
        records,
        payment_month=MONTH,
        params=PARAMS,
        deductions={},
        households={},
    ) == g.household_benefits(records, payment_month=MONTH, params=PARAMS)


@given(
    pia=st.integers(2, 20000),
    count=st.integers(2, 6),
    partial=st.integers(0, 100),
    temporary=st.booleans(),
)
@settings(max_examples=80, deadline=None)
def test_formula_bounds_monotonicity_households_order_and_determinism(
    pia, count, partial, temporary
):
    state, members = survivor(F(pia), F(pia * 3, 2), count)
    old = compute(state, members)
    before = old.by_id()
    payable = g.floor_dime(before["E"].auxiliary_payable * partial / 100)
    event = g.BenefitDeduction(
        g.DeductionReason.OWN_EARNINGS_TEST, payable, not temporary
    )
    households = {
        b.beneficiary_id: ("elsewhere" if b.beneficiary_id == "C1" else "home")
        for b in members
    }
    if payable == before["E"].auxiliary_payable:
        with pytest.raises(g.InvalidFamilyInput):
            compute(state, members, {"E": event}, households)
        return
    result = compute(state, members, {"E": event}, households)
    again = compute(
        state,
        tuple(reversed(members)),
        {"E": event},
        dict(reversed(tuple(households.items()))),
    )
    assert amounts(result) == amounts(again)
    assert compute(state, members, {"E": event}, households) == result
    assert result.subject_total <= state.family_maximum
    for row in result.beneficiaries:
        assert row.family_maximum_rate <= row.original_benefit
        if row.beneficiary_id == "E":
            assert row.auxiliary_payable == payable
            continue
        assert (
            row.family_maximum_rate
            >= before[row.beneficiary_id].family_maximum_rate
        )
        if temporary and row.beneficiary_id == "C1":
            assert row.auxiliary_payable == before["C1"].auxiliary_payable
        else:
            denominator = sum(
                b.original_benefit
                for b in old.beneficiaries
                if b.beneficiary_id != "E"
            )
            expected = g.floor_dime(
                min(
                    row.original_benefit,
                    row.original_benefit
                    * (state.family_maximum - payable)
                    / denominator,
                )
            )
            assert row.family_maximum_rate == expected


@pytest.mark.parametrize(
    "reason,expected",
    [
        (
            g.DeductionReason.WORKERS_COMPENSATION,
            g.UnsupportedReason.WORKERS_COMPENSATION_OFFSET,
        ),
        (
            g.DeductionReason.PRISONER_SUSPENSION,
            g.UnsupportedReason.PRISONER_SUSPENSION,
        ),
        (
            g.DeductionReason.DRUG_ADDICTION_SUSPENSION,
            g.UnsupportedReason.DRUG_ADDICTION_SUSPENSION,
        ),
        (
            g.DeductionReason.FOREIGN_WORK,
            g.UnsupportedReason.FOREIGN_WORK_DEDUCTION,
        ),
        (g.DeductionReason.PENALTY, g.UnsupportedReason.PENALTY_DEDUCTION),
        (g.DeductionReason.MARITIME, g.UnsupportedReason.MARITIME_DEDUCTION),
        (
            g.DeductionReason.ELECTION_CERTIFICATE_SUSPENSION,
            g.UnsupportedReason.ELECTION_CERTIFICATE_SUSPENSION,
        ),
    ],
)
def test_unsupported_deductions_keep_named_denominator(reason, expected):
    state, members = survivor()
    outcome = g.evaluate_family(
        "deduction",
        1,
        lambda: compute(state, members, {"E": g.BenefitDeduction(reason)}),
    )
    assert outcome.unsupported.reason is expected
    assert g.count_family_outcomes((outcome,)).unsupported_rows == 1
    with pytest.raises(g.InvalidFamilyInput):
        compute(state, members, {"missing": g.BenefitDeduction(reason)})


def test_nh_partial_reservation_cannot_redistribute_original_rounding_slack():
    state = g.RecordState(
        g.FamilyKind.RETIREMENT,
        F(400),
        F(600),
        worker=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(400)),
    )
    members = tuple(g.Beneficiary(f"C{i}", g.Role.CHILD) for i in range(3))
    nh = dict.fromkeys(("C0", "C1", "C2"), F("46.64"))
    result = compute(
        state,
        members,
        {
            "C0": g.BenefitDeduction(
                g.DeductionReason.OWN_EARNINGS_TEST, F("9.96")
            )
        },
        worker_deductions=nh,
    )
    assert amounts(result) == {
        "C0": F("9.96"),
        "C1": F("24.90"),
        "C2": F("24.90"),
    }
    assert amounts(result)["C1"] + amounts(result)["C2"] - F("19.96") * 2 <= 10


def test_fields_remain_sealed_and_exact():
    state, members = survivor()
    result = compute(
        state,
        members,
        {
            "E": g.BenefitDeduction(
                g.DeductionReason.OWN_EARNINGS_TEST, F(1, 3)
            )
        },
    )
    assert amounts(result)["E"] == F(1, 3)
    with pytest.raises(g.InvalidFamilyInput):
        g.FamilyBenefits(
            **{
                item.name: getattr(result, item.name)
                for item in fields(result)
            }
        )


@pytest.mark.parametrize(
    "source,figures",
    [
        (
            "poms_gn_02603_060",
            (
                "300.40",
                "548.40",
                "225.30",
                "137.10",
                "182.80",
                "274.20",
                "37.20",
                "170.40",
                "280.00",
            ),
        ),
        (
            "poms_rs_02501_130",
            ("242.30", "409.40", "121.20", "55.70", "83.50"),
        ),
        (
            "poms_rs_02501_160",
            ("159.90", "213.10", "396", "99", "132", "119", "39"),
        ),
    ],
)
def test_worked_example_figures_are_quoted_from_the_captures(source, figures):
    text = source_text(source)
    for figure in figures:
        assert figure in text


def test_temporary_partial_reading_is_explicit_in_captures():
    assert (
        "there are no partial deductions for temporary work deductions"
        in source_text("poms_gn_02603_050")
    )
    assert "C3 $ 39 C2 $119" in source_text("poms_rs_02501_160")
    assert "C2 can receive the extra $20 for June immediately" in source_text(
        "poms_rs_02501_160"
    )


def test_nh_age_interaction_is_named_refusal():
    for quote in (
        "Total amount of work deductions to be imposed against auxiliaries "
        "or survivors due to the number holder's work",
        "Age reduction amount for all workers or deductees",
    ):
        assert quote in source_text("poms_gn_02603_050")
    assert (
        "The partial benefits of other auxiliaries cannot be readjusted "
        "except to the extent to which we charge the auxiliary's excess "
        "earnings against the benefits to which the auxiliary otherwise "
        "was eligible."
    ) in source_text("poms_rs_02501_155")
    state = g.RecordState(
        g.FamilyKind.RETIREMENT,
        F(400),
        F(600),
        worker=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(400)),
    )
    members = (
        g.Beneficiary("B", g.Role.SPOUSE, reduction_months=12),
        g.Beneficiary("C1", g.Role.CHILD),
        g.Beneficiary("C2", g.Role.CHILD),
    )
    with pytest.raises(g.FamilyConfigurationUnsupported) as error:
        compute(
            state,
            members,
            {"C1": g.BenefitDeduction(g.DeductionReason.OWN_EARNINGS_TEST)},
            worker_deductions={"C1": F(1)},
        )
    assert (
        error.value.reason
        is g.UnsupportedReason.DEDUCTION_AGE_WORK_INTERACTION
    )


def test_all_dual_beneficiaries_do_not_gain_from_another_deduction():
    state = g.RecordState(
        g.FamilyKind.SURVIVOR, F(300), F(450), widow_drc_savings_clause=False
    )
    members = tuple(
        g.Beneficiary(
            f"C{i}",
            g.Role.CHILD,
            own_benefit=g.OwnBenefit(g.OwnBenefitKind.DISABILITY, F(200)),
        )
        for i in range(3)
    )
    result = compute(state, members)
    assert amounts(result) == dict.fromkeys(("C0", "C1", "C2"), F(0))
    # R2 never emits an own-work event for zero actual withholding.
    # A zero-rate dual beneficiary cannot have a further earnings deduction.
    with pytest.raises(g.InvalidFamilyInput):
        compute(
            state,
            members,
            {"C0": g.BenefitDeduction(g.DeductionReason.OWN_EARNINGS_TEST)},
        )


@given(scale=st.integers(1, 20))
@example(scale=1)
@settings(max_examples=12, deadline=None)
def test_single_full_permanent_exception_disregards_age_reduction(scale):
    state = g.RecordState(
        g.FamilyKind.RETIREMENT,
        F(400),
        F(650),
        worker=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(400)),
    )
    members = (
        g.Beneficiary("B", g.Role.SPOUSE, reduction_months=36),
        g.Beneficiary("C1", g.Role.CHILD),
        g.Beneficiary("C2", g.Role.CHILD),
    )
    result = compute(
        state,
        members,
        {"B": g.BenefitDeduction(g.DeductionReason.OWN_EARNINGS_TEST)},
    )
    assert amounts(result) == {"B": F(0), "C1": F(125), "C2": F(125)}
    assert (
        "disregard that beneficiary when distributing the family maximum"
        in source_text("poms_gn_02603_050")
    )
    # Literal C reserves B age reduction20.90 and gives114.50, but A.1
    # explicitly calls this a full-permanent exception to that formula.
    assert g.floor_dime((F(250) - F("20.90")) / 2) == F("114.50")
    # A.1 applies only while there is no other deduction. Entering C by
    # adding a second worker restores the age reserve and can LOWER the
    # remaining children's payments: absolute monotonicity is not a rule.
    state = g.RecordState(
        g.FamilyKind.RETIREMENT,
        F(48 * scale),
        F(78 * scale),
        worker=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(48 * scale)),
    )
    members = (
        g.Beneficiary("B", g.Role.SPOUSE, reduction_months=60),
    ) + tuple(g.Beneficiary(f"C{i}", g.Role.CHILD) for i in range(1, 4))
    baseline = compute(state, members)
    events = {"B": g.BenefitDeduction(g.DeductionReason.OWN_EARNINGS_TEST)}
    single = compute(state, members, events)
    child_payable = baseline.by_id()["C1"].auxiliary_payable - F("0.10")
    multiple = compute(
        state,
        members,
        {
            **events,
            "C1": g.BenefitDeduction(
                g.DeductionReason.OWN_EARNINGS_TEST, child_payable
            ),
        },
    )
    spouse = baseline.by_id()["B"]
    age_reserve = spouse.family_maximum_rate - spouse.age_adjusted_rate
    expected = g.floor_dime((F(30 * scale) - age_reserve - child_payable) / 2)
    assert amounts(single)["C2"] == amounts(single)["C3"] == 10 * scale
    assert amounts(multiple)["C2"] == amounts(multiple)["C3"] == expected
    assert expected < amounts(single)["C2"]
    if scale == 1:
        assert child_payable == F("7.40")
        assert age_reserve == F("2.70")
        assert expected == F("9.90")
        # Extending A.1 despite the second worker would instead pay11.30.
        assert g.floor_dime((F(30) - child_payable) / 2) == F("11.30")
    text = source_text("poms_gn_02603_050")
    assert "and no other deduction is involved for any beneficiary" in text
    assert "Age reduction amount for all workers or deductees" in text


@pytest.mark.parametrize("household", (False, True))
@given(excess=st.integers(1, 10000))
@settings(max_examples=10, deadline=None)
def test_impossible_payable_precedes_statutory_refusal(household, excess):
    state, members = survivor()
    state = replace(
        state, conditions={g.RecordCondition.WORKERS_COMPENSATION_OFFSET}
    )
    event = g.BenefitDeduction(
        g.DeductionReason.OWN_EARNINGS_TEST, F("225.30") + excess
    )
    rows = []
    with pytest.raises(g.InvalidFamilyInput):
        if household:
            rows.append(
                g.evaluate_family(
                    "invalid",
                    1,
                    lambda: g.household_benefits_after_deductions(
                        {
                            "record": g.HouseholdRecord(
                                "worker", state, members
                            )
                        },
                        payment_month=MONTH,
                        params=PARAMS,
                        deductions={"E": event},
                        households={},
                    ),
                )
            )
        else:
            rows.append(
                g.evaluate_family(
                    "invalid", 1, lambda: compute(state, members, {"E": event})
                )
            )
    assert g.count_family_outcomes(rows).rows == 0
