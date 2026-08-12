#!/usr/bin/env python3
"""Extract audited SSA Supplement Table 4.B7 worker-band shares."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_DIR = ROOT / "data/external/snapshots/ssa_level_anchors_vintage1"
SOURCE = SNAPSHOT_DIR / "supplement2025_4b.html"
SOURCE_SHA256 = (
    "c228920ea9d53b1e323e5933b6d9f926e3c9b609d868b549fabc40118554b449"
)
SOURCE_SIZE_BYTES = 488_165
CAPTURE_MANIFEST = SNAPSHOT_DIR / "capture_manifest.txt"
CAPTURE_MANIFEST_SHA256 = (
    "569dbed5922c2192277eb671685a5859ba1440e30289e8c252e1762956c150ca"
)
OUT = ROOT / "data/external/ssa_supplement2025_4b7_band_shares_v1.json"
TABLE_ID = "table4.b7"
SOURCE_URL = (
    "https://www.ssa.gov/policy/docs/statcomps/supplement/2025/"
    "4b.html#table4.b7"
)


ROW_SPECS = (
    {
        "row_id": "ssa_4b7_all_workers_share_1_9999",
        "header": "1-9,999",
        "column_index": 0,
        "years": list(range(2015, 2023)),
    },
    {
        "row_id": "ssa_4b7_all_workers_share_10000_19999",
        "header": "10,000-19,999",
        "column_index": 1,
        "years": list(range(2015, 2023)),
    },
    {
        "row_id": "ssa_4b7_all_workers_share_20000_39999",
        "header": "20,000-39,999",
        "column_index": 2,
        "years": list(range(2015, 2023)),
    },
    {
        "row_id": "ssa_4b7_all_workers_share_40000_59999",
        "header": "40,000-59,999",
        "column_index": 3,
        "years": list(range(2015, 2023)),
    },
    {
        "row_id": "ssa_4b7_all_workers_share_60000_79999",
        "header": "60,000-79,999",
        "column_index": 4,
        "years": list(range(2015, 2023)),
    },
    {
        "row_id": "ssa_4b7_all_workers_share_80000_99999",
        "header": "80,000-99,999",
        "column_index": 5,
        "years": list(range(2015, 2023)),
    },
    {
        "row_id": "ssa_4b7_all_workers_share_100000_119999",
        "header": "100,000-119,999",
        "column_index": 6,
        "years": list(range(2015, 2023)),
    },
    {
        "row_id": "ssa_4b7_all_workers_share_120000_139999",
        "header": "120,000-139,999",
        "column_index": 7,
        "years": list(range(2017, 2023)),
    },
    {
        "row_id": "ssa_4b7_all_workers_share_140000_149999",
        "header": "140,000-149,999",
        "column_index": 8,
        "years": [2021, 2022],
    },
    {
        "row_id": "ssa_4b7_all_workers_share_150000_160199",
        "header": "150,000-160,199",
        "column_index": 9,
        "years": [2023],
    },
    {
        "row_id": "ssa_4b7_all_workers_share_at_taxable_maximum",
        "header": "Workers with maximum earnings",
        "column_index": 10,
        "years": list(range(2015, 2023)),
    },
)


def sha256(raw: bytes) -> str:
    """Return the lowercase SHA-256 identity of bytes."""

    return hashlib.sha256(raw).hexdigest()


class TableParser(HTMLParser):
    """Collect table rows while tolerating the publisher's stray end tags."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.div_stack: list[str | None] = []
        self.rows: dict[str | None, list[list[dict[str, Any]]]] = defaultdict(
            list
        )
        self.current_row: dict[str, Any] | None = None
        self.current_cell: dict[str, Any] | None = None

    @property
    def active_table_id(self) -> str | None:
        """Return the innermost named div, if any."""

        return next(
            (value for value in reversed(self.div_stack) if value), None
        )

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = dict(attrs)
        if tag == "div":
            self.div_stack.append(attributes.get("id"))
        elif tag == "tr":
            self.current_row = {
                "table_id": self.active_table_id,
                "cells": [],
            }
        elif tag in {"th", "td"} and self.current_row is not None:
            self.current_cell = {"parts": []}

    def handle_data(self, data: str) -> None:
        if self.current_cell is not None:
            self.current_cell["parts"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"th", "td"} and self.current_cell is not None:
            assert self.current_row is not None
            text = " ".join("".join(self.current_cell["parts"]).split())
            self.current_row["cells"].append({"text": text})
            self.current_cell = None
        elif tag == "tr" and self.current_row is not None:
            self.rows[self.current_row["table_id"]].append(
                self.current_row["cells"]
            )
            self.current_row = None
        elif tag == "div" and self.div_stack:
            self.div_stack.pop()


