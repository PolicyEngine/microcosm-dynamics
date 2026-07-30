"""Build non-authoritative source-identity evidence for entry 11.

The ratified design requires final physical, alias, and arithmetic registries
to cover both official artifact vintages.  The committed bytes do not support
the final vintage-2 authority, so this module does not mint an artifact
vintage identity or expose a final registry.  It instead records the complete
source-identity evidence that can be established now:

* all 120 cells in the committed vintage-1 level-anchor artifact, after an
  exact offline re-render of that artifact;
* all 825 Table 4.B2/4.B11 cells in the hash-verified entry-11 re-extraction;
* the 24 overlapping vintage-1/B11 cells and every source-defined B2/B11
  primitive or structural sibling relation; and
* 275 structural-only arithmetic rules whose definition hashes are computed
  from exact raw HTML cell fragments selected from the verified Table 4.B11
  bytes.

The occurrence-scoped physical IDs deliberately distinguish the committed
vintage-1 occurrence from the entry-11 re-extraction occurrence.  That
namespace is evidence-only: the design does not say whether identical
cross-artifact occurrences receive one physical ID or two occurrence IDs.
The stable structural locator follows the design's exact seven-part tuple law
and therefore matches for the 24 republished cells.

Run from the repository root for an offline validation summary::

    python scripts/build_covered_earnings_source_identity_evidence.py
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from itertools import combinations
from pathlib import Path
from typing import Any

import build_ssa_covered_earnings_calibration_targets as entry11
import build_ssa_level_anchors as entry10

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = (
    ROOT
    / "data"
    / "external"
    / "covered_earnings_source_identity_evidence_v1.json"
)

SCHEMA_VERSION = "covered_earnings_source_identity_evidence.v1"
PHYSICAL_SOURCE_CELL_SPECS_SCHEMA_VERSION = "physical_source_cell_specs.v1"
OFFICIAL_SOURCE_ALIAS_SPECS_SCHEMA_VERSION = "official_source_alias_specs.v1"
OFFICIAL_SOURCE_ARITHMETIC_RULE_SPECS_SCHEMA_VERSION = (
    "official_source_arithmetic_rule_specs.v1"
)

PUBLICATION_FAMILY_SUPPLEMENT = "ssa_annual_statistical_supplement"
PUBLICATION_FAMILY_TRUSTEES = "ssa_oasdi_trustees_report"
SUPPLEMENT_EDITION_ID = "2025"
CANONICAL_B11_TABLE_ID = "table4.b11"
TARGET_YEARS = tuple(range(1968, 2023))

VINTAGE1_OCCURRENCE = "committed_vintage1"
ENTRY11_OCCURRENCE = "entry11_source_reextraction"
OCCURRENCE_NAMESPACE = "covered_earnings_source_evidence_occurrence.v1"
PINNED_CANONICAL_SIZE_BYTES = 1_515_354
PINNED_CANONICAL_SHA256 = (
    "130fbcbdf1b78c871ac47391f6eaadb1a74f9f3eadcb8827c997f3a6982c8e3b"
)

PHYSICAL_SOURCE_CELL_FIELDS = (
    "physical_cell_id",
    "structural_locator_id",
    "publication_family_id",
    "edition_id",
    "source_document_id",
    "table_id",
    "row_path",
    "nested_column_header_path",
    "calendar_year",
    "as_published_token_sha256",
    "normalized_semantic_sha256",
    "full_source_sha256",
)
OFFICIAL_SOURCE_ALIAS_FIELDS = (
    "alias_group_id",
    "left_physical_cell_id",
    "right_physical_cell_id",
    "relation",
    "effective_calendar_year",
    "arithmetic_rule_id",
    "adjudication",
)
OFFICIAL_SOURCE_ARITHMETIC_RULE_FIELDS = (
    "arithmetic_rule_id",
    "effective_calendar_year",
    "relation_class",
    "ordered_operand_structural_locator_ids",
    "output_structural_locator_id",
    "sibling_structural_locator_ids",
    "assertion_scope",
    "numeric_validation_law",
    "formula_ast",
    "source_definition_locator_id",
    "source_definition_fragment_sha256",
)
SOURCE_DEFINITION_FRAGMENT_FIELDS = (
    "source_definition_locator_id",
    "publication_family_id",
    "edition_id",
    "source_document_id",
    "table_id",
    "citation_coordinates",
    "composite_hash_basis",
    "exact_raw_html_cells_utf8",
    "source_definition_fragment_sha256",
)

SHARED_PRIMITIVES = (
    ("c11", "workers_wage", "wage_worker_count"),
    ("c12", "workers_self_employment", "self_employment_worker_count"),
    ("c13", "taxable_earnings_wage", "wage_taxable_earnings"),
    (
        "c17",
        "taxable_earnings_self_employment",
        "self_employment_taxable_earnings",
    ),
)

TOTAL_COMPONENT_GROUPS = (
    {
        "group_id": "b11_worker_membership",
        "relation_class": "worker_membership",
        "components": (
            "workers_total",
            "workers_wage",
            "workers_self_employment",
        ),
        "ordered_operands": (
            "workers_wage",
            "workers_self_employment",
        ),
        "output": "workers_total",
        "definition_key": "worker_membership",
    },
    {
        "group_id": "b11_taxable_earnings_components",
        "relation_class": "total_component",
        "components": (
            "taxable_earnings_total",
            "taxable_earnings_wage",
            "taxable_earnings_self_employment",
        ),
        "ordered_operands": (
            "taxable_earnings_wage",
            "taxable_earnings_self_employment",
        ),
        "output": "taxable_earnings_total",
        "definition_key": "taxable_earnings_components",
    },
    {
        "group_id": "b11_contribution_components",
        "relation_class": "total_component",
        "components": (
            "contributions_total",
            "contributions_wage",
            "contributions_self_employment",
        ),
        "ordered_operands": (
            "contributions_wage",
            "contributions_self_employment",
        ),
        "output": "contributions_total",
        "definition_key": "contribution_components",
    },
)

TAXABLE_CONTRIBUTION_GROUPS = (
    {
        "group_id": "b11_wage_taxable_earnings_gross_contribution",
        "relation_class": "taxable_earnings_gross_contribution",
        "components": (
            "taxable_earnings_wage",
            "contributions_wage",
        ),
        "ordered_operands": ("taxable_earnings_wage",),
        "output": "contributions_wage",
        "definition_key": "wage_taxable_earnings_gross_contribution",
    },
    {
        "group_id": (
            "b11_self_employment_taxable_earnings_gross_contribution"
        ),
        "relation_class": "taxable_earnings_gross_contribution",
        "components": (
            "taxable_earnings_self_employment",
            "contributions_self_employment",
        ),
        "ordered_operands": ("taxable_earnings_self_employment",),
        "output": "contributions_self_employment",
        "definition_key": (
            "self_employment_taxable_earnings_gross_contribution"
        ),
    },
)
ARITHMETIC_GROUPS = TOTAL_COMPONENT_GROUPS + TAXABLE_CONTRIBUTION_GROUPS

VINTAGE1_B11_SERIES_TO_COMPONENT = {
    "oasdi_workers_with_taxable_earnings": "workers_total",
    "oasdi_reported_taxable_earnings": "taxable_earnings_total",
    "oasdi_gross_contributions": "contributions_total",
}

RELATION_ADJUDICATION = {
    "same_physical_cell": "identity_by_structural_locator",
    "cross_vintage_republication": ("republication_by_registered_source_rule"),
    "shared_primitive": "shared_primitive_by_registered_source_rule",
    "exact_arithmetic_sibling": (
        "exact_arithmetic_sibling_by_registered_rule"
    ),
    "structural_formula_sibling": (
        "structural_formula_sibling_by_registered_definition"
    ),
}

_HEX_64 = re.compile(r"[0-9a-f]{64}")
_RAW_CELL = re.compile(
    rb"<(?P<tag>th|td)\b[^>]*>.*?</(?P=tag)>",
    flags=re.DOTALL,
)


class EvidenceValidationError(ValueError):
    """Source-identity evidence violates a frozen shape or derivation law."""


def canonical_json_bytes(value: Any) -> bytes:
    """Return the repository's canonical JSON encoding."""

    return entry10.canonical_json_bytes(value)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_canonical(value: Any) -> str:
    return _sha256_bytes(canonical_json_bytes(value))


