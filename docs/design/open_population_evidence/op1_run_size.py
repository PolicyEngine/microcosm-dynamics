"""Measure full-horizon OP1 resource use on invented rosters (design §8).

Run ``python docs/design/open_population_evidence/op1_run_size.py --sizes 25
100 --output docs/design/open_population_evidence/op1_run_size.json`` from the
repository root. Each size and stream mode runs in a fresh worker,
sequentially. The sealed loop's own module generators always come from its
registry (``engine/loop.py:217``, ``:297–350``). Three stream modes compare
which class serves the other draws:

- ``registry``: the adapters' person and tagged draws and the emigration
  draws all come from ``ProjectionRNGRegistry`` (``rng_streams="registry"``,
  with the exit adapter's binding patched to the registry);
- ``direct_emigration``: OP1's behavior before the injection, the adapters on
  the registry and emigration on ``DirectRNGStreams``;
- ``direct``: the default, every person and tagged draw on
  ``DirectRNGStreams`` (``rng_streams="direct"``).

Each record names the stream classes the adapters and the exit adapter were
observed to receive, and the SHA-256 of ``open_population/streams.py``.

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
The direct wrappers measure ``_sequence`` construction, for emigration and,
in ``direct`` mode, for the adapters; four disjoint adapter wrappers report
complete direct setup as the sealed ones do. Complete emigration
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
ROOT = Path(__file__).resolve().parents[3]
# Each mode: (harness rng_streams, emigration stream class).
STREAM_MODES = {
    "registry": ("registry", "registry"),
    "direct_emigration": ("registry", "direct"),
    "direct": ("direct", "direct"),
}
HASHED_SOURCES = (
    "src/populace_dynamics/open_population/streams.py",
    "src/populace_dynamics/open_population/harness.py",
    "src/populace_dynamics/open_population/exits.py",
)


def _source_digests() -> dict:
    """Hash the stream, harness and exit sources a run used (design §8)."""
    return {
        path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        for path in HASHED_SOURCES
    }


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
        "adapter_direct_sequences",
        "adapter_direct_module_generator_setup",
        "adapter_direct_person_generator_setup",
        "adapter_direct_tagged_generator_setup",
        "adapter_direct_tagged_child_generator_setup",
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
    direct_names = (
        "adapter_direct_module_generator_setup",
        "adapter_direct_person_generator_setup",
        "adapter_direct_tagged_generator_setup",
        "adapter_direct_tagged_child_generator_setup",
    )
    direct_seconds = sum(
        out[name]["cumulative_seconds"] for name in direct_names
    )
    out["adapter_direct_generator_setup_total"] = {
        "calls": sum(out[name]["calls"] for name in direct_names),
        "cumulative_seconds": direct_seconds,
        "share_of_profile_total": direct_seconds / stats.total_tt,
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
    rng_streams, emigration_stream = STREAM_MODES[stream_mode]
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
    from populace_dynamics.open_population import exits, harness, streams
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
    observed = {"adapters": set(), "emigration": set()}

    def stream_class(cls):
        """Name the project class behind a profiled subclass."""
        base = next(
            item
            for item in cls.__mro__
            if item.__module__.startswith("populace_dynamics")
        )
        return f"{base.__module__}.{base.__qualname__}"

    def mortality(frame, context, rng):
        draw_counts["mortality"] += len(frame)
        observed["adapters"].add(stream_class(type(context.rng_registry)))
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
            observed["emigration"].add(stream_class(type(self)))
            return tagged_child_generator(self, *args)

        tagged_child_generator = emigration_generator_setup

    class ProfiledDirect(DirectRNGStreams):
        def emigration_direct_sequences(self, period, module, *tail):
            return super()._sequence(period, module, *tail)

        _sequence = emigration_direct_sequences

        def emigration_generator_setup(self, *args):
            observed["emigration"].add(stream_class(type(self)))
            return super().tagged_child_generator(*args)

        tagged_child_generator = emigration_generator_setup

    class ProfiledAdapterDirect(DirectRNGStreams):
        """The adapters' direct streams, with disjoint setup wrappers."""

        def adapter_direct_sequences(self, period, module, *tail):
            return super()._sequence(period, module, *tail)

        _sequence = adapter_direct_sequences

        def adapter_direct_module_generator_setup(self, *args):
            return super().generator(*args)

        generator = adapter_direct_module_generator_setup

        def adapter_direct_person_generator_setup(self, *args):
            return super().child_generator(*args)

        child_generator = adapter_direct_person_generator_setup

        def adapter_direct_tagged_generator_setup(self, *args):
            return super().tagged_generator(*args)

        tagged_generator = adapter_direct_tagged_generator_setup

        def adapter_direct_tagged_child_generator_setup(self, *args):
            return super().tagged_child_generator(*args)

        tagged_child_generator = adapter_direct_tagged_child_generator_setup

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
    projection_cpu_started = time.process_time()
    cls = ProfiledDirect if emigration_stream == "direct" else ProfiledRegistry
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
        patch.object(harness, "DirectRNGStreams", ProfiledAdapterDirect),
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
            rng_streams=rng_streams,
        )
        profile.disable()
    projection_cpu_seconds = time.process_time() - projection_cpu_started
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
    expected_adapters = (
        "populace_dynamics.open_population.streams.DirectRNGStreams"
        if rng_streams == "direct"
        else "populace_dynamics.engine.rng.ProjectionRNGRegistry"
    )
    expected_emigration = (
        "populace_dynamics.open_population.streams.DirectRNGStreams"
        if emigration_stream == "direct"
        else "populace_dynamics.engine.rng.ProjectionRNGRegistry"
    )
    if observed["adapters"] != {expected_adapters} or observed[
        "emigration"
    ] != {expected_emigration}:
        raise AssertionError(f"{stream_mode} ran other stream classes")
    summary = {
        "status": "completed",
        "stream_mode": stream_mode,
        "rng_streams": result.rng_streams,
        "adapter_stream_class": expected_adapters,
        "emigration_stream": emigration_stream,
        "emigration_stream_class": expected_emigration,
        "result_rng_stream_class": result.rng_stream_class,
        "streams_py_sha256": hashlib.sha256(
            Path(streams.__file__).read_bytes()
        ).hexdigest(),
        "source_sha256": _source_digests(),
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
        "projection_process_cpu_seconds": projection_cpu_seconds,
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
    for mode in STREAM_MODES:
        records = sorted(
            (item for item in measurements if item["stream_mode"] == mode),
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
        choices=tuple(STREAM_MODES),
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
        "process_isolation": "one fresh worker per size and stream mode; workers run sequentially",
        "stream_modes": {
            "registry": "adapters' person and tagged draws and emigration draws on ProjectionRNGRegistry",
            "direct_emigration": "adapters on ProjectionRNGRegistry, emigration on DirectRNGStreams (OP1 before the injection)",
            "direct": "every person and tagged draw on DirectRNGStreams (the default)",
            "loop_module_generators": "the sealed loop's 600 positional module generators stay on its registry in every mode",
        },
        "source_sha256": _source_digests(),
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
        for mode in STREAM_MODES:
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
                            "stream_mode",
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
            raise AssertionError("the stream modes' projections differ")
    payload["stream_modes_have_identical_projection_hashes"] = True
    payload["rng_microbenchmark"] = _microbenchmark()
    _write(payload, arguments.output)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
