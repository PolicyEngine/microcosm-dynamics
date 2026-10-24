"""Exact spec-only arithmetic and narrow Trustees baseline extractions.

No real cohort is read. The context parser returns only the registered
2030 OASDI beneficiary count, with its source labels and provenance.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal, localcontext
from fractions import Fraction
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from populace_dynamics.acola_track.config import ROOT
from populace_dynamics.data import tr2008

SNAPSHOT_DIR = ROOT / "data/external/snapshots/tr2026_v_c1_vintage1"
VC1_PATH = SNAPSHOT_DIR / "trustees2026_v_c1_table.html"
VC1_SHA256 = "4d29f2b85d67b995eea25f0bdfb46b3755671c082d75a9855680836d4b80c46a"
VC1_MANIFEST_SHA256 = (
    "fd271e0067c70737ac36e3a442c96d0b7e4650aaa14398b8383ac6e24e853abb"
)
TIMING_NOTE_SHA256 = (
    "f63274d3ef3b06c1647326490945ed05c01421466f9b0cca891bd1d0a511341b"
)
TIMING_NOTE = (
    "a Effective with benefits payable for June in each year 1975-82, "
    "and for December in each year after 1982."
)
VC1_CAPTION = (
    "Table V.C1.—Cost-of-Living Benefit Increases, Average Wage Index, "
    "Contribution and Benefit Bases, and Retirement Earnings Test "
    "Exempt Amounts, 1975-2035"
)
VC1_COLUMN = "Cost-of-living benefit increasea (percent)"
VC1_SOURCE_URL = "https://www.ssa.gov/oact/TR/2026/V_C_prog.html"
CONTEXT_PATH = (
    ROOT
    / "data/external/snapshots/ssa_level_anchors_vintage1"
    / "trustees2026_lr4b4.html"
)
CONTEXT_SHA256 = (
    "40435030d154e29eb49a4e411b78253f504049eddff6e149d7e33033fb139458"
)
CONTEXT_CAPTION = (
    "Table IV.B4.—Covered Workers and Beneficiaries, Calendar Years 1945-2100"
)
CONTEXT_COLUMN = ("Beneficiaries b (in thousands)", "OASDI c")
NULLS_PATH = ROOT / "docs/design/acola_spec_only_nulls.json"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _verified(path: Path, expected: str) -> bytes:
    raw = path.read_bytes()
    if _sha(raw) != expected:
        raise ValueError(f"source SHA-256 differs from pin: {path.name}")
    return raw


def _text(chunks: list[str]) -> str:
    return " ".join("".join(chunks).replace("\xa0", " ").split())


@dataclass
class _Cell:
    text: str
    tag: str
    colspan: int
    rowspan: int


class _Tables(HTMLParser):
    """Resolve literal table labels and spans without printing other cells."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables: list[dict] = []
        self.stack: list[dict] = []

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.stack.append(
                {"caption": None, "rows": [], "row": None, "cell": None}
            )
        elif self.stack:
            table = self.stack[-1]
            if tag == "caption":
                table["caption_chunks"] = []
            elif tag == "tr":
                table["row"] = []
            elif tag in {"th", "td"} and table["row"] is not None:
                table["cell"] = []
                table["tag"] = tag
                table["attrs"] = dict(attrs)
            elif tag == "br" and table["cell"] is not None:
                table["cell"].append(" ")

    def handle_data(self, data):
        if self.stack:
            table = self.stack[-1]
            if "caption_chunks" in table:
                table["caption_chunks"].append(data)
            if table["cell"] is not None:
                table["cell"].append(data)

    def handle_endtag(self, tag):
        if not self.stack:
            return
        table = self.stack[-1]
        if tag == "caption" and "caption_chunks" in table:
            table["caption"] = _text(table.pop("caption_chunks"))
        elif tag in {"th", "td"} and table["cell"] is not None:
            spans = []
            for name in ("colspan", "rowspan"):
                value = table["attrs"].get(name) or "1"
                if not re.fullmatch(r"[1-9]\d*", value):
                    raise ValueError("invalid HTML table span")
                spans.append(int(value))
            table["row"].append(
                _Cell(_text(table["cell"]), table["tag"], *spans)
            )
            table["cell"] = None
        elif tag == "tr" and table["row"] is not None:
            table["rows"].append(table["row"])
            table["row"] = None
        elif tag == "table":
            self.tables.append(self.stack.pop())


