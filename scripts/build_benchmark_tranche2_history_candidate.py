#!/usr/bin/env python3
"""Build the complete tranche-2 benchmark history candidate.

This builder carries forward the immutable 42-row seed measurements, replaces
the revised CBO tax-revenue evaluation, and adds the other 59 audited actions.
It never appends history; ``benchmarks/append_history.py`` remains the only
writer for the standing append-only artifacts.
"""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS = ROOT / "benchmarks"
EVALUATION = ROOT / "runs/benchmark_tranche2_evaluation_v1.json"

sys.path.insert(0, str(BENCHMARKS))
from schema import (  # noqa: E402
    LEGACY_ROW_IDS,
    MISSING_MODULE_DEVIATION,
    canonical_jsonl_line,
    embedded_label_arrays,
    evidence_bound_label_note,
    load_history,
    load_registry,
    sha256_bytes,
    validate_history,
    validate_history_against_registry,
)

REVISED_ROW_ID = "cbo.tax_revenue.share_of_taxable_payroll"
EXPECTED_EVALUATION_SCHEMA = "benchmark_tranche2_evaluation.v1"
EXPECTED_REGISTRY_ROW_COUNT = 101
EXPECTED_ACTION_COUNTS = {"add": 59, "revise": 1}


def load_evaluation() -> tuple[dict[str, Any], bytes]:
    """Load and validate the immutable 60-action evaluation artifact."""

    raw = EVALUATION.read_bytes()
    evaluation = json.loads(raw)
    if evaluation.get("schema_version") != EXPECTED_EVALUATION_SCHEMA:
        raise AssertionError("tranche-2 evaluation schema drifted")
    rows = evaluation.get("rows")
    if not isinstance(rows, list) or len(rows) != 60:
        raise AssertionError("tranche-2 evaluation must contain 60 actions")
    row_ids = [row.get("row_id") for row in rows]
    if not all(isinstance(row_id, str) and row_id for row_id in row_ids):
        raise AssertionError("tranche-2 evaluation has an invalid row id")
    if len(set(row_ids)) != len(row_ids):
        raise AssertionError("tranche-2 evaluation row ids collide")
    action_counts = {
        action: sum(row.get("action") == action for row in rows)
        for action in EXPECTED_ACTION_COUNTS
    }
    if action_counts != EXPECTED_ACTION_COUNTS:
        raise AssertionError("tranche-2 evaluation action census drifted")
    revised = [row for row in rows if row.get("action") == "revise"]
    if len(revised) != 1 or revised[0]["row_id"] != REVISED_ROW_ID:
        raise AssertionError("unexpected revised tranche-2 row")
    return evaluation, raw


def artifact_label_state(
    entry: dict[str, Any],
    registered_state: dict[str, Any],
    cache: dict[Path, list[str] | None],
) -> dict[str, Any]:
    """Bind one history label state to its registered model artifact."""

    pointer = entry["our_side_artifact"]["artifact_pointer"]
    path = (ROOT / pointer["path"]).resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise AssertionError(f"model artifact escapes repository: {path}")
    if path not in cache:
        raw = path.read_bytes()
        if sha256_bytes(raw) != pointer["sha256"]:
            raise AssertionError(f"model artifact identity drifted: {path}")
        arrays = embedded_label_arrays(json.loads(raw))
        identities = {json.dumps(array, sort_keys=True) for array in arrays}
        if len(identities) > 1:
            raise AssertionError(f"ambiguous model artifact labels: {path}")
        cache[path] = (
            json.loads(next(iter(identities))) if identities else None
        )

    labels = cache[path]
    legacy_labels = registered_state["source_artifact_embedded_labels"]
    state = deepcopy(registered_state)
    state["source_artifact_embedded_labels"] = deepcopy(labels)
    state["source_artifact_label_note"] = evidence_bound_label_note(
        labels, legacy_labels
    )
    return state


def evaluation_record(
    row: dict[str, Any],
    entry: dict[str, Any],
    *,
    run_sha: str,
    registry_sha: str,
    label_state: dict[str, Any],
) -> dict[str, Any]:
    """Translate one audited evaluation action to standing-history shape."""

    pointer = entry["our_side_artifact"]["artifact_pointer"]
    if row["our"]["artifact_pointer"] != pointer:
        raise AssertionError(
            f"evaluation model provenance disagrees with registry: "
            f"{row['row_id']}"
        )
    if row["gap_class"] != entry["gap_class"]:
        raise AssertionError(
            f"evaluation gap class disagrees with registry: {row['row_id']}"
        )
    if row["our"]["unit"] != entry["our_side_artifact"]["unit"]:
        raise AssertionError(
            f"evaluation model unit disagrees with registry: {row['row_id']}"
        )
    if row["published"]["unit"] != entry["published_unit"]:
        raise AssertionError(
            f"evaluation published unit disagrees with registry: "
            f"{row['row_id']}"
        )
    if row["our"]["value"] is None:
        if (
            row["gap_class"] != "module_missing"
            or row["deviation"] != MISSING_MODULE_DEVIATION
        ):
            raise AssertionError(
                f"invalid null evaluation sentinel: {row['row_id']}"
            )

    return {
        "deviation": deepcopy(row["deviation"]),
        "evaluated_at_run": run_sha,
        "gap_class": entry["gap_class"],
        "gap_note": entry["gap_note"],
        "label_state": label_state,
        "our": {
            "unit": row["our"]["unit"],
            "value": deepcopy(row["our"]["value"]),
        },
        "published": deepcopy(row["published"]),
        "registry_sha": registry_sha,
        "row_id": row["row_id"],
    }


