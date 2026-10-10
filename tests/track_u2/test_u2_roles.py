"""Relationship labels and the section 3 role amendment (section 13).

Groups: labels (codes 10/20/22/88/90 in every support wave; code 92
absent in 2013/2015 and present 2017-2023; reported-birth-year anchors)
and roles (code 20 of either sex, code 90, code 92, code 88's
administrative-support distinction, cohabitor income slots, zero-weight
legal spouses, unresolved and ambiguous pairings), with the two
family-unit exclusions Max ratified on 2026-10-10 (d1090; section 16c).
INVENTED DATA - NOT A COMPARISON.
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


#: Section 16c (d1090): the waves of each ratified family-unit exclusion.
B1_WAVES = (2015,)
B2_WAVES = (2019, 2021, 2023)


def expected_exclusion(wave: int, code: int, sex: str) -> str | None:
    """Section 16c's two rules, restated: the disposition a member of
    ``code`` and recorded ``sex`` brings on its ``wave`` family unit."""

    if wave in B1_WAVES and code == 20 and sex == "male":
        return "male code 20 in 2015 family unit"
    if wave in B2_WAVES and code in (90, 92):
        return "uncooperative spouse or partner in family unit"
    return None


def test_declared_rules_follow_the_section_3_table():
    """Section 3's table, with section 16c's exclusions where it differs."""

    rules = sources.declared_role_rules()
    for wave in sources.SUPPORT_WAVES:
        assert rules[(wave, 10)].income_role == "head"
        twenty = rules[(wave, 20)]
        assert (twenty.income_role, twenty.spouse_slot) == ("wife", True)
        assert twenty.legal_spouse_annuity and twenty.marital_resolution
        if wave in B1_WAVES:
            assert twenty.family_unit_exclusion == sources.FamilyUnitExclusion(
                sources.MALE_CODE_20_2015, "male"
            )
        else:
            assert twenty.family_unit_exclusion is None
        cohabitor = rules[(wave, 22)]
        assert (cohabitor.income_role, cohabitor.spouse_slot) == (
            "wife",
            True,
        )
        assert not cohabitor.legal_spouse_annuity
        assert not cohabitor.marital_resolution
        ninety = rules[(wave, 90)]
        b2 = sources.FamilyUnitExclusion(
            sources.UNCOOPERATIVE_SPOUSE_OR_PARTNER
        )
        # 2019-2023: B2's exclusion and no income role (no OFUM routing
        # is asserted); 2013-2017: the documented OFUM role.
        role = None if wave in B2_WAVES else "ofum"
        exclusion = b2 if wave in B2_WAVES else None
        assert (ninety.income_role, ninety.spouse_slot) == (role, False)
        assert ninety.family_unit_exclusion == exclusion
        assert ninety.legal_spouse_annuity and ninety.marital_resolution
        assert rules[(wave, 88)].refusal is not None
        assert rules[(wave, 88)].family_unit_exclusion is None
        assert rules[(wave, 22)].family_unit_exclusion is None
        assert rules[(wave, 10)].family_unit_exclusion is None
        ninety_two = rules[(wave, 92)]
        if wave < 2017:
            assert not ninety_two.present and ninety_two.refusal
            assert ninety_two.family_unit_exclusion is None
        else:
            assert (ninety_two.income_role, ninety_two.spouse_slot) == (
                role,
                False,
            )
            assert ninety_two.family_unit_exclusion == exclusion
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


#: The role entries the committed registries refuse: code 88 everywhere
#: (TO VERIFY) and code 92's absence in 2013 and 2015.  2013 and
#: 2015-2017 code 90 and 2017 code 92 are documented rules (disposition
#: D).  2015 code 20 and 2019-2023 codes 90 and 92, which the
#: adjudication refused (disposition F), carry section 16c's ratified
#: exclusions since the d1090 registry commit (:data:`D1090_RULED`).
REFUSED_ROLES = frozenset(
    {(wave, 88) for wave in sources.SUPPORT_WAVES} | {(2013, 92), (2015, 92)}
)
D1090_RULED = frozenset(
    {(2015, 20)} | {(wave, code) for wave in B2_WAVES for code in (90, 92)}
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
    # The d1090 registry entries resolve to exactly the declared rules,
    # each carrying its section 16c exclusion.
    assert D1090_RULED <= set(resolved)
    excluding = {
        k for k, r in registry.rules.items() if r.family_unit_exclusion
    }
    assert excluding == D1090_RULED


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


@pytest.mark.parametrize("row", ["U0", "U1"])
def test_registry_context_builds_as_the_declared_context(
    row, u2_inputs, u2_births, declared
):
    """Differential: since the d1090 registry commit the committed roles
    registry resolves every code the invented population holds, so the
    registry context builds it exactly as the declared context does,
    the section 16c exclusions included (only the context label
    differs)."""

    registry = sources.RoleContext.from_registry()
    spec = cohort.U2CohortSpec(row=row)
    by_registry = cohort.build_u2_cohort(
        u2_inputs, spec, role_context=registry, births=u2_births
    )
    by_declared = cohort.build_u2_cohort(
        u2_inputs, spec, role_context=declared, births=u2_births
    )
    assert set(by_registry.observations["income_role_rule"]) == {
        sources.REGISTRY
    }
    pd.testing.assert_frame_equal(
        by_registry.observations.drop(columns="income_role_rule"),
        by_declared.observations.drop(columns="income_role_rule"),
    )
    pd.testing.assert_frame_equal(
        by_registry.dispositions, by_declared.dispositions
    )
    ruled = by_registry.dispositions["disposition"].isin(
        sources.FAMILY_UNIT_EXCLUSIONS
    )
    assert set(by_registry.dispositions.loc[ruled, "disposition"]) == set(
        sources.FAMILY_UNIT_EXCLUSIONS
    )


def test_registry_context_refuses_refused_codes():
    registry = sources.RoleContext.from_registry()
    with pytest.raises(sources.U2RoleRefusal, match="code 92 absent in 2015"):
        registry.rule(2015, 92)
    for wave in sources.SUPPORT_WAVES:
        with pytest.raises(sources.U2RoleRefusal, match="TO VERIFY"):
            registry.rule(wave, 88)
    # The ruled codes resolve, each with its exclusion (section 16c).
    for wave, code in sorted(D1090_RULED):
        rule = registry.rule(wave, code)
        assert rule.family_unit_exclusion is not None, (wave, code)
        assert rule.family_unit_exclusion.disposition == expected_exclusion(
            wave, code, "male"
        )


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
    """From 2017 code 20 of either sex holds the spouse slot; in 2015 a
    unit with a male code-20 person supplies no observation (section 16c,
    B1) and a female code-20 spouse keeps the slot."""

    obs = u1_cohort.observations
    males = obs[obs["relationship"].eq(20) & obs["sex"].eq("male")]
    assert not males.empty
    assert (males["member_role"] == "wife").all()
    assert (males["marital_status_4"] == "married").all()
    assert set(males["wave"]) >= {2017} and 2015 not in set(males["wave"])
    assert obs[obs["wave"].eq(2015) & obs["spouse_slot_sex"].eq("male")].empty
    females = obs[
        obs["relationship"].eq(20)
        & obs["sex"].eq("female")
        & obs["wave"].eq(2015)
    ]
    assert not females.empty and (females["member_role"] == "wife").all()
    disp = u1_cohort.dispositions
    b1 = disp[disp["disposition"].eq(sources.MALE_CODE_20_2015)]
    assert not b1.empty and set(b1["wave"]) == {2015}


def test_code_90_is_ofum_income_and_a_legal_spouse_life(u1_cohort):
    obs = u1_cohort.observations
    ninety = obs[obs["relationship"].eq(90)]
    assert not ninety.empty
    # 2019-2023 units holding a code-90 person supply no observation.
    assert set(ninety["wave"]) <= {2013, 2015, 2017}
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
    # Code 92 exists from 2017, and its 2019-2023 units are excluded.
    assert set(partners["wave"]) == {2017}
    heads = obs[
        obs["relationship"].eq(10)
        & obs["interview"].isin(partners["interview"])
        & obs["wave"].isin(partners["wave"])
    ]
    assert not heads.empty
    assert (~heads["fu_head_spouse_present"]).all()


# ---------------------------------------------------------------------------
# Section 16c: the family-unit exclusions Max ratified (d1090, 2026-10-10)
# ---------------------------------------------------------------------------
SEXES = ("male", "female", "na")


@pytest.mark.parametrize("wave", sources.SUPPORT_WAVES)
def test_exclusion_rules_are_exactly_section_16c(wave):
    """Exhaustive over the relationship codes, an outside code and every
    recorded sex: a lone member brings exactly section 16c's
    disposition."""

    rules = sources.declared_role_rules()
    assert sources.FAMILY_UNIT_EXCLUSIONS == (
        expected_exclusion(2015, 20, "male"),
        expected_exclusion(2019, 90, "male"),
    )
    for code in (*sources.RELATIONSHIP_CODES, 40):
        rule = rules.get(
            (wave, code), sources.RoleRule(wave, code, **sources.OFUM_RULE)
        )
        for sex in SEXES:
            found = sources.family_unit_exclusion({1: rule}, {1: sex})
            assert found == expected_exclusion(wave, code, sex), (
                wave,
                code,
                sex,
            )


def test_exclusion_dispositions_are_the_ratified_names():
    """The builder's dispositions are the names section 16c ratifies."""

    from pathlib import Path

    spec = (
        Path(__file__).resolve().parents[2]
        / "docs/design/boomers2004_1946_55_comparison.md"
    ).read_text(encoding="utf-8")
    record = spec[spec.index("## 16c. ") : spec.index("## 17. ")]
    for name in sources.FAMILY_UNIT_EXCLUSIONS:
        assert f"named disposition `{name}`" in record, name
    with pytest.raises(ValueError, match="ratified"):
        sources.FamilyUnitExclusion("male code 20 in 2017 family unit")
    with pytest.raises(ValueError, match="sex"):
        sources.FamilyUnitExclusion(sources.MALE_CODE_20_2015, "unknown")


