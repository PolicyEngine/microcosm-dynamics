"""Track A registered one-shot run on the real PSID cohorts (plan item A10).

This is the only entry point that computes the five-group 2030 COLA
statistic on real data.  It runs once, after the issue #42 registration
comment exists, at exactly the commit that comment registers:

* the registration pointer must be a comment on issue #42
  (``.../issues/42#issuecomment-<id>``);
* the working tree must be clean and ``HEAD`` must equal
  ``--registered-commit``;
* the A1 specification must be ratified: its section 21 block may not
  carry a candidate, draft or not-merged status or version (A1 says it
  authorizes no run until Max ratifies it by merging, plan section 6
  item 4);
* the output artifact must not exist yet (one shot, no overwrite; it is
  created exclusively, so a file that appears during the run is not
  overwritten either);
* the configuration is :class:`TrackAConfig`'s default, which the A1
  specification freezes (K=20 draws, rows R0-R6); no flag changes it;
* every committed input is value-checked (``run_track_a`` refuses any
  mismatch for a ``registered_real`` cohort) and the cohorts carry the
  provenance the A3 builder recorded from the PSID files it read;
* as in the dry run, the A1 rate path must equal A2's ``cola_path`` and
  the runtime baseline, and every registered row must equal the A1
  block (``scripts/track_a_dry_run.py`` ``_spec_rate_check``), before
  any projection.

The artifact publishes regardless of outcome.  It never reads the sealed
comparator; the seal is opened only after this artifact is committed.

Usage::

    python scripts/run_track_a_registered.py \\
        --registration-pointer <issue #42 comment URL> \\
        --registered-commit <full SHA> \\
        [--output runs/replication_urban2010_cola_v1.json]

Writes the artifact and a ``.env.json`` sidecar next to it.  The sidecar
records each package by the installed distribution that provides it (the
repository's ``populace_dynamics`` installs as the distribution
``pyproject.toml`` names), the project name and version at the commit,
and the revision of the policyengine-us checkout the oracle reads.
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
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import populace_dynamics  # noqa: E402
from populace_dynamics.cohorts import psid2010  # noqa: E402
from populace_dynamics.cola_track_a import (  # noqa: E402
    TrackAConfig,
    TrackAInputs,
    prepare_track_a_cohort,
    run_track_a,
)
from populace_dynamics.cola_track_a.mortality import (  # noqa: E402
    load_tr2008_mortality,
)
from populace_dynamics.cola_track_a.runner import (  # noqa: E402
    A1_SPECIFICATION_PATH,
    a1_parameter_block,
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
from populace_dynamics.estimates import cola_age_profile  # noqa: E402
from populace_dynamics.estimates.parameters import (  # noqa: E402
    load_cola_history,
)
from populace_dynamics.ss.params import load_ssa_parameters  # noqa: E402

REGISTERED_HEADER = (
    "REGISTERED ONE-SHOT RUN - Track A, DynaSim exercise 1 "
    "(COLA -1pp, 2030 age profile). Python oracle benefits: not Axiom. "
    "Publishes regardless of outcome."
)
DEFAULT_OUTPUT = ROOT / "runs" / "replication_urban2010_cola_v1.json"
#: A comment on issue #42, the registration issue (CLAUDE.md, plan item
#: A9); nothing else is a registration pointer.
REGISTRATION_POINTER = re.compile(
    r"https://github\.com/PolicyEngine/microcosm-dynamics/issues/42"
    r"#issuecomment-[0-9]+"
)
#: Markers of an A1 status or version that is not ratified.  A7 owns the
#: test (``specification_unratified_fields``), so this preflight and each
#: row's pending-rulings status apply the same one.
UNRATIFIED_MARKERS = cola_age_profile.UNRATIFIED_MARKERS
#: Import names whose installed distributions the sidecar records.  An
#: import name is not a distribution name: the repository's package
#: imports as ``populace_dynamics`` but installs as the distribution that
#: ``pyproject.toml`` names, and the oracle reads policyengine-us as a git
#: checkout rather than an installed distribution.  So each import name is
#: resolved to the distributions that provide it
#: (``importlib.metadata.packages_distributions``), never guessed.
ENV_IMPORTS = (
    "numpy",
    "pandas",
    "scipy",
    "populace_dynamics",
    "policyengine_us",
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


def _dry_run_module() -> Any:
    """The dry-run script, so its gaps and spec checks are the same here."""

    path = ROOT / "scripts" / "track_a_dry_run.py"
    spec = importlib.util.spec_from_file_location("_track_a_dry_run", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def check_specification_ratified(block: dict[str, Any]) -> None:
    """Refuse an A1 block whose status or version is not ratified."""

    for field in cola_age_profile.specification_unratified_fields(block):
        raise ValueError(
            f"the A1 specification {field} is {block.get(field)!r}: A1 "
            "authorizes no run until Max ratifies it by merging (plan "
            "section 6 item 4), and the ratified text must say so in its "
            "section 21 block"
        )


def preflight(
    *,
    registration_pointer: str,
    registered_commit: str,
    output: Path,
    git: Any = _git,
    specification: dict[str, Any] | None = None,
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
    check_specification_ratified(
        a1_parameter_block() if specification is None else specification
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


def distributions_for_import(
    import_name: str,
    packages: Mapping[str, Sequence[str]] | None = None,
) -> dict[str, str]:
    """The installed distributions that provide ``import_name``, by version.

    ``packages`` is ``importlib.metadata.packages_distributions()`` (passed
    in by tests).  A name the mapping lists more than once (an editable
    install whose metadata is also on the path) is recorded once.  An
    import name no installed distribution provides maps to ``{}``.
    """

    if packages is None:
        packages = importlib.metadata.packages_distributions()
    names = dict.fromkeys(packages.get(import_name, ()))
    return {name: importlib.metadata.version(name) for name in names}


def _project() -> dict[str, str]:
    """The project name and version in ``pyproject.toml`` at this commit."""

    import tomllib

    with (ROOT / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)["project"]
    return {"name": project["name"], "version": project["version"]}


def _environment(
    *,
    ssa_parameters_revision: str,
    packages: Mapping[str, Sequence[str]] | None = None,
) -> dict[str, Any]:
    """The run environment the sidecar records, with no unresolved name.

    ``packages`` maps each installed distribution name to its version;
    ``distributions_by_import`` records which distributions provide each
    of :data:`ENV_IMPORTS`.  The code the run imports is this commit's
    ``src/populace_dynamics`` (the script puts ``src`` first on the path),
    recorded as ``populace_dynamics_source`` with the project name and
    version from ``pyproject.toml``.  policyengine-us is not an installed
    distribution here: the oracle reads its parameters from a git
    checkout, whose revision is recorded.
    """

    if packages is None:
        packages = importlib.metadata.packages_distributions()
    by_import = {
        name: distributions_for_import(name, packages) for name in ENV_IMPORTS
    }
    versions: dict[str, str] = {}
    for distributions in by_import.values():
        versions.update(distributions)
    source = Path(populace_dynamics.__file__).resolve().parent
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": dict(sorted(versions.items())),
        "distributions_by_import": {
            name: sorted(distributions)
            for name, distributions in by_import.items()
        },
        "project": _project(),
        "populace_dynamics_source": (
            str(source.relative_to(ROOT))
            if source.is_relative_to(ROOT)
            else str(source)
        ),
        "policyengine_us_parameters": {
            "source": (
                "git checkout read by populace_dynamics.ss.params."
                "load_ssa_parameters (not an installed distribution)"
            ),
            "revision": ssa_parameters_revision,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--registration-pointer", required=True)
    parser.add_argument("--registered-commit", required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    state = preflight(
        registration_pointer=args.registration_pointer,
        registered_commit=args.registered_commit,
        output=args.output,
    )
    config = TrackAConfig()
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
            a3, data_provenance="registered_real", config=config
        )
    base_params = load_ssa_parameters()
    params = tr2008_ssa_parameters(
        base_params, alternative=config.tr2008_alternative
    )
    # Resolved before the run, so an environment the sidecar cannot
    # record fails before any projection and before any file is written.
    environment = _environment(
        ssa_parameters_revision=base_params.pe_us_revision
    )
    realized = load_cola_history()
    baseline = tr2008_baseline_cola(
        realized,
        first_year=config.tr2008_first_rate_year,
        last_year=config.reference_year,
        alternative=config.tr2008_alternative,
    )
    dry_run = _dry_run_module()
    # The dry run's checks, before any projection: the A1 rate path equals
    # A2's and the runtime baseline, and every row equals the A1 block.
    spec_rate_check = dry_run._spec_rate_check(baseline)
    di_rates = load_di_entitlement_rates(config.di_spec)
    first_projection_year = min(config.start_years.values()) + 1
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
        "mortality": dict(mortality.provenance),
        "psid_inputs": {
            str(wave): dict(raw.provenance) for wave, raw in raw_inputs.items()
        },
    }
    primary, *others = (cohorts[wave] for wave in config.anchor_waves)
    result = run_track_a(
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
        "checks": {"spec_rate_path": spec_rate_check},
        "gaps": dry_run.gaps_for(result),
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
                    "scripts/run_track_a_registered.py",
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
                "environment": environment,
            },
            indent=2,
        )
        + "\n",
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
