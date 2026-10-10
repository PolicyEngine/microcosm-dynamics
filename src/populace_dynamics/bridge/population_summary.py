"""Weighted totals and distributions of a population decomposition.

Everything here is exact: household cents from
:func:`~.population.decompose_population` times household weights as exact
rationals (:class:`~.population.ExactWeights`).  Totals by leaf, by the
bridge's display category and by level of government
(:func:`~.population.level_for`) are each a partition of the leaves, so
each sums exactly to the weighted net change; group summaries are a
partition of the households, so they sum exactly to the population's.
:func:`summarize` checks both and records the checks.

The share of the Social Security change taken back is ``(dSS - dNet) /
dSS``: the part of the change in Social Security that other programs and
taxes offset.  For a rise it is the share taxed or means-tested away; for
a cut, the share cushioned.  By level it splits into the federal part
(every federal leaf but Social Security), the state, local and health
parts, which sum exactly to the whole.  For a group whose households'
Social Security moves both ways it is a ratio of net sums, which can fall
outside [0, 1] (a rise offset by SSI nets against the cuts); the summary
flags such a group (``mixes_rises_and_falls``).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from fractions import Fraction
from typing import Any

import numpy as np

from populace_dynamics.bridge import policyengine_us as bridge
from populace_dynamics.bridge.population import (
    LEVELS,
    ExactWeights,
    PopulationDecomposition,
)

__all__ = [
    "UNCLASSIFIED",
    "dollars",
    "health_split",
    "social_security_direction",
    "ssi_status",
    "summarize",
    "take_back",
]

#: The level recorded for a leaf :func:`~.population.level_for` does not
#: classify (such a leaf never changes; the decomposition refuses one that
#: does), so the levels still partition net income.
UNCLASSIFIED = "unclassified"
_SOCIAL_SECURITY = "social_security"


def dollars(value: Fraction) -> float:
    """An exact amount as float dollars rounded to the cent."""

    return round(float(value), 2)


def _amount_fields(values: Mapping[str, Fraction]) -> dict[str, float | str]:
    """Rounded display amounts and their exact rational dollar values."""

    return {
        field: exported
        for name, value in values.items()
        for field, exported in (
            (name, dollars(value)),
            (f"{name}_exact", str(value)),
        )
    }


def _share(numerator: Fraction, denominator: Fraction) -> float | None:
    return None if denominator == 0 else float(numerator / denominator)


def _leaf_totals(
    decomposition: PopulationDecomposition,
    weights: ExactWeights,
    mask: Any = None,
) -> list[dict[str, Any]]:
    out = []
    for j, (name, path, sign, category, level) in enumerate(
        decomposition.leaves
    ):
        baseline = weights.dollars(decomposition.baseline_cents[j], mask)
        reform = weights.dollars(decomposition.reform_cents[j], mask)
        out.append(
            {
                "variable": name,
                "path": list(path),
                "sign": sign,
                "category": category,
                "level": level or UNCLASSIFIED,
                "baseline": baseline,
                "reform": reform,
                "change": reform - baseline,
            }
        )
    return out


def _group_by(
    leaves: Sequence[Mapping[str, Any]], key: str, order: Sequence[str]
) -> dict[str, dict[str, Fraction]]:
    out: dict[str, dict[str, Fraction]] = {
        name: {"baseline": Fraction(0), "reform": Fraction(0)}
        for name in order
    }
    for leaf in leaves:
        entry = out.setdefault(
            leaf[key], {"baseline": Fraction(0), "reform": Fraction(0)}
        )
        entry["baseline"] += leaf["baseline"]
        entry["reform"] += leaf["reform"]
    for entry in out.values():
        entry["change"] = entry["reform"] - entry["baseline"]
    return out


def take_back(
    by_level: Mapping[str, Mapping[str, Fraction]],
    social_security_change: Fraction,
) -> dict[str, Any]:
    """The share of the Social Security change others offset (docstring).

    ``by_level`` holds each level's weighted change, Social Security inside
    ``federal``.  Returns the share and its parts by level, exactly
    summing to it, as floats (``None`` when Social Security does not
    change).
    """

    ss = social_security_change
    net = sum((entry["change"] for entry in by_level.values()), Fraction(0))
    parts = {}
    for level, entry in by_level.items():
        change = entry["change"] - (ss if level == "federal" else 0)
        parts[level] = -change
    if ss == 0:
        return {
            "share": None,
            "by_level": dict.fromkeys(parts),
            "exact_parts_sum_to_share": True,
        }
    share = (ss - net) / ss
    return {
        "share": float(share),
        "by_level": {
            level: float(value / ss) for level, value in parts.items()
        },
        "exact_parts_sum_to_share": sum(parts.values(), Fraction(0)) / ss
        == share,
    }


def ssi_status(decomposition: PopulationDecomposition) -> np.ndarray:
    """Each household's SSI receipt at baseline and under the reform."""

    baseline = np.zeros(decomposition.n_households, dtype=np.int64)
    reform = np.zeros(decomposition.n_households, dtype=np.int64)
    for j, (name, _, sign, _, _) in enumerate(decomposition.leaves):
        if name == "ssi":
            baseline += sign * decomposition.baseline_cents[j]
            reform += sign * decomposition.reform_cents[j]
    labels = np.full(decomposition.n_households, "no SSI", dtype=object)
    labels[(baseline > 0) & (reform > 0)] = "SSI in both"
    labels[(baseline > 0) & (reform <= 0)] = "SSI at baseline only"
    labels[(baseline <= 0) & (reform > 0)] = "SSI under the reform only"
    return labels


