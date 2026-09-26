"""The quarter-of-coverage capture recaptured from policyengine-us.

Needs the policyengine-us checkout the oracle reads
(``POPULACE_DYNAMICS_PE_US_DIR`` or ``~/PolicyEngine/policyengine-us``);
skipped without it.  The capture script's in-memory recapture must equal
the committed file byte for byte, and every committed amount must equal
the one 42 USC 413(d) sets from the oracle's wage index (a differential
check of the file against the statute).
"""

from __future__ import annotations

import importlib.util
import os
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


def test_the_recapture_equals_the_committed_file():
    script = _script()
    fresh = script.serialize(script.build())
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
