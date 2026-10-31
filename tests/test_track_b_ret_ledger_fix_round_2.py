"""R2 review regressions: statutory conformance on invented cases only.

No population, behavioral, or forecast claim. RS 02501.145-.150 require
coordinated charging when a beneficiary has entitlement on two records.
"""

from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from populace_dynamics.track_b import ret_ledger as r
from populace_dynamics.track_b.ret_grace import BenefitType as T
from populace_dynamics.track_b.ret_params import load_ret_parameters
from tests.test_track_b_ret_ledger_deductions import family_record
from tests.track_b_gross_benefit_support import ssa_params

YEAR = 2026
MONTHS = frozenset(range(1, 13))
PARAMS = load_ret_parameters()


def dual_record(pia=10, *, estimated=False, declared=None, own=True, excess=1):
    """The reviewer's PIA 10/MAX 15 and PIA 1000/MAX 1500 cases."""
    params = ssa_params()
    state = g.RecordState(
        g.FamilyKind.RETIREMENT,
        F(pia),
        F(3 * pia, 2),
        worker=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(pia)),
        eligibility_year=YEAR,
    )
    spouse = g.Beneficiary(
        "spouse",
        g.Role.SPOUSE,
        **(
            {
                "own_benefit": g.OwnBenefit(
                    g.OwnBenefitKind.OLD_AGE, F(pia, 10)
                ),
                "own_benefit_first": True,
            }
            if own
            else {}
        ),
    )
    members = (spouse, g.Beneficiary("child", g.Role.CHILD))
    baseline = g.family_benefits(
        state,
        members,
        payment_month=g.YearMonth(YEAR, 1),
        params=params,
        standalone=True,
    )
    baseline_rows = baseline.by_id()
    assert baseline.worker_benefit == pia
    assert baseline_rows["spouse"].original_benefit == F(pia, 2)
    assert baseline_rows["child"].original_benefit == F(pia, 2)
    assert baseline_rows["spouse"].auxiliary_payable == (
        F(3 * pia, 20) if own else F(pia, 4)
    )
    assert baseline_rows["child"].auxiliary_payable == (
        F(7 * pia, 20) if own else F(pia, 4)
    )
    rates = [("nh", F(pia), F(pia), T.RIB)] + [
        (
            row.beneficiary_id,
            row.auxiliary_payable,
            row.original_benefit,
            T.SPOUSE if row.beneficiary_id == "spouse" else T.CHILD,
        )
        for row in baseline.beneficiaries
    ]
    wages = (
        PARAMS.for_year(YEAR).lower_exempt_amount.value + 2 * excess
        if excess
        else 0
    )
    earnings = r.WorkEarnings((F(wages),) + (F(0),) * 11)
    people = []
    for key, rate, original, kind in rates:
        kwargs = {}
        if key == "spouse":
            kwargs["estimated_earnings" if estimated else "earnings"] = (
                earnings
            )
            if declared is not None:
                kwargs["two_record_entitlement"] = declared
        people.append(
            r.RETBeneficiary(
                key,
                (kind,) * 12,
                MONTHS,
                (rate,) * 12,
                (original,) * 12,
                **kwargs,
            )
        )
    return r.RecordYear(
        YEAR,
        "nh",
        beneficiaries=tuple(people),
        family_maximum_binding_months=MONTHS,
        family_months={
            1: r.RETFamilyMonth(
                state, members, params, {"spouse": "h", "child": "h"}
            )
        },
    )


