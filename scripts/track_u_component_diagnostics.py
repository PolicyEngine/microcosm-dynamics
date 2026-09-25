"""F17 component diagnostics of the Track U age-67 population (no statistic).

Builds the exercise-2 age-67 observations of row U0 from the staged PSID
(:mod:`populace_dynamics.cohorts.age67`) and writes
``track-u-component-diagnostics.json`` and ``SUMMARY.md``: weighted
Social Security, SSI and WEALTH1 summaries per income year, the Social
Security summaries set against the committed SSA Annual Statistical
Supplement 2025 Table 5.A4 cells, the SSI amounts against the committed
federal benefit rates, and counts of ``# IN FU`` against the individual
records (the reading of the unregistered institution rule).  WEALTH1 has
no committed or saved published comparator, so it is reported without
one.

It computes **no** income concept, annuity, threshold, poverty status or
poverty rate, and no official-concept poverty rate (plan
``critical-path-uniform-cut-20260923.md`` section 8 limits real-file
work before the issue #42 registration to label verification,
structural counts and component aggregates that involve no threshold).
It never imports the income concept, the tabulation, the Track U runner
or the invented generator, and checks that none was loaded.

Usage::

    python scripts/track_u_component_diagnostics.py --output-dir DIR
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

from populace_dynamics.cohorts import age67  # noqa: E402
from populace_dynamics.uniform_cut_track_u import diagnostics  # noqa: E402

FORBIDDEN_MODULES = (
    "populace_dynamics.estimates.adjusted_poverty",
    "populace_dynamics.estimates.uniform_cut_tabulation",
    "populace_dynamics.uniform_cut_track_u.runner",
    "populace_dynamics.uniform_cut_track_u.invented",
)
LABELS = (
    "PSID-realized outcomes (not a projection)",
    "component aggregates only: no income concept, threshold or poverty "
    "rate",
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def _leaked() -> list[str]:
    return [name for name in FORBIDDEN_MODULES if name in sys.modules]


def build(data_dir: Path | None = None) -> dict[str, Any]:
    leaked = _leaked()
    if leaked:
        raise RuntimeError(f"forbidden modules already imported: {leaked}")
    inputs = age67.load_age67_inputs(data_dir=data_dir)
    cohort = age67.build_age67_cohort(inputs, age67.Age67Spec())
    result = diagnostics.component_diagnostics(cohort, inputs)
    leaked = _leaked()
    if leaked:
        raise RuntimeError(f"income-concept modules were imported: {leaked}")
    return {
        "description": (
            "Track U (DynaSim exercise 2) F17 component diagnostics for the "
            "row U0 age-67 population: Social Security, SSI and WEALTH1 "
            "summaries against committed published aggregates. No income "
            "concept, annuity, threshold, poverty status or poverty rate "
            "was computed."
        ),
        "labels": list(LABELS),
        "code_commit": _git("rev-parse", "HEAD"),
        "code_clean": _git("status", "--porcelain") == "",
        "provenance": {
            key: value
            for key, value in cohort.provenance.items()
            if key != "psid_files_sha256"
        },
        "psid_files_sha256": dict(cohort.provenance["psid_files_sha256"]),
        "wealth_refusals": {
            str(k): v for k, v in sorted(inputs.wealth_refusals.items())
        },
        "diagnostics": result,
        "forbidden_modules_loaded": _leaked(),
    }


def _sentence(text: str) -> str:
    return text[:1].upper() + text[1:] + "."


def _fmt(value: Any, digits: int) -> str:
    return "n/a" if value is None else f"{value:,.{digits}f}"


def summary_markdown(result: dict[str, Any]) -> str:
    diag = result["diagnostics"]
    lines = [
        "# Track U component diagnostics (plan field F17)",
        "",
        "Labels: " + "; ".join(f"*{label}*" for label in result["labels"]),
        "",
        f"Row U0 population: {diag['population']['n_observations']} "
        f"observations of {diag['population']['n_persons']} persons, income "
        f"years {diag['population']['income_years']}; weighted by the "
        "observation weights. Code "
        f"`{result['code_commit']}` (clean: {result['code_clean']}). No "
        "income concept, annuity, threshold, poverty status or poverty "
        "rate was computed.",
        "",
        "## Social Security (head and wife members' own amounts)",
        "",
        "PSID: weighted share of head and wife members reporting their own "
        "Social Security and the weighted mean annual amount among them, "
        "divided by 12. SSA: Annual Statistical Supplement 2025 Table 5.A4, "
        "December average monthly benefit of retired workers (total monthly "
        "benefits over number; the division is ours), all ages.",
        "",
        "| Income year | Obs. | Own receipt share | Family receipt share | "
        "PSID mean monthly | SSA Dec (prior) | SSA Dec (income year) | "
        "PSID ÷ SSA prior Dec | PSID ÷ SSA Dec |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for year, ss in diag["social_security"].items():
        prior = ss["published"]["december_prior_year"]
        same = ss["published"]["december_income_year"]
        lines.append(
            f"| {year} | {ss['n_observations']} "
            f"| {_fmt(ss['own_receipt_share'], 3)} "
            f"| {_fmt(ss['family_receipt_share'], 3)} "
            f"| {_fmt(ss['own_mean_monthly_among_recipients'], 0)} "
            f"| {_fmt(prior['ssa_retired_worker_average_monthly'], 0)} "
            f"| {_fmt(same['ssa_retired_worker_average_monthly'], 0)} "
            f"| {_fmt(prior['psid_over_ssa_retired_worker'], 3)} "
            f"| {_fmt(same['psid_over_ssa_retired_worker'], 3)} |"
        )
    lines += [
        "",
        "Concept differences (not adjusted): "
        + "; ".join(
            diag["published_sources"]["social_security"]["concept_differences"]
        )
        + ".",
        "",
        "## SSI",
        "",
        "| Income year | Own receipt share | Family receipt share | Own "
        "recipients | Mean annual among recipients | Federal maximum "
        "(individual, annual) | Recipients above the federal maximum |",
        "|---|---|---|---|---|---|---|",
    ]
    for year, ssi in diag["ssi"].items():
        lines.append(
            f"| {year} | {_fmt(ssi['own_receipt_share'], 3)} "
            f"| {_fmt(ssi['family_receipt_share'], 3)} "
            f"| {ssi['n_own_recipients']} "
            f"| {_fmt(ssi['own_mean_annual_among_recipients'], 0)} "
            f"| {_fmt(ssi['federal_maximum_annual']['individual'], 0)} "
            f"| {ssi['n_recipients_above_federal_maximum']} |"
        )
    lines += [
        "",
        "No published SSI recipient or payment aggregate is committed or "
        "saved; the federal benefit rates are the committed capture "
        "(policyengine-us, citing SSA's SSI Federal Payment Amounts). An "
        "amount above the federal maximum is consistent with a state "
        "supplement or a reporting difference; which is not determined.",
        "",
        "## WEALTH1 (family imputed wealth excluding home equity)",
        "",
        "| Income year | Obs. | p10 | p25 | p50 | p75 | p90 | Share ≤ 0 | "
        "Share imputed |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for year, wealth in diag["wealth1"].items():
        q = wealth["quantiles"] or {}
        lines.append(
            f"| {year} | {wealth['n_observations']} "
            + " ".join(
                f"| {_fmt(q.get(key), 0)}"
                for key in ("p10", "p25", "p50", "p75", "p90")
            )
            + f" | {_fmt(wealth['share_at_or_below_zero'], 3)} "
            f"| {_fmt(wealth['share_imputed'], 3)} |"
        )
    lines += [
        "",
        _sentence(diag["published_sources"]["wealth1"]["not_compared"])
        + " Waves 2005 and 2007 have no WEALTH1 (supplements not staged).",
        "",
        "## `# IN FU` against the individual records (institution rule)",
        "",
        "| Wave | Families | # IN FU = in-family records | Institution "
        "records | Families with them | … # IN FU = in-family only | … "
        "# IN FU = in-family + institution |",
        "|---|---|---|---|---|---|---|",
    ]
    for wave, counts in diag["institution_record_counts"].items():
        lines.append(
            f"| {wave} | {counts['n_families']} "
            f"| {counts['n_fu_size_equals_in_family_records']} "
            f"| {counts['n_institution_records']} "
            f"| {counts['n_families_with_institution_records']} "
            f"| {counts['of_which_fu_size_equals_in_family_only']} "
            f"| {counts['of_which_fu_size_equals_in_family_plus_institution']}"
            " |"
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, default=None)
    args = parser.parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    result = build(args.data_dir)
    path = args.output_dir / "track-u-component-diagnostics.json"
    path.write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "SUMMARY.md").write_text(
        summary_markdown(result), encoding="utf-8"
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
