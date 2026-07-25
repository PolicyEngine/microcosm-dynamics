#!/usr/bin/env python3
"""Reduce the registered first-estimates birth-year evidence for one draw.

This is manual, read-only evidence tooling, not a sealed ceremony entry point.
It does not mutate registered inputs or projection state.  Its sole write is
the canonical JSON path selected by ``--output``.

The fast path reads the sha256-pinned draw cache created by the unregistered
diagnostic probe.  With ``--regenerate``, the script instead uses
``coordinator._load_registered_input_plan`` and holds the registered scripts
path context over the production candidate-3 prefix.  That cache-independent
path runs one real draw and clones it only to satisfy the production driver's
twenty-wrapper contract; on the reference machine it takes about 55 minutes.

Regenerate the canonical artifact from the pinned diagnostic cache, from this
worktree and never from the sealed runner worktree:

    POPULACE_DYNAMICS_PE_US_DIR=/Users/maxghenis/PolicyEngine/\
social-security-model-worktrees/sol-c3-runner/.venv/lib/python3.14/site-packages \
    /Users/maxghenis/PolicyEngine/social-security-model-worktrees/\
sol-c3-runner/.venv/bin/python \
    scripts/first_estimates_birth_evidence.py

Replay the cache-independent registered-input path with the same command plus
``--regenerate``.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import pickle
import subprocess
import sys
from collections import Counter
from collections.abc import Collection, Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

from populace_dynamics import claiming  # noqa: E402
from populace_dynamics.estimates import (  # noqa: E402
    career,
    coordinator,
    ledgers,
    preparation,
    publication,
    runner,
)
from populace_dynamics.estimates import (  # noqa: E402
    parameters as parameter_module,
)
from populace_dynamics.estimates.runner import (  # noqa: E402
    FirstReportProjectionDraw,
)
from populace_dynamics.harness.m6_cells import (  # noqa: E402
    EARN_ANCHOR_YEAR,
    SEED_WAVE,
)

SCHEMA_VERSION = "first_estimates_birth_evidence.v2"
EXPECTED_MASTER_SHA = "daf3ff5978de5137ba50490f78ac52890291a399"
EXPECTED_PE_US_VERSION = "1.752.2"
EXPECTED_INTERPRETER = Path(
    "/Users/maxghenis/PolicyEngine/social-security-model-worktrees/"
    "sol-c3-runner/.venv/bin/python"
)
SEALED_RUN_ROOT = EXPECTED_INTERPRETER.parents[2]
EXPECTED_PE_US_DIR = Path(
    "/Users/maxghenis/PolicyEngine/social-security-model-worktrees/"
    "sol-c3-runner/.venv/lib/python3.14/site-packages"
)
DEFAULT_CACHE = Path(
    "/private/tmp/claude-501/-Users-maxghenis/"
    "3a1c17cd-d932-4345-9056-960569766f0a/scratchpad/"
    "e8_batch_draw0.pickle"
)
DEFAULT_CACHE_SHA256 = (
    "3ba147f7666ad77d8f7735969e4329fa7180cef091ad4ee326f35b2834a72068"
)
DERIVED_BIRTH_MIN = 1889
DERIVED_BIRTH_MAX = 2016
SOURCE_CLASSES = (
    "exact_marriage",
    "inferred_period_age",
    "synthetic_native",
    "derived_projection_age",
    "unresolved",
)
IMPRECISE_BIRTH_SOURCES = frozenset(
    {"inferred_period_age", "derived_projection_age"}
)
DI_CLASSES = ("di_conversion", "di_unknown", "non_di")
STAGE_D_PREDICATES = (
    "domain_complete",
    "eligibility_era",
    "nonempty_span",
    "chronology",
    "coverage",
)
STAGE_D_OUTCOMES = (
    "excluded_domain_incomplete",
    "excluded_pre1979_eligibility",
    "excluded_empty_span",
    "excluded_chronology_inconsistent",
    "excluded_low_coverage",
    "included",
)
PRODUCTION_SOURCE_PATHS = (
    Path("src/populace_dynamics"),
    Path("scripts/registered_m6_candidate3_inputs.py"),
    Path("scripts/registered_m6_candidate2_inputs.py"),
    Path("scripts/registered_m6_inputs.py"),
    Path("scripts/build_mortality_floors.py"),
)


@dataclass(frozen=True)
class LoadedDraw:
    """The three cached/regenerated objects consumed by the reducer."""

    inputs: Any
    phase: Any
    draw: FirstReportProjectionDraw
    execution: Mapping[str, Any]


@dataclass(frozen=True)
class BirthEvidence:
    """Resolved source law and the frames needed downstream."""

    trajectory: pd.DataFrame
    roster: pd.DataFrame
    synthetic_birth_years: Mapping[int, int]
    population_ids: frozenset[int]
    seed: pd.DataFrame
    birth_year_by_person: Mapping[int, int]
    source_by_person: Mapping[int, str]
    initially_unresolved_ids: frozenset[int]
    derived_ids: frozenset[int]
    unresolved_ids: frozenset[int]
    infant_code_ids: frozenset[int]
    sentinel_ids: frozenset[int]
    result: Mapping[str, Any]


@dataclass(frozen=True)
class FunnelEvidence:
    """Full Stage-A/B partition and production candidate baseline."""

    di_by_person: Mapping[int, str]
    raw_claim_year_carrier_ids: frozenset[int]
    candidate_ids: frozenset[int]
    domain_ids: frozenset[int]
    claiming_schedule: Any
    baseline_inclusion: career.InclusionResult
    result: Mapping[str, Any]


@dataclass(frozen=True)
class CandidateStageState:
    """One scenario's production coordinates and ordered predicates."""

    outcome_by_person: Mapping[int, str]
    included_ids: frozenset[int]
    predicate_value_by_person: Mapping[int, Mapping[str, bool]]
    predicate_reached_by_person: Mapping[int, Mapping[str, bool]]


@dataclass(frozen=True)
class SensitivityEvidence:
    """Baseline and both production birth-coordinate perturbations."""

    inclusions: Mapping[int, career.InclusionResult]
    birth_maps: Mapping[int, Mapping[int, int]]
    states: Mapping[int, CandidateStageState]
    result: Mapping[str, Any]


@dataclass(frozen=True)
class LedgerEvidence:
    """Coherent-shift ledgers and the personwise adversarial range."""

    result: Mapping[str, Any]


def _run_git(
    *arguments: str, check: bool = True
) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(ROOT), *arguments],
        check=check,
        capture_output=True,
        text=True,
    )


def _assert_input_identity() -> None:
    """Require the reducer branch to retain the pinned production bytes."""

    observed_root = Path(
        _run_git("rev-parse", "--show-toplevel").stdout.strip()
    ).resolve()
    if observed_root != ROOT:
        raise RuntimeError(
            f"Git root {observed_root} differs from reducer root {ROOT}"
        )
    _run_git("cat-file", "-e", f"{EXPECTED_MASTER_SHA}^{{commit}}")
    ancestor = _run_git(
        "merge-base",
        "--is-ancestor",
        EXPECTED_MASTER_SHA,
        "HEAD",
        check=False,
    )
    if ancestor.returncode != 0:
        raise RuntimeError(
            f"pinned master {EXPECTED_MASTER_SHA} is not an ancestor of HEAD"
        )
    paths = tuple(str(path) for path in PRODUCTION_SOURCE_PATHS)
    committed = _run_git(
        "diff",
        "--quiet",
        EXPECTED_MASTER_SHA,
        "HEAD",
        "--",
        *paths,
        check=False,
    )
    working = _run_git(
        "diff",
        "--quiet",
        "--",
        *paths,
        check=False,
    )
    if committed.returncode != 0 or working.returncode != 0:
        raise RuntimeError(
            "production sources differ from the pinned master bytes"
        )


