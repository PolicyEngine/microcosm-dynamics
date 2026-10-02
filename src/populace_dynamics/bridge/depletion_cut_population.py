"""Registered, frame-relative SSI replacement arithmetic on explicit arrays.

This module never imports PolicyEngine-US or reads HDF. Invented HDF writing
is delegated to the explicitly selected interpreter through the child module.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from collections.abc import Hashable, Mapping
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

SPECIFICATION_PATH = (
    Path(__file__).resolve().parents[3]
    / "docs/design/pe_us_depletion_cut_population.md"
)
SPECIFICATION_NAME = "pe_us_depletion_cut_population_ssi_asset_test"

SPECIFICATION_VERSION = "sa1-draft-3"

SPECIFICATION_STATUS = "draft"

SPECIFICATION_SHA256 = None

MAX_RULINGS = {
    "authorization": {
        "decision": "d806",
        "ruled_at": "2026-10-01T18:14",
        "ruling": "Max in chat 2026-10-01 (Claude session "
        "45a0ea0e): 'Register the analysis first, "
        "the way this repo registers tests: "
        "cells, population, the 22% OASI cut, and "
        "the 17% OASDI sensitivity.' 'Run the cut "
        "on a population that carries assets, "
        "through PolicyEngine-US.' 'Label results "
        "as frame-relative unless calibrated to "
        "national totals.' 'Open a PR, get an "
        "independent review, and keep published "
        "numbers behind Max's go (cos "
        "add-decision).' 'Run compute-heavy work "
        "on Modal.' Authorizes the #42 "
        "registration and the one-shot run; "
        "publication of numbers needs a separate "
        "go.",
    }
}

FRAME_PIN = {
    "repo_id": "policyengine/populace-us",
    "repo_type": "dataset",
    "filename": "populace_us_2024.h5",
    "tag": "populace-us-2024-spm-20260909",
    "revision": "9a814a3b3b53c0ecd6e1737b6ec862c31300ef6f",
    "bytes": 826917837,
    "sha256": "6496cc4393d4d3c6574f76eca231de5898c803b9067645591fd5c4d3e65aee84",
    "period": "2024",
}

PR506_HEAD = "363d9e81a8fa787c690085308d4f2e0602aed07a"

PE_US_PIN = {
    "version": "2.18.0",
    "package_record_digest": "9f9f090894638e3d0e0dd5ad8ab34f36cf8cb2134ef3627407d0653381906007",
    "package_record_lines": 17551,
}

SCENARIOS = {
    "oasi22": {
        "role": "primary",
        "payable_share_source": "trustees_citation OASI",
        "components": [
            "social_security_retirement",
            "social_security_survivors",
            "social_security_dependents",
        ],
    },
    "oasdi17": {
        "role": "sensitivity",
        "payable_share_source": "trustees_citation OASDI",
        "components": [
            "social_security_retirement",
            "social_security_survivors",
            "social_security_dependents",
            "social_security_disability",
        ],
    },
}

VARIANTS = ["asset_test_as_encoded", "no_asset_test"]

ROWS = {
    "R0": {
        "field": None,
        "value": "encoded resource test; frame asset placement; "
        "ssi_if_takes_up; all beneficiaries",
    },
    "R2": {"field": "ssi_measure", "value": "ssi"},
    "R3": {"field": "resource_test", "value": "spousal_deeming_couple_limit"},
    "R4": {
        "field": "resource_test",
        "value": "household_pooling_couple_limit",
    },
    "R5": {"field": "universe", "value": "exclude_four_component_records"},
}

CELLS = {
    "all": ["all"],
    "age": [
        "under_18",
        "18_61",
        "62_64",
        "65_69",
        "70_74",
        "75_79",
        "80_84",
        "85_plus",
    ],
    "sex": ["female", "male"],
    "marital": [
        "married",
        "widowed",
        "divorced",
        "separated",
        "never_married",
    ],
    "race": ["hispanic", "white", "black", "asian", "other"],
    "income_quintile": ["q1", "q2", "q3", "q4", "q5"],
    "income_quintile_pe_decile": ["negative", "q1", "q2", "q3", "q4", "q5"],
}

HEADLINE = {
    "row": "R0",
    "scenario": "oasi22",
    "cell": "all",
    "statistics": [
        "F_test",
        "P_test",
        "N_test",
        "F_no",
        "P_no",
        "N_no",
        "R_test",
        "R_no",
        "B",
        "B_part",
        "B_cond",
    ],
}

TOLERANCE_DOLLARS = 1.0

CUT_CHECK_TOLERANCE = 0.05

IDENTITY_TOLERANCE = 0.01

BOUNDARY_TOLERANCE = 0.01

BOOTSTRAP = {
    "method": "household_bootstrap",
    "replicates": 500,
    "seed": 20261001,
    "interval": [0.025, 0.975],
    "quantile_method": "linear",
}

SMALL_CELL_N = 50

LABELS = [
    "FRAME-RELATIVE: Microcosm populace-us-2024 frame; liquid assets are "
    "imputed and not calibrated, and beneficiary counts are not "
    "calibrated to national totals.",
    "Applied to 2026 law and prices: the cut would not happen in 2026, "
    "and this is not a projection.",
    "Static: no behavioral response.",
    "Registered one-shot, not blind: registered after PR #506's "
    "illustrative results and after real-data diagnostics on this frame "
    "were seen (issue #42, Registration 19).",
    "Headline basis: potential federal SSI replacement, as if everyone "
    "eligible takes SSI up, under the row's modeled resource test; shares "
    "count cut beneficiaries by replacement of their marital unit's "
    "combined cut.",
]

NAMED_DIFFERENCES = [
    "1. **Frame-relative.** Liquid assets are imputed (one draw per "
    "household, SCF 2022 or SIPP 2023 donors by Microcosm's code; the "
    "blend is not confirmed for this frame) and not calibrated; "
    "beneficiary counts and concurrent SS-SSI receipt are not calibrated.",
    "2. **Asset placement.** Each household's assets sit on its "
    "lowest-`A_LINENO` person; other members hold none. Rows R3 and R4 "
    "are two alternative resource tests addressing this.",
    "3. **No resource deeming in PE-US 2.18.0** (§4.1). Row R3 applies "
    "the spousal rule; the parent-to-child rule is not applied in any "
    "row.",
    "4. **The fund of a dependent's benefit is unknown.** PE-US's single "
    "dependents component cannot separate dependents of disabled workers "
    "(DI) from dependents of retired workers (OASI), so the OASI cut "
    "reduces both.",
    "5. **Synthetic splits.** 16.9 percent of beneficiaries (weighted) "
    "carry a synthetic fixed-proportion split across all four components "
    "(76.4 percent of it in OASI components); row R5 excludes them.",
    "6. **Marital and living-arrangement composition.** The frame's "
    "beneficiaries aged 62 and over are 85.6 percent married. Urban "
    "Institute tabulations of SSA's MINT model (MINTEX), published in "
    "2005/2006, project 60 percent of Social Security beneficiaries aged "
    "62 or older in 2022 to be married (Butrica, Cashin and Uccello, "
    "Social Security Bulletin 66(4), Table 1, row Married, column All, "
    "2022). Widowed, divorced and never-married beneficiaries, and people "
    "living alone, are underrepresented in the frame. The all-beneficiary "
    "shares reflect this skew, and one-way breakdowns do not remove it: "
    "composition can also differ within age, sex, race and income cells.",
    "7. **Model versions.** The weights were solved under PE-US 1.764.6; "
    "the data release declares compatibility with policyengine-us 2.0.0 "
    "(core 3.32.5); policyengine.py certifies it for 2.2.1; the run uses "
    "2.18.0 (core 3.32.11).",
    "8. **Year.** 2026 law, a 2024 frame extended by PE-US; asset inputs "
    "grow with CPI-U while the limits stay at $2,000 and $3,000.",
    "9. **Take-up.** The headline assumes everyone eligible takes SSI up; "
    "row R2 uses the frame's take-up flags.",
    "10. **Static.** No change in work, claiming, saving, asset "
    "spend-down or living arrangements.",
    "11. **Age.** Top-coded at 80-84 and 85+. CPS does not collect a "
    "child's own Social Security income below age 15; beneficiaries under "
    "15 appear only as 25 synthetic PUF-support records, so the frame "
    "omits or misattributes child beneficiaries.",
    "12. **The spousal-deeming cap.** When an ineligible spouse's income "
    "is deemed, 20 CFR 416.1163(e)(2) limits the benefit to the lesser of "
    "the deeming computation and the individual FBR less the person's own "
    "countable income. PE-US 2.18.0 caps it at the individual FBR only "
    "(`PEUS/variables/gov/ssa/ssi/ssi_if_takes_up.py:25-38`). A cut that "
    "ends deeming can therefore lower modeled SSI. Labels describe "
    "PE-US's modeled response, including this discrepancy.",
]
SYNTHETIC_SPLIT = {
    "count": 5924,
    "proportions": {
        "social_security_retirement": 0.2496,
        "social_security_survivors": 0.3793,
        "social_security_dependents": 0.1355,
        "social_security_disability": 0.2356,
    },
}

FRAME_SHA256 = FRAME_PIN["sha256"]
COMPONENTS = tuple(SCENARIOS["oasdi17"]["components"])
FULL, PART, NONE = 0, 1, 2
REPLACEMENT_NAMES = ("full", "part", "none")


def monthly_whole_dollars(annual: NDArray[Any]) -> NDArray[np.int64]:
    """Find the exact float64 integer floor satisfying 12m <= a < 12(m+1).

    The correction loops avoid trusting rounded division at a boundary. The
    registered inputs are float32 values promoted to float64; excessively
    large amounts are refused because consecutive monthly integers would
    not be distinguishable in float64.
    """
    values = np.asarray(annual, dtype=np.float64)
    if (
        not np.isfinite(values).all()
        or (values < 0).any()
        or (values >= 12 * 2**50).any()
    ):
        raise ValueError(
            "annual benefits must be finite, nonnegative and bounded"
        )
    monthly = np.floor(values / 12).astype(np.int64)
    too_high = 12.0 * monthly > values
    while too_high.any():
        monthly[too_high] -= 1
        too_high = 12.0 * monthly > values
    too_low = 12.0 * (monthly + 1) <= values
    while too_low.any():
        monthly[too_low] += 1
        too_low = 12.0 * (monthly + 1) <= values
    return monthly


def payable_monthly_array(
    monthly: NDArray[np.int64], share: Decimal
) -> NDArray[np.int64]:
    """Multiply whole monthly dollars by a Decimal share and floor exactly.

    Fraction supplies exact integer numerator and denominator. NumPy's
    int64 path handles ordinary amounts; an object-integer path handles
    long Decimal shares or amounts whose product would overflow int64.
    """
    amounts = np.asarray(monthly)
    if amounts.dtype.kind not in "iu" or (amounts < 0).any():
        raise ValueError("monthly benefits must be nonnegative integers")
    if (amounts > np.iinfo(np.int64).max).any():
        raise ValueError("monthly benefits exceed int64")
    if not isinstance(share, Decimal):
        raise TypeError("share must be a Decimal")
    if not share.is_finite() or not Decimal(0) <= share <= Decimal(1):
        raise ValueError("share must lie in [0, 1]")
    fraction = Fraction(share)
    numerator, denominator = fraction.numerator, fraction.denominator
    limit = np.iinfo(np.int64).max
    largest = int(amounts.max(initial=0))
    if denominator <= limit and (
        numerator == 0 or largest <= limit // numerator
    ):
        return (amounts.astype(np.int64) * numerator // denominator).astype(
            np.int64
        )
    exact = amounts.astype(object) * numerator // denominator
    return np.asarray(exact, dtype=np.int64)


def cut_components(
    components: Mapping[str, NDArray[Any]], scenario: str, share: Decimal
) -> tuple[
    dict[str, NDArray[np.float64]],
    dict[str, NDArray[np.int64]],
    NDArray[np.int64],
]:
    """Apply the registered per-component cut, preserving annual remainders."""
    if scenario != "baseline" and scenario not in SCENARIOS:
        raise ValueError(f"unknown scenario {scenario!r}")
    selected = (
        set()
        if scenario == "baseline"
        else set(SCENARIOS[scenario]["components"])
    )
    arrays = {
        name: np.asarray(components[name], dtype=np.float64)
        for name in COMPONENTS
    }
    if len({value.shape for value in arrays.values()}) != 1:
        raise ValueError("components need identical shapes")
    cuts = {}
    reform = {}
    for name, values in arrays.items():
        monthly = monthly_whole_dollars(values)
        cuts[name] = (
            12 * (monthly - payable_monthly_array(monthly, share))
            if name in selected
            else np.zeros(values.shape, dtype=np.int64)
        )
        reform[name] = values - cuts[name]
    person_cut = sum(
        cuts.values(),
        np.zeros(next(iter(arrays.values())).shape, dtype=np.int64),
    )
    return reform, cuts, person_cut


def unit_totals(
    values: NDArray[Any], unit_index: NDArray[Any]
) -> NDArray[np.float64]:
    """Sum person values once into each nonnegative integer unit index."""
    index = np.asarray(unit_index, dtype=np.int64)
    amounts = np.asarray(values, dtype=np.float64)
    if index.shape != amounts.shape or index.ndim != 1 or (index < 0).any():
        raise ValueError("one nonnegative unit index per person is required")
    return np.bincount(index, weights=amounts)


def replacement_labels(
    person_cut: NDArray[Any],
    baseline_ssi: NDArray[Any],
    scenario_ssi: NDArray[Any],
    unit_index: NDArray[Any],
    tolerance: float = TOLERANCE_DOLLARS,
) -> NDArray[np.int8]:
    """Return full=0, part=1 or none=2 from each marital unit's SSI change.

    All persons enter the unit sums; only reporting masks restrict the
    beneficiary universe, including R5's excluded synthetic records.
    Units without any cut receive none because they are outside the universe.
    """
    index = np.asarray(unit_index, dtype=np.int64)
    person_cut = np.asarray(person_cut, dtype=np.float64)
    baseline = np.asarray(baseline_ssi, dtype=np.float64)
    scenario = np.asarray(scenario_ssi, dtype=np.float64)
    if (
        not np.isfinite(tolerance)
        or tolerance < 0
        or not all(
            np.isfinite(values).all()
            for values in (person_cut, baseline, scenario)
        )
        or (person_cut < 0).any()
    ):
        raise ValueError(
            "replacement inputs must be finite with nonnegative cuts and tolerance"
        )
    with np.errstate(over="ignore", invalid="ignore"):
        cut = unit_totals(person_cut, index)
        change = unit_totals(scenario - baseline, index)
    if not np.isfinite(cut).all() or not np.isfinite(change).all():
        raise ValueError("replacement unit totals must be finite")
    labels = np.full(len(cut), NONE, dtype=np.int8)
    labels[(cut > 0) & (change > tolerance)] = PART
    labels[(cut > 0) & (change >= cut - tolerance)] = FULL
    return labels[index]


def resource_test_encoded(
    resources: NDArray[Any],
    unit_index: NDArray[Any],
    joint: NDArray[Any],
    individual_limit: float,
    couple_limit: float,
) -> NDArray[np.bool_]:
    """Apply the encoded own-or-joint-unit resource test with equality passing."""
    own = np.asarray(resources, dtype=np.float64)
    joint_claim = np.asarray(joint, dtype=bool)
    pooled = unit_totals(own, unit_index)[
        np.asarray(unit_index, dtype=np.int64)
    ]
    return np.where(joint_claim, pooled, own) <= np.where(
        joint_claim, couple_limit, individual_limit
    )


def _person_unit_sizes(
    unit_index: NDArray[Any], unit_sizes: NDArray[Any]
) -> NDArray[np.int64]:
    """Project per-marital-unit sizes to persons."""
    return np.asarray(unit_sizes, dtype=np.int64)[
        np.asarray(unit_index, dtype=np.int64)
    ]


def resource_test_spousal(
    resources: NDArray[Any],
    unit_index: NDArray[Any],
    unit_sizes: NDArray[Any],
    individual_limit: float,
    couple_limit: float,
) -> NDArray[np.bool_]:
    """Test two-person units on their sum and couple limit, otherwise own resources."""
    own = np.asarray(resources, dtype=np.float64)
    pair = _person_unit_sizes(unit_index, unit_sizes) == 2
    pooled = unit_totals(own, unit_index)[
        np.asarray(unit_index, dtype=np.int64)
    ]
    return np.where(pair, pooled, own) <= np.where(
        pair, couple_limit, individual_limit
    )


def resource_test_household(
    resources: NDArray[Any],
    unit_index: NDArray[Any],
    household_index: NDArray[Any],
    unit_sizes: NDArray[Any],
    individual_limit: float,
    couple_limit: float,
) -> NDArray[np.bool_]:
    """Apply the spousal limits against the person's household resource sum."""
    pair = _person_unit_sizes(unit_index, unit_sizes) == 2
    pooled = unit_totals(resources, household_index)[
        np.asarray(household_index, dtype=np.int64)
    ]
    return pooled <= np.where(pair, couple_limit, individual_limit)


