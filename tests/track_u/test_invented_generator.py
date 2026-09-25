"""The INVENTED Track U generator (plan item U5).

Everything here runs on the invented generator's output: no PSID file, no
Census threshold, no SSA value and no comparator value is read.  The tests
check that the invented frames have the reader shapes, satisfy the
codebook identities, exercise every Track U path, and cannot pass as PSID.
"""

from __future__ import annotations

import dataclasses

import pandas as pd
import pytest

from populace_dynamics.cohorts import age67
from populace_dynamics.data import family_income
from populace_dynamics.estimates import adjusted_poverty as ap
from populace_dynamics.uniform_cut_track_u import invented
from tests.cohorts.test_age67 import _inputs


@pytest.fixture(scope="module")
def blocked() -> age67.Age67Inputs:
    return invented.invented_age67_inputs()


@pytest.fixture(scope="module")
def staged() -> age67.Age67Inputs:
    return invented.invented_age67_inputs(supplement_waves_staged=True)


def test_the_generator_is_deterministic_in_its_seed(blocked):
    again = invented.invented_age67_inputs()
    assert age67.input_frames_sha256(again) == age67.input_frames_sha256(
        blocked
    )
    other = invented.invented_age67_inputs(seed=invented.DEFAULT_SEED + 1)
    assert age67.input_frames_sha256(other) != age67.input_frames_sha256(
        blocked
    )
    with pytest.raises(ValueError, match="integer"):
        invented.invented_age67_inputs(seed=True)


def test_provenance_is_labelled_invented(blocked):
    provenance = blocked.provenance
    assert provenance["kind"] == age67.INVENTED == "invented"
    assert provenance["data"].startswith("INVENTED DATA")
    assert "not PSID observations" in provenance["data"]
    assert provenance["seed"] == invented.DEFAULT_SEED
    assert provenance["supplement_waves_staged"] is False
    assert provenance["input_frames_sha256"] == age67.input_frames_sha256(
        blocked
    )
    cohort = age67.build_age67_cohort(blocked)
    assert cohort.provenance["kind"] == age67.INVENTED
    assert cohort.provenance["label"] == provenance["data"]


def test_frames_have_the_reader_shapes(staged):
    for wave in age67.WAVES:
        income = staged.family_income[wave]
        assert list(income.columns) == [
            "wave",
            "income_year",
            *family_income.income_variables(wave),
            "wife_present",
        ]
        assert (income["income_year"] == wave - 1).all()
        assert str(income["head_sex"].dtype) == "string"
        assert str(income["head_age"].dtype) == "Int64"
        assert str(income["wife_age"].dtype) == "Int64"
        assert (income["wife_present"] == income["wife_age"].notna()).all()
        assert income["interview"].is_unique
        assert (income["census_needs_standard"] > 0).all()
        assert (income["n_children"] < income["fu_size"]).all()
        # negative amounts only where the codebooks document a loss
        for concept in family_income.income_variables(wave):
            if concept in family_income.MAY_BE_NEGATIVE or concept in (
                "head_sex",
                "head_age",
                "wife_age",
            ):
                continue
            assert (income[concept] >= 0).all(), (wave, concept)
        wealth = staged.family_wealth[wave]
        assert list(wealth.columns) == [
            "wave",
            "interview",
            *family_income.wealth_variables(wave),
        ]
        # the supplement waves carry the 2009 family file's concepts
        assert list(family_income.wealth_variables(wave)) == list(
            family_income.wealth_variables(2009 if wave < 2009 else wave)
        )
        assert set(wealth["interview"]) == set(income["interview"])
    anchor = staged.anchors[2009]
    assert list(anchor.columns) == [
        "person_id",
        "interview",
        "sequence",
        "relationship",
        "age",
        "reported_birth_year",
        "weight",
    ]
    assert anchor["person_id"].is_unique


def test_income_and_wealth_identities_hold_exactly(staged):
    incomes = pd.concat(
        [staged.family_income[wave] for wave in age67.WAVES],
        ignore_index=True,
    )
    for identities in family_income.reconcile_family_income(incomes).values():
        for counts in identities.values():
            assert counts["n_exact"] == counts["n_families"]
    wealth = pd.concat(
        [staged.family_wealth[wave] for wave in age67.WAVES],
        ignore_index=True,
    )
    reconciled = family_income.reconcile_wealth1(wealth)
    assert sorted(reconciled) == [str(wave) for wave in age67.WAVES]
    for identities in reconciled.values():
        for counts in identities.values():
            assert counts["n_exact"] == counts["n_families"]


