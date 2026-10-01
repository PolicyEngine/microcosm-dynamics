"""Registration 18's model side, using the unchanged mechanism L."""

from __future__ import annotations

import copy
import math
from collections import Counter, defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd

from populace_dynamics import scenario_benefits as sb
from populace_dynamics.cola_track_a import runner as legacy
from populace_dynamics.cola_track_a.adapters import claiming_schedule
from populace_dynamics.cola_track_a.benefits import (
    BenefitContext,
    StateLookups,
    reference_benefit_rows,
)
from populace_dynamics.cola_track_a.config import (
    builder_defaults,
    max_rulings,
    rulings_departures,
)
from populace_dynamics.engine.di_entitlement import (
    fra_schedule_from_parameters,
)
from populace_dynamics.estimates.cola_age_profile import REGISTERED_REAL

from .config import (
    AUTHORIZATION,
    DEFERRED_ROWS,
    REGISTERED_ROWS,
    REGISTRATION_POINTER,
    SPECIFICATION_PATH,
    ACOLAConfig,
    check_specification,
)
from .nulls import context_beneficiary_count, nulls_for_run
from .statistics import (
    summarize_cost,
    summarize_mint,
)

SCHEMA_VERSION = "populace_dynamics.acola_track.run.v1"
MEMBERSHIP_NOTE = (
    "Under mechanism L S_base and S_reform are equal by construction: "
    "the legacy emitter retains positive baseline benefits, refuses a "
    "nonpositive reform total, and sets both beneficiary flags true. "
    "Equal counts are not evidence of independently equal membership."
)
GAPS = (
    {
        "key": "statutory_rounding",
        "description": (
            "Worker PIA paths floor to dimes after increases and again "
            "after the claim-age factor. The common eligibility AIME "
            "uses dollar rounding. A worker's cut bound uses a "
            "benefit-level-dependent allowance for propagated dime "
            "losses and the final dime floor, not a fixed percentage "
            "tolerance. Dual entitlement has a separate structural "
            "exception. No rounding adjustment is applied to results."
        ),
        "source": (
            "scenario_benefits.increased_pia_path, monthly_benefit_path; "
            "ss.benefits.aime; ss.statutory_aime"
        ),
        "adjustment_applied": False,
    },
    {
        "key": "dual_entitlement_bounds_and_monotonicity",
        "intended_violation": True,
        "description": (
            "Mechanism L subtracts the full own increased PIA from the "
            "spouse excess while an early own retirement benefit carries "
            "a smaller claim-age factor. If the spouse excess begins "
            "later and carries fewer reduced COLAs, its increase can "
            "exceed the loss of the own benefit. Individual and aggregate "
            "benefits can therefore rise under a cut, violating the "
            "intended full-null-to-zero bounds and monotonicity. This is "
            "a structural effect, so no fixed rounding tolerance is "
            "asserted. The shared registered arithmetic is unchanged."
        ),
        "source": (
            "cola_track_a/benefits.py:_spouse_excess; "
            "scenario_benefits.py:spouse_excess_path; "
            "ss/benefits.py:spousal_benefit"
        ),
    },
    {
        "key": "reform_only_auxiliary_excess",
        "description": (
            "Mechanism L drops spouse and widow excesses whose baseline "
            "is zero even when the reform excess is positive. This "
            "pushes P away from zero; the registered arithmetic is kept."
        ),
        "source": "cola_track_a/benefits.py:_spouse_excess,_widow_excess",
        "counter": None,
        "undefined_reason": (
            "The public row emitter exposes neither the dropped excess "
            "nor a counter; counting would require copying private "
            "benefit arithmetic or editing a shared module."
        ),
    },
    {
        "key": "annual_convention_omissions",
        "description": (
            "The annual convention omits family maximums, earnings "
            "tests, recomputation and payment-month timing."
        ),
        "source": "scenario_benefits.py module annual-convention note",
    },
    {
        "key": "closed_cohort",
        "description": (
            "The R0 population is closed, has no children or post-2010 "
            "immigrants and draws no post-2010 earnings. Disabled "
            "widow(er)s enter only in the opening stock. The context "
            "beneficiary count does not scale the row."
        ),
        "source": "Registration 18 Population and Adjustments",
    },
    {
        "key": "benefits_only_cost",
        "description": (
            "P covers scheduled benefits only. Comparator cost "
            "definitions and their administrative-expense and Railroad "
            "Retirement interchange flags are reported by the comparison "
            "lane; an unstated flag gives unsigned dilution. Income-rate "
            "changes are comparator memo items, not this cost statistic."
        ),
        "source": "Registration 18 Adjustments",
    },
    {
        "key": "baseline_vintage",
        "description": (
            "The model uses TR 2008 paths; OACT uses TR 2026, PWBM its "
            "own baseline and MINT5 TR 2008. N minus N_model records the "
            "COLA-rate vintage delta without adjusting any result."
        ),
        "source": "Registration 18 Adjustments",
    },
    {
        "key": "december_null",
        "description": (
            "C1 and M2 include the increase effective December 2030. "
            "The registered nulls stop at determination year 2029; "
            "no December null is registered or computed."
        ),
        "source": "Builder brief ruling 11",
    },
)