def _units_with_a_trigger(inputs) -> dict[tuple[int, int], str]:
    """An independent oracle from the raw frames: each (wave, interview)
    whose in-family members (sequence 1-20) include a section 16c
    trigger, with the disposition it brings."""

    sex = inputs.persons.set_index("person_id")["sex"]
    out = {}
    for wave, frame in inputs.anchors.items():
        members = frame[frame["sequence"].between(1, 20)]
        for row in members.itertuples(index=False):
            found = expected_exclusion(
                wave, int(row.relationship), str(sex.get(row.person_id))
            )
            if found:
                out[(wave, int(row.interview))] = found
    return out


@pytest.mark.parametrize("row", ["U0", "U1"])
def test_exclusions_remove_exactly_the_units_that_hold_a_trigger(
    row, u2_inputs, declared, u2_births
):
    built = cohort.build_u2_cohort(
        u2_inputs,
        cohort.U2CohortSpec(row=row),
        role_context=declared,
        births=u2_births,
    )
    triggers = _units_with_a_trigger(u2_inputs)
    assert set(triggers.values()) == set(sources.FAMILY_UNIT_EXCLUSIONS)
    obs = built.observations
    for unit in zip(obs["wave"], obs["interview"], strict=True):
        assert unit not in triggers, unit
    disp = built.dispositions
    excluded = disp[disp["disposition"].isin(sources.FAMILY_UNIT_EXCLUSIONS)]
    assert not excluded.empty
    for item in excluded.itertuples(index=False):
        anchor = u2_inputs.anchors[item.wave].set_index("person_id")
        unit = (item.wave, int(anchor.loc[item.person_id, "interview"]))
        assert triggers.get(unit) == item.disposition, unit
    # One disposition per planned (person, cell): exclusions never sit
    # beside an observation of the same person and wave.
    keys = list(zip(disp["person_id"], disp["wave"], strict=True))
    assert len(keys) == len(set(keys))
    assert set(zip(obs["person_id"], obs["wave"], strict=True)).isdisjoint(
        zip(excluded["person_id"], excluded["wave"], strict=True)
    )


