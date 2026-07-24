"""Publication contracts for the registered first-estimates report.

This module only builds, validates, and exclusively writes records.  It never
starts a projection.  The primary report is integrity-bound to the exact
``.env.json`` bytes supplied to :func:`populace_dynamics.artifacts.write_new`;
incident records use the frozen nine-key ``first_estimates_incident.v1``
schema from design revision 9.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from datetime import datetime, timezone
from numbers import Integral, Real
from pathlib import Path
from typing import Any

from populace_dynamics import artifacts
from populace_dynamics.contract import ContractRef, environment_block

ARTIFACT_SCHEMA_VERSION = "first_estimates.v1"
INCIDENT_SCHEMA_VERSION = "first_estimates_incident.v1"
DEFAULT_ARTIFACT_PATH = Path("runs/first_estimates_v1.json")
INCIDENT_PHASES = frozenset(
    {"preparation", "invariant", "compute", "publication"}
)
EVIDENCE_LABELS = (
    "frame-relative",
    "pre-alignment",
    "labor-income proxy",
)
ODD_YEAR_CARRY_DISCLOSURE = (
    "The engine draws even-year earnings and carries the prior even-year "
    "value into odd years (2015 repeats 2014, 2017 repeats 2016, and so on)."
)
CANONICAL_EXECUTION_RULE = {
    "registered_runs": 1,
    "publishes_regardless": True,
    "no_self_rescue": True,
    "retry": (
        "At most one coordinator-adjudicated, report-first retry solely for "
        "an external pre-output failure yielding no estimate-bearing "
        "information."
    ),
    "fresh_registration_required_if": (
        "A published v1, any changed configuration byte, or a second failure "
        "of any kind."
    ),
}
CERTIFIES_NOTHING = (
    "This report does not certify forward production.",
    "This report does not estimate national dollars.",
    "This report does not claim that PSID labor income is OASDI-covered "
    "earnings.",
    "This report does not claim administrative benefit-payment dollars.",
    "This report creates no gate, floor, threshold, or verdict.",
)

# The design freezes the gap block.  Keep it data, rather than prose assembled
# by a runner, so the artifact validator can reject omissions or paraphrase
# drift before publication.
GAP_BLOCK: tuple[dict[str, str], ...] = (
    {
        "disclosure": "Scheduled realized 2017/2019 openers condition the object",
        "classification": (
            "material — the reproduction panel is anchored, not forward"
        ),
    },
    {
        "disclosure": "Widowhood limitations",
        "classification": ("material — survivor composition affects presence"),
    },
    {
        "disclosure": (
            'Open additions — certified sentence quoted exactly: "The gate '
            "covers the closed panel only; "
            "synthetic births, immigrant cohorts, and other open additions "
            'remain report-only."'
        ),
        "classification": "material",
    },
    {
        "disclosure": "Lag-5 persistence unscored",
        "classification": "material context for earnings paths",
    },
    {
        "disclosure": "Stock margins unscored",
        "classification": "material context",
    },
    {
        "disclosure": "65+ remarriage tail limitation",
        "classification": (
            "material context — presence of older married persons"
        ),
    },
    {
        "disclosure": (
            "Earnings survivorship — certified sentence quoted exactly: "
            '"Gated earnings use realized support and do not certify '
            "mortality's effect on the earnings composition through "
            'survivorship."'
        ),
        "classification": "material",
    },
    {
        "disclosure": "Full-window model selection",
        "classification": "material context",
    },
    {
        "disclosure": "Redrawn-seed comparison unavailable",
        "classification": "material context",
    },
    {
        "disclosure": (
            "The artifact's earnings-certification string quoted exactly: "
            '"M6-first-certified forward earnings law; no gate_1 backward-law '
            'certificate transfers"'
        ),
        "classification": "restated verbatim",
    },
    {
        "disclosure": (
            "F4 — partial overlay: _merge_period_columns drops named columns "
            "before left-merging, so unmatched live state becomes NaN "
            "(pinned: carried di_converted=True read as no-conversion)"
        ),
        "classification": (
            "material — directly motivates the DI precedence law and the "
            "di_unknown class"
        ),
    },
    {
        "disclosure": (
            "F5 — exact-anchor household seed gap (minors reaching 15 later "
            "and source-gap adults never enter the household domain)"
        ),
        "classification": (
            "inapplicable to presence (certified: household fields feed no "
            "locked cell and are not serialized; roster presence is "
            "unaffected) — material only if household-domain counts are "
            "quoted, and then the certified excluded/domain counts publish "
            "first"
        ),
    },
    {
        "disclosure": (
            'F6 — closed "85+" band (nominal 85+ ends at 120; uncovered ages '
            "get p=0)"
        ),
        "classification": (
            "material context — oldest-old presence in benefit-years"
        ),
    },
    {
        "disclosure": (
            "F8 — entrant classification (anchor_wave > 2015 & ~domain "
            "treated as row existence)"
        ),
        "classification": (
            "material — the reason §3.3/§10 re-derive the entrant count from "
            "explicit earnings rows"
        ),
    },
    {
        "disclosure": (
            "F9 — candidate-9/live-roster reconciliation (household fields do "
            "not reconcile mortality-thinned members or newborns)"
        ),
        "classification": (
            "inapplicable — household composition fields are not consumed"
        ),
    },
    {
        "disclosure": (
            "F9 sub-item — coresident_spouse carried for a person whose "
            "spouse was removed by simulated mortality"
        ),
        "classification": (
            "inapplicable here (household column unconsumed), listed by name "
            "as the certified record requires"
        ),
    },
    {
        "disclosure": (
            "F10 — entrant schema NAs (synthetic_entry=NA inheritance; "
            "certified surface: future panel/schema consumers)"
        ),
        "classification": (
            "this report is such a consumer — it identifies synthetic persons "
            "by ID-set difference per the certified mechanism and never reads "
            "this field; classified handled-by-construction, listed"
        ),
    },
    {
        "disclosure": (
            "F11 — fertility-domain coverage (births draw over "
            "state.marital_ids only; certified surface: family-B birth "
            "counts, no gated cell)"
        ),
        "classification": (
            "inapplicable to benefit tables (no in-window newborn claims); "
            "for revenue person-years the certified fertility-domain "
            "denominator disclosure is restated, not extended"
        ),
    },
    {
        "disclosure": (
            "Certified `forward_projection_2100_extrapolation` limitation"
        ),
        "classification": (
            "material — restated: nothing here extends past 2022, and nothing "
            "certifies any longer horizon"
        ),
    },
    {
        "disclosure": "Mortality drift uncertified",
        "classification": "material",
    },
    {
        "disclosure": "Families B/C ungated",
        "classification": "material",
    },
    {
        "disclosure": "2020-2022 shock window report-only",
        "classification": "material — in-window years",
    },
    {
        "disclosure": "Mechanical claiming, 1998-2013 table",
        "classification": "material",
    },
    {
        "disclosure": "M4 is not DI adjudication",
        "classification": "material — DI is out of scope",
    },
    {
        "disclosure": "Alignment `not_computed`; scored path unaligned",
        "classification": "material",
    },
    {
        "disclosure": "Domain and coverage exclusions (§3.3)",
        "classification": "material; counts published",
    },
    {
        "disclosure": "Odd-year earnings carry law (§3.2)",
        "classification": "material — annual tables",
    },
    {
        "disclosure": "Spouse/survivor benefits out of scope",
        "classification": "material",
    },
    {
        "disclosure": (
            "Levels unanchored — no committed annual SSA level series"
        ),
        "classification": (
            "material; the registered anchor extraction is the successor step"
        ),
    },
)

_ARTIFACT_KEYS = frozenset(
    {
        "schema_version",
        "identity",
        "configuration_echo",
        "integrity",
        "parameters",
        "execution",
        "tables",
        "counts",
        "diagnostics",
        "gap_block",
        "certifies_nothing",
    }
)
_INCIDENT_KEYS = frozenset(
    {
        "schema_version",
        "incident_index",
        "timestamp_utc",
        "phase",
        "reason",
        "reason_detail",
        "registration_reference",
        "configuration_echo",
        "artifact_path",
    }
)
_INCIDENT_FILENAME = re.compile(r"first_estimates_incident_(\d+)\.json")
_UTC_TIMESTAMP = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}" r"(?:\.\d{1,6})?Z"
)
_REGISTERED_DRAW_INDICES = tuple(range(20))
_REPORT_YEARS = tuple(range(2015, 2023))
_BIENNIAL_END_YEARS = (2016, 2018, 2020, 2022)
_BENEFIT_ORIGINS = ("modeled_award", "opening_backfill")
_TABLE_NAMES = frozenset({"modeled_award_flow", "opening_stock", "revenue"})
_TABLE_KEYS = frozenset(
    {
        "labels",
        "unit_label",
        "annual",
        "per_draw",
        "aggregate",
        "odd_year_carry_disclosure",
        "biennial_companion",
    }
)
_BENEFIT_METRICS = (
    "unweighted_award_count",
    "weighted_award_count",
    "average_monthly_benefit_at_award",
    "unweighted_beneficiary_count",
    "weighted_beneficiary_count",
    "frame_annualized_benefit",
)
_REVENUE_METRICS = (
    "unweighted_person_year_count",
    "weighted_person_year_count",
    "unweighted_covered_earner_count",
    "weighted_covered_earner_count",
    "weighted_taxable_payroll",
    "employee_contributions",
    "employer_contributions",
    "combined_contributions",
)
_BENEFIT_MEASURE_LABEL = (
    "annualized statutory benefit, eligibility-PIA with COLA, "
    "no recomputation"
)
_TABLE_UNIT_LABELS = {
    "modeled_award_flow": _BENEFIT_MEASURE_LABEL,
    "opening_stock": (
        "report-only imputed opening stock; " f"{_BENEFIT_MEASURE_LABEL}"
    ),
    "revenue": (
        "nominal frame-relative OASDI payroll contributions on "
        "the labor-income proxy"
    ),
}
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
    "drawn_never_claimed",
    "never_drawn",
    "origin_modeled_award",
    "origin_opening_backfill",
)
_BIRTH_SOURCE_KEYS = (
    "exact_marriage",
    "inferred_period_age",
    "synthetic_native",
)
_COUNT_METRICS = frozenset(
    [
        *(
            f"inclusion__{key}__{measure}"
            for key in _INCLUSION_COUNT_KEYS
            for measure in ("unweighted", "weighted")
        ),
        *(
            f"birth_source__{key}__{measure}"
            for key in _BIRTH_SOURCE_KEYS
            for measure in ("unweighted", "weighted")
        ),
        *(
            f"opening_stock_snap__{key}__{measure}"
            for key in ("lower_endpoint", "upper_endpoint")
            for measure in ("unweighted", "weighted")
        ),
        *(
            "opening_stock_snap__included_opening_backfill__" f"{measure}"
            for measure in ("unweighted", "weighted")
        ),
        *(
            f"opening_stock_snap__{key}__{measure}"
            for key in ("lower_endpoint", "upper_endpoint")
            for measure in (
                "numerator_weight",
                "denominator_weight",
                "weighted_share",
            )
        ),
        *(
            "entrant__explicit_2016_2018_row_entrant__" f"{measure}"
            for measure in ("unweighted", "weighted")
        ),
        *(
            f"included_origin__{origin}__{measure}"
            for origin in _BENEFIT_ORIGINS
            for measure in ("unweighted", "weighted")
        ),
    ]
)
_COUNTS_KEYS = frozenset({"per_draw", "aggregate", "entrant_diagnostic"})
_DIAGNOSTICS_KEYS = frozenset(
    {
        "per_draw",
        "aggregate",
        "included_career_per_draw",
        "context_ratio",
        "payment_year_convention",
        "benefit_measure",
        "revenue_population_basis",
    }
)
_ENTRANT_DISCLOSURE = {
    "source_income_years": [2016, 2018],
    "may_overlap_inclusion_classes": True,
    "operative_exclusion_rule": False,
}
_CONTEXT_RATIO_DISCLOSURE = {
    "status": "not_computed",
    "report_only": True,
    "anchor": False,
    "reason": (
        "No committed, hash-pinned annual SSA average-monthly-benefit-at-"
        "award series is registered, so no simulated-to-published ratio is "
        "computed."
    ),
    "design_question": (
        "Which exact SSA annual award statistic, source table, vintage, and "
        "calendar-year convention should a successor registration pin?"
    ),
}
_PAYMENT_YEAR_CONVENTION = (
    "Twelve annualized monthly payments only in realized presence years; "
    "partial first and last years are not modeled."
)
_CAREER_DIAGNOSTIC_KEYS = frozenset(
    {
        "draw_index",
        "person_id",
        "claim_origin",
        "birth_source",
        "birth_year_inferred",
        "coverage_ratio",
        "imputed_year_share",
        "affected_odd_year_share",
        "provenance_counts",
        "coverage_provenance_counts",
        "top35_reaches_pre_1968",
        "pre_1968_top35_zero_year_count",
        "positive_post_claim_earnings",
        "award_formula_computation_count",
        "post_claim_recomputation_count",
    }
)
_CAREER_PROVENANCE_KEYS = frozenset(
    {"observed", "gap_imputed", "boundary_2014", "projected", "unknown"}
)


def canonical_json_bytes(value: Any) -> bytes:
    """Return the report's canonical hash representation."""
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def prepare_environment_sidecar(
    root: str | Path | None = None,
) -> tuple[bytes, str]:
    """Freeze exact sidecar bytes before any projection compute begins."""
    record = {
        "environment": environment_block(),
        "contract": asdict(ContractRef.current(root)),
    }
    payload = canonical_json_bytes(record)
    return payload, hashlib.sha256(payload).hexdigest()


