"""U2's target-bound parameters: thresholds, SSI and life tables.

Specification sections 5, 6, 8 and 14.  Every loader here reads a fixed,
committed file under a pin written in this module; none accepts a
caller-supplied expected hash (section 14: "caller-supplied expected
hashes cannot bypass the target-bound parameter bundle").

* **Census thresholds** (section 6): the full registered Track M capture
  ``data/external/census_poverty_thresholds_1982_2022.json`` (SHA-256
  ``288399c4...``), read with its whole schema -- the weighted averages
  by family size and the size-by-related-children matrix, not Track M's
  one-person accessor (``min_benefit_track_m/thresholds.py:50``).  Every
  required income year 2012-2022 must be present; income year 2012 must
  equal U1's capture (``dc21a787...``) in every weighted average,
  all-ages weighted average and matrix entry, or the load refuses; the
  2022 weighted averages are read as captured under
  ``weighted_average_unit_dollars: 10`` (never multiplied again).
  U1's capture is refused as a U2 threshold source.
* **SSI** (section 8): the separate U2 capture
  ``data/external/track_u2_ssi_parameters_2012_2022.json`` (SHA-256
  ``a58d55c1...``, milestone 1): exactly the years 2012-2022, an exact
  40-hex policyengine-us revision, the five constant parameters constant
  across the eleven years, and a 2012 projection equal to U1's capture in
  all seven parameters.  U1's SSI capture is refused as a U2 source.
* **Life tables** (section 5): NCHS 2000 and the SSA 2004 period table,
  hash-verified by the inherited loaders (no later table).

The objects returned are :class:`populace_dynamics.estimates.
adjusted_poverty.PovertyThresholds` and ``SsiParameters`` whose
provenance records ``target_id: U2``; :func:`check_u2_parameters`
refuses a bundle whose provenance is not U2's pinned captures (or, for
an invented run, invented values).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from populace_dynamics.estimates import adjusted_poverty as ap
from populace_dynamics.uniform_cut_track_u2 import identity

__all__ = [
    "INVENTED",
    "REQUIRED_INCOME_YEARS",
    "SSI_PATH",
    "SSI_SCHEMA_VERSION",
    "SSI_SHA256",
    "SSI_YEARS",
    "THRESHOLDS_PATH",
    "THRESHOLDS_SHA256",
    "U1_SSI_PATH",
    "U1_THRESHOLDS_PATH",
    "U2ParameterError",
    "U2Parameters",
    "check_u2_parameters",
    "committed_u2_parameters",
    "load_u2_ssi_parameters",
    "load_u2_thresholds",
]

_EXTERNAL = identity.ROOT / "data" / "external"
THRESHOLDS_PATH = _EXTERNAL / "census_poverty_thresholds_1982_2022.json"
THRESHOLDS_SHA256 = (
    "288399c475ae3ff02e6d8367425ee0a568b50d239da5656f24d0d2dfafabfb53"
)
_THRESHOLDS_SCHEMA = "populace_dynamics.census_poverty_thresholds.v1"
U1_THRESHOLDS_PATH = _EXTERNAL / "census_poverty_thresholds_2004_2012.json"
#: Section 6: coverage for income years 2012, 2014, ..., 2022.
REQUIRED_INCOME_YEARS: tuple[int, ...] = (2012, 2014, 2016, 2018, 2020, 2022)
#: The year whose weighted averages the 2022 workbook prints to $10.
_TEN_DOLLAR_YEAR = 2022

SSI_PATH = _EXTERNAL / "track_u2_ssi_parameters_2012_2022.json"
SSI_SHA256 = (
    "a58d55c160b48cd3e21f730d45265374bd3c8a9eb7eae947469a5a5dc0b23762"
)
SSI_SCHEMA_VERSION = "populace_dynamics.track_u2_ssi_parameters.v1"
SSI_YEARS: tuple[int, ...] = tuple(range(2012, 2023))
U1_SSI_PATH = _EXTERNAL / "track_u_ssi_parameters.json"
_CONSTANT_PARAMETERS: tuple[str, ...] = (
    "general_income_exclusion",
    "earned_income_exclusion",
    "earned_income_share_excluded",
    "resource_limit_individual",
    "resource_limit_couple",
)
_U1_SSI_SCHEMA = "populace_dynamics.track_u_ssi_parameters.v1"
INVENTED = ap.INVENTED
_LIFE_TABLE_PINS = {
    "nchs_2000": ap.NCHS_2000_SHA256,
    "ssa_period_2004": (
        "78c5e55b29615e21f60dc6345572ab06206245246394e2a2791d82358c45d7d7"
    ),
}


class U2ParameterError(ValueError):
    """A U2 parameter capture is missing, changed or not U2's."""


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_pinned(path: Path, pin: str, what: str) -> dict[str, Any]:
    if not path.is_file():
        raise U2ParameterError(f"{what}: {path} is missing")
    raw = path.read_bytes()
    observed = _sha256(raw)
    if observed == identity.U1_THRESHOLDS_SHA256 or (
        observed == identity.U1_SSI_SHA256
    ):
        raise U2ParameterError(
            f"{what}: {path} is a U1 capture ({observed[:12]}...); U2 "
            "refuses U1's threshold and SSI captures even where years "
            "overlap (section 14)"
        )
    if observed != pin:
        raise U2ParameterError(
            f"{what}: {path} sha256 {observed} != U2's pin {pin}"
        )
    return json.loads(raw)


