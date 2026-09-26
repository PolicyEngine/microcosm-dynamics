"""The Track M beneficiary cohort (plan item M4): section 4b's rules.

Python rules (not Axiom).  The M1 specification (``docs/design/
minimum_benefits_comparison.md``, ``m1-draft-2``) defines the universe
(section 10: persons of the 2023 wave in a responding family unit with a
positive cross-section weight, born 1960 or earlier by the first-estimates
birth-year law, receiving OASDI in 2022) and freezes the rules that turn
biennial PSID receipt into each worker record's basis, entitlement year,
onset year and window membership (section 4b).  This module applies them
to the label-verified receipt histories of plan item M3
(:mod:`populace_dynamics.data.social_security_receipt`) and builds, for
every person of the universe, their own worker record, their links to a
living spouse's or a deceased spouse's record, and the flags section 9
needs.  It computes no years of coverage, no PIA, no threshold, no
minimum and no share: those are plan items M5 and M8
(:mod:`.careers`, :mod:`.evaluation`, :mod:`.tabulation`), and this
module imports none of them, nor the rules, so the structural-count
script can load it (``scripts/track_m_structure.py``).

**Receipt observations** (:class:`ReceiptObservation`).  A person-year is
observed when a person-level item describes it (the individual file,
waves 1984-1992 and 2005-2023; the 1993 family file's head and wife
items) or when a family-level item identifies the person (M3's reading:
a family reporting none identifies every member's non-receipt; a
year-before-last "yes" identifies a one-member family's receipt, of an
unknown type in the whether-only waves 2009-2015).
Person-level items take precedence.  An observation is:

* ``none``: no receipt;
* ``auxiliary``: receipt whose every mentioned type is a spouse's,
  survivor's or dependent's (all type items known);
* ``own``: any other receipt, a worker type (retirement, disability), an
  "other" or combination code, or an unknown type.  Section 4b's "own
  receipt" is read as receipt that may be the person's own worker
  benefit; a year of auxiliary receipt only is a year "without own
  receipt" (rule 2).

**Section 4b, as applied** (:func:`classify_own_record`):

1. *Basis.*  A person with an ``own`` year has a worker record.  With
   *F* the first ``own`` year: disability origin when the observation at
   *F* mentions disability or *F* precedes the year of attaining 62;
   otherwise old age (for a type that is unknown or "other" this is the
   rule's age rule).
2. *Entitlement year.*  With *L* the last observed year before *F*
   without own receipt: old age, max(year of attaining 62, *L* + 1);
   disability origin, *L* + 1 (its onset, the entitlement year less one,
   always precedes it).
3. *Records with receipt in their first observed year* (no *L*).  *F*
   before 2004: out of the window at either policy year (entitlement
   precedes *F*); the window year is the year of attaining 62 (old age)
   or *F* (disability origin, which has no earliest year of its own).
   *F* in or after 2004: the rule's age rule, and the record is counted
   unresolved.  At *Y*₀ = 2004 it is in the window if born 1942 or later
   with a retirement type; at *Y*₀ = 2007, if also *F* is 2007 or later
   (so its 2006 receipt was unobserved: a later PSID entrant for 2007)
   and born 1945 or later.  "A retirement type" is read as a retirement
   mention at *F* or an old-age basis (the age rule's old age for a type
   that is unknown or other).  The window year is the earliest year
   consistent with that membership: the year of attaining 62 for old age
   (which reproduces the rule, because an old-age record born 1942 or
   later cannot be entitled before 2004, nor one born 1945 or later
   before 2007), and for disability origin 2007 or 2004 when rule 3
   places it in a window, or 2003, the latest year consistent with its
   being out of both, when it does not.
   *Rule 2 before rule 3.*  Rule 2's second bullet sends to rule 3 only
   a record with receipt in its first observed year, so a record with an
   observed year without own receipt takes rule 2's earliest consistent
   year even when the year just before the policy year is unobserved
   (receipt in 2004, unknown status in 2003, non-receipt observed
   earlier).  Rule 3's clause for "receipt in 2004 and unknown status in
   2003" reads on such a record too; :func:`boundary_year_unobserved`
   counts the records where the two readings could differ, and how many
   they would place in the window, without choosing between them.
4. *Onset* (disability origin): the entitlement year less one.
5. *Links* (section 4b rule 5; G13).  At the end of 2022 (marriage
   history, :func:`populace_dynamics.cohorts.psid2010.marital_state_at`):
   a married person whose spouse is alive and has ``own`` receipt in 2022
   gets a spouse's link to the spouse's record; a widowed person whose
   late spouse's death year is known gets a survivor's link to the late
   spouse's record.  A late spouse with an ``own`` year keeps that basis;
   one with none is a record of a worker who died before any own
   entitlement, whose window year is the survivor's first entitlement on
   the record (the earliest over linking survivors).  Whether the
   auxiliary benefit is paid is the oracle's decision (M5 and M8).
6. *Other family-unit members* stay in the universe (``other_member``).
7. *Sex*: ER32000; code 9 is ``unknown`` (All only).

**Claim years** for the claim factors and months early M5 computes: a
worker's own entitlement year; a survivor's first entitlement on the
deceased's record (the earliest year consistent with their receipt of a
survivor type, or of any receipt when they report none, no earlier than
the death year and the year of attaining 60; a receipt year whose
survivor item is unknown does not bound it, :func:`survivor_claim_year`);
a spouse's claim year (the later of their own or auxiliary entitlement
year, the worker's entitlement year and the year of attaining 62).

**Unlinked auxiliaries.**  A person whose 2022 receipt mentions a
survivor's benefit without a survivor's link, or a dependent's benefit
without a spouse's link.

What this module does not do: compute any benefit, years of coverage,
PIA, threshold, minimum, flag or share.  :func:`cohort_structure` counts
records, classes, links and the threshold *years* in-window records need
(years, never thresholds), with the counts that size the readings above:
records whose year before a policy year is unobserved, death-basis
records whose worker died at 62 or older or in a year no person-level
item records, old-age entitlement ages, and the source of each rule-2
boundary.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from populace_dynamics.cohorts import psid2010
from populace_dynamics.data import prior_year_labor_income as pyl
from populace_dynamics.data import psid
from populace_dynamics.data import social_security_receipt as ssr
from populace_dynamics.estimates import career
from populace_dynamics.min_benefit_track_m import structure

__all__ = [
    "AUXILIARY",
    "BASIS_DEATH",
    "BASIS_DISABILITY",
    "BASIS_OLD_AGE",
    "FIRST_AGE_62_YEAR_ENCODED",
    "NONE",
    "OWN",
    "OwnRecordClass",
    "POLICY_YEARS",
    "ReceiptObservation",
    "RULE3_BIRTH_YEAR",
    "TrackMCohort",
    "TrackMCohortInputs",
    "YEARS_WITHOUT_PERSON_LEVEL_RECEIPT",
    "boundary_year_unobserved",
    "build_cohort",
    "classify_own_record",
    "cohort_structure",
    "history_source_counts",
    "load_cohort_inputs",
    "observation",
    "receipt_histories",
    "record_years",
    "spouse_claim_year",
    "structural_counts_before_registration",
    "survivor_claim_year",
    "unlinked_kind",
]

WAVE = structure.WAVE
INCOME_YEAR = structure.INCOME_YEAR
#: The two policy years section 4b rule 3 classifies at (MS0, MS1).
POLICY_YEARS: tuple[int, ...] = (2004, 2007)
#: Rule 3's birth-year cutoffs for the age rule at each policy year.
RULE3_BIRTH_YEAR: dict[int, int] = {2004: 1942, 2007: 1945}
#: The bases of section 4a (the same strings as ``rules.BASES``).
BASIS_OLD_AGE = "old_age"
BASIS_DISABILITY = "disability"
BASIS_DEATH = "death"
OWN, AUXILIARY, NONE = "own", "auxiliary", "none"
_ELIGIBILITY_AGE = 62
_SURVIVOR_EARLIEST_AGE = 60
#: ``ss.statutory_aime.FIRST_AGE_62_YEAR_ENCODED``: the oracle refuses a
#: worker who attains 62 earlier (a test holds the two equal).
FIRST_AGE_62_YEAR_ENCODED = 1975
#: Income years whose Social Security receipt no person-level item
#: records (M3): the family totals of waves 1994-2003 and the
#: year-before-last items of the 2005-2015 waves are family-level, 1997,
#: 1999, 2001 and the odd years 2015-2021 have no item at all, and the
#: individual file's items cover the even years from 2004 only.  (1992 has the 1993
#: family file's head and wife items.)
YEARS_WITHOUT_PERSON_LEVEL_RECEIPT: tuple[int, ...] = (
    *range(1993, 2004),
    *range(2005, 2022, 2),
)
_PERSON_LEVEL = ("individual", "family_1993")
_FAMILY_LEVEL = ("year_before_last", "total")


# ---------------------------------------------------------------------------
# Observations and classification (pure)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ReceiptObservation:
    """One observed person-year: ``status`` own, auxiliary or none.

    ``types`` are the mentioned types; ``unknown_types`` the types whose
    item the observation leaves unknown (every type for a combination
    code, an unknown code or a whether-only "yes"; the flags coded DK or
    NA).  The default, none unknown, is an observation whose every type
    item is known.
    """

    year: int
    status: str
    types: frozenset[str] = frozenset()
    source: str = "individual"
    unknown_types: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if self.status not in (OWN, AUXILIARY, NONE):
            raise ValueError(f"status {self.status!r}")
        if self.status == NONE and (self.types or self.unknown_types):
            raise ValueError("an observation of no receipt has no types")
        if self.status == AUXILIARY and self.unknown_types:
            raise ValueError("auxiliary receipt needs every type known")
        if not set(self.unknown_types) <= set(ssr.SS_TYPES):
            raise ValueError(f"unknown types {sorted(self.unknown_types)}")
        if self.types & self.unknown_types:
            raise ValueError("a mentioned type cannot be unknown")

    @property
    def mentions_survivor(self) -> bool:
        return "survivor" in self.types

    @property
    def shows_no_survivor_receipt(self) -> bool:
        """No receipt, or receipt whose survivor item is known and not
        mentioned: an observation a survivor's benefit contradicts.  A
        receipt year whose survivor item is unknown shows nothing."""

        if self.status == NONE:
            return True
        return not self.mentions_survivor and (
            "survivor" not in self.unknown_types
        )

    @property
    def receipt(self) -> bool:
        return self.status != NONE


def observation(
    year: int,
    *,
    receipt: bool,
    types: Mapping[str, Any] | None = None,
    combination: bool = False,
    source: str = "individual",
) -> ReceiptObservation:
    """Classify one observed person-year (module docstring).

    ``types`` maps each of ``ssr.SS_TYPES`` to True, False or missing
    (``None``/``pd.NA``).  Receipt is ``auxiliary`` only when every type
    item is known, at least one is mentioned and every mentioned type is
    auxiliary; otherwise ``own``.
    """

    if not receipt:
        return ReceiptObservation(int(year), NONE, frozenset(), source)
    values = dict(types or {})
    known = {}
    for name in ssr.SS_TYPES:
        value = values.get(name)
        if value is None or value is pd.NA:
            continue
        if isinstance(value, float) and math.isnan(value):
            continue
        known[name] = bool(value)
    mentioned = frozenset(name for name, value in known.items() if value)
    all_known = len(known) == len(ssr.SS_TYPES) and not combination
    auxiliary = (
        all_known
        and bool(mentioned)
        and mentioned <= frozenset(ssr.AUXILIARY_TYPES)
    )
    # A combination code names no type, so it leaves every type unknown.
    unknown = frozenset(ssr.SS_TYPES) - (
        mentioned if combination else frozenset(known)
    )
    return ReceiptObservation(
        int(year),
        AUXILIARY if auxiliary else OWN,
        mentioned,
        source,
        unknown,
    )


@dataclass(frozen=True)
class OwnRecordClass:
    """Section 4b's classification of one worker record.

    ``window_year`` is the entitlement year (section 4a's window year);
    ``first_own_year`` *F*; ``last_without_year`` *L* (or ``None``);
    ``resolution`` is ``rule2_observed_boundary``,
    ``receipt_in_first_observation_before_2004`` or ``rule3_age_rule``;
    ``unresolved`` is True for the last; ``rule3_in_window`` records rule
    3's membership at each policy year for an unresolved record;
    ``last_without_source`` is the source of the observation at *L*
    (``individual``, ``family_1993``, ``year_before_last`` or ``total``).
    """

    birth_year: int
    basis: str
    first_own_year: int
    last_without_year: int | None
    window_year: int
    onset_year: int | None
    resolution: str
    unresolved: bool
    retirement_type: bool
    first_types: frozenset[str]
    rule3_in_window: Mapping[int, bool] = field(default_factory=dict)
    last_without_source: str | None = None

    def in_window(
        self, policy_year: int, *, strictly_after: bool = False
    ) -> bool:
        if strictly_after:
            return self.window_year > policy_year
        return self.window_year >= policy_year


def classify_own_record(
    history: Mapping[int, ReceiptObservation] | Iterable[ReceiptObservation],
    birth_year: int,
) -> OwnRecordClass | None:
    """Section 4b rules 1-4 for one person (``None`` without own receipt).

    ``history`` is the person's observations (a year may appear once).
    See the module docstring for the rules as applied.
    """

    observations = (
        dict(history)
        if isinstance(history, Mapping)
        else {obs.year: obs for obs in history}
    )
    for year, obs in observations.items():
        if int(year) != obs.year:
            raise ValueError(f"observation keyed {year} is for {obs.year}")
    birth = int(birth_year)
    own_years = sorted(y for y, o in observations.items() if o.status == OWN)
    if not own_years:
        return None
    first = own_years[0]
    first_obs = observations[first]
    attains_62 = birth + _ELIGIBILITY_AGE
    disability = "disability" in first_obs.types or first < attains_62
    basis = BASIS_DISABILITY if disability else BASIS_OLD_AGE
    retirement_type = basis == BASIS_OLD_AGE or "retirement" in first_obs.types
    without = [
        y for y, o in observations.items() if y < first and o.status != OWN
    ]
    last = max(without) if without else None
    rule3: dict[int, bool] = {}
    if last is not None:
        window = (
            max(attains_62, last + 1) if basis == BASIS_OLD_AGE else last + 1
        )
        resolution, unresolved = "rule2_observed_boundary", False
    elif first < POLICY_YEARS[0]:
        window = attains_62 if basis == BASIS_OLD_AGE else first
        resolution = "receipt_in_first_observation_before_2004"
        unresolved = False
    else:
        in_2004 = birth >= RULE3_BIRTH_YEAR[2004] and retirement_type
        in_2007 = in_2004 and first >= 2007 and birth >= RULE3_BIRTH_YEAR[2007]
        rule3 = {2004: in_2004, 2007: in_2007}
        if basis == BASIS_OLD_AGE:
            window = attains_62
        elif in_2007:
            window = 2007
        elif in_2004:
            window = 2004
        else:
            window = POLICY_YEARS[0] - 1
        resolution, unresolved = "rule3_age_rule", True
    onset = window - 1 if basis == BASIS_DISABILITY else None
    return OwnRecordClass(
        birth_year=birth,
        basis=basis,
        first_own_year=first,
        last_without_year=last,
        window_year=window,
        onset_year=onset,
        resolution=resolution,
        unresolved=unresolved,
        retirement_type=retirement_type,
        first_types=first_obs.types,
        rule3_in_window=rule3,
        last_without_source=(
            None if last is None else observations[last].source
        ),
    )


def record_years(
    basis: str,
    birth_year: int,
    window_year: int,
    *,
    onset_year: int | None = None,
    death_year: int | None = None,
) -> dict[str, int]:
    """Section 4a's threshold year and last year of *Y* and *P*.

    The same table as ``rules.record_years`` (a differential test holds
    them equal), computed here so that the structural counts never load
    the rules: old age, the year of attaining 62 and the window year less
    one; disability origin, the onset year and onset less one; death, the
    earlier of the death year and the year of attaining 62, and the death
    year less one.
    """

    attains_62 = int(birth_year) + _ELIGIBILITY_AGE
    if basis == BASIS_OLD_AGE:
        return {"threshold_year": attains_62, "last_year": window_year - 1}
    if basis == BASIS_DISABILITY:
        if onset_year is None:
            raise ValueError("a disability-origin record needs its onset")
        return {"threshold_year": onset_year, "last_year": onset_year - 1}
    if basis == BASIS_DEATH:
        if death_year is None:
            raise ValueError("a death-basis record needs its death year")
        return {
            "threshold_year": min(death_year, attains_62),
            "last_year": death_year - 1,
        }
    raise ValueError(f"basis {basis!r}")


def _first_consistent(
    observations: Mapping[int, ReceiptObservation],
    *,
    earliest: int,
    counts: Any,
    contradicts: Any = None,
) -> tuple[int, bool]:
    """Rule 2's earliest consistent year for a receipt event.

    ``counts(obs)`` says whether an observation shows the event and
    ``contradicts(obs)`` whether it shows its absence (by default, every
    observation that does not show it).  Returns ``(year, observed)``: the
    later of ``earliest`` and the year after the last observed year that
    shows the event absent before its first observed year at or after
    ``earliest``; without an observed event, ``earliest`` and False.  An
    observation that shows neither (a receipt year whose type is unknown,
    for a survivor's benefit) does not bound the year.
    """

    if contradicts is None:

        def contradicts(obs: ReceiptObservation) -> bool:
            return not counts(obs)

    years = sorted(y for y in observations if y >= earliest)
    hits = [y for y in years if counts(observations[y])]
    if not hits:
        return earliest, False
    first = hits[0]
    without = [y for y in years if y < first and contradicts(observations[y])]
    if without:
        return max(earliest, max(without) + 1), True
    return earliest, True


def survivor_claim_year(
    observations: Mapping[int, ReceiptObservation],
    *,
    birth_year: int,
    death_year: int,
) -> tuple[int, str]:
    """A survivor's first entitlement year on the deceased's record.

    The earliest year consistent with the survivor's receipt of a
    survivor type, no earlier than the death year and the year of
    attaining 60; when no survivor type is ever mentioned from the death
    year on, the same over any receipt.  Only an observation that shows no
    survivor's benefit (no receipt, or a survivor item known and not
    mentioned) bounds the year: a receipt year whose survivor item is
    unknown (a combination code, an unknown code, a DK or NA flag, a
    whether-only "yes") is consistent with a survivor's benefit.  (The
    independent review of 2026-09-25: the build had let such a year push
    the claim year later.)  Returns the year and which receipt decided it
    (``survivor_mention``, ``any_receipt`` or ``earliest_allowed``).
    """

    earliest = max(int(death_year), int(birth_year) + _SURVIVOR_EARLIEST_AGE)
    year, seen = _first_consistent(
        observations,
        earliest=earliest,
        counts=lambda obs: obs.mentions_survivor,
        contradicts=lambda obs: obs.shows_no_survivor_receipt,
    )
    if seen:
        return min(year, INCOME_YEAR), "survivor_mention"
    year, seen = _first_consistent(
        observations, earliest=earliest, counts=lambda obs: obs.receipt
    )
    return (
        min(year, INCOME_YEAR),
        "any_receipt" if seen else "earliest_allowed",
    )


def spouse_claim_year(
    *,
    birth_year: int,
    own_entitlement_year: int | None,
    auxiliary_entitlement_year: int | None,
    worker_entitlement_year: int,
) -> int:
    """A spouse's claim year for the months-early count (module docstring).

    The later of the person's own entitlement year (or, without an own
    record, their auxiliary entitlement year), the worker's entitlement
    year and the year of attaining 62, capped at 2022.
    """

    candidates = [int(worker_entitlement_year), int(birth_year) + 62]
    for value in (own_entitlement_year, auxiliary_entitlement_year):
        if value is not None:
            candidates.append(int(value))
            break
    return min(max(candidates), INCOME_YEAR)


# ---------------------------------------------------------------------------
# Receipt histories from the M3 frames
# ---------------------------------------------------------------------------
def _types_of(row: Any) -> dict[str, Any]:
    return {name: getattr(row, f"type_{name}") for name in ssr.SS_TYPES}


def receipt_histories(
    individual: pd.DataFrame,
    family_1993: pd.DataFrame,
    family_level: pd.DataFrame,
    person_ids: Iterable[int] | None = None,
) -> dict[int, dict[int, ReceiptObservation]]:
    """``{person: {year: observation}}`` from M3's frames.

    ``individual`` (:func:`ssr.read_individual_receipt`) and
    ``family_1993`` (:func:`ssr.read_family_1993_receipt`) are
    person-level; ``family_level`` is the concatenation of
    :func:`ssr.family_level_person_rows`.  A person-level observation of a
    year wins over a family-level one.  ``person_ids`` restricts the
    result.
    """

    wanted = None if person_ids is None else {int(p) for p in person_ids}
    out: dict[int, dict[int, ReceiptObservation]] = {}

    def keep(pid: int) -> bool:
        return wanted is None or pid in wanted

    for frame, source in (
        (individual, "individual"),
        (family_1993, "family_1993"),
    ):
        if frame is None or frame.empty:
            continue
        for row in frame.itertuples(index=False):
            pid = int(row.person_id)
            if not keep(pid):
                continue
            obs = observation(
                int(row.income_year),
                receipt=int(row.amount) > 0,
                types=_types_of(row),
                combination=bool(row.type_combination),
                source=source,
            )
            person = out.setdefault(pid, {})
            if obs.year in person:
                raise ValueError(
                    f"person {pid}: two person-level observations of "
                    f"{obs.year}"
                )
            person[obs.year] = obs
    if family_level is not None and not family_level.empty:
        for row in family_level.itertuples(index=False):
            pid = int(row.person_id)
            if not keep(pid):
                continue
            person = out.setdefault(pid, {})
            year = int(row.income_year)
            if year in person:
                continue
            person[year] = observation(
                year,
                receipt=bool(row.receipt),
                types=_types_of(row),
                source=str(row.source),
            )
    return out


# ---------------------------------------------------------------------------
# Inputs from the staged PSID
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class TrackMCohortInputs:
    """Every frame the cohort reads, with the PSID files' SHA-256."""

    structure_inputs: structure.TrackMStructureInputs
    individual_receipt: pd.DataFrame
    family_1993_receipt: pd.DataFrame
    family_level_receipt: pd.DataFrame
    prior_year_labor: pd.DataFrame
    provenance: Mapping[str, Any] = field(default_factory=dict)

    @property
    def anchor(self) -> pd.DataFrame:
        return self.structure_inputs.anchor

    @property
    def earnings(self) -> pd.DataFrame:
        return self.structure_inputs.observed_earnings


