"""Verify the SSA source evidence for a possible vintage-2 target artifact.

This entry-11 extraction is deliberately offline.  It reuses the entry-10
capture verifier and HTML parser and reads only committed source bytes.  The
Table 4.B2 and Table 4.B11 extraction is complete, but the committed bytes do
not resolve the registration-required V-B7 worker-share universe or all
worker-membership cases.  Consequently this module deliberately cannot emit
the append-only vintage-2 authority.

The committed source rows cited by the ratified design are:

* Table 4.B2: header lines 964-995, 1968 row lines 1254-1266, and
  2014 row lines 1944-1956.
* Table 4.B11: header lines 14838-14861, 1968 row lines 15118-15127,
  and 2014 row lines 15670-15679.
* Table 4.B1: header lines 41-65 and definitions at lines 929-947.
* Trustees Table IV.B4: caption/header lines 242-291 and covered-worker
  definition at lines 4913-4915.
* Trustees Table VI.G1: caption/header lines 240-287 and taxable-payroll
  definition at lines 4566-4570.
* Tables 4.B10 and 4.B12: 2023 all-area worker totals and their CWHS,
  preliminary, and unduplicated-count notes.

Table 4.B1's published reported-taxable percentage is an earnings-dollar
share, not the worker-incidence ratio frozen by sections 3.1 and 6.2.  A
cross-publication worker-count construction also fails: the Trustees
denominator does not establish the required duplicate-worker and membership
rules, and the resulting displayed-count ratio exceeds one in many years.
VI.G1's payroll-to-GDP ratio and IV.B4's worker/beneficiary ratios are not
worker-incidence shares.  The 2023 4.B10 OASDI-worker/4.B12 HI-worker quotient
is synthesized, preliminary, outside every registered role, and lacks an HI
model-denominator analogue.
The exact adjudication is returned by :func:`vb7_adjudication`.

Run from the repository root::

    python scripts/build_ssa_covered_earnings_calibration_targets.py
"""

from __future__ import annotations

import copy
import hashlib
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path, PurePosixPath
from typing import Any

import build_ssa_level_anchors as entry10

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = (
    ROOT
    / "data"
    / "external"
    / "ssa_covered_earnings_calibration_targets_vintage2.json"
)

SCHEMA_VERSION = "ssa_covered_earnings_calibration_targets.v1"
ARTIFACT_VINTAGE_ID = "ssa_covered_earnings_calibration_targets.vintage2"
ARTIFACT_ROLE = "official_calibration_target_source_only"
YEAR_BASIS = "calendar_year"
REQUIRED_CALENDAR_YEARS = tuple(range(1968, 2023))
COVERED_SHARE_REQUIRED_YEARS: tuple[int, ...] = ()
CANONICALIZATION = "python-json-sort-keys-compact-ascii-no-nan-lf-v1"

# Replaced with the first coherent builder commit before the artifact is
# committed.  Keeping the pin literal makes an offline rebuild independent of
# the current checkout's HEAD.
EXTRACTION_IMPLEMENTATION_COMMIT = "14efbded2b6d02bbfe0014a7b059068a733a1e11"

SOURCE_DOCUMENT_ID = "ssa_supplement_2025_4b"
SOURCE_FILENAME = "supplement2025_4b.html"
SOURCE_PUBLICATION = "Annual Statistical Supplement, 2025"
SOURCE_EDITION = "2025"
SOURCE_URL = (
    "https://www.ssa.gov/policy/docs/statcomps/supplement/2025/4b.html"
)
SOURCE_COMMITTED_PATH = (
    "data/external/snapshots/ssa_level_anchors_vintage1/"
    "supplement2025_4b.html"
)
SOURCE_CAPTURE_MANIFEST_PATH = (
    "data/external/snapshots/ssa_level_anchors_vintage1/"
    "capture_manifest.txt"
)
SOURCE_SHA256 = (
    "c228920ea9d53b1e323e5933b6d9f926e3c9b609d868b549fabc40118554b449"
)
SOURCE_SIZE_BYTES = 488_165
SOURCE_RETRIEVED_AT_UTC = "2026-07-27T13:02:54Z"
SOURCE_CAPTURE_MANIFEST_ENTRY = (
    f"{SOURCE_RETRIEVED_AT_UTC} {SOURCE_SHA256} "
    f"{SOURCE_SIZE_BYTES} {SOURCE_FILENAME}"
)

TRUSTEES_COVERED_WORKERS_DOCUMENT_ID = "ssa_trustees_2026_lr4b4"
TRUSTEES_COVERED_WORKERS_FILENAME = "trustees2026_lr4b4.html"
TRUSTEES_COVERED_WORKERS_SHA256 = (
    "40435030d154e29eb49a4e411b78253f504049eddff6e149d7e33033fb139458"
)
TRUSTEES_COVERED_WORKERS_SIZE_BYTES = 133_558
TRUSTEES_VI_G1_DOCUMENT_ID = "ssa_trustees_2026_lr6g1"
TRUSTEES_VI_G1_FILENAME = "trustees2026_lr6g1.html"
TRUSTEES_VI_G1_SHA256 = (
    "3b9e96be991d5a102d41ede443e157d2d1a2a928174430497dc9c3a1fa532dc0"
)
TRUSTEES_VI_G1_SIZE_BYTES = 226_685
TABLE4_B1_CAPTION = (
    "Table 4.B1 Number of workers with Social Security (OASDI) taxable "
    "earnings and amount of earnings, selected years 1937\u20132024"
)
TRUSTEES_IV_B4_CAPTION = (
    "Table IV.B4.\u2014Covered Workers and Beneficiaries, Calendar Years "
    "1945-2100"
)
TRUSTEES_VI_G1_CAPTION = (
    "Table VI.G1.\u2014Selected Economic Variables, Calendar Years 1970-2100 "
    "[GDP and taxable payroll in billions]"
)
TABLE4_B10_CAPTION = (
    "Table 4.B10 Number of workers with Social Security (OASDI) taxable "
    "earnings, amount taxable, and contributions, by state or other area and "
    "type of earnings, 2023"
)
TABLE4_B12_CAPTION = (
    "Table 4.B12 Number of workers with Medicare Part A (HI) taxable "
    "earnings, amount taxable, and contributions, by state or other area and "
    "type of earnings, 2023"
)
TABLE4_B1_PERCENTAGE_HEADER = (
    "Earnings",
    "Reported taxable a",
    "Percentage of total",
)
TABLE4_B1_TOTAL_WORKERS_HEADER = ("Number a (thousands)", "Total")
TRUSTEES_COVERED_WORKERS_HEADER = ("Covered workers a (in thousands)",)
TRUSTEES_WORKERS_PER_BENEFICIARY_HEADER = (
    "Covered workers per OASDI beneficiary",
)
TRUSTEES_BENEFICIARIES_PER_100_WORKERS_HEADER = (
    "OASDI beneficiaries per 100 covered workers",
)
TRUSTEES_VI_G1_PAYROLL_GDP_RATIO_HEADER = ("Ratio of taxable payroll to GDP",)
TABLE4_B10_B12_TOTAL_WORKERS_HEADER = (
    "Number b (thousands)",
    "Total",
)


class RegistrationAborted(ValueError):
    """Committed bytes do not satisfy a registration-required design law."""


ROUNDING_NOT_ESTABLISHED = {
    "status": "not_established_from_source_bytes",
    "lower": None,
    "upper": None,
    "lower_closed": None,
    "upper_closed": None,
    "rule_source_document_id": None,
    "rule_citation": None,
}


@dataclass(frozen=True)
class TableSpec:
    """One exact reviewed Supplement table identity."""

    table_id: str
    table_title: str
    exact_caption: str
    preliminary_note: str


TABLE_SPECS = (
    TableSpec(
        table_id="table4.b2",
        table_title=(
            "Number of workers with Social Security (OASDI) taxable "
            "earnings and amount of earnings, by type of earnings, "
            "1951\u20132024"
        ),
        exact_caption=(
            "Table 4.B2 Number of workers with Social Security (OASDI) "
            "taxable earnings and amount of earnings, by type of earnings, "
            "1951\u20132024"
        ),
        preliminary_note="e. Preliminary data.",
    ),
    TableSpec(
        table_id="table4.b11",
        table_title=(
            "Number of workers with Social Security (OASDI) taxable "
            "earnings, amount taxable, and contributions, by type of "
            "earnings, selected years 1937\u20132024"
        ),
        exact_caption=(
            "Table 4.B11 Number of workers with Social Security (OASDI) "
            "taxable earnings, amount taxable, and contributions, by type "
            "of earnings, selected years 1937\u20132024"
        ),
        preliminary_note="e. Preliminary data.",
    ),
)
TABLE_SPEC_BY_ID = {spec.table_id: spec for spec in TABLE_SPECS}


