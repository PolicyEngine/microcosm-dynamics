"""Insured-status statutory conformance on invented and captured cases.

No population, behavioral, or forecast claim. Every history explicitly
states provenance, including the zero years before a worked record begins.
"""

import pickle
import re
import xml.etree.ElementTree as ET
from copy import copy, deepcopy
from dataclasses import replace
from datetime import date
from fractions import Fraction
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import insured_status as i
from populace_dynamics.track_b.gross_benefits import (
    InvalidFamilyInput,
    count_family_outcomes,
)

SOURCES = Path(__file__).parent / "data/track_b/insured_status_sources"
PROPERTY = settings(max_examples=25, deadline=None)


def declared(count=0, *, provenance=None, convention_id=None, year=2000):
    provenance = provenance or i.EarningsProvenance.OBSERVED
    if provenance is i.EarningsProvenance.UNKNOWN:
        return i.CoverageYear(provenance)
    values = {"qc_count": count}
    if year < 1978:
        values = {"qc_quarters": tuple(n < count for n in range(4))}
    return i.CoverageYear(provenance, convention_id=convention_id, **values)


def history(person, month, counts=None, *, end=None):
    counts = counts or {}
    last = min(month.year, end.year) if end else month.year
    if person.death_date is not None:
        last = min(last, person.death_date.year)
    return {
        year: declared(counts.get(year, 0), year=year)
        for year in range(max(1937, person.birth_date.year), last + 1)
    }


def compute(person, month, counts=None, **kwargs):
    return i.insured_status(
        person,
        history(person, month, counts, end=kwargs.get("coverage_end_month")),
        month,
        **kwargs,
    )


def qid(year, quarter):
    return year * 4 + quarter - 1


def statuses(result):
    return tuple(
        getattr(result, name).insured
        for name in ("fully", "currently", "disability")
    )


def test_version_and_explicit_zero_history():
    person = i.Person(date(1990, 5, 2))
    result = compute(person, date(2026, 12, 1))
    assert result.version == "track-b-insured-v1"
    assert not any(statuses(result))
    assert result.fully.required == 14
    assert result.currently.required == 6
    assert result.disability.required == 20
    assert result.unknown_years == ()
    assert result.convention_years == {}
    assert not result.decided_despite_unknowns
    assert set(result.qcs_by_year.values()) == {(0, 0)}


def test_fred_brown_35_quarters_require_17_poms_140_example_1():
    person = i.Person(date(1958, 5, 13), disability_onset=date(1988, 1, 15))
    result = compute(
        person,
        date(1988, 1, 1),
        {1980: 4, 1981: 4, 1982: 4, 1983: 4, 1984: 1},
    )
    assert result.disability.required == 17
    assert len(result.disability.window) == 35
    assert result.disability.window[0] == qid(1979, 3)
    assert result.disability.window[-1] == qid(1988, 1)
    assert result.disability.insured


def test_sam_white_6_in_12_poms_140_example_2():
    person = i.Person(date(1961, 8, 20), disability_onset=date(1984, 4, 12))
    result = compute(person, date(1984, 4, 1), {1982: 4, 1983: 2})
    assert result.disability.required == 6
    assert result.disability.window == tuple(
        range(qid(1981, 3), qid(1984, 2) + 1)
    )
    assert result.disability.insured


@pytest.mark.parametrize(
    "counts,expected",
    [
        ({1984: 4, 1985: 2}, True),
        ({1981: 4, 1982: 1, 1983: 1, 1984: 3}, False),
        ({1982: 3, 1984: 4, 1985: 1}, True),
    ],
    ids=["mary-example-3", "mary-example-4", "mary-example-5-moveable"],
)
def test_mary_smith_special_window_poms_140_examples_3_to_5(counts, expected):
    person = i.Person(date(1964, 11, 15), disability_onset=date(1985, 8, 30))
    result = compute(person, date(1985, 8, 1), counts)
    assert result.disability.required == 6
    assert result.disability.window == tuple(
        range(qid(1982, 4), qid(1985, 3) + 1)
    )
    assert result.disability.insured is expected


