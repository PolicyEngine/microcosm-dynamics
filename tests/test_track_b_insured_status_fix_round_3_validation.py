"""Statutory conformance: impossible UNKNOWN histories never count rows.

Invented declarations only; no population, behavioral, or forecast claim.
"""

from dataclasses import replace
from datetime import date
from fractions import Fraction

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import insured_status as i
from populace_dynamics.track_b.gross_benefits import count_family_outcomes
from tests.test_track_b_insured_status import declared, history
from tests.test_track_b_insured_status_fix_round_2 import _person


def _impossible_person(onset=date(2000, 2, 2)):
    return _person(
        date(2000, 2, 2),
        disability_onset=onset,
        current_disability_period_established=True,
        prior_disability_periods_provenance=i.EarningsProvenance.UNKNOWN,
    )


@pytest.mark.parametrize("onset", [date(2000, 2, 2), date(2020, 1, 15)])
def test_impossible_establishment_with_unknown_prior_history_is_input_error(
    onset,
):
    person = _impossible_person(onset)
    month = date(2029, 4, 1)
    years = history(person, month, {2028: 4, 2029: 2})
    with pytest.raises(i.InvalidFamilyInput):
        i.insured_status(person, years, month, test=i.InsuredTest.FULLY)


def test_impossible_establishment_creates_no_evaluator_denominator_row():
    person = _impossible_person()
    month = date(2029, 4, 1)
    rows = []
    with pytest.raises(i.InvalidFamilyInput):
        rows.append(
            i.evaluate_insured_status(
                "impossible-current-period",
                Fraction(2),
                lambda: i.insured_status(
                    person,
                    history(person, month, {2028: 4, 2029: 2}),
                    month,
                    test=i.InsuredTest.FULLY,
                ),
            )
        )
    denominator = count_family_outcomes(rows)
    assert denominator.rows == denominator.unsupported_rows == 0
    assert denominator.unsupported_weight == 0


def test_impossible_unknown_history_validation_precedes_coverage_refusal():
    person = replace(
        _impossible_person(),
        conditions=(i.CoverageCondition.RAILROAD_CREDITS,),
    )
    month = date(2029, 4, 1)
    # Three own QCs cannot pass the floor even when foreign coverage is
    # declared. Six own QCs leave that unmodeled route unresolved.
    with pytest.raises(i.InvalidFamilyInput):
        i.insured_status(
            person,
            history(person, month, {2028: 3}),
            month,
            totalization_credits=("invented-foreign-credit",),
        )


@settings(max_examples=20, deadline=None)
@example(
    earlier=4,
    later=4,
    unknown_early=True,
    onset=date(2022, 1, 15),
    old_history=True,
)
@given(
    earlier=st.integers(0, 4),
    later=st.integers(0, 4),
    unknown_early=st.booleans(),
    onset=st.sampled_from([date(2000, 2, 2), date(2022, 1, 15)]),
    old_history=st.booleans(),
)
def test_invalid_unknown_declaration_has_no_valid_enumerated_filling(
    earlier, later, unknown_early, onset, old_history
):
    """One-way soundness against empty/one/two-period small fillings.

    Candidate periods must themselves begin disability insured without
    earlier periods and last at least five months. UNKNOWN earnings are
    filled by all five annual QC counts before checking the declarations.
    Unproved feasibility may retain a refusal; no completeness is claimed.
    """
    person = _impossible_person(onset)
    month = date(2029, 4, 1)
    counts = (
        {2019: earlier, 2020: later, 2028: 4}
        if old_history
        else {2028: earlier, 2029: later}
    )
    years = history(person, month, counts)
    if unknown_early:
        years[2018] = declared(provenance=i.EarningsProvenance.UNKNOWN)
    raised_invalid = False
    try:
        i.insured_status(person, years, month, test=i.InsuredTest.FULLY)
    except i.InvalidFamilyInput:
        raised_invalid = True
    except i.InsuredConfigurationUnsupported:
        pass

    valid = []
    observed = replace(
        person,
        prior_disability_periods_provenance=i.EarningsProvenance.OBSERVED,
    )
    for count in range(5) if unknown_early else (0,):
        filled = dict(years)
        if unknown_early:
            filled[2018] = declared(count)
        credits = {
            year: i._credits(year, row, False) for year, row in filled.items()
        }
        candidates = []
        for start, end in (
            (date(2020, 7, 1), date(2021, 1, 31)),
            (date(2021, 4, 1), date(2021, 10, 31)),
        ):
            if (
                end < onset
                and i._witness(
                    observed,
                    credits,
                    start,
                    None,
                    i.InsuredTest.DISABILITY,
                    onset=False,
                )[0]
            ):
                candidates.append(i.DisabilityPeriod(start, end))
        fillings = [(), *((period,) for period in candidates)]
        if len(candidates) == 2:
            fillings.append(tuple(candidates))
        for periods in fillings:
            try:
                i.insured_status(
                    replace(observed, prior_disability_periods=periods),
                    filled,
                    month,
                    test=i.InsuredTest.FULLY,
                )
            except i.InvalidFamilyInput:
                valid.append(False)
            except i.InsuredConfigurationUnsupported:
                # A refusal is not a proof of a valid declaration.
                continue
            else:
                valid.append(True)
    if raised_invalid:
        assert not any(valid)
    if any(valid):
        assert not raised_invalid


@settings(max_examples=12, deadline=None)
@given(shift=st.integers(0, 3), late=st.integers(2, 4))
def test_valid_prior_freeze_filling_prevents_false_invalidity(shift, late):
    """A long special period can rescue a current start invalid without it."""
    birth = date(1980 + shift, 2, 2)
    month = date(2019 + shift, 4, 1)
    person = _person(
        birth,
        disability_onset=date(2019 + shift, 1, 15),
        current_disability_period_established=True,
        prior_disability_periods_provenance=i.EarningsProvenance.UNKNOWN,
    )
    years = history(person, month, {2001 + shift: 4, 2002 + shift: late})
    empty = replace(
        person,
        prior_disability_periods_provenance=i.EarningsProvenance.OBSERVED,
    )
    with pytest.raises(i.InvalidFamilyInput):
        i.insured_status(empty, years, month, test=i.InsuredTest.FULLY)
    period = i.DisabilityPeriod(
        date(2002 + shift, 4, 1),
        date(2018 + shift, 9, 30),
        special_insured=True,
    )
    filled = i.insured_status(
        replace(empty, prior_disability_periods=(period,)),
        years,
        month,
        test=i.InsuredTest.FULLY,
    )
    assert filled.fully.insured
    try:
        i.insured_status(person, years, month, test=i.InsuredTest.FULLY)
    except i.InsuredConfigurationUnsupported as refusal:
        assert refusal.reason is i.InsuredUnsupportedReason.UNKNOWN_PERIODS
