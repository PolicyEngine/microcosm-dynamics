"""Build gate_epuf_fill's floors, partition, checks on bite and oracles.

Reads only the DEV part of EPUF (``epuf_fill_gate.split_part == DEV``)
and the PSID-scale counts (``runs/epuf_fill_gate_psid_scale_v1.json``),
and writes, per the registration
(``docs/amendments/gate_epuf_fill_registration_proposal.md``):

1. every cell's true DEV value;
2. each floor group's sample size (section 5), pool, seed, replicate
   errors and per-cell sigma;
3. the partition into gating and report-only cells (section 6) and each
   gating cell's tolerance ``K_TOLERANCE * sigma``;
4. the checks on bite B1 (the current odd-year rule) and B2 (the current
   pre-career rule), each of which must fail a gating cell of its family by
   more than ``BITE_MULTIPLE`` tolerances, or the gate does not lock;
5. the oracles O1 and O2 over ``ORACLE_SEEDS``, reported without a verdict.

No TEST person is read. Usage::

    python scripts/build_epuf_fill_gate_floors.py \
        --psid-scale runs/epuf_fill_gate_psid_scale_v1.json \
        --output runs/epuf_fill_gate_floors_v1.json

``--part train --replicates 20`` makes a dry run on TRAIN for debugging;
its output is never a registered floor.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import time
import warnings
from pathlib import Path

import numpy as np

from populace_dynamics.artifacts import write_new
from populace_dynamics.cola_track_a.statutory import captured_ssa_parameters
from populace_dynamics.data import epuf
from populace_dynamics.harness import epuf_fill_gate as g
from populace_dynamics.harness.epuf_operator import wage_base

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "populace_dynamics.epuf_fill_gate_floors.v1"
PARTS = {"train": g.TRAIN, "dev": g.DEV}


def _git_head() -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _finite(value: float) -> float | str:
    """JSON-safe: non-finite values become strings."""
    value = float(value)
    return value if np.isfinite(value) else str(value)


def sample_size(
    group: str,
    scale: dict[str, dict[str, int]],
    eligible: np.ndarray,
    birth_year: np.ndarray,
) -> tuple[int, dict[str, float]]:
    """A group's PSID-scale sample size in persons (section 5)."""

    family, _, stratum = group.split(".")
    if family == "odd" and stratum in g.ODD_AGE_BANDS:
        low, high = g.ODD_AGE_BANDS[stratum]
        ages = (
            np.asarray(g.MASKED_ODD_YEARS)[None, :]
            - birth_year[eligible][:, None]
        )
        units = int(((ages >= low) & (ages <= high)).sum())
        per_person = units / int(eligible.sum())
        psid_units = scale[group]["filled_person_years"]
        return int(round(psid_units / per_person)), {
            "psid_filled_person_years": psid_units,
            "dev_units_per_eligible_person": per_person,
        }
    return int(scale[group]["persons"]), {
        "psid_persons": scale[group]["persons"]
    }


def cells_record(cells) -> dict[str, dict[str, object]]:
    return {
        cell_id: {
            "value": _finite(value.value),
            "events": int(value.events),
            "n": int(value.n),
        }
        for cell_id, value in sorted(cells.items())
    }


def judged(truth, filled_draws, tolerance, gating) -> dict[str, object]:
    """Score, plus each gating cell's |gap| in tolerances."""

    family = g.group_of(next(iter(filled_draws[0]))).split(".")[0]
    truth = {k: v for k, v in truth.items() if k.startswith(f"{family}.")}
    result = g.score(truth, filled_draws, tolerance, gating)
    for row in result["cells"].values():
        if "tolerance" in row:
            row["gap_in_tolerances"] = (
                abs(row["gap"]) / row["tolerance"]
                if np.isfinite(row["gap"])
                else float("inf")
            )
        for key in list(row):
            if isinstance(row[key], float):
                row[key] = _finite(row[key])
    return result