@pytest.mark.parametrize("row", ["U0", "U1"])
def test_exclusions_change_nothing_else(
    row, u2_inputs, declared, u2_births, monkeypatch
):
    """Differential: the build with the exclusions equals the build with
    them switched off, less exactly the excluded observations, which the
    switched-off build would have made."""

    spec = cohort.U2CohortSpec(row=row)
    built = cohort.build_u2_cohort(
        u2_inputs, spec, role_context=declared, births=u2_births
    )
    monkeypatch.setattr(sources, "family_unit_exclusion", lambda *_: None)
    unexcluded = cohort.build_u2_cohort(
        u2_inputs, spec, role_context=declared, births=u2_births
    )
    disp = built.dispositions
    ruled = disp["disposition"].isin(sources.FAMILY_UNIT_EXCLUSIONS)
    excluded = set(
        disp.loc[ruled, "person_id"].astype(str)
        + ":"
        + disp.loc[ruled, "wave"].astype(str)
    )
    would_be = set(unexcluded.observations["observation_id"])
    assert excluded and excluded <= would_be
    kept = unexcluded.observations[
        ~unexcluded.observations["observation_id"].isin(excluded)
    ].reset_index(drop=True)
    pd.testing.assert_frame_equal(
        built.observations.reset_index(drop=True), kept
    )
    # The same planned cells in the same order; only the excluded ones
    # change disposition, each from an observation.
    before = unexcluded.dispositions
    pd.testing.assert_frame_equal(
        disp.drop(columns="disposition"), before.drop(columns="disposition")
    )
    assert (before.loc[ruled, "disposition"] == "observation").all()
    assert disp.loc[~ruled, "disposition"].equals(
        before.loc[~ruled, "disposition"]
    )


