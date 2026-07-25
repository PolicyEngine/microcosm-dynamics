"""Pure downstream preparation for the first-estimates statutory pipeline.

The projection itself is produced by :mod:`populace_dynamics.estimates.runner`.
This module only adapts an already-materialized projection batch into career,
benefit, and revenue ledgers.  In particular, it never consults the fitted
``phase.bundle`` and never invokes a projection operation.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Collection, Mapping
from dataclasses import dataclass
from typing import Any

import pandas as pd

from populace_dynamics.engine.refit import (
    BOUNDARY_YEAR,
    claiming_pmfs_from_reference,
)
from populace_dynamics.engine.steps import ClaimingSchedule
from populace_dynamics.estimates import parameters as parameter_module
from populace_dynamics.estimates.career import (
    InclusionResult,
    build_career_inclusion,
    build_population_roster,
)
from populace_dynamics.estimates.first_report import (
    FirstReportDrawBundle,
    build_first_estimates_artifact,
)
from populace_dynamics.estimates.ledgers import (
    BenefitLedger,
    RevenueLedger,
    build_benefit_ledger,
    build_revenue_ledger,
)
from populace_dynamics.estimates.parameters import (
    COLA_CONTENT_SHA256,
    COLA_FILE_SHA256,
    PINNED_PE_US_VERSION,
    ReportParameters,
)
from populace_dynamics.estimates.runner import (
    DRAW_INDICES,
    DRAW_ROOT_SEEDS,
    PROJECTION_END_YEAR,
    PROJECTION_START_YEAR,
    STOCK_IMPUTATION_ROOT_SEED,
    FirstReportProjectionBatch,
    FirstReportProjectionDraw,
)

__all__ = [
    "PreparedFirstReportBatch",
    "PreparedFirstReportDraw",
    "concatenate_realized_trajectory",
    "derive_synthetic_birth_years",
    "first_report_draw_bundles",
    "reconstruct_claiming_schedule",
    "validate_full_actual_report_parameters",
]


@dataclass(frozen=True)
class PreparedFirstReportDraw:
    """Career inclusion and both statutory ledgers for one projection draw."""

    draw_index: int
    root_seed: int
    projection: Any
    trajectory: pd.DataFrame
    population_roster: pd.DataFrame
    synthetic_birth_years: Mapping[int, int]
    inclusion: InclusionResult
    benefits: BenefitLedger
    revenue: RevenueLedger

    @property
    def benefit_ledger(self) -> BenefitLedger:
        """Compatibility name for callers that spell out the ledger type."""

        return self.benefits

    @property
    def revenue_ledger(self) -> RevenueLedger:
        """Compatibility name for callers that spell out the ledger type."""

        return self.revenue


@dataclass(frozen=True)
class PreparedFirstReportBatch:
    """All twenty prepared report draws and their independent inputs."""

    parameters: ReportParameters
    claiming_schedule: ClaimingSchedule
    draws: tuple[PreparedFirstReportDraw, ...]


def first_report_draw_bundles(
    prepared: PreparedFirstReportBatch,
) -> tuple[FirstReportDrawBundle, ...]:
    """Convert preparation results into the artifact assembler's input type."""

    if not isinstance(prepared, PreparedFirstReportBatch):
        raise TypeError(
            "artifact conversion requires PreparedFirstReportBatch"
        )
    observed = tuple(draw.draw_index for draw in prepared.draws)
    if observed != DRAW_INDICES:
        raise ValueError(
            "prepared artifact input must contain draw indices 0 through 19 "
            "in protocol order"
        )
    return tuple(
        FirstReportDrawBundle(
            draw_index=draw.draw_index,
            inclusion=draw.inclusion,
            benefits=draw.benefits,
            revenue=draw.revenue,
        )
        for draw in prepared.draws
    )


