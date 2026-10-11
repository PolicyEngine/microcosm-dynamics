#!/usr/bin/env python3
"""Track B B0.1 addendum: B2's gate power on the configuration Max ruled.

On 2026-10-11 Max ruled the three questions the addendum queued:

- d781 (a): B2 gates only the six level cells, ``earn_p50``, ``earn_p90``
  and ``earn_zero_rate`` by cohort. The other ten cells are scored and
  published report-only. Section 5's ladder still runs inside the six on
  B2's own floor.
- d782: B2's registered standard error resamples PSID's sampling-error
  clusters within strata (Rao-Wu). The floor split and the gate seeds'
  split stay household (d693 Q3).
- d765: the refit arm's household half-samples stand, so the planning
  record's estimation variances stand.

Round-1 Q6 finding M2 adds a rider to d782: a design-based standard error
built from 63 strata with two clusters each has about 63 degrees of
freedom, so B2 registers a t critical value in place of the normal one.

This module recomputes the named power procedure (protocol v2,
``scripts/track_b_b0_1_addendum_power.py``) on that configuration. Like
that script it reads no data. Its only input is the planning-value record
``docs/design/track_b_b0_1_planning_values.json``, which holds variance
ratios from the 2006 pseudo-origin and nothing dated after 2010.

The model, per cell, in units of the cell's household se_up:

- ``r`` is arm F's point estimate of the shared-anchor ratio and ``d`` the
  design ratio, SD(gap over arm D) / SD(gap over arm F). Under Rao-Wu
  resampling the gap's sampling variance is ``(r d)**2``.
- ``e_true`` and ``e_reg`` are the estimation parts of the gap variance
  and of the registered variance. Protocol v2's binding evaluation sets
  both to ``s2_gate - r**2`` (``s2_gate`` is the 97.5% upper limit of
  ``r**2 + e``); its point-variance sensitivity sets ``e_true`` to
  ``s2 - r**2`` and ``e_reg`` to the registered ``e_B2``. d765 leaves
  both as measured.
- The full-support gap is ``x ~ N(0, (r d)**2 + e_true)``.
- The registered variance is ``V = (r d)**2 W + e_reg``, with
  ``W ~ chi2(nu) / nu`` independent of x: B2 measures the Rao-Wu part with
  ``nu`` degrees of freedom, and the estimation part is a registered
  constant (addendum section 7).
- The bound rule passes the cell when ``|x| + t*(m, nu) sqrt(V) <= tau``,
  with ``t*(m, nu)`` the Student t quantile at ``1 - 0.05 / (2 m)``.
- Each gate seed's side-A gap, given x, is ``N(x, r**2)``. The seed split
  is a household split of the realized sample, so its spread is the
  household resampling variance whatever the design.
- As in protocol v2, ``a_j = E[1{bound passes} p(x)**j]`` and
  ``P(gate) = 5 prod a_4 - 4 prod a_5``.

The expectation over W is a composite Gauss-Legendre rule. W's range,
truncated where the bound rule can no longer pass, is cut into panels of
equal probability, and each panel's weights are scaled to its exact
probability, so the weights never sum above one. Each slab integral over
x is a Gauss-Legendre rule on [0, c], split at tau. The tests check both
against adaptive quadrature and against brute-force simulation.

With ``nu`` infinite, ``d = 1`` and the normal critical value, the model is
protocol v2's evaluation term for term
(``track_b_b0_1_addendum_power.cell_terms``), and the six level cells
reproduce the 0.952 that d781 cites.

The binding evaluation takes ``d`` at its 95th percentile (the design
rule's own statistic), protocol v2's binding variances, ``nu`` from the
record's design strata and the estimated standard error. The other
evaluations are sensitivities and decide nothing.

The verdict applies protocol v2's verdict rule (addendum section 16) to
the ruled surface. Its concept families are log quantiles and zero rate,
and section 5's four-cell guard applies. The record also reports whether
the six cells together reach 0.90, the ladder's outcome over every
pruning order, and each named option's power under tolerance
sensitivities. Every figure is nominal: B2's floor fixes the real
tolerances.
"""