def test_a_trigger_outside_the_family_unit_does_not_exclude(
    u1_cohort, u2_inputs
):
    """Section 16c applies the exclusions to the family unit's in-family
    members (sequence 1-20).  A code-90 husband in an institution in 2021
    (sequence 51, the FAQ's rare case) is outside the unit, so the head's
    2021 observation stands; his own 2019 unit, where he is in the family,
    is excluded."""

    anchor = u2_inputs.anchors[2021]
    away = anchor[anchor["relationship"].eq(90) & anchor["sequence"].eq(51)]
    assert len(away) == 1
    interview = int(away["interview"].iloc[0])
    obs = u1_cohort.observations
    heads = obs[
        obs["wave"].eq(2021)
        & obs["interview"].eq(interview)
        & obs["relationship"].eq(10)
    ]
    assert len(heads) == 1
    assert not heads["fu_head_spouse_present"].iloc[0]
    husband = int(away["person_id"].iloc[0])
    disp = u1_cohort.dispositions
    mine = disp[disp["person_id"].eq(husband)].set_index("wave")
    assert mine.loc[2019, "disposition"] == (
        sources.UNCOOPERATIVE_SPOUSE_OR_PARTNER
    )
    assert mine.loc[2017, "disposition"] == "observation"


def test_b2_excludes_whoever_the_target_is(u1_cohort, u2_inputs):
    """Reference person, uncooperative spouse or partner, or another
    member: every target in a 2019-2023 unit with code 90 or 92 is
    excluded (section 16c)."""

    disp = u1_cohort.dispositions
    b2 = disp[disp["disposition"].eq(sources.UNCOOPERATIVE_SPOUSE_OR_PARTNER)]
    codes = set()
    for item in b2.itertuples(index=False):
        anchor = u2_inputs.anchors[item.wave].set_index("person_id")
        codes.add(int(anchor.loc[item.person_id, "relationship"]))
    assert {10, 90, 92, 40} <= codes
    assert set(b2["wave"]) <= set(B2_WAVES)


