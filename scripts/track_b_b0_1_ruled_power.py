#!/usr/bin/env python3
"""Track B B0.1 addendum: B2's gate power on the configuration Max ruled.

On 2026-10-11 Max ruled the three questions the addendum queued:

- d781 (a): B2 gates only the six level cells, ``earn_p50``, ``earn_p90``
  and ``earn_zero_rate`` by cohort. The other ten cells are scored and
  published report-only.
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
- ``e = s2_gate - r**2`` is the estimation part of protocol v2's binding
  gating variance (the planning record's ``s2_gate``, the 97.5% upper
  limit of ``r**2 + e``). d765 leaves it as measured.
- The full-support gap is ``x ~ N(0, (r d)**2 + e)``.
- The registered variance is ``V = (r d)**2 W + e``, with
  ``W ~ chi2(nu) / nu`` independent of x: B2 measures the Rao-Wu part with
  ``nu`` degrees of freedom, and the estimation part is a registered
  constant (addendum section 7).
- The bound rule passes the cell when ``|x| + t*(m, nu) sqrt(V) <= tau``,
  with ``t*(m, nu)`` the Student t quantile at ``1 - 0.05 / (2 m)``.
- Each gate seed's side-A gap, given x, is ``N(x, r**2)``. The seed split
  is a household split of the realized sample, so its spread is the
  household resampling variance whatever the design.
- As in protocol v2, ``a_j = E[1{bound passes} p(x)**j]`` and
  ``P(gate) = 5 prod a_4 - 4 prod a_5``. The expectation over W uses
  Gauss-Legendre nodes over W's range weighted by its density, and each
  slab integral over x uses Gauss-Legendre nodes on [0, c]; the tests
  check both against adaptive quadrature and brute-force simulation.

With ``nu`` infinite, ``d = 1`` and the normal critical value, the model is
protocol v2's binding evaluation term for term
(``track_b_b0_1_addendum_power.cell_terms``), and the six level cells
reproduce the 0.952 that d781 cites.

The binding evaluation is the one above with ``d`` at its 95th percentile
(the design rule's own limit statistic) and ``nu`` counted from the
record's design strata. The sensitivities report the most lenient basis
beside it. Every figure here decides nothing by itself: the addendum's
verdict rule and Max's rulings do.
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
SCHEMA = "track_b_b0_1_ruled_power.v1"

ALPHA = power.ALPHA
POWER_TARGET = power.POWER_TARGET
TAU = power.TAU_UNCAPPED
#: Gauss-Legendre nodes over W and over the gap x, and the mass left out
#: of each of W's tails.
W_NODES = 200
X_NODES = 160
TAIL = 1e-14

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

    Gauss-Legendre over W's range below ``upper``, each weight times W's
    density; each tail beyond ``TAIL`` of mass is left out. The bound
    rule fails for every W at or above ``upper``, so the integrand is zero
    there; stopping at ``upper`` keeps its kink out of the nodes' range.
    (Nodes in W's quantile scale converge slowly, because the quantile
    function is singular at 1.)
    """
    if nu is None or math.isinf(nu):
        return (
            (np.ones(1), np.ones(1))
            if upper > 1.0
            else (
                np.ones(0),
                np.ones(0),
            )
        )
    dist = chi2(nu, scale=1.0 / nu)
    lo, hi = dist.ppf(TAIL), min(dist.isf(TAIL), upper)
    if hi <= lo:
        return np.ones(0), np.ones(0)
    u, w = roots_legendre(W_NODES)
    nodes = lo + (hi - lo) * (u + 1.0) / 2.0
    return nodes, (hi - lo) / 2.0 * w * dist.pdf(nodes)


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
    e: float,
    m: int,
    nu: float | None,
    critical: str = "t",
    random_se: bool = True,
) -> power.CellTerms:
    """One cell's joint pass probabilities on the ruled model (memoised).

    ``sampling_variance`` is ``(r d)**2``; ``e`` the estimation variance,
    both over se_up**2. ``critical`` is ``"t"`` (``t*(m, nu)``) or ``"z"``.
    With ``random_se`` false, the registered variance is its expectation.
    """
    if tau <= 0 or r_seed < 0 or sampling_variance < 0 or e < 0:
        raise ValueError("tau must be positive and variances non-negative")
    s = math.sqrt(sampling_variance + e)
    if s == 0:
        raise ValueError("the gap has zero variance")
    if critical == "t":
        crit = t_star(m, nu)
    elif critical == "z":
        crit = power.z_star(m)
    else:
        raise ValueError(f"unknown critical value {critical!r}")
    # The bound rule can pass only while V < (tau / crit)**2.
    room = (tau / crit) ** 2 - e
    upper = math.inf if sampling_variance == 0 else room / sampling_variance
    if room <= 0:
        upper = -math.inf
    nodes, weights = _w_nodes(nu if random_se else None, upper)
    c = tau - crit * np.sqrt(sampling_variance * nodes + e)
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
    e: float
    tau: float = TAU