from __future__ import annotations

import argparse
import functools
import hashlib
import itertools
import json
import math
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np
from scipy.special import roots_legendre
from scipy.stats import chi2, norm
from scipy.stats import t as student_t

sys.path.insert(0, str(Path(__file__).resolve().parent))

import track_b_b0_1_addendum_power as power  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PLANNING = ROOT / "docs" / "design" / "track_b_b0_1_planning_values.json"
OUTPUT = ROOT / "docs" / "design" / "track_b_b0_1_ruled_power.json"
SCHEMA = "track_b_b0_1_ruled_power.v2"

ALPHA = power.ALPHA
POWER_TARGET = power.POWER_TARGET
TAU = power.TAU_UNCAPPED
#: Quadrature: equal-probability panels over W, Gauss-Legendre nodes per
#: panel and per x interval, and the mass left out of each of W's tails.
W_PANELS = 40
W_PANEL_NODES = 16
X_NODES = 160
TAIL = 1e-14
#: Tolerance multipliers for the robustness rows. For the six cells, M6's
#: realized tolerance/sigma and the 2006 floor-to-bootstrap ratios put
#: B2's tolerance roughly 15% below to 8% above nominal.
TOLERANCE_SCALES = (0.85, 0.92, 1.00, 1.08)

#: d781 (a): the six level cells.
LEVEL_CELLS = (
    "earn_p50.older",
    "earn_p50.prime",
    "earn_p90.older",
    "earn_p90.prime",
    "earn_zero_rate.older",
    "earn_zero_rate.prime",
)
RULINGS = {
    "d765": "household half-samples for the refit arm",
    "d781": "option (a): gate the six level cells",
    "d782": "Rao-Wu design clusters for the registered standard error",
}
#: Fixed surfaces named in the decision the shortfall queues. Each is the
#: six level cells less the listed cells.
FIXED_OPTIONS = {
    "B": ("earn_p50.older",),
    "C1": ("earn_p50.older", "earn_p50.prime"),
    "C2": ("earn_p50.older", "earn_zero_rate.older"),
}


def t_star(m: int, nu: float | None) -> float:
    """Two-sided simultaneous 95% critical value over m cells.

    ``nu`` is the registered standard error's degrees of freedom; ``None``
    (or infinity) gives the normal value ``z*_m``.
    """
    if m < 1:
        raise ValueError("a gate needs at least one cell")
    if nu is None or math.isinf(nu):
        return power.z_star(m)
    if nu <= 0:
        raise ValueError("degrees of freedom must be positive")
    return float(student_t.ppf(1.0 - ALPHA / (2.0 * m), nu))


def design_degrees_of_freedom(design: Mapping[str, Any]) -> int:
    """sum over strata of (clusters - 1), from the record's design counts.

    A stratum with one cluster adds nothing. The record counts strata with
    three or more clusters but not their clusters, so their presence makes
    the count unknown here and raises.
    """
    if int(design["strata_with_three_or_more_clusters"]) != 0:
        raise ValueError("clusters per stratum above two are not recorded")
    total = (
        int(design["strata_with_one_cluster"])
        + int(design["strata_with_two_clusters"])
        + int(design["strata_with_three_or_more_clusters"])
    )
    if total != int(design["strata"]):
        raise ValueError("stratum counts do not add up")
    return int(design["strata_with_two_clusters"])


