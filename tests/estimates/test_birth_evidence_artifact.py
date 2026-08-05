"""Byte, arithmetic, and cheap replay pins for the birth-evidence artifact.

The replay tests exercise only a tiny synthetic production boundary.  They do
not load the diagnostic cache or recompute the projection.
"""

from __future__ import annotations

import ast
import hashlib
import json
from collections import Counter
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd
import pytest

from populace_dynamics.engine.loop import ProjectionResult
from populace_dynamics.estimates import career, preparation
from populace_dynamics.estimates.publication import (
    COMMON_SUPPORT_AGREEMENT,
    GAP_BLOCK,
)
from populace_dynamics.estimates.runner import (
    DRAW_ROOT_SEEDS,
    FirstReportProjectionDraw,
)
from scripts import first_estimates_birth_evidence as reducer
from tests.estimates.test_first_estimates_fixture import (
    _fixture as _pipeline_fixture,
)
from tests.estimates.test_first_estimates_fixture import (
    _observed as _pipeline_observed,
)
from tests.estimates.test_first_estimates_fixture import (
    _parameters as _pipeline_parameters,
)
from tests.estimates.test_first_estimates_fixture import (
    _schedule as _pipeline_schedule,
)
from tests.estimates.test_first_estimates_fixture import (
    _trajectory as _pipeline_trajectory,
)
from tests.estimates.test_preparation import _full_actual_parameters

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_PATH = ROOT / "runs" / "first_estimates_birth_evidence_draw0.json"
ARTIFACT_SHA256 = (
    "92c6319bdeb2b02681a7c6ab700fc8df47b43de703054450040dba053ac309a5"
)
CACHE_SHA256 = (
    "3ba147f7666ad77d8f7735969e4329fa7180cef091ad4ee326f35b2834a72068"
)


def _artifact() -> dict[str, Any]:
    return json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))


def test_reducer_input_identity_matches_reviewed_branch():
    reducer._assert_input_identity()


def test_context_report_sources_are_outside_historical_reducer_identity():
    assert reducer.POST_REVIEW_SOURCE_EXCLUSIONS == (
        Path("src/populace_dynamics/artifacts.py"),
        Path("src/populace_dynamics/data/psid_codebook_extraction.py"),
        Path("src/populace_dynamics/data/psid_covered_earnings_registry.py"),
        Path("src/populace_dynamics/data/psid_job_context.py"),
        Path("src/populace_dynamics/data/psid_job_context_registry.py"),
        Path("src/populace_dynamics/data/psid_missing_reason_authority.py"),
        Path("src/populace_dynamics/data/psid_questionnaire_inventory.py"),
        Path("src/populace_dynamics/data/psid_unit_authority.py"),
        Path("src/populace_dynamics/data/psid_unit_predicate_authority.py"),
        Path("src/populace_dynamics/data/psid_unit_title_authority.py"),
        Path(
            "src/populace_dynamics/data/historical_coverage_rule_validation.py"
        ),
        Path("src/populace_dynamics/estimates/anchor_context_coordinator.py"),
        Path("src/populace_dynamics/estimates/anchor_context_publication.py"),
        Path("src/populace_dynamics/estimates/anchor_context_registry.py"),
        Path("src/populace_dynamics/estimates/anchor_context_rehearsal.py"),
        Path("src/populace_dynamics/estimates/anchor_context_report.py"),
    )
    assert reducer.POST_REVIEW_SHARED_SOURCE_BLOBS == {
        Path(
            "src/populace_dynamics/artifacts.py"
        ): "c03afa29cbdaf722c2cf62608dbb01f061f6558d"
    }


def _repository_module_paths() -> dict[str, Path]:
    modules: dict[str, Path] = {}
    for source_root, prefix in (
        (ROOT / "src", ()),
        (ROOT / "scripts", ("scripts",)),
    ):
        for path in source_root.rglob("*.py"):
            relative = path.relative_to(source_root).with_suffix("")
            parts = (*prefix, *relative.parts)
            if parts[-1] == "__init__":
                parts = parts[:-1]
            if parts:
                modules[".".join(parts)] = path
    return modules


