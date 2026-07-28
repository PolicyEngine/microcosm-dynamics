"""Fixture-only tests for the frozen anchor-context comparison engine."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import statistics
from numbers import Real
from pathlib import Path
from typing import Any

import pytest

from populace_dynamics.estimates import (
    anchor_context_publication as publication,
)
from populace_dynamics.estimates import anchor_context_registry as registry
from populace_dynamics.estimates import anchor_context_report as report

REPOSITORY_ROOT = Path(__file__).parents[2]
FIXTURE_ROOT = Path(__file__).parents[1] / "fixtures" / "anchor_context"
FIRST_ESTIMATES_FIXTURE = FIXTURE_ROOT / "first_estimates_fixture_v1.json"
ANCHOR_FIXTURE = FIXTURE_ROOT / "ssa_level_anchors_fixture_v1.json"
YEARS = tuple(range(2015, 2023))
DRAW_YEAR_KEYS = tuple(
    (draw_index, year) for draw_index in range(20) for year in YEARS
)
INDEPENDENT_AVAILABLE_COMPARISON_IDS = (
    "cmp_reported_taxable_earnings_per_worker",
    "cmp_adjusted_taxable_payroll_per_covered_worker",
    "cmp_gross_contributions_per_worker",
    "cmp_net_payroll_tax_contributions_per_covered_worker",
    "cmp_retired_worker_beneficiaries_per_worker",
    "cmp_retired_worker_awards_per_worker",
    "cmp_retired_worker_benefits_per_reported_taxable_earnings",
)


@pytest.fixture(scope="module")
def fixture_inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    first_estimates = json.loads(
        FIRST_ESTIMATES_FIXTURE.read_text(encoding="utf-8")
    )
    anchors = json.loads(ANCHOR_FIXTURE.read_text(encoding="utf-8"))
    assert first_estimates["fixture_only"] is True
    assert anchors["fixture_only"] is True
    return first_estimates, anchors


@pytest.fixture(scope="module")
def fixture_bundle():
    return publication.load_fixture_documents(REPOSITORY_ROOT)


@pytest.fixture(scope="module")
def fixture_results(
    fixture_bundle,
) -> dict[str, Any]:
    return report.build_results(fixture_bundle)


def _resolve_pointer(document: Any, pointer: str) -> Any:
    value = document
    assert pointer.startswith("/")
    for raw_token in pointer.removeprefix("/").split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        value = value[token]
    return value


def _raw_model_rows(
    first_estimates: dict[str, Any],
) -> tuple[
    dict[tuple[int, int], dict[str, Any]],
    dict[tuple[int, int], dict[str, Any]],
    dict[tuple[int, int], dict[str, Any]],
]:
    tables = first_estimates["tables"]
    return tuple(
        {
            (row["draw_index"], row["year"]): row
            for row in tables[table_name]["per_draw"]
        }
        for table_name in ("modeled_award_flow", "opening_stock", "revenue")
    )


def _raw_official_value(
    anchors: dict[str, Any],
    series_id: str,
    year: int,
) -> float:
    determination = anchors["determinations"][series_id]
    observation = next(
        row for row in determination["observations"] if row["year"] == year
    )
    return float(observation["as_published"]) * float(
        observation["scale_multiplier"]
    )


def _mean_and_sample_sd(values: list[float]) -> tuple[float, float]:
    return statistics.fmean(values), statistics.stdev(values)


def _bundle_from_documents(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    first_estimates: dict[str, Any],
    anchors: dict[str, Any],
):
    root = tmp_path / "fixture-root"
    first_raw = publication.canonical_json_bytes(first_estimates)
    anchor_raw = publication.canonical_json_bytes(anchors)
    monkeypatch.setattr(
        publication,
        "_FIXTURE_FIRST_SHA256",
        hashlib.sha256(first_raw).hexdigest(),
    )
    monkeypatch.setattr(
        publication,
        "_FIXTURE_ANCHOR_SHA256",
        hashlib.sha256(anchor_raw).hexdigest(),
    )
    for relative, payload in (
        (publication._FIXTURE_FIRST_PATH, first_raw),
        (publication._FIXTURE_ANCHOR_PATH, anchor_raw),
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return publication.load_fixture_documents(root)


def _independent_statistics(
    comparison_id: str,
    first_estimates: dict[str, Any],
    anchors: dict[str, Any],
    year: int,
) -> tuple[list[float], float, list[float]]:
    flow, stock, revenue = _raw_model_rows(first_estimates)
    model_values = []

    for draw_index in range(20):
        key = (draw_index, year)
        if comparison_id in {
            "cmp_reported_taxable_earnings_per_worker",
            "cmp_adjusted_taxable_payroll_per_covered_worker",
        }:
            model_value = (
                revenue[key]["weighted_taxable_payroll"]
                / revenue[key]["weighted_covered_earner_count"]
            )
        elif comparison_id in {
            "cmp_gross_contributions_per_worker",
            "cmp_net_payroll_tax_contributions_per_covered_worker",
        }:
            model_value = (
                revenue[key]["combined_contributions"]
                / revenue[key]["weighted_covered_earner_count"]
            )
        elif comparison_id == ("cmp_retired_worker_beneficiaries_per_worker"):
            combined_beneficiaries = (
                flow[key]["weighted_beneficiary_count"]
                + stock[key]["weighted_beneficiary_count"]
            )
            model_value = (
                combined_beneficiaries
                / revenue[key]["weighted_covered_earner_count"]
            )
        elif comparison_id == "cmp_retired_worker_awards_per_worker":
            model_value = (
                flow[key]["weighted_award_count"]
                / revenue[key]["weighted_covered_earner_count"]
            )
        elif comparison_id == (
            "cmp_retired_worker_benefits_per_reported_taxable_earnings"
        ):
            combined_benefits = (
                flow[key]["frame_annualized_benefit"]
                + stock[key]["frame_annualized_benefit"]
            )
            model_value = (
                combined_benefits / revenue[key]["weighted_taxable_payroll"]
            )
        else:  # pragma: no cover - the parametrization is a closed registry
            raise AssertionError(f"unknown independent spec {comparison_id}")
        model_values.append(float(model_value))

    official_series = {
        "cmp_reported_taxable_earnings_per_worker": (
            "oasdi_reported_taxable_earnings",
            "oasdi_workers_with_taxable_earnings",
        ),
        "cmp_adjusted_taxable_payroll_per_covered_worker": (
            "oasdi_adjusted_taxable_payroll",
            "oasdi_covered_workers",
        ),
        "cmp_gross_contributions_per_worker": (
            "oasdi_gross_contributions",
            "oasdi_workers_with_taxable_earnings",
        ),
        "cmp_net_payroll_tax_contributions_per_covered_worker": (
            "oasdi_net_payroll_tax_contributions",
            "oasdi_covered_workers",
        ),
        "cmp_retired_worker_beneficiaries_per_worker": (
            "retired_worker_december_current_payment_stock",
            "oasdi_workers_with_taxable_earnings",
        ),
        "cmp_retired_worker_awards_per_worker": (
            "retired_worker_awards",
            "oasdi_workers_with_taxable_earnings",
        ),
        "cmp_retired_worker_benefits_per_reported_taxable_earnings": (
            "retired_worker_benefits_paid_estimated_allocation",
            "oasdi_reported_taxable_earnings",
        ),
    }
    try:
        official_numerator, official_denominator = official_series[
            comparison_id
        ]
    except KeyError as error:  # pragma: no cover - closed independent tuple
        raise AssertionError(
            f"unknown independent official spec {comparison_id}"
        ) from error
    official_value = _raw_official_value(
        anchors,
        official_numerator,
        year,
    ) / _raw_official_value(
        anchors,
        official_denominator,
        year,
    )

    comparisons = [value / official_value for value in model_values]
    return model_values, official_value, comparisons


def test_fixture_builds_exact_complete_results_shape(
    fixture_bundle,
    fixture_results: dict[str, Any],
):
    specs = registry.comparison_specs()

    assert set(fixture_results) == {
        "comparison_results",
        "official_anchor_level_panel",
        "model_level_panel",
    }
    comparison_results = fixture_results["comparison_results"]
    assert len(specs) == 9
    assert [row["comparison_id"] for row in comparison_results] == [
        spec["comparison_id"] for spec in specs
    ]

    available = [row for row in comparison_results if row["evaluated"]]
    unavailable = [row for row in comparison_results if not row["evaluated"]]
    assert len(available) == 7
    assert sum(len(row["annual_rows"]) for row in available) == 56
    assert len(unavailable) == 2
    assert all(
        set(row)
        == {
            "comparison_id",
            "availability",
            "evaluated",
            "annual_rows",
        }
        for row in available
    )
    assert all(
        set(annual)
        == {
            "year",
            "model_statistic_mean",
            "model_statistic_sample_sd",
            "official_statistic",
            "comparison_mean",
            "comparison_sample_sd",
        }
        for row in available
        for annual in row["annual_rows"]
    )
    assert all(
        set(row) == {"comparison_id", "availability", "evaluated", "reason"}
        for row in unavailable
    )

    official_panel = fixture_results["official_anchor_level_panel"]
    model_panel = fixture_results["model_level_panel"]
    assert len(official_panel) == 15
    assert len(model_panel) == 7
    assert [row["series_id"] for row in official_panel] == list(
        registry.required_series_ids()
    )
    assert [row["model_metric_id"] for row in model_panel] == [
        spec["model_metric_id"] for spec in registry.model_metric_specs()
    ]
    assert all(
        [annual["year"] for annual in row["annual_rows"]] == list(YEARS)
        for row in (*official_panel, *model_panel)
    )
    assert sum(len(row["annual_rows"]) for row in official_panel) == 120
    assert sum(len(row["annual_rows"]) for row in model_panel) == 56
    assert all(
        set(row) == {"series_id", "stored_unit", "annual_rows"}
        and all(
            set(annual) == {"year", "value"} for annual in row["annual_rows"]
        )
        for row in official_panel
    )
    assert all(
        set(row) == {"model_metric_id", "unit", "annual_rows"}
        and all(
            set(annual) == {"year", "mean", "sample_sd"}
            for annual in row["annual_rows"]
        )
        for row in model_panel
    )

    report.validate_results(
        fixture_results,
        fixture_inputs=fixture_bundle,
    )


def test_all_nine_model_operands_resolve_to_the_exact_draw_year_grid(
    fixture_inputs: tuple[dict[str, Any], dict[str, Any]],
    fixture_bundle,
):
    first_estimates, _ = fixture_inputs
    specs = registry.model_metric_specs()
    extracted = report.extract_model_metrics(fixture_bundle)
    operand_count = 0

    assert list(extracted) == [spec["model_metric_id"] for spec in specs]
    for spec in specs:
        assert list(extracted[spec["model_metric_id"]]) == list(DRAW_YEAR_KEYS)
        operand_grids = []
        for operand in spec["operands"]:
            operand_count += 1
            rows = _resolve_pointer(first_estimates, operand["row_pointer"])
            table_pointer = operand["row_pointer"].removesuffix("/per_draw")
            table = _resolve_pointer(first_estimates, table_pointer)
            assert table["unit_label"] == operand["required_table_unit_label"]
            keys = [
                tuple(row[field] for field in operand["key_fields"])
                for row in rows
            ]
            assert keys == list(DRAW_YEAR_KEYS)
            assert len(keys) == len(set(keys)) == 160
            for row in rows:
                assert all(
                    row[key] == value
                    for key, value in operand["required_row_values"].items()
                )
                selected = row[operand["value_field"]]
                assert (
                    isinstance(selected, Real)
                    and not isinstance(selected, bool)
                    and math.isfinite(selected)
                )
            operand_grids.append(keys)
        assert all(grid == operand_grids[0] for grid in operand_grids)

    assert operand_count == 9


def test_official_extraction_is_exact_complete_and_normalized(
    fixture_inputs: tuple[dict[str, Any], dict[str, Any]],
    fixture_bundle,
):
    _, anchors = fixture_inputs
    extracted = report.extract_official_values(fixture_bundle)

    assert list(extracted) == list(registry.required_series_ids())
    for series_id in registry.required_series_ids():
        assert list(extracted[series_id]) == list(YEARS)
        for year in YEARS:
            assert extracted[series_id][year] == _raw_official_value(
                anchors,
                series_id,
                year,
            )


def test_independent_formula_oracle_covers_every_available_comparison():
    available = tuple(
        spec["comparison_id"]
        for spec in registry.comparison_specs()
        if spec["availability"]["status"] == "available"
    )

    assert len(INDEPENDENT_AVAILABLE_COMPARISON_IDS) == 7
    assert INDEPENDENT_AVAILABLE_COMPARISON_IDS == available


@pytest.mark.parametrize(
    "comparison_id",
    INDEPENDENT_AVAILABLE_COMPARISON_IDS,
)
def test_registered_formula_matches_independent_per_draw_recomputation(
    comparison_id: str,
    fixture_inputs: tuple[dict[str, Any], dict[str, Any]],
    fixture_results: dict[str, Any],
):
    first_estimates, anchors = fixture_inputs
    published = next(
        row
        for row in fixture_results["comparison_results"]
        if row["comparison_id"] == comparison_id
    )

    assert published["availability"] == "available"
    assert published["evaluated"] is True
    assert len(published["annual_rows"]) == len(YEARS) == 8
    for annual_row in published["annual_rows"]:
        model, official, comparison = _independent_statistics(
            comparison_id,
            first_estimates,
            anchors,
            annual_row["year"],
        )
        assert len(model) == len(comparison) == 20
        model_mean, model_sd = _mean_and_sample_sd(model)
        comparison_mean, comparison_sd = _mean_and_sample_sd(comparison)
        assert annual_row["model_statistic_mean"] == pytest.approx(model_mean)
        assert annual_row["model_statistic_sample_sd"] == pytest.approx(
            model_sd
        )
        assert annual_row["official_statistic"] == pytest.approx(official)
        assert annual_row["comparison_mean"] == pytest.approx(comparison_mean)
        assert annual_row["comparison_sample_sd"] == pytest.approx(
            comparison_sd
        )


@pytest.mark.parametrize(
    "mutation",
    ["missing", "duplicate", "reordered", "extra"],
)
def test_model_input_grid_forgery_aborts(
    mutation: str,
    fixture_inputs: tuple[dict[str, Any], dict[str, Any]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    first_estimates, anchors = fixture_inputs
    mutant = copy.deepcopy(first_estimates)
    rows = mutant["tables"]["modeled_award_flow"]["per_draw"]

    if mutation == "missing":
        rows.pop()
    elif mutation == "duplicate":
        rows[-1] = copy.deepcopy(rows[0])
    elif mutation == "reordered":
        rows[0], rows[1] = rows[1], rows[0]
    else:
        extra = copy.deepcopy(rows[-1])
        extra["year"] = 2023
        rows.append(extra)

    with pytest.raises((TypeError, ValueError)):
        report.extract_model_metrics(
            _bundle_from_documents(
                tmp_path,
                monkeypatch,
                mutant,
                anchors,
            )
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_year",
        "duplicate_year",
        "reordered_year",
        "extra_series",
        "reordered_series",
    ],
)
def test_anchor_input_grid_or_registry_forgery_aborts(
    mutation: str,
    fixture_inputs: tuple[dict[str, Any], dict[str, Any]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    first_estimates, anchors = fixture_inputs
    mutant = copy.deepcopy(anchors)
    first_id = mutant["required_series_ids"][0]
    observations = mutant["determinations"][first_id]["observations"]

    if mutation == "missing_year":
        observations.pop()
    elif mutation == "duplicate_year":
        observations[-1] = copy.deepcopy(observations[0])
    elif mutation == "reordered_year":
        observations[0], observations[1] = (
            observations[1],
            observations[0],
        )
    elif mutation == "extra_series":
        extra_id = "fixture_only_extra_series"
        extra = copy.deepcopy(mutant["determinations"][first_id])
        extra["series_id"] = extra_id
        mutant["required_series_ids"].append(extra_id)
        mutant["determinations"][extra_id] = extra
    else:
        required = mutant["required_series_ids"]
        required[0], required[1] = required[1], required[0]

    with pytest.raises((TypeError, ValueError)):
        report.extract_official_values(
            _bundle_from_documents(
                tmp_path,
                monkeypatch,
                first_estimates,
                mutant,
            )
        )


@pytest.mark.parametrize(
    "mutation",
    ["omission", "reordering", "extra_spec", "wrong_value"],
)
def test_results_forgery_aborts(
    mutation: str,
    fixture_bundle,
    fixture_results: dict[str, Any],
):
    mutant = copy.deepcopy(fixture_results)
    comparisons = mutant["comparison_results"]

    if mutation == "omission":
        comparisons.pop()
    elif mutation == "reordering":
        comparisons[0], comparisons[1] = comparisons[1], comparisons[0]
    elif mutation == "extra_spec":
        extra = copy.deepcopy(comparisons[-1])
        extra["comparison_id"] = "fixture_only_extra_comparison"
        comparisons.append(extra)
    else:
        evaluated = next(row for row in comparisons if row["evaluated"])
        evaluated["annual_rows"][0]["comparison_mean"] += 1.0

    with pytest.raises((TypeError, ValueError)):
        report.validate_results(
            mutant,
            fixture_inputs=fixture_bundle,
        )


def test_wrong_ordered_mismatch_array_fails_registry_validation():
    registry.validate_frozen_registries(
        required_series_ids=registry.required_series_ids(),
        model_metric_specs=registry.model_metric_specs(),
        pairings=registry.pairings(),
        comparison_specs=registry.comparison_specs(),
    )
    wrong_pairings = registry.pairings()
    wrong_pairings[0]["mismatch_codes"].reverse()

    with pytest.raises((TypeError, ValueError)):
        registry.validate_frozen_registries(
            required_series_ids=registry.required_series_ids(),
            model_metric_specs=registry.model_metric_specs(),
            pairings=wrong_pairings,
            comparison_specs=registry.comparison_specs(),
        )


def test_oasi_cash_series_is_complete_level_only_and_mandatory(
    fixture_bundle,
    fixture_results: dict[str, Any],
):
    series_id = "oasi_net_payroll_tax_contributions"
    official = report.extract_official_values(fixture_bundle)[series_id]
    panel = next(
        row
        for row in fixture_results["official_anchor_level_panel"]
        if row["series_id"] == series_id
    )

    assert [row["year"] for row in panel["annual_rows"]] == list(YEARS)
    assert [row["value"] for row in panel["annual_rows"]] == [
        official[year] for year in YEARS
    ]
    assert series_id not in {
        row["anchor_series_id"] for row in registry.pairings()
    }
    assert series_id not in {
        spec[field]
        for spec in registry.comparison_specs()
        for field in (
            "official_numerator_series_id",
            "official_denominator_series_id",
        )
    }

    mutant = copy.deepcopy(fixture_results)
    mutant["official_anchor_level_panel"].remove(
        next(
            row
            for row in mutant["official_anchor_level_panel"]
            if row["series_id"] == series_id
        )
    )
    with pytest.raises((TypeError, ValueError)):
        report.validate_results(
            mutant,
            fixture_inputs=fixture_bundle,
        )
