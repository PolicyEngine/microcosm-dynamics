"""Rebuild Supplement 2026 Table 6.B5.1 from the supplied SSA captures.

The captured 2026 edition has the same twelve age columns as the 2023
reference, with entitlement years 1998-2025. Every cell is parsed using
its HTML ``headers`` attribute; unexpected headers, missing cells,
duplicate years, and incomplete coverage are refused. The published
rounding residuals are retained, never normalized in the artifact.

No network is used. Both the 2025 and 2026 captures are SHA-256 verified.
The 2026 edition is selected because its layout matches the existing
``ssa_claim_ages.v1`` schema. ``--check`` re-parses both captured tables
and compares the deterministic outputs without writing. Small, exact
captures are committed as deterministic gzip streams for offline replay.

Source: SSA Annual Statistical Supplement 2026, section 6.B,
https://www.ssa.gov/policy/docs/statcomps/supplement/2026/6b.html,
div ``table6.b5.1``, thead/tbody/tfoot. Captured 2026-10-02T12:08:05Z.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import math
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from build_ssa_claim_ages import (
    COLLAPSED_CATEGORIES,
    FRA_MONTHS_BY_ATTAIN_65_YEAR,
    RAW_COLUMNS,
    SUM_TOLERANCE,
    _collapse,
    _era_mapping,
    _fra_at,
)

ROOT = Path(__file__).resolve().parents[1]
EXTERNAL = ROOT / "data" / "external"
OUT_PATH = EXTERNAL / "ssa_claim_ages_2026supplement.json"
PROVENANCE_PATH = EXTERNAL / "ssa_supplement_2026_6b.source.provenance.json"
CAPTURED_UTC = "2026-10-02T12:08:05Z"
SOURCE_SHA256 = {
    2025: "1ba2e4f895da924286401189ab1144406640b58e56ce1b2e74f00f9caba405a2",
    2026: "1f9eceb2cfa45e181aa38ca7ce33b5babc77e8cb6d77fd1343650224a0a7d06a",
}
LEAF_FIELDS = dict(
    zip(
        (
            "c2",
            "c3",
            "c5",
            "c6",
            "c7",
            "c8",
            "c14",
            "c15",
            "c16",
            "c17",
            "c18",
            "c19",
            "c11",
            "c12",
            "c13",
        ),
        ("number_thousands", "average_age", "published_total", *RAW_COLUMNS),
        strict=True,
    )
)
EXPECTED_HEADERS = {
    "c1": "Year of entitlement",
    "c2": "Number (thousands)",
    "c3": "Average age",
    "c4": "Percentage distribution by age at month of entitlement",
    "c5": "Total, all ages",
    "c6": "62",
    "c7": "63",
    "c8": "64",
    "c9": "65 a",
    "c10": "66 a",
    "c11": "Disability conversions b",
    "c12": "67–69",
    "c13": "70 or older",
    "c14": "Before FRA",
    "c15": "At FRA",
    "c16": "After FRA",
    "c17": "Before FRA",
    "c18": "At FRA",
    "c19": "After FRA",
}


def source_name(edition: int) -> str:
    return f"ssa_supplement_{edition}_6b.source.html.gz"


def gzip_bytes(raw: bytes) -> bytes:
    """Stable gzip metadata across supported Python versions."""
    output = io.BytesIO()
    with gzip.GzipFile(
        filename="", mode="wb", fileobj=output, mtime=0
    ) as stream:
        stream.write(raw)
    return output.getvalue()


def read_source(edition: int, inputs: Path | None = None) -> bytes:
    """Verify exact supplied bytes, using committed gzip if no input root."""
    if inputs is None:
        raw = gzip.decompress((EXTERNAL / source_name(edition)).read_bytes())
    else:
        raw = (inputs / f"supplement_{edition}_6b.html").read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256[edition]:
        raise ValueError(f"Supplement {edition} source SHA-256 mismatch")
    return raw


class TableParser(HTMLParser):
    """Collect rows/cells and text from an isolated table, preserving labels."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[tuple[str, dict[str, str], str]]] = []
        self.caption = ""
        self._row: list[tuple[str, dict[str, str], str]] = []
        self._cell: tuple[str, dict[str, str]] | None = None
        self._text: list[str] = []
        self._in_caption = False

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag == "tr":
            self._row = []
        elif tag in ("th", "td"):
            self._cell = (tag, dict(attrs))
            self._text = []
        elif tag == "caption":
            self._in_caption = True

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._text.append(data)
        if self._in_caption:
            self.caption += data

    def handle_endtag(self, tag: str) -> None:
        if tag in ("th", "td") and self._cell is not None:
            kind, attrs = self._cell
            value = " ".join("".join(self._text).split())
            self._row.append((kind, attrs, value))
            self._cell = None
        elif tag == "tr":
            self.rows.append(self._row)
        elif tag == "caption":
            self._in_caption = False