def _canonical_table_id(table_id: str) -> str:
    lowered = table_id.lower()
    return lowered if lowered.startswith("table") else f"table{lowered}"


def _publication_identity(
    source_document_id: str,
    edition_or_report_year: int,
) -> tuple[str, str]:
    if source_document_id.startswith("ssa_supplement_"):
        return PUBLICATION_FAMILY_SUPPLEMENT, str(edition_or_report_year)
    if source_document_id.startswith("ssa_trustees_"):
        return PUBLICATION_FAMILY_TRUSTEES, str(edition_or_report_year)
    raise EvidenceValidationError(
        f"unregistered publication family for {source_document_id!r}"
    )


def _structural_locator_preimage(
    *,
    publication_family_id: str,
    edition_id: str,
    source_document_id: str,
    table_id: str,
    row_path: Sequence[str],
    nested_column_header_path: Sequence[str],
    calendar_year: int,
) -> list[Any]:
    """Return the design's exact seven-part structural-locator tuple."""

    return [
        publication_family_id,
        edition_id,
        source_document_id,
        table_id,
        list(row_path),
        list(nested_column_header_path),
        calendar_year,
    ]


def _physical_occurrence(
    *,
    occurrence: str,
    publication_family_id: str,
    edition_id: str,
    source_document_id: str,
    table_id: str,
    row_path: Sequence[str],
    nested_column_header_path: Sequence[str],
    calendar_year: int,
    as_published: str,
    normalized_value: int,
    stored_unit: str,
    full_source_sha256: str,
) -> dict[str, Any]:
    canonical_table_id = _canonical_table_id(table_id)
    structural_preimage = _structural_locator_preimage(
        publication_family_id=publication_family_id,
        edition_id=edition_id,
        source_document_id=source_document_id,
        table_id=canonical_table_id,
        row_path=row_path,
        nested_column_header_path=nested_column_header_path,
        calendar_year=calendar_year,
    )
    structural_locator_id = _sha256_canonical(structural_preimage)
    token_sha256 = _sha256_bytes(as_published.encode("utf-8"))
    semantic_sha256 = _sha256_canonical(
        {"unit": stored_unit, "value": normalized_value}
    )
    occurrence_preimage = [
        OCCURRENCE_NAMESPACE,
        occurrence,
        *structural_preimage,
        token_sha256,
    ]
    return {
        "physical_cell_id": (
            f"evidence_occurrence:{occurrence}:"
            f"{_sha256_canonical(occurrence_preimage)}"
        ),
        "structural_locator_id": structural_locator_id,
        "publication_family_id": publication_family_id,
        "edition_id": edition_id,
        "source_document_id": source_document_id,
        "table_id": canonical_table_id,
        "row_path": list(row_path),
        "nested_column_header_path": list(nested_column_header_path),
        "calendar_year": calendar_year,
        "as_published_token_sha256": token_sha256,
        "normalized_semantic_sha256": semantic_sha256,
        "full_source_sha256": full_source_sha256,
    }


