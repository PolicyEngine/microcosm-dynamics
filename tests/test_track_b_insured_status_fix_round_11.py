"""Statutory conformance: credit routes and proof-before-refusal ordering.

Invented declarations only. No population, behavioral, or forecast claim.
The minimum oracle below uses calendar arithmetic and no implementation
helper. Foreign cases claim no totalization minimum or eligibility rule.
"""

from dataclasses import replace
from datetime import date
from fractions import Fraction

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import insured_status as i
from populace_dynamics.track_b.gross_benefits import count_family_outcomes
from tests.test_track_b_insured_status import history

OBSERVED = i.EarningsProvenance.OBSERVED
UNKNOWN = i.EarningsProvenance.UNKNOWN
WEIGHT = Fraction(11, 5)
FULLY_ROUTES = (
    i.CoverageCondition.DEEMED_FULLY_INSURED,
    i.CoverageCondition.TRANSITIONAL_INSURED,
    i.CoverageCondition.EARNED_BASIS,
    i.CoverageCondition.SIMPLIFIED_PRE1951,
)
RAW_EARNINGS = (
    i.CoverageCondition.RAILROAD_CREDITS,
    i.CoverageCondition.FISCAL_TAXABLE_YEAR,
    i.CoverageCondition.SHORT_TAXABLE_YEAR,
)
CREDIT_ROUTES = (
    i.CoverageCondition.MILITARY_CREDITS,
    i.CoverageCondition.MEDICARE_GOVERNMENT_EMPLOYMENT,
)
RECENT_TEST = i.CoverageCondition.DISABILITY_BEFORE_1956
NO_ADDED_CREDIT = (*FULLY_ROUTES, *RAW_EARNINGS, RECENT_TEST)
TESTS = (i.InsuredTest.FULLY, i.InsuredTest.DISABILITY)


def _person(birth=date(1980, 2, 2), onset=date(2022, 1, 15), **kwargs):
    return i.Person(
        birth,
        disability_onset=onset,
        current_disability_period_established=True,
        current_disability_period_provenance=OBSERVED,
        current_disability_period_end=date(onset.year, 12, 31),
        current_disability_period_end_provenance=OBSERVED,
        prior_disability_periods_provenance=OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
        **kwargs,
    )


def _counts(total, *, last=2021):
    """Place final direct QCs in the years immediately preceding onset."""
    result = {}
    for year in range(last, last - 10, -1):
        result[year], total = min(total, 4), max(0, total - 4)
    assert total == 0
    return result


def _evaluate(person, years, month, *, test=i.InsuredTest.FULLY, **kwargs):
    return i.evaluate_insured_status(
        "round-eleven",
        WEIGHT,
        lambda: i.insured_status(person, years, month, test=test, **kwargs),
    )


def _assert_refusal(person, years, month, reason, **kwargs):
    row = _evaluate(person, years, month, **kwargs)
    assert row.result is None
    assert row.unsupported.reason is reason
    denominator = count_family_outcomes((row,))
    assert denominator.rows == denominator.unsupported_rows == 1
    assert denominator.weight == denominator.unsupported_weight == WEIGHT
    return row


def _assert_invalid(person, years, month, **kwargs):
    rows = []
    with pytest.raises(i.InvalidFamilyInput, match="no possible insured"):
        rows.append(_evaluate(person, years, month, **kwargs))
    denominator = count_family_outcomes(rows)
    assert denominator.rows == denominator.unsupported_rows == 0
    assert denominator.weight == denominator.unsupported_weight == 0


def _reason(condition):
    return i.InsuredUnsupportedReason[condition.name]


@pytest.mark.parametrize("test", TESTS)
@pytest.mark.parametrize("own_qcs", [0, 3, 6, 10])
@pytest.mark.parametrize(
    "month,coverage_end",
    [
        (date(2001, 1, 1), None),
        (date(2022, 2, 1), None),
        (date(2022, 2, 1), date(2000, 12, 1)),
    ],
    ids=["direct", "age62", "coverage-end"],
)
def test_foreign_credits_refuse_without_an_own_qc_floor(
    test, own_qcs, month, coverage_end
):
    """Includes Sol's three-QC counterexample and six-QC controls."""
    person = _person(date(1960, 2, 2), date(2000, 1, 15))
    counts = {1998: 3} if own_qcs == 3 else _counts(own_qcs, last=1999)
    years = history(person, month, counts, end=coverage_end)
    _assert_refusal(
        person,
        years,
        month,
        i.InsuredUnsupportedReason.TOTALIZATION,
        test=test,
        totalization_credits=("canada",),
        coverage_end_month=coverage_end,
    )


