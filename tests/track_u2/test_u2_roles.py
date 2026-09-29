"""Relationship labels and the section 3 role amendment (section 13).

Groups: labels (codes 10/20/22/88/90 in every support wave; code 92
absent in 2013/2015 and present 2017-2023; reported-birth-year anchors)
and roles (code 20 of either sex, code 90, code 92, code 88's
administrative-support distinction, cohabitor income slots, zero-weight
legal spouses, unresolved and ambiguous pairings).  INVENTED DATA - NOT A
COMPARISON.
"""

from __future__ import annotations

import dataclasses

import pandas as pd
import pytest

from populace_dynamics.estimates import adjusted_poverty as ap
from populace_dynamics.uniform_cut_track_u2 import (
    cohort,
    estimator,
    invented,
    sources,
)

#: Section 3, "Mandatory relationship-label tests": the documented
#: prefixes after case folding and whitespace normalization.
PREFIXES = {
    2013: {
        10: "Head in 2013",
        20: "Legal Wife in 2013",
        22: '"Wife"--female cohabitor',
        88: "First-year cohabitor of Head",
        90: "Legal husband of Head",
        92: None,
    },
    2015: {
        10: "Head in 2015",
        20: "Legal Spouse in 2015",
        22: "Partner--female cohabitor",
        88: "First-year cohabitor of Head",
        90: "Uncooperative legal spouse of Head",
        92: None,
    },
    **{
        wave: {
            10: f"Reference Person in {wave}",
            20: f"Legal Spouse in {wave}",
            22: "Partner--cohabitor",
            88: "First-year cohabitor of Reference Person",
            90: "Uncooperative legal spouse of Reference Person",
            92: "Uncooperative partner of Reference Person",
        }
        for wave in (2017, 2019, 2021, 2023)
    },
}
BIRTH_ANCHORS = {
    2013: "ER34206",
    2015: "ER34307",
    2017: "ER34506",
    2019: "ER34706",
    2021: "ER34906",
    2023: "ER35106",
}


def _norm(text: str) -> str:
    return " ".join(text.casefold().split())


@pytest.mark.parametrize("wave", sources.SUPPORT_WAVES)
def test_relationship_labels_carry_the_documented_prefixes(
    wave, committed_registries
):
    for code, prefix in PREFIXES[wave].items():
        entry = committed_registries.entry(
            "roles", f"{wave}.relationship.{code}"
        )
        if prefix is None:
            assert entry["present"] is False
            assert entry["label"] is None
        else:
            assert entry["present"] is True
            assert _norm(entry["label"]).startswith(_norm(prefix)), (
                wave,
                code,
            )
            # A generic "spouse" match is not enough (section 3).
            assert _norm(prefix) != "spouse"


@pytest.mark.parametrize("wave", sources.SUPPORT_WAVES)
def test_reported_birth_year_anchor_labels(wave, committed_registries):
    entry = committed_registries.entry(
        "individual", f"{wave}.reported_birth_year"
    )
    assert entry["variable"] == BIRTH_ANCHORS[wave]
    assert _norm(entry["label"]) == _norm(
        f"YEAR INDIVIDUAL BORN {str(wave)[2:]}"
    )


def test_declared_rules_follow_the_section_3_table():
    rules = sources.declared_role_rules()
    for wave in sources.SUPPORT_WAVES:
        assert rules[(wave, 10)].income_role == "head"
        twenty = rules[(wave, 20)]
        assert (twenty.income_role, twenty.spouse_slot) == ("wife", True)
        assert twenty.legal_spouse_annuity and twenty.marital_resolution
        cohabitor = rules[(wave, 22)]
        assert (cohabitor.income_role, cohabitor.spouse_slot) == (
            "wife",
            True,
        )
        assert not cohabitor.legal_spouse_annuity
        assert not cohabitor.marital_resolution
        ninety = rules[(wave, 90)]
        assert (ninety.income_role, ninety.spouse_slot) == ("ofum", False)
        assert ninety.legal_spouse_annuity and ninety.marital_resolution
        assert rules[(wave, 88)].refusal is not None
        ninety_two = rules[(wave, 92)]
        if wave < 2017:
            assert not ninety_two.present and ninety_two.refusal
        else:
            assert (ninety_two.income_role, ninety_two.spouse_slot) == (
                "ofum",
                False,
            )
            assert not ninety_two.legal_spouse_annuity
            assert not ninety_two.marital_resolution
            assert not ninety_two.administrative_birth_support


