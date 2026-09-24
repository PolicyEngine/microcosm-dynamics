"""Hand-computed cases for the exercise-2 (Track U) tabulation.

Every row here is INVENTED: five made-up observations whose weights and
poverty flags make each rate, change and design-based standard error
workable by hand (the arithmetic is next to each assertion). No value is a
PSID observation, a model output or a comparator value.
"""

from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
import pytest

from populace_dynamics.estimates import uniform_cut_tabulation as ut
from populace_dynamics.estimates.adjusted_poverty import OUTPUT_LABELS
from populace_dynamics.harness.panel import split_panel_by_person


def _rows() -> pd.DataFrame:
    """INVENTED observations (not PSID)."""

    return pd.DataFrame(
        {
            "observation_id": ["o1", "o2", "o3", "o4", "o5"],
            "person_id": [1, 2, 3, 4, 5],
            "family_unit_id": [10, 10, 20, 30, 40],
            "weight": [1.0, 1.0, 2.0, 4.0, 2.0],
            "sex": ["male", "female", "female", "male", "female"],
            "married": [True, True, False, False, False],
            "birth_year": [1941, 1943, 1941, 1945, 1945],
            "stratum": [1, 1, 1, 2, 2],
            "cluster": [1, 1, 2, 1, 2],
            "poor_baseline": [False, False, True, False, False],
            "poor_reform": [False, True, True, True, False],
        }
    )


def _cells(result: dict) -> dict:
    return {entry["cell"]: entry for entry in result["cells"]}


def test_rates_and_changes_by_hand():
    result = ut.tabulate_uniform_cut(_rows(), data_provenance="invented")
    cells = _cells(result)
    expected = {
        # all: W = 10; poor B: o3 (2) -> 20; poor R: o2+o3+o4 (7) -> 70
        "all": (20.0, 70.0, 50.0),
        # men o1, o4: W = 5; R: o4 (4) -> 80
        "men": (0.0, 80.0, 80.0),
        # women o2, o3, o5: W = 5; B: 2 -> 40; R: 1 + 2 -> 60
        "women": (40.0, 60.0, 20.0),
        "married": (0.0, 50.0, 50.0),
        # non-married o3, o4, o5: W = 8; B 2 -> 25; R 6 -> 75
        "non_married": (25.0, 75.0, 50.0),
        "men_married": (0.0, 0.0, 0.0),
        "men_non_married": (0.0, 100.0, 100.0),
        "women_married": (0.0, 100.0, 100.0),
        "women_non_married": (50.0, 50.0, 0.0),
        "birth_year_1941": (200 / 3, 200 / 3, 0.0),
        "birth_year_1943": (0.0, 100.0, 100.0),
        "birth_year_1945": (0.0, 400 / 6, 400 / 6),
    }
    assert set(cells) == set(expected)
    for name, (base, reform, delta) in expected.items():
        assert cells[name]["baseline_rate"] == pytest.approx(base), name
        assert cells[name]["reform_rate"] == pytest.approx(reform), name
        assert cells[name]["delta"] == pytest.approx(delta), name
    assert cells["all"]["n_persons"] == 5
    assert cells["all"]["n_family_units"] == 4
    assert cells["all"]["weight_total"] == 10.0
    assert cells["birth_year_1941"]["diagnostic"]
    assert cells["men"]["scored_candidate"]
    assert cells["men_married"]["optional"]
    json.dumps(result)


def test_design_standard_error_by_hand():
    result = ut.tabulate_uniform_cut(_rows(), data_provenance="invented")
    se = _cells(result)["all"]["design_se"]["delta"]
    # d = R - B: 0, 1, 0, 1, 0; r = .5; z = w (d - r) / 10:
    # -.05, .05, -.1, .2, -.1.  Stratum 1 clusters: 0, -.1 (mean -.05,
    # 2 * (.05^2 + .05^2) = .01); stratum 2: .2, -.1 (mean .05,
    # 2 * (.15^2 + .15^2) = .09).  SE = 100 * sqrt(.1).
    assert se["se"] == pytest.approx(100 * math.sqrt(0.1))
    assert se["n_strata"] == 2
    assert se["n_singleton_strata"] == 0


