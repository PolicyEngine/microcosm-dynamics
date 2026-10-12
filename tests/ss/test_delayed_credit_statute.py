"""Statutory conformance for the sibling float 42 U.S.C. 402(w) function.

Admitted scope: delayed-credit fractions for supported cohorts, using only
invented claims and captured SSA tables. No population, behavioral, or
forecast claim. The literal table independently states FRA, annual rate,
and maximum months for every combined statutory band. January 1 births
belong to the preceding year's band, as POMS RS 00615.692D-E specifies.

The sealed oracle keeps its legacy 48-month convention. An explicit
``DelayedCreditWindow`` selects that oracle or the sibling statutory
function. Pre-1917 positive credits are refused by the statutory function;
the legacy convention preserves the registered paths' historical values.
"""

from __future__ import annotations

import hashlib
import math
from fractions import Fraction as F
from typing import NamedTuple

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.ss import benefits as sealed_oracle
from populace_dynamics.ss.statutory_delayed_credit import (
    DelayedCreditWindow,
    delayed_credit,
    oracle_delayed_credit,
)
from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import (
    SOURCES,
    manifest,
    poms_delayed_credit_chart,
    poms_delayed_credit_rates,
    source_text,
    ssa_params,
)

PARAMS = ssa_params()
FRA_TO_70_RULE = "42 U.S.C. 402(w)(2)(A), 402(w)(6); POMS RS 00615.692D/E"


class CohortRule(NamedTuple):
    first_year: int
    last_year: int | None
    fra_months: int
    annual_rate: F
    window_months: int
    poms_row: str
    citation: str = FRA_TO_70_RULE


# Every row cites 402(w)(2)(A), 402(w)(6), and RS 00615.692D/E through its
# literal citation field. Row figures are checked against the capture.
STATUTORY_TABLE = (
    CohortRule(
        1917,
        1924,
        780,
        F(3, 100),
        60,
        "01/02/17 thru 01/01/25 65 1/4% 3% 60 15.00%",
    ),
    CohortRule(
        1925,
        1926,
        780,
        F(7, 200),
        60,
        "01/02/25 thru 01/01/27 65 7/24% 3.5% 60 17.50%",
    ),
    CohortRule(
        1927,
        1928,
        780,
        F(4, 100),
        60,
        "01/02/27 thru 01/01/29 65 1/3% 4% 60 20.00%",
    ),
    CohortRule(
        1929,
        1930,
        780,
        F(9, 200),
        60,
        "01/02/29 thru 01/01/31 65 3/8% 4.5% 60 22.50%",
    ),
    CohortRule(
        1931,
        1932,
        780,
        F(5, 100),
        60,
        "01/02/31 thru 01/01/33 65 5/12% 5% 60 25.00%",
    ),
    CohortRule(
        1933,
        1934,
        780,
        F(11, 200),
        60,
        "01/02/33 thru 01/01/35 65 11/24% 5.5% 60 27.50%",
    ),
    CohortRule(
        1935,
        1936,
        780,
        F(6, 100),
        60,
        "01/02/35 thru 01/01/37 65 1/2% 6% 60 30.00%",
    ),
    CohortRule(
        1937,
        1937,
        780,
        F(13, 200),
        60,
        "01/02/37 thru 01/01/38 65 13/24% 6.5% 60 32.50%",
    ),
    CohortRule(
        1938,
        1938,
        782,
        F(13, 200),
        58,
        "01/02/38 thru 01/01/39 65&2 13/24% 6.5% 58 31.42%",
    ),
    CohortRule(
        1939,
        1939,
        784,
        F(7, 100),
        56,
        "01/02/39 thru 01/01/40 65&4 7/12% 7.0% 56 32.67%",
    ),
    CohortRule(
        1940,
        1940,
        786,
        F(7, 100),
        54,
        "01/02/40 thru 01/01/41 65&6 7/12% 7.0% 54 31.50%",
    ),
    CohortRule(
        1941,
        1941,
        788,
        F(3, 40),
        52,
        "01/02/41 thru 01/01/42 65&8 5/8% 7.5% 52 32.50%",
    ),
    CohortRule(
        1942,
        1942,
        790,
        F(3, 40),
        50,
        "01/02/42 thru 01/01/43 65&10 5/8% 7.5% 50 31.25%",
    ),
    CohortRule(
        1943,
        1954,
        792,
        F(8, 100),
        48,
        "01/02/43 thru 01/01/55 66 2/3% 8% 48 32.00%",
    ),
    CohortRule(
        1955,
        1955,
        794,
        F(8, 100),
        46,
        "01/02/55 thru 01/01/56 66&2 2/3% 8% 46 30.67%",
    ),
    CohortRule(
        1956,
        1956,
        796,
        F(8, 100),
        44,
        "01/02/56 thru 01/01/57 66&4 2/3% 8% 44 29.33%",
    ),
    CohortRule(
        1957,
        1957,
        798,
        F(8, 100),
        42,
        "01/02/57 thru 01/01/58 66&6 2/3% 8% 42 28.00%",
    ),
    CohortRule(
        1958,
        1958,
        800,
        F(8, 100),
        40,
        "01/02/58 thru 01/01/59 66&8 2/3% 8% 40 26.67%",
    ),
    CohortRule(
        1959,
        1959,
        802,
        F(8, 100),
        38,
        "01/02/59 thru 01/01/60 66&10 2/3% 8% 38 25.33%",
    ),
    CohortRule(
        1960,
        1960,
        804,
        F(8, 100),
        36,
        "After 01/01/60 67 2/3% 8% 36 24.00%",
    ),
    CohortRule(
        1961,
        None,
        804,
        F(8, 100),
        36,
        "After 01/01/60 67 2/3% 8% 36 24.00%",
    ),
)

