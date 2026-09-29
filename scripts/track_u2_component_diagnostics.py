"""F17 component diagnostics of the U2 population (no statistic; built).

Specification section 9 ("Permitted before registration") and section 20
step 4, which is separately authorized and has **not** been run.  When
authorized it builds row U0's observations from the staged PSID (U2
loader, committed-registry role context) and writes
``track-u2-component-diagnostics.json``: Social Security, SSI and WEALTH1
component summaries by income year against the committed SSA Table 5.A4
snapshot and the U2 federal benefit rates, and family-size counts.

It computes **no** income concept, annuity, threshold assignment,
poverty status or poverty rate, and never imports the income concept,
the tabulation, the runner, the parameter bundle or the invented
generator (:data:`FORBIDDEN_MODULES`, checked before and after).  Until
every required route is resolved, the loader refuses before opening any
PSID file.

Usage::

    python scripts/track_u2_component_diagnostics.py --output-dir DIR
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from populace_dynamics.uniform_cut_track_u2 import (  # noqa: E402
    cohort,
    diagnostics,
    loader,
    sources,
)

FORBIDDEN_MODULES = (
    "populace_dynamics.estimates.adjusted_poverty",
    "populace_dynamics.estimates.uniform_cut_tabulation",
    "populace_dynamics.uniform_cut_track_u2.estimator",
    "populace_dynamics.uniform_cut_track_u2.tabulation",
    "populace_dynamics.uniform_cut_track_u2.runner",
    "populace_dynamics.uniform_cut_track_u2.parameters",
    "populace_dynamics.uniform_cut_track_u2.invented",
)


def _leaked() -> list[str]:
    return [name for name in FORBIDDEN_MODULES if name in sys.modules]


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def build(data_dir: Path | None = None) -> dict[str, Any]:
    leaked = _leaked()
    if leaked:
        raise RuntimeError(f"forbidden modules already imported: {leaked}")
    inputs = loader.load_u2_inputs(data_dir=data_dir)
    built = cohort.build_u2_cohort(
        inputs,
        cohort.U2CohortSpec(),
        role_context=sources.RoleContext.from_registry(),
    )
    result = diagnostics.component_diagnostics(built, inputs)
    leaked = _leaked()
    if leaked:
        raise RuntimeError(f"income-concept modules were imported: {leaked}")
    return {
        "description": (
            "U2 F17 component diagnostics for row U0: Social Security, SSI "
            "and WEALTH1 summaries. No income concept, annuity, threshold "
            "assignment, poverty status or poverty rate was computed."
        ),
        "labels": [
            "PSID-realized outcomes (not a projection)",
            "component aggregates only: no income concept, threshold or "
            "poverty rate",
        ],
        "code_commit": _git("rev-parse", "HEAD"),
        "code_clean": _git("status", "--porcelain") == "",
        "diagnostics": result,
        "forbidden_modules_loaded": _leaked(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, default=None)
    args = parser.parse_args(argv)
    result = build(args.data_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    path = args.output_dir / "track-u2-component-diagnostics.json"
    path.write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
