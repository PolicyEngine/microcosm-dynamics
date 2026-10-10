"""Consistency checks for the exercise 2 (Track U) specification.

``docs/design/boomers2004_uniform_cut_comparison.md`` is read by
downstream lanes through its machine-readable JSON block (§15).  These
tests hold that block to the code's defaults and constants (the income
concept, the cohort builder, the reader tables, the tabulation, the
registered rows, Max's rulings and the runner's named deltas), so a text
change and a code change cannot drift apart silently.  Since
``u1-ratified-1`` (cos decision d411, 2026-09-26) the specification is
ratified and frozen.  They use only the document and the code: no PSID
value, no model output and no comparator value.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from populace_dynamics.cohorts import age67
from populace_dynamics.data import employer_dc, family_income
from populace_dynamics.estimates import adjusted_poverty as ap
from populace_dynamics.estimates import uniform_cut_tabulation as ut
from populace_dynamics.uniform_cut_track_u import rows as track_u_rows
from populace_dynamics.uniform_cut_track_u import runner

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "docs" / "design" / "boomers2004_uniform_cut_comparison.md"
EVIDENCE = (
    Path.home() / "microcosm-launch-evidence" / "dynasim-parity-20260909"
)


@pytest.fixture(scope="module")
def text() -> str:
    return SPEC_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def block(text: str) -> dict:
    blocks = re.findall(r"```json\n(.*?)\n```", text, re.DOTALL)
    assert len(blocks) == 1
    return json.loads(blocks[0])


def _section(text: str, number: str, following: str) -> str:
    return text.split(f"## {number}. ")[1].split(f"## {following}. ")[0]


#: Max's ruling on the u1-draft-7 card, as the cos record of d411 holds it.
D411_RULING = (
    "yes, as on the card: (a)-(g) as corrected 2026-09-25, including the "
    "memo's n<30 small-cell flag and 'uncertainty not estimable' for a "
    "no-switcher cell; registration states it is a static simulation on "
    "PSID-observed incomes (Max in chat, 2026-09-26)"
)
D411_RULED_AT = "2026-09-26T07:41"
#: The awaiting text of every pending decision since u1-ratified-1.
FIXED = "fixed by the ratification of u1-ratified-1 (cos decision d411)"
#: The ruling fields d189 decided; every other field is d411's.
D189_FIELDS = frozenset({"claim_class", "ssi_rule", "wealth_supplements"})


def _flat(value: str) -> str:
    return " ".join(value.split())


def test_block_identity_and_status(block):
    assert block["specification"] == "boomers2004_uniform_cut_exercise2"
    # u1-ratified-1 (cos decision d411): ratified and frozen, nothing
    # blocks the registered run
    assert block["version"] == "u1-ratified-1"
    assert block["status"] == "ratified_frozen"
    assert block["blocked_by"] == []
    # Max ruled on exercise 2 (cos decision d189, 2026-09-24): the claim
    # class is decided and no longer awaited
    assert block["claim_class"]["decided"] == "d189"
    assert "awaiting" not in block["claim_class"]
    assert block["claim_class"]["class"] == (
        "track_u_psid_realized_measurement_not_a_projection"
    )
    assert block["acceptance_rule"] is None
    assert block["labels"] == list(ap.OUTPUT_LABELS)
    module = _registered_script()
    assert module._awaiting(block) == []
    module.check_specification_ratified(block)


def test_status_line_records_the_ratification(text):
    """The header records d411's ruling verbatim and the ratification by
    merge; the claim class keeps d189's name and says, as the ruling
    directs, that the exercise is a static simulation on PSID-observed
    incomes."""

    status = _flat(text.split("- **Specification:**")[0])
    assert status.startswith("# ")
    assert "- **Status:** ratified and frozen." in status
    assert "draft for the referee" not in status
    assert "Nothing here is ratified" not in status
    assert f'Max ruled cos decision d411 on 2026-09-26: "{D411_RULING}"' in (
        status
    )
    assert "item (g) adds a small-cell rule for the comparison memo" in (
        status
    )
    assert "Two referee passes are recorded (§17)" in status
    header = _flat(text.split("- **Plan item:**")[0])
    assert "version `u1-ratified-1`" in header
    claim = _flat(
        text.split("- **Claim class (decided, cos decision d189")[1].split(
            "- **Labels every output carries:**"
        )[0]
    )
    assert "realized-outcome measurement on PSID persons at age 67" in claim
    assert "Python, not Axiom (plan decision 4; §16 ruling 11)" in claim
    assert "static simulation on PSID-observed incomes" in claim
    assert "the incomes and wealth are PSID-observed" in claim
    assert "the annuitized income are counterfactual" in claim
    boundary = _flat(
        text.split("- **Builder boundary:**")[1].split("## 1. Target")[0]
    )
    assert (
        "The lane that wrote `u1-ratified-1` read `RESTRICTED-FILES.md`"
        in (boundary)
    )


def test_builder_boundary_records_the_extract_values_scan(text):
    """The builder boundary states the cleared extract's values-scan
    verdict as ``RESTRICTED-FILES.md`` records it.

    Regression (independent review of u1-draft-5, 2026-09-24): the
    boundary said the governance file did not yet hold the 16:10 changelog
    entry recording the scan; it does, so the sentence was stale.
    """

    boundary = " ".join(
        text.split("- **Builder boundary:**")[1]
        .split("## 1. Target")[0]
        .split()
    )
    assert "did not yet hold" not in boundary
    assert "values scan of the extract at this hash is clean" in boundary
    assert "0 genuine leaks" in boundary
    assert "2026-09-24 16:10" in boundary
    restricted = EVIDENCE / "RESTRICTED-FILES.md"
    if not restricted.is_file():
        pytest.skip("RESTRICTED-FILES.md is outside this checkout")
    governance = " ".join(restricted.read_text(encoding="utf-8").split())
    assert "2026-09-24 16:10: exercise-2 values scan" in governance
    assert "Exercise 2 values scan: values scan clean." in governance


def test_population_matches_the_builder(block):
    population = block["population"]
    assert population["primary_birth_years"] == list(age67.PRIMARY_BIRTH_YEARS)
    assert population["fallback_birth_years"] == list(
        age67.FALLBACK_BIRTH_YEARS
    )
    assert population["u1_birth_years"] == [
        age67.ALL_BIRTH_YEARS[0],
        age67.ALL_BIRTH_YEARS[-1],
    ]
    spec = age67.Age67Spec()
    assert population["presence"] == spec.presence
    assert population["seed_wave_rule"] == spec.seed_wave_rule
    assert population["separated_is_married"] == spec.separated_is_married
    assert population["unresolved_marital_status"] == (
        spec.unresolved_marital_status
    )
    assert population["unresolved_marital_status"] in (
        age67.UNRESOLVED_MARITAL_RULES
    )
    assert population["annuitant_age_source"] == spec.annuitant_age_source
    assert population["annuitant_age_source"] in age67.ANNUITANT_AGE_SOURCES
    assert population["institution_income_rule"] == (
        spec.institution_income_rule
    )
    assert population["institution_income_rule"] in (
        age67.INSTITUTION_INCOME_RULES
    )
    assert population["u1_single_observation_weight"] == (
        spec.u1_single_observation_weight
    )
    plan = age67.observation_plan(age67.Age67Spec(row="U1"))
    halves = {m for b, _, _, m in plan if b % 2 == 0 and b != 1936}
    assert halves == {population["u1_even_birth_year_weight"]}
    for wave, entry in population["waves"].items():
        layout = age67.ANCHOR_LAYOUTS[int(wave)]
        assert entry["income_year"] == int(wave) - 1
        assert entry["weight"] == layout.weight_variable
        assert entry["family_unit_id"] == layout.family_unit_variable
        # u1-draft-6: every wave has WEALTH1, the supplement waves from
        # the PSID wealth supplements joined by their family ID
        assert entry["wealth1"] == (
            family_income.wealth_variables(int(wave))["wealth1"][0]
        )
        if int(wave) in family_income.WEALTH_WAVES:
            assert entry["wealth_source"] == "family_file"
        else:
            assert int(wave) in family_income.WEALTH_SUPPLEMENT_WAVES
            assert entry["wealth_source"] == f"WLTH{wave}"
            assert f"WLTH{wave}.txt" in (
                family_income.WEALTH_SUPPLEMENT_SHA256[int(wave)]
            )
            assert entry["wealth_join"] == (
                family_income.wealth_supplement_variables(int(wave))[
                    "interview"
                ][0]
            )
    assert population["design"] == {"stratum": "ER31996", "cluster": "ER31997"}


def test_headline_rule_matches_the_code(block):
    headline = block["population"]["headline"]
    assert headline["rule"] == track_u_rows.HEADLINE_RULE
    assert headline["fallback_row"] == track_u_rows.FALLBACK_ROW
    # with the supplements staged and adjudicated the rule gives U0, which
    # Max ruled the headline (d411 item (a)); no awaiting note
    assert headline["staged_psid_headline"] == track_u_rows.PRIMARY_ROW
    assert "awaiting" not in headline
    assert headline["ruled"].startswith("d411 item (a): U0 is the headline")
    assert block["population"]["primary_row"] == track_u_rows.PRIMARY_ROW
    fallback = age67.observation_plan(age67.Age67Spec(row="U0-F"))
    assert sorted({b for b, _, _, _ in fallback}) == list(
        age67.FALLBACK_BIRTH_YEARS
    )
    # the fallback's waves all carry WEALTH1 in the family file
    assert {w for _, w, _, _ in fallback} <= set(family_income.WEALTH_WAVES)


def test_income_concept_matches_the_spec_defaults(block):
    spec = ap.AdjustedPovertySpec()
    concept = block["income_concept"]
    assert concept["income_unit"] == spec.income_unit
    assert concept["asset_income_rule"] == spec.asset_income_rule
    assert concept["asset_income_items"] == list(
        family_income.ASSET_INCOME_CONCEPTS
    )
    assert concept["retirement_account_income_rule"] == (
        spec.retirement_account_income_rule
    )
    assert concept["retirement_account_income_items"] == list(
        ap.RETIREMENT_ACCOUNT_INCOME_CONCEPTS
    )
    for item in ap.RETIREMENT_ACCOUNT_INCOME_CONCEPTS:
        assert any(
            item in family_income.income_variables(wave)
            for wave in family_income.INCOME_WAVES
        )
    assert concept["farm_asset_share"] == spec.farm_asset_share
    # row U7 (u1-draft-7): the primary's financial assets and U7's rule
    assert concept["financial_assets"] == spec.financial_assets == "wealth1"
    assert set(ap.FINANCIAL_ASSETS) == {
        "wealth1",
        "wealth1_plus_employer_dc",
    }
    dc = concept["employer_dc"]
    assert dc["row"] == "U7"
    assert dc["persons"] == list(employer_dc.PERSONS)
    assert dc["previous_plans"] == list(employer_dc.PREVIOUS_PLANS)
    assert employer_dc.COUNTED_DISPOSITION == 3
    assert employer_dc.EXCLUDED_IRA_DISPOSITION == 2
    assert dc["counted_disposition"] == "left_to_accumulate"
    assert dc["excluded"] == [
        "rolled_over_into_ira",
        "both_plan_account_items_reasked",
        "off_route",
    ]
    # the questionnaires' routes the reader applies (checkpoint P62A asks
    # the account items of a formula or DK-type plan after a DK expected
    # benefit; independent review of u1-draft-7)
    assert dc["route_source"] == "questionnaires_checkpoint_p62a"
    assert dc["previous_routes"] == {
        "both_items": ["both"],
        "account_items": ["account", "formula", "dk"],
    }
    for wave in employer_dc.EMPLOYER_DC_WAVES:
        codes = employer_dc.plan_type_codes(wave)
        plan_type = np.array(
            [codes["previous_" + key] for key in ("formula", "account")]
            + [codes["previous_both"], codes["previous_dk"], 9, 0]
        )
        both = employer_dc._account_route("combo", plan_type, wave)
        account = employer_dc._account_route("dc", plan_type, wave)
        assert both.tolist() == [False, False, True, False, False, False]
        assert account.tolist() == [True, True, False, True, False, False]
    assert dc["reader"] == "data/employer_dc.py"
    assert (ROOT / "src" / "populace_dynamics" / dc["reader"]).is_file()
    assert concept["farm_loss"] == ap.FARM_LOSS_RULE
    assert concept["annuitized_share"] == spec.annuitized_share
    annuity = concept["annuity"]
    assert annuity == {
        "real_interest_rate": spec.real_interest_rate,
        "timing": spec.annuity_timing,
        "load": spec.annuity_load,
        "survivor_share": spec.survivor_share,
        "mortality_basis": spec.mortality_basis,
        "terminal_closure": spec.terminal_closure,
        "lives": spec.annuity_lives,
        "negative_wealth": spec.negative_wealth_rule,
    }
    decisions = {item.field: item for item in ap.pending_decisions()}
    assert concept["sensitivities_unscored"] == {
        "real_interest_rate": list(
            decisions["real_interest_rate"].alternatives
        )
    }
    assert block["threshold"]["rule"] == spec.threshold_rule
    # captured under cos decision d194: the block names the pinned capture
    assert block["threshold"]["capture_status"] == "captured"
    assert block["threshold"]["capture"] == {
        "file": str(ap.THRESHOLDS_PATH.relative_to(ROOT)),
        "sha256": ap.THRESHOLDS_SHA256,
    }
    assert ap.load_poverty_thresholds().provenance["sha256"] == (
        block["threshold"]["capture"]["sha256"]
    )
    assert "census_thresholds_not_captured" not in block["blocked_by"]
    ssi = block["ssi"]
    assert ssi["rule"] == spec.ssi_rule
    assert ssi["deeming"] == spec.ssi_deeming
    assert ssi["ofum_unit"] == spec.ofum_ssi_unit
    assert ssi["parameters"]["sha256"] == ap.SSI_PARAMETERS_SHA256
    assert ssi["parameters"]["file"] == str(
        ap.SSI_PARAMETERS_PATH.relative_to(ROOT)
    )


def test_target_records_the_cleared_extract(block):
    """Second referee S1 and S9: the comparator column, the Report's 36
    rows, whole-number cells and the cleared extract's path and hash."""

    target = block["target"]
    assert target["column"] == ut.COMPARATOR_COLUMN == "1936-45"
    assert target["report_rows"] == 36
    assert target["report_rows"] == len(ut.DEFAULT_CELLS) + len(
        ut.OPTIONAL_CELLS
    ) + sum(len(e["rows"]) for e in ut.NOT_COMPUTED_REPORT_ROWS.values())
    assert target["printed_precision"] == "whole_numbers"
    extract = target["definitions_extract"]
    assert extract["file"] == (
        "EVID/exercise2-definitions-cleared-20260924.md"
    )
    assert extract["sha256"] == (
        "a3978b683b4275424b6d12e9fe45f021fae277ccf9731a7883952564b6ed0384"
    )
    local = EVIDENCE / Path(extract["file"]).name
    if not local.is_file():
        pytest.skip("the cleared extract is outside this checkout")
    assert hashlib.sha256(local.read_bytes()).hexdigest() == (
        extract["sha256"]
    )


