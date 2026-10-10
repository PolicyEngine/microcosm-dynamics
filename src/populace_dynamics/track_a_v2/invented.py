"""Invented people AND invented parameter bundles for §17's dry run.

No file-based population or parameter loader is called here. The generator
is the existing invented A3 fixture (cola_track_a/invented.py:119–132).
Zero recovery deliberately supplies supported continuous spells; rejected
spell histories are exercised separately, never silently removed.
"""

import numpy as np

from populace_dynamics.cohorts import psid2010
from populace_dynamics.cola_track_a import (
    TrackAConfig,
    TrackAInputs,
    invented,
    prepare_track_a_cohort,
)
from populace_dynamics.cola_track_a.mortality import Tr2008YearAwareMortality
from populace_dynamics.engine.di_entitlement_rates import (
    MAX_AGE,
    DIEntitlementRates,
    DIEntitlementSpec,
)
from populace_dynamics.estimates.parameters import COLASeries
from populace_dynamics.ss.params import SSAParameters


def invented_parameters() -> SSAParameters:
    """An invented level bundle with the inherited cohort FRA schedule."""
    return SSAParameters(
        nawi={
            year: 2800 * 1.04 ** (year - 1951) for year in range(1951, 2061)
        },
        wage_base={1951: 1e9},
        pia_factors=(0.9, 0.32, 0.15),
        fra_months_by_birth_year=[
            (1900, 780),
            (1938, 782),
            (1939, 784),
            (1940, 786),
            (1941, 788),
            (1942, 790),
            (1943, 792),
            (1955, 794),
            (1956, 796),
            (1957, 798),
            (1958, 800),
            (1959, 802),
            (1960, 804),
        ],
        early_monthly_rates=(5 / 900, 5 / 1200),
        early_first_bracket_months=36,
        delayed_credit_by_birth_year=[(1900, 0.08)],
        pe_us_revision="INVENTED DATA - NOT A COMPARISON",
    )


def invented_inputs(seed: int = 7) -> TrackAInputs:
    """Build a single 2011-wave invented population without external reads."""
    config = TrackAConfig(rows=tuple(f"R{i}" for i in range(6)))
    pmf = invented.invented_claiming_pmf()
    raw = invented.invented_psid2010_inputs(seed=seed, claiming_pmf=pmf)
    cohort = prepare_track_a_cohort(
        psid2010.build_psid2010_cohort(raw),
        data_provenance="invented",
        config=config,
    )
    shape = (2, MAX_AGE + 1)
    incidence = np.zeros(shape)
    incidence[:, 18:70] = 0.006
    rates = DIEntitlementRates(
        spec=DIEntitlementSpec(),
        incidence=incidence,
        recovery_attained=np.zeros(shape),
        death_attained=np.full(shape, 0.002),
        population_reference_death=np.full(shape, 0.002),
        recovery_select=None,
        death_select=None,
        recovery_level_factor=1.0,
        death_level_factor=1.0,
    )
    qx = np.minimum(0.0001 * np.exp(0.085 * np.arange(MAX_AGE + 1)), 1)
    mortality = Tr2008YearAwareMortality(
        qx_by_sex={"female": qx * 0.8, "male": qx},
        ratio_by_year={year: (1.0, 1.0) for year in range(2011, 2031)},
        alternative="INVENTED",
        base_year=2004,
    )
    return TrackAInputs(
        cohort=cohort,
        params=invented_parameters(),
        baseline=COLASeries(
            by_determination_year={year: 0.025 for year in range(1979, 2032)},
            provenance={"invented": True},
        ),
        di_rates=rates,
        population_mortality=mortality,
        claiming_pmf=pmf,
        provenance={"invented": True, "seed": seed},
    )
