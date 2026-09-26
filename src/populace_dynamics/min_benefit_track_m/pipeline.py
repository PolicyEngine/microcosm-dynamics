"""Track M end to end: every registered row, after the guards (plan M10).

Python rules (not Axiom).  :func:`run_track_m` takes the records
(:class:`~.evaluation.TrackMInputs`, from the M4 cohort and M5 careers,
:mod:`.cohort` and :mod:`.careers`, or from :mod:`.invented`) and the
parameters, and
for each registered row MS0-MS6 evaluates every record under the row's
policy (:mod:`.evaluation`) and tabulates Table 6's twelve cells with
their uncertainty (:mod:`.tabulation`).  Before computing anything it:

* refuses records read from staged PSID files (their source carries the
  files' SHA-256, :data:`PSID_FILES_SOURCE_KEY`) outside the registered
  run, or with a specification block other than the committed one;
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
  :class:`.rules.ThresholdYearMissingError`;
* refuses scored records built under any own-receipt reading but the one
  Max's d430 keeps for the scored rows, and, for ``registered_real``, a
  run without d430's sensitivity (below).

**d430's sensitivity** (:data:`.policy.SENSITIVITIES`; M1 specification
sections 4c, 11, 14 and 19).  Given ``own_receipt_sensitivity``, the same
universe's records built under d430's sensitivity reading
(``cohort.build_cohort(..., own_receipt_reading=...)`` and M5's careers),
the run also computes, unscored: MS0's twelve cells under that reading,
with the same tabulation, floor and design-based standard error; and
which records and persons the two readings' inputs differ on
(:func:`own_receipt_reclassification`), with the weighted share of the
universe (and of each Table 6 row) whose *A*_k rests on a record
classified differently.  A person whose inputs are the same under both
readings (their person record and every worker record their *A* reads)
has the same *A*_k under both, so the gap between the two
readings' shares in a cell is at most that cell's resting share; the run
checks that every person whose *A* differs is among the resting.  The
sensitivity's records pass the same guards as the scored records, and the
threshold years they need are checked before anything is computed.  The
scored rows' outputs do not depend on it: MS0-MS6 are computed as without
it, and the sensitivity is published under ``sensitivities``.

The result records the rulings (:data:`.policy.MAX_RULINGS`), the frozen
choices, the parameters' provenance, the labels and the covered-earnings
disclosure (d280).  Nothing here reads a file or a comparator value.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
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
    PSID_FILES,
    PersonRecord,
    TrackMInputs,
    TrackMParameters,
    evaluate,
    needed_threshold_years,
)
from populace_dynamics.min_benefit_track_m.policy import (
    HEADLINE_CELL,
    MAX_RULINGS,
    OWN_RECEIPT_SENSITIVITY_ID,
    REGISTERED_ROWS,
    SENSITIVITIES,
    SPECIFICATION_ID,
    TABLE6_OPTIONS,
    TABLE6_ROWS,
    frozen_choices,
    max_rulings,
    policy_for_row,
)

__all__ = [
    "NAMED_DELTAS",
    "OwnReceiptReclassification",
    "PSID_FILES_SOURCE_KEY",
    "own_receipt_reclassification",
    "receipt_under_both_readings",
    "run_track_m",
]

#: The ``TrackMInputs.source`` key under which records built from staged
#: PSID files carry the files' SHA-256 (:mod:`.cohort`, :mod:`.careers`).
#: Such records are evaluated only by the registered run and only against
#: the committed specification block (the review of 2026-09-25: an
#: injectable block must not reach real records).
PSID_FILES_SOURCE_KEY = "psid_files_sha256"

#: The named deltas every output carries (M1 specification, section 15).
NAMED_DELTAS: tuple[str, ...] = (
    "realized 2022 against DYNASIM's projected 2025",
    "exposure: aligned in MS0 with a residual age-structure delta; 16 "
    "against 19 cohorts in MS1",
    "realized AWI and CPI against the 2005 Trustees paths",
    "PSID against SIPP population and weights",
    "labor income treated as covered earnings (d280)",
    "pre-1968 and pre-entry years",
    "odd income years: 1997 and 1999 never asked in the family files; "
    "2001-2021 asked a wave later, for the reference person and spouse "
    "only",
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
    "the next wave's year-before-last labor income counts farm, business "
    "and self-employment earnings, which the panel's constructed labor "
    "income excludes from income year 1993 on, and leaves a DK or NA "
    "amount unassigned (the year then takes the gap rule)",
    "next-wave amounts reported per hour, day, week, two weeks or month "
    "annualized at full-year factors",
    "own receipt read from self-reported types: a year of spouse's, "
    "survivor's or dependent's receipt only counts as without own receipt",
    "family-level receipt items read as every member's non-receipt when the "
    "family reports none, and as a one-member family's receipt",
    "a late spouse with no observed own receipt read as having died before "
    "any own entitlement, including one who died at 62 or older or in an "
    "income year no person-level item records (1993-2003 and the odd "
    "years 2005-2021)",
    "entitlement years read from observed non-receipt: rule 2's earliest "
    "consistent year takes the year after the last observed year without "
    "own receipt, including non-receipt observed at 70 or older",
    "the next wave's loss (net of self-employment) read as zero covered "
    "earnings, although wages may have been paid that year",
    "the individual file's person-level earnings of 1997, 1999 and 2001 "
    "(ER33537N, ER33628N, ER33728N) are not read: the frozen odd-year "
    "source is the family files' next-wave items",
    "spouses linked by the marital state at the end of 2022 only: divorced "
    "spouses, and late spouses of survivors who remarried, are not linked",
    "MS5's benefit is the 2022 annual total over 12, understated for a "
    "benefit first paid during 2022",
    "the oracle's survivor reduction runs from 60 to 67 for every cohort",
    # Recorded as named deltas by Max's d430 (2026-09-26), restated from
    # the statute capture against the text (M1 specification section 18
    # item 4; EV/track-m-4-review-20260925.md).
    "F2: a disability-origin record's Y history ends at onset - 1, "
    "dropping quarters 413(a)(2)(B)(i) can count (the onset year's "
    "quarters before the period of disability and its initial quarter); "
    "P's history ends there too, which matches 423(a)(2) and "
    "415(b)(2)(B)(ii)(I) only when the DI application falls in the onset "
    "year",
    "F3a: for a survivor entitled to own DI benefit D in the first month of "
    "the widow(er)'s benefit W, 402(q)(3)(A)(ii) and (C) with 402(k)(3)(A) "
    "pay (W - D)(1 - r), positive whenever W > D; the oracle's test "
    "W(1 - r) > D reports some of those as not paid",
    "F3b: where 402(q)(3)(A) does not apply to a spouse (an own old-age "
    "benefit begun at or after retirement age, or begun after the spouse's "
    "benefit but before retirement age), the text pays the spouse's "
    "benefit S(1 - r) less the own benefit as paid, which can be zero or "
    "less while S > O, where the oracle reports the spouse's benefit paid",
    "O1: current law's special minimum PIA (415(a)(1)(C)) is not modeled; "
    "neither option 1 nor the count of people receiving a minimum accounts "
    "for it",
    "section 4c item 1's own-receipt reading (d430): receipt of an unknown "
    "or 'other' type or a combination code counts as own receipt, before "
    "the year of attaining 62 too; d430's unscored sensitivity reads such "
    "years before 62 as neither own receipt nor non-receipt",
)


_SENSITIVITY = SENSITIVITIES[OWN_RECEIPT_SENSITIVITY_ID]
#: The reading the registered rows are scored under (d430).
_SCORED_READING = MAX_RULINGS["own_receipt_reading"]["ruling"]
#: The fields of a person record that do not depend on the own-receipt
#: reading: the universe, its weights and its design are the same under
#: both (``cohort.build_cohort``).
_UNIVERSE_FIELDS = (
    "person_id",
    "family_unit_id",
    "weight",
    "sex",
    "stratum",
    "cluster",
    "other_member",
)


def _check_psid_records(
    records: TrackMInputs,
    *,
    data_provenance: str,
    specification: Mapping[str, Any] | None,
) -> None:
    """Records carrying PSID file hashes: the registered run only, and
    only against the committed specification block."""

    if not records.source.get(PSID_FILES_SOURCE_KEY):
        return
    if records.provenance_kind != PSID_FILES:
        raise ValueError(
            "records carrying PSID file hashes are marked psid_files, "
            f"not {records.provenance_kind!r}"
        )
    if data_provenance != tabulation.REGISTERED_REAL:
        raise ValueError(
            "records read from staged PSID files are evaluated only by "
            "the registered run"
        )
    if specification is not None:
        from populace_dynamics.min_benefit_track_m import (
            specification as m1,
        )

        if dict(specification) != m1.m1_parameter_block():
            raise ValueError(
                "records read from staged PSID files are evaluated only "
                "against the committed M1 specification block; a "
                "supplied block must equal it"
            )


def _check_sensitivity_inputs(
    scored: TrackMInputs, sensitivity: TrackMInputs
) -> None:
    """d430's sensitivity reads the scored run's universe under the other
    reading: same provenance, files, persons, weights and design."""

    reading = _SENSITIVITY["sensitivity_reading"]
    if sensitivity.own_receipt_reading != reading:
        raise ValueError(
            f"d430's sensitivity records are built under {reading!r}, not "
            f"{sensitivity.own_receipt_reading!r}"
        )
    if sensitivity.provenance_kind != scored.provenance_kind:
        raise ValueError(
            "d430's sensitivity records and the scored records differ in "
            "provenance kind"
        )
    if sensitivity.source.get(PSID_FILES_SOURCE_KEY) != scored.source.get(
        PSID_FILES_SOURCE_KEY
    ):
        raise ValueError(
            "d430's sensitivity records were read from other PSID files "
            "than the scored records"
        )
    left = [
        tuple(getattr(person, name) for name in _UNIVERSE_FIELDS)
        for person in scored.persons
    ]
    right = [
        tuple(getattr(person, name) for name in _UNIVERSE_FIELDS)
        for person in sensitivity.persons
    ]
    if left != right:
        raise ValueError(
            "d430's sensitivity reads the same universe: its persons, "
            "weights, sexes and design variables must equal the scored "
            "records', in order"
        )
    if not scored.design.reset_index(drop=True).equals(
        sensitivity.design.reset_index(drop=True)
    ):
        raise ValueError(
            "d430's sensitivity reads the same sample design frame"
        )


def _record_ids(person: PersonRecord) -> tuple[str, ...]:
    ids = [link.worker_record_id for link in person.links]
    if person.own_record_id is not None:
        ids.append(person.own_record_id)
    return tuple(ids)


@dataclass(frozen=True)
class OwnReceiptReclassification:
    """Where the two own-receipt readings' inputs differ (d430).

    ``records_differing``: every worker record id present under one
    reading only, or whose record differs (basis, window, onset or death
    year, resolution, or the MS5 inputs these set).  ``persons_differing``:
    every person whose *A*_k rests on a record classified
    differently, that is, whose own record or any linked record, under
    either reading, is among ``records_differing``, or whose person record
    (own record, links, claim factor) differs; ``reasons`` names, per
    person, which of these holds.  A person outside
    ``persons_differing`` reads identical inputs under both readings.
    """

    records_differing: frozenset[str]
    persons_differing: frozenset[str]
    reasons: Mapping[str, frozenset[str]]
    record_changes: Mapping[str, int]

    def summary(self) -> dict[str, Any]:
        by_reason: Counter[str] = Counter()
        for reasons in self.reasons.values():
            by_reason.update(reasons)
        return {
            "worker_records_classified_differently": len(
                self.records_differing
            ),
            "worker_record_changes": dict(sorted(self.record_changes.items())),
            "persons_resting_on_a_record_classified_differently": len(
                self.persons_differing
            ),
            "persons_by_reason": dict(sorted(by_reason.items())),
        }


def own_receipt_reclassification(
    scored: TrackMInputs, sensitivity: TrackMInputs
) -> OwnReceiptReclassification:
    """The records and persons whose inputs differ between the readings.

    ``scored`` and ``sensitivity`` are the same universe's records under
    the scored reading and d430's sensitivity reading.  Compares every
    worker record by id (:class:`~.evaluation.WorkerRecord` equality: every
    field a record's evaluation reads) and every person record, and names
    each person whose *A* reads a record that differs (``own_record``,
    ``linked_record``), whose links differ (``links``: a link present
    under one reading only) or whose person record differs otherwise
    (``person_record``).
    """

    _check_sensitivity_inputs(scored, sensitivity)
    ids = set(scored.workers) | set(sensitivity.workers)
    differing = frozenset(
        key
        for key in ids
        if scored.workers.get(key) != sensitivity.workers.get(key)
    )
    changes: Counter[str] = Counter()
    for key in differing:
        left, right = scored.workers.get(key), sensitivity.workers.get(key)
        if right is None:
            changes["only_under_the_scored_reading"] += 1
            continue
        if left is None:
            changes["only_under_the_sensitivity_reading"] += 1
            continue
        for name in ("basis", "window_year", "onset_year", "death_year"):
            if getattr(left, name) != getattr(right, name):
                changes[name] += 1
        if left.unresolved != right.unresolved:
            changes["unresolved"] += 1
        if left.window_year < right.window_year:
            changes["window_year_later_under_the_sensitivity"] += 1
        elif left.window_year > right.window_year:
            changes["window_year_earlier_under_the_sensitivity"] += 1
    reasons: dict[str, frozenset[str]] = {}
    for left, right in zip(scored.persons, sensitivity.persons, strict=True):
        found = set()
        own = {left.own_record_id, right.own_record_id} - {None}
        if left.own_record_id != right.own_record_id or own & differing:
            found.add("own_record")
        left_links = {(ln.kind, ln.worker_record_id) for ln in left.links}
        right_links = {(ln.kind, ln.worker_record_id) for ln in right.links}
        if left_links != right_links:
            found.add("links")
        linked = {key for _, key in left_links | right_links}
        if linked & differing:
            found.add("linked_record")
        if left != right and not found:
            found.add("person_record")
        if found:
            reasons[left.person_id] = frozenset(found)
    return OwnReceiptReclassification(
        records_differing=differing,
        persons_differing=frozenset(reasons),
        reasons=reasons,
        record_changes=dict(changes),
    )


def _cell_mask(rows: pd.DataFrame, cell: str) -> np.ndarray:
    sex = {"all": None, "men": "male", "women": "female"}[cell]
    if sex is None:
        return np.ones(len(rows), dtype=bool)
    return rows["sex"].eq(sex).to_numpy()


def _percent(weight: np.ndarray, mask: np.ndarray, total: float) -> float:
    return 100.0 * math.fsum(weight[mask]) / total


def receipt_under_both_readings(
    scored_rows: pd.DataFrame,
    sensitivity_rows: pd.DataFrame,
    resting: frozenset[str],
) -> dict[str, Any]:
    """MS0's receipt under both readings, by Table 6 row and option.

    ``scored_rows`` and ``sensitivity_rows`` are :func:`.evaluation.
    evaluate`'s person rows for MS0 under each reading; ``resting`` the
    persons :func:`own_receipt_reclassification` finds resting on a record
    classified differently.  For each cell: the weighted (and unweighted)
    share of the cell resting; for each option, the share receiving under
    each reading, the change, the shares moved out (receiving under the
    scored reading only) and in, and the shares receiving and resting.
    Refuses rows whose persons differ, and raises if a person whose *A*
    differs between the readings is not among ``resting`` (their inputs
    are the same, so their *A* cannot differ).
    """

    left = scored_rows.reset_index(drop=True)
    right = sensitivity_rows.set_index("person_id").loc[left["person_id"]]
    for name in ("weight", "sex"):
        if not np.array_equal(left[name].to_numpy(), right[name].to_numpy()):
            raise ValueError(f"the two readings' rows differ in {name}")
    weight = left["weight"].to_numpy(dtype=float)
    rests = left["person_id"].isin(resting).to_numpy()
    moved = np.zeros(len(left), dtype=bool)
    for number in TABLE6_OPTIONS:
        column = f"receives_{number}"
        moved |= left[column].to_numpy(bool) != right[column].to_numpy(bool)
    if (moved & ~rests).any():
        raise AssertionError(
            "a person whose inputs are the same under both readings "
            "receives differently under them"
        )
    by_cell: dict[str, Any] = {}
    for cell in TABLE6_ROWS:
        mask = _cell_mask(left, cell)
        total = math.fsum(weight[mask])
        entry: dict[str, Any] = {
            "unweighted_n": int(mask.sum()),
            "weighted_n": total,
            "resting_unweighted": int((mask & rests).sum()),
            "resting_weighted": math.fsum(weight[mask & rests]),
        }
        if total <= 0:
            by_cell[cell] = {
                **entry,
                "defined": False,
                "undefined_reason": "empty cell or zero total weight",
            }
            continue
        entry["defined"] = True
        entry["resting_weighted_share_percent"] = _percent(
            weight, mask & rests, total
        )
        options = {}
        for number in TABLE6_OPTIONS:
            a = left[f"receives_{number}"].to_numpy(bool)
            b = right[f"receives_{number}"].to_numpy(bool)
            under_a = _percent(weight, mask & a, total)
            under_b = _percent(weight, mask & b, total)
            options[str(number)] = {
                "share_percent_scored_reading": under_a,
                "share_percent_sensitivity_reading": under_b,
                "change_percent_points": under_b - under_a,
                "moved_out_percent": _percent(weight, mask & a & ~b, total),
                "moved_in_percent": _percent(weight, mask & ~a & b, total),
                "moved_out_unweighted": int((mask & a & ~b).sum()),
                "moved_in_unweighted": int((mask & ~a & b).sum()),
                "receiving_and_resting_percent_scored_reading": _percent(
                    weight, mask & a & rests, total
                ),
                "receiving_and_resting_percent_sensitivity_reading": (
                    _percent(weight, mask & b & rests, total)
                ),
            }
        entry["options"] = options
        by_cell[cell] = entry
    return by_cell


def _own_receipt_sensitivity(
    scored: TrackMInputs,
    sensitivity: TrackMInputs,
    scored_ms0_rows: pd.DataFrame,
    parameters: TrackMParameters,
    needed: Mapping[int, int],
    *,
    data_provenance: str,
    registration_pointer: str | None,
    labels: Sequence[str],
    specification: Mapping[str, Any] | None,
    seeds: Mapping[str, Any],
) -> dict[str, Any]:
    """d430's sensitivity: MS0 under the other reading, and the share
    resting on records the readings classify differently (unscored)."""

    policy = policy_for_row(_SENSITIVITY["row"])
    evaluation = evaluate(sensitivity, policy, parameters)
    table = tabulation.tabulate_track_m(
        evaluation.rows,
        row_id=f"{_SENSITIVITY['row']}:{OWN_RECEIPT_SENSITIVITY_ID}",
        data_provenance=data_provenance,
        design=sensitivity.design,
        registration_pointer=registration_pointer,
        labels=labels,
        specification=specification,
        scored=False,
        **seeds,
    )
    reclassified = own_receipt_reclassification(scored, sensitivity)
    by_cell = receipt_under_both_readings(
        scored_ms0_rows, evaluation.rows, reclassified.persons_differing
    )
    everyone = by_cell["all"]
    return {
        "id": OWN_RECEIPT_SENSITIVITY_ID,
        "registered": dict(_SENSITIVITY),
        "scored": False,
        "description": (
            "Cos d430's pre-registered, unscored sensitivity: MS0's twelve "
            "cells with receipt years before the year of attaining 62 of "
            "unknown or 'other' type (naming neither a retirement nor a "
            "disability benefit) read as neither own receipt nor "
            "non-receipt, and the weighted share of the universe whose A_k "
            "rests on a record the two readings classify differently. "
            "MS0 under the scored reading is the scored row."
        ),
        "counterpart_of_the_headline": {
            "option": HEADLINE_CELL[0],
            "row": HEADLINE_CELL[1],
        },
        "weighted_share_of_the_universe_resting_percent": everyone.get(
            "resting_weighted_share_percent"
        ),
        "threshold_years_needed": {
            str(year): count for year, count in needed.items()
        },
        "tabulation": table,
        "reclassification": reclassified.summary(),
        "receipt_under_both_readings": by_cell,
        "diagnostics": dict(evaluation.diagnostics),
    }


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
    own_receipt_sensitivity: TrackMInputs | None = None,
) -> dict[str, Any]:
    """Every registered row in ``rows``, each with its twelve cells.

    The guards run first (module docstring); then each row's policy is
    :func:`.policy.policy_for_row`'s one-field change of MS0.
    ``own_receipt_sensitivity`` (required for ``registered_real``) is the
    same universe's records under d430's sensitivity reading; with it the
    result carries d430's sensitivity under ``sensitivities`` (module
    docstring), and the rows are unchanged.
    """

    rows = tuple(rows)
    unknown = [row for row in rows if row not in REGISTERED_ROWS]
    if unknown or "MS0" not in rows or len(set(rows)) != len(rows):
        raise ValueError(
            "rows must include MS0 and only registered rows, each once, "
            f"not {list(rows)}"
        )
    _check_psid_records(
        inputs, data_provenance=data_provenance, specification=specification
    )
    if own_receipt_sensitivity is not None:
        _check_psid_records(
            own_receipt_sensitivity,
            data_provenance=data_provenance,
            specification=specification,
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
    if inputs.own_receipt_reading != _SCORED_READING:
        raise ValueError(
            "the registered rows are scored under the own-receipt reading "
            f"Max's d430 keeps ({_SCORED_READING!r}), not "
            f"{inputs.own_receipt_reading!r}; d430's sensitivity reading "
            "enters only as own_receipt_sensitivity"
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
        if own_receipt_sensitivity is None:
            raise ValueError(
                "a registered run computes Max's d430 sensitivity "
                f"({OWN_RECEIPT_SENSITIVITY_ID}): it needs the records "
                "built under the sensitivity reading "
                "(own_receipt_sensitivity)"
            )
    if own_receipt_sensitivity is not None:
        _check_sensitivity_inputs(inputs, own_receipt_sensitivity)
    policies = {row: policy_for_row(row) for row in rows}
    needed = needed_threshold_years(inputs.workers.values(), policies.values())
    rules.check_threshold_years(needed, parameters.thresholds)
    sensitivity_needed: dict[int, int] = {}
    if own_receipt_sensitivity is not None:
        sensitivity_needed = needed_threshold_years(
            own_receipt_sensitivity.workers.values(),
            [policy_for_row(_SENSITIVITY["row"])],
        )
        rules.check_threshold_years(sensitivity_needed, parameters.thresholds)
    seeds = {} if floor_seeds is None else {"floor_seeds": floor_seeds}
    results: dict[str, Any] = {}
    scored_ms0_rows = None
    for row, policy in policies.items():
        evaluation = evaluate(inputs, policy, parameters)
        if row == _SENSITIVITY["row"]:
            scored_ms0_rows = evaluation.rows
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
    out = {
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
    if own_receipt_sensitivity is not None:
        out["sensitivities"] = {
            OWN_RECEIPT_SENSITIVITY_ID: _own_receipt_sensitivity(
                inputs,
                own_receipt_sensitivity,
                scored_ms0_rows,
                parameters,
                sensitivity_needed,
                data_provenance=data_provenance,
                registration_pointer=registration_pointer,
                labels=labels,
                specification=specification,
                seeds=seeds,
            )
        }
    return out
