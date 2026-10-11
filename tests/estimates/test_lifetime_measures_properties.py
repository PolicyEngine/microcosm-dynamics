"""Adversarial lifetime-measure invariants on INVENTED inputs (unit tier).

No source data is loaded. Parameters, careers, marriage episodes, and rate
schedules are all INVENTED. Different-age spouses conserve shared taxes
after their age-62 present values are expressed at a common date. Missing
observations remain distinct from observed zero earnings; post-62 AIME
earnings follow the explicitly selected oracle convention.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.estimates import lifetime_measures as lm
from populace_dynamics.ss import benefits, statutory_aime
from populace_dynamics.ss.params import SSAParameters

PROPERTY_SETTINGS = settings(max_examples=25, deadline=None)


@dataclass(frozen=True)
class _Rates:
    """INVENTED combined employee/employer payroll rate."""

    value: float = 0.1

    def combined_for(self, year: int) -> float:
        return self.value


@dataclass(frozen=True)
class _Interest:
    """INVENTED constant annual interest rate."""

    value: float = 0.03

    def rate_for(self, year: int) -> float:
        return self.value


def _sparse_report_conventions() -> lm.ReportEarningsConventions:
    """Explicit INVENTED sparse-history sensitivity for these fixtures."""
    return lm.ReportEarningsConventions(
        divisor=lm.AverageDivisor.COVERED_AGES,
        missing_spouse=lm.MissingSpousePolicy.OWN_ONLY,
    )


def _params() -> SSAParameters:
    """INVENTED flat wage index and contribution/benefit base."""
    return SSAParameters(
        nawi={year: 100.0 for year in range(1951, 2101)},
        wage_base={1937: 10_000.0},
        pia_factors=(0.9, 0.32, 0.15),
        fra_months_by_birth_year=[(1900, 792)],
        early_monthly_rates=(5 / 900, 5 / 1200),
        early_first_bracket_months=36,
        pe_us_revision="INVENTED",
    )


def _persons(birth1: int = 1950, birth2: int = 1950) -> pd.DataFrame:
    return pd.DataFrame({"person_id": [1, 2], "birth_year": [birth1, birth2]})


def _careers(rows: list[tuple[int, int, float]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows, columns=["person_id", "year", "earnings"])
    frame["provenance"] = "INVENTED"
    return frame


def _episodes() -> pd.DataFrame:
    """INVENTED reciprocal marriage, intact from 1970 onward."""
    return pd.DataFrame(
        {
            "person_id": [1, 2],
            "marriage_order": [1, 1],
            "start_year": pd.array([1970, 1970], dtype="Int64"),
            "episode_end_year": pd.array([None, None], dtype="Int64"),
            "how_ended": ["intact", "intact"],
            "spouse_person_id": pd.array([2, 1], dtype="Int64"),
        }
    )


@PROPERTY_SETTINGS
@given(
    st.integers(1940, 1955),
    st.integers(1, 10),
    st.lists(st.integers(0, 9_000), min_size=8, max_size=8),
)
def test_different_age_couple_conserves_pv_at_a_common_date(
    birth, gap, earnings
):
    """Sharing conserves the couple's sum at one valuation date.

    Comparing a raw sum of values at different age-62 years would compare
    amounts measured at different dates, and is not a conservation law.
    """
    careers = _careers(
        [
            (1, 1985 + offset, value)
            for offset, value in enumerate(earnings[:4])
        ]
        + [
            (2, 1987 + offset, value)
            for offset, value in enumerate(earnings[4:])
        ]
    )
    persons = _persons(birth, birth + gap)
    args = {
        "rates": _Rates(),
        "interest": _Interest(),
    }
    own = lm.lifetime_payroll_tax_pv_at_62(
        careers, persons, _params(), shared=False, **args
    ).frame.set_index("person_id")
    shared = lm.lifetime_payroll_tax_pv_at_62(
        careers,
        persons,
        _params(),
        shared=True,
        marriage_episodes=_episodes(),
        **args,
    ).frame.set_index("person_id")
    common_year = birth + gap + 62

    def common_value(frame: pd.DataFrame) -> float:
        return sum(
            frame.at[pid, "pv_at_62"]
            * 1.03 ** (common_year - frame.at[pid, "reference_year"])
            for pid in [1, 2]
        )

    assert shared["status"].tolist() == [lm.COMPUTED, lm.COMPUTED]
    assert common_value(shared) == pytest.approx(
        common_value(own), rel=1e-12, abs=1e-12
    )


def test_different_age_raw_pv_sums_are_not_a_conservation_law():
    careers = _careers([(1, 2000, 1_000.0), (2, 2000, 3_000.0)])
    persons = _persons(1940, 1950)
    own = lm.lifetime_payroll_tax_pv_at_62(
        careers,
        persons,
        _params(),
        shared=False,
        rates=_Rates(),
        interest=_Interest(),
    ).frame
    shared = lm.lifetime_payroll_tax_pv_at_62(
        careers,
        persons,
        _params(),
        shared=True,
        marriage_episodes=_episodes(),
        rates=_Rates(),
        interest=_Interest(),
    ).frame
    assert shared["pv_at_62"].sum() != pytest.approx(own["pv_at_62"].sum())


@pytest.mark.parametrize("measure", ["aime", "payroll", "report"])
def test_measures_leave_input_frames_and_parameters_unchanged(measure):
    careers = _careers([(2, 2001, 3_000.0), (1, 2000, 1_000.0)])
    persons = _persons()
    episodes = _episodes().iloc[::-1].copy()
    params = _params()
    snapshots = [
        frame.copy(deep=True) for frame in [careers, persons, episodes]
    ]
    nawi, wage_base = dict(params.nawi), dict(params.wage_base)
    if measure == "aime":
        lm.initial_aime_at_62(
            careers,
            persons,
            params,
            analysis_year=2030,
            convention=lm.AIME_CONVENTIONS["mint8_initial_aime"],
        )
    elif measure == "payroll":
        lm.lifetime_payroll_tax_pv_at_62(
            careers,
            persons,
            params,
            shared=True,
            marriage_episodes=episodes,
            rates=_Rates(),
            interest=_Interest(),
        )
    else:
        lm.report_average_indexed_earnings_22_62(
            careers,
            persons,
            params,
            shared=True,
            marriage_episodes=episodes,
            conventions=_sparse_report_conventions(),
        )
    for original, snapshot in zip(
        [careers, persons, episodes], snapshots, strict=True
    ):
        pd.testing.assert_frame_equal(original, snapshot)
    assert params.nawi == nawi
    assert params.wage_base == wage_base


def test_payroll_shares_union_years_and_counts_absent_spouse_years():
    """An absent spouse-year uses the registered zero-year convention.

    Both spouses have careers; neither is counted as unavailable. Each
    receives half of each observed tax year, including spouse-only years.
    """
    result = lm.lifetime_payroll_tax_pv_at_62(
        _careers([(1, 2000, 1_000.0), (2, 2001, 3_000.0)]),
        _persons(),
        _params(),
        shared=True,
        marriage_episodes=_episodes(),
        rates=_Rates(),
        interest=_Interest(0.0),
    )
    assert result.frame["pv_at_62"].tolist() == [200.0, 200.0]
    assert result.frame["married_years_shared"].tolist() == [2, 2]
    assert result.frame["married_years_spouse_year_absent"].tolist() == [1, 1]
    assert result.frame["married_years_own_year_absent"].tolist() == [1, 1]
    assert result.frame["married_years_spouse_unavailable"].tolist() == [0, 0]


def test_report_sharing_uses_own_covered_age_support_and_counts_gaps():
    """The report's covered-age divisor does not fill a missing own row."""
    result = lm.report_average_indexed_earnings_22_62(
        _careers([(1, 2000, 1_000.0), (2, 2001, 3_000.0)]),
        _persons(),
        _params(),
        shared=True,
        marriage_episodes=_episodes(),
        conventions=_sparse_report_conventions(),
    )
    assert result.frame["average_indexed_earnings"].tolist() == [
        500.0,
        1_500.0,
    ]
    assert result.frame["n_ages_covered"].tolist() == [1, 1]
    assert result.frame["married_years_spouse_year_absent"].tolist() == [1, 1]