def test_dli_1990_june_poms_148_example():
    person = i.Person(date(1954, 3, 9))
    counts = {
        1973: 2,
        1975: 4,
        1976: 4,
        1980: 2,
        1981: 2,
        1982: 4,
        1985: 4,
        1986: 4,
        1987: 2,
        1988: 2,
    }
    result = compute(person, date(1991, 12, 1), counts)
    assert sum(pair[0] for pair in result.qcs_by_year.values()) == 30
    assert i.fully_insured_requirement(person, date(1990, 6, 1)) == 14
    assert result.dli.lower == result.dli.upper == date(1990, 6, 30)
    assert not result.dli.right_censored
    at_dli = compute(person, date(1990, 6, 1), counts)
    after_dli = compute(person, date(1990, 7, 1), counts)
    assert at_dli.disability.insured
    assert not after_dli.disability.insured


def test_calvin_hill_blind_clock_poms_150_example():
    person = i.Person(
        date(1957, 7, 12),
        disability_onset=date(1957, 7, 12),
        statutory_blindness=True,
    )
    counts = {1977: 2, 1982: 1, 1983: 1, 1985: 1, 1986: 2}
    first = history(person, date(1986, 1, 1), counts)
    first[1977] = i.CoverageYear(
        i.EarningsProvenance.OBSERVED,
        qc_quarters=(False, False, True, True),
    )
    march = i.insured_status(person, first, date(1986, 3, 1))
    april = i.insured_status(person, first, date(1986, 4, 1))
    assert march.fully.required == april.fully.required == 7
    assert march.fully.qc_count_lower == 6
    assert not march.disability.insured
    assert april.fully.qc_count_lower == 7
    assert april.disability.insured


def test_fully_requirement_differential_cfr_404_115_every_captured_row():
    document = ET.parse(SOURCES / "ecfr_20cfr404_subpart_b.xml")
    section = next(d for d in document.iter("DIV8") if d.get("N") == "404.115")
    tested = 0
    for row in section.findall(".//TBODY/TR"):
        cells = [
            "".join(cell.itertext()).strip() for cell in row.findall("TD")
        ]
        if not cells:
            continue
        years = [int(value) for value in re.findall(r"\b\d{4}\b", cells[0])]
        if "or earlier" in cells[0]:
            births = (date(years[0], 1, 1),)
        elif "or later" in cells[0]:
            births = (date(years[0], 1, 2), date(1960, 1, 2))
        else:
            births = (date(years[0], 1, 2), date(years[1], 1, 1))
        for birth in births:
            for sex, cell in (
                (i.Sex.MALE, cells[1]),
                (i.Sex.FEMALE, cells[2]),
            ):
                if not cell:
                    continue
                assert i.fully_insured_requirement(
                    i.Person(birth, sex=sex), date(2026, 12, 1)
                ) == int(cell)
                tested += 1
    assert tested >= 140


def _rs00301_800_exhibit_rows():
    text = (SOURCES / "poms_rs_00301_800_exhibit_pdftotext.txt").read_text(
        encoding="utf-8"
    )
    rows = re.findall(
        r"^\s*(\d{4}(?: or prior|-\d{4}| or later)?)\s+(\d{4})?\s*"
        r"(\d{4}(?: or prior| or later)?)\s+(\d{1,2})\b",
        text,
        re.M,
    )
    assert len(rows) == 38
    return rows


def test_fully_requirement_differential_poms_rs_00301_800_exhibit():
    """Every row of the RS 00301.800 exhibit, by birth cohort and death year.

    Men born before January 2, 1913 use age 65 and women age 62; from 1914
    one row serves both. Footnote 1: a January 1 birth takes the prior
    year's row. The death-year column is checked for a worker who attained
    21 before 1951 (born July 1, 1929) and dies that year.
    """
    tested = 0
    for men, women, event, required in _rs00301_800_exhibit_rows():
        required = int(required)
        years_in_cell = [int(y) for y in re.findall(r"\d{4}", men)]
        first, last = years_in_cell[0], years_in_cell[-1]
        cohorts = [
            (i.Sex.MALE, date(year, 7, 1) if year < 1913 else date(1913, 1, 1))
            for year in range(first, last + 1)
            if year <= 1913
        ]
        if first >= 1914:
            cohorts.append((i.Sex.MALE, date(first, 7, 1)))
        female_year = int(women) if women else first
        cohorts += [
            (i.Sex.FEMALE, date(female_year, 7, 1)),
            (i.Sex.FEMALE, date(female_year + 1, 1, 1)),
        ]
        for sex, birth in cohorts:
            age = 65 if sex is i.Sex.MALE and birth < date(1913, 1, 2) else 62
            month = date(birth.year + age + 1, 12, 1)
            person = i.Person(birth, sex=sex)
            assert i.fully_insured_requirement(person, month) == required, (
                men,
                women,
                sex,
                birth,
            )
            tested += 1
        years = [int(event[:4])]
        if "or prior" in event:
            years.append(int(event[:4]) - 2)
        if "or later" in event:
            years.append(int(event[:4]) + 14)
        for year in years:
            person = i.Person(
                date(1929, 7, 1),
                sex=i.Sex.FEMALE,
                death_date=date(year, 7, 1),
            )
            assert (
                i.fully_insured_requirement(person, date(year, 12, 1))
                == required
            ), (event, year)
            tested += 1
    assert tested >= 150


