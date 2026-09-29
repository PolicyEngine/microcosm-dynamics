"""U2 registered one-shot run on the real PSID 1946-55 cohort (built).

Specification sections 14 and 20.  This is the only entry point that
would compute the U2 statistic on real data.  It is built but not
authorized: the specification is ``u2-draft-4`` (unratified; section
16a's amendments await Max's ruling) and the registries hold open and
refused routes, so its preflight refuses before any PSID file is
opened.  :func:`preflight` verifies, in order:

1. the registration pointer is an issue #42 comment URL;
2. ``--registered-commit`` is a full SHA equal to ``HEAD`` and the
   execution checkout is clean;
3. the output identity is exactly U2's artifact
   (``runs/replication_boomers2004_1946_55_v1.json``; U1's artifact and
   any other path are refused) and neither the artifact nor its
   ``.env.json`` sidecar exists (one shot);
4. the U2 specification is ratified (status and version say
   "ratified" with no draft or negating marker), awaits no decision,
   has an empty ``blocked_by``, records the threshold capture as
   captured, pins the SSI capture's SHA-256 and carries no ``TO_VERIFY``
   value anywhere;
5. its rows equal :data:`~populace_dynamics.uniform_cut_track_u2.rows.
   REGISTERED_ROWS` with the fixed U0 headline, its ``decisions`` equal
   U2's own rulings record (U1's are refused), and section 12's named
   deltas equal the code's literal strings;
6. row U1's observation plan (and so U0's) equals milestone 1's
   committed support registry, cell by cell;
7. the parameter bundle is complete (every required income year,
   2012 included), U2-pinned and, by content, the pinned captures'
   values (a relabelled or altered value refuses);
8. the pre-registration evidence exists: the committed record the
   section 20 step-4 structure pass wrote
   (:data:`~populace_dynamics.uniform_cut_track_u2.loader.
   PREREGISTRATION_EVIDENCE_PATH`), holding the SHA-256 of every PSID
   file the loader reads and the sealed ``input_frames_sha256``, under
   this checkout's pinned registries; while it is absent the run refuses;
9. the registration binding -- target, specification SHA-256, rows,
   plans, registry (map) SHA-256s, source identities, parameter pins and
   the frozen input identities (the evidence record's SHA-256, every
   PSID file's SHA-256 and the frame digest) -- hashes to the
   ``--binding-sha256`` the #42 registration quotes;
10. the independent mapping review is complete: every registry entry a
    U2 run applies is RESOLVED with no blocker (the loader's source
    preflight, which rechecks the plan), which refuses at the adjudicated
    registries.

Only then are PSID files read (:func:`populace_dynamics.
uniform_cut_track_u2.loader.load_u2_inputs` with the evidence record: it
rehashes every frozen file before parsing any record and refuses a
changed byte, a different file set or a different frame digest; section
14), and the artifact and sidecar are created exclusively.  The artifact
publishes regardless of outcome and never reads the sealed comparator.

Usage::

    python scripts/run_track_u2_registered.py \\
        --registration-pointer <issue #42 comment URL> \\
        --registered-commit <full SHA> \\
        --binding-sha256 <SHA-256 quoted by the registration> \\
        --headline-row U0 \\
        [--output runs/replication_boomers2004_1946_55_v1.json]
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
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from populace_dynamics.estimates import adjusted_poverty as ap  # noqa: E402
from populace_dynamics.estimates import cola_age_profile  # noqa: E402
from populace_dynamics.uniform_cut_track_u2 import (  # noqa: E402
    REGISTERED_HEADER,
    cohort,
    identity,
    loader,
    parameters,
    rows,
    runner,
    sources,
)

DEFAULT_OUTPUT = identity.ARTIFACT_PATH
REGISTRATION_POINTER = runner.REGISTRATION_POINTER
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


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _find(value: Any, needle: str, path: str = "") -> list[str]:
    """``path=value`` of every string under ``value`` containing
    ``needle`` (the value is named so a refusal says what is open)."""

    found: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            found += _find(item, needle, f"{path}.{key}" if path else str(key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found += _find(item, needle, f"{path}[{index}]")
    elif isinstance(value, str) and needle in value:
        found.append(f"{path}={value!r}")
    return found


def check_specification_ratified(block: Mapping[str, Any]) -> None:
    """Refuse a U2 block that is not ratified, complete and pinned."""

    identity.check_target(block.get("target_id"), "the specification")
    if block.get("specification") != identity.SPECIFICATION_ID:
        raise ValueError(
            f"the block is {block.get('specification')!r}, not U2's"
        )
    for field in cola_age_profile.specification_unratified_fields(block):
        raise ValueError(
            f"the U2 specification {field} is {block.get(field)!r}: U2 "
            "authorizes no run until it is ratified by merge (section 20 "
            "step 6)"
        )
    awaiting = _find(block, "pending")
    if awaiting:
        raise ValueError(
            f"the U2 specification still awaits decisions: {awaiting}"
        )
    if block.get("blocked_by"):
        raise ValueError(
            "the U2 specification authorizes no run while it is blocked by "
            f"{block.get('blocked_by')}"
        )
    unresolved = _find(block, "TO_VERIFY")
    if unresolved:
        raise ValueError(
            f"the U2 specification still holds TO_VERIFY values: {unresolved}"
        )
    if (block.get("threshold") or {}).get("capture_status") != "captured":
        raise ValueError("the Census threshold capture is not recorded")
    ssi = ((block.get("ssi") or {}).get("parameters") or {}).get("sha256")
    if ssi != parameters.SSI_SHA256:
        raise ValueError(
            f"the block pins SSI capture {ssi!r}, not {parameters.SSI_SHA256}"
        )
    headline = (block.get("population") or {}).get("headline") or {}
    if headline != {"rule": rows.HEADLINE_RULE, "fallback_row": None}:
        raise ValueError("the block's headline is not the fixed U0")


def registration_binding(
    specification_sha256: str, evidence: Mapping[str, Any]
) -> dict[str, Any]:
    """Everything the #42 registration binds, as one canonical record.

    ``evidence`` is the frozen pre-registration record
    (:func:`~populace_dynamics.uniform_cut_track_u2.loader.
    check_preregistration_evidence`): its SHA-256, every PSID file's
    SHA-256 and the sealed frame digest are bound (section 14 and
    section 20 step 8, "input and parameter pins").
    """

    frozen = loader.check_preregistration_evidence(evidence)
    return {
        "target": identity.identity(),
        "specification_sha256": specification_sha256,
        "rows": [row.as_dict() for row in rows.REGISTERED_ROWS.values()],
        "headline": {"row": rows.HEADLINE_ROW, "rule": rows.HEADLINE_RULE},
        "plans": {
            row: [
                list(cell)
                for cell in cohort.plan_cells(cohort.U2CohortSpec(row=row))
            ]
            for row in cohort.ROWS
        },
        "support_waves": list(sources.SUPPORT_WAVES),
        "registries_sha256": dict(sorted(sources.REGISTRY_SHA256.items())),
        "parameters": {
            "thresholds_sha256": parameters.THRESHOLDS_SHA256,
            "ssi_sha256": parameters.SSI_SHA256,
            "nchs_2000_sha256": ap.NCHS_2000_SHA256,
            "ssa_period_2004_sha256": parameters._LIFE_TABLE_PINS[
                "ssa_period_2004"
            ],
        },
        "named_deltas": list(rows.NAMED_DELTAS),
        "rulings": rows.U2_RULINGS,
        "sensitivities_unscored": {
            key: list(value)
            for key, value in rows.SENSITIVITIES_UNSCORED.items()
        },
        "preregistration_evidence": {
            "sha256": loader.preregistration_evidence_sha256(frozen),
            "psid_files_sha256": dict(frozen["psid_files_sha256"]),
            "psid_files_bundle_sha256": frozen["psid_files_bundle_sha256"],
            "input_frames_sha256": frozen["input_frames_sha256"],
        },
    }


def binding_sha256(
    specification_sha256: str, evidence: Mapping[str, Any]
) -> str:
    return hashlib.sha256(
        _canonical(registration_binding(specification_sha256, evidence))
    ).hexdigest()


def preflight(
    *,
    registration_pointer: str,
    registered_commit: str,
    output: Path,
    binding: str,
    git: Any = _git,
    specification: Mapping[str, Any] | None = None,
    specification_sha256: str | None = None,
    evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Refuse to run unless this is the registered U2 one-shot state.

    ``specification``, ``specification_sha256`` and ``evidence`` default
    to the committed specification block, its file hash and the committed
    pre-registration evidence record (tests pass invented ones).
    """

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
    identity.refuse_u1_identity({"output": output}, what="--output")
    if Path(output).resolve() != identity.ARTIFACT_PATH.resolve():
        raise ValueError(
            f"{output} is not U2's artifact {identity.ARTIFACT_PATH}"
        )
    if output.exists() or output.with_suffix(".env.json").exists():
        raise ValueError(
            f"{output} already exists: the registered run is one-shot"
        )
    block = (
        rows.specification_block()
        if specification is None
        else (specification)
    )
    check_specification_ratified(block)
    row_check = rows.check_rows_against_block(block)
    ruling_check = rows.check_u2_rulings_against_block(block)
    delta_check = rows.check_named_deltas_against_specification()
    plan_check = cohort.check_plan_against_support_registry(
        sources.RegistrySet.committed()
    )
    params = parameters.committed_u2_parameters()
    parameters.check_u2_parameters(params, ap.REGISTERED_REAL)
    spec_sha = (
        _sha256(identity.SPECIFICATION_PATH)
        if specification_sha256 is None
        else specification_sha256
    )
    frozen = (
        loader.read_preregistration_evidence()
        if evidence is None
        else loader.check_preregistration_evidence(evidence)
    )
    expected = binding_sha256(spec_sha, frozen)
    if binding != expected:
        raise ValueError(
            f"the registration binds {binding}, but this checkout's binding "
            f"is {expected}: not the registered state"
        )
    review = loader.source_preflight()
    return {
        "head": head,
        "specification_sha256": spec_sha,
        "binding_sha256": expected,
        "rows": row_check,
        "rulings": ruling_check,
        "named_deltas": delta_check,
        "plan": plan_check,
        "mapping_review": review,
        "params": params,
        "evidence": frozen,
        "evidence_sha256": loader.preregistration_evidence_sha256(frozen),
    }


