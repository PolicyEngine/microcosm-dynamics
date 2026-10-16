"""Executed money comparisons for documented R2 source readings.

Verification class: statutory conformance; all monetary cases are invented.
Source quotations are hash-pinned in test_track_b_ret_ledger_sources and
test_track_b_ret_grace. No population or forecast claim is admitted.
"""

from dataclasses import replace
from decimal import Decimal
from fractions import Fraction as F

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import ret_ledger as r
from populace_dynamics.track_b.ret_grace import (
    BenefitType,
    DisabilityGraceReading,
    GraceMonth,
    GraceYearState,
    grace_year,
)
from tests.test_track_b_ret_ledger import (
    PARAMS,
    YEAR,
    beneficiary,
    earnings,
    record,
)
from tests.track_b_ret_ledger_support import source_text


def _simultaneous_dib_elected_rib(rate, work, reading):
    entitlement = frozenset(range(6, 13))
    months = tuple(
        (
            GraceMonth(
                frozenset({BenefitType.RIB, BenefitType.DIB}),
                frozenset({BenefitType.RIB}),
                nonservice=True,
            )
            if m in entitlement
            else GraceMonth()
        )
        for m in range(1, 13)
    )
    decision = grace_year(
        YEAR,
        GraceYearState(),
        months,
        disability_reading=reading,
    )
    return r.apply_ret_year(
        record(
            beneficiary(
                rate=rate, entitled=entitlement, work=work, grace=decision
            )
        ),
        PARAMS,
    )


def test_simultaneous_dib_rib_source_readings_change_4200_dollars():
    work = earnings(45_000)
    strict = _simultaneous_dib_elected_rib(
        600, work, DisabilityGraceReading.CFR_ENTITLEMENT_EXCLUSION
    )
    poms = _simultaneous_dib_elected_rib(
        600, work, DisabilityGraceReading.POMS_RIB_ELECTION
    )
    assert sum(m.deduction for m in strict.months) == 4200
    assert sum(m.deduction for m in poms.months) == 0
    assert sum(m.payment for m in strict.months) == 0
    assert sum(m.payment for m in poms.months) == 4200
    assert strict.crediting_months["nh"] == frozenset(range(6, 13))
    assert not poms.crediting_months["nh"]


@settings(max_examples=100, deadline=None)
@given(st.integers(1, 2000), st.integers(24_480, 100_000))
def test_property_explicit_poms_election_protects_only_eligible_rib_months(
    rate, wages
):
    work = earnings(wages)
    strict = _simultaneous_dib_elected_rib(
        rate, work, DisabilityGraceReading.CFR_ENTITLEMENT_EXCLUSION
    )
    poms = _simultaneous_dib_elected_rib(
        rate, work, DisabilityGraceReading.POMS_RIB_ELECTION
    )
    excess = (F(wages) - PARAMS.for_year(YEAR).lower_exempt_amount.value) // 2
    assert sum(m.deduction for m in strict.months) == min(excess, 7 * rate)
    assert all(m.deduction == 0 for m in poms.months)
    assert sum(m.payment for m in poms.months) == 7 * rate
    assert all(m.deduction == 0 for m in strict.months if m.month < 6)


def _reported_grace_change(rate):
    actual = earnings(
        24_480 + 24 * rate,
        self_employment_months=frozenset(range(1, 13)),
        substantial_service_months=frozenset(range(1, 13)),
    )
    estimate = earnings(
        24_480 + 24 * rate,
        self_employment_months=frozenset(range(1, 13)),
        substantial_service_months=frozenset(range(1, 6)),
    )

    def decision(predicted):
        return grace_year(
            YEAR,
            GraceYearState(),
            tuple(
                GraceMonth(
                    {BenefitType.RIB},
                    {BenefitType.RIB},
                    nonservice=predicted and m >= 6,
                )
                for m in range(1, 13)
            ),
        )

    return r.apply_ret_year(
        record(
            beneficiary(
                rate=rate,
                work=actual,
                estimate=estimate,
                grace=decision(False),
                estimated_grace=decision(True),
            )
        ),
        PARAMS,
    )


def test_estimated_initial_grace_and_actual_grace_are_separate():
    result = _reported_grace_change(600)
    assert sum(m.deduction for m in result.months) == 7200
    assert sum(m.provisional_deduction for m in result.months) == 3000
    assert result.reconciliation["nh"] == -4200
    assert result.crediting_months["nh"] == frozenset(range(1, 13))