def test_elapsed_years_from_birth_not_projection_entry():
    person = i.Person(date(1980, 2, 2))
    assert i.fully_insured_requirement(person, date(2026, 1, 1)) == 24
    result = compute(person, date(2026, 1, 1), {2024: 4, 2025: 4, 2026: 1})
    assert not result.fully.insured
    assert result.fully.required == 24


def test_fully_requirement_excludes_partial_disability_years_cfr_example():
    plain = i.Person(date(1935, 1, 2))
    frozen = replace(
        plain,
        prior_disability_periods=(
            i.DisabilityPeriod(date(1975, 12, 5), date(1977, 1, 31)),
        ),
    )
    month = date(1980, 1, 1)
    assert (
        i.fully_insured_requirement(plain, month)
        - i.fully_insured_requirement(frozen, month)
        == 3
    )


def test_unknown_is_never_zero_and_named_refusal_stays_in_denominator():
    person = i.Person(date(2000, 2, 2))
    month = date(2026, 12, 1)
    years = history(person, month, {2025: 4})
    years[2024] = declared(provenance=i.EarningsProvenance.UNKNOWN)
    outcome = i.evaluate_insured_status(
        "unknown",
        Fraction(3, 2),
        lambda: i.insured_status(
            person, years, month, test=i.InsuredTest.FULLY
        ),
    )
    assert not outcome.supported
    assert (
        outcome.unsupported.reason.value
        == "unknown_earnings_years_decide_status"
    )
    denominator = count_family_outcomes((outcome,))
    assert denominator.rows == denominator.unsupported_rows == 1
    assert (
        denominator.weight == denominator.unsupported_weight == Fraction(3, 2)
    )


def test_decided_despite_unknown_reports_range_and_unknown_years():
    person = i.Person(date(2000, 2, 2))
    month = date(2026, 12, 1)
    years = history(person, month, {2025: 4, 2026: 4})
    years[2024] = declared(provenance=i.EarningsProvenance.UNKNOWN)
    result = i.insured_status(person, years, month, test=i.InsuredTest.FULLY)
    assert result.fully.insured
    assert result.decided_despite_unknowns
    assert result.unknown_years == (2024,)
    assert result.fully.qc_count_lower == 8
    assert result.fully.qc_count_upper == 12
    assert result.qcs_by_year[2024] == (0, 4)


def test_missing_year_and_provenance_are_input_errors():
    person = i.Person(date(2000, 2, 2))
    month = date(2026, 12, 1)
    years = history(person, month)
    del years[2010]
    with pytest.raises(InvalidFamilyInput):
        i.insured_status(person, years, month)
    with pytest.raises((InvalidFamilyInput, TypeError)):
        i.CoverageYear(qc_count=0)
    with pytest.raises(InvalidFamilyInput):
        i.CoverageYear("observed", qc_count=0)
    with pytest.raises(InvalidFamilyInput):
        i.CoverageYear(i.EarningsProvenance.UNKNOWN, qc_count=0)
    with pytest.raises(InvalidFamilyInput):
        i.CoverageYear(i.EarningsProvenance.CONVENTION_FILLED, qc_count=0)


@pytest.mark.parametrize(
    "change",
    [
        {"qc_count": 1, "wages": Fraction(1)},
        {"qc_count": True},
        {"qc_count": 5},
    ],
)
def test_ambiguous_or_malformed_direct_coverage_is_input_error(change):
    with pytest.raises(InvalidFamilyInput):
        i.CoverageYear(i.EarningsProvenance.OBSERVED, **change)