def test_singleton_strata_are_left_out_and_counted():
    rows = _rows()
    extra = rows.iloc[[0]].copy()
    extra["observation_id"] = "o6"
    extra["person_id"] = 6
    extra["family_unit_id"] = 60
    extra["stratum"] = 3
    rows = pd.concat([rows, extra], ignore_index=True)
    result = ut.tabulate_uniform_cut(rows, data_provenance="invented")
    se = _cells(result)["all"]["design_se"]["delta"]
    assert se["n_singleton_strata"] == 1
    assert se["n_strata"] == 2


def _reference_delta(rows: pd.DataFrame, mask: np.ndarray) -> float | None:
    w = rows["weight"].to_numpy()[mask]
    if not mask.any() or w.sum() <= 0:
        return None
    d = rows["poor_reform"].to_numpy()[mask].astype(float) - rows[
        "poor_baseline"
    ].to_numpy()[mask].astype(float)
    return 100.0 * float(np.sum(w * d)) / float(w.sum())


def test_half_split_floor_uses_family_units():
    rows = _rows()
    result = ut.tabulate_uniform_cut(rows, data_provenance="invented")
    units = pd.DataFrame({"family_unit_id": rows["family_unit_id"].tolist()})
    gaps = []
    for seed in ut.DEFAULT_FLOOR_SEEDS:
        side_a, _ = split_panel_by_person(
            units, "family_unit_id", fraction=0.5, seed=seed
        )
        in_a = np.zeros(len(rows), dtype=bool)
        in_a[side_a.index.to_numpy()] = True
        # o1 and o2 share family unit 10: always on one side
        assert in_a[0] == in_a[1]
        a = _reference_delta(rows, in_a)
        b = _reference_delta(rows, ~in_a)
        if a is not None and b is not None:
            gaps.append(abs(a - b))
    floor = _cells(result)["all"]["floor"]["delta"]
    assert floor["values"] == pytest.approx(gaps)
    assert floor["n_seeds"] == len(gaps)
    if len(gaps) >= 2:
        assert floor["mean"] == pytest.approx(float(np.mean(gaps)))
        assert floor["sd"] == pytest.approx(float(np.std(gaps, ddof=1)))


def _u1_rows() -> pd.DataFrame:
    """INVENTED U1-style rows: person 4 observed again in a second wave.

    Row U1 observes the even birth years at 66 and at 68, in two waves,
    and a wave's family unit id differs from the other wave's, so one
    person carries two family units (o4 in unit 30, o6 in unit 99).
    """

    rows = _rows()
    extra = rows.iloc[[3]].copy()
    extra["observation_id"] = "o6"
    extra["family_unit_id"] = 99
    extra["poor_reform"] = False
    return pd.concat([rows, extra], ignore_index=True)


def test_floor_split_units_link_family_units_through_persons():
    # U0-style rows: every person once, so the split unit is the family
    # unit itself and the split is the family-unit split unchanged.
    rows = _rows()
    assert ut.floor_split_units(rows).tolist() == (
        rows["family_unit_id"].tolist()
    )
    # U1-style rows: person 4's units 30 and 99 merge (smallest id).
    assert ut.floor_split_units(_u1_rows()).tolist() == [
        10,
        10,
        20,
        30,
        40,
        30,
    ]
    # Transitive: person 7 links units 1 and 2, person 8 links 2 and 3.
    chain = pd.DataFrame(
        {"person_id": [7, 7, 8, 8, 9], "family_unit_id": [1, 2, 2, 3, 4]}
    )
    assert ut.floor_split_units(chain).tolist() == [1, 1, 1, 1, 4]


def test_half_split_floor_is_person_disjoint_under_u1():
    """Plan F15: the half-split is person-disjoint as well as unit-wise.

    On the unit-only split, seeds 0 and 3 put person 4's two observations
    (units 30 and 99) on opposite sides.
    """

    rows = _u1_rows()
    result = ut.tabulate_uniform_cut(rows, data_provenance="invented")
    units = pd.DataFrame({"split_unit": ut.floor_split_units(rows)})
    gaps = []
    for seed in ut.DEFAULT_FLOOR_SEEDS:
        side_a, _ = split_panel_by_person(
            units, "split_unit", fraction=0.5, seed=seed
        )
        in_a = np.zeros(len(rows), dtype=bool)
        in_a[side_a.index.to_numpy()] = True
        assert in_a[3] == in_a[5]
        a = _reference_delta(rows, in_a)
        b = _reference_delta(rows, ~in_a)
        if a is not None and b is not None:
            gaps.append(abs(a - b))
    floor = _cells(result)["all"]["floor"]["delta"]
    assert floor["values"] == pytest.approx(gaps)
    assert result["config"]["floor_split_unit"] == ut.FLOOR_SPLIT_UNIT


