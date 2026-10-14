"""R2 ledger boundaries and invented cases: statutory conformance only.

Amounts are independently invented arithmetic, except the POMS .110 $93
apportionment rounding regression. Its figures, the other published worked
examples, and capture quotations are pinned in the source-conformance tests.
No survey data, population computation, or forecast claim is admitted.
"""

from __future__ import annotations

import dataclasses
from fractions import Fraction as F

import pytest

from populace_dynamics.track_b import gross_benefits as g
from populace_dynamics.track_b import ret_ledger as r
from populace_dynamics.track_b.gross_benefits import InvalidFamilyInput
from populace_dynamics.track_b.ret_grace import (
    BenefitType,
    GraceKind,
    GraceMonth,
    GraceYearState,
    TerminationEvent,
    grace_year,
)
from populace_dynamics.track_b.ret_params import (
    RETParameters,
    load_ret_parameters,
)
from tests.track_b_gross_benefit_support import ssa_params

PARAMS = load_ret_parameters()
MONTHS = frozenset(range(1, 13))
YEAR = 2026


def earnings(total=0, *, month=1, **kwargs):
    """Put invented wages in their month earned, without annualizing them."""
    wages = [F(0)] * 12
    wages[month - 1] = F(total)
    return r.WorkEarnings(wages=tuple(wages), **kwargs)


def grace_work(
    total,
    protected,
    *,
    benefit_type=BenefitType.RIB,
    entitled=MONTHS,
    year=YEAR,
):
    """Actual NSMs with annual NESE and explicit substantial-service facts.

    Zero monthly wages remain below every positive monthly exempt amount.
    Services in the other months keep the protected set fixed as the
    independently reportable annual NESE changes.
    """
    work = r.WorkEarnings(
        nese=F(total),
        self_employment_months=MONTHS,
        substantial_service_months=MONTHS - protected,
    )
    months = tuple(
        GraceMonth(
            frozenset({benefit_type}) if month in entitled else frozenset(),
            frozenset({benefit_type}) if month in entitled else frozenset(),
            nonservice=month in protected,
        )
        for month in range(1, 13)
    )
    return grace_year(year, GraceYearState(), months), work


def beneficiary(
    beneficiary_id="nh",
    rate=600,
    *,
    benefit_type=BenefitType.RIB,
    entitled=MONTHS,
    original_rate=None,
    work=None,
    estimate=None,
    **kwargs,
):
    """A twelve-month invented beneficiary; zero rates outside entitlement."""
    rates = (rate,) * 12 if not isinstance(rate, tuple) else rate
    original = original_rate if original_rate is not None else rates
    if not isinstance(original, tuple):
        original = (original,) * 12
    return r.RETBeneficiary(
        beneficiary_id,
        benefit_types=(benefit_type,) * 12,
        entitled_months=frozenset(entitled),
        gross_rates=tuple(
            F(amount) if month in entitled else F(0)
            for month, amount in enumerate(rates, 1)
        ),
        original_rates=tuple(F(amount) for amount in original),
        earnings=work or earnings(),
        estimated_earnings=estimate,
        **kwargs,
    )


def record(*members, year=YEAR, **kwargs):
    return r.RecordYear(
        year=year,
        nh_id="nh",
        beneficiaries=tuple(members or (beneficiary(),)),
        **kwargs,
    )


def ledger(*members, year=YEAR, **kwargs):
    return r.apply_ret_year(record(*members, year=year, **kwargs), PARAMS)


def worker(result, beneficiary_id="nh"):
    return next(
        row for row in result.workers if row.beneficiary_id == beneficiary_id
    )


def by_month(result, beneficiary_id="nh"):
    return {row.month: row for row in result.for_beneficiary(beneficiary_id)}


def lower_earnings_for_excess(excess, year=YEAR):
    """Invert the lower test for an exact invented whole-dollar excess."""
    return PARAMS.for_year(year).lower_exempt_amount.value + 2 * excess


def higher_earnings_for_excess(excess, year=YEAR):
    return PARAMS.for_year(year).higher_exempt_amount.value + 3 * excess


def test_mixed_child_cdb_termination_grace_preserves_one_dollar_january_check():
    # Review round 3's minimized case: ordinary child at 17 in January,
    # disability-based child at 18 in February, legal non-death termination
    # after February, and no March entitlement. No age exemption is asserted
    # for January. Caller-classified NESE has no substantial services.
    state = GraceYearState(
        last_met_year=2025,
        previous_entitled_types={BenefitType.CHILD},
        had_entitlement=True,
        last_processed_year=2025,
    )
    months = [
        GraceMonth({BenefitType.CHILD}, {BenefitType.CHILD}, True),
        GraceMonth({BenefitType.CDB}, {BenefitType.CDB}, True),
    ] + [GraceMonth()] * 10
    decision = grace_year(
        YEAR,
        state,
        months,
        termination_events=[TerminationEvent(2, BenefitType.CDB)],
    )
    child = dataclasses.replace(
        beneficiary(
            "child",
            rate=1,
            original_rate=1,
            entitled={1, 2},
            benefit_type=BenefitType.CDB,
            work=r.WorkEarnings(
                nese=24482,
                self_employment_months=MONTHS,
            ),
            grace=decision,
        ),
        benefit_types=(BenefitType.CHILD,) + (BenefitType.CDB,) * 11,
    )
    result = ledger(child, kind=r.RecordKind.DECEASED)
    rows = by_month(result, "child")
    assert rows[1].payment == 1
    assert rows[1].deduction == 0
    assert rows[2].payment == 1
    assert rows[2].deduction == 0
    assert sum(row.payment for row in result.months) == 2
    assert worker(result, "child").excess == 1
    assert worker(result, "child").charged == 0
    assert worker(result, "child").uncharged == 1
    assert decision.kinds == {GraceKind.TERMINATION}
    assert decision.met_eligible_months == decision.protected_months == {1}
    assert decision.next_state.last_met_year == 2025


