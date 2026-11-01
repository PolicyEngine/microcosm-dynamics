"""Statutory conformance for the round-fourteen establishment corrections.

Invented declarations only; no population, behavioral, or forecast claim.
Rows and exact weight survive every named refusal. Tests named ``unchanged``
pin existing rejection or refusal behavior rather than a new defect.
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
from tests.test_track_b_insured_status import history

OBSERVED = i.EarningsProvenance.OBSERVED
UNKNOWN = i.EarningsProvenance.UNKNOWN
WEIGHT = Fraction(17, 9)
FLAG_WEIGHT = Fraction(3, 2)
FULLY_FLAGS = (
    i.CoverageCondition.DEEMED_FULLY_INSURED,
    i.CoverageCondition.TRANSITIONAL_INSURED,
    i.CoverageCondition.EARNED_BASIS,
    i.CoverageCondition.SIMPLIFIED_PRE1951,
)
PROPERTY = settings(max_examples=24, deadline=None)


def _person(**changes):
    values = dict(
        sex=i.Sex.FEMALE,
        disability_onset=date(2000, 2, 15),
        current_disability_period_established=True,
        current_disability_period_provenance=OBSERVED,
        current_disability_period_end=date(2002, 12, 31),
        current_disability_period_end_provenance=OBSERVED,
        prior_disability_periods=(
            i.DisabilityPeriod(date(1999, 1, 1), date(2000, 1, 31)),
        ),
        prior_disability_periods_provenance=OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
    )
    birth = changes.pop("birth", date(1960, 2, 2))
    values.update(changes)
    return i.Person(birth, **values)


def _row(
    person,
    years,
    month,
    *,
    test=i.InsuredTest.FULLY,
    weight=WEIGHT,
    coverage_end=None,
):
    row = i.evaluate_insured_status(
        "round-fourteen-establishment",
        weight,
        lambda: i.insured_status(
            person,
            years,
            month,
            test=test,
            coverage_end_month=coverage_end,
        ),
    )
    counts = count_family_outcomes((row,))
    assert counts.rows == 1
    assert counts.weight == weight
    if row.unsupported:
        assert counts.unsupported_rows == 1
        assert counts.unsupported_weight == weight
    else:
        assert counts.unsupported_rows == 0
        assert counts.unsupported_weight == 0
    return row


def _refusal(person, years, month, reason, **kwargs):
    row = _row(person, years, month, **kwargs)
    assert row.result is None
    assert row.unsupported.reason is reason
    return row


def _blind_history(*, subsequent=False, month=None, coverage_end=None):
    onset = date(1995, 1, 15) if subsequent else date(1976, 1, 15)
    month = month or date(onset.year + 1, 1, 1)
    person = _person(
        birth=date(1951, 2, 2),
        sex=i.Sex.MALE,
        disability_onset=onset,
        current_disability_period_end=date(onset.year, 12, 31),
        prior_disability_periods=(),
        prior_disability_periods_provenance=UNKNOWN,
    )
    credited = {
        1970 * 4 + 1,
        1972 * 4 + 1,
        1972 * 4 + 2,
        1972 * 4 + 3,
        1973 * 4,
        1973 * 4 + 1,
        1976 * 4,
    }
    years = history(person, month, end=coverage_end)
    for year in years:
        if year < 1978:
            years[year] = i.CoverageYear(
                OBSERVED,
                qc_quarters=tuple(year * 4 + q in credited for q in range(4)),
            )
    return person, years, month


def _flag_history(
    flag=FULLY_FLAGS[0], *, month=date(1985, 12, 1), coverage_end=None
):
    person = _person(
        birth=date(1924, 1, 2),
        disability_onset=date(1985, 2, 15),
        current_disability_period_end=date(1985, 12, 31),
        prior_disability_periods=(
            i.DisabilityPeriod(date(1979, 1, 1), date(1985, 1, 31)),
        ),
        conditions=(() if flag is None else (flag,)),
    )
    counts = {
        1951: 4,
        1952: 4,
        1953: 4,
        1954: 1,
        1975: 3,
        1976: 4,
        1977: 4,
        1978: 4,
        1984: 4,
        1985: 4,
    }
    years = history(person, month, counts, end=coverage_end)
    years[1975] = i.CoverageYear(
        OBSERVED,
        qc_quarters=(False, True, True, True),
    )
    return person, years, month


def _placement_history(
    *,
    month=date(2006, 1, 1),
    coverage_end=None,
    claiming=False,
    round_thirteen=False,
):
    person = _person(
        current_disability_period_end=(
            date(2000, 12, 31) if round_thirteen else date(2002, 12, 31)
        ),
    )
    counts = {
        1990: 1,
        1995: 4,
        1996: 4,
        1997: 4,
        1998: 4,
        1999: 2,
        2000: 1,
        2002: 1,
    }
    if round_thirteen:
        counts = {1995: 4, 1996: 4, 1997: 4, 1998: 4, 1999: 3, 2000: 1}
    if claiming:
        counts.update({year: 4 for year in range(2003, 2007)})
    return person, history(person, month, counts, end=coverage_end), month


@pytest.mark.parametrize(
    "test", (i.InsuredTest.FULLY, i.InsuredTest.DISABILITY)
)
@pytest.mark.parametrize(
    "month,coverage_end,subsequent",
    (
        (None, None, False),
        (None, date(1976, 12, 1), False),
        (date(2013, 3, 1), None, False),
        (None, None, True),
    ),
    ids=("single", "coverage-end", "claiming-age", "subsequent-special"),
)
def test_unknown_prior_history_keeps_historical_blindness(
    test, month, coverage_end, subsequent
):
    person, years, month = _blind_history(
        month=month,
        coverage_end=coverage_end,
        subsequent=subsequent,
    )
    row = _row(person, years, month, test=test, coverage_end=coverage_end)
    if test is i.InsuredTest.FULLY and month.year == 1977:
        assert row.unsupported is None
        assert row.result.fully.insured
        assert row.result.fully.qc_count_lower == 0
        assert row.result.fully.qc_count_upper == 7
        assert row.result.fully.required == 6
    else:
        assert row.result is None
        assert (
            row.unsupported.reason
            is i.InsuredUnsupportedReason.UNKNOWN_PERIODS
        )


@pytest.mark.parametrize("flag", FULLY_FLAGS)
@pytest.mark.parametrize(
    "month,coverage_end",
    (
        (date(1985, 12, 1), None),
        (date(1985, 12, 1), date(1985, 12, 1)),
        (date(1986, 1, 1), None),
    ),
    ids=("ordinary-query", "coverage-end", "claiming-age"),
)
def test_recent_only_overlap_does_not_disprove_flagged_start(
    flag, month, coverage_end
):
    person, years, month = _flag_history(
        flag,
        month=month,
        coverage_end=coverage_end,
    )
    _refusal(
        person,
        years,
        month,
        i.InsuredUnsupportedReason[flag.name],
        weight=FLAG_WEIGHT,
        coverage_end=coverage_end,
    )


def test_unchanged_unflagged_disregard_control_is_fully_insured():
    person, years, month = _flag_history(None)
    row = _row(person, years, month, weight=FLAG_WEIGHT)
    assert row.unsupported is None
    assert row.result.fully.insured


@pytest.mark.parametrize("test", tuple(i.InsuredTest))
@pytest.mark.parametrize(
    "month,coverage_end,claiming",
    (
        (date(2006, 1, 1), None, False),
        (date(2006, 1, 1), date(2002, 12, 1), False),
        (date(2022, 3, 1), None, True),
    ),
    ids=("ordinary-query", "coverage-end", "claiming-age"),
)
def test_first_successful_placement_cannot_settle_status(
    test, month, coverage_end, claiming
):
    person, years, month = _placement_history(
        month=month,
        coverage_end=coverage_end,
        claiming=claiming,
    )
    _refusal(
        person,
        years,
        month,
        i.InsuredUnsupportedReason.ASSIGNMENT_COMPLEXITY,
        test=test,
        coverage_end=coverage_end,
    )


def test_round_thirteen_annual_start_needs_named_refusal():
    person, years, month = _placement_history(
        month=date(2001, 1, 1),
        round_thirteen=True,
    )
    _refusal(
        person,
        years,
        month,
        i.InsuredUnsupportedReason.ASSIGNMENT_COMPLEXITY,
        test=i.InsuredTest.DISABILITY,
    )


def _invalid(person, years, month, *, match="no possible insured", **kwargs):
    rows = []
    with pytest.raises(i.InvalidFamilyInput, match=match):
        rows.append(_row(person, years, month, **kwargs))
    counts = count_family_outcomes(rows)
    assert counts.rows == counts.unsupported_rows == 0
    assert counts.weight == counts.unsupported_weight == 0


@pytest.mark.parametrize("flag", FULLY_FLAGS)
def test_unchanged_ordinary_overlap_cannot_be_delayed_by_a_flag(flag):
    """Ordinary insurance at onset in every placement fixes the start."""
    person = _person(conditions=(flag,))
    month = date(2006, 1, 1)
    years = history(person, month, {year: 4 for year in range(1985, 2001)})
    _invalid(person, years, month)


@pytest.mark.parametrize("flag", FULLY_FLAGS)
def test_unchanged_1962_ordinary_overlap_fixes_start(flag):
    person = _person(
        birth=date(1910, 2, 2),
        disability_onset=date(1962, 2, 15),
        current_disability_period_end=date(1962, 8, 31),
        prior_disability_periods=(
            i.DisabilityPeriod(date(1960, 1, 1), date(1962, 1, 31)),
        ),
        conditions=(flag,),
    )
    month = date(1968, 1, 1)
    years = history(person, month)
    credited = {*range(1957 * 4, 1961 * 4 + 3), 1962 * 4}
    for year in years:
        years[year] = i.CoverageYear(
            OBSERVED,
            qc_quarters=tuple(year * 4 + q in credited for q in range(4)),
        )
    _invalid(person, years, month)


@pytest.mark.parametrize("flag", FULLY_FLAGS)
@pytest.mark.parametrize("overlap", (False, True))
def test_blind_flagged_zero_qcs_keep_named_refusal(flag, overlap):
    """The clear-onset case is unchanged; an overlap admits a free flag start."""
    person = _person(
        statutory_blindness=True,
        conditions=(flag,),
        prior_disability_periods=(
            i.DisabilityPeriod(
                date(1999, 1, 1),
                date(2000, 1, 31) if overlap else date(1999, 12, 31),
            ),
        ),
    )
    month = date(2006, 1, 1)
    _refusal(
        person,
        history(person, month),
        month,
        i.InsuredUnsupportedReason[flag.name],
    )


@pytest.mark.parametrize("flag", FULLY_FLAGS)
def test_unchanged_blind_ordinary_fully_insured_overlap_is_invalid(flag):
    person = _person(statutory_blindness=True, conditions=(flag,))
    month = date(2006, 1, 1)
    years = history(person, month, {year: 4 for year in range(1985, 2001)})
    _invalid(person, years, month)


@pytest.mark.parametrize("total", (5, 6))
def test_unchanged_unknown_prior_needs_a_possible_fully_insured_start(total):
    person = _person(
        prior_disability_periods=(),
        prior_disability_periods_provenance=UNKNOWN,
    )
    month = date(2006, 1, 1)
    # Even six lifetime QCs cannot fully insure any earliest prior: they
    # first arrive in 1998, when sixteen are needed without a prior freeze.
    # The six-credit case passes the universal floor and still rejects.
    _invalid(person, history(person, month, {1998: 4, 1999: total - 4}), month)


def test_unchanged_no_placement_can_clear_the_prior_overlap():
    person = _person()
    month = date(2006, 1, 1)
    years = history(person, month, {year: 4 for year in range(1985, 2001)})
    _invalid(person, years, month)


@pytest.mark.parametrize("flag", (None, *FULLY_FLAGS))
def test_one_treatment_overlaps_and_the_other_leaves_a_clear_start(flag):
    # Move four old QCs into the used-prior recent window, keeping the
    # lifetime count unchanged. Use now insures the overlapping Q1:
    # 20 recent and 29/27 fully. Disregard still has only 33/34 fully
    # in Q1, first becoming insured in the clear Q2 with 34/34.
    person, years, month = _flag_history(flag)
    years[1951] = i.CoverageYear(
        OBSERVED, qc_quarters=(False, False, False, False)
    )
    years[1974] = i.CoverageYear(
        OBSERVED, qc_quarters=(False, True, True, True)
    )
    years[1975] = i.CoverageYear(
        OBSERVED, qc_quarters=(True, True, True, True)
    )
    _refusal(
        person,
        years,
        month,
        (
            i.InsuredUnsupportedReason[flag.name]
            if flag
            else i.InsuredUnsupportedReason.ASSIGNMENT_COMPLEXITY
        ),
        weight=FLAG_WEIGHT,
    )


def test_search_refusal_waits_for_later_input_validation(monkeypatch):
    person, years, month = _placement_history()
    called = []

    def later_validation(*args, **kwargs):
        called.append(True)
        raise i.InvalidFamilyInput("later declared input is invalid")

    monkeypatch.setattr(i, "_coverage_checks", later_validation)
    _invalid(person, years, month, match="later declared input is invalid")
    assert called == [True]


def test_unchanged_schema_error_precedes_assignment_search():
    person, years, month = _placement_history()
    years.pop(1980)
    _invalid(
        person, years, month, match="Every coverage year must be declared"
    )


def _lattice_declarations():
    """A finite lattice of known annual boundary and fixed-quarter cases."""
    yield _flag_history(None)
    yield _placement_history()
    yield _placement_history(month=date(2022, 3, 1), claiming=True)
    for blind, onset_count, prior_end in product(
        (False, True),
        (0, 1, 4),
        (date(1999, 12, 31), date(2000, 1, 31)),
    ):
        person = _person(
            statutory_blindness=blind,
            current_disability_period_end=date(2000, 12, 31),
            prior_disability_periods=(
                i.DisabilityPeriod(date(1999, 1, 1), prior_end),
            ),
        )
        month = date(2001, 1, 1)
        yield person, history(
            person,
            month,
            {1995: 4, 1996: 4, 1997: 4, 1998: 4, 1999: 3, 2000: onset_count},
        ), month


def _classification(person, years, month):
    try:
        return _row(person, years, month)
    except i.InvalidFamilyInput:
        return None


def _assert_flags_only_relax(person, years, month):
    unflagged = _classification(replace(person, conditions=()), years, month)
    if unflagged is None:
        return
    for flag in FULLY_FLAGS:
        flagged = _row(replace(person, conditions=(flag,)), years, month)
        assert flagged.result is not None or flagged.unsupported is not None


def test_fully_route_flag_only_relaxes_deterministic_lattice():
    for person, years, month in _lattice_declarations():
        _assert_flags_only_relax(person, years, month)


@PROPERTY
@example(old=2, onset=1, blind=False, overlap=True, historical=True)
@example(old=2, onset=1, blind=False, overlap=True, historical=False)
@given(
    old=st.integers(0, 4),
    onset=st.integers(0, 4),
    blind=st.booleans(),
    overlap=st.booleans(),
    historical=st.booleans(),
)
def test_fully_route_flag_only_relaxes_generated_declarations(
    old, onset, blind, overlap, historical
):
    if historical:
        person, years, month = _flag_history(
            None, month=date(1986, 1, 1) if overlap else date(1985, 12, 1)
        )
        _assert_flags_only_relax(person, years, month)
        return
    person = _person(
        statutory_blindness=blind,
        prior_disability_periods=(
            i.DisabilityPeriod(
                date(1999, 1, 1),
                date(2000, 1, 31) if overlap else date(1999, 12, 31),
            ),
        ),
    )
    month = date(2006, 1, 1)
    years = history(
        person,
        month,
        {
            1990: 1,
            1995: 4,
            1996: 4,
            1997: 4,
            1998: 4,
            1999: old,
            2000: onset,
            2002: 1,
        },
    )
    _assert_flags_only_relax(person, years, month)


def _outcome(person, years, month):
    try:
        row = _row(person, years, month)
    except i.InvalidFamilyInput as error:
        return type(error), str(error)
    if row.unsupported:
        return (
            row.key,
            row.weight,
            row.unsupported.reason,
            row.unsupported.detail,
        )
    return row.key, row.weight, row.result


def _reverse_treatments(code):
    """Swap only the explicit Boolean treatment tuple, preserving semantics."""
    from types import CodeType

    constants = tuple(
        (
            _reverse_treatments(value)
            if isinstance(value, CodeType)
            else (
                (False, True)
                if isinstance(value, tuple)
                and len(value) == 2
                and all(type(item) is bool for item in value)
                and value == (True, False)
                else value
            )
        )
        for value in code.co_consts
    )
    return code.replace(co_consts=constants)


@pytest.mark.parametrize(
    "assignment,treatment", ((True, False), (False, True), (True, True))
)
def test_assignment_and_treatment_order_leave_public_result_unchanged(
    monkeypatch, assignment, treatment
):
    cases = list(_lattice_declarations())
    cases.append(_flag_history())
    baseline = [_outcome(*case) for case in cases]
    if assignment:
        original = i._assignment_candidates
        monkeypatch.setattr(
            i, "_assignment_candidates", lambda *args: original(*args)[::-1]
        )
    if treatment:
        for function in (i._with_current_period, i._recent_rule_possible):
            monkeypatch.setattr(
                function, "__code__", _reverse_treatments(function.__code__)
            )
    assert [_outcome(*case) for case in cases] == baseline


@settings(max_examples=12, deadline=None)
@example(old=2, onset=1, reverse_assignment=True, reverse_treatment=True)
@given(
    old=st.integers(0, 4),
    onset=st.integers(0, 4),
    reverse_assignment=st.booleans(),
    reverse_treatment=st.booleans(),
)
def test_assignment_and_treatment_order_generated(
    old, onset, reverse_assignment, reverse_treatment
):
    person, years, month = _placement_history()
    years[1999] = i.CoverageYear(OBSERVED, qc_count=old)
    years[2000] = i.CoverageYear(OBSERVED, qc_count=onset)
    baseline = _outcome(person, years, month)
    with pytest.MonkeyPatch.context() as monkeypatch:
        if reverse_assignment:
            original = i._assignment_candidates
            monkeypatch.setattr(
                i,
                "_assignment_candidates",
                lambda *args: original(*args)[::-1],
            )
        if reverse_treatment:
            for function in (i._with_current_period, i._recent_rule_possible):
                monkeypatch.setattr(
                    function,
                    "__code__",
                    _reverse_treatments(function.__code__),
                )
        assert _outcome(person, years, month) == baseline


@pytest.mark.parametrize("subsequent", (False, True))
def test_past_blindness_only_adds_rows_deterministic(subsequent):
    person, years, month = _blind_history(subsequent=subsequent)
    blind = _row(replace(person, statutory_blindness=True), years, month)
    assert blind.result is not None or blind.unsupported is not None
    _row(person, years, month)


@PROPERTY
@example(subsequent=False, claiming=False, extra=0)
@given(
    subsequent=st.booleans(), claiming=st.booleans(), extra=st.integers(0, 4)
)
def test_past_blindness_only_adds_rows_generated(subsequent, claiming, extra):
    person, years, month = _blind_history(
        subsequent=subsequent,
        month=date(2013, 3, 1) if claiming else None,
    )
    years[1974] = i.CoverageYear(
        OBSERVED,
        qc_quarters=tuple(q < extra for q in range(4)),
    )
    blind = _classification(
        replace(person, statutory_blindness=True), years, month
    )
    if blind is not None:
        _row(person, years, month)


@pytest.mark.parametrize(
    "credit_gap", (9, 15), ids=("ordinary_window", "prior_needed")
)
@pytest.mark.parametrize(
    "birth_year,onset_year",
    ((1890, 1954), (1900, 1964), (1910, 1974), (1912, 1976)),
)
def test_unchanged_joint_proof_keeps_pre1913_male_blind_prior_attack(
    birth_year, onset_year, credit_gap
):
    """An insured pre-FRA prior keeps twenty old QCs current again.

    The 1890 case is a pre1956 control, outside the joint-proof branch.
    For the others, earlier blindness is an additional legal basis for
    the same first prior; the ordinary twenty-credit route is also proved.
    """
    start = date(onset_year - credit_gap + 5, 1, 1)
    end = date(onset_year - 1, 12, 31)
    # At the prior start the immediately preceding twenty quarters all
    # carry a QC, meeting 20/40. Add an older QC where the independent
    # male fully prerequisite exceeds twenty (the 1912 cohort).
    elapsed = max(6, min(40, start.year - 1951))
    assert elapsed <= 24
    person = _person(
        birth=date(birth_year, 2, 2),
        sex=i.Sex.MALE,
        disability_onset=date(onset_year, 1, 15),
        current_disability_period_end=date(onset_year, 12, 31),
        prior_disability_periods=(i.DisabilityPeriod(start, end),),
    )
    month = date(max(1968, onset_year + 1), 1, 1)
    counts = {year: 4 for year in range(onset_year - credit_gap, start.year)}
    if elapsed > 20:
        counts[1951] = elapsed - 20
    years = history(person, month, counts)
    known = _row(person, years, month, test=i.InsuredTest.DISABILITY)
    assert known.unsupported is None
    assert known.result.disability.insured
    assert known.result.disability.qc_count_lower == 20
    assert known.result.disability.required == 20
    unknown = replace(
        person,
        prior_disability_periods=(),
        prior_disability_periods_provenance=UNKNOWN,
    )
    _row(unknown, years, month, test=i.InsuredTest.DISABILITY)


def test_six_qc_special_prior_attack_keeps_unknown_row():
    """Six recent QCs for a special prior still satisfy its fully floor.

    A blind prefix first insures six QCs in 1973. The 1976 special prior
    uses six recent QCs, then permits the 1995 subsequent-special period.
    Six is fewer than twenty, but does not waive fully insured status.
    """
    person, years, month = _blind_history(subsequent=True)
    observed = replace(
        person,
        prior_disability_periods_provenance=OBSERVED,
        prior_disability_periods=(
            i.DisabilityPeriod(date(1973, 4, 1), date(1975, 12, 31)),
            i.DisabilityPeriod(
                date(1976, 1, 1), date(1994, 12, 31), special_insured=True
            ),
        ),
    )
    row = _row(observed, years, month, test=i.InsuredTest.DISABILITY)
    assert row.unsupported is None
    assert row.result.disability.insured
    assert row.result.disability.rule == "subsequent_special"
    assert row.result.disability.qc_count_lower == 6
    assert row.result.disability.required == 6
    assert row.result.disability.fully_qc_count_lower == 7
    assert row.result.disability.fully_required == 6
    _row(person, years, month, test=i.InsuredTest.DISABILITY)


def _simplified_prior_basis(flag=None):
    """A deliberately inadmissible aggregate disability-prior basis."""
    person = _person(
        birth=date(1926, 2, 2),
        disability_onset=date(1989, 1, 15),
        current_disability_period_end=date(1989, 12, 31),
        prior_disability_periods=(),
        prior_disability_periods_provenance=UNKNOWN,
        conditions=() if flag is None else (flag,),
    )
    month = date(1990, 1, 1)
    years = history(
        person,
        month,
        {1964: 4, 1965: 4, 1966: 4, 1967: 2, 1987: 4, 1988: 2},
    )
    years[1950] = i.CoverageYear(
        OBSERVED,
        quarterly_wages=(
            Fraction(1200),
            Fraction(0),
            Fraction(0),
            Fraction(0),
        ),
    )
    return person, years, month


def test_unchanged_simplified_prior_basis_does_not_insure_disability():
    """RS 00301.315 B.1 excludes this ordinary-to-aggregate conversion."""
    person, years, month = _simplified_prior_basis()
    _invalid(person, years, month, test=i.InsuredTest.DISABILITY)


def test_unchanged_declared_simplified_prior_basis_keeps_named_refusal():
    """A fully-route declaration retains its unadjudicated specialist flag."""
    person, years, month = _simplified_prior_basis(
        i.CoverageCondition.SIMPLIFIED_PRE1951,
    )
    _refusal(
        person,
        years,
        month,
        i.InsuredUnsupportedReason.SIMPLIFIED_PRE1951,
        test=i.InsuredTest.DISABILITY,
    )
