"""Capability-gated comparison engine for the anchor-context report.

The public helpers accept visibly nonproduction fixture documents only.
Production computation consumes the opaque, hash-gated input bundle minted
inside the sealed coordinator; raw production mappings are never a supported
engine input.
"""

from __future__ import annotations

import copy
import importlib
import math
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from populace_dynamics.estimates import anchor_context_registry as registry
from populace_dynamics.estimates.ledgers import _summary

EVIDENCE_LABELS = (
    "frame-relative",
    "pre-alignment",
    "labor-income proxy",
)

_BENEFIT_ROW_KEYS = frozenset(
    {
        "draw_index",
        "claim_origin",
        "year",
        "unweighted_award_count",
        "weighted_award_count",
        "average_monthly_benefit_at_award",
        "unweighted_beneficiary_count",
        "weighted_beneficiary_count",
        "frame_annualized_benefit",
    }
)
_REVENUE_ROW_KEYS = frozenset(
    {
        "draw_index",
        "year",
        "unweighted_person_year_count",
        "weighted_person_year_count",
        "unweighted_covered_earner_count",
        "weighted_covered_earner_count",
        "weighted_taxable_payroll",
        "employee_contributions",
        "employer_contributions",
        "combined_contributions",
        "odd_year_carry_affected",
    }
)
_TABLE_ROW_KEYS = {
    "modeled_award_flow": _BENEFIT_ROW_KEYS,
    "opening_stock": _BENEFIT_ROW_KEYS,
    "revenue": _REVENUE_ROW_KEYS,
}
_TABLE_CLAIM_ORIGINS = {
    "modeled_award_flow": "modeled_award",
    "opening_stock": "opening_backfill",
    "revenue": None,
}
_EXPECTED_GRID = tuple(
    (draw_index, year)
    for draw_index in registry.DRAW_INDICES
    for year in registry.REPORT_YEARS
)
_RESULT_KEYS = frozenset(
    {
        "comparison_results",
        "official_anchor_level_panel",
        "model_level_panel",
    }
)
_AVAILABLE_RESULT_KEYS = frozenset(
    {"comparison_id", "availability", "evaluated", "annual_rows"}
)
_UNAVAILABLE_RESULT_KEYS = frozenset(
    {"comparison_id", "availability", "evaluated", "reason"}
)
_COMPARISON_ROW_KEYS = frozenset(
    {
        "year",
        "model_statistic_mean",
        "model_statistic_sample_sd",
        "official_statistic",
        "comparison_mean",
        "comparison_sample_sd",
    }
)
_OFFICIAL_PANEL_KEYS = frozenset({"series_id", "stored_unit", "annual_rows"})
_OFFICIAL_ROW_KEYS = frozenset({"year", "value"})
_MODEL_PANEL_KEYS = frozenset({"model_metric_id", "unit", "annual_rows"})
_MODEL_ROW_KEYS = frozenset({"year", "mean", "sample_sd"})


class AnchorContextValidationError(ValueError):
    """A frozen selector, grid, formula, or results contract was violated."""


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a JSON object")
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise TypeError(f"{label} must be a JSON array")
    return value


def _require_exact_keys(
    value: Mapping[str, Any],
    expected: frozenset[str],
    label: str,
) -> None:
    observed = frozenset(value)
    if observed != expected:
        raise AnchorContextValidationError(
            f"{label} keys {sorted(observed)} != expected {sorted(expected)}"
        )


def _integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be a JSON integer")
    return value


def _number(value: Any, label: str) -> int | float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise TypeError(f"{label} must be a finite JSON number")
    return value


def _positive_number(value: Any, label: str) -> int | float:
    observed = _number(value, label)
    if observed <= 0:
        raise AnchorContextValidationError(f"{label} must be positive")
    return observed


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise TypeError(f"{label} must be a nonempty JSON string")
    return value


