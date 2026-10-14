#!/usr/bin/env python3
"""Track B B2: the one-shot scorer (B0.1 addendum, sections 7 and 8).

``docs/design/track_b_b0_1_addendum.md`` is the frozen record B2 registers
on. This script runs B2's one candidate run and scores it:

- it fits candidate 3's registered law at origin 2010 with seed 5200 and
  element 1's wage vintage (policyengine-us 1.752.2 NAWI realized through
  2010, with the fitter's log-linear projection over 2001-2010);
- it projects draw seeds 6200-6219 (K = 20) to 2012 and 2014 by the
  selectors' projection loop, and computes the 16 gateable cells'
  full-support gaps;
- se_boot is the SD of the signed gap over 4,000 design replicates
  (Rao-Wu, streams [20261002, b, 4]) with the law and each person's paths
  fixed; se_c = sqrt(se_boot**2 + a_c se_up**2) with a_c = e_B2 from the
  planning record and se_up from B2's committed floor artifact;
- it applies the bound rule with t*_{m,nu}, the Monte Carlo and
  undefined-replicate rules, and M6's seed conjunction on the side-A gaps
  of gate seeds 0-4 (household splits of the full 2011 anchor);
- it returns the outcome (INVALID, FAIL, PASS or INCONCLUSIVE) and scores
  every report-only cell with its own unadjusted 95% interval.

It refuses to run without a committed floor artifact whose outcome is
LADDER_CLEARED (it records its hash), a registration identifier and the
expected commit, and its output is exclusive: after any candidate outcome
the registration permits no rerun. For example::

    PYTHONDONTWRITEBYTECODE=1 PYTHONWARNINGS='ignore::FutureWarning' \\
      PYTHONPATH=src:scripts OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \\
      MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \\
      OMP_WAIT_POLICY=PASSIVE \\
      POPULACE_DYNAMICS_PSID_DIR=/Users/maxghenis/PolicyEngine/psid-data \\
      POPULACE_DYNAMICS_PE_US_DIR=/path/to/site-packages \\
      /path/to/runtime/bin/python scripts/track_b_b2_score.py \\
      --registration-id <#42 comment id> --expected-commit <sha> \\
      --workers 4

Progress goes to stderr as stage names and counts only; no value is
printed before the record is written.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
from collections.abc import Mapping, Sequence
from contextlib import redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import select_m6_qstar_train_only as selector  # noqa: E402
import track_b_b0_1_planning_values as planning  # noqa: E402
import track_b_b2_floor as floor_builder  # noqa: E402

from populace_dynamics.engine.candidates import CANDIDATE_3  # noqa: E402
from populace_dynamics.engine.earnings_domain import (  # noqa: E402
    EARNINGS_DOMAIN_COLUMN,
    earnings_domain_person_ids,
)
from populace_dynamics.engine.refit import (  # noqa: E402
    refit_earnings_chained_generator,
    truncate_estimation_frame,
)
from populace_dynamics.harness.m6_scoring import (  # noqa: E402
    side_a_person_ids,
)
from populace_dynamics.track_b import b2  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "track_b_b2_score.v1"
OUTPUT = ROOT / "runs" / "track_b_b2_score.json"
#: The one-shot attempt log, opened before any data is read.
ATTEMPT = ROOT / "runs" / "track_b_b2_score.attempt.jsonl"
FLOOR = floor_builder.OUTPUT
PE_US_ENV = "POPULACE_DYNAMICS_PE_US_DIR"
POLICYENGINE_US_VERSION = planning.POLICYENGINE_US_VERSION
NAWI_RELATIVE = planning.NAWI_RELATIVE
#: Files whose bytes must equal the floor artifact's record of them: the
#: rules and the machinery the floor's values and this score share.
SHARED_CODE = (
    "src/populace_dynamics/track_b/b2.py",
    "scripts/track_b_b0_1_planning_values.py",
    "scripts/track_b_b0_1_ruled_power.py",
    "scripts/track_b_b0_1_addendum_power.py",
    "scripts/select_m6_qstar_train_only.py",
    "src/populace_dynamics/harness/m6_cells.py",
)
CODE = (
    Path(__file__).resolve(),
    ROOT / "scripts" / "track_b_b2_floor.py",
    *(ROOT / path for path in SHARED_CODE),
)


@dataclass(frozen=True)
class ScoreConfig:
    """Replicate count and workers. Only the registered count may be
    written to a record (``assert_registered``)."""

    b_design: int = b2.B_DESIGN
    workers: int = 4


def assert_registered(config: ScoreConfig) -> None:
    """Refuse a record built with anything but the registered settings."""
    if config.b_design != b2.B_DESIGN:
        raise AssertionError("the design bootstrap is not 4,000")
    if tuple(planning.DRAW_SEEDS) != b2.DRAW_SEEDS:
        raise AssertionError("the draw seeds are not 6200-6219")
    if tuple(selector.SELECTION_DRAW_SEEDS) != b2.DRAW_SEEDS:
        raise AssertionError("the selectors' draw seeds are not 6200-6219")
    if selector.FIT_SEED != b2.FIT_SEED:
        raise AssertionError("the fit seed is not 5200")


# --------------------------------------------------------------------------
# Wage index, law and context at origin 2010
# --------------------------------------------------------------------------
def nawi_2010(pe_us_dir: Path) -> tuple[dict[int, float], dict[str, Any]]:
    """NAWI realized through 2010 by the selectors' prefix reader, with the
    selectors' 2010 pins (element 1)."""
    dist = list(pe_us_dir.glob("policyengine_us-*.dist-info"))
    if len(dist) != 1:
        raise RuntimeError("expected exactly one policyengine-us dist-info")
    metadata = (dist[0] / "METADATA").read_text(encoding="utf-8")
    version = next(
        line.split(":", 1)[1].strip()
        for line in metadata.splitlines()
        if line.startswith("Version:")
    )
    if version != POLICYENGINE_US_VERSION:
        raise RuntimeError(f"policyengine-us {version} is not 1.752.2")
    values, audit = selector._read_historical_nawi(
        pe_us_dir / NAWI_RELATIVE, maximum_year=b2.ORIGIN
    )
    expected = selector.EXPECTED_BOUNDARY_NAWI[b2.ORIGIN]
    if (
        audit["bytes_consumed_through_maximum_key"] != expected["prefix_bytes"]
        or audit["admitted_prefix_sha256"] != expected["prefix_sha256"]
        or b2.canonical_sha256(values) != expected["mapping_sha256"]
    ):
        raise RuntimeError("the 2010 NAWI prefix differs from the pin")
    if missing := sorted(
        set(range(b2.ORIGIN - 9, b2.ORIGIN + 1)) - set(values)
    ):
        raise ValueError(f"NAWI misses fit-decade years {missing}")
    return values, {
        "policyengine_us_version": version,
        "maximum_key_year": audit["maximum_admitted_key_year"],
        "prefix_bytes": audit["bytes_consumed_through_maximum_key"],
        "prefix_sha256": audit["admitted_prefix_sha256"],
        "mapping_sha256": b2.canonical_sha256(values),
        "wage_vintage": b2.WAGE_VINTAGE,
        "wage_vintage_label": b2.WAGE_VINTAGE_LABEL,
    }