def _build_prepared_first_estimates_artifact(
    prepared: PreparedFirstReportBatch,
    *,
    configuration_echo: Mapping[str, Any],
    environment_sidecar_sha256: str,
    prior_incidents: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Assemble an artifact only under the parameters used for its ledgers."""

    if not isinstance(prepared, PreparedFirstReportBatch):
        raise TypeError("artifact assembly requires PreparedFirstReportBatch")
    validate_full_actual_report_parameters(prepared.parameters)
    if not isinstance(configuration_echo, Mapping):
        raise TypeError("configuration_echo must be a mapping")
    if configuration_echo.get("parameters") != prepared.parameters.provenance:
        raise ValueError(
            "configuration parameter provenance differs from the bundle "
            "used to compute the prepared statutory ledgers"
        )
    return build_first_estimates_artifact(
        first_report_draw_bundles(prepared),
        configuration_echo=configuration_echo,
        environment_sidecar_sha256=environment_sidecar_sha256,
        prior_incidents=prior_incidents,
    )


def _whole_number(value: Any, label: str) -> int:
    """Return an integer-valued scalar, rejecting missing/fractional values."""

    if pd.isna(value):
        raise ValueError(f"{label} is missing")
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} is not numeric: {value!r}") from error
    if not number.is_integer():
        raise ValueError(f"{label} must be integer-valued, got {value!r}")
    return int(number)


def _canonical_mapping_sha256(values: Mapping[str, str]) -> str:
    encoded = (
        json.dumps(dict(values), sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def validate_full_actual_report_parameters(
    parameters: ReportParameters,
) -> None:
    """Require the independently loaded, hash-bound full-actual parameter set.

    The loader has already validated the actual NAWI, wage base, OASDI rate
    legs, and COLA coverage.  This downstream check freezes that loader's
    provenance so a projection-owned or hand-built parameter object cannot
    silently enter report preparation.
    """

    if not isinstance(parameters, ReportParameters):
        raise TypeError(
            "first-report preparation requires a ReportParameters object"
        )
    provenance = parameters.provenance
    if provenance.get("schema_version") != "first_estimates.parameters.v1":
        raise ValueError("report parameters have the wrong provenance schema")
    policyengine = provenance.get("policyengine_us")
    if not isinstance(policyengine, Mapping):
        raise ValueError("report parameters lack policyengine-us provenance")
    if policyengine.get("version") != PINNED_PE_US_VERSION:
        raise ValueError(
            "report preparation requires the pinned full-actual "
            f"policyengine-us {PINNED_PE_US_VERSION} tree"
        )
    if (
        policyengine.get("ssa_parameter_bundle_sha256")
        != parameter_module.SSA_PARAMETER_BUNDLE_SHA256
    ):
        raise ValueError("SSA parameter bundle provenance changed")
    if (
        policyengine.get("all_consumed_files_sha256")
        != parameter_module.PE_US_CONSUMED_BUNDLE_SHA256
    ):
        raise ValueError("consumed policyengine-us bundle provenance changed")

    rates = provenance.get("oasdi_rate_legs")
    if not isinstance(rates, Mapping):
        raise ValueError("report parameters lack OASDI rate-leg provenance")
    if rates.get("bundle_sha256") != parameter_module.RATE_LEG_BUNDLE_SHA256:
        raise ValueError("OASDI rate-leg bundle provenance changed")
    if (
        rates.get("asserted_employee_rate"),
        rates.get("asserted_employer_rate"),
        rates.get("asserted_combined_rate"),
    ) != (0.062, 0.062, 0.124):
        raise ValueError("OASDI rate-leg assertions changed")

    cola = provenance.get("cola")
    if not isinstance(cola, Mapping):
        raise ValueError("report parameters lack COLA provenance")
    if (
        cola.get("sha256"),
        cola.get("content_sha256"),
    ) != (COLA_FILE_SHA256, COLA_CONTENT_SHA256):
        raise ValueError("COLA parameter provenance changed")

    components = provenance.get("bundle_components")
    expected_components = {
        "policyengine_us_consumed_files": (
            parameter_module.PE_US_CONSUMED_BUNDLE_SHA256
        ),
        "cola_file": COLA_FILE_SHA256,
        "cola_content": COLA_CONTENT_SHA256,
    }
    if components != expected_components:
        raise ValueError("report parameter bundle components changed")
    if provenance.get("bundle_sha256") != _canonical_mapping_sha256(
        expected_components
    ):
        raise ValueError("report parameter bundle sha256 changed")


def concatenate_realized_trajectory(projection: Any) -> pd.DataFrame:
    """Concatenate only the returned 2014-2022 projection slices.

    Population seed frames are intentionally absent here.  They are metadata
    used to complete the Stage-A universe, not invented presence or disability
    observations.
    """

    try:
        slices = tuple(projection.slices)
    except AttributeError as error:
        raise TypeError("projection must expose returned slices") from error
    expected_years = tuple(
        range(PROJECTION_START_YEAR, PROJECTION_END_YEAR + 1)
    )
    if len(slices) != len(expected_years):
        raise ValueError(
            "first-report trajectory requires exactly the returned "
            f"{PROJECTION_START_YEAR}-{PROJECTION_END_YEAR} slices"
        )

    copied: list[pd.DataFrame] = []
    for expected_year, frame in zip(expected_years, slices, strict=True):
        if not isinstance(frame, pd.DataFrame):
            raise TypeError(
                f"projection slice {expected_year} is not a pandas frame"
            )
        missing = {"person_id", "year"} - set(frame.columns)
        if missing:
            raise ValueError(
                f"projection slice {expected_year} lacks {sorted(missing)}"
            )
        if frame["person_id"].duplicated().any():
            raise ValueError(
                f"projection slice {expected_year} has duplicate people"
            )
        years = {
            _whole_number(value, f"projection slice {expected_year} year")
            for value in frame["year"].unique()
        }
        if years and years != {expected_year}:
            raise ValueError(
                f"projection slice {expected_year} carries years "
                f"{sorted(years)}"
            )
        copied.append(frame.copy())

    trajectory = pd.concat(copied, ignore_index=True, sort=False)
    if trajectory.duplicated(["person_id", "year"]).any():
        raise ValueError("returned trajectory has duplicate person-year rows")
    return trajectory


def derive_synthetic_birth_years(
    trajectory: pd.DataFrame,
    reserved_real_ids: Collection[int],
) -> dict[int, int]:
    """Return native births for IDs outside the reserved real namespace."""

    if "person_id" not in trajectory:
        raise ValueError("trajectory lacks person_id")
    real_ids = {
        _whole_number(value, "reserved real person_id")
        for value in reserved_real_ids
    }
    person_ids = trajectory["person_id"].map(
        lambda value: _whole_number(value, "trajectory person_id")
    )
    synthetic_ids = sorted(set(person_ids) - real_ids)
    if not synthetic_ids:
        return {}
    if "birth_year" not in trajectory:
        raise ValueError("synthetic trajectory rows lack native birth_year")

    work = trajectory.assign(_report_person_id=person_ids)
    result: dict[int, int] = {}
    for person_id in synthetic_ids:
        rows = work[work["_report_person_id"] == person_id]
        years = {
            _whole_number(
                value, f"native birth year for synthetic person {person_id}"
            )
            for value in rows["birth_year"]
            if not pd.isna(value)
        }
        if not years:
            raise ValueError(
                f"synthetic person {person_id} has no native birth_year"
            )
        if len(years) != 1:
            raise ValueError(
                f"synthetic person {person_id} has conflicting native "
                f"birth years {sorted(years)}"
            )
        result[person_id] = next(iter(years))
    return result


def reconstruct_claiming_schedule(inputs: Any) -> ClaimingSchedule:
    """Rebuild the cutoff-pinned schedule from the caller-owned reference."""

    try:
        reference = inputs.refit_inputs.claiming_reference
    except AttributeError as error:
        raise TypeError(
            "first-report inputs lack the pinned claiming reference"
        ) from error
    pmf = claiming_pmfs_from_reference(
        reference,
        boundary_year=BOUNDARY_YEAR,
    )
    return ClaimingSchedule(pmf)


def _validate_draw(draw: FirstReportProjectionDraw) -> None:
    if not isinstance(draw, FirstReportProjectionDraw):
        raise TypeError(
            "first-report preparation requires FirstReportProjectionDraw"
        )
    draw_index = _whole_number(draw.draw_index, "draw_index")
    if draw_index not in DRAW_INDICES:
        raise ValueError(f"draw_index must be one of {DRAW_INDICES}")
    expected_root = DRAW_ROOT_SEEDS[draw_index]
    if draw.root_seed != expected_root:
        raise ValueError(
            f"draw {draw_index} root seed {draw.root_seed} != "
            f"registered {expected_root}"
        )
    observed = getattr(draw.projection, "draw_index", None)
    if observed != draw_index:
        raise ValueError(
            f"projection draw index {observed!r} != wrapper {draw_index}"
        )


def _prepare_first_report_draw(
    batch: FirstReportProjectionBatch,
    draw: FirstReportProjectionDraw,
    *,
    parameters: ReportParameters,
    claiming_schedule: ClaimingSchedule,
) -> PreparedFirstReportDraw:
    _validate_draw(draw)
    try:
        population = batch.phase.population
        initial_slice = population.initial_slice
        scheduled_entries = population.scheduled_entries_by_year
        reserved_real_ids = population.reserved_real_ids
        earnings_domain_ids = population.earnings_domain_ids
        observed_earnings = batch.inputs.earnings_panel
        marriage_history = (
            batch.inputs.refit_inputs.family_context.marriage_records
        )
    except AttributeError as error:
        raise TypeError(
            "projection batch lacks candidate-3 preparation inputs"
        ) from error

    trajectory = concatenate_realized_trajectory(draw.projection)
    roster = build_population_roster(
        initial_slice,
        scheduled_entries,
        trajectory,
    )
    synthetic_birth_years = derive_synthetic_birth_years(
        trajectory,
        reserved_real_ids,
    )
    inclusion = build_career_inclusion(
        trajectory=trajectory,
        population_roster=roster,
        observed_earnings=observed_earnings,
        marriage_history=marriage_history,
        synthetic_birth_years=synthetic_birth_years,
        claiming_schedule=claiming_schedule,
        earnings_domain_ids=earnings_domain_ids,
        stock_imputation_root_seed=STOCK_IMPUTATION_ROOT_SEED,
        projection_start_year=PROJECTION_START_YEAR,
    )
    benefit_ledger = build_benefit_ledger(
        inclusion.included,
        parameters,
        draw_index=draw.draw_index,
    )
    revenue_ledger = build_revenue_ledger(draw.projection, parameters)
    return PreparedFirstReportDraw(
        draw_index=draw.draw_index,
        root_seed=draw.root_seed,
        projection=draw.projection,
        trajectory=trajectory,
        population_roster=roster,
        synthetic_birth_years=synthetic_birth_years,
        inclusion=inclusion,
        benefits=benefit_ledger,
        revenue=revenue_ledger,
    )


def _prepare_first_report_draw_for_test(
    batch: FirstReportProjectionBatch,
    draw: FirstReportProjectionDraw,
    *,
    parameters: ReportParameters,
) -> PreparedFirstReportDraw:
    """Prepare one already-projected draw without invoking the engine."""

    if not isinstance(batch, FirstReportProjectionBatch):
        raise TypeError(
            "first-report preparation requires FirstReportProjectionBatch"
        )
    validate_full_actual_report_parameters(parameters)
    schedule = reconstruct_claiming_schedule(batch.inputs)
    return _prepare_first_report_draw(
        batch,
        draw,
        parameters=parameters,
        claiming_schedule=schedule,
    )


def _prepare_first_report_batch(
    batch: FirstReportProjectionBatch,
    *,
    parameters: ReportParameters,
) -> PreparedFirstReportBatch:
    """Prepare the exact registered draw-0-through-19 projection batch."""

    if not isinstance(batch, FirstReportProjectionBatch):
        raise TypeError(
            "first-report preparation requires FirstReportProjectionBatch"
        )
    validate_full_actual_report_parameters(parameters)
    draws = tuple(batch.draws)
    observed_indices = tuple(draw.draw_index for draw in draws)
    if observed_indices != DRAW_INDICES:
        raise ValueError(
            "first-report batch must contain draw indices 0 through 19 "
            "exactly once and in protocol order"
        )
    observed_roots = tuple(draw.root_seed for draw in draws)
    if observed_roots != DRAW_ROOT_SEEDS:
        raise ValueError("first-report batch projection root seeds changed")

    schedule = reconstruct_claiming_schedule(batch.inputs)
    prepared = tuple(
        _prepare_first_report_draw(
            batch,
            draw,
            parameters=parameters,
            claiming_schedule=schedule,
        )
        for draw in draws
    )
    if tuple(draw.draw_index for draw in prepared) != DRAW_INDICES:
        raise AssertionError("prepared draw batch is out of protocol order")
    return PreparedFirstReportBatch(
        parameters=parameters,
        claiming_schedule=schedule,
        draws=prepared,
    )
