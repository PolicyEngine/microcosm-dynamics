"""The registered TEST scoring path, on synthetic matrices."""

from __future__ import annotations

import hashlib
import json

import numpy as np
import pytest

from populace_dynamics.cola_track_a.statutory import captured_ssa_parameters
from populace_dynamics.harness import epuf_fill_gate as g
from populace_dynamics.harness import epuf_fill_scoring as scoring
from populace_dynamics.harness.epuf_operator import disclosure_constants

WAGE_BASES = {
    year: float(row["wage_base"])
    for year, row in disclosure_constants().items()
}
NAWI = captured_ssa_parameters().nawi


def _matrix(seed=31, n=1_200):
    rng = np.random.default_rng(seed)
    birth = rng.integers(1925, 1981, size=n)
    sex = rng.choice([1, 2], size=n)
    caps = np.array([WAGE_BASES[year] for year in g.YEARS])
    level = rng.normal(-1.2, 0.8, size=n)
    shares = np.exp(
        level[:, None] + rng.normal(0, 0.3, (n, len(g.YEARS))).cumsum(1) * 0.2
    )
    work = rng.random((n, len(g.YEARS))) < 0.8
    age = np.asarray(g.YEARS)[None, :] - birth[:, None]
    earnings = np.where(
        work & (age >= 15), np.minimum(shares, 1.0) * caps, 0.0
    )
    return g.EPUFMatrix(
        person_id=np.arange(n) + 1,
        birth_year=birth,
        sex=sex,
        earnings=np.round(earnings),
    )


def _floors(tmp_path, gating, tolerance=10.0):
    document = {
        "registered_build": True,
        "lockable": True,
        "partition": {cell: "gates" for cell in gating},
        "tolerance": {cell: tolerance for cell in gating},
    }
    path = tmp_path / "floors.json"
    path.write_text(json.dumps(document))
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def test_registered_floors_are_hash_checked(tmp_path):
    path, sha = _floors(tmp_path, ["odd.men.a30_44.r1"])
    loaded = scoring.load_registered_floors(path, sha)
    assert loaded["gating"] == ["odd.men.a30_44.r1"]
    with pytest.raises(ValueError, match="SHA-256"):
        scoring.load_registered_floors(path, "0" * 64)


def _spec():
    return {
        "primary": ("primary.npz", "0" * 64),
        "alternative": ("alt.npz", "1" * 64),
    }


def test_score_registered_scores_the_current_rule_and_both_candidates(
    tmp_path,
):
    matrix = _matrix()
    truth = g.family_cells(
        "odd",
        matrix.earnings,
        matrix.birth_year,
        matrix.sex,
        WAGE_BASES,
        NAWI,
    )
    # Cells the current rule moves by a finite amount.
    gating = [
        cell
        for cell, value in truth.items()
        if cell.rsplit(".", 1)[1] in ("r1", "level", "aime_p50", "q50")
        and np.isfinite(value.value)
        and value.value > 0
    ]
    path, sha = _floors(tmp_path, gating)
    record = scoring.score_registered(
        {"odd": _spec()},
        floors_path=path,
        floors_sha256=sha,
        matrix=matrix,
        seeds=(7100, 7101),
        fills={
            "odd": {
                "primary": g.CurrentOddFill(),
                "alternative": g.CurrentOddFill(),
            }
        },
    )
    family = record["families"]["odd"]
    # A candidate identical to the current rule scores exactly as its
    # fallback reading does and, within the wide synthetic tolerance,
    # certifies; both readings of the current rule are reported.
    fallback = family["current_rule"]["fallback"]
    assert family["primary"]["n_failing"] == fallback["n_failing"]
    assert set(family["current_rule"]) == {"fallback", "two_sided"}
    assert family["primary"]["tier"] == "certified"
    assert family["adopted"] == "primary"
    assert record["floors_sha256"] == sha
    assert record["constants_sha256"] == scoring.constants()[2]
    assert record["candidates"]["odd"]["primary"]["sha256"] == "0" * 64


def test_undefined_test_truth_is_dropped_and_reported():
    truth = {
        "odd.men.a30_44.r1": g.CellValue(0.9, 10, 10),
        "odd.men.a30_44.zint": g.CellValue(0.0, 0, 10),
        "odd.men.a30_44.level": g.CellValue(float("nan"), 0, 0),
    }
    kept, dropped = scoring.defined_gating(truth, sorted(truth))
    assert kept == ["odd.men.a30_44.r1"]
    assert dropped == ["odd.men.a30_44.level", "odd.men.a30_44.zint"]


def test_combined_current_takes_the_smaller_gap_per_cell():
    def score(gaps, failing):
        return {
            "cells": {f"c{i}": {"gap": x} for i, x in enumerate(gaps)},
            "n_failing": failing,
            "passes": False,
        }

    combined = scoring.combined_current(
        score([0.5, -np.inf, -0.2], 3), score([0.1, 0.4, -np.inf], 2)
    )
    assert [combined["cells"][f"c{i}"]["gap"] for i in range(3)] == [
        0.1,
        0.4,
        -0.2,
    ]
    assert combined["n_failing"] == 2


def test_registered_candidates_are_hash_checked(tmp_path):
    path, sha = _floors(tmp_path, ["odd.men.a30_44.r1"])
    pytest.importorskip("populace_dynamics.estimates.epuf_fill")
    with pytest.raises((ValueError, FileNotFoundError)):
        scoring.score_registered(
            {"odd": {"primary": (tmp_path / "missing.npz", "0" * 64)}},
            floors_path=path,
            floors_sha256=sha,
            matrix=_matrix(n=50),
        )


def test_score_registered_reads_test_only_through_the_lock(tmp_path):
    path, sha = _floors(tmp_path, ["odd.men.a30_44.r1"])
    gates = tmp_path / "gates.yaml"
    gates.write_text("gates: {}\n")
    with pytest.raises(g.TestPartLocked):
        scoring.score_registered(
            {"odd": _spec()},
            floors_path=path,
            floors_sha256=sha,
            gates_path=gates,
            fills={
                "odd": {
                    "primary": g.CurrentOddFill(),
                    "alternative": g.CurrentOddFill(),
                }
            },
        )