@pytest.mark.parametrize("pia,excess", [(10, 1), (1000, 100)])
@pytest.mark.parametrize("estimated", [False, True])
@pytest.mark.parametrize("declared", [None, True])
def test_contextual_own_rib_requires_two_record_refusal(
    pia, excess, estimated, declared
):
    case = dual_record(
        pia, estimated=estimated, declared=declared, excess=excess
    )
    outcome = r.evaluate_ret("dual", 3, lambda: r.apply_ret_year(case, PARAMS))
    assert not outcome.supported
    assert (
        outcome.unsupported.reason
        is r.RETUnsupportedReason.TWO_RECORD_EARNINGS
    )
    assert outcome.unsupported.beneficiary_id == "spouse"
    denominator = g.count_family_outcomes([outcome])
    assert denominator.rows == denominator.unsupported_rows == 1
    assert denominator.weight == denominator.unsupported_weight == 3


@pytest.mark.parametrize("own,declared", [(True, False), (False, True)])
@pytest.mark.parametrize("estimated", [False, True])
@settings(max_examples=6, deadline=None, derandomize=True)
@example(scale=1, excess=0, g_refusal=True)
@example(scale=1, excess=1, g_refusal=False)
@given(
    scale=st.integers(1, 100),
    excess=st.integers(0, 2),
    g_refusal=st.booleans(),
)
def test_declared_two_record_contradiction_is_input_error(
    own, declared, estimated, scale, excess, g_refusal
):
    def contradictory_record():
        case = dual_record(
            10 * scale, own=own, estimated=estimated, excess=excess
        )
        people = tuple(
            (
                replace(person, two_record_entitlement=declared)
                if person.beneficiary_id == "spouse"
                else person
            )
            for person in case.beneficiaries
        )
        contexts = case.family_months
        if g_refusal:
            contexts = {
                month: replace(
                    context,
                    beneficiaries=tuple(
                        (
                            replace(
                                member,
                                conditions=frozenset(
                                    {
                                        g.BeneficiaryCondition.ENTITLED_ON_ANOTHER_RECORD
                                    }
                                ),
                            )
                            if member.beneficiary_id == "spouse"
                            else member
                        )
                        for member in context.beneficiaries
                    ),
                )
                for month, context in contexts.items()
            }
        return replace(case, beneficiaries=people, family_months=contexts)

    outcomes = []
    with pytest.raises(r.InvalidFamilyInput, match="two.record"):
        outcomes.append(
            r.evaluate_ret(
                "contradiction",
                1,
                lambda: r.apply_ret_year(contradictory_record(), PARAMS),
            )
        )
    assert outcomes == []
    assert g.count_family_outcomes(outcomes).rows == 0


@settings(max_examples=12, deadline=None, derandomize=True)
@given(pia=st.integers(1, 100).map(lambda n: 10 * n), estimated=st.booleans())
def test_two_record_derivation_is_order_independent(pia, estimated):
    case = dual_record(pia, estimated=estimated)
    reordered = replace(
        case,
        beneficiaries=tuple(reversed(case.beneficiaries)),
        family_months={
            month: replace(
                context,
                beneficiaries=tuple(reversed(context.beneficiaries)),
                households=dict(reversed(tuple(context.households.items()))),
            )
            for month, context in reversed(tuple(case.family_months.items()))
        },
    )
    outcomes = [
        r.evaluate_ret(
            "dual", 1, lambda case=case: r.apply_ret_year(case, PARAMS)
        )
        for case in (case, reordered)
    ]
    assert all(not outcome.supported for outcome in outcomes)
    assert all(
        outcome.unsupported.reason
        is r.RETUnsupportedReason.TWO_RECORD_EARNINGS
        for outcome in outcomes
    )
    assert all(
        outcome.unsupported.beneficiary_id == "spouse" for outcome in outcomes
    )


def test_contextual_own_rib_without_excess_remains_supported():
    result = r.apply_ret_year(dual_record(excess=0), PARAMS)
    assert all(
        row.deduction == row.provisional_deduction == 0
        for row in result.months
    )