def _internal_imports(
    module_name: str,
    path: Path,
    module_paths: dict[str, Path],
) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    is_package = path.name == "__init__.py"
    module_parts = module_name.split(".")
    package_parts = module_parts if is_package else module_parts[:-1]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(
                alias.name
                for alias in node.names
                if alias.name in module_paths
            )
            continue
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.level:
            keep = len(package_parts) - node.level + 1
            if keep < 0:
                continue
            base_parts = package_parts[:keep]
            if node.module:
                base_parts.extend(node.module.split("."))
            base = ".".join(base_parts)
        else:
            base = node.module or ""
        if base in module_paths:
            imports.add(base)
        for alias in node.names:
            candidate = f"{base}.{alias.name}" if base else alias.name
            if candidate in module_paths:
                imports.add(candidate)
    return imports


def test_psid_identity_exclusions_are_unreachable_from_birth_evidence():
    module_paths = _repository_module_paths()
    root_module = "scripts.first_estimates_birth_evidence"
    psid_exclusions = {
        "populace_dynamics.data.psid_codebook_extraction",
        "populace_dynamics.data.psid_covered_earnings_registry",
        "populace_dynamics.data.psid_job_context",
        "populace_dynamics.data.psid_job_context_registry",
        "populace_dynamics.data.psid_missing_reason_authority",
        "populace_dynamics.data.psid_questionnaire_inventory",
    }
    assert root_module in module_paths
    assert psid_exclusions.issubset(module_paths)
    module_by_path = {
        path.resolve(): module_name
        for module_name, path in module_paths.items()
    }
    dynamic_identity_roots = {
        module_by_path[(ROOT / path).resolve()]
        for path in reducer.PRODUCTION_SOURCE_PATHS
        if (ROOT / path).is_file()
    }
    assert {
        "scripts.registered_m6_candidate3_inputs",
        "scripts.registered_m6_candidate2_inputs",
        "scripts.registered_m6_inputs",
    }.issubset(dynamic_identity_roots)

    reachable: set[str] = set()
    pending = [root_module, *sorted(dynamic_identity_roots)]
    while pending:
        module_name = pending.pop()
        if module_name in reachable:
            continue
        reachable.add(module_name)
        pending.extend(
            _internal_imports(
                module_name,
                module_paths[module_name],
                module_paths,
            )
            - reachable
        )

    assert psid_exclusions.isdisjoint(reachable), (
        "historically excluded PSID modules became reachable from the "
        f"birth-evidence reducer: {sorted(psid_exclusions & reachable)}"
    )


def test_reducer_accepts_explicit_unresolved_upstream_boundary():
    records = (
        career.BirthYearRecord(
            1,
            1950,
            career.BirthSource.EXACT_MARRIAGE,
        ),
        career.BirthYearRecord(
            2,
            None,
            career.BirthSource.UNRESOLVED,
        ),
    )

    years, sources, unresolved = reducer._split_upstream_birth_records(
        records,
        {1, 2, 3},
    )

    assert years == {1: 1950}
    assert sources == {1: "exact_marriage"}
    assert unresolved == frozenset({2, 3})


def test_replay_adapter_matches_frozen_birth_source_rows():
    frozen_rows = {
        "derived_projection_age": 4_077,
        "unresolved": 2_315,
    }
    artifact_rows = _artifact()["birth_source_law"]["initially_unresolved"][
        "corrected_counts_by_class"
    ]
    assert {key: artifact_rows[key] for key in frozen_rows} == frozen_rows

    person_ids = list(range(1, 6_393))
    seed = pd.DataFrame(
        {
            "person_id": person_ids,
            "year": [2014] * 6_392,
            "anchor_wave": [2015] * 6_392,
            "age": [2] * 4_077 + [1] * 2_298 + [999] * 17,
        }
    )
    records = career.derive_birth_years(
        pd.DataFrame(columns=["person_id", "birth_year"]),
        pd.DataFrame(columns=["person_id", "period", "age"]),
        seed_coordinates=seed,
        required_person_ids=person_ids,
    )
    observed_rows = Counter(record.source.value for record in records)

    assert dict(observed_rows) == frozen_rows


