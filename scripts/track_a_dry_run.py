"""Track A end-to-end DRY RUN on an INVENTED cohort (plan items A5/A9).

INVENTED DATA - NOT A COMPARISON.  The cohort is the invented population
of :mod:`populace_dynamics.cola_track_a.invented`, read both as the 2011
wave (rows R0-R5, opening 2010) and as the 2009 wave (row R6, opening
2008), each run through the real A3 builder, the unmodified projection
loop with the A2/A4 adapters, the A6 benefit paths and the A7 tabulation.
No PSID file is opened and no comparator value is read.  The parameters
are the committed ones (TR2008 capture, 2008-vintage DI rates, the
claim-age table, the realized COLA history) plus the oracle's statutory
parameters from the local policyengine-us checkout, with the AWI replaced
by TR2008's.  The run compares every one of them with its committed
source (``check_committed_parameters``), the statutory parameters with
the committed capture ``data/external/track_a_statutory_parameters.json``.

Usage::

    python scripts/track_a_dry_run.py --output-dir <dir> [--draws 3]

Writes ``result.json`` and ``RESULTS.md`` into ``--output-dir``.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
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
    DRY_RUN_HEADER,
    TrackAConfig,
    TrackAInputs,
    invented,
    prepare_track_a_cohort,
    run_track_a,
)
from populace_dynamics.cola_track_a.config import (  # noqa: E402
    REGISTERED_ROWS,
)
from populace_dynamics.cola_track_a.mortality import (  # noqa: E402
    load_tr2008_mortality,
)
from populace_dynamics.cola_track_a.runner import (  # noqa: E402
    A1_SPECIFICATION_PATH,
    a1_parameter_block,
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
from populace_dynamics.ss.params import load_ssa_parameters  # noqa: E402

GAPS: tuple[dict[str, str], ...] = (
    {
        "item": "Mortality after the opening year",
        "gap": (
            "TR2008 publishes no projected death probabilities by single "
            "age and sex; the A2 substitute (SSA 2004 period table x TR2008 "
            "V.A1 ASADR ratio, under-65 and 65+ groups, base year 2004) is "
            "used for 2011-2030 (2009-2030 for R6). It is proposed, not "
            "adopted; with base 2004 the 65+ ratio exceeds 1 in 2011-2012, "
            "and in 2009-2010, which only R6 projects"
        ),
    },
    {
        "item": "DI-aware mortality netting",
        "gap": (
            "A4 nets non-DI mortality within the population model's cells; "
            "for the single-year A2 model these are single ages by sex, and "
            "a cell whose DI-origin expected deaths exceed the model's gives "
            "its other members probability zero. Infeasible cells are "
            "counted per draw (small invented cohort: many)"
        ),
    },
    {
        "item": "Earnings after the opening year",
        "gap": (
            "no earnings are drawn after the opening year, 2010 (2008 for "
            "R6; the certified forward law is fit for 2015-2022 from 2014); "
            "AIME uses the career from 1968 through the opening year with "
            "later years zero. Weights only"
        ),
    },
    {
        "item": "Earnings before 1968",
        "gap": "absent (zero in the AIME). Weights only",
    },
    {
        "item": "DI and pre-eligibility-death levels",
        "gap": (
            "disclosed oracle approximation (the oracle's AIME over the "
            "career through the onset or death year, indexed to the second "
            "year before it, divided by 35 years with no elapsed or dropout "
            "years; PIA at that year's bend points); Max's ruling on "
            "decision 2(b) (2026-09-23, d074) for DI levels, and an A5 "
            "builder default for deaths before 62. Weights only"
        ),
    },
    {
        "item": "Disability clock for awards at 62 or later",
        "gap": (
            "A4 exposes retirement claimants below FRA to DI awards; A5 "
            "keeps such a worker's eligibility clock at the year of "
            "attaining 62 (its reading of 415(a)(3)(B)(i) and "
            "415(i)(2)(A)(iii)), not the award year the A1 section 6 table "
            "gives for a disabled worker; R2 keeps the award year. The DI "
            "benefit replaces the retirement benefit and carries no "
            "claim-age reduction. A1 does not address this case"
        ),
    },
    {
        "item": "Insured status",
        "gap": (
            "not modeled for retirement or survivor benefits: a projected "
            "claimant whose career through the opening year gives a "
            "positive AIME has a positive oracle PIA and becomes a "
            "retired-worker beneficiary however few years it covers, and a "
            "widow(er)'s benefit does not check the deceased's insured "
            "status (A4 sets DI incidence per population, so DI awards "
            "never consult it). Membership and weights"
        ),
    },
    {
        "item": "Linked spouses outside the opening roster",
        "gap": (
            "their deaths are not simulated, so their partners are never "
            "widowed in the projection, and with no career or simulated "
            "state in the cohort no spouse's benefit rests on their record "
            "(counted in the cohort diagnostics, and per row as "
            "spouse_outside_roster, or spouse_unlinked for a married "
            "claimant with no linked spouse)"
        ),
    },
    {
        "item": "Opening-year Social Security unobserved",
        "gap": (
            "a person whose opening-year Social Security (2010, or 2008 "
            "for R6) A3 could not observe (status unobserved) opens as a "
            "non-recipient, so any benefit is projected as a "
            "non-recipient's would be (a claim plan or an A4 award, on the "
            "career PIA) rather than carried from an observed amount "
            "(counted as ss_opening_year_unobserved in the cohort "
            "diagnostics and beneficiaries_ss_opening_year_unobserved per "
            "row)"
        ),
    },
    {
        "item": "Widow(er)s of workers who died before the opening wave",
        "gap": (
            "the late spouse is outside the cohort and has no career, so a "
            "widow(er) not receiving in the opening year gets no "
            "aged-widow(er) benefit (counted as "
            "widow_deceased_outside_roster)"
        ),
    },
    {
        "item": "Disabled widow(er)s and child-in-care beneficiaries",
        "gap": (
            "not projected (A4 models disabled workers only); only opening "
            "stock survivors still under 60 in 2030 carry the "
            "disabled_widow component"
        ),
    },
    {
        "item": "Marriage dynamics",
        "gap": (
            "no marriage, divorce or remarriage is drawn after the opening "
            "year"
        ),
    },
    {
        "item": "Auxiliary entitlement timing",
        "gap": (
            "A5 builder choices: aged widow(er)s entitled at the later of "
            "widowhood and 60; spouses at the later of their own claim and "
            "the worker's entitlement, at 62 or older. A disabled worker "
            "still entitled to DI draws no spouse's excess; one converted "
            "at FRA claims at the conversion"
        ),
    },
    {
        "item": "Contribution and benefit base",
        "gap": (
            "the oracle's realized series (policyengine-us, bound to the "
            "committed statutory capture), which equals TR2008 V.C1 for "
            "1975-2008; for 2009 and 2010 the realized 106,800 differs "
            "from V.C1's projected 106,500 and 110,700 (recorded as "
            "documented differences). Only years through the opening year "
            "enter because no later earnings are drawn, so R6 reads none "
            "of the differing years"
        ),
    },
    {
        "item": "R6 opening receipt start",
        "gap": (
            "the Social Security reader resolves income years 2008, 2010 "
            "and 2012 only, so no 2009-wave recipient's first receipt can "
            "be bracketed: every 2008 recipient's receipt start is "
            "censored at 2008 (the R20 year-before-last item, about 2007, "
            "is not used). Retired workers' claim years are imputed at or "
            "before 2008, and the receipt-start clocks of disabled workers "
            "and of survivors and spouses under 62 are 2008 at the latest, "
            "before the first reduced increase (2009), so no reduced "
            "increase is lost (A1 section 6)"
        ),
    },
    {
        "item": "R6 disability status",
        "gap": (
            "the M4 self-report comes from the 2009 wave only (the A3 "
            "default: the anchor wave, nearest the 2008 opening); later "
            "waves are not consulted"
        ),
    },
    {
        "item": "Opening-stock DI recovery",
        "gap": (
            "A1 rule 4 fixes the opening basis but does not mention "
            "recovery; A5 ends a disabled worker's opening basis at a "
            "simulated recovery"
        ),
    },
    {
        "item": "Claiming",
        "gap": (
            "one plan per person drawn at 50+ from the 2008 table row "
            "(every projection year snaps to it); a plan age already passed "
            "claims in the next year. No claiming response to the reform"
        ),
    },
    {
        "item": "Immigration and births",
        "gap": "closed cohort: no entrants after the opening year",
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


def _spec_rate_check(baseline: Any) -> dict[str, Any]:
    block = a1_parameter_block()
    spec = {
        int(k): float(v) for k, v in block["rate_path"]["baseline"].items()
    }
    a2 = {
        entry.determination_year: entry.percent
        for entry in tr2008.cola_path(min(spec), max(spec))
    }
    runtime = {
        year: round(100.0 * baseline.rate_for_determination_year(year), 10)
        for year in spec
    }
    mismatches = {
        year: {"a1": spec[year], "a2": a2[year], "runtime": runtime[year]}
        for year in spec
        if not (spec[year] == a2[year] == runtime[year])
    }
    if mismatches:
        raise ValueError(f"A1 rate path differs from A2/runtime: {mismatches}")
    rows = block["rows"]
    for row_id, row in REGISTERED_ROWS.items():
        expected = {**rows["R0"], **rows[row_id]}
        if (
            expected["first_reduced_determination_year"]
            != row.first_reduced_determination_year
            or expected["exposure_clock"] != row.exposure_clock.value
            or list(expected["components"]) != list(row.components)
            or expected["population"] != row.population.as_dict(2030)
        ):
            raise ValueError(f"{row_id} differs from the A1 block")
    return {
        "a1_version": block["version"],
        "a1_status": block["status"],
        "years_checked": [min(spec), max(spec)],
        "a1_equals_a2_equals_runtime": True,
        "registered_rows_equal_the_a1_block": sorted(REGISTERED_ROWS),
    }


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


def _undefined_lines(result: dict[str, Any]) -> list[str]:
    lines = []
    for row_id, row in result["rows"].items():
        tabulation = row["tabulation"]
        if tabulation is None:
            continue
        for cell in tabulation["undefined_cells"]:
            reasons = ", ".join(
                f"draw {item['draw']}: {item['reason']}"
                for item in cell["undefined_draws"]
            )
            lines.append(
                f"- {row_id}, {cell['group']}, {cell['statistic']}: "
                f"{cell['n_defined_draws']} draws defined ({reasons})."
            )
        for group in tabulation["groups"]:
            for statistic in (
                "ratio_of_scenario_means",
                "mean_of_individual_ratios",
            ):
                floor = group[statistic]["floor"]
                if not floor["defined"]:
                    lines.append(
                        f"- {row_id}, {group['label']}, {statistic} floor: "
                        f"undefined ({floor['undefined_reason']}; "
                        f"{floor['n_seeds']} usable seeds)."
                    )
    return lines


def _results_markdown(result: dict[str, Any]) -> str:
    config = result["config"]
    n_draws = len(config["draw_indices"])
    cohorts = result["cohorts"]
    populations = config["populations"]
    lines = [
        f"# {DRY_RUN_HEADER}",
        "",
        "Track A (plan item A5) end-to-end dry run, "
        f"{result['run']['date']}. Every person, date, earnings amount, "
        "Social Security amount and weight in the cohort is **invented** "
        "(`populace_dynamics.cola_track_a.invented`, seed "
        f"{result['run']['invented_seed']}). No PSID file was opened, no "
        "comparator value was read, and nothing below is a model result "
        "or a comparison with DYNASIM.",
        "",
        "Labels on every output: "
        + "; ".join(f"*{label}*" for label in result["labels"])
        + ".",
        "",
        "## What ran",
        "",
        "- Invented cohort, read as two populations through the real A3 "
        "builder (`cohorts.psid2010.build_psid2010_cohort`), with "
        "retired-worker, disabled-worker and survivor openers and "
        "non-beneficiaries, every person aged 30 to 80 at the end of "
        "2010:",
    ]
    for wave, population in populations.items():
        diagnostics = cohorts[wave]
        rows = [
            row_id
            for row_id, row in result["rows"].items()
            if str(row["row"]["population"]["wave"]) == wave
        ]
        lines.append(
            f"  - {wave} wave (weight {population['weight']}, family unit "
            f"{population['family_unit_id']}), "
            f"{'row' if len(rows) == 1 else 'rows'} {', '.join(rows)}: "
            f"{diagnostics['members']} persons in "
            f"{diagnostics['family_units']} family units, "
            f"{diagnostics['recipients_opening_year']} Social Security "
            f"recipients in {population['start_year']}, projected "
            f"{population['start_year']} to {config['reference_year']} "
            f"({population['periods']} periods). A3 source provenance: "
            f"`{diagnostics['source_provenance']['kind']}`."
        )
    lines += [
        "- Projection: unmodified `engine.loop.ProjectionEngine`, draws "
        f"{config['draw_indices']} (root entropy 5200 + k, person-keyed "
        "streams), once per population. Mortality: A4 DI-aware adapter "
        "over the A2 year-aware substitute. DI: A4. Claiming: "
        "`engine.claiming` successor, DI rows excluded, table rows <= "
        "2008. Marital: pass through with widowhood from the simulated "
        "death of a linked spouse. No births, earnings or household steps.",
        "- Benefits: A6 scenario paths on the TR2008 intermediate COLA "
        "path, Python oracle (not Axiom). Both scenarios read the same "
        "projected paths.",
        "- Tabulation: A7 five-group statistic for rows "
        f"{', '.join(config['rows'])}. Every registered row of A1 section "
        "18 was built.",
        "",
        "## Invented-data tabulation (not a comparison)",
        "",
        "Percent change in the average 2030 benefit, reform against "
        "baseline: mean over draws, (sample SD over draws) and [mean "
        "half-split floor over seeds, split by opening-wave family unit; "
        "undefined with fewer than two usable seeds, per A1 section 16]. "
        "An undefined cell is reported as undefined with its number of "
        "defined draws (A1 section 7); the rest of the row is kept. These "
        "numbers describe the invented cohort only.",
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
    lines.append("| Row | " + " | ".join(labels) + " |")
    lines.append("|---" * (1 + len(labels)) + "|")
    for row_id, row in result["rows"].items():
        if row["tabulation"] is None:
            lines.append(f"| {row_id} | {row['status']} |")
            continue
        headline = row["row"]["headline_statistic"]
        cells = [
            _cell_text(group[headline], n_draws)
            for group in row["tabulation"]["groups"]
        ]
        lines.append(f"| {row_id} | " + " | ".join(cells) + " |")
    undefined = _undefined_lines(result)
    lines += [
        "",
        "R3 reports the mean of individual ratios; every other row the "
        "ratio of scenario means. Floors, per-draw cells, counts and the "
        "weighted component shares of each cell are in `result.json`.",
        "",
        "## Row status and undefined values",
        "",
    ]
    lines += [
        f"- {row_id}: {row['status']}."
        for row_id, row in result["rows"].items()
    ]
    lines += [""]
    if undefined:
        lines += [
            "Undefined draw summaries and floors, each with its reason "
            "(A1 sections 7 and 16):",
            "",
            *undefined,
        ]
    else:
        lines.append(
            "No draw summary or floor of any row is undefined in this run."
        )
    consistency = result["parameter_consistency"]
    lines += [
        "",
        "## Checks",
        "",
        f"- A1 rate path = A2 `cola_path` = runtime baseline, "
        f"{result['checks']['spec_rate_path']['years_checked']}: "
        f"{result['checks']['spec_rate_path']['a1_equals_a2_equals_runtime']}"
        "; every registered row (R0-R6) equals the A1 section 21 block.",
        "- Lowest reduced rate through 2030 by row: "
        + ", ".join(
            f"{row} {100 * value:.1f}%"
            for row, value in result["reduced_rate_minimum_by_row"].items()
        )
        + " (the A1 floor assertion requires every one to be positive).",
        "- A4 DI stock-flow identity held in every year of every draw of "
        "both populations (`di_stock_flow` raises otherwise).",
        "- Scheduled entrants: 0, and no step creates a person. The "
        "projection metadata carries no allocator, so the entrant "
        "allocator check had nothing to test.",
        "- Configuration against inputs, value by value against the "
        "committed sources (consistent = "
        f"{consistency['consistent']}): "
        + ", ".join(
            f"`{name}` {check['consistent']}"
            for name, check in consistency["checks"].items()
        )
        + ". The statutory checks bind the realized COLA history before "
        "2008 (determination years 1979-2007) and the oracle's bend "
        "points, contribution and benefit base, PIA factors, FRA, early "
        "reduction, delayed credits and auxiliary constants to the "
        f"committed capture (sha256 `{CAPTURE_SHA256[:12]}...`).",
        "- Provenance guard: each cohort's `invented` label agrees with "
        "the source provenance the A3 builder recorded (the invented "
        "generator's frame digest, re-generated from its seed).",
        "",
        "## Diagnostics per draw",
        "",
        "| Population | Draw | Alive 2030 | Deaths | DI stock 2030 | "
        "Widowed in projection (alive 2030) | Infeasible mortality cells |",
        "|---|---|---|---|---|---|---|",
    ]
    reference = str(config["reference_year"])
    for wave, by_draw in result["draws"].items():
        for draw, diag in by_draw.items():
            flows = diag["di_stock_flow"]
            lines.append(
                f"| {wave} wave | {draw} "
                f"| {diag['alive_by_year'][reference]} "
                f"| {sum(diag['deaths_by_year'].values())} "
                f"| {flows[-1]['stock_end'] if flows else 'n/a'} "
                f"| {diag['widowed_in_projection_alive_reference_year']} "
                f"| {diag['infeasible_mortality_cells']} |"
            )
    lines += ["", "## Gaps (named, not fixed)", ""]
    lines += [f"- **{gap['item']}.** {gap['gap']}." for gap in result["gaps"]]
    lines += [
        "",
        "## Max's rulings (2026-09-23, decision records d074 and d075)",
        "",
    ]
    lines += [
        f"- `{item['field']}` = `{item['value']}` ({item['decided']}, "
        f"{item['decision_record']}; ruling `{item['ruling']}`; follows "
        f"the ruling: {item['follows_ruling']})."
        for item in result["max_rulings"]
    ]
    lines += [
        "",
        "## Builder defaults (no ruling covers them; not ratified)",
        "",
    ]
    lines += [
        f"- `{item['field']}` = `{item['value']}` ({item['source']}; fixed "
        f"by {item['fixed_by']})."
        + (f" Note: {item['note']}." if item.get("note") else "")
        for item in result["builder_defaults"]
    ]
    lines += [
        "",
        "## Provenance",
        "",
        f"- Code: `{result['run']['git_head']}` "
        f"(worktree clean: {result['run']['git_clean']}).",
        "- Population mortality: "
        f"`{result['population_mortality']['class']}` (year-aware: "
        f"{result['population_mortality']['year_aware']}).",
        f"- Python {result['run']['python']}; oracle parameters "
        f"`{result['inputs_provenance']['ssa_parameters']}`.",
        "- Input hashes are listed under `inputs_provenance` in "
        "`result.json`.",
        "",
    ]
    return "\n".join(lines)


def _prepared_cohort(
    config: TrackAConfig, *, seed: int, anchor_wave: int, claiming_pmf: Any
) -> tuple[Any, Any]:
    raw = invented.invented_psid2010_inputs(
        seed=seed, claiming_pmf=claiming_pmf, anchor_wave=anchor_wave
    )
    a3 = psid2010.build_psid2010_cohort(
        raw, psid2010.Psid2010CohortSpec(anchor_wave=anchor_wave)
    )
    cohort = prepare_track_a_cohort(
        a3, data_provenance="invented", config=config
    )
    return raw, cohort


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--draws", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20260922)
    args = parser.parse_args(argv)

    config = TrackAConfig(draw_indices=tuple(range(args.draws)))
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
    di_rates = load_di_entitlement_rates(config.di_spec)
    first_projection_year = min(config.start_years.values()) + 1
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
        "mortality": dict(mortality.provenance),
        "invented_inputs": {
            str(wave): dict(raw.provenance) for wave, raw in raw_inputs.items()
        },
    }
    primary, *others = (cohorts[wave] for wave in config.anchor_waves)
    result = run_track_a(
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
        "checks": {"spec_rate_path": _spec_rate_check(baseline)},
        "gaps": list(GAPS),
        "run": {
            "date": run_date(),
            "invented_seed": args.seed,
            "git_head": _git("rev-parse", "HEAD"),
            "git_clean": _git("status", "--porcelain") == "",
            "python": platform.python_version(),
            "command": " ".join(
                [
                    "python",
                    "scripts/track_a_dry_run.py",
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
