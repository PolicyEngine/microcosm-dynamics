"""Local helpers for the labelled d1408 delayed-credit diagnostic.

Verification class: labelled diagnostic, not registered reproduction or
statutory population validation. Only the six authorized model results
are admitted. Historical code and local PSID are read without changing
registered artifacts. 42 USC 402(w)(2)(A)'s convention is explicitly
selected; positive credits before 1917 remain unsupported (402(w)(6)(A)).
"""

from __future__ import annotations

import contextlib
import dataclasses
import importlib.util
import io
import json
import os
import subprocess
import sys
import tarfile
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = ROOT / "scratch" / "d1408"
PE_ROOT = Path(
    os.environ.get("POPULACE_DYNAMICS_PE_US_DIR")
    or "~/PolicyEngine/policyengine-us"
).expanduser()
PSID_ROOT = Path(
    os.environ.get("POPULACE_DYNAMICS_PSID_DIR") or "~/PolicyEngine/psid-data"
).expanduser()
HEADER = (
    "labelled diagnostic under ruling d1408; "
    "no registered artifact rerun or replaced"
)
FORBIDDEN_NAMES = ("comparison", "comparator", "seal", "dynasim")


def safe_relative(path: str) -> bool:
    """Reject restricted path names before git reads any file bytes."""
    return not any(word in path.lower() for word in FORBIDDEN_NAMES)


def _git(repo: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True
    ).stdout


def export_history(commit: str, extra_paths=()) -> Path:
    """Copy safe historical sources and explicitly requested local inputs.

    No checkout, archive of the whole repository, or alternate git metadata
    is created. Explicit safe files are obtained with read-only git archive. Tests,
    documents, registered results and benchmarks are never bulk exported.
    """
    commit = _git(ROOT, "rev-parse", commit).decode().strip()
    target = SCRATCH / f"src-{commit}"
    paths = _git(ROOT, "ls-tree", "-r", "--name-only", commit, "src").decode()
    selected = {p for p in paths.splitlines() if safe_relative(p)}
    for item in extra_paths:
        if not safe_relative(item):
            raise ValueError("restricted historical input requested")
        selected.update(
            p
            for p in _git(ROOT, "ls-tree", "-r", "--name-only", commit, item)
            .decode()
            .splitlines()
            if safe_relative(p)
        )
    _export_files(ROOT, commit, selected, target)
    return target


def _export_files(repo, commit, selected, target):
    missing = sorted(p for p in selected if not (target / p).exists())
    if not missing:
        return
    archive = _git(repo, "archive", "--format=tar", commit, *missing)
    with tarfile.open(fileobj=io.BytesIO(archive)) as contents:
        for member in contents:
            if not member.isfile() or member.name not in selected:
                continue
            destination = target / member.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(contents.extractfile(member).read())


def export_parameters(commit: str) -> Path:
    """Copy only SSA parameter YAMLs from the pinned local PE checkout."""
    commit = _git(PE_ROOT, "rev-parse", commit).decode().strip()
    target = SCRATCH / f"parameters-{commit}"
    prefix = "policyengine_us/parameters/gov/ssa"
    paths = _git(PE_ROOT, "ls-tree", "-r", "--name-only", commit, prefix)
    selected = {
        p
        for p in paths.decode().splitlines()
        if p.endswith(".yaml") and safe_relative(p)
    }
    _export_files(PE_ROOT, commit, selected, target)
    return target


def load_pinned_parameters(commit: str):
    """Load historical parameter bytes and keep their original revision."""
    from populace_dynamics.ss.params import load_ssa_parameters

    target = export_parameters(commit)
    return dataclasses.replace(
        load_ssa_parameters(target), pe_us_revision=commit
    )


def suppressed_count(count: int) -> int | str:
    """Publish no positive count below ten unweighted people."""
    return "<10" if 0 < count < 10 else count


def aggregate_group(people, records, weights, denominator: float) -> dict:
    """Deduplicate people/records and suppress the entire small cell."""
    ids = set(people)
    n = len(ids)
    if 0 < n < 10:
        return {
            "people": "<10",
            "worker_records": "<10",
            "weight": "<10",
            "admitted_weight_share": "<10",
        }
    weight = sum(float(weights[person]) for person in sorted(ids))
    return {
        "people": n,
        "worker_records": len(set(records)),
        "weight": weight,
        "admitted_weight_share": weight / denominator if denominator else None,
    }


def flagged(months_late: int, birth_year: int) -> bool:
    """The exact region authorized by d1408, including pre-1917 refusal."""
    return (1917 <= birth_year <= 1942 and months_late > 48) or (
        birth_year < 1917 and months_late > 0
    )


@lru_cache(maxsize=1)
def statutory_reference():
    """Load the isolated #494 reference beside historical packages."""
    spec = importlib.util.spec_from_file_location(
        "d1408_statutory_reference",
        ROOT / "src/populace_dynamics/ss/statutory_delayed_credit.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextlib.contextmanager
def credit_convention(*, statutory: bool, callback=None):
    """Temporarily select a credit convention in historical benefit calls.

    Pre-1917 positive inputs retain the legacy placeholder solely to allow
    supported-subset diagnostics. They must be counted separately and never
    described as statutory amounts. The patch is restored even on failure.
    """
    from populace_dynamics.ss import benefits

    original = benefits.delayed_credit
    reference = statutory_reference()

    def replacement(months_late, birth_year, params):
        if callback is not None:
            callback(months_late, birth_year, params)
        if not statutory or birth_year < 1917 or months_late <= 0:
            return original(months_late, birth_year, params)
        return reference.oracle_delayed_credit(
            months_late,
            birth_year,
            params,
            window=reference.DelayedCreditWindow.STATUTORY,
        )

    benefits.delayed_credit = replacement
    try:
        yield
    finally:
        benefits.delayed_credit = original


def install_read_guard() -> set[str]:
    """Block restricted names and record every real PSID file opened."""
    reads: set[str] = set()

    def audit(event, args):
        if event != "open" or not isinstance(args[0], (str, bytes, Path)):
            return
        path = Path(os.fsdecode(args[0])).expanduser().absolute()
        value = str(path)
        if not safe_relative(value):
            raise PermissionError("d1408 restricted path guard")
        if "microcosm-launch-evidence" in value or "/dynasim-refs/" in value:
            raise PermissionError("d1408 evidence path guard")
        if "/.subfleet/" in value or "/claude-501/" in value:
            raise PermissionError("d1408 transcript path guard")
        if path.is_relative_to(PSID_ROOT):
            reads.add(value)

    sys.addaudithook(audit)
    return reads


def write_aggregate(path: Path, result: dict) -> None:
    """Write aggregates only inside the assigned diagnostic scratch root."""
    if not path.resolve().is_relative_to(SCRATCH.resolve()):
        raise ValueError("diagnostic output must be in scratch/d1408")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