def test_replay_mode_runs_production_preparation_for_frozen_row_subset(
    monkeypatch,
):
    document = _pipeline_fixture()
    trajectory = _pipeline_trajectory(document)
    initial = pd.DataFrame(document["initial_population"])
    initial["anchor_wave"] = 2015
    age_at_start = trajectory.loc[trajectory["year"] == 2014].set_index(
        "person_id"
    )["age"]
    initial["age"] = initial["person_id"].map(age_at_start)

    marriage = pd.DataFrame(document["marriage_history"])
    marriage_births = marriage.set_index("person_id")["birth_year"]
    scheduled = {}
    for anchor_wave, rows in document["scheduled_entries_by_year"].items():
        frame = pd.DataFrame(rows)
        frame["anchor_wave"] = int(anchor_wave)
        frame["age"] = frame["year"] - frame["person_id"].map(marriage_births)
        scheduled[int(anchor_wave)] = frame

    holdout_ids = frozenset(
        int(value)
        for value in (
            *initial["person_id"],
            *(
                person_id
                for frame in scheduled.values()
                for person_id in frame["person_id"]
            ),
        )
    )
    synthetic_ids = {
        int(person_id) for person_id in document["synthetic_birth_years"]
    }
    population = SimpleNamespace(
        initial_slice=initial,
        scheduled_entries_by_year=scheduled,
        holdout_ids=holdout_ids,
        reserved_real_ids=holdout_ids - synthetic_ids,
        earnings_domain_ids=frozenset(document["earnings_domain_ids"]),
    )
    projection = ProjectionResult(
        slices=tuple(
            trajectory.loc[trajectory["year"] == year].copy()
            for year in range(2014, 2023)
        ),
        traces=(),
        draw_index=0,
    )
    draw = FirstReportProjectionDraw(
        draw_index=0,
        root_seed=DRAW_ROOT_SEEDS[0],
        projection=projection,
        collector={},
    )
    inputs = SimpleNamespace(
        earnings_panel=_pipeline_observed(document),
        refit_inputs=SimpleNamespace(
            claiming_reference=object(),
            family_context=SimpleNamespace(marriage_records=marriage),
        ),
    )
    loaded = reducer.LoadedDraw(
        inputs=inputs,
        phase=SimpleNamespace(population=population),
        draw=draw,
        execution={},
    )
    parameters = replace(
        _pipeline_parameters(document),
        provenance=_full_actual_parameters().provenance,
    )
    frozen_rows = {
        "birth_source.derived_projection_age": 0,
        "birth_source.unresolved": 0,
        "candidate_funnel.canonical_candidates": 8,
        "inclusion.baseline": 3,
        "inclusion.birth_minus_1": 2,
        "inclusion.birth_plus_1": 3,
    }
    preparation_calls = []
    production_prepare = preparation._prepare_first_report_draw_for_test

    def prepare(batch, replay_draw, *, parameters):
        preparation_calls.append((replay_draw, parameters))
        return production_prepare(
            batch,
            replay_draw,
            parameters=parameters,
        )

    monkeypatch.setattr(
        preparation,
        "reconstruct_claiming_schedule",
        lambda _inputs: _pipeline_schedule(document),
    )
    monkeypatch.setattr(
        preparation,
        "_prepare_first_report_draw_for_test",
        prepare,
    )
    monkeypatch.setattr(
        reducer,
        "_artifact_implementation_replay_rows",
        lambda: frozen_rows,
    )
    monkeypatch.setattr(reducer, "IMPLEMENTATION_REPLAY_ROWS", frozen_rows)

    replay = reducer._run_implementation_replay(loaded, parameters)

    assert preparation_calls == [(draw, parameters)]
    assert replay == {
        "draw_index": 0,
        "reviewed_implementation_commit": (
            reducer.REVIEWED_IMPLEMENTATION_COMMIT
        ),
        "rows": frozen_rows,
        "status": "matched",
    }


