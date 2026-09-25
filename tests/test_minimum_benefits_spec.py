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
    assert block["version"] == "m1-draft-1"
    assert block["status"] == "draft_for_referee"
    assert block["claim_class"]["awaiting"] == pol.DECISION_RECORD
    assert block["acceptance_rule"] is None
    assert block["labels"] == list(OUTPUT_LABELS)
    assert block["target"]["comparator_values"] == (
        "sealed_comparator_side_not_opened_by_builder"
    )


def test_status_line_does_not_claim_ratification(text):
    status = text.split("- **Specification:**")[0]
    assert "draft for the referee" in status
    assert "Nothing here is ratified" in status
    assert "d219" in status


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


def test_every_d219_item_awaits_max_at_its_default(block):
    awaiting = block["decisions_awaiting_max"]
    assert list(awaiting) == list(spec.d219_decision_fields())
    policy = pol.TrackMPolicy()
    for number, (name, entry) in enumerate(awaiting.items(), start=1):
        assert entry["item"] == number
        assert entry["decision_record"] == "d219"
        assert entry["proposed_default"] == spec.decision_value(policy, name)
    assert block["decisions"] == {}


def test_the_draft_cannot_authorize_a_registered_run(block):
    with pytest.raises(ValueError, match="authorizes no real-data run"):
        spec.check_specification_for_registered_run(block)


def _ratified(block: dict) -> dict:
    ratified = json.loads(json.dumps(block))
    ratified["status"] = "ratified_frozen"
    ratified["version"] = "m1-ratified-1"
    ratified["decisions_awaiting_max"] = {}
    ratified["decisions"] = {
        name: {"ruling": entry["proposed_default"]}
        for name, entry in block["decisions_awaiting_max"].items()
    }
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
    ruled_other = json.loads(json.dumps(ratified))
    ruled_other["decisions"]["order"] = {"ruling": pol.ORDER_CUT_AFTER_FLOOR}
    with pytest.raises(ValueError, match="departs"):
        spec.check_specification_for_registered_run(ruled_other)
    # A ruling the configuration follows passes the ruling step, and the
    # block must then carry that configuration.
    reversed_policy = pol.TrackMPolicy(order=pol.ORDER_CUT_AFTER_FLOOR)
    with pytest.raises(ValueError, match="differ"):
        spec.check_specification_for_registered_run(
            ruled_other, reversed_policy
        )
    ruled_other["policy"] = reversed_policy.as_dict()
    spec.check_specification_for_registered_run(ruled_other, reversed_policy)


def test_pending_decisions_are_listed_in_the_text(text):
    section = text.split("## 20. Pending decisions")[1].split("## 21.")[0]
    assert "d219" in section
    for item in pol.pending_decisions():
        if item.card_item is not None:
            assert f"`{item.field}`" in section


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