@pytest.mark.parametrize("test", TESTS)
@pytest.mark.parametrize("coverage_end", [None, date(1985, 12, 1)])
@pytest.mark.parametrize("deemed", [False, True])
def test_review_recent_credit_shortfall_cannot_be_cured_by_deeming(
    test, coverage_end, deemed
):
    """Sol's second counterexample and the same case without its flag."""
    person = _person(
        date(1924, 1, 2),
        date(1985, 1, 15),
        conditions=(
            (i.CoverageCondition.DEEMED_FULLY_INSURED,) if deemed else ()
        ),
    )
    month = date(1986, 1, 1)
    years = history(person, month, {1984: 4, 1985: 2}, end=coverage_end)
    _assert_invalid(
        person, years, month, test=test, coverage_end_month=coverage_end
    )


@pytest.mark.parametrize("condition", list(i.CoverageCondition))
@pytest.mark.parametrize("foreign", [False, True])
def test_fixed_overlap_precedes_every_flag_and_foreign_route(
    condition, foreign
):
    person = _person(
        conditions=(condition,),
        prior_disability_periods=(
            i.DisabilityPeriod(date(2021, 1, 1), date(2022, 1, 14)),
        ),
    )
    person = replace(person, current_disability_period_end=date(2022, 1, 31))
    month = date(2023, 1, 1)
    _assert_invalid(
        person,
        history(person, month, _counts(20)),
        month,
        totalization_credits=("canada",) if foreign else (),
    )


@pytest.mark.parametrize("condition", NO_ADDED_CREDIT)
@pytest.mark.parametrize("age,minimum", [(42, 20), (29, 16)])
@pytest.mark.parametrize("meets_minimum", [False, True])
def test_no_credit_flag_shortfall_and_exact_minimum_pair(
    condition, age, minimum, meets_minimum
):
    person = _person(birth=date(2022 - age, 2, 2), conditions=(condition,))
    month = date(2023, 1, 1)
    total = minimum if meets_minimum else minimum - 1
    years = history(person, month, _counts(total))
    assert sum(row.qc_count or 0 for row in years.values()) == total
    if meets_minimum:
        _assert_refusal(person, years, month, _reason(condition))
    else:
        _assert_invalid(person, years, month)


@pytest.mark.parametrize("condition", CREDIT_ROUTES)
@pytest.mark.parametrize("age,minimum", [(42, 20), (29, 16)])
@pytest.mark.parametrize("total_kind", ["zero", "shortfall", "minimum"])
def test_credit_route_keeps_refusal_even_with_complete_direct_envelope(
    condition, age, minimum, total_kind
):
    person = _person(birth=date(2022 - age, 2, 2), conditions=(condition,))
    month = date(2023, 1, 1)
    total = {"zero": 0, "shortfall": minimum - 1, "minimum": minimum}[
        total_kind
    ]
    _assert_refusal(
        person,
        history(person, month, _counts(total)),
        month,
        _reason(condition),
    )


@pytest.mark.parametrize("condition", FULLY_ROUTES)
@pytest.mark.parametrize(
    "exception,total,last,possible",
    [
        ("blind", 3, 2021, True),
        ("unknown-prior", 3, 2021, False),
        # 404.130(c)-(d): Rule III needs an earlier Rule II period. Credits
        # first earned at age 40 can't supply its six QCs before age 31.
        ("unknown-prior", 6, 2021, False),
        ("unknown-prior", 6, 2003, True),
    ],
)
def test_fully_route_refuses_when_recent_credit_proof_does_not_apply(
    condition, exception, total, last, possible
):
    person = _person(conditions=(condition,))
    if exception == "blind":
        person = replace(person, statutory_blindness=True)
    else:
        person = replace(person, prior_disability_periods_provenance=UNKNOWN)
    month = date(2023, 1, 1)
    years = history(person, month, _counts(total, last=last))
    if not possible:
        _assert_invalid(person, years, month)
        return
    _assert_refusal(person, years, month, _reason(condition))


@pytest.mark.parametrize("total", [3, 20])
def test_pre1956_flag_with_blindness_keeps_ordinary_six_qc_floor(total):
    person = _person(statutory_blindness=True, conditions=(RECENT_TEST,))
    month = date(2023, 1, 1)
    years = history(person, month, _counts(total))
    if total < 6:
        _assert_invalid(person, years, month)
    else:
        _assert_refusal(person, years, month, _reason(RECENT_TEST))


@pytest.mark.parametrize("condition", RAW_EARNINGS)
@pytest.mark.parametrize("age,minimum", [(42, 20), (29, 16)])
def test_raw_earnings_flag_preserves_route_only_without_direct_envelope(
    condition, age, minimum
):
    person = _person(birth=date(2022 - age, 2, 2), conditions=(condition,))
    month = date(2023, 1, 1)
    years = history(person, month, _counts(minimum - 1))
    _assert_invalid(person, years, month)
    years[2010] = i.CoverageYear(OBSERVED, wages=Fraction(0))
    _assert_refusal(person, years, month, _reason(condition))