def _w_nodes(
    nu: float | None, upper: float = math.inf
) -> tuple[np.ndarray, np.ndarray]:
    """Nodes and weights for E[1{W < upper} g(W)], W ~ chi2(nu) / nu.

    W's range below ``upper``, less ``TAIL`` of mass at each end, is cut
    into ``W_PANELS`` panels of equal probability. Each panel takes
    ``W_PANEL_NODES`` Gauss-Legendre nodes weighted by W's density, scaled
    to the panel's exact probability, so the weights sum to the truncated
    mass and never above one. The bound rule fails for every W at or above
    ``upper``, so stopping there keeps the integrand's kink at a panel
    edge. With ``nu`` None (a known standard error) W is 1.
    """
    if nu is None or math.isinf(nu):
        if upper > 1.0:
            return np.ones(1), np.ones(1)
        return np.ones(0), np.ones(0)
    dist = chi2(nu, scale=1.0 / nu)
    u_hi = 1.0 - TAIL
    if math.isfinite(upper):
        u_hi = min(u_hi, float(dist.cdf(upper))) if upper > 0 else 0.0
    if u_hi <= TAIL:
        return np.ones(0), np.ones(0)
    probabilities = np.linspace(TAIL, u_hi, W_PANELS + 1)
    edges = dist.ppf(probabilities)
    masses = np.diff(probabilities)
    u, w = roots_legendre(W_PANEL_NODES)
    nodes, weights = [], []
    for lo, hi, mass in zip(edges[:-1], edges[1:], masses, strict=True):
        x = lo + (hi - lo) * (u + 1.0) / 2.0
        raw = (hi - lo) / 2.0 * w * dist.pdf(x)
        nodes.append(x)
        weights.append(raw * (mass / raw.sum()))
    return np.concatenate(nodes), np.concatenate(weights)


@functools.cache
def _x_nodes() -> tuple[np.ndarray, np.ndarray]:
    """Gauss-Legendre nodes and weights on [0, 1]."""
    u, w = roots_legendre(X_NODES)
    return (u + 1.0) / 2.0, w / 2.0


def slab_moments(
    c: np.ndarray, s: float, tau: float, r_seed: float
) -> tuple[np.ndarray, np.ndarray]:
    """E[1{|x| <= c} p(x)**j] for j = 4, 5 and x ~ N(0, s**2), per c.

    ``p(x)`` is one seed's pass probability given x, which falls steeply
    near x = tau. The integrand is even in x, so each moment is twice the
    integral over [0, c]. That interval is split at tau, and each piece
    takes Gauss-Legendre nodes. Entries with c <= 0 are zero.
    """
    c = np.maximum(np.asarray(c, dtype=float), 0.0)
    u, w = _x_nodes()
    j4 = np.zeros_like(c)
    j5 = np.zeros_like(c)
    split = np.minimum(c, tau)
    for lo, hi in ((np.zeros_like(c), split), (split, c)):
        width = hi - lo
        x = lo[:, None] + width[:, None] * u[None, :]
        if r_seed > 0:
            p = norm.cdf((tau - x) / r_seed) - norm.cdf((-tau - x) / r_seed)
        else:
            p = (np.abs(x) <= tau).astype(float)
        base = 2.0 * width[:, None] * w[None, :] * norm.pdf(x, scale=s)
        j4 += (base * p**4).sum(axis=1)
        j5 += (base * p**5).sum(axis=1)
    return j4, j5


@functools.cache
def ruled_cell_terms(
    tau: float,
    r_seed: float,
    sampling_variance: float,
    e_true: float,
    e_reg: float,
    m: int,
    nu: float | None,
    critical: str = "t",
    random_se: bool = True,
) -> power.CellTerms:
    """One cell's joint pass probabilities on the ruled model (memoised).

    ``sampling_variance`` is ``(r d)**2``; ``e_true`` and ``e_reg`` the
    estimation parts of the gap's variance and of the registered variance,
    all over se_up**2. ``critical`` is ``"t"`` (``t*(m, nu)``) or ``"z"``.
    With ``random_se`` false, the registered variance is its expectation.
    """
    if (
        tau <= 0
        or r_seed < 0
        or sampling_variance < 0
        or e_true < 0
        or e_reg < 0
    ):
        raise ValueError("tau must be positive and variances non-negative")
    s = math.sqrt(sampling_variance + e_true)
    if s == 0:
        raise ValueError("the gap has zero variance")
    if critical == "t":
        crit = t_star(m, nu)
    elif critical == "z":
        crit = power.z_star(m)
    else:
        raise ValueError(f"unknown critical value {critical!r}")
    # The bound rule can pass only while V < (tau / crit)**2.
    room = (tau / crit) ** 2 - e_reg
    if room <= 0:
        upper = -math.inf
    elif sampling_variance == 0:
        upper = math.inf
    else:
        upper = room / sampling_variance
    nodes, weights = _w_nodes(nu if random_se else None, upper)
    c = tau - crit * np.sqrt(sampling_variance * nodes + e_reg)
    a4, a5 = slab_moments(c, s, tau, r_seed)
    bound = 2.0 * norm.cdf(np.maximum(c, 0.0) / s) - 1.0
    wide = tau + 12.0 * max(r_seed, s)
    b4, b5 = slab_moments(np.array([wide]), s, tau, r_seed)
    return power.CellTerms(
        bound=float(weights @ bound),
        a4=float(weights @ a4),
        a5=float(weights @ a5),
        b4=float(b4[0]),
        b5=float(b5[0]),
    )


