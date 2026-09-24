"""Capture the parameters Track U's income concept reads (plan item U3).

Two captures, each written to ``data/external`` and pinned by SHA-256 in
:mod:`populace_dynamics.estimates.adjusted_poverty`:

* ``--ssi`` writes ``track_u_ssi_parameters.json``: the federal SSI
  benefit rate (individual and couple, monthly) in force on January 1 of
  each income year 2004-2012, the $20 general and $65 earned income
  exclusions, the share of remaining earned income excluded, and the
  individual and couple resource limits.  The values come from the
  policyengine-us parameter files (``gov/ssa/ssi``) of the checkout given
  by ``--pe-us-dir`` (default ``POPULACE_DYNAMICS_PE_US_DIR`` or
  ``~/PolicyEngine/policyengine-us``); the capture records each file's
  SHA-256, the checkout revision and each file's cited reference.  These
  are assumptions for the SSI response rule, not comparator values.
* ``--census-dir DIR`` writes ``census_poverty_thresholds_2004_2012.json``
  from the Census Bureau's threshold spreadsheets for income years
  2004-2012 staged in ``DIR`` as ``thresh04.xlsx`` ... ``thresh12.xlsx``
  (the file names the Census historical thresholds page lists under
  ``https://www2.census.gov/programs-surveys/cps/tables/time-series/
  historical-poverty-thresholds/``).  The spreadsheets were **not**
  downloaded by the builder, so the parser below has been exercised only
  on an invented workbook; the first real capture must be checked by eye
  against the files.  The parser locates rows and columns by their
  printed labels and refuses any layout it does not recognize.

Usage::

    python scripts/capture_track_u_parameters.py --ssi [--pe-us-dir DIR]
    python scripts/capture_track_u_parameters.py --census-dir DIR
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from populace_dynamics.estimates import adjusted_poverty  # noqa: E402

#: Income years the exact-age primary and the pooled row observe.
YEARS: tuple[int, ...] = tuple(range(2004, 2013))
_PE_US_ENV = "POPULACE_DYNAMICS_PE_US_DIR"
_PE_US_DEFAULT = Path("~/PolicyEngine/policyengine-us").expanduser()
_SSI_ROOT = Path("policyengine_us/parameters/gov/ssa/ssi")
SSI_FILES: dict[str, Path] = {
    "fbr_individual": _SSI_ROOT / "amount" / "individual.yaml",
    "fbr_couple": _SSI_ROOT / "amount" / "couple.yaml",
    "general_income_exclusion": _SSI_ROOT
    / "income"
    / "exclusions"
    / "general.yaml",
    "earned_income_exclusion": _SSI_ROOT
    / "income"
    / "exclusions"
    / "earned.yaml",
    "earned_income_share_excluded": _SSI_ROOT
    / "income"
    / "exclusions"
    / "earned_share.yaml",
    "resource_limit_individual": _SSI_ROOT
    / "eligibility"
    / "resources"
    / "limit"
    / "individual.yaml",
    "resource_limit_couple": _SSI_ROOT
    / "eligibility"
    / "resources"
    / "limit"
    / "couple.yaml",
}
CENSUS_URL_BASE = (
    "https://www2.census.gov/programs-surveys/cps/tables/time-series/"
    "historical-poverty-thresholds/"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def resolve_pe_us(pe_us_dir: Path | None) -> Path:
    if pe_us_dir is not None:
        return Path(pe_us_dir).expanduser()
    env = os.environ.get(_PE_US_ENV)
    return Path(env).expanduser() if env else _PE_US_DEFAULT


def _in_force(values: dict[Any, Any], year: int) -> float:
    """The value of a dated parameter in force on January 1 of ``year``."""

    dated = sorted(
        (dt.date.fromisoformat(str(key)), float(value))
        for key, value in values.items()
    )
    start = dt.date(year, 1, 1)
    eligible = [value for date, value in dated if date <= start]
    if not eligible:
        raise ValueError(f"no value in force on {start}")
    return eligible[-1]


def build_ssi_capture(pe_us_dir: Path | None = None) -> dict[str, Any]:
    root = resolve_pe_us(pe_us_dir).resolve()
    documents: dict[str, dict[str, Any]] = {}
    hashes: dict[str, str] = {}
    references: dict[str, list[dict[str, str]]] = {}
    for name, relative in SSI_FILES.items():
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(f"policyengine-us file missing: {path}")
        hashes[str(relative)] = _sha256(path)
        documents[name] = yaml.safe_load(path.read_text())
        references[name] = [
            {"title": ref.get("title", ""), "href": ref.get("href", "")}
            for ref in documents[name].get("metadata", {}).get("reference", [])
        ]
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        revision = "unknown"

    def year_map(name: str) -> dict[str, float]:
        return {
            str(year): _in_force(documents[name]["values"], year)
            for year in YEARS
        }

    def constant(name: str) -> float:
        values = {_in_force(documents[name]["values"], year) for year in YEARS}
        if len(values) != 1:
            raise ValueError(f"{name} changes within {YEARS[0]}-{YEARS[-1]}")
        return values.pop()

    return {
        "schema_version": adjusted_poverty.SSI_SCHEMA_VERSION,
        "description": (
            "Federal SSI parameters for the Track U SSI response rules "
            "(exercise 2; Python income concept, not Axiom): the federal "
            "benefit rate in force on January 1 of each income year, the "
            "general and earned income exclusions and the resource limits"
        ),
        "years": [YEARS[0], YEARS[-1]],
        "source": {
            "policyengine_us_revision": revision,
            "policyengine_us_files_sha256": hashes,
            "references": references,
            "rule": "value in force on January 1 of the income year",
            "generated_by": "scripts/capture_track_u_parameters.py --ssi",
        },
        "federal_benefit_rate_monthly": {
            "individual": year_map("fbr_individual"),
            "couple": year_map("fbr_couple"),
        },
        "general_income_exclusion_monthly": constant(
            "general_income_exclusion"
        ),
        "earned_income_exclusion_monthly": constant("earned_income_exclusion"),
        "earned_income_share_excluded": constant(
            "earned_income_share_excluded"
        ),
        "resource_limit": {
            "individual": constant("resource_limit_individual"),
            "couple": constant("resource_limit_couple"),
        },
    }


# ---------------------------------------------------------------------------
# Census thresholds
# ---------------------------------------------------------------------------
_ROW_LABELS: dict[str, str] = {
    "under 65 years": "under_65",
    "65 years and over": "65_plus",
    "householder under 65 years": "under_65",
    "householder 65 years and over": "65_plus",
}
_SIZE_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
}
_CHILD_HEADERS = {
    "none": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight or more": 8,
}


def _clean(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.replace("…", " ").replace(".", " ")
    return " ".join(text.lower().split())


def _number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    text = str(value).replace(",", "").replace("$", "").strip()
    if not text or not re.fullmatch(r"\d+(\.\d+)?", text):
        return None
    return float(text)


def parse_threshold_rows(
    rows: list[list[Any]], year: int
) -> dict[str, dict[str, Any]]:
    """Parse one year's threshold table from its cell rows.

    Returns ``{"weighted_average": {row_key: value}, "matrix": {row_key:
    {children: value}}, "title": str}``.  Refuses a table whose title
    does not name ``year``, whose header lacks the weighted-average or
    children columns, or which misses any of the eleven rows.
    """

    title = next(
        (
            " ".join(str(cell).split())
            for row in rows
            for cell in row
            if cell is not None
            and re.search(rf"poverty thresholds for {year}\b", _clean(cell))
        ),
        None,
    )
    if title is None:
        raise ValueError(f"no 'Poverty Thresholds for {year}' title found")
    header_index = None
    weighted_col = None
    child_cols: dict[int, int] = {}
    for index, row in enumerate(rows):
        cleaned = [_clean(cell) for cell in row]
        if any(cell.startswith("weighted") for cell in cleaned):
            weighted_col = next(
                i
                for i, cell in enumerate(cleaned)
                if cell.startswith("weighted")
            )
            for scan in range(index, min(index + 4, len(rows))):
                for i, cell in enumerate(_clean(c) for c in rows[scan]):
                    if cell in _CHILD_HEADERS:
                        child_cols.setdefault(_CHILD_HEADERS[cell], i)
            header_index = index
            break
    if header_index is None or weighted_col is None:
        raise ValueError(f"{year}: no weighted-average header row")
    if sorted(child_cols) != list(range(9)):
        raise ValueError(
            f"{year}: children columns {sorted(child_cols)} != 0-8"
        )
    weighted: dict[str, float] = {}
    matrix: dict[str, dict[int, float]] = {}
    current_size: int | None = None
    for row in rows[header_index + 1 :]:
        if not row:
            continue
        label = _clean(row[0])
        size_match = re.match(
            r"^(one|two|three|four|five|six|seven|eight|nine)"
            r" (person|people|persons)",
            label,
        )
        key: str | None = None
        if size_match:
            current_size = _SIZE_WORDS[size_match.group(1)]
            if current_size >= 3:
                key = (
                    "nine_plus"
                    if current_size == 9
                    else {
                        3: "three",
                        4: "four",
                        5: "five",
                        6: "six",
                        7: "seven",
                        8: "eight",
                    }[current_size]
                )
        elif label in _ROW_LABELS and current_size in (1, 2):
            prefix = "one" if current_size == 1 else "two"
            key = f"{prefix}_{_ROW_LABELS[label]}"
        if key is None:
            continue
        value = _number(row[weighted_col]) if weighted_col < len(row) else None
        if value is None:
            raise ValueError(f"{year}: row {label!r} has no weighted average")
        weighted[key] = value
        matrix[key] = {
            children: number
            for children, col in child_cols.items()
            if col < len(row) and (number := _number(row[col])) is not None
        }
    missing = set(adjusted_poverty.THRESHOLD_ROW_KEYS) - set(weighted)
    if missing:
        raise ValueError(f"{year}: rows missing {sorted(missing)}")
    _validate_year(year, weighted, matrix)
    return {"weighted_average": weighted, "matrix": matrix, "title": title}


def _validate_year(
    year: int,
    weighted: dict[str, float],
    matrix: dict[str, dict[int, float]],
) -> None:
    for size in ("one", "two"):
        if not weighted[f"{size}_65_plus"] < weighted[f"{size}_under_65"]:
            raise ValueError(
                f"{year}: 65-and-over threshold not below under-65 ({size})"
            )
    larger = ["three", "four", "five", "six", "seven", "eight", "nine_plus"]
    chain = [weighted["two_under_65"], *(weighted[key] for key in larger)]
    if any(b <= a for a, b in zip(chain, chain[1:], strict=False)):
        raise ValueError(f"{year}: weighted averages not increasing in size")
    expected_columns = {
        "one_under_65": [0],
        "one_65_plus": [0],
        "two_under_65": [0, 1],
        "two_65_plus": [0, 1],
        **{
            key: list(range(min(size - 1, 8) + 1))
            for key, size in zip(larger, range(3, 10), strict=True)
        },
    }
    for key, columns in expected_columns.items():
        if sorted(matrix[key]) != columns:
            raise ValueError(
                f"{year}: matrix row {key} has children columns "
                f"{sorted(matrix[key])}, expected {columns}"
            )


def read_workbook_rows(path: Path) -> tuple[str, list[list[Any]]]:
    import openpyxl

    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        sheet = workbook.worksheets[0]
        rows = [list(row) for row in sheet.iter_rows(values_only=True)]
        return sheet.title, rows
    finally:
        workbook.close()


def build_threshold_capture(census_dir: Path) -> dict[str, Any]:
    census_dir = Path(census_dir)
    weighted: dict[str, Any] = {}
    matrix: dict[str, Any] = {}
    sources: dict[str, Any] = {}
    for year in YEARS:
        name = f"thresh{year % 100:02d}.xlsx"
        path = census_dir / name
        if not path.is_file():
            raise FileNotFoundError(f"missing Census file {path}")
        sheet, rows = read_workbook_rows(path)
        parsed = parse_threshold_rows(rows, year)
        weighted[str(year)] = parsed["weighted_average"]
        matrix[str(year)] = {
            key: {str(k): v for k, v in cells.items()}
            for key, cells in parsed["matrix"].items()
        }
        sources[str(year)] = {
            "file": name,
            "url": CENSUS_URL_BASE + name,
            "sha256": _sha256(path),
            "bytes": path.stat().st_size,
            "sheet": sheet,
            "title": parsed["title"],
        }
    return {
        "schema_version": adjusted_poverty.THRESHOLDS_SCHEMA_VERSION,
        "description": (
            "U.S. Census Bureau poverty thresholds for income years "
            "2004-2012: weighted averages by family size (with the "
            "under-65 and 65-and-over rows for one and two persons) and "
            "the size-by-related-children matrix"
        ),
        "sources": sources,
        "generated_by": "scripts/capture_track_u_parameters.py --census-dir",
        "weighted_average": weighted,
        "matrix": matrix,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ssi", action="store_true")
    parser.add_argument("--pe-us-dir", type=Path, default=None)
    parser.add_argument("--census-dir", type=Path, default=None)
    parser.add_argument(
        "--ssi-output", type=Path, default=adjusted_poverty.SSI_PARAMETERS_PATH
    )
    parser.add_argument(
        "--census-output", type=Path, default=adjusted_poverty.THRESHOLDS_PATH
    )
    args = parser.parse_args(argv)
    if not args.ssi and args.census_dir is None:
        parser.error("pass --ssi and/or --census-dir")
    if args.ssi:
        capture = build_ssi_capture(args.pe_us_dir)
        args.ssi_output.write_text(
            json.dumps(capture, indent=2) + "\n", encoding="utf-8"
        )
        print(args.ssi_output, _sha256(args.ssi_output))
    if args.census_dir is not None:
        capture = build_threshold_capture(args.census_dir)
        args.census_output.write_text(
            json.dumps(capture, indent=2) + "\n", encoding="utf-8"
        )
        print(args.census_output, _sha256(args.census_output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
