"""R3 statutory ARF examples and boundaries; invented or published inputs.

Verification class: statutory conformance. These cases admit ARF credit
and rounding mechanics only, without population or behavioral claims.
Published figures are checked against locally captured SSA text.
"""

from dataclasses import replace
from datetime import date
from fractions import Fraction as F

import pytest

from populace_dynamics.track_b import arf as a
from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import ssa_params

PARAMS = ssa_params()
FRA = g.YearMonth(2027, 1)


def months(first, count):
    """Generate invented final deduction months, independently of ARF."""
    index = first.year * 12 + first.month - 1
    return frozenset(
        g.YearMonth((index + i) // 12, (index + i) % 12 + 1)
        for i in range(count)
    )


def rib_claim(**kwargs):
    values = dict(
        kind=a.ARFBenefitKind.RIB,
        birth_date=date(1960, 1, 2),
        first_reduction_month=g.YearMonth(2022, 1),
        unreduced_benefit=F(1300),
    )
    values.update(kwargs)
    return a.ARFClaim(**values)


@pytest.mark.parametrize("credits,expected", [(0, 910), (12, 975), (60, 1300)])
def test_publication_05_10069_worked_example(credits, expected):
    """SSA: PIA1300,60 RF;0/12/60credits give910/975/1300 exactly.

    60 RF reduction =36*5/900+24*5/1200=3/10;1300*(7/10)=910.
    48 RF reduction =36*5/900+12*5/1200=1/4;1300*(3/4)=975.
    Zero remaining RF pays1300. Figures are today's dollars, without COLA.
    """
    claim = rib_claim(
        full_work_deduction_months=months(g.YearMonth(2022, 1), credits)
    )
    result = a.apply_arf(claim, payment_month=FRA, params=PARAMS)
    assert result.original_reduction_months == 60
    assert result.adjusted_reduction_months == 60 - credits
    assert result.benefit == F(expected)
    assert result.whole_dollar_benefit == expected


def test_partial_work_deduction_is_a_full_crediting_month():
    one = frozenset({g.YearMonth(2022, 1)})
    full = a.apply_arf(
        rib_claim(full_work_deduction_months=one),
        payment_month=FRA,
        params=PARAMS,
    )
    partial = a.apply_arf(
        rib_claim(partial_work_deduction_months=one),
        payment_month=FRA,
        params=PARAMS,
    )
    assert partial.adjusted_reduction_months == 59
    assert partial.benefit == full.benefit == F("915.4")
    assert partial.crediting_months == one


def test_rib_simultaneous_dib_entitlement_is_an_independent_crediting_month():
    """Invented q7F:60RF minus1 simultaneousDIB month gives59RF.

    36*5/900+23*5/1200=71/240;1300*71/240=384.58333...,
    reduction rounds up384.6;hypothetical RIB is915.4.
    There is no work deduction in this case.
    """
    one = frozenset({g.YearMonth(2022, 1)})
    result = a.apply_arf(
        rib_claim(simultaneous_dib_months=one),
        payment_month=FRA,
        params=PARAMS,
    )
    assert result.crediting_months == one
    assert result.adjusted_reduction_months == 59
    assert result.reduction == F("384.6")
    assert result.benefit == F("915.4")


def test_overlapping_categories_credit_a_month_once_and_ignore_outside_window():
    first = g.YearMonth(2022, 1)
    inside = first
    outside = {g.YearMonth(2021, 12), FRA, g.YearMonth(2027, 2)}
    result = a.apply_arf(
        rib_claim(
            full_work_deduction_months={inside, *outside},
            partial_work_deduction_months={inside},
            simultaneous_dib_months={inside},
        ),
        payment_month=FRA,
        params=PARAMS,
    )
    assert result.crediting_months == frozenset({inside})
    assert result.adjusted_reduction_months == 59


@pytest.mark.parametrize(
    "birth,kind,expected",
    [
        (date(1963, 3, 1), a.ARFBenefitKind.RIB, (2030, 2)),
        (date(1963, 3, 2), a.ARFBenefitKind.RIB, (2030, 3)),
        (date(1963, 3, 31), a.ARFBenefitKind.RIB, (2030, 3)),
        (date(1960, 1, 1), a.ARFBenefitKind.RIB, (2026, 10)),
        (date(1960, 1, 2), a.ARFBenefitKind.RIB, (2027, 1)),
        (date(1962, 1, 1), a.ARFBenefitKind.WIDOW, (2028, 10)),
        (date(1962, 1, 2), a.ARFBenefitKind.WIDOW, (2029, 1)),
    ],
)
def test_birthday_fra_boundaries_use_day_before_and_january_cohort(
    birth, kind, expected
):
    assert (
        a.full_retirement_age_month(birth, kind, PARAMS).as_tuple() == expected
    )


def test_first_day_birthday_adjustment_is_not_one_month_early():
    claim = rib_claim(
        birth_date=date(1963, 3, 1),
        first_reduction_month=(2025, 3),
        partial_work_deduction_months={(2025, 3)},
    )
    before = a.apply_arf(claim, payment_month=(2030, 1), params=PARAMS)
    at = a.apply_arf(claim, payment_month=(2030, 2), params=PARAMS)
    assert before.fra_month == at.fra_month == g.YearMonth(2030, 2)
    assert before.adjusted_reduction_months == 59
    assert before.crediting_months == frozenset()
    assert at.adjusted_reduction_months == 58
    assert at.benefit > before.benefit


@pytest.mark.parametrize(
    "kind,birth,first,expected_reduction,expected_benefit",
    [
        (a.ARFBenefitKind.RIB, date(1960, 1, 2), (2026, 12), "5.6", "994.4"),
        (
            a.ARFBenefitKind.SPOUSE,
            date(1960, 1, 2),
            (2026, 12),
            "7.0",
            "993.0",
        ),
        (a.ARFBenefitKind.WIDOW, date(1962, 1, 2), (2028, 12), "3.4", "996.6"),
    ],
)
def test_reduction_rounds_up_to_dime_after_exact_fraction(
    kind, birth, first, expected_reduction, expected_benefit
):
    claim = a.ARFClaim(kind, birth, first, F(1000))
    at = a.full_retirement_age_month(birth, kind, PARAMS)
    result = a.apply_arf(claim, payment_month=at, params=PARAMS)
    assert result.reduction == F(expected_reduction)
    assert result.benefit == F(expected_benefit)


def test_widow_age62_credits_persist_and_later_credits_wait_for_fra():
    """Invented:84 RF,PIA1000;credits1 before62 and1 after62.

    At62,83 RF: reduction1000*.285*83/84=281.607142...,ceil281.7,
    benefit718.3. AtFRA82 RF:278.214285...,ceil278.3,benefit721.7.
    """
    claim = a.ARFClaim(
        a.ARFBenefitKind.WIDOW,
        date(1962, 1, 2),
        (2022, 1),
        F(1000),
        partial_work_deduction_months={(2022, 1), (2024, 2)},
    )
    before = a.apply_arf(claim, payment_month=(2023, 12), params=PARAMS)
    age62 = a.apply_arf(claim, payment_month=(2024, 1), params=PARAMS)
    later = a.apply_arf(claim, payment_month=(2028, 12), params=PARAMS)
    fra = a.apply_arf(claim, payment_month=(2029, 1), params=PARAMS)
    assert before.adjusted_reduction_months == 84
    assert before.benefit == F(715)
    assert (
        age62.adjusted_reduction_months
        == later.adjusted_reduction_months
        == 83
    )
    assert age62.benefit == later.benefit == F("718.3")
    assert fra.adjusted_reduction_months == 82
    assert fra.benefit == F("721.7")


def test_spouse_child_in_care_and_termination_months_are_credits_at_fra():
    claim = a.ARFClaim(
        a.ARFBenefitKind.SPOUSE,
        date(1960, 1, 2),
        (2022, 1),
        F(650),
        child_in_care_months={(2022, 1)},
        nonentitlement_months={(2022, 2)},
    )
    result = a.apply_arf(claim, payment_month=FRA, params=PARAMS)
    assert result.adjusted_reduction_months == 58
    assert result.benefit == F("427.9")


def test_widow_mother_father_rate_and_termination_months_are_credits():
    claim = a.ARFClaim(
        a.ARFBenefitKind.WIDOW,
        date(1962, 1, 2),
        (2022, 1),
        F(1000),
        mother_father_rate_months={(2022, 1)},
        nonentitlement_months={(2022, 2)},
    )
    result = a.apply_arf(claim, payment_month=(2029, 1), params=PARAMS)
    assert result.adjusted_reduction_months == 82
    assert result.benefit == F("721.7")


def test_spouse_dual_concurrent_or_preceding_reduces_only_excess():
    """Invented:.500 excess650-200=450;48 RF,rate.3 gives315.

    Own independently adjusted RIB160 is separate; together475 before
    whole-dollar rounding each component. Crediting sets are per record.
    """
    claim = a.ARFClaim(
        a.ARFBenefitKind.SPOUSE,
        date(1960, 1, 2),
        (2022, 1),
        F(650),
        full_work_deduction_months=months(g.YearMonth(2022, 1), 12),
        spouse_own=a.SpouseOwnBenefit(
            F(200), F(160), a.SpouseOwnSequence.CONCURRENT_OR_PRECEDING
        ),
    )
    result = a.apply_arf(claim, payment_month=FRA, params=PARAMS)
    assert result.adjusted_reduction_months == 48
    assert result.benefit == F(315)
    assert result.benefit + claim.spouse_own.payable == F(475)


def test_own_entitlement_after_spouse_arf_preserves_spouse_adjustment():
    """Invented:.500A.1,650 at48RF=>455;new ownRIB200=>excess255."""
    claim = a.ARFClaim(
        a.ARFBenefitKind.SPOUSE,
        date(1960, 1, 2),
        (2022, 1),
        F(650),
        full_work_deduction_months=months(g.YearMonth(2022, 1), 12),
        spouse_own=a.SpouseOwnBenefit(
            F(200), F(200), a.SpouseOwnSequence.AFTER_SPOUSE_ARF
        ),
    )
    result = a.apply_arf(claim, payment_month=(2027, 2), params=PARAMS)
    assert result.benefit == F(255)


@pytest.mark.parametrize(
    "kind,first",
    [
        (a.ARFBenefitKind.RIB, (2021, 12)),
        (a.ARFBenefitKind.SPOUSE, (2021, 12)),
        (a.ARFBenefitKind.WIDOW, (1990, 1)),
    ],
)
def test_disabled_widow_flag_does_not_hide_invalid_minimum_age(kind, first):
    """Executed minimized counterexamples:age61y11m RIB,age30 widow."""
    claim = a.ARFClaim(
        kind,
        date(1960, 1, 2),
        first,
        F(1000),
        conditions={a.ARFUnsupportedReason.DISABLED_WIDOW},
    )
    with pytest.raises(g.InvalidFamilyInput):
        a.apply_arf(claim, payment_month=(2027, 1), params=PARAMS)


def test_valid_disabled_widow_at_age50_is_refused_as_coverage():
    claim = a.ARFClaim(
        a.ARFBenefitKind.WIDOW,
        date(1960, 1, 2),
        (2010, 1),
        F(1000),
        conditions={a.ARFUnsupportedReason.DISABLED_WIDOW},
    )
    with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
        a.apply_arf(claim, payment_month=(2027, 1), params=PARAMS)
    assert caught.value.reason is a.ARFUnsupportedReason.DISABLED_WIDOW


def test_deceased_numberholder_waits_until_hypothetical_fra_and_credits_alive_months():
    claim = rib_claim(
        death_date=date(2023, 4, 15),
        full_work_deduction_months={(2023, 3), (2023, 4), (2023, 5)},
    )
    before = a.apply_arf(claim, payment_month=(2026, 12), params=PARAMS)
    result = a.apply_arf(claim, payment_month=FRA, params=PARAMS)
    assert before.crediting_months == frozenset()
    assert before.benefit == F(910)
    assert result.crediting_months == frozenset({g.YearMonth(2023, 3)})
    assert result.benefit == F("915.4")


@pytest.mark.parametrize("reason", list(a.ARFUnsupportedReason))
def test_explicit_exceptional_history_is_refused_by_name(reason):
    with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
        a.apply_arf(
            rib_claim(conditions={reason}), payment_month=FRA, params=PARAMS
        )
    assert caught.value.code == "FAMILY_CONFIG_UNSUPPORTED"
    assert caught.value.reason is reason


def test_spouse_reentitlement_before_fra_is_explicitly_refused():
    claim = a.ARFClaim(
        a.ARFBenefitKind.SPOUSE,
        date(1960, 1, 2),
        (2022, 1),
        F(650),
        nonentitlement_months={(2022, 2)},
        conditions={a.ARFUnsupportedReason.SPOUSE_REENTITLEMENT_BEFORE_FRA},
    )
    with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
        a.apply_arf(claim, payment_month=(2024, 1), params=PARAMS)
    assert (
        caught.value.reason
        is a.ARFUnsupportedReason.SPOUSE_REENTITLEMENT_BEFORE_FRA
    )


def test_spouse_reentitlement_before_fra_is_detected_from_termination_history():
    claim = a.ARFClaim(
        a.ARFBenefitKind.SPOUSE,
        date(1960, 1, 2),
        (2022, 1),
        F(650),
        nonentitlement_months={(2022, 2)},
    )
    with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
        a.apply_arf(claim, payment_month=(2024, 1), params=PARAMS)
    assert (
        caught.value.reason
        is a.ARFUnsupportedReason.SPOUSE_REENTITLEMENT_BEFORE_FRA
    )
    # The same known history has a settled final adjustment at FRA.
    result = a.apply_arf(claim, payment_month=FRA, params=PARAMS)
    assert result.adjusted_reduction_months == 59


def test_dual_spouse_after_spouse_before_arf_is_refused():
    claim = a.ARFClaim(
        a.ARFBenefitKind.SPOUSE,
        date(1960, 1, 2),
        (2022, 1),
        F(650),
        spouse_own=a.SpouseOwnBenefit(
            F(200), F(160), a.SpouseOwnSequence.AFTER_SPOUSE_BEFORE_ARF
        ),
    )
    with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
        a.apply_arf(claim, payment_month=FRA, params=PARAMS)
    assert (
        caught.value.reason
        is a.ARFUnsupportedReason.SPOUSE_OWN_AFTER_SPOUSE_BEFORE_ARF
    )


def test_historic_survivor_fra_conflict_is_refused():
    claim = a.ARFClaim(
        a.ARFBenefitKind.WIDOW, date(1911, 1, 2), (1972, 1), F(1000)
    )
    with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
        a.apply_arf(claim, payment_month=(1983, 1), params=PARAMS)
    assert (
        caught.value.reason
        is a.ARFUnsupportedReason.HISTORICAL_WIDOW_FRA_CONFLICT
    )
    with pytest.raises(g.FamilyConfigurationUnsupported) as calendar_error:
        a.full_retirement_age_month(
            date(1911, 1, 2), a.ARFBenefitKind.WIDOW, PARAMS
        )
    assert (
        calendar_error.value.reason
        is a.ARFUnsupportedReason.HISTORICAL_WIDOW_FRA_CONFLICT
    )
    # Invented counterfactual: first1/1973,36/60 RF gives829 under
    # POMS FRA65; CFR FRA62 gives1000. Neither reading is paid by R3.
    assert g.survivor_age_reduced(F(1000), 36, 60, PARAMS) == F(829)
    assert F(1000) - F(829) == F(171)


def test_widow_nonbinding_child_care_readings_are_explicit():
    """Invented q7D/CFR.412(a)(4) conflict:1000PIA,36 RF,6 care months.

    Without the mother/father floor binding:1000-.285*36/84=877.8
    after ceil-dime reduction. Categorical care credits give30RF:898.2.
    This20.4 difference is not silently selected by the adapter.
    """
    claim = a.ARFClaim(
        a.ARFBenefitKind.WIDOW, date(1962, 3, 2), (2026, 3), F(1000)
    )
    no_credit = a.apply_arf(claim, payment_month=(2029, 3), params=PARAMS)
    assert no_credit.benefit == F("877.8")
    with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
        a.apply_arf(
            replace(
                claim,
                conditions={
                    a.ARFUnsupportedReason.WIDOW_CHILD_CARE_WITHOUT_RATE_INCREASE
                },
            ),
            payment_month=(2029, 3),
            params=PARAMS,
        )
    assert (
        caught.value.reason
        is a.ARFUnsupportedReason.WIDOW_CHILD_CARE_WITHOUT_RATE_INCREASE
    )
    alternative = g.survivor_age_reduced(F(1000), 30, 84, PARAMS)
    assert alternative == F("898.2")
    assert alternative - no_credit.benefit == F("20.4")


@pytest.mark.parametrize(
    "change",
    [
        dict(unreduced_benefit=F(-1)),
        dict(unreduced_benefit=F("1.01")),
        dict(unreduced_benefit=1000.0),
        dict(full_work_deduction_months={(2022, 13)}),
        dict(child_in_care_months={(2022, 1)}),
        dict(first_reduction_month=(2021, 12)),
        dict(first_reduction_month=(2027, 2)),
        dict(death_date=date(1950, 1, 1)),
        dict(conditions={"not a reason"}),
    ],
)
def test_invalid_input_precedes_coverage_refusal(change):
    claim = rib_claim(
        conditions={a.ARFUnsupportedReason.OTHER_SUSPENSION},
        **{k: v for k, v in change.items() if k != "conditions"},
    )
    if "conditions" in change:
        claim = replace(claim, **change)
    with pytest.raises(g.InvalidFamilyInput):
        a.apply_arf(claim, payment_month=FRA, params=PARAMS)


def test_refusals_remain_in_weighted_denominator_and_invalid_rows_raise():
    supported = a.evaluate_arf(
        "supported",
        F(2),
        lambda: a.apply_arf(rib_claim(), payment_month=FRA, params=PARAMS),
    )
    refused = a.evaluate_arf(
        "refused",
        F(3),
        lambda: a.apply_arf(
            rib_claim(conditions={a.ARFUnsupportedReason.OTHER_SUSPENSION}),
            payment_month=FRA,
            params=PARAMS,
        ),
    )
    denominator = a.count_arf_outcomes([supported, refused])
    assert denominator.rows == 2
    assert denominator.weight == 5
    assert denominator.supported_weight_share == F(2, 5)
    assert denominator.unsupported_by_reason[
        a.ARFUnsupportedReason.OTHER_SUSPENSION
    ] == (1, F(3))
    with pytest.raises(g.InvalidFamilyInput):
        a.evaluate_arf(
            "invalid",
            F(1),
            lambda: a.apply_arf(
                rib_claim(unreduced_benefit=-1),
                payment_month=FRA,
                params=PARAMS,
            ),
        )


# .015 source figures are whole-dollar payments; dime intermediate values
# below are independently reproduced with 402(q)'s exact Fraction rates.
BIRTHDAY_EXAMPLES = [
    (date(1935, 5, 31), (1997, 6), 1207, 35, "972.3", 972),
    (date(1935, 6, 1), (1997, 6), 1207, 35, "972.3", 972),
    (date(1935, 6, 2), (1997, 6), 1207, 36, "965.6", 965),
    (date(1935, 6, 3), (1997, 7), 1207, 35, "972.3", 972),
    (date(1935, 12, 31), (1998, 1), 1232, 35, "992.4", 992),
    (date(1936, 1, 1), (1998, 1), 1232, 35, "992.4", 992),
    (date(1936, 1, 2), (1998, 1), 1266, 36, "1012.8", 1012),
    (date(1936, 1, 3), (1998, 2), 1266, 35, "1019.8", 1019),
    (date(1937, 12, 31), (2000, 1), 1372, 35, "1105.2", 1105),
    (date(1938, 1, 1), (2000, 1), 1372, 35, "1105.2", 1105),
    (date(1938, 1, 2), (2000, 1), 1410, 38, "1116.2", 1116),
    (date(1938, 1, 3), (2000, 2), 1410, 37, "1122.1", 1122),
]


@pytest.mark.parametrize("birth,first,pia,rf,dimes,payment", BIRTHDAY_EXAMPLES)
def test_poms_00615_015_birthday_worked_examples(
    birth, first, pia, rf, dimes, payment
):
    claim = a.ARFClaim(a.ARFBenefitKind.RIB, birth, first, F(pia))
    result = a.apply_arf(claim, payment_month=first, params=PARAMS)
    assert result.original_reduction_months == rf
    assert result.benefit == F(dimes)
    assert result.whole_dollar_benefit == payment


def test_worked_example_figures_are_quoted_from_the_captures():
    from tests.track_b_arf_recompute_support import source_text

    publication = source_text("ssa_pub_05_10069_arf_recompute_excerpts")
    for figure in ("$910", "12 months", "67", "$975", "$1,300", "62", "2026"):
        assert figure in publication
    birthdays = source_text("poms_rs_00615_015")
    for figure in (
        "$1207",
        "$972",
        "$965",
        "$1232",
        "$1266",
        "$992",
        "$1012",
        "$1019",
        "$1372",
        "$1410",
        "$1105",
        "$1116",
        "$1122",
        "35",
        "36",
        "37",
        "38",
    ):
        assert figure in birthdays


def test_poms_00615_015_date_erratum_is_pinned_against_correct_table():
    from tests.track_b_arf_recompute_support import source_text

    text = source_text("poms_rs_00615_015")
    assert "In 2/1998 Demi has 37 RF." in text
    assert "Demi - $1122 starting 2/2000" in text
    # Correct chronology is the captured example's benefit date and table.
    claim = a.ARFClaim(
        a.ARFBenefitKind.RIB, date(1938, 1, 3), (2000, 2), F(1410)
    )
    assert (
        a.apply_arf(
            claim, payment_month=(2000, 2), params=PARAMS
        ).original_reduction_months
        == 37
    )
