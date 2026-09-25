"""Track M realized careers and records (plan item M5).

Python rules (not Axiom).  :mod:`.cohort` (M4) classifies each worker
record and links each person of the universe; this module turns them into
the records :mod:`.evaluation` reads (:class:`~.evaluation.TrackMInputs`):

* **One history per worker** (M1 specification sections 4a and 5; referee
  R7).  ``WorkerRecord.observed`` is the earnings panel's labor income by
  year (``data/family.py``: every year 1968-1996 and even years from
  1998, head and spouse only), treated as covered earnings (d280);
  ``WorkerRecord.next_wave`` is the next wave's year-before-last labor
  income of the reference person and spouse for the odd years 2001-2021
  (:mod:`populace_dynamics.data.prior_year_labor_income`, observed items
  only).  :func:`.coverage.one_history` then applies the gap rule, and
  *Y* and *P* read that one history through section 4a's last year
  (:func:`.evaluation.evaluate_worker_record`, through the oracle).
* **Claim factors and months early** (section 4b rule 5).  A worker's own
  claim factor is ``rules.claim_factor`` at the whole-year claim age of
  its entitlement year (1 for a disability-origin record, whose benefit
  is not reduced, and for a worker who died before any own entitlement).
  A spouse's months early are counted against their own full retirement
  age (``params.fra_months``) at the claim year M4 gives.  A survivor's
  months early are counted against the oracle's survivor reduction span
  (``params.survivor_earliest_claim_age`` plus
  ``params.survivor_reduction_period_months``: age 67 at the default, the
  oracle's documented survivor simplification), capped at the span.
* **MS5's inputs** (section 6; referee R9).  For a person paid their own
  worker benefit alone in 2022 (2022 type mentions retirement or
  disability only, every type item known), *B* is ER35219 over 12 (an
  annual total received during 2022, taken as gross; M3,
  ``social_security_receipt.AMOUNT_2023_READING``), the claim factor is
  the record's own and the COLA factor is ``rules.cola_factor`` from the
  threshold year of section 4a through the COLA determined in 2021.  The
  committed COLA history starts in 1979: a record whose threshold year
  precedes it keeps the MS0 PIA when it lies outside every registered
  row's window (no option can flag it, so its MS5 PIA sets nothing;
  counted in ``source["careers_diagnostics"]``) and is refused when it
  lies inside one.

**Refusals before anything is computed**: a record whose worker attains
62 before 1975, which the oracle cannot compute
(:func:`check_oracle_domain`); a cohort read from staged PSID files but
marked anything other than ``psid_files``; and records marked invented
from a cohort whose provenance lacks the invented generator's label.

It reads no file itself: :func:`build_track_m_inputs` takes M4's cohort,
the earnings panel, M3's next-wave frame, the oracle's parameters and the
COLA history.  Records built from staged PSID files carry the provenance
``psid_files`` and the files' SHA-256 under ``source["psid_files_sha256"]``;
the pipeline evaluates them only in the registered run and only against
the committed specification, and the tabulation refuses them without the
issue #42 registration pointer and an authorizing specification.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

import pandas as pd

from populace_dynamics.data import prior_year_labor_income as pyl
from populace_dynamics.min_benefit_track_m import DRY_RUN_HEADER, rules
from populace_dynamics.min_benefit_track_m.cohort import (
    BASIS_OLD_AGE,
    FIRST_AGE_62_YEAR_ENCODED,
    POLICY_YEARS,
    TrackMCohort,
)
from populace_dynamics.min_benefit_track_m.evaluation import (
    INVENTED,
    PROVENANCE_KINDS,
    PSID_FILES,
    Link,
    PersonRecord,
    TrackMInputs,
    WorkerRecord,
)
from populace_dynamics.ss.params import SSAParameters

#: Where a cohort read from the staged PSID records its files' SHA-256
#: (``pipeline.PSID_FILES_SOURCE_KEY``; not imported here, so that
#: building inputs loads no share computation).
PSID_FILES_SOURCE_KEY = "psid_files_sha256"

__all__ = [
    "FIRST_PIA_FORMULA_YEAR",
    "build_track_m_inputs",
    "check_oracle_domain",
    "observed_histories",
    "own_claim_factor",
    "spouse_months_early",
    "survivor_months_early",
]

_MONTHS = 12


def own_claim_factor(
    basis: str, birth_year: int, window_year: int, params: SSAParameters
) -> float:
    """A worker's benefit-to-PIA factor at the entitlement year (rule 5).

    Old age: ``rules.claim_factor`` at the whole-year claim age;
    disability origin and death basis: 1.
    """

    if basis == BASIS_OLD_AGE:
        return rules.claim_factor(int(birth_year), int(window_year), params)
    return 1.0


def spouse_months_early(
    birth_year: int, claim_year: int, params: SSAParameters
) -> int:
    """Months before the spouse's own full retirement age at the claim."""

    months = params.fra_months(int(birth_year)) - _MONTHS * (
        int(claim_year) - int(birth_year)
    )
    return int(max(0, months))


