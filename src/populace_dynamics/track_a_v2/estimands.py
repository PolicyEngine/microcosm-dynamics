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


class WorkerFloorMismatch(ValueError):
    """A paired worker-only population changed before tabulation (§10)."""

    def __init__(self, person_id, draw):
        super().__init__("paired worker-only amounts or population differ")
        self.person_id = person_id
        self.draw = draw


def _worker_floor_rows(rows, reference, config, row):
    """Retain paired legacy family splits for the §9 worker-only identities."""
    if row.mechanism not in ("S", "DS") or row.row_id not in ("R5", "F6"):
        raise ValueError("paired floor inputs require an S/DS worker-only row")
    floor_rows = normalize_rows(reference, config)

    def selected_people(normalized):
        return {
            (int(normalized.draw[i]), normalized.person_id[i]): (
                normalized.selected_base[i],
                normalized.selected_reform[i],
                normalized.weight[i],
                normalized.birth_year[i],
                normalized.family_unit_id[i],
            )
            for i in range(normalized.n)
            if normalized.selected_base[i] > 0
            or normalized.selected_reform[i] > 0
        }

    people, reference_people = selected_people(rows), selected_people(
        floor_rows
    )
    for key in sorted(
        set(people) | set(reference_people), key=lambda k: (k[0], str(k[1]))
    ):
        if people.get(key) != reference_people.get(key):
            raise WorkerFloorMismatch(person_id=key[1], draw=key[0])
    return floor_rows


def validate_worker_floor_pair(
    records, reference, row, *, draw_indices=tuple(range(20))
):
    """Validate every paired floor before any joint tabulation (§10)."""
    config = a7_config(row, draw_indices=draw_indices)
    _worker_floor_rows(normalize_rows(records, config), reference, config, row)


def tabulate_rows(
    records: Iterable[Mapping[str, Any]],
    row: MatrixRow,
    *,
    draw_indices: tuple[int, ...] = tuple(range(20)),
    floor_seeds: tuple[int, ...] = tuple(range(5)),
    floor_records: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Tabulate a guarded row; no pooled ratios or undefined-draw deletion.

    The joint runner must complete every row's guard before invoking this
    function (§10). R retains the final A7 membership check as well. For
    S/DS worker-only rows, the joint runner supplies corresponding L/D
    floor_records to preserve the explicit §§9/12.9 row identities.
    """
    config = a7_config(row, draw_indices=draw_indices, floor_seeds=floor_seeds)
    rows = normalize_rows(records, config)
    if row.row_id.startswith("R") and np.any(
        rows.recipient_base != rows.recipient_reform
    ):
        raise a7.MembershipDifferenceError("R selected memberships differ")
    profile = _profile(rows, config, np.ones(rows.n, dtype=bool))
    # §§9/12.9 require worker-only row equality, including uncertainty.
    # §7.3 and A1 §16 fix the split rule but do not specify how to reconcile
    # spouse-only families added by S with that identity. Conservatively
    # retain the corresponding L/D worker-equivalent frame for floors only;
    # point statistics retain this mechanism's realized membership (§3.4).
    floor_rows = (
        rows
        if floor_records is None
        else _worker_floor_rows(rows, floor_records, config, row)
    )
    per_seed, floors = _floors(floor_rows, config, row.statistic)
    groups = []
    for group, cells in zip(config.age_groups, profile, strict=True):
        summary = a7._draw_summary(cells, row.statistic)
        if not row.row_id.startswith("U"):
            # §7.1 reserves all-alive means and denominators for the frame
            # retaining double zeros. R/F retain their inherited filters,
            # so their supplied records cannot describe all-alive levels.
            for cell in cells:
                for field in (
                    "all_alive_weight",
                    "all_alive_count",
                    "all_alive_mean_base",
                    "all_alive_mean_reform",
                ):
                    cell.pop(field)
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