def test_administrative_birth_support_is_administrative_only():
    assert sources.ADMINISTRATIVE_BIRTH_SUPPORT_CODES == (10, 20, 22, 88, 90)
    rules = sources.declared_role_rules()
    for wave in sources.SUPPORT_WAVES:
        assert rules[(wave, 88)].administrative_birth_support
        assert not rules[(wave, 88)].legal_spouse_annuity
        assert not rules[(wave, 92)].administrative_birth_support


#: The role entries the adjudicated registries refuse (commit 883ea48):
#: code 88 everywhere (TO VERIFY); 2015 code 20 (disposition F, the
#: loader refuses the whole entry); code 92's absence in 2013 and 2015;
#: codes 90 and 92 in 2019-2023 (disposition F).  2013 and 2015-2017
#: code 90 and 2017 code 92 are documented rules (disposition D).
REFUSED_ROLES = frozenset(
    {(wave, 88) for wave in sources.SUPPORT_WAVES}
    | {(2015, 20), (2013, 92), (2015, 92)}
    | {(wave, code) for wave in (2019, 2021, 2023) for code in (90, 92)}
)


def test_registry_rules_equal_declared_rules_where_resolved(
    committed_registries,
):
    registry = sources.RoleContext.from_registry(committed_registries)
    declared = sources.RoleContext.declared()
    resolved = [k for k, r in registry.rules.items() if r.refusal is None]
    assert resolved
    for key in resolved:
        assert registry.rules[key] == declared.rules[key], key
    refused = {k for k, r in registry.rules.items() if r.refusal}
    assert refused == REFUSED_ROLES
    assert {(2013, 90), (2015, 90), (2017, 90), (2017, 92)} <= set(resolved)


@pytest.mark.parametrize("wave", sources.SUPPORT_WAVES)
@pytest.mark.parametrize("code", sources.RELATIONSHIP_CODES)
def test_role_refusals_agree_with_the_loader_api(wave, code):
    """Differential: the role context refuses exactly what the milestone-1
    loader's ``require_resolved`` refuses (absent codes aside, which the
    loader resolves and the builder refuses on sight)."""

    from populace_dynamics.data import u2_source_registry as registry

    context = sources.RoleContext.from_registry()
    entry_id = f"{wave}.relationship.{code}"
    try:
        entry = registry.require_resolved("roles", entry_id)
    except registry.SourceAdjudicationError:
        with pytest.raises(sources.U2RoleRefusal) as refusal:
            context.rule(wave, code)
        assert entry_id in str(refusal.value)
        assert (wave, code) in REFUSED_ROLES
        return
    if entry["present"]:
        assert context.rule(wave, code).present
        assert (wave, code) not in REFUSED_ROLES
    else:
        with pytest.raises(sources.U2RoleRefusal, match="absent"):
            context.rule(wave, code)


def test_registry_context_refuses_refused_codes(u2_inputs, u2_births):
    registry = sources.RoleContext.from_registry()
    with pytest.raises(sources.U2RoleRefusal, match="roles:"):
        cohort.build_u2_cohort(
            u2_inputs, role_context=registry, births=u2_births
        )
    with pytest.raises(sources.U2RoleRefusal, match="code 92 absent in 2015"):
        registry.rule(2015, 92)
    with pytest.raises(
        sources.U2RoleRefusal, match="refuse_male_code20_per_u2_adjudicate_F"
    ):
        registry.rule(2015, 20)
    for wave in (2019, 2021, 2023):
        for code in (90, 92):
            with pytest.raises(
                sources.U2RoleRefusal,
                match="refuse_ofum_assignment_per_u2_adjudicate_F",
            ):
                registry.rule(wave, code)


def test_code_88_refuses_under_every_context(u2_inputs):
    variant = invented.with_code_88_cohabitor(u2_inputs)
    with pytest.raises(sources.U2RoleRefusal, match="code 88"):
        cohort.build_u2_cohort(
            variant,
            cohort.U2CohortSpec(row="U1"),
            role_context=sources.RoleContext.declared(),
        )
    registry = sources.RoleContext.from_registry()
    for wave in sources.SUPPORT_WAVES:
        with pytest.raises(sources.U2RoleRefusal, match="relationship.88"):
            registry.rule(wave, 88)
    with pytest.raises(sources.U2RoleRefusal):
        cohort.build_u2_cohort(
            variant, cohort.U2CohortSpec(row="U1"), role_context=registry
        )


