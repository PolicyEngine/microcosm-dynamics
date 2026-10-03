"""One factory for Track A inputs under a selectable baseline.

Five places build :class:`~populace_dynamics.cola_track_a.runner.
TrackAInputs` by hand from the same TR2008 constructors
(``scripts/run_track_a_registered.py``, ``scripts/run_fra68_registered.
py``, ``scripts/track_a_dry_run.py``, ``scripts/fra68_dry_run.py`` and
``track_a_v2.protocol.load_registered_inputs``).  Those files are
registered entry points and are not edited; :func:`build_track_a_inputs`
composes the same inputs from a :class:`~populace_dynamics.baselines.
base.Baseline` instead.  Under the default ``tr2008_intermediate``
baseline every input it returns equals the hand-built one value for
value (``tests/baselines/test_track_a_inputs.py``: the Track A and FRA-68
dry runs' inputs), and the configuration is not touched, so
``TrackAConfig.as_dict()`` and every artifact field it feeds are
unchanged.  The baseline's name, vintage and file hashes are recorded
under ``provenance["baseline"]``.

Scope of the 2026 baselines.  ``run_track_a`` (``cola_track_a/runner.
py``, not edited) is hard-wired to TR2008 in three ways, so the 2026
baselines are exposed for invented-data projections only:

1. A ``registered_real`` run compares the COLA path, AWI, mortality, DI
   rates and claim table with the TR2008 captures and refuses any
   mismatch.  :func:`build_track_a_inputs` refuses ``registered_real``
   under any other baseline first: a real-data run under a non-legacy
   baseline needs its own registered entry point and an issue #42
   registration (future work).
2. The run artifact labels the rate path ``"TR2008 <alternative>"``
   (A7 upstream conventions) and records a population mortality that is
   not the A2 class as having "no year axis".  Under a 2026 baseline both
   labels are wrong; ``inputs_provenance["baseline"]`` (this module's
   record, which the runner copies into the result) is authoritative and
   says so in ``runner_label_caveat``.
3. A1's floor assertion (``runner._check_floor``) requires every reduced
   COLA from the first reduced year (2009 or 2010) to be positive.  The
   2026 baselines keep realized increases, which were zero for
   determination years 2009, 2010 and 2015, so ``run_track_a`` refuses a
   one-point cut under them.  Running exercise 1 under a 2026 baseline
   needs a floor ruling (``NegativeRatePolicy.FLOOR_AT_ZERO`` or later
   first years).  :func:`project_track_a` runs the projection alone
   (mortality, DI, claiming) on invented cohorts under any baseline, the
   path the invented-data smoke tests use.

The claim table: ``run_track_a`` reads claim rows at or before
``config.claim_table_max_year``.  :func:`track_a_config_for` returns the
configuration a baseline needs (the legacy one unchanged; a 2026 one
with the cap at its last row, 2025), and :func:`build_track_a_inputs`
refuses a configuration whose cap is not the baseline's, which would
otherwise silently read an old row of the new table.  Pass the same
configuration to ``run_track_a`` or :func:`project_track_a`.

Invented cohorts: when no cohorts are passed, an ``invented`` call
builds them as the dry runs do (``scripts/track_a_dry_run.py``
``_prepared_cohort``): the INVENTED generator
(:func:`~populace_dynamics.cola_track_a.invented.
invented_psid2010_inputs`) with seed :data:`INVENTED_SEED` and the
baseline's claim-age table, the A3 builder and
:func:`~populace_dynamics.cola_track_a.opening.prepare_track_a_cohort`.
A ``registered_real`` cohort is never built here: the registered entry
point's cohort code prepares it and passes it in, so this module never
reads PSID files.
"""

from __future__ import annotations

import dataclasses
import warnings
from collections.abc import Mapping, MutableMapping
from typing import Any

import pandas as pd

from populace_dynamics.baselines.base import Baseline
from populace_dynamics.baselines.legacy import TR2008Legacy
from populace_dynamics.cohorts import psid2010
from populace_dynamics.cola_track_a import invented
from populace_dynamics.cola_track_a.adapters import (
    build_period_modules,
    claiming_schedule,
)
from populace_dynamics.cola_track_a.config import TrackAConfig
from populace_dynamics.cola_track_a.opening import (
    TrackACohort,
    prepare_track_a_cohort,
    track_a_cohort_sha256,
)
from populace_dynamics.cola_track_a.runner import TrackAInputs
from populace_dynamics.engine.di_entitlement import (
    fra_schedule_from_parameters,
)
from populace_dynamics.engine.loop import ProjectionEngine, ProjectionResult
from populace_dynamics.estimates.cola_age_profile import (
    INVENTED,
    REGISTERED_REAL,
)
from populace_dynamics.ss.params import SSAParameters, load_ssa_parameters

