"""a2-ratified-1 §9 guards, applied before any joint tabulation (§10)."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from populace_dynamics.fra68_track.benefits import (
    classify_membership_differences,
)
from populace_dynamics.fra68_track.config import ClaimingResponse
from populace_dynamics.track_a_v2.estimands import normalize_rows
from populace_dynamics.track_a_v2.matrix import MatrixRow, a7_config


class MembershipRefusal(ValueError):
    """A joint refusal with the first failing person-draw and counters."""

    def __init__(self, row, item, step, counters):
        self.person_id = item["person_id"]
        self.draw = int(item["draw"])
        self.step = step
        self.row = row.key
        self.counters = counters
        super().__init__(
            f"{row.key}: membership difference at draw {self.draw}, "
            f"person {self.person_id}; joint step {step}"
        )


def guard_membership(
    records: Iterable[Mapping[str, Any]],
    row: MatrixRow,
    *,
    baseline_params=None,
    reform_params=None,
) -> dict[str, Any]:
    """Refuse both C0 directions, subject only to the exact L/D predicate.

    R callers supply unfiltered components. Truthful flags are constructed
    before A7's selected-component rule; baseline-zero people cannot vanish.
    C1/C2 permit differences and retain diagnostic legacy-predicate matches.
    """
    # §10 does not break ties between failing people. Conservatively use a
    # deterministic draw/key order, independent of input row presentation.
    records = sorted(
        (dict(item) for item in records),
        key=lambda item: (int(item["draw"]), str(item["person_id"])),
    )
    exercise1 = row.row_id.startswith("R")
    if exercise1:
        for item in records:
            item["beneficiary_base"] = item["benefit_base"] > 0
            item["beneficiary_reform"] = item["benefit_reform"] > 0
    draws = tuple(sorted({int(r["draw"]) for r in records})) or (0,)
    normalized = normalize_rows(records, a7_config(row, draw_indices=draws))
    base, reform = normalized.recipient_base, normalized.recipient_reform
    directions = {
        "n_rows": len(records),
        "n_rows_differ": int((base != reform).sum()),
        "n_rows_baseline_only": int((base & ~reform).sum()),
        "n_rows_reform_only": int((reform & ~base).sum()),
    }
    if exercise1:
        for index, item in enumerate(records):
            if base[index] != reform[index] or (
                item["benefit_base"] > 0 and item["benefit_reform"] <= 0
            ):
                raise MembershipRefusal(row, item, 3, directions)
        return directions
    if not directions["n_rows_differ"]:
        return {**directions, "n_legacy_predicate_matches": 0}
    classified = classify_membership_differences(
        records,
        base,
        reform,
        components=row.components,
        baseline_params=baseline_params,
        reform_params=reform_params,
        reference_year=2030,
        assumed_birth_month=7,
        claiming_response=row.claiming_response,
    )
    record = classified["record"]
    counts = {
        **record,
        "n_legacy_predicate_matches": (
            directions["n_rows_differ"] - record["n_rows_not_explained"]
        ),
    }
    if row.claiming_response is not ClaimingResponse.FIXED:
        return counts
    allow_legacy = row.mechanism in ("L", "D") and row.row_id != "F6"
    first = (
        classified["first_not_explained"]
        if allow_legacy
        else next(
            item
            for index, item in enumerate(records)
            if base[index] != reform[index]
        )
    )
    if first is not None:
        raise MembershipRefusal(row, first, 5, counts)
    return counts
