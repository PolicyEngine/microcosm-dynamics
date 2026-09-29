"""U2 end-to-end DRY RUN on an INVENTED cohort (specification section 14).

INVENTED DATA - NOT A COMPARISON.  The cohort is the invented population
of :mod:`populace_dynamics.uniform_cut_track_u2.invented` (persons,
families, income, Social Security, SSI, wealth, employer DC, weights and
design all invented), run through the real U2 builder, income rows,
income concept and tabulation for all ten registered rows, with the
unscored two-percent interest sensitivity and the F17 diagnostics.  The
poverty thresholds are INVENTED as well; the committed U2 SSI capture and
life tables are the parameters used, and the pinned Track M Census
capture is loaded only to record its pin and its 2012 equality with U1.
No PSID file is opened and no comparator value is read.

The run applies the specification's declared role interpretation
(section 3) under the ``invented_declared`` gate, which exists only for
invented data.  The checks record the refusals the real path gives:

* every family-record mapping round-trips through the registry layouts
  (invented fixed-width records: losses, sentinels, top codes, the
  seven/eight-asset WEALTH1 identities, every employer-DC route);
* under the committed registries, the source gate refuses each wave the
  milestone-1 record leaves open, the registry role context refuses the
  TO VERIFY relationship codes, code 88 refuses under every context, and
  the loader's preflight refuses before any PSID file is opened;
* the registered runner refuses these invented inputs and parameters;
* U2 refuses U1's captures, seed rule, column, rows and rulings, and
  U1's guards refuse U2's settings;
* per-observation monotonicity (R <= B, poverty never lost) in every row
  and both halves of every split.

Usage::

    python scripts/track_u2_dry_run.py --output-dir <dir> [--seed N]

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

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from populace_dynamics.cohorts import age67  # noqa: E402
from populace_dynamics.estimates import adjusted_poverty as ap  # noqa: E402
from populace_dynamics.uniform_cut_track_u2 import (  # noqa: E402
    DRY_RUN_HEADER,
    cohort,
    estimator,
    identity,
    invented,
    loader,
    parameters,
    rows,
    runner,
    sources,
    tabulation,
)

#: A syntactically valid pointer used only to show that the registered
#: path refuses invented inputs (no such comment is implied).
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
            "message": str(error)[:600],
        }
    return {"refused": False}


def _mapping_checks(inputs: cohort.U2Inputs) -> dict[str, Any]:
    """Invented fixed-width records through every wave's registry layout."""

    registries = sources.RegistrySet.committed()
    out: dict[str, Any] = {}
    for wave in sources.SUPPORT_WAVES:
        declared = sources.SourceGate(sources.INVENTED_DECLARED, registries)
        records = invented.invented_fixed_width_records(inputs, wave, declared)
        parsed = loader.read_family_records(records["lines"], wave, declared)
        raw = records["raw"]
        reparsed = sources.parse_fixed_width(records["lines"], records["specs"])
        route = sources.dc_route(wave, declared)
        identity_terms = sources.wealth1_identity(wave, declared)
        strict = sources.SourceGate(sources.REGISTRY, registries)
        out[str(wave)] = {
            "n_records": len(records["lines"]),
            "n_fields": len(records["specs"]),
            "round_trip_equal": bool(
                reparsed.equals(raw[[s.concept for s in records["specs"]]])
            ),
            "income_equal_to_invented_frame": bool(
                parsed["income"]
                .reset_index(drop=True)
                .equals(inputs.family_income[wave].reset_index(drop=True))
            ),
            "income_identity": parsed["income_identity"],
            "wealth1_identity": parsed["wealth1_identity"],
            "wealth1_asset_components": len(identity_terms["assets"]),
            "home_equity_excluded": identity_terms["excluded"],
            "negative_amounts_parsed": {
                concept: int((raw[concept] < 0).sum())
                for concept in (
                    "head_farm",
                    "head_business_asset",
                    "head_rent",
                    "wealth1",
                )
            },
            "top_coded_items": int((raw["head_dividends"] == 999_997).sum()),
            "spouse_age_dk_na": int((raw["wife_age"] == 999).sum()),
            "dc_route_declared": route.as_dict(),
            "dc_paths": {
                column: int(parsed["employer_dc"][column].sum())
                for column in sources.DC_BALANCE_COLUMNS
                if column != "employer_dc"
            },
            "dc_equal_to_invented_frame": bool(
                parsed["employer_dc"][list(sources.DC_BALANCE_COLUMNS)]
                .reset_index(drop=True)
                .equals(
                    inputs.employer_dc[wave][
                        list(sources.DC_BALANCE_COLUMNS)
                    ].reset_index(drop=True)
                )
            ),
            "would_refuse_under_registry_gate": len(declared.would_refuse),
            "registry_gate": _refusal(
                lambda wave=wave, strict=strict: loader.family_record_specs(
                    wave, strict
                )
            ),
            "registry_gate_dc_route": _refusal(
                lambda wave=wave, strict=strict: sources.dc_route(wave, strict)
            ),
        }
    malformed = inputs.family_income[2019].copy()
    return {
        "by_wave": out,
        "negative_where_undocumented_refused": _refusal(
            lambda: _parse_negative(inputs, registries)
        ),
        "crosswalk_as_input_refused": _refusal(
            lambda: sources.field_specs(
                "income",
                2019,
                ["wife_retirement_annuities"],
                sources.SourceGate(sources.INVENTED_DECLARED, registries),
            )
        ),
        "n_families_2019": int(len(malformed)),
    }


