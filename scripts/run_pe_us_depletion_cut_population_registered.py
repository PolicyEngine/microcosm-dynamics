"""Run Registration 19, or its explicitly labelled invented rehearsal.

The main interpreter never imports PolicyEngine-US or reads HDF. Each
simulation uses an explicit invented or registered dataset in a fresh,
sequential child. All checks precede publication, and files are exclusive.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import platform
import re
import resource
import shlex
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
from collections.abc import Callable, Mapping
from decimal import Decimal
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from populace_dynamics.bridge import (  # noqa: E402
    depletion_cut_population as pop,
)
from populace_dynamics.bridge import policyengine_us as bridge  # noqa: E402

REGISTRATION_POINTER = re.compile(
    r"^https://github\.com/PolicyEngine/microcosm-dynamics/issues/42"
    r"#issuecomment-[0-9]+$"
)
DEFAULT_OUTPUT = ROOT / "runs/pe_us_depletion_cut_population_v1.json"
DEFAULT_DOCS_DIR = (
    ROOT / "docs/analysis/pe_us_depletion_cut_population_20261001"
)
CHILD = ROOT / "src/populace_dynamics/bridge/depletion_cut_population_child.py"
COMPONENTS = (
    "social_security_retirement",
    "social_security_survivors",
    "social_security_dependents",
    "social_security_disability",
)
DRY_RUN_LABEL = "INVENTED DRY RUN - NOT RESULTS"
INTERVAL_LABEL = (
    "a frame-resampling interval: it excludes imputation, calibration "
    "and model uncertainty"
)
CONTEXT_SHA256 = (
    "e488dce9bac3b1645813440acc73e7bd93e60e70a7e1ba4d902ed83f088b81d0"
)
SHARE_STATISTICS = (
    "F_test",
    "P_test",
    "N_test",
    "F_no",
    "P_no",
    "N_no",
    "R_test",
    "R_no",
    "B",
    "B_part",
    "B_cond",
)


def _import_script(name: str) -> Any:
    """Import a reviewed script by path, including its script imports."""

    scripts = str(ROOT / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    spec = importlib.util.spec_from_file_location(
        name, ROOT / f"scripts/{name}.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import reviewed script")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


minimum = _import_script("pe_us_minimum_benefit_sample_households")
sample = _import_script("pe_us_depletion_cut_sample_households")


class Refusal(ValueError):
    """A failed registered check, with no per-person values attached."""

    def __init__(self, check: int | str, name: str, failing_persons: int = 0):
        self.check = check
        self.name = name
        self.failing_persons = int(failing_persons)
        # Only the numbered refusal checks of specification section 10 end
        # a registration by rule. Preflight, child, pipeline, source and
        # hook failures are operational: section 14 decides whether one is
        # an external infrastructure failure eligible for re-execution.
        self.registered_check = isinstance(check, int) or (
            isinstance(check, str) and check.isdigit()
        )
        self.child_returncode: int | None = None
        super().__init__(
            f"check {check}: {name}; failing persons: {failing_persons}"
        )


def _sha256(path: Path) -> str:
    """Hash a file without keeping the full frame in memory."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git(*args: str) -> str:
    """Run a read-only repository command."""

    return minimum._git(ROOT, *args)


def specification_block(path: Path | None = None) -> dict[str, Any]:
    """Read the binding machine-readable block without editing it."""

    source = (path or ROOT / pop.SPECIFICATION_PATH).read_text()
    section = source.split("## 18. Machine-readable block", 1)[1]
    return json.loads(section.split("```json\n", 1)[1].split("```", 1)[0])


def preflight(
    *,
    registration_pointer: str,
    registered_commit: str,
    output: Path,
    git: Callable[..., str] = _git,
    specification: Mapping[str, Any] | None = None,
    specification_sha256: str | None = None,
) -> dict[str, Any]:
    """Refuse every unregistered, mutable or already-written run state."""

    if not REGISTRATION_POINTER.fullmatch(registration_pointer):
        raise Refusal(
            "preflight", "registration pointer is not an issue #42 comment URL"
        )
    if not re.fullmatch(r"[0-9a-fA-F]{40}", registered_commit):
        raise Refusal(
            "preflight", "registered commit must be a full 40-hex SHA"
        )
    head = git("rev-parse", "HEAD")
    if head.lower() != registered_commit.lower():
        raise Refusal("preflight", "HEAD differs from registered commit")
    if git("status", "--porcelain"):
        raise Refusal("preflight", "working tree is dirty")
    block = specification_block() if specification is None else specification
    if (
        block.get("status") != "ratified_frozen"
        or block.get("version") != "sa1-ratified-1"
        or pop.SPECIFICATION_STATUS != "ratified_frozen"
        or pop.SPECIFICATION_VERSION != "sa1-ratified-1"
    ):
        raise Refusal(
            "preflight", "specification is not ratified_frozen sa1-ratified-1"
        )
    digest = specification_sha256 or _sha256(ROOT / pop.SPECIFICATION_PATH)
    if pop.SPECIFICATION_SHA256 is None or digest != pop.SPECIFICATION_SHA256:
        raise Refusal(
            "preflight", "specification SHA-256 differs from code pin"
        )
    if _present(output) or _present(output.with_suffix(".env.json")):
        raise Refusal(
            "preflight", "artifact or environment sidecar already exists"
        )
    return {"head": head, "git_clean": True, "skipped": []}


def release_decision(metadata: Mapping[str, Any], *, invented: bool) -> str:
    """The cos decision that holds the release (specification section 14).

    A registered run must name it before it starts, so that the artifact
    records its id. An invented dry run has nothing to release.
    """

    value = metadata.get("release_held_for")
    if invented:
        return value if isinstance(value, str) and value else "not_applicable"
    if not isinstance(value, str) or not re.fullmatch(r"d[0-9]+", value):
        raise Refusal(
            "preflight",
            "run metadata must name the release decision (release_held_for)",
        )
    return value


def _inside(path: Path, root: Path) -> bool:
    """Whether a resolved path lies in a directory, including symlinks."""

    return path.resolve().is_relative_to(root.resolve())


def _present(path: Path) -> bool:
    """Treat dangling symlinks as existing destinations as well."""

    return path.exists() or path.is_symlink()


def output_destinations(
    raw_dir: Path,
    output: Path | None,
    docs_dir: Path | None,
    *,
    invented: bool,
) -> tuple[Path, Path]:
    """Keep all rehearsal files outside the repository and inside raw-dir."""

    if _inside(raw_dir, ROOT):
        raise Refusal("preflight", "raw-dir must be outside the repository")
    output = output or (
        raw_dir / "invented_population.json" if invented else DEFAULT_OUTPUT
    )
    docs_dir = docs_dir or (
        raw_dir / "invented_report" if invented else DEFAULT_DOCS_DIR
    )
    if invented:
        if any(
            _inside(path, ROOT) or not _inside(path, raw_dir)
            for path in (output, docs_dir)
        ):
            raise Refusal(
                "preflight",
                "invented dry run outputs must lie in raw-dir; runs/ and docs/ are refused",
            )
    if _present(output) or _present(output.with_suffix(".env.json")):
        raise Refusal(
            "preflight", "artifact or environment sidecar already exists"
        )
    for name in ("report.md", "replacement.png", "replacement.svg"):
        if _present(docs_dir / name):
            raise Refusal("preflight", "report or chart already exists")
    return output, docs_dir


