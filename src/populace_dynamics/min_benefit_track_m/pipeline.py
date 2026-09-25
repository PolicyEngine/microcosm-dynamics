"""Track M end to end: every registered row, after the guards (plan M10).

Python rules (not Axiom).  :func:`run_track_m` takes the records
(:class:`~.evaluation.TrackMInputs`, from the M4 cohort and M5 careers on
real data, not built, or from :mod:`.invented`) and the parameters, and
for each registered row MS0-MS6 evaluates every record under the row's
policy (:mod:`.evaluation`) and tabulates Table 6's twelve cells with
their uncertainty (:mod:`.tabulation`).  Before computing anything it:

* refuses a provenance the tabulation would refuse
  (:func:`.tabulation.check_provenance`): PSID-built records need
  ``registered_real``, the issue #42 comment pointer and an M1
  specification the registered-run gate authorizes;
* refuses, for ``registered_real``, anything but every registered row in
  order (MS0-MS6: each reports all 12 cells, section 14) and the
  registered floor seeds; and
* refuses a cohort that needs a threshold year the Census capture lacks
  (referee R8): :func:`.evaluation.needed_threshold_years` over every
  row's policy, then :func:`.rules.check_threshold_years`, which raises
  :class:`.rules.ThresholdYearMissingError`.

The result records the rulings (:data:`.policy.MAX_RULINGS`), the frozen
choices, the parameters' provenance, the labels and the covered-earnings
disclosure (d280).  Nothing here reads a file or a comparator value.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd

from populace_dynamics.min_benefit_track_m import (
    COVERED_EARNINGS_DISCLOSURE,
    DRY_RUN_HEADER,
    OUTPUT_LABELS,
    rules,
    tabulation,
)
from populace_dynamics.min_benefit_track_m.evaluation import (
    INVENTED,
    TrackMInputs,
    TrackMParameters,
    evaluate,
    needed_threshold_years,
)
from populace_dynamics.min_benefit_track_m.policy import (
    HEADLINE_CELL,
    REGISTERED_ROWS,
    SPECIFICATION_ID,
    frozen_choices,
    max_rulings,
    policy_for_row,
)

__all__ = ["NAMED_DELTAS", "run_track_m"]

#: The named deltas every output carries (M1 specification, section 15).
NAMED_DELTAS: tuple[str, ...] = (
    "realized 2022 against DYNASIM's projected 2025",
    "exposure: aligned in MS0 with a residual age-structure delta; 16 "
    "against 19 cohorts in MS1",
    "realized AWI and CPI against the 2005 Trustees paths",
    "PSID against SIPP population and weights",
    "labor income treated as covered earnings (d280)",
    "pre-1968 and pre-entry years",
    "odd income years: 1997 and 1999 never asked; 2001-2021 asked a wave "
    "later, for the reference person and spouse only",
    "pre-1978 quarters read from annual amounts ($200 a year)",
    "the death year dropped from a death-basis record's history",
    "unlinked auxiliaries",
    "entitlement classification at the 2004 boundary",
    "no windfall-elimination rule applied to the minimum",
    "no recomputation for later earnings",
    "children's benefits: DYNASIM has none",
    "the stock date: 2022 beneficiaries who died or moved out before the "
    "2023 interview are outside the universe",
    "years as another family member are unobserved",
    "the 2022 Census workbook prints weighted averages rounded to $10",
)


def run_track_m(
    inputs: TrackMInputs,
    parameters: TrackMParameters,
    *,
    data_provenance: str,
    registration_pointer: str | None = None,
    rows: Sequence[str] = tuple(REGISTERED_ROWS),
    labels: Sequence[str] = OUTPUT_LABELS,
    floor_seeds: Sequence[int] | None = None,
    specification: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Every registered row in ``rows``, each with its twelve cells.

    The guards run first (module docstring); then each row's policy is
    :func:`.policy.policy_for_row`'s one-field change of MS0.
    """

    rows = tuple(rows)
    unknown = [row for row in rows if row not in REGISTERED_ROWS]
    if unknown or "MS0" not in rows or len(set(rows)) != len(rows):
        raise ValueError(
            "rows must include MS0 and only registered rows, each once, "
            f"not {list(rows)}"
        )
    marker = pd.DataFrame()
    marker.attrs["provenance_kind"] = inputs.provenance_kind
    tabulation.check_provenance(
        marker,
        data_provenance=data_provenance,
        registration_pointer=registration_pointer,
        labels=labels,
        specification=specification,
    )
    if data_provenance == tabulation.REGISTERED_REAL:
        if rows != tuple(REGISTERED_ROWS):
            raise ValueError(
                f"a registered run reports every registered row "
                f"{list(REGISTERED_ROWS)}, not {list(rows)}"
            )
        if floor_seeds is not None:
            raise ValueError(
                "a registered run uses the registered floor seeds; "
                "floor_seeds may not be set"
            )
    policies = {row: policy_for_row(row) for row in rows}
    needed = needed_threshold_years(inputs.workers.values(), policies.values())
    rules.check_threshold_years(needed, parameters.thresholds)
    seeds = {} if floor_seeds is None else {"floor_seeds": floor_seeds}
    results: dict[str, Any] = {}
    for row, policy in policies.items():
        evaluation = evaluate(inputs, policy, parameters)
        table = tabulation.tabulate_track_m(
            evaluation.rows,
            row_id=row,
            data_provenance=data_provenance,
            design=inputs.design,
            registration_pointer=registration_pointer,
            labels=labels,
            specification=specification,
            **seeds,
        )
        results[row] = {
            "change_from_ms0": dict(REGISTERED_ROWS[row]),
            "policy": policy.as_dict(),
            "rulings_departed_from": [
                item["field"]
                for item in max_rulings(policy)
                if not item["follows_ruling"]
            ],
            "tabulation": table,
            "diagnostics": dict(evaluation.diagnostics),
        }
    headline = next(
        cell
        for cell in results["MS0"]["tabulation"]["cells"]
        if (cell["option"], cell["row"]) == HEADLINE_CELL
    )
    invented = data_provenance == INVENTED
    return {
        "header": DRY_RUN_HEADER if invented else None,
        "specification": SPECIFICATION_ID,
        "data_provenance": data_provenance,
        "registration_pointer": registration_pointer,
        "labels": results["MS0"]["tabulation"]["labels"],
        "disclosure": COVERED_EARNINGS_DISCLOSURE,
        "named_deltas": list(NAMED_DELTAS),
        "headline": {
            "row": "MS0",
            "option": HEADLINE_CELL[0],
            "cell": HEADLINE_CELL[1],
            "share_percent": headline.get("share_percent"),
        },
        "threshold_years_needed": {
            str(year): count for year, count in needed.items()
        },
        "parameters": parameters.source(),
        "inputs": {
            "provenance_kind": inputs.provenance_kind,
            "n_persons": len(inputs.persons),
            "n_worker_records": len(inputs.workers),
            "source": dict(inputs.source),
        },
        "max_rulings": max_rulings(),
        "frozen_choices": [item.as_dict() for item in frozen_choices()],
        "rows": results,
    }