def test_floor_is_undefined_with_one_family_unit():
    rows = _rows()
    rows["family_unit_id"] = 1
    result = ut.tabulate_uniform_cut(rows, data_provenance="invented")
    floor = _cells(result)["all"]["floor"]["delta"]
    assert floor["defined"] is False
    assert floor["mean"] is None
    assert floor["undefined_reason"] == "no usable seed"
    assert floor["dropped_seeds"] == list(ut.DEFAULT_FLOOR_SEEDS)


def test_undefined_cells_are_reported_not_raised():
    rows = _rows()
    rows["sex"] = "male"
    rows.loc[rows["married"], "weight"] = 0.0
    result = ut.tabulate_uniform_cut(rows, data_provenance="invented")
    undefined = {
        item["cell"]: item["reason"] for item in result["undefined_cells"]
    }
    assert undefined["women"] == "empty cell"
    assert undefined["married"] == "zero total weight"
    assert _cells(result)["all"]["defined"]


def test_invented_results_are_labelled():
    result = ut.tabulate_uniform_cut(_rows(), data_provenance="invented")
    assert result["labels"][0] == ut.INVENTED_DATA_LABEL
    assert set(OUTPUT_LABELS) <= set(result["labels"])
    assert result["config"]["draws"] == 1
    assert result["statistic_id"] == ut.STATISTIC_ID


def test_provenance_guards():
    with pytest.raises(ut.UniformCutTabulationError, match="pointer"):
        ut.tabulate_uniform_cut(_rows(), data_provenance="registered_real")
    with pytest.raises(ut.UniformCutTabulationError, match="invented label"):
        ut.tabulate_uniform_cut(
            _rows(),
            data_provenance="registered_real",
            registration_pointer="#42 (invented pointer)",
            labels=(*OUTPUT_LABELS, ut.INVENTED_DATA_LABEL),
        )
    with pytest.raises(ut.UniformCutTabulationError, match="labels"):
        ut.tabulate_uniform_cut(
            _rows(), data_provenance="invented", labels=("other",)
        )
    rows = _rows()
    rows.attrs["provenance_kind"] = "psid_files"
    with pytest.raises(ut.UniformCutTabulationError, match="PSID"):
        ut.tabulate_uniform_cut(rows, data_provenance="invented")


@pytest.mark.parametrize("kind", [None, "caller_frames", "invented"])
def test_registered_real_needs_rows_built_from_psid_files(kind):
    """A registered_real result must come from sealed PSID-built rows.

    Without this, invented or caller-built rows could be tabulated under
    the registered_real label (Track A's opening refuses the same
    contradiction).
    """

    rows = _rows()
    if kind is not None:
        rows.attrs["provenance_kind"] = kind
    with pytest.raises(ut.UniformCutTabulationError, match="contradicts"):
        ut.tabulate_uniform_cut(
            rows,
            data_provenance="registered_real",
            registration_pointer="#42 (invented pointer)",
        )


@pytest.mark.parametrize(
    "column, value",
    [
        ("weight", -1.0),
        ("sex", "unknown"),
        ("poor_reform", None),
        ("stratum", None),
    ],
)
def test_rows_are_validated(column, value):
    rows = _rows()
    rows[column] = rows[column].astype(object)
    rows.loc[0, column] = value
    with pytest.raises(ut.UniformCutTabulationError):
        ut.tabulate_uniform_cut(rows, data_provenance="invented")


def test_config_validation():
    with pytest.raises(ut.UniformCutTabulationError):
        ut.TabulationConfig(cells=("men",))
    with pytest.raises(ut.UniformCutTabulationError):
        ut.TabulationConfig(cells=("all", "retirees"))
    with pytest.raises(ut.UniformCutTabulationError):
        ut.TabulationConfig(floor_seeds=(0, 0))