def test_structure_and_runner_disclose_each_exclusion(u1_cohort, u2_run):
    """Each count is disclosed (section 16c): by birth year in the
    structural summary, and per row in the runner's dispositions."""

    summary = cohort.structural_summary(u1_cohort)
    disp = u1_cohort.dispositions
    for name in sources.FAMILY_UNIT_EXCLUSIONS:
        stated = sum(
            counts.get(name, 0)
            for counts in summary["dispositions_by_birth_year"].values()
        )
        assert stated == int(disp["disposition"].eq(name).sum()) > 0
    for row_id, entry in u2_run["rows"].items():
        counts = entry["population"]["dispositions"]
        assert set(sources.FAMILY_UNIT_EXCLUSIONS) <= set(counts), row_id


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


def test_zero_weight_legal_spouse_keeps_a_derived_age(u2_inputs, declared):
    inputs = invented.invented_variant(
        u2_inputs, "zero_weight_legal_spouse_2019"
    )
    anchor = u2_inputs.anchors[2019]
    zeroed = {
        int(pid)
        for pid in inputs.anchors[2019]
        .loc[
            inputs.anchors[2019]["weight"].eq(0) & anchor["weight"].gt(0),
            "person_id",
        ]
        .tolist()
    }
    assert len(zeroed) == 1
    (spouse,) = zeroed
    assert (
        int(anchor.loc[anchor["person_id"].eq(spouse), "relationship"].iloc[0])
        == 20
    )
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
    # A second code-20 person joins a family whose head's history cannot
    # be dated: the pairing is ambiguous, so the head stays unresolved.
    obs = cohort.build_u2_cohort(u2_inputs, role_context=declared).observations
    target = obs[
        obs["marital_resolution"].eq(
            "relationship_code_head_with_legal_spouse"
        )
        & obs["fu_head_spouse_relationship"].eq(20)
    ].iloc[0]
    inputs = invented.invented_variant(u2_inputs, "ambiguous_legal_spouse")
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
    # With two code-20 persons the roster has no unique occupant of the
    # family file's one spouse income slot.  Section 3 keeps an ambiguous
    # *pairing* unresolved and counted (spec line 156) but is silent on
    # two slot occupants; the conservative reading refuses the income
    # rows (section 14: failed joins refuse execution) rather than
    # attribute the slot to either person.
    assert not row["spouse_slot_occupied_roster"]
    built = cohort.build_u2_cohort(inputs, role_context=declared)
    with pytest.raises(cohort.U2CohortError, match="spouse income slot"):
        cohort.income_rows(built, inputs)


def test_spouse_slot_disagreement_refuses(u2_inputs, declared):
    inputs = invented.invented_variant(
        u2_inputs, "spouse_slot_disagreement_2019"
    )
    built = cohort.build_u2_cohort(inputs, role_context=declared)
    with pytest.raises(cohort.U2CohortError, match="spouse income slot"):
        cohort.income_rows(built, inputs)


def test_missing_head_refuses_the_annuity(u2_inputs, declared, u2_params):
    obs = cohort.build_u2_cohort(u2_inputs, role_context=declared).observations
    target = obs[obs["relationship"].eq(50)].iloc[0]
    inputs = invented.invented_variant(u2_inputs, "missing_head")
    built = cohort.build_u2_cohort(inputs, role_context=declared)
    row = built.observations[
        built.observations["observation_id"].eq(target["observation_id"])
    ].iloc[0]
    assert row["head_pairing"] == "absent"
    # No head, so no legal spouse is paired: the count says so rather
    # than reporting a unique pairing (finding 8 of the u2m2 review).
    assert row["legal_spouse_pairing"] == cohort.NO_HEAD_PAIRING
    assert not row["fu_head_spouse_present"]
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


