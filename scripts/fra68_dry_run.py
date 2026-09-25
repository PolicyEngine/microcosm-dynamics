"""Exercise 3 (FRA to 68) end-to-end DRY RUN on an INVENTED cohort.

INVENTED DATA - NOT A COMPARISON.  The cohort is the invented population
of :mod:`populace_dynamics.cola_track_a.invented` (Track A's dry-run
cohort), read both as the 2011 wave (rows F0-F7, opening 2010) and as the
2009 wave (row F8, opening 2008), each run through the real A3 builder,
Track A's projection on the unmodified loop, the exercise-3 scenario
benefits (:mod:`populace_dynamics.fra68_track`) and the A7 tabulation.  No
PSID file is opened and no comparator value is read.  The parameters are
the committed ones (TR2008 capture, 2008-vintage DI rates, the claim-age
table, the realized COLA history) plus the oracle's statutory parameters
from the local policyengine-us checkout, with the AWI replaced by
TR2008's; the run compares every one with its committed source
(``check_committed_parameters``).  The reform bundles P1-P3 are derived
from the baseline bundle and recorded with their SHA-256s.

The E1 specification records Max's rulings of 2026-09-24 (decision
records d188 and d196): the run records each ruled field with its
configured value and whether it follows the ruling, and checks the
specification block against the code.

Usage::

    python scripts/fra68_dry_run.py --output-dir <dir> [--draws 3]

Writes ``result.json`` and ``RESULTS.md`` into ``--output-dir``.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.util
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

from populace_dynamics.cohorts import psid2010  # noqa: E402
from populace_dynamics.cola_track_a import (  # noqa: E402
    TrackAInputs,
    invented,
    prepare_track_a_cohort,
)
from populace_dynamics.cola_track_a.mortality import (  # noqa: E402
    load_tr2008_mortality,
)
from populace_dynamics.cola_track_a.runner import (  # noqa: E402
    A1_SPECIFICATION_PATH,
    load_claiming_pmf,
    tr2008_baseline_cola,
    tr2008_ssa_parameters,
)
from populace_dynamics.cola_track_a.statutory import (  # noqa: E402
    CAPTURE_PATH,
    CAPTURE_SHA256,
)
from populace_dynamics.data import tr2008  # noqa: E402
from populace_dynamics.engine.di_entitlement_rates import (  # noqa: E402
    load_di_entitlement_rates,
)
from populace_dynamics.estimates.parameters import (  # noqa: E402
    load_cola_history,
)
from populace_dynamics.fra68_track import (  # noqa: E402
    DRY_RUN_HEADER,
    FRA68Config,
    run_fra68,
)
from populace_dynamics.fra68_track.benefits import (  # noqa: E402
    CONVERSION_CLAIM_EXCESS,
    CONVERSION_CLAIM_MONTHS_EARLY,
    CREDITS_NOT_INHERITED,
    CREDITS_NOT_INHERITED_CLAIM_MOVED_PAST_DEATH,
)
from populace_dynamics.fra68_track.runner import (  # noqa: E402
    E1_SPECIFICATION_PATH,
)
from populace_dynamics.ss.params import load_ssa_parameters  # noqa: E402

#: Exercise-3 gaps on top of Track A's (E1 section 12).
FRA68_GAPS: tuple[dict[str, str], ...] = (
    {
        "item": "Retirement earnings test to 68",
        "gap": (
            "42 USC 403(f)(1)(B) and (f)(8)(E) stop the earnings test at "
            "the retirement age, so the reform extends it to 68; Track A "
            "draws no earnings after the opening year and pays gross "
            "amounts, so no scenario withholds anything"
        ),
    },
    {
        "item": "Adjusted reduction period",
        "gap": (
            "402(q)(7)(A) excludes months with earnings-test deductions "
            "from the adjusted reduction period; not modeled"
        ),
    },
    {
        "item": "DI eligibility window extended to 68",
        "gap": (
            "423(a)(1)(B): the reform lets people aged 67 be awarded DI; "
            "the shared projection draws no such award. Reported as the "
            "di_window_diagnostic (people exposed and expected awards at "
            "A4's rates), not modeled"
        ),
    },
    {
        "item": "DI recovery in the extended window",
        "gap": (
            "A4 draws no recovery after the baseline conversion; in the "
            "reform scenario the worker would still be exposed until the "
            "later conversion. Membership only"
        ),
    },
    {
        "item": "Spouse's excess of a converted DI worker",
        "gap": (
            "Track A pays none while a worker is DI-entitled, so under the "
            "reform a converted worker's excess starts a year later (a "
            "convention, not the statute: 402(q)(3)(C) would pay a DI "
            "beneficiary a reduced excess)"
        ),
    },
    {
        "item": "Whole-year conversion claim (Track A)",
        "gap": (
            "a converted disabled worker's claim for the spouse's excess is "
            "counted from its whole conversion year (A4's July birth "
            "month), 2 months before the FRA for spouses born 1955 and 4 "
            "for 1956, where 402(q)(1) reduces an excess that starts at "
            "the FRA not at all. Exercise 3 keeps Track A's count in both "
            "scenarios (the baseline start moved by the FRA increase), so "
            "the reform leaves an excess paid in both scenarios unchanged, "
            "as the statute does, at Track A's reduced level (a worker the "
            "reform has not converted by 2030 is still a disabled worker "
            "there and draws none). Counted, not fixed (benefit "
            "counters fra68_spouse_excess_on_conversion_claim and "
            "fra68_spouse_excess_on_conversion_claim_months_early)"
        ),
    },
    {
        "item": "Credits of a worker who died unclaimed",
        "gap": (
            "402(e)(2)(C) and 402(f)(2)(C) pass delayed retirement credits "
            "to the survivor of a worker who died after retirement age "
            "without claiming; the model's never-entitled decedent carries "
            "factor 1.0 in both scenarios, so the reform's cut of those "
            "credits is missed, and under C1/C2 a claim moved past death "
            "loses credits the statute would keep. Counted, not modeled "
            "(benefit counters fra68_widow_credits_not_inherited and "
            "fra68_widow_credits_not_inherited_claim_moved_past_death)"
        ),
    },
    {
        "item": "Survivor reduction span",
        "gap": (
            "exact by cohort (416(l)(2) mapping) in both scenarios; "
            "exercise 1 used the oracle's fixed 84 months, which differs "
            "for survivors born before 1962 who were entitled after 60"
        ),
    },
    {
        "item": "Credit timing and month resolution",
        "gap": (
            "402(w)(3) credits increment months from the following "
            "January; the model applies the full factor at the claim. "
            "Claim ages are whole years and conversion uses A4's July "
            "birth month, so the C1/C2 delay is 0 below 6 months"
        ),
    },
    {
        "item": "Claiming",
        "gap": (
            "one plan per person drawn at 50+ from the 2008 table row "
            "(every projection year snaps to it; its at-FRA age is 65 for "
            "every cohort). C0 keeps every claim age; C1 and C2 (rows F3, "
            "F4) are deterministic stylized delays, not a fitted response"
        ),
    },
)


def run_date() -> str:
    """The calendar date of this run (ISO 8601), recorded in its outputs."""

    return datetime.date.today().isoformat()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _track_a_dry_run() -> Any:
    """Track A's dry-run script (its gaps and A1 rate-path check)."""

    path = ROOT / "scripts" / "track_a_dry_run.py"
    spec = importlib.util.spec_from_file_location("_track_a_dry_run", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def gaps() -> list[dict[str, str]]:
    """Track A's named gaps, with its claiming gap replaced, plus E1's."""

    track = [
        gap for gap in _track_a_dry_run().GAPS if gap["item"] != "Claiming"
    ]
    return [*track, *FRA68_GAPS]


def _fmt(value: Any, digits: int = 2) -> str:
    if value is None or (
        isinstance(value, float) and not math.isfinite(value)
    ):
        return "undefined"
    return f"{value:.{digits}f}"


def _cell_text(stat: dict[str, Any], n_draws: int) -> str:
    floor = stat["floor"]
    floor_text = _fmt(floor["mean"]) if floor["defined"] else "undefined"
    if not stat["defined"]:
        return (
            f"undefined ({stat['n_defined_draws']} of {n_draws} draws "
            f"defined) [{floor_text}]"
        )
    return f"{_fmt(stat['mean'])} ({_fmt(stat['sample_sd'])}) [{floor_text}]"


def _results_markdown(result: dict[str, Any]) -> str:
    config = result["config"]
    n_draws = len(config["draw_indices"])
    cohorts = result["cohorts"]
    lines = [
        f"# {DRY_RUN_HEADER}",
        "",
        "DynaSim exercise 3 (full retirement age to 68, 2030 age profile) "
        f"end-to-end dry run, {result['run']['date']}. Every person, date, "
        "earnings amount, Social Security amount and weight in the cohort "
        "is **invented** (`populace_dynamics.cola_track_a.invented`, seed "
        f"{result['run']['invented_seed']}). No PSID file was opened, no "
        "comparator value was read, and nothing below is a model result "
        "or a comparison with DYNASIM.",
        "",
        "The specification (`docs/design/urban2010_fra68_comparison.md`, "
        f"`{result['specification_check']['specification_version']}`, "
        f"status `{result['specification_check']['specification_status']}`)"
        " records Max's rulings of 2026-09-24 (decision records d188 and "
        "d196); every ruled field below runs at its ruling unless it says "
        "otherwise.",
        "",
        "Labels on every output: "
        + "; ".join(f"*{label}*" for label in result["labels"])
        + "; rows F3 and F4 carry *fixed paths; stylized claiming response "
        "(registered sensitivity)* in place of the mechanical-incidence "
        "label.",
        "",
        "## What ran",
        "",
    ]
    for wave, population in config["populations"].items():
        diagnostics = cohorts[wave]
        rows = [
            row_id
            for row_id, row in result["rows"].items()
            if str(row["row"]["population"]["wave"]) == wave
        ]
        lines.append(
            f"- {wave} wave (weight {population['weight']}, family unit "
            f"{population['family_unit_id']}), rows {', '.join(rows)}: "
            f"{diagnostics['members']} invented persons in "
            f"{diagnostics['family_units']} family units, "
            f"{diagnostics['recipients_opening_year']} Social Security "
            f"recipients in {population['start_year']}, projected "
            f"{population['start_year']} to {config['reference_year']} "
            f"({population['periods']} periods)."
        )
    lines += [
        "- Projection: Track A's (`cola_track_a.runner._project_population`, "
        "the unmodified `engine.loop.ProjectionEngine`), draws "
        f"{config['draw_indices']} (root entropy 5200 + k), once per "
        "population; both scenarios read the same projected state.",
        "- Benefits: `fra68_track.benefits`, Python oracle (not Axiom), "
        "on the TR2008 intermediate COLA path in both scenarios; the "
        "reform overrides the oracle's FRA schedule (P1-P3) and the "
        "widow(er)'s reduction span.",
        "- Tabulation: the A7 five-group statistic, scenario-specific "
        f"membership, statistic id `{config['statistic_id']}`.",
        "",
        "## Invented-data tabulation (not a comparison)",
        "",
        "Percent change in the average 2030 benefit, reform against "
        "baseline: mean over draws, (sample SD over draws) and [mean "
        "half-split floor over seeds, split by opening-wave family unit; "
        "undefined with fewer than two usable seeds]. These numbers "
        "describe the invented cohort only.",
        "",
    ]
    labels = [
        group["label"]
        for group in next(
            row["tabulation"]["groups"]
            for row in result["rows"].values()
            if row["tabulation"]
        )
    ]
    lines.append("| Row | Field changed | " + " | ".join(labels) + " |")
    lines.append("|---" * (2 + len(labels)) + "|")
    for row_id, row in result["rows"].items():
        changed = row["row"]["field_changed"] or "primary"
        if row["tabulation"] is None:
            lines.append(f"| {row_id} | {changed} | {row['status']} |")
            continue
        statistic = row["row"]["statistic"]
        cells = [
            _cell_text(group[statistic], n_draws)
            for group in row["tabulation"]["groups"]
        ]
        lines.append(f"| {row_id} | {changed} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "F5 reports the mean of individual ratios; every other row the "
        "ratio of scenario means. Floors, per-draw cells, counts, the "
        "component shares and the section 16 diagnostics are in "
        "`result.json`.",
        "",
        "## Row status",
        "",
    ]
    lines += [
        f"- {row_id}: {row['status']}."
        for row_id, row in result["rows"].items()
    ]
    lines += ["", "## Checks", ""]
    spec = result["specification_check"]
    consistency = result["parameter_consistency"]
    lines += [
        "- E1 section 21 block against the code (schedules, primary, rows, "
        f"statistic id): consistent = {spec['consistent']}"
        + (f" (mismatches {spec['mismatches']})" if spec["mismatches"] else "")
        + ".",
        "- A1 rate path = A2 `cola_path` = runtime baseline, "
        f"{result['checks']['a1_rate_path']['years_checked']}: "
        f"{result['checks']['a1_rate_path']['a1_equals_a2_equals_runtime']}"
        "; both scenarios read that one path "
        f"(`cola_paths.identical_in_both_scenarios` = "
        f"{result['cola_paths']['identical_in_both_scenarios']}).",
        "- Configuration against inputs, value by value against the "
        "committed sources (consistent = "
        f"{consistency['consistent']}): "
        + ", ".join(
            f"`{name}` {check['consistent']}"
            for name, check in consistency["checks"].items()
        )
        + f". Statutory capture sha256 `{CAPTURE_SHA256[:12]}...`.",
        "- Reform bundles (derived from the baseline bundle): "
        + ", ".join(
            f"{sid} `{record['age_factor_fields_sha256'][:12]}...`"
            for sid, record in result["age_factor_parameters"][
                "schedules"
            ].items()
        )
        + "; baseline `"
        + result["age_factor_parameters"]["baseline"][
            "age_factor_fields_sha256"
        ][:12]
        + "...`.",
        "- Under fixed claim ages (C0 rows) the baseline and reform "
        "memberships coincided in every row (the runner refuses "
        "otherwise).",
        "- Projection identity with exercise 1: "
        f"{result['projection_identity_with_exercise_1']['reason']}.",
        "",
        "## DI window (reported, not modeled)",
        "",
        result["di_window_diagnostic"]["definition"] + ".",
        "",
        "| Population | Schedule | Draw | Person-years exposed | "
        "Expected awards |",
        "|---|---|---|---|---|",
    ]
    for wave, by_schedule in result["di_window_diagnostic"][
        "by_wave_schedule_draw_year"
    ].items():
        for sid, by_draw in by_schedule.items():
            for draw, by_year in by_draw.items():
                exposed = sum(item["exposed"] for item in by_year.values())
                expected = sum(
                    item["expected_awards"] for item in by_year.values()
                )
                lines.append(
                    f"| {wave} wave | {sid} | {draw} | {exposed} | "
                    f"{expected:.3f} |"
                )
    lines += [
        "",
        "## Credits of workers who died unclaimed (counted, not modeled)",
        "",
        "Paid aged widow(er)'s excesses resting on a never-entitled "
        "decedent who died in or after the calendar year of attaining the "
        "scenario's retirement age, summed over draws; in parentheses, "
        "those whose claim C1 or C2 moved past death. The count is not a "
        "bound on the survivors to whom 402(e)(2)(C) and 402(f)(2)(C) "
        "would pass credits the model does not: the death year is annual, "
        "so it can include a decedent who died in the attainment year "
        "before the retirement-age month, and it omits a survivor paid no "
        "excess without the credits whom the credits would have given one.",
        "",
        "| Row | Baseline | Reform |",
        "|---|---|---|",
    ]
    for row_id, row in result["rows"].items():
        counters = row["benefit_counters"]
        cells = []
        for scenario in ("baseline", "reform"):
            total = counters.get(f"{scenario}_{CREDITS_NOT_INHERITED}", 0)
            moved = counters.get(
                f"{scenario}_{CREDITS_NOT_INHERITED_CLAIM_MOVED_PAST_DEATH}",
                0,
            )
            cells.append(f"{total} ({moved})")
        lines.append(f"| {row_id} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "## Spouse's excesses on a conversion claim (counted, not fixed)",
        "",
        "Paid spouse's excesses resting on a converted disabled worker's "
        "conversion claim, summed over draws; in parentheses, those whose "
        "months early are positive (Track A's whole-year conversion count; "
        "402(q)(1) reduces none of them). Each reform keeps the baseline "
        "count, so an excess paid in both scenarios has the same amount in "
        "each; a worker the reform has not converted by 2030 is still a "
        "disabled worker there and draws none, and under C1 and C2 a moved "
        "worker claim can start the excess later.",
        "",
        "| Row | Baseline | Reform |",
        "|---|---|---|",
    ]
    for row_id, row in result["rows"].items():
        counters = row["benefit_counters"]
        cells = [
            f"{counters.get(f'{scenario}_{CONVERSION_CLAIM_EXCESS}', 0)} "
            f"({counters.get(f'{scenario}_{CONVERSION_CLAIM_MONTHS_EARLY}', 0)})"
            for scenario in ("baseline", "reform")
        ]
        lines.append(f"| {row_id} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "## Max's rulings (2026-09-24, decision records d188 and d196)",
        "",
    ]
    lines += [
        f"- `{item['field']}` = `{item['value']}` ({item['decided']}; "
        f"ruling `{item['ruling']}`; follows the ruling: "
        f"{item['follows_ruling']})."
        for item in result["max_rulings"]
    ]
    lines += ["", "## Builder defaults (no ruling names them)", ""]
    lines += [
        f"- `{item['field']}` = `{item['value']}` ({item['source']})."
        for item in result["builder_defaults"]
    ]
    lines += ["", "## Gaps (named, not fixed)", ""]
    lines += [f"- **{gap['item']}.** {gap['gap']}." for gap in result["gaps"]]
    lines += [
        "",
        "## Provenance",
        "",
        f"- Code: `{result['run']['git_head']}` "
        f"(worktree clean: {result['run']['git_clean']}).",
        f"- Python {result['run']['python']}; oracle parameters "
        f"`{result['inputs_provenance']['ssa_parameters']}`.",
        "- Input hashes are listed under `inputs_provenance` in "
        "`result.json`.",
        "",
    ]
    return "\n".join(lines)


def _prepared_cohort(
    config: FRA68Config, *, seed: int, anchor_wave: int, claiming_pmf: Any
) -> tuple[Any, Any]:
    raw = invented.invented_psid2010_inputs(
        seed=seed, claiming_pmf=claiming_pmf, anchor_wave=anchor_wave
    )
    a3 = psid2010.build_psid2010_cohort(
        raw, psid2010.Psid2010CohortSpec(anchor_wave=anchor_wave)
    )
    cohort = prepare_track_a_cohort(
        a3, data_provenance="invented", config=config.track_a_config()
    )
    return raw, cohort


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--draws", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20260922)
    args = parser.parse_args(argv)

    config = FRA68Config(draw_indices=tuple(range(args.draws)))
    claiming_pmf = load_claiming_pmf()
    raw_inputs = {}
    cohorts = {}
    for wave in config.anchor_waves:
        raw_inputs[wave], cohorts[wave] = _prepared_cohort(
            config, seed=args.seed, anchor_wave=wave, claiming_pmf=claiming_pmf
        )
    base_params = load_ssa_parameters()
    params = tr2008_ssa_parameters(
        base_params, alternative=config.tr2008_alternative
    )
    realized = load_cola_history()
    baseline = tr2008_baseline_cola(
        realized,
        first_year=config.tr2008_first_rate_year,
        last_year=config.reference_year,
        alternative=config.tr2008_alternative,
    )
    rate_check = _track_a_dry_run()._spec_rate_check(baseline)
    di_rates = load_di_entitlement_rates(config.di_spec)
    first_projection_year = (
        min(config.track_a_config().start_years.values()) + 1
    )
    mortality = load_tr2008_mortality(
        range(first_projection_year, config.reference_year + 1),
        alternative=config.tr2008_alternative,
        base_year=config.mortality_base_year,
    )
    provenance = {
        "ssa_parameters": params.pe_us_revision,
        "statutory_capture": {
            "path": str(CAPTURE_PATH.relative_to(ROOT)),
            "sha256": CAPTURE_SHA256,
        },
        "tr2008_file_sha256": dict(tr2008.FILE_SHA256),
        "di_rates": {
            key: value
            for key, value in di_rates.provenance.items()
            if key.endswith("sha256")
        },
        "cola_history_sha256": realized.provenance["sha256"],
        "claiming_reference_sha256": _sha256(psid2010.CLAIMING_REFERENCE_PATH),
        "a1_specification_sha256": _sha256(A1_SPECIFICATION_PATH),
        "e1_specification_sha256": _sha256(E1_SPECIFICATION_PATH),
        "mortality": dict(mortality.provenance),
        "invented_inputs": {
            str(wave): dict(raw.provenance) for wave, raw in raw_inputs.items()
        },
    }
    primary, *others = (cohorts[wave] for wave in config.anchor_waves)
    result = run_fra68(
        TrackAInputs(
            cohort=primary,
            params=params,
            baseline=baseline,
            di_rates=di_rates,
            population_mortality=mortality,
            claiming_pmf=claiming_pmf,
            provenance=provenance,
            additional_cohorts=tuple(others),
        ),
        config=config,
        progress=lambda message: print(message, file=sys.stderr),
        check_committed_parameters=True,
    )
    if not result["parameter_consistency"]["consistent"]:
        raise ValueError(
            "the dry-run inputs differ from the configuration: "
            f"{result['parameter_consistency']}"
        )
    result = {
        "header": DRY_RUN_HEADER,
        **result,
        "checks": {"a1_rate_path": rate_check},
        "gaps": gaps(),
        "run": {
            "date": run_date(),
            "invented_seed": args.seed,
            "git_head": _git("rev-parse", "HEAD"),
            "git_clean": _git("status", "--porcelain") == "",
            "python": platform.python_version(),
            "command": " ".join(
                [
                    "python",
                    "scripts/fra68_dry_run.py",
                    *(sys.argv[1:] if argv is None else argv),
                ]
            ),
        },
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "RESULTS.md").write_text(
        _results_markdown(result), encoding="utf-8"
    )
    print(args.output_dir / "result.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