__all__ = [
    "INVENTED_SEED",
    "RUNNER_LABEL_CAVEAT",
    "build_track_a_inputs",
    "invented_track_a_cohorts",
    "project_track_a",
    "track_a_config_for",
]

#: The invented generator's seed in both dry runs (``--seed`` default).
INVENTED_SEED = 20260922
RUNNER_LABEL_CAVEAT = (
    "cola_track_a.runner labels the rate path 'TR2008 <alternative>' and "
    "records a population mortality that is not the A2 class as having no "
    "year axis; under a non-legacy baseline both labels are wrong and this "
    "baseline record is authoritative"
)
#: The warning the DI-aware mortality adapter emits for an infeasible
#: cell; ``run_track_a`` counts it rather than failing, and so does
#: :func:`project_track_a`.
_INFEASIBLE_CELL_WARNING = "DI-origin expected deaths exceed"


def track_a_config_for(
    config: TrackAConfig, baseline: Baseline
) -> TrackAConfig:
    """``config`` with the claim-table cap ``baseline`` reads.

    The legacy baseline returns ``config`` itself (the registered cap,
    2008), so a default configuration's ``as_dict()`` is unchanged.
    """
    if config.claim_table_max_year == baseline.claim_table_max_year:
        return config
    return dataclasses.replace(
        config, claim_table_max_year=baseline.claim_table_max_year
    )


def invented_track_a_cohorts(
    config: TrackAConfig,
    baseline: Baseline,
    *,
    seed: int = INVENTED_SEED,
) -> dict[int, TrackACohort]:
    """INVENTED cohorts for every anchor wave ``config`` projects.

    The dry runs' construction (module docstring), with ``baseline``'s
    claim-age table as the generator's claiming parameter.  Under the
    legacy baseline that table is ``load_claiming_pmf()``, the one the
    dry runs pass, so the cohorts are the dry runs' cohorts.
    """
    claiming_pmf = baseline.claim_pmf()
    cohorts = {}
    for wave in config.anchor_waves:
        raw = invented.invented_psid2010_inputs(
            seed=seed, claiming_pmf=claiming_pmf, anchor_wave=wave
        )
        a3 = psid2010.build_psid2010_cohort(
            raw, psid2010.Psid2010CohortSpec(anchor_wave=wave)
        )
        cohorts[wave] = prepare_track_a_cohort(
            a3, data_provenance=INVENTED, config=config
        )
    return cohorts


def _check_legacy_conventions(
    config: TrackAConfig, baseline: TR2008Legacy
) -> None:
    for field, expected in (
        ("tr2008_alternative", baseline.alternative),
        ("mortality_base_year", baseline.mortality_base_year),
    ):
        if getattr(config, field) != expected:
            raise ValueError(
                f"config.{field} is {getattr(config, field)!r} but the "
                f"legacy baseline uses {expected!r}"
            )


def _checked_cohorts(
    config: TrackAConfig,
    cohorts: Mapping[int, TrackACohort],
    data_provenance: str,
) -> dict[int, TrackACohort]:
    waves = config.anchor_waves
    missing = [wave for wave in waves if wave not in cohorts]
    if missing:
        raise ValueError(f"no prepared cohort for anchor waves {missing}")
    for wave in waves:
        cohort = cohorts[wave]
        if int(cohort.anchor_wave) != int(wave):
            raise ValueError(
                f"the cohort given for wave {wave} has anchor wave "
                f"{cohort.anchor_wave}"
            )
        if cohort.data_provenance != data_provenance:
            raise ValueError(
                f"the anchor-wave {wave} cohort is labelled "
                f"{cohort.data_provenance!r}, not {data_provenance!r}"
            )
    return {wave: cohorts[wave] for wave in waves}


