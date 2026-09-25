"""Structural counts of the Track M population (counts only).

Reads the staged PSID with
:mod:`populace_dynamics.min_benefit_track_m.structure` and the M3 readers
and M4 cohort (:mod:`populace_dynamics.min_benefit_track_m.cohort`), and
writes ``track-m-structure.json``: the 2023-wave universe funnel (sequence
groups, weights, the birth-year law, OASDI receipt in 2022 and its
reconciliation with the family file), counts of the beneficiaries aged 62
and older by sex, role, birth-year band, benefit-type mention and accuracy
code, the availability of the earnings years that years of coverage would
count, and M4's counts (``cohort.structural_counts_before_registration``):
worker records by basis and by how section 4b resolved them, links,
unresolved and boundary records, and the threshold *years* (never
thresholds, and without counts) the in-window records of each registered
window need.  It counts no in-window record and no exposed person: the
M1 specification's section 11 reserves those diagnostics for the
registered run.

It computes **no** years of coverage, PIA, threshold, minimum, worker flag
or share receiving a minimum: plan ``critical-path-minimum-benefit-
20260924.md`` section 8 limits real-file work before the issue #42
registration to label verification, structural counts and aggregates that
involve no threshold and no minimum.  It refuses to write if the rules,
coverage, thresholds, careers or share-computation modules (evaluation,
tabulation, pipeline, invented, invented_psid) were imported.

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

from populace_dynamics.data import (  # noqa: E402
    social_security_receipt as ssr,
)
from populace_dynamics.min_benefit_track_m import (  # noqa: E402
    OUTPUT_LABELS,
    cohort,
    structure,
)
from populace_dynamics.min_benefit_track_m.policy import (  # noqa: E402
    decision_register,
)

FORBIDDEN_MODULES = (
    "populace_dynamics.min_benefit_track_m.rules",
    "populace_dynamics.min_benefit_track_m.coverage",
    "populace_dynamics.min_benefit_track_m.thresholds",
    "populace_dynamics.min_benefit_track_m.evaluation",
    "populace_dynamics.min_benefit_track_m.tabulation",
    "populace_dynamics.min_benefit_track_m.pipeline",
    "populace_dynamics.min_benefit_track_m.invented",
    "populace_dynamics.min_benefit_track_m.invented_psid",
    "populace_dynamics.min_benefit_track_m.careers",
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
    cohort_inputs = cohort.load_cohort_inputs(data_dir=data_dir)
    inputs = cohort_inputs.structure_inputs
    counts = structure.structural_counts(inputs)
    built = cohort.build_cohort(cohort_inputs)
    m4 = cohort.structural_counts_before_registration(built)
    universe = counts["funnel"]["receives_oasdi_person_level"]
    if m4["persons"] != universe:
        raise AssertionError(
            f"the M4 cohort holds {m4['persons']} persons, the funnel "
            f"{universe}: the two universes differ"
        )
    sources = cohort.history_source_counts(
        built, cohort_inputs.earnings, cohort_inputs.prior_year_labor
    )
    codes = ssr.verify_individual_codes(data_dir=data_dir)
    leaked = [name for name in FORBIDDEN_MODULES if name in sys.modules]
    if leaked:
        raise RuntimeError(f"rules modules were imported: {leaked}")
    return {
        "description": (
            "Track M (DynaSim exercise 4) population and M4 cohort: "
            "structural counts only, unweighted persons, records and "
            "years. No years of coverage, PIA, threshold, minimum, worker "
            "flag or share receiving a minimum was computed, and no count "
            "of in-window records or exposed persons (registered-run "
            "diagnostics, M1 specification section 11): of the windows, "
            "only the threshold years their records need, as years."
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
        "m3_individual_codes_verified": {
            str(wave): checked for wave, checked in codes.items()
        },
        "provenance": dict(cohort_inputs.provenance),
        "counts": counts,
        "m4_cohort": m4,
        "m5_history_sources": sources,
        "decisions": [item.as_dict() for item in decision_register()],
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