@settings(max_examples=100, deadline=None)
@given(st.integers(1, 3000))
def test_property_changed_grace_estimate_can_require_recovery(rate):
    result = _reported_grace_change(rate)
    assert result.reconciliation["nh"] == -7 * rate
    assert sum(m.deduction for m in result.months) == 12 * rate
    assert sum(m.provisional_deduction for m in result.months) == 5 * rate
    assert all(m.gross == m.net_due + m.deduction for m in result.months)


@settings(max_examples=200, deadline=None)
@given(
    st.integers(-100_000, 100_000),
    st.integers(0, 100_000),
    st.sampled_from([F(1, 2), F(1, 3)]),
    st.integers(0, 99),
)
def test_property_excess_uses_exact_statutory_rate_and_dollar_floor(
    dollars, exempt, rate, cents
):
    income = F(dollars) + F(cents, 100)
    exact = max(F(0), income - exempt) * rate
    excess = r.calculated_excess(income, exempt, rate)
    assert isinstance(excess, int)
    assert 0 <= exact - excess < 1
    assert excess >= 0


def _historical_monthly_boundary(year, february_wages, excess=1):
    """An initial grace year with only February entitled before March FRA.

    The caller's chart-derived NSM flag cannot override the ledger's exact
    statutory wage threshold. January wages produce the supplied excess.
    """
    annual = PARAMS.for_year(year).higher_exempt_amount.value
    wages = (annual + 3 * excess - february_wages, february_wages) + (0,) * 10
    months = tuple(
        (
            GraceMonth({BenefitType.RIB}, {BenefitType.RIB}, nonservice=True)
            if month == 2
            else GraceMonth()
        )
        for month in range(1, 13)
    )
    grace = grace_year(year, GraceYearState(), months, fra_month=3)
    return record(
        beneficiary(
            rate=1,
            entitled={2},
            fra_month=3,
            work=r.WorkEarnings(wages=wages),
            grace=grace,
        ),
        year=year,
    )


def test_act_203_f_8_d_vi_exact_limit_is_not_chart_ceiling():
    # Reviewer's minimized case: January22919 + February2084 =25003.
    case = _historical_monthly_boundary(2001, F(2084))
    assert case.beneficiaries[0].earnings.wages[:2] == (22919, 2084)
    result = r.apply_ret_year(case, PARAMS)
    february = result.for_beneficiary("nh")[1]
    worker = result.workers[0]
    assert worker.monthly_exempt == F(25000, 12)
    assert worker.countable_earnings == 25003
    assert worker.excess == worker.charged == 1
    assert worker.uncharged == 0
    assert february.payment == 0
    assert february.deduction == 1


def test_nonstatutory_chart_ceiling_is_explicit_operational_sensitivity():
    case = _historical_monthly_boundary(2001, F(2084))
    statutory = r.apply_ret_year(case, PARAMS)
    chart = r.apply_ret_year(
        case,
        PARAMS,
        monthly_limit_policy=(r.MonthlyLimitPolicy.NONSTATUTORY_CHART_CEILING),
    )
    assert statutory.workers[0].monthly_exempt == F(25000, 12)
    assert chart.workers[0].monthly_exempt == 2084
    assert statutory.for_beneficiary("nh")[1].payment == 0
    assert chart.for_beneficiary("nh")[1].payment == 1
    assert statutory.workers[0].charged == 1
    assert chart.workers[0].charged == 0
    assert chart.workers[0].uncharged == 1


@settings(max_examples=100, deadline=None)
@given(
    st.integers(2000, 2026),
    st.sampled_from([F(-1, 100), F(0), F(1, 100)]),
    st.integers(1, 20),
)
def test_property_default_monthly_limit_is_exact_twelfth_and_controls_grace_wages(
    year, offset, excess
):
    # Differential against R1's pinned annual amount, with zero tolerance.
    monthly = PARAMS.for_year(year).higher_exempt_amount.value / 12
    case = _historical_monthly_boundary(year, monthly + offset, excess)
    result = r.apply_ret_year(case, PARAMS)
    explicit = r.apply_ret_year(
        case,
        PARAMS,
        monthly_limit_policy=r.MonthlyLimitPolicy.EXACT_TWELFTH,
    )
    assert result == explicit
    assert result.workers[0].monthly_exempt == monthly
    assert result.workers[0].excess == excess
    february = result.for_beneficiary("nh")[1]
    assert february.deduction == int(offset > 0)
    assert february.payment == int(offset <= 0)
    assert result.workers[0].charged == february.deduction
    assert result.workers[0].uncharged == excess - february.deduction


