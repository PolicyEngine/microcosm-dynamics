"""Lifetime-earnings measures and weighted quintiles (package G2).

Every career, marriage record, wage index, contribution and benefit base,
tax rate and interest rate in this module is INVENTED.  No PSID file and
no committed evidence file is read here; the captured SSA schedules are
tested in ``test_lifetime_measure_sources.py``.  Expected values come from
the stated definitions (hand arithmetic in comments) or from independent
reference implementations written in this module, never from the code
under test.
"""

from __future__ import annotations

import math
import random
from fractions import Fraction

import numpy as np
import pandas as pd
import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from populace_dynamics import scenario_benefits as sb
from populace_dynamics.cola_track_a import benefits as track_a_benefits
from populace_dynamics.estimates import lifetime_measures as lm
from populace_dynamics.fra68_track import config as fra68_config
from populace_dynamics.min_benefit_track_m import rules as track_m_rules
from populace_dynamics.ss import benefits, statutory_aime
from populace_dynamics.ss.params import SSAParameters
from populace_dynamics.ss.statutory_aime import ComputationYears

SETTINGS = settings(
    max_examples=60,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)


# ---------------------------------------------------------------------------
# INVENTED parameters, schedules and frames
# ---------------------------------------------------------------------------
def _params(*, cap: float | None = None) -> SSAParameters:
    """INVENTED: 4 percent wage growth from 1951; a rising base, or one
    flat base ``cap`` when given."""
    wage_base = (
        {1937: float(cap)}
        if cap is not None
        else {1937: 3_000.0, 1975: 14_100.0, 1990: 51_300.0, 2010: 106_800}
    )
    return SSAParameters(
        nawi={y: 2_800.0 * 1.04 ** (y - 1951) for y in range(1951, 2071)},
        wage_base=wage_base,
        pia_factors=(0.9, 0.32, 0.15),
        fra_months_by_birth_year=[(1900, 792), (1955, 804)],
        early_monthly_rates=(5 / 900, 5 / 1200),
        early_first_bracket_months=36,
        pe_us_revision="INVENTED",
        delayed_credit_by_birth_year=[(1900, 0.08)],
    )


def _rates(percent: float = 12.0) -> lm.OASDITaxRates:
    """INVENTED: one combined rate for every year from 1937."""
    return lm.OASDITaxRates(
        combined_percent_by_year={1937: percent},
        open_ended_from=1938,
        open_ended_combined_percent=percent,
        basis=lm.TaxRateBasis.TRUST_FUND_RECEIVED,
        provenance={"source": "INVENTED"},
    )


def _interest(
    percent: float = 5.0, first: int = 1930, last: int = 2100
) -> lm.TrustFundInterestRates:
    """INVENTED: one interest rate for every year in [first, last]."""
    return lm.TrustFundInterestRates(
        percent_by_year={y: percent for y in range(first, last + 1)},
        series="INVENTED",
        provenance={"source": "INVENTED"},
    )


def _careers(histories: dict[int, dict[int, float]]) -> pd.DataFrame:
    rows = [
        (pid, year, value)
        for pid, history in histories.items()
        for year, value in sorted(history.items())
    ]
    return pd.DataFrame(rows, columns=["person_id", "year", "earnings"])


def _persons(births: dict[int, int]) -> pd.DataFrame:
    return pd.DataFrame(
        {"person_id": list(births), "birth_year": list(births.values())}
    )


def _episodes(rows: list[tuple]) -> pd.DataFrame:
    """INVENTED marriage episodes: (person, order, start, end, how,
    spouse)."""
    columns = [
        "person_id",
        "marriage_order",
        "start_year",
        "episode_end_year",
        "how_ended",
        "spouse_person_id",
    ]
    frame = pd.DataFrame(rows, columns=columns)
    for column in ("start_year", "episode_end_year", "spouse_person_id"):
        frame[column] = frame[column].astype("Int64")
    return frame


def _couple(start: int = 1950) -> pd.DataFrame:
    """INVENTED: persons 1 and 2 married to each other from ``start``."""
    return _episodes(
        [
            (1, 1, start, None, "intact", 2),
            (2, 1, start, None, "intact", 1),
        ]
    )


def _pv(result: lm.MeasureResult, pid: int) -> float:
    frame = result.frame.set_index("person_id")
    return float(frame.at[pid, "pv_at_62"])


histories_strategy = st.dictionaries(
    st.integers(1951, 2030),
    st.floats(0, 300_000, allow_nan=False, allow_infinity=False),
    min_size=1,
    max_size=45,
)


# ---------------------------------------------------------------------------
# 4. Weighted quintiles
# ---------------------------------------------------------------------------
def _reference_ranks(values: list[float], weights: list[float]) -> list[int]:
    """Brute-force midpoint rule, exact (independent of the module)."""
    total = sum(Fraction(w) for w in weights)
    ranks = []
    for value in values:
        below = sum(
            Fraction(w)
            for v, w in zip(values, weights, strict=True)
            if v < value
        )
        tied = sum(
            Fraction(w)
            for v, w in zip(values, weights, strict=True)
            if v == value
        )
        midpoint = below + tied / 2
        ranks.append(min(4, math.floor(5 * midpoint / total)))
    return ranks


def _rank(label: str) -> int:
    return 4 - lm.QUINTILE_LABELS.index(label)


weights_strategy = st.floats(0.01, 1_000.0, allow_nan=False)