def test_before_1978_direct_qcs_require_quarter_flags():
    person = i.Person(date(1950, 2, 2))
    month = date(1977, 12, 1)
    years = history(person, month)
    years[1977] = i.CoverageYear(i.EarningsProvenance.OBSERVED, qc_count=2)
    with pytest.raises(InvalidFamilyInput):
        i.insured_status(person, years, month)


def test_totalization_is_named_refusal_and_empty_changes_nothing():
    person = i.Person(date(1990, 2, 2))
    month = date(2026, 12, 1)
    years = history(person, month)
    assert i.insured_status(person, years, month) == i.insured_status(
        person, years, month, totalization_credits=()
    )
    outcome = i.evaluate_insured_status(
        "foreign",
        Fraction(1),
        lambda: i.insured_status(
            person, years, month, totalization_credits=("UK:2020",)
        ),
    )
    assert (
        outcome.unsupported.reason.value == "totalization_credits_unsupported"
    )


def test_exit_freezes_credits_but_recent_work_clocks_continue():
    person = i.Person(date(1980, 2, 2))
    exit_month = date(2020, 12, 1)
    counts = {year: 4 for year in range(2011, 2021)}
    years = history(person, exit_month, counts)
    before = i.insured_status(
        person, years, exit_month, coverage_end_month=exit_month
    )
    after = i.insured_status(
        person, years, date(2031, 1, 1), coverage_end_month=exit_month
    )
    assert statuses(before) == (True, True, True)
    assert statuses(after) == (True, False, False)
    assert after.fully.required > before.fully.required
    assert after.qcs_by_year == before.qcs_by_year
    invalid = dict(years, **{})
    invalid[2021] = declared()
    with pytest.raises(InvalidFamilyInput):
        i.insured_status(
            person, invalid, date(2031, 1, 1), coverage_end_month=exit_month
        )


def test_results_outcomes_and_denominators_are_sealed():
    person = i.Person(date(2000, 2, 2))
    result = compute(person, date(2026, 12, 1))
    outcome = i.evaluate_insured_status("sealed", Fraction(1), lambda: result)
    denominator = count_family_outcomes((outcome,))
    for value in (result, result.fully, result.dli, outcome, denominator):
        for operation in (copy, deepcopy, replace, pickle.dumps):
            with pytest.raises(InvalidFamilyInput):
                operation(value)


@PROPERTY
@given(
    st.lists(st.integers(0, 4), min_size=10, max_size=10),
    st.integers(0, 9),
    st.sampled_from([1980, 1990, 2000]),
)
def test_property_status_and_dli_monotone_in_quarters(
    counts, index, birth_year
):
    person = i.Person(date(birth_year, 2, 2))
    month = date(2026, 12, 1)
    lower = dict(zip(range(2017, 2027), counts, strict=True))
    upper = dict(lower)
    upper[2017 + index] = min(4, upper[2017 + index] + 1)
    left = compute(person, month, lower)
    right = compute(person, month, upper)
    assert all(
        not old or new
        for old, new in zip(statuses(left), statuses(right), strict=True)
    )
    assert (right.dli.lower or date.min) >= (left.dli.lower or date.min)
    assert (right.dli.upper or date.min) >= (left.dli.upper or date.min)
    assert not left.disability.insured or left.fully.insured
    assert not right.disability.insured or right.fully.insured


@PROPERTY
@given(
    st.lists(st.integers(0, 4), min_size=10, max_size=10), st.integers(0, 9)
)
def test_property_unknown_bounds_cover_every_filling(counts, index):
    person = i.Person(date(1990, 2, 2))
    month = date(2026, 12, 1)
    years = history(
        person, month, dict(zip(range(2017, 2027), counts, strict=True))
    )
    unknown_year = 2017 + index
    years[unknown_year] = declared(provenance=i.EarningsProvenance.UNKNOWN)
    for selected, field in (
        (i.InsuredTest.FULLY, "fully"),
        (i.InsuredTest.CURRENTLY, "currently"),
        (i.InsuredTest.DISABILITY, "disability"),
    ):
        outcome = i.evaluate_insured_status(
            "bounds",
            Fraction(1),
            lambda selected=selected: i.insured_status(
                person, years, month, test=selected
            ),
        )
        concrete = []
        concrete_dates = []
        for filling in range(5):
            filled = dict(years)
            filled[unknown_year] = declared(filling)
            computed = i.insured_status(person, filled, month, test=selected)
            concrete.append(getattr(computed, field))
            if computed.dli is not None:
                concrete_dates.append(computed.dli.lower or date.min)
        if outcome.supported:
            decision = getattr(outcome.result, field)
            assert all(row.insured is decision.insured for row in concrete)
            assert all(
                decision.qc_count_lower
                <= row.qc_count_lower
                <= decision.qc_count_upper
                for row in concrete
            )
            if concrete_dates:
                assert all(
                    (outcome.result.dli.lower or date.min)
                    <= concrete_date
                    <= (outcome.result.dli.upper or date.min)
                    for concrete_date in concrete_dates
                )
        else:
            assert (
                outcome.unsupported.reason.value
                == "unknown_earnings_years_decide_status"
            )
            assert len({row.insured for row in concrete}) == 2


