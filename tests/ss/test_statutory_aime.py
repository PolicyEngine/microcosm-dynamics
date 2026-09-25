"""Statutory benefit computation years and AIME (42 USC 415(b)(2)).

Every parameter bundle and earnings history here is INVENTED; the
expected values are computed by hand in the comments from the statute's
counting rules, not read back from the code under test.
"""

from __future__ import annotations

import ast
import math
import random
from pathlib import Path

import pytest

from populace_dynamics.ss import benefits
from populace_dynamics.ss import statutory_aime as sa
from populace_dynamics.ss.params import SSAParameters
from populace_dynamics.ss.statutory_aime import ComputationYears

ROOT = Path(__file__).resolve().parents[2]


def _flat_params(nawi_overrides: dict[int, float] | None = None):
    """INVENTED: a flat wage index (indexing is neutral) and no binding
    contribution and benefit base, so AIMEs are hand-computable."""
    nawi = {year: 10_000.0 for year in range(1951, 2071)}
    nawi.update(nawi_overrides or {})
    return SSAParameters(
        nawi=nawi,
        wage_base={1937: 1.0e12},
        pia_factors=(0.9, 0.32, 0.15),
        fra_months_by_birth_year=[(1900, 66 * 12)],
        early_monthly_rates=(5 / 900, 5 / 1200),
        early_first_bracket_months=36,
        pe_us_revision="INVENTED",
        delayed_credit_by_birth_year=[(1900, 0.08)],
    )


def _growth_params() -> SSAParameters:
    """INVENTED: 4 percent wage growth and a binding, rising base."""
    return SSAParameters(
        nawi={
            year: 2_800.0 * 1.04 ** (year - 1951) for year in range(1951, 2071)
        },
        wage_base={1937: 3_000.0, 1975: 14_100.0, 1990: 51_300.0},
        pia_factors=(0.9, 0.32, 0.15),
        fra_months_by_birth_year=[(1900, 792), (1955, 804)],
        early_monthly_rates=(5 / 900, 5 / 1200),
        early_first_bracket_months=36,
        pe_us_revision="INVENTED",
        delayed_credit_by_birth_year=[(1900, 0.08)],
    )


# ---------------------------------------------------------------------------
# Elapsed years and benefit computation years (hand counts)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("birth", "elapsed", "computation"),
    [
        # Attains 21 in 1941 and 62 in 1982: 1951-1981 elapsed.
        (1920, 31, 26),
        # Attains 21 in 1949 and 62 in 1990: 1951-1989 elapsed.
        (1928, 39, 34),
        # Attains 21 in 1950 and 62 in 1991: 1951-1990 elapsed.
        (1929, 40, 35),
        # Attains 21 in 1956 and 62 in 1997: 1957-1996 elapsed.
        (1935, 40, 35),
        # Attains 21 in 1934 and 62 in 1975: 1951-1974 elapsed.
        (1913, 24, 19),
        # Attains 21 in 1938 and 62 in 1979: 1951-1978 elapsed.
        (1917, 28, 23),
    ],
)
def test_old_age_counts_by_birth_year(birth, elapsed, computation):
    assert sa.elapsed_years(birth) == elapsed
    assert sa.benefit_computation_years(birth) == computation


@pytest.mark.parametrize("birth", [1929, 1940, 1960, 1975, 1990, 2005])
def test_attaining_21_after_1950_always_gives_40_elapsed_and_35_years(birth):
    # Years after the year of attaining 21 and before the year of attaining
    # 62: (birth + 22) through (birth + 61), 40 years; less 5 is 35.
    assert sa.elapsed_years(birth) == 40
    assert sa.benefit_computation_years(birth) == 35
    assert sa.benefit_computation_years(birth) == (
        sa.LEGACY_FIXED_COMPUTATION_YEARS
    )


