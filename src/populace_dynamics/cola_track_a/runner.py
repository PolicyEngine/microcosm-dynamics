"""Run the Track A assembly: K draws, benefits per row, A7 tabulation.

:func:`run_track_a` projects each population's opening state once per
draw with the unmodified ``engine.loop.ProjectionEngine`` (draw ``k`` has
root entropy ``5200 + k`` and person-keyed streams), computes every
registered row's baseline and reform benefits from its population's one
projection (so both scenarios share every simulated path), and tabulates
each row with the A7 five-group statistic.  Rows R0-R5 read the 2011-wave
cohort (opening 2010, 20 periods); R6 reads the 2009-wave cohort (opening
2008, 22 periods), passed in ``TrackAInputs.additional_cohorts``.  Nothing
is scheduled as an entrant.  The runner still passes the projection
metadata to
``engine.entrant_schedule.validate_projection_allocator``; that metadata
carries no allocator, so the check accepts it without testing anything,
and the loop builds its own allocator from ``max(person_id) + 1``.  No
step creates a person, so no allocated identifier is ever used.

The configuration names the TR2008 alternative, the first TR2008 rate
year, the mortality base year, the DI specification and the claim-table
cap; the inputs are built separately.  Every result records whether the
two agree (``parameter_consistency``).  On request, and always for a
``registered_real`` cohort, the input values themselves are compared with
the committed sources those settings name: the COLA path, the AWI, the
population mortality, the DI rates and the claim-age table, and (through
:mod:`~populace_dynamics.cola_track_a.statutory`) the realized COLA
history before the first TR2008 rate year and every statutory parameter
the oracle reads beyond the AWI.  A ``registered_real`` run refuses any
disagreement.

Governance interlock: a cohort whose ``data_provenance`` is
``"registered_real"`` is refused unless a registration pointer (the issue
#42 comment that must precede the one-shot run) is supplied; A7 refuses
the same case independently.  The label must also agree with the source
provenance the A3 builder recorded (``TrackACohort.source_provenance``):
``"invented"`` needs an invented source and ``"registered_real"`` a
source read from PSID files, so a relabelled cohort is refused here as
well as in
:func:`~populace_dynamics.cola_track_a.opening.prepare_track_a_cohort`.
Invented cohorts carry the invented-data label on every output.
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
    builder_defaults,
    max_rulings,
    rulings_departures,
)
from populace_dynamics.cola_track_a.mortality import (
    Tr2008YearAwareMortality,
    load_tr2008_mortality,
)
from populace_dynamics.cola_track_a.opening import TrackACohort
from populace_dynamics.cola_track_a.statutory import statutory_value_checks
from populace_dynamics.data import tr2008
from populace_dynamics.engine.di_entitlement import (
    di_prevalence,
    di_stock_flow,
    fra_schedule_from_parameters,
)
from populace_dynamics.engine.di_entitlement_rates import (
    DIEntitlementRates,
    SelectUltimateTable,
    load_di_entitlement_rates,
)
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
    INVENTED,
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
    """The machine-readable block of the A1 specification (section 21)."""

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
    """Everything a Track A run reads besides its configuration.

    ``cohort`` is the 2011-wave population of R0-R5; the 2009-wave
    population of R6 goes in ``additional_cohorts``.  The population
    mortality must cover every projection year of every population.
    """

    cohort: TrackACohort
    params: SSAParameters
    baseline: COLASeries | sb.COLARateSource
    di_rates: DIEntitlementRates
    population_mortality: Any
    claiming_pmf: Mapping[tuple[str, int], Mapping[int, float]]
    provenance: Mapping[str, Any] = dataclasses.field(default_factory=dict)
    additional_cohorts: tuple[TrackACohort, ...] = ()

    def cohorts_by_wave(self) -> dict[int, TrackACohort]:
        """Every supplied cohort by anchor wave (one per wave)."""
        cohorts: dict[int, TrackACohort] = {}
        for cohort in (self.cohort, *self.additional_cohorts):
            wave = int(cohort.anchor_wave)
            if wave in cohorts:
                raise ValueError(f"two cohorts for anchor wave {wave}")
            cohorts[wave] = cohort
        return cohorts


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


def _tr2008_value_checks(
    inputs: TrackAInputs, config: TrackAConfig
) -> dict[str, dict[str, Any]]:
    """Compare the baseline COLA and the AWI with the A2 TR2008 capture.

    Reads the committed TR2008 capture through :mod:`~populace_dynamics.
    data.tr2008`, so :func:`run_track_a` calls it only when asked or for a
    ``registered_real`` run.
    """

    alternative = config.tr2008_alternative
    first, last = config.tr2008_first_rate_year, config.reference_year
    cola_mismatch: dict[str, Any] = {}
    for entry in tr2008.cola_path(first, last, alternative=alternative):
        year = entry.determination_year
        try:
            runtime = 100.0 * inputs.baseline.rate_for_determination_year(year)
        except (KeyError, ValueError):
            runtime = None
        if runtime is None or not np.isclose(
            runtime, entry.percent, rtol=0.0, atol=1e-9
        ):
            cola_mismatch[str(year)] = {
                "tr2008_percent": entry.percent,
                "runtime_percent": runtime,
            }
    awi_mismatch: dict[str, Any] = {}
    for entry in tr2008.awi_path(
        _TR2008_AWI_FIRST_YEAR, last, alternative=alternative
    ):
        runtime = inputs.params.nawi.get(entry.year)
        if runtime is None or not np.isclose(
            runtime, entry.amount, rtol=1e-12, atol=0.0
        ):
            awi_mismatch[str(entry.year)] = {
                "tr2008": entry.amount,
                "runtime": runtime,
            }
    return {
        "cola_path": {
            "expected": (
                f"TR2008 {alternative} rates, determination years "
                f"{first}-{last}"
            ),
            "consistent": not cola_mismatch,
            "mismatched_years": cola_mismatch,
        },
        "awi": {
            "expected": (
                f"TR2008 {alternative} AWI, {_TR2008_AWI_FIRST_YEAR}-{last}"
            ),
            "consistent": not awi_mismatch,
            "mismatched_years": awi_mismatch,
        },
    }


#: The fitted arrays and factors of an A4 ``DIEntitlementRates``.
_DI_RATE_FIELDS = (
    "incidence",
    "recovery_attained",
    "death_attained",
    "population_reference_death",
    "recovery_select",
    "death_select",
    "recovery_level_factor",
    "death_level_factor",
)


def _same_values(left: Any, right: Any) -> bool:
    """Exact equality of rate arrays, factors or select tables (NaN = NaN)."""

    if left is None or right is None:
        return left is None and right is None
    if isinstance(left, SelectUltimateTable) or isinstance(
        right, SelectUltimateTable
    ):
        return (
            isinstance(left, SelectUltimateTable)
            and isinstance(right, SelectUltimateTable)
            and _same_values(left.select, right.select)
            and _same_values(left.ultimate, right.ultimate)
            and left.first_select_age == right.first_select_age
            and left.last_select_age == right.last_select_age
        )
    left_array = np.asarray(left, dtype=np.float64)
    right_array = np.asarray(right, dtype=np.float64)
    return left_array.shape == right_array.shape and bool(
        np.array_equal(left_array, right_array, equal_nan=True)
    )


def _capped_pmf(
    pmf: Mapping[tuple[str, int], Mapping[int, float]], cap: int
) -> dict[tuple[str, int], dict[int, float]]:
    return {
        (str(sex), int(year)): {
            int(age): float(value) for age, value in values.items()
        }
        for (sex, year), values in pmf.items()
        if int(year) <= int(cap)
    }


def _committed_value_checks(
    inputs: TrackAInputs, config: TrackAConfig
) -> dict[str, dict[str, Any]]:
    """Compare mortality, DI rates and the claim table with the captures.

    The configuration's mortality settings name the A2 substitute
    (:func:`~populace_dynamics.cola_track_a.mortality.
    load_tr2008_mortality` for every projection year), its DI
    specification names the rates A4 fits from the committed inputs
    (:func:`~populace_dynamics.engine.di_entitlement_rates.
    load_di_entitlement_rates`), and its claim-table cap names the rows of
    the A3-pinned claim-age table (:func:`load_claiming_pmf`) that the
    projection reads.  Each input must equal them exactly; a population
    mortality that is not the A2 substitute fails.  Reads committed
    files, so :func:`run_track_a` calls it only when asked or for a
    ``registered_real`` run.
    """

    years = range(
        min(config.start_years.values()) + 1, config.reference_year + 1
    )
    expected_mortality = load_tr2008_mortality(
        years,
        alternative=config.tr2008_alternative,
        base_year=config.mortality_base_year,
    )
    model = inputs.population_mortality
    mortality_mismatch: list[str] = []
    if isinstance(model, Tr2008YearAwareMortality):
        for sex, values in expected_mortality.qx_by_sex.items():
            if not _same_values(model.qx_by_sex.get(sex), values):
                mortality_mismatch.append(f"qx_{sex}")
        for year in years:
            runtime = model.ratio_by_year.get(year)
            if runtime is None or not _same_values(
                runtime, expected_mortality.ratio_by_year[year]
            ):
                mortality_mismatch.append(f"ratio_{year}")
        if tuple(model.bands) != tuple(expected_mortality.bands):
            mortality_mismatch.append("bands")
    else:
        mortality_mismatch.append("not_the_a2_substitute")
    expected_di = load_di_entitlement_rates(config.di_spec)
    di_mismatch = [
        name
        for name in _DI_RATE_FIELDS
        if not _same_values(
            getattr(inputs.di_rates, name), getattr(expected_di, name)
        )
    ]
    cap = config.claim_table_max_year
    runtime_pmf = _capped_pmf(inputs.claiming_pmf, cap)
    expected_pmf = _capped_pmf(load_claiming_pmf(), cap)
    pmf_mismatch = sorted(
        f"{sex}|{year}"
        for sex, year in set(runtime_pmf) | set(expected_pmf)
        if runtime_pmf.get((sex, year)) != expected_pmf.get((sex, year))
    )
    return {
        "mortality_values": {
            "expected": (
                f"A2 substitute, TR2008 {config.tr2008_alternative}, base "
                f"year {config.mortality_base_year}, projection years "
                f"{years.start}-{years.stop - 1}"
            ),
            "consistent": not mortality_mismatch,
            "mismatched": mortality_mismatch,
            "runtime_class": type(model).__name__,
        },
        "di_rates": {
            "expected": "load_di_entitlement_rates(config.di_spec)",
            "consistent": not di_mismatch,
            "mismatched": di_mismatch,
        },
        "claiming_pmf": {
            "expected": (
                "the A3-pinned claim-age table (load_claiming_pmf), rows "
                f"at or before {cap}"
            ),
            "consistent": not pmf_mismatch,
            "mismatched_rows": pmf_mismatch,
        },
    }


def _parameter_consistency(
    inputs: TrackAInputs,
    config: TrackAConfig,
    cohorts: Mapping[int, TrackACohort],
    *,
    compare_committed_values: bool,
) -> dict[str, Any]:
    """Whether the inputs are the parameters the config labels the run with.

    ``config`` names the TR2008 alternative, the first TR2008 rate year,
    the mortality base year, the DI specification and the claim-table
    cap, and the result reports them as the run's conventions; the
    inputs are built separately.  Each check compares the two.  A
    ``registered_real`` run refuses any mismatch (:func:`run_track_a`);
    an invented run, whose tests use invented parameters, records it.
    Without ``compare_committed_values`` only the labels are compared
    (the DI specification, the A2 model's alternative and base year, the
    A3 claim-table cap of every population), and a population mortality
    that is not the A2 substitute is recorded as a gap by
    ``_mortality_record`` only.  With it, the COLA path, the AWI, the
    mortality probabilities, the DI rates and the claim-age table are
    compared value by value with the committed captures, a population
    mortality that is not the A2 substitute is a mismatch, and
    :func:`~populace_dynamics.cola_track_a.statutory.statutory_value_checks`
    binds the realized COLA history before the first TR2008 rate year and
    the statutory parameters (bend points, contribution and benefit base,
    PIA factors, FRA, early reduction, delayed credits and the auxiliary
    constants) to their committed sources.
    """

    alternative = config.tr2008_alternative
    checks: dict[str, dict[str, Any]] = {}
    if compare_committed_values:
        checks.update(_tr2008_value_checks(inputs, config))
        checks.update(_committed_value_checks(inputs, config))
        checks.update(
            statutory_value_checks(
                inputs.params,
                inputs.baseline,
                first_tr2008_rate_year=config.tr2008_first_rate_year,
                reference_year=config.reference_year,
                last_earnings_year=max(config.start_years.values()),
                tr2008_alternative=alternative,
            )
        )
    checks.update(
        {
            "di_spec": {
                "expected": config.di_spec.as_dict(),
                "consistent": inputs.di_rates.spec == config.di_spec,
                "runtime": inputs.di_rates.spec.as_dict(),
            },
        }
    )
    model = inputs.population_mortality
    if isinstance(model, Tr2008YearAwareMortality):
        checks["mortality"] = {
            "expected": {
                "alternative": alternative,
                "base_year": config.mortality_base_year,
            },
            "consistent": (
                model.alternative == alternative
                and model.base_year == config.mortality_base_year
            ),
            "runtime": {
                "alternative": model.alternative,
                "base_year": model.base_year,
            },
        }
    a3_caps = {
        str(wave): cohort.diagnostics.get("a3_spec", {}).get(
            "claim_table_max_year"
        )
        for wave, cohort in cohorts.items()
    }
    checks["claim_table_max_year"] = {
        "expected": config.claim_table_max_year,
        "consistent": all(
            cap == config.claim_table_max_year for cap in a3_caps.values()
        ),
        "runtime_a3_opening_imputation_by_anchor_wave": a3_caps,
    }
    return {
        "committed_values_compared": compare_committed_values,
        "consistent": all(check["consistent"] for check in checks.values()),
        "checks": checks,
    }


def _mortality_record(model: Any) -> dict[str, Any]:
    """What population mortality the run used, and the gap if it is flat."""

    year_aware = isinstance(model, Tr2008YearAwareMortality)
    record: dict[str, Any] = {
        "class": type(model).__name__,
        "year_aware": year_aware,
    }
    if year_aware:
        record["provenance"] = dict(model.provenance)
    else:
        record["gap"] = (
            "population mortality has no year axis (for example the "
            "engine's AgeSexMortalityModel); TR2008 mortality improvement "
            "over 2011-2030 is not applied"
        )
    return record


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


def _selected_baseline(row: dict, components: tuple[str, ...]) -> float:
    """The row's baseline amount summed over the selected components."""

    return sum(
        row["benefit_components"].get(name, {}).get("base", 0.0)
        for name in components
    )


