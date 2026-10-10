"""``cbo2026_long_term``: CBO's 2026 long-term demographic and economic paths.

Every CBO value comes from B1's pinned accessor
(:mod:`populace_dynamics.data.cbo2026`; January 2026 demographic
projections, February 2026 ten-year and long-term economics, September
2026 covered workers and earnings) and keeps its tags and builder
defaults there.  CBO publishes no COLA, CPI-W or AWI, and its
demographic files start in 2021, so this baseline splices realized
values first (:mod:`~populace_dynamics.baselines.realized`):

* **COLA.**  The committed realized history through 2022, the TR2026
  V.C1 historical rows for 2023 and 2024 and the 2025 actual
  (2.8 percent), then from 2026 annual CPI-U growth as the COLA proxy
  (cbo2026 builder defaults ``cpiw_equals_cpiu_growth``,
  ``cola_equals_annual_cpiu_growth``, ``ten_year_cpiu_then_long_term_
  growth`` and, after 2056, ``hold_2056_economic_growth``).  The proxy is
  an annual-average growth, not the statutory third-quarter comparison.
* **CPI-W.**  TR2026 V.B1 through 2025 (historical through 2024; the
  2025 value is TR2026's estimate, tagged so), CPI-U growth from 2026.
* **AWI.**  TR2026 VI.G1 realized values from 1975 through 2024, then
  the CBO analog (cbo2026 builder defaults ``awi_bridge_2025_2026_real_
  earnings_times_cpiu`` and ``awi_growth_of_covered_earnings_per_
  worker``), which starts from the same 2024 actual
  (:func:`~populace_dynamics.baselines.realized.check_awi_anchor`).
* **Mortality.**  CBO's printed rate per 1,000 divided by 1,000 is
  ``q`` (B1 verified the q reading against every published 2026-2099
  life expectancy; the m reading fails), ages 0-119 with ``q(119) = 1``,
  2021-2099; age 120 repeats age 119.  Before 2021, where CBO publishes
  nothing, the OACT TR2026 historical period ``q`` is spliced (builder
  default ``cbo_mortality_before_2021_oact_historical``, awaiting
  ratification).  After 2099 nothing is supplied.
* **Fertility.**  CBO's all-women single-age (14-49) ASFR as published,
  2021-2099, and CBO's TFR (published from 2026; the ASFR sum before).
* **Claiming and DI.**  :mod:`~populace_dynamics.baselines.common2026`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from populace_dynamics.baselines.base import (
    AWI_FIRST_REPLACED_YEAR,
    SEXES,
    BaselineYearAwareMortality,
    pad_to_max_age,
    replace_awi,
    splice_cola_percent,
)
from populace_dynamics.baselines.common2026 import (
    DI_GAP,
    Vintage2026Inputs,
)
from populace_dynamics.baselines.realized import (
    FIRST_SPLICED_COLA_YEAR,
    LAST_ACTUAL_AWI_YEAR,
    LAST_ACTUAL_COLA_YEAR,
    REALIZED_HISTORY_LAST_YEAR,
    check_awi_anchor,
    check_cola_request,
    check_realized_cola_agreement,
    realized_awi,
    realized_cola_percent,
)
from populace_dynamics.data import cbo2026, tr2026
from populace_dynamics.estimates.parameters import (
    COLASeries,
    load_cola_history,
)
from populace_dynamics.ss.params import SSAParameters

__all__ = ["CBO2026LongTerm"]

#: CBO's economic paths (as extended by B1) end in this year.
LAST_ECONOMIC_YEAR = 2100
#: CBO's demographic projections cover 2021-2099.
FIRST_DEMOGRAPHIC_YEAR = 2021
LAST_DEMOGRAPHIC_YEAR = 2099
_MORTALITY_SPLICE_DEFAULT = "cbo_mortality_before_2021_oact_historical"


@dataclass(frozen=True)
class CBO2026LongTerm(Vintage2026Inputs):
    """CBO's 2026 long-term baseline (see module docstring)."""

    name: str = "cbo2026_long_term"
    vintage: str = (
        "CBO 2026 long-term projections (demographics January 2026, "
        "economics February 2026, covered earnings September 2026)"
    )

    # -- COLA, CPI and AWI --------------------------------------------------
    def cola_rates(self, first: int, last: int) -> COLASeries:
        """History through 2022, V.C1 2023-2025, CBO's CPI-U proxy after.

        ``first`` is validated but does not move the splice (realized
        increases are kept through 2025; :func:`~populace_dynamics.
        baselines.realized.check_cola_request`).
        """
        first, last = check_cola_request(first, last)
        if last > LAST_ECONOMIC_YEAR:
            raise KeyError(
                f"CBO2026 projects no COLA after {LAST_ECONOMIC_YEAR}"
            )
        check_realized_cola_agreement()
        projected = {
            year: realized_cola_percent(year)[0]
            for year in range(
                FIRST_SPLICED_COLA_YEAR, min(last, LAST_ACTUAL_COLA_YEAR) + 1
            )
        }
        if last > LAST_ACTUAL_COLA_YEAR:
            projected.update(
                {
                    entry.determination_year: entry.percent
                    for entry in cbo2026.cola_path(
                        LAST_ACTUAL_COLA_YEAR + 1, last
                    )
                }
            )
        return splice_cola_percent(
            load_cola_history(),
            projected,
            label=(
                "CBO 2026 long-term: realized increases through "
                f"{LAST_ACTUAL_COLA_YEAR} (TR2026 V.C1 historical rows and "
                "the 2025 actual), then annual CPI-U growth as the COLA "
                "proxy (cbo2026 builder defaults), via "
                "populace_dynamics.baselines.cbo2026_long_term"
            ),
        )

    def cpiw_growth(self, year: int) -> float:
        year = int(year)
        if year <= LAST_ACTUAL_COLA_YEAR:
            return tr2026.cpiw_growth(year)
        return cbo2026.cpiw_growth(year)

    def awi(self, first: int, last: int) -> dict[int, float]:
        first, last = int(first), int(last)
        if first > last:
            raise ValueError("first must not exceed last")
        check_awi_anchor()
        out = {
            year: realized_awi(year)[0]
            for year in range(first, min(last, LAST_ACTUAL_AWI_YEAR) + 1)
        }
        if last > LAST_ACTUAL_AWI_YEAR:
            out.update(
                {
                    entry.year: entry.amount
                    for entry in cbo2026.awi(
                        max(first, LAST_ACTUAL_AWI_YEAR + 1), last
                    )
                }
            )
        return out

    def ssa_parameters(self, params: SSAParameters) -> SSAParameters:
        return replace_awi(
            params,
            self.awi(AWI_FIRST_REPLACED_YEAR, LAST_ECONOMIC_YEAR),
            revision_suffix=(
                f"cbo2026_awi_analog_{AWI_FIRST_REPLACED_YEAR}_"
                f"{LAST_ECONOMIC_YEAR}"
            ),
        )

    # -- Mortality ----------------------------------------------------------
    def qx(self, year: int) -> dict[str, np.ndarray]:
        year = int(year)
        if year > LAST_DEMOGRAPHIC_YEAR:
            raise KeyError(
                f"CBO2026 projects no mortality after {LAST_DEMOGRAPHIC_YEAR}"
            )
        out = {}
        for sex in SEXES:
            source = (
                cbo2026.mortality(year, sex)
                if year >= FIRST_DEMOGRAPHIC_YEAR
                else tr2026.death_probability(year, sex)
            )
            values = pad_to_max_age(source)
            values.setflags(write=False)
            out[sex] = values
        return out

    def population_mortality(self, years: range) -> BaselineYearAwareMortality:
        return BaselineYearAwareMortality(
            baseline=self.name,
            qx_by_year={int(year): self.qx(year) for year in years},
            provenance={
                "basis": (
                    "CBO 2026 deaths per 1,000 / 1,000 read as q (B1 "
                    f"check), {FIRST_DEMOGRAPHIC_YEAR}-"
                    f"{LAST_DEMOGRAPHIC_YEAR}; OACT TR2026 historical q "
                    f"before {FIRST_DEMOGRAPHIC_YEAR} "
                    f"({_MORTALITY_SPLICE_DEFAULT})"
                ),
                "accessor": "populace_dynamics.data.cbo2026.mortality",
                "ages_above_table": "age 120 repeats age 119 (q = 1)",
                "age_convention": "start-of-year age (year - 1 - birth_year)",
                "years": [int(years.start), int(years.stop) - 1],
                "files_verified_by": (
                    "data.cbo2026.FILE_SHA256 and data.tr2026.FILE_SHA256"
                ),
            },
        )

    # -- Fertility ----------------------------------------------------------
    def tfr(self, year: int) -> float:
        return cbo2026.tfr(year)

    def asfr(self, year: int) -> dict[int, float]:
        return cbo2026.asfr(year, "all")

    # -- Provenance ---------------------------------------------------------
    def value_sources(self, year: int) -> dict[str, str]:
        year = int(year)
        if year <= LAST_ACTUAL_COLA_YEAR:
            cola = realized_cola_percent(year)[1]
            cpiw = tr2026.value_provenance("cpiw_growth", year).source
        else:
            cola = cbo2026.value_provenance("cola", year).source
            cpiw = cbo2026.value_provenance("cpiw_growth", year).source
        awi = (
            realized_awi(year)[1]
            if year <= LAST_ACTUAL_AWI_YEAR
            else cbo2026.value_provenance("awi", year).source
        )
        demographic = FIRST_DEMOGRAPHIC_YEAR <= year <= LAST_DEMOGRAPHIC_YEAR
        return {
            "cola": cola,
            "cpiw_growth": cpiw,
            "awi": awi,
            "mortality": (
                cbo2026.value_provenance("mortality", year, sex="male").source
                if demographic
                else (
                    f"{_MORTALITY_SPLICE_DEFAULT}:"
                    + tr2026.value_provenance(
                        "death_probability", year, sex="male"
                    ).source
                    if year < FIRST_DEMOGRAPHIC_YEAR
                    else "not_supplied"
                )
            ),
            "tfr": (
                cbo2026.value_provenance("tfr", year).source
                if demographic
                else "not_supplied"
            ),
            "asfr": (
                cbo2026.value_provenance("asfr", year).source
                if demographic
                else "not_supplied"
            ),
            "claiming": (
                "ssa_supplement_2026_6b5_1_row_"
                f"{min(max(year, 1998), self.claim_table_max_year)}"
            ),
            "di_rates": "di_entitlement_fit_2008",
        }

    def provenance(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "vintage": self.vintage,
            "splices": {
                "cola": (
                    "committed realized history through "
                    f"{REALIZED_HISTORY_LAST_YEAR}; realized TR2026 V.C1 "
                    f"rows {FIRST_SPLICED_COLA_YEAR}-2024 and the "
                    f"{LAST_ACTUAL_COLA_YEAR} actual; CBO annual CPI-U growth "
                    f"{LAST_ACTUAL_COLA_YEAR + 1}-{LAST_ECONOMIC_YEAR}. "
                    "Realized rates run through the last actual "
                    "determination year, whatever the caller's first rate "
                    "year"
                ),
                "cpiw_growth": (
                    "TR2026 V.B1 through 2025 (2025 estimated); CBO CPI-U "
                    "growth after"
                ),
                "awi": (
                    f"oracle NAWI before {AWI_FIRST_REPLACED_YEAR}; TR2026 "
                    f"VI.G1 realized {AWI_FIRST_REPLACED_YEAR}-"
                    f"{LAST_ACTUAL_AWI_YEAR} (the last actual year); CBO "
                    f"analog {LAST_ACTUAL_AWI_YEAR + 1}-{LAST_ECONOMIC_YEAR} "
                    f"from the same {LAST_ACTUAL_AWI_YEAR} actual"
                ),
                "mortality": (
                    "OACT TR2026 historical q before "
                    f"{FIRST_DEMOGRAPHIC_YEAR}; CBO q "
                    f"{FIRST_DEMOGRAPHIC_YEAR}-{LAST_DEMOGRAPHIC_YEAR}"
                ),
                "claiming": (
                    "Supplement 2026 Table 6.B5.1, rows 1998-"
                    f"{self.claim_table_max_year}; later years snap to "
                    f"{self.claim_table_max_year}"
                ),
            },
            "builder_defaults_awaiting_ratification": {
                **{
                    name: "data.cbo2026 builder default"
                    for name in cbo2026.PENDING_RATIFICATION
                },
                _MORTALITY_SPLICE_DEFAULT: (
                    "OACT TR2026 historical period q (SSA area) for years "
                    "before CBO's first demographic year, 2021"
                ),
                "claim_table_last_row": (
                    f"the 2026 Supplement's {self.claim_table_max_year} row "
                    "(SSA: current-year rows are revised each update) is "
                    "used for every later year"
                ),
                "awi_first_replaced_year": (
                    f"{AWI_FIRST_REPLACED_YEAR}, the legacy baseline's year"
                ),
            },
            "gaps": [
                DI_GAP,
                "CBO publishes no COLA, CPI-W or AWI: proxies are tagged "
                "derived (cbo2026 builder defaults)",
                f"no demographic inputs after {LAST_DEMOGRAPHIC_YEAR} and "
                f"no CBO fertility before {FIRST_DEMOGRAPHIC_YEAR}",
            ],
            "files_sha256": {
                **self.shared_files_sha256(),
                **self.cbo_files_sha256(),
            },
            "captured_sources_sha256": self.captured_sources_sha256(
                include_cbo=True
            ),
        }
