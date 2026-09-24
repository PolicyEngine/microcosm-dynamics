"""Frozen-statistic tabulation for DynaSim scorecard exercise 2 (Track U).

Exercise 2 is the change in the adjusted poverty rate at age 67 when all
Social Security benefits are cut by 13 percent, for the 1936-45 birth
cohort (plan ``critical-path-uniform-cut-20260923.md``, work item U7).
This module takes one row per cohort-member observation that already
carries baseline and reform poverty status (from
:func:`populace_dynamics.estimates.adjusted_poverty.adjusted_incomes`) and
reduces it to the registered cells.  It computes no income, reads no
comparator value, applies no acceptance rule and writes no artifact.

Statistic (plan section 7), per cell ``c`` with observation weights
``w_i``::

    P_B = 100 * sum_{i in c} w_i 1{B_i < T_i} / sum_{i in c} w_i
    P_R = 100 * sum_{i in c} w_i 1{R_i < T_i} / sum_{i in c} w_i
    delta = P_R - P_B   (percentage points)

``delta`` is the headline; ``P_B`` and ``P_R`` are the secondary rows
(the Table 19 and Table 21 analogues).  Cells: ``all`` (headline),
``men``, ``women``, ``married`` and ``non_married`` (the reporting
splits the plan reads in the Report's methods, plan section 7), the four
sex-by-marital cells (optional) and one diagnostic cell per birth year
(not scored).  An empty cell, or one with
zero total weight, is undefined and reported with its reason, never
imputed.

Uncertainty (plan field F15; the run is deterministic, K = 1):

* **Half-split floor.**  For each of five seeds (0-4),
  :func:`populace_dynamics.harness.panel.split_panel_by_person` with
  ``fraction=0.5`` splits the split units (:func:`floor_split_units`) into
  two disjoint halves.  A split unit is a family unit
  (``family_unit_id``) merged with every other family unit that shares a
  person with it, so the halves are disjoint in family units *and* in
  persons (plan F15, "person-disjoint half-split floor on the family
  unit").  Under row U0 each person is observed once and the split units
  are the family units themselves; under row U1 an even birth year's
  observations at 66 and 68 sit in two waves' family units, which the
  merge keeps on one side.  Each
  statistic is recomputed in each half; the floor is the mean, sample SD
  (``ddof=1``), min and max of ``|side_a - side_b|`` over the seeds where
  both halves are defined.  With fewer than two usable seeds the floor is
  undefined, never zero (the exercise-1 convention of
  :mod:`populace_dynamics.estimates.cola_age_profile`).  Floors are at
  half sample and are not rescaled.
* **Design-based standard error.**  Taylor linearization of the weighted
  ratio with the PSID sampling-error stratum and cluster (ER31996,
  ER31997): ``z_i = w_i (y_i - r) / sum w`` inside the cell and 0 outside
  it, summed by cluster; ``var = sum_h n_h/(n_h - 1) sum_c (z_hc -
  mean_h)^2``.  ``design_se_domain="full_sample_design"`` (default, the
  specification's section 10 after the referee's Q5): a domain estimator
  on the full sample design, where every (stratum, cluster) pair of the
  ``design`` frame (the pairs of persons with a positive cross-section
  weight in the observation waves) enters, with ``z = 0`` for a cluster
  that holds no observation of the cell; a row whose pair is not in the
  frame is refused.  ``tabulated_rows`` (the u1-draft-3 estimator) uses
  only the pairs present in the input rows.  Strata with a single
  cluster cannot contribute a variance term: they are left out, counted
  and listed.

Provenance: ``data_provenance="invented"`` prefixes the invented-data
label; ``"registered_real"`` requires the issue #42 registration pointer,
refuses the invented label and requires rows marked as built from staged
PSID files (``rows.attrs["provenance_kind"] == "psid_files"``, which
:func:`tabulation_rows` carries); such rows cannot be tabulated as
invented.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.estimates.adjusted_poverty import (
    DATA_PROVENANCES,
    INVENTED,
    OUTPUT_LABELS,
    REGISTERED_REAL,
    PendingDecision,
)
from populace_dynamics.harness.panel import split_panel_by_person

__all__ = [
    "CELL_DEFINITIONS",
    "DEFAULT_CELLS",
    "DESIGN_SE_DOMAINS",
    "DEFAULT_FLOOR_SEEDS",
    "DIAGNOSTIC_BIRTH_YEAR_CELLS",
    "FLOOR_FRACTION",
    "FLOOR_SPLIT_UNIT",
    "INVENTED_DATA_LABEL",
    "MIN_FLOOR_SEEDS",
    "OPTIONAL_CELLS",
    "REQUIRED_COLUMNS",
    "SCHEMA_VERSION",
    "STATISTICS",
    "STATISTIC_ID",
    "TabulationConfig",
    "UniformCutTabulationError",
    "floor_split_units",
    "pending_decisions",
    "tabulate_uniform_cut",
    "tabulation_rows",
]

SCHEMA_VERSION = "populace_dynamics.uniform_cut_tabulation.v1"
STATISTIC_ID = (
    "dynasim_exercise2_uniform_13pct_cut_adjusted_poverty_at_67_1936_45"
)
INVENTED_DATA_LABEL = "INVENTED DATA - not PSID, not a result"

REQUIRED_COLUMNS: tuple[str, ...] = (
    "observation_id",
    "person_id",
    "family_unit_id",
    "weight",
    "sex",
    "married",
    "birth_year",
    "stratum",
    "cluster",
    "poor_baseline",
    "poor_reform",
)

STATISTICS: tuple[str, ...] = ("delta", "baseline_rate", "reform_rate")
STATISTIC_DEFINITIONS = {
    "delta": "reform_rate - baseline_rate (percentage points)",
    "baseline_rate": ("100 * sum w 1{B < T} / sum w (the Table 19 analogue)"),
    "reform_rate": "100 * sum w 1{R < T} / sum w (the Table 21 analogue)",
}

CELL_DEFINITIONS: dict[str, str] = {
    "all": "every observation (headline)",
    "men": "sex == male",
    "women": "sex == female",
    "married": "legally married at the end of the income year (F12)",
    "non_married": "not legally married (cohabitors included, F12)",
    "men_married": "optional: male and married",
    "men_non_married": "optional: male and not married",
    "women_married": "optional: female and married",
    "women_non_married": "optional: female and not married",
}
DEFAULT_CELLS: tuple[str, ...] = (
    "all",
    "men",
    "women",
    "married",
    "non_married",
)
OPTIONAL_CELLS: tuple[str, ...] = (
    "men_married",
    "men_non_married",
    "women_married",
    "women_non_married",
)
#: Diagnostic cells, one per birth year present (not scored).
DIAGNOSTIC_BIRTH_YEAR_CELLS = "birth_year_<yyyy>"

DEFAULT_FLOOR_SEEDS: tuple[int, ...] = (0, 1, 2, 3, 4)
FLOOR_FRACTION = 0.5
MIN_FLOOR_SEEDS = 2
#: The half-split unit: family units merged through shared persons
#: (:func:`floor_split_units`).
FLOOR_SPLIT_UNIT = "family_unit_id_linked_by_person_id"
#: The population of clusters the design-based standard error sums over.
DESIGN_SE_DOMAINS: dict[str, str] = {
    "full_sample_design": (
        "domain estimation on the full sample design: every (stratum, "
        "cluster) pair of the design frame enters, z = 0 for clusters "
        "without an observation of the cell (referee Q5)"
    ),
    "tabulated_rows": (
        "the (stratum, cluster) pairs present in the tabulated rows only "
        "(u1-draft-3)"
    ),
}


class UniformCutTabulationError(ValueError):
    """The rows or configuration cannot yield the frozen statistic."""


@dataclass(frozen=True)
class TabulationConfig:
    """Cells and uncertainty settings; defaults are the plan's proposal."""

    cells: tuple[str, ...] = DEFAULT_CELLS + OPTIONAL_CELLS
    birth_year_diagnostics: bool = True
    floor_seeds: tuple[int, ...] = DEFAULT_FLOOR_SEEDS
    design_standard_errors: bool = True
    design_se_domain: str = "full_sample_design"
    notes: tuple[str, ...] = field(default=())

    def __post_init__(self) -> None:
        unknown = set(self.cells) - set(CELL_DEFINITIONS)
        if unknown:
            raise UniformCutTabulationError(f"unknown cells {sorted(unknown)}")
        if "all" not in self.cells:
            raise UniformCutTabulationError(
                "the headline cell 'all' is needed"
            )
        seeds = tuple(int(seed) for seed in self.floor_seeds)
        if len(set(seeds)) != len(seeds) or any(seed < 0 for seed in seeds):
            raise UniformCutTabulationError(
                "floor seeds must be distinct >= 0"
            )
        if self.design_se_domain not in DESIGN_SE_DOMAINS:
            raise UniformCutTabulationError(
                f"design_se_domain must be one of {sorted(DESIGN_SE_DOMAINS)}"
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "cells": list(self.cells),
            "birth_year_diagnostics": self.birth_year_diagnostics,
            "floor_seeds": list(self.floor_seeds),
            "floor_fraction": FLOOR_FRACTION,
            "floor_split_unit": FLOOR_SPLIT_UNIT,
            "min_floor_seeds": MIN_FLOOR_SEEDS,
            "design_standard_errors": self.design_standard_errors,
            "design_se_domain": self.design_se_domain,
            "draws": 1,
            "notes": list(self.notes),
        }