POMS_RATE_QUOTES = (
    "After 01/01/43 2/3% .0066667 8%",
    "01/02/41 thru 01/01/43 5/8% .0062500 7.5%",
    "01/02/39 thru 01/01/41 7/12% .0058333 7%",
    "01/02/37 thru 01/01/39 13/24% .0054167 6.5%",
    "01/02/35 thru 01/01/37 1/2% .0050000 6%",
    "01/02/33 thru 01/01/35 11/24% .0045833 5.5%",
    "01/02/31 thru 01/01/33 5/12% .0041667 5%",
    "01/02/29 thru 01/01/31 3/8% .0037500 4.5%",
    "01/02/27 thru 01/01/29 1/3% .0033333 4%",
    "01/02/25 thru 01/01/27 7/24% .0029167 3.5%",
    "01/02/17 thru 01/01/25 1/4% .0025000 3%",
    "Before 01/02/17 1/12% .0008333 1%",
)
WORKED_EXAMPLE_QUOTES = (
    "PIA = $1000.00",
    "Date of birth = 06/15/1940",
    "30 DRCs apply at 7/12 of 1 percent per month",
    "$1000.00 times 30 times .01 times 7/12 = $175.00",
    "$1000.00 + $175.00 = $1175.00",
    "$1000.00 times 30 times .0058333 = $174.999 ($174.90 after rounding down)",
)

RULE_QUOTES = {
    "lii_usc_402_415": (
        "after the month before the month in which such individual "
        "attained retirement age",
        "prior to the month in which such individual attained age 70",
        "1 ⁄ 12 of 1 percent in the case of an individual who first "
        "becomes eligible for an old-age insurance benefit in any "
        "calendar year before 1979",
        "¼ of 1 percent in the case of an individual who first becomes "
        "eligible for an old-age insurance benefit in any calendar year "
        "after 1978 and before 1987",
        "plus 1 ⁄ 24 of 1 percent if the calendar year in which that "
        "particular individual first becomes eligible for such benefit "
        "is not evenly divisible by 2",
        "⅔ of 1 percent in the case of an individual who first becomes "
        "eligible for an old-age insurance benefit in a calendar year "
        "after 2004",
    ),
    "poms_rs_00615_692": (
        "D. Chart for Delayed Retirement Credits",
        "E. Chart for Maximum Delayed Retirement Credits",
    ),
}


