"""Exercise 3 (FRA to 68) registered one-shot run on the real PSID cohorts.

This is the only entry point that computes the exercise-3 five-group 2030
statistic on real data.  It mirrors ``scripts/run_track_a_registered.py``
and runs once, after the issue #42 registration comment exists, at exactly
the commit that comment registers:

* the registration pointer must be a comment on issue #42
  (``.../issues/42#issuecomment-<id>``);
* the working tree must be clean and ``HEAD`` must equal
  ``--registered-commit``;
* the E1 specification (``docs/design/urban2010_fra68_comparison.md``)
  must be ratified: its section 21 status and version must each say
  "ratified" as a word, with no negating word and no candidate, draft,
  not-merged, not-ratified or referee marker (A7's fail-closed test,
  ``cola_age_profile.specification_unratified_fields``, with E1's
  ``referee`` marker; each row's tabulation records its ratification
  status by the same test).  The block may list no decision awaiting Max
  (decision record d188), must record his ruling on every decision field
  with the configuration following each, and must equal the code
  (``fra68_track.runner.check_specification_for_registered_run``); the
  committed draft (``e1-draft-4``) is refused;
* the output artifact must not exist yet (one shot, no overwrite; it is
  created exclusively);
* the configuration is :class:`FRA68Config`'s default, which the E1
  specification freezes (K=20 draws, rows F0-F8, primary schedule P3); no
  flag changes it;
* every committed input is value-checked (``run_fra68`` refuses any
  mismatch for a ``registered_real`` cohort) and the cohorts carry the
  provenance the A3 builder recorded from the PSID files it read;
* the A1 rate path (which E1 carries over to both scenarios) must equal
  A2's ``cola_path`` and the runtime baseline before any projection.

The artifact publishes regardless of outcome.  It never reads a sealed
comparator; the comparator is opened only after this artifact is
committed.  Nothing here has been run on real data: the preflight refuses
while E1 is a draft.

Usage::

    python scripts/run_fra68_registered.py \\
        --registration-pointer <issue #42 comment URL> \\
        --registered-commit <full SHA> \\
        [--output runs/replication_urban2010_fra68_v1.json]

Writes the artifact and a ``.env.json`` sidecar next to it.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.metadata
import importlib.util
import json
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from populace_dynamics.cohorts import psid2010  # noqa: E402
from populace_dynamics.cola_track_a import (  # noqa: E402
    TrackAInputs,
    prepare_track_a_cohort,
)
from populace_dynamics.cola_track_a.mortality import (  # noqa: E402
    load_tr2008_mortality,
)
from populace_dynamics.cola_track_a.runner import (  # noqa: E402
    A1_SPECIFICATION_PATH,
    load_claiming_pmf,
    tr2008_baseline_cola,
    tr2008_ssa_parameters,
)
from populace_dynamics.cola_track_a.statutory import (  # noqa: E402
    CAPTURE_PATH,
    CAPTURE_SHA256,
)
from populace_dynamics.data import tr2008  # noqa: E402
from populace_dynamics.engine.di_entitlement_rates import (  # noqa: E402
    load_di_entitlement_rates,
)
from populace_dynamics.estimates.parameters import (  # noqa: E402
    load_cola_history,
)
from populace_dynamics.fra68_track import FRA68Config, run_fra68  # noqa: E402
from populace_dynamics.fra68_track.runner import (  # noqa: E402
    E1_SPECIFICATION_PATH,
    check_specification_for_registered_run,
    e1_parameter_block,
)
from populace_dynamics.ss.params import load_ssa_parameters  # noqa: E402

REGISTERED_HEADER = (
    "REGISTERED ONE-SHOT RUN - DynaSim exercise 3 (full retirement age to "
    "68, 2030 age profile) on the Track A pipeline. Python oracle "
    "benefits: not Axiom. Publishes regardless of outcome."
)
DEFAULT_OUTPUT = ROOT / "runs" / "replication_urban2010_fra68_v1.json"
#: A comment on issue #42, the registration issue; nothing else is a
#: registration pointer.
REGISTRATION_POINTER = re.compile(
    r"https://github\.com/PolicyEngine/microcosm-dynamics/issues/42"
    r"#issuecomment-[0-9]+"
)
ENV_PACKAGES = (
    "numpy",
    "pandas",
    "scipy",
    "policyengine-us",
    "populace-dynamics",
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


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
    git: Any = _git,
    specification: dict[str, Any] | None = None,
    config: FRA68Config | None = None,
) -> dict[str, str]:
    """Refuse to run unless this is the registered one-shot state."""

    if not REGISTRATION_POINTER.fullmatch(registration_pointer):
        raise ValueError(
            "the registration pointer must be an issue #42 comment URL "
            "(https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
            "#issuecomment-<id>)"
        )
    if not re.fullmatch(r"[0-9a-f]{40}", registered_commit):
        raise ValueError("--registered-commit must be a full 40-hex SHA")
    head = git("rev-parse", "HEAD")
    if head != registered_commit:
        raise ValueError(
            f"HEAD {head} is not the registered commit {registered_commit}"
        )
    if git("status", "--porcelain") != "":
        raise ValueError("the working tree must be clean for a registered run")
    check_specification_for_registered_run(
        e1_parameter_block() if specification is None else specification,
        config or FRA68Config(),
    )
    if output.exists() or output.with_suffix(".env.json").exists():
        raise ValueError(
            f"{output} already exists: the registered run is one-shot"
        )
    return {"head": head}


def _write_new(path: Path, text: str) -> None:
    """Create ``path`` exclusively: never overwrite (one shot)."""

    with path.open("x", encoding="utf-8") as handle:
        handle.write(text)


def _environment() -> dict[str, Any]:
    versions = {}
    for name in ENV_PACKAGES:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": versions,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--registration-pointer", required=True)
    parser.add_argument("--registered-commit", required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    config = FRA68Config()
    state = preflight(
        registration_pointer=args.registration_pointer,
        registered_commit=args.registered_commit,
        output=args.output,
        config=config,
    )
    track_config = config.track_a_config()
    claiming_pmf = load_claiming_pmf()
    raw_inputs = {}
    cohorts = {}
    for wave in config.anchor_waves:
        raw = psid2010.load_psid2010_inputs(anchor_wave=wave)
        a3 = psid2010.build_psid2010_cohort(
            raw, psid2010.Psid2010CohortSpec(anchor_wave=wave)
        )
        raw_inputs[wave] = raw
        cohorts[wave] = prepare_track_a_cohort(
            a3, data_provenance="registered_real", config=track_config
        )
    base_params = load_ssa_parameters()
    params = tr2008_ssa_parameters(
        base_params, alternative=config.tr2008_alternative
    )
    realized = load_cola_history()
    baseline = tr2008_baseline_cola(
        realized,
        first_year=config.tr2008_first_rate_year,
        last_year=config.reference_year,
        alternative=config.tr2008_alternative,
    )
    # Before any projection: the A1 rate path, which E1 carries over to
    # both scenarios, equals A2's and the runtime baseline.
    rate_check = _script_module("track_a_dry_run")._spec_rate_check(baseline)
    di_rates = load_di_entitlement_rates(config.di_spec)
    first_projection_year = min(track_config.start_years.values()) + 1
    mortality = load_tr2008_mortality(
        range(first_projection_year, config.reference_year + 1),
        alternative=config.tr2008_alternative,
        base_year=config.mortality_base_year,
    )
    provenance = {
        "ssa_parameters": params.pe_us_revision,
        "statutory_capture": {
            "path": str(CAPTURE_PATH.relative_to(ROOT)),
            "sha256": CAPTURE_SHA256,
        },
        "tr2008_file_sha256": dict(tr2008.FILE_SHA256),
        "di_rates": {
            key: value
            for key, value in di_rates.provenance.items()
            if key.endswith("sha256")
        },
        "cola_history_sha256": realized.provenance["sha256"],
        "claiming_reference_sha256": _sha256(psid2010.CLAIMING_REFERENCE_PATH),
        "a1_specification_sha256": _sha256(A1_SPECIFICATION_PATH),
        "e1_specification_sha256": _sha256(E1_SPECIFICATION_PATH),
        "mortality": dict(mortality.provenance),
        "psid_inputs": {
            str(wave): dict(raw.provenance) for wave, raw in raw_inputs.items()
        },
    }
    primary, *others = (cohorts[wave] for wave in config.anchor_waves)
    result = run_fra68(
        TrackAInputs(
            cohort=primary,
            params=params,
            baseline=baseline,
            di_rates=di_rates,
            population_mortality=mortality,
            claiming_pmf=claiming_pmf,
            provenance=provenance,
            additional_cohorts=tuple(others),
        ),
        config=config,
        registration_pointer=args.registration_pointer,
        progress=lambda message: print(message, file=sys.stderr),
        check_committed_parameters=True,
    )
    artifact = {
        "header": REGISTERED_HEADER,
        "publishes_regardless": True,
        "comparator_seal_opened_before_commit": False,
        **result,
        "checks": {"a1_rate_path": rate_check},
        "gaps": _script_module("fra68_dry_run").gaps(),
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
                    "scripts/run_fra68_registered.py",
                    *(sys.argv[1:] if argv is None else argv),
                ]
            ),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    _write_new(
        args.output,
        json.dumps(artifact, indent=2, sort_keys=False, allow_nan=False)
        + "\n",
    )
    _write_new(
        args.output.with_suffix(".env.json"),
        json.dumps(
            {
                "artifact": args.output.name,
                "artifact_sha256": _sha256(args.output),
                "environment": _environment(),
            },
            indent=2,
        )
        + "\n",
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