def test_fu_size_counts_the_in_family_records_only(staged):
    for wave in age67.WAVES:
        anchor = staged.anchors[wave]
        in_family = (
            anchor[anchor["sequence"].between(1, 20)]
            .groupby("interview")
            .size()
        )
        income = staged.family_income[wave].set_index("interview")
        assert (income["fu_size"] == in_family.reindex(income.index)).all()


def test_supplement_waves_follow_the_flag(blocked, staged):
    assert set(blocked.family_wealth) == set(family_income.WEALTH_WAVES)
    assert set(blocked.wealth_refusals) == {2005, 2007}
    assert "INVENTED" in blocked.wealth_refusals[2005]
    assert set(staged.family_wealth) == set(age67.WAVES)
    assert staged.wealth_refusals == {}
    # u1-draft-6: the supplement waves' wealth is marked as the
    # supplement's, the family-file waves' as the family file's
    for inputs, expected in (
        (
            staged,
            {
                2005: "wealth_supplement",
                2007: "wealth_supplement",
                2009: "family_file",
                2011: "family_file",
                2013: "family_file",
            },
        ),
        (
            blocked,
            {
                2005: age67.WEALTH_BLOCKED_STATUS,
                2007: age67.WEALTH_BLOCKED_STATUS,
                2009: "family_file",
                2011: "family_file",
                2013: "family_file",
            },
        ),
    ):
        obs = age67.build_age67_cohort(inputs).observations
        found = {
            int(wave): set(rows["wealth_status"])
            for wave, rows in obs.groupby("wave")
        }
        assert found == {wave: {s} for wave, s in expected.items()}


def test_every_track_u_path_is_exercised(staged):
    u0 = age67.build_age67_cohort(staged)
    obs = u0.observations
    assert set(obs["birth_year"]) == set(age67.PRIMARY_BIRTH_YEARS)
    assert set(obs["member_role"]) == {"head", "wife", "ofum"}
    assert {
        "married",
        "widowed",
        "divorced",
        "never_married",
        "unknown",
        "no_marriage_history",
    } <= set(obs["marital_status"])
    assert {
        "exact_marriage",
        "inferred_period_age",
        "derived_projection_age",
    } <= set(obs["birth_source"])
    assert obs["member_married_coresident"].any()
    assert (obs["married"] & ~obs["member_married_coresident"]).any()
    assert (obs["relationship"] == 22).any()
    assert obs.groupby("family_unit_id")["person_id"].nunique().max() >= 2
    assert {
        "not_present:moved_out",
        "not_present:died",
        "not_present:institution",
        "zero_weight",
    } <= set(u0.dispositions["disposition"])
    rows = age67.income_rows(u0, staged)
    assert (rows["wealth1"] < 0).any()
    assert (rows[list(family_income.SSI_CONCEPTS)].sum(axis=1) > 0).any()
    assert (rows["n_children"] > 0).any()
    # every four-way marital status of specification section 9
    assert set(obs["marital_status_4"]) == {
        *age67.MARITAL_STATUS_4,
        age67.UNCLASSIFIED_MARITAL_STATUS,
    }
    # the unregistered institution option (U-inst withdrawn, u1-draft-5)
    u_inst = age67.build_age67_cohort(
        staged,
        age67.Age67Spec(
            presence="in_family_or_institution",
            institution_income_rule="family_of_record",
        ),
    )
    institution = u_inst.observations[u_inst.observations["in_institution"]]
    assert len(institution) > 0
    assert set(institution["income_status"]) == {"family_of_record"}
    assert set(institution["member_role"]) == {"ofum"}
    u1 = age67.build_age67_cohort(staged, age67.Age67Spec(row="U1"))
    assert set(u1.observations["birth_year"]) == set(age67.ALL_BIRTH_YEARS)
    # losses the codebooks allow reach cohort members' families
    losses = age67.income_rows(u1, staged)[
        ["head_business_asset", "head_rent", "head_farm"]
    ]
    assert (losses < 0).any().any()
    # specification u1-draft-4: every relationship-code resolution path,
    # a legal husband (code 90), the head's annuity and IRA income (and
    # HEAD IRAS in 2013), positive farm income, and interview ages that
    # exceed the income-year age
    assert {
        "marriage_history",
        "relationship_code_head_with_legal_spouse",
        "relationship_code_legal_wife",
        "relationship_code_legal_husband",
        "unresolved_non_married",
    } <= set(u1.observations["marital_resolution"])
    assert (u1.observations["relationship"] == 90).any()
    u1_rows = age67.income_rows(u1, staged)
    assert (u1_rows["head_annuities"] > 0).any()
    assert (u1_rows["head_farm"] > 0).any()
    assert (staged.family_income[2013]["head_iras"] > 0).any()
    anchor = staged.anchors[2009]
    present = anchor[anchor["sequence"].between(1, 20)]
    births = {
        row.person_id: row.birth_year
        for row in staged.marriage_history.itertuples()
    }
    older = [
        age - (2008 - births[pid])
        for pid, age in zip(present["person_id"], present["age"], strict=True)
        if pid in births
    ]
    assert set(older) == {0, 1}


