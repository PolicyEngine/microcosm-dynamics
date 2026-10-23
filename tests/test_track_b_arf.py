"""R3 statutory ARF examples and boundaries; invented or published inputs.

Verification class: statutory conformance. These cases admit ARF credit
and rounding mechanics only, without population or behavioral claims.
Published figures are checked against locally captured SSA text.
"""

from dataclasses import replace
from datetime import date
from decimal import Decimal
from fractions import Fraction as F

import pytest

from populace_dynamics.track_b import arf as a
from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import ssa_params

PARAMS = ssa_params()
FRA = g.YearMonth(2027, 1)

INVALID_RIB_PARAMETERS = [
    pytest.param(
        {"early_first_bracket_months": 35},
        "early_first_bracket_months must be 36 (402(q))",
        id="bracket",
    ),
    pytest.param(
        {"early_monthly_rates": (0, 0.00416667)},
        "Parameter bundle early_monthly_rates[0]=0 disagrees with the "
        "statutory 1/180; refusing to compute gross benefits.",
        id="first-rate",
    ),
    pytest.param(
        {"early_monthly_rates": (0.00555556, 0)},
        "Parameter bundle early_monthly_rates[1]=0 disagrees with the "
        "statutory 1/240; refusing to compute gross benefits.",
        id="later-rate",
    ),
]

# Every scalar in the complete shared bundle read by G's statutory_rates.
# ARF validates this bundle for each record kind before any coverage rule.
STATUTORY_RATE_FIELDS = (
    ("early_monthly_rates", 0),
    ("early_monthly_rates", 1),
    ("early_first_bracket_months", None),
    ("spousal_early_monthly_rates", 0),
    ("spousal_early_monthly_rates", 1),
    ("spousal_early_first_bracket_months", None),
    ("survivor_reduction_floor", None),
    ("rib_lim_pia_share", None),
    ("spousal_pia_share", None),
    ("survivor_pia_share", None),
)


def nonfinite_statutory_params(field, index, value):
    """Replace one scalar while retaining every other statutory value."""
    if index is None:
        replacement = value
    else:
        replacement = list(getattr(PARAMS, field))
        replacement[index] = value
        replacement = tuple(replacement)
    return ssa_params(**{field: replacement})


def statutory_validation_claim(kind, coverage, amount=F(1300)):
    """Valid invented claims, including a condition-free coverage refusal."""
    claim = a.ARFClaim(kind, date(1960, 1, 2), (2022, 1), amount)
    payment = FRA
    if coverage == "explicit":
        claim = replace(
            claim, conditions=(a.ARFUnsupportedReason.OTHER_SUSPENSION,)
        )
    elif coverage == "automatic":
        # All three kinds validly reach INITIAL_ENTITLEMENT_BEFORE_1978.
        claim = replace(
            claim,
            birth_date=date(1915, 1, 2),
            first_reduction_month=(1977, 1),
        )
        payment = g.YearMonth(1983, 1)
    return claim, payment


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


def test_original_claim_collection_credit_survives_repeated_application():
    """Reviewer counterexample: one credit always pays $915.40/$915."""
    claim = rib_claim(full_work_deduction_months=list([(2022, 1)]))
    first = a.apply_arf(claim, payment_month=FRA, params=PARAMS)
    second = a.apply_arf(claim, payment_month=FRA, params=PARAMS)
    assert first.adjusted_reduction_months == 59
    assert first.benefit == F("915.4")
    assert first.whole_dollar_benefit == 915
    assert second == first


def test_original_claim_collection_refusal_survives_repeated_evaluation():
    """Reviewer counterexample: evaluating a refusal never erases it."""
    claim = rib_claim(
        conditions=list([a.ARFUnsupportedReason.OTHER_SUSPENSION])
    )
    outcomes = [
        a.evaluate_arf(
            key,
            F(1),
            lambda: a.apply_arf(claim, payment_month=FRA, params=PARAMS),
        )
        for key in ("left", "right")
    ]
    for outcome in outcomes:
        assert not outcome.supported
        assert (
            outcome.unsupported.reason
            is a.ARFUnsupportedReason.OTHER_SUSPENSION
        )
    denominator = a.count_arf_outcomes(outcomes)
    assert denominator.rows == denominator.unsupported_rows == 2
    assert denominator.weight == denominator.unsupported_weight == 2