def test_carried_child_cdb_same_legal_type_gap_charges_one_dollar_january():
    # Review round 4: DOB February 2007, CHILD in 2024, CDB from
    # February 2025, established normal termination after November 2025,
    # student CHILD in January 2026 and CDB from February onward. No
    # optional Act-age exemption is asserted; d1418 defaults apply.
    child_month = GraceMonth({BenefitType.CHILD}, {BenefitType.CHILD}, True)
    cdb_month = GraceMonth({BenefitType.CDB}, {BenefitType.CDB}, True)
    initial = grace_year(2024, GraceYearState(), [child_month] * 12)
    assert initial.kinds == {GraceKind.INITIAL}
    assert initial.next_state.last_met_year == 2024
    terminated = grace_year(
        2025,
        initial.next_state,
        [child_month] + [cdb_month] * 10 + [GraceMonth()],
        termination_events=[TerminationEvent(11, BenefitType.CDB)],
    )
    assert terminated.kinds == {GraceKind.TERMINATION}
    assert terminated.protected_months == {1}
    assert terminated.next_state == GraceYearState(
        last_met_year=2024,
        previous_entitled_types={BenefitType.CDB},
        had_entitlement=True,
        gap_since_entitlement=True,
        last_processed_year=2025,
    )
    decision = grace_year(
        YEAR, terminated.next_state, [child_month] + [cdb_month] * 11
    )
    child = dataclasses.replace(
        beneficiary(
            "child",
            rate=1,
            original_rate=1,
            benefit_type=BenefitType.CDB,
            work=r.WorkEarnings(nese=24482, self_employment_months=MONTHS),
            grace=decision,
        ),
        benefit_types=(BenefitType.CHILD,) + (BenefitType.CDB,) * 11,
    )
    result = ledger(child, kind=r.RecordKind.DECEASED)
    rows = by_month(result, "child")
    assert rows[1].payment == 0
    assert rows[1].deduction == 1
    assert all(rows[m].payment == 1 for m in range(2, 13))
    assert all(rows[m].deduction == 0 for m in range(2, 13))
    assert sum(row.payment for row in result.months) == 11
    assert worker(result, "child").excess == 1
    assert worker(result, "child").charged == 1
    assert worker(result, "child").uncharged == 0
    assert not decision.applies
    assert not decision.kinds
    assert decision.met_eligible_months == {1}
    assert not decision.protected_months
    assert decision.next_state.last_met_year == 2024
    assert not decision.next_state.pending_after_break


@pytest.mark.parametrize(
    "disabled, ordinary, role",
    [
        (BenefitType.DWB, BenefitType.WIDOW, g.Role.WIDOW),
        (BenefitType.CDB, BenefitType.CHILD, g.Role.CHILD),
    ],
    ids=["dwb-widow", "cdb-child"],
)
def test_carried_different_disability_type_grace_preserves_one_dollar_february(
    disabled, ordinary, role
):
    # Review round 5: young-spouse entitlement through November 2025,
    # no December entitlement, then a genuinely different section 202
    # entitlement in January 2026, initially disability-based. The widow
    # turns 60 in February; the CDB analogue has established disability
    # cessation and ordinary child entitlement from February. Caller
    # supplies the legal facts; d1418's optional own-work exemption is empty.
    spouse = GraceMonth({BenefitType.SPOUSE}, {BenefitType.SPOUSE}, True)
    initial = grace_year(2024, GraceYearState(), [spouse] * 12)
    assert initial.kinds == {GraceKind.INITIAL}
    assert initial.next_state.last_met_year == 2024
    terminated = grace_year(
        2025,
        initial.next_state,
        [spouse] * 11 + [GraceMonth()],
        termination_events=[
            TerminationEvent(11, BenefitType.SPOUSE, young_spouse=True)
        ],
    )
    assert terminated.kinds == {GraceKind.TERMINATION}
    assert terminated.next_state.last_met_year == 2024
    assert terminated.next_state.gap_since_entitlement
    assert not terminated.next_state.pending_after_break
    types = (disabled,) + (ordinary,) * 11
    decision = grace_year(
        YEAR,
        terminated.next_state,
        [GraceMonth({kind}, {kind}, True) for kind in types],
    )
    params = ssa_params()
    state = g.RecordState(
        g.FamilyKind.SURVIVOR,
        F("1.40"),
        g.retirement_survivor_family_maximum(F("1.40"), YEAR, params),
        eligibility_year=YEAR,
    )
    reduction = (
        dict(reduction_months=84, reduction_period_months=84)
        if role is g.Role.WIDOW
        else {}
    )
    family = g.family_benefits(
        state,
        [g.Beneficiary("survivor", role, **reduction)],
        payment_month=g.YearMonth(YEAR, 2),
        params=params,
        standalone=True,
    )
    rate = family.by_id()["survivor"]
    assert rate.auxiliary_payable == 1
    assert rate.original_benefit == (
        F("1.40") if role is g.Role.WIDOW else F(1)
    )
    survivor = dataclasses.replace(
        beneficiary(
            "survivor",
            rate=rate.auxiliary_payable,
            original_rate=rate.original_benefit,
            benefit_type=ordinary,
            work=r.WorkEarnings(nese=24482, self_employment_months=MONTHS),
            grace=decision,
        ),
        benefit_types=types,
    )
    result = ledger(survivor, kind=r.RecordKind.DECEASED)
    rows = by_month(result, "survivor")
    assert rows[1].payment == 1
    assert rows[2].payment == 1
    assert rows[2].deduction == 0
    assert all(row.payment == 1 for row in result.months)
    assert sum(row.payment for row in result.months) == 12
    assert worker(result, "survivor").excess == 1
    assert worker(result, "survivor").charged == 0
    assert worker(result, "survivor").uncharged == 1
    assert decision.kinds == {GraceKind.AFTER_BREAK}
    assert decision.met_eligible_months == set(range(2, 13))
    assert decision.protected_months == set(range(2, 13))
    assert decision.next_state.last_met_year == YEAR
    assert not decision.next_state.pending_after_break


