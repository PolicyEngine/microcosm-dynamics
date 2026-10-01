#!/usr/bin/env python3
"""Track B B0.1 addendum: B2's named power procedure on the ruled basis.

Max's ruling d693 set B2's scoring rule to Q2 option (d): §5.2's
simultaneous bound rule on full-support scoring at the k = 3 floor
tolerance, with M6's seed conjunction (at least 4 of 5 side-A seeds) kept
as a second condition, and power computed for the whole gate. This module
is that power procedure. It reads no data: its inputs are tolerances in
standard-error units and the planning values that protocol v2 derives
(``docs/design/track_b_b0_1_planning_values.json``).

The operating characteristic (protocol v2, "Named power procedure").
Units are each cell's upper-bound full-support gap standard error,
``se_up = sigma * sqrt(1 + 1/K) / 2`` (audit §11), with ``sigma`` the
cell's household-split floor sigma. A faithful candidate's gaps are
modelled per cell as:

- full support: ``x ~ N(0, r**2 + e_true)``, where ``r`` is the
  shared-anchor ratio and ``e_true`` the estimation variance over
  ``se_up**2``;
- side A of gate seed s, given x: ``N(x, r**2)``, independent across the
  five seeds. A random half has twice the full sample's sampling variance,
  two independent halves share a quarter of the units, and the estimation
  error is common to every seed and to the full support.

The bound rule passes cell c when ``|x| + z*_m sqrt(r**2 + e_reg) <= tau``
(``e_reg`` is the registered estimation-variance bound; ``z*_m`` the
two-sided Bonferroni value over the m gated cells). Seed s passes cell c
when its side-A gap lies within ``+-tau``. With
``a_j = E[1{bound passes} p(x)**j]`` and ``p(x)`` one seed's conditional
pass probability, and cells independent,

    P(gate passes) = 5 prod_c a_c,4 - 4 prod_c a_c,5,

the probability that every cell passes the bound rule and at least four of
five seeds pass every cell. The ``a_j`` are one-dimensional integrals,
evaluated by adaptive quadrature. Treating cells as independent understates
the probability that every cell passes the bound rule (the event is an
intersection of symmetric slabs, so the Gaussian correlation inequality
applies) and, in every case tested, the whole gate's.

The binding evaluation (protocol v2) uses each cell's arm-F point estimate
of r, and e_true = e_reg = e_B2, the transported 95% upper limit of the
estimation variance. Two other bases are reported as sensitivities and
decide nothing: the 95th percentile of r with the same e, and M6's own
seed convention (``m6_cells.oc_4of5``) in place of the conditional model.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scipy import integrate
from scipy.stats import norm

sys.path.insert(0, str(Path(__file__).resolve().parent))

import track_b_b0_1_counts as frozen  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PLANNING = ROOT / "docs" / "design" / "track_b_b0_1_planning_values.json"
OUTPUT = ROOT / "docs" / "design" / "track_b_b0_1_addendum_power.json"
SCHEMA = "track_b_b0_1_addendum_power.v1"

K = frozen.M6_DRAWS
ALPHA = frozen.ALPHA
POWER_TARGET = frozen.POWER_TARGET
N_SEEDS = 5
SEEDS_REQUIRED = 4
MIN_GATED_CELLS = 4
#: Tolerance / half-split sigma of the uncapped k = 3 floor rule.
FLOOR_RATIO = frozen.half_normal_floor_ratio(frozen.M6_K)
#: se_up / sigma.
SE_UP_OVER_SIGMA = math.sqrt(1.0 + 1.0 / K) / 2.0
#: Uncapped k = 3 tolerance in se_up units.
TAU_UNCAPPED = FLOOR_RATIO / SE_UP_OVER_SIGMA

#: M6's concept families (``scripts/build_m6_holdout_floors_v2.py:118``).
CONCEPT_FAMILY = {
    "earn_p10": "log_quantiles",
    "earn_p50": "log_quantiles",
    "earn_p90": "log_quantiles",
    "earn_dlog_sd": "dispersion",
    "earn_mob_h1_diag": "mobility",
    "earn_mob_h2_diag": "mobility",
    "earn_zero_rate": "zero_rate",
    "earn_autocorr_lag1": "autocorrelation",
    "earn_autocorr_lag2": "autocorrelation",
    "earn_dlog_mean": "change_mean",
}
#: The 16 gateable cells (``m6_cells.earnings_cells``; audit §9.1).
CONCEPT_FAMILY_CELLS = (
    *(
        f"earn_{tag}.{cohort}"
        for tag in ("p10", "p50", "p90", "zero_rate", "dlog_sd", "dlog_mean")
        for cohort in ("prime", "older")
    ),
    "earn_mob_h1_diag",
    "earn_mob_h2_diag",
    "earn_autocorr_lag1",
    "earn_autocorr_lag2",
)
#: M6 v3's retained six (``gates.yaml:5600-5606``).
M6_RETAINED = (
    "earn_autocorr_lag2",
    "earn_dlog_mean.prime",
    "earn_dlog_sd.older",
    "earn_mob_h1_diag",
    "earn_p10.prime",
    "earn_zero_rate.older",
)


def concept(cell: str) -> str:
    return CONCEPT_FAMILY[cell.split(".")[0]]


def z_star(m: int) -> float:
    """Two-sided simultaneous 95% critical value over m cells."""
    if m < 1:
        raise ValueError("a gate needs at least one cell")
    return float(norm.ppf(1.0 - ALPHA / (2.0 * m)))


@dataclass(frozen=True)
class CellTerms:
    """One cell's contribution at one family size."""

    bound: float  # P(bound rule passes)
    a4: float  # P(bound passes and 4 given seeds pass)
    a5: float  # P(bound passes and all 5 seeds pass)
    b4: float  # P(4 given seeds pass)
    b5: float  # P(all 5 seeds pass)


