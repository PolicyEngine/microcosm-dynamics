"""Track M records to receipt flags: the rules side of plan items M5 and M8.

Python rules (not Axiom).  The M1 specification (``m1-draft-2``) defines,
for every worker record, the years of section 4a, the one history *Y* and
*P* read, the PIA, the worker flag under each option, and, for every
person in the universe, whether they receive the minimum (*A*, G23).  This
module applies those rules to records the cohort supplies:

* :class:`WorkerRecord`: one worker record (section 4a's basis, window
  year, onset or death year; the observed labor income and the next-wave
  odd-year items; MS5's inputs).  The M4 cohort and M5 careers build them
  from the PSID (not built); :mod:`.invented` builds INVENTED ones.
* :class:`PersonRecord`: one person of the universe (weight, sex, design
  variables, their own worker record, their links to a spouse's or a
  deceased spouse's record, and whether they are an unlinked auxiliary).
  :class:`TrackMInputs` refuses a link to a missing record and the links
  section 4b cannot produce: an own death-basis record, a spouse's link
  to a death-basis record, a link to the person's own record.  It also
  refuses MS5 inputs outside section 6's scope: a record in MS5's scope
  that a survivor's link names (a deceased worker) or that is not the own
  record of a person paid their own worker benefit.
* :func:`evaluate`: every record under one registered row's policy, to one
  row per person with ``receives_<k>`` for options 2-5, plus the
  diagnostics of G21 (the referee's O2 included).

It reads no file.  It never sees a comparator value.  The tabulation
(:mod:`.tabulation`) turns its rows into Table 6's shares and refuses rows
built from PSID files without the issue #42 registration pointer.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.min_benefit_track_m import coverage, rules
from populace_dynamics.min_benefit_track_m.policy import (
    OPTIONS,
    PIA_BENEFIT_IMPLIED,
    TABLE6_OPTIONS,
    TrackMPolicy,
)
from populace_dynamics.ss.params import SSAParameters

__all__ = [
    "INVENTED",
    "Evaluation",
    "Link",
    "PROVENANCE_KINDS",
    "PSID_FILES",
    "PersonRecord",
    "SEXES",
    "TrackMInputs",
    "TrackMParameters",
    "WorkerOutcome",
    "WorkerRecord",
    "evaluate",
    "evaluate_worker_record",
    "needed_threshold_years",
]

#: The provenance kind of records built from the staged PSID files (the
#: M4 cohort and M5 careers) and of INVENTED records (:mod:`.invented`).
PSID_FILES = "psid_files"
INVENTED = "invented"
PROVENANCE_KINDS: tuple[str, ...] = (INVENTED, PSID_FILES)
#: ER32000's codes as the universe reads them: code 9 is "unknown", which
#: counts in All and in neither Men nor Women (section 4b rule 7).
SEXES: tuple[str, ...] = ("male", "female", "unknown")
_LINK_KINDS = ("spouse", "survivor")


def _year_map(values: Mapping[int, float], label: str) -> dict[int, float]:
    out = {}
    for year, value in values.items():
        if isinstance(year, bool) or not isinstance(year, int):
            raise TypeError(f"{label} year {year!r} must be an int")
        out[year] = float(value)
    return out


@dataclass(frozen=True)
class WorkerRecord:
    """One worker record (the M1 specification, sections 4a, 4b and 6).

    ``observed`` is the earnings panel's labor income by year (treated as
    covered earnings, d280); ``next_wave`` the next wave's year-before-last
    labor income for odd years 2001-2021.  ``ms5_in_scope`` marks a record
    whose 2022 person-level amount is its own worker benefit alone (section
    6); it then carries ``observed_benefit_2022`` (*B*, monthly),
    ``claim_factor`` and ``cola_factor``.  ``unresolved`` marks a record
    whose window membership section 4b rule 3 resolved by the age rule.
    """

    record_id: str
    birth_year: int
    basis: str
    window_year: int
    observed: Mapping[int, float]
    next_wave: Mapping[int, float] = field(default_factory=dict)
    onset_year: int | None = None
    death_year: int | None = None
    ms5_in_scope: bool = False
    observed_benefit_2022: float | None = None
    claim_factor: float | None = None
    cola_factor: float | None = None
    unresolved: bool = False

    def __post_init__(self) -> None:
        if not self.record_id:
            raise ValueError("a worker record needs an id")
        object.__setattr__(
            self, "observed", _year_map(self.observed, "observed")
        )
        object.__setattr__(
            self, "next_wave", _year_map(self.next_wave, "next_wave")
        )
        _ = self.years  # section 4a validates the dates
        ms5 = (self.observed_benefit_2022, self.claim_factor, self.cola_factor)
        if self.ms5_in_scope and any(value is None for value in ms5):
            raise ValueError(
                f"{self.record_id}: an MS5 record needs its observed "
                "benefit, claim factor and COLA factor"
            )
        if self.basis == rules.BASIS_DEATH and self.ms5_in_scope:
            raise ValueError(
                f"{self.record_id}: a worker who died before any own "
                "entitlement has no own benefit (MS5 keeps the MS0 PIA)"
            )

    @property
    def years(self) -> rules.RecordYears:
        return rules.record_years(
            basis=self.basis,
            birth_year=self.birth_year,
            window_year=self.window_year,
            onset_year=self.onset_year,
            death_year=self.death_year,
        )


@dataclass(frozen=True)
class Link:
    """A person's link to a linked worker's record (G13; section 4b rule 5).

    ``kind`` is ``"spouse"`` (the linked worker is alive and receives
    OASDI in 2022) or ``"survivor"`` (the linked worker is deceased); the
    cohort creates a link only then.  ``months_early`` is the auxiliary
    beneficiary's months before their full retirement age (spouse) or
    survivor full retirement age (survivor) at the claim age of section
    4b; ``worker_claim_factor`` is the deceased worker's 402(q)/(w)
    factor (1 for one who died before any own entitlement).
    """

    kind: str
    worker_record_id: str
    months_early: int = 0
    worker_claim_factor: float = 1.0

    def __post_init__(self) -> None:
        if self.kind not in _LINK_KINDS:
            raise ValueError(f"link kind must be one of {_LINK_KINDS}")
        if self.months_early < 0:
            raise ValueError("months_early must be nonnegative")
        if not self.worker_claim_factor > 0:
            raise ValueError("worker_claim_factor must be positive")


@dataclass(frozen=True)
class PersonRecord:
    """One person of the universe (section 10), with their records.

    ``own_record_id`` is the person's own worker record, if any;
    ``paid_own_worker_benefit`` whether they are paid their own worker
    benefit in 2022; ``own_claim_factor`` that benefit's 402(q)/(w) factor
    (the survivor's own amount, section 4b rule 5).  ``unlinked_auxiliary``
    marks a spouse's or survivor's benefit with no linked worker record;
    ``other_member`` a person who is not the reference person or spouse
    (section 10's 103).
    """

    person_id: str
    family_unit_id: str
    weight: float
    sex: str
    stratum: int
    cluster: int
    own_record_id: str | None = None
    paid_own_worker_benefit: bool = False
    own_claim_factor: float | None = None
    links: tuple[Link, ...] = ()
    unlinked_auxiliary: bool = False
    other_member: bool = False

    def __post_init__(self) -> None:
        if self.sex not in SEXES:
            raise ValueError(f"sex must be one of {SEXES}, not {self.sex!r}")
        if not (math.isfinite(float(self.weight)) and self.weight >= 0):
            raise ValueError("weight must be finite and nonnegative")
        if self.paid_own_worker_benefit and self.own_record_id is None:
            raise ValueError(
                f"{self.person_id}: an own worker benefit needs an own record"
            )
        if self.paid_own_worker_benefit and self.own_claim_factor is None:
            raise ValueError(
                f"{self.person_id}: an own worker benefit needs its claim "
                "factor"
            )
        object.__setattr__(self, "links", tuple(self.links))


@dataclass(frozen=True)
class TrackMInputs:
    """The records one run evaluates, and where they came from.

    ``provenance_kind`` is ``"psid_files"`` for records the M4 cohort and
    M5 careers build from staged PSID files and ``"invented"`` for
    :mod:`.invented`'s; the tabulation refuses the first without the issue
    #42 registration pointer.  ``design`` is the sample design frame
    (``stratum``, ``cluster``) the full-sample standard error sums over.
    """

    workers: Mapping[str, WorkerRecord]
    persons: tuple[PersonRecord, ...]
    provenance_kind: str
    design: pd.DataFrame
    source: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.provenance_kind not in PROVENANCE_KINDS:
            raise ValueError(
                f"provenance_kind must be one of {PROVENANCE_KINDS}"
            )
        for key, record in self.workers.items():
            if key != record.record_id:
                raise ValueError(f"worker key {key} != {record.record_id}")
        ids = [person.person_id for person in self.persons]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate person_id")
        for person in self.persons:
            wanted = [link.worker_record_id for link in person.links]
            if person.own_record_id is not None:
                wanted.append(person.own_record_id)
            missing = [key for key in wanted if key not in self.workers]
            if missing:
                raise ValueError(
                    f"{person.person_id}: no worker record {missing}; an "
                    "auxiliary without a linked record is an unlinked "
                    "auxiliary"
                )
            _check_links(person, self.workers)
        _check_ms5_scope(self.persons, self.workers)
        object.__setattr__(self, "persons", tuple(self.persons))


def _check_links(
    person: PersonRecord, workers: Mapping[str, WorkerRecord]
) -> None:
    """Refuse links the M1 specification's section 4b cannot produce.

    A person of the universe is alive in 2023, so their own record cannot
    be a death-basis record (a worker who died before any own
    entitlement); a spouse's benefit needs a living worker (section 4b
    rule 5), so a spouse link cannot name a death-basis record; and no
    link names the person's own record.
    """

    own = person.own_record_id
    if own is not None and workers[own].basis == rules.BASIS_DEATH:
        raise ValueError(
            f"{person.person_id}: an own record cannot be a death-basis "
            "record (a worker who died before any own entitlement)"
        )
    for link in person.links:
        if link.worker_record_id == own:
            raise ValueError(
                f"{person.person_id}: a link names the person's own record"
            )
        basis = workers[link.worker_record_id].basis
        if link.kind == "spouse" and basis == rules.BASIS_DEATH:
            raise ValueError(
                f"{person.person_id}: a spouse's benefit needs a living "
                "worker, not a death-basis record (section 4b rule 5)"
            )


def _check_ms5_scope(
    persons: Iterable[PersonRecord], workers: Mapping[str, WorkerRecord]
) -> None:
    """Refuse MS5 inputs outside the M1 specification's section 6 scope.

    MS5's benefit-implied PIA is for "a worker record whose 2022
    person-level amount (ER35219) is its own worker benefit alone"; "a
    linked worker who is deceased or outside the universe keeps the MS0
    PIA".  So a record marked ``ms5_in_scope`` must be the own record of a
    person of the universe who is paid their own worker benefit in 2022,
    and no survivor's link (a deceased worker) may name it.  (Added by the
    independent review of 2026-09-25: the inputs accepted both.)
    """

    persons = tuple(persons)
    paid_owners = {
        person.own_record_id
        for person in persons
        if person.own_record_id is not None and person.paid_own_worker_benefit
    }
    deceased = {
        link.worker_record_id
        for person in persons
        for link in person.links
        if link.kind == "survivor"
    }
    for key, record in workers.items():
        if not record.ms5_in_scope:
            continue
        if key in deceased:
            raise ValueError(
                f"{key}: a survivor's link names this record, so its worker "
                "is deceased and has no 2022 benefit; it keeps the MS0 PIA "
                "and cannot be in MS5's scope (section 6)"
            )
        if key not in paid_owners:
            raise ValueError(
                f"{key}: an MS5 record must be the own record of a person "
                "of the universe paid their own worker benefit in 2022; a "
                "linked worker outside the universe keeps the MS0 PIA "
                "(section 6)"
            )


@dataclass(frozen=True)
class TrackMParameters:
    """The parameters a run reads: the oracle's, the QC amounts, the
    thresholds."""

    params: SSAParameters
    qc: coverage.QuarterOfCoverageAmounts
    thresholds: rules.AgedThresholds

    @property
    def nawi(self) -> Mapping[int, float]:
        return self.params.nawi

    def source(self) -> dict[str, Any]:
        return {
            "oracle_pe_us_revision": self.params.pe_us_revision,
            "quarter_of_coverage": dict(self.qc.source),
            "thresholds": dict(self.thresholds.source),
        }


@dataclass(frozen=True)
class WorkerOutcome:
    """One worker record under one policy: *Y*, *P* and the option flags."""

    record_id: str
    years: rules.RecordYears
    history: coverage.OneHistory
    count: coverage.CoverageCount
    work_years_without_imputation: int
    history_pia: rules.PiaRecord
    benefit_implied_pia: float | None
    pia: float
    pia_source: str
    outcomes: Mapping[int, rules.OptionOutcome]


def evaluate_worker_record(
    record: WorkerRecord,
    policy: TrackMPolicy,
    parameters: TrackMParameters,
) -> WorkerOutcome:
    """Section 4a's years, the one history, *Y*, *P* and every option."""

    years = record.years
    history = coverage.one_history(
        record.observed,
        record.next_wave,
        last_year=years.last_year,
        policy=policy,
    )
    count = coverage.count_coverage_years(
        history.values,
        birth_year=record.birth_year,
        through_year=years.last_year,
        qc=parameters.qc,
        nawi=parameters.nawi,
        policy=policy,
        gap_years=(),
        imputed_years=history.imputed_years,
    )
    without = sum(
        1 for year in count.counted_years if year not in history.imputed_years
    )
    pia_record = rules.history_pia(
        history.values,
        birth_year=record.birth_year,
        params=parameters.params,
        basis=record.basis,
        window_year=record.window_year,
        onset_year=record.onset_year,
        death_year=record.death_year,
        policy=policy,
    )
    implied = None
    if record.ms5_in_scope:
        implied = rules.benefit_implied_pia(
            record.observed_benefit_2022,
            claim_factor=record.claim_factor,
            cola_factor=record.cola_factor,
        )
    if policy.pia_rule == PIA_BENEFIT_IMPLIED and implied is not None:
        pia, source = implied, "benefit_implied"
    else:
        pia, source = pia_record.pia, "history_oracle"
    inputs = rules.WorkerInputs(
        pia=pia,
        work_years=count.years,
        first_pia_year=years.window_year,
        threshold_year=years.threshold_year,
        birth_year=record.birth_year,
        di_onset_year=(
            years.onset_year
            if record.basis == rules.BASIS_DISABILITY
            else None
        ),
    )
    outcomes = {
        number: rules.evaluate_worker(
            inputs,
            number,
            thresholds=parameters.thresholds,
            nawi=parameters.nawi,
            policy=policy,
        )
        for number in OPTIONS
    }
    return WorkerOutcome(
        record.record_id,
        years,
        history,
        count,
        without,
        pia_record,
        implied,
        pia,
        source,
        outcomes,
    )


