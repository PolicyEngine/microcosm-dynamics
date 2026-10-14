#!/usr/bin/env python3
"""Track B B2: the truth-only floor builder (B0.1 addendum, section 9).

``docs/design/track_b_b0_1_addendum.md`` is the frozen record B2 registers
on. This script is section 9's floor builder, steps 2-6:

2. It defines the domain from data alone, the 2011 anchor persons with a
   valid 2010 row, and reads no candidate output, projection or selection
   ledger. It reads the addendum's planning-value record, which holds only
   variance ratios from the 2006 pseudo-origin, and says so in its
   artifact.
3. It computes the household-split floor (2011 households, seeds 0-99)
   and, without gating on it, the person-split floor.
4. It computes each cell's tolerance (section 6) and se_up (section 7,
   4,000 household replicates on streams [20261002, b, 0]). It counts the
   design strata among the truth-support persons, applies the fixed
   singleton merges, and publishes counts before and after, merges, L and
   nu.
5. It applies eligibility inside the six level cells (d781 (a), d1342
   option A); a cell that fails it is scored report-only. A zero nu, or
   an eligible cell whose se_up or tau is zero or undefined, stops the
   build as WEAK_POWER_OR_VACUITY before the ladder or any candidate run.
   Otherwise it runs the ladder and the guards over the eligible cells. Power is the ruled binding evaluation
   (``scripts/track_b_b0_1_ruled_power.py``) with r, the 95th percentile
   of d and s2_gate from the planning record, and nu, tau = tol / se_up
   and t*_{m,nu} from B2's own floor.
6. It writes one exclusive artifact: the gated and pruned cells with
   exposure labels and plain-unit tolerances, the power, and the canonical
   SHA-256 of the person-split floor block and seed 0-4 detail of the six
   M6-retained cells. B2's candidate runs only after it is committed.

Run it once, after B2's registration on #42 pins this script's commit,
the comparator's and the addendum, from a clean worktree at that commit
and in the selectors' pinned runtime, for example::

    PYTHONDONTWRITEBYTECODE=1 PYTHONWARNINGS='ignore::FutureWarning' \\
      PYTHONPATH=src:scripts OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \\
      MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \\
      OMP_WAIT_POLICY=PASSIVE POPULACE_FIT_N_JOBS=4 \\
      POPULACE_DYNAMICS_PSID_DIR=/Users/maxghenis/PolicyEngine/psid-data \\
      /path/to/runtime/bin/python scripts/track_b_b2_floor.py \\
      --registration-id <#42 comment id> --expected-commit <sha> \\
      --workers 4

Progress goes to stderr as stage names and counts only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from contextlib import redirect_stdout
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import select_m6_qstar_train_only as selector  # noqa: E402
import track_b_b0_1_planning_values as planning  # noqa: E402
import track_b_b0_1_ruled_power as ruled  # noqa: E402

from populace_dynamics.cohorts.age67 import (  # noqa: E402
    read_design_variables,
)
from populace_dynamics.cohorts.psid2010 import record_files_read  # noqa: E402
from populace_dynamics.harness import m6_cells  # noqa: E402
from populace_dynamics.track_b import b2  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "track_b_b2_floor.v1"
OUTPUT = ROOT / "runs" / "track_b_b2_floor.json"
ADDENDUM = ROOT / "docs" / "design" / "track_b_b0_1_addendum.md"
PLANNING = ROOT / "docs" / "design" / "track_b_b0_1_planning_values.json"
COUNTS = ROOT / "docs" / "design" / "track_b_b0_1_counts.json"
PSID_ENV = "POPULACE_DYNAMICS_PSID_DIR"
#: The code this artifact's numbers depend on, hashed into it.
CODE = (
    Path(__file__).resolve(),
    ROOT / "src" / "populace_dynamics" / "track_b" / "b2.py",
    ROOT / "scripts" / "track_b_b0_1_planning_values.py",
    ROOT / "scripts" / "track_b_b0_1_ruled_power.py",
    ROOT / "scripts" / "track_b_b0_1_addendum_power.py",
    ROOT / "scripts" / "select_m6_qstar_train_only.py",
    ROOT / "src" / "populace_dynamics" / "harness" / "m6_cells.py",
)
READS_STATEMENT = (
    "The builder is truth-only. It read B2's pinned PSID read set, the "
    "B0.1 addendum, the frozen counts record (B2's read-set pin and source "
    "counts) and the addendum's planning-value record, which holds only "
    "variance ratios from the 2006 pseudo-origin. It read no candidate "
    "output, projection or selection ledger."
)


@dataclass(frozen=True)
class FloorConfig:
    """Replicate counts and workers. Only the registered counts may be
    written to an artifact (``assert_registered``)."""

    b_household: int = b2.B_HOUSEHOLD
    workers: int = 4


def assert_registered(config: FloorConfig) -> None:
    """Refuse an artifact built with anything but the registered counts."""
    if config.b_household != b2.B_HOUSEHOLD:
        raise AssertionError("the household bootstrap is not 4,000")
    if tuple(m6_cells.FLOOR_SEEDS) != b2.FLOOR_SEEDS:
        raise AssertionError("the floor seeds are not 0-99")
    if tuple(m6_cells.GATE_SEEDS) != b2.GATE_SEEDS:
        raise AssertionError("the gate seeds are not 0-4")


# --------------------------------------------------------------------------
# Sources
# --------------------------------------------------------------------------
def read_set() -> dict[str, str]:
    """B2's pinned read set: 80 files and their SHA-256 (audit 4.1)."""
    record = json.loads(COUNTS.read_text(encoding="utf-8"))
    return dict(record["b2_read_set_sha256"])


