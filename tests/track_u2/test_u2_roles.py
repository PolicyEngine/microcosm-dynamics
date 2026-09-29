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
    # Any one rule changed is refused, e.g. 2015 code 20 made applicable.
    rules = dict(registry.rules)
    rules[(2015, 20)] = sources.declared_role_rules()[(2015, 20)]
    with pytest.raises(sources.U2SourceRefusal, match=r"\(2015, 20\)"):
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