@pytest.mark.parametrize("offset, excess", [(0, 0), (1, 0), (2, 1), (3, 1)])
def test_lower_threshold_and_whole_dollar_floor(offset, excess):
    limit = PARAMS.for_year(YEAR).lower_exempt_amount.value
    result = ledger(beneficiary(work=earnings(limit + offset)))
    assert worker(result).excess == excess
    assert sum(row.deduction for row in result.months) == excess


@pytest.mark.parametrize(
    "offset, excess", [(0, 0), (1, 0), (2, 0), (3, 1), (5, 1), (6, 2)]
)
def test_fra_threshold_uses_one_third_and_floors(offset, excess):
    limit = PARAMS.for_year(YEAR).higher_exempt_amount.value
    result = ledger(beneficiary(fra_month=6, work=earnings(limit + offset)))
    assert worker(result).excess == excess
    assert worker(result).withholding_rate == F(1, 3)
    assert all(row.deduction == 0 for row in result.months if row.month >= 6)


def test_fra_month_wages_and_later_wages_are_not_counted():
    pre = higher_earnings_for_excess(1)
    wages = (pre, 0, 0, 0, 0, 90_000, 90_000, 0, 0, 0, 0, 0)
    result = ledger(beneficiary(fra_month=6, work=r.WorkEarnings(wages=wages)))
    assert worker(result).countable_earnings == pre
    assert worker(result).excess == 1
    assert by_month(result)[1].deduction == 1


def test_fra_before_year_has_no_test_despite_large_earnings():
    result = ledger(beneficiary(fra_month=0, work=earnings(1_000_000)))
    assert worker(result).excess == 0
    assert not result.crediting_months["nh"]
    assert all(row.deduction == 0 for row in result.months)


def test_last_month_is_partial_final_but_full_provisional():
    result = ledger(beneficiary(work=earnings(lower_earnings_for_excess(801))))
    rows = by_month(result)
    assert [rows[m].deduction for m in (1, 2, 3)] == [600, 201, 0]
    assert [rows[m].provisional_deduction for m in (1, 2, 3)] == [600, 600, 0]
    assert [rows[m].payment for m in (1, 2, 3)] == [0, 399, 600]
    assert result.reconciliation["nh"] == 399
    assert result.crediting_months["nh"] == {1, 2}
    assert worker(result).charged == 801
    assert worker(result).provisional_withheld == 1200


def test_actual_and_estimated_earnings_are_separate_inputs():
    result = ledger(
        beneficiary(
            work=earnings(lower_earnings_for_excess(1000)),
            estimate=earnings(lower_earnings_for_excess(100)),
        )
    )
    assert worker(result).excess == 1000
    assert worker(result).estimated_excess == 100
    assert result.crediting_months["nh"] == {1, 2}
    assert result.reconciliation["nh"] == -400


def test_uncharged_excess_does_not_carry_into_the_next_year():
    first = ledger(
        beneficiary(work=earnings(lower_earnings_for_excess(9000, 2000))),
        year=2000,
    )
    assert worker(first).charged == 7200
    assert worker(first).uncharged == 1800
    next_year = ledger(beneficiary(), year=2001)
    assert worker(next_year).excess == 0
    assert all(row.payment == 600 for row in next_year.months)
    assert all(row.deduction == 0 for row in next_year.months)


def test_charging_starts_with_first_entitled_month_and_tracks_rate_changes():
    rates = (0, 0, 0, 100, 200, 300, 400, 500, 500, 500, 500, 510)
    result = ledger(
        beneficiary(
            rate=rates,
            entitled=frozenset(range(4, 13)),
            work=earnings(lower_earnings_for_excess(350)),
        )
    )
    rows = by_month(result)
    assert all(rows[m].deduction == 0 for m in range(1, 4))
    assert [rows[m].deduction for m in (4, 5, 6, 7)] == [100, 200, 50, 0]
    assert rows[12].gross == rows[12].net_due == 510


def test_year_of_death_uses_full_annual_exemption():
    limit = PARAMS.for_year(YEAR).lower_exempt_amount.value
    result = ledger(
        beneficiary(
            entitled=frozenset(range(1, 6)),
            death_month=6,
            work=earnings(limit),
        )
    )
    assert worker(result).annual_exempt == limit
    assert worker(result).excess == 0


