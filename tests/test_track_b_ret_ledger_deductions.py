"""R2 part (b), statutory conformance on invented/captured examples only.

No population, behavioral, or forecast claim. GN 02603.050 and RS
02501.155-.160 govern the monthly readjustment and household timing.
"""

from dataclasses import fields, replace
from datetime import date
from fractions import Fraction as F

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import arf as a
from populace_dynamics.track_b import gross_benefits as g
from populace_dynamics.track_b import ret_ledger as r
from populace_dynamics.track_b.ret_grace import BenefitType as T
from populace_dynamics.track_b.ret_params import load_ret_parameters
from tests.track_b_gross_benefit_support import ssa_params
from tests.track_b_ret_ledger_support import source_text

YEAR = 2026
MONTHS = frozenset(range(1, 13))
PARAMS = load_ret_parameters()


def family_record(*, excess=555, separate=False, other_excess=0, nh_excess=0):
    """Published .160 family, or an invented living-worker interaction."""
    params = ssa_params()
    if nh_excess:
        state = g.RecordState(
            g.FamilyKind.RETIREMENT,
            F(600),
            F(900),
            worker=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(600)),
            eligibility_year=YEAR,
        )
        members = tuple(
            g.Beneficiary(k, g.Role.CHILD) for k in ("c1", "c2", "c3")
        )
    else:
        state = g.RecordState(
            g.FamilyKind.SURVIVOR,
            F("213.10"),
            F(396),
            eligibility_year=YEAR,
        )
        members = (g.Beneficiary("e", g.Role.MOTHER_FATHER),) + tuple(
            g.Beneficiary(k, g.Role.CHILD) for k in ("c1", "c2", "c3")
        )
    family = g.family_benefits(
        state,
        members,
        payment_month=g.YearMonth(YEAR, 1),
        params=params,
        standalone=True,
    )
    households = {
        b.beneficiary_id: (
            "other"
            if separate and b.beneficiary_id in ("e", "c1")
            else "worker"
        )
        for b in members
    }
    context = r.RETFamilyMonth(state, members, params, households)
    own_excess = {"c3": excess, "c1": other_excess, "nh": nh_excess}
    people = []
    rates = [
        (b.beneficiary_id, b.auxiliary_payable, b.original_benefit)
        for b in family.beneficiaries
    ]
    if nh_excess:
        rates.append(("nh", family.worker_benefit, family.pia))
    for key, rate, original in rates:
        annual = own_excess.get(key, 0)
        wages = (
            PARAMS.for_year(YEAR).lower_exempt_amount.value + 2 * annual
            if annual
            else 0
        )
        people.append(
            r.RETBeneficiary(
                key,
                (
                    (
                        T.RIB
                        if key == "nh"
                        else T.MOTHER_FATHER if key == "e" else T.CHILD
                    ),
                )
                * 12,
                MONTHS,
                (rate,) * 12,
                (original,) * 12,
                earnings=r.WorkEarnings((F(wages),) + (F(0),) * 11),
            )
        )
    return r.RecordYear(
        YEAR,
        "nh",
        r.RecordKind.RETIREMENT if nh_excess else r.RecordKind.DECEASED,
        tuple(people),
        family_maximum_binding_months=MONTHS,
        family_months={month: context for month in MONTHS},
    )


def month(result, key, number=1):
    return result.for_beneficiary(key)[number - 1]


def payload(value):
    """All declared fields, without private process-specific seal metadata."""
    return {field.name: getattr(value, field.name) for field in fields(value)}