@dataclass(frozen=True)
class Evaluation:
    """How the ruled model is evaluated."""

    design: str = "d95"  # "d95", "point" or "none" (d = 1)
    critical: str = "t"  # "t" or "z"
    random_se: bool = True
    seeds: str = "household"  # "household" (r) or "design" (r d)


BINDING = Evaluation()
EVALUATIONS = {
    "binding": BINDING,
    "registered_se_known": replace(BINDING, random_se=False),
    "design_ratio_point": replace(BINDING, design="point"),
    "normal_critical_value": replace(BINDING, critical="z", random_se=False),
    "seeds_take_the_design_ratio": replace(BINDING, seeds="design"),
    "most_lenient": Evaluation("point", "z", False, "household"),
    "household_as_measured": Evaluation("none", "z", False, "household"),
}


def ruled_cells(
    planning: Mapping[str, Any],
    design: str,
    names: Sequence[str] = LEVEL_CELLS,
) -> dict[str, RuledCell]:
    """The ruled cells on one design basis.

    ``e`` is protocol v2's binding estimation part, ``s2_gate - r**2``.
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
        }[design]
        e = max(0.0, float(record["gap_variance"]["s2_gate"]) - r**2)
        out[name] = RuledCell(name, r, d, e)
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
                c.e,
                m,
                nu,
                how.critical,
                how.random_se,
            )
            for c in cells
        ]
    )


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
        ends[tuple(sorted(retained))] = (
            ends.get(tuple(sorted(retained)), 0) + 1
        )
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
        tau = power.tolerance_for_k(k)
        return surface_power([replace(c, tau=tau) for c in cells], nu, how)[
            "p_gate"
        ]

    if at(hi) < target:
        return {"k": math.inf, "width_over_k3": math.inf}
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


def ruled_record(planning: Mapping[str, Any]) -> dict[str, Any]:
    nu = design_degrees_of_freedom(planning["counts"]["design"])
    m = len(LEVEL_CELLS)
    bases = {
        design: ruled_cells(planning, design)
        for design in ("d95", "point", "none")
    }
    six = {
        name: surface_power(list(bases[how.design].values()), nu, how)
        for name, how in EVALUATIONS.items()
    }
    binding_cells = bases[BINDING.design]
    previous = power.design_inflated(
        planning, power.planning_cells(planning, "binding")
    )
    reaches = six["binding"]["p_gate"] >= POWER_TARGET
    tolerance = {
        "binding": tolerance_reaching(
            list(binding_cells.values()), nu, BINDING
        ),
        "most_lenient": tolerance_reaching(
            list(bases["point"].values()), nu, EVALUATIONS["most_lenient"]
        ),
    }
    #: The binding k rounded up to two decimals, the form a registration
    #: would state.
    k_option = math.ceil(tolerance["binding"]["k"] * 100) / 100

    def at_k(cells: Mapping[str, RuledCell], how: Evaluation) -> float:
        tau = power.tolerance_for_k(k_option)
        return surface_power(
            [replace(c, tau=tau) for c in cells.values()], nu, how
        )["p_gate"]

    correlation = planning["arm_f_gap_correlation"]
    matrix = correlation["matrix"]
    index = {name: i for i, name in enumerate(correlation["cells"])}
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
            "w_quadrature_nodes": W_NODES,
            "x_quadrature_nodes": X_NODES,
        },
        "evaluations": {
            name: {
                "design": how.design,
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
                "d_point": bases["point"][name].d,
                "e": cell.e,
                "gap_variance": (cell.r * cell.d) ** 2 + cell.e,
                "bound_pass_at_m": ruled_cell_terms(
                    cell.tau, cell.r, (cell.r * cell.d) ** 2, cell.e, m, nu
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
            binding_cells, nu, BINDING, bases["point"]
        ),
        "ladder_inside_the_six": ladder_outcomes(binding_cells, nu, BINDING),
        "ladder_inside_the_six_most_lenient": ladder_outcomes(
            bases["point"], nu, EVALUATIONS["most_lenient"]
        ),
        "tolerance_for_target": tolerance,
        "tolerance_option": {
            "k": k_option,
            "width_over_k3": power.tolerance_for_k(k_option) / TAU,
            "p_gate": at_k(binding_cells, BINDING),
            "p_gate_most_lenient": at_k(
                bases["point"], EVALUATIONS["most_lenient"]
            ),
        },
        "level_cell_gap_correlation_max": max(
            abs(matrix[index[a]][index[b]])
            for a, b in itertools.combinations(LEVEL_CELLS, 2)
        ),
        "verdict": {
            "ruled_six_reach_target": reaches,
            "every_evaluation_of_the_six_below_target": all(
                value["p_gate"] < POWER_TARGET
                for key, value in six.items()
                if key != "household_as_measured"
            ),
            "b2_stops": not reaches,
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