def test_auxiliarys_own_excess_begins_after_number_holders_full_deductions():
    result = ledger(
        beneficiary(rate=400, work=earnings(lower_earnings_for_excess(1200))),
        beneficiary(
            "spouse",
            rate=200,
            benefit_type=BenefitType.SPOUSE,
            work=earnings(lower_earnings_for_excess(300)),
        ),
    )
    nh = by_month(result)
    spouse = by_month(result, "spouse")
    assert [nh[m].nh_deduction for m in (1, 2, 3, 4)] == [400, 400, 0, 0]
    assert [spouse[m].nh_deduction for m in (1, 2, 3, 4)] == [200, 200, 0, 0]
    assert [spouse[m].own_deduction for m in (1, 2, 3, 4)] == [0, 0, 200, 100]
    assert all(row.own_deduction == 0 for row in nh.values())
    assert worker(result, "spouse").charged == 300


@pytest.mark.parametrize("qualification", ["two_years", "prior_rib"])
def test_qualifying_divorced_spouse_is_outside_number_holders_test(
    qualification,
):
    nh = beneficiary(rate=400, work=earnings(lower_earnings_for_excess(500)))
    child = beneficiary("child", rate=200, benefit_type=BenefitType.CHILD)
    facts = (
        {"divorced_months": MONTHS}
        if qualification == "two_years"
        else {"nh_entitled_before_divorce": True}
    )
    divorced = beneficiary(
        "divorced", rate=200, benefit_type=BenefitType.DIVORCED_SPOUSE, **facts
    )
    without = ledger(nh, child)
    with_divorced = ledger(nh, child, divorced)
    for bid in ("nh", "child"):
        assert with_divorced.for_beneficiary(bid) == without.for_beneficiary(
            bid
        )
    assert all(
        row.nh_deduction == 0 and row.payment == 200
        for row in with_divorced.for_beneficiary("divorced")
    )


def test_nonqualifying_divorced_spouse_is_charged_to_number_holders_excess():
    result = ledger(
        beneficiary(rate=400, work=earnings(lower_earnings_for_excess(600))),
        beneficiary(
            "divorced", rate=200, benefit_type=BenefitType.DIVORCED_SPOUSE
        ),
    )
    assert by_month(result, "divorced")[1].nh_deduction == 200


def test_divorced_spouse_remains_subject_to_own_earnings_test():
    result = ledger(
        beneficiary(rate=400, work=earnings(lower_earnings_for_excess(600))),
        beneficiary(
            "divorced",
            rate=200,
            benefit_type=BenefitType.DIVORCED_SPOUSE,
            divorced_months=MONTHS,
            work=earnings(lower_earnings_for_excess(100)),
        ),
    )
    row = by_month(result, "divorced")[1]
    assert row.nh_deduction == 0
    assert row.own_deduction == 100
    assert row.payment == 100


def test_grace_nonservice_months_protect_own_benefit():
    wages = (30_000,) + (0,) * 11
    months = tuple(
        GraceMonth(
            entitled_types=frozenset({BenefitType.RIB}),
            received_types=frozenset({BenefitType.RIB}),
            nonservice=month != 1,
        )
        for month in range(1, 13)
    )
    grace = grace_year(YEAR, GraceYearState(), months)
    result = ledger(beneficiary(work=r.WorkEarnings(wages=wages), grace=grace))
    assert grace.protected_months == frozenset(range(2, 13))
    assert by_month(result)[1].deduction == 600
    assert all(row.deduction == 0 for row in result.months if row.month != 1)
    assert worker(result).uncharged > 0


@pytest.mark.parametrize(
    "benefit_type", [BenefitType.DIB, BenefitType.DWB, BenefitType.CDB]
)
def test_disability_benefits_are_exempt_from_their_own_work_test(benefit_type):
    result = ledger(
        beneficiary(),
        beneficiary(
            "disabled",
            rate=200,
            benefit_type=benefit_type,
            work=earnings(500_000),
        ),
    )
    assert all(
        row.own_deduction == 0 for row in result.for_beneficiary("disabled")
    )


def test_auxiliary_fra_protects_against_own_excess_but_not_nh_excess():
    result = ledger(
        beneficiary(rate=400, work=earnings(lower_earnings_for_excess(600))),
        beneficiary(
            "spouse", rate=200, benefit_type=BenefitType.SPOUSE, fra_month=0
        ),
    )
    assert by_month(result, "spouse")[1].nh_deduction == 200
    assert by_month(result, "spouse")[1].own_deduction == 0


def test_protected_number_holder_protects_family_against_number_holder_excess():
    grace, work = grace_work(lower_earnings_for_excess(400), MONTHS)
    result = ledger(
        beneficiary(
            rate=400,
            grace=grace,
            work=work,
        ),
        beneficiary("child", rate=200, benefit_type=BenefitType.CHILD),
    )
    assert all(row.nh_deduction == 0 for row in result.for_beneficiary("nh"))
    assert all(
        row.nh_deduction == 0 for row in result.for_beneficiary("child")
    )
    assert worker(result).charged == 0


def test_partial_apportionment_keeps_fractional_entitlements_until_check_floor():
    shares = r.partial_payments(
        F(93),
        {"nh": F(117), "spouse": F(16), "a": F("19.90"), "b": F("19.90")},
        {"nh": F(117), "spouse": F("58.50"), "a": F("58.50"), "b": F("58.50")},
    )
    assert shares == {
        "nh": F("38.50"),
        "spouse": F(16),
        "a": F("19.25"),
        "b": F("19.25"),
    }
    assert sum(shares.values()) == 93
    assert {key: int(value) for key, value in shares.items()} == {
        "nh": 38,
        "spouse": 16,
        "a": 19,
        "b": 19,
    }