def test_every_pairing_state_is_named(u2_run):
    """The runner's counts use only the builder's four pairing states."""

    for entry in u2_run["rows"].values():
        states = set(entry["population"]["legal_spouse_pairing"])
        assert states <= {"unique", "absent", "ambiguous", "no_head"}


# ---------------------------------------------------------------------------
# The role context is bound to its kind (review finding 2)
# ---------------------------------------------------------------------------
def test_a_registry_context_cannot_carry_the_declared_rules():
    with pytest.raises(sources.U2SourceRefusal, match="committed roles"):
        sources.RoleContext(sources.REGISTRY, sources.declared_role_rules())
    registry = sources.RoleContext.from_registry()
    with pytest.raises(sources.U2SourceRefusal, match="declared table"):
        sources.RoleContext(sources.INVENTED_DECLARED, registry.rules)
    # Any one rule changed is refused, e.g. 2015 code 20 without its
    # section 16c exclusion, or code 88 made applicable.
    for key, changed in (
        (
            (2015, 20),
            dataclasses.replace(
                registry.rules[(2015, 20)], family_unit_exclusion=None
            ),
        ),
        (
            (2019, 88),
            dataclasses.replace(registry.rules[(2019, 88)], refusal=None),
        ),
    ):
        rules = dict(registry.rules)
        rules[key] = changed
        with pytest.raises(
            sources.U2SourceRefusal, match=rf"\({key[0]}, {key[1]}\)"
        ):
            sources.RoleContext(sources.REGISTRY, rules)


def test_role_rules_are_read_only():
    for context in (
        sources.RoleContext.from_registry(),
        sources.RoleContext.declared(),
    ):
        with pytest.raises(TypeError):
            context.rules[(2015, 20)] = None  # type: ignore[index]
        with pytest.raises(dataclasses.FrozenInstanceError):
            context.kind = sources.INVENTED_DECLARED  # type: ignore[misc]


def test_relabelled_inputs_cannot_reach_the_declared_rules(
    u2_inputs, declared
):
    """Review finding 1: only the generator seals invented inputs.

    ``replace_provenance`` refuses the invented kind; a hand-copied
    invented provenance on replaced frames (as a relabelled loader
    output would be) carries no seal; and frames changed in place after
    sealing no longer match the seal.  Each refuses the declared rules.
    """

    with pytest.raises(cohort.U2CohortError, match="cannot label"):
        cohort.replace_provenance(u2_inputs, kind="invented")
    copied = dataclasses.replace(
        u2_inputs,
        anchors=dict(u2_inputs.anchors),
        provenance=dict(u2_inputs.provenance),
    )
    assert copied.invented_seal is None
    with pytest.raises(cohort.U2CohortError, match="no seal"):
        cohort.build_u2_cohort(copied, role_context=declared)
    # This variant copies every anchor frame (``DataFrame.assign``), so
    # the in-place change below cannot reach the shared base fixture.
    variant = invented.invented_variant(
        u2_inputs, "zero_weight_legal_spouse_2019"
    )
    assert all(
        variant.anchors[w] is not u2_inputs.anchors[w] for w in variant.anchors
    )
    variant.anchors[2019].loc[0, "weight"] += 1.0
    with pytest.raises(cohort.U2CohortError, match="sealed"):
        cohort.build_u2_cohort(variant, role_context=declared)
    with pytest.raises(ValueError, match="changed after sealing"):
        invented.check_invented_inputs(variant)


def test_frames_sealed_outside_the_generator_do_not_regenerate(
    u2_inputs, declared
):
    """Review 2, finding 2: a seal set by the private helper (or by
    ``object.__setattr__``) on frames the generator did not make is
    refused by the cohort, which regenerates (seed, variant)."""

    doubled = dataclasses.replace(
        u2_inputs,
        anchors={
            wave: frame.assign(weight=frame["weight"] * 2)
            for wave, frame in u2_inputs.anchors.items()
        },
    )
    forged = invented._sealed(
        doubled, seed=u2_inputs.provenance["seed"], variant=None
    )
    assert forged.invented_seal is not None
    with pytest.raises(cohort.U2CohortError, match="do not regenerate"):
        cohort.build_u2_cohort(forged, role_context=declared)
    by_hand = dataclasses.replace(
        doubled,
        provenance={
            **u2_inputs.provenance,
            "input_frames_sha256": cohort.input_frames_sha256(doubled),
        },
    )
    object.__setattr__(by_hand, "invented_seal", dict(forged.invented_seal))
    with pytest.raises(cohort.U2CohortError, match="do not regenerate"):
        cohort.build_u2_cohort(by_hand, role_context=declared)


