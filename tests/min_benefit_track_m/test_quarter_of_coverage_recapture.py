"""The quarter-of-coverage capture recaptured from policyengine-us.

Needs the policyengine-us checkout the oracle reads
(``POPULACE_DYNAMICS_PE_US_DIR`` or ``~/PolicyEngine/policyengine-us``);
skipped without it.  The capture script's in-memory recapture must equal
the committed file byte for byte (skipped unless the checkout holds the
files and revisions the committed file records), and every committed amount must equal
the one 42 USC 413(d) sets from the oracle's wage index (a differential
check of the file against the statute).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
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


def _require_the_captured_checkout():
    """Skip unless the checkout holds what the committed capture records.

    The capture's bytes carry the quarter-of-coverage file, the wage-index
    file and the revision each loader reported, so any of them differing
    is a different input, not a different recapture.
    """
    from populace_dynamics.ss.params import load_ssa_parameters

    committed = json.loads(coverage.QC_CAPTURE_PATH.read_text())
    root = coverage._resolve_pe_us(None)
    source = committed["source"]
    wage_index = committed["value_check"]["wage_index"]
    unpinned = []
    for record in (source, wage_index):
        path = root / record["path"]
        if not path.is_file():
            unpinned.append(f"{path} is absent")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
            unpinned.append(f"{path} is not the captured file")
    if not unpinned:
        revisions = (
            (source, coverage.load_qc_amounts_from_checkout().source),
            (
                wage_index,
                {"pe_us_revision": load_ssa_parameters().pe_us_revision},
            ),
        )
        for record, observed in revisions:
            if observed["pe_us_revision"] != record["pe_us_revision"]:
                unpinned.append(
                    f"{record['path']} was read at revision "
                    f"{observed['pe_us_revision']!r}, not the captured "
                    f"{record['pe_us_revision']!r}"
                )
    if unpinned:
        pytest.skip(
            f"policyengine-us checkout {root} is not the captured one: "
            + "; ".join(unpinned)
        )


def test_the_recapture_equals_the_committed_file():
    _require_the_captured_checkout()
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
