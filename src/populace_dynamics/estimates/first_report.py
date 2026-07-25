"""Pure assembly of the registered first-estimates publication artifact.

This module is deliberately post-compute.  It accepts the career/inclusion,
benefit-ledger, and revenue-ledger results for the twenty registered draws,
checks that those objects still describe one coherent report, and converts
them into the frozen publication schema.  It does not load inputs, project a
population, write an artifact, or provide a recovery path.
"""

from __future__ import annotations

import copy
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from numbers import Integral, Real
from typing import Any

from populace_dynamics.estimates.career import (
    BirthSource,
    ClaimOrigin,
    InclusionResult,
    NonClaimantPath,
)
from populace_dynamics.estimates.ledgers import (
    BENEFIT_MEASURE_LABEL,
    DRAW_INDICES,
    EVIDENCE_LABELS,
    REPORT_YEARS,
    AcrossDrawLedgers,
    AcrossDrawTableRow,
    BenefitLedger,
    RevenueLedger,
    aggregate_benefit_draws,
    aggregate_revenue_draws,
)
from populace_dynamics.estimates.publication import (
    ARTIFACT_SCHEMA_VERSION,
    CANONICAL_EXECUTION_RULE,
    CERTIFIES_NOTHING,
    GAP_BLOCK,
    table_record,
    validate_first_estimates_artifact,
)

__all__ = [
    "CONTEXT_RATIO_DISCLOSURE",
    "FirstReportDrawBundle",
    "build_first_estimates_artifact",
]

_BENEFIT_ORIGINS = tuple(origin.value for origin in ClaimOrigin)
_BIENNIAL_END_YEARS = (2016, 2018, 2020, 2022)
_INCLUSION_COUNT_KEYS = (
    "excluded_di_conversion",
    "excluded_di_unknown",
    "nonclaimant",
    "excluded_domain_incomplete",
    "excluded_pre1979_eligibility",
    "excluded_empty_span",
    "excluded_chronology_inconsistent",
    "excluded_low_coverage",
    "included",
    *(path.value for path in NonClaimantPath),
    *(f"origin_{origin.value}" for origin in ClaimOrigin),
)
_BIRTH_SOURCE_KEYS = tuple(source.value for source in BirthSource)
_SNAP_KEYS = ("lower_endpoint", "upper_endpoint")
_HEX_DIGITS = frozenset("0123456789abcdef")

CONTEXT_RATIO_DISCLOSURE = {
    "status": "deferred_to_anchor_extraction",
}


@dataclass(frozen=True)
class FirstReportDrawBundle:
    """All pure report products belonging to one registered draw."""

    draw_index: int
    inclusion: InclusionResult
    benefits: BenefitLedger
    revenue: RevenueLedger