def needed_threshold_years(
    workers: Iterable[WorkerRecord], policies: Iterable[TrackMPolicy]
) -> dict[int, int]:
    """Every threshold year a run needs, before anything is computed (R8).

    The policy year of each policy (the wage-indexed base, counted 0) and
    the section 4a threshold year of every record in some policy's window,
    with the number of such records.  A superset of what the flags read:
    a price-indexed threshold is looked up only when *Y*\\* >= 10.
    """

    policies = tuple(policies)
    counts: dict[int, int] = {policy.policy_year: 0 for policy in policies}
    for record in workers:
        years = record.years
        if any(rules.in_window(years.window_year, p) for p in policies):
            counts[years.threshold_year] = (
                counts.get(years.threshold_year, 0) + 1
            )
    return dict(sorted(counts.items()))


def _receipts(
    person: PersonRecord,
    outcomes: Mapping[str, WorkerOutcome],
    policy: TrackMPolicy,
    params: SSAParameters,
) -> dict[int, rules.Receipt]:
    own = (
        outcomes[person.own_record_id]
        if person.own_record_id is not None
        else None
    )
    out = {}
    for number in TABLE6_OPTIONS:
        own_outcome = own.outcomes[number] if own is not None else None
        linked = []
        for link in person.links:
            worker = outcomes[link.worker_record_id].outcomes[number]
            if link.kind == "spouse":
                own_pia = own_outcome.option_pia if own_outcome else 0.0
                paid = rules.spouse_excess_paid(
                    own_pia, worker.option_pia, link.months_early, params
                )
            else:
                own_amount = rules.survivor_own_amount(
                    own_outcome.option_pia if own_outcome else None,
                    person.own_claim_factor,
                    receives_own_benefit=person.paid_own_worker_benefit,
                )
                paid = rules.survivor_excess_paid(
                    own_amount,
                    worker.option_pia,
                    link.months_early,
                    link.worker_claim_factor,
                    params,
                )
            linked.append(
                rules.LinkedBenefit(link.kind, worker.on_minimum, paid)
            )
        out[number] = rules.receives_minimum(
            own_on_minimum=bool(own_outcome and own_outcome.on_minimum),
            paid_own_worker_benefit=person.paid_own_worker_benefit,
            linked=linked,
            unlinked_auxiliary=person.unlinked_auxiliary,
            policy=policy,
        )
    return out