def parse_table(raw: bytes, edition: int) -> dict[str, Any]:
    """Extract exact cells and notes; refuse schema and coverage changes."""
    text = raw.decode("utf-8")
    anchor = text.find('id="table6.b5.1"')
    start = text.find("<table>", anchor)
    end = text.find("</table>", start)
    if anchor < 0 or start < 0 or end < 0:
        raise ValueError("Table 6.B5.1 boundaries missing")
    parser = TableParser()
    parser.feed(text[start : end + len("</table>")])
    header_cells = [
        (attrs["id"], value)
        for row in parser.rows
        for kind, attrs, value in row
        if kind == "th" and attrs.get("id", "").startswith("c")
    ]
    headers = dict(header_cells)
    if len(headers) != len(header_cells) or headers != EXPECTED_HEADERS:
        raise ValueError("Table 6.B5.1 column layout changed")
    data: dict[str, dict[str, Any]] = {"male": {}, "female": {}}
    notes: list[str] = []
    sex = None
    for row in parser.rows:
        panels = [v for _, a, v in row if a.get("class") == "panel"]
        if panels:
            if panels not in (["Men"], ["Women"]):
                raise ValueError(f"Unknown sex panel: {panels}")
            sex = "male" if panels == ["Men"] else "female"
            continue
        years = [v for _, a, v in row if a.get("class") == "stub0"]
        if not years:
            notes.extend(
                v
                for _, a, v in row
                if "Note" in a.get("class", "") or a.get("class") == "note"
            )
            continue
        if (
            sex is None
            or len(years) != 1
            or not re.fullmatch(r"\d{4}", years[0])
        ):
            raise ValueError("Unexpected year row or missing sex panel")
        year = years[0]
        if year in data[sex]:
            raise ValueError(f"Duplicate {sex} year {year}")
        fields = {}
        for kind, attrs, value in row:
            if kind != "td":
                continue
            leaf = attrs.get("headers", "").split()[-1:]
            if not leaf or leaf[0] not in LEAF_FIELDS:
                raise ValueError("Missing or unknown cell header")
            field = LEAF_FIELDS[leaf[0]]
            if field in fields:
                raise ValueError("Duplicate cell header")
            if value == ". . .":
                fields[field] = None
            else:
                try:
                    parsed = float(value.replace(",", ""))
                    if not math.isfinite(parsed):
                        raise ValueError("nonfinite numeric cell")
                    fields[field] = parsed
                except ValueError as exc:
                    raise ValueError(f"Unrecognized cell {value!r}") from exc
        if set(fields) != set(LEAF_FIELDS.values()):
            raise ValueError("Missing published cells")
        raw_values = {k: fields[k] for k in RAW_COLUMNS}
        if any(
            v is not None and not 0 <= v <= 100 for v in raw_values.values()
        ):
            raise ValueError("Claiming share outside [0,100]")
        at_columns = [raw_values[k] for k in ("age65_at_fra", "age66_at_fra")]
        if sum(v is not None for v in at_columns) != 1:
            raise ValueError("Expected one at-FRA column")
        number = fields["number_thousands"]
        if number is None or number != int(number) or number <= 0:
            raise ValueError("Invalid number of awardees")
        if fields["average_age"] is None:
            raise ValueError("Missing average age")
        if fields["published_total"] != 100.0:
            raise ValueError("Expected published total 100")
        categories = _collapse(raw_values)
        component_sum = round(sum(categories.values()), 1)
        residual = round(component_sum - 100.0, 1)
        if abs(residual) > SUM_TOLERANCE:
            raise ValueError("Shares exceed published rounding tolerance")
        data[sex][year] = {
            "number_thousands": int(number),
            "average_age": fields["average_age"],
            "published_total": fields["published_total"],
            "raw": raw_values,
            "categories": categories,
            "fra_at": _fra_at(raw_values),
            "applicable_raw_columns": [
                k for k in RAW_COLUMNS if raw_values[k] is not None
            ],
            "component_sum": component_sum,
            "residual": residual,
        }
    expected_years = [str(y) for y in range(1998, edition)]
    if any(list(rows) != expected_years for rows in data.values()):
        raise ValueError(f"Expected complete 1998-{edition - 1} coverage")
    if len(notes) != 8:
        raise ValueError("Unexpected table footnotes")
    return {
        "title": " ".join(parser.caption.split()),
        "data": data,
        "notes": notes,
    }