@SETTINGS
@given(
    st.lists(
        st.tuples(st.integers(-50, 50).map(float), weights_strategy),
        min_size=1,
        max_size=60,
    )
)
def test_quintiles_match_the_brute_force_reference(pairs):
    values = [v for v, _ in pairs]
    weights = [w for _, w in pairs]
    labels = lm.weighted_quintiles(pd.Series(values), pd.Series(weights))
    assert [_rank(label) for label in labels] == _reference_ranks(
        values, weights
    )


@SETTINGS
@given(
    st.lists(
        st.floats(-1e6, 1e6, allow_nan=False),
        min_size=1,
        max_size=80,
        unique=True,
    ),
    st.data(),
)
def test_quintile_shares_are_a_fifth_within_the_largest_weight(values, data):
    weights = data.draw(
        st.lists(weights_strategy, min_size=len(values), max_size=len(values))
    )
    labels = lm.weighted_quintiles(pd.Series(values), pd.Series(weights))
    total = math.fsum(weights)
    bound = max(weights) / total + 1e-12
    for label in lm.QUINTILE_LABELS:
        share = (
            math.fsum(
                w
                for w, got in zip(weights, labels, strict=True)
                if got == label
            )
            / total
        )
        assert abs(share - 0.2) <= bound


@pytest.mark.parametrize("m", [1, 2, 7, 40])
def test_equal_weights_distinct_values_split_exactly(m):
    values = pd.Series(
        random.Random(m).sample(range(10_000), 5 * m), dtype=float
    )
    labels = lm.weighted_quintiles(values, pd.Series(np.ones(5 * m)))
    assert (
        labels.value_counts().reindex(lm.QUINTILE_LABELS).tolist() == [m] * 5
    )
    ordered = labels[values.sort_values().index].tolist()
    assert ordered == [
        label for label in reversed(lm.QUINTILE_LABELS) for _ in range(m)
    ]


@SETTINGS
@given(
    st.lists(
        st.tuples(
            st.integers(0, 30).map(float), st.integers(1, 10_000).map(float)
        ),
        min_size=1,
        max_size=50,
    ),
    st.integers(-20, 20),
    st.integers(1, 1_000),
)
def test_quintiles_are_invariant_to_exact_weight_scaling(pairs, power, factor):
    values = pd.Series([v for v, _ in pairs])
    weights = pd.Series([w for _, w in pairs])
    base = lm.weighted_quintiles(values, weights)
    # Powers of two and integer factors of integer weights are exact.
    assert lm.weighted_quintiles(values, weights * 2.0**power).equals(base)
    assert lm.weighted_quintiles(values, weights * float(factor)).equals(base)


@SETTINGS
@given(
    st.lists(
        st.tuples(st.integers(0, 20).map(float), weights_strategy),
        min_size=1,
        max_size=50,
    ),
    st.randoms(use_true_random=False),
)
def test_quintiles_are_invariant_to_row_order(pairs, rng):
    frame = pd.DataFrame(pairs, columns=["value", "weight"])
    frame["cell"] = [i % 3 for i in range(len(frame))]
    base = lm.weighted_quintiles(
        frame["value"], frame["weight"], by=frame["cell"]
    )
    order = list(frame.index)
    rng.shuffle(order)
    shuffled = frame.loc[order]
    again = lm.weighted_quintiles(
        shuffled["value"], shuffled["weight"], by=shuffled["cell"]
    )
    assert again.reindex(frame.index).equals(base)


@SETTINGS
@given(
    st.lists(
        st.tuples(
            st.integers(0, 15).map(float),
            weights_strategy,
            st.sampled_from(["1950–1959", "1960–1969"]),
        ),
        min_size=1,
        max_size=60,
    )
)
def test_a_higher_value_never_gets_a_lower_quintile_in_its_cell(rows):
    frame = pd.DataFrame(rows, columns=["value", "weight", "cell"])
    labels = lm.weighted_quintiles(
        frame["value"], frame["weight"], by=frame["cell"]
    )
    frame["rank"] = [_rank(label) for label in labels]
    for _, cell in frame.groupby("cell"):
        ordered = cell.sort_values("value", kind="stable")
        assert ordered["rank"].is_monotonic_increasing
        for _, tied in cell.groupby("value"):
            assert tied["rank"].nunique() == 1


@SETTINGS
@given(
    st.lists(
        st.tuples(
            st.one_of(st.none(), st.integers(0, 40).map(float)),
            weights_strategy,
        ),
        min_size=1,
        max_size=50,
    )
)
def test_missing_values_and_only_they_are_not_computed(pairs):
    values = pd.Series([np.nan if v is None else v for v, _ in pairs])
    weights = pd.Series([w for _, w in pairs])
    labels = lm.weighted_quintiles(values, weights)
    assert ((labels == lm.NOT_COMPUTED) == values.isna()).all()
    present = values.notna()
    if present.any():
        alone = lm.weighted_quintiles(values[present], weights[present])
        assert labels[present].astype(str).equals(alone.astype(str))


def test_cells_are_cut_independently():
    values = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 100.0, 200.0])
    weights = pd.Series(np.ones(7))
    by = pd.Series(["a"] * 5 + ["b"] * 2)
    labels = lm.weighted_quintiles(values, weights, by=by)
    a_only = lm.weighted_quintiles(values[:5], weights[:5])
    assert labels[:5].astype(str).tolist() == a_only.astype(str).tolist()
    # Cell b: two rows, midpoints at 1/4 and 3/4 of its weight.
    assert labels[5:].tolist() == ["Second lowest", "Second highest"]