def test_cut_and_threshold_years_match_the_code(block):
    spec = ap.AdjustedPovertySpec()
    cut = block["cut"]
    assert cut["rate"] == spec.cut_rate == block["target"]["cut_rate"]
    # second referee S5: the Report's "beginning in 2004"
    assert cut["start_year"] == spec.cut_start_year == 2004
    decision = {item.field: item for item in ap.pending_decisions()}[
        "cut_start_year"
    ]
    assert decision.alternatives == (None,)
    assert "S5" in decision.default_basis
    # u1-draft-7: plan decision 8 is settled by the Report's "beginning in
    # 2004" (cleared extract), so the cut no longer awaits Max
    assert "awaiting" not in cut
    assert "beginning in 2004" in cut["start_year_basis"]
    assert cut["ruled"] == "d411 item (d)"
    assert "decision 8" in decision.default_basis
    assert not decision.awaiting.startswith("Max")
    assert cut["start_year_rule"] == ap.CUT_START_YEAR_RULE
    # not code parameters: the cut base and behaviour are fixed in
    # adjusted_incomes (specification section 16 lists them as pending)
    assert cut["base"] == "all_social_security_of_the_unit"
    assert cut["behavior"] == "none"
    income_years = [wave - 1 for wave in family_income.INCOME_WAVES]
    ssi_years = sorted(ap.load_ssi_parameters().fbr_individual_monthly)
    assert block["threshold"]["years"] == [
        min(income_years),
        max(income_years),
    ]
    assert block["threshold"]["years"] == [ssi_years[0], ssi_years[-1]]