@dataclass(frozen=True)
class Evaluation:
    """One registered row's evaluation: person rows and worker outcomes."""

    rows: pd.DataFrame
    workers: Mapping[str, WorkerOutcome]
    diagnostics: Mapping[str, Any]


_Y_BANDS = ((0, 10), (10, 20), (20, 30), (30, 40), (40, math.inf))
_RATIO_BANDS = (
    (0.0, 0.5),
    (0.5, 0.75),
    (0.75, 1.0),
    (1.0, 1.25),
    (1.25, math.inf),
)


def _band_label(low: float, high: float) -> str:
    return f"{low:g}+" if math.isinf(high) else f"{low:g}-<{high:g}"


def _bands(values: Iterable[float], bands) -> dict[str, int]:
    values = list(values)
    return {
        _band_label(low, high): sum(1 for v in values if low <= v < high)
        for low, high in bands
    }


def _weighted_share(frame: pd.DataFrame, mask: np.ndarray) -> float | None:
    total = float(frame["weight"].sum())
    if total <= 0:
        return None
    return 100.0 * float(frame.loc[mask, "weight"].sum()) / total


def _diagnostics(
    inputs: TrackMInputs,
    outcomes: Mapping[str, WorkerOutcome],
    rows: pd.DataFrame,
    policy: TrackMPolicy,
) -> dict[str, Any]:
    """G21's diagnostics and the referee's O2 (not scored)."""

    in_window = {
        key: out
        for key, out in outcomes.items()
        if rules.in_window(out.years.window_year, policy)
    }
    records = inputs.workers
    by_basis = {basis: 0 for basis in rules.BASES}
    in_window_by_basis = {basis: 0 for basis in rules.BASES}
    for key, record in records.items():
        by_basis[record.basis] += 1
        if key in in_window:
            in_window_by_basis[record.basis] += 1
    stars = {
        key: out.outcomes[2].work_years_star for key, out in in_window.items()
    }
    ratios: dict[str, dict[str, int]] = {}
    for number in TABLE6_OPTIONS:
        values = [
            out.pia / out.outcomes[number].minimum
            for out in in_window.values()
            if out.outcomes[number].minimum > 0
        ]
        ratios[str(number)] = _bands(values, _RATIO_BANDS)
    y_exceeds_d = 0
    for key, out in in_window.items():
        record = records[key]
        if record.basis == rules.BASIS_DISABILITY:
            elapsed = record.onset_year - (
                record.birth_year + policy.di_proration_start_age
            )
            possible = min(max(elapsed, 1), policy.di_proration_cap_years)
            y_exceeds_d += int(out.count.years > possible)
    nesting = sum(
        int(out.outcomes[2].on_minimum and not out.outcomes[4].on_minimum)
        + int(out.outcomes[3].on_minimum and not out.outcomes[5].on_minimum)
        for out in outcomes.values()
    )
    implied = [
        (out.benefit_implied_pia, out.history_pia.pia)
        for out in outcomes.values()
        if out.benefit_implied_pia is not None and out.history_pia.pia > 0
    ]
    implied_ratio = [a / b for a, b in implied]
    exposed = rows["exposed"].to_numpy()
    receiving_other = {}
    for number in TABLE6_OPTIONS:
        receiving = rows[f"receives_{number}"].to_numpy()
        n = int(receiving.sum())
        others = int((receiving & rows["other_member"].to_numpy()).sum())
        receiving_other[str(number)] = {
            "n_receiving": n,
            "n_other_members": others,
            "other_member_share_of_receiving": others / n if n else None,
        }
    pia_sources = {"history_oracle": 0, "benefit_implied": 0}
    for out in outcomes.values():
        pia_sources[out.pia_source] += 1
    return {
        "worker_records_by_basis": by_basis,
        "in_window_records_by_basis": in_window_by_basis,
        "unresolved_in_window": sum(
            1 for key in in_window if records[key].unresolved
        ),
        "earliest_threshold_year_in_window": min(
            (out.years.threshold_year for out in in_window.values()),
            default=None,
        ),
        "exposed_persons": int(exposed.sum()),
        "exposed_weighted_share_percent": _weighted_share(rows, exposed),
        "work_years_star_bands_in_window": _bands(stars.values(), _Y_BANDS),
        "pia_over_minimum_bands_in_window": ratios,
        "di_origin_share_of_in_window_records": (
            in_window_by_basis[rules.BASIS_DISABILITY] / len(in_window)
            if in_window
            else None
        ),
        "di_records_with_y_above_d": y_exceeds_d,
        "records_whose_imputed_odd_years_changed_y": sum(
            1
            for out in in_window.values()
            if out.work_years_without_imputation != out.count.years
        ),
        "unlinked_auxiliaries": int(rows["unlinked_auxiliary"].sum()),
        "unlinked_auxiliary_weighted_share_percent": _weighted_share(
            rows, rows["unlinked_auxiliary"].to_numpy()
        ),
        "other_members_among_receiving": receiving_other,
        "worker_flag_nesting_violations": nesting,
        "pia_source_by_record": pia_sources,
        "benefit_implied_over_history_pia": {
            "n_records": len(implied_ratio),
            "median": (
                float(np.median(implied_ratio)) if implied_ratio else None
            ),
            "p10": (
                float(np.quantile(implied_ratio, 0.1))
                if implied_ratio
                else None
            ),
            "p90": (
                float(np.quantile(implied_ratio, 0.9))
                if implied_ratio
                else None
            ),
        },
        "persons": int(len(rows)),
        "persons_weighted_total": float(rows["weight"].sum()),
    }