def _check_floor(inputs: legacy.TrackAInputs, config: ACOLAConfig) -> dict:
    """Require positive reduced increases through the December horizon."""

    minima = {}
    for row_id in config.rows:
        row = REGISTERED_ROWS[row_id]
        reform = sb.COLAReform(
            annual_reduction=config.annual_reduction,
            first_reduced_determination_year=(
                row.first_reduced_determination_year
            ),
        )
        minimum = sb.minimum_reformed_rate(
            inputs.baseline,
            reform,
            through_determination_year=config.reference_year,
        )
        if not minimum > 0:
            raise ValueError(
                f"{row_id}: reduced rate {minimum!r}; REFUSE requires "
                "the preflight's strictly positive floor through 2030"
            )
        minima[row_id] = minimum
    return minima


def spouse_worker_class(person_id: int, lookups: StateLookups) -> str:
    """Classify the living 2030 spouse link, including opening spouses."""

    state = lookups.final.loc[person_id]
    spouse = state.get("spouse_person_id")
    if pd.isna(spouse) or not lookups.alive(int(spouse)):
        return "unclassified"
    worker = lookups.final.loc[int(spouse)]
    entitled = worker.get("di_entitled", False)
    if not pd.isna(entitled) and bool(entitled):
        if pd.isna(worker.get("di_conversion_year")):
            return "entitled_unconverted_di_worker"
    return "another_worker"


def _shifted_summary(summary: dict, null: dict) -> dict:
    shifted = copy.deepcopy(summary)
    shifted["mean"] = (
        None if summary["mean"] is None else summary["mean"] - null["value"]
    )
    shifted["per_draw"] = [
        None if value is None else value - null["value"]
        for value in summary["per_draw"]
    ]
    shifted["null_value"] = null["value"]
    shifted["unit"] = "percentage points"
    return shifted


def _add_null_gaps(summary: dict, row: Any, nulls: dict) -> None:
    """Shift percent statistics only; levels and shares remain memo items."""

    if row.sub_row == "cost":
        summary["null_gaps"] = {
            "P_minus_N": _shifted_summary(
                summary["statistics"]["P"], nulls["N"]
            ),
            "P_minus_N_model": _shifted_summary(
                summary["statistics"]["P"], nulls["N_model"]
            ),
        }
    else:
        null_key = "N_M1" if row.row_id == "M1" else "N_MINT"
        summary["registered_null"] = null_key
        for band in summary["bands"].values():
            band["null_gaps"] = {
                statistic
                + "_minus_"
                + null_key: _shifted_summary(
                    band["statistics"][statistic], nulls[null_key]
                )
                for statistic in (
                    "ratio_of_scenario_means",
                    "median_individual_pct_change",
                    "difference_of_weighted_medians_pct",
                )
            }


