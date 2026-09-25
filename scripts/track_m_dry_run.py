"""Track M end-to-end DRY RUN on an INVENTED cohort (plan item M10).

INVENTED DATA - NOT A COMPARISON.  The cohort is the invented population
of :mod:`populace_dynamics.min_benefit_track_m.invented` (persons, family
units, weights, design variables, entitlements, deaths, earnings histories
and observed benefits all invented), run through the real Track M code for
every registered row MS0-MS6 (:func:`populace_dynamics.min_benefit_track_m.
pipeline.run_track_m`): section 4a's years, the one history, years of
coverage, the PIA through the oracle, the options, receipt and the Table 6
tabulation with its floors and design-based standard errors.  The
parameters are real and committed or read from the policyengine-us
checkout the oracle reads: the oracle's wage index, bend points and
reductions, the quarter-of-coverage amounts, the Census one-person 65+
thresholds 2003-2022 (the pinned capture) and the SSA COLA history (for
the invented MS5 benefits).  No PSID file is opened and no comparator
value is read.

The checks record that the specification block equals the code and the
committed draft authorizes no real-data run (nor would a ratified copy
that still lists blockers); that every threshold year the invented cohort
needs is captured, and that a record needing an earlier year is refused
before anything is computed (referee R8); that MS5 read benefit-implied
PIAs and MS0 none; that the registered path refuses invented records,
PSID-kind records without the issue #42 pointer or an authorizing
specification, a subset of rows and other floor seeds; that the one-shot
entry point still refuses because the PSID readers (M3-M5) are not built;
and the plan's INVENTED worked cases (M1 section 16).

Usage::

    python scripts/track_m_dry_run.py --output-dir <dir> [--seed N]
        [--family-units N]

Writes ``result.json`` and ``RESULTS.md`` into ``--output-dir``.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime
import hashlib
import importlib.util
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from populace_dynamics.estimates.parameters import (  # noqa: E402
    load_cola_history,
)
from populace_dynamics.min_benefit_track_m import (  # noqa: E402
    DRY_RUN_HEADER,
    coverage,
    invented,
    pipeline,
    rules,
    specification,
    tabulation,
)
from populace_dynamics.min_benefit_track_m.evaluation import (  # noqa: E402
    PSID_FILES,
    TrackMInputs,
    TrackMParameters,
    WorkerRecord,
    needed_threshold_years,
)
from populace_dynamics.min_benefit_track_m.policy import (  # noqa: E402
    REGISTERED_ROWS,
    TABLE6_OPTIONS,
    TABLE6_ROWS,
    policy_for_row,
)
from populace_dynamics.ss.params import load_ssa_parameters  # noqa: E402

#: A syntactically valid registration pointer used only to show that the
#: registered path refuses invented inputs (no such comment is implied).
_GUARD_POINTER = (
    "https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
    "#issuecomment-0"
)
DEFAULT_SEED = 20260925


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


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


def _entry_script():
    path = ROOT / "scripts" / "run_track_m_registered.py"
    spec = importlib.util.spec_from_file_location("_track_m_entry", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def committed_parameters() -> tuple[TrackMParameters, dict[str, Any]]:
    """The oracle's, the QC amounts, the Census capture and the COLAs."""

    params = load_ssa_parameters()
    qc = coverage.load_qc_amounts()
    thresholds = rules.load_aged_thresholds()
    cola = load_cola_history()
    return TrackMParameters(params, qc, thresholds), {
        "cola_rates": cola,
        "cola_provenance": dict(cola.provenance),
    }


#: The plan's INVENTED cases of the M1 specification's section 16: (P, Y,
#: DI onset).  Every case is born 1948 with its PIA first calculated in
#: 2010 against an invented threshold of $10,000.
PLAN_CASES: dict[str, tuple[float, int, int | None]] = {
    "A": (600.0, 30, None),
    "B": (600.0, 9, None),
    "C": (900.0, 40, None),
    "D": (500.0, 15, 1948 + 44),
    "H": (953.0, 40, None),
    "I": (700.0, 20, None),
}


