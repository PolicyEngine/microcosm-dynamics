"""An INVENTED, PSID-shaped Track M cohort for the dry run (plan M10).

INVENTED DATA - NOT A COMPARISON.  Every person, family unit, weight,
design variable, birth year, entitlement, onset, death, earnings history
and observed benefit here is drawn from a seeded random generator.  No
PSID value, Census value, model output or comparator value enters it.
The shapes follow the M1 specification so that every rule runs:

* the universe: persons born 1960 or earlier in family units, with a
  weight, a sex (one person with sex unknown, ER32000 code 9), and a
  stratum and cluster from an invented design frame (20 strata, 2-3
  clusters each), shared by every person of a family unit;
* worker records of all three bases of section 4a (old age, disability
  origin, died before any own entitlement), in and out of the window, a
  few marked unresolved (section 4b rule 3);
* the earnings panel's shape: labor income observed every year 1968-1996
  and every even year 1998-2022, none before 1968; the next wave's odd
  years 2001-2021 for most reference persons and spouses, never 1997 or
  1999; sparse years for other family-unit members;
* couples (a spouse's link to a living worker who receives in 2022, some
  spouses with no record of their own), widow(er)s (a survivor's link to
  a deceased worker's record), unlinked auxiliaries and other members;
* MS5's inputs for records whose 2022 amount is their own worker benefit
  alone: an invented observed benefit near the history PIA times the claim
  factor (``rules.claim_factor``) and the COLA factor (``rules.cola_factor``
  over the COLA rates the caller passes).

Every in-window record's threshold year is 2003 or later
(:data:`INVENTED_THRESHOLD_YEARS`, the years the invented thresholds of
:func:`invented_parameters` cover; the real Census capture also covers
fifteen years before 2003); the dry run checks records with other years
separately (the named error of referee R8).
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.min_benefit_track_m import (
    DRY_RUN_HEADER,
    coverage,
    rules,
)
from populace_dynamics.min_benefit_track_m.evaluation import (
    INVENTED,
    Link,
    PersonRecord,
    TrackMInputs,
    TrackMParameters,
    WorkerRecord,
)
from populace_dynamics.min_benefit_track_m.policy import HEADLINE_POLICY_YEAR
from populace_dynamics.ss.params import SSAParameters

__all__ = [
    "INVENTED_LABEL",
    "INVENTED_THRESHOLD_YEARS",
    "PANEL_YEARS",
    "invented_parameters",
    "invented_track_m_inputs",
]

INVENTED_LABEL = DRY_RUN_HEADER
#: The years :func:`invented_parameters` gives an invented threshold: the
#: years the invented cohort's in-window records need (2003-2022).  Fixed
#: here rather than read from the real capture's years, so that the
#: invented tests' refusals of a year before 2003 do not move with it.
INVENTED_THRESHOLD_YEARS: tuple[int, ...] = tuple(range(2003, 2023))
#: The earnings panel's income years: every year 1968-1996, even years
#: 1998-2022 (``data/family.py``).
PANEL_YEARS: tuple[int, ...] = (
    *range(1968, 1997),
    *range(1998, 2023, 2),
)
_NEXT_WAVE_YEARS = tuple(range(2001, 2022, 2))
_LAST_BIRTH_YEAR = 1960
_FIRST_BIRTH_YEAR = 1928
_N_STRATA = 20
#: Old-age claim ages and their invented probabilities.
_CLAIM_AGES = (62, 63, 64, 65, 66, 67, 68, 69, 70)
_CLAIM_PROBS = (0.42, 0.07, 0.06, 0.14, 0.18, 0.07, 0.02, 0.01, 0.03)


class _Generator:
    def __init__(
        self,
        seed: int,
        params: SSAParameters,
        cola_rates: Mapping[int, float],
    ) -> None:
        self.rng = np.random.default_rng(seed)
        self.params = params
        self.cola_rates = cola_rates
        self.workers: dict[str, WorkerRecord] = {}
        self.counter = 0
        clusters = self.rng.integers(2, 4, size=_N_STRATA)
        self.design = pd.DataFrame(
            [
                {"stratum": stratum + 1, "cluster": cluster + 1}
                for stratum in range(_N_STRATA)
                for cluster in range(int(clusters[stratum]))
            ]
        )

    # -- draws ------------------------------------------------------------
    def birth_year(self, low: int = _FIRST_BIRTH_YEAR) -> int:
        # more of the younger cohorts, as among today's beneficiaries
        u = self.rng.random() ** 0.7
        return int(low + round(u * (_LAST_BIRTH_YEAR - low)))

    def history(
        self, birth: int, last: int, *, member: str
    ) -> tuple[dict[int, float], dict[int, float]]:
        """Invented labor income: observed panel years and next-wave odd
        years, through ``last``."""

        rng = self.rng
        start = birth + int(rng.integers(18, 27))
        low = rng.random() < 0.3
        level = float(
            np.exp(rng.normal(-1.9 if low else -0.4, 0.55 if low else 0.45))
        )
        out_rate = float(rng.choice([0.03, 0.12, 0.35], p=[0.5, 0.3, 0.2]))
        nawi = self.params.nawi
        earnings: dict[int, float] = {}
        for year in range(max(start, 1951), last + 1):
            if year not in nawi or rng.random() < out_rate:
                earnings[year] = 0.0
                continue
            noise = float(np.exp(rng.normal(0.0, 0.25)))
            earnings[year] = round(level * nawi[year] * noise, 0)
        observed = {}
        for year in PANEL_YEARS:
            if year > last:
                break
            if member == "other" and rng.random() < 0.6:
                continue
            observed[year] = earnings.get(year, 0.0)
        next_wave = {}
        if member != "other":
            for year in _NEXT_WAVE_YEARS:
                if year <= last and rng.random() < 0.85:
                    next_wave[year] = earnings.get(year, 0.0)
        return observed, next_wave

    def new_id(self) -> str:
        self.counter += 1
        return f"W{self.counter:05d}"

    def old_age_window(self, birth: int) -> int:
        age = int(self.rng.choice(_CLAIM_AGES, p=_CLAIM_PROBS))
        window = min(birth + age, 2022)
        # Keep every in-window threshold year within the capture: a worker
        # born before 1941 (threshold year 2002 or earlier) is entitled
        # before the policy year here.
        if birth < 1941:
            window = min(window, HEADLINE_POLICY_YEAR - 1)
        return window

    # -- records ----------------------------------------------------------
    def worker(
        self, birth: int, *, member: str, ms5: bool
    ) -> tuple[WorkerRecord, float]:
        """An own worker record and its own claim factor."""

        rng = self.rng
        if birth + 22 < 2022 and rng.random() < 0.14:
            onset = birth + int(rng.integers(35, 62))
            window = onset + 1  # section 4b rule 4
            if window <= 2022:
                observed, next_wave = self.history(
                    birth, onset - 1, member=member
                )
                record = WorkerRecord(
                    self.new_id(),
                    birth,
                    rules.BASIS_DISABILITY,
                    window,
                    observed,
                    next_wave,
                    onset_year=onset,
                )
                return self._with_ms5(record, 1.0, ms5), 1.0
        window = self.old_age_window(birth)
        observed, next_wave = self.history(birth, window - 1, member=member)
        factor = rules.claim_factor(birth, window, self.params)
        record = WorkerRecord(
            self.new_id(),
            birth,
            rules.BASIS_OLD_AGE,
            window,
            observed,
            next_wave,
            # section 4b rule 3: receipt in 2004, status in 2003 unknown
            unresolved=bool(
                window in (HEADLINE_POLICY_YEAR - 1, HEADLINE_POLICY_YEAR)
                and rng.random() < 0.4
            ),
        )
        return self._with_ms5(record, factor, ms5), factor

    def _with_ms5(
        self, record: WorkerRecord, factor: float, ms5: bool
    ) -> WorkerRecord:
        # The committed COLA history starts with the 1979 determination.
        if not ms5 or record.years.threshold_year < 1979:
            return record
        pia = rules.history_pia(
            {**record.next_wave, **record.observed},
            birth_year=record.birth_year,
            params=self.params,
            basis=record.basis,
            window_year=record.window_year,
            onset_year=record.onset_year,
        ).pia
        cola = rules.cola_factor(record.years.threshold_year, self.cola_rates)
        observed = (
            pia * factor * cola * float(np.exp(self.rng.normal(0.0, 0.04)))
        )
        return WorkerRecord(
            record.record_id,
            record.birth_year,
            record.basis,
            record.window_year,
            record.observed,
            record.next_wave,
            onset_year=record.onset_year,
            ms5_in_scope=True,
            observed_benefit_2022=round(observed, 2),
            claim_factor=factor,
            cola_factor=cola,
            unresolved=record.unresolved,
        )

    def deceased(self, survivor_birth: int) -> tuple[WorkerRecord, int, float]:
        """A deceased spouse's record, the survivor's first entitlement
        year on it, and the deceased's claim factor."""

        rng = self.rng
        birth = int(
            np.clip(
                survivor_birth + rng.integers(-5, 4),
                _FIRST_BIRTH_YEAR - 5,
                _LAST_BIRTH_YEAR + 3,
            )
        )
        if rng.random() < 0.45:
            # died before any own entitlement, 2003 or later, aged 45-66
            earliest = max(2003, birth + 45)
            latest = min(2021, birth + 66)
            if earliest <= latest:
                death = int(rng.integers(earliest, latest + 1))
                survivor_first = max(death, survivor_birth + 60)
                survivor_first = min(survivor_first, 2022)
                if survivor_first >= death and birth + 62 >= 2003:
                    observed, next_wave = self.history(
                        birth, death - 1, member="rp"
                    )
                    record = WorkerRecord(
                        self.new_id(),
                        birth,
                        rules.BASIS_DEATH,
                        survivor_first,
                        observed,
                        next_wave,
                        death_year=death,
                    )
                    return record, survivor_first, 1.0
        birth = max(birth, _FIRST_BIRTH_YEAR)
        birth = min(birth, _LAST_BIRTH_YEAR)
        window = self.old_age_window(birth)
        observed, next_wave = self.history(birth, window - 1, member="rp")
        record = WorkerRecord(
            self.new_id(),
            birth,
            rules.BASIS_OLD_AGE,
            window,
            observed,
            next_wave,
        )
        factor = rules.claim_factor(birth, window, self.params)
        survivor_first = min(max(window, survivor_birth + 60), 2022)
        return record, survivor_first, factor

    def months_early(self, birth: int, claim_year: int) -> int:
        months = self.params.fra_months(birth) - 12 * (claim_year - birth)
        return int(max(0, months))