def _verified_vintage1_artifact() -> tuple[dict[str, Any], bytes]:
    """Re-render and verify the checked-in vintage-1 artifact exactly."""

    checked_bytes = entry10.OUT_PATH.read_bytes()
    rendered_bytes = entry10.render()
    if checked_bytes != rendered_bytes:
        raise EvidenceValidationError(
            "checked-in vintage-1 artifact differs from its offline re-render"
        )
    artifact = json.loads(checked_bytes)
    entry10._validate_artifact(artifact)
    observation_count = sum(
        len(determination["observations"])
        for determination in artifact["determinations"].values()
    )
    if observation_count != 120:
        raise EvidenceValidationError(
            f"vintage-1 artifact contains {observation_count}, not 120, cells"
        )
    return artifact, checked_bytes


def _build_physical_occurrences() -> tuple[
    list[dict[str, Any]],
    dict[tuple[str, int], str],
    dict[str, str],
    dict[str, Any],
]:
    vintage1, vintage1_bytes = _verified_vintage1_artifact()
    entry11_evidence = entry11.extract_b2_b11_source_evidence()
    if len(entry11_evidence["observations"]) != 825:
        raise EvidenceValidationError("entry-11 evidence is not 825 cells")

    physical_rows: list[dict[str, Any]] = []
    vintage1_b11_ids: dict[tuple[str, int], str] = {}
    entry11_ids: dict[str, str] = {}

    source_manifest = vintage1["source_documents"]
    series_specs = {spec.series_id: spec for spec in entry10.SERIES_SPECS}
    for series_id in entry10.REQUIRED_SERIES_IDS:
        series = series_specs[series_id]
        table_spec = entry10.TABLE_SPECS[series.table_id]
        publication_family_id, edition_id = _publication_identity(
            table_spec.source_document_id,
            table_spec.edition_or_report_year,
        )
        source_sha256 = source_manifest[table_spec.source_document_id][
            "sha256"
        ]
        observations = vintage1["determinations"][series_id]["observations"]
        for observation in observations:
            row = _physical_occurrence(
                occurrence=VINTAGE1_OCCURRENCE,
                publication_family_id=publication_family_id,
                edition_id=edition_id,
                source_document_id=observation["source_document_id"],
                table_id=observation["source_table_id"],
                row_path=observation["source_row_header_path"],
                nested_column_header_path=observation[
                    "source_column_header_path"
                ],
                calendar_year=observation["year"],
                as_published=observation["as_published"],
                normalized_value=observation["value"],
                stored_unit=observation["stored_unit"],
                full_source_sha256=source_sha256,
            )
            physical_rows.append(row)
            if series_id in VINTAGE1_B11_SERIES_TO_COMPONENT:
                component_id = VINTAGE1_B11_SERIES_TO_COMPONENT[series_id]
                vintage1_b11_ids[(component_id, observation["year"])] = row[
                    "physical_cell_id"
                ]

    for observation in entry11_evidence["observations"]:
        row = _physical_occurrence(
            occurrence=ENTRY11_OCCURRENCE,
            publication_family_id=PUBLICATION_FAMILY_SUPPLEMENT,
            edition_id=SUPPLEMENT_EDITION_ID,
            source_document_id=observation["source_document_id"],
            table_id=observation["table_id"],
            row_path=observation["row_path"],
            nested_column_header_path=observation["nested_column_header_path"],
            calendar_year=observation["calendar_year"],
            as_published=observation["as_published"],
            normalized_value=observation["normalized_value"],
            stored_unit=observation["stored_unit"],
            full_source_sha256=observation["source_sha256"],
        )
        physical_rows.append(row)
        entry11_ids[observation["source_cell_id"]] = row["physical_cell_id"]

    if len(physical_rows) != 945:
        raise EvidenceValidationError(
            f"physical occurrence count {len(physical_rows)} != 945"
        )
    if len(vintage1_b11_ids) != 24:
        raise EvidenceValidationError("vintage-1 B11 overlap is not 24 cells")
    if len(entry11_ids) != 825:
        raise EvidenceValidationError(
            "entry-11 physical lookup is not 825 cells"
        )

    verification = {
        "vintage1_artifact_path": str(entry10.OUT_PATH.relative_to(ROOT)),
        "vintage1_artifact_sha256": _sha256_bytes(vintage1_bytes),
        "vintage1_artifact_size_bytes": len(vintage1_bytes),
        "vintage1_artifact_observation_count": 120,
        "vintage1_reproduction": "exact_byte_equality_pass",
        "entry11_evidence_observation_count": 825,
        "entry11_source_document_id": entry11.SOURCE_DOCUMENT_ID,
        "entry11_full_source_sha256": entry11.SOURCE_SHA256,
        "entry11_source_size_bytes": entry11.SOURCE_SIZE_BYTES,
        "network_capture": False,
    }
    return (
        physical_rows,
        vintage1_b11_ids,
        entry11_ids,
        verification,
    )


