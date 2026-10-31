"""Statutory conformance: prove impossibility before coverage refusals.

Invented declarations only. No population, behavioral, or forecast claim.
The enumeration oracle uses the witness path, never the new lower bound.
"""

from dataclasses import replace
from datetime import date
from fractions import Fraction
from itertools import product

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import insured_status as i
from populace_dynamics.track_b.gross_benefits import count_family_outcomes
from tests.test_track_b_insured_status import declared, history
from tests.test_track_b_insured_status_fix_round_4_routes import (
    _short_period_case,
)

OBSERVED = i.EarningsProvenance.OBSERVED
UNKNOWN = i.EarningsProvenance.UNKNOWN
WEIGHT = Fraction(7, 3)


def _person(birth=date(1960, 2, 2), onset=date(2000, 1, 15), **kwargs):
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


def _evaluate(person, years, month, *, test=i.InsuredTest.FULLY, **kwargs):
    return i.evaluate_insured_status(
        "round-ten-proof",
        WEIGHT,
        lambda: i.insured_status(person, years, month, test=test, **kwargs),
    )


def _assert_row(row, reason=None):
    denominator = count_family_outcomes((row,))
    assert denominator.rows == 1
    assert denominator.weight == WEIGHT
    if reason is None:
        assert row.result is not None
        assert row.unsupported is None
        assert denominator.unsupported_rows == 0
        assert denominator.unsupported_weight == 0
    else:
        assert row.result is None
        assert row.unsupported.reason is reason
        assert denominator.unsupported_rows == 1
        assert denominator.unsupported_weight == WEIGHT


def _complexity_case():
    periods = (
        i.DisabilityPeriod(date(1980, 1, 15), date(1983, 12, 31), True),
        *(
            i.DisabilityPeriod(date(year, 1, 1), date(year, 6, 30), True)
            for year in range(1984, 1989)
        ),
    )
    person = _person(prior_disability_periods=periods)
    month = date(2022, 2, 1)
    counts = {1978: 4, 1979: 2, 1988: 1}
    counts.update({year: 2 for year in range(1984, 1988)})
    return person, history(person, month, counts), month


@pytest.mark.parametrize(
    "test", [i.InsuredTest.FULLY, i.InsuredTest.DISABILITY]
)
def test_impossible_fifteen_qcs_precede_boundary_complexity_without_a_row(
    test,
):
    person, years, month = _complexity_case()
    assert sum(row.qc_count or 0 for row in years.values()) == 15
    rows = []
    with pytest.raises(i.InvalidFamilyInput, match="no possible insured"):
        rows.append(_evaluate(person, years, month, test=test))
    assert count_family_outcomes(rows).rows == 0
    assert count_family_outcomes(rows).weight == 0


def test_ten_own_qcs_and_foreign_credits_keep_named_refusal_and_weight():
    person = _person()
    month = date(2001, 1, 1)
    years = history(person, month, {1997: 4, 1998: 4, 1999: 2})
    row = _evaluate(person, years, month, totalization_credits=("canada",))
    _assert_row(row, i.InsuredUnsupportedReason.TOTALIZATION)


def test_six_own_qcs_foreign_credits_and_unknown_prior_keep_refusal():
    person = replace(
        _person(birth=date(2000, 2, 2), onset=date(2000, 2, 2)),
        current_disability_period_end=None,
        current_disability_period_end_provenance=UNKNOWN,
        prior_disability_periods_provenance=UNKNOWN,
        conditions=(i.CoverageCondition.RAILROAD_CREDITS,),
    )
    month = date(2029, 4, 1)
    row = _evaluate(
        person,
        history(person, month, {2028: 4, 2029: 2}),
        month,
        totalization_credits=("invented-foreign-credit",),
    )
    _assert_row(row, i.InsuredUnsupportedReason.TOTALIZATION)


def test_three_own_qcs_and_foreign_credits_still_fail_six_qc_floor():
    person = _person()
    month = date(2001, 1, 1)
    years = history(person, month, {1999: 3})
    rows = []
    with pytest.raises(i.InvalidFamilyInput, match="no possible insured"):
        rows.append(
            _evaluate(person, years, month, totalization_credits=("canada",))
        )
    assert count_family_outcomes(rows).rows == 0


