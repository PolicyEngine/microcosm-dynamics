#!/usr/bin/env python3
"""S0.1 power on INVENTED data for gates SM3 and ED2.

Authority: design #558 at ``2c19f5b6`` (sections 5.2, 5.3 and 8, the
``WEAK_POWER_OR_VACUITY`` condition and the SM kill criterion); the frozen
record is ``docs/design/s0_1_source_audit.md``.

**Every population here is invented.** No survey record, PSID file or HRS
file is read. PSID use follows the project's data-access record.
The only repository input is OACT's TR 2026 single-age death
probability (``populace_dynamics.data.tr2026.death_probability``), which
the brief permits; it reports descriptive mean q by sex and age band
and is skipped with ``--no-anchors``.

The registered tests (record sections SM3 and ED2):

* **SM3.** In each sex x age-band cell (50-64, 65-84), each classified
  group's weighted observed-to-expected death ratio divided by the
  cohort's overall ratio (``R_g = (O_g/E_g) / (O/E)``, unclassified
  persons in ``O`` and ``E`` only). A cell passes when its simultaneous
  95 percent bound for ``log R_g`` (Bonferroni over the registered
  family) lies inside ``[-log 1.15, log 1.15]``; it fails when the bound
  lies wholly outside; otherwise it is inconclusive. A dimension passes
  only if every cell passes.
* **ED2.** For each attainment category, sex and age group (25-34), the
  projected share minus the target survey's share, with the same
  three-way rule and a tolerance of 0.02.

The power procedure is the probability that the pass conjunction holds
when the model is right (the operating characteristic at the 0.90
criterion), screened by a conservative normal union bound on effective deaths or
persons. Full-family Monte Carlo preserves the invented shared-denominator
or multinomial covariance. Separate cluster-linearized and Rao-Wu
stratified family bootstrap diagnostics exercise the SM3 estimators;
ED2 uses finite-sample Hoeffding bounds over independent invented
households, with Bonferroni coverage over every category. These retain
within-household dependence and do not use sparse plug-in variances;
their low replication counts cannot establish the 0.90 power criterion.

Run from the repository root::

    .venv/bin/python scripts/s0_1_power.py --out docs/design/s0_1_power_results.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
from scipy.special import gammainc, gammaincc, ndtr, ndtri

SCHEMA_VERSION = "s0_1_power.v3"
DESIGN_COMMIT = "2c19f5b6856b9da62924706067ef96f00f55012d"
PROCEDURE = "S01-Bonferroni-Equivalence-Grid-v2"

ALPHA = 0.05
POWER_CRITERION = 0.90
SM3_TOLERANCE = math.log(1.15)
ED2_TOLERANCE = 0.02
SM3_AGE_BANDS = ((50, 64), (65, 84))
SEXES = ("female", "male")

#: SM3 dimensions and their registered (proposed) category counts; record
#: section SM3, "Critical cells".
SM3_GROUPS = {
    "lifetime_earnings": 5,
    "education": 4,
    "race_hispanic_origin": 4,
}

# Public structural context only: the 2011 user guide, Table 1, reports
# 24,661 individuals in 8,907 families. These are documentation totals,
# not counts of the proposed analysis population. They contextualize the
# invented person grid and cannot establish real-data feasibility.
PUBLIC_SAMPLE_CONTEXT = {
    "url": "https://psidonline.isr.umich.edu/data/Documentation/UserGuide2011.pdf",
    "locator": "Table 1, 2011 total",
    "individuals": 24_661,
    "families": 8_907,
}
ASSUMED_PERSON_GRID = (
    100,
    250,
    500,
    1000,
    2500,
    5000,
    10000,
    25000,
    50000,
    100000,
    250000,
    500000,
)
ASSUMED_WINDOW_RISKS = (0.02, 0.05, 0.10, 0.25)
ASSUMED_DESIGN_EFFECTS = (1.0, 1.5, 2.0, 4.0)

PASS, FAIL, INCONCLUSIVE = "pass", "fail", "inconclusive"
# A computation/precision envelope, not a restriction of the input domain.
# Accepted inputs outside it count as inconclusive without attempting an
# overflowing RNG call or an unbounded allocation.
MAX_INVENTED_PERSON_DRAWS = 10_000_000
MAX_WEIGHT_CV = math.sqrt(sys.float_info.max)


# --------------------------------------------------------------------------
# Validation helpers
# --------------------------------------------------------------------------
def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _finite_positive(value: float, name: str) -> float:
    value = float(value)
    _require(math.isfinite(value) and value > 0, f"{name} must be > 0")
    return value


def _probability(value: float, name: str, *, open_interval=True) -> float:
    value = float(value)
    if open_interval:
        _require(0 < value < 1, f"{name} must lie in (0, 1)")
    else:
        _require(0 <= value <= 1, f"{name} must lie in [0, 1]")
    return value


def _family_size(m: int) -> int:
    _require(
        isinstance(m, (int, np.integer)) and not isinstance(m, bool),
        "family size must be an integer",
    )
    _require(int(m) >= 1, "family size must be at least 1")
    return int(m)


def _shares(values: Sequence[float], name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    _require(array.ndim == 1 and array.size >= 1, f"{name} must be 1-d")
    _require(np.isfinite(array).all(), f"{name} must be finite")
    _require((array > 0).all(), f"{name} must be positive")
    _require(abs(array.sum() - 1.0) < 1e-9, f"{name} must sum to one")
    return array


# --------------------------------------------------------------------------
# The registered decision rule
# --------------------------------------------------------------------------
def bonferroni_z(m: int, alpha: float = ALPHA) -> float:
    """Two-sided simultaneous critical value over a family of ``m`` cells."""
    m = _family_size(m)
    alpha = _probability(alpha, "alpha")
    return float(ndtri(1.0 - alpha / (2.0 * m)))


def classify_bounds(
    estimate: np.ndarray, half_width: np.ndarray, tolerance: float
) -> np.ndarray:
    """Pass, fail or inconclusive for each cell's bound against ``±tol``.

    A non-finite estimate or half-width (an empty cell, a zero count) is
    inconclusive: insufficient precision never passes.
    """
    tolerance = _finite_positive(tolerance, "tolerance")
    estimate = np.asarray(estimate, dtype=float)
    half_width = np.asarray(half_width, dtype=float)
    _require(estimate.shape == half_width.shape, "shape mismatch")
    _require(
        bool(np.all((half_width >= 0) | np.isnan(half_width))),
        "half-widths must be nonnegative",
    )
    lower, upper = estimate - half_width, estimate + half_width
    finite = np.isfinite(lower) & np.isfinite(upper)
    out = np.full(estimate.shape, INCONCLUSIVE, dtype=object)
    inside = finite & (lower >= -tolerance) & (upper <= tolerance)
    outside = finite & ((lower > tolerance) | (upper < -tolerance))
    out[inside] = PASS
    out[outside] = FAIL
    return out


def conjunction(outcomes: Sequence[str]) -> str:
    """A family passes only if every cell passes; any failure fails it."""
    outcomes = list(outcomes)
    _require(len(outcomes) >= 1, "a family needs at least one cell")
    _require(
        set(outcomes) <= {PASS, FAIL, INCONCLUSIVE}, "unknown cell outcome"
    )
    if all(o == PASS for o in outcomes):
        return PASS
    if any(o == FAIL for o in outcomes):
        return FAIL
    return INCONCLUSIVE


# --------------------------------------------------------------------------
# Analytic operating characteristic
# --------------------------------------------------------------------------
def cell_pass_probability(
    delta: float, se: float, tolerance: float, z: float
) -> float:
    """P(bound inside ±tol) for a normal estimate N(delta, se²)."""
    se = _finite_positive(se, "standard error")
    tolerance = _finite_positive(tolerance, "tolerance")
    z = _finite_positive(z, "critical value")
    _require(math.isfinite(float(delta)), "delta must be finite")
    upper = (tolerance - delta) / se - z
    lower = (-tolerance - delta) / se + z
    return float(max(0.0, ndtr(upper) - ndtr(lower)))


def family_power(
    deltas: Sequence[float],
    ses: Sequence[float],
    tolerance: float,
    alpha: float = ALPHA,
) -> float:
    """Power of the pass conjunction over independent normal cells.

    This is a labeled approximation, never the registered power guarantee.
    The cohort denominator and category sums induce dependence; use
    ``family_power_lower_bound`` for a guarantee under arbitrary dependence.
    """
    deltas = np.asarray(deltas, dtype=float)
    ses = np.asarray(ses, dtype=float)
    _require(
        deltas.ndim == 1 and deltas.shape == ses.shape and deltas.size >= 1,
        "deltas and standard errors must be matching 1-d arrays",
    )
    z = bonferroni_z(deltas.size, alpha)
    return float(
        np.prod(
            [
                cell_pass_probability(d, s, tolerance, z)
                for d, s in zip(deltas, ses, strict=True)
            ]
        )
    )


def family_power_lower_bound(
    deltas: Sequence[float],
    ses: Sequence[float],
    tolerance: float,
    alpha: float = ALPHA,
) -> float:
    """Normal-theory lower bound on conjunction power, any dependence.

    The union bound gives P(all pass) >= 1 - sum P(cell does not pass).
    Bonferroni controls coverage; this second union bound controls power.
    Both are conditional on the declared normal sampling model and SEs.
    """
    deltas = np.asarray(deltas, dtype=float)
    ses = np.asarray(ses, dtype=float)
    _require(
        deltas.ndim == 1 and deltas.shape == ses.shape and deltas.size >= 1,
        "matching nonempty 1-d arrays required",
    )
    z = bonferroni_z(deltas.size, alpha)
    probabilities = [
        cell_pass_probability(d, se, tolerance, z)
        for d, se in zip(deltas, ses, strict=True)
    ]
    return max(0.0, 1.0 - math.fsum(1 - p for p in probabilities))


def sm3_log_ratio_se(
    group_deaths: float, cohort_deaths: float, deff: float = 1.0
) -> float:
    """Large-sample SE of ``log R_g`` from expected deaths.

    ``Var(log R_g) = deff * (1/D_g - 1/D)`` under invented Poisson
    counts: D includes every registered sex/age-band cell and unclassified
    persons. Subtracting the covariance with that shared denominator
    yields ``-1/D``. Deff here is an assumed common variance multiplier.
    """
    d_g = _finite_positive(group_deaths, "group deaths")
    d = _finite_positive(cohort_deaths, "cohort deaths")
    deff = _finite_positive(deff, "design effect")
    _require(d_g < d, "group deaths must be below the cohort's")
    return math.sqrt(deff * (1.0 / d_g - 1.0 / d))


def share_difference_se(
    share: float, n_model_eff: float, n_target_eff: float
) -> float:
    """SE of a projected share minus an independent survey's share."""
    p = _probability(share, "share")
    n_m = _finite_positive(n_model_eff, "model effective n")
    n_t = _finite_positive(n_target_eff, "target effective n")
    return math.sqrt(p * (1 - p) * (1.0 / n_m + 1.0 / n_t))


