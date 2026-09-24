"""The committed SSI capture reproduces from policyengine-us.

Oracle tier: reads the policyengine-us checkout that
``POPULACE_DYNAMICS_PE_US_DIR`` (default ``~/PolicyEngine/policyengine-us``)
names and skips when it is absent or its SSI parameter files differ from
the hashes the committed capture records.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from populace_dynamics.estimates import adjusted_poverty as ap

ROOT = Path(__file__).resolve().parents[2]


def _script():
    path = ROOT / "scripts" / "capture_track_u_parameters.py"
    spec = importlib.util.spec_from_file_location("capture_track_u", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ssi_capture_reproduces_from_policyengine_us():
    module = _script()
    root = module.resolve_pe_us(None)
    committed = json.loads(ap.SSI_PARAMETERS_PATH.read_text())
    recorded = committed["source"]["policyengine_us_files_sha256"]
    for relative, digest in recorded.items():
        path = root / relative
        if not path.is_file():
            pytest.skip(f"policyengine-us checkout lacks {relative}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            pytest.skip(f"policyengine-us {relative} differs from the capture")
    rebuilt = module.build_ssi_capture(None)
    rebuilt["source"]["policyengine_us_revision"] = committed["source"][
        "policyengine_us_revision"
    ]
    assert rebuilt == committed
