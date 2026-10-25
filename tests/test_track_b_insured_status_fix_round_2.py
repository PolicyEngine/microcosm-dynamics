"""Statutory conformance: round-two invented insured-status regressions.

No population, behavioral, or forecast claim. Counterexamples were executed
by the independent reviewer against the reviewed head.
"""

from dataclasses import replace
from datetime import date

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import insured_status as i
from tests.test_track_b_insured_status import declared, history

PROPERTY = settings(max_examples=35, deadline=None)


def _person(birth, **values):
    declarations = {
        "prior_disability_periods_provenance": i.EarningsProvenance.OBSERVED,
        "sspa211_applies": False,
        "sspa211_provenance": i.EarningsProvenance.OBSERVED,
    }
    if values.get("disability_onset") is not None:
        declarations.update(
            current_disability_period_established=False,
            current_disability_period_provenance=i.EarningsProvenance.OBSERVED,
        )
    declarations.update(values)
    return i.Person(birth, **declarations)


def test_medical_onset_alone_never_freezes_fully_insured_elapsed_years():
    person = _person(date(1980, 2, 2), disability_onset=date(2007, 1, 15))
    month = date(2009, 4, 1)
    years = history(person, month, {2008: 4, 2009: 2})
    result = i.insured_status(person, years, month, test=i.InsuredTest.FULLY)
    assert result.fully.required == 7
    assert not result.fully.insured


def test_continuous_disability_can_first_qualify_after_medical_onset():
    person = _person(date(2000, 2, 2), disability_onset=date(2022, 1, 15))
    month = date(2022, 4, 1)
    years = history(person, month, {2021: 4, 2022: 2})
    result = i.insured_status(person, years, month)
    assert result.disability.insured
    assert result.disability.qc_count_lower == 6


def test_currently_insured_excludes_period_containing_dib_event():
    person = _person(
        date(1980, 2, 2),
        dib_entitlement_month=date(2004, 7, 1),
        prior_disability_periods=(
            i.DisabilityPeriod(
                date(2004, 1, 1), date(2004, 12, 31), special_insured=True
            ),
        ),
    )
    month = date(2005, 1, 1)
    years = history(person, month, {2001: 3, 2002: 3})
    result = i.insured_status(
        person, years, month, test=i.InsuredTest.CURRENTLY
    )
    assert result.currently.insured
    assert result.currently.qc_count_lower == 6
    assert result.currently.window == tuple(range(2000 * 4 + 3, 2004 * 4))


def test_unknown_prerequisite_count_bounds_contain_witness_switch_fillings():
    person = _person(
        date(1970, 2, 2),
        prior_disability_periods=(
            i.DisabilityPeriod(date(2005, 4, 2), date(2015, 9, 30)),
        ),
    )
    month = date(2020, 12, 1)
    counts = {year: 4 for year in (1996, 1997, 1998, 1999, 2000, 2015)}
    years = history(person, month, counts)
    years[2004] = declared(provenance=i.EarningsProvenance.UNKNOWN)
    result = i.insured_status(
        person, years, month, test=i.InsuredTest.DISABILITY
    )
    concrete = []
    for filling in range(5):
        years[2004] = declared(filling)
        filled = i.insured_status(
            person, years, month, test=i.InsuredTest.DISABILITY
        )
        assert filled.disability.insured == result.disability.insured
        concrete.append(filled.disability.fully_qc_count_lower)
    assert concrete == [24, 23, 24, 25, 26]
    assert all(
        result.disability.fully_qc_count_lower
        <= count
        <= result.disability.fully_qc_count_upper
        for count in concrete
    )


def _quarter(value):
    return value.year * 4 + (value.month - 1) // 3