def _seed_pass(x: float, tau: float, r: float) -> float:
    if r <= 0:
        return 1.0 if abs(x) <= tau else 0.0
    return float(norm.cdf((tau - x) / r) - norm.cdf((-tau - x) / r))


def cell_terms(
    tau: float, r: float, e_true: float, e_reg: float, m: int
) -> CellTerms:
    """Quadrature for one cell's joint pass probabilities."""
    if tau <= 0 or r < 0 or e_true < 0 or e_reg < 0:
        raise ValueError("tau must be positive and variances non-negative")
    s = math.sqrt(r**2 + e_true)
    if s == 0:
        raise ValueError("the gap has zero variance")
    c = tau - z_star(m) * math.sqrt(r**2 + e_reg)
    density = norm(0.0, s).pdf

    def moment(j: int, lower: float, upper: float) -> float:
        if upper <= lower:
            return 0.0
        value, _ = integrate.quad(
            lambda x: _seed_pass(x, tau, r) ** j * density(x),
            lower,
            upper,
            epsabs=1e-13,
            epsrel=1e-11,
            limit=400,
        )
        return float(value)

    wide = tau + 12.0 * max(r, s)
    bound = float(2.0 * norm.cdf(c / s) - 1.0) if c > 0 else 0.0
    return CellTerms(
        bound=bound,
        a4=moment(4, -c, c) if c > 0 else 0.0,
        a5=moment(5, -c, c) if c > 0 else 0.0,
        b4=moment(4, -wide, wide),
        b5=moment(5, -wide, wide),
    )


def gate_probabilities(terms: Sequence[CellTerms]) -> dict[str, float]:
    """Gate-level probabilities for cells assumed independent."""
    a4 = math.prod(term.a4 for term in terms)
    a5 = math.prod(term.a5 for term in terms)
    b4 = math.prod(term.b4 for term in terms)
    b5 = math.prod(term.b5 for term in terms)
    bound_only = math.prod(term.bound for term in terms)
    joint = N_SEEDS * a4 - (N_SEEDS - 1) * a5
    seeds_only = N_SEEDS * b4 - (N_SEEDS - 1) * b5
    return {
        "p_gate": joint,
        "p_bound_rule_only": bound_only,
        "p_seed_conjunction_only": seeds_only,
        "p_seeds_fail_given_bound_passes": (
            None if bound_only <= 0 else 1.0 - joint / bound_only
        ),
    }


