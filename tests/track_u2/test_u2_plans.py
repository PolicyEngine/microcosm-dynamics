"""U2 observation plans, identification and cohort bounds (section 13).

Groups: observation plans; boundary wave; missing observations; support
separation; identification; cohort bounds.  INVENTED DATA - NOT A
COMPARISON.
"""

from __future__ import annotations

import dataclasses
from collections import defaultdict

import pandas as pd
import pytest

from populace_dynamics.cohorts import age67
from populace_dynamics.uniform_cut_track_u2 import cohort, identity, invented


def test_u0_has_five_exact_age_pairs():
    plan = cohort.observation_plan(cohort.U2CohortSpec())
    assert plan == (
        (1947, 2015, 2014, 1.0),
        (1949, 2017, 2016, 1.0),
        (1951, 2019, 2018, 1.0),
        (1953, 2021, 2020, 1.0),
        (1955, 2023, 2022, 1.0),
    )


def test_u1_has_fifteen_pairs_over_ten_births_summing_to_one():
    cells = cohort.plan_cells(cohort.U2CohortSpec(row="U1"))
    assert len(cells) == 15
    assert {b for b, *_ in cells} == set(range(1946, 1956))
    total: dict[int, float] = defaultdict(float)
    for birth, wave, income_year, age, multiplier in cells:
        assert income_year == wave - 1 == birth + age
        total[birth] += multiplier
        if birth % 2:
            assert (age, multiplier) == (67, 1.0)
        else:
            assert age in (66, 68) and multiplier == 0.5
    assert all(value == 1.0 for value in total.values())


def test_plan_equals_the_milestone_1_support_registry(committed_registries):
    assert cohort.check_plan_against_support_registry(
        committed_registries
    ) == {"cells": 15, "equal_to_support_registry": True}


def test_wave_2013_is_an_observation_only_for_1946_at_66():
    for row in cohort.ROWS:
        cells = cohort.plan_cells(cohort.U2CohortSpec(row=row))
        in_2013 = [cell for cell in cells if cell[1] == 2013]
        assert in_2013 == (
            [(1946, 2013, 2012, 66, 0.5)] if row == "U1" else []
        )


def test_u1_plan_does_not_alter_u1_of_track_u():
    assert age67.WAVES == identity.U1_WAVES == (2005, 2007, 2009, 2011, 2013)
    assert age67.observation_plan(age67.Age67Spec(row="U0")) == tuple(
        sorted(
            (b, b + 68, b + 67, 1.0) for b in (1937, 1939, 1941, 1943, 1945)
        )
    )


def test_missing_observation_keeps_its_half_weight(u1_cohort, u2_inputs):
    obs = u1_cohort.observations
    by_person = obs.groupby("person_id")
    singles = [
        pid
        for pid, rows in by_person
        if rows["birth_year"].iloc[0] % 2 == 0 and len(rows) == 1
    ]
    assert singles, "the invented cohort has an even birth with one wave"
    for pid in singles:
        row = obs[obs["person_id"].eq(pid)].iloc[0]
        assert row["weight_multiplier"] == 0.5
        assert row["weight"] == pytest.approx(0.5 * row["weight_raw"])
    moved = u1_cohort.dispositions[
        u1_cohort.dispositions["disposition"].eq("not_present:moved_out")
    ]
    assert len(moved) >= 1
    assert set(moved["person_id"]) <= set(singles)


