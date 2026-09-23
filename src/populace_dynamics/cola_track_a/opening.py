"""The 2010 opening state for Track A, read from an A3 cohort.

:func:`prepare_track_a_cohort` turns a
:class:`populace_dynamics.cohorts.psid2010.Psid2010Cohort` into:

* the engine's initial slice (year 2010) with the A4 DI state, the
  claiming state and the marital state the A5 adapters carry;
* a static table of the A3 columns the benefit step reads;
* each member's 1968-2010 career as ``{year: earnings}``;
* one :class:`OpeningStockRecord` per 2010 Social Security recipient whose
  A3 status maps to a benefit component, with the A1 section 6 clock.

It never copies the A3 realized death columns (``death_year`` and its
bounds, which include deaths after 2010) into anything the projection
reads: the projection draws mortality.  The one death date it keeps is the
late spouse's, which precedes the 2011 interview and so belongs to the
opening state.

Opening-stock clocks follow the A1 draft (section 6, "Existing
beneficiaries"):

* retired workers: birth year + 62;
* disabled workers, and survivors or spouses under 62 in 2010: the A3
  receipt start (``opening_claim_year``, else its upper bound), which is
  never earlier than the observations allow;
* survivors and spouses aged 62 or older in 2010: the linked worker's
  clock (birth year + 62, or the year of death when the worker died
  before 62) when A3 links the worker, otherwise the person's own birth
  year + 62.

The own first entitlement year (for the entitlement-clock row R2) is the
A3 receipt start.  Where it would precede the clock it is set to the
clock and flagged.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import cached_property
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.cohorts.psid2010 import OpeningStatus, Psid2010Cohort
from populace_dynamics.cola_track_a.config import (
    INVENTED_COHORT_LABEL,
    TRACK_A_LABELS,
    TrackAConfig,
)
from populace_dynamics.estimates.cola_age_profile import (
    INVENTED,
    REGISTERED_REAL,
)

__all__ = [
    "INITIAL_SLICE_COLUMNS",
    "MARITAL_COLUMNS",
    "OpeningStockRecord",
    "TrackACohort",
    "prepare_track_a_cohort",
]

#: Marital columns the A5 marital step owns.
MARITAL_COLUMNS: tuple[str, ...] = (
    "marital_status",
    "spouse_person_id",
    "widowhood_year",
    "late_spouse_person_id",
    "widowed_in_projection",
)
INITIAL_SLICE_COLUMNS: tuple[str, ...] = (
    "person_id",
    "year",
    "age",
    "sex",
    "birth_year",
    "weight",
    "di_entitled",
    "di_award_year",
    "di_conversion_year",
    "di_recovery_year",
    "claimed",
    "claim_age",
    "claim_year",
    *MARITAL_COLUMNS,
)
_STATIC_COLUMNS: tuple[str, ...] = (
    "person_id",
    "interview_2011",
    "weight",
    "sex",
    "birth_year",
    "age_2010",
    "opening_status",
    "ss_2008",
    "ss_2010",
    "ss_receipt_2010",
    "opening_claim_year",
    "opening_claim_year_upper_bound",
    "opening_claim_age",
    "marital_status_2010",
    "spouse_person_id",
    "late_spouse_person_id",
    "late_spouse_death_year",
    "widowhood_year",
    "linked_spouse_birth_year",
)
_COMPONENT_BY_STATUS = {
    OpeningStatus.RETIRED_WORKER.value: "retired_worker",
    OpeningStatus.DISABLED_WORKER.value: "disabled_worker",
    OpeningStatus.SPOUSE.value: "spouse",
}
_AUXILIARY_STATUSES = (
    OpeningStatus.SURVIVOR.value,
    OpeningStatus.SPOUSE.value,
)
_RETIREMENT_AGE = 62


@dataclass(frozen=True)
class OpeningStockRecord:
    """A 2010 recipient's fixed benefit basis (A1 section 11, rule 4)."""

    person_id: int
    status: str
    component: str
    observed_annual_amount: float
    clock_year: int
    clock_rule: str
    entitlement_year: int
    entitlement_clamped: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "person_id": self.person_id,
            "status": self.status,
            "component": self.component,
            "observed_annual_amount": self.observed_annual_amount,
            "clock_year": self.clock_year,
            "clock_rule": self.clock_rule,
            "entitlement_year": self.entitlement_year,
            "entitlement_clamped": self.entitlement_clamped,
        }


@dataclass(frozen=True)
class TrackACohort:
    """Everything the A5 projection and benefit step read."""

    persons: pd.DataFrame
    careers: Mapping[int, Mapping[int, float]]
    initial_slice: pd.DataFrame
    opening: Mapping[int, OpeningStockRecord]
    data_provenance: str
    labels: tuple[str, ...]
    diagnostics: Mapping[str, Any]

    @cached_property
    def roster_ids(self) -> frozenset[int]:
        return frozenset(int(pid) for pid in self.initial_slice["person_id"])

    @cached_property
    def persons_by_id(self) -> pd.DataFrame:
        return self.persons.set_index("person_id", drop=False)


