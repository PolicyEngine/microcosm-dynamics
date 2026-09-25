"""The Table 6 statistic for Track M (plan item M8): the PSID share.

Python rules (not Axiom).  For option *k* of Table 5's options 2-5 and
cell *c* of Table 6's rows (All, Men, Women), over the universe of the M1
specification (section 10), with *w* the 2023 cross-section weight and *A*
from :mod:`.evaluation` (G23)::

    S_k[c] = 100 * sum_{i in c} w_i A_k,i / sum_{i in c} w_i

The headline is *S*₂[All], designated before any result (d219 item 1).
Twelve cells are scored; the N column (weighted and unweighted) is
reported, never scored.  Y3, the women-to-men comparison of option 3's
receipt, is reported as a ratio of rates and as a ratio of weighted
counts and is not scored.  A person whose sex is unknown (ER32000 code 9)
counts in All only.

Uncertainty (the plan's G19, the Track U pattern; :data:`UNCERTAINTY`,
which the M1 specification's section 19 block must equal).  The
estimators are Track U's, reused unchanged from
:mod:`populace_dynamics.estimates.uniform_cut_tabulation` (its
``floor_split_units``, ``_floor_summary``, ``_design_clusters`` and
``_design_se``), so both tracks compute a floor and a standard error the
same way:

* deterministic (K = 1);
* a five-seed (0-4) half-split floor: family units linked through shared
  persons (``floor_split_units``; with one row per person these are the
  family units) split person-disjointly (``split_panel_by_person``,
  fraction 0.5); each cell's share recomputed in each half; the floor is
  the mean, SD, min and max of ``|a - b|`` over the seeds where both
  halves are defined, undefined with fewer than two;
* a design-based standard error by Taylor linearization with the PSID
  stratum and cluster (ER31996, ER31997), as a domain estimator on the
  full sample design: every (stratum, cluster) pair of the design frame
  (the 2023 wave's persons with a positive ER35265 weight, which the
  cohort supplies) enters, with ``z = 0`` outside the cell; a stratum
  with one cluster cannot contribute a variance term and is left out,
  counted and listed.  The standard error is in percentage points.

**Provenance guard** (as Track U's, and stricter):
``data_provenance="invented"`` prefixes :data:`INVENTED_DATA_LABEL` and
refuses rows not marked invented, so rows built from PSID files are
refused; ``"registered_real"`` requires the issue #42 registration pointer
(a comment URL), rows marked as built from staged PSID files, no invented
label, the registered floor seeds, and an M1 specification block the
registered-run gate authorizes
(``specification.check_specification_for_registered_run``: ratified,
nothing awaiting Max, every ruling recorded, nothing blocking it, block
equal to code).  The committed ``m1-draft-2`` authorizes none (it is a
draft, and its ``blocked_by`` names the open blockers), so nothing computes
the share on real data.

Every result carries the Track M labels and the covered-earnings
disclosure Max's d280 ruling requires.
"""

from __future__ import annotations

import copy
import math
import re
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.estimates import uniform_cut_tabulation as track_u
from populace_dynamics.estimates.uniform_cut_tabulation import (
    DEFAULT_FLOOR_SEEDS,
    FLOOR_FRACTION,
    MIN_FLOOR_SEEDS,
    floor_split_units,
)
from populace_dynamics.harness.panel import split_panel_by_person
from populace_dynamics.min_benefit_track_m import (
    COVERED_EARNINGS_DISCLOSURE,
    DRY_RUN_HEADER,
    OUTPUT_LABELS,
)
from populace_dynamics.min_benefit_track_m.evaluation import (
    INVENTED,
    PSID_FILES,
)
from populace_dynamics.min_benefit_track_m.policy import (
    HEADLINE_CELL,
    TABLE6_OPTIONS,
    TABLE6_ROWS,
)

__all__ = [
    "DATA_PROVENANCES",
    "FLOOR_SPLIT_UNIT",
    "FORMULA",
    "INVENTED",
    "INVENTED_DATA_LABEL",
    "PSID_FILES",
    "REGISTERED_REAL",
    "REGISTRATION_POINTER",
    "REQUIRED_COLUMNS",
    "SCHEMA_VERSION",
    "STATISTIC",
    "STATISTIC_ID",
    "TrackMTabulationError",
    "UNCERTAINTY",
    "check_provenance",
    "statistic_block",
    "tabulate_track_m",
    "uncertainty_block",
]

