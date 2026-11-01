"""Round 16: exact diagnostics and the aggregate below six ordinary QCs.

Verification class: statutory conformance on invented declarations; no
population, behavioral or forecast claim. Where annual placement can move the
first insured start, each status's exact count and assignment must rest on a
filling whose own first start is the reported start (404.321(a); RS 00301.230;
source conflict us:oasdi-insured-one-filling-first-start).

A blind person's date last insured needs no recent QCs, so fewer than six
ordinary QCs don't settle it while Act 213(c)'s aggregate could still meet the
fully insured requirement (source conflict
us:oasdi-insured-simplified-pre1951-disability-scope).
"""

from dataclasses import replace
from datetime import date
from fractions import Fraction
from itertools import combinations, product

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import insured_status as i
from populace_dynamics.track_b.gross_benefits import count_family_outcomes

OBSERVED = i.EarningsProvenance.OBSERVED
UNKNOWN = i.EarningsProvenance.UNKNOWN
ASSIGNMENT = i.InsuredUnsupportedReason.ASSIGNMENT_COMPLEXITY
SIMPLIFIED = i.InsuredUnsupportedReason.SIMPLIFIED_PRE1951
WEIGHT = Fraction(11, 3)
BIRTH = date(1962, 2, 2)
ONSET = date(2010, 1, 15)
QUERY = date(2011, 1, 1)
# Nineteen QCs from 2001 through 2005 leave the 2000 QC to reach 20 of 40 at
# the onset, and only 2000Q2-Q4 sit in that window.
LATER = {2000: 1, 2001: 4, 2002: 4, 2003: 4, 2004: 4, 2005: 3}
PLAIN = {1998: 4, 1999: 2, **LATER}
EARLIER = {1990: 4, 1991: 4, 1992: 4, 1993: 2, **PLAIN}
FULL_HISTORY = {1990: 4, 1991: 4}
PRIOR = i.DisabilityPeriod(date(1999, 10, 1), date(2000, 3, 31))
BLIND_BIRTH = date(1926, 2, 2)
BLIND_QUERY = date(1974, 1, 1)
# Nineteen QCs through 1999 leave the 2000 QC to reach 20 of 40, so a first
# insured quarter of 2000Q1 holds that QC there.
TIGHT = {1995: 3, 1996: 4, 1997: 4, 1998: 4, 1999: 4, 2000: 1}
STARTED = date(2000, 1, 1)


def q(year, number):
    return year * 4 + number - 1


def _history(first, last, counts):
    return {
        year: (
            i.CoverageYear(OBSERVED, qc_count=counts.get(year, 0))
            if year >= 1978
            else i.CoverageYear(OBSERVED, qc_quarters=(False,) * 4)
        )
        for year in range(first, last + 1)
    }


def _established(entitlement, *priors, **changes):
    values = dict(
        sex=i.Sex.FEMALE,
        disability_onset=ONSET,
        current_disability_period_established=True,
        current_disability_period_provenance=OBSERVED,
        current_disability_period_end=date(2010, 12, 31),
        current_disability_period_end_provenance=OBSERVED,
        prior_disability_periods=priors,
        prior_disability_periods_provenance=OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
        dib_entitlement_month=entitlement,
    )
    values.update(changes)
    return i.Person(BIRTH, **values)


def _plain():
    return _established(date(2000, 1, 1))


def _tight(end, provenance=OBSERVED):
    return _established(
        None,
        disability_onset=date(1999, 6, 15),
        current_disability_period_end=end,
        current_disability_period_end_provenance=provenance,
    )


def _with_prior():
    return _established(date(2000, 3, 1), PRIOR)


def _blind(**changes):
    values = dict(
        sex=i.Sex.FEMALE,
        statutory_blindness=True,
        current_disability_period_established=False,
        current_disability_period_provenance=OBSERVED,
        prior_disability_periods=(),
        prior_disability_periods_provenance=OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
    )
    values.update(changes)
    return i.Person(BLIND_BIRTH, **values)


def _single_quarter(amount):
    return i.CoverageYear(
        OBSERVED,
        quarterly_wages=(
            Fraction(amount),
            Fraction(0),
            Fraction(0),
            Fraction(0),
        ),
    )


def _blind_years(amounts, last=1974):
    years = _history(1937, last, {})
    for year, amount in amounts.items():
        years[year] = _single_quarter(amount)
    return years