def run_acola(
    inputs: legacy.TrackAInputs,
    *,
    config: ACOLAConfig | None = None,
    registration_pointer: str | None = None,
    progress: Callable[[str], None] | None = None,
    check_committed_parameters: bool = False,
    specification_path: Path = SPECIFICATION_PATH,
) -> dict[str, Any]:
    """Project each draw once, then publish every mechanism-L row."""

    config = config or ACOLAConfig()
    config.check_runnable()
    track_config = config.track_a_config()
    cohorts = legacy._population_cohorts(inputs, track_config)
    data_provenance = next(iter(cohorts.values())).data_provenance
    labels = tuple(next(iter(cohorts.values())).labels)
    real = data_provenance == REGISTERED_REAL
    if real:
        if registration_pointer != REGISTRATION_POINTER:
            raise ValueError(
                "a registered_real run needs Registration 18's pointer"
            )
        config.check_registered()
        departures = rulings_departures(track_config)
        if departures:
            raise ValueError(
                f"registered run departs from Track A rulings: {departures}"
            )
    specification = check_specification(specification_path)
    minima = _check_floor(inputs, config)
    consistency = legacy._parameter_consistency(
        inputs,
        track_config,
        cohorts,
        compare_committed_values=real or check_committed_parameters,
    )
    if (real or check_committed_parameters) and not consistency["consistent"]:
        failed = sorted(
            name
            for name, check in consistency["checks"].items()
            if not check["consistent"]
        )
        raise ValueError(
            f"registered parameters differ from committed inputs: {failed}"
        )
    legacy._check_source_provenance(cohorts, data_provenance)
    legacy._check_output_labels(labels, data_provenance)
    nulls = nulls_for_run(
        inputs.baseline, annual_reduction=config.annual_reduction
    )
    context_count = context_beneficiary_count()
    schedule = claiming_schedule(
        inputs.claiming_pmf, max_table_year=track_config.claim_table_max_year
    )
    fra_schedule = fra_schedule_from_parameters(inputs.params)
    records = {key: [] for key in config.rows}
    counters = {key: Counter() for key in config.rows}
    refusals: dict[str, list[dict]] = defaultdict(list)
    weights: dict[int, set[float]] = defaultdict(set)
    draws = {}
    for wave, cohort in cohorts.items():
        results, draws[str(wave)] = legacy._project_population(
            cohort,
            inputs,
            track_config,
            schedule=schedule,
            fra_schedule=fra_schedule,
            progress=progress,
        )
        if set(results) != set(config.draw_indices):
            raise ValueError("projection omitted a configured draw")
        context = BenefitContext(
            cohort, inputs.params, inputs.baseline, track_config
        )
        pia_cache: dict = {}
        for draw in config.draw_indices:
            result = results[draw]
            lookups = StateLookups(result, config.reference_year)
            for person in lookups.final.itertuples(index=False):
                weights[int(person.person_id)].add(float(person.weight))
            for row_id in config.rows:
                row = REGISTERED_ROWS[row_id]
                if progress is not None:
                    progress(
                        f"anchor wave {wave}, draw {draw}, row {row_id}: benefits"
                    )
                try:
                    emitted, row_counters = reference_benefit_rows(
                        result,
                        draw=draw,
                        row=row.track_row(),
                        context=context,
                        pia_cache=pia_cache,
                        lookups=lookups,
                    )
                except ValueError as error:
                    refusals[row_id].append(
                        {"draw": draw, "reason": str(error)}
                    )
                    continue
                for record in emitted:
                    record["spouse_worker_class"] = spouse_worker_class(
                        int(record["person_id"]), lookups
                    )
                records[row_id].extend(emitted)
                counters[row_id].update(row_counters)
    rows = {}
    output_labels = [*labels, "report-only"]
    for row_id in config.rows:
        row = REGISTERED_ROWS[row_id]
        options = {
            "draw_indices": config.draw_indices,
            "floor_seeds": config.floor_seeds,
            "certified_draw_indices": config.draw_indices,
            "refused_draws": {
                entry["draw"]: entry["reason"] for entry in refusals[row_id]
            },
        }
        if row.sub_row == "cost":
            summary = summarize_cost(records[row_id], **options)
        else:
            summary = summarize_mint(
                records[row_id],
                reference_year=config.reference_year,
                age_rule=row.age_rule,
                **options,
            )
        status = "refused" if refusals[row_id] else "computed"
        _add_null_gaps(summary, row, nulls)
        rows[row_id] = {
            "status": status,
            "labels": output_labels,
            "row": row.as_dict(),
            "benefit_counters": dict(sorted(counters[row_id].items())),
            "refusals": refusals[row_id],
            "membership_note": MEMBERSHIP_NOTE,
            **summary,
        }
    cost_cells = rows.get("C0", {}).get("per_draw", [])
    model_counts = [
        {
            "draw": cell["draw"],
            "weighted_count": cell.get("weight_base"),
            "undefined_reason": cell.get("undefined_reasons", {}).get(
                "weight_base"
            ),
        }
        for cell in cost_cells
    ]
    complete_counts = [cell["weighted_count"] for cell in model_counts]
    model_mean = (
        math.fsum(complete_counts) / len(complete_counts)
        if complete_counts
        and all(value is not None for value in complete_counts)
        else None
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "publishes_regardless": True,
        "comparator_seal_opened_before_commit": False,
        "data_provenance": data_provenance,
        "registration_pointer": registration_pointer,
        "labels": output_labels,
        "config": config.as_dict(),
        "specification": specification,
        "authorization": copy.deepcopy(AUTHORIZATION),
        "carried_track_a_rulings": max_rulings(track_config),
        "carried_track_a_builder_defaults": builder_defaults(track_config),
        "deferred_rows": copy.deepcopy(DEFERRED_ROWS),
        "reduced_rate_minimum_by_row": minima,
        "parameter_consistency": consistency,
        "cohorts": {
            str(wave): {
                **dict(cohort.diagnostics),
                "source_provenance": dict(cohort.source_provenance),
            }
            for wave, cohort in cohorts.items()
        },
        "scheduled_entrants": 0,
        "population_mortality": legacy._mortality_record(
            inputs.population_mortality
        ),
        "ssa_parameters_revision": inputs.params.pe_us_revision,
        "draws": draws,
        "rows": rows,
        "nulls": nulls,
        "context_beneficiary_count": {
            "context_only": True,
            "scaling_applied": False,
            "model_per_draw": model_counts,
            "model_mean": model_mean,
            "undefined_reason": (
                None if model_mean is not None else "C0 unavailable"
            ),
            "trustees": context_count,
        },
        "projection_weights": {
            "n_persons_weight_varies_across_draws": sum(
                len(values) > 1 for values in weights.values()
            ),
            "population": "all persons alive in at least one 2030 draw",
        },
        "gaps": copy.deepcopy(list(GAPS)),
        "inputs_provenance": dict(inputs.provenance),
    }