SCHEMA_VERSION = "populace_dynamics.track_m_tabulation.v1"
STATISTIC_ID = "dynasim_exercise4_share_receiving_minimum_income_year_2022"
FORMULA = "100 * sum_i w_i A_k,i / sum_i w_i over the universe, per cell"
#: The statistic as the M1 specification's section 19 block records it
#: (``statistic``); the N column is reported, never scored.
STATISTIC: dict[str, Any] = {
    "id": STATISTIC_ID,
    "formula": FORMULA,
    "unit": "percent",
    "n_scored": False,
}
#: The floor's split unit: family units linked through shared persons
#: (Track U's ``floor_split_units``).
FLOOR_SPLIT_UNIT = "family_unit_linked_by_person"
#: The uncertainty the M1 specification registers (section 12; the
#: section 19 block's ``uncertainty``): the Track U pattern (plan G19).
UNCERTAINTY: dict[str, Any] = {
    "draws": 1,
    "floor": {
        "seeds": list(DEFAULT_FLOOR_SEEDS),
        "fraction": FLOOR_FRACTION,
        "split_unit": FLOOR_SPLIT_UNIT,
        "min_usable_seeds": MIN_FLOOR_SEEDS,
    },
    "design_se": {
        "method": "taylor_linearization",
        "domain": "full_sample_design",
        "frame": "wave_2023_persons_with_positive_ER35265",
        "stratum": "ER31996",
        "cluster": "ER31997",
        "singleton_strata": "left_out_counted_and_listed",
        "unit": "percentage_points",
    },
}
INVENTED_DATA_LABEL = DRY_RUN_HEADER
REGISTERED_REAL = "registered_real"
DATA_PROVENANCES: tuple[str, ...] = (INVENTED, REGISTERED_REAL)
#: A comment on issue #42, the registration issue; nothing else is a
#: registration pointer (the entry script reads the same pattern).
REGISTRATION_POINTER = re.compile(
    r"https://github\.com/PolicyEngine/microcosm-dynamics/issues/42"
    r"#issuecomment-[0-9]+"
)
REQUIRED_COLUMNS: tuple[str, ...] = (
    "person_id",
    "family_unit_id",
    "weight",
    "sex",
    "stratum",
    "cluster",
    *(f"receives_{number}" for number in TABLE6_OPTIONS),
)
_ROW_SEX = {"all": None, "men": "male", "women": "female"}


class TrackMTabulationError(ValueError):
    """The rows or the provenance cannot yield the Track M statistic."""


def statistic_block() -> dict[str, Any]:
    """A copy of :data:`STATISTIC`, as the M1 block must record it."""

    return copy.deepcopy(STATISTIC)


def uncertainty_block() -> dict[str, Any]:
    """A copy of :data:`UNCERTAINTY`, as the M1 block must record it."""

    return copy.deepcopy(UNCERTAINTY)


def _design_clusters(design: pd.DataFrame | None) -> pd.MultiIndex | None:
    try:
        return track_u._design_clusters(design)
    except track_u.UniformCutTabulationError as error:
        raise TrackMTabulationError(str(error)) from error


def _design_se(
    rows: pd.DataFrame,
    mask: np.ndarray,
    indicator: np.ndarray,
    clusters_all: pd.MultiIndex,
) -> dict[str, Any]:
    try:
        return track_u._design_se(rows, mask, indicator, clusters_all)
    except track_u.UniformCutTabulationError as error:
        raise TrackMTabulationError(str(error)) from error


def _floor_summary(values: list[float]) -> dict[str, Any]:
    try:
        return track_u._floor_summary(values)
    except track_u.UniformCutTabulationError as error:
        raise TrackMTabulationError(str(error)) from error