def _member_waves() -> tuple[int, ...]:
    waves = {
        *ssr.INDIVIDUAL_WAVES,
        1993,
        *ssr.FAMILY_TOTAL_WAVES,
        *ssr.YEAR_BEFORE_LAST_WAVES,
        *(year + 2 for year in pyl.ODD_INCOME_YEARS),
    }
    return tuple(sorted(waves))


def load_cohort_inputs(*, data_dir: Path | None = None) -> TrackMCohortInputs:
    """Read every input from the staged PSID, recording file hashes.

    The structural inputs (:func:`structure.load_structure_inputs`: the
    2023 anchor, family-file Social Security, deaths, marriage history,
    earnings panel, design) and M3's receipt and next-wave labor-income
    frames.  Nothing is computed beyond decoding.
    """

    root = psid._resolve_data_dir(data_dir)
    base = structure.load_structure_inputs(data_dir=data_dir)
    with psid2010.record_files_read(root) as files:
        members = ssr.read_wave_members(_member_waves(), data_dir=data_dir)
        individual = ssr.read_individual_receipt(
            data_dir=data_dir, members=members
        )
        family_1993 = ssr.read_family_1993_receipt(
            data_dir=data_dir, members=members
        )
        rows = []
        for wave in ssr.YEAR_BEFORE_LAST_WAVES:
            rows.append(
                ssr.family_level_person_rows(
                    ssr.read_year_before_last(wave, data_dir=data_dir),
                    members,
                    kind="year_before_last",
                )
            )
        for wave in ssr.FAMILY_TOTAL_WAVES:
            rows.append(
                ssr.family_level_person_rows(
                    ssr.read_family_totals(wave, data_dir=data_dir),
                    members,
                    kind="total",
                )
            )
        family_level = pd.concat(rows, ignore_index=True)
        prior = pyl.read_prior_year_labor_income(
            data_dir=data_dir, members=members
        )
    files_read = {
        **dict(base.provenance.get("psid_files_sha256", {})),
        **files,
    }
    return TrackMCohortInputs(
        structure_inputs=base,
        individual_receipt=individual,
        family_1993_receipt=family_1993,
        family_level_receipt=family_level,
        prior_year_labor=prior,
        provenance={
            "psid_data_dir": str(root),
            "psid_files_sha256": dict(sorted(files_read.items())),
        },
    )