def test_whole_population_and_cohort_scopes():
    births = pd.Series([1958, 1961, 1969, 1970])
    assert lm.quintile_cells(births, lm.QuintileScope.WHOLE_POPULATION) is None
    cells = lm.quintile_cells(births, lm.QuintileScope.TEN_YEAR_BIRTH_COHORT)
    assert cells.tolist() == [
        "1950–1959",
        "1960–1969",
        "1960–1969",
        "1970–1979",
    ]


@pytest.mark.parametrize(
    ("values", "weights", "by", "message"),
    [
        ([1.0, 2.0], [1.0, 0.0], None, "positive"),
        ([1.0, 2.0], [1.0, np.nan], None, "positive"),
        ([1.0, np.inf], [1.0, 1.0], None, "finite"),
        ([1.0, 2.0], [1.0, 1.0], [None, "a"], "by is missing"),
    ],
)
def test_quintiles_refuse_bad_inputs(values, weights, by, message):
    with pytest.raises(ValueError, match=message):
        lm.weighted_quintiles(
            pd.Series(values),
            pd.Series(weights),
            by=None if by is None else pd.Series(by),
        )


def test_quintiles_refuse_misaligned_indexes_and_bad_labels():
    with pytest.raises(ValueError, match="share one index"):
        lm.weighted_quintiles(
            pd.Series([1.0], index=[0]), pd.Series([1.0], index=[1])
        )
    with pytest.raises(ValueError, match="five distinct"):
        lm.weighted_quintiles(
            pd.Series([1.0]), pd.Series([1.0]), labels=("a", "b")
        )


def test_quintile_summary_reports_counts_and_shares():
    values = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, np.nan])
    weights = pd.Series([1.0, 1.0, 1.0, 1.0, 1.0, 9.0])
    labels = lm.weighted_quintiles(values, weights)
    summary = lm.quintile_summary(labels, weights).set_index("label")
    assert summary.loc["Highest", "n"] == 1
    assert summary.loc["Highest", "weight_share"] == pytest.approx(0.2)
    assert summary.loc[lm.NOT_COMPUTED, "weight"] == 9.0
    assert math.isnan(summary.loc[lm.NOT_COMPUTED, "weight_share"])


# ---------------------------------------------------------------------------
# 1. Initial AIME at 62
# ---------------------------------------------------------------------------
@SETTINGS
@given(
    histories_strategy,
    st.integers(1929, 1985),
    st.integers(2000, 2060),
    st.sampled_from(sorted(lm.AIME_CONVENTIONS)),
)
def test_aime_equals_the_oracle_on_the_same_cut_history(
    history, birth, analysis_year, name
):
    convention = lm.AIME_CONVENTIONS[name]
    params = _params()
    result = lm.initial_aime_at_62(
        _careers({7: history}),
        _persons({7: birth}),
        params,
        analysis_year=analysis_year,
        convention=convention,
    )
    row = result.frame.iloc[0]
    cutoff = analysis_year
    if convention.last_earnings_age is not None:
        cutoff = min(cutoff, birth + convention.last_earnings_age)
    kept = {y: e for y, e in history.items() if y <= cutoff}
    assert row["history_cutoff_year"] == cutoff
    assert row["n_history_years"] == len(kept)
    assert bool(row["reaches_62_by_analysis_year"]) == (
        birth + 62 <= analysis_year
    )
    if not kept:
        # Rows only after the cutoff: unobserved before 62, not zero.
        assert row["reason"] == "no_career_rows_before_cutoff"
        return
    assert row["status"] == lm.COMPUTED
    assert row["first_earnings_year"] == min(kept)
    assert bool(row["history_starts_after_age_22"]) == (min(kept) > birth + 22)
    assert row["aime"] == statutory_aime.oracle_aime(
        kept, birth, params, computation_years=convention.computation_years
    )


@SETTINGS
@given(histories_strategy, st.integers(1929, 1985))
def test_legacy_and_statutory_agree_for_births_from_1929(history, birth):
    """Two implementations of one semantics: 415(b)(2) gives 35 years to
    every worker born 1929 or later who is alive at 62."""
    frames = [
        lm.initial_aime_at_62(
            _careers({1: history}),
            _persons({1: birth}),
            _params(),
            analysis_year=2100,
            convention=lm.AimeConvention(
                name="t",
                computation_years=years,
                last_earnings_age=61,
                source="",
            ),
        ).frame
        for years in ComputationYears
    ]
    pd.testing.assert_series_equal(frames[0]["aime"], frames[1]["aime"])
    assert frames[0]["status"].tolist() == frames[1]["status"].tolist()


@SETTINGS
@given(histories_strategy, st.integers(1913, 1985))
def test_exercise_4_convention_equals_track_m_history_pia(history, birth):
    """Differential against Track M's own old-age PIA record (rules.py),
    for an entitlement in the year of attaining 62."""
    assume(any(year <= birth + 61 for year in history))
    params = _params()
    record = track_m_rules.history_pia(
        history,
        birth_year=birth,
        params=params,
        basis=track_m_rules.BASIS_OLD_AGE,
        window_year=birth + 62,
    )
    row = lm.initial_aime_at_62(
        _careers({1: history}),
        _persons({1: birth}),
        params,
        analysis_year=birth + 62,
        convention=lm.AIME_CONVENTIONS["exercise_4_min_benefit"],
    ).frame.iloc[0]
    assert row["aime"] == record.aime


