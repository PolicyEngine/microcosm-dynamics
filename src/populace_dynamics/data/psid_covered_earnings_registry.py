"""Frozen PSID reference-year law and crosswalk registration boundary.

The production year map is independent of both reader availability and the
questionnaire crosswalk.  In particular, a staged post-cutoff interview
cannot turn its prior-year answer into a direct production source.

The official Amendment-1 crosswalk identity is v2.  It cannot be emitted
until the independently ratified questionnaire slot specifications and
source-field inventory exist, so this module exposes a typed fail-closed
boundary rather than an empty or provisional official crosswalk.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any, NoReturn

CROSSWALK_SCHEMA_VERSION = "psid_covered_earnings_crosswalk.v2"
CROSSWALK_ARTIFACT_ID = CROSSWALK_SCHEMA_VERSION

PRODUCTION_REFERENCE_YEARS: tuple[int, ...] = tuple(range(1968, 2023))
DIRECT_REFERENCE_YEARS: tuple[int, ...] = (
    *range(1968, 1997),
    *range(1998, 2013, 2),
)
STRUCTURAL_GAP_REFERENCE_YEARS: tuple[int, ...] = tuple(range(1997, 2012, 2))
CLAIM_SPECIFIC_REFERENCE_YEARS: tuple[int, ...] = (2013,)
BOUNDARY_REFERENCE_YEARS: tuple[int, ...] = (2014,)
PROJECTED_REFERENCE_YEARS: tuple[int, ...] = tuple(range(2015, 2023))

STAGED_INTERVIEW_WAVES: tuple[int, ...] = (
    *range(1968, 1998),
    *range(1999, 2024, 2),
)
DIRECT_INVENTORY_WAVES: tuple[int, ...] = (
    *range(1969, 1998),
    *range(1999, 2014, 2),
)
OUTSIDE_SUPPORT_INVENTORY_WAVES: tuple[int, ...] = (1968,)
POST_CUTOFF_INVENTORY_WAVES: tuple[int, ...] = (
    2015,
    2017,
    2019,
    2021,
    2023,
)

_YEAR_SOURCE_CLASSES = (
    "direct_questionnaire",
    "structural_gap_imputed",
    "claim_specific_boundary_gap",
    "boundary_2014",
    "projected",
)
_INVENTORY_YEAR_DISPOSITIONS = (
    "direct_questionnaire",
    "inventory_only_outside_production_support",
    "inventory_only_post_cutoff",
)


class ReferenceRegistryError(ValueError):
    """Raised when a year registry violates the frozen law."""


class CrosswalkRegistrationRequiredError(RuntimeError):
    """Raised instead of returning an unratified official crosswalk."""

    def __init__(self, item_ids: Sequence[str]):
        self.target_schema_version = CROSSWALK_SCHEMA_VERSION
        self.target_artifact_id = CROSSWALK_ARTIFACT_ID
        self.item_ids = tuple(item_ids)
        super().__init__(
            f"{CROSSWALK_ARTIFACT_ID} registration aborted; "
            f"registration_required: {', '.join(self.item_ids)}"
        )


@dataclass(frozen=True, slots=True)
class ProductionYearRow:
    """One independently frozen production-year coordinate."""

    earnings_reference_year: int
    interview_wave: int | None
    year_source_class: str


@dataclass(frozen=True, slots=True)
class InventoryWaveRow:
    """One staged interview wave's all-key inventory disposition."""

    interview_wave: int
    earnings_reference_year: int
    inventory_year_disposition: str


@dataclass(frozen=True, slots=True)
class ReferenceEraSpec:
    """A reference-year era; bounds never use interview-year aliases."""

    reference_era_id: str
    first_reference_year: int
    last_reference_year: int


REFERENCE_ERA_SPECS: tuple[ReferenceEraSpec, ...] = (
    ReferenceEraSpec("ry1968_1974_early_totals", 1968, 1974),
    ReferenceEraSpec("ry1975_1977_spouse_concept_seam", 1975, 1977),
    ReferenceEraSpec("ry1978_1992_pre_er_totals", 1978, 1992),
    ReferenceEraSpec("ry1993_2001_er_biennial_transition", 1993, 2001),
    ReferenceEraSpec("ry2002_2014_modern_boundary", 2002, 2014),
)

