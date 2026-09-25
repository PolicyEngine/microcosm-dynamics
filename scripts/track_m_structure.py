"""Structural counts of the Track M population (counts only).

Reads the staged PSID with
:mod:`populace_dynamics.min_benefit_track_m.structure` and writes
``track-m-structure.json``: the 2023-wave universe funnel (sequence
groups, weights, the birth-year law, OASDI receipt in 2022 and its
reconciliation with the family file), counts of the beneficiaries aged 62
and older by sex, role, birth-year band, benefit-type mention and accuracy
code, and the availability of the earnings years that years of coverage
would count.

It computes **no** years of coverage, PIA, threshold, minimum, worker flag
or share receiving a minimum: plan ``critical-path-minimum-benefit-
20260924.md`` section 8 limits real-file work before the issue #42
registration to label verification, structural counts and aggregates that
involve no threshold and no minimum.  It refuses to write if the rules or
coverage modules were imported.

Usage::

    python scripts/track_m_structure.py --output-dir DIR
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

from populace_dynamics.min_benefit_track_m import (  # noqa: E402
    OUTPUT_LABELS,
    structure,
)
from populace_dynamics.min_benefit_track_m.policy import (  # noqa: E402
    pending_decisions,
)

FORBIDDEN_MODULES = (
    "populace_dynamics.min_benefit_track_m.rules",
    "populace_dynamics.min_benefit_track_m.coverage",
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def build(data_dir: Path | None = None) -> dict:
    inputs = structure.load_structure_inputs(data_dir=data_dir)
    counts = structure.structural_counts(inputs)
    leaked = [name for name in FORBIDDEN_MODULES if name in sys.modules]
    if leaked:
        raise RuntimeError(f"rules modules were imported: {leaked}")
    return {
        "description": (
            "Track M (DynaSim exercise 4) population: structural counts "
            "only, unweighted persons. No years of coverage, PIA, "
            "threshold, minimum, worker flag or share receiving a minimum "
            "was computed."
        ),
        "labels": [*OUTPUT_LABELS, "counts only"],
        "code_commit": _git("rev-parse", "HEAD"),
        "code_tree_clean": _git("status", "--porcelain") == "",
        "universe": (
            "2023 wave, sequence 1-20, ER35265 > 0, born 1960 or earlier "
            "by estimates.career.derive_birth_years (seed: 2023 age), "
            "ER35219 > 0 (plan section 4; the family-file reconciliation "
            "is counted, not applied)"
        ),
        "codes_verified": dict(inputs.codes),
        "provenance": dict(inputs.provenance),
        "counts": counts,
        "pending_decisions": [item.as_dict() for item in pending_decisions()],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, default=None)
    args = parser.parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    result = build(args.data_dir)
    path = args.output_dir / "track-m-structure.json"
    path.write_text(
        json.dumps(result, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
