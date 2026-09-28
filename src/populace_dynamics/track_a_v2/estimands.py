"""a2-ratified-1 §7: A7 normalization and common-base union arithmetic.

Normalization is inherited from estimates/cola_age_profile.py:1045–1178;
draw and floor definedness from that file's :1308–1406. Family splitting
uses harness/panel.py:195–214, the same helper as A7 :1458–1461.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import replace
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.estimates import cola_age_profile as a7
from populace_dynamics.track_a_v2.matrix import (
    UNION_STATISTIC,
    MatrixRow,
    a7_config,
)


def pair_scenarios(
    baseline: Mapping[int, Mapping[str, Any]],
    reform: Mapping[int, Mapping[str, Any]],
    *,
    draw: int,
) -> list[dict[str, Any]]:
    """Pair all alive persons, refusing unequal persons, weights or metadata.

    Each scenario record supplies birth_year, family_unit_id, weight and a
    components mapping. Double zeros remain available for population means.
    """
    if set(baseline) != set(reform):
        raise ValueError("the two scenarios cover different persons")
    out = []
    for person in sorted(baseline):
        base, new = baseline[person], reform[person]
        for field in ("weight", "birth_year", "family_unit_id"):
            # §7.2 is silent on metadata disagreements beyond weights.
            # Conservatively refuse: these fixed attributes define the cell.
            if base[field] != new[field]:
                raise ValueError(f"scenario {field} mismatch: {person}")
        names = sorted(set(base["components"]) | set(new["components"]))
        components = {
            name: {
                "base": base["components"].get(name, 0.0),
                "reform": new["components"].get(name, 0.0),
            }
            for name in names
        }
        total_base = sum(v["base"] for v in components.values())
        total_reform = sum(v["reform"] for v in components.values())
        out.append(
            {
                "draw": draw,
                "person_id": person,
                "family_unit_id": base["family_unit_id"],
                "birth_year": base["birth_year"],
                "weight": base["weight"],
                "beneficiary_base": total_base > 0,
                "beneficiary_reform": total_reform > 0,
                "benefit_base": total_base,
                "benefit_reform": total_reform,
                "benefit_components": components,
            }
        )
    return out


def normalize_rows(
    records: Iterable[Mapping[str, Any]], config: a7.ColaAgeProfileConfig
) -> a7._Rows:
    """Use A7 validation, admitting empty draws as undefined cells (§7.2)."""
    records = list(records)
    present = tuple(sorted({int(r["draw"]) for r in records}))
    if not set(present) <= set(config.draw_indices):
        raise ValueError("rows contain an unregistered draw")
    if records:
        return a7._normalize(records, replace(config, draw_indices=present))
    # §7.2 requires no-member cells to be undefined. A7's input normalizer
    # rejects an entirely empty table; represent it without inventing people.
    empty_int = np.array([], dtype=np.int64)
    empty_float = np.array([], dtype=float)
    empty_bool = np.array([], dtype=bool)
    return a7._Rows(
        draw=empty_int,
        person_id=np.array([], dtype=object),
        family_unit_id=np.array([], dtype=object),
        weight=empty_float,
        birth_year=empty_int,
        age=empty_int,
        group=empty_int,
        selected_base=empty_float,
        selected_reform=empty_float,
        recipient_base=empty_bool,
        recipient_reform=empty_bool,
        flagged_zero_base=0,
        flagged_zero_reform=0,
        n_persons_weight_varies=0,
        extra_columns=(),
    )


def _cell(rows, selected, masks, draw):
    cell = a7._cell(rows, selected, masks, draw)
    weights = rows.weight[selected]
    total_base = a7._fsum(weights * rows.selected_base[selected])
    total_reform = a7._fsum(weights * rows.selected_reform[selected])
    all_alive_weight = a7._fsum(weights)
    cell.update(
        {
            UNION_STATISTIC: (
                a7._finite(
                    100 * (total_reform / total_base - 1), UNION_STATISTIC
                )
                if total_base > 0
                else None
            ),
            "weighted_total_base": total_base,
            "weighted_total_reform": total_reform,
            "all_alive_weight": all_alive_weight,
            "all_alive_count": int(np.count_nonzero(selected)),
            "all_alive_mean_base": (
                total_base / all_alive_weight if all_alive_weight else None
            ),
            "all_alive_mean_reform": (
                total_reform / all_alive_weight if all_alive_weight else None
            ),
        }
    )
    if total_base <= 0:
        cell["undefined_reasons"][
            UNION_STATISTIC
        ] = "nonpositive_baseline_total"
    return cell


def _profile(rows, config, subset):
    masks = a7._membership_masks(rows, config.membership_basis)
    return [
        [
            _cell(
                rows,
                subset & (rows.group == group) & (rows.draw == draw),
                masks,
                draw,
            )
            for draw in config.draw_indices
        ]
        for group in range(len(config.age_groups))
    ]


def _floors(rows, config, statistic):
    # §§3.4/7.3 retain the inherited row-specific family frame. §9's
    # workers-only statistic identities concern per-draw estimands; if S
    # adds a spouse-only family with zero selected worker benefits, floors
    # may change. Do not alter v1 filtering to force uncertainty equality.
    per_seed = []
    unit_frame = pd.DataFrame({a7.FAMILY_UNIT: rows.family_unit_id.tolist()})
    for seed in config.floor_seeds:
        if rows.n:
            side, _ = a7.split_panel_by_person(
                unit_frame, a7.FAMILY_UNIT, fraction=0.5, seed=seed
            )
            in_a = np.zeros(rows.n, dtype=bool)
            in_a[side.index.to_numpy()] = True
        else:
            in_a = np.array([], dtype=bool)
        summaries = []
        for selected in (in_a, ~in_a):
            summaries.append(
                {
                    group.label: a7._draw_summary(cells, statistic)
                    for group, cells in zip(
                        config.age_groups,
                        _profile(rows, config, selected),
                        strict=True,
                    )
                }
            )
        per_seed.append(
            {"seed": seed, "side_a": summaries[0], "side_b": summaries[1]}
        )
    floors = {}
    for group in config.age_groups:
        gaps, dropped = [], []
        for seed in per_seed:
            a = seed["side_a"][group.label]["mean"]
            b = seed["side_b"][group.label]["mean"]
            if a is None or b is None:
                dropped.append(seed["seed"])
            else:
                gaps.append(abs(a - b))
        floors[group.label] = {
            **a7._floor_summary(gaps),
            "dropped_seeds": dropped,
        }
    return per_seed, floors


def tabulate_rows(
    records: Iterable[Mapping[str, Any]],
    row: MatrixRow,
    *,
    draw_indices: tuple[int, ...] = tuple(range(20)),
    floor_seeds: tuple[int, ...] = tuple(range(5)),
) -> dict[str, Any]:
    """Tabulate a guarded row; no pooled ratios or undefined-draw deletion.

    The joint runner must complete every row's guard before invoking this
    function (§10). R retains the final A7 membership check as well.
    """
    config = a7_config(row, draw_indices=draw_indices, floor_seeds=floor_seeds)
    rows = normalize_rows(records, config)
    if row.row_id.startswith("R") and np.any(
        rows.recipient_base != rows.recipient_reform
    ):
        raise a7.MembershipDifferenceError("R selected memberships differ")
    profile = _profile(rows, config, np.ones(rows.n, dtype=bool))
    per_seed, floors = _floors(rows, config, row.statistic)
    groups = []
    for group, cells in zip(config.age_groups, profile, strict=True):
        summary = a7._draw_summary(cells, row.statistic)
        groups.append(
            {
                **group.as_dict(),
                row.statistic: {**summary, "floor": floors[group.label]},
                "cells": cells,
            }
        )
    return {
        "row": row.as_dict(),
        "labels": list(row.labels),
        "groups": groups,
        "floor_per_seed": per_seed,
    }
