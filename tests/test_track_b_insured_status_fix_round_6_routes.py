"""Statutory conformance: settled alternate routes and quarter overlaps.

Invented declarations and captured statutory text only; no population,
behavioral, payment, or forecast claim.
"""

import calendar
from dataclasses import replace
from datetime import date
from fractions import Fraction
from itertools import product

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import insured_status as i
from populace_dynamics.track_b.gross_benefits import count_family_outcomes
from tests.test_track_b_insured_status import history
from tests.test_track_b_insured_status_fix_round_4_routes import (
    _pre1956_case,
)
from tests.test_track_b_insured_status_sources import source_text

OBSERVED = i.EarningsProvenance.OBSERVED
UNKNOWN = i.EarningsProvenance.UNKNOWN


def _ordinary_pre1956_case(*, unknown_prior=False):
    person = i.Person(
        date(1920, 2, 2),
        disability_onset=date(1955, 1, 15),
        current_disability_period_established=True,
        current_disability_period_provenance=OBSERVED,
        prior_disability_periods_provenance=(
            UNKNOWN if unknown_prior else OBSERVED
        ),
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
    )
    month = date(1968, 1, 1)
    years = history(person, month, {year: 4 for year in range(1950, 1955)})
    return person, years, month


def _row(person, years, month):
    return i.evaluate_insured_status(
        "round-six-route",
        Fraction(11, 5),
        lambda: i.insured_status(
            person, years, month, test=i.InsuredTest.FULLY
        ),
    )


def _assert_invalid_without_row(person, years, month):
    rows = []
    with pytest.raises(i.InvalidFamilyInput):
        rows.append(_row(person, years, month))
    assert rows == []
    assert count_family_outcomes(rows).rows == 0


def test_pre1956_alternate_exclusion_is_quoted_from_capture():
    assert (
        "does not have 20/40 for freeze or DIB in any quarter before 10/60"
    ) in source_text("poms_rs_00301_480")


def test_twenty_of_forty_before_october_1960_excludes_alternate_refusal():
    person, years, month = _ordinary_pre1956_case()
    result = i.insured_status(person, years, month, test=i.InsuredTest.FULLY)
    assert result.fully.insured
    assert result.current_disability_period_start == date(1955, 1, 15)


def test_twenty_of_forty_scan_includes_later_disabled_quarters_before_1960():
    person, years, month = _ordinary_pre1956_case()
    person = replace(
        person,
        current_disability_period_end=date(1956, 12, 31),
        current_disability_period_end_provenance=OBSERVED,
    )
    years[1950] = i.CoverageYear(OBSERVED, qc_quarters=(False,) * 4)
    years[1940] = i.CoverageYear(OBSERVED, qc_quarters=(True,) * 4)
    years[1956] = i.CoverageYear(OBSERVED, qc_quarters=(True,) * 4)
    result = i.insured_status(person, years, month, test=i.InsuredTest.FULLY)
    assert result.fully.insured
    assert result.current_disability_period_start == date(1956, 10, 1)


@pytest.mark.parametrize("quarter", [3, 4])
def test_twenty_of_forty_alternate_exclusion_stops_before_october_1960(
    quarter,
):
    person, years, month = _ordinary_pre1956_case()
    person = replace(
        person,
        current_disability_period_end=date(1960, 12, 31),
        current_disability_period_end_provenance=OBSERVED,
    )
    years[1950] = i.CoverageYear(OBSERVED, qc_quarters=(False,) * 4)
    years[1940] = i.CoverageYear(OBSERVED, qc_quarters=(True,) * 4)
    years[1955] = i.CoverageYear(
        OBSERVED, qc_quarters=(True, True, True, False)
    )
    years[1960] = i.CoverageYear(
        OBSERVED,
        qc_quarters=tuple(n == quarter for n in range(1, 5)),
    )
    row = _row(person, years, month)
    if quarter == 3:
        assert row.unsupported is None
        assert row.result.fully.insured
        assert row.result.current_disability_period_start == date(1960, 7, 1)
    else:
        assert (
            row.unsupported.reason
            is i.InsuredUnsupportedReason.DISABILITY_BEFORE_1956
        )