def _refused_row(person, years, month, reason, **options):
    row = i.evaluate_insured_status(
        "round-sixteen",
        WEIGHT,
        lambda: i.insured_status(person, years, month, **options),
    )
    counts = count_family_outcomes((row,))
    assert (counts.rows, counts.weight, counts.unsupported_weight) == (
        1,
        WEIGHT,
        WEIGHT,
    )
    assert row.unsupported.reason is reason
    return row


CASES = (
    pytest.param(_plain, PLAIN, id="no-prior"),
    pytest.param(_with_prior, EARLIER, id="prior"),
)


@pytest.mark.parametrize(("person", "counts"), CASES)
@pytest.mark.parametrize("test", (i.InsuredTest.CURRENTLY, i.InsuredTest.ALL))
@pytest.mark.parametrize(
    ("exit_month", "last"), ((None, 2011), (date(2005, 12, 1), 2005))
)
def test_count_and_assignment_keep_the_reported_start(
    person, counts, test, exit_month, last
):
    result = i.insured_status(
        person(),
        _history(1962, last, counts),
        QUERY,
        coverage_end_month=exit_month,
        test=test,
    )
    assert result.current_disability_period_start == ONSET
    decision = result.currently
    assert decision.insured
    assert (decision.qc_count_lower, decision.qc_count_upper) == (6, 6)
    assert q(2000, 1) not in decision.assigned_quarters
    # The 13-quarter window can't reach a 2000 QC the start needs later.
    assert (
        sum(1998 * 4 <= x < 2000 * 4 for x in decision.assigned_quarters) >= 6
    )


@pytest.mark.parametrize(("person", "counts"), CASES)
def test_every_exact_diagnostic_rests_on_one_filling(person, counts):
    result = i.insured_status(person(), _history(1962, 2011, counts), QUERY)
    assert q(2000, 1) not in result.assigned_quarters[2000]
    assert len(result.assigned_quarters[2000]) == 1
    assert q(2000, 1) not in result.fully.assigned_quarters
    assert result.fully.insured and result.disability.insured
    assert result.dli.upper == result.dli.lower == date(2011, 3, 31)


def test_a_fixed_start_keeps_the_favorable_count():
    # A twentieth later QC frees the 2000 QC to reach the 13-quarter window.
    counts = {**PLAIN, 2005: 4}
    result = i.insured_status(_plain(), _history(1962, 2011, counts), QUERY)
    decision = result.currently
    assert (decision.qc_count_lower, decision.qc_count_upper) == (7, 7)
    assert q(2000, 1) in decision.assigned_quarters


def test_fully_only_keeps_its_status_and_count_under_a_moving_start():
    years = _history(1962, 2011, PLAIN)
    result = i.insured_status(_plain(), years, QUERY, test=i.InsuredTest.FULLY)
    assert result.fully.insured
    assert (result.fully.qc_count_lower, result.fully.required) == (26, 26)


def test_a_status_only_the_moved_placement_met_refuses():
    # 1998:3 leaves five QCs in the window once the 2000 QC keeps the start.
    counts = {**FULL_HISTORY, **PLAIN, 1998: 3}
    _refused_row(
        _plain(),
        _history(1962, 2011, counts),
        QUERY,
        ASSIGNMENT,
        test=i.InsuredTest.CURRENTLY,
    )


def _envelope(decision):
    return (
        decision.qc_count_lower,
        decision.qc_count_upper,
        decision.fully_qc_count_lower,
        decision.fully_qc_count_upper,
    )


@pytest.mark.parametrize(
    ("test", "name"),
    ((i.InsuredTest.FULLY, "fully"), (i.InsuredTest.CURRENTLY, "currently")),
)
def test_unknown_years_keep_the_universal_envelope(test, name):
    # 1995 sits outside every window that fixes the start, so the 2000 QC
    # still moves it, and UNKNOWN earnings leave only the outer bound.
    years = _history(1962, 2011, PLAIN)
    years[1995] = i.CoverageYear(UNKNOWN)
    result = i.insured_status(_plain(), years, QUERY, test=test)
    assert result.unknown_years == (1995,)
    assert _envelope(getattr(result, name)) == (0, 30, 0, 30)


def test_unknown_priors_keep_the_universal_envelope():
    person = replace(
        _plain(),
        prior_disability_periods=(),
        prior_disability_periods_provenance=UNKNOWN,
    )
    result = i.insured_status(
        person,
        _history(1962, 2011, PLAIN),
        QUERY,
        test=i.InsuredTest.CURRENTLY,
    )
    assert _envelope(result.currently) == (0, 26, 0, 26)