def test_death_before_62_counts_to_the_year_before_death():
    # Born 1960 (attains 21 in 1981), died 2000: 1982-1999 elapsed = 18;
    # clause (i) "or who has died" reduces by 5 -> 13.
    assert sa.elapsed_years(1960, death_year=2000) == 18
    assert sa.benefit_computation_years(1960, death_year=2000) == 13
    # A death at or after 62 leaves the old-age count unchanged.
    for death in (2022, 2023, 2040):
        assert sa.benefit_computation_years(1960, death_year=death) == 35
    assert sa.benefit_computation_years(1920, death_year=1990) == 26


@pytest.mark.parametrize(
    ("death", "elapsed"),
    [
        (1985, 3),  # 1982-1984: 3 - 5 < 2 -> 2
        (1984, 2),  # 1982-1983
        (1982, 0),  # the year after attaining 21: no elapsed year
        (1981, 0),  # the year of attaining 21: never negative
        (1970, 0),
    ],
)
def test_two_year_minimum(death, elapsed):
    assert sa.elapsed_years(1960, death_year=death) == elapsed
    assert sa.benefit_computation_years(1960, death_year=death) == 2


@pytest.mark.parametrize(
    ("onset", "elapsed", "dropout", "computation"),
    [
        # Born 1960 (attains 21 in 1981).  The onset year and later are
        # excluded ("any part of which is included in a period of
        # disability").  Clause (ii): one-fifth of the elapsed years,
        # fraction disregarded, at most 5.
        (1983, 1, 0, 2),  # 1982: 1 - 0 = 1 -> minimum 2
        (1987, 5, 1, 4),  # 1982-1986
        (1990, 8, 1, 7),  # 1982-1989
        (2005, 23, 4, 19),  # 1982-2004
        (2015, 33, 5, 28),  # 1982-2014: 6 would exceed the cap of 5
        (2021, 39, 5, 34),  # 1982-2020
    ],
)
def test_disability_dropout_years(onset, elapsed, dropout, computation):
    assert sa.elapsed_years(1960, disability_year=onset) == elapsed
    assert elapsed - dropout == computation or computation == 2
    assert sa.benefit_computation_years(1960, disability_year=onset) == (
        computation
    )


def test_disability_after_62_keeps_the_age_62_window():
    # Born 1950 (attains 21 in 1971, 62 in 2012); a period of disability
    # beginning in 2014 excludes nothing before 2012: 1972-2011 = 40,
    # clause (ii) reduces by min(5, 8) = 5.
    assert sa.elapsed_years(1950, disability_year=2014) == 40
    assert sa.benefit_computation_years(1950, disability_year=2014) == 35


def test_indexing_year_is_the_second_year_before_the_earliest_event():
    assert sa.indexing_year(1960) == 2020  # attains 62 in 2022
    assert sa.indexing_year(1960, death_year=2000) == 1998
    assert sa.indexing_year(1960, death_year=2030) == 2020
    assert sa.indexing_year(1960, disability_year=2005) == 2003
    assert sa.indexing_year(1920) == 1980


# ---------------------------------------------------------------------------
# AIME (hand-computed on INVENTED flat parameters)
# ---------------------------------------------------------------------------
def test_aime_born_1920_divides_by_26_years():
    params = _flat_params()
    # 12,000 in each of 1968-1981 (14 years): total 168,000.
    history = {year: 12_000.0 for year in range(1968, 1982)}
    # Statutory: 168,000 / (26 * 12 = 312) = 538.46 -> 538.
    assert sa.aime(history, 1920, params) == 538
    # Legacy: 168,000 / 420 = 400.
    assert benefits.aime(history, 1920, params) == 400


def test_aime_born_1928_divides_by_34_years():
    params = _flat_params()
    # 12,000 in each of 1968-1989 (22 years): total 264,000.
    history = {year: 12_000.0 for year in range(1968, 1990)}
    # Statutory: 264,000 / 408 = 647.06 -> 647; legacy: / 420 = 628.57.
    assert sa.aime(history, 1928, params) == 647
    assert benefits.aime(history, 1928, params) == 628


