"""gate_epuf_fill's one TEST scoring, as published.

``runs/epuf_fill_gate_test_v1.json`` is the record ``scripts/
score_epuf_fill_test.py`` wrote after the gate locked (decision d927). These
tests hold it to the registration: it is the registered scoring of the
registered candidates against the registered floors, and every published
pass, failing count, tier and adoption follows from its recorded cells
under the registered rule (``epuf_fill_gate.adoption_tier`` and ``adopt``
and ``epuf_fill_scoring.combined_current``). Nothing here reads TEST.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import math
import subprocess
from pathlib import Path

import pytest
import yaml

from populace_dynamics.harness import epuf_fill_gate as g
from populace_dynamics.harness import epuf_fill_scoring as scoring

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "runs" / "epuf_fill_gate_test_v1.json"
SIDECAR = ROOT / "runs" / "epuf_fill_gate_test_v1.json.env.json"
STARTED = ROOT / "runs" / "epuf_fill_gate_test_v1.json.started.json"


@pytest.fixture(scope="module")
def result():
    return json.loads(RESULT.read_text())


def _score_script():
    spec = importlib.util.spec_from_file_location(
        "score_epuf_fill_test", ROOT / "scripts" / "score_epuf_fill_test.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args], capture_output=True, text=True
    )


def test_it_is_the_registered_scoring(result):
    assert result["schema"] == "populace_dynamics.epuf_fill_gate_test.v1"
    assert result["registered_test_scoring"] is True
    assert result["injected"] == {
        "matrix": False,
        "fills": False,
        "gates_path": False,
        "data_dir": False,
    }
    assert result["registration_id"] == g.REGISTRATION_ID
    assert result["floors_sha256"] == scoring.REGISTERED_FLOORS_SHA256
    script = _score_script()
    assert result["manifest_sha256"] == script.REGISTERED_MANIFEST_SHA256
    assert result["manifest"] == "runs/epuf_fill_candidates_v1.json"
    assert result["code_files_clean"] is True
    assert result["seeds"] == list(g.DRAW_SEEDS)
    manifest = json.loads((ROOT / result["manifest"]).read_text())
    for family, roles in result["candidates"].items():
        for role, record in roles.items():
            (fill,) = [
                f
                for f in manifest["fills"].values()
                if f["family"] == family and f["role"] == role
            ]
            assert record == {"path": fill["file"], "sha256": fill["sha256"]}


def test_it_ran_after_the_lock_at_a_commit_on_this_history(result):
    started = json.loads(STARTED.read_text())
    assert started["manifest_sha256"] == result["manifest_sha256"]
    start = dt.datetime.fromisoformat(started["started_at_utc"])
    end = dt.datetime.fromisoformat(result["scored_at_utc"])
    assert start < end
    sidecar = json.loads(SIDECAR.read_text())
    assert sidecar["contract"]["path"] == "gates.yaml"
    assert sidecar["contract"]["head_sha"] == result["code_commit"]
    commit = result["code_commit"]
    if _git("cat-file", "-e", f"{commit}^{{commit}}").returncode:
        pytest.skip("the scoring commit is not in this clone")
    assert _git("merge-base", "--is-ancestor", commit, "HEAD").returncode == 0
    contract = _git("rev-parse", f"{commit}:gates.yaml").stdout.strip()
    assert contract == sidecar["contract"]["blob_sha"]
    gates = yaml.safe_load(_git("show", f"{commit}:gates.yaml").stdout)
    block = gates["gates"]["gate_epuf_fill"]
    assert block["locked"] is True and block["thresholds"]["locked"] is True
    assert block["registration_id"] == g.REGISTRATION_ID


def _restored(record):
    """A recorded score with its numbers restored (non-finite as text)."""

    cells = {}
    for cell, row in record["cells"].items():
        cells[cell] = {
            key: float(value) if key in ("gap", "tolerance") else value
            for key, value in row.items()
        }
    return {**record, "cells": cells}


@pytest.mark.parametrize("family", ["odd", "pre"])
def test_every_published_verdict_follows_from_its_cells(result, family):
    floors = scoring.load_registered_floors()
    entry = result["families"][family]
    gating = sorted(
        c
        for c in floors["gating"]
        if c.startswith(f"{family}.")
        and c not in entry["dropped_undefined_truth"]
    )
    readings = [_restored(r) for r in entry["current_rule"].values()]
    reference = scoring.combined_current(*readings)
    tiers = {}
    for role in ("primary", "alternative"):
        score = _restored(entry[role])
        gated = {c: r for c, r in score["cells"].items() if "passes" in r}
        assert sorted(gated) == gating
        for cell, row in gated.items():
            assert row["tolerance"] == floors["tolerance"][cell]
            within = math.isfinite(row["gap"]) and (
                abs(row["gap"]) <= row["tolerance"]
            )
            assert row["passes"] == within, cell
        failing = sum(not row["passes"] for row in gated.values())
        assert score["n_failing"] == failing
        assert score["n_gating"] == len(gating)
        assert score["passes"] == (failing == 0)
        tiers[role] = g.adoption_tier(score, reference)
        assert tiers[role] == entry[role]["tier"]
    assert g.adopt(tiers["primary"], tiers["alternative"]) == entry["adopted"]


def test_the_published_outcome(result):
    odd, pre = result["families"]["odd"], result["families"]["pre"]
    assert odd["primary"]["tier"] == "improves"
    assert odd["primary"]["n_failing"] == 8
    assert odd["alternative"]["tier"] == "not_adopted"
    assert odd["adopted"] == "primary"
    assert pre["primary"]["tier"] == "certified"
    assert pre["primary"]["n_failing"] == 0
    assert pre["alternative"]["tier"] == "not_adopted"
    assert pre["adopted"] == "primary"
    assert result["n_persons"] == 878481