def test_invented_inputs_need_the_generator_loaded(tmp_path):
    """Sealed inputs cannot exist unless the generator is loaded; the
    cohort looks it up in ``sys.modules`` (it never imports it), so in an
    interpreter where it is absent an invented label refuses."""

    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    script = tmp_path / "no_generator.py"
    script.write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(root / 'src')!r})\n"
        "import pandas as pd\n"
        "from populace_dynamics.uniform_cut_track_u2 import cohort, sources\n"
        "empty = pd.DataFrame({'person_id': pd.Series([], dtype='int64')})\n"
        "inputs = cohort.U2Inputs(anchors={}, design=empty, persons=empty,\n"
        "    marriage_history=empty, observed_earnings=empty,\n"
        "    family_income={}, family_wealth={})\n"
        "digest = cohort.input_frames_sha256(inputs)\n"
        "label = {'generator': 'x', 'seed': 1, 'variant': None,\n"
        "         'input_frames_sha256': digest}\n"
        "inputs = cohort.replace_provenance(inputs, kind='caller_frames')\n"
        "object.__setattr__(inputs, 'provenance', {'kind': 'invented',\n"
        "    **label})\n"
        "object.__setattr__(inputs, 'invented_seal', dict(label))\n"
        "assert cohort._INVENTED_MODULE not in sys.modules\n"
        "try:\n"
        "    cohort.build_u2_cohort(inputs,\n"
        "        role_context=sources.RoleContext.declared())\n"
        "except cohort.U2CohortError as error:\n"
        "    print('REFUSED', error)\n"
        "assert cohort._INVENTED_MODULE not in sys.modules\n"
    )
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        check=True,
        cwd=root,
    )
    assert result.stdout.startswith("REFUSED"), result.stdout
    assert "generator is not loaded" in result.stdout


def test_role_contexts_inputs_and_cohorts_are_final():
    """Review 3, finding 1: a subclass could override ``rule`` while
    carrying the registry kind; none can be defined."""

    for base in (sources.RoleContext, cohort.U2Inputs, cohort.U2Cohort):
        with pytest.raises(TypeError, match="final"):
            type("_Sub", (base,), {})


def test_seals_are_read_only_and_bound_to_the_label(u2_inputs, declared):
    with pytest.raises(TypeError):
        u2_inputs.invented_seal["seed"] = 12345  # type: ignore[index]
    relabelled = dataclasses.replace(
        u2_inputs,
        provenance={**u2_inputs.provenance, "seed": 12345},
    )
    object.__setattr__(
        relabelled, "invented_seal", dict(u2_inputs.invented_seal)
    )
    with pytest.raises(cohort.U2CohortError, match="seed"):
        cohort.build_u2_cohort(relabelled, role_context=declared)


def test_a_frame_must_be_a_plain_dataframe(u2_inputs, declared):
    """Review 3, finding 6: a DataFrame subclass could report another
    frame's text to the digest; input frames must be exactly
    ``pandas.DataFrame``."""

    class _Lying(pd.DataFrame):
        pass

    anchors = dict(u2_inputs.anchors)
    anchors[2019] = _Lying(anchors[2019])
    changed = dataclasses.replace(u2_inputs, anchors=anchors)
    with pytest.raises(cohort.U2CohortError, match="pandas.DataFrame"):
        cohort.input_frames_sha256(changed)
    with pytest.raises(cohort.U2CohortError, match="pandas.DataFrame"):
        cohort.build_u2_cohort(changed, role_context=declared)