def test_aime_born_1929_and_1935_is_unchanged():
    params = _flat_params()
    # 1929: 12,000 in 1968-1990 (23 years) = 276,000 / 420 = 657.14.
    history_1929 = {year: 12_000.0 for year in range(1968, 1991)}
    assert sa.aime(history_1929, 1929, params) == 657
    assert benefits.aime(history_1929, 1929, params) == 657
    # 1935: 20,000 in 1968-1996 (29 years) = 580,000 / 420 = 1380.95.
    history_1935 = {year: 20_000.0 for year in range(1968, 1997)}
    assert sa.aime(history_1935, 1935, params) == 1380
    assert benefits.aime(history_1935, 1935, params) == 1380


def test_aime_keeps_the_highest_years_when_there_are_more_than_the_count():
    params = _flat_params()
    # Born 1920: 26 computation years.  30 years 1952-1981 of 1,000 each,
    # plus 4 of them raised by 26,000: the top 26 are the 4 raised years
    # and 22 plain ones: (4 * 27,000 + 22 * 1,000) / 312 = 416.67 -> 416.
    history = {year: 1_000.0 for year in range(1952, 1982)}
    for year in (1960, 1965, 1970, 1975):
        history[year] = 27_000.0
    assert sa.aime(history, 1920, params) == 416


def test_aime_for_a_death_before_62_uses_the_minimum_and_death_indexing():
    params = _flat_params()
    # Born 1960, died 1984: 2 computation years (the minimum).  The top
    # two of 30,000 / 18,000 / 6,000 are 48,000; / 24 = 2,000.
    history = {1982: 30_000.0, 1983: 18_000.0, 1984: 6_000.0}
    assert sa.aime(history, 1960, params, death_year=1984) == 2_000
    # The legacy divisor would give 54,000 / 420 = 128.57 -> 128.
    assert benefits.aime(history, 1960, params) == 128


def test_aime_indexes_to_the_second_year_before_death():
    # INVENTED wage index: 1,000 before 1998, 2,000 in 1998-2019, 4,000
    # from 2020.  Born 1960, died 2000 (13 computation years, index 1998):
    # 1990's 10,000 -> 10,000 * 2,000 / 1,000 = 20,000; 1999 is after the
    # indexing year and enters unindexed at 5,000.  25,000 / 156 = 160.26.
    index = {year: 1_000.0 for year in range(1951, 1998)}
    index.update({year: 2_000.0 for year in range(1998, 2020)})
    index.update({year: 4_000.0 for year in range(2020, 2071)})
    params = _flat_params(index)
    history = {1990: 10_000.0, 1999: 5_000.0}
    assert sa.aime(history, 1960, params, death_year=2000) == 160
    # Alive at 62 (index 2020): 1990 -> 40,000 and 1999 -> 10,000;
    # 50,000 / 420 = 119.05 -> 119, the legacy result for this cohort too.
    assert sa.aime(history, 1960, params) == 119
    assert benefits.aime(history, 1960, params) == 119


def test_aime_for_a_disability_onset_uses_dropout_years_and_onset_indexing():
    params = _flat_params()
    # Born 1960, period of disability from 2005: 19 computation years,
    # index year 2003.  24,000 in each of 1990-2004 (15 years) = 360,000;
    # / (19 * 12 = 228) = 1578.95 -> 1578.
    history = {year: 24_000.0 for year in range(1990, 2005)}
    assert sa.aime(history, 1960, params, disability_year=2005) == 1578


# ---------------------------------------------------------------------------
# Unchanged results from the 1929 birth cohort on (INVENTED random careers)
# ---------------------------------------------------------------------------
def _random_history(rng: random.Random, birth: int) -> dict[int, float]:
    first = max(1968, birth + 18)
    last = min(2060, birth + 70)
    history = {}
    for year in range(first, last + 1):
        if rng.random() < 0.8:
            history[year] = rng.choice(
                (0.0, rng.uniform(0.0, 20_000.0), rng.uniform(0.0, 2.0e5))
            )
    return history


