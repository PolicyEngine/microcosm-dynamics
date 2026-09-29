"""One projection ensemble and the ordered joint attempt (§§3, 10).

The inherited projector is cola_track_a/runner.py:893–950. Its callers
build baseline claiming/FRA schedules at :1019–1022. FRA scenarios retain
fra68_track/runner.py:420–472. No v1 runner or engine module is modified.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.cola_track_a import runner as legacy
from populace_dynamics.cola_track_a.adapters import claiming_schedule
from populace_dynamics.cola_track_a.benefits import (
    BenefitContext,
    StateLookups,
)
from populace_dynamics.cola_track_a.config import REGISTERED_ROWS, TrackAConfig
from populace_dynamics.engine.di_entitlement import (
    fra_schedule_from_parameters,
)
from populace_dynamics.fra68_track import runner as fra_runner
from populace_dynamics.fra68_track.benefits import union_benefit_rows
from populace_dynamics.fra68_track.config import FRA68Config

from . import INVENTED_HEADER, SPECIFICATION_VERSION


@dataclass(frozen=True)
class JointConfig:
    """The fixed design; fewer invented draws are a test-only convenience."""

    draw_indices: tuple[int, ...] = tuple(range(20))
    floor_seeds: tuple[int, ...] = (0, 1, 2, 3, 4)
    reference_year: int = 2030

    def track_a(self):
        return TrackAConfig(
            rows=tuple(f"R{i}" for i in range(6)),
            draw_indices=self.draw_indices,
            floor_seeds=self.floor_seeds,
        )

    def fra(self):
        return FRA68Config(
            rows=tuple(f"F{i}" for i in range(8)),
            draw_indices=self.draw_indices,
            floor_seeds=self.floor_seeds,
        )


def _canonical(value):
    if isinstance(value, np.generic):
        value = value.item()
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, float):
        return {"float": value.hex()} if not math.isnan(value) else None
    if isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _canonical(item) for key, item in value.items()}
    # §3.2 is silent about extension-valued columns: refuse serialization
    # rather than hash a lossy repr that could hide a changed state.
    raise ValueError(f"unsupported projection scalar {type(value).__name__}")


def projection_hash(result) -> str:
    """Hash every slice, schema, index and exact scalar without mutating it."""
    payload = [
        {
            "columns": _canonical(list(frame.columns)),
            "dtypes": [str(dtype) for dtype in frame.dtypes],
            "index": _canonical(list(frame.index)),
            "values": _canonical(frame.to_numpy(dtype=object).tolist()),
        }
        for frame in result.slices
    ]
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _paired_scenarios(base, reform, *, draw, context, lookups, params):
    """Keep the inherited diagnostics and add all double-zero persons (§7)."""
    if set(base) != set(reform) or set(base) != set(lookups.final.index):
        raise ValueError("the two scenarios cover different persons")
    rows, counters = union_benefit_rows(
        base,
        reform,
        draw=draw,
        context=context,
        lookups=lookups,
        baseline_params=context.params,
        reform_params=params,
    )
    present = {item["person_id"] for item in rows}
    for pid in sorted(set(base) - present):
        state = lookups.final.loc[pid]
        names = sorted(set(base[pid].components) | set(reform[pid].components))
        rows.append(
            {
                "draw": draw,
                "person_id": pid,
                "family_unit_id": int(
                    context.cohort.persons_by_id.loc[pid, "family_unit_id"]
                ),
                "weight": float(state["weight"]),
                "birth_year": int(state["birth_year"]),
                "beneficiary_base": False,
                "beneficiary_reform": False,
                "benefit_base": 0.0,
                "benefit_reform": 0.0,
                "benefit_components": {
                    name: {"base": 0.0, "reform": 0.0} for name in names
                },
                "basis": base[pid].basis,
                "own_kind_base": base[pid].own_kind,
                "own_kind_reform": reform[pid].own_kind,
            }
        )
    for item in rows:
        item["age_reference"] = 2030 - item["birth_year"]
    return sorted(rows, key=lambda item: item["person_id"]), counters


def _before_projection(inputs, config, registration, pointer):
    if inputs.cohort.anchor_wave != 2011 or inputs.additional_cohorts:
        raise ValueError("§3 requires only the 2011-wave population")
    real = inputs.cohort.data_provenance == "registered_real"
    if real:
        from .protocol import PreflightRecord

        if not isinstance(registration, PreflightRecord):
            raise ValueError("registered data requires validated preflight")
        if registration.mode != "registered" or not pointer:
            raise ValueError("registered outcome protocol is required")
        if registration.registration_pointer != pointer:
            raise ValueError("registration pointer differs from preflight")
        if config != JointConfig():
            raise ValueError("the registered 20-draw protocol is frozen")
        registration.validate_inputs(inputs)
    elif inputs.cohort.data_provenance != "invented":
        raise ValueError("unknown input provenance")
    cohorts = {2011: inputs.cohort}
    legacy._check_source_provenance(cohorts, inputs.cohort.data_provenance)
    legacy._check_output_labels(
        inputs.cohort.labels, inputs.cohort.data_provenance
    )
    config.track_a().check_runnable()
    config.fra().check_runnable()
    legacy._check_floor(inputs, config.track_a())
    if real:
        consistency = legacy._parameter_consistency(
            inputs, config.track_a(), cohorts, compare_committed_values=True
        )
        if not consistency["consistent"]:
            raise ValueError("registered inputs differ from frozen parameters")


def run_joint(
    inputs,
    *,
    registration_pointer=None,
    draw_indices=tuple(range(20)),
    registration=None,
    progress=None,
) -> dict[str, Any]:
    """Execute §§10's six stages; every refusal retains all uncomputed rows."""
    from .benefits import collect_reference_benefit_rows, scenario_benefits
    from .estimands import tabulate_rows, validate_worker_floor_pair
    from .histories import HistoryValidator
    from .matrix import MATRIX, MECHANISMS
    from .membership import guard_membership

    config = JointConfig(draw_indices=tuple(draw_indices))
    labels = [
        "registered, one-shot, post hoc, not blind",
        "PSID-seeded closed cohort",
        "Python oracle (not Axiom)",
    ]
    keys = [f"{row.mechanism}×{row.row_id}" for row in MATRIX]
    attempt = {
        "status": "started",
        "step": 0,
        "refusal": None,
        "first_failing_person_draw": None,
        "uncomputed_rows": list(keys),
        "counters": {},
    }
    artifact = {
        "header": (
            INVENTED_HEADER
            if inputs.cohort.data_provenance == "invented"
            else labels[0]
        ),
        "labels": labels,
        "specification": SPECIFICATION_VERSION,
        "headlines": ["D×R0", "D×F0"],
        "historical_only": {
            "R6": "not rerun: requires a second population",
            "F8": "not rerun: requires a second population",
        },
        "attempt": attempt,
        "rows": {},
        "draw_indices": list(config.draw_indices),
        "root_entropies": [5200 + k for k in config.draw_indices],
    }
    person_draw = {"person_id": None, "draw": None}
    counters = Counter()
    row_counters = {key: Counter() for key in keys}
    membership = {}
    artifact["membership"] = membership
    artifact["benefit_counters"] = row_counters

    def stage(number):
        attempt["step"] = number
        if progress is not None:
            progress(f"joint stage {number}/6")

    try:
        _before_projection(inputs, config, registration, registration_pointer)
        stage(1)
        results, diagnostics = legacy._project_population(
            inputs.cohort,
            inputs,
            config.track_a(),
            schedule=claiming_schedule(
                inputs.claiming_pmf, max_table_year=2008
            ),
            fra_schedule=fra_schedule_from_parameters(inputs.params),
            progress=progress,
        )
        hashes = {
            str(draw): projection_hash(result)
            for draw, result in results.items()
        }
        artifact["projection_hashes_before"] = hashes
        artifact["projection_diagnostics"] = diagnostics
        artifact["projection_identity_record"] = (
            fra_runner.projection_identity_record(
                {"2011": diagnostics},
                data_provenance=inputs.cohort.data_provenance,
            )
        )
        stage(2)
        validators = {}
        for draw, result in results.items():
            person_draw["draw"] = draw
            validators[draw] = HistoryValidator(result, inputs.cohort)
            counters.update(validators[draw].validate_requested())

        stage(3)
        prepared = {key: [] for key in keys}
        base_scenario, reform_params, scenario_record = fra_runner._scenarios(
            config.fra(), inputs.params
        )
        artifact["scenarios"] = scenario_record
        context = BenefitContext(
            inputs.cohort, inputs.params, inputs.baseline, config.track_a()
        )
        cache = {}
        first_mutation_draw = None
        artifact["projection_hashes_after_mechanism"] = {}
        for mechanism in MECHANISMS:
            for draw, result in results.items():
                if progress is not None:
                    progress(f"{mechanism}, draw {draw}: building benefits")
                person_draw["draw"] = draw
                lookups = StateLookups(result, 2030)
                shared = {
                    "mechanism": mechanism,
                    "history_validator": validators[draw],
                    "pia_cache": cache,
                    "lookups": lookups,
                }
                for row in MATRIX:
                    if (
                        row.mechanism != mechanism
                        or not row.row_id.startswith("R")
                    ):
                        continue
                    key = f"{mechanism}×{row.row_id}"
                    raw, count = collect_reference_benefit_rows(
                        result,
                        draw=draw,
                        row=REGISTERED_ROWS[row.row_id],
                        context=context,
                        **shared,
                    )
                    row_counters[key].update(count)
                    counters.update(count)
                    guard_membership(
                        raw,
                        row,
                        baseline_params=inputs.params,
                        reform_params=inputs.params,
                    )
                    # §9 guards see all persons before the inherited filter.
                    prepared[key].extend(
                        item for item in raw if item["benefit_base"] > 0
                    )
                base_people, base_counts = scenario_benefits(
                    result,
                    context=context,
                    track_row=REGISTERED_ROWS["R0"],
                    scenario=base_scenario,
                    assumed_birth_month=7,
                    **shared,
                )
                counters.update(base_counts)
                by_reform = {}
                for row in MATRIX:
                    if row.mechanism != mechanism or row.row_id.startswith(
                        "R"
                    ):
                        continue
                    source = row.source_row
                    scenario = fra_runner._reform_scenario(
                        source, config.fra(), inputs.params, reform_params
                    )
                    if source.reform_key not in by_reform:
                        scenario_context = BenefitContext(
                            inputs.cohort,
                            scenario.params,
                            inputs.baseline,
                            config.track_a(),
                        )
                        by_reform[source.reform_key] = scenario_benefits(
                            result,
                            context=scenario_context,
                            track_row=REGISTERED_ROWS["R0"],
                            scenario=scenario,
                            assumed_birth_month=7,
                            **shared,
                        )
                    people, count = by_reform[source.reform_key]
                    raw, pair_counts = _paired_scenarios(
                        base_people,
                        people,
                        draw=draw,
                        context=context,
                        lookups=lookups,
                        params=scenario.params,
                    )
                    key = f"{mechanism}×{row.row_id}"
                    # §7 retains E1's recipient-union inputs for F, including
                    # its family-split universe. U additionally retains every
                    # alive double-zero person for population denominators.
                    prepared[key].extend(
                        item
                        for item in raw
                        if row.row_id.startswith("U")
                        or item["benefit_base"] > 0
                        or item["benefit_reform"] > 0
                    )
                    row_counters[key].update(pair_counts)
                    counters.update(pair_counts)
                    row_counters[key].update(
                        {f"baseline_{k}": v for k, v in base_counts.items()}
                    )
                    row_counters[key].update(
                        {f"reform_{k}": v for k, v in count.items()}
                    )
                    counters.update(count)
            # §3.2 requires each post-mechanism snapshot; §10 requires every
            # step-3 benefit refusal to precede the step-4 mutation refusal.
            # Remember the first mismatch even if a later mechanism restores
            # the slices, rather than losing that intermediate violation.
            snapshot = {
                str(draw): projection_hash(result)
                for draw, result in results.items()
            }
            artifact["projection_hashes_after_mechanism"][mechanism] = snapshot
            for draw in results:
                if (
                    first_mutation_draw is None
                    and snapshot[str(draw)] != hashes[str(draw)]
                ):
                    first_mutation_draw = draw
        stage(4)
        artifact["projection_hashes_after"] = {
            str(draw): projection_hash(result)
            for draw, result in results.items()
        }
        if first_mutation_draw is not None:
            person_draw["draw"] = first_mutation_draw
            # §10 is silent on attributing whole-slice hash mismatches.
            # Keep person_id null rather than inventing an affected person.
            raise ValueError("projection slices changed during benefits")
        if artifact["projection_hashes_after"] != hashes:
            raise ValueError("projection slices changed during benefits")
        stage(5)
        floor_inputs = {}
        for row in MATRIX:
            key = f"{row.mechanism}×{row.row_id}"
            params = (
                inputs.params
                if row.row_id.startswith("R")
                else reform_params[row.source_row.schedule_id]
            )
            membership[key] = guard_membership(
                prepared[key],
                row,
                baseline_params=inputs.params,
                reform_params=params,
            )
            # §§9/12.9 fix worker-only S=L and DS=D, including floors.
            # Validate paired inputs at step 5, before any tabulation (§10).
            if row.mechanism in ("S", "DS") and row.row_id in ("R5", "F6"):
                reference = "L" if row.mechanism == "S" else "D"
                floor_inputs[key] = prepared[f"{reference}×{row.row_id}"]
                validate_worker_floor_pair(
                    prepared[key],
                    floor_inputs[key],
                    row,
                    draw_indices=config.draw_indices,
                )
        artifact["membership"] = membership
        artifact["benefit_counters"] = {
            key: dict(value) for key, value in row_counters.items()
        }
        stage(6)
        for row in MATRIX:
            key = f"{row.mechanism}×{row.row_id}"
            artifact["rows"][key] = tabulate_rows(
                prepared[key],
                row,
                draw_indices=config.draw_indices,
                floor_seeds=config.floor_seeds,
                floor_records=floor_inputs.get(key),
            )
            attempt["uncomputed_rows"].remove(key)
        attempt["status"] = "completed"
    except (Exception, KeyboardInterrupt) as error:
        # §10 reports infrastructure failures and interrupted attempts too;
        # preserve progress instead of letting an outer script lose counters.
        attempt["status"] = "refused"
        attempt["refusal"] = {
            "type": type(error).__name__,
            "reason": str(error),
        }
        attempt["first_failing_person_draw"] = {
            "person_id": getattr(error, "person_id", person_draw["person_id"]),
            "draw": getattr(error, "draw", person_draw["draw"]),
        }
        failure_counters = getattr(error, "counters", {})
        artifact["failure_counters"] = failure_counters
        if hasattr(error, "row"):
            membership[error.row] = failure_counters
        counters.update(
            {
                key: value
                for key, value in failure_counters.items()
                if isinstance(value, int)
            }
        )
    attempt["counters"] = dict(counters)
    return artifact
