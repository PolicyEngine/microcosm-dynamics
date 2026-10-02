"""Render the registered ``gates.gate_epuf`` block from its floor artifact.

The block is the gate's registration record. It is carried as
``docs/design/gate_epuf_block_draft.yaml`` with ``locked: false`` and is
not in ``gates.yaml`` (the pattern gate_m6 used for its drafts), because a
byte change to ``gates.yaml`` moves pins that only a ratified flip may
move. Round 1 of the referee review ruled that the gate does not lock as
registered (``ROUND_1`` below), so the block records the mechanical
partition the registered rules produced beside the ruling, and gates
nothing. Every number comes from ``runs/epuf_gate_floors_v1.json``;
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
FIRST_BUILD = ROOT / "runs" / "epuf_gate_floors_v1_first_build.json"
SUPPLEMENT = ROOT / "runs" / "epuf_gate_supplement_v1.json"
BLOCK = ROOT / "docs" / "design" / "gate_epuf_block_draft.yaml"
PROPOSAL = "docs/amendments/gate_epuf_registration_proposal.md"
SCORING_PATH = "src/populace_dynamics/harness/epuf_run.py"

#: The commit holding the registered rules, pushed before any real-PSID
#: value in EPUF units existed (2026-10-02 13:37 UTC, PR #509).
RULES_COMMIT = "eec910d61a7e0afe21995957740e03d64acdffdc"

#: Round 1 of the adversarial referee review and the ruling taken on it.
ROUND_1 = {
    "report": "reviews/gate_epuf_round1_referee_20261002.md",
    "reviewer": (
        "independent Opus 5.5 lane (subfleet job "
        "20261002-095515-epuf-gate-r1b), reviewing head ce8d5000"
    ),
    "verdict": "AMEND: do not lock as registered",
    "ruling": (
        "Not locked. The registered persistence bite could not be met by "
        "design: the tolerance is about 3.2 realised sigmas (0.079) while "
        "giving 10 percent of persons a donor's early years shifts the "
        "1998-2004 rank correlation by about 0.07, so the pause was an "
        "internal inconsistency of the registration, not a data surprise. "
        "The two cells the rules selected add no demonstrated catch beyond "
        "gate 1, and with the bridge signs public the registered "
        "candidate's verdict is largely predictable. Relaxing the bite "
        "requirement after seeing the result (option (a)) is rejected; the "
        "cells publish report-only with every gate-1 run. A gate with bite "
        "needs a fresh registration (proposal section 12)."
    ),
}

HEADER = """\
# gate_epuf registration record (unlocked; not in gates.yaml).
#
# Round 1 of the referee review ruled that the gate does not lock as
# registered: as designed it cannot fail the generator for anything gate 1
# does not already catch. The block records the registered rules, the
# partition they produced, and the ruling. It gates nothing; every cell
# publishes report-only with each gate-1 run. It edits no gates.yaml byte.
#
# Rendered by scripts/render_gate_epuf_block_draft.py from
# runs/epuf_gate_floors_v1.json; tests/test_gate_epuf_block_draft.py requires
# this file to equal a fresh render. Proposal, results and ruling:
# docs/amendments/gate_epuf_registration_proposal.md.
"""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _round(value, places=6):
    return None if value is None else round(float(value), places)


def _interval(cell: dict) -> dict:
    return {
        "metric": cell["metric"],
        "cap": _round(cell["cap"]),
        "epuf_value": _round(cell["epuf_value"]),
        "psid_value": _round(cell["psid_value"]),
        "bridge_psid_minus_epuf": _round(cell["bridge_psid_minus_epuf"]),
        "tolerance": cell["floor"]["tolerance"],
        "realized_sigma": _round(cell["floor"]["realized_sigma"]),
        "lower": cell["lower"],
        "upper": cell["upper"],
        "faithful_pass_probability": _round(cell["faithful_pass_probability"]),
    }


def render_block(
    artifact: dict, artifact_sha256: str, hashes: dict[str, str]
) -> dict:
    partition = artifact["gate_partition"]
    cells = artifact["cells"]
    selected = partition["gated"]
    design = artifact["design"]
    oc = artifact["faithful_candidate_oc"]
    bites = artifact["bite_demonstrations"]
    report_only = {
        cell_id: "not_locked_referee_round_1" for cell_id in selected
    }
    report_only.update(partition["report_only"])
    return {
        "gates": {
            "gate_epuf": {
                "id": "epuf_covered_earnings",
                "status": "unlocked_report_only",
                "locked": False,
                "kind": "external_anchor",
                "proposal": PROPOSAL,
                "rules_commit": RULES_COMMIT,
                "floor_build_commit": artifact["revision_pins"]["head_sha"],
                "floor_run": "runs/epuf_gate_floors_v1.json",
                "floor_run_sha256": artifact_sha256,
                "first_floor_build": {
                    "path": "runs/epuf_gate_floors_v1_first_build.json",
                    "sha256": hashes["first_build"],
                    "note": (
                        "the build before the report-only career-AIME fix "
                        "(proposal section 10); its window cells, floors, "
                        "partition and bites equal the floor run's"
                    ),
                },
                "supplement": {
                    "path": "runs/epuf_gate_supplement_v1.json",
                    "sha256": hashes["supplement"],
                },
                "scoring_path": {
                    "module": SCORING_PATH,
                    "sha256": hashes["scoring_path"],
                },
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
                "covers": (
                    "Nothing is gated. Every cell is published report-only "
                    "with each gate-1 candidate run: the candidate's 20-seed "
                    "estimate, its distance from EPUF, and that distance "
                    "split into the candidate's distance from the PSID and "
                    "the PSID's distance from EPUF."
                ),
                "not_certified": [
                    "anything: the gate is unlocked and gates no cell",
                    "careers, years without earnings by age 62, and the "
                    "35-year AIME (tranche R, report-only)",
                    "any year before 1998, and 2006",
                    "that the PSID agrees with EPUF (the bridge is published "
                    "per cell)",
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
                },
                "registered_scoring": {
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
                },
                "gated_cells": {},
                "selected_by_registered_rules": {
                    cell_id: _interval(cells[cell_id]) for cell_id in selected
                },
                "report_only": report_only,
                "faithful_candidate_oc_of_selected_cells": {
                    "analytic_product": _round(oc["analytic_product"]),
                    "empirical_joint": _round(oc["empirical_joint"]),
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
                "referee_round_1": ROUND_1,
                "lock_ceremony": {
                    "exists": False,
                    "stage": "closed without lock (referee round 1)",
                    "required_for_any_future_lock": (
                        "a fresh registration with a new id, its rules "
                        "fixed before anything is recomputed (proposal "
                        "section 12)"
                    ),
                },
                "history": [
                    {
                        "id": "2026-10-02-epuf-registration-proposal",
                        "proposed": "2026-10-02",
                        "content": (
                            "Rules committed and pushed before the floor "
                            f"build (commit {RULES_COMMIT[:12]}); floors "
                            "built at commit "
                            f"{artifact['revision_pins']['head_sha'][:12]}."
                        ),
                    },
                    {
                        "id": "2026-10-02-epuf-referee-round-1",
                        "content": (
                            "Referee round 1: AMEND. Ruling: not locked; "
                            "report-only (referee_round_1)."
                        ),
                    },
                ],
            }
        }
    }


def render() -> str:
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    hashes = {
        "first_build": _sha256(FIRST_BUILD),
        "supplement": _sha256(SUPPLEMENT),
        "scoring_path": _sha256(ROOT / SCORING_PATH),
    }
    block = render_block(artifact, _sha256(ARTIFACT), hashes)
    return HEADER + yaml.safe_dump(
        block, sort_keys=False, width=79, allow_unicode=True
    )


def main() -> None:
    BLOCK.write_text(render(), encoding="utf-8")
    print(f"wrote {BLOCK.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