def test_revision_10_1_candidate_share_recomputes_from_artifact_counts():
    candidates = _artifact()["candidate_funnel"]["canonical_candidates"]
    by_source = candidates["counts_by_birth_source"]
    age_derived = (
        by_source["inferred_period_age"] + by_source["derived_projection_age"]
    )
    candidate_count = candidates["count"]
    share = age_derived / candidate_count

    assert (age_derived, candidate_count) == (2_892, 3_083)
    assert share == pytest.approx(0.938047356471)
    published = next(
        row["disclosure"]
        for row in GAP_BLOCK
        if row["disclosure"].startswith("**Birth-timing sensitivity")
    )
    assert (
        f"{age_derived:,} of {candidate_count:,} candidates ({share:.1%})"
        in published
    )


def test_birth_evidence_artifact_byte_schema_and_execution_pin():
    raw = ARTIFACT_PATH.read_bytes()
    artifact = json.loads(raw)
    canonical = (
        json.dumps(
            artifact,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode()

    assert raw == canonical
    assert hashlib.sha256(raw).hexdigest() == ARTIFACT_SHA256
    assert artifact["schema_version"] == "first_estimates_birth_evidence.v2"
    assert set(artifact) == {
        "benefit_ledger_sensitivity",
        "birth_source_law",
        "candidate_funnel",
        "common_support_agreement",
        "execution",
        "inclusion_sensitivity",
        "input_identity",
        "oracle_reconciliation",
        "revenue_person_year_evidence",
        "schema_version",
    }

    execution = artifact["execution"]
    assert execution["artifact_source"] == "sha256_pinned_diagnostic_pickle"
    assert execution["data_path"] == "diagnostic_pickle_cache"
    assert execution["cache"]["sha256"] == CACHE_SHA256
    assert execution["cache"]["size_bytes"] == 7_133_539_989
    assert execution["canonical_artifact_command"].endswith(
        execution["cache"]["path"]
    )
    assert execution["cache_independent_regeneration_command"].endswith(
        "--regenerate"
    )


def test_birth_evidence_artifact_count_tables_reconcile():
    artifact = _artifact()
    birth = artifact["birth_source_law"]
    whole = birth["whole_population"]
    unresolved = birth["initially_unresolved"]

    assert sum(whole["counts_by_class"].values()) == whole["count"] == 30_482
    assert (
        sum(unresolved["corrected_counts_by_class"].values())
        == unresolved["count"]
        == 6_392
    )
    assert sum(unresolved["age_code_counts"].values()) == unresolved["count"]
    assert birth["seed_coordinate"]["derived_birth_asserted_bounds"] == [
        1889,
        2016,
    ]
    assert birth["seed_coordinate"]["derived_birth_observed_range"] == [
        1914,
        2016,
    ]
    assert birth["seed_coordinate"]["derived_birth_per_row_assertion"] == {
        "asserted_rows": 4_077,
        "passed": True,
        "rule": "seed_year - 125 <= birth_year <= seed_year - 2",
    }

    candidate_count = artifact["candidate_funnel"]["canonical_candidates"][
        "count"
    ]
    sensitivity = artifact["inclusion_sensitivity"]
    coherent = artifact["benefit_ledger_sensitivity"][
        "coherent_shift_stress_scenarios"
    ]
    full_scenarios = coherent["full_scenario_ledger"]["scenarios"]
    expected_included = {
        "baseline": 1_514,
        "birth_minus_1": 1_520,
        "birth_plus_1": 1_240,
    }
    for name, scenario in sensitivity["scenarios"].items():
        counts = scenario["ordered_stage_d_counts"]
        by_source = scenario["ordered_stage_d_counts_by_birth_source"]
        assert sum(counts.values()) == candidate_count == 3_083
        for source_counts in by_source.values():
            assert sum(source_counts.values()) >= 0
        for outcome, count in counts.items():
            assert (
                sum(
                    source_counts[outcome]
                    for source_counts in by_source.values()
                )
                == count
            )
        assert counts["included"] == expected_included[name]
        assert (
            full_scenarios[name]["complete_included_set_count"]
            == counts["included"]
        )

    overall = sensitivity["overall_inclusion"]
    expected_flows = {
        "birth_minus_1": (16, 10),
        "birth_plus_1": (5, 279),
    }
    baseline_included = expected_included["baseline"]
    for name, (expected_inbound, expected_outbound) in expected_flows.items():
        direction = overall["directions"][name]
        changes = direction["neutral_inclusion_changes"]
        inbound = changes["inbound_to_included"]["count"]
        outbound = changes["outbound_from_included"]["count"]
        assert (inbound, outbound) == (
            expected_inbound,
            expected_outbound,
        )
        assert inbound + outbound == direction["inclusion_flip_count"]
        assert (
            baseline_included + inbound - outbound == expected_included[name]
        )
        ledger_changes = full_scenarios[name][
            "included_set_changes_from_baseline"
        ]
        assert ledger_changes["inbound_to_included"] == inbound
        assert ledger_changes["outbound_from_included"] == outbound
        assert ledger_changes["reconciled_count"] == expected_included[name]

    predicates = sensitivity["predicates"]
    for predicate in predicates.values():
        for direction in predicate["directions"].values():
            assert (
                sum(direction["flip_count_by_origin"].values())
                == direction["flip_count"]
            )
            assert (
                sum(
                    direction[
                        "inclusion_changing_flip_count_by_origin"
                    ].values()
                )
                == direction["inclusion_changing_flip_count"]
            )
            changes = direction["neutral_inclusion_changes"]
            assert (
                changes["inbound_to_included"]["count"]
                + changes["outbound_from_included"]["count"]
                == direction["inclusion_changing_flip_count"]
            )
    chronology = predicates["chronology"]
    assert (
        chronology["directions"]["birth_minus_1"]["neutral_inclusion_changes"][
            "inbound_to_included"
        ]["count"]
        == 16
    )
    assert (
        chronology["directions"]["birth_plus_1"]["neutral_inclusion_changes"][
            "outbound_from_included"
        ]["count"]
        == 278
    )
    assert chronology["origin_assertion"] == {
        "asserted_flip_directions": 600,
        "assertion": (
            "Every measured chronology predicate flip is modeled_award."
        ),
        "observed_counts_by_origin": {
            "modeled_award": 600,
            "opening_backfill": 0,
        },
        "passed": True,
    }
    assert (
        predicates["coverage"]["directions"]["birth_plus_1"][
            "neutral_inclusion_changes"
        ]["outbound_from_included"]["count"]
        == 1
    )

    fixed = coherent["fixed_clause2_cohort"]
    assert fixed["cohort"]["count"] == 1_440
    assert fixed["semantics"]["baseline_included_non_clause2_not_priced"] == 74
    assert fixed["cohort"]["count"] + 74 == baseline_included
    assert fixed["semantics"]["scenario_inbound_not_priced"] == {
        "birth_minus_1": 16,
        "birth_plus_1": 5,
    }
    for scenario in fixed["scenarios"].values():
        assert (
            scenario["retained_after_inclusion_rerun"]
            + scenario["excluded_after_inclusion_rerun"]
            == fixed["cohort"]["count"]
        )

    baseline_total = full_scenarios["baseline"][
        "weighted_annualized_benefit_total"
    ]["amount"]
    for scenario in full_scenarios.values():
        annual = scenario["weighted_annualized_benefit_by_year"]
        total = scenario["weighted_annualized_benefit_total"]
        assert total["amount"] == pytest.approx(
            sum(row["amount"] for row in annual.values()),
            abs=0.001,
        )
        assert total["delta_from_baseline"] == pytest.approx(
            total["amount"] - baseline_total,
            abs=0.001,
        )
        assert total["sum_of_per_year_deltas"] == pytest.approx(
            sum(row["delta_from_baseline"] for row in annual.values()),
            abs=0.001,
        )
        assert total["person_contribution_sum"] == pytest.approx(
            total["amount"],
            abs=0.001,
        )

    agreement = artifact["common_support_agreement"]
    production_copy = {
        key: value
        for key, value in COMMON_SUPPORT_AGREEMENT.items()
        if key not in {"evidence_reference", "interpretation"}
    }
    assert production_copy == agreement
    assert COMMON_SUPPORT_AGREEMENT["evidence_reference"] == {
        "path": "runs/first_estimates_birth_evidence_draw0.json",
        "sha256": ARTIFACT_SHA256,
        "schema_version": "first_estimates_birth_evidence.v2",
        "section": "common_support_agreement",
    }
    assert agreement["common_support_count"] == 4_518
    endpoint_expectations = {
        "exact": {
            "clause2": 2_307,
            "clause3": 2_299,
            "cells": (1_916, 391, 383, 1_828),
            "method": "chi_square_continuity_corrected",
            "p_value": 0.8013426797762091,
        },
        "within_plus_or_minus_1": {
            "clause2": 4_516,
            "clause3": 4_508,
            "cells": (4_507, 9, 1, 1),
            "method": "exact_two_sided_binomial",
            "p_value": 0.021484375,
        },
    }
    cell_keys = (
        "clause2_match__clause3_match",
        "clause2_match__clause3_mismatch",
        "clause2_mismatch__clause3_match",
        "clause2_mismatch__clause3_mismatch",
    )
    for name, expected in endpoint_expectations.items():
        table = agreement["endpoints"][name]
        cells = table["mcnemar_2x2_cells"]
        assert tuple(cells[key] for key in cell_keys) == expected["cells"]
        assert sum(cells.values()) == table["denominator"] == 4_518
        assert (
            cells[cell_keys[0]] + cells[cell_keys[1]]
            == table["clause2_inferred_period_age"]["match_count"]
            == expected["clause2"]
        )
        assert (
            cells[cell_keys[0]] + cells[cell_keys[2]]
            == table["clause3_seed_age"]["match_count"]
            == expected["clause3"]
        )
        assert table["discordant_pairs"] == {
            "clause2_only": cells[cell_keys[1]],
            "clause3_only": cells[cell_keys[2]],
        }
        reported = table["paired_tests"]["reported_test"]
        assert reported["method_key"] == expected["method"]
        assert reported["p_value"] == pytest.approx(expected["p_value"])

    anchor_expected = {
        "2015": (3_645, 1_908, 1_932),
        "2017": (601, 254, 215),
        "2019": (272, 145, 152),
    }
    anchor_tables = agreement["exact_endpoint_by_anchor_wave"]
    for wave, (
        denominator,
        clause2_count,
        clause3_count,
    ) in anchor_expected.items():
        table = anchor_tables[wave]
        cells = table["mcnemar_2x2_cells"]
        assert sum(cells.values()) == table["denominator"] == denominator
        assert (
            cells[cell_keys[0]] + cells[cell_keys[1]]
            == table["clause2_inferred_period_age"]["match_count"]
            == clause2_count
        )
        assert (
            cells[cell_keys[0]] + cells[cell_keys[2]]
            == table["clause3_seed_age"]["match_count"]
            == clause3_count
        )
    assert (
        sum(table["denominator"] for table in anchor_tables.values())
        == agreement["common_support_count"]
    )
    reported_2017 = anchor_tables["2017"]["paired_tests"]["reported_test"]
    assert reported_2017["method_key"] == "chi_square_continuity_corrected"
    assert reported_2017["p_value"] == pytest.approx(0.000046206995513884114)

    revenue = artifact["revenue_person_year_evidence"]
    assert revenue["groups"] == {
        "combined": {
            "in_window_rows": 43_044,
            "people": 6_392,
            "zero_earnings_rows": 43_044,
        },
        "derived_projection_age": {
            "in_window_rows": 28_978,
            "people": 4_077,
            "zero_earnings_rows": 28_978,
        },
        "unresolved": {
            "in_window_rows": 14_066,
            "people": 2_315,
            "zero_earnings_rows": 14_066,
        },
    }
    assert revenue["reconciliation"] == {
        "in_window_rows_sum": 28_978 + 14_066,
        "passed": True,
        "people_sum": 4_077 + 2_315,
        "zero_earnings_rows_sum": 28_978 + 14_066,
    }

    oracle = artifact["oracle_reconciliation"]
    assert oracle["matched_rows"] == len(oracle["rows"]) == 37
    assert all(
        row["match"] and row["ours"] == row["oracle"] for row in oracle["rows"]
    )