#: :func:`ssi_status`'s groups in table order.
SSI_STATUS_ORDER = (
    "SSI in both",
    "SSI at baseline only",
    "SSI under the reform only",
    "no SSI",
)


def social_security_direction(
    decomposition: PopulationDecomposition,
) -> np.ndarray:
    """Whether each household's Social Security rises, falls or holds."""

    change = np.zeros(decomposition.n_households, dtype=np.int64)
    for j, (name, _, _, _, _) in enumerate(decomposition.leaves):
        if name == _SOCIAL_SECURITY:
            change += decomposition.change_cents(j)
    labels = np.full(
        decomposition.n_households, "Social Security unchanged", dtype=object
    )
    labels[change > 0] = "Social Security rises"
    labels[change < 0] = "Social Security falls"
    return labels


DIRECTION_ORDER = (
    "Social Security rises",
    "Social Security falls",
    "Social Security unchanged",
)


def _summary(
    decomposition: PopulationDecomposition,
    weights: ExactWeights,
    people: np.ndarray,
    mask: Any = None,
) -> dict[str, Any]:
    leaves = _leaf_totals(decomposition, weights, mask)
    levels = _group_by(leaves, "level", (*LEVELS, UNCLASSIFIED))
    categories = _group_by(leaves, "category", bridge.CATEGORY_ORDER)
    ss = sum(
        (
            leaf["change"]
            for leaf in leaves
            if leaf["variable"] == "social_security"
        ),
        Fraction(0),
    )
    net = weights.dollars(decomposition.net_change_cents, mask)
    baseline = weights.dollars(decomposition.baseline_net_cents, mask)
    reform = weights.dollars(decomposition.reform_net_cents, mask)
    chosen = (
        np.ones(decomposition.n_households, dtype=bool)
        if mask is None
        else np.asarray(mask, dtype=bool)
    )
    person_weights = ExactWeights(
        tuple(
            n * int(p) for n, p in zip(weights.numerators, people, strict=True)
        ),
        weights.denominator,
    )
    weighted_households = weights.total_weight(mask)
    ss_cents = np.zeros(decomposition.n_households, dtype=np.int64)
    for j, leaf in enumerate(decomposition.leaves):
        if leaf[0] == _SOCIAL_SECURITY:
            ss_cents += decomposition.change_cents(j)
    rises = int(((ss_cents > 0) & chosen).sum())
    falls = int(((ss_cents < 0) & chosen).sum())
    identity = {
        "leaves": sum((leaf["change"] for leaf in leaves), Fraction(0)) == net,
        "categories": sum(
            (entry["change"] for entry in categories.values()), Fraction(0)
        )
        == net,
        "levels": sum(
            (entry["change"] for entry in levels.values()), Fraction(0)
        )
        == net,
        "baseline_levels": sum(
            (entry["baseline"] for entry in levels.values()), Fraction(0)
        )
        == baseline,
    }
    return {
        "households": int(chosen.sum()),
        "people": int(np.asarray(people)[chosen].sum()),
        "weighted_households": float(weighted_households),
        "weighted_people": float(person_weights.total_weight(mask)),
        "baseline_net_income": dollars(baseline),
        "baseline_net_income_exact": str(baseline),
        "reform_net_income": dollars(reform),
        "reform_net_income_exact": str(reform),
        "net_change": dollars(net),
        "net_change_exact": str(net),
        "social_security_change": dollars(ss),
        "social_security_change_exact": str(ss),
        "mean_net_change_per_household": (
            dollars(net / weighted_households) if weighted_households else None
        ),
        "mean_social_security_change_per_household": (
            dollars(ss / weighted_households) if weighted_households else None
        ),
        "by_level": {
            level: _amount_fields(entry) for level, entry in levels.items()
        },
        "by_category": {
            name: _amount_fields(entry) for name, entry in categories.items()
        },
        "by_leaf": [
            {
                **{k: leaf[k] for k in ("variable", "path", "sign")},
                "category": leaf["category"],
                "level": leaf["level"],
                **_amount_fields(
                    {
                        key: leaf[key]
                        for key in ("baseline", "reform", "change")
                    }
                ),
            }
            for leaf in leaves
            if leaf["baseline"] or leaf["reform"]
        ],
        "households_social_security_rises": rises,
        "households_social_security_falls": falls,
        "take_back": {
            **take_back(levels, ss),
            "mixes_rises_and_falls": bool(rises and falls),
        },
        "identity_exact": identity,
        "_exact": {"net": net, "levels": levels, "ss": ss},
    }