@dataclass(frozen=True)
class ComponentSpec:
    """One frozen source component and its exact nested header path."""

    table_id: str
    component_id: str
    nested_column_header_path: tuple[str, ...]
    published_unit: str
    stored_unit: str
    scale: int
    html_header_id: str | None = None


THOUSANDS_OF_PERSONS = "thousands_of_persons"
PERSONS = "persons"
MILLIONS_OF_CURRENT_DOLLARS = "millions_of_current_dollars"
CURRENT_DOLLARS = "current_dollars"

TABLE4_B2_COMPONENT_SPECS = (
    ComponentSpec(
        table_id="table4.b2",
        component_id="c5",
        nested_column_header_path=(
            "Wage and salary",
            "Total in covered employment b (millions of dollars)",
        ),
        published_unit=MILLIONS_OF_CURRENT_DOLLARS,
        stored_unit=CURRENT_DOLLARS,
        scale=1_000_000,
        html_header_id="c5",
    ),
    ComponentSpec(
        table_id="table4.b2",
        component_id="c8",
        nested_column_header_path=(
            "Self-employed",
            "Total in covered employment d (millions of dollars)",
        ),
        published_unit=MILLIONS_OF_CURRENT_DOLLARS,
        stored_unit=CURRENT_DOLLARS,
        scale=1_000_000,
        html_header_id="c8",
    ),
    ComponentSpec(
        table_id="table4.b2",
        component_id="c11",
        nested_column_header_path=(
            "Number a (thousands)",
            "Wage and salary",
        ),
        published_unit=THOUSANDS_OF_PERSONS,
        stored_unit=PERSONS,
        scale=1_000,
        html_header_id="c11",
    ),
    ComponentSpec(
        table_id="table4.b2",
        component_id="c12",
        nested_column_header_path=(
            "Number a (thousands)",
            "Self- employed",
        ),
        published_unit=THOUSANDS_OF_PERSONS,
        stored_unit=PERSONS,
        scale=1_000,
        html_header_id="c12",
    ),
    ComponentSpec(
        table_id="table4.b2",
        component_id="c13",
        nested_column_header_path=(
            "Wage and salary",
            "Reported taxable",
            "Amount c (millions of dollars)",
        ),
        published_unit=MILLIONS_OF_CURRENT_DOLLARS,
        stored_unit=CURRENT_DOLLARS,
        scale=1_000_000,
        html_header_id="c13",
    ),
    ComponentSpec(
        table_id="table4.b2",
        component_id="c17",
        nested_column_header_path=(
            "Self-employed",
            "Reported taxable",
            "Amount c (millions of dollars)",
        ),
        published_unit=MILLIONS_OF_CURRENT_DOLLARS,
        stored_unit=CURRENT_DOLLARS,
        scale=1_000_000,
        html_header_id="c17",
    ),
)

TABLE4_B11_COMPONENT_SPECS = (
    ComponentSpec(
        table_id="table4.b11",
        component_id="workers_total",
        nested_column_header_path=("Number a (thousands)", "Total"),
        published_unit=THOUSANDS_OF_PERSONS,
        stored_unit=PERSONS,
        scale=1_000,
    ),
    ComponentSpec(
        table_id="table4.b11",
        component_id="workers_wage",
        nested_column_header_path=(
            "Number a (thousands)",
            "Wage and salary",
        ),
        published_unit=THOUSANDS_OF_PERSONS,
        stored_unit=PERSONS,
        scale=1_000,
    ),
    ComponentSpec(
        table_id="table4.b11",
        component_id="workers_self_employment",
        nested_column_header_path=(
            "Number a (thousands)",
            "Self- employed",
        ),
        published_unit=THOUSANDS_OF_PERSONS,
        stored_unit=PERSONS,
        scale=1_000,
    ),
    ComponentSpec(
        table_id="table4.b11",
        component_id="taxable_earnings_total",
        nested_column_header_path=(
            "Taxable earnings b (millions of dollars)",
            "Total",
        ),
        published_unit=MILLIONS_OF_CURRENT_DOLLARS,
        stored_unit=CURRENT_DOLLARS,
        scale=1_000_000,
    ),
    ComponentSpec(
        table_id="table4.b11",
        component_id="taxable_earnings_wage",
        nested_column_header_path=(
            "Taxable earnings b (millions of dollars)",
            "Wage and salary",
        ),
        published_unit=MILLIONS_OF_CURRENT_DOLLARS,
        stored_unit=CURRENT_DOLLARS,
        scale=1_000_000,
    ),
    ComponentSpec(
        table_id="table4.b11",
        component_id="taxable_earnings_self_employment",
        nested_column_header_path=(
            "Taxable earnings b (millions of dollars)",
            "Self- employed",
        ),
        published_unit=MILLIONS_OF_CURRENT_DOLLARS,
        stored_unit=CURRENT_DOLLARS,
        scale=1_000_000,
    ),
    ComponentSpec(
        table_id="table4.b11",
        component_id="contributions_total",
        nested_column_header_path=(
            "OASDI contributions c,d (millions of dollars)",
            "Total",
        ),
        published_unit=MILLIONS_OF_CURRENT_DOLLARS,
        stored_unit=CURRENT_DOLLARS,
        scale=1_000_000,
    ),
    ComponentSpec(
        table_id="table4.b11",
        component_id="contributions_wage",
        nested_column_header_path=(
            "OASDI contributions c,d (millions of dollars)",
            "Wage and salary",
        ),
        published_unit=MILLIONS_OF_CURRENT_DOLLARS,
        stored_unit=CURRENT_DOLLARS,
        scale=1_000_000,
    ),
    ComponentSpec(
        table_id="table4.b11",
        component_id="contributions_self_employment",
        nested_column_header_path=(
            "OASDI contributions c,d (millions of dollars)",
            "Self- employed",
        ),
        published_unit=MILLIONS_OF_CURRENT_DOLLARS,
        stored_unit=CURRENT_DOLLARS,
        scale=1_000_000,
    ),
)

COMPONENT_SPECS_BY_TABLE = {
    "table4.b2": TABLE4_B2_COMPONENT_SPECS,
    "table4.b11": TABLE4_B11_COMPONENT_SPECS,
}

ADJUDICATION = (
    "preserve_both_use_registered_table_specific_selector_never_average"
)
COARSER_DISPLAY = "coarser_display_pattern_rounding_rule_unverified"
LITERAL_CONFLICT = "literal_source_conflict_not_display_precision"

# These literals are the complete reviewed unequal-cell set in the ratified
# design.  The builder independently scans all four overlapping primitives
# for every common 1951-2024 row and requires exact equality to this tuple.
EXPECTED_CROSS_TABLE_DISCREPANCIES = (
    (1968, "SE taxable amount", "27,340", "27,300", COARSER_DISPLAY),
    (1969, "SE taxable amount", "27,540", "27,500", COARSER_DISPLAY),
    (1970, "SE taxable amount", "26,920", "26,900", COARSER_DISPLAY),
    (1971, "SE taxable amount", "27,410", "27,400", COARSER_DISPLAY),
    (1972, "SE taxable amount", "32,060", "32,100", COARSER_DISPLAY),
    (1974, "SE taxable amount", "42,360", "42,400", COARSER_DISPLAY),
    (1975, "SE taxable amount", "43,560", "43,600", COARSER_DISPLAY),
    (1977, "SE taxable amount", "52,950", "53,000", COARSER_DISPLAY),
    (1985, "Wage-worker count", "113,100", "113,400", LITERAL_CONFLICT),
    (1992, "SE taxable amount", "146,600", "146,900", LITERAL_CONFLICT),
)

OVERLAPPING_PRIMITIVES = (
    ("Wage-worker count", "c11", "workers_wage"),
    ("SE-worker count", "c12", "workers_self_employment"),
    (
        "Wage taxable amount",
        "c13",
        "taxable_earnings_wage",
    ),
    (
        "SE taxable amount",
        "c17",
        "taxable_earnings_self_employment",
    ),
)

OBSERVATION_KEYS = {
    "as_published",
    "calendar_year",
    "nested_column_header_path",
    "normalized_value",
    "published_rounding_interval",
    "published_unit",
    "row_path",
    "scale",
    "source_cell_id",
    "source_document_id",
    "source_sha256",
    "status",
    "stored_unit",
    "table_id",
    "table_title",
}


def _source_cell_id(table_id: str, year: int, component_id: str) -> str:
    return f"{table_id}/{year}/{component_id}"


def _required_source_cell_ids() -> dict[str, list[str]]:
    return {
        "table4_b2": [
            _source_cell_id(spec.table_id, year, spec.component_id)
            for year in REQUIRED_CALENDAR_YEARS
            for spec in TABLE4_B2_COMPONENT_SPECS
        ],
        "table4_b11": [
            _source_cell_id(spec.table_id, year, spec.component_id)
            for year in REQUIRED_CALENDAR_YEARS
            for spec in TABLE4_B11_COMPONENT_SPECS
        ],
        "ssa_covered_share": [],
    }