@pytest.mark.parametrize(
    "pool, nh_share, child_share, residual",
    [
        (F(8), F(4), F(2), F("0.10")),
        (F("9.90"), F("4.95"), F("2.475"), F("0.575")),
    ],
)
def test_review_subdollar_stop_preserves_last_shares_and_residual(
    pool, nh_share, child_share, residual
):
    rates = {"nh": F(10), "spouse": F("1.90"), "child": F(10)}
    originals = {"nh": F(2), "spouse": F(1), "child": F(1)}
    stopped = r.partial_payments(pool, rates, originals)
    assert stopped == {
        "nh": nh_share,
        "spouse": F(19, 10),
        "child": child_share,
    }
    assert stopped.undistributed_subdollar_residual == residual
    assert sum(stopped.values()) + residual == pool
    assert {key: int(value) for key, value in stopped.items()} == {
        "nh": 4,
        "spouse": 1,
        "child": 2,
    }


def test_review_source_stop_with_rates_generated_by_g():
    params = ssa_params()
    state = g.RecordState(
        g.FamilyKind.RETIREMENT,
        F(5),
        F("7.50"),
        worker=g.OwnBenefit(
            g.OwnBenefitKind.OLD_AGE, F(5), reduction_months=60
        ),
        eligibility_year=YEAR,
    )
    family = g.family_benefits(
        state,
        [
            g.Beneficiary(
                "spouse",
                g.Role.SPOUSE,
                own_benefit=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F("1.10")),
                own_benefit_first=True,
            ),
            g.Beneficiary(
                "child",
                g.Role.CHILD,
                own_benefit=g.OwnBenefit(
                    g.OwnBenefitKind.DISABILITY, F("0.20")
                ),
            ),
        ],
        payment_month=g.YearMonth(YEAR, 1),
        params=params,
        standalone=True,
    )
    rows = family.by_id()
    assert family.worker_benefit == F("3.50")
    assert rows["spouse"].auxiliary_payable == F("0.10")
    assert rows["child"].auxiliary_payable == F(1)
    result = ledger(
        beneficiary(
            rate=family.worker_benefit,
            original_rate=5,
            work=earnings(24_486),
        ),
        beneficiary(
            "spouse",
            rate=rows["spouse"].auxiliary_payable,
            original_rate=rows["spouse"].original_benefit,
            benefit_type=BenefitType.SPOUSE,
            fra_month=0,
            two_record_entitlement=True,
        ),
        beneficiary(
            "child",
            rate=rows["child"].auxiliary_payable,
            original_rate=rows["child"].original_benefit,
            benefit_type=BenefitType.CDB,
            two_record_entitlement=True,
        ),
        family_maximum_binding_months=MONTHS,
    )
    january = {
        key: by_month(result, key)[1] for key in ("nh", "spouse", "child")
    }
    assert [january[k].net_due for k in january] == [
        F("0.80"),
        F("0.10"),
        F("0.40"),
    ]
    assert [january[k].payment for k in january] == [0, 0, 0]
    assert worker(result).excess == worker(result).charged == 3
    assert worker(result).uncharged == 0
    assert worker(result).undistributed_subdollar_residual == F("0.30")
    assert sum(row.deduction for row in result.months) == F("3.30")


def test_two_beneficiary_capped_payment_pays_exact_balance_without_subdollar_stop():
    rates = {"nh": F(10), "spouse": F("1.90")}
    originals = {"nh": F(2), "spouse": F(1)}
    result = r.partial_payments(F(6), rates, originals)
    assert result == {"nh": F("4.10"), "spouse": F("1.90")}
    assert sum(result.values()) == 6
    assert result.undistributed_subdollar_residual == 0


def test_exactly_one_dollar_overflow_is_reapportioned():
    result = r.partial_payments(
        8,
        {"nh": 10, "spouse": 1, "child": 10},
        {"nh": 2, "spouse": 1, "child": 1},
    )
    assert result == {"nh": F(14, 3), "spouse": F(1), "child": F(7, 3)}
    assert result.undistributed_subdollar_residual == 0


def test_later_subdollar_stop_retains_previously_capped_beneficiary():
    # First cap releases $2; the next cap releases 17/30, requiring a stop
    # even though only two of the original three beneficiaries remain.
    result = r.partial_payments(
        8,
        {"nh": 10, "spouse": 0, "child": "2.10"},
        {"nh": 2, "spouse": 1, "child": 1},
    )
    assert result == {"nh": F(16, 3), "spouse": F(0), "child": F(21, 10)}
    assert result.undistributed_subdollar_residual == F(17, 30)
    assert sum(result.values()) + result.undistributed_subdollar_residual == 8


