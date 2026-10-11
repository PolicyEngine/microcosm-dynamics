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


def test_subdollar_stop_and_complete_reading_can_change_a_check_by_one_dollar():
    rates = {"nh": F(10), "spouse": F("1.90"), "child": F(10)}
    weights = {"nh": F(2), "spouse": F(1), "child": F(1)}
    with pytest.raises(r.RETConfigurationUnsupported) as error:
        r.partial_payments(F("9.90"), rates, weights)
    assert error.value.reason is r.UnsupportedReason.SUBDOLLAR_REAPPORTIONMENT
    complete = r.partial_payments(
        F("9.90"),
        rates,
        weights,
        subdollar_policy=r.SubdollarPolicy.COMPLETE_REAPPORTIONMENT,
    )
    assert complete == {"nh": F(16, 3), "spouse": F("1.90"), "child": F(8, 3)}
    # Literal source stop: cap spouse and retain others' initial shares.
    source_stop = {"nh": F("4.95"), "spouse": F("1.90"), "child": F("2.475")}
    assert sum(int(v) for v in source_stop.values()) == 7
    assert sum(int(v) for v in complete.values()) == 8


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
