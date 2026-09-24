"""The opening state for Track A, read from an A3 cohort.

:func:`prepare_track_a_cohort` turns a
:class:`populace_dynamics.cohorts.psid2010.Psid2010Cohort` into:

* the engine's initial slice (the opening year: 2010 for the 2011 wave,
  2008 for the 2009 wave of row R6) with the A4 DI state, the claiming
  state and the marital state the A5 adapters carry;
* a static table of the A3 columns the benefit step reads, with the
  opening-year columns under wave-free names (``age_opening``,
  ``ss_opening``, ``ss_receipt_opening``, ``marital_status_opening``) and
  the anchor wave's ``family_unit_id`` (A1 section 16);
* each member's career through the opening year as ``{year: earnings}``;
* one :class:`OpeningStockRecord` per opening-year Social Security
  recipient whose A3 status maps to a benefit component, with the A1
  section 6 clock.

Provenance guard: the ``data_provenance`` label must agree with the
provenance the A3 builder recorded on the cohort
(``Psid2010Cohort.provenance``, read-only): ``"invented"`` needs a cohort
that the invented generator reproduces (its frames are re-generated from
the recorded seed and compared, and the cohort is rebuilt from them with
its own spec and compared on everything its data determine,
:func:`~populace_dynamics.cohorts.psid2010.cohort_data_sha256`), and
``"registered_real"`` needs a cohort built from inputs that
``load_psid2010_inputs`` read from PSID files and sealed.  A cohort edited
after the build, or assembled by hand, is refused under either label, so a
real PSID cohort cannot be labeled invented and skip the issue #42
registration check.

It never copies the A3 realized death columns (``death_year`` and its
bounds, which include deaths after 2010) into anything the projection
reads: the projection draws mortality.  The one death date it keeps is the
late spouse's, which precedes the 2011 interview and so belongs to the
opening state.

Opening-stock clocks follow A1 (section 6, "Existing
beneficiaries"):

* retired workers: birth year + 62;
* disabled workers, and survivors or spouses under 62 in the opening
  year: the A3 receipt start (``opening_claim_year``, else its upper
  bound), which is never earlier than the observations allow; a disabled
  worker whose receipt starts after the year of attaining 62 (possible
  only under a non-default A3 ``aged_m4_disabled_di_below_age`` or
  ``status_rule``) keeps the age-62 clock (A5 reading; see
  :mod:`~populace_dynamics.cola_track_a.benefits`);
* survivors and spouses aged 62 or older in the opening year: the
  linked worker's clock (birth year + 62, or the year of death when the
  worker died before 62) when A3 links the worker, otherwise the person's
  own birth year + 62.

The own first entitlement year (for the entitlement-clock row R2) is the
A3 receipt start.  Where it would precede the clock it is set to the
clock and flagged (``entitlement_clamped``).  Only a retired worker's or
an aged auxiliary's record can be clamped (every other clock is the
receipt start, or precedes it).  A retired worker's receipt start before
the year of attaining 62 cannot be that benefit's entitlement year.  An
aged auxiliary's can be only if its clock, a proxy (the linked worker's
year of attaining 62 or of death, or the own-62 fallback), is later than
the worker's true clock (for example a disability onset A3 does not
observe); R0 uses the same clock.  No count or amount starts before the
clock, so the clamp changes
no amount; it is a named Track A gap ("Opening-stock entitlement before
the clock"), counted in the cohort diagnostics
(``opening_stock_entitlement_clamped``, and by clock rule) and per R2
beneficiary (``beneficiaries_opening_entitlement_clamped``).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.cohorts import psid2010
from populace_dynamics.cohorts.psid2010 import OpeningStatus, Psid2010Cohort
from populace_dynamics.cola_track_a.config import (
    INVENTED_COHORT_LABEL,
    POPULATIONS,
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
    "track_a_cohort_sha256",
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
#: The static columns, wave-free; A3's opening-year columns are renamed
#: to these by :func:`_opening_columns`.
_STATIC_COLUMNS: tuple[str, ...] = (
    "person_id",
    "family_unit_id",
    "weight",
    "sex",
    "birth_year",
    "age_opening",
    "opening_status",
    "ss_opening",
    "ss_receipt_opening",
    "opening_claim_year",
    "opening_claim_year_upper_bound",
    "opening_claim_age",
    "marital_status_opening",
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
    """Everything the A5 projection and benefit step read.

    ``anchor_wave`` and ``start_year`` name the population (A1 section
    14): 2011 and 2010 for R0 and its one-field variants, 2009 and 2008
    for R6.

    ``seal`` is set by :func:`prepare_track_a_cohort` only (it is not a
    constructor argument, and ``dataclasses.replace`` resets it to
    ``None``): the :func:`track_a_cohort_sha256` of the prepared cohort.
    The runner refuses a cohort whose seal is missing or no longer
    matches, so a prepared cohort cannot be relabelled, have its source
    provenance replaced, or be edited in place and still run.
    """

    persons: pd.DataFrame
    careers: Mapping[int, Mapping[int, float]]
    initial_slice: pd.DataFrame
    opening: Mapping[int, OpeningStockRecord]
    data_provenance: str
    labels: tuple[str, ...]
    diagnostics: Mapping[str, Any]
    anchor_wave: int = 2011
    #: The A3 provenance, read-only
    #: (:class:`~populace_dynamics.cohorts.psid2010.ReadOnlyProvenance`).
    source_provenance: Mapping[str, Any] = field(default_factory=dict)
    seal: str | None = field(
        default=None, init=False, repr=False, compare=False
    )

    @property
    def start_year(self) -> int:
        return int(self.anchor_wave) - 1

    @cached_property
    def roster_ids(self) -> frozenset[int]:
        return frozenset(int(pid) for pid in self.initial_slice["person_id"])

    @cached_property
    def persons_by_id(self) -> pd.DataFrame:
        return self.persons.set_index("person_id", drop=False)


def _frame_digest(digest: Any, name: str, frame: pd.DataFrame) -> None:
    digest.update(f"{name}\n".encode())
    digest.update(json.dumps([str(c) for c in frame.columns]).encode())
    digest.update(json.dumps([str(t) for t in frame.dtypes]).encode())
    digest.update(
        frame.to_csv(index=False, lineterminator="\n").encode("utf-8")
    )


def track_a_cohort_sha256(cohort: TrackACohort) -> str:
    """SHA-256 of everything a prepared cohort gives the projection.

    Covers the label (``data_provenance``), the output labels, the anchor
    wave, the A3 source provenance, the diagnostics, the persons, the
    initial slice, the careers and the opening-stock records, so a
    relabelled, replaced or edited cohort no longer matches the seal
    :func:`prepare_track_a_cohort` set.
    """

    header = {
        "data_provenance": cohort.data_provenance,
        "labels": list(cohort.labels),
        "anchor_wave": int(cohort.anchor_wave),
        "source_provenance": dict(cohort.source_provenance),
        "diagnostics": dict(cohort.diagnostics),
        "opening": {
            str(pid): record.as_dict()
            for pid, record in sorted(cohort.opening.items())
        },
        "careers": {
            str(pid): {
                str(year): float(value)
                for year, value in sorted(career.items())
            }
            for pid, career in sorted(cohort.careers.items())
        },
    }
    digest = hashlib.sha256(
        json.dumps(
            header, sort_keys=True, separators=(",", ":"), default=str
        ).encode("utf-8")
    )
    _frame_digest(digest, "persons", cohort.persons)
    _frame_digest(digest, "initial_slice", cohort.initial_slice)
    return digest.hexdigest()


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
    row: Any, config: TrackAConfig, start_year: int
) -> tuple[OpeningStockRecord | None, str | None]:
    """The record for one opening-year recipient, or why there is none."""

    status = str(row.opening_status)
    if status == OpeningStatus.SURVIVOR.value:
        component = (
            "aged_widow"
            if int(row.age_opening) >= config.opening_aged_widow_min_age
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
    elif (
        status == OpeningStatus.DISABLED_WORKER.value
        and receipt_start > birth + _RETIREMENT_AGE
    ):
        # Only a non-default A3 spec (aged_m4_disabled_di_below_age, or
        # status_rule=reported_type) yields a disabled worker whose
        # receipt starts after 62; the PIA already runs on the age-62
        # clock (benefits module docstring).
        clock_year, rule = birth + _RETIREMENT_AGE, "own_birth_plus_62_di"
    elif status == OpeningStatus.DISABLED_WORKER.value or (
        int(row.age_opening) < _RETIREMENT_AGE
    ):
        clock_year, rule = receipt_start, "a3_receipt_start"
    else:
        linked = _linked_worker_clock(row, start_year)
        if linked is None:
            clock_year = birth + _RETIREMENT_AGE
            rule = "fallback_own_birth_plus_62"
        else:
            clock_year, rule = linked
    if clock_year > start_year:
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
            observed_annual_amount=float(row.ss_opening),
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


def _initial_slice(persons: pd.DataFrame, start_year: int) -> pd.DataFrame:
    status = persons["opening_status"].astype(str)
    receipt = persons["ss_receipt_opening"].fillna(False).astype(bool)
    disabled = (status == OpeningStatus.DISABLED_WORKER.value).to_numpy()
    retired = (status == OpeningStatus.RETIRED_WORKER.value).to_numpy()
    no_na = pd.array([pd.NA] * len(persons), dtype="Int64")
    frame = pd.DataFrame(
        {
            "person_id": persons["person_id"].astype("int64"),
            "year": np.full(len(persons), start_year, dtype=np.int64),
            "age": (start_year - persons["birth_year"]).astype("int64"),
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
            "marital_status": persons["marital_status_opening"]
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


def _check_source_provenance(
    cohort: Psid2010Cohort, data_provenance: str
) -> psid2010.ReadOnlyProvenance:
    """Refuse a label that contradicts the cohort's builder-set provenance.

    The provenance record is only a claim (anyone can compute a digest),
    so an ``invented`` label is accepted only when the invented generator
    reproduces the cohort: its frames for the recorded seed must hash to
    the recorded digest, and the cohort rebuilt from them with the
    cohort's own spec must equal the cohort on
    :func:`~populace_dynamics.cohorts.psid2010.cohort_data_sha256`.
    """

    recorded = dict(cohort.provenance)
    kind = recorded.get("kind")
    if kind not in (psid2010.PSID_FILES, psid2010.INVENTED):
        raise ValueError(
            f"the A3 cohort's provenance is {kind!r}: it was not built by "
            "build_psid2010_cohort from recorded PSID files or from the "
            "invented generator (or it was replaced after the build), so "
            "neither data_provenance label can be verified"
        )
    if recorded.get("content_sha256") != psid2010.cohort_content_sha256(
        cohort
    ):
        raise ValueError(
            "the A3 cohort's persons or careers changed after the build; "
            "its recorded provenance no longer describes them"
        )
    if data_provenance == INVENTED:
        if kind != psid2010.INVENTED:
            raise ValueError(
                f"data_provenance 'invented' contradicts the cohort's "
                f"provenance {kind!r}: a cohort built from PSID files "
                "cannot be labeled invented (it would skip the issue #42 "
                "registration check)"
            )
        # Imported here: the generator module is needed only for this
        # check, and only for invented cohorts.
        from populace_dynamics.cola_track_a import invented

        seed = recorded.get("seed")
        regenerated = invented.invented_frames_sha256(
            seed=seed, anchor_wave=cohort.anchor_wave
        )
        if regenerated is None or regenerated != recorded.get(
            "input_frames_sha256"
        ):
            raise ValueError(
                "the cohort claims invented provenance, but the invented "
                f"generator with seed {seed!r} and anchor wave "
                f"{cohort.anchor_wave} does not produce its input frames"
            )
        rebuilt = invented.regenerate_invented_cohort(
            seed=seed, spec=cohort.spec
        )
        if psid2010.cohort_data_sha256(rebuilt) != psid2010.cohort_data_sha256(
            cohort
        ):
            raise ValueError(
                "the cohort claims invented provenance, but its persons or "
                "careers are not what the invented generator with seed "
                f"{seed!r} and the cohort's spec produce"
            )
    elif kind != psid2010.PSID_FILES:
        raise ValueError(
            f"data_provenance 'registered_real' contradicts the cohort's "
            f"provenance {kind!r}: a registered run needs a cohort built "
            "from recorded PSID files"
        )
    return psid2010.ReadOnlyProvenance(recorded)


def _opening_columns(cohort: Psid2010Cohort) -> pd.DataFrame:
    """A3 persons with the opening-year columns under wave-free names."""

    start = cohort.start_year
    renamed = {
        f"age_{start}": "age_opening",
        f"ss_{start}": "ss_opening",
        f"ss_receipt_{start}": "ss_receipt_opening",
        f"marital_status_{start}": "marital_status_opening",
    }
    missing = set(renamed) - set(cohort.persons.columns)
    if missing:
        raise ValueError(f"A3 persons lack columns {sorted(missing)}")
    return cohort.persons.rename(columns=renamed)


def prepare_track_a_cohort(
    cohort: Psid2010Cohort,
    *,
    data_provenance: str,
    config: TrackAConfig | None = None,
) -> TrackACohort:
    """Build the Track A opening state from an A3 cohort.

    ``data_provenance`` is ``"invented"`` for the dry run and tests, or
    ``"registered_real"`` for the one-shot run that the issue #42
    registration must precede; the runner enforces the pointer.  The label
    must agree with the provenance the A3 builder recorded on ``cohort``
    (module docstring); a contradiction is refused.  The opening year is
    the cohort's (its anchor wave's income year).
    """

    config = config or TrackAConfig()
    if data_provenance not in (INVENTED, REGISTERED_REAL):
        raise ValueError(
            f"data_provenance must be {INVENTED!r} or {REGISTERED_REAL!r}"
        )
    if not isinstance(cohort, Psid2010Cohort):
        raise TypeError("cohort must be a Psid2010Cohort (plan item A3)")
    if cohort.anchor_wave not in POPULATIONS:
        raise ValueError(
            f"anchor wave {cohort.anchor_wave} is not a registered "
            f"population ({sorted(POPULATIONS)})"
        )
    source_provenance = _check_source_provenance(cohort, data_provenance)
    start_year = cohort.start_year
    a3_persons = _opening_columns(cohort)
    missing = set(_STATIC_COLUMNS) - set(a3_persons.columns)
    if missing:
        raise ValueError(f"A3 persons lack columns {sorted(missing)}")
    persons = (
        a3_persons[list(_STATIC_COLUMNS)]
        .sort_values("person_id", kind="stable")
        .reset_index(drop=True)
        .copy()
    )
    if persons["person_id"].duplicated().any():
        raise ValueError("A3 persons contain duplicate person_id")
    if (persons["age_opening"] != start_year - persons["birth_year"]).any():
        raise ValueError(f"A3 age_{start_year} disagrees with the start year")
    opening: dict[int, OpeningStockRecord] = {}
    excluded: dict[str, int] = {}
    clock_rules: dict[str, int] = {}
    receipt = persons["ss_receipt_opening"].fillna(False).astype(bool)
    for row in persons[receipt].itertuples(index=False):
        record, reason = _opening_record(row, config, start_year)
        if record is None:
            excluded[str(reason)] = excluded.get(str(reason), 0) + 1
            continue
        opening[record.person_id] = record
        clock_rules[record.clock_rule] = (
            clock_rules.get(record.clock_rule, 0) + 1
        )
    initial = _initial_slice(persons, start_year)
    roster = set(int(pid) for pid in initial["person_id"])
    married = initial["marital_status"] == "married"
    spouse = initial["spouse_person_id"]
    labels = (
        (INVENTED_COHORT_LABEL, *TRACK_A_LABELS[1:])
        if data_provenance == INVENTED
        else TRACK_A_LABELS
    )
    diagnostics = {
        "anchor_wave": cohort.anchor_wave,
        "start_year": start_year,
        "source_provenance_kind": source_provenance["kind"],
        "members": int(len(persons)),
        "family_units": int(persons["family_unit_id"].nunique()),
        "weighted_members": float(persons["weight"].sum()),
        "recipients_opening_year": int(receipt.sum()),
        "ss_opening_year_unobserved": int(
            persons["ss_receipt_opening"].isna().sum()
        ),
        "opening_stock_records": len(opening),
        "opening_stock_by_component": _count(
            record.component for record in opening.values()
        ),
        "opening_stock_clock_rules": dict(sorted(clock_rules.items())),
        "opening_stock_entitlement_clamped": sum(
            record.entitlement_clamped for record in opening.values()
        ),
        "opening_stock_entitlement_clamped_by_clock_rule": _count(
            record.clock_rule
            for record in opening.values()
            if record.entitlement_clamped
        ),
        "opening_recipients_without_record": dict(sorted(excluded.items())),
        "opening_di_entitled": int(initial["di_entitled"].sum()),
        "married_with_spouse_outside_roster": int(
            (married & spouse.notna() & ~spouse.isin(roster)).sum()
        ),
        "married_without_linked_spouse": int((married & spouse.isna()).sum()),
        "widowed_opening_year": int(
            (initial["marital_status"] == "widowed").sum()
        ),
        "a3_spec": cohort.spec.as_dict(),
    }
    prepared = TrackACohort(
        persons=persons,
        careers=_careers(cohort),
        initial_slice=initial,
        opening=opening,
        data_provenance=data_provenance,
        labels=labels,
        diagnostics=diagnostics,
        anchor_wave=cohort.anchor_wave,
        source_provenance=source_provenance,
    )
    object.__setattr__(prepared, "seal", track_a_cohort_sha256(prepared))
    return prepared


def _count(values) -> dict[str, int]:
    out: dict[str, int] = {}
    for value in values:
        out[str(value)] = out.get(str(value), 0) + 1
    return dict(sorted(out.items()))
