"""Structural counts of the U2 age-67 population (counts only; built).

Specification sections 4 and 14: the pre-registration structural,
join and reconciliation pass (section 20 step 4), which is separately
authorized and has **not** been run.  When authorized it builds the U0
and U1 observations from the staged PSID through the U2 loader and the
committed-registry role context and writes ``track-u2-structure.json``:
dispositions, observations, roles, pairings, design strata, the family
income and WEALTH1 identity counts per wave and the registry status.

It also writes ``track-u2-preregistration-evidence.json``: the frozen
input identities section 14 says execution rechecks -- the SHA-256 of
every PSID file the loader read and the sealed ``input_frames_sha256``
(:func:`populace_dynamics.uniform_cut_track_u2.loader.
preregistration_evidence`).  Once reviewed, that record is committed at
``docs/design/u2_preregistration_evidence.json``
(:data:`~populace_dynamics.uniform_cut_track_u2.loader.
PREREGISTRATION_EVIDENCE_PATH`); the registered run binds its hash and
refuses while it is absent, and its loader refuses any changed file byte
or frame digest.

It computes **no** income concept, annuity, threshold, poverty status or
poverty rate and never imports the income concept or the tabulation
(:data:`FORBIDDEN_MODULES`, checked before and after).  Until every
required route is resolved, the loader refuses before opening any PSID
file, so running it at the adjudicated registries writes nothing.

Usage::

    python scripts/track_u2_structure.py --output-dir DIR
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
    loader,
    sources,
)

EVIDENCE_NAME = "track-u2-preregistration-evidence.json"
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
    registries = sources.RegistrySet.committed()
    roles = sources.RoleContext.from_registry(registries)
    births = cohort.derive_u2_births(inputs)
    rows = {}
    for row in cohort.ROWS:
        built = cohort.build_u2_cohort(
            inputs,
            cohort.U2CohortSpec(row=row),
            role_context=roles,
            births=births,
        )
        rows[row] = cohort.structural_summary(built)
    gate = sources.SourceGate(sources.REGISTRY, registries)
    identities = {}
    for wave in sources.SUPPORT_WAVES:
        income = inputs.family_income[wave]
        wealth = inputs.family_wealth[wave]
        identities[str(wave)] = {
            "n_families": int(len(income)),
            "income": sources.income_identity_counts(
                income, sources.income_identity(wave, gate)
            ),
            "wealth1": sources.wealth1_identity_counts(
                wealth, sources.wealth1_identity(wave, gate)
            ),
        }
    leaked = _leaked()
    if leaked:
        raise RuntimeError(f"income-concept modules were imported: {leaked}")
    return {
        "description": (
            "U2 age-67 population: structural counts only. No income "
            "concept, annuity, threshold, poverty status or poverty rate "
            "was computed."
        ),
        "labels": ["PSID-realized outcomes (not a projection)", "counts only"],
        "code_commit": _git("rev-parse", "HEAD"),
        "provenance": {
            k: v
            for k, v in inputs.provenance.items()
            if k != "psid_files_sha256"
        },
        "psid_files_sha256": dict(inputs.provenance["psid_files_sha256"]),
        "registry_status": sources.registry_status_summary(registries),
        "identities": identities,
        "rows": rows,
        "preregistration_evidence": loader.preregistration_evidence(inputs),
        "forbidden_modules_loaded": _leaked(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, default=None)
    args = parser.parse_args(argv)
    result = build(args.data_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    path = args.output_dir / "track-u2-structure.json"
    path.write_text(
        json.dumps(result, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    evidence = args.output_dir / EVIDENCE_NAME
    evidence.write_text(
        json.dumps(
            result["preregistration_evidence"], indent=2, sort_keys=True
        )
        + "\n",
        encoding="utf-8",
    )
    print(path)
    print(evidence)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