def test_declared_context_refuses_non_invented_inputs(u2_inputs, declared):
    caller = cohort.replace_provenance(u2_inputs, kind="caller_frames")
    with pytest.raises(cohort.U2CohortError, match="invented"):
        cohort.build_u2_cohort(caller, role_context=declared)


def test_code_20_of_either_sex_occupies_the_spouse_slot(u1_cohort):
    obs = u1_cohort.observations
    males = obs[obs["relationship"].eq(20) & obs["sex"].eq("male")]
    assert not males.empty
    assert (males["member_role"] == "wife").all()
    assert (males["marital_status_4"] == "married").all()
    assert set(males["wave"]) >= {2015}


def test_code_90_is_ofum_income_and_a_legal_spouse_life(u1_cohort):
    obs = u1_cohort.observations
    ninety = obs[obs["relationship"].eq(90)]
    assert not ninety.empty
    assert (ninety["member_role"] == "ofum").all()
    assert (
        ninety["marital_resolution"] == "relationship_code_legal_spouse_90"
    ).all()
    assert ninety["member_married_coresident"].all()
    heads = obs[obs["fu_head_spouse_relationship"].eq(90)]
    assert heads["fu_head_spouse_present"].all()
    resolved = heads[heads["relationship"].eq(10)]
    assert (
        resolved["marital_resolution"]
        == "relationship_code_head_with_legal_spouse"
    ).all()
    assert (~heads["spouse_slot_occupied_roster"]).all()


def test_code_92_is_ofum_never_a_legal_spouse_and_never_resolves(u1_cohort):
    obs = u1_cohort.observations
    partners = obs[obs["relationship"].eq(92)]
    assert not partners.empty
    assert (partners["member_role"] == "ofum").all()
    assert (partners["marital_resolution"] == "unresolved_non_married").all()
    assert (partners["marital_status_4"] == "unclassified").all()
    assert set(partners["wave"]) <= {2017, 2019, 2021, 2023}
    heads = obs[
        obs["relationship"].eq(10)
        & obs["interview"].isin(partners["interview"])
        & obs["wave"].isin(partners["wave"])
    ]
    assert not heads.empty
    assert (~heads["fu_head_spouse_present"]).all()


def test_cohabitor_22_occupies_the_slot_without_legal_status(u1_cohort):
    obs = u1_cohort.observations
    partners = obs[obs["relationship"].eq(22)]
    assert not partners.empty
    assert (partners["member_role"] == "wife").all()
    assert (~partners["married"]).all()
    heads = obs[
        obs["relationship"].eq(10)
        & obs["interview"].isin(partners["interview"])
    ]
    assert heads["spouse_slot_occupied_roster"].all()
    assert (~heads["fu_head_spouse_present"]).all()


def _restamped(inputs, **frames):
    changed = dataclasses.replace(inputs, **frames)
    return cohort.replace_provenance(
        changed,
        kind="invented",
        generator="test",
        seed=0,
        data="INVENTED DATA - NOT A COMPARISON",
    )


def _family_of(inputs, wave, kind_head_birth, relationship):
    """(interview, person ids) of the first family holding ``relationship``
    whose head has birth year ``kind_head_birth``."""

    anchor = inputs.anchors[wave]
    for interview, rows in anchor[anchor["sequence"].between(1, 20)].groupby(
        "interview"
    ):
        codes = set(rows["relationship"])
        if relationship in codes and 10 in codes:
            return int(interview), rows
    raise AssertionError("no such family")


def test_zero_weight_legal_spouse_keeps_a_derived_age(u2_inputs, declared):
    interview, rows = _family_of(u2_inputs, 2019, None, 20)
    spouse = int(rows.loc[rows["relationship"].eq(20), "person_id"].iloc[0])
    anchors = {
        wave: frame.assign(
            weight=frame["weight"].where(frame["person_id"] != spouse, 0.0)
        )
        for wave, frame in u2_inputs.anchors.items()
    }
    inputs = _restamped(u2_inputs, anchors=anchors)
    births = cohort.derive_u2_births(inputs)
    assert spouse not in births.universe
    assert births.birth_year(spouse) is not None
    built = cohort.build_u2_cohort(
        inputs, cohort.U2CohortSpec(row="U1"), role_context=declared
    )
    obs = built.observations
    paired = obs[obs["fu_head_spouse_person_id"].eq(spouse)]
    assert not paired.empty
    assert (paired["fu_head_spouse_age_source"] == "derived_birth_year").all()


