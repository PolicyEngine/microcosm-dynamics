"""Consistency checks for the exercise 2 (Track U) specification draft.

``docs/design/boomers2004_uniform_cut_comparison.md`` is read by
downstream lanes through its machine-readable JSON block (§15).  These
tests hold that block to the code's defaults and constants (the income
concept, the cohort builder, the reader tables, the tabulation, the
registered rows and the runner's named deltas), so a draft change and a
code change cannot drift apart silently.  They use only the document and
the code: no PSID value, no model output and no comparator value.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path

import pytest

from populace_dynamics.cohorts import age67
from populace_dynamics.data import family_income
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


def test_block_identity_and_status(block):
    assert block["specification"] == "boomers2004_uniform_cut_exercise2"
    assert block["version"] == "u1-draft-6"
    assert block["status"] == "draft_for_referee"
    # Max ruled on exercise 2 (cos decision d189, 2026-09-24): the claim
    # class is decided and no longer awaited
    assert block["claim_class"]["decided"] == "d189"
    assert "awaiting" not in block["claim_class"]
    assert block["claim_class"]["class"] == (
        "track_u_psid_realized_measurement_not_a_projection"
    )
    assert block["acceptance_rule"] is None
    assert block["labels"] == list(ap.OUTPUT_LABELS)
    # u1-draft-6: the supplements are read and d189 is decided, so only
    # the registration and row U7 still block
    assert block["blocked_by"] == [
        "issue_42_registration_absent",
        "row_u7_not_built",
    ]


def test_status_line_does_not_claim_ratification(text):
    status = text.split("- **Specification:**")[0]
    assert "draft for the referee" in status
    assert "Nothing here is ratified" in status
    assert "`u1-draft-6`" in text.split("- **Plan item:**")[0]
    assert "cos decision d189, decided" in " ".join(status.split())
    assert "Two" in status and "referee passes are recorded" in status


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
    assert headline["awaiting"]
    # with the supplements staged and adjudicated the rule gives U0
    assert headline["staged_psid_headline"] == track_u_rows.PRIMARY_ROW
    assert "decision 3, the downloads, is decided: d189" in (
        headline["awaiting"]
    )
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
    assert comparison["acceptance"]["rule"] is None
    # the pending acceptance rule is an "awaiting" key the registered run's
    # ratification scan finds
    module = _registered_script()
    assert "comparison.acceptance.awaiting" in module._awaiting(block)
    assert "population.headline.awaiting" in module._awaiting(block)


def _registered_script():
    spec = importlib.util.spec_from_file_location(
        "_registered", ROOT / "scripts" / "run_track_u_registered.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_choice_awaiting_max_is_awaited_in_the_block(block):
    """Every code parameter whose pending decision awaits Max (other than
    the freeze, Max's ratification by merge) carries an ``awaiting`` key in
    the section 15 block, so the registered run's ratification scan refuses
    the block until Max rules.

    Regression (independent review of u1-draft-5, 2026-09-24): withdrawing
    row U6 removed the block's only ``awaiting`` for plan decision 8 (the
    cut's start year, now the primary's ``cut_start_year = 2004``), which
    ``adjusted_poverty.pending_decisions`` and section 16 still list as
    awaiting Max's confirmation of the scorecard's "from 2004" wording.
    """

    where = {"cut_start_year": "cut.awaiting"}
    awaiting_max = {
        item.field
        for decisions in (
            age67.pending_decisions(),
            ap.pending_decisions(),
            ut.pending_decisions(),
        )
        for item in decisions
        if item.awaiting.startswith("Max")
    }
    assert awaiting_max == set(where)
    found = _registered_script()._awaiting(block)
    for field, path in where.items():
        assert path in found, field
    decision = {item.field: item for item in ap.pending_decisions()}[
        "cut_start_year"
    ]
    assert "decision 8" in decision.awaiting
    assert "decision 8" in block["cut"]["awaiting"]
    # d189 decided the SSI rule and the claim class (2026-09-24): neither
    # is awaited any more
    assert "ssi.awaiting" not in found
    assert "claim_class.awaiting" not in found
    assert block["ssi"]["decided"] == "d189"
    assert block["ssi"]["rule"] == ap.AdjustedPovertySpec().ssi_rule


def test_rows_name_real_alternatives(block):
    rows = block["rows"]
    fallback = {f"{row}-F" for row in ("U2", "U3", "U4", "U5")} | {
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
        assert entry.pop("awaiting") == rows["U0-F"]["awaiting"]
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
    # every row but U7 is built, and the code's rows equal the block's
    assert [name for name, row in rows.items() if "status" in row] == ["U7"]
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


def test_pending_decisions_are_listed_in_the_text(text):
    section = _section(text, "16", "17")
    assert "d189" in section
    assert "decision 8" in section and "cut_start_year = 2004" in section
    assert "the institution income rule (used by no registered row" in (
        " ".join(section.split())
    )
    assert "d194" in section
    assert "fallback rule" in section
    ssi = next(
        item for item in ap.pending_decisions() if item.field == "ssi_rule"
    )
    assert ap.D189_RULING in ssi.default_basis
    flat = " ".join(section.split())
    assert "Decided by Max (cos decision d189, 2026-09-24)" in flat
    assert "offset for existing recipients (Max's ruling" in flat
    # the items still open after d189, stated exactly
    still_open = flat.split("Still awaiting Max")[1].split(
        "The Census threshold files"
    )[0]
    assert "these six remain open after d189" in still_open
    for item in (
        "decision 2 (",
        "decision 4 (",
        "decision 6 (",
        "decision 7 (",
        "decision 8 (",
        "the fallback rule of §11",
    ):
        assert item in still_open, item
    for phrase in (
        "retirement-account income (remove the head's)",
        "farm asset share (0.5",
        "annuity lives (FU head rule)",
        "annuitant ages (derived birth year)",
        "unresolved marital status (relationship code)",
        "design SE (full-design domain)",
        "real rate (3 percent; 2 percent sensitivity)",
        "cut start year (2004)",
        "U2-F … U10-F",
        "no card or ruling by Max on it was found",
    ):
        assert phrase in flat, phrase
    # every pending field of the code is listed by the code
    assert {item.field for item in age67.pending_decisions()} == set(
        age67.Age67Spec().as_dict()
    )
    fields = {item.field for item in ap.pending_decisions()}
    for name in (
        "retirement_account_income_rule",
        "farm_asset_share",
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