def check_provenance(
    rows: pd.DataFrame,
    *,
    data_provenance: str,
    registration_pointer: str | None,
    labels: Sequence[str] = OUTPUT_LABELS,
    specification: Mapping[str, Any] | None = None,
) -> None:
    """Refuse a tabulation its provenance does not authorize.

    Runs before anything is computed.  PSID-built rows need
    ``registered_real``, the issue #42 comment pointer and an M1 block the
    registered-run gate authorizes; invented rows need ``invented``.
    """

    if data_provenance not in DATA_PROVENANCES:
        raise TrackMTabulationError(
            f"data_provenance must be one of {DATA_PROVENANCES}"
        )
    if isinstance(labels, str):
        raise TrackMTabulationError("labels must be a sequence")
    missing = [label for label in OUTPUT_LABELS if label not in labels]
    if missing:
        raise TrackMTabulationError(
            f"every output carries the Track M labels; missing {missing}"
        )
    kind = (
        rows.attrs.get("provenance_kind")
        if isinstance(rows, pd.DataFrame)
        else None
    )
    if data_provenance == REGISTERED_REAL:
        if not isinstance(
            registration_pointer, str
        ) or not REGISTRATION_POINTER.fullmatch(registration_pointer):
            raise TrackMTabulationError(
                "real-data tabulation requires the issue #42 registration "
                "pointer (https://github.com/PolicyEngine/microcosm-"
                "dynamics/issues/42#issuecomment-<id>), which must exist "
                "before the run"
            )
        if INVENTED_DATA_LABEL in labels:
            raise TrackMTabulationError(
                "a registered_real result cannot carry the invented label"
            )
        if kind != PSID_FILES:
            raise TrackMTabulationError(
                f"data_provenance 'registered_real' contradicts the rows' "
                f"provenance {kind!r}: a registered run tabulates rows built "
                "from staged PSID files"
            )
        from populace_dynamics.min_benefit_track_m import (
            specification as m1,
        )

        block = (
            m1.m1_parameter_block() if specification is None else specification
        )
        try:
            m1.check_specification_for_registered_run(block)
        except ValueError as error:
            raise TrackMTabulationError(
                f"the M1 specification does not authorize a real-data run: "
                f"{error}"
            ) from error
    elif kind == PSID_FILES:
        raise TrackMTabulationError(
            "rows built from staged PSID files cannot be tabulated as "
            "invented data"
        )
    elif kind != INVENTED:
        raise TrackMTabulationError(
            f"invented rows must say so (provenance_kind 'invented'), not "
            f"{kind!r}"
        )