def fixed_nh_record(excess, *, dual):
    """NH partial charges on a fixed Parisi/outside-maximum auxiliary."""
    params = ssa_params()
    state = g.RecordState(
        g.FamilyKind.RETIREMENT,
        F(600),
        F(900),
        worker=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(600)),
        eligibility_year=YEAR,
    )
    fixed = (
        g.Beneficiary(
            "fixed",
            g.Role.SPOUSE,
            own_benefit=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(10)),
            own_benefit_first=True,
        )
        if dual
        else g.Beneficiary(
            "fixed",
            g.Role.DIVORCED_SPOUSE,
            child_in_care=False,
            first_entitlement_child_in_care=False,
        )
    )
    members = (fixed,) + tuple(
        g.Beneficiary(f"c{n}", g.Role.CHILD)
        for n in range(1, 3 if dual else 4)
    )
    baseline = g.family_benefits(
        state,
        members,
        payment_month=g.YearMonth(YEAR, 1),
        params=params,
        standalone=True,
    )
    rates = [("nh", F(600), F(600), T.RIB)] + [
        (
            row.beneficiary_id,
            row.auxiliary_payable,
            row.original_benefit,
            (
                T.SPOUSE
                if dual and row.beneficiary_id == "fixed"
                else (
                    T.DIVORCED_SPOUSE
                    if row.beneficiary_id == "fixed"
                    else T.CHILD
                )
            ),
        )
        for row in baseline.beneficiaries
    ]
    people = []
    for key, rate, original, kind in rates:
        deduction = 600 if key == "nh" else excess if key == "c1" else 0
        annual = (
            PARAMS.for_year(YEAR).lower_exempt_amount.value + 2 * deduction
            if deduction
            else 0
        )
        people.append(
            r.RETBeneficiary(
                key,
                (kind,) * 12,
                MONTHS,
                (rate,) * 12,
                (original,) * 12,
                earnings=r.WorkEarnings((F(annual),) + (F(0),) * 11),
            )
        )
    context = r.RETFamilyMonth(
        state, members, params, {b.beneficiary_id: "one" for b in members}
    )
    return r.RecordYear(
        YEAR,
        "nh",
        beneficiaries=tuple(people),
        family_maximum_binding_months=MONTHS,
        family_months={1: context, 2: context},
    )


def test_rs_02501_160_permanent_full_and_partial_months():
    result = r.apply_ret_year(family_record(), PARAMS)
    assert [month(result, "c3", n).net_due for n in range(1, 8)] == [0] * 5 + [
        39,
        99,
    ]
    assert (
        sum(row.own_deduction for row in result.for_beneficiary("c3")) == 555
    )
    for key in ("e", "c1", "c2"):
        assert [month(result, key, n).net_due for n in range(1, 8)] == [
            132
        ] * 5 + [119, 99]
        assert month(result, key, 6).payment == 119
        assert result.crediting_months[key] == frozenset()
    assert result.crediting_months["c3"] == frozenset(range(1, 7))


def test_rs_02501_160_separate_household_increases_wait_for_final_deduction():
    result = r.apply_ret_year(family_record(separate=True), PARAMS)
    for key in ("e", "c1"):
        row = month(result, key)
        assert type(row) is r.RedistributedBeneficiaryMonth
        assert row.gross == row.net_due == 132
        assert row.provisional_gross == row.provisional_net == 99
        assert row.deduction == row.provisional_deduction == 0
        assert result.reconciliation[key] == 5 * 33 + 20
    assert month(result, "c2").provisional_net == 132
    # R2 retains full-month estimated suspension, GN .050D.2. The .160
    # partial June example is a different operational reading covered by G.
    assert month(result, "c3", 6).provisional_net == 0
    assert month(result, "c2", 6).provisional_net == 132


def test_rs_02501_155_multiple_workers_charge_before_redistribution():
    result = r.apply_ret_year(
        family_record(excess=100, other_excess=150), PARAMS
    )
    assert month(result, "c3").own_deduction == 99
    assert month(result, "c1").own_deduction == 99
    assert month(result, "e").net_due == F("159.80")
    assert month(result, "c3", 2).net_due == 98
    assert month(result, "c1", 2).net_due == 48
    assert month(result, "e", 2).net_due == 125
    assert month(result, "c2", 2).net_due == 125


