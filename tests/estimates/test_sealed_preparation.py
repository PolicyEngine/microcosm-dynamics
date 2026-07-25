"""Sealed-process regression for first-estimates preparation and compute."""

from __future__ import annotations

import os
import shutil
import site
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from populace_dynamics.estimates import coordinator, publication

_REPOSITORY = Path(__file__).resolve().parents[2]
_FACTORY_PATH = Path("scripts/registered_m6_candidate2_inputs.py")
_FAST_LAZY_FACTORY = """\
from populace_dynamics.harness.m6_candidate2_runner import M6Candidate2InputPlan


def build_input_plan():
    import build_mortality_floors

    return M6Candidate2InputPlan(
        fit_inputs=build_mortality_floors.BANDS,
        load_full_inputs=lambda: None,
    )
"""
_PREPARATION_PROBE = """\
import json
import sys
from dataclasses import replace
from pathlib import Path
from types import ModuleType, SimpleNamespace

root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root / "src"))

from populace_dynamics.estimates import coordinator

expected_coordinator = (
    root / "src/populace_dynamics/estimates/coordinator.py"
).resolve()
if Path(coordinator.__file__).resolve() != expected_coordinator:
    raise AssertionError("coordinator did not load from the fixture worktree")

committed_path = root / (
    "docs/registrations/"
    "first_estimates_registration_3_configuration.json"
)
committed = json.loads(committed_path.read_bytes())
from populace_dynamics.estimates import publication, runner

sealed_reference = "populace-dynamics#0-sealed-preparation-test"
configuration = runner.registered_configuration_echo(
    registration_reference=sealed_reference,
    parameter_bundle=committed["parameters"],
)
configuration_path = root / (
    "docs/registrations/first_estimates_sealed_test_configuration.json"
)
configuration_path.write_bytes(
    publication.canonical_json_bytes(configuration)
)
import subprocess as _sp

_sp.run(
    ["git", "-C", str(root), "add", str(configuration_path)],
    check=True,
    capture_output=True,
)
_sp.run(
    [
        "git",
        "-C",
        str(root),
        "-c",
        "user.email=test@example.com",
        "-c",
        "user.name=Sealed Test",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-q",
        "--no-verify",
        "-m",
        "sealed-test configuration",
    ],
    check=True,
    capture_output=True,
)


def load_registered_parameters():
    return SimpleNamespace(
        provenance=configuration["parameters"],
        runtime_provenance={
            "schema_version": "first_estimates.runtime_provenance.v1",
            "parameters": {},
        },
    )


original_path = sys.path.copy()
poisoned = ModuleType("build_m4_gate_floors")
sys.modules["build_m4_gate_floors"] = poisoned
observed = {}


def execute_projection(*_args, **_kwargs):
    import build_m4_gate_floors

    expected = (root / "scripts/build_m4_gate_floors.py").resolve()
    if Path(build_m4_gate_floors.__file__).resolve() != expected:
        raise AssertionError("compute imported an unregistered scripts module")
    observed["compute_module"] = build_m4_gate_floors
    return "stubbed-projection-batch"


def prepare_batch(batch, *, parameters):
    if batch != "stubbed-projection-batch":
        raise AssertionError("stubbed projection batch changed")
    if parameters.provenance != configuration["parameters"]:
        raise AssertionError("prepared parameters changed")
    return "stubbed-prepared-batch"


def build_artifact(prepared, **_kwargs):
    import build_m4_gate_floors

    if prepared != "stubbed-prepared-batch":
        raise AssertionError("stubbed prepared batch changed")
    if sys.path[0] != str(root / "scripts"):
        raise AssertionError("scripts scope ended before artifact build")
    if build_m4_gate_floors is not observed["compute_module"]:
        raise AssertionError("compute scripts module was not held through build")
    return {"sealed_compute_surface": True}


def publish_artifact(_token, artifact):
    if artifact != {"sealed_compute_surface": True}:
        raise AssertionError("stubbed artifact changed")
    return root / "runs/first_estimates_v1.json"


operations = replace(
    coordinator._default_operations(),
    load_parameters=load_registered_parameters,
    execute_projection=execute_projection,
    prepare_batch=prepare_batch,
    build_artifact=build_artifact,
    publish_artifact=publish_artifact,
)
result = coordinator._run_registered_first_estimates_from_path_for_test(
    repository_root=root,
    registration_reference=sealed_reference,
    registered_configuration_path=configuration_path,
    retry_after_incident=None,
    operations=operations,
)
if result.status != "published":
    raise AssertionError(f"stubbed compute did not complete: {result!r}")
if sys.modules["build_m4_gate_floors"] is not poisoned:
    raise AssertionError("preexisting scripts module was not restored")
if sys.path != original_path:
    raise AssertionError("interpreter path was not restored")
print("COMPUTE_SURFACE_COMPLETE")
"""


def _git_failure(error: subprocess.CalledProcessError) -> str:
    detail = (error.stderr or error.stdout or str(error)).strip()
    return detail.splitlines()[-1] if detail else str(error)