def test_zero_earnings_are_computed_but_an_absent_history_is_not():
    careers = _careers([(1, 2000, 0.0)])
    persons = _persons()
    results_and_values = [
        (
            lm.initial_aime_at_62(
                careers,
                persons,
                _params(),
                analysis_year=2030,
                convention=lm.AIME_CONVENTIONS["mint8_initial_aime"],
            ),
            "aime",
        ),
        (
            lm.lifetime_payroll_tax_pv_at_62(
                careers,
                persons,
                _params(),
                shared=False,
                rates=_Rates(),
                interest=_Interest(),
            ),
            "pv_at_62",
        ),
        (
            lm.report_average_indexed_earnings_22_62(
                careers,
                persons,
                _params(),
                shared=False,
                conventions=_sparse_report_conventions(),
            ),
            "average_indexed_earnings",
        ),
    ]
    for result, column in results_and_values:
        frame = result.frame.set_index("person_id")
        assert frame.at[1, "status"] == lm.COMPUTED
        assert frame.at[1, column] == 0.0
        assert frame.at[2, "status"] == lm.NOT_COMPUTED
        assert pd.isna(frame.at[2, column])


@pytest.mark.parametrize("name", list(lm.AIME_CONVENTIONS))
def test_post62_earnings_follow_named_oracle_and_are_counted(name):
    """Differential: initial statutory cutoff and legacy full history."""
    params = _params()
    history = {2000: 1_000.0, 2012: 5_000.0, 2015: 9_000.0}
    convention = lm.AIME_CONVENTIONS[name]
    row = lm.initial_aime_at_62(
        _careers([(1, year, value) for year, value in history.items()]),
        _persons(),
        params,
        analysis_year=2020,
        convention=convention,
    ).frame.iloc[0]
    if convention.last_earnings_age is None:
        expected = benefits.aime(history, 1950, params)
        assert row["n_history_years_after_age_61"] == 2
    else:
        expected = statutory_aime.aime({2000: 1_000.0}, 1950, params)
        assert row["n_history_years_after_age_61"] == 0
    assert row["aime"] == expected