@dataclass(frozen=True)
class RuledCell:
    name: str
    r: float
    d: float
    e_true: float
    e_reg: float
    tau: float = TAU


@dataclass(frozen=True)
class Evaluation:
    """How the ruled model is evaluated."""

    design: str = "d95"  # "d95", "point" or "none" (d = 1)
    variance: str = "gate"  # "gate" (protocol v2 binding) or "point"
    critical: str = "t"  # "t" or "z"
    random_se: bool = True
    seeds: str = "household"  # "household" (r) or "design" (r d)


BINDING = Evaluation()
EVALUATIONS = {
    "binding": BINDING,
    "registered_se_known": replace(BINDING, random_se=False),
    "design_ratio_point": replace(BINDING, design="point"),
    "point_variances": replace(BINDING, variance="point"),
    "normal_critical_value": replace(BINDING, critical="z", random_se=False),
    "seeds_take_the_design_ratio": replace(BINDING, seeds="design"),
    "most_lenient": Evaluation("point", "point", "z", False, "household"),
    "household_as_measured": Evaluation(
        "none", "gate", "z", False, "household"
    ),
}


def ruled_cells(
    planning: Mapping[str, Any],
    how: Evaluation,
    names: Sequence[str] = LEVEL_CELLS,
) -> dict[str, RuledCell]:
    """The ruled cells on one evaluation's design and variance basis.

    ``gate``: both estimation parts are ``s2_gate - r**2`` (protocol v2's
    binding evaluation). ``point``: the gap's is ``s2 - r**2`` and the
    registered one ``e_B2`` (protocol v2's point-variance sensitivity).
    """
    out: dict[str, RuledCell] = {}
    for name in names:
        record = planning["cells"][name]
        if not record.get("defined"):
            raise ValueError(f"{name} has no planning values")
        r = float(record["shared_anchor_ratio"]["r"])
        ratio = record["design_ratio"]
        d = {
            "d95": float(ratio["ci"][1]),
            "point": float(ratio["d"]),
            "none": 1.0,
        }[how.design]
        gap = record["gap_variance"]
        if how.variance == "gate":
            e_true = e_reg = max(0.0, float(gap["s2_gate"]) - r**2)
        elif how.variance == "point":
            e_true = max(0.0, float(gap["s2"]) - r**2)
            e_reg = float(record["estimation_variance"]["e_b2"])
        else:
            raise ValueError(f"unknown variance basis {how.variance!r}")
        out[name] = RuledCell(name, r, d, e_true, e_reg)
    return out


def surface_power(
    cells: Sequence[RuledCell], nu: float | None, how: Evaluation
) -> dict[str, float]:
    m = len(cells)
    return power.gate_probabilities(
        [
            ruled_cell_terms(
                c.tau,
                c.r * c.d if how.seeds == "design" else c.r,
                (c.r * c.d) ** 2,
                c.e_true,
                c.e_reg,
                m,
                nu,
                how.critical,
                how.random_se,
            )
            for c in cells
        ]
    )


def _with_tau(cells: Sequence[RuledCell], tau: float) -> list[RuledCell]:
    return [replace(c, tau=tau) for c in cells]


