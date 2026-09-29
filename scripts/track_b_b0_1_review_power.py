#!/usr/bin/env python3
"""Track B B0.1 revision 1: power figures with an explicit scoring basis.

The blinded review of the B0.1 audit found that section 11 mixed scoring
bases without saying so, and called worst-case bounds "necessary
conditions". This module restates those figures with the basis and the
gap-standard-error convention named for every number.

It reads only the sample sizes in the frozen count record
(``docs/design/track_b_b0_1_counts.json``) and, for one labelled planning
illustration, M6 v4's published 2016/2018 lag-2 floor sigma, which is not
B2 data. It reuses the frozen count script's functions unchanged. It
computes no B2 gate statistic, cell value or candidate outcome, and it
reads no reference-year 2012 or 2014 record.

Conventions (``sigma`` is a cell's half-split floor sigma; ``K`` = 20):

- ``m6_convention``: the gap of a faithful candidate is treated as having
  standard error ``sigma``. This is the basis of M6's operating
  characteristic (``m6_cells.py:701-734``) and of the frozen record's
  "gap-sigma" figures.
- ``side_a``: M6's scoring, the mean of K draws on a 50% person split
  against that split's truth. The survey-plus-simulation standard error
  of the gap is at most ``sigma * sqrt((1 + 1/K) / 2)``.
- ``full_support``: the same on the whole domain; at most
  ``sigma * sqrt(1 + 1/K) / 2``.

The two scoring bases give upper bounds because side-A truth and side-A
projections start from the same persons' 2010 anchors, so the part of a
statistic's sampling variation that the anchors explain cancels in the
gap. None of the three includes estimation error.
"""

from __future__ import annotations

import math
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import track_b_b0_1_counts as frozen  # noqa: E402

K = frozen.M6_DRAWS
FAMILY_SIZES = frozen.FAMILY_SIZES
#: Tolerance / half-split sigma of the k = 3 floor rule.
FLOOR_RATIO = frozen.half_normal_floor_ratio(frozen.M6_K)
#: The §5.3 earnings limits the frozen script evaluates.
PARTICIPATION_PP = frozen.SECTION_5_3_LIMITS["participation_pp"]
PERSISTENCE = frozen.SECTION_5_3_LIMITS["persistence_correlation"]

BASES = ("m6_convention", "side_a", "full_support")
GAP_SE_OVER_SIGMA: dict[str, float] = {
    "m6_convention": 1.0,
    "side_a": math.sqrt((1.0 + 1.0 / K) / 2.0),
    "full_support": math.sqrt(1.0 + 1.0 / K) / 2.0,
}
#: Share of each recorded effective size available on a basis. A 50%
#: person split halves the Kish size in expectation; for the
#: household-worst size, halving is conservative (side A keeps at least
#: half).
SUPPORT_SHARE = {"full_support": 1.0, "side_a": 0.5}

#: M6 v4's published 2016/2018 floor sigma for ``earn_autocorr_lag2``, and
#: its minimum weaker-half support count (persons), from
#: ``docs/amendments/gate_m6_amendment_1_closed_domain_floors.md:72``.
#: Not B2 data; used only as a labelled planning illustration (Q5).
M6_LAG2_FLOOR_SIGMA = 0.033346
M6_LAG2_WEAKER_HALF_SUPPORT = 5636


# --------------------------------------------------------------------------
# §5.2 bound rule at the k = 3 floor tolerance
# --------------------------------------------------------------------------
def tol_over_gap_se(basis: str) -> float:
    """Floor tolerance over the gap's standard error on ``basis``."""
    return FLOOR_RATIO / GAP_SE_OVER_SIGMA[basis]


def bound_rule_pass(basis: str, m: int) -> float:
    """P(a faithful cell passes the bound rule), no estimation term."""
    return frozen.bound_rule_pass_probability(tol_over_gap_se(basis), m)


