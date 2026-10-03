"""INVENTED DATA - NOT A COMPARISON: exercise-2 adapter invariants.

All frames and measure stubs here are invented. These tests call no reader,
load no committed outcome and do not execute a real-data pipeline.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pandas.testing import assert_frame_equal

from populace_dynamics.cohorts import age67
from populace_dynamics.cohorts import group_attributes as ga
from populace_dynamics.estimates import group_breakdown as gb
from populace_dynamics.estimates import lifetime_measures as lm
from populace_dynamics.estimates import uniform_cut_tabulation as ut
from populace_dynamics.group_breakdowns import uniform_cut as adapter
from populace_dynamics.group_breakdowns.common import GroupBreakdownRefusal
from populace_dynamics.ss.params import SSAParameters

FAST = settings(max_examples=20, deadline=None)
TABULATIONS = settings(max_examples=8, deadline=None)


def _inputs(
    careers: pd.DataFrame, person_ids: tuple[int, ...] = (1, 2)
) -> age67.Age67Inputs:
    """An INVENTED materialized cohort input, with known never-married IDs."""

    history = pd.DataFrame(
        {
            "person_id": person_ids,
            "is_marriage": False,
            "marriage_order": pd.array(
                [None] * len(person_ids), dtype="Int64"
            ),
            "start_year": pd.array([None] * len(person_ids), dtype="Int64"),
            "start_month": pd.array([None] * len(person_ids), dtype="Int64"),
            "end_year": pd.array([None] * len(person_ids), dtype="Int64"),
            "separation_year": pd.array(
                [None] * len(person_ids), dtype="Int64"
            ),
            "how_ended": "never_married",
            "spouse_person_id": pd.array(
                [None] * len(person_ids), dtype="Int64"
            ),
            "last_known_status": "never_married",
        }
    )
    return age67.Age67Inputs(
        anchors={},
        design=pd.DataFrame(),
        death_records=pd.DataFrame(),
        marriage_history=history,
        observed_earnings=careers,
        family_income={},
        family_wealth={},
        wealth_refusals={},
        provenance={"kind": "invented"},
    )


def _params() -> SSAParameters:
    """INVENTED flat schedules; G2 calls are stubbed in the cutoff test."""

    return SSAParameters(
        nawi={year: 100.0 for year in range(1951, 2026)},
        wage_base={1937: 10_000.0},
        pia_factors=(0.9, 0.32, 0.15),
        fra_months_by_birth_year=[(1900, 792)],
        early_monthly_rates=(5 / 900, 5 / 1200),
        early_first_bracket_months=36,
        pe_us_revision="INVENTED",
    )


@FAST
@given(st.lists(st.integers(1936, 1945), min_size=1, max_size=15))
def test_valid_observation_births_stay_inside_registered_cohort(births):
    members = pd.DataFrame(
        {
            "observation_id": range(len(births)),
            "person_id": range(1, len(births) + 1),
            "birth_year": births,
            "member_age": 67,
        }
    )
    original = members.copy(deep=True)
    adapter.check_observations(members)
    assert_frame_equal(members, original)


@FAST
@given(st.integers(1946, 2100))
def test_every_held_out_birth_refuses(birth):
    members = pd.DataFrame(
        {
            "observation_id": [1],
            "person_id": [1],
            "birth_year": [birth],
            "member_age": [67],
        }
    )
    with pytest.raises(GroupBreakdownRefusal, match="1936"):
        adapter.check_observations(members)


@FAST
@given(
    st.integers(1936, 1944),
    st.sampled_from((0.125, 0.25, 0.5, 0.75)),
)
def test_fractional_birth_is_not_a_registered_birth_year(birth, fraction):
    members = pd.DataFrame(
        {
            "observation_id": [1],
            "person_id": [1],
            "birth_year": [birth + fraction],
            "member_age": [67],
        }
    )
    with pytest.raises(GroupBreakdownRefusal):
        adapter.check_observations(members)


@FAST
@given(st.data(), st.integers(1, 12))
def test_many_to_one_join_preserves_keys_order_weights_and_inputs(data, n):
    order = data.draw(st.permutations(tuple(range(n))))
    left = pd.DataFrame(
        {
            "observation_id": order,
            "person_id": [i // 2 + 1 for i in order],
            "weight": [float(i + 1) for i in order],
        },
        index=[i + 100 for i in range(n)],
    )
    persons = sorted(set(left["person_id"]))
    right = pd.DataFrame(
        {"person_id": persons[::-1], "invented_group": persons[::-1]}
    )
    original_left, original_right = left.copy(), right.copy()
    joined = adapter._join(left, right, "person_id")
    assert joined["observation_id"].tolist() == left["observation_id"].tolist()
    assert joined["weight"].tolist() == left["weight"].tolist()
    assert joined["invented_group"].tolist() == left["person_id"].tolist()
    assert len(joined) == len(left)
    assert_frame_equal(left, original_left)
    assert_frame_equal(right, original_right)


@FAST
@given(st.integers(1, 10_000))
def test_duplicate_or_missing_side_key_refuses(person_id):
    left = pd.DataFrame({"person_id": [person_id]})
    duplicate = pd.DataFrame(
        {"person_id": [person_id, person_id], "attribute": [1, 1]}
    )
    with pytest.raises(GroupBreakdownRefusal, match="duplicate"):
        adapter._join(left, duplicate, "person_id")
    missing = pd.DataFrame({"person_id": [person_id + 1], "attribute": [1]})
    with pytest.raises(GroupBreakdownRefusal, match="missing"):
        adapter._join(left, missing, "person_id")


def test_join_preserves_and_isolates_the_cohort_source_guard():
    left = pd.DataFrame({"person_id": [1]})
    left.attrs = {"provenance_kind": "psid_files", "audit": {"sealed": True}}
    right = pd.DataFrame({"person_id": [1], "attribute": [None]})
    joined = adapter._join(left, right, "person_id")
    assert joined.attrs == left.attrs
    joined.attrs["audit"]["sealed"] = False
    assert left.attrs["audit"]["sealed"] is True


def _measure_stub(
    value_column: str, calls: list[pd.DataFrame]
) -> Callable[..., lm.MeasureResult]:
    """INVENTED reduction solely to observe the adapter's G2 boundary."""

    def compute(careers, persons, params, **kwargs):
        del params
        calls.append(careers.copy(deep=True))
        totals = careers.groupby("person_id")["earnings"].sum()
        frame = persons[["person_id"]].copy()
        frame[value_column] = frame["person_id"].map(totals)
        frame["status"] = lm.COMPUTED
        if kwargs.get("shared"):
            frame["marriage_history_absent"] = False
            for column in (
                "years_marital_unknown",
                "married_years_spouse_unavailable",
                "married_years_spouse_year_absent",
                "married_years_own_year_absent",
                "married_years_spouse_record_disagrees",
                "years_multiple_marriages_in_force",
            ):
                frame[column] = 0
        return lm.MeasureResult("INVENTED", frame, {"kind": "INVENTED"})

    return compute