def _critical_se(
    m: int, delta: float, tolerance: float, alpha: float, criterion: float
) -> float:
    """Largest common SE at which ``m`` equal cells reach the criterion."""
    m = _family_size(m)
    criterion = _probability(criterion, "criterion")
    tolerance = _finite_positive(tolerance, "tolerance")
    _require(abs(delta) < tolerance, "|delta| must be inside the tolerance")
    z = bonferroni_z(m, alpha)

    def power(se: float) -> float:
        return max(
            0.0,
            1.0 - m * (1.0 - cell_pass_probability(delta, se, tolerance, z)),
        )

    lo, hi = 1e-9, tolerance / z
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if power(mid) >= criterion:
            lo = mid
        else:
            hi = mid
    return lo


def min_effective_deaths_per_cell(
    m: int,
    *,
    group_share: float = 0.0,
    delta: float = 0.0,
    tolerance: float = SM3_TOLERANCE,
    alpha: float = ALPHA,
    criterion: float = POWER_CRITERION,
) -> int:
    """Smallest sufficient effective deaths per cell in the normal model.

    Every cell holds D_g effective deaths and a share ``group_share`` of
    the entire cohort's deaths, so Var(log R_g) = (1-share)/D_g.
    The returned integer is minimal for the union-bound power guarantee,
    not an exact minimum for an unknown real survey covariance. ``delta``
    bounds the absolute true error in every cell.
    """
    share = _probability(group_share, "group share", open_interval=False)
    _require(share < 1, "group share must be below one")
    se = _critical_se(m, delta, tolerance, alpha, criterion)
    return int(math.ceil((1.0 - share) / se**2))


def min_effective_n_per_cell(
    m: int,
    *,
    share: float,
    n_target_eff: float = math.inf,
    delta: float = 0.0,
    tolerance: float = ED2_TOLERANCE,
    alpha: float = ALPHA,
    criterion: float = POWER_CRITERION,
) -> int | None:
    """Smallest sufficient effective model sample; None if unreachable.

    ``n_target_eff`` is the target survey's effective sample in the cell
    (``inf`` for a target whose sampling error is negligible).
    """
    p = _probability(share, "share")
    se = _critical_se(m, delta, tolerance, alpha, criterion)
    target_var = (
        0.0
        if n_target_eff == math.inf
        else p
        * (1 - p)
        / float(_finite_positive(n_target_eff, "target effective n"))
    )
    remaining = se**2 - target_var
    if remaining <= 0:
        return None
    return int(math.ceil(p * (1 - p) / remaining))


def bootstrap_replicates_for_mc_error(
    z: float, se: float, tolerance: float, fraction: float = 0.1
) -> int:
    """Replicates B so a normal-theory bound's MC error < fraction * tol.

    The bootstrap SE's relative Monte Carlo error is about
    ``1/sqrt(2(B-1))``, so the bound ``z * se`` moves by about
    ``z * se / sqrt(2(B-1))``.
    """
    z = _finite_positive(z, "critical value")
    se = _finite_positive(se, "standard error")
    target = _finite_positive(fraction, "fraction") * _finite_positive(
        tolerance, "tolerance"
    )
    return int(math.floor(1 + 0.5 * (z * se / target) ** 2)) + 1


def projection_replicates_for_mc_error(
    replicate_sd: float, tolerance: float, fraction: float = 0.1
) -> int:
    """Projection replicates R so the mean's MC SE < fraction * tol."""
    sd = _finite_positive(replicate_sd, "replicate SD")
    target = _finite_positive(fraction, "fraction") * _finite_positive(
        tolerance, "tolerance"
    )
    return max(1, int(math.floor((sd / target) ** 2)) + 1)


# --------------------------------------------------------------------------
# Invented clustered populations and the registered estimator (SM3)
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class InventedStratum:
    """One sex x age-band stratum of an INVENTED cohort.

    Persons sit in family units (clusters) inside survey design strata.
    ``mean_risk`` is a person's expected deaths over the window under the
    model (person-years x q); ``model_log_rr`` is the model's invented
    gradient; ``true_log_misfit`` multiplies each group's true hazard
    relative to the model (zero means the model is right). Unclassified
    persons follow the model exactly and enter only the overall ratio.
    """

    n_clusters: int
    group_shares: tuple[float, ...]
    unclassified_share: float = 0.1
    mean_cluster_size: float = 2.0
    n_design_strata: int = 40
    mean_risk: float = 0.1
    weight_cv: float = 0.6
    frailty_variance: float = 0.0
    model_log_rr: tuple[float, ...] | None = None
    true_log_misfit: tuple[float, ...] | None = None

    def __post_init__(self) -> None:
        _require(
            isinstance(self.n_clusters, int)
            and not isinstance(self.n_clusters, bool)
            and self.n_clusters >= 4,
            "n_clusters must be an integer >= 4",
        )
        shares = _shares(self.group_shares, "group shares")
        _require(shares.size >= 2, "a dimension needs at least two groups")
        _probability(
            self.unclassified_share, "unclassified share", open_interval=False
        )
        _require(self.unclassified_share < 1, "unclassified share < 1")
        _require(
            math.isfinite(self.mean_cluster_size)
            and self.mean_cluster_size >= 1,
            "mean cluster size must be >= 1",
        )
        _require(
            isinstance(self.n_design_strata, int)
            and not isinstance(self.n_design_strata, bool)
            and 1 <= self.n_design_strata <= self.n_clusters // 2,
            "each design stratum needs at least two clusters",
        )
        _require(0 < self.mean_risk <= 0.5, "mean risk must lie in (0, 0.5]")
        _require(
            math.isfinite(self.weight_cv) and self.weight_cv >= 0,
            "weight CV must be >= 0",
        )
        _require(
            math.isfinite(self.frailty_variance)
            and self.frailty_variance >= 0,
            "frailty variance must be >= 0",
        )
        for name in ("model_log_rr", "true_log_misfit"):
            value = getattr(self, name)
            if value is not None:
                array = np.asarray(value, dtype=float)
                _require(
                    array.shape == shares.shape and np.isfinite(array).all(),
                    f"{name} needs one finite value per group",
                )
                _require(
                    (np.abs(array) < 100).all(),
                    f"{name} magnitude must be below 100",
                )
        _require(
            self.mean_risk * 1.5 * self.model_rr().max() <= 1,
            "model probabilities exceed one",
        )
        if self.frailty_variance == 0:
            _require(
                self.mean_risk * 1.5 * np.max(self.model_rr() * self.misfit())
                <= 1,
                "true probabilities exceed one",
            )

    @property
    def n_groups(self) -> int:
        return len(self.group_shares)

    def model_rr(self) -> np.ndarray:
        if self.model_log_rr is None:
            return np.ones(self.n_groups)
        return np.exp(np.asarray(self.model_log_rr, dtype=float))

    def misfit(self) -> np.ndarray:
        if self.true_log_misfit is None:
            return np.ones(self.n_groups)
        return np.exp(np.asarray(self.true_log_misfit, dtype=float))

    def expected_group_deaths_share(self) -> np.ndarray:
        """Each group's expected share of the stratum's model deaths."""
        shares = np.asarray(self.group_shares) * (1 - self.unclassified_share)
        rr = self.model_rr()
        classified = shares * rr
        return classified / (classified.sum() + self.unclassified_share)