def _subsets(names: Sequence[str], size: int) -> list[tuple[str, ...]]:
    """Subsets of ``size`` keeping a cell of every concept family."""
    families = {power.concept(n) for n in names}
    return [
        subset
        for subset in itertools.combinations(sorted(names), size)
        if {power.concept(n) for n in subset} == families
    ]


def fixed_surfaces(
    cells: Mapping[str, RuledCell],
    nu: float | None,
    how: Evaluation,
    lenient: Mapping[str, RuledCell],
) -> dict[str, Any]:
    """Every surface of the six with at least four cells and both
    families, with its binding power and its most lenient power."""
    out: dict[str, Any] = {}
    for size in range(len(cells), power.MIN_GATED_CELLS - 1, -1):
        rows = []
        for subset in _subsets(list(cells), size):
            rows.append(
                {
                    "cells": list(subset),
                    "dropped": sorted(set(cells) - set(subset)),
                    "p_gate": surface_power(
                        [cells[n] for n in subset], nu, how
                    )["p_gate"],
                    "p_gate_most_lenient": surface_power(
                        [lenient[n] for n in subset],
                        nu,
                        EVALUATIONS["most_lenient"],
                    )["p_gate"],
                }
            )
        rows.sort(key=lambda row: (-row["p_gate"], row["cells"]))
        out[str(size)] = {
            "n_surfaces": len(rows),
            "n_reaching_target": sum(
                r["p_gate"] >= POWER_TARGET for r in rows
            ),
            "surfaces": rows,
        }
    return out


def ladder_outcomes(
    cells: Mapping[str, RuledCell], nu: float | None, how: Evaluation
) -> dict[str, Any]:
    """Section 5's ladder inside the six, over every pruning order.

    B2's floor fixes the order (descending tolerance/sigma), and it is not
    known before the floor runs, so every one of the 720 orders is run.
    The count of orders says how many orders clear, not how likely the
    floor is to produce one: nothing makes the orders equally likely.
    The ladder prunes in order, never a family's last cell, and stops at
    the first power at or above 0.90; it fails if it stops below 0.90 or
    with fewer than four cells.
    """
    names = sorted(cells)
    cache: dict[tuple[str, ...], float] = {}

    def p(subset: list[str]) -> float:
        key = tuple(sorted(subset))
        if key not in cache:
            cache[key] = surface_power([cells[n] for n in key], nu, how)[
                "p_gate"
            ]
        return cache[key]

    ends: dict[tuple[str, ...], int] = {}
    cleared = 0
    for order in itertools.permutations(names):
        retained = list(names)
        value = p(retained)
        for cell in order:
            if value >= POWER_TARGET:
                break
            family = power.concept(cell)
            if sum(power.concept(c) == family for c in retained) <= 1:
                continue
            retained.remove(cell)
            value = p(retained)
        ok = value >= POWER_TARGET and len(retained) >= power.MIN_GATED_CELLS
        cleared += ok
        key = tuple(sorted(retained))
        ends[key] = ends.get(key, 0) + 1
    return {
        "orders": math.factorial(len(names)),
        "orders_clearing": cleared,
        "end_surfaces": [
            {
                "cells": list(key),
                "orders": count,
                "p_gate": p(list(key)),
                "clears": p(list(key)) >= POWER_TARGET
                and len(key) >= power.MIN_GATED_CELLS,
            }
            for key, count in sorted(
                ends.items(), key=lambda item: (-item[1], item[0])
            )
        ],
    }


def tolerance_reaching(
    cells: Sequence[RuledCell],
    nu: float | None,
    how: Evaluation,
    target: float = POWER_TARGET,
    lo: float = 3.0,
    hi: float = 10.0,
) -> dict[str, float]:
    """The smallest uncapped k whose tolerance lifts ``cells`` to target."""

    def at(k: float) -> float:
        return surface_power(
            _with_tau(cells, power.tolerance_for_k(k)), nu, how
        )["p_gate"]

    if at(hi) < target:
        return {"k": math.inf, "width_over_k3": math.inf}
    if at(lo) >= target:
        return {
            "k": lo,
            "tau": power.tolerance_for_k(lo),
            "width_over_k3": power.tolerance_for_k(lo) / TAU,
            "p_gate": at(lo),
        }
    for _ in range(40):
        mid = (lo + hi) / 2
        if at(mid) >= target:
            hi = mid
        else:
            lo = mid
    return {
        "k": hi,
        "tau": power.tolerance_for_k(hi),
        "width_over_k3": power.tolerance_for_k(hi) / TAU,
        "p_gate": at(hi),
    }