def _parse_negative(inputs: cohort.U2Inputs, registries: Any) -> None:
    gate = sources.SourceGate(sources.INVENTED_DECLARED, registries)
    records = invented.invented_fixed_width_records(inputs, 2019, gate)
    raw = records["raw"].copy()
    raw.loc[raw.index[0], "head_ss"] = -5
    lines = sources.encode_fixed_width(
        raw[[s.concept for s in records["specs"]]], records["specs"]
    )
    sources.parse_fixed_width(lines, records["specs"])


def _monotone(result: dict[str, Any]) -> dict[str, Any]:
    """Every cell's change, full sample and each half, is at least zero."""

    out = {}
    for row_id, entry in result["rows"].items():
        table = entry["tabulation"]
        full = all(
            cell["delta"] >= -1e-12
            for cell in table["cells"]
            if cell["defined"]
        )
        halves = all(
            side[name]["delta"] >= -1e-12
            for seed in table["floor_per_seed"]
            for side in (seed["side_a"], seed["side_b"])
            for name in side
            if side[name]["defined"]
        )
        out[row_id] = {
            "per_observation": entry["invariants"],
            "cells_full_sample": full,
            "cells_both_halves_every_seed": halves,
        }
    return out


def _invariants(
    inputs: cohort.U2Inputs, params: parameters.U2Parameters
) -> dict[str, Any]:
    """Per-observation checks for every row, recomputed (not tabulated)."""

    context = sources.RoleContext.declared()
    births = cohort.derive_u2_births(inputs)
    out = {}
    for row_id, row in rows.REGISTERED_ROWS.items():
        built = cohort.build_u2_cohort(
            inputs, row.cohort_spec(), role_context=context, births=births
        )
        members = cohort.income_rows(built, inputs)
        spec = row.income_spec()
        adjusted = estimator.u2_adjusted_incomes(
            members,
            spec,
            context=estimator.U2EstimatorContext(context.kind),
            data_provenance=ap.INVENTED,
            life_table=params.life_tables[spec.mortality_basis],
            thresholds=params.thresholds,
            ssi=params.ssi,
        )
        zero = estimator.u2_adjusted_incomes(
            members,
            estimator.U2IncomeSpec(**{**row.income, "cut_rate": 0.0}),
            context=estimator.U2EstimatorContext(context.kind),
            data_provenance=ap.INVENTED,
            life_table=params.life_tables[spec.mortality_basis],
            thresholds=params.thresholds,
            ssi=params.ssi,
        )
        out[row_id] = {
            "reform_le_baseline": bool(
                (adjusted["reform_income"] <= adjusted["baseline_income"] + 1e-9)
                .all()
            ),
            "poverty_never_lost": bool(
                (~(adjusted["poor_baseline"] & ~adjusted["poor_reform"])).all()
            ),
            "ssi_offset_within_cut": bool(
                (
                    (adjusted["ssi_offset"] >= 0)
                    & (adjusted["ssi_offset"] <= adjusted["cut"] + 1e-9)
                ).all()
            ),
            "ssi_new_nonnegative": bool((adjusted["ssi_new"] >= 0).all()),
            "zero_cut_identity": bool(
                np.allclose(zero["reform_income"], zero["baseline_income"])
                and (zero["poor_reform"] == zero["poor_baseline"]).all()
            ),
            "n_ssi_new_positive": int((adjusted["ssi_new"] > 0).sum()),
            "n_ssi_offset_positive": int((adjusted["ssi_offset"] > 0).sum()),
        }
    return out


