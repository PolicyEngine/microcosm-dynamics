"""The U2 frozen-statistic tabulation, under U2's own identity.

Specification sections 9, 10 and 14 ("Tabulation identity: preserve U1
``COMPARATOR_COLUMN`` at ``S/estimates/uniform_cut_tabulation.py:159``;
provide separate U2 identity").  The statistic, cells, uncertainty and
undefined-cell rules are U1's; this module reuses U1's computation
helpers from :mod:`populace_dynamics.estimates.uniform_cut_tabulation`
unchanged and supplies the U2 identity around them:

* ``schema_version``, ``statistic_id`` and ``comparator_column``
  (``1946-55``) are U2's, and U1's are refused;
* the cells are the fifteen of section 9 (``all`` headline; six scored;
  eight secondary) with the Report row labels of the cleared U2
  statement, plus unscored birth-year diagnostics;
* the design frame must satisfy the documented domains (see
  :func:`populace_dynamics.uniform_cut_track_u2.cohort.design_frame`);
  singleton strata are excluded, counted and listed;
* the half-split floor uses U1's split implementation (family units
  linked transitively by persons, labelled by the smallest family unit,
  seeds 0-4, fraction 0.5, mean and ``ddof=1`` SD, at least two usable
  seeds), never rescaled;
* rows must carry ``attrs["target_id"] == "U2"``; provenance guards are
  U1's.

It computes no income, reads no comparator value and applies no
acceptance rule.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from populace_dynamics.estimates import adjusted_poverty as ap
from populace_dynamics.estimates import uniform_cut_tabulation as ut
from populace_dynamics.uniform_cut_track_u2 import identity

__all__ = [
    "CELL_DEFINITIONS",
    "COMPARATOR_COLUMN",
    "DEFAULT_CELLS",
    "NOT_COMPUTED_REPORT_ROWS",
    "OPTIONAL_CELLS",
    "REPORT_ROWS",
    "SCHEMA_VERSION",
    "STATISTIC_ID",
    "U2TabulationConfig",
    "U2TabulationError",
    "tabulate_u2",
    "tabulation_rows",
]

SCHEMA_VERSION = "populace_dynamics.uniform_cut_tabulation_u2.v1"
STATISTIC_ID = identity.STATISTIC_ID
COMPARATOR_COLUMN = identity.COMPARATOR_COLUMN
#: The fifteen cells and their Report rows (section 9; the cleared U2
#: statement lists the same Total, Gender, Marital Status and Gender x
#: Marital rows as U1's column).
REPORT_ROWS: dict[str, str] = dict(ut.REPORT_ROWS)
DEFAULT_CELLS: tuple[str, ...] = ut.DEFAULT_CELLS
OPTIONAL_CELLS: tuple[str, ...] = ut.OPTIONAL_CELLS
CELL_DEFINITIONS: dict[str, str] = dict(ut.CELL_DEFINITIONS)
#: Section 9: the twenty-one Report rows U2 does not compute, as named
#: omissions.  The sections and row labels are the Report's (as U1 lists
#: them); the reason is U2's own -- U1's old-cohort age-22 rationale is
#: not carried over.
NOT_COMPUTED_REPORT_ROWS: dict[str, dict[str, Any]] = {
    key: {
        "section": entry["section"],
        "rows": tuple(entry["rows"]),
        "reason": (
            "named omission: the classification work for this row group "
            "is outside the U2 extension (section 9)"
        ),
    }
    for key, entry in ut.NOT_COMPUTED_REPORT_ROWS.items()
}
INVENTED_DATA_LABEL = "INVENTED DATA - NOT A COMPARISON"


class U2TabulationError(ValueError):
    """The rows or configuration cannot yield the U2 statistic."""


@dataclass(frozen=True)
class U2TabulationConfig:
    """Cells and uncertainty settings (section 9-10 values only)."""

    cells: tuple[str, ...] = DEFAULT_CELLS + OPTIONAL_CELLS
    unclassified_marital_cells: str = "excluded_counted"
    birth_year_diagnostics: bool = True
    floor_seeds: tuple[int, ...] = ut.DEFAULT_FLOOR_SEEDS
    design_standard_errors: bool = True
    design_se_domain: str = "full_sample_design"
    comparator_column: str = COMPARATOR_COLUMN
    target_id: str = identity.TARGET_ID
    notes: tuple[str, ...] = field(default=())

    def __post_init__(self) -> None:
        identity.check_target(self.target_id, "U2TabulationConfig")
        identity.refuse_u1_identity(
            {"comparator_column": self.comparator_column},
            what="U2TabulationConfig",
        )
        if self.comparator_column != COMPARATOR_COLUMN:
            raise U2TabulationError(f"the U2 column is {COMPARATOR_COLUMN!r}")
        if tuple(self.cells) != DEFAULT_CELLS + OPTIONAL_CELLS:
            raise U2TabulationError(
                "U2 tabulates exactly the fifteen section 9 cells"
            )
        if self.unclassified_marital_cells != "excluded_counted":
            raise U2TabulationError("unclassified members: excluded_counted")
        if tuple(self.floor_seeds) != ut.DEFAULT_FLOOR_SEEDS:
            raise U2TabulationError("the floor seeds are 0-4 (section 10)")
        if self.design_se_domain != "full_sample_design":
            raise U2TabulationError(
                "the design SE uses the full sample design (section 10)"
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "cells": list(self.cells),
            "comparator_column": self.comparator_column,
            "unclassified_marital_cells": self.unclassified_marital_cells,
            "birth_year_diagnostics": self.birth_year_diagnostics,
            "floor_seeds": list(self.floor_seeds),
            "floor_fraction": ut.FLOOR_FRACTION,
            "floor_split_unit": ut.FLOOR_SPLIT_UNIT,
            "min_floor_seeds": ut.MIN_FLOOR_SEEDS,
            "design_standard_errors": self.design_standard_errors,
            "design_se_domain": self.design_se_domain,
            "draws": 1,
            "notes": list(self.notes),
        }


def tabulation_rows(
    members: pd.DataFrame, adjusted: pd.DataFrame
) -> pd.DataFrame:
    """U1's one-to-one join, keeping the U2 target identity."""

    for what, frame in (("members", members), ("adjusted", adjusted)):
        identity.check_target(frame.attrs.get("target_id"), what)
    try:
        out = ut.tabulation_rows(members, adjusted)
    except ut.UniformCutTabulationError as error:
        raise U2TabulationError(str(error)) from error
    out.attrs["target_id"] = identity.TARGET_ID
    return out


