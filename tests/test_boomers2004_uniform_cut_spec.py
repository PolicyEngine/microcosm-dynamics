"""Consistency checks for the exercise 2 (Track U) specification draft.

``docs/design/boomers2004_uniform_cut_comparison.md`` is read by
downstream lanes through its machine-readable JSON block (§15).  These
tests hold that block to the code's defaults and constants (the income
concept, the cohort builder, the reader tables and the tabulation), so a
draft change and a code change cannot drift apart silently.  They use
only the document and the code: no PSID value, no model output and no
comparator value.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from populace_dynamics.cohorts import age67
from populace_dynamics.data import family_income
from populace_dynamics.estimates import adjusted_poverty as ap
from populace_dynamics.estimates import uniform_cut_tabulation as ut

SPEC_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "design"
    / "boomers2004_uniform_cut_comparison.md"
)


@pytest.fixture(scope="module")
def text() -> str:
    return SPEC_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def block(text: str) -> dict:
    blocks = re.findall(r"```json\n(.*?)\n```", text, re.DOTALL)
    assert len(blocks) == 1
    return json.loads(blocks[0])


def test_block_identity_and_status(block):
    assert block["specification"] == "boomers2004_uniform_cut_exercise2"
    assert block["status"] == "draft_for_referee"
    assert block["claim_class"]["awaiting"] == "d189"
    assert block["acceptance_rule"] is None
    assert block["labels"] == list(ap.OUTPUT_LABELS)


def test_status_line_does_not_claim_ratification(text):
    status = text.split("- **Specification:**")[0]
    assert "draft for the referee" in status
    assert "Nothing here is ratified" in status


def test_population_matches_the_builder(block):
    population = block["population"]
    assert population["primary_birth_years"] == list(age67.PRIMARY_BIRTH_YEARS)
    assert population["u1_birth_years"] == [
        age67.ALL_BIRTH_YEARS[0],
        age67.ALL_BIRTH_YEARS[-1],
    ]
    spec = age67.Age67Spec()
    assert population["presence"] == spec.presence
    assert population["seed_wave_rule"] == spec.seed_wave_rule
    assert population["separated_is_married"] == spec.separated_is_married
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


def test_income_concept_matches_the_spec_defaults(block):
    spec = ap.AdjustedPovertySpec()
    concept = block["income_concept"]
    assert concept["income_unit"] == spec.income_unit
    assert concept["asset_income_rule"] == spec.asset_income_rule
    assert concept["asset_income_items"] == list(
        family_income.ASSET_INCOME_CONCEPTS
    )
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
    assert block["threshold"]["rule"] == spec.threshold_rule
    assert block["threshold"]["capture_status"] == "not_captured"
    assert ap.THRESHOLDS_SHA256 is None
    assert block["cut"]["rate"] == spec.cut_rate == block["target"]["cut_rate"]
    ssi = block["ssi"]
    assert ssi["rule"] == spec.ssi_rule
    assert ssi["deeming"] == spec.ssi_deeming
    assert ssi["ofum_unit"] == spec.ofum_ssi_unit
    assert ssi["parameters"]["sha256"] == ap.SSI_PARAMETERS_SHA256


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
        "U7",
        "U8",
        "U9",
        "U10",
        "U-inst",
    }
    for name, row in rows.items():
        if row.get("status") in ("not_built", "counted_only_no_income_rule"):
            continue
        overrides = {
            key: value
            for key, value in row.items()
            if key in ap.AdjustedPovertySpec().as_dict()
        }
        ap.AdjustedPovertySpec(**overrides)
        if "population" in row:
            assert row["population"] == "all_ten_birth_years", name
    assert rows["U-inst"]["presence"] == "in_family_or_institution"
    age67.Age67Spec(presence=rows["U-inst"]["presence"])


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
    assert uncertainty["floor"]["split_unit"] == "family_unit_id"


def test_pending_decisions_are_listed_in_the_text(text):
    section = text.split("## 16. Pending decisions")[1].split("## 17.")[0]
    assert "d189" in section
    ssi = next(
        item for item in ap.pending_decisions() if item.field == "ssi_rule"
    )
    assert "d189" in ssi.awaiting
    assert "offset for existing recipients (default)" in section


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