def resource_boundary_mask(
    resources: NDArray[Any],
    unit_index: NDArray[Any],
    joint: NDArray[Any],
    individual_limit: float,
    couple_limit: float,
    tolerance: float = BOUNDARY_TOLERANCE,
) -> NDArray[np.bool_]:
    """Flag people whose encoded tested resources lie within tolerance of the limit."""
    own = np.asarray(resources, dtype=np.float64)
    joint_claim = np.asarray(joint, dtype=bool)
    pooled = unit_totals(own, unit_index)[
        np.asarray(unit_index, dtype=np.int64)
    ]
    value = np.where(joint_claim, pooled, own)
    limit = np.where(joint_claim, couple_limit, individual_limit)
    return np.abs(value - limit) <= tolerance


def age_band(age: NDArray[Any]) -> NDArray[np.str_]:
    """Assign each age to one of the eight registered bands."""
    values = np.asarray(age)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("ages must be finite and nonnegative")
    return np.asarray(CELLS["age"])[
        np.searchsorted([18, 62, 65, 70, 75, 80, 85], values, side="right")
    ]


def sex_cell(is_female: NDArray[Any]) -> NDArray[np.str_]:
    """Assign the registered sex cell from the frame's boolean flag."""
    return np.where(np.asarray(is_female, dtype=bool), "female", "male")


