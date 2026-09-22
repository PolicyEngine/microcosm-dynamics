"""Build the PSID 2010 starting cohort and write its structural counts.

Usage::

    python scripts/psid2010_cohort_structure.py --output counts.json

The output holds structural counts only (persons, weights, dispositions,
sources, statuses, SS receipt by 2010 age band, diagnostics), the spec used,
every pending decision and the input provenance. It computes no benefit,
no reform and no comparison statistic.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from populace_dynamics.cohorts import psid2010

ROOT = Path(__file__).resolve().parents[1]


def _git_head() -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, default=None)
    args = parser.parse_args()

    inputs = psid2010.load_psid2010_inputs(data_dir=args.data_dir)
    cohort = psid2010.build_psid2010_cohort(inputs)
    document = {
        "schema": "populace_dynamics.psid2010_cohort_structure.v1",
        "code_commit": _git_head(),
        "provenance": dict(inputs.provenance),
        "pending_decisions": [
            decision.as_dict() for decision in psid2010.pending_decisions()
        ],
        "summary": psid2010.structural_summary(cohort),
    }
    args.output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
