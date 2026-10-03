"""Registered, one-shot post hoc group breakdowns of projection tests 1/3.

This entry point composes the frozen registered builders and refuses before
group attributes or cells unless every parent-artifact value reproduces.
Each exercise has its own new artifact and environment sidecar because its
registration, parent specification, and row manifest are independent. No
real-data run is authorized without a new issue #42 comment and its clean
registered commit. The v1 artifacts remain the reproduction references.

Usage::

    python scripts/run_projection_groups_registered.py \\
        --exercise cola --registration-pointer <issue #42 comment URL> \\
        --registered-commit <full SHA>

See scripts/run_track_a_registered.py and scripts/run_fra68_registered.py
for the frozen builders, guards, provenance records and environment resolver.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from populace_dynamics.group_breakdowns import common  # noqa: E402

REGISTRATION_POINTER = common.REGISTRATION_POINTER
PARENT_SHA256 = {
    "cola": (
        "270acf292682b8111133f9047f366c93173e713bc422cb7e108bd064ac33d53e"
    ),
    "fra68": (
        "9c768fff17bfd828d16bdca738f92d8487f082ec99cd94ee0c73959bb050746e"
    ),
}
PARENT_ENVIRONMENT_SHA256 = {
    "cola": (
        "a79b54ec5d3aadaacee41e8877e5a985821fbd3bba82b97fe8fa962d8aa8e6f9"
    ),
    "fra68": (
        "8c04da45818cc88ece6693b12fd630b624c3c8d6843829ed92dec258af81fab6"
    ),
}
POSTHOC_LABEL = "registered, one-shot, post hoc, not blind"
POSTHOC_SPECIFICATION_SHA256 = (
    "0cfaab69a4e50e5e77754d164915c591e5168b97878eba7c505e7242fa3660cf"
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _script_module(name: str) -> Any:
    """Import the existing registered script, without executing its main."""
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_groups_{name}", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot resolve frozen registered script {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _check_specification(
    exercise: str, specification: dict[str, Any] | None, config: Any
) -> None:
    if exercise == "cola":
        legacy = _script_module("run_track_a_registered")
        legacy.check_specification_ratified(
            legacy.a1_parameter_block()
            if specification is None
            else specification
        )
    else:
        legacy = _script_module("run_fra68_registered")
        legacy.check_specification_for_registered_run(
            (
                legacy.e1_parameter_block()
                if specification is None
                else specification
            ),
            config or legacy.FRA68Config(),
        )


def preflight(
    *,
    exercise: str,
    registration_pointer: str,
    registered_commit: str,
    output: Path,
    git: Any = _git,
    specification: dict[str, Any] | None = None,
    config: Any = None,
    root: Path = ROOT,
) -> dict[str, str]:
    """Require registration, clean exact HEAD and a new output pair first."""
    if exercise not in PARENT_SHA256:
        raise ValueError("exercise must be cola or fra68")
    state = common.preflight(
        registration_pointer=registration_pointer,
        registered_commit=registered_commit,
        output=output,
        root=root,
        git=git,
    )
    _check_specification(exercise, specification, config)
    return {"head": state.git_head}


def _parent(exercise: str) -> tuple[dict[str, Any], dict[str, Any], str]:
    """Read only the committed model artifact and its binding sidecar."""
    path = ROOT / "runs" / f"replication_urban2010_{exercise}_v1.json"
    digest = _sha256(path)
    if digest != PARENT_SHA256[exercise]:
        raise ValueError("parent artifact SHA-256 differs from its frozen pin")
    sidecar_path = path.with_suffix(".env.json")
    sidecar_digest = _sha256(sidecar_path)
    if sidecar_digest != PARENT_ENVIRONMENT_SHA256[exercise]:
        raise ValueError(
            "parent environment SHA-256 differs from its frozen pin"
        )
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    if (
        sidecar.get("artifact_sha256") != digest
        or sidecar.get("artifact") != path.name
    ):
        raise ValueError("parent environment sidecar is not bound to artifact")
    return (
        json.loads(path.read_text(encoding="utf-8")),
        sidecar["environment"],
        sidecar_digest,
    )


def check_reproduction_environment(
    current: dict[str, Any], expected: dict[str, Any], revision: str
) -> None:
    """Require the four recorded versions and the frozen parameter checkout."""
    if current.get("python") != expected.get("python"):
        raise ValueError("Python version differs from parent environment")
    for package in ("numpy", "pandas", "scipy"):
        wanted = expected.get("packages", {}).get(package)
        if not wanted or current.get("packages", {}).get(package) != wanted:
            raise ValueError(
                f"{package} version differs from parent environment"
            )
    if revision != "a03e82e503":
        raise ValueError("policyengine-us parameters require a03e82e503")


def build_registered_inputs(
    exercise: str,
    config: Any,
    *,
    parent: dict[str, Any],
    expected_environment: dict[str, Any],
) -> tuple[Any, dict[str, Any], dict[int, Any], Any]:
    """Compose existing cohort readers exactly, retaining marriage inputs.

    No PSID reader is called outside psid2010 cohort code. Version guards run
    before cohort loading. The raw marriage histories remain unused until the
    common reproduction gate has passed; their later episode loader is lazy.
    """
    legacy = _script_module(
        "run_track_a_registered"
        if exercise == "cola"
        else "run_fra68_registered"
    )
    track_config = config if exercise == "cola" else config.track_a_config()
    base_params = legacy.load_ssa_parameters()
    environment = _script_module("run_track_a_registered")._environment(
        ssa_parameters_revision=base_params.pe_us_revision
    )
    check_reproduction_environment(
        environment, expected_environment, base_params.pe_us_revision
    )
    claiming_pmf = legacy.load_claiming_pmf()
    raw_inputs = {}
    cohorts = {}
    for wave in config.anchor_waves:
        raw = legacy.psid2010.load_psid2010_inputs(anchor_wave=wave)
        a3 = legacy.psid2010.build_psid2010_cohort(
            raw, legacy.psid2010.Psid2010CohortSpec(anchor_wave=wave)
        )
        raw_inputs[wave] = raw
        cohorts[wave] = legacy.prepare_track_a_cohort(
            a3, data_provenance="registered_real", config=track_config
        )
    params = legacy.tr2008_ssa_parameters(
        base_params, alternative=config.tr2008_alternative
    )
    realized = legacy.load_cola_history()
    baseline = legacy.tr2008_baseline_cola(
        realized,
        first_year=config.tr2008_first_rate_year,
        last_year=config.reference_year,
        alternative=config.tr2008_alternative,
    )
    rate_check = _script_module("track_a_dry_run")._spec_rate_check(baseline)
    di_rates = legacy.load_di_entitlement_rates(config.di_spec)
    first_projection_year = min(track_config.start_years.values()) + 1
    mortality = legacy.load_tr2008_mortality(
        range(first_projection_year, config.reference_year + 1),
        alternative=config.tr2008_alternative,
        base_year=config.mortality_base_year,
    )
    provenance = {
        "ssa_parameters": params.pe_us_revision,
        "statutory_capture": {
            "path": str(legacy.CAPTURE_PATH.relative_to(ROOT)),
            "sha256": legacy.CAPTURE_SHA256,
        },
        "tr2008_file_sha256": dict(legacy.tr2008.FILE_SHA256),
        "di_rates": {
            key: value
            for key, value in di_rates.provenance.items()
            if key.endswith("sha256")
        },
        "cola_history_sha256": realized.provenance["sha256"],
        "claiming_reference_sha256": _sha256(
            legacy.psid2010.CLAIMING_REFERENCE_PATH
        ),
        "a1_specification_sha256": _sha256(legacy.A1_SPECIFICATION_PATH),
        "mortality": dict(mortality.provenance),
        "psid_inputs": {
            str(wave): dict(raw.provenance) for wave, raw in raw_inputs.items()
        },
    }
    if exercise == "fra68":
        provenance["e1_specification_sha256"] = _sha256(
            legacy.E1_SPECIFICATION_PATH
        )
    if provenance != parent.get("inputs_provenance"):
        raise ValueError("registered inputs differ from parent provenance")
    primary, *others = (cohorts[wave] for wave in config.anchor_waves)
    inputs = legacy.TrackAInputs(
        cohort=primary,
        params=params,
        baseline=baseline,
        di_rates=di_rates,
        population_mortality=mortality,
        claiming_pmf=claiming_pmf,
        provenance=provenance,
        additional_cohorts=tuple(others),
    )
    return inputs, environment, raw_inputs, rate_check


def write_new_pair(
    output: Path, artifact: dict[str, Any], environment: dict[str, Any]
) -> None:
    """Serialize finite JSON first, then exclusively create the new pair.

    A sidecar race or write failure removes only files this invocation created.
    Existing artifact/sidecar bytes are never touched. The caller invokes this
    only after reproduction and all group computations have succeeded.
    """
    common.write_artifact_pair(
        output=output, artifact=artifact, environment=environment
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--exercise", choices=("cola", "fra68"), required=True)
    parser.add_argument("--registration-pointer", required=True)
    parser.add_argument("--registered-commit", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    output = args.output or (
        ROOT
        / "runs"
        / f"replication_urban2010_{args.exercise}_groups_posthoc_v1.json"
    )
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    state = preflight(
        exercise=args.exercise,
        registration_pointer=args.registration_pointer,
        registered_commit=args.registered_commit,
        output=output,
    )
    posthoc_specification = (
        ROOT / "docs/design/nasi_projection_groups_posthoc.md"
    )
    posthoc_specification_sha256 = _sha256(posthoc_specification)
    if posthoc_specification_sha256 != POSTHOC_SPECIFICATION_SHA256:
        raise ValueError("post hoc methodology specification SHA-256 differs")
    parent, expected_environment, parent_environment_sha256 = _parent(
        args.exercise
    )
    if args.registration_pointer == parent["registration_pointer"]:
        raise ValueError(
            "group outputs require a new issue #42 registration pointer"
        )
    if args.exercise == "cola":
        from populace_dynamics.cola_track_a import TrackAConfig
        from populace_dynamics.group_breakdowns.cola import reproduce_cola

        config = TrackAConfig()
        reproduce = reproduce_cola
    else:
        from populace_dynamics.fra68_track import FRA68Config
        from populace_dynamics.group_breakdowns.fra68 import reproduce_fra68

        config = FRA68Config()
        reproduce = reproduce_fra68
    from populace_dynamics.cohorts import psid2010
    from populace_dynamics.group_breakdowns.common import (
        LifetimeOptions,
        run_group_breakdown,
    )

    inputs, environment, raw_inputs, rate_check = build_registered_inputs(
        args.exercise,
        config,
        parent=parent,
        expected_environment=expected_environment,
    )
    replay = reproduce(
        inputs,
        config=config,
        registration_pointer=parent["registration_pointer"],
        check_committed_parameters=True,
        progress=lambda message: print(message, file=sys.stderr),
    )

    def marriage_episodes(wave: int) -> tuple[Any, tuple[int, ...]]:
        history = raw_inputs[wave].marriage_history
        return (
            psid2010._episodes_with_separation(history),
            tuple(int(value) for value in history.person_id.unique()),
        )

    result = run_group_breakdown(
        replay,
        parent,
        inputs=inputs,
        config=config,
        parent_sha256=PARENT_SHA256[args.exercise],
        registration_pointer=args.registration_pointer,
        lifetime_options=LifetimeOptions(
            marriage_episode_loader=marriage_episodes
        ),
    )
    artifact = {
        **result,
        "header": f"{POSTHOC_LABEL}; report-only; exercise {args.exercise}",
        "labels": list(
            dict.fromkeys([*parent["labels"], POSTHOC_LABEL, "report-only"])
        ),
        "publishes_regardless": True,
        "comparator_seal_opened_before_commit": False,
        "data_provenance": "registered_real",
        "registration_pointer": args.registration_pointer,
        "parent_registration_pointer": parent["registration_pointer"],
        "parent_environment_sha256": parent_environment_sha256,
        "posthoc_specification": {
            "path": str(posthoc_specification.relative_to(ROOT)),
            "sha256": posthoc_specification_sha256,
        },
        "checks": {"registered_rate_path": rate_check},
        "run": {
            "started": started,
            "finished": datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat(),
            "registration_pointer": args.registration_pointer,
            "registered_commit": args.registered_commit,
            "git_head": state["head"],
            "git_clean": True,
            "command": " ".join(
                [
                    "python",
                    "scripts/run_projection_groups_registered.py",
                    *(sys.argv[1:] if argv is None else argv),
                ]
            ),
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    write_new_pair(output, artifact, environment)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