def marital_cell(marital_code: NDArray[Any]) -> NDArray[np.str_]:
    """Map the CPS marital code using deployment_frame.MARITAL_MAP."""
    from populace_dynamics.data.deployment_frame import MARITAL_MAP

    codes = np.asarray(marital_code)
    if not np.isin(codes, list(MARITAL_MAP)).all():
        raise ValueError("unknown CPS marital code")
    lookup = np.asarray(["", *(MARITAL_MAP[i] for i in range(1, 8))])
    return lookup[codes.astype(np.int64)]


def race_cell(
    cps_race: NDArray[Any], is_hispanic: NDArray[Any]
) -> NDArray[np.str_]:
    """Assign Hispanic first, then White, Black, Asian or other CPS race."""
    race = np.asarray(cps_race)
    return np.select(
        [np.asarray(is_hispanic, dtype=bool), race == 1, race == 2, race == 4],
        ["hispanic", "white", "black", "asian"],
        default="other",
    )


def income_per_person(
    market_income: NDArray[Any],
    benefits: NDArray[Any],
    health_benefits: NDArray[Any],
    count_people: NDArray[Any],
) -> NDArray[np.float64]:
    """Compute registered pre-tax household income per person excluding health."""
    count = np.asarray(count_people, dtype=np.float64)
    if not np.isfinite(count).all() or (count <= 0).any():
        raise ValueError("household counts must be finite and positive")
    return (
        np.asarray(market_income, dtype=np.float64)
        + np.asarray(benefits, dtype=np.float64)
        - np.asarray(health_benefits, dtype=np.float64)
    ) / count