def m6_convention_gate(n_cells: int, ratio: float = FLOOR_RATIO) -> float:
    """M6's own operating characteristic (``m6_cells.oc_4of5``)."""
    p_cell = 2.0 * norm.cdf(ratio) - 1.0
    p_seed = p_cell**n_cells
    return float(p_seed**5 + 5 * p_seed**4 * (1.0 - p_seed))


@dataclass(frozen=True)
class PlanningCell:
    name: str
    r: float
    e_true: float
    e_reg: float
    tau: float = TAU_UNCAPPED
    tol_over_sigma: float = FLOOR_RATIO
    capped: bool = False


def surface_power(cells: Sequence[PlanningCell]) -> dict[str, float]:
    m = len(cells)
    return gate_probabilities(
        [cell_terms(c.tau, c.r, c.e_true, c.e_reg, m) for c in cells]
    )


def ladder(
    cells: Sequence[PlanningCell], target: float = POWER_TARGET
) -> dict[str, Any]:
    """M6's decompounding ladder with B2's gate-level power.

    Order by descending tolerance/sigma (ties by name); prune one cell at a
    time, never the last cell of a concept family; recompute the power
    with Bonferroni m equal to the cells still gated; stop at the first
    power at or above ``target`` (``scripts/build_m6_holdout_floors_v2.py``
    lines 330-373).
    """
    retained = list(sorted(cells, key=lambda c: c.name))
    power = surface_power(retained)["p_gate"]
    log: list[dict[str, Any]] = []
    for cell in sorted(cells, key=lambda c: (-c.tol_over_sigma, c.name)):
        if power >= target:
            break
        family = concept(cell.name)
        if sum(1 for c in retained if concept(c.name) == family) <= 1:
            log.append({"cell": cell.name, "action": "kept_last_in_concept"})
            continue
        retained.remove(cell)
        power = surface_power(retained)["p_gate"]
        log.append(
            {"cell": cell.name, "action": "pruned", "p_gate_after": power}
        )
    vacuity = len(retained) < MIN_GATED_CELLS or all(
        c.capped for c in retained
    )
    return {
        "retained": [c.name for c in retained],
        "pruned": sorted(c.name for c in cells if c not in retained),
        "log": log,
        "p_gate": power,
        "clears": power >= target and not vacuity,
        "vacuity_guard_failed": vacuity,
    }


def admissible_surfaces(names: Sequence[str]) -> Iterable[tuple[str, ...]]:
    """Every subset with at least one cell in each concept family."""
    families = sorted({concept(name) for name in names})
    for size in range(len(families), len(names) + 1):
        for subset in itertools.combinations(sorted(names), size):
            if {concept(name) for name in subset} == set(families):
                yield subset


def envelope(cells: Mapping[str, PlanningCell]) -> dict[str, Any]:
    """Best and worst admissible surface of each size, uncapped."""
    names = sorted(cells)
    terms = {
        m: {
            name: cell_terms(
                cells[name].tau,
                cells[name].r,
                cells[name].e_true,
                cells[name].e_reg,
                m,
            )
            for name in names
        }
        for m in range(1, len(names) + 1)
    }
    by_size: dict[int, dict[str, Any]] = {}
    for subset in admissible_surfaces(names):
        m = len(subset)
        power = gate_probabilities([terms[m][name] for name in subset])[
            "p_gate"
        ]
        slot = by_size.setdefault(
            m,
            {"n_surfaces": 0, "best": None, "worst": None},
        )
        slot["n_surfaces"] += 1
        if slot["best"] is None or power > slot["best"]["p_gate"]:
            slot["best"] = {"cells": list(subset), "p_gate": power}
        if slot["worst"] is None or power < slot["worst"]["p_gate"]:
            slot["worst"] = {"cells": list(subset), "p_gate": power}
    return {str(m): slot for m, slot in sorted(by_size.items())}