@SETTINGS
@given(histories_strategy, st.integers(1913, 1985), st.integers(2000, 2060))
def test_exercise_1_convention_reproduces_the_track_a_age_62_pia(
    history, birth, analysis_year
):
    """Differential against the Track A calculator's age-62 PIA call
    (scenario_benefits.eligibility_pia_for_clock with Track A's
    computation years over the history as supplied)."""
    params = _params()
    supplied = {y: e for y, e in history.items() if y <= analysis_year}
    assume(supplied)
    expected = sb.eligibility_pia_for_clock(
        sb.WorkerClock.at_age_62(birth),
        history=supplied,
        birth_year=birth,
        params=params,
        computation_years=track_a_benefits.TRACK_A_COMPUTATION_YEARS,
    )
    row = lm.initial_aime_at_62(
        _careers({1: history}),
        _persons({1: birth}),
        params,
        analysis_year=analysis_year,
        convention=lm.AIME_CONVENTIONS["exercise_1_cola"],
    ).frame.iloc[0]
    assert benefits.pia(row["aime"], birth + 62, params) == expected


def test_named_conventions_match_the_blind_test_code():
    conventions = lm.AIME_CONVENTIONS
    assert (
        conventions["exercise_1_cola"].computation_years
        is track_a_benefits.TRACK_A_COMPUTATION_YEARS
    )
    assert (
        conventions["exercise_3_fra68"].computation_years.value
        == fra68_config.MAX_RULINGS["benefit_computation_years"]["ruling"]
    )
    assert conventions["exercise_4_min_benefit"].computation_years is (
        ComputationYears.STATUTORY
    )
    assert conventions["mint8_initial_aime"].last_earnings_age == 61


def test_aime_example_and_flags():
    # INVENTED: flat wage index (indexing neutral), no binding base.
    params = SSAParameters(
        nawi={y: 10_000.0 for y in range(1951, 2071)},
        wage_base={1937: 1.0e12},
        pia_factors=(0.9, 0.32, 0.15),
        fra_months_by_birth_year=[(1900, 792)],
        early_monthly_rates=(5 / 900, 5 / 1200),
        early_first_bracket_months=36,
        pe_us_revision="INVENTED",
    )
    careers = _careers(
        {
            # 35 years of 42,000 before 62: AIME 42,000 / 12 = 3,500.
            1: {y: 42_000.0 for y in range(1975, 2010)} | {2012: 9e9},
            # Younger than 62 in 2030: provisional, 20 years of 42,000
            # over 35 years: floor(840,000 / 420) = 2,000.
            2: {y: 42_000.0 for y in range(1990, 2010)},
            # Years before 1951 are dropped and counted.
            3: {1949: 5.0, 1950: 5.0, 1980: 4_200.0},
        }
    )
    persons = _persons({1: 1950, 2: 1975, 3: 1925, 4: 1960, 5: 1910})
    frame = lm.initial_aime_at_62(
        careers,
        persons,
        params,
        analysis_year=2030,
        convention=lm.AIME_CONVENTIONS["mint8_initial_aime"],
    ).frame.set_index("person_id")
    assert frame.at[1, "aime"] == 3_500.0
    assert frame.at[1, "basis"] == lm.AimeBasis.AGE_62.value
    assert frame.at[1, "history_cutoff_year"] == 2011
    assert frame.at[2, "aime"] == 2_000.0
    assert frame.at[2, "basis"] == (
        lm.AimeBasis.PROVISIONAL_THROUGH_LAST_OBSERVED.value
    )
    assert bool(frame.at[2, "history_ends_before_cutoff"])
    # Born 1925: statutory 415(b)(2) gives 1951-1986 elapsed less 5 = 31.
    assert frame.at[3, "years_before_1951_dropped"] == 2
    assert frame.at[3, "computation_years"] == 31
    assert frame.at[3, "aime"] == math.floor(4_200.0 / (31 * 12))
    assert frame.at[4, "reason"] == "no_career_rows"
    assert frame.at[5, "status"] == lm.NOT_COMPUTED


def test_aime_refuses_pre_1975_and_missing_nawi_with_reasons():
    params = _params()
    careers = _careers({1: {1960: 1_000.0}, 2: {2000: 1_000.0}})
    frame = lm.initial_aime_at_62(
        careers,
        _persons({1: 1910, 2: 2010}),
        params,
        analysis_year=2090,
        convention=lm.AIME_CONVENTIONS["mint8_initial_aime"],
    ).frame.set_index("person_id")
    assert frame.at[1, "reason"] == (
        "statutory_oracle_refuses_attaining_62_before_1975"
    )
    # Born 2010: indexing year 2070 is in the series, but 2072 is not.
    assert frame.at[2, "status"] == lm.COMPUTED
    frame = lm.initial_aime_at_62(
        careers,
        _persons({2: 2012}),
        params,
        analysis_year=2090,
        convention=lm.AIME_CONVENTIONS["mint8_initial_aime"],
    ).frame
    assert frame.at[0, "reason"] == "nawi_unavailable:2072"