def load_sources(psid_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The selectors' field-capped earnings rows (collection waves
    1969-2015) and anchor roster, by their own reader."""
    with redirect_stdout(sys.stderr):
        earnings, anchor_demo, _ = selector._load_field_capped_psid(psid_dir)
    if int(earnings["period"].max()) > max(b2.SCORED_PERIODS):
        raise AssertionError("an earnings row is dated after 2014")
    return earnings, anchor_demo


def read_inputs(
    psid_dir: Path, pinned: Mapping[str, str]
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, str]]:
    """Read the sources and the design variables under B2's read guard,
    and check every opened file against its pinned hash."""
    allowed = frozenset(pinned)
    with (
        b2.psid_read_guard(psid_dir, allowed),
        record_files_read(psid_dir) as opened,
    ):
        earnings, anchor_demo = load_sources(psid_dir)
        design = read_design_variables(data_dir=psid_dir)
    return earnings, anchor_demo, design, b2.check_opened(opened, pinned)


def source_counts(
    full_anchor: pd.DataFrame,
    domain_ids: frozenset[int],
    truth: pd.DataFrame,
) -> dict[str, Any]:
    """Counts the frozen record already holds (audit section 7)."""
    return {
        "full_anchor_persons": int(len(full_anchor)),
        "full_anchor_households": int(full_anchor["household_id"].nunique()),
        "domain_persons": int(len(domain_ids)),
        "scored_rows_by_period": {
            str(year): int((truth["period"] == year).sum())
            for year in b2.SCORED_PERIODS
        },
    }


def frozen_counts() -> dict[str, Any]:
    """The same counts from ``track_b_b0_1_counts.json``."""
    counts = json.loads(COUNTS.read_text(encoding="utf-8"))["counts"]
    return {
        "full_anchor_persons": int(counts["full_anchor_persons"]),
        "full_anchor_households": int(counts["full_anchor_households"]),
        "domain_persons": int(counts["domain_persons"]),
        "scored_rows_by_period": {
            str(year): int(counts["scored_support"][str(year)]["scored_rows"])
            for year in b2.SCORED_PERIODS
        },
    }


# --------------------------------------------------------------------------
# The household bootstrap for se_up (truth only)
# --------------------------------------------------------------------------
def household_replicate(replicate: int) -> dict[str, Any]:
    """Household replicate b's truth deviations, stream [20261002, b, 0].

    Persons are copied by their household's multiplicity
    (``copy_persons``); weights are never multiplied.
    """
    payload = b2.worker_payload()
    mult = b2.anchor_multiplicities(
        payload["clusters"], replicate, root=b2.ROOT_SEED
    )
    values = b2.cell_values(
        b2.copy_persons(payload["truth"], mult, planning.copy_persons)
    )
    reference = payload["reference"]
    return {
        "replicate": int(replicate),
        "tdev": {
            name: planning.truth_deviation(
                metric, values[name], reference[name]
            )
            for name, metric in b2.CELL_METRICS.items()
        },
    }


def se_up_records(
    replicates: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Each cell's se_up and undefined-replicate count. A replicate that
    raised counts as undefined for every cell."""
    out: dict[str, dict[str, Any]] = {}
    for name in b2.CELLS:
        deviations = [
            None if record.get("failed") else record["tdev"][name]
            for record in replicates
        ]
        out[name] = b2.se_upper(deviations)
    failures = sorted(
        {
            record["exception_class"]
            for record in replicates
            if record.get("failed")
        }
    )
    for record in out.values():
        record["failed_replicate_classes"] = failures
    return out


