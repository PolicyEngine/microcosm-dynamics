"""U2 historical isolation and protected sources (section 13, group
"Historical isolation"; section 14).

* The protected files -- ``data/family.py``, ``data/psid.py``,
  ``estimates/career.py``, the engine loop and steps, ``gates.yaml``,
  U1's specification, parameter captures, registered artifact and
  environment sidecar, and U1's code and tests -- keep the bytes the
  milestone-1 manifest (``data/external/track_u2/u1_identity.json``)
  records, and no committed ``runs/*.json`` changed.
* Every U2 milestone-2 module is an exact file exclusion in
  ``POST_REVIEW_SOURCE_EXCLUSIONS`` (the exact-tuple and transitive
  reachability tests live in ``tests/estimates/
  test_birth_evidence_artifact.py``); here the package's own files are
  held to that list, so a new U2 module cannot be added without it.
* U1's wave pin ``(2005, 2007, 2009, 2011, 2013)`` and every shared U1
  constant U2 could have extended stay unchanged.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from populace_dynamics.cohorts import age67
from populace_dynamics.data import employer_dc, family_income
from populace_dynamics.estimates import adjusted_poverty as ap
from scripts import first_estimates_birth_evidence as reducer

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data" / "external" / "track_u2" / "u1_identity.json"
#: The repository reference of the U2 specification (header): U1's
#: registered state.  Milestone 1 and every later U2 lane change only U2
#: paths (``track_u2`` registries, captures and documentary sources), so
#: the U1 paths below must be byte-identical to this commit.
BASE = "9cee2423f048"
#: U2's own milestone-1 data: allowed to differ from ``BASE``.
U2_PATHS = (
    ":(exclude)data/external/track_u2",
    ":(exclude)data/external/track_u2_ssi_parameters_2012_2022.json",
    ":(exclude)tests/data/track_u2",
    ":(exclude)tests/data/test_track_u2_*",
)
PROTECTED = (
    "src/populace_dynamics/data/family.py",
    "src/populace_dynamics/data/psid.py",
    "src/populace_dynamics/estimates/career.py",
    "src/populace_dynamics/engine/loop.py",
    "src/populace_dynamics/engine/steps.py",
    "gates.yaml",
)


def test_protected_bytes_match_the_milestone_1_manifest():
    manifest = json.loads(MANIFEST.read_text())["sha256"]
    for path in PROTECTED:
        assert path in manifest, path
    for path, digest in manifest.items():
        observed = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        assert observed == digest, path


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True
    )


def test_no_committed_run_engine_gate_or_u1_file_changed():
    if _git("cat-file", "-e", f"{BASE}^{{commit}}").returncode != 0:
        pytest.skip("the U1 base commit is not in this clone's history")
    changed = _git(
        "diff",
        "--name-only",
        BASE,
        "--",
        "runs",
        "gates.yaml",
        "src/populace_dynamics/engine",
        "src/populace_dynamics/data/family.py",
        "src/populace_dynamics/data/psid.py",
        "src/populace_dynamics/estimates/career.py",
        "src/populace_dynamics/cohorts/age67.py",
        "src/populace_dynamics/estimates/adjusted_poverty.py",
        "src/populace_dynamics/estimates/uniform_cut_tabulation.py",
        "src/populace_dynamics/uniform_cut_track_u",
        "data/external",
        "tests/track_u",
        "tests/cohorts",
        "tests/data",
        "tests/test_boomers2004_uniform_cut_spec.py",
        "tests/test_replication_boomers2004_uniform_cut.py",
        *U2_PATHS,
    )
    assert changed.returncode == 0, changed.stderr
    assert changed.stdout.split() == []


def test_every_u2_module_is_an_exact_historical_exclusion():
    package = ROOT / "src" / "populace_dynamics" / "uniform_cut_track_u2"
    modules = {path.relative_to(ROOT) for path in sorted(package.glob("*.py"))}
    exclusions = set(reducer.POST_REVIEW_SOURCE_EXCLUSIONS)
    assert modules <= exclusions, sorted(modules - exclusions)
    for script in (
        "track_u2_dry_run",
        "track_u2_structure",
        "track_u2_component_diagnostics",
        "run_track_u2_registered",
        "u2_u1_differential",
    ):
        assert Path(f"scripts/{script}.py") in exclusions
    # Exact files, never directories.
    assert all(path.suffix == ".py" for path in exclusions)


def test_u1_wave_pins_and_shared_constants_are_unchanged():
    assert age67.WAVES == (2005, 2007, 2009, 2011, 2013)
    assert family_income.INCOME_WAVES == (2005, 2007, 2009, 2011, 2013)
    assert employer_dc.EMPLOYER_DC_WAVES == (2005, 2007, 2009, 2011, 2013)
    assert ap._HEAD_IRA_INCOME_YEARS == frozenset({2012})
    assert (
        ap.THRESHOLDS_PATH.name == "census_poverty_thresholds_2004_2012.json"
    )
    assert ap.SSI_PARAMETERS_PATH.name == "track_u_ssi_parameters.json"
    assert age67.Age67Spec().as_dict() == {
        "row": "U0",
        "presence": "in_family",
        "separated_is_married": True,
        "u1_single_observation_weight": 1.0,
        "seed_wave_rule": "earliest_presence_wave",
        "unresolved_marital_status": "relationship_code",
        "annuitant_age_source": "derived_birth_year",
        "institution_income_rule": "excluded",
    }