@pytest.mark.parametrize(
    ("careers", "message"),
    [
        (
            pd.DataFrame(
                {"person_id": [1, 1], "year": [2000, 2000], "earnings": [1, 2]}
            ),
            "duplicate",
        ),
        (
            pd.DataFrame({"person_id": [1], "year": [2000], "earnings": [-1]}),
            "non-negative",
        ),
        (
            pd.DataFrame(
                {"person_id": [1], "year": [2000.5], "earnings": [1]}
            ),
            "integers",
        ),
        (pd.DataFrame({"person_id": [1], "year": [2000]}), "lacks"),
    ],
)
def test_measures_refuse_malformed_careers(careers, message):
    with pytest.raises(ValueError, match=message):
        lm.initial_aime_at_62(
            careers,
            _persons({1: 1950}),
            _params(),
            analysis_year=2030,
            convention=lm.AIME_CONVENTIONS["mint8_initial_aime"],
        )


def test_measures_refuse_malformed_persons():
    careers = _careers({1: {2000: 1.0}})
    with pytest.raises(ValueError, match="duplicate person_id"):
        lm.initial_aime_at_62(
            careers,
            pd.DataFrame({"person_id": [1, 1], "birth_year": [1950, 1950]}),
            _params(),
            analysis_year=2030,
            convention=lm.AIME_CONVENTIONS["mint8_initial_aime"],
        )
    with pytest.raises(ValueError, match="missing"):
        lm.initial_aime_at_62(
            careers,
            pd.DataFrame({"person_id": [1], "birth_year": [None]}),
            _params(),
            analysis_year=2030,
            convention=lm.AIME_CONVENTIONS["mint8_initial_aime"],
        )
    with pytest.raises(TypeError, match="AimeConvention"):
        lm.initial_aime_at_62(
            careers,
            _persons({1: 1950}),
            _params(),
            analysis_year=2030,
            convention="mint8_initial_aime",
        )


# ---------------------------------------------------------------------------
# 2. Lifetime payroll tax at 62
# ---------------------------------------------------------------------------
def _reference_pv(
    history: dict[int, float],
    birth: int,
    params: SSAParameters,
    rate: float,
    interest: float,
) -> float:
    """Independent reference: constant rates, closed-form factors."""
    reference = birth + 62
    return math.fsum(
        min(e, params.wage_base_for(y))
        * rate
        * (1.0 + interest) ** (reference - y)
        for y, e in history.items()
    )


@SETTINGS
@given(
    histories_strategy,
    st.integers(1920, 1990),
    st.floats(1.0, 20.0),
    st.floats(0.0, 10.0),
)
def test_pv_matches_the_closed_form_reference(history, birth, rate, interest):
    params = _params()
    result = lm.lifetime_payroll_tax_pv_at_62(
        _careers({1: history}),
        _persons({1: birth}),
        params,
        shared=False,
        rates=_rates(rate),
        interest=_interest(interest),
    )
    expected = _reference_pv(
        history, birth, params, rate / 100.0, interest / 100.0
    )
    assert _pv(result, 1) == pytest.approx(expected, rel=1e-9, abs=1e-9)


@SETTINGS
@given(
    st.dictionaries(
        st.integers(1951, 2030),
        st.floats(0, 1e6, allow_nan=False),
        min_size=1,
        max_size=40,
    ),
    st.integers(1920, 1990),
)
def test_pv_is_homogeneous_below_the_cap(history, birth):
    params = _params(cap=1.0e12)
    kwargs = {
        "shared": False,
        "rates": _rates(12.4),
        "interest": _interest(3.0),
    }
    persons = _persons({1: birth})
    once = lm.lifetime_payroll_tax_pv_at_62(
        _careers({1: history}), persons, params, **kwargs
    )
    twice = lm.lifetime_payroll_tax_pv_at_62(
        _careers({1: {y: 2.0 * e for y, e in history.items()}}),
        persons,
        params,
        **kwargs,
    )
    zero = lm.lifetime_payroll_tax_pv_at_62(
        _careers({1: dict.fromkeys(history, 0.0)}), persons, params, **kwargs
    )
    assert _pv(twice, 1) == 2.0 * _pv(once, 1)
    assert _pv(zero, 1) == 0.0
    double_rate = lm.lifetime_payroll_tax_pv_at_62(
        _careers({1: history}),
        persons,
        params,
        shared=False,
        rates=_rates(24.8),
        interest=_interest(3.0),
    )
    assert _pv(double_rate, 1) == 2.0 * _pv(once, 1)


@SETTINGS
@given(
    st.dictionaries(
        st.integers(1951, 2030),
        st.floats(0, 1e6, allow_nan=False),
        min_size=1,
        max_size=40,
    ),
    st.integers(1920, 1990),
)
def test_earnings_above_the_cap_do_not_change_pv(extra, birth):
    params = _params(cap=50_000.0)
    persons = _persons({1: birth})
    at_cap = {y: 50_000.0 for y in extra}
    above = {y: 50_000.0 + e for y, e in extra.items()}
    kwargs = {
        "shared": False,
        "rates": _rates(12.4),
        "interest": _interest(4.0),
    }
    assert _pv(
        lm.lifetime_payroll_tax_pv_at_62(
            _careers({1: at_cap}), persons, params, **kwargs
        ),
        1,
    ) == _pv(
        lm.lifetime_payroll_tax_pv_at_62(
            _careers({1: above}), persons, params, **kwargs
        ),
        1,
    )


