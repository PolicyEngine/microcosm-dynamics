"""Build the vintage-2 SSA covered-earnings calibration-target artifact.

This entry-11 extraction is deliberately offline.  It reuses the entry-10
capture verifier and HTML parser, reads only the committed Supplement bytes,
and extracts the exact Table 4.B2 and Table 4.B11 cells registered in
``docs/design/covered_earnings_correction.md`` section 6.

The committed source rows cited by the ratified design are:

* Table 4.B2: header lines 964-995, 1968 row lines 1254-1266, and
  2014 row lines 1944-1956.
* Table 4.B11: header lines 14838-14861, 1968 row lines 15118-15127,
  and 2014 row lines 15670-15679.

V-B7 covered-share source capture and universe verification are explicitly
registration-time work and are outside this extraction unit.  Until that
authority is registered, both covered-share arrays are therefore empty and
no covered-share source document is synthesized.

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
EXTRACTION_IMPLEMENTATION_COMMIT = "34b8bfdfbce17d39a4a42c586df550278ae209d8"

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
    if integrity["reproduced_from_source_bytes"] is not True:
        raise ValueError("artifact is not marked source-byte reproducible")
    expected_content_sha256 = _content_sha256(artifact)
    if integrity["content_sha256"] != expected_content_sha256:
        raise ValueError(
            f"content_sha256 {integrity['content_sha256']} != "
            f"{expected_content_sha256}"
        )


def build() -> dict[str, Any]:
    """Build and fail-closed validate the complete offline extraction."""
    entries, raw_by_document_id = entry10.read_verified_snapshots()
    raw = raw_by_document_id[SOURCE_DOCUMENT_ID]
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("Supplement source-byte drift before parsing")
    if len(raw) != SOURCE_SIZE_BYTES:
        raise ValueError("Supplement source-size drift before parsing")

    tables = _select_tables(raw)
    observations, literals = _extract_observations(tables)
    artifact: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_vintage_id": ARTIFACT_VINTAGE_ID,
        "artifact_role": ARTIFACT_ROLE,
        "year_basis": YEAR_BASIS,
        "required_calendar_years": list(REQUIRED_CALENDAR_YEARS),
        "required_source_cell_ids": _required_source_cell_ids(),
        "covered_share_required_years": list(COVERED_SHARE_REQUIRED_YEARS),
        "source_document_manifest": _source_document_manifest(entries),
        "observations": observations,
        "cross_table_discrepancies": _cross_table_discrepancies(literals),
        "integrity": {
            "canonicalization": CANONICALIZATION,
            "content_sha256": "0" * 64,
            "extraction_implementation_commit": (
                EXTRACTION_IMPLEMENTATION_COMMIT
            ),
            "reproduced_from_source_bytes": True,
        },
    }
    artifact["integrity"]["content_sha256"] = _content_sha256(artifact)
    validate_artifact(artifact)
    return artifact


def render() -> bytes:
    """Rebuild and return the exact canonical artifact bytes."""
    return entry10.canonical_json_bytes(build())


def main() -> None:
    raw = render()
    OUT_PATH.write_bytes(raw)
    print(f"wrote {OUT_PATH} ({15 * len(REQUIRED_CALENDAR_YEARS)} cells)")
    print(f"json sha256: {hashlib.sha256(raw).hexdigest()}")


if __name__ == "__main__":
    main()