# --------------------------------------------------------------------------
# The ladder's power: the ruled binding evaluation on B2's floor
# --------------------------------------------------------------------------
def ladder_power(
    planning_record: Mapping[str, Any],
    tau: Mapping[str, float],
    nu: int,
) -> Callable[[tuple[str, ...]], float]:
    """Gate-level power of a surface on the ruled binding evaluation.

    r, the design ratio's 95th percentile and s2_gate come from the
    planning record; tau = tol / se_up and nu from B2's floor; m is the
    number of cells passed in.
    """

    def power(names: tuple[str, ...]) -> float:
        cells = ruled.ruled_cells(planning_record, ruled.BINDING, names)
        surface = [replace(cells[name], tau=tau[name]) for name in names]
        return float(ruled.surface_power(surface, nu, ruled.BINDING)["p_gate"])

    return power


# --------------------------------------------------------------------------
# The floor build (steps 2-6), truth only
# --------------------------------------------------------------------------
def measure(
    earnings: pd.DataFrame,
    anchor_demo: pd.DataFrame,
    *,
    config: FloorConfig,
    expected_counts: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Steps 2-4's truth-side measurements: the domain from data, both
    split floors and the household bootstrap. Nothing here is a candidate
    output."""
    full_anchor = b2.full_anchor_frame(anchor_demo)
    domain_ids = b2.domain_person_ids(earnings, full_anchor)
    truth = b2.truth_support(earnings, full_anchor, domain_ids)
    counts = source_counts(full_anchor, domain_ids, truth)
    if expected_counts is not None and counts != dict(expected_counts):
        raise AssertionError(
            "source reproduction failed: the domain or support differs "
            "from the frozen record"
        )

    b2.progress("household-split floor, seeds 0-99")
    floor_household, _ = b2.split_floor(full_anchor, truth, "household_id")
    b2.progress("person-split floor, seeds 0-99 (non-gating)")
    floor_person, detail_person = b2.split_floor(
        full_anchor, truth, "person_id"
    )

    b2.progress(f"household bootstrap, {config.b_household} replicates")
    replicates = b2.run_replicates(
        household_replicate,
        config.b_household,
        {
            "clusters": b2.household_clusters(full_anchor),
            "truth": truth,
            "reference": b2.cell_values(truth),
        },
        config.workers,
    )
    return {
        "truth": truth,
        "floor_household": floor_household,
        "se_up": se_up_records(replicates),
        "record": {
            "counts": counts,
            "domain": {
                "full_anchor_ids_sha256": b2.id_sha256(
                    full_anchor["person_id"]
                ),
                "domain_ids_sha256": b2.id_sha256(domain_ids),
                "truth_support_keys_sha256": selector._key_checksum(truth),
                "truth_support_rows": int(len(truth)),
            },
            "person_split": {
                "gating": False,
                "floor_block_six_cells_sha256": b2.canonical_sha256(
                    b2.six_cell_floor_block(floor_person)
                ),
                "seed_detail_six_cells_sha256": b2.canonical_sha256(
                    b2.six_cell_seed_detail(detail_person)
                ),
                "cells": list(b2.M6_RETAINED),
                "seeds": [int(entry["seed"]) for entry in detail_person],
            },
            "config": {
                "b_household": config.b_household,
                "floor_seeds": len(m6_cells.FLOOR_SEEDS),
                "root_seed": b2.ROOT_SEED,
                "household_stream": (
                    f"[{b2.ROOT_SEED}, b, {b2.HOUSEHOLD_WORD}]"
                ),
            },
        },
    }


def cell_records(
    floor_household: Mapping[str, Mapping[str, Any]],
    se_up: Mapping[str, Mapping[str, Any]],
    planning_record: Mapping[str, Any],
    n_seeds: int,
) -> dict[str, dict[str, Any]]:
    """Each gateable cell's floor, eligibility, tolerance (section 6) and
    se_up (section 7)."""
    cells: dict[str, dict[str, Any]] = {}
    for name, metric in b2.CELL_METRICS.items():
        floor = floor_household[name]
        if all(
            floor[key] is not None and math.isfinite(floor[key])
            for key in ("mean", "sd")
        ):
            tolerance = b2.tolerance(floor["mean"], floor["sd"], metric)
        else:
            tolerance = {
                "tolerance": None,
                "uncapped": None,
                "cap": b2.METRIC_CAP[metric],
                "at_cap": False,
                "metric": metric,
                "plain_units": "undefined tolerance",
            }
        planning_cell = planning_record["cells"][name]
        eligible_floor = bool(b2.floor_eligible(floor, n_seeds))
        planning_defined = bool(planning_cell.get("defined"))
        value = se_up[name]["se_up"]
        cells[name] = {
            "metric": metric,
            "family": b2.concept(name),
            "exposure_label": b2.exposure_label(name),
            "floor_household": {
                key: floor[key]
                for key in (
                    "mean",
                    "sd",
                    "realized_sigma",
                    "n_defined_seeds",
                    "min_events_weaker_half",
                )
            },
            "floor_eligible": eligible_floor,
            "planning_values_defined": planning_defined,
            "eligible": bool(eligible_floor and planning_defined),
            **tolerance,
            "se_up": dict(se_up[name]),
            "tau_se_up_units": (
                tolerance["tolerance"] / value
                if value is not None
                and math.isfinite(value)
                and value > 0
                and tolerance["tolerance"] is not None
                else None
            ),
            "registered_estimation_ratio": (
                b2.registered_estimation_ratio(planning_cell)
                if planning_defined
                else None
            ),
        }
    return cells


def decide(
    measured: Mapping[str, Any],
    design: pd.DataFrame,
    planning_record: Mapping[str, Any],
) -> dict[str, Any]:
    """Step 4's stratum merges and stops, and step 5's eligibility, ladder
    and guards inside the six level cells."""
    truth = measured["truth"]
    truth_persons = set(int(value) for value in truth["person_id"].unique())
    design = design[design["person_id"].isin(truth_persons)].reset_index(
        drop=True
    )
    if set(design["person_id"].astype(int)) != truth_persons:
        raise AssertionError("a truth-support person has no design variables")
    summary = b2.design_summary(design)
    nu = int(summary["design_degrees_of_freedom"])
    cells = cell_records(
        measured["floor_household"],
        measured["se_up"],
        planning_record,
        len(m6_cells.FLOOR_SEEDS),
    )
    record: dict[str, Any] = {
        **measured["record"],
        "design": summary,
        "cells": cells,
    }
    # Section 5's eligibility comes first: a cell of the six that fails it
    # (its floor's seeds or events, or its planning values) is scored
    # report-only, and the ladder runs on the others. B2 stops only when nu
    # is 0 after the merges, or when an eligible cell's sigma, se_up or tau
    # is zero or undefined: its tolerance is uninformative or its power
    # undefined (the design's "undefined cells, or uninformative
    # tolerances"), and section 5 never drops an eligible cell.
    eligible = [name for name in b2.LEVEL_CELLS if cells[name]["eligible"]]
    causes = []
    if nu == 0:
        causes.append({"cell": None, "quantity": "nu"})
    for name in eligible:
        quantities = {
            "sigma": cells[name]["floor_household"]["realized_sigma"],
            "se_up": cells[name]["se_up"]["se_up"],
            "tau": cells[name]["tau_se_up_units"],
        }
        for quantity, value in quantities.items():
            if value is None or not math.isfinite(value) or value <= 0:
                causes.append({"cell": name, "quantity": quantity})
    if causes:
        record["outcome"] = b2.WEAK_POWER_OR_VACUITY
        record["stop_causes"] = causes
        record["ladder"] = None
        return finish(record, cells)

    tau = {name: cells[name]["tau_se_up_units"] for name in eligible}
    power = ladder_power(planning_record, tau, nu)
    result = b2.ladder(
        [
            b2.LadderCell(
                name,
                cells[name]["tolerance"],
                cells[name]["floor_household"]["realized_sigma"],
                cells[name]["at_cap"],
            )
            for name in eligible
        ],
        power,
    )
    result["eligible"] = eligible
    result["evaluation"] = "ruled binding (d781 (a), d782, M2 rider, d765)"
    result["design_degrees_of_freedom"] = nu
    result["t_star"] = (
        b2.t_star(len(result["retained"]), nu) if result["retained"] else None
    )
    record["ladder"] = result
    record["outcome"] = result["outcome"]
    return finish(record, cells)


def build_floor(
    earnings: pd.DataFrame,
    anchor_demo: pd.DataFrame,
    design: pd.DataFrame,
    planning_record: Mapping[str, Any],
    *,
    config: FloorConfig,
    expected_counts: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Section 9's steps 2-5 and the computed part of step 6."""
    measured = measure(
        earnings,
        anchor_demo,
        config=config,
        expected_counts=expected_counts,
    )
    return decide(measured, design, planning_record)


def finish(
    record: dict[str, Any], cells: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    """The surface the artifact publishes: gated cells (only when the
    ladder clears) and every other gateable cell, report-only."""
    cleared = record["outcome"] == b2.LADDER_CLEARED
    gated = list(record["ladder"]["retained"]) if cleared else []
    nu = record["design"]["design_degrees_of_freedom"]

    def reason(name: str) -> str:
        if name not in b2.LEVEL_CELLS:
            return "outside the ruled surface (d781 (a))"
        if not cells[name]["planning_values_defined"]:
            return "no planning values"
        if not cells[name]["floor_eligible"]:
            return "floor ineligible"
        if not cleared:
            return f"B2 stopped at floor build ({record['outcome']})"
        return "pruned by the ladder"

    def entry(name: str) -> dict[str, Any]:
        cell = cells[name]
        return {
            "cell": name,
            "metric": cell["metric"],
            "family": cell["family"],
            "tolerance": cell["tolerance"],
            "plain_units": cell["plain_units"],
            "exposure_label": cell["exposure_label"],
        }

    labels = [cells[name]["exposure_label"] for name in gated]
    record["surface"] = {
        "ruled_surface": list(b2.LEVEL_CELLS),
        "gated": [entry(name) for name in gated],
        "report_only": [
            {**entry(name), "reason": reason(name)}
            for name in b2.CELLS
            if name not in gated
        ],
        "headline": {
            "scope": b2.HEADLINE_SCOPE,
            "gated_cells": len(gated),
            "gated_by_exposure_label": {
                label: labels.count(label)
                for label in (
                    b2.EXPOSURE_PUBLISHED_OUTCOMES,
                    b2.EXPOSURE_FLOOR_DETAIL,
                )
            },
        },
    }
    record["power"] = (
        {
            "p_gate": record["ladder"]["p_gate"],
            "m": len(gated),
            "design_degrees_of_freedom": nu,
            "t_star": b2.t_star(len(gated), nu),
            "evaluation": record["ladder"]["evaluation"],
        }
        if cleared
        else None
    )
    record["candidate_runs_permitted"] = cleared
    return record


# --------------------------------------------------------------------------
# Provenance and the run
# --------------------------------------------------------------------------
def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def statements() -> dict[str, str]:
    """What B2's registration carries (addendum section 13, "To B2")."""
    return {
        "headline_scope": b2.HEADLINE_SCOPE,
        "fallback_scope": b2.FALLBACK_SCOPE,
        "section_5_3": b2.SECTION_5_3_SENTENCE,
        "planning_caveat": b2.PLANNING_CAVEAT,
        "age_convention": b2.AGE_CONVENTION,
        "reference_year_mapping": b2.REFERENCE_YEAR_MAPPING,
        "wage_vintage": b2.WAGE_VINTAGE,
        "wage_vintage_label": b2.WAGE_VINTAGE_LABEL,
        "codebook_concept_check": b2.CODEBOOK_CONCEPT_CHECK,
        "candidate_3_disclosure": b2.CANDIDATE_3_DISCLOSURE,
        "b1": f"{b2.B1_EVIDENCE}; label: {b2.B1_LABEL}",
        "reads": READS_STATEMENT,
    }


def provenance(
    registration_id: str, head: str, opened: Mapping[str, str]
) -> dict[str, Any]:
    addendum = ADDENDUM.read_text(encoding="utf-8")
    block = planning.protocol_block_sha256(addendum)
    if block != planning.PROTOCOL_V2_SHA256:
        raise RuntimeError("the protocol-v2 block differs from the frozen one")
    return {
        "registration_id": registration_id,
        "repository_head": head,
        "worktree_clean": True,
        "addendum_sha256": sha256_file(ADDENDUM),
        "protocol_v2_sha256": block,
        "planning_values_sha256": sha256_file(PLANNING),
        "counts_record_sha256": sha256_file(COUNTS),
        "code_sha256": {
            path.relative_to(ROOT).as_posix(): sha256_file(path)
            for path in CODE
        },
        "psid_files_opened_sha256": dict(opened),
        "read_set_complete": True,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--registration-id", required=True)
    parser.add_argument("--expected-commit", required=True)
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
        raise FileExistsError(f"{OUTPUT} exists; the floor build is one-shot")
    runtime = planning.runtime_record()
    config = FloorConfig(workers=args.workers)
    assert_registered(config)
    psid_value = os.environ.get(PSID_ENV)
    if not psid_value:
        raise RuntimeError(f"{PSID_ENV} must be set explicitly")
    psid_dir = Path(psid_value).resolve()
    planning_record = json.loads(PLANNING.read_text(encoding="utf-8"))

    b2.progress("reading B2's pinned read set under the read guard")
    earnings, anchor_demo, design, opened = read_inputs(psid_dir, read_set())
    record = build_floor(
        earnings,
        anchor_demo,
        design,
        planning_record,
        config=config,
        expected_counts=frozen_counts(),
    )
    assert_registered(config)
    artifact = {
        "schema": SCHEMA,
        **provenance(registration, head, opened),
        "runtime": runtime,
        "threads": threads,
        "workers": config.workers,
        "psid_dir": str(psid_dir),
        "geometry": {
            "origin": b2.ORIGIN,
            "anchor_wave": b2.ANCHOR_WAVE,
            "level_years": list(b2.LEVEL_YEARS),
            "change_years": list(b2.CHANGE_YEARS),
            "collection_wave_of": {
                str(year): wave for year, wave in b2.COLLECTION_WAVE_OF.items()
            },
        },
        "statements": statements(),
        **record,
        "wall_seconds": round(time.time() - started, 1),
    }
    digest = b2.write_exclusive(OUTPUT, artifact)
    b2.progress(
        f"wrote {OUTPUT.relative_to(ROOT)} (sha256 {digest}); "
        f"outcome {record['outcome']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
