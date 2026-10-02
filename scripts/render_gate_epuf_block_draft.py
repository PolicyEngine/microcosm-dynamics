"""Render the proposed ``gates.gate_epuf`` block from its floor artifact.

The block is the entry the lock flip will copy into ``gates.yaml``. It
is carried as ``docs/design/gate_epuf_block_draft.yaml`` with
``locked: false`` until then (the pattern gate_m6 used), because a byte
change to ``gates.yaml`` moves pins that only a ratified flip may move.
Every number in it comes from ``runs/epuf_gate_floors_v1.json``;
``tests/test_gate_epuf_block_draft.py`` requires the committed block to
equal this script's output.

Usage::

    uv run python scripts/render_gate_epuf_block_draft.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "runs" / "epuf_gate_floors_v1.json"
BLOCK = ROOT / "docs" / "design" / "gate_epuf_block_draft.yaml"
PROPOSAL = "docs/amendments/gate_epuf_registration_proposal.md"

HEADER = """\
# gate_epuf block draft (registration proposal; lock flip PENDING).
#
# The `gates.gate_epuf` block exactly as the lock flip will add it under the
# top-level `gates:` key of gates.yaml, after gate_m6, with `locked: true`.
# Until then it lives here with `locked: false` and edits no gates.yaml byte:
# any change to gates.yaml moves runs/legacy_manifest_v1.json's pin and three
# others, which only a ratified flip may move.
#
# Rendered by scripts/render_gate_epuf_block_draft.py from
# runs/epuf_gate_floors_v1.json; tests/test_gate_epuf_block_draft.py requires
# this file to equal a fresh render. Proposal and rationale:
# docs/amendments/gate_epuf_registration_proposal.md.
"""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _round(value, places=6):
    return None if value is None else round(float(value), places)


STATISTIC_TEXT = {
    "r6": "rank persistence of capped earnings from 1998 to 2004",
    "zint": "zero years inside the window among persons positive at both ends",
    "d_anyzero": "zero years before 2004 among persons positive in 2004",
    "q_atmax": "the share of positive person-years at the taxable maximum",
    "mpers": "persistence at the taxable maximum from 1998 to 2004",
    "q_sexratio": "men's over women's share at the taxable maximum",
}


def covers(gated: list[str]) -> str:
    """The scored surface in words: exactly the gated cells."""
    if not gated:
        return (
            "Nothing is gated: every cell is report-only "
            "(report_only_bridge_dominated)."
        )
    parts = []
    for cell_id in gated:
        stat, *rest = cell_id.split(".")
        where = " ".join(rest) if rest else "both sexes"
        parts.append(f"{STATISTIC_TEXT[stat]} ({where}; {cell_id})")
    return (
        "Tranche G: a candidate generator's earnings on gate 1's held-out "
        "persons at the even reference years 1998, 2000, 2002 and 2004, in "
        "EPUF's capped and disclosed units, scored on the mean of the 20 "
        "registered seeds against EPUF with an allowance for the PSID's own "
        "measured distance from EPUF. Gated cells, and nothing else: "
        + "; ".join(parts)
        + ". Every other cell is report-only."
    )


def render_block(artifact: dict, artifact_sha256: str) -> dict:
    partition = artifact["gate_partition"]
    cells = artifact["cells"]
    gated = partition["gated"]
    design = artifact["design"]
    oc = artifact["faithful_candidate_oc"]
    if not gated:
        status = "report_only_bridge_dominated"
    elif artifact["ceremony_pause"]:
        status = "paused_pending_referee_round"
    else:
        status = "draft_pending_referee_round"
    bites = artifact["bite_demonstrations"]
    gated_cells = {}
    for cell_id in gated:
        cell = cells[cell_id]
        gated_cells[cell_id] = {
            "metric": cell["metric"],
            "cap": _round(cell["cap"]),
            "epuf_value": _round(cell["epuf_value"]),
            "psid_value": _round(cell["psid_value"]),
            "bridge_psid_minus_epuf": _round(cell["bridge_psid_minus_epuf"]),
            "tolerance": cell["floor"]["tolerance"],
            "realized_sigma": _round(cell["floor"]["realized_sigma"]),
            "lower": cell["lower"],
            "upper": cell["upper"],
            "faithful_pass_probability": _round(
                cell["faithful_pass_probability"]
            ),
        }
    return {
        "gates": {
            "gate_epuf": {
                "id": "epuf_covered_earnings",
                "status": status,
                "locked": False,
                "kind": "external_anchor",
                "proposal": PROPOSAL,
                "floor_run": "runs/epuf_gate_floors_v1.json",
                "floor_run_sha256": artifact_sha256,
                "external_anchor": {
                    "source": (
                        "SSA 2006 Earnings Public-Use File (EPUF), "
                        "https://www.ssa.gov/policy/docs/microdata/epuf/"
                    ),
                    "provenance": "data/external/epuf_2006/provenance.md",
                    "members_sha256": artifact["inputs"]["epuf_sha256"],
                    "disclosure_constants_sha256": artifact["inputs"][
                        "disclosure_constants_sha256"
                    ],
                },
                "covers": covers(gated),
                "not_certified": [
                    "careers, years without earnings by age 62, and the "
                    "35-year AIME (tranche R, report-only)",
                    "any year before 1998, and 2006",
                    "ages outside the support's window range (about 25-57)",
                    "the forward earnings law certified by gate_m6",
                    "that the PSID agrees with EPUF (the bridge is published "
                    "per cell)",
                    "earnings levels by age, which the generator takes from "
                    "PSID marginals",
                ],
                "validation_only": (
                    "No candidate may use EPUF in fitting, tuning or "
                    "calibration; a candidate that does is scored and "
                    "labelled a calibration check."
                ),
                "candidate_protocol": {
                    "panel": (
                        "gate 1's candidate panel: for each gate seed s, "
                        "populace_dynamics.harness.panel."
                        "split_panel_by_person(filtered_panel, 'person_id', "
                        "fraction=0.2, seed=s) draws the holdout; the "
                        "candidate emits the holdout's persons on their "
                        "observed periods with generated earnings"
                    ),
                    "gate_seeds": design["gate_seeds"],
                    "support": design["support"],
                    "scoring": (
                        "populace_dynamics.harness.epuf_run.score_candidate"
                    ),
                    "reproduction": (
                        "a verdict attaches to a registered candidate only if "
                        "the run reproduces that candidate's committed gate-1 "
                        "artifact exactly"
                    ),
                },
                "scoring": {
                    "estimator": (
                        "mean over the 20 gate seeds of the per-seed value, "
                        "then log for shares, identity for rank correlations"
                    ),
                    "floor": design["floor"],
                    "k": design["k"],
                    "tolerance": design["tolerance"],
                    "interval": design["interval"],
                    "eligibility": design["eligibility"],
                    "caps": {
                        key: _round(value)
                        for key, value in design["caps"].items()
                    },
                    "min_events": design["min_events"],
                    "pass_rule": (
                        "the gate passes iff every gated cell's 20-seed "
                        "estimate lies inside its interval"
                    ),
                },
                "gated_cells": gated_cells,
                "report_only": dict(partition["report_only"]),
                "faithful_candidate_oc": {
                    "analytic_product": _round(oc["analytic_product"]),
                    "empirical_joint": _round(oc["empirical_joint"]),
                    "pause_below": oc["pause_below"],
                },
                "bite_requirements": {
                    family: {
                        "bite": row["bite"],
                        "required_fail_share": row["required_fail_share"],
                        "fail_share": row["fail_share"],
                        "met": row["met"],
                    }
                    for family, row in bites["requirements"].items()
                },
                "ceremony_pause": artifact["ceremony_pause"],
                "lock_ceremony": {
                    "exists": True,
                    "stage": "proposal",
                    "next": [
                        "adversarial referee round",
                        "fixes",
                        "verification round",
                        "ratify by merge of the flip PR",
                        "registration of the first run on issue #42",
                    ],
                },
                "history": [
                    {
                        "id": "2026-10-02-epuf-registration-proposal",
                        "proposed": "2026-10-02",
                        "content": (
                            "Registration proposed with the rules committed "
                            "before the floor build (commit "
                            f"{artifact['revision_pins']['head_sha'][:12]}); "
                            "floors in runs/epuf_gate_floors_v1.json."
                        ),
                    }
                ],
            }
        }
    }


def render() -> str:
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    block = render_block(artifact, _sha256(ARTIFACT))
    return HEADER + yaml.safe_dump(
        block, sort_keys=False, width=79, allow_unicode=True
    )


def main() -> None:
    BLOCK.write_text(render(), encoding="utf-8")
    print(f"wrote {BLOCK.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