@PROPERTY
@given(st.lists(st.integers(0, 4), min_size=10, max_size=10))
def test_property_convention_equal_amounts_and_order_independence(counts):
    person = i.Person(date(1990, 2, 2))
    month = date(2026, 12, 1)
    years = history(
        person, month, dict(zip(range(2017, 2027), counts, strict=True))
    )
    observed = i.insured_status(person, years, month)
    reversed_result = i.insured_status(
        person, dict(reversed(tuple(years.items()))), month
    )
    assert observed == reversed_result
    filled = {
        year: replace(
            row,
            provenance=i.EarningsProvenance.CONVENTION_FILLED,
            convention_id="invented-zero-and-counts-v1",
        )
        for year, row in years.items()
    }
    convention = i.insured_status(person, filled, month)
    assert statuses(observed) == statuses(convention)
    assert observed.qcs_by_year == convention.qcs_by_year
    assert observed.dli == convention.dli
    assert convention.convention_years == {
        year: "invented-zero-and-counts-v1" for year in years
    }
    assert i.insured_status(person, years, month) == observed


@PROPERTY
@given(st.integers(1930, 2000), st.integers(1, 4))
def test_property_windows_and_blindness_rule(birth_year, quarter):
    person = i.Person(date(birth_year, 2, 2))
    month = date(2026, quarter * 3, 1)
    counts = {year: 4 for year in range(max(birth_year, 1990), 2026)}
    ordinary = compute(person, month, counts)
    blind = compute(replace(person, statutory_blindness=True), month, counts)
    assert len(ordinary.currently.window) == 13
    assert len(set(ordinary.currently.window)) == 13
    assert 6 <= ordinary.fully.required <= 40
    if ordinary.disability.rule == "under31_special":
        assert qid(2026, quarter) < qid(birth_year + 31, 1)
    if birth_year <= 1995:
        assert ordinary.disability.required == 20
        assert len(ordinary.disability.window) == 40
    assert blind.disability.insured is blind.fully.insured


@PROPERTY
@given(st.integers(1, 30), st.integers(0, 5))
def test_property_input_errors_are_atomic_before_refusal(
    weight, missing_offset
):
    person = i.Person(date(2000, 2, 2))
    month = date(2026, 12, 1)
    years = history(person, month)
    del years[2000 + missing_offset]
    with pytest.raises(InvalidFamilyInput):
        i.evaluate_insured_status(
            "invalid",
            Fraction(weight),
            lambda: i.insured_status(
                person, years, month, totalization_credits=("foreign",)
            ),
        )


@PROPERTY
@given(st.integers(0, 100), st.integers(0, 100))
def test_property_refusal_denominator_conserves_rows_and_weights(left, right):
    person = i.Person(date(2000, 2, 2))
    month = date(2026, 12, 1)
    years = history(person, month)
    supported = i.evaluate_insured_status(
        "supported",
        Fraction(left, 3),
        lambda: i.insured_status(person, years, month),
    )
    refused = i.evaluate_insured_status(
        "refused",
        Fraction(right, 7),
        lambda: i.insured_status(
            person, years, month, totalization_credits=("foreign",)
        ),
    )
    rows = (supported, refused)
    denominator = count_family_outcomes(rows)
    assert denominator == count_family_outcomes(tuple(reversed(rows)))
    assert (
        denominator.rows
        == denominator.supported_rows + denominator.unsupported_rows
        == 2
    )
    assert (
        denominator.weight
        == denominator.supported_weight + denominator.unsupported_weight
        == Fraction(left, 3) + Fraction(right, 7)
    )