def _footer_text(table: Any) -> tuple[str, ...]:
    return tuple(
        cell.text
        for row in table.rows
        if row.section == "tfoot"
        for cell in row.cells
    )


def _select_tables(raw: bytes) -> dict[str, Any]:
    parsed = entry10._parse_tables(raw, SOURCE_DOCUMENT_ID)
    selected: dict[str, Any] = {}
    for spec in TABLE_SPECS:
        matches = [
            table for table in parsed if table.caption == spec.exact_caption
        ]
        if len(matches) != 1:
            raise ValueError(
                f"expected exactly one literal {spec.table_id} caption "
                f"{spec.exact_caption!r}, found {len(matches)}"
            )
        table = matches[0]
        footer = _footer_text(table)
        if not any(spec.preliminary_note in text for text in footer):
            raise ValueError(
                f"{spec.table_id} preliminary-status evidence "
                f"{spec.preliminary_note!r} not found"
            )
        selected[spec.table_id] = table

    b11_footer = _footer_text(selected["table4.b11"])
    required_b11_notes = (
        "NOTES: Totals do not necessarily equal the sum of rounded "
        "components.",
        (
            "a. Workers with earnings in both wage and salary employment "
            "and self-employment are counted in each type of employment but "
            "only once in the total."
        ),
    )
    for note in required_b11_notes:
        if not any(note in text for text in b11_footer):
            raise ValueError(f"table4.b11 structural note {note!r} not found")
    return selected


def _all_year_rows(table: Any) -> dict[int, tuple[str, list[Any]]]:
    """Index every exact year row, including 4.B2's scope-less row headers."""
    body_rows = [row for row in table.rows if row.section == "tbody"]
    grid = entry10._expand_rows(body_rows)
    indexed: dict[int, tuple[str, list[Any]]] = {}
    for source_row, expanded_row in zip(body_rows, grid, strict=True):
        if not source_row.cells:
            continue
        first = source_row.cells[0]
        if first.tag != "th":
            continue
        match = re.fullmatch(
            r"(?P<year>\d{4})(?: [a-z](?:,[a-z])*)?", first.text
        )
        if match is None:
            continue
        year = int(match.group("year"))
        if year in indexed:
            raise ValueError(f"duplicate source year row {year}")
        if first.rowspan != 1 or first.colspan != 1:
            raise ValueError(
                f"source year {year} did not resolve to a physical 1x1 "
                "row header"
            )
        indexed[year] = (first.text, expanded_row)
    return indexed


def _select_one_captioned_table(
    raw: bytes,
    *,
    source_document_id: str,
    exact_caption: str,
) -> tuple[Any, tuple[Any, ...]]:
    parsed = entry10._parse_tables(raw, source_document_id)
    matches = [table for table in parsed if table.caption == exact_caption]
    if len(matches) != 1:
        raise ValueError(
            f"{source_document_id} caption {exact_caption!r} selected "
            f"{len(matches)} tables"
        )
    return matches[0], parsed


def _select_one_parsed_table(
    tables: Sequence[Any],
    *,
    source_document_id: str,
    exact_caption: str,
) -> Any:
    matches = [table for table in tables if table.caption == exact_caption]
    if len(matches) != 1:
        raise ValueError(
            f"{source_document_id} caption {exact_caption!r} selected "
            f"{len(matches)} parsed tables"
        )
    return matches[0]


def _unique_column(table: Any, header_path: tuple[str, ...]) -> int:
    matches = [
        index
        for index, path in enumerate(entry10._column_header_paths(table))
        if path == header_path
    ]
    if len(matches) != 1:
        raise ValueError(
            f"header path {header_path!r} selected {len(matches)} columns"
        )
    return matches[0]


def _trustees_year_rows(table: Any) -> dict[int, tuple[str, list[Any]]]:
    body_rows = [row for row in table.rows if row.section == "tbody"]
    grid = entry10._expand_rows(body_rows)
    indexed: dict[int, tuple[str, list[Any]]] = {}
    row_group: str | None = None
    for source_row, expanded_row in zip(body_rows, grid, strict=True):
        nonempty = [cell for cell in source_row.cells if cell.text]
        if (
            len(nonempty) == 1
            and nonempty[0].tag == "th"
            and nonempty[0].colspan > 1
        ):
            row_group = nonempty[0].text
            continue
        row_headers = [
            cell
            for cell in source_row.cells
            if cell.attributes.get("scope") == "row"
        ]
        if len(row_headers) != 1 or row_group != "Historical data:":
            continue
        row_header = row_headers[0]
        match = re.fullmatch(r"(?P<year>\d{4})(?: [a-z])?", row_header.text)
        if match is None:
            continue
        if row_header.rowspan != 1 or row_header.colspan != 1:
            raise ValueError(
                f"Trustees row {row_header.text!r} is not a physical 1x1 cell"
            )
        year = int(match.group("year"))
        if year in indexed:
            raise ValueError(f"duplicate Trustees source year {year}")
        indexed[year] = (row_header.text, expanded_row)
    return indexed


def _unique_stub_row(table: Any, *, stub_text: str) -> list[Any]:
    body_rows = [row for row in table.rows if row.section == "tbody"]
    grid = entry10._expand_rows(body_rows)
    matches: list[list[Any]] = []
    for source_row, expanded_row in zip(body_rows, grid, strict=True):
        row_headers = [
            cell
            for cell in source_row.cells
            if cell.attributes.get("scope") == "row" and cell.text == stub_text
        ]
        if not row_headers:
            continue
        if len(row_headers) != 1:
            raise ValueError(
                f"{table.caption} has duplicate {stub_text!r} row headers"
            )
        row_header = row_headers[0]
        if row_header.rowspan != 1 or row_header.colspan != 1:
            raise ValueError(
                f"{table.caption} {stub_text!r} is not a physical 1x1 cell"
            )
        matches.append(expanded_row)
    if len(matches) != 1:
        raise ValueError(
            f"{table.caption} selected {len(matches)} {stub_text!r} rows"
        )
    return matches[0]


def _selected_literal(
    row: Sequence[Any],
    column: int,
    *,
    where: str,
) -> str:
    if column >= len(row) or row[column] is None:
        raise ValueError(f"{where} has no physical source cell")
    cell = row[column]
    if (
        cell.tag != "td"
        or cell.rowspan != 1
        or cell.colspan != 1
        or not cell.text
    ):
        raise ValueError(f"{where} did not select a literal physical 1x1 cell")
    return cell.text


def _source_fragment(
    tables: Sequence[Any],
    *,
    required_text: str,
    source_document_id: str,
) -> str:
    matches = [
        cell.text
        for table in tables
        for row in table.rows
        for cell in row.cells
        if required_text in cell.text
    ]
    if len(matches) != 1:
        raise ValueError(
            f"{source_document_id} definition {required_text!r} selected "
            f"{len(matches)} fragments"
        )
    return matches[0]


def _parse_decimal_cell(literal: str, *, where: str) -> Fraction:
    if not re.fullmatch(r"(?:\d+(?:\.\d+)?|\.\d+)", literal):
        raise ValueError(f"{where} literal {literal!r} is not a decimal")
    whole, separator, fraction = literal.partition(".")
    if not separator:
        return Fraction(int(whole), 1)
    return Fraction(int(whole + fraction), 10 ** len(fraction))


def _fraction_decimal(value: Fraction, *, places: int) -> str:
    if value < 0 or places < 1:
        raise ValueError(
            "fraction decimal renderer requires nonnegative value"
        )
    scale = 10**places
    quotient, remainder = divmod(value.numerator * scale, value.denominator)
    if remainder * 2 >= value.denominator:
        quotient += 1
    return f"{quotient // scale}.{quotient % scale:0{places}d}"