# ===========================================================================
# Thresholds
# ===========================================================================
def _u1_2012_threshold_projection() -> dict[str, Any]:
    raw = U1_THRESHOLDS_PATH.read_bytes()
    if _sha256(raw) != identity.U1_THRESHOLDS_SHA256:
        raise U2ParameterError(
            "U1's threshold capture changed; the 2012 overlap check cannot "
            "run (U1's captures must stay byte-identical)"
        )
    data = json.loads(raw)
    return {
        key: data[key]["2012"]
        for key in ("weighted_average", "weighted_average_all_ages", "matrix")
    }


def load_u2_thresholds() -> ap.PovertyThresholds:
    """The full Track M Census capture, bound to U2 (section 6).

    Refuses: another file or hash (U1's capture by name), another schema,
    any required income year missing from the weighted averages, the
    all-ages averages or the matrix, any difference from U1's capture in
    income year 2012, and a 2022 precision record other than ``10``.
    """

    data = _read_pinned(THRESHOLDS_PATH, THRESHOLDS_SHA256, "thresholds")
    if data.get("schema_version") != _THRESHOLDS_SCHEMA:
        raise U2ParameterError("unexpected threshold schema")
    for key in ("weighted_average", "weighted_average_all_ages", "matrix"):
        missing = [
            year
            for year in REQUIRED_INCOME_YEARS
            if str(year) not in data.get(key, {})
        ]
        if missing:
            raise U2ParameterError(
                f"the capture's {key} lacks required income years {missing}"
            )
    u1 = _u1_2012_threshold_projection()
    for key, expected in u1.items():
        if data[key]["2012"] != expected:
            raise U2ParameterError(
                f"income year 2012 {key} differs from U1's capture "
                f"(dc21a787...): refused (section 6)"
            )
    layout = data["checks"]["layout_by_year"]
    unit = layout[str(_TEN_DOLLAR_YEAR)]["weighted_average_unit_dollars"]
    if unit != 10:
        raise U2ParameterError(
            f"2022 weighted_average_unit_dollars is {unit!r}, not 10"
        )
    years = sorted(int(year) for year in data["weighted_average"])
    return ap.PovertyThresholds(
        weighted_average={
            int(year): {row: float(v) for row, v in rows.items()}
            for year, rows in data["weighted_average"].items()
        },
        matrix={
            int(year): {
                row: {int(k): float(v) for k, v in cells.items()}
                for row, cells in rows.items()
            }
            for year, rows in data["matrix"].items()
        },
        provenance={
            "kind": "census_capture",
            "sha256": THRESHOLDS_SHA256,
            "target_id": identity.TARGET_ID,
            "file": str(THRESHOLDS_PATH.relative_to(identity.ROOT)),
            "required_income_years": list(REQUIRED_INCOME_YEARS),
            "years": [years[0], years[-1]],
            "overlap_2012": "exact_equality_with_u1_capture",
            "weighted_average_unit_dollars_2022": unit,
        },
    )


# ===========================================================================
# SSI
# ===========================================================================
def _check_revision(revision: Any) -> str:
    if not isinstance(revision, str) or not re.fullmatch(
        r"[0-9a-f]{40}", revision
    ):
        raise U2ParameterError(
            f"SSI source revision {revision!r}: a missing, empty or "
            "'unknown' revision is refused (section 8)"
        )
    return revision


