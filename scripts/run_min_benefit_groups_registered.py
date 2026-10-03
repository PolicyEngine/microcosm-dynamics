"""Exercise 4 (Track M) by MINT8 subgroups: the registered post hoc run.

NASI follow-up package G4c.  The only entry point that computes exercise
4's group breakdowns on real data
(:mod:`populace_dynamics.group_breakdowns.min_benefit`).  It runs once,
after its own issue #42 registration comment exists, at exactly the commit
that comment registers, and writes a NEW artifact beside the committed
exercise-4 run, which it never edits.  It mirrors
``scripts/run_track_m_registered.py``.

**Preflight** (:func:`preflight`, before anything is loaded):

* the registration pointer must be a comment on issue #42, and not
  Registration 17's (the breakdown's cells are new outcomes, so they need
  a new registration);
* the working tree must be clean and ``HEAD`` must equal
  ``--registered-commit``;
* the output artifact and its sidecar must not exist yet (both are
  created exclusively, so a file that appears during the run is not
  overwritten either);
* the parent artifact ``runs/replication_urban2006_minimum_benefit_v1.json``
  must be the committed bytes (SHA-256 pinned) with its sidecar binding
  them, Registration 17's pointer and commit, and the M1 specification it
  recorded must be the file at this commit; the M1 block must still pass
  Track M's registered-run gate.

**Before any PSID file is read:** Track M's components and parameter pins
(``run_track_m_registered.check_runnable`` and ``committed_parameters``,
reused through importlib); the pins must equal the parent's
``checks.parameter_pins``; the environment (Track A's ``_environment``
resolver, as exercises 3 and 4 reuse it) must match the parent's sidecar
in Python, numpy, pandas and scipy versions and the policyengine-us
revision, because the reproduction is compared bit for bit
(``scripts/make_nasi_repro_venv.sh`` builds that environment).

**The computation** is :func:`populace_dynamics.group_breakdowns.
min_benefit.run_group_breakdowns` with the staged-PSID loaders: Track M's
``cohort.load_cohort_inputs`` and G1's ``group_attributes.
load_group_attributes`` (anchor wave 2023).  It re-executes Registration
17's computation, refuses unless every recomputed block equals the parent
exactly (before the group-attribute loader is called), then computes the
cells and refuses unless G3's Total, Female and Male cells equal the
registered All, Women and Men cells.  A refusal writes nothing.

The artifact carries Track M's labels, "registered, one-shot, post hoc,
not blind" and "report-only", the covered-earnings disclosure (d280), the
reproduction record, the SHA-256 of every module the run composes and the
run block; it publishes regardless of outcome.  Nothing here has been run
on real data.

Usage::

    python scripts/run_min_benefit_groups_registered.py \\
        --registration-pointer <new issue #42 comment URL> \\
        --registered-commit <full SHA> \\
        [--output runs/replication_urban2006_minimum_benefit_groups_posthoc_v1.json]

Writes the artifact and a ``.env.json`` sidecar next to it.
"""

from __future__ import annotations

import argparse
import datetime
import importlib.util
import subprocess
import sys
import sysconfig
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from populace_dynamics.group_breakdowns import common  # noqa: E402
from populace_dynamics.group_breakdowns import (  # noqa: E402
    min_benefit as mb,
)
from populace_dynamics.min_benefit_track_m import (  # noqa: E402
    COVERED_EARNINGS_DISCLOSURE,
)
from populace_dynamics.min_benefit_track_m.evaluation import (  # noqa: E402
    PSID_FILES,
    TrackMParameters,
)
from populace_dynamics.min_benefit_track_m.specification import (  # noqa: E402
    M1_SPECIFICATION_PATH,
    check_specification_for_registered_run,
    m1_parameter_block,
)
from populace_dynamics.min_benefit_track_m.tabulation import (  # noqa: E402
    REGISTERED_REAL,
)