def invented_track_m_inputs(
    *,
    seed: int = 0,
    n_family_units: int = 600,
    params: SSAParameters,
    cola_rates: Mapping[int, float],
) -> TrackMInputs:
    """The INVENTED cohort: persons, worker records and a design frame.

    ``params`` supplies the wage index (earnings levels), the full
    retirement ages and the reductions (claim factors); ``cola_rates``
    maps a COLA determination year to a fraction (MS5's COLA factor).
    Deterministic for a given seed and parameters.
    """

    gen = _Generator(seed, params, cola_rates)
    rng = gen.rng
    persons: list[PersonRecord] = []
    counts: dict[str, int] = {}

    def add_person(**kwargs: Any) -> None:
        persons.append(
            PersonRecord(
                person_id=f"P{len(persons) + 1:05d}",
                weight=round(float(np.exp(rng.normal(8.4, 0.6))), 1),
                **kwargs,
            )
        )

    for unit in range(n_family_units):
        unit_id = f"FU{unit + 1:04d}"
        stratum = int(rng.integers(1, _N_STRATA + 1))
        clusters = gen.design.loc[gen.design["stratum"] == stratum, "cluster"]
        # every person of a family unit shares its stratum and cluster
        design = {
            "stratum": stratum,
            "cluster": int(rng.choice(clusters.to_numpy())),
        }
        kind = str(
            rng.choice(
                ["single", "couple", "widowed", "unlinked"],
                p=[0.33, 0.44, 0.2, 0.03],
            )
        )
        counts[kind] = counts.get(kind, 0) + 1
        sex = str(rng.choice(["male", "female"]))
        birth = gen.birth_year()
        if kind == "unlinked":
            add_person(
                family_unit_id=unit_id,
                sex="female",
                **design,
                unlinked_auxiliary=True,
            )
            continue
        if kind == "widowed":
            record, first, dead_factor = gen.deceased(birth)
            gen.workers[record.record_id] = record
            own = rng.random() < 0.8
            own_record, own_factor = (None, None)
            if own:
                own_record, own_factor = gen.worker(
                    birth, member="rp", ms5=False
                )
                gen.workers[own_record.record_id] = own_record
            survivor_claim = max(first, birth + 60)
            add_person(
                family_unit_id=unit_id,
                sex="female" if rng.random() < 0.8 else "male",
                **design,
                own_record_id=own_record.record_id if own_record else None,
                paid_own_worker_benefit=own,
                own_claim_factor=own_factor,
                links=(
                    Link(
                        "survivor",
                        record.record_id,
                        months_early=min(
                            84, gen.months_early(birth, survivor_claim)
                        ),
                        worker_claim_factor=dead_factor,
                    ),
                ),
            )
            continue
        ms5 = rng.random() < 0.6
        head, head_factor = gen.worker(birth, member="rp", ms5=ms5)
        gen.workers[head.record_id] = head
        add_person(
            family_unit_id=unit_id,
            sex=sex,
            **design,
            own_record_id=head.record_id,
            paid_own_worker_benefit=True,
            own_claim_factor=head_factor,
        )
        if kind == "couple":
            spouse_birth = int(
                np.clip(
                    birth + rng.integers(-4, 5),
                    _FIRST_BIRTH_YEAR,
                    _LAST_BIRTH_YEAR,
                )
            )
            spouse_sex = "female" if sex == "male" else "male"
            if rng.random() < 0.82:
                spouse, spouse_factor = gen.worker(
                    spouse_birth, member="spouse", ms5=False
                )
                gen.workers[spouse.record_id] = spouse
                claim = spouse.window_year
                own_id, paid = spouse.record_id, True
            else:
                own_id, paid, spouse_factor = None, False, None
                claim = min(spouse_birth + int(rng.integers(62, 68)), 2022)
            add_person(
                family_unit_id=unit_id,
                sex=spouse_sex,
                **design,
                own_record_id=own_id,
                paid_own_worker_benefit=paid,
                own_claim_factor=spouse_factor,
                links=(
                    Link(
                        "spouse",
                        head.record_id,
                        months_early=gen.months_early(spouse_birth, claim),
                    ),
                ),
            )
        if rng.random() < 0.08:
            member_birth = gen.birth_year(low=1935)
            member, member_factor = gen.worker(
                member_birth, member="other", ms5=False
            )
            gen.workers[member.record_id] = member
            add_person(
                family_unit_id=unit_id,
                sex=str(rng.choice(["male", "female"])),
                **design,
                own_record_id=member.record_id,
                paid_own_worker_benefit=True,
                own_claim_factor=member_factor,
                other_member=True,
            )
    # One person with sex unknown (ER32000 code 9): All only.
    persons[0] = dataclasses.replace(persons[0], sex="unknown")
    return TrackMInputs(
        workers=dict(gen.workers),
        persons=tuple(persons),
        provenance_kind=INVENTED,
        design=gen.design,
        source={
            "label": INVENTED_LABEL,
            "generator": "min_benefit_track_m.invented",
            "seed": seed,
            "n_family_units": n_family_units,
            "family_unit_kinds": dict(sorted(counts.items())),
            "parameters_revision": params.pe_us_revision,
        },
    )