def _table(raw: bytes, caption: str) -> dict:
    parser = _Tables()
    parser.feed(raw.decode("utf-8"))
    parser.close()
    matches = [t for t in parser.tables if t["caption"] == caption]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one literal table {caption!r}")
    return matches[0]


def _grid(rows: list[list[_Cell]]) -> list[list[_Cell | None]]:
    occupied = {}
    width = 0
    for r, cells in enumerate(rows):
        col = 0
        for cell in cells:
            while (r, col) in occupied:
                col += 1
            for dr in range(cell.rowspan):
                for dc in range(cell.colspan):
                    key = (r + dr, col + dc)
                    if key in occupied:
                        raise ValueError("overlapping HTML spans")
                    occupied[key] = cell
            col += cell.colspan
        width = max(width, col)
    return [
        [occupied.get((r, c)) for c in range(width)] for r in range(len(rows))
    ]


def _headers(rows: list[list[_Cell]]) -> tuple[tuple[str, ...], ...]:
    paths = []
    grid = _grid(rows)
    for column in range(len(grid[0])):
        parts = []
        previous = None
        for row in grid:
            cell = row[column]
            if cell is not None and cell is not previous and cell.text:
                parts.append(cell.text)
            previous = cell
        paths.append(tuple(parts))
    return tuple(paths)


def _group_rows(table: dict, group: str, years: Iterable[int]):
    wanted = {str(y) for y in years}
    output = {}
    current = None
    for source, expanded in zip(
        table["rows"], _grid(table["rows"]), strict=True
    ):
        nonempty = [c for c in source if c.text]
        if len(nonempty) == 1 and nonempty[0].text.endswith(":"):
            current = nonempty[0].text
        if current != group:
            continue
        labels = [c.text for c in source if c.text in wanted]
        if not labels:
            continue
        if len(labels) != 1 or labels[0] in output:
            raise ValueError("ambiguous registered row label")
        output[labels[0]] = expanded
    if set(output) != wanted:
        raise ValueError("registered Intermediate years missing from table")
    return output


def extract_tr2026_rates(raw: bytes) -> dict[str, Any]:
    """Read V.C1's COLA column only, over the three registered years."""
    table = _table(raw, VC1_CAPTION)
    paths = _headers(table["rows"][:2])
    expected = (VC1_COLUMN,)
    if paths.count(expected) != 1:
        raise ValueError("V.C1 COLA column header differs")
    column = paths.index(expected)
    rows = _group_rows(table, "Intermediate:", (2027, 2028, 2029))
    cells = {}
    for year, row in rows.items():
        cell = row[column]
        if cell is None:
            raise ValueError("registered COLA cell missing")
        literal = cell.text
        percent = Decimal(literal)
        if not percent.is_finite():
            raise ValueError("nonfinite COLA input")
        cells[year] = {
            "as_published": literal,
            "percent": str(percent),
            "rate": str(percent / 100),
            "row_header_path": ["Intermediate:", year],
            "column_header_path": list(expected),
        }
    return {"table": "Table V.C1", "column": VC1_COLUMN, "cells": cells}


