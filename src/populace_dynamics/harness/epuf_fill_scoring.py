"""The registered TEST scoring of gate_epuf_fill's candidates.

One entry point, :func:`score_registered`, does the gate's single TEST
scoring for both families
(``docs/amendments/gate_epuf_fill_registration_proposal.md``, sections 7.3
and 14):

1. it loads the registered DEV floor build and refuses other bytes than
   :data:`REGISTERED_FLOORS_SHA256`;
2. it loads each family's two registered candidates and refuses other
   bytes than their registered SHA-256;
3. it reads TEST through :func:`epuf_fill_gate.test_part`, which refuses
   until ``gates.yaml`` locks the gate;
4. it builds the wage bases and NAWI itself (EPUF's and the committed
   capture's) and records their hashes;
5. it computes the truth with ``family_cells`` on that matrix, and drops
   from every score a gating cell whose TEST truth is undefined (not
   finite, or not positive for a log ratio), reporting it;
6. it scores the current rule and both candidates of each family through
   ``score_candidate`` over the registered draw seeds;
7. it returns each candidate's tier and the adoption under ``adopt``.

**The current rule's gap, for the "improves" tier.** The odd-year rule has
two readings at age 22, where the year before is pre-career: the
assembler averages it in when the PSID recorded it (``_impute_gap``) and
falls back to the other neighbour when not. The scoring path hides
pre-career years, so its current rule always falls back
(:class:`epuf_fill_gate.CurrentOddFill`); the two-sided reading averages
the true pre-career year in (``current_odd_fill`` on the truth). Where they
differ, the improves allowance uses the smaller of the two current gaps in
each cell, and "strictly fewer failing cells" counts against the smaller
of the two failing counts (referee round 3, finding 1). The pre-career rule
has one reading.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

import numpy as np

from populace_dynamics.harness import epuf_fill_gate as g

__all__ = [
    "REGISTERED_FLOORS",
    "REGISTERED_FLOORS_SHA256",
    "combined_current",
    "constants",
    "defined_gating",
    "load_registered_floors",
    "score_registered",
]

_ROOT = Path(__file__).resolve().parents[3]
REGISTERED_FLOORS = _ROOT / "runs" / "epuf_fill_gate_floors_v3.json"
#: SHA-256 of the registered build.
REGISTERED_FLOORS_SHA256 = (
    "d403a824416f00524fadceefb897f5bdcaa197c12ebee0b1f1fd52304d98e25e"
)


def load_registered_floors(
    path: Path = REGISTERED_FLOORS,
    sha256: str = REGISTERED_FLOORS_SHA256,
) -> dict[str, object]:
    """The registered build's tolerances and gating cells, hash-checked."""

    data = Path(path).read_bytes()
    observed = hashlib.sha256(data).hexdigest()
    if observed != sha256:
        raise ValueError(
            f"{path} has SHA-256 {observed}, not the registered {sha256}"
        )
    floors = json.loads(data)
    if not floors.get("registered_build") or not floors.get("lockable"):
        raise ValueError(f"{path} is not a registered, lockable build")
    gating = sorted(
        cell
        for cell, reason in floors["partition"].items()
        if reason == "gates"
    )
    return {
        "tolerance": {k: float(v) for k, v in floors["tolerance"].items()},
        "gating": gating,
        "sha256": observed,
    }


def constants() -> tuple[dict[int, float], dict[int, float], str]:
    """EPUF's wage bases, the capture's NAWI, and a hash of both."""

    from populace_dynamics.cola_track_a.statutory import (
        captured_ssa_parameters,
    )
    from populace_dynamics.harness.epuf_operator import wage_base

    wage_bases = {year: float(wage_base(year)) for year in g.YEARS}
    nawi = {
        int(year): float(value)
        for year, value in captured_ssa_parameters().nawi.items()
    }
    digest = hashlib.sha256(
        json.dumps(
            {"wage_bases": wage_bases, "nawi": nawi}, sort_keys=True
        ).encode()
    ).hexdigest()
    return wage_bases, nawi, digest


def defined_gating(truth, gating) -> tuple[list[str], list[str]]:
    """Gating cells whose truth is defined, and those dropped (reported)."""

    kept, dropped = [], []
    for cell in gating:
        value = truth[cell].value if cell in truth else np.nan
        undefined = not np.isfinite(value) or (
            g.cell_metric(cell) == "log_ratio" and value <= 0
        )
        (dropped if undefined else kept).append(cell)
    return kept, dropped


def combined_current(*scores: Mapping[str, object]) -> dict[str, object]:
    """The current rule's score with the smaller gap in each cell.

    Used only for the "improves" allowance and the failing-count
    comparison; every reading's own score is reported as well.
    """

    first = scores[0]
    cells = {}
    for cell, row in first["cells"].items():
        gaps = [float(score["cells"][cell]["gap"]) for score in scores]
        magnitudes = [abs(x) if np.isfinite(x) else np.inf for x in gaps]
        cells[cell] = {**row, "gap": gaps[int(np.argmin(magnitudes))]}
    return {
        "cells": cells,
        "n_failing": min(int(score["n_failing"]) for score in scores),
        "passes": any(score["passes"] for score in scores),
    }