@SETTINGS
@given(histories_strategy, histories_strategy, st.integers(1920, 1985))
def test_shared_pvs_of_a_couple_sum_to_their_own_pvs(a, b, birth):
    """A couple with one birth year, married to each other in every year
    either paid tax: the shared PVs sum to the own PVs."""
    params = _params()
    careers = _careers({1: a, 2: b})
    persons = _persons({1: birth, 2: birth})
    common = {"rates": _rates(12.4), "interest": _interest(4.0)}
    own = lm.lifetime_payroll_tax_pv_at_62(
        careers, persons, params, shared=False, **common
    )
    shared = lm.lifetime_payroll_tax_pv_at_62(
        careers,
        persons,
        params,
        shared=True,
        marriage_episodes=_couple(1940),
        **common,
    )
    assert _pv(shared, 1) + _pv(shared, 2) == pytest.approx(
        _pv(own, 1) + _pv(own, 2), rel=1e-12, abs=1e-6
    )
    # Each spouse holds half the couple's taxes in every shared year.
    assert _pv(shared, 1) == pytest.approx(_pv(shared, 2), rel=1e-12)
    years = set(a) | set(b)
    assert shared.frame["married_years_shared"].tolist() == [len(years)] * 2
    # Person 1's spouse lacks a row in the years only person 1 worked.
    assert shared.frame["married_years_spouse_year_absent"].tolist() == [
        len(years - set(b)),
        len(years - set(a)),
    ]


@SETTINGS
@given(histories_strategy, st.integers(1920, 1985))
def test_never_married_shared_equals_own(history, birth):
    params = _params()
    common = {"rates": _rates(12.4), "interest": _interest(4.0)}
    careers = _careers({1: history})
    persons = _persons({1: birth})
    own = lm.lifetime_payroll_tax_pv_at_62(
        careers, persons, params, shared=False, **common
    )
    shared = lm.lifetime_payroll_tax_pv_at_62(
        careers,
        persons,
        params,
        shared=True,
        marriage_episodes=_episodes([]),
        **common,
    )
    assert _pv(shared, 1) == _pv(own, 1)
    assert shared.frame.at[0, "married_years_shared"] == 0


def test_shared_example_by_hand():
    # INVENTED: rate 10 percent, interest 0, no binding base.  Person 1
    # (born 1950) earns 100 in 1980-1989; person 2 earns 300 in 1985-1994.
    # They marry in 1985 and divorce in 1990 (married at the end of
    # 1985-1989).  Own taxes: 1 -> 100, 2 -> 300.  Person 1's shared
    # taxes: 1980-84 own 10 each = 50; 1985-89 (10 + 30) / 2 = 20 each =
    # 100: total 150.  Person 2's: 1985-89 20 each = 100; 1990-94 own 30
    # each = 150: total 250.
    params = _params(cap=1.0e12)
    careers = _careers(
        {
            1: {y: 100.0 for y in range(1980, 1990)},
            2: {y: 300.0 for y in range(1985, 1995)},
        }
    )
    episodes = _episodes(
        [
            (1, 1, 1985, 1990, "divorce", 2),
            (2, 1, 1985, 1990, "divorce", 1),
        ]
    )
    result = lm.lifetime_payroll_tax_pv_at_62(
        careers,
        _persons({1: 1950, 2: 1950}),
        params,
        shared=True,
        rates=_rates(10.0),
        interest=_interest(0.0),
        marriage_episodes=episodes,
    )
    assert _pv(result, 1) == pytest.approx(150.0)
    assert _pv(result, 2) == pytest.approx(250.0)
    assert result.frame["married_years_shared"].tolist() == [5, 5]
    assert result.frame["married_years_spouse_record_disagrees"].sum() == 0


def test_missing_spouse_is_counted_or_refused():
    params = _params(cap=1.0e12)
    careers = _careers({1: {y: 100.0 for y in range(1980, 1990)}})
    # Spouse 9 has no career; spouse NA is not a PSID person.
    episodes = _episodes(
        [
            (1, 1, 1979, 1985, "divorce", 9),
            (1, 2, 1986, None, "intact", None),
        ]
    )
    common = {
        "shared": True,
        "rates": _rates(10.0),
        "interest": _interest(0.0),
        "marriage_episodes": episodes,
    }
    own_only = lm.lifetime_payroll_tax_pv_at_62(
        careers, _persons({1: 1950}), params, **common
    )
    assert _pv(own_only, 1) == pytest.approx(100.0)
    assert own_only.frame.at[0, "married_years_spouse_unavailable"] == 9
    refused = lm.lifetime_payroll_tax_pv_at_62(
        careers,
        _persons({1: 1950}),
        params,
        missing_spouse=lm.MissingSpousePolicy.NOT_COMPUTED,
        **common,
    )
    assert refused.frame.at[0, "reason"] == "spouse_career_unavailable"


def test_disagreeing_spouse_records_are_counted():
    params = _params(cap=1.0e12)
    careers = _careers({1: {2000: 100.0}, 2: {2000: 300.0}})
    episodes = _episodes([(1, 1, 1990, None, "intact", 2)])
    episodes = pd.concat(
        [episodes, _episodes([(2, 1, 1970, 1980, "divorce", 5)])]
    )
    result = lm.lifetime_payroll_tax_pv_at_62(
        careers,
        _persons({1: 1950, 2: 1950}),
        params,
        shared=True,
        rates=_rates(10.0),
        interest=_interest(0.0),
        marriage_episodes=episodes,
        marriage_history_person_ids=[1],
    )
    frame = result.frame.set_index("person_id")
    assert frame.at[1, "married_years_spouse_record_disagrees"] == 1
    assert _pv(result, 1) == pytest.approx(20.0)
    assert _pv(result, 2) == pytest.approx(30.0)
    assert not bool(frame.at[1, "marriage_history_absent"])
    assert bool(frame.at[2, "marriage_history_absent"])