@pytest.mark.parametrize(
    "kind,field",
    [
        (a.ARFBenefitKind.RIB, "full_work_deduction_months"),
        (a.ARFBenefitKind.RIB, "partial_work_deduction_months"),
        (a.ARFBenefitKind.SPOUSE, "child_in_care_months"),
        (a.ARFBenefitKind.SPOUSE, "nonentitlement_months"),
        (a.ARFBenefitKind.RIB, "simultaneous_dib_months"),
        (a.ARFBenefitKind.WIDOW, "mother_father_rate_months"),
    ],
)
def test_every_collection_credit_field_is_stable_for_supported_and_refused_claims(
    kind, field
):
    for refused in (False, True):
        claim = rib_claim(
            kind=kind,
            **{field: list([(2022, 1)])},
            conditions=list(
                [a.ARFUnsupportedReason.OTHER_SUSPENSION] if refused else []
            ),
        )

        def compute(claim=claim):
            return a.apply_arf(claim, payment_month=FRA, params=PARAMS)

        first = a.evaluate_arf("same", F(1), compute)
        second = a.evaluate_arf("same", F(1), compute)
        assert second.supported == first.supported == (not refused)
        if refused:
            assert second.unsupported.reason is first.unsupported.reason
        else:
            assert second.benefits == first.benefits
            assert first.benefits.crediting_months == frozenset(
                {g.YearMonth(2022, 1)}
            )
            assert first.benefits.adjusted_reduction_months == (
                first.benefits.original_reduction_months - 1
            )
        assert isinstance(getattr(claim, field), (tuple, frozenset))
        assert isinstance(claim.conditions, (tuple, frozenset))


def test_collection_inputs_are_snapshotted_before_caller_mutation():
    credits = list([(2022, 1)])
    conditions = list([a.ARFUnsupportedReason.OTHER_SUSPENSION])
    claim = rib_claim(
        full_work_deduction_months=credits, conditions=conditions
    )
    credits.clear()
    conditions.clear()
    assert credits == conditions == []
    with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
        a.apply_arf(claim, payment_month=FRA, params=PARAMS)
    assert caught.value.reason is a.ARFUnsupportedReason.OTHER_SUSPENSION
    supported = a.apply_arf(
        replace(claim, conditions=()), payment_month=FRA, params=PARAMS
    )
    assert supported.benefit == F("915.4")


def test_result_collection_credits_are_immutable_and_survive_inspection():
    result = a.apply_arf(
        rib_claim(full_work_deduction_months={(2022, 1)}),
        payment_month=FRA,
        params=PARAMS,
    )
    direct = a.apply_arf(
        replace(
            result.claim,
            full_work_deduction_months=list(result.crediting_months),
        ),
        payment_month=FRA,
        params=PARAMS,
    )
    assert direct == result
    assert frozenset(direct.crediting_months) == result.crediting_months
    assert frozenset(direct.crediting_months) == result.crediting_months


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
    "unreduced,own_pia,own_payable,expected,whole_dollars",
    [
        (F("26.2"), F(15), F("15.1"), F("1.9"), 1),
        (F(650), F(200), F(208), F("214.5"), 214),
    ],
)
def test_own_entitlement_after_spouse_arf_offsets_own_payable_not_pia(
    unreduced, own_pia, own_payable, expected, whole_dollars
):
    """Invented reviewer cases: separately adjusted own RIB changes money.

    At 60 RF the single spouse rates are $17.00 and $422.50. The supplied
    own payments, $15.10 and $208.00, leave $1.90/$1 and $214.50/$214.
    RS 00615.500A.1 preserves the spouse ARF before this own offset.
    """
    claim = a.ARFClaim(
        a.ARFBenefitKind.SPOUSE,
        date(1960, 1, 2),
        (2022, 1),
        unreduced,
        spouse_own=a.SpouseOwnBenefit(
            own_pia, own_payable, a.SpouseOwnSequence.AFTER_SPOUSE_ARF
        ),
    )
    result = a.apply_arf(claim, payment_month=(2028, 1), params=PARAMS)
    assert result.adjusted_reduction_months == 60
    assert result.benefit == expected
    assert result.whole_dollar_benefit == whole_dollars
    assert (
        a.apply_arf(result, payment_month=(2028, 1), params=PARAMS) == result
    )


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


def test_spouse_reentitled_before_fra_keeps_original_months_until_fra():
    """402(q)(1)(B): only the 62 and FRA months use the adjusted period.

    Source conflict us:oasdi-arf-spouse-reentitlement-credits. Invented
    1960-01-02 spouse, $650 unreduced, first reduced 2022-01, terminated
    2022-02 and reentitled 2022-03. Every month before FRA keeps the 60
    original months (35 percent, $422.50); the January 2027 ARF removes
    the terminated month (59 months, reduction $224.80, $425.20).
    """
    claim = a.ARFClaim(
        a.ARFBenefitKind.SPOUSE,
        date(1960, 1, 2),
        (2022, 1),
        F(650),
        nonentitlement_months={(2022, 2)},
    )
    plain = replace(claim, nonentitlement_months=frozenset())
    for payment in ((2022, 3), (2024, 1), (2026, 12)):
        result = a.apply_arf(claim, payment_month=payment, params=PARAMS)
        assert result.crediting_months == frozenset()
        assert result.effective_adjustment_month is None
        assert result.original_reduction_months == 60
        assert result.adjusted_reduction_months == 60
        assert result.benefit == F("422.50")
        assert (
            result.benefit
            == a.apply_arf(plain, payment_month=payment, params=PARAMS).benefit
        )
    result = a.apply_arf(claim, payment_month=FRA, params=PARAMS)
    assert result.adjusted_reduction_months == 59
    assert result.crediting_months == frozenset({g.YearMonth(2022, 2)})
    assert result.benefit == F("425.20")