def quintile_cutpoints(
    income: NDArray[Any],
    weights: NDArray[Any],
    beneficiary_mask: NDArray[Any],
) -> NDArray[np.float64]:
    """Return the smallest observed incomes attaining each weighted fifth.

    Ties receive the same quintile; unequal weights and ties can prevent
    quintiles from containing exactly twenty percent of beneficiary weight.
    """
    values = np.asarray(income, dtype=np.float64)
    w = np.asarray(weights, dtype=np.float64)
    mask = np.asarray(beneficiary_mask, dtype=bool)
    if not (values.shape == w.shape == mask.shape) or values.ndim != 1:
        raise ValueError("income, weights and mask need matching vectors")
    if (
        not np.isfinite(values).all()
        or not np.isfinite(w).all()
        or (w < 0).any()
    ):
        raise ValueError("incomes and nonnegative weights must be finite")
    chosen = mask & (w > 0)
    order = np.argsort(values[chosen], kind="stable")
    incomes, sorted_weights = values[chosen][order], w[chosen][order]
    if not len(incomes):
        raise ValueError("beneficiary weights have no positive total")
    cumulative = np.cumsum(sorted_weights)
    targets = cumulative[-1] * np.arange(1, 5) / 5
    return incomes[np.searchsorted(cumulative, targets, side="left")]


