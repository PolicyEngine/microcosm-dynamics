"""Round 15: the disability aggregate and each filling's own start.

Verification class: statutory conformance on invented declarations; no
population, behavioral or forecast claim. A decisive pre-1951 aggregate
(Act 213(c); 404.132) refuses by name on DISABILITY, the established period,
its first start and the date last insured. It never loses a row, and
simplified credits never count toward the recent rule. Source conflict
us:oasdi-insured-simplified-pre1951-disability-scope.

One record has one start (404.321(a)). A result stands only if one filling
attains it with the reported start as its own, and no filling can improve on
it. Source conflict us:oasdi-insured-one-filling-first-start.
"""

from dataclasses import replace
from datetime import date
from fractions import Fraction

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import insured_status as i
from populace_dynamics.track_b.gross_benefits import (
    InvalidFamilyInput,
    count_family_outcomes,
)
from tests.test_track_b_insured_status import history

OBSERVED = i.EarningsProvenance.OBSERVED
UNKNOWN = i.EarningsProvenance.UNKNOWN
SIMPLIFIED = i.InsuredUnsupportedReason.SIMPLIFIED_PRE1951
ASSIGNMENT = i.InsuredUnsupportedReason.ASSIGNMENT_COMPLEXITY
WEIGHT = Fraction(13, 7)
BIRTH = date(1926, 2, 2)
ONSET = date(1989, 1, 15)
QUERY = date(1990, 1, 1)
# Three ordinary QCs, or eighteen simplified ones, plus 22 recent QCs:
# 25 ordinary and 40 simplified against the 37 required at onset.
RECENT = {1983: 2, **dict.fromkeys(range(1984, 1989), 4)}
PROPERTY = settings(max_examples=24, deadline=None)


def _person(**changes):
    values = dict(
        sex=i.Sex.FEMALE,
        disability_onset=ONSET,
        current_disability_period_established=True,
        current_disability_period_provenance=OBSERVED,
        current_disability_period_end=date(1989, 12, 31),
        current_disability_period_end_provenance=OBSERVED,
        prior_disability_periods=(),
        prior_disability_periods_provenance=OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
    )
    birth = changes.pop("birth", BIRTH)
    values.update(changes)
    return i.Person(birth, **values)


def _unestablished(**changes):
    values = dict(
        sex=i.Sex.FEMALE,
        current_disability_period_established=False,
        current_disability_period_provenance=OBSERVED,
        prior_disability_periods=(),
        prior_disability_periods_provenance=OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
    )
    values.update(changes)
    return i.Person(BIRTH, **values)


def _medical():
    return _unestablished(disability_onset=ONSET)


def _no_onset():
    return _unestablished()


def _wages(amount):
    return i.CoverageYear(
        OBSERVED,
        quarterly_wages=(
            Fraction(amount),
            Fraction(0),
            Fraction(0),
            Fraction(0),
        ),
    )


def _years(person, month, amount=2400, counts=None):
    years = history(person, month, RECENT if counts is None else counts)
    for year in (1948, 1949, 1950):
        years[year] = _wages(amount)
    return years


def _row(person, years, month, *, test=i.InsuredTest.ALL):
    row = i.evaluate_insured_status(
        "round-fifteen-aggregate",
        WEIGHT,
        lambda: i.insured_status(person, years, month, test=test),
    )
    counts = count_family_outcomes((row,))
    assert counts.rows == 1
    assert counts.weight == WEIGHT
    assert counts.unsupported_weight == (WEIGHT if row.unsupported else 0)
    return row


def _reason(person, years, month, *, test=i.InsuredTest.ALL):
    row = _row(person, years, month, test=test)
    assert row.result is None
    return row.unsupported.reason


def _computed(person, years, month, *, test=i.InsuredTest.ALL):
    row = _row(person, years, month, test=test)
    assert not row.unsupported
    return row.result


@pytest.mark.parametrize(
    "test",
    (i.InsuredTest.FULLY, i.InsuredTest.DISABILITY, i.InsuredTest.ALL),
)
def test_aggregate_keeps_the_established_period_row(test):
    person = _person()
    years = _years(person, QUERY)
    assert _reason(person, years, QUERY, test=test) is SIMPLIFIED


