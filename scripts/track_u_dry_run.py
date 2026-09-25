"""Track U end-to-end DRY RUN on an INVENTED cohort (plan item U9).

INVENTED DATA - NOT A COMPARISON.  The cohort is the invented population
of :mod:`populace_dynamics.uniform_cut_track_u.invented` (persons,
families, income, Social Security, SSI, wealth, weights and design
variables all invented), run through the real age-67 builder, income
rows, income concept and tabulation for every registered row, with the
F17 diagnostics.  The poverty thresholds are INVENTED as well (round
numbers in the Census table shape), because the invented near-threshold
singles are placed against them; the committed Census capture (cos
decision d194) is loaded only to record its pin, not used.  The other parameters are
the committed ones: the NCHS 2000 and SSA 2004 life tables and the SSI
capture.  No PSID file is opened and no comparator value is read.

The invented generator gives waves 2005 and 2007 invented wealth, as if
the PSID wealth supplements were staged, so U0's five birth years run
end to end; the real supplements are not staged (cos decision d189).  The
checks record what the real staging does today (the income rows refuse
the blocked waves, and under the fallback rule U0-F becomes the headline
while the rows that need 2005 or 2007 are reported as blocked with their
counts), that the registered-run guards refuse invented inputs, and that
the committed Census threshold capture loads under its pin while a
threshold table without that pin is refused.

Usage::

    python scripts/track_u_dry_run.py --output-dir <dir> [--seed N]

Writes ``result.json`` and ``RESULTS.md`` into ``--output-dir``.
"""

from __future__ import annotations

import argparse
import datetime
import json
import math
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import pandas as pd  # noqa: E402

from populace_dynamics.cohorts import age67  # noqa: E402
from populace_dynamics.data import family_income  # noqa: E402
from populace_dynamics.estimates import adjusted_poverty as ap  # noqa: E402
from populace_dynamics.uniform_cut_track_u import (  # noqa: E402
    DRY_RUN_HEADER,
    invented,
    rows,
    runner,
)