def _require_exact_keys(
    value: Mapping[str, Any], expected: frozenset[str], label: str
) -> None:
    observed = frozenset(value)
    if observed != expected:
        raise ValueError(
            f"{label} keys {sorted(observed)} != expected {sorted(expected)}"
        )


def _require_json_finite(value: Any, path: str = "$") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{path} contains a non-finite number")
    if isinstance(value, Mapping):
        for key, child in value.items():
            _require_json_finite(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _require_json_finite(child, f"{path}[{index}]")


def _rows(
    value: Any,
    label: str,
    *,
    allow_empty: bool = False,
) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        raise TypeError(f"{label} must be a list")
    if (not value and not allow_empty) or not all(
        isinstance(row, Mapping) for row in value
    ):
        raise ValueError(f"{label} rows must be nonempty mappings")
    return value


def _integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{label} must be an integer")
    return int(value)


def _number(
    value: Any,
    label: str,
    *,
    allow_none: bool = False,
) -> float | None:
    if value is None and allow_none:
        return None
    if isinstance(value, bool) or not isinstance(value, Real):
        suffix = " or null" if allow_none else ""
        raise TypeError(f"{label} must be numeric{suffix}")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _component_years(
    value: Any, *, end_year: int, label: str
) -> tuple[int, int]:
    if (
        isinstance(value, (str, bytes))
        or not isinstance(value, Sequence)
        or len(value) != 2
    ):
        raise ValueError(f"{label} component_years must be a two-year pair")
    years = (
        _integer(value[0], f"{label} first component year"),
        _integer(value[1], f"{label} second component year"),
    )
    if years != (end_year - 1, end_year):
        raise ValueError(f"{label} component_years do not match end_year")
    return years


def _expected_summary(
    values: Sequence[float | None],
) -> tuple[int, int, float | None, float | None]:
    observed = [value for value in values if value is not None]
    if not observed:
        return len(values), 0, None, None
    mean = math.fsum(observed) / len(observed)
    sample_sd = None
    if len(observed) >= 2:
        sample_sd = math.sqrt(
            math.fsum((value - mean) ** 2 for value in observed)
            / (len(observed) - 1)
        )
    return len(values), len(observed), mean, sample_sd


def _require_summary(
    row: Mapping[str, Any],
    values: Sequence[float | None],
    *,
    label: str,
) -> None:
    expected_n_draws, expected_n_observations, expected_mean, expected_sd = (
        _expected_summary(values)
    )
    n_draws = _integer(row.get("n_draws"), f"{label} n_draws")
    n_observations = _integer(
        row.get("n_observations"),
        f"{label} n_observations",
    )
    if n_draws != expected_n_draws:
        raise ValueError(f"{label} n_draws does not match per-draw rows")
    if n_observations != expected_n_observations:
        raise ValueError(
            f"{label} n_observations does not match non-null per-draw values"
        )
    mean = _number(row.get("mean"), f"{label} mean", allow_none=True)
    sample_sd = _number(
        row.get("sample_sd"),
        f"{label} sample_sd",
        allow_none=True,
    )
    if mean != expected_mean:
        raise ValueError(f"{label} mean does not match per-draw values")
    if sample_sd != expected_sd:
        raise ValueError(f"{label} sample_sd does not match per-draw values")


def _validate_aggregate_rows(
    *,
    rows: Sequence[Mapping[str, Any]],
    values_by_dimension: Mapping[
        tuple[Any, ...], Mapping[int, Mapping[str, float | None]]
    ],
    dimension_names: tuple[str, ...],
    metrics: tuple[str, ...],
    expected_draw_indices: tuple[int, ...],
    label: str,
    row_basis: bool = False,
) -> None:
    expected_keys = frozenset(
        {
            *dimension_names,
            "metric",
            "n_draws",
            "n_observations",
            "mean",
            "sample_sd",
            *(("row_basis",) if row_basis else ()),
        }
    )
    indexed: dict[tuple[tuple[Any, ...], str], Mapping[str, Any]] = {}
    for index, row in enumerate(rows):
        _require_exact_keys(row, expected_keys, f"{label} row {index}")
        if row_basis and row["row_basis"] != "across_draw":
            raise ValueError(f"{label} row_basis must be across_draw")
        dimensions: list[Any] = []
        for name in dimension_names:
            value = row[name]
            if name in {"year", "end_year"}:
                value = _integer(value, f"{label} {name}")
            elif name == "component_years":
                end_year = _integer(row["end_year"], f"{label} end_year")
                value = _component_years(
                    value,
                    end_year=end_year,
                    label=label,
                )
            elif not isinstance(value, str):
                raise TypeError(f"{label} {name} must be a string")
            dimensions.append(value)
        metric = row["metric"]
        if metric not in metrics:
            raise ValueError(f"{label} has unknown metric {metric!r}")
        key = (tuple(dimensions), metric)
        if key in indexed:
            raise ValueError(f"{label} contains duplicate aggregate grids")
        indexed[key] = row

    expected = {
        (dimensions, metric)
        for dimensions in values_by_dimension
        for metric in metrics
    }
    if set(indexed) != expected:
        raise ValueError(f"{label} aggregate grid is incomplete")
    for (dimensions, metric), row in indexed.items():
        by_draw = values_by_dimension[dimensions]
        values = [by_draw[draw][metric] for draw in expected_draw_indices]
        _require_summary(
            row,
            values,
            label=f"{label} {dimensions!r} {metric}",
        )


def _table_spec(
    name: str,
) -> tuple[str | None, tuple[str, ...], tuple[str, ...]]:
    if name == "modeled_award_flow":
        return "modeled_award", ("claim_origin", "year"), _BENEFIT_METRICS
    if name == "opening_stock":
        return "opening_backfill", ("claim_origin", "year"), _BENEFIT_METRICS
    if name == "revenue":
        return None, ("year",), _REVENUE_METRICS
    raise ValueError(f"unknown first-estimates table {name!r}")


def _validate_table(
    name: str,
    table: Any,
    *,
    expected_draw_indices: tuple[int, ...],
) -> None:
    if not isinstance(table, Mapping):
        raise TypeError(f"table {name!r} must be a mapping")
    _require_exact_keys(table, _TABLE_KEYS, f"table {name!r}")
    if tuple(table["labels"]) != EVIDENCE_LABELS:
        raise ValueError(f"table {name!r} does not carry all evidence labels")
    if table["unit_label"] != _TABLE_UNIT_LABELS[name]:
        raise ValueError(f"table {name!r} changed its unit label")
    if table["annual"] is not True:
        raise ValueError(f"table {name!r} must be annual")
    if table["odd_year_carry_disclosure"] != ODD_YEAR_CARRY_DISCLOSURE:
        raise ValueError(
            f"annual table {name!r} omits the odd-year carry disclosure"
        )

    origin, dimension_names, metrics = _table_spec(name)
    per_draw = _rows(table["per_draw"], f"table {name!r} per_draw")
    annual_keys = frozenset(
        {
            "draw_index",
            *dimension_names,
            *metrics,
            *(("odd_year_carry_affected",) if origin is None else ()),
        }
    )
    annual_values: dict[
        tuple[Any, ...], dict[int, Mapping[str, float | None]]
    ] = {}
    observed_grid: set[tuple[int, tuple[Any, ...]]] = set()
    for index, row in enumerate(per_draw):
        _require_exact_keys(
            row,
            annual_keys,
            f"table {name!r} per_draw row {index}",
        )
        draw = _integer(row["draw_index"], f"table {name!r} draw_index")
        year = _integer(row["year"], f"table {name!r} year")
        if draw not in expected_draw_indices:
            raise ValueError(f"table {name!r} has an unregistered draw")
        if year not in _REPORT_YEARS:
            raise ValueError(f"table {name!r} has an out-of-window year")
        dimensions: tuple[Any, ...]
        if origin is None:
            dimensions = (year,)
            if row["odd_year_carry_affected"] is not (year % 2 == 1):
                raise ValueError(
                    f"table {name!r} odd-year carry flag is inconsistent"
                )
        else:
            if row["claim_origin"] != origin:
                raise ValueError(f"table {name!r} has the wrong claim origin")
            dimensions = (origin, year)
        grid_key = (draw, dimensions)
        if grid_key in observed_grid:
            raise ValueError(f"table {name!r} contains duplicate annual grids")
        observed_grid.add(grid_key)
        metric_values: dict[str, float | None] = {}
        for metric in metrics:
            metric_values[metric] = _number(
                row[metric],
                f"table {name!r} {metric}",
                allow_none=(metric == "average_monthly_benefit_at_award"),
            )
        annual_values.setdefault(dimensions, {})[draw] = metric_values

    expected_dimensions = (
        {(origin, year) for year in _REPORT_YEARS}
        if origin is not None
        else {(year,) for year in _REPORT_YEARS}
    )
    expected_grid = {
        (draw, dimensions)
        for draw in expected_draw_indices
        for dimensions in expected_dimensions
    }
    if observed_grid != expected_grid:
        raise ValueError(
            f"table {name!r} does not publish the exact annual draw grid"
        )
    aggregate = _rows(table["aggregate"], f"table {name!r} aggregate")
    _validate_aggregate_rows(
        rows=aggregate,
        values_by_dimension=annual_values,
        dimension_names=dimension_names,
        metrics=metrics,
        expected_draw_indices=expected_draw_indices,
        label=f"table {name!r} annual",
    )

    companion = _rows(
        table["biennial_companion"],
        f"table {name!r} biennial_companion",
    )
    per_draw_companion = [
        row for row in companion if row.get("row_basis") == "per_draw"
    ]
    across_draw_companion = [
        row for row in companion if row.get("row_basis") == "across_draw"
    ]
    if len(per_draw_companion) + len(across_draw_companion) != len(companion):
        raise ValueError(
            f"table {name!r} biennial row_basis is outside the frozen enum"
        )
    biennial_dimension_names = (
        ("claim_origin", "end_year", "component_years")
        if origin is not None
        else ("end_year", "component_years")
    )
    companion_keys = frozenset(
        {
            "row_basis",
            "draw_index",
            *biennial_dimension_names,
            *metrics,
            "odd_year_carry_disclosure",
            *(
                ("odd_year_carry_pair_interpretation",)
                if origin is None
                else ()
            ),
        }
    )
    biennial_values: dict[
        tuple[Any, ...], dict[int, Mapping[str, float | None]]
    ] = {}
    observed_biennial_grid: set[tuple[int, tuple[Any, ...]]] = set()
    for index, row in enumerate(per_draw_companion):
        _require_exact_keys(
            row,
            companion_keys,
            f"table {name!r} per-draw biennial row {index}",
        )
        draw = _integer(
            row["draw_index"],
            f"table {name!r} biennial draw_index",
        )
        end_year = _integer(
            row["end_year"],
            f"table {name!r} biennial end_year",
        )
        if draw not in expected_draw_indices:
            raise ValueError(
                f"table {name!r} biennial row has an unregistered draw"
            )
        if end_year not in _BIENNIAL_END_YEARS:
            raise ValueError(
                f"table {name!r} biennial row has an invalid end_year"
            )
        component_years = _component_years(
            row["component_years"],
            end_year=end_year,
            label=f"table {name!r} biennial",
        )
        if row["odd_year_carry_disclosure"] != ODD_YEAR_CARRY_DISCLOSURE:
            raise ValueError(
                f"table {name!r} biennial row changed its carry disclosure"
            )
        if origin is None:
            dimensions = (end_year, component_years)
            if (
                not isinstance(
                    row["odd_year_carry_pair_interpretation"],
                    str,
                )
                or not row["odd_year_carry_pair_interpretation"]
            ):
                raise ValueError(
                    f"table {name!r} omits its pair interpretation"
                )
        else:
            if row["claim_origin"] != origin:
                raise ValueError(
                    f"table {name!r} biennial row has the wrong claim origin"
                )
            dimensions = (origin, end_year, component_years)
        grid_key = (draw, dimensions)
        if grid_key in observed_biennial_grid:
            raise ValueError(
                f"table {name!r} contains duplicate biennial grids"
            )
        observed_biennial_grid.add(grid_key)
        metric_values = {}
        for metric in metrics:
            metric_values[metric] = _number(
                row[metric],
                f"table {name!r} biennial {metric}",
                allow_none=(metric == "average_monthly_benefit_at_award"),
            )
        biennial_values.setdefault(dimensions, {})[draw] = metric_values

    expected_biennial_dimensions = (
        {
            (origin, end_year, (end_year - 1, end_year))
            for end_year in _BIENNIAL_END_YEARS
        }
        if origin is not None
        else {
            (end_year, (end_year - 1, end_year))
            for end_year in _BIENNIAL_END_YEARS
        }
    )
    expected_biennial_grid = {
        (draw, dimensions)
        for draw in expected_draw_indices
        for dimensions in expected_biennial_dimensions
    }
    if observed_biennial_grid != expected_biennial_grid:
        raise ValueError(
            f"table {name!r} does not publish the exact biennial draw grid"
        )
    _validate_aggregate_rows(
        rows=across_draw_companion,
        values_by_dimension=biennial_values,
        dimension_names=biennial_dimension_names,
        metrics=metrics,
        expected_draw_indices=expected_draw_indices,
        label=f"table {name!r} biennial",
        row_basis=True,
    )


def _validate_wide_section(
    section: Mapping[str, Any],
    *,
    expected_draw_indices: tuple[int, ...],
    label: str,
    expected_metrics: frozenset[str] | None = None,
) -> dict[int, Mapping[str, float | None]]:
    per_draw = _rows(section["per_draw"], f"{label} per_draw")
    first_metrics = frozenset(per_draw[0]) - {"draw_index"}
    if not first_metrics:
        raise ValueError(f"{label} per_draw has no metrics")
    if expected_metrics is not None and first_metrics != expected_metrics:
        raise ValueError(f"{label} per_draw metric set is incomplete")
    by_draw: dict[int, Mapping[str, float | None]] = {}
    expected_row_keys = frozenset({"draw_index", *first_metrics})
    for index, row in enumerate(per_draw):
        _require_exact_keys(row, expected_row_keys, f"{label} row {index}")
        draw = _integer(row["draw_index"], f"{label} draw_index")
        if draw in by_draw:
            raise ValueError(f"{label} contains duplicate draw rows")
        if draw not in expected_draw_indices:
            raise ValueError(f"{label} contains an unregistered draw")
        by_draw[draw] = {
            metric: _number(row[metric], f"{label} {metric}")
            for metric in first_metrics
        }
    if set(by_draw) != set(expected_draw_indices):
        raise ValueError(f"{label} does not publish every registered draw")

    aggregate = _rows(section["aggregate"], f"{label} aggregate")
    aggregate_keys = frozenset(
        {
            "metric",
            "n_draws",
            "n_observations",
            "mean",
            "sample_sd",
        }
    )
    by_metric: dict[str, Mapping[str, Any]] = {}
    for index, row in enumerate(aggregate):
        _require_exact_keys(
            row,
            aggregate_keys,
            f"{label} aggregate row {index}",
        )
        metric = row["metric"]
        if not isinstance(metric, str) or metric not in first_metrics:
            raise ValueError(f"{label} aggregate has an unknown metric")
        if metric in by_metric:
            raise ValueError(f"{label} aggregate contains duplicate metrics")
        by_metric[metric] = row
    if set(by_metric) != set(first_metrics):
        raise ValueError(f"{label} aggregate metric grid is incomplete")
    for metric, row in by_metric.items():
        _require_summary(
            row,
            [by_draw[draw][metric] for draw in expected_draw_indices],
            label=f"{label} {metric}",
        )
    return by_draw


def _validate_career_diagnostics(
    rows: Any,
    *,
    expected_draw_indices: tuple[int, ...],
    count_rows: Mapping[int, Mapping[str, float | None]],
) -> None:
    records = _rows(
        rows,
        "diagnostics included_career_per_draw",
        allow_empty=True,
    )
    grid: set[tuple[int, int | str]] = set()
    observed_counts = {draw: 0 for draw in expected_draw_indices}
    for index, row in enumerate(records):
        _require_exact_keys(
            row,
            _CAREER_DIAGNOSTIC_KEYS,
            f"included career diagnostic row {index}",
        )
        draw = _integer(row["draw_index"], "career diagnostic draw_index")
        if draw not in expected_draw_indices:
            raise ValueError("career diagnostic has an unregistered draw")
        person_id = row["person_id"]
        if isinstance(person_id, bool) or not (
            isinstance(person_id, Integral)
            or isinstance(person_id, str)
            and person_id
        ):
            raise TypeError(
                "career diagnostic person_id must be an integer or string"
            )
        grid_key = (draw, person_id)
        if grid_key in grid:
            raise ValueError("career diagnostics contain duplicate people")
        grid.add(grid_key)
        observed_counts[draw] += 1
        if row["claim_origin"] not in _BENEFIT_ORIGINS:
            raise ValueError("career diagnostic has an unknown claim origin")
        if row["birth_source"] not in _BIRTH_SOURCE_KEYS:
            raise ValueError("career diagnostic has an unknown birth source")
        for boolean_key in (
            "birth_year_inferred",
            "top35_reaches_pre_1968",
            "positive_post_claim_earnings",
        ):
            if not isinstance(row[boolean_key], bool):
                raise TypeError(
                    f"career diagnostic {boolean_key} must be boolean"
                )
        if row["birth_year_inferred"] is (
            row["birth_source"] != "inferred_period_age"
        ):
            raise ValueError(
                "career diagnostic birth inference fields are inconsistent"
            )
        for share_key in (
            "coverage_ratio",
            "imputed_year_share",
            "affected_odd_year_share",
        ):
            share = _number(row[share_key], f"career diagnostic {share_key}")
            if share is None or not 0.0 <= share <= 1.0:
                raise ValueError(
                    f"career diagnostic {share_key} must lie in [0, 1]"
                )
        for provenance_key in (
            "provenance_counts",
            "coverage_provenance_counts",
        ):
            provenance = row[provenance_key]
            if not isinstance(provenance, Mapping):
                raise TypeError(
                    f"career diagnostic {provenance_key} must be a mapping"
                )
            _require_exact_keys(
                provenance,
                _CAREER_PROVENANCE_KEYS,
                f"career diagnostic {provenance_key}",
            )
            if any(
                _integer(value, f"career diagnostic {provenance_key}") < 0
                for value in provenance.values()
            ):
                raise ValueError(
                    f"career diagnostic {provenance_key} must be nonnegative"
                )
        pre_1968_count = _integer(
            row["pre_1968_top35_zero_year_count"],
            "career diagnostic pre-1968 count",
        )
        if pre_1968_count < 0:
            raise ValueError("career diagnostic pre-1968 count is negative")
        if row["top35_reaches_pre_1968"] is (pre_1968_count == 0):
            raise ValueError(
                "career diagnostic pre-1968 fields are inconsistent"
            )
        if (
            _integer(
                row["award_formula_computation_count"],
                "career diagnostic award computation count",
            )
            != 1
        ):
            raise ValueError("career diagnostic award must be computed once")
        if (
            _integer(
                row["post_claim_recomputation_count"],
                "career diagnostic recomputation count",
            )
            != 0
        ):
            raise ValueError("career diagnostic records benefit recomputation")
    for draw in expected_draw_indices:
        included = count_rows[draw]["inclusion__included__unweighted"]
        if included is None or not included.is_integer() or included < 0:
            raise ValueError(
                "included unweighted count must be a nonnegative integer"
            )
        if observed_counts[draw] != int(included):
            raise ValueError(
                "career diagnostics do not match included claimant counts"
            )


def _validate_count_invariants(
    count_rows: Mapping[int, Mapping[str, float | None]],
) -> None:
    def value(
        row: Mapping[str, float | None],
        category: str,
        key: str,
        measure: str,
    ) -> float:
        result = row[f"{category}__{key}__{measure}"]
        if result is None:
            raise ValueError("count metrics cannot be null")
        return result

    def equal(left: float, right: float, label: str) -> None:
        if not math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-9):
            raise ValueError(f"count invariant failed: {label}")

    stage_d_exclusions = (
        "excluded_domain_incomplete",
        "excluded_pre1979_eligibility",
        "excluded_empty_span",
        "excluded_chronology_inconsistent",
        "excluded_low_coverage",
    )
    for draw, row in count_rows.items():
        for metric, metric_value in row.items():
            if metric_value is None:
                raise ValueError("count metrics cannot be null")
            if metric.endswith("__unweighted") and (
                metric_value < 0 or not metric_value.is_integer()
            ):
                raise ValueError(
                    f"draw {draw} unweighted counts must be "
                    "nonnegative integers"
                )
            if metric.endswith("__weighted_share"):
                if not 0.0 <= metric_value <= 1.0:
                    raise ValueError(
                        f"draw {draw} weighted shares must lie in [0, 1]"
                    )
            elif metric_value < 0:
                raise ValueError(
                    f"draw {draw} count weights must be nonnegative"
                )
        for measure in ("unweighted", "weighted"):
            dispositions = math.fsum(
                value(row, "inclusion", key, measure)
                for key in _INCLUSION_COUNT_KEYS[:9]
            )
            births = math.fsum(
                value(row, "birth_source", key, measure)
                for key in _BIRTH_SOURCE_KEYS
            )
            equal(
                dispositions,
                births,
                f"draw {draw} dispositions versus birth sources ({measure})",
            )
            nonclaimant = value(
                row,
                "inclusion",
                "nonclaimant",
                measure,
            )
            paths = math.fsum(
                value(row, "inclusion", key, measure)
                for key in ("drawn_never_claimed", "never_drawn")
            )
            equal(
                nonclaimant,
                paths,
                f"draw {draw} nonclaimant paths ({measure})",
            )
            candidates = math.fsum(
                value(row, "inclusion", f"origin_{origin}", measure)
                for origin in _BENEFIT_ORIGINS
            )
            stage_d = math.fsum(
                value(row, "inclusion", key, measure)
                for key in (*stage_d_exclusions, "included")
            )
            equal(
                candidates,
                stage_d,
                f"draw {draw} Stage-D candidate origins ({measure})",
            )
            included = value(row, "inclusion", "included", measure)
            included_origins = math.fsum(
                value(row, "included_origin", origin, measure)
                for origin in _BENEFIT_ORIGINS
            )
            equal(
                included,
                included_origins,
                f"draw {draw} included origins ({measure})",
            )
            opening = value(
                row,
                "included_origin",
                "opening_backfill",
                measure,
            )
            denominator = value(
                row,
                "opening_stock_snap",
                "included_opening_backfill",
                measure,
            )
            equal(
                opening,
                denominator,
                f"draw {draw} opening snap denominator ({measure})",
            )
            for endpoint in ("lower_endpoint", "upper_endpoint"):
                endpoint_count = value(
                    row,
                    "opening_stock_snap",
                    endpoint,
                    measure,
                )
                if endpoint_count < 0 or endpoint_count > denominator:
                    raise ValueError(
                        "count invariant failed: opening endpoint snap "
                        f"exceeds denominator in draw {draw} ({measure})"
                    )
            for endpoint in ("lower_endpoint", "upper_endpoint"):
                numerator = value(
                    row,
                    "opening_stock_snap",
                    endpoint,
                    "numerator_weight",
                )
                endpoint_weight = value(
                    row,
                    "opening_stock_snap",
                    endpoint,
                    "weighted",
                )
                equal(
                    numerator,
                    endpoint_weight,
                    f"draw {draw} {endpoint} weighted numerator",
                )
                share_denominator = value(
                    row,
                    "opening_stock_snap",
                    endpoint,
                    "denominator_weight",
                )
                weighted_denominator = value(
                    row,
                    "opening_stock_snap",
                    "included_opening_backfill",
                    "weighted",
                )
                equal(
                    share_denominator,
                    weighted_denominator,
                    f"draw {draw} {endpoint} weighted denominator",
                )
                expected_share = (
                    numerator / weighted_denominator
                    if weighted_denominator > 0
                    else 0.0
                )
                share = value(
                    row,
                    "opening_stock_snap",
                    endpoint,
                    "weighted_share",
                )
                equal(
                    share,
                    expected_share,
                    f"draw {draw} {endpoint} weighted share",
                )


