"""INVENTED DATA - NOT A COMPARISON: exercise 1/3 group adapter dry run.

All people, careers, rates, weights and group reports are invented. The
inherited statutory FRA schedule supplies the mechanism, not observations.
No PSID files, real parameters, model artifacts or comparator values load.
G1 builds attributes, G2 builds lifetime measures and G3 builds every cell.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from populace_dynamics.cohorts import group_attributes as g1  # noqa: E402
from populace_dynamics.cohorts import psid2010  # noqa: E402
from populace_dynamics.cola_track_a import (  # noqa: E402
    TrackAConfig,
    invented,
    prepare_track_a_cohort,
    run_track_a,
)
from populace_dynamics.data import group_attributes_psid as gap  # noqa: E402
from populace_dynamics.estimates import lifetime_measures as g2  # noqa: E402
from populace_dynamics.fra68_track import FRA68Config, run_fra68  # noqa: E402
from populace_dynamics.group_breakdowns.cola import (  # noqa: E402
    reproduce_cola,
)
from populace_dynamics.group_breakdowns.common import (  # noqa: E402
    INVENTED_HEADER,
    LifetimeOptions,
    run_group_breakdown,
)
from populace_dynamics.group_breakdowns.fra68 import (  # noqa: E402
    reproduce_fra68,
)
from populace_dynamics.track_a_v2.invented import invented_inputs  # noqa: E402


def build_invented_inputs(seed: int = 7):
    """Both original waves, with invented rates and their marriage histories."""
    inputs = invented_inputs(seed)
    raw_by_wave = {
        wave: invented.invented_psid2010_inputs(
            seed=seed, anchor_wave=wave, claiming_pmf=inputs.claiming_pmf
        )
        for wave in (2011, 2009)
    }
    secondary = prepare_track_a_cohort(
        psid2010.build_psid2010_cohort(
            raw_by_wave[2009], psid2010.Psid2010CohortSpec(anchor_wave=2009)
        ),
        data_provenance="invented",
        config=TrackAConfig(),
    )
    mortality = replace(
        inputs.population_mortality,
        ratio_by_year={year: (1.0, 1.0) for year in range(2009, 2031)},
    )
    return (
        replace(
            inputs,
            additional_cohorts=(secondary,),
            population_mortality=mortality,
        ),
        raw_by_wave,
    )


def invented_attribute_loader(person_ids, *, anchor_waves):
    """Pass INVENTED reports through the actual G1 cohort builder."""
    wave = anchor_waves[0]
    reports = []
    education = []
    for index, pid in enumerate(person_ids):
        report = dict.fromkeys(gap.REPORT_CODE_COLUMNS, pd.NA)
        report.update(person_id=pid, wave=wave, role="head")
        report["hispanic_code"] = 1 if index % 4 == 0 else 0
        for mention in range(1, len(gap.FAMILY_ITEMS[wave].race["head"]) + 1):
            report[f"race_code_{mention}"] = (
                (1, 2, 3)[index % 3] if mention == 1 else 0
            )
        if wave in gap.BIRTHPLACE_WAVES:
            report["birth_state_code"] = 1
            report["year_came_code"] = 0
        if wave in gap.FAMILY_EDUCATION_WAVES:
            report["family_education_code"] = 12
        reports.append(report)
        education.append(
            {
                "person_id": pid,
                "wave": wave,
                "education_code": (11, 12, 14, 16, 17)[index % 5],
                "role": "head",
                "family_education_code": pd.NA,
            }
        )
    report_frame = pd.DataFrame(reports)
    education_frame = pd.DataFrame(education)
    for frame in (report_frame, education_frame):
        for column in frame:
            frame[column] = frame[column].astype(
                "string" if column == "role" else "Int64"
            )
    supplied = g1.GroupAttributeInputs(
        reports=report_frame,
        education=education_frame,
        universe=pd.Series(person_ids, dtype="int64", name="person_id"),
        provenance={"kind": "INVENTED", "fixture": "projection group dry run"},
    )
    return g1.build_group_attributes(
        supplied, person_ids, anchor_waves=anchor_waves
    )


def invented_lifetime_options(raw_by_wave) -> LifetimeOptions:
    """INVENTED tax and interest values; no captured data values are used."""
    rates = g2.OASDITaxRates(
        combined_percent_by_year={},
        open_ended_from=1937,
        open_ended_combined_percent=12.4,
        basis=g2.TaxRateBasis.EMPLOYEE_EMPLOYER_PAID,
        provenance={"kind": "INVENTED"},
    )
    interest = g2.TrustFundInterestRates(
        percent_by_year={year: 3.0 for year in range(1940, 2101)},
        series="INVENTED",
        provenance={"kind": "INVENTED"},
    )

    def episodes(wave):
        history = raw_by_wave[wave].marriage_history
        return psid2010._episodes_with_separation(history), tuple(
            int(pid) for pid in history.person_id.unique()
        )

    return LifetimeOptions(
        rates=rates, interest=interest, marriage_episode_loader=episodes
    )


def dry_run(exercise: str, *, draws: int = 2, seed: int = 7):
    """Differential replay against a frozen runner on INVENTED inputs."""
    inputs, raw = build_invented_inputs(seed)
    if exercise == "cola":
        config = TrackAConfig(draw_indices=tuple(range(draws)))
        parent = run_track_a(inputs, config=config)
        replay = reproduce_cola(inputs, config=config)
    elif exercise == "fra68":
        config = FRA68Config(draw_indices=tuple(range(draws)))
        parent = run_fra68(inputs, config=config)
        replay = reproduce_fra68(inputs, config=config)
    else:
        raise ValueError("exercise must be cola or fra68")
    digest = hashlib.sha256(
        json.dumps(parent, sort_keys=True, allow_nan=False).encode()
    ).hexdigest()
    return run_group_breakdown(
        replay,
        parent,
        inputs=inputs,
        config=config,
        parent_sha256=digest,
        attribute_loader=invented_attribute_loader,
        lifetime_options=invented_lifetime_options(raw),
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--exercise", choices=("cola", "fra68", "both"), default="both"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "docs/analysis/nasi_group_breakdowns_invented_20261001",
    )
    parser.add_argument("--draws", type=int, default=2)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args(argv)
    if args.draws < 1:
        parser.error("--draws must be positive")
    exercises = (
        ("cola", "fra68") if args.exercise == "both" else (args.exercise,)
    )
    for exercise in exercises:
        result = dry_run(exercise, draws=args.draws, seed=args.seed)
        encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
        output = args.output_dir / exercise
        output.mkdir(parents=True, exist_ok=True)
        (output / "result.json").write_text(encoded)
        (output / "RESULTS.md").write_text(
            f"# {INVENTED_HEADER}\n\nExercise: {exercise}. "
            "Registered, one-shot, post hoc, not blind; report-only labels "
            "describe the intended registered artifact. This dry run is "
            "unregistered and uses invented data only.\n\n"
            f"All {len(result['rows'])} registered rows reproduced the "
            "frozen runner exactly before group loading. Both original "
            "waves and both population variants are in [result.json](result.json). "
            "G1 supplies attributes, G2 supplies lifetime measures, and G3 "
            "supplies labels, suppression flags and every group cell.\n\n"
            "No PSID file, real-data outcome or comparator value was used. "
            "Income/poverty are unavailable. Lifetime careers stop at the "
            "opening year, and interest/tax inputs here are invented.\n"
        )
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