def fit_law(
    fit_input: pd.DataFrame,
    nawi: Mapping[int, float],
    *,
    boundary: int = b2.ORIGIN,
    qrf_factory: Any = None,
) -> Any:
    """Candidate 3's registered law at ``boundary``, fit seed 5200."""
    with redirect_stdout(sys.stderr):
        return refit_earnings_chained_generator(
            fit_input,
            nawi,
            seed=b2.FIT_SEED,
            boundary_year=boundary,
            qrf_factory=qrf_factory,
            candidate_spec=CANDIDATE_3,
        )


def build_context(
    fitted: Any,
    earnings: pd.DataFrame,
    full_anchor: pd.DataFrame,
    *,
    boundary: int = b2.ORIGIN,
) -> selector.BoundaryContext:
    """The selectors' boundary context at ``boundary``, without floor or
    truth cells: the planning script's ``build_context`` with the boundary
    as a parameter. The domain must equal the fitted anchor set."""
    fitted_domain = earnings_domain_person_ids(fitted.generator)
    domain_ids = frozenset(
        int(value)
        for value in set(full_anchor["person_id"].astype(int)) & fitted_domain
    )
    fitted_anchor_ids = frozenset(fitted.anchors["person_id"].astype(int))
    if domain_ids != fitted_anchor_ids:
        raise AssertionError(f"full-anchor/domain mismatch at {boundary}")
    truth = b2.truth_support(
        earnings,
        full_anchor,
        domain_ids,
        (boundary, boundary + 2, boundary + 4),
    )
    anchor_state = fitted.anchors[
        fitted.anchors["person_id"].isin(domain_ids)
    ][["person_id", "age"]].copy()
    anchor_state = anchor_state.sort_values("person_id", kind="stable")
    initial_slice = anchor_state.assign(
        year=boundary,
        sex=selector.SCHEMA_SEX_SENTINEL,
        **{EARNINGS_DOMAIN_COLUMN: True},
    )
    return selector.BoundaryContext(
        boundary=boundary,
        full_anchor=full_anchor,
        domain_ids=domain_ids,
        initial_slice=initial_slice,
        truth_support=truth,
        truth_cells={},
        floor={},
        floor_gate_seed_detail=(),
        standardizers={},
        support_audit={},
        rng_manifest={},
    )