@FAST
@given(st.floats(min_value=0.0, max_value=1e9, allow_nan=False))
def test_future_earnings_cannot_enter_any_of_the_five_g2_measures(future):
    members = pd.DataFrame(
        {
            "observation_id": ["early", "later", "second"],
            "person_id": [1, 1, 2],
            "birth_year": [1937, 1937, 1938],
            "income_year": [2003, 2005, 2005],
            "member_age": [66, 68, 67],
        }
    )
    adapter.check_observations(members)
    careers = pd.DataFrame(
        {
            "person_id": [1, 1, 1, 2, 2],
            "period": [2002, 2003, 2005, 2003, 2005],
            "earnings": [10.0, 20.0, 30.0, 40.0, 50.0],
        }
    )
    later = pd.concat(
        [
            careers,
            pd.DataFrame(
                {
                    "person_id": [1, 2],
                    "period": [2020, 2022],
                    "earnings": [future, future],
                }
            ),
        ],
        ignore_index=True,
    )
    calls = []
    supplied = adapter.LifetimeInputs(
        _params(), rates=object(), interest=object()
    )
    with pytest.MonkeyPatch.context() as patch:
        for name, column in (
            ("initial_aime_at_62", "aime"),
            ("lifetime_payroll_tax_pv_at_62", "pv_at_62"),
            (
                "report_average_indexed_earnings_22_62",
                "average_indexed_earnings",
            ),
        ):
            patch.setattr(adapter.lm, name, _measure_stub(column, calls))
        baseline, _ = adapter.lifetime_frame(
            members, _inputs(careers), supplied
        )
        with_future, _ = adapter.lifetime_frame(
            members, _inputs(later), supplied
        )
    assert_frame_equal(baseline, with_future)
    assert set(adapter.MEASURES).issubset(baseline)
    assert len(calls) == 20  # five measures, two years, two input histories
    for position, called in enumerate(calls):
        cutoff = 2003 if position % 10 < 5 else 2005
        assert called["year"].le(cutoff).all()
    assert "year" not in careers and "year" not in later