def test_subdollar_stop_prevents_former_redistribution_dollar_error():
    rates = {"nh": F(10), "spouse": F("1.90"), "child": F(10)}
    weights = {"nh": F(2), "spouse": F(1), "child": F(1)}
    stopped = r.partial_payments(F("9.90"), rates, weights)
    # Literal source stop: cap spouse and retain others' initial shares.
    source_stop = {"nh": F("4.95"), "spouse": F("1.90"), "child": F("2.475")}
    assert stopped == source_stop
    assert stopped.undistributed_subdollar_residual == F("0.575")
    assert sum(int(v) for v in source_stop.values()) == 7
    # The former completed redistribution is an arithmetic diagnostic only;
    # the statutory interface cannot select that prohibited computation.
    former = {"nh": F(16, 3), "spouse": F("1.90"), "child": F(8, 3)}
    assert sum(int(v) for v in former.values()) == 8
    assert not hasattr(r, "SubdollarPolicy")
    assert "subdollar_partial_reapportionment" not in {
        reason.value for reason in r.UnsupportedReason
    }


def test_work_after_known_death_is_invalid_before_coverage_refusal():
    with pytest.raises(r.InvalidFamilyInput, match="after the death"):
        record(
            beneficiary(
                entitled=frozenset(range(1, 6)),
                death_month=6,
                work=earnings(1, month=7),
            ),
            fiscal_year=True,
        )


@pytest.mark.parametrize(
    "make_input",
    [
        lambda: r.WorkEarnings(wages=None),
        lambda: r.WorkEarnings(wages=42),
        lambda: r.WorkEarnings(wages="111111111111"),
        lambda: replace(beneficiary(), benefit_types=None),
        lambda: replace(beneficiary(), gross_rates=None),
        lambda: replace(beneficiary(), original_rates=None),
        lambda: r.RecordYear(YEAR, "nh", beneficiaries=None),
        lambda: r.RecordYear(YEAR, "nh", beneficiaries=42),
        lambda: r.WorkEarnings(nese=Decimal("Infinity")),
    ],
)
def test_invalid_sequences_and_infinite_numbers_are_input_errors(make_input):
    with pytest.raises(r.InvalidFamilyInput):
        make_input()


@pytest.mark.parametrize("benefit_type", [BenefitType.RIB, BenefitType.SPOUSE])
def test_own_work_exempt_flag_requires_a_statutory_benefit_type(benefit_type):
    with pytest.raises(r.InvalidFamilyInput, match="Child or widow"):
        record(
            beneficiary(
                benefit_type=benefit_type,
                own_work_exempt_months={1},
            ),
            fiscal_year=True,
        )


@settings(max_examples=75, deadline=None)
@given(
    st.sampled_from([BenefitType.CHILD, BenefitType.WIDOW]),
    st.frozensets(st.integers(1, 12), max_size=12),
    st.integers(0, 10_000),
)
def test_property_other_statutory_own_exemptions_protect_only_that_workers_excess(
    benefit_type, protected, excess
):
    nh = beneficiary()
    auxiliary = beneficiary(
        "aux",
        benefit_type=benefit_type,
        own_work_exempt_months=protected,
        work=earnings(
            PARAMS.for_year(YEAR).lower_exempt_amount.value + 2 * excess
        ),
    )
    case = (
        r.RecordYear(
            YEAR,
            "deceased",
            kind=r.RecordKind.DECEASED,
            beneficiaries=(auxiliary,),
        )
        if benefit_type is BenefitType.WIDOW
        else record(nh, auxiliary)
    )
    result = r.apply_ret_year(case, PARAMS)
    assert all(
        m.deduction == 0
        for m in result.for_beneficiary("aux")
        if m.month in protected
    )
    assert all(m.deduction == 0 for m in result.for_beneficiary("nh"))
    assert sum(m.deduction for m in result.for_beneficiary("aux")) == min(
        excess, 600 * (12 - len(protected))
    )
    if benefit_type is BenefitType.CHILD:
        # A child's asserted own-work exemption must not protect that
        # child's benefit from the NH's independently chargeable excess.
        nh_worked = replace(
            nh,
            earnings=earnings(
                PARAMS.for_year(YEAR).lower_exempt_amount.value + 2 * excess
            ),
        )
        protected_result = r.apply_ret_year(
            record(nh_worked, auxiliary), PARAMS
        )
        reference = r.apply_ret_year(
            record(
                nh_worked,
                replace(
                    auxiliary,
                    own_work_exempt_months=frozenset(),
                    earnings=earnings(),
                ),
            ),
            PARAMS,
        )
        assert [m.nh_deduction for m in protected_result.months] == [
            m.nh_deduction for m in reference.months
        ]