# ---------------------------------------------------------------------------
# The cohort
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class TrackMCohort:
    """The universe with its worker records and links (plan item M4).

    ``persons``: one row per person of the universe (``person_id``,
    ``family_unit_id``, ``weight``, ``sex``, ``stratum``, ``cluster``,
    ``birth_year``, ``role``, ``other_member``, ``own_record_id``,
    ``paid_own_worker_benefit``, ``ms5_in_scope``, ``amount_2022``,
    ``types_2022``, ``unlinked_auxiliary``, ``unlinked_kind``).
    ``records``: one row per worker record (``record_id``, ``person_id``,
    ``birth_year``, ``basis``, ``window_year``, ``onset_year``,
    ``death_year``, ``unresolved``, ``resolution``, ``first_own_year``,
    ``in_universe``, ``threshold_year``, ``last_year``,
    ``death_after_62``).  ``links``: one row per link (``person_id``,
    ``kind``, ``record_id``, ``claim_year``, ``claim_source``).
    ``design``: the 2023 design frame.  ``diagnostics``: counts that
    arise while building.
    """

    persons: pd.DataFrame
    records: pd.DataFrame
    links: pd.DataFrame
    design: pd.DataFrame
    histories: Mapping[int, Mapping[int, ReceiptObservation]]
    diagnostics: Mapping[str, Any]
    provenance: Mapping[str, Any] = field(default_factory=dict)


