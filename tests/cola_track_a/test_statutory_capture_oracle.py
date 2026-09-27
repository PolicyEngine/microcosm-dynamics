"""The committed statutory capture reproduces from policyengine-us.

Oracle tier: reads the policyengine-us checkout that
``POPULACE_DYNAMICS_PE_US_DIR`` (default ``~/PolicyEngine/policyengine-us``)
names, and skips when the checkout is absent, its parameter files are
not the ones the repository pins
(``estimates.parameters.SSA_PARAMETER_SHA256``).  The statutory checks
run on the pinned files at any commit; the comparisons that carry the
checkout's revision skip unless git reports the one the capture records.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

from populace_dynamics.cola_track_a import statutory
from populace_dynamics.estimates import parameters
from populace_dynamics.ss import params as ss_params

ROOT = Path(__file__).resolve().parents[2]


def _capture_script():
    path = ROOT / "scripts" / "capture_track_a_statutory_parameters.py"
    spec = importlib.util.spec_from_file_location("capture_statutory", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _pinned_checkout() -> Path:
    root = ss_params._resolve_pe_us(None)
    for relative, expected in parameters.SSA_PARAMETER_SHA256.items():
        path = root / relative
        if not path.is_file():
            pytest.skip(f"policyengine-us parameter file absent: {path}")
        if parameters._sha256(path.read_bytes()) != expected:
            pytest.skip(f"policyengine-us file {path} is not the pinned one")
    return root


def _skip_unless_captured_revision(root: Path, *, exact: bool) -> str:
    """Skip when the checkout is not at the commit the capture records.

    The capture carries the checkout's abbreviated revision as well as the
    file digests, so the same files at another commit are a different
    input.  The revision comes from git directly, not from the loader
    under test, so a change to how the loader records it still fails.
    ``exact`` demands the recorded string itself (a byte-for-byte
    recapture); otherwise it must prefix git's abbreviation.
    """
    captured = json.loads(statutory.CAPTURE_PATH.read_text())["source"][
        "policyengine_us_revision"
    ]
    completed = subprocess.run(
        ["git", "log", "-1", "--format=%h"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    revision = completed.stdout.strip() if completed.returncode == 0 else ""
    if not (revision == captured if exact else revision.startswith(captured)):
        pytest.skip(
            f"policyengine-us checkout {root} is at {revision!r}, not the "
            f"captured {captured!r}"
        )
    return captured


def test_capture_script_reproduces_the_committed_capture(tmp_path):
    root = _pinned_checkout()
    module = _capture_script()
    output = tmp_path / "capture.json"
    assert (
        module.main(["--pe-us-dir", str(root), "--output", str(output)]) == 0
    )
    # The script's own checks ran above; only the bytes need the commit.
    _skip_unless_captured_revision(root, exact=True)
    assert output.read_bytes() == statutory.CAPTURE_PATH.read_bytes()


def test_oracle_parameters_pass_every_statutory_check():
    from populace_dynamics.cola_track_a.runner import (
        tr2008_baseline_cola,
        tr2008_ssa_parameters,
    )
    from populace_dynamics.estimates.parameters import load_cola_history

    root = _pinned_checkout()
    runtime = tr2008_ssa_parameters(ss_params.load_ssa_parameters(root))
    checks = statutory.statutory_value_checks(
        runtime,
        tr2008_baseline_cola(load_cola_history()),
        first_tr2008_rate_year=2008,
        reference_year=2030,
        last_earnings_year=2010,
    )
    inconsistent = {
        name: check["mismatched"]
        for name, check in checks.items()
        if not check["consistent"]
    }
    assert inconsistent == {}
    captured = _skip_unless_captured_revision(root, exact=False)
    assert runtime.pe_us_revision.startswith(captured)