def test_interest_gaps_refuse_or_mark_and_extension_is_named():
    params = _params()
    careers = _careers({1: {2000: 1_000.0}})
    persons = _persons({1: 1970})  # reference year 2032
    interest = _interest(3.0, first=1990, last=2025)
    with pytest.raises(ValueError, match="2026-2032"):
        lm.lifetime_payroll_tax_pv_at_62(
            careers,
            persons,
            params,
            shared=False,
            rates=_rates(),
            interest=interest,
        )
    marked = lm.lifetime_payroll_tax_pv_at_62(
        careers,
        persons,
        params,
        shared=False,
        rates=_rates(),
        interest=interest,
        missing_rate=lm.MissingRatePolicy.NOT_COMPUTED,
    )
    assert marked.frame.at[0, "reason"] == "interest_rate_unavailable:2026"
    extended = interest.extended(
        dict.fromkeys(range(2026, 2033), 3.0), source="INVENTED test path"
    )
    computed = lm.lifetime_payroll_tax_pv_at_62(
        careers,
        persons,
        params,
        shared=False,
        rates=_rates(),
        interest=extended,
    )
    assert _pv(computed, 1) == pytest.approx(
        1_000.0 * 0.12 * 1.03**32, rel=1e-12
    )
    record = computed.provenance["interest_rates"]
    assert record["assumed_years"] == list(range(2026, 2033))
    assert record["assumption_source"] == "INVENTED test path"
    with pytest.raises(ValueError, match="already have rates"):
        interest.extended({2000: 1.0}, source="x")
    with pytest.raises(ValueError, match="named source"):
        interest.extended({2030: 1.0}, source=" ")


@SETTINGS
@given(st.integers(1940, 2100), st.integers(1940, 2100))
def test_accumulation_factors_compose_and_invert(t, y):
    interest = _interest(4.0, first=1940, last=2100)
    forward = lm.accumulation_factor(t, y, interest)
    backward = lm.accumulation_factor(y, t, interest)
    assert forward * backward == pytest.approx(1.0, rel=1e-12)
    assert forward == pytest.approx(1.04 ** (y - t), rel=1e-12)


def test_tax_rate_bases_from_an_invented_document():
    document = {
        "rows": [
            {
                "first_year": 1937,
                "last_year": 1983,
                "employee_employer_each": {"total": 5.0},
            },
            {
                "first_year": 1984,
                "last_year": 1989,
                "employee_employer_each": {"total": 6.0},
            },
            {
                "first_year": 1990,
                "last_year": None,
                "employee_employer_each": {"total": 7.0},
            },
        ],
        "paid_rate_adjustments": [
            {
                "year": 1984,
                "employee_effective_rate": 5.5,
                "employer_rate": 6.0,
            }
        ],
    }
    received = lm.OASDITaxRates.from_document(document)
    paid = lm.OASDITaxRates.from_document(
        document, basis=lm.TaxRateBasis.EMPLOYEE_EMPLOYER_PAID
    )
    assert received.combined_percent_for(1984) == 12.0
    assert paid.combined_percent_for(1984) == 11.5
    assert paid.combined_percent_for(1985) == 12.0
    assert received.combined_percent_for(2050) == 14.0
    with pytest.raises(KeyError):
        received.combined_for(1936)


def test_annual_taxes_cap_each_year_at_its_base():
    params = _params()
    taxes = lm.annual_payroll_taxes(
        _careers({1: {1980: 50_000.0, 1995: 50_000.0}}), params, _rates(10.0)
    )
    assert taxes["taxable_earnings"].tolist() == [14_100.0, 50_000.0]
    assert taxes["tax"].tolist() == pytest.approx([1_410.0, 5_000.0])


# ---------------------------------------------------------------------------
# 3. The Report's average indexed earnings at ages 22-62
# ---------------------------------------------------------------------------
@SETTINGS
@given(histories_strategy, st.integers(1930, 1990))
def test_report_average_matches_the_oracle_indexing(history, birth):
    """Differential against ss.benefits.indexed_history (uncapped)."""
    params = _params()
    window = {
        y: e for y, e in history.items() if birth + 22 <= y <= birth + 62
    }
    frame = lm.report_average_indexed_earnings_22_62(
        _careers({1: history}), _persons({1: birth}), params, shared=False
    ).frame
    if not window:
        assert frame.at[0, "reason"] == "no_career_rows_at_ages_22_62"
        return
    indexed = benefits.indexed_history(window, birth, params)
    expected = math.fsum(indexed[y] for y in sorted(indexed)) / len(window)
    assert frame.at[0, "average_indexed_earnings"] == expected
    assert frame.at[0, "n_ages_covered"] == len(window)
    assert bool(frame.at[0, "ages_complete"]) == (len(window) == 41)
    all_ages = lm.report_average_indexed_earnings_22_62(
        _careers({1: history}),
        _persons({1: birth}),
        params,
        shared=False,
        conventions=lm.ReportEarningsConventions(
            divisor=lm.AverageDivisor.ALL_AGES
        ),
    ).frame
    assert all_ages.at[0, "average_indexed_earnings"] == pytest.approx(
        expected * len(window) / 41, rel=1e-12
    )