def tabulate_u2(
    rows: pd.DataFrame,
    *,
    data_provenance: str,
    design: pd.DataFrame,
    config: U2TabulationConfig | None = None,
    registration_pointer: str | None = None,
    upstream_spec: dict[str, Any] | None = None,
    pending_decisions: Sequence[dict[str, Any]] = (),
) -> dict[str, Any]:
    """Tabulate the U2 statistic from per-observation rows.

    The computation is U1's :func:`~populace_dynamics.estimates.
    uniform_cut_tabulation.tabulate_uniform_cut` (run with U1's default
    configuration, which has the same cells, seeds and design domain); the
    returned mapping replaces U1's identity fields with U2's and records
    the U2 configuration.
    """

    config = U2TabulationConfig() if config is None else config
    if not isinstance(config, U2TabulationConfig):
        raise U2TabulationError("config must be a U2TabulationConfig")
    identity.check_target(rows.attrs.get("target_id"), "the tabulation rows")
    labels = list(ap.OUTPUT_LABELS)
    try:
        result = ut.tabulate_uniform_cut(
            rows,
            data_provenance=data_provenance,
            config=ut.TabulationConfig(
                cells=config.cells,
                unclassified_marital_cells=config.unclassified_marital_cells,
                birth_year_diagnostics=config.birth_year_diagnostics,
                floor_seeds=config.floor_seeds,
                design_standard_errors=config.design_standard_errors,
                design_se_domain=config.design_se_domain,
            ),
            registration_pointer=registration_pointer,
            labels=labels,
            upstream_spec=upstream_spec,
            pending_decisions=pending_decisions,
            design=design,
        )
    except ut.UniformCutTabulationError as error:
        raise U2TabulationError(str(error)) from error
    # Section 10a: a cell where nobody changes poverty status is a
    # no-switcher cell; the memo reports its change uncertainty as not
    # estimable, so each cell records how many observations switch.
    switched = (
        rows["poor_baseline"].astype(bool).to_numpy()
        != rows["poor_reform"].astype(bool).to_numpy()
    )
    for cell in result["cells"]:
        name = cell["cell"]
        if name.startswith("birth_year_"):
            mask = (
                rows["birth_year"]
                .astype("int64")
                .eq(int(name.removeprefix("birth_year_")))
                .to_numpy()
            )
        else:
            mask = ut.cell_mask(rows, name)
        cell["n_switchers"] = int((mask & switched).sum())
    result_labels = [
        label for label in result["labels"] if label != ut.INVENTED_DATA_LABEL
    ]
    if data_provenance == ap.INVENTED:
        result_labels.insert(0, INVENTED_DATA_LABEL)
    return {
        **result,
        "schema_version": SCHEMA_VERSION,
        "statistic_id": STATISTIC_ID,
        "target_id": identity.TARGET_ID,
        "labels": result_labels,
        "config": config.as_dict(),
    }
