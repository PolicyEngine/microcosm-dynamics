"""Measure OP1 resource use through 2100 on invented rosters only.

Implement ``docs/design/open_population.md`` §§3.1 (OP1), 7 and 8,
approved in ruling d1925. This measures accounting conformance and run size;
it supplies no scientific or population claim. Each size runs in a fresh
process, including imports, so peak RSS belongs to that size alone.

The existing mortality step draws person-keyed deaths before aging
(``engine/steps.py:113–148``). The opt-in fertility adapter draws from the
invented ASFR below and delegates child materialization
(``baselines/fertility.py:163–181``). The cohort builder allocates scheduled
IDs and stamps their entry year (``engine/entrant_schedule.py:298–314``).
OP1 wraps those adapters and runs both accounting checks
(``open_population/harness.py:236–275``).

Run from the repository root with this checkout's package importable::

    python docs/design/open_population_evidence/op1_run_size.py \\
        --sizes 25 100 --output \\
        docs/design/open_population_evidence/op1_run_size.json

Wall time includes worker imports, setup, projection and summary. The separate
projection timing excludes imports and invented-frame construction. Peak RSS
includes the worker's import closure and retained annual projection slices.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

START_YEAR = 2025
REGISTERED_HORIZON = 2100


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("sizes must be positive integers")
    return parsed


def _measure(size: int) -> dict[str, object]:
    started = time.perf_counter()
    import resource
    from collections import Counter
    from functools import partial

    import numpy as np
    import pandas as pd

    from populace_dynamics.baselines.fertility import AsfrFertilityStep
    from populace_dynamics.engine.entrant_schedule import (
        build_entrant_schedule,
    )
    from populace_dynamics.engine.loop import MaritalStepResult, PeriodModules
    from populace_dynamics.engine.steps import (
        AgeSexMortalityModel,
        advance_age,
        apply_mortality,
    )
    from populace_dynamics.open_population.harness import (
        ProductionRequest,
        run_production,
    )

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

    def no_marriages(frame, context, rng):
        return MaritalStepResult(
            sim_years=frame.iloc[:0].copy(), births=pd.DataFrame()
        )

    def no_composition(frame, context, marital, rng):
        return frame

    # These are invented computational loads, not estimated demographic laws.
    mortality = AgeSexMortalityModel(
        bands=((0, 74), (75, 120)),
        probability={
            (band, sex): probability
            for band, probability in (("0-74", 0.01), ("75+", 0.10))
            for sex in ("female", "male")
        },
    )
    modules = PeriodModules(
        mortality=partial(apply_mortality, model=mortality),
        aging=advance_age,
        marital_core=no_marriages,
        fertility=AsfrFertilityStep(
            asfr=lambda year: {age: 0.06 for age in range(18, 41)}
        ),
        disability=unchanged,
        earnings=unchanged,
        claiming=unchanged,
        household_composition=no_composition,
    )
    projection_started = time.perf_counter()
    result = run_production(
        initial,
        modules,
        ProductionRequest(
            registered_horizon=REGISTERED_HORIZON,
            end_year=REGISTERED_HORIZON,
            draw_index=0,
        ),
        schedule_builder=build_schedule,
        reserved_real_ids=initial["person_id"],
    )
    projection_seconds = time.perf_counter() - projection_started
    events = Counter(event.kind.value for event in result.events)
    periods = result.accounting.periods
    system = platform.system()
    if system not in {"Darwin", "Linux"}:
        raise RuntimeError(
            "peak RSS units are defined here for macOS and Linux"
        )
    peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    summary = {
        "status": "completed",
        "initial_people": size,
        "final_people": len(result.projection.slices[-1]),
        "maximum_live_people": max(
            len(frame) for frame in result.projection.slices
        ),
        "retained_person_year_rows": sum(
            len(frame) for frame in result.projection.slices
        ),
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
        "projection_wall_time_seconds": projection_seconds,
        "peak_memory_bytes": int(
            peak_rss * (1 if system == "Darwin" else 1024)
        ),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
    }
    summary["wall_time_seconds"] = time.perf_counter() - started
    return summary


def _write(payload: dict[str, object], output: Path | None) -> None:
    serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if output is not None:
        output.write_text(serialized, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sizes", type=_positive_int, nargs="+", default=[25, 100, 400]
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timeout-seconds", type=_positive_int)
    parser.add_argument(
        "--worker-size", type=_positive_int, help=argparse.SUPPRESS
    )
    arguments = parser.parse_args()
    if arguments.worker_size is not None:
        print(json.dumps(_measure(arguments.worker_size), sort_keys=True))
        return
    measurements = []
    payload = {
        "scope": "invented data; arithmetic conformance and resource use only",
        "start_year": START_YEAR,
        "registered_horizon": REGISTERED_HORIZON,
        "requested_initial_sizes": arguments.sizes,
        "process_isolation": "one fresh worker per initial roster size",
        "peak_memory_method": "resource.getrusage(RUSAGE_SELF).ru_maxrss; bytes on macOS, KiB converted to bytes on Linux",
        "wall_time_scope": "worker imports, setup, projection and summary",
        "draw_index": 0,
        "measurements": measurements,
        "largest_completed_initial_size": None,
    }
    for size in arguments.sizes:
        started = time.perf_counter()
        try:
            process = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "--worker-size",
                    str(size),
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=arguments.timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            payload["stopped_before_initial_size"] = size
            payload["stop_reason"] = "worker exceeded timeout"
            _write(payload, arguments.output)
            break
        measurement = json.loads(process.stdout)
        measurement["subprocess_wall_time_seconds"] = (
            time.perf_counter() - started
        )
        measurements.append(measurement)
        payload["largest_completed_initial_size"] = max(
            item["initial_people"] for item in measurements
        )
        _write(payload, arguments.output)
        print(json.dumps(measurement, sort_keys=True), flush=True)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