@pytest.mark.parametrize("test", (i.InsuredTest.DISABILITY, i.InsuredTest.ALL))
def test_aggregate_refuses_a_false_disability_after_medical_onset(test):
    person = _medical()
    years = _years(person, QUERY)
    assert _reason(person, years, QUERY, test=test) is SIMPLIFIED


def test_aggregate_refuses_a_false_disability_without_onset():
    month = date(1989, 1, 1)
    person = _no_onset()
    years = _years(person, month)
    assert (
        _reason(person, years, month, test=i.InsuredTest.DISABILITY)
        is SIMPLIFIED
    )


def test_aggregate_refuses_for_blindness_without_the_recent_rule():
    person = _medical()
    person = replace(person, statutory_blindness=True)
    years = _years(person, QUERY, counts=dict.fromkeys(range(1980, 1985), 4))
    assert (
        _reason(person, years, QUERY, test=i.InsuredTest.DISABILITY)
        is SIMPLIFIED
    )


def test_blind_established_period_keeps_the_aggregate_row():
    person = replace(_person(), statutory_blindness=True)
    years = _years(person, QUERY, counts=dict.fromkeys(range(1980, 1985), 4))
    assert _reason(person, years, QUERY) is SIMPLIFIED


@pytest.mark.parametrize("test", (i.InsuredTest.DISABILITY, i.InsuredTest.ALL))
def test_declared_flag_and_automatic_route_share_their_reason(test):
    person = _person(
        conditions=(i.CoverageCondition.SIMPLIFIED_PRE1951,),
    )
    years = _years(person, QUERY)
    assert _reason(person, years, QUERY, test=test) is SIMPLIFIED


@pytest.mark.parametrize("amount,refuses", ((2000, True), (1999, False)))
def test_disability_boundary_is_one_whole_400_credit(amount, refuses):
    """$6,000 gives 15 + 22 = 37; $5,997 gives 14 + 22 = 36."""
    person = _medical()
    years = _years(person, QUERY, amount)
    if refuses:
        assert (
            _reason(person, years, QUERY, test=i.InsuredTest.DISABILITY)
            is SIMPLIFIED
        )
    else:
        result = _computed(person, years, QUERY, test=i.InsuredTest.DISABILITY)
        assert not result.disability.insured


@PROPERTY
@example(cents=600000)
@example(cents=599999)
@given(st.integers(min_value=0, max_value=900000))
def test_disability_refusal_tracks_the_exact_aggregate(cents):
    person = _medical()
    years = _years(person, QUERY, Fraction(cents, 300))
    row = _row(person, years, QUERY, test=i.InsuredTest.DISABILITY)
    if cents >= 600000:
        assert row.unsupported.reason is SIMPLIFIED
    else:
        assert not row.result.disability.insured


def test_simplified_credits_never_count_toward_the_recent_rule():
    counts = dict.fromkeys(range(1968, 1975), 4)
    person = _medical()
    years = _years(person, QUERY, counts=counts)
    result = _computed(person, years, QUERY, test=i.InsuredTest.DISABILITY)
    assert not result.disability.insured
    person = _person()
    with pytest.raises(InvalidFamilyInput):
        i.insured_status(person, _years(person, QUERY, counts=counts), QUERY)


def test_ordinary_insurance_stays_computed_with_the_aggregate():
    counts = {**RECENT, **dict.fromkeys(range(1978, 1983), 4)}
    person = _medical()
    with_wages = _years(person, QUERY, counts=counts)
    result = _computed(
        person, with_wages, QUERY, test=i.InsuredTest.DISABILITY
    )
    assert result.disability.insured


def test_no_pre1951_wages_keeps_the_ordinary_answers():
    person = _medical()
    years = history(person, QUERY, RECENT)
    result = _computed(person, years, QUERY, test=i.InsuredTest.DISABILITY)
    assert not result.disability.insured
    established = _person()
    with pytest.raises(InvalidFamilyInput):
        i.insured_status(
            established,
            history(established, QUERY, RECENT),
            QUERY,
        )


def _first_start_record(amount):
    person = _person(current_disability_period_end=date(1990, 12, 31))
    month = date(1991, 1, 1)
    counts = {
        **dict.fromkeys(range(1981, 1989), 4),
        1980: 1,
        1990: 1,
    }
    return person, _years(person, month, amount, counts), month


def test_aggregate_can_move_the_first_insured_start():
    """37 ordinary QCs first appear in 1990; 18 + 34 insure the onset."""
    person, years, month = _first_start_record(2400)
    assert _reason(person, years, month) is SIMPLIFIED