def _summary(result: Mapping[str, object]) -> dict[str, object]:
    return {
        "passes": result["passes"],
        "n_gating": result["n_gating"],
        "n_failing": result["n_failing"],
        "cells": result["cells"],
    }


def _two_sided_current(matrix, truth, tolerance, gating, wage_bases, nawi):
    """The odd-year rule averaging the true pre-career year in."""

    own = g.family_mask("odd", matrix.birth_year)
    earnings = np.where(
        own,
        g.current_odd_fill(matrix.earnings, matrix.birth_year),
        matrix.earnings,
    )
    caps = np.array([float(wage_bases[year]) for year in g.YEARS])
    earnings = np.minimum(earnings, caps[None, :])
    cells = g.family_cells(
        "odd", earnings, matrix.birth_year, matrix.sex, wage_bases, nawi
    )
    family_truth = {k: v for k, v in truth.items() if k.startswith("odd.")}
    return g.score(family_truth, [cells], tolerance, gating)


def score_registered(
    candidates: Mapping[str, Mapping[str, tuple[Path, str]]],
    *,
    floors_path: Path = REGISTERED_FLOORS,
    floors_sha256: str = REGISTERED_FLOORS_SHA256,
    gates_path: Path | None = None,
    data_dir: Path | None = None,
    seeds=g.DRAW_SEEDS,
    matrix: g.EPUFMatrix | None = None,
    fills: Mapping[str, Mapping[str, object]] | None = None,
) -> dict[str, object]:
    """Score each family's registered primary and alternative on TEST, once.

    ``candidates`` maps ``"odd"`` and/or ``"pre"`` to ``{"primary": (path,
    sha256), "alternative": (path, sha256)}``; each artifact is loaded with
    :func:`populace_dynamics.estimates.epuf_fill.load_fill`, which refuses
    other bytes. The matrix is read through ``test_part`` unless one is
    passed, and ``fills`` may replace the loaded candidates; tests use both,
    and the registered run uses neither.
    """

    floors = load_registered_floors(floors_path, floors_sha256)
    wage_bases, nawi, constants_sha256 = constants()
    loaded: dict[str, dict[str, object]] = {}
    for family, spec in candidates.items():
        if fills is not None:
            loaded[family] = dict(fills[family])
            continue
        from populace_dynamics.estimates import epuf_fill

        loaded[family] = {
            role: epuf_fill.load_fill(Path(path), sha256=sha256)
            for role, (path, sha256) in spec.items()
        }
    if matrix is None:
        matrix = g.test_part(gates_path=gates_path, data_dir=data_dir)
    record: dict[str, object] = {
        "registration_id": g.REGISTRATION_ID,
        "floors_sha256": floors["sha256"],
        "constants_sha256": constants_sha256,
        "candidates": {
            family: {
                role: {"path": str(path), "sha256": sha256}
                for role, (path, sha256) in spec.items()
            }
            for family, spec in candidates.items()
        },
        "n_persons": int(len(matrix.birth_year)),
        "seeds": list(seeds),
        "families": {},
    }
    for family, roles in loaded.items():
        truth = g.family_cells(
            family,
            matrix.earnings,
            matrix.birth_year,
            matrix.sex,
            wage_bases,
            nawi,
        )
        family_gating = [
            c for c in floors["gating"] if c.startswith(f"{family}.")
        ]
        gating, dropped = defined_gating(truth, family_gating)

        def scored(
            fill, draw_seeds, family=family, truth=truth, gating=gating
        ):
            return g.score_candidate(
                fill,
                family,
                matrix,
                truth,
                floors["tolerance"],
                gating,
                seeds=draw_seeds,
                wage_bases=wage_bases,
                nawi=nawi,
            )

        readings = {"fallback": scored(g.current_rule(family), seeds[:1])}
        if family == "odd":
            readings["two_sided"] = _two_sided_current(
                matrix, truth, floors["tolerance"], gating, wage_bases, nawi
            )
        reference = combined_current(*readings.values())
        entry: dict[str, object] = {
            "dropped_undefined_truth": dropped,
            "truth": {
                cell: {"value": value.value, "events": value.events}
                for cell, value in truth.items()
            },
            "current_rule": {
                name: _summary(score) for name, score in readings.items()
            },
        }
        tiers = {}
        for role, fill in roles.items():
            score = scored(fill, seeds)
            tiers[role] = g.adoption_tier(score, reference)
            entry[role] = {**_summary(score), "tier": tiers[role]}
        entry["adopted"] = g.adopt(
            tiers.get("primary", "not_adopted"),
            tiers.get("alternative", "not_adopted"),
        )
        record["families"][family] = entry
    return _jsonable(record)


def _jsonable(value):
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, float | np.floating):
        return float(value) if np.isfinite(value) else str(float(value))
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value
