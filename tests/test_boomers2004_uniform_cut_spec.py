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
    assert block["version"] == "u1-draft-4"
    assert block["status"] == "draft_for_referee"
    assert block["claim_class"]["awaiting"] == "d189"
    assert block["acceptance_rule"] is None
    assert block["labels"] == list(ap.OUTPUT_LABELS)
    assert "row_u7_not_built" in block["blocked_by"]


def test_status_line_does_not_claim_ratification(text):
    status = text.split("- **Specification:**")[0]
    assert "draft for the referee" in status
    assert "Nothing here is ratified" in status
    assert "`u1-draft-4`" in text.split("- **Plan item:**")[0]


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
        if int(wave) in family_income.WEALTH_WAVES:
            assert entry["wealth1"] == (
                family_income.wealth_variables(int(wave))["wealth1"][0]
            )
        else:
            assert entry["wealth1"] is None
            assert int(wave) in family_income.WEALTH_SUPPLEMENT_WAVES
    assert population["design"] == {"stratum": "ER31996", "cluster": "ER31997"}


def test_headline_rule_matches_the_code(block):
    headline = block["population"]["headline"]
    assert headline["rule"] == track_u_rows.HEADLINE_RULE
    assert headline["fallback_row"] == track_u_rows.FALLBACK_ROW
    assert headline["awaiting"]
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
    assert block["threshold"]["capture_status"] == "not_captured"
    assert ap.THRESHOLDS_SHA256 is None
    ssi = block["ssi"]
    assert ssi["rule"] == spec.ssi_rule
    assert ssi["deeming"] == spec.ssi_deeming
    assert ssi["ofum_unit"] == spec.ofum_ssi_unit
    assert ssi["parameters"]["sha256"] == ap.SSI_PARAMETERS_SHA256
    assert ssi["parameters"]["file"] == str(
        ap.SSI_PARAMETERS_PATH.relative_to(ROOT)
    )


def test_cut_and_threshold_years_match_the_code(block):
    spec = ap.AdjustedPovertySpec()
    cut = block["cut"]
    assert cut["rate"] == spec.cut_rate == block["target"]["cut_rate"]
    assert cut["start_year"] == spec.cut_start_year is None
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
    spec = importlib.util.spec_from_file_location(
        "_registered", ROOT / "scripts" / "run_track_u_registered.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert "comparison.acceptance.awaiting" in module._awaiting(block)
    assert "population.headline.awaiting" in module._awaiting(block)


def test_rows_name_real_alternatives(block):
    rows = block["rows"]
    assert set(rows) == {
        "U0",
        "U1",
        "U2",
        "U3",
        "U4",
        "U5",
        "U6",
        "U0-F",
        "U7",
        "U8",
        "U9",
        "U10",
        "U-inst",
    }
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
    assert rows["U-inst"]["presence"] == "in_family_or_institution"
    age67.Age67Spec(
        presence=rows["U-inst"]["presence"],
        institution_income_rule=rows["U-inst"]["institution_income_rule"],
    )
    assert rows["U6"]["on"] == "U1"
    ap.AdjustedPovertySpec(cut_start_year=rows["U6"]["cut_start_year"])
    # every row but U7 is built, and the code's rows equal the block's
    assert [name for name, row in rows.items() if "status" in row] == ["U7"]
    assert track_u_rows.check_rows_against_block(block)["rows_equal_the_block"]


def test_cells_and_uncertainty_match_the_tabulation(block):
    cells = block["cells"]
    assert cells["scored_candidates"] == list(ut.DEFAULT_CELLS)
    assert cells["optional"] == list(ut.OPTIONAL_CELLS)
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
    assert "decision 8" in section and "cut_start_year" in section
    assert "institution_income_rule = family_of_record" in section
    assert "d194" in section
    assert "fallback rule" in section
    ssi = next(
        item for item in ap.pending_decisions() if item.field == "ssi_rule"
    )
    assert "d189" in ssi.awaiting
    assert "offset for existing recipients (default)" in section
    flat = " ".join(section.split())
    for phrase in (
        "retirement-account income (remove the head's)",
        "farm asset share (0.5",
        "annuity lives (FU head rule)",
        "annuitant ages (derived birth year)",
        "unresolved marital status (relationship code)",
        "design SE (full-design domain)",
        "real rate (3 percent; 2 percent sensitivity)",
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


def test_referee_pass_is_recorded(block, text):
    (entry,) = block["referee_passes"]
    assert entry["object_version"] == "u1-draft-2"
    assert entry["object_commit"] == "8d7e7431"
    assert entry["required_changes"] == 17
    assert entry["applied_in"] == block["version"]
    assert re.fullmatch(r"[0-9a-f]{64}", entry["sha256"])
    section = _section(text, "17", "18")
    assert entry["sha256"] in section
    for change in [f"R{n}" for n in range(1, 18)] + [
        f"O{n}" for n in range(1, 9)
    ]:
        assert f"| {change} " in section, change
    assert "**Declined:**" in section
    report = EVIDENCE / Path(entry["report"]).name
    if not report.is_file():
        pytest.skip("the referee report is outside this checkout")
    assert hashlib.sha256(report.read_bytes()).hexdigest() == entry["sha256"]


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