def test_entitled_zero_rate_auxiliary_keeps_its_original_partial_share():
    # G supports a spouse whose own PIA leaves technical entitlement, but
    # one delayed credit makes the payable spouse excess zero. All subject
    # auxiliaries are dual, so G does not require Parisi redistribution.
    params = ssa_params()
    state = g.RecordState(
        g.FamilyKind.RETIREMENT,
        F(1000),
        g.retirement_survivor_family_maximum(F(1000), YEAR, params),
        worker=g.OwnBenefit(
            g.OwnBenefitKind.OLD_AGE, F(1000), reduction_months=60
        ),
        eligibility_year=YEAR,
    )
    family = g.family_benefits(
        state,
        [
            g.Beneficiary(
                "spouse",
                g.Role.SPOUSE,
                own_benefit=g.OwnBenefit(
                    g.OwnBenefitKind.OLD_AGE,
                    F(499),
                    delayed_credit_months=1,
                    birth_year=1955,
                ),
                own_benefit_first=True,
            ),
            g.Beneficiary(
                "child",
                g.Role.CHILD,
                own_benefit=g.OwnBenefit(g.OwnBenefitKind.DISABILITY, F(100)),
            ),
        ],
        payment_month=g.YearMonth(YEAR, 1),
        params=params,
        standalone=True,
    )
    rows = family.by_id()
    assert family.worker_benefit == 700
    assert rows["spouse"].entitled
    assert rows["spouse"].original_benefit == 500
    assert rows["spouse"].auxiliary_payable == 0
    assert rows["child"].auxiliary_payable == 150
    case = record(
        beneficiary(
            rate=family.worker_benefit,
            original_rate=1000,
            work=earnings(lower_earnings_for_excess(849)),
        ),
        beneficiary(
            "spouse",
            rate=rows["spouse"].auxiliary_payable,
            original_rate=rows["spouse"].original_benefit,
            benefit_type=BenefitType.SPOUSE,
            fra_month=0,
            two_record_entitlement=True,
        ),
        beneficiary(
            "child",
            rate=rows["child"].auxiliary_payable,
            original_rate=rows["child"].original_benefit,
            benefit_type=BenefitType.CDB,
            two_record_entitlement=True,
        ),
        family_maximum_binding_months=MONTHS,
    )
    # The $1 partial pool's original shares are .50/.25/.25. Capping
    # the technically entitled spouse at zero leaves a sub-$1 overflow.
    stopped = r.apply_ret_year(case, PARAMS)
    assert by_month(stopped)[1].net_due == F(1, 2)
    assert by_month(stopped, "child")[1].net_due == F(1, 4)
    assert by_month(stopped, "spouse")[1].net_due == 0
    assert sum(row.net_due for row in stopped.months if row.month == 1) == F(
        3, 4
    )
    assert worker(stopped).undistributed_subdollar_residual == F(1, 4)
    assert worker(stopped).charged == 849
    assert sum(row.deduction for row in stopped.months) == F("849.25")
    assert stopped.crediting_months["spouse"] == frozenset()


def test_binding_survivor_maximum_with_zero_rate_cdb_is_deferred_to_part_b():
    # A zero auxiliary rate after dual entitlement does not remove that
    # beneficiary from the family-maximum computation. Widow own work
    # can release room for the entitled CDB recipient.
    params = ssa_params()
    state = g.RecordState(
        g.FamilyKind.SURVIVOR,
        F(1000),
        g.retirement_survivor_family_maximum(F(1000), YEAR, params),
        eligibility_year=YEAR,
    )
    family = g.family_benefits(
        state,
        [
            g.Beneficiary(
                "widow",
                g.Role.WIDOW,
                reduction_months=60,
                reduction_period_months=84,
            ),
            g.Beneficiary(
                "cdb",
                g.Role.CHILD,
                own_benefit=g.OwnBenefit(g.OwnBenefitKind.DISABILITY, F(650)),
            ),
        ],
        payment_month=g.YearMonth(YEAR, 1),
        params=params,
        standalone=True,
    )
    rows = family.by_id()
    assert family.family_maximum_binding
    assert rows["widow"].auxiliary_payable == F("796.40")
    assert rows["cdb"].entitled
    assert rows["cdb"].original_benefit == 750
    assert rows["cdb"].auxiliary_payable == 0
    case = record(
        beneficiary(
            "widow",
            rate=rows["widow"].auxiliary_payable,
            original_rate=rows["widow"].original_benefit,
            benefit_type=BenefitType.WIDOW,
            work=earnings(lower_earnings_for_excess(100)),
        ),
        beneficiary(
            "cdb",
            rate=0,
            original_rate=750,
            benefit_type=BenefitType.CDB,
            two_record_entitlement=True,
        ),
        kind=r.RecordKind.DECEASED,
        family_maximum_binding_months=MONTHS,
    )
    with pytest.raises(r.RETConfigurationUnsupported) as error:
        r.apply_ret_year(case, PARAMS)
    assert error.value.reason is r.UnsupportedReason.DEDUCTION_BEFORE_REDUCTION


@pytest.mark.parametrize(
    "kwargs, reason",
    [
        ({"year": 1999}, "YEAR_BEFORE_2000"),
        ({"fiscal_year": True}, "FISCAL_YEAR"),
        ({"short_taxable_year": True}, "SHORT_TAXABLE_YEAR"),
        ({"foreign_work": True}, "FOREIGN_WORK"),
        (
            {"vocational_rehabilitation_refusal": True},
            "VOCATIONAL_REHABILITATION",
        ),
        ({"other_deduction_months": frozenset({1})}, "OTHER_DEDUCTION"),
    ],
)
def test_record_coverage_refusals_are_explicit(kwargs, reason):
    with pytest.raises(r.RETConfigurationUnsupported) as error:
        ledger(**kwargs)
    assert error.value.reason is r.UnsupportedReason[reason]
    assert error.value.code == "FAMILY_CONFIG_UNSUPPORTED"


@pytest.mark.parametrize(
    "method, reason",
    [
        ("PRORATED", "PRORATED_SUSPENSION"),
        ("DEFERRED", "DEFERRED_SUSPENSION"),
        ("PROTEST_PARTIAL", "PROTEST_PARTIAL_SUSPENSION"),
    ],
)
def test_requested_suspension_methods_are_refused(method, reason):
    with pytest.raises(r.RETConfigurationUnsupported) as error:
        ledger(suspension_method=r.SuspensionMethod[method])
    assert error.value.reason is r.UnsupportedReason[reason]