def stratum_analytic_ses(stratum: InventedStratum) -> np.ndarray:
    """First-order SE of each group's ``log R_g`` in an invented stratum.

    With Bernoulli deaths of risk ``p`` and weights independent of risk,
    ``Var(log R_g) = A_g/O_g^2 + A/O^2 - 2 A_g/(O_g O)``, where ``O`` sums
    ``w p`` and ``A`` sums ``w^2 p (1 - p)``. Risks are
    ``mean_risk * u * rr_g`` with ``u ~ U(0.5, 1.5)``; the model is right.
    """
    _require(
        stratum.frailty_variance == 0, "analytic SE requires zero frailty"
    )
    n = stratum.n_clusters * stratum.mean_cluster_size
    shares = np.append(
        np.asarray(stratum.group_shares) * (1 - stratum.unclassified_share),
        stratum.unclassified_share,
    )
    rr = np.append(stratum.model_rr(), 1.0)
    kish = 1.0 + stratum.weight_cv**2
    e_p = stratum.mean_risk * rr
    e_p2 = (stratum.mean_risk * rr) ** 2 * (13.0 / 12.0)
    o = n * shares * e_p
    a = n * shares * kish * (e_p - e_p2)
    o_total, a_total = o.sum(), a.sum()
    var = a / o**2 + a_total / o_total**2 - 2 * a / (o * o_total)
    return np.sqrt(var[:-1])


def misfit_for_target_log_ratio(
    stratum: InventedStratum, group: int, target: float
) -> tuple[float, ...]:
    """Misfit vector making group ``group``'s population log R equal target.

    Only that group departs from the model. With linear risk and no
    frailty, ``R_g = k (E_g k + E_rest)^-1 E`` for misfit factor ``k``, so
    ``k = e^t E_rest / (E - e^t E_g)``.
    """
    _require(0 <= group < stratum.n_groups, "group index out of range")
    share = float(stratum.expected_group_deaths_share()[group])
    rest = 1.0 - share
    factor = math.exp(target)
    denominator = 1.0 - factor * share
    _require(denominator > 0, "target ratio unreachable for this share")
    k = factor * rest / denominator
    out = [0.0] * stratum.n_groups
    out[group] = math.log(k)
    return tuple(out)