def test_statistic_and_comparison_match_the_tabulation(block):
    statistic = block["statistic"]
    assert [statistic["headline"], *statistic["secondary"]] == list(
        ut.STATISTICS
    )
    assert statistic["unit"] == "percentage_points"
    comparison = block["comparison"]
    assert comparison["gap"] == "model_minus_report"
    # Max ruled no acceptance threshold (d411 item (c))
    assert comparison["acceptance"] == {
        "rule": None,
        "ruled": "d411 item (c)",
    }
    rulings = track_u_rows.MAX_RULINGS
    assert rulings["acceptance_rule"]["ruling"] is None
    assert rulings["acceptance_rule"]["item"] == "(c)"
    # d411 item (g): the memo's small-cell rule, a reporting rule for the
    # comparison memo that the block and the code's rulings record alike
    memo = dict(comparison["memo_small_cells"])
    assert memo.pop("ruled") == "d411 item (g)"
    assert memo == rulings["memo_small_cells"]["ruling"]
    assert memo == {
        "flag_unweighted_n_below": 30,
        "unweighted_n": "n_observations",
        "no_switcher_cell": "uncertainty_not_estimable",
    }
    module = _registered_script()
    assert module._awaiting(block) == []


def test_memo_small_cell_rule_uses_what_the_artifact_carries():
    """d411 item (g) flags cells by their unweighted n, which the
    tabulation reports per cell as ``n_observations``; and in a cell where
    nobody's poverty status changes, Delta and its design SE are both 0,
    which is why the memo reports that cell's uncertainty as not
    estimable rather than as SE 0.  INVENTED rows only."""

    rows = pd.DataFrame(
        {
            "observation_id": ["o1", "o2", "o3", "o4"],
            "person_id": [1, 2, 3, 4],
            "family_unit_id": [10, 20, 30, 40],
            "weight": [1.0, 2.0, 1.0, 3.0],
            "sex": ["female", "female", "male", "male"],
            "marital_status_4": [
                "never_married",
                "never_married",
                "married",
                "married",
            ],
            "birth_year": [1937, 1939, 1941, 1943],
            "stratum": [1, 1, 2, 2],
            "cluster": [1, 2, 1, 2],
            # nobody in never_married switches; one married member enters
            "poor_baseline": [True, False, False, False],
            "poor_reform": [True, False, True, False],
        }
    )
    result = ut.tabulate_uniform_cut(
        rows,
        data_provenance="invented",
        design=rows[["stratum", "cluster"]],
    )
    entry = {cell["cell"]: cell for cell in result["cells"]}
    assert entry["never_married"]["n_observations"] == 2
    assert entry["never_married"]["delta"] == 0.0
    assert entry["never_married"]["design_se"]["delta"]["se"] == 0.0
    assert entry["married"]["delta"] > 0.0
    assert entry["married"]["design_se"]["delta"]["se"] > 0.0


