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

import pandas as pd

root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root / "src"))

from populace_dynamics import claiming
from populace_dynamics.engine.loop import ProjectionResult
from populace_dynamics.estimates import coordinator, preparation

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
from populace_dynamics.estimates.parameters import (
    COLASeries,
    PayrollRateLegs,
    ReportParameters,
)
from populace_dynamics.estimates.runner import (
    DRAW_INDICES,
    DRAW_ROOT_SEEDS,
    FirstReportProjectionBatch,
    FirstReportProjectionDraw,
)
from populace_dynamics.ss.params import SSAParameters

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
    return ReportParameters(
        ssa=SSAParameters(
            nawi={year: 100.0 for year in range(1968, 2023)},
            wage_base={1900: 1_000_000.0},
            pia_factors=(0.9, 0.32, 0.15),
            fra_months_by_birth_year=[(1900, 66 * 12)],
            early_monthly_rates=(5 / 900, 5 / 1200),
            early_first_bracket_months=36,
            pe_us_revision="sealed-preparation-fixture",
            delayed_credit_by_birth_year=[(1900, 0.08)],
        ),
        rates=PayrollRateLegs(
            employee_by_effective_year={1900: 0.062},
            employer_by_effective_year={1900: 0.062},
            provenance={},
        ),
        cola=COLASeries(
            by_determination_year={
                year: 0.0 for year in range(1979, 2023)
            },
            provenance={},
        ),
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


class PhaseWithForbiddenBundle:
    def __init__(self, population):
        self.population = population

    @property
    def bundle(self):
        raise AssertionError("real preparation consulted phase.bundle")


def tiny_projection(draw_index):
    slices = []
    for year in range(2014, 2023):
        rows = []
        for person_id, birth_year, sex, weight in (
            (1, 1954, "female", 1.5),
            (2, 1954, "male", 1.2),
            (3, 2013, "female", 1.0),
        ):
            projected = year > 2014
            rows.append(
                {
                    "person_id": person_id,
                    "year": year,
                    "age": year - birth_year,
                    "sex": sex,
                    "weight": weight,
                    "earnings": 9_000.0 if person_id < 3 else 0.0,
                    "claim_age": (
                        (62 if person_id < 3 else 1)
                        if projected
                        else pd.NA
                    ),
                    "claim_year": 2016 if projected else pd.NA,
                    "di_converted": False if projected else pd.NA,
                }
            )
        slices.append(pd.DataFrame(rows))
    return ProjectionResult(
        slices=tuple(slices),
        traces=(),
        draw_index=draw_index,
    )


def tiny_batch():
    initial = pd.DataFrame(
        {
            "person_id": [1, 2, 3],
            "year": [2014, 2014, 2014],
            "anchor_wave": [2015, 2015, 2015],
            "age": [60, 60, 1],
            "sex": ["female", "male", "female"],
            "weight": [1.5, 1.2, 1.0],
        }
    )
    population = SimpleNamespace(
        initial_slice=initial,
        scheduled_entries_by_year={},
        holdout_ids=frozenset({1, 2, 3}),
        reserved_real_ids=frozenset({1, 2, 3}),
        earnings_domain_ids=frozenset({1, 2}),
    )
    observed_rows = []
    for person_id in (1, 2):
        for year in range(1976, 2014):
            observed_rows.append(
                {
                    "person_id": person_id,
                    "period": year,
                    "age": (
                        year - 1954 if person_id == 1 else pd.NA
                    ),
                    "earnings": 9_000.0,
                }
            )
    reference = replace(
        claiming.load_claim_age_reference(),
        supplement_year=2014,
    )
    inputs = SimpleNamespace(
        earnings_panel=pd.DataFrame(observed_rows),
        refit_inputs=SimpleNamespace(
            claiming_reference=reference,
            family_context=SimpleNamespace(
                marriage_records=pd.DataFrame(
                    {"person_id": [1], "birth_year": [1954]}
                )
            ),
        ),
    )
    draws = tuple(
        FirstReportProjectionDraw(
            draw_index=draw_index,
            root_seed=DRAW_ROOT_SEEDS[draw_index],
            projection=tiny_projection(draw_index),
            collector={},
        )
        for draw_index in DRAW_INDICES
    )
    return FirstReportProjectionBatch(
        inputs=inputs,
        phase=PhaseWithForbiddenBundle(population),
        incumbent_phase=None,
        fit_preflight={},
        first_marriage_disclosure={},
        preflight_1={},
        preflight_2={},
        draws=draws,
    )


def execute_projection(*_args, **_kwargs):
    import build_m4_gate_floors

    expected = (root / "scripts/build_m4_gate_floors.py").resolve()
    if Path(build_m4_gate_floors.__file__).resolve() != expected:
        raise AssertionError("compute imported an unregistered scripts module")
    observed["compute_module"] = build_m4_gate_floors
    return tiny_batch()


def build_artifact(prepared, **_kwargs):
    import build_m4_gate_floors

    if not isinstance(prepared, preparation.PreparedFirstReportBatch):
        raise AssertionError("production preparation did not run")
    if len(prepared.draws) != 20:
        raise AssertionError("production preparation omitted a draw")
    draw = prepared.draws[0]
    births = {
        row.person_id: (row.birth_year, row.source.value)
        for row in draw.inclusion.births
    }
    if births != {
        1: (1954, "exact_marriage"),
        2: (1954, "derived_projection_age"),
        3: (None, "unresolved"),
    }:
        raise AssertionError(f"real birth preparation changed: {births!r}")
    origin = next(
        row for row in draw.inclusion.origins if row.person_id == 3
    )
    if (
        origin.origin.value != "opening_backfill"
        or origin.operative_claim_age is not None
        or origin.operative_claim_year is not None
    ):
        raise AssertionError("unresolved candidate crossed C.5")
    exclusions = [
        (row.person_id, row.reason) for row in draw.inclusion.exclusions
    ]
    if exclusions != [(3, "excluded_birth_year_unresolved")]:
        raise AssertionError(
            f"real C.5 exclusions changed: {exclusions!r}"
        )
    if [row.person_id for row in draw.inclusion.included] != [1, 2]:
        raise AssertionError("real baseline inclusion changed")
    scenario_counts = {
        name: int(values["complete_included_set_count"])
        for name, values in draw.birth_timing_sensitivity.scenarios.items()
    }
    if scenario_counts != {
        "baseline": 2,
        "birth_minus_1": 2,
        "birth_plus_1": 1,
    }:
        raise AssertionError(
            f"real sensitivity preparation changed: {scenario_counts!r}"
        )
    if sys.path[0] != str(root / "scripts"):
        raise AssertionError("scripts scope ended before artifact build")
    if build_m4_gate_floors is not observed["compute_module"]:
        raise AssertionError("compute scripts module was not held through build")
    artifact = base_operations.build_artifact(prepared, **_kwargs)
    observed["artifact"] = artifact
    return artifact


def publish_artifact(_token, artifact):
    if artifact is not observed.get("artifact"):
        raise AssertionError("real artifact assembly changed")
    count_row = artifact["counts"]["per_draw"][0]
    expected_counts = {
        "inclusion__excluded_birth_year_unresolved__unweighted": 1,
        "birth_source__exact_marriage__unweighted": 1,
        "birth_source__derived_projection_age__unweighted": 1,
        "birth_source__unresolved__unweighted": 1,
        "inclusion__included__unweighted": 2,
    }
    for key, expected in expected_counts.items():
        if count_row[key] != expected:
            raise AssertionError(f"real artifact count changed: {key}")
    scenarios = artifact["diagnostics"]["birth_timing_sensitivity"][
        "per_draw"
    ][0]["coherent_shift_stress_scenarios"]["full_scenario_ledger"][
        "scenarios"
    ]
    observed_counts = {
        name: row["complete_included_set_count"]
        for name, row in scenarios.items()
    }
    if observed_counts != {
        "baseline": 2,
        "birth_minus_1": 2,
        "birth_plus_1": 1,
    }:
        raise AssertionError("real artifact sensitivity changed")
    return root / "runs/first_estimates_v1.json"


base_operations = coordinator._default_operations()
operations = replace(
    base_operations,
    load_parameters=load_registered_parameters,
    execute_projection=execute_projection,
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
            # The fixture simulates a pre-publication ceremony; once the
            # real v1 pair is committed at HEAD, the coordinator's
            # published-v1 guard would correctly refuse to start, so the
            # fixture repository removes it from its own committed state.
            published = [
                path
                for path in (
                    "runs/first_estimates_v1.json",
                    "runs/first_estimates_v1.json.env.json",
                )
                if (worktree / path).exists()
            ]
            if published:
                subprocess.run(
                    [git, "-C", str(worktree), "rm", "-q", "--", *published],
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


def test__sealed_interpreter__runs_c5_sensitivity_and_compute_surface(
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
