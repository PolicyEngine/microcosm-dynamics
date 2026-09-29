"""Design-based SE and the half-split floor for U2 (section 13).

Groups "Design" (strata 88-94, invalid-design refusal, zero-contribution
clusters, singleton reporting, paired change SE) and "Floor" (transitive
person/family linkage, both observations on one side, undefined floors,
required seed count).  INVENTED DATA - NOT A COMPARISON.
"""

from __future__ import annotations

import dataclasses

import numpy as np
import pandas as pd
import pytest

from populace_dynamics.estimates import adjusted_poverty as ap
from populace_dynamics.estimates import uniform_cut_tabulation as ut
from populace_dynamics.uniform_cut_track_u2 import cohort, tabulation


def _rows(n=40, *, seed=0, target="U2"):
    rng = np.random.default_rng(seed)
    frame = pd.DataFrame(
        {
            "observation_id": [f"{i}:2019" for i in range(n)],
            "person_id": np.arange(n),
            "family_unit_id": 2019 * 100_000 + np.arange(n) // 2,
            "weight": rng.uniform(1, 5, n),
            "sex": np.where(np.arange(n) % 2, "male", "female"),
            "marital_status_4": np.array(
                ["married", "widowed", "divorced", "never_married"]
            )[np.arange(n) % 4],
            "birth_year": 1951,
            "stratum": np.array([1, 2, 88, 94])[np.arange(n) % 4],
            "cluster": np.array([1, 2])[(np.arange(n) // 4) % 2],
        }
    )
    base = rng.random(n) < 0.3
    frame["poor_baseline"] = base
    frame["poor_reform"] = base | (rng.random(n) < 0.2)
    frame.attrs["target_id"] = target
    frame.attrs["provenance_kind"] = "invented"
    return frame


def _design(rows):
    return rows[["stratum", "cluster"]].drop_duplicates()


def test_refresher_strata_88_to_94_are_valid(u2_inputs):
    assert set(range(88, 95)) <= cohort.DESIGN_VALID_STRATA
    assert cohort.DESIGN_VALID_CLUSTERS == frozenset({1, 2})
    frame = cohort.design_frame(u2_inputs, cohort.U2CohortSpec())
    assert set(frame["stratum"]) & set(range(88, 95))


def test_design_domains_equal_the_design_registry(committed_registries):
    stratum = committed_registries.entry("design", "common.stratum")
    cluster = committed_registries.entry("design", "common.cluster")
    assert set(stratum["valid_codes"]) == cohort.DESIGN_VALID_STRATA
    assert set(cluster["valid_codes"]) == cohort.DESIGN_VALID_CLUSTERS


@pytest.mark.parametrize(
    "column, value", [("stratum", 95), ("stratum", 0), ("cluster", 3)]
)
def test_invalid_design_refuses(u2_inputs, column, value):
    design = u2_inputs.design.copy()
    design.loc[design.index[0], column] = value
    changed = cohort.replace_provenance(
        dataclasses.replace(u2_inputs, design=design), kind="caller_frames"
    )
    with pytest.raises(cohort.U2CohortError, match="valid sampling-error"):
        cohort.design_frame(changed, cohort.U2CohortSpec(row="U1"))


def test_positive_weight_person_without_design_refuses(u2_inputs):
    design = u2_inputs.design.iloc[1:]
    changed = cohort.replace_provenance(
        dataclasses.replace(u2_inputs, design=design), kind="caller_frames"
    )
    with pytest.raises(cohort.U2CohortError, match="lack a design"):
        cohort.design_frame(changed, cohort.U2CohortSpec(row="U1"))


def test_zero_contribution_clusters_enter_the_variance():
    rows = _rows()
    design = pd.concat(
        [_design(rows), pd.DataFrame([{"stratum": 1, "cluster": 3}])]
    )
    with_extra = tabulation.tabulate_u2(
        rows, data_provenance=ap.INVENTED, design=design
    )
    plain = tabulation.tabulate_u2(
        rows, data_provenance=ap.INVENTED, design=_design(rows)
    )
    a = next(c for c in with_extra["cells"] if c["cell"] == "all")
    b = next(c for c in plain["cells"] if c["cell"] == "all")
    assert with_extra["design"]["n_clusters"] == plain["design"]["n_clusters"] + 1
    assert a["design_se"]["delta"]["se"] != b["design_se"]["delta"]["se"]


def test_singleton_strata_are_excluded_counted_and_listed():
    rows = _rows()
    rows.loc[rows["stratum"].eq(94), "cluster"] = 1
    table = tabulation.tabulate_u2(
        rows, data_provenance=ap.INVENTED, design=_design(rows)
    )
    assert 94 in table["design"]["singleton_strata"]
    cell = next(c for c in table["cells"] if c["cell"] == "all")
    assert cell["design_se"]["delta"]["n_singleton_strata"] >= 1


def test_paired_change_se_uses_the_indicator_difference():
    rows = _rows()
    table = tabulation.tabulate_u2(
        rows, data_provenance=ap.INVENTED, design=_design(rows)
    )
    cell = next(c for c in table["cells"] if c["cell"] == "all")
    mask = np.ones(len(rows), dtype=bool)
    clusters = ut._design_clusters(_design(rows))
    paired = ut._design_se(
        rows,
        mask,
        rows["poor_reform"].to_numpy(float) - rows["poor_baseline"].to_numpy(float),
        clusters,
    )["se"]
    assert cell["design_se"]["delta"]["se"] == pytest.approx(paired)
    independent = np.hypot(
        cell["design_se"]["baseline_rate"]["se"],
        cell["design_se"]["reform_rate"]["se"],
    )
    assert paired != pytest.approx(independent)


def test_rows_outside_the_design_frame_refuse():
    rows = _rows()
    design = _design(rows)
    design = design[~design["stratum"].eq(88)]
    with pytest.raises(tabulation.U2TabulationError, match="not in the design"):
        tabulation.tabulate_u2(rows, data_provenance=ap.INVENTED, design=design)


def test_split_units_link_family_units_transitively():
    rows = pd.DataFrame(
        {
            "family_unit_id": [201_700_005, 201_900_003, 202_100_009, 201_900_007],
            "person_id": [1, 1, 2, 2],
        }
    )
    rows.loc[2, "person_id"] = 1  # person 1 links three family units
    units = ut.floor_split_units(rows)
    assert len(set(units[:3])) == 1
    assert units[0] == min(rows["family_unit_id"][:3])


def test_both_observations_of_a_person_fall_on_one_side(u1_cohort):
    obs = u1_cohort.observations
    units = pd.Series(ut.floor_split_units(obs), index=obs.index)
    for pid, rows in obs.groupby("person_id"):
        assert units.loc[rows.index].nunique() == 1


def test_undefined_floors_and_the_required_seed_count():
    rows = _rows(n=4)
    table = tabulation.tabulate_u2(
        rows, data_provenance=ap.INVENTED, design=_design(rows)
    )
    for cell in table["cells"]:
        floor = cell["floor"]["delta"]
        if floor["n_seeds"] < ut.MIN_FLOOR_SEEDS:
            assert floor["defined"] is False
            assert floor["mean"] is None
            assert floor["undefined_reason"]
    assert tabulation.U2TabulationConfig().floor_seeds == (0, 1, 2, 3, 4)
    with pytest.raises(tabulation.U2TabulationError, match="seeds"):
        tabulation.U2TabulationConfig(floor_seeds=(0, 1))


def test_floor_is_not_rescaled_and_uses_sample_sd(u2_run):
    cell = next(
        c for c in u2_run["rows"]["U0"]["tabulation"]["cells"] if c["cell"] == "all"
    )
    floor = cell["floor"]["delta"]
    assert floor["defined"]
    values = np.asarray(floor["values"])
    assert floor["mean"] == pytest.approx(values.mean())
    assert floor["sd"] == pytest.approx(values.std(ddof=1))