FLAG_PAIRS = (
    (FULLY_ROUTES[0], RECENT_TEST),
    (FULLY_ROUTES[0], RAW_EARNINGS[0]),
    (FULLY_ROUTES[0], CREDIT_ROUTES[0]),
    (RECENT_TEST, RAW_EARNINGS[0]),
    (RECENT_TEST, CREDIT_ROUTES[0]),
    (RAW_EARNINGS[0], CREDIT_ROUTES[0]),
)


@pytest.mark.parametrize("conditions", FLAG_PAIRS)
@pytest.mark.parametrize("total", [6, 20])
def test_two_flag_classes_preserve_each_independent_route(conditions, total):
    person = _person(conditions=conditions)
    month = date(2023, 1, 1)
    years = history(person, month, _counts(total))
    if total < 20 and not set(conditions).intersection(CREDIT_ROUTES):
        _assert_invalid(person, years, month)
    else:
        first = min(conditions, key=lambda condition: condition.value)
        _assert_refusal(person, years, month, _reason(first))


@settings(max_examples=48, deadline=None)
@example(total=0, age=22, blind=False, condition=None)
@example(total=3, age=42, blind=True, condition=FULLY_ROUTES[0])
@given(
    total=st.integers(0, 40),
    age=st.sampled_from([22, 29, 31, 42]),
    blind=st.booleans(),
    condition=st.one_of(st.none(), st.sampled_from(list(i.CoverageCondition))),
)
def test_foreign_credit_refusal_is_independent_of_own_qc_count(
    total, age, blind, condition
):
    person = _person(
        birth=date(2022 - age, 2, 2),
        statutory_blindness=blind,
        conditions=() if condition is None else (condition,),
    )
    month = date(2023, 1, 1)
    _assert_refusal(
        person,
        history(person, month, _counts(total)),
        month,
        i.InsuredUnsupportedReason.TOTALIZATION,
        totalization_credits=("invented-foreign-credit",),
    )


def _independent_recent_minimum(age):
    """404.130: twenty, or half elapsed quarters after age 21, floor six.

    Birth is always February 2 and onset January 15, 2022. Attainment is
    February 1; quarter arithmetic here is deliberately independent of
    the insured-status implementation. There are no prior periods.
    """
    birth_year = 2022 - age
    onset_quarter = 2022 * 4
    age31_quarter = (birth_year + 31) * 4
    if onset_quarter >= age31_quarter:
        return 20
    first_elapsed_quarter = (birth_year + 21) * 4 + 1
    elapsed = onset_quarter - first_elapsed_quarter + 1
    return min(20, max(6, elapsed // 2))


@settings(max_examples=64, deadline=None)
@example(age=42, missing=1, conditions=frozenset((FULLY_ROUTES[0],)))
@example(age=29, missing=1, conditions=frozenset((RAW_EARNINGS[2],)))
@given(
    age=st.sampled_from([22, 24, 29, 31, 42]),
    missing=st.integers(1, 20),
    conditions=st.sets(st.sampled_from(NO_ADDED_CREDIT), min_size=1),
)
def test_no_credit_flag_set_cannot_hide_independently_proved_shortfall(
    age, missing, conditions
):
    required = _independent_recent_minimum(age)
    total = max(0, required - missing)
    assert total < required
    person = _person(birth=date(2022 - age, 2, 2), conditions=conditions)
    month = date(2023, 1, 1)
    _assert_invalid(person, history(person, month, _counts(total)), month)


@settings(max_examples=36, deadline=None)
@example(age=29, extra=0, condition=RAW_EARNINGS[2])
@given(
    age=st.sampled_from([22, 24, 29, 31, 42]),
    extra=st.integers(0, 10),
    condition=st.sampled_from(list(i.CoverageCondition)),
)
def test_no_flag_rejects_declaration_meeting_every_requirement(
    age, extra, condition
):
    required = _independent_recent_minimum(age)
    person = _person(birth=date(2022 - age, 2, 2))
    month = date(2023, 1, 1)
    years = history(person, month, _counts(required + extra))
    baseline = _evaluate(person, years, month)
    assert baseline.result is not None
    assert baseline.unsupported is None
    denominator = count_family_outcomes((baseline,))
    assert denominator.rows == 1
    assert denominator.weight == WEIGHT
    assert denominator.unsupported_rows == denominator.unsupported_weight == 0
    _assert_refusal(
        replace(person, conditions=(condition,)),
        years,
        month,
        _reason(condition),
    )