@pytest.mark.parametrize("benefit_type", [BenefitType.SPOUSE, BenefitType.RIB])
def test_deemed_entitlement_requires_the_acts_child_or_parent_basis(
    benefit_type,
):
    with pytest.raises(r.InvalidFamilyInput, match="Deemed entitlement"):
        beneficiary(
            "deemed",
            benefit_type=benefit_type,
            deemed_entitled=True,
            deemed_married_to_nh=True,
        )


def test_deemed_ordinary_child_requires_explicit_adult_age_facts():
    with pytest.raises(r.InvalidFamilyInput, match="age 18"):
        beneficiary(
            "deemed",
            benefit_type=BenefitType.CHILD,
            deemed_entitled=True,
            deemed_married_to_nh=True,
        )
    adult = beneficiary(
        "deemed",
        rate=200,
        benefit_type=BenefitType.CHILD,
        deemed_entitled=True,
        deemed_married_to_nh=True,
        deemed_child_age_18_months=frozenset(range(1, 13)),
    )
    assert adult.deemed_child_age_18_months == frozenset(range(1, 13))
    with pytest.raises(r.RETConfigurationUnsupported) as error:
        r.apply_ret_year(
            record(beneficiary(rate=400, work=earnings(24_480 + 1200)), adult),
            PARAMS,
        )
    assert error.value.reason is r.UnsupportedReason.DEEMED_ENTITLEMENT_BASIS


def _deemed_cdb_january_counterfactual(nh, recipient, *, broader_poms):
    """Test-only full-January-charge reading on an unrelated CDB record.

    This deliberately narrow harness admits only a positive NH rate and
    enough wage excess to deduct the entire combined January family rate.
    It never changes marriage facts or enables the broader reading through
    the public API. The CDB recipient has no excess of their own.
    """
    assert recipient.deemed_entitled and not recipient.deemed_married_to_nh
    assert set(recipient.benefit_types) == {BenefitType.CDB}
    assert 1 in nh.entitled_months & recipient.entitled_months
    assert recipient.earnings == earnings()
    assert nh.fra_month is None and nh.grace is None
    assert nh.earnings.nese == 0 and nh.gross_rates[0] > 0
    year = PARAMS.for_year(YEAR)
    excess = int(
        max(F(0), sum(nh.earnings.wages) - year.lower_exempt_amount.value)
        * year.lower_withholding_rate.value
    )
    assert excess >= nh.gross_rates[0] + recipient.gross_rates[0]
    # RS 02501.140 puts the other-record CDB rate in the NH's full family
    # deduction. Act 203(b)(1) / CFR .420 leave an unmarried recipient's
    # separate record outside that charge. This is test-only arithmetic.
    nh_deduction = recipient.gross_rates[0] if broader_poms else F(0)
    return recipient.gross_rates[0] - nh_deduction


def test_unmarried_deemed_entitlement_counterfactual_changes_200_dollars():
    """Invented $400/$200 rates and $600 excess, with no real data."""
    assert (
        "is married to an individual entitled to old-age insurance benefits under section 202(a)"
        in source_text("ssa_act_203")
    )
    assert "a person who is married to an old-age insurance beneficiary" in (
        source_text("ecfr_20cfr404_subpart_e")
    )
    assert (
        "deem a retirement beneficiary's spouse or child entitled on their record"
        in source_text("poms_rs_02501_140")
    )
    assert (
        "also to the spouse's or child's benefits that are based on the other ER."
        in source_text("poms_rs_02501_140")
    )
    nh = beneficiary(rate=400, work=earnings(24_480 + 1200))
    recipient = beneficiary(
        "deemed",
        rate=200,
        benefit_type=BenefitType.CDB,
        deemed_entitled=True,
    )
    with pytest.raises(r.RETConfigurationUnsupported) as error:
        r.apply_ret_year(record(nh, recipient), PARAMS)
    assert error.value.reason is r.UnsupportedReason.DEEMED_ENTITLEMENT_BASIS

    married = r.apply_ret_year(
        record(nh, replace(recipient, deemed_married_to_nh=True)), PARAMS
    )
    unrelated = r.apply_ret_year(
        r.RecordYear(
            YEAR,
            "other",
            kind=r.RecordKind.DECEASED,
            beneficiaries=(replace(recipient, deemed_entitled=False),),
        ),
        PARAMS,
    )
    act_cfr_due = _deemed_cdb_january_counterfactual(
        nh, recipient, broader_poms=False
    )
    poms_due = _deemed_cdb_january_counterfactual(
        nh, recipient, broader_poms=True
    )
    married_january = married.for_beneficiary("deemed")[0]
    unrelated_january = unrelated.for_beneficiary("deemed")[0]
    nh_worker = next(w for w in married.workers if w.beneficiary_id == "nh")
    assert nh_worker.excess == nh_worker.charged == 600
    assert married_january.nh_deduction == 200
    assert married_january.own_deduction == 0
    assert act_cfr_due == unrelated_january.net_due == 200
    assert poms_due == married_january.net_due == 0
    assert int(act_cfr_due) - int(poms_due) == 200
    assert unrelated_january.payment == 200
    assert married_january.payment == 0
    assert all(row.deduction == 0 for row in unrelated.months)
    assert sum(row.payment for row in unrelated.months) == 2400
    assert (
        sum(row.payment for row in married.for_beneficiary("deemed")) == 2200
    )


