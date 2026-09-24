"""Statutory benefit computation years and AIME (42 USC 415(b)).

Python oracle (transitional, not Axiom).  :func:`populace_dynamics.ss.
benefits.aime` averages every worker's highest 35 indexed years over 420
months.  42 USC 415(b)(2) instead makes the number of benefit computation
years depend on the worker's elapsed years.  For anyone born 1929 or later
who is alive at 62, the two agree: 40 elapsed years less 5 is 35.  For
people born before 1929 the statute gives fewer than 35 years, and the
Track C step 1 comparison (the Axiom 415(b) candidate against this oracle
on the Track A cohort, 2026-09-23) traced all 251 of its disagreements to
that count.  This module computes the statutory count and the AIME that
uses it.  ``ss/__init__.py`` asks that the oracle's rule coverage not be
extended; this module corrects the old-age count the oracle already
computes, and adds the death and disability counts only as functions of
dates the caller supplies (no production path passes them yet).

Statute text.  Quoted from 42 USC 415(b) as the Axiom corpus holds it
(uscode.house.gov release point 119-100, expression date 2026-06-26, text
SHA-256
``5b41d1cdacd39f4c49da7cf41dbbf22e1ea29b125be7105ca2daa12292e06eae``;
a copy is the encoder workspace ``source.txt`` under
``microcosm-launch-evidence/dynasim-parity-20260909/parallel-oasdi-20260920/
encoder-recovery/``).  The builder-visible excerpt file of the COLA work
(``tr2008-inputs-20260922/usc-42-415-excerpts.txt``) holds 415(a)(3)(B)
and 415(i) only, not 415(b).

415(b)(1)::

    An individual’s average indexed monthly earnings shall be equal to the
    quotient obtained by dividing— (A) the total (after adjustment under
    paragraph (3)) of his wages paid in and self-employment income credited
    to his benefit computation years (determined under paragraph (2)), by
    (B) the number of months in those years.

415(b)(2)(A), first sentence::

    The number of an individual’s benefit computation years equals the
    number of elapsed years reduced— (i) in the case of an individual who
    is entitled to old-age insurance benefits (except as provided in the
    second sentence of this subparagraph), or who has died, by 5 years, and
    (ii) in the case of an individual who is entitled to disability
    insurance benefits, by the number of years equal to one-fifth of such
    individual’s elapsed years (disregarding any resulting fractional part
    of a year), but not by more than 5 years.

415(b)(2)(A), last sentence::

    The number of an individual’s benefit computation years as determined
    under this subparagraph shall in no case be less than 2.

415(b)(2)(B)(i)::

    the term “benefit computation years” means those computation base
    years, equal in number to the number determined under subparagraph (A),
    for which the total of such individual’s wages and self-employment
    income, after adjustment under paragraph (3), is the largest;

415(b)(2)(B)(iii)::

    the term “number of elapsed years” means (except as otherwise provided
    by section 104(j)(2) of the Social Security Amendments of 1972) the
    number of calendar years after 1950 (or, if later, the year in which
    the individual attained age 21) and before the year in which the
    individual died, or, if it occurred earlier (but after 1960), the year
    in which he attained age 62; except that such term excludes any
    calendar year any part of which is included in a period of disability.

415(b)(3)(A)(ii)(I), the indexing year::

    the national average wage index (as defined in section 409(k)(1) of
    this title ) for the second calendar year preceding the earliest of the
    year of the individual’s death, eligibility for an old-age insurance
    benefit, or eligibility for a disability insurance benefit

415(a)(3)(B) (in the excerpt file) deems eligibility for old-age benefits
to begin with the month of attaining 62 and for disability benefits with
the month the period of disability began.

Section 104(j)(2) of the Social Security Amendments of 1972 (Pub. L.
92-603, 86 Stat. 1341), from the statutory note "Effective Date of 1972
Amendment" under 42 USC 414 (law.cornell.edu/uscode/text/42/414, read
2026-09-24, page SHA-256
``731e1dbc8648c689d2d97546980739a1a53477da0669d566d3d32ec9f3966a2d``;
bracketed text is the note's)::

    In the case of a man who attains age 62 prior to 1975, the number of
    his elapsed years for purposes of section 215(b)(3) of the Social
    Security Act [42 U.S.C. 415(b)(3)] shall be equal to (A) the number
    determined under such section as in effect on September 1, 1972, or
    (B) if less, the number determined as though he attained age 65 in
    1975, [...]

The oracle has no sex input and does not encode the 1972 law, so it
refuses anyone who attains 62 before 1975.  That also makes the "(but
after 1960)" condition always hold.  Quotations keep the sources'
characters; only line breaks were added.

What is encoded:

* the elapsed years of 415(b)(2)(B)(iii), for a worker alive at 62, a
  worker who died (``death_year``), or a worker with one period of
  disability that began in ``disability_year`` and runs through the end
  of the elapsed-year window;
* the 415(b)(2)(A) reduction: 5 years for old-age entitlement or death,
  one-fifth of the elapsed years (at most 5) for disability entitlement,
  and the 2-year minimum;
* the 415(b)(3)(A) indexing year (the second year before the earliest of
  death, attaining 62 and the start of the period of disability), with
  later years entering unindexed through the existing
  :func:`~populace_dynamics.ss.benefits.indexed_history`.

What is not encoded (each is a documented limitation, not an
approximation this module applies silently):

* the child-care dropout years of 415(b)(2)(A)'s third sentence (a
  disabled worker living with a child under 3, up to a combined reduction
  of 3): for such a worker the returned count can be too high and the AIME
  too low;
* the second sentence of 415(b)(2)(A) (clause (ii) continuing into later
  old-age eligibility unless 12 months pass without entitlement): a caller
  whose old-age benefit follows a disability entitlement passes the
  ``disability_year`` itself;
* periods of disability that ended, more than one period, and the
  12-month rule of 415(a)(3)(B); a death after a disability entitlement is
  refused;
* 104(j)(2) of the 1972 amendments and the 1960 condition (see above);
* the choice of computation base years (415(b)(2)(B)(ii)): like
  ``benefits.aime``, the AIME ranks every year the caller supplies, and
  the caller applies the entitlement or death cutoff.  Years before 1951
  are refused because they cannot be computation base years.

The legacy convention.  ``ss/benefits.py`` is not edited.  It sits inside
the source identity the first-estimates birth-evidence reducer seals
(``scripts/first_estimates_birth_evidence.py``: every file under
``src/populace_dynamics`` outside ``POST_REVIEW_SOURCE_EXCLUSIONS`` must
equal reviewed commit ``1c7f3540``), and two sealed callers use it: the
first-estimates ledger (``estimates/ledgers.py``, ``runs/first_estimates_
v1.json``) and the gate-2c couple-earnings AIME proxy
(``data/couple_earnings.py``).  ``benefits.aime`` therefore stays what it
was, and this module names it :attr:`ComputationYears.LEGACY_FIXED_35`.
Callers pick a convention explicitly through :func:`oracle_aime`; the
legacy one is for code paths whose committed artifacts were computed with
it (``tests/ss/test_statutory_aime.py`` pins where it is used).
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from enum import Enum

from populace_dynamics.ss import benefits
from populace_dynamics.ss.params import SSAParameters

__all__ = [
    "ComputationYears",
    "LEGACY_FIXED_COMPUTATION_YEARS",
    "elapsed_years",
    "benefit_computation_years",
    "indexing_year",
    "aime_with_computation_years",
    "aime",
    "oracle_aime",
]

#: The fixed divisor years of ``ss.benefits.aime`` (the legacy convention).
LEGACY_FIXED_COMPUTATION_YEARS = 35
#: 415(b)(2)(B)(iii): elapsed years are the calendar years after 1950 ...
ELAPSED_YEARS_AFTER = 1950
#: ... or, if later, after the year of attaining 21 ...
ELAPSED_START_AGE = 21
#: ... and before the year of attaining 62 (or of death, if earlier).
ELIGIBILITY_AGE = 62
#: 415(b)(2)(A)(i): the reduction for old-age entitlement or death.
OLD_AGE_OR_DEATH_REDUCTION = 5
#: 415(b)(2)(A)(ii): one-fifth of the elapsed years, at most 5.
DISABILITY_REDUCTION_DIVISOR = 5
DISABILITY_REDUCTION_MAXIMUM = 5
#: 415(b)(2)(A): "shall in no case be less than 2".
MINIMUM_COMPUTATION_YEARS = 2
#: 104(j)(2) of the 1972 amendments governs men attaining 62 before 1975.
FIRST_AGE_62_YEAR_ENCODED = 1975
#: 415(b)(3)(A)(ii)(I): the second calendar year preceding.
INDEXING_LAG_YEARS = 2
#: ``benefits.indexed_history`` indexes to its birth-year argument + 60.
_BENEFITS_INDEXING_AGE = 60
_MONTHS = 12


class ComputationYears(str, Enum):
    """How an oracle AIME counts its benefit computation years.

    ``STATUTORY``: 42 USC 415(b)(2), through :func:`aime`.
    ``LEGACY_FIXED_35``: always 35, the unchanged
    :func:`populace_dynamics.ss.benefits.aime`; kept only for code paths
    whose committed artifacts were computed with it.
    """

    STATUTORY = "statutory_415_b_2"
    LEGACY_FIXED_35 = "legacy_fixed_35"


def _year(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an integer year, not {value!r}.")
    return int(value)


def _optional_year(value: object, label: str) -> int | None:
    return None if value is None else _year(value, label)


def _checked_dates(
    birth_year: object, death_year: object, disability_year: object
) -> tuple[int, int | None, int | None]:
    birth = _year(birth_year, "birth_year")
    death = _optional_year(death_year, "death_year")
    onset = _optional_year(disability_year, "disability_year")
    if birth + ELIGIBILITY_AGE < FIRST_AGE_62_YEAR_ENCODED:
        raise ValueError(
            f"Born {birth}: attains 62 before {FIRST_AGE_62_YEAR_ENCODED}. "
            "Section 104(j)(2) of the Social Security Amendments of 1972 "
            "sets a man's elapsed years then, and the oracle has no sex "
            "input and does not encode the 1972 law."
        )
    if death is not None and death < birth:
        raise ValueError(f"death_year {death} precedes birth_year {birth}.")
    if onset is not None and onset < birth:
        raise ValueError(
            f"disability_year {onset} precedes birth_year {birth}."
        )
    if death is not None and onset is not None:
        raise ValueError(
            "A death after a disability entitlement is not encoded: "
            "415(b)(2)(A) reduces for death by 5 years (clause (i)) and "
            "continues clause (ii) only into later disability or old-age "
            "eligibility; the oracle does not settle that case."
        )
    return birth, death, onset


def elapsed_years(
    birth_year: int,
    *,
    death_year: int | None = None,
    disability_year: int | None = None,
) -> int:
    """Number of elapsed years, 42 USC 415(b)(2)(B)(iii).

    The calendar years after the later of 1950 and the year of attaining
    21, and before the earlier of the year of death (``death_year``, if
    given) and the year of attaining 62.  ``disability_year`` is the
    calendar year in which the worker's period of disability began; that
    year and every later year are excluded (any part of each is in the
    period, which is taken to run through the end of the window).
    Never negative.
    """

    birth, death, onset = _checked_dates(
        birth_year, death_year, disability_year
    )
    after = max(ELAPSED_YEARS_AFTER, birth + ELAPSED_START_AGE)
    before = birth + ELIGIBILITY_AGE
    if death is not None:
        before = min(before, death)
    if onset is not None:
        before = min(before, onset)
    return max(0, before - after - 1)


def benefit_computation_years(
    birth_year: int,
    *,
    death_year: int | None = None,
    disability_year: int | None = None,
) -> int:
    """Number of benefit computation years, 42 USC 415(b)(2)(A).

    With neither date, the worker is taken to be entitled to old-age
    benefits and alive at 62; with ``death_year``, to have died; with
    ``disability_year``, to be entitled to disability benefits (clause
    (ii), which also carries into a later old-age benefit).  Elapsed years
    less 5 (clause (i)) or less one-fifth of them, at most 5 (clause
    (ii)), and never fewer than 2.  The child-care dropout years of the
    third sentence are not encoded.
    """

    elapsed = elapsed_years(
        birth_year, death_year=death_year, disability_year=disability_year
    )
    if disability_year is None:
        reduction = OLD_AGE_OR_DEATH_REDUCTION
    else:
        reduction = min(
            DISABILITY_REDUCTION_MAXIMUM,
            elapsed // DISABILITY_REDUCTION_DIVISOR,
        )
    return max(MINIMUM_COMPUTATION_YEARS, elapsed - reduction)


def indexing_year(
    birth_year: int,
    *,
    death_year: int | None = None,
    disability_year: int | None = None,
) -> int:
    """The wage-indexing year, 42 USC 415(b)(3)(A)(ii)(I).

    The second calendar year before the earliest of the year of death,
    the year of attaining 62 (old-age eligibility, 415(a)(3)(B)(i)) and
    the year the period of disability began (disability eligibility,
    415(a)(3)(B)(ii)).  With neither date it is the year of attaining 60,
    the year :func:`populace_dynamics.ss.benefits.aime` indexes to.
    """

    birth, death, onset = _checked_dates(
        birth_year, death_year, disability_year
    )
    earliest = birth + ELIGIBILITY_AGE
    for year in (death, onset):
        if year is not None:
            earliest = min(earliest, year)
    return earliest - INDEXING_LAG_YEARS


def aime_with_computation_years(
    history: Mapping[int, float],
    computation_years: int,
    params: SSAParameters,
    *,
    indexing_year: int,
) -> int:
    """The AIME arithmetic of ``benefits.aime`` with any year count.

    Earnings limited to the contribution and benefit base
    (``benefits.creditable_history``), indexed to ``indexing_year`` with
    later years unindexed (``benefits.indexed_history``), the highest
    ``computation_years`` values (years absent from ``history`` count as
    zero), summed in the same order and floored over
    ``12 * computation_years`` months.  With 35 years and the year of
    attaining 60 it is ``benefits.aime`` operation for operation.
    """

    count = _year(computation_years, "computation_years")
    if count < 1:
        raise ValueError(f"computation_years must be positive, not {count}.")
    index = _year(indexing_year, "indexing_year")
    early = sorted(year for year in history if int(year) <= 1950)
    if early:
        raise ValueError(
            f"Years {early} precede 1951 and cannot be computation base "
            "years (42 USC 415(b)(2)(B)(ii))."
        )
    creditable = benefits.creditable_history(dict(history), params)
    indexed = benefits.indexed_history(
        creditable, index - _BENEFITS_INDEXING_AGE, params
    )
    top = sorted(indexed.values(), reverse=True)[:count]
    top += [0.0] * (count - len(top))
    return math.floor(sum(top) / (count * _MONTHS))


def aime(
    history: Mapping[int, float],
    birth_year: int,
    params: SSAParameters,
    *,
    death_year: int | None = None,
    disability_year: int | None = None,
) -> int:
    """Average indexed monthly earnings under 42 USC 415(b).

    The statutory number of benefit computation years
    (:func:`benefit_computation_years`) and indexing year
    (:func:`indexing_year`), then :func:`aime_with_computation_years`.
    For a worker born 1929 or later with neither date it equals
    ``benefits.aime(history, birth_year, params)`` exactly.
    ``history`` must hold only the worker's computation base years; the
    caller applies the entitlement or death cutoff.
    """

    return aime_with_computation_years(
        history,
        benefit_computation_years(
            birth_year, death_year=death_year, disability_year=disability_year
        ),
        params,
        indexing_year=indexing_year(
            birth_year, death_year=death_year, disability_year=disability_year
        ),
    )


def oracle_aime(
    history: Mapping[int, float],
    birth_year: int,
    params: SSAParameters,
    *,
    computation_years: ComputationYears,
) -> int:
    """The old-age (age-62) oracle AIME under a named convention.

    ``STATUTORY`` is :func:`aime` for a worker alive at 62;
    ``LEGACY_FIXED_35`` is the unchanged ``benefits.aime``.
    """

    convention = ComputationYears(computation_years)
    if convention is ComputationYears.LEGACY_FIXED_35:
        return benefits.aime(dict(history), birth_year, params)
    return aime(history, birth_year, params)