def plan_cases() -> dict[str, Any]:
    """The section 16 table recomputed: options 1, 2 and 4, both orders.

    The cases define a price-indexed threshold only, so the wage-indexed
    options 3 and 5 (which need an average wage index) are not evaluated,
    as section 16 does not.
    """

    thresholds = rules.AgedThresholds({2010: 10_000.0}, {"kind": "INVENTED"})
    ms2 = policy_for_row("MS2")
    out = {}
    for name, (pia, years, onset) in PLAN_CASES.items():
        worker = rules.WorkerInputs(
            pia=pia,
            work_years=years,
            first_pia_year=2010,
            threshold_year=2010,
            birth_year=1948,
            di_onset_year=onset,
        )

        def run(number, policy=None, worker=worker):
            return rules.evaluate_worker(
                worker, number, thresholds=thresholds, nawi={}, policy=policy
            )

        one, two, four = run(1), run(2), run(4)
        out[name] = {
            "work_years_star": round(two.work_years_star, 2),
            "minimum_option_2": round(two.minimum, 2),
            "flag_option_2": {
                "floor_after_cut": two.on_minimum,
                "cut_after_floor_ms2": run(2, ms2).on_minimum,
            },
            "flag_option_4": {
                "floor_after_cut": four.on_minimum,
                "cut_after_floor_ms2": run(4, ms2).on_minimum,
            },
            "option_2_against_option_1_percent": round(
                100 * rules.relative_to_option_1(two, one), 2
            ),
        }
    return out


def checks(
    inputs: TrackMInputs,
    parameters: TrackMParameters,
    result: dict[str, Any],
) -> dict[str, Any]:
    """The dry run's checks, each recorded (none reads a PSID file)."""

    block = specification.m1_parameter_block()
    needed = needed_threshold_years(
        inputs.workers.values(),
        [policy_for_row(row) for row in REGISTERED_ROWS],
    )
    # A record needing a threshold year before the capture: a worker born
    # 1936, entitled at 68 in 2004, whose year of attaining 62 is 1998.
    early = WorkerRecord(
        "INVENTED-EARLY",
        1936,
        rules.BASIS_OLD_AGE,
        2004,
        {year: 30_000.0 for year in range(1968, 1997)},
    )
    with_early = dataclasses.replace(
        inputs, workers={**inputs.workers, early.record_id: early}
    )
    psid_kind = dataclasses.replace(inputs, provenance_kind=PSID_FILES)
    ratified = json.loads(json.dumps(block))
    ratified["status"], ratified["version"] = (
        "ratified_frozen",
        "m1-ratified-1",
    )
    unblocked = {**ratified, "blocked_by": []}
    entry = _entry_script()
    sources = {
        row: entry_["diagnostics"]["pia_source_by_record"]
        for row, entry_ in result["rows"].items()
    }
    return {
        "specification_block_equals_code": (
            specification.specification_code_check(block)
        ),
        "committed_draft_authorizes_no_real_run": _refusal(
            lambda: specification.check_specification_for_registered_run(block)
        ),
        "a_ratified_copy_still_listing_blockers_is_refused": _refusal(
            lambda: specification.check_specification_for_registered_run(
                ratified
            )
        ),
        "a_ratified_unblocked_copy_would_pass_the_specification_gate": (
            _refusal(
                lambda: specification.check_specification_for_registered_run(
                    unblocked
                )
            )
        ),
        "threshold_years_needed_by_the_invented_cohort": {
            str(year): count for year, count in needed.items()
        },
        "threshold_years_all_captured": _refusal(
            lambda: rules.check_threshold_years(needed, parameters.thresholds)
        )
        | {"captured": parameters.thresholds.source["years"]},
        "a_record_needing_1998_is_refused_before_any_computation": _refusal(
            lambda: pipeline.run_track_m(
                with_early, parameters, data_provenance="invented"
            )
        ),
        "ms5_reads_benefit_implied_pias_and_ms0_none": {
            "passed": (
                sources["MS5"]["benefit_implied"] > 0
                and all(
                    counts["benefit_implied"] == 0
                    for row, counts in sources.items()
                    if row != "MS5"
                )
            ),
            "pia_source_by_row": sources,
        },
        "registered_path_refuses_invented_records": _refusal(
            lambda: pipeline.run_track_m(
                inputs,
                parameters,
                data_provenance=tabulation.REGISTERED_REAL,
                registration_pointer=_GUARD_POINTER,
            )
        ),
        "psid_kind_records_refused_as_invented": _refusal(
            lambda: pipeline.run_track_m(
                psid_kind, parameters, data_provenance="invented"
            )
        ),
        "psid_kind_records_refused_without_the_42_pointer": _refusal(
            lambda: pipeline.run_track_m(
                psid_kind,
                parameters,
                data_provenance=tabulation.REGISTERED_REAL,
            )
        ),
        "psid_kind_records_refused_with_a_pointer_under_the_draft": _refusal(
            lambda: pipeline.run_track_m(
                psid_kind,
                parameters,
                data_provenance=tabulation.REGISTERED_REAL,
                registration_pointer=_GUARD_POINTER,
            )
        ),
        "a_registered_subset_of_rows_is_refused": _refusal(
            lambda: pipeline.run_track_m(
                psid_kind,
                parameters,
                data_provenance=tabulation.REGISTERED_REAL,
                registration_pointer=_GUARD_POINTER,
                specification=unblocked,
                rows=("MS0",),
            )
        ),
        "registered_floor_seeds_cannot_be_changed": _refusal(
            lambda: pipeline.run_track_m(
                psid_kind,
                parameters,
                data_provenance=tabulation.REGISTERED_REAL,
                registration_pointer=_GUARD_POINTER,
                specification=unblocked,
                floor_seeds=(0, 1),
            )
        ),
        "entry_point_missing_components": entry.missing_components(),
        "entry_point_refuses_before_any_psid_read": _refusal(
            entry.check_runnable
        ),
        "plan_invented_cases": plan_cases(),
    }


