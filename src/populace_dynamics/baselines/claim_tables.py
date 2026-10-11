"""Claim-age PMFs from the latest committed SSA awards distribution.

The 2026 baselines claim from SSA *Annual Statistical Supplement, 2026*,
Table 6.B5.1 (retired-worker awardees by age at entitlement, by sex and
entitlement year 1998-2025), committed as
``data/external/ssa_claim_ages_2026supplement.json`` by
``scripts/extract_ssa_claim_ages_2026.py`` and pinned here by SHA-256.
The table's notes warn that "statistics for current and prior years are
subject to revision with each annual update", so the 2025 row, the last
and the row every later projection year snaps to, is the least settled.

:func:`populace_dynamics.claiming.claim_age_pmf` cannot read rows after
2022: it snaps every request to its module-level 1998-2022 span before
reading the reference.  :func:`claim_pmf_from_reference` therefore
applies the same category-to-age rule directly to each row: ages 62-66
and 70+ from their categories, the 67-69 aggregate split uniformly over
67, 68 and 69, disability conversions excluded and the rest renormalized
to one.  For every row in 1998-2022 the two constructions must agree
exactly (differential test in
``tests/baselines/test_asfr_and_claim_tables.py``).
"""

from __future__ import annotations

import hashlib
from functools import cache
from pathlib import Path

from populace_dynamics import claiming

__all__ = [
    "CLAIM_AGES_2026_PATH",
    "CLAIM_AGES_2026_SHA256",
    "claim_pmf_2026_supplement",
    "claim_pmf_from_reference",
    "claim_row_pmf",
    "last_year_2026_supplement",
]

_ROOT = Path(__file__).resolve().parents[3]
CLAIM_AGES_2026_PATH = (
    _ROOT / "data" / "external" / "ssa_claim_ages_2026supplement.json"
)
CLAIM_AGES_2026_SHA256 = (
    "1721f82ae6bc865a1e19f22a9578963032e7b30da9ba3f6f53448ab49fd17210"
)
_BAND_67_69 = (67, 68, 69)


def claim_row_pmf(categories: dict[str, float]) -> dict[int, float]:
    """Claim-age PMF of one row's collapsed categories, no conversions."""
    band = float(categories["age67_69"]) / len(_BAND_67_69)
    mass = {
        62: float(categories["age62"]),
        63: float(categories["age63"]),
        64: float(categories["age64"]),
        65: float(categories["age65"]),
        66: float(categories["age66"]),
        67: band,
        68: band,
        69: band,
        70: float(categories["age70plus"]),
    }
    if any(value < 0.0 for value in mass.values()):
        raise ValueError("claim-age category shares must be non-negative")
    total = sum(mass.values())
    if total <= 0.0:
        raise ValueError("degenerate claim-age row")
    return {age: value / total for age, value in mass.items()}


def claim_pmf_from_reference(
    reference: claiming.ClaimAgeReference,
) -> dict[tuple[str, int], dict[int, float]]:
    """Every (sex, entitlement year) PMF of a Table 6.B5.1 reference."""
    return {
        (sex, year): claim_row_pmf(reference.row(sex, year)["categories"])
        for sex in ("female", "male")
        for year in reference.years()
    }


@cache
def _reference_2026() -> claiming.ClaimAgeReference:
    digest = hashlib.sha256(CLAIM_AGES_2026_PATH.read_bytes()).hexdigest()
    if digest != CLAIM_AGES_2026_SHA256:
        raise ValueError(
            f"{CLAIM_AGES_2026_PATH.name} sha256 {digest} != pinned "
            f"{CLAIM_AGES_2026_SHA256}; re-pin deliberately"
        )
    reference = claiming.load_claim_age_reference(CLAIM_AGES_2026_PATH)
    if reference.supplement_year != 2026 or reference.table != "6.B5.1":
        raise ValueError("the 2026 claim-age file is not Supplement 6.B5.1")
    return reference


def claim_pmf_2026_supplement() -> dict[tuple[str, int], dict[int, float]]:
    """Every row of the 2026 Supplement table (1998-2025), as PMFs."""
    return claim_pmf_from_reference(_reference_2026())


def last_year_2026_supplement() -> int:
    """The last entitlement year the 2026 Supplement table prints."""
    return max(_reference_2026().years())
