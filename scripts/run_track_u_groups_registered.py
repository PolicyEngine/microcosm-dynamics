#!/usr/bin/env python3
# ruff: noqa: E402
"""Registered, one-shot, post hoc, not blind Track U groups (report-only).

Do not run before a new issue #42 registration. The frozen parent is
reproduced before any group attribute is read or new cell calculated.
See uniform_cut.py for the registered post hoc conventions.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from populace_dynamics.cohorts import age67
from populace_dynamics.estimates import adjusted_poverty as ap
from populace_dynamics.group_breakdowns import (
    common,
)
from populace_dynamics.group_breakdowns import (
    uniform_cut as groups,
)
from populace_dynamics.ss import params as ss_params
from populace_dynamics.uniform_cut_track_u import rows, runner

SIDECAR_SHA256 = (
    "4041a19ada1cb4c05628cf31bf10cbfdb364bdd2d5d62455a3121143913e0ed9"
)


def check_environment(actual: dict, expected: dict) -> None:
    """Match every recorded version; record the absent SciPy pin honestly."""

    common.assert_exact_cells(
        expected["python"], actual["python"], path="Python version"
    )
    for name, version in expected["packages"].items():
        common.assert_exact_cells(
            version, actual["packages"].get(name), path=f"package {name}"
        )
    common.assert_exact_cells(
        expected["project"], actual["project"], path="project"
    )


def check_parameter_checkout() -> str:
    """Require the existing checkout's full HEAD and clean tracked files."""

    checkout = ss_params._resolve_pe_us(None)

    def git(*args):
        return subprocess.run(
            ["git", "--no-optional-locks", "-C", str(checkout), *args],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    head = git("rev-parse", "HEAD")
    if not head.startswith("a03e82e503") or len(head) != 40:
        raise common.GroupBreakdownRefusal(
            "SSA checkout must be revision a03e82e503"
        )
    if git("status", "--porcelain", "--untracked-files=no"):
        raise common.GroupBreakdownRefusal(
            "SSA parameter checkout must have clean tracked files"
        )
    return head


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--registration-pointer", required=True)
    parser.add_argument("--registered-commit", required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT
        / "runs/replication_boomers2004_uniform_cut_groups_posthoc_v1.json",
    )
    args = parser.parse_args(argv)
    state = common.preflight(
        registration_pointer=args.registration_pointer,
        registered_commit=args.registered_commit,
        output=args.output,
        root=ROOT,
    )
    committed = groups.load_committed_artifact()
    if args.registration_pointer == committed["registration_pointer"]:
        raise common.GroupBreakdownRefusal(
            "a new issue #42 registration is required"
        )
    sidecar = groups.BASE_ARTIFACT.with_suffix(".env.json")
    common.assert_sha256(sidecar, SIDECAR_SHA256)
    expected_environment = json.loads(sidecar.read_text())["environment"]
    block = rows.specification_block()
    spec = importlib.util.spec_from_file_location(
        "_track_u_parent", ROOT / "scripts/run_track_u_registered.py"
    )
    if spec is None or spec.loader is None:
        raise common.GroupBreakdownRefusal(
            "cannot load frozen Track U registration guards"
        )
    parent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parent)
    parent.check_specification_ratified(block)
    common.assert_exact_cells(
        committed["checks"]["specification_rows"],
        rows.check_rows_against_block(block),
        path="specification rows",
    )
    common.assert_exact_cells(
        committed["checks"]["max_rulings"],
        rows.check_rulings_against_block(block),
        path="Max rulings",
    )
    common.assert_sha256(
        rows.SPECIFICATION_PATH, committed["specification"]["sha256"]
    )
    # The existing parameter checkout is selected by the documented env
    # variable. No checkout is created, changed, or fetched by this script.
    full_parameter_head = check_parameter_checkout()
    ssa = ss_params.load_ssa_parameters()
    environment = common.environment(
        ssa_parameters_revision=full_parameter_head
    )
    check_environment(environment, expected_environment)
    parameters = runner.committed_parameters(ap.load_poverty_thresholds())
    inputs = age67.load_age67_inputs()
    parent.check_headline(committed["headline"]["row"], inputs)
    artifact = groups.build_uniform_cut_groups(
        inputs,
        parameters,
        committed,
        data_provenance=ap.REGISTERED_REAL,
        registration_pointer=args.registration_pointer,
        lifetime_inputs=groups.LifetimeInputs(ssa),
    )
    run = asdict(state)
    run["output_path"] = str(state.output_path.relative_to(ROOT))
    run["sidecar_path"] = str(state.sidecar_path.relative_to(ROOT))
    artifact["run"] = run
    artifact["parent_artifact"] = {
        "path": str(groups.BASE_ARTIFACT.relative_to(ROOT)),
        "sha256": groups.BASE_ARTIFACT_SHA256,
    }
    artifact["environment_reproduction"] = {
        "recorded_versions_matched": True,
        "scipy_version_recorded_by_parent": False,
        "note": (
            "parent sidecar has no SciPy pin; current resolver versions "
            "retained in sidecar"
        ),
    }
    common.write_artifact_pair(
        output=state.output_path, artifact=artifact, environment=environment
    )
    print(state.output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
