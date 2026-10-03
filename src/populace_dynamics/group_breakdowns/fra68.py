"""Frozen exercise-3 replay for registered post hoc group breakdowns.

The orchestration follows ``fra68_track/runner.py:841-1175``. Every
projection, benefit, diagnostic and tabulation calculation is composed
from the frozen modules. There is no new implementation of any measure.
The retained state and benefit rows are inputs to G1/G2/G3 only after the
common module's reproduction check succeeds.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from populace_dynamics.cola_track_a import benefits as track_benefits
from populace_dynamics.cola_track_a import runner as track_runner
from populace_dynamics.cola_track_a.adapters import claiming_schedule
from populace_dynamics.cola_track_a.benefits import (
    BenefitContext,
    StateLookups,
)
from populace_dynamics.cola_track_a.config import (
    builder_defaults as track_a_builder_defaults,
)
from populace_dynamics.cola_track_a.config import (
    max_rulings as track_a_max_rulings,
)
from populace_dynamics.cola_track_a.runner import TrackAInputs
from populace_dynamics.engine.di_entitlement import (
    fra_schedule_from_parameters,
)
from populace_dynamics.estimates.cola_age_profile import (
    REGISTERED_REAL,
    ColaTabulationError,
    tabulate_cola_age_profile,
)
from populace_dynamics.fra68_track import runner as legacy
from populace_dynamics.fra68_track.benefits import (
    PersonScenario,
    union_benefit_rows,
)
from populace_dynamics.fra68_track.config import (
    E1_RULINGS,
    SPECIFICATION_ID,
    STATISTIC_ID,
    TRACK_A_ROW_BY_WAVE,
    FRA68Config,
    builder_defaults,
    max_rulings,
    row_labels,
)
from populace_dynamics.fra68_track.reform import SCHEDULES
from populace_dynamics.group_breakdowns.common import ProjectionReplay

__all__ = ["reproduce_fra68"]


def reproduce_fra68(
    inputs: TrackAInputs,
    *,
    config: FRA68Config | None = None,
    registration_pointer: str | None = None,
    progress: Callable[[str], None] | None = None,
    check_committed_parameters: bool = False,
    specification: Mapping[str, Any] | None = None,
    exercise_1_artifact: Path = legacy.EXERCISE_1_ARTIFACT_PATH,
) -> ProjectionReplay:
    """Replay frozen F0-F8 cells, retaining rows before attribute loading.

    Reuses the registered projection, scenario calculator, union builder,
    diagnostics and A7 tabulator without changing their implementations.
    ``result`` reproduces :func:`fra68_track.runner.run_fra68`; callers
    must verify every committed cell before deriving group attributes or
    calling the G3 group tabulator. This function neither loads attributes
    nor writes artifacts.
    """

    config = config or FRA68Config()
    config.check_runnable()
    track_config = config.track_a_config()
    cohorts = track_runner._population_cohorts(inputs, track_config)
    data_provenance = next(iter(cohorts.values())).data_provenance
    labels = tuple(next(iter(cohorts.values())).labels)
    real = data_provenance == REGISTERED_REAL
    if real and not registration_pointer:
        raise ValueError(
            "no real-data statistic before the issue #42 registration "
            "comment exists; pass its pointer to run a registered_real cohort"
        )
    block = (
        legacy.e1_parameter_block() if specification is None else specification
    )
    if real:
        legacy.check_specification_for_registered_run(block, config)
    spec_check = legacy.specification_code_check(block, config)
    consistency = track_runner._parameter_consistency(
        inputs,
        track_config,
        cohorts,
        compare_committed_values=real or check_committed_parameters,
    )
    if real and not consistency["consistent"]:
        failed = sorted(
            name
            for name, check in consistency["checks"].items()
            if not check["consistent"]
        )
        raise ValueError(
            "the inputs differ from the parameters the configuration "
            f"reports for this run: {failed}; a registered run refuses "
            "a mismatch"
        )
    track_runner._check_source_provenance(cohorts, data_provenance)
    track_runner._check_output_labels(labels, data_provenance)
    baseline_params = inputs.params
    base_scenario, reform_by_schedule, schedule_record = legacy._scenarios(
        config, baseline_params
    )
    birth_month = int(config.di_spec.assumed_birth_month)
    schedule = claiming_schedule(
        inputs.claiming_pmf, max_table_year=config.claim_table_max_year
    )
    fra_schedule = fra_schedule_from_parameters(baseline_params)
    rows_by_row: dict[str, list[dict]] = {row: [] for row in config.rows}
    counters_by_row: dict[str, Counter] = {
        row: Counter() for row in config.rows
    }
    states: dict[int, list[pd.DataFrame]] = {}
    draws: dict[str, Any] = {}
    di_window: dict[str, Any] = {}
    for wave, cohort in cohorts.items():
        results, draws[str(wave)] = track_runner._project_population(
            cohort,
            inputs,
            track_config,
            schedule=schedule,
            fra_schedule=fra_schedule,
            progress=progress,
        )
        states[wave] = []
        track_row = legacy.TRACK_A_ROWS[TRACK_A_ROW_BY_WAVE[wave]]
        wave_rows = config.rows_for_wave(wave)
        reform_keys = {
            config.row(row_id).reform_key: config.row(row_id)
            for row_id in wave_rows
        }
        pia_cache: dict = {}
        di_window[str(wave)] = {sid: {} for sid in config.schedule_ids}
        for draw, result in results.items():
            if progress is not None:
                progress(f"anchor wave {wave}, draw {draw}: benefits")
            lookups = StateLookups(result, config.reference_year)
            final = lookups.final.reset_index(drop=True).copy(deep=True)
            final["draw"] = int(draw)
            states[wave].append(final)
            shared = {
                "cohort": cohort,
                "inputs": inputs,
                "track_config": track_config,
                "track_row": track_row,
                "result": result,
                "lookups": lookups,
                "pia_cache": pia_cache,
                "assumed_birth_month": birth_month,
            }
            base_people, base_counters = legacy._compute_scenario(
                base_scenario, **shared
            )
            reform_people: dict[tuple, dict[int, PersonScenario]] = {}
            reform_counters: dict[tuple, Counter] = {}
            for key, sample_row in reform_keys.items():
                reform_people[key], reform_counters[key] = (
                    legacy._compute_scenario(
                        legacy._reform_scenario(
                            sample_row,
                            config,
                            baseline_params,
                            reform_by_schedule,
                        ),
                        **shared,
                    )
                )
            context = BenefitContext(
                cohort=cohort,
                params=baseline_params,
                baseline=inputs.baseline,
                config=track_config,
            )
            for row_id in wave_rows:
                row = config.row(row_id)
                rows, counters = union_benefit_rows(
                    base_people,
                    reform_people[row.reform_key],
                    draw=draw,
                    context=context,
                    lookups=lookups,
                    baseline_params=baseline_params,
                    reform_params=reform_by_schedule[row.schedule_id],
                )
                for item in rows:
                    item["age_reference"] = config.reference_year - int(
                        item["birth_year"]
                    )
                rows_by_row[row_id].extend(rows)
                counters_by_row[row_id].update(counters)
                counters_by_row[row_id].update(
                    {f"baseline_{k}": v for k, v in base_counters.items()}
                )
                counters_by_row[row_id].update(
                    {
                        f"reform_{k}": v
                        for k, v in reform_counters[row.reform_key].items()
                    }
                )
            for sid in config.schedule_ids:
                di_window[str(wave)][sid][str(draw)] = legacy._di_window(
                    result,
                    di_rates=inputs.di_rates,
                    baseline=baseline_params,
                    reform=reform_by_schedule[sid],
                    assumed_birth_month=birth_month,
                )
    # Membership first (E1 sections 7 and 12): every row's differences are
    # sorted from A7's own recipient flags, and a C0 difference no named
    # mechanism explains refuses the run before any row is tabulated.
    membership = {
        row_id: legacy._membership_differences(
            rows_by_row[row_id],
            config.row(row_id),
            config,
            baseline=baseline_params,
            reform=reform_by_schedule[config.row(row_id).schedule_id],
            assumed_birth_month=birth_month,
        )
        for row_id in config.rows
    }
    legacy._refuse_unexplained_c0_differences(membership)
    tabulations: dict[str, Any] = {}
    for row_id in config.rows:
        row = config.row(row_id)
        if progress is not None:
            progress(f"{row_id}: tabulating")
        output_labels = row_labels(row, labels)
        tabulation_config = legacy._tabulation_config(row, config)
        population = row.population
        upstream = {
            "specification": SPECIFICATION_ID,
            "row": row_id,
            "field_changed": row.field_changed,
            "schedule": row.schedule_id,
            "schedule_sha256": SCHEDULES[row.schedule_id].sha256(),
            "survivor_retirement_age": row.survivor_retirement_age.value,
            "claiming_response": row.claiming_response.value,
            "benefit_period": "calendar_2030_payments",
            "benefit_scale": "annual_12_times_monthly",
            "rate_path": (
                f"TR2008 {config.tr2008_alternative}, both scenarios"
            ),
            "behavior": row.behavior,
            "population_wave": population.anchor_wave,
            "population_weight": population.weight_variable,
            "population_start_year": population.start_year,
            "population_periods": population.periods(config.reference_year),
            "family_unit_id": population.family_unit_variable,
        }
        try:
            tabulation = tabulate_cola_age_profile(
                pd.DataFrame(rows_by_row[row_id]),
                data_provenance=data_provenance,
                config=tabulation_config,
                registration_pointer=registration_pointer,
                labels=output_labels,
                upstream_conventions=upstream,
                statistic_id=STATISTIC_ID,
                specification=block,
                pending_rulings=E1_RULINGS,
            )
        except ColaTabulationError as error:
            tabulation = None
            status = f"refused: {type(error).__name__}: {error}"
        else:
            # A7's own count must equal the classification's, which read
            # A7's flags: a difference would mean the two disagree.
            summary = tabulation["input_summary"]
            record = membership[row_id]["record"]
            if not record.get("classified") or (
                summary["n_rows_membership_differs"] != record["n_rows_differ"]
            ):
                raise ValueError(
                    f"{row_id}: A7 counts "
                    f"{summary['n_rows_membership_differs']} rows whose "
                    "membership differs, but the membership classification "
                    f"recorded {record.get('n_rows_differ')}"
                )
            undefined = tabulation["undefined_cells"]
            status = (
                "tabulated"
                if not undefined
                else "tabulated with undefined cells: "
                + ", ".join(
                    f"{cell['group']} {cell['statistic']} "
                    f"({cell['n_defined_draws']} of "
                    f"{len(config.draw_indices)} draws defined)"
                    for cell in undefined
                )
            )
        tabulations[row_id] = {
            "status": status,
            "row": row.as_dict(),
            "labels": list(output_labels),
            "membership_differences": membership[row_id]["record"],
            "benefit_counters": dict(sorted(counters_by_row[row_id].items())),
            "diagnostics": legacy._row_diagnostics(
                rows_by_row[row_id], row, config.draw_indices
            ),
            "component_shares_by_age_group": track_runner._component_shares(
                rows_by_row[row_id], row.components, config.draw_indices
            ),
            "tabulation": tabulation,
        }
    result = {
        "schema_version": legacy.SCHEMA_VERSION,
        "specification": SPECIFICATION_ID,
        "data_provenance": data_provenance,
        "registration_pointer": registration_pointer,
        "labels": list(labels),
        "config": config.as_dict(),
        "max_rulings": max_rulings(config),
        "builder_defaults": builder_defaults(config),
        "track_a_conventions": {
            "note": (
                "the shared projection and the benefit-level and auxiliary "
                "rules are Track A's; Max ruled these for exercise 1 (d074, "
                "d075) and ruled on 2026-09-24 that exercise 3 runs exactly "
                "like Track A (d188 item (a); d196 items (2) and (3) carry "
                "over the COLA horizon and the opening-stock basis)"
            ),
            "config": track_config.as_dict(),
            "benefit_computation_years": (
                track_benefits.TRACK_A_COMPUTATION_YEARS.value
            ),
            "max_rulings_exercise_1": track_a_max_rulings(track_config),
            "builder_defaults": track_a_builder_defaults(track_config),
        },
        "specification_check": spec_check,
        "age_factor_parameters": schedule_record,
        "cola_paths": legacy._cola_record(inputs.baseline),
        "parameter_consistency": consistency,
        "cohorts": {
            str(wave): {
                **dict(cohort.diagnostics),
                "source_provenance": dict(cohort.source_provenance),
            }
            for wave, cohort in cohorts.items()
        },
        "scheduled_entrants": 0,
        "population_mortality": track_runner._mortality_record(
            inputs.population_mortality
        ),
        "ssa_parameters_revision": baseline_params.pe_us_revision,
        "draws": draws,
        "projection_identity_with_exercise_1": legacy.projection_identity_record(
            draws,
            data_provenance=data_provenance,
            artifact_path=exercise_1_artifact,
        ),
        "di_window_diagnostic": {
            "definition": legacy._DI_WINDOW_DEFINITION,
            "incidence_at_start_ages": legacy._incidence_at(
                inputs.di_rates, (65, 66, 67)
            ),
            "by_wave_schedule_draw_year": di_window,
        },
        "rows": tabulations,
        "inputs_provenance": dict(inputs.provenance),
    }

    return ProjectionReplay(
        exercise="fra68",
        result=result,
        benefit_rows={
            row_id: pd.DataFrame(rows_by_row[row_id]) for row_id in config.rows
        },
        states={
            wave: pd.concat(frames, ignore_index=True)
            for wave, frames in states.items()
        },
    )
