"""Track M registered one-shot run on the real PSID (DynaSim exercise 4).

Plan item M11 of ``critical-path-minimum-benefit-20260924.md``.  This will
be the only entry point that computes the Track M statistic (Table 6's 2025
concept: the share of OASDI beneficiaries aged 62 and older receiving a
minimum, options 2-5 by All, Men and Women, on income year 2022) on real
data.  It mirrors ``scripts/run_track_a_registered.py`` and runs once,
after the issue #42 registration comment exists, at exactly the commit
that comment registers:

* the registration pointer must be a comment on issue #42
  (``.../issues/42#issuecomment-<id>``);
* the working tree must be clean and ``HEAD`` must equal
  ``--registered-commit``;
* the M1 specification (``docs/design/minimum_benefits_comparison.md``)
  must be ratified: its section 19 status and version must each say
  "ratified" as a word, with no negating word and no candidate, draft,
  not-merged, not-ratified or referee marker; it may list no decision
  awaiting Max (cos decision d219), must record his ruling on every d219
  field with the configuration following each, and must equal the code
  (``min_benefit_track_m.specification.
  check_specification_for_registered_run``).  The committed draft
  (``m1-draft-1``) is refused;
* the output artifact must not exist yet (one shot, no overwrite; it is
  created exclusively, so a file that appears during the run is not
  overwritten either);
* the configuration is :class:`TrackMPolicy`'s default, which the M1
  specification freezes (rows MS0-MS6); no flag changes it.

After the preflight, the run refuses **before reading any PSID file**
while a component it needs is missing (:func:`missing_components`): the
Census threshold capture (M2), the beneficiary cohort (M3, M4), the
realized careers (M5) and the tabulation (M8).  Plan item M10 wires the
pipeline into :func:`run_pipeline`; until then that function refuses too.

The artifact publishes regardless of outcome.  It never reads the sealed
comparator; the seal is opened only after this artifact is committed.
Nothing here has been run on real data.

Usage::

    python scripts/run_track_m_registered.py \\
        --registration-pointer <issue #42 comment URL> \\
        --registered-commit <full SHA> \\
        [--output runs/replication_urban2006_minimum_benefit_v1.json]
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
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

from populace_dynamics.min_benefit_track_m import (  # noqa: E402
    OUTPUT_LABELS,
    rules,
)
from populace_dynamics.min_benefit_track_m.policy import (  # noqa: E402
    TrackMPolicy,
)
from populace_dynamics.min_benefit_track_m.specification import (  # noqa: E402
    M1_SPECIFICATION_PATH,
    check_specification_for_registered_run,
    m1_parameter_block,
)

REGISTERED_HEADER = (
    "REGISTERED ONE-SHOT RUN - Track M, DynaSim exercise 4 (minimum "
    "benefit; Table 6's 2025 share of OASDI beneficiaries 62+ receiving a "
    "minimum, options 2-5). " + "; ".join(OUTPUT_LABELS) + ". Publishes "
    "regardless of outcome."
)
DEFAULT_OUTPUT = (
    ROOT / "runs" / "replication_urban2006_minimum_benefit_v1.json"
)
#: A comment on issue #42, the registration issue; nothing else is a
#: registration pointer.
REGISTRATION_POINTER = re.compile(
    r"https://github\.com/PolicyEngine/microcosm-dynamics/issues/42"
    r"#issuecomment-[0-9]+"
)
#: Modules later plan items add; each is missing until it exists.
PIPELINE_MODULES = {
    "M3/M4 beneficiary cohort": "populace_dynamics.min_benefit_track_m.cohort",
    "M5 realized careers": "populace_dynamics.min_benefit_track_m.careers",
    "M8 tabulation": "populace_dynamics.min_benefit_track_m.tabulation",
}


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def preflight(
    *,
    registration_pointer: str,
    registered_commit: str,
    output: Path,
    git: Any = _git,
    specification: dict[str, Any] | None = None,
    policy: TrackMPolicy | None = None,
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
        m1_parameter_block() if specification is None else specification,
        policy or TrackMPolicy(),
    )
    if output.exists() or output.with_suffix(".env.json").exists():
        raise ValueError(
            f"{output} already exists: the registered run is one-shot"
        )
    return {"head": head}


def missing_components() -> list[str]:
    """The pipeline pieces that do not exist yet, by plan item."""

    missing = []
    try:
        rules.load_aged_thresholds()
    except rules.ThresholdsNotCapturedError:
        missing.append("M2 Census one-person 65+ threshold capture")
    for item, module in PIPELINE_MODULES.items():
        if importlib.util.find_spec(module) is None:
            missing.append(item)
    return missing


def check_runnable() -> None:
    """Refuse, before any PSID read, while a component is missing."""

    missing = missing_components()
    if missing:
        raise RuntimeError(
            "the Track M pipeline is not built: missing "
            + "; ".join(missing)
            + " (plan items M2-M8; M10 wires the pipeline)"
        )


def run_pipeline(policy: TrackMPolicy) -> dict[str, Any]:
    """The registered computation (plan item M10 wires it)."""

    raise NotImplementedError(
        "plan item M10 wires the cohort, careers, rules and tabulation "
        "into the registered run; nothing is computed until then"
    )


def _write_new(path: Path, text: str) -> None:
    """Create ``path`` exclusively: never overwrite (one shot)."""

    with path.open("x", encoding="utf-8") as handle:
        handle.write(text)


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
    check_runnable()
    policy = TrackMPolicy()
    result = run_pipeline(policy)
    artifact = {
        "header": REGISTERED_HEADER,
        "publishes_regardless": True,
        "comparator_seal_opened_before_commit": False,
        **result,
        "provenance": {
            "m1_specification_sha256": _sha256(M1_SPECIFICATION_PATH),
            **result.get("provenance", {}),
        },
        "run": {
            "started": started,
            "finished": datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat(),
            "registration_pointer": args.registration_pointer,
            "registered_commit": args.registered_commit,
            "git_head": state["head"],
            "git_clean": True,
            "python": platform.python_version(),
            "command": " ".join(
                [
                    "python",
                    "scripts/run_track_m_registered.py",
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
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