def test_statutory_equals_legacy_for_every_birth_year_from_1929():
    params = _growth_params()
    rng = random.Random(20260924)
    for birth in range(1929, 1996):
        for _ in range(15):
            history = _random_history(rng, birth)
            statutory = sa.aime(history, birth, params)
            assert statutory == benefits.aime(history, birth, params)
            assert statutory == sa.oracle_aime(
                history,
                birth,
                params,
                computation_years=ComputationYears.STATUTORY,
            )


def _reference_aime(history, birth, params, count, index_year):
    """Independent restatement of 415(b)(1)-(3) for the property test."""
    indexed = []
    for year, earnings in history.items():
        creditable = min(float(earnings), params.wage_base_for(year))
        if year < index_year:
            creditable = (
                creditable * params.nawi[index_year] / params.nawi[year]
            )
        indexed.append(creditable)
    top = sorted(indexed, reverse=True)[:count]
    top += [0.0] * (count - len(top))
    return math.floor(sum(top) / (12 * count))


def test_before_1929_equals_the_oracle_arithmetic_with_the_statutory_count():
    # The Track C attribution check's form: the oracle's own creditable and
    # indexed history, the highest (elapsed - 5) years, floored.
    params = _growth_params()
    rng = random.Random(1917)
    for birth in range(1913, 1929):
        # Elapsed: 1951 through the year before attaining 62; less 5.
        count = (birth + 62 - 1950 - 1) - 5
        assert sa.benefit_computation_years(birth) == count < 35
        for _ in range(10):
            history = _random_history(rng, birth)
            expected = _reference_aime(
                history, birth, params, count, birth + 60
            )
            assert sa.aime(history, birth, params) == expected
            assert (
                sa.aime_with_computation_years(
                    history, count, params, indexing_year=birth + 60
                )
                == expected
            )
            assert sa.aime_with_computation_years(
                history, 35, params, indexing_year=birth + 60
            ) == benefits.aime(history, birth, params)


def test_oracle_aime_legacy_is_the_unchanged_benefits_aime():
    params = _growth_params()
    rng = random.Random(35)
    # Every birth year, including those the statutory encoding refuses.
    for birth in (1905, 1912, 1920, 1928, 1929, 1960):
        for _ in range(5):
            history = _random_history(rng, birth)
            assert sa.oracle_aime(
                history,
                birth,
                params,
                computation_years=ComputationYears.LEGACY_FIXED_35,
            ) == benefits.aime(history, birth, params)
    assert ComputationYears("legacy_fixed_35") is (
        ComputationYears.LEGACY_FIXED_35
    )
    assert ComputationYears("statutory_415_b_2") is ComputationYears.STATUTORY


# ---------------------------------------------------------------------------
# Refusals
# ---------------------------------------------------------------------------
def test_refuses_workers_attaining_62_before_1975():
    # 104(j)(2) of the 1972 amendments sets a man's elapsed years then.
    with pytest.raises(ValueError, match="104"):
        sa.benefit_computation_years(1912)
    with pytest.raises(ValueError, match="104"):
        sa.aime({1968: 1_000.0}, 1900, _flat_params())
    assert sa.benefit_computation_years(1913) == 19


def test_refuses_undecided_or_invalid_dates():
    with pytest.raises(ValueError, match="death after a disability"):
        sa.benefit_computation_years(
            1960, death_year=2010, disability_year=2005
        )
    with pytest.raises(ValueError, match="precedes birth_year"):
        sa.elapsed_years(1960, death_year=1959)
    with pytest.raises(ValueError, match="precedes birth_year"):
        sa.elapsed_years(1960, disability_year=1950)
    with pytest.raises(TypeError):
        sa.elapsed_years(1960.0)
    with pytest.raises(TypeError):
        sa.elapsed_years(True)