def option_record(
    cells: Sequence[RuledCell],
    lenient: Sequence[RuledCell],
    nu: float | None,
    tau: float = TAU,
) -> dict[str, Any]:
    """One fixed option: its binding and most lenient power at ``tau``,
    and its binding power at each tolerance multiplier."""
    return {
        "cells": [c.name for c in cells],
        "tau": tau,
        "width_over_k3": tau / TAU,
        "p_gate": surface_power(_with_tau(cells, tau), nu, BINDING)["p_gate"],
        "p_gate_most_lenient": surface_power(
            _with_tau(lenient, tau), nu, EVALUATIONS["most_lenient"]
        )["p_gate"],
        "p_gate_by_tolerance_scale": {
            f"{scale:.2f}": surface_power(
                _with_tau(cells, tau * scale), nu, BINDING
            )["p_gate"]
            for scale in TOLERANCE_SCALES
        },
    }


def protocol_verdict(
    cells: Mapping[str, RuledCell], nu: float | None, how: Evaluation
) -> dict[str, Any]:
    """Protocol v2's verdict rule (section 16) on the ruled surface.

    - ``weak_power_or_vacuity``: no four of the ruled cells reach 0.90;
    - ``family_floor_blocks``: four cells reach 0.90, but no surface of
      four or more that keeps every family of the ruled surface does;
    - ``feasible_subject_to_floor``: such a surface reaches 0.90, and
      B2's floor builder decides with its own floor and ladder.

    Surfaces below four cells are left out because section 5's guard
    refuses them.
    """
    names = sorted(cells)
    best_four = max(
        (
            surface_power([cells[n] for n in subset], nu, how)["p_gate"],
            list(subset),
        )
        for subset in itertools.combinations(names, power.MIN_GATED_CELLS)
    )
    best_family = max(
        (
            surface_power([cells[n] for n in subset], nu, how)["p_gate"],
            list(subset),
        )
        for size in range(power.MIN_GATED_CELLS, len(names) + 1)
        for subset in _subsets(names, size)
    )
    if best_four[0] < POWER_TARGET:
        verdict = "weak_power_or_vacuity"
    elif best_family[0] < POWER_TARGET:
        verdict = "family_floor_blocks"
    else:
        verdict = "feasible_subject_to_floor"
    return {
        "verdict": verdict,
        "families": sorted({power.concept(n) for n in names}),
        "best_four_cell_surface": {
            "cells": best_four[1],
            "p_gate": best_four[0],
        },
        "best_family_surface": {
            "cells": best_family[1],
            "p_gate": best_family[0],
        },
    }