@PROPERTY
@given(
    st.integers(2010, 2023),
    st.lists(st.integers(0, 4), min_size=2, max_size=2),
)
def test_property_disability_period_exclusion_never_adds_qcs(
    start_year, counts
):
    person = i.Person(date(1980, 2, 2))
    frozen = replace(
        person,
        prior_disability_periods=(
            i.DisabilityPeriod(
                date(start_year, 4, 2), date(start_year + 1, 8, 2)
            ),
        ),
    )
    month = date(2026, 12, 1)
    annual = {start_year: counts[0], start_year + 1: counts[1]}
    plain = compute(person, month, annual)
    excluded = compute(frozen, month, annual)
    for year in plain.qcs_by_year:
        assert excluded.qcs_by_year[year][0] <= plain.qcs_by_year[year][0]
        assert excluded.qcs_by_year[year][1] <= plain.qcs_by_year[year][1]
    unavailable = set(range(qid(start_year, 3), qid(start_year + 1, 3)))
    assert unavailable.isdisjoint(
        quarter
        for quarters in excluded.assigned_quarters.values()
        for quarter in quarters
    )


def test_unknown_upper_bound_respects_exit_quarter():
    person = i.Person(date(2000, 2, 2))
    exit_month = date(2026, 4, 1)
    years = history(person, exit_month, {2024: 4, 2025: 4})
    years[2026] = declared(provenance=i.EarningsProvenance.UNKNOWN)
    result = i.insured_status(
        person,
        years,
        date(2027, 1, 1),
        coverage_end_month=exit_month,
        test=i.InsuredTest.FULLY,
    )
    assert result.qcs_by_year[2026] == (0, 2)
    assert result.fully.insured


def test_special_insured_quarter_before_31_boundary():
    person = i.Person(date(1995, 11, 15))
    counts = {2018: 4, 2019: 4, 2020: 4, 2021: 4, 2022: 3}
    before = compute(person, date(2026, 7, 1), counts)
    attainment_quarter = compute(person, date(2026, 10, 1), counts)
    assert before.disability.required == 19
    assert before.disability.insured
    assert attainment_quarter.disability.required == 20
    assert not attainment_quarter.disability.insured


def test_joseph_subsequent_poms_140_example_6_endpoint_erratum():
    person = i.Person(
        date(1956, 9, 16),
        disability_onset=date(1984, 2, 14),
        prior_disability_periods=(
            i.DisabilityPeriod(
                date(1981, 2, 3), date(1982, 12, 31), special_insured=True
            ),
        ),
    )
    result = compute(
        person,
        date(1984, 2, 1),
        {1978: 2, 1979: 3, 1980: 4, 1981: 1, 1982: 2, 1983: 4, 1984: 1},
    )
    assert result.disability.insured
    # The capture says 18 elapsed / 9 needed. Under .240 and 404.130(f),
    # its credited first/last quarters remain: 26 total - 6 interior =20.
    source_elapsed, source_required = 18, 9
    assert len(result.disability.window) == source_elapsed + 2 == 20
    assert result.disability.required == source_required + 1 == 10
    assert result.disability.qc_count_lower == 16


@pytest.mark.parametrize(
    "birth,onset,start,end,counts,required,window_length",
    [
        (
            date(1967, 3, 16),
            date(1990, 12, 3),
            date(1988, 3, 29),
            date(1990, 10, 31),
            {1986: 3, 1987: 3},
            6,
            12,
        ),
        (
            date(1967, 4, 12),
            date(1997, 3, 16),
            date(1988, 2, 16),
            date(1990, 12, 31),
            {1986: 1, 1987: 4, 1988: 1, 1993: 2, 1994: 3, 1995: 4, 1996: 3},
            12,
            25,
        ),
    ],
    ids=["jane-example-7", "ralph-example-8"],
)
def test_subsequent_under31_poms_140_examples_7_and_8(
    birth, onset, start, end, counts, required, window_length
):
    person = i.Person(
        birth,
        disability_onset=onset,
        prior_disability_periods=(
            i.DisabilityPeriod(start, end, special_insured=True),
        ),
    )
    result = compute(person, onset.replace(day=1), counts)
    assert result.disability.insured
    assert result.disability.required == required
    assert result.disability.qc_count_lower == required
    assert len(result.disability.window) == window_length