@PROPERTY_SETTINGS
@given(
    st.lists(st.integers(1, 10_000), min_size=2, max_size=25),
    st.floats(0.01, 10_000.0, allow_nan=False, allow_infinity=False),
)
def test_quintiles_are_invariant_to_inexact_positive_weight_scaling(
    weights, factor
):
    """Scale changes preserve labels even when floats round differently."""
    values = pd.Series(range(len(weights)), dtype="float64")
    base = pd.Series(weights, dtype="float64")
    pd.testing.assert_series_equal(
        lm.weighted_quintiles(values, base),
        lm.weighted_quintiles(values, base * factor),
    )


def test_quintile_midpoint_boundary_survives_decimal_weight_scaling():
    """The first group's midpoint is exactly the twenty-percent cut.

    Binary representations of 1.2 and 1.8 must not move the row below
    that cut after multiplying the weights by the positive factor 0.3.
    """
    values = pd.Series([1.0, 2.0])
    weights = pd.Series([4.0, 6.0])
    original = lm.weighted_quintiles(values, weights)
    scaled = lm.weighted_quintiles(values, weights * 0.3)
    assert original.tolist() == ["Second lowest", "Second highest"]
    pd.testing.assert_series_equal(original, scaled)


def test_overlapping_marriages_use_latest_start_and_flag_ambiguity():
    episodes = pd.concat(
        [
            _episodes(),
            pd.DataFrame(
                {
                    "person_id": [1],
                    "marriage_order": [2],
                    "start_year": pd.array([1990], dtype="Int64"),
                    "episode_end_year": pd.array([None], dtype="Int64"),
                    "how_ended": ["intact"],
                    "spouse_person_id": pd.array([3], dtype="Int64"),
                }
            ),
        ],
        ignore_index=True,
    )
    result = lm.lifetime_payroll_tax_pv_at_62(
        _careers([(1, 2000, 1_000.0), (2, 2000, 3_000.0), (3, 2000, 5_000.0)]),
        _persons(),
        _params(),
        shared=True,
        marriage_episodes=episodes,
        rates=_Rates(),
        interest=_Interest(0.0),
    )
    frame = result.frame.set_index("person_id")
    assert frame.at[1, "pv_at_62"] == 300.0
    assert frame.at[1, "years_multiple_marriages_in_force"] == 1