def _reduced_increase_summary(
    rows: list[dict], components: tuple[str, ...]
) -> dict[str, Any]:
    """Reduced-increase counts of the row's members, by age group.

    A7 keeps a person in a row only when the benefit summed over the row's
    components is positive, so a component-restricted row (R5) drops a
    person whose benefit rests only on another worker's record; the
    summary counts the same members (``rows`` sums over draws).
    """

    members = [row for row in rows if _selected_baseline(row, components) > 0]
    if not members:
        return {}
    frame = pd.DataFrame(
        [
            {
                "age": row["age_reference"],
                "basis": row["basis"],
                "count": row["reduced_increases"],
            }
            for row in members
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


_REDUCED_INCREASE_DEFINITION = (
    "per member row (all draws pooled): the reduced increases in one PIA "
    "for the row's payment year.  An opening-stock person's count is on "
    "the opening record's clock.  A projected person's count is that of "
    "the own worker benefit when there is one, otherwise that of the "
    "deceased worker's PIA behind the widow(er)'s benefit.  A dually "
    "entitled person's spouse's or widow(er)'s amount rests on another "
    "PIA whose count can differ and is not shown here"
)


_COMPONENT_SHARE_DEFINITION = (
    "per draw and age group: each selected component's share of the "
    "weighted baseline benefit total, sum_i w_i B_base[i, c] / sum_i w_i "
    "B_base[i], over the rows the tabulation receives; reported as the "
    "mean over draws in which the total is positive.  A1 section 16 asks "
    "for 'weighted component shares' without saying whether persons or "
    "amounts are weighted; this reports amounts, so a dually entitled "
    "person's components each count at their own amount"
)


def _component_shares(
    rows: list[dict],
    components: tuple[str, ...],
    draw_indices: tuple[int, ...],
) -> dict[str, Any]:
    """A1 section 16 cell diagnostic: weighted component shares."""

    frame = pd.DataFrame(
        [
            {
                "draw": row["draw"],
                "age": row["age_reference"],
                **{
                    name: row["weight"]
                    * row["benefit_components"].get(name, {}).get("base", 0.0)
                    for name in components
                },
            }
            for row in rows
        ],
        columns=["draw", "age", *components],
    )
    by_group: dict[str, Any] = {}
    for group in DEFAULT_AGE_GROUPS:
        mask = frame["age"] >= group.lower
        if group.upper is not None:
            mask &= frame["age"] <= group.upper
        per_draw = []
        for draw in draw_indices:
            totals = frame.loc[
                mask & (frame["draw"] == draw), components
            ].sum()
            total = float(totals.sum())
            if total > 0.0:
                per_draw.append(totals / total)
        by_group[group.label] = {
            "draws_defined": len(per_draw),
            "mean_share": (
                None
                if not per_draw
                else {
                    name: float(np.mean([shares[name] for shares in per_draw]))
                    for name in components
                }
            ),
        }
    return {"definition": _COMPONENT_SHARE_DEFINITION, "by_group": by_group}


#: The A3 source provenance kind each ``data_provenance`` label needs.
_SOURCE_KIND_BY_LABEL = {
    INVENTED: psid2010.INVENTED,
    REGISTERED_REAL: psid2010.PSID_FILES,
}


def _check_source_provenance(
    cohorts: Mapping[int, TrackACohort], data_provenance: str
) -> None:
    """Refuse a cohort whose label contradicts its A3 source provenance.

    :func:`~populace_dynamics.cola_track_a.opening.prepare_track_a_cohort`
    already refuses the contradiction; this repeats it for a
    ``TrackACohort`` whose label was replaced after preparation, so a
    cohort built from PSID files cannot run as invented data (and skip
    the issue #42 registration check).
    """

    expected = _SOURCE_KIND_BY_LABEL[data_provenance]
    for wave, cohort in cohorts.items():
        kind = dict(cohort.source_provenance).get("kind")
        if kind != expected:
            raise ValueError(
                f"the anchor-wave {wave} cohort is labelled "
                f"{data_provenance!r} but its A3 source provenance is "
                f"{kind!r} (expected {expected!r}); a cohort's label must "
                "agree with the data it was built from"
            )


def _population_cohorts(
    inputs: TrackAInputs, config: TrackAConfig
) -> dict[int, TrackACohort]:
    """The cohort of every population the configured rows project."""

    supplied = inputs.cohorts_by_wave()
    missing = {
        wave: config.rows_for_wave(wave)
        for wave in config.anchor_waves
        if wave not in supplied
    }
    if missing:
        raise ValueError(
            "no cohort for the populations of rows "
            + "; ".join(
                f"{list(rows)} (anchor wave {wave})"
                for wave, rows in missing.items()
            )
            + ": pass it in TrackAInputs (the 2009-wave cohort of R6 in "
            "additional_cohorts) or leave those rows out of config.rows"
        )
    cohorts = {wave: supplied[wave] for wave in config.anchor_waves}
    first = next(iter(cohorts.values()))
    for wave, cohort in cohorts.items():
        if cohort.data_provenance != first.data_provenance or tuple(
            cohort.labels
        ) != tuple(first.labels):
            raise ValueError(
                f"the anchor-wave {wave} cohort's provenance or labels "
                "differ from the others; one run tabulates one kind of data"
            )
    return cohorts


def _project_population(
    cohort: TrackACohort,
    inputs: TrackAInputs,
    config: TrackAConfig,
    *,
    schedule: Any,
    fra_schedule: Any,
    progress: Callable[[str], None] | None,
) -> tuple[dict[int, ProjectionResult], dict[str, Any]]:
    """Project one population once per draw; return results and diagnostics."""

    initial = cohort.initial_slice
    metadata: dict[str, Any] = {}
    if SCHEDULED_ENTRIES_KEY in metadata:
        raise ValueError("Track A schedules no entrants")
    validate_projection_allocator(initial["person_id"], metadata)
    results: dict[int, ProjectionResult] = {}
    diagnostics: dict[str, Any] = {}
    for draw in config.draw_indices:
        if progress is not None:
            progress(
                f"anchor wave {cohort.anchor_wave}, draw {draw}: projecting"
            )
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
        diagnostics[str(draw)] = _draw_diagnostics(
            result, death_log, cell_log, infeasible_warnings
        )
        results[draw] = result
    return results, diagnostics


def run_track_a(
    inputs: TrackAInputs,
    *,
    config: TrackAConfig | None = None,
    registration_pointer: str | None = None,
    progress: Callable[[str], None] | None = None,
    check_committed_parameters: bool = False,
) -> dict[str, Any]:
    """Project, compute benefits and tabulate every configured row.

    ``check_committed_parameters`` compares the baseline COLA, the AWI,
    the population mortality, the DI rates, the claim-age table, the
    realized COLA history and the statutory parameters with the committed
    sources that ``config`` names (always done for a ``registered_real``
    cohort, which refuses any mismatch).  Each population (anchor wave)
    is projected once per draw and every row of that population reads the
    same projection.
    """

    config = config or TrackAConfig()
    config.check_runnable()
    cohorts = _population_cohorts(inputs, config)
    data_provenance = next(iter(cohorts.values())).data_provenance
    labels = tuple(next(iter(cohorts.values())).labels)
    if data_provenance == REGISTERED_REAL and not registration_pointer:
        raise ValueError(
            "no real-data statistic before the issue #42 registration "
            "comment exists; pass its pointer to run a registered_real cohort"
        )
    real = data_provenance == REGISTERED_REAL
    departures = rulings_departures(config)
    if real and departures:
        raise ValueError(
            f"the configuration departs from Max's rulings on {departures} "
            "(2026-09-23, d074/d075); a registered run follows every ruling"
        )
    floor_minima = _check_floor(inputs, config)
    consistency = _parameter_consistency(
        inputs,
        config,
        cohorts,
        compare_committed_values=real or check_committed_parameters,
    )
    if real and not consistency["consistent"]:
        failed = sorted(
            name
            for name, check in consistency["checks"].items()
            if not check["consistent"]
        )
        raise ValueError(
            "the inputs differ from the parameters the configuration "
            f"reports for this run: {failed}; a registered run refuses "
            "a mismatch"
        )
    _check_source_provenance(cohorts, data_provenance)
    schedule = claiming_schedule(
        inputs.claiming_pmf, max_table_year=config.claim_table_max_year
    )
    fra_schedule = fra_schedule_from_parameters(inputs.params)
    rows_by_row: dict[str, list[dict]] = {row: [] for row in config.rows}
    counters_by_row: dict[str, Counter] = {
        row: Counter() for row in config.rows
    }
    draws: dict[str, Any] = {}
    for wave, cohort in cohorts.items():
        results, draws[str(wave)] = _project_population(
            cohort,
            inputs,
            config,
            schedule=schedule,
            fra_schedule=fra_schedule,
            progress=progress,
        )
        context = BenefitContext(
            cohort=cohort,
            params=inputs.params,
            baseline=inputs.baseline,
            config=config,
        )
        pia_cache: dict = {}
        for draw, result in results.items():
            lookups = StateLookups(result, config.reference_year)
            for row_id in config.rows_for_wave(wave):
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
        population = row.population
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
            "population_wave": population.anchor_wave,
            "population_weight": population.weight_variable,
            "population_start_year": population.start_year,
            "population_periods": population.periods(config.reference_year),
            "family_unit_id": population.family_unit_variable,
        }
        try:
            tabulation = tabulate_cola_age_profile(
                pd.DataFrame(rows_by_row[row_id]),
                data_provenance=data_provenance,
                config=tabulation_config,
                registration_pointer=registration_pointer,
                labels=labels,
                upstream_conventions=upstream,
            )
        except ColaTabulationError as error:
            tabulation = None
            status = f"refused: {type(error).__name__}: {error}"
        else:
            undefined = tabulation["undefined_cells"]
            status = (
                "tabulated"
                if not undefined
                else "tabulated with undefined cells: "
                + ", ".join(
                    f"{cell['group']} {cell['statistic']} "
                    f"({cell['n_defined_draws']} of "
                    f"{len(config.draw_indices)} draws defined)"
                    for cell in undefined
                )
            )
        tabulations[row_id] = {
            "status": status,
            "row": row.as_dict(),
            "benefit_counters": dict(sorted(counters_by_row[row_id].items())),
            "reduced_increases_definition": _REDUCED_INCREASE_DEFINITION,
            "reduced_increases_by_age_group": _reduced_increase_summary(
                rows_by_row[row_id], row.components
            ),
            "component_shares_by_age_group": _component_shares(
                rows_by_row[row_id], row.components, config.draw_indices
            ),
            "tabulation": tabulation,
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "data_provenance": data_provenance,
        "registration_pointer": registration_pointer,
        "labels": list(labels),
        "config": config.as_dict(),
        "max_rulings": max_rulings(config),
        "builder_defaults": builder_defaults(config),
        "rows_not_built": dict(ROWS_NOT_BUILT),
        "reduced_rate_minimum_by_row": floor_minima,
        "parameter_consistency": consistency,
        "cohorts": {
            str(wave): {
                **dict(cohort.diagnostics),
                "source_provenance": dict(cohort.source_provenance),
            }
            for wave, cohort in cohorts.items()
        },
        "scheduled_entrants": 0,
        "population_mortality": _mortality_record(inputs.population_mortality),
        # The oracle's statutory parameter revision; the committed-value
        # checks (parameter_consistency, when run) bind the values.
        "ssa_parameters_revision": inputs.params.pe_us_revision,
        "draws": draws,
        "rows": tabulations,
        "inputs_provenance": dict(inputs.provenance),
    }