def test_first_start_control_without_a_400_dollar_aggregate():
    person, years, month = _first_start_record(50)
    result = _computed(person, years, month)
    assert result.disability.insured
    assert result.disability.qualifying_quarter == date(1990, 1, 1)


def _last_insured_record(amount):
    """Ordinary fully status lapses in 1979, the recent rule in 1983."""
    month = date(1985, 1, 1)
    person = _no_onset()
    counts = dict.fromkeys(range(1972, 1978), 4)
    return person, _years(person, month, amount, counts), month


def test_aggregate_can_extend_the_date_last_insured():
    person, years, month = _last_insured_record(2400)
    assert (
        _reason(person, years, month, test=i.InsuredTest.DISABILITY)
        is SIMPLIFIED
    )


def test_date_last_insured_control_without_a_400_dollar_aggregate():
    person, years, month = _last_insured_record(50)
    result = _computed(person, years, month, test=i.InsuredTest.DISABILITY)
    assert not result.disability.insured
    assert result.dli.lower == date(1978, 12, 31)


def _unknown_prior_record(amount):
    """A prior funded by the aggregate could reopen the 40-quarter window."""
    person = _person(
        prior_disability_periods=(),
        prior_disability_periods_provenance=UNKNOWN,
    )
    years = history(
        person,
        QUERY,
        {1964: 4, 1965: 4, 1966: 4, 1967: 2, 1987: 4, 1988: 2},
    )
    years[1950] = _wages(amount)
    return person, years


def test_unknown_prior_history_keeps_the_aggregate_row():
    person, years = _unknown_prior_record(1200)
    assert (
        _reason(person, years, QUERY, test=i.InsuredTest.DISABILITY)
        is i.InsuredUnsupportedReason.UNKNOWN_PERIODS
    )


def test_unknown_prior_control_needs_a_400_dollar_aggregate():
    person, years = _unknown_prior_record(50)
    with pytest.raises(InvalidFamilyInput):
        i.insured_status(person, years, QUERY, test=i.InsuredTest.DISABILITY)


def test_mapping_order_leaves_the_disability_reason_unchanged():
    person = _medical()
    years = _years(person, QUERY)
    forward = _reason(person, years, QUERY, test=i.InsuredTest.DISABILITY)
    reverse = _reason(
        person,
        dict(reversed(tuple(years.items()))),
        QUERY,
        test=i.InsuredTest.DISABILITY,
    )
    assert forward is reverse is SIMPLIFIED


def _outcome(person, years, month, test):
    try:
        result = i.insured_status(person, years, month, test=test)
    except i.InsuredConfigurationUnsupported as error:
        return "refused", error.reason
    except InvalidFamilyInput:
        return "invalid", None
    return "computed", result


@PROPERTY
@given(
    amount=st.sampled_from((0, 50, 399, 400, 2000, 2400, 5000)),
    start=st.integers(1978, 1985),
    span=st.integers(1, 11),
    filled=st.integers(0, 4),
    established=st.booleans(),
    blind=st.booleans(),
)
def test_pre1951_wages_only_add_rows(
    amount, start, span, filled, established, blind
):
    """Adding raw pre-1951 wages never turns a row into an input error."""
    counts = {
        year: filled
        for year in range(max(start, 1978), min(start + span, 1989))
        if filled
    }
    person = replace(
        _person() if established else _medical(),
        statutory_blindness=blind,
    )
    base = history(person, QUERY, counts)
    added = _years(person, QUERY, amount, counts)
    before = _outcome(person, base, QUERY, i.InsuredTest.ALL)
    after = _outcome(person, added, QUERY, i.InsuredTest.ALL)
    if before[0] != "invalid":
        assert after[0] != "invalid", (before, after)


@PROPERTY
@given(
    amount=st.sampled_from((400, 800, 2000, 2400, 5000)),
    start=st.integers(1978, 1985),
    span=st.integers(2, 11),
)
def test_fully_refusal_and_a_met_recent_rule_never_compute_false(
    amount, start, span
):
    """The same facts cannot refuse FULLY and answer DISABILITY false."""
    counts = {year: 4 for year in range(start, min(start + span, 1989))}
    person = _medical()
    years = _years(person, QUERY, amount, counts)
    fully = _outcome(person, years, QUERY, i.InsuredTest.FULLY)
    disability = _outcome(person, years, QUERY, i.InsuredTest.DISABILITY)
    recent = sum(count for year, count in counts.items() if year >= 1979) >= 20
    if fully[:2] == ("refused", SIMPLIFIED) and recent:
        if disability[0] == "computed":
            assert disability[1].disability.insured


