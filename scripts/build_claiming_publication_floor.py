"""Publication-revision floor for the SSA claim-age reference (#74, B2).

This builds ``runs/claiming_publication_floor_v1.json`` -- a REPORTED,
not gated, artifact. Changes no gate. It exists because the DRAFT
``gate_b2_claiming`` packet (lane ``cap-claiming-pia-gates``) derives
every tolerance it proposes from a floor artifact that did not exist:
the packet's own numbers were computed in that lane and labelled as
such. This builder measures the same quantities from committed inputs
so the packet rests on committed, test-pinned bytes.

Why a PUBLICATION floor and not a sampling floor
================================================
Every locked gate in ``gates.yaml`` prices its tolerances off sampling
noise (person-disjoint splits). Table 6.B5.1 admits no such floor: the
reference's own provenance records it as ``"Master Beneficiary Record,
100 percent data (not a sample) for these entitlement years
1998-2022"``. There is no sample, so no half-split null exists. The
measurable noise is REVISION plus ROUNDING, and SSA states the
mechanism in the table notes carried by both editions: *"Because
entitlements can be awarded retroactively, data for current and prior
years are subject to revision with each annual update of this table."*

What is measured
================
1. **Cross-edition revision.** The committed 2014 edition (entitlement
   years 1998-2013) against the committed 2023 edition on the 1998-2013
   overlap, in two spaces: the PUBLISHED eight-category shares and the
   CONDITIONAL seven-category shares (disability conversions dropped and
   the remainder renormalised to 100 -- the object
   :func:`populace_dynamics.claiming.claim_age_pmf` emits). Stratified
   into settled years (1998-2012) and the terminal year (2013), plus the
   ``average_age`` column.
2. **The derived power cap.** The DRAFT tolerance rule
   ``round(K_REV * revision_sd_terminal + |trend| * horizon + rounding,
   2)`` with the DRAFT knobs, and the gate-eligible / report-only
   partition it produces at ``T_max_pp = 3.0``. Which cells demote is
   DERIVED from the trend term, never hand-picked.
3. **Reference values.** The held-out conditional shares each cell would
   score against, for all 42 (category x sex x horizon) cells.
4. **Both holdout rules.** ``nearest_year`` and ``linear_trend`` fit on
   1998-2019 and scored on 2020-2022, in both spaces, with an explicit
   equality check against the committed ``runs/claiming_reference_v1.json``
   on the published construct the two share.
5. **Candidate rules on the DRAFT gated surface.** The deployed v1
   nearest-year rule fails 6 of the 34 DRAFT gate-eligible cells. That
   finding is REPORTED, NOT GATED -- there is no ``gate_b2_claiming``
   in ``gates.yaml``, this artifact proposes none, and no threshold
   here is ratified.

Nothing here is a threshold. No ``gates.yaml`` block is written, read
for binding, or implied to be locked.

Run from the repository root::

    .venv/bin/python scripts/build_claiming_publication_floor.py
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "runs" / "claiming_publication_floor_v1.json"

EDITION_2023_REL = "data/external/ssa_claim_ages_2023supplement.json"
EDITION_2014_REL = "data/external/ssa_claim_ages_2014supplement.json"
CLAIMING_REFERENCE_REL = "runs/claiming_reference_v1.json"

SCHEMA_VERSION = "claiming_publication_floor.v1"
RUN = "claiming_publication_floor_v1"

#: The stable eight-way published partition (Table 6.B5.1 collapsed).
PUBLISHED_CATEGORIES = (
    "age62",
    "age63",
    "age64",
    "age65",
    "age66",
    "disability_conversion",
    "age67_69",
    "age70plus",
)
#: The seven non-conversion categories the module's PMF spans.
CONDITIONAL_CATEGORIES = tuple(
    category
    for category in PUBLISHED_CATEGORIES
    if category != "disability_conversion"
)

SEXES = ("female", "male")

OVERLAP_YEARS = tuple(range(1998, 2014))
SETTLED_YEARS = tuple(range(1998, 2013))
TERMINAL_YEARS = (2013,)

FIT_YEARS = tuple(range(1998, 2020))
HOLDOUT_YEARS = (2020, 2021, 2022)
HORIZON_OF_YEAR = {2020: 1, 2021: 2, 2022: 3}

#: DRAFT tolerance knobs, quoted from the cap-claiming-pia-gates packet
#: (`gate_b2_claiming.thresholds.gated_surface.derivations.knobs`). They
#: are a PROPOSAL: no referee round has run and `gates.yaml` carries no
#: `gate_b2_claiming`.
K_REV = 2.0
ROUNDING_PP = 0.05
T_MAX_PP = 3.0
TOLERANCE_DECIMALS = 2
STAT_DECIMALS = 6

PACKET = "cap-claiming-pia-gates REPORT.md (2026-09-06, drafting lane)"

#: The sentence in SSA's own table notes that states the revision
#: mechanism this floor measures. Verbatim in BOTH committed editions
#: (their full notes are not otherwise identical).
RETROACTIVE_SENTENCE = (
    "Because entitlements can be awarded retroactively, data for "
    "current and prior years are subject to revision with each annual "
    "update of this table."
)


# --------------------------------------------------------------------------
# Committed-byte helpers
# --------------------------------------------------------------------------
def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text())


def _pin(relative: str) -> dict[str, Any]:
    path = ROOT / relative
    return {
        "path": relative,
        "sha256": _sha256(path),
        "bytes": path.stat().st_size,
    }


# --------------------------------------------------------------------------
# The two share constructs
# --------------------------------------------------------------------------
def published_shares(row: dict[str, Any]) -> dict[str, float]:
    """The published eight-category collapsed shares, as published."""
    return {
        category: float(row["categories"][category])
        for category in PUBLISHED_CATEGORIES
    }


def conditional_shares(row: dict[str, Any]) -> dict[str, float]:
    """The seven non-conversion shares renormalised to sum to 100.

    This is the object ``claim_age_pmf`` emits, re-aggregated to the
    reference's own category partition: the disability-conversion
    column is dropped (an auto-conversion at FRA, not a claiming
    choice; source footnote b) and the remainder is renormalised.
    """
    categories = row["categories"]
    total = sum(categories[name] for name in CONDITIONAL_CATEGORIES)
    return {
        name: 100.0 * float(categories[name]) / total
        for name in CONDITIONAL_CATEGORIES
    }


CONSTRUCTS = {
    "published": (PUBLISHED_CATEGORIES, published_shares),
    "conditional": (CONDITIONAL_CATEGORIES, conditional_shares),
}


# --------------------------------------------------------------------------
# Statistics (closed form; no numpy, so the artifact is bit-stable)
# --------------------------------------------------------------------------
def _round(value: float, decimals: int = STAT_DECIMALS) -> float:
    return round(float(value), decimals)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _population_sd(values: list[float]) -> float:
    mean = _mean(values)
    return (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5


def _sample_sd(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = _mean(values)
    return (sum((v - mean) ** 2 for v in values) / (len(values) - 1)) ** 0.5


def _ols_slope(xs: tuple[int, ...], ys: list[float]) -> tuple[float, float]:
    """Closed-form OLS slope and intercept (deterministic, no numpy)."""
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    numerator = sum(
        (x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True)
    )
    denominator = sum((x - mean_x) ** 2 for x in xs)
    slope = numerator / denominator
    return slope, mean_y - slope * mean_x


# --------------------------------------------------------------------------
# Cross-edition revision
# --------------------------------------------------------------------------
def _revision_cells(
    doc_2014: dict[str, Any],
    doc_2023: dict[str, Any],
    construct: str,
    years: tuple[int, ...],
) -> list[dict[str, Any]]:
    categories, shares = CONSTRUCTS[construct]
    cells: list[dict[str, Any]] = []
    for sex in SEXES:
        for year in years:
            old = shares(doc_2014["data"][sex][str(year)])
            new = shares(doc_2023["data"][sex][str(year)])
            for category in categories:
                cells.append(
                    {
                        "sex": sex,
                        "year": year,
                        "category": category,
                        "edition_2014_pp": _round(old[category]),
                        "edition_2023_pp": _round(new[category]),
                        "revision_pp": _round(new[category] - old[category]),
                    }
                )
    return cells


def _stratum(cells: list[dict[str, Any]]) -> dict[str, Any]:
    magnitudes = [abs(cell["revision_pp"]) for cell in cells]
    argmax = max(cells, key=lambda cell: abs(cell["revision_pp"]))
    return {
        "n_cells": len(cells),
        "nonzero_cells": sum(1 for m in magnitudes if m > 0.0),
        "mean_pp": _round(_mean(magnitudes)),
        "sd_pp": _round(_population_sd(magnitudes)),
        "sd_sample_pp": _round(_sample_sd(magnitudes)),
        "max_pp": _round(max(magnitudes)),
        "argmax": {
            "sex": argmax["sex"],
            "year": argmax["year"],
            "category": argmax["category"],
            "revision_pp": argmax["revision_pp"],
        },
        "sd_convention": (
            "sd_pp is the POPULATION standard deviation (ddof=0) of the "
            "absolute per-cell revisions; sd_sample_pp is the ddof=1 "
            "value. The DRAFT tolerance knob quotes sd_pp."
        ),
    }


def _average_age_stratum(
    doc_2014: dict[str, Any], doc_2023: dict[str, Any]
) -> dict[str, Any]:
    rows = []
    for sex in SEXES:
        for year in OVERLAP_YEARS:
            old = float(doc_2014["data"][sex][str(year)]["average_age"])
            new = float(doc_2023["data"][sex][str(year)]["average_age"])
            rows.append(
                {
                    "sex": sex,
                    "year": year,
                    "edition_2014_years": old,
                    "edition_2023_years": new,
                    "revision_years": _round(new - old),
                }
            )
    magnitudes = [abs(row["revision_years"]) for row in rows]
    return {
        "n_rows": len(rows),
        "nonzero_rows": sum(1 for m in magnitudes if m > 0.0),
        "mean_years": _round(_mean(magnitudes)),
        "max_years": _round(max(magnitudes)),
    }


# --------------------------------------------------------------------------
# The DRAFT tolerance surface
# --------------------------------------------------------------------------
def _cell_key(category: str, sex: str, horizon: int) -> str:
    return f"{category}|{sex}|h{horizon}"


def _fit_series(
    doc_2023: dict[str, Any], construct: str
) -> dict[tuple[str, str], list[float]]:
    _, shares = CONSTRUCTS[construct]
    return {
        (category, sex): [
            shares(doc_2023["data"][sex][str(year)])[category]
            for year in FIT_YEARS
        ]
        for sex in SEXES
        for category in CONSTRUCTS[construct][0]
    }


def _actuals(
    doc_2023: dict[str, Any], construct: str
) -> dict[tuple[str, str, int], float]:
    _, shares = CONSTRUCTS[construct]
    return {
        (category, sex, HORIZON_OF_YEAR[year]): shares(
            doc_2023["data"][sex][str(year)]
        )[category]
        for sex in SEXES
        for category in CONSTRUCTS[construct][0]
        for year in HOLDOUT_YEARS
    }


def _tolerance(sd_pp: float, trend: float, horizon: int) -> float:
    return round(
        K_REV * sd_pp + abs(trend) * horizon + ROUNDING_PP,
        TOLERANCE_DECIMALS,
    )


def _power_cap(
    fit_series: dict[tuple[str, str], list[float]],
    sd_knob: float,
    sd_full: float,
) -> dict[str, Any]:
    gated: dict[str, float] = {}
    report_only: dict[str, dict[str, Any]] = {}
    derivations: dict[str, dict[str, Any]] = {}
    knob_sensitive: dict[str, dict[str, Any]] = {}
    eligibility_flips: list[str] = []
    for sex in SEXES:
        for category in CONDITIONAL_CATEGORIES:
            slope, _ = _ols_slope(FIT_YEARS, fit_series[(category, sex)])
            trend = round(slope, 4)
            for horizon in (1, 2, 3):
                key = _cell_key(category, sex, horizon)
                tolerance = _tolerance(sd_knob, trend, horizon)
                at_full = _tolerance(sd_full, trend, horizon)
                if (tolerance <= T_MAX_PP) != (at_full <= T_MAX_PP):
                    eligibility_flips.append(key)
                if tolerance != at_full:
                    knob_sensitive[key] = {
                        "tolerance_pp_at_rounded_sd": tolerance,
                        "tolerance_pp_at_full_precision_sd": at_full,
                        "unrounded_pp": _round(
                            K_REV * sd_knob
                            + abs(trend) * horizon
                            + ROUNDING_PP
                        ),
                    }
                derivations[key] = {
                    "trend_pp_per_year": trend,
                    "horizon_years": horizon,
                    "rounding": TOLERANCE_DECIMALS,
                    "tolerance_pp": tolerance,
                    "tolerance_pp_at_full_precision_sd": at_full,
                }
                if tolerance <= T_MAX_PP:
                    gated[key] = tolerance
                else:
                    report_only[key] = {
                        "tolerance_pp_would_be": tolerance,
                        "trend_pp_per_year": trend,
                        "reason": "tolerance_above_t_max",
                    }
    return {
        "rule": (
            "tolerance_pp == round(K_REV * revision_sd_terminal_pp + "
            "abs(trend_pp_per_year) * horizon_years + rounding_pp, 2); "
            "a cell is gate-eligible iff tolerance_pp <= t_max_pp"
        ),
        "knobs": {
            "k_rev": K_REV,
            "revision_sd_terminal_pp": sd_knob,
            "revision_sd_terminal_pp_full_precision": _round(sd_full),
            "rounding_pp": ROUNDING_PP,
            "t_max_pp": T_MAX_PP,
            "fit_window": [FIT_YEARS[0], FIT_YEARS[-1]],
            "horizon_years": [1, 2, 3],
            "trend_estimator": (
                "closed-form OLS slope of the conditional share on the "
                "fit years, rounded to 4 decimals"
            ),
        },
        "knobs_are_a_draft_proposal": (
            "K_REV, the rounding allowance and T_max_pp are quoted from "
            f"the {PACKET} DRAFT gate_b2_claiming block. gates.yaml "
            "carries no gate_b2_claiming; nothing here is ratified and "
            "this artifact proposes no threshold."
        ),
        "sd_knob_rounding_check": {
            "note": (
                "The DRAFT knob rounds the measured terminal-year sd to "
                "4 decimals. This block records every cell whose "
                "2-decimal tolerance changes when the full-precision sd "
                "is used instead, and whether any cell's gate-eligible "
                "status changes with it."
            ),
            "partition_identical": not eligibility_flips,
            "n_gate_eligibility_flips": len(eligibility_flips),
            "gate_eligibility_flips": sorted(eligibility_flips),
            "n_cells_with_a_different_tolerance": len(knob_sensitive),
            "cells_with_a_different_tolerance": knob_sensitive,
        },
        "n_gate_eligible": len(gated),
        "n_report_only_tolerance_above_t_max": len(report_only),
        "gate_eligible_tolerances_pp": gated,
        "report_only_tolerance_above_t_max": report_only,
        "derivations": derivations,
        "out_of_module_scope": {
            "cells": [
                _cell_key("disability_conversion", sex, horizon)
                for sex in SEXES
                for horizon in (1, 2, 3)
            ],
            "reason": "conversion_flow_owned_by_di_surface",
            "basis": (
                "The conditional construct excludes the "
                "disability-conversion column before any tolerance is "
                "derived, so these six cells never enter the surface. "
                "They are named here so the exclusion is visible as a "
                "SCOPE decision taken before any candidate runs, not a "
                "power-cap demotion and not a candidate's performance."
            ),
        },
    }


# --------------------------------------------------------------------------
# Holdout rules
# --------------------------------------------------------------------------
def _predict(
    rule: str,
    fit_values: list[float],
    slope: float,
    intercept: float,
    year: int,
) -> float:
    if rule == "nearest_year":
        return fit_values[-1]
    if rule == "linear_trend":
        return intercept + slope * year
    raise ValueError(rule)


def _holdout_block(
    doc_2023: dict[str, Any], construct: str, rule: str
) -> dict[str, Any]:
    categories, shares = CONSTRUCTS[construct]
    per_cell: list[dict[str, Any]] = []
    # The published-construct arithmetic is byte-identical to
    # scripts/build_claiming_reference.py: predictions are rounded to 4
    # decimals and the deviation is the rounded difference, so the two
    # artifacts' headline numbers are comparable without translation.
    for sex in ("male", "female") if construct == "published" else SEXES:
        for category in categories:
            fit_values = [
                shares(doc_2023["data"][sex][str(year)])[category]
                for year in FIT_YEARS
            ]
            slope, intercept = _ols_slope(FIT_YEARS, fit_values)
            for year in HOLDOUT_YEARS:
                actual = shares(doc_2023["data"][sex][str(year)])[category]
                predicted = _predict(rule, fit_values, slope, intercept, year)
                per_cell.append(
                    {
                        "sex": sex,
                        "year": year,
                        "horizon": HORIZON_OF_YEAR[year],
                        "category": category,
                        "predicted": round(predicted, 4),
                        "actual": round(actual, 4),
                        "deviation": round(round(predicted, 4) - actual, 4),
                    }
                )
    magnitudes = [abs(cell["deviation"]) for cell in per_cell]
    argmax = max(per_cell, key=lambda cell: abs(cell["deviation"]))
    return {
        "n_cells": len(per_cell),
        "max_abs_deviation": round(max(magnitudes), 4),
        "mean_abs_deviation": round(_mean(magnitudes), 4),
        "rmse": round(
            (sum(m * m for m in magnitudes) / len(magnitudes)) ** 0.5, 4
        ),
        "argmax": argmax,
        "per_cell": per_cell,
    }


def _reference_cross_check(published: dict[str, Any]) -> dict[str, Any]:
    """Equality check against the committed claiming_reference_v1."""
    committed = _load(CLAIMING_REFERENCE_REL)
    checks = {}
    matches = True
    for rule in ("nearest_year", "linear_trend"):
        theirs = committed["results"][rule]
        ours = published[rule]
        row = {
            "committed_max_abs_deviation": theirs["max_abs_deviation"],
            "rebuilt_max_abs_deviation": ours["max_abs_deviation"],
            "committed_mean_abs_deviation": theirs["mean_abs_deviation"],
            "rebuilt_mean_abs_deviation": ours["mean_abs_deviation"],
            "committed_rmse": theirs["rmse"],
            "rebuilt_rmse": ours["rmse"],
            "committed_n_cells": theirs["n_cells"],
            "rebuilt_n_cells": ours["n_cells"],
        }
        row["match"] = (
            theirs["max_abs_deviation"] == ours["max_abs_deviation"]
            and theirs["mean_abs_deviation"] == ours["mean_abs_deviation"]
            and theirs["rmse"] == ours["rmse"]
            and theirs["n_cells"] == ours["n_cells"]
        )
        matches = matches and row["match"]
        checks[rule] = row
    return {
        "artifact": CLAIMING_REFERENCE_REL,
        "artifact_pin": _pin(CLAIMING_REFERENCE_REL),
        "overlap": (
            "the PUBLISHED eight-category construct and the same "
            "fit 1998-2019 / predict 2020-2022 protocol; "
            "claiming_reference_v1 scores only that construct"
        ),
        "all_match": matches,
        "rules": checks,
    }


# --------------------------------------------------------------------------
# Candidate rules on the DRAFT gate-eligible surface
# --------------------------------------------------------------------------
def _candidate_predictors(
    fit_series: dict[tuple[str, str], list[float]],
) -> dict[str, Any]:
    """Named rules, each a callable (category, sex, horizon) -> pp."""

    def nearest_year(category, sex, horizon):
        return fit_series[(category, sex)][-1]

    def uniform(category, sex, horizon):
        return 100.0 / len(CONDITIONAL_CATEGORIES)

    def fit_window_mean(category, sex, horizon):
        return _mean(fit_series[(category, sex)])

    def sex_pooled_nearest_year(category, sex, horizon):
        return _mean([fit_series[(category, other)][-1] for other in SEXES])

    def ols(window):
        def predict(category, sex, horizon):
            values = fit_series[(category, sex)][-window:]
            years = FIT_YEARS[-window:]
            slope, intercept = _ols_slope(years, values)
            return intercept + slope * (FIT_YEARS[-1] + horizon)

        return predict

    def damped(window, delta):
        def predict(category, sex, horizon):
            values = fit_series[(category, sex)][-window:]
            years = FIT_YEARS[-window:]
            slope, _ = _ols_slope(years, values)
            return fit_series[(category, sex)][-1] + delta * slope * horizon

        return predict

    return {
        "deployed_v1_nearest_year": {
            "rule_class": "forecast",
            "description": (
                "the module's documented default: predict every "
                "out-of-range year with the last fit year (2019) "
                "(populace_dynamics.claiming._resolve_year)"
            ),
            "predict": nearest_year,
        },
        "uniform_over_seven_categories": {
            "rule_class": "degenerate",
            "description": "every category 100/7 pp",
            "predict": uniform,
        },
        "fit_window_mean": {
            "rule_class": "degenerate",
            "description": "predict each cell by its own 1998-2019 mean",
            "predict": fit_window_mean,
        },
        "sex_pooled_nearest_year": {
            "rule_class": "degenerate",
            "description": "nearest-year with the two sexes averaged",
            "predict": sex_pooled_nearest_year,
        },
        "ols_full_fit_window": {
            "rule_class": "forecast",
            "description": "OLS on all 22 fit years, extrapolated",
            "predict": ols(22),
        },
        "ols_last_10": {
            "rule_class": "forecast",
            "description": "OLS on the last ten fit years",
            "predict": ols(10),
        },
        "ols_last_5": {
            "rule_class": "forecast",
            "description": "OLS on the last five fit years (2015-2019)",
            "predict": ols(5),
        },
        "ols_last_3": {
            "rule_class": "forecast",
            "description": "OLS on the last three fit years",
            "predict": ols(3),
        },
        "damped_local_trend_w5_d0.5": {
            "rule_class": "forecast",
            "description": "last fit value plus half the 5-year slope",
            "predict": damped(5, 0.5),
        },
        "damped_local_trend_w5_d1.0": {
            "rule_class": "forecast",
            "description": "last fit value plus the full 5-year slope",
            "predict": damped(5, 1.0),
        },
        "damped_local_trend_w10_d0.5": {
            "rule_class": "forecast",
            "description": "last fit value plus half the 10-year slope",
            "predict": damped(10, 0.5),
        },
    }


def _deviation_arithmetic(
    holdout_per_cell: list[dict[str, Any]],
    fit_series: dict[tuple[str, str], list[float]],
    actuals: dict[tuple[str, str, int], float],
    tolerances: dict[str, float],
) -> dict[str, Any]:
    """Reconcile the two deviation arithmetics this artifact carries.

    ``holdout_rules`` rounds each prediction to 4 decimals BEFORE
    differencing, because that is byte-for-byte what
    ``scripts/build_claiming_reference.py`` does and the published
    construct has to reproduce that committed artifact exactly.
    ``candidate_rules_on_the_draft_surface`` -- and the
    ``deployed_v1_finding`` that reads its numbers -- differences the
    unrounded prediction and rounds once at the end, a candidate scan
    being under no such constraint.

    The nearest-year rule appears under both, so the SAME cell can
    carry two values one 4-decimal ulp apart (``age62|female|h1`` is
    3.8086 in one and 3.8087 in the other). This block names every cell
    where they differ, so a referee reading the JSON is not left to
    reconcile that unaided, and records whether any gate-eligible
    verdict depends on the choice.
    """
    predict = _candidate_predictors(fit_series)["deployed_v1_nearest_year"][
        "predict"
    ]
    rounded = {
        _cell_key(cell["category"], cell["sex"], cell["horizon"]): abs(
            cell["deviation"]
        )
        for cell in holdout_per_cell
    }
    differing: dict[str, Any] = {}
    flips: list[str] = []
    closest_margin: float | None = None
    for key, tolerance in sorted(tolerances.items()):
        category, sex, horizon = key.split("|")
        horizon_n = int(horizon[1:])
        unrounded = round(
            abs(
                predict(category, sex, horizon_n)
                - actuals[(category, sex, horizon_n)]
            ),
            4,
        )
        margin = min(abs(rounded[key] - tolerance), abs(unrounded - tolerance))
        closest_margin = (
            margin if closest_margin is None else min(closest_margin, margin)
        )
        if unrounded == rounded[key]:
            continue
        fails_rounded = rounded[key] > tolerance
        fails_unrounded = unrounded > tolerance
        if fails_rounded != fails_unrounded:
            flips.append(key)
        differing[key] = {
            "rounded_prediction_path_pp": rounded[key],
            "unrounded_prediction_path_pp": unrounded,
            "difference_pp": _round(abs(unrounded - rounded[key]), 4),
            "tolerance_pp": tolerance,
            "exceeds_tolerance_either_way": fails_rounded == fails_unrounded,
        }
    differences = [block["difference_pp"] for block in differing.values()]
    return {
        "note": (
            "Two arithmetics, both deliberate, reported side by side. "
            "holdout_rules rounds the prediction to 4 decimals before "
            "differencing (matching scripts/build_claiming_reference.py "
            "so the published construct reproduces the committed "
            "artifact exactly); candidate_rules_on_the_draft_surface "
            "and deployed_v1_finding difference the unrounded "
            "prediction and round once. They differ by at most one "
            "4-decimal ulp."
        ),
        "rounded_prediction_path": (
            "holdout_rules.per_cell.*, holdout_rules.published.*, "
            "holdout_rules.conditional.*, reproduces_claiming_reference_v1"
        ),
        "unrounded_prediction_path": (
            "candidate_rules_on_the_draft_surface.*, deployed_v1_finding"
        ),
        "surface": (
            "the 34 DRAFT gate-eligible cells, under the deployed "
            "nearest-year rule -- the one rule both paths score"
        ),
        "n_cells_compared": len(tolerances),
        "n_cells_differing": len(differing),
        "max_abs_difference_pp": (
            _round(max(differences), 4) if differences else 0.0
        ),
        "n_verdict_flips": len(flips),
        "verdict_flips": flips,
        "verdict_identical_under_both_paths": not flips,
        "closest_any_cell_comes_to_its_tolerance_pp": _round(
            closest_margin if closest_margin is not None else 0.0, 4
        ),
        "why_no_flip_is_possible_here": (
            "the largest disagreement between the paths is one "
            "4-decimal ulp, and no gate-eligible cell sits within that "
            "of its tolerance -- see "
            "closest_any_cell_comes_to_its_tolerance_pp"
        ),
        "cells": differing,
    }


def _score_candidates(
    fit_series: dict[tuple[str, str], list[float]],
    actuals: dict[tuple[str, str, int], float],
    tolerances: dict[str, float],
) -> dict[str, Any]:
    candidates = _candidate_predictors(fit_series)
    scored: dict[str, Any] = {}
    envelope: dict[str, float] = {}
    for name, spec in candidates.items():
        deviations: dict[str, float] = {}
        failures: list[str] = []
        for sex in SEXES:
            for category in CONDITIONAL_CATEGORIES:
                for horizon in (1, 2, 3):
                    key = _cell_key(category, sex, horizon)
                    if key not in tolerances:
                        continue
                    predicted = spec["predict"](category, sex, horizon)
                    deviation = abs(
                        predicted - actuals[(category, sex, horizon)]
                    )
                    deviations[key] = round(deviation, 4)
                    if deviation > tolerances[key]:
                        failures.append(key)
                    if spec["rule_class"] == "forecast":
                        envelope[key] = min(
                            envelope.get(key, deviation), deviation
                        )
        magnitudes = list(deviations.values())
        scored[name] = {
            "rule_class": spec["rule_class"],
            "description": spec["description"],
            "n_gate_eligible_cells": len(magnitudes),
            "n_failed": len(failures),
            "failing_cells": sorted(failures),
            "max_abs_deviation_pp": round(max(magnitudes), 4),
            "mean_abs_deviation_pp": round(_mean(magnitudes), 4),
        }
    envelope_failures = sorted(
        key for key, value in envelope.items() if value > tolerances[key]
    )
    return {
        "surface": (
            "the 34 DRAFT gate-eligible (category x sex x horizon) "
            "cells of the conditional construct"
        ),
        "rule_classes": {
            "forecast": (
                "rules that predict a held-out year from the fit "
                "window's own level and trend. These bound the "
                "achievable frontier."
            ),
            "degenerate": (
                "shapeless, level-only and sex-blind rules, included "
                "to show which dimensions the surface has bite on. "
                "They are NOT part of the frontier envelope: a "
                "degenerate rule that lands near a cell by accident "
                "would otherwise flatter it."
            ),
        },
        "rules": scored,
        "post_hoc_best_of_forecast_class_envelope": {
            "description": (
                "per cell, the smallest absolute deviation achieved by "
                "any FORECAST-class rule above. NOT prospectively "
                "achievable -- it picks the best rule per cell after "
                "the fact -- and reported only to bound the frontier."
            ),
            "rules_in_envelope": sorted(
                name
                for name, spec in candidates.items()
                if spec["rule_class"] == "forecast"
            ),
            "n_failed": len(envelope_failures),
            "failing_cells": envelope_failures,
            "max_abs_deviation_pp": round(max(envelope.values()), 4),
            "mean_abs_deviation_pp": round(_mean(list(envelope.values())), 4),
            "per_cell_pp": {
                key: round(value, 4) for key, value in sorted(envelope.items())
            },
        },
        "every_gate_eligible_cell_failed_by_some_rule": sorted(tolerances)
        == sorted(
            {
                key
                for block in scored.values()
                for key in block["failing_cells"]
            }
        ),
    }


# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------
def build() -> dict[str, Any]:
    doc_2014 = _load(EDITION_2014_REL)
    doc_2023 = _load(EDITION_2023_REL)

    revision_cells = {
        construct: {
            "settled_years": _revision_cells(
                doc_2014, doc_2023, construct, SETTLED_YEARS
            ),
            "terminal_year": _revision_cells(
                doc_2014, doc_2023, construct, TERMINAL_YEARS
            ),
            "all_overlap": _revision_cells(
                doc_2014, doc_2023, construct, OVERLAP_YEARS
            ),
        }
        for construct in CONSTRUCTS
    }
    strata = {
        f"{construct}_{name}": _stratum(cells)
        for construct, blocks in revision_cells.items()
        for name, cells in blocks.items()
    }
    strata["average_age_column"] = _average_age_stratum(doc_2014, doc_2023)

    nonzero = {
        f"{construct}_{name}": [
            {
                "cell": f"{cell['category']}|{cell['sex']}|{cell['year']}",
                "edition_2014_pp": cell["edition_2014_pp"],
                "edition_2023_pp": cell["edition_2023_pp"],
                "revision_pp": cell["revision_pp"],
            }
            for cell in cells
            if cell["revision_pp"] != 0.0
        ]
        for construct, blocks in revision_cells.items()
        for name, cells in blocks.items()
        if name != "all_overlap"
    }

    sd_full = _population_sd(
        [
            abs(cell["revision_pp"])
            for cell in revision_cells["conditional"]["terminal_year"]
        ]
    )
    sd_knob = round(sd_full, 4)

    conditional_fit = _fit_series(doc_2023, "conditional")
    conditional_actuals = _actuals(doc_2023, "conditional")
    power_cap = _power_cap(conditional_fit, sd_knob, sd_full)

    reference_values = {
        _cell_key(category, sex, horizon): _round(
            conditional_actuals[(category, sex, horizon)], 4
        )
        for sex in SEXES
        for category in CONDITIONAL_CATEGORIES
        for horizon in (1, 2, 3)
    }

    holdout = {
        construct: {
            rule: _holdout_block(doc_2023, construct, rule)
            for rule in ("nearest_year", "linear_trend")
        }
        for construct in CONSTRUCTS
    }
    cross_check = _reference_cross_check(holdout["published"])

    candidates = _score_candidates(
        conditional_fit,
        conditional_actuals,
        power_cap["gate_eligible_tolerances_pp"],
    )
    deployed = candidates["rules"]["deployed_v1_nearest_year"]
    deviation_arithmetic = _deviation_arithmetic(
        holdout["conditional"]["nearest_year"]["per_cell"],
        conditional_fit,
        conditional_actuals,
        power_cap["gate_eligible_tolerances_pp"],
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "run": RUN,
        "reported_not_gated": True,
        "purpose": (
            "Publication-revision floor for the SSA claim-age reference "
            "(Table 6.B5.1). Changes no gate. Measures, from committed "
            "inputs, the quantities the DRAFT gate_b2_claiming packet "
            "derives its proposed tolerances from: the cross-edition "
            "revision floor (no sampling floor exists -- the table is "
            "100 percent Master Beneficiary Record data), the derived "
            "power-cap partition, the held-out reference values, and "
            "the two holdout rules' out-of-sample scores. Proposes no "
            "threshold and ratifies none."
        ),
        "component": "claiming-age distribution (#74 component CA)",
        "gate_status": {
            "gates_yaml_block": None,
            "note": (
                "gates.yaml carries no gate_b2_claiming. Every knob and "
                "partition below is a DRAFT proposal from "
                f"{PACKET}; none has been through a referee round and "
                "none is locked."
            ),
        },
        "sources": {
            "edition_2023": _pin(EDITION_2023_REL),
            "edition_2014": _pin(EDITION_2014_REL),
            "claiming_reference_v1": _pin(CLAIMING_REFERENCE_REL),
            "edition_2023_supplement_year": doc_2023["supplement_year"],
            "edition_2014_supplement_year": doc_2014["supplement_year"],
            "table": doc_2023["table"],
            "schema_versions": [
                doc_2014["schema_version"],
                doc_2023["schema_version"],
            ],
        },
        "no_sampling_floor": {
            "mbr_100_percent_note": doc_2023["provenance"][
                "mbr_100_percent_note"
            ],
            "mbr_100_percent_note_2014_edition": doc_2014["provenance"][
                "mbr_100_percent_note"
            ],
            "table_notes": doc_2023["provenance"]["table_notes"],
            "table_notes_2014_edition": doc_2014["provenance"]["table_notes"],
            "table_notes_identical_across_editions": (
                doc_2014["provenance"]["table_notes"]
                == doc_2023["provenance"]["table_notes"]
            ),
            "retroactive_revision_sentence": RETROACTIVE_SENTENCE,
            "retroactive_revision_sentence_in_both_editions": (
                RETROACTIVE_SENTENCE in doc_2014["provenance"]["table_notes"]
                and RETROACTIVE_SENTENCE
                in doc_2023["provenance"]["table_notes"]
            ),
            "table_notes_difference_note": (
                "The two editions' full table notes are NOT identical: "
                "the 2023 edition adds a sentence about differences "
                "from Office of the Chief Actuary statistics and "
                "reorders the footnote key. The sentence this floor "
                "rests on -- retroactive entitlement causing revision "
                "with each annual update -- is verbatim in both, which "
                "is what "
                "retroactive_revision_sentence_in_both_editions "
                "records."
            ),
            "consequence": (
                "Table 6.B5.1 is a 100 percent count, not a sample, so "
                "no person-disjoint half-split null exists and the "
                "sampling-floor construction every locked gate in "
                "gates.yaml uses is inapplicable. The measurable noise "
                "is REVISION plus ROUNDING, which is what this artifact "
                "measures."
            ),
        },
        "construction": {
            "overlap_years": [OVERLAP_YEARS[0], OVERLAP_YEARS[-1]],
            "settled_years": [SETTLED_YEARS[0], SETTLED_YEARS[-1]],
            "terminal_year": TERMINAL_YEARS[0],
            "terminal_year_definition": (
                "the last entitlement year the 2014 edition publishes, "
                "and therefore the year in that edition most exposed to "
                "retroactive revision at the time it was published"
            ),
            "sexes": list(SEXES),
            "published_categories": list(PUBLISHED_CATEGORIES),
            "conditional_categories": list(CONDITIONAL_CATEGORIES),
            "conditional_construct": (
                "the disability-conversion column is dropped and the "
                "remaining seven categories renormalised to sum to 100 "
                "-- the object populace_dynamics.claiming.claim_age_pmf "
                "emits, re-aggregated to the reference's own partition"
            ),
            "metric": (
                "absolute revision in published percentage points "
                "(share on a 0-100 scale), 2023 edition minus 2014 "
                "edition, per (sex, entitlement year, category) cell"
            ),
        },
        "strata": strata,
        "nonzero_revision_cells": nonzero,
        "finding": {
            "revision_is_a_terminal_year_effect": (
                strata["published_terminal_year"]["nonzero_cells"]
                == strata["published_terminal_year"]["n_cells"]
                and strata["published_settled_years"]["nonzero_cells"] <= 1
            ),
            "statement": (
                "Every published terminal-year cell moved; across the "
                "fifteen settled years a single published cell moved, "
                "by one 0.1 pp rounding tick; the average_age column "
                "did not move at all. In the conditional construct that "
                "one published movement propagates through the "
                "renormalising denominator to all seven categories of "
                "its (sex, year) row, which is why the conditional "
                "settled stratum has more nonzero cells than the "
                "published one at the same mean magnitude."
            ),
        },
        "power_cap": power_cap,
        "reference_values_pp": {
            "definition": (
                "the held-out conditional share each cell scores "
                "against: 100 x category share / sum of the seven "
                "non-conversion shares, for entitlement years 2020 "
                "(h1), 2021 (h2) and 2022 (h3) of the 2023 edition"
            ),
            "gate_eligible": {
                key: value
                for key, value in reference_values.items()
                if key in power_cap["gate_eligible_tolerances_pp"]
            },
            "report_only": {
                key: value
                for key, value in reference_values.items()
                if key not in power_cap["gate_eligible_tolerances_pp"]
            },
        },
        "holdout_rules": {
            "protocol": {
                "fit_years": [FIT_YEARS[0], FIT_YEARS[-1]],
                "holdout_years": list(HOLDOUT_YEARS),
                "horizons": {
                    str(year): horizon
                    for year, horizon in HORIZON_OF_YEAR.items()
                },
                "rules": {
                    "nearest_year": (
                        "predict each held-out year with the last "
                        "in-sample year (2019); the module's documented "
                        "default fallback"
                    ),
                    "linear_trend": (
                        "per (sex, category) OLS on the fit years, "
                        "extrapolated to each held-out year"
                    ),
                },
                "arithmetic_note": (
                    "predictions are rounded to 4 decimals before the "
                    "deviation is taken, matching "
                    "scripts/build_claiming_reference.py exactly so the "
                    "published-construct numbers are comparable"
                ),
            },
            "published": {
                rule: {
                    key: value
                    for key, value in block.items()
                    if key != "per_cell"
                }
                for rule, block in holdout["published"].items()
            },
            "conditional": {
                rule: {
                    key: value
                    for key, value in block.items()
                    if key != "per_cell"
                }
                for rule, block in holdout["conditional"].items()
            },
            "per_cell": {
                construct: {
                    rule: block["per_cell"] for rule, block in blocks.items()
                }
                for construct, blocks in holdout.items()
            },
        },
        "reproduces_claiming_reference_v1": cross_check,
        "candidate_rules_on_the_draft_surface": candidates,
        "deployed_v1_finding": {
            "reported_not_gated": True,
            "statement": (
                "Under the DRAFT gate_b2_claiming tolerances the "
                "CURRENTLY DEPLOYED v1 nearest-year claiming rule fails "
                f"{deployed['n_failed']} of "
                f"{deployed['n_gate_eligible_cells']} gate-eligible "
                "cells. This is a measurement against a DRAFT surface, "
                "not a gate verdict: gates.yaml carries no "
                "gate_b2_claiming, no candidate has been registered, "
                "and no run has been scored."
            ),
            "n_gate_eligible_cells": deployed["n_gate_eligible_cells"],
            "n_failed": deployed["n_failed"],
            "failing_cells": deployed["failing_cells"],
            "max_abs_deviation_pp": deployed["max_abs_deviation_pp"],
            "mean_abs_deviation_pp": deployed["mean_abs_deviation_pp"],
            "per_failing_cell": {
                key: {
                    "tolerance_pp": power_cap["gate_eligible_tolerances_pp"][
                        key
                    ],
                    "reference_pp": reference_values[key],
                    "tolerance_is_sd_knob_sensitive": key
                    in power_cap["sd_knob_rounding_check"][
                        "cells_with_a_different_tolerance"
                    ],
                }
                for key in deployed["failing_cells"]
            },
            "sd_knob_sensitive_failing_cells": sorted(
                key
                for key in deployed["failing_cells"]
                if key
                in power_cap["sd_knob_rounding_check"][
                    "cells_with_a_different_tolerance"
                ]
            ),
        },
        "deviation_arithmetic": deviation_arithmetic,
        "packet_reconciliation": {
            "packet": PACKET,
            "purpose": (
                "Where this build's measurement differs from the number "
                "the DRAFT packet states, the difference is recorded "
                "here rather than silently adopted."
            ),
            "differences": [
                {
                    "field": (
                        "floor.strata.conditional_settled_years."
                        "nonzero_cells"
                    ),
                    "packet_states": 1,
                    "measured": strata["conditional_settled_years"][
                        "nonzero_cells"
                    ],
                    "note": (
                        "The packet carries the PUBLISHED stratum's "
                        "nonzero count (1) on the CONDITIONAL row. One "
                        "published cell moving renormalises its whole "
                        "(sex, year) row, so all seven conditional "
                        "categories of that row move. The packet's "
                        "mean, sd and max for the same stratum "
                        "reproduce exactly, so only the count is "
                        "affected and no proposed tolerance changes."
                    ),
                }
            ],
        },
        "does_not_establish": [
            "any threshold: no tolerance here is ratified and gates.yaml "
            "carries no gate_b2_claiming",
            "that the DRAFT tolerances are insensitive to the sd knob's "
            "4-decimal rounding: see power_cap.sd_knob_rounding_check, "
            "which names every cell whose 2-decimal tolerance moves "
            "when the full-precision sd is used",
            "the revision settle path: the 2021 and 2022 Supplement "
            "editions are not staged, so the terminal-year stratum is "
            "measured on ONE edition pair and one year (14 conditional "
            "cells)",
            "that the scanned rule class is complete: the candidate "
            "rules above are a scan, not a proof that no admissible "
            "rule does better",
            "any cause for the 2020 level shift in the reference: not "
            "established by any source read here",
        ],
        "build": {
            "built_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "built_by": "scripts/build_claiming_publication_floor.py",
        },
    }


def main() -> None:
    artifact = build()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(artifact, indent=2) + "\n")
    cap = artifact["power_cap"]
    deployed = artifact["deployed_v1_finding"]
    terminal = artifact["strata"]["conditional_terminal_year"]
    print(
        f"wrote {OUT_PATH}\n"
        f"  conditional terminal-year revision: mean "
        f"{terminal['mean_pp']} pp, sd {terminal['sd_pp']} pp, max "
        f"{terminal['max_pp']} pp over {terminal['n_cells']} cells\n"
        f"  power cap: {cap['n_gate_eligible']} gate-eligible, "
        f"{cap['n_report_only_tolerance_above_t_max']} report-only\n"
        f"  claiming_reference_v1 reproduced: "
        f"{artifact['reproduces_claiming_reference_v1']['all_match']}\n"
        f"  deployed v1 nearest-year: {deployed['n_failed']} of "
        f"{deployed['n_gate_eligible_cells']} gate-eligible cells fail "
        "(REPORTED, NOT GATED)"
    )


if __name__ == "__main__":
    main()