def _simulate_cluster_totals(
    stratum: InventedStratum, rng: np.random.Generator
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """One invented sample: cluster totals of weighted deaths and risks.

    Returns ``(observed, expected, design_stratum)`` where the first two
    have shape ``(clusters, groups + 1)``; the last column holds the
    unclassified persons.
    """
    g = stratum.n_groups
    c = stratum.n_clusters
    sizes = 1 + rng.poisson(stratum.mean_cluster_size - 1.0, size=c)
    cluster = np.repeat(np.arange(c), sizes)
    n = cluster.size
    probabilities = np.append(
        np.asarray(stratum.group_shares) * (1 - stratum.unclassified_share),
        stratum.unclassified_share,
    )
    cumulative = np.cumsum(probabilities / probabilities.sum())
    cumulative[-1] = 1.0
    group = np.searchsorted(cumulative, rng.random(n), side="right")
    if stratum.weight_cv > 0:
        sigma2 = math.log1p(stratum.weight_cv**2)
        weight = rng.lognormal(-0.5 * sigma2, math.sqrt(sigma2), size=n)
    else:
        weight = np.ones(n)
    rr = np.append(stratum.model_rr(), 1.0)
    misfit = np.append(stratum.misfit(), 1.0)
    heterogeneity = rng.uniform(0.5, 1.5, size=n)
    model_risk = stratum.mean_risk * heterogeneity * rr[group]
    if stratum.frailty_variance > 0:
        v = stratum.frailty_variance
        frailty = rng.gamma(1.0 / v, v, size=c)[cluster]
    else:
        frailty = np.ones(n)
    true_risk = np.minimum(1.0, model_risk * misfit[group] * frailty)
    died = rng.random(n) < true_risk
    index = cluster * (g + 1) + group
    observed = np.bincount(
        index, weights=weight * died, minlength=c * (g + 1)
    ).reshape(c, g + 1)
    expected = np.bincount(
        index, weights=weight * model_risk, minlength=c * (g + 1)
    ).reshape(c, g + 1)
    design = np.arange(c) % stratum.n_design_strata
    return observed, expected, design


def _validated_totals(observed, expected):
    observed = np.asarray(observed, dtype=float)
    expected = np.asarray(expected, dtype=float)
    _require(
        observed.ndim >= 2 and observed.shape == expected.shape,
        "matching arrays with cluster and category axes required",
    )
    _require(
        observed.shape[-2] >= 1 and observed.shape[-1] >= 3,
        "at least one cluster, two groups and unclassified column",
    )
    _require(
        np.isfinite(observed).all() and np.isfinite(expected).all(),
        "totals must be finite",
    )
    _require(
        (observed >= 0).all() and (expected >= 0).all(),
        "totals must be nonnegative",
    )
    return observed, expected


def log_ratio_estimates(
    observed: np.ndarray, expected: np.ndarray
) -> np.ndarray:
    """``log R_g`` for every classified group from cluster totals.

    The last column is the unclassified persons, who enter only the
    overall ratio. A group with no observed deaths returns ``nan``.
    """
    observed, expected = _validated_totals(observed, expected)
    o_g = observed[..., :-1].sum(axis=-2)
    e_g = expected[..., :-1].sum(axis=-2)
    o = observed.sum(axis=(-2, -1))[..., None]
    e = expected.sum(axis=(-2, -1))[..., None]
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.log(o_g / e_g) - np.log(o / e)
    out[~np.isfinite(out)] = np.nan
    return out


def linearized_se(
    observed: np.ndarray, expected: np.ndarray, design: np.ndarray
) -> np.ndarray:
    """Taylor-linearized SE of ``log R_g`` with strata and clusters.

    ``z_c = (O_gc/O_g - E_gc/E_g) - (O_c/O - E_c/E)`` per cluster, and
    ``var = sum_h n_h/(n_h-1) sum_c (z_hc - mean_h)^2``: the
    ``uniform_cut_tabulation`` design-based convention.
    """
    observed, expected = _validated_totals(observed, expected)
    _require(observed.ndim == 2, "linearization requires 2-d totals")
    o_g = observed[:, :-1].sum(axis=0)
    e_g = expected[:, :-1].sum(axis=0)
    o_c = observed.sum(axis=1)
    e_c = expected.sum(axis=1)
    o, e = o_c.sum(), e_c.sum()
    with np.errstate(divide="ignore", invalid="ignore"):
        z = (observed[:, :-1] / o_g - expected[:, :-1] / e_g) - (
            o_c / o - e_c / e
        )[:, None]
    variance = _stratified_cluster_variance(z, design)
    se = np.sqrt(variance)
    se[~np.isfinite(se) | (o_g <= 0)] = np.nan
    return se


def _stratified_cluster_variance(
    z: np.ndarray, design: np.ndarray
) -> np.ndarray:
    """``sum_h n_h/(n_h-1) sum_c (z_hc - mean_h)^2`` for each column.

    Singleton design strata are refused: they cannot establish precision.
    """
    z = np.asarray(z, dtype=float)
    design = np.asarray(design)
    _require(
        z.ndim == 2
        and design.ndim == 1
        and z.shape[0] == design.size
        and design.size >= 2,
        "cluster totals and design must align",
    )
    _, stratum = np.unique(design, return_inverse=True)
    n_h = np.bincount(stratum).astype(float)
    _require((n_h >= 2).all(), "each design stratum needs two clusters")
    sums = np.stack(
        [np.bincount(stratum, weights=z[:, j]) for j in range(z.shape[1])],
        axis=1,
    )
    squares = np.stack(
        [
            np.bincount(stratum, weights=z[:, j] ** 2)
            for j in range(z.shape[1])
        ],
        axis=1,
    )
    within = squares - sums**2 / n_h[:, None]
    factor = np.where(n_h > 1, n_h / np.maximum(n_h - 1, 1), 0.0)
    return np.maximum((factor[:, None] * within).sum(axis=0), 0.0)


def bootstrap_se(
    observed: np.ndarray,
    expected: np.ndarray,
    design: np.ndarray,
    replicates: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Rao-Wu stratified cluster bootstrap SE of ``log R_g``.

    Within each design stratum, ``n_h - 1`` clusters are drawn with
    replacement and rescaled by ``n_h / (n_h - 1)``.
    """
    _require(
        isinstance(replicates, int)
        and not isinstance(replicates, bool)
        and replicates >= 2,
        "bootstrap needs at least two replicates",
    )
    observed, expected = _validated_totals(observed, expected)
    design = np.asarray(design)
    _require(
        observed.ndim == 2
        and design.ndim == 1
        and design.size == observed.shape[0],
        "design must align",
    )
    c = observed.shape[0]
    multipliers = np.zeros((replicates, c))
    for h in np.unique(design):
        members = np.flatnonzero(design == h)
        n_h = members.size
        _require(n_h >= 2, "each design stratum needs two clusters")
        draws = rng.integers(0, n_h, size=(replicates, n_h - 1))
        counts = np.zeros((replicates, n_h))
        np.add.at(
            counts,
            (np.repeat(np.arange(replicates), n_h - 1), draws.ravel()),
            1.0,
        )
        multipliers[:, members] = counts * n_h / (n_h - 1)
    boot_o = np.einsum("bc,ck->bk", multipliers, observed)
    boot_e = np.einsum("bc,ck->bk", multipliers, expected)
    estimates = log_ratio_estimates(boot_o[:, None, :], boot_e[:, None, :])
    # Any undefined replicate means this cell's bootstrap precision is
    # unresolved. Dropping such replicates could manufacture a narrow bound.
    return np.std(estimates, axis=0, ddof=1)


@dataclass(frozen=True)
class MonteCarloResult:
    """Pass/fail/inconclusive frequencies over simulated samples."""

    n_sims: int
    pass_rate: float
    fail_rate: float
    inconclusive_rate: float
    mc_se: float
    coverage: float | None = None
    extra: dict = field(default_factory=dict)


def _summarize(outcomes: list[str], coverage=None, **extra):
    n = len(outcomes)
    _require(n >= 1, "need at least one simulated realization")
    _require(
        set(outcomes) <= {PASS, FAIL, INCONCLUSIVE}, "unknown trial outcome"
    )
    counts = {k: outcomes.count(k) for k in (PASS, FAIL, INCONCLUSIVE)}
    rates = {k: count / n for k, count in counts.items()}
    p = rates[PASS]
    z_mc = bonferroni_z(1)
    denominator = 1 + z_mc**2 / n
    centre = (p + z_mc**2 / (2 * n)) / denominator
    radius = (
        z_mc * math.sqrt(p * (1 - p) / n + z_mc**2 / (4 * n * n)) / denominator
    )
    extra.update(
        outcome_counts=counts,
        mc_95_lower=max(0.0, centre - radius),
        mc_95_upper=min(1.0, centre + radius),
        mc_95_halfwidth=radius,
        mc_precision_target=ED2_TOLERANCE / 10,
        mc_precision_sufficient=(radius < ED2_TOLERANCE / 10),
        mc_lower_reaches_power_criterion=(
            centre - radius >= 0.90 and radius < ED2_TOLERANCE / 10
        ),
    )
    return MonteCarloResult(
        n_sims=n,
        pass_rate=p,
        fail_rate=rates[FAIL],
        inconclusive_rate=rates[INCONCLUSIVE],
        mc_se=math.sqrt(max(p * (1 - p), 1e-12) / n),
        coverage=coverage,
        extra=extra,
    )


def simulate_sm3_family(
    strata: Sequence[InventedStratum],
    *,
    n_sims: int,
    seed: int,
    tolerance: float = SM3_TOLERANCE,
    alpha: float = ALPHA,
    method: str = "linearized",
    bootstrap_replicates: int = 200,
) -> MonteCarloResult:
    """Monte Carlo of the registered SM3 decision over a family of strata.

    The family is every classified group in every stratum given; the
    Bonferroni factor counts all of those cells. Cluster linearization
    and bootstrap SEs have no finite-sample coverage guarantee on this
    accepted domain. Their raw decisions and empirical coverage are
    diagnostics only; every gate realization is inconclusive. The
    separate known-SE normal experiment retains its model-based bounds.
    """
    _require(
        isinstance(n_sims, int)
        and not isinstance(n_sims, bool)
        and n_sims >= 1,
        "n_sims must be >= 1",
    )
    tolerance = _finite_positive(tolerance, "tolerance")
    _require(method in ("linearized", "bootstrap"), "unknown method")
    strata = list(strata)
    _require(len(strata) >= 1, "a family needs at least one stratum")
    m = sum(s.n_groups for s in strata)
    z = bonferroni_z(m, alpha)
    supported = all(
        s.n_clusters <= MAX_INVENTED_PERSON_DRAWS
        and s.mean_cluster_size <= MAX_INVENTED_PERSON_DRAWS / s.n_clusters
        and s.weight_cv <= MAX_WEIGHT_CV
        and s.mean_risk >= 1e-12
        and min(s.group_shares) >= 1e-12
        and (s.frailty_variance == 0 or 1e-6 <= s.frailty_variance <= 1e6)
        for s in strata
    )
    if not supported:
        return _summarize(
            [INCONCLUSIVE] * n_sims,
            coverage=None,
            family_size=m,
            z=z,
            method=method,
            diagnostic_only=True,
            diagnostic_coverage=None,
            diagnostic_outcome_counts=None,
            interval_status="outside invented diagnostic precision envelope",
        )
    rng = np.random.default_rng(seed)
    truth = _population_family_log_ratios(strata)
    outcomes, covered = [], 0
    for _ in range(n_sims):
        samples = [_simulate_cluster_totals(s, rng) for s in strata]
        obs, exp_, design = _join_sm3_strata(samples)
        est = log_ratio_estimates(obs, exp_)
        if method == "linearized":
            se = linearized_se(obs, exp_, design)
        else:
            se = bootstrap_se(obs, exp_, design, bootstrap_replicates, rng)
        half = z * se
        cells = classify_bounds(est, half, tolerance)
        ok = np.isfinite(est) & np.isfinite(half)
        covered += bool(ok.all() and (np.abs(est - truth) <= half).all())
        outcomes.append(conjunction(cells))
    return _summarize(
        [INCONCLUSIVE] * n_sims,
        coverage=None,
        family_size=m,
        z=z,
        method=method,
        diagnostic_only=True,
        diagnostic_coverage=covered / n_sims,
        diagnostic_outcome_counts={
            value: outcomes.count(value)
            for value in (PASS, FAIL, INCONCLUSIVE)
        },
        interval_status="unsupported finite-sample SM3 precision",
    )


def _join_sm3_strata(samples):
    """Combine invented strata, retaining one cohort-wide denominator.

    Families are independent across the invented strata. Real analyses
    must retain a family's common identifier across all sex/age cells.
    The shared last column pools every unclassified person.
    """
    n = sum(o.shape[0] for o, _, _ in samples)
    m = sum(o.shape[1] - 1 for o, _, _ in samples)
    observed, expected = np.zeros((n, m + 1)), np.zeros((n, m + 1))
    design = np.empty(n, dtype=int)
    row = column = offset = 0
    for obs, exp_, labels in samples:
        c, k = obs.shape[0], obs.shape[1] - 1
        observed[row : row + c, column : column + k] = obs[:, :-1]
        expected[row : row + c, column : column + k] = exp_[:, :-1]
        observed[row : row + c, -1] = obs[:, -1]
        expected[row : row + c, -1] = exp_[:, -1]
        _, labels = np.unique(labels, return_inverse=True)
        design[row : row + c] = labels + offset
        offset += int(labels.max()) + 1
        row, column = row + c, column + k
    return observed, expected, design


def _population_expected_and_observed(stratum):
    shares = np.append(
        np.asarray(stratum.group_shares) * (1 - stratum.unclassified_share),
        stratum.unclassified_share,
    )
    rr = np.append(stratum.model_rr(), 1.0)
    misfit = np.append(stratum.misfit(), 1.0)
    scale = stratum.n_clusters * stratum.mean_cluster_size
    expected = scale * shares * stratum.mean_risk * rr
    if stratum.frailty_variance == 0:
        return expected, expected * misfit
    # Deterministic quadrature integrates min(1, a*frailty) over the
    # Uniform(.5,1.5) risk mixture and Gamma(shape=1/v, scale=v) frailty.
    nodes, weights = np.polynomial.legendre.leggauss(80)
    u = 1 + nodes / 2
    a = stratum.mean_risk * rr[:, None] * misfit[:, None] * u
    shape = 1 / stratum.frailty_variance
    risk = a * gammainc(shape + 1, shape / a) + gammaincc(shape, shape / a)
    observed = scale * shares * (risk @ (weights / 2))
    return expected, observed


def _population_family_log_ratios(strata):
    totals = [_population_expected_and_observed(s) for s in strata]
    overall = sum(o.sum() for _, o in totals) / sum(e.sum() for e, _ in totals)
    return np.concatenate(
        [np.log(o[:-1] / e[:-1]) - math.log(overall) for e, o in totals]
    )


def _population_log_ratio(stratum: InventedStratum, seed: int) -> np.ndarray:
    """Deterministic invented-population truth; seed retained for API use."""
    return _population_family_log_ratios([stratum])


# --------------------------------------------------------------------------
# ED2: projected minus target shares on invented samples
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class InventedSharesCell:
    """One sex x age-group ED2 cell with ``K`` categories (INVENTED).

    The model sample is the frame's persons projected ``replicates``
    times; the target is an independent survey. ``icc`` is the
    intraclass correlation of attainment within a household; ``bias`` is
    the model's true share error (it must sum to zero).
    """

    shares: tuple[float, ...]
    n_model: int
    n_target: int
    model_cluster_size: float = 2.0
    target_cluster_size: float = 2.0
    icc: float = 0.1
    weight_cv: float = 0.6
    replicates: int = 10
    bias: tuple[float, ...] | None = None

    def __post_init__(self) -> None:
        p = _shares(self.shares, "shares")
        _require(p.size >= 2, "need at least two categories")
        for name in ("n_model", "n_target"):
            value = getattr(self, name)
            _require(
                isinstance(value, int)
                and not isinstance(value, bool)
                and value >= 10,
                f"{name} must be >= 10",
            )
        for name in ("model_cluster_size", "target_cluster_size"):
            value = getattr(self, name)
            _require(
                math.isfinite(value) and value >= 1, f"{name} must be >= 1"
            )
        _require(0 <= self.icc < 1, "icc must lie in [0, 1)")
        _require(
            math.isfinite(self.weight_cv) and self.weight_cv >= 0,
            "weight CV must be finite and >= 0",
        )
        _require(
            isinstance(self.replicates, int)
            and not isinstance(self.replicates, bool)
            and self.replicates >= 1,
            "replicates must be >= 1",
        )
        if self.bias is not None:
            b = np.asarray(self.bias, dtype=float)
            _require(b.shape == p.shape, "bias needs one value per category")
            _require(abs(b.sum()) < 1e-12, "bias must sum to zero")
            _require(np.isfinite(b).all(), "bias must be finite")
            _require(
                ((p + b) > 0).all() and ((p + b) < 1).all(),
                "biased shares must lie in (0, 1)",
            )


def _clustered_categories(
    shares: np.ndarray,
    n: int,
    cluster_size: float,
    icc: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Persons' category probabilities, cluster index and cluster sizes."""
    draw = int(math.ceil(n / cluster_size)) + 16
    sizes = 1 + rng.poisson(cluster_size - 1.0, size=draw)
    while sizes.sum() < n:
        sizes = np.append(sizes, 1 + rng.poisson(cluster_size - 1.0, draw))
    ends = np.cumsum(sizes)
    last = int(np.searchsorted(ends, n))
    sizes = sizes[: last + 1].copy()
    sizes[-1] -= int(ends[last] - n)
    cluster = np.repeat(np.arange(sizes.size), sizes)
    if icc > 0:
        concentration = (1 - icc) / icc
        cluster_p = rng.dirichlet(shares * concentration, size=sizes.size)
    else:
        cluster_p = np.tile(shares, (sizes.size, 1))
    return cluster_p[cluster], cluster, sizes


def _weights(n: int, cv: float, rng: np.random.Generator) -> np.ndarray:
    if cv == 0:
        return np.ones(n)
    sigma2 = math.log1p(cv**2)
    return rng.lognormal(-0.5 * sigma2, math.sqrt(sigma2), size=n)


class UnestimableRealization(ValueError):
    """A valid stochastic draw cannot establish sampling precision."""


def _share_and_var(
    indicator: np.ndarray, weight: np.ndarray, cluster: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Weighted shares and their cluster-linearized variances.

    Refuse a sample with fewer than two realized clusters: its variance
    is unestimated, so it cannot establish the gate's power criterion.
    """
    n_c = int(cluster.max()) + 1
    if n_c < 2:
        raise UnestimableRealization(
            "ED2 variance needs at least two realized clusters"
        )
    total = weight.sum()
    share = (weight[:, None] * indicator).sum(axis=0) / total
    z = weight[:, None] * (indicator - share) / total
    zc = np.stack(
        [
            np.bincount(cluster, weights=z[:, j], minlength=n_c)
            for j in range(z.shape[1])
        ],
        axis=1,
    )
    var = n_c / (n_c - 1) * ((zc - zc.mean(axis=0)) ** 2).sum(axis=0)
    return share, var


def ed2_cluster_half_width(
    model_weight: np.ndarray,
    model_cluster: np.ndarray,
    target_weight: np.ndarray,
    target_cluster: np.ndarray,
    m: int,
    alpha: float = ALPHA,
) -> float:
    """Finite-sample simultaneous Hoeffding bound for share differences.

    Condition on weights and cluster sizes, independent of attainment in
    this invented sampler. Each independent household's contribution to
    a share lies in an interval of length ``a_c = W_c / sum W``. For
    independent model/target samples, Hoeffding gives
    ``P(|estimated difference - true difference| > h) <= alpha/m`` with
    ``h² = log(2m/alpha) * (sum a_model² + sum a_target²) / 2``.
    A union bound covers all m categories regardless of their covariance,
    prevalence or zero counts. Replicate averaging stays in [0, 1]; it
    does not create independent households. No normal approximation or
    estimated category variance enters this bound.

    Actual complex surveys need their registered design-specific bound;
    these independent invented households cannot certify that design.
    """
    m = _family_size(m)
    alpha = _probability(alpha, "alpha")

    def squared_ranges(weight, cluster):
        weight = np.asarray(weight, dtype=float)
        cluster = np.asarray(cluster)
        _require(
            weight.ndim == cluster.ndim == 1
            and weight.size == cluster.size
            and weight.size > 0,
            "weights and clusters must align",
        )
        _require(
            np.isfinite(weight).all() and (weight >= 0).all(),
            "weights must be finite and nonnegative",
        )
        _, labels = np.unique(cluster, return_inverse=True)
        # Scaling avoids overflow without changing normalized weights.
        scale = weight.max()
        if scale == 0:
            raise UnestimableRealization("ED2 weights have no positive mass")
        household = np.bincount(labels, weights=weight / scale)
        ranges = household / household.sum()
        return float(ranges @ ranges)

    ranges = squared_ranges(model_weight, model_cluster) + squared_ranges(
        target_weight, target_cluster
    )
    return math.sqrt(0.5 * (math.log(2 * m) - math.log(alpha)) * ranges)


def simulate_ed2_family(
    cells: Sequence[InventedSharesCell],
    *,
    n_sims: int,
    seed: int,
    tolerance: float = ED2_TOLERANCE,
    alpha: float = ALPHA,
) -> MonteCarloResult:
    """Monte Carlo of the registered ED2 decision over a family of cells.

    The family is every category of every cell. Each simulated sample
    draws a frame and projects each frame person ``replicates`` times
    from their own probabilities, and draws an independent target
    survey. The model's systematic error is ``bias``, added to its
    shares. Hoeffding bounds use normalized household weight totals on
    both sides, retaining within-household dependence even for empty
    categories. Projection noise is also reported separately
    (``max_projection_mc_se``) for the one-tenth rule. An unestimable
    realization is counted once as inconclusive, without retrying it.
    """
    _require(
        isinstance(n_sims, int)
        and not isinstance(n_sims, bool)
        and n_sims >= 1,
        "n_sims must be >= 1",
    )
    tolerance = _finite_positive(tolerance, "tolerance")
    cells = list(cells)
    _require(len(cells) >= 1, "a family needs at least one cell")
    m = sum(len(c.shares) for c in cells)
    z = bonferroni_z(m, alpha)

    def supported(cell):
        # Validate the numeric sampler before any realization. Specifications
        # remain accepted; unavailable precision is counted, never retried.
        if (
            cell.n_model > MAX_INVENTED_PERSON_DRAWS
            or cell.n_target > MAX_INVENTED_PERSON_DRAWS
            or cell.replicates > MAX_INVENTED_PERSON_DRAWS // cell.n_model
            or cell.model_cluster_size > MAX_INVENTED_PERSON_DRAWS
            or cell.target_cluster_size > MAX_INVENTED_PERSON_DRAWS
            or cell.weight_cv > MAX_WEIGHT_CV
        ):
            return False
        if cell.icc > 0:
            concentration = (1 - cell.icc) / cell.icc
            shapes = np.asarray(cell.shares) * concentration
            if not np.isfinite(shapes).all() or (shapes < 1e-12).any():
                return False
        return True

    if not all(supported(cell) for cell in cells):
        return _summarize(
            [INCONCLUSIVE] * n_sims,
            coverage=None,
            family_size=m,
            z=z,
            interval_method="household_hoeffding_bonferroni",
            unestimable_realizations=n_sims,
            max_projection_mc_se=None,
            interval_status="outside invented sampler precision envelope",
        )
    rng = np.random.default_rng(seed)
    outcomes, covered, worst_mc, unestimable = [], 0, 0.0, 0
    for _ in range(n_sims):
        results, ok = [], True
        for cell in cells:
            p = np.asarray(cell.shares, dtype=float)
            b = (
                np.zeros_like(p)
                if cell.bias is None
                else np.asarray(cell.bias, dtype=float)
            )
            k = p.size
            probs_m, cl_m, _ = _clustered_categories(
                p, cell.n_model, cell.model_cluster_size, cell.icc, rng
            )
            w_m = _weights(cell.n_model, cell.weight_cv, rng)
            draws = np.stack(
                [_categorical(probs_m, rng) for _ in range(cell.replicates)]
            )
            ind = np.eye(k)[draws].mean(axis=0)
            try:
                share_m, _ = _share_and_var(ind, w_m, cl_m)
            except UnestimableRealization:
                unestimable += 1
                results, ok = [INCONCLUSIVE], False
                break
            share_m = share_m + b
            # Conditional projection noise is known on invented probabilities;
            # an empirical across-replicate variance can understate it, or be
            # undefined for one replicate. Insufficient MC precision prevents
            # a pass even if the sampling confidence bound is narrow.
            mc_se = np.sqrt(
                ((w_m[:, None] ** 2) * probs_m * (1 - probs_m)).sum(axis=0)
                / w_m.sum() ** 2
                / cell.replicates
            )
            worst_mc = max(worst_mc, float(mc_se.max()))
            probs_t, cl_t, _ = _clustered_categories(
                p, cell.n_target, cell.target_cluster_size, cell.icc, rng
            )
            w_t = _weights(cell.n_target, cell.weight_cv, rng)
            ind_t = np.eye(k)[_categorical(probs_t, rng)]
            try:
                share_t, _ = _share_and_var(ind_t, w_t, cl_t)
                half = ed2_cluster_half_width(w_m, cl_m, w_t, cl_t, m, alpha)
            except UnestimableRealization:
                unestimable += 1
                results, ok = [INCONCLUSIVE], False
                break
            est = share_m - share_t
            cell_outcomes = classify_bounds(
                est, np.full(est.shape, half), tolerance
            )
            cell_outcomes[
                (cell_outcomes == PASS) & (mc_se >= tolerance / 10)
            ] = INCONCLUSIVE
            results.extend(cell_outcomes)
            ok &= bool((np.abs(est - b) <= half).all())
        outcomes.append(conjunction(results))
        covered += ok
    return _summarize(
        outcomes,
        coverage=covered / n_sims,
        family_size=m,
        z=z,
        interval_method="household_hoeffding_bonferroni",
        unestimable_realizations=unestimable,
        max_projection_mc_se=worst_mc,
    )


def ed2_cell_analytic_ses(cell: InventedSharesCell) -> np.ndarray:
    """First-order SE of each category's share difference in a cell.

    With household sizes ``1 + Poisson(s - 1)`` the size-biased mean is
    ``kappa = (s - 1 + s^2) / s``; Dirichlet household probabilities give
    ``Var(pi) = p(1-p) icc``. The model's averaged indicator has
    variance ``Var(pi) kappa + E[pi(1-pi)] / R`` per person; the target's
    observed indicator ``p(1-p)(1 + (kappa - 1) icc)``; both scale by the
    weights' Kish factor and divide by their sample sizes.
    """
    p = np.asarray(cell.shares, dtype=float)
    kish = 1.0 + cell.weight_cv**2

    def kappa(size: float) -> float:
        return (size - 1.0 + size**2) / size

    v = p * (1 - p)
    model = (
        v
        * (
            kish * (cell.icc + (1 - cell.icc) / cell.replicates)
            + (kappa(cell.model_cluster_size) - 1) * cell.icc
        )
        / cell.n_model
    )
    target = (
        v
        * (kish + (kappa(cell.target_cluster_size) - 1) * cell.icc)
        / cell.n_target
    )
    return np.sqrt(model + target)


def _categorical(probabilities: np.ndarray, rng: np.random.Generator):
    cumulative = np.cumsum(probabilities, axis=1)
    cumulative[:, -1] = 1.0
    u = rng.random((probabilities.shape[0], 1))
    return (u > cumulative).sum(axis=1)


# --------------------------------------------------------------------------
# The record's grid
# --------------------------------------------------------------------------
def sm3_analytic_grid() -> dict:
    """Minimal sufficient effective deaths for the union-bound guarantee.

    Per-dimension admission uses four sex/age-band cells per group.
    The 52-cell all-dimension family is a sensitivity. Equal expected
    deaths and 10% unclassified deaths are invented assumptions, not
    estimates. Every denominator is the entire registered cohort.
    """
    out = {}
    all_cells = sum(SM3_GROUPS.values()) * 4
    for dimension, groups in SM3_GROUPS.items():
        rows = []
        share = 0.9 / (groups * 4)
        for scope, m in (
            ("per_dimension", groups * 4),
            ("all_dimensions_sensitivity", all_cells),
        ):
            for delta in (0.0, 0.05):
                d = min_effective_deaths_per_cell(
                    m, group_share=share, delta=delta
                )
                rows.append(
                    {
                        "scope": scope,
                        "family_size": m,
                        "true_abs_log_ratio_bound": delta,
                        "assumed_cohort_death_share_per_cell": share,
                        "min_sufficient_effective_deaths_per_cell": d,
                        "effective_classified_deaths_over_dimension_cells": d
                        * groups
                        * 4,
                        "effective_cohort_deaths_including_unclassified": math.ceil(
                            d * groups * 4 / 0.9
                        ),
                    }
                )
        out[dimension] = {"groups": groups, "rows": rows}
    return out


def sm3_power_curve() -> list[dict]:
    """Declared effective-death grid; guarantee and independence diagnostic."""
    rows = []
    for dimension, groups in SM3_GROUPS.items():
        m, share = groups * 4, 0.9 / (groups * 4)
        for d in (10, 25, 50, 100, 200, 400, 800, 1600, 3200, 6400):
            se = math.sqrt((1 - share) / d)
            lower = family_power_lower_bound(
                [0.0] * m, [se] * m, SM3_TOLERANCE
            )
            rows.append(
                {
                    "dimension": dimension,
                    "family_size": m,
                    "effective_deaths_per_cell": d,
                    "power_lower_bound": lower,
                    "independence_approximation": family_power(
                        [0.0] * m, [se] * m, SM3_TOLERANCE
                    ),
                    "condition": (
                        None
                        if lower >= POWER_CRITERION
                        else "WEAK_POWER_OR_VACUITY"
                    ),
                }
            )
    return rows


def sm3_assumed_count_grid() -> dict:
    """Persons/risk/design grid, with no real structural count input.

    D_eff = n * window_death_probability / design_effect is a conservative
    Poisson screening model; actual finite-person Bernoulli and survey
    effects must be estimated in the authorized step. The public sample
    totals contextualize grid scale and do not bound a particular cohort.
    """
    rows, minima = [], []
    for dimension, groups in SM3_GROUPS.items():
        m, share = groups * 4, 0.9 / (groups * 4)
        d_min = min_effective_deaths_per_cell(m, group_share=share)
        for risk in ASSUMED_WINDOW_RISKS:
            for deff in ASSUMED_DESIGN_EFFECTS:
                passing = []
                for n in ASSUMED_PERSON_GRID:
                    d = n * risk / deff
                    se = math.sqrt((1 - share) / d)
                    lower = family_power_lower_bound(
                        [0.0] * m, [se] * m, SM3_TOLERANCE
                    )
                    if lower >= POWER_CRITERION:
                        passing.append(n)
                    rows.append(
                        {
                            "dimension": dimension,
                            "persons_per_group_sex_band_cell": n,
                            "invented_independent_cell_people_total": n * m,
                            "within_documentation_person_envelope": n * m
                            <= PUBLIC_SAMPLE_CONTEXT["individuals"],
                            "window_death_probability": risk,
                            "design_effect": deff,
                            "effective_deaths_per_cell": d,
                            "family_power_lower_bound": lower,
                            "condition": (
                                None
                                if lower >= POWER_CRITERION
                                else "WEAK_POWER_OR_VACUITY"
                            ),
                        }
                    )
                minima.append(
                    {
                        "dimension": dimension,
                        "window_death_probability": risk,
                        "design_effect": deff,
                        "minimum_sufficient_persons_per_cell": math.ceil(
                            d_min * deff / risk
                        ),
                        "smallest_passing_person_grid_count": (
                            min(passing) if passing else None
                        ),
                    }
                )
    return {
        "assumed_person_grid": ASSUMED_PERSON_GRID,
        "assumed_window_death_probabilities": ASSUMED_WINDOW_RISKS,
        "assumed_design_effects": ASSUMED_DESIGN_EFFECTS,
        "risk_window": [2011, 2023],
        "unclassified_cohort_death_share": 0.1,
        "minima": minima,
        "rows": rows,
    }


ED2_INVENTED_SHARES = (0.08, 0.26, 0.26, 0.26, 0.14)
"""Invented shares: <HS, HS, some college/associate, bachelor, graduate."""


def ed2_analytic_grid() -> list[dict]:
    """Sufficient effective n for each sex/cohort cell, all categories.

    Proposed primary: ten age-derived birth-cohort intervals x two sexes
    x five categories = 100 cells, conditional on locating and freezing
    suitable public held-out target microdata. Published CPS tables support
    the 20-cell sensitivity and ACS supports the 10-cell sensitivity.
    Pooling cohorts changes the estimand. The binding variance p(1-p) conservatively stands
    in for every category in the union-bound power calculation.
    """
    k = len(ED2_INVENTED_SHARES)
    p = max(ED2_INVENTED_SHARES, key=lambda p: p * (1 - p))
    rows = []
    for scope, m in (
        ("sex_x_single_cohort_25_34_primary", k * 2 * 10),
        ("sex_x_25_29_30_34_sensitivity", k * 2 * 2),
        ("sex_x_25_34_sensitivity", k * 2),
    ):
        for label, target in (
            ("negligible_target_error", math.inf),
            ("target_n_eff_100000", 100_000.0),
            ("target_n_eff_20000", 20_000.0),
            ("target_n_eff_5000", 5_000.0),
        ):
            for delta in (0.0, 0.005):
                n = min_effective_n_per_cell(
                    m, share=p, n_target_eff=target, delta=delta
                )
                rows.append(
                    {
                        "scope": scope,
                        "family_size": m,
                        "target": label,
                        "true_abs_share_error_bound": delta,
                        "binding_share": p,
                        "min_sufficient_effective_model_n_per_sex_cohort": n,
                        "condition": (
                            "WEAK_POWER_OR_VACUITY" if n is None else None
                        ),
                    }
                )
    return rows


def tr2026_band_q(years=range(2012, 2024)) -> dict:
    """Mean single-age q by band and sex (OACT TR 2026, permitted input)."""
    try:
        from populace_dynamics.data import tr2026
    except ImportError:  # pragma: no cover - uninstalled checkout
        root = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(root / "src"))
        from populace_dynamics.data import tr2026

    out = {}
    for sex in SEXES:
        for lo, hi in SM3_AGE_BANDS:
            values = [
                float(np.mean(tr2026.death_probability(y, sex)[lo : hi + 1]))
                for y in years
            ]
            out[f"{sex}_{lo}_{hi}"] = round(float(np.mean(values)), 6)
    return {
        "source": "populace_dynamics.data.tr2026.death_probability",
        "years": [min(years), max(years)],
        "unweighted_mean_of_single_age_q": out,
    }


def cumulative_risk_bound(
    q_lookup,
    band: tuple[int, int],
    years: Sequence[int],
    relative_risk: float,
) -> float:
    """Largest risk of dying within one band inside the window.

    A person entering the band at any age and any window year, with every
    year's ``q`` multiplied by ``relative_risk`` (capped at one), stays at
    most until the band's top age or the window's end. Because each
    person dies at most once, deaths' Bernoulli variance is at least
    ``1 - bound`` times their Poisson variance, which bounds effective
    deaths from below by raw deaths times that factor.
    """
    lo, hi = band
    _require(0 <= lo <= hi <= 119, "band must lie in ages 0-119")
    years = sorted(int(y) for y in years)
    _require(len(years) >= 1, "window needs at least one year")
    rr = _finite_positive(relative_risk, "relative risk")
    tables = {
        (y, sex): np.asarray(q_lookup(y, sex), dtype=float)
        for y in years
        for sex in SEXES
    }
    worst = 0.0
    for sex in SEXES:
        for start_index in range(len(years)):
            for entry_age in range(lo, hi + 1):
                survive = 1.0
                for offset, year in enumerate(years[start_index:]):
                    age = entry_age + offset
                    if age > hi:
                        break
                    q = min(1.0, rr * tables[(year, sex)][age])
                    survive *= 1.0 - q
                worst = max(worst, 1.0 - survive)
    return worst


def simulate_sm3_normal_family(
    groups: int,
    effective_deaths: float,
    *,
    n_sims: int,
    seed: int,
    unclassified_share: float = 0.1,
) -> MonteCarloResult:
    """Full 4K-cell family with the actual shared-denominator covariance.

    Independent normal Poisson count perturbations induce
    Cov(log R_i, log R_j) = -1/D_cohort and
    Var(log R_i) = 1/D_i - 1/D_cohort. The unclassified count is perturbed
    too, while never receiving a group cell. This is a power approximation
    on an invented covariance, not a survey admission calculation.
    """
    groups = _family_size(groups)
    _require(groups >= 2, "need at least two groups")
    d = _finite_positive(effective_deaths, "effective deaths")
    u = _probability(unclassified_share, "unclassified share")
    _require(
        isinstance(n_sims, int)
        and not isinstance(n_sims, bool)
        and n_sims > 0,
        "n_sims must be a positive integer",
    )
    m = groups * 4
    counts = np.append(np.full(m, d), m * d * u / (1 - u))
    total = counts.sum()
    se = math.sqrt(1 / d - 1 / total)
    rng = np.random.default_rng(seed)
    outcomes, covered = [], 0
    z = bonferroni_z(m)
    # Batching caps memory for high-precision power estimates.
    for first in range(0, n_sims, 5000):
        size = min(5000, n_sims - first)
        perturb = rng.normal(size=(size, m + 1)) * np.sqrt(counts)
        estimate = perturb[:, :-1] / d - perturb.sum(axis=1)[:, None] / total
        half = np.full(estimate.shape, z * se)
        cells = classify_bounds(estimate, half, SM3_TOLERANCE)
        passed = (cells == PASS).all(axis=1)
        failed = (cells == FAIL).any(axis=1)
        outcomes.extend(
            np.where(passed, PASS, np.where(failed, FAIL, INCONCLUSIVE))
        )
        covered += int((np.abs(estimate) <= half).all(axis=1).sum())
    return _summarize(
        outcomes,
        coverage=covered / n_sims,
        family_size=m,
        effective_deaths_per_cell=d,
        shared_cohort_denominator=True,
    )


def simulate_ed2_normal_family(
    n_model_eff: float,
    n_target_eff: float,
    *,
    n_sims: int,
    seed: int,
    cohort_sex_cells: int = 20,
) -> MonteCarloResult:
    """Full multinomial share covariance over five categories per cell."""
    nm = _finite_positive(n_model_eff, "model effective n")
    nt = _finite_positive(n_target_eff, "target effective n")
    blocks = _family_size(cohort_sex_cells)
    _require(
        isinstance(n_sims, int)
        and not isinstance(n_sims, bool)
        and n_sims > 0,
        "n_sims must be a positive integer",
    )
    p = np.asarray(ED2_INVENTED_SHARES)
    m = p.size * blocks
    scale = math.sqrt(1 / nm + 1 / nt)
    se = np.sqrt(p * (1 - p)) * scale
    half = bonferroni_z(m) * se
    rng = np.random.default_rng(seed)
    outcomes, covered = [], 0
    for first in range(0, n_sims, 2000):
        size = min(2000, n_sims - first)
        noise = rng.normal(size=(size, blocks, p.size)) * np.sqrt(p)
        estimate = (noise - p * noise.sum(axis=2, keepdims=True)) * scale
        bounds = np.broadcast_to(half, estimate.shape)
        cells = classify_bounds(estimate, bounds, ED2_TOLERANCE)
        passed = (cells == PASS).all(axis=(1, 2))
        failed = (cells == FAIL).any(axis=(1, 2))
        outcomes.extend(
            np.where(passed, PASS, np.where(failed, FAIL, INCONCLUSIVE))
        )
        covered += int((np.abs(estimate) <= bounds).all(axis=(1, 2)).sum())
    return _summarize(
        outcomes,
        coverage=covered / n_sims,
        family_size=m,
        model_effective_n=nm,
        target_effective_n=nt,
    )


def validation_points(n_sims: int, seed: int) -> list[dict]:
    """High-precision Monte Carlo over the complete primary families."""
    points = []
    for groups in (4, 5):
        m, share = groups * 4, 0.9 / (groups * 4)
        d_min = min_effective_deaths_per_cell(m, group_share=share)
        for factor in (0.5, 1.0, 1.25):
            d = math.ceil(d_min * factor)
            se = math.sqrt((1 - share) / d)
            mc = simulate_sm3_normal_family(
                groups, d, n_sims=n_sims, seed=seed + groups
            )
            points.append(
                {
                    "label": f"sm3_{m}_cells_deaths_{d}",
                    "normal_power_lower_bound": family_power_lower_bound(
                        [0.0] * m, [se] * m, SM3_TOLERANCE
                    ),
                    "independence_approximation": family_power(
                        [0.0] * m, [se] * m, SM3_TOLERANCE
                    ),
                    "mc": asdict(mc),
                }
            )
    m = 100
    p = max(ED2_INVENTED_SHARES, key=lambda p: p * (1 - p))
    n_min = min_effective_n_per_cell(m, share=p, n_target_eff=100000)
    for factor in (0.5, 1.0, 1.25):
        n = math.ceil(n_min * factor)
        ses = [share_difference_se(p, n, 100000)] * m
        mc = simulate_ed2_normal_family(
            n, 100000, n_sims=n_sims, seed=seed + 101
        )
        points.append(
            {
                "label": f"ed2_100_cells_model_n_{n}",
                "normal_power_lower_bound": family_power_lower_bound(
                    [0.0] * m, ses, ED2_TOLERANCE
                ),
                "independence_binding_category_approximation": family_power(
                    [0.0] * m, ses, ED2_TOLERANCE
                ),
                "mc": asdict(mc),
            }
        )
    return points


def clustered_validation_points(seed: int) -> list[dict]:
    """Estimator/bootstrap diagnostics, explicitly too imprecise for power.

    These low-replication checks exercise invented survey/family clusters.
    Only the high-precision normal experiment is used to quantify grid
    operating characteristics; neither stands in for the real design.
    """
    stratum = InventedStratum(
        n_clusters=2000, group_shares=(0.2,) * 5, mean_risk=0.15, weight_cv=0.6
    )
    points = []
    for method in ("linearized", "bootstrap"):
        result = simulate_sm3_family(
            [stratum] * 4,
            n_sims=40,
            seed=seed,
            method=method,
            bootstrap_replicates=400,
        )
        points.append(
            {
                "label": f"sm3_full_family_cluster_{method}",
                "diagnostic_only": True,
                "mc": asdict(result),
            }
        )
    cell = InventedSharesCell(
        shares=ED2_INVENTED_SHARES, n_model=500, n_target=1000, replicates=40
    )
    result = simulate_ed2_family([cell] * 20, n_sims=40, seed=seed)
    points.append(
        {
            "label": "ed2_full_family_cluster_hoeffding",
            "diagnostic_only": True,
            "mc": asdict(result),
        }
    )
    return points


def build_results(n_sims: int, seed: int, anchors: bool) -> dict:
    """Invented-data calculations; real structural power remains open."""
    _require(
        isinstance(n_sims, int)
        and not isinstance(n_sims, bool)
        and n_sims >= 250000,
        "at least 250000 simulations for worst-case 95% MC halfwidth < .002",
    )
    out = {
        "schema_version": SCHEMA_VERSION,
        "invented_data_only": True,
        "design_commit": DESIGN_COMMIT,
        "procedure": PROCEDURE,
        "seed": seed,
        "constants": {
            "alpha": ALPHA,
            "power_criterion": POWER_CRITERION,
            "sm3_tolerance_log": SM3_TOLERANCE,
            "ed2_tolerance": ED2_TOLERANCE,
            "sm3_age_bands": SM3_AGE_BANDS,
            "sm3_groups": SM3_GROUPS,
            "ed2_invented_shares": ED2_INVENTED_SHARES,
        },
        "public_sample_context": PUBLIC_SAMPLE_CONTEXT,
        "sm3_analytic": sm3_analytic_grid(),
        "sm3_power_curve": sm3_power_curve(),
        "sm3_assumed_count_grid": sm3_assumed_count_grid(),
        "ed2_analytic": ed2_analytic_grid(),
        "mc_requirements": {
            "normal_power_sims": n_sims,
            "worst_case_power_mc_se": 0.5 / math.sqrt(n_sims),
            "worst_case_power_mc_95_halfwidth": bonferroni_z(1)
            * 0.5
            / math.sqrt(n_sims),
            "power_decision_rule": "95% MC lower bound >= .90 and halfwidth < .002",
            "sm3_bootstrap_replicates_at_se_0_05_m20": bootstrap_replicates_for_mc_error(
                bonferroni_z(20), 0.05, SM3_TOLERANCE
            ),
            "ed2_projection_replicates_at_sd_0_005": projection_replicates_for_mc_error(
                0.005, ED2_TOLERANCE
            ),
        },
        "validation": validation_points(n_sims, seed),
        "clustered_validation": clustered_validation_points(seed),
        "real_structural_power_status": "open; counts not inspected",
    }
    if anchors:
        out["tr2026_band_q"] = tr2026_band_q(range(2011, 2024))
    return out


def _jsonable(value):
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (np.floating, float)):
        return float(round(float(value), 6))
    if isinstance(value, (np.integer,)):
        return int(value)
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--sims", type=int, default=300_000)
    parser.add_argument("--seed", type=int, default=20261024)
    parser.add_argument("--no-anchors", action="store_true")
    args = parser.parse_args(argv)
    results = _jsonable(
        build_results(args.sims, args.seed, anchors=not args.no_anchors)
    )
    text = json.dumps(results, indent=2, sort_keys=True) + "\n"
    if args.out is None:
        sys.stdout.write(text)
    else:
        args.out.write_text(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
