"""Host-only: the committed exercise-4 run reproduces exactly (NASI G4c).

Integration tier (staged PSID under ``POPULACE_DYNAMICS_PSID_DIR`` or
``~/PolicyEngine/psid-data``).  Re-executes Registration 17's registered
computation on the staged PSID exactly as the registered runner did
(:func:`min_benefit.reproduce_parent`) and asserts that every recomputed
block equals the committed artifact (floats bit for bit; the COLA
history's location compared by its repository-relative path).  That is
the precondition of any group breakdown, checked here on its own: no
side frame is loaded, no group attribute or group cell is computed, and
nothing is written or printed (a mismatch names paths only).  It
recomputes the committed, published cells; it produces no new outcome.

It skips unless all three hold: the staged PSID files exist; the oracle's
policyengine-us checkout is at the parent's revision (``a03e82e503``);
and Python, numpy, pandas and scipy are the versions the parent's sidecar
records (build them with ``scripts/make_nasi_repro_venv.sh``).
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
import os
import platform
from pathlib import Path

import pytest

from populace_dynamics.group_breakdowns import common
from populace_dynamics.group_breakdowns import min_benefit as mb

ROOT = Path(__file__).resolve().parents[2]
PSID_DIR = Path(
    os.environ.get("POPULACE_DYNAMICS_PSID_DIR", "~/PolicyEngine/psid-data")
).expanduser()


def _environment_matches(sidecar: dict) -> list[str]:
    recorded = sidecar["environment"]
    here = {
        "python": platform.python_version(),
        **{
            name: importlib.metadata.version(name)
            for name in ("numpy", "pandas", "scipy")
        },
    }
    wanted = {
        "python": recorded["python"],
        **{
            name: recorded["packages"][name]
            for name in ("numpy", "pandas", "scipy")
        },
    }
    return [name for name in wanted if wanted[name] != here[name]]


def _track_m_script():
    path = ROOT / "scripts" / "run_track_m_registered.py"
    spec = importlib.util.spec_from_file_location("_g4c_track_m", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_registered_computation_reproduces_exactly():
    if not PSID_DIR.is_dir():
        pytest.skip("staged PSID files absent")
    parent = mb.load_parent_artifact()
    differ = _environment_matches(dict(parent.sidecar))
    if differ:
        pytest.skip(
            f"environment differs from the parent run's in {differ} "
            "(scripts/make_nasi_repro_venv.sh builds it)"
        )
    from populace_dynamics.estimates.parameters import load_cola_history
    from populace_dynamics.min_benefit_track_m import cohort
    from populace_dynamics.min_benefit_track_m.evaluation import PSID_FILES
    from populace_dynamics.min_benefit_track_m.specification import (
        m1_parameter_block,
    )
    from populace_dynamics.min_benefit_track_m.tabulation import (
        REGISTERED_REAL,
    )

    track_m = _track_m_script()
    try:
        parameters, pins = track_m.committed_parameters(m1_parameter_block())
    except FileNotFoundError:
        pytest.skip("the oracle's policyengine-us checkout is absent")
    revision = parent.sidecar["environment"]["policyengine_us_parameters"][
        "revision"
    ]
    if parameters.params.pe_us_revision != revision:
        pytest.skip(
            f"policyengine-us is at {parameters.params.pe_us_revision}, not "
            f"the parent's {revision}"
        )
    assert pins == parent.document["checks"]["parameter_pins"]
    cola = load_cola_history()
    _, checks = mb.reproduce_parent(
        parameters=parameters,
        parent=parent,
        data_provenance=REGISTERED_REAL,
        load_cohort_inputs=cohort.load_cohort_inputs,
        cola_rates=cola,
        provenance_kind=PSID_FILES,
        source={"cola_history": dict(cola.provenance)},
    )
    assert all(check.identical for check in checks)
    names = {check.name for check in checks}
    assert {"pipeline.rows", "pipeline.cohort_structure"} <= names
    common.require_identical(checks, stage="host reproduction")