def build(inputs: Path | None = None) -> dict[Path, bytes]:
    """Reparse both supplied editions and build deterministic output bytes."""
    captures = {y: read_source(y, inputs) for y in SOURCE_SHA256}
    tables = {y: parse_table(raw, y) for y, raw in captures.items()}
    chosen = tables[2026]
    notes = chosen["notes"]
    sources = {
        str(y): {
            "source_url": f"https://www.ssa.gov/policy/docs/statcomps/supplement/{y}/6b.html",
            "source_sha256": SOURCE_SHA256[y],
            "committed_source": f"data/external/{source_name(y)}",
            "retrieved_utc": CAPTURED_UTC,
            "locator": "div#table6.b5.1; thead/tbody/tfoot",
            "bytes": len(captures[y]),
            "compression": "gzip mtime=0; SHA-256 is of decompressed captured bytes",
        }
        for y in captures
    }
    provenance = {
        "source": "SSA Annual Statistical Supplement 2026, Table 6.B5.1",
        **sources["2026"],
        "fetch_method": "Supplied local captures; no network fetch by this builder. SSA baseline captures used User-Agent Wget/1.21.4; the supplement capture client is not recorded in the supplied retrieval marker.",
        "captures": sources,
        "selection": "2026 edition selected: twelve-column layout matches the 2023 schema; rows through 2025. 2025 edition also re-parsed and its hash recorded.",
        "data_basis": notes[0].removeprefix("SOURCE: "),
        "table_notes": " ".join(notes[1:5]),
        "footnote_a_fra_schedule": notes[5].removeprefix("a. "),
        "footnote_b_disability_conversion": notes[6].removeprefix("b. "),
        "not_applicable_marker": ". . .",
        "contact": "statistics@ssa.gov",
        "consumer_note": "claiming.load_claim_age_reference(path) loads this schema and reference.row accesses all years. Legacy claiming.claim_age_distribution and claim_age_pmf retain their global 2022 cap; a new baseline must resolve against reference.years rather than those legacy convenience functions.",
    }
    eras = _era_mapping()
    eras[-1] = {**eras[-1], "entitlement_years": "2021-2025"}
    residuals = [
        r["residual"]
        for rows in chosen["data"].values()
        for r in rows.values()
    ]
    document = {
        "schema_version": "ssa_claim_ages.v1",
        "table": "6.B5.1",
        "title": chosen["title"].removeprefix("Table 6.B5.1 "),
        "supplement_year": 2026,
        "provenance": provenance,
        "column_schema": {
            "raw_columns": list(RAW_COLUMNS),
            "collapsed_categories": list(COLLAPSED_CATEGORIES),
            "fra_at_note": "Exactly one at-FRA column per row; a subset of age65/age66, never an additional partition member.",
            "disability_conversion_note": "Automatic conversion at FRA, not a voluntary claiming choice.",
            "era_map": eras,
        },
        "fra_schedule": {
            "unit": "months",
            "keyed_by": "year worker attains age 65",
            "birth_year_equivalent": "attain_65_year - 65",
            "schedule": [
                {"attain_65_year_from": y, "fra_months": m}
                for y, m in FRA_MONTHS_BY_ATTAIN_65_YEAR
            ],
            "source": "Table 6.B5.1 footnote a; initial year 1900 is the existing schema's lower-bound sentinel, not a source datum.",
        },
        "validation": {
            "sum_tolerance": SUM_TOLERANCE,
            "max_abs_residual": max(map(abs, residuals)),
            "n_rows": len(residuals),
            "years": "1998-2025",
            "sexes": ["male", "female"],
            "reparsed_editions": [2025, 2026],
        },
        "build": {
            "built_by": "scripts/extract_ssa_claim_ages_2026.py",
            "reproducible": "Exact supplied HTML bytes, no clock or network dependency",
        },
        "data": chosen["data"],
    }
    outputs = {OUT_PATH: document, PROVENANCE_PATH: provenance}
    result = {
        p: (json.dumps(d, indent=2, ensure_ascii=False) + "\n").encode()
        for p, d in outputs.items()
    }
    result.update(
        {
            EXTERNAL / source_name(y): gzip_bytes(raw)
            for y, raw in captures.items()
        }
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--inputs",
        type=Path,
        help="Supplied ssa-supplement directory; default committed captures",
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    outputs = build(args.inputs)
    if args.check:
        stale = [
            str(p.relative_to(ROOT))
            for p, raw in outputs.items()
            if not p.exists() or p.read_bytes() != raw
        ]
        if stale:
            raise SystemExit(f"Stale supplement outputs: {stale}")
        print(
            "Supplement 2026 outputs match re-parsed sources (both editions)"
        )
        return 0
    for path, raw in outputs.items():
        path.write_bytes(raw)
    print(
        f"Wrote Supplement 2026 reference: {hashlib.sha256(outputs[OUT_PATH]).hexdigest()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