REGISTERED_HEADER = (
    "REGISTERED ONE-SHOT POST HOC RUN - exercise 4 (Track M: the share of "
    "OASDI beneficiaries 62+ receiving a minimum benefit, options 2-5, "
    "income year 2022) by MINT8 characteristic subgroups. "
    + "; ".join(mb.LABELS)
    + ". "
    + COVERED_EARNINGS_DISCLOSURE
    + ". Publishes regardless of outcome."
)
DEFAULT_OUTPUT = mb.OUTPUT_ARTIFACT_PATH
#: The environment fields the reproduction needs to match the parent's.
ENVIRONMENT_FIELDS: tuple[str, ...] = (
    "python",
    "packages.numpy",
    "packages.pandas",
    "packages.scipy",
    "policyengine_us_parameters.revision",
)
#: The files this run composes, beyond the packages in
#: :data:`COMPOSED_PACKAGES`; their SHA-256 go in the artifact.  The
#: registered commit on a clean tree fixes every byte; these digests make
#: the composition auditable from the artifact alone.
COMPOSED_SOURCES: tuple[str, ...] = (
    "scripts/run_min_benefit_groups_registered.py",
    "scripts/run_track_m_registered.py",
    "scripts/run_track_a_registered.py",
    "src/populace_dynamics/estimates/group_breakdown.py",
    "src/populace_dynamics/estimates/lifetime_measures.py",
    "src/populace_dynamics/estimates/uniform_cut_tabulation.py",
    "src/populace_dynamics/estimates/cola_age_profile.py",
    "src/populace_dynamics/estimates/career.py",
    "src/populace_dynamics/estimates/parameters.py",
    "src/populace_dynamics/cohorts/group_attributes.py",
    "src/populace_dynamics/cohorts/psid2010.py",
    "src/populace_dynamics/data/group_attributes_psid.py",
    "src/populace_dynamics/data/social_security_receipt.py",
    "src/populace_dynamics/data/prior_year_labor_income.py",
    "data/external/group_category_schemes_v1.json",
    "data/external/mint8_row_categories.json",
    "data/external/mint8_lifetime_quintile_definitions.json",
    "data/external/ssa_oasdi_tax_rates_2026.json",
    "data/external/ssa_trust_fund_interest_rates_2026.json",
    "docs/design/minimum_benefits_comparison.md",
)
#: Packages every module of which the run composes (all ``*.py``).
COMPOSED_PACKAGES: tuple[str, ...] = (
    "src/populace_dynamics/group_breakdowns",
    "src/populace_dynamics/min_benefit_track_m",
    "src/populace_dynamics/ss",
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _script_module(name: str) -> Any:
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_{name}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def preflight(
    *,
    registration_pointer: str,
    registered_commit: str,
    output: Path,
    git: Callable[..., str] = _git,
    parent_path: Path = mb.PARENT_ARTIFACT_PATH,
    parent_sha256: str = mb.PARENT_ARTIFACT_SHA256,
    specification_path: Path = M1_SPECIFICATION_PATH,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Refuse to run unless this is the registered one-shot state."""

    if not isinstance(
        registration_pointer, str
    ) or not common.REGISTRATION_POINTER.fullmatch(registration_pointer):
        raise ValueError(
            "the registration pointer must be an issue #42 comment URL "
            "(https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
            "#issuecomment-<id>)"
        )
    if registration_pointer == mb.PARENT_REGISTRATION_POINTER:
        raise ValueError(
            "the breakdown's cells are new outcomes: they need their own "
            "issue #42 registration, not Registration 17's"
        )
    state = common.preflight(
        registration_pointer=registration_pointer,
        registered_commit=registered_commit,
        output=output,
        root=root,
        git=git,
    )
    parent = mb.load_parent_artifact(
        parent_path, expected_sha256=parent_sha256
    )
    binding = mb.check_parent_binding(
        parent,
        specification_sha256=common.file_sha256(specification_path),
    )
    check_specification_for_registered_run(m1_parameter_block())
    return {"head": state.git_head, "parent": parent, "binding": binding}


def _field(record: Mapping[str, Any], dotted: str) -> Any:
    value: Any = record
    for key in dotted.split("."):
        value = (value or {}).get(key) if isinstance(value, Mapping) else None
    return value


def check_environment(
    environment: Mapping[str, Any], parent_sidecar: Mapping[str, Any]
) -> dict[str, Any]:
    """Refuse an environment other than the parent run's.

    Compares :data:`ENVIRONMENT_FIELDS` with the parent sidecar's
    ``environment``; the platform string is recorded, not compared.
    """

    recorded = parent_sidecar.get("environment") or {}
    fields = {
        name: {
            "parent": _field(recorded, name),
            "this_run": _field(environment, name),
        }
        for name in ENVIRONMENT_FIELDS
    }
    differ = [
        name
        for name, pair in fields.items()
        if pair["parent"] is None or pair["parent"] != pair["this_run"]
    ]
    if differ:
        raise ValueError(
            f"the environment differs from the parent run's in {differ}; "
            "the reproduction is compared bit for bit (build the recorded "
            "environment with scripts/make_nasi_repro_venv.sh)"
        )
    return {
        "fields": fields,
        "matches_parent": True,
        "platform_parent": recorded.get("platform"),
        "platform_this_run": environment.get("platform"),
        "gil_disabled_this_run": bool(
            sysconfig.get_config_var("Py_GIL_DISABLED")
        ),
        "gil_note": (
            "recorded, not compared: the parent's sidecar does not record "
            "the interpreter build; scripts/make_nasi_repro_venv.sh builds "
            "the default (GIL) CPython, and a build that changed any float "
            "would show as a reproduction mismatch"
        ),
    }


def check_parameter_pins(
    pins: Mapping[str, str], parent: common.CommittedArtifact
) -> dict[str, str]:
    """The Track M parameter pins must equal the parent's recorded pins."""

    recorded = (parent.document.get("checks") or {}).get("parameter_pins")
    if dict(pins) != dict(recorded or {}):
        raise ValueError(
            "the Track M parameter files' SHA-256 differ from the parent "
            "run's checks.parameter_pins"
        )
    return dict(pins)


def composed_paths(
    paths: Sequence[str] = COMPOSED_SOURCES,
    packages: Sequence[str] = COMPOSED_PACKAGES,
) -> tuple[str, ...]:
    """Every composed file, repository-relative and sorted."""

    found = set(paths)
    for package in packages:
        found.update(
            str(path.relative_to(ROOT))
            for path in (ROOT / package).glob("*.py")
        )
    return tuple(sorted(found))


def source_sha256(paths: Sequence[str] | None = None) -> dict[str, str]:
    """SHA-256 of every composed file (refuses a missing one)."""

    return {
        path: common.file_sha256(ROOT / path)
        for path in (composed_paths() if paths is None else paths)
    }


def _default_cohort_loader() -> Any:
    from populace_dynamics.min_benefit_track_m import cohort

    return cohort.load_cohort_inputs()


def _default_side_frame_loader(person_ids: Sequence[int]) -> Any:
    from populace_dynamics.cohorts import group_attributes

    return group_attributes.load_group_attributes(
        person_ids, anchor_waves=mb.ANCHOR_WAVES
    )


def execute(
    *,
    registration_pointer: str,
    registered_commit: str,
    output: Path,
    argv: Sequence[str],
    git: Callable[..., str] = _git,
    track_m_script: Any = None,
    environment: Callable[..., dict[str, Any]] | None = None,
    load_parameters: (
        Callable[[Mapping[str, Any]], tuple[TrackMParameters, dict]] | None
    ) = None,
    load_cola: Callable[[], Any] | None = None,
    load_cohort_inputs: Callable[[], Any] = _default_cohort_loader,
    load_side_frame: Callable[
        [Sequence[int]], Any
    ] = _default_side_frame_loader,
    parent_path: Path = mb.PARENT_ARTIFACT_PATH,
    parent_sha256: str = mb.PARENT_ARTIFACT_SHA256,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Preflight, the pre-PSID checks, the run, then the exclusive writes.

    The keyword hooks default to the staged-PSID loaders, the real
    resolvers and the committed parent; tests replace them with INVENTED
    ones.  Nothing is written unless :func:`~populace_dynamics.
    group_breakdowns.min_benefit.run_group_breakdowns` returns.
    """

    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    state = preflight(
        registration_pointer=registration_pointer,
        registered_commit=registered_commit,
        output=output,
        git=git,
        parent_path=parent_path,
        parent_sha256=parent_sha256,
        root=root,
    )
    parent: common.CommittedArtifact = state["parent"]
    track_m = track_m_script or _script_module("run_track_m_registered")
    block = m1_parameter_block()
    track_m.check_runnable()
    parameters, pins = (load_parameters or track_m.committed_parameters)(block)
    pins = check_parameter_pins(pins, parent)
    resolve = (
        environment or _script_module("run_track_a_registered")._environment
    )
    env = resolve(ssa_parameters_revision=parameters.params.pe_us_revision)
    env_check = check_environment(env, parent.sidecar or {})
    if load_cola is None:
        from populace_dynamics.estimates.parameters import load_cola_history

        load_cola = load_cola_history
    cola = load_cola()
    document = mb.run_group_breakdowns(
        parameters=parameters,
        parent=parent,
        data_provenance=REGISTERED_REAL,
        registration_pointer=registration_pointer,
        load_cohort_inputs=load_cohort_inputs,
        load_side_frame=load_side_frame,
        cola_rates=cola,
        provenance_kind=PSID_FILES,
        source={"cola_history": dict(cola.provenance)},
    )
    artifact = {
        **document,
        "header": REGISTERED_HEADER,
        "reads_comparator_values": False,
        "registration": {
            "pointer": registration_pointer,
            "binding_to_parent": state["binding"],
        },
        "checks": {
            "parameter_pins": pins,
            "environment": env_check,
        },
        "code_sha256": source_sha256(),
        "run": {
            "started": started,
            "finished": datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat(),
            "registration_pointer": registration_pointer,
            "registered_commit": registered_commit,
            "git_head": state["head"],
            "git_clean": True,
            "command": " ".join(
                [
                    "python",
                    "scripts/run_min_benefit_groups_registered.py",
                    *argv,
                ]
            ),
        },
    }
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    common.write_artifact_pair(
        output=output, artifact=artifact, environment=env
    )
    return artifact


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--registration-pointer", required=True)
    parser.add_argument("--registered-commit", required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    execute(
        registration_pointer=args.registration_pointer,
        registered_commit=args.registered_commit,
        output=args.output,
        argv=list(sys.argv[1:] if argv is None else argv),
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