def validate_first_estimates_artifact(
    artifact: Mapping[str, Any],
    *,
    expected_configuration_echo: Mapping[str, Any],
) -> None:
    """Validate the complete publication object before its one-shot write."""
    _require_exact_keys(artifact, _ARTIFACT_KEYS, "artifact")
    if artifact["schema_version"] != ARTIFACT_SCHEMA_VERSION:
        raise ValueError("first-estimates artifact schema version changed")
    if artifact["configuration_echo"] != expected_configuration_echo:
        raise ValueError(
            "configuration_echo differs from the pre-compute configuration"
        )
    identity = artifact["identity"]
    if not isinstance(identity, Mapping):
        raise TypeError("artifact identity must be a mapping")
    _require_exact_keys(
        identity,
        frozenset({"report_id", "report_class", "registration_reference"}),
        "artifact identity",
    )
    if identity["report_id"] != "first_estimates":
        raise ValueError("artifact report_id changed")
    if identity["report_class"] != "registered estimates report":
        raise ValueError("artifact report_class changed")
    if not isinstance(identity.get("registration_reference"), str):
        raise TypeError("registration_reference must be a JSON string")
    if identity["registration_reference"] != expected_configuration_echo.get(
        "registration_reference"
    ):
        raise ValueError(
            "identity registration reference differs from configuration"
        )
    integrity = artifact["integrity"]
    sidecar = (
        integrity.get("environment_sidecar")
        if isinstance(integrity, Mapping)
        else None
    )
    if not isinstance(sidecar, Mapping):
        raise ValueError("artifact has no environment-sidecar binding")
    _require_exact_keys(
        integrity,
        frozenset({"environment_sidecar"}),
        "artifact integrity",
    )
    _require_exact_keys(
        sidecar,
        frozenset({"path", "sha256"}),
        "artifact environment sidecar",
    )
    if sidecar["path"] != "first_estimates_v1.json.env.json":
        raise ValueError("artifact environment-sidecar path changed")
    digest = sidecar.get("sha256")
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise ValueError("environment-sidecar sha256 is invalid")
    execution = artifact["execution"]
    if not isinstance(execution, Mapping):
        raise TypeError("artifact execution must be a mapping")
    _require_exact_keys(
        execution,
        frozenset({"canonical_rule", "completed_draw_indices", "assembly"}),
        "artifact execution",
    )
    if execution.get("canonical_rule") != (CANONICAL_EXECUTION_RULE):
        raise ValueError("artifact changed the canonical execution rule")
    if execution["completed_draw_indices"] != list(_REGISTERED_DRAW_INDICES):
        raise ValueError("artifact execution does not record all draws")
    if execution["assembly"] != "pure_post_compute":
        raise ValueError("artifact execution assembly mode changed")
    if artifact["parameters"] != expected_configuration_echo.get("parameters"):
        raise ValueError(
            "artifact parameters differ from the registered configuration"
        )
    counts = artifact["counts"]
    if not isinstance(counts, Mapping):
        raise TypeError("artifact counts must be a mapping")
    _require_exact_keys(counts, _COUNTS_KEYS, "artifact counts")
    diagnostics = artifact["diagnostics"]
    if not isinstance(diagnostics, Mapping):
        raise TypeError("artifact diagnostics must be a mapping")
    _require_exact_keys(
        diagnostics,
        _DIAGNOSTICS_KEYS,
        "artifact diagnostics",
    )
    tables = artifact["tables"]
    if not isinstance(tables, Mapping):
        raise TypeError("artifact tables must be a mapping")
    _require_exact_keys(tables, _TABLE_NAMES, "artifact tables")
    projection = expected_configuration_echo.get("projection")
    expected_draw_indices = (
        projection.get("draw_indices")
        if isinstance(projection, Mapping)
        else None
    )
    if not isinstance(expected_draw_indices, list):
        raise ValueError("configuration has no integer draw-index list")
    normalized_draw_indices = tuple(
        _integer(index, "configuration draw index")
        for index in expected_draw_indices
    )
    if normalized_draw_indices != _REGISTERED_DRAW_INDICES:
        raise ValueError(
            "configuration does not register exact draw indices 0-19"
        )
    for name, table in tables.items():
        _validate_table(
            str(name),
            table,
            expected_draw_indices=normalized_draw_indices,
        )
    count_rows = _validate_wide_section(
        counts,
        expected_draw_indices=normalized_draw_indices,
        label="counts",
        expected_metrics=_COUNT_METRICS,
    )
    if counts["entrant_diagnostic"] != _ENTRANT_DISCLOSURE:
        raise ValueError("entrant diagnostic disclosure changed")
    _validate_count_invariants(count_rows)
    _validate_wide_section(
        diagnostics,
        expected_draw_indices=normalized_draw_indices,
        label="diagnostics",
    )
    _validate_career_diagnostics(
        diagnostics["included_career_per_draw"],
        expected_draw_indices=normalized_draw_indices,
        count_rows=count_rows,
    )
    if diagnostics["context_ratio"] != _CONTEXT_RATIO_DISCLOSURE:
        raise ValueError(
            "context ratio must retain its exact not_computed disclosure"
        )
    if diagnostics["payment_year_convention"] != _PAYMENT_YEAR_CONVENTION:
        raise ValueError("payment-year convention disclosure changed")
    if diagnostics["benefit_measure"] != _BENEFIT_MEASURE_LABEL:
        raise ValueError("benefit measure disclosure changed")
    if diagnostics["revenue_population_basis"] != (
        "unsplit projection.slices"
    ):
        raise ValueError("revenue population-basis disclosure changed")
    if artifact["gap_block"] != list(GAP_BLOCK):
        raise ValueError("artifact gap block differs from the frozen design")
    if artifact["certifies_nothing"] != list(CERTIFIES_NOTHING):
        raise ValueError("artifact certifies_nothing statements changed")
    _require_json_finite(artifact)
    canonical_json_bytes(artifact)