def planning_cells(
    planning: Mapping[str, Any], basis: str
) -> dict[str, PlanningCell]:
    """Planning cells on one basis. A cell without planning values
    (``defined`` false in the record) cannot gate and is left out.

    ``binding``: the gap variance is ``s2_gate``, the joint upper limit of
    r**2 + e at B2's origin, and the registered standard error uses the
    same value; the side-A seeds use r's point estimate.
    ``central`` (sensitivity): the gap variance is the point value ``s2``
    and the registered bound is ``e_b2``.
    ``audit_upper_bound`` (sensitivity): r = 1, e = 0, the audit's basis.
    """
    out: dict[str, PlanningCell] = {}
    for name, record in sorted(planning["cells"].items()):
        if not record.get("defined"):
            continue
        r = float(record["shared_anchor_ratio"]["r"])
        gap = record["gap_variance"]
        if basis == "binding":
            e = max(0.0, float(gap["s2_gate"]) - r**2)
            out[name] = PlanningCell(name, r, e, e)
        elif basis == "central":
            out[name] = PlanningCell(
                name,
                r,
                max(0.0, float(gap["s2"]) - r**2),
                float(record["estimation_variance"]["e_b2"]),
            )
        elif basis == "audit_upper_bound":
            out[name] = PlanningCell(name, 1.0, 0.0, 0.0)
        else:
            raise ValueError(f"unknown basis {basis!r}")
    return out


def best_surface_of_size(
    cells: Mapping[str, PlanningCell], size: int
) -> dict[str, Any] | None:
    """The best surface of exactly ``size`` cells, any families."""
    names = sorted(cells)
    if len(names) < size:
        return None
    terms = {
        name: cell_terms(
            cells[name].tau,
            cells[name].r,
            cells[name].e_true,
            cells[name].e_reg,
            size,
        )
        for name in names
    }
    best: dict[str, Any] | None = None
    for subset in itertools.combinations(names, size):
        power = gate_probabilities([terms[name] for name in subset])["p_gate"]
        if best is None or power > best["p_gate"]:
            best = {"cells": list(subset), "p_gate": power}
    return best


def m6_seed_convention_gate(cells: Sequence[PlanningCell]) -> float:
    """Sensitivity: bound rule on full support times M6's own oc_4of5."""
    m = len(cells)
    bound = math.prod(
        cell_terms(c.tau, c.r, c.e_true, c.e_reg, m).bound for c in cells
    )
    p_seed = math.prod(2.0 * norm.cdf(c.tol_over_sigma) - 1.0 for c in cells)
    return float(bound * (p_seed**5 + 5 * p_seed**4 * (1.0 - p_seed)))


def feasibility_verdict(cells: Mapping[str, PlanningCell]) -> dict[str, Any]:
    """Protocol v2's prospective verdict at uncapped tolerances.

    - ``d693_flip_fires``: no surface of four cells (any families) reaches
      0.90 on this basis; B2 is WEAK_POWER_OR_VACUITY.
    - ``family_floor_blocks``: a four-cell surface reaches 0.90 but no
      surface with every concept family does, so M6's ladder, not the
      d693 flip, stops B2. The two ruled texts then disagree, and the
      choice goes to Max.
    - ``feasible``: some surface with every family reaches 0.90. B2's
      floor builder decides with B2's own floor.

    Uncapped tolerances bound every capped surface's power from above.
    """
    families = {concept(name) for name in cells}
    four = best_surface_of_size(cells, MIN_GATED_CELLS)
    env = envelope(cells) if cells else {}
    best_family = max(
        (slot["best"]["p_gate"] for slot in env.values()), default=0.0
    )
    flip = four is None or four["p_gate"] < POWER_TARGET
    family_block = (not flip) and best_family < POWER_TARGET
    return {
        "eligible_families": sorted(families),
        "best_four_cell_surface": four,
        "best_family_surface_p_gate": best_family,
        "d693_flip_fires": flip,
        "family_floor_blocks": family_block,
        "feasible": (not flip) and not family_block,
        "envelope": env,
    }


def seed_conjunction_bound(m: int) -> float:
    """Structural bound on P(two or more seeds fail | bound rule passes).

    Given a bound-rule pass, |x| <= tau - z*_m s_reg with s_reg >= r, so a
    seed's side-A gap N(x, r**2) leaves +-tau with probability at most
    P(|Z| > z*_m) = 0.05 / m per cell, and at most 0.05 per seed over the
    m cells. Two or more of five seeds fail with probability at most
    C(5, 2) * 0.05**2 = 0.025 when seeds are treated as independent given
    the gaps, which they are under the conditional model.
    """
    per_seed = min(1.0, m * (ALPHA / m))
    return float(math.comb(5, 2) * per_seed**2)