def survivor_months_early(
    birth_year: int, claim_year: int, params: SSAParameters
) -> int:
    """Months before the end of the oracle's survivor reduction span.

    ``12 * survivor_earliest_claim_age + survivor_reduction_period_months``
    months of age (67 years at the defaults) less the claim age in whole
    years, bounded to [0, the span].
    """

    end = (
        _MONTHS * params.survivor_earliest_claim_age
        + params.survivor_reduction_period_months
    )
    months = end - _MONTHS * (int(claim_year) - int(birth_year))
    return int(min(max(0, months), params.survivor_reduction_period_months))


#: The first eligibility year of the PIA formula the oracle encodes:
#: ``ss.params.SSAParameters.bend_points`` scales the 1979 bend points
#: ($180 and $1,085) by the wage index for every year, so a PIA whose
#: section 4a bend-point year precedes 1979 would be computed under a
#: formula that did not govern it.
FIRST_PIA_FORMULA_YEAR = 1979


def check_oracle_domain(records: pd.DataFrame) -> None:
    """Refuse, before computing, a record the oracle cannot compute.

    ``ss.statutory_aime`` refuses a worker who attains 62 before 1975
    (``cohort.FIRST_AGE_62_YEAR_ENCODED``); the evaluation computes every
    record's PIA, so such a record is refused here with its id rather
    than deep inside the oracle.  (The M4 cohort drops links to such
    workers outside every policy window; the structural counts report
    how many records remain.)  A record in a policy window (window year
    2004 or later) whose threshold and bend-point year precedes
    :data:`FIRST_PIA_FORMULA_YEAR` is refused as well: its minimum would
    be compared with a PIA the oracle's 1979 formula computes for a year
    that formula did not govern (a worker who died before 1979 whose
    survivor first claimed in the window, for example).
    """

    early = records[
        records["birth_year"].astype(int) + 62 < FIRST_AGE_62_YEAR_ENCODED
    ]
    if len(early):
        raise ValueError(
            "worker records attain 62 before "
            f"{FIRST_AGE_62_YEAR_ENCODED}, outside the oracle: "
            f"{sorted(early['record_id'])[:10]}"
        )
    formula = records[
        (records["threshold_year"].astype(int) < FIRST_PIA_FORMULA_YEAR)
        & (records["window_year"].astype(int) >= min(POLICY_YEARS))
    ]
    if len(formula):
        raise ValueError(
            f"{len(formula)} worker records in a policy window have a "
            f"bend-point year before {FIRST_PIA_FORMULA_YEAR}, which the "
            "oracle's PIA formula does not govern: "
            f"{sorted(formula['record_id'])[:10]}"
        )


def observed_histories(
    earnings: pd.DataFrame, person_ids: set[int] | None = None
) -> dict[int, dict[int, float]]:
    """``{person: {income year: labor income}}`` from the earnings panel.

    Years after 2022 are dropped; a negative amount (none on the staged
    panel, whose constructed totals are nonnegative) is refused.
    """

    frame = earnings
    if person_ids is not None:
        frame = frame[frame["person_id"].isin(person_ids)]
    frame = frame[frame["period"] <= 2022]
    out: dict[int, dict[int, float]] = {}
    for pid, year, value in zip(
        frame["person_id"], frame["period"], frame["earnings"], strict=True
    ):
        value = float(value)
        if math.isnan(value):
            continue
        if value < 0:
            raise ValueError(f"person {pid}: negative labor income in {year}")
        person = out.setdefault(int(pid), {})
        if int(year) in person:
            raise ValueError(f"person {pid}: two panel rows for {year}")
        person[int(year)] = value
    return out


def _optional_int(value: Any) -> int | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if value is pd.NA:
        return None
    return int(value)