def record_id(person_id: int) -> str:
    return f"W{int(person_id)}"


def _universe(inputs: TrackMCohortInputs) -> pd.DataFrame:
    """Section 10's universe, as :func:`structure.structural_counts` reads
    it (the counts equal its funnel; a test holds them equal)."""

    anchor = inputs.anchor
    base = anchor[
        anchor["sequence"].between(1, 20) & (anchor["weight"] > 0)
    ].copy()
    young = base["age"].between(0, 2022 - career.DERIVED_BIRTH_MAX - 1)
    base = base[~young].copy()
    seed = pd.DataFrame(
        {
            "person_id": base["person_id"].astype("int64"),
            "year": INCOME_YEAR,
            "anchor_wave": WAVE,
            "age": base["age"].astype("int64"),
        }
    )
    ids = set(int(pid) for pid in base["person_id"])
    history = inputs.structure_inputs.marriage_history
    earnings = inputs.earnings
    records = career.derive_birth_years(
        history[history["person_id"].isin(ids)],
        earnings[earnings["person_id"].isin(ids)],
        seed_coordinates=seed,
        required_person_ids=ids,
    )
    births = {record.person_id: record.birth_year for record in records}
    base["birth_year"] = base["person_id"].map(lambda p: births[int(p)])
    base = base[base["birth_year"].notna()].copy()
    base["birth_year"] = base["birth_year"].astype("int64")
    base = base[base["birth_year"] <= structure.LAST_BIRTH_YEAR]
    return base[base["ss_amount"] > 0].reset_index(drop=True)


def _linked_birth_years(
    inputs: TrackMCohortInputs, person_ids: set[int]
) -> dict[int, int]:
    history = inputs.structure_inputs.marriage_history
    earnings = inputs.earnings
    records = career.derive_birth_years(
        history[history["person_id"].isin(person_ids)],
        earnings[earnings["person_id"].isin(person_ids)],
        required_person_ids=(),
    )
    return {
        record.person_id: int(record.birth_year)
        for record in records
        if record.birth_year is not None
    }


_ANCHOR_FLAGS = {
    name: f"type_{name}"
    for name in (
        "disability",
        "retirement",
        "survivor",
        "dependent_of_disabled",
        "dependent_of_retired",
        "other",
    )
}


def _anchor_types(row: Any) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, column in _ANCHOR_FLAGS.items():
        code = int(getattr(row, column))
        out[name] = True if code == 1 else False if code == 5 else None
    return out


