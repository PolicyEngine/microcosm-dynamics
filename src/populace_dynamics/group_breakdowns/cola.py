"""Frozen exercise-1 replay for registered post hoc group breakdowns.

The orchestration follows ``cola_track_a/runner.py:953-1158`` and the
registered A1 specification, ``docs/design/urban2010_cola_comparison.md``.
All guards, projections, benefit calculations, diagnostics and five-age
cell tabulations call the frozen modules read-only. The additional return
values retain the final person state and benefit rows already produced by
the registered runner; no new mechanism or measure is implemented here.

Invariants: one projection per population and draw; every row reads its
population's shared path; the aggregate result equals the frozen runner;
no group attribute or group cell is computed before the caller's exact
reproduction check. Invented differential and property tests establish
these invariants without reading PSID or comparator outcomes.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping
from typing import Any

import pandas as pd

from populace_dynamics.cola_track_a import runner as legacy
from populace_dynamics.group_breakdowns.common import ProjectionReplay

__all__ = ["reproduce_cola"]


def reproduce_cola(
    inputs: legacy.TrackAInputs,
    *,
    config: legacy.TrackAConfig | None = None,
    registration_pointer: str | None = None,
    progress: Callable[[str], None] | None = None,
    check_committed_parameters: bool = False,
    specification: Mapping[str, Any] | None = None,
) -> ProjectionReplay:
    """Replay R0-R6 with frozen guards and retain person rows for G1/G2/G3.

    The result equals ``cola_track_a.runner.run_track_a`` on identical
    inputs. Populations share their projection across registered rows;
    scenario benefits share simulated paths. The caller must compare the
    reproduced result to its committed parent before computing any group
    attribute or cell. This function neither loads group attributes nor
    writes an artifact.
    """

    config = config or legacy.TrackAConfig()
    config.check_runnable()
    if specification is None:
        specification = legacy.a1_parameter_block()
    recorded_specification = legacy.specification_record(specification)
    cohorts = legacy._population_cohorts(inputs, config)
    data_provenance = next(iter(cohorts.values())).data_provenance
    labels = tuple(next(iter(cohorts.values())).labels)
    if data_provenance == legacy.REGISTERED_REAL and not registration_pointer:
        raise ValueError(
            "no real-data statistic before the issue #42 registration "
            "comment exists; pass its pointer to run a registered_real cohort"
        )
    real = data_provenance == legacy.REGISTERED_REAL
    departures = legacy.rulings_departures(config)
    if real and departures:
        raise ValueError(
            f"the configuration departs from Max's rulings on {departures} "
            "(2026-09-23, d074/d075); a registered run follows every ruling"
        )
    floor_minima = legacy._check_floor(inputs, config)
    consistency = legacy._parameter_consistency(
        inputs,
        config,
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
    legacy._check_source_provenance(cohorts, data_provenance)
    legacy._check_output_labels(labels, data_provenance)
    schedule = legacy.claiming_schedule(
        inputs.claiming_pmf, max_table_year=config.claim_table_max_year
    )
    fra_schedule = legacy.fra_schedule_from_parameters(inputs.params)
    rows_by_row: dict[str, list[dict]] = {row: [] for row in config.rows}
    counters_by_row: dict[str, Counter] = {
        row: Counter() for row in config.rows
    }
    draws: dict[str, Any] = {}
    states_by_wave: dict[int, list[pd.DataFrame]] = {
        wave: [] for wave in cohorts
    }
    for wave, cohort in cohorts.items():
        results, draws[str(wave)] = legacy._project_population(
            cohort,
            inputs,
            config,
            schedule=schedule,
            fra_schedule=fra_schedule,
            progress=progress,
        )
        context = legacy.BenefitContext(
            cohort=cohort,
            params=inputs.params,
            baseline=inputs.baseline,
            config=config,
        )
        pia_cache: dict = {}
        for draw, result in results.items():
            states_by_wave[wave].append(
                result.slices[-1].copy().assign(draw=draw)
            )
            lookups = legacy.StateLookups(result, config.reference_year)
            for row_id in config.rows_for_wave(wave):
                rows, counters = legacy.reference_benefit_rows(
                    result,
                    draw=draw,
                    row=legacy.REGISTERED_ROWS[row_id],
                    context=context,
                    pia_cache=pia_cache,
                    lookups=lookups,
                )
                for row in rows:
                    row["age_reference"] = config.reference_year - int(
                        row["birth_year"]
                    )
                rows_by_row[row_id].extend(rows)
                counters_by_row[row_id].update(counters)
    tabulations: dict[str, Any] = {}
    for row_id in config.rows:
        row = legacy.REGISTERED_ROWS[row_id]
        if progress is not None:
            progress(f"{row_id}: tabulating")
        tabulation_config = legacy.ColaAgeProfileConfig(
            reference_year=config.reference_year,
            components=row.components,
            benefit_period=row.tabulation_benefit_period,
            headline_statistic=row.headline_statistic,
            draw_indices=config.draw_indices,
            floor_seeds=config.floor_seeds,
        )
        population = row.population
        upstream = {
            "row": row_id,
            "field_changed": row.field_changed,
            "first_reduced_determination_year": (
                row.first_reduced_determination_year
            ),
            "exposure_clock": row.exposure_clock.value,
            "benefit_period": row.benefit_period.value,
            "benefit_scale": "annual_12_times_monthly",
            "rate_path": f"TR2008 {config.tr2008_alternative}",
            "behavior": "fixed_paths_shared_draws",
            "population_wave": population.anchor_wave,
            "population_weight": population.weight_variable,
            "population_start_year": population.start_year,
            "population_periods": population.periods(config.reference_year),
            "family_unit_id": population.family_unit_variable,
        }
        try:
            tabulation = legacy.tabulate_cola_age_profile(
                pd.DataFrame(rows_by_row[row_id]),
                data_provenance=data_provenance,
                config=tabulation_config,
                registration_pointer=registration_pointer,
                labels=labels,
                upstream_conventions=upstream,
                specification=specification,
            )
        except legacy.ColaTabulationError as error:
            tabulation = None
            status = f"refused: {type(error).__name__}: {error}"
        else:
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
            "benefit_counters": dict(sorted(counters_by_row[row_id].items())),
            "reduced_increases_definition": legacy._REDUCED_INCREASE_DEFINITION,
            "reduced_increases_by_age_group": legacy._reduced_increase_summary(
                rows_by_row[row_id], row.components
            ),
            "component_shares_by_age_group": legacy._component_shares(
                rows_by_row[row_id], row.components, config.draw_indices
            ),
            "tabulation": tabulation,
        }
    artifact = {
        "schema_version": legacy.SCHEMA_VERSION,
        "data_provenance": data_provenance,
        "registration_pointer": registration_pointer,
        "labels": list(labels),
        "config": config.as_dict(),
        "specification": recorded_specification,
        "max_rulings": legacy.max_rulings(config),
        "builder_defaults": legacy.builder_defaults(config),
        "rows_not_built": dict(legacy.ROWS_NOT_BUILT),
        "reduced_rate_minimum_by_row": floor_minima,
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
        # The oracle's statutory parameter revision; the committed-value
        # checks (parameter_consistency, when run) bind the values.
        "ssa_parameters_revision": inputs.params.pe_us_revision,
        "draws": draws,
        "rows": tabulations,
        "inputs_provenance": dict(inputs.provenance),
    }
    return ProjectionReplay(
        exercise="cola",
        result=artifact,
        benefit_rows={
            row: pd.DataFrame(values) for row, values in rows_by_row.items()
        },
        states={
            wave: pd.concat(values, ignore_index=True)
            for wave, values in states_by_wave.items()
        },
    )
