"""INVENTED age-67 cohort inputs and thresholds (dry runs and tests only).

Every person, family, income amount, Social Security and SSI amount,
wealth component, weight, sampling stratum and cluster produced here is
INVENTED by a seeded generator.  Nothing is a PSID observation, an SSA or
Census statistic, or a comparator value.  The frames have the shapes of
the Track U readers (:class:`populace_dynamics.cohorts.age67.Age67Inputs`:
the individual-file anchors of waves 2005-2013, the design variables, the
death and marriage records, and the family income and wealth frames of
:mod:`populace_dynamics.data.family_income`), so the invented population
runs through the real age-67 builder, the income concept and the
tabulation without touching PSID.

The family mix is chosen to exercise every Track U path, not to resemble
any real population:

* retired couples (both members sometimes in the target cohort, so a
  family unit holds two members), single retirees (widowed, divorced,
  never married, and an undated marriage whose status is ``unknown``),
  low-income singles near the invented threshold, SSI recipients (some
  above the federal maximum, a stand-in for a state supplement) and SSI
  couples;
* a parent in the target cohort living as an OFUM in an adult child's
  family with a grandchild under 18 (U4 and U10), some without a
  marriage-history record (birth year from the seed coordinate); and
  couples in the target cohort with an earning adult child as an OFUM
  (U4 drops the child's income for them);
* couples still working at 67 with business, farm and rental losses
  (negative items the codebooks allow) and large wealth; retired couples
  with farm income and head IRA income, and retired singles with annuity
  income (the head's annuity and IRA income is ``HEAD ANNUITIES`` before
  2013 and ``HEAD ANNUITIES`` plus ``HEAD IRAS`` in 2013, as in the
  codebooks); singles with negative WEALTH1; cohabiting couples
  (relationship 22, not married; the partner's birth year inferred from
  invented earnings); separated members whose spouse lives elsewhere;
* couples with a legal wife (code 20) in which the head's marriage
  history cannot date the marriage (``unknown``) or the wife has no
  marriage-history record, and female
  heads with a legal husband (code 90) who has no marriage-history
  record (the relationship-code resolution of unresolved marital states;
  the husband's income is put in the family file's "wife" items, an
  invented assumption not checked against the codebooks);
* members who enter an institution (sequence 51) in the first wave whose
  income year is at or after their 66th birthday year and stay, attached
  to the family they left, where the spouse becomes head (the
  unregistered institution option; row U-inst was withdrawn in
  u1-draft-5);
  members who move out (71) or die (81) by that wave's interview; and
  members whose weight is zero from that wave.

Individual-file ages are ages at the interview: a person whose invented
birthday falls before the interview is one year older than the income
year minus the birth year, as in the PSID, so the birth-year law's seed
coordinate and the wave age can differ from the income-year age.

Every family unit's income adds up exactly under the codebook identities
(:func:`populace_dynamics.data.family_income.reconcile_family_income`),
and WEALTH1 equals its assets less its debts in every wave.  Waves 2005
and 2007 have no invented wealth unless ``supplement_waves_staged`` (the
real supplements are not staged, cos decision d189); with it they carry
invented wealth in the 2009 component layout.

The threshold table (:func:`invented_poverty_thresholds`) is INVENTED
too: round numbers in the shape of the Census tables, not Census values.
The Census thresholds are not captured (cos decision d194).

Provenance: the inputs record ``kind="invented"``, the seed, the
supplement flag and the SHA-256 of their frames, which the age-67 builder
checks.  A recorded digest proves nothing on its own, so
:func:`check_invented_inputs` and :func:`check_invented_cohort`
re-generate the frames from the seed and compare.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterable, Mapping
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.cohorts import age67
from populace_dynamics.data import family_income
from populace_dynamics.estimates import adjusted_poverty as ap

__all__ = [
    "DEFAULT_SEED",
    "INVENTED_FAMILY_COUNTS",
    "INVENTED_INPUTS_LABEL",
    "INVENTED_THRESHOLDS_LABEL",
    "INVENTED_THRESHOLD_BASE_2004",
    "check_invented_cohort",
    "check_invented_inputs",
    "invented_age67_inputs",
    "invented_frames_sha256",
    "invented_needs_standard",
    "invented_poverty_thresholds",
]

INVENTED_INPUTS_LABEL = (
    "INVENTED DATA: synthetic persons and families in the Track U age-67 "
    "reader shapes (PSID individual and family files, waves 2005-2013); "
    "not PSID observations"
)
INVENTED_THRESHOLDS_LABEL = (
    "INVENTED THRESHOLDS: made-up round numbers in the shape of the Census "
    "poverty-threshold tables, not Census values; the Census thresholds "
    "are not captured (cos decision d194)"
)
DEFAULT_SEED = 20260924
_GENERATOR = (
    "populace_dynamics.uniform_cut_track_u.invented.invented_age67_inputs"
)

#: Families per invented type.
INVENTED_FAMILY_COUNTS: dict[str, int] = {
    "retired_couple": 36,
    "retired_single": 30,
    "ssi_single": 12,
    "ssi_couple": 4,
    "near_threshold_single": 24,
    "elder_with_child": 10,
    "couple_with_adult_child": 6,
    "working_couple": 10,
    "negative_wealth_single": 8,
    "cohabiting_couple": 8,
    "separated": 4,
    "unresolved_couple": 4,
    "legal_husband_couple": 3,
    "institution_spouse": 6,
    "mover_out": 3,
    "decedent": 3,
    "zero_weight": 2,
}

#: INVENTED threshold rows for income year 2004 (round numbers, not the
#: Census values); later years grow by :data:`_THRESHOLD_GROWTH`.
INVENTED_THRESHOLD_BASE_2004: dict[str, float] = {
    "one_under_65": 9_800.0,
    "one_65_plus": 9_000.0,
    "two_under_65": 12_600.0,
    "two_65_plus": 11_400.0,
    "three": 15_000.0,
    "four": 19_300.0,
    "five": 22_800.0,
    "six": 25_800.0,
    "seven": 29_300.0,
    "eight": 32_600.0,
    "nine_plus": 39_000.0,
}
_THRESHOLD_SIZES: dict[str, int] = {
    "one_under_65": 1,
    "one_65_plus": 1,
    "two_under_65": 2,
    "two_65_plus": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine_plus": 9,
}
#: INVENTED annual growth of thresholds and of income amounts.
_THRESHOLD_GROWTH = 0.028
_PRICE_GROWTH = 0.028
#: INVENTED annual growth of wealth components.
_WEALTH_GROWTH = 0.03
#: An invented monthly SSI payment level (not the federal benefit rate).
_INVENTED_SSI_MONTHLY_2004 = 560.0
_YEARS = tuple(range(2004, 2013))
_WAVES = age67.WAVES
_TARGET_YEARS = age67.ALL_BIRTH_YEARS
_FAMILY_UNIT_OFFSET = 1_000
_PERSON_BASE = 500_000
_N_STRATA = 8
_SEQ_INSTITUTION, _SEQ_MOVED, _SEQ_DIED = 51, 71, 81
_HEAD, _WIFE, _PARTNER, _PARENT, _GRANDCHILD = 10, 20, 22, 50, 60
_LEGAL_HUSBAND = 90
#: Relationship codes whose person fills the family file's "wife" items.
_SPOUSE_CODES = (_WIFE, _PARTNER, _LEGAL_HUSBAND)
#: Individual-income items of an invented person, in 2004 dollars.
_ITEMS = (
    "labor",
    "farm",
    "business_labor",
    "business_asset",
    "rent",
    "dividends",
    "interest",
    "trusts",
    "ss",
    "ssi",
    "pension",
    "annuity",
    "va",
    "other_retirement",
    "ira",
)
_WEALTH_ITEMS = (
    "farm_business",
    "checking_saving",
    "other_real_estate",
    "stocks",
    "vehicles",
    "other_assets",
    "ira_annuity",
    "unsecured_debt",
    "home_equity",
)


# =========================================================================
# Thresholds
# =========================================================================
def _threshold(row: str, year: int) -> float:
    base = INVENTED_THRESHOLD_BASE_2004[row]
    value = base * (1.0 + _THRESHOLD_GROWTH) ** (int(year) - 2004)
    return float(round(value / 10.0) * 10)


def _matrix_value(row: str, year: int, children: int) -> float:
    value = _threshold(row, year) * (1.02 - 0.015 * int(children))
    return float(round(value / 10.0) * 10)


def invented_poverty_thresholds(
    years: Iterable[int] = _YEARS,
) -> ap.PovertyThresholds:
    """INVENTED thresholds in the Census table shapes (not Census values).

    Weighted averages: :data:`INVENTED_THRESHOLD_BASE_2004` grown by 2.8
    percent a year and rounded to $10.  Matrix: the weighted average times
    ``1.02 - 0.015 * children`` for children 0 to ``min(size - 1, 8)``,
    rounded to $10.  Its provenance kind is ``invented``, which a
    registered run refuses.
    """

    years = tuple(int(year) for year in years)
    weighted = {
        year: {row: _threshold(row, year) for row in ap.THRESHOLD_ROW_KEYS}
        for year in years
    }
    matrix = {
        year: {
            row: {
                children: _matrix_value(row, year, children)
                for children in range(min(_THRESHOLD_SIZES[row] - 1, 8) + 1)
            }
            for row in ap.THRESHOLD_ROW_KEYS
        }
        for year in years
    }
    return ap.PovertyThresholds(
        weighted_average=weighted,
        matrix=matrix,
        provenance={
            "kind": ap.INVENTED,
            "label": INVENTED_THRESHOLDS_LABEL,
            "generator": (
                "populace_dynamics.uniform_cut_track_u.invented."
                "invented_poverty_thresholds"
            ),
            "base_2004": dict(INVENTED_THRESHOLD_BASE_2004),
            "annual_growth": _THRESHOLD_GROWTH,
        },
    )


def invented_needs_standard(
    year: int, size: int, children: int, head_age: int | None
) -> int:
    """An INVENTED stand-in for PSID's CENSUS NEEDS STANDARD (row U8).

    The invented matrix cell by unit size, children and the householder's
    age (the under-65 rows for a head under 65), not the 65-and-over rule.
    """

    size = int(size)
    if size <= 2:
        older = head_age is not None and int(head_age) >= 65
        row = ("one" if size == 1 else "two") + (
            "_65_plus" if older else "_under_65"
        )
    else:
        row = {3: "three", 4: "four", 5: "five", 6: "six", 7: "seven"}.get(
            size, "eight" if size == 8 else "nine_plus"
        )
    column = min(int(children), size - 1, 8)
    return int(_matrix_value(row, year, column))


# =========================================================================
# Families
# =========================================================================
def _first_wave(birth_year: int) -> int:
    """The first wave whose income year is at or after age 66."""

    return next(w for w in _WAVES if w - 1 >= birth_year + 66)


class _Builder:
    """Accumulates invented families (one pass, fixed draw order)."""

    def __init__(self, rng: np.random.Generator) -> None:
        self.rng = rng
        self.families: list[dict[str, Any]] = []
        self.target_counter = 0

    # -- draws -------------------------------------------------------------
    def uniform(self, low: float, high: float) -> float:
        return float(self.rng.uniform(low, high))

    def chance(self, p: float) -> bool:
        return bool(self.rng.random() < p)

    def target_year(self) -> int:
        year = _TARGET_YEARS[self.target_counter % len(_TARGET_YEARS)]
        self.target_counter += 1
        return int(year)

    def sex(self) -> str:
        return str(self.rng.choice(["female", "male"]))

    # -- persons -----------------------------------------------------------
    def person(
        self,
        family: dict[str, Any],
        slot: int,
        *,
        sex: str,
        birth_year: int,
        marital: str,
        spouse_slot: int | None = None,
        **income: float,
    ) -> dict[str, Any]:
        roll = self.rng.random()
        reported: int | None = birth_year
        if roll < 0.08:
            reported = None
        elif roll < 0.10:
            reported = birth_year + 1
        person = {
            "person_id": _PERSON_BASE + 100 * family["index"] + slot,
            "slot": slot,
            "sex": sex,
            "birth_year": int(birth_year),
            "marital": marital,
            "spouse_slot": spouse_slot,
            "reported_birth_year": reported,
            "ss_start_age": int(self.rng.integers(62, 67)),
            # 1 when the invented birthday falls before the interview.
            "birthday_before_interview": int(self.rng.random() < 0.6),
            "income": {item: float(income.get(item, 0.0)) for item in _ITEMS},
            "noise": {
                wave: float(np.exp(self.rng.normal(0.0, 0.04)))
                for wave in _WAVES
            },
            "earnings_rows": False,
        }
        family["persons"].append(person)
        return person

    def family(self, family_type: str) -> dict[str, Any]:
        index = len(self.families) + 1
        family = {
            "type": family_type,
            "index": index,
            "persons": [],
            "roster": {},
            "weight": round(self.uniform(1_500.0, 15_000.0), 2),
            "zero_weight": {},
            "stratum": 1 + index % _N_STRATA,
            "cluster": 1 + (index // _N_STRATA) % 2,
            "wealth": {item: 0.0 for item in _WEALTH_ITEMS},
            "wealth_imputed": self.chance(0.1),
            "ss_imputed": self.chance(0.05),
            "death_year": {},
        }
        self.families.append(family)
        return family

    def steady_roster(
        self, family: dict[str, Any], members: list[tuple[int, int, int]]
    ) -> None:
        """Every wave: ``(slot, sequence, relationship)`` for each member."""

        for wave in _WAVES:
            family["roster"][wave] = list(members)

    def wealth(self, family: dict[str, Any], **values: float) -> None:
        for key, value in values.items():
            family["wealth"][key] = float(value)

    # -- family types ------------------------------------------------------
    def retired_couple(self) -> None:
        family = self.family("retired_couple")
        head_birth = self.target_year()
        wife_birth = int(
            np.clip(head_birth + self.rng.integers(-4, 6), 1930, 1955)
        )
        modest = self.chance(0.25)
        self.person(
            family,
            1,
            sex="male",
            birth_year=head_birth,
            marital="married",
            spouse_slot=2,
            ss=(
                self.uniform(8_000, 11_000)
                if modest
                else self.uniform(11_000, 22_000)
            ),
            pension=(
                0.0
                if modest or self.chance(0.5)
                else self.uniform(3_000, 25_000)
            ),
            interest=self.uniform(0, 3_000) if self.chance(0.6) else 0.0,
            dividends=self.uniform(0, 5_000) if self.chance(0.3) else 0.0,
            rent=self.uniform(-3_000, 8_000) if self.chance(0.1) else 0.0,
            ira=self.uniform(1_000, 8_000) if self.chance(0.2) else 0.0,
            farm=self.uniform(-2_000, 9_000) if self.chance(0.1) else 0.0,
        )
        self.person(
            family,
            2,
            sex="female",
            birth_year=wife_birth,
            marital="married",
            spouse_slot=1,
            ss=(
                self.uniform(3_000, 6_000)
                if modest
                else self.uniform(5_000, 13_000)
            ),
            pension=self.uniform(2_000, 10_000) if self.chance(0.3) else 0.0,
            interest=self.uniform(0, 1_500) if self.chance(0.4) else 0.0,
        )
        self.steady_roster(family, [(1, 1, _HEAD), (2, 2, _WIFE)])
        if modest:
            self.wealth(
                family,
                checking_saving=self.uniform(0, 4_000),
                vehicles=self.uniform(0, 6_000),
                unsecured_debt=self.uniform(0, 3_000),
                home_equity=self.uniform(0, 60_000),
            )
        else:
            self.wealth(
                family,
                checking_saving=self.uniform(2_000, 40_000),
                stocks=(
                    self.uniform(5_000, 200_000) if self.chance(0.4) else 0.0
                ),
                ira_annuity=(
                    self.uniform(10_000, 300_000) if self.chance(0.5) else 0.0
                ),
                vehicles=self.uniform(3_000, 25_000),
                other_real_estate=(
                    self.uniform(20_000, 150_000) if self.chance(0.1) else 0.0
                ),
                other_assets=(
                    self.uniform(1_000, 30_000) if self.chance(0.1) else 0.0
                ),
                unsecured_debt=(
                    self.uniform(500, 15_000) if self.chance(0.3) else 0.0
                ),
                home_equity=(
                    self.uniform(30_000, 250_000) if self.chance(0.8) else 0.0
                ),
            )

    def retired_single(self) -> None:
        family = self.family("retired_single")
        birth = self.target_year()
        roll = self.rng.random()
        marital = (
            "widowed"
            if roll < 0.5
            else (
                "divorced"
                if roll < 0.75
                else "never_married" if roll < 0.9 else "unknown"
            )
        )
        self.person(
            family,
            1,
            sex=self.sex(),
            birth_year=birth,
            marital=marital,
            ss=self.uniform(7_000, 17_000),
            pension=self.uniform(2_000, 12_000) if self.chance(0.3) else 0.0,
            interest=self.uniform(0, 1_200) if self.chance(0.5) else 0.0,
            annuity=self.uniform(500, 6_000) if self.chance(0.2) else 0.0,
        )
        self.steady_roster(family, [(1, 1, _HEAD)])
        self.wealth(
            family,
            checking_saving=self.uniform(500, 20_000),
            ira_annuity=(
                self.uniform(5_000, 80_000) if self.chance(0.3) else 0.0
            ),
            vehicles=self.uniform(1_000, 12_000) if self.chance(0.5) else 0.0,
            unsecured_debt=(
                self.uniform(200, 5_000) if self.chance(0.2) else 0.0
            ),
            home_equity=(
                self.uniform(20_000, 150_000) if self.chance(0.5) else 0.0
            ),
        )

    def _ssi_amount(self, ss: float, above_federal: bool) -> float:
        base = 12 * _INVENTED_SSI_MONTHLY_2004 - max(0.0, ss - 240.0)
        amount = max(0.0, base) * self.uniform(0.8, 1.0)
        return amount + (1_200.0 if above_federal else 0.0)

    def ssi_single(self) -> None:
        family = self.family("ssi_single")
        ss = self.uniform(2_400, 6_000)
        self.person(
            family,
            1,
            sex=self.sex(),
            birth_year=self.target_year(),
            marital="never_married" if self.chance(0.5) else "divorced",
            ss=ss,
            ssi=self._ssi_amount(ss, above_federal=self.chance(0.25)),
        )
        self.steady_roster(family, [(1, 1, _HEAD)])
        self.wealth(
            family,
            checking_saving=self.uniform(0, 1_500),
            vehicles=self.uniform(0, 2_500) if self.chance(0.5) else 0.0,
        )

    def ssi_couple(self) -> None:
        family = self.family("ssi_couple")
        head_birth = self.target_year()
        for slot, sex, spouse in ((1, "male", 2), (2, "female", 1)):
            ss = self.uniform(2_000, 5_000)
            self.person(
                family,
                slot,
                sex=sex,
                # Both members share a birth year, so under U0 one family
                # unit holds two observations.
                birth_year=head_birth,
                marital="married",
                spouse_slot=spouse,
                ss=ss,
                ssi=self._ssi_amount(ss, above_federal=False) * 0.75,
            )
        self.steady_roster(family, [(1, 1, _HEAD), (2, 2, _WIFE)])
        self.wealth(
            family,
            checking_saving=self.uniform(0, 2_000),
            vehicles=self.uniform(0, 3_000),
        )

    def near_threshold_single(self) -> None:
        family = self.family("near_threshold_single")
        target = INVENTED_THRESHOLD_BASE_2004["one_65_plus"]
        self.person(
            family,
            1,
            sex=self.sex(),
            birth_year=self.target_year(),
            marital="widowed" if self.chance(0.6) else "divorced",
            ss=target * self.uniform(0.95, 1.18),
            interest=self.uniform(50, 400) if self.chance(0.4) else 0.0,
        )
        self.steady_roster(family, [(1, 1, _HEAD)])
        self.wealth(
            family,
            checking_saving=self.uniform(0, 3_000),
            vehicles=self.uniform(0, 4_000) if self.chance(0.4) else 0.0,
        )

    def elder_with_child(self) -> None:
        family = self.family("elder_with_child")
        elder_birth = self.target_year()
        child_birth = int(elder_birth + 28 + self.rng.integers(0, 6))
        self.person(
            family,
            1,
            sex="male",
            birth_year=child_birth,
            marital="married",
            spouse_slot=2,
            labor=self.uniform(25_000, 70_000),
        )
        self.person(
            family,
            2,
            sex="female",
            birth_year=int(child_birth + self.rng.integers(-3, 4)),
            marital="married",
            spouse_slot=1,
            labor=self.uniform(10_000, 40_000) if self.chance(0.6) else 0.0,
        )
        self.person(
            family,
            3,
            sex=self.sex(),
            birth_year=elder_birth,
            marital="widowed" if self.chance(0.5) else "none",
            ss=self.uniform(6_000, 14_000),
            ssi=self.uniform(1_000, 3_000) if self.chance(0.2) else 0.0,
            interest=self.uniform(0, 1_500) if self.chance(0.3) else 0.0,
            pension=self.uniform(1_000, 6_000) if self.chance(0.2) else 0.0,
        )
        self.person(
            family,
            4,
            sex=self.sex(),
            birth_year=int(1995 + self.rng.integers(0, 6)),
            marital="none",
        )
        self.steady_roster(
            family,
            [
                (1, 1, _HEAD),
                (2, 2, _WIFE),
                (3, 3, _PARENT),
                (4, 4, _GRANDCHILD),
            ],
        )
        self.wealth(
            family,
            checking_saving=self.uniform(1_000, 15_000),
            ira_annuity=(
                self.uniform(5_000, 60_000) if self.chance(0.5) else 0.0
            ),
            vehicles=self.uniform(5_000, 25_000),
            unsecured_debt=self.uniform(1_000, 12_000),
            home_equity=self.uniform(20_000, 120_000),
        )

    def couple_with_adult_child(self) -> None:
        family = self.family("couple_with_adult_child")
        head_birth = self.target_year()
        self.person(
            family,
            1,
            sex="male",
            birth_year=head_birth,
            marital="married",
            spouse_slot=2,
            ss=self.uniform(7_000, 14_000),
        )
        self.person(
            family,
            2,
            sex="female",
            birth_year=int(head_birth + self.rng.integers(-2, 4)),
            marital="married",
            spouse_slot=1,
            ss=self.uniform(3_000, 8_000),
        )
        self.person(
            family,
            3,
            sex=self.sex(),
            birth_year=int(head_birth + 30 + self.rng.integers(0, 5)),
            marital="never_married",
            labor=self.uniform(12_000, 40_000),
            interest=self.uniform(0, 500) if self.chance(0.3) else 0.0,
        )
        self.steady_roster(family, [(1, 1, _HEAD), (2, 2, _WIFE), (3, 3, 30)])
        self.wealth(
            family,
            checking_saving=self.uniform(500, 6_000),
            vehicles=self.uniform(2_000, 12_000),
            unsecured_debt=self.uniform(0, 4_000),
            home_equity=self.uniform(0, 90_000),
        )

    def working_couple(self) -> None:
        family = self.family("working_couple")
        owner = self.chance(0.5)
        head_birth = self.target_year()
        self.person(
            family,
            1,
            sex="male",
            birth_year=head_birth,
            marital="married",
            spouse_slot=2,
            labor=self.uniform(20_000, 90_000),
            business_labor=self.uniform(5_000, 40_000) if owner else 0.0,
            business_asset=self.uniform(-15_000, 30_000) if owner else 0.0,
            farm=self.uniform(-5_000, 20_000) if self.chance(0.2) else 0.0,
            rent=self.uniform(-6_000, 12_000) if self.chance(0.4) else 0.0,
            dividends=self.uniform(0, 20_000),
            interest=self.uniform(0, 6_000),
            trusts=self.uniform(0, 5_000) if self.chance(0.2) else 0.0,
            ss=0.0 if self.chance(0.5) else self.uniform(15_000, 25_000),
        )
        family["persons"][-1]["earnings_rows"] = True
        self.person(
            family,
            2,
            sex="female",
            birth_year=int(head_birth + self.rng.integers(-3, 6)),
            marital="married",
            spouse_slot=1,
            labor=self.uniform(10_000, 50_000) if self.chance(0.5) else 0.0,
            business_labor=self.uniform(0, 10_000) if owner else 0.0,
            business_asset=self.uniform(-3_000, 8_000) if owner else 0.0,
            ss=self.uniform(6_000, 14_000) if self.chance(0.5) else 0.0,
        )
        self.steady_roster(family, [(1, 1, _HEAD), (2, 2, _WIFE)])
        self.wealth(
            family,
            farm_business=self.uniform(50_000, 500_000) if owner else 0.0,
            checking_saving=self.uniform(10_000, 80_000),
            stocks=self.uniform(20_000, 400_000),
            ira_annuity=self.uniform(50_000, 600_000),
            vehicles=self.uniform(10_000, 40_000),
            other_real_estate=(
                self.uniform(50_000, 300_000) if self.chance(0.4) else 0.0
            ),
            home_equity=self.uniform(100_000, 500_000),
        )

    def negative_wealth_single(self) -> None:
        family = self.family("negative_wealth_single")
        self.person(
            family,
            1,
            sex=self.sex(),
            birth_year=self.target_year(),
            marital="divorced",
            ss=self.uniform(8_000, 14_000),
        )
        self.steady_roster(family, [(1, 1, _HEAD)])
        self.wealth(
            family,
            checking_saving=self.uniform(0, 1_000),
            vehicles=self.uniform(0, 3_000),
            unsecured_debt=self.uniform(5_000, 40_000),
        )

    def cohabiting_couple(self) -> None:
        family = self.family("cohabiting_couple")
        head_birth = self.target_year()
        self.person(
            family,
            1,
            sex="male",
            birth_year=head_birth,
            marital="divorced",
            ss=self.uniform(9_000, 16_000),
        )
        partner = self.person(
            family,
            2,
            sex="female",
            birth_year=int(head_birth + self.rng.integers(-3, 5)),
            marital="none",
            ss=self.uniform(4_000, 10_000),
            labor=self.uniform(0, 8_000) if self.chance(0.3) else 0.0,
        )
        partner["earnings_rows"] = True
        self.steady_roster(family, [(1, 1, _HEAD), (2, 2, _PARTNER)])
        self.wealth(
            family,
            checking_saving=self.uniform(500, 8_000),
            vehicles=self.uniform(1_000, 10_000),
            home_equity=self.uniform(0, 80_000),
        )

    def separated(self) -> None:
        family = self.family("separated")
        self.person(
            family,
            1,
            sex="female",
            birth_year=self.target_year(),
            marital="separated",
            ss=self.uniform(6_000, 12_000),
            pension=self.uniform(1_000, 5_000) if self.chance(0.5) else 0.0,
        )
        self.steady_roster(family, [(1, 1, _HEAD)])
        self.wealth(
            family,
            checking_saving=self.uniform(200, 6_000),
            vehicles=self.uniform(0, 8_000),
        )

    def unresolved_couple(self) -> None:
        """A head and legal wife (code 20), one of whom has an unresolved
        marital state: the head's history cannot date the marriage, or the
        wife has no marriage-history record."""

        family = self.family("unresolved_couple")
        head_birth = self.target_year()
        # Either the head's history cannot date the marriage, or the wife
        # has no marriage-history record.
        head_unknown = self.chance(0.5)
        self.person(
            family,
            1,
            sex="male",
            birth_year=head_birth,
            marital="unknown" if head_unknown else "married",
            spouse_slot=None if head_unknown else 2,
            ss=self.uniform(9_000, 16_000),
            interest=self.uniform(0, 1_000) if self.chance(0.5) else 0.0,
        )
        self.person(
            family,
            2,
            sex="female",
            birth_year=int(head_birth + self.rng.integers(-2, 4)),
            marital="married" if head_unknown else "none",
            spouse_slot=1 if head_unknown else None,
            ss=self.uniform(4_000, 9_000),
        )
        self.steady_roster(family, [(1, 1, _HEAD), (2, 2, _WIFE)])
        self.wealth(
            family,
            checking_saving=self.uniform(1_000, 15_000),
            vehicles=self.uniform(1_000, 12_000),
            ira_annuity=(
                self.uniform(5_000, 60_000) if self.chance(0.5) else 0.0
            ),
            home_equity=self.uniform(0, 90_000),
        )

    def legal_husband_couple(self) -> None:
        """A female head whose legal husband (code 90) has no
        marriage-history record."""

        family = self.family("legal_husband_couple")
        husband_birth = self.target_year()
        self.person(
            family,
            1,
            sex="female",
            birth_year=int(husband_birth + self.rng.integers(-1, 4)),
            marital="married",
            spouse_slot=2,
            ss=self.uniform(5_000, 11_000),
        )
        self.person(
            family,
            2,
            sex="male",
            birth_year=husband_birth,
            marital="none",
            ss=self.uniform(9_000, 17_000),
        )
        self.steady_roster(family, [(1, 1, _HEAD), (2, 2, _LEGAL_HUSBAND)])
        self.wealth(
            family,
            checking_saving=self.uniform(1_000, 12_000),
            vehicles=self.uniform(1_000, 10_000),
            home_equity=self.uniform(0, 80_000),
        )

    def institution_spouse(self) -> None:
        family = self.family("institution_spouse")
        birth = self.target_year()
        self.person(
            family,
            1,
            sex="male",
            birth_year=birth,
            marital="married",
            spouse_slot=2,
            ss=self.uniform(10_000, 18_000),
        )
        self.person(
            family,
            2,
            sex="female",
            birth_year=int(birth + self.rng.integers(-2, 5)),
            marital="married",
            spouse_slot=1,
            ss=self.uniform(5_000, 11_000),
        )
        start = _first_wave(birth)
        for wave in _WAVES:
            if wave < start:
                family["roster"][wave] = [(1, 1, _HEAD), (2, 2, _WIFE)]
            else:
                # The husband enters an institution; the wife becomes head
                # and his record (relationship to the previous head, 10)
                # stays attached to her family.
                family["roster"][wave] = [
                    (2, 1, _HEAD),
                    (1, _SEQ_INSTITUTION, _HEAD),
                ]
        self.wealth(
            family,
            checking_saving=self.uniform(1_000, 20_000),
            vehicles=self.uniform(0, 10_000),
            home_equity=self.uniform(0, 100_000),
        )

    def exact_age_year(self) -> int:
        """An odd (U0) birth year from 1939, so the member is in a family
        in a wave before the first one at or after age 66."""

        return int(self.rng.choice([1939, 1941, 1943, 1945]))

    def _leaver(self, family_type: str, sequence: int) -> None:
        family = self.family(family_type)
        birth = self.exact_age_year()
        self.person(
            family,
            1,
            sex=self.sex(),
            birth_year=birth,
            marital="widowed",
            ss=self.uniform(8_000, 15_000),
        )
        start = _first_wave(birth)
        for wave in _WAVES:
            if wave < start:
                family["roster"][wave] = [(1, 1, _HEAD)]
            elif wave == start:
                family["roster"][wave] = [(1, sequence, _HEAD)]
            else:
                family["roster"][wave] = []
        if sequence == _SEQ_DIED:
            family["death_year"][1] = start - 1
        self.wealth(family, checking_saving=self.uniform(500, 5_000))

    def mover_out(self) -> None:
        self._leaver("mover_out", _SEQ_MOVED)

    def decedent(self) -> None:
        self._leaver("decedent", _SEQ_DIED)

    def zero_weight(self) -> None:
        family = self.family("zero_weight")
        birth = self.exact_age_year()
        self.person(
            family,
            1,
            sex=self.sex(),
            birth_year=birth,
            marital="never_married",
            ss=self.uniform(8_000, 15_000),
        )
        self.steady_roster(family, [(1, 1, _HEAD)])
        start = _first_wave(birth)
        family["zero_weight"] = {1: start}
        self.wealth(family, checking_saving=self.uniform(500, 5_000))


def _families(rng: np.random.Generator) -> list[dict[str, Any]]:
    builder = _Builder(rng)
    for family_type, count in INVENTED_FAMILY_COUNTS.items():
        make = getattr(builder, family_type)
        for _ in range(count):
            make()
    return builder.families


# =========================================================================
# Frames
# =========================================================================
def _interview(family: Mapping[str, Any], wave: int) -> int:
    return (wave - 2000) * _FAMILY_UNIT_OFFSET + int(family["index"])


def _grow(amount: float, year: int, rate: float = _PRICE_GROWTH) -> float:
    return float(amount) * (1.0 + rate) ** (int(year) - 2004)


def _person_amounts(person: Mapping[str, Any], wave: int) -> dict[str, int]:
    """One person's invented items in ``wave``'s income year (dollars)."""

    year = wave - 1
    age = year - int(person["birth_year"])
    factor = person["noise"][wave]
    out = {}
    for item in _ITEMS:
        amount = person["income"][item]
        if item == "ss" and age < int(person["ss_start_age"]):
            amount = 0.0
        out[item] = int(round(_grow(amount, year) * factor))
    return out


def _marriage_rows(family: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    by_slot = {person["slot"]: person for person in family["persons"]}
    for person in family["persons"]:
        marital = person["marital"]
        if marital == "none":
            continue
        base = {
            "person_id": person["person_id"],
            "sex": person["sex"],
            "birth_year": person["birth_year"],
            "birth_month": pd.NA,
            "marriage_order": pd.NA,
            "spouse_person_id": pd.NA,
            "start_year": pd.NA,
            "start_month": pd.NA,
            "end_year": pd.NA,
            "end_month": pd.NA,
            "separation_year": pd.NA,
            "separation_month": pd.NA,
            "how_ended": "never_married",
            "last_known_status": "never_married",
            "most_recent_report_year": 2023,
            "n_marriages": 0,
            "n_records": 1,
            "is_marriage": False,
        }
        married = {
            "is_marriage": True,
            "marriage_order": 1,
            "n_marriages": 1,
        }
        birth = int(person["birth_year"])
        if marital == "married":
            spouse = by_slot[person["spouse_slot"]]
            base.update(
                married,
                spouse_person_id=spouse["person_id"],
                start_year=max(birth, int(spouse["birth_year"])) + 24,
                how_ended="intact",
                last_known_status="married",
            )
        elif marital == "widowed":
            base.update(
                married,
                spouse_person_id=person["person_id"] + 90_000_000,
                start_year=birth + 23,
                end_year=1990 + int(person["person_id"]) % 13,
                how_ended="widowhood",
                last_known_status="widowed",
            )
        elif marital == "divorced":
            base.update(
                married,
                start_year=birth + 25,
                end_year=birth + 33,
                how_ended="divorce",
                last_known_status="divorced",
            )
        elif marital == "separated":
            base.update(
                married,
                spouse_person_id=person["person_id"] + 80_000_000,
                start_year=birth + 22,
                separation_year=1998,
                how_ended="separated",
                last_known_status="separated",
            )
        elif marital == "unknown":
            # A marriage the history cannot date: the state is "unknown".
            base.update(
                married,
                how_ended="other",
                last_known_status="married",
            )
        rows.append(base)
    return rows


def _typed_marriage_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    for column in (
        "birth_year",
        "birth_month",
        "marriage_order",
        "spouse_person_id",
        "start_year",
        "start_month",
        "end_year",
        "end_month",
        "separation_year",
        "separation_month",
        "most_recent_report_year",
        "n_marriages",
    ):
        frame[column] = frame[column].astype("Int64")
    for column in ("sex", "how_ended", "last_known_status"):
        frame[column] = frame[column].astype("string")
    frame["n_records"] = frame["n_records"].astype("int64")
    frame["is_marriage"] = frame["is_marriage"].astype(bool)
    return frame


def _anchor_frames(
    families: list[dict[str, Any]],
) -> dict[int, pd.DataFrame]:
    out = {}
    for index, wave in enumerate(_WAVES):
        rows = []
        for family in families:
            placed = {
                slot: (sequence, relationship)
                for slot, sequence, relationship in family["roster"][wave]
            }
            for person in family["persons"]:
                slot = person["slot"]
                if slot not in placed:
                    rows.append(
                        {
                            "person_id": person["person_id"],
                            "interview": 0,
                            "sequence": 0,
                            "relationship": 0,
                            "age": 0,
                            "reported_birth_year": pd.NA,
                            "weight": 0.0,
                        }
                    )
                    continue
                sequence, relationship = placed[slot]
                zero_from = family["zero_weight"].get(slot)
                weight = round(family["weight"] * (1.0 + 0.01 * index), 2)
                if zero_from is not None and wave >= zero_from:
                    weight = 0.0
                reported = person["reported_birth_year"]
                rows.append(
                    {
                        "person_id": person["person_id"],
                        "interview": _interview(family, wave),
                        "sequence": sequence,
                        "relationship": relationship,
                        "age": _wave_age(person, wave),
                        "reported_birth_year": (
                            pd.NA if reported is None else int(reported)
                        ),
                        "weight": float(weight),
                    }
                )
        frame = pd.DataFrame(rows)
        for column in ("interview", "sequence", "relationship", "age"):
            frame[column] = frame[column].astype("int64")
        frame["weight"] = frame["weight"].astype("float64")
        frame["reported_birth_year"] = frame["reported_birth_year"].astype(
            "Int64"
        )
        out[wave] = frame
    return out


def _wave_age(person: Mapping[str, Any], wave: int) -> int:
    """The invented age at the ``wave`` interview (spring of ``wave``)."""

    return (
        (wave - 1)
        - int(person["birth_year"])
        + int(person["birthday_before_interview"])
    )


def _in_family(
    family: Mapping[str, Any], wave: int
) -> list[tuple[dict[str, Any], int]]:
    by_slot = {person["slot"]: person for person in family["persons"]}
    return [
        (by_slot[slot], relationship)
        for slot, sequence, relationship in family["roster"][wave]
        if 1 <= sequence <= 20
    ]


def _income_row(family: Mapping[str, Any], wave: int) -> dict[str, Any]:
    """One family's invented income record in the reader's decoded shape."""

    table = family_income.income_variables(wave)
    row: dict[str, Any] = {concept: 0 for concept in table}
    members = _in_family(family, wave)
    head = next(person for person, rel in members if rel == _HEAD)
    wives = [person for person, rel in members if rel in _SPOUSE_CODES]
    wife = wives[0] if wives else None
    ofums = [
        person
        for person, rel in members
        if person is not head and person is not wife
    ]
    year = wave - 1
    for role, person in (("head", head), ("wife", wife)):
        if person is None:
            continue
        a = _person_amounts(person, wave)
        row[f"{role}_labor"] += a["labor"]
        row[f"{role}_business_labor"] += a["business_labor"]
        row[f"{role}_business_asset"] += a["business_asset"]
        for item in ("rent", "dividends", "interest", "trusts"):
            row[f"{role}_{item}"] += a[item]
        row[f"{role}_ss"] += a["ss"]
        row[f"{role}_ssi"] += a["ssi"]
        # The codebooks' farm income is the head's and wife's together.
        row["head_farm"] += a["farm"]
        if role == "head":
            row["head_retirement_pensions"] += a["pension"]
            row["head_va_pension"] += a["va"]
            row["head_other_retirement"] += a["other_retirement"]
            if wave == 2013:
                row["head_annuities"] += a["annuity"]
                row["head_iras"] += a["ira"]
            else:
                # "Head's Income from Annuities and IRAs" (2005-2011).
                row["head_annuities"] += a["annuity"] + a["ira"]
        elif wave == 2013:
            row["wife_retirement_pensions"] += a["pension"] + a["va"]
            row["wife_annuities"] += a["annuity"]
            row["wife_iras"] += a["ira"]
            row["wife_other_retirement"] += a["other_retirement"]
        else:
            row["wife_retirement_annuities"] += (
                a["pension"]
                + a["annuity"]
                + a["va"]
                + a["other_retirement"]
                + a["ira"]
            )
    for person in ofums:
        a = _person_amounts(person, wave)
        row["ofum_labor"] += a["labor"] + a["business_labor"] + a["farm"]
        row["ofum_asset"] += (
            a["business_asset"]
            + a["rent"]
            + a["dividends"]
            + a["interest"]
            + a["trusts"]
        )
        row["ofum_ss"] += a["ss"]
        row["ofum_ssi"] += a["ssi"]
        row["ofum_va_pension"] += a["va"]
        row["ofum_retirement_annuities"] += (
            a["pension"] + a["annuity"] + a["other_retirement"] + a["ira"]
        )
    hw_assets = [
        c for c in family_income.ASSET_INCOME_CONCEPTS if c != "ofum_asset"
    ]
    row["hw_taxable"] = sum(
        row[c] for c in (*family_income.HW_EARNED_CONCEPTS, *hw_assets)
    )
    row["hw_transfer"] = sum(
        row[c] for c in family_income.HW_TRANSFER_COMPONENTS[wave]
    )
    row["ofum_taxable"] = row["ofum_labor"] + row["ofum_asset"]
    row["ofum_transfer"] = sum(
        row[c] for c in family_income.OFUM_TRANSFER_COMPONENTS
    )
    row["total_family_income"] = sum(
        row[c] for c in family_income.FAMILY_INCOME_AGGREGATES
    )
    size = len(members)
    children = sum(
        1 for person in ofums if year - int(person["birth_year"]) < 18
    )
    head_age = _wave_age(head, wave)
    row["interview"] = _interview(family, wave)
    row["fu_size"] = size
    row["n_children"] = children
    row["head_age"] = head_age
    row["head_sex"] = head["sex"]
    row["wife_age"] = None if wife is None else _wave_age(wife, wave)
    row["census_needs_standard"] = invented_needs_standard(
        year, size, children, head_age
    )
    if family["ss_imputed"] and row["head_ss"] > 0:
        row["head_ss_acc"] = 1
    return row


def _income_frame(families: list[dict[str, Any]], wave: int) -> pd.DataFrame:
    rows = [
        _income_row(family, wave)
        for family in families
        if _in_family(family, wave)
    ]
    table = family_income.income_variables(wave)
    frame = pd.DataFrame(rows)[list(table)]
    for concept in table:
        if concept not in ("head_sex", "head_age", "wife_age"):
            frame[concept] = frame[concept].astype("int64")
    frame["head_sex"] = frame["head_sex"].astype("string")
    frame["head_age"] = frame["head_age"].astype("Int64")
    frame["wife_present"] = frame["wife_age"].notna().astype(bool)
    frame["wife_age"] = pd.array(
        [
            pd.NA if pd.isna(value) else int(value)
            for value in frame["wife_age"]
        ],
        dtype="Int64",
    )
    frame.insert(0, "income_year", wave - 1)
    frame.insert(0, "wave", wave)
    return frame.reset_index(drop=True)


def _wealth_concepts(wave: int) -> list[str]:
    layout = 2009 if wave in family_income.WEALTH_SUPPLEMENT_WAVES else wave
    return list(family_income.wealth_variables(layout))


def _wealth_row(family: Mapping[str, Any], wave: int) -> dict[str, Any]:
    growth = (1.0 + _WEALTH_GROWTH) ** (wave - 2005)
    values = {
        key: int(round(value * growth))
        for key, value in family["wealth"].items()
    }
    layout = 2009 if wave in family_income.WEALTH_SUPPLEMENT_WAVES else wave
    row: dict[str, Any] = dict.fromkeys(_wealth_concepts(wave), 0)
    for concept in ("checking_saving", "stocks", "vehicles", "other_assets"):
        row[concept] = values[concept]
    row["ira_annuity"] = values["ira_annuity"]
    if layout == 2013:
        row["farm_business_asset"] = values["farm_business"]
        row["other_real_estate_asset"] = values["other_real_estate"]
    else:
        row["farm_business"] = values["farm_business"]
        row["other_real_estate"] = values["other_real_estate"]
    debt = values["unsecured_debt"]
    if layout == 2011 or layout == 2013:
        card = int(round(0.6 * debt))
        medical = int(round(0.2 * debt))
        row["credit_card_debt"] = card
        row["medical_debt"] = medical
        row["family_loan_debt"] = debt - card - medical
    else:
        row["other_debt"] = debt
    assets = sum(row[c] for c in family_income.WEALTH1_ASSETS[layout])
    debts = sum(row[c] for c in family_income.WEALTH1_DEBTS[layout])
    row["wealth1"] = assets - debts
    row["home_equity"] = values["home_equity"]
    row["wealth2"] = row["wealth1"] + row["home_equity"]
    row["wealth1_acc"] = 1 if family["wealth_imputed"] else 0
    row["interview"] = _interview(family, wave)
    return row


def _wealth_frame(families: list[dict[str, Any]], wave: int) -> pd.DataFrame:
    rows = [
        _wealth_row(family, wave)
        for family in families
        if _in_family(family, wave)
    ]
    frame = pd.DataFrame(rows)[["interview", *_wealth_concepts(wave)]]
    frame = frame.astype("int64")
    frame.insert(0, "wave", wave)
    return frame.reset_index(drop=True)


def _earnings_frame(families: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for family in families:
        for person in family["persons"]:
            if not person["earnings_rows"]:
                continue
            birth = int(person["birth_year"])
            for period in range(1990, 2003, 2):
                rows.append(
                    {
                        "person_id": person["person_id"],
                        "period": period,
                        "earnings": float(20_000 + 500 * (period - 1990)),
                        "role": "head" if person["slot"] == 1 else "spouse",
                        "age": period - birth,
                        "weight": 1.0,
                        "earnings_acc": 0,
                    }
                )
    frame = pd.DataFrame(
        rows,
        columns=[
            "person_id",
            "period",
            "earnings",
            "role",
            "age",
            "weight",
            "earnings_acc",
        ],
    )
    return frame.astype(
        {
            "person_id": "int64",
            "period": "int64",
            "earnings": "float64",
            "age": "int64",
            "weight": "float64",
            "earnings_acc": "int64",
        }
    )


def invented_age67_inputs(
    *,
    seed: int = DEFAULT_SEED,
    supplement_waves_staged: bool = False,
) -> age67.Age67Inputs:
    """INVENTED :class:`~populace_dynamics.cohorts.age67.Age67Inputs`.

    ``supplement_waves_staged`` adds invented wealth for waves 2005 and
    2007 (as if the PSID wealth supplements were staged, in the 2009
    component layout); without it those waves carry the reader's
    refusal, as the real staging does today.
    """

    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("seed must be an integer")
    rng = np.random.default_rng(seed)
    families = _families(rng)
    anchors = _anchor_frames(families)
    persons = [p for family in families for p in family["persons"]]
    design = pd.DataFrame(
        {
            "person_id": [p["person_id"] for p in persons],
            "stratum": [
                family["stratum"]
                for family in families
                for _ in family["persons"]
            ],
            "cluster": [
                family["cluster"]
                for family in families
                for _ in family["persons"]
            ],
        }
    ).astype("int64")
    deaths = []
    for family in families:
        for person in family["persons"]:
            death = family["death_year"].get(person["slot"])
            deaths.append(
                {
                    "person_id": person["person_id"],
                    "sex": person["sex"],
                    "death_status": (
                        "not_deceased" if death is None else "exact"
                    ),
                    "death_year": pd.NA if death is None else int(death),
                }
            )
    death_frame = pd.DataFrame(deaths)
    death_frame["death_year"] = death_frame["death_year"].astype("Int64")
    marriages = [row for family in families for row in _marriage_rows(family)]
    wealth_waves = (
        age67.WAVES if supplement_waves_staged else family_income.WEALTH_WAVES
    )
    refusals = (
        {}
        if supplement_waves_staged
        else {
            wave: (
                "WealthSupplementNotStagedError: INVENTED inputs mirror the "
                f"real staging: the PSID {wave} wealth supplement is not "
                "staged"
            )
            for wave in family_income.WEALTH_SUPPLEMENT_WAVES
        }
    )
    inputs = age67.Age67Inputs(
        anchors=anchors,
        design=design,
        death_records=death_frame,
        marriage_history=_typed_marriage_frame(marriages),
        observed_earnings=_earnings_frame(families),
        family_income={
            wave: _income_frame(families, wave) for wave in age67.WAVES
        },
        family_wealth={
            wave: _wealth_frame(families, wave) for wave in wealth_waves
        },
        wealth_refusals=refusals,
    )
    return dataclasses.replace(
        inputs,
        provenance={
            "kind": age67.INVENTED,
            "data": INVENTED_INPUTS_LABEL,
            "generator": _GENERATOR,
            "seed": int(seed),
            "supplement_waves_staged": bool(supplement_waves_staged),
            "family_counts": dict(INVENTED_FAMILY_COUNTS),
            "input_frames_sha256": age67.input_frames_sha256(inputs),
        },
    )


def invented_frames_sha256(*, seed: int, supplement_waves_staged: bool) -> str:
    """The frame digest this generator produces for ``seed``."""

    return age67.input_frames_sha256(
        invented_age67_inputs(
            seed=seed, supplement_waves_staged=supplement_waves_staged
        )
    )


def _recorded_invented(provenance: Mapping[str, Any]) -> tuple[int, bool]:
    if provenance.get("kind") != age67.INVENTED:
        raise ValueError(
            f"the provenance kind is {provenance.get('kind')!r}, not "
            "invented: only the invented generator's output may run under "
            "the invented label"
        )
    seed = provenance.get("seed")
    staged = provenance.get("supplement_waves_staged")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError(f"an invented input records seed {seed!r}")
    if not isinstance(staged, bool):
        raise ValueError(
            f"an invented input records supplement flag {staged!r}"
        )
    if provenance.get("generator") != _GENERATOR:
        raise ValueError(
            f"generator {provenance.get('generator')!r} is not {_GENERATOR}"
        )
    return seed, staged


def check_invented_inputs(inputs: age67.Age67Inputs) -> dict[str, Any]:
    """Refuse inputs that are not this generator's output for their seed.

    Re-generates the frames from the recorded seed and supplement flag
    and compares their digest with the inputs' own frames.
    """

    seed, staged = _recorded_invented(dict(inputs.provenance or {}))
    expected = invented_frames_sha256(
        seed=seed, supplement_waves_staged=staged
    )
    observed = age67.input_frames_sha256(inputs)
    if observed != expected:
        raise ValueError(
            "the inputs are labelled invented but their frames are not the "
            f"invented generator's for seed {seed} (digest {observed} != "
            f"{expected})"
        )
    return {
        "seed": seed,
        "supplement_waves_staged": staged,
        "input_frames_sha256": observed,
        "regenerated": True,
    }


def _observations_digest(frame: pd.DataFrame) -> str:
    import hashlib

    digest = hashlib.sha256()
    digest.update(frame.to_csv(index=False, lineterminator="\n").encode())
    return digest.hexdigest()


def check_invented_cohort(cohort: age67.Age67Cohort) -> dict[str, Any]:
    """Refuse a cohort that is not the generator's cohort under its spec.

    The cohort's builder-recorded provenance must be ``invented``; the
    generator's inputs for the recorded seed are rebuilt with the
    cohort's spec and the observations compared.
    """

    provenance = dict(cohort.provenance or {})
    seed, staged = _recorded_invented(provenance)
    inputs = invented_age67_inputs(seed=seed, supplement_waves_staged=staged)
    if provenance.get("input_frames_sha256") != age67.input_frames_sha256(
        inputs
    ):
        raise ValueError(
            "the cohort's recorded input digest is not the invented "
            f"generator's for seed {seed}"
        )
    rebuilt = age67.build_age67_cohort(inputs, cohort.spec)
    if _observations_digest(rebuilt.observations) != _observations_digest(
        cohort.observations
    ):
        raise ValueError(
            "the cohort's observations differ from the invented generator's "
            f"cohort for seed {seed}"
        )
    return {"seed": seed, "supplement_waves_staged": staged, "rebuilt": True}