def _cohort_rule(birth_year: int) -> CohortRule:
    return next(
        row
        for row in STATUTORY_TABLE
        if row.first_year <= birth_year
        and (row.last_year is None or birth_year <= row.last_year)
    )


@pytest.mark.parametrize("source_id", ("lii_usc_402_415", "poms_rs_00615_692"))
def test_cited_captures_match_the_source_manifest(source_id):
    entry = next(
        source for source in manifest()["sources"] if source["id"] == source_id
    )
    data = (SOURCES / entry["file"]).read_bytes()
    assert len(data) == entry["bytes"]
    assert hashlib.sha256(data).hexdigest() == entry["sha256"]


@pytest.mark.parametrize(
    ("source_id", "quote"),
    [
        (source_id, quote)
        for source_id, quotes in RULE_QUOTES.items()
        for quote in quotes
    ],
)
def test_rule_text_is_quoted_from_the_captures(source_id, quote):
    assert quote in source_text(source_id)


@pytest.mark.parametrize(
    "quote",
    [row.poms_row for row in STATUTORY_TABLE]
    + list(POMS_RATE_QUOTES)
    + list(WORKED_EXAMPLE_QUOTES),
)
def test_statutory_table_figures_are_quoted_from_the_capture(quote):
    assert quote in source_text("poms_rs_00615_692")


def test_literal_table_covers_every_combined_band_without_gaps_or_overlap():
    expected_start = 1917
    for row in STATUTORY_TABLE:
        assert row.first_year == expected_start
        assert row.citation == FRA_TO_70_RULE
        assert row.window_months == 840 - row.fra_months
        if row.last_year is None:
            assert row.first_year == 1961
        else:
            assert row.last_year >= row.first_year
            expected_start = row.last_year + 1


def _assert_statutory_window_and_rate_identity(birth_year):
    row = _cohort_rule(birth_year)
    chart = poms_delayed_credit_chart(1962)
    rates = poms_delayed_credit_rates()
    fra, monthly, maximum, displayed_percent = chart[birth_year]
    assert (fra, maximum) == (row.fra_months, row.window_months)
    assert maximum == 840 - PARAMS.fra_months(birth_year)
    assert PARAMS.fra_months(birth_year) == row.fra_months
    assert rates[birth_year] == (row.annual_rate / 12, row.annual_rate)
    assert monthly == row.annual_rate / 12
    # RS 00615.692E displays the maximum percent to two decimal places.
    assert round(100 * monthly * maximum, 2) == displayed_percent
    assert F(repr(PARAMS.delayed_credit_annual_rate(birth_year))) == (
        row.annual_rate
    )
    assert g.delayed_credit_window_months(birth_year, PARAMS) == maximum


@pytest.mark.parametrize("birth_year", range(1917, 1963))
def test_statutory_cohort_table_matches_both_captured_charts_and_bundle(
    birth_year,
):
    _assert_statutory_window_and_rate_identity(birth_year)


@settings(deadline=None)
@given(birth_year=st.integers(1917, 1962))
def test_statutory_window_and_rate_identity(birth_year):
    _assert_statutory_window_and_rate_identity(birth_year)


def test_poms_692_worked_example_reproduces_175_credit_and_1175_benefit():
    """RS 00615.692C: PIA 1000, 30 months at 7/12 of 1 percent.

    The oracle returns a float fraction, with at most 1e-12 error; cent
    rounding gives the published amounts. G reproduces them exactly and
    215(g)'s whole-dollar payment remains 1175.
    """
    credit = delayed_credit(30, 1940, PARAMS)
    assert abs(credit - float(F(175, 1000))) <= 1e-12
    assert round(1000.0 * credit, 2) == 175.00
    assert round(1000.0 + 1000.0 * credit, 2) == 1175.00
    assert math.floor(1000.0 + 1000.0 * credit) == 1175
    base, credited = g.worker_age_adjusted(F(1000), 0, 30, 1940, PARAMS)
    assert credited - base == F("175.00")
    assert credited == F("1175.00")
    assert g.whole_dollars(credited) == 1175
    decimal_credit = F(1000) * 30 * F(".0058333")
    assert decimal_credit == F("174.999")
    assert g.floor_dime(decimal_credit) == F("174.90")


