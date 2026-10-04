"""Inputs the two 2026 baselines share: claiming, DI and file identity.

* **Claiming.**  The latest SSA awards distribution committed in
  ``data/external`` is Supplement 2026 Table 6.B5.1 (entitlement years
  1998-2025, :mod:`~populace_dynamics.baselines.claim_tables`).  Every
  row is supplied, and the projection reads rows at or before its last
  row, 2025 (``claim_table_max_year``), so every projection year after
  2025 snaps to the 2025 row.  The registered tests' table is the 2014
  Supplement capped at 2008 (``baselines.legacy``).
* **DI.**  The DI incidence, recovery and death rates are the 2008 fit
  (``load_di_entitlement_rates(DIEntitlementSpec())``) under every
  baseline, a named gap: no projected DI incidence or termination rates
  by age were found for TR2008 or any later vintage, and the fitted
  arrays have no year axis.  In the default multiplier death mode DI
  death is the AS118 rate times the baseline's population ``q`` over the
  NCHS 2000 ``q``, so it follows the baseline's mortality.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from populace_dynamics.baselines.asfr import NCHS_ASFR_PATH, NCHS_ASFR_SHA256
from populace_dynamics.baselines.base import file_sha256, repo_relative
from populace_dynamics.baselines.claim_tables import (
    CLAIM_AGES_2026_PATH,
    CLAIM_AGES_2026_SHA256,
    claim_pmf_2026_supplement,
    last_year_2026_supplement,
)
from populace_dynamics.data import cbo2026, tr2026
from populace_dynamics.engine.di_entitlement_rates import (
    DEFAULT_INPUTS_PATH,
    NCHS_2000_PATH,
    DIEntitlementRates,
    DIEntitlementSpec,
    load_di_entitlement_rates,
)
from populace_dynamics.estimates.parameters import (
    COLA_FILE_SHA256,
    COLA_HISTORY_PATH,
)

__all__ = [
    "CLAIM_TABLE_MAX_YEAR_2026",
    "DI_GAP",
    "Vintage2026Inputs",
]

#: The last row of the 2026 Supplement claim-age table.
CLAIM_TABLE_MAX_YEAR_2026 = 2025
DI_GAP = (
    "DI incidence, recovery and death are the 2008 fit (A4, "
    "load_di_entitlement_rates(DIEntitlementSpec())) under every baseline; "
    "no projected DI rates by age are captured for any vintage. DI death "
    "follows the baseline's population mortality in multiplier mode"
)


def _captured_sources(data_dir: Path) -> dict[str, str]:
    """Captured upstream source SHA-256s recorded in ``sources.json``."""
    document = json.loads((data_dir / "sources.json").read_bytes())
    return {
        name: record["sha256"]
        for name, record in sorted(document["sources"].items())
    }


class Vintage2026Inputs:
    """Claiming, DI and file-identity methods of the 2026 baselines."""

    claim_table_max_year: int = CLAIM_TABLE_MAX_YEAR_2026

    def claim_pmf(self) -> dict[tuple[str, int], dict[int, float]]:
        """Every 2026 Supplement row (1998-2025) as a claim-age PMF."""
        if last_year_2026_supplement() != self.claim_table_max_year:
            raise ValueError(
                "the 2026 Supplement table's last row is not "
                f"{self.claim_table_max_year}"
            )
        return claim_pmf_2026_supplement()

    def di_rates(
        self, spec: DIEntitlementSpec | None = None
    ) -> DIEntitlementRates:
        """The 2008 DI fit (a named gap; see the module docstring)."""
        return load_di_entitlement_rates(spec or DIEntitlementSpec())

    @staticmethod
    def shared_files_sha256() -> dict[str, str]:
        """Pinned or hashed identity of every shared input file read."""
        tr2026.verify_files()
        cbo2026.verify_files()
        for path, pinned in (
            (NCHS_ASFR_PATH, NCHS_ASFR_SHA256),
            (CLAIM_AGES_2026_PATH, CLAIM_AGES_2026_SHA256),
            (COLA_HISTORY_PATH, COLA_FILE_SHA256),
        ):
            observed = file_sha256(path)
            if observed != pinned:
                raise ValueError(
                    f"{path.name} sha256 {observed} != pinned {pinned}"
                )
        return {
            **{
                f"data/external/tr2026/{name}": digest
                for name, digest in tr2026.FILE_SHA256.items()
            },
            repo_relative(COLA_HISTORY_PATH): COLA_FILE_SHA256,
            repo_relative(CLAIM_AGES_2026_PATH): CLAIM_AGES_2026_SHA256,
            repo_relative(NCHS_ASFR_PATH): NCHS_ASFR_SHA256,
            repo_relative(DEFAULT_INPUTS_PATH): file_sha256(
                DEFAULT_INPUTS_PATH
            ),
            repo_relative(NCHS_2000_PATH): file_sha256(NCHS_2000_PATH),
        }

    @staticmethod
    def cbo_files_sha256() -> dict[str, str]:
        cbo2026.verify_files()
        return {
            f"data/external/cbo2026/{name}": digest
            for name, digest in cbo2026.FILE_SHA256.items()
        }

    @staticmethod
    def captured_sources_sha256(*, include_cbo: bool) -> dict[str, Any]:
        """Upstream capture hashes the extractors recorded (pinned JSON)."""
        out: dict[str, Any] = {
            "tr2026": _captured_sources(tr2026.DATA_DIR),
        }
        if include_cbo:
            out["cbo2026"] = _captured_sources(cbo2026.DATA_DIR)
        return out