SOURCE_CONCEPT_SEAMS: tuple[Mapping[str, Any], ...] = (
    {
        "seam_id": "spouse_reference_1975_mixed",
        "interview_wave": 1976,
        "earnings_reference_year": 1975,
        "role": "spouse_or_partner",
        "raw_field_id": "V4379",
        "remuneration_type": "mixed",
        "registration_required_item_id": None,
    },
    {
        "seam_id": "spouse_reference_1976_unresolved",
        "interview_wave": 1977,
        "earnings_reference_year": 1976,
        "role": "spouse_or_partner",
        "raw_field_id": "V5289",
        "remuneration_type": None,
        "registration_required_item_id": "V-B6",
    },
    {
        "seam_id": "spouse_reference_1977_unresolved",
        "interview_wave": 1978,
        "earnings_reference_year": 1977,
        "role": "spouse_or_partner",
        "raw_field_id": "V5788",
        "remuneration_type": None,
        "registration_required_item_id": "V-B6",
    },
    {
        "seam_id": "pre_er_farm_business_exact_once",
        "first_reference_year": 1978,
        "last_reference_year": 1992,
        "source_concept": (
            "edited_role_totals_include_applicable_farm_business_labor"
        ),
        "combination_law": "separate_fields_validate_or_split_never_add",
    },
    {
        "seam_id": "er_farm_business_exact_once",
        "first_reference_year": 1993,
        "last_reference_year": 2001,
        "first_interview_wave": 1994,
        "source_concept": (
            "er_role_totals_and_separate_farm_business_components"
        ),
        "combination_law": "combine_exactly_once",
    },
    {
        "seam_id": "modern_bc_de_direct",
        "first_reference_year": 2002,
        "last_reference_year": 2012,
        "first_interview_wave": 2003,
        "interview_waves": tuple(range(2003, 2014, 2)),
        "gap_law": "odd_reference_years_are_structural_gap_imputed",
    },
    {
        "seam_id": "modern_bc_de_post_cutoff",
        "first_reference_year": 2014,
        "last_reference_year": 2022,
        "interview_waves": POST_CUTOFF_INVENTORY_WAVES,
        "inventory_year_disposition": "inventory_only_post_cutoff",
        "production_use": "lineage_only",
    },
)


def _require_json_integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ReferenceRegistryError(f"{name} must be a JSON integer")
    return value


def earnings_reference_year(interview_wave: int) -> int:
    """Return the income-attachment coordinate, always wave minus one."""

    wave = _require_json_integer(interview_wave, "interview_wave")
    if wave not in STAGED_INTERVIEW_WAVES:
        raise ReferenceRegistryError(f"unstaged interview wave: {wave}")
    return wave - 1


def year_source_class(reference_year: int) -> str:
    """Return the frozen production source class for 1968--2022."""

    year = _require_json_integer(reference_year, "reference_year")
    if year in DIRECT_REFERENCE_YEARS:
        return "direct_questionnaire"
    if year in STRUCTURAL_GAP_REFERENCE_YEARS:
        return "structural_gap_imputed"
    if year in CLAIM_SPECIFIC_REFERENCE_YEARS:
        return "claim_specific_boundary_gap"
    if year in BOUNDARY_REFERENCE_YEARS:
        return "boundary_2014"
    if year in PROJECTED_REFERENCE_YEARS:
        return "projected"
    raise ReferenceRegistryError(
        f"reference year outside production support: {year}"
    )


def direct_interview_wave(reference_year: int) -> int | None:
    """Return the direct source wave, or null for every nondirect year."""

    year = _require_json_integer(reference_year, "reference_year")
    source_class = year_source_class(year)
    if source_class == "direct_questionnaire":
        return year + 1
    return None


def inventory_year_disposition(interview_wave: int) -> str:
    """Return the independent all-key disposition for a staged wave."""

    wave = _require_json_integer(interview_wave, "interview_wave")
    if wave in DIRECT_INVENTORY_WAVES:
        return "direct_questionnaire"
    if wave in OUTSIDE_SUPPORT_INVENTORY_WAVES:
        return "inventory_only_outside_production_support"
    if wave in POST_CUTOFF_INVENTORY_WAVES:
        return "inventory_only_post_cutoff"
    raise ReferenceRegistryError(f"unstaged interview wave: {wave}")


def production_year_rows() -> tuple[ProductionYearRow, ...]:
    """Materialize the complete 55-row production domain."""

    return tuple(
        ProductionYearRow(
            earnings_reference_year=year,
            interview_wave=direct_interview_wave(year),
            year_source_class=year_source_class(year),
        )
        for year in PRODUCTION_REFERENCE_YEARS
    )


def inventory_wave_rows() -> tuple[InventoryWaveRow, ...]:
    """Materialize the complete 43-row staged-wave domain."""

    return tuple(
        InventoryWaveRow(
            interview_wave=wave,
            earnings_reference_year=earnings_reference_year(wave),
            inventory_year_disposition=inventory_year_disposition(wave),
        )
        for wave in STAGED_INTERVIEW_WAVES
    )


def reference_era(reference_year: int) -> ReferenceEraSpec:
    """Resolve one pre/projection-boundary reference-year era."""

    year = _require_json_integer(reference_year, "reference_year")
    matches = tuple(
        spec
        for spec in REFERENCE_ERA_SPECS
        if spec.first_reference_year <= year <= spec.last_reference_year
    )
    if len(matches) != 1:
        raise ReferenceRegistryError(
            f"reference year has no unique registered era: {year}"
        )
    return matches[0]


