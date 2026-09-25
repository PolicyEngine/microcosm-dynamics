"""Consistency checks for the exercise 4 (Track M) specification draft.

``docs/design/minimum_benefits_comparison.md`` is read by downstream code
through its machine-readable JSON block (section 19).  These tests hold
that block to the code (the options, the policy defaults, the registered
rows, the cells, the labels and the structural-count universe), check that
the draft cannot authorize a registered run, and recompute the draft's
INVENTED worked cases.  They use only the document and the code: no PSID
value, no model output and no comparator value.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from populace_dynamics.min_benefit_track_m import (
    OUTPUT_LABELS,
    rules,
    structure,
)
from populace_dynamics.min_benefit_track_m import policy as pol
from populace_dynamics.min_benefit_track_m import specification as spec

SPEC_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "design"
    / "minimum_benefits_comparison.md"
)


@pytest.fixture(scope="module")
def text() -> str:
    return SPEC_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def block(text: str) -> dict:
    blocks = re.findall(r"```json\n(.*?)\n```", text, re.DOTALL)
    assert len(blocks) == 1
    parsed = json.loads(blocks[0])
    assert parsed == spec.m1_parameter_block(SPEC_PATH)
    return parsed


def test_block_identity_and_status(block):
    assert spec.M1_SPECIFICATION_PATH == SPEC_PATH
    assert block["specification"] == pol.SPECIFICATION_ID
    assert block["version"] == "m1-draft-2"
    assert block["status"] == "draft_referee_changes_applied"
    assert block["claim_class"] == {
        "ruled": pol.CLAIM_CLASS,
        "decision_record": pol.DECISION_RECORD,
        "item": 2,
    }
    assert block["acceptance_rule"] is None
    assert block["labels"] == list(OUTPUT_LABELS)
    assert block["target"]["comparator_values"] == (
        "sealed_comparator_side_not_opened_by_builder"
    )
    assert "max_ruling_d219_open" not in block["blocked_by"]
    assert (
        "independent_check_of_m1_draft_2_then_ratification_by_merge"
        in block["blocked_by"]
    )


def test_status_line_records_the_rulings_and_claims_no_ratification(text):
    status = text.split("- **Specification:**")[0]
    assert "draft with the referee's required changes applied" in status
    assert "Nothing here is ratified" in status
    for record in ("d219", "d279", "d280"):
        assert record in status
    assert "ruled 2026-09-24 21:44" in status
    assert "independent check" in status
    assert "pending" not in status


def test_no_d219_item_is_left_pending_in_the_text(text):
    flat = " ".join(text.split())
    assert "pending)" not in flat
    assert "d219, open" not in flat
    for item in (1, 2, 3, 5, 6, 7, 8):
        assert f"d219 item {item}, accepted 2026-09-24" in flat, item


def test_block_matches_the_code(block):
    assert spec.specification_code_check(block) == {
        "consistent": True,
        "mismatches": [],
    }
    assert block["snapshot"] == {
        "wave": pol.SNAPSHOT_WAVE,
        "income_year": pol.SNAPSHOT_INCOME_YEAR,
    }
    assert block["cells"]["headline"] == {"option": 2, "row": "all"}


def test_population_matches_the_structure_module(block):
    population = block["population"]
    assert population["weight"] == structure.ANCHOR_2023.weight_variable
    assert population["born_on_or_before"] == structure.LAST_BIRTH_YEAR
    assert population["receipt"] == {
        "person_level": structure.SOCIAL_SECURITY_2023["amount"][0],
        "family_file": [
            structure.FAMILY_2023["rp_amount"][0],
            structure.FAMILY_2023["spouse_amount"][0],
        ],
    }
    assert population["design"] == {"stratum": "ER31996", "cluster": "ER31997"}


def test_every_ruling_is_recorded_as_the_code_records_it(block):
    assert block["decisions_awaiting_max"] == {}
    decisions = block["decisions"]
    assert decisions == spec.expected_decisions()
    assert decisions["ruled_by"] == "Max"
    assert list(decisions)[1:] == list(pol.MAX_RULINGS)
    policy = pol.TrackMPolicy()
    for name in spec.ruled_fields():
        assert decisions[name]["ruling"] == spec.decision_value(policy, name)
    assert spec.d219_decision_fields() == tuple(
        field for _, (field, _) in sorted(pol.d219_items().items())
    )
    for name in spec.d219_decision_fields():
        assert decisions[name]["decision_record"] == "d219"
        assert decisions[name]["ruled_on"] == "2026-09-24"
    assert decisions["covered_earnings_rule"]["decision_record"] == "d280"
    assert decisions["census_threshold_download"]["decision_record"] == (
        "d279"
    )


def test_the_draft_cannot_authorize_a_registered_run(block):
    with pytest.raises(ValueError, match="authorizes no real-data run"):
        spec.check_specification_for_registered_run(block)


def _ratified(block: dict) -> dict:
    """The ratified text changes the status and version only (R1)."""

    ratified = json.loads(json.dumps(block))
    ratified["status"] = "ratified_frozen"
    ratified["version"] = "m1-ratified-1"
    return ratified


def test_the_gate_checks_every_step(block):
    ratified = _ratified(block)
    spec.check_specification_for_registered_run(ratified)
    referee = {**ratified, "version": "m1-ratified-after-referee-1"}
    with pytest.raises(ValueError, match="authorizes no"):
        spec.check_specification_for_registered_run(referee)
    pending = {**ratified, "decisions_awaiting_max": {"order": {}}}
    with pytest.raises(ValueError, match="awaiting Max"):
        spec.check_specification_for_registered_run(pending)
    unruled = {**ratified, "decisions": {}}
    with pytest.raises(ValueError, match="no ruling"):
        spec.check_specification_for_registered_run(unruled)
    missing = json.loads(json.dumps(ratified))
    del missing["decisions"]["covered_earnings_rule"]
    with pytest.raises(ValueError, match="covered_earnings_rule"):
        spec.check_specification_for_registered_run(missing)
    # A block recording another ruling than the code's is refused ...
    ruled_other = json.loads(json.dumps(ratified))
    ruled_other["decisions"]["order"]["ruling"] = pol.ORDER_CUT_AFTER_FLOOR
    with pytest.raises(ValueError, match="differ from the code's record"):
        spec.check_specification_for_registered_run(ruled_other)
    # ... and so is a configuration that departs from a ruling.
    with pytest.raises(ValueError, match="departs"):
        spec.check_specification_for_registered_run(
            ratified, pol.policy_for_row("MS2")
        )
    # A frozen choice the configuration changes makes the block differ.
    with pytest.raises(ValueError, match="differ"):
        spec.check_specification_for_registered_run(
            ratified, pol.policy_for_row("MS6")
        )


def test_the_decisions_section_lists_every_ruling(text):
    section = text.split("## 20. Decisions (ruled by Max")[1].split("## 21.")[
        0
    ]
    for record in ("d219", "d279", "d280"):
        assert record in section
    for name in pol.MAX_RULINGS:
        assert f"`{name}`" in section, name
    frozen = section.split("**Frozen by this version")[1]
    for phrase in (
        "statutory computation years",
        "statutory death computation",
        "$50 a quarter",
        "next-wave labor income",
    ):
        assert phrase in frozen


def test_the_referee_section_records_every_required_change(text):
    section = text.split("## 21. Referee pass")[1].split("## 22.")[0]
    for number in range(1, 11):
        assert f"| R{number}. " in section, number
    assert "Declined in part" in section
    for question in range(1, 11):
        assert f"| Q{question} |" in section, question


def test_invented_cases_in_the_text_match_the_code(text):
    section = text.split("## 16. Invented worked cases")[1].split("## 17.")[0]
    thresholds = rules.AgedThresholds({2010: 10_000.0}, {"kind": "INVENTED"})
    cases = {
        "A": (600.0, 30, None),
        "B": (600.0, 9, None),
        "C": (900.0, 40, None),
        "D": (500.0, 15, 1948 + 44),
        "H": (953.0, 40, None),
        "I": (700.0, 20, None),
    }
    for name, (pia, years, onset) in cases.items():
        worker = rules.WorkerInputs(
            pia=pia,
            work_years=years,
            first_pia_year=2010,
            threshold_year=2010,
            birth_year=1948,
            di_onset_year=onset,
        )
        two = rules.evaluate_worker(worker, 2, thresholds=thresholds, nawi={})
        one = rules.evaluate_worker(worker, 1, thresholds=thresholds, nawi={})
        relative = 100 * rules.relative_to_option_1(two, one)
        row = next(
            line
            for line in section.splitlines()
            if line.startswith(f"| {name}.")
        )
        sign = "+" if relative >= 0 else "−"
        assert f"{sign}{abs(relative):.2f}%" in row, name
        if two.minimum:
            assert f"${two.minimum:,.2f}" in row, name
