"""Rebuild intermediate TR2026 baseline inputs from pinned captured sources.

Only the specific input tables V.C1, V.B1, VI.G1, V.A1 and V.A4 are
parsed; no cost, income or balance table is transcribed. Captures were made
2026-10-01 with the Wget/1.21.4 user agent. HTML digests identify captured
bytes, not stable live pages. ``--check`` reparses every source, verifies
its capture digest and compares every generated artifact without writing.
The raw CSV/PDF sources under 2 MB are retained (gzip mtime=0 for CSVs
above 500 KB); HTML is identified by URL and capture SHA-256 only.

Usage: PYTHONPATH=src python scripts/extract_tr2026_parameters.py
       --input-dir /path/to/captured/baseline-inputs [--check]
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import re
import sys
from collections.abc import Sequence
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from populace_dynamics.data.life_table import life_expectancy_profile

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "external" / "tr2026"
DEFAULT_INPUT_DIR = (
    Path.home()
    / "microcosm-launch-evidence"
    / "nasi-meeting-20261001"
    / "followup"
    / "inputs"
    / "baseline-inputs"
)
RETRIEVED = "2026-10-01"
RELEASED = "2026-06-09"

# Digests from the capture SHA256SUMS.txt; keys are capture-relative paths.
SOURCE_SHA256: dict[str, str] = {
    "tr2026/V_C_prog.html": "b6af98b6e8f131ef17b3208ef0fbfb8f9fbc494bc6d33dbee5c1bcbbfc99d93a",
    "tr2026/lr5b1.html": "f1e1347ac2e9013d53a517e0acf05e692660113acd6cbe7554f0efd7c1aaa3a4",
    "tr2026/lr6g1.html": "2e0214278e0b2271616093af02280277f6e363d112c47a90b49fe7168e795e75",
    "tr2026/lr5a1.html": "7476bb5e9e99a04bd1b7e77afd6f367c4f94d6eb9aff74e33724b5db9d1dc357",
    "tr2026/lr5a4.html": "ab45c5e84253cea122ba0f8a284335d03a5819051914422f5980412822a2b919",
    "oact_downloadables_tr2026/DeathProbsE_M_Hist_TR2026.csv": "ee423873ef2b532fc53c97312a9d6162b876f56e50bd227d45f6c9d9a1cefc8f",
    "oact_downloadables_tr2026/DeathProbsE_M_Alt2_TR2026.csv": "4e2a632a964fadb4cc3fe6127a97ef656eafd43348bf8c7408b018b83840db27",
    "oact_downloadables_tr2026/DeathProbsE_F_Hist_TR2026.csv": "1e2ecd7d24233310108da582ae922c53205d1d239ce3a484ecc5fd6cdb88d0c8",
    "oact_downloadables_tr2026/DeathProbsE_F_Alt2_TR2026.csv": "e3178487512f23666ca05754246798557275bc0728f3f937bbca97358f32532b",
    "oact_downloadables_tr2026/PerLifeTables_M_Hist_TR2026.csv": "bcf123b13a107e3a5d55a3e47e5129b470624e047346171cf1ee3a0a1542d1a5",
    "oact_downloadables_tr2026/PerLifeTables_M_Alt2_TR2026.csv": "0d3f38d38d7428e286bb00ae5a318df4eb100e2c801e1487a0410c2f917bc938",
    "oact_downloadables_tr2026/PerLifeTables_F_Hist_TR2026.csv": "a5e71b5a5011468e87b6c0407d60eef956039eb09524c94a3cc5bf6cf165ab97",
    "oact_downloadables_tr2026/PerLifeTables_F_Alt2_TR2026.csv": "80f612185a269069d097fc32b52ba8f65cb24e5605c2201068d4ca414728bef8",
    "oact_downloadables_tr2026/LifeTableDefinitions.pdf": "94c8fd5806cdb5be3762d1284155e4827a2971d3845088943e3f96a14f26e889",
}

TABLE_LOCATORS = {
    "V_C_prog.html": (
        "V.C1",
        "Table V.C1, anchor #1047210; historical and Intermediate rows",
    ),
    "lr5b1.html": (
        "V.B1",
        "Single-year V.B1; historical and Intermediate; final CPI column",
    ),
    "lr6g1.html": (
        "VI.G1",
        "Single-year VI.G1; historical and Intermediate; AWI and adjusted CPI",
    ),
    "lr5a1.html": (
        "V.A1",
        "Single-year V.A1; historical and Intermediate; TFR and ASADR",
    ),
    "lr5a4.html": (
        "V.A4",
        "Single-year V.A4; historical table and first alternative in projected table",
    ),
}


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _gzip(raw: bytes) -> bytes:
    """Deterministic across Python versions: fixed timestamp, no filename."""
    buffer = io.BytesIO()
    with gzip.GzipFile(
        filename="", mode="wb", fileobj=buffer, mtime=0
    ) as stream:
        stream.write(raw)
    return buffer.getvalue()


def _read(input_dir: Path, name: str) -> bytes:
    raw = (input_dir / name).read_bytes()
    observed = _sha256(raw)
    if observed != SOURCE_SHA256[name]:
        raise ValueError(f"capture sha256 mismatch for {name}: {observed}")
    return raw


class TableRows(HTMLParser):
    """Collect cells from an already selected input table."""

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self.row: list[str] | None = None
        self.cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th"):
            self.cell = []

    def handle_data(self, data: str) -> None:
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th") and self.cell is not None:
            if self.row is None:
                raise ValueError("table cell outside a row")
            value = " ".join("".join(self.cell).split())
            if value:
                self.row.append(value)
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None


def _table_rows(table: str) -> list[list[str]]:
    parser = TableRows()
    parser.feed(table)
    return parser.rows


def _tables(raw: bytes) -> list[str]:
    return re.findall(
        r"<table\b[^>]*>.*?</table>", raw.decode("utf-8"), re.I | re.S
    )


def _number(text: str) -> float:
    matches = re.findall(r"[-+]?(?:\d[\d,]*\.?\d*|\.\d+)", text)
    if len(matches) != 1:
        raise ValueError(f"expected one numeric table cell, got {text!r}")
    return float(matches[0].replace(",", ""))


def _year(text: str) -> int | None:
    match = re.fullmatch(r"(\d{4})(?:\s+[a-z])?", text)
    return int(match.group(1)) if match else None


def _section_rows(raw: bytes, *, vc1: bool = False) -> list[list[Any]]:
    tables = _tables(raw)
    if vc1:
        selected = [table for table in tables if "Table V.C1" in table]
        if len(selected) != 1:
            raise ValueError("expected exactly one V.C1 input table")
        table = selected[0]
    else:
        table = max(tables, key=len)
    section = None
    out = []
    for cells in _table_rows(table):
        if not cells:
            continue
        if cells[0] == "Historical data:":
            section = "historical"
            continue
        if cells[0] == "Intermediate:":
            section = "intermediate"
            continue
        if cells[0] in ("Low-cost:", "High-cost:"):
            break
        year = _year(cells[0])
        if year is not None and section in ("historical", "intermediate"):
            out.append([year, section, *cells[1:]])
    return out


def _coverage(rows: list[list[Any]], first: int, last: int) -> None:
    years = [row[0] for row in rows]
    if years != list(range(first, last + 1)):
        raise ValueError(
            f"table lacks unique consecutive {first}..{last} rows"
        )


def parse_parameters(raws: dict[str, bytes]) -> dict[str, Any]:
    """Transcribe only the published input columns, preserving units."""
    vc1 = _section_rows(raws["tr2026/V_C_prog.html"], vc1=True)
    vb1 = _section_rows(raws["tr2026/lr5b1.html"])
    g1 = _section_rows(raws["tr2026/lr6g1.html"])
    a1 = _section_rows(raws["tr2026/lr5a1.html"])
    for rows, first, last in (
        (vc1, 1975, 2035),
        (vb1, 1960, 2100),
        (g1, 1970, 2100),
        (a1, 1940, 2100),
    ):
        _coverage(rows, first, last)
    expectancy = []
    for table in _tables(raws["tr2026/lr5a4.html"]):
        for cells in _table_rows(table):
            if cells and (year := _year(cells[0])) is not None:
                if len(cells) not in (5, 13):
                    raise ValueError("V.A4 expectancy layout changed")
                expectancy.append([year, *map(_number, cells[1:5])])
    _coverage(expectancy, 1940, 2100)
    return {
        "schema_version": "tr2026_parameters.v1",
        "release_date": RELEASED,
        "alternative": "intermediate",
        "tables": {
            "V.C1": {
                "source_file": "V_C_prog.html",
                "columns": ["year", "section", "cola_percent", "awi"],
                "rows": [
                    [y, s, _number(c), _number(w)] for y, s, c, w, *_ in vc1
                ],
            },
            "V.B1": {
                "source_file": "lr5b1.html",
                "columns": ["year", "section", "cpiw_growth_percent"],
                "rows": [[r[0], r[1], _number(r[-1])] for r in vb1],
            },
            "VI.G1": {
                "source_file": "lr6g1.html",
                "columns": ["year", "section", "awi", "adjusted_cpi_2026_100"],
                "rows": [
                    [y, s, _number(w), _number(c)] for y, s, c, w, *_ in g1
                ],
            },
            "V.A1": {
                "source_file": "lr5a1.html",
                "columns": [
                    "year",
                    "section",
                    "tfr",
                    "total",
                    "under_65",
                    "65_and_over",
                ],
                "cell_footnotes": {
                    str(row[0]): {
                        column: cell.split()[0]
                        for column, cell in zip(
                            ("tfr", "total", "under_65", "65_and_over"),
                            row[2:],
                            strict=True,
                        )
                        if re.match(r"^[def]\s", cell)
                    }
                    for row in a1
                    if any(re.match(r"^[def]\s", cell) for cell in row[2:])
                },
                "asadr_unit": "deaths per 100000; April 1 2010 standard population",
                "rows": [[r[0], r[1], *map(_number, r[2:])] for r in a1],
            },
            "V.A4": {
                "source_file": "lr5a4.html",
                "columns": [
                    "year",
                    "male_birth",
                    "female_birth",
                    "male_65",
                    "female_65",
                ],
                "rows": expectancy,
            },
        },
    }


def _death_rows(raw: bytes, first: int, last: int) -> dict[str, list[float]]:
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"))))
    header = rows[1]
    if header != ["Year", *map(str, range(120))]:
        raise ValueError("DeathProbsE age header changed")
    out = {}
    for row in rows[2:]:
        if not row:
            continue
        year = int(row[0])
        q = list(map(float, row[1:]))
        if len(q) != 120 or any(not 0 <= value <= 1 for value in q):
            raise ValueError(f"invalid q vector for {year}")
        if str(year) in out:
            raise ValueError(f"duplicate mortality year {year}")
        out[str(year)] = q
    if list(map(int, out)) != list(range(first, last + 1)):
        raise ValueError("mortality year coverage changed")
    return out


def _life_rows(raw: bytes) -> dict[str, list[dict[str, str]]]:
    lines = raw.decode("utf-8-sig").splitlines()
    header_index = next(
        i for i, line in enumerate(lines) if line.startswith("Year,x,q(x),")
    )
    rows = csv.DictReader(lines[header_index:])
    out: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        out.setdefault(row["Year"], []).append(row)
    for year, ages in out.items():
        if [int(r["x"]) for r in ages] != list(range(120)):
            raise ValueError(f"life table age coverage changed for {year}")
    return out


def parse_mortality(
    raws: dict[str, bytes],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Preserve published q and derive f0 solely for expectancy checks."""
    result: dict[str, Any] = {
        "schema_version": "tr2026_death_probabilities.v1",
        "age_first": 0,
        "age_last": 119,
        "unit": "one-year probability of death at exact age",
        "f0_rule": "(l0-L0)/(l0*q0) from OACT integer person-years; check-only",
        "sexes": {},
    }
    checks = []
    for sex, code in (("male", "M"), ("female", "F")):
        q_by_year: dict[str, list[float]] = {}
        check_inputs = {}
        for variant, first, last in (
            ("Hist", 1900, 2023),
            ("Alt2", 2024, 2100),
        ):
            q_name = f"oact_downloadables_tr2026/DeathProbsE_{code}_{variant}_TR2026.csv"
            life_name = f"oact_downloadables_tr2026/PerLifeTables_{code}_{variant}_TR2026.csv"
            q_rows = _death_rows(raws[q_name], first, last)
            life_rows = _life_rows(raws[life_name])
            if q_rows.keys() != life_rows.keys():
                raise ValueError("DeathProbsE and PerLifeTables years differ")
            q_by_year.update(q_rows)
            max_error = 0.0
            for year, q in q_rows.items():
                ages = life_rows[year]
                if q != [float(row["q(x)"]) for row in ages]:
                    raise ValueError(f"q columns disagree at {sex} {year}")
                birth = ages[0]
                f0 = (float(birth["l(x)"]) - float(birth["L(x)"])) / (
                    float(birth["l(x)"]) * q[0]
                )
                ex = life_expectancy_profile(q, f0=f0)
                check_inputs[year] = [
                    f0,
                    float(ages[0]["e(x)"]),
                    float(ages[65]["e(x)"]),
                ]
                # OACT's e for extinct lx=0 cohorts is printed as zero.
                errors = [
                    abs(ex[age] - float(ages[age]["e(x)"]))
                    for age in range(110)
                    if float(ages[age]["l(x)"]) > 0
                ]
                max_error = float(max(max_error, max(errors)))
            checks.append(
                {
                    "id": f"{sex}_{variant}_life_table_e0_to_e109",
                    "source": life_name,
                    "years": [first, last],
                    "compared_q_cells": len(q_rows) * 120,
                    "max_absolute_expectancy_error_years": max_error,
                    "tolerance_years": 0.006,
                    "passed": max_error <= 0.006,
                }
            )
        result["sexes"][sex] = {
            "q": q_by_year,
            "check_inputs_f0_e0_e65": check_inputs,
        }
    return result, checks