def _assert_runtime() -> Mapping[str, str]:
    """Fail closed unless the requested parameter environment is active."""

    observed_interpreter = Path(sys.executable).resolve()
    if observed_interpreter != EXPECTED_INTERPRETER.resolve():
        raise RuntimeError(
            "evidence reducer requires the pinned runner interpreter: "
            f"{EXPECTED_INTERPRETER}"
        )
    if ROOT == SEALED_RUN_ROOT or SEALED_RUN_ROOT in ROOT.parents:
        raise RuntimeError(
            "refusing to execute inside the sealed run worktree"
        )
    raw_parameter_root = os.environ.get("POPULACE_DYNAMICS_PE_US_DIR")
    if raw_parameter_root is None:
        raise RuntimeError(
            "POPULACE_DYNAMICS_PE_US_DIR must point at the pinned runner "
            f"site-packages directory {EXPECTED_PE_US_DIR}"
        )
    observed_parameter_root = Path(raw_parameter_root).resolve()
    if observed_parameter_root != EXPECTED_PE_US_DIR.resolve():
        raise RuntimeError(
            "POPULACE_DYNAMICS_PE_US_DIR is not the pinned parameter stack: "
            f"{observed_parameter_root}"
        )
    version = importlib.metadata.version("policyengine-us")
    if version != EXPECTED_PE_US_VERSION:
        raise RuntimeError(
            f"policyengine-us {version!r} != pinned "
            f"{EXPECTED_PE_US_VERSION!r}"
        )
    return {
        "interpreter": str(EXPECTED_INTERPRETER),
        "interpreter_resolved": str(observed_interpreter),
        "policyengine_us_dir": str(observed_parameter_root),
        "policyengine_us_version": version,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(16 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _reducer_command(*arguments: str) -> str:
    return " ".join(
        (
            f"POPULACE_DYNAMICS_PE_US_DIR={EXPECTED_PE_US_DIR}",
            str(EXPECTED_INTERPRETER),
            "scripts/first_estimates_birth_evidence.py",
            *arguments,
        )
    )


def _validate_loaded_draw(
    *,
    inputs: Any,
    phase: Any,
    draw: Any,
    draw_index: int,
) -> FirstReportProjectionDraw:
    if not isinstance(draw, FirstReportProjectionDraw):
        raise TypeError(
            "draw cache does not contain FirstReportProjectionDraw"
        )
    expected_root = runner.DRAW_ROOT_SEEDS[draw_index]
    if draw.draw_index != draw_index or draw.root_seed != expected_root:
        raise ValueError(
            "draw identity mismatch: "
            f"index/root={draw.draw_index}/{draw.root_seed}, "
            f"expected={draw_index}/{expected_root}"
        )
    if getattr(draw.projection, "draw_index", None) != draw_index:
        raise ValueError("projection carries the wrong draw index")
    if getattr(phase, "population", None) is None:
        raise TypeError("candidate-3 phase has no population")
    if getattr(inputs, "refit_inputs", None) is None:
        raise TypeError("cached inputs have no refit inputs")
    runner._assert_phase_lineage(phase)
    return draw


def _load_cached_draw(path: Path, draw_index: int) -> LoadedDraw:
    if draw_index != 0:
        raise ValueError("the available diagnostic cache contains only draw 0")
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"draw cache is absent: {resolved}")
    digest = _sha256(resolved)
    if digest != DEFAULT_CACHE_SHA256:
        raise RuntimeError(
            f"draw cache sha256 {digest} != pinned {DEFAULT_CACHE_SHA256}"
        )
    with resolved.open("rb") as stream:
        blob = pickle.load(stream)
    if not isinstance(blob, dict) or set(blob) != {"inputs", "phase", "draw0"}:
        raise TypeError("draw cache must have exactly inputs/phase/draw0")
    draw = _validate_loaded_draw(
        inputs=blob["inputs"],
        phase=blob["phase"],
        draw=blob["draw0"],
        draw_index=draw_index,
    )
    return LoadedDraw(
        inputs=blob["inputs"],
        phase=blob["phase"],
        draw=draw,
        execution={
            "data_path": "diagnostic_pickle_cache",
            "artifact_source": "sha256_pinned_diagnostic_pickle",
            "cache": {
                "path": str(resolved),
                "sha256": digest,
                "size_bytes": resolved.stat().st_size,
            },
            "canonical_artifact_command": _reducer_command(
                "--cache",
                str(resolved),
            ),
            "cache_independent_regeneration_command": _reducer_command(
                "--regenerate"
            ),
            "regeneration_path": (
                "coordinator._load_registered_input_plan plus the registered "
                "scripts path context and the production candidate-3 prefix; "
                "one real draw with wrapper clones (~55 minutes)"
            ),
        },
    )


def _regenerate_draw(
    draw_index: int,
    report_parameters: Any,
) -> LoadedDraw:
    """Replay the probe's production driver with exactly one real draw."""

    plan = coordinator._load_registered_input_plan(ROOT)
    configuration = runner.registered_configuration_echo(
        registration_reference=(
            "manual:first_estimates_birth_evidence:"
            f"{EXPECTED_MASTER_SHA}:draw{draw_index}"
        ),
        parameter_bundle=report_parameters.provenance,
    )
    configuration_bytes = publication.canonical_json_bytes(configuration)
    resolved_contract = coordinator.resolve_report_contract(ROOT)
    base_operations = runner.default_projection_operations()
    real: dict[str, Any] = {}

    def project_one_real_draw(
        phase: Any,
        population: Any,
        wrapper_index: int,
    ) -> tuple[Any, Any]:
        if not real:
            projection, collector = base_operations.project_draw(
                phase,
                population,
                draw_index,
            )
            real["projection"] = projection
            real["collector"] = collector
        projection = real["projection"]
        if getattr(projection, "draw_index", None) != wrapper_index:
            projection = replace(projection, draw_index=wrapper_index)
        return projection, real["collector"]

    operations = replace(
        base_operations,
        project_draw=project_one_real_draw,
    )
    with coordinator._registered_scripts_path(ROOT / "scripts"):
        batch = runner.execute_first_report_projection(
            plan,
            resolved=resolved_contract,
            configuration_echo=configuration,
            registered_configuration_bytes=configuration_bytes,
            operations=operations,
        )
        draw = batch.draws[draw_index]
    draw = _validate_loaded_draw(
        inputs=batch.inputs,
        phase=batch.phase,
        draw=draw,
        draw_index=draw_index,
    )
    return LoadedDraw(
        inputs=batch.inputs,
        phase=batch.phase,
        draw=draw,
        execution={
            "data_path": "regenerated_registered_single_draw",
            "artifact_source": "cache_independent_registered_input_replay",
            "cache": None,
            "canonical_artifact_command": _reducer_command("--regenerate"),
            "cache_independent_regeneration_command": _reducer_command(
                "--regenerate"
            ),
            "regeneration_path": (
                "coordinator._load_registered_input_plan plus the registered "
                "scripts path context and the production candidate-3 prefix; "
                "one real draw with wrapper clones (~55 minutes)"
            ),
        },
    )


def _integer_ids(values: Collection[Any]) -> frozenset[int]:
    return frozenset(int(value) for value in values)


def _zero_filled_counts(
    counts: Mapping[str, int],
    keys: Collection[str],
) -> dict[str, int]:
    return {key: int(counts.get(key, 0)) for key in keys}


def _seed_frame(population: Any) -> pd.DataFrame:
    initial = population.initial_slice.copy()
    if set(initial["anchor_wave"].astype(int)) != {SEED_WAVE}:
        raise AssertionError("initial slice is not entirely at SEED_WAVE")
    if set(initial["year"].astype(int)) != {EARN_ANCHOR_YEAR}:
        raise AssertionError(
            "initial slice is not entirely at EARN_ANCHOR_YEAR"
        )
    frames = [initial]
    for entry_year, frame in sorted(
        population.scheduled_entries_by_year.items()
    ):
        copied = frame.copy()
        if set(copied["anchor_wave"].astype(int)) != {int(entry_year)}:
            raise AssertionError(
                f"scheduled {entry_year} frame has another anchor_wave"
            )
        if set(copied["year"].astype(int)) != {int(entry_year) - 1}:
            raise AssertionError(
                f"scheduled {entry_year} frame is not keyed at year-1"
            )
        frames.append(copied)
    seed = pd.concat(frames, ignore_index=True, sort=False)
    if seed["person_id"].duplicated().any():
        raise AssertionError("seed frames contain duplicate people")
    if not (
        seed["year"].astype(int) == seed["anchor_wave"].astype(int) - 1
    ).all():
        raise AssertionError("seed year differs from anchor_wave - 1")
    if _integer_ids(seed["person_id"]) != _integer_ids(population.holdout_ids):
        raise AssertionError("seed frames do not reconcile to holdout IDs")
    return seed


def _derive_birth_evidence(loaded: LoadedDraw) -> BirthEvidence:
    inputs = loaded.inputs
    population = loaded.phase.population
    trajectory = preparation.concatenate_realized_trajectory(
        loaded.draw.projection
    )
    roster = career.build_population_roster(
        population.initial_slice,
        population.scheduled_entries_by_year,
        trajectory,
    )
    population_ids = _integer_ids(roster["person_id"])
    synthetic = preparation.derive_synthetic_birth_years(
        trajectory,
        population.reserved_real_ids,
    )
    marriage_history = inputs.refit_inputs.family_context.marriage_records
    existing = career.derive_birth_years(
        marriage_history,
        inputs.earnings_panel,
        synthetic,
        required_person_ids=population_ids,
    )
    existing = tuple(
        record for record in existing if record.person_id in population_ids
    )
    birth_year_by_person = {
        record.person_id: record.birth_year for record in existing
    }
    source_by_person = {
        record.person_id: record.source.value for record in existing
    }
    initially_unresolved = population_ids - set(birth_year_by_person)
    seed = _seed_frame(population)
    seed_by_person = seed.set_index("person_id")
    if not seed_by_person.index.is_unique:
        raise AssertionError("seed person index is not unique")
    if not initially_unresolved <= _integer_ids(seed["person_id"]):
        raise AssertionError(
            "a clauses-1/2/synthetic unresolved person has no seed row"
        )

    derived_ids: set[int] = set()
    infant_ids: set[int] = set()
    sentinel_ids: set[int] = set()
    invalid: list[tuple[int, Any]] = []
    for person_id in sorted(initially_unresolved):
        row = seed_by_person.loc[person_id]
        raw_age = row["age"]
        if pd.isna(raw_age) or int(raw_age) == 999:
            sentinel_ids.add(person_id)
            continue
        age = int(raw_age)
        if age == 1:
            infant_ids.add(person_id)
            continue
        if 2 <= age <= 125:
            seed_year = int(row["year"])
            anchor_wave = int(row["anchor_wave"])
            if seed_year != anchor_wave - 1:
                raise AssertionError(
                    f"person {person_id} violates the seed coordinate"
                )
            birth_year = seed_year - age
            if not seed_year - 125 <= birth_year <= seed_year - 2:
                raise AssertionError(
                    f"derived birth year {birth_year} for person {person_id} "
                    "violates its seed-year/age support"
                )
            if not DERIVED_BIRTH_MIN <= birth_year <= DERIVED_BIRTH_MAX:
                raise AssertionError(
                    f"derived birth year {birth_year} for person {person_id} "
                    f"lies outside [{DERIVED_BIRTH_MIN}, {DERIVED_BIRTH_MAX}]"
                )
            derived_ids.add(person_id)
            birth_year_by_person[person_id] = birth_year
            source_by_person[person_id] = "derived_projection_age"
            continue
        invalid.append((person_id, raw_age))
    if invalid:
        raise ValueError(
            "unrecognized PSID seed-age codes: " f"{invalid[:10]}"
        )
    unresolved_ids = set(initially_unresolved) - derived_ids
    if unresolved_ids != infant_ids | sentinel_ids:
        raise AssertionError("unresolved age-code disposition is incomplete")
    for person_id in unresolved_ids:
        source_by_person[person_id] = "unresolved"
    if set(source_by_person) != set(population_ids):
        raise AssertionError(
            "corrected source classes do not cover population"
        )

    initially_unresolved_counts = Counter(
        source_by_person[person_id] for person_id in initially_unresolved
    )
    whole_counts = Counter(source_by_person.values())
    derived_years = [
        birth_year_by_person[person_id] for person_id in sorted(derived_ids)
    ]
    by_seed_part = {
        "initial_slice": len(
            initially_unresolved
            & _integer_ids(population.initial_slice["person_id"])
        ),
        **{
            f"scheduled_{year}": len(
                initially_unresolved & _integer_ids(frame["person_id"])
            )
            for year, frame in sorted(
                population.scheduled_entries_by_year.items()
            )
        },
    }
    result = {
        "draw_invariant_by_construction": True,
        "draw_invariance_reason": (
            "Clause 3 reads only phase.population initial/scheduled seed "
            "frames built before projection mortality and RNG; it reads no "
            "trajectory row."
        ),
        "seed_coordinate": {
            "formula": (
                "birth_year = seed_year - seed_age = "
                "(anchor_wave - 1) - collection_wave_age"
            ),
            "age_semantics": (
                "Raw PSID age code from the person's collection-wave "
                "anchor interview."
            ),
            "anchor_wave_semantics": (
                "Earliest gated start-wave interview at which the person "
                "is present with positive weight."
            ),
            "seed_year_semantics": (
                "Reference year immediately before anchor_wave; initial "
                "2015 anchors use EARN_ANCHOR_YEAR 2014, scheduled 2017/2019 "
                "anchors use 2016/2018."
            ),
            "earn_anchor_year": EARN_ANCHOR_YEAR,
            "seed_wave": SEED_WAVE,
            "derived_birth_asserted_bounds": [
                DERIVED_BIRTH_MIN,
                DERIVED_BIRTH_MAX,
            ],
            "derived_birth_observed_range": [
                min(derived_years),
                max(derived_years),
            ],
            "derived_birth_per_row_assertion": {
                "asserted_rows": len(derived_ids),
                "rule": ("seed_year - 125 <= birth_year <= seed_year - 2"),
                "passed": True,
            },
        },
        "seed_population": {
            "initial_slice": len(population.initial_slice),
            "scheduled_entries": {
                str(year): len(frame)
                for year, frame in sorted(
                    population.scheduled_entries_by_year.items()
                )
            },
            "real_seed_people": len(seed),
            "synthetic_people": len(synthetic),
            "whole_report_population": len(population_ids),
        },
        "initially_unresolved": {
            "count": len(initially_unresolved),
            "by_seed_part": by_seed_part,
            "age_code_counts": {
                "actual_age_2_125": len(derived_ids),
                "unresolved_infant_code": len(infant_ids),
                "unresolved_sentinel": len(sentinel_ids),
            },
            "corrected_counts_by_class": _zero_filled_counts(
                initially_unresolved_counts,
                SOURCE_CLASSES,
            ),
        },
        "whole_population": {
            "count": len(population_ids),
            "counts_by_class": _zero_filled_counts(
                whole_counts,
                SOURCE_CLASSES,
            ),
        },
    }
    return BirthEvidence(
        trajectory=trajectory,
        roster=roster,
        synthetic_birth_years=synthetic,
        population_ids=population_ids,
        seed=seed,
        birth_year_by_person=dict(birth_year_by_person),
        source_by_person=dict(source_by_person),
        initially_unresolved_ids=frozenset(initially_unresolved),
        derived_ids=frozenset(derived_ids),
        unresolved_ids=frozenset(unresolved_ids),
        infant_code_ids=frozenset(infant_ids),
        sentinel_ids=frozenset(sentinel_ids),
        result=result,
    )


def _mcnemar_tests(
    clause2_only: int,
    clause3_only: int,
) -> Mapping[str, Any]:
    discordant = clause2_only + clause3_only
    if discordant:
        smaller = min(clause2_only, clause3_only)
        exact_tail = sum(
            math.comb(discordant, value) for value in range(smaller + 1)
        )
        exact_p = min(1.0, 2.0 * exact_tail / (2**discordant))
        corrected_difference = max(
            abs(clause2_only - clause3_only) - 1,
            0,
        )
        corrected_statistic = corrected_difference**2 / discordant
        corrected_p = math.erfc(math.sqrt(corrected_statistic / 2.0))
    else:
        exact_p = 1.0
        corrected_statistic = 0.0
        corrected_p = 1.0
    return {
        "exact_two_sided_binomial": {
            "method": (
                "Two-sided exact McNemar test: binomial test on discordant "
                "pairs with null probability 0.5."
            ),
            "p_value": exact_p,
        },
        "chi_square_continuity_corrected": {
            "method": (
                "McNemar chi-square test with Edwards continuity correction "
                "and one degree of freedom."
            ),
            "statistic": corrected_statistic,
            "p_value": corrected_p,
        },
    }


def _agreement_table(
    *,
    people: Collection[int],
    exact_by_person: Mapping[int, int],
    clause2_by_person: Mapping[int, int],
    clause3_by_person: Mapping[int, int],
    tolerance: int,
) -> Mapping[str, Any]:
    person_ids = tuple(sorted(people))
    clause2_matches = {
        person_id
        for person_id in person_ids
        if (
            abs(clause2_by_person[person_id] - exact_by_person[person_id])
            <= tolerance
        )
    }
    clause3_matches = {
        person_id
        for person_id in person_ids
        if (
            abs(clause3_by_person[person_id] - exact_by_person[person_id])
            <= tolerance
        )
    }
    both = clause2_matches & clause3_matches
    clause2_only = clause2_matches - clause3_matches
    clause3_only = clause3_matches - clause2_matches
    neither = set(person_ids) - clause2_matches - clause3_matches
    cells = {
        "clause2_match__clause3_match": len(both),
        "clause2_match__clause3_mismatch": len(clause2_only),
        "clause2_mismatch__clause3_match": len(clause3_only),
        "clause2_mismatch__clause3_mismatch": len(neither),
    }
    if sum(cells.values()) != len(person_ids):
        raise AssertionError("agreement cells do not cover common support")
    return {
        "denominator": len(person_ids),
        "clause2_inferred_period_age": {
            "match_count": len(clause2_matches),
            "match_share": (
                len(clause2_matches) / len(person_ids) if person_ids else 0.0
            ),
        },
        "clause3_seed_age": {
            "match_count": len(clause3_matches),
            "match_share": (
                len(clause3_matches) / len(person_ids) if person_ids else 0.0
            ),
        },
        "mcnemar_2x2_cells": cells,
        "discordant_pairs": {
            "clause2_only": len(clause2_only),
            "clause3_only": len(clause3_only),
        },
        "paired_tests": _mcnemar_tests(
            len(clause2_only),
            len(clause3_only),
        ),
    }


def _derive_common_support_agreement(
    loaded: LoadedDraw,
    births: BirthEvidence,
) -> Mapping[str, Any]:
    marriage = loaded.inputs.refit_inputs.family_context.marriage_records
    earnings = loaded.inputs.earnings_panel
    exact_records = career.derive_birth_years(
        marriage,
        earnings.iloc[0:0].copy(),
        {},
        required_person_ids=births.population_ids,
    )
    clause2_records = career.derive_birth_years(
        marriage.iloc[0:0].copy(),
        earnings,
        {},
        required_person_ids=births.population_ids,
    )
    exact_by_person = {
        record.person_id: record.birth_year
        for record in exact_records
        if record.person_id in births.population_ids
    }
    clause2_by_person = {
        record.person_id: record.birth_year
        for record in clause2_records
        if record.person_id in births.population_ids
    }
    clause3_by_person: dict[int, int] = {}
    anchor_wave_by_person: dict[int, int] = {}
    for row in births.seed.itertuples():
        if pd.isna(row.age):
            continue
        age = int(row.age)
        if not 2 <= age <= 125:
            continue
        person_id = int(row.person_id)
        seed_year = int(row.year)
        anchor_wave = int(row.anchor_wave)
        if seed_year != anchor_wave - 1:
            raise AssertionError(
                f"agreement seed coordinate differs for {person_id}"
            )
        clause3_by_person[person_id] = seed_year - age
        anchor_wave_by_person[person_id] = anchor_wave

    common_support = frozenset(
        set(exact_by_person) & set(clause2_by_person) & set(clause3_by_person)
    )
    exact = _agreement_table(
        people=common_support,
        exact_by_person=exact_by_person,
        clause2_by_person=clause2_by_person,
        clause3_by_person=clause3_by_person,
        tolerance=0,
    )
    within_one = _agreement_table(
        people=common_support,
        exact_by_person=exact_by_person,
        clause2_by_person=clause2_by_person,
        clause3_by_person=clause3_by_person,
        tolerance=1,
    )
    by_anchor_wave = {
        str(anchor_wave): _agreement_table(
            people={
                person_id
                for person_id in common_support
                if anchor_wave_by_person[person_id] == anchor_wave
            },
            exact_by_person=exact_by_person,
            clause2_by_person=clause2_by_person,
            clause3_by_person=clause3_by_person,
            tolerance=0,
        )
        for anchor_wave in sorted(
            {anchor_wave_by_person[person_id] for person_id in common_support}
        )
    }
    anchor_total = sum(
        table["denominator"] for table in by_anchor_wave.values()
    )
    if anchor_total != len(common_support):
        raise AssertionError("anchor strata do not cover common support")
    return {
        "construction": "seed_triple_overlap",
        "common_support_definition": (
            "Real report-population people with an exact marriage-record "
            "birth year, a clause-2 median(period-age) estimate on age "
            "14-90 earnings support, and a valid clause-3 seed age 2-125."
        ),
        "truth_source": "exact_marriage",
        "common_support_count": len(common_support),
        "endpoints": {
            "exact": exact,
            "within_plus_or_minus_1": within_one,
        },
        "exact_endpoint_by_anchor_wave": by_anchor_wave,
        "anchor_strata_reconciliation": {
            "sum": anchor_total,
            "common_support_count": len(common_support),
            "passed": anchor_total == len(common_support),
        },
    }


def _derive_revenue_person_year_evidence(
    births: BirthEvidence,
) -> Mapping[str, Any]:
    if births.derived_ids & births.unresolved_ids:
        raise AssertionError("revenue birth-source groups overlap")
    window = births.trajectory[
        births.trajectory["year"].isin(ledgers.REPORT_YEARS)
    ].copy()
    if window.duplicated(["person_id", "year"]).any():
        raise AssertionError("revenue evidence has duplicate person-years")

    def group(person_ids: frozenset[int]) -> Mapping[str, Any]:
        rows = window[window["person_id"].isin(person_ids)]
        zero_rows = rows["earnings"].notna() & rows["earnings"].eq(0)
        if not bool(zero_rows.all()):
            raise AssertionError(
                "birth-source revenue rows are not all explicit zero earnings"
            )
        return {
            "people": len(person_ids),
            "in_window_rows": len(rows),
            "zero_earnings_rows": int(zero_rows.sum()),
        }

    derived = group(births.derived_ids)
    unresolved = group(births.unresolved_ids)
    combined_ids = births.derived_ids | births.unresolved_ids
    combined = group(combined_ids)
    people_sum = derived["people"] + unresolved["people"]
    row_sum = derived["in_window_rows"] + unresolved["in_window_rows"]
    zero_sum = derived["zero_earnings_rows"] + unresolved["zero_earnings_rows"]
    passed = (
        people_sum == combined["people"]
        and row_sum == combined["in_window_rows"]
        and zero_sum == combined["zero_earnings_rows"]
    )
    if not passed:
        raise AssertionError(
            "revenue person-year partition does not reconcile"
        )
    return {
        "production_semantics": (
            "Revenue is birth-independent: ledgers.build_revenue_ledger "
            "consumes the unsplit projection directly and does not consume "
            "birth-year classifications."
        ),
        "report_years": list(ledgers.REPORT_YEARS),
        "groups": {
            "derived_projection_age": derived,
            "unresolved": unresolved,
            "combined": combined,
        },
        "reconciliation": {
            "people_sum": people_sum,
            "in_window_rows_sum": row_sum,
            "zero_earnings_rows_sum": zero_sum,
            "passed": passed,
        },
    }


def _production_candidate_inclusion(
    *,
    loaded: LoadedDraw,
    births: BirthEvidence,
    candidate_ids: frozenset[int],
    birth_year_by_person: Mapping[int, int],
    claiming_schedule: Any,
) -> career.InclusionResult:
    """Transport explicit births into the unmodified production Stage C/D."""

    if set(birth_year_by_person) != set(candidate_ids):
        raise AssertionError(
            "production birth transport is not candidate-total"
        )
    transport = pd.DataFrame(
        {
            "person_id": sorted(candidate_ids),
            "birth_year": [
                int(birth_year_by_person[person_id])
                for person_id in sorted(candidate_ids)
            ],
        }
    )
    candidate_trajectory = births.trajectory[
        births.trajectory["person_id"].isin(candidate_ids)
    ].copy()
    candidate_roster = births.roster[
        births.roster["person_id"].isin(candidate_ids)
    ].copy()
    result = career.build_career_inclusion(
        trajectory=candidate_trajectory,
        population_roster=candidate_roster,
        observed_earnings=loaded.inputs.earnings_panel,
        marriage_history=transport,
        synthetic_birth_years={},
        claiming_schedule=claiming_schedule,
        earnings_domain_ids=loaded.phase.population.earnings_domain_ids,
        stock_imputation_root_seed=runner.STOCK_IMPUTATION_ROOT_SEED,
        projection_start_year=runner.PROJECTION_START_YEAR,
    )
    observed_origins = {record.person_id for record in result.origins}
    if observed_origins != set(candidate_ids):
        raise AssertionError(
            "production origin partition is not candidate-total"
        )
    if result.nonclaimants:
        raise AssertionError("candidate-only production run made nonclaimants")
    if any(
        record.classification is not career.DIClass.NON_DI
        for record in result.di_partition
    ):
        raise AssertionError("candidate-only production run changed Stage A")
    outcome_ids = {
        *(record.person_id for record in result.exclusions),
        *(record.person_id for record in result.included),
    }
    if outcome_ids != set(candidate_ids):
        raise AssertionError("production Stage D is not candidate-total")
    return result


def _derive_funnel_evidence(
    loaded: LoadedDraw,
    births: BirthEvidence,
) -> FunnelEvidence:
    population = loaded.phase.population
    di_records = career.classify_di_trajectory(
        births.trajectory,
        projection_start_year=runner.PROJECTION_START_YEAR,
        population_ids=births.population_ids,
    )
    di_by_person = {
        record.person_id: record.classification.value for record in di_records
    }
    if set(di_by_person) != set(births.population_ids):
        raise AssertionError("full-population DI partition is incomplete")
    raw_carriers = _integer_ids(
        births.trajectory.loc[
            births.trajectory["claim_year"].notna(),
            "person_id",
        ]
    )
    candidate_ids = frozenset(
        person_id
        for person_id in raw_carriers
        if di_by_person[person_id] == career.DIClass.NON_DI.value
    )
    if candidate_ids & births.unresolved_ids:
        raise RuntimeError(
            "a Stage-B candidate remains unresolved after corrected clause 3"
        )
    domain_ids = _integer_ids(population.earnings_domain_ids)
    claiming_schedule = preparation.reconstruct_claiming_schedule(
        loaded.inputs
    )
    candidate_births = {
        person_id: births.birth_year_by_person[person_id]
        for person_id in candidate_ids
    }
    baseline = _production_candidate_inclusion(
        loaded=loaded,
        births=births,
        candidate_ids=candidate_ids,
        birth_year_by_person=candidate_births,
        claiming_schedule=claiming_schedule,
    )

    initially_unresolved_carriers = (
        raw_carriers & births.initially_unresolved_ids
    )
    initially_unresolved_di = Counter(
        di_by_person[person_id] for person_id in initially_unresolved_carriers
    )
    newly_dated_candidates = candidate_ids & births.derived_ids
    origins = {record.person_id: record for record in baseline.origins}
    exclusion_reason = {
        record.person_id: record.reason for record in baseline.exclusions
    }
    included_ids = {record.person_id for record in baseline.included}
    new_origin_counts = Counter(
        origins[person_id].origin.value for person_id in newly_dated_candidates
    )
    new_stage_d_counts = Counter(
        (
            "included"
            if person_id in included_ids
            else exclusion_reason[person_id]
        )
        for person_id in newly_dated_candidates
    )
    canonical_origin_counts = Counter(
        record.origin.value for record in baseline.origins
    )
    candidate_source_counts = Counter(
        births.source_by_person[person_id] for person_id in candidate_ids
    )
    result = {
        "stage_a_rule": (
            "Ever True di_converted; otherwise any missing extant "
            "post-2014 DI observation; otherwise non-DI."
        ),
        "stage_b_rule": (
            "Among non-DI people, any non-null claim_year in any extant "
            "trajectory slice."
        ),
        "initially_unresolved_raw_claim_year_carriers": {
            "count": len(initially_unresolved_carriers),
            "di_partition": _zero_filled_counts(
                initially_unresolved_di,
                DI_CLASSES,
            ),
            "true_stage_b_candidates": len(
                initially_unresolved_carriers & candidate_ids
            ),
            "still_unresolved_after_clause_3": len(
                initially_unresolved_carriers & births.unresolved_ids
            ),
        },
        "newly_dated_stage_b_candidates": {
            "count": len(newly_dated_candidates),
            "origin_counts": _zero_filled_counts(
                new_origin_counts,
                tuple(origin.value for origin in career.ClaimOrigin),
            ),
            "ordered_stage_d_landing": dict(
                sorted(new_stage_d_counts.items())
            ),
        },
        "canonical_candidates": {
            "count": len(candidate_ids),
            "domain_resident": len(candidate_ids & domain_ids),
            "counts_by_birth_source": _zero_filled_counts(
                candidate_source_counts,
                SOURCE_CLASSES,
            ),
            "origin_counts": _zero_filled_counts(
                canonical_origin_counts,
                tuple(origin.value for origin in career.ClaimOrigin),
            ),
        },
        "production_transport": {
            "method": (
                "Run career.build_career_inclusion on the canonical candidate "
                "universe with an explicit one-row birth transport. This "
                "exercises unmodified production Stage C, opening-stock draw, "
                "career construction, and ordered Stage D. Original birth "
                "source labels are retained externally."
            ),
            "why_candidate_universe_only": (
                "The 2,315 residual unresolved people are noncandidates and "
                "master's whole-population birth guard intentionally fails on "
                "them; all 3,083 canonical candidates have corrected births."
            ),
        },
    }
    return FunnelEvidence(
        di_by_person=di_by_person,
        raw_claim_year_carrier_ids=raw_carriers,
        candidate_ids=candidate_ids,
        domain_ids=domain_ids,
        claiming_schedule=claiming_schedule,
        baseline_inclusion=baseline,
        result=result,
    )


def _outcome_counts(
    inclusion: career.InclusionResult,
) -> Counter[str]:
    counts: Counter[str] = Counter(
        record.reason for record in inclusion.exclusions
    )
    counts["included"] = len(inclusion.included)
    return counts


def _source_split(
    person_ids: Collection[int],
    source_by_person: Mapping[int, str],
) -> dict[str, int]:
    counts = Counter(
        source_by_person[int(person_id)] for person_id in person_ids
    )
    return _zero_filled_counts(counts, SOURCE_CLASSES)


def _origin_split(
    person_ids: Collection[int],
    origins_by_person: Mapping[int, career.CandidateOriginRecord],
) -> dict[str, int]:
    counts = Counter(
        origins_by_person[int(person_id)].origin.value
        for person_id in person_ids
    )
    return _zero_filled_counts(
        counts,
        tuple(origin.value for origin in career.ClaimOrigin),
    )


def _neutral_inclusion_changes(
    person_ids: Collection[int],
    baseline: CandidateStageState,
    alternative: CandidateStageState,
) -> Mapping[str, Any]:
    inbound = [
        person_id
        for person_id in person_ids
        if (
            person_id not in baseline.included_ids
            and person_id in alternative.included_ids
        )
    ]
    outbound = [
        person_id
        for person_id in person_ids
        if (
            person_id in baseline.included_ids
            and person_id not in alternative.included_ids
        )
    ]
    if len(inbound) + len(outbound) != len(person_ids):
        raise AssertionError(
            "neutral inclusion-change split does not cover changed people"
        )
    return {
        "inbound_to_included": {
            "count": len(inbound),
            "baseline_outcomes": dict(
                sorted(
                    Counter(
                        baseline.outcome_by_person[person_id]
                        for person_id in inbound
                    ).items()
                )
            ),
        },
        "outbound_from_included": {
            "count": len(outbound),
            "alternative_outcomes": dict(
                sorted(
                    Counter(
                        alternative.outcome_by_person[person_id]
                        for person_id in outbound
                    ).items()
                )
            ),
        },
    }


def _stage_d_source_split(
    inclusion: career.InclusionResult,
    source_by_person: Mapping[int, str],
) -> dict[str, dict[str, int]]:
    outcome_by_person = {
        **{record.person_id: record.reason for record in inclusion.exclusions},
        **{record.person_id: "included" for record in inclusion.included},
    }
    return {
        source: _zero_filled_counts(
            Counter(
                outcome
                for person_id, outcome in outcome_by_person.items()
                if source_by_person[person_id] == source
            ),
            STAGE_D_OUTCOMES,
        )
        for source in SOURCE_CLASSES
    }


def _candidate_stage_state(
    *,
    inclusion: career.InclusionResult,
    birth_year_by_person: Mapping[int, int],
    domain_ids: frozenset[int],
) -> CandidateStageState:
    """Extract predicates and prove they reproduce production's first failure."""

    origins = {record.person_id: record for record in inclusion.origins}
    included = {record.person_id: record for record in inclusion.included}
    exclusions = {record.person_id: record for record in inclusion.exclusions}
    people = set(origins)
    if set(birth_year_by_person) != people:
        raise AssertionError("candidate state birth map is incomplete")
    if set(included) | set(exclusions) != people:
        raise AssertionError("candidate state outcomes are incomplete")
    if set(included) & set(exclusions):
        raise AssertionError("candidate state outcomes overlap")

    outcome_by_person: dict[int, str] = {}
    predicate_values: dict[int, dict[str, bool]] = {}
    predicate_reached: dict[int, dict[str, bool]] = {}
    for person_id in sorted(people):
        birth_year = int(birth_year_by_person[person_id])
        origin = origins[person_id]
        eligibility_year = birth_year + 62
        coverage_start = max(
            career.OBSERVED_START_YEAR,
            birth_year + 22,
        )
        coverage_end = min(
            origin.operative_claim_year,
            career.PROJECTED_END_YEAR,
        )
        domain_complete = person_id in domain_ids
        era = eligibility_year >= career.MIN_ELIGIBILITY_YEAR
        nonempty_span = coverage_start <= coverage_end
        chronology = eligibility_year <= origin.operative_claim_year

        coverage_ratio: float | None
        if person_id in included:
            coverage_ratio = included[person_id].career.coverage_ratio
        else:
            coverage_ratio = exclusions[person_id].coverage_ratio
        coverage = bool(
            coverage_ratio is not None
            and coverage_ratio >= career.COVERAGE_THRESHOLD
        )
        reached = {
            "domain_complete": True,
            "eligibility_era": domain_complete,
            "nonempty_span": domain_complete and era,
            "chronology": domain_complete and era and nonempty_span,
            "coverage": (
                domain_complete and era and nonempty_span and chronology
            ),
        }
        values = {
            "domain_complete": domain_complete,
            "eligibility_era": era,
            "nonempty_span": nonempty_span,
            "chronology": chronology,
            "coverage": coverage,
        }
        if reached["coverage"] and coverage_ratio is None:
            raise AssertionError(
                f"production did not evaluate coverage for {person_id}"
            )

        if not domain_complete:
            reconstructed = "excluded_domain_incomplete"
        elif not era:
            reconstructed = "excluded_pre1979_eligibility"
        elif not nonempty_span:
            reconstructed = "excluded_empty_span"
        elif not chronology:
            reconstructed = "excluded_chronology_inconsistent"
        elif not coverage:
            reconstructed = "excluded_low_coverage"
        else:
            reconstructed = "included"
        observed = (
            "included"
            if person_id in included
            else exclusions[person_id].reason
        )
        if reconstructed != observed:
            raise AssertionError(
                "predicate extraction differs from production for "
                f"{person_id}: {reconstructed} != {observed}"
            )
        outcome_by_person[person_id] = observed
        predicate_values[person_id] = values
        predicate_reached[person_id] = reached

    return CandidateStageState(
        outcome_by_person=outcome_by_person,
        included_ids=frozenset(included),
        predicate_value_by_person=predicate_values,
        predicate_reached_by_person=predicate_reached,
    )


def _direction_name(shift: int) -> str:
    return {
        -1: "birth_minus_1",
        0: "baseline",
        1: "birth_plus_1",
    }[shift]


def _transition_counts(
    baseline: CandidateStageState,
    alternative: CandidateStageState,
) -> dict[str, int]:
    counts = Counter(
        (
            f"{baseline.outcome_by_person[person_id]}"
            f"__to__{alternative.outcome_by_person[person_id]}"
        )
        for person_id in baseline.outcome_by_person
        if (
            baseline.outcome_by_person[person_id]
            != alternative.outcome_by_person[person_id]
        )
    )
    return dict(sorted(counts.items()))


def _derive_sensitivity_evidence(
    *,
    loaded: LoadedDraw,
    births: BirthEvidence,
    funnel: FunnelEvidence,
) -> SensitivityEvidence:
    baseline_births = {
        person_id: int(births.birth_year_by_person[person_id])
        for person_id in funnel.candidate_ids
    }
    birth_maps: dict[int, dict[int, int]] = {0: baseline_births}
    inclusions: dict[int, career.InclusionResult] = {
        0: funnel.baseline_inclusion
    }
    for shift in (-1, 1):
        shifted = {
            person_id: (
                birth_year + shift
                if births.source_by_person[person_id]
                in IMPRECISE_BIRTH_SOURCES
                else birth_year
            )
            for person_id, birth_year in baseline_births.items()
        }
        birth_maps[shift] = shifted
        inclusions[shift] = _production_candidate_inclusion(
            loaded=loaded,
            births=births,
            candidate_ids=funnel.candidate_ids,
            birth_year_by_person=shifted,
            claiming_schedule=funnel.claiming_schedule,
        )

    states = {
        shift: _candidate_stage_state(
            inclusion=inclusion,
            birth_year_by_person=birth_maps[shift],
            domain_ids=funnel.domain_ids,
        )
        for shift, inclusion in inclusions.items()
    }
    baseline_state = states[0]
    baseline_origins = {
        record.person_id: record for record in inclusions[0].origins
    }

    scenario_results: dict[str, Any] = {}
    for shift in (0, -1, 1):
        name = _direction_name(shift)
        inclusion = inclusions[shift]
        state = states[shift]
        origins = {record.person_id: record for record in inclusion.origins}
        if {
            person_id: record.origin for person_id, record in origins.items()
        } != {
            person_id: record.origin
            for person_id, record in baseline_origins.items()
        }:
            raise AssertionError("birth perturbation changed the origin class")
        coordinate_changes = {
            "operative_claim_age": sum(
                origins[person_id].operative_claim_age
                != baseline_origins[person_id].operative_claim_age
                for person_id in origins
            ),
            "operative_claim_year": sum(
                origins[person_id].operative_claim_year
                != baseline_origins[person_id].operative_claim_year
                for person_id in origins
            ),
            "schedule_year": sum(
                origins[person_id].schedule_year
                != baseline_origins[person_id].schedule_year
                for person_id in origins
            ),
        }
        scenario_results[name] = {
            "ordered_stage_d_counts": _zero_filled_counts(
                _outcome_counts(inclusion),
                STAGE_D_OUTCOMES,
            ),
            "ordered_stage_d_counts_by_birth_source": (
                _stage_d_source_split(
                    inclusion,
                    births.source_by_person,
                )
            ),
            "stage_c_coordinate_changes_from_baseline": coordinate_changes,
            "ordered_outcome_transitions_from_baseline": (
                {} if shift == 0 else _transition_counts(baseline_state, state)
            ),
        }

    predicate_results: dict[str, Any] = {}
    for predicate in STAGE_D_PREDICATES:
        aggregate_flips: list[int] = []
        aggregate_inclusion_flips: list[int] = []
        by_direction: dict[str, Any] = {}
        for shift in (-1, 1):
            alternative = states[shift]
            flipped = [
                person_id
                for person_id in sorted(funnel.candidate_ids)
                if (
                    baseline_state.predicate_reached_by_person[person_id][
                        predicate
                    ]
                    and alternative.predicate_reached_by_person[person_id][
                        predicate
                    ]
                    and (
                        baseline_state.predicate_value_by_person[person_id][
                            predicate
                        ]
                        != alternative.predicate_value_by_person[person_id][
                            predicate
                        ]
                    )
                )
            ]
            inclusion_flipped = [
                person_id
                for person_id in flipped
                if (
                    (person_id in baseline_state.included_ids)
                    != (person_id in alternative.included_ids)
                )
            ]
            aggregate_flips.extend(flipped)
            aggregate_inclusion_flips.extend(inclusion_flipped)
            by_direction[_direction_name(shift)] = {
                "flip_count": len(flipped),
                "flip_count_by_birth_source": _source_split(
                    flipped,
                    births.source_by_person,
                ),
                "flip_count_by_origin": _origin_split(
                    flipped,
                    baseline_origins,
                ),
                "inclusion_changing_flip_count": len(inclusion_flipped),
                "inclusion_changing_flip_count_by_birth_source": (
                    _source_split(
                        inclusion_flipped,
                        births.source_by_person,
                    )
                ),
                "inclusion_changing_flip_count_by_origin": _origin_split(
                    inclusion_flipped,
                    baseline_origins,
                ),
                "neutral_inclusion_changes": _neutral_inclusion_changes(
                    inclusion_flipped,
                    baseline_state,
                    alternative,
                ),
            }
        distinct = frozenset(aggregate_flips)
        distinct_inclusion = frozenset(aggregate_inclusion_flips)
        predicate_results[predicate] = {
            "directions": by_direction,
            "flip_directions": len(aggregate_flips),
            "flip_directions_by_birth_source": _source_split(
                aggregate_flips,
                births.source_by_person,
            ),
            "inclusion_changing_flip_directions": len(
                aggregate_inclusion_flips
            ),
            "inclusion_changing_flip_directions_by_birth_source": (
                _source_split(
                    aggregate_inclusion_flips,
                    births.source_by_person,
                )
            ),
            "distinct_people_affected": len(distinct),
            "distinct_people_affected_by_birth_source": _source_split(
                distinct,
                births.source_by_person,
            ),
            "distinct_people_with_inclusion_change": len(distinct_inclusion),
            "distinct_people_with_inclusion_change_by_birth_source": (
                _source_split(
                    distinct_inclusion,
                    births.source_by_person,
                )
            ),
        }

    chronology_flip_ids = [
        person_id
        for shift in (-1, 1)
        for person_id in sorted(funnel.candidate_ids)
        if (
            baseline_state.predicate_reached_by_person[person_id]["chronology"]
            and states[shift].predicate_reached_by_person[person_id][
                "chronology"
            ]
            and (
                baseline_state.predicate_value_by_person[person_id][
                    "chronology"
                ]
                != states[shift].predicate_value_by_person[person_id][
                    "chronology"
                ]
            )
        )
    ]
    chronology_origin_counts = _origin_split(
        chronology_flip_ids,
        baseline_origins,
    )
    chronology_origin_assertion_passed = (
        chronology_origin_counts[career.ClaimOrigin.MODELED_AWARD.value]
        == len(chronology_flip_ids)
        and chronology_origin_counts[career.ClaimOrigin.OPENING_BACKFILL.value]
        == 0
    )
    if not chronology_origin_assertion_passed:
        raise AssertionError(
            "a chronology predicate flip has a non-modeled-award origin"
        )
    predicate_results["chronology"]["origin_assertion"] = {
        "assertion": "Every measured chronology predicate flip is modeled_award.",
        "asserted_flip_directions": len(chronology_flip_ids),
        "observed_counts_by_origin": chronology_origin_counts,
        "passed": chronology_origin_assertion_passed,
    }

    overall_direction_ids: dict[int, list[int]] = {}
    all_overall_directions: list[int] = []
    for shift in (-1, 1):
        alternative = states[shift]
        changed = [
            person_id
            for person_id in sorted(funnel.candidate_ids)
            if (
                (person_id in baseline_state.included_ids)
                != (person_id in alternative.included_ids)
            )
        ]
        overall_direction_ids[shift] = changed
        all_overall_directions.extend(changed)
    distinct_overall = frozenset(all_overall_directions)
    overall = {
        "directions": {
            _direction_name(shift): {
                "inclusion_flip_count": len(person_ids),
                "inclusion_flip_count_by_birth_source": _source_split(
                    person_ids,
                    births.source_by_person,
                ),
                "neutral_inclusion_changes": _neutral_inclusion_changes(
                    person_ids,
                    baseline_state,
                    states[shift],
                ),
            }
            for shift, person_ids in overall_direction_ids.items()
        },
        "inclusion_flip_directions": len(all_overall_directions),
        "inclusion_flip_directions_by_birth_source": _source_split(
            all_overall_directions,
            births.source_by_person,
        ),
        "distinct_people_affected": len(distinct_overall),
        "distinct_people_affected_by_birth_source": _source_split(
            distinct_overall,
            births.source_by_person,
        ),
    }
    result = {
        "perturbation": {
            "values": [-1, 1],
            "scope": sorted(IMPRECISE_BIRTH_SOURCES),
            "fixed_sources": sorted(
                set(SOURCE_CLASSES)
                - set(IMPRECISE_BIRTH_SOURCES)
                - {"unresolved"}
            ),
            "production_path": (
                "Each coordinate re-runs career.build_career_inclusion, "
                "including the opening-stock PMF lookup at birth+62, the "
                "person-keyed draw, operative claim year, career build, and "
                "ordered Stage D."
            ),
            "predicate_flip_definition": (
                "Compare a predicate only when both baseline and alternative "
                "coordinates reach it under ordered Stage D."
            ),
        },
        "scenarios": scenario_results,
        "predicates": predicate_results,
        "overall_inclusion": overall,
    }
    return SensitivityEvidence(
        inclusions=inclusions,
        birth_maps=birth_maps,
        states=states,
        result=result,
    )


def _annualized_benefits_by_year(
    benefit_ledger: ledgers.BenefitLedger,
) -> dict[int, float]:
    result = {
        year: math.fsum(
            row.frame_annualized_benefit
            for row in benefit_ledger.annual_rows
            if row.year == year
        )
        for year in ledgers.REPORT_YEARS
    }
    observed_cells = Counter(row.year for row in benefit_ledger.annual_rows)
    if observed_cells != Counter(
        {year: len(ledgers.BENEFIT_ORIGINS) for year in ledgers.REPORT_YEARS}
    ):
        raise AssertionError("benefit ledger annual cells are incomplete")
    return result


def _benefit_amount_by_person(
    benefit_ledger: ledgers.BenefitLedger,
) -> dict[int, float]:
    return {
        int(row.person_id): math.fsum(
            12.0 * row.weight * row.payment_monthly_by_year[year]
            for year in sorted(row.payment_monthly_by_year)
        )
        for row in benefit_ledger.people
    }


def _derive_ledger_evidence(
    *,
    report_parameters: parameter_module.ReportParameters,
    draw_index: int,
    births: BirthEvidence,
    sensitivity: SensitivityEvidence,
) -> LedgerEvidence:
    """Price coherent shifts and independent personwise adversarial choices."""

    full_ledgers = {
        shift: ledgers.build_benefit_ledger(
            sensitivity.inclusions[shift].included,
            report_parameters,
            draw_index=draw_index,
        )
        for shift in (0, -1, 1)
    }
    full_annual_by_shift = {
        shift: _annualized_benefits_by_year(full_ledgers[shift])
        for shift in (0, -1, 1)
    }
    full_people_by_shift = {
        shift: _benefit_amount_by_person(full_ledgers[shift])
        for shift in (0, -1, 1)
    }
    full_included_ids = {
        shift: frozenset(int(row.person_id) for row in ledger.people)
        for shift, ledger in full_ledgers.items()
    }
    for shift in (0, -1, 1):
        expected_ids = frozenset(
            int(row.person_id)
            for row in sensitivity.inclusions[shift].included
        )
        if full_included_ids[shift] != expected_ids:
            raise AssertionError(
                "full scenario ledger differs from its complete included set"
            )

    baseline_full_annual = full_annual_by_shift[0]
    baseline_full_total = math.fsum(baseline_full_annual.values())
    full_scenarios: dict[str, Any] = {}
    for shift in (0, -1, 1):
        annual = full_annual_by_shift[shift]
        total = math.fsum(annual.values())
        delta_by_year = {
            year: annual[year] - baseline_full_annual[year]
            for year in ledgers.REPORT_YEARS
        }
        delta = total - baseline_full_total
        inbound = full_included_ids[shift] - full_included_ids[0]
        outbound = full_included_ids[0] - full_included_ids[shift]
        reconciled_count = (
            len(full_included_ids[0]) + len(inbound) - len(outbound)
        )
        if reconciled_count != len(full_included_ids[shift]):
            raise AssertionError(
                "full scenario included-set changes do not reconcile"
            )
        person_sum = math.fsum(full_people_by_shift[shift].values())
        full_scenarios[_direction_name(shift)] = {
            "complete_included_set_count": len(full_included_ids[shift]),
            "included_set_changes_from_baseline": {
                "inbound_to_included": len(inbound),
                "outbound_from_included": len(outbound),
                "reconciled_count": reconciled_count,
            },
            "weighted_annualized_benefit_by_year": {
                str(year): {
                    "amount": annual[year],
                    "delta_from_baseline": delta_by_year[year],
                }
                for year in ledgers.REPORT_YEARS
            },
            "weighted_annualized_benefit_total": {
                "amount": total,
                "delta_from_baseline": delta,
                "delta_share_of_baseline": (
                    delta / baseline_full_total if baseline_full_total else 0.0
                ),
                "sum_of_per_year_deltas": math.fsum(delta_by_year.values()),
                "person_contribution_sum": person_sum,
                "person_minus_annual_reconciliation_residual": (
                    person_sum - total
                ),
            },
        }

    all_ledger_person_ids = frozenset().union(
        *(set(values) for values in full_people_by_shift.values())
    )
    baseline_person_sum = math.fsum(
        full_people_by_shift[0].get(person_id, 0.0)
        for person_id in sorted(all_ledger_person_ids)
    )
    personwise_minimum = math.fsum(
        min(
            full_people_by_shift[-1].get(person_id, 0.0),
            full_people_by_shift[1].get(person_id, 0.0),
        )
        for person_id in sorted(all_ledger_person_ids)
    )
    personwise_maximum = math.fsum(
        max(
            full_people_by_shift[-1].get(person_id, 0.0),
            full_people_by_shift[1].get(person_id, 0.0),
        )
        for person_id in sorted(all_ledger_person_ids)
    )
    personwise = {
        "semantics": {
            "allowed_person_birth_shifts": [-1, 1],
            "baseline_shift_zero_is_reference_only": True,
            "shift_scope": sorted(IMPRECISE_BIRTH_SOURCES),
            "fixed_sources": sorted(
                set(SOURCE_CLASSES)
                - set(IMPRECISE_BIRTH_SOURCES)
                - {"unresolved"}
            ),
            "excluded_person_contribution": 0.0,
            "construction": (
                "For each person independently, select the smaller or larger "
                "complete-ledger contribution from birth-minus-1 and "
                "birth-plus-1. Person-keyed production draws and additive "
                "ledger rows make the selections separable."
            ),
        },
        "baseline_reference": {
            "person_contribution_sum": baseline_person_sum,
            "full_scenario_ledger_total": baseline_full_total,
            "person_minus_annual_reconciliation_residual": (
                baseline_person_sum - baseline_full_total
            ),
        },
        "minimum": {
            "amount": personwise_minimum,
            "delta_from_baseline_person_contribution_sum": (
                personwise_minimum - baseline_person_sum
            ),
        },
        "maximum": {
            "amount": personwise_maximum,
            "delta_from_baseline_person_contribution_sum": (
                personwise_maximum - baseline_person_sum
            ),
        },
    }

    baseline_included = {
        row.person_id: row for row in sensitivity.inclusions[0].included
    }
    cohort_ids = frozenset(
        person_id
        for person_id in baseline_included
        if (
            births.source_by_person[person_id]
            == career.BirthSource.INFERRED_PERIOD_AGE.value
        )
    )
    if not cohort_ids:
        raise AssertionError("baseline clause-2 included cohort is empty")
    if any(
        births.source_by_person[person_id]
        != career.BirthSource.INFERRED_PERIOD_AGE.value
        for person_id in cohort_ids
    ):
        raise AssertionError("dollar cohort includes a non-clause-2 source")

    benefit_ledgers: dict[int, ledgers.BenefitLedger] = {}
    retained_ids: dict[int, frozenset[int]] = {}
    for shift in (0, -1, 1):
        included_by_person = {
            row.person_id: row
            for row in sensitivity.inclusions[shift].included
        }
        retained = cohort_ids & set(included_by_person)
        retained_ids[shift] = frozenset(retained)
        benefit_ledgers[shift] = ledgers.build_benefit_ledger(
            (included_by_person[person_id] for person_id in sorted(retained)),
            report_parameters,
            draw_index=draw_index,
        )
        ledger_ids = {
            int(row.person_id) for row in benefit_ledgers[shift].people
        }
        if ledger_ids != retained:
            raise AssertionError(
                "benefit ledger does not contain the retained fixed cohort"
            )
    if retained_ids[0] != cohort_ids:
        raise AssertionError("baseline benefit ledger dropped cohort members")

    annual_by_shift = {
        shift: _annualized_benefits_by_year(benefit_ledgers[shift])
        for shift in (0, -1, 1)
    }
    people_by_shift = {
        shift: {
            int(row.person_id): row for row in benefit_ledgers[shift].people
        }
        for shift in (0, -1, 1)
    }
    baseline_people = people_by_shift[0]
    for person_id, row in baseline_people.items():
        expected_factor = claiming.benefit_factor(
            row.claim_age * 12,
            row.birth_year,
            report_parameters.ssa,
        )
        if expected_factor != row.claim_age_factor:
            raise AssertionError(
                "direct baseline benefit factor differs from the ledger for "
                f"{person_id}"
            )

    payment_change_ids: dict[int, frozenset[int]] = {}
    factor_change_ids: dict[int, frozenset[int]] = {}
    scenarios: dict[str, Any] = {}
    baseline_annual = annual_by_shift[0]
    baseline_total = math.fsum(baseline_annual.values())
    for shift in (-1, 1):
        alternative_people = people_by_shift[shift]
        changed_payment_windows: set[int] = set()
        lost_payment_years: set[int] = set()
        gained_payment_years: set[int] = set()
        fixed_age_factor_changes: set[int] = set()
        for person_id in sorted(cohort_ids):
            baseline_person = baseline_people[person_id]
            baseline_window = frozenset(
                baseline_person.payment_monthly_by_year
            )
            alternative_person = alternative_people.get(person_id)
            alternative_window = (
                frozenset(alternative_person.payment_monthly_by_year)
                if alternative_person is not None
                else frozenset()
            )
            if baseline_window != alternative_window:
                changed_payment_windows.add(person_id)
            if baseline_window - alternative_window:
                lost_payment_years.add(person_id)
            if alternative_window - baseline_window:
                gained_payment_years.add(person_id)

            perturbed_birth_year = sensitivity.birth_maps[shift][person_id]
            if perturbed_birth_year != baseline_person.birth_year + shift:
                raise AssertionError(
                    "clause-2 cohort birth coordinate did not move by "
                    f"{shift:+d} for {person_id}"
                )
            alternative_factor = claiming.benefit_factor(
                baseline_person.claim_age * 12,
                perturbed_birth_year,
                report_parameters.ssa,
            )
            if alternative_factor != baseline_person.claim_age_factor:
                fixed_age_factor_changes.add(person_id)

        payment_change_ids[shift] = frozenset(changed_payment_windows)
        factor_change_ids[shift] = frozenset(fixed_age_factor_changes)
        alternative_annual = annual_by_shift[shift]
        alternative_total = math.fsum(alternative_annual.values())
        delta_by_year = {
            year: alternative_annual[year] - baseline_annual[year]
            for year in ledgers.REPORT_YEARS
        }
        total_delta = alternative_total - baseline_total
        sum_of_per_year_deltas = math.fsum(delta_by_year.values())
        scenarios[_direction_name(shift)] = {
            "retained_after_inclusion_rerun": len(retained_ids[shift]),
            "excluded_after_inclusion_rerun": len(
                cohort_ids - retained_ids[shift]
            ),
            "weighted_annualized_benefit_by_year": {
                str(year): {
                    "baseline": baseline_annual[year],
                    "perturbed": alternative_annual[year],
                    "delta": delta_by_year[year],
                }
                for year in ledgers.REPORT_YEARS
            },
            "weighted_annualized_benefit_total": {
                "baseline": baseline_total,
                "perturbed": alternative_total,
                "delta": total_delta,
                "sum_of_per_year_deltas": sum_of_per_year_deltas,
                "floating_reconciliation_residual": (
                    sum_of_per_year_deltas - total_delta
                ),
            },
            "payment_window_membership": {
                "changed_count": len(changed_payment_windows),
                "changed_weighted_count": math.fsum(
                    baseline_people[person_id].weight
                    for person_id in changed_payment_windows
                ),
                "lost_any_payment_year_count": len(lost_payment_years),
                "gained_any_payment_year_count": len(gained_payment_years),
            },
            "benefit_factor_at_fixed_baseline_claim_age": {
                "changed_count": len(fixed_age_factor_changes),
                "changed_weighted_count": math.fsum(
                    baseline_people[person_id].weight
                    for person_id in fixed_age_factor_changes
                ),
            },
        }

    distinct_payment_changes = frozenset().union(*payment_change_ids.values())
    distinct_factor_changes = frozenset().union(*factor_change_ids.values())
    fixed_clause2_cohort = {
        "cohort": {
            "definition": (
                "Unperturbed Stage-D-included claimants whose corrected "
                "birth source is clause 2 (inferred_period_age). The cohort "
                "is fixed across perturbations."
            ),
            "count": len(cohort_ids),
            "weighted_count": math.fsum(
                baseline_people[person_id].weight for person_id in cohort_ids
            ),
        },
        "semantics": {
            "membership": (
                "The cohort is exactly the baseline-included clause-2 set. "
                "It excludes baseline-included exact-dated claimants and "
                "does not add scenario-only inbound claimants."
            ),
            "baseline_included_non_clause2_not_priced": len(
                full_included_ids[0] - cohort_ids
            ),
            "scenario_inbound_not_priced": {
                _direction_name(shift): len(
                    full_included_ids[shift] - full_included_ids[0]
                )
                for shift in (-1, 1)
            },
            "production_path": (
                "Reuse each scenario's production career-inclusion rerun, "
                "filter to the fixed baseline cohort, then call "
                "ledgers.build_benefit_ledger with the pinned full-actual "
                "ReportParameters."
            ),
            "excluded_cohort_member_payment_window": (
                "empty; the perturbed ledger receives only claimants that "
                "remain included"
            ),
            "weighted_benefit_measure": ledgers.BENEFIT_MEASURE_LABEL,
            "weighted_benefit_units": (
                "frame-annualized nominal dollars: 12 * person weight * "
                "monthly payment, summed over both production origin rows"
            ),
            "fixed_claim_age_factor_definition": (
                "Re-evaluate claiming.benefit_factor at the baseline "
                "integer claim age and perturbed birth year; do not use a "
                "scenario-specific opening-stock claim-age redraw."
            ),
            "total_delta_definition": (
                "The reported total delta is perturbed aggregate total minus "
                "baseline aggregate total. The separately reported sum of "
                "the eight annual deltas and binary-float residual expose "
                "the sub-mill summation-order difference."
            ),
        },
        "scenarios": scenarios,
        "distinct_people": {
            "payment_window_membership_changed": len(distinct_payment_changes),
            "benefit_factor_changed_at_fixed_claim_age": len(
                distinct_factor_changes
            ),
        },
    }
    result = {
        "coherent_shift_stress_scenarios": {
            "semantics": (
                "All shift-eligible birth coordinates move coherently in "
                "one direction. These are deterministic stress scenarios."
            ),
            "fixed_clause2_cohort": fixed_clause2_cohort,
            "full_scenario_ledger": {
                "semantics": {
                    "included_set": (
                        "Each scenario prices its complete production "
                        "Stage-D-included set; inbound and outbound changes "
                        "are both reflected."
                    ),
                    "production_path": (
                        "Call ledgers.build_benefit_ledger on every included "
                        "claimant from that scenario's production "
                        "career-inclusion rerun."
                    ),
                    "weighted_benefit_measure": (
                        ledgers.BENEFIT_MEASURE_LABEL
                    ),
                    "weighted_benefit_units": (
                        "frame-annualized nominal dollars: 12 * person "
                        "weight * monthly payment, summed over both "
                        "production origin rows"
                    ),
                },
                "scenarios": full_scenarios,
            },
        },
        "personwise_adversarial_range": personwise,
    }
    return LedgerEvidence(result=result)


def _oracle_reconciliation(
    *,
    draw_index: int,
    births: BirthEvidence,
    common_support: Mapping[str, Any],
    funnel: FunnelEvidence,
    revenue: Mapping[str, Any],
    sensitivity: SensitivityEvidence,
    ledger: LedgerEvidence,
) -> Mapping[str, Any]:
    if draw_index != 0:
        return {
            "status": "not_applicable",
            "reason": "The independent referee oracle is pinned to draw 0.",
            "rows": [],
        }

    rows = (
        (
            "clauses_1_2_synthetic_unresolved",
            births.result["initially_unresolved"]["count"],
            6392,
        ),
        (
            "seed_age_code_2_125",
            births.result["initially_unresolved"]["age_code_counts"][
                "actual_age_2_125"
            ],
            4077,
        ),
        (
            "seed_age_code_1",
            births.result["initially_unresolved"]["age_code_counts"][
                "unresolved_infant_code"
            ],
            2298,
        ),
        (
            "seed_age_999_or_missing",
            births.result["initially_unresolved"]["age_code_counts"][
                "unresolved_sentinel"
            ],
            17,
        ),
        (
            "corrected_derived_projection_age",
            births.result["initially_unresolved"]["corrected_counts_by_class"][
                "derived_projection_age"
            ],
            4077,
        ),
        (
            "corrected_unresolved",
            births.result["initially_unresolved"]["corrected_counts_by_class"][
                "unresolved"
            ],
            2315,
        ),
        (
            "raw_claim_year_carriers",
            funnel.result["initially_unresolved_raw_claim_year_carriers"][
                "count"
            ],
            276,
        ),
        (
            "raw_carrier_di_unknown",
            funnel.result["initially_unresolved_raw_claim_year_carriers"][
                "di_partition"
            ]["di_unknown"],
            190,
        ),
        (
            "new_true_stage_b_candidates",
            funnel.result["initially_unresolved_raw_claim_year_carriers"][
                "true_stage_b_candidates"
            ],
            86,
        ),
        (
            "new_candidate_opening_backfill",
            funnel.result["newly_dated_stage_b_candidates"]["origin_counts"][
                "opening_backfill"
            ],
            69,
        ),
        (
            "new_candidate_modeled_award",
            funnel.result["newly_dated_stage_b_candidates"]["origin_counts"][
                "modeled_award"
            ],
            17,
        ),
        (
            "canonical_candidates",
            funnel.result["canonical_candidates"]["count"],
            3083,
        ),
        (
            "canonical_domain_resident",
            funnel.result["canonical_candidates"]["domain_resident"],
            2784,
        ),
        (
            "era_flip_directions",
            sensitivity.result["predicates"]["eligibility_era"][
                "flip_directions"
            ],
            1,
        ),
        (
            "empty_span_flip_directions",
            sensitivity.result["predicates"]["nonempty_span"][
                "flip_directions"
            ],
            0,
        ),
        (
            "chronology_flip_directions",
            sensitivity.result["predicates"]["chronology"]["flip_directions"],
            600,
        ),
        (
            "chronology_inclusion_changing_flip_directions",
            sensitivity.result["predicates"]["chronology"][
                "inclusion_changing_flip_directions"
            ],
            294,
        ),
        (
            "coverage_flip_directions",
            sensitivity.result["predicates"]["coverage"]["flip_directions"],
            15,
        ),
        (
            "overall_inclusion_flip_directions",
            sensitivity.result["overall_inclusion"][
                "inclusion_flip_directions"
            ],
            310,
        ),
        (
            "overall_distinct_people_affected",
            sensitivity.result["overall_inclusion"][
                "distinct_people_affected"
            ],
            304,
        ),
        (
            "baseline_included_clause_2_claimants",
            ledger.result["coherent_shift_stress_scenarios"][
                "fixed_clause2_cohort"
            ]["cohort"]["count"],
            1440,
        ),
        (
            "full_ledger_baseline_included",
            ledger.result["coherent_shift_stress_scenarios"][
                "full_scenario_ledger"
            ]["scenarios"]["baseline"]["complete_included_set_count"],
            1514,
        ),
        (
            "full_ledger_birth_minus_1_included",
            ledger.result["coherent_shift_stress_scenarios"][
                "full_scenario_ledger"
            ]["scenarios"]["birth_minus_1"]["complete_included_set_count"],
            1520,
        ),
        (
            "full_ledger_birth_plus_1_included",
            ledger.result["coherent_shift_stress_scenarios"][
                "full_scenario_ledger"
            ]["scenarios"]["birth_plus_1"]["complete_included_set_count"],
            1240,
        ),
        (
            "birth_minus_1_chronology_inbound",
            sensitivity.result["predicates"]["chronology"]["directions"][
                "birth_minus_1"
            ]["neutral_inclusion_changes"]["inbound_to_included"]["count"],
            16,
        ),
        (
            "birth_plus_1_chronology_outbound",
            sensitivity.result["predicates"]["chronology"]["directions"][
                "birth_plus_1"
            ]["neutral_inclusion_changes"]["outbound_from_included"]["count"],
            278,
        ),
        (
            "birth_plus_1_low_coverage_outbound",
            sensitivity.result["predicates"]["coverage"]["directions"][
                "birth_plus_1"
            ]["neutral_inclusion_changes"]["outbound_from_included"]["count"],
            1,
        ),
        (
            "chronology_flip_directions_modeled_award",
            sensitivity.result["predicates"]["chronology"]["origin_assertion"][
                "observed_counts_by_origin"
            ]["modeled_award"],
            600,
        ),
        (
            "chronology_flip_directions_opening_backfill",
            sensitivity.result["predicates"]["chronology"]["origin_assertion"][
                "observed_counts_by_origin"
            ]["opening_backfill"],
            0,
        ),
        (
            "common_support_people",
            common_support["common_support_count"],
            4518,
        ),
        (
            "common_support_clause2_exact",
            common_support["endpoints"]["exact"][
                "clause2_inferred_period_age"
            ]["match_count"],
            2307,
        ),
        (
            "common_support_clause3_exact",
            common_support["endpoints"]["exact"]["clause3_seed_age"][
                "match_count"
            ],
            2299,
        ),
        (
            "common_support_clause2_within_1",
            common_support["endpoints"]["within_plus_or_minus_1"][
                "clause2_inferred_period_age"
            ]["match_count"],
            4516,
        ),
        (
            "common_support_clause3_within_1",
            common_support["endpoints"]["within_plus_or_minus_1"][
                "clause3_seed_age"
            ]["match_count"],
            4508,
        ),
        (
            "revenue_derived_zero_rows",
            revenue["groups"]["derived_projection_age"]["zero_earnings_rows"],
            28978,
        ),
        (
            "revenue_unresolved_zero_rows",
            revenue["groups"]["unresolved"]["zero_earnings_rows"],
            14066,
        ),
        (
            "revenue_combined_zero_rows",
            revenue["groups"]["combined"]["zero_earnings_rows"],
            43044,
        ),
    )
    reconciled = [
        {
            "key": key,
            "ours": int(ours),
            "oracle": oracle,
            "match": int(ours) == oracle,
        }
        for key, ours, oracle in rows
    ]
    mismatches = [row for row in reconciled if not row["match"]]
    if mismatches:
        raise AssertionError(
            "draw-0 evidence differs from the referee oracle: "
            + json.dumps(mismatches, sort_keys=True, separators=(",", ":"))
        )
    return {
        "status": "matched",
        "scope": (
            "Hardcoded unweighted count values only; dollar totals, shares, "
            "paired-test p-values, and float arithmetic are excluded."
        ),
        "matched_rows": len(reconciled),
        "rows": reconciled,
    }


def _parameter_identity(
    report_parameters: parameter_module.ReportParameters,
) -> Mapping[str, Any]:
    provenance = report_parameters.provenance
    policyengine = provenance["policyengine_us"]
    runtime_policyengine = report_parameters.runtime_provenance["parameters"][
        "policyengine_us"
    ]
    return {
        "schema_version": provenance["schema_version"],
        "bundle_sha256": provenance["bundle_sha256"],
        "policyengine_us_version": policyengine["version"],
        "policyengine_us_ssa_parameter_bundle_sha256": policyengine[
            "ssa_parameter_bundle_sha256"
        ],
        "policyengine_us_all_consumed_files_sha256": policyengine[
            "all_consumed_files_sha256"
        ],
        "policyengine_us_git_revision": runtime_policyengine["git_revision"],
    }


def _resolve_output_path(argument: Path | None, draw_index: int) -> Path:
    if argument is None:
        return (
            ROOT
            / "runs"
            / f"first_estimates_birth_evidence_draw{draw_index}.json"
        )
    path = argument if argument.is_absolute() else ROOT / argument
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT)
    except ValueError as error:
        raise ValueError(
            "output path must remain inside this worktree"
        ) from error
    return resolved


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--draw-index",
        type=int,
        default=0,
        choices=runner.DRAW_INDICES,
    )
    parser.add_argument(
        "--cache",
        type=Path,
        default=DEFAULT_CACHE,
        help="Optional diagnostic pickle cache (draw 0 only).",
    )
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="Ignore the cache and run the registered one-real-draw path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help=(
            "Canonical JSON destination; defaults to "
            "runs/first_estimates_birth_evidence_draw<index>.json."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    _assert_input_identity()
    runtime_identity = _assert_runtime()
    report_parameters = parameter_module.load_report_parameters()
    preparation.validate_full_actual_report_parameters(report_parameters)
    if args.regenerate or not args.cache.is_file():
        loaded = _regenerate_draw(args.draw_index, report_parameters)
    else:
        loaded = _load_cached_draw(args.cache, args.draw_index)
    births = _derive_birth_evidence(loaded)
    common_support = _derive_common_support_agreement(loaded, births)
    revenue = _derive_revenue_person_year_evidence(births)
    funnel = _derive_funnel_evidence(loaded, births)
    sensitivity = _derive_sensitivity_evidence(
        loaded=loaded,
        births=births,
        funnel=funnel,
    )
    ledger = _derive_ledger_evidence(
        report_parameters=report_parameters,
        draw_index=args.draw_index,
        births=births,
        sensitivity=sensitivity,
    )
    oracle = _oracle_reconciliation(
        draw_index=args.draw_index,
        births=births,
        common_support=common_support,
        funnel=funnel,
        revenue=revenue,
        sensitivity=sensitivity,
        ledger=ledger,
    )
    document = {
        "benefit_ledger_sensitivity": ledger.result,
        "birth_source_law": births.result,
        "candidate_funnel": funnel.result,
        "common_support_agreement": common_support,
        "execution": {
            **loaded.execution,
            "parameters": _parameter_identity(report_parameters),
            "runtime": runtime_identity,
        },
        "inclusion_sensitivity": sensitivity.result,
        "input_identity": {
            "master_sha": EXPECTED_MASTER_SHA,
            "draw_index": args.draw_index,
            "root_seed": loaded.draw.root_seed,
        },
        "oracle_reconciliation": oracle,
        "revenue_person_year_evidence": revenue,
        "schema_version": SCHEMA_VERSION,
    }
    encoded = (
        json.dumps(
            document,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    )
    output_path = _resolve_output_path(args.output, args.draw_index)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(encoded)
    relative_output = output_path.relative_to(ROOT)
    coherent = ledger.result["coherent_shift_stress_scenarios"]
    full_ledger = coherent["full_scenario_ledger"]
    minus_total = full_ledger["scenarios"]["birth_minus_1"][
        "weighted_annualized_benefit_total"
    ]["delta_from_baseline"]
    plus_total = full_ledger["scenarios"]["birth_plus_1"][
        "weighted_annualized_benefit_total"
    ]["delta_from_baseline"]
    initially_unresolved = births.result["initially_unresolved"]
    canonical_candidates = funnel.result["canonical_candidates"]
    raw_carriers = funnel.result[
        "initially_unresolved_raw_claim_year_carriers"
    ]
    predicates = sensitivity.result["predicates"]
    overall_inclusion = sensitivity.result["overall_inclusion"]
    print(
        f"WROTE {relative_output} bytes={len(encoded.encode())}\n"
        f"DATA_PATH {loaded.execution['data_path']}\n"
        f"ORACLE {oracle['status']} rows={oracle.get('matched_rows', 0)}\n"
        f"A unresolved={initially_unresolved['count']} "
        "derived="
        f"{initially_unresolved['corrected_counts_by_class']['derived_projection_age']} "
        "residual="
        f"{initially_unresolved['corrected_counts_by_class']['unresolved']}\n"
        f"B raw_carriers={raw_carriers['count']} "
        f"stage_b={raw_carriers['true_stage_b_candidates']} "
        f"canonical={canonical_candidates['count']} "
        f"domain={canonical_candidates['domain_resident']}\n"
        "C chronology_flips="
        f"{predicates['chronology']['flip_directions']} "
        "chronology_inclusion="
        f"{predicates['chronology']['inclusion_changing_flip_directions']} "
        f"coverage_flips={predicates['coverage']['flip_directions']} "
        "overall_directions="
        f"{overall_inclusion['inclusion_flip_directions']} "
        f"distinct_people={overall_inclusion['distinct_people_affected']}\n"
        "D fixed_cohort="
        f"{coherent['fixed_clause2_cohort']['cohort']['count']} "
        "full_baseline="
        f"{full_ledger['scenarios']['baseline']['complete_included_set_count']} "
        f"birth_minus_1_delta={minus_total:.17g} "
        f"birth_plus_1_delta={plus_total:.17g}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