def invented_parameters() -> tuple[TrackMParameters, dict[int, float]]:
    """INVENTED parameters, for tests that must not read any checkout.

    An invented wage index (2,800 in 1951, growing 4 percent a year), wage
    base, PIA factors (90, 32 and 15 percent), full retirement ages and
    reduction rates; quarter-of-coverage amounts of 2.4 percent of that
    wage index; one-person 65+ thresholds of $8,000 in 2003 growing 2.5
    percent a year to 2022 (:data:`INVENTED_THRESHOLD_YEARS`: the invented
    cohort's years, not the real capture's, which also holds fifteen years
    before 2003); and COLAs of 2.5 percent for 1979-2021.  None is an SSA,
    Census or PSID value.  Returns the parameters and the COLA rates.
    """

    nawi = {
        year: 2_800.0 * 1.04 ** (year - 1951) for year in range(1951, 2061)
    }
    params = SSAParameters(
        nawi=nawi,
        wage_base={1937: 3_000.0, 1975: 14_100.0, 1990: 51_300.0},
        pia_factors=(0.9, 0.32, 0.15),
        fra_months_by_birth_year=[(1900, 792), (1955, 804)],
        early_monthly_rates=(5 / 900, 5 / 1200),
        early_first_bracket_months=36,
        pe_us_revision="INVENTED",
        delayed_credit_by_birth_year=[(1900, 0.08)],
    )
    qc = coverage.QuarterOfCoverageAmounts(
        {year: round(0.024 * nawi[year], 0) for year in range(1978, 2031)},
        {"kind": "INVENTED"},
    )
    thresholds = rules.AgedThresholds(
        {
            year: round(8_000.0 * 1.025 ** (year - 2003), 0)
            for year in INVENTED_THRESHOLD_YEARS
        },
        {"kind": "INVENTED", "years": [2003, 2022]},
    )
    cola = {year: 0.025 for year in range(1979, 2022)}
    return TrackMParameters(params, qc, thresholds), cola
