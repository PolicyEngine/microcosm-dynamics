"""Reproduce the default DI diagnostic with the statutory FRA schedule.

The FRA schedule comes from :func:`populace_dynamics.ss.params.load_ssa_parameters`,
which reads the policyengine-us parameter tree (``POPULACE_DYNAMICS_PE_US_DIR``
or the default checkout).  The test skips when that tree is absent.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from populace_dynamics.engine.di_entitlement_rates import DEFAULT_INPUTS_PATH
from populace_dynamics.ss.params import load_ssa_parameters

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs" / "di_entitlement_asr2023_validation_v1.json"
sys.path.insert(0, str(ROOT / "scripts"))

import validate_di_entitlement_asr2023 as validation  # noqa: E402


def test_default_diagnostic_reproduces_exactly():
    try:
        params = load_ssa_parameters()
    except FileNotFoundError:
        pytest.skip("the policyengine-us parameter tree is not installed")
    artifact = json.loads(RUN.read_text(encoding="utf-8"))
    assert artifact["fra_schedule"]["policyengine_us_revision"]
    inputs = json.loads(DEFAULT_INPUTS_PATH.read_text(encoding="utf-8"))
    result = validation.run_variant(
        validation.VARIANTS["default"],
        validation.synthetic_opening_population(inputs),
        params.fra_months,
        validation.nchs_2000_mortality(),
    )
    expected = artifact["variants"]["default"]["years"]
    assert json.loads(json.dumps(result["years"])) == expected