def _table_section(raw: bytes, section: bytes) -> bytes:
    marker = b'<div class="table" id="table4.b11">'
    if raw.count(marker) != 1:
        raise EvidenceValidationError(
            "Table 4.B11 raw container is not unique"
        )
    table_start = raw.index(marker)
    table_end = raw.find(b"</table>", table_start)
    if table_end < 0:
        raise EvidenceValidationError("Table 4.B11 raw table is unclosed")
    table_raw = raw[table_start : table_end + len(b"</table>")]
    start_tag = b"<" + section + b">"
    end_tag = b"</" + section + b">"
    if table_raw.count(start_tag) != 1 or table_raw.count(end_tag) != 1:
        raise EvidenceValidationError(
            f"Table 4.B11 {section.decode()} is not unique"
        )
    start = table_raw.index(start_tag) + len(start_tag)
    end = table_raw.index(end_tag, start)
    return table_raw[start:end]


def _raw_cells(section_raw: bytes) -> list[bytes]:
    cells = [match.group(0) for match in _RAW_CELL.finditer(section_raw)]
    if not cells:
        raise EvidenceValidationError("raw HTML section contains no cells")
    return cells


def _visible_cell_text(raw_cell: bytes) -> str:
    wrapped = b"<table><tbody><tr>" + raw_cell + b"</tr></tbody></table>"
    tables = entry10._parse_tables(wrapped, "source_definition_fragment")
    if len(tables) != 1 or len(tables[0].rows) != 1:
        raise EvidenceValidationError("raw definition cell is not one cell")
    cells = tables[0].rows[0].cells
    if len(cells) != 1:
        raise EvidenceValidationError("raw definition fragment spans cells")
    return cells[0].text


def _definition_locator_id(citation_coordinates: Sequence[str]) -> str:
    citation_coordinate = "+".join(citation_coordinates)
    return _sha256_canonical(
        [
            PUBLICATION_FAMILY_SUPPLEMENT,
            SUPPLEMENT_EDITION_ID,
            entry11.SOURCE_DOCUMENT_ID,
            CANONICAL_B11_TABLE_ID,
            citation_coordinate,
        ]
    )


def _composite_fragment_sha256(fragments: Sequence[bytes]) -> str:
    if not fragments or any(b"\x00" in fragment for fragment in fragments):
        raise EvidenceValidationError("invalid source-definition fragments")
    return _sha256_bytes(b"\x00".join(fragments))


def _definition_fragment_row(
    *,
    citation_coordinates: Sequence[str],
    fragments: Sequence[bytes],
) -> dict[str, Any]:
    return {
        "source_definition_locator_id": _definition_locator_id(
            citation_coordinates
        ),
        "publication_family_id": PUBLICATION_FAMILY_SUPPLEMENT,
        "edition_id": SUPPLEMENT_EDITION_ID,
        "source_document_id": entry11.SOURCE_DOCUMENT_ID,
        "table_id": CANONICAL_B11_TABLE_ID,
        "citation_coordinates": list(citation_coordinates),
        "composite_hash_basis": (
            "sha256 of exact raw HTML cell bytes in listed order, "
            "separated by one NUL byte"
        ),
        "exact_raw_html_cells_utf8": [
            fragment.decode("utf-8") for fragment in fragments
        ],
        "source_definition_fragment_sha256": (
            _composite_fragment_sha256(fragments)
        ),
    }


def _source_definition_fragments() -> dict[str, dict[str, Any]]:
    """Select exact B11 definition cells from verified committed bytes."""

    _, raw_by_document_id = entry10.read_verified_snapshots()
    raw = raw_by_document_id[entry11.SOURCE_DOCUMENT_ID]
    if (
        _sha256_bytes(raw) != entry11.SOURCE_SHA256
        or len(raw) != entry11.SOURCE_SIZE_BYTES
    ):
        raise EvidenceValidationError(
            "Table 4.B11 definition source failed byte verification"
        )

    header_cells = _raw_cells(_table_section(raw, b"thead"))
    footer_cells = _raw_cells(_table_section(raw, b"tfoot"))
    header_text = [_visible_cell_text(cell) for cell in header_cells]
    footer_text = [_visible_cell_text(cell) for cell in footer_cells]

    component_paths = [
        spec.nested_column_header_path
        for spec in entry11.TABLE4_B11_COMPONENT_SPECS
    ]
    expected_groups = [component_paths[index][0] for index in (0, 3, 6)]
    expected_children = [path[1] for path in component_paths]
    expected_header = ["Year", *expected_groups, *expected_children]
    if header_text != expected_header:
        raise EvidenceValidationError(
            "Table 4.B11 raw nested-header structure drift"
        )
    footer_prefixes = (
        "SOURCES:",
        "NOTES:",
        "OASDI",
        "a.",
        "b.",
        "c.",
        "d.",
        "e.",
        "f.",
        "g.",
        "CONTACT:",
    )
    if len(footer_text) != len(footer_prefixes) or any(
        not text.startswith(prefix)
        for text, prefix in zip(footer_text, footer_prefixes, strict=True)
    ):
        raise EvidenceValidationError(
            "Table 4.B11 raw footer-coordinate structure drift"
        )

    selected = {
        "worker_membership": (
            ("thead/cell[1]", "tfoot/cell[3]", "tfoot/cell[1]"),
            (header_cells[1], footer_cells[3], footer_cells[1]),
        ),
        "taxable_earnings_components": (
            ("thead/cell[2]", "tfoot/cell[4]", "tfoot/cell[1]"),
            (header_cells[2], footer_cells[4], footer_cells[1]),
        ),
        "contribution_components": (
            ("thead/cell[3]", "tfoot/cell[1]"),
            (header_cells[3], footer_cells[1]),
        ),
        "wage_taxable_earnings_gross_contribution": (
            (
                "thead/cell[2]",
                "thead/cell[8]",
                "thead/cell[3]",
                "thead/cell[11]",
                "tfoot/cell[5]",
                "tfoot/cell[6]",
            ),
            (
                header_cells[2],
                header_cells[8],
                header_cells[3],
                header_cells[11],
                footer_cells[5],
                footer_cells[6],
            ),
        ),
        "self_employment_taxable_earnings_gross_contribution": (
            (
                "thead/cell[2]",
                "thead/cell[9]",
                "thead/cell[3]",
                "thead/cell[12]",
                "tfoot/cell[5]",
                "tfoot/cell[6]",
            ),
            (
                header_cells[2],
                header_cells[9],
                header_cells[3],
                header_cells[12],
                footer_cells[5],
                footer_cells[6],
            ),
        ),
    }
    return {
        key: _definition_fragment_row(
            citation_coordinates=coordinates,
            fragments=fragments,
        )
        for key, (coordinates, fragments) in selected.items()
    }