def test_an_unknown_ending_keeps_each_endings_witness():
    person = replace(
        _plain(),
        current_disability_period_end=None,
        current_disability_period_end_provenance=UNKNOWN,
    )
    result = i.insured_status(
        person,
        _history(1962, 2011, PLAIN),
        QUERY,
        test=i.InsuredTest.CURRENTLY,
    )
    decision = result.currently
    assert decision.insured
    assert (decision.qc_count_lower, decision.qc_count_upper) == (6, 6)
    assert q(2000, 1) not in decision.assigned_quarters


def test_an_unknown_ending_reports_each_requirement_in_its_own_field():
    # A later ending excludes more elapsed years, so the last ending sets
    # the lower requirement and the first sets the upper.
    person = replace(
        _established(
            None,
            disability_onset=date(1992, 1, 15),
            current_disability_period_end=None,
            current_disability_period_end_provenance=UNKNOWN,
        ),
        birth_date=date(1956, 2, 2),
    )
    counts = {
        1978: 2,
        1987: 2,
        1988: 4,
        1989: 3,
        1990: 4,
        1991: 4,
        1992: 2,
        1994: 1,
    }
    decision = i.insured_status(
        person,
        _history(1956, 1998, counts),
        date(1998, 7, 1),
        test=i.InsuredTest.FULLY,
    ).fully
    assert (decision.required, decision.upper_required) == (16, 19)


@pytest.mark.parametrize(
    ("end", "count"),
    (
        (date(2000, 6, 30), 6),
        (date(2000, 9, 30), 7),
        (date(2001, 12, 31), 8),
    ),
)
def test_a_later_ending_meets_currently_at_the_reported_start(end, count):
    result = i.insured_status(
        _tight(end),
        _history(1962, 2003, {**TIGHT, 2001: 4, 2002: 1}),
        date(2003, 4, 1),
        test=i.InsuredTest.CURRENTLY,
    )
    decision = result.currently
    assert result.current_disability_period_start == STARTED
    assert result.assigned_quarters[2000] == (q(2000, 1),)
    assert decision.insured
    assert (decision.qc_count_lower, decision.qc_count_upper) == (count, count)


@pytest.mark.parametrize(
    ("end", "provenance"),
    ((date(2000, 3, 31), OBSERVED), (None, UNKNOWN)),
    ids=("first-quarter-ending", "unknown-ending"),
)
def test_an_ending_the_reported_start_fails_refuses(end, provenance):
    # Ending in 2000Q1 windows 2000Q2-2003Q2. The 2000 QC reaches six there
    # only outside 2000Q1, which moves the start. An unknown ending includes
    # that one, so its later endings can't carry the status.
    _refused_row(
        _tight(end, provenance),
        _history(1962, 2003, {**TIGHT, 2001: 4, 2002: 1}),
        date(2003, 4, 1),
        ASSIGNMENT,
        test=i.InsuredTest.CURRENTLY,
    )


@pytest.mark.parametrize("test", (i.InsuredTest.DISABILITY, i.InsuredTest.ALL))
def test_a_date_only_a_moved_placement_reaches_refuses(test):
    # Nineteen QCs from 2001 through 2005 need the 2000 QC for 20 of 40 after
    # 2009, and the latest date needs it in 2000Q2 or later.
    counts = {**TIGHT, 2001: 4, 2002: 4, 2003: 4, 2004: 4, 2005: 3}
    _refused_row(
        _tight(date(2000, 3, 31)),
        _history(1962, 2012, counts),
        date(2012, 1, 1),
        ASSIGNMENT,
        test=test,
    )


def test_a_date_the_reported_start_reaches_computes():
    counts = {**TIGHT, 2001: 4, 2002: 4, 2003: 4, 2004: 4, 2005: 4}
    result = i.insured_status(
        _tight(date(2000, 3, 31)),
        _history(1962, 2012, counts),
        date(2012, 1, 1),
    )
    assert result.current_disability_period_start == STARTED
    assert result.dli.lower == result.dli.upper == date(2010, 12, 31)


def _lawful_currently(counts):
    """Exhaust placements in plain arithmetic for the no-prior record.

    FULL_HISTORY's eight QCs sit outside both windows and meet fully at 26.
    """
    options = [
        combinations(range(year * 4, year * 4 + 4), count)
        for year, count in sorted(counts.items())
    ]
    window = range(q(2000, 1) - 12, q(2000, 1) + 1)
    onset_window = range(q(2010, 1) - 39, q(2010, 1) + 1)
    best = None
    for pieces in product(*options):
        credits = {credit for piece in pieces for credit in piece}
        if len(credits) + 8 < 26:
            continue
        if sum(credit in onset_window for credit in credits) < 20:
            continue
        held = sum(credit in window for credit in credits)
        best = held if best is None else max(best, held)
    return best