@settings(max_examples=50, deadline=None)
@given(st.integers(1, 2000), st.integers(1, 2000))
def test_property_deemed_counterfactual_matches_full_married_charge(
    nh_rate, cdb_rate
):
    """Independent reading harness and married ledger agree exactly.

    Shared surface: whole-dollar RIB/CDB rates, no other excess/protection,
    and NH excess equal to the combined January rate. Tolerance is zero.
    The Act/CFR counterfactual always preserves the unrelated CDB rate;
    the public API always retains the unmarried source-conflict refusal.
    """
    family_rate = nh_rate + cdb_rate
    nh = beneficiary(
        rate=nh_rate,
        work=earnings(
            PARAMS.for_year(YEAR).lower_exempt_amount.value + 2 * family_rate
        ),
    )
    recipient = beneficiary(
        "deemed",
        rate=cdb_rate,
        benefit_type=BenefitType.CDB,
        deemed_entitled=True,
    )
    with pytest.raises(r.RETConfigurationUnsupported) as error:
        r.apply_ret_year(record(nh, recipient), PARAMS)
    assert error.value.reason is r.UnsupportedReason.DEEMED_ENTITLEMENT_BASIS
    married = r.apply_ret_year(
        record(nh, replace(recipient, deemed_married_to_nh=True)), PARAMS
    )
    unrelated = r.apply_ret_year(
        r.RecordYear(
            YEAR,
            "other",
            kind=r.RecordKind.DECEASED,
            beneficiaries=(replace(recipient, deemed_entitled=False),),
        ),
        PARAMS,
    )
    january = married.for_beneficiary("deemed")[0]
    assert (
        _deemed_cdb_january_counterfactual(nh, recipient, broader_poms=True)
        == january.net_due
        == 0
    )
    assert january.nh_deduction == cdb_rate
    assert january.own_deduction == 0
    assert (
        _deemed_cdb_january_counterfactual(nh, recipient, broader_poms=False)
        == unrelated.for_beneficiary("deemed")[0].net_due
        == cdb_rate
    )
    assert all(row.deduction == 0 for row in unrelated.months)


def test_deemed_entitlement_requires_a_different_rib_number_holder():
    deemed = beneficiary(
        "deemed",
        benefit_type=BenefitType.CDB,
        deemed_entitled=True,
        deemed_married_to_nh=True,
    )
    with pytest.raises(r.InvalidFamilyInput, match="NH's RIB"):
        record(beneficiary(benefit_type=BenefitType.DIB), deemed)


def test_missing_supported_year_is_not_hidden_by_a_coverage_refusal():
    with pytest.raises(KeyError):
        r.apply_ret_year(record(year=2027, fiscal_year=True), PARAMS)


@pytest.mark.parametrize(
    "benefit_type", [BenefitType.CHILD, BenefitType.WIDOW]
)
def test_optional_act_age_exemptions_are_an_explicit_600_dollar_reading(
    benefit_type,
):
    person = beneficiary(
        "aux",
        rate=200,
        benefit_type=benefit_type,
        work=earnings(PARAMS.for_year(YEAR).lower_exempt_amount.value + 1200),
    )

    def case(person):
        return (
            r.RecordYear(
                YEAR,
                "deceased",
                kind=r.RecordKind.DECEASED,
                beneficiaries=(person,),
            )
            if benefit_type is BenefitType.WIDOW
            else record(beneficiary(), person)
        )

    conservative = r.apply_ret_year(case(person), PARAMS)
    act = r.apply_ret_year(
        case(replace(person, own_work_exempt_months=frozenset(range(1, 13)))),
        PARAMS,
    )
    assert sum(m.deduction for m in conservative.months) == 600
    assert sum(m.deduction for m in act.months) == 0
    assert (
        sum(m.payment for m in act.months)
        - sum(m.payment for m in conservative.months)
        == 600
    )