def write_first_estimates_artifact(
    path: str | Path,
    artifact: Mapping[str, Any],
    *,
    expected_configuration_echo: Mapping[str, Any],
    sidecar_payload: bytes,
) -> None:
    """Validate and exclusively write the integrity-bound report pair."""
    destination = Path(path)
    if destination.name != DEFAULT_ARTIFACT_PATH.name:
        raise ValueError(
            "the first-estimates writer requires first_estimates_v1.json"
        )
    expected_hash = hashlib.sha256(sidecar_payload).hexdigest()
    integrity = artifact.get("integrity")
    sidecar = (
        integrity.get("environment_sidecar")
        if isinstance(integrity, Mapping)
        else None
    )
    if not isinstance(sidecar, Mapping) or sidecar.get("sha256") != (
        expected_hash
    ):
        raise ValueError(
            "primary artifact does not bind the supplied sidecar bytes"
        )
    if sidecar.get("path") != f"{destination.name}.env.json":
        raise ValueError("primary artifact records the wrong sidecar path")
    try:
        parsed_sidecar = json.loads(sidecar_payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("environment sidecar is not valid JSON") from error
    if canonical_json_bytes(parsed_sidecar) != sidecar_payload:
        raise ValueError("environment sidecar bytes are not canonical JSON")
    validate_first_estimates_artifact(
        artifact,
        expected_configuration_echo=expected_configuration_echo,
    )
    artifacts.write_new(
        destination,
        artifact,
        sidecar=True,
        sidecar_payload=sidecar_payload,
    )


def _parse_utc_timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or _UTC_TIMESTAMP.fullmatch(value) is None:
        raise ValueError("timestamp_utc must be ISO-8601 with Z")
    try:
        parsed = datetime.fromisoformat(f"{value[:-1]}+00:00")
    except ValueError as error:
        raise ValueError("timestamp_utc must be ISO-8601 with Z") from error
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(
        parsed
    ):
        raise ValueError("timestamp_utc must be UTC")
    return parsed


def _contains_numeric_array(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_contains_numeric_array(child) for child in value.values())
    if isinstance(value, (list, tuple)):
        if any(
            isinstance(child, (int, float)) and not isinstance(child, bool)
            for child in value
        ):
            return True
        return any(_contains_numeric_array(child) for child in value)
    return False


def validate_first_estimates_incident(
    record: Mapping[str, Any],
    *,
    path: str | Path,
    expected_configuration_echo: Mapping[str, Any],
    repository_root: str | Path,
) -> None:
    """Enforce the exact frozen incident schema and no-output-value rule."""
    _require_exact_keys(record, _INCIDENT_KEYS, "incident")
    if record["schema_version"] != INCIDENT_SCHEMA_VERSION:
        raise ValueError("incident schema version changed")
    index = record["incident_index"]
    if isinstance(index, bool) or not isinstance(index, int) or index < 1:
        raise TypeError("incident_index must be a positive integer")
    match = _INCIDENT_FILENAME.fullmatch(Path(path).name)
    if match is None or int(match.group(1)) != index:
        raise ValueError("incident index does not match its filename")
    _parse_utc_timestamp(record["timestamp_utc"])
    phase = record["phase"]
    if phase not in INCIDENT_PHASES:
        raise ValueError("incident phase is outside the frozen enum")
    for key in ("reason", "reason_detail", "registration_reference"):
        if not isinstance(record[key], str):
            raise TypeError(f"{key} must be a JSON string")
    if not record["reason"]:
        raise ValueError("incident reason must not be empty")
    if record["configuration_echo"] != expected_configuration_echo:
        raise ValueError(
            "incident configuration_echo is not the pre-compute object"
        )
    if not isinstance(record["configuration_echo"], Mapping):
        raise TypeError("incident configuration_echo must be a mapping")
    if record["registration_reference"] != expected_configuration_echo.get(
        "registration_reference"
    ):
        raise ValueError(
            "incident registration reference differs from configuration"
        )
    artifact_path = record["artifact_path"]
    if artifact_path is not None and not isinstance(artifact_path, str):
        raise TypeError("artifact_path must be a JSON string or null")
    root = Path(repository_root).resolve()
    default_partial = root / DEFAULT_ARTIFACT_PATH
    partial_exists = default_partial.is_file()
    if artifact_path is not None:
        candidate = root / artifact_path
        try:
            candidate.resolve().relative_to(root)
        except ValueError as error:
            raise ValueError("artifact_path escapes the repository") from error
        if candidate.resolve() != default_partial.resolve():
            raise ValueError(
                "artifact_path must identify runs/first_estimates_v1.json"
            )
    expected_artifact_path = (
        DEFAULT_ARTIFACT_PATH.as_posix()
        if phase == "publication" and partial_exists
        else None
    )
    if artifact_path != expected_artifact_path:
        raise ValueError(
            "artifact_path must be non-null iff a publication partial exists"
        )
    outside_echo = {
        key: value
        for key, value in record.items()
        if key != "configuration_echo"
    }
    if _contains_numeric_array(outside_echo):
        raise ValueError(
            "incident contains a numeric array outside configuration_echo"
        )
    _require_json_finite(record)
    canonical_json_bytes(record)


def incident_is_retry_eligible(record: Mapping[str, Any]) -> bool:
    """Return the canonical external-pre-output retry classification."""
    return (
        record.get("phase") in {"preparation", "compute"}
        and isinstance(record.get("reason"), str)
        and record["reason"].startswith("external_")
    )


def _next_incident_path(repository_root: Path) -> tuple[Path, int]:
    runs = repository_root / "runs"
    existing: list[int] = []
    for path in runs.glob("first_estimates_incident_*.json"):
        match = _INCIDENT_FILENAME.fullmatch(path.name)
        if match is not None:
            existing.append(int(match.group(1)))
    ordered = sorted(existing)
    if ordered != list(range(1, len(ordered) + 1)):
        raise RuntimeError(
            "existing first-estimates incidents are not contiguous"
        )
    index = len(ordered) + 1
    return runs / f"first_estimates_incident_{index}.json", index


def write_first_estimates_incident(
    *,
    repository_root: str | Path,
    phase: str,
    reason: str,
    reason_detail: str,
    registration_reference: str,
    configuration_echo: Mapping[str, Any],
    partial_artifact_path: str | Path | None = None,
    timestamp_utc: str | None = None,
) -> Path:
    """Append the next validated incident record without a sidecar."""
    root = Path(repository_root).resolve()
    path, index = _next_incident_path(root)
    relative_artifact: str | None = None
    if partial_artifact_path is not None:
        partial = Path(partial_artifact_path)
        if not partial.is_absolute():
            partial = root / partial
        try:
            relative_artifact = partial.resolve().relative_to(root).as_posix()
        except ValueError as error:
            raise ValueError(
                "partial artifact path is outside the repository"
            ) from error
        if not partial.is_file():
            raise FileNotFoundError(
                "partial artifact path does not identify an existing file"
            )
    timestamp = timestamp_utc or (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )
    record = {
        "schema_version": INCIDENT_SCHEMA_VERSION,
        "incident_index": index,
        "timestamp_utc": timestamp,
        "phase": phase,
        "reason": reason,
        "reason_detail": reason_detail,
        "registration_reference": registration_reference,
        "configuration_echo": dict(configuration_echo),
        "artifact_path": relative_artifact,
    }
    validate_first_estimates_incident(
        record,
        path=path,
        expected_configuration_echo=configuration_echo,
        repository_root=root,
    )
    artifacts.write_new(path, record)
    return path


def table_record(
    *,
    per_draw: Sequence[Mapping[str, Any]],
    aggregate: Sequence[Mapping[str, Any]],
    unit_label: str,
    annual: bool,
    biennial_companion: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Wrap report rows with the repeated evidential labels and disclosures."""
    record: dict[str, Any] = {
        "labels": list(EVIDENCE_LABELS),
        "unit_label": unit_label,
        "annual": bool(annual),
        "per_draw": [dict(row) for row in per_draw],
        "aggregate": [dict(row) for row in aggregate],
    }
    if annual:
        record["odd_year_carry_disclosure"] = ODD_YEAR_CARRY_DISCLOSURE
        record["biennial_companion"] = [
            dict(row) for row in (biennial_companion or ())
        ]
    return record