def assign_quintile(
    income: NDArray[Any], cutpoints: NDArray[Any]
) -> NDArray[np.str_]:
    """Assign q1 through q5, putting income equal to a cutpoint below it."""
    cut = np.asarray(cutpoints, dtype=np.float64)
    if cut.shape != (4,) or (np.diff(cut) < 0).any():
        raise ValueError("four ordered quintile cutpoints are required")
    return np.asarray(CELLS["income_quintile"])[
        np.searchsorted(cut, np.asarray(income), side="left")
    ]


def pe_decile_quintile(decile: NDArray[Any]) -> NDArray[np.str_]:
    """Collapse PE deciles by ceil(decile/2), with -1 mapped to negative."""
    values = np.asarray(decile)
    if not np.isin(values, [-1, *range(1, 11)]).all():
        raise ValueError("PE deciles must be -1 or integers 1 through 10")
    index = np.where(values == -1, 0, (values.astype(np.int64) + 1) // 2)
    return np.asarray(CELLS["income_quintile_pe_decile"])[index]


def reason_partition(
    abd: NDArray[Any],
    immigration_pass: NDArray[Any],
    unit_index: NDArray[Any],
    labels_no: NDArray[Any] | None = None,
) -> NDArray[np.str_]:
    """Return the first applicable no-test nonreplacement reason per marital unit.

    This eligibility-basis partition must not be applied to take-up row R2.
    When labels are supplied, replaced persons receive the empty string.
    """
    categorical = np.asarray(abd, dtype=bool)
    immigration = np.asarray(immigration_pass, dtype=bool)
    index = np.asarray(unit_index, dtype=np.int64)
    any_abd = unit_totals(categorical, index) > 0
    any_qualified = unit_totals(categorical & immigration, index) > 0
    reasons = np.where(
        ~any_abd,
        "not_abd",
        np.where(
            ~any_qualified, "immigration", "no_positive_modeled_ssi_response"
        ),
    )[index]
    if labels_no is not None:
        reasons = np.where(np.asarray(labels_no) == NONE, reasons, "")
    return reasons


def statistics(
    labels_test: NDArray[Any],
    labels_no: NDArray[Any],
    weights: NDArray[Any],
    beneficiary_mask: NDArray[Any],
    cell_mask: NDArray[Any] | None = None,
) -> dict[str, Any]:
    """Compute all registered point statistics and the no-to-test transition table."""
    test, no = np.asarray(labels_test), np.asarray(labels_no)
    w = np.asarray(weights, dtype=np.float64)
    mask = np.asarray(beneficiary_mask, dtype=bool).copy()
    if cell_mask is not None:
        mask &= np.asarray(cell_mask, dtype=bool)
    if not (test.shape == no.shape == w.shape == mask.shape):
        raise ValueError("one label and weight per person is required")
    if (
        not np.isin(test, [FULL, PART, NONE]).all()
        or not np.isin(no, [FULL, PART, NONE]).all()
    ):
        raise ValueError("unknown replacement label")
    if not np.isfinite(w).all() or (w < 0).any():
        raise ValueError("weights must be finite and nonnegative")
    chosen = np.flatnonzero(mask)
    code = 3 * no[chosen] + test[chosen]
    unweighted = np.bincount(code, minlength=9).reshape(3, 3)
    weighted = np.bincount(code, weights=w[chosen], minlength=9).reshape(3, 3)
    out = _statistics_from_table(weighted)
    n_cond = int((mask & (no != NONE)).sum())
    out.update(
        n=int(mask.sum()),
        W=float(weighted.sum()),
        n_cond=n_cond,
        W_cond=float(weighted[:2].sum()),
        small_cell=int(mask.sum()) < SMALL_CELL_N,
        small_cell_cond=n_cond < SMALL_CELL_N,
        transition_table={
            "labels": list(REPLACEMENT_NAMES),
            "orientation": "no_asset_test rows; row resource test columns",
            "unweighted": unweighted.tolist(),
            "weighted": weighted.tolist(),
        },
    )
    return out


def _statistics_from_table(table: NDArray[np.float64]) -> dict[str, Any]:
    """Convert a weighted no-by-test transition table to registered shares."""
    total = float(table.sum())
    conditional = float(table[:2].sum())
    out: dict[str, Any] = {"undefined_reasons": {}}
    names = ("F", "P", "N")
    for label, marginals in (
        ("test", table.sum(axis=0)),
        ("no", table.sum(axis=1)),
    ):
        for name, amount in zip(names, marginals, strict=True):
            key = f"{name}_{label}"
            out[key] = float(amount / total) if total > 0 else None
    out["R_test"] = float(table[:, :2].sum() / total) if total > 0 else None
    out["R_no"] = conditional / total if total > 0 else None
    blocked = float(table[:2, NONE].sum())
    out["B"] = blocked / total if total > 0 else None
    out["B_part"] = float(table[FULL, PART] / total) if total > 0 else None
    out["B_cond"] = blocked / conditional if conditional > 0 else None
    for key, value in tuple(out.items()):
        if value is None:
            out["undefined_reasons"][key] = (
                "R_no is zero"
                if key == "B_cond" and total > 0
                else "no positive denominator weight"
            )
    return out


def bootstrap_intervals(
    jobs: Mapping[Hashable, Mapping[str, Any]],
    household_ids: NDArray[Any],
    *,
    replicates: int = BOOTSTRAP["replicates"],
    seed: int = BOOTSTRAP["seed"],
) -> dict[Hashable, dict[str, Any]]:
    """Bootstrap all jobs with one sorted-household multiplicity sequence.

    Each job accepts the same fields as statistics. Integer transition
    counts are aggregated by household first and then weighted once,
    making the intervals invariant to person order within households.
    Only households contributing to a cell enter its matrix multiply.
    Empty-denominator replicates are omitted and counted independently.
    """
    ids, first, household = np.unique(
        np.asarray(household_ids), return_index=True, return_inverse=True
    )
    count = len(ids)
    rng = np.random.default_rng(seed)
    multiplicities = np.zeros(
        (replicates, count), dtype=np.min_scalar_type(count)
    )
    if count:
        for b in range(replicates):
            idx = rng.integers(0, count, size=count)
            multiplicities[b] = np.bincount(idx, minlength=count)
    out = {}
    names = HEADLINE["statistics"]
    household_weight_cache: dict[int, NDArray[np.float64]] = {}
    for key, job in jobs.items():
        test = np.asarray(job["labels_test"], dtype=np.int64)
        no = np.asarray(job["labels_no"], dtype=np.int64)
        weights = np.asarray(job["weights"], dtype=np.float64)
        mask = np.asarray(job["beneficiary_mask"], dtype=bool).copy()
        if job.get("cell_mask") is not None:
            mask &= np.asarray(job["cell_mask"], dtype=bool)
        if not (
            test.shape
            == no.shape
            == weights.shape
            == mask.shape
            == household.shape
        ):
            raise ValueError("bootstrap job vectors must match household ids")
        if (
            not np.isin(test, [FULL, PART, NONE]).all()
            or not np.isin(no, [FULL, PART, NONE]).all()
        ):
            raise ValueError("unknown replacement label")
        if not np.isfinite(weights).all() or (weights < 0).any():
            raise ValueError("weights must be finite and nonnegative")
        identity = id(job["weights"])
        if identity not in household_weight_cache:
            high = weights[first]
            if not np.array_equal(weights, high[household]):
                raise ValueError(
                    "all persons in a household must share its weight"
                )
            household_weight_cache[identity] = high
        high = household_weight_cache[identity]
        selected = np.flatnonzero(mask)
        h, compact = np.unique(household[selected], return_inverse=True)
        transition = 3 * no[selected] + test[selected]
        counts = np.bincount(
            9 * compact + transition, minlength=9 * len(h)
        ).reshape(len(h), 9)
        table = multiplicities[:, h] @ (counts * high[h, None])
        table = table.reshape(replicates, 3, 3)
        denominators = table.sum(axis=(1, 2))
        conditional = table[:, :2, :].sum(axis=(1, 2))
        numerators = {
            **{
                f"{name}_test": table[:, :, label].sum(axis=1)
                for label, name in enumerate(("F", "P", "N"))
            },
            **{
                f"{name}_no": table[:, label, :].sum(axis=1)
                for label, name in enumerate(("F", "P", "N"))
            },
            "R_test": table[:, :, :2].sum(axis=(1, 2)),
            "R_no": conditional,
            "B": table[:, :2, NONE].sum(axis=1),
            "B_part": table[:, FULL, PART],
            "B_cond": table[:, :2, NONE].sum(axis=1),
        }
        intervals = {}
        for name in names:
            denominator = conditional if name == "B_cond" else denominators
            valid = denominator > 0
            values = numerators[name][valid] / denominator[valid]
            interval = (
                np.quantile(
                    values, BOOTSTRAP["interval"], method="linear"
                ).tolist()
                if len(values)
                else None
            )
            intervals[name] = {
                "interval": interval,
                "valid_replicates": int(valid.sum()),
                "omitted_replicates": int((~valid).sum()),
                "undefined_reason": (
                    None
                    if len(values)
                    else (
                        "no replicate has positive conditional weight"
                        if name == "B_cond"
                        else "no replicate has positive cell weight"
                    )
                ),
            }
        out[key] = intervals
    return out


def diagnostics(
    person_cut: NDArray[Any],
    baseline: Mapping[str, NDArray[Any]],
    scenario: Mapping[str, NDArray[Any]],
    unit_index: NDArray[Any],
    household_index: NDArray[Any],
    household_weights: NDArray[Any],
) -> dict[str, Any]:
    """Aggregate simulated diagnostics over distinct beneficiary households and units."""
    cut = np.asarray(person_cut, dtype=np.float64)
    u = np.asarray(unit_index, dtype=np.int64)
    h = np.asarray(household_index, dtype=np.int64)
    weights = np.asarray(household_weights, dtype=np.float64)
    beneficiary = cut > 0
    households = np.unique(h[beneficiary])
    units = np.unique(u[beneficiary])
    unit_household = np.zeros(int(u.max(initial=-1)) + 1, dtype=np.int64)
    unit_household[u] = h
    unit_cut = unit_totals(cut, u)
    weighted_cut = float(
        np.dot(unit_totals(cut, h)[households], weights[households])
    )
    totals: dict[str, Any] = {"cut": weighted_cut}
    out: dict[str, Any] = {
        "beneficiary_households": int(len(households)),
        "attributed_marital_units": int(len(units)),
        "weighted_totals": totals,
        "ssi_outside_attributed_units": {},
        "unit_responses": {},
    }
    for measure in ("ssi_if_takes_up", "ssi"):
        delta = np.asarray(scenario[measure], dtype=np.float64) - np.asarray(
            baseline[measure], dtype=np.float64
        )
        household_delta = unit_totals(delta, h)
        change = unit_totals(delta, u)
        total = float(np.dot(household_delta[households], weights[households]))
        attributed = float(
            np.dot(change[units], weights[unit_household[units]])
        )
        totals[measure] = total
        out["ssi_outside_attributed_units"][measure] = total - attributed
        over = units[change[units] > unit_cut[units] + TOLERANCE_DOLLARS]
        falls = units[change[units] < -TOLERANCE_DOLLARS]
        out["unit_responses"][measure] = {
            "over_replacing": {
                "n": int(len(over)),
                "W": float(weights[unit_household[over]].sum()),
            },
            "ssi_falls": {
                "n": int(len(falls)),
                "W": float(weights[unit_household[falls]].sum()),
                "weighted_ssi_loss": float(
                    np.dot(-change[falls], weights[unit_household[falls]])
                ),
            },
        }
    for measure in ("household_state_benefits", "household_net_income"):
        delta = np.asarray(scenario[measure], dtype=np.float64) - np.asarray(
            baseline[measure], dtype=np.float64
        )
        totals[measure] = float(np.dot(delta[households], weights[households]))
    ss_delta = np.asarray(
        scenario["social_security"], dtype=np.float64
    ) - np.asarray(baseline["social_security"], dtype=np.float64)
    ss_change = float(
        np.dot(unit_totals(ss_delta, h)[households], weights[households])
    )
    totals["social_security_change"] = ss_change
    totals["offset_share"] = (
        1 - totals["household_net_income"] / ss_change if ss_change else None
    )
    return out


def check_frame(path: str | Path, *, registered: bool) -> str:
    """Hash explicit frame bytes, refusing real data outside a registered run.

    Main-venv access is bytes only: the child additionally refuses any
    non-real file lacking its invented HDF marker before simulation.
    Registered calls must use the pinned real frame, never arbitrary files.
    """
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    value = digest.hexdigest()
    if value == FRAME_SHA256 and not registered:
        raise ValueError("real frame is forbidden outside a registered run")
    if registered and value != FRAME_SHA256:
        raise ValueError("registered frame does not match its pinned SHA-256")
    return value


def write_invented_frame(
    path: str | Path,
    households: int,
    persons: int,
    seed: int,
    *,
    python: str | Path | None = None,
) -> dict[str, Any]:
    """Write invented HDF tables in the PE-US child, keeping HDF out of main."""
    from populace_dynamics.bridge import policyengine_us as bridge

    interpreter = bridge._interpreter(python)
    child = Path(__file__).with_name("depletion_cut_population_child.py")
    job = {
        "mode": "write-invented",
        "frame_path": str(Path(path).resolve()),
        "households": households,
        "persons": persons,
        "seed": seed,
        "labels": ["INVENTED DRY RUN - NOT RESULTS", *LABELS],
        "named_differences": NAMED_DIFFERENCES,
    }
    completed = subprocess.run(
        [str(interpreter), str(child)],
        input=json.dumps(job),
        capture_output=True,
        text=True,
        check=True,
        timeout=300,
        env={
            **os.environ,
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
        },
    )
    return json.loads(completed.stdout)