def test_refuses_years_that_cannot_be_computation_base_years():
    params = _flat_params()
    with pytest.raises(ValueError, match="1951"):
        sa.aime({1950: 1_000.0, 1968: 1_000.0}, 1929, params)
    with pytest.raises(ValueError, match="positive"):
        sa.aime_with_computation_years(
            {1968: 1.0}, 0, params, indexing_year=1990
        )


# ---------------------------------------------------------------------------
# Where the legacy convention is used (source scan, no imports)
# ---------------------------------------------------------------------------
#: Every module that calls ``benefits.aime`` (the legacy fixed-35
#: convention) directly, with the committed evidence it serves.
LEGACY_BENEFITS_AIME_CALLERS = {
    # Sealed first-estimates ledger (birth-evidence source identity).
    "src/populace_dynamics/estimates/ledgers.py",
    # Sealed gate-2c couple-earnings AIME proxy.
    "src/populace_dynamics/data/couple_earnings.py",
    # Track A's disclosed approximation (Registration 13).
    "src/populace_dynamics/cola_track_a/benefits.py",
    # The LEGACY_FIXED_35 branch of oracle_aime itself.
    "src/populace_dynamics/ss/statutory_aime.py",
    # The cross-engine PIA artifact (born 1958/1964: 35 either way); its
    # notes record a comparison against the fixed 35.
    "scripts/build_cross_engine_pia_artifact.py",
    # The R7 earnings-sharing replication, whose PIA supply admits every
    # birth year with an age-60 year in the wage-index series.
    "scripts/replication_r7_sharing.py",
}
#: The sealed package initializer re-exports ``benefits.aime`` as
#: ``ss.aime``; nothing may import it under that name or call it.
LEGACY_AIME_REEXPORTS = {"src/populace_dynamics/ss/__init__.py"}
#: Every module that names ``ComputationYears.LEGACY_FIXED_35``.
LEGACY_CONVENTION_USERS = {
    "src/populace_dynamics/cola_track_a/benefits.py",
    "src/populace_dynamics/ss/statutory_aime.py",
    # Track C step 1 compares the Axiom engine with the oracle AIME under
    # --oracle-computation-years (statutory by default; legacy_fixed_35 is
    # the oracle of track-c-aime-agreement-20260923), records Track A's
    # legacy AIME beside it, and refuses to run if Track A's convention
    # changes.
    "scripts/track_c_aime_agreement.py",
    # Exercise 3 (FRA to 68) reads Track A's convention so its projection
    # stays identical to exercise 1's (E1 e1-ratified-1; Max's rulings d188
    # item (a) and, by name, d281 on 2026-09-25).
    "src/populace_dynamics/fra68_track/config.py",
}


def _python_sources():
    for base in ("src", "scripts"):
        for path in sorted((ROOT / base).rglob("*.py")):
            yield path.relative_to(ROOT).as_posix(), ast.parse(
                path.read_text(encoding="utf-8")
            )


def test_the_legacy_convention_is_used_only_where_pinned():
    callers, users, aliases = set(), set(), set()
    for relative, tree in _python_sources():
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "aime"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in ("benefits", "ss")
            ):
                callers.add(relative)
            if (
                isinstance(node, ast.Attribute)
                and node.attr == "LEGACY_FIXED_35"
            ):
                users.add(relative)
            if isinstance(node, ast.ImportFrom) and node.module in (
                "populace_dynamics.ss",
                "populace_dynamics.ss.benefits",
            ):
                if any(alias.name == "aime" for alias in node.names):
                    aliases.add(relative)
    assert callers == LEGACY_BENEFITS_AIME_CALLERS
    assert users == LEGACY_CONVENTION_USERS
    assert aliases == LEGACY_AIME_REEXPORTS