def _quarter_date(quarter):
    return date(quarter // 4, 3 * (quarter % 4) + 1, 1)


def _plain_quarter_predicate(person, counts, quarter):
    """Independent direct-QC predicate: 214(a), 223(c), 404.130-.132.

    Generated births are February 2: ages are attained February 1, so the
    age-21 and age-31 quarters have no one-day boundary ambiguity. Annual
    QCs are assigned favorably within the candidate quarter and its year.
    """
    year = quarter // 4
    fully_required = min(40, max(6, year - (person.birth_date.year + 22)))
    total = sum(
        min(count, max(0, min(4, quarter - 4 * earnings_year + 1)))
        for earnings_year, count in counts.items()
        if earnings_year <= year
    )
    if total < fully_required:
        return False
    windows = [(quarter - 39, 20)]
    if quarter < (person.birth_date.year + 31) * 4:
        first = (person.birth_date.year + 21) * 4 + 1
        elapsed = quarter - first + 1
        if elapsed < 12:
            windows.append((quarter - 11, 6))
        elif elapsed > 40:
            windows.append((quarter - 39, 20))
        else:
            windows.append((first, max(6, elapsed // 2)))
    for first, required in windows:
        available = sum(
            min(
                count,
                max(
                    0,
                    min(quarter, earnings_year * 4 + 3)
                    - max(first, earnings_year * 4)
                    + 1,
                ),
            )
            for earnings_year, count in counts.items()
        )
        if available >= required:
            return True
    return False


@PROPERTY
@given(
    birth_year=st.integers(1978, 2000),
    onset_age=st.integers(18, 45),
    onset_quarter=st.integers(0, 3),
    elapsed_quarters=st.integers(0, 12),
    annual_counts=st.lists(st.integers(0, 4), min_size=16, max_size=16),
)
def test_continuous_onset_status_and_dli_equal_plain_quarter_scan(
    birth_year, onset_age, onset_quarter, elapsed_quarters, annual_counts
):
    first = (birth_year + onset_age) * 4 + onset_quarter
    last = first + elapsed_quarters
    onset = _quarter_date(first).replace(day=15)
    month = _quarter_date(last)
    person = _person(date(birth_year, 2, 2), disability_onset=onset)
    counts = {
        year: count
        for year, count in zip(
            range(last // 4 - 15, last // 4 + 1), annual_counts, strict=True
        )
        if year >= birth_year
    }
    quarters = [
        quarter
        for quarter in range(first, last + 1)
        if _plain_quarter_predicate(person, counts, quarter)
    ]
    result = i.insured_status(
        person,
        history(person, month, counts),
        month,
        test=i.InsuredTest.DISABILITY,
    )
    assert result.disability.insured == bool(quarters)
    assert result.disability.insured == (
        result.disability.qc_count_lower >= result.disability.required
        and result.disability.fully_qc_count_lower
        >= result.disability.fully_required
    )
    assert (
        result.dli.lower is not None and _quarter(result.dli.lower) >= first
    ) == bool(quarters)
    if quarters:
        assert result.disability.qualifying_quarter == _quarter_date(
            quarters[0]
        )
        assert result.disability.window[-1] == quarters[0]
        established = replace(
            person, current_disability_period_established=True
        )
        frozen = i.insured_status(
            established,
            history(established, month, counts),
            month,
            test=i.InsuredTest.DISABILITY,
        )
        expected_start = (
            onset if quarters[0] == first else _quarter_date(quarters[0])
        )
        assert frozen.current_disability_period_start == expected_start
        # CFR404.315(a): a waiting month is both disabled and insured.
        # No such month can precede the derived period's first insured year.
        assert all(
            not _plain_quarter_predicate(person, counts, quarter)
            for quarter in range(first, quarters[0])
        )
        assert expected_start.year == _quarter_date(quarters[0]).year


@PROPERTY
@given(
    shift=st.integers(0, 4),
    late_count=st.integers(0, 4),
    filling=st.integers(0, 4),
)
def test_unknown_recent_and_fully_counts_contain_concrete_period_fillings(
    shift, late_count, filling
):
    """Include the reviewer's treatment switch: 24,23,24,25,26 QCs."""
    person = _person(
        date(1970 + shift, 2, 2),
        prior_disability_periods=(
            i.DisabilityPeriod(
                date(2005 + shift, 4, 2), date(2015 + shift, 9, 30)
            ),
        ),
    )
    month = date(2020 + shift, 12, 1)
    counts = {year + shift: 4 for year in (1996, 1997, 1998, 1999, 2000, 2015)}
    counts[2019 + shift] = late_count
    years = history(person, month, counts)
    years[2004 + shift] = declared(provenance=i.EarningsProvenance.UNKNOWN)
    try:
        bounded = i.insured_status(
            person, years, month, test=i.InsuredTest.DISABILITY
        )
    except i.InsuredConfigurationUnsupported as error:
        assert error.reason is i.InsuredUnsupportedReason.UNKNOWN_EARNINGS
        return
    years[2004 + shift] = declared(filling)
    concrete = i.insured_status(
        person, years, month, test=i.InsuredTest.DISABILITY
    )
    assert bounded.disability.insured == concrete.disability.insured
    assert (
        bounded.disability.qc_count_lower
        <= concrete.disability.qc_count_lower
        <= bounded.disability.qc_count_upper
    )
    assert (
        bounded.disability.fully_qc_count_lower
        <= concrete.disability.fully_qc_count_lower
        <= bounded.disability.fully_qc_count_upper
    )


@PROPERTY
@example(
    start_year=2005,
    end_year=2015,
    recent=[4, 4, 4, 4, 4],
    kind=i.InsuredTest.DISABILITY,
    current_unknown=True,
    early_current=False,
    established_current=False,
)
@example(
    start_year=2005,
    end_year=2015,
    recent=[0, 0, 0, 0, 0],
    kind=i.InsuredTest.DISABILITY,
    current_unknown=True,
    early_current=True,
    established_current=False,
)
@example(
    start_year=2005,
    end_year=2015,
    recent=[0, 0, 0, 0, 0],
    kind=i.InsuredTest.DISABILITY,
    current_unknown=True,
    early_current=False,
    established_current=False,
)
@example(
    start_year=2005,
    end_year=2015,
    recent=[0, 0, 0, 0, 0],
    kind=i.InsuredTest.DISABILITY,
    current_unknown=True,
    early_current=True,
    established_current=True,
)
@given(
    established_current=st.booleans(),
    early_current=st.booleans(),
    current_unknown=st.booleans(),
    start_year=st.integers(2005, 2008),
    end_year=st.integers(2010, 2015),
    recent=st.lists(st.integers(0, 4), min_size=5, max_size=5),
    kind=st.sampled_from(
        [
            i.InsuredTest.FULLY,
            i.InsuredTest.CURRENTLY,
            i.InsuredTest.DISABILITY,
        ]
    ),
)
def test_unknown_period_status_and_dli_bounds_contain_concrete_fillings(
    start_year,
    end_year,
    recent,
    kind,
    current_unknown,
    early_current,
    established_current,
):
    """The declared prior period was insured at its start for every draw."""
    month = date(2020, 12, 1)
    onset_year = 2004 if early_current else 2016
    if early_current:
        start_year = 2000 + (start_year - 2005) // 2
        end_year = 2003
    unknown = _person(
        date(1970, 2, 2),
        prior_disability_periods_provenance=i.EarningsProvenance.UNKNOWN,
        **(
            {
                "disability_onset": date(onset_year, 1, 15),
                "current_disability_period_established": (
                    True if early_current and established_current else None
                ),
                "current_disability_period_provenance": (
                    i.EarningsProvenance.OBSERVED
                    if early_current and established_current
                    else i.EarningsProvenance.UNKNOWN
                ),
            }
            if current_unknown
            else {}
        ),
    )
    first_earnings_year = 1990 if early_current else 1995
    counts = {
        year: 4
        for year in range(first_earnings_year, first_earnings_year + 10)
    }
    counts.update(zip(range(2016, 2021), recent, strict=True))
    years = history(unknown, month, counts)
    try:
        bounded = i.insured_status(unknown, years, month, test=kind)
    except i.InsuredConfigurationUnsupported as error:
        if (
            early_current
            and current_unknown
            and established_current
            and kind in (i.InsuredTest.FULLY, i.InsuredTest.DISABILITY)
        ):
            pytest.fail("Disregarding all periods already proves insurance")
        assert error.reason in (
            i.InsuredUnsupportedReason.UNKNOWN_PERIODS,
            i.InsuredUnsupportedReason.UNKNOWN_CURRENT_PERIOD,
        )
        return
    assert bounded.decided_despite_unknowns
    for periods in (
        (),
        (i.DisabilityPeriod(date(start_year, 4, 2), date(end_year, 9, 30)),),
    ):
        known = replace(
            unknown,
            prior_disability_periods=periods,
            prior_disability_periods_provenance=i.EarningsProvenance.OBSERVED,
            **(
                {
                    "current_disability_period_established": False,
                    "current_disability_period_provenance": i.EarningsProvenance.OBSERVED,
                }
                if current_unknown
                else {}
            ),
        )
        completions = (
            [] if unknown.current_disability_period_established else [known]
        )
        if current_unknown:
            credits = {
                year: i._credits(year, row, False)
                for year, row in years.items()
            }
            if any(
                i._witness(
                    known,
                    credits,
                    _quarter_date(quarter),
                    None,
                    i.InsuredTest.DISABILITY,
                )[0]
                for quarter in range(
                    _quarter(known.disability_onset), _quarter(month) + 1
                )
            ):
                completions.append(
                    replace(known, current_disability_period_established=True)
                )
        for completed in completions:
            concrete = i.insured_status(completed, years, month, test=kind)
            name = kind.value
            assert (
                getattr(bounded, name).insured
                == getattr(concrete, name).insured
            )
            if concrete.dli is not None:
                assert bounded.dli is not None
                if concrete.dli.lower is not None:
                    assert bounded.dli.lower is None or (
                        bounded.dli.lower <= concrete.dli.lower
                    )
                    assert bounded.dli.upper is not None
                    assert concrete.dli.upper <= bounded.dli.upper


def test_sam_white_can_become_insured_later_poms_140_example_2():
    """Published birth/onset; the missing later earnings are invented."""
    person = _person(date(1961, 8, 20), disability_onset=date(1984, 4, 12))
    onset_month = date(1984, 4, 1)
    later_month = date(1984, 7, 1)
    counts = {1983: 3, 1984: 3}
    onset = i.insured_status(
        person,
        history(person, onset_month, counts),
        onset_month,
        test=i.InsuredTest.DISABILITY,
    )
    later = i.insured_status(
        person,
        history(person, later_month, counts),
        later_month,
        test=i.InsuredTest.DISABILITY,
    )
    assert not onset.disability.insured
    assert onset.disability.qc_count_lower == 5
    assert later.disability.insured
    assert later.disability.qc_count_lower == 6
    assert later.disability.qualifying_quarter == later_month
    assert later.disability.window[-1] == 1984 * 4 + 2


def test_missing_current_period_declaration_is_input_error_with_onset():
    with pytest.raises(i.InvalidFamilyInput):
        person = i.Person(
            date(1980, 2, 2),
            disability_onset=date(2007, 1, 15),
            prior_disability_periods_provenance=i.EarningsProvenance.OBSERVED,
            sspa211_applies=False,
            sspa211_provenance=i.EarningsProvenance.OBSERVED,
        )
        month = date(2009, 4, 1)
        i.insured_status(
            person, history(person, month, {2008: 4, 2009: 2}), month
        )


def test_explicit_unknown_current_period_can_decide_status_without_a_freeze():
    person = _person(
        date(1980, 2, 2),
        disability_onset=date(2020, 1, 15),
        current_disability_period_established=None,
        current_disability_period_provenance=i.EarningsProvenance.UNKNOWN,
    )
    month = date(2026, 1, 1)
    years = history(person, month, {year: 4 for year in range(2010, 2020)})
    result = i.insured_status(person, years, month, test=i.InsuredTest.FULLY)
    assert result.fully.insured
    assert result.decided_despite_unknowns


def test_unknown_sspa_applicability_does_not_block_qc_only_uninsured_result():
    person = _person(
        date(1980, 2, 2),
        sspa211_applies=None,
        sspa211_provenance=i.EarningsProvenance.UNKNOWN,
    )
    month = date(2026, 1, 1)
    result = i.insured_status(person, history(person, month), month)
    assert not result.fully.insured
    assert not result.currently.insured
    assert not result.disability.insured
    assert result.decided_despite_unknowns

    # Current status can be false while the QC-only historical DLI is positive.
    old_years = history(person, month, {year: 4 for year in range(2000, 2005)})
    historical = i.insured_status(person, old_years, month)
    exempt = i.insured_status(
        replace(
            person,
            sspa211_applies=False,
            sspa211_provenance=i.EarningsProvenance.OBSERVED,
        ),
        old_years,
        month,
    )
    assert not historical.fully.insured
    assert not historical.currently.insured
    assert not historical.disability.insured
    assert historical.decided_despite_unknowns
    assert exempt.dli.lower == exempt.dli.upper == date(2009, 12, 31)
    assert historical.dli.lower is None
    assert historical.dli.upper == exempt.dli.upper


def test_unknown_sspa_applicability_refuses_when_qcs_would_insure():
    person = _person(
        date(1980, 2, 2),
        sspa211_applies=None,
        sspa211_provenance=i.EarningsProvenance.UNKNOWN,
    )
    month = date(2026, 1, 1)
    years = history(person, month, {year: 4 for year in range(2010, 2020)})
    with pytest.raises(i.InsuredConfigurationUnsupported) as error:
        i.insured_status(person, years, month, test=i.InsuredTest.FULLY)
    assert error.value.reason.value == "sspa211_applicability_unknown"


def test_never_assigned_ssn_retains_sspa211_additional_requirement():
    person = _person(
        date(1980, 2, 2),
        alien_worker=True,
        ssn_never_assigned=True,
        sspa211_applies=None,
        sspa211_provenance=i.EarningsProvenance.UNKNOWN,
    )
    month = date(2026, 1, 1)
    years = history(person, month, {year: 4 for year in range(2010, 2020)})
    with pytest.raises(i.InsuredConfigurationUnsupported) as error:
        i.insured_status(person, years, month, test=i.InsuredTest.FULLY)
    assert error.value.reason is i.InsuredUnsupportedReason.ALIEN_WORKER


@PROPERTY
@given(
    provenance=st.sampled_from(
        [
            i.EarningsProvenance.OBSERVED,
            i.EarningsProvenance.CONVENTION_FILLED,
        ]
    ),
    count=st.integers(0, 4),
)
def test_declared_fact_provenance_preserves_computed_status(provenance, count):
    month = date(2022, 4, 1)
    person = _person(date(2000, 2, 2), disability_onset=date(2022, 1, 15))
    years = history(person, month, {2021: 4, 2022: count})
    observed = i.insured_status(person, years, month)
    convention_id = (
        "invented-round-two-facts"
        if provenance is i.EarningsProvenance.CONVENTION_FILLED
        else None
    )
    alternate = replace(
        person,
        prior_disability_periods_provenance=provenance,
        prior_disability_periods_convention_id=convention_id,
        current_disability_period_provenance=provenance,
        current_disability_period_convention_id=convention_id,
        sspa211_provenance=provenance,
        sspa211_convention_id=convention_id,
    )
    result = i.insured_status(alternate, years, month)
    assert result.fully == observed.fully
    assert result.currently == observed.currently
    assert result.disability == observed.disability
    assert result.dli == observed.dli


@pytest.mark.parametrize(
    "counts,expected_start",
    [
        ({2020: 2, 2021: 4}, date(2022, 1, 15)),
        ({2021: 4, 2022: 2}, date(2022, 4, 1)),
    ],
    ids=["insured-onset-day", "first-later-insured-quarter"],
)
def test_established_current_period_starts_only_when_disabled_and_insured(
    counts, expected_start
):
    person = _person(
        date(2000, 2, 2),
        disability_onset=date(2022, 1, 15),
        current_disability_period_established=True,
    )
    month = date(2022, 4, 1)
    result = i.insured_status(person, history(person, month, counts), month)
    assert result.current_disability_period_start == expected_start
    assert result.disability.insured
    assert result.disability.qualifying_quarter == expected_start.replace(
        month=3 * ((expected_start.month - 1) // 3) + 1, day=1
    )


def test_unknown_current_period_refuses_when_establishment_changes_full_status():
    person = _person(
        date(1980, 2, 2),
        disability_onset=date(2000, 1, 15),
        current_disability_period_established=None,
        current_disability_period_provenance=i.EarningsProvenance.UNKNOWN,
    )
    month = date(2009, 4, 1)
    years = history(person, month, {1999: 4, 2000: 2})
    with pytest.raises(i.InsuredConfigurationUnsupported) as error:
        i.insured_status(person, years, month, test=i.InsuredTest.FULLY)
    assert (
        error.value.reason is i.InsuredUnsupportedReason.UNKNOWN_CURRENT_PERIOD
    )
    unfrozen = i.insured_status(
        replace(
            person,
            current_disability_period_established=False,
            current_disability_period_provenance=i.EarningsProvenance.OBSERVED,
        ),
        years,
        month,
        test=i.InsuredTest.ALL,
    )
    frozen = i.insured_status(
        replace(
            person,
            current_disability_period_established=True,
            current_disability_period_provenance=i.EarningsProvenance.OBSERVED,
        ),
        years,
        month,
        test=i.InsuredTest.FULLY,
    )
    assert not unfrozen.fully.insured
    assert unfrozen.fully.required == 7
    assert unfrozen.disability.insured
    assert unfrozen.disability.qualifying_quarter == date(2000, 4, 1)
    assert (
        unfrozen.disability.fully_qc_count_lower
        >= unfrozen.disability.fully_required
    )
    assert frozen.fully.insured
    assert frozen.fully.required == 6
    assert frozen.current_disability_period_start == date(2000, 4, 1)


@PROPERTY
@example(counts=(0, 0), kind=i.InsuredTest.DISABILITY, old_history=True)
@given(
    old_history=st.booleans(),
    counts=st.tuples(st.integers(0, 4), st.integers(0, 4)).filter(
        lambda values: sum(values) < 6
    ),
    kind=st.sampled_from(
        [
            i.InsuredTest.FULLY,
            i.InsuredTest.CURRENTLY,
            i.InsuredTest.DISABILITY,
        ]
    ),
)
def test_unknown_sspa_applicability_preserves_qc_impossibility(
    counts, kind, old_history
):
    month = date(2026, 1, 1)
    person = _person(
        date(1980, 2, 2),
        sspa211_applies=None,
        sspa211_provenance=i.EarningsProvenance.UNKNOWN,
    )
    annual_counts = {2025: counts[0], 2026: counts[1]}
    if old_history:
        annual_counts.update({year: 4 for year in range(2000, 2005)})
    years = history(person, month, annual_counts)
    exempt = i.insured_status(
        replace(
            person,
            sspa211_applies=False,
            sspa211_provenance=i.EarningsProvenance.OBSERVED,
        ),
        years,
        month,
        test=kind,
    )
    try:
        uncertain = i.insured_status(person, years, month, test=kind)
    except i.InsuredConfigurationUnsupported as error:
        assert error.reason is i.InsuredUnsupportedReason.UNKNOWN_SSPA211
        assert getattr(exempt, kind.value).insured
        return
    assert not getattr(uncertain, kind.value).insured
    assert (
        getattr(uncertain, kind.value).insured
        == getattr(exempt, kind.value).insured
    )
    assert uncertain.decided_despite_unknowns

    if exempt.dli is not None:
        assert uncertain.dli is not None
        assert uncertain.dli.lower is None
        assert uncertain.dli.upper == exempt.dli.upper


@PROPERTY
@given(
    shift=st.integers(0, 3),
    onset_offset=st.integers(0, 11),
    recent=st.lists(st.integers(0, 4), min_size=5, max_size=5),
)
def test_continuous_onset_with_prior_period_matches_plain_predicate_scan(
    shift, onset_offset, recent
):
    """Shared per-quarter predicate checks the scan with prior treatments."""
    first = (2016 + shift) * 4 + onset_offset
    month = date(2020 + shift, 12, 1)
    person = _person(
        date(1970 + shift, 2, 2),
        disability_onset=_quarter_date(first).replace(day=15),
        prior_disability_periods=(
            i.DisabilityPeriod(
                date(2005 + shift, 4, 2), date(2015 + shift, 9, 30)
            ),
        ),
    )
    counts = {year + shift: 4 for year in range(1995, 2005)}
    counts.update(zip(range(2016 + shift, 2021 + shift), recent, strict=True))
    years = history(person, month, counts)
    credits = {
        year: i._credits(year, row, False) for year, row in years.items()
    }
    quarters = [
        quarter
        for quarter in range(first, _quarter(month) + 1)
        if i._witness(
            person,
            credits,
            _quarter_date(quarter),
            None,
            i.InsuredTest.DISABILITY,
        )[0]
    ]
    result = i.insured_status(
        person, years, month, test=i.InsuredTest.DISABILITY
    )
    assert result.disability.insured == bool(quarters)
    assert result.disability.insured == (
        result.disability.qc_count_lower >= result.disability.required
        and result.disability.fully_qc_count_lower
        >= result.disability.fully_required
    )
    assert (
        result.dli.lower is not None and _quarter(result.dli.lower) >= first
    ) == bool(quarters)
    if quarters:
        assert result.disability.qualifying_quarter == _quarter_date(
            quarters[0]
        )
        assert result.disability.window[-1] == quarters[0]
