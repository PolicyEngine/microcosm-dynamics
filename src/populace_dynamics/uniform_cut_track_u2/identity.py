"""The U2 target identity and the cross-cohort refusals (section 14).

Every U2 object that could be confused with its U1 counterpart carries or
checks the identity below: the target (``U2``), the specification and its
path, the Report column (``1946-55``), the birth years, the statistic,
the comparison-interval identifier and the artifact destination.  The
U1 identities are recorded here as literals, not imported, so that the
structure and component entry points (which must not import the income
concept) can refuse them too; ``tests/track_u2/test_u2_identity.py``
holds each literal equal to the U1 module constant it names.

Section 14 "Cross-cohort refusals": U2 refuses U1's specification,
column, row/rulings record, ``MAX_RULINGS`` and artifact path, U1's
threshold hash ``dc21a787...`` and SSI hash ``79e641a1...`` even where
years overlap, and U1's seed setting; U1's own guards refuse U2's
settings and captures (tested, not changed).
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

__all__ = [
    "ARTIFACT_PATH",
    "BIRTH_YEARS",
    "COMPARATOR_COLUMN",
    "COMPARATOR_INTERVAL",
    "ROOT",
    "SIDECAR_PATH",
    "SPECIFICATION_ID",
    "SPECIFICATION_PATH",
    "STATISTIC_ID",
    "TARGET_AGE",
    "TARGET_ID",
    "U1_ARTIFACT_PATH",
    "U1_BIRTH_YEARS",
    "U1_COMPARATOR_COLUMN",
    "U1_COMPARATOR_INTERVAL",
    "U1_SEED_WAVE_RULE",
    "U1_SIDECAR_PATH",
    "U1_SPECIFICATION_ID",
    "U1_SPECIFICATION_PATH",
    "U1_SPECIFICATION_SHA256",
    "U1_SSI_SHA256",
    "U1_STATISTIC_ID",
    "U1_THRESHOLDS_SHA256",
    "U1_WAVES",
    "U2IdentityError",
    "check_target",
    "identity",
    "refuse_u1_identity",
]

ROOT = Path(__file__).resolve().parents[3]

#: The held-out target (specification header).
TARGET_ID = "U2"
#: The specification identity (section 15 ``specification``).
SPECIFICATION_ID = "boomers2004_1946_55_uniform_cut"
SPECIFICATION_PATH = (
    ROOT / "docs" / "design" / "boomers2004_1946_55_comparison.md"
)
#: The Report column as printed (section 1: hyphen, abbreviated end year).
COMPARATOR_COLUMN = "1946-55"
BIRTH_YEARS: tuple[int, ...] = tuple(range(1946, 1956))
TARGET_AGE = 67
#: The frozen statistic's identity (distinct from U1's).
STATISTIC_ID = "boomers2004_uniform_13pct_cut_adjusted_poverty_at_67_1946_55"
#: Section 10a: the U2 machine-readable interval identifier ends in
#: ``_open``; U1's identifier is unchanged.
COMPARATOR_INTERVAL = "whole_number_rounding_level_0_5_difference_1_open"
#: Section 14 implementation table: artifact and environment sidecar.
ARTIFACT_PATH = ROOT / "runs" / "replication_boomers2004_1946_55_v1.json"
SIDECAR_PATH = ARTIFACT_PATH.with_suffix(".env.json")

# ---------------------------------------------------------------------------
# U1 identities, as literals (tests hold them equal to the U1 modules).
# ---------------------------------------------------------------------------
#: ``uniform_cut_tabulation.COMPARATOR_COLUMN``.
U1_COMPARATOR_COLUMN = "1936-45"
#: ``uniform_cut_tabulation.STATISTIC_ID``.
U1_STATISTIC_ID = (
    "dynasim_exercise2_uniform_13pct_cut_adjusted_poverty_at_67_1936_45"
)
#: The U1 specification block's ``specification``, path and pinned hash.
U1_SPECIFICATION_ID = "boomers2004_uniform_cut_exercise2"
U1_SPECIFICATION_PATH = (
    ROOT / "docs" / "design" / "boomers2004_uniform_cut_comparison.md"
)
U1_SPECIFICATION_SHA256 = (
    "830b0ab4c18273563add529fecf21f843eb418996da741d087d785c4f882781f"
)
#: The U1 block's ``comparison.comparator_interval``.
U1_COMPARATOR_INTERVAL = "whole_number_rounding_level_0_5_difference_1"
U1_ARTIFACT_PATH = (
    ROOT / "runs" / "replication_boomers2004_uniform_cut_v1.json"
)
U1_SIDECAR_PATH = U1_ARTIFACT_PATH.with_suffix(".env.json")
#: ``adjusted_poverty.THRESHOLDS_SHA256`` and ``SSI_PARAMETERS_SHA256``.
U1_THRESHOLDS_SHA256 = (
    "dc21a78736f5085872cf56c9cf291258034c1293572b77455cba689a1ed0eec5"
)
U1_SSI_SHA256 = (
    "79e641a10d95afba81c8d831852fb52ef0a801e7175e06df17e6cc7cc3e3c523"
)
#: ``age67.Age67Spec().seed_wave_rule`` and ``age67.WAVES``.
U1_SEED_WAVE_RULE = "earliest_presence_wave"
U1_WAVES: tuple[int, ...] = (2005, 2007, 2009, 2011, 2013)
U1_BIRTH_YEARS: tuple[int, ...] = tuple(range(1936, 1946))

_U1_VALUES: dict[str, Any] = {
    "comparator_column": U1_COMPARATOR_COLUMN,
    "statistic_id": U1_STATISTIC_ID,
    "specification": U1_SPECIFICATION_ID,
    "specification_sha256": U1_SPECIFICATION_SHA256,
    "comparator_interval": U1_COMPARATOR_INTERVAL,
    "thresholds_sha256": U1_THRESHOLDS_SHA256,
    "ssi_sha256": U1_SSI_SHA256,
    "seed_wave_rule": U1_SEED_WAVE_RULE,
}
_U1_PATHS: tuple[Path, ...] = (
    U1_SPECIFICATION_PATH,
    U1_ARTIFACT_PATH,
    U1_SIDECAR_PATH,
)


class U2IdentityError(ValueError):
    """A U2 object carries another target's identity (section 14)."""