def _marital_states(
    history: pd.DataFrame, person_ids: set[int]
) -> dict[int, dict[str, Any]]:
    rows = history[history["person_id"].isin(person_ids)]
    # The PSID 2010 cohort's episodes, with the marriage history's
    # separation year alongside (``marital_state_at`` reads it).
    episodes = psid2010._episodes_with_separation(rows)
    by_person = {
        int(pid): group for pid, group in episodes.groupby("person_id")
    }
    with_history = set(int(pid) for pid in rows["person_id"])
    empty = episodes.iloc[0:0]
    out = {}
    for pid in person_ids:
        if pid in with_history:
            out[pid] = psid2010.marital_state_at(
                by_person.get(pid, empty), INCOME_YEAR
            )
        else:
            out[pid] = {"status": "no_marriage_history"}
    return out


def _death_year(death: Mapping[str, Any]) -> tuple[int | None, str]:
    """``(year used, status)`` for a linked late spouse: the exact year,
    or a range's last year; ``None`` when no year is known."""

    status = str(death.get("death_status"))
    if status == "exact":
        return int(death["death_year"]), status
    if status == "range" and not pd.isna(death.get("death_year_hi")):
        return int(death["death_year_hi"]), status
    return None, status


def unlinked_kind(mentions: frozenset[str], kinds: set[str]) -> str | None:
    """Section 9's unlinked auxiliary: a 2022 survivor mention without a
    survivor's link, or a dependent mention without a spouse's link."""

    if "survivor" in mentions and "survivor" not in kinds:
        return "survivor"
    if mentions & {"dependent_of_disabled", "dependent_of_retired"} and (
        "spouse" not in kinds
    ):
        return "dependent"
    return None


def _oracle_domain(
    links: pd.DataFrame,
    classes: Mapping[int, OwnRecordClass],
    births: Mapping[int, int],
    diagnostics: Counter[str],
) -> pd.DataFrame:
    """Drop links to records the oracle cannot compute, when harmless.

    ``ss.statutory_aime`` refuses a worker who attains 62 before 1975
    (born before 1913; :data:`FIRST_AGE_62_YEAR_ENCODED`).  A linked
    record of such a worker whose window year precedes 2004, the earliest
    policy year of any registered row, can rest on no minimum under any
    row, so its link is dropped and counted; one inside a window is
    refused, because no row could compute its PIA.
    """

    keep = []
    for row in links.itertuples(index=False):
        worker = int(row.worker_person_id)
        birth = births[worker]
        if birth + _ELIGIBILITY_AGE >= FIRST_AGE_62_YEAR_ENCODED:
            keep.append(True)
            continue
        cls = classes.get(worker)
        window = cls.window_year if cls is not None else int(row.claim_year)
        if window >= POLICY_YEARS[0]:
            raise ValueError(
                f"linked worker {worker}, born {birth}, attains 62 before "
                f"{FIRST_AGE_62_YEAR_ENCODED} (outside the oracle) with a "
                f"window year {window} inside a policy window"
            )
        diagnostics[f"{row.kind}_link_dropped_worker_born_before_1913"] += 1
        keep.append(False)
    return links[keep].reset_index(drop=True)