def _only_in_2013(u2_inputs):
    """The inputs plus a person present only in wave 2013, stratum 80."""

    pid = 699_999
    anchors = {}
    for wave, frame in u2_inputs.anchors.items():
        row = {
            "person_id": pid,
            "interview": 1_001 if wave == 2013 else 0,
            "sequence": 3 if wave == 2013 else 0,
            "relationship": 30 if wave == 2013 else 0,
            "age": 40 if wave == 2013 else 0,
            "reported_birth_year": pd.NA,
            "weight": 900.0 if wave == 2013 else 0.0,
        }
        anchors[wave] = pd.concat(
            [frame, pd.DataFrame([row])], ignore_index=True
        ).astype(frame.dtypes.to_dict())
    design = pd.concat(
        [
            u2_inputs.design,
            pd.DataFrame([{"person_id": pid, "stratum": 80, "cluster": 2}]),
        ],
        ignore_index=True,
    ).astype("int64")
    changed = dataclasses.replace(u2_inputs, anchors=anchors, design=design)
    return cohort.replace_provenance(changed, kind="caller_frames"), (80, 2)


def test_support_waves_never_enter_u0_observations_or_design(
    u0_cohort, u2_inputs
):
    assert set(u0_cohort.observations["wave"]) <= set(cohort.PRIMARY_WAVES)
    changed, pair = _only_in_2013(u2_inputs)
    u0 = cohort.design_frame(changed, cohort.U2CohortSpec())
    u1 = cohort.design_frame(changed, cohort.U2CohortSpec(row="U1"))
    assert pair not in set(map(tuple, u0.to_numpy().tolist()))
    assert pair in set(map(tuple, u1.to_numpy().tolist()))
    positive = set()
    for wave in cohort.PRIMARY_WAVES:
        anchor = changed.anchors[wave]
        positive |= set(anchor.loc[anchor["weight"] > 0, "person_id"])
    design = changed.design[changed.design["person_id"].isin(positive)]
    expected = set(
        map(tuple, design[["stratum", "cluster"]].to_numpy().tolist())
    )
    assert set(map(tuple, u0.to_numpy().tolist())) == expected


def test_design_frame_of_u1_includes_the_2013_wave(u2_inputs):
    u0 = cohort.design_frame(u2_inputs, cohort.U2CohortSpec())
    u1 = cohort.design_frame(u2_inputs, cohort.U2CohortSpec(row="U1"))
    assert set(map(tuple, u0.to_numpy().tolist())) <= set(
        map(tuple, u1.to_numpy().tolist())
    )


def test_shared_observations_have_identical_births_and_annuitants(
    u0_cohort, u1_cohort
):
    shared = u0_cohort.observations.merge(
        u1_cohort.observations, on="observation_id", suffixes=("_0", "_1")
    )
    assert len(shared) == len(u0_cohort.observations)
    for column in (
        "birth_year",
        "birth_source",
        "fu_head_person_id",
        "fu_head_age",
        "fu_head_age_source",
        "fu_head_spouse_person_id",
        "fu_head_spouse_age",
        "fu_head_spouse_age_source",
        "marital_status_4",
        "member_role",
        "weight",
    ):
        left = shared[f"{column}_0"].astype(str).tolist()
        right = shared[f"{column}_1"].astype(str).tolist()
        assert left == right, column


def test_births_are_derived_once_and_refused_from_other_inputs(
    u2_inputs, declared
):
    other = cohort.derive_u2_births(invented.with_code_88_cohabitor(u2_inputs))
    with pytest.raises(cohort.U2CohortError, match="other inputs"):
        cohort.build_u2_cohort(u2_inputs, role_context=declared, births=other)


def test_seed_is_the_earliest_positive_weight_presence(u2_births, u2_inputs):
    seed = u2_births.seed.set_index("person_id")
    for pid, row in seed.iterrows():
        earlier = [
            wave
            for wave in cohort.SUPPORT_WAVES
            if wave < row["anchor_wave"]
            and bool(
                (
                    u2_inputs.anchors[wave]["person_id"].eq(pid)
                    & u2_inputs.anchors[wave]["sequence"].between(1, 20)
                    & (u2_inputs.anchors[wave]["weight"] > 0)
                ).any()
            )
        ]
        assert not earlier
        assert row["year"] == row["anchor_wave"] - 1


