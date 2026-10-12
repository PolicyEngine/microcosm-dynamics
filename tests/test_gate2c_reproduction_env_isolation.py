"""Collecting the gate-2c reproduction pins must not redirect the oracle.

Both candidate pins once ran ``os.environ.setdefault`` on the
policyengine-us checkout variable at import.  Collection imports every
module before any test runs, so a full-suite (or ``-k``) session pointed
every later oracle load at their ``policyengine-us-main`` checkout, and
oracle tests that pass alone failed there.  The pins, and the floors module
(whose reproduction pin ran in such sessions only because of that leak,
unless the variable was exported), now read their checkout without writing
the environment and export it only while their own tests run.

Every check runs in a fresh interpreter: this session imported the modules
during collection already, and an in-process import that leaked would
repeat the bug for every later test.  The variable is named through the
oracle loader, so this module needs no checkout and no data.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from populace_dynamics.ss import params as ss_params

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
MODULES = (
    "test_gate2c_candidate1_reproduction.py",
    "test_gate2c_candidate2_reproduction.py",
    "test_gate2c_floors.py",
)
PE_US_ENV = ss_params._PE_US_ENV
#: The checkout the gate-2c floor and both one-shots were built against.
FROZEN_DEFAULT = Path.home() / "PolicyEngine" / "policyengine-us-main"

_IMPORT_PROBE = """
import importlib.util, json, os, sys
name, path, variable = sys.argv[1:]
before = os.environ.get(variable)
spec = importlib.util.spec_from_file_location(name, path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
print(json.dumps({
    "before": before,
    "after": os.environ.get(variable),
    "variable": getattr(module, "PE_US_ENV", None),
    "pe_us_dir": str(module.PE_US_DIR),
}))
"""

# Imports a module's ``_pe_us_dir_env`` fixture into a synthetic test module
# (an imported autouse fixture applies there), so its scope and restoration
# are exercised without the PSID data the real tests need.  The
# module-scoped fixture stands in for ``sources``, which loads the oracle.
_FIXTURE_PROBE = """
import importlib.util
import os

import pytest

_spec = importlib.util.spec_from_file_location({name!r}, {path!r})
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
_pe_us_dir_env = _module._pe_us_dir_env


@pytest.fixture(scope="module")
def seen_by_a_module_fixture():
    return os.environ.get({variable!r})


def test_a_module_scoped_fixture_sees_the_checkout(seen_by_a_module_fixture):
    assert seen_by_a_module_fixture == {expected!r}


def test_a_test_sees_the_checkout():
    assert os.environ.get({variable!r}) == {expected!r}
"""

_AFTER_PROBE = """
import os


def test_the_next_module_does_not_see_it():
    assert {variable!r} not in os.environ
"""

# Loaded with ``-p`` (before any conftest), it traces every write to
# ``os.environ`` while pytest starts and collects, attributes it to the first
# caller outside the mapping and patching helpers, and reports the writes
# made by the repository's own code.  Dependencies may set variables at
# import (scikit-learn sets two ``KMP_*`` ones); those are not the suite's
# to police.
_ENV_GUARD_PLUGIN = """
import json
import os
import sys

_ROOT = os.path.realpath(os.environ["ENV_GUARD_ROOT"])
_REPORT = os.environ["ENV_GUARD_REPORT"]
_REPO_CODE = tuple(
    os.path.join(_ROOT, part) + os.sep for part in ("src", "scripts", "tests")
)
_OS_MODULE = os.path.realpath(os.__file__)
_PATCHERS = (
    os.path.join("_pytest", "monkeypatch.py"),
    os.path.join("unittest", "mock.py"),
)
_writes = []


def _is_helper(filename):
    # release builds freeze os and _collections_abc ("<frozen os>").
    return (
        filename.startswith("<frozen ")
        or "_collections_abc" in filename
        or filename.endswith(_PATCHERS)
        or os.path.realpath(filename) == _OS_MODULE
    )


def _record(key):
    frame = sys._getframe(2)
    while frame is not None and _is_helper(frame.f_code.co_filename):
        frame = frame.f_back
    if frame is None:
        return
    path = os.path.realpath(frame.f_code.co_filename)
    if path.startswith(_REPO_CODE):
        where = os.path.relpath(path, _ROOT)
        _writes.append(f"{where}:{frame.f_lineno} {key}")


_Environ = type(os.environ)
_setitem = _Environ.__setitem__
_delitem = _Environ.__delitem__


def _traced_setitem(self, key, value):
    if self is os.environ:
        _record(key)
    _setitem(self, key, value)


def _traced_delitem(self, key):
    if self is os.environ:
        _record(key)
    _delitem(self, key)


_Environ.__setitem__ = _traced_setitem
_Environ.__delitem__ = _traced_delitem


def pytest_collection_finish(session):
    with open(_REPORT, "w", encoding="utf-8") as handle:
        json.dump(_writes, handle)
"""


def _without_variable() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k != PE_US_ENV}


def _run(args: list[str], cwd: Path, env: dict[str, str]):
    return subprocess.run(
        [sys.executable, *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _import_in_fresh_interpreter(module: str, env: dict[str, str]) -> dict:
    path = TESTS / module
    result = _run(
        ["-c", _IMPORT_PROBE, path.stem, str(path), PE_US_ENV], ROOT, env
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.splitlines()[-1])


@pytest.mark.parametrize("module", MODULES)
def test_importing_leaves_the_unset_variable_unset(module):
    seen = _import_in_fresh_interpreter(module, _without_variable())
    assert seen["before"] is None
    assert seen["after"] is None
    # the module still names the variable the oracle loaders read and still
    # defaults to the checkout its frozen artifacts were built against.
    assert seen["variable"] == PE_US_ENV
    assert Path(seen["pe_us_dir"]) == FROZEN_DEFAULT


@pytest.mark.parametrize("module", MODULES)
def test_importing_keeps_and_honours_an_override(module, tmp_path):
    override = str(tmp_path / "pe-us-override")
    seen = _import_in_fresh_interpreter(
        module, {**_without_variable(), PE_US_ENV: override}
    )
    assert seen["before"] == override
    assert seen["after"] == override
    assert seen["pe_us_dir"] == override


@pytest.mark.parametrize("module", MODULES)
def test_the_checkout_is_exported_only_while_the_module_runs(module, tmp_path):
    path = TESTS / module
    (tmp_path / "pytest.ini").write_text("[pytest]\n")
    (tmp_path / "test_a_module.py").write_text(
        _FIXTURE_PROBE.format(
            name=path.stem,
            path=str(path),
            variable=PE_US_ENV,
            expected=str(FROZEN_DEFAULT),
        )
    )
    (tmp_path / "test_b_after.py").write_text(
        _AFTER_PROBE.format(variable=PE_US_ENV)
    )
    result = _run(
        ["-m", "pytest", "-q", "-p", "no:cacheprovider", str(tmp_path)],
        tmp_path,
        _without_variable(),
    )
    assert result.returncode == 0, result.stdout[-3000:]
    assert "3 passed" in result.stdout


def test_collecting_the_suite_writes_no_environment_variable(tmp_path):
    """No repository code may write ``os.environ`` during collection."""
    (tmp_path / "env_guard_plugin.py").write_text(_ENV_GUARD_PLUGIN)
    report = tmp_path / "report.json"
    env = _without_variable()
    env["ENV_GUARD_ROOT"] = str(ROOT)
    env["ENV_GUARD_REPORT"] = str(report)
    env["PYTHONPATH"] = os.pathsep.join(
        p for p in (str(tmp_path), env.get("PYTHONPATH")) if p
    )
    result = _run(
        [
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "-p",
            "no:cacheprovider",
            "-p",
            "env_guard_plugin",
        ],
        ROOT,
        env,
    )
    assert report.is_file(), result.stdout[-2000:] + result.stderr[-2000:]
    assert json.loads(report.read_text()) == []