def test_auxiliary_excess_with_binding_family_maximum_is_deferred_to_part_b():
    spouse = beneficiary(
        "spouse",
        rate=200,
        benefit_type=BenefitType.SPOUSE,
        work=earnings(lower_earnings_for_excess(100)),
    )
    with pytest.raises(r.RETConfigurationUnsupported) as error:
        ledger(
            beneficiary(), spouse, family_maximum_binding_months=frozenset({1})
        )
    assert error.value.reason is r.UnsupportedReason.DEDUCTION_BEFORE_REDUCTION


def test_nonbinding_number_holder_partial_deduction_precedes_auxiliary_own():
    # CFR 404.441 expressly permits the working auxiliary's own excess
    # against the benefits left in the NH's final partial month. With no
    # binding maximum, this does not require part (b)'s rate readjustment.
    result = ledger(
        beneficiary(rate=400, work=earnings(lower_earnings_for_excess(500))),
        beneficiary(
            "spouse",
            rate=200,
            benefit_type=BenefitType.SPOUSE,
            work=earnings(lower_earnings_for_excess(100)),
        ),
    )
    spouse = by_month(result, "spouse")
    assert worker(result).charged == 500
    assert worker(result, "spouse").charged == 100
    assert spouse[1].nh_deduction == F(500, 3)
    assert spouse[1].own_deduction == F(100, 3)
    assert spouse[1].net_due == 0
    assert spouse[2].own_deduction == F(200, 3)


def test_two_record_entitlement_with_excess_is_refused():
    with pytest.raises(r.RETConfigurationUnsupported) as error:
        ledger(
            beneficiary(
                two_record_entitlement=True,
                work=earnings(lower_earnings_for_excess(1)),
            )
        )
    assert error.value.reason is r.UnsupportedReason.TWO_RECORD_EARNINGS


def test_two_record_entitlement_without_excess_does_not_require_combined_charging():
    result = ledger(beneficiary(two_record_entitlement=True))
    assert all(row.deduction == 0 for row in result.months)


def test_missing_parameter_year_is_not_carried_forward():
    missing = max(PARAMS.years) + 1
    with pytest.raises(KeyError, match=f"year {missing}"):
        ledger(year=missing)


def test_supplied_parameter_table_is_used_for_the_exemption():
    original = PARAMS.for_year(YEAR)
    altered = dataclasses.replace(
        original,
        lower_exempt_amount=dataclasses.replace(
            original.lower_exempt_amount, value=30_000
        ),
    )
    parameters = RETParameters({YEAR: altered}, PARAMS.parameter_sha256)
    result = r.apply_ret_year(
        record(beneficiary(work=earnings(30_002))), parameters
    )
    assert worker(result).annual_exempt == 30_000
    assert worker(result).monthly_exempt == 2500
    assert worker(result).excess == 1


@pytest.mark.parametrize("fra_month", [-1, 13, True, "6"])
def test_invalid_fra_month_is_an_input_error(fra_month):
    with pytest.raises(InvalidFamilyInput):
        ledger(beneficiary(fra_month=fra_month))


@pytest.mark.parametrize(
    "wages", [(0,) * 11, (-1,) + (0,) * 11, (0.1,) + (0,) * 11]
)
def test_invalid_wage_inputs_raise_before_coverage_refusal(wages):
    with pytest.raises(InvalidFamilyInput):
        ledger(beneficiary(work=r.WorkEarnings(wages=wages)), fiscal_year=True)


@pytest.mark.parametrize("rate", [F(-1), F(1, 3), 0.1, True])
def test_invalid_rates_raise_before_coverage_refusal(rate):
    with pytest.raises(InvalidFamilyInput):
        row = r.RETBeneficiary(
            "nh",
            (BenefitType.RIB,) * 12,
            MONTHS,
            (rate,) * 12,
            (F(600),) * 12,
        )
        r.apply_ret_year(record(row, fiscal_year=True), PARAMS)


def test_duplicate_identity_is_invalid_even_in_an_unsupported_record():
    with pytest.raises(InvalidFamilyInput):
        ledger(beneficiary(), beneficiary(), fiscal_year=True)


def test_invalid_inputs_are_not_counted_as_coverage_gaps():
    with pytest.raises(InvalidFamilyInput):
        r.evaluate_ret(
            "invalid",
            1,
            lambda: ledger(beneficiary(fra_month=13), fiscal_year=True),
        )


@pytest.mark.parametrize("months", [(1, True), (True, 1), (1, 1.0), (1.0, 1)])
def test_invalid_self_employment_month_collision_is_an_input_error(months):
    # Round 4's minimized NESE case must inspect both raw equal values.
    with pytest.raises(InvalidFamilyInput):
        r.WorkEarnings(nese=1, self_employment_months=months)


@pytest.mark.parametrize("months", [(1, True), (True, 1), (1, 1.0), (1.0, 1)])
def test_invalid_entitlement_month_collision_precedes_foreign_work_refusal(
    months,
):
    # Construct inside the outcome callback: malformed facts must raise
    # before the foreign-work flag can create a retained coverage refusal.
    with pytest.raises(InvalidFamilyInput):
        r.evaluate_ret(
            "malformed-months",
            1,
            lambda: ledger(
                dataclasses.replace(
                    beneficiary(entitled={1}), entitled_months=months
                ),
                foreign_work=True,
            ),
        )