def build_track_a_inputs(
    config: TrackAConfig,
    baseline: Baseline,
    *,
    data_provenance: str,
    cohorts: Mapping[int, TrackACohort] | None = None,
    base_params: SSAParameters | None = None,
    invented_seed: int = INVENTED_SEED,
    provenance: Mapping[str, Any] | None = None,
) -> TrackAInputs:
    """The Track A inputs for ``config`` under ``baseline``.

    ``data_provenance`` is ``"invented"`` or ``"registered_real"`` (the
    latter under the legacy baseline only).  ``cohorts`` holds a
    prepared cohort for every anchor wave the configured rows project;
    the first wave's goes in ``cohort`` and the others in
    ``additional_cohorts``, as the dry runs do.  Omitted for an
    ``invented`` call, the INVENTED cohorts are built
    (:func:`invented_track_a_cohorts`, seed ``invented_seed``); a
    ``registered_real`` call must pass the cohorts its entry point's
    cohort code prepared.  ``base_params`` are the oracle's statutory
    parameters before the baseline replaces the AWI (default
    :func:`~populace_dynamics.ss.params.load_ssa_parameters`, the
    policyengine-us checkout every builder reads).  ``provenance`` holds
    the caller's other records (statutory capture, script name); it may
    not carry a ``"baseline"`` key.

    The inputs: ``params = baseline.ssa_parameters(base_params)``;
    ``baseline = baseline.cola_rates(config.tr2008_first_rate_year,
    config.reference_year)``; ``di_rates = baseline.di_rates(config.
    di_spec)``; population mortality for every projection year of every
    population (the earliest start year plus one through the reference
    year); ``claiming_pmf = baseline.claim_pmf()``.
    """
    if data_provenance not in (INVENTED, REGISTERED_REAL):
        raise ValueError(
            f"data_provenance must be {INVENTED!r} or {REGISTERED_REAL!r}"
        )
    if not isinstance(baseline, Baseline):
        raise TypeError("baseline must implement the Baseline protocol")
    legacy = isinstance(baseline, TR2008Legacy)
    if data_provenance == REGISTERED_REAL and not legacy:
        raise ValueError(
            f"a registered_real run under the {baseline.name!r} baseline "
            "is not supported: run_track_a checks a real run against the "
            "TR2008 captures, so a real-data run under a non-legacy "
            "baseline needs its own registered entry point and an issue "
            "#42 registration (future work)"
        )
    if legacy:
        _check_legacy_conventions(config, baseline)
    if config.claim_table_max_year != baseline.claim_table_max_year:
        raise ValueError(
            f"config.claim_table_max_year is {config.claim_table_max_year} "
            f"but the {baseline.name!r} baseline reads claim rows through "
            f"{baseline.claim_table_max_year}; pass "
            "track_a_config_for(config, baseline)"
        )
    extra = dict(provenance or {})
    if "baseline" in extra:
        raise ValueError("provenance['baseline'] is written by this factory")
    built_invented = cohorts is None
    if cohorts is None:
        if data_provenance != INVENTED:
            raise ValueError(
                "a registered_real call must pass the cohorts its entry "
                "point's cohort code prepared; this factory builds only "
                "INVENTED cohorts and never reads PSID files"
            )
        cohorts = invented_track_a_cohorts(
            config, baseline, seed=invented_seed
        )
    cohorts = _checked_cohorts(config, cohorts, data_provenance)
    if base_params is None:
        base_params = load_ssa_parameters()
    first_projection_year = min(config.start_years.values()) + 1
    mortality = baseline.population_mortality(
        range(first_projection_year, config.reference_year + 1)
    )
    di_rates = baseline.di_rates(config.di_spec)
    cola = baseline.cola_rates(
        config.tr2008_first_rate_year, config.reference_year
    )
    params = baseline.ssa_parameters(base_params)
    record = {
        **baseline.provenance(),
        "cola_series_provenance": dict(cola.provenance),
        "mortality": dict(mortality.provenance),
        "di_rates_sha256": {
            key: value
            for key, value in di_rates.provenance.items()
            if key.endswith("sha256")
        },
        "ssa_parameters": params.pe_us_revision,
        "claim_table_max_year": baseline.claim_table_max_year,
        "first_rate_year": config.tr2008_first_rate_year,
        "projection_years": [first_projection_year, config.reference_year],
    }
    if built_invented:
        record["invented_cohorts"] = {
            "seed": int(invented_seed),
            "builder": "baselines.track_a.invented_track_a_cohorts",
        }
    if not legacy:
        record["runner_label_caveat"] = RUNNER_LABEL_CAVEAT
    primary, *others = cohorts.values()
    return TrackAInputs(
        cohort=primary,
        params=params,
        baseline=cola,
        di_rates=di_rates,
        population_mortality=mortality,
        claiming_pmf=baseline.claim_pmf(),
        provenance={**extra, "baseline": record},
        additional_cohorts=tuple(others),
    )


