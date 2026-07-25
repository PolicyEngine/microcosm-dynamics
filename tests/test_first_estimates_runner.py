"""Reader-free tests for the first-estimates candidate-3 driver."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from populace_dynamics.estimates import runner
from populace_dynamics.harness.m6_candidate3_runner import (
    M6Candidate3InputPlan,
)
from populace_dynamics.harness.m6_runner import M6ResolvedContract

FAMILY_SPEC_SHA256 = (
    "734a5b04f347c5d4904bbc6d5ab9a1c2876272d35284eedd2f450518acf1cec5"
)
ENGINE_SPEC_SHA256 = (
    "c9be28a28d6fcc3911723872386906af559f6d0e0d5c89a87f741a5b2c3eacd6"
)


def _configuration() -> dict:
    return runner.registered_configuration_echo(
        registration_reference="issue-42-comment-1234567",
        parameter_bundle={"bundle_sha256": "a" * 64},
    )


def _configuration_bytes(configuration: dict | None = None) -> bytes:
    value = configuration if configuration is not None else _configuration()
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()


def _resolved() -> M6ResolvedContract:
    return M6ResolvedContract(
        contract=SimpleNamespace(),
        floor_artifact={},
        floor_path="runs/floor.json",
        floor_sha256="f" * 64,
    )


def _operations(calls: list[str], *, bad_family_hash: bool = False):
    population = object()
    identity = SimpleNamespace(
        family_spec_sha256=(
            "0" * 64 if bad_family_hash else FAMILY_SPEC_SHA256
        ),
        engine_spec_sha256=ENGINE_SPEC_SHA256,
    )
    phase = SimpleNamespace(
        population=population,
        lineage={
            "resolved_spec_sha256s": {
                "family_transitions": FAMILY_SPEC_SHA256,
                "engine_candidate": ENGINE_SPEC_SHA256,
            },
            "engine_candidate_id": "m6_candidate3_engine_v1",
        },
    )

    def mark(name, result):
        def call(*_args):
            calls.append(name)
            return result

        return call

    def project(observed_phase, observed_population, draw_index):
        assert observed_phase is phase
        assert observed_population is population
        calls.append(f"project:{draw_index}")
        return SimpleNamespace(draw_index=draw_index), {"draw": draw_index}

    return runner.FirstReportProjectionOperations(
        resolve_identity=mark("resolve_identity", identity),
        assert_identity=mark("assert_identity", None),
        fit=mark("fit", "bundle"),
        first_marriage_preflight=mark("fit_preflight", {"fit": "pass"}),
        fit_postrepair_incumbent=mark("fit_incumbent", "incumbent"),
        materialize=mark("materialize", phase),
        materialize_postrepair_incumbent=mark(
            "materialize_incumbent",
            "incumbent_phase",
        ),
        first_marriage_disclosure=mark("transport_disclosure", {"ok": True}),
        preflight_1=mark("preflight_1", {"ok": True}),
        preflight_2=mark("preflight_2", {"ok": True}),
        project_draw=project,
    )


def test__driver__replays_prefix_then_projects_twenty_unsplit_draws():
    calls: list[str] = []
    fit_inputs = object()

    def load_full_inputs():
        calls.append("load_full_inputs")
        return SimpleNamespace(refit_inputs=fit_inputs)

    plan = M6Candidate3InputPlan(
        fit_inputs=fit_inputs,
        load_full_inputs=load_full_inputs,
    )
    batch = runner.execute_first_report_projection(
        plan,
        resolved=_resolved(),
        configuration_echo=_configuration(),
        registered_configuration_bytes=_configuration_bytes(),
        operations=_operations(calls),
    )

    assert calls[:11] == [
        "resolve_identity",
        "assert_identity",
        "fit",
        "fit_preflight",
        "fit_incumbent",
        "load_full_inputs",
        "materialize",
        "materialize_incumbent",
        "transport_disclosure",
        "preflight_1",
        "preflight_2",
    ]
    assert calls[11:] == [
        f"project:{draw_index}" for draw_index in runner.DRAW_INDICES
    ]
    assert tuple(draw.draw_index for draw in batch.draws) == (
        runner.DRAW_INDICES
    )
    assert tuple(draw.root_seed for draw in batch.draws) == (
        runner.DRAW_ROOT_SEEDS
    )


def test__driver__rejects_spec_drift_before_fit_or_projection():
    calls: list[str] = []
    fit_inputs = object()
    plan = M6Candidate3InputPlan(
        fit_inputs=fit_inputs,
        load_full_inputs=lambda: SimpleNamespace(refit_inputs=fit_inputs),
    )

    with pytest.raises(RuntimeError, match="family spec sha256"):
        runner.execute_first_report_projection(
            plan,
            resolved=_resolved(),
            configuration_echo=_configuration(),
            registered_configuration_bytes=_configuration_bytes(),
            operations=_operations(calls, bad_family_hash=True),
        )

    assert calls == ["resolve_identity", "assert_identity"]


def test__driver__rejects_draw_configuration_drift_before_operations():
    calls: list[str] = []
    configuration = _configuration()
    configuration["projection"]["draw_indices"] = [0, 1]
    fit_inputs = object()
    plan = M6Candidate3InputPlan(
        fit_inputs=fit_inputs,
        load_full_inputs=lambda: SimpleNamespace(refit_inputs=fit_inputs),
    )

    with pytest.raises(ValueError, match="draw indices"):
        runner.execute_first_report_projection(
            plan,
            resolved=_resolved(),
            configuration_echo=configuration,
            registered_configuration_bytes=_configuration_bytes(configuration),
            operations=_operations(calls),
        )

    assert calls == []


def test__driver__pins_literal_spec_hashes_independently():
    assert runner.FAMILY_SPEC_SHA256 == FAMILY_SPEC_SHA256
    assert runner.ENGINE_SPEC_SHA256 == ENGINE_SPEC_SHA256


def test__driver__pins_ratified_design_and_amendment_identities():
    assert _configuration()["design"] == {
        "path": "docs/design/first_estimates_report.md",
        "ratification_commit": "6586b92",
        "amendment_commit": "f543597",
        "revision": 10,
    }


def test__driver__rejects_nonexact_registered_configuration_bytes():
    configuration = _configuration()
    with pytest.raises(ValueError, match="exact registered bytes"):
        runner.validate_registered_configuration_echo(
            configuration,
            registered_configuration_bytes=json.dumps(
                configuration,
                indent=2,
            ).encode(),
        )

    configuration["unregistered"] = True
    with pytest.raises(ValueError, match="exact registered structure"):
        runner.validate_registered_configuration_echo(
            configuration,
            registered_configuration_bytes=_configuration_bytes(configuration),
        )

    for volatile in (
        {"git_revision": "later"},
        {"root": "/tmp/site-packages"},
        {"file": {"path": "/tmp/parameter.yaml"}},
    ):
        with pytest.raises(ValueError, match="run-time parameter identity"):
            runner.registered_configuration_echo(
                registration_reference="issue-42-comment-1234567",
                parameter_bundle={
                    "bundle_sha256": "a" * 64,
                    **volatile,
                },
            )