def _document_authority_protocol():
    module_globals = globals()
    getframe = sys._getframe
    require_fixture_inputs: Callable[..., Any] | None = None
    require_production_inputs: Callable[..., Any] | None = None
    binding_taken = False
    publication_name = "populace_dynamics.estimates.anchor_context_publication"
    publication_source = (
        Path(__file__).with_name("anchor_context_publication.py").resolve()
    )
    publication_code = compile(
        publication_source.read_bytes(),
        str(publication_source),
        "exec",
        dont_inherit=True,
        optimize=sys.flags.optimize,
    )

    def bind(
        fixture_verifier: Callable[..., Any],
        production_verifier: Callable[..., Any],
    ) -> None:
        nonlocal require_fixture_inputs, require_production_inputs
        if (
            require_fixture_inputs is not None
            or require_production_inputs is not None
        ):
            raise RuntimeError("report document authority already bound")
        require_fixture_inputs = fixture_verifier
        require_production_inputs = production_verifier

    def take():
        nonlocal binding_taken
        caller = getframe(1)
        module = sys.modules.get(publication_name)
        spec = getattr(module, "__spec__", None)
        origin = getattr(spec, "origin", None)
        try:
            resolved_origin = Path(origin).resolve()
            resolved_code = Path(caller.f_code.co_filename).resolve()
        except (OSError, TypeError, ValueError):
            resolved_origin = None
            resolved_code = None
        if (
            binding_taken
            or module is None
            or vars(module) is not caller.f_globals
            or caller.f_code != publication_code
            or caller.f_globals.get("__name__") != publication_name
            or resolved_origin != publication_source
            or resolved_code != publication_source
            or getattr(spec, "_initializing", False) is not True
        ):
            raise TypeError(
                "document bootstrap belongs to the canonical publication "
                "import"
            )
        binding_taken = True
        module_globals.pop(
            "_take_document_authority_verifier_binding",
            None,
        )
        return bind

    def authorize(
        input_bundle: object,
        *,
        ceremony_capability: object | None,
    ) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
        if require_fixture_inputs is None or require_production_inputs is None:
            raise RuntimeError("report document authority is not bound")
        if ceremony_capability is None:
            return require_fixture_inputs(input_bundle)
        return require_production_inputs(
            input_bundle,
            ceremony_capability=ceremony_capability,
        )

    def is_bound() -> bool:
        return (
            require_fixture_inputs is not None
            and require_production_inputs is not None
        )

    return authorize, take, is_bound


(
    _authorized_documents,
    _take_document_authority_verifier_binding,
    _document_authority_is_bound,
) = _document_authority_protocol()
del _document_authority_protocol