def _verified_vb7_inputs() -> dict[str, Any]:
    entries, raw_by_document_id = entry10.read_verified_snapshots()
    supplement_raw = raw_by_document_id[SOURCE_DOCUMENT_ID]
    trustees_raw = raw_by_document_id[TRUSTEES_COVERED_WORKERS_DOCUMENT_ID]
    trustees_vi_g1_raw = raw_by_document_id[TRUSTEES_VI_G1_DOCUMENT_ID]
    if (
        hashlib.sha256(supplement_raw).hexdigest() != SOURCE_SHA256
        or len(supplement_raw) != SOURCE_SIZE_BYTES
    ):
        raise ValueError(
            "Supplement source identity drift before V-B7 parsing"
        )
    if (
        hashlib.sha256(trustees_raw).hexdigest()
        != TRUSTEES_COVERED_WORKERS_SHA256
        or len(trustees_raw) != TRUSTEES_COVERED_WORKERS_SIZE_BYTES
    ):
        raise ValueError("Trustees source identity drift before V-B7 parsing")
    if (
        hashlib.sha256(trustees_vi_g1_raw).hexdigest() != TRUSTEES_VI_G1_SHA256
        or len(trustees_vi_g1_raw) != TRUSTEES_VI_G1_SIZE_BYTES
    ):
        raise ValueError("Trustees VI.G1 identity drift before V-B7 parsing")

    supplement_entry = entries[SOURCE_DOCUMENT_ID]
    trustees_entry = entries[TRUSTEES_COVERED_WORKERS_DOCUMENT_ID]
    trustees_vi_g1_entry = entries[TRUSTEES_VI_G1_DOCUMENT_ID]
    if (
        supplement_entry.filename != SOURCE_FILENAME
        or trustees_entry.filename != TRUSTEES_COVERED_WORKERS_FILENAME
        or trustees_vi_g1_entry.filename != TRUSTEES_VI_G1_FILENAME
    ):
        raise ValueError("V-B7 capture-manifest filename drift")

    b1, supplement_tables = _select_one_captioned_table(
        supplement_raw,
        source_document_id=SOURCE_DOCUMENT_ID,
        exact_caption=TABLE4_B1_CAPTION,
    )
    trustees, trustees_tables = _select_one_captioned_table(
        trustees_raw,
        source_document_id=TRUSTEES_COVERED_WORKERS_DOCUMENT_ID,
        exact_caption=TRUSTEES_IV_B4_CAPTION,
    )
    trustees_vi_g1, trustees_vi_g1_tables = _select_one_captioned_table(
        trustees_vi_g1_raw,
        source_document_id=TRUSTEES_VI_G1_DOCUMENT_ID,
        exact_caption=TRUSTEES_VI_G1_CAPTION,
    )
    table4_b10 = _select_one_parsed_table(
        supplement_tables,
        source_document_id=SOURCE_DOCUMENT_ID,
        exact_caption=TABLE4_B10_CAPTION,
    )
    table4_b12 = _select_one_parsed_table(
        supplement_tables,
        source_document_id=SOURCE_DOCUMENT_ID,
        exact_caption=TABLE4_B12_CAPTION,
    )
    return {
        "b1": b1,
        "supplement_tables": supplement_tables,
        "trustees": trustees,
        "trustees_tables": trustees_tables,
        "trustees_vi_g1": trustees_vi_g1,
        "trustees_vi_g1_tables": trustees_vi_g1_tables,
        "table4_b10": table4_b10,
        "table4_b12": table4_b12,
    }


