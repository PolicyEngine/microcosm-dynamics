"""``tr2008_intermediate``: the registered tests' baseline, unchanged.

:class:`TR2008Legacy` adds no rate of its own.  Every input delegates to
the constructor the registered Track A and FRA-68 entry points already
call (``scripts/run_track_a_registered.py``, ``run_fra68_registered.py``
and the dry runs), so its outputs are those constructors' outputs, value
for value (differential tests in
``tests/baselines/test_legacy_differential.py``):

* COLA: :func:`~populace_dynamics.cola_track_a.runner.tr2008_baseline_cola`
  on the realized history
  (:func:`~populace_dynamics.estimates.parameters.load_cola_history`):
  realized rates before ``first``, TR2008 V.C1 through 2017 and the
  derived ultimate CPI (2.8) after (A1 section 4).  The 2008-vintage
  splice is the registered convention: TR2008 rates replace realized
  ones from 2008, so this baseline does not splice realized COLAs through
  the last actual year, unlike the 2026 baselines.
* AWI: :func:`~populace_dynamics.cola_track_a.runner.
  tr2008_ssa_parameters` (TR2008 from 1975 through 2085).
* Mortality: :func:`~populace_dynamics.cola_track_a.mortality.
  load_tr2008_mortality` (the A2 substitute, 2004 period table times the
  V.A1 ASADR ratio; base year 2004).
* Claiming: :func:`~populace_dynamics.cola_track_a.runner.
  load_claiming_pmf` (Supplement 2014 Table 6.B5.1, pinned by A3), read
  through rows at or before 2008 (``claim_table_max_year``).
* DI: :func:`~populace_dynamics.engine.di_entitlement_rates.
  load_di_entitlement_rates` (the 2008 fit).
* Fertility: none.  TR2008 publishes no age-specific fertility, and the
  registered projection tests draw no births, so :meth:`TR2008Legacy.asfr`
  and :meth:`TR2008Legacy.tfr` refuse with :class:`BaselineGapError`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.baselines.base import (
    AWI_FIRST_REPLACED_YEAR,
    SEXES,
    BaselineGapError,
    file_sha256,
    repo_relative,
)
from populace_dynamics.cohorts import psid2010
from populace_dynamics.cola_track_a.mortality import (
    Tr2008YearAwareMortality,
    load_tr2008_mortality,
)
from populace_dynamics.cola_track_a.runner import (
    load_claiming_pmf,
    tr2008_baseline_cola,
    tr2008_ssa_parameters,
)
from populace_dynamics.data import tr2008
from populace_dynamics.engine.di_entitlement_rates import (
    DEFAULT_INPUTS_PATH,
    MAX_AGE,
    NCHS_2000_PATH,
    DIEntitlementRates,
    DIEntitlementSpec,
    load_di_entitlement_rates,
)
from populace_dynamics.estimates.parameters import (
    COLA_FILE_SHA256,
    COLA_HISTORY_PATH,
    COLASeries,
    load_cola_history,
)
from populace_dynamics.ss.params import SSAParameters

__all__ = ["TR2008Legacy"]

#: ``tr2008_ssa_parameters``'s default last AWI year.
_LEGACY_AWI_LAST_YEAR = 2085


@dataclass(frozen=True)
class TR2008Legacy:
    """The 2008 Trustees intermediate baseline the registered tests use."""

    alternative: str = "intermediate"
    mortality_base_year: int = 2004
    claim_table_max_year: int = 2008
    name: str = "tr2008_intermediate"
    vintage: str = (
        "2008 Trustees Report, intermediate (registered projection tests)"
    )

    def __post_init__(self) -> None:
        if self.claim_table_max_year != 2008:
            raise ValueError(
                "the legacy baseline's claim-table cap is the registered "
                "2008 (TrackAConfig.claim_table_max_year)"
            )

    # -- COLA, CPI and AWI --------------------------------------------------
    def cola_rates(self, first: int, last: int) -> COLASeries:
        return tr2008_baseline_cola(
            load_cola_history(),
            first_year=first,
            last_year=last,
            alternative=self.alternative,
        )

    def cpiw_growth(self, year: int) -> float:
        """TR2008 single-year V.B1 CPI growth (CPI-W), 1960-2082."""
        return tr2008.economic_assumptions(
            year, alternative=self.alternative
        ).cpi

    def awi(self, first: int, last: int) -> dict[int, float]:
        return {
            entry.year: entry.amount
            for entry in tr2008.awi_path(
                first, last, alternative=self.alternative
            )
        }

    def ssa_parameters(self, params: SSAParameters) -> SSAParameters:
        return tr2008_ssa_parameters(params, alternative=self.alternative)

    # -- Mortality ----------------------------------------------------------
    def population_mortality(self, years: range) -> Tr2008YearAwareMortality:
        return load_tr2008_mortality(
            years,
            alternative=self.alternative,
            base_year=self.mortality_base_year,
        )

    def qx(self, year: int) -> dict[str, np.ndarray]:
        """The A2 substitute's probabilities by age, as the model applies.

        Evaluated through the model itself
        (:meth:`Tr2008YearAwareMortality.probabilities_for_year`), so it is
        the clipped product ``qx_2004 x ratio(year, group)``.
        """
        model = self.population_mortality(range(int(year), int(year) + 1))
        ages = np.arange(MAX_AGE + 1)
        out = {}
        for sex in SEXES:
            frame = pd.DataFrame({"age": ages, "sex": sex})
            values = model.probabilities_for_year(frame, int(year))
            values.setflags(write=False)
            out[sex] = values
        return out

    # -- Fertility ----------------------------------------------------------
    def tfr(self, year: int) -> float:
        raise BaselineGapError(
            "the tr2008_intermediate baseline supplies no fertility: the "
            "registered projection tests draw no births and no TR2008 "
            "accessor reads its V.A1 TFR column"
        )

    def asfr(self, year: int) -> dict[int, float]:
        raise BaselineGapError(
            "the tr2008_intermediate baseline supplies no age-specific "
            "fertility: TR2008 publishes none and the registered "
            "projection tests draw no births"
        )

    # -- Claiming and DI ----------------------------------------------------
    def claim_pmf(self) -> dict[tuple[str, int], dict[int, float]]:
        return load_claiming_pmf()

    def di_rates(
        self, spec: DIEntitlementSpec | None = None
    ) -> DIEntitlementRates:
        return load_di_entitlement_rates(spec or DIEntitlementSpec())

    # -- Provenance ---------------------------------------------------------
    def value_sources(self, year: int) -> dict[str, str]:
        year = int(year)
        cola = tr2008.cola_path(year, year, alternative=self.alternative)[0]
        awi = tr2008.awi_path(year, year, alternative=self.alternative)[0]
        return {
            "cola": (
                f"{cola.source} (realized history is used for determination "
                "years before the caller's first rate year)"
            ),
            "cpiw_growth": tr2008.economic_assumptions(
                year, alternative=self.alternative
            ).source,
            "awi": awi.source,
            "mortality": (
                "a2_substitute_qx2004_times_tr2008_v_a1_asadr_ratio_base_"
                f"{self.mortality_base_year}"
            ),
            "tfr": "gap_not_supplied",
            "asfr": "gap_not_supplied",
            "claiming": (
                "ssa_supplement_2014_6b5_1_row_"
                f"{min(year, self.claim_table_max_year)}"
            ),
            "di_rates": "di_entitlement_fit_2008",
        }

    def provenance(self) -> dict[str, Any]:
        tr2008.verify_files()
        return {
            "name": self.name,
            "vintage": self.vintage,
            "alternative": self.alternative,
            "constructors": {
                "cola": "cola_track_a.runner.tr2008_baseline_cola",
                "awi": "cola_track_a.runner.tr2008_ssa_parameters",
                "mortality": "cola_track_a.mortality.load_tr2008_mortality",
                "claiming": "cola_track_a.runner.load_claiming_pmf",
                "di": "engine.di_entitlement_rates.load_di_entitlement_rates",
            },
            "splices": {
                "cola": (
                    "realized history before the caller's first rate year "
                    "(A1 section 4: 2008), TR2008 V.C1 to 2017, derived "
                    "ultimate CPI after 2017"
                ),
                "awi": (
                    f"oracle NAWI before {AWI_FIRST_REPLACED_YEAR}; TR2008 "
                    f"V.C1/VI.F6 {AWI_FIRST_REPLACED_YEAR}-"
                    f"{_LEGACY_AWI_LAST_YEAR}"
                ),
                "claiming": f"rows at or before {self.claim_table_max_year}",
            },
            "mortality_base_year": self.mortality_base_year,
            "claim_table_max_year": self.claim_table_max_year,
            "gaps": [
                "no fertility (TR2008 publishes no ASFR; the registered "
                "projection tests draw no births)",
                "DI rates are the 2008 fit (A4); DI death follows the "
                "population mortality in multiplier mode",
                tr2008.MORTALITY_SUBSTITUTE_STANDING,
            ],
            "files_sha256": {
                **{
                    f"data/external/tr2008/{name}": digest
                    for name, digest in tr2008.FILE_SHA256.items()
                },
                "data/external/ssa_cola_history.json": COLA_FILE_SHA256,
                "data/external/ssa_claim_ages_2014supplement.json": (
                    psid2010.CLAIMING_REFERENCE_SHA256
                ),
                repo_relative(DEFAULT_INPUTS_PATH): file_sha256(
                    DEFAULT_INPUTS_PATH
                ),
                repo_relative(NCHS_2000_PATH): file_sha256(NCHS_2000_PATH),
            },
            "cola_history_path": repo_relative(COLA_HISTORY_PATH),
        }
