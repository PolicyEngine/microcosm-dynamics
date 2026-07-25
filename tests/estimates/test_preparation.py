from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from types import SimpleNamespace

import pandas as pd
import pytest

import populace_dynamics.estimates.preparation as preparation
from populace_dynamics.engine.loop import ProjectionResult
from populace_dynamics.estimates import parameters as parameter_module
from populace_dynamics.estimates.career import BirthSource, DIClass
from populace_dynamics.estimates.first_report import FirstReportDrawBundle
from populace_dynamics.estimates.parameters import ReportParameters
from populace_dynamics.estimates.runner import (
    DRAW_INDICES,
    DRAW_ROOT_SEEDS,
    STOCK_IMPUTATION_ROOT_SEED,
    FirstReportProjectionBatch,
    FirstReportProjectionDraw,
)


class _PhaseWithForbiddenBundle:
    def __init__(self, population):
        self.population = population

    @property
    def bundle(self):  # pragma: no cover - access is the failure
        raise AssertionError("statutory preparation consulted phase.bundle")


def _canonical_sha256(values):
    encoded = (
        json.dumps(values, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _full_actual_parameters() -> ReportParameters:
    components = {
        "policyengine_us_consumed_files": (
            parameter_module.PE_US_CONSUMED_BUNDLE_SHA256
        ),
        "cola_file": parameter_module.COLA_FILE_SHA256,
        "cola_content": parameter_module.COLA_CONTENT_SHA256,
    }
    provenance = {
        "schema_version": "first_estimates.parameters.v1",
        "bundle_sha256": _canonical_sha256(components),
        "bundle_components": components,
        "policyengine_us": {
            "version": parameter_module.PINNED_PE_US_VERSION,
            "ssa_parameter_bundle_sha256": (
                parameter_module.SSA_PARAMETER_BUNDLE_SHA256
            ),
            "all_consumed_files_sha256": (
                parameter_module.PE_US_CONSUMED_BUNDLE_SHA256
            ),
        },
        "oasdi_rate_legs": {
            "bundle_sha256": parameter_module.RATE_LEG_BUNDLE_SHA256,
            "asserted_employee_rate": 0.062,
            "asserted_employer_rate": 0.062,
            "asserted_combined_rate": 0.124,
        },
        "cola": {
            "sha256": parameter_module.COLA_FILE_SHA256,
            "content_sha256": parameter_module.COLA_CONTENT_SHA256,
        },
    }
    return ReportParameters(
        ssa=object(),  # type: ignore[arg-type]
        rates=object(),  # type: ignore[arg-type]
        cola=object(),  # type: ignore[arg-type]
        provenance=provenance,
    )


def _projection(draw_index: int) -> ProjectionResult:
    slices = []
    for year in range(2014, 2023):
        records = [
            {
                "person_id": 1,
                "year": year,
                "age": 60 + (year - 2014),
                "sex": "female",
                "weight": 1.5,
                "earnings": 10_000.0,
                "claim_age": 62,
                "claim_year": 2016,
                "birth_year": 1954,
                "di_converted": False,
            }
        ]
        if year >= 2016:
            records.append(
                {
                    "person_id": 100,
                    "year": year,
                    "age": year - 2016,
                    "sex": "male",
                    "weight": 1.5,
                    "earnings": 0.0,
                    "claim_age": pd.NA,
                    "claim_year": pd.NA,
                    "birth_year": 2016,
                    "di_converted": False,
                }
            )
        slices.append(pd.DataFrame(records))
    return ProjectionResult(
        slices=tuple(slices),
        traces=(),
        draw_index=draw_index,
    )


def _batch() -> FirstReportProjectionBatch:
    initial = pd.DataFrame(
        {
            "person_id": [1],
            "year": [2014],
            "anchor_wave": [2015],
            "age": [60],
            "sex": ["female"],
            "weight": [1.5],
            "birth_year": [1954],
        }
    )
    scheduled = pd.DataFrame(
        {
            "person_id": [2],
            "year": [2016],
            "anchor_wave": [2017],
            "age": [67],
            "sex": ["male"],
            "weight": [2.5],
            "birth_year": [1950],
        }
    )
    population = SimpleNamespace(
        initial_slice=initial,
        scheduled_entries_by_year={2017: scheduled},
        reserved_real_ids=frozenset({1, 2}),
        earnings_domain_ids=frozenset({1}),
    )
    marriage_history = pd.DataFrame(
        {"person_id": [1, 2], "birth_year": [1954, 1950]}
    )
    observed_earnings = pd.DataFrame(
        {
            "person_id": [1, 2],
            "period": [2012, 2018],
            "age": [58, 68],
            "earnings": [9_000.0, 4_000.0],
        }
    )
    reference = object()
    inputs = SimpleNamespace(
        earnings_panel=observed_earnings,
        refit_inputs=SimpleNamespace(
            claiming_reference=reference,
            family_context=SimpleNamespace(marriage_records=marriage_history),
        ),
    )
    draws = tuple(
        FirstReportProjectionDraw(
            draw_index=draw_index,
            root_seed=DRAW_ROOT_SEEDS[draw_index],
            projection=_projection(draw_index),
            collector={},
        )
        for draw_index in DRAW_INDICES
    )
    return FirstReportProjectionBatch(
        inputs=inputs,
        phase=_PhaseWithForbiddenBundle(population),
        incumbent_phase=None,
        fit_preflight={},
        first_marriage_disclosure={},
        preflight_1={},
        preflight_2={},
        draws=draws,
    )


def test_validate_full_actual_parameters_rejects_other_vintages():
    parameters = _full_actual_parameters()
    preparation.validate_full_actual_report_parameters(parameters)

    provenance = dict(parameters.provenance)
    provenance["policyengine_us"] = {
        **provenance["policyengine_us"],
        "version": "1.751.0",
    }
    with pytest.raises(ValueError, match="pinned full-actual"):
        preparation.validate_full_actual_report_parameters(
            replace(parameters, provenance=provenance)
        )
    with pytest.raises(TypeError, match="ReportParameters"):
        preparation.validate_full_actual_report_parameters(object())


def test_trajectory_excludes_population_seed_metadata():
    batch = _batch()
    trajectory = preparation.concatenate_realized_trajectory(
        batch.draws[0].projection
    )

    assert sorted(trajectory["year"].unique()) == list(range(2014, 2023))
    assert 2 not in set(trajectory["person_id"])
    assert set(trajectory["person_id"]) == {1, 100}
    assert not trajectory.duplicated(["person_id", "year"]).any()


def test_synthetic_births_use_reserved_id_set_difference():
    trajectory = preparation.concatenate_realized_trajectory(
        _batch().draws[0].projection
    )

    assert preparation.derive_synthetic_birth_years(trajectory, {1, 2}) == {
        100: 2016
    }
    assert (
        preparation.derive_synthetic_birth_years(trajectory, {1, 2, 100}) == {}
    )

    conflicting = trajectory.copy()
    conflicting.loc[
        (conflicting["person_id"] == 100) & (conflicting["year"] == 2022),
        "birth_year",
    ] = 2017
    with pytest.raises(ValueError, match="conflicting native birth"):
        preparation.derive_synthetic_birth_years(conflicting, {1, 2})


def test_claiming_schedule_is_rebuilt_from_input_reference(monkeypatch):
    batch = _batch()
    calls = []
    expected_pmf = {
        ("female", 1998): {62: 1.0},
        ("male", 1998): {62: 1.0},
    }

    def claiming_pmfs(reference, *, boundary_year):
        calls.append((reference, boundary_year))
        return expected_pmf

    monkeypatch.setattr(
        preparation,
        "claiming_pmfs_from_reference",
        claiming_pmfs,
    )

    schedule = preparation.reconstruct_claiming_schedule(batch.inputs)

    assert schedule.pmf is expected_pmf
    assert calls == [(batch.inputs.refit_inputs.claiming_reference, 2014)]


def test_draw_preparation_routes_only_downstream_objects(monkeypatch):
    batch = _batch()
    parameters = _full_actual_parameters()
    schedule_pmf = {
        ("female", 1998): {62: 1.0},
        ("male", 1998): {62: 1.0},
    }
    monkeypatch.setattr(
        preparation,
        "claiming_pmfs_from_reference",
        lambda _reference, *, boundary_year: schedule_pmf,
    )
    calls = {}
    inclusion = SimpleNamespace(included=("included claimant",))
    benefit = object()
    revenue = object()
    birth_timing_sensitivity = object()

    def include(**kwargs):
        calls["inclusion"] = kwargs
        return inclusion

    def benefits(claimants, report_parameters, *, draw_index):
        calls["benefit"] = (claimants, report_parameters, draw_index)
        return benefit

    def revenues(projection, report_parameters):
        calls["revenue"] = (projection, report_parameters)
        return revenue

    monkeypatch.setattr(preparation, "build_career_inclusion", include)
    monkeypatch.setattr(preparation, "build_benefit_ledger", benefits)
    monkeypatch.setattr(preparation, "build_revenue_ledger", revenues)
    monkeypatch.setattr(
        preparation,
        "_build_birth_timing_sensitivity",
        lambda **_kwargs: birth_timing_sensitivity,
    )

    prepared = preparation._prepare_first_report_draw_for_test(
        batch,
        batch.draws[0],
        parameters=parameters,
    )

    inclusion_call = calls["inclusion"]
    assert inclusion_call["observed_earnings"] is batch.inputs.earnings_panel
    assert (
        inclusion_call["marriage_history"]
        is batch.inputs.refit_inputs.family_context.marriage_records
    )
    assert inclusion_call["earnings_domain_ids"] == frozenset({1})
    assert (
        inclusion_call["stock_imputation_root_seed"]
        == STOCK_IMPUTATION_ROOT_SEED
        == 8108
    )
    assert inclusion_call["projection_start_year"] == 2014
    assert set(inclusion_call["trajectory"]["person_id"]) == {1, 100}
    assert set(inclusion_call["population_roster"]["person_id"]) == {
        1,
        2,
        100,
    }
    assert 2 not in set(inclusion_call["trajectory"]["person_id"])
    assert inclusion_call["synthetic_birth_years"] == {100: 2016}
    pd.testing.assert_frame_equal(
        inclusion_call["seed_coordinates"],
        pd.DataFrame(
            {
                "person_id": [1, 2],
                "year": [2014, 2016],
                "anchor_wave": [2015, 2017],
                "age": [60, 67],
            }
        ),
    )
    assert inclusion_call["claiming_schedule"].pmf is schedule_pmf
    assert calls["benefit"] == (
        inclusion.included,
        parameters,
        0,
    )
    assert calls["revenue"] == (batch.draws[0].projection, parameters)
    assert prepared.inclusion is inclusion
    assert prepared.benefit_ledger is benefit
    assert prepared.revenue_ledger is revenue
    assert prepared.birth_timing_sensitivity is birth_timing_sensitivity


@pytest.mark.parametrize("shift", [-1, 1])
def test_shifted_candidate_inclusion_transports_only_age_derived_births(
    monkeypatch,
    shift,
):
    sources = (
        BirthSource.INFERRED_PERIOD_AGE,
        BirthSource.DERIVED_PROJECTION_AGE,
        BirthSource.EXACT_MARRIAGE,
        BirthSource.SYNTHETIC_NATIVE,
        BirthSource.UNRESOLVED,
    )
    baseline = SimpleNamespace(
        births=tuple(
            SimpleNamespace(
                person_id=person_id,
                birth_year=None if source is BirthSource.UNRESOLVED else 1950,
                source=source,
            )
            for person_id, source in enumerate(sources, start=1)
        ),
        origins=tuple(
            SimpleNamespace(person_id=person_id) for person_id in range(1, 6)
        ),
    )
    trajectory = pd.DataFrame(
        {"person_id": [*range(1, 6), 99], "year": [2015] * 6}
    )
    roster = pd.DataFrame({"person_id": [*range(1, 6), 99]})
    calls = {}

    def include(**kwargs):
        calls.update(kwargs)
        return SimpleNamespace(
            origins=baseline.origins,
            nonclaimants=(),
            di_partition=tuple(
                SimpleNamespace(classification=DIClass.NON_DI)
                for _ in baseline.origins
            ),
        )

    monkeypatch.setattr(preparation, "build_career_inclusion", include)

    result = preparation._shifted_candidate_inclusion(
        baseline=baseline,
        shift=shift,
        trajectory=trajectory,
        population_roster=roster,
        observed_earnings=pd.DataFrame(),
        claiming_schedule=SimpleNamespace(),
        earnings_domain_ids={1, 2, 3},
    )

    assert result.origins == baseline.origins
    assert set(calls["trajectory"]["person_id"]) == set(range(1, 6))
    assert set(calls["population_roster"]["person_id"]) == set(range(1, 6))
    assert calls["synthetic_birth_years"] == {}
    assert calls["stock_imputation_root_seed"] == STOCK_IMPUTATION_ROOT_SEED
    assert "seed_coordinates" not in calls
    assert calls["marriage_history"].to_dict("records") == [
        {"person_id": 1, "birth_year": 1950 + shift},
        {"person_id": 2, "birth_year": 1950 + shift},
        {"person_id": 3, "birth_year": 1950},
        {"person_id": 4, "birth_year": 1950},
    ]


def test_batch_preparation_requires_exact_registered_draw_sequence(
    monkeypatch,
):
    batch = _batch()
    parameters = _full_actual_parameters()
    schedule = SimpleNamespace(pmf={})
    monkeypatch.setattr(
        preparation,
        "reconstruct_claiming_schedule",
        lambda _inputs: schedule,
    )
    calls = []

    def prepare_draw(batch_arg, draw, *, parameters, claiming_schedule):
        calls.append(
            (batch_arg, draw.draw_index, parameters, claiming_schedule)
        )
        return SimpleNamespace(draw_index=draw.draw_index)

    monkeypatch.setattr(
        preparation,
        "_prepare_first_report_draw",
        prepare_draw,
    )

    prepared = preparation._prepare_first_report_batch(
        batch,
        parameters=parameters,
    )

    assert tuple(draw.draw_index for draw in prepared.draws) == DRAW_INDICES
    assert [call[1] for call in calls] == list(DRAW_INDICES)
    assert all(call[0] is batch for call in calls)
    assert all(call[2] is parameters for call in calls)
    assert all(call[3] is schedule for call in calls)

    missing = replace(batch, draws=batch.draws[:-1])
    with pytest.raises(ValueError, match="0 through 19"):
        preparation._prepare_first_report_batch(
            missing,
            parameters=parameters,
        )

    wrong_root_draw = replace(batch.draws[-1], root_seed=9999)
    wrong_root = replace(
        batch,
        draws=(*batch.draws[:-1], wrong_root_draw),
    )
    with pytest.raises(ValueError, match="root seeds changed"):
        preparation._prepare_first_report_batch(
            wrong_root,
            parameters=parameters,
        )


def test_prepared_batch_converts_and_binds_artifact_parameters(monkeypatch):
    parameters = _full_actual_parameters()
    inclusions = [object() for _ in DRAW_INDICES]
    benefits = [object() for _ in DRAW_INDICES]
    revenues = [object() for _ in DRAW_INDICES]
    birth_timing_sensitivities = [object() for _ in DRAW_INDICES]
    prepared_draws = tuple(
        preparation.PreparedFirstReportDraw(
            draw_index=draw_index,
            root_seed=DRAW_ROOT_SEEDS[draw_index],
            projection=object(),
            trajectory=pd.DataFrame(),
            population_roster=pd.DataFrame(),
            synthetic_birth_years={},
            inclusion=inclusions[draw_index],  # type: ignore[arg-type]
            benefits=benefits[draw_index],  # type: ignore[arg-type]
            revenue=revenues[draw_index],  # type: ignore[arg-type]
            birth_timing_sensitivity=birth_timing_sensitivities[draw_index],  # type: ignore[arg-type]
        )
        for draw_index in DRAW_INDICES
    )
    prepared = preparation.PreparedFirstReportBatch(
        parameters=parameters,
        claiming_schedule=SimpleNamespace(),  # type: ignore[arg-type]
        draws=prepared_draws,
    )

    bundles = preparation.first_report_draw_bundles(prepared)

    assert all(isinstance(bundle, FirstReportDrawBundle) for bundle in bundles)
    assert tuple(bundle.draw_index for bundle in bundles) == DRAW_INDICES
    for draw_index, bundle in enumerate(bundles):
        assert bundle.inclusion is inclusions[draw_index]
        assert bundle.benefits is benefits[draw_index]
        assert bundle.revenue is revenues[draw_index]
        assert (
            bundle.birth_timing_sensitivity
            is birth_timing_sensitivities[draw_index]
        )

    incomplete = replace(prepared, draws=prepared.draws[:-1])
    with pytest.raises(ValueError, match="0 through 19"):
        preparation.first_report_draw_bundles(incomplete)

    calls = []
    artifact = object()

    def build(bundles, **kwargs):
        calls.append((tuple(bundles), kwargs))
        return artifact

    monkeypatch.setattr(preparation, "build_first_estimates_artifact", build)
    configuration = {"parameters": dict(parameters.provenance)}
    observed = preparation._build_prepared_first_estimates_artifact(
        prepared,
        configuration_echo=configuration,
        runtime_provenance=parameters.runtime_provenance,
        environment_sidecar_sha256="a" * 64,
    )

    assert observed is artifact
    assert tuple(bundle.draw_index for bundle in calls[0][0]) == DRAW_INDICES
    assert calls[0][1] == {
        "configuration_echo": configuration,
        "runtime_provenance": parameters.runtime_provenance,
        "environment_sidecar_sha256": "a" * 64,
        "prior_incidents": (),
    }

    mismatched_configuration = {
        "parameters": {
            **parameters.provenance,
            "bundle_sha256": "b" * 64,
        }
    }
    with pytest.raises(ValueError, match="parameter provenance differs"):
        preparation._build_prepared_first_estimates_artifact(
            prepared,
            configuration_echo=mismatched_configuration,
            runtime_provenance=parameters.runtime_provenance,
            environment_sidecar_sha256="a" * 64,
        )
    mismatched_runtime = {
        **parameters.runtime_provenance,
        "parameters": {"policyengine_us": {"git_revision": "later"}},
    }
    with pytest.raises(ValueError, match="run-time parameter provenance"):
        preparation._build_prepared_first_estimates_artifact(
            prepared,
            configuration_echo=configuration,
            runtime_provenance=mismatched_runtime,
            environment_sidecar_sha256="a" * 64,
        )
    assert len(calls) == 1