def _pointer_tokens(pointer: Any) -> tuple[str, ...]:
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise AnchorContextValidationError(
            "row_pointer must be an RFC 6901 JSON Pointer"
        )
    tokens: list[str] = []
    for raw in pointer[1:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if "~" in token:
            encoded = token.replace("~", "~0").replace("/", "~1")
            if encoded != raw:
                raise AnchorContextValidationError(
                    f"row_pointer has an invalid escape: {pointer!r}"
                )
        tokens.append(token)
    return tuple(tokens)


def _resolve_pointer(document: Mapping[str, Any], pointer: str) -> Any:
    current: Any = document
    for token in _pointer_tokens(pointer):
        if not isinstance(current, Mapping) or token not in current:
            raise AnchorContextValidationError(
                f"row_pointer does not resolve: {pointer!r}"
            )
        current = current[token]
    return current


def _table_name_from_pointer(pointer: str) -> str:
    tokens = _pointer_tokens(pointer)
    if (
        len(tokens) != 3
        or tokens[0] != "tables"
        or tokens[2] != "per_draw"
        or tokens[1] not in _TABLE_ROW_KEYS
    ):
        raise AnchorContextValidationError(
            f"unregistered per_draw row_pointer {pointer!r}"
        )
    return tokens[1]


def _detect_duplicate_keys(
    keys: Sequence[Any],
    *,
    label: str,
) -> None:
    seen: set[Any] = set()
    for key in keys:
        if key in seen:
            raise AnchorContextValidationError(
                f"{label} contains duplicate key {key!r}"
            )
        seen.add(key)


def _validate_table_rows(
    table_name: str,
    table: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    if table.get("labels") != list(EVIDENCE_LABELS):
        raise AnchorContextValidationError(
            f"table {table_name!r} changed the three evidence labels"
        )
    _string(table.get("unit_label"), f"table {table_name!r} unit_label")
    rows = _require_list(
        table.get("per_draw"),
        f"table {table_name!r} per_draw",
    )
    observed_grid: list[tuple[int, int]] = []
    expected_origin = _TABLE_CLAIM_ORIGINS[table_name]
    normalized: list[Mapping[str, Any]] = []
    for position, raw_row in enumerate(rows):
        row = _require_mapping(
            raw_row,
            f"table {table_name!r} per_draw row {position}",
        )
        _require_exact_keys(
            row,
            _TABLE_ROW_KEYS[table_name],
            f"table {table_name!r} per_draw row {position}",
        )
        draw_index = _integer(
            row["draw_index"],
            f"table {table_name!r} row {position} draw_index",
        )
        year = _integer(
            row["year"],
            f"table {table_name!r} row {position} year",
        )
        observed_grid.append((draw_index, year))
        if expected_origin is not None and row["claim_origin"] != (
            expected_origin
        ):
            raise AnchorContextValidationError(
                f"table {table_name!r} row {position} has wrong claim_origin"
            )
        if table_name == "revenue":
            expected_carry = year % 2 == 1
            if row["odd_year_carry_affected"] is not expected_carry:
                raise AnchorContextValidationError(
                    f"table {table_name!r} row {position} has wrong "
                    "odd_year_carry_affected"
                )
        normalized.append(row)
    _detect_duplicate_keys(observed_grid, label=f"table {table_name!r} grid")
    if tuple(observed_grid) != _EXPECTED_GRID:
        raise AnchorContextValidationError(
            f"table {table_name!r} grid is missing, extra, or reordered"
        )
    return normalized


def _validated_model_tables(
    first_estimates: Mapping[str, Any],
) -> dict[str, tuple[Mapping[str, Any], list[Mapping[str, Any]]]]:
    tables = _require_mapping(
        first_estimates.get("tables"),
        "first-estimates tables",
    )
    if frozenset(tables) != frozenset(_TABLE_ROW_KEYS):
        raise AnchorContextValidationError(
            "first-estimates tables are missing, extra, or renamed"
        )
    result = {}
    for table_name in _TABLE_ROW_KEYS:
        table = _require_mapping(
            tables[table_name],
            f"table {table_name!r}",
        )
        result[table_name] = (
            table,
            _validate_table_rows(table_name, table),
        )
    return result


def _operand_values(
    first_estimates: Mapping[str, Any],
    tables: Mapping[
        str,
        tuple[Mapping[str, Any], list[Mapping[str, Any]]],
    ],
    operand: Mapping[str, Any],
) -> dict[tuple[int, int], int | float]:
    pointer = operand["row_pointer"]
    table_name = _table_name_from_pointer(pointer)
    table, rows = tables[table_name]
    resolved = _resolve_pointer(first_estimates, pointer)
    if resolved is not table.get("per_draw"):
        raise AnchorContextValidationError(
            f"row_pointer {pointer!r} did not resolve to the validated array"
        )
    if table.get("unit_label") != operand["required_table_unit_label"]:
        raise AnchorContextValidationError(
            f"row_pointer {pointer!r} table unit label changed"
        )
    if operand["key_fields"] != ["draw_index", "year"]:
        raise AnchorContextValidationError(
            f"row_pointer {pointer!r} key fields changed"
        )
    required_values = _require_mapping(
        operand["required_row_values"],
        f"row_pointer {pointer!r} required_row_values",
    )
    value_field = operand["value_field"]
    values: dict[tuple[int, int], int | float] = {}
    for position, row in enumerate(rows):
        for field, expected in required_values.items():
            if row.get(field) != expected:
                raise AnchorContextValidationError(
                    f"row_pointer {pointer!r} row {position} changed {field}"
                )
        key = (row["draw_index"], row["year"])
        values[key] = _number(
            row.get(value_field),
            f"row_pointer {pointer!r} row {position} {value_field}",
        )
    if tuple(values) != _EXPECTED_GRID:
        raise AnchorContextValidationError(
            f"row_pointer {pointer!r} index is incomplete or reordered"
        )
    return values


def _model_metric_protocol(
    authorize_documents: Callable[
        ..., tuple[Mapping[str, Any], Mapping[str, Any]]
    ],
):
    def extract(
        input_bundle: object,
        *,
        ceremony_capability: object | None = None,
    ) -> dict[str, dict[tuple[int, int], int | float]]:
        """Resolve the exact seven model metrics on the frozen 20x8 grid."""
        first_estimates, _anchors = authorize_documents(
            input_bundle,
            ceremony_capability=ceremony_capability,
        )
        source = _require_mapping(first_estimates, "first-estimates input")
        registries = registry.frozen_registries()
        registry.validate_frozen_registries(
            required_series_ids=registries["required_series_ids"],
            model_metric_specs=registries["model_metric_specs"],
            pairings=registries["pairings"],
            comparison_specs=registries["comparison_specs"],
        )
        tables = _validated_model_tables(source)
        extracted: dict[str, dict[tuple[int, int], int | float]] = {}
        for spec in registry.model_metric_specs():
            operands = [
                _operand_values(source, tables, operand)
                for operand in spec["operands"]
            ]
            if any(tuple(values) != _EXPECTED_GRID for values in operands):
                raise AnchorContextValidationError(
                    f"metric {spec['model_metric_id']!r} operand grids differ"
                )
            units = {operand["value_unit"] for operand in spec["operands"]}
            if units != {spec["unit"]}:
                raise AnchorContextValidationError(
                    f"metric {spec['model_metric_id']!r} units differ"
                )
            operation = spec["operation"]
            if operation == "select":
                if len(operands) != 1:
                    raise AnchorContextValidationError(
                        f"select metric {spec['model_metric_id']!r} "
                        "must have one operand"
                    )
                values = operands[0]
            elif operation == "same_key_sum":
                if len(operands) != 2:
                    raise AnchorContextValidationError(
                        f"same_key_sum metric {spec['model_metric_id']!r} "
                        "must have two operands"
                    )
                values = {
                    key: _number(
                        operands[0][key] + operands[1][key],
                        f"metric {spec['model_metric_id']!r} at {key!r}",
                    )
                    for key in _EXPECTED_GRID
                }
            else:
                raise AnchorContextValidationError(
                    f"metric {spec['model_metric_id']!r} operation changed"
                )
            extracted[spec["model_metric_id"]] = values
        if tuple(extracted) != tuple(
            spec["model_metric_id"] for spec in registry.model_metric_specs()
        ):
            raise AnchorContextValidationError(
                "model metrics are missing, extra, duplicated, or reordered"
            )
        return extracted

    extract.__name__ = "_extract_model_metrics"
    extract.__qualname__ = "_extract_model_metrics"
    return extract


_extract_model_metrics = _model_metric_protocol(_authorized_documents)
del _model_metric_protocol


def _fixture_model_metric_protocol(
    extract_model_metrics_impl: Callable[
        ...,
        dict[str, dict[tuple[int, int], int | float]],
    ],
):
    def extract_model_metrics(
        fixture_inputs: object,
    ) -> dict[str, dict[tuple[int, int], int | float]]:
        """Resolve model metrics only from the fixed nonproduction bundle."""
        return extract_model_metrics_impl(fixture_inputs)

    return extract_model_metrics


extract_model_metrics = _fixture_model_metric_protocol(_extract_model_metrics)
del _fixture_model_metric_protocol


def _validated_anchor_determinations(
    anchors: Mapping[str, Any],
) -> Mapping[str, Any]:
    if anchors.get("required_calendar_years") != list(registry.REPORT_YEARS):
        raise AnchorContextValidationError(
            "anchor required years are missing, extra, or reordered"
        )
    if anchors.get("required_series_ids") != registry.required_series_ids():
        raise AnchorContextValidationError(
            "anchor required series are missing, extra, or reordered"
        )
    determinations = _require_mapping(
        anchors.get("determinations"),
        "anchor determinations",
    )
    if frozenset(determinations) != frozenset(registry.REQUIRED_SERIES_IDS):
        raise AnchorContextValidationError(
            "anchor determinations are missing or extra"
        )
    return determinations


def _official_value_protocol(
    authorize_documents: Callable[
        ..., tuple[Mapping[str, Any], Mapping[str, Any]]
    ],
):
    def extract(
        input_bundle: object,
        *,
        ceremony_capability: object | None = None,
        expected_vintage_id: str | None = None,
    ) -> dict[str, dict[int, int | float]]:
        """Resolve all 120 normalized official values in registered order."""
        _first_estimates, anchors = authorize_documents(
            input_bundle,
            ceremony_capability=ceremony_capability,
        )
        source = _require_mapping(anchors, "anchor input")
        vintage_id = _string(
            source.get("artifact_vintage_id"),
            "anchor artifact_vintage_id",
        )
        if (
            expected_vintage_id is not None
            and vintage_id != expected_vintage_id
        ):
            raise AnchorContextValidationError(
                "anchor vintage identity changed"
            )
        if source.get("year_basis") != "calendar_year":
            raise AnchorContextValidationError("anchor year basis changed")
        determinations = _validated_anchor_determinations(source)
        extracted: dict[str, dict[int, int | float]] = {}
        for series_id in registry.REQUIRED_SERIES_IDS:
            determination = _require_mapping(
                determinations[series_id],
                f"anchor determination {series_id!r}",
            )
            if determination.get("series_id") != series_id:
                raise AnchorContextValidationError(
                    f"anchor determination {series_id!r} changed series_id"
                )
            stored_unit = _string(
                determination.get("stored_unit"),
                f"anchor determination {series_id!r} stored_unit",
            )
            scale_multiplier = _positive_number(
                determination.get("scale_multiplier"),
                f"anchor determination {series_id!r} scale_multiplier",
            )
            observations = _require_list(
                determination.get("observations"),
                f"anchor determination {series_id!r} observations",
            )
            years: list[int] = []
            by_year: dict[int, int | float] = {}
            for position, raw_observation in enumerate(observations):
                observation = _require_mapping(
                    raw_observation,
                    f"anchor {series_id!r} observation {position}",
                )
                year = _integer(
                    observation.get("year"),
                    f"anchor {series_id!r} observation {position} year",
                )
                years.append(year)
                if observation.get("year_basis") != "calendar_year":
                    raise AnchorContextValidationError(
                        f"anchor {series_id!r} {year} year basis changed"
                    )
                if observation.get("stored_unit") != stored_unit:
                    raise AnchorContextValidationError(
                        f"anchor {series_id!r} {year} stored unit changed"
                    )
                if observation.get("scale_multiplier") != scale_multiplier:
                    raise AnchorContextValidationError(
                        f"anchor {series_id!r} {year} scale multiplier changed"
                    )
                by_year[year] = _number(
                    observation.get("value"),
                    f"anchor {series_id!r} {year} value",
                )
            _detect_duplicate_keys(
                years,
                label=f"anchor {series_id!r} years",
            )
            if tuple(years) != registry.REPORT_YEARS:
                raise AnchorContextValidationError(
                    f"anchor {series_id!r} years are missing, extra, or "
                    "reordered"
                )
            extracted[series_id] = by_year
        if tuple(extracted) != registry.REQUIRED_SERIES_IDS:
            raise AnchorContextValidationError(
                "official values are missing, extra, duplicated, or reordered"
            )
        return extracted

    extract.__name__ = "_extract_official_values"
    extract.__qualname__ = "_extract_official_values"
    return extract


_extract_official_values = _official_value_protocol(_authorized_documents)
del _official_value_protocol


def _fixture_official_value_protocol(
    extract_official_values_impl: Callable[
        ...,
        dict[str, dict[int, int | float]],
    ],
):
    def extract_official_values(
        fixture_inputs: object,
        *,
        expected_vintage_id: str | None = None,
    ) -> dict[str, dict[int, int | float]]:
        """Resolve official values only from the fixed nonproduction bundle."""
        return extract_official_values_impl(
            fixture_inputs,
            expected_vintage_id=expected_vintage_id,
        )

    return extract_official_values


extract_official_values = _fixture_official_value_protocol(
    _extract_official_values
)
del _fixture_official_value_protocol


def _summarize(
    values: Sequence[int | float], label: str
) -> tuple[float, float]:
    summary = _summary(values)
    if (
        summary.n_draws != len(registry.DRAW_INDICES)
        or summary.n_observations != len(registry.DRAW_INDICES)
        or summary.mean is None
        or summary.sample_sd is None
    ):
        raise AnchorContextValidationError(
            f"{label} does not contain all registered draws"
        )
    mean = float(_number(summary.mean, f"{label} mean"))
    sample_sd = float(_number(summary.sample_sd, f"{label} sample SD"))
    if sample_sd < 0:
        raise AnchorContextValidationError(f"{label} sample SD is negative")
    return mean, sample_sd


def _model_statistic(
    spec: Mapping[str, Any],
    metrics: Mapping[str, Mapping[tuple[int, int], int | float]],
    draw_index: int,
    year: int,
) -> int | float:
    numerator_id = spec["model_numerator_metric_id"]
    numerator = _number(
        metrics[numerator_id][(draw_index, year)],
        f"{spec['comparison_id']} model numerator",
    )
    denominator_id = spec["model_denominator_metric_id"]
    if denominator_id is None:
        return numerator
    denominator = _positive_number(
        metrics[denominator_id][(draw_index, year)],
        f"{spec['comparison_id']} model denominator",
    )
    return _number(
        numerator / denominator,
        f"{spec['comparison_id']} model statistic",
    )


def _official_statistic(
    spec: Mapping[str, Any],
    official: Mapping[str, Mapping[int, int | float]],
    year: int,
) -> int | float:
    numerator_id = spec["official_numerator_series_id"]
    if numerator_id is None:
        raise AnchorContextValidationError(
            f"{spec['comparison_id']} has no official numerator"
        )
    numerator = _number(
        official[numerator_id][year],
        f"{spec['comparison_id']} official numerator",
    )
    denominator_id = spec["official_denominator_series_id"]
    if denominator_id is None:
        return numerator
    denominator = _positive_number(
        official[denominator_id][year],
        f"{spec['comparison_id']} official denominator",
    )
    return _number(
        numerator / denominator,
        f"{spec['comparison_id']} official statistic",
    )


def _available_comparison_rows(
    spec: Mapping[str, Any],
    metrics: Mapping[str, Mapping[tuple[int, int], int | float]],
    official: Mapping[str, Mapping[int, int | float]],
) -> list[dict[str, int | float]]:
    rows = []
    for year in registry.REPORT_YEARS:
        model_values = [
            _model_statistic(spec, metrics, draw_index, year)
            for draw_index in registry.DRAW_INDICES
        ]
        official_value = _positive_number(
            _official_statistic(spec, official, year),
            f"{spec['comparison_id']} official ratio denominator",
        )
        operation = spec["operation"]
        if operation not in {
            "model_intensity_over_official_intensity",
            "model_value_over_official_value",
        }:
            raise AnchorContextValidationError(
                f"{spec['comparison_id']} operation changed"
            )
        comparison_values = [
            _number(
                value / official_value,
                f"{spec['comparison_id']} comparison draw",
            )
            for value in model_values
        ]
        model_mean, model_sd = _summarize(
            model_values,
            f"{spec['comparison_id']} {year} model statistic",
        )
        comparison_mean, comparison_sd = _summarize(
            comparison_values,
            f"{spec['comparison_id']} {year} comparison",
        )
        rows.append(
            {
                "year": year,
                "model_statistic_mean": model_mean,
                "model_statistic_sample_sd": model_sd,
                "official_statistic": official_value,
                "comparison_mean": comparison_mean,
                "comparison_sample_sd": comparison_sd,
            }
        )
    return rows


def _result_build_protocol(
    authorize_documents: Callable[
        ..., tuple[Mapping[str, Any], Mapping[str, Any]]
    ],
    extract_model_metrics_impl: Callable[
        ...,
        dict[str, dict[tuple[int, int], int | float]],
    ],
    extract_official_values_impl: Callable[
        ...,
        dict[str, dict[int, int | float]],
    ],
):
    def build(
        input_bundle: object,
        *,
        ceremony_capability: object | None = None,
    ) -> dict[str, Any]:
        """Build the exact-complete three-panel results payload."""
        _first_estimates, anchors = authorize_documents(
            input_bundle,
            ceremony_capability=ceremony_capability,
        )
        metrics = extract_model_metrics_impl(
            input_bundle,
            ceremony_capability=ceremony_capability,
        )
        official = extract_official_values_impl(
            input_bundle,
            ceremony_capability=ceremony_capability,
        )
        comparison_results: list[dict[str, Any]] = []
        for spec in registry.comparison_specs():
            availability = spec["availability"]
            if availability["status"] == "unavailable":
                comparison_results.append(
                    {
                        "comparison_id": spec["comparison_id"],
                        "availability": "unavailable",
                        "evaluated": False,
                        "reason": availability["reason"],
                    }
                )
                continue
            if availability != {"status": "available", "reason": None}:
                raise AnchorContextValidationError(
                    f"{spec['comparison_id']} availability changed"
                )
            comparison_results.append(
                {
                    "comparison_id": spec["comparison_id"],
                    "availability": "available",
                    "evaluated": True,
                    "annual_rows": _available_comparison_rows(
                        spec,
                        metrics,
                        official,
                    ),
                }
            )

        determinations = _validated_anchor_determinations(anchors)
        official_panel = []
        for series_id in registry.REQUIRED_SERIES_IDS:
            determination = determinations[series_id]
            official_panel.append(
                {
                    "series_id": series_id,
                    "stored_unit": determination["stored_unit"],
                    "annual_rows": [
                        {"year": year, "value": official[series_id][year]}
                        for year in registry.REPORT_YEARS
                    ],
                }
            )

        model_panel = []
        for metric_spec in registry.model_metric_specs():
            metric_id = metric_spec["model_metric_id"]
            annual_rows = []
            for year in registry.REPORT_YEARS:
                mean, sample_sd = _summarize(
                    [
                        metrics[metric_id][(draw_index, year)]
                        for draw_index in registry.DRAW_INDICES
                    ],
                    f"{metric_id} {year} level",
                )
                annual_rows.append(
                    {"year": year, "mean": mean, "sample_sd": sample_sd}
                )
            model_panel.append(
                {
                    "model_metric_id": metric_id,
                    "unit": metric_spec["unit"],
                    "annual_rows": annual_rows,
                }
            )

        results = {
            "comparison_results": comparison_results,
            "official_anchor_level_panel": official_panel,
            "model_level_panel": model_panel,
        }
        _validate_results_structure(results)
        return results

    build.__name__ = "_build_results"
    build.__qualname__ = "_build_results"
    return build


_build_results = _result_build_protocol(
    _authorized_documents,
    _extract_model_metrics,
    _extract_official_values,
)
del _result_build_protocol


def _result_entry_protocol(
    authorize_documents: Callable[
        ..., tuple[Mapping[str, Any], Mapping[str, Any]]
    ],
    build_results_impl: Callable[..., dict[str, Any]],
):
    def build_results(
        fixture_inputs: object,
    ) -> dict[str, Any]:
        """Build results only from the fixed nonproduction fixture bundle."""
        return build_results_impl(fixture_inputs)

    def build_production_results(
        ceremony_capability: object,
        verified_inputs: object,
    ) -> dict[str, Any]:
        """Build production results only with coordinator-issued authority."""
        authorize_documents(
            verified_inputs,
            ceremony_capability=ceremony_capability,
        )
        return build_results_impl(
            verified_inputs,
            ceremony_capability=ceremony_capability,
        )

    build_production_results.__name__ = "_build_production_results"
    build_production_results.__qualname__ = "_build_production_results"
    return build_results, build_production_results


build_results, _build_production_results = _result_entry_protocol(
    _authorized_documents,
    _build_results,
)
del _result_entry_protocol


def _validate_year_rows(
    rows: Any,
    *,
    expected_keys: frozenset[str],
    label: str,
    numeric_fields: Sequence[str],
    nonnegative_fields: Sequence[str] = (),
) -> None:
    observed = _require_list(rows, f"{label} annual_rows")
    years: list[int] = []
    for position, raw_row in enumerate(observed):
        row = _require_mapping(raw_row, f"{label} row {position}")
        _require_exact_keys(row, expected_keys, f"{label} row {position}")
        year = _integer(row["year"], f"{label} row {position} year")
        years.append(year)
        for field in numeric_fields:
            _number(row[field], f"{label} {year} {field}")
        for field in nonnegative_fields:
            if _number(row[field], f"{label} {year} {field}") < 0:
                raise AnchorContextValidationError(
                    f"{label} {year} {field} must be nonnegative"
                )
    _detect_duplicate_keys(years, label=f"{label} years")
    if tuple(years) != registry.REPORT_YEARS:
        raise AnchorContextValidationError(
            f"{label} years are missing, extra, or reordered"
        )


def _validate_ordered_ids(
    rows: Any,
    *,
    id_field: str,
    expected_ids: Sequence[str],
    label: str,
) -> list[Mapping[str, Any]]:
    values = _require_list(rows, label)
    identifiers = []
    normalized = []
    for position, raw_value in enumerate(values):
        value = _require_mapping(raw_value, f"{label} row {position}")
        identifier = _string(
            value.get(id_field),
            f"{label} row {position} {id_field}",
        )
        identifiers.append(identifier)
        normalized.append(value)
    _detect_duplicate_keys(identifiers, label=f"{label} IDs")
    if tuple(identifiers) != tuple(expected_ids):
        raise AnchorContextValidationError(
            f"{label} IDs are missing, extra, or reordered"
        )
    return normalized


def _validate_results_structure(results: Mapping[str, Any]) -> None:
    _require_exact_keys(results, _RESULT_KEYS, "results")
    comparison_specs = registry.comparison_specs()
    comparison_rows = _validate_ordered_ids(
        results["comparison_results"],
        id_field="comparison_id",
        expected_ids=[spec["comparison_id"] for spec in comparison_specs],
        label="comparison_results",
    )
    for spec, row in zip(comparison_specs, comparison_rows, strict=True):
        availability = spec["availability"]
        if availability["status"] == "unavailable":
            _require_exact_keys(
                row,
                _UNAVAILABLE_RESULT_KEYS,
                f"comparison {spec['comparison_id']!r}",
            )
            if (
                row["availability"] != "unavailable"
                or row["evaluated"] is not False
                or row["reason"] != availability["reason"]
            ):
                raise AnchorContextValidationError(
                    f"comparison {spec['comparison_id']!r} changed its "
                    "unavailable disclosure"
                )
            continue
        _require_exact_keys(
            row,
            _AVAILABLE_RESULT_KEYS,
            f"comparison {spec['comparison_id']!r}",
        )
        if row["availability"] != "available" or row["evaluated"] is not True:
            raise AnchorContextValidationError(
                f"comparison {spec['comparison_id']!r} changed its "
                "available branch"
            )
        _validate_year_rows(
            row["annual_rows"],
            expected_keys=_COMPARISON_ROW_KEYS,
            label=f"comparison {spec['comparison_id']!r}",
            numeric_fields=(
                "model_statistic_mean",
                "model_statistic_sample_sd",
                "official_statistic",
                "comparison_mean",
                "comparison_sample_sd",
            ),
            nonnegative_fields=(
                "model_statistic_sample_sd",
                "comparison_sample_sd",
            ),
        )

    official_rows = _validate_ordered_ids(
        results["official_anchor_level_panel"],
        id_field="series_id",
        expected_ids=registry.REQUIRED_SERIES_IDS,
        label="official_anchor_level_panel",
    )
    for series_id, row in zip(
        registry.REQUIRED_SERIES_IDS,
        official_rows,
        strict=True,
    ):
        _require_exact_keys(
            row,
            _OFFICIAL_PANEL_KEYS,
            f"official panel {series_id!r}",
        )
        _string(row["stored_unit"], f"official panel {series_id!r} unit")
        _validate_year_rows(
            row["annual_rows"],
            expected_keys=_OFFICIAL_ROW_KEYS,
            label=f"official panel {series_id!r}",
            numeric_fields=("value",),
        )

    metric_specs = registry.model_metric_specs()
    model_rows = _validate_ordered_ids(
        results["model_level_panel"],
        id_field="model_metric_id",
        expected_ids=[spec["model_metric_id"] for spec in metric_specs],
        label="model_level_panel",
    )
    for spec, row in zip(metric_specs, model_rows, strict=True):
        _require_exact_keys(
            row,
            _MODEL_PANEL_KEYS,
            f"model panel {spec['model_metric_id']!r}",
        )
        if row["unit"] != spec["unit"]:
            raise AnchorContextValidationError(
                f"model panel {spec['model_metric_id']!r} unit changed"
            )
        _validate_year_rows(
            row["annual_rows"],
            expected_keys=_MODEL_ROW_KEYS,
            label=f"model panel {spec['model_metric_id']!r}",
            numeric_fields=("mean", "sample_sd"),
            nonnegative_fields=("sample_sd",),
        )


def _assert_result_values(
    actual: Any,
    expected: Any,
    *,
    path: str,
) -> None:
    if isinstance(expected, Mapping):
        if not isinstance(actual, Mapping) or frozenset(actual) != frozenset(
            expected
        ):
            raise AnchorContextValidationError(
                f"{path} differs from recomputed results"
            )
        for key, expected_value in expected.items():
            _assert_result_values(
                actual[key],
                expected_value,
                path=f"{path}.{key}",
            )
        return
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise AnchorContextValidationError(
                f"{path} differs from recomputed results"
            )
        for index, (actual_value, expected_value) in enumerate(
            zip(actual, expected, strict=True)
        ):
            _assert_result_values(
                actual_value,
                expected_value,
                path=f"{path}[{index}]",
            )
        return
    if (
        isinstance(expected, (int, float))
        and not isinstance(expected, bool)
        and isinstance(actual, (int, float))
        and not isinstance(actual, bool)
    ):
        if not math.isfinite(actual) or actual != expected:
            raise AnchorContextValidationError(
                f"{path} differs from recomputed value"
            )
        return
    if type(actual) is not type(expected) or actual != expected:
        raise AnchorContextValidationError(
            f"{path} differs from recomputed result"
        )


def _result_validation_protocol(
    authorize_documents: Callable[
        ..., tuple[Mapping[str, Any], Mapping[str, Any]]
    ],
    build_results_impl: Callable[..., dict[str, Any]],
):
    def validate(
        results: Mapping[str, Any],
        *,
        input_bundle: object,
        ceremony_capability: object | None = None,
    ) -> None:
        """Validate schema, coverage, and independently recomputed rows."""
        supplied = _require_mapping(results, "results")
        _validate_results_structure(supplied)
        expected = build_results_impl(
            input_bundle,
            ceremony_capability=ceremony_capability,
        )
        _assert_result_values(supplied, expected, path="results")

    def validate_results(
        results: Mapping[str, Any],
        *,
        fixture_inputs: object,
    ) -> None:
        """Validate results only against the fixed nonproduction bundle."""
        validate(
            results,
            input_bundle=fixture_inputs,
        )

    def validate_production_results(
        ceremony_capability: object,
        results: Mapping[str, Any],
        verified_inputs: object,
    ) -> None:
        """Validate production results through the same live capability."""
        authorize_documents(
            verified_inputs,
            ceremony_capability=ceremony_capability,
        )
        validate(
            results,
            input_bundle=verified_inputs,
            ceremony_capability=ceremony_capability,
        )

    validate.__name__ = "_validate_results"
    validate.__qualname__ = "_validate_results"
    validate_production_results.__name__ = "_validate_production_results"
    validate_production_results.__qualname__ = "_validate_production_results"
    return validate, validate_results, validate_production_results


(
    _validate_results,
    validate_results,
    _validate_production_results,
) = _result_validation_protocol(
    _authorized_documents,
    _build_results,
)
del _result_validation_protocol


def copy_results(results: Mapping[str, Any]) -> dict[str, Any]:
    """Return a detached JSON copy after validating finite JSON encoding."""
    value = copy.deepcopy(dict(results))
    _validate_results_structure(value)
    return value


def _seal_document_authority_import() -> None:
    """Do not expose an unclaimed verifier-binding surface after import."""
    if _document_authority_is_bound():
        return
    publication_name = "populace_dynamics.estimates.anchor_context_publication"
    publication_source = (
        Path(__file__).with_name("anchor_context_publication.py").resolve()
    )
    publication_code = compile(
        publication_source.read_bytes(),
        str(publication_source),
        "exec",
        dont_inherit=True,
        optimize=sys.flags.optimize,
    )
    importlib.import_module(publication_name)
    if _document_authority_is_bound():
        return
    frame = sys._getframe(1)
    while frame is not None:
        module = sys.modules.get(publication_name)
        spec = getattr(module, "__spec__", None)
        origin = getattr(spec, "origin", None)
        try:
            origin_path = Path(origin).resolve()
            code_path = Path(frame.f_code.co_filename).resolve()
        except (OSError, TypeError, ValueError):
            origin_path = None
            code_path = None
        if (
            module is not None
            and vars(module) is frame.f_globals
            and frame.f_code == publication_code
            and frame.f_globals.get("__name__") == publication_name
            and origin_path == publication_source
            and code_path == publication_source
            and getattr(spec, "_initializing", False) is True
        ):
            return
        frame = frame.f_back
    raise RuntimeError(
        "report authority requires the canonical publication import"
    )


_seal_document_authority_import()
del _seal_document_authority_import


__all__ = [
    "AnchorContextValidationError",
    "EVIDENCE_LABELS",
    "build_results",
    "copy_results",
    "extract_model_metrics",
    "extract_official_values",
    "validate_results",
]
