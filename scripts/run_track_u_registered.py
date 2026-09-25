"""Track U registered one-shot run on the real PSID age-67 cohort (U10).

This is the only entry point that computes the exercise-2 statistic (the
change in the adjusted poverty rate at 67 under a uniform 13 percent
cut) on real data.  It runs once, after the issue #42 registration
comment exists, at exactly the commit that comment registers:

* the registration pointer must be a comment on issue #42
  (``.../issues/42#issuecomment-<id>``);
* the working tree must be clean and ``HEAD`` must equal
  ``--registered-commit``;
* the U1 specification (``docs/design/boomers2004_uniform_cut_
  comparison.md``, section 15 block) must be ratified: its status and
  version must each say "ratified" without a draft, candidate or other
  negating marker (the exercise-1 test,
  ``cola_age_profile.specification_unratified_fields``); no key of the
  block may still be ``awaiting`` a decision; ``blocked_by`` must be
  empty; and the threshold capture must be recorded as captured;
* the output artifact and its sidecar must not exist yet (one shot, no
  overwrite; both are created exclusively, so a file that appears during
  the run is not overwritten either);
* the rows are :data:`populace_dynamics.uniform_cut_track_u.rows.
  REGISTERED_ROWS`, which must equal the block's rows; no flag changes
  them;
* the Census thresholds must be the committed, hash-pinned capture
  (:func:`populace_dynamics.estimates.adjusted_poverty.
  load_poverty_thresholds` refuses until it exists), checked before any
  PSID file is read;
* ``--headline-row`` must name the headline row the #42 registration
  comment states, and it must equal the row the specification's fallback
  rule gives for the staged PSID (:func:`populace_dynamics.
  uniform_cut_track_u.runner.headline_row`: U0 when the 2005 and 2007
  wealth supplements are staged, adjudicated and read, U0-F otherwise);
  a mismatch means the staging changed after registration and the run
  refuses (a new registration is needed).  Rows that need a wave without
  WEALTH1 are reported as blocked with their counts; the -F alternatives
  on U0-F's population are computed in either staging state.

The artifact publishes regardless of outcome.  It never reads the sealed
comparator; the seal is opened only after this artifact is committed.

As of this script's writing (``u1-draft-6``, 2026-09-25) the
specification is a draft and refuses a run.  Max ruled on exercise 2 on
2026-09-24 (cos decision d189): yes to Track U as exercise 2's first
score (the claim class: PSID-realized outcomes at 67, not a projection),
with the SSI rule "offset only for existing SSI recipients"; and he
downloaded the 2005 and 2007 PSID wealth supplements, which are staged
and adjudicated (``populace_dynamics.data.family_income``), so on the
staged PSID the fallback rule gives U0 as the headline.  Still open, and
named as ``awaiting`` or ``blocked_by`` in the section 15 block: the
fallback rule itself (whether U0-F and the -F alternatives stay
registered), plan decision 8 (the scorecard's "from 2004"), plan
decision 6 (the acceptance rule), the #42 registration and row U7; the
specification's section 16 also lists plan decisions 2, 4 and 7 and the
freeze defaults.  The Census thresholds are captured and pinned (cos
decision d194; ``data/external/census_poverty_thresholds_2004_2012.json``),
and the specification's threshold block records ``capture_status:
captured``.

Usage::

    python scripts/run_track_u_registered.py \\
        --registration-pointer <issue #42 comment URL> \\
        --registered-commit <full SHA> \\
        --headline-row {U0,U0-F} \\
        [--output runs/replication_boomers2004_uniform_cut_v1.json]

Writes the artifact and a ``.env.json`` sidecar next to it.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.metadata
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
from populace_dynamics.cohorts import age67  # noqa: E402
from populace_dynamics.estimates import adjusted_poverty as ap  # noqa: E402
from populace_dynamics.estimates import cola_age_profile  # noqa: E402
from populace_dynamics.uniform_cut_track_u import (  # noqa: E402
    REGISTERED_HEADER,
    rows,
    runner,
)

DEFAULT_OUTPUT = ROOT / "runs" / "replication_boomers2004_uniform_cut_v1.json"
#: A comment on issue #42, the registration issue; nothing else is a
#: registration pointer.
REGISTRATION_POINTER = runner.REGISTRATION_POINTER
#: The exercise-1 markers of an unratified status or version.
UNRATIFIED_MARKERS = cola_age_profile.UNRATIFIED_MARKERS
#: Import names whose installed distributions the sidecar records.
ENV_IMPORTS = ("numpy", "pandas", "populace_dynamics")


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _awaiting(value: Any, path: str = "") -> list[str]:
    """Every ``awaiting`` key in the block that still names a decision."""

    found: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            here = f"{path}.{key}" if path else str(key)
            if key == "awaiting" and item not in (None, "", []):
                found.append(here)
            else:
                found.extend(_awaiting(item, here))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_awaiting(item, f"{path}[{index}]"))
    return found


def check_specification_ratified(block: Mapping[str, Any]) -> None:
    """Refuse a specification block that is not ratified and complete."""

    for field in cola_age_profile.specification_unratified_fields(block):
        raise ValueError(
            f"the U1 specification {field} is {block.get(field)!r}: U1 "
            "authorizes no run until Max ratifies it by merging (plan "
            "section 10 item 7), and the ratified text must say so in its "
            "section 15 block"
        )
    pending = _awaiting(block)
    if pending:
        raise ValueError(
            "the U1 specification authorizes no run while decisions are "
            f"awaited: {pending}"
        )
    if block.get("blocked_by"):
        raise ValueError(
            "the U1 specification authorizes no run while it is blocked "
            f"by {block.get('blocked_by')}"
        )
    status = (block.get("threshold") or {}).get("capture_status")
    if status != "captured":
        raise ValueError(
            "the U1 specification authorizes no run until the Census "
            f"thresholds are captured (capture_status {status!r})"
        )


def preflight(
    *,
    registration_pointer: str,
    registered_commit: str,
    output: Path,
    git: Any = _git,
    specification: Mapping[str, Any] | None = None,
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
        rows.specification_block() if specification is None else specification
    )
    if output.exists() or output.with_suffix(".env.json").exists():
        raise ValueError(
            f"{output} already exists: the registered run is one-shot"
        )
    return {"head": head}


def check_headline(registered: str, inputs: Any) -> str:
    """Refuse unless the registered headline is the fallback rule's row."""

    staged = runner.headline_row(inputs)
    if registered != staged:
        raise ValueError(
            f"the registration names headline row {registered}, but the "
            f"staged PSID gives {staged} under the fallback rule (WEALTH1 "
            f"refused for waves {sorted(inputs.wealth_refusals)}): the "
            "staging changed after registration, so this is not the "
            "registered run"
        )
    return staged