def _finite(value: float, what: str) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise UniformCutTabulationError(f"non-finite {what}")
    return value


def _normalize(rows: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(rows, pd.DataFrame):
        raise UniformCutTabulationError("rows must be a DataFrame")
    if rows.columns.duplicated().any():
        raise UniformCutTabulationError("repeated column names")
    missing = [c for c in REQUIRED_COLUMNS if c not in rows.columns]
    if missing:
        raise UniformCutTabulationError(f"rows lack columns {missing}")
    out = rows[list(REQUIRED_COLUMNS)].reset_index(drop=True).copy()
    if out.empty:
        raise UniformCutTabulationError("no rows")
    if out["observation_id"].duplicated().any():
        raise UniformCutTabulationError("duplicate observation_id")
    weight = pd.to_numeric(out["weight"], errors="raise").astype("float64")
    if not np.all(np.isfinite(weight)) or (weight < 0).any():
        raise UniformCutTabulationError("weights must be finite and >= 0")
    out["weight"] = weight
    sexes = set(out["sex"].astype(str))
    if not sexes <= {"male", "female"}:
        raise UniformCutTabulationError(f"sex outside male/female: {sexes}")
    for column in ("married", "poor_baseline", "poor_reform"):
        values = out[column]
        if (
            values.isna().any()
            or not values.map(lambda v: isinstance(v, bool | np.bool_)).all()
        ):
            raise UniformCutTabulationError(f"{column} must be boolean")
        out[column] = values.astype(bool)
    identifiers = ["person_id", "stratum", "cluster", "family_unit_id"]
    if out[identifiers].isna().any().any():
        raise UniformCutTabulationError(
            "person_id, stratum, cluster and family_unit_id must be present"
        )
    out["birth_year"] = out["birth_year"].astype("int64")
    for column in ("stratum", "cluster"):
        out[column] = out[column].astype("int64")
    return out


def _cell_masks(rows: pd.DataFrame, config: TabulationConfig) -> dict:
    male = rows["sex"].eq("male").to_numpy()
    married = rows["married"].to_numpy()
    masks = {
        "all": np.ones(len(rows), dtype=bool),
        "men": male,
        "women": ~male,
        "married": married,
        "non_married": ~married,
        "men_married": male & married,
        "men_non_married": male & ~married,
        "women_married": ~male & married,
        "women_non_married": ~male & ~married,
    }
    out = {name: masks[name] for name in config.cells}
    if config.birth_year_diagnostics:
        for year in sorted(set(rows["birth_year"].tolist())):
            out[f"birth_year_{year}"] = rows["birth_year"].eq(year).to_numpy()
    return out


def _rates(rows: pd.DataFrame, mask: np.ndarray) -> dict[str, Any]:
    weight = rows["weight"].to_numpy()[mask]
    total = float(weight.sum())
    if not mask.any():
        return {"defined": False, "undefined_reason": "empty cell"}
    if total <= 0:
        return {"defined": False, "undefined_reason": "zero total weight"}
    base = rows["poor_baseline"].to_numpy()[mask]
    reform = rows["poor_reform"].to_numpy()[mask]
    baseline_rate = _finite(
        100.0 * math.fsum(weight[base]) / total, "baseline rate"
    )
    reform_rate = _finite(
        100.0 * math.fsum(weight[reform]) / total, "reform rate"
    )
    return {
        "defined": True,
        "undefined_reason": None,
        "baseline_rate": baseline_rate,
        "reform_rate": reform_rate,
        "delta": reform_rate - baseline_rate,
    }


def _design_clusters(design: pd.DataFrame | None) -> pd.MultiIndex | None:
    """The distinct (stratum, cluster) pairs of a design frame."""

    if design is None:
        return None
    if not isinstance(design, pd.DataFrame):
        raise UniformCutTabulationError("design must be a DataFrame")
    missing = [c for c in ("stratum", "cluster") if c not in design.columns]
    if missing:
        raise UniformCutTabulationError(f"design lacks columns {missing}")
    pairs = design[["stratum", "cluster"]]
    if pairs.isna().any().any():
        raise UniformCutTabulationError("design stratum/cluster missing")
    pairs = pairs.astype("int64").drop_duplicates()
    if pairs.empty:
        raise UniformCutTabulationError("the design frame has no clusters")
    return pd.MultiIndex.from_frame(pairs.sort_values(["stratum", "cluster"]))


def _design_se(
    rows: pd.DataFrame,
    mask: np.ndarray,
    indicator: np.ndarray,
    clusters_all: pd.MultiIndex | None = None,
) -> dict[str, Any]:
    weight = rows["weight"].to_numpy()
    in_cell = weight * mask
    total = float(in_cell.sum())
    if total <= 0:
        return {"se": None, "n_strata": 0, "n_singleton_strata": 0}
    ratio = float(np.sum(in_cell * indicator)) / total
    z = in_cell * (indicator - ratio) / total
    frame = pd.DataFrame(
        {"stratum": rows["stratum"], "cluster": rows["cluster"], "z": z}
    )
    clusters = frame.groupby(["stratum", "cluster"], sort=True)["z"].sum()
    if clusters_all is not None:
        clusters = clusters.reindex(clusters_all, fill_value=0.0)
    variance = 0.0
    used = 0
    singleton = 0
    for _, values in clusters.groupby(level=0, sort=True):
        n = len(values)
        if n < 2:
            singleton += 1
            continue
        used += 1
        centered = values.to_numpy() - values.mean()
        variance += n / (n - 1) * float(np.sum(centered**2))
    return {
        "se": _finite(100.0 * math.sqrt(variance), "design SE"),
        "n_strata": used,
        "n_singleton_strata": singleton,
    }


def _cell_entry(
    rows: pd.DataFrame,
    name: str,
    mask: np.ndarray,
    config: TabulationConfig,
    clusters_all: pd.MultiIndex | None = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "cell": name,
        "definition": CELL_DEFINITIONS.get(
            name, "diagnostic: birth year (not scored)"
        ),
        "scored_candidate": name in DEFAULT_CELLS,
        "optional": name in OPTIONAL_CELLS,
        "diagnostic": name.startswith("birth_year_"),
        "n_observations": int(mask.sum()),
        "n_persons": int(rows.loc[mask, "person_id"].nunique()),
        "n_family_units": int(rows.loc[mask, "family_unit_id"].nunique()),
        "weight_total": _finite(
            math.fsum(rows["weight"].to_numpy()[mask]), "weight total"
        ),
        **_rates(rows, mask),
    }
    if entry["defined"] and config.design_standard_errors:
        base = rows["poor_baseline"].to_numpy().astype(np.float64)
        reform = rows["poor_reform"].to_numpy().astype(np.float64)
        entry["design_se"] = {
            "delta": _design_se(rows, mask, reform - base, clusters_all),
            "baseline_rate": _design_se(rows, mask, base, clusters_all),
            "reform_rate": _design_se(rows, mask, reform, clusters_all),
        }
    return entry


def _floor_summary(values: list[float]) -> dict[str, Any]:
    gaps = [_finite(v, "floor gap") for v in values]
    if len(gaps) < MIN_FLOOR_SEEDS:
        return {
            "defined": False,
            "undefined_reason": (
                "no usable seed"
                if not gaps
                else f"fewer than {MIN_FLOOR_SEEDS} usable seeds"
            ),
            "mean": None,
            "sd": None,
            "min": None,
            "max": None,
            "n_seeds": len(gaps),
            "values": gaps,
        }
    arr = np.asarray(gaps, dtype=np.float64)
    return {
        "defined": True,
        "undefined_reason": None,
        "mean": _finite(arr.mean(), "floor mean"),
        "sd": _finite(arr.std(ddof=1), "floor sd"),
        "min": _finite(arr.min(), "floor min"),
        "max": _finite(arr.max(), "floor max"),
        "n_seeds": int(arr.size),
        "values": gaps,
    }


def floor_split_units(rows: pd.DataFrame) -> np.ndarray:
    """The half-split unit of each row: family units linked by persons.

    Family units that share a person (directly or through a chain of
    persons) form one split unit, labelled by its smallest
    ``family_unit_id``.  When every person sits in one family unit (row
    U0) the split units are the family units, so the split is the plain
    family-unit split.
    """

    families = rows["family_unit_id"].tolist()
    persons = rows["person_id"].tolist()
    parent: dict[Any, Any] = {unit: unit for unit in families}

    def root(unit: Any) -> Any:
        while parent[unit] != unit:
            parent[unit] = parent[parent[unit]]
            unit = parent[unit]
        return unit

    first_unit: dict[Any, Any] = {}
    for person, unit in zip(persons, families, strict=True):
        if person not in first_unit:
            first_unit[person] = unit
            continue
        a, b = root(first_unit[person]), root(unit)
        if a != b:
            low, high = sorted((a, b))
            parent[high] = low
    return np.asarray([root(unit) for unit in families])


def _floors(
    rows: pd.DataFrame, masks: dict[str, np.ndarray], config: TabulationConfig
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    units = pd.DataFrame({"split_unit": floor_split_units(rows)})
    per_seed = []
    for seed in config.floor_seeds:
        side_a, _ = split_panel_by_person(
            units, "split_unit", fraction=FLOOR_FRACTION, seed=int(seed)
        )
        in_a = np.zeros(len(rows), dtype=bool)
        in_a[side_a.index.to_numpy()] = True
        per_seed.append(
            {
                "seed": int(seed),
                "side_a": {
                    name: _rates(rows, mask & in_a)
                    for name, mask in masks.items()
                },
                "side_b": {
                    name: _rates(rows, mask & ~in_a)
                    for name, mask in masks.items()
                },
            }
        )
    floors: dict[str, dict[str, Any]] = {}
    for name in masks:
        entry: dict[str, Any] = {}
        for statistic in STATISTICS:
            gaps, dropped = [], []
            for row in per_seed:
                a, b = row["side_a"][name], row["side_b"][name]
                if a["defined"] and b["defined"]:
                    gaps.append(abs(a[statistic] - b[statistic]))
                else:
                    dropped.append(row["seed"])
            entry[statistic] = {
                **_floor_summary(gaps),
                "dropped_seeds": dropped,
            }
        floors[name] = entry
    return per_seed, floors


def pending_decisions() -> tuple[PendingDecision, ...]:
    """The open choices of :class:`TabulationConfig`, with their defaults.

    None is ratified; each awaits the specification freeze (or, for the
    cells, plan section 10 decision 2(b)).
    """

    config = TabulationConfig()
    freeze = "U1 specification freeze (Max's ratification by merge)"
    return (
        PendingDecision(
            "design_se_domain",
            config.design_se_domain,
            ("tabulated_rows",),
            "referee (boomers2004-referee-20260924.md) Q5/R10: domain "
            "estimation on the full sample design, every (stratum, "
            "cluster) pair of the observation waves' positive-weight "
            "persons with z = 0 outside the cell; relative to the "
            "tabulated rows only, every stratum with one cluster present "
            "drops out and the variance is understated",
            freeze,
        ),
        PendingDecision(
            "cells",
            list(config.cells),
            (),
            "plan section 7: all (headline), men, women, married, "
            "non_married (the Report's list of appendix tables names "
            "Appendix Table 17 'by Gender and Marital Status') and the "
            "four optional sex-by-marital cells; which splits Tables 19 "
            "and 21 carry is unknown",
            "Max (plan section 10 decision 2(b)) and the specification "
            "freeze",
        ),
    )


def tabulation_rows(
    members: pd.DataFrame, adjusted: pd.DataFrame
) -> pd.DataFrame:
    """Join member observations to their baseline and reform poverty flags.

    ``members`` holds the observation columns of :data:`REQUIRED_COLUMNS`
    other than the two flags (for example
    :func:`populace_dynamics.cohorts.age67.income_rows`); ``adjusted`` is
    :func:`populace_dynamics.estimates.adjusted_poverty.adjusted_incomes`
    output.  The join is one-to-one on ``observation_id`` and refuses a
    row on either side without a partner.  The provenance kind of either
    input (``attrs["provenance_kind"]``) is carried to the result, a
    ``psid_files`` kind winning, so the tabulation guard still sees it.
    """

    flags = ["observation_id", "poor_baseline", "poor_reform"]
    needed = [c for c in REQUIRED_COLUMNS if c not in flags[1:]]
    missing = [c for c in needed if c not in members.columns]
    if missing:
        raise UniformCutTabulationError(f"members lack columns {missing}")
    if set(members["observation_id"]) != set(adjusted["observation_id"]):
        raise UniformCutTabulationError(
            "members and adjusted incomes cover different observations"
        )
    out = members[needed].merge(
        adjusted[flags], on="observation_id", how="inner", validate="1:1"
    )
    kinds = {
        members.attrs.get("provenance_kind"),
        adjusted.attrs.get("provenance_kind"),
    }
    out.attrs["provenance_kind"] = (
        "psid_files"
        if "psid_files" in kinds
        else next((kind for kind in kinds if kind), None)
    )
    return out


def tabulate_uniform_cut(
    rows: pd.DataFrame,
    *,
    data_provenance: str,
    config: TabulationConfig | None = None,
    registration_pointer: str | None = None,
    labels: Sequence[str] = OUTPUT_LABELS,
    upstream_spec: dict[str, Any] | None = None,
    pending_decisions: Sequence[dict[str, Any]] = (),
    design: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Tabulate the exercise-2 statistic from per-observation rows.

    ``rows`` has the columns of :data:`REQUIRED_COLUMNS` (extra columns are
    ignored).  ``upstream_spec`` (the income-concept specification that
    produced the poverty flags) and ``pending_decisions`` are recorded
    verbatim.  ``design`` (columns ``stratum`` and ``cluster``) is the
    sample design the ``full_sample_design`` standard error sums over; it
    is required when design standard errors use that domain.  Returns a
    JSON-serializable mapping; an undefined cell is reported with its
    reason, never raised.
    """

    config = TabulationConfig() if config is None else config
    if not isinstance(config, TabulationConfig):
        raise UniformCutTabulationError("config must be a TabulationConfig")
    if data_provenance not in DATA_PROVENANCES:
        raise UniformCutTabulationError(
            f"data_provenance must be one of {DATA_PROVENANCES}"
        )
    if isinstance(labels, str):
        raise UniformCutTabulationError("labels must be a sequence")
    labels = tuple(labels)
    if not all(isinstance(label, str) and label for label in labels):
        raise UniformCutTabulationError("labels must be non-empty strings")
    missing_labels = [label for label in OUTPUT_LABELS if label not in labels]
    if missing_labels:
        raise UniformCutTabulationError(
            f"every output carries the Track U labels; missing "
            f"{missing_labels}"
        )
    if data_provenance == REGISTERED_REAL:
        if not isinstance(registration_pointer, str) or not (
            registration_pointer.strip()
        ):
            raise UniformCutTabulationError(
                "real-data tabulation requires the issue #42 registration "
                "pointer, which must exist before the run"
            )
        if INVENTED_DATA_LABEL in labels:
            raise UniformCutTabulationError(
                "a registered_real result cannot carry the invented label"
            )
        kind = (
            rows.attrs.get("provenance_kind")
            if isinstance(rows, pd.DataFrame)
            else None
        )
        if kind != "psid_files":
            raise UniformCutTabulationError(
                f"data_provenance 'registered_real' contradicts the rows' "
                f"provenance {kind!r}: a registered run tabulates rows built "
                "from recorded PSID files (age67.income_rows through "
                "tabulation_rows)"
            )
    elif isinstance(rows, pd.DataFrame) and (
        rows.attrs.get("provenance_kind") == "psid_files"
    ):
        raise UniformCutTabulationError(
            "rows built from staged PSID files cannot be tabulated as "
            "invented data"
        )
    normalized = _normalize(rows)
    masks = _cell_masks(normalized, config)
    clusters_all = None
    design_summary: dict[str, Any] = {"domain": config.design_se_domain}
    if config.design_standard_errors:
        if config.design_se_domain == "full_sample_design":
            clusters_all = _design_clusters(design)
            if clusters_all is None:
                raise UniformCutTabulationError(
                    "the full_sample_design standard error needs the "
                    "design frame (every stratum and cluster of the "
                    "observation waves' positive-weight persons)"
                )
            present = pd.MultiIndex.from_frame(
                normalized[["stratum", "cluster"]].astype("int64")
            )
            outside = present[~present.isin(clusters_all)].unique()
            if len(outside):
                raise UniformCutTabulationError(
                    f"{len(outside)} (stratum, cluster) pairs of the rows "
                    f"are not in the design frame (first: {list(outside)[:3]})"
                )
            sizes = pd.Series(1, index=clusters_all).groupby(level=0).sum()
        else:
            sizes = (
                normalized[["stratum", "cluster"]]
                .drop_duplicates()
                .groupby("stratum")["cluster"]
                .count()
            )
        design_summary.update(
            n_strata=int(len(sizes)),
            n_clusters=int(sizes.sum()),
            singleton_strata=[int(s) for s in sizes[sizes < 2].index],
        )
    elif design is not None:
        _design_clusters(design)
    cells = [
        _cell_entry(normalized, name, mask, config, clusters_all)
        for name, mask in masks.items()
    ]
    per_seed, floors = _floors(normalized, masks, config)
    for entry in cells:
        entry["floor"] = floors[entry["cell"]]
    undefined = [
        {"cell": entry["cell"], "reason": entry["undefined_reason"]}
        for entry in cells
        if not entry["defined"]
    ]
    output_labels = [label for label in labels if label != INVENTED_DATA_LABEL]
    if data_provenance == INVENTED:
        output_labels.insert(0, INVENTED_DATA_LABEL)
    return {
        "schema_version": SCHEMA_VERSION,
        "statistic_id": STATISTIC_ID,
        "data_provenance": data_provenance,
        "registration_pointer": registration_pointer,
        "labels": output_labels,
        "config": config.as_dict(),
        "statistic_definitions": dict(STATISTIC_DEFINITIONS),
        "upstream_spec": dict(upstream_spec or {}),
        "pending_decisions": [dict(item) for item in pending_decisions],
        "design": design_summary,
        "input_summary": {
            "n_observations": int(len(normalized)),
            "n_persons": int(normalized["person_id"].nunique()),
            "n_family_units": int(normalized["family_unit_id"].nunique()),
            "n_zero_weight": int((normalized["weight"] == 0).sum()),
        },
        "cells": cells,
        "undefined_cells": undefined,
        "floor_per_seed": per_seed,
    }