@pytest.mark.parametrize("measure", ["payroll", "report"])
def test_unrecorded_sharing_conventions_are_explicit(measure):
    if measure == "payroll":
        defaults = lm.PAYROLL_TAX_BUILDER_DEFAULTS
    else:
        defaults = lm.REPORT_EARNINGS_BUILDER_DEFAULTS
    for key in (
        "reciprocal_history_disagreement",
        "missing_spouse_year",
        "missing_own_year",
    ):
        assert defaults[key].strip()


@pytest.mark.parametrize("measure", ["aime", "payroll", "report"])
@pytest.mark.parametrize("schedule", ["nawi", "wage_base"])
def test_parameter_provenance_pins_changed_paths_with_same_revision(
    measure, schedule
):
    """Replacing a parameter path cannot retain its old source fingerprint.

    An alternate wage projection or cap path may be supplied without
    changing the parameter repository revision. Every result distinguishes
    those paths, including parameters that do not affect that measure.
    """
    careers = _careers([(1, 2000, 15_000.0)])
    persons = _persons()
    original = _params()
    if schedule == "nawi":
        changed = replace(original, nawi={**original.nawi, 2010: 200.0})
    else:
        changed = replace(
            original, wage_base={**original.wage_base, 1970: 5_000.0}
        )

    def run(params: SSAParameters) -> lm.MeasureResult:
        if measure == "aime":
            return lm.initial_aime_at_62(
                careers,
                persons,
                params,
                analysis_year=2030,
                convention=lm.AIME_CONVENTIONS["mint8_initial_aime"],
            )
        if measure == "payroll":
            return lm.lifetime_payroll_tax_pv_at_62(
                careers,
                persons,
                params,
                shared=False,
                rates=_Rates(),
                interest=_Interest(),
            )
        return lm.report_average_indexed_earnings_22_62(
            careers,
            persons,
            params,
            shared=False,
            conventions=_sparse_report_conventions(),
        )

    before, after = run(original), run(changed)
    before_source = before.provenance["ssa_parameters"]
    after_source = after.provenance["ssa_parameters"]
    assert before_source["pe_us_revision"] == after_source["pe_us_revision"]
    assert (
        before_source[f"{schedule}_sha256"]
        != after_source[f"{schedule}_sha256"]
    )
    other = "wage_base" if schedule == "nawi" else "nawi"
    assert before_source[f"{other}_sha256"] == after_source[f"{other}_sha256"]
    if (measure == "report" and schedule == "wage_base") or (
        measure == "payroll" and schedule == "nawi"
    ):
        pd.testing.assert_frame_equal(before.frame, after.frame)
    else:
        assert (
            before.provenance["output_sha256"]
            != after.provenance["output_sha256"]
        )


@pytest.mark.parametrize("schedule", ["tax", "interest"])
def test_payroll_provenance_pins_supplied_rates_without_metadata(schedule):
    """Callable rate sources with identical empty metadata remain distinct."""
    careers = _careers([(1, 2000, 1_000.0)])
    persons = _persons()
    original_rates, changed_rates = _Rates(), _Rates(0.2)
    original_interest, changed_interest = _Interest(), _Interest(0.06)
    before = lm.lifetime_payroll_tax_pv_at_62(
        careers,
        persons,
        _params(),
        shared=False,
        rates=original_rates,
        interest=original_interest,
    )
    after = lm.lifetime_payroll_tax_pv_at_62(
        careers,
        persons,
        _params(),
        shared=False,
        rates=changed_rates if schedule == "tax" else original_rates,
        interest=(
            changed_interest if schedule == "interest" else original_interest
        ),
    )
    hashes = {
        "tax": ("tax_rates", "applied_rates_sha256"),
        "interest": ("interest_rates", "available_rates_sha256"),
    }
    source, key = hashes[schedule]
    assert before.provenance[source][key] != after.provenance[source][key]
    other = "interest" if schedule == "tax" else "tax"
    source, key = hashes[other]
    assert before.provenance[source][key] == after.provenance[source][key]
    assert before.frame.at[0, "pv_at_62"] != after.frame.at[0, "pv_at_62"]