def vb7_adjudication() -> dict[str, Any]:
    """Adjudicate every committed-byte V-B7 candidate without minting v2."""

    inputs = _verified_vb7_inputs()
    b1 = inputs["b1"]
    trustees = inputs["trustees"]
    trustees_vi_g1 = inputs["trustees_vi_g1"]
    table4_b10 = inputs["table4_b10"]
    table4_b12 = inputs["table4_b12"]
    b1_rows = _all_year_rows(b1)
    trustees_rows = _trustees_year_rows(trustees)
    trustees_vi_g1_rows = _trustees_year_rows(trustees_vi_g1)
    vi_g1_required_years = tuple(range(1970, 2023))
    missing_b1 = sorted(set(REQUIRED_CALENDAR_YEARS) - set(b1_rows))
    missing_trustees = sorted(
        set(REQUIRED_CALENDAR_YEARS) - set(trustees_rows)
    )
    missing_vi_g1 = sorted(
        set(vi_g1_required_years) - set(trustees_vi_g1_rows)
    )
    if missing_b1 or missing_trustees or missing_vi_g1:
        raise ValueError(
            "V-B7 candidate source years missing: "
            f"4.B1={missing_b1}, IV.B4={missing_trustees}, "
            f"VI.G1={missing_vi_g1}"
        )

    percentage_column = _unique_column(b1, TABLE4_B1_PERCENTAGE_HEADER)
    b1_workers_column = _unique_column(b1, TABLE4_B1_TOTAL_WORKERS_HEADER)
    trustees_workers_column = _unique_column(
        trustees, TRUSTEES_COVERED_WORKERS_HEADER
    )
    trustees_workers_per_beneficiary_column = _unique_column(
        trustees,
        TRUSTEES_WORKERS_PER_BENEFICIARY_HEADER,
    )
    trustees_beneficiaries_per_100_workers_column = _unique_column(
        trustees,
        TRUSTEES_BENEFICIARIES_PER_100_WORKERS_HEADER,
    )
    trustees_vi_g1_ratio_column = _unique_column(
        trustees_vi_g1,
        TRUSTEES_VI_G1_PAYROLL_GDP_RATIO_HEADER,
    )

    percentages: dict[int, str] = {}
    count_pairs: dict[int, tuple[str, str]] = {}
    workers_per_beneficiary: dict[int, str] = {}
    beneficiaries_per_100_workers: dict[int, str] = {}
    comparisons = {"above_one": 0, "below_one": 0, "equal_one": 0}
    for year in REQUIRED_CALENDAR_YEARS:
        percentage = _selected_literal(
            b1_rows[year][1],
            percentage_column,
            where=f"table4.b1/{year}/reported_taxable_percentage",
        )
        _parse_decimal_cell(
            percentage,
            where=f"table4.b1/{year}/reported_taxable_percentage",
        )
        percentages[year] = percentage

        numerator = _selected_literal(
            b1_rows[year][1],
            b1_workers_column,
            where=f"table4.b1/{year}/workers_total",
        )
        denominator = _selected_literal(
            trustees_rows[year][1],
            trustees_workers_column,
            where=f"trustees.iv.b4/{year}/covered_workers",
        )
        numerator_value = entry10._parse_integer_cell(
            numerator, where=f"table4.b1/{year}/workers_total"
        )
        denominator_value = entry10._parse_integer_cell(
            denominator, where=f"trustees.iv.b4/{year}/covered_workers"
        )
        if denominator_value <= 0:
            raise ValueError(
                f"Trustees covered-worker denominator {year} <= 0"
            )
        ratio = Fraction(numerator_value, denominator_value)
        comparison = (
            "above_one"
            if ratio > 1
            else "below_one" if ratio < 1 else "equal_one"
        )
        comparisons[comparison] += 1
        count_pairs[year] = (numerator, denominator)

        workers_per_beneficiary_literal = _selected_literal(
            trustees_rows[year][1],
            trustees_workers_per_beneficiary_column,
            where=f"trustees.iv.b4/{year}/workers_per_beneficiary",
        )
        beneficiaries_per_100_workers_literal = _selected_literal(
            trustees_rows[year][1],
            trustees_beneficiaries_per_100_workers_column,
            where=f"trustees.iv.b4/{year}/beneficiaries_per_100_workers",
        )
        _parse_decimal_cell(
            workers_per_beneficiary_literal,
            where=f"trustees.iv.b4/{year}/workers_per_beneficiary",
        )
        _parse_decimal_cell(
            beneficiaries_per_100_workers_literal,
            where=f"trustees.iv.b4/{year}/beneficiaries_per_100_workers",
        )
        workers_per_beneficiary[year] = workers_per_beneficiary_literal
        beneficiaries_per_100_workers[year] = (
            beneficiaries_per_100_workers_literal
        )

    vi_g1_ratios: dict[int, str] = {}
    for year in vi_g1_required_years:
        literal = _selected_literal(
            trustees_vi_g1_rows[year][1],
            trustees_vi_g1_ratio_column,
            where=f"trustees.vi.g1/{year}/taxable_payroll_to_gdp",
        )
        _parse_decimal_cell(
            literal,
            where=f"trustees.vi.g1/{year}/taxable_payroll_to_gdp",
        )
        vi_g1_ratios[year] = literal

    table4_b10_total_column = _unique_column(
        table4_b10,
        TABLE4_B10_B12_TOTAL_WORKERS_HEADER,
    )
    table4_b12_total_column = _unique_column(
        table4_b12,
        TABLE4_B10_B12_TOTAL_WORKERS_HEADER,
    )
    table4_b10_total = _selected_literal(
        _unique_stub_row(table4_b10, stub_text="All areas"),
        table4_b10_total_column,
        where="table4.b10/2023/all_areas/workers_total",
    )
    table4_b12_total = _selected_literal(
        _unique_stub_row(table4_b12, stub_text="All areas"),
        table4_b12_total_column,
        where="table4.b12/2023/all_areas/workers_total",
    )
    table4_b10_total_value = entry10._parse_integer_cell(
        table4_b10_total,
        where="table4.b10/2023/all_areas/workers_total",
    )
    table4_b12_total_value = entry10._parse_integer_cell(
        table4_b12_total,
        where="table4.b12/2023/all_areas/workers_total",
    )
    if table4_b12_total_value <= 0:
        raise ValueError("Table 4.B12 2023 all-areas worker total <= 0")
    table4_b10_b12_ratio = Fraction(
        table4_b10_total_value,
        table4_b12_total_value,
    )

    b1_definition = _source_fragment(
        [b1],
        required_text=(
            "Reported taxable earnings include Social Security taxable wages"
        ),
        source_document_id=SOURCE_DOCUMENT_ID,
    )
    b1_total_definition = _source_fragment(
        [b1],
        required_text="Total wages, including estimated amounts above taxable",
        source_document_id=SOURCE_DOCUMENT_ID,
    )
    trustees_definition = _source_fragment(
        inputs["trustees_tables"],
        required_text=(
            "Workers who are paid at some time during the year for employment"
        ),
        source_document_id=TRUSTEES_COVERED_WORKERS_DOCUMENT_ID,
    )
    trustees_workers_per_beneficiary_header = _source_fragment(
        [trustees],
        required_text="Covered workers per OASDI beneficiary",
        source_document_id=TRUSTEES_COVERED_WORKERS_DOCUMENT_ID,
    )
    trustees_beneficiaries_per_100_workers_header = _source_fragment(
        [trustees],
        required_text="OASDI beneficiaries per 100 covered workers",
        source_document_id=TRUSTEES_COVERED_WORKERS_DOCUMENT_ID,
    )
    trustees_vi_g1_definition = _source_fragment(
        inputs["trustees_vi_g1_tables"],
        required_text="Total earnings subject to OASDI contribution rates",
        source_document_id=TRUSTEES_VI_G1_DOCUMENT_ID,
    )
    trustees_vi_g1_ratio_header = _source_fragment(
        [trustees_vi_g1],
        required_text="Ratio of taxable payroll to GDP",
        source_document_id=TRUSTEES_VI_G1_DOCUMENT_ID,
    )

    table4_b10_b12_fragments: dict[str, str] = {}
    for fragment_id, required_text in (
        (
            "cwhs_source",
            (
                "SOURCE: Social Security Administration, Continuous Work "
                "History Sample"
            ),
        ),
        (
            "preliminary_status",
            "NOTES: Data are based on preliminary estimates.",
        ),
        (
            "unduplicated_worker_rule",
            (
                "National and state totals and subtotals are unduplicated "
                "counts of workers in each type of employment."
            ),
        ),
    ):
        b10_fragment = _source_fragment(
            [table4_b10],
            required_text=required_text,
            source_document_id=SOURCE_DOCUMENT_ID,
        )
        b12_fragment = _source_fragment(
            [table4_b12],
            required_text=required_text,
            source_document_id=SOURCE_DOCUMENT_ID,
        )
        if b10_fragment != b12_fragment:
            raise ValueError(
                f"Tables 4.B10/4.B12 {fragment_id} fragments differ"
            )
        table4_b10_b12_fragments[fragment_id] = b10_fragment

    return {
        "schema_version": "ssa_covered_earnings_vb7_adjudication.v1",
        "candidate_constructions": [
            {
                "candidate_id": "table4_b1_reported_taxable_earnings_share",
                "available_years": list(REQUIRED_CALENDAR_YEARS),
                "published_percentage_examples": {
                    "1968": percentages[1968],
                    "2014": percentages[2014],
                },
                "source_definition_fragment_sha256": hashlib.sha256(
                    b1_definition.encode("utf-8")
                ).hexdigest(),
                "source_total_definition_fragment_sha256": hashlib.sha256(
                    b1_total_definition.encode("utf-8")
                ).hexdigest(),
                "established": [
                    "publication_table_vintage",
                    "annual_calendar_year",
                    "oasdi_scope",
                    "same_system_earnings_amount_numerator_denominator",
                    "every_1968_2022_published_percentage",
                ],
                "not_established": [
                    "worker_incidence_numerator_denominator",
                    "worker_duplicate_rule",
                    "exact_worker_universe_model_analogue",
                ],
                "verdict": "reject_earnings_share_is_not_worker_share",
            },
            {
                "candidate_id": (
                    "supplement_workers_with_taxable_earnings_over_"
                    "trustees_covered_workers"
                ),
                "available_years": list(REQUIRED_CALENDAR_YEARS),
                "trustees_definition_fragment_sha256": hashlib.sha256(
                    trustees_definition.encode("utf-8")
                ).hexdigest(),
                "displayed_ratio_comparison_counts": comparisons,
                "example_1978": {
                    "numerator_thousands": count_pairs[1978][0],
                    "denominator_thousands": count_pairs[1978][1],
                },
                "established": [
                    "publication_table_vintages",
                    "annual_calendar_year",
                    "oasdi_scope",
                    "worker_count_units",
                    "every_1968_2022_displayed_count",
                ],
                "not_established": [
                    "same_population_universe_across_publications",
                    "trustees_multiple_job_duplicate_rule",
                    "trustees_dual_type_duplicate_rule",
                    "zero_loss_threshold_cap_membership_equivalence",
                    "source_authorized_cross_publication_reconciliation",
                    "one_as_published_covered_share_observation_per_year",
                ],
                "verdict": (
                    "reject_not_a_source_defined_subset_share_and_universe_"
                    "rules_are_incomplete"
                ),
            },
            {
                "candidate_id": "trustees_vi_g1_taxable_payroll_to_gdp",
                "available_years": list(vi_g1_required_years),
                "source_document_sha256": TRUSTEES_VI_G1_SHA256,
                "published_ratio_examples": {
                    "1970": vi_g1_ratios[1970],
                    "2014": vi_g1_ratios[2014],
                    "2022": vi_g1_ratios[2022],
                },
                "source_definition_fragment_sha256": hashlib.sha256(
                    trustees_vi_g1_definition.encode("utf-8")
                ).hexdigest(),
                "ratio_header_fragment_sha256": hashlib.sha256(
                    trustees_vi_g1_ratio_header.encode("utf-8")
                ).hexdigest(),
                "established": [
                    "publication_table_vintage",
                    "direct_published_taxable_payroll_to_gdp_ratio",
                    "oasdi_taxable_payroll_dollar_numerator",
                    "gdp_dollar_denominator",
                    "calendar_years_1970_2022",
                    "multiple_employer_excess_wage_payroll_adjustment",
                ],
                "not_established": [
                    "worker_incidence_numerator_denominator",
                    "person_or_worker_denominator",
                    "worker_duplicate_rule",
                    "one_as_published_covered_share_observation_per_year",
                    "exact_worker_universe_model_analogue",
                    "1968_1969_source_cells",
                ],
                "verdict": (
                    "reject_payroll_to_gdp_dollar_ratio_is_not_worker_"
                    "incidence_share"
                ),
            },
            {
                "candidate_id": (
                    "trustees_iv_b4_covered_workers_per_oasdi_beneficiary"
                ),
                "available_years": list(REQUIRED_CALENDAR_YEARS),
                "published_ratio_examples": {
                    "1968": workers_per_beneficiary[1968],
                    "1978": workers_per_beneficiary[1978],
                    "2014": workers_per_beneficiary[2014],
                    "2022": workers_per_beneficiary[2022],
                },
                "source_definition_fragment_sha256": hashlib.sha256(
                    trustees_definition.encode("utf-8")
                ).hexdigest(),
                "ratio_header_fragment_sha256": hashlib.sha256(
                    trustees_workers_per_beneficiary_header.encode("utf-8")
                ).hexdigest(),
                "established": [
                    "publication_table_vintage",
                    "direct_published_ratio_cells",
                    "annual_covered_worker_numerator",
                    "june_30_current_payment_beneficiary_denominator",
                    "every_1968_2022_ratio",
                ],
                "not_established": [
                    "worker_incidence_numerator_denominator",
                    "population_universe_denominator",
                    "common_annual_timing_numerator_denominator",
                    "worker_duplicate_rule",
                    "one_as_published_covered_share_observation_per_year",
                    "exact_worker_universe_model_analogue",
                ],
                "verdict": (
                    "reject_beneficiary_burden_ratio_is_not_worker_"
                    "incidence_share"
                ),
            },
            {
                "candidate_id": (
                    "trustees_iv_b4_oasdi_beneficiaries_per_100_"
                    "covered_workers"
                ),
                "available_years": list(REQUIRED_CALENDAR_YEARS),
                "published_ratio_examples": {
                    "1968": beneficiaries_per_100_workers[1968],
                    "1978": beneficiaries_per_100_workers[1978],
                    "2014": beneficiaries_per_100_workers[2014],
                    "2022": beneficiaries_per_100_workers[2022],
                },
                "source_definition_fragment_sha256": hashlib.sha256(
                    trustees_definition.encode("utf-8")
                ).hexdigest(),
                "ratio_header_fragment_sha256": hashlib.sha256(
                    trustees_beneficiaries_per_100_workers_header.encode(
                        "utf-8"
                    )
                ).hexdigest(),
                "established": [
                    "publication_table_vintage",
                    "direct_published_ratio_cells",
                    "june_30_current_payment_beneficiary_numerator",
                    "annual_covered_worker_denominator",
                    "every_1968_2022_ratio",
                ],
                "not_established": [
                    "worker_incidence_numerator_denominator",
                    "population_universe_denominator",
                    "common_annual_timing_numerator_denominator",
                    "worker_duplicate_rule",
                    "one_as_published_covered_share_observation_per_year",
                    "exact_worker_universe_model_analogue",
                ],
                "verdict": (
                    "reject_beneficiary_burden_ratio_is_not_worker_"
                    "incidence_share"
                ),
            },
            {
                "candidate_id": (
                    "supplement_2023_table4_b10_oasdi_workers_over_"
                    "table4_b12_hi_workers"
                ),
                "available_years": [2023],
                "source_document_sha256": SOURCE_SHA256,
                "example_2023": {
                    "numerator_thousands": table4_b10_total,
                    "denominator_thousands": table4_b12_total,
                    "exact_fraction": (
                        f"{table4_b10_b12_ratio.numerator}/"
                        f"{table4_b10_b12_ratio.denominator}"
                    ),
                    "decimal_10_places": _fraction_decimal(
                        table4_b10_b12_ratio,
                        places=10,
                    ),
                },
                "numerator_fragment_sha256": hashlib.sha256(
                    table4_b10_total.encode("utf-8")
                ).hexdigest(),
                "denominator_fragment_sha256": hashlib.sha256(
                    table4_b12_total.encode("utf-8")
                ).hexdigest(),
                "operand_fragment_composite_sha256": hashlib.sha256(
                    table4_b10_total.encode("utf-8")
                    + b"\x00"
                    + table4_b12_total.encode("utf-8")
                ).hexdigest(),
                "cwhs_source_fragment_sha256": hashlib.sha256(
                    table4_b10_b12_fragments["cwhs_source"].encode("utf-8")
                ).hexdigest(),
                "unduplicated_worker_rule_fragment_sha256": hashlib.sha256(
                    table4_b10_b12_fragments[
                        "unduplicated_worker_rule"
                    ].encode("utf-8")
                ).hexdigest(),
                "preliminary_status_fragment_sha256": hashlib.sha256(
                    table4_b10_b12_fragments["preliminary_status"].encode(
                        "utf-8"
                    )
                ).hexdigest(),
                "established": [
                    "same_cwhs_one_percent_source",
                    "unduplicated_national_worker_totals",
                    "2023_calendar_year_worker_counts",
                ],
                "not_established": [
                    "one_as_published_covered_share_observation_per_year",
                    "non_preliminary_status",
                    "any_1968_2022_registered_role_year",
                    "hi_worker_denominator_model_analogue",
                ],
                "verdict": (
                    "reject_synthesized_preliminary_2023_only_quotient_"
                    "without_hi_model_denominator"
                ),
            },
            {
                "candidate_id": "other_committed_same_universe_construction",
                "available_years": [],
                "established": [],
                "not_established": [
                    "a_published_worker_share_with_exact_same_universe_"
                    "numerator_and_denominator"
                ],
                "verdict": "reject_no_committed_source_cell",
            },
        ],
        "worker_membership_relationships": [
            {
                "family": "b2_wage_total_intensity",
                "established": [
                    "c5_total_wages_include_amounts_above_taxable_limit",
                    "c11_is_number_in_wage_and_salary_employment",
                    "dual_type_people_are_included_in_each_type",
                ],
                "not_established": [
                    "zero_and_below_threshold_membership",
                    "multiple_job_duplicate_treatment_for_all_years",
                    "exact_c5_population_equals_c11_population",
                ],
                "verdict": "fail_closed",
            },
            {
                "family": "b2_se_total_intensity",
                "established": [
                    "c8_is_reported_self_employment_net_earnings",
                    "c12_is_number_in_self_employment",
                    "dual_type_people_are_included_in_each_type",
                ],
                "not_established": [
                    "zero_and_loss_only_membership",
                    "below_threshold_and_wage_first_cap_membership",
                    "multiple_component_and_multiple_job_duplicate_treatment",
                    "exact_c8_population_equals_c12_population",
                ],
                "verdict": "fail_closed",
            },
            {
                "family": "b11_worker_distribution",
                "established": [
                    "dual_type_workers_count_in_each_type_once_in_total"
                ],
                "not_established": [
                    "zero_loss_only_below_threshold_and_cap_membership",
                    "multiple_job_and_multiple_component_treatment_all_years",
                ],
                "verdict": "fail_closed",
            },
        ],
        "covered_share_required_years": [],
        "registration_disposition": (
            "abort_no_authoritative_vintage2_or_calibration_target_specs"
        ),
    }


