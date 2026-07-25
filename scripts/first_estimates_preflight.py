#!/usr/bin/env python3
"""Advisory birth-completeness preflight for the first estimates.

Run this read-only tool before registering a first-estimates ceremony.  It
loads the registered input plan and its full source frames, materializes only
the realized population seed frames, and applies the section 3.1 birth-year
disposition law.  It does not fit a model, run a projection draw, write an
artifact, or participate in the sealed ceremony.

Every registered holdout person is treated conservatively as
``CANDIDATE-POSSIBLE`` because claim candidacy is unknown until projection.
The command fails if that all-holdout universe is not disposition-complete or
if an independently repeated clause-3 bounds check fails.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from collections.abc import Collection, Sequence
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

from populace_dynamics.estimates import career, coordinator  # noqa: E402
from populace_dynamics.harness import m6_population  # noqa: E402

SOURCE_KEYS = tuple(source.value for source in career.BirthSource)
DERIVED_SOURCE = career.BirthSource.DERIVED_PROJECTION_AGE.value
UNRESOLVED_SOURCE = career.BirthSource.UNRESOLVED.value
MAX_ERROR_SAMPLE = 20


def _integer(value: Any, label: str) -> int:
    """Return a finite integer without silently truncating source data."""

    if pd.isna(value):
        raise ValueError(f"{label} is missing")
    number = float(value)
    if not math.isfinite(number) or not number.is_integer():
        raise ValueError(f"{label} must be a finite integer, got {value!r}")
    return int(number)


def _integer_ids(values: Collection[Any], label: str) -> frozenset[int]:
    return frozenset(_integer(value, label) for value in values)


def _load_candidate_possible_population(
    repository: Path,
) -> tuple[Any, m6_population.M6RealizedPopulation]:
    """Load registered sources and build seed frames without fitting.

    ``build_realized_population`` requires an earnings-domain marker set even
    though that marker is irrelevant to this audit.  Passing every holdout
    anchor ID is deliberately conservative and avoids fitting the production
    earnings model solely to recover its narrower domain.
    """

    plan = coordinator._load_registered_input_plan(repository)
    inputs = plan.load_full_inputs()
    if getattr(inputs, "refit_inputs", None) is not plan.fit_inputs:
        raise RuntimeError(
            "registered full inputs do not retain the plan's fit-input identity"
        )
    candidate_possible_ids = _integer_ids(
        inputs.truth.anchor["person_id"],
        "registered anchor person_id",
    )
    population = m6_population.build_realized_population(
        demographic_panel=inputs.demographic_panel,
        death_records=inputs.death_records,
        earnings_panel=inputs.earnings_panel,
        disability_panel=inputs.disability_panel,
        panel_builder_inputs=inputs.panel_builder_inputs,
        earnings_domain_ids=candidate_possible_ids,
        reserved_real_ids=candidate_possible_ids,
    )
    realized_ids = _integer_ids(
        population.holdout_ids,
        "realized holdout person_id",
    )
    if realized_ids != candidate_possible_ids:
        missing = sorted(candidate_possible_ids - realized_ids)
        extra = sorted(realized_ids - candidate_possible_ids)
        raise RuntimeError(
            "registered anchor and realized holdout universes differ: "
            f"missing={missing[:MAX_ERROR_SAMPLE]}, "
            f"extra={extra[:MAX_ERROR_SAMPLE]}"
        )
    return inputs, population


def audit_birth_dispositions(
    *,
    candidate_possible_ids: Collection[Any],
    seed_coordinates: pd.DataFrame,
    records: Sequence[career.BirthYearRecord],
) -> dict[str, Any]:
    """Return the five-class disposition and independent-bounds audit."""

    candidate_ids = _integer_ids(
        candidate_possible_ids,
        "CANDIDATE-POSSIBLE person_id",
    )
    seed = seed_coordinates.copy()
    required_seed_columns = {"person_id", "year", "age"}
    missing_seed_columns = required_seed_columns - set(seed.columns)
    if missing_seed_columns:
        raise ValueError(
            "seed coordinates are missing columns "
            f"{sorted(missing_seed_columns)}"
        )
    seed["person_id"] = seed["person_id"].map(
        lambda value: _integer(value, "seed person_id")
    )
    if seed["person_id"].duplicated().any():
        raise ValueError("seed coordinates contain duplicate people")
    seed_by_person = seed.set_index("person_id")

    by_person: dict[int, career.BirthYearRecord] = {}
    duplicate_ids: list[int] = []
    for record in records:
        person_id = _integer(record.person_id, "birth disposition person_id")
        if person_id not in candidate_ids:
            continue
        if person_id in by_person:
            duplicate_ids.append(person_id)
            continue
        by_person[person_id] = record

    missing_ids = sorted(candidate_ids - set(by_person))
    duplicate_ids = sorted(set(duplicate_ids))
    counts: Counter[str] = Counter()
    invalid_dispositions: list[dict[str, Any]] = []
    derived_violations: list[dict[str, Any]] = []
    derived_count = 0

    for person_id, record in sorted(by_person.items()):
        source = getattr(record.source, "value", record.source)
        source = str(source)
        birth_year = record.birth_year
        if source not in SOURCE_KEYS:
            invalid_dispositions.append(
                {
                    "person_id": person_id,
                    "reason": "source is not one of the five frozen keys",
                    "source": source,
                }
            )
            continue
        counts[source] += 1
        if (source == UNRESOLVED_SOURCE) != (birth_year is None):
            invalid_dispositions.append(
                {
                    "person_id": person_id,
                    "reason": (
                        "unresolved source and numeric birth year disagree"
                    ),
                    "source": source,
                    "birth_year": birth_year,
                }
            )
        if source != DERIVED_SOURCE:
            continue

        derived_count += 1
        violation: dict[str, Any] = {"person_id": person_id}
        if birth_year is None:
            violation["reason"] = "derived source has no birth year"
            derived_violations.append(violation)
            continue
        if person_id not in seed_by_person.index:
            violation["reason"] = "derived source has no seed coordinate"
            derived_violations.append(violation)
            continue
        row = seed_by_person.loc[person_id]
        try:
            year = _integer(birth_year, f"birth year for person {person_id}")
            seed_year = _integer(
                row["year"], f"seed year for person {person_id}"
            )
            age = _integer(row["age"], f"seed age for person {person_id}")
        except ValueError as error:
            violation["reason"] = str(error)
            derived_violations.append(violation)
            continue

        lower = seed_year - 125
        upper = seed_year - 2
        expected = seed_year - age
        per_row_ok = lower <= year <= upper
        global_ok = (
            career.DERIVED_BIRTH_MIN <= year <= career.DERIVED_BIRTH_MAX
        )
        coordinate_ok = 2 <= age <= 125 and year == expected
        if not (per_row_ok and global_ok and coordinate_ok):
            violation.update(
                {
                    "reason": "derived birth year violates clause-3 bounds",
                    "birth_year": year,
                    "seed_year": seed_year,
                    "seed_age": age,
                    "expected_birth_year": expected,
                    "per_row_bounds": [lower, upper],
                    "global_bounds": [
                        career.DERIVED_BIRTH_MIN,
                        career.DERIVED_BIRTH_MAX,
                    ],
                }
            )
            derived_violations.append(violation)

    source_counts = {key: int(counts.get(key, 0)) for key in SOURCE_KEYS}
    disposition_count = sum(source_counts.values())
    coverage_passed = (
        not missing_ids
        and not duplicate_ids
        and not invalid_dispositions
        and disposition_count == len(candidate_ids)
    )
    bounds_passed = not derived_violations
    errors: list[str] = []
    if missing_ids:
        errors.append(
            f"{len(missing_ids)} CANDIDATE-POSSIBLE people lack a disposition"
        )
    if duplicate_ids:
        errors.append(
            f"{len(duplicate_ids)} CANDIDATE-POSSIBLE people have duplicate "
            "dispositions"
        )
    if invalid_dispositions:
        errors.append(
            f"{len(invalid_dispositions)} dispositions violate the frozen "
            "source inventory"
        )
    if disposition_count != len(candidate_ids):
        errors.append(
            "five-class source counts do not reconcile to the "
            "CANDIDATE-POSSIBLE population"
        )
    if derived_violations:
        errors.append(
            f"{len(derived_violations)} derived_projection_age records "
            "violate clause-3 bounds"
        )

    return {
        "status": "pass" if coverage_passed and bounds_passed else "fail",
        "scope": {
            "advisory_tooling": True,
            "sealed_ceremony_component": False,
            "fit_run": False,
            "projection_run": False,
            "candidate_possible_rule": "all registered holdout persons",
        },
        "source_counts": source_counts,
        "checks": {
            "candidate_possible_disposition_coverage": {
                "passed": coverage_passed,
                "candidate_possible_count": len(candidate_ids),
                "disposition_count": disposition_count,
                "missing_count": len(missing_ids),
                "missing_person_ids_sample": missing_ids[:MAX_ERROR_SAMPLE],
                "duplicate_count": len(duplicate_ids),
                "duplicate_person_ids_sample": duplicate_ids[
                    :MAX_ERROR_SAMPLE
                ],
                "invalid_count": len(invalid_dispositions),
                "invalid_sample": invalid_dispositions[:MAX_ERROR_SAMPLE],
            },
            "derived_projection_age_bounds": {
                "passed": bounds_passed,
                "derived_count": derived_count,
                "rule": (
                    "seed_year - 125 <= birth_year <= seed_year - 2; "
                    "1889 <= birth_year <= 2016; "
                    "birth_year = seed_year - seed_age for age 2..125"
                ),
                "violation_count": len(derived_violations),
                "violation_sample": derived_violations[:MAX_ERROR_SAMPLE],
            },
            "five_source_counts_reconcile": {
                "passed": disposition_count == len(candidate_ids),
                "source_count_total": disposition_count,
                "candidate_possible_count": len(candidate_ids),
            },
        },
        "errors": errors,
    }


def run_preflight(repository: Path = ROOT) -> dict[str, Any]:
    """Run the advisory preflight over the registered all-holdout universe."""

    inputs, population = _load_candidate_possible_population(
        repository.resolve()
    )
    seed_coordinates = career.build_seed_coordinates(
        population.initial_slice,
        population.scheduled_entries_by_year,
    )
    candidate_possible_ids = _integer_ids(
        population.holdout_ids,
        "realized holdout person_id",
    )
    records = career.derive_birth_years(
        inputs.refit_inputs.family_context.marriage_records,
        inputs.earnings_panel,
        synthetic_birth_years=None,
        seed_coordinates=seed_coordinates,
        required_person_ids=candidate_possible_ids,
    )
    return audit_birth_dispositions(
        candidate_possible_ids=candidate_possible_ids,
        seed_coordinates=seed_coordinates,
        records=records,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the advisory, pre-registration first-estimates "
            "birth-completeness preflight. This is not a sealed ceremony "
            "entry point."
        )
    )
    parser.add_argument(
        "--repository",
        type=Path,
        default=ROOT,
        help="repository checkout containing the registered input sources",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        report = run_preflight(args.repository)
    except Exception as error:
        print(
            "first-estimates birth-completeness preflight could not run: "
            f"{type(error).__name__}: {error}",
            file=sys.stderr,
        )
        return 2

    print(json.dumps(report, allow_nan=False, indent=2, sort_keys=True))
    if report["status"] != "pass":
        print(
            "first-estimates birth-completeness preflight FAILED: "
            + "; ".join(report["errors"]),
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