@settings(max_examples=40, deadline=None)
@example(early=4, middle=2, later=4, last=3)
@example(early=4, middle=2, later=4, last=4)
@example(early=2, middle=3, later=2, last=3)
@given(
    early=st.integers(1, 4),
    middle=st.integers(1, 3),
    later=st.integers(1, 4),
    last=st.integers(2, 4),
)
def test_a_computed_count_is_the_best_lawful_count(early, middle, later, last):
    counts = {
        1998: early,
        1999: middle,
        2000: 1,
        2001: later,
        2002: 4,
        2003: 4,
        2004: 4,
        2005: last,
    }
    expected = _lawful_currently(counts)
    try:
        result = i.insured_status(
            _plain(),
            _history(1962, 2011, {**FULL_HISTORY, **counts}),
            QUERY,
            test=i.InsuredTest.CURRENTLY,
        )
    except i.InsuredConfigurationUnsupported:
        return
    except i.InvalidFamilyInput:
        assert expected is None
        return
    if result.current_disability_period_start == ONSET:
        assert result.currently.qc_count_upper == expected


@pytest.mark.parametrize("test", (i.InsuredTest.DISABILITY, i.InsuredTest.ALL))
@pytest.mark.parametrize(
    ("exit_month", "last"),
    (
        (None, 1974),
        (date(1974, 1, 1), 1974),
        (date(1950, 12, 1), 1950),
    ),
)
def test_aggregate_below_six_ordinary_qcs_refuses_the_dli(
    test, exit_month, last
):
    # Three ordinary QCs, and $8,800 / $400 = 22 against the 22 of 1973.
    years = _blind_years({1948: 2933, 1949: 2933, 1950: 2934}, last)
    _refused_row(
        _blind(),
        years,
        BLIND_QUERY,
        SIMPLIFIED,
        test=test,
        coverage_end_month=exit_month,
    )


def test_aggregate_with_no_ordinary_qc_refuses_the_dli():
    # $49 in each quarter earns no QC, and 52 quarters total $2,548.
    years = _history(1937, 1974, {})
    for year in range(1938, 1951):
        years[year] = i.CoverageYear(
            OBSERVED, quarterly_wages=(Fraction(49),) * 4
        )
    _refused_row(
        _blind(),
        years,
        BLIND_QUERY,
        SIMPLIFIED,
        test=i.InsuredTest.DISABILITY,
    )


@pytest.mark.parametrize("blind", (False, True))
def test_no_wages_leave_no_dli(blind):
    result = i.insured_status(
        _blind(statutory_blindness=blind),
        _history(1937, 1974, {}),
        BLIND_QUERY,
        test=i.InsuredTest.DISABILITY,
    )
    assert not result.disability.insured
    assert result.dli.upper is None


def test_a_nonblind_record_below_six_needs_no_aggregate_refusal():
    # No recent rule can pass on three ordinary QCs, whatever the aggregate.
    years = _blind_years({1948: 2933, 1949: 2933, 1950: 2934})
    result = i.insured_status(
        _blind(statutory_blindness=False),
        years,
        BLIND_QUERY,
        test=i.InsuredTest.DISABILITY,
    )
    assert not result.disability.insured
    assert result.dli.upper is None


@settings(max_examples=40, deadline=None)
@example(total=2399)
@example(total=2400)
@given(total=st.integers(150, 9000))
def test_the_dli_refusal_tracks_six_aggregate_qcs(total):
    # Six aggregate QCs meet the 404.110 floor at the earliest credited
    # quarter, so the refusal needs only the $2,400 total.
    share = total // 3
    amounts = {1948: share, 1949: share, 1950: total - 2 * share}
    years = _blind_years(amounts)

    def call():
        return i.insured_status(
            _blind(), years, BLIND_QUERY, test=i.InsuredTest.DISABILITY
        )

    if total // 400 >= 6:
        with pytest.raises(i.InsuredConfigurationUnsupported) as error:
            call()
        assert error.value.reason is SIMPLIFIED
    else:
        result = call()
        assert not result.disability.insured
        assert result.dli.upper is None