def _labels(invented: bool) -> list[str]:
    """Give each output all specification labels and its rehearsal warning."""

    return ([DRY_RUN_LABEL] if invented else []) + list(pop.LABELS)


def _run_child(
    python: Path, job: dict[str, Any], timeout: float
) -> dict[str, Any]:
    """Run one child synchronously with an explicit deadline."""

    env = dict(os.environ)
    env.update(
        {
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
        }
    )
    try:
        child = subprocess.run(
            [str(python), str(CHILD)],
            input=json.dumps(job),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired as error:
        raise Refusal(
            "child", "child process exceeded explicit timeout"
        ) from error
    except OSError as error:
        raise Refusal("child", "child process could not start") from error
    if child.returncode:
        # Logs are operational evidence outside the repository. They never
        # enter the refusal document, which contains no paths or values.
        output = Path(job.get("output_path", job["frame_path"]))
        log = Path(
            job.get("error_log_path", output.with_suffix(".stderr.txt"))
        )
        with log.open("x") as stream:
            stream.write(child.stderr)
        refusal = Refusal(
            "child",
            (
                "child process was killed by a signal"
                if child.returncode < 0
                else "child process exited nonzero"
            ),
        )
        refusal.child_returncode = child.returncode
        raise refusal
    try:
        return json.loads(child.stdout)
    except json.JSONDecodeError as error:
        raise Refusal(
            "child", "child did not return the JSON protocol"
        ) from error


def _load_arrays(path: Path) -> dict[str, np.ndarray]:
    """Copy a child result and close its NPZ file immediately."""

    with np.load(path, allow_pickle=False) as arrays:
        return {name: arrays[name].copy() for name in arrays.files}


def _run_array_child(
    python: Path,
    job: dict[str, Any],
    timeout: float,
    owned_paths: set[Path],
) -> dict[str, Any]:
    """Stage child arrays privately, then copy to an exclusive destination.

    Timeout and child failures remove the private directory, including any
    partial arrays. Canonical paths become owned only after exclusive open
    succeeds, so a raced external file is preserved.
    """

    destination = Path(job["output_path"])
    with tempfile.TemporaryDirectory(
        prefix=".population-child-", dir=destination.parent
    ) as private:
        staged = Path(private) / destination.name
        result = _run_child(
            python,
            {
                **job,
                "output_path": str(staged),
                "error_log_path": str(destination.with_suffix(".stderr.txt")),
            },
            timeout,
        )
        with destination.open("xb") as target:
            owned_paths.add(destination)
            with staged.open("rb") as source:
                shutil.copyfileobj(source, target)
        result["array_path"] = str(destination)
        return result


def _record(
    checks: dict[str, Any],
    group: str,
    key: str,
    name: str,
    failures: int,
    **extra: Any,
) -> None:
    """Record check counts and raise only for refusal checks."""

    checks[group][key] = {
        "name": name,
        "passed": failures == 0,
        "failing_persons": int(failures),
        **extra,
    }
    if failures and group == "refusals":
        raise Refusal(key, name, failures)


def _structural_check(
    probe: Mapping[str, np.ndarray],
    baseline: Mapping[str, np.ndarray],
    *,
    invented: bool,
) -> dict[str, Any]:
    """Check memberships, nesting, resources, age and synthetic proportions."""

    n = len(probe["person_id"])
    household = np.asarray(probe["household_index"], dtype=np.int64)
    unit = np.asarray(probe["marital_unit_index"], dtype=np.int64)
    if (
        len(household) != n
        or len(unit) != n
        or n == 0
        or (household < 0).any()
        or (unit < 0).any()
    ):
        raise Refusal(
            5, "one household and marital unit membership per person", n
        )
    h = len(probe["household_id"])
    u = len(probe["marital_unit_id"])
    if household.max() >= h or unit.max() >= u:
        raise Refusal(5, "membership index exceeds entity count", n)
    sizes = np.bincount(unit, minlength=u)
    owners = np.full(u, -1, dtype=np.int64)
    owners[unit] = household
    invalid = (
        (sizes[unit] < 1) | (sizes[unit] > 2) | (owners[unit] != household)
    )
    invalid |= baseline["ssi_countable_resources"] < 0
    invalid |= ~np.isfinite(baseline["ssi_countable_resources"])
    invalid |= probe["age"] != probe["frame_age"]
    if (
        len(np.unique(probe["person_id"])) != n
        or np.any(sizes == 0)
        or np.any(np.bincount(household, minlength=h) == 0)
    ):
        invalid[:] = True
    for key in COMPONENTS:
        invalid |= ~(probe[key] >= 0)
    frame = np.column_stack([probe[f"frame_{key}"] for key in COMPONENTS])
    synthetic, wrong_split = pop.synthetic_split(
        {key: probe[f"frame_{key}"] for key in COMPONENTS}
    )
    invalid |= wrong_split
    # Recorded, not refused: the specification states that no other record
    # carries more than one positive component, but does not refuse on it.
    nonsynthetic_multi = (~synthetic) & ((frame > 0).sum(axis=1) > 1)
    if not invented and int(synthetic.sum()) != pop.SYNTHETIC_SPLIT["count"]:
        invalid[:] = True
    return {
        "failures": int(invalid.sum()),
        "failure_mask": invalid,
        "marital_unit_sizes": sizes,
        "synthetic": synthetic,
        "other_multi_component_records": int(nonsynthetic_multi.sum()),
        "synthetic_count": int(synthetic.sum()),
        "synthetic_count_basis": (
            "invented population count; real count pin inapplicable"
            if invented
            else "registered frame count 5924"
        ),
    }


def runtime_checks(
    probe: Mapping[str, np.ndarray],
    simulations: Mapping[str, Mapping[str, Mapping[str, np.ndarray]]],
    inputs: Mapping[str, Mapping[str, np.ndarray]],
    checks: dict[str, Any],
    *,
    invented: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Separate registration-ending checks from R3/R4 validity checks."""

    baseline = simulations["baseline"]["asset_test_as_encoded"]
    baseline_fail = np.zeros(len(probe["person_id"]), dtype=bool)
    cut_fail = baseline_fail.copy()
    identity_fail = baseline_fail.copy()
    resources_fail = baseline_fail.copy()
    boundary = pop.resource_boundary_mask(
        baseline["ssi_countable_resources"],
        probe["marital_unit_index"],
        baseline["ssi_claim_is_joint"],
        float(baseline["individual_limit"]),
        float(baseline["couple_limit"]),
    )
    encoded = pop.resource_test_encoded(
        baseline["ssi_countable_resources"],
        probe["marital_unit_index"],
        baseline["ssi_claim_is_joint"],
        float(baseline["individual_limit"]),
        float(baseline["couple_limit"]),
    )
    encoded_fail = (encoded != baseline["meets_ssi_resource_test"]) & ~boundary
    for scenario, variants in simulations.items():
        for variant, arrays in variants.items():
            for name in COMPONENTS:
                baseline_fail |= arrays[f"baseline_{name}"] != probe[name]
                baseline_fail |= ~np.isfinite(arrays[f"baseline_{name}"])
            for name in (
                "person_id",
                "household_id",
                "marital_unit_id",
                "household_index",
                "marital_unit_index",
            ):
                if not np.array_equal(arrays[name], probe[name]):
                    baseline_fail[:] = True
            # Refusal 4: each calculated component equals the float32 of
            # the input set, exactly; uncut components therefore equal the
            # baseline exactly, including disability under the OASI cut.
            for name in COMPONENTS:
                expected = (
                    np.asarray(inputs[scenario][name], dtype=np.float64)
                    .astype(np.float32)
                    .astype(np.float64)
                )
                cut_fail |= arrays[name] != expected
            if scenario == "oasi22":
                cut_fail |= (
                    arrays["social_security_disability"]
                    != simulations["baseline"][variant][
                        "social_security_disability"
                    ]
                )
            resources_fail |= (
                arrays["ssi_countable_resources"]
                != baseline["ssi_countable_resources"]
            )
        tested = variants["asset_test_as_encoded"]
        no = variants["no_asset_test"]
        for measure in ("ssi_if_takes_up", "ssi"):
            difference = (
                tested[measure]
                - no[measure] * tested["meets_ssi_resource_test"]
            )
            identity_fail |= ~np.isfinite(difference) | (
                np.abs(difference) > pop.IDENTITY_TOLERANCE
            )
        scenario_boundary = pop.resource_boundary_mask(
            tested["ssi_countable_resources"],
            probe["marital_unit_index"],
            tested["ssi_claim_is_joint"],
            float(tested["individual_limit"]),
            float(tested["couple_limit"]),
        )
        python_test = pop.resource_test_encoded(
            tested["ssi_countable_resources"],
            probe["marital_unit_index"],
            tested["ssi_claim_is_joint"],
            float(tested["individual_limit"]),
            float(tested["couple_limit"]),
        )
        encoded_fail |= (
            python_test != tested["meets_ssi_resource_test"]
        ) & ~scenario_boundary
        boundary |= scenario_boundary
    _record(
        checks,
        "refusals",
        "3",
        "baseline component arrays and entity order identical in every child",
        int(baseline_fail.sum()),
    )
    _record(
        checks,
        "refusals",
        "4",
        "each calculated component equals the float32 of the input set; OASI preserves disability",
        int(cut_fail.sum()),
    )
    structure = _structural_check(probe, baseline, invented=invented)
    _record(
        checks,
        "refusals",
        "5",
        "structural memberships, nesting, nonnegative resources and components, age and synthetic splits",
        int(np.sum(structure["failure_mask"] | resources_fail)),
        synthetic_count=structure["synthetic_count"],
        other_multi_component_records=structure[
            "other_multi_component_records"
        ],
        synthetic_count_basis=structure["synthetic_count_basis"],
    )
    _record(
        checks,
        "row_validity",
        "a",
        "SSI identity in every scenario",
        int(identity_fail.sum()),
    )
    _record(
        checks,
        "row_validity",
        "b",
        "Python encoded resource test equals PE-US away from boundaries",
        int(encoded_fail.sum()),
        boundary_persons=int(boundary.sum()),
    )
    reasons = [
        {"check": key, **record}
        for key, record in checks["row_validity"].items()
        if not record["passed"]
    ]
    return structure, reasons


def cell_assignments(
    probe: Mapping[str, np.ndarray], baseline: Mapping[str, np.ndarray]
) -> tuple[dict[str, np.ndarray], np.ndarray]:
    """Fix every one-way cell and both quintiles at encoded baseline."""

    household = probe["household_index"]
    income = pop.income_per_person(
        baseline["household_market_income"],
        baseline["household_benefits"],
        baseline["household_health_benefits"],
        baseline["household_count_people"],
    )[household]
    weights = baseline["household_weight"][household]
    ss_beneficiaries = sum(probe[name] for name in COMPONENTS) > 0
    cutpoints = pop.quintile_cutpoints(income, weights, ss_beneficiaries)
    return {
        "all": np.full(len(household), "all"),
        "age": pop.age_band(probe["age"]),
        "sex": pop.sex_cell(probe["is_female"]),
        "marital": pop.marital_cell(probe["A_MARITL"]),
        "race": pop.race_cell(probe["cps_race"], probe["is_hispanic"]),
        "income_quintile": pop.assign_quintile(income, cutpoints),
        "income_quintile_pe_decile": pop.pe_decile_quintile(
            baseline["household_income_decile"]
        )[household],
    }, cutpoints


def prepare_jobs(
    probe: Mapping[str, np.ndarray],
    simulations: Mapping[str, Any],
    cuts: Mapping[str, np.ndarray],
    structure: Mapping[str, Any],
    assignments: Mapping[str, np.ndarray],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Prepare unit labels once; R5 restricts only reporting denominators."""

    base = simulations["baseline"]["asset_test_as_encoded"]
    household = probe["household_index"]
    unit = probe["marital_unit_index"]
    weights = base["household_weight"][household]
    resources = base["ssi_countable_resources"]
    limits = float(base["individual_limit"]), float(base["couple_limit"])
    tests = {
        "R3": pop.resource_test_spousal(
            resources, unit, structure["marital_unit_sizes"], *limits
        ),
        "R4": pop.resource_test_household(
            resources,
            unit,
            household,
            structure["marital_unit_sizes"],
            *limits,
        ),
    }
    jobs, row_labels = {}, {}
    for scenario, cut in cuts.items():
        for row in pop.ROWS:
            measure = "ssi" if row == "R2" else "ssi_if_takes_up"
            no_base = simulations["baseline"]["no_asset_test"][measure]
            no_scenario = simulations[scenario]["no_asset_test"][measure]
            if row in tests:
                test_base, test_scenario = (
                    no_base * tests[row],
                    no_scenario * tests[row],
                )
            else:
                test_base = simulations["baseline"]["asset_test_as_encoded"][
                    measure
                ]
                test_scenario = simulations[scenario]["asset_test_as_encoded"][
                    measure
                ]
            labels_no = pop.replacement_labels(cut, no_base, no_scenario, unit)
            labels_test = pop.replacement_labels(
                cut, test_base, test_scenario, unit
            )
            universe = cut > 0
            if row == "R5":
                universe &= ~structure["synthetic"]
            row_labels[f"{row}/{scenario}"] = {
                "labels_test": labels_test,
                "labels_no": labels_no,
                "universe": universe,
                "test_baseline": test_base,
                "test_scenario": test_scenario,
            }
            for dimension, cells in pop.CELLS.items():
                for cell in cells:
                    jobs[f"{row}/{scenario}/{dimension}/{cell}"] = {
                        "labels_test": labels_test,
                        "labels_no": labels_no,
                        "weights": weights,
                        "beneficiary_mask": universe,
                        "cell_mask": assignments[dimension] == cell,
                    }
    return jobs, row_labels


def check_partitions(
    jobs: Mapping[str, Mapping[str, Any]],
    assignments: Mapping[str, np.ndarray],
    checks: dict[str, Any],
) -> None:
    """Validate exhaustive labels and cell masks before first statistic."""

    failure = np.zeros(len(assignments["all"]), dtype=bool)
    for dimension, cells in pop.CELLS.items():
        failure |= (
            np.sum([assignments[dimension] == cell for cell in cells], axis=0)
            != 1
        )
    for job in jobs.values():
        selected = job["beneficiary_mask"] & job["cell_mask"]
        for name in ("labels_test", "labels_no"):
            labels = job[name]
            failure |= selected & ~np.isin(
                labels, [pop.FULL, pop.PART, pop.NONE]
            )
            failure |= selected & (
                ~np.isfinite(job["weights"]) | (job["weights"] < 0)
            )
    _record(
        checks,
        "refusals",
        "6",
        "labels sum to one and one-way cells partition every universe",
        int(failure.sum()),
    )


def _reason_table(
    labels: Mapping[str, Any],
    baseline: Mapping[str, np.ndarray],
    unit: np.ndarray,
    weights: np.ndarray,
) -> dict[str, Any]:
    """Partition no-replacement beneficiaries on the eligibility basis."""

    immigration = (
        baseline["immigration_status"].astype(str) == "CITIZEN"
    ) | baseline["is_ssi_qualified_noncitizen"].astype(bool)
    reasons = pop.reason_partition(
        baseline["is_ssi_aged_blind_disabled"],
        immigration,
        unit,
        labels["labels_no"],
    )
    selected = labels["universe"] & (labels["labels_no"] == pop.NONE)
    return {
        reason: {
            "n": int(np.sum(selected & (reasons == reason))),
            "W": float(weights[selected & (reasons == reason)].sum()),
        }
        for reason in (
            "not_abd",
            "immigration",
            "no_positive_modeled_ssi_response",
        )
    }


def _unit_diagnostics(
    cut: np.ndarray,
    labels: Mapping[str, Any],
    unit: np.ndarray,
    weights: np.ndarray,
) -> dict[str, Any]:
    """Count each attributed marital unit once using its household weight."""

    count = int(unit.max()) + 1
    unit_cut = np.bincount(unit, weights=cut, minlength=count)
    change = np.bincount(
        unit,
        weights=labels["test_scenario"] - labels["test_baseline"],
        minlength=count,
    )
    owners = np.zeros(count, dtype=np.int64)
    owners[unit] = np.arange(len(unit))
    unit_weights = weights[owners]
    attributed = (
        np.bincount(unit, weights=labels["universe"], minlength=count) > 0
    )
    over = attributed & (change > unit_cut + pop.TOLERANCE_DOLLARS)
    falling = attributed & (change < -pop.TOLERANCE_DOLLARS)
    return {
        "attributed_marital_units": int(attributed.sum()),
        "over_replacing": {
            "n": int(over.sum()),
            "W": float(unit_weights[over].sum()),
        },
        "ssi_falls": {
            "n": int(falling.sum()),
            "W": float(unit_weights[falling].sum()),
            "weighted_ssi_loss": float(
                np.sum(-change[falling] * unit_weights[falling])
            ),
        },
    }


def context_block(
    snapshot: Path | None,
    probe: Mapping[str, np.ndarray],
    baseline: Mapping[str, np.ndarray],
) -> dict[str, Any]:
    """Place frame counts beside a pinned snapshot, or record its absence."""

    weights = baseline["household_weight"][probe["household_index"]]
    beneficiaries = sum(probe[name] for name in COMPONENTS) > 0
    frame = {"beneficiaries": float(weights[beneficiaries].sum())}
    for measure in ("ssi_if_takes_up", "ssi"):
        frame[f"beneficiaries_receiving_{measure}"] = float(
            weights[beneficiaries & (baseline[measure] > 0)].sum()
        )
    result: dict[str, Any] = {
        "unscored": True,
        "frame_relative_weighted_counts": frame,
        "status": "not_provided",
    }
    result.update(_context_source(snapshot))
    return result


def _context_source(snapshot: Path | None) -> dict[str, Any]:
    """Validate only the source record before entering statistics."""

    result: dict[str, Any] = {"status": "not_provided"}
    if snapshot is not None:
        try:
            record = json.loads(snapshot.read_text())
        except (OSError, ValueError) as error:
            raise Refusal(
                "context", "SSA snapshot record could not be read"
            ) from error
        if not isinstance(record, dict):
            raise Refusal(
                "context", "SSA snapshot record must be a JSON object"
            )
        values = record.get("values_thousands")
        if not isinstance(values, dict) or not all(
            isinstance(record.get(key), str)
            for key in ("sha256", "url", "table")
        ):
            raise Refusal(
                "context", "SSA snapshot fields have invalid shapes or types"
            )
        if (
            record.get("sha256") != CONTEXT_SHA256
            or values.get("social_security_only") != 65522
            or values.get("both") != 2533
        ):
            raise Refusal(
                "context",
                "SSA snapshot does not match specification source and values",
            )
        result.update(
            {
                "status": "provided",
                "source": {
                    key: record[key] for key in ("sha256", "url", "table")
                },
                "values_thousands": values,
                "note": "December 2024; dual entitlement counted once; SSI includes federally administered state supplementation",
            }
        )
    return result


def _environment() -> dict[str, Any]:
    """Describe versions without interpreter or installation paths."""

    packages = {}
    for name in ("numpy", "pandas", "matplotlib", "populace-dynamics"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = "not_installed"
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": packages,
    }


def _write_new(
    path: Path, text: str, *, created_paths: set[Path] | None = None
) -> None:
    """Create an output exclusively, preserving any existing bytes."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        if created_paths is not None:
            created_paths.add(path)
        stream.write(text)


def _percent(value: float | None) -> str:
    """Format a table share while retaining undefined values."""

    return "not estimable" if value is None else f"{value:.2%}"


def markdown_report(document: Mapping[str, Any]) -> str:
    """Render every row and cell with R0/R3/R4 together in each table."""

    lines = [
        "# " + document["header"][0],
        "",
        *[f"> {label}\n" for label in document["header"]],
        "Shares describe replacement of each marital unit's combined cut. Completely blocked, among all cut beneficiaries, is B; completely blocked, among beneficiaries SSI would otherwise compensate, is B_cond.",
        "",
        f"Intervals are {INTERVAL_LABEL}.",
        "",
    ]
    for scenario in pop.SCENARIOS:
        for dimension, cells in pop.CELLS.items():
            lines += [
                f"## {scenario}: {dimension}",
                "",
                "| Cell | Row | n | W | F_test | P_test | N_test | F_no | P_no | N_no | R_test | R_no | B | B_part | n_cond | W_cond | B_cond | Flags / validity |",
                "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
            ]
            for cell in cells:
                for row in ("R0", "R3", "R4", "R2", "R5"):
                    entry = document["results"][row][scenario][dimension][cell]
                    flags = []
                    if entry.get("small_cell"):
                        flags.append("small cell (n < 50)")
                    if entry.get("small_cell_cond"):
                        flags.append("B_cond small cell (n_cond < 50)")
                    if entry["status"] == "invalid":
                        flags.append(
                            "invalid: "
                            + "; ".join(
                                reason["name"]
                                for reason in entry["invalid_reasons"]
                            )
                        )
                    values = [cell, row, str(entry["n"]), f"{entry['W']:.2f}"]
                    values += [
                        _percent(entry[key]) for key in SHARE_STATISTICS[:10]
                    ]
                    values += [
                        str(entry["n_cond"]),
                        f"{entry['W_cond']:.2f}",
                        _percent(entry["B_cond"]),
                        "; ".join(flags),
                    ]
                    lines.append("| " + " | ".join(values) + " |")
            lines += [
                "",
                "Bootstrap intervals and transition counts for every cell:",
                "",
                "```json",
                json.dumps(
                    {
                        row: document["results"][row][scenario][dimension]
                        for row in ("R0", "R3", "R4", "R2", "R5")
                    },
                    indent=2,
                    allow_nan=False,
                ),
                "```",
                "",
            ]
    lines += [
        "## Unscored diagnostics",
        "",
        "```json",
        json.dumps(document["diagnostics"], indent=2, allow_nan=False),
        "```",
        "",
        "## Named differences",
        "",
    ]
    differences = document["named_differences"]
    if isinstance(differences, Mapping):
        lines += [f"{key}. {value}" for key, value in differences.items()]
    else:
        lines += list(differences)
    return "\n".join(lines) + "\n"


def write_chart(
    document: Mapping[str, Any],
    directory: Path,
    *,
    created_paths: set[Path] | None = None,
) -> dict[str, Any]:
    """Write one headline replacement chart, retaining all output labels."""

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return {"status": "skipped", "reason": "matplotlib is not installed"}
    table = document["results"]["R0"]["oasi22"]
    cells = [
        (dimension, cell)
        for dimension, names in pop.CELLS.items()
        for cell in names
    ]
    height = max(8, len(cells) * 0.25)
    fig, axes = plt.subplots(1, 2, figsize=(13, height), sharey=True)
    positions = np.arange(len(cells))
    names = [f"{dimension}: {cell}" for dimension, cell in cells]
    for axis, suffix, title in zip(
        axes,
        ("test", "no"),
        ("Encoded resource test", "No asset test"),
        strict=True,
    ):
        left = np.zeros(len(cells))
        for code, color in zip(
            ("F", "P", "N"), ("#21918c", "#fde725", "#443983"), strict=True
        ):
            values = np.array(
                [
                    table[dimension][cell][f"{code}_{suffix}"] or 0
                    for dimension, cell in cells
                ]
            )
            axis.barh(
                positions,
                values,
                left=left,
                color=color,
                label={"F": "Full", "P": "Part", "N": "None"}[code],
            )
            left += values
        axis.set_title(title)
        axis.set_xlim(0, 1)
        axis.set_xlabel("Weighted share of cut beneficiaries")
        axis.legend(loc="lower right")
        for position, (dimension, cell) in enumerate(cells):
            if table[dimension][cell][f"F_{suffix}"] is None:
                axis.text(
                    0.02, position, "not estimable", va="center", fontsize=7
                )
    axes[0].set_yticks(positions, names)
    axes[0].invert_yaxis()
    # The title starts with the frame-relative label even in a rehearsal;
    # the warning and remaining labels are also visible in the image.
    title_labels = list(pop.LABELS)
    if DRY_RUN_LABEL in document["header"]:
        title_labels.append(DRY_RUN_LABEL)
    chart_title = "\n".join(
        textwrap.fill(label, width=140) for label in title_labels
    )
    fig.suptitle(chart_title + "\nR0, 22 percent OASI cut", fontsize=7)
    fig.tight_layout(rect=(0, 0, 1, 0.81))
    metadata = json.dumps(
        {
            "header": document["header"],
            "named_differences": document["named_differences"],
        },
        ensure_ascii=False,
    )
    directory.mkdir(parents=True, exist_ok=True)
    try:
        for suffix in ("png", "svg"):
            path = directory / f"replacement.{suffix}"
            with path.open("xb") as stream:
                if created_paths is not None:
                    created_paths.add(path)
                values = (
                    {"Title": "\n".join(title_labels), "Description": metadata}
                    if suffix == "svg"
                    else {
                        "Title": "\n".join(title_labels),
                        "Description": metadata,
                    }
                )
                fig.savefig(stream, format=suffix, dpi=130, metadata=values)
    finally:
        plt.close(fig)
    return {
        "status": "written",
        "files": ["replacement.png", "replacement.svg"],
    }


def write_outputs(
    document: dict[str, Any], output: Path, docs_dir: Path
) -> None:
    """Create the complete artifact, labelled sidecar, report and chart."""

    preparation_started = time.monotonic()
    minimum._no_absolute_paths(document)
    json.dumps(document, allow_nan=False)
    # Validate all environment/provenance fields before any statistic is
    # published. The digest is filled from the final serialized bytes.
    sidecar = {
        "header": document["header"],
        "named_differences": document["named_differences"],
        "artifact": output.name,
        "artifact_sha256": None,
        "environment": _environment(),
        "data_provenance": document["data_provenance"],
    }
    sidecar["environment"]["policyengine_us"] = document["provenance"][
        "policyengine_us"
    ]
    try:
        minimum._no_absolute_paths(sidecar)
    except ValueError as error:
        raise Refusal(
            7, "environment sidecar contains an absolute local path"
        ) from error
    json.dumps(sidecar, allow_nan=False)
    created_paths: set[Path] = set()
    try:
        document["chart"] = write_chart(
            document, docs_dir, created_paths=created_paths
        )
        report = markdown_report(document)
        minimum._no_absolute_paths(report)
        preparation_seconds = time.monotonic() - preparation_started
        document["run"]["output_preparation_seconds"] = preparation_seconds
        document["run"]["elapsed_seconds"] += preparation_seconds
        document["run"]["finished"] = dt.datetime.now(
            dt.timezone.utc
        ).isoformat()
        document["run"]["main_peak_rss_bytes"] = _peak_rss()
        artifact_text = json.dumps(document, indent=2, allow_nan=False) + "\n"
        sidecar["artifact_sha256"] = hashlib.sha256(
            artifact_text.encode("utf-8")
        ).hexdigest()
        sidecar_text = json.dumps(sidecar, indent=2, allow_nan=False) + "\n"
        _write_new(output, artifact_text, created_paths=created_paths)
        _write_new(
            output.with_suffix(".env.json"),
            sidecar_text,
            created_paths=created_paths,
        )
        _write_new(docs_dir / "report.md", report, created_paths=created_paths)
    except BaseException:
        for path in created_paths:
            path.unlink(missing_ok=True)
        raise


def write_refusal(
    output: Path,
    refusal: Refusal,
    phase: str,
    *,
    invented: bool,
    outcomes_computed: bool,
) -> Path:
    """Write only a refusal record: no statistic and no per-person value."""

    document = {
        "header": _labels(invented),
        "data_provenance": (
            "invented_dry_run" if invented else "registered_real"
        ),
        "refusal": {
            "check": refusal.check,
            "name": refusal.name,
            "registered_refusal_check": refusal.registered_check,
            "child_returncode": refusal.child_returncode,
            "failing_persons": refusal.failing_persons,
            "phase_reached": phase,
            "ssi_outcomes_computed_and_discarded": outcomes_computed,
        },
        "named_differences": pop.NAMED_DIFFERENCES,
    }
    minimum._no_absolute_paths(document)
    path = output.with_suffix(".refusal.json")
    _write_new(path, json.dumps(document, indent=2, allow_nan=False) + "\n")
    return path


def _peak_rss() -> int:
    """Return main-process peak RSS in bytes on supported Unix hosts."""

    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == "darwin" else value * 1024)


def argument_parser() -> argparse.ArgumentParser:
    """Build the registered and invented-rehearsal CLI."""

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--registration-pointer", default="")
    parser.add_argument("--registered-commit", default="")
    parser.add_argument("--frame-path", type=Path)
    parser.add_argument("--python")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--docs-dir", type=Path)
    parser.add_argument("--raw-dir", required=True, type=Path)
    parser.add_argument("--run-metadata", type=Path)
    parser.add_argument("--invented-dry-run", action="store_true")
    parser.add_argument("--invented-households", type=int, default=60)
    parser.add_argument("--invented-persons", type=int, default=160)
    parser.add_argument("--invented-seed", type=int, default=20261001)
    parser.add_argument("--phase-marker", type=Path)
    parser.add_argument("--phase-hook")
    parser.add_argument("--context-snapshot", type=Path)
    parser.add_argument("--child-timeout", type=float, default=7200)
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    """Run the full sequential pipeline, preserving the one-shot boundary."""

    started_clock = time.monotonic()
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    invented = args.invented_dry_run
    phase, outcomes_computed = "preflight", False
    owned_arrays: set[Path] = set()
    output = args.output or (
        args.raw_dir / "invented_population.json"
        if invented
        else DEFAULT_OUTPUT
    )
    try:
        output, docs_dir = output_destinations(
            args.raw_dir, args.output, args.docs_dir, invented=invented
        )
        raw_names = ["probe.npz", "manifest.json"]
        raw_names += [
            f"inputs_{scenario}.npz"
            for scenario in ("baseline", *pop.SCENARIOS)
        ]
        raw_names += [
            f"{scenario}_{variant}.npz"
            for scenario in ("baseline", *pop.SCENARIOS)
            for variant in pop.VARIANTS
        ]
        if invented:
            raw_names.append("invented_frame.h5")
        if any(_present(args.raw_dir / name) for name in raw_names):
            raise Refusal("preflight", "raw transport output already exists")
        if args.child_timeout <= 0:
            raise Refusal("preflight", "child timeout must be positive")
        if invented:
            if args.frame_path is not None:
                raise Refusal(
                    "preflight", "invented dry run generates its own frame"
                )
            state = {
                "head": _git("rev-parse", "HEAD"),
                "git_clean": None,
                "skipped": [
                    "registration_pointer",
                    "registered_commit",
                    "clean_tree",
                    "specification_status_version_and_hash",
                ],
            }
        else:
            state = preflight(
                registration_pointer=args.registration_pointer,
                registered_commit=args.registered_commit,
                output=output,
            )
            if args.frame_path is None:
                raise Refusal("preflight", "registered frame-path is required")
        for path in (args.phase_marker,):
            if path is not None and (
                _present(path)
                or (invented and not _inside(path, args.raw_dir))
            ):
                raise Refusal(
                    "preflight",
                    "phase marker exists or lies outside invented raw-dir",
                )
        try:
            metadata = (
                json.loads(args.run_metadata.read_text())
                if args.run_metadata
                else {}
            )
            if not isinstance(metadata, dict):
                raise ValueError("metadata must be an object")
        except (OSError, ValueError) as error:
            raise Refusal(
                "preflight", "run metadata is not a readable JSON object"
            ) from error
        try:
            minimum._no_absolute_paths(metadata)
        except ValueError as error:
            raise Refusal(
                7, "run metadata contains an absolute local path"
            ) from error
        held_for = release_decision(metadata, invented=invented)
        try:
            python = bridge._interpreter(args.python)
        except bridge.PolicyEngineUSUnavailable as error:
            raise Refusal(
                2, "PolicyEngine-US interpreter is unavailable"
            ) from error
        phase = "pinned_release"
        try:
            _, installation = minimum.pinned_release(str(python))
        except (ValueError, bridge.PolicyEngineUSUnavailable) as error:
            raise Refusal(
                2, "PolicyEngine-US installation is not the pinned release"
            ) from error
        if (
            installation["record_check"]["package_record_digest"]
            != pop.PE_US_PIN["package_record_digest"]
        ):
            raise Refusal(
                2, "PolicyEngine-US RECORD digest differs from specification"
            )
        try:
            citation = sample.trustees_citation(
                ROOT / "docs/analysis/pe_us_depletion_cut_20261001/sources",
                None,
            )
        except sample.InvariantError as error:
            raise Refusal(
                "source",
                "Trustees citation does not match committed source provenance",
            ) from error
        shares = {
            "oasi22": Decimal(citation["quotes"]["OASI"]["payable_share"]),
            "oasdi17": Decimal(citation["quotes"]["OASDI"]["payable_share"]),
        }
        try:
            minimum._no_absolute_paths(
                {
                    "installation": installation,
                    "trustees": citation,
                    "run_metadata": metadata,
                    "context": _context_source(args.context_snapshot),
                }
            )
        except ValueError as error:
            if isinstance(error, Refusal):
                raise
            raise Refusal(
                7, "scalar provenance contains an absolute local path"
            ) from error
        checks: dict[str, Any] = {
            "refusals": {},
            "row_validity": {},
            "recorded": {},
        }
        _record(
            checks,
            "refusals",
            "2",
            "PE-US release, source and RECORD match specification",
            0,
        )
        args.raw_dir.mkdir(parents=True, exist_ok=True)
        child_metadata: dict[str, Any] = {}
        job_common = {
            "registered": not invented,
            "labels": _labels(invented),
            "named_differences": pop.NAMED_DIFFERENCES,
        }
        if invented:
            phase = "write_invented"
            frame = args.raw_dir / "invented_frame.h5"
            child_metadata["write_invented"] = _run_child(
                python,
                {
                    **job_common,
                    "mode": "write-invented",
                    "frame_path": str(frame),
                    "households": args.invented_households,
                    "persons": args.invented_persons,
                    "seed": args.invented_seed,
                },
                args.child_timeout,
            )
        else:
            frame = args.frame_path
        phase = "frame_check"
        try:
            digest = pop.check_frame(frame, registered=not invented)
        except (ValueError, OSError) as error:
            raise Refusal(
                1, "frame SHA-256 fails explicit real-frame guard"
            ) from error
        digest = digest if isinstance(digest, str) else _sha256(frame)
        if not invented and (
            digest != pop.FRAME_SHA256
            or frame.stat().st_size != pop.FRAME_PIN["bytes"]
        ):
            raise Refusal(
                1, "frame bytes and SHA-256 differ from specification"
            )
        job_common.update(
            {"frame_path": str(frame), "expected_sha256": digest}
        )
        phase = "probe"
        probe_path = args.raw_dir / "probe.npz"
        child_metadata["probe"] = _run_array_child(
            python,
            {**job_common, "mode": "probe", "output_path": str(probe_path)},
            args.child_timeout,
            owned_arrays,
        )
        probe = _load_arrays(probe_path)
        component_nonfinite = np.any(
            np.stack([~np.isfinite(probe[name]) for name in COMPONENTS]),
            axis=0,
        )
        if component_nonfinite.any():
            raise Refusal(
                3,
                "probe component arrays contain nonfinite values",
                int(component_nonfinite.sum()),
            )
        _record(
            checks,
            "refusals",
            "1",
            "frame bytes and SHA-256; child verifies invented marker when applicable",
            0,
            data_provenance=(
                "invented_dry_run" if invented else "registered_real"
            ),
            sha256=digest,
            bytes=frame.stat().st_size,
        )
        baseline_components = {name: probe[name] for name in COMPONENTS}
        cuts, inputs = {}, {"baseline": baseline_components}
        for scenario, share in shares.items():
            inputs[scenario], _, cuts[scenario] = pop.cut_components(
                baseline_components, scenario, share
            )
        for scenario, components in inputs.items():
            path = args.raw_dir / f"inputs_{scenario}.npz"
            with path.open("xb") as stream:
                owned_arrays.add(path)
                np.savez(
                    stream,
                    **components,
                    metadata_labels=np.asarray(_labels(invented)),
                    metadata_named_differences=np.asarray(
                        json.dumps(pop.NAMED_DIFFERENCES)
                    ),
                )
        simulations: dict[str, Any] = {}
        for scenario in ("baseline", *pop.SCENARIOS):
            simulations[scenario] = {}
            for variant in pop.VARIANTS:
                phase = f"scenario_{scenario}_{variant}"
                print(
                    f"Running {scenario}, {variant}",
                    file=sys.stderr,
                    flush=True,
                )
                path = args.raw_dir / f"{scenario}_{variant}.npz"
                # Conservatively disclose outcomes once the first scenario
                # starts: a failing child may already have computed SSI.
                outcomes_computed = True
                child_metadata[f"{scenario}/{variant}"] = _run_array_child(
                    python,
                    {
                        **job_common,
                        "mode": "scenario",
                        "variant": variant,
                        "components_path": str(
                            args.raw_dir / f"inputs_{scenario}.npz"
                        ),
                        "output_path": str(path),
                    },
                    args.child_timeout,
                    owned_arrays,
                )
                simulations[scenario][variant] = _load_arrays(path)
        # Child JSON paths are only transport; the published run records
        # durations/RSS and scalar observations, never these local paths.
        transport_keys = {"array_path", "output_path", "frame_path", "path"}
        child_metadata = {
            key: {
                name: value
                for name, value in record.items()
                if name not in transport_keys
            }
            for key, record in child_metadata.items()
        }
        phase = "refusal_checks"
        structure, invalid_reasons = runtime_checks(
            probe, simulations, inputs, checks, invented=invented
        )
        baseline = simulations["baseline"]["asset_test_as_encoded"]
        assignments, cutpoints = cell_assignments(probe, baseline)
        nonfinite_ssi = np.zeros(len(probe["person_id"]), dtype=bool)
        for variants in simulations.values():
            for arrays in variants.values():
                for measure in ("ssi_if_takes_up", "ssi"):
                    nonfinite_ssi |= ~np.isfinite(arrays[measure])
        if nonfinite_ssi.any():
            raise Refusal(
                6,
                "nonfinite SSI cannot receive a replacement label",
                int(nonfinite_ssi.sum()),
            )
        try:
            jobs, row_labels = prepare_jobs(
                probe, simulations, cuts, structure, assignments
            )
        except ValueError as error:
            raise Refusal(
                6, "replacement labels could not partition the universe"
            ) from error
        check_partitions(jobs, assignments, checks)
        phase = "phase-statistics"
        marker_contents = {
            "phase": phase,
            "registered_commit": state["head"],
            "utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "header": _labels(invented),
            "named_differences": pop.NAMED_DIFFERENCES,
        }
        if args.phase_marker is not None:
            _write_new(
                args.phase_marker, json.dumps(marker_contents, indent=2) + "\n"
            )
        if args.phase_hook:
            try:
                hook = subprocess.run(
                    shlex.split(args.phase_hook),
                    capture_output=True,
                    text=True,
                    timeout=args.child_timeout,
                )
            except (OSError, subprocess.SubprocessError, ValueError) as error:
                raise Refusal(
                    "phase_hook", "phase-statistics hook could not complete"
                ) from error
            if hook.returncode:
                raise Refusal(
                    "phase_hook", "phase-statistics hook exited nonzero"
                )
        statistics_started = time.monotonic()
        context = context_block(args.context_snapshot, probe, baseline)
        intervals = pop.bootstrap_intervals(
            jobs, probe["household_id"][probe["household_index"]]
        )
        results: dict[str, Any] = {row: {} for row in pop.ROWS}
        for key, job in jobs.items():
            row, scenario, dimension, cell = key.split("/")
            entry = pop.statistics(**job)
            for suffix in ("test", "no"):
                shares = [
                    entry[f"{name}_{suffix}"] for name in ("F", "P", "N")
                ]
                if (
                    all(value is not None for value in shares)
                    and abs(sum(shares) - 1) > 1e-12
                ):
                    raise Refusal(
                        6,
                        "calculated label shares fail normalization",
                        entry["n"],
                    )
            invalid = row in ("R3", "R4") and bool(invalid_reasons)
            entry.update(
                {
                    "status": "invalid" if invalid else "valid",
                    "invalid_reasons": invalid_reasons if invalid else [],
                    "intervals": intervals[key],
                    "interval_label": INTERVAL_LABEL,
                }
            )
            if invalid:
                for statistic in SHARE_STATISTICS:
                    entry[statistic] = None
                    entry["undefined_reasons"][
                        statistic
                    ] = "row machinery invalid"
                    entry["intervals"][statistic] = {
                        "interval": None,
                        "valid_replicates": 0,
                        "omitted_replicates": pop.BOOTSTRAP["replicates"],
                        "undefined_reason": "row machinery invalid",
                    }
            results[row].setdefault(scenario, {}).setdefault(dimension, {})[
                cell
            ] = entry
        diagnostics: dict[str, Any] = {
            "simulated_variants": {},
            "marital_units": {},
            "reasons": {},
            "context": context,
        }
        weights = baseline["household_weight"][probe["household_index"]]
        for scenario, cut in cuts.items():
            diagnostics["simulated_variants"][scenario] = {}
            for variant in pop.VARIANTS:
                diagnostics["simulated_variants"][scenario][variant] = (
                    pop.diagnostics(
                        cut,
                        simulations["baseline"][variant],
                        simulations[scenario][variant],
                        probe["marital_unit_index"],
                        probe["household_index"],
                        baseline["household_weight"],
                    )
                )
            for row in pop.ROWS:
                key = f"{row}/{scenario}"
                diagnostics["marital_units"][key] = _unit_diagnostics(
                    cut, row_labels[key], probe["marital_unit_index"], weights
                )
                diagnostics["marital_units"][key]["status"] = (
                    "invalid"
                    if row in ("R3", "R4") and invalid_reasons
                    else "valid"
                )
                diagnostics["marital_units"][key]["invalid_reasons"] = (
                    invalid_reasons if row in ("R3", "R4") else []
                )
                if row != "R2":
                    diagnostics["reasons"][key] = _reason_table(
                        row_labels[key],
                        baseline,
                        probe["marital_unit_index"],
                        weights,
                    )
        checks["recorded"] = {
            "transition_tables": "retained for every row/scenario/cell, including label rises",
            "over_replacing_and_ssi_falls": diagnostics["marital_units"],
            "ssi_change_outside_attributed_marital_units": "retained for each simulated variant in diagnostics",
        }
        statistics_seconds = time.monotonic() - statistics_started
        peak_child = max(
            (
                record.get("peak_rss_bytes", 0)
                for record in child_metadata.values()
            ),
            default=0,
        )
        document = {
            "header": _labels(invented),
            "schema_version": "pe_us_depletion_cut_population.v1",
            "data_provenance": (
                "invented_dry_run" if invented else "registered_real"
            ),
            "publication": {
                "computed_regardless": True,
                "release_held_for": held_for,
                "release_scope": "timing and wording only",
            },
            "specification": {
                "path": str(Path(pop.SPECIFICATION_PATH).relative_to(ROOT)),
                "name": pop.SPECIFICATION_NAME,
                "version": pop.SPECIFICATION_VERSION,
                "status": pop.SPECIFICATION_STATUS,
                "sha256": _sha256(ROOT / pop.SPECIFICATION_PATH),
            },
            "provenance": {
                "registration_pointer": args.registration_pointer or None,
                "registered_commit": args.registered_commit or None,
                "microcosm_dynamics_commit": state["head"],
                "pr506_head": pop.PR506_HEAD,
                "frame_pin": pop.FRAME_PIN,
                "actual_frame": {
                    "sha256": digest,
                    "bytes": frame.stat().st_size,
                },
                "policyengine_us": installation,
                "trustees": citation,
            },
            "preflight": state,
            "headline": pop.HEADLINE,
            "checks": checks,
            "results": results,
            "diagnostics": diagnostics,
            "named_differences": pop.NAMED_DIFFERENCES,
            "income_quintile_cutpoints": cutpoints.tolist(),
            "run_metadata": metadata,
            "phase_statistics_marker": marker_contents,
            "run": {
                "started": started,
                "finished": dt.datetime.now(dt.timezone.utc).isoformat(),
                "children": child_metadata,
                "statistics_seconds": statistics_seconds,
                "elapsed_seconds": time.monotonic() - started_clock,
                "main_peak_rss_bytes": _peak_rss(),
                "child_peak_rss_bytes": peak_child,
            },
        }
        phase = "output_checks"
        try:
            minimum._no_absolute_paths(document)
        except ValueError as error:
            raise Refusal(
                7, "output contains an absolute local path"
            ) from error
        _record(
            checks,
            "refusals",
            "7",
            "no output contains an absolute local path",
            0,
        )
        raw_manifest = {
            "header": _labels(invented),
            "named_differences": pop.NAMED_DIFFERENCES,
            "data_provenance": document["data_provenance"],
            "frame_sha256": digest,
            "array_files": sorted(path.name for path in owned_arrays),
        }
        _write_new(
            args.raw_dir / "manifest.json",
            json.dumps(raw_manifest, indent=2, allow_nan=False) + "\n",
            created_paths=owned_arrays,
        )
        write_outputs(document, output, docs_dir)
        return document
    except (
        Refusal,
        OSError,
        ValueError,
        KeyError,
        subprocess.SubprocessError,
    ) as error:
        refusal = (
            error
            if isinstance(error, Refusal)
            else Refusal("pipeline", "pipeline could not complete in " + phase)
        )
        for path in owned_arrays:
            path.unlink(missing_ok=True)
        # A rejected destination never authorizes writes into runs/docs in
        # rehearsal mode, even for the refusal record.
        if _inside(args.raw_dir, ROOT):
            if refusal is error:
                raise
            raise refusal from error
        if invented and (
            _inside(output, ROOT) or not _inside(output, args.raw_dir)
        ):
            output = args.raw_dir / "invented_population.json"
        write_refusal(
            output,
            refusal,
            phase,
            invented=invented,
            outcomes_computed=outcomes_computed,
        )
        if refusal is error:
            raise
        raise refusal from error


def main(argv: list[str] | None = None) -> int:
    """Run the entry point and print only its labelled operational summary."""

    args = argument_parser().parse_args(argv)
    try:
        document = run(args)
    except Refusal as error:
        print(str(error), file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "header": document["header"],
                "named_differences": document["named_differences"],
                "checks": document["checks"]["refusals"],
                "run": document["run"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
