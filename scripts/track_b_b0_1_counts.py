#!/usr/bin/env python3
"""Track B B0.1: structural counts and design-based power for B2.

B0.1 freezes the source, exposure, access and power record for Track B's
B2 gate (the 2010 -> 2014 earnings bridge scored on reference years 2012
and 2014). The protocol is ``docs/design/track_b_b0_1_audit.md`` section
"Structural-audit protocol", committed before this script was run on
staged data.

The script counts records, verifies variable labels, hashes the PSID
files it opens and the files B2's fit would open, checks the pinned 2010
NAWI prefix, and derives design-based power quantities from sample sizes
and weights only.

It computes no B2 gate statistic, candidate outcome or cell value. Every
family-file labor-income level is reduced to a validity flag (below the
PSID missing sentinel) as soon as it is read. No earnings level, sign or
zero indicator for any reference year enters a count; the unit test
``test_counts_are_invariant_to_valid_earnings_values`` pins that.

Run from the repository root (the staged PSID directory is resolved by
the repository's own loader rules)::

    .venv/bin/python scripts/track_b_b0_1_counts.py \\
        --pe-us-ssa-dir <site-packages>/policyengine_us/parameters/gov/ssa \\
        --out docs/design/track_b_b0_1_counts.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import norm

from populace_dynamics.data import family, panels, psid
from populace_dynamics.engine import forward_earnings as fe
from populace_dynamics.harness.m6_cells import EARN_COHORTS

ROOT = Path(__file__).resolve().parents[1]
#: Committed evidence directory; B0.1 never writes below it (design §5.1).
RUNS_DIR = ROOT / "runs"
SCHEMA = "track_b_b0_1_counts.v1"

#: B2's registered geometry (design §3.1 row B2; §3.2 row B2).
BOUNDARY_YEAR = 2010
HORIZON_YEARS: tuple[int, ...] = (2012, 2014)
REFERENCE_YEARS: tuple[int, ...] = (BOUNDARY_YEAR, *HORIZON_YEARS)
AGE_SUPPORT: tuple[int, int] = (fe.AGE_MIN, fe.AGE_MAX)
#: PSID collection wave for an income-reference year (family.py:843).
WAVE_OFFSET = 1

#: Individual-file sequence-number groups (psid2010-cohort.md:17-28;
#: panels.py:18-21).
SEQUENCE_GROUPS: tuple[tuple[str, int, int], ...] = (
    ("in_family", 1, 20),
    ("institution", 51, 59),
    ("moved_out", 71, 80),
    ("died", 81, 89),
)

#: Dispositions of a domain person at a horizon year, in precedence
#: order. Every domain person receives exactly one.
DISPOSITIONS: tuple[str, ...] = (
    "scored",
    "valid_row_age_outside_support",
    "head_or_spouse_earnings_missing",
    "present_no_family_record",
    "present_other_relationship",
    "present_nonpositive_weight",
    "institution",
    "moved_out",
    "died",
    "not_in_responding_family",
)

#: Registered-family sizes for which multiplicity-dependent power is
#: reported: one cell, the six M6-retained cells, and the 16-cell
#: gateable battery (m6_cells.py:478-586).
FAMILY_SIZES: tuple[int, ...] = (1, 6, 16)
M6_K = 3
M6_DRAWS = 20
POWER_TARGET = 0.90
ALPHA = 0.05
MC_FRACTION = 0.10

#: §5.3 earnings limits (design §5.3 row "Earnings"), expressed on the
#: scale this script evaluates. They are registered for B3's bands; this
#: script evaluates them on B2's support only as a feasibility record.
SECTION_5_3_LIMITS = {
    "participation_pp": 0.03,
    "quantile_relative": 0.10,
    "persistence_correlation": 0.05,
}


# --------------------------------------------------------------------------
# Validity reduction (the only place a labor-income field is touched)
# --------------------------------------------------------------------------
def validity_frame(labor: pd.DataFrame) -> pd.DataFrame:
    """Reduce one wave's family labor frame to validity and flag columns.

    ``labor`` is :func:`family.read_family_labor` output. The returned
    frame carries no labor-income level: only whether each role's value
    is below the missing sentinel, and whether its accuracy code is
    positive (assigned or edited).
    """
    required = {
        "interview",
        "head_labor",
        "spouse_labor",
        "head_acc",
        "spouse_acc",
    }
    if missing := required - set(labor):
        raise ValueError(f"family labor frame lacks {sorted(missing)}")
    out = pd.DataFrame(
        {
            "interview": labor["interview"].astype("int64").to_numpy(),
            "head_valid": (labor["head_labor"] < family._MISSING).to_numpy(),
            "spouse_valid": (
                labor["spouse_labor"] < family._MISSING
            ).to_numpy(),
            "head_acc_flag": (labor["head_acc"] > 0).to_numpy(),
            "spouse_acc_flag": (labor["spouse_acc"] > 0).to_numpy(),
        }
    )
    if out["interview"].duplicated().any():
        raise ValueError("family labor frame has duplicate interviews")
    return out


# --------------------------------------------------------------------------
# Pure structural counting
# --------------------------------------------------------------------------
def _sequence_group(sequence: pd.Series) -> pd.Series:
    values = pd.to_numeric(sequence, errors="coerce")
    group = pd.Series("other", index=sequence.index, dtype=object)
    for name, low, high in SEQUENCE_GROUPS:
        group[(values >= low) & (values <= high)] = name
    return group


def _cohort(age: float) -> str | None:
    if pd.isna(age):
        return None
    value = int(age)
    for name, low, high in EARN_COHORTS:
        if low <= value <= high:
            return name
    return None


def earnings_rows(
    person_wave: pd.DataFrame,
    validity_by_wave: Mapping[int, pd.DataFrame],
    reference_years: Iterable[int],
) -> pd.DataFrame:
    """Head/spouse rows with validity, mirroring ``family_earnings_panel``.

    A row is valid when the person is present (sequence 1-20) at the
    collection wave, is head/reference person or wife/spouse/partner
    there, has positive collection-wave weight, and that role's labor
    income is below the missing sentinel (family.py:821-859).
    """
    frames = []
    for year in reference_years:
        wave = year + WAVE_OFFSET
        people = person_wave[
            (person_wave["period"] == wave)
            & person_wave["sequence"].between(1, 20)
        ]
        merged = people.merge(
            validity_by_wave[wave], on="interview", how="inner"
        )
        head_codes, spouse_codes = family._relationship_codes(wave)
        is_head = merged["relationship"].isin(head_codes)
        is_spouse = merged["relationship"].isin(spouse_codes)
        merged = merged[is_head | is_spouse].copy()
        head = merged["relationship"].isin(head_codes)
        merged["role"] = np.where(head, "head", "spouse")
        role_valid = np.where(
            head, merged["head_valid"], merged["spouse_valid"]
        ).astype(bool)
        merged["acc_flag"] = np.where(
            head, merged["head_acc_flag"], merged["spouse_acc_flag"]
        ).astype(bool)
        merged["weight_positive"] = merged["weight"] > 0
        merged["valid"] = role_valid & merged["weight_positive"].to_numpy()
        merged["reference_year"] = year
        frames.append(
            merged[
                [
                    "person_id",
                    "reference_year",
                    "age",
                    "role",
                    "valid",
                    "weight_positive",
                    "acc_flag",
                ]
            ]
        )
    rows = pd.concat(frames, ignore_index=True)
    if rows.duplicated(["person_id", "reference_year"]).any():
        raise ValueError("a person holds two head/spouse rows in one wave")
    return rows


def kish_n_eff(weights: np.ndarray) -> float:
    """Kish effective sample size, sum(w)^2 / sum(w^2)."""
    w = np.asarray(weights, dtype=np.float64)
    if w.size == 0:
        return 0.0
    if np.any(w <= 0) or not np.isfinite(w).all():
        raise ValueError("weights must be finite and positive")
    return math.fsum(w) ** 2 / math.fsum(w**2)


def cluster_worst_n_eff(weights: np.ndarray, clusters: np.ndarray) -> float:
    """Effective size if every row in a cluster were perfectly correlated.

    Each cluster then acts as one unit carrying its total weight, so the
    effective size is sum(w)^2 / sum_c(W_c^2). It is a lower bound on the
    effective size for any non-negative within-cluster correlation.
    """
    w = np.asarray(weights, dtype=np.float64)
    if w.size == 0:
        return 0.0
    if np.any(w <= 0) or not np.isfinite(w).all():
        raise ValueError("weights must be finite and positive")
    totals: dict[Any, list[float]] = {}
    for weight, cluster in zip(
        w.tolist(), np.asarray(clusters).tolist(), strict=True
    ):
        totals.setdefault(cluster, []).append(weight)
    squared = [math.fsum(values) ** 2 for values in totals.values()]
    return math.fsum(w) ** 2 / math.fsum(squared)


def _weight_summary(frame: pd.DataFrame) -> dict[str, Any]:
    weights = frame["fixed_weight"].to_numpy(dtype=np.float64)
    clusters = frame["household_id"].to_numpy()
    return {
        "rows": int(len(frame)),
        "persons": int(frame["person_id"].nunique()),
        "households": int(pd.Series(clusters).nunique()),
        "kish_n_eff": round(kish_n_eff(weights), 3),
        "cluster_worst_n_eff": round(
            cluster_worst_n_eff(weights, clusters), 3
        ),
    }


def structural_counts(
    person_wave: pd.DataFrame,
    validity_by_wave: Mapping[int, pd.DataFrame],
    *,
    boundary_year: int = BOUNDARY_YEAR,
    horizon_years: tuple[int, ...] = HORIZON_YEARS,
    age_support: tuple[int, int] = AGE_SUPPORT,
) -> dict[str, Any]:
    """Count B2's anchor, domain, support, exits and entrants.

    ``person_wave`` has one row per person and collection wave with
    ``person_id, period, age, sequence, relationship, weight,
    interview`` (unfiltered). ``validity_by_wave`` maps each collection
    wave to :func:`validity_frame` output. Nothing here reads a labor
    income level.
    """
    reference_years = (boundary_year, *horizon_years)
    anchor_wave = boundary_year + WAVE_OFFSET
    low, high = age_support

    at_anchor = person_wave[person_wave["period"] == anchor_wave]
    present = at_anchor["sequence"].between(1, 20)
    positive = pd.to_numeric(at_anchor["weight"], errors="coerce") > 0
    full_anchor = at_anchor[present & positive][
        ["person_id", "interview", "weight", "age"]
    ].rename(columns={"interview": "household_id", "weight": "fixed_weight"})
    if full_anchor["person_id"].duplicated().any():
        raise ValueError("full anchor has duplicate persons")
    anchor_ids = frozenset(full_anchor["person_id"].astype("int64"))

    rows = earnings_rows(person_wave, validity_by_wave, reference_years)
    valid = rows[rows["valid"]]
    boundary_valid = valid[valid["reference_year"] == boundary_year]
    domain_ids = (
        frozenset(boundary_valid["person_id"].astype("int64")) & anchor_ids
    )
    if not frozenset(boundary_valid["person_id"].astype("int64")) <= (
        anchor_ids
    ):
        raise AssertionError("a valid boundary row lies outside the anchor")

    fixed = full_anchor.set_index("person_id")
    in_support = valid["age"].between(low, high)
    valid = valid.assign(
        cohort=valid["age"].map(_cohort),
        in_support=in_support.to_numpy(),
    )
    scored = valid[
        valid["in_support"] & valid["person_id"].isin(domain_ids)
    ].copy()
    scored["fixed_weight"] = scored["person_id"].map(fixed["fixed_weight"])
    scored["household_id"] = scored["person_id"].map(fixed["household_id"])

    domain_frame = full_anchor[full_anchor["person_id"].isin(domain_ids)]
    boundary_rows = boundary_valid[
        boundary_valid["person_id"].isin(domain_ids)
    ]
    domain_age = domain_frame["age"].astype("float64")
    result: dict[str, Any] = {
        "anchor_wave": anchor_wave,
        "full_anchor_persons": int(len(anchor_ids)),
        "full_anchor_households": int(full_anchor["household_id"].nunique()),
        "domain_persons": int(len(domain_ids)),
        "domain_by_role": {
            role: int((boundary_rows["role"] == role).sum())
            for role in ("head", "spouse")
        },
        "domain_by_anchor_wave_age": {
            "under_25": int((domain_age < low).sum()),
            "25_44": int(domain_age.between(25, 44).sum()),
            "45_64": int(domain_age.between(45, high).sum()),
            "65_plus": int((domain_age > high).sum()),
        },
        "domain_weights": _weight_summary(domain_frame),
    }

    by_year: dict[str, Any] = {}
    for year in reference_years:
        year_rows = scored[scored["reference_year"] == year]
        dropped = valid[
            (valid["reference_year"] == year)
            & valid["person_id"].isin(domain_ids)
            & ~valid["in_support"]
        ]
        by_year[str(year)] = {
            "collection_wave": year + WAVE_OFFSET,
            "scored_rows": int(len(year_rows)),
            "rows_by_cohort": {
                name: int((year_rows["cohort"] == name).sum())
                for name, _, _ in EARN_COHORTS
            },
            "valid_domain_rows_outside_age_support": int(len(dropped)),
            "assigned_or_edited_rows": int(year_rows["acc_flag"].sum()),
        }
    result["scored_support"] = by_year
    result["scored_rows_total"] = int(len(scored))

    level_rows = scored[scored["reference_year"].isin(horizon_years)]
    result["level_cells"] = {
        name: _weight_summary(level_rows[level_rows["cohort"] == name])
        for name, _, _ in EARN_COHORTS
    }
    result["level_cells"]["pooled"] = _weight_summary(level_rows)

    def pairs(first: int, second: int, same_cohort: str | None):
        left = scored[scored["reference_year"] == first]
        right = scored[scored["reference_year"] == second]
        joined = left.merge(
            right[["person_id", "cohort"]],
            on="person_id",
            suffixes=("", "_later"),
        )
        if same_cohort is not None:
            joined = joined[
                (joined["cohort"] == same_cohort)
                & (joined["cohort_later"] == same_cohort)
            ]
        return joined

    step = horizon_years[0] - boundary_year
    one_step = [
        (year, year + step)
        for year in reference_years
        if year + step in reference_years
    ]
    change: dict[str, Any] = {}
    for name, _, _ in EARN_COHORTS:
        joined = pd.concat(
            [pairs(a, b, name) for a, b in one_step], ignore_index=True
        )
        change[name] = _weight_summary(joined)
    change["pooled_one_step"] = _weight_summary(
        pd.concat([pairs(a, b, None) for a, b in one_step], ignore_index=True)
    )
    change["pooled_two_step"] = _weight_summary(
        pairs(boundary_year, horizon_years[-1], None)
    )
    result["change_pairs"] = change

    dispositions: dict[str, Any] = {}
    for year in horizon_years:
        wave = year + WAVE_OFFSET
        at_wave = person_wave[
            (person_wave["period"] == wave)
            & person_wave["person_id"].isin(domain_ids)
        ].set_index("person_id")
        year_rows = rows[
            (rows["reference_year"] == year)
            & rows["person_id"].isin(domain_ids)
        ].set_index("person_id")
        head_codes, spouse_codes = family._relationship_codes(wave)
        codes = frozenset((*head_codes, *spouse_codes))
        labels = {
            person_id: _disposition(
                person_id, at_wave, year_rows, codes, low, high
            )
            for person_id in sorted(domain_ids)
        }
        counts = pd.Series(labels, dtype=object).value_counts()
        if unknown := set(counts.index) - set(DISPOSITIONS):
            raise AssertionError(f"unregistered dispositions {unknown}")
        dispositions[str(year)] = {
            name: int(counts.get(name, 0)) for name in DISPOSITIONS
        }
    result["domain_dispositions"] = dispositions

    entrants: dict[str, Any] = {}
    for year in horizon_years:
        year_valid = valid[
            (valid["reference_year"] == year)
            & valid["in_support"]
            & ~valid["person_id"].isin(domain_ids)
        ]
        in_anchor = year_valid["person_id"].isin(anchor_ids)
        entrants[str(year)] = {
            "in_2011_anchor_without_valid_boundary_row": {
                name: int(((year_valid["cohort"] == name) & in_anchor).sum())
                for name, _, _ in EARN_COHORTS
            },
            "outside_2011_anchor": {
                name: int(((year_valid["cohort"] == name) & ~in_anchor).sum())
                for name, _, _ in EARN_COHORTS
            },
        }
    result["entrants_not_scored"] = entrants
    return result


def _disposition(
    person_id: int,
    at_wave: pd.DataFrame,
    year_rows: pd.DataFrame,
    head_spouse_codes: frozenset[int],
    low: int,
    high: int,
) -> str:
    """Assign one :data:`DISPOSITIONS` label, in precedence order."""
    if person_id in year_rows.index:
        row = year_rows.loc[person_id]
        if bool(row["valid"]):
            if low <= float(row["age"]) <= high:
                return "scored"
            return "valid_row_age_outside_support"
        if bool(row["weight_positive"]):
            return "head_or_spouse_earnings_missing"
        return "present_nonpositive_weight"
    if person_id not in at_wave.index:
        return "not_in_responding_family"
    record = at_wave.loc[person_id]
    group = _sequence_group(pd.Series([record["sequence"]])).iloc[0]
    if group == "in_family":
        if not float(record["weight"]) > 0:
            return "present_nonpositive_weight"
        if int(record["relationship"]) in head_spouse_codes:
            return "present_no_family_record"
        return "present_other_relationship"
    if group in ("institution", "moved_out", "died"):
        return group
    return "not_in_responding_family"


# --------------------------------------------------------------------------
# Design-based power (no outcome enters)
# --------------------------------------------------------------------------
def half_normal_floor_ratio(k: int = M6_K) -> float:
    """Tolerance / sigma for round(mean + k*sd) of a half-normal score."""
    return math.sqrt(2.0 / math.pi) + k * math.sqrt(1.0 - 2.0 / math.pi)


def cell_pass_probability(ratio: float) -> float:
    """P(|X| <= ratio * sigma) for X ~ N(0, sigma^2)."""
    return float(2.0 * norm.cdf(ratio) - 1.0)


def p_gate(p_seed: float, required: int = 4, total: int = 5) -> float:
    """P(at least ``required`` of ``total`` independent seeds pass)."""
    return float(
        sum(
            math.comb(total, j) * p_seed**j * (1.0 - p_seed) ** (total - j)
            for j in range(required, total + 1)
        )
    )


def max_uncapped_surface(
    ratio: float, target: float = POWER_TARGET, limit: int = 64
) -> int:
    """Largest cell count m with p_gate(p_cell ** m) >= target."""
    p_cell = cell_pass_probability(ratio)
    best = 0
    for m in range(1, limit + 1):
        if p_gate(p_cell**m) >= target:
            best = m
    return best


def bonferroni_z(m: int, alpha: float = ALPHA) -> float:
    """Two-sided simultaneous critical value over ``m`` cells."""
    if m < 1:
        raise ValueError("cell family must have at least one cell")
    return float(norm.ppf(1.0 - alpha / (2.0 * m)))


def bound_rule_ratio(
    m: int, power: float = POWER_TARGET, alpha: float = ALPHA
) -> float:
    """Tolerance / se a faithful cell needs to pass the bound rule.

    The §5.2 rule passes a cell when |g| + z* se <= tol. With g ~ N(0, se^2)
    that has probability 2 Phi(tol/se - z*) - 1, which reaches ``power``
    when tol/se >= z* + Phi^-1((1 + power) / 2).
    """
    return bonferroni_z(m, alpha) + float(norm.ppf((1.0 + power) / 2.0))


def bound_rule_pass_probability(
    ratio: float, m: int, alpha: float = ALPHA
) -> float:
    """P(a faithful cell passes the bound rule) at tol/se = ``ratio``."""
    margin = ratio - bonferroni_z(m, alpha)
    return max(0.0, float(2.0 * norm.cdf(margin) - 1.0))


def required_n_eff_proportion(
    tol: float, m: int, draws: int = M6_DRAWS
) -> float:
    """Worst-case (p = 1/2) effective size for an absolute-pp cell."""
    inflation = math.sqrt(1.0 + 1.0 / draws)
    return (0.5 * bound_rule_ratio(m) * inflation / tol) ** 2


def required_n_eff_correlation(
    tol: float, m: int, draws: int = M6_DRAWS
) -> float:
    """Effective pairs for a correlation cell (delta-method se <= 1/sqrt n)."""
    inflation = math.sqrt(1.0 + 1.0 / draws)
    return (bound_rule_ratio(m) * inflation / tol) ** 2


def max_log_sd_for_quantile(
    tol_log: float, q: float, n_eff: float, m: int, draws: int = M6_DRAWS
) -> float:
    """Largest log-earnings SD (log-normal planning) a quantile cell allows.

    se(ln xi_q) = sigma * sqrt(q (1 - q) / n) / phi(z_q) under a log-normal
    planning model; the cell is feasible when sigma is at most this value.
    """
    inflation = math.sqrt(1.0 + 1.0 / draws)
    z_q = float(norm.ppf(q))
    return (
        tol_log
        * float(norm.pdf(z_q))
        * math.sqrt(n_eff)
        / (bound_rule_ratio(m) * inflation * math.sqrt(q * (1.0 - q)))
    )


def min_draws_for_mc(ratio_tol_se: float, fraction: float = MC_FRACTION):
    """Smallest K with se/sqrt(K) < fraction * tol when tol = ratio * se."""
    bound = (1.0 / (fraction * ratio_tol_se)) ** 2
    return int(math.floor(bound)) + 1


def _required_share(needed: float, available: float) -> float | None:
    """Minimum positive share of ``available``; None when there is none.

    A share above 1 means the cell cannot reach the limit even if every
    row were a positive earner; None means the support is empty.
    """
    if available <= 0:
        return None
    return round(needed / available, 4)


def power_record(counts: Mapping[str, Any]) -> dict[str, Any]:
    """Structural and sample-size power quantities for the audit."""
    ratio = half_normal_floor_ratio(M6_K)
    p_cell = cell_pass_probability(ratio)
    m6_rule = {
        "floor_ratio_tol_over_sigma_half": round(ratio, 6),
        "cell_pass_probability": round(p_cell, 6),
        "p_gate_by_family_size": {
            str(m): round(p_gate(p_cell**m), 6) for m in FAMILY_SIZES
        },
        "max_uncapped_cells_at_0_90": max_uncapped_surface(ratio),
        "tol_over_se_full": round(2.0 * ratio, 6),
        "tol_over_se_half": round(math.sqrt(2.0) * ratio, 6),
        "min_draws_mc_full_support": min_draws_for_mc(2.0 * ratio),
        "min_draws_mc_half_support": min_draws_for_mc(math.sqrt(2.0) * ratio),
    }
    bound_rule = {}
    for m in FAMILY_SIZES:
        needed = bound_rule_ratio(m)
        bound_rule[str(m)] = {
            "bonferroni_z": round(bonferroni_z(m), 6),
            "required_tol_over_se": round(needed, 6),
            "pass_probability_at_m6_floor_tolerance_gap_sigma_half": round(
                bound_rule_pass_probability(ratio, m), 6
            ),
            "k_needed_for_floor_tolerance": round(
                (needed - math.sqrt(2.0 / math.pi))
                / math.sqrt(1.0 - 2.0 / math.pi),
                6,
            ),
        }

    limits: dict[str, Any] = {}
    level = counts["level_cells"]
    change = counts["change_pairs"]
    tol_q = math.log(1.0 + SECTION_5_3_LIMITS["quantile_relative"])
    for m in FAMILY_SIZES:
        by_cohort: dict[str, Any] = {}
        for name, _, _ in EARN_COHORTS:
            cell = level[name]
            need_p = required_n_eff_proportion(
                SECTION_5_3_LIMITS["participation_pp"], m
            )
            by_cohort[name] = {
                "participation_required_n_eff_worst_p": round(need_p, 1),
                "participation_feasible_kish": cell["kish_n_eff"] >= need_p,
                "participation_feasible_cluster_worst": (
                    cell["cluster_worst_n_eff"] >= need_p
                ),
                "quantile_max_log_sd_if_all_positive": {
                    f"p{int(q * 100)}": {
                        "kish": round(
                            max_log_sd_for_quantile(
                                tol_q, q, cell["kish_n_eff"], m
                            ),
                            4,
                        ),
                        "cluster_worst": round(
                            max_log_sd_for_quantile(
                                tol_q, q, cell["cluster_worst_n_eff"], m
                            ),
                            4,
                        ),
                    }
                    for q in (0.1, 0.5, 0.9)
                },
            }
        need_r = required_n_eff_correlation(
            SECTION_5_3_LIMITS["persistence_correlation"], m
        )
        pairs = {
            "lag1_pooled_one_step": change["pooled_one_step"],
            "lag2_pooled_two_step": change["pooled_two_step"],
        }
        persistence = {
            key: {
                "required_positive_pair_n_eff": round(need_r, 1),
                "min_positive_share_kish": _required_share(
                    need_r, value["kish_n_eff"]
                ),
                "min_positive_share_cluster_worst": _required_share(
                    need_r, value["cluster_worst_n_eff"]
                ),
            }
            for key, value in pairs.items()
        }
        limits[str(m)] = {
            "by_cohort": by_cohort,
            "persistence": persistence,
        }
    return {
        "m6_floor_rule": m6_rule,
        "section_5_2_bound_rule": bound_rule,
        "section_5_3_limits_on_b2_support": limits,
        "draws": M6_DRAWS,
        "alpha": ALPHA,
        "power_target": POWER_TARGET,
    }


# --------------------------------------------------------------------------
# Source identity (runs only against staged data)
# --------------------------------------------------------------------------
def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _individual_variables(
    data_dir: Path, waves: Iterable[int]
) -> dict[str, Any]:
    concepts = {
        name: panels.DEMOGRAPHIC_CONCEPTS[name]
        for name in ("age", "sequence", "relationship", "weight", "interview")
    }
    sps = data_dir / "ind2023er" / "IND2023ER.sps"
    labels = psid.parse_sps_labels(sps)
    resolved, _ = panels._resolve_concepts(labels, concepts)
    return {
        str(wave): {
            concept: {
                "variable": resolved[concept][wave],
                "label": " ".join(labels[resolved[concept][wave]].split()),
            }
            for concept in concepts
        }
        for wave in waves
    }


def _family_variables(data_dir: Path, wave: int) -> dict[str, Any]:
    sps, _ = family._family_paths(wave, data_dir)
    labels = psid.parse_sps_labels(sps)
    interview = family._single(
        labels,
        rf"^{wave} (INTERVIEW #|FAMILY INTERVIEW \(ID\) NUMBER)$",
        wave,
        "interview number",
    )
    head = family._single(labels, family._HEAD_LABOR, wave, "head labor")
    spouse = family._single(labels, family._SPOUSE_LABOR, wave, "spouse labor")
    family._check_reference_year(labels[head], wave)
    family._check_reference_year(labels[spouse], wave)

    def entry(name: str) -> dict[str, str]:
        return {"variable": name, "label": " ".join(labels[name].split())}

    return {
        "interview": entry(interview),
        "head_labor": entry(head),
        "spouse_labor": entry(spouse),
        "head_accuracy": [
            entry(name)
            for name in family._acc_component_vars(labels, wave, "head")
        ],
        "spouse_accuracy": [
            entry(name)
            for name in family._acc_component_vars(labels, wave, "spouse")
        ],
    }


def _fit_window_file_hashes(data_dir: Path) -> dict[str, str]:
    waves = [
        wave
        for wave in family.FAMILY_WAVES
        if wave - WAVE_OFFSET <= HORIZON_YEARS[-1]
    ]
    out: dict[str, str] = {}
    for wave in waves:
        sps, txt = family._family_paths(wave, data_dir)
        for path in (sps, txt):
            out[str(path.relative_to(data_dir))] = _sha256_file(path)
    for name in ("IND2023ER.txt", "IND2023ER.sps"):
        path = data_dir / "ind2023er" / name
        out[str(path.relative_to(data_dir))] = _sha256_file(path)
    return out


def _nawi_check(ssa_dir: Path | None) -> dict[str, Any]:
    if ssa_dir is None:
        return {"checked": False, "reason": "no --pe-us-ssa-dir supplied"}
    sys.path.insert(0, str(ROOT / "scripts"))
    import select_m6_qstar_train_only as selector  # noqa: E402

    path = Path(ssa_dir) / "nawi.yaml"
    values, audit = selector._read_historical_nawi(
        path, maximum_year=BOUNDARY_YEAR
    )
    expected = selector.EXPECTED_BOUNDARY_NAWI[BOUNDARY_YEAR]
    mapping_sha = selector._canonical_sha256(values)
    return {
        "checked": True,
        "path": str(path.resolve()),
        "maximum_admitted_key_year": audit["maximum_admitted_key_year"],
        "prefix_bytes": audit["bytes_consumed_through_maximum_key"],
        "prefix_sha256": audit["admitted_prefix_sha256"],
        "mapping_sha256": mapping_sha,
        "matches_repository_pin": (
            audit["bytes_consumed_through_maximum_key"]
            == expected["prefix_bytes"]
            and audit["admitted_prefix_sha256"] == expected["prefix_sha256"]
            and mapping_sha == expected["mapping_sha256"]
        ),
        "fit_decade_keys_present": sorted(
            set(range(BOUNDARY_YEAR - 9, BOUNDARY_YEAR + 1)) & set(values)
        )
        == list(range(BOUNDARY_YEAR - 9, BOUNDARY_YEAR + 1)),
    }


def _ledger_support_counts() -> dict[str, Any]:
    """Read only count fields of the committed 2010-boundary ledgers."""
    fields = (
        "n_full_anchor",
        "n_domain",
        "truth_support_rows",
        "truth_support_rows_by_period",
        "endpoint_support_rows",
        "support_age_min",
        "support_age_max",
        "anchor_wave",
    )
    out = {}
    for name in (
        "m6_qstar_train_only_selection_results.json",
        "m6_rhostar_train_only_selection_results.json",
    ):
        path = ROOT / "docs" / "analysis" / name
        ledger = json.loads(path.read_text(encoding="utf-8"))
        support = ledger["boundaries"][str(BOUNDARY_YEAR)]["support"]
        out[name] = {field: support[field] for field in fields}
        out[name]["fit_input_rows"] = ledger["boundaries"][str(BOUNDARY_YEAR)][
            "fit_input_rows"
        ]
    return out


def _git(*arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--pe-us-ssa-dir", type=Path, default=None)
    args = parser.parse_args(argv)
    out = args.out if args.out.is_absolute() else ROOT / args.out
    if out.exists():
        raise SystemExit(f"refusing to overwrite {out}")
    if RUNS_DIR.resolve() in out.resolve().parents:
        raise SystemExit("B0.1 writes no file under runs/")

    from populace_dynamics.cohorts.psid2010 import record_files_read

    data_dir = psid._resolve_data_dir(None).resolve()
    waves = [year + WAVE_OFFSET for year in REFERENCE_YEARS]
    concepts = {
        name: panels.DEMOGRAPHIC_CONCEPTS[name]
        for name in ("age", "sequence", "relationship", "weight", "interview")
    }
    with record_files_read(data_dir) as opened:
        person_wave = panels.ind_person_period(
            concepts, data_dir=data_dir, waves=waves
        )
        validity = {
            wave: validity_frame(
                family.read_family_labor(wave, data_dir=data_dir)
            )
            for wave in waves
        }
        individual_vars = _individual_variables(data_dir, waves)
        family_vars = {
            str(wave): _family_variables(data_dir, wave) for wave in waves
        }
    counts = structural_counts(person_wave, validity)
    payload = {
        "schema": SCHEMA,
        "repository_head": _git("rev-parse", "HEAD"),
        "worktree_clean": _git("status", "--porcelain") == "",
        "script_sha256": _sha256_file(Path(__file__)),
        "outcome_blind": {
            "earnings_levels_read_into_counts": False,
            "zero_or_positive_earnings_counted": False,
            "b2_cell_or_floor_computed": False,
            "projection_run": False,
        },
        "geometry": {
            "boundary_reference_year": BOUNDARY_YEAR,
            "horizon_reference_years": list(HORIZON_YEARS),
            "collection_waves": waves,
            "age_support_at_collection_wave": list(AGE_SUPPORT),
            "cohorts": [list(entry) for entry in EARN_COHORTS],
        },
        "psid_dir": str(data_dir),
        "psid_files_opened_sha256": dict(sorted(opened.items())),
        "b2_read_set_sha256": _fit_window_file_hashes(data_dir),
        "individual_variables": individual_vars,
        "family_variables": family_vars,
        "nawi": _nawi_check(args.pe_us_ssa_dir),
        "counts": counts,
        "ledger_support_counts": _ledger_support_counts(),
        "power": power_record(counts),
    }
    out.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