# --------------------------------------------------------------------------
# Cells and gaps on a frame set
# --------------------------------------------------------------------------
def frame_set_values(
    truth: pd.DataFrame,
    draws: Sequence[pd.DataFrame],
    *,
    level_years: tuple[int, ...] = b2.LEVEL_YEARS,
    change_years: tuple[int, ...] = b2.CHANGE_YEARS,
) -> tuple[dict[str, float | None], list[dict[str, float | None]]]:
    """The truth's and each draw's cell values on one frame set."""
    years = {"level_years": level_years, "change_years": change_years}
    return b2.cell_values(truth, **years), [
        b2.cell_values(frame, **years) for frame in draws
    ]


def set_gaps(
    truth_values: Mapping[str, float | None],
    draw_values: Sequence[Mapping[str, float | None]],
) -> dict[str, float | None]:
    """Each cell's signed gap: ln(P/T) or P - T, P the mean over draws."""
    return {
        name: planning.signed_gap(
            metric,
            [values[name] for values in draw_values],
            truth_values[name],
        )
        for name, metric in b2.CELL_METRICS.items()
    }


def copied_frames(
    truth: pd.DataFrame,
    draws: Sequence[pd.DataFrame],
    multiplicity: Mapping[int, int],
) -> tuple[pd.DataFrame, list[pd.DataFrame]]:
    """Copy every person c times, truth rows and each draw's projected rows
    alike, by the addendum's ``copy_persons`` (arm F's construction)."""
    return b2.copy_persons(truth, multiplicity, planning.copy_persons), [
        b2.copy_persons(frame, multiplicity, planning.copy_persons)
        for frame in draws
    ]


def replicate_gaps(
    truth: pd.DataFrame,
    draws: Sequence[pd.DataFrame],
    multiplicity: Mapping[int, int],
    **years: tuple[int, ...],
) -> dict[str, float | None]:
    """The signed gaps on one resampled frame set."""
    copied_truth, copied_draws = copied_frames(truth, draws, multiplicity)
    return set_gaps(*frame_set_values(copied_truth, copied_draws, **years))


def design_replicate(replicate: int) -> dict[str, Any]:
    """Design replicate b's signed gaps, Rao-Wu on [20261002, b, 4]."""
    payload = b2.worker_payload()
    mult = b2.design_multiplicities(
        payload["design"], replicate, root=b2.ROOT_SEED
    )
    return {
        "replicate": int(replicate),
        "gaps": replicate_gaps(payload["truth"], payload["draws"], mult),
    }


