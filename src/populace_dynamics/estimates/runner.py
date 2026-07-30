"""Non-executed driver for the registered first-estimates projection.

The default operations replay the candidate-3 gate runner's frozen
fit/preflight/materialization prefix, then call its projection recipe on the
*unsplit* realized population for draw indices 0 through 19.  Everything is
injectable so the sequence and spec guards can be unit-tested without PSID or
performing a projection.
"""

from __future__ import annotations

import copy
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Any

from populace_dynamics.engine.loop import ProjectionResult
from populace_dynamics.engine.rng import DRAW_SEED_BASE
from populace_dynamics.estimates.publication import canonical_json_bytes
from populace_dynamics.harness import m6_candidate3_runner, m6_runner
from populace_dynamics.harness.m6_candidate3_runner import (
    M6Candidate3InputPlan,
)
from populace_dynamics.harness.m6_runner import M6ResolvedContract

DESIGN_COMMIT = "6586b92"
DESIGN_AMENDMENT_COMMIT = "f771b49"
FAMILY_SPEC_SHA256 = (
    "734a5b04f347c5d4904bbc6d5ab9a1c2876272d35284eedd2f450518acf1cec5"
)
ENGINE_SPEC_SHA256 = (
    "c9be28a28d6fcc3911723872386906af559f6d0e0d5c89a87f741a5b2c3eacd6"
)
DRAW_INDICES = tuple(range(20))
DRAW_ROOT_SEED_BASE = 5200
DRAW_ROOT_SEEDS = tuple(DRAW_ROOT_SEED_BASE + index for index in DRAW_INDICES)
STOCK_IMPUTATION_ROOT_SEED = 8108
PROJECTION_START_YEAR = 2014
PROJECTION_END_YEAR = 2022
PROJECTION_OBJECT = "candidate-3 GATED_REALIZED reproduction panel, unsplit"

if DRAW_SEED_BASE != DRAW_ROOT_SEED_BASE:
    raise RuntimeError(
        f"engine DRAW_SEED_BASE {DRAW_SEED_BASE} != frozen report root "
        f"{DRAW_ROOT_SEED_BASE}"
    )
if STOCK_IMPUTATION_ROOT_SEED in DRAW_ROOT_SEEDS:
    raise RuntimeError("stock-imputation root overlaps a projection root seed")


@dataclass(frozen=True)
class FirstReportProjectionOperations:
    """Injectable seams preserving the candidate-3 normative order."""

    resolve_identity: Callable[[], Any]
    assert_identity: Callable[[Any], None]
    fit: Callable[[Any], Any]
    first_marriage_preflight: Callable[[Any], Mapping[str, Any]]
    fit_postrepair_incumbent: Callable[[Any, Any], Any]
    materialize: Callable[[Any, Any], Any]
    materialize_postrepair_incumbent: Callable[[Any, Any], Any]
    first_marriage_disclosure: Callable[
        [Any, Any, M6ResolvedContract, Mapping[str, Any]],
        Mapping[str, Any],
    ]
    preflight_1: Callable[[Any, Any, Any], Mapping[str, Any]]
    preflight_2: Callable[[Any, Any, Any], Mapping[str, Any]]
    project_draw: Callable[[Any, Any, int], tuple[ProjectionResult, Any]]


@dataclass(frozen=True)
class FirstReportProjectionDraw:
    """One unsplit candidate-3 projection and its collected diagnostics."""

    draw_index: int
    root_seed: int
    projection: ProjectionResult | Any
    collector: Any


@dataclass(frozen=True)
class FirstReportProjectionBatch:
    """Objects returned only after the complete frozen prefix and all draws."""

    inputs: Any
    phase: Any
    incumbent_phase: Any
    fit_preflight: Mapping[str, Any]
    first_marriage_disclosure: Mapping[str, Any]
    preflight_1: Mapping[str, Any]
    preflight_2: Mapping[str, Any]
    draws: tuple[FirstReportProjectionDraw, ...]