def test_sam_subsequent_poms_140_example_9_favorable_disregard_erratum():
    person = i.Person(
        date(1964, 2, 16),
        disability_onset=date(1993, 5, 16),
        prior_disability_periods=(
            i.DisabilityPeriod(
                date(1985, 12, 16), date(1989, 12, 31), special_insured=True
            ),
        ),
    )
    counts = {1983: 2, 1984: 4, 1988: 4, 1989: 4, 1992: 4, 1993: 4}
    result = compute(person, date(1993, 5, 1), counts)
    # Source says 17 elapsed / 8 needed / 7 available after exclusion.
    # CFR404.130(f) requires favorable disregard of the entire period.
    source_elapsed, source_required, source_qcs = 17, 8, 7
    assert source_qcs < source_required == source_elapsed // 2
    assert result.disability.insured
    assert result.disability.rule == "disability_20_of_40"
    assert result.disability.required == result.disability.qc_count_lower == 20
    assert tuple(
        q for q in result.disability.assigned_quarters if q // 4 == 1983
    ) == (qid(1983, 3), qid(1983, 4))
    # Disregarding all periods produces the identical qualifying witness.
    ignored = compute(
        replace(person, prior_disability_periods=()), date(1993, 5, 1), counts
    )
    assert ignored.disability.insured
    assert ignored.disability.qc_count_lower == 20


@settings(max_examples=12, deadline=None)
@given(st.integers(1978, 1982), st.integers(0, 4))
def test_property_subsequent_special_and_dli_monotonic(year, count):
    person = i.Person(
        date(1950, 4, 16),
        prior_disability_periods=(
            i.DisabilityPeriod(
                date(1975, 5, 16), date(1978, 12, 31), special_insured=True
            ),
        ),
    )
    month = date(1983, 6, 1)
    lower = {
        1970: 1,
        1971: 2,
        1972: 3,
        1973: 2,
        1974: 2,
        1978: 4,
        1979: 1,
        1980: 1,
        1981: 1,
        1982: 3,
    }
    lower[year] = count
    upper = dict(lower)
    upper[year] = min(4, count + 1)
    a = compute(person, month, lower)
    b = compute(person, month, upper)
    assert all(
        not old or new
        for old, new in zip(statuses(a), statuses(b), strict=True)
    )
    assert (b.dli.lower or date.min) >= (a.dli.lower or date.min)
    assert a.disability.rule in {"subsequent_special", "disability_20_of_40"}
    assert b.disability.rule in {"subsequent_special", "disability_20_of_40"}


@pytest.mark.parametrize("count,expected", [(5, False), (6, True)])
def test_currently_six_qcs_boundary(count, expected):
    person = i.Person(date(1990, 2, 2))
    result = compute(
        person,
        date(2026, 12, 1),
        {2025: 4, 2026: count - 4},
        test=i.InsuredTest.CURRENTLY,
    )
    assert result.currently.required == 6
    assert result.currently.insured is expected


@pytest.mark.parametrize("count,expected", [(19, False), (20, True)])
def test_disability_twenty_qcs_boundary(count, expected):
    person = i.Person(date(1990, 2, 2))
    counts = {2021: 4, 2022: 4, 2023: 4, 2024: 4, 2025: count - 16}
    result = compute(person, date(2026, 12, 1), counts)
    assert result.fully.insured
    assert result.disability.required == 20
    assert result.disability.insured is expected


@pytest.mark.parametrize("count,expected", [(5, False), (6, True)])
def test_fully_six_qcs_minimum(count, expected):
    person = i.Person(date(2000, 2, 2))
    result = compute(
        person,
        date(2026, 12, 1),
        {2025: 4, 2026: count - 4},
        test=i.InsuredTest.FULLY,
    )
    assert result.fully.required == 6
    assert result.fully.insured is expected


def test_guinness_lis_poms_120_freeze_protects_onset_status():
    # The capture supplies insured status at onset, not a DOB/full record.
    # This invented completion realizes its declared 20-QC premise.
    person = i.Person(date(1940, 2, 2), disability_onset=date(1977, 12, 15))
    counts = {year: 4 for year in range(1973, 1978)}
    onset = compute(person, date(1977, 12, 1), counts)
    waiting = compute(person, date(1987, 2, 1), counts)
    assert onset.disability.insured
    assert waiting.disability.insured
    assert (
        onset.disability.qc_count_lower
        == waiting.disability.qc_count_lower
        == 20
    )
    assert onset.disability.window == waiting.disability.window
    assert onset.disability.window[-1] == qid(1977, 4)