def side_a_scores(
    full_anchor: pd.DataFrame,
    domain_ids: frozenset[int],
    truth: pd.DataFrame,
    draws: Sequence[pd.DataFrame],
) -> list[dict[str, Any]]:
    """Each gate seed's side-A validity and gaps.

    Side A is the first half of a household split of the full 2011 anchor
    (``m6_scoring.side_a_person_ids``), intersected with the domain. Its
    statistics come from the full-domain projection's K draws restricted
    to side-A persons; nothing is re-projected.
    """
    out = []
    for seed in b2.GATE_SEEDS:
        side = set(
            int(value)
            for value in side_a_person_ids(
                full_anchor, split_unit="household", seed=seed
            )
        ) & set(domain_ids)
        truth_values, draw_values = frame_set_values(
            truth[truth["person_id"].isin(side)],
            [frame[frame["person_id"].isin(side)] for frame in draws],
        )
        out.append(
            {
                "seed": seed,
                "persons": len(side),
                "valid": {
                    name: b2.frame_valid(
                        truth_values[name],
                        [values[name] for values in draw_values],
                    )
                    for name in b2.CELLS
                },
                "gap": set_gaps(truth_values, draw_values),
            }
        )
    return out


# --------------------------------------------------------------------------
# The score
# --------------------------------------------------------------------------
def score(
    context: selector.BoundaryContext,
    draws: Sequence[pd.DataFrame],
    design: pd.DataFrame,
    floor_record: Mapping[str, Any],
    planning_record: Mapping[str, Any],
    *,
    config: ScoreConfig,
) -> dict[str, Any]:
    """Sections 7 and 8 on one projection: every gated and report-only
    cell scored, and the outcome."""
    truth = context.truth_support
    gated = [entry["cell"] for entry in floor_record["surface"]["gated"]]
    if not gated:
        raise RuntimeError("the floor artifact gates no cell")
    nu = int(floor_record["design"]["design_degrees_of_freedom"])
    critical = b2.t_star(len(gated), nu)

    b2.progress("full-support cells")
    truth_values, draw_values = frame_set_values(truth, draws)
    full_gaps = set_gaps(truth_values, draw_values)

    b2.progress(f"design bootstrap, {config.b_design} replicates")
    replicates = b2.run_replicates(
        design_replicate,
        config.b_design,
        {"design": design, "truth": truth, "draws": draws},
        config.workers,
    )
    failures = sorted(
        {r["exception_class"] for r in replicates if r.get("failed")}
    )

    b2.progress("side A of gate seeds 0-4")
    sides = side_a_scores(
        context.full_anchor, context.domain_ids, truth, draws
    )

    cells: dict[str, dict[str, Any]] = {}
    for name, metric in b2.CELL_METRICS.items():
        draws_c = [values[name] for values in draw_values]
        floor_cell = floor_record["cells"][name]
        a_c = b2.registered_estimation_ratio(planning_record["cells"][name])
        se_boot, design_undefined = b2.defined_sd(
            [
                None if record.get("failed") else record["gaps"][name]
                for record in replicates
            ]
        )
        se_up = floor_cell["se_up"]["se_up"]
        se = b2.registered_se(se_boot, a_c, se_up)
        projected = (
            None
            if any(value is None for value in draws_c)
            else float(np.mean(np.asarray(draws_c, dtype=np.float64)))
        )
        cells[name] = {
            "metric": metric,
            "family": b2.concept(name),
            "exposure_label": b2.exposure_label(name),
            "gated": name in gated,
            "tolerance": floor_cell["tolerance"],
            "plain_units": floor_cell["plain_units"],
            "truth": truth_values[name],
            "projected_mean": projected,
            "gap": full_gaps[name],
            "valid_full_support": b2.frame_valid(truth_values[name], draws_c),
            "within_tolerance": (
                floor_cell["tolerance"] is not None
                and b2.within(full_gaps[name], floor_cell["tolerance"])
            ),
            "mc_error": planning.monte_carlo_error(metric, draws_c),
            "se_boot": se_boot,
            "design_replicates": len(replicates),
            "design_undefined": design_undefined,
            "se_up": se_up,
            "household_replicates": floor_cell["se_up"]["replicates"],
            "household_undefined": floor_cell["se_up"]["undefined"],
            "a_c": a_c,
            "se": se,
            "side_a": [
                {
                    "seed": side["seed"],
                    "valid": side["valid"][name],
                    "gap": side["gap"][name],
                    "within_tolerance": (
                        floor_cell["tolerance"] is not None
                        and b2.within(
                            side["gap"][name], floor_cell["tolerance"]
                        )
                    ),
                }
                for side in sides
            ],
        }
        cells[name]["monte_carlo_rule"] = floor_cell[
            "tolerance"
        ] is not None and b2.monte_carlo_passes(
            cells[name]["mc_error"], floor_cell["tolerance"]
        )
        if name not in gated:
            cells[name]["report_interval_95"] = b2.report_interval(
                full_gaps[name], se, nu
            )
            cells[name]["report_critical_value"] = b2.t_star(1, nu)

    gate = b2.gate_outcome(
        [
            b2.GatedCell(
                name=name,
                tolerance=cells[name]["tolerance"],
                full_valid=cells[name]["valid_full_support"],
                full_gap=cells[name]["gap"],
                side_a_valid=tuple(s["valid"] for s in cells[name]["side_a"]),
                side_a_gap=tuple(s["gap"] for s in cells[name]["side_a"]),
                se=cells[name]["se"],
                mc_error=cells[name]["mc_error"],
                design_undefined=cells[name]["design_undefined"],
                design_replicates=cells[name]["design_replicates"],
                household_undefined=cells[name]["household_undefined"],
                household_replicates=cells[name]["household_replicates"],
            )
            for name in gated
        ],
        critical,
    )
    for name in gated:
        cells[name]["bound"] = gate["per_cell"][name]["bound"]
    return {
        "outcome": gate["outcome"],
        "gate": {
            **gate,
            "gated_cells": gated,
            "m": len(gated),
            "design_degrees_of_freedom": nu,
        },
        "cells": cells,
        "side_a_persons": {
            str(side["seed"]): side["persons"] for side in sides
        },
        "design_replicate_failures": failures,
        "config": {
            "b_design": config.b_design,
            "root_seed": b2.ROOT_SEED,
            "design_stream": f"[{b2.ROOT_SEED}, b, {b2.DESIGN_WORD}]",
            "draw_seeds": list(b2.DRAW_SEEDS),
            "fit_seed": b2.FIT_SEED,
            "gate_seeds": list(b2.GATE_SEEDS),
        },
    }