def _entry11_cell_id(year: int, component_id: str) -> str:
    return f"{CANONICAL_B11_TABLE_ID}/{year}/{component_id}"


def _rule_id(group_id: str, year: int) -> str:
    return f"evidence_arithmetic_rule:{group_id}:{year}"


def _build_arithmetic_rules(
    *,
    physical_by_id: Mapping[str, Mapping[str, Any]],
    entry11_ids: Mapping[str, str],
    definitions: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for year in TARGET_YEARS:
        for group in ARITHMETIC_GROUPS:
            components = group["components"]
            structural_by_component = {
                component: physical_by_id[
                    entry11_ids[_entry11_cell_id(year, component)]
                ]["structural_locator_id"]
                for component in components
            }
            definition = definitions[group["definition_key"]]
            rows.append(
                {
                    "arithmetic_rule_id": _rule_id(
                        group["group_id"],
                        year,
                    ),
                    "effective_calendar_year": year,
                    "relation_class": group["relation_class"],
                    "ordered_operand_structural_locator_ids": [
                        structural_by_component[component]
                        for component in group["ordered_operands"]
                    ],
                    "output_structural_locator_id": structural_by_component[
                        group["output"]
                    ],
                    "sibling_structural_locator_ids": [
                        structural_by_component[component]
                        for component in components
                    ],
                    "assertion_scope": "structural_dependence_only",
                    "numeric_validation_law": (
                        "not_applicable_no_published_numeric_assertion"
                    ),
                    "formula_ast": None,
                    "source_definition_locator_id": definition[
                        "source_definition_locator_id"
                    ],
                    "source_definition_fragment_sha256": definition[
                        "source_definition_fragment_sha256"
                    ],
                }
            )
    return rows


def _alias_row(
    *,
    relation: str,
    year: int,
    left_physical_cell_id: str,
    right_physical_cell_id: str,
    arithmetic_rule_id: str | None,
) -> dict[str, Any]:
    preimage = [
        relation,
        year,
        left_physical_cell_id,
        right_physical_cell_id,
        arithmetic_rule_id,
    ]
    return {
        "alias_group_id": f"evidence_alias:{_sha256_canonical(preimage)}",
        "left_physical_cell_id": left_physical_cell_id,
        "right_physical_cell_id": right_physical_cell_id,
        "relation": relation,
        "effective_calendar_year": year,
        "arithmetic_rule_id": arithmetic_rule_id,
        "adjudication": RELATION_ADJUDICATION[relation],
    }


def _build_aliases(
    *,
    vintage1_b11_ids: Mapping[tuple[str, int], str],
    entry11_ids: Mapping[str, str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for year in range(2015, 2023):
        for component_id in VINTAGE1_B11_SERIES_TO_COMPONENT.values():
            left = vintage1_b11_ids[(component_id, year)]
            right = entry11_ids[_entry11_cell_id(year, component_id)]
            for relation in (
                "same_physical_cell",
                "cross_vintage_republication",
            ):
                rows.append(
                    _alias_row(
                        relation=relation,
                        year=year,
                        left_physical_cell_id=left,
                        right_physical_cell_id=right,
                        arithmetic_rule_id=None,
                    )
                )

    for year in TARGET_YEARS:
        for b2_component, b11_component, _ in SHARED_PRIMITIVES:
            rows.append(
                _alias_row(
                    relation="shared_primitive",
                    year=year,
                    left_physical_cell_id=entry11_ids[
                        f"table4.b2/{year}/{b2_component}"
                    ],
                    right_physical_cell_id=entry11_ids[
                        _entry11_cell_id(year, b11_component)
                    ],
                    arithmetic_rule_id=None,
                )
            )

    for year in TARGET_YEARS:
        for group in TOTAL_COMPONENT_GROUPS:
            rule_id = _rule_id(group["group_id"], year)
            for left_component, right_component in combinations(
                group["components"],
                2,
            ):
                rows.append(
                    _alias_row(
                        relation="structural_formula_sibling",
                        year=year,
                        left_physical_cell_id=entry11_ids[
                            _entry11_cell_id(year, left_component)
                        ],
                        right_physical_cell_id=entry11_ids[
                            _entry11_cell_id(year, right_component)
                        ],
                        arithmetic_rule_id=rule_id,
                    )
                )

    for year in TARGET_YEARS:
        for group in TAXABLE_CONTRIBUTION_GROUPS:
            left_component, right_component = group["components"]
            rows.append(
                _alias_row(
                    relation="structural_formula_sibling",
                    year=year,
                    left_physical_cell_id=entry11_ids[
                        _entry11_cell_id(year, left_component)
                    ],
                    right_physical_cell_id=entry11_ids[
                        _entry11_cell_id(year, right_component)
                    ],
                    arithmetic_rule_id=_rule_id(group["group_id"], year),
                )
            )

    return rows


def _count_adjudication(
    aliases: Sequence[Mapping[str, Any]],
    rules: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    relation_counts = Counter(row["relation"] for row in aliases)
    total_rule_prefixes = {
        f"evidence_arithmetic_rule:{group['group_id']}:"
        for group in TOTAL_COMPONENT_GROUPS
    }
    b11_group_structural = sum(
        row["relation"] == "structural_formula_sibling"
        and any(
            row["arithmetic_rule_id"].startswith(prefix)
            for prefix in total_rule_prefixes
        )
        for row in aliases
    )
    taxable_contribution_structural = (
        relation_counts["structural_formula_sibling"] - b11_group_structural
    )
    return {
        "registration_status": (
            "evidence_only_final_authority_registration_aborted"
        ),
        "physical_occurrence_count": 945,
        "structural_locator_count": 921,
        "same_physical_cell_alias_count": relation_counts[
            "same_physical_cell"
        ],
        "cross_vintage_republication_alias_count": relation_counts[
            "cross_vintage_republication"
        ],
        "shared_primitive_alias_count": relation_counts["shared_primitive"],
        "b11_group_structural_formula_sibling_alias_count": (
            b11_group_structural
        ),
        "taxable_contribution_structural_formula_sibling_alias_count": (
            taxable_contribution_structural
        ),
        "exact_arithmetic_sibling_alias_count": relation_counts[
            "exact_arithmetic_sibling"
        ],
        "structural_arithmetic_rule_count": len(rules),
        "exact_arithmetic_rule_count": sum(
            row["assertion_scope"] == "exact_published_value_equality"
            for row in rules
        ),
        "source_definition_fragment_count": 5,
        "adjudication": (
            "all published total/component, worker-membership, and "
            "taxable-earnings/gross-contribution relationships are "
            "structural-only; the committed source provides no express "
            "displayed-precision equality guarantee"
        ),
    }


def _build_unvalidated() -> dict[str, Any]:
    (
        physical_rows,
        vintage1_b11_ids,
        entry11_ids,
        source_verification,
    ) = _build_physical_occurrences()
    physical_by_id = {row["physical_cell_id"]: row for row in physical_rows}
    definitions = _source_definition_fragments()
    arithmetic_rules = _build_arithmetic_rules(
        physical_by_id=physical_by_id,
        entry11_ids=entry11_ids,
        definitions=definitions,
    )
    aliases = _build_aliases(
        vintage1_b11_ids=vintage1_b11_ids,
        entry11_ids=entry11_ids,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "authority": {
            "status": "non_authoritative_source_identity_evidence_only",
            "final_registry_registration": "aborted",
            "artifact_vintage_identity_assigned": False,
            "physical_cell_id_namespace": OCCURRENCE_NAMESPACE,
            "physical_cell_id_namespace_status": "non_authoritative",
            "physical_cell_id_namespace_adjudication": (
                "the final physical-ID occurrence law is under-specified; "
                "evidence IDs distinguish the committed vintage-1 and "
                "entry-11 re-extraction occurrences while structural "
                "locators carry the design-specified stable identity"
            ),
        },
        "source_verification": source_verification,
        "physical_source_cell_specs_schema_version": (
            PHYSICAL_SOURCE_CELL_SPECS_SCHEMA_VERSION
        ),
        "physical_source_cell_specs": physical_rows,
        "official_source_alias_specs_schema_version": (
            OFFICIAL_SOURCE_ALIAS_SPECS_SCHEMA_VERSION
        ),
        "official_source_alias_specs": aliases,
        "official_source_arithmetic_rule_specs_schema_version": (
            OFFICIAL_SOURCE_ARITHMETIC_RULE_SPECS_SCHEMA_VERSION
        ),
        "official_source_arithmetic_rule_specs": arithmetic_rules,
        "source_definition_fragments": list(definitions.values()),
        "adjudication": _count_adjudication(aliases, arithmetic_rules),
    }


def _exact_keys(
    value: object,
    keys: Sequence[str],
    where: str,
) -> Mapping[str, Any]:
    if type(value) is not dict or set(value) != set(keys):
        actual = tuple(value) if type(value) is dict else type(value).__name__
        raise EvidenceValidationError(
            f"{where} keys {actual!r} != {tuple(keys)!r}"
        )
    return value


def _validate_evidence_laws(value: object) -> None:
    if type(value) is not dict:
        raise EvidenceValidationError("evidence must be an object")
    physical_rows = value.get("physical_source_cell_specs")
    alias_rows = value.get("official_source_alias_specs")
    arithmetic_rows = value.get("official_source_arithmetic_rule_specs")
    fragments = value.get("source_definition_fragments")
    if (
        type(physical_rows) is not list
        or type(alias_rows) is not list
        or type(arithmetic_rows) is not list
        or type(fragments) is not list
    ):
        raise EvidenceValidationError("registry evidence arrays are missing")

    if len(physical_rows) != 945:
        raise EvidenceValidationError("physical occurrence count drift")
    physical_by_id: dict[str, Mapping[str, Any]] = {}
    structural_ids: set[str] = set()
    for index, candidate in enumerate(physical_rows):
        row = _exact_keys(
            candidate,
            PHYSICAL_SOURCE_CELL_FIELDS,
            f"physical_source_cell_specs[{index}]",
        )
        physical_id = row["physical_cell_id"]
        if (
            type(physical_id) is not str
            or not physical_id.startswith("evidence_occurrence:")
            or physical_id in physical_by_id
        ):
            raise EvidenceValidationError(
                f"invalid or duplicate physical ID at row {index}"
            )
        preimage = _structural_locator_preimage(
            publication_family_id=row["publication_family_id"],
            edition_id=row["edition_id"],
            source_document_id=row["source_document_id"],
            table_id=row["table_id"],
            row_path=row["row_path"],
            nested_column_header_path=row["nested_column_header_path"],
            calendar_year=row["calendar_year"],
        )
        if row["structural_locator_id"] != _sha256_canonical(preimage):
            raise EvidenceValidationError(
                f"physical row {index} structural-locator hash drift"
            )
        for digest_field in (
            "structural_locator_id",
            "as_published_token_sha256",
            "normalized_semantic_sha256",
            "full_source_sha256",
        ):
            digest = row[digest_field]
            if type(digest) is not str or _HEX_64.fullmatch(digest) is None:
                raise EvidenceValidationError(
                    f"physical row {index} invalid {digest_field}"
                )
        if (
            type(row["row_path"]) is not list
            or not row["row_path"]
            or type(row["nested_column_header_path"]) is not list
            or not row["nested_column_header_path"]
            or type(row["calendar_year"]) is not int
        ):
            raise EvidenceValidationError(
                f"physical row {index} invalid structural path"
            )
        physical_by_id[physical_id] = row
        structural_ids.add(row["structural_locator_id"])
    if len(structural_ids) != 921:
        raise EvidenceValidationError("structural-locator count drift")

    fragment_by_locator: dict[str, Mapping[str, Any]] = {}
    for index, candidate in enumerate(fragments):
        row = _exact_keys(
            candidate,
            SOURCE_DEFINITION_FRAGMENT_FIELDS,
            f"source_definition_fragments[{index}]",
        )
        raw_fragments = [
            fragment.encode("utf-8")
            for fragment in row["exact_raw_html_cells_utf8"]
        ]
        if row["source_definition_fragment_sha256"] != (
            _composite_fragment_sha256(raw_fragments)
        ):
            raise EvidenceValidationError(
                f"source definition fragment {index} digest drift"
            )
        if row["source_definition_locator_id"] != _definition_locator_id(
            row["citation_coordinates"]
        ):
            raise EvidenceValidationError(
                f"source definition fragment {index} locator drift"
            )
        locator_id = row["source_definition_locator_id"]
        if locator_id in fragment_by_locator:
            raise EvidenceValidationError("duplicate definition locator")
        fragment_by_locator[locator_id] = row
    if len(fragment_by_locator) != 5:
        raise EvidenceValidationError("source definition count drift")

    if len(arithmetic_rows) != 275:
        raise EvidenceValidationError("arithmetic-rule count drift")
    arithmetic_by_id: dict[str, Mapping[str, Any]] = {}
    for index, candidate in enumerate(arithmetic_rows):
        row = _exact_keys(
            candidate,
            OFFICIAL_SOURCE_ARITHMETIC_RULE_FIELDS,
            f"official_source_arithmetic_rule_specs[{index}]",
        )
        rule_id = row["arithmetic_rule_id"]
        if type(rule_id) is not str or rule_id in arithmetic_by_id:
            raise EvidenceValidationError(
                f"invalid or duplicate arithmetic rule {index}"
            )
        if (
            row["effective_calendar_year"] not in TARGET_YEARS
            or row["relation_class"]
            not in {
                "total_component",
                "taxable_earnings_gross_contribution",
                "worker_membership",
            }
            or row["assertion_scope"] != "structural_dependence_only"
            or row["numeric_validation_law"]
            != "not_applicable_no_published_numeric_assertion"
            or row["formula_ast"] is not None
        ):
            raise EvidenceValidationError(
                f"arithmetic rule {rule_id} is not structural-only"
            )
        operands = row["ordered_operand_structural_locator_ids"]
        siblings = row["sibling_structural_locator_ids"]
        if (
            type(operands) is not list
            or not operands
            or len(operands) != len(set(operands))
            or type(siblings) is not list
            or not siblings
            or len(siblings) != len(set(siblings))
            or not set(operands).issubset(siblings)
            or row["output_structural_locator_id"] not in siblings
            or not set(siblings).issubset(structural_ids)
        ):
            raise EvidenceValidationError(
                f"arithmetic rule {rule_id} topology drift"
            )
        definition = fragment_by_locator.get(
            row["source_definition_locator_id"]
        )
        if (
            definition is None
            or row["source_definition_fragment_sha256"]
            != definition["source_definition_fragment_sha256"]
        ):
            raise EvidenceValidationError(
                f"arithmetic rule {rule_id} definition drift"
            )
        arithmetic_by_id[rule_id] = row

    if len(alias_rows) != 873:
        raise EvidenceValidationError("alias count drift")
    referenced_rules: set[str] = set()
    seen_alias_ids: set[str] = set()
    for index, candidate in enumerate(alias_rows):
        row = _exact_keys(
            candidate,
            OFFICIAL_SOURCE_ALIAS_FIELDS,
            f"official_source_alias_specs[{index}]",
        )
        if (
            type(row["alias_group_id"]) is not str
            or row["alias_group_id"] in seen_alias_ids
        ):
            raise EvidenceValidationError(f"alias {index} ID drift")
        seen_alias_ids.add(row["alias_group_id"])
        try:
            left = physical_by_id[row["left_physical_cell_id"]]
            right = physical_by_id[row["right_physical_cell_id"]]
        except KeyError as error:
            raise EvidenceValidationError(
                f"alias {index} has a missing physical foreign key"
            ) from error
        relation = row["relation"]
        if (
            relation not in RELATION_ADJUDICATION
            or row["adjudication"] != RELATION_ADJUDICATION[relation]
            or row["effective_calendar_year"] != left["calendar_year"]
            or row["effective_calendar_year"] != right["calendar_year"]
        ):
            raise EvidenceValidationError(f"alias {index} relation drift")
        rule_id = row["arithmetic_rule_id"]
        if relation.endswith("_arithmetic_sibling") or relation == (
            "structural_formula_sibling"
        ):
            if rule_id not in arithmetic_by_id:
                raise EvidenceValidationError(
                    f"alias {index} arithmetic-rule foreign-key drift"
                )
            referenced_rules.add(rule_id)
            rule = arithmetic_by_id[rule_id]
            if {
                left["structural_locator_id"],
                right["structural_locator_id"],
            }.difference(rule["sibling_structural_locator_ids"]):
                raise EvidenceValidationError(
                    f"alias {index} is outside its rule component"
                )
        elif rule_id is not None:
            raise EvidenceValidationError(
                f"alias {index} unexpectedly references a rule"
            )
        if relation in {
            "same_physical_cell",
            "cross_vintage_republication",
        }:
            compared_fields = (
                "structural_locator_id",
                "as_published_token_sha256",
                "normalized_semantic_sha256",
                "full_source_sha256",
            )
            if any(left[field] != right[field] for field in compared_fields):
                raise EvidenceValidationError(
                    f"alias {index} lacks exact republication proof"
                )

    if referenced_rules != set(arithmetic_by_id):
        raise EvidenceValidationError(
            "not every arithmetic rule is referenced by an alias"
        )
    expected_adjudication = _count_adjudication(
        alias_rows,
        arithmetic_rows,
    )
    if value.get("adjudication") != expected_adjudication:
        raise EvidenceValidationError("adjudication count drift")
    fixed_counts = (
        expected_adjudication["same_physical_cell_alias_count"] == 24
        and expected_adjudication["cross_vintage_republication_alias_count"]
        == 24
        and expected_adjudication["shared_primitive_alias_count"] == 220
        and expected_adjudication[
            "b11_group_structural_formula_sibling_alias_count"
        ]
        == 495
        and expected_adjudication[
            "taxable_contribution_structural_formula_sibling_alias_count"
        ]
        == 110
        and expected_adjudication["exact_arithmetic_sibling_alias_count"] == 0
        and expected_adjudication["structural_arithmetic_rule_count"] == 275
        and expected_adjudication["exact_arithmetic_rule_count"] == 0
    )
    if not fixed_counts:
        raise EvidenceValidationError("source-identity closure count drift")


def build() -> dict[str, Any]:
    """Build and validate the complete evidence-only identity registries."""

    evidence = _build_unvalidated()
    _validate_evidence_laws(evidence)
    return evidence


def validate_evidence(value: object) -> None:
    """Re-resolve sources and require exact equality plus all registry laws."""

    _validate_evidence_laws(value)
    expected = build()
    if value != expected:
        raise EvidenceValidationError(
            "evidence differs from a fresh committed-source re-resolution"
        )


def load_pinned_evidence() -> dict[str, Any]:
    """Load canonical evidence only after independent byte pins pass."""

    raw = OUT_PATH.read_bytes()
    if len(raw) != PINNED_CANONICAL_SIZE_BYTES:
        raise EvidenceValidationError(
            f"pinned evidence size {len(raw)} != "
            f"{PINNED_CANONICAL_SIZE_BYTES}"
        )
    digest = _sha256_bytes(raw)
    if digest != PINNED_CANONICAL_SHA256:
        raise EvidenceValidationError(
            f"pinned evidence sha256 {digest} != " f"{PINNED_CANONICAL_SHA256}"
        )
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise EvidenceValidationError(
            "pinned evidence is not canonical JSON"
        ) from error
    if canonical_json_bytes(value) != raw:
        raise EvidenceValidationError(
            "pinned evidence bytes violate canonical serialization"
        )
    _validate_evidence_laws(value)
    return value


def validate_pinned_evidence() -> None:
    """Require both independent byte pins and fresh source reproduction."""

    pinned = load_pinned_evidence()
    validate_evidence(pinned)


def render() -> bytes:
    """Return canonical evidence bytes without assigning artifact authority."""

    return canonical_json_bytes(build())


def main() -> None:
    raw = render()
    if (
        len(raw) != PINNED_CANONICAL_SIZE_BYTES
        or _sha256_bytes(raw) != PINNED_CANONICAL_SHA256
    ):
        raise EvidenceValidationError(
            "rendered evidence differs from independent canonical pins"
        )
    OUT_PATH.write_bytes(raw)
    validate_pinned_evidence()
    evidence = json.loads(raw)
    print(
        "wrote and validated non-authoritative source-identity evidence: "
        f"{len(evidence['physical_source_cell_specs'])} occurrences, "
        f"{len(evidence['official_source_alias_specs'])} aliases, "
        f"{len(evidence['official_source_arithmetic_rule_specs'])} rules; "
        f"canonical sha256={_sha256_bytes(raw)}"
    )


if __name__ == "__main__":
    main()