def build_cohort(inputs: TrackMCohortInputs) -> TrackMCohort:
    """The universe, its worker records and links (module docstring)."""

    universe = _universe(inputs)
    universe_ids = set(int(pid) for pid in universe["person_id"])
    deaths = inputs.structure_inputs.death_records.set_index("person_id")
    design_frame = inputs.structure_inputs.design.set_index("person_id")
    anchor = inputs.anchor.set_index("person_id")
    diagnostics: Counter[str] = Counter()

    states = _marital_states(
        inputs.structure_inputs.marriage_history, universe_ids
    )
    spouse_ids: set[int] = set()
    late_ids: set[int] = set()
    for state in states.values():
        if state["status"] == "married" and not pd.isna(
            state.get("spouse_person_id")
        ):
            spouse_ids.add(int(state["spouse_person_id"]))
        if state["status"] == "widowed" and not pd.isna(
            state.get("former_spouse_person_id")
        ):
            late_ids.add(int(state["former_spouse_person_id"]))
    everyone = universe_ids | spouse_ids | late_ids
    histories = receipt_histories(
        inputs.individual_receipt,
        inputs.family_1993_receipt,
        inputs.family_level_receipt,
        person_ids=everyone,
    )
    births = {
        int(p): int(b)
        for p, b in zip(
            universe["person_id"], universe["birth_year"], strict=True
        )
    }
    births.update(
        {
            pid: year
            for pid, year in _linked_birth_years(
                inputs, (spouse_ids | late_ids) - universe_ids
            ).items()
            if pid not in births
        }
    )

    # -- worker records of persons with own receipt ------------------------
    classes: dict[int, OwnRecordClass] = {}
    for pid in sorted(everyone):
        if pid not in births:
            continue
        found = classify_own_record(histories.get(pid, {}), births[pid])
        if found is not None:
            classes[pid] = found

    # -- persons, links ------------------------------------------------------
    person_rows = []
    link_rows = []
    death_records: dict[int, dict[str, Any]] = {}
    for row in universe.itertuples(index=False):
        pid = int(row.person_id)
        birth = births[pid]
        types_2022 = _anchor_types(row)
        obs_2022 = observation(
            INCOME_YEAR, receipt=True, types=types_2022, source="individual"
        )
        own_class = classes.get(pid)
        paid_own = obs_2022.status == OWN and own_class is not None
        mentions = obs_2022.types
        known = all(value is not None for value in types_2022.values())
        ms5 = (
            paid_own
            and known
            and bool(mentions)
            and mentions <= frozenset(ssr.WORKER_TYPES)
        )
        relationship = int(row.relationship)
        role = {10: "reference_person", 20: "spouse", 22: "partner"}.get(
            relationship, "other_member"
        )
        state = states[pid]
        links_here = []
        # spouse's link
        if state["status"] == "married" and not pd.isna(
            state.get("spouse_person_id")
        ):
            spouse = int(state["spouse_person_id"])
            spouse_class = classes.get(spouse)
            spouse_2022 = histories.get(spouse, {}).get(INCOME_YEAR)
            alive = (
                spouse not in deaths.index
                or str(deaths.loc[spouse, "death_status"]) == "not_deceased"
            )
            reason = (
                "spouse_without_own_record"
                if spouse_class is None
                else (
                    "spouse_deceased"
                    if not alive
                    else (
                        "spouse_2022_unobserved"
                        if spouse_2022 is None
                        else (
                            None
                            if spouse_2022.status == OWN
                            else "spouse_2022_not_own_receipt"
                        )
                    )
                )
            )
            if reason is None:
                aux_year = None
                if own_class is None:
                    aux_year, _ = _first_consistent(
                        histories.get(pid, {}),
                        earliest=birth + 62,
                        counts=lambda obs: obs.receipt,
                    )
                claim = spouse_claim_year(
                    birth_year=birth,
                    own_entitlement_year=(
                        own_class.window_year if own_class else None
                    ),
                    auxiliary_entitlement_year=aux_year,
                    worker_entitlement_year=spouse_class.window_year,
                )
                links_here.append(
                    {
                        "person_id": pid,
                        "kind": "spouse",
                        "record_id": record_id(spouse),
                        "worker_person_id": spouse,
                        "claim_year": claim,
                        "claim_source": "spouse_claim_year",
                    }
                )
            else:
                diagnostics["married_no_spouse_link"] += 1
                diagnostics[f"married_no_spouse_link_{reason}"] += 1
        # survivor's link
        if state["status"] == "widowed" and not pd.isna(
            state.get("former_spouse_person_id")
        ):
            late = int(state["former_spouse_person_id"])
            death = deaths.loc[late].to_dict() if late in deaths.index else {}
            year, death_status = _death_year(death)
            if late in universe_ids:
                diagnostics["widowed_late_spouse_in_universe"] += 1
            elif year is None or year > INCOME_YEAR:
                diagnostics[f"widowed_late_spouse_death_{death_status}"] += 1
            elif late not in classes and death_status != "exact":
                diagnostics["widowed_death_basis_without_exact_year"] += 1
            elif late not in births:
                diagnostics["widowed_late_spouse_birth_unresolved"] += 1
            else:
                claim, source = survivor_claim_year(
                    histories.get(pid, {}), birth_year=birth, death_year=year
                )
                death_records[late] = {
                    "death_year": year,
                    "death_status": death_status,
                }
                links_here.append(
                    {
                        "person_id": pid,
                        "kind": "survivor",
                        "record_id": record_id(late),
                        "worker_person_id": late,
                        "claim_year": claim,
                        "claim_source": source,
                    }
                )
        link_rows.extend(links_here)
        sex = str(deaths.loc[pid, "sex"]) if pid in deaths.index else "na"
        stratum = design_frame.loc[pid, "stratum"]
        cluster = design_frame.loc[pid, "cluster"]
        person_rows.append(
            {
                "person_id": pid,
                "family_unit_id": int(anchor.loc[pid, "interview"]),
                "weight": float(row.weight),
                "sex": {"male": "male", "female": "female"}.get(
                    sex, "unknown"
                ),
                "stratum": int(stratum),
                "cluster": int(cluster),
                "birth_year": birth,
                "role": role,
                "other_member": role == "other_member",
                "own_record_id": record_id(pid) if own_class else None,
                "paid_own_worker_benefit": bool(paid_own),
                "ms5_in_scope": bool(ms5),
                "amount_2022": int(row.ss_amount),
                "types_2022": ",".join(sorted(mentions)),
                "status_2022": obs_2022.status,
                "marital_status_2022": state["status"],
            }
        )
    persons = pd.DataFrame(person_rows)
    links = pd.DataFrame(
        link_rows,
        columns=[
            "person_id",
            "kind",
            "record_id",
            "worker_person_id",
            "claim_year",
            "claim_source",
        ],
    )

    links = _oracle_domain(links, classes, births, diagnostics)
    kinds = links.groupby("person_id")["kind"].agg(set).to_dict()
    unlinked = [
        unlinked_kind(
            frozenset(t for t in str(types).split(",") if t),
            kinds.get(int(pid), set()),
        )
        for pid, types in zip(
            persons["person_id"], persons["types_2022"], strict=True
        )
    ]
    persons["unlinked_auxiliary"] = [kind is not None for kind in unlinked]
    persons["unlinked_kind"] = unlinked
    # -- the records the persons need -----------------------------------------
    needed = set()
    for value in persons["own_record_id"].dropna():
        needed.add(int(str(value)[1:]))
    for value in links["worker_person_id"]:
        needed.add(int(value))
    record_rows = []
    for pid in sorted(needed):
        birth = births[pid]
        cls = classes.get(pid)
        death = death_records.get(pid)
        if cls is not None:
            years = record_years(
                cls.basis, birth, cls.window_year, onset_year=cls.onset_year
            )
            record_rows.append(
                {
                    "record_id": record_id(pid),
                    "person_id": pid,
                    "birth_year": birth,
                    "basis": cls.basis,
                    "window_year": cls.window_year,
                    "onset_year": cls.onset_year,
                    "death_year": None,
                    "unresolved": cls.unresolved,
                    "resolution": cls.resolution,
                    "first_own_year": cls.first_own_year,
                    "last_without_year": cls.last_without_year,
                    "last_without_source": cls.last_without_source,
                    "retirement_type": cls.retirement_type,
                    "rule3_in_2004": cls.rule3_in_window.get(2004),
                    "rule3_in_2007": cls.rule3_in_window.get(2007),
                    "in_universe": pid in universe_ids,
                    "deceased": death is not None,
                    "death_after_62": False,
                    **years,
                }
            )
        else:
            if death is None:
                raise AssertionError(f"record {pid} is neither own nor dead")
            survivors = links[
                (links["worker_person_id"] == pid)
                & (links["kind"] == "survivor")
            ]
            window = int(survivors["claim_year"].min())
            death_year = int(death["death_year"])
            years = record_years(
                BASIS_DEATH, birth, window, death_year=death_year
            )
            record_rows.append(
                {
                    "record_id": record_id(pid),
                    "person_id": pid,
                    "birth_year": birth,
                    "basis": BASIS_DEATH,
                    "window_year": window,
                    "onset_year": None,
                    "death_year": death_year,
                    "unresolved": False,
                    "resolution": "died_before_any_observed_own_receipt",
                    "first_own_year": None,
                    "last_without_year": None,
                    "last_without_source": None,
                    "retirement_type": False,
                    "rule3_in_2004": None,
                    "rule3_in_2007": None,
                    "in_universe": pid in universe_ids,
                    "deceased": True,
                    "death_after_62": death_year >= birth + 62,
                    **years,
                }
            )
    records = pd.DataFrame(record_rows)
    anchor_all = inputs.anchor
    frame = anchor_all[
        anchor_all["sequence"].between(1, 20) & (anchor_all["weight"] > 0)
    ][["person_id"]]
    design = frame.merge(
        inputs.structure_inputs.design, on="person_id", how="left"
    )[["stratum", "cluster"]]
    if design.isna().any().any():
        raise ValueError("a 2023 design-frame person has no stratum/cluster")
    return TrackMCohort(
        persons=persons,
        records=records,
        links=links,
        design=design.astype("int64").reset_index(drop=True),
        histories=histories,
        diagnostics=dict(diagnostics),
        provenance=dict(inputs.provenance),
    )


# ---------------------------------------------------------------------------
# Structural counts (counts and years only)
# ---------------------------------------------------------------------------
def _counter(values: Iterable[Any]) -> dict[str, int]:
    return {str(k): int(v) for k, v in sorted(Counter(values).items())}


def _death_basis_counts(frame: pd.DataFrame) -> dict[str, int]:
    """Death-basis records by when their worker died (counts only).

    Section 4b rule 1 reads a linked late spouse with no observed own
    receipt as a worker who died before any own entitlement.  One who died
    at 62 or older, or in an income year no person-level item records
    (:data:`YEARS_WITHOUT_PERSON_LEVEL_RECEIPT`), may have been entitled
    unobserved; these counts size that reading, they do not change it.
    """

    if frame.empty:
        return {
            "records": 0,
            "died_at_or_after_62": 0,
            "died_in_a_year_without_person_level_receipt": 0,
            "died_at_or_after_62_in_such_a_year": 0,
        }
    death = frame["death_year"].astype("int64")
    late = death >= frame["birth_year"].astype("int64") + _ELIGIBILITY_AGE
    blind = death.isin(YEARS_WITHOUT_PERSON_LEVEL_RECEIPT)
    return {
        "records": int(len(frame)),
        "died_at_or_after_62": int(late.sum()),
        "died_in_a_year_without_person_level_receipt": int(blind.sum()),
        "died_at_or_after_62_in_such_a_year": int((late & blind).sum()),
    }