def check_scoring_inputs(
    floor_record: Mapping[str, Any],
    planning_record: Mapping[str, Any],
) -> None:
    """Validate every gated and report-only input before any fit begins."""
    if floor_record.get(
        "outcome"
    ) != b2.LADDER_CLEARED or not floor_record.get("candidate_runs_permitted"):
        raise ValueError("the floor does not permit a candidate run")
    try:
        gated = [entry["cell"] for entry in floor_record["surface"]["gated"]]
        if (
            len(gated) < b2.MIN_GATED_CELLS
            or len(set(gated)) != len(gated)
            or not set(gated) <= set(b2.LEVEL_CELLS)
        ):
            raise ValueError("the floor's gated surface is invalid")
        b2.t_star(
            len(gated), floor_record["design"]["design_degrees_of_freedom"]
        )
        for name in b2.CELLS:
            cell = floor_record["cells"][name]
            a_c = b2.registered_estimation_ratio(
                planning_record["cells"][name]
            )
            if cell["registered_estimation_ratio"] != a_c:
                raise ValueError(f"{name}'s a_c differs from the floor's")
            tolerance = cell["tolerance"]
            if tolerance is None:
                valid_tolerance = name not in gated
            else:
                valid_tolerance = math.isfinite(tolerance) and (
                    tolerance > 0 if name in gated else tolerance >= 0
                )
            if not valid_tolerance or not isinstance(cell["plain_units"], str):
                raise ValueError(f"{name}'s floor tolerance is invalid")
            se_up = cell["se_up"]
            value = se_up["se_up"]
            if value is not None and not (math.isfinite(value) and value >= 0):
                raise ValueError(f"{name}'s se_up is invalid")
            if name in gated and (value is None or value == 0):
                raise ValueError(f"{name}'s gated se_up is undefined")
            total, undefined = se_up["replicates"], se_up["undefined"]
            if not (
                isinstance(total, int)
                and isinstance(undefined, int)
                and total > 0
                and 0 <= undefined <= total
            ):
                raise ValueError(f"{name}'s replicate counts are invalid")
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(
            f"B2 scoring inputs are incomplete or invalid: {error}"
        ) from error