def checks(
    seed: int, inputs: cohort.U2Inputs, params: parameters.U2Parameters
) -> dict[str, Any]:
    """The dry run's checks, each recorded (none computes a PSID value)."""

    block = rows.specification_block()
    registries = sources.RegistrySet.committed()
    registry_roles = sources.RoleContext.from_registry(registries)
    declared = sources.RoleContext.declared()
    census = parameters.load_u2_thresholds()
    u1_bound = parameters.U2Parameters(
        thresholds=ap.load_poverty_thresholds(),
        ssi=params.ssi,
        life_tables=params.life_tables,
    )
    u1_ssi = parameters.U2Parameters(
        thresholds=census, ssi=ap.load_ssi_parameters(),
        life_tables=params.life_tables,
    )
    births = cohort.derive_u2_births(inputs)
    u0 = cohort.build_u2_cohort(
        inputs, cohort.U2CohortSpec(), role_context=declared, births=births
    )
    u1 = cohort.build_u2_cohort(
        inputs,
        cohort.U2CohortSpec(row="U1"),
        role_context=declared,
        births=births,
    )
    shared = u0.observations.merge(
        u1.observations, on="observation_id", suffixes=("_u0", "_u1")
    )
    same_attributes = all(
        shared[f"{column}_u0"].astype(str).equals(
            shared[f"{column}_u1"].astype(str)
        )
        for column in (
            "birth_year",
            "fu_head_age",
            "fu_head_spouse_age",
            "fu_head_spouse_person_id",
            "marital_status_4",
            "member_role",
        )
    )
    code88 = invented.with_code_88_cohabitor(inputs)
    return {
        "specification_rows": rows.check_rows_against_block(block),
        "named_deltas": rows.check_named_deltas_against_specification(),
        "u2_rulings_against_block": _refusal(
            lambda: rows.check_u2_rulings_against_block(block)
        ),
        "plans": {
            "u0_pairs": len(cohort.observation_plan(cohort.U2CohortSpec())),
            "u1_pairs": len(
                cohort.observation_plan(cohort.U2CohortSpec(row="U1"))
            ),
            "u1_birth_years": len(
                {b for b, *_ in cohort.observation_plan(
                    cohort.U2CohortSpec(row="U1")
                )}
            ),
            "support_registry": cohort.check_plan_against_support_registry(
                registries
            ),
            "wave_2013_cells": [
                list(cell)
                for cell in cohort.plan_cells(cohort.U2CohortSpec(row="U1"))
                if cell[1] == 2013
            ],
        },
        "identification": {
            "shared_observations": int(len(shared)),
            "identical_births_and_annuitant_attributes": bool(
                same_attributes
            ),
        },
        "mapping": _mapping_checks(inputs),
        "role_refusals": {
            "registry_context_on_invented_inputs": _refusal(
                lambda: cohort.build_u2_cohort(
                    inputs, role_context=registry_roles, births=births
                )
            ),
            "code_88_under_declared_context": _refusal(
                lambda: cohort.build_u2_cohort(
                    code88, role_context=declared
                )
            ),
            "declared_context_on_non_invented_inputs": _refusal(
                lambda: cohort.build_u2_cohort(
                    cohort.replace_provenance(inputs, kind="caller_frames"),
                    role_context=declared,
                )
            ),
            "registry_rules_equal_declared_where_resolved": all(
                registry_roles.rules[key].as_dict()
                == declared.rules[key].as_dict()
                for key, rule in registry_roles.rules.items()
                if rule.refusal is None
            ),
        },
        "loader_preflight": _refusal(loader.source_preflight),
        "registered_guard_refuses_invented_inputs": _refusal(
            lambda: runner.run_track_u2(
                inputs,
                params,
                data_provenance=ap.REGISTERED_REAL,
                role_context=registry_roles,
                registration_pointer=_GUARD_POINTER,
            )
        ),
        "registered_parameter_check_refuses_invented_thresholds": _refusal(
            lambda: parameters.check_u2_parameters(params, ap.REGISTERED_REAL)
        ),
        "census_capture": {
            "sha256": census.provenance["sha256"],
            "overlap_2012": census.provenance["overlap_2012"],
            "weighted_average_unit_dollars_2022": census.provenance[
                "weighted_average_unit_dollars_2022"
            ],
            "required_income_years": census.provenance[
                "required_income_years"
            ],
            "used_by_this_dry_run": False,
        },
        "cross_cohort_refusals": {
            "u1_threshold_capture_under_u2": _refusal(
                lambda: parameters.check_u2_parameters(u1_bound, ap.INVENTED)
            ),
            "u1_ssi_capture_under_u2": _refusal(
                lambda: parameters.check_u2_parameters(u1_ssi, ap.INVENTED)
            ),
            "u1_seed_rule_under_u2": _refusal(
                lambda: cohort.U2CohortSpec(
                    seed_wave_rule=identity.U1_SEED_WAVE_RULE
                )
            ),
            "u0_f_under_u2": _refusal(lambda: cohort.U2CohortSpec(row="U0-F")),
            "u1_column_under_u2": _refusal(
                lambda: tabulation.U2TabulationConfig(
                    comparator_column=identity.U1_COMPARATOR_COLUMN
                )
            ),
            "u1_specification_under_u2": _refusal(
                lambda: rows.specification_block(identity.U1_SPECIFICATION_PATH)
            ),
            "u1_rulings_under_u2": _refusal(
                lambda: rows.check_u2_rulings_against_block(
                    {"decisions": {"ruled_by": "Max", "ruled_on": "2026-09-26",
                                   "decision_record": "d411"}}
                )
            ),
            "u2_seed_rule_under_u1": _refusal(
                lambda: age67.Age67Spec(seed_wave_rule=cohort.SEED_WAVE_RULE)
            ),
            "fallback_headline_under_u2": _refusal(
                lambda: runner.check_headline("U0-F")
            ),
        },
        "invariants": _invariants(inputs, params),
    }


