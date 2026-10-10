"""The committed block passes every gate before the PSID read (M11).

Since the registered-commit edit of 2026-09-27 the M1 specification's
section 19 block lists no blocker, so at the registered commit on a clean
tree the one-shot entry point (``scripts/run_track_m_registered.py``)
passes its preflight, its component check and its parameter pins on the
committed block, resolves its environment and reaches the PSID read.  A
fake ``git`` stands in for the registered commit; the PSID loader is
replaced, so no PSID file is read, nothing is computed and nothing is
written.  The parameters are the oracle's from the policyengine-us
checkout (``POPULACE_DYNAMICS_PE_US_DIR`` or
``~/PolicyEngine/policyengine-us``), the committed quarter-of-coverage
capture and the committed Census capture; the test skips without the
checkout.  This mirrors Track U's "the ratified block passes every gate
before the PSID read" (``tests/track_u/test_registered_script.py``).
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

from populace_dynamics.min_benefit_track_m import specification as spec

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
POINTER = (
    "https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
    "#issuecomment-1"
)
COMMIT = "a" * 40


class _PsidReached(Exception):
    """Raised by the stand-in PSID loader: every earlier gate passed."""


def _script():
    path = ROOT / "scripts" / "run_track_m_registered.py"
    module_spec = importlib.util.spec_from_file_location(
        "_track_m_registered_commit", path
    )
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def _git(head: str = COMMIT, porcelain: str = ""):
    def fake(*args: str) -> str:
        if args == ("rev-parse", "HEAD"):
            return head
        if args == ("status", "--porcelain"):
            return porcelain
        raise AssertionError(args)

    return fake


def _main(script, output: Path) -> int:
    return script.main(
        [
            "--registration-pointer",
            POINTER,
            "--registered-commit",
            COMMIT,
            "--output",
            str(output),
        ]
    )


def test_the_committed_block_passes_each_check_before_the_psid_read(
    tmp_path,
):
    """Each check the entry point makes before the PSID read, called
    directly on the committed block: the preflight (a fake ``git`` at the
    registered commit on a clean tree), the component check, and the
    parameter pins, which hold the loaded files to the block's
    ``sources``."""

    script = _script()
    block = spec.m1_parameter_block()
    assert block["blocked_by"] == []
    assert script.preflight(
        registration_pointer=POINTER,
        registered_commit=COMMIT,
        output=tmp_path / "run.json",
        git=_git(),
    ) == {"head": COMMIT}
    assert script.missing_components() == []
    script.check_runnable()
    parameters, pins = script.committed_parameters(block)
    assert pins == {
        "quarter_of_coverage": (
            block["sources"]["quarter_of_coverage_amounts"]["sha256"]
        ),
        "census_thresholds": block["sources"]["census_thresholds"]["sha256"],
    }
    assert parameters.thresholds.source["sha256"] == pins["census_thresholds"]
    assert parameters.params.pe_us_revision
    assert list(tmp_path.iterdir()) == []


def test_the_committed_block_passes_every_gate_before_the_psid_read(
    tmp_path, monkeypatch
):
    """``main`` on the committed block, with a fake ``git`` at the
    registered commit on a clean tree: the real preflight, component
    check, parameter pins and environment run, in that order, and the run
    reaches the PSID loader, which is replaced so that no PSID file is
    read.  Nothing is computed and nothing is written."""

    from populace_dynamics.min_benefit_track_m import cohort, pipeline

    # Fail closed: were the stand-in loader bypassed, the PSID directory
    # would not exist, so no staged PSID file could be read.
    monkeypatch.setenv("POPULACE_DYNAMICS_PSID_DIR", str(tmp_path / "none"))
    script = _script()
    calls = []

    def recorded(name, function):
        def wrapper(*args, **kwargs):
            calls.append(name)
            return function(*args, **kwargs)

        return wrapper

    preflight = script.preflight
    monkeypatch.setattr(
        script,
        "preflight",
        recorded("preflight", lambda **kw: preflight(git=_git(), **kw)),
    )
    for name in ("check_runnable", "committed_parameters", "_environment"):
        monkeypatch.setattr(
            script, name, recorded(name, getattr(script, name))
        )

    def psid_reached(**_):
        calls.append("psid_read")
        raise _PsidReached

    def never(*args, **kwargs):
        raise AssertionError("computed before the PSID read")

    monkeypatch.setattr(cohort, "load_cohort_inputs", psid_reached)
    monkeypatch.setattr(pipeline, "run_track_m", never)
    output = tmp_path / "run.json"
    with pytest.raises(_PsidReached):
        _main(script, output)
    assert calls == [
        "preflight",
        "check_runnable",
        "committed_parameters",
        "_environment",
        "psid_read",
    ]
    assert not output.exists()
    assert not output.with_suffix(".env.json").exists()


@pytest.mark.parametrize(
    ("git", "match"),
    [
        (_git(head="b" * 40), "is not the registered commit"),
        (_git(porcelain=" M src/x.py"), "clean"),
    ],
    ids=["another-head", "dirty-tree"],
)
def test_the_same_run_stops_at_the_preflight_outside_the_registered_state(
    tmp_path, monkeypatch, git, match
):
    """The same ``main`` with ``HEAD`` elsewhere or a dirty tree stops at
    the preflight, before the parameters or any PSID file are read."""

    from populace_dynamics.min_benefit_track_m import cohort

    monkeypatch.setenv("POPULACE_DYNAMICS_PSID_DIR", str(tmp_path / "none"))
    script = _script()
    preflight = script.preflight
    monkeypatch.setattr(
        script, "preflight", lambda **kw: preflight(git=git, **kw)
    )

    def not_reached(*_, **__):
        raise AssertionError("read before the preflight refused")

    monkeypatch.setattr(script, "committed_parameters", not_reached)
    monkeypatch.setattr(cohort, "load_cohort_inputs", not_reached)
    output = tmp_path / "run.json"
    with pytest.raises(ValueError, match=match):
        _main(script, output)
    assert not output.exists()