def _write_new(path: Path, text: str) -> None:
    with path.open("x", encoding="utf-8") as handle:
        handle.write(text)


def _environment() -> dict[str, Any]:
    packages = importlib.metadata.packages_distributions()
    versions = {}
    for name in ENV_IMPORTS:
        for distribution in dict.fromkeys(packages.get(name, ())):
            versions[distribution] = importlib.metadata.version(distribution)
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": dict(sorted(versions.items())),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--registration-pointer", required=True)
    parser.add_argument("--registered-commit", required=True)
    parser.add_argument("--binding-sha256", required=True)
    parser.add_argument(
        "--headline-row", required=True, choices=(rows.HEADLINE_ROW,)
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    runner.check_headline(args.headline_row)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    state = preflight(
        registration_pointer=args.registration_pointer,
        registered_commit=args.registered_commit,
        output=args.output,
        binding=args.binding_sha256,
    )
    inputs = loader.load_u2_inputs(evidence=state["evidence"])
    result = runner.run_track_u2(
        inputs,
        state["params"],
        data_provenance=ap.REGISTERED_REAL,
        role_context=sources.RoleContext.from_registry(),
        registration_pointer=args.registration_pointer,
        progress=lambda message: print(message, file=sys.stderr),
        preregistration_evidence_sha256=state["evidence_sha256"],
    )
    artifact = {
        "header": REGISTERED_HEADER,
        "publishes_regardless": True,
        "comparator_seal_opened_before_commit": False,
        **result,
        "specification": {
            "path": str(identity.SPECIFICATION_PATH.relative_to(ROOT)),
            "sha256": state["specification_sha256"],
        },
        "checks": {
            "rows": state["rows"],
            "rulings": state["rulings"],
            "named_deltas": state["named_deltas"],
            "plan": state["plan"],
            "mapping_review": state["mapping_review"],
            "binding_sha256": state["binding_sha256"],
            "preregistration_evidence_sha256": state["evidence_sha256"],
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
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    _write_new(
        args.output, json.dumps(artifact, indent=2, allow_nan=False) + "\n"
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