@pytest.mark.parametrize(
    "birth,onset,start,end,patterns,insured,required,available,elapsed",
    [
        (
            date(1950, 4, 16),
            date(1982, 11, 2),
            date(1975, 5, 16),
            date(1978, 12, 31),
            {
                1970: "NNNC",
                1971: "NNCC",
                1972: "CCCN",
                1973: "CNNC",
                1974: "NNCC",
                1976: "CNNN",
                1978: "CCCC",
                1979: "CNNN",
                1980: "CNNN",
                1981: "CNNN",
                1982: "CCCN",
            },
            True,
            16,
            16,
            32,
        ),
        (
            date(1940, 7, 16),
            date(1983, 2, 11),
            date(1968, 3, 4),
            date(1981, 6, 30),
            {
                1961: "NNNC",
                1962: "NCCN",
                1963: "NNCC",
                1964: "CCNC",
                1966: "CCNN",
                1967: "CNCC",
                1970: "NNCC",
                1977: "NNNC",
                1980: "CCCC",
                1981: "CCCC",
                1982: "CCNN",
            },
            True,
            16,
            18,
            33,
        ),
        (
            date(1945, 7, 14),
            date(1983, 2, 11),
            date(1970, 12, 13),
            date(1978, 11, 30),
            {
                1967: "CNCN",
                1968: "NNCC",
                1969: "NNNC",
                1970: "CCCN",
                1976: "NCCN",
                1978: "CNNN",
            },
            False,
            17,
            9,
            34,
        ),
    ],
    ids=[
        "mary-brown-example-1",
        "john-jones-example-2",
        "frank-smith-example-3-moveable-qc-erratum",
    ],
)
def test_subsequent_over31_poms_147_examples(
    birth, onset, start, end, patterns, insured, required, available, elapsed
):
    person = i.Person(
        birth,
        disability_onset=onset,
        prior_disability_periods=(
            i.DisabilityPeriod(start, end, special_insured=True),
        ),
    )
    years = history(person, date(1983, 6, 1))
    for year, pattern in patterns.items():
        values = (
            {"qc_quarters": tuple(letter == "C" for letter in pattern)}
            if year < 1978
            else {"qc_count": pattern.count("C")}
        )
        years[year] = i.CoverageYear(i.EarningsProvenance.OBSERVED, **values)
    result = i.insured_status(person, years, date(1983, 6, 1))
    assert result.disability.insured is insured
    assert result.disability.required == required
    assert result.disability.qc_count_lower == available
    assert len(result.disability.window) == elapsed
    assert result.disability.rule == "subsequent_special"
    if birth == date(1945, 7, 14):
        # Source freezes 1978 CNNN in Q1. .230 permits moving it to Q4,
        # the last PPD quarter; .240 then retains it in both counts.
        source_elapsed, source_required, source_available = 33, 16, 8
        assert elapsed == source_elapsed + 1
        assert required == source_required + 1
        assert available == source_available + 1
        assert qid(1978, 4) in result.disability.assigned_quarters


def test_sam_favorable_disregard_counterexample_one_qc_boundary():
    person = i.Person(
        date(1964, 2, 16),
        disability_onset=date(1993, 5, 16),
        prior_disability_periods=(
            i.DisabilityPeriod(
                date(1985, 12, 16), date(1989, 12, 31), special_insured=True
            ),
        ),
    )
    counts = {1983: 1, 1984: 4, 1988: 4, 1989: 4, 1992: 4, 1993: 2}
    below = compute(person, date(1993, 5, 1), counts)
    counts[1983] = 2
    at = compute(person, date(1993, 5, 1), counts)
    assert not below.disability.insured
    assert at.disability.insured
    assert at.disability.qc_count_lower == 20


def test_dli_fra_cap_poms_148_november_2019():
    # The source specifies FRA11/2019, not a birth date or earnings record.
    # This invented completion has at least40QCs before that FRA quarter.
    person = i.Person(date(1953, 11, 2))
    result = compute(
        person, date(2019, 12, 1), {year: 4 for year in range(2009, 2020)}
    )
    assert result.dli.lower == result.dli.upper == date(2019, 9, 30)
    assert not result.dli.right_censored


def test_age_attainment_day_before_birthday_cfr_404_102_example():
    assert i._attain(date(1917, 7, 1), 62) == date(1979, 6, 30)