def _summary(result: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for row, entry in result["rows"].items():
        table = entry["tabulation"]
        out[row] = {
            f"{cell['option']}:{cell['row']}": {
                "share_percent": cell.get("share_percent"),
                "floor_mean": cell["floor"]["mean"],
                "design_se": (cell.get("design_se") or {}).get("se"),
                "unweighted_n": cell.get("unweighted_n"),
            }
            for cell in table["cells"]
        }
        out[row]["y3"] = {
            key: table["y3_option_3_women_to_men"].get(key)
            for key in ("ratio_of_rates", "ratio_of_weighted_counts")
        }
    return out


def provenance(
    parameters: TrackMParameters, extra: dict[str, Any]
) -> dict[str, Any]:
    """What a registration package pins, as far as the dry run knows it.

    The specification and code, the parameter files and the invented
    generator.  The PSID file hashes need the M3-M5 readers; the
    comparator seal is not opened or hashed by a builder lane.
    """

    return {
        "m1_specification": {
            "path": str(specification.M1_SPECIFICATION_PATH.relative_to(ROOT)),
            "sha256": _sha256(specification.M1_SPECIFICATION_PATH),
            "version": specification.m1_parameter_block()["version"],
            "status": specification.m1_parameter_block()["status"],
        },
        "oracle_pe_us_revision": parameters.params.pe_us_revision,
        "quarter_of_coverage": dict(parameters.qc.source),
        "census_thresholds": dict(parameters.thresholds.source),
        "cola_history": {
            key: extra["cola_provenance"][key]
            for key in ("path", "sha256", "content_sha256")
        },
        "psid_files": "none read (the M3-M5 readers are not built)",
        "comparator_seal": "not opened and not hashed by this lane",
    }


def _markdown(document: dict[str, Any]) -> str:
    result = document["result"]
    checks_ = document["checks"]
    lines = [
        f"# {DRY_RUN_HEADER}",
        "",
        "Track M (DynaSim exercise 4, the minimum benefit) end-to-end dry "
        "run on an **INVENTED** PSID-shaped cohort. Every person, family "
        "unit, weight, design variable, entitlement, death, earnings "
        "history and observed benefit is invented; the numbers below are "
        "not PSID values and not a result, and they compare with nothing. "
        "The parameters are real: the oracle's (policyengine-us), the "
        "quarter-of-coverage amounts, the pinned Census one-person 65+ "
        "thresholds 2003-2022 and the SSA COLA history.",
        "",
        f"- Labels: {'; '.join(result['labels'])}",
        f"- Disclosure (d280): {result['disclosure']}",
        f"- Code: `{document['run']['git_head']}` (tree clean: "
        f"{document['run']['git_clean']})",
        f"- M1 specification: `{document['provenance']['m1_specification']['version']}` "
        f"(`{document['provenance']['m1_specification']['sha256']}`)",
        f"- Invented cohort: {result['inputs']['n_persons']} persons, "
        f"{result['inputs']['n_worker_records']} worker records, "
        f"{result['inputs']['source']['n_family_units']} family units, seed "
        f"{result['inputs']['source']['seed']}",
        "- Census threshold capture: "
        f"`{result['parameters']['thresholds']['sha256']}`",
        "",
        "## Invented shares receiving a minimum (percent), by row",
        "",
        "| Row | "
        + " | ".join(
            f"Opt {n} {r}" for n in TABLE6_OPTIONS for r in TABLE6_ROWS
        )
        + " |",
        "|---|" + "---:|" * (len(TABLE6_OPTIONS) * len(TABLE6_ROWS)),
    ]
    for row, cells in document["summary"].items():
        values = [
            cells[f"{n}:{r}"]["share_percent"]
            for n in TABLE6_OPTIONS
            for r in TABLE6_ROWS
        ]
        lines.append(
            f"| {row} | "
            + " | ".join("—" if v is None else f"{v:.1f}" for v in values)
            + " |"
        )
    head = document["summary"]["MS0"]["2:all"]
    floor = head["floor_mean"]
    lines += [
        "",
        "Invented headline cell (MS0, option 2, All): "
        f"{head['share_percent']:.1f}, five-seed floor mean "
        + ("undefined" if floor is None else f"{floor:.2f}")
        + f", design SE {head['design_se']:.2f} percentage points.",
        "",
        "## Checks",
        "",
    ]
    for name, value in checks_.items():
        if isinstance(value, dict) and "refused" in value:
            state = "refused" if value["refused"] else "passed"
            detail = value.get("message", "")
            lines.append(
                f"- `{name}`: {state}"
                + (f" ({value['error']}: {detail[:200]})" if detail else "")
            )
        elif isinstance(value, dict) and "passed" in value:
            lines.append(f"- `{name}`: passed = {value['passed']}")
        elif name == "entry_point_missing_components":
            lines.append(f"- `{name}`: {', '.join(value)}")
        elif name == "specification_block_equals_code":
            lines.append(f"- `{name}`: {value['consistent']}")
        elif name == "threshold_years_needed_by_the_invented_cohort":
            lines.append(
                f"- `{name}`: "
                + ", ".join(f"{year} ({n})" for year, n in value.items())
            )
    lines += [
        "",
        "## The plan's INVENTED worked cases (M1 section 16)",
        "",
        "| Case | Y* | M, option 2 | Option 2 flag (G10 / MS2) | "
        "Option 4 flag (G10 / MS2) | Option 2 against option 1 |",
        "|---|---:|---:|---|---|---:|",
    ]
    for name, case in checks_["plan_invented_cases"].items():
        two, four = case["flag_option_2"], case["flag_option_4"]
        lines.append(
            f"| {name} | {case['work_years_star']:.2f} | "
            f"{case['minimum_option_2']:.2f} | "
            f"{int(two['floor_after_cut'])} / "
            f"{int(two['cut_after_floor_ms2'])} | "
            f"{int(four['floor_after_cut'])} / "
            f"{int(four['cut_after_floor_ms2'])} | "
            f"{case['option_2_against_option_1_percent']:+.2f}% |"
        )
    lines += [
        "",
        "`result.json` holds every cell, floor, standard error, Y3, N "
        "column and diagnostic of every row, each check in full, and the "
        "provenance a registration package pins.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--family-units", type=int, default=600)
    args = parser.parse_args(argv)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    parameters, extra = committed_parameters()
    inputs = invented.invented_track_m_inputs(
        seed=args.seed,
        n_family_units=args.family_units,
        params=parameters.params,
        cola_rates=extra["cola_rates"],
    )
    result = pipeline.run_track_m(
        inputs, parameters, data_provenance="invented"
    )
    document = {
        "header": DRY_RUN_HEADER,
        "description": (
            "Track M end-to-end dry run on an INVENTED PSID-shaped cohort: "
            "every registered row MS0-MS6 through the real Track M code, "
            "with real committed parameters. Not PSID values, not a "
            "result, not a comparison."
        ),
        "summary": _summary(result),
        "checks": checks(inputs, parameters, result),
        "provenance": provenance(parameters, extra),
        "result": result,
        "run": {
            "started": started,
            "finished": datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat(),
            "git_head": _git("rev-parse", "HEAD"),
            "git_clean": _git("status", "--porcelain") == "",
            "python": platform.python_version(),
            "command": " ".join(
                [
                    "python",
                    "scripts/track_m_dry_run.py",
                    *(sys.argv[1:] if argv is None else argv),
                ]
            ),
        },
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    path = args.output_dir / "result.json"
    path.write_text(
        json.dumps(document, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "RESULTS.md").write_text(
        _markdown(document), encoding="utf-8"
    )
    print(path, hashlib.sha256(path.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