def tr2026_inputs() -> dict[str, Any]:
    _verified(SNAPSHOT_DIR / "capture_manifest.txt", VC1_MANIFEST_SHA256)
    raw = _verified(VC1_PATH, VC1_SHA256)
    capture = json.loads((SNAPSHOT_DIR / "capture_record.json").read_bytes())
    if (
        capture["source_url"] != VC1_SOURCE_URL
        or capture["caption"] != VC1_CAPTION
        or capture["fragment"]["sha256"] != VC1_SHA256
        or capture["fragment"]["bytes"] != len(raw)
    ):
        raise ValueError(
            "TR2026 capture record does not identify pinned table"
        )
    timing_raw = _verified(
        SNAPSHOT_DIR / "cola_timing_note.txt", TIMING_NOTE_SHA256
    )
    if timing_raw.decode("utf-8").strip() != TIMING_NOTE:
        raise ValueError(
            "V.C1 timing footnote differs from registered mapping"
        )
    timing_record = json.loads(
        (SNAPSHOT_DIR / "timing_note_record.json").read_bytes()
    )
    if (
        timing_record["sha256"] != TIMING_NOTE_SHA256
        or timing_record["bytes"] != len(timing_raw)
        or timing_record["source_url"] != VC1_SOURCE_URL
        or timing_record["text"] != TIMING_NOTE
    ):
        raise ValueError("V.C1 timing footnote record differs")
    return {
        **extract_tr2026_rates(raw),
        "source_url": VC1_SOURCE_URL,
        "file": str(VC1_PATH.relative_to(ROOT)),
        "sha256": VC1_SHA256,
        "capture_manifest_sha256": VC1_MANIFEST_SHA256,
        "retrieved_utc": capture["retrieved_utc"],
        "located_from": capture["located_from"],
        "timing_footnote": {
            "text": TIMING_NOTE,
            "file": str(
                (SNAPSHOT_DIR / "cola_timing_note.txt").relative_to(ROOT)
            ),
            "sha256": TIMING_NOTE_SHA256,
            "retrieved_utc": timing_record["retrieved_utc"],
            "anchor": timing_record["anchor"],
        },
        "fallback_used": False,
        "column_choice": (
            "Printed COLA column, matching TR2008 V.C1; determination "
            "year k is the increase effective December k."
        ),
    }


def _fraction(value: Any) -> Fraction:
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("nonfinite rate")
        return Fraction(str(value))
    return Fraction(value)


def spec_null(
    rates: Iterable[Any], annual_reduction: Any = "0.01"
) -> Fraction:
    """Exact percent effect 100 * (product of registered factors - 1)."""
    reduction = _fraction(annual_reduction)
    if reduction < 0:
        raise ValueError("annual reduction must be non-negative")
    product = Fraction(1)
    for value in rates:
        rate = _fraction(value)
        if rate <= -1 or rate - reduction < 0:
            raise ValueError("REFUSE: reformed increase is negative")
        product *= (1 + rate - reduction) / (1 + rate)
    return 100 * (product - 1)


def _exact_record(value: Fraction) -> dict[str, Any]:
    with localcontext() as context:
        context.prec = 50
        decimal = Decimal(value.numerator) / Decimal(value.denominator)
    return {
        "value": float(value),
        "value_decimal": str(decimal),
        "exact": {
            "numerator": str(value.numerator),
            "denominator": str(value.denominator),
        },
    }


def model_inputs() -> dict[str, Any]:
    entries = tr2008.cola_path(2010, 2029, alternative="intermediate")
    return {
        "file": "data/external/tr2008/tr2008_report.json",
        "sha256": _sha(
            (ROOT / "data/external/tr2008/tr2008_report.json").read_bytes()
        ),
        "rates": {
            str(e.determination_year): str(Decimal(str(e.percent)) / 100)
            for e in entries
        },
        "source_tags": {str(e.determination_year): e.source for e in entries},
        "basis": (
            "TR2008 V.C1 printed COLAs through 2017; Table II.C1 ultimate "
            "annual-average CPI from 2018, matching the runtime model path."
        ),
    }