@pytest.mark.parametrize("birth_year", range(1917, 1963))
def test_every_window_month_is_linear_and_age_70_has_the_full_credit(
    birth_year,
):
    row = _cohort_rule(birth_year)
    for months in range(row.window_months + 1):
        expected = float(months * row.annual_rate / 12)
        actual = delayed_credit(months, birth_year, PARAMS)
        assert isinstance(actual, float)
        assert abs(actual - expected) <= 1e-12
    expected_maximum = float(row.window_months * row.annual_rate / 12)
    assert (
        abs(
            delayed_credit(row.window_months, birth_year, PARAMS)
            - expected_maximum
        )
        <= 1e-12
    )


@pytest.mark.parametrize("birth_year", range(1917, 1963))
def test_each_of_24_months_after_age_70_keeps_the_window_credit(birth_year):
    row = _cohort_rule(birth_year)
    expected = float(row.window_months * row.annual_rate / 12)
    for extra in range(1, 25):
        assert (
            abs(
                delayed_credit(row.window_months + extra, birth_year, PARAMS)
                - expected
            )
            <= 1e-12
        )


@pytest.mark.parametrize("birth_year", range(1900, 1917))
def test_pre_1917_positive_credit_months_refuse_the_incorrect_bundle_rate(
    birth_year,
):
    monthly, annual = poms_delayed_credit_rates()[birth_year]
    assert (monthly, annual) == (F(1, 1200), F(1, 100))
    assert PARAMS.delayed_credit_annual_rate(birth_year) == 0.03
    for months in (1, 48, 60, 84):
        with pytest.raises(ValueError, match=r"402\(w\)\(6\)\(A\)"):
            delayed_credit(months, birth_year, PARAMS)


@pytest.mark.parametrize("birth_year", range(1900, 1963))
def test_nonpositive_credit_months_return_float_zero(birth_year):
    for months in (-120, -1, 0):
        result = delayed_credit(months, birth_year, PARAMS)
        assert isinstance(result, float)
        assert result == 0.0


def test_a_1960_birth_claiming_48_months_after_fra_gets_36_months_of_credit():
    assert delayed_credit(48, 1960, PARAMS) == 0.24
    assert delayed_credit(48, 1960, PARAMS) == delayed_credit(36, 1960, PARAMS)


@pytest.mark.parametrize("max_delayed_months", (0, 1, 36, 48, 60, 84, 120))
def test_bundle_maximum_does_not_bound_the_statutory_credit(
    max_delayed_months,
):
    bundle = ssa_params(max_delayed_months=max_delayed_months)
    assert bundle.max_delayed_months == max_delayed_months
    assert delayed_credit(60, 1935, bundle) == 0.30
    assert delayed_credit(48, 1960, bundle) == 0.24


@pytest.mark.parametrize("birth_year", range(1917, 1961))
@settings(deadline=None)
@given(months=st.integers(-240, 2400), added=st.integers(0, 2400))
def test_credit_is_monotone_in_entitlement_month(birth_year, months, added):
    assert delayed_credit(months, birth_year, PARAMS) <= delayed_credit(
        months + added, birth_year, PARAMS
    )


@pytest.mark.parametrize("birth_year", range(1917, 1961))
@settings(deadline=None)
@given(months=st.integers(-240, 2400))
def test_credit_is_nonnegative_and_bounded_by_the_age_70_credit(
    birth_year, months
):
    row = _cohort_rule(birth_year)
    maximum = float(row.window_months * row.annual_rate / 12)
    assert 0.0 <= delayed_credit(months, birth_year, PARAMS) <= maximum + 1e-12


