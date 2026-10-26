"""Measure full-horizon OP1 resource use on invented rosters (design §8).

Run ``python docs/design/open_population_evidence/op1_run_size.py --sizes 25
100 --output docs/design/open_population_evidence/op1_run_size.json`` from the
repository root. Each size and emigration stream implementation runs in a
fresh worker, sequentially. The sealed loop always uses its own registry.
Only the exit adapter's stream-class binding changes for the comparison.

Mortality draws person streams (``engine/steps.py:125–131``); fertility draws
tagged person streams (``baselines/fertility.py:114–126``). Aging draws none
(``engine/steps.py:142–148``). Nonzero emigration requires the harness's
no-marital-transition adapter (``open_population/exits.py:64–67``), so a
different marital adapter cannot be included in this measurement.

The cProfile wrappers measure registry ``seed_sequence`` cumulative time:
root/period/module spawning (``engine/rng.py:61–77``), excluding the additional
leaf and generator construction (``:94–100``, ``:149–156``). This is a lower
bound on all sealed RNG setup cost. Four disjoint sealed-generator wrappers
also report complete setup, including leaves and generator construction.
They wrap module, child, tagged and tagged-child methods; ``person_generator``
delegates to the child method (``engine/rng.py:158–170``) and is not added.
The direct wrapper measures ``_sequence`` construction. Complete emigration
tagged-generator setup is also reported.
The sealed-loop and emigration profiler groups do not overlap. Profile time
excludes imports and fixture construction. Peak RSS includes imports and the
maximum live projection/accounting state. Full size remains due before OP10a.
"""

from __future__ import annotations

import argparse
import cProfile
import hashlib
import json
import os
import platform
import pstats
import statistics
import subprocess
import sys
import time
from pathlib import Path

START_YEAR = 2025
REGISTERED_HORIZON = 2100
EMIGRATION_PROBABILITY = 0.02


def _positive_int(value: str) -> int:
    """Parse a positive measurement size or timeout (design §8)."""
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be a positive integer")
    return parsed


def _profile_summary(profile: cProfile.Profile) -> dict:
    """Report costs without adding overlapping calls (design §8)."""
    stats = pstats.Stats(profile)
    out = {"total_seconds": stats.total_tt}
    for name in (
        "sealed_registry_sequences",
        "sealed_module_generator_setup",
        "sealed_person_generator_setup",
        "sealed_tagged_generator_setup",
        "sealed_tagged_child_generator_setup",
        "emigration_registry_sequences",
        "emigration_direct_sequences",
        "emigration_generator_setup",
    ):
        matches = [v for k, v in stats.stats.items() if k[2] == name]
        seconds = sum(v[3] for v in matches)
        out[name] = {
            "calls": sum(v[1] for v in matches),
            "cumulative_seconds": seconds,
            "share_of_profile_total": seconds / stats.total_tt,
        }
    setup_names = (
        "sealed_module_generator_setup",
        "sealed_person_generator_setup",
        "sealed_tagged_generator_setup",
        "sealed_tagged_child_generator_setup",
    )
    setup_seconds = sum(
        out[name]["cumulative_seconds"] for name in setup_names
    )
    out["sealed_generator_setup_total"] = {
        "calls": sum(out[name]["calls"] for name in setup_names),
        "cumulative_seconds": setup_seconds,
        "share_of_profile_total": setup_seconds / stats.total_tt,
    }
    out["top_self_costs"] = [
        {
            "function": f"{Path(filename).name}:{line}:{name}",
            "calls": value[1],
            "self_seconds": value[2],
            "cumulative_seconds": value[3],
        }
        for (filename, line, name), value in sorted(
            stats.stats.items(), key=lambda item: item[1][2], reverse=True
        )[:12]
    ]
    return out