def _source_records(raws: dict[str, bytes]) -> dict[str, Any]:
    records = {}
    for relative, raw in raws.items():
        name = Path(relative).name
        stored = None
        if name.endswith((".csv", ".pdf", ".xlsx")) and len(raw) < 2_000_000:
            stored = "sources/" + name + (".gz" if len(raw) > 500_000 else "")
        if name in TABLE_LOCATORS:
            table, locator = TABLE_LOCATORS[name]
            url = "https://www.ssa.gov/oact/TR/2026/" + name
            if table == "V.C1":
                url += "#1047210"
            role = table
        else:
            url = "https://www.ssa.gov/OACT/Downloadables/" + (
                name if name == "LifeTableDefinitions.pdf" else "CY/" + name
            )
            locator = (
                "Life-table function definitions and separation factor at age zero"
                if name.endswith(".pdf")
                else (
                    "Header Year,0..119; one row per year"
                    if name.startswith("DeathProbs")
                    else "Header line 5; Year,x,q(x),l(x),d(x),L(x),T(x),e(x),...; ages 0..119"
                )
            )
            role = (
                "q"
                if name.startswith("DeathProbs")
                else (
                    "life_table_definitions"
                    if name.endswith(".pdf")
                    else "life_table_check"
                )
            )
        records[name] = {
            "capture_relative_path": relative,
            "original_url": url,
            "sha256": SOURCE_SHA256[relative],
            "bytes": len(raw),
            "retrieved": RETRIEVED,
            "locator": locator,
            "role": role,
            "committed_file": stored,
            "compression": (
                "gzip mtime=0; hash identifies decompressed bytes"
                if stored and stored.endswith(".gz")
                else None
            ),
            "durable_downloadables_locator": (
                "https://www.ssa.gov/OACT/Downloadables/2026/TR2026.html"
                if relative.startswith("oact_")
                else None
            ),
        }
    return {
        "schema_version": "tr2026_sources.v1",
        "fetch_method": "Captured with curl User-Agent Wget/1.21.4; browser User-Agent received Akamai 403. No fetch performed by this builder.",
        "html_hash_policy": "Live HTML contains per-request Akamai markup; pin captured bytes and parsed JSON values, not future live HTML.",
        "sources": records,
    }


