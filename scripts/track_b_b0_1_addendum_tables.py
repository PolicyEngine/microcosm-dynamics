#!/usr/bin/env python3
"""Track B B0.1 addendum: render the planning-value and power tables.

The addendum's sections 10 and 11 quote these tables. They are rendered
from the two committed records, and
``tests/test_track_b_b0_1_addendum_record.py`` requires the addendum to
hold them verbatim, so no figure is transcribed by hand.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PLANNING = ROOT / "docs" / "design" / "track_b_b0_1_planning_values.json"
POWER = ROOT / "docs" / "design" / "track_b_b0_1_addendum_power.json"

REASONS = {
    "pseudo_origin_floor_ineligible": "floor ineligible at the pseudo-origin",
    "arm_void": "an arm is void",
    "too_few_defined_replicates": "too few defined replicates",
}


def _f(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}"


def planning_table(planning: Mapping[str, Any]) -> str:
    """One row per cell: the two planning values and what B2 registers."""
    lines = [
        "| Cell | r (5th-95th) | e (5th-95th) | e upper | f | e_B2 | s² | "
        "s²_gate | d (95th) |",
        "|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for name, cell in sorted(planning["cells"].items()):
        if not cell.get("defined"):
            reason = REASONS[cell["undefined_reason"]]
            lines.append(f"| `{name}` | no planning values: {reason} |")
            continue
        ratio = cell["shared_anchor_ratio"]
        est = cell["estimation_variance"]
        gap = cell["gap_variance"]
        design = cell.get("design_ratio")
        design_text = (
            "not computed"
            if design is None
            else f"{_f(design['d'])} ({_f(design['ci'][1])})"
        )
        lines.append(
            f"| `{name}` | {_f(ratio['r'])} "
            f"({_f(ratio['ci'][0])}-{_f(ratio['ci'][1])}) | "
            f"{_f(est['e'])} ({_f(est['ci'][0])}-{_f(est['ci'][1])}) | "
            f"{_f(est['e_ucl'])} | {_f(est['transport_factor'])} | "
            f"{_f(est['e_b2'])} | {_f(gap['s2'])} | {_f(gap['s2_gate'])} | "
            f"{design_text} |"
        )
    return "\n".join(lines)


def diagnostics_table(planning: Mapping[str, Any]) -> str:
    lines = [
        "| Cell | Cross term (5th-95th) | Simulation share of Var(δ) | "
        "Floor σ / (2 × truth SD) | Monte Carlo error / se_up |",
        "|---|---|---:|---:|---:|",
    ]
    for name, cell in sorted(planning["cells"].items()):
        if not cell.get("defined"):
            continue
        diag = cell["diagnostics"]
        ci = diag["cross_term_ci"]
        mc = diag.get("mc_error_over_se_up")
        lines.append(
            f"| `{name}` | {_f(diag['cross_term'])} "
            f"({_f(ci[0])}-{_f(ci[1])}) | "
            f"{_f(diag['simulation_share_of_refit_variance'], 2)} | "
            f"{_f(diag['floor_sigma_over_twice_truth_sd'], 2)} | "
            f"{'not defined' if mc is None else _f(mc)} |"
        )
    return "\n".join(lines)


def surface_table(power: Mapping[str, Any]) -> str:
    """Gate-level power of named surfaces on each evaluation."""
    labels = {
        "binding": "Binding",
        "central": "Point variance (sensitivity)",
        "audit_upper_bound": "r = 1, e = 0 (sensitivity)",
    }
    lines = [
        "| Evaluation | All cells with planning values | M6-retained six | "
        "Best four cells | Best surface with every family |",
        "|---|---:|---:|---:|---:|",
    ]
    for basis, label in labels.items():
        record = power["bases"][basis]
        verdict = record["verdict"]
        all_cells = record["all_cells"]
        six = record["m6_retained_6"]
        four = verdict["best_four_cell_surface"]
        lines.append(
            f"| {label} | "
            f"{'none' if all_cells is None else _f(all_cells['p_gate'])} | "
            f"{'not all defined' if six is None else _f(six['p_gate'])} | "
            f"{'none' if four is None else _f(four['p_gate'])} | "
            f"{_f(verdict['best_family_surface_p_gate'])} |"
        )
    return "\n".join(lines)


def envelope_table(power: Mapping[str, Any]) -> str:
    """Best and worst family-complete surface of each size, binding."""
    envelope = power["bases"]["binding"]["verdict"]["envelope"]
    lines = [
        "| Gated cells | Surfaces | Best p_gate | Worst p_gate |",
        "|---:|---:|---:|---:|",
    ]
    for size, slot in sorted(envelope.items(), key=lambda item: int(item[0])):
        lines.append(
            f"| {size} | {slot['n_surfaces']:,} | "
            f"{_f(slot['best']['p_gate'])} | {_f(slot['worst']['p_gate'])} |"
        )
    return "\n".join(lines)


def verdict_sentence(power: Mapping[str, Any]) -> str:
    verdict = power["bases"]["binding"]["verdict"]
    if verdict["d693_flip_fires"]:
        return (
            "**Verdict: `WEAK_POWER_OR_VACUITY`.** On the binding "
            "evaluation no four-cell surface reaches 0.90, so d693's Q2 "
            "flip fires."
        )
    if verdict["family_floor_blocks"]:
        return (
            "**Verdict: stopped by the family floor.** On the binding "
            "evaluation a four-cell surface reaches 0.90 but no surface "
            "holding every concept family does."
        )
    return (
        "**Verdict: feasible.** On the binding evaluation a surface "
        "holding every concept family reaches 0.90."
    )


def _families(names: list[str]) -> str:
    return ", ".join(name.replace("_", " ") for name in names)


def illustration_table(power: Mapping[str, Any]) -> str:
    """Section 13: surfaces at 0.90 if a family's last cell may be pruned."""
    variants = {
        "as_measured": "Household resampling, as measured",
        "design_inflated": "Over-limit cells' sampling variance × d² "
        "(95th percentile)",
    }
    pruned = power["decision_illustrations"]["families_may_be_pruned"]
    lines = [
        "| Basis | Largest surface at 0.90 | Its families | "
        "Most families at 0.90 |",
        "|---|---|---|---|",
    ]
    for key, label in variants.items():
        scan = pruned[key]
        largest = scan["largest_surface"]
        most = scan["by_family_count"][max(scan["by_family_count"], key=int)]
        lines.append(
            f"| {label} | {len(largest['cells'])} cells, "
            f"{_f(largest['p_gate'])} | {_families(largest['families'])} | "
            f"{len(most['families'])} ({_families(most['families'])}), "
            f"{_f(most['p_gate'])} |"
        )
    return "\n".join(lines)


def render() -> dict[str, str]:
    planning = json.loads(PLANNING.read_text(encoding="utf-8"))
    power = json.loads(POWER.read_text(encoding="utf-8"))
    return {
        "planning": planning_table(planning),
        "diagnostics": diagnostics_table(planning),
        "surfaces": surface_table(power),
        "envelope": envelope_table(power),
        "verdict": verdict_sentence(power),
        "illustrations": illustration_table(power),
    }


if __name__ == "__main__":
    for title, text in render().items():
        print(f"<!-- {title} -->\n{text}\n")