def _draw_index(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError("draw_index must be an integer")
    return int(value)


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{label} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def _require_exact_keys(
    observed: Sequence[str],
    expected: Sequence[str],
    label: str,
) -> None:
    if len(observed) != len(set(observed)):
        raise ValueError(f"{label} contains duplicate keys")
    if set(observed) != set(expected):
        raise ValueError(
            f"{label} keys {sorted(observed)} != expected "
            f"{sorted(expected)}"
        )


def _validate_inclusion(result: InclusionResult) -> None:
    _require_exact_keys(
        [row.key for row in result.counts],
        _INCLUSION_COUNT_KEYS,
        "inclusion counts",
    )
    _require_exact_keys(
        [row.key for row in result.birth_source_counts],
        _BIRTH_SOURCE_KEYS,
        "birth-source counts",
    )
    _require_exact_keys(
        [row.key for row in result.opening_stock_snap_counts],
        _SNAP_KEYS,
        "opening-stock endpoint counts",
    )
    _require_exact_keys(
        [row.key for row in result.opening_stock_snap_weighted_shares],
        _SNAP_KEYS,
        "opening-stock endpoint shares",
    )
    if result.opening_stock_snap_denominator.key != (
        "included_opening_backfill"
    ):
        raise ValueError("opening-stock snap denominator key changed")
    if result.entrant_diagnostic.count.key != (
        "explicit_2016_2018_row_entrant"
    ):
        raise ValueError("explicit-row entrant count key changed")
    if result.entrant_diagnostic.source_income_years != (2016, 2018):
        raise ValueError("explicit-row entrant source years changed")
    if (
        result.entrant_diagnostic.operative_exclusion_rule
        or not result.entrant_diagnostic.may_overlap_inclusion_classes
    ):
        raise ValueError("explicit-row entrant disclosure changed")

    counts = {row.key: row for row in result.counts}
    stage_keys = _INCLUSION_COUNT_KEYS[:9]
    if sum(counts[key].unweighted for key in stage_keys) != len(
        result.di_partition
    ):
        raise ValueError("inclusion stages do not reconcile to the population")
    if counts["included"].unweighted != len(result.included):
        raise ValueError("included count does not match included records")
    if sum(
        counts[f"origin_{origin}"].unweighted for origin in _BENEFIT_ORIGINS
    ) != len(result.origins):
        raise ValueError("origin counts do not match candidate records")


def _validate_benefit_grid(ledger: BenefitLedger) -> None:
    annual = [(row.claim_origin, row.year) for row in ledger.annual_rows]
    expected_annual = [
        (origin, year) for origin in _BENEFIT_ORIGINS for year in REPORT_YEARS
    ]
    if len(annual) != len(set(annual)) or set(annual) != set(expected_annual):
        raise ValueError("benefit annual row grid is incomplete")
    biennial = [
        (row.claim_origin, row.end_year, tuple(row.component_years))
        for row in ledger.biennial_rows
    ]
    expected_biennial = [
        (origin, end_year, (end_year - 1, end_year))
        for origin in _BENEFIT_ORIGINS
        for end_year in _BIENNIAL_END_YEARS
    ]
    if len(biennial) != len(set(biennial)) or set(biennial) != set(
        expected_biennial
    ):
        raise ValueError("benefit biennial row grid is incomplete")
    if tuple(ledger.evidence_labels) != EVIDENCE_LABELS:
        raise ValueError("benefit evidence labels changed")
    if ledger.measure_label != BENEFIT_MEASURE_LABEL:
        raise ValueError("benefit measure label changed")
    if ledger.diagnostics.get("post_claim_recomputation_count") != 0:
        raise ValueError("post-claim benefit recomputation is forbidden")
    if any(row.post_claim_recomputation_count != 0 for row in ledger.people):
        raise ValueError("a benefit person ledger records recomputation")


def _validate_revenue_grid(ledger: RevenueLedger) -> None:
    annual = [row.year for row in ledger.annual_rows]
    if len(annual) != len(set(annual)) or set(annual) != set(REPORT_YEARS):
        raise ValueError("revenue annual row grid is incomplete")
    biennial = [
        (row.end_year, tuple(row.component_years))
        for row in ledger.biennial_rows
    ]
    expected = [
        (end_year, (end_year - 1, end_year))
        for end_year in _BIENNIAL_END_YEARS
    ]
    if len(biennial) != len(set(biennial)) or set(biennial) != set(expected):
        raise ValueError("revenue biennial row grid is incomplete")
    if tuple(ledger.evidence_labels) != EVIDENCE_LABELS:
        raise ValueError("revenue evidence labels changed")
    if ledger.earnings_measure_label != "labor-income proxy":
        raise ValueError("revenue earnings label changed")
    if ledger.dollar_basis != "nominal":
        raise ValueError("revenue dollar basis changed")
    if ledger.population_basis != "unsplit projection.slices":
        raise ValueError("revenue population basis changed")


def _validate_draw_bundle(bundle: FirstReportDrawBundle) -> None:
    draw = _draw_index(bundle.draw_index)
    if draw != bundle.benefits.draw_index or draw != bundle.revenue.draw_index:
        raise ValueError("draw bundle and ledger draw indices differ")
    _validate_inclusion(bundle.inclusion)
    _validate_benefit_grid(bundle.benefits)
    _validate_revenue_grid(bundle.revenue)

    included = {
        row.person_id: row.claim_origin for row in bundle.inclusion.included
    }
    if len(included) != len(bundle.inclusion.included):
        raise ValueError("included claimant records contain duplicate people")
    benefit_people = {
        row.person_id: row.claim_origin for row in bundle.benefits.people
    }
    if len(benefit_people) != len(bundle.benefits.people):
        raise ValueError("benefit person ledgers contain duplicate people")
    if benefit_people != included:
        raise ValueError(
            "benefit people and Stage-D included claimant origins differ"
        )


def _ordered_draws(
    bundles: Sequence[FirstReportDrawBundle],
    configuration_echo: Mapping[str, Any],
) -> tuple[FirstReportDrawBundle, ...]:
    projection = configuration_echo.get("projection")
    if not isinstance(projection, Mapping) or projection.get(
        "draw_indices"
    ) != list(DRAW_INDICES):
        raise ValueError(
            f"configuration must register exact draw indices "
            f"{DRAW_INDICES}"
        )
    rows = tuple(bundles)
    observed = tuple(sorted(_draw_index(row.draw_index) for row in rows))
    if observed != DRAW_INDICES:
        raise ValueError(
            f"artifact assembly requires draw indices {DRAW_INDICES}; "
            f"received {observed}"
        )
    ordered = tuple(sorted(rows, key=lambda row: row.draw_index))
    for row in ordered:
        _validate_draw_bundle(row)
    return ordered


def _row_dict(row: Any, *, draw_index: int) -> dict[str, Any]:
    return {"draw_index": draw_index, **asdict(row)}


def _per_draw_rows(
    bundles: Sequence[FirstReportDrawBundle],
    *,
    ledger_attribute: str,
    row_attribute: str,
    claim_origin: str | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for bundle in bundles:
        ledger = getattr(bundle, ledger_attribute)
        for row in getattr(ledger, row_attribute):
            if claim_origin is None or row.claim_origin == claim_origin:
                rows.append(_row_dict(row, draw_index=bundle.draw_index))
    return rows


def _flatten_aggregate_rows(
    rows: Sequence[AcrossDrawTableRow],
    *,
    claim_origin: str | None = None,
) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for row in rows:
        dimensions = dict(row.dimensions)
        if (
            claim_origin is not None
            and dimensions.get("claim_origin") != claim_origin
        ):
            continue
        for metric_name, metric in sorted(row.metrics.items()):
            flattened.append(
                {
                    **dimensions,
                    "metric": metric_name,
                    "n_draws": metric.n_draws,
                    "n_observations": metric.n_observations,
                    "mean": metric.mean,
                    "sample_sd": metric.sample_sd,
                }
            )
    return flattened


def _biennial_companion(
    bundles: Sequence[FirstReportDrawBundle],
    aggregate: AcrossDrawLedgers,
    *,
    ledger_attribute: str,
    claim_origin: str | None = None,
) -> list[dict[str, Any]]:
    per_draw = _per_draw_rows(
        bundles,
        ledger_attribute=ledger_attribute,
        row_attribute="biennial_rows",
        claim_origin=claim_origin,
    )
    across_draw = _flatten_aggregate_rows(
        aggregate.biennial_rows,
        claim_origin=claim_origin,
    )
    return [
        *({"row_basis": "per_draw", **row} for row in per_draw),
        *({"row_basis": "across_draw", **row} for row in across_draw),
    ]


def _table(
    bundles: Sequence[FirstReportDrawBundle],
    aggregate: AcrossDrawLedgers,
    *,
    ledger_attribute: str,
    claim_origin: str | None,
    unit_label: str,
) -> dict[str, Any]:
    return table_record(
        per_draw=_per_draw_rows(
            bundles,
            ledger_attribute=ledger_attribute,
            row_attribute="annual_rows",
            claim_origin=claim_origin,
        ),
        aggregate=_flatten_aggregate_rows(
            aggregate.annual_rows,
            claim_origin=claim_origin,
        ),
        unit_label=unit_label,
        annual=True,
        biennial_companion=_biennial_companion(
            bundles,
            aggregate,
            ledger_attribute=ledger_attribute,
            claim_origin=claim_origin,
        ),
    )


def _count_values(result: InclusionResult) -> dict[str, float | int]:
    values: dict[str, float | int] = {}
    for category, records in (
        ("inclusion", result.counts),
        ("birth_source", result.birth_source_counts),
        ("opening_stock_snap", result.opening_stock_snap_counts),
    ):
        for record in records:
            values[f"{category}__{record.key}__unweighted"] = record.unweighted
            values[f"{category}__{record.key}__weighted"] = record.weighted
    denominator = result.opening_stock_snap_denominator
    values["opening_stock_snap__included_opening_backfill__unweighted"] = (
        denominator.unweighted
    )
    values["opening_stock_snap__included_opening_backfill__weighted"] = (
        denominator.weighted
    )
    for share in result.opening_stock_snap_weighted_shares:
        prefix = f"opening_stock_snap__{share.key}"
        values[f"{prefix}__numerator_weight"] = share.numerator_weight
        values[f"{prefix}__denominator_weight"] = share.denominator_weight
        values[f"{prefix}__weighted_share"] = share.share
    entrant = result.entrant_diagnostic.count
    values[f"entrant__{entrant.key}__unweighted"] = entrant.unweighted
    values[f"entrant__{entrant.key}__weighted"] = entrant.weighted
    for origin in _BENEFIT_ORIGINS:
        people = [row for row in result.included if row.claim_origin == origin]
        values[f"included_origin__{origin}__unweighted"] = len(people)
        values[f"included_origin__{origin}__weighted"] = math.fsum(
            row.weight for row in people
        )
    return values


def _weighted_mean(
    values: Sequence[tuple[float, float]],
) -> float:
    denominator = math.fsum(weight for _, weight in values)
    if denominator == 0:
        return 0.0
    return math.fsum(value * weight for value, weight in values) / denominator


def _diagnostic_values(
    bundle: FirstReportDrawBundle,
) -> dict[str, float | int]:
    values: dict[str, float | int] = {
        f"benefit__{key}": value
        for key, value in bundle.benefits.diagnostics.items()
    }
    values.update(
        {
            f"revenue__{key}": value
            for key, value in bundle.revenue.diagnostics.items()
        }
    )
    included = bundle.inclusion.included
    values["career__top35_reaches_pre_1968__unweighted"] = sum(
        row.career.top35_reaches_pre_1968 for row in included
    )
    values["career__top35_reaches_pre_1968__weighted"] = math.fsum(
        row.weight for row in included if row.career.top35_reaches_pre_1968
    )
    values["career__coverage_ratio_mean_unweighted"] = (
        math.fsum(row.career.coverage_ratio for row in included)
        / len(included)
        if included
        else 0.0
    )
    values["career__coverage_ratio_mean_weighted"] = _weighted_mean(
        [(row.career.coverage_ratio, row.weight) for row in included]
    )
    values["career__imputed_year_share_mean_unweighted"] = (
        math.fsum(row.career.imputed_year_share for row in included)
        / len(included)
        if included
        else 0.0
    )
    values["career__imputed_year_share_mean_weighted"] = _weighted_mean(
        [(row.career.imputed_year_share, row.weight) for row in included]
    )
    values["career__birth_year_inferred__unweighted"] = sum(
        row.birth_source is BirthSource.INFERRED_PERIOD_AGE for row in included
    )
    values["career__birth_year_inferred__weighted"] = math.fsum(
        row.weight
        for row in included
        if row.birth_source is BirthSource.INFERRED_PERIOD_AGE
    )
    return values


def _wide_rows(
    bundles: Sequence[FirstReportDrawBundle],
    extractor: Any,
) -> list[dict[str, Any]]:
    return [
        {"draw_index": bundle.draw_index, **extractor(bundle)}
        for bundle in bundles
    ]


def _numeric_aggregate(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if not rows:
        raise ValueError("cannot aggregate an empty draw collection")
    keys = set(rows[0]) - {"draw_index"}
    if any(set(row) - {"draw_index"} != keys for row in rows[1:]):
        raise ValueError("wide diagnostic/count columns differ across draws")
    aggregates: list[dict[str, Any]] = []
    for key in sorted(keys):
        values = [
            _finite_number(row[key], f"{key} for draw {row['draw_index']}")
            for row in rows
        ]
        mean = math.fsum(values) / len(values)
        sample_sd = math.sqrt(
            math.fsum((value - mean) ** 2 for value in values)
            / (len(values) - 1)
        )
        aggregates.append(
            {
                "metric": key,
                "n_draws": len(values),
                "n_observations": len(values),
                "mean": mean,
                "sample_sd": sample_sd,
            }
        )
    return aggregates


def _career_diagnostic_rows(
    bundles: Sequence[FirstReportDrawBundle],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for bundle in bundles:
        benefit_by_person = {
            row.person_id: row for row in bundle.benefits.people
        }
        for claimant in sorted(
            bundle.inclusion.included,
            key=lambda row: row.person_id,
        ):
            benefit = benefit_by_person[claimant.person_id]
            rows.append(
                {
                    "draw_index": bundle.draw_index,
                    "person_id": claimant.person_id,
                    "claim_origin": claimant.claim_origin,
                    "birth_source": claimant.birth_source.value,
                    "birth_year_inferred": (
                        claimant.birth_source
                        is BirthSource.INFERRED_PERIOD_AGE
                    ),
                    "coverage_ratio": claimant.career.coverage_ratio,
                    "imputed_year_share": claimant.career.imputed_year_share,
                    "affected_odd_year_share": (
                        claimant.career.affected_odd_year_share
                    ),
                    "provenance_counts": (claimant.career.provenance_counts),
                    "coverage_provenance_counts": (
                        claimant.career.coverage_provenance_counts
                    ),
                    "top35_reaches_pre_1968": (
                        claimant.career.top35_reaches_pre_1968
                    ),
                    "pre_1968_top35_zero_year_count": len(
                        claimant.career.pre_1968_top35_zero_years
                    ),
                    "positive_post_claim_earnings": (
                        benefit.positive_post_claim_earnings
                    ),
                    "award_formula_computation_count": (
                        benefit.award_formula_computation_count
                    ),
                    "post_claim_recomputation_count": (
                        benefit.post_claim_recomputation_count
                    ),
                }
            )
    return rows


def _validate_sha256(value: Any) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX_DIGITS for character in value)
    ):
        raise ValueError("environment_sidecar_sha256 must be lowercase sha256")
    return value


def build_first_estimates_artifact(
    bundles: Sequence[FirstReportDrawBundle],
    *,
    configuration_echo: Mapping[str, Any],
    environment_sidecar_sha256: str,
    prior_incidents: Sequence[str] = (),
) -> dict[str, Any]:
    """Assemble and validate the immutable post-compute report object."""

    if not isinstance(configuration_echo, Mapping):
        raise TypeError("configuration_echo must be a mapping")
    registration_reference = configuration_echo.get("registration_reference")
    if (
        not isinstance(registration_reference, str)
        or not registration_reference
    ):
        raise ValueError("configuration has no registration reference")
    parameters = configuration_echo.get("parameters")
    if not isinstance(parameters, Mapping):
        raise ValueError("configuration has no parameter provenance")

    draws = _ordered_draws(bundles, configuration_echo)
    benefit_aggregate = aggregate_benefit_draws(
        [row.benefits for row in draws]
    )
    revenue_aggregate = aggregate_revenue_draws([row.revenue for row in draws])

    count_rows = _wide_rows(draws, lambda row: _count_values(row.inclusion))
    diagnostic_rows = _wide_rows(draws, _diagnostic_values)
    artifact = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "identity": {
            "report_id": "first_estimates",
            "report_class": "registered estimates report",
            "registration_reference": registration_reference,
        },
        "configuration_echo": copy.deepcopy(dict(configuration_echo)),
        "integrity": {
            "environment_sidecar": {
                "path": "first_estimates_v1.json.env.json",
                "sha256": _validate_sha256(environment_sidecar_sha256),
            }
        },
        "parameters": copy.deepcopy(dict(parameters)),
        "execution": {
            "canonical_rule": copy.deepcopy(CANONICAL_EXECUTION_RULE),
            "completed_draw_indices": list(DRAW_INDICES),
            "assembly": "pure_post_compute",
        },
        "tables": {
            "modeled_award_flow": _table(
                draws,
                benefit_aggregate,
                ledger_attribute="benefits",
                claim_origin=ClaimOrigin.MODELED_AWARD.value,
                unit_label=BENEFIT_MEASURE_LABEL,
            ),
            "opening_stock": _table(
                draws,
                benefit_aggregate,
                ledger_attribute="benefits",
                claim_origin=ClaimOrigin.OPENING_BACKFILL.value,
                unit_label=(
                    "report-only imputed opening stock; "
                    f"{BENEFIT_MEASURE_LABEL}"
                ),
            ),
            "revenue": _table(
                draws,
                revenue_aggregate,
                ledger_attribute="revenue",
                claim_origin=None,
                unit_label=(
                    "nominal frame-relative OASDI payroll contributions on "
                    "the labor-income proxy"
                ),
            ),
        },
        "counts": {
            "per_draw": count_rows,
            "aggregate": _numeric_aggregate(count_rows),
            "entrant_diagnostic": {
                "source_income_years": [2016, 2018],
                "may_overlap_inclusion_classes": True,
                "operative_exclusion_rule": False,
            },
        },
        "diagnostics": {
            "per_draw": diagnostic_rows,
            "aggregate": _numeric_aggregate(diagnostic_rows),
            "included_career_per_draw": _career_diagnostic_rows(draws),
            "context_ratio": copy.deepcopy(CONTEXT_RATIO_DISCLOSURE),
            "payment_year_convention": (
                "Twelve annualized monthly payments only in realized "
                "presence years; partial first and last years are not "
                "modeled."
            ),
            "benefit_measure": BENEFIT_MEASURE_LABEL,
            "revenue_population_basis": "unsplit projection.slices",
        },
        "prior_incidents": list(prior_incidents),
        "gap_block": [dict(row) for row in GAP_BLOCK],
        "certifies_nothing": list(CERTIFIES_NOTHING),
    }
    validate_first_estimates_artifact(
        artifact,
        expected_configuration_echo=configuration_echo,
        expected_prior_incidents=prior_incidents,
    )
    return artifact
