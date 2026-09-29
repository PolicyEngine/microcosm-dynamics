"""Track B B1 version 2: the reconstructed-reproduction baseline.

Decision d571 (Max, 2026-09-28): "Reconstructed baseline: new registered B1
version with exact equality on the 600 committed per-draw cells, fit
lineage, original-loop vs copy person-level equality and provenance,
labelled weaker than bit-for-bit".

Candidate 3 archived no person-level outputs or RNG signatures, so the v1
bit-for-bit rule cannot pass. v2 admits a weaker, separately labelled
result, RECONSTRUCTED_REPRODUCTION, only when all four conditions hold
exactly:

1. ``per_draw_cells``: each of the 600 committed per-draw earnings cells
   (5 seeds x 20 draws x 6 cells) equals, bit for bit, the cell computed
   from the copied loop's scored output and from the unchanged original
   loop's scored output.
2. ``fit_lineage``: the committed ``lineage`` block equals the replay
   refit's lineage plus the gate-floor binding, composed as the candidate-3
   runner composed it.
3. ``person_level_differential``: the unchanged original loop and the copy
   agree person by person. This is the existing B1 differential.
4. ``provenance``: the registered provenance records are equal, and the
   ``ssa_revision`` anchor (rule (a)) holds.

No tolerance, rounding or normalization is applied. No historical
person-level reference is read, and v2 never yields REPRODUCED. Importing
this module reads no data.
"""

from __future__ import annotations

import json
import os
import struct
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.harness.m6_cells import earnings_cells
from populace_dynamics.harness.m6_scoring import EARNINGS_CELL_NAMES
from populace_dynamics.harness.m6_scoring import (
    _cell_value as scored_cell_value,
)
from populace_dynamics.track_b import runner
from populace_dynamics.track_b.equality import (
    MISMATCH,
    _compare_signature,
    compare_replay,
)

SCHEMA_VERSION = "track_b_b1.v2"
DEFAULT_OUTPUT = Path("scratch/track_b/b1_v2")
RECONSTRUCTED_REPRODUCTION = "RECONSTRUCTED_REPRODUCTION"
ADMITTED_SCOPE = "reconstructed reproduction (weaker than bit-for-bit)"
BASELINE_KIND = "reconstructed_reproduction_v2"
CONDITIONS = (
    "per_draw_cells",
    "fit_lineage",
    "person_level_differential",
    "provenance",
)
PASS, FAIL, NOT_EVALUATED = "pass", "fail", "not_evaluated"
# Condition 1 compares the committed cells with both loops' cells.
SIDES = ("replay", "original")
# Rule (a): the artifact's external_details.ssa_revision, reproduced by the
# unchanged loader in the pinned environment rather than normalized.
REGISTERED_SSA_REVISION = "f10cca5"
# The command ss/params.py:308-317 runs, with cwd set to the pe-us root.
LOADER_REVISION_COMMAND = ("git", "log", "-1", "--format=%h")
PROVENANCE_RECORDS = (
    "provenance",
    "runtime_identity",
    "candidate3_gate_freeze",
)
RUNTIME_IDENTITY_KEYS = ("python", "numpy", "pandas", "scipy")
# Sources v2's provenance depends on beyond runner.BASELINE_SOURCES: the SSA
# loader that computes ssa_revision, and environment_block, from which the
# candidate-3 runner derived runtime_identity. Both must be byte-identical
# to BASELINE_COMMIT.
RECONSTRUCTED_SOURCES = (
    "src/populace_dynamics/ss/params.py",
    "src/populace_dynamics/contract.py",
)


class ClaimRefused(ValueError):
    """A v2 claim the guard could not re-derive from the published evidence."""

    def __init__(
        self, message: str, rederived: Mapping[str, Any] | None = None
    ) -> None:
        super().__init__(message)
        self.rederived = rederived


# ---------------------------------------------------------------------------
# Condition 1: the 600 committed per-draw cells
# ---------------------------------------------------------------------------
def registered_cells(
    baseline: Any, *, seeds: Sequence[int], draws: Sequence[int]
) -> tuple[dict[tuple[int, int, str], Any], list[dict[str, Any]]]:
    """Committed per-draw earnings cells keyed by ``(seed, draw, cell)``.

    ``per_draw_rate`` is positional over the registered draw list, the
    artifact's ``protocol.draw_index``, which ``runner.execute`` requires to
    equal ``REGISTERED_DRAWS``. The order of per-seed rows and of cell
    entries is immaterial. Duplicate, missing, extra or mistyped seeds and
    rate lists of the wrong length fail closed.
    """
    cells: dict[tuple[int, int, str], Any] = {}
    problems: list[dict[str, Any]] = []
    family = (
        baseline.get("family_a") if isinstance(baseline, Mapping) else None
    )
    rows = family.get("per_seed") if isinstance(family, Mapping) else None
    if not isinstance(rows, list):
        problems.append({"kind": "missing_registered_cells"})
        return cells, problems
    registered_seeds, seen = set(seeds), set()
    for position, row in enumerate(rows):
        seed = row.get("seed") if isinstance(row, Mapping) else None
        if type(seed) is not int:
            problems.append(
                {"kind": "registered_seed_type", "row_position": position}
            )
            continue
        if seed in seen:
            problems.append(
                {"kind": "duplicate_registered_seed", "seed": seed}
            )
            continue
        seen.add(seed)
        if seed not in registered_seeds:
            problems.append({"kind": "extra_registered_seed", "seed": seed})
            continue
        gated = row.get("gated_cells")
        if not isinstance(gated, Mapping):
            problems.append({"kind": "missing_gated_cells", "seed": seed})
            continue
        for cell in EARNINGS_CELL_NAMES:
            record = gated.get(cell)
            rates = (
                record.get("per_draw_rate")
                if isinstance(record, Mapping)
                else None
            )
            if not isinstance(rates, list) or len(rates) != len(draws):
                problems.append(
                    {
                        "kind": "registered_rate_length",
                        "seed": seed,
                        "cell": cell,
                        "length": (
                            len(rates) if isinstance(rates, list) else None
                        ),
                        "expected_length": len(draws),
                    }
                )
                continue
            for draw, value in zip(draws, rates, strict=True):
                cells[seed, draw, cell] = value
    for seed in seeds:
        if seed not in seen:
            problems.append({"kind": "missing_registered_seed", "seed": seed})
    return cells, problems