def _write_new(path: Path, text: str) -> None:
    """Create ``path`` exclusively: never overwrite (one shot)."""

    with path.open("x", encoding="utf-8") as handle:
        handle.write(text)


def distributions_for_import(
    import_name: str,
    packages: Mapping[str, Sequence[str]] | None = None,
) -> dict[str, str]:
    """The installed distributions that provide ``import_name``, by version."""

    if packages is None:
        packages = importlib.metadata.packages_distributions()
    names = dict.fromkeys(packages.get(import_name, ()))
    return {name: importlib.metadata.version(name) for name in names}


def _environment() -> dict[str, Any]:
    import tomllib

    with (ROOT / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)["project"]
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
        "project": {"name": project["name"], "version": project["version"]},
        "populace_dynamics_source": (
            str(source.relative_to(ROOT))
            if source.is_relative_to(ROOT)
            else str(source)
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--registration-pointer", required=True)
    parser.add_argument("--registered-commit", required=True)
    parser.add_argument(
        "--headline-row",
        required=True,
        choices=(rows.PRIMARY_ROW, rows.FALLBACK_ROW),
        help="the headline row the #42 registration comment states",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    state = preflight(
        registration_pointer=args.registration_pointer,
        registered_commit=args.registered_commit,
        output=args.output,
    )
    block = rows.specification_block()
    row_check = rows.check_rows_against_block(block)
    # Refused before any PSID file is read: no pinned Census capture, no
    # run.
    thresholds = ap.load_poverty_thresholds()
    params = runner.committed_parameters(thresholds)
    environment = _environment()
    inputs = age67.load_age67_inputs()
    check_headline(args.headline_row, inputs)
    result = runner.run_track_u(
        inputs,
        params,
        data_provenance=ap.REGISTERED_REAL,
        registration_pointer=args.registration_pointer,
        progress=lambda message: print(message, file=sys.stderr),
    )
    artifact = {
        "header": REGISTERED_HEADER,
        "publishes_regardless": True,
        "comparator_seal_opened_before_commit": False,
        **result,
        "specification": {
            "path": str(rows.SPECIFICATION_PATH.relative_to(ROOT)),
            "sha256": _sha256(rows.SPECIFICATION_PATH),
            "version": block.get("version"),
            "status": block.get("status"),
        },
        "checks": {"specification_rows": row_check},
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
                    "scripts/run_track_u_registered.py",
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