def _registered_script():
    spec = importlib.util.spec_from_file_location(
        "_registered", ROOT / "scripts" / "run_track_u_registered.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_nothing_awaits_max_in_the_block_or_the_code(block):
    """Since u1-ratified-1 (cos decision d411) nothing awaits Max: no code
    parameter's ``awaiting`` names him, every pending decision records the
    ratification that fixed it, and the block holds no ``awaiting`` key,
    so the registered run's ratification scan passes.  Regression history
    (independent review of u1-draft-5): withdrawing row U6 once removed
    the block's only ``awaiting`` for decision 8 while the code still
    listed it as awaiting Max; this test holds the two together.
    """

    pending = [
        item
        for decisions in (
            age67.pending_decisions(),
            ap.pending_decisions(),
            ut.pending_decisions(),
        )
        for item in decisions
    ]
    assert pending
    assert {item.awaiting for item in pending} == {FIXED}
    assert _registered_script()._awaiting(block) == []
    assert "plan_decisions" not in block
    # d189 decided the SSI rule and the claim class (2026-09-24)
    assert block["ssi"]["decided"] == "d189"
    assert block["ssi"]["rule"] == ap.AdjustedPovertySpec().ssi_rule


def test_decisions_record_max_rulings_equal_to_the_code(block):
    """u1-ratified-1: the section 15 ``decisions`` block records Max's
    rulings (d189 and d411) in the E1 section 21 form, equal to the code's
    ``MAX_RULINGS``, and each ruling equals the code default or constant it
    fixes."""

    decisions = block["decisions"]
    assert decisions["ruled_by"] == "Max"
    assert decisions["ruled_on"] == D411_RULED_AT[:10] == "2026-09-26"
    rulings = track_u_rows.MAX_RULINGS
    assert set(decisions) == set(rulings) | {"ruled_by", "ruled_on"}
    check = track_u_rows.check_rulings_against_block(block)
    assert check == {"rulings_checked": sorted(rulings), "rulings_equal": True}
    for name, entry in rulings.items():
        assert "ruling" in entry, name
        expected = "d189" if name in D189_FIELDS else "d411"
        assert entry["decision_record"] == expected, name
        if expected == "d411":
            assert re.fullmatch(r"\([a-g]\)", entry.get("item", "(a)")), name
    # each ruling is the code's default or constant
    spec = ap.AdjustedPovertySpec()
    assert rulings["claim_class"]["ruling"] == block["claim_class"]["class"]
    assert rulings["ssi_rule"]["ruling"] == spec.ssi_rule
    assert rulings["ssi_rule"]["registered_as"] == ["U2", "U3"]
    assert rulings["headline_row"]["ruling"] == track_u_rows.PRIMARY_ROW
    assert rulings["headline_row"]["rule"] == track_u_rows.HEADLINE_RULE
    assert rulings["headline_row"]["registration_states"] == [
        "u1_matches_the_report_birth_year_mix",
        "u0_omits_the_uncut_1936_birth_year",
    ]
    assert rulings["rows"]["ruling"] == list(track_u_rows.REGISTERED_ROWS)
    assert rulings["rows"]["ruling"] == list(block["rows"])
    assert rulings["financial_assets"]["ruling"] == spec.financial_assets
    assert rulings["financial_assets"]["registered_as"] == ["U7", "U7-F"]
    assert rulings["acceptance_rule"]["ruling"] is block["acceptance_rule"]
    assert rulings["cut_start_year"]["ruling"] == spec.cut_start_year
    assert rulings["definitions_extract"]["sha256"] == (
        block["target"]["definitions_extract"]["sha256"]
    )
    assert rulings["rules_implementation"]["ruling"] == (
        "python_income_concept_not_axiom"
    )
    assert "Python income concept (not Axiom)" in ap.OUTPUT_LABELS
    registration = rulings["ratification_and_registration"]
    assert registration["publishes_regardless"] is True
    assert registration["registration_describes"] == (
        "static_simulation_on_psid_observed_incomes"
    )
    # d411 item (g): the freeze defaults, except the memo's small cells
    assert rulings["freeze_defaults"]["except"] == ["memo_small_cells"]
    assert rulings["memo_small_cells"]["declined"] == ["no_small_cell_flag"]
    assert rulings["memo_small_cells"]["item"] == "(g)"


def test_no_ratified_text_registers_a_withdrawn_or_absent_row(block, text):
    """d411 item (a) registers U0, U1-U5, U7-U10, U0-F, U2-F-U5-F and
    U7-F-U10-F.  U6 (withdrawn in u1-draft-5) and U1-F (never defined) are
    registered nowhere: not in the block's rows, the code's rulings or
    rows, the section 11 table, section 16's rulings, or the ratification
    record."""

    registered = {
        "U0",
        "U1",
        "U2",
        "U3",
        "U4",
        "U5",
        "U7",
        "U8",
        "U9",
        "U10",
        "U0-F",
        "U2-F",
        "U3-F",
        "U4-F",
        "U5-F",
        "U7-F",
        "U8-F",
        "U9-F",
        "U10-F",
    }
    assert set(block["rows"]) == registered
    assert set(track_u_rows.MAX_RULINGS["rows"]["ruling"]) == registered
    assert set(track_u_rows.REGISTERED_ROWS) == registered
    assert "U1-F" not in text
    table = _section(text, "11", "12").split("| Row | Field |")[1]
    table_rows = [
        line.split("|")[1].strip().strip("*")
        for line in table.splitlines()
        if line.startswith("| ") and not line.startswith("|---")
    ]
    assert "U6" not in table_rows
    # no range in section 11 (which registers the rows) spans U6
    rows_section = _flat(_section(text, "11", "12"))
    assert "U2-F–U5-F and U7-F–U10-F (U2-F, U3-F, U4-F, U5-F, U7-F" in (
        rows_section
    )
    assert "as U2–U5 and U7–U10" in rows_section
    for spanning in ("U2 … U10", "U2-F … U10-F", "U1–U10", "U2–U10"):
        assert spanning not in rows_section, spanning
    for number, following in (("16", "17"), ("20", None)):
        section = (
            _section(text, number, following)
            if following
            else text.split(f"## {number}. ")[1]
        )
        assert not re.search(r"\bU6\b", section), number
    ruling = _flat(_section(text, "16", "17"))
    assert (
        "U0; U1, U2, U3, U4, U5, U7, U8, U9 and U10; U0-F; and U2-F, U3-F, "
        "U4-F, U5-F, U7-F, U8-F, U9-F and U10-F on U0-F's population"
    ) in ruling


def test_section_7_discloses_the_birth_year_mix(text):
    """d411 item (a): the registration says U1 matches the Report's
    birth-year mix and U0 omits the 1936 birth year, which this
    specification reads as uncut in the Report; section 7 states both, on
    the specification's own reading of the cut's start."""

    section = _flat(_section(text, "7", "8"))
    assert (
        "so its 1936 birth year, 67 in 2003, is uncut at its age-67 year"
        in (section)
    )
    disclosure = section.split(
        "**Birth-year mix (disclosed; d411 item (a)).**"
    )[1]
    assert "U0 omits the 1936 birth year" in disclosure
    assert "reads as uncut in the Report" in disclosure
    assert "U1 is the registered row whose birth-year mix matches" in (
        disclosure
    )
    assert "one cross-section's worth of weight (§3)" in disclosure
    # the code agrees: U0 and U0-F hold no 1936 observation, U1 does, and
    # the primary's 2004 start leaves 1936 uncut
    for row, has_1936 in (("U0", False), ("U0-F", False), ("U1", True)):
        plan = age67.observation_plan(age67.Age67Spec(row=row))
        assert (1936 in {b for b, _, _, _ in plan}) is has_1936, row
    assert ap.AdjustedPovertySpec().cut_start_year == 2004 > 1936 + 67


def test_section_10a_states_the_memo_small_cell_rule(text):
    """d411 item (g): the memo flags each cell under an unweighted n of 30
    and reports a no-switcher cell as 'uncertainty not estimable'; the
    section says it is a memo rule, not a code change."""

    section = _flat(_section(text, "10a", "11"))
    assert (
        "**Acceptance:** none (ruled by Max, d411 item (c); §16 ruling 8)"
        in (section)
    )
    small = section.split("**Small cells (ruled by Max, d411 item (g)")[1]
    assert "`n_observations`" in small and "under 30" in small
    assert '"uncertainty not estimable", not as a design SE of 0' in small
    # the floor is undefined, never zero, with fewer than two usable seeds
    # (section 10), so the no-switcher floor is 0 only where it is defined
    assert "so the floor, where it is defined, is 0 too" in small
    assert ut.MIN_FLOOR_SEEDS == 2
    assert "no computation of the code or the run artifact changes" in small
    assert "(`MAX_RULINGS`, §15)" in small


def test_the_ratification_record_closes_the_specification(text):
    """u1-ratified-1: the last section records d411's ruling verbatim and
    what the #42 registration states."""

    headings = re.findall(r"^## (\d+)\. ", text, re.MULTILINE)
    assert headings[-1] == "20"
    assert "## 20. Ratification record\n" in text
    assert "## 20. Card for Max" not in text
    record = _flat(text.split("## 20. Ratification record")[1])
    assert f'"{D411_RULING}"' in record
    assert f"`ruled_at` {D411_RULED_AT}" in record
    assert "The issue #42 registration comment follows the merge" in record
    # the card's cos record was corrected before the ruling (its notes
    # keep the previous text); the record says what changed without
    # naming the withdrawn row
    assert (
        "The card's cos record was corrected on 2026-09-25, before the "
        "ruling, after an independent skeptic's check"
    ) in record
    assert "listed U7 twice" in record
    assert "withdrawn in `u1-draft-5`" in record
    assert "headline row (U0)" in record
    assert "static simulation on PSID-observed incomes" in record
    assert "U1 matches the Report's birth-year mix" in record
    assert "U0 omits the 1936 birth year" in record
    assert "`scripts/run_track_u_registered.py --headline-row U0`" in record
    changelog = _flat(_section(text, "19", "20").split("\n- `")[1])
    assert changelog.startswith(
        "u1-ratified-1` (2026-09-26; cos decision d411)"
    )


def test_rows_name_real_alternatives(block):
    rows = block["rows"]
    fallback = {f"{row}-F" for row in ("U2", "U3", "U4", "U5", "U7")} | {
        f"{row}-F" for row in ("U8", "U9", "U10")
    }
    # second referee S5 and S7 withdrew U6 and U-inst; S8 added the -F
    # alternatives on U0-F's population
    assert (
        set(rows)
        == {
            "U0",
            "U1",
            "U2",
            "U3",
            "U4",
            "U5",
            "U0-F",
            "U7",
            "U8",
            "U9",
            "U10",
        }
        | fallback
    )
    assert set(track_u_rows.FALLBACK_ALTERNATIVES.values()) == fallback
    for base, alternative in track_u_rows.FALLBACK_ALTERNATIVES.items():
        entry = dict(rows[alternative])
        assert entry.pop("population") == "birth_years_1941_1943_1945"
        # u1-draft-7: the fallback rule is resolved; no row awaits Max
        assert "awaiting" not in entry
        assert entry == rows[base], alternative
    for row in rows.values():
        if row.get("status") == "not_built":
            continue
        overrides = {
            key: value
            for key, value in row.items()
            if key in ap.AdjustedPovertySpec().as_dict()
        }
        ap.AdjustedPovertySpec(**overrides)
    assert rows["U1"]["population"] == "all_ten_birth_years"
    assert rows["U0-F"]["population"] == "birth_years_1941_1943_1945"
    assert rows["U0-F"]["on"] == "U0"
    # u1-draft-7: every row is built (U7 and U7-F included), and the code's
    # rows equal the block's
    assert [name for name, row in rows.items() if "status" in row] == []
    assert rows["U7"] == {"financial_assets": "wealth1_plus_employer_dc"}
    assert "awaiting" not in rows["U0-F"]
    assert track_u_rows.check_rows_against_block(block)["rows_equal_the_block"]


def test_cells_and_uncertainty_match_the_tabulation(block):
    cells = block["cells"]
    assert cells["column"] == ut.COMPARATOR_COLUMN
    assert cells["scored"] == list(ut.DEFAULT_CELLS)
    assert cells["secondary"] == list(ut.OPTIONAL_CELLS)
    assert cells["unclassified_marital_cells"] == (
        ut.TabulationConfig().unclassified_marital_cells
    )
    assert cells["not_computed"] == list(ut.NOT_COMPUTED_REPORT_ROWS)
    assert block["comparison"]["comparator_interval"] == (
        "whole_number_rounding_level_0_5_difference_1"
    )
    uncertainty = block["uncertainty"]
    config = ut.TabulationConfig()
    assert uncertainty["draws"] == config.as_dict()["draws"] == 1
    assert uncertainty["floor"]["seeds"] == list(config.floor_seeds)
    assert uncertainty["floor"]["fraction"] == ut.FLOOR_FRACTION
    assert uncertainty["floor"]["min_usable_seeds"] == ut.MIN_FLOOR_SEEDS
    assert uncertainty["floor"]["split_unit"] == ut.FLOOR_SPLIT_UNIT
    assert config.as_dict()["floor_split_unit"] == ut.FLOOR_SPLIT_UNIT
    design = uncertainty["design_se"]
    assert design["domain"] == config.design_se_domain
    assert design["domain"] in ut.DESIGN_SE_DOMAINS
    assert config.design_standard_errors


def test_named_deltas_equal_the_runner(text):
    section = _section(text, "12", "13")
    bullets = []
    for line in section.splitlines():
        if line.startswith("- "):
            bullets.append(line[2:])
        elif bullets and line.startswith("  ") and line.strip():
            bullets[-1] += " " + line.strip()
    cleaned = [bullet.rstrip(";.") for bullet in bullets]
    assert cleaned == list(runner.NAMED_DELTAS)


def test_section_16_records_every_ruling_and_the_frozen_list(text):
    """u1-ratified-1: section 16 is "Decisions (ruled by Max, ...)", quotes
    d189's and d411's rulings verbatim, names every ruling field of
    ``MAX_RULINGS`` and lists the freeze defaults, with d411 item (g)'s
    small-cell rule in place of the filed default (no small-cell flag)."""

    assert "## 16. Decisions (ruled by Max, 2026-09-24 and 2026-09-26)\n" in (
        text
    )
    section = _section(text, "16", "17")
    flat = _flat(section)
    assert (
        "d189's ruling reads \"Yes to Track U with the SSI offset rule for "
        "existing recipients (Max in chat 2026-09-24); Max will download the "
        'PSID 2005/2007 wealth supplements with his simba login"'
    ) in flat
    assert f'd411\'s reads "{D411_RULING}"' in flat
    for name in track_u_rows.MAX_RULINGS:
        assert f"(`{name}`;" in flat, name
    for number in range(1, 15):
        assert f"{number}. **" in section, number
    ssi = next(
        item for item in ap.pending_decisions() if item.field == "ssi_rule"
    )
    assert ap.D189_RULING in ssi.default_basis
    assert "d194" in flat
    assert "fallback rule" in flat
    assert "**Ruling:** 2004, keyed on each member's age-67 year" in flat
    frozen = flat.split("**Frozen by this version (d411 item (g);")[1].split(
        "The Census threshold files"
    )[0]
    for phrase in (
        "cut rate (0.13)",
        "retirement-account income (remove the head's)",
        "farm asset share (0.5",
        "annuity lives (FU head rule)",
        "annuitant ages (derived birth year)",
        "unresolved marital status (relationship code)",
        "design SE (full-design domain)",
        "real rate (3 percent; 2 percent an unscored sensitivity)",
        "U1 1936 weight (1)",
        "the memo's small-cell rule (ruling 14",
        "the institution income rule (`excluded`; used by no registered row)",
    ):
        assert phrase in frozen, phrase
    assert "no small-cell flag in the memo" not in flat
    small = flat.split("14. **Memo small cells** (`memo_small_cells`;")[1]
    assert "under 30" in small
    assert '"uncertainty not estimable", not as SE 0' in small
    assert "no small-cell flag, which was declined" in small
    # every pending field of the code is listed by the code
    assert {item.field for item in age67.pending_decisions()} == set(
        age67.Age67Spec().as_dict()
    )
    fields = {item.field for item in ap.pending_decisions()}
    for name in (
        "retirement_account_income_rule",
        "farm_asset_share",
        "financial_assets",
        "annuity_lives",
        "real_interest_rate",
    ):
        assert name in fields


def test_referee_passes_are_recorded(block, text):
    first, second = block["referee_passes"]
    assert first["object_version"] == "u1-draft-2"
    assert first["object_commit"] == "8d7e7431"
    assert first["required_changes"] == 17
    assert first["applied_in"] == "u1-draft-4"
    assert second["object_version"] == "u1-draft-4"
    assert second["object_commit"] == "37a94ea2"
    assert second["required_changes"] == 9
    assert second["applied_in"] == "u1-draft-5"
    section = _section(text, "17", "18")
    for entry in (first, second):
        assert re.fullmatch(r"[0-9a-f]{64}", entry["sha256"])
        assert entry["sha256"] in section
    assert second["object_blob_sha256"] in section
    first_pass = section.split("### 17.2")[0]
    for change in [f"R{n}" for n in range(1, 18)] + [
        f"O{n}" for n in range(1, 9)
    ]:
        assert f"| {change} " in first_pass, change
    assert "**Declined:**" in first_pass
    second_pass = section.split("### 17.3")[1]
    for change in [f"S{n}" for n in range(1, 10)] + [
        f"O{n}" for n in range(1, 11)
    ]:
        assert f"| {change} " in second_pass, change
    answers = section.split("### 17.2")[1].split("### 17.3")[0]
    for number in range(9, 15):
        assert f"{number}. **" in answers, number
    for entry in (first, second):
        report = EVIDENCE / Path(entry["report"]).name
        if not report.is_file():
            pytest.skip("the referee reports are outside this checkout")
        assert hashlib.sha256(report.read_bytes()).hexdigest() == (
            entry["sha256"]
        )


def test_invented_cases_match_the_code():
    table = ap.LifeTable(
        name=ap.INVENTED_LIFE_TABLE,
        qx={
            "male": (0.0, 0.0, 0.2, 0.5, 1.0),
            "female": (0.0, 0.0, 0.1, 0.25, 1.0),
        },
    )
    assert ap.annuity_factor_single(table, "male", 2, rate=0.25) == (
        pytest.approx(0.896)
    )
    assert ap.annuity_factor_joint(
        table, "male", 2, "female", 2, rate=0.25
    ) == pytest.approx(1.024)


def test_annuity_price_table_matches_the_committed_tables(text):
    """Section 5's prices, recomputed from the committed life tables."""

    nchs = ap.load_nchs_2000_life_table()
    ssa = ap.load_ssa_period_2004_life_table()
    section = _section(text, "5", "6")
    for age, rate in ((66, 0.03), (67, 0.03), (68, 0.03), (67, 0.02)):
        values = [
            ap.annuity_factor_single(table, sex, age, rate=rate)
            for table in (nchs, ssa)
            for sex in ("male", "female")
        ]
        line = f"| {age} | {int(rate * 100)}% | " + " | ".join(
            f"{value:.4f}" for value in values
        )
        assert line in section, line
    for table, rate in ((nchs, 0.03), (ssa, 0.03), (nchs, 0.02), (ssa, 0.02)):
        joint = ap.annuity_factor_joint(
            table, "male", 67, "female", 67, rate=rate
        )
        assert f"{joint:.4f}" in section


def test_u3_is_never_called_a_bound(text):
    """Referee O4: U3 is the largest SSI response of the three rules, not a
    bound on DYNASIM's simulation.

    Regression (independent review, 2026-09-24): after the labels were
    dropped from ``SSI_RULES`` and the rows, the income concept's module
    text still called U3 "an upper bound" across a line break, which a
    line-by-line search misses; the check collapses whitespace first.
    """

    sources = {
        "adjusted_poverty module text": ap.__doc__,
        "adjusted_poverty.SSI_RULES": " ".join(ap.SSI_RULES.values()),
        "registered rows": " ".join(
            row.description for row in track_u_rows.REGISTERED_ROWS.values()
        ),
        "specification": text,
    }
    for name, source in sources.items():
        flat = " ".join(source.split()).lower()
        assert "upper bound" not in flat, name
    assert "the largest SSI response" in " ".join(ap.__doc__.split())


def test_section_9_names_where_members_of_a_family_differ(text):
    """Section 9's family-level claim holds under ``fu_head_rule`` except in
    U4 (B and T by role) and under U1, where the primary's 2004 start
    follows each member's age-67 year (:func:`adjusted_poverty.
    cut_applies`); regression (independent review, 2026-09-24): the
    exception was missing (it was row U6's until u1-draft-5)."""

    section = " ".join(_section(text, "9", "10").split())
    assert "except in row U4 and under U1" in section
    assert "Under row U4" in section
    assert "Under U1 the cut follows each member's own age-67" in section
    assert ap.CUT_START_YEAR_RULE == (
        "cut_when_birth_year_plus_67_at_or_after_start"
    )
