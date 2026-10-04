"""The registered TEST scoring of gate_epuf_fill's candidates.

One entry point, :func:`score_registered`, does the gate's single TEST
scoring for both families
(``docs/amendments/gate_epuf_fill_registration_proposal.md``, sections 7.3
and 14):

1. it loads the registered DEV floor build and refuses other bytes than
   :data:`REGISTERED_FLOORS_SHA256`;
2. it reads TEST through :func:`epuf_fill_gate.test_part`, which refuses
   until ``gates.yaml`` locks the gate;
3. it computes the truth with ``family_cells`` on that matrix;
4. it scores the current rule, the primary and the alternative of each
   family through ``score_candidate`` over the registered draw seeds;
5. it returns each candidate's tier and the adoption under ``adopt``.

The tolerances and partition come from the registered build only.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

import numpy as np

from populace_dynamics.harness import epuf_fill_gate as g
from populace_dynamics.harness.epuf_cells import CellValue

__all__ = [
    "REGISTERED_FLOORS",
    "REGISTERED_FLOORS_SHA256",
    "load_registered_floors",
    "score_registered",
]

_ROOT = Path(__file__).resolve().parents[3]
REGISTERED_FLOORS = _ROOT / "runs" / "epuf_fill_gate_floors_v3.json"
#: SHA-256 of the registered build; set when the build is committed.
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


def _summary(result: Mapping[str, object]) -> dict[str, object]:
    return {
        "passes": result["passes"],
        "n_gating": result["n_gating"],
        "n_failing": result["n_failing"],
        "cells": result["cells"],
    }


def score_registered(
    candidates: Mapping[str, tuple[object, object]],
    *,
    wage_bases: Mapping[int, float],
    nawi: Mapping[int, float],
    floors_path: Path = REGISTERED_FLOORS,
    floors_sha256: str = REGISTERED_FLOORS_SHA256,
    gates_path: Path | None = None,
    data_dir: Path | None = None,
    seeds=g.DRAW_SEEDS,
    matrix: g.EPUFMatrix | None = None,
) -> dict[str, object]:
    """Score each family's (primary, alternative) on TEST, once.

    ``candidates`` maps ``"odd"`` and/or ``"pre"`` to the two fills. The
    matrix is read through ``test_part`` unless one is passed (tests pass a
    synthetic matrix; the registered run never does).
    """

    floors = load_registered_floors(floors_path, floors_sha256)
    if matrix is None:
        matrix = g.test_part(gates_path=gates_path, data_dir=data_dir)
    record: dict[str, object] = {
        "registration_id": g.REGISTRATION_ID,
        "floors_sha256": floors["sha256"],
        "n_persons": int(len(matrix.birth_year)),
        "seeds": list(seeds),
        "families": {},
    }
    for family, (primary, alternative) in candidates.items():
        truth = g.family_cells(
            family,
            matrix.earnings,
            matrix.birth_year,
            matrix.sex,
            wage_bases,
            nawi,
        )

        def scored(fill, draw_seeds, family=family, truth=truth):
            return g.score_candidate(
                fill,
                family,
                matrix,
                truth,
                floors["tolerance"],
                floors["gating"],
                seeds=draw_seeds,
                wage_bases=wage_bases,
                nawi=nawi,
            )

        current = scored(g.current_rule(family), seeds[:1])
        primary_score = scored(primary, seeds)
        alternative_score = scored(alternative, seeds)
        primary_tier = g.adoption_tier(primary_score, current)
        alternative_tier = g.adoption_tier(alternative_score, current)
        record["families"][family] = {
            "truth": {
                cell: {"value": value.value, "events": value.events}
                for cell, value in truth.items()
                if isinstance(value, CellValue)
            },
            "current_rule": _summary(current),
            "primary": {**_summary(primary_score), "tier": primary_tier},
            "alternative": {
                **_summary(alternative_score),
                "tier": alternative_tier,
            },
            "adopted": g.adopt(primary_tier, alternative_tier),
        }
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
