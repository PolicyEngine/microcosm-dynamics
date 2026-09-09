"""Build entrant cohorts for the loop's scheduled-entries seam.

REPORT-ONLY.  Nothing this module produces enters a fitted law, and no gate
scores it.  It converts a sized control (Trustees Table V.A2 gross inflow) and
an explicitly supplied demographic donor into
frames the existing seam already accepts.

**The seam is not new.**  ``engine/loop.py`` has activated scheduled entries
since the M6 openers: :data:`~populace_dynamics.engine.loop.SCHEDULED_ENTRIES_KEY`
at ``loop.py:27``, validation at ``loop.py:219-247``, activation at
``loop.py:262-281``.  This module only produces its input, so three properties
are inherited rather than designed:

1. **The frame coordinate is the year BEFORE activation.**  ``loop.py:236-239``
   rejects any other year.  Following the documented opener convention at
   ``m6_population.py:328-334`` -- "the frame coordinate is the reference year
   immediately before the anchor interview, while age is the realized
   collection-wave age" -- an entrant row carries ``year = activation_year - 1``
   and ``age = entry_age``.  The loop's first step is therefore a **mortality
   draw at the entrant's entry age**, before any aging; the aging step then
   advances them to ``entry_age + 1`` in the activation year.  That entry-year
   exposure convention is fixed by the seam, not chosen here.
2. **IDs come from the projection-wide allocator.**  ``loop.py:41-63`` raises
   on any overlap with ``reserved_real_ids``, which is what stops an entrant
   from silently inheriting a fitted person's ``u_w``.
3. **RNG streams are stable per person** (``loop.py:285-292, 351-353``), so
   reproducibility is free.

**Sizing.**  Cohorts are sized to V.A2's *gross positive inflow* (LPR inflow +
temporary-or-unlawfully-present inflow), never to its total net change.  Net
change is a residual whose age/sex/family composition has no literal
interpretation, and adjustment of status is a reclassification between two
stocks rather than a new person.  Native control and donor readers from the original branch are not included
in this isolated source slice; all controls and rows are supplied by callers.

**Method.**  The donor pool is reweighted, not resampled: every positive-weight donor row
appears once per positive-inflow activation year with its weight scaled by a single factor so
the cohort's weighted total equals the control.  That is deterministic,
consumes no RNG, and reproduces the donor composition exactly, so any residual
against the control is arithmetic rather than sampling noise.

**Provenance.**  Every emitted row carries ``entry_kind``, so births, realized
openers and immigrant cohorts stop being inferred from ID arithmetic.  That
inference is what ``harness/m6_runner.py:1026-1032`` currently does when it
writes ``"immigrant_cohorts": 0`` under the comment "Every synthetic ID
allocated by this closed-panel engine is a step-4 materialized maternal
birth" -- true today, and false the moment a schedule is supplied.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from numbers import Integral
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.engine.loop import SyntheticPersonIdAllocator

__all__ = [
    "ENTRY_KIND_COLUMN",
    "ENTRY_KIND_IMMIGRANT",
    "ENTRY_KIND_BIRTH",
    "ENTRY_KIND_REALIZED_OPENER",
    "ENTRY_KIND_INCUMBENT",
    "EntrantSchedule",
    "build_entrant_schedule",
    "entrant_provenance_counters",
]

#: The provenance column every open-addition row should carry.
ENTRY_KIND_COLUMN = "entry_kind"
ENTRY_KIND_IMMIGRANT = "immigrant_cohort"
ENTRY_KIND_BIRTH = "maternal_birth"
ENTRY_KIND_REALIZED_OPENER = "realized_opener"
ENTRY_KIND_INCUMBENT = "incumbent"

#: V.A2 is published in thousands of persons.
_THOUSANDS = 1000.0

#: Columns this module owns on an entrant row.  Anything else present on the
#: roster is emitted as NA, which is the same disposition the birth path uses
#: (``steps.py:485-487`` builds children on ``frame.columns`` and fills only
#: what a newborn genuinely has).
_OWNED_COLUMNS = (
    "person_id",
    "year",
    "age",
    "sex",
    "birth_year",
    "weight",
    "start_weight",
    "synthetic_entry",
    ENTRY_KIND_COLUMN,
    "entry_year",
    "entry_age",
    "donor_person_id",
    "donor_source_year",
    "donor_peinusyr",
    "donor_prcitshp",
    "donor_penatvty",
    "foreign_born",
)


@dataclass(frozen=True)
class EntrantSchedule:
    """Scheduled entrant frames plus the audit record of how they were sized."""

    frames: dict[int, pd.DataFrame]
    alignment: dict[int, dict[str, float]]
    provenance: dict[str, Any]

    def as_metadata(self) -> dict[int, pd.DataFrame]:
        """The value for ``metadata[SCHEDULED_ENTRIES_KEY]``."""
        return {year: frame.copy() for year, frame in self.frames.items()}

    def total_rows(self) -> int:
        return int(sum(len(frame) for frame in self.frames.values()))

    def total_weight(self) -> float:
        return float(
            sum(frame["weight"].sum() for frame in self.frames.values())
        )


def _validate_donor(donor: pd.DataFrame) -> None:
    required = {
        "person_id",
        "weight",
        "entry_age",
        "is_female",
        "source_year",
        "peinusyr",
        "prcitshp",
        "penatvty",
        # Carried, never asserted: the recent-arrival band's universe is
        # everyone not born in the fifty states, so it contains natives too
        # (see nativity_frame.recent_arrival_donor).
        "foreign_born",
    }
    missing = required - set(donor.columns)
    if missing:
        raise ValueError(f"entrant donor is missing columns {sorted(missing)}")
    if donor.empty:
        raise ValueError("entrant donor pool is empty")
    weight = donor["weight"].to_numpy(dtype=np.float64)
    if not np.isfinite(weight).all() or (weight < 0).any():
        raise ValueError("entrant donor weights must be finite and >= 0")
    if not np.isfinite(weight.sum()) or weight.sum() <= 0:
        raise ValueError(
            "entrant donor pool needs a finite positive total weight"
        )
    age = donor["entry_age"].to_numpy(dtype=np.float64)
    if (
        not np.isfinite(age).all()
        or (age < 0).any()
        or (age != np.floor(age)).any()
        or (age >= np.iinfo(np.int64).max).any()
    ):
        raise ValueError(
            "entrant donor entry_age must be nonnegative integers"
        )
    for column in ("is_female", "foreign_born"):
        if not all(
            isinstance(value, (bool, np.bool_)) for value in donor[column]
        ):
            raise ValueError(f"entrant donor {column} must contain booleans")


def build_entrant_schedule(
    donor: pd.DataFrame,
    inflow_thousands_by_year: Mapping[int, float],
    *,
    allocator: SyntheticPersonIdAllocator,
    roster_columns: Sequence[str] | None = None,
    entry_kind: str = ENTRY_KIND_IMMIGRANT,
    control_provenance: Mapping[str, Any] | None = None,
    donor_provenance: Mapping[str, Any] | None = None,
) -> EntrantSchedule:
    """Materialize one entrant frame per activation year.

    ``donor`` supplies the explicit demographic/provenance columns; no native
    donor reader or source admission is included in this experimental slice.
    ``inflow_thousands_by_year`` supplies scenario controls in thousands using
    the historical gross-positive-inflow convention. ``allocator`` is the
    projection-wide
    :class:`~populace_dynamics.engine.loop.SyntheticPersonIdAllocator`; passing
    the projection's own allocator is what guarantees entrant IDs never
    collide with a fitted person-keyed support.
    """
    _validate_donor(donor)
    if entry_kind != ENTRY_KIND_IMMIGRANT:
        raise ValueError("immigrant schedules require immigrant_cohort kind")
    if any(
        isinstance(year, (bool, np.bool_)) or not isinstance(year, Integral)
        for year in inflow_thousands_by_year
    ):
        raise ValueError("activation years must be integers")
    years = sorted(inflow_thousands_by_year)
    if not years:
        raise ValueError("no activation years requested")
    controls = {}
    for year in years:
        inflow = float(inflow_thousands_by_year[year])
        if (
            not np.isfinite(inflow)
            or inflow < 0
            or not np.isfinite(inflow * _THOUSANDS)
        ):
            raise ValueError(
                f"activation year {year} has a non-finite or negative control "
                f"inflow {inflow!r}"
            )
        controls[year] = inflow

    # Zero-weight donors never become demographic actors or consume IDs.
    # Keep the float representation validated above; an integer sum can
    # overflow before scaling even when every individual weight is valid.
    donor = donor.copy()
    donor["weight"] = donor["weight"].to_numpy(dtype=np.float64)
    donor = donor.loc[donor["weight"] > 0].copy()

    donor_weight_total = float(donor["weight"].sum())
    donor_weight = donor["weight"].to_numpy(dtype=np.float64)
    donor_proportion = donor_weight / donor_weight_total
    for inflow in controls.values():
        if inflow == 0:
            continue
        scale = inflow * _THOUSANDS / donor_weight_total
        with np.errstate(over="ignore", under="ignore"):
            extrema = donor_proportion[
                [donor_weight.argmin(), donor_weight.argmax()]
            ] * (inflow * _THOUSANDS)
        if (
            not np.isfinite(scale)
            or scale <= 0
            or not np.isfinite(extrema).all()
            or (extrema <= 0).any()
        ):
            raise ValueError(
                "control scaling must yield finite positive donor weights"
            )
    entry_age = donor["entry_age"].to_numpy(dtype=np.int64)
    sex = np.where(donor["is_female"].to_numpy(dtype=bool), "female", "male")

    frames: dict[int, pd.DataFrame] = {}
    alignment: dict[int, dict[str, float]] = {}
    for year in years:
        inflow = controls[year]
        target_weight = inflow * _THOUSANDS
        scale = target_weight / donor_weight_total
        if target_weight == 0:
            alignment[year] = {
                "control_inflow_thousands": inflow,
                "target_weighted_persons": 0.0,
                "scheduled_weighted_persons": 0.0,
                "residual_persons": 0.0,
                "relative_residual": 0.0,
                "n_rows": 0,
                "donor_weight_scale": 0.0,
            }
            # The existing loop rejects empty scheduled frames. Omitting the
            # executable frame also preserves its ID/RNG state for this year.
            continue
        # Normalize before scaling: a positive subnormal common scale can
        # lose material precision even though the target is representable.
        weight = donor_proportion * target_weight
        person_id = allocator.allocate(len(donor))
        frame_year = year - 1
        row = pd.DataFrame(
            {
                "person_id": person_id,
                "year": np.full(len(donor), frame_year, dtype=np.int64),
                "age": entry_age,
                "sex": sex,
                "birth_year": frame_year - entry_age,
                "weight": weight,
                "start_weight": weight,
                "synthetic_entry": np.ones(len(donor), dtype=bool),
                ENTRY_KIND_COLUMN: np.full(
                    len(donor), entry_kind, dtype=object
                ),
                "entry_year": np.full(len(donor), year, dtype=np.int64),
                "entry_age": entry_age,
                "donor_person_id": donor["person_id"].to_numpy(),
                "donor_source_year": donor["source_year"].to_numpy(),
                "donor_peinusyr": donor["peinusyr"].to_numpy(),
                "donor_prcitshp": donor["prcitshp"].to_numpy(),
                "donor_penatvty": donor["penatvty"].to_numpy(),
                "foreign_born": donor["foreign_born"].to_numpy(dtype=bool),
            }
        )
        if roster_columns is not None:
            for column in roster_columns:
                if column not in row.columns:
                    row[column] = pd.NA
            row = row[
                list(roster_columns)
                + [c for c in row.columns if c not in set(roster_columns)]
            ]
        row = row.sort_values("person_id", kind="stable").reset_index(
            drop=True
        )
        frames[year] = row
        realized = float(row["weight"].sum())
        alignment[year] = {
            "control_inflow_thousands": inflow,
            "target_weighted_persons": target_weight,
            "scheduled_weighted_persons": realized,
            "residual_persons": realized - target_weight,
            "relative_residual": (
                (realized - target_weight) / target_weight
                if target_weight
                else 0.0
            ),
            "n_rows": int(len(row)),
            "donor_weight_scale": scale,
        }

    provenance: dict[str, Any] = {
        "method": "donor_reweighted_to_control",
        "method_detail": (
            "every positive-weight donor appears once per positive-inflow "
            "activation year with its weight "
            "scaled by a single factor, so the cohort's weighted total equals "
            "the control and its composition equals the donor exactly; no RNG "
            "is consumed and no row is resampled"
        ),
        "sizing_basis": "trustees_va2_gross_positive_inflow",
        "sizing_excludes": [
            "outflow (the engine has no emigration law)",
            "adjustment of status (a reclassification, not a new person)",
            "total net change (a residual with no literal composition)",
        ],
        "sizing_basis_disclosure": (
            "a stock-accounting inflow proxy, NOT a count of physical "
            "arrivals: V.A2's temporary-or-unlawfully-present inflow counts "
            "only those who remain to year-end, so the gross total understates "
            "border arrivals and the cohort must not be read as one "
            "(2026 OASDI Trustees Report Table V.A2; the same qualification "
            "PR #218 section 0 states for this control)"
        ),
        "frame_coordinate": (
            "year = activation_year - 1, age = entry_age; the loop's first "
            "step is a mortality draw at the entry age, then aging advances "
            "to entry_age + 1 in the activation year (loop.py:236-239, "
            "262-281; convention per m6_population.py:328-334)"
        ),
        "entry_kind": entry_kind,
        "activation_years": years,
        "scheduled_activation_years": sorted(frames),
        "zero_inflow_years": [year for year in years if controls[year] == 0],
        "id_allocation": (
            "projection-wide SyntheticPersonIdAllocator; loop.py:52-61 raises "
            "on any overlap with reserved_real_ids"
        ),
        "gated": False,
        "report_only": True,
    }
    if control_provenance is not None:
        provenance["control"] = dict(control_provenance)
    if donor_provenance is not None:
        provenance["donor"] = dict(donor_provenance)
    return EntrantSchedule(
        frames=frames, alignment=alignment, provenance=provenance
    )


def entrant_provenance_counters(
    frames: Mapping[int, pd.DataFrame],
) -> dict[str, Any]:
    """Counts by ``entry_kind`` and by year, for the run artifact.

    This is the replacement for inferring an entrant's kind from ID
    arithmetic.  ``harness/m6_runner.py:1026-1032`` and ``:1210-1216`` publish
    a hardcoded ``"immigrant_cohorts": 0`` justified by a comment that holds
    only while no schedule exists; a counter keyed on an explicit column
    survives the schedule existing.
    """
    by_kind: dict[str, int] = {}
    by_year: dict[int, dict[str, Any]] = {}
    weighted_by_kind: dict[str, float] = {}
    for year, frame in sorted(frames.items()):
        if ENTRY_KIND_COLUMN not in frame.columns:
            raise ValueError(
                f"scheduled entries {year} carry no {ENTRY_KIND_COLUMN!r} "
                "column; entrant provenance cannot be counted"
            )
        if (
            not frame[ENTRY_KIND_COLUMN]
            .isin(
                {
                    ENTRY_KIND_BIRTH,
                    ENTRY_KIND_INCUMBENT,
                    ENTRY_KIND_IMMIGRANT,
                    ENTRY_KIND_REALIZED_OPENER,
                }
            )
            .all()
        ):
            raise ValueError(
                "scheduled provenance has missing or unknown entry_kind"
            )
        counts = frame[ENTRY_KIND_COLUMN].value_counts().to_dict()
        by_year[int(year)] = {
            "n_rows": int(len(frame)),
            "weighted_persons": float(frame["weight"].sum()),
            "by_entry_kind": {str(k): int(v) for k, v in counts.items()},
        }
        for kind, count in counts.items():
            by_kind[str(kind)] = by_kind.get(str(kind), 0) + int(count)
            mask = frame[ENTRY_KIND_COLUMN] == kind
            weighted_by_kind[str(kind)] = weighted_by_kind.get(
                str(kind), 0.0
            ) + float(frame.loc[mask, "weight"].sum())
    return {
        "n_rows_by_entry_kind": by_kind,
        "weighted_persons_by_entry_kind": weighted_by_kind,
        "by_activation_year": by_year,
        "immigrant_cohorts": by_kind.get(ENTRY_KIND_IMMIGRANT, 0),
        "counter_basis": (
            f"explicit {ENTRY_KIND_COLUMN!r} column, not ID arithmetic"
        ),
    }