def k_needed(basis: str, m: int) -> float:
    """The k a floor tolerance round(mean + k sd) needs for 0.90 power."""
    needed_over_sigma = frozen.bound_rule_ratio(m) * GAP_SE_OVER_SIGMA[basis]
    return (needed_over_sigma - math.sqrt(2.0 / math.pi)) / math.sqrt(
        1.0 - 2.0 / math.pi
    )


def estimation_headroom(basis: str, m: int) -> float:
    """Largest estimation variance, as a share of the survey-plus-simulation
    gap variance, that still leaves 0.90 power. Negative means none."""
    return (tol_over_gap_se(basis) / frozen.bound_rule_ratio(m)) ** 2 - 1.0


def estimation_headroom_over_se_full_sq(m: int) -> float:
    """The full-support headroom as a share of se_full^2 (the statistic's
    own full-support variance), the reference the frozen audit text used."""
    tol_over_se_full = 2.0 * FLOOR_RATIO
    return (tol_over_se_full / frozen.bound_rule_ratio(m)) ** 2 - (
        1.0 + 1.0 / K
    )


# --------------------------------------------------------------------------
# §5.3 limits on B2's support, by basis
# --------------------------------------------------------------------------
def participation_required(m: int, p: float) -> float:
    """Effective size a 3-point participation cell needs at share ``p``."""
    return frozen.required_n_eff_proportion(PARTICIPATION_PP, m) * (
        4.0 * p * (1.0 - p)
    )


def participation_min_p(n_eff: float, m: int) -> float:
    """Smallest p >= 1/2 at which ``n_eff`` suffices (by symmetry, the cell
    is also feasible at 1 - p). Returns 0.5 when every p is feasible."""
    ratio = n_eff / frozen.required_n_eff_proportion(PARTICIPATION_PP, m)
    if ratio >= 1.0:
        return 0.5
    return (1.0 + math.sqrt(1.0 - ratio)) / 2.0


def persistence_required(
    m: int, rho: float, fourth_moment_factor: float = 1.0
) -> float:
    """Effective positive pairs a 0.05 correlation cell needs.

    Normal theory gives var(r) = (1 - rho^2)^2 / n. For elliptical
    distributions the variance is multiplied by 1 + kappa (kappa the
    kurtosis parameter); ``fourth_moment_factor`` carries that multiplier.
    Heavy-tailed earnings have a factor above 1.
    """
    base = frozen.required_n_eff_correlation(PERSISTENCE, m)
    return base * fourth_moment_factor * (1.0 - rho**2) ** 2


def persistence_min_rho(
    n_eff: float,
    m: int,
    fourth_moment_factor: float = 1.0,
    positive_share: float = 1.0,
) -> float:
    """Smallest rho >= 0 at which the positive pairs suffice."""
    base = frozen.required_n_eff_correlation(PERSISTENCE, m)
    ratio = positive_share * n_eff / (base * fourth_moment_factor)
    if ratio >= 1.0:
        return 0.0
    return math.sqrt(1.0 - math.sqrt(ratio))


def m6_lag2_planning() -> dict[str, Any]:
    """What M6's published lag-2 floor sigma implies, as a planning value."""
    se_half = M6_LAG2_FLOOR_SIGMA / math.sqrt(2.0)
    se_full = M6_LAG2_FLOOR_SIGMA / 2.0
    out: dict[str, Any] = {
        "floor_sigma": M6_LAG2_FLOOR_SIGMA,
        "se_per_half": round(se_half, 5),
        "se_full_support": round(se_full, 5),
        "pairs_below_which_se_half_is_within_1_over_sqrt_n": round(
            1.0 / se_half**2, 1
        ),
        "weaker_half_support_persons": M6_LAG2_WEAKER_HALF_SUPPORT,
        "by_family_size": {},
    }
    for m in FAMILY_SIZES:
        allowed = PERSISTENCE / (
            frozen.bound_rule_ratio(m) * math.sqrt(1.0 + 1.0 / K)
        )
        multiple = (se_full / allowed) ** 2
        out["by_family_size"][str(m)] = {
            "se_full_allowed": round(allowed, 5),
            "support_multiple_of_m6_needed_full_support": round(multiple, 2),
            "support_multiple_of_m6_needed_side_a": round(2.0 * multiple, 2),
        }
    return out