def ruled_record(planning: Mapping[str, Any]) -> dict[str, Any]:
    nu = design_degrees_of_freedom(planning["counts"]["design"])
    m = len(LEVEL_CELLS)
    bases = {
        name: ruled_cells(planning, how) for name, how in EVALUATIONS.items()
    }
    six = {
        name: surface_power(list(bases[name].values()), nu, how)
        for name, how in EVALUATIONS.items()
    }
    binding_cells = bases["binding"]
    lenient_cells = bases["most_lenient"]
    previous = power.design_inflated(
        planning, power.planning_cells(planning, "binding")
    )
    tolerance = {
        "binding": tolerance_reaching(
            list(binding_cells.values()), nu, BINDING
        ),
        "most_lenient": tolerance_reaching(
            list(lenient_cells.values()), nu, EVALUATIONS["most_lenient"]
        ),
    }
    #: The binding k rounded up to two decimals, the form a registration
    #: would state.
    k_option = math.ceil(tolerance["binding"]["k"] * 100) / 100
    options: dict[str, Any] = {
        "six": option_record(
            list(binding_cells.values()), list(lenient_cells.values()), nu
        ),
    }
    for label, dropped in FIXED_OPTIONS.items():
        kept = [n for n in LEVEL_CELLS if n not in dropped]
        options[label] = option_record(
            [binding_cells[n] for n in kept],
            [lenient_cells[n] for n in kept],
            nu,
        )
        options[label]["dropped"] = list(dropped)
    options["D"] = option_record(
        list(binding_cells.values()),
        list(lenient_cells.values()),
        nu,
        tau=power.tolerance_for_k(k_option),
    )
    options["D"]["k"] = k_option
    correlation = planning["arm_f_gap_correlation"]
    matrix = correlation["matrix"]
    index = {name: i for i, name in enumerate(correlation["cells"])}
    verdict = protocol_verdict(binding_cells, nu, BINDING)
    return {
        "schema": SCHEMA,
        "rulings": RULINGS,
        "decides_nothing_by_itself": True,
        "constants": {
            "alpha": ALPHA,
            "power_target": POWER_TARGET,
            "tau_uncapped_se_up_units": TAU,
            "gated_cells": m,
            "design_degrees_of_freedom": nu,
            "t_star": t_star(m, nu),
            "z_star": power.z_star(m),
            "w_panels": W_PANELS,
            "w_panel_nodes": W_PANEL_NODES,
            "x_quadrature_nodes": X_NODES,
            "tolerance_scales": list(TOLERANCE_SCALES),
        },
        "evaluations": {
            name: {
                "design": how.design,
                "variance": how.variance,
                "critical": how.critical,
                "random_se": how.random_se,
                "seeds": how.seeds,
                "binding": name == "binding",
            }
            for name, how in EVALUATIONS.items()
        },
        "per_cell": {
            name: {
                "r": cell.r,
                "d_95th": cell.d,
                "d_point": bases["design_ratio_point"][name].d,
                "e_gate": cell.e_true,
                "e_point": bases["point_variances"][name].e_true,
                "e_b2": bases["point_variances"][name].e_reg,
                "gap_variance": (cell.r * cell.d) ** 2 + cell.e_true,
                "bound_pass_at_m": ruled_cell_terms(
                    cell.tau,
                    cell.r,
                    (cell.r * cell.d) ** 2,
                    cell.e_true,
                    cell.e_reg,
                    m,
                    nu,
                ).bound,
            }
            for name, cell in binding_cells.items()
        },
        "six_level_cells": six,
        "cross_checks": {
            "household_six_protocol_v2": power.surface_power(
                [
                    power.planning_cells(planning, "binding")[n]
                    for n in LEVEL_CELLS
                ]
            )["p_gate"],
            "addendum_illustration_six": power.surface_power(
                [previous[n] for n in LEVEL_CELLS]
            )["p_gate"],
        },
        "fixed_surfaces": fixed_surfaces(
            binding_cells, nu, BINDING, lenient_cells
        ),
        "ladder_inside_the_six": ladder_outcomes(binding_cells, nu, BINDING),
        "ladder_inside_the_six_most_lenient": ladder_outcomes(
            lenient_cells, nu, EVALUATIONS["most_lenient"]
        ),
        "tolerance_for_target": tolerance,
        "options": options,
        "level_cell_gap_correlation_max": max(
            abs(matrix[index[a]][index[b]])
            for a, b in itertools.combinations(LEVEL_CELLS, 2)
        ),
        "verdict": {
            "protocol": verdict,
            "six_reach_target": six["binding"]["p_gate"] >= POWER_TARGET,
            "evaluations_of_the_six_reaching_target": sorted(
                name
                for name, value in six.items()
                if value["p_gate"] >= POWER_TARGET
            ),
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.parse_args(argv)
    planning = json.loads(PLANNING.read_text(encoding="utf-8"))
    record = ruled_record(planning)
    record["planning_values_sha256"] = hashlib.sha256(
        PLANNING.read_bytes()
    ).hexdigest()
    if OUTPUT.exists():
        raise FileExistsError(f"{OUTPUT} exists")
    with OUTPUT.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=1, sort_keys=True)
        stream.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