def evaluate(
    inputs: TrackMInputs,
    policy: TrackMPolicy,
    parameters: TrackMParameters,
) -> Evaluation:
    """Every record under ``policy``: one row per person, and diagnostics.

    ``rows`` has ``person_id``, ``family_unit_id``, ``weight``, ``sex``,
    ``stratum``, ``cluster``, ``receives_2`` ... ``receives_5`` (*A*,
    G23), ``basis`` (the receipt basis under option 2), ``exposed`` (an
    own or linked worker record in the window), ``other_member`` and
    ``unlinked_auxiliary``; ``rows.attrs["provenance_kind"]`` carries the
    inputs' provenance kind to the tabulation's guard.
    """

    outcomes = {
        key: evaluate_worker_record(record, policy, parameters)
        for key, record in inputs.workers.items()
    }
    table = []
    for person in inputs.persons:
        receipts = _receipts(person, outcomes, policy, parameters.params)
        linked_ids = [link.worker_record_id for link in person.links]
        if person.own_record_id is not None:
            linked_ids.append(person.own_record_id)
        exposed = any(
            rules.in_window(outcomes[key].years.window_year, policy)
            for key in linked_ids
        )
        table.append(
            {
                "person_id": person.person_id,
                "family_unit_id": person.family_unit_id,
                "weight": float(person.weight),
                "sex": person.sex,
                "stratum": int(person.stratum),
                "cluster": int(person.cluster),
                **{
                    f"receives_{number}": bool(receipts[number].receives)
                    for number in TABLE6_OPTIONS
                },
                "basis": receipts[TABLE6_OPTIONS[0]].basis,
                "exposed": bool(exposed),
                "other_member": bool(person.other_member),
                "unlinked_auxiliary": bool(person.unlinked_auxiliary),
            }
        )
    rows = pd.DataFrame(table)
    rows.attrs["provenance_kind"] = inputs.provenance_kind
    return Evaluation(
        rows, outcomes, _diagnostics(inputs, outcomes, rows, policy)
    )