def test_ambiguous_pairing_stays_unresolved_and_counted(u2_inputs, declared):
    # Add a second code-20 person to a family whose head's history cannot
    # be dated: the pairing is ambiguous, so the head stays unresolved.
    obs = cohort.build_u2_cohort(u2_inputs, role_context=declared).observations
    target = obs[
        obs["marital_resolution"].eq(
            "relationship_code_head_with_legal_spouse"
        )
        & obs["fu_head_spouse_relationship"].eq(20)
    ].iloc[0]
    wave, interview = int(target["wave"]), int(target["interview"])
    extra = 699_998
    anchors = {}
    for w, frame in u2_inputs.anchors.items():
        row = {
            "person_id": extra,
            "interview": interview if w == wave else 0,
            "sequence": 5 if w == wave else 0,
            "relationship": 20 if w == wave else 0,
            "age": 60 if w == wave else 0,
            "reported_birth_year": pd.NA,
            "weight": 100.0 if w == wave else 0.0,
        }
        anchors[w] = pd.concat(
            [frame, pd.DataFrame([row])], ignore_index=True
        ).astype(frame.dtypes.to_dict())
    persons = pd.concat(
        [
            u2_inputs.persons,
            pd.DataFrame([{"person_id": extra, "sex": "female"}]),
        ],
        ignore_index=True,
    ).astype({"person_id": "int64", "sex": "string"})
    design = pd.concat(
        [
            u2_inputs.design,
            pd.DataFrame([{"person_id": extra, "stratum": 1, "cluster": 1}]),
        ],
        ignore_index=True,
    ).astype("int64")
    inputs = _restamped(
        u2_inputs, anchors=anchors, persons=persons, design=design
    )
    rebuilt = cohort.build_u2_cohort(
        inputs, role_context=declared
    ).observations
    row = rebuilt[rebuilt["observation_id"].eq(target["observation_id"])].iloc[
        0
    ]
    assert row["legal_spouse_pairing"] == "ambiguous"
    assert row["marital_resolution"] == "unresolved_non_married"
    assert row["marital_status_4"] == "unclassified"
    assert not row["fu_head_spouse_present"]


def test_spouse_slot_disagreement_refuses(u2_inputs, declared):
    wave = 2019
    income = u2_inputs.family_income[wave].copy()
    obs = cohort.build_u2_cohort(u2_inputs, role_context=declared).observations
    single = obs[obs["wave"].eq(wave) & ~obs["spouse_slot_occupied_roster"]][
        "interview"
    ].iloc[0]
    income.loc[income["interview"].eq(single), "wife_present"] = True
    inputs = _restamped(
        u2_inputs, family_income={**u2_inputs.family_income, wave: income}
    )
    built = cohort.build_u2_cohort(inputs, role_context=declared)
    with pytest.raises(cohort.U2CohortError, match="spouse income slot"):
        cohort.income_rows(built, inputs)


def test_missing_head_refuses_the_annuity(u2_inputs, declared, u2_params):
    obs = cohort.build_u2_cohort(u2_inputs, role_context=declared).observations
    target = obs[obs["relationship"].eq(50)].iloc[0]
    wave, interview = int(target["wave"]), int(target["interview"])
    anchors = dict(u2_inputs.anchors)
    frame = anchors[wave].copy()
    head = frame["interview"].eq(interview) & frame["relationship"].eq(10)
    frame.loc[head, "relationship"] = 30
    anchors[wave] = frame
    inputs = _restamped(u2_inputs, anchors=anchors)
    built = cohort.build_u2_cohort(inputs, role_context=declared)
    row = built.observations[
        built.observations["observation_id"].eq(target["observation_id"])
    ].iloc[0]
    assert row["head_pairing"] == "absent"
    members = cohort.income_rows(built, inputs)
    with pytest.raises(ap.AdjustedPovertyError, match="annuitant age"):
        estimator.u2_adjusted_incomes(
            members,
            context=estimator.U2EstimatorContext(declared.kind),
            data_provenance=ap.INVENTED,
            life_table=u2_params.life_tables["nchs_2000"],
            thresholds=u2_params.thresholds,
            ssi=u2_params.ssi,
        )