def test_spouse_reentitlement_is_no_longer_a_coverage_reason():
    """The settled timing leaves no named refusal to declare."""
    values = {reason.value for reason in a.ARFUnsupportedReason}
    assert "arf_spouse_reentitlement_before_fra" not in values


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
    # Intrinsic declaration errors now reject during construction; cohort
    # checks still require apply_arf. The same invalid values must raise.
    with pytest.raises(g.InvalidFamilyInput):
        claim = rib_claim(
            conditions={a.ARFUnsupportedReason.OTHER_SUSPENSION},
            **{k: v for k, v in change.items() if k != "conditions"},
        )
        if "conditions" in change:
            claim = replace(claim, **change)
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


@pytest.mark.parametrize("overrides,message", INVALID_RIB_PARAMETERS)
@pytest.mark.parametrize("entrypoint", ["apply", "evaluate", "count"])
@pytest.mark.parametrize(
    "claim,payment",
    [
        pytest.param(
            rib_claim(first_reduction_month=(2027, 1), unreduced_benefit=F(0)),
            FRA,
            id="ordinary-zero-rf",
        ),
        pytest.param(
            rib_claim(
                first_reduction_month=(2027, 1),
                unreduced_benefit=F(0),
                conditions=list([a.ARFUnsupportedReason.OTHER_SUSPENSION]),
            ),
            FRA,
            id="explicit-suspension-zero-rf",
        ),
        pytest.param(
            rib_claim(
                birth_date=date(1915, 1, 2),
                first_reduction_month=(1977, 1),
                unreduced_benefit=F(0),
            ),
            (1983, 1),
            id="automatic-historical-entitlement",
        ),
        pytest.param(
            rib_claim(
                birth_date=date(1920, 1, 2),
                first_reduction_month=(1982, 1),
                unreduced_benefit=F(0),
            ),
            (1982, 1),
            id="automatic-historical-payment",
        ),
        pytest.param(
            a.ARFClaim(
                a.ARFBenefitKind.WIDOW,
                date(1911, 1, 2),
                (1972, 1),
                F(0),
            ),
            (1983, 1),
            id="automatic-historical-widow-conflict",
        ),
        pytest.param(
            a.ARFClaim(
                a.ARFBenefitKind.SPOUSE,
                date(1960, 1, 2),
                (2022, 1),
                F(0),
                nonentitlement_months={(2022, 2)},
            ),
            (2024, 1),
            id="automatic-spouse-reentitlement",
        ),
        pytest.param(
            a.ARFClaim(
                a.ARFBenefitKind.SPOUSE,
                date(1960, 1, 2),
                (2022, 1),
                F(0),
                spouse_own=a.SpouseOwnBenefit(
                    F(200), F(160), a.SpouseOwnSequence.AFTER_SPOUSE_BEFORE_ARF
                ),
            ),
            FRA,
            id="automatic-own-entitlement-sequence",
        ),
    ],
)
def test_invalid_rib_parameters_precede_all_arf_refusals_and_counts(
    overrides, message, entrypoint, claim, payment
):
    """Invalid bundles propagate; no unsupported outcome is constructed."""
    params = ssa_params(**overrides)

    def compute():
        return a.apply_arf(claim, payment_month=payment, params=params)

    with pytest.raises(ValueError) as caught:
        if entrypoint == "apply":
            compute()
        elif entrypoint == "evaluate":
            a.evaluate_arf("invalid", F(1), compute)
        else:
            a.count_arf_outcomes(
                [
                    a.evaluate_arf(key, F(1), compute)
                    for key in ("left", "right")
                ]
            )
    assert str(caught.value) == message


@pytest.mark.parametrize("overrides,message", INVALID_RIB_PARAMETERS)
def test_invalid_rib_parameters_precede_arf_money_arithmetic(
    monkeypatch, overrides, message
):
    def forbidden(*args, **kwargs):
        pytest.fail("invalid statutory bundle reached money arithmetic")

    monkeypatch.setattr(a, "_worker_reduction_fraction_validated", forbidden)
    with pytest.raises(ValueError) as caught:
        a.apply_arf(
            rib_claim(), payment_month=FRA, params=ssa_params(**overrides)
        )
    assert str(caught.value) == message