@pytest.mark.parametrize("young", [False, True])
def test_exact_minimum_qcs_are_not_rejected_by_the_proof(young):
    person = _person(
        birth=date(2000 if young else 1980, 2, 2),
        onset=date(2022, 1, 15),
    )
    month = date(2023, 1, 1)
    counts = (
        {2020: 2, 2021: 4}
        if young
        else {year: 4 for year in range(2017, 2022)}
    )
    row = _evaluate(person, history(person, month, counts), month)
    _assert_row(row)
    assert (
        row.result.current_disability_period_start == person.disability_onset
    )
    assert row.result.fully.insured


def test_blindness_keeps_six_qc_concrete_short_prior_period_route():
    person, years, month = _short_period_case()
    person = replace(
        person,
        prior_disability_periods_provenance=OBSERVED,
        prior_disability_periods=(
            i.DisabilityPeriod(date(2028, 10, 1), date(2028, 12, 31)),
        ),
    )
    row = _evaluate(person, years, month)
    _assert_row(row)
    assert row.result.fully.insured
    assert row.result.fully.qc_count_lower == 6


def test_unknown_prior_history_can_reduce_the_unseen_special_requirement():
    person = replace(_person(), prior_disability_periods_provenance=UNKNOWN)
    month = date(2001, 1, 1)
    years = history(person, month, {1978: 4, 1979: 2})
    row = _evaluate(person, years, month)
    _assert_row(row, i.InsuredUnsupportedReason.UNKNOWN_PERIODS)


@settings(max_examples=32, deadline=None)
@example(age=22, earlier=2, unknowns=(2021,), prior=False, blind=False)
@example(age=42, earlier=0, unknowns=(2020, 2021), prior=True, blind=False)
@example(age=42, earlier=4, unknowns=(2020, 2021), prior=True, blind=False)
@given(
    age=st.sampled_from([22, 29, 31, 42]),
    earlier=st.integers(0, 4),
    unknowns=st.sampled_from([(2021,), (2020, 2021)]),
    prior=st.booleans(),
    blind=st.booleans(),
)
def test_minimum_qc_proof_never_rejects_an_enumerated_witness(
    age, earlier, unknowns, prior, blind
):
    birth = date(2022 - age, 2, 2)
    prior_start = min(2015, birth.year + 25)
    person = _person(
        birth=birth,
        onset=date(2022, 1, 15),
        statutory_blindness=blind,
        prior_disability_periods=(
            (
                i.DisabilityPeriod(
                    date(prior_start, 1, 1), date(2019, 12, 31), True
                ),
            )
            if prior
            else ()
        ),
    )
    month = date(2023, 1, 1)
    years = history(person, month, {prior_start - 2: earlier})
    for year in unknowns:
        years[year] = i.CoverageYear(UNKNOWN)
    accepted = False
    horizon = person.current_disability_period_end
    for counts in product(range(5), repeat=len(unknowns)):
        concrete = {**years}
        concrete.update(
            (year, declared(count))
            for year, count in zip(unknowns, counts, strict=True)
        )
        credits = {
            year: i._credits(year, row, True) for year, row in concrete.items()
        }
        # This enumerates the pre-existing witness/assignment path. It
        # neither calls the proof nor replaces its bound with an oracle.
        try:
            i._with_current_period(person, credits, horizon, None)
        except i.InvalidFamilyInput:
            continue
        accepted = True
    if age == 42 and earlier == 4 and unknowns == (2020, 2021) and prior:
        # This explicit twelve-QC subsequent-special completion keeps the
        # nonblind, over31 branch of the property from being vacuous.
        assert accepted
    upper = {year: i._credits(year, row, True) for year, row in years.items()}
    rows, _ = i._world(person, upper, i._qid(month), None, False)
    maximum = sum(len(i._assign_qcs(*row)) for row in rows.values())
    if accepted:
        assert i._could_establish_current_period(
            person, years, upper, month, None, maximum
        )
        row = _evaluate(person, years, month)
        denominator = count_family_outcomes((row,))
        assert denominator.rows == 1
        assert denominator.weight == WEIGHT