@settings(max_examples=10, deadline=None, derandomize=True)
@example(excess=0)
@example(excess=1)
@example(excess=555)
@given(excess=st.integers(0, 600))
def test_r2_emits_only_positive_actual_deduction_events(excess):
    """Zero-excess people never become G deductees in either run."""
    original = g._family_benefits_after_deductions_validated
    calls = []

    def capture(state, beneficiaries, **kwargs):
        baseline = g._family_benefits_validated(
            state,
            beneficiaries,
            payment_month=kwargs["payment_month"],
            params=kwargs["params"],
            standalone=kwargs["standalone"],
        ).by_id()
        for key, event in kwargs["deductions"].items():
            assert event.reason is g.DeductionReason.OWN_EARNINGS_TEST
            assert event.payable < baseline[key].auxiliary_payable
            assert key == "c3"
        calls.append(kwargs["deductions"])
        return original(state, beneficiaries, **kwargs)

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            g, "_family_benefits_after_deductions_validated", capture
        )
        result = r.apply_ret_year(family_record(excess=excess), PARAMS)
    assert bool(calls) is bool(excess)
    if not excess:
        assert all(row.deduction == 0 for row in result.months)


def missing_parameter_case(year=2027):
    member = g.Beneficiary(
        "c",
        g.Role.CHILD,
        conditions=frozenset(
            {g.BeneficiaryCondition.ENTITLED_ON_ANOTHER_RECORD}
        ),
    )
    context = r.RETFamilyMonth(
        g.RecordState(
            g.FamilyKind.SURVIVOR, F(100), F(100), eligibility_year=year
        ),
        (member,),
        ssa_params(),
        {"c": "h"},
    )
    beneficiary = r.RETBeneficiary(
        "c",
        (T.CHILD,) * 12,
        frozenset({1}),
        (F(75),) + (F(0),) * 11,
        (F(75),) * 12,
    )
    return r.RecordYear(
        year,
        "nh",
        r.RecordKind.DECEASED,
        (beneficiary,),
        family_months={1: context},
    )


@pytest.mark.parametrize("fiscal_year", [False, True])
def test_missing_r1_parameter_precedes_held_g_refusal(fiscal_year):
    outcomes = []
    with pytest.raises(
        KeyError, match="RET parameters unavailable for year 2027"
    ):
        outcomes.append(
            r.evaluate_ret(
                "missing",
                1,
                lambda: r.apply_ret_year(
                    replace(missing_parameter_case(), fiscal_year=fiscal_year),
                    PARAMS,
                ),
            )
        )
    assert outcomes == []
    assert g.count_family_outcomes(outcomes).rows == 0


@settings(max_examples=10, deadline=None, derandomize=True)
@given(year=st.integers(2027, 2100), fiscal_year=st.booleans())
def test_unavailable_supported_r1_year_is_never_a_coverage_row(
    year, fiscal_year
):
    outcomes = []
    with pytest.raises(KeyError, match=f"year {year}"):
        outcomes.append(
            r.evaluate_ret(
                "missing",
                1,
                lambda: r.apply_ret_year(
                    replace(
                        missing_parameter_case(year), fiscal_year=fiscal_year
                    ),
                    PARAMS,
                ),
            )
        )
    assert g.count_family_outcomes(outcomes).rows == 0


def test_pre_2000_legal_refusal_does_not_request_an_r1_year():
    case = replace(missing_parameter_case(1999), family_months={})
    outcome = r.evaluate_ret(
        "historical", 1, lambda: r.apply_ret_year(case, PARAMS)
    )
    assert (
        outcome.unsupported.reason is r.RETUnsupportedReason.YEAR_BEFORE_2000
    )


def test_r2_statutory_order_describes_contextual_g_readjustment():
    note = (
        Path(__file__).parents[1] / "docs/design/track_b_r2_ret_ledger.md"
    ).read_text()
    step = note.split("5. **Other workers' charging.**", 1)[1].split(
        "6. **Protected months.**", 1
    )[0]
    assert "RETFamilyMonth" in step
    assert "deduction_readjustment_requires_family_context" in step
    assert "refuse the\n   record for part (b)" not in step