def test_quintile_summary_refuses_misaligned_cell_index():
    values = pd.Series([100.0, 200.0], index=[1, 2])
    weights = pd.Series([1.0, 1.0], index=[1, 2])
    labels = lm.weighted_quintiles(values, weights)
    with pytest.raises(ValueError, match="by must share"):
        lm.quintile_summary(
            labels, weights, by=pd.Series(["a", "b"], index=[2, 1])
        )


@pytest.mark.parametrize("measure", ["aime", "report"])
@pytest.mark.parametrize("year", [2000, 2010])
@pytest.mark.parametrize("value", [0.0, -1.0, float("nan"), float("inf")])
def test_indexing_refuses_nonpositive_or_nonfinite_nawi(measure, year, value):
    """Both source-year and indexing-year NAWI must be finite and positive."""
    original = _params()
    params = replace(original, nawi={**original.nawi, year: value})
    careers = _careers([(1, 2000, 1_000.0)])
    with pytest.raises(ValueError, match="NAWI.*finite and positive"):
        if measure == "aime":
            lm.initial_aime_at_62(
                careers,
                _persons(),
                params,
                analysis_year=2030,
                convention=lm.AIME_CONVENTIONS["mint8_initial_aime"],
            )
        else:
            lm.report_average_indexed_earnings_22_62(
                careers,
                _persons(),
                params,
                shared=False,
                conventions=_sparse_report_conventions(),
            )


@pytest.mark.parametrize(
    "measure", ["aime_statutory", "aime_legacy", "report"]
)
def test_negative_wage_base_is_refused_by_every_capped_measure(measure):
    params = replace(_params(), wage_base={1937: -1.0})
    careers = _careers([(1, 2000, 1_000.0)])
    with pytest.raises(ValueError, match="Wage base.*finite and non-negative"):
        if measure.startswith("aime"):
            name = (
                "mint8_initial_aime"
                if measure == "aime_statutory"
                else "exercise_1_cola"
            )
            lm.initial_aime_at_62(
                careers,
                _persons(),
                params,
                analysis_year=2030,
                convention=lm.AIME_CONVENTIONS[name],
            )
        else:
            lm.report_average_indexed_earnings_22_62(
                careers,
                _persons(),
                params,
                shared=False,
                conventions=lm.ReportEarningsConventions(
                    cap_at_taxable_maximum=True,
                    divisor=lm.AverageDivisor.COVERED_AGES,
                ),
            )


@pytest.mark.parametrize(
    "column",
    [
        "person_id",
        "marriage_order",
        "start_year",
        "episode_end_year",
        "spouse_person_id",
        "separation_year",
    ],
)
def test_fractional_episode_coordinates_are_refused(column):
    """A fractional year or identifier must never be silently truncated."""
    episodes = _episodes()
    if column == "separation_year":
        episodes[column] = pd.Series([None, None], dtype="float64")
    else:
        episodes[column] = episodes[column].astype("float64")
    episodes.at[0, column] = 2000.5
    with pytest.raises(ValueError, match="must hold integers"):
        lm.lifetime_payroll_tax_pv_at_62(
            _careers([(1, 2000, 1_000.0), (2, 2000, 3_000.0)]),
            _persons(),
            _params(),
            shared=True,
            marriage_episodes=episodes,
            rates=_Rates(),
            interest=_Interest(),
        )