def bite_holds(result: dict[str, object], family: str) -> dict[str, object]:
    multiples = [
        float(row["gap_in_tolerances"])
        for cell_id, row in result["cells"].items()
        if cell_id.startswith(f"{family}.") and "gap_in_tolerances" in row
    ]
    beyond = sum(value > g.BITE_MULTIPLE for value in multiples)
    return {
        "family": family,
        "n_gating_cells": len(multiples),
        "n_cells_beyond_bite_multiple": int(beyond),
        "max_gap_in_tolerances": _finite(max(multiples, default=np.nan)),
        "holds": bool(beyond >= 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--psid-scale", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--part", choices=sorted(PARTS), default="dev")
    parser.add_argument("--replicates", type=int, default=g.N_FLOOR_REPLICATES)
    parser.add_argument("--oracle-seeds", type=int, default=None)
    args = parser.parse_args()
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    started = time.time()
    built_at = dt.datetime.now(dt.UTC).isoformat(timespec="seconds")

    scale_document = json.loads(args.psid_scale.read_text())
    scale = scale_document["groups"]
    matrix = g.epuf_matrix(PARTS[args.part])
    earnings, birth, sex = matrix.earnings, matrix.birth_year, matrix.sex
    wage_bases = {year: float(wage_base(year)) for year in g.YEARS}
    nawi = captured_ssa_parameters().nawi

    def family_cells(family, rows=None, matrix_override=None):
        values = earnings if matrix_override is None else matrix_override
        if rows is None:
            return g.family_cells(family, values, birth, sex, wage_bases, nawi)
        return g.family_cells(
            family, values[rows], birth[rows], sex[rows], wage_bases, nawi
        )

    truth = {**family_cells("odd"), **family_cells("pre")}
    print(f"truth: {len(truth)} cells, {time.time() - started:.0f}s")

    groups = sorted({g.group_of(cell_id) for cell_id in truth})
    floors = {}
    group_records = {}
    for index, group in enumerate(groups):
        family = group.split(".")[0]
        eligible = g.group_eligible(group, earnings, birth, sex)
        size, basis = sample_size(group, scale, eligible, birth)
        floor = g.floor_group(
            group,
            lambda rows, family=family: family_cells(family, rows),
            np.flatnonzero(eligible),
            size,
            group_index=index,
            n_replicates=args.replicates,
        )
        floors[group] = floor
        group_records[group] = {
            "group_index": index,
            "sample_size": floor.sample_size,
            "sample_size_basis": basis,
            "pool_size": floor.pool_size,
            # A faithful fill's gap on a part of this size has a standard
            # deviation of at most about this multiple of sigma.
            "noise_ratio": float(np.sqrt(floor.sample_size / floor.pool_size)),
            "seed": list(floor.seed),
            "sigma": {k: _finite(v) for k, v in floor.sigma.items()},
            "replicates": {
                k: [_finite(x) for x in v] for k, v in floor.replicates.items()
            },
            "min_events": {k: list(v) for k, v in floor.min_events.items()},
        }
        print(f"floor {group}: n={size} {time.time() - started:.0f}s")

    reasons = g.partition(truth, floors)
    gating = sorted(c for c, reason in reasons.items() if reason == "gates")
    tolerance = {
        cell_id: g.K_TOLERANCE * floors[g.group_of(cell_id)].sigma[cell_id]
        for cell_id in gating
    }

    b1 = judged(
        truth,
        [family_cells("odd", matrix_override=g.current_odd_fill(earnings))],
        tolerance,
        gating,
    )
    b2 = judged(
        truth,
        [
            family_cells(
                "pre",
                matrix_override=g.current_pre_career_fill(earnings, birth),
            )
        ],
        tolerance,
        gating,
    )
    bites = {
        "B1_current_odd_rule": {**bite_holds(b1, "odd"), "score": b1},
        "B2_current_pre_career_rule": {
            **bite_holds(b2, "pre"),
            "score": b2,
        },
    }
    print(f"bites: {time.time() - started:.0f}s")

    seeds = g.ORACLE_SEEDS[: args.oracle_seeds]
    o1 = [
        family_cells(
            "odd",
            matrix_override=g.odd_oracle_fill(
                earnings, birth, sex, wage_bases, seed
            ),
        )
        for seed in seeds
    ]
    o2 = [
        family_cells(
            "pre",
            matrix_override=g.pre_career_oracle_fill(
                earnings, birth, sex, wage_bases, seed
            ),
        )
        for seed in seeds
    ]
    oracles = {
        "O1_odd_conditional_permutation": judged(truth, o1, tolerance, gating),
        "O2_pre_career_block_permutation": judged(
            truth, o2, tolerance, gating
        ),
        "seeds": list(seeds),
    }
    print(f"oracles: {time.time() - started:.0f}s")

    document = {
        "schema": SCHEMA,
        "registration_id": g.REGISTRATION_ID,
        "part": args.part,
        "registered_build": bool(
            args.part == "dev"
            and args.replicates == g.N_FLOOR_REPLICATES
            and args.oracle_seeds is None
        ),
        "code_commit": _git_head(),
        "built_at_utc": built_at,
        "inputs": {
            "epuf_sha256": dict(epuf.EPUF_SHA256),
            "psid_scale": str(args.psid_scale),
            "psid_scale_sha256": _sha256(args.psid_scale),
        },
        "n_persons": int(len(birth)),
        "constants": {
            "k_tolerance": g.K_TOLERANCE,
            "min_events": g.MIN_EVENTS,
            "events_share": g.EVENTS_SHARE,
            "bite_multiple": g.BITE_MULTIPLE,
            "n_floor_replicates": args.replicates,
            "floor_seed_base": g.FLOOR_SEED_BASE,
        },
        "truth": cells_record(truth),
        "groups": group_records,
        "partition": dict(sorted(reasons.items())),
        "tolerance": {k: _finite(v) for k, v in tolerance.items()},
        "bites": bites,
        "lockable": bool(
            bites["B1_current_odd_rule"]["holds"]
            and bites["B2_current_pre_career_rule"]["holds"]
        ),
        "oracles": oracles,
        "elapsed_seconds": round(time.time() - started, 1),
    }
    write_new(args.output, document, sidecar=True)


if __name__ == "__main__":
    main()
