"""``tr2026_intermediate``: the 2026 Trustees Report intermediate paths.

Every value comes from B1's pinned accessors
(:mod:`populace_dynamics.data.tr2026`, Tables V.C1, V.B1, VI.G1 and V.A1
and OACT's DeathProbsE files, captured 2026-10-01) or from the files
named below; nothing is typed in.

* **COLA.**  The committed realized history (``ssa_cola_history.json``)
  through 2022, then V.C1: historical rows for 2023 and 2024, the 2025
  actual (2.8 percent, footnote g) and the intermediate projection
  2026-2035, then annual-average CPI-W growth from V.B1 for 2036-2100
  (B1's builder default ``post_2035_cola_annual_cpiw``, awaiting
  ratification, tagged ``derived_annual_cpiw_cola``).  Realized rates
  therefore run through 2025 whatever the caller's first rate year is
  (:mod:`~populace_dynamics.baselines.realized`).
* **AWI.**  VI.G1 from 1975 (historical through 2024, the last actual;
  2025 estimated; projected 2026-2100); the oracle's NAWI before 1975.
* **Mortality.**  OACT's period ``q`` by single age (0-119) and sex:
  historical tables through 2023, Alternative II from 2024 to 2100;
  age 120 repeats age 119, whose published ``q`` (below one) is kept.
* **Fertility.**  V.A1 TFR (1940-2100).  TR2026 publishes no age
  schedule, so ASFR is derived (tag ``derived_shape_scaled_to_v_a1_
  tfr``): a fixed single-age shape scaled each year to the TFR
  (:mod:`~populace_dynamics.baselines.asfr`).  The default shape is
  NCHS 2024 spread to single ages by the mean-preserving monotone
  interpolation; CBO's single-year shape is the registered alternative
  (``asfr_shape="cbo2026"``, 2021-2099 only).  Both are builder defaults
  awaiting ratification.
* **Claiming and DI.**  :mod:`~populace_dynamics.baselines.common2026`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from populace_dynamics.baselines.asfr import (
    SHAPES,
    AsfrShape,
    age_shape,
    scale_shape_to_tfr,
)
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
    check_cola_request,
    check_realized_cola_agreement,
)
from populace_dynamics.data import tr2026
from populace_dynamics.estimates.parameters import (
    COLASeries,
    load_cola_history,
)
from populace_dynamics.ss.params import SSAParameters

__all__ = ["TR2026Intermediate"]

#: The last year TR2026's single-year tables and q files project.
LAST_YEAR = 2100
_LAST_HISTORICAL_Q_YEAR = 2023
_ASFR_TAG = "derived_shape_scaled_to_v_a1_tfr"


@dataclass(frozen=True)
class TR2026Intermediate(Vintage2026Inputs):
    """The 2026 Trustees intermediate baseline (see module docstring)."""

    asfr_shape: AsfrShape = "nchs2024"
    name: str = "tr2026_intermediate"
    vintage: str = "2026 Trustees Report, intermediate (released 2026-06-09)"

    def __post_init__(self) -> None:
        if self.asfr_shape not in SHAPES:
            raise ValueError(f"asfr_shape must be one of {SHAPES}")

    # -- COLA, CPI and AWI --------------------------------------------------
    def cola_rates(self, first: int, last: int) -> COLASeries:
        """History through 2022, V.C1 2023-2035, V.B1 CPI-W after.

        ``first`` is validated but does not move the splice (realized
        increases are kept through 2025; :func:`~populace_dynamics.
        baselines.realized.check_cola_request`).
        """
        first, last = check_cola_request(first, last)
        check_realized_cola_agreement()
        projected = {
            entry.determination_year: entry.percent
            for entry in tr2026.cola_path(FIRST_SPLICED_COLA_YEAR, last)
        }
        return splice_cola_percent(
            load_cola_history(),
            projected,
            label=(
                "TR2026 intermediate: Table V.C1 (historical through 2024, "
                f"actual {LAST_ACTUAL_COLA_YEAR}, projected 2026-2035), "
                "then V.B1 annual-average CPI-W growth from 2036 (builder "
                "default post_2035_cola_annual_cpiw), via "
                "populace_dynamics.baselines.tr2026_intermediate"
            ),
        )

    def cpiw_growth(self, year: int) -> float:
        return tr2026.cpiw_growth(year)

    def awi(self, first: int, last: int) -> dict[int, float]:
        return {entry.year: entry.amount for entry in tr2026.awi(first, last)}

    def ssa_parameters(self, params: SSAParameters) -> SSAParameters:
        return replace_awi(
            params,
            self.awi(AWI_FIRST_REPLACED_YEAR, LAST_YEAR),
            revision_suffix=(
                f"tr2026_awi_intermediate_{AWI_FIRST_REPLACED_YEAR}_"
                f"{LAST_YEAR}"
            ),
        )

    # -- Mortality ----------------------------------------------------------
    def qx(self, year: int) -> dict[str, np.ndarray]:
        out = {}
        for sex in SEXES:
            values = pad_to_max_age(tr2026.death_probability(year, sex))
            values.setflags(write=False)
            out[sex] = values
        return out

    def population_mortality(self, years: range) -> BaselineYearAwareMortality:
        return BaselineYearAwareMortality(
            baseline=self.name,
            qx_by_year={int(year): self.qx(year) for year in years},
            provenance={
                "basis": (
                    "OACT TR2026 DeathProbsE q by single age and sex: "
                    f"historical through {_LAST_HISTORICAL_Q_YEAR}, "
                    "Alternative II after"
                ),
                "accessor": "populace_dynamics.data.tr2026.death_probability",
                "ages_above_table": "age 120 repeats age 119",
                "age_convention": "start-of-year age (year - 1 - birth_year)",
                "years": [int(years.start), int(years.stop) - 1],
                "files_verified_by": "data.tr2026.FILE_SHA256",
            },
        )

    # -- Fertility ----------------------------------------------------------
    def tfr(self, year: int) -> float:
        return tr2026.tfr(year)

    def asfr(self, year: int) -> dict[int, float]:
        return scale_shape_to_tfr(
            age_shape(self.asfr_shape, int(year)), self.tfr(year)
        )

    # -- Provenance ---------------------------------------------------------
    def value_sources(self, year: int) -> dict[str, str]:
        year = int(year)
        (cola,) = tr2026.cola_path(year, year)
        (awi,) = tr2026.awi(year, year)
        return {
            "cola": cola.source,
            "cpiw_growth": tr2026.value_provenance("cpiw_growth", year).source,
            "awi": awi.source,
            "mortality": tr2026.value_provenance(
                "death_probability", year, sex="male"
            ).source,
            "tfr": tr2026.value_provenance("tfr", year).source,
            "asfr": f"{_ASFR_TAG}:{self.asfr_shape}",
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
            "asfr_shape": self.asfr_shape,
            "splices": {
                "cola": (
                    "committed realized history through "
                    f"{REALIZED_HISTORY_LAST_YEAR}; TR2026 V.C1 from "
                    f"{FIRST_SPLICED_COLA_YEAR} (historical through 2024, "
                    f"actual {LAST_ACTUAL_COLA_YEAR}, projected 2026-2035); "
                    "V.B1 CPI-W growth 2036-2100. Realized rates run through "
                    f"{LAST_ACTUAL_COLA_YEAR}, the last actual determination "
                    "year, whatever the caller's first rate year"
                ),
                "awi": (
                    f"oracle NAWI before {AWI_FIRST_REPLACED_YEAR}; TR2026 "
                    f"VI.G1 {AWI_FIRST_REPLACED_YEAR}-{LAST_YEAR}: realized "
                    f"through {LAST_ACTUAL_AWI_YEAR}, the last actual year, "
                    f"estimated {LAST_ACTUAL_AWI_YEAR + 1}, projected after"
                ),
                "mortality": (
                    f"OACT historical q through {_LAST_HISTORICAL_Q_YEAR}, "
                    f"Alternative II {_LAST_HISTORICAL_Q_YEAR + 1}-{LAST_YEAR}"
                ),
                "claiming": (
                    "Supplement 2026 Table 6.B5.1, rows 1998-"
                    f"{self.claim_table_max_year}; later years snap to "
                    f"{self.claim_table_max_year}"
                ),
            },
            "builder_defaults_awaiting_ratification": {
                **dict(tr2026.PENDING_RULINGS),
                "asfr_shape": (
                    f"{self.asfr_shape}: a fixed single-age shape scaled each "
                    "year to the V.A1 TFR (TR2026 publishes no ASFR); the "
                    "default is NCHS 2024 ungrouped by the mean-preserving "
                    "monotone interpolation, the alternative CBO's 2026 "
                    "single-year shape"
                ),
                "fold_under_14_into_14": (
                    "NCHS 10-14 band mass interpolated below age 14 is added "
                    "to age 14, the youngest exposed age"
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
            "gaps": [DI_GAP],
            "files_sha256": self.shared_files_sha256(),
            "captured_sources_sha256": self.captured_sources_sha256(
                include_cbo=self.asfr_shape == "cbo2026"
            ),
            **(
                {"cbo_files_sha256": self.cbo_files_sha256()}
                if self.asfr_shape == "cbo2026"
                else {}
            ),
        }
