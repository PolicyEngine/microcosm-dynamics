"""Run the Amendment 10 (§24) successor census over the field denominator.

The input is the §24 unit-authority input relation: one JSON object per line,
in §20.3.7 denominator order, carrying exactly ``interview_wave``,
``raw_field_id``, ``derivation_status`` and ``resolution_reason`` (the
ratified terminal and its diagnostic), and ``source_description`` (the
derived codebook description, JSON null when the field block is silent).
That relation is produced by the pinned §19.3.2 codebook derivation together
with the ratified §20 classifier; this script neither derives nor re-derives
it, so the successor census reproduces from the frozen relation alone.

Usage::

    python scripts/build_amendment10_successor_census.py \\
        --field-rows <path.jsonl> [--output <path.json>] [--statements]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from populace_dynamics.data.psid_unit_authority import (  # noqa: E402
    canonical_sha256,
    statement_table,
    successor_census,
)

INPUT_KEYS = (
    "derivation_status",
    "interview_wave",
    "raw_field_id",
    "resolution_reason",
    "source_description",
)


def read_field_rows(path: Path) -> Iterator[dict[str, Any]]:
    """Yield the input relation, asserting its exact five-key shape."""

    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            row = json.loads(line)
            if tuple(sorted(row)) != INPUT_KEYS:
                raise SystemExit(
                    f"line {number}: unexpected keys {sorted(row)}"
                )
            yield row


def input_relation_sha256(path: Path) -> tuple[int, str]:
    """Return the row count and §10.1 digest of the complete input."""

    rows = [
        [
            row["interview_wave"],
            row["raw_field_id"],
            row["derivation_status"],
            row["resolution_reason"],
            row["source_description"],
        ]
        for row in read_field_rows(path)
    ]
    return len(rows), canonical_sha256(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--field-rows", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--statements",
        type=Path,
        help="write the complete spelling table as canonical JSON lines",
    )
    arguments = parser.parse_args()

    row_count, relation_sha256 = input_relation_sha256(arguments.field_rows)
    census = successor_census(read_field_rows(arguments.field_rows))
    if census["field_count"] != row_count:
        raise SystemExit("census did not cover the input relation")

    table = statement_table(read_field_rows(arguments.field_rows))
    unit_rows = [row for row in table if row["typed_value_unit"] is not None]
    payload: dict[str, Any] = {
        "schema_version": "amendment_10_successor_census.v1",
        "input_relation_row_count": row_count,
        "input_relation_sha256": relation_sha256,
        "statement_table_row_count": len(table),
        "statement_table_sha256": canonical_sha256(table),
        "unit_bearing_statement_count": len(unit_rows),
        **census,
    }
    payload["census_sha256"] = canonical_sha256(payload)

    if arguments.statements is not None:
        with arguments.statements.open("w", encoding="utf-8") as handle:
            for row in table:
                handle.write(
                    json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n"
                )
    if arguments.output is not None:
        arguments.output.write_bytes(
            json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
            + b"\n"
        )
    print(json.dumps(payload, indent=2, sort_keys=True)[:4000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
