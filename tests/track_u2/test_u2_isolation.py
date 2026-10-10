"""U2 historical isolation and protected sources (section 13, group
"Historical isolation"; section 14).

* The protected files -- ``data/family.py``, ``data/psid.py``,
  ``estimates/career.py``, the engine loop and steps, ``gates.yaml``,
  U1's specification, parameter captures, registered artifact and
  environment sidecar, and U1's code and tests -- keep the bytes the
  milestone-1 manifest (``data/external/track_u2/u1_identity.json``)
  records, and no U2 commit or merge resolution (attributed by path; see
  ``test_no_committed_run_engine_gate_or_u1_file_changed``) changed a
  committed ``runs/*.json`` or any other protected path.
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
from populace_dynamics.uniform_cut_track_u2 import identity
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
#: Paths only U2 work writes.  A commit that touches one of these is a U2
#: commit; the isolation check below holds every such commit to the
#: protected paths.  Other tracks' commits reach this branch through merges
#: of master and are not U2's to police here.
U2_OWNED = (
    "src/populace_dynamics/uniform_cut_track_u2",
    "src/populace_dynamics/data/u2_source_registry.py",
    "data/external/track_u2",
    "data/external/track_u2_ssi_parameters_2012_2022.json",
    "tests/data/track_u2",
    "tests/data/test_track_u2_*",
    "tests/track_u2",
    "scripts/*track_u2*",
    "scripts/u2_*",
    "docs/design/u2_*",
    "docs/design/boomers2004_1946_55_comparison.md",
)
#: U2's own registered artifact and sidecar may be added once, by the
#: authorized registered run, and never modified afterwards.
U2_ARTIFACTS = tuple(
    path.relative_to(identity.ROOT).as_posix()
    for path in (identity.ARTIFACT_PATH, identity.SIDECAR_PATH)
)
PROTECTED = (
    "src/populace_dynamics/data/family.py",
    "src/populace_dynamics/data/psid.py",
    "src/populace_dynamics/estimates/career.py",
    "src/populace_dynamics/engine/loop.py",
    "src/populace_dynamics/engine/steps.py",
    "gates.yaml",
)

#: Paths no U2 commit or merge resolution may change.
PROTECTED_PATHSPECS = (
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
    *(f":(exclude){path}" for path in U2_ARTIFACTS),
)


#: The ratified contract: ``gates.yaml`` moves only at a ratified flip,
#: which records the new bytes here through
#: ``scripts/build_legacy_manifest.py --transition``.
LEGACY_MANIFEST = ROOT / "runs" / "legacy_manifest_v1.json"


def _ratified_gates_sha256() -> str:
    entries = json.loads(LEGACY_MANIFEST.read_text())["entries"]
    (entry,) = [e for e in entries if e["path"] == "gates.yaml"]
    return entry["sha256"]


def test_protected_bytes_match_the_milestone_1_manifest():
    manifest = json.loads(MANIFEST.read_text())["sha256"]
    for path in PROTECTED:
        assert path in manifest, path
    for path, digest in manifest.items():
        observed = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        if path == "gates.yaml" and observed != digest:
            # A ratified flip outside U2 (first: gate_epuf_fill, decision
            # d927) may move the contract; it must then be the ratified
            # one. No U2 commit may move it (the path-attribution test).
            assert observed == _ratified_gates_sha256(), path
            continue
        assert observed == digest, path


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True
    )


def _u2_commits() -> list[str]:
    """Non-merge commits since ``BASE`` that touch a U2-owned path."""
    log = _git(
        "log",
        "--no-merges",
        "--full-history",
        "--format=%H",
        f"{BASE}..HEAD",
        "--",
        *U2_OWNED,
    )
    assert log.returncode == 0, log.stderr
    return log.stdout.split()


def test_no_committed_run_engine_gate_or_u1_file_changed():
    """No U2 commit touches a committed run, the engine, a gate or U1.

    The check is per commit, not a tree diff against ``BASE``: master keeps
    moving (new runs, gates and other tracks' test data land there), and a
    tree diff would charge those to U2 once this branch merges master or
    lands on it. A merge counts as U2's when its merged bytes
    (``--cc --name-only``: paths that differ from every parent, including
    conflict resolutions and hand edits) touch a U2-owned path, and it is
    then held to the protected paths the same way.

    Attribution is by path: a commit or merge that touches no U2-owned
    path (for example one that changes only shared files such as the
    reducer or the tier counts, plus protected paths) is not recognised as
    U2's and is not caught here. ``gates.yaml``, the engine loop and
    steps, family/psid/career and U1's files and artifact stay byte-pinned
    by ``test_protected_bytes_match_the_milestone_1_manifest``; other runs
    and engine modules rely on review. U2's own artifact and sidecar may
    be added once and never modified, by any commit or merge.
    """
    if _git("cat-file", "-e", f"{BASE}^{{commit}}").returncode != 0:
        pytest.skip("the U1 base commit is not in this clone's history")
    commits = _u2_commits()
    assert commits, "no U2 commit found since the U1 base"
    offending = {}
    for commit in commits:
        changed = _git(
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            commit,
            "--",
            *PROTECTED_PATHSPECS,
        )
        assert changed.returncode == 0, changed.stderr
        if changed.stdout.split():
            offending[commit] = changed.stdout.split()
    merges = _git("log", "--merges", "--format=%H", f"{BASE}..HEAD")
    assert merges.returncode == 0, merges.stderr
    for merge in merges.stdout.split():
        own_u2 = _git(
            "diff-tree",
            "--cc",
            "--no-commit-id",
            "--name-only",
            "-r",
            merge,
            "--",
            *U2_OWNED,
        )
        assert own_u2.returncode == 0, own_u2.stderr
        if not own_u2.stdout.split():
            continue
        own = _git(
            "diff-tree",
            "--cc",
            "--no-commit-id",
            "--name-only",
            "-r",
            merge,
            "--",
            *PROTECTED_PATHSPECS,
        )
        assert own.returncode == 0, own.stderr
        if own.stdout.split():
            offending[merge] = own.stdout.split()
    rewritten = _git(
        "log",
        "-m",
        "--full-history",
        "--diff-filter=MDRT",
        "--format=%H",
        f"{BASE}..HEAD",
        "--",
        *U2_ARTIFACTS,
    )
    assert rewritten.returncode == 0, rewritten.stderr
    for commit in rewritten.stdout.split():
        offending[commit] = list(U2_ARTIFACTS)
    assert offending == {}


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
    assert all((ROOT / path).is_file() for path in exclusions), sorted(
        path for path in exclusions if not (ROOT / path).is_file()
    )


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