def _moving_start_person(**changes):
    values = dict(
        birth=date(1956, 2, 2),
        disability_onset=date(1992, 1, 15),
        current_disability_period_end=date(1994, 9, 30),
    )
    values.update(changes)
    return _person(**values)


# The 1994 QC must sit in the first insured quarter, so at most two later
# quarters leave the 13-quarter window and five of six QCs remain in every
# lawful filling.
MOVING_START = {
    1987: 2,
    1988: 4,
    1989: 3,
    1990: 4,
    1991: 4,
    1992: 2,
    1994: 1,
}
MOVING_QUERY = date(1995, 1, 1)


@pytest.mark.parametrize("test", (i.InsuredTest.CURRENTLY, i.InsuredTest.ALL))
def test_no_filling_carries_the_start_and_the_status_together(test):
    person = _moving_start_person()
    years = history(person, MOVING_QUERY, MOVING_START)
    assert _reason(person, years, MOVING_QUERY, test=test) is ASSIGNMENT


def test_a_partial_year_that_cannot_move_the_start_stays_computed():
    person = _moving_start_person()
    counts = {**dict.fromkeys(range(1982, 1992), 4), 1992: 2}
    result = _computed(
        person, history(person, MOVING_QUERY, counts), MOVING_QUERY
    )
    assert result.current_disability_period_start == date(1992, 1, 15)
    assert result.disability.insured


def test_a_moving_start_keeps_a_result_one_filling_attains():
    """The search starts at the filling that insures the reported start."""
    person = _person(
        birth=date(1978, 2, 2),
        disability_onset=date(2011, 1, 15),
        current_disability_period_end=date(2013, 12, 31),
    )
    month = date(2014, 1, 1)
    counts = {
        2002: 2,
        2003: 2,
        2004: 4,
        2006: 1,
        2007: 2,
        2008: 2,
        2009: 3,
        2010: 1,
        2011: 1,
        2012: 2,
    }
    result = _computed(
        person,
        history(person, month, counts),
        month,
        test=i.InsuredTest.DISABILITY,
    )
    assert result.current_disability_period_start == date(2012, 4, 1)


@pytest.mark.parametrize(
    ("amount", "refused"),
    ((Fraction(2950), True), (Fraction(2900), True), (Fraction(799), False)),
)
def test_blind_aggregate_decides_below_six_ordinary_qcs(amount, refused):
    """Three first-quarter wages earn three ordinary QCs.

    That stays under the $3,000 that would earn gift QCs. Elapsed years run
    1951 through 1972, so 22 QCs insure at the onset, and $8,850 reaches 22
    at $400 each. $8,700 reaches 21, which meets 1972's 21 for a historical
    date last insured. $2,397 reaches five, below every requirement.
    """
    person = replace(
        _unestablished(
            disability_onset=date(1973, 2, 15), statutory_blindness=True
        ),
        birth_date=date(1926, 2, 2),
    )
    month = date(1974, 7, 1)
    years = _years(person, month, amount, {})
    if refused:
        assert _reason(
            person, years, month, test=i.InsuredTest.DISABILITY
        ) is (SIMPLIFIED)
    else:
        row = _row(person, years, month, test=i.InsuredTest.DISABILITY)
        assert row.result.disability.insured is False


def test_the_date_last_insured_alone_can_refuse_a_moving_start():
    """DISABILITY never reads the period, so only the date can differ.

    The QCs through 2012 give the prior the 18 fully insured status asks at
    its start on every placement, so only the current start can refuse.
    """
    person = _person(
        birth=date(1973, 2, 2),
        disability_onset=date(2015, 5, 15),
        current_disability_period_end=date(2018, 1, 31),
        prior_disability_periods=(
            i.DisabilityPeriod(date(2013, 1, 1), date(2014, 12, 31)),
        ),
    )
    month = date(2022, 1, 1)
    counts = {
        2000: 3,
        2008: 1,
        2009: 2,
        2010: 4,
        2011: 4,
        2012: 4,
        2013: 1,
        2014: 4,
        2015: 3,
        2016: 4,
    }
    years = history(person, month, counts)
    row = _row(person, years, month, test=i.InsuredTest.DISABILITY)
    assert row.unsupported.reason is ASSIGNMENT
    assert row.unsupported.detail.startswith("First insured start depends")