def parse_number(text: str) -> int | None:
    """Parse one printed thousand-count or its structural N/A marker."""

    if "..." in text.replace(" ", ""):
        return None
    return int(text.replace(",", ""))


def verified_source_bytes() -> bytes:
    """Return the source bytes after checking both snapshot identities."""

    manifest_raw = CAPTURE_MANIFEST.read_bytes()
    if sha256(manifest_raw) != CAPTURE_MANIFEST_SHA256:
        raise AssertionError("SSA snapshot capture manifest SHA-256 drifted")
    source_raw = SOURCE.read_bytes()
    if (
        sha256(source_raw) != SOURCE_SHA256
        or len(source_raw) != SOURCE_SIZE_BYTES
    ):
        raise AssertionError("SSA Supplement 4.B source identity drifted")
    matching_lines = [
        line
        for line in manifest_raw.decode("utf-8").splitlines()
        if line.endswith(" supplement2025_4b.html")
    ]
    if len(matching_lines) != 1:
        raise AssertionError("SSA 4.B capture manifest entry is ambiguous")
    parts = matching_lines[0].split()
    if parts[1:] != [
        SOURCE_SHA256,
        str(SOURCE_SIZE_BYTES),
        "supplement2025_4b.html",
    ]:
        raise AssertionError("SSA 4.B capture manifest entry drifted")
    return source_raw


def all_worker_rows(source_raw: bytes) -> dict[int, dict[str, Any]]:
    """Return audited all-worker rows, taking the first panel occurrence."""

    parser = TableParser()
    parser.feed(source_raw.decode("utf-8"))
    rows: dict[int, dict[str, Any]] = {}
    for cells in parser.rows[TABLE_ID]:
        texts = [cell["text"] for cell in cells]
        if not texts or re.match(r"20(?:1[5-9]|2[0-3])", texts[0]) is None:
            continue
        year = int(texts[0][:4])
        if year in rows:
            continue
        values = [parse_number(value) for value in texts[1:]]
        if len(values) != 12 or values[0] is None:
            raise AssertionError(f"unexpected SSA 4.B7 row shape: {year}")
        denominator, *numerators = values
        rounded_sum = sum(value for value in numerators if value is not None)
        if abs(rounded_sum - denominator) > 2:
            raise AssertionError(f"SSA 4.B7 row does not reconcile: {year}")
        rows[year] = {
            "denominator_thousands": denominator,
            "numerators_thousands": numerators,
        }
    if set(rows) != set(range(2015, 2024)):
        raise AssertionError("SSA 4.B7 audited year window is incomplete")
    return rows


def build() -> dict[str, Any]:
    """Build the canonical audited extraction."""

    source_rows = all_worker_rows(verified_source_bytes())
    rows = {}
    for spec in ROW_SPECS:
        observations = []
        for year in spec["years"]:
            source_row = source_rows[year]
            numerator = source_row["numerators_thousands"][
                spec["column_index"]
            ]
            denominator = source_row["denominator_thousands"]
            if numerator is None:
                raise AssertionError(
                    f"structural N/A entered audited row: {spec['row_id']}"
                )
            observations.append(
                {
                    "denominator_thousands": denominator,
                    "numerator_thousands": numerator,
                    "share": numerator / denominator,
                    "year": year,
                }
            )
        rows[spec["row_id"]] = {
            "header": spec["header"],
            "one_based_data_column": spec["column_index"] + 2,
            "observations": observations,
        }
    return {
        "rows": rows,
        "schema_version": "ssa_supplement_4b7_band_shares.v1",
        "source": {
            "capture_manifest": {
                "path": CAPTURE_MANIFEST.relative_to(ROOT).as_posix(),
                "sha256": CAPTURE_MANIFEST_SHA256,
            },
            "capture_path": SOURCE.relative_to(ROOT).as_posix(),
            "capture_sha256": SOURCE_SHA256,
            "capture_size_bytes": SOURCE_SIZE_BYTES,
            "denominator": "same-year Table 4.B7 all-worker Total",
            "document": "Annual Statistical Supplement, 2025",
            "locator": "div#table4.b7 > table",
            "publisher": "Social Security Administration",
            "table": "4.B7",
            "url": SOURCE_URL,
        },
        "transform": (
            "printed band thousand-count divided by the same-year, same-panel "
            "printed Total; structural N/A cells excluded"
        ),
    }


def render() -> bytes:
    """Render canonical sorted JSON bytes."""

    return (
        json.dumps(
            build(),
            sort_keys=True,
            indent=2,
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if the committed extraction differs; never write",
    )
    args = parser.parse_args()
    expected = render()
    if args.check:
        if not OUT.exists() or OUT.read_bytes() != expected:
            raise SystemExit(f"generated artifact is stale: {OUT}")
        return
    OUT.write_bytes(expected)


if __name__ == "__main__":
    main()