@settings(max_examples=12, deadline=None)
@example(excess=30)
@given(excess=st.integers(1, 59))
def test_rs_02501_155_nh_partial_month_preserves_nh_deductions(excess):
    result = r.apply_ret_year(
        family_record(excess=excess, nh_excess=600), PARAMS
    )
    assert month(result, "nh").net_due == 120
    assert month(result, "c3").net_due == 60 - excess
    assert month(result, "c3").nh_deduction == 40
    assert month(result, "c3").own_deduction == excess
    for key in ("c1", "c2"):
        assert month(result, key).net_due == 60 + F(excess, 2)
        assert month(result, key).nh_deduction == 40
        assert month(result, key).own_deduction == 0
        assert month(result, key).gross == 100 + F(excess, 2)
    dual = r.apply_ret_year(fixed_nh_record(excess, dual=True), PARAMS)
    assert month(dual, "fixed").net_due == 60
    assert month(dual, "fixed").nh_deduction == 30
    assert month(dual, "fixed").gross == 90
    assert month(dual, "c1").net_due == 60 - excess
    assert month(dual, "c2").net_due == 60 + excess
    outside = r.apply_ret_year(fixed_nh_record(excess, dual=False), PARAMS)
    assert month(outside, "fixed").net_due == 100
    assert month(outside, "fixed").nh_deduction == 200
    assert month(outside, "fixed").gross == 300
    assert month(outside, "c1").net_due == 100 - excess
    for key in ("c2", "c3"):
        assert month(outside, key).net_due == 100 + F(excess, 2)
    case = fixed_nh_record(excess, dual=False)
    own_work = next(
        b.earnings for b in case.beneficiaries if b.beneficiary_id == "c1"
    )
    case = replace(
        case,
        beneficiaries=tuple(
            (
                replace(
                    b,
                    earnings=(
                        own_work
                        if b.beneficiary_id == "fixed"
                        else r.WorkEarnings()
                    ),
                )
                if b.beneficiary_id in ("fixed", "c1")
                else b
            )
            for b in case.beneficiaries
        ),
    )
    outside_worker = r.apply_ret_year(case, PARAMS)
    assert month(outside_worker, "fixed").net_due == 100 - excess
    assert month(outside_worker, "fixed").nh_deduction == 200
    for key in ("c1", "c2", "c3"):
        assert month(outside_worker, key).net_due == 100


def test_readjusted_deductions_flow_to_r3_without_household_delay_credits():
    params = ssa_params()
    state = g.RecordState(
        g.FamilyKind.SURVIVOR, F(1000), F(1500), eligibility_year=YEAR
    )
    members = (
        g.Beneficiary(
            "widow",
            g.Role.WIDOW,
            reduction_months=60,
            reduction_period_months=84,
            child_in_care=False,
        ),
        g.Beneficiary(
            "cdb",
            g.Role.CHILD,
            own_benefit=g.OwnBenefit(g.OwnBenefitKind.DISABILITY, F(650)),
        ),
    )
    family = g.family_benefits(
        state,
        members,
        payment_month=g.YearMonth(YEAR, 1),
        params=params,
        standalone=True,
    )
    rows = {row.beneficiary_id: row for row in family.beneficiaries}
    annual = PARAMS.for_year(YEAR).lower_exempt_amount.value + 200
    people = tuple(
        r.RETBeneficiary(
            key,
            (T.WIDOW if key == "widow" else T.CDB,) * 12,
            MONTHS,
            (rows[key].auxiliary_payable,) * 12,
            (rows[key].original_benefit,) * 12,
            earnings=r.WorkEarnings(
                (F(annual if key == "widow" else 0),) + (F(0),) * 11
            ),
        )
        for key in ("widow", "cdb")
    )
    context = r.RETFamilyMonth(
        state, members, params, {"widow": "one", "cdb": "two"}
    )
    record = r.RecordYear(
        YEAR,
        "nh",
        r.RecordKind.DECEASED,
        people,
        family_maximum_binding_months=MONTHS,
        family_months={m: context for m in MONTHS},
    )
    result = r.apply_ret_year(record, PARAMS)
    credits = frozenset(
        g.YearMonth(YEAR, m) for m in result.crediting_months["widow"]
    )
    claim = a.ARFClaim(
        a.ARFBenefitKind.WIDOW,
        date(1962, 1, 2),
        g.YearMonth(2024, 1),
        F(1000),
        partial_work_deduction_months=credits,
    )
    adjusted = a.apply_arf(
        claim, payment_month=g.YearMonth(2029, 1), params=params
    )
    assert (
        adjusted.crediting_months
        == credits
        == frozenset({g.YearMonth(YEAR, 1)})
    )
    assert adjusted.adjusted_reduction_months == 59
    assert adjusted.benefit == F("799.80")
    assert result.crediting_months["cdb"] == frozenset()