# An entitlement month ends a currently insured window in a year before the
# onset. That year then wants its QC early for the status and late for the
# recent rule, so each row needs the first-start search to vary that year.
# Each row names the only line of _start_sensitive_years that reaches it,
# and "later start" keeps the status only on a filling whose start differs.
# All QC arithmetic sits on the row: the fixed QCs leave one short of the
# recent rule, and the event's 13 quarters leave one short of six.
ENTITLEMENT_CONFLICTS = {
    "forty quarter back edge": dict(
        birth=date(1960, 2, 2),
        disability_onset=date(2010, 1, 15),
        current_disability_period_end=date(2013, 12, 31),
        dib_entitlement_month=date(2000, 1, 1),
        month=date(2015, 1, 1),
        counts={
            1990: 4,
            1991: 4,
            1998: 3,
            1999: 2,
            2000: 1,
            **dict.fromkeys(range(2001, 2005), 4),
            2005: 3,
        },
    ),
    "later start": dict(
        birth=date(1960, 2, 2),
        disability_onset=date(2010, 8, 15),
        current_disability_period_end=date(2013, 12, 31),
        dib_entitlement_month=date(2000, 1, 1),
        month=date(2015, 1, 1),
        counts={
            1990: 4,
            1991: 4,
            1998: 3,
            1999: 2,
            2000: 1,
            **dict.fromkeys(range(2002, 2006), 4),
            2006: 3,
            2011: 1,
        },
    ),
    "prior period year": dict(
        birth=date(1960, 2, 2),
        disability_onset=date(2010, 8, 15),
        current_disability_period_end=date(2011, 6, 30),
        dib_entitlement_month=date(2005, 1, 1),
        prior_disability_periods=(
            i.DisabilityPeriod(date(2005, 1, 1), date(2005, 9, 30)),
        ),
        month=date(2012, 1, 1),
        counts={
            1986: 4,
            1987: 4,
            1990: 4,
            1991: 4,
            2000: 4,
            2002: 3,
            2003: 2,
            2005: 1,
            2006: 4,
            2007: 4,
            2008: 2,
        },
    ),
    "twelve quarter back edge": dict(
        birth=date(1985, 2, 2),
        disability_onset=date(2008, 8, 15),
        current_disability_period_end=date(2009, 6, 30),
        dib_entitlement_month=date(2005, 1, 1),
        month=date(2010, 1, 1),
        counts={
            2002: 2,
            2003: 2,
            2004: 1,
            2005: 1,
            2006: 2,
            2007: 2,
            2008: 1,
        },
    ),
    "age 21 back edge": dict(
        birth=date(1980, 8, 2),
        disability_onset=date(2008, 8, 15),
        current_disability_period_end=date(2009, 6, 30),
        dib_entitlement_month=date(2001, 1, 1),
        month=date(2010, 1, 1),
        counts={
            1999: 3,
            2000: 2,
            2001: 1,
            **dict.fromkeys(range(2002, 2008), 2),
            2008: 1,
        },
    ),
}


@pytest.mark.parametrize("name", ENTITLEMENT_CONFLICTS)
@pytest.mark.parametrize("test", (i.InsuredTest.CURRENTLY, i.InsuredTest.ALL))
def test_an_entitlement_window_cannot_borrow_the_starts_placement(name, test):
    values = dict(ENTITLEMENT_CONFLICTS[name])
    month, counts = values.pop("month"), values.pop("counts")
    person = _person(**values)
    years = history(person, month, counts)
    assert _reason(person, years, month, test=test) is ASSIGNMENT


@pytest.mark.parametrize("name", ENTITLEMENT_CONFLICTS)
def test_the_same_record_computes_without_the_entitlement(name):
    values = dict(ENTITLEMENT_CONFLICTS[name])
    month, counts = values.pop("month"), values.pop("counts")
    values.pop("dib_entitlement_month")
    person = _person(**values)
    result = _computed(
        person,
        history(person, month, counts),
        month,
        test=i.InsuredTest.CURRENTLY,
    )
    assert result.current_disability_period_start == person.disability_onset
    assert result.currently.insured is False