def boundary_year_unobserved(
    records: pd.DataFrame, policy_year: int
) -> dict[str, Any]:
    """Rule-2 records whose year before the policy year is unobserved.

    Section 4b rule 2 sets the entitlement year to the earliest year
    consistent with the observations.  For a record whose last observed
    year without own receipt (*L*) precedes the policy year less one while
    its first observed own receipt (*F*) is in the policy year or later,
    the observations allow an entitlement year on either side of the
    boundary.  Rule 3's age rule (born at the cutoff or later with a
    retirement type) is written for "receipt in 2004 and unknown status
    in 2003"; this counts both readings for these records and chooses
    neither (the build applies rule 2 as written, since rule 2 sends only
    records with receipt in their first observed year to rule 3).
    """

    gap, by_rule_2, age_rule = _boundary_readings(records, policy_year)
    return {
        "records": int(len(gap)),
        "in_universe": int(gap["in_universe"].astype(bool).sum()),
        "by_basis": _counter(gap["basis"]),
        "in_window_by_rule_2": int(by_rule_2.sum()),
        "in_window_by_rule_3_age_rule": int(age_rule.sum()),
        "readings_disagree": int((by_rule_2 != age_rule).sum()),
    }


def _boundary_readings(
    records: pd.DataFrame, policy_year: int
) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """The records :func:`boundary_year_unobserved` counts, with each
    record's membership under rule 2 and under rule 3's age rule."""

    policy_year = int(policy_year)
    own = records[records["resolution"] == "rule2_observed_boundary"]
    if own.empty:
        gap = own
    else:
        last = own["last_without_year"].astype("int64")
        first = own["first_own_year"].astype("int64")
        gap = own[(last < policy_year - 1) & (first >= policy_year)]
    by_rule_2 = (gap["window_year"] >= policy_year).astype(bool)
    age_rule = (gap["birth_year"] >= RULE3_BIRTH_YEAR[policy_year]) & gap[
        "retirement_type"
    ].astype(bool)
    return gap, by_rule_2, age_rule


def _counts_outside_the_windows(cohort: TrackMCohort) -> dict[str, Any]:
    """The counts of :func:`cohort_structure` that involve no policy
    window, no exposed person, no unlinked auxiliary and no MS5 scope:
    persons, records and links by class, the records outside the oracle,
    the old-age entitlement ages of all records and the first-receipt
    bands.  :func:`structural_counts_before_registration` computes these
    and nothing the M1 specification's section 11 reserves."""

    persons, records, links = cohort.persons, cohort.records, cohort.links
    claim_ages = [
        int(row.window_year) - int(row.birth_year)
        for row in records.itertuples(index=False)
        if row.basis == BASIS_OLD_AGE
    ]
    return {
        "persons": int(len(persons)),
        "persons_by_status_2022": _counter(persons["status_2022"]),
        "persons_with_own_record": int(persons["own_record_id"].notna().sum()),
        "persons_paid_own_worker_benefit": int(
            persons["paid_own_worker_benefit"].sum()
        ),
        "persons_by_marital_status_2022": _counter(
            persons["marital_status_2022"]
        ),
        "persons_by_role": _counter(persons["role"]),
        "persons_by_sex": _counter(persons["sex"]),
        "amount_2022_top_coded": int(
            (persons["amount_2022"] >= ssr.AMOUNT_TOP_CODE).sum()
        ),
        "links_by_kind": _counter(links["kind"]),
        "links_by_claim_source": _counter(
            links["kind"] + ":" + links["claim_source"]
        ),
        "persons_with_links": int(links["person_id"].nunique()),
        "records": int(len(records)),
        "records_by_basis": _counter(records["basis"]),
        "records_by_resolution": _counter(records["resolution"]),
        "records_outside_universe": int((~records["in_universe"]).sum()),
        "records_of_deceased_workers_by_basis": _counter(
            records.loc[records["deceased"], "basis"]
        ),
        "death_basis_records_died_at_or_after_62": int(
            records["death_after_62"].sum()
        ),
        "records_outside_the_oracle": int(
            (
                records["birth_year"] + _ELIGIBILITY_AGE
                < FIRST_AGE_62_YEAR_ENCODED
            ).sum()
        ),
        "old_age_entitlement_age": _counter(claim_ages),
        "first_own_year_band": _counter(
            (
                "1983_1992_person_level"
                if y <= 1992
                else (
                    "1993_2003_family_level_only" if y <= 2003 else "2004_2022"
                )
            )
            for y in records["first_own_year"].dropna().astype(int)
        ),
        "build_diagnostics": dict(cohort.diagnostics),
    }


def _unresolved_counts(records: pd.DataFrame) -> dict[str, Any]:
    """Rule-3 records in total, by first receipt and by basis (no window)."""

    unresolved = records[records["unresolved"]]
    return {
        "records": int(len(unresolved)),
        "first_own_year_2004": int(
            (unresolved["first_own_year"] == 2004).sum()
        ),
        "first_own_year_after_2004": int(
            (unresolved["first_own_year"] > 2004).sum()
        ),
        "by_basis": _counter(unresolved["basis"]),
    }


def cohort_structure(cohort: TrackMCohort) -> dict[str, Any]:
    """Counts of the cohort's classes, links and needed threshold years.

    Persons, records and links by class; unresolved records by rule 3's
    case at each policy year; in-window records by basis at 2004 and
    2007 (in or after, and after); the threshold *years* in-window
    records need (section 4a; years, never thresholds) with the earliest;
    and the claim-year sources.  No benefit, years of coverage, PIA,
    threshold or minimum enters.  Its window, exposure, unlinked-auxiliary
    and MS5 counts are section 11's registered-run diagnostics: on real
    data only the registered run computes them
    (:func:`structural_counts_before_registration` does not call this).
    """

    persons, records = cohort.persons, cohort.records
    out: dict[str, Any] = _counts_outside_the_windows(cohort)
    out["persons_ms5_in_scope"] = int(persons["ms5_in_scope"].sum())
    out["unlinked_auxiliaries"] = _counter(
        persons.loc[persons["unlinked_auxiliary"], "unlinked_kind"]
    )
    ms5 = persons[persons["ms5_in_scope"]]
    own_windows = records.set_index("record_id")["window_year"]
    ms5_ids = ms5["own_record_id"].astype(str)
    out["ms5_in_scope_entitled_in_2022"] = int(
        (ms5_ids.map(own_windows) == INCOME_YEAR).sum()
    )
    by_policy: dict[str, Any] = {}
    for year in POLICY_YEARS:
        for strictly in (False, True):
            key = f"{year}_{'after' if strictly else 'in_or_after'}"
            window = (
                records["window_year"] > year
                if strictly
                else records["window_year"] >= year
            )
            inside = records[window]
            needed = _counter(inside["threshold_year"])
            by_policy[key] = {
                "in_window_records": int(len(inside)),
                "in_window_by_basis": _counter(inside["basis"]),
                "in_window_unresolved": int(inside["unresolved"].sum()),
                "threshold_years_needed": needed,
                "earliest_threshold_year": (
                    int(inside["threshold_year"].min())
                    if len(inside)
                    else None
                ),
                "threshold_years_before_2003": {
                    k: v for k, v in needed.items() if int(k) < 2003
                },
                "threshold_years_before_2003_by_basis": {
                    basis: _counter(group["threshold_year"])
                    for basis, group in inside[
                        inside["threshold_year"] < 2003
                    ].groupby("basis")
                },
                "death_basis": _death_basis_counts(
                    inside[inside["basis"] == BASIS_DEATH]
                ),
                "by_resolution": _counter(inside["resolution"]),
                "rule2_by_boundary_source": _counter(
                    inside.loc[
                        inside["resolution"] == "rule2_observed_boundary",
                        "last_without_source",
                    ]
                ),
                "old_age_entitlement_age": _counter(
                    (
                        inside.loc[
                            inside["basis"] == BASIS_OLD_AGE, "window_year"
                        ]
                        - inside.loc[
                            inside["basis"] == BASIS_OLD_AGE, "birth_year"
                        ]
                    ).astype(int)
                ),
                "outside_the_oracle": int(
                    (
                        inside["birth_year"] + _ELIGIBILITY_AGE
                        < FIRST_AGE_62_YEAR_ENCODED
                    ).sum()
                ),
            }
    out["by_policy_year"] = by_policy
    out["boundary_year_unobserved"] = {
        str(year): boundary_year_unobserved(records, year)
        for year in POLICY_YEARS
    }
    unresolved = records[records["unresolved"]]
    out["unresolved_rule3"] = {
        **_unresolved_counts(records),
        "in_2004": int(unresolved["rule3_in_2004"].fillna(False).sum()),
        "in_2007": int(unresolved["rule3_in_2007"].fillna(False).sum()),
    }
    return out