@pytest.mark.parametrize("route", ["blind", "young"])
def test_other_ordinary_disability_routes_do_not_supply_twenty_of_forty(
    route,
):
    person, years, month = _pre1956_case()
    if route == "blind":
        person = replace(person, statutory_blindness=True)
        month = date(1973, 1, 1)
        years = {**history(person, month), **years}
    else:
        person = replace(person, birth_date=date(1930, 2, 2))
    ordinary = replace(person, current_disability_period_established=False)
    result = i.insured_status(
        ordinary, years, month, test=i.InsuredTest.DISABILITY
    )
    assert result.disability.insured
    assert result.disability.required == 6
    assert result.disability.rule == (
        "blindness_fully_only" if route == "blind" else "under31_special"
    )
    row = _row(person, years, month)
    assert (
        row.unsupported.reason
        is i.InsuredUnsupportedReason.DISABILITY_BEFORE_1956
    )


@settings(max_examples=12, deadline=None)
@given(extra_year=st.sampled_from([1940, 1949, 1955, 1960]))
def test_fixed_twenty_of_forty_exclusion_survives_extra_unknown_credits(
    extra_year,
):
    person, years, month = _ordinary_pre1956_case()
    years[extra_year] = i.CoverageYear(UNKNOWN)
    row = _row(person, years, month)
    assert row.unsupported is None
    assert row.result.fully.insured


def test_some_twenty_of_forty_fillings_keep_named_alternate_refusal():
    person, years, month = _ordinary_pre1956_case()
    years[1940] = i.CoverageYear(OBSERVED, qc_quarters=(True,) * 4)
    years[1950] = i.CoverageYear(UNKNOWN)
    outcomes = []
    for flags in product((False, True), repeat=4):
        concrete = {**years, 1950: i.CoverageYear(OBSERVED, qc_quarters=flags)}
        row = _row(person, concrete, month)
        if all(flags):
            assert row.unsupported is None
            assert row.result.fully.insured
            outcomes.append("ordinary")
        else:
            assert (
                row.unsupported.reason
                is i.InsuredUnsupportedReason.DISABILITY_BEFORE_1956
            )
            outcomes.append("alternate")
    assert outcomes.count("ordinary") == 1
    assert outcomes.count("alternate") == 15
    row = _row(person, years, month)
    assert (
        row.unsupported.reason
        is i.InsuredUnsupportedReason.DISABILITY_BEFORE_1956
    )
    denominator = count_family_outcomes((row,))
    assert denominator.rows == denominator.unsupported_rows == 1
    assert (
        denominator.weight == denominator.unsupported_weight == Fraction(11, 5)
    )


def test_excluding_alternate_preserves_ordinary_current_establishment():
    person, years, month = _ordinary_pre1956_case()
    credits = {
        year: i._credits(year, row, True) for year, row in years.items()
    }
    assert i._could_establish_current_period(
        person, years, credits, month, None, 20
    )


def test_excluding_alternate_preserves_possible_nonempty_prior_history():
    person, years, month = _ordinary_pre1956_case(unknown_prior=True)
    credits = {
        year: i._credits(year, row, True) for year, row in years.items()
    }
    # Ordinary 20/40 in 1954 Q4 permits a prior period before 1955 onset.
    # Excluding the alternate route cannot prove that history empty.
    assert not i._unknown_prior_history_is_empty(person, credits, month, None)
    row = _row(person, years, month)
    assert count_family_outcomes((row,)).rows == 1
    if row.unsupported is not None:
        assert (
            row.unsupported.reason
            is i.InsuredUnsupportedReason.UNKNOWN_PERIODS
        )
    else:
        assert row.result.fully.insured


def _shared_end_quarter_case(prior_end=date(1977, 1, 31)):
    # Fully insured in 1973Q1 (12 QCs for 11 elapsed years) and short of
    # 20 of 40, the prior rests on past blindness (404.130(e), from January
    # 1973 under RS 00301.150 A). The April end puts recovery in February
    # (404.321(b)), so only 1977Q1, the quarter the prior ended in January,
    # can start the period (RS 00301.140 example 7). There 20 of 40 needs
    # the prior disregarded (404.130(f)) and every 1974-1977Q1 quarter
    # credited, which UNKNOWN 1974-1977 leaves open.
    person = i.Person(
        date(1940, 2, 2),
        disability_onset=date(1977, 2, 15),
        prior_disability_periods=(
            i.DisabilityPeriod(date(1973, 1, 1), prior_end),
        ),
        prior_disability_periods_provenance=OBSERVED,
        current_disability_period_established=True,
        current_disability_period_provenance=OBSERVED,
        current_disability_period_end=date(1977, 4, 30),
        current_disability_period_end_provenance=OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
    )
    month = date(1978, 1, 1)
    years = history(person, month, {1966: 4, 1967: 4, 1968: 4})
    years.update({year: i.CoverageYear(UNKNOWN) for year in range(1974, 1978)})
    return person, years, month