@pytest.mark.parametrize(
    "conditions", [(), (a.ARFUnsupportedReason.OTHER_SUSPENSION,)]
)
def test_reviewer_nan_rib_rate_is_an_input_error_before_support_or_refusal(
    conditions,
):
    """Reviewer NaN counterexample: neither a $0 result nor a refused row."""
    params = ssa_params(early_monthly_rates=(float("nan"), 0.00416667))
    claim = rib_claim(
        first_reduction_month=(2027, 1),
        unreduced_benefit=F(0),
        conditions=conditions,
    )
    with pytest.raises(ValueError, match="finite") as caught:
        a.apply_arf(claim, payment_month=FRA, params=params)
    assert "early_monthly_rates[0]" in str(caught.value)


@pytest.mark.parametrize(
    "field,index",
    STATUTORY_RATE_FIELDS,
    ids=[
        field if index is None else f"{field}[{index}]"
        for field, index in STATUTORY_RATE_FIELDS
    ],
)
@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), float("-inf")],
    ids=["nan", "positive-infinity", "negative-infinity"],
)
@pytest.mark.parametrize("kind", list(a.ARFBenefitKind), ids=lambda k: k.value)
@pytest.mark.parametrize("coverage", ["ordinary", "explicit", "automatic"])
@pytest.mark.parametrize("entrypoint", ["apply", "evaluate", "count"])
def test_nonfinite_statutory_fields_precede_arf_refusals_and_arithmetic(
    monkeypatch, field, index, value, kind, coverage, entrypoint
):
    """Invalid rates/brackets cannot create benefits or unsupported rows."""
    params = nonfinite_statutory_params(field, index, value)
    claim, payment = statutory_validation_claim(kind, coverage)

    def forbidden(*args, **kwargs):
        pytest.fail("non-finite statutory input reached coverage or money")

    for name in (
        "_statutory_rates_validated",
        "_refuse",
        "_worker_reduction_fraction_validated",
        "_spouse_reduction_fraction_validated",
        "_survivor_reduction_fraction_validated",
        "_ceil_dime_validated",
        "_floor_dime_validated",
        "_whole_dollars_validated",
    ):
        monkeypatch.setattr(a, name, forbidden)

    calls = []

    def compute():
        calls.append("compute")
        return a.apply_arf(claim, payment_month=payment, params=params)

    def evaluate():
        return a.evaluate_arf("invalid", F(3), compute)

    if entrypoint == "apply":
        invoke = compute
    elif entrypoint == "evaluate":
        invoke = evaluate
    else:
        assert calls == []  # Row construction starts only on invocation.

        def invoke():
            return a.count_arf_outcomes([evaluate() for _ in range(2)])

    with pytest.raises(ValueError, match="finite") as caught:
        invoke()
    label = field if index is None else f"{field}[{index}]"
    assert label in str(caught.value)
    assert calls == ["compute"]  # No invalid row enters the denominator.


@pytest.mark.parametrize(
    "field,index",
    [
        ("early_monthly_rates", 0),
        ("spousal_early_first_bracket_months", None),
        ("survivor_reduction_floor", None),
    ],
)
@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
def test_nonfinite_decimal_statutory_fields_are_input_errors(
    field, index, value
):
    """Numeric finiteness also applies to Decimal rate and bracket inputs."""
    params = nonfinite_statutory_params(field, index, Decimal(value))
    with pytest.raises(ValueError, match="finite") as caught:
        a.apply_arf(rib_claim(), payment_month=FRA, params=params)
    label = field if index is None else f"{field}[{index}]"
    assert label in str(caught.value)


@pytest.mark.parametrize("field", (*a._CREDIT_FIELDS, "conditions"))
def test_arf_iterator_fields_are_rejected_without_consumption(field):
    """Only built-in containers enter a declaration's schema boundary."""
    item = (
        a.ARFUnsupportedReason.OTHER_SUSPENSION
        if field == "conditions"
        else (2022, 1)
    )
    values = iter([item])
    with pytest.raises(g.InvalidFamilyInput):
        rib_claim(**{field: values})
    assert next(values) == item


def test_arf_outcome_iterator_is_rejected_without_computing_a_row():
    calls = []

    def evaluate():
        calls.append("evaluated")
        return a.evaluate_arf(
            "control",
            F(1),
            lambda: a.apply_arf(rib_claim(), payment_month=FRA, params=PARAMS),
        )

    outcomes = (evaluate() for _ in range(2))
    with pytest.raises(g.InvalidFamilyInput):
        a.count_arf_outcomes(outcomes)
    assert calls == []
