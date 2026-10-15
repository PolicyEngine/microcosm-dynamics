"""The quarter-of-coverage capture recaptured from policyengine-us.

Needs the policyengine-us checkout the oracle reads
(``POPULACE_DYNAMICS_PE_US_DIR`` or ``~/PolicyEngine/policyengine-us``);
skipped without it.  The capture script's in-memory recapture must equal
the committed file byte for byte (skipped unless the checkout holds the
files and the revision the committed file records), and every committed
amount must equal the one 42 USC 413(d) sets from the oracle's wage index
(a differential check of the file against the statute).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest

from populace_dynamics.min_benefit_track_m import coverage

ROOT = Path(__file__).resolve().parents[2]
_PE_US = Path(
    os.environ.get(
        "POPULACE_DYNAMICS_PE_US_DIR", "~/PolicyEngine/policyengine-us"
    )
).expanduser()
pytestmark = pytest.mark.skipif(
    not (_PE_US / "policyengine_us").is_dir(),
    reason="needs a policyengine-us checkout (POPULACE_DYNAMICS_PE_US_DIR)",
)


def _script():
    path = ROOT / "scripts" / "capture_track_m_quarter_of_coverage.py"
    spec = importlib.util.spec_from_file_location("_qc_capture", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _captured():
    return json.loads(coverage.QC_CAPTURE_PATH.read_text())


def _without_revisions(document):
    document["source"].pop("pe_us_revision")
    document["value_check"]["wage_index"].pop("pe_us_revision")
    return document


def _skip_unless_captured_files(root, committed):
    """Skip unless the checkout holds the files the capture records."""
    unpinned = []
    for record in (
        committed["source"],
        committed["value_check"]["wage_index"],
    ):
        path = root / record["path"]
        if not path.is_file():
            unpinned.append(f"{path} is absent")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
            unpinned.append(f"{path} is not the captured file")
    if unpinned:
        pytest.skip(
            f"policyengine-us checkout {root} is not the captured one: "
            + "; ".join(unpinned)
        )


def _skip_unless_captured_revision(root, committed):
    """Skip unless git reports the revision the capture records.

    Read from git directly rather than through the loaders under test, so
    a change to how they record the revision still fails the recapture.
    """
    try:
        completed = subprocess.run(
            ["git", "log", "-1", "--format=%h"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:  # no git: the revision cannot be the pin
        completed = None
    revision = (
        completed.stdout.strip()
        if completed is not None and completed.returncode == 0
        else ""
    )
    recorded = {
        committed["source"]["pe_us_revision"],
        committed["value_check"]["wage_index"]["pe_us_revision"],
    }
    # One checkout was captured; two revisions would make this skip forever.
    assert len(recorded) == 1, recorded
    if recorded != {revision}:
        pytest.skip(
            f"policyengine-us checkout {root} is at {revision!r}, not the "
            f"captured {sorted(recorded)!r}"
        )


def test_the_recapture_equals_the_committed_file():
    committed = _captured()
    root = coverage._resolve_pe_us(None)
    _skip_unless_captured_files(root, committed)
    script = _script()
    # build() checks every amount against the statute, and the captured
    # files fix every field but the two recorded revisions, so compare the
    # rest at any commit; only the bytes need the captured one.
    fresh = script.serialize(script.build())
    assert _without_revisions(json.loads(fresh)) == _without_revisions(
        _captured()
    )
    _skip_unless_captured_revision(root, committed)
    assert fresh == coverage.QC_CAPTURE_PATH.read_bytes()


def test_every_amount_is_the_statutes():
    from populace_dynamics.ss.params import load_ssa_parameters

    captured = coverage.load_qc_amounts().amounts
    statute = coverage.statutory_qc_amounts(
        load_ssa_parameters().nawi, max(captured)
    )
    assert {year: statute[year] for year in captured} == dict(captured)
    checkout = coverage.load_qc_amounts_from_checkout().amounts
    assert dict(checkout) == dict(captured)