def test_coverage_denominator_keeps_refusals_and_blocks_aggregate():
    outcomes = [
        r.evaluate_ret("supported", 2, ledger),
        r.evaluate_ret("refused", 3, lambda: ledger(fiscal_year=True)),
    ]
    totals = r.count_ret_outcomes(outcomes)
    assert (totals.rows, totals.supported_rows, totals.unsupported_rows) == (
        2,
        1,
        1,
    )
    assert totals.weight == 5
    assert totals.unsupported_weight == 3
    with pytest.raises(r.FamilyTargetBlocked):
        r.weighted_ret_total(outcomes)


def test_negative_nese_floor_and_drop_cents_readings_are_explicit():
    work = r.WorkEarnings(nese=F(-13), self_employment_months=MONTHS)
    assert r.countable_earnings(work, 6) == -10
    assert (
        r.countable_earnings(
            work,
            6,
            nese_proration_policy=r.NESEProrationPolicy.DROP_CENTS,
        )
        == -5
    )


def test_negative_nese_reading_changes_final_deduction_by_one_dollar():
    higher = PARAMS.for_year(YEAR).higher_exempt_amount.value
    wages = (higher + 13,) + (0,) * 11
    work = r.WorkEarnings(wages=wages, nese=-13, self_employment_months=MONTHS)
    case = record(beneficiary(fra_month=6, work=work))
    literal_round_down = r.apply_ret_year(case, PARAMS)
    alternative = r.apply_ret_year(
        case,
        PARAMS,
        nese_proration_policy=r.NESEProrationPolicy.DROP_CENTS,
    )
    assert worker(literal_round_down).countable_earnings == higher + 3
    assert worker(alternative).countable_earnings == higher + 8
    assert worker(literal_round_down).excess == 1
    assert worker(alternative).excess == 2
    assert by_month(literal_round_down)[1].payment == 599
    assert by_month(alternative)[1].payment == 598


def test_unmarried_deemed_entitlement_is_refused_pending_source_judgment():
    with pytest.raises(r.RETConfigurationUnsupported) as error:
        ledger(
            beneficiary(work=earnings(lower_earnings_for_excess(600))),
            beneficiary(
                "deemed",
                rate=200,
                benefit_type=BenefitType.CDB,
                deemed_entitled=True,
            ),
        )
    assert error.value.reason is r.UnsupportedReason.DEEMED_ENTITLEMENT_BASIS


def test_married_deemed_disabled_child_is_charged_number_holders_excess():
    result = ledger(
        beneficiary(rate=400, work=earnings(lower_earnings_for_excess(600))),
        beneficiary(
            "deemed",
            rate=200,
            benefit_type=BenefitType.CDB,
            deemed_entitled=True,
            deemed_married_to_nh=True,
        ),
    )
    assert by_month(result, "deemed")[1].nh_deduction == 200
    assert by_month(result, "deemed")[1].own_deduction == 0


def test_chart_ceiling_and_exact_monthly_limit_readings_change_grace_payment():
    year = 2001
    higher = PARAMS.for_year(year).higher_exempt_amount.value
    exact_monthly = higher / 12
    chart_monthly = -(-higher // 12)
    assert exact_monthly < chart_monthly
    wages = (higher + 3000, chart_monthly) + (0,) * 10
    months = tuple(
        GraceMonth(
            entitled_types=frozenset({BenefitType.RIB}),
            received_types=frozenset({BenefitType.RIB}),
            nonservice=month != 1,
        )
        for month in range(1, 13)
    )
    grace = grace_year(year, GraceYearState(), months, fra_month=6)
    case = record(
        beneficiary(
            fra_month=6, work=r.WorkEarnings(wages=wages), grace=grace
        ),
        year=year,
    )
    exact = r.apply_ret_year(case, PARAMS)
    chart = r.apply_ret_year(
        case,
        PARAMS,
        monthly_limit_policy=r.MonthlyLimitPolicy.NONSTATUTORY_CHART_CEILING,
    )
    assert worker(chart).monthly_exempt == chart_monthly
    assert worker(exact).monthly_exempt == exact_monthly
    assert by_month(chart)[2].payment == 600
    assert by_month(exact)[2].payment == 0
    assert worker(exact).charged - worker(chart).charged == 600


def test_disability_number_holder_is_exempt_while_spouses_own_work_is_tested():
    result = ledger(
        beneficiary(benefit_type=BenefitType.DIB, work=earnings(500_000)),
        beneficiary(
            "spouse",
            rate=200,
            benefit_type=BenefitType.SPOUSE,
            work=earnings(lower_earnings_for_excess(300)),
        ),
        kind=r.RecordKind.DISABILITY,
    )
    assert all(row.deduction == 0 for row in result.for_beneficiary("nh"))
    assert all(row.nh_deduction == 0 for row in result.months)
    assert [row.own_deduction for row in result.for_beneficiary("spouse")][
        :3
    ] == [200, 100, 0]


@pytest.mark.parametrize(
    "benefit_type", [BenefitType.WIDOW, BenefitType.MOTHER_FATHER]
)
def test_survivors_own_excess_is_charged_on_a_deceased_record(benefit_type):
    result = ledger(
        beneficiary(
            "survivor",
            rate=200,
            benefit_type=benefit_type,
            work=earnings(lower_earnings_for_excess(300)),
        ),
        kind=r.RecordKind.DECEASED,
    )
    assert [row.own_deduction for row in result.for_beneficiary("survivor")][
        :3
    ] == [200, 100, 0]
    assert all(row.nh_deduction == 0 for row in result.months)
    assert result.crediting_months["survivor"] == {1, 2}