def run_score(
    earnings: pd.DataFrame,
    anchor_demo: pd.DataFrame,
    design: pd.DataFrame,
    nawi: Mapping[int, float],
    floor_record: Mapping[str, Any],
    planning_record: Mapping[str, Any],
    *,
    config: ScoreConfig,
    qrf_factory: Any = None,
) -> dict[str, Any]:
    """Check the sources against the floor, then fit, project and score."""
    check_scoring_inputs(floor_record, planning_record)
    full_anchor = b2.full_anchor_frame(anchor_demo)
    data_domain = b2.domain_person_ids(earnings, full_anchor)
    domain = floor_record["domain"]
    if (
        b2.id_sha256(full_anchor["person_id"])
        != domain["full_anchor_ids_sha256"]
    ):
        raise AssertionError("the full anchor differs from the floor's")
    if b2.id_sha256(data_domain) != domain["domain_ids_sha256"]:
        raise AssertionError("the domain differs from the floor's")
    data_truth = b2.truth_support(earnings, full_anchor, data_domain)
    if (
        selector._key_checksum(data_truth)
        != domain["truth_support_keys_sha256"]
    ):
        raise AssertionError("the truth support differs from the floor's")
    truth_persons = set(int(v) for v in data_truth["person_id"].unique())
    design = design[design["person_id"].isin(truth_persons)].reset_index(
        drop=True
    )
    if set(design["person_id"].astype(int)) != truth_persons:
        raise AssertionError("a truth-support person has no design variables")
    if b2.design_summary(design) != floor_record["design"]:
        raise AssertionError("the design summary differs from the floor's")

    fit_input = truncate_estimation_frame(
        earnings,
        boundary_year=b2.ORIGIN,
        year_column="period",
        flow=False,
        label="B2 fit input",
    )
    b2.progress("fitting candidate 3's law at origin 2010")
    fitted = fit_law(fit_input, nawi, qrf_factory=qrf_factory)
    context = build_context(fitted, earnings, full_anchor)
    if context.domain_ids != data_domain:
        raise AssertionError("the fitted domain differs from the data domain")
    if not context.truth_support.equals(data_truth):
        raise AssertionError("the context's truth support differs")
    b2.progress("projecting the K draws to 2012 and 2014")
    draws = planning.project_draws(fitted.generator, context)
    law = {
        "candidate_id": CANDIDATE_3.candidate_id,
        "candidate_spec_sha256": CANDIDATE_3.sha256,
        "fit_seed": b2.FIT_SEED,
        "draw_seeds": list(b2.DRAW_SEEDS),
        "boundary": b2.ORIGIN,
        "fit_input_rows": int(len(fit_input)),
        "fit_input_max_period": int(fit_input["period"].max()),
        "anchor_forward_pairs": int(len(fitted.forward_pairs)),
        "wage_vintage_label": b2.WAGE_VINTAGE_LABEL,
    }
    del fitted
    record = score(
        context,
        draws,
        design,
        floor_record,
        planning_record,
        config=config,
    )
    record["law"] = law
    return record