def _int_or_none(value: Any) -> int | None:
    return None if pd.isna(value) else int(value)


def _receipt_start(row: Any) -> int | None:
    start = _int_or_none(row.opening_claim_year)
    if start is None:
        start = _int_or_none(row.opening_claim_year_upper_bound)
    return start


def _linked_worker_clock(row: Any, start_year: int) -> tuple[int, str] | None:
    """The linked worker's clock for an aged auxiliary, if A3 links one."""

    birth = _int_or_none(row.linked_spouse_birth_year)
    if birth is None:
        return None
    if row.opening_status == OpeningStatus.SURVIVOR.value:
        death = _int_or_none(row.late_spouse_death_year)
        if death is None:
            death = _int_or_none(row.widowhood_year)
        if death is not None and death < birth + _RETIREMENT_AGE:
            clock = (death, "linked_worker_death_before_eligibility")
        else:
            clock = (birth + _RETIREMENT_AGE, "linked_worker_birth_plus_62")
    else:
        clock = (birth + _RETIREMENT_AGE, "linked_worker_birth_plus_62")
    if clock[0] > start_year:
        return None
    return clock


def _opening_record(
    row: Any, config: TrackAConfig
) -> tuple[OpeningStockRecord | None, str | None]:
    """The record for one 2010 recipient, or the reason there is none."""

    status = str(row.opening_status)
    if status == OpeningStatus.SURVIVOR.value:
        component = (
            "aged_widow"
            if int(row.age_2010) >= config.opening_aged_widow_min_age
            else "disabled_widow"
        )
    elif status in _COMPONENT_BY_STATUS:
        component = _COMPONENT_BY_STATUS[status]
    else:
        return None, f"unmapped_status_{status}"
    receipt_start = _receipt_start(row)
    if receipt_start is None:
        return None, "no_receipt_start"
    birth = int(row.birth_year)
    if status == OpeningStatus.RETIRED_WORKER.value:
        clock_year, rule = birth + _RETIREMENT_AGE, "own_birth_plus_62"
    elif status == OpeningStatus.DISABLED_WORKER.value or (
        int(row.age_2010) < _RETIREMENT_AGE
    ):
        clock_year, rule = receipt_start, "a3_receipt_start"
    else:
        linked = _linked_worker_clock(row, config.start_year)
        if linked is None:
            clock_year = birth + _RETIREMENT_AGE
            rule = "fallback_own_birth_plus_62"
        else:
            clock_year, rule = linked
    if clock_year > config.start_year:
        return None, "clock_after_opening_year"
    entitlement = receipt_start
    clamped = entitlement < clock_year
    if clamped:
        entitlement = clock_year
    return (
        OpeningStockRecord(
            person_id=int(row.person_id),
            status=status,
            component=component,
            observed_annual_amount=float(row.ss_2010),
            clock_year=int(clock_year),
            clock_rule=rule,
            entitlement_year=int(entitlement),
            entitlement_clamped=bool(clamped),
        ),
        None,
    )


def _careers(cohort: Psid2010Cohort) -> dict[int, dict[int, float]]:
    careers: dict[int, dict[int, float]] = {
        int(pid): {} for pid in cohort.persons["person_id"]
    }
    rows = cohort.careers[["person_id", "year", "earnings"]]
    for pid, year, earnings in rows.itertuples(index=False, name=None):
        value = float(earnings)
        if not np.isfinite(value) or value < 0:
            raise ValueError(f"invalid career earnings for person {pid}")
        careers[int(pid)][int(year)] = value
    return careers


def _initial_slice(
    persons: pd.DataFrame, config: TrackAConfig
) -> pd.DataFrame:
    status = persons["opening_status"].astype(str)
    receipt = persons["ss_receipt_2010"].fillna(False).astype(bool)
    disabled = (status == OpeningStatus.DISABLED_WORKER.value).to_numpy()
    retired = (status == OpeningStatus.RETIRED_WORKER.value).to_numpy()
    no_na = pd.array([pd.NA] * len(persons), dtype="Int64")
    frame = pd.DataFrame(
        {
            "person_id": persons["person_id"].astype("int64"),
            "year": np.full(len(persons), config.start_year, dtype=np.int64),
            "age": (config.start_year - persons["birth_year"]).astype("int64"),
            "sex": persons["sex"].astype(str),
            "birth_year": persons["birth_year"].astype("int64"),
            "weight": persons["weight"].astype("float64"),
            "di_entitled": disabled,
            "di_award_year": pd.array(
                persons["opening_claim_year"].where(disabled),
                dtype="Int64",
            ),
            "di_conversion_year": no_na.copy(),
            "di_recovery_year": no_na.copy(),
            "claimed": (receipt.to_numpy() & ~disabled),
            "claim_age": pd.array(
                persons["opening_claim_age"].where(retired), dtype="Int64"
            ),
            "claim_year": pd.array(
                persons["opening_claim_year"].where(
                    receipt.to_numpy() & ~disabled
                ),
                dtype="Int64",
            ),
            "marital_status": persons["marital_status_2010"]
            .astype(str)
            .to_numpy(dtype=object),
            "spouse_person_id": pd.array(
                persons["spouse_person_id"], dtype="Int64"
            ),
            "widowhood_year": pd.array(
                persons["widowhood_year"], dtype="Int64"
            ),
            "late_spouse_person_id": pd.array(
                persons["late_spouse_person_id"], dtype="Int64"
            ),
            "widowed_in_projection": np.zeros(len(persons), dtype=bool),
        }
    )
    return frame.sort_values("person_id", kind="stable").reset_index(
        drop=True
    )[list(INITIAL_SLICE_COLUMNS)]


