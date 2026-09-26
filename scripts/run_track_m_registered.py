"""Track M registered one-shot run on the real PSID (DynaSim exercise 4).

Plan item M11 of ``critical-path-minimum-benefit-20260924.md``.  This will
be the only entry point that computes the Track M statistic (Table 6's 2025
concept: the share of OASDI beneficiaries aged 62 and older receiving a
minimum, options 2-5 by All, Men and Women, on income year 2022) on real
data.  It mirrors ``scripts/run_track_a_registered.py`` and
``scripts/run_fra68_registered.py`` and runs once, after the issue #42
registration comment exists, at exactly the commit that comment registers.

**Preflight** (:func:`preflight`, before anything is loaded):

* the registration pointer must be a comment on issue #42
  (``.../issues/42#issuecomment-<id>``);
* the working tree must be clean and ``HEAD`` must equal
  ``--registered-commit``;
* the M1 specification (``docs/design/minimum_benefits_comparison.md``)
  must authorize the run (``min_benefit_track_m.specification.
  check_specification_for_registered_run``): its section 19 status and
  version must each say "ratified" as a word, with no negating word and
  no candidate, draft, not-merged, not-ratified or referee marker; it may
  list no decision awaiting Max and no blocker (``blocked_by`` empty);
  it must record his ruling on every ruled field (cos d219, d279, d280)
  as the code records it, with the configuration following each; and it
  must equal the code, the statistic and the uncertainty included.  The
  committed draft (``m1-draft-2``) is refused;
* the output artifact and its sidecar must not exist yet (one shot, no
  overwrite; both are created exclusively, so a file that appears during
  the run is not overwritten either);
* the configuration is :class:`TrackMPolicy`'s default, which the M1
  specification freezes and Max's rulings fix (rows MS0-MS6); no flag
  changes it.

**Before any PSID file is read:**

* every pipeline component must exist (:func:`missing_components`): the
  pinned Census threshold capture (M2), the beneficiary cohort (M3, M4),
  the realized careers (M5), the tabulation (M8) and the pipeline (M10);
* the parameters must be the files the specification records
  (:func:`check_parameter_pins`): the Census capture and the committed
  quarter-of-coverage capture, each by SHA-256;
* the environment the sidecar records is resolved (Track A's resolver).

**The computation** (:func:`run_pipeline`) reads the staged PSID
through M4's cohort (``min_benefit_track_m.cohort``) and M5's careers
(``min_benefit_track_m.careers``) and hands the records, marked as built
from staged PSID files and carrying every file's SHA-256, to
``min_benefit_track_m.pipeline.run_track_m``, which refuses again, before
evaluating any record, unless the pointer is an issue #42 comment, the
committed specification authorizes the run (a supplied block cannot reach
real records), every registered row runs with the registered floor seeds,
and every threshold year the in-window records need is captured (referee
R8).  ``scripts/track_m_dry_run.py`` runs the same pipeline on INVENTED
cohorts, one of them through the same M4 and M5 code.

The artifact publishes regardless of outcome and carries the Track M
labels, the covered-earnings disclosure (d280), the PSID files' SHA-256
and M4's structural counts.  It never reads the sealed comparator; the
seal is opened only after this artifact is committed.  Nothing here has
been run on real data: the committed draft specification refuses it.

Usage::

    python scripts/run_track_m_registered.py \\
        --registration-pointer <issue #42 comment URL> \\
        --registered-commit <full SHA> \\
        [--output runs/replication_urban2006_minimum_benefit_v1.json]

Writes the artifact and a ``.env.json`` sidecar next to it.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from populace_dynamics.min_benefit_track_m import (  # noqa: E402
    COVERED_EARNINGS_DISCLOSURE,
    OUTPUT_LABELS,
    coverage,
    rules,
    tabulation,
)
from populace_dynamics.min_benefit_track_m.evaluation import (  # noqa: E402
    PSID_FILES,
    TrackMParameters,
)
from populace_dynamics.min_benefit_track_m.policy import (  # noqa: E402
    TrackMPolicy,
)
from populace_dynamics.min_benefit_track_m.specification import (  # noqa: E402
    M1_SPECIFICATION_PATH,
    check_specification_for_registered_run,
    m1_parameter_block,
)
from populace_dynamics.ss.params import load_ssa_parameters  # noqa: E402

REGISTERED_HEADER = (
    "REGISTERED ONE-SHOT RUN - Track M, DynaSim exercise 4 (minimum "
    "benefit; Table 6's 2025 share of OASDI beneficiaries 62+ receiving a "
    "minimum, options 2-5). "
    + "; ".join(OUTPUT_LABELS)
    + ". "
    + COVERED_EARNINGS_DISCLOSURE
    + ". Publishes regardless of outcome."
)
DEFAULT_OUTPUT = (
    ROOT / "runs" / "replication_urban2006_minimum_benefit_v1.json"
)
#: A comment on issue #42, the registration issue; nothing else is a
#: registration pointer.  One pattern, shared with the tabulation guard.
REGISTRATION_POINTER = tabulation.REGISTRATION_POINTER
#: The pipeline's modules by plan item; each is missing until it exists.
PIPELINE_MODULES = {
    "M3 Social Security receipt readers": (
        "populace_dynamics.data.social_security_receipt"
    ),
    "M3 next-wave labor income reader": (
        "populace_dynamics.data.prior_year_labor_income"
    ),
    "M3/M4 beneficiary cohort": "populace_dynamics.min_benefit_track_m.cohort",
    "M5 realized careers": "populace_dynamics.min_benefit_track_m.careers",
    "M8 tabulation": "populace_dynamics.min_benefit_track_m.tabulation",
    "M10 pipeline": "populace_dynamics.min_benefit_track_m.pipeline",
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
    try:
        coverage.load_qc_amounts()
    except FileNotFoundError:
        missing.append("M2 quarter-of-coverage capture")
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
            + " (plan items M2-M10)"
        )


def check_parameter_pins(
    block: Mapping[str, Any],
    *,
    quarter_of_coverage: Mapping[str, Any],
    thresholds: Mapping[str, Any],
) -> dict[str, str]:
    """Refuse parameters other than the files the specification records.

    ``quarter_of_coverage`` and ``thresholds`` are the loaders' ``source``
    records (``coverage.load_qc_amounts``, ``rules.load_aged_thresholds``).
    Each SHA-256 must equal the section 19 block's ``sources`` entry: the
    policyengine-us quarter-of-coverage file the specification read, and
    the committed Census capture.
    """

    sources = block.get("sources") or {}
    pins = {
        "quarter_of_coverage": (
            quarter_of_coverage,
            (sources.get("quarter_of_coverage_amounts") or {}).get("sha256"),
        ),
        "census_thresholds": (
            thresholds,
            (sources.get("census_thresholds") or {}).get("sha256"),
        ),
    }
    out = {}
    for name, (source, expected) in pins.items():
        if not isinstance(expected, str) or not expected:
            raise ValueError(
                f"the M1 specification records no SHA-256 for {name}"
            )
        actual = source.get("sha256")
        if actual != expected:
            raise ValueError(
                f"the {name} file has SHA-256 {actual}, not the "
                f"{expected} the M1 specification records: not the "
                "registered parameters"
            )
        out[name] = actual
    return out


def committed_parameters(
    block: Mapping[str, Any],
) -> tuple[TrackMParameters, dict[str, str]]:
    """The oracle's parameters, the QC amounts and the Census capture.

    Each file is checked against the specification's record
    (:func:`check_parameter_pins`) before any PSID file is read.
    """

    params = load_ssa_parameters()
    qc = coverage.load_qc_amounts()
    thresholds = rules.load_aged_thresholds()
    pins = check_parameter_pins(
        block, quarter_of_coverage=qc.source, thresholds=thresholds.source
    )
    return TrackMParameters(params, qc, thresholds), pins


def _environment(*, ssa_parameters_revision: str) -> dict[str, Any]:
    """The run environment the sidecar records (Track A's resolver,
    reused unchanged, as exercise 3's entry point does)."""

    return _script_module("run_track_a_registered")._environment(
        ssa_parameters_revision=ssa_parameters_revision
    )


def run_pipeline(
    parameters: TrackMParameters,
    *,
    registration_pointer: str,
    data_dir: Path | None = None,
) -> dict[str, Any]:
    """The registered computation: M4's cohort and M5's careers into
    ``min_benefit_track_m.pipeline.run_track_m``.

    Reads the staged PSID through ``cohort.load_cohort_inputs`` (recording
    every file's SHA-256), builds the cohort (M4) and its records (M5,
    marked ``psid_files`` and carrying the file hashes, with the committed
    COLA history for MS5), and calls ``run_track_m(inputs, parameters,
    data_provenance="registered_real", registration_pointer=...)``.  That
    call refuses again before evaluating any record: the committed
    specification must authorize the run (no supplied block reaches real
    records), every registered row runs with the registered floor seeds,
    and every threshold year the in-window records need must be captured
    (referee R8).  Called only by :func:`main`, after the preflight, the
    component check and the parameter pins.
    """

    from populace_dynamics.estimates.parameters import load_cola_history
    from populace_dynamics.min_benefit_track_m import (
        careers,
        cohort,
        pipeline,
    )

    inputs = cohort.load_cohort_inputs(data_dir=data_dir)
    built = cohort.build_cohort(inputs)
    cola = load_cola_history()
    records = careers.build_track_m_inputs(
        built,
        earnings=inputs.earnings,
        prior_year=inputs.prior_year_labor,
        params=parameters.params,
        cola_rates=cola,
        provenance_kind=PSID_FILES,
        source={"cola_history": dict(cola.provenance)},
    )
    result = pipeline.run_track_m(
        records,
        parameters,
        data_provenance=tabulation.REGISTERED_REAL,
        registration_pointer=registration_pointer,
    )
    result["cohort_structure"] = cohort.cohort_structure(built)
    return result


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
    block = m1_parameter_block()
    # Refused before any PSID file is read: a missing component, then
    # parameters other than the files the specification records.
    check_runnable()
    parameters, pins = committed_parameters(block)
    # Resolved before the run, so an environment the sidecar cannot record
    # fails before any PSID file is read and before any file is written.
    environment = _environment(
        ssa_parameters_revision=parameters.params.pe_us_revision
    )
    result = run_pipeline(
        parameters, registration_pointer=args.registration_pointer
    )
    artifact = {
        "header": REGISTERED_HEADER,
        "publishes_regardless": True,
        "comparator_seal_opened_before_commit": False,
        **result,
        "specification": {
            "path": str(M1_SPECIFICATION_PATH.relative_to(ROOT)),
            "sha256": _sha256(M1_SPECIFICATION_PATH),
            "version": block.get("version"),
            "status": block.get("status"),
        },
        "checks": {"parameter_pins": pins},
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