@pytest.fixture
def _sealed_preparation_worktree(tmp_path: Path) -> Iterator[Path]:
    git = shutil.which("git")
    if git is None:
        pytest.skip("git is unavailable for the sealed worktree fixture")
    worktree = tmp_path / "repository"
    added = False
    try:
        try:
            subprocess.run(
                [
                    git,
                    "-C",
                    str(_REPOSITORY),
                    "worktree",
                    "add",
                    "--detach",
                    str(worktree),
                    "HEAD",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            added = True
            (worktree / _FACTORY_PATH).write_text(
                _FAST_LAZY_FACTORY,
                encoding="utf-8",
            )
            subprocess.run(
                [git, "-C", str(worktree), "add", "--", str(_FACTORY_PATH)],
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                [
                    git,
                    "-C",
                    str(worktree),
                    "-c",
                    "user.name=First Estimates Test",
                    "-c",
                    "user.email=first-estimates@example.invalid",
                    "-c",
                    "commit.gpgsign=false",
                    "commit",
                    "--no-verify",
                    "-qm",
                    "sealed preparation fixture",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError) as error:
            if isinstance(error, subprocess.CalledProcessError):
                detail = _git_failure(error)
            else:
                detail = str(error)
            pytest.skip(f"git worktree fixture is unavailable: {detail}")
        yield worktree
    finally:
        if added:
            subprocess.run(
                [
                    git,
                    "-C",
                    str(_REPOSITORY),
                    "worktree",
                    "remove",
                    "--force",
                    str(worktree),
                ],
                capture_output=True,
                text=True,
            )


def _sealed_venv_python(tmp_path: Path) -> Path:
    environment = tmp_path / "venv"
    try:
        created = subprocess.run(
            [
                sys.executable,
                "-m",
                "venv",
                "--without-pip",
                str(environment),
            ],
            capture_output=True,
            text=True,
        )
    except OSError as error:
        pytest.skip(f"venv is unavailable for the sealed subprocess: {error}")
    if created.returncode != 0:
        detail = (created.stderr or created.stdout).strip()
        pytest.skip(f"venv is unavailable for the sealed subprocess: {detail}")
    executable = environment / (
        "Scripts/python.exe" if os.name == "nt" else "bin/python"
    )
    if not executable.is_file():
        pytest.skip("venv did not create a Python executable")
    located = subprocess.run(
        [
            str(executable),
            "-I",
            "-c",
            "import site; print(site.getsitepackages()[0])",
        ],
        capture_output=True,
        text=True,
    )
    if located.returncode != 0:
        pytest.skip(
            "venv site-packages are unavailable for the sealed subprocess"
        )
    dependency_paths = sorted(
        {
            str(Path(value).resolve())
            for value in site.getsitepackages()
            if Path(value).is_dir()
        }
    )
    if not dependency_paths:
        pytest.skip("pytest environment has no dependency site-packages")
    target = Path(located.stdout.strip())
    (target / "sealed-preparation-dependencies.pth").write_text(
        "".join(f"{value}\n" for value in dependency_paths),
        encoding="utf-8",
    )
    dependencies = subprocess.run(
        [
            str(executable),
            "-I",
            "-c",
            "import numpy, pandas, scipy, sklearn, yaml",
        ],
        capture_output=True,
        text=True,
    )
    if dependencies.returncode != 0:
        pytest.skip(
            "temporary venv cannot import the installed project dependencies"
        )
    return executable


def test__sealed_interpreter__prepares_and_smokes_compute_import_surface(
    tmp_path: Path,
    _sealed_preparation_worktree: Path,
):
    worktree = _sealed_preparation_worktree
    executable = _sealed_venv_python(tmp_path)
    pycache = tmp_path / "pycache"
    pycache.mkdir()
    environment = os.environ.copy()
    environment[coordinator._PYCACHE_SENTINEL_ENV] = str(pycache)

    completed = subprocess.run(
        [
            str(executable),
            "-I",
            "-B",
            "-X",
            f"pycache_prefix={pycache}",
            "-c",
            _PREPARATION_PROBE,
            str(worktree),
        ],
        cwd=worktree,
        capture_output=True,
        text=True,
        env=environment,
        timeout=60,
    )

    assert (
        completed.returncode == 0
    ), f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    assert completed.stdout == "COMPUTE_SURFACE_COMPLETE\n"
    assert completed.stderr == ""
    committed_incidents = sorted(
        line
        for line in subprocess.run(
            ["git", "-C", str(worktree), "ls-files", "runs/"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        if line.startswith("runs/first_estimates_incident_")
    )
    assert (
        sorted(
            f"runs/{path.name}"
            for path in (worktree / "runs").glob(
                "first_estimates_incident_*.json"
            )
        )
        == committed_incidents
    )
    artifact = worktree / publication.DEFAULT_ARTIFACT_PATH
    assert not artifact.exists()
    assert not Path(f"{artifact}.env.json").exists()
    assert not any(pycache.iterdir())
    status = subprocess.run(
        [
            shutil.which("git") or "git",
            "-C",
            str(worktree),
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ],
        check=True,
        capture_output=True,
    )
    assert status.stdout == b""