def _projection_2012(data: Mapping[str, Any]) -> dict[str, float]:
    fbr = data["federal_benefit_rate_monthly"]
    return {
        "fbr_individual": float(fbr["individual"]["2012"]),
        "fbr_couple": float(fbr["couple"]["2012"]),
        "general_income_exclusion": float(
            data["general_income_exclusion_monthly"]
        ),
        "earned_income_exclusion": float(
            data["earned_income_exclusion_monthly"]
        ),
        "earned_income_share_excluded": float(
            data["earned_income_share_excluded"]
        ),
        "resource_limit_individual": float(data["resource_limit"]["individual"]),
        "resource_limit_couple": float(data["resource_limit"]["couple"]),
    }


def validate_u2_ssi_document(data: Mapping[str, Any]) -> None:
    """Schema, years, revision, constancy and the 2012 overlap (sec. 8)."""

    if data.get("schema_version") != SSI_SCHEMA_VERSION:
        raise U2ParameterError(f"SSI schema {data.get('schema_version')!r}")
    identity.check_target(data.get("target_id"), "the SSI capture")
    if data.get("years") != list(SSI_YEARS):
        raise U2ParameterError(
            f"SSI years {data.get('years')} are not exactly 2012-2022"
        )
    _check_revision((data.get("source") or {}).get("policyengine_us_revision"))
    fbr = data.get("federal_benefit_rate_monthly") or {}
    for unit in ("individual", "couple"):
        years = sorted(int(year) for year in (fbr.get(unit) or {}))
        if years != list(SSI_YEARS):
            raise U2ParameterError(
                f"SSI {unit} FBR years {years} are not exactly 2012-2022"
            )
    # Section 8: the capture's constant() check over all eleven years, per
    # parameter; variation needs a schema/method amendment.
    constants = (data.get("verification") or {}).get("constant_parameters")
    if not isinstance(constants, Mapping) or set(constants) != set(
        _CONSTANT_PARAMETERS
    ):
        raise U2ParameterError(
            "the SSI capture records no constant() check for exactly "
            f"{_CONSTANT_PARAMETERS}"
        )
    for name, years in constants.items():
        if list(years) != list(SSI_YEARS):
            raise U2ParameterError(
                f"SSI {name} is not constant over 2012-2022 ({years}): a "
                "schema/method amendment is required (section 8)"
            )
    u1 = json.loads(U1_SSI_PATH.read_bytes())
    if u1.get("schema_version") != _U1_SSI_SCHEMA:
        raise U2ParameterError("U1's SSI capture has another schema")
    if _projection_2012(data) != _projection_2012(u1):
        raise U2ParameterError(
            "the 2012 SSI parameters differ from U1's capture (79e641a1...): "
            "refused (section 8)"
        )


def load_u2_ssi_parameters() -> ap.SsiParameters:
    """The separate U2 SSI capture, bound to U2 (section 8)."""

    data = _read_pinned(SSI_PATH, SSI_SHA256, "SSI parameters")
    if _sha256(U1_SSI_PATH.read_bytes()) != identity.U1_SSI_SHA256:
        raise U2ParameterError("U1's SSI capture changed")
    validate_u2_ssi_document(data)
    fbr = data["federal_benefit_rate_monthly"]
    return ap.SsiParameters(
        fbr_individual_monthly={
            int(y): float(v) for y, v in fbr["individual"].items()
        },
        fbr_couple_monthly={
            int(y): float(v) for y, v in fbr["couple"].items()
        },
        general_income_exclusion_monthly=float(
            data["general_income_exclusion_monthly"]
        ),
        earned_income_exclusion_monthly=float(
            data["earned_income_exclusion_monthly"]
        ),
        earned_income_share_excluded=float(
            data["earned_income_share_excluded"]
        ),
        resource_limit_individual=float(data["resource_limit"]["individual"]),
        resource_limit_couple=float(data["resource_limit"]["couple"]),
        provenance={
            "kind": "policyengine_us_capture",
            "sha256": SSI_SHA256,
            "target_id": identity.TARGET_ID,
            "file": str(SSI_PATH.relative_to(identity.ROOT)),
            "policyengine_us_revision": data["source"][
                "policyengine_us_revision"
            ],
            "years": list(SSI_YEARS),
            "overlap_2012": "all_seven_parameters_equal_u1",
        },
    )