def test_cohort_bounds_and_outside_births(u0_cohort, u1_cohort, u2_births):
    for built in (u0_cohort, u1_cohort):
        obs = built.observations
        assert obs["birth_year"].between(1946, 1955).all()
        assert (
            obs["member_age"] == obs["income_year"] - obs["birth_year"]
        ).all()
        assert (obs["income_year"] == obs["wave"] - 1).all()
        assert (
            obs["weight"] == obs["weight_raw"] * obs["weight_multiplier"]
        ).all()
        assert (
            obs["family_unit_id"] == obs["wave"] * 100_000 + obs["interview"]
        ).all()
    outside = [
        pid
        for pid in u2_births.universe
        if u2_births.birth_year(pid) is not None
        and u2_births.birth_year(pid) not in range(1946, 1956)
    ]
    assert outside
    assert u0_cohort.diagnostics["n_outside_birth_years"] == len(outside)
    assert not set(outside) & set(u1_cohort.observations["person_id"])


def test_dispositions_are_counted(u0_cohort, u1_cohort):
    counts = u1_cohort.dispositions["disposition"].value_counts()
    for reason in (
        "observation",
        "not_present:institution",
        "not_present:died",
        "not_present:moved_out",
        "zero_weight",
        "excluded_sex_unknown",
    ):
        assert counts.get(reason, 0) >= 1, reason
    assert int(counts["observation"]) == len(u1_cohort.observations)


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"row": "U0-F"}, "row-set amendment"),
        ({"row": "U2-F"}, "row-set amendment"),
        ({"row": "U7"}, "must be one of"),
        ({"seed_wave_rule": "earliest_presence_wave"}, "U1's rule"),
        ({"seed_wave_rule": "latest"}, "registers only"),
        ({"presence": "in_family_or_institution"}, "registers only"),
        ({"separated_is_married": False}, "registers only"),
        ({"separated_is_married": 1}, "registers only"),
        ({"missing_observation_reweighting": True}, "registers only"),
        ({"target_id": "U1"}, "not 'U2'"),
    ],
)
def test_cohort_spec_refuses_other_settings(overrides, message):
    with pytest.raises(ValueError, match=message):
        cohort.U2CohortSpec(**overrides)


def test_malformed_inputs_refuse(u2_inputs, declared):
    missing = dataclasses.replace(
        u2_inputs,
        anchors={k: v for k, v in u2_inputs.anchors.items() if k != 2017},
    )
    missing = cohort.replace_provenance(missing, kind="caller_frames")
    with pytest.raises(cohort.U2CohortError, match="support waves"):
        cohort.derive_u2_births(missing)
    no_family = dataclasses.replace(
        u2_inputs,
        family_income={
            **u2_inputs.family_income,
            2019: u2_inputs.family_income[2019].iloc[1:],
        },
    )
    no_family = cohort.replace_provenance(no_family, kind="invented")
    with pytest.raises(cohort.U2CohortError, match="failed joins"):
        cohort.build_u2_cohort(no_family, role_context=declared)


def test_invented_provenance_is_checked(u2_inputs, declared):
    tampered = dataclasses.replace(
        u2_inputs,
        persons=u2_inputs.persons.assign(
            sex=pd.Series(["female"] * len(u2_inputs.persons), dtype="string")
        ),
    )
    with pytest.raises(cohort.U2CohortError, match="invented"):
        cohort.build_u2_cohort(tampered, role_context=declared)


def test_every_u1_cell_holds_an_invented_observation(u1_cohort):
    """The invented population reaches all fifteen of row U1's planned
    cells, so the dry run exercises every birth year and wave."""

    obs = u1_cohort.observations
    for birth, wave, _, age, _ in cohort.plan_cells(
        cohort.U2CohortSpec(row="U1")
    ):
        cell = obs[obs["birth_year"].eq(birth) & obs["wave"].eq(wave)]
        assert len(cell) > 0, (birth, wave, age)
    assert obs["birth_year"].nunique() == 10