def build_track_m_inputs(
    cohort: TrackMCohort,
    *,
    earnings: pd.DataFrame,
    prior_year: pd.DataFrame,
    params: SSAParameters,
    cola_rates: Mapping[int, float],
    provenance_kind: str,
    source: Mapping[str, Any] | None = None,
) -> TrackMInputs:
    """M4's cohort and M5's histories as :class:`~.evaluation.TrackMInputs`.

    ``provenance_kind`` is ``"psid_files"`` for a cohort read from the
    staged PSID and ``"invented"`` for an invented one; the tabulation's
    guard reads it.
    """

    if provenance_kind not in PROVENANCE_KINDS:
        raise ValueError(f"provenance_kind must be one of {PROVENANCE_KINDS}")
    files = dict(cohort.provenance.get(PSID_FILES_SOURCE_KEY) or {})
    if files and provenance_kind != PSID_FILES:
        raise ValueError(
            "a cohort read from staged PSID files is marked psid_files, "
            f"not {provenance_kind!r}"
        )
    if provenance_kind == INVENTED and (
        cohort.provenance.get("label") != DRY_RUN_HEADER
    ):
        # Invented records need positive proof: the invented generator's
        # label (``invented_psid``), not merely the absence of file hashes.
        raise ValueError(
            "records are marked invented only for a cohort whose provenance "
            f"carries the invented label {DRY_RUN_HEADER!r}"
        )
    records = cohort.records
    ids = set(int(pid) for pid in records["person_id"])
    panel = observed_histories(earnings, ids)
    next_wave = pyl.next_wave_histories(
        prior_year[prior_year["person_id"].isin(ids)]
    )
    persons = cohort.persons.set_index("person_id")
    check_oracle_domain(records)
    first_cola = min(int(year) for year in cola_rates)
    diagnostics: dict[str, int] = {"ms5_out_of_window_before_cola_history": 0}
    factors: dict[str, float] = {}
    workers: dict[str, WorkerRecord] = {}
    for row in records.itertuples(index=False):
        pid = int(row.person_id)
        window = int(row.window_year)
        birth = int(row.birth_year)
        factor = own_claim_factor(row.basis, birth, window, params)
        factors[row.record_id] = factor
        in_scope = bool(
            row.in_universe
            and pid in persons.index
            and persons.loc[pid, "ms5_in_scope"]
        )
        if in_scope and int(row.threshold_year) < first_cola:
            # MS5's COLA factor runs from the threshold year's COLA; the
            # committed history starts with the COLA determined in 1979.
            if window >= min(POLICY_YEARS):
                raise ValueError(
                    f"{row.record_id}: MS5 needs the COLAs from "
                    f"{int(row.threshold_year)}, before the committed COLA "
                    f"history ({first_cola}), for a record in a policy "
                    "window"
                )
            # Outside every registered row's window no option flags the
            # record, so its MS5 PIA sets nothing; it keeps the MS0 PIA.
            in_scope = False
            diagnostics["ms5_out_of_window_before_cola_history"] += 1
        ms5: dict[str, Any] = {}
        if in_scope:
            ms5 = {
                "ms5_in_scope": True,
                "observed_benefit_2022": float(persons.loc[pid, "amount_2022"])
                / _MONTHS,
                "claim_factor": factor,
                "cola_factor": rules.cola_factor(
                    int(row.threshold_year), cola_rates
                ),
            }
        # Passed whole: ``coverage.one_history`` refuses a next-wave year
        # the panel also observes, rather than this module dropping it.
        observed = panel.get(pid, {})
        odd = dict(next_wave.get(pid, {}))
        workers[row.record_id] = WorkerRecord(
            record_id=row.record_id,
            birth_year=birth,
            basis=row.basis,
            window_year=window,
            observed=observed,
            next_wave=odd,
            onset_year=_optional_int(row.onset_year),
            death_year=_optional_int(row.death_year),
            unresolved=bool(row.unresolved),
            **ms5,
        )
    links_by_person: dict[int, list[Link]] = {}
    for row in cohort.links.itertuples(index=False):
        pid = int(row.person_id)
        birth = int(persons.loc[pid, "birth_year"])
        if row.kind == "spouse":
            link = Link(
                "spouse",
                row.record_id,
                months_early=spouse_months_early(
                    birth, int(row.claim_year), params
                ),
            )
        else:
            link = Link(
                "survivor",
                row.record_id,
                months_early=survivor_months_early(
                    birth, int(row.claim_year), params
                ),
                worker_claim_factor=factors[row.record_id],
            )
        links_by_person.setdefault(pid, []).append(link)
    person_records = []
    for pid, row in persons.iterrows():
        own = row["own_record_id"]
        own_id = None if own is None or pd.isna(own) else str(own)
        paid = bool(row["paid_own_worker_benefit"])
        person_records.append(
            PersonRecord(
                person_id=str(pid),
                family_unit_id=str(int(row["family_unit_id"])),
                weight=float(row["weight"]),
                sex=str(row["sex"]),
                stratum=int(row["stratum"]),
                cluster=int(row["cluster"]),
                own_record_id=own_id,
                paid_own_worker_benefit=paid,
                own_claim_factor=factors[own_id] if own_id else None,
                links=tuple(links_by_person.get(int(pid), ())),
                unlinked_auxiliary=bool(row["unlinked_auxiliary"]),
                other_member=bool(row["other_member"]),
            )
        )
    return TrackMInputs(
        workers=workers,
        persons=tuple(person_records),
        provenance_kind=provenance_kind,
        design=cohort.design,
        source={
            "cohort": "min_benefit_track_m.cohort",
            "careers": "min_benefit_track_m.careers",
            "careers_diagnostics": diagnostics,
            **dict(source or {}),
            **({PSID_FILES_SOURCE_KEY: files} if files else {}),
        },
    )
