"""Pension documentation checks; no survey records or balances are read."""

import re

import pytest

from populace_dynamics.data import u2_source_registry as registry


@pytest.fixture(scope="module")
def pension_entries():
    return registry.load_registry("pension")["entries"]


def test_all_documented_slot_suffixes_match_registry_person(pension_entries):
    """Compact -HD/-RP labels must not accidentally become spouse fields."""
    variables = [e for e in pension_entries if e["kind"] == "variable"]
    for entry in variables:
        match = re.search(r"-\s*(HD|RP|WF|SP)\s*$", entry["label"])
        assert match is not None, entry["id"]
        slot = "head" if match[1] in {"HD", "RP"} else "wife"
        assert entry["person_slot"] == slot, entry["id"]
        assert entry["concept"].startswith(f"{slot}_"), entry["id"]
        assert entry["id"] == f"{entry['wave']}.{entry['concept']}"
        if slot == "head":
            assert "roles:2015.relationship.20" not in entry.get(
                "blocking_dependencies", []
            )
    for wave in registry.U2_SOURCE_WAVES:
        counts = [
            e
            for e in variables
            if e["wave"] == wave and e["question"] == "P45A"
        ]
        assert {e["person_slot"] for e in counts} == {"head", "wife"}
        assert len(counts) == 2


@pytest.mark.parametrize("wave", registry.U2_SOURCE_WAVES)
def test_both_people_and_previous_employers_have_complete_routes(
    pension_entries, wave
):
    by_concept = {
        entry["concept"]: entry
        for entry in pension_entries
        if entry["wave"] == wave and entry["kind"] == "variable"
    }
    for person in ("head", "wife"):
        assert by_concept[f"{person}_current_type"]["question"] == "P16"
        assert by_concept[f"{person}_current_amount"]["question"] == "P20"
        for plan in (1, 2):
            for concept, question in (
                ("type", "P46"),
                ("combo_disposition", "P48"),
                ("combo_amount", "P49"),
                ("dc_disposition", "P64"),
                ("dc_amount", "P65"),
            ):
                entry = by_concept[f"{person}_prev{plan}_{concept}"]
                assert entry["question"] == question
                assert entry["previous_plan"] == plan


def test_amount_domains_and_evidence_are_explicit(pension_entries):
    for entry in pension_entries:
        if entry["kind"] != "variable":
            continue
        position = entry["position"]
        assert position["coordinate"] == "one_based_inclusive"
        assert position["start"] > 0
        assert position["end"] - position["start"] + 1 == position["width"]
        assert any(
            c["file"].endswith(".sps") and "line" in c
            for c in entry["citations"]
        )
        assert any(
            c["file"].endswith("codebook.pdf") and "page" in c
            for c in entry["citations"]
        )
        if entry["question"] not in {"P20", "P49", "P65"}:
            continue
        expected_width = 9 if entry["question"] == "P20" else 8
        assert position["width"] == expected_width
        codes = entry["amount_codes"]
        assert codes["actual_min"] == 1
        assert codes["inapplicable"] == 0
        assert (
            codes["actual_max"]
            < codes["top"]
            < codes["dk"]
            < codes["na_refused"]
        )
        for name in ("top", "dk", "na_refused"):
            assert f"{codes[name]:,}" in entry["codebook_documentation"]
        assert entry["u2_value_handling"]["brackets"] == "not_used"


def test_2015_checkpoint_admits_the_documentary_intersection(
    pension_entries,
):
    """Amendment 5b (ratified by d637, section 16b): P46=5 reaches
    P64/P65 and P46=7 reaches P48/P49; the disputed P62ACKPT branch is
    refused, so an amount reached only through it is off-route."""
    by_id = {e["id"]: e for e in pension_entries}
    checkpoint = by_id["2015.route.formula_unknown_checkpoint"]
    assert checkpoint["status"] == "RESOLVED"
    assert checkpoint["accepted_plan_types"] == [5]
    assert set(checkpoint["rejected_plan_types"]) == {1, 7, 8, 9}
    assert "accepted_conditional_types" not in checkpoint
    assert checkpoint["refused_branch"] == (
        "P62ACKPT: P46=1 AND P52=1 AND P62AMT=DK/RF"
    )
    assert checkpoint["off_route_disposition"] == "off_route"
    assert checkpoint["adjudication"]["disposition"] == "A"
    assert checkpoint["ruling"]["amendment"] == "5b"
    assert registry.require_resolved("pension", checkpoint["id"])
    assert by_id["2015.route.previous_combined"]["accepted_plan_types"] == [7]
    assert by_id["2015.route.previous_dc_only"]["accepted_plan_types"] == [5]
    for person in ("head", "wife"):
        for plan in (1, 2):
            for item in ("dc_disposition", "dc_amount"):
                key = f"2015.{person}_prev{plan}_{item}"
                assert "blocking_dependencies" not in by_id[key], key
                assert registry.require_resolved("pension", key)


@pytest.mark.parametrize("wave", (2017, 2019, 2021, 2023))
def test_later_checkpoint_does_not_inherit_formula_unknown_route(
    pension_entries, wave
):
    by_id = {e["id"]: e for e in pension_entries}
    documented = by_id[f"{wave}.route.formula_unknown_checkpoint"]
    assert documented["accepted_plan_types"] == [5]
    assert set(documented["rejected_plan_types"]) == {1, 7, 8, 9}
    amendment = by_id[f"{wave}.route.inherited_route_amendment"]
    # Independent adjudication D: the documents resolve the DC-only route,
    # but application waits for Max's ruling on u2-draft-4 amendment 5.
    assert amendment["status"] == "RESOLVED"
    assert amendment["adjudication"]["disposition"] == "D"
    assert amendment["action"] == "refuse_pending_amendment_5_ruling"
    with pytest.raises(registry.SourceAdjudicationError, match="amendment_5"):
        registry.require_resolved("pension", amendment["id"])
    for person in ("head", "wife"):
        for plan in (1, 2):
            entry = by_id[f"{wave}.{person}_prev{plan}_dc_amount"]
            assert (
                f"pension:{amendment['id']}" in entry["blocking_dependencies"]
            )
            with pytest.raises(registry.SourceAdjudicationError):
                registry.require_resolved("pension", entry["id"])