def test_report_average_example_and_cap_option():
    # INVENTED: flat NAWI, so indexing is neutral.  Born 1950: ages 22-62
    # are 1972-2012.  Rows in 1971 (age 21) and 2013 (age 63) fall out.
    params = SSAParameters(
        nawi={y: 10_000.0 for y in range(1951, 2071)},
        wage_base={1937: 60_000.0},
        pia_factors=(0.9, 0.32, 0.15),
        fra_months_by_birth_year=[(1900, 792)],
        early_monthly_rates=(5 / 900, 5 / 1200),
        early_first_bracket_months=36,
        pe_us_revision="INVENTED",
    )
    careers = _careers(
        {1: {1971: 1e9, 1980: 100_000.0, 1990: 20_000.0, 2013: 1e9}}
    )
    own = lm.report_average_indexed_earnings_22_62(
        careers, _persons({1: 1950}), params, shared=False
    ).frame
    assert own.at[0, "average_indexed_earnings"] == 60_000.0
    capped = lm.report_average_indexed_earnings_22_62(
        careers,
        _persons({1: 1950}),
        params,
        shared=False,
        conventions=lm.ReportEarningsConventions(cap_at_taxable_maximum=True),
    ).frame
    assert capped.at[0, "average_indexed_earnings"] == 40_000.0


@SETTINGS
@given(histories_strategy, histories_strategy, st.integers(1930, 1980))
def test_report_shared_couple_conserves_the_sum_over_common_years(a, b, birth):
    """With identical covered years, the couple's shared averages sum to
    their own averages."""
    years = sorted(set(a) | set(b))
    a = {y: a.get(y, 0.0) for y in years}
    b = {y: b.get(y, 0.0) for y in years}
    params = _params()
    careers = _careers({1: a, 2: b})
    persons = _persons({1: birth, 2: birth})
    own = lm.report_average_indexed_earnings_22_62(
        careers, persons, params, shared=False
    ).frame
    shared = lm.report_average_indexed_earnings_22_62(
        careers,
        persons,
        params,
        shared=True,
        marriage_episodes=_couple(1930),
    ).frame
    assert shared["status"].tolist() == own["status"].tolist()
    if (own["status"] == lm.COMPUTED).all():
        assert shared["average_indexed_earnings"].sum() == pytest.approx(
            own["average_indexed_earnings"].sum(), rel=1e-12
        )


def test_report_conventions_are_recorded_or_registered():
    provenance = lm.report_average_indexed_earnings_22_62(
        _careers({1: {2000: 1.0}}),
        _persons({1: 1960}),
        _params(),
        shared=False,
    ).provenance
    assert "ages 22-62" in provenance["conventions"]["recorded"]["measure"]
    defaults = provenance["conventions"]["builder_defaults"]
    for key in ("wage_index", "divisor", "shared_rule", "index_age"):
        assert key in defaults
    assert provenance["conventions"]["conventions"]["divisor"] == (
        "covered_ages"
    )


# ---------------------------------------------------------------------------
# Schemes and provenance
# ---------------------------------------------------------------------------
def test_boomers2004_scheme_is_unregistered_and_refuses():
    from populace_dynamics.estimates.uniform_cut_tabulation import (
        NOT_COMPUTED_REPORT_ROWS,
    )

    scheme = lm.boomers2004_scheme()
    assert not scheme.registered
    for dimension in scheme.dimensions:
        record = NOT_COMPUTED_REPORT_ROWS[dimension.key]
        assert dimension.section == record["section"]
        with pytest.raises(ValueError, match="highest quintile"):
            dimension.labels()
        with pytest.raises(ValueError, match="population"):
            dimension.cells(pd.Series([1940]))


def test_results_carry_provenance_and_output_digest():
    result = lm.lifetime_payroll_tax_pv_at_62(
        _careers({1: {2000: 1_000.0}}),
        _persons({1: 1950, 2: 1960}),
        _params(),
        shared=False,
        rates=_rates(),
        interest=_interest(),
    )
    record = result.provenance
    assert record["schema_version"] == lm.SCHEMA_VERSION
    assert record["status_counts"] == {"computed": 1, "not computed": 1}
    assert record["reason_counts"] == {"no_career_rows": 1, "none": 1}
    assert len(record["output_sha256"]) == 64
    assert record["conventions"]["builder_defaults"] == (
        lm.PAYROLL_TAX_BUILDER_DEFAULTS
    )
    again = lm.lifetime_payroll_tax_pv_at_62(
        _careers({1: {2000: 1_000.0}}),
        _persons({1: 1950, 2: 1960}),
        _params(),
        shared=False,
        rates=_rates(),
        interest=_interest(),
    )
    assert again.provenance == record


def test_shared_measures_need_marriage_episodes():
    with pytest.raises(ValueError, match="marriage_episodes"):
        lm.lifetime_payroll_tax_pv_at_62(
            _careers({1: {2000: 1.0}}),
            _persons({1: 1950}),
            _params(),
            shared=True,
            rates=_rates(),
            interest=_interest(),
        )
    with pytest.raises(ValueError, match="marriage_episodes"):
        lm.report_average_indexed_earnings_22_62(
            _careers({1: {2000: 1.0}}),
            _persons({1: 1950}),
            _params(),
            shared=True,
        )