@pytest.mark.parametrize(
    "reason",
    (
        "marriage_history_absent",
        "years_marital_unknown",
        "married_years_spouse_year_absent",
        "married_years_own_year_absent",
        "married_years_spouse_record_disagrees",
        "years_multiple_marriages_in_force",
    ),
)
def test_incomplete_shared_inputs_remain_unavailable(reason, monkeypatch):
    members = pd.DataFrame(
        {
            "observation_id": ["o1"],
            "person_id": [1],
            "birth_year": [1937],
            "income_year": [2004],
        }
    )
    careers = pd.DataFrame(
        {"person_id": [1], "period": [2000], "earnings": [10.0]}
    )
    for name, column in (
        ("initial_aime_at_62", "aime"),
        ("lifetime_payroll_tax_pv_at_62", "pv_at_62"),
        ("report_average_indexed_earnings_22_62", "average_indexed_earnings"),
    ):
        stub = _measure_stub(column, [])

        def compute(*args, _stub=stub, **kwargs):
            result = _stub(*args, **kwargs)
            if kwargs.get("shared") and reason != "marriage_history_absent":
                result.frame[reason] = 1
            return result

        monkeypatch.setattr(adapter.lm, name, compute)
    inputs = _inputs(
        careers, (2,) if reason == "marriage_history_absent" else (1,)
    )
    side, provenance = adapter.lifetime_frame(
        members,
        inputs,
        adapter.LifetimeInputs(_params(), rates=object(), interest=object()),
    )
    for name in adapter.MEASURES:
        if name.endswith("shared"):
            assert pd.isna(side.loc[0, name])
            record = next(
                r for r in provenance["records"] if r["dimension"] == name
            )
            assert record["adapter_exclusion_counts"][reason] == 1
        else:
            assert side.loc[0, name] == 10.0


def _rows(incomes, weights):
    """INVENTED U1 observations and already-computed poverty flags."""

    births = [1936, 1937, 1940, 1941, 1944, 1945]
    ages = [66, 67, 68, 66, 67, 68]
    members = pd.DataFrame(
        {
            "observation_id": [f"o{i}" for i in range(6)],
            "person_id": range(1, 7),
            "birth_year": births,
            "member_age": ages,
            "income_year": np.array(births) + ages,
            "wave": np.array(births) + ages + 1,
            "family_unit_id": range(1, 7),
            "sex": ["female", "male"] * 3,
            "marital_status_4": [
                "unclassified",
                "married",
                "widowed",
                "divorced",
                "never_married",
                "married",
            ],
            "weight": weights,
            "stratum": 1,
            "cluster": [1, 2, 1, 2, 1, 2],
        }
    )
    money = np.asarray(incomes, dtype=float)
    members["total_family_income"] = money
    adjusted = pd.DataFrame(
        {
            "observation_id": members["observation_id"],
            "baseline_income": money + 5.0,
            "money_income": money,
            "threshold": 100.0,
            "cut": 6.5,
            "ssi_offset": 0.0,
            "ssi_new": 0.0,
            "poor_baseline": money + 5.0 < 100.0,
            "poor_reform": money + 5.0 - 6.5 < 100.0,
        }
    )
    design = pd.DataFrame({"stratum": [1, 1, 1], "cluster": [1, 2, 3]})
    result = {"tabulation": {"config": {"floor_seeds": [0, 1]}}}
    return adapter.ReplayedRow(result, members, adjusted, design)