def _component_columns(
    table: Any, specs: Sequence[ComponentSpec]
) -> dict[str, int]:
    header_paths = entry10._column_header_paths(table)
    columns: dict[str, int] = {}
    for spec in specs:
        matches = [
            index
            for index, path in enumerate(header_paths)
            if path == spec.nested_column_header_path
        ]
        if len(matches) != 1:
            raise ValueError(
                f"{spec.table_id}/{spec.component_id} header path "
                f"{spec.nested_column_header_path!r} selected "
                f"{len(matches)} columns"
            )
        columns[spec.component_id] = matches[0]
    if len(set(columns.values())) != len(specs):
        raise ValueError(f"{specs[0].table_id} component columns overlap")
    return columns


def _literal_cell(
    *,
    table_id: str,
    year: int,
    component: ComponentSpec,
    row: Sequence[Any],
    column: int,
) -> Any:
    if column >= len(row) or row[column] is None:
        raise ValueError(
            f"{table_id}/{year}/{component.component_id} has no source cell"
        )
    cell = row[column]
    if cell.rowspan != 1 or cell.colspan != 1:
        raise ValueError(
            f"{table_id}/{year}/{component.component_id} did not resolve "
            "to a unique physical 1x1 data cell "
            f"(rowspan={cell.rowspan}, colspan={cell.colspan})"
        )
    if cell.tag != "td" or not cell.text:
        raise ValueError(
            f"{table_id}/{year}/{component.component_id} selected "
            f"{cell.tag} {cell.text!r}, not a literal data cell"
        )
    if component.html_header_id is not None:
        header_ids = cell.attributes.get("headers", "").split()
        if component.html_header_id not in header_ids:
            raise ValueError(
                f"{table_id}/{year}/{component.component_id} lacks exact "
                f"HTML header identity {component.html_header_id!r}"
            )
    return cell


def _extract_observations(
    tables: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, dict[int, dict[str, str]]]]:
    observations: list[dict[str, Any]] = []
    all_literals: dict[str, dict[int, dict[str, str]]] = {}

    for table_spec in TABLE_SPECS:
        table = tables[table_spec.table_id]
        component_specs = COMPONENT_SPECS_BY_TABLE[table_spec.table_id]
        columns = _component_columns(table, component_specs)
        rows = _all_year_rows(table)
        if not set(range(1951, 2025)).issubset(rows):
            missing = sorted(set(range(1951, 2025)) - set(rows))
            raise ValueError(
                f"{table_spec.table_id} missing overlap rows {missing}"
            )

        table_literals: dict[int, dict[str, str]] = {}
        for year, (row_label, row) in rows.items():
            literals: dict[str, str] = {}
            for component in component_specs:
                cell = _literal_cell(
                    table_id=table_spec.table_id,
                    year=year,
                    component=component,
                    row=row,
                    column=columns[component.component_id],
                )
                # All four overlap series must remain numeric for the complete
                # 1951-2024 discrepancy scan.
                if year >= 1951 and component.component_id in {
                    item for _, *ids in OVERLAPPING_PRIMITIVES for item in ids
                }:
                    entry10._parse_integer_cell(
                        cell.text,
                        where=(
                            f"{table_spec.table_id}/{year}/"
                            f"{component.component_id}"
                        ),
                    )
                literals[component.component_id] = cell.text
            table_literals[year] = literals

            if year not in REQUIRED_CALENDAR_YEARS:
                continue
            expected_row_label = (
                f"{year} e" if year in {2021, 2022} else str(year)
            )
            if row_label != expected_row_label:
                raise ValueError(
                    f"{table_spec.table_id}/{year} row label "
                    f"{row_label!r} != {expected_row_label!r}"
                )
            status = "preliminary" if year in {2021, 2022} else "historical"
            for component in component_specs:
                literal = literals[component.component_id]
                published = entry10._parse_integer_cell(
                    literal,
                    where=(
                        f"{table_spec.table_id}/{year}/"
                        f"{component.component_id}"
                    ),
                )
                observations.append(
                    {
                        "source_cell_id": _source_cell_id(
                            table_spec.table_id,
                            year,
                            component.component_id,
                        ),
                        "source_document_id": SOURCE_DOCUMENT_ID,
                        "table_id": table_spec.table_id,
                        "table_title": table_spec.table_title,
                        "calendar_year": year,
                        "row_path": [row_label],
                        "nested_column_header_path": list(
                            component.nested_column_header_path
                        ),
                        "as_published": literal,
                        "normalized_value": published * component.scale,
                        "published_unit": component.published_unit,
                        "stored_unit": component.stored_unit,
                        "scale": component.scale,
                        "status": status,
                        "published_rounding_interval": copy.deepcopy(
                            ROUNDING_NOT_ESTABLISHED
                        ),
                        "source_sha256": SOURCE_SHA256,
                    }
                )
        all_literals[table_spec.table_id] = table_literals

    return observations, all_literals