#: The policy-year windows of the registered rows: MS0 and MS2-MS6 at
#: 2004 in or after, MS4 at 2004 after, MS1 at 2007 in or after.
_ROW_WINDOWS: tuple[tuple[str, int, bool], ...] = (
    ("2004_in_or_after", 2004, False),
    ("2004_after", 2004, True),
    ("2007_in_or_after", 2007, False),
)


def structural_counts_before_registration(
    cohort: TrackMCohort,
) -> dict[str, Any]:
    """The M4 counts real-file work may compute before the registration.

    The M1 specification asks M4 for "structural counts of records by
    basis, unresolved counts and the earliest threshold year needed"
    (section 18, item 3; section 7: "a year, not a threshold") and
    reserves for the registered run the diagnostics of section 11, among
    them the worker records by basis in the window, the unresolved
    in-window records, the exposed persons, the unlinked auxiliaries and
    the PIA source of each record ("None may be computed on real data
    before the registration").  So this computes, and returns, only:
    persons, records and links by class; unresolved records in total and
    by basis; for each registered window, the earliest threshold year its
    records need, the years before 2003 they need (those the first
    capture, of 2003-2022, lacked; section 7) and the section 4a bases
    that need them, as years and names without counts;
    and, for the rule-2 records whose year before a policy year is
    unobserved, how many there are and on how many rule 2 and rule 3's
    age rule disagree.  It never calls :func:`cohort_structure` (the
    independent review of 2026-09-25: it had computed the reserved counts
    in memory and dropped them).  No benefit, years of coverage, PIA,
    threshold, minimum or flag enters.
    """

    records = cohort.records
    out: dict[str, Any] = _counts_outside_the_windows(cohort)
    out["unresolved_rule3"] = _unresolved_counts(records)
    years: dict[str, Any] = {}
    union: set[int] = set()
    bases: set[str] = set()
    for key, year, strictly in _ROW_WINDOWS:
        window = (
            records["window_year"] > year
            if strictly
            else records["window_year"] >= year
        )
        # the years and bases of the window's records, never their number
        needed = sorted(
            {int(y) for y in records.loc[window, "threshold_year"]}
        )
        early = window & (records["threshold_year"] < 2003)
        early_bases = sorted(set(records.loc[early, "basis"]))
        union |= set(needed)
        years[key] = {
            "earliest_threshold_year": needed[0] if needed else None,
            "threshold_years_before_2003": [y for y in needed if y < 2003],
            # which section 4a rows need them: names, never counts
            "bases_needing_years_before_2003": early_bases,
        }
        bases |= set(early_bases)
    years["any_registered_row"] = {
        "earliest_threshold_year": min(union) if union else None,
        "threshold_years_before_2003": sorted(y for y in union if y < 2003),
        "bases_needing_years_before_2003": sorted(bases),
    }
    out["threshold_years_needed"] = years
    boundary: dict[str, Any] = {}
    for year in POLICY_YEARS:
        gap, by_rule_2, age_rule = _boundary_readings(records, year)
        boundary[str(year)] = {
            "records": int(len(gap)),
            "readings_disagree": int((by_rule_2 != age_rule).sum()),
        }
    out["boundary_year_unobserved"] = boundary
    out["withheld_until_registration"] = [
        "in-window records by basis, resolution and entitlement age",
        "threshold years needed, with counts",
        "unresolved in-window records (rule 3 at 2004 and 2007)",
        "records in each window by the rule-2 and rule-3 readings",
        "unlinked auxiliaries",
        "persons in MS5's scope",
    ]
    return out


def history_source_counts(
    cohort: TrackMCohort,
    earnings: pd.DataFrame,
    prior_year: pd.DataFrame,
) -> dict[str, Any]:
    """Where each record's history years come from (counts of years).

    For every worker record, over the years from the year of attaining 22
    through section 4a's last year: years the earnings panel observes,
    odd years the next wave's items observe (M3), odd years 1997-2021 the
    neighbor law could fill (a neighbor observed), and years unobserved.
    Observation only: no amount is compared with anything, and no count
    is split by window membership (a registered-run diagnostic, section
    11 of the M1 specification).
    """

    observed_by = {
        int(pid): set(int(p) for p in group["period"])
        for pid, group in earnings.groupby("person_id")
    }
    next_wave = pyl.next_wave_histories(prior_year)
    totals: Counter[str] = Counter()
    by_basis: dict[str, Counter[str]] = {}
    for row in cohort.records.itertuples(index=False):
        pid = int(row.person_id)
        last = int(row.last_year)
        start = int(row.birth_year) + 22
        panel = {y for y in observed_by.get(pid, set()) if y <= last}
        odd = {y for y in next_wave.get(pid, {}) if y <= last}
        years = range(start, last + 1)
        counts: Counter[str] = Counter()
        for year in years:
            if year in panel:
                counts["panel"] += 1
            elif year in odd:
                counts["next_wave"] += 1
            elif (
                1997 <= year <= 2021
                and year % 2 == 1
                and (
                    (year - 1) in panel
                    or ((year + 1) <= last and (year + 1) in panel)
                )
            ):
                counts["neighbor_fillable"] += 1
            elif year < 1968:
                counts["before_1968"] += 1
            else:
                counts["unobserved"] += 1
        counts["panel_before_22"] = sum(1 for y in panel if y < start)
        totals.update(counts)
        by_basis.setdefault(str(row.basis), Counter()).update(counts)
    return {
        "window": "from the year of attaining 22 through section 4a's last year",
        "person_years": dict(totals),
        "person_years_by_basis": {k: dict(v) for k, v in by_basis.items()},
        "next_wave_items_by_status": _counter(prior_year["status"]),
        "next_wave_items_by_time_unit": _counter(prior_year["per"]),
    }