def _measure(size: int, stream_mode: str) -> dict:
    """Profile one invented 75-year production run (design §§2.9, 8)."""
    started = time.perf_counter()
    load_start = os.getloadavg()
    import resource
    from collections import Counter
    from unittest.mock import patch

    import numpy as np
    import pandas as pd

    from populace_dynamics.baselines.fertility import AsfrFertilityStep
    from populace_dynamics.engine.entrant_schedule import (
        build_entrant_schedule,
    )
    from populace_dynamics.engine.loop import PeriodModules
    from populace_dynamics.engine.rng import ProjectionRNGRegistry
    from populace_dynamics.engine.steps import (
        AgeSexMortalityModel,
        advance_age,
        apply_mortality,
    )
    from populace_dynamics.open_population import exits, harness
    from populace_dynamics.open_population.exits import no_marital_transitions
    from populace_dynamics.open_population.harness import ProductionRequest
    from populace_dynamics.open_population.streams import DirectRNGStreams

    indices = np.arange(size)
    initial = pd.DataFrame(
        {
            "person_id": indices + 1,
            "year": START_YEAR,
            "age": 18 + indices % 22,
            "sex": np.where(indices % 2 == 0, "female", "male"),
            "weight": 1.0,
            "start_weight": 1.0,
        }
    )
    cohort_rows = max(1, size // 25)
    donor_indices = np.arange(cohort_rows)
    donor = pd.DataFrame(
        {
            "person_id": donor_indices + 1,
            "weight": 1.0,
            "entry_age": 25 + donor_indices % 15,
            "is_female": donor_indices % 2 == 0,
            "source_year": 2024,
            "peinusyr": 1,
            "prcitshp": 4,
            "penatvty": 100,
            "foreign_born": True,
        }
    )

    def build_schedule(allocator):
        return build_entrant_schedule(
            donor,
            {
                year: cohort_rows / 1000
                for year in range(START_YEAR + 1, REGISTERED_HORIZON + 1)
            },
            allocator=allocator,
            roster_columns=list(initial.columns),
        )

    def unchanged(frame, context, rng):
        return frame

    def no_composition(frame, context, marital, rng):
        return frame

    # Invented computational loads, not estimated demographic laws.
    model = AgeSexMortalityModel(
        bands=((0, 74), (75, 120)),
        probability={
            (band, sex): probability
            for band, probability in (("0-74", 0.01), ("75+", 0.10))
            for sex in ("female", "male")
        },
    )
    draw_counts = {"mortality": 0, "emigration": 0}

    def mortality(frame, context, rng):
        draw_counts["mortality"] += len(frame)
        return apply_mortality(frame, context, rng, model=model)

    def emigration(frame, context):
        draw_counts["emigration"] += len(frame)
        return np.full(len(frame), EMIGRATION_PROBABILITY)

    modules = PeriodModules(
        mortality=mortality,
        aging=advance_age,
        marital_core=no_marital_transitions,
        fertility=AsfrFertilityStep(
            asfr=lambda year: {age: 0.06 for age in range(18, 41)}
        ),
        disability=unchanged,
        earnings=unchanged,
        claiming=unchanged,
        household_composition=no_composition,
    )
    registry_sequence = ProjectionRNGRegistry.seed_sequence
    module_generator = ProjectionRNGRegistry.generator
    child_generator = ProjectionRNGRegistry.child_generator
    tagged_generator = ProjectionRNGRegistry.tagged_generator
    tagged_child_generator = ProjectionRNGRegistry.tagged_child_generator
    history_reconciler = harness.reconcile_history
    memory = {}

    def sealed_registry_sequences(self, period, module):
        return registry_sequence(self, period, module)

    def sealed_module_generator_setup(self, *args):
        return module_generator(self, *args)

    def sealed_person_generator_setup(self, *args):
        return child_generator(self, *args)

    def sealed_tagged_generator_setup(self, *args):
        return tagged_generator(self, *args)

    def sealed_tagged_child_generator_setup(self, *args):
        return tagged_child_generator(self, *args)

    class ProfiledRegistry(ProjectionRNGRegistry):
        def emigration_registry_sequences(self, period, module):
            return registry_sequence(self, period, module)

        seed_sequence = emigration_registry_sequences

        def emigration_generator_setup(self, *args):
            return tagged_child_generator(self, *args)

        tagged_child_generator = emigration_generator_setup

    class ProfiledDirect(DirectRNGStreams):
        def emigration_direct_sequences(self, period, module, *tail):
            return super()._sequence(period, module, *tail)

        _sequence = emigration_direct_sequences

        def emigration_generator_setup(self, *args):
            return super().tagged_child_generator(*args)

        tagged_child_generator = emigration_generator_setup

    def capture_snapshots(transitions, **kwargs):
        snapshots = [
            frame
            for transition in transitions
            for frame in (transition.opening, transition.closing)
        ]
        unique = {id(frame): frame for frame in snapshots}
        memory["annual_snapshot_columns"] = sorted(
            {tuple(frame.columns) for frame in snapshots}
        )
        memory["unique_annual_snapshot_bytes"] = sum(
            int(frame.memory_usage(index=True, deep=True).sum())
            for frame in unique.values()
        )
        memory["annual_snapshot_references"] = len(snapshots)
        memory["unique_annual_snapshots"] = len(unique)
        return history_reconciler(transitions, **kwargs)

    profile = cProfile.Profile()
    projection_load_start = os.getloadavg()
    projection_started = time.perf_counter()
    cls = ProfiledDirect if stream_mode == "direct" else ProfiledRegistry
    with (
        patch.object(
            ProjectionRNGRegistry, "seed_sequence", sealed_registry_sequences
        ),
        patch.object(
            ProjectionRNGRegistry, "generator", sealed_module_generator_setup
        ),
        patch.object(
            ProjectionRNGRegistry,
            "child_generator",
            sealed_person_generator_setup,
        ),
        patch.object(
            ProjectionRNGRegistry,
            "tagged_generator",
            sealed_tagged_generator_setup,
        ),
        patch.object(
            ProjectionRNGRegistry,
            "tagged_child_generator",
            sealed_tagged_child_generator_setup,
        ),
        patch.object(exits, "DirectRNGStreams", cls),
        patch.object(harness, "reconcile_history", capture_snapshots),
    ):
        profile.enable()
        result = harness.run_production(
            initial,
            modules,
            ProductionRequest(scenario="tr2026_intermediate", draw_index=0),
            schedule_builder=build_schedule,
            reserved_real_ids=initial["person_id"],
            emigration_hazard=emigration,
        )
        profile.disable()
    projection_seconds = time.perf_counter() - projection_started
    projection_load_end = os.getloadavg()
    events = Counter(event.kind.value for event in result.events)
    periods = result.accounting.periods
    slices = result.projection.slices
    slice_bytes = [
        int(frame.memory_usage(index=True, deep=True).sum())
        for frame in slices
    ]
    digest = hashlib.sha256()
    for frame in slices:
        digest.update(pd.util.hash_pandas_object(frame, index=False).values)
    system = platform.system()
    if system not in {"Darwin", "Linux"}:
        raise RuntimeError("peak RSS units are defined for macOS and Linux")
    peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    summary = {
        "status": "completed",
        "emigration_stream": stream_mode,
        "emigration_probability": EMIGRATION_PROBABILITY,
        "initial_people": size,
        "final_people": len(slices[-1]),
        "maximum_live_people": max(len(frame) for frame in slices),
        "retained_person_year_rows": sum(len(frame) for frame in slices),
        "mortality_person_years": draw_counts["mortality"],
        "emigration_survivor_person_years": draw_counts["emigration"],
        "births": events["birth"],
        "scheduled_entries": events["scheduled_entry"],
        "deaths": events["death"],
        "emigrations": events["emigration"],
        "annual_cohort_rows": cohort_rows,
        "accounted_periods": len(periods),
        "all_count_residuals_zero": all(
            period.count_residual == 0 for period in periods
        ),
        "all_revaluations_zero": all(
            period.weights.revaluation.total == 0 for period in periods
        ),
        "maximum_absolute_weight_residual": max(
            abs(period.weight_residual) for period in periods
        ),
        "projection_sha256": digest.hexdigest(),
        "projection_wall_time_seconds": projection_seconds,
        "seconds_per_mortality_person_year": projection_seconds
        / draw_counts["mortality"],
        "peak_memory_bytes": int(
            peak_rss * (1 if system == "Darwin" else 1024)
        ),
        "retained_slice_bytes": sum(slice_bytes),
        "shared_full_column_snapshot_counterfactual_bytes": sum(slice_bytes),
        "original_full_column_snapshot_counterfactual_bytes": (
            sum(slice_bytes[:-1]) + sum(slice_bytes[1:])
        ),
        "load_at_worker_start": load_start,
        "load_at_projection_start": projection_load_start,
        "load_at_projection_end": projection_load_end,
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "platform": platform.platform(),
        "profile": _profile_summary(profile),
        **memory,
    }
    summary["wall_time_seconds"] = time.perf_counter() - started
    return summary


def _microbenchmark() -> dict:
    """Interleave tagged-child draws at short and long horizons (§8)."""
    from populace_dynamics.engine.rng import (
        ProjectionModule,
        ProjectionRNGRegistry,
    )
    from populace_dynamics.open_population.exits import EMIGRATION_STREAM_TAG
    from populace_dynamics.open_population.streams import DirectRNGStreams

    samples = {
        f"{mode}_{horizon}": []
        for mode in ("registry", "direct")
        for horizon in (7, 75)
    }
    load_start = os.getloadavg()
    draws = 400
    for repetition in range(5):
        horizons = (7, 75) if repetition % 2 == 0 else (75, 7)
        modes = (
            ("registry", "direct")
            if repetition % 2 == 0
            else ("direct", "registry")
        )
        for horizon in horizons:
            for mode in modes:
                cls = (
                    ProjectionRNGRegistry
                    if mode == "registry"
                    else DirectRNGStreams
                )
                registry = cls(draw_index=0, n_periods=horizon)
                started = time.perf_counter()
                for ordinal in range(draws):
                    registry.tagged_child_generator(
                        horizon // 2,
                        ProjectionModule.MORTALITY,
                        EMIGRATION_STREAM_TAG,
                        ordinal,
                    ).random()
                samples[f"{mode}_{horizon}"].append(
                    (time.perf_counter() - started) / draws * 1e6
                )
    return {
        "method": "five interleaved repetitions; one tagged_child_generator plus random per address",
        "draws_per_repetition": draws,
        "load_at_start": load_start,
        "load_at_end": os.getloadavg(),
        "microseconds_per_draw_samples": samples,
        "median_microseconds_per_draw": {
            key: statistics.median(values) for key, values in samples.items()
        },
        "minimum_microseconds_per_draw": {
            key: min(values) for key, values in samples.items()
        },
        "maximum_microseconds_per_draw": {
            key: max(values) for key, values in samples.items()
        },
        "limitation": "wall-clock samples include severe host scheduling variation; the direct path's medians do not establish a horizon cost relationship",
    }


def _comparisons(measurements: list[dict]) -> dict:
    """Fit a two-size engineering extrapolation, without a full run (§8)."""
    comparisons = {}
    for mode in ("direct", "registry"):
        records = sorted(
            (
                item
                for item in measurements
                if item["emigration_stream"] == mode
            ),
            key=lambda item: item["initial_people"],
        )
        if len(records) < 2:
            continue
        smaller, larger = records[0], records[-1]
        rows = (
            larger["mortality_person_years"]
            - smaller["mortality_person_years"]
        )
        seconds = (
            larger["projection_wall_time_seconds"]
            - smaller["projection_wall_time_seconds"]
        )
        slope = seconds / rows
        fixed = (
            smaller["projection_wall_time_seconds"]
            - slope * smaller["mortality_person_years"]
        )
        average_costs = [
            item["projection_wall_time_seconds"]
            / item["mortality_person_years"]
            for item in records
        ]
        envelope = [min(average_costs), max(average_costs)]
        comparisons[mode] = {
            "marginal_seconds_per_mortality_person_year": slope,
            "fitted_fixed_seconds_per_projected_year": fixed / 75,
            "fitted_estimate_status": "unusable under varying host load; the raw marginal coefficient is not a runtime prediction",
            "observed_average_seconds_per_mortality_person_year_envelope": envelope,
            "average_cost_extrapolation_seconds_per_million_person_years": [
                value * 1_000_000 for value in envelope
            ],
            "extrapolation_formula": "multiply the observed average-cost envelope by the full run's mortality person-years; this includes fixed overhead and is not a marginal estimate",
            "limitation": "two small profiled sizes on a loaded host; the average-cost envelope is an engineering extrapolation, not a bound; full-size measurement remains open before OP10a",
        }
    return comparisons


def _write(payload: dict, output: Path | None) -> None:
    """Write the completed measurements (design §8)."""
    if output is not None:
        output.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def main() -> None:
    """Run one process at a time and retain partial measurements (§8)."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sizes", type=_positive_int, nargs="+", default=[25, 100]
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timeout-seconds", type=_positive_int, default=600)
    parser.add_argument(
        "--worker-size", type=_positive_int, help=argparse.SUPPRESS
    )
    parser.add_argument(
        "--worker-stream",
        choices=("direct", "registry"),
        help=argparse.SUPPRESS,
    )
    arguments = parser.parse_args()
    if arguments.worker_size is not None:
        print(
            json.dumps(
                _measure(arguments.worker_size, arguments.worker_stream),
                sort_keys=True,
            )
        )
        return
    measurements = []
    payload = {
        "scope": "invented data; arithmetic conformance and resource use only",
        "start_year": START_YEAR,
        "registered_horizon": REGISTERED_HORIZON,
        "projected_years": 75,
        "requested_initial_sizes": arguments.sizes,
        "process_isolation": "one fresh worker per size and emigration stream implementation; workers run sequentially",
        "peak_memory_method": "resource.getrusage(RUSAGE_SELF).ru_maxrss; bytes on macOS, KiB converted to bytes on Linux",
        "profile_method": "cProfile projection only; registry_sequences measure root/period/module seed_sequence cumulative cost, excluding child leaves and default_rng; sealed_generator_setup_total adds four disjoint module/child/tagged/tagged-child setup wrappers and includes all leaves/default_rng; emigration_direct_sequences measures direct construction; emigration_generator_setup includes complete tagged generator setup",
        "person_stream_adapters": [
            "engine.steps.apply_mortality",
            "baselines.fertility.AsfrFertilityStep",
        ],
        "nondrawing_adapters": [
            "engine.steps.advance_age",
            "open_population.exits.no_marital_transitions",
            "no-op disability, earnings, claiming and household",
        ],
        "marital_choice_reason": "nonnull emigration permits only no_marital_transitions until OP4; exits.py:64–67",
        "draw_index": 0,
        "measurements": measurements,
        "full_size_measurement": "open OP1 item required before OP10a; intentionally not attempted in this build",
    }
    for size in arguments.sizes:
        for mode in ("direct", "registry"):
            started = time.perf_counter()
            try:
                process = subprocess.run(
                    [
                        sys.executable,
                        str(Path(__file__).resolve()),
                        "--worker-size",
                        str(size),
                        "--worker-stream",
                        mode,
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=arguments.timeout_seconds,
                )
            except subprocess.TimeoutExpired:
                payload["stopped_before"] = {
                    "initial_size": size,
                    "stream": mode,
                }
                payload["stop_reason"] = "worker exceeded timeout"
                _write(payload, arguments.output)
                print(json.dumps(payload, indent=2, sort_keys=True))
                return
            except subprocess.CalledProcessError as error:
                raise RuntimeError(
                    f"invented worker failed for size {size}, {mode}:\n"
                    f"{error.stderr}"
                ) from error
            measurement = json.loads(process.stdout)
            measurement["subprocess_wall_time_seconds"] = (
                time.perf_counter() - started
            )
            measurements.append(measurement)
            payload["size_comparisons"] = _comparisons(measurements)
            _write(payload, arguments.output)
            print(
                json.dumps(
                    {
                        key: measurement[key]
                        for key in (
                            "initial_people",
                            "emigration_stream",
                            "projection_wall_time_seconds",
                            "load_at_projection_start",
                        )
                    }
                ),
                flush=True,
            )
    for size in arguments.sizes:
        records = [
            item for item in measurements if item["initial_people"] == size
        ]
        if len({item["projection_sha256"] for item in records}) != 1:
            raise AssertionError(
                "registry and direct projection outputs differ"
            )
    payload["stream_modes_have_identical_projection_hashes"] = True
    payload["rng_microbenchmark"] = _microbenchmark()
    _write(payload, arguments.output)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