@settings(max_examples=30, deadline=None)
@given(
    excess=st.integers(1, 1600),
    other_excess=st.integers(0, 500),
    separate=st.booleans(),
)
def test_property_readjustment_conserves_deductions_and_preserves_order(
    excess, other_excess, separate
):
    case = family_record(
        excess=excess, other_excess=other_excess, separate=separate
    )
    result = r.apply_ret_year(case, PARAMS)
    reverse = r.apply_ret_year(
        replace(case, beneficiaries=tuple(reversed(case.beneficiaries))),
        PARAMS,
    )
    repeated = r.apply_ret_year(case, PARAMS)
    assert [payload(v) for v in result.months] == [
        payload(v) for v in reverse.months
    ]
    assert [payload(v) for v in result.months] == [
        payload(v) for v in repeated.months
    ]
    assert sum(v.deduction for v in result.months) == sum(
        v.charged for v in result.workers
    )
    assert sum(v.provisional_deduction for v in result.months) == sum(
        v.provisional_withheld for v in result.workers
    )
    workers = {row.beneficiary_id: row for row in result.workers}
    assert workers["c3"].charged == min(excess, 12 * 99)
    assert workers["c1"].charged == min(other_excess, 12 * 99)
    for n in range(1, 13):
        assert (
            sum(month(result, k, n).net_due for k in ("e", "c1", "c2", "c3"))
            <= 396
        )
        for key in ("e", "c1", "c2"):
            row = month(result, key, n)
            if not row.own_deduction:
                assert 99 <= row.net_due <= F("159.80")
                assert row.deduction == 0
            if (
                separate
                and key != "c2"
                and not month(result, "c1", n).provisional_deduction
            ):
                assert row.provisional_net == 99
        row = month(result, "c3", n)
        assert (n in result.crediting_months["c3"]) == (row.own_deduction > 0)


@settings(max_examples=20, deadline=None)
@given(separate=st.booleans(), amount=st.integers(0, 20))
def test_property_unused_g_context_preserves_original_result_fields(
    separate, amount
):
    case = family_record(excess=0, separate=separate)
    # Earnings below the exempt amount create no deduction event.
    people = tuple(
        replace(b, earnings=r.WorkEarnings((F(amount),) * 12))
        for b in case.beneficiaries
    )
    with_context = r.apply_ret_year(
        replace(case, beneficiaries=people), PARAMS
    )
    without_context = r.apply_ret_year(
        replace(case, beneficiaries=people, family_months={}), PARAMS
    )
    assert all(type(row) is r.BeneficiaryMonth for row in with_context.months)
    assert [payload(row) for row in with_context.months] == [
        payload(row) for row in without_context.months
    ]