def build_all(input_dir: Path) -> dict[str, bytes]:
    """Reparse every pinned capture and return deterministic artifacts."""
    raws = {name: _read(input_dir, name) for name in SOURCE_SHA256}
    parameters = parse_parameters(raws)
    mortality, checks = parse_mortality(raws)
    expectancy = {
        str(row[0]): row[1:] for row in parameters["tables"]["V.A4"]["rows"]
    }
    for sex, birth_index, age65_index in (("male", 0, 2), ("female", 1, 3)):
        data = mortality["sexes"][sex]
        errors = []
        life_errors = []
        for year, inputs in data["check_inputs_f0_e0_e65"].items():
            f0, e0, e65 = inputs
            ex = life_expectancy_profile(data["q"][year], f0=f0)
            life_errors.extend(
                (float(abs(ex[0] - e0)), float(abs(ex[65] - e65)))
            )
            if year in expectancy:
                published = expectancy[year]
                errors.extend(
                    (
                        float(abs(ex[0] - published[birth_index])),
                        float(abs(ex[65] - published[age65_index])),
                    )
                )
        checks.extend(
            [
                {
                    "id": f"{sex}_q_reproduces_V_A4",
                    "years": [1940, 2100],
                    "ages": [0, 65],
                    "max_absolute_error_years": max(errors),
                    "tolerance_years": 0.051,
                    "passed": max(errors) <= 0.051,
                },
                {
                    "id": f"{sex}_q_reproduces_PerLifeTables_e0_e65",
                    "years": [1900, 2100],
                    "ages": [0, 65],
                    "max_absolute_error_years": max(life_errors),
                    "tolerance_years": 0.006,
                    "passed": max(life_errors) <= 0.006,
                },
            ]
        )
    vc1 = {row[0]: row[3] for row in parameters["tables"]["V.C1"]["rows"]}
    g1 = {row[0]: row[2] for row in parameters["tables"]["VI.G1"]["rows"]}
    checks.append(
        {
            "id": "V_C1_AWI_equals_VI_G1",
            "years": [1975, 2035],
            "compared_cells": len(vc1),
            "passed": all(g1[y] == amount for y, amount in vc1.items()),
        }
    )
    sources = _source_records(raws)
    transcription = {
        "schema_version": "tr2026_transcription_check.v1",
        "all_passed": all(c["passed"] for c in checks),
        "checks": checks,
        "source_capture_sha256": {
            Path(n).name: h for n, h in SOURCE_SHA256.items()
        },
        "reparse_check": "--check verifies capture hashes, rebuilds every JSON and compares exact bytes; no network required",
        "rounding": "V.A4 printed to 0.1 years; PerLifeTables e to 0.01; f0 inferred from integer L0. Tail rule is documented in data.life_table.",
        "q119": "Preserved exactly; OACT does not force q119 to 1. No terminal-age replacement or clipping.",
    }
    if not transcription["all_passed"]:
        raise ValueError(
            f"transcription checks failed: {[c for c in checks if not c['passed']]}"
        )
    outputs = {
        "tr2026_parameters.json": _json_bytes(parameters),
        "tr2026_death_probabilities.json": _json_bytes(mortality),
        "transcription_check.json": _json_bytes(transcription),
        "sources.json": _json_bytes(sources),
    }
    for record in sources["sources"].values():
        name = record["committed_file"]
        if name:
            raw = raws[record["capture_relative_path"]]
            outputs[name] = _gzip(raw) if name.endswith(".gz") else raw
    return outputs


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Reparse and compare; write nothing",
    )
    args = parser.parse_args(argv)
    outputs = build_all(args.input_dir)
    if args.check:
        stale = [
            name
            for name, raw in outputs.items()
            if not (OUT_DIR / name).exists()
            or (OUT_DIR / name).read_bytes() != raw
        ]
        if stale:
            print(f"stale TR2026 outputs: {stale}", file=sys.stderr)
            return 1
        print(
            f"TR2026: {len(outputs)} artifacts reproduced from {len(SOURCE_SHA256)} pinned captures"
        )
        return 0
    for name, raw in outputs.items():
        path = OUT_DIR / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    print(f"TR2026: wrote {len(outputs)} deterministic artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