def _filled(years, counts):
    return {
        **years,
        **{
            year: i.CoverageYear(
                OBSERVED, qc_quarters=tuple(n < count for n in range(4))
            )
            for year, count in zip(range(1974, 1978), counts, strict=True)
        },
    }


def _assert_earnings_refusal_row(person, years, month):
    row = _row(person, years, month)
    assert (
        row.unsupported.reason is i.InsuredUnsupportedReason.UNKNOWN_EARNINGS
    )
    assert row.unsupported.detail == (
        "Unknown earnings decide a valid established current period"
    )
    assert count_family_outcomes((row,)).rows == 1


def test_a_shared_end_quarter_leaves_validity_to_unknown_credits():
    """Round 6 rejected this record: its only start overlapped the prior.

    A period may now begin in the quarter a prior ended, so the credits
    decide validity. Every 1974-1977Q1 quarter credited starts the period
    on the onset day; one fewer leaves no insured quarter by February.
    """
    person, years, month = _shared_end_quarter_case()
    _assert_earnings_refusal_row(person, years, month)
    result = i.insured_status(
        person, _filled(years, (4, 4, 4, 1)), month, test=i.InsuredTest.FULLY
    )
    assert result.fully.insured
    assert result.current_disability_period_start == date(1977, 2, 15)
    for counts in ((0, 0, 0, 0), (4, 4, 4, 0), (3, 4, 4, 1)):
        _assert_invalid_without_row(person, _filled(years, counts), month)


@settings(max_examples=12, deadline=None)
@given(
    ending_month=st.sampled_from([4, 5]),
    extra_unknown=st.sampled_from([None, 1973, 1978]),
)
def test_shared_end_quarter_validity_stays_with_unknown_credits(
    ending_month, extra_unknown
):
    """A May end (recovery in March) still leaves only 1977Q1 to start."""
    person, years, month = _shared_end_quarter_case()
    person = replace(
        person,
        current_disability_period_end=date(
            1977, ending_month, calendar.monthrange(1977, ending_month)[1]
        ),
    )
    if extra_unknown is not None:
        years[extra_unknown] = i.CoverageYear(UNKNOWN)
    _assert_earnings_refusal_row(person, years, month)


@pytest.mark.parametrize("prior_end", [date(1977, 1, 31), date(1976, 12, 31)])
def test_a_prior_ending_in_the_onset_quarter_classifies_like_one_before(
    prior_end,
):
    """A January end constrains the start no more than a December one.

    Round 6 kept only the December end valid. Under the disregard that
    insures 1977Q1, the two records count the same quarters.
    """
    person, years, month = _shared_end_quarter_case(prior_end)
    _assert_earnings_refusal_row(person, years, month)
    result = i.insured_status(
        person, _filled(years, (4, 4, 4, 4)), month, test=i.InsuredTest.FULLY
    )
    assert result.current_disability_period_start == date(1977, 2, 15)
    _assert_invalid_without_row(person, _filled(years, (4, 4, 4, 0)), month)


@pytest.mark.parametrize("twentieth_quarter", [2, 3])
def test_alternate_exclusion_uses_existing_disability_scan_fra_boundary(
    twentieth_quarter,
):
    person = i.Person(
        date(1888, 5, 2),
        sex=i.Sex.FEMALE,
        disability_onset=date(1952, 7, 15),
        current_disability_period_established=True,
        current_disability_period_provenance=OBSERVED,
        current_disability_period_end=date(1952, 9, 30),
        current_disability_period_end_provenance=OBSERVED,
        prior_disability_periods_provenance=OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
    )
    month = date(1968, 1, 1)
    years = history(
        person,
        month,
        {
            1938: 2,
            1944: 4,
            1945: 4,
            1946: 4,
            1951: 4,
        },
    )
    years[1952] = i.CoverageYear(
        OBSERVED, qc_quarters=(True, True, False, True)
    )
    years[1953] = i.CoverageYear(
        OBSERVED,
        qc_quarters=tuple(q == twentieth_quarter for q in range(1, 5)),
    )
    assert i._fra_date(person) == date(1953, 5, 1)
    # Neither a post-end pre-FRA witness nor a post-FRA witness can
    # displace the possible alternate start in July 1952.
    row = _row(person, years, month)
    assert (
        row.unsupported.reason
        is i.InsuredUnsupportedReason.DISABILITY_BEFORE_1956
    )
    denominator = count_family_outcomes((row,))
    assert denominator.rows == denominator.unsupported_rows == 1
    assert (
        denominator.weight == denominator.unsupported_weight == Fraction(11, 5)
    )