def test_family_context_invalidity_precedes_record_refusal():
    case = family_record(excess=100)
    b = case.beneficiaries[0]
    case = replace(
        case,
        fiscal_year=True,
        beneficiaries=(replace(b, gross_rates=(F(1),) * 12),)
        + case.beneficiaries[1:],
    )
    with pytest.raises(g.InvalidFamilyInput, match="does not match"):
        r.apply_ret_year(case, PARAMS)

    living = fixed_nh_record(30, dual=True)
    no_nh_entitlement = replace(
        living,
        fiscal_year=True,
        beneficiaries=tuple(
            (
                replace(
                    b, entitled_months=frozenset(), gross_rates=(F(0),) * 12
                )
                if b.beneficiary_id == "nh"
                else b
            )
            for b in living.beneficiaries
        ),
    )
    with pytest.raises(g.InvalidFamilyInput, match="NH entitlement"):
        r.apply_ret_year(no_nh_entitlement, PARAMS)

    context = living.family_months[1]
    not_entitled = replace(
        context.beneficiaries[0],
        own_benefit=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(300)),
    )
    context = replace(
        context, beneficiaries=(not_entitled,) + context.beneficiaries[1:]
    )
    baseline = g.family_benefits(
        context.state,
        context.beneficiaries,
        payment_month=g.YearMonth(YEAR, 1),
        params=context.params,
        standalone=True,
    )
    rows = {row.beneficiary_id: row for row in baseline.beneficiaries}
    assert rows["fixed"].entitled is False
    declared_entitled = replace(
        living,
        fiscal_year=True,
        family_months={1: context, 2: context},
        beneficiaries=tuple(
            (
                replace(
                    b,
                    gross_rates=(rows[b.beneficiary_id].auxiliary_payable,)
                    * 12,
                    original_rates=(rows[b.beneficiary_id].original_benefit,)
                    * 12,
                )
                if b.beneficiary_id != "nh"
                else b
            )
            for b in living.beneficiaries
        ),
    )
    with pytest.raises(g.InvalidFamilyInput, match="auxiliary entitlement"):
        r.apply_ret_year(declared_entitled, PARAMS)


def test_later_family_input_error_precedes_earlier_g_coverage_refusal():
    case = family_record(excess=100)
    contexts = dict(case.family_months)
    context = contexts[1]
    child = replace(
        context.beneficiaries[-1],
        conditions=frozenset(
            {g.BeneficiaryCondition.ENTITLED_ON_ANOTHER_RECORD}
        ),
    )
    contexts[1] = replace(
        context, beneficiaries=context.beneficiaries[:-1] + (child,)
    )
    person = case.beneficiaries[0]
    person = replace(person, gross_rates=person.gross_rates[:11] + (F(1),))
    case = replace(
        case,
        family_months=contexts,
        beneficiaries=(person,) + case.beneficiaries[1:],
    )
    with pytest.raises(g.InvalidFamilyInput, match="does not match"):
        r.apply_ret_year(case, PARAMS)


@pytest.mark.parametrize(
    "field,value",
    [
        ("households", {"e": "only"}),
        ("standalone", 1),
        ("beneficiaries", frozenset()),
    ],
)
def test_family_context_schema_rejects_invalid_fields(field, value):
    context = family_record().family_months[1]
    with pytest.raises(g.InvalidFamilyInput):
        replace(context, **{field: value})


@pytest.mark.parametrize(
    "field",
    ("gross", "provisional_gross", "deduction", "provisional_deduction"),
)
def test_redistributed_month_tampering_cannot_enter_ret_denominator(field):
    result = r.apply_ret_year(family_record(separate=True), PARAMS)
    row = next(
        row
        for row in result.months
        if type(row) is r.RedistributedBeneficiaryMonth
    )
    object.__setattr__(row, field, F(-1))
    with pytest.raises(g.InvalidFamilyInput):
        r.evaluate_ret("altered", 1, lambda: result)


def test_captured_original_rounding_and_worked_payment_figures_are_explicit():
    text = source_text("poms_rs_02501_160")
    for figure in (
        "$159.90",
        "$213.10",
        "$396",
        "$99",
        "$555",
        "$60",
        "$132",
        "$119",
        "$33",
        "$20",
        "$ 39",
    ):
        assert figure in text
    # Modern floor differs from this undated example's upward-rounded
    # original benefit. Equal shares make every published payment identical.
    case = family_record()
    assert all(b.original_rates[0] == F("159.80") for b in case.beneficiaries)