def summarize(
    decomposition: PopulationDecomposition,
    weights: Sequence[float],
    people: Sequence[int],
    groupings: Mapping[str, tuple[np.ndarray, Sequence[Any]]] | None = None,
) -> dict[str, Any]:
    """The weighted totals, and each grouping's partition of them.

    ``weights`` and ``people`` are per household; ``groupings`` maps a name
    to (one label per household, the labels in table order).  Every total
    is exact before rounding; ``identity_exact`` records that leaves,
    categories and levels each sum exactly to the net change, and each
    grouping's ``partition_exact`` that its groups sum exactly to the
    population's net change and Social Security change.  Raises if any
    check fails.
    """

    exact = ExactWeights.from_floats(weights)
    counts = np.asarray(people, dtype=np.int64)
    overall = _summary(decomposition, exact, counts)
    if not all(overall["identity_exact"].values()):
        raise AssertionError(f"identity failed: {overall['identity_exact']}")
    groups_out: dict[str, Any] = {}
    for name, (labels, order) in (groupings or {}).items():
        labels = np.asarray(labels, dtype=object)
        if len(labels) != decomposition.n_households:
            raise ValueError(f"{name}: one label per household")
        unknown = set(labels.tolist()) - set(order)
        if unknown:
            raise ValueError(f"{name}: labels {sorted(unknown)} not ordered")
        groups = {}
        net = Fraction(0)
        ss = Fraction(0)
        for label in order:
            mask = labels == label
            if not mask.any():
                continue
            summary = _summary(decomposition, exact, counts, mask)
            if not all(summary["identity_exact"].values()):
                raise AssertionError(f"{name}={label}: identity failed")
            net += summary["_exact"]["net"]
            ss += summary["_exact"]["ss"]
            groups[str(label)] = summary
        partition = (
            net == overall["_exact"]["net"] and ss == overall["_exact"]["ss"]
        )
        if not partition:
            raise AssertionError(f"{name}: groups do not sum to the total")
        for summary in groups.values():
            summary.pop("_exact")
            summary.pop("by_leaf")
        groups_out[name] = {"groups": groups, "partition_exact": partition}
    overall.pop("_exact")
    return {"population": overall, "groupings": groups_out}