@pytest.mark.parametrize("birth_year", range(1917, 1961))
@settings(deadline=None)
@given(data=st.data())
def test_credit_is_linear_within_the_full_window(birth_year, data):
    row = _cohort_rule(birth_year)
    months = data.draw(
        st.integers(0, row.window_months), label="credit months"
    )
    assert (
        abs(
            delayed_credit(months, birth_year, PARAMS)
            - float(months * row.annual_rate / 12)
        )
        <= 1e-12
    )


@pytest.mark.parametrize("birth_year", range(1917, 1961))
@settings(deadline=None)
@given(extra=st.integers(1, 10_000))
def test_entitlement_after_age_70_preserves_the_window_credit(
    birth_year, extra
):
    window = _cohort_rule(birth_year).window_months
    assert delayed_credit(window + extra, birth_year, PARAMS) == (
        delayed_credit(window, birth_year, PARAMS)
    )


@pytest.mark.parametrize("birth_year", range(1917, 1961))
@settings(deadline=None)
@given(data=st.data())
def test_credit_matches_gs_exact_fraction_over_the_whole_window(
    birth_year, data
):
    """PIA 2400 makes every G credit a whole dollar; tolerance is 1e-12.

    This removes rounding from the differential. G's recovered fraction
    remains exact; only the oracle's float representation has a tolerance.
    """
    window = _cohort_rule(birth_year).window_months
    months = data.draw(st.integers(0, window), label="credit months")
    base, credited = g.worker_age_adjusted(
        F(2400), 0, months, birth_year, PARAMS
    )
    fraction = (credited - base) / base
    assert fraction == months * _cohort_rule(birth_year).annual_rate / 12
    assert (
        abs(delayed_credit(months, birth_year, PARAMS) - float(fraction))
        <= 1e-12
    )


@settings(deadline=None)
@given(birth_year=st.integers(1900, 2200), months=st.integers(-10_000, 0))
def test_nonpositive_months_are_neutral_for_every_cohort(birth_year, months):
    assert delayed_credit(months, birth_year, PARAMS) == 0.0
    empty = ssa_params(
        fra_months_by_birth_year=[], delayed_credit_by_birth_year=[]
    )
    assert delayed_credit(months, birth_year, empty) == 0.0


@pytest.mark.parametrize("fra", (840, 841, 900))
def test_an_empty_window_returns_zero_without_a_credit_rate(fra):
    bundle = ssa_params(
        fra_months_by_birth_year=[(1900, fra)],
        delayed_credit_by_birth_year=[],
    )
    for months in (1, 48, 10_000):
        assert delayed_credit(months, 1935, bundle) == 0.0


@settings(deadline=None)
@given(
    birth_year=st.integers(1917, 2200),
    fra=st.integers(840, 1200),
    months=st.integers(1, 10_000),
)
def test_every_empty_window_is_zero_before_the_rate_lookup(
    birth_year, fra, months
):
    bundle = ssa_params(
        fra_months_by_birth_year=[(1900, fra)],
        delayed_credit_by_birth_year=[],
    )
    assert delayed_credit(months, birth_year, bundle) == 0.0


@settings(deadline=None)
@given(birth_year=st.integers(1900, 1916), months=st.integers(1, 10_000))
def test_pre_1917_positive_months_always_refuse(birth_year, months):
    with pytest.raises(ValueError, match=r"402\(w\)\(6\)\(A\)"):
        delayed_credit(months, birth_year, PARAMS)


@pytest.mark.parametrize("birth_year", range(1900, 1917))
def test_pre_1917_positive_credits_preserve_legacy_nonconforming_behavior(
    birth_year,
):
    """Preservation only: these 3-percent credits have no statutory admission."""
    for months in (1, 48, 60, 84):
        old_window = min(
            PARAMS.max_delayed_months, 840 - PARAMS.fra_months(birth_year)
        )
        old_credit = (
            min(months, old_window)
            / 12
            * (PARAMS.delayed_credit_annual_rate(birth_year))
        )
        assert (
            oracle_delayed_credit(
                months,
                birth_year,
                PARAMS,
                window=DelayedCreditWindow.LEGACY_48_MONTH_CAP,
            )
            == old_credit
        )


