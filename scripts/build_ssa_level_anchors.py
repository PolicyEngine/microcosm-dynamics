"""Build the vintage-1 official SSA level-anchor artifact.

The builder is deliberately offline.  It verifies the committed capture
manifest and all six raw snapshots before parsing any HTML, then selects the
120 registered cells through exact table, row-header, and column-header
paths.

Run from the repository root::

    .venv/bin/python scripts/build_ssa_level_anchors.py
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_DIR = (
    ROOT / "data" / "external" / "snapshots" / "ssa_level_anchors_vintage1"
)
MANIFEST_FILENAME = "capture_manifest.txt"
MANIFEST_RELATIVE_PATH = (
    "data/external/snapshots/ssa_level_anchors_vintage1/"
    "capture_manifest.txt"
)
OUT_PATH = (
    ROOT
    / "data"
    / "external"
    / "ssa_level_anchors_supplement2025_trustees2026_vintage1.json"
)

SCHEMA_VERSION = "ssa_level_anchors.v1"
ARTIFACT_VINTAGE_ID = "ssa_level_anchors.supplement2025_trustees2026.vintage1"
ARTIFACT_ROLE = "official_context_only"
YEAR_BASIS = "calendar_year"
REQUIRED_CALENDAR_YEARS = tuple(range(2015, 2023))
REQUIRED_SERIES_IDS = (
    "retired_worker_awards",
    "retired_worker_benefits_paid_estimated_allocation",
    "oasi_benefits_paid_estimated_allocation",
    "oasi_trust_fund_benefit_payments",
    "oasdi_trust_fund_benefit_payments",
    "retired_worker_december_current_payment_stock",
    "oasi_december_current_payment_stock",
    "oasdi_december_current_payment_stock",
    "oasdi_workers_with_taxable_earnings",
    "oasdi_reported_taxable_earnings",
    "oasdi_gross_contributions",
    "oasdi_adjusted_taxable_payroll",
    "oasdi_covered_workers",
    "oasi_net_payroll_tax_contributions",
    "oasdi_net_payroll_tax_contributions",
)

CAPTURE_MANIFEST_SHA256 = (
    "569dbed5922c2192277eb671685a5859ba1440e30289e8c252e1762956c150ca"
)
# sha256 of canonical_json_bytes(artifact["determinations"]).  This pin makes
# a locator or normalized-value change fail closed even when the changed
# output is not written to the committed artifact.
DETERMINATIONS_SHA256 = (
    "d5a70e2c4eb3943de65cef10194ec1c318c230bf3c440d56140f69a806aa21a1"
)

VERIFIED_AGAINST = (
    "Exact source-cell transcription only; this does not verify conceptual "
    "equivalence."
)
SOURCE_HASH_BASIS = "sha256 of exact committed raw snapshot bytes"
DETERMINATIONS_HASH_BASIS = (
    "sha256 of canonical UTF-8 JSON for the complete determinations object "
    "(sorted keys, compact separators, trailing newline)"
)
CANONICAL_ARTIFACT_BASIS = (
    "UTF-8 JSON with sorted keys, compact separators, ensure_ascii=True, "
    "allow_nan=False, and one trailing newline"
)
CERTIFIES_NOTHING = (
    (
        "Exact-cell transcription verification is not concept-equivalence "
        "verification."
    ),
    (
        "This official-context extraction does not align, scale, calibrate, "
        "or nationalize the model frame."
    ),
    (
        "This extraction creates no gate, floor, threshold, verdict, or "
        "exhaustive SSA-series completeness claim."
    ),
)


@dataclass(frozen=True)
class SourceDocumentSpec:
    """A reviewed literal source identity."""

    document_id: str
    filename: str
    official_url: str


SOURCE_DOCUMENT_SPECS = (
    SourceDocumentSpec(
        document_id="ssa_supplement_2025_6a",
        filename="supplement2025_6a.html",
        official_url=(
            "https://www.ssa.gov/policy/docs/statcomps/supplement/"
            "2025/6a.html"
        ),
    ),
    SourceDocumentSpec(
        document_id="ssa_supplement_2025_4a",
        filename="supplement2025_4a.html",
        official_url=(
            "https://www.ssa.gov/policy/docs/statcomps/supplement/"
            "2025/4a.html"
        ),
    ),
    SourceDocumentSpec(
        document_id="ssa_supplement_2025_5a",
        filename="supplement2025_5a.html",
        official_url=(
            "https://www.ssa.gov/policy/docs/statcomps/supplement/"
            "2025/5a.html"
        ),
    ),
    SourceDocumentSpec(
        document_id="ssa_supplement_2025_4b",
        filename="supplement2025_4b.html",
        official_url=(
            "https://www.ssa.gov/policy/docs/statcomps/supplement/"
            "2025/4b.html"
        ),
    ),
    # Trustees identities are intentionally literal.  Do not generate their
    # filenames, URLs, or table IDs from a table-number pattern.
    SourceDocumentSpec(
        document_id="ssa_trustees_2026_lr4b4",
        filename="trustees2026_lr4b4.html",
        official_url="https://www.ssa.gov/oact/TR/2026/lr4b4.html",
    ),
    SourceDocumentSpec(
        document_id="ssa_trustees_2026_lr6g1",
        filename="trustees2026_lr6g1.html",
        official_url="https://www.ssa.gov/OACT/TR/2026/lr6g1.html",
    ),
)


@dataclass(frozen=True)
class TableSpec:
    """An exact reviewed table identity and its row-label law."""

    table_id: str
    source_document_id: str
    publication: str
    edition_or_report_year: int
    table_title: str
    exact_caption: str
    row_group: str | None = None
    footnoted_years: tuple[tuple[int, str], ...] = ()
    status_evidence: str | None = None

    def row_header_path(self, year: int) -> tuple[str, ...]:
        """Return the exact visible row-header path for one calendar year."""
        footnotes = dict(self.footnoted_years)
        label = f"{year} {footnotes[year]}" if year in footnotes else str(year)
        if self.row_group is None:
            return (label,)
        return (self.row_group, label)


TABLE_SPECS = {
    "6.A1": TableSpec(
        table_id="6.A1",
        source_document_id="ssa_supplement_2025_6a",
        publication="Annual Statistical Supplement, 2025",
        edition_or_report_year=2025,
        table_title=("Number of awards, by type of benefit, 1940\u20132024"),
        exact_caption=(
            "Table 6.A1 Number of awards, by type of benefit, 1940\u20132024"
        ),
    ),
    "4.A1": TableSpec(
        table_id="4.A1",
        source_document_id="ssa_supplement_2025_4a",
        publication="Annual Statistical Supplement, 2025",
        edition_or_report_year=2025,
        table_title=(
            "Old-Age and Survivors Insurance Trust Fund: Receipts, "
            "expenditures, and assets, 1937\u20132024 (in millions of "
            "dollars)"
        ),
        exact_caption=(
            "Table 4.A1 Old-Age and Survivors Insurance Trust Fund: "
            "Receipts, expenditures, and assets, 1937\u20132024 (in "
            "millions of dollars)"
        ),
    ),
    "4.A3": TableSpec(
        table_id="4.A3",
        source_document_id="ssa_supplement_2025_4a",
        publication="Annual Statistical Supplement, 2025",
        edition_or_report_year=2025,
        table_title=(
            "Combined Old-Age and Survivors Insurance (OASI) and "
            "Disability Insurance (DI) Trust Funds: Receipts, "
            "expenditures, and assets, 1957\u20132024 (in millions of "
            "dollars)"
        ),
        exact_caption=(
            "Table 4.A3 Combined Old-Age and Survivors Insurance (OASI) "
            "and Disability Insurance (DI) Trust Funds: Receipts, "
            "expenditures, and assets, 1957\u20132024 (in millions of "
            "dollars)"
        ),
    ),
    "4.A5": TableSpec(
        table_id="4.A5",
        source_document_id="ssa_supplement_2025_4a",
        publication="Annual Statistical Supplement, 2025",
        edition_or_report_year=2025,
        table_title=(
            "Total annual benefits paid from Old-Age and Survivors "
            "Insurance Trust Fund, by type of benefit, selected years "
            "1937\u20132024 (in millions of dollars)"
        ),
        exact_caption=(
            "Table 4.A5 Total annual benefits paid from Old-Age and "
            "Survivors Insurance Trust Fund, by type of benefit, selected "
            "years 1937\u20132024 (in millions of dollars)"
        ),
        status_evidence=("NOTES: Amounts by type of benefit are estimated."),
    ),
    "5.A4": TableSpec(
        table_id="5.A4",
        source_document_id="ssa_supplement_2025_5a",
        publication="Annual Statistical Supplement, 2025",
        edition_or_report_year=2025,
        table_title=(
            "Number of beneficiaries and total monthly benefits, by trust "
            "fund and type of benefit, December 1940\u20132024, selected "
            "years"
        ),
        exact_caption=(
            "Table 5.A4 Number of beneficiaries and total monthly "
            "benefits, by trust fund and type of benefit, December "
            "1940\u20132024, selected years"
        ),
        row_group="Number",
    ),
    "4.B11": TableSpec(
        table_id="4.B11",
        source_document_id="ssa_supplement_2025_4b",
        publication="Annual Statistical Supplement, 2025",
        edition_or_report_year=2025,
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
        footnoted_years=((2021, "e"), (2022, "e")),
        status_evidence="e. Preliminary data.",
    ),
    "IV.B4": TableSpec(
        table_id="IV.B4",
        source_document_id="ssa_trustees_2026_lr4b4",
        publication="2026 OASDI Trustees Report",
        edition_or_report_year=2026,
        table_title=(
            "Covered Workers and Beneficiaries, Calendar Years 1945-2100"
        ),
        exact_caption=(
            "Table IV.B4.\u2014Covered Workers and Beneficiaries, Calendar "
            "Years 1945-2100"
        ),
        row_group="Historical data:",
    ),
    "VI.G1": TableSpec(
        table_id="VI.G1",
        source_document_id="ssa_trustees_2026_lr6g1",
        publication="2026 OASDI Trustees Report",
        edition_or_report_year=2026,
        table_title=(
            "Selected Economic Variables, Calendar Years 1970-2100 "
            "[GDP and taxable payroll in billions]"
        ),
        exact_caption=(
            "Table VI.G1.\u2014Selected Economic Variables, Calendar Years "
            "1970-2100 [GDP and taxable payroll in billions]"
        ),
        row_group="Historical data:",
    ),
}


@dataclass(frozen=True)
class SeriesSpec:
    """A registered official series and exact source-cell locator."""

    series_id: str
    table_id: str
    column_header_path: tuple[str, ...]
    published_unit: str
    stored_unit: str
    scale_multiplier: int
    program_scope: str
    population_scope: str
    measure: str
    time_basis: str
    accounting_basis: str


MILLION_DOLLARS = "millions_of_current_dollars"
THOUSAND_PERSONS = "thousands_of_persons"
BILLION_DOLLARS = "billions_of_current_dollars"
CURRENT_DOLLARS = "current_dollars"
PERSONS = "persons"

SERIES_SPECS = (
    SeriesSpec(
        series_id="retired_worker_awards",
        table_id="6.A1",
        column_header_path=("Retired workers",),
        published_unit="awards",
        stored_unit="awards",
        scale_multiplier=1,
        program_scope="OASI",
        population_scope="Retired workers",
        measure="Number of awards",
        time_basis="awards_during_calendar_year",
        accounting_basis="administrative_award_actions",
    ),
    SeriesSpec(
        series_id=("retired_worker_benefits_paid_estimated_allocation"),
        table_id="4.A5",
        column_header_path=(
            "Retired-worker and dependents benefits",
            "Retired workers",
        ),
        published_unit=MILLION_DOLLARS,
        stored_unit=CURRENT_DOLLARS,
        scale_multiplier=1_000_000,
        program_scope="OASI",
        population_scope="Retired workers",
        measure="Total annual benefits paid",
        time_basis="calendar_year_flow",
        accounting_basis="estimated_benefit_type_allocation",
    ),
    SeriesSpec(
        series_id="oasi_benefits_paid_estimated_allocation",
        table_id="4.A5",
        column_header_path=("Total",),
        published_unit=MILLION_DOLLARS,
        stored_unit=CURRENT_DOLLARS,
        scale_multiplier=1_000_000,
        program_scope="OASI",
        population_scope="All OASI benefit types",
        measure="Total annual benefits paid",
        time_basis="calendar_year_flow",
        accounting_basis="estimated_benefit_type_allocation",
    ),
    SeriesSpec(
        series_id="oasi_trust_fund_benefit_payments",
        table_id="4.A1",
        column_header_path=("Expenditures", "Benefit payments e"),
        published_unit=MILLION_DOLLARS,
        stored_unit=CURRENT_DOLLARS,
        scale_multiplier=1_000_000,
        program_scope="OASI",
        population_scope="OASI Trust Fund benefit payments",
        measure="Benefit payments",
        time_basis="calendar_year_flow",
        accounting_basis="trust_fund_expenditure_accounting",
    ),
    SeriesSpec(
        series_id="oasdi_trust_fund_benefit_payments",
        table_id="4.A3",
        column_header_path=("Expenditures", "Benefit payments e"),
        published_unit=MILLION_DOLLARS,
        stored_unit=CURRENT_DOLLARS,
        scale_multiplier=1_000_000,
        program_scope="OASDI",
        population_scope=("Combined OASI and DI Trust Funds benefit payments"),
        measure="Benefit payments",
        time_basis="calendar_year_flow",
        accounting_basis="trust_fund_expenditure_accounting",
    ),
    SeriesSpec(
        series_id="retired_worker_december_current_payment_stock",
        table_id="5.A4",
        column_header_path=("Retired workers",),
        published_unit=PERSONS,
        stored_unit=PERSONS,
        scale_multiplier=1,
        program_scope="OASI",
        population_scope=(
            "Retired workers in current-payment status in December"
        ),
        measure="Number of beneficiaries",
        time_basis="december_point_stock",
        accounting_basis="administrative_current_payment_status",
    ),
    SeriesSpec(
        series_id="oasi_december_current_payment_stock",
        table_id="5.A4",
        column_header_path=("OASDI", "OASI Trust Fund"),
        published_unit=PERSONS,
        stored_unit=PERSONS,
        scale_multiplier=1,
        program_scope="OASI",
        population_scope=(
            "All OASI beneficiaries in current-payment status in December"
        ),
        measure="Number of beneficiaries",
        time_basis="december_point_stock",
        accounting_basis="administrative_current_payment_status",
    ),
    SeriesSpec(
        series_id="oasdi_december_current_payment_stock",
        table_id="5.A4",
        column_header_path=("OASDI", "Total"),
        published_unit=PERSONS,
        stored_unit=PERSONS,
        scale_multiplier=1,
        program_scope="OASDI",
        population_scope=(
            "All OASDI beneficiaries in current-payment status in December"
        ),
        measure="Number of beneficiaries",
        time_basis="december_point_stock",
        accounting_basis="administrative_current_payment_status",
    ),
    SeriesSpec(
        series_id="oasdi_workers_with_taxable_earnings",
        table_id="4.B11",
        column_header_path=("Number a (thousands)", "Total"),
        published_unit=THOUSAND_PERSONS,
        stored_unit=PERSONS,
        scale_multiplier=1_000,
        program_scope="OASDI",
        population_scope=(
            "Workers with Social Security (OASDI) taxable earnings"
        ),
        measure="Number of workers",
        time_basis="calendar_year_earnings",
        accounting_basis="reported_taxable_earnings_records",
    ),
    SeriesSpec(
        series_id="oasdi_reported_taxable_earnings",
        table_id="4.B11",
        column_header_path=(
            "Taxable earnings b (millions of dollars)",
            "Total",
        ),
        published_unit=MILLION_DOLLARS,
        stored_unit=CURRENT_DOLLARS,
        scale_multiplier=1_000_000,
        program_scope="OASDI",
        population_scope=(
            "Workers with Social Security (OASDI) taxable earnings"
        ),
        measure="Taxable earnings",
        time_basis="calendar_year_earnings",
        accounting_basis="reported_taxable_earnings",
    ),
    SeriesSpec(
        series_id="oasdi_gross_contributions",
        table_id="4.B11",
        column_header_path=(
            "OASDI contributions c,d (millions of dollars)",
            "Total",
        ),
        published_unit=MILLION_DOLLARS,
        stored_unit=CURRENT_DOLLARS,
        scale_multiplier=1_000_000,
        program_scope="OASDI",
        population_scope=(
            "Wage, salary, and self-employment taxable earnings"
        ),
        measure="OASDI contributions",
        time_basis="calendar_year_earnings",
        accounting_basis=(
            "gross_contribution_arithmetic_unadjusted_for_refunds_and_"
            "tax_credits"
        ),
    ),
    SeriesSpec(
        series_id="oasdi_adjusted_taxable_payroll",
        table_id="VI.G1",
        column_header_path=("Taxable payroll b",),
        published_unit=BILLION_DOLLARS,
        stored_unit=CURRENT_DOLLARS,
        scale_multiplier=1_000_000_000,
        program_scope="OASDI",
        population_scope="Earnings subject to OASDI contribution rates",
        measure="Taxable payroll",
        time_basis="calendar_year_earnings",
        accounting_basis="actuarially_adjusted_taxable_payroll",
    ),
    SeriesSpec(
        series_id="oasdi_covered_workers",
        table_id="IV.B4",
        column_header_path=("Covered workers a (in thousands)",),
        published_unit=THOUSAND_PERSONS,
        stored_unit=PERSONS,
        scale_multiplier=1_000,
        program_scope="OASDI",
        population_scope=(
            "Workers paid during the year for employment on which OASDI "
            "taxes are due"
        ),
        measure="Covered workers",
        time_basis="calendar_year_worker_count",
        accounting_basis="covered_employment_with_oasdi_taxes_due",
    ),
    SeriesSpec(
        series_id="oasi_net_payroll_tax_contributions",
        table_id="4.A1",
        column_header_path=(
            "Receipts a",
            "Net payroll tax contributions b",
        ),
        published_unit=MILLION_DOLLARS,
        stored_unit=CURRENT_DOLLARS,
        scale_multiplier=1_000_000,
        program_scope="OASI",
        population_scope="OASI Trust Fund receipts",
        measure="Net payroll tax contributions",
        time_basis="calendar_year_flow",
        accounting_basis="trust_fund_receipt_accounting",
    ),
    SeriesSpec(
        series_id="oasdi_net_payroll_tax_contributions",
        table_id="4.A3",
        column_header_path=(
            "Receipts a",
            "Net payroll tax contributions b",
        ),
        published_unit=MILLION_DOLLARS,
        stored_unit=CURRENT_DOLLARS,
        scale_multiplier=1_000_000,
        program_scope="OASDI",
        population_scope="Combined OASI and DI Trust Funds receipts",
        measure="Net payroll tax contributions",
        time_basis="calendar_year_flow",
        accounting_basis="trust_fund_receipt_accounting",
    ),
)


@dataclass(frozen=True)
class ManifestEntry:
    """One exact line in the committed capture manifest."""

    retrieval_timestamp: str
    sha256: str
    size_bytes: int
    filename: str
    literal_entry: str


@dataclass(frozen=True)
class _Cell:
    """One normalized visible HTML table cell."""

    tag: str
    text: str
    attributes: Mapping[str, str]

    @property
    def colspan(self) -> int:
        return _positive_span(self.attributes.get("colspan"), "colspan")

    @property
    def rowspan(self) -> int:
        return _positive_span(self.attributes.get("rowspan"), "rowspan")


@dataclass(frozen=True)
class _Row:
    """One HTML table row and its publication section."""

    section: str | None
    cells: tuple[_Cell, ...]


@dataclass(frozen=True)
class _ParsedTable:
    """The visible structure needed for exact-cell extraction."""

    caption: str | None
    rows: tuple[_Row, ...]


def _positive_span(raw: str | None, name: str) -> int:
    if raw is None:
        return 1
    if not re.fullmatch(r"[1-9]\d*", raw):
        raise ValueError(f"invalid HTML table {name}={raw!r}")
    return int(raw)


def _normalize_visible_text(chunks: Sequence[str]) -> str:
    """Collapse presentation whitespace while preserving visible content."""
    return " ".join("".join(chunks).replace("\xa0", " ").split())


class _AllTablesParser(HTMLParser):
    """Collect table captions, sections, rows, cells, and span attributes."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[_ParsedTable] = []
        self._stack: list[dict[str, Any]] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag == "table":
            self._stack.append(
                {
                    "caption": None,
                    "caption_chunks": None,
                    "cell": None,
                    "cell_attributes": None,
                    "cell_tag": None,
                    "row": None,
                    "rows": [],
                    "section": None,
                }
            )
            return
        if not self._stack:
            return
        table = self._stack[-1]
        if tag in {"thead", "tbody", "tfoot"}:
            table["section"] = tag
        elif tag == "caption":
            table["caption_chunks"] = []
        elif tag == "tr":
            if table["row"] is not None:
                raise ValueError("nested table row")
            table["row"] = []
        elif tag in {"th", "td"} and table["row"] is not None:
            if table["cell"] is not None:
                raise ValueError("nested table cell")
            table["cell"] = []
            table["cell_tag"] = tag
            table["cell_attributes"] = {
                key: value for key, value in attrs if value is not None
            }
        elif tag == "br":
            if table["caption_chunks"] is not None:
                table["caption_chunks"].append(" ")
            if table["cell"] is not None:
                table["cell"].append(" ")

    def handle_data(self, data: str) -> None:
        if not self._stack:
            return
        table = self._stack[-1]
        if table["caption_chunks"] is not None:
            table["caption_chunks"].append(data)
        if table["cell"] is not None:
            table["cell"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if not self._stack:
            return
        table = self._stack[-1]
        if tag in {"th", "td"} and table["cell"] is not None:
            if table["row"] is None or table["cell_tag"] != tag:
                raise ValueError(f"unbalanced HTML table cell {tag}")
            table["row"].append(
                _Cell(
                    tag=tag,
                    text=_normalize_visible_text(table["cell"]),
                    attributes=table["cell_attributes"],
                )
            )
            table["cell"] = None
            table["cell_attributes"] = None
            table["cell_tag"] = None
        elif tag == "tr" and table["row"] is not None:
            table["rows"].append(
                _Row(
                    section=table["section"],
                    cells=tuple(table["row"]),
                )
            )
            table["row"] = None
        elif tag == "caption" and table["caption_chunks"] is not None:
            table["caption"] = _normalize_visible_text(table["caption_chunks"])
            table["caption_chunks"] = None
        elif tag in {"thead", "tbody", "tfoot"}:
            table["section"] = None
        elif tag == "table":
            if table["row"] is not None or table["cell"] is not None:
                raise ValueError("unclosed HTML table row or cell")
            completed = self._stack.pop()
            self.tables.append(
                _ParsedTable(
                    caption=completed["caption"],
                    rows=tuple(completed["rows"]),
                )
            )


_MANIFEST_LINE = re.compile(
    r"(?P<retrieved>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) "
    r"(?P<sha256>[0-9a-f]{64}) "
    r"(?P<size>[1-9]\d*) "
    r"(?P<filename>[A-Za-z0-9_.-]+)"
)


def _parse_manifest(raw: bytes) -> tuple[ManifestEntry, ...]:
    """Verify and parse the complete committed capture manifest."""
    digest = hashlib.sha256(raw).hexdigest()
    if digest != CAPTURE_MANIFEST_SHA256:
        raise ValueError(
            f"capture manifest sha256 {digest} != pinned "
            f"{CAPTURE_MANIFEST_SHA256}; source manifest drift"
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("capture manifest is not UTF-8") from error
    if not text.endswith("\n") or text.endswith("\n\n"):
        raise ValueError("capture manifest must have one trailing newline")

    entries: list[ManifestEntry] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        match = _MANIFEST_LINE.fullmatch(line)
        if match is None:
            raise ValueError(
                f"malformed capture manifest line {line_number}: {line!r}"
            )
        entries.append(
            ManifestEntry(
                retrieval_timestamp=match.group("retrieved"),
                sha256=match.group("sha256"),
                size_bytes=int(match.group("size")),
                filename=match.group("filename"),
                literal_entry=line,
            )
        )

    actual_filenames = tuple(entry.filename for entry in entries)
    expected_filenames = tuple(spec.filename for spec in SOURCE_DOCUMENT_SPECS)
    if actual_filenames != expected_filenames:
        raise ValueError(
            "capture manifest filenames are missing, extra, duplicated, or "
            f"reordered: {actual_filenames!r} != {expected_filenames!r}"
        )
    return tuple(entries)


def read_verified_snapshots() -> (
    tuple[Mapping[str, ManifestEntry], Mapping[str, bytes]]
):
    """Hash-verify every committed source before returning any parse input."""
    manifest_path = SNAPSHOT_DIR / MANIFEST_FILENAME
    try:
        manifest_raw = manifest_path.read_bytes()
    except OSError as error:
        raise ValueError(
            f"cannot read committed capture manifest {manifest_path}"
        ) from error
    entries = _parse_manifest(manifest_raw)

    raw_by_document_id: dict[str, bytes] = {}
    entry_by_document_id: dict[str, ManifestEntry] = {}
    for source_spec, entry in zip(SOURCE_DOCUMENT_SPECS, entries, strict=True):
        path = SNAPSHOT_DIR / source_spec.filename
        try:
            raw = path.read_bytes()
        except OSError as error:
            raise ValueError(
                f"cannot read committed snapshot {path}"
            ) from error
        if len(raw) != entry.size_bytes:
            raise ValueError(
                f"{source_spec.filename} byte count {len(raw)} != manifest "
                f"{entry.size_bytes}; source-byte drift"
            )
        digest = hashlib.sha256(raw).hexdigest()
        if digest != entry.sha256:
            raise ValueError(
                f"{source_spec.filename} sha256 {digest} != manifest "
                f"{entry.sha256}; source-byte drift"
            )
        raw_by_document_id[source_spec.document_id] = raw
        entry_by_document_id[source_spec.document_id] = entry

    expected_ids = tuple(spec.document_id for spec in SOURCE_DOCUMENT_SPECS)
    if tuple(raw_by_document_id) != expected_ids:
        raise ValueError("verified snapshot registry order drift")
    return entry_by_document_id, raw_by_document_id


def _parse_tables(raw: bytes, document_id: str) -> tuple[_ParsedTable, ...]:
    try:
        source = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"{document_id} snapshot is not UTF-8") from error
    parser = _AllTablesParser()
    parser.feed(source)
    parser.close()
    return tuple(parser.tables)


def _select_tables(
    raw_by_document_id: Mapping[str, bytes],
) -> Mapping[str, _ParsedTable]:
    """Select each reviewed table by its complete literal caption."""
    parsed_by_document_id = {
        document_id: _parse_tables(raw, document_id)
        for document_id, raw in raw_by_document_id.items()
    }
    selected: dict[str, _ParsedTable] = {}
    for table_id, table_spec in TABLE_SPECS.items():
        matches = [
            table
            for table in parsed_by_document_id[table_spec.source_document_id]
            if table.caption == table_spec.exact_caption
        ]
        if len(matches) != 1:
            raise ValueError(
                f"expected exactly one literal {table_id} caption "
                f"{table_spec.exact_caption!r}, found {len(matches)}"
            )
        table = matches[0]
        if table_spec.status_evidence is not None:
            notes = tuple(
                cell.text
                for row in table.rows
                if row.section == "tfoot"
                for cell in row.cells
            )
            if not any(table_spec.status_evidence in note for note in notes):
                raise ValueError(
                    f"{table_id} status evidence "
                    f"{table_spec.status_evidence!r} not found"
                )
        selected[table_id] = table
    return selected


def _expand_rows(rows: Sequence[_Row]) -> list[list[_Cell | None]]:
    """Expand HTML row/column spans into a rectangular logical grid."""
    occupied: dict[tuple[int, int], _Cell] = {}
    max_column = 0
    for row_index, row in enumerate(rows):
        column = 0
        for cell in row.cells:
            while (row_index, column) in occupied:
                column += 1
            for row_offset in range(cell.rowspan):
                for column_offset in range(cell.colspan):
                    key = (
                        row_index + row_offset,
                        column + column_offset,
                    )
                    if key in occupied:
                        raise ValueError(
                            f"overlapping HTML table span at {key}"
                        )
                    occupied[key] = cell
            column += cell.colspan
        while (row_index, column) in occupied:
            column += 1
        max_column = max(max_column, column)

    return [
        [occupied.get((row_index, column)) for column in range(max_column)]
        for row_index in range(len(rows))
    ]


def _column_header_paths(
    table: _ParsedTable,
) -> tuple[tuple[str, ...], ...]:
    """Resolve every logical column to its complete nested header path."""
    header_rows = [row for row in table.rows if row.section == "thead"]
    if not header_rows:
        raise ValueError(f"table {table.caption!r} has no thead rows")
    grid = _expand_rows(header_rows)
    width = len(grid[0])
    if any(len(row) != width for row in grid):
        raise ValueError("nonrectangular expanded header grid")

    paths: list[tuple[str, ...]] = []
    for column in range(width):
        parts: list[str] = []
        previous: _Cell | None = None
        for row in grid:
            cell = row[column]
            if (
                cell is not None
                and cell is not previous
                and cell.tag == "th"
                and cell.text
            ):
                parts.append(cell.text)
            previous = cell
        paths.append(tuple(parts))
    return tuple(paths)


_YEAR_ROW = re.compile(r"(?P<year>\d{4})(?: [a-z](?:,[a-z])*)?")


def _body_rows_by_header_path(
    table: _ParsedTable,
) -> Mapping[tuple[str, ...], tuple[int, list[_Cell | None]]]:
    """Index year rows by their exact row-group and row-label path."""
    body_rows = [row for row in table.rows if row.section == "tbody"]
    grid = _expand_rows(body_rows)
    row_group: str | None = None
    indexed: dict[tuple[str, ...], tuple[int, list[_Cell | None]]] = {}

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
        if len(row_headers) != 1:
            continue
        row_label = row_headers[0].text
        match = _YEAR_ROW.fullmatch(row_label)
        if match is None:
            continue
        year = int(match.group("year"))
        if year not in REQUIRED_CALENDAR_YEARS:
            continue
        path = (
            (row_group, row_label) if row_group is not None else (row_label,)
        )
        if path in indexed:
            raise ValueError(f"duplicate source row header path {path!r}")
        indexed[path] = (year, expanded_row)
    return indexed


def _parse_integer_cell(literal: str, *, where: str) -> int:
    """Parse one selected whole-number source cell without synthesis."""
    if not re.fullmatch(r"\$?-?\d{1,3}(?:,\d{3})*|\$?-?\d+", literal):
        raise ValueError(
            f"{where} literal cell {literal!r} is missing or nonnumeric"
        )
    normalized = literal.replace("$", "").replace(",", "")
    return int(normalized)


def _source_status(table_id: str, year: int) -> str:
    if table_id == "4.A5":
        return "estimated_allocation"
    if table_id == "4.B11" and year >= 2021:
        return "preliminary"
    return "historical"


def _extract_observations(
    series: SeriesSpec,
    table: _ParsedTable,
    source_document: SourceDocumentSpec,
) -> list[dict[str, Any]]:
    """Extract all eight registered cells for one series."""
    table_spec = TABLE_SPECS[series.table_id]
    header_paths = _column_header_paths(table)
    matching_columns = [
        index
        for index, path in enumerate(header_paths)
        if path == series.column_header_path
    ]
    if len(matching_columns) != 1:
        raise ValueError(
            f"{series.series_id} column path "
            f"{series.column_header_path!r} selected "
            f"{len(matching_columns)} columns"
        )
    column = matching_columns[0]
    rows = _body_rows_by_header_path(table)

    observations: list[dict[str, Any]] = []
    for year in REQUIRED_CALENDAR_YEARS:
        row_path = table_spec.row_header_path(year)
        matches = [
            (path, resolved_year, row)
            for path, (resolved_year, row) in rows.items()
            if path == row_path
        ]
        if len(matches) != 1:
            raise ValueError(
                f"{series.series_id} row path {row_path!r} selected "
                f"{len(matches)} rows"
            )
        _, resolved_year, row = matches[0]
        if resolved_year != year:
            raise ValueError(
                f"{series.series_id} row path {row_path!r} resolved to "
                f"calendar year {resolved_year}"
            )
        if column >= len(row) or row[column] is None:
            raise ValueError(
                f"{series.series_id} {year} locator has no source cell"
            )
        cell = row[column]
        assert cell is not None
        if cell.tag != "td" or not cell.text:
            raise ValueError(
                f"{series.series_id} {year} locator selected "
                f"{cell.tag} {cell.text!r}, not a literal data cell"
            )
        published_value = _parse_integer_cell(
            cell.text,
            where=f"{series.series_id} {year}",
        )
        value = published_value * series.scale_multiplier
        observations.append(
            {
                "as_published": cell.text,
                "published_unit": series.published_unit,
                "scale_multiplier": series.scale_multiplier,
                "source_column_header_path": list(series.column_header_path),
                "source_document_id": source_document.document_id,
                "source_row_header_path": list(row_path),
                "source_status": _source_status(series.table_id, year),
                "source_table_id": series.table_id,
                "source_url": source_document.official_url,
                "stored_unit": series.stored_unit,
                "value": value,
                "verified_against": VERIFIED_AGAINST,
                "year": year,
                "year_basis": YEAR_BASIS,
            }
        )
    return observations


def canonical_json_bytes(value: Any) -> bytes:
    """Return the design's canonical compact JSON representation."""
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _sha256_canonical(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _validate_registry() -> None:
    actual_ids = tuple(series.series_id for series in SERIES_SPECS)
    if actual_ids != REQUIRED_SERIES_IDS:
        raise ValueError(
            "registered series IDs are missing, extra, duplicated, or "
            f"reordered: {actual_ids!r} != {REQUIRED_SERIES_IDS!r}"
        )
    source_ids = tuple(spec.document_id for spec in SOURCE_DOCUMENT_SPECS)
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("duplicate source document ID")
    filenames = tuple(spec.filename for spec in SOURCE_DOCUMENT_SPECS)
    if len(filenames) != len(set(filenames)):
        raise ValueError("duplicate source snapshot filename")
    if set(TABLE_SPECS) != {series.table_id for series in SERIES_SPECS}:
        raise ValueError("table registry does not equal registered table use")

    # These exact reviewed pairs defend against pattern-generated Trustees
    # identities.
    trustees_literals = (
        (
            "ssa_trustees_2026_lr4b4",
            "trustees2026_lr4b4.html",
            "https://www.ssa.gov/oact/TR/2026/lr4b4.html",
            "IV.B4",
        ),
        (
            "ssa_trustees_2026_lr6g1",
            "trustees2026_lr6g1.html",
            "https://www.ssa.gov/OACT/TR/2026/lr6g1.html",
            "VI.G1",
        ),
    )
    by_id = {spec.document_id: spec for spec in SOURCE_DOCUMENT_SPECS}
    actual_trustees = tuple(
        (
            document_id,
            by_id[document_id].filename,
            by_id[document_id].official_url,
            table_id,
        )
        for document_id, _, _, table_id in trustees_literals
    )
    if actual_trustees != trustees_literals:
        raise ValueError("Trustees identities differ from reviewed literals")


def _source_document_manifest(
    entries: Mapping[str, ManifestEntry],
) -> dict[str, dict[str, Any]]:
    documents: dict[str, dict[str, Any]] = {}
    for source_spec in SOURCE_DOCUMENT_SPECS:
        entry = entries[source_spec.document_id]
        documents[source_spec.document_id] = {
            "capture_manifest_entry": entry.literal_entry,
            "capture_manifest_path": MANIFEST_RELATIVE_PATH,
            "committed_raw_snapshot_path": (
                "data/external/snapshots/ssa_level_anchors_vintage1/"
                f"{source_spec.filename}"
            ),
            "official_url": source_spec.official_url,
            "retrieval_timestamp": entry.retrieval_timestamp,
            "sha256": entry.sha256,
            "size_bytes": entry.size_bytes,
            "source_hash_basis": SOURCE_HASH_BASIS,
        }
    return documents


def _build_metadata() -> dict[str, Any]:
    return {
        "built_by": "scripts/build_ssa_level_anchors.py",
        "canonical_artifact_basis": CANONICAL_ARTIFACT_BASIS,
        "capture_manifest_path": MANIFEST_RELATIVE_PATH,
        "capture_manifest_sha256": CAPTURE_MANIFEST_SHA256,
        "network_access": (
            "none; reads only the committed, hash-verified source snapshots"
        ),
        "reproducible": (
            "deterministic from the committed capture manifest and six raw "
            "snapshots; no network or wall clock"
        ),
    }


def _validation_metadata() -> dict[str, Any]:
    return {
        "all_committed_table_ids_verified": True,
        "n_observations": (
            len(REQUIRED_SERIES_IDS) * len(REQUIRED_CALENDAR_YEARS)
        ),
        "required_series_ids_exact": True,
        "required_years_complete_and_ordered_per_series": True,
        "row_and_column_header_paths_exact": True,
        "scope_statement": (
            "Complete only for the 15 registered series and calendar years "
            "2015-2022; not an exhaustive inventory of SSA series."
        ),
        "source_bytes_verified_before_parsing": True,
        "status_law_exact": True,
    }


def _validate_artifact(artifact: Mapping[str, Any]) -> None:
    """Apply the design's fail-closed schema and cell laws."""
    expected_top_level = {
        "artifact_role",
        "artifact_vintage_id",
        "build",
        "certifies_nothing",
        "determinations",
        "integrity",
        "required_calendar_years",
        "required_series_ids",
        "schema_version",
        "source_documents",
        "validation",
        "year_basis",
    }
    if set(artifact) != expected_top_level:
        raise ValueError(
            f"artifact keys {set(artifact)!r} != {expected_top_level!r}"
        )
    if artifact["schema_version"] != SCHEMA_VERSION:
        raise ValueError("schema_version drift")
    if artifact["artifact_vintage_id"] != ARTIFACT_VINTAGE_ID:
        raise ValueError("artifact_vintage_id drift")
    if artifact["artifact_role"] != ARTIFACT_ROLE:
        raise ValueError("artifact_role drift")
    if artifact["year_basis"] != YEAR_BASIS:
        raise ValueError("year_basis drift")
    if artifact["required_calendar_years"] != list(REQUIRED_CALENDAR_YEARS):
        raise ValueError("required calendar years missing or reordered")
    if artifact["required_series_ids"] != list(REQUIRED_SERIES_IDS):
        raise ValueError("required series IDs missing, extra, or reordered")
    if artifact["build"] != _build_metadata():
        raise ValueError("build metadata drift")
    if artifact["validation"] != _validation_metadata():
        raise ValueError("validation metadata drift")
    if artifact["certifies_nothing"] != list(CERTIFIES_NOTHING):
        raise ValueError("certifies_nothing boundary drift")

    determinations = artifact["determinations"]
    if not isinstance(determinations, dict):
        raise ValueError("determinations must be an object")
    if set(determinations) != set(REQUIRED_SERIES_IDS):
        raise ValueError(
            "determination keys are missing, extra, or duplicated"
        )

    source_documents = artifact["source_documents"]
    if not isinstance(source_documents, dict):
        raise ValueError("source_documents must be an object")
    expected_document_ids = tuple(
        spec.document_id for spec in SOURCE_DOCUMENT_SPECS
    )
    if set(source_documents) != set(expected_document_ids):
        raise ValueError("source document manifest identity drift")
    verified_entries, _ = read_verified_snapshots()
    expected_source_documents = _source_document_manifest(verified_entries)
    if source_documents != expected_source_documents:
        raise ValueError(
            "source document metadata differs from the verified manifest"
        )
    for document_id, document in source_documents.items():
        expected_document_keys = {
            "capture_manifest_entry",
            "capture_manifest_path",
            "committed_raw_snapshot_path",
            "official_url",
            "retrieval_timestamp",
            "sha256",
            "size_bytes",
            "source_hash_basis",
        }
        if set(document) != expected_document_keys:
            raise ValueError(
                f"{document_id} source manifest fields missing or extra"
            )
        for key in (
            "capture_manifest_entry",
            "capture_manifest_path",
            "committed_raw_snapshot_path",
            "official_url",
            "retrieval_timestamp",
            "sha256",
            "source_hash_basis",
        ):
            if not isinstance(document[key], str) or not document[key]:
                raise ValueError(
                    f"{document_id}.{key} is missing or not a string"
                )
        if not re.fullmatch(r"[0-9a-f]{64}", document["sha256"]):
            raise ValueError(f"{document_id}.sha256 is not lowercase sha256")
        if (
            isinstance(document["size_bytes"], bool)
            or not isinstance(document["size_bytes"], int)
            or document["size_bytes"] <= 0
        ):
            raise ValueError(f"{document_id}.size_bytes is invalid")

    spec_by_id = {series.series_id: series for series in SERIES_SPECS}
    observations_seen = 0
    for series_id in REQUIRED_SERIES_IDS:
        series = spec_by_id[series_id]
        table_spec = TABLE_SPECS[series.table_id]
        determination = determinations[series_id]
        expected_determination_keys = {
            "official_concept",
            "observations",
            "published_unit",
            "scale_multiplier",
            "series_id",
            "source_table",
            "stored_unit",
            "year_basis",
        }
        if set(determination) != expected_determination_keys:
            raise ValueError(
                f"{series_id} determination fields missing or extra"
            )
        if determination["series_id"] != series_id:
            raise ValueError(f"{series_id} literal series_id drift")
        if determination["published_unit"] != series.published_unit:
            raise ValueError(f"{series_id} published unit drift")
        if determination["stored_unit"] != series.stored_unit:
            raise ValueError(f"{series_id} stored unit drift")
        if determination["scale_multiplier"] != series.scale_multiplier:
            raise ValueError(f"{series_id} scale multiplier drift")
        if determination["year_basis"] != YEAR_BASIS:
            raise ValueError(f"{series_id} year basis drift")

        official_concept = determination["official_concept"]
        expected_concept = {
            "accounting_basis": series.accounting_basis,
            "comparison_status": "context_only",
            "measure": series.measure,
            "population_scope": series.population_scope,
            "program_scope": series.program_scope,
            "time_basis": series.time_basis,
        }
        if official_concept != expected_concept:
            raise ValueError(f"{series_id} official concept/scope drift")

        source_table = determination["source_table"]
        expected_source_table = {
            "edition_or_report_year": table_spec.edition_or_report_year,
            "publication": table_spec.publication,
            "publisher": "Social Security Administration",
            "source_document_id": table_spec.source_document_id,
            "table_id": table_spec.table_id,
            "table_title": table_spec.table_title,
        }
        if source_table != expected_source_table:
            raise ValueError(f"{series_id} source table identity drift")

        observations = determination["observations"]
        if not isinstance(observations, list):
            raise ValueError(f"{series_id} observations must be an array")
        years = [
            observation.get("year")
            for observation in observations
            if isinstance(observation, dict)
        ]
        if years != list(REQUIRED_CALENDAR_YEARS):
            raise ValueError(
                f"{series_id} years missing, extra, duplicated, or reordered"
            )
        for observation in observations:
            observations_seen += 1
            expected_observation_keys = {
                "as_published",
                "published_unit",
                "scale_multiplier",
                "source_column_header_path",
                "source_document_id",
                "source_row_header_path",
                "source_status",
                "source_table_id",
                "source_url",
                "stored_unit",
                "value",
                "verified_against",
                "year",
                "year_basis",
            }
            if set(observation) != expected_observation_keys:
                raise ValueError(
                    f"{series_id} observation fields missing or extra"
                )
            year = observation["year"]
            if isinstance(year, bool) or not isinstance(year, int):
                raise ValueError(f"{series_id} observation year invalid")
            for field in (
                "as_published",
                "published_unit",
                "source_document_id",
                "source_status",
                "source_table_id",
                "source_url",
                "stored_unit",
                "verified_against",
                "year_basis",
            ):
                if (
                    not isinstance(observation[field], str)
                    or not observation[field]
                ):
                    raise ValueError(f"{series_id} {year} missing {field}")
            for field in (
                "source_row_header_path",
                "source_column_header_path",
            ):
                path = observation[field]
                if (
                    not isinstance(path, list)
                    or not path
                    or any(
                        not isinstance(part, str) or not part for part in path
                    )
                ):
                    raise ValueError(
                        f"{series_id} {year} missing exact {field}"
                    )
            if observation["published_unit"] != series.published_unit:
                raise ValueError(f"{series_id} {year} published unit drift")
            if observation["stored_unit"] != series.stored_unit:
                raise ValueError(f"{series_id} {year} stored unit drift")
            if observation["scale_multiplier"] != series.scale_multiplier:
                raise ValueError(f"{series_id} {year} scale drift")
            if observation["year_basis"] != YEAR_BASIS:
                raise ValueError(f"{series_id} {year} year basis drift")
            if observation["source_table_id"] != series.table_id:
                raise ValueError(f"{series_id} {year} table ID drift")
            if observation["source_document_id"] != (
                table_spec.source_document_id
            ):
                raise ValueError(f"{series_id} {year} document ID drift")
            source_document = source_documents[table_spec.source_document_id]
            if observation["source_url"] != source_document["official_url"]:
                raise ValueError(f"{series_id} {year} source URL drift")
            if observation["source_row_header_path"] != list(
                table_spec.row_header_path(year)
            ):
                raise ValueError(f"{series_id} {year} row path drift")
            if observation["source_column_header_path"] != list(
                series.column_header_path
            ):
                raise ValueError(f"{series_id} {year} column path drift")
            if observation["source_status"] != _source_status(
                series.table_id, year
            ):
                raise ValueError(
                    f"{series_id} {year} status is preliminary/final or "
                    "estimated-allocation drift"
                )
            if observation["verified_against"] != VERIFIED_AGAINST:
                raise ValueError(
                    f"{series_id} {year} verified_against must mean exact "
                    "cell transcription, not conceptual equivalence"
                )
            published_value = _parse_integer_cell(
                observation["as_published"],
                where=f"{series_id} {year}",
            )
            expected_value = published_value * series.scale_multiplier
            value = observation["value"]
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value != expected_value
            ):
                raise ValueError(f"{series_id} {year} normalized value drift")

    if observations_seen != len(REQUIRED_SERIES_IDS) * len(
        REQUIRED_CALENDAR_YEARS
    ):
        raise ValueError(
            f"observation count {observations_seen} != required 120"
        )
    observed_digest = _sha256_canonical(determinations)
    if observed_digest != DETERMINATIONS_SHA256:
        raise ValueError(
            f"canonical determinations sha256 {observed_digest} != pinned "
            f"{DETERMINATIONS_SHA256}; locator or canonical-value drift"
        )
    if artifact["integrity"] != {
        "determinations_hash_basis": DETERMINATIONS_HASH_BASIS,
        "determinations_sha256": DETERMINATIONS_SHA256,
    }:
        raise ValueError("integrity metadata drift")


def build() -> dict[str, Any]:
    """Build and fail-closed validate the complete vintage-1 artifact."""
    _validate_registry()
    entries, raw_by_document_id = read_verified_snapshots()
    tables = _select_tables(raw_by_document_id)
    source_spec_by_id = {
        source.document_id: source for source in SOURCE_DOCUMENT_SPECS
    }

    determinations: dict[str, dict[str, Any]] = {}
    for series in SERIES_SPECS:
        table_spec = TABLE_SPECS[series.table_id]
        observations = _extract_observations(
            series,
            tables[series.table_id],
            source_spec_by_id[table_spec.source_document_id],
        )
        determinations[series.series_id] = {
            "official_concept": {
                "accounting_basis": series.accounting_basis,
                "comparison_status": "context_only",
                "measure": series.measure,
                "population_scope": series.population_scope,
                "program_scope": series.program_scope,
                "time_basis": series.time_basis,
            },
            "observations": observations,
            "published_unit": series.published_unit,
            "scale_multiplier": series.scale_multiplier,
            "series_id": series.series_id,
            "source_table": {
                "edition_or_report_year": (table_spec.edition_or_report_year),
                "publication": table_spec.publication,
                "publisher": "Social Security Administration",
                "source_document_id": table_spec.source_document_id,
                "table_id": table_spec.table_id,
                "table_title": table_spec.table_title,
            },
            "stored_unit": series.stored_unit,
            "year_basis": YEAR_BASIS,
        }

    artifact: dict[str, Any] = {
        "artifact_role": ARTIFACT_ROLE,
        "artifact_vintage_id": ARTIFACT_VINTAGE_ID,
        "build": _build_metadata(),
        "certifies_nothing": list(CERTIFIES_NOTHING),
        "determinations": determinations,
        "integrity": {
            "determinations_hash_basis": DETERMINATIONS_HASH_BASIS,
            "determinations_sha256": DETERMINATIONS_SHA256,
        },
        "required_calendar_years": list(REQUIRED_CALENDAR_YEARS),
        "required_series_ids": list(REQUIRED_SERIES_IDS),
        "schema_version": SCHEMA_VERSION,
        "source_documents": _source_document_manifest(entries),
        "validation": _validation_metadata(),
        "year_basis": YEAR_BASIS,
    }
    _validate_artifact(artifact)
    return artifact


def render() -> bytes:
    """Rebuild and return the exact canonical artifact bytes."""
    return canonical_json_bytes(build())


def main() -> None:
    raw = render()
    OUT_PATH.write_bytes(raw)
    print(
        f"wrote {OUT_PATH} "
        f"({len(REQUIRED_SERIES_IDS) * len(REQUIRED_CALENDAR_YEARS)} cells)"
    )
    print(f"json sha256: {hashlib.sha256(raw).hexdigest()}")


if __name__ == "__main__":
    main()