def review_power_record(counts: Mapping[str, Any]) -> dict[str, Any]:
    """Every revision-1 power figure the audit quotes."""
    bound = {
        str(m): {
            basis: {
                "pass_probability_no_estimation": round(
                    bound_rule_pass(basis, m), 4
                ),
                "k_needed": round(k_needed(basis, m), 2),
                "estimation_headroom_share_of_gap_variance": round(
                    estimation_headroom(basis, m), 4
                ),
            }
            for basis in BASES
        }
        for m in (1, 2, 3, 4, 5, 6, 16)
    }
    headroom_full = {
        str(m): round(estimation_headroom_over_se_full_sq(m), 4)
        for m in FAMILY_SIZES
    }
    participation: dict[str, Any] = {}
    quantiles: dict[str, Any] = {}
    frozen_limits = frozen.power_record(counts)[
        "section_5_3_limits_on_b2_support"
    ]
    for cohort in ("prime", "older"):
        cell = counts["level_cells"][cohort]
        for basis, share in SUPPORT_SHARE.items():
            for size in ("kish_n_eff", "cluster_worst_n_eff"):
                n_eff = cell[size] * share
                key = f"{cohort}.{basis}.{size}"
                participation[key] = {
                    "n_eff": round(n_eff),
                    "feasible_at_p_half": {
                        str(m): n_eff >= participation_required(m, 0.5)
                        for m in FAMILY_SIZES
                    },
                    "min_p": {
                        str(m): round(participation_min_p(n_eff, m), 3)
                        for m in FAMILY_SIZES
                    },
                }
        by_q = frozen_limits["6"]["by_cohort"][cohort][
            "quantile_max_log_sd_if_all_positive"
        ]
        for q in ("p10", "p50"):
            for size, label in (
                ("kish", "kish_n_eff"),
                ("cluster_worst", "cluster_worst_n_eff"),
            ):
                full = by_q[q][size]
                quantiles[f"{cohort}.{q}.{label}"] = {
                    "full_support": round(full, 2),
                    "side_a": round(full * math.sqrt(0.5), 2),
                }
    persistence: dict[str, Any] = {}
    pairs = {
        "lag1": counts["change_pairs"]["pooled_one_step"],
        "lag2": counts["change_pairs"]["pooled_two_step"],
    }
    for lag, cell in pairs.items():
        for basis, share in SUPPORT_SHARE.items():
            for size in ("kish_n_eff", "cluster_worst_n_eff"):
                n_eff = cell[size] * share
                persistence[f"{lag}.{basis}.{size}"] = {
                    "n_eff": round(n_eff),
                    "min_rho_normal": {
                        str(m): round(persistence_min_rho(n_eff, m), 2)
                        for m in FAMILY_SIZES
                    },
                    "min_rho_factor_2": {
                        str(m): round(persistence_min_rho(n_eff, m, 2.0), 2)
                        for m in FAMILY_SIZES
                    },
                }
    return {
        "gap_se_over_sigma": {
            basis: round(value, 4)
            for basis, value in GAP_SE_OVER_SIGMA.items()
        },
        "bound_rule_at_k3": bound,
        "full_support_headroom_share_of_se_full_sq": headroom_full,
        "participation_3pp": {
            "required_n_eff_at_p_half": {
                str(m): round(participation_required(m, 0.5), 1)
                for m in FAMILY_SIZES
            },
            "by_cell": participation,
        },
        "quantile_10pct_max_log_sd_m6": quantiles,
        "persistence_0_05": {
            "required_pairs_rho0_normal": {
                str(m): round(persistence_required(m, 0.0), 1)
                for m in FAMILY_SIZES
            },
            "by_pairs": persistence,
        },
        "m6_lag2_planning_illustration": m6_lag2_planning(),
    }