@settings(deadline=None)
@given(
    birth_year=st.integers(1900, 1916),
    months=st.integers(1, 10_000),
    maximum=st.integers(0, 120),
)
def test_pre_1917_legacy_nonconformance_is_preserved_by_convention(
    birth_year, months, maximum
):
    bundle = ssa_params(max_delayed_months=maximum)
    old_window = min(maximum, 840 - bundle.fra_months(birth_year))
    old_credit = (
        min(months, old_window)
        / 12
        * (bundle.delayed_credit_annual_rate(birth_year))
    )
    assert (
        oracle_delayed_credit(
            months,
            birth_year,
            bundle,
            window=DelayedCreditWindow.LEGACY_48_MONTH_CAP,
        )
        == old_credit
    )


@settings(deadline=None)
@given(birth_year=st.integers(1917, 2200), months=st.integers(-240, 2400))
def test_credit_is_deterministic(birth_year, months):
    first = delayed_credit(months, birth_year, PARAMS)
    assert delayed_credit(months, birth_year, PARAMS) == first
    assert delayed_credit(months, birth_year, ssa_params()) == first


@settings(deadline=None)
@given(
    birth_year=st.integers(1917, 2200),
    months=st.integers(-240, 2400),
    maximum=st.integers(-120, 10_000),
)
def test_credit_is_independent_of_the_bundle_maximum(
    birth_year, months, maximum
):
    bundle = ssa_params(max_delayed_months=maximum)
    assert delayed_credit(months, birth_year, bundle) == delayed_credit(
        months, birth_year, PARAMS
    )


def test_the_oracle_requires_an_explicit_window_convention():
    with pytest.raises(TypeError, match="window"):
        oracle_delayed_credit(60, 1935, PARAMS)
    with pytest.raises(ValueError):
        oracle_delayed_credit(60, 1935, PARAMS, window="unregistered")


@settings(deadline=None)
@given(
    birth_year=st.integers(1900, 2200),
    months=st.integers(-10_000, 10_000),
    maximum=st.integers(0, 120),
)
def test_legacy_convention_equals_the_sealed_oracle_everywhere(
    birth_year, months, maximum
):
    """Exact equality, including the bundle's pre-1917 legacy rate."""
    bundle = ssa_params(max_delayed_months=maximum)
    assert oracle_delayed_credit(
        months,
        birth_year,
        bundle,
        window=DelayedCreditWindow.LEGACY_48_MONTH_CAP,
    ) == sealed_oracle.delayed_credit(months, birth_year, bundle)


@settings(deadline=None)
@given(birth_year=st.integers(1917, 2200), months=st.integers(-240, 2400))
def test_statutory_convention_equals_the_statutory_function(
    birth_year, months
):
    assert oracle_delayed_credit(
        months, birth_year, PARAMS, window=DelayedCreditWindow.STATUTORY
    ) == delayed_credit(months, birth_year, PARAMS)


@settings(deadline=None)
@given(birth_year=st.integers(1900, 1916), months=st.integers(1, 10_000))
def test_statutory_convention_preserves_the_pre_1917_refusal(
    birth_year, months
):
    with pytest.raises(ValueError, match=r"402\(w\)\(6\)\(A\)"):
        oracle_delayed_credit(
            months, birth_year, PARAMS, window=DelayedCreditWindow.STATUTORY
        )


@settings(deadline=None)
@given(birth_year=st.integers(1943, 2200), months=st.integers(-240, 2400))
def test_conventions_agree_exactly_for_windows_at_most_48_months(
    birth_year, months
):
    assert 840 - PARAMS.fra_months(birth_year) <= 48
    assert oracle_delayed_credit(
        months, birth_year, PARAMS, window=DelayedCreditWindow.STATUTORY
    ) == oracle_delayed_credit(
        months,
        birth_year,
        PARAMS,
        window=DelayedCreditWindow.LEGACY_48_MONTH_CAP,
    )


