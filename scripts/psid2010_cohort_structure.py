"""Build a PSID Track A starting cohort and write its structural counts.

Usage::

    python scripts/psid2010_cohort_structure.py --output counts.json \
        [--anchor-wave 2011|2009]

``--anchor-wave`` 2011 (the default) builds the A1 R0 population, opening
in 2010; 2009 builds the A1 R6 population, opening in 2008.  The output
holds structural counts only (persons, weights, dispositions, sources,
statuses, SS receipt by opening-year age band, diagnostics), the spec
used, every pending decision, the input provenance (with the SHA-256 of
every PSID file read) and the cohort provenance the builder recorded.  It
computes no benefit, no reform and no comparison statistic.
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
    parser.add_argument(
        "--anchor-wave",
        type=int,
        default=psid2010.ANCHOR_WAVE,
        choices=psid2010.ANCHOR_WAVES,
    )
    args = parser.parse_args()

    inputs = psid2010.load_psid2010_inputs(
        data_dir=args.data_dir, anchor_wave=args.anchor_wave
    )
    spec = psid2010.Psid2010CohortSpec(anchor_wave=args.anchor_wave)
    cohort = psid2010.build_psid2010_cohort(inputs, spec)
    document = {
        "schema": "populace_dynamics.psid2010_cohort_structure.v1",
        "code_commit": _git_head(),
        "anchor_wave": args.anchor_wave,
        "spec": spec.as_dict(),
        "provenance": dict(inputs.provenance),
        "cohort_provenance": dict(cohort.provenance),
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