def default_projection_operations() -> FirstReportProjectionOperations:
    """Bind the exact candidate-3 gate runner operations and projection recipe."""
    candidate = m6_candidate3_runner.default_operations()

    def project_draw(
        phase: Any, population: Any, draw_index: int
    ) -> tuple[ProjectionResult, Any]:
        return m6_runner._project_side(
            phase,
            population,
            draw_index=draw_index,
        )

    return FirstReportProjectionOperations(
        resolve_identity=m6_candidate3_runner.resolve_candidate3_identity,
        assert_identity=(
            m6_candidate3_runner.assert_candidate3_identity_is_frozen
        ),
        fit=candidate.fit,
        first_marriage_preflight=candidate.first_marriage_preflight,
        fit_postrepair_incumbent=candidate.fit_postrepair_incumbent,
        materialize=candidate.materialize,
        materialize_postrepair_incumbent=(
            candidate.materialize_postrepair_incumbent
        ),
        first_marriage_disclosure=candidate.first_marriage_disclosure,
        preflight_1=candidate.preflight_1,
        preflight_2=candidate.preflight_2,
        project_draw=project_draw,
    )


def registered_configuration_echo(
    *,
    registration_reference: str,
    parameter_bundle: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the immutable JSON configuration built before any compute."""
    if (
        not isinstance(registration_reference, str)
        or not registration_reference
    ):
        raise ValueError("registration_reference must be a nonempty string")
    _assert_registered_parameter_bundle_is_stable(parameter_bundle)
    return {
        "registration_reference": registration_reference,
        "design": {
            "path": "docs/design/first_estimates_report.md",
            "ratification_commit": DESIGN_COMMIT,
            "amendment_commit": DESIGN_AMENDMENT_COMMIT,
            "revision": 10,
        },
        "projection": {
            "object": PROJECTION_OBJECT,
            "start_year": PROJECTION_START_YEAR,
            "end_year": PROJECTION_END_YEAR,
            "split": False,
            "draw_indices": list(DRAW_INDICES),
            "root_seeds": list(DRAW_ROOT_SEEDS),
        },
        "candidate_specs": {
            "family": {
                "id": "m6_candidate2_registry_v1",
                "sha256": FAMILY_SPEC_SHA256,
            },
            "engine": {
                "id": "m6_candidate3_engine_v1",
                "sha256": ENGINE_SPEC_SHA256,
            },
        },
        "stock_imputation": {
            "root_seed": STOCK_IMPUTATION_ROOT_SEED,
            "namespace": "first_estimates.opening_stock.person.v1",
            "person_keyed": True,
        },
        "parameters": copy.deepcopy(dict(parameter_bundle)),
    }


def _assert_registered_parameter_bundle_is_stable(
    parameter_bundle: Mapping[str, Any],
) -> None:
    """Exclude run-time identity from the byte-compared parameter record."""

    def walk(value: Any, path: tuple[str, ...]) -> None:
        if isinstance(value, Mapping):
            for key, nested in value.items():
                if not isinstance(key, str):
                    raise ValueError(
                        "registered parameter keys must be JSON strings"
                    )
                if key in {"git_revision", "path", "root"}:
                    location = ".".join((*path, key))
                    raise ValueError(
                        f"run-time parameter identity {location} is not "
                        "registerable"
                    )
                walk(nested, (*path, key))
            return
        if isinstance(value, (list, tuple)):
            for index, nested in enumerate(value):
                walk(nested, (*path, str(index)))
            return
        if isinstance(value, str) and (
            Path(value).is_absolute() or PureWindowsPath(value).is_absolute()
        ):
            location = ".".join(path)
            raise ValueError(
                f"absolute run-time path at {location} is not registerable"
            )

    if not isinstance(parameter_bundle, Mapping):
        raise TypeError("parameter_bundle must be a mapping")
    walk(parameter_bundle, ("parameters",))


def validate_registered_configuration_echo(
    configuration: Mapping[str, Any],
    *,
    registered_configuration_bytes: bytes,
) -> None:
    """Require the exact canonical bytes and every registered constant."""
    if not isinstance(registered_configuration_bytes, bytes):
        raise TypeError("registered configuration must be supplied as bytes")
    if canonical_json_bytes(configuration) != registered_configuration_bytes:
        raise ValueError(
            "configuration differs from the exact registered bytes"
        )
    projection = configuration.get("projection")
    if not isinstance(projection, Mapping):
        raise ValueError("configuration has no projection block")
    if projection.get("object") != PROJECTION_OBJECT:
        raise ValueError("configuration selects the wrong projection object")
    if projection.get("start_year") != PROJECTION_START_YEAR:
        raise ValueError("configuration start year changed")
    if projection.get("end_year") != PROJECTION_END_YEAR:
        raise ValueError("configuration end year changed")
    if projection.get("split") is not False:
        raise ValueError("first-estimates projection must be unsplit")
    if projection.get("draw_indices") != list(DRAW_INDICES):
        raise ValueError("configuration draw indices changed")
    if projection.get("root_seeds") != list(DRAW_ROOT_SEEDS):
        raise ValueError("configuration root seeds changed")
    design = configuration.get("design")
    if not isinstance(design, Mapping) or design != {
        "path": "docs/design/first_estimates_report.md",
        "ratification_commit": DESIGN_COMMIT,
        "amendment_commit": DESIGN_AMENDMENT_COMMIT,
        "revision": 10,
    }:
        raise ValueError("configuration design binding changed")
    specs = configuration.get("candidate_specs")
    if not isinstance(specs, Mapping):
        raise ValueError("configuration has no candidate-spec block")
    if specs.get("family", {}).get("sha256") != FAMILY_SPEC_SHA256:
        raise ValueError("registered family CandidateSpec sha256 changed")
    if specs.get("engine", {}).get("sha256") != ENGINE_SPEC_SHA256:
        raise ValueError("registered engine CandidateSpec sha256 changed")
    if specs.get("family", {}).get("id") != "m6_candidate2_registry_v1":
        raise ValueError("registered family CandidateSpec id changed")
    if specs.get("engine", {}).get("id") != "m6_candidate3_engine_v1":
        raise ValueError("registered engine CandidateSpec id changed")
    stock = configuration.get("stock_imputation")
    if not isinstance(stock, Mapping) or stock != {
        "root_seed": STOCK_IMPUTATION_ROOT_SEED,
        "namespace": "first_estimates.opening_stock.person.v1",
        "person_keyed": True,
    }:
        raise ValueError("stock-imputation root seed changed")
    registration_reference = configuration.get("registration_reference")
    if (
        not isinstance(registration_reference, str)
        or not registration_reference
    ):
        raise ValueError("configuration registration reference is invalid")
    parameters = configuration.get("parameters")
    if not isinstance(parameters, Mapping):
        raise ValueError("configuration has no parameter-bundle provenance")
    digest = parameters.get("bundle_sha256")
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise ValueError("configuration parameter-bundle sha256 is invalid")
    expected = registered_configuration_echo(
        registration_reference=registration_reference,
        parameter_bundle=parameters,
    )
    if dict(configuration) != expected:
        raise ValueError(
            "configuration does not have the exact registered structure"
        )


def _assert_identity_hashes(identity: Any) -> None:
    family = getattr(identity, "family_spec_sha256", None)
    engine = getattr(identity, "engine_spec_sha256", None)
    if family != FAMILY_SPEC_SHA256:
        raise RuntimeError(
            f"candidate-3 family spec sha256 {family!r} != "
            f"{FAMILY_SPEC_SHA256}"
        )
    if engine != ENGINE_SPEC_SHA256:
        raise RuntimeError(
            f"candidate-3 engine spec sha256 {engine!r} != "
            f"{ENGINE_SPEC_SHA256}"
        )


def _assert_phase_lineage(phase: Any) -> None:
    lineage = getattr(phase, "lineage", None)
    if not isinstance(lineage, Mapping):
        raise RuntimeError("candidate-3 phase has no fitted lineage")
    specs = lineage.get("resolved_spec_sha256s")
    if not isinstance(specs, Mapping):
        raise RuntimeError("candidate-3 phase has no resolved spec sha256s")
    if specs.get("family_transitions") != FAMILY_SPEC_SHA256:
        raise RuntimeError("fitted family CandidateSpec sha256 changed")
    if specs.get("engine_candidate") != ENGINE_SPEC_SHA256:
        raise RuntimeError("fitted engine CandidateSpec sha256 changed")
    if lineage.get("engine_candidate_id") != "m6_candidate3_engine_v1":
        raise RuntimeError("fitted phase has the wrong engine candidate id")


def execute_first_report_projection(
    input_plan: M6Candidate3InputPlan,
    *,
    resolved: M6ResolvedContract,
    configuration_echo: Mapping[str, Any],
    registered_configuration_bytes: bytes,
    operations: FirstReportProjectionOperations | None = None,
) -> FirstReportProjectionBatch:
    """Replay the frozen prefix and project twenty unsplit draws.

    This function is intentionally not called by tests with real data and is
    not invoked anywhere at import time.  Its caller owns incident publication
    if a preparation, invariant, or compute exception escapes.
    """
    if not isinstance(input_plan, M6Candidate3InputPlan):
        raise TypeError(
            "first-estimates driver requires M6Candidate3InputPlan"
        )
    if not isinstance(resolved, M6ResolvedContract):
        raise TypeError("first-estimates driver requires M6ResolvedContract")
    validate_registered_configuration_echo(
        configuration_echo,
        registered_configuration_bytes=registered_configuration_bytes,
    )
    ops = operations or default_projection_operations()

    # Spec assertions occur before fit, materialization, or any projection draw.
    identity = ops.resolve_identity()
    ops.assert_identity(identity)
    _assert_identity_hashes(identity)

    # Candidate-3 gate runner normative sequence through preflight 2.
    bundle = ops.fit(input_plan.fit_inputs)
    fit_preflight = ops.first_marriage_preflight(bundle)
    incumbent_bundle = ops.fit_postrepair_incumbent(
        input_plan.fit_inputs,
        bundle,
    )
    inputs = input_plan.load_full_inputs()
    if getattr(inputs, "refit_inputs", None) is not input_plan.fit_inputs:
        raise RuntimeError(
            "full inputs do not carry the exact preflighted fit-input object"
        )
    phase = ops.materialize(inputs, bundle)
    _assert_phase_lineage(phase)
    incumbent_phase = ops.materialize_postrepair_incumbent(
        phase,
        incumbent_bundle,
    )
    first_marriage = ops.first_marriage_disclosure(
        inputs,
        phase,
        resolved,
        fit_preflight,
    )
    preflight_1 = ops.preflight_1(inputs, phase, resolved.contract)
    preflight_2 = ops.preflight_2(inputs, phase, resolved.contract)

    population = getattr(phase, "population", None)
    if population is None:
        raise RuntimeError("candidate-3 phase has no unsplit population")
    draws: list[FirstReportProjectionDraw] = []
    for draw_index, root_seed in zip(
        DRAW_INDICES,
        DRAW_ROOT_SEEDS,
        strict=True,
    ):
        projection, collector = ops.project_draw(
            phase,
            population,
            draw_index,
        )
        observed_index = getattr(projection, "draw_index", draw_index)
        if observed_index != draw_index:
            raise RuntimeError(
                "projection draw result is out of protocol order"
            )
        draws.append(
            FirstReportProjectionDraw(
                draw_index=draw_index,
                root_seed=root_seed,
                projection=projection,
                collector=collector,
            )
        )
    if tuple(draw.draw_index for draw in draws) != DRAW_INDICES:
        raise RuntimeError("projection draw batch is out of protocol order")
    return FirstReportProjectionBatch(
        inputs=inputs,
        phase=phase,
        incumbent_phase=incumbent_phase,
        fit_preflight=fit_preflight,
        first_marriage_disclosure=first_marriage,
        preflight_1=preflight_1,
        preflight_2=preflight_2,
        draws=tuple(draws),
    )


def resolve_report_contract(
    root: str | Path,
) -> M6ResolvedContract:
    """Read the same committed gate contract used by the candidate-3 prefix."""
    return m6_runner.resolve_m6_contract(Path(root).resolve())