def identity() -> dict[str, Any]:
    """The U2 identity every U2 output records."""

    return {
        "target_id": TARGET_ID,
        "specification": SPECIFICATION_ID,
        "specification_path": str(SPECIFICATION_PATH.relative_to(ROOT)),
        "comparator_column": COMPARATOR_COLUMN,
        "birth_years": [BIRTH_YEARS[0], BIRTH_YEARS[-1]],
        "target_age": TARGET_AGE,
        "statistic_id": STATISTIC_ID,
        "comparator_interval": COMPARATOR_INTERVAL,
        "artifact": str(ARTIFACT_PATH.relative_to(ROOT)),
        "sidecar": str(SIDECAR_PATH.relative_to(ROOT)),
    }


def check_target(value: Any, what: str) -> str:
    """Refuse ``value`` unless it is the U2 target identity."""

    if value != TARGET_ID:
        raise U2IdentityError(
            f"{what} records target {value!r}, not {TARGET_ID!r}: a U2 "
            "computation accepts only U2-bound objects (section 14)"
        )
    return TARGET_ID


def _same_path(value: Any, path: Path) -> bool:
    try:
        candidate = Path(value)
    except TypeError:
        return False
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    return candidate.resolve() == path.resolve()


def refuse_u1_identity(values: Mapping[str, Any], *, what: str) -> None:
    """Refuse any field of ``values`` equal to its U1 counterpart.

    Keys of :data:`_U1_VALUES` compare by equality; any value naming the
    U1 specification, artifact or sidecar path is refused under any key.
    Section 14: U2 refuses U1's specification, column, statistic,
    parameter hashes, seed setting and artifact path.
    """

    for key, value in values.items():
        if key in _U1_VALUES and value == _U1_VALUES[key]:
            raise U2IdentityError(
                f"{what}: {key}={value!r} is U1's identity; U2 refuses it "
                "(section 14 cross-cohort refusals)"
            )
        if isinstance(value, str | Path) and any(
            _same_path(value, path) for path in _U1_PATHS
        ):
            raise U2IdentityError(
                f"{what}: {key}={value!s} names a U1 specification or "
                "artifact path; U2 refuses it (section 14)"
            )