def carried_seed_record(
    seed: dict[str, Any],
    entry: dict[str, Any],
    *,
    run_sha: str,
    registry_sha: str,
    label_state: dict[str, Any],
) -> dict[str, Any]:
    """Carry one unrevised legacy measurement into the current evaluation."""

    row_id = entry["row_id"]
    if seed["row_id"] != row_id:
        raise AssertionError(f"legacy seed order drifted: {row_id}")
    if seed["our"]["unit"] != entry["our_side_artifact"]["unit"]:
        raise AssertionError(f"legacy model unit drifted: {row_id}")
    if seed["published"]["unit"] != entry["published_unit"]:
        raise AssertionError(f"legacy published unit drifted: {row_id}")
    return {
        "deviation": deepcopy(seed["deviation"]),
        "evaluated_at_run": run_sha,
        "gap_class": entry["gap_class"],
        "gap_note": entry["gap_note"],
        "label_state": label_state,
        "our": deepcopy(seed["our"]),
        "published": deepcopy(seed["published"]),
        "registry_sha": registry_sha,
        "row_id": row_id,
    }


def build() -> list[dict[str, Any]]:
    """Build the full current-registry evaluation in exact registry order."""

    registry, registry_raw = load_registry()
    entries = registry["entries"]
    if len(entries) != EXPECTED_REGISTRY_ROW_COUNT:
        raise AssertionError("tranche-2 registry must contain 101 rows")
    row_order = [entry["row_id"] for entry in entries]
    if tuple(row_order[: len(LEGACY_ROW_IDS)]) != LEGACY_ROW_IDS:
        raise AssertionError("legacy registry prefix drifted")

    history, _ = load_history(require_git=False)
    seeds = history[: len(LEGACY_ROW_IDS)]
    if tuple(seed["row_id"] for seed in seeds) != LEGACY_ROW_IDS:
        raise AssertionError("immutable 42-row history seed drifted")
    seed_by_id = {seed["row_id"]: seed for seed in seeds}

    evaluation, evaluation_raw = load_evaluation()
    action_by_id = {row["row_id"]: row for row in evaluation["rows"]}
    expected_action_ids = {REVISED_ROW_ID, *row_order[len(LEGACY_ROW_IDS) :]}
    if set(action_by_id) != expected_action_ids:
        raise AssertionError(
            "evaluation actions do not match the revised row and additions"
        )
    if any(
        action_by_id[row_id]["action"] != "add"
        for row_id in row_order[len(LEGACY_ROW_IDS) :]
    ):
        raise AssertionError("new registry row is not an add action")

    registry_sha = sha256_bytes(registry_raw)
    run_sha = sha256_bytes(evaluation_raw)
    registered_state = registry["migration_context"]["wish_financing_stub"][
        "our"
    ]["label_state"]
    label_cache: dict[Path, list[str] | None] = {}
    records = []
    for entry in entries:
        row_id = entry["row_id"]
        label_state = artifact_label_state(
            entry, registered_state, label_cache
        )
        if row_id in action_by_id:
            record = evaluation_record(
                action_by_id[row_id],
                entry,
                run_sha=run_sha,
                registry_sha=registry_sha,
                label_state=label_state,
            )
        else:
            record = carried_seed_record(
                seed_by_id[row_id],
                entry,
                run_sha=run_sha,
                registry_sha=registry_sha,
                label_state=label_state,
            )
        records.append(record)

    validate_history(records)
    validate_history_against_registry(records, registry, registry_sha)
    return records


def render() -> bytes:
    """Render canonical candidate JSONL bytes."""

    return b"".join(canonical_jsonl_line(record) for record in build())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="candidate JSONL path")
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if output differs from rebuilt bytes; never write",
    )
    args = parser.parse_args()
    expected = render()
    if args.check:
        if not args.output.exists() or args.output.read_bytes() != expected:
            raise SystemExit(f"generated candidate is stale: {args.output}")
        return
    args.output.write_bytes(expected)


if __name__ == "__main__":
    main()