# --------------------------------------------------------------------------
# Preconditions and the run
# --------------------------------------------------------------------------
def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_floor_record(
    floor_record: Mapping[str, Any], registration_id: str, head: str
) -> None:
    """The floor artifact must clear, belong to this registration, come
    from an ancestor of HEAD and share this run's rules and records."""
    if floor_record.get("schema") != floor_builder.SCHEMA:
        raise RuntimeError("the floor artifact's schema is not B2's")
    outcome = floor_record.get("outcome")
    permitted = bool(floor_record.get("candidate_runs_permitted"))
    if outcome != b2.LADDER_CLEARED or not permitted:
        raise RuntimeError(
            f"the floor artifact does not permit a candidate run ({outcome})"
        )
    if floor_record.get("registration_id") != registration_id:
        raise RuntimeError(
            "the floor artifact belongs to another registration"
        )
    try:
        b2.git(
            ROOT,
            "merge-base",
            "--is-ancestor",
            floor_record["repository_head"],
            head,
        )
    except Exception as error:  # noqa: BLE001 (any failure refuses)
        raise RuntimeError(
            "the floor was not built at an ancestor of HEAD"
        ) from error
    expected = {
        "addendum_sha256": sha256_file(floor_builder.ADDENDUM),
        "planning_values_sha256": sha256_file(floor_builder.PLANNING),
        "counts_record_sha256": sha256_file(floor_builder.COUNTS),
    }
    for key, value in expected.items():
        if floor_record.get(key) != value:
            raise RuntimeError(f"{key} differs from the floor artifact's")
    recorded = floor_record.get("code_sha256", {})
    for path in SHARED_CODE:
        if recorded.get(path) != sha256_file(ROOT / path):
            raise RuntimeError(f"{path} changed since the floor was built")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--registration-id", required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--floor-artifact", type=Path, default=FLOOR)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args(argv)
    # First, before anything is read: more than one thread hangs
    # candidate 3's projection in this environment (b2.thread_settings).
    threads = b2.thread_settings()
    b2.require_workers(args.workers)

    started = time.time()
    registration = b2.require_registration(args.registration_id)
    head = b2.require_clean_head(ROOT, args.expected_commit)
    if OUTPUT.exists():
        raise FileExistsError(f"{OUTPUT} exists; B2's score is one-shot")
    if ATTEMPT.exists():
        raise FileExistsError(
            f"{ATTEMPT} exists: B2 has been attempted; see its last stage"
        )
    floor_pin = b2.committed_sha256(ROOT, args.floor_artifact)
    floor_record = json.loads(args.floor_artifact.read_text(encoding="utf-8"))
    check_floor_record(floor_record, registration, head)
    runtime = planning.runtime_record()
    config = ScoreConfig(workers=args.workers)
    assert_registered(config)
    psid_value = os.environ.get(floor_builder.PSID_ENV)
    pe_us_value = os.environ.get(PE_US_ENV)
    if not psid_value or not pe_us_value:
        raise RuntimeError(
            f"{floor_builder.PSID_ENV} and {PE_US_ENV} must be set explicitly"
        )
    psid_dir = Path(psid_value).resolve()
    pe_us_dir = Path(pe_us_value).resolve()
    planning_record = json.loads(
        floor_builder.PLANNING.read_text(encoding="utf-8")
    )

    # Every check that needs no PSID data runs before the attempt log
    # exists, so an operator error there leaves no attempt behind.
    check_scoring_inputs(floor_record, planning_record)
    nawi, nawi_record = nawi_2010(pe_us_dir)
    b2.open_attempt(
        ATTEMPT,
        {
            "registration_id": registration,
            "expected_commit": args.expected_commit,
            "repository_head": head,
            "floor_artifact": floor_pin,
            "workers": config.workers,
            "threads": threads,
        },
    )
    b2.progress("reading B2's pinned read set under the read guard")
    earnings, anchor_demo, design, opened = floor_builder.read_inputs(
        psid_dir, floor_builder.read_set()
    )
    record = run_score(
        earnings,
        anchor_demo,
        design,
        nawi,
        floor_record,
        planning_record,
        config=config,
    )
    assert_registered(config)
    output = {
        "schema": SCHEMA,
        "registration_id": registration,
        "expected_commit": args.expected_commit,
        "repository_head": head,
        "worktree_clean": True,
        "floor_artifact": floor_pin,
        "addendum_sha256": sha256_file(floor_builder.ADDENDUM),
        "planning_values_sha256": sha256_file(floor_builder.PLANNING),
        "code_sha256": {
            path.relative_to(ROOT).as_posix(): sha256_file(path)
            for path in CODE
        },
        "psid_files_opened_sha256": dict(opened),
        "nawi": nawi_record,
        "runtime": runtime,
        "threads": threads,
        "workers": config.workers,
        "statements": floor_builder.statements(),
        **record,
        "wall_seconds": round(time.time() - started, 1),
    }
    digest = b2.write_exclusive(OUTPUT, output)
    b2.progress(f"wrote {OUTPUT.relative_to(ROOT)} (sha256 {digest})")
    b2.close_attempt()
    b2.progress(f"outcome {record['outcome']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