def _float_bits(value: float) -> str:
    return struct.pack(">d", value).hex()


def _cell_token(value: Any) -> dict[str, Any]:
    """An exact, JSON-safe description of one cell value."""
    if type(value) is float:
        return {"float64_hex": _float_bits(value), "repr": repr(value)}
    return {"type": type(value).__name__, "repr": repr(value)}


def compare_cells(
    registered: Mapping[tuple[int, int, str], Any],
    observed: Mapping[str, Mapping[tuple[int, int, str], Any]],
    *,
    seeds: Sequence[int],
    draws: Sequence[int],
    problems: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Condition 1: every registered cell equals both sides, bit for bit.

    Values must be Python floats on both sides with identical IEEE-754 bits,
    so signed zeros and NaN payloads are material and ``1`` never equals
    ``1.0``. Comparison is keyed by ``(seed, draw, cell)``, so the order in
    which cells are supplied is immaterial; diagnostics follow the fixed
    registered order. Missing and extra cells fail closed.
    """
    differences = [dict(problem) for problem in problems]
    coverage = [
        (seed, draw, cell)
        for seed in seeds
        for draw in draws
        for cell in EARNINGS_CELL_NAMES
    ]
    covered = set(coverage)
    for side in sorted(set(observed) - set(SIDES), key=repr):
        differences.append({"kind": "unregistered_side", "side": repr(side)})
    for key in coverage:
        seed, draw, cell = key
        where = {"seed": seed, "draw": draw, "cell": cell}
        expected = registered.get(key)
        expected_ok = key in registered and type(expected) is float
        if key not in registered:
            differences.append({"kind": "missing_registered_cell", **where})
        elif not expected_ok:
            differences.append(
                {
                    "kind": "registered_cell_type",
                    **where,
                    "expected": _cell_token(expected),
                }
            )
        for side in SIDES:
            values = observed.get(side, {})
            if key not in values:
                differences.append(
                    {"kind": "missing_observed_cell", "side": side, **where}
                )
                continue
            actual = values[key]
            if type(actual) is not float:
                differences.append(
                    {
                        "kind": "observed_cell_type",
                        "side": side,
                        **where,
                        "actual": _cell_token(actual),
                    }
                )
            elif expected_ok and _float_bits(expected) != _float_bits(actual):
                differences.append(
                    {
                        "kind": "value",
                        "side": side,
                        **where,
                        "expected": _cell_token(expected),
                        "actual": _cell_token(actual),
                    }
                )
    for key in sorted(set(registered) - covered, key=repr):
        differences.append({"kind": "extra_registered_cell", "key": repr(key)})
    for side in SIDES:
        for key in sorted(set(observed.get(side, {})) - covered, key=repr):
            differences.append(
                {"kind": "extra_observed_cell", "side": side, "key": repr(key)}
            )
    return {
        "status": FAIL if differences else PASS,
        "equal": not differences,
        "compared_cells": len(coverage),
        "sides": list(SIDES),
        "differences": differences,
    }


def observed_cells(scored: pd.DataFrame) -> dict[str, Any]:
    """The six gated earnings cells of one scored surface.

    ``m6_scoring._cell_value`` is the conversion that produced every
    committed ``per_draw_rate`` (m6_scoring.py:588-596, :651-658): float of
    the value when finite, else None. The scorer also records None for a
    non-positive log-ratio draw (:653-654). Every committed value is a
    float, which ``compare_cells`` checks by type, so a non-positive replay
    value mismatches under either rule.
    """
    cells = earnings_cells(scored)
    return {
        name: scored_cell_value(cells[name]) for name in EARNINGS_CELL_NAMES
    }


def _decode_cell(encoded: Any) -> Any:
    """Invert ``runner._scalar`` for a cell; anything else stays as found."""
    if (
        isinstance(encoded, Mapping)
        and set(encoded) == {"float64_hex"}
        and isinstance(encoded["float64_hex"], str)
    ):
        try:
            bits = bytes.fromhex(encoded["float64_hex"])
        except ValueError:
            return dict(encoded)
        if len(bits) == 8:
            return float(np.frombuffer(bits, dtype=np.float64)[0])
    return dict(encoded) if isinstance(encoded, Mapping) else encoded


# ---------------------------------------------------------------------------
# Condition 2: the committed fit lineage
# ---------------------------------------------------------------------------
def compare_lineage(expected: Any, actual: Any) -> dict[str, Any]:
    """Condition 2: the committed lineage equals the replay's, exactly.

    Every field is compared: the refit lineage the candidate-3 runner
    published and the floor binding it added (m6_candidate3_runner.py
    :2488-2492). Keys match by exact type and values by type and bits.
    """
    differences: list[dict[str, Any]] = []
    if not isinstance(expected, Mapping) or not expected:
        differences.append({"kind": "missing_registered_lineage"})
    if not isinstance(actual, Mapping) or not actual:
        differences.append({"kind": "missing_replay_lineage"})
    if not differences:
        _compare_signature(expected, actual, ["lineage"], differences)
        if not differences and _canonical(expected) != _canonical(actual):
            differences.append(
                {"kind": "canonical_bytes", "path": ["lineage"]}
            )
    return {
        "status": FAIL if differences else PASS,
        "equal": not differences,
        "expected": expected,
        "actual": actual,
        "differences": differences,
    }


def _canonical(value: Any) -> bytes | None:
    try:
        return runner.json_bytes(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Condition 3: original loop against the copy, person by person
# ---------------------------------------------------------------------------
def differential_condition(differential: Mapping[str, Any]) -> dict[str, Any]:
    """Condition 3 from the in-memory differential (``compare_replay``).

    Its status is recast as pass or fail so that no v2 record carries the
    string REPRODUCED.
    """
    equal = differential.get("equal") is True
    return {
        "status": PASS if equal else FAIL,
        "equal": equal,
        "verification_class": "differential_test",
        "registered_seeds": list(differential.get("registered_seeds", [])),
        "registered_draws": list(differential.get("registered_draws", [])),
        "differences": list(differential.get("differences", [])),
        "comparisons": list(differential.get("comparisons", [])),
    }


def _null_token(value: Any) -> bool:
    if value is None or value == {"missing": "pd.NA"}:
        return True
    decoded = _decode_cell(value)
    return type(decoded) is float and decoded != decoded


def compare_frame_payloads(
    expected: Any,
    actual: Any,
    *,
    keys: Sequence[str] = ("person_id", "period"),
) -> list[dict[str, Any]]:
    """Keyed, exact comparison of two ``runner.frame_payload`` records.

    This is the guard's second implementation of the person-level check.
    It reads the published evidence without rebuilding DataFrames: columns
    match by name and dtype string, rows by their typed key values, and
    cells by their exact JSON encoding (float bits included). Row and column
    order are immaterial, as in ``equality.compare_frames``; empty, ragged,
    duplicate-keyed and null-keyed frames fail closed.
    """
    differences: list[dict[str, Any]] = []
    tables: dict[str, tuple[dict[str, tuple[str, list]], int]] = {}
    for side, payload in (("expected", expected), ("actual", actual)):
        columns = (
            payload.get("columns") if isinstance(payload, Mapping) else None
        )
        if not isinstance(columns, list):
            differences.append({"kind": "missing_frame", "side": side})
            continue
        table: dict[str, tuple[str, list]] = {}
        lengths = set()
        for position, column in enumerate(columns):
            name = column.get("name") if isinstance(column, Mapping) else None
            dtype = (
                column.get("dtype") if isinstance(column, Mapping) else None
            )
            values = (
                column.get("values") if isinstance(column, Mapping) else None
            )
            if not (
                isinstance(name, str)
                and isinstance(dtype, str)
                and isinstance(values, list)
            ):
                differences.append(
                    {
                        "kind": "malformed_column",
                        "side": side,
                        "position": position,
                    }
                )
                continue
            if name in table:
                differences.append(
                    {"kind": "duplicate_columns", "side": side, "column": name}
                )
                continue
            table[name] = (dtype, values)
            lengths.add(len(values))
        if len(lengths) > 1:
            differences.append({"kind": "ragged_frame", "side": side})
        rows = next(iter(lengths)) if len(lengths) == 1 else 0
        if rows == 0:
            differences.append({"kind": "empty_frame", "side": side})
        missing = sorted(set(keys) - set(table))
        if missing:
            differences.append(
                {"kind": "missing_keys", "side": side, "columns": missing}
            )
        tables[side] = (table, rows)
    if differences:
        return differences
    (left, left_rows), (right, right_rows) = (
        tables["expected"],
        tables["actual"],
    )
    for column in sorted(set(left) - set(right)):
        differences.append({"kind": "missing_column", "column": column})
    for column in sorted(set(right) - set(left)):
        differences.append({"kind": "extra_column", "column": column})
    shared = sorted(set(left) & set(right))
    for column in shared:
        if left[column][0] != right[column][0]:
            differences.append(
                {
                    "kind": "dtype",
                    "column": column,
                    "expected": left[column][0],
                    "actual": right[column][0],
                }
            )
    lookups: dict[str, dict[tuple[str, ...], int]] = {}
    for side, table, rows in (
        ("expected", left, left_rows),
        ("actual", right, right_rows),
    ):
        lookup: dict[tuple[str, ...], int] = {}
        lookups[side] = lookup
        for index in range(rows):
            values = [table[key][1][index] for key in keys]
            if any(_null_token(value) for value in values):
                differences.append(
                    {"kind": "null_key", "side": side, "row_position": index}
                )
                continue
            token = tuple(
                json.dumps(value, sort_keys=True) for value in values
            )
            if token in lookup:
                differences.append(
                    {
                        "kind": "duplicate_key",
                        "side": side,
                        "key": list(token),
                        "row_positions": [lookup[token], index],
                    }
                )
            else:
                lookup[token] = index
    for token in sorted(set(lookups["expected"]) | set(lookups["actual"])):
        if token not in lookups["actual"]:
            differences.append({"kind": "missing_row", "key": list(token)})
            continue
        if token not in lookups["expected"]:
            differences.append({"kind": "extra_row", "key": list(token)})
            continue
        for column in shared:
            expected_value = left[column][1][lookups["expected"][token]]
            actual_value = right[column][1][lookups["actual"][token]]
            if json.dumps(expected_value, sort_keys=True) != json.dumps(
                actual_value, sort_keys=True
            ):
                differences.append(
                    {
                        "kind": "value",
                        "key": list(token),
                        "column": column,
                        "expected": expected_value,
                        "actual": actual_value,
                    }
                )
    return differences


def _nonempty_signature(value: Any) -> bool:
    return isinstance(value, Mapping) and len(value) > 0


def compare_evidence_differential(
    payloads: Mapping[tuple[int, int], Mapping[str, Any]],
    *,
    seeds: Sequence[int],
    draws: Sequence[int],
    problems: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Condition 3 re-derived from the hash-verified evidence files."""
    differences = [dict(problem) for problem in problems]
    for seed in seeds:
        for draw in draws:
            where = {"seed": seed, "draw": draw}
            payload = payloads.get((seed, draw))
            if payload is None:
                differences.append({"kind": "missing_evidence", **where})
                continue
            differences.extend(
                {**where, "field": "scored", **item}
                for item in compare_frame_payloads(
                    payload.get("original_scored"),
                    payload.get("replay_scored"),
                )
            )
            for field in ("fit_signature", "rng_signature"):
                left = payload.get(f"original_{field}")
                right = payload.get(f"replay_{field}")
                if not (
                    _nonempty_signature(left) and _nonempty_signature(right)
                ):
                    differences.append(
                        {"kind": "missing_signature", **where, "field": field}
                    )
                    continue
                current: list[dict[str, Any]] = []
                _compare_signature(left, right, [field], current)
                differences.extend({**where, **item} for item in current)
    return {
        "status": FAIL if differences else PASS,
        "equal": not differences,
        "verification_class": "differential_test",
        "compared_seed_draws": len(seeds) * len(draws),
        "differences": differences,
    }


# ---------------------------------------------------------------------------
# Condition 4: provenance and the ssa_revision anchor
# ---------------------------------------------------------------------------
def registered_provenance(baseline: Any, sidecar: Any) -> dict[str, Any]:
    """The registered provenance records v2 compares, all fields each.

    ``provenance`` and ``runtime_identity`` are the artifact's top-level
    records; ``candidate3_gate_freeze`` is the pinned-environment record in
    the hash-pinned environment sidecar.
    """
    environment = (
        sidecar.get("environment") if isinstance(sidecar, Mapping) else None
    )
    return {
        "provenance": (
            baseline.get("provenance")
            if isinstance(baseline, Mapping)
            else None
        ),
        "runtime_identity": (
            baseline.get("runtime_identity")
            if isinstance(baseline, Mapping)
            else None
        ),
        "candidate3_gate_freeze": (
            environment.get("candidate3_gate_freeze")
            if isinstance(environment, Mapping)
            else None
        ),
    }


def anchor_problems(
    anchor: Any, registered: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Rule (a): the unchanged loader must itself report ``f10cca5``.

    The registered artifact must record ``REGISTERED_SSA_REVISION``. The
    probe must report that same abbreviation from a checkout whose full
    HEAD is ``BASELINE_COMMIT``, whose tracked files are clean, and with no
    GIT_* variable able to redirect repository discovery.
    """
    problems: list[dict[str, Any]] = []
    provenance = registered.get("provenance")
    details = (
        provenance.get("external_details")
        if isinstance(provenance, Mapping)
        else None
    )
    recorded = (
        details.get("ssa_revision") if isinstance(details, Mapping) else None
    )
    if recorded != REGISTERED_SSA_REVISION:
        problems.append(
            {
                "kind": "registered_ssa_revision",
                "expected": REGISTERED_SSA_REVISION,
                "actual": recorded,
            }
        )
    if not isinstance(anchor, Mapping):
        problems.append({"kind": "missing_ssa_revision_anchor"})
        return problems
    required = (
        ("loader_revision", REGISTERED_SSA_REVISION),
        ("head", runner.BASELINE_COMMIT),
        ("tracked_clean", True),
        ("git_environment", {}),
    )
    for field, wanted in required:
        found = anchor.get(field)
        if type(found) is not type(wanted) or found != wanted:
            problems.append(
                {
                    "kind": "ssa_revision_anchor",
                    "path": ["ssa_revision_anchor", field],
                    "expected": wanted,
                    "actual": found,
                }
            )
    return problems


def compare_provenance(
    expected: Mapping[str, Any], actual: Any, anchor: Any
) -> dict[str, Any]:
    """Condition 4: every registered provenance field, plus the anchor."""
    differences: list[dict[str, Any]] = []
    for name in PROVENANCE_RECORDS:
        left = expected.get(name)
        right = actual.get(name) if isinstance(actual, Mapping) else None
        if not isinstance(left, Mapping) or not left:
            differences.append(
                {"kind": "missing_registered_record", "record": name}
            )
        elif not isinstance(right, Mapping) or not right:
            differences.append(
                {"kind": "missing_replay_record", "record": name}
            )
        else:
            _compare_signature(left, right, [name], differences)
    if isinstance(actual, Mapping):
        for name in sorted(set(actual) - set(PROVENANCE_RECORDS), key=repr):
            differences.append(
                {"kind": "unregistered_record", "record": repr(name)}
            )
    differences.extend(anchor_problems(anchor, expected))
    return {
        "status": FAIL if differences else PASS,
        "equal": not differences,
        "expected": dict(expected),
        "actual": actual,
        "ssa_revision_anchor": anchor,
        "differences": differences,
    }


def _git_or_none(root: Path, *arguments: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=root,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    return completed.stdout.strip() if completed.returncode == 0 else None


def _tracked_clean(root: Path) -> bool | None:
    codes = []
    for arguments in (("diff", "--quiet"), ("diff", "--cached", "--quiet")):
        try:
            codes.append(
                subprocess.run(
                    ["git", *arguments], cwd=root, capture_output=True
                ).returncode
            )
        except OSError:
            return None
    if all(code == 0 for code in codes):
        return True
    return False if all(code in (0, 1) for code in codes) else None


def ssa_revision_anchor(pe_us_dir: Path | None = None) -> dict[str, Any]:
    """Probe the ``ssa_revision`` the unchanged loader will record.

    ``load_ssa_parameters`` resolves its root with ``_resolve_pe_us``
    (ss/params.py:187-192, :218) and records ``git log -1 --format=%h`` run
    there (:308-317), falling back to "unknown"; m6_inputs.py:391 and :417
    copy it into ``external_details.ssa_revision``. This probe runs the same
    command in the same directory with the same inherited environment,
    before any data access. It adds the full HEAD of the repository git
    discovers there, whether its tracked files are clean, its
    ``core.abbrev`` setting and any GIT_* variables.
    """
    from populace_dynamics.ss.params import _resolve_pe_us

    root = _resolve_pe_us(pe_us_dir)
    record: dict[str, Any] = {
        "pe_us_root": str(root),
        "command": list(LOADER_REVISION_COMMAND),
        "git_environment": {
            key: value
            for key, value in sorted(os.environ.items())
            if key.startswith("GIT_")
        },
    }
    try:
        revision = subprocess.run(
            list(LOADER_REVISION_COMMAND),
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        revision = "unknown"
    record["loader_revision"] = revision
    record["head"] = _git_or_none(root, "rev-parse", "HEAD")
    record["toplevel"] = _git_or_none(root, "rev-parse", "--show-toplevel")
    record["core_abbrev"] = _git_or_none(
        root, "config", "--get", "core.abbrev"
    )
    record["tracked_clean"] = _tracked_clean(root)
    return record


def runtime_identity() -> dict[str, str]:
    """The live runtime identity, derived as the candidate-3 runner did.

    m6_candidate3_runner.py:1225-1228 takes these four keys, as strings,
    from ``contract.environment_block()`` (contract.py:186-202).
    """
    from populace_dynamics.contract import environment_block

    environment = environment_block()
    return {key: str(environment[key]) for key in RUNTIME_IDENTITY_KEYS}


# ---------------------------------------------------------------------------
# Admission
# ---------------------------------------------------------------------------
def admission(conditions: Any) -> dict[str, Any]:
    """The v2 status: RECONSTRUCTED_REPRODUCTION only if all four pass.

    A condition passes only when its record says ``status == "pass"``,
    ``equal is True`` and has no differences. Missing records count as not
    evaluated; unregistered condition names fail closed.
    """
    records = conditions if isinstance(conditions, Mapping) else {}
    statuses = {}
    for name in CONDITIONS:
        record = records.get(name)
        if not isinstance(record, Mapping):
            statuses[name] = NOT_EVALUATED
        elif (
            record.get("status") == PASS
            and record.get("equal") is True
            and not record.get("differences")
        ):
            statuses[name] = PASS
        elif record.get("status") == NOT_EVALUATED:
            statuses[name] = NOT_EVALUATED
        else:
            statuses[name] = FAIL
    unregistered = sorted(
        repr(name) for name in records if name not in CONDITIONS
    )
    passed = not unregistered and all(
        status == PASS for status in statuses.values()
    )
    return {
        "status": RECONSTRUCTED_REPRODUCTION if passed else MISMATCH,
        "equal": passed,
        "admitted_scope": ADMITTED_SCOPE if passed else "none",
        "condition_status": statuses,
        "failed_conditions": [
            name for name in CONDITIONS if statuses[name] == FAIL
        ],
        "not_evaluated_conditions": [
            name for name in CONDITIONS if statuses[name] == NOT_EVALUATED
        ],
        "unregistered_conditions": unregistered,
    }


def _v2_result(conditions: Mapping[str, Any], files: list) -> dict[str, Any]:
    return {
        **admission(conditions),
        "verification_class": "reproduction",
        "baseline_kind": BASELINE_KIND,
        "historical_person_level_reference_used": False,
        "conditions": dict(conditions),
        "files": files,
    }


def run_reconstructed(
    *,
    populations: Mapping[int, Any],
    generator: Any,
    baseline: Mapping[str, Any],
    sidecar: Mapping[str, Any],
    output: Path,
    actual_lineage: Mapping[str, Any],
    actual_provenance: Mapping[str, Any],
    anchor: Mapping[str, Any],
    seeds: Sequence[int] | None = None,
    draws: Sequence[int] | None = None,
) -> dict[str, Any]:
    """Evaluate the four v2 conditions on supplied inputs.

    This seam accepts invented populations. Production passes the registered
    seeds and draws (the default), the replay's refit lineage and live
    provenance, and the anchor probed before any data access. Each seed and
    draw writes one evidence file: the v1 fields plus both sides' cells.
    """
    seeds = tuple(runner.REGISTERED_SEEDS if seeds is None else seeds)
    draws = tuple(runner.REGISTERED_DRAWS if draws is None else draws)
    replay_fit = runner._fit_lineage_signature(actual_lineage)
    original_fit = runner._fit_lineage_signature(baseline["lineage"])
    expected, observed, files = {}, {}, []
    cells: dict[str, dict[tuple[int, int, str], Any]] = {
        side: {} for side in SIDES
    }
    for seed in seeds:
        population = populations[seed]
        for draw in draws:
            original, replay, copied = runner._replay_pair(
                population, generator, draw
            )
            original_rng = runner._original_rng_signature(population, draw)
            expected[seed, draw] = dict(
                scored=original,
                fit_signature=original_fit,
                rng_signature=original_rng,
            )
            observed[seed, draw] = dict(
                scored=copied,
                fit_signature=replay_fit,
                rng_signature=replay.rng_signature,
            )
            per_side = {
                "replay": observed_cells(copied),
                "original": observed_cells(original),
            }
            for side, values in per_side.items():
                for cell, value in values.items():
                    cells[side][seed, draw, cell] = value
            payload = runner._evidence_payload(
                seed=seed,
                draw=draw,
                replay=replay,
                original=original,
                copied=copied,
                original_fit=original_fit,
                replay_fit=replay_fit,
                original_rng=original_rng,
            )
            for side, values in per_side.items():
                payload[f"{side}_cells"] = {
                    cell: runner._scalar(value)
                    for cell, value in values.items()
                }
            name = f"seed_{seed}_draw_{draw}.json"
            files.append(
                {
                    "path": name,
                    "sha256": runner._write_new(output / name, payload),
                }
            )
    registered, problems = registered_cells(baseline, seeds=seeds, draws=draws)
    differential = compare_replay(
        expected, observed, registered_seeds=seeds, registered_draws=draws
    )
    conditions = {
        "per_draw_cells": compare_cells(
            registered, cells, seeds=seeds, draws=draws, problems=problems
        ),
        "fit_lineage": compare_lineage(
            baseline.get("lineage"), actual_lineage
        ),
        "person_level_differential": differential_condition(differential),
        "provenance": compare_provenance(
            registered_provenance(baseline, sidecar), actual_provenance, anchor
        ),
    }
    return _v2_result(conditions, files)


def preflight_mismatch(
    anchor: Mapping[str, Any], registered: Mapping[str, Any]
) -> dict[str, Any]:
    """Record an anchor failure found before any data access.

    Condition 4 fails and conditions 1-3 are not evaluated: nothing is read,
    fitted or replayed once the unchanged loader is known to record another
    ``ssa_revision``.
    """
    conditions: dict[str, Any] = {}
    for name in CONDITIONS:
        if name == "provenance":
            conditions[name] = {
                "status": FAIL,
                "equal": False,
                "expected": dict(registered),
                "actual": None,
                "ssa_revision_anchor": anchor,
                "differences": anchor_problems(anchor, registered),
            }
        else:
            conditions[name] = {
                "status": NOT_EVALUATED,
                "equal": False,
                "reason": (
                    "not evaluated: the ssa_revision anchor failed before "
                    "any data access"
                ),
            }
    return _v2_result(conditions, [])


def production_reconstructed(
    root: Path, output: Path, baseline: dict
) -> dict[str, Any]:
    """Lazy registered-input path; never called by invented-data tests.

    Order: the frozen candidate-3 environment check, then the ssa_revision
    anchor, both before the input factory is imported or any PSID is read.
    """
    from populace_dynamics.harness import m6_candidate3_runner as candidate

    environment = candidate._frozen_gate_environment()
    sidecar = json.loads((root / runner.SIDECAR_PATH).read_text())
    registered = registered_provenance(baseline, sidecar)
    anchor = ssa_revision_anchor()
    if anchor_problems(anchor, registered):
        result = preflight_mismatch(anchor, registered)
        result["frozen_candidate3_environment"] = environment
        return result

    import registered_m6_candidate3_inputs

    from populace_dynamics.harness.m6_population import (
        subset_realized_population,
    )
    from populace_dynamics.harness.m6_runner import materialize_m6_refit_phase
    from populace_dynamics.harness.m6_scoring import side_a_person_ids

    plan = registered_m6_candidate3_inputs.build_input_plan()
    if not isinstance(plan, candidate.M6Candidate3InputPlan):
        raise TypeError(
            "registered factory did not return candidate-3 input plan"
        )
    bundle = candidate._fit_candidate3(plan.fit_inputs)
    fit_preflight = candidate._preflight_candidate3_first_marriage(bundle)
    inputs = plan.load_full_inputs()
    if inputs.refit_inputs is not plan.fit_inputs:
        raise ValueError("input plan replaced the preflighted fit inputs")
    phase = materialize_m6_refit_phase(inputs, bundle)
    # The floor binding exactly as the candidate-3 runner resolved it, from
    # gates.yaml at the inherited commit (m6_candidate3_runner.py:774-798).
    resolved = candidate._resolve_pinned_contract(
        root,
        runner.BASELINE_COMMIT,
        candidate._live_gate_document(root, runner.BASELINE_COMMIT),
    )
    actual_lineage = runner._json_canonical(
        {
            **dict(phase.lineage),
            "floor_run": resolved.floor_path,
            "floor_sha256": resolved.floor_sha256,
        }
    )
    actual_provenance = {
        # The artifact writer's own conversion (m6_candidate3_runner.py:2379).
        "provenance": runner._json_canonical(
            candidate._plain_provenance(getattr(inputs, "provenance", {}))
        ),
        "runtime_identity": runtime_identity(),
        "candidate3_gate_freeze": runner._json_canonical(environment),
    }
    populations = {
        seed: subset_realized_population(
            phase.population,
            side_a_person_ids(
                phase.population.anchor, split_unit="person", seed=seed
            ),
        )
        for seed in runner.REGISTERED_SEEDS
    }
    result = run_reconstructed(
        populations=populations,
        generator=bundle.earnings.generator,
        baseline=baseline,
        sidecar=sidecar,
        output=output,
        actual_lineage=actual_lineage,
        actual_provenance=actual_provenance,
        anchor=anchor,
    )
    result["fit_preflight"] = fit_preflight
    result["frozen_candidate3_environment"] = environment
    return result


# ---------------------------------------------------------------------------
# The no-reference guard for v2
# ---------------------------------------------------------------------------
def evidence_payloads(
    result: Mapping[str, Any],
    destination: Path,
    *,
    seeds: Sequence[int],
    draws: Sequence[int],
) -> tuple[dict[tuple[int, int], dict[str, Any]], list[dict[str, Any]]]:
    """The published evidence files, each re-hashed against the result."""
    problems: list[dict[str, Any]] = []
    listed = result.get("files")
    if not isinstance(listed, list):
        return {}, [{"kind": "missing_evidence_list"}]
    registered = {
        f"seed_{seed}_draw_{draw}.json": (seed, draw)
        for seed in seeds
        for draw in draws
    }
    payloads: dict[tuple[int, int], dict[str, Any]] = {}
    listed_names = set()
    for entry in listed:
        path = entry.get("path") if isinstance(entry, Mapping) else None
        digest = entry.get("sha256") if isinstance(entry, Mapping) else None
        if path not in registered:
            problems.append(
                {"kind": "unregistered_evidence_file", "path": path}
            )
            continue
        if path in listed_names:
            problems.append({"kind": "duplicate_evidence_file", "path": path})
            continue
        listed_names.add(path)
        try:
            payload_bytes = (destination / path).read_bytes()
        except OSError:
            problems.append({"kind": "missing_evidence_file", "path": path})
            continue
        if runner.sha256(payload_bytes) != digest:
            problems.append({"kind": "evidence_sha256", "path": path})
            continue
        payload = json.loads(payload_bytes)
        seed, draw = registered[path]
        if not (
            isinstance(payload, Mapping)
            and type(payload.get("seed")) is int
            and type(payload.get("draw")) is int
            and (payload["seed"], payload["draw"]) == (seed, draw)
        ):
            problems.append({"kind": "evidence_identity", "path": path})
            continue
        payloads[seed, draw] = payload
    for path in sorted(set(registered) - listed_names):
        problems.append({"kind": "unlisted_registered_evidence", "path": path})
    on_disk = {path.name for path in destination.glob("seed_*_draw_*.json")}
    for path in sorted(on_disk - listed_names):
        problems.append({"kind": "unlisted_evidence_file", "path": path})
    return payloads, problems


def rederive_conditions(
    result: Mapping[str, Any],
    *,
    baseline: Mapping[str, Any],
    sidecar: Mapping[str, Any],
    destination: Path,
    seeds: Sequence[int],
    draws: Sequence[int],
) -> dict[str, Any]:
    """Re-derive all four conditions without trusting the reported verdicts.

    Cells and person-level rows come from the hash-verified evidence files.
    The lineage and provenance actuals come from the result and are compared
    with the registered records that ``execute`` loaded itself. The anchor
    is probed again now and must equal the one the run reported.
    """
    payloads, problems = evidence_payloads(
        result, destination, seeds=seeds, draws=draws
    )
    cells: dict[str, dict[tuple[int, int, str], Any]] = {
        side: {} for side in SIDES
    }
    cell_problems = list(problems)
    for (seed, draw), payload in sorted(payloads.items()):
        for side in SIDES:
            encoded = payload.get(f"{side}_cells")
            if not isinstance(encoded, Mapping):
                cell_problems.append(
                    {
                        "kind": "missing_evidence_cells",
                        "side": side,
                        "seed": seed,
                        "draw": draw,
                    }
                )
                continue
            for cell, value in encoded.items():
                cells[side][seed, draw, cell] = _decode_cell(value)
    registered, registered_problems = registered_cells(
        baseline, seeds=seeds, draws=draws
    )
    reported = result.get("conditions")
    reported = reported if isinstance(reported, Mapping) else {}
    lineage = reported.get("fit_lineage")
    provenance = reported.get("provenance")
    fresh_anchor = ssa_revision_anchor()
    provenance_condition = compare_provenance(
        registered_provenance(baseline, sidecar),
        provenance.get("actual") if isinstance(provenance, Mapping) else None,
        fresh_anchor,
    )
    reported_anchor = (
        provenance.get("ssa_revision_anchor")
        if isinstance(provenance, Mapping)
        else None
    )
    if reported_anchor != fresh_anchor:
        provenance_condition["differences"].append(
            {
                "kind": "ssa_revision_anchor_changed",
                "reported": reported_anchor,
                "probed": fresh_anchor,
            }
        )
        provenance_condition.update(status=FAIL, equal=False)
    return {
        "per_draw_cells": compare_cells(
            registered,
            cells,
            seeds=seeds,
            draws=draws,
            problems=[*cell_problems, *registered_problems],
        ),
        "fit_lineage": compare_lineage(
            baseline.get("lineage"),
            lineage.get("actual") if isinstance(lineage, Mapping) else None,
        ),
        "person_level_differential": compare_evidence_differential(
            payloads, seeds=seeds, draws=draws, problems=problems
        ),
        "provenance": provenance_condition,
    }


def guard_claim(
    result: Mapping[str, Any],
    *,
    root: Path,
    baseline: Mapping[str, Any],
    destination: Path,
) -> None:
    """Permit RECONSTRUCTED_REPRODUCTION only when v2's four checks pass.

    A plain mismatch claims nothing and passes through. Any other claim
    must be exactly the v2 admission, and the guard re-derives all four
    conditions from the published evidence against the registered records.
    REPRODUCED, other scopes and truthy non-boolean ``equal`` values are
    refused.
    """
    if not runner.claims_admission(result):
        return
    offending = [
        field
        for field, ok in (
            ("status", result.get("status") == RECONSTRUCTED_REPRODUCTION),
            ("equal", result.get("equal") is True),
            ("admitted_scope", result.get("admitted_scope") == ADMITTED_SCOPE),
            (
                "baseline_version",
                result.get("baseline_version") == runner.RECONSTRUCTED,
            ),
            ("schema_version", result.get("schema_version") == SCHEMA_VERSION),
            (
                "historical_person_level_reference_used",
                result.get("historical_person_level_reference_used") is False,
            ),
        )
        if not ok
    ]
    if offending:
        raise ClaimRefused(
            "the reconstructed baseline may claim only "
            f"{RECONSTRUCTED_REPRODUCTION} with equal=True and admitted scope "
            f"{ADMITTED_SCOPE!r}; refused fields: {offending}"
        )
    reported = admission(result.get("conditions"))
    if reported["status"] != RECONSTRUCTED_REPRODUCTION:
        raise ClaimRefused(
            f"{RECONSTRUCTED_REPRODUCTION} was claimed but the reported "
            f"conditions do not all pass: failed "
            f"{reported['failed_conditions']}, not evaluated "
            f"{reported['not_evaluated_conditions']}, unregistered "
            f"{reported['unregistered_conditions']}"
        )
    sidecar = json.loads((root / runner.SIDECAR_PATH).read_text())
    rederived = rederive_conditions(
        result,
        baseline=baseline,
        sidecar=sidecar,
        destination=destination,
        seeds=runner.REGISTERED_SEEDS,
        draws=runner.REGISTERED_DRAWS,
    )
    verdict = admission(rederived)
    if verdict["status"] != RECONSTRUCTED_REPRODUCTION:
        raise ClaimRefused(
            f"{RECONSTRUCTED_REPRODUCTION} was claimed but, re-derived from "
            f"the published evidence, condition(s) "
            f"{verdict['failed_conditions']} fail",
            rederived=rederived,
        )


def record_abort(result: dict[str, Any], error: BaseException) -> None:
    """Name which of the four conditions failed in a v2 abort record."""
    statuses = dict(admission(result.get("conditions"))["condition_status"])
    rederived = getattr(error, "rederived", None)
    if isinstance(rederived, Mapping):
        guard_statuses = admission(rederived)["condition_status"]
        result["guard"] = {
            "rederived_conditions": dict(rederived),
            "condition_status": guard_statuses,
        }
        for name, status in guard_statuses.items():
            if status == FAIL:
                statuses[name] = FAIL
    result["condition_status"] = statuses
    result["failed_conditions"] = [
        name for name in CONDITIONS if statuses[name] == FAIL
    ]
    result["not_evaluated_conditions"] = [
        name for name in CONDITIONS if statuses[name] == NOT_EVALUATED
    ]