@settings(deadline=None)
@given(birth_year=st.integers(1917, 2200), data=st.data())
def test_conventions_agree_exactly_within_the_shared_window(birth_year, data):
    shared_window = min(48, 840 - PARAMS.fra_months(birth_year))
    months = data.draw(st.integers(-240, shared_window), label="claim delay")
    assert oracle_delayed_credit(
        months, birth_year, PARAMS, window=DelayedCreditWindow.STATUTORY
    ) == oracle_delayed_credit(
        months,
        birth_year,
        PARAMS,
        window=DelayedCreditWindow.LEGACY_48_MONTH_CAP,
    )


@pytest.mark.parametrize(
    ("birth_year", "months", "legacy_credit", "statutory_credit"),
    [
        (1935, 60, 0.24, F(30, 100)),
        (1938, 58, 0.26, F(377, 1200)),
        (1942, 50, 0.30, F(3125, 10_000)),
    ],
)
def test_issue_494_differences_are_named_convention_choices(
    birth_year, months, legacy_credit, statutory_credit
):
    """Invented claims: #494's 0.30, 0.314167 and 0.3125 fractions."""
    legacy = oracle_delayed_credit(
        months,
        birth_year,
        PARAMS,
        window=DelayedCreditWindow.LEGACY_48_MONTH_CAP,
    )
    statutory = oracle_delayed_credit(
        months, birth_year, PARAMS, window=DelayedCreditWindow.STATUTORY
    )
    assert legacy == legacy_credit
    assert abs(statutory - float(statutory_credit)) <= 1e-12
    assert round(statutory, 6) == round(float(statutory_credit), 6)
    assert statutory > legacy


def test_the_largest_legacy_shortfall_is_1937_at_age_70():
    """An invented 1937 claim loses 12 months at 6.5%: 6.5% of PIA."""
    statutory = oracle_delayed_credit(
        60, 1937, PARAMS, window=DelayedCreditWindow.STATUTORY
    )
    legacy = oracle_delayed_credit(
        60, 1937, PARAMS, window=DelayedCreditWindow.LEGACY_48_MONTH_CAP
    )
    assert abs(statutory - 0.325) <= 1e-12
    assert abs(legacy - 0.26) <= 1e-12
    assert abs(statutory - legacy - 0.065) <= 1e-12
    assert round(1000 * (statutory - legacy), 2) == 65.00


@settings(deadline=None)
@given(birth_year=st.integers(1917, 1942), months=st.integers(49, 10_000))
def test_pre_1943_conventions_differ_only_by_months_above_48(
    birth_year, months
):
    """The statutory extra is the cohort rate times credited months past 48."""
    window = _cohort_rule(birth_year).window_months
    annual = _cohort_rule(birth_year).annual_rate
    statutory = oracle_delayed_credit(
        months, birth_year, PARAMS, window=DelayedCreditWindow.STATUTORY
    )
    legacy = oracle_delayed_credit(
        months,
        birth_year,
        PARAMS,
        window=DelayedCreditWindow.LEGACY_48_MONTH_CAP,
    )
    assert statutory > legacy
    extra_fraction = (min(months, window) - 48) * annual / 12
    assert F(0) < extra_fraction <= F(13, 200)
    assert abs(statutory - legacy - float(extra_fraction)) <= 1e-12


@settings(deadline=None)
@given(
    window=st.sampled_from(list(DelayedCreditWindow)),
    birth_year=st.integers(1917, 2200),
    months=st.integers(-240, 2400),
)
def test_window_convention_string_round_trip_preserves_results(
    window, birth_year, months
):
    assert DelayedCreditWindow(window.value) is window
    assert oracle_delayed_credit(
        months, birth_year, PARAMS, window=window.value
    ) == oracle_delayed_credit(months, birth_year, PARAMS, window=window)
