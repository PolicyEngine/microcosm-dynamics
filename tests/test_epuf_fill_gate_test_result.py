"""gate_epuf_fill's one TEST scoring, as published.

``runs/epuf_fill_gate_test_v1.json`` is the record ``scripts/
score_epuf_fill_test.py`` wrote after the gate locked (decision d927). These
tests hold it to the registration:

- the record, its environment sidecar and its start marker are pinned by
  SHA-256, so no byte of the published record can change;
- it is the registered scoring of the registered candidates against the
  registered floors and constants, run after the lock at a commit on this
  history;
- every recorded gap follows from its recorded filled and true values
  (``epuf_fill_gate.gap``), and every true value from the truth block;
- every pass and failing count, for the current rule's readings and both
  candidates, follows from the gaps and tolerances, and every tier and
  adoption from those under the registered rule (``adoption_tier``,
  ``adopt`` and ``epuf_fill_scoring.combined_current``).

Nothing here reads TEST.
"""

from __future__ import annotations

import datetime as dt
import hashlib
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
#: The published bytes.
PINNED_SHA256 = {
    RESULT: "9fa726be90134546c54148d681209ccf4a33939a7d6e2cfe5c2e384832dace03",
    SIDECAR: "02bcfab5bf3546abdf8f5b7b03d6aaf6ad452b5c7205217cd11d3f490b80a699",
    STARTED: "82240cf15e7c81ef8b400bd4c6d18851b0cbd1d02238277ed629ba3243c6250c",
}


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


def test_the_published_bytes_are_pinned():
    for path, sha256 in PINNED_SHA256.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == sha256, path


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
    assert result["constants_sha256"] == scoring.constants()[2]
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


def _records(entry):
    """Every recorded score of a family: the current rule's and the roles'."""

    yield from entry["current_rule"].items()
    for role in ("primary", "alternative"):
        yield role, entry[role]


@pytest.mark.parametrize("family", ["odd", "pre"])
def test_every_gap_follows_from_its_values(result, family):
    entry = result["families"][family]
    truth = entry["truth"]
    for name, record in _records(entry):
        for cell, row in record["cells"].items():
            assert float(row["truth"]) == float(truth[cell]["value"]) or (
                math.isnan(float(row["truth"]))
                and math.isnan(float(truth[cell]["value"]))
            ), (name, cell)
            derived = g.gap(cell, float(row["filled"]), float(row["truth"]))
            recorded = float(row["gap"])
            assert recorded == derived or (
                math.isnan(recorded) and math.isnan(derived)
            ), (name, cell)


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
    for name, record in _records(entry):
        score = _restored(record)
        gated = {c: r for c, r in score["cells"].items() if "passes" in r}
        assert sorted(gated) == gating, name
        for cell, row in gated.items():
            assert row["tolerance"] == floors["tolerance"][cell]
            within = math.isfinite(row["gap"]) and (
                abs(row["gap"]) <= row["tolerance"]
            )
            assert row["passes"] == within, (name, cell)
        failing = sum(not row["passes"] for row in gated.values())
        assert score["n_failing"] == failing, name
        assert score["n_gating"] == len(gating), name
        assert score["passes"] == (failing == 0), name
    readings = [_restored(r) for r in entry["current_rule"].values()]
    reference = scoring.combined_current(*readings)
    tiers = {
        role: g.adoption_tier(_restored(entry[role]), reference)
        for role in ("primary", "alternative")
    }
    for role, tier in tiers.items():
        assert tier == entry[role]["tier"], role
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
    current = {
        family: {
            name: reading["n_failing"]
            for name, reading in result["families"][family][
                "current_rule"
            ].items()
        }
        for family in ("odd", "pre")
    }
    assert current == {
        "odd": {"fallback": 100, "two_sided": 99},
        "pre": {"fallback": 131},
    }
    assert result["n_persons"] == 878481
