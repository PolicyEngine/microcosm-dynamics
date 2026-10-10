"""The frozen a2-ratified-1 §§2, 7–9 matrix; no selectable headline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from populace_dynamics.cola_track_a.config import REGISTERED_ROWS
from populace_dynamics.estimates import cola_age_profile as a7
from populace_dynamics.fra68_track.config import (
    ClaimingResponse,
    FRA68Row,
    registered_rows,
)

MECHANISMS = ("L", "D", "S", "DS")
ROW_IDS = (
    tuple(f"R{i}" for i in range(6))
    + tuple(f"F{i}" for i in range(8))
    + ("U0", "U1", "U2")
)
UNION_STATISTIC = "ratio_of_all_alive_weighted_totals"
HEADLINES = ("D×R0", "D×F0")
ARTIFACT_LABELS = (
    "registered, one-shot, post hoc, not blind",
    "PSID-seeded closed cohort",
    "Python oracle (not Axiom)",
)
INVENTED_HEADER = "INVENTED DATA - NOT A COMPARISON"
HISTORICAL_ROWS = {
    "R6": "not rerun: requires a second population",
    "F8": "not rerun: requires a second population",
}


@dataclass(frozen=True)
class MatrixRow:
    """An immutable benefit configuration and estimand in publication order."""

    mechanism: str
    row_id: str
    source_row: Any
    statistic: str
    claiming_response: ClaimingResponse
    components: tuple[str, ...]

    @property
    def key(self) -> str:
        return f"{self.mechanism}×{self.row_id}"

    @property
    def headline(self) -> bool:
        return self.key in HEADLINES

    @property
    def labels(self) -> tuple[str, ...]:
        label = (
            "fixed-path mechanical incidence"
            if self.claiming_response is ClaimingResponse.FIXED
            else "fixed paths; stylized claiming response "
            "(registered sensitivity)"
        )
        return (*ARTIFACT_LABELS, label)

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "mechanism": self.mechanism,
            "row_id": self.row_id,
            "source_row": self.source_row.as_dict(),
            "statistic": self.statistic,
            "claiming_response": self.claiming_response.value,
            "components": list(self.components),
            "labels": list(self.labels),
            "headline": self.headline,
            "age_groups": [g.as_dict() for g in a7.DEFAULT_AGE_GROUPS],
        }


def _matrix() -> tuple[MatrixRow, ...]:
    fra_rows = registered_rows()
    union_sources = dict(
        zip(("U0", "U1", "U2"), ("F0", "F3", "F4"), strict=True)
    )
    rows = []
    for mechanism in MECHANISMS:
        for row_id in ROW_IDS:
            source = (
                REGISTERED_ROWS[row_id]
                if row_id.startswith("R")
                else fra_rows[union_sources.get(row_id, row_id)]
            )
            rows.append(
                MatrixRow(
                    mechanism,
                    row_id,
                    source,
                    (
                        UNION_STATISTIC
                        if row_id.startswith("U")
                        else source.headline_statistic
                    ),
                    (
                        source.claiming_response
                        if isinstance(source, FRA68Row)
                        else ClaimingResponse.FIXED
                    ),
                    source.components,
                )
            )
    return tuple(rows)


MATRIX = _matrix()


def get_row(mechanism: str, row_id: str) -> MatrixRow:
    """Return only a registered mechanism/row, in its frozen configuration."""
    for row in MATRIX:
        if (row.mechanism, row.row_id) == (mechanism, row_id):
            return row
    raise ValueError(f"unregistered Track A v2 row: {mechanism}×{row_id}")


def a7_config(
    row: MatrixRow,
    *,
    draw_indices: tuple[int, ...] = tuple(range(20)),
    floor_seeds: tuple[int, ...] = tuple(range(5)),
) -> a7.ColaAgeProfileConfig:
    """Retain A7's frozen normalization and scenario membership semantics."""
    exercise1 = row.row_id.startswith("R")
    return a7.ColaAgeProfileConfig(
        components=row.components,
        draw_indices=draw_indices,
        floor_seeds=floor_seeds,
        allow_membership_difference=not exercise1,
        membership_basis=(
            a7.COMMON_RECIPIENTS if exercise1 else a7.SCENARIO_SPECIFIC
        ),
        headline_statistic=(
            a7.RATIO_OF_SCENARIO_MEANS
            if row.statistic == UNION_STATISTIC
            else row.statistic
        ),
        benefit_period=(
            row.source_row.tabulation_benefit_period
            if exercise1
            else "calendar_year_payments"
        ),
    )
