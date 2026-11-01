"""Bounded independent classification oracle for invented declarations.

Verification class: statutory conformance. No population, behavioral, or
forecast claim. The oracle uses public declaration types, plain quarter
arithmetic, and exhaustive annual placements; it calls no implementation
helper. CFR 404.110/.130/.131/.320/.321 and POMS RS 00301.132/.140/.147/.480
supply the rules.

The deterministic lattice contains more than 3,000 declarations, with at most
two UNKNOWN credit years (each completed by every permitted quarter subset, up
to sixteen), two observed prior periods, and bounded UNKNOWN histories. UNKNOWN
history is completed by the empty history and every one-period quarter interval
from the first possible credited quarter through the onset quarter, with the
end clamped before the onset day. Each start must itself be insured. Special
provenance is admitted only for an under31 witness without 20/40. Earlier
blindness may supply insurance through fully insured status even when current
blindness is absent. Two bounded classes combine a blind prefix with a later
special prior: the existing flagged prefix from birth through the quarter
before the first QC, and every fully insured blind start with a prefix ending
immediately before each later insured special start. Each class includes every
possible special ending. Thus no-flag blind prefixes must establish ordinary
fully insured status at their own starts. This is an explicit bound: arbitrary
gapped two-period histories, arbitrary other two-period
histories and three or more UNKNOWN periods are not exhausted. Named negative
examples have separate impossibility proofs that exclude additional periods;
a bounded search alone is not such a proof.

UNKNOWN endings enumerate every month end through query, plus the statutory
FRA/death cap. Modern queries are at most four elapsed quarters after onset.
Historical boundary queries are in 1968 or 1973; the no-flag historical blind
controls query in 1977 or 1996. These historical cases have known endings.
Annual totals have at most two partly credited observed years; selected cases
have at most 192 complete annual placements each. A fully-route flag's first
quarter is a free fact: every candidate start, the quarter before onset, and a
quarter after
the start horizon are enumerated. UNKNOWN histories also admit every possible
historical start and a sentinel before birth. One common flag start governs
both prior and current insurance; an established prior does not backdate it.
Raw earnings, foreign credits, credit-adding flags, complex boundary refusals,
administrative application facts and SSPA211 are outside this oracle.
Declarations use female sex; the male fully insured transition for cohorts
born before 1913 is outside the bound. The
separate round 13 regression module covers credit-adding routes. Known prior
periods are declared established facts and are not re-adjudicated. This oracle
checks declaration classification, not coherence across separate assignment
witnesses returned for individual statuses and DLI.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass, replace
from datetime import date, timedelta
from fractions import Fraction
from functools import lru_cache
from itertools import combinations, product

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import insured_status as rule
from populace_dynamics.track_b.gross_benefits import count_family_outcomes

OBSERVED = rule.EarningsProvenance.OBSERVED
UNKNOWN = rule.EarningsProvenance.UNKNOWN
WEIGHT = Fraction(17, 9)
FULLY_FLAGS = (
    rule.CoverageCondition.DEEMED_FULLY_INSURED,
    rule.CoverageCondition.TRANSITIONAL_INSURED,
    rule.CoverageCondition.EARNED_BASIS,
    rule.CoverageCondition.SIMPLIFIED_PRE1951,
)
ALTERNATE_FLAG = rule.CoverageCondition.DISABILITY_BEFORE_1956
FLAG_SETS = (
    (),
    *((flag,) for flag in FULLY_FLAGS),
    (ALTERNATE_FLAG,),
    *((flag, ALTERNATE_FLAG) for flag in FULLY_FLAGS),
    (FULLY_FLAGS[0], FULLY_FLAGS[1]),
)


def _quarter(value):
    return value.year * 4 + (value.month - 1) // 3


def _quarter_date(value):
    year, part = divmod(value, 4)
    return date(year, part * 3 + 1, 1)


def _attained(birth, age):
    year = birth.year + age
    day = min(birth.day, calendar.monthrange(year, birth.month)[1])
    return date(year, birth.month, day) - timedelta(days=1)


def _fra(birth):
    cohort = (birth - timedelta(days=1)).year
    months = 780
    if 1938 <= cohort <= 1942:
        months += (cohort - 1937) * 2
    elif 1943 <= cohort <= 1954:
        months = 792
    elif 1955 <= cohort <= 1959:
        months = 792 + (cohort - 1954) * 2
    elif cohort >= 1960:
        months = 804
    index = birth.year * 12 + birth.month - 1 + months
    year, month = divmod(index, 12)
    return date(year, month + 1, birth.day) - timedelta(days=1)


def _month_end(value):
    return value.replace(day=calendar.monthrange(value.year, value.month)[1])


def _minus_two_months(value):
    year, month = divmod(value.year * 12 + value.month - 3, 12)
    return date(year, month + 1, 1)


@dataclass(frozen=True)
class EnumeratedPeriod:
    """An arithmetic completion, independent of production validation."""

    start: date
    end: date
    special_insured: bool = False


@dataclass(frozen=True)
class Declaration:
    person: rule.Person
    month: date
    # Each entry is (year, fixed quarters or None, annual count or None).
    # Both None represents UNKNOWN, independently completed by all subsets.
    annual: tuple[tuple[int, tuple[int, ...] | None, int | None], ...]
    exit_month: date | None = None


def _history(case):
    rows = {}
    for year, fixed, count in case.annual:
        if fixed is None and count is None:
            rows[year] = rule.CoverageYear(UNKNOWN)
        elif year < 1978:
            assert fixed is not None
            rows[year] = rule.CoverageYear(
                OBSERVED,
                qc_quarters=tuple(year * 4 + q in fixed for q in range(4)),
            )
        else:
            rows[year] = rule.CoverageYear(OBSERVED, qc_count=count)
    return rows


def _declaration(
    *,
    birth=date(1960, 2, 2),
    onset=date(2000, 1, 15),
    end=date(2000, 12, 31),
    month=date(2001, 1, 1),
    flags=(),
    blind=False,
    established=True,
    periods=(),
    prior_unknown=False,
    through=None,
    death=None,
    exit_month=None,
    counts=(),
    fixed=(),
    unknown_years=(),
):
    person = rule.Person(
        birth,
        sex=rule.Sex.FEMALE,
        death_date=death,
        disability_onset=onset,
        statutory_blindness=blind,
        conditions=frozenset(flags),
        prior_disability_periods=periods,
        prior_disability_periods_provenance=(
            UNKNOWN if prior_unknown else OBSERVED
        ),
        current_disability_period_established=established,
        current_disability_period_provenance=(
            UNKNOWN if established is None else OBSERVED
        ),
        current_disability_period_end=end if established else None,
        current_disability_period_end_provenance=(
            OBSERVED if end is not None and established else UNKNOWN
        ),
        current_disability_period_continues_through=through,
        current_disability_period_continues_through_provenance=(
            OBSERVED if through is not None else UNKNOWN
        ),
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
    )
    last_year = min(
        month.year,
        exit_month.year if exit_month else month.year,
        death.year if death else month.year,
    )
    counts = dict(counts)
    fixed = frozenset(fixed)
    annual = []
    for year in range(max(1937, birth.year), last_year + 1):
        if year in unknown_years:
            annual.append((year, None, None))
        elif year < 1978:
            annual.append(
                (year, tuple(q for q in sorted(fixed) if q // 4 == year), 0)
            )
        else:
            annual.append((year, None, counts.get(year, 0)))
    return Declaration(person, month, tuple(annual), exit_month)


def _placements(case):
    person = case.person
    last = min(
        _quarter(case.month),
        _quarter(person.death_date) if person.death_date else 99999,
        _quarter(case.exit_month) if case.exit_month else 99999,
    )
    alternatives = []
    for year, fixed, count in case.annual:
        slots = tuple(
            q
            for q in range(year * 4, year * 4 + 4)
            if _quarter(person.birth_date) <= q <= last
        )
        if fixed is not None:
            alternatives.append((fixed,))
        elif count is None:
            alternatives.append(
                tuple(
                    choice
                    for number in range(len(slots) + 1)
                    for choice in combinations(slots, number)
                )
            )
        else:
            alternatives.append(
                tuple(combinations(slots, min(count, len(slots))))
            )
    for chosen in product(*alternatives):
        yield frozenset(q for annual in chosen for q in annual)


@lru_cache(maxsize=32768)
def _fully_needed(person, start, periods):
    first = max(1951, _attained(person.birth_date, 21).year + 1)
    last = min(start.year, _attained(person.birth_date, 62).year)
    if person.death_date is not None:
        last = min(last, person.death_date.year)
    return min(
        40,
        max(
            6,
            sum(
                not any(p.start.year <= year <= p.end.year for p in periods)
                for year in range(first, last)
            ),
        ),
    )


def _usable(credits, start, periods):
    return frozenset(
        q
        for q in credits
        if q <= start
        and not any(
            _quarter(period.start) < q < _quarter(period.end)
            for period in periods
        )
    )


def _elapsed_quarters(first, last, periods, credits):
    return tuple(
        q
        for q in range(first, last + 1)
        if not any(
            _quarter(period.start) <= q <= _quarter(period.end)
            and q not in credits
            for period in periods
        )
    )


def _lookback(start, number, periods, credits):
    answer = []
    while len(answer) < number:
        if not any(
            _quarter(period.start) <= start <= _quarter(period.end)
            and start not in credits
            for period in periods
        ):
            answer.append(start)
        start -= 1
    return frozenset(answer)


@lru_cache(maxsize=32768)
def _ordinary_routes(
    person, credits, start, periods, fully_from, *, special=False
):
    """All routes for one fixed placement, start and prior treatment."""
    used = _usable(credits, start, periods)
    fully = (fully_from is not None and start >= fully_from) or len(
        used
    ) >= _fully_needed(person, _quarter_date(start), periods)
    if not fully:
        return ()
    if person.statutory_blindness:
        return ("blindness",)
    routes = []
    if len(used & _lookback(start, 40, periods, used)) >= 20:
        routes.append("20_of_40")
    young = start < _quarter(_attained(person.birth_date, 31))
    subsequent = special or any(p.special_insured for p in periods)
    if young or subsequent:
        elapsed = _elapsed_quarters(
            max(1937 * 4, _quarter(_attained(person.birth_date, 21)) + 1),
            start,
            periods,
            used,
        )
        if len(elapsed) < 12:
            window, needed = _lookback(start, 12, periods, used), 6
        elif len(elapsed) > 40:
            window, needed = frozenset(elapsed[-40:]), 20
        else:
            window, needed = frozenset(elapsed), max(6, len(elapsed) // 2)
        if len(used & window) >= needed:
            routes.append("under31" if young else "subsequent_special")
    return tuple(routes)


def _endings(case):
    person = case.person
    if person.current_disability_period_end is not None:
        return (person.current_disability_period_end,)
    cap = _fra(person.birth_date).replace(day=1) - timedelta(days=1)
    if person.death_date is not None:
        cap = min(cap, person.death_date)
    through = person.current_disability_period_continues_through
    first = person.disability_onset
    candidates = []
    index = first.year * 12 + first.month - 1
    stop = min(case.month, cap).year * 12 + min(case.month, cap).month - 1
    for value in range(index, stop + 1):
        year, month = divmod(value, 12)
        ending = min(_month_end(date(year, month + 1, 1)), cap)
        if through is None or ending >= through:
            candidates.append(ending)
    if cap > case.month and (through is None or cap >= through):
        candidates.append(cap)
    return tuple(dict.fromkeys(candidates))


def _start_horizon(case, ending):
    person = case.person
    horizon = min(case.month, ending, _fra(person.birth_date).replace(day=1))
    fra_end = _fra(person.birth_date).replace(day=1) - timedelta(days=1)
    # Only an actually declared pre-February-1981 ending implies recovery;
    # an UNKNOWN completion may instead be an adjudicated paragraph(c) end.
    declared = person.current_disability_period_end
    if (
        declared is not None
        and declared < date(1981, 2, 1)
        and declared.replace(day=1) < fra_end.replace(day=1)
        and (
            person.death_date is None
            or declared.replace(day=1) < person.death_date.replace(day=1)
        )
    ):
        horizon = min(horizon, _minus_two_months(declared))
    if person.death_date is not None:
        horizon = min(horizon, person.death_date)
    if person.current_disability_period_continues_through is not None:
        horizon = min(
            horizon, person.current_disability_period_continues_through
        )
    return _quarter(horizon)


def _alternate(case, credits, start, periods, prior):
    person = case.person
    if not 1952 * 4 + 2 <= start <= 1955 * 4 + 3:
        return False
    # The period-covered reading is the conservative existing contract.
    # Every completion's guaranteed disabled months end at the observed
    # end/continuity minus two, clamped at onset; UNKNOWN ends share onset.
    dated = (
        person.current_disability_period_end
        or person.current_disability_period_continues_through
    )
    covered = person.disability_onset
    if dated is not None:
        covered = max(covered, _minus_two_months(dated))
    last = min(
        _quarter(case.month),
        _quarter(_fra(person.birth_date).replace(day=1) - timedelta(days=1)),
        _quarter(covered),
        1960 * 4 + 2,
    )
    for candidate in range(_quarter(person.disability_onset), last + 1):
        # The exclusion can use either favorable treatment, independently
        # of the treatment supplying this alternate clock.
        for treatment in (prior, ()):
            used = _usable(credits, candidate, treatment)
            if len(used & _lookback(candidate, 40, treatment, used)) >= 20:
                return False
    used = _usable(credits, start, periods)
    continuous = _elapsed_quarters(1951 * 4, start - 1, periods, used)
    return len(used) >= 20 and len(continuous) >= 6 and set(continuous) <= used


def _unknown_priors(case, credits, fully_from):
    person = case.person
    yield ()
    if not credits:
        return
    stop = _quarter(person.disability_onset)
    first_candidate = (
        _quarter(person.birth_date) if fully_from is not None else min(credits)
    )
    blind_person = replace(person, statutory_blindness=True)
    for first in range(first_candidate, stop + 1):
        routes = _ordinary_routes(person, credits, first, (), fully_from)
        blind_prior = _ordinary_routes(
            blind_person,
            credits,
            first,
            (),
            fully_from,
        )
        if not routes and not blind_prior:
            continue
        for last in range(first, stop + 1):
            # At quarter resolution a one-month DIB-entitled period can
            # occupy even a single quarter (Act216(i)(2)(A),404.315(a)(4)).
            end = min(
                _month_end(
                    _quarter_date(last).replace(
                        month=(_quarter_date(last).month + 2)
                    )
                ),
                person.disability_onset - timedelta(days=1),
            )
            for special in (
                (False, True)
                if "under31" in routes and "20_of_40" not in routes
                else (False,)
            ):
                yield (
                    EnumeratedPeriod(
                        max(person.birth_date, _quarter_date(first)),
                        end,
                        special_insured=special,
                    ),
                )

    special_stop = min(stop, _quarter(_attained(person.birth_date, 31)) - 1)
    # Preserve the existing favorable birth prefix. Its gap before the later
    # special start leaves all six QCs available to establish that start.
    birth_quarter = _quarter(person.birth_date)
    prefix_end = _quarter_date(min(credits)) - timedelta(days=1)
    if prefix_end >= person.birth_date and _ordinary_routes(
        blind_person, credits, birth_quarter, (), fully_from
    ):
        prefix = EnumeratedPeriod(person.birth_date, prefix_end)
        for first in range(min(credits), special_stop + 1):
            yield from _special_after_prefix(
                case, credits, fully_from, prefix, first
            )

    # The added two-period class covers contiguous blind-then-special periods.
    # Each blind start must independently be fully insured, including when
    # no flag exists; current nonblindness says nothing about that prior.
    for blind_first in range(first_candidate, special_stop):
        if not _ordinary_routes(
            blind_person, credits, blind_first, (), fully_from
        ):
            continue
        for first in range(
            max(min(credits), blind_first + 1), special_stop + 1
        ):
            prefix = EnumeratedPeriod(
                max(person.birth_date, _quarter_date(blind_first)),
                _quarter_date(first) - timedelta(days=1),
            )
            yield from _special_after_prefix(
                case, credits, fully_from, prefix, first
            )


def _special_after_prefix(case, credits, fully_from, prefix, first):
    person = case.person
    routes = _ordinary_routes(person, credits, first, (prefix,), fully_from)
    if "under31" not in routes or "20_of_40" in routes:
        return
    for last in range(first, _quarter(person.disability_onset) + 1):
        end = min(
            _month_end(
                _quarter_date(last).replace(
                    month=(_quarter_date(last).month + 2)
                )
            ),
            person.disability_onset - timedelta(days=1),
        )
        yield (
            prefix,
            EnumeratedPeriod(_quarter_date(first), end, special_insured=True),
        )


def _flag_starts(case, horizon):
    if not set(case.person.conditions) & set(FULLY_FLAGS):
        return (None,)
    onset = _quarter(case.person.disability_onset)
    first = (
        _quarter(case.person.birth_date) - 1
        if case.person.prior_disability_periods_provenance is UNKNOWN
        else onset - 1
    )
    return tuple(range(first, horizon + 2))


def _has_valid_filling(case):
    # Individual fully flags have identical oracle semantics; the alternate
    # flag adds no route. Canonicalization avoids repeating the enumeration.
    canonical = (
        (FULLY_FLAGS[0],)
        if set(case.person.conditions) & set(FULLY_FLAGS)
        else ()
    )
    return _enumerated_filling(
        replace(
            case, person=replace(case.person, conditions=frozenset(canonical))
        )
    )


@lru_cache(maxsize=16384)
def _enumerated_filling(case):
    person = case.person
    # UNKNOWN establishment always has the absent-period completion.
    if person.current_disability_period_established is not True:
        return True
    for credits in _placements(case):
        # Every nonblind route needs at least six actual QCs, regardless of
        # a flag's start or any deletion of elapsed quarters by a prior.
        if not person.statutory_blindness and len(credits) < 6:
            continue
        # After age 31 fewer than twenty QCs require a special prior. With
        # UNKNOWN history, no QC before age 31 excludes every such prior;
        # a blind prior alone never supplies special provenance.
        age31 = _quarter(_attained(person.birth_date, 31))
        if (
            not person.statutory_blindness
            and len(credits) < 20
            and _quarter(person.disability_onset) >= age31
            and not any(
                p.special_insured for p in person.prior_disability_periods
            )
            and (
                person.prior_disability_periods_provenance is OBSERVED
                or not any(q < age31 for q in credits)
            )
        ):
            continue
        for ending in _endings(case):
            horizon = _start_horizon(case, ending)
            for fully_from in _flag_starts(case, horizon):
                histories = (
                    _unknown_priors(case, credits, fully_from)
                    if person.prior_disability_periods_provenance is UNKNOWN
                    else (person.prior_disability_periods,)
                )
                for prior in histories:
                    if _history_has_clear_start(
                        case, credits, prior, horizon, fully_from
                    ):
                        return True
    return False


def _history_has_clear_start(case, credits, prior, horizon, fully_from):
    person = case.person
    starts = range(
        _quarter(person.disability_onset),
        horizon + 1,
    )
    for periods in ((prior, ()) if prior else ((),)):
        # 404.321(a) fixes the first insured quarter. A later
        # clear quarter cannot repair an already insured but
        # overlapping onset quarter for this fixed filling, treatment and f.
        first_ordinary = next(
            (
                start
                for start in starts
                if _ordinary_routes(
                    person,
                    credits,
                    start,
                    periods,
                    fully_from,
                    special=any(p.special_insured for p in prior),
                )
            ),
            None,
        )
        if first_ordinary is not None and not any(
            _quarter(p.start) <= first_ordinary <= _quarter(p.end)
            for p in prior
        ):
            return True
        for start in starts:
            if any(
                _quarter(p.start) <= start <= _quarter(p.end) for p in prior
            ):
                continue
            if _alternate(case, credits, start, periods, prior):
                return True
    return False


@lru_cache(maxsize=16384)
def _public_rows(case):
    """Keep the public observation for direct metamorphic lattice checks."""
    try:
        return (
            rule.evaluate_insured_status(
                "classification-oracle",
                WEIGHT,
                lambda: rule.insured_status(
                    case.person,
                    _history(case),
                    case.month,
                    test=rule.InsuredTest.FULLY,
                    coverage_end_month=case.exit_month,
                ),
            ),
        )
    except rule.InvalidFamilyInput:
        return ()


def _check_classification(case):
    possible = _has_valid_filling(case)
    rows = _public_rows(case)
    if not rows:
        assert not possible, f"oracle found a concrete filling: {case!r}"
    else:
        assert possible, f"oracle found no valid filling: {case!r}"
        row = rows[0]
        assert (row.result is None) != (row.unsupported is None)
        if row.unsupported is not None:
            assert isinstance(
                row.unsupported.reason, rule.InsuredUnsupportedReason
            )
    counts = count_family_outcomes(rows)
    assert counts.rows == int(possible)
    assert counts.weight == WEIGHT * int(possible)
    assert counts.unsupported_rows == sum(
        row.unsupported is not None for row in rows
    )
    assert counts.unsupported_weight == WEIGHT * counts.unsupported_rows


def _counts(total, first):
    answer = []
    while total:
        amount = min(total, 4)
        answer.append((first, amount))
        total -= amount
        first += 1
    return tuple(answer)


def _modern_case(age, total, placement, flags, blind, prior, established=True):
    onset_year = 2022
    birth = date(onset_year - age, 2, 2)
    first = 2016 if placement == "recent" else max(birth.year, 1978)
    periods = ()
    if prior in ("one", "two", "special"):
        periods = (
            rule.DisabilityPeriod(
                date(2010, 1, 1),
                date(2012, 12, 31),
                special_insured=prior == "special",
            ),
        )
        if prior == "two":
            periods += (
                rule.DisabilityPeriod(date(2014, 1, 1), date(2014, 12, 31)),
            )
    return _declaration(
        birth=birth,
        onset=date(2022, 1, 15),
        end=date(2022, 12, 31),
        month=date(2023, 1, 1),
        flags=flags,
        blind=blind,
        established=established,
        periods=periods,
        prior_unknown=prior == "unknown",
        counts=_counts(total, first),
    )


@pytest.mark.parametrize("flags", FLAG_SETS)
def test_classification_oracle_modern_lattice(flags):
    # 11 * 4 * 6 * 2 * 2 * 3 = 3,168 declarations. UNKNOWN priors use
    # the focused completion lattice below, avoiding redundant scans.
    for age, total, placement, blind, established in product(
        (24, 29, 42, 60),
        (0, 5, 6, 19, 20, 24),
        ("old", "recent"),
        (False, True),
        (False, True, None),
    ):
        _check_classification(
            _modern_case(
                age, total, placement, flags, blind, "none", established
            )
        )


def test_classification_oracle_modern_lattice_fully_flags_only_relax():
    """Every modern unflagged row survives each of the four fully flags."""
    for age, total, placement, blind, established in product(
        (24, 29, 42, 60),
        (0, 5, 6, 19, 20, 24),
        ("old", "recent"),
        (False, True),
        (False, True, None),
    ):
        case = _modern_case(
            age, total, placement, (), blind, "none", established
        )
        if _public_rows(case):
            for flag in FULLY_FLAGS:
                assert _public_rows(
                    replace(
                        case,
                        person=replace(
                            case.person, conditions=frozenset((flag,))
                        ),
                    )
                ), (case, flag)


@pytest.mark.parametrize("flags", FLAG_SETS)
def test_classification_oracle_prior_and_unknown_completions(flags):
    for prior, total in product(
        ("one", "two", "special", "unknown"), (0, 5, 6, 20)
    ):
        _check_classification(
            _modern_case(42, total, "recent", flags, False, prior)
        )
    for total, unknown_at in product((0, 5, 6, 19, 20), (2021, 2023)):
        case = _modern_case(42, total, "recent", flags, False, "none")
        case = replace(
            case,
            annual=tuple(
                (year, None, None) if year == unknown_at else row
                for row in case.annual
                for year in (row[0],)
            ),
        )
        _check_classification(case)


@pytest.mark.parametrize("flags", FLAG_SETS)
def test_classification_oracle_historical_boundary_lattice(flags):
    for birth_year, onset_year, total, prior_end in product(
        (1890, 1900, 1910),
        (1952, 1955, 1956),
        (19, 20),
        (None, (1955, 9, 30), (1955, 11, 30)),
    ):
        if prior_end is not None and onset_year < 1955:
            continue
        onset = date(onset_year, 12, 15)
        if prior_end is not None and date(*prior_end) >= onset:
            continue
        # The 1890 cohort is past FRA by late 1955: it belongs on the
        # absent/UNKNOWN side of the declaration boundary, not a malformed
        # Person constructor on the established side.
        established = onset < _fra(date(birth_year, 2, 2)).replace(day=1)
        periods = (
            (rule.DisabilityPeriod(date(1952, 7, 1), date(*prior_end)),)
            if prior_end is not None
            else ()
        )
        fixed = (
            *range(1938 * 4, 1938 * 4 + total - 6),
            *range(1951 * 4, 1952 * 4 + 2),
        )
        _check_classification(
            _declaration(
                birth=date(birth_year, 2, 2),
                onset=onset,
                end=date(onset_year + 1, 3, 31),
                month=date(1968, 1, 1),
                flags=flags,
                established=established,
                periods=periods,
                fixed=fixed,
            )
        )


@pytest.mark.parametrize("flags", FLAG_SETS)
def test_classification_oracle_dated_bounds(flags):
    for end_month, through_month, death_month, exit_month in (
        (2, None, None, None),
        (3, None, None, None),
        (4, None, None, None),
        (None, None, None, None),
        (None, 2, None, None),
        (None, 4, None, None),
        (None, None, 2, None),
        (None, None, 4, None),
        (None, None, None, date(2021, 12, 1)),
    ):
        for total in (5, 6, 19, 20):
            _check_classification(
                _declaration(
                    birth=date(1980, 2, 2),
                    onset=date(2022, 1, 15),
                    end=(
                        _month_end(date(2022, end_month, 1))
                        if end_month
                        else None
                    ),
                    month=date(2022, 7, 1),
                    through=(
                        date(2022, through_month, 15)
                        if through_month
                        else None
                    ),
                    death=(
                        date(2022, death_month, 20) if death_month else None
                    ),
                    exit_month=exit_month,
                    flags=flags,
                    counts=_counts(total, 2017),
                )
            )


def _property_case(
    scenario, age, total, blind, flag, prior, phase, established
):
    flags = FLAG_SETS[flag]
    if scenario == "modern":
        return _modern_case(
            age,
            total,
            "recent" if phase % 2 else "old",
            flags,
            blind,
            prior,
            established,
        )
    if scenario == "historical":
        birth = date((1890, 1900, 1910)[phase % 3], 2, 2)
        onset = date((1952, 1955, 1956)[(age + phase) % 3], 12, 15)
        periods = ()
        if phase % 2 and onset.year >= 1955:
            periods = (
                rule.DisabilityPeriod(date(1952, 7, 1), date(1955, 11, 30)),
            )
        number = 20 if blind else 19
        return _declaration(
            birth=birth,
            onset=onset,
            end=date(onset.year + 1, 3, 31),
            month=date(1968, 1, 1),
            flags=flags,
            established=onset < _fra(birth).replace(day=1),
            periods=periods,
            fixed=(
                *range(1938 * 4, 1938 * 4 + number - 6),
                *range(1951 * 4, 1952 * 4 + 2),
            ),
        )
    if scenario == "dated":
        end, through, death, exit_month = (
            (date(2022, 2, 28), None, None, None),
            (date(2022, 3, 31), None, None, None),
            (date(2022, 4, 30), None, None, None),
            (None, None, None, None),
            (None, date(2022, 2, 15), None, None),
            (None, date(2022, 4, 15), None, None),
            (None, None, date(2022, 2, 20), None),
            (None, None, date(2022, 4, 20), None),
            (None, None, None, date(2021, 12, 1)),
        )[phase]
        return _declaration(
            birth=date(1980, 2, 2),
            onset=date(2022, 1, 15),
            end=end,
            month=date(2022, 7, 1),
            flags=flags,
            through=through,
            death=death,
            exit_month=exit_month,
            counts=_counts((5, 6, 19, 20)[phase % 4], 2017),
        )
    if scenario == "annual":
        return _declaration(
            onset=date(2000, 2, 15),
            end=date(2000, 2, 29) if phase % 2 else date(2000, 12, 31),
            flags=flags,
            periods=(
                rule.DisabilityPeriod(
                    date(1999, 1, 1),
                    date(2000, 1, 31) if blind else date(1999, 12, 31),
                ),
            ),
            counts=(
                (1995, 4),
                (1996, 4),
                (1997, 4),
                (1998, 4),
                (1999, 3),
                (2000, (0, 1, 4)[phase % 3]),
            ),
        )
    if scenario == "unknown-years":
        return _declaration(
            birth=date(1999, 2, 2),
            onset=date(2022, 1, 15),
            end=date(2022, 12, 31),
            month=date(2023, 1, 1),
            flags=flags,
            counts=((2020, 1 + phase % 2),),
            unknown_years=(2021, 2023),
        )
    assert scenario == "special"
    periods = (
        ()
        if phase % 2
        else (
            rule.DisabilityPeriod(
                date(2012, 4, 1), date(2021, 12, 31), special_insured=True
            ),
        )
    )
    return _declaration(
        birth=date(1990, 2, 2),
        onset=date(2022, 1, 15),
        end=date(2022, 12, 31),
        month=date(2023, 1, 1),
        flags=flags,
        periods=periods,
        prior_unknown=bool(phase % 2),
        counts=_counts(5 + int(blind), 2011),
    )


@settings(max_examples=48, deadline=None, derandomize=True)
@example(
    scenario="modern",
    age=42,
    total=0,
    blind=False,
    flag=0,
    prior="unknown",
    phase=1,
    established=True,
)
@given(
    scenario=st.sampled_from(
        ("modern", "historical", "dated", "annual", "unknown-years", "special")
    ),
    age=st.sampled_from((24, 29, 42, 60)),
    total=st.sampled_from((0, 5, 6, 19, 20, 24)),
    blind=st.booleans(),
    flag=st.integers(0, len(FLAG_SETS) - 1),
    prior=st.sampled_from(("none", "unknown")),
    phase=st.integers(0, 8),
    established=st.sampled_from((False, True, None)),
)
def test_classification_oracle_hypothesis(
    scenario,
    age,
    total,
    blind,
    flag,
    prior,
    phase,
    established,
):
    _check_classification(
        _property_case(
            scenario, age, total, blind, flag, prior, phase, established
        )
    )


def test_classification_oracle_requires_ordinary_recent_route():
    """A fully flag supplies no QCs but can make a 20/40 filling valid."""
    _check_classification(
        _declaration(
            birth=date(1940, 2, 2),
            flags=(FULLY_FLAGS[0],),
            counts=_counts(20, 1995),
        )
    )


def test_classification_oracle_requires_alternate_route():
    """Twenty lifetime QCs and the six-quarter clock need the alternate."""
    _check_classification(
        _declaration(
            birth=date(1900, 2, 2),
            onset=date(1952, 7, 15),
            end=date(1953, 12, 31),
            month=date(1968, 1, 1),
            flags=(FULLY_FLAGS[0],),
            fixed=(
                *range(1938 * 4, 1941 * 4 + 2),
                *range(1951 * 4, 1952 * 4 + 2),
            ),
        )
    )


def test_classification_oracle_unknown_prior_must_jointly_insure_current():
    """Earliest insured prior has a credited endpoint, leaving 14 quarters.

    Six QCs first exist in 2017Q2. Under31 insurance can establish a first
    prior then, but using every remaining prior quarter through 2021Q4
    still leaves fourteen elapsed quarters at the earliest current start.
    Seven QCs are needed. An additional prior cannot precede that first
    insured start or remove its credited endpoint or any current quarter;
    no multi-period completion can improve the bound.
    """
    case = _modern_case(29, 6, "recent", (), False, "unknown")
    assert not _has_valid_filling(case)
    _check_classification(case)


@pytest.mark.parametrize("flag", FULLY_FLAGS)
def test_classification_oracle_unknown_prior_cannot_invent_special_eligibility(
    flag,
):
    """The first QCs are after age31; no special prior can exist."""
    case = _modern_case(42, 6, "recent", (flag,), False, "unknown")
    assert not _has_valid_filling(case)
    _check_classification(case)


@pytest.mark.parametrize("flags", FLAG_SETS)
def test_classification_oracle_onset_quarter_and_credited_endpoint(flags):
    for prior_end, credit_quarter, total in product(
        (date(1961, 12, 31), date(1962, 1, 31)),
        (1962 * 4, 1962 * 4 + 1, 1962 * 4 + 2),
        (5, 6, 19, 20),
    ):
        # A credited prior endpoint remains in the window, while an
        # established current start still cannot occupy that quarter.
        fixed = (*range(1957 * 4, 1957 * 4 + total - 1), credit_quarter)
        _check_classification(
            _declaration(
                birth=date(1910, 2, 2),
                onset=date(1962, 2, 15),
                end=date(1962, 8, 31),
                month=date(1968, 1, 1),
                flags=flags,
                fixed=fixed,
                periods=(rule.DisabilityPeriod(date(1960, 1, 1), prior_end),),
            )
        )


@pytest.mark.parametrize("flags", FLAG_SETS)
def test_classification_oracle_six_qc_special_completions(flags):
    for prior_unknown, total in product((False, True), (5, 6)):
        prior = (
            ()
            if prior_unknown
            else (
                rule.DisabilityPeriod(
                    date(2012, 4, 1), date(2021, 12, 31), special_insured=True
                ),
            )
        )
        _check_classification(
            _declaration(
                birth=date(1990, 2, 2),
                onset=date(2022, 1, 15),
                end=date(2022, 12, 31),
                month=date(2023, 1, 1),
                flags=flags,
                periods=prior,
                prior_unknown=prior_unknown,
                counts=_counts(total, 2011),
            )
        )
    _check_classification(
        _declaration(
            birth=date(1999, 2, 2),
            onset=date(2022, 1, 15),
            end=date(2022, 12, 31),
            month=date(2023, 1, 1),
            flags=flags,
            counts=_counts(6, 2020),
        )
    )


@pytest.mark.parametrize("flags", FLAG_SETS)
def test_classification_oracle_unknown_years_straddle_start_horizon(flags):
    for known in (1, 2):
        _check_classification(
            _declaration(
                birth=date(1999, 2, 2),
                onset=date(2022, 1, 15),
                end=date(2022, 12, 31),
                month=date(2023, 1, 1),
                flags=flags,
                counts=((2020, known),),
                unknown_years=(2021, 2023),
            )
        )


@pytest.mark.parametrize("flag", FULLY_FLAGS)
def test_classification_oracle_historical_blindness_can_supply_two_priors(
    flag,
):
    case = _modern_case(29, 6, "recent", (flag,), False, "unknown")
    assert _has_valid_filling(case)
    _check_classification(case)


def test_classification_oracle_unknown_twenty_qcs_need_one_joint_start():
    case = _declaration(
        birth=date(1931, 2, 2),
        onset=date(1972, 4, 15),
        end=date(1972, 12, 31),
        month=date(1973, 1, 1),
        prior_unknown=True,
        fixed=(1962 * 4, *range(1967 * 4 + 1, 1972 * 4)),
    )
    assert not _has_valid_filling(case)
    _check_classification(case)


@pytest.mark.parametrize("flag", FULLY_FLAGS)
@pytest.mark.parametrize("total", (0, 5))
def test_classification_oracle_unknown_history_cannot_remove_six_qc_floor(
    flag, total
):
    case = _modern_case(42, total, "recent", (flag,), False, "unknown")
    assert not _has_valid_filling(case)
    _check_classification(case)


def test_classification_oracle_alternate_needs_clear_start_before_1956():
    case = _declaration(
        birth=date(1900, 2, 2),
        onset=date(1955, 12, 15),
        end=date(1956, 3, 31),
        month=date(1968, 1, 1),
        periods=(rule.DisabilityPeriod(date(1952, 7, 1), date(1955, 11, 30)),),
        fixed=(*range(1938 * 4, 1941 * 4 + 2), *range(1951 * 4, 1952 * 4 + 2)),
    )
    assert not _has_valid_filling(case)
    _check_classification(case)


@pytest.mark.parametrize("flag", FULLY_FLAGS)
def test_classification_oracle_fully_flag_cannot_delay_an_insured_onset(flag):
    case = _declaration(
        birth=date(1910, 2, 2),
        onset=date(1962, 2, 15),
        end=date(1962, 8, 31),
        month=date(1968, 1, 1),
        flags=(flag,),
        periods=(rule.DisabilityPeriod(date(1960, 1, 1), date(1962, 1, 31)),),
        fixed=(*range(1957 * 4, 1961 * 4 + 3), 1962 * 4),
    )
    assert not _has_valid_filling(case)
    _check_classification(case)


@pytest.mark.parametrize("flag", FULLY_FLAGS)
def test_classification_oracle_blind_fully_flag_still_has_one_first_start(
    flag,
):
    case = _declaration(
        birth=date(1960, 2, 2),
        flags=(flag,),
        blind=True,
        periods=(rule.DisabilityPeriod(date(1999, 1, 1), date(2000, 1, 14)),),
    )
    assert _has_valid_filling(case)
    _check_classification(case)
    row = rule.evaluate_insured_status(
        "free-flag-start",
        WEIGHT,
        lambda: rule.insured_status(
            case.person,
            _history(case),
            case.month,
            test=rule.InsuredTest.FULLY,
        ),
    )
    assert row.unsupported.reason is getattr(
        rule.InsuredUnsupportedReason, flag.name
    )
    assert count_family_outcomes((row,)).weight == WEIGHT


@pytest.mark.parametrize("flag", FULLY_FLAGS)
def test_classification_oracle_blind_ordinary_onset_cannot_be_delayed(flag):
    """Ordinary fully insurance fixes this overlapping start for every f."""
    case = _declaration(
        birth=date(1960, 2, 2),
        flags=(flag,),
        blind=True,
        periods=(rule.DisabilityPeriod(date(1999, 1, 1), date(2000, 1, 14)),),
        counts=tuple((year, 4) for year in range(1980, 1990)),
    )
    assert not _has_valid_filling(case)
    with pytest.raises(rule.InvalidFamilyInput):
        rule.insured_status(case.person, _history(case), case.month)
    _check_classification(case)


@pytest.mark.parametrize("two_priors", (False, True))
def test_classification_oracle_no_flag_historical_blind_prior(two_priors):
    """A blind start with six ordinary QCs can precede a special prior."""
    year = 1995 if two_priors else 1976
    case = _declaration(
        birth=date(1951, 2, 2),
        onset=date(year, 1, 15),
        end=date(year, 12, 31),
        month=date(year + 1, 1, 1),
        prior_unknown=True,
        fixed=(
            1970 * 4 + 1,
            1972 * 4 + 1,
            1972 * 4 + 2,
            1972 * 4 + 3,
            1973 * 4,
            1973 * 4 + 1,
            1976 * 4,
        ),
    )
    assert _has_valid_filling(case)
    _check_classification(case)


@pytest.mark.parametrize("flag", FULLY_FLAGS)
def test_classification_oracle_free_flag_start_preserves_disregard(flag):
    """A recent-only overlapping quarter is not an insured first start."""
    case = _declaration(
        birth=date(1924, 1, 2),
        onset=date(1985, 2, 15),
        end=date(1985, 12, 31),
        month=date(1985, 12, 1),
        flags=(flag,),
        periods=(rule.DisabilityPeriod(date(1979, 1, 1), date(1985, 1, 31)),),
        fixed=(
            *range(1951 * 4, 1954 * 4 + 1),
            *range(1975 * 4 + 1, 1978 * 4),
        ),
        counts=((1978, 4), (1984, 4), (1985, 4)),
    )
    assert _has_valid_filling(case)
    _check_classification(case)


def test_classification_oracle_annual_placement_can_delay_first_insured_quarter():
    case = _declaration(
        onset=date(2000, 2, 15),
        periods=(rule.DisabilityPeriod(date(1999, 1, 1), date(2000, 1, 31)),),
        counts=(
            (1995, 4),
            (1996, 4),
            (1997, 4),
            (1998, 4),
            (1999, 3),
            (2000, 1),
        ),
    )
    assert _has_valid_filling(case)
    _check_classification(case)


@pytest.mark.parametrize("flags", FLAG_SETS)
def test_classification_oracle_annual_placement_boundary_lattice(flags):
    for onset_count, prior_end, end in product(
        (0, 1, 4),
        (date(1999, 12, 31), date(2000, 1, 31)),
        (date(2000, 2, 29), date(2000, 12, 31)),
    ):
        _check_classification(
            _declaration(
                onset=date(2000, 2, 15),
                end=end,
                flags=flags,
                periods=(rule.DisabilityPeriod(date(1999, 1, 1), prior_end),),
                counts=(
                    (1995, 4),
                    (1996, 4),
                    (1997, 4),
                    (1998, 4),
                    (1999, 3),
                    (2000, onset_count),
                ),
            )
        )


@pytest.mark.parametrize("boundary", ("age31", "1952-start"))
@pytest.mark.parametrize("after", (False, True))
def test_classification_oracle_adjacent_calendar_boundaries(boundary, after):
    if boundary == "age31":
        # RS00301.140 A: eligibility closes in the quarter attaining age 31.
        # The known nonspecial prior preserves six QCs without opening
        # the subsequent-special route on the other side of that line.
        case = _declaration(
            birth=date(1991, 2, 2),
            onset=date(2022, 1, 15) if after else date(2021, 10, 15),
            end=date(2022, 12, 31),
            month=date(2023, 1, 1),
            periods=(
                rule.DisabilityPeriod(date(2013, 7, 1), date(2021, 9, 30)),
            ),
            counts=((2012, 4), (2013, 2)),
        )
        expected = not after
    else:
        # RS00301.480 B.1 opens the alternate in 1952Q3. These historical
        # endings imply recovery in Q2 versus Q3 under 404.321(b).
        case = _declaration(
            birth=date(1900, 2, 2),
            onset=date(1952, 4, 15),
            end=date(1952, 9, 30) if after else date(1952, 6, 30),
            month=date(1968, 1, 1),
            fixed=(
                *range(1938 * 4, 1941 * 4 + 2),
                *range(1951 * 4, 1952 * 4 + 2),
            ),
        )
        expected = after
    assert _has_valid_filling(case) is expected
    _check_classification(case)