def _cross_table_discrepancies(
    literals: Mapping[str, Mapping[int, Mapping[str, str]]],
) -> list[dict[str, Any]]:
    found: list[tuple[int, str, str, str]] = []
    for year in range(1951, 2025):
        for concept, b2_component, b11_component in OVERLAPPING_PRIMITIVES:
            b2_literal = literals["table4.b2"][year][b2_component]
            b11_literal = literals["table4.b11"][year][b11_component]
            b2_value = entry10._parse_integer_cell(
                b2_literal,
                where=f"table4.b2/{year}/{b2_component}",
            )
            b11_value = entry10._parse_integer_cell(
                b11_literal,
                where=f"table4.b11/{year}/{b11_component}",
            )
            if b2_value != b11_value:
                found.append((year, concept, b2_literal, b11_literal))

    expected_values = tuple(
        (year, concept, b2_literal, b11_literal)
        for year, concept, b2_literal, b11_literal, _ in (
            EXPECTED_CROSS_TABLE_DISCREPANCIES
        )
    )
    if tuple(found) != expected_values:
        raise ValueError(
            "cross-table unequal-cell set drift: "
            f"{tuple(found)!r} != {expected_values!r}"
        )

    return _expected_cross_table_discrepancies()


def _expected_cross_table_discrepancies() -> list[dict[str, Any]]:
    """Return the exact ten-row discrepancy registry frozen by §6.1."""

    rows: list[dict[str, Any]] = []
    lookup = {
        (concept, "table4.b2"): b2_component
        for concept, b2_component, _ in OVERLAPPING_PRIMITIVES
    }
    lookup.update(
        {
            (concept, "table4.b11"): b11_component
            for concept, _, b11_component in OVERLAPPING_PRIMITIVES
        }
    )
    for (
        year,
        concept,
        b2_literal,
        b11_literal,
        discrepancy_class,
    ) in EXPECTED_CROSS_TABLE_DISCREPANCIES:
        rows.append(
            {
                "calendar_year": year,
                "concept": concept,
                "table4_b2_source_cell_id": _source_cell_id(
                    "table4.b2",
                    year,
                    lookup[(concept, "table4.b2")],
                ),
                "table4_b2_as_published": b2_literal,
                "table4_b11_source_cell_id": _source_cell_id(
                    "table4.b11",
                    year,
                    lookup[(concept, "table4.b11")],
                ),
                "table4_b11_as_published": b11_literal,
                "discrepancy_class": discrepancy_class,
                "adjudication": ADJUDICATION,
            }
        )
    return rows


def _source_document_manifest(
    entries: Mapping[str, entry10.ManifestEntry],
) -> list[dict[str, Any]]:
    entry = entries[SOURCE_DOCUMENT_ID]
    expected = (
        entry.filename,
        entry.retrieval_timestamp,
        entry.sha256,
        entry.size_bytes,
        entry.literal_entry,
    )
    required = (
        SOURCE_FILENAME,
        SOURCE_RETRIEVED_AT_UTC,
        SOURCE_SHA256,
        SOURCE_SIZE_BYTES,
        SOURCE_CAPTURE_MANIFEST_ENTRY,
    )
    if expected != required:
        raise ValueError(
            f"Supplement capture identity drift: {expected!r} != {required!r}"
        )
    return [
        {
            "source_document_id": SOURCE_DOCUMENT_ID,
            "publication": SOURCE_PUBLICATION,
            "edition": SOURCE_EDITION,
            "table_ids": ["table4.b2", "table4.b11"],
            "url": SOURCE_URL,
            "retrieved_at_utc": SOURCE_RETRIEVED_AT_UTC,
            "committed_path": SOURCE_COMMITTED_PATH,
            "sha256": SOURCE_SHA256,
            "size_bytes": SOURCE_SIZE_BYTES,
            "capture_manifest_path": SOURCE_CAPTURE_MANIFEST_PATH,
            "capture_manifest_entry": SOURCE_CAPTURE_MANIFEST_ENTRY,
        }
    ]


def _content_sha256(artifact: Mapping[str, Any]) -> str:
    preimage = copy.deepcopy(artifact)
    preimage["integrity"]["content_sha256"] = "0" * 64
    return hashlib.sha256(entry10.canonical_json_bytes(preimage)).hexdigest()


def extract_b2_b11_source_evidence() -> dict[str, Any]:
    """Return the complete verified extraction without an artifact identity."""

    entries, raw_by_document_id = entry10.read_verified_snapshots()
    raw = raw_by_document_id[SOURCE_DOCUMENT_ID]
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("Supplement source-byte drift before parsing")
    if len(raw) != SOURCE_SIZE_BYTES:
        raise ValueError("Supplement source-size drift before parsing")
    tables = _select_tables(raw)
    observations, literals = _extract_observations(tables)
    evidence = {
        "required_calendar_years": list(REQUIRED_CALENDAR_YEARS),
        "required_source_cell_ids": {
            key: value
            for key, value in _required_source_cell_ids().items()
            if key != "ssa_covered_share"
        },
        "source_document_manifest": _source_document_manifest(entries),
        "observations": observations,
        "cross_table_discrepancies": _cross_table_discrepancies(literals),
    }
    if len(evidence["observations"]) != 15 * len(REQUIRED_CALENDAR_YEARS):
        raise ValueError("B2/B11 evidence extraction is not exactly 825 cells")
    return evidence


def _validate_rounding_interval(value: Any, where: str) -> None:
    if value != ROUNDING_NOT_ESTABLISHED:
        raise ValueError(f"{where} rounding interval is not source-closed")


def _validate_manifest(manifest: Any) -> None:
    if not isinstance(manifest, list) or len(manifest) != 1:
        raise ValueError(
            "source_document_manifest must contain only the committed "
            "Supplement in this pre-registration extraction unit"
        )
    expected = _source_document_manifest(entry10.read_verified_snapshots()[0])
    if manifest != expected:
        raise ValueError("source_document_manifest identity or order drift")
    document = manifest[0]
    expected_keys = {
        "capture_manifest_entry",
        "capture_manifest_path",
        "committed_path",
        "edition",
        "publication",
        "retrieved_at_utc",
        "sha256",
        "size_bytes",
        "source_document_id",
        "table_ids",
        "url",
    }
    if set(document) != expected_keys:
        raise ValueError("source document fields missing or extra")
    for key, value in document.items():
        if key == "table_ids":
            if value != ["table4.b2", "table4.b11"]:
                raise ValueError("Supplement table_ids drift")
        elif key == "size_bytes":
            if type(value) is not int or value <= 0:
                raise ValueError("source size_bytes is not a positive integer")
        elif not isinstance(value, str) or not value:
            raise ValueError(f"source document {key} is not a nonempty string")
    if not re.fullmatch(r"[0-9a-f]{64}", document["sha256"]):
        raise ValueError("source sha256 is not lowercase hexadecimal")
    if not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",
        document["retrieved_at_utc"],
    ):
        raise ValueError("retrieved_at_utc is not canonical UTC")
    for key in ("committed_path", "capture_manifest_path"):
        path = PurePosixPath(document[key])
        if path.is_absolute() or ".." in path.parts or "." in path.parts:
            raise ValueError(f"{key} is not traversal-free repo-relative")
    manifest_parts = document["capture_manifest_entry"].split(" ")
    if manifest_parts != [
        document["retrieved_at_utc"],
        document["sha256"],
        str(document["size_bytes"]),
        PurePosixPath(document["committed_path"]).name,
    ]:
        raise ValueError(
            "capture manifest entry does not bind source identity"
        )