def _attribute_loader(person_ids, *, anchor_waves):
    """INVENTED G1-shaped labels, including explicitly missing attributes."""

    frame = pd.DataFrame(
        {
            "person_id": person_ids,
            "race_ethnicity_mint8": [
                gb.MINT8_SCHEME.dimension("race_ethnicity")
                .categories[(pid - 1) % 4]
                .label
                for pid in person_ids
            ],
            "country_of_birth_mint8": [
                "United States" if pid % 2 else None for pid in person_ids
            ],
            "education_years": [12 if pid % 2 else None for pid in person_ids],
        }
    )
    return ga.GroupAttributes(
        frame,
        {
            "content_sha256": ga.content_sha256(frame),
            "anchor_waves": list(anchor_waves),
            "kind": "INVENTED",
        },
    )


@TABULATIONS
@given(
    st.lists(st.integers(0, 200), min_size=6, max_size=6),
    st.lists(st.integers(1, 10), min_size=6, max_size=6),
)
def test_adapter_totals_match_frozen_rates_design_se_and_floors(
    incomes, weights
):
    replayed = _rows(incomes, weights)
    original_members = replayed.members.copy(deep=True)
    original_adjusted = replayed.adjusted.copy(deep=True)
    result = adapter.tabulate_row_groups(
        "U1",
        replayed,
        inputs=_inputs(pd.DataFrame(), tuple(range(1, 7))),
        attribute_loader=_attribute_loader,
        lifetime_inputs=None,
        data_provenance="invented",
        registration_pointer=None,
    )
    rows = ut.tabulation_rows(replayed.members, replayed.adjusted)
    reference = ut.tabulate_uniform_cut(
        rows,
        data_provenance="invented",
        design=replayed.design,
        config=ut.TabulationConfig(floor_seeds=(0, 1)),
    )["cells"][0]
    grouped = result["groups"]["adjusted"]
    dimensions = {d["key"]: d for d in grouped["dimensions"]}
    total = dimensions["total"]["cells"][0]
    statistics = {s["statistic"]: s for s in total["statistics"]}
    for name, legacy in (
        (gb.POVERTY_RATE_CURRENT_LAW, "baseline_rate"),
        (gb.POVERTY_RATE_PROPOSAL, "reform_rate"),
        (gb.POVERTY_RATE_CHANGE, "delta"),
    ):
        assert statistics[name]["value"] == reference[legacy]
        assert statistics[name]["uncertainty"]["design_se"] == (
            reference["design_se"][legacy]
        )
        assert statistics[name]["uncertainty"]["floor"] == (
            reference["floor"][legacy]
        )
    assert dimensions["marital_status"]["unclassified"]["n_rows"] == 1
    assert [c["label"] for c in dimensions["age"]["cells"]] == [
        "66",
        "67",
        "68",
    ]
    for dimension in dimensions.values():
        classified = sum(
            c["counts"]["unweighted_n"] for c in dimension["cells"]
        )
        assert classified + dimension["unclassified"]["n_rows"] == 6
    partitions = grouped["assignment"]["quintile_partitions"]
    for name in adapter.MEASURES[:3]:
        assert partitions[name] == ["birth_cohort"]
    assert partitions["household_income_quintile"] == []
    assert_frame_equal(replayed.members, original_members)
    assert_frame_equal(replayed.adjusted, original_adjusted)


@pytest.mark.parametrize("row_id", ("U0", "U1", "U3", "U8"))
def test_scheme_preserves_mint_dimensions_and_states_u1_age_variant(row_id):
    scheme = adapter._scheme(row_id)
    assert scheme.composite
    assert scheme.keys[-5:] == adapter.MEASURES
    for dimension in gb.MINT8_SCHEME.dimensions:
        if row_id == "U1" and dimension.key == "age":
            ages = scheme.dimension("age")
            assert ages.labels == ("66", "67", "68")
            assert [(c.lower, c.upper) for c in ages.categories] == [
                (66, 66),
                (67, 67),
                (68, 68),
            ]
        else:
            assert scheme.dimension(dimension.key) == dimension
