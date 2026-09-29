"""Unit and property tests for the B0.1 revision-1 tools.

``scripts/track_b_b0_1_exposure_inventory.py`` inventories pseudo-boundary
exposure without recording content; ``scripts/track_b_b0_1_review_power.py``
restates the audit's power figures with an explicit scoring basis. These
tests use invented inputs only.
"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import track_b_b0_1_counts as frozen  # noqa: E402
import track_b_b0_1_exposure_inventory as inv  # noqa: E402
import track_b_b0_1_review_power as rp  # noqa: E402

SELECTOR = ROOT / "scripts" / "select_m6_qstar_train_only.py"


# --------------------------------------------------------------------------
# Exposure inventory
# --------------------------------------------------------------------------
def test_boundary_geometry_matches_the_selector_source():
    source = SELECTOR.read_text(encoding="utf-8")
    match = re.search(r"^PSEUDO_BOUNDARIES = \(([^)]*)\)", source, re.M)
    assert match is not None
    declared = tuple(int(x) for x in match.group(1).split(","))
    assert declared == inv.PSEUDO_BOUNDARIES
    assert "periods = (boundary, boundary + 2, boundary + 4)" in source
    assert inv.boundaries_touching_targets() == {
        "2008": [2012],
        "2010": [2012, 2014],
    }


@pytest.mark.parametrize(
    ("line", "family"),
    [
        ("the pseudo-boundary 2010 fit", "pseudo_boundary"),
        ('"pseudo_boundaries": [2006]', "pseudo_boundary"),
        ("a train-only selector", "train_only"),
        ("at boundary 2010 the score", "boundary_year"),
        ("the 2008-boundary floor", "boundary_year"),
        ("boundaries 2006, 2008 and 2010", "boundary_year"),
        ("selected q\\* on J(q)", "selector"),
        ("rhostar ledger", "selector"),
        ("ρ* rung", "selector"),
        ("the F1 mechanism split", "f1_mechanism"),
        ("see @fig-m6-frontier", "frontier_figure"),
    ],
)
def test_line_families_detect_each_family(line, family):
    assert family in inv.line_families(line)


@pytest.mark.parametrize(
    "line",
    [
        "frequency* of events",
        "the 2010 wave of the family file",
        "boundary year of the M6 run is 2014",
        "a plain sentence",
    ],
)
def test_line_families_ignore_unrelated_lines(line):
    assert inv.line_families(line) == set()


def test_text_ranges_merge_and_count_without_content():
    lines = ["intro"] * 30
    lines[3] = "the pseudo-boundary objective was 0.41 at 2012"
    lines[9] = "q* = 0.55"
    lines[25] = "train-only phrase"
    ranges = inv.text_ranges(lines, context=2)
    assert [(r["start"], r["end"]) for r in ranges] == [
        (2, 6),
        (8, 12),
        (24, 28),
    ]
    first, second, third = ranges
    assert first["families"] == ["pseudo_boundary"]
    assert first["decimal_tokens"] == 1 and first["target_year_tokens"] == 1
    assert second["families"] == ["selector"]
    assert third["families"] == ["train_only"]
    assert inv.range_is_value_bearing(first)
    assert inv.range_is_value_bearing(second)
    assert not inv.range_is_value_bearing(third)
    assert "0.41" not in json.dumps(ranges)


@settings(max_examples=80, deadline=None)
@given(
    secret=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        min_size=12,
        max_size=24,
    ),
    value=st.floats(min_value=-10, max_value=10, allow_nan=False),
)
def test_scan_records_no_line_content(secret, value):
    text = "\n".join(
        [
            "# note",
            f"At pseudo-boundary 2010 the {secret} score was {value:.4f}.",
            f"q* = 0.55 and {secret}",
        ]
    )
    record = inv.scan_file("docs/design/example.md", text)
    assert record is not None
    dumped = json.dumps(record)
    assert secret not in dumped
    assert f"{value:.4f}" not in dumped


def _ledger(value: float, marital_rows: bool = False) -> dict:
    cell = {"mean": value, "sd": value / 2}
    block = {
        "floor": {"earn_p10.prime": cell},
        "support": {"truth_support_rows_by_period": {"2008": 1, "2012": 2}},
    }
    rows = [{"pseudo_boundary": 2010, "count": value}]
    if marital_rows:
        rows = [{"pseudo_boundary": 2010, "first_marriage_delta": value}]
    return {
        "boundaries": {"2006": block, "2008": block, "2010": block},
        "rungs": {"0.55": {"boundaries": {"2010": block}}},
        "rows": rows,
    }


def test_json_facts_find_blocks_fields_and_years():
    facts = inv.json_boundary_facts(_ledger(0.3))
    paths = {entry["path"]: entry for entry in facts["boundary_blocks"]}
    assert set(paths) == {
        "/boundaries/{year}",
        "/rungs/{rung}/boundaries/{year}",
    }
    top = paths["/boundaries/{year}"]
    assert top["years"] == [2006, 2008, 2010]
    assert top["n_blocks"] == 3
    assert top["field_names"] == ["floor", "support"]
    assert top["descendant_year_keys"] == ["2008", "2012"]
    assert top["earnings_cells"] and not top["marital"]
    (field,) = facts["pseudo_boundary_fields"]
    assert field == {
        "path": "/rows/[]",
        "values": [2010],
        "n": 1,
        "marital": False,
    }
    assert "0.3" not in json.dumps(facts)


def test_marital_rows_are_classified_marital():
    facts = inv.json_boundary_facts(
        {"rows": [{"pseudo_boundary": 2008, "remarriage_delta": 1.5}]}
    )
    assert facts["pseudo_boundary_fields"][0]["marital"] is True
    assert (
        inv.classify("docs/analysis/example.json", "json", [], facts)
        == "marital"
    )


@settings(max_examples=60, deadline=None)
@given(
    first=st.floats(min_value=-1e6, max_value=1e6, allow_nan=False),
    second=st.floats(min_value=-1e6, max_value=1e6, allow_nan=False),
)
def test_json_facts_are_invariant_to_values(first, second):
    assert inv.json_boundary_facts(_ledger(first)) == inv.json_boundary_facts(
        _ledger(second)
    )


def test_json_string_hits_flag_selection_prose_only():
    document = {
        "entries": [
            {"reason": "At boundary 2010 the score was 0.41."},
            {"reason": "q* was chosen train-only at 0.55."},
            {"reason": "rho* shrinkage of 0.3 in the gate-1 model."},
            {"reason": "pseudo-boundary design, no numbers."},
        ]
    }
    hits = {
        tuple(entry["families"]): entry
        for entry in inv.json_string_hits(document)
    }
    assert hits[("boundary_year",)]["value_bearing"] == 1
    assert hits[("selector", "train_only")]["value_bearing"] == 1
    assert hits[("selector",)]["value_bearing"] == 0
    assert hits[("pseudo_boundary",)]["value_bearing"] == 0
    assert "0.41" not in json.dumps(inv.json_string_hits(document))
    facts = {
        **inv.json_boundary_facts(document),
        "strings": inv.json_string_hits(document),
    }
    assert inv.classify("docs/x.json", "json", [], facts) == "boundary_values"
    gate1 = {"note": "rho* shrinkage of 0.3"}
    facts = {
        **inv.json_boundary_facts(gate1),
        "strings": inv.json_string_hits(gate1),
    }
    assert inv.classify("docs/gate1_x.json", "json", [], facts) == "mentions"


def test_classification_and_q6_scope_rules():
    facts = inv.json_boundary_facts(_ledger(0.1))
    assert (
        inv.classify("docs/analysis/x.json", "json", [], facts)
        == "boundary_values"
    )
    early = inv.json_boundary_facts({"boundaries": {"2006": {"a": 1}}})
    assert (
        inv.classify("docs/analysis/x.json", "json", [], early) == "mentions"
    )
    assert inv.classify("scripts/x.py", "code", [], None) == "code"
    assert (
        inv.classify("docs/design/m6_remarriage_x.md", "text", [], None)
        == "marital"
    )
    value_range = {
        "start": 10,
        "end": 20,
        "families": ["selector"],
        "hit_lines": 1,
        "decimal_tokens": 1,
        "target_year_tokens": 0,
    }
    plain_range = dict(value_range, families=["train_only"])
    assert (
        inv.classify("docs/x.md", "text", [value_range], None)
        == "boundary_values"
    )
    assert inv.classify("docs/x.md", "text", [plain_range], None) == "mentions"
    assert inv.q6_scope("docs/x.md", "text", 100, [value_range]) == {
        "path": "docs/x.md",
        "scope": "whole_file",
        "lines": None,
    }
    assert inv.q6_scope(
        "docs/x.md", "text", 4000, [value_range, plain_range]
    ) == {"path": "docs/x.md", "scope": "line_ranges", "lines": [[10, 20]]}
    assert inv.q6_scope("x.svg", "text", 4000, [])["scope"] == "whole_file"


def test_build_inventory_excludes_its_own_record():
    files = {
        "docs/design/track_b_b0_1_audit.md": b"pseudo-boundary 2010 0.5",
        "docs/design/other.md": b"pseudo-boundary 2010 score 0.5",
        "docs/design/plain.md": b"nothing here",
    }
    record = inv.build_inventory(
        {path: "0" * 40 for path in files}, read=lambda p: files[p]
    )
    assert record["excluded_self_paths"] == [
        "docs/design/track_b_b0_1_audit.md"
    ]
    assert [f["path"] for f in record["files"]] == ["docs/design/other.md"]
    assert record["q6_exclusions"] == [
        {"path": "docs/design/other.md", "scope": "whole_file", "lines": None}
    ]
    assert record["content_recorded"] is False


# --------------------------------------------------------------------------
# Basis-explicit power
# --------------------------------------------------------------------------
def test_gap_conventions():
    assert rp.GAP_SE_OVER_SIGMA["m6_convention"] == 1.0
    assert rp.GAP_SE_OVER_SIGMA["side_a"] == pytest.approx(math.sqrt(1.05 / 2))
    assert rp.GAP_SE_OVER_SIGMA["full_support"] == pytest.approx(
        math.sqrt(1.05) / 2
    )


@pytest.mark.parametrize("m", [1, 6, 16])
def test_m6_convention_reproduces_the_frozen_record(m):
    frozen_value = frozen.bound_rule_pass_probability(rp.FLOOR_RATIO, m)
    assert rp.bound_rule_pass("m6_convention", m) == frozen_value
    frozen_k = (
        frozen.bound_rule_ratio(m) - math.sqrt(2 / math.pi)
    ) / math.sqrt(1 - 2 / math.pi)
    assert rp.k_needed("m6_convention", m) == pytest.approx(frozen_k)


@settings(max_examples=100, deadline=None)
@given(m=st.integers(min_value=1, max_value=40))
def test_bound_rule_orders_bases_and_family_sizes(m):
    m6 = rp.bound_rule_pass("m6_convention", m)
    side_a = rp.bound_rule_pass("side_a", m)
    full = rp.bound_rule_pass("full_support", m)
    assert 0.0 <= m6 <= side_a <= full <= 1.0
    for basis in rp.BASES:
        assert rp.bound_rule_pass(basis, m + 1) <= rp.bound_rule_pass(basis, m)
        assert rp.k_needed(basis, m + 1) >= rp.k_needed(basis, m)
        # Headroom is zero exactly where 0.90 power is reached.
        headroom = rp.estimation_headroom(basis, m)
        at_power = rp.bound_rule_pass(basis, m) >= frozen.POWER_TARGET
        assert (headroom >= -1e-12) == at_power or abs(headroom) < 1e-9


@pytest.mark.parametrize("m", [1, 6, 16])
def test_full_support_headroom_references_agree(m):
    over_gap = rp.estimation_headroom("full_support", m)
    over_se_full = rp.estimation_headroom_over_se_full_sq(m)
    assert over_se_full == pytest.approx(over_gap * (1 + 1 / rp.K))


@settings(max_examples=150, deadline=None)
@given(
    n=st.floats(min_value=50, max_value=50_000),
    m=st.sampled_from([1, 6, 16]),
    factor=st.floats(min_value=0.5, max_value=4.0),
    share=st.floats(min_value=0.05, max_value=1.0),
)
def test_persistence_min_rho_round_trips_and_is_monotone(n, m, factor, share):
    rho = rp.persistence_min_rho(n, m, factor, share)
    assert 0.0 <= rho < 1.0
    if rho > 0:
        needed = rp.persistence_required(m, rho, factor)
        assert needed == pytest.approx(share * n, rel=1e-9)
    else:
        assert share * n >= rp.persistence_required(m, 0.0, factor)
    assert rp.persistence_min_rho(n * 1.5, m, factor, share) <= rho
    assert rp.persistence_min_rho(n, m, factor * 1.5, share) >= rho
    assert rp.persistence_min_rho(n, 16, factor, share) >= (
        rp.persistence_min_rho(n, 1, factor, share)
    )


def test_persistence_rho0_normal_matches_the_frozen_bound():
    for m in (1, 6, 16):
        assert rp.persistence_required(m, 0.0) == pytest.approx(
            frozen.required_n_eff_correlation(0.05, m)
        )
        # The frozen figure is the largest requirement over rho >= 0 under
        # normal theory, not a necessary condition.
        assert rp.persistence_required(m, 0.3) < rp.persistence_required(
            m, 0.0
        )


@settings(max_examples=150, deadline=None)
@given(
    n=st.floats(min_value=50, max_value=50_000),
    m=st.sampled_from([1, 6, 16]),
)
def test_participation_threshold_round_trips(n, m):
    p = rp.participation_min_p(n, m)
    assert 0.5 <= p < 1.0
    if p > 0.5:
        assert rp.participation_required(m, p) == pytest.approx(n, rel=1e-9)
        assert rp.participation_required(m, 1 - p) == pytest.approx(
            n, rel=1e-9
        )
    else:
        assert n >= rp.participation_required(m, 0.5)
    assert rp.participation_min_p(n * 1.5, m) <= p


def test_m6_planning_illustration_arithmetic():
    plan = rp.m6_lag2_planning()
    sigma = rp.M6_LAG2_FLOOR_SIGMA
    assert plan["se_per_half"] == round(sigma / math.sqrt(2), 5)
    assert plan["se_full_support"] == round(sigma / 2, 5)
    assert plan["pairs_below_which_se_half_is_within_1_over_sqrt_n"] == round(
        2 / sigma**2, 1
    )
    for entry in plan["by_family_size"].values():
        assert entry["support_multiple_of_m6_needed_side_a"] == pytest.approx(
            2 * entry["support_multiple_of_m6_needed_full_support"], abs=0.02
        )