#: The programs whose federal and state cost policyengine-us 2.18.0 splits
#: (``medicaid_federal_cost.py:17-20`` and ``medicaid_state_cost.py:17-20``
#: with the FMAP of ``medicaid_federal_share.py:19-32``;
#: ``chip_federal_cost.py:18-19`` and ``chip_state_cost.py:18-21`` with the
#: enhanced FMAP of ``chip_federal_share.py:19-24``;
#: ``msp_federal_cost.py:24-50`` and ``msp_state_cost.py:17-21``).
HEALTH_PROGRAMS: dict[str, tuple[str, str, str]] = {
    "medicaid": (
        "medicaid_cost",
        "medicaid_federal_cost",
        "medicaid_state_cost",
    ),
    "chip": ("chip", "chip_federal_cost", "chip_state_cost"),
    "msp": ("msp_cost", "msp_federal_cost", "msp_state_cost"),
}
#: The person-level memo variables :func:`health_split` reads.
HEALTH_MEMO: tuple[str, ...] = (
    *(name for names in HEALTH_PROGRAMS.values() for name in names),
    "medicaid_enrolled",
)


def health_split(
    memo: Mapping[str, Mapping[str, np.ndarray]],
    person_weights: Sequence[float],
    scenarios: Sequence[str],
) -> dict[str, Any]:
    """Each program's weighted total, federal and state cost by scenario.

    ``memo[scenario][name]`` is policyengine-us's value per person; weights
    are each person's household weight.  Amounts are rounded to cents per
    person (as the decomposition rounds leaves) and summed exactly.
    ``max_split_gap_cents`` is the largest per-person gap between the
    program's cost and its federal plus state parts (float32 products in
    policyengine-us; a gap of a cent or two is rounding).
    """

    from populace_dynamics.bridge.population import to_cents_array

    exact = ExactWeights.from_floats(person_weights)
    out: dict[str, Any] = {}
    for program, (total, federal, state) in HEALTH_PROGRAMS.items():
        entry: dict[str, Any] = {}
        gap = 0
        for scenario in scenarios:
            values = {
                key: to_cents_array(memo[scenario][name])
                for key, name in (
                    ("total", total),
                    ("federal", federal),
                    ("state", state),
                )
            }
            gap = max(
                gap,
                int(
                    np.abs(
                        values["total"] - values["federal"] - values["state"]
                    ).max(initial=0)
                ),
            )
            entry[scenario] = {
                key: dollars(exact.dollars(array))
                for key, array in values.items()
            }
            entry[scenario]["_exact"] = {
                key: exact.dollars(array) for key, array in values.items()
            }
        first, last = scenarios[0], scenarios[-1]
        entry["change"] = {
            key: dollars(
                entry[last]["_exact"][key] - entry[first]["_exact"][key]
            )
            for key in ("total", "federal", "state")
        }
        for scenario in scenarios:
            entry[scenario].pop("_exact")
        entry["max_split_gap_cents"] = gap
        out[program] = entry
    enrolled = {}
    for scenario in scenarios:
        flags = np.asarray(memo[scenario]["medicaid_enrolled"], dtype=float)
        enrolled[scenario] = float(exact.total_weight(flags > 0))
    out["medicaid_enrolled_weighted_people"] = enrolled
    return out