def build_nulls(*, annual_reduction: Any = "0.01", baseline=None) -> dict:
    inputs = tr2026_inputs()
    model = model_inputs()
    rates = dict(model["rates"])
    if baseline is not None:
        rates = {
            str(y): str(baseline.rate_for_determination_year(y))
            for y in range(2010, 2030)
        }
        model = {
            **model,
            "rates": rates,
            "runtime_matches_committed_tr2008": all(
                _fraction(rates[y]) == _fraction(model["rates"][y])
                for y in rates
            ),
        }
    specifications = {
        "N": (range(2027, 2030), inputs, "TR2026"),
        "N_model": (range(2027, 2030), model, "model_TR2008"),
        "N_MINT": (range(2011, 2030), model, "model_TR2008"),
        "N_M1": (range(2010, 2030), model, "model_TR2008"),
    }
    output = {
        "schema_version": "populace_dynamics.acola_track.spec_nulls.v1",
        "annual_reduction": str(annual_reduction),
        "inputs": {"TR2026": inputs, "model_TR2008": model},
        "december_null_registered": False,
        "december_note": (
            "C1 and M2 include December2030; the registered nulls stop "
            "at determination year2029. No December null is computed."
        ),
    }
    exact = {}
    for name, (years, source, source_key) in specifications.items():
        years = list(years)
        values = {
            str(y): (
                source["cells"][str(y)]["rate"]
                if source_key == "TR2026"
                else rates[str(y)]
            )
            for y in years
        }
        exact[name] = spec_null(values.values(), annual_reduction)
        output[name] = {
            **_exact_record(exact[name]),
            "years": years,
            "factor_count": len(years),
            "rates": values,
            "source": source_key,
        }
    output["N_minus_N_model"] = _exact_record(exact["N"] - exact["N_model"])
    return output


def nulls_for_run(baseline, annual_reduction: Any = "0.01") -> dict:
    """Recompute using the runtime baseline; retain a pre-run source record."""
    committed = json.loads(NULLS_PATH.read_bytes())
    expected = build_nulls()
    if committed != expected:
        raise ValueError("committed spec-only nulls differ from their inputs")
    result = build_nulls(annual_reduction=annual_reduction, baseline=baseline)
    result["committed_file"] = str(NULLS_PATH.relative_to(ROOT))
    result["committed_file_sha256"] = _sha(NULLS_PATH.read_bytes())
    return result


def extract_context_count(raw: bytes) -> dict[str, Any]:
    """Extract exactly one beneficiary count; return no other source values."""
    table = _table(raw, CONTEXT_CAPTION)
    # The committed table has three header rows, ending before Historical.
    header_rows = []
    for row in table["rows"]:
        if any(c.text == "Historical data:" for c in row):
            break
        header_rows.append(row)
    paths = _headers(header_rows)
    if paths.count(CONTEXT_COLUMN) != 1:
        raise ValueError("IV.B4 OASDI beneficiary column header differs")
    selected = _group_rows(table, "Intermediate:", (2030,))["2030"]
    cell = selected[paths.index(CONTEXT_COLUMN)]
    if cell is None or not re.fullmatch(r"\d[\d,]*", cell.text):
        raise ValueError("IV.B4 OASDI beneficiary count is not an integer")
    thousands = int(cell.text.replace(",", ""))
    return {
        "beneficiary_count": thousands * 1000,
        "published_count_thousands": thousands,
        "as_published": cell.text,
        "table": "Table IV.B4",
        "row_header_path": ["Intermediate:", "2030"],
        "column_header_path": list(CONTEXT_COLUMN),
        "published_unit": "thousand_persons",
        "stored_unit": "persons",
        "scale_multiplier": 1000,
        "context_only": True,
        "scaling_applied_to_model": False,
    }


def context_beneficiary_count() -> dict[str, Any]:
    raw = _verified(CONTEXT_PATH, CONTEXT_SHA256)
    return {
        **extract_context_count(raw),
        "source_url": "https://www.ssa.gov/oact/TR/2026/lr4b4.html",
        "file": str(CONTEXT_PATH.relative_to(ROOT)),
        "sha256": CONTEXT_SHA256,
    }