def structural_record() -> dict[str, Any]:
    """Figures that need no planning value (the Q2 correction)."""
    upper = PlanningCell("x", 1.0, 0.0, 0.0)
    out: dict[str, Any] = {
        "tau_uncapped_se_up_units": TAU_UNCAPPED,
        "floor_ratio": FLOOR_RATIO,
        "se_up_over_sigma": SE_UP_OVER_SIGMA,
        "seed_conjunction_bound_given_bound_pass": seed_conjunction_bound(6),
        "by_family_size": {},
    }
    for m in range(1, 17):
        term = cell_terms(upper.tau, 1.0, 0.0, 0.0, m)
        gate = gate_probabilities([term] * m)
        per_cell_needed = z_star(m) + float(norm.ppf(0.95))
        gate_needed = z_star(m) + float(
            norm.ppf((1.0 + POWER_TARGET ** (1.0 / m)) / 2.0)
        )
        out["by_family_size"][str(m)] = {
            "z_star": z_star(m),
            "cell_bound_pass": term.bound,
            "p_bound_rule_only": gate["p_bound_rule_only"],
            "p_gate_joint": gate["p_gate"],
            "p_seeds_fail_given_bound_passes": gate[
                "p_seeds_fail_given_bound_passes"
            ],
            "m6_convention_p_gate": m6_convention_gate(m),
            "m6_seed_convention_with_bound_rule": m6_seed_convention_gate(
                [upper] * m
            ),
            "estimation_room_per_cell": (TAU_UNCAPPED / per_cell_needed) ** 2
            - 1.0,
            "estimation_room_gate_bound_only": (TAU_UNCAPPED / gate_needed)
            ** 2
            - 1.0,
        }
    return out


BASES = ("binding", "central", "audit_upper_bound")


def power_record(planning: Mapping[str, Any] | None) -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema": SCHEMA,
        "structural": structural_record(),
    }
    if planning is None:
        return record
    cells = planning["cells"]
    record["planning_flags"] = {
        "cells_without_planning_values": sorted(
            name for name, cell in cells.items() if not cell.get("defined")
        ),
        "cells_with_cross_term_resolved_positive": sorted(
            name
            for name, cell in cells.items()
            if cell.get("defined")
            and cell["gap_variance"]["cross_term_resolved_positive"]
        ),
        "cells_over_design_ratio_limit": sorted(
            name
            for name, cell in cells.items()
            if cell.get("defined")
            and not cell.get("design_ratio", {}).get("within_limit", False)
        ),
        "household_resampling_stands": bool(
            planning["design_rule"]["household_resampling_stands"]
        ),
    }
    record["bases"] = {}
    for basis in BASES:
        chosen = planning_cells(planning, basis)
        names = sorted(chosen)
        retained = [chosen[n] for n in M6_RETAINED if n in chosen]
        record["bases"][basis] = {
            "binding": basis == "binding",
            "per_cell": {
                name: {
                    "r": chosen[name].r,
                    "gap_variance": chosen[name].r ** 2 + chosen[name].e_true,
                    "registered_variance": chosen[name].r ** 2
                    + chosen[name].e_reg,
                    "bound_pass_at_m6": cell_terms(
                        chosen[name].tau,
                        chosen[name].r,
                        chosen[name].e_true,
                        chosen[name].e_reg,
                        6,
                    ).bound,
                }
                for name in names
            },
            "all_cells": (
                surface_power([chosen[n] for n in names]) if names else None
            ),
            "m6_retained_6": (
                surface_power(retained)
                if len(retained) == len(M6_RETAINED)
                else None
            ),
            "m6_seed_convention_m6_retained_6": (
                m6_seed_convention_gate(retained)
                if len(retained) == len(M6_RETAINED)
                else None
            ),
            "verdict": feasibility_verdict(chosen),
        }
    return record


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.parse_args(argv)
    planning = json.loads(PLANNING.read_text(encoding="utf-8"))
    record = power_record(planning)
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