def _plain_rows(rows: Sequence[object]) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        if hasattr(row, "__dataclass_fields__"):
            result.append(asdict(row))
        elif isinstance(row, Mapping):
            result.append(dict(row))
        else:
            raise ReferenceRegistryError(
                f"registry row is not a mapping/dataclass: {row!r}"
            )
    return result


def _canonical_hash(rows: Sequence[object]) -> str:
    encoded = json.dumps(
        _plain_rows(rows),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_production_year_rows(rows: Sequence[object]) -> None:
    """Exact-compare supplied production rows with the independent law."""

    actual = _plain_rows(rows)
    expected = _plain_rows(production_year_rows())
    if actual != expected:
        raise ReferenceRegistryError(
            "production year rows do not exact-match the frozen domain"
        )
    counts = Counter(row["year_source_class"] for row in actual)
    if counts != {
        "direct_questionnaire": 37,
        "structural_gap_imputed": 8,
        "claim_specific_boundary_gap": 1,
        "boundary_2014": 1,
        "projected": 8,
    }:
        raise ReferenceRegistryError("production source-class counts drifted")
    if set(counts) != set(_YEAR_SOURCE_CLASSES):
        raise ReferenceRegistryError("production source-class domain drifted")


def validate_inventory_wave_rows(rows: Sequence[object]) -> None:
    """Exact-compare supplied inventory rows with the independent law."""

    actual = _plain_rows(rows)
    expected = _plain_rows(inventory_wave_rows())
    if actual != expected:
        raise ReferenceRegistryError(
            "inventory wave rows do not exact-match the frozen domain"
        )
    counts = Counter(row["inventory_year_disposition"] for row in actual)
    if counts != {
        "direct_questionnaire": 37,
        "inventory_only_outside_production_support": 1,
        "inventory_only_post_cutoff": 5,
    }:
        raise ReferenceRegistryError(
            "inventory year-disposition counts drifted"
        )
    if set(counts) != set(_INVENTORY_YEAR_DISPOSITIONS):
        raise ReferenceRegistryError(
            "inventory year-disposition domain drifted"
        )


def validate_reference_eras() -> None:
    """Require the registered eras to partition 1968--2014 exactly."""

    expanded = [
        year
        for spec in REFERENCE_ERA_SPECS
        for year in range(
            spec.first_reference_year,
            spec.last_reference_year + 1,
        )
    ]
    if expanded != list(range(1968, 2015)):
        raise ReferenceRegistryError(
            "reference-era registry has a gap, overlap, or reorder"
        )


def crosswalk_registration_status(
    dictionary_audit: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the explicit non-artifact status of the official crosswalk."""

    abort = dictionary_audit.get("inventory_ratification_abort")
    if not isinstance(abort, Mapping):
        raise ReferenceRegistryError(
            "dictionary audit lacks inventory ratification status"
        )
    item_ids = abort.get("registration_required_item_ids")
    if item_ids != ["V-B5", "V-B6", "V-B8"]:
        raise ReferenceRegistryError(
            "dictionary audit registration-required items drifted"
        )
    return {
        "target_schema_version": CROSSWALK_SCHEMA_VERSION,
        "target_artifact_id": CROSSWALK_ARTIFACT_ID,
        "status": "registration_required",
        "failure_disposition": "abort_crosswalk_registration",
        "unavailable_prerequisites": [
            "psid_questionnaire_slot_specs.v1",
            "psid_covered_earnings_source_field_inventory.v1",
        ],
        "registration_required_item_ids": list(item_ids),
    }


def require_ratified_crosswalk(
    dictionary_audit: Mapping[str, Any],
) -> NoReturn:
    """Always fail closed while the independent inventory is unavailable."""

    status = crosswalk_registration_status(dictionary_audit)
    raise CrosswalkRegistrationRequiredError(
        status["registration_required_item_ids"]
    )


PRODUCTION_YEAR_ROWS_SHA256 = (
    "bdf7d2b4740f6c3385b46982f595573a9d7385f6aeef86a9a3972385b96debe9"
)
INVENTORY_WAVE_ROWS_SHA256 = (
    "dd91873b7964afea577e094a2598e21ec8d3d14f977ab6ea688913d05045b2ab"
)


def validate_frozen_registry() -> None:
    """Validate every built-in count, mapping, era, and anchor hash."""

    production = production_year_rows()
    inventory = inventory_wave_rows()
    validate_production_year_rows(production)
    validate_inventory_wave_rows(inventory)
    validate_reference_eras()
    if _canonical_hash(production) != PRODUCTION_YEAR_ROWS_SHA256:
        raise ReferenceRegistryError("production year registry hash drifted")
    if _canonical_hash(inventory) != INVENTORY_WAVE_ROWS_SHA256:
        raise ReferenceRegistryError("inventory wave registry hash drifted")


validate_frozen_registry()
