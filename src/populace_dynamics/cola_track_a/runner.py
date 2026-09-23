"""Run the Track A assembly: K draws, benefits per row, A7 tabulation.

:func:`run_track_a` projects the opening state once per draw with the
unmodified ``engine.loop.ProjectionEngine`` (draw ``k`` has root entropy
``5200 + k`` and person-keyed streams), computes every registered row's
baseline and reform benefits from that one projection (so both scenarios
share every simulated path), and tabulates each row with the A7
five-group statistic.  Nothing is scheduled as an entrant; the allocator
check of ``engine.entrant_schedule`` runs on the projection metadata all
the same.

Governance interlock: a cohort whose ``data_provenance`` is
``"registered_real"`` is refused unless a registration pointer (the issue
#42 comment that must precede the one-shot run) is supplied; A7 refuses
the same case independently.  Invented cohorts carry the invented-data
label on every output.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import re
import warnings
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics import claiming
from populace_dynamics import scenario_benefits as sb
from populace_dynamics.cohorts import psid2010
from populace_dynamics.cola_track_a.adapters import (
    build_period_modules,
    claiming_schedule,
)
from populace_dynamics.cola_track_a.benefits import (
    BenefitContext,
    StateLookups,
    reference_benefit_rows,
)
from populace_dynamics.cola_track_a.config import (
    REGISTERED_ROWS,
    ROWS_NOT_BUILT,
    TrackAConfig,
    pending_decisions,
)
from populace_dynamics.cola_track_a.opening import TrackACohort
from populace_dynamics.data import tr2008
from populace_dynamics.engine.di_entitlement import (
    di_prevalence,
    di_stock_flow,
    fra_schedule_from_parameters,
)
from populace_dynamics.engine.di_entitlement_rates import DIEntitlementRates
from populace_dynamics.engine.entrant_schedule import (
    validate_projection_allocator,
)
from populace_dynamics.engine.loop import (
    SCHEDULED_ENTRIES_KEY,
    ProjectionEngine,
    ProjectionResult,
)
from populace_dynamics.estimates.cola_age_profile import (
    DEFAULT_AGE_GROUPS,
    REGISTERED_REAL,
    ColaAgeProfileConfig,
    ColaTabulationError,
    tabulate_cola_age_profile,
)
from populace_dynamics.estimates.parameters import COLASeries
from populace_dynamics.ss.params import SSAParameters

__all__ = [
    "A1_SPECIFICATION_PATH",
    "SCHEMA_VERSION",
    "TrackAInputs",
    "a1_parameter_block",
    "load_claiming_pmf",
    "run_track_a",
    "tr2008_baseline_cola",
    "tr2008_ssa_parameters",
]

SCHEMA_VERSION = "populace_dynamics.cola_track_a.run.v1"
_ROOT = Path(__file__).resolve().parents[3]
A1_SPECIFICATION_PATH = (
    _ROOT / "docs" / "design" / "urban2010_cola_comparison.md"
)
_TR2008_AWI_FIRST_YEAR = 1975


def a1_parameter_block(path: Path = A1_SPECIFICATION_PATH) -> dict:
    """The machine-readable block of the A1 draft (its section 21)."""

    text = Path(path).read_text(encoding="utf-8")
    match = re.search(
        r"## 21\. Machine-readable parameter block.*?```json\n(.*?)\n```",
        text,
        flags=re.S,
    )
    if match is None:
        raise ValueError(f"no section 21 JSON block in {path}")
    return json.loads(match.group(1))


def load_claiming_pmf(
    path: Path = psid2010.CLAIMING_REFERENCE_PATH,
) -> dict[tuple[str, int], dict[int, float]]:
    """The claim-age PMF the A3 builder uses, from the pinned table.

    The same construction as A3's input loader: the committed Supplement
    table, verified against A3's pinned SHA-256, conversions excluded,
    every sex and table year.  Track A restricts it to rows at or before
    ``TrackAConfig.claim_table_max_year`` when it builds the schedule.
    """

    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    if digest != psid2010.CLAIMING_REFERENCE_SHA256:
        raise ValueError(
            f"claiming reference {path} sha256 {digest} != the A3 pin"
        )
    reference = claiming.load_claim_age_reference(path)
    return {
        (sex, year): claiming.claim_age_pmf(
            sex, year, exclude_conversions=True, reference=reference
        )
        for sex in ("female", "male")
        for year in reference.years()
    }


def tr2008_ssa_parameters(
    base: SSAParameters,
    *,
    alternative: str = "intermediate",
    last_year: int = 2085,
) -> SSAParameters:
    """``base`` with the AWI replaced by TR2008's from 1975 (A2 default).

    A2's ``awi_path`` default is the pure TR2008 series (historical rows
    through 2006, TR2008 estimates from 2007).  Years before 1975, which
    TR2008 does not print, keep ``base``'s series (A2 gap "AWI before
    1975").  Bend points follow, because the oracle derives them from the
    AWI.  The contribution and benefit base is left as ``base`` has it;
    Track A draws no earnings after 2010, so only realized bases enter.
    """

    awi = {
        entry.year: entry.amount
        for entry in tr2008.awi_path(
            _TR2008_AWI_FIRST_YEAR, last_year, alternative=alternative
        )
    }
    nawi = {
        year: value
        for year, value in base.nawi.items()
        if year < _TR2008_AWI_FIRST_YEAR
    }
    nawi.update(awi)
    return dataclasses.replace(
        base,
        nawi=dict(sorted(nawi.items())),
        pe_us_revision=(
            f"{base.pe_us_revision}+tr2008_awi_{alternative}_"
            f"{_TR2008_AWI_FIRST_YEAR}_{last_year}"
        ),
    )


def tr2008_baseline_cola(
    realized: COLASeries,
    *,
    first_year: int = 2008,
    last_year: int = 2030,
    alternative: str = "intermediate",
) -> COLASeries:
    """The realized series with TR2008 rates from ``first_year`` on.

    A1 section 4: every rate that enters a reform ratio is TR2008's; the
    realized series supplies only the earlier years, which enter levels.
    """

    projected = {
        entry.determination_year: round(entry.percent / 100.0, 10)
        for entry in tr2008.cola_path(
            first_year, last_year, alternative=alternative
        )
    }
    return sb.extend_cola_series(
        realized,
        projected,
        projection_label=(
            f"TR2008 {alternative}: Table V.C1 through 2017, ultimate CPI "
            "(Table II.C1) after 2017, via populace_dynamics.data.tr2008."
            "cola_path"
        ),
    )


@dataclass(frozen=True)
class TrackAInputs:
    """Everything a Track A run reads besides its configuration."""

    cohort: TrackACohort
    params: SSAParameters
    baseline: COLASeries | sb.COLARateSource
    di_rates: DIEntitlementRates
    population_mortality: Any
    claiming_pmf: Mapping[tuple[str, int], Mapping[int, float]]
    provenance: Mapping[str, Any] = dataclasses.field(default_factory=dict)


def _check_floor(inputs: TrackAInputs, config: TrackAConfig) -> dict:
    """A1 section 4: every reduced rate through the horizon is positive."""

    last = config.reference_year
    minima = {}
    for row_id in config.rows:
        row = REGISTERED_ROWS[row_id]
        reform = sb.COLAReform(
            annual_reduction=config.annual_reduction,
            first_reduced_determination_year=(
                row.first_reduced_determination_year
            ),
        )
        minimum = sb.minimum_reformed_rate(
            inputs.baseline, reform, through_determination_year=last
        )
        if not minimum > 0.0:
            raise ValueError(
                f"{row_id}: a reduced rate through {last} is {minimum!r}; "
                "the A1 floor assertion requires every one to be positive"
            )
        minima[row_id] = minimum
    return minima


def _draw_diagnostics(
    result: ProjectionResult,
    death_log: Mapping[int, pd.DataFrame],
    cell_log: Mapping[int, pd.DataFrame],
    warnings_seen: int,
) -> dict[str, Any]:
    slices = result.slices
    final = slices[-1]
    flows = di_stock_flow(slices, weight_column="weight", death_log=death_log)
    groups = [
        (group.label, group.lower, group.upper) for group in DEFAULT_AGE_GROUPS
    ]
    prevalence = di_prevalence(
        final, age_groups=groups, weight_column="weight"
    )
    claimed = final["claim_year"].dropna().astype(int)
    infeasible = sum(
        int(frame["infeasible"].astype(bool).sum())
        for frame in cell_log.values()
        if len(frame)
    )
    return {
        "alive_by_year": {
            str(int(frame["year"].iloc[0])): int(len(frame))
            for frame in slices
            if len(frame)
        },
        "deaths_by_year": {
            str(year): int(len(frame))
            for year, frame in sorted(death_log.items())
        },
        "di_stock_flow": flows.to_dict(orient="records"),
        "di_prevalence_reference_year": prevalence.to_dict(orient="records"),
        "widowed_in_projection_alive_reference_year": int(
            final["widowed_in_projection"].astype(bool).sum()
        ),
        "claims_in_projection_alive_reference_year": int(
            (claimed > int(slices[0]["year"].iloc[0])).sum()
        ),
        "infeasible_mortality_cells": infeasible,
        "infeasible_mortality_cell_warnings": warnings_seen,
    }


def _reduced_increase_summary(rows: list[dict]) -> dict[str, Any]:
    if not rows:
        return {}
    frame = pd.DataFrame(
        [
            {
                "age": row["age_reference"],
                "basis": row["basis"],
                "count": row["reduced_increases"],
            }
            for row in rows
        ]
    )
    out = {}
    for group in DEFAULT_AGE_GROUPS:
        mask = frame["age"] >= group.lower
        if group.upper is not None:
            mask &= frame["age"] <= group.upper
        cell = frame[mask & frame["count"].notna()]
        counts = cell["count"].astype(int)
        out[group.label] = {
            "rows": int(mask.sum()),
            "by_basis": {
                str(key): int(value)
                for key, value in cell["basis"].value_counts().items()
            },
            "min": None if cell.empty else int(counts.min()),
            "median": None if cell.empty else float(np.median(counts)),
            "max": None if cell.empty else int(counts.max()),
        }
    return out


def run_track_a(
    inputs: TrackAInputs,
    *,
    config: TrackAConfig | None = None,
    registration_pointer: str | None = None,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Project, compute benefits and tabulate every configured row."""

    config = config or TrackAConfig()
    config.check_runnable()
    cohort = inputs.cohort
    if cohort.data_provenance == REGISTERED_REAL and not registration_pointer:
        raise ValueError(
            "no real-data statistic before the issue #42 registration "
            "comment exists; pass its pointer to run a registered_real cohort"
        )
    floor_minima = _check_floor(inputs, config)
    schedule = claiming_schedule(
        inputs.claiming_pmf, max_table_year=config.claim_table_max_year
    )
    fra_schedule = fra_schedule_from_parameters(inputs.params)
    initial = cohort.initial_slice
    metadata: dict[str, Any] = {}
    if SCHEDULED_ENTRIES_KEY in metadata:
        raise ValueError("Track A schedules no entrants")
    validate_projection_allocator(initial["person_id"], metadata)
    context = BenefitContext(
        cohort=cohort,
        params=inputs.params,
        baseline=inputs.baseline,
        config=config,
    )
    rows_by_row: dict[str, list[dict]] = {row: [] for row in config.rows}
    counters_by_row: dict[str, Counter] = {
        row: Counter() for row in config.rows
    }
    draws: dict[str, Any] = {}
    pia_cache: dict = {}
    for draw in config.draw_indices:
        if progress is not None:
            progress(f"draw {draw}: projecting")
        death_log: dict[int, pd.DataFrame] = {}
        cell_log: dict[int, pd.DataFrame] = {}
        modules = build_period_modules(
            roster_ids=cohort.roster_ids,
            population_model=inputs.population_mortality,
            di_rates=inputs.di_rates,
            fra_schedule=fra_schedule,
            schedule=schedule,
            death_log=death_log,
            cell_log=cell_log,
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", RuntimeWarning)
            result = ProjectionEngine(modules).project(
                initial,
                end_year=config.reference_year,
                draw_index=draw,
                metadata=metadata,
            )
        infeasible_warnings = sum(
            "DI-origin expected deaths exceed" in str(item.message)
            for item in caught
        )
        other = [
            str(item.message)
            for item in caught
            if "DI-origin expected deaths exceed" not in str(item.message)
        ]
        if other:
            raise RuntimeError(f"unexpected projection warnings: {other[:3]}")
        draws[str(draw)] = _draw_diagnostics(
            result, death_log, cell_log, infeasible_warnings
        )
        lookups = StateLookups(result, config.reference_year)
        for row_id in config.rows:
            rows, counters = reference_benefit_rows(
                result,
                draw=draw,
                row=REGISTERED_ROWS[row_id],
                context=context,
                pia_cache=pia_cache,
                lookups=lookups,
            )
            for row in rows:
                row["age_reference"] = config.reference_year - int(
                    row["birth_year"]
                )
            rows_by_row[row_id].extend(rows)
            counters_by_row[row_id].update(counters)
    tabulations: dict[str, Any] = {}
    for row_id in config.rows:
        row = REGISTERED_ROWS[row_id]
        if progress is not None:
            progress(f"{row_id}: tabulating")
        tabulation_config = ColaAgeProfileConfig(
            reference_year=config.reference_year,
            components=row.components,
            benefit_period=row.tabulation_benefit_period,
            headline_statistic=row.headline_statistic,
            draw_indices=config.draw_indices,
            floor_seeds=config.floor_seeds,
        )
        upstream = {
            "row": row_id,
            "field_changed": row.field_changed,
            "first_reduced_determination_year": (
                row.first_reduced_determination_year
            ),
            "exposure_clock": row.exposure_clock.value,
            "benefit_period": row.benefit_period.value,
            "benefit_scale": "annual_12_times_monthly",
            "rate_path": f"TR2008 {config.tr2008_alternative}",
            "behavior": "fixed_paths_shared_draws",
        }
        try:
            tabulation = tabulate_cola_age_profile(
                pd.DataFrame(rows_by_row[row_id]),
                data_provenance=cohort.data_provenance,
                config=tabulation_config,
                registration_pointer=registration_pointer,
                labels=cohort.labels,
                upstream_conventions=upstream,
            )
            status = "tabulated"
        except ColaTabulationError as error:
            tabulation = None
            status = f"refused: {type(error).__name__}: {error}"
        tabulations[row_id] = {
            "status": status,
            "row": row.as_dict(),
            "benefit_counters": dict(sorted(counters_by_row[row_id].items())),
            "reduced_increases_by_age_group": _reduced_increase_summary(
                rows_by_row[row_id]
            ),
            "tabulation": tabulation,
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "data_provenance": cohort.data_provenance,
        "registration_pointer": registration_pointer,
        "labels": list(cohort.labels),
        "config": config.as_dict(),
        "pending_decisions": pending_decisions(config),
        "rows_not_built": dict(ROWS_NOT_BUILT),
        "reduced_rate_minimum_by_row": floor_minima,
        "cohort": dict(cohort.diagnostics),
        "scheduled_entrants": 0,
        "draws": draws,
        "rows": tabulations,
        "inputs_provenance": dict(inputs.provenance),
    }