#: A syntactically valid registration pointer used only to show that the
#: registered path refuses invented inputs (no such comment is implied).
_GUARD_POINTER = (
    "https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
    "#issuecomment-0"
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def _refusal(call: Any) -> dict[str, Any]:
    try:
        call()
    except Exception as error:  # recorded, not swallowed
        return {
            "refused": True,
            "error": type(error).__name__,
            "message": str(error),
        }
    return {"refused": False}


def checks(seed: int, params: runner.TrackUParameters) -> dict[str, Any]:
    """The dry run's checks, each recorded (none computes a PSID value)."""

    staged = invented.invented_age67_inputs(
        seed=seed, supplement_waves_staged=True
    )
    incomes = pd.concat(
        [staged.family_income[wave] for wave in age67.WAVES],
        ignore_index=True,
    )
    wealth = pd.concat(
        [staged.family_wealth[wave] for wave in family_income.WEALTH_WAVES],
        ignore_index=True,
    )
    blocked = invented.invented_age67_inputs(seed=seed)
    cohort = age67.build_age67_cohort(blocked)
    left = age67.income_rows(cohort, blocked, allow_blocked=True)
    fallback = runner.run_track_u(blocked, params, data_provenance=ap.INVENTED)
    return {
        "specification_rows": rows.check_rows_against_block(
            rows.specification_block()
        ),
        "invented_family_income_reconciliation": (
            family_income.reconcile_family_income(incomes)
        ),
        "invented_wealth1_reconciliation": family_income.reconcile_wealth1(
            wealth
        ),
        "blocked_waves_as_staged_today": {
            "wealth_refusals": {
                str(k): v for k, v in sorted(blocked.wealth_refusals.items())
            },
            "income_rows_without_allow_blocked": _refusal(
                lambda: age67.income_rows(cohort, blocked)
            ),
            "left_out_with_allow_blocked": dict(left.attrs["left_out"]),
            "observations_kept_with_allow_blocked": int(len(left)),
            "fallback_rule": {
                "headline": fallback["headline"],
                "row_status": {
                    row_id: entry["status"]
                    for row_id, entry in fallback["rows"].items()
                },
                "blocked_counts": {
                    row_id: entry["population"]
                    for row_id, entry in fallback["rows"].items()
                    if entry["status"] == "blocked"
                },
                "headline_all_cell": next(
                    {
                        key: cell[key]
                        for key in (
                            "n_observations",
                            "baseline_rate",
                            "reform_rate",
                            "delta",
                        )
                    }
                    for cell in fallback["rows"][fallback["headline"]["row"]][
                        "tabulation"
                    ]["cells"]
                    if cell["cell"] == "all"
                ),
            },
        },
        "registered_guard_refuses_invented_inputs": _refusal(
            lambda: runner.run_track_u(
                staged,
                params,
                data_provenance=ap.REGISTERED_REAL,
                registration_pointer=_GUARD_POINTER,
            )
        ),
        "census_threshold_capture": _census_capture(params),
    }


def _census_capture(params: runner.TrackUParameters) -> dict[str, Any]:
    """The committed Census capture loads under its pin (not used here),
    and a registered run refuses this dry run's invented thresholds."""

    thresholds = ap.load_poverty_thresholds()
    return {
        "loads_under_pin": thresholds.provenance["sha256"]
        == ap.THRESHOLDS_SHA256,
        "sha256": thresholds.provenance["sha256"],
        "years": [
            min(thresholds.weighted_average),
            max(thresholds.weighted_average),
        ],
        "used_by_this_dry_run": False,
        "registered_check_refuses_invented_thresholds": _refusal(
            lambda: runner._check_parameters(params, ap.REGISTERED_REAL)
        ),
    }


def _fmt(value: Any, digits: int = 2) -> str:
    if value is None or (
        isinstance(value, float) and not math.isfinite(value)
    ):
        return "undefined"
    return f"{value:.{digits}f}"


def _cell(tabulation: dict[str, Any], name: str) -> dict[str, Any]:
    return next(c for c in tabulation["cells"] if c["cell"] == name)


def _cell_line(label: str, cell: dict[str, Any]) -> str:
    if not cell["defined"]:
        return (
            f"| {label} | {cell['n_observations']} | undefined "
            f"({cell['undefined_reason']}) | | | | |"
        )
    floor = cell["floor"]["delta"]
    se = cell.get("design_se", {}).get("delta", {}).get("se")
    return (
        f"| {label} | {cell['n_observations']} "
        f"| {_fmt(cell['baseline_rate'])} | {_fmt(cell['reform_rate'])} "
        f"| {_fmt(cell['delta'])} "
        f"| {_fmt(floor['mean']) if floor['defined'] else 'undefined'} "
        f"| {_fmt(se)} |"
    )


def results_markdown(result: dict[str, Any]) -> str:
    run = result["run"]
    provenance = result["cohort_provenance"]
    lines = [
        f"# {DRY_RUN_HEADER}",
        "",
        f"Track U (DynaSim exercise 2, plan item U9) end-to-end dry run, "
        f"{run['date']}. Every person, family, income amount, Social "
        "Security and SSI amount, wealth component, weight and sampling "
        "stratum and cluster is **invented** "
        "(`populace_dynamics.uniform_cut_track_u.invented`, seed "
        f"{provenance['seed']}). The poverty thresholds are **invented** "
        "too: round numbers in the Census table shape, labelled "
        f"\"{result['parameters']['thresholds']['label']}\". No PSID file "
        "was opened, no comparator value was read, and nothing below is a "
        "result or a comparison with DYNASIM.",
        "",
        "Labels on every output: "
        + "; ".join(f"*{label}*" for label in result["labels"])
        + ".",
        "",
        "## What ran",
        "",
        "- Invented cohort through the real builder "
        "(`cohorts.age67.build_age67_cohort`), income rows, income concept "
        "(`estimates.adjusted_poverty.adjusted_incomes`) and tabulation "
        "(`estimates.uniform_cut_tabulation.tabulate_uniform_cut`), once "
        "per registered row. Waves 2005 and 2007 carry invented wealth as "
        "if the PSID wealth supplements were staged; the real ones are "
        "not (see Checks).",
        "- Parameters: the committed NCHS 2000 and SSA 2004 life tables "
        "and the committed SSI capture; **invented** thresholds (the "
        "invented near-threshold singles are placed against them; the "
        "committed Census capture is loaded only to record its pin).",
        "- Rows: "
        + ", ".join(
            f"{row_id} ({entry['status'].replace('_', ' ')})"
            for row_id, entry in result["rows"].items()
        )
        + ".",
        "",
        "## Invented-data tabulation (not a comparison)",
        "",
        "Cell `all` of each row: observations, baseline rate P_B, reform "
        "rate P_R and Δ = P_R − P_B in percentage points, the mean "
        "half-split floor of Δ over five seeds (split units: family units "
        "linked by persons) and the design-based standard error of Δ. "
        "These numbers describe the invented cohort only.",
        "",
        "| Row | Observations | P_B | P_R | Δ | Δ floor | Δ design SE |",
        "|---|---|---|---|---|---|---|",
    ]
    for row_id, entry in result["rows"].items():
        if entry["status"] != "computed":
            status = entry["status"].replace("_", " ")
            lines.append(
                f"| {row_id} | {status}: {entry['reason']} | | | | | |"
            )
            continue
        lines.append(_cell_line(row_id, _cell(entry["tabulation"], "all")))
    headline = result["headline"]["row"]
    primary = result["rows"][headline]["tabulation"]
    design = primary["design"]
    lines += [
        "",
        f"Headline row {headline} (fallback rule "
        f"`{result['headline']['rule']}`). Design-based standard errors "
        f"use the {design['domain'].replace('_', ' ')}: "
        f"{design.get('n_strata')} invented strata, "
        f"{design.get('n_clusters')} clusters, singleton strata "
        f"{design.get('singleton_strata')}.",
        "",
        f"### Row {headline} by cell (invented)",
        "",
        "| Cell | Observations | P_B | P_R | Δ | Δ floor | Δ design SE |",
        "|---|---|---|---|---|---|---|",
    ]
    for cell in primary["cells"]:
        lines.append(_cell_line(cell["cell"], cell))
    undefined = [
        f"- {row_id}, {item['cell']}: {item['reason']}."
        for row_id, entry in result["rows"].items()
        if entry["status"] == "computed"
        for item in entry["tabulation"]["undefined_cells"]
    ]
    lines += ["", "Undefined cells, each with its reason:", ""]
    lines += undefined or ["- none in this run."]
    f17 = result["f17_diagnostics"]
    lines += [
        "",
        "## F17 diagnostics on invented data (not scored)",
        "",
        "Official-concept poverty rate (money income, reported asset "
        "income kept, no annuity, no cut, against the same invented "
        f"thresholds), row {f17['row']}: "
        + "; ".join(
            f"{name} {_fmt(cell.get('rate'))}"
            for name, cell in f17["official_concept_poverty_rate"][
                "cells"
            ].items()
        )
        + ".",
        "",
        "| Income year | Own SS receipt share | Own SS mean monthly | "
        "÷ SSA Dec retired-worker average (prior Dec) | Own SSI receipt "
        "share | SSI above federal maximum | WEALTH1 p50 |",
        "|---|---|---|---|---|---|---|",
    ]
    components = f17["components"]
    for year, ss in components["social_security"].items():
        ssi = components["ssi"][year]
        wealth = components["wealth1"].get(year)
        ratio = ss["published"]["december_prior_year"][
            "psid_over_ssa_retired_worker"
        ]
        lines.append(
            f"| {year} | {_fmt(ss['own_receipt_share'], 3)} "
            f"| {_fmt(ss['own_mean_monthly_among_recipients'], 0)} "
            f"| {_fmt(ratio, 3)} | {_fmt(ssi['own_receipt_share'], 3)} "
            f"| {ssi['n_recipients_above_federal_maximum']} "
            f"| {_fmt(wealth['quantiles']['p50'], 0) if wealth else 'n/a'} |"
        )
    lines += [
        "",
        "The SSA averages are the committed Annual Statistical Supplement "
        "2025 Table 5.A4 cells (a real published source); set against "
        "invented amounts, their ratio says nothing about PSID.",
        "",
        "## Checks",
        "",
    ]
    check = result["checks"]
    blocked = check["blocked_waves_as_staged_today"]
    reconciliation = check["invented_family_income_reconciliation"]
    exact = all(
        counts["n_exact"] == counts["n_families"]
        for identities in reconciliation.values()
        for counts in identities.values()
    )
    wealth_exact = all(
        counts["n_exact"] == counts["n_families"]
        for identities in check["invented_wealth1_reconciliation"].values()
        for counts in identities.values()
    )
    lines += [
        "- Every registered row equals the specification block "
        f"({check['specification_rows']['specification_version']}): "
        f"{check['specification_rows']['rows_equal_the_block']}.",
        "- Invented family income adds up exactly under the codebook "
        f"identities in every wave: {exact}; WEALTH1 and WEALTH2 "
        f"identities exact: {wealth_exact}.",
        "- The inputs and the U0 cohort re-generate from the invented "
        "generator's seed (`check_invented_inputs`, "
        "`check_invented_cohort`).",
        "- As the real staging is today (no 2005/2007 wealth), the income "
        "rows refuse without `allow_blocked`: "
        f"{blocked['income_rows_without_allow_blocked']['refused']}; with "
        "it, "
        f"{blocked['left_out_with_allow_blocked']['wealth_supplement_not_staged']}"
        " observations (waves 2005 and 2007) are left out and "
        f"{blocked['observations_kept_with_allow_blocked']} kept.",
        "- Under the fallback rule with that staging, the headline is "
        f"{blocked['fallback_rule']['headline']['row']}; rows reported "
        "blocked with their counts: "
        + ", ".join(
            row_id
            for row_id, status in blocked["fallback_rule"][
                "row_status"
            ].items()
            if status == "blocked"
        )
        + f"; {blocked['fallback_rule']['headline']['row']} cell `all` "
        f"(invented): {blocked['fallback_rule']['headline_all_cell']['n_observations']} "
        "observations, Δ "
        f"{_fmt(blocked['fallback_rule']['headline_all_cell']['delta'])}.",
        "- The registered path refuses these invented inputs: "
        f"{check['registered_guard_refuses_invented_inputs']['refused']} "
        f"(`{check['registered_guard_refuses_invented_inputs'].get('error')}`).",
        "- The committed Census threshold capture loads under its pin "
        f"(`{check['census_threshold_capture']['sha256'][:12]}…`, income "
        f"years {check['census_threshold_capture']['years'][0]}–"
        f"{check['census_threshold_capture']['years'][1]}): "
        f"{check['census_threshold_capture']['loads_under_pin']}; the "
        "registered parameter check refuses this dry run's invented "
        "thresholds: "
        + str(
            check["census_threshold_capture"][
                "registered_check_refuses_invented_thresholds"
            ]["refused"]
        )
        + ".",
        "",
        "## Pending decisions",
        "",
        "Every choice below is a parameter at its default; none is ratified.",
        "",
    ]
    for item in (
        result["pending_decisions"]["age67"]
        + result["pending_decisions"]["income_concept"]
        + result["pending_decisions"]["tabulation"]
    ):
        lines.append(
            f"- `{item['field']}` = `{item['default']}` (awaiting "
            f"{item['awaiting']})."
        )
    for row_id, awaiting in result["pending_decisions"]["rows"].items():
        lines.append(f"- Row {row_id}: awaiting {awaiting}.")
    lines += ["", "## Named deltas", ""]
    lines += [f"- {delta}." for delta in result["named_deltas"]]
    thresholds = result["parameters"]["thresholds"]
    lines += [
        "",
        "## Provenance",
        "",
        f"- Code: `{run['git_head']}` (worktree clean: {run['git_clean']}).",
        f"- Invented inputs: generator `{provenance['generator']}`, seed "
        f"{provenance['seed']}, frames SHA-256 "
        f"`{provenance['input_frames_sha256']}`.",
        f"- Thresholds: `{thresholds['kind']}` ({thresholds['generator']}).",
        f"- SSI: sha256 `{result['parameters']['ssi']['sha256']}`.",
        "- Life tables: "
        + ", ".join(
            f"`{name}` sha256 `{entry.get('sha256')}`"
            for name, entry in result["parameters"]["life_tables"].items()
        )
        + ".",
        f"- Python {run['python']}; command `{run['command']}`.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=invented.DEFAULT_SEED)
    args = parser.parse_args(argv)

    params = runner.committed_parameters(
        invented.invented_poverty_thresholds()
    )
    inputs = invented.invented_age67_inputs(
        seed=args.seed, supplement_waves_staged=True
    )
    result = runner.run_track_u(
        inputs,
        params,
        data_provenance=ap.INVENTED,
        progress=lambda message: print(message, file=sys.stderr),
    )
    result = {
        "header": DRY_RUN_HEADER,
        **result,
        "checks": checks(args.seed, params),
        "run": {
            "date": datetime.date.today().isoformat(),
            "invented_seed": args.seed,
            "git_head": _git("rev-parse", "HEAD"),
            "git_clean": _git("status", "--porcelain") == "",
            "python": platform.python_version(),
            "command": " ".join(
                [
                    "python",
                    "scripts/track_u_dry_run.py",
                    *(sys.argv[1:] if argv is None else argv),
                ]
            ),
        },
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "result.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "RESULTS.md").write_text(
        results_markdown(result), encoding="utf-8"
    )
    print(args.output_dir / "result.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