# ===========================================================================
# The bundle
# ===========================================================================
@dataclass(frozen=True)
class U2Parameters:
    """Thresholds, SSI and life tables, bound to target U2."""

    thresholds: ap.PovertyThresholds
    ssi: ap.SsiParameters
    life_tables: Mapping[str, ap.LifeTable]
    target_id: str = identity.TARGET_ID

    def __post_init__(self) -> None:
        identity.check_target(self.target_id, "the parameter bundle")

    def provenance(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "thresholds": dict(self.thresholds.provenance),
            "ssi": dict(self.ssi.provenance),
            "life_tables": {
                name: {"name": table.name, **dict(table.source)}
                for name, table in sorted(self.life_tables.items())
            },
        }


def committed_u2_parameters(
    thresholds: ap.PovertyThresholds | None = None,
) -> U2Parameters:
    """U2's committed SSI capture and life tables, with ``thresholds``.

    The registered run passes nothing (the pinned Track M capture is
    read); the invented dry run passes its invented threshold table.
    """

    return U2Parameters(
        thresholds=load_u2_thresholds() if thresholds is None else thresholds,
        ssi=load_u2_ssi_parameters(),
        life_tables={
            "nchs_2000": ap.load_nchs_2000_life_table(),
            "ssa_period_2004": ap.load_ssa_period_2004_life_table(),
        },
    )


def check_u2_parameters(params: U2Parameters, data_provenance: str) -> None:
    """Refuse parameters that are not U2's for ``data_provenance``.

    Every run: a U2 bundle, life tables filed under their own basis (or
    invented tables in an invented run), U1's threshold and SSI captures
    refused by hash.  A registered run: exactly U2's pinned Census and
    SSI captures, each recording ``target_id: U2``, and the committed life
    tables with their pinned SHA-256.
    """

    if not isinstance(params, U2Parameters):
        raise U2ParameterError("a U2 run needs a U2Parameters bundle")
    identity.check_target(params.target_id, "the parameter bundle")
    for name, value in (("thresholds", params.thresholds), ("ssi", params.ssi)):
        sha = dict(value.provenance).get("sha256")
        if sha in (identity.U1_THRESHOLDS_SHA256, identity.U1_SSI_SHA256):
            raise U2ParameterError(
                f"the {name} are a U1 capture ({sha[:12]}...): refused "
                "(section 14)"
            )
    for basis, table in params.life_tables.items():
        invented = data_provenance == INVENTED and table.name == (
            ap.INVENTED_LIFE_TABLE
        )
        if table.name != basis and not invented:
            raise U2ParameterError(
                f"life table {table.name!r} is filed under {basis!r}"
            )
    if data_provenance != ap.REGISTERED_REAL:
        return
    thresholds = dict(params.thresholds.provenance)
    if (
        thresholds.get("kind") != "census_capture"
        or thresholds.get("sha256") != THRESHOLDS_SHA256
        or thresholds.get("target_id") != identity.TARGET_ID
    ):
        raise U2ParameterError(
            "a registered U2 run needs the pinned Track M Census capture "
            f"bound to U2; the thresholds record {thresholds!r}"
        )
    ssi = dict(params.ssi.provenance)
    if (
        ssi.get("kind") != "policyengine_us_capture"
        or ssi.get("sha256") != SSI_SHA256
        or ssi.get("target_id") != identity.TARGET_ID
    ):
        raise U2ParameterError(
            "a registered U2 run needs the pinned U2 SSI capture; the SSI "
            f"parameters record {ssi!r}"
        )
    if set(params.life_tables) != set(_LIFE_TABLE_PINS) or any(
        params.life_tables[basis].source.get("sha256") != pin
        for basis, pin in _LIFE_TABLE_PINS.items()
    ):
        raise U2ParameterError(
            "a registered U2 run needs the committed life tables "
            f"{sorted(_LIFE_TABLE_PINS)} with their pinned SHA-256"
        )
    missing = [
        year
        for year in REQUIRED_INCOME_YEARS
        if year not in params.thresholds.weighted_average
        or year not in params.thresholds.matrix
        or year not in params.ssi.fbr_individual_monthly
        or year not in params.ssi.fbr_couple_monthly
    ]
    if missing:
        raise U2ParameterError(
            f"parameter coverage lacks income years {missing}"
        )