def _fmt(value: Any, digits: int = 2) -> str:
    if value is None or (
        isinstance(value, float) and not math.isfinite(value)
    ):
        return "undefined"
    return f"{value:.{digits}f}"


def _cell(table: dict[str, Any], name: str) -> dict[str, Any]:
    return next(c for c in table["cells"] if c["cell"] == name)


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
    check = result["checks"]
    lines = [
        f"# {DRY_RUN_HEADER}",
        "",
        f"U2 (Boomers 2004, column {result['comparator_column']}) invented "
        f"end-to-end dry run, {run['date']}. Every person, family, amount, "
        "weight and sampling stratum and cluster is **invented** "
        "(`populace_dynamics.uniform_cut_track_u2.invented`, seed "
        f"{provenance['seed']}); so are the poverty thresholds. No PSID "
        "file was opened, no comparator value was read, and nothing below "
        "is a result, a forecast or a comparison with DYNASIM.",
        "",
        "Labels: " + "; ".join(f"*{label}*" for label in result["labels"])
        + ".",
        "",
        "## What ran",
        "",
        "- The invented cohort through the U2 builder, income rows, income "
        "concept and tabulation for all ten rows ("
        + ", ".join(result["rows"])
        + "), under the declared section 3 role interpretation "
        f"(`{result['role_context']}`, invented data only).",
        f"- Headline: row {result['headline']['row']} "
        f"(`{result['headline']['rule']}`; no fallback).",
        "- Parameters: the committed U2 SSI capture and life tables; "
        "**invented** thresholds (the pinned Track M Census capture is "
        "loaded only to record its pin and 2012 equality with U1).",
        "",
        "## Invented-data tabulation (not a comparison)",
        "",
        "Cell `all` of each row: observations, P_B, P_R, Δ = P_R − P_B "
        "(percentage points), the mean half-split floor of Δ and its "
        "design-based SE. These numbers describe invented data only.",
        "",
        "| Row | Observations | P_B | P_R | Δ | Δ floor | Δ design SE |",
        "|---|---|---|---|---|---|---|",
    ]
    for row_id, entry in result["rows"].items():
        lines.append(_cell_line(row_id, _cell(entry["tabulation"], "all")))
    table = result["rows"]["U0"]["tabulation"]
    design = table["design"]
    lines += [
        "",
        f"Row U0 design: {design.get('n_strata')} invented strata, "
        f"{design.get('n_clusters')} clusters, singleton strata "
        f"{design.get('singleton_strata')}.",
        "",
        "### Row U0 by cell (invented)",
        "",
        "| Cell | Observations | P_B | P_R | Δ | Δ floor | Δ design SE |",
        "|---|---|---|---|---|---|---|",
    ]
    for cell in table["cells"]:
        lines.append(_cell_line(cell["cell"], cell))
    sensitivity = result["sensitivities_unscored"]
    lines += ["", "## Unscored sensitivity (invented)", ""]
    for name, entry in sensitivity.items():
        cell = next(c for c in entry["cells"] if c["cell"] == "all")
        lines.append(
            f"- {name} on {entry['row']}: cell `all` Δ "
            f"{_fmt(cell['delta'])} (not scored)."
        )
    mapping = check["mapping"]["by_wave"]
    lines += [
        "",
        "## Checks",
        "",
        f"- Rows equal the section 15 block "
        f"({check['specification_rows']['specification_version']}): "
        f"{check['specification_rows']['rows_equal_the_block']}; named "
        f"deltas equal section 12: "
        f"{check['named_deltas']['equal_to_section_12']}.",
        "- U2 rulings record against the draft block: refused "
        f"{check['u2_rulings_against_block']['refused']} (section 20 step 5 "
        "materializes it).",
        f"- Plans: U0 {check['plans']['u0_pairs']} pairs; U1 "
        f"{check['plans']['u1_pairs']} pairs over "
        f"{check['plans']['u1_birth_years']} birth years; equal to the "
        "support registry: "
        f"{check['plans']['support_registry']['equal_to_support_registry']}; "
        f"wave 2013 cells {check['plans']['wave_2013_cells']}.",
        "- Shared U0/U1 observations have identical births and annuitant "
        "attributes: "
        f"{check['identification']['identical_births_and_annuitant_attributes']}.",
        "- Mapping round trips (invented fixed-width records in each "
        "wave's registry layout): "
        + ", ".join(
            f"{wave} {entry['round_trip_equal']}"
            f"/{entry['income_equal_to_invented_frame']}"
            f"/{entry['dc_equal_to_invented_frame']}"
            for wave, entry in mapping.items()
        )
        + "; WEALTH1 asset components "
        + ", ".join(
            f"{wave}: {entry['wealth1_asset_components']}"
            for wave, entry in mapping.items()
        )
        + ".",
        "- Under the committed registries the source gate refuses: "
        + ", ".join(
            f"{wave} {entry['registry_gate']['refused']}"
            for wave, entry in mapping.items()
        )
        + ".",
        "- Role refusals: registry context on invented inputs "
        f"{check['role_refusals']['registry_context_on_invented_inputs']['refused']};"
        " code 88 under the declared context "
        f"{check['role_refusals']['code_88_under_declared_context']['refused']};"
        " declared context on non-invented inputs "
        f"{check['role_refusals']['declared_context_on_non_invented_inputs']['refused']}.",
        "- Loader preflight refuses before any PSID file is opened: "
        f"{check['loader_preflight']['refused']}.",
        "- The registered runner refuses these invented inputs: "
        f"{check['registered_guard_refuses_invented_inputs']['refused']}; "
        "the registered parameter check refuses invented thresholds: "
        f"{check['registered_parameter_check_refuses_invented_thresholds']['refused']}.",
        "- Cross-cohort refusals: "
        + ", ".join(
            f"{name} {entry['refused']}"
            for name, entry in check["cross_cohort_refusals"].items()
        )
        + ".",
        "- Per-observation monotonicity and SSI bounds, every row: "
        + ", ".join(
            f"{row_id} "
            + str(
                all(
                    value
                    for key, value in entry.items()
                    if not key.startswith("n_")
                )
            )
            for row_id, entry in check["invariants"].items()
        )
        + "; cells in both halves of every split: "
        + ", ".join(
            f"{row_id} {entry['cells_both_halves_every_seed']}"
            for row_id, entry in result["monotonicity"].items()
        )
        + ".",
        "",
        "## Named deltas",
        "",
    ]
    lines += [f"- {delta}." for delta in result["named_deltas"]]
    lines += [
        "",
        "## Provenance",
        "",
        f"- Code: `{run['git_head']}` (worktree clean: {run['git_clean']}).",
        f"- Invented inputs: generator `{provenance['generator']}`, seed "
        f"{provenance['seed']}, frames SHA-256 "
        f"`{provenance['input_frames_sha256']}`.",
        f"- SSI: sha256 `{result['parameters']['ssi']['sha256']}`.",
        f"- Python {run['python']}; command `{run['command']}`.",
        "",
    ]
    return "\n".join(lines)


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_json_ready(v) for v in value]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if value is pd.NA:
        return None
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=invented.DEFAULT_SEED)
    args = parser.parse_args(argv)

    params = parameters.committed_u2_parameters(
        invented.invented_poverty_thresholds()
    )
    inputs = invented.invented_u2_inputs(seed=args.seed)
    gate = sources.SourceGate(
        sources.INVENTED_DECLARED, sources.RegistrySet.committed()
    )
    for wave in sources.SUPPORT_WAVES:
        loader.family_record_specs(wave, gate)
        sources.dc_route(wave, gate)
    result = runner.run_track_u2(
        inputs,
        params,
        data_provenance=ap.INVENTED,
        role_context=sources.RoleContext.declared(),
        source_gate=gate,
        progress=lambda message: print(message, file=sys.stderr),
    )
    result = {
        "header": DRY_RUN_HEADER,
        **result,
        "monotonicity": _monotone(result),
        "checks": checks(args.seed, inputs, params),
        "run": {
            "date": datetime.date.today().isoformat(),
            "invented_seed": args.seed,
            "git_head": _git("rev-parse", "HEAD"),
            "git_clean": _git("status", "--porcelain") == "",
            "python": platform.python_version(),
            "command": " ".join(
                [
                    "python",
                    "scripts/track_u2_dry_run.py",
                    *(sys.argv[1:] if argv is None else argv),
                ]
            ),
        },
    }
    result = _json_ready(result)
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