def prepare_track_a_cohort(
    cohort: Psid2010Cohort,
    *,
    data_provenance: str,
    config: TrackAConfig | None = None,
) -> TrackACohort:
    """Build the Track A opening state from an A3 cohort.

    ``data_provenance`` is ``"invented"`` for the dry run and tests, or
    ``"registered_real"`` for the one-shot run that the issue #42
    registration must precede; the runner enforces the pointer.
    """

    config = config or TrackAConfig()
    if data_provenance not in (INVENTED, REGISTERED_REAL):
        raise ValueError(
            f"data_provenance must be {INVENTED!r} or {REGISTERED_REAL!r}"
        )
    if not isinstance(cohort, Psid2010Cohort):
        raise TypeError("cohort must be a Psid2010Cohort (plan item A3)")
    missing = set(_STATIC_COLUMNS) - set(cohort.persons.columns)
    if missing:
        raise ValueError(f"A3 persons lack columns {sorted(missing)}")
    persons = (
        cohort.persons[list(_STATIC_COLUMNS)]
        .sort_values("person_id", kind="stable")
        .reset_index(drop=True)
        .copy()
    )
    if persons["person_id"].duplicated().any():
        raise ValueError("A3 persons contain duplicate person_id")
    if (
        persons["age_2010"] != config.start_year - persons["birth_year"]
    ).any():
        raise ValueError("A3 age_2010 disagrees with the start year")
    opening: dict[int, OpeningStockRecord] = {}
    excluded: dict[str, int] = {}
    clock_rules: dict[str, int] = {}
    receipt = persons["ss_receipt_2010"].fillna(False).astype(bool)
    for row in persons[receipt].itertuples(index=False):
        record, reason = _opening_record(row, config)
        if record is None:
            excluded[str(reason)] = excluded.get(str(reason), 0) + 1
            continue
        opening[record.person_id] = record
        clock_rules[record.clock_rule] = (
            clock_rules.get(record.clock_rule, 0) + 1
        )
    initial = _initial_slice(persons, config)
    roster = set(int(pid) for pid in initial["person_id"])
    married = initial["marital_status"] == "married"
    spouse = initial["spouse_person_id"]
    labels = (
        (INVENTED_COHORT_LABEL, *TRACK_A_LABELS[1:])
        if data_provenance == INVENTED
        else TRACK_A_LABELS
    )
    diagnostics = {
        "members": int(len(persons)),
        "weighted_members": float(persons["weight"].sum()),
        "recipients_2010": int(receipt.sum()),
        "ss_2010_unobserved": int(persons["ss_receipt_2010"].isna().sum()),
        "opening_stock_records": len(opening),
        "opening_stock_by_component": _count(
            record.component for record in opening.values()
        ),
        "opening_stock_clock_rules": dict(sorted(clock_rules.items())),
        "opening_stock_entitlement_clamped": sum(
            record.entitlement_clamped for record in opening.values()
        ),
        "opening_recipients_without_record": dict(sorted(excluded.items())),
        "opening_di_entitled": int(initial["di_entitled"].sum()),
        "married_with_spouse_outside_roster": int(
            (married & spouse.notna() & ~spouse.isin(roster)).sum()
        ),
        "married_without_linked_spouse": int((married & spouse.isna()).sum()),
        "widowed_2010": int((initial["marital_status"] == "widowed").sum()),
        "a3_spec": {
            key: (value.value if hasattr(value, "value") else value)
            for key, value in vars(cohort.spec).items()
        },
    }
    return TrackACohort(
        persons=persons,
        careers=_careers(cohort),
        initial_slice=initial,
        opening=opening,
        data_provenance=data_provenance,
        labels=labels,
        diagnostics=diagnostics,
    )


def _count(values) -> dict[str, int]:
    out: dict[str, int] = {}
    for value in values:
        out[str(value)] = out.get(str(value), 0) + 1
    return dict(sorted(out.items()))