def _check_invented(cohort: TrackACohort) -> None:
    """``run_track_a``'s source checks for an invented cohort, repeated.

    The label, the A3 source kind, the seal and the generator's persons,
    weights and family units must all say INVENTED, so no PSID cohort
    is projected here however it was relabelled.
    """
    recorded = dict(cohort.source_provenance)
    if cohort.data_provenance != INVENTED:
        raise ValueError(
            f"project_track_a projects INVENTED cohorts only; the "
            f"anchor-wave {cohort.anchor_wave} cohort is labelled "
            f"{cohort.data_provenance!r}.  A real-data projection runs "
            "through a registered entry point after its issue #42 "
            "registration"
        )
    if recorded.get("kind") != psid2010.INVENTED:
        raise ValueError(
            f"the anchor-wave {cohort.anchor_wave} cohort's A3 source "
            f"provenance is {recorded.get('kind')!r}, not invented"
        )
    if cohort.seal is None or cohort.seal != track_a_cohort_sha256(cohort):
        raise ValueError(
            f"the anchor-wave {cohort.anchor_wave} cohort does not match "
            "the seal prepare_track_a_cohort set"
        )
    invented.check_invented_population(
        persons=cohort.persons,
        initial_slice=cohort.initial_slice,
        career_ids=cohort.careers.keys(),
        seed=recorded.get("seed"),
        anchor_wave=int(cohort.anchor_wave),
    )


def project_track_a(
    inputs: TrackAInputs,
    config: TrackAConfig,
    *,
    draw_index: int = 0,
    death_log: (
        MutableMapping[int, MutableMapping[int, pd.DataFrame]] | None
    ) = None,
) -> dict[int, ProjectionResult]:
    """Project every INVENTED population once through ``config``'s year.

    The projection ``run_track_a`` runs for one draw (the runner's
    ``build_period_modules`` adapters: DI-aware population mortality, the
    DI step, claiming from the inputs' table capped at
    ``config.claim_table_max_year``, no earnings, births or entrants),
    without the A1 floor assertion, the benefit computation or the A7
    tabulation, so it runs under any baseline.  Invented cohorts only
    (:func:`_check_invented`); results are keyed by anchor wave.
    ``death_log[wave]``, when given, receives that population's death
    records by year.  The DI-aware mortality adapter's infeasible-cell
    warnings are absorbed, as ``run_track_a`` counts them; any other
    warning is an error.
    """
    recorded = dict(inputs.provenance).get("baseline", {})
    cap = recorded.get("claim_table_max_year")
    if cap is not None and int(cap) != config.claim_table_max_year:
        raise ValueError(
            f"the inputs were built for claim rows through {cap} but "
            f"config.claim_table_max_year is {config.claim_table_max_year}; "
            "pass the configuration the inputs were built with"
        )
    cohorts = inputs.cohorts_by_wave()
    missing = [wave for wave in config.anchor_waves if wave not in cohorts]
    if missing:
        raise ValueError(f"no cohort for anchor waves {missing}")
    schedule = claiming_schedule(
        inputs.claiming_pmf, max_table_year=config.claim_table_max_year
    )
    fra_schedule = fra_schedule_from_parameters(inputs.params)
    results = {}
    for wave in config.anchor_waves:
        cohort = cohorts[wave]
        _check_invented(cohort)
        log: MutableMapping[int, pd.DataFrame] = {}
        modules = build_period_modules(
            roster_ids=cohort.roster_ids,
            population_model=inputs.population_mortality,
            di_rates=inputs.di_rates,
            fra_schedule=fra_schedule,
            schedule=schedule,
            death_log=log,
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", RuntimeWarning)
            results[wave] = ProjectionEngine(modules).project(
                cohort.initial_slice,
                end_year=config.reference_year,
                draw_index=int(draw_index),
                metadata={},
            )
        other = [
            str(item.message)
            for item in caught
            if _INFEASIBLE_CELL_WARNING not in str(item.message)
        ]
        if other:
            raise RuntimeError(f"unexpected projection warnings: {other[:3]}")
        if death_log is not None:
            death_log[wave] = log
    return results