def _validate_observations(artifact: Mapping[str, Any]) -> None:
    observations = artifact["observations"]
    if not isinstance(observations, list):
        raise ValueError("observations must be an ordered array")
    required = artifact["required_source_cell_ids"]
    expected_ids = required["table4_b2"] + required["table4_b11"]
    observed_ids = [
        observation.get("source_cell_id")
        for observation in observations
        if isinstance(observation, dict)
    ]
    if observed_ids != expected_ids:
        raise ValueError(
            "observations are missing, extra, duplicated, or reordered"
        )
    if len(observations) != 15 * len(REQUIRED_CALENDAR_YEARS):
        raise ValueError("observation count is not the required 825")

    component_by_key = {
        (spec.table_id, spec.component_id): spec
        for specs in COMPONENT_SPECS_BY_TABLE.values()
        for spec in specs
    }
    for observation in observations:
        source_cell_id = observation["source_cell_id"]
        if set(observation) != OBSERVATION_KEYS:
            raise ValueError(
                f"{source_cell_id} observation fields missing or extra"
            )
        parts = source_cell_id.split("/")
        if len(parts) != 3:
            raise ValueError(f"{source_cell_id} has invalid cell-ID grammar")
        table_id, encoded_year, component_id = parts
        if not re.fullmatch(r"\d{4}", encoded_year):
            raise ValueError(f"{source_cell_id} has invalid encoded year")
        year = observation["calendar_year"]
        if type(year) is not int or year != int(encoded_year):
            raise ValueError(f"{source_cell_id} calendar-year equality failed")
        if year not in REQUIRED_CALENDAR_YEARS:
            raise ValueError(
                f"{source_cell_id} year is outside required range"
            )
        spec = component_by_key.get((table_id, component_id))
        if spec is None:
            raise ValueError(f"{source_cell_id} is not a registered component")
        table_spec = TABLE_SPEC_BY_ID[table_id]
        expected_row_label = f"{year} e" if year in {2021, 2022} else str(year)
        expected_values = {
            "source_document_id": SOURCE_DOCUMENT_ID,
            "table_id": table_id,
            "table_title": table_spec.table_title,
            "row_path": [expected_row_label],
            "nested_column_header_path": list(spec.nested_column_header_path),
            "published_unit": spec.published_unit,
            "stored_unit": spec.stored_unit,
            "scale": spec.scale,
            "status": (
                "preliminary" if year in {2021, 2022} else "historical"
            ),
            "source_sha256": SOURCE_SHA256,
        }
        for key, expected in expected_values.items():
            if observation[key] != expected:
                raise ValueError(
                    f"{source_cell_id} {key} drift: "
                    f"{observation[key]!r} != {expected!r}"
                )
        _validate_rounding_interval(
            observation["published_rounding_interval"],
            source_cell_id,
        )
        published = entry10._parse_integer_cell(
            observation["as_published"],
            where=source_cell_id,
        )
        normalized = observation["normalized_value"]
        if (
            type(normalized) is not int
            or not math.isfinite(normalized)
            or normalized != published * spec.scale
        ):
            raise ValueError(f"{source_cell_id} normalized value drift")


def _reresolve_observations_from_sources(
    artifact: Mapping[str, Any],
) -> None:
    """Re-extract each B2/B11 cell and compare the complete observation."""

    expected = extract_b2_b11_source_evidence()
    expected_by_id = {
        row["source_cell_id"]: row for row in expected["observations"]
    }
    for observation in artifact["observations"]:
        source_cell_id = observation["source_cell_id"]
        source_row = expected_by_id.get(source_cell_id)
        if source_row is None:
            raise ValueError(
                f"{source_cell_id} does not resolve to committed source bytes"
            )
        if observation != source_row:
            changed = sorted(
                key
                for key in OBSERVATION_KEYS
                if observation.get(key) != source_row.get(key)
            )
            raise ValueError(
                f"{source_cell_id} does not re-resolve from source bytes; "
                f"changed fields={changed}"
            )


def _validate_cross_table_discrepancies(artifact: Mapping[str, Any]) -> None:
    rows = artifact["cross_table_discrepancies"]
    if not isinstance(rows, list) or len(rows) != 10:
        raise ValueError("cross_table_discrepancies must contain ten rows")
    expected_keys = {
        "adjudication",
        "calendar_year",
        "concept",
        "discrepancy_class",
        "table4_b11_as_published",
        "table4_b11_source_cell_id",
        "table4_b2_as_published",
        "table4_b2_source_cell_id",
    }
    expected_order = [
        (year, concept)
        for year, concept, *_ in EXPECTED_CROSS_TABLE_DISCREPANCIES
    ]
    actual_order = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != expected_keys:
            raise ValueError("cross-table discrepancy fields missing or extra")
        if type(row["calendar_year"]) is not int:
            raise ValueError("cross-table discrepancy year is not an integer")
        if row["adjudication"] != ADJUDICATION:
            raise ValueError("cross-table discrepancy adjudication drift")
        if row["discrepancy_class"] not in {
            COARSER_DISPLAY,
            LITERAL_CONFLICT,
        }:
            raise ValueError("cross-table discrepancy class drift")
        year = row["calendar_year"]
        for key in (
            "table4_b2_source_cell_id",
            "table4_b11_source_cell_id",
        ):
            encoded_year = row[key].split("/")[1]
            if int(encoded_year) != year:
                raise ValueError("cross-table discrepancy year alias detected")
        actual_order.append((year, row["concept"]))
    if actual_order != expected_order:
        raise ValueError("cross-table discrepancies reordered")
    expected_rows = _expected_cross_table_discrepancies()
    if rows != expected_rows:
        raise ValueError(
            "cross-table discrepancy literals, cells, or classes drift"
        )

    observations = {
        row["source_cell_id"]: row for row in artifact["observations"]
    }
    for row in rows:
        for table in ("table4_b2", "table4_b11"):
            source_cell_id = row[f"{table}_source_cell_id"]
            as_published = row[f"{table}_as_published"]
            if observations[source_cell_id]["as_published"] != as_published:
                raise ValueError(
                    f"{source_cell_id} discrepancy literal does not "
                    "resolve to its observation"
                )


def validate_artifact(artifact: Mapping[str, Any]) -> None:
    """Apply the extraction unit's strict §6 schema and cell laws."""
    expected_top_level = {
        "artifact_role",
        "artifact_vintage_id",
        "covered_share_required_years",
        "cross_table_discrepancies",
        "integrity",
        "observations",
        "required_calendar_years",
        "required_source_cell_ids",
        "schema_version",
        "source_document_manifest",
        "year_basis",
    }
    if set(artifact) != expected_top_level:
        raise ValueError("artifact top-level fields missing or extra")
    expected_literals = {
        "schema_version": SCHEMA_VERSION,
        "artifact_vintage_id": ARTIFACT_VINTAGE_ID,
        "artifact_role": ARTIFACT_ROLE,
        "year_basis": YEAR_BASIS,
        "required_calendar_years": list(REQUIRED_CALENDAR_YEARS),
        "covered_share_required_years": [],
        "required_source_cell_ids": _required_source_cell_ids(),
    }
    for key, expected in expected_literals.items():
        if artifact[key] != expected:
            raise ValueError(f"{key} drift")

    _validate_manifest(artifact["source_document_manifest"])
    _validate_observations(artifact)
    _reresolve_observations_from_sources(artifact)
    _validate_cross_table_discrepancies(artifact)

    integrity = artifact["integrity"]
    expected_integrity_keys = {
        "canonicalization",
        "content_sha256",
        "extraction_implementation_commit",
        "reproduced_from_source_bytes",
    }
    if (
        not isinstance(integrity, dict)
        or set(integrity) != expected_integrity_keys
    ):
        raise ValueError("integrity fields missing or extra")
    if integrity["canonicalization"] != CANONICALIZATION:
        raise ValueError("canonicalization law drift")
    if not re.fullmatch(r"[0-9a-f]{64}", integrity["content_sha256"]):
        raise ValueError("content_sha256 is not lowercase hexadecimal")
    if not re.fullmatch(
        r"[0-9a-f]{40}",
        integrity["extraction_implementation_commit"],
    ):
        raise ValueError("extraction implementation commit is invalid")
    if (
        integrity["extraction_implementation_commit"]
        != EXTRACTION_IMPLEMENTATION_COMMIT
    ):
        raise ValueError("extraction implementation commit drift")
    if integrity["reproduced_from_source_bytes"] is not True:
        raise ValueError("artifact is not marked source-byte reproducible")
    expected_content_sha256 = _content_sha256(artifact)
    if integrity["content_sha256"] != expected_content_sha256:
        raise ValueError(
            f"content_sha256 {integrity['content_sha256']} != "
            f"{expected_content_sha256}"
        )
    disposition = vb7_adjudication()["registration_disposition"]
    raise RegistrationAborted(
        "V-B7 and worker-membership authority are unresolved; "
        f"{disposition}"
    )


def build() -> dict[str, Any]:
    """Abort because committed bytes cannot establish the full authority."""

    extract_b2_b11_source_evidence()
    adjudication = vb7_adjudication()
    raise RegistrationAborted(
        "cannot emit ssa_covered_earnings_calibration_targets.vintage2: "
        f"{adjudication['registration_disposition']}"
    )


def render() -> bytes:
    """Abort instead of rendering an incomplete object under the final ID."""

    return entry10.canonical_json_bytes(build())


def main() -> None:
    render()


if __name__ == "__main__":
    main()