def _normalize(rows: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(rows, pd.DataFrame):
        raise TrackMTabulationError("rows must be a DataFrame")
    missing = [c for c in REQUIRED_COLUMNS if c not in rows.columns]
    if missing:
        raise TrackMTabulationError(f"rows lack columns {missing}")
    out = rows[list(REQUIRED_COLUMNS)].reset_index(drop=True).copy()
    if out.empty:
        raise TrackMTabulationError("no rows")
    if out["person_id"].duplicated().any():
        raise TrackMTabulationError(
            "duplicate person_id: each person is observed once"
        )
    weight = pd.to_numeric(out["weight"], errors="raise").astype("float64")
    if not np.all(np.isfinite(weight)) or (weight < 0).any():
        raise TrackMTabulationError("weights must be finite and >= 0")
    out["weight"] = weight
    sexes = set(out["sex"].astype(str))
    if not sexes <= {"male", "female", "unknown"}:
        raise TrackMTabulationError(
            f"sex outside male/female/unknown: {sexes}"
        )
    for number in TABLE6_OPTIONS:
        column = f"receives_{number}"
        values = out[column]
        if not values.map(lambda v: isinstance(v, bool | np.bool_)).all():
            raise TrackMTabulationError(f"{column} must be boolean")
        out[column] = values.astype(bool)
    if (
        out[["person_id", "family_unit_id", "stratum", "cluster"]]
        .isna()
        .any(axis=None)
    ):
        raise TrackMTabulationError(
            "person_id, family_unit_id, stratum and cluster must be present"
        )
    for column in ("stratum", "cluster"):
        out[column] = out[column].astype("int64")
    return out


def _mask(rows: pd.DataFrame, row: str) -> np.ndarray:
    sex = _ROW_SEX[row]
    if sex is None:
        return np.ones(len(rows), dtype=bool)
    return rows["sex"].eq(sex).to_numpy()


def _share(rows: pd.DataFrame, mask: np.ndarray, number: int) -> dict:
    weight = rows["weight"].to_numpy()
    receiving = rows[f"receives_{number}"].to_numpy()
    total = math.fsum(weight[mask])
    if not mask.any():
        return {"defined": False, "undefined_reason": "empty cell"}
    if total <= 0:
        return {"defined": False, "undefined_reason": "zero total weight"}
    numerator = math.fsum(weight[mask & receiving])
    return {
        "defined": True,
        "undefined_reason": None,
        "share_percent": 100.0 * numerator / total,
        "weighted_receiving": numerator,
        "weighted_n": total,
        "unweighted_n": int(mask.sum()),
        "unweighted_receiving": int((mask & receiving).sum()),
    }


def _y3(rows: pd.DataFrame, mask: np.ndarray) -> dict[str, Any]:
    """Option 3's women-to-men comparison, both ways (not scored)."""

    women = _share(rows, mask & _mask(rows, "women"), 3)
    men = _share(rows, mask & _mask(rows, "men"), 3)
    if not (women["defined"] and men["defined"]):
        return {"defined": False, "undefined_reason": "a sex cell is empty"}
    rates = (
        women["share_percent"] / men["share_percent"]
        if men["share_percent"] > 0
        else None
    )
    counts = (
        women["weighted_receiving"] / men["weighted_receiving"]
        if men["weighted_receiving"] > 0
        else None
    )
    if rates is None or counts is None:
        return {"defined": False, "undefined_reason": "no man receives"}
    return {
        "defined": True,
        "undefined_reason": None,
        "ratio_of_rates": rates,
        "ratio_of_weighted_counts": counts,
    }


def _floors(
    rows: pd.DataFrame, seeds: tuple[int, ...]
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    units = pd.DataFrame({"split_unit": floor_split_units(rows)})
    per_seed = []
    gaps: dict[str, list[float]] = {}
    dropped: dict[str, list[int]] = {}
    y3_gaps: dict[str, list[float]] = {
        "ratio_of_rates": [],
        "ratio_of_weighted_counts": [],
    }
    y3_dropped: list[int] = []
    everyone = np.ones(len(rows), dtype=bool)
    for seed in seeds:
        side_a, _ = split_panel_by_person(
            units, "split_unit", fraction=FLOOR_FRACTION, seed=int(seed)
        )
        in_a = np.zeros(len(rows), dtype=bool)
        in_a[side_a.index.to_numpy()] = True
        entry = {"seed": int(seed), "n_side_a": int(in_a.sum())}
        for number in TABLE6_OPTIONS:
            for row in TABLE6_ROWS:
                key = f"{number}:{row}"
                mask = _mask(rows, row)
                a = _share(rows, mask & in_a, number)
                b = _share(rows, mask & ~in_a, number)
                if a["defined"] and b["defined"]:
                    gaps.setdefault(key, []).append(
                        abs(a["share_percent"] - b["share_percent"])
                    )
                else:
                    dropped.setdefault(key, []).append(int(seed))
        a3, b3 = _y3(rows, everyone & in_a), _y3(rows, everyone & ~in_a)
        if a3["defined"] and b3["defined"]:
            for name in y3_gaps:
                y3_gaps[name].append(abs(a3[name] - b3[name]))
        else:
            y3_dropped.append(int(seed))
        per_seed.append(entry)
    keys = [f"{n}:{r}" for n in TABLE6_OPTIONS for r in TABLE6_ROWS]
    floors = {
        key: {
            **_floor_summary(gaps.get(key, [])),
            "dropped_seeds": dropped.get(key, []),
        }
        for key in keys
    }
    y3_floors = {
        name: {**_floor_summary(values), "dropped_seeds": y3_dropped}
        for name, values in y3_gaps.items()
    }
    return floors, y3_floors, per_seed


def tabulate_track_m(
    rows: pd.DataFrame,
    *,
    row_id: str,
    data_provenance: str,
    design: pd.DataFrame,
    registration_pointer: str | None = None,
    labels: Sequence[str] = OUTPUT_LABELS,
    floor_seeds: Sequence[int] = DEFAULT_FLOOR_SEEDS,
    specification: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Table 6's twelve cells for one registered row, with uncertainty.

    ``rows`` is :func:`.evaluation.evaluate`'s person table (one row per
    person of the universe).  ``design`` (columns ``stratum`` and
    ``cluster``) is the sample design frame of the wave's positive-weight
    persons.  :func:`check_provenance` runs first; a ``registered_real``
    tabulation also refuses floor seeds other than the registered ones.
    Returns a JSON-serializable mapping; an undefined cell is reported
    with its reason, never raised.  Each defined cell's ``design_se``
    holds the standard error ``se`` in percentage points.
    """

    check_provenance(
        rows,
        data_provenance=data_provenance,
        registration_pointer=registration_pointer,
        labels=labels,
        specification=specification,
    )
    seeds = tuple(int(seed) for seed in floor_seeds)
    if len(set(seeds)) != len(seeds) or any(seed < 0 for seed in seeds):
        raise TrackMTabulationError("floor seeds must be distinct and >= 0")
    if data_provenance == REGISTERED_REAL and seeds != DEFAULT_FLOOR_SEEDS:
        raise TrackMTabulationError(
            f"a registered run uses the registered floor seeds "
            f"{list(DEFAULT_FLOOR_SEEDS)}, not {list(seeds)}"
        )
    normalized = _normalize(rows)
    clusters_all = _design_clusters(design)
    if clusters_all is None:
        raise TrackMTabulationError(
            "the design-based standard error needs the design frame"
        )
    present = pd.MultiIndex.from_frame(normalized[["stratum", "cluster"]])
    outside = present[~present.isin(clusters_all)].unique()
    if len(outside):
        raise TrackMTabulationError(
            f"{len(outside)} (stratum, cluster) pairs of the rows are not in "
            "the design frame"
        )
    floors, y3_floors, per_seed = _floors(normalized, seeds)
    cells = []
    for number in TABLE6_OPTIONS:
        indicator = normalized[f"receives_{number}"].to_numpy().astype(float)
        for row in TABLE6_ROWS:
            mask = _mask(normalized, row)
            entry: dict[str, Any] = {
                "option": number,
                "row": row,
                "headline": (number, row) == HEADLINE_CELL,
                "scored": True,
                **_share(normalized, mask, number),
            }
            if entry["defined"]:
                entry["design_se"] = _design_se(
                    normalized, mask, indicator, clusters_all
                )
            entry["floor"] = floors[f"{number}:{row}"]
            cells.append(entry)
    n_column = {
        row: {
            "unweighted": int(_mask(normalized, row).sum()),
            "weighted": math.fsum(
                normalized["weight"].to_numpy()[_mask(normalized, row)]
            ),
        }
        for row in TABLE6_ROWS
    }
    y3 = _y3(normalized, np.ones(len(normalized), dtype=bool))
    y3["floor"] = y3_floors
    y3["scored"] = False
    output_labels = [label for label in labels if label != INVENTED_DATA_LABEL]
    if data_provenance == INVENTED:
        output_labels.insert(0, INVENTED_DATA_LABEL)
    sizes = pd.Series(1, index=clusters_all).groupby(level=0).sum()
    return {
        "schema_version": SCHEMA_VERSION,
        "statistic_id": STATISTIC_ID,
        "row_id": row_id,
        "data_provenance": data_provenance,
        "registration_pointer": registration_pointer,
        "labels": output_labels,
        "disclosure": COVERED_EARNINGS_DISCLOSURE,
        "statistic": statistic_block(),
        "formula": FORMULA,
        "headline": {"option": HEADLINE_CELL[0], "row": HEADLINE_CELL[1]},
        "cells": cells,
        "n_column": {**n_column, "scored": False},
        "y3_option_3_women_to_men": y3,
        "uncertainty": {
            "registered": uncertainty_block(),
            "draws": 1,
            "floor_seeds": list(seeds),
            "floor_fraction": FLOOR_FRACTION,
            "floor_split_unit": FLOOR_SPLIT_UNIT,
            "min_floor_seeds": MIN_FLOOR_SEEDS,
            "design_se": {
                "method": "taylor_linearization",
                "domain": "full_sample_design",
                "stratum": "ER31996",
                "cluster": "ER31997",
                "n_strata": int(len(sizes)),
                "n_clusters": int(sizes.sum()),
                "singleton_strata": [int(s) for s in sizes[sizes < 2].index],
            },
            "floor_per_seed": per_seed,
        },
        "input_summary": {
            "n_persons": int(len(normalized)),
            "n_family_units": int(normalized["family_unit_id"].nunique()),
            "sex": {
                str(key): int(value)
                for key, value in normalized["sex"]
                .value_counts()
                .sort_index()
                .items()
            },
        },
    }
