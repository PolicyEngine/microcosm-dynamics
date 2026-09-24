"""Structural counts of the Track U age-67 population (counts only).

Builds the exercise-2 age-67 observations (rows U0 and U1) from the
staged PSID with :mod:`populace_dynamics.cohorts.age67` and writes
``track-u-structure.json``: persons, observations, dispositions, family
units, design strata, the wealth blockers, threshold-free receipt counts
and the family-income and WEALTH1 reconciliation counts.

It computes **no** income concept, annuity, threshold, poverty status or
poverty rate: plan ``critical-path-uniform-cut-20260923.md`` section 8
limits real-file work before the issue #42 registration to label
verification, structural counts and component aggregates that involve no
threshold.  It never imports the income-concept or tabulation modules.

Usage::

    python scripts/track_u_structure.py --output-dir DIR
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import pandas as pd  # noqa: E402

from populace_dynamics.cohorts import age67  # noqa: E402
from populace_dynamics.data import family_income  # noqa: E402

FORBIDDEN_MODULES = (
    "populace_dynamics.estimates.adjusted_poverty",
    "populace_dynamics.estimates.uniform_cut_tabulation",
)


def _git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def build(data_dir: Path | None = None) -> dict:
    inputs = age67.load_age67_inputs(data_dir=data_dir)
    rows = {}
    for row in age67.ROWS:
        cohort = age67.build_age67_cohort(inputs, age67.Age67Spec(row=row))
        rows[row] = age67.structural_summary(cohort, inputs)
    incomes = pd.concat(
        [inputs.family_income[wave] for wave in age67.WAVES],
        ignore_index=True,
    )
    wealth = pd.concat(
        [inputs.family_wealth[wave] for wave in sorted(inputs.family_wealth)],
        ignore_index=True,
    )
    leaked = [name for name in FORBIDDEN_MODULES if name in sys.modules]
    if leaked:
        raise RuntimeError(f"income-concept modules were imported: {leaked}")
    return {
        "description": (
            "Track U (DynaSim exercise 2) age-67 population: structural "
            "counts only. No income concept, annuity, threshold, poverty "
            "status or poverty rate was computed."
        ),
        "labels": [
            "PSID-realized outcomes (not a projection)",
            "counts only",
        ],
        "code_commit": _git_head(),
        "provenance": {
            key: value
            for key, value in inputs.provenance.items()
            if key != "psid_files_sha256"
        },
        "psid_files_sha256": inputs.provenance["psid_files_sha256"],
        "family_counts_by_wave": {
            str(wave): int(len(inputs.family_income[wave]))
            for wave in age67.WAVES
        },
        "family_income_reconciliation": (
            family_income.reconcile_family_income(incomes)
        ),
        "wealth1_reconciliation": family_income.reconcile_wealth1(wealth),
        "wealth_refusals": {
            str(k): v for k, v in sorted(inputs.wealth_refusals.items())
        },
        "rows": rows,
        "pending_decisions": [
            item.as_dict() for item in age67.pending_decisions()
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, default=None)
    args = parser.parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    result = build(args.data_dir)
    path = args.output_dir / "track-u-structure.json"
    path.write_text(
        json.dumps(result, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