def test_duplicate_episode_orders_are_refused():
    episodes = _episodes()
    episodes = pd.concat([episodes, episodes.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate marriage orders"):
        lm.lifetime_payroll_tax_pv_at_62(
            _careers([(1, 2000, 1_000.0), (2, 2000, 3_000.0)]),
            _persons(),
            _params(),
            shared=True,
            marriage_episodes=episodes,
            rates=_Rates(),
            interest=_Interest(),
        )


@pytest.mark.parametrize("rate", [float("nan"), float("inf"), -0.1])
def test_annual_taxes_refuse_invalid_schedule_rates(rate):
    with pytest.raises(ValueError):
        lm.annual_payroll_taxes(
            _careers([(1, 2000, 1_000.0)]), _params(), _Rates(rate)
        )


@pytest.mark.parametrize("rate", [float("nan"), float("inf"), -1.0, -1.01])
@pytest.mark.parametrize("years", [(2000, 2001), (2001, 2000)])
def test_accumulation_refuses_invalid_interest_in_both_directions(rate, years):
    with pytest.raises(ValueError):
        lm.accumulation_factor(*years, _Interest(rate))


def test_returned_provenance_cannot_change_later_results():
    def run():
        return lm.report_average_indexed_earnings_22_62(
            _careers([(1, 2000, 1_000.0)]),
            _persons(),
            _params(),
            shared=False,
            conventions=_sparse_report_conventions(),
        )

    first = run()
    expected = first.provenance["conventions"]["builder_defaults"]["divisor"]
    first.provenance["conventions"]["builder_defaults"]["divisor"] = "edited"
    assert run().provenance["conventions"]["builder_defaults"]["divisor"] == (
        expected
    )


def test_summary_keeps_empty_quintiles_for_disclosure():
    weights = pd.Series([1.0])
    labels = lm.weighted_quintiles(pd.Series([100.0]), weights)
    summary = lm.quintile_summary(labels, weights).set_index("label")
    for label in lm.QUINTILE_LABELS:
        assert summary.at[label, "n"] == int(label == "Middle")
    assert summary.at["Lowest", "weight"] == 0
    assert summary.at["Lowest", "weight_share"] == 0


def test_summary_all_missing_values_has_undefined_weight_shares():
    weights = pd.Series([1.0])
    labels = lm.weighted_quintiles(pd.Series([float("nan")]), weights)
    summary = lm.quintile_summary(labels, weights)
    assert summary["weight_share"].isna().all()
    assert summary.loc[summary["label"] == lm.NOT_COMPUTED, "n"].item() == 1


@pytest.mark.parametrize("measure", ["payroll", "report"])
def test_marriage_history_roster_is_pinned(measure):
    def run(roster):
        args = {
            "shared": True,
            "marriage_episodes": _episodes(),
            "marriage_history_person_ids": roster,
        }
        if measure == "payroll":
            return lm.lifetime_payroll_tax_pv_at_62(
                _careers([(1, 2000, 1_000.0)]),
                _persons(),
                _params(),
                rates=_Rates(),
                interest=_Interest(),
                **args,
            )
        return lm.report_average_indexed_earnings_22_62(
            _careers([(1, 2000, 1_000.0)]),
            _persons(),
            _params(),
            **args,
            conventions=_sparse_report_conventions(),
        )

    before, reordered, changed = run([1, 2]), run([2, 1]), run([1])
    assert before.provenance["inputs"] == reordered.provenance["inputs"]
    key = "marriage_history_person_ids_sha256"
    assert (
        before.provenance["inputs"][key] != changed.provenance["inputs"][key]
    )


@pytest.mark.parametrize("measure", ["payroll", "report"])
def test_shared_switch_refuses_truthy_text(measure):
    args = {"shared": "False"}
    with pytest.raises(TypeError, match="shared must be a bool"):
        if measure == "payroll":
            lm.lifetime_payroll_tax_pv_at_62(
                _careers([(1, 2000, 1_000.0)]),
                _persons(),
                _params(),
                rates=_Rates(),
                interest=_Interest(),
                **args,
            )
        else:
            lm.report_average_indexed_earnings_22_62(
                _careers([(1, 2000, 1_000.0)]),
                _persons(),
                _params(),
                **args,
                conventions=_sparse_report_conventions(),
            )