def test_invented_thresholds_by_hand():
    thresholds = invented.invented_poverty_thresholds()
    assert thresholds.provenance["kind"] == ap.INVENTED
    assert thresholds.provenance["label"].startswith("INVENTED THRESHOLDS")
    assert "not Census values" in thresholds.provenance["label"]
    # 2004 is the base; 2005: 9,000 * 1.028 = 9,252 -> $10 rounding 9,250
    assert thresholds.weighted_average[2004]["one_65_plus"] == 9_000.0
    assert thresholds.weighted_average[2005]["one_65_plus"] == 9_250.0
    # matrix, three persons, two children: 15,000 * (1.02 - 0.03) = 14,850
    assert thresholds.matrix[2004]["three"][2] == 14_850.0
    assert set(thresholds.matrix[2004]["one_65_plus"]) == {0}
    assert set(thresholds.matrix[2004]["nine_plus"]) == set(range(9))
    # the needs standard stand-in uses the householder's age:
    # 65+: 9,000 * 1.02 = 9,180; under 65: 9,800 * 1.02 = 9,996 -> 10,000
    assert invented.invented_needs_standard(2004, 1, 0, 70) == 9_180
    assert invented.invented_needs_standard(2004, 1, 0, 60) == 10_000


def test_invented_inputs_are_regenerated_not_trusted(blocked):
    assert invented.check_invented_inputs(blocked)["regenerated"]
    # edit one amount and re-seal the digest: the builder accepts the
    # recorded digest, but re-generation from the seed refuses it
    income = dict(blocked.family_income)
    edited = income[2009].copy()
    edited.loc[0, "head_ss"] += 1
    income[2009] = edited
    forged = dataclasses.replace(blocked, family_income=income)
    forged = dataclasses.replace(
        forged,
        provenance={
            **blocked.provenance,
            "input_frames_sha256": age67.input_frames_sha256(forged),
        },
    )
    age67.build_age67_cohort(forged)
    with pytest.raises(ValueError, match="not the invented generator's"):
        invented.check_invented_inputs(forged)
    # an edit without re-sealing is refused by the builder itself
    stale = dataclasses.replace(blocked, family_income=income)
    with pytest.raises(ValueError, match="invented provenance"):
        age67.build_age67_cohort(stale)


def test_other_frames_cannot_claim_the_invented_label():
    caller = _inputs()
    with pytest.raises(ValueError, match="not invented"):
        invented.check_invented_inputs(caller)
    cohort = age67.build_age67_cohort(caller)
    assert cohort.provenance["kind"] == age67.CALLER_FRAMES
    with pytest.raises(ValueError, match="not invented"):
        invented.check_invented_cohort(cohort)


def test_the_invented_cohort_is_checked_by_rebuilding(staged):
    cohort = age67.build_age67_cohort(staged)
    assert invented.check_invented_cohort(cohort)["rebuilt"]
    edited = cohort.observations.copy()
    edited.loc[0, "weight"] = edited.loc[0, "weight"] + 1.0
    forged = dataclasses.replace(cohort, observations=edited)
    object.__setattr__(forged, "provenance", cohort.provenance)
    with pytest.raises(ValueError, match="observations differ"):
        invented.check_invented_cohort(forged)
