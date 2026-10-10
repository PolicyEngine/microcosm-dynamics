"""INVENTED U2 inputs, thresholds and fixed-width records (tests only).

INVENTED DATA - NOT A COMPARISON.  Every person, family, amount, weight,
stratum and cluster produced here is invented by a seeded generator.
Nothing is a PSID observation, an SSA or Census statistic, a comparator
value, or a statement about any 1946-55 outcome.  The frames have the
shapes of the U2 readers (:class:`populace_dynamics.uniform_cut_track_u2.
cohort.U2Inputs` over the support waves 2013-2023), so the invented
population runs through the real U2 builder, income rows, income concept
and tabulation without touching PSID.

The family mix is chosen to exercise every U2 path, not to resemble any
population:

* **roles** (section 3): married heads with a code-20 legal spouse
  (including a **male** code-20 spouse in 2015, whose 2015 family unit
  the section 16c B1 exclusion removes, and a 2015 couple with a female
  code-20 spouse, which it keeps); a code-22 cohabiting partner whose
  birth year is inferred from invented earnings; a female head with a
  code-90 uncooperative legal spouse in 2015-2017 (OFUM income role,
  legal-spouse annuity life, resolves the head's unresolved history); a
  head with a code-92 uncooperative partner from 2017 (OFUM, never a
  legal spouse, never resolves); a head whose marriage history cannot be
  dated with a code-20 spouse without a record; a parent living as an
  OFUM (code 50) in an adult child's family with a grandchild;
* **section 16c exclusions** (d1090): code-90 and code-92 members in
  2019-2023 family units, which the B2 exclusion removes whether the
  target is the reference person, the uncooperative spouse or partner,
  or another member (an OFUM sibling), and a code-90 husband who is in an
  institution in 2021 (sequence 51), outside the family unit, so that
  unit stays;
* **plans** (section 3): every U0 birth year at 67; every even birth
  year 1946-1954 at 66 and 68 (every one of row U1's fifteen cells holds
  an observation), 1946 at 66 in the 2013 wave; an even-birth member who
  moves out before the second observation (no weight transfer);
* **dispositions**: an institutionalized member (sequence 51), a
  decedent (81), a zero-weight member, a member of unknown sex, and
  members born 1945 and 1956 (outside the column);
* **income and SSI** (sections 4, 7, 8): existing SSI recipients (one
  above the federal maximum, a stand-in for a state supplement), an SSI
  couple, an OFUM SSI recipient, newly income-eligible singles (row U3),
  near-threshold singles, farm, business and rental losses, head annuity
  and IRA income, and negative WEALTH1;
* **wealth** (section 4): seven asset components in 2013-2017 and eight
  from 2019, each debt once, home equity outside WEALTH1;
* **employer DC** (row U7): a current-job account, a combined plan
  whose current type counts, a DK amount, a combined previous plan left
  to accumulate (and its re-asked account items, a duplicate), account,
  formula and DK plans on the declared account route, an IRA rollover
  and an off-route amount;
* **design** (section 10): strata including the 2017/2019 refresher
  strata 88-94 and a singleton stratum.

The thresholds (:func:`invented_poverty_thresholds`) are INVENTED round
numbers in the Census table shape; the dry run keeps them because the
near-threshold singles are placed against them.  The fixed-width records
(:func:`invented_fixed_width_records`) write the invented family frames
in each wave's registry layout, for the adapters' round trip.

Provenance: the inputs record ``kind="invented"``, the generator, the
seed, the variant and their frame digest, and carry the invented seal
(:attr:`~populace_dynamics.uniform_cut_track_u2.cohort.U2Inputs.
invented_seal`) that only this module sets.  Besides the base
population, the generator makes a fixed set of named variants
(:data:`INVENTED_VARIANTS`), each a deterministic change to a seed's base
population that exercises one refusal or role branch; no public function
here seals frames a caller supplies.  :func:`check_invented_inputs`
re-generates ``(seed, variant)`` and compares, and both the cohort and
the runner call it, so frames sealed any other way (the private
``_sealed``, ``object.__setattr__``) are refused because they do not
regenerate.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.estimates import adjusted_poverty as ap
from populace_dynamics.uniform_cut_track_u2 import cohort, loader, sources

__all__ = [
    "DEFAULT_SEED",
    "FAMILY_COUNTS",
    "FBR_INDIVIDUAL_MONTHLY",
    "INVENTED_INPUTS_LABEL",
    "INVENTED_THRESHOLDS_LABEL",
    "INVENTED_VARIANTS",
    "WEALTH_ASSETS",
    "WEALTH_DEBTS",
    "check_invented_inputs",
    "invented_fixed_width_records",
    "invented_poverty_thresholds",
    "invented_u2_inputs",
    "invented_variant",
    "raw_family_frame",
    "with_code_88_cohabitor",
]

INVENTED_INPUTS_LABEL = (
    "INVENTED DATA - NOT A COMPARISON: synthetic persons and families in "
    "the U2 reader shapes (PSID individual and family files, waves "
    "2013-2023); not PSID observations"
)
INVENTED_THRESHOLDS_LABEL = (
    "INVENTED THRESHOLDS: made-up round numbers in the shape of the Census "
    "poverty-threshold tables, not Census values"
)
DEFAULT_SEED = 20260928
_GENERATOR = (
    "populace_dynamics.uniform_cut_track_u2.invented.invented_u2_inputs"
)
_WAVES = sources.SUPPORT_WAVES
_PERSON_BASE = 700_000
_INTERVIEW_STEP = 1_000

#: Families per invented type.
FAMILY_COUNTS: dict[str, int] = {
    "couple_both_target": 3,
    "widow_ssi_offset": 3,
    "divorced_ssi_above_fbr": 2,
    "never_married_negative_wealth": 2,
    "cohabiting_partner_22": 2,
    "unknown_history_couple": 2,
    "code90_husband": 2,
    "code92_partner": 2,
    "male_code20_2015": 2,
    "parent_ofum": 2,
    "working_couple_losses_dc": 2,
    "ssi_couple": 2,
    "new_enrollment_single": 3,
    "near_threshold_single": 4,
    "ssi_offset_edge": 2,
    "even_birth_1946": 2,
    "missing_second_observation": 2,
    "institution": 1,
    "died": 1,
    "zero_weight": 1,
    "outside_births": 1,
    "sex_unknown": 1,
    "refresher_stratum": 3,
    "separated": 2,
    "even_birth_1954": 2,
    # Section 16c (d1090), appended so every earlier family keeps its id,
    # interview numbers and random draws: a 2015 couple with a female
    # code-20 spouse (B1 keeps it), a 2017 code-92 partner (OFUM in 2017,
    # B2 excludes the 2019 unit), a 2019-2023 code-90 husband with an
    # OFUM sibling (B2 excludes every unit, whoever the target), and a
    # code-90 husband in an institution in 2021 (outside the family unit,
    # so B2 does not exclude it that year).
    "couple_2015": 1,
    "code92_partner_2017": 1,
    "code90_spouse_2019": 1,
    "code90_institution_2021": 1,
}
#: WEALTH1's documented components by concept (section 4; held equal to
#: the wealth registry identities by the tests).
WEALTH_ASSETS: dict[int, tuple[str, ...]] = {
    wave: (
        "farm_business_asset",
        "checking_saving",
        "other_real_estate_asset",
        "stocks",
        "vehicles",
        "other_assets",
        "ira_annuity",
        *(("cd_bonds_treasury",) if wave >= 2019 else ()),
    )
    for wave in _WAVES
}
WEALTH_DEBTS: tuple[str, ...] = (
    "farm_business_debt",
    "other_real_estate_debt",
    "credit_card_debt",
    "student_loan_debt",
    "medical_debt",
    "legal_debt",
    "family_loan_debt",
    "other_debt",
)
#: Field widths of the employer-DC amounts (pension registry: P20 9
#: digits; P49 and P65 8 digits).
DC_AMOUNT_WIDTHS: dict[str, int] = {
    "current": 9,
    "combo": 8,
    "dc": 8,
}
_THRESHOLD_BASE_2012: dict[str, float] = {
    "one_under_65": 13_000.0,
    "one_65_plus": 12_000.0,
    "two_under_65": 16_500.0,
    "two_65_plus": 15_000.0,
    "three": 20_000.0,
    "four": 25_000.0,
    "five": 30_000.0,
    "six": 34_000.0,
    "seven": 39_000.0,
    "eight": 43_000.0,
    "nine_plus": 52_000.0,
}
_THRESHOLD_GROWTH = 0.025
#: The January federal benefit rates (individual, monthly) the U3
#: enrollment cases are placed against: the public values of the committed
#: U2 SSI capture, which a test holds equal.
FBR_INDIVIDUAL_MONTHLY: dict[int, int] = {
    2012: 698,
    2013: 710,
    2014: 721,
    2015: 733,
    2016: 733,
    2017: 735,
    2018: 750,
    2019: 771,
    2020: 783,
    2021: 794,
    2022: 841,
}


# ===========================================================================
# Thresholds
# ===========================================================================
def _threshold(row: str, year: int) -> float:
    value = _THRESHOLD_BASE_2012[row] * (1 + _THRESHOLD_GROWTH) ** (
        year - 2012
    )
    return float(round(value / 10) * 10)


def invented_poverty_thresholds() -> ap.PovertyThresholds:
    """INVENTED thresholds for income years 2012-2022 (Census shape)."""

    years = range(2012, 2023)
    weighted = {
        year: {row: _threshold(row, year) for row in _THRESHOLD_BASE_2012}
        for year in years
    }
    matrix = {
        year: {
            row: {
                children: float(
                    round(_threshold(row, year) * (1 - 0.01 * children) / 10)
                    * 10
                )
                for children in range(0, 9)
            }
            for row in _THRESHOLD_BASE_2012
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
                "populace_dynamics.uniform_cut_track_u2.invented."
                "invented_poverty_thresholds"
            ),
        },
    )


# ===========================================================================
# Families
# ===========================================================================
def _person(
    slot: int,
    sex: str,
    birth: int,
    marital: str,
    *,
    spouse_slot: int | None = None,
    earnings: bool = False,
    reported: bool = True,
    birthday_before_interview: bool | None = None,
) -> dict[str, Any]:
    if birthday_before_interview is None:
        # A person with neither a marriage-history record nor earnings is
        # dated by the seed coordinate, (wave - 1) - age at the
        # interview: an interview after the birthday would place the
        # derived birth a year early, so these persons' birthdays fall
        # after the interview.
        birthday_before_interview = marital != "none" or earnings
    return {
        "slot": slot,
        "sex": sex,
        "birth_year": birth,
        "marital": marital,
        "spouse_slot": spouse_slot,
        "earnings_rows": earnings,
        "reported_birth_year": birth if reported else None,
        "birthday_before_interview": birthday_before_interview,
    }


def _roster(
    placements: Mapping[int, tuple[int, int]],
    overrides: Mapping[int, Mapping[int, tuple[int, int]]] | None = None,
) -> dict[int, list[tuple[int, int, int]]]:
    """``{wave: [(slot, sequence, relationship)]}`` from base placements."""

    out = {}
    for wave in _WAVES:
        wave_map = dict(placements)
        if overrides and wave in overrides:
            wave_map.update(overrides[wave])
        out[wave] = [
            (slot, sequence, relationship)
            for slot, (sequence, relationship) in sorted(wave_map.items())
            if sequence > 0
        ]
    return out


def _family_spec(kind: str, index: int, rng: np.random.Generator) -> dict:
    """One invented family of ``kind`` (index varies birth years)."""

    shift = 2 * (index % 2)  # alternate odd birth years within the cohort
    spec: dict[str, Any] = {
        "kind": kind,
        "income": {},
        "wealth": 60_000,
        "dc": None,
        "children": 0,
        "zero_weight": {},
        "stratum": None,
    }
    if kind == "couple_both_target":
        persons = [
            _person(1, "male", 1949 + shift, "married", spouse_slot=2),
            _person(2, "female", 1951 + shift, "married", spouse_slot=1),
        ]
        roster = _roster({1: (1, 10), 2: (2, 20)})
        spec["income"] = {"head_ss": 19_000, "wife_ss": 12_000}
        spec["wealth"] = 150_000
    elif kind == "widow_ssi_offset":
        persons = [_person(1, "female", 1947 + shift, "widowed")]
        roster = _roster({1: (1, 10)})
        spec["income"] = {"head_ss": 6_000, "head_ssi": 2_400}
        spec["wealth"] = 1_500
    elif kind == "divorced_ssi_above_fbr":
        persons = [_person(1, "male", 1953, "divorced")]
        roster = _roster({1: (1, 10)})
        spec["income"] = {"head_ss": 4_000, "head_ssi": 12_500}
        spec["wealth"] = 800
    elif kind == "never_married_negative_wealth":
        persons = [_person(1, "female", 1955, "never")]
        roster = _roster({1: (1, 10)})
        spec["income"] = {"head_ss": 9_000, "head_labor": 4_000}
        spec["wealth"] = -12_000
    elif kind == "cohabiting_partner_22":
        persons = [
            _person(1, "male", 1951, "never"),
            _person(2, "female", 1950, "none", earnings=True, reported=False),
        ]
        roster = _roster({1: (1, 10), 2: (2, 22)})
        spec["income"] = {"head_ss": 14_000, "wife_ss": 8_000}
        spec["wealth"] = 40_000
    elif kind == "unknown_history_couple":
        persons = [
            _person(1, "male", 1953, "unknown"),
            _person(2, "female", 1956, "none"),
        ]
        roster = _roster({1: (1, 10), 2: (2, 20)})
        spec["income"] = {"head_ss": 17_000, "wife_ss": 6_000}
        spec["wealth"] = 25_000
        # The spouse slot's age is coded 999 (DK; NA): still occupied.
        spec["wife_age_code"] = 999
    elif kind == "code90_husband":
        # Index 0: the code-90 husband is a U1 member (born 1948); index
        # 1: he is born outside the column (1945).
        persons = [
            _person(1, "female", 1947 + shift, "none"),
            _person(2, "male", 1948 if index == 0 else 1945, "none"),
        ]
        roster = _roster({1: (1, 10), 2: (2, 90)})
        spec["income"] = {"head_ss": 11_000, "ofum_ss": 15_000}
        spec["wealth"] = 5_000
    elif kind == "code92_partner":
        persons = [
            _person(1, "male", 1951, "never"),
            _person(2, "female", 1952, "none", earnings=True),
        ]
        roster = _roster(
            {1: (1, 10), 2: (2, 92)},
            {2013: {2: (0, 0)}, 2015: {2: (0, 0)}},
        )
        spec["income"] = {"head_ss": 11_000, "ofum_ss": 7_000}
        spec["wealth"] = 2_000
    elif kind == "male_code20_2015":
        persons = [
            _person(1, "female", 1947, "married", spouse_slot=2),
            _person(2, "male", 1948, "married", spouse_slot=1),
        ]
        roster = _roster({1: (1, 10), 2: (2, 20)})
        spec["income"] = {"head_ss": 10_000, "wife_ss": 16_000}
        spec["wealth"] = 90_000
    elif kind == "parent_ofum":
        persons = [
            _person(1, "female", 1975, "married", spouse_slot=2),
            _person(2, "male", 1974, "married", spouse_slot=1),
            _person(3, "female", 1953, "widowed"),
            _person(4, "male", 2009, "none"),
        ]
        roster = _roster({1: (1, 10), 2: (2, 20), 3: (3, 50), 4: (4, 60)})
        spec["income"] = {
            "head_labor": 38_000,
            "wife_labor": 30_000,
            "ofum_ss": 9_000,
            "ofum_ssi": 1_800,
        }
        spec["children"] = 1
        spec["wealth"] = 30_000
    elif kind == "working_couple_losses_dc":
        persons = [
            _person(1, "male", 1949 + shift, "married", spouse_slot=2),
            _person(2, "female", 1949 + shift, "married", spouse_slot=1),
        ]
        roster = _roster({1: (1, 10), 2: (2, 20)})
        spec["income"] = {
            "head_labor": 55_000,
            "wife_labor": 20_000,
            "head_farm": -6_000,
            "head_business_asset": -2_500,
            "head_rent": -1_200,
            "head_dividends": 3_000,
            "head_interest": 800,
            "head_annuities": 2_000,
            "head_iras": 4_000,
            "head_ss": 8_000,
        }
        spec["wealth"] = 400_000
        spec["dc"] = "rich"
        # A top-coded amount (6-digit item: 999,997), carried as recorded.
        spec["top_code"] = index == 1
    elif kind == "ssi_couple":
        persons = [
            _person(1, "male", 1955, "married", spouse_slot=2),
            _person(2, "female", 1955, "married", spouse_slot=1),
        ]
        roster = _roster({1: (1, 10), 2: (2, 20)})
        spec["income"] = {
            "head_ss": 5_000,
            "wife_ss": 3_000,
            "head_ssi": 3_000,
            "wife_ssi": 2_500,
        }
        spec["wealth"] = 1_000
    elif kind == "new_enrollment_single":
        persons = [_person(1, "female", 1951 + shift, "divorced")]
        roster = _roster({1: (1, 10)})
        # Placed against the federal benefit rate (a public parameter,
        # :data:`FBR_INDIVIDUAL_MONTHLY`): countable income at or above
        # the annual FBR before the cut and below it after.
        spec["new_enrollment"] = True
        spec["income"] = {}
        # Row U3: other welfare (outside countable income) lifts indexes
        # 0 and 2 just above the threshold, so new enrollment matters.
        spec["welfare_lever"] = index != 1
        spec["wealth"] = 3_000
        spec["vehicles"] = 3_000
    elif kind == "near_threshold_single":
        persons = [
            _person(
                1,
                "male" if index % 2 else "female",
                1949 + 2 * (index % 3),
                "widowed",
            )
        ]
        roster = _roster({1: (1, 10)})
        spec["income"] = {"head_ss": 7_000}
        spec["near_threshold"] = 250 + 150 * (index % 3)
        spec["wealth"] = 0
        # Row U7: an employer DC account adds an annuity (index 2); row
        # U5: reported dividends kept under U5 only (index 3).
        spec["dc"] = "single_account" if index == 2 else None
        spec["dividend_lever"] = index == 3
    elif kind == "ssi_offset_edge":
        # Row U2: an SSI recipient just above the threshold whom the SSI
        # offset keeps above it under the cut.
        persons = [_person(1, "female", 1949 + shift, "widowed")]
        roster = _roster({1: (1, 10)})
        spec["income"] = {}
        spec["offset_edge"] = True
        spec["wealth"] = 0
    elif kind == "even_birth_1946":
        persons = [
            _person(1, "male" if index % 2 else "female", 1946, "widowed")
        ]
        roster = _roster({1: (1, 10)})
        spec["income"] = {"head_ss": 15_000}
        spec["wealth"] = 35_000
    elif kind == "even_birth_1954":
        # Row U1's last even birth year: observed at 66 (2021) and 68
        # (2023), a married couple (index 0) and a never-married man.
        if index == 0:
            persons = [
                _person(1, "female", 1954, "married", spouse_slot=2),
                _person(2, "male", 1952, "married", spouse_slot=1),
            ]
            roster = _roster({1: (1, 10), 2: (2, 20)})
            spec["income"] = {"head_ss": 13_000, "wife_ss": 17_000}
        else:
            persons = [_person(1, "male", 1954, "never")]
            roster = _roster({1: (1, 10)})
            spec["income"] = {"head_ss": 11_500}
        spec["wealth"] = 20_000
    elif kind == "missing_second_observation":
        persons = [_person(1, "female", 1948 + 4 * (index % 2), "divorced")]
        birth = persons[0]["birth_year"]
        roster = _roster(
            {1: (1, 10)},
            {wave: {1: (71, 10)} for wave in _WAVES if wave >= birth + 69},
        )
        spec["income"] = {"head_ss": 12_000}
    elif kind == "institution":
        persons = [_person(1, "male", 1949, "widowed")]
        roster = _roster({1: (1, 10)}, {2017: {1: (51, 10)}})
        spec["income"] = {"head_ss": 16_000}
    elif kind == "died":
        persons = [_person(1, "female", 1951, "widowed")]
        roster = _roster(
            {1: (1, 10)},
            {2019: {1: (81, 10)}, 2021: {1: (0, 0)}, 2023: {1: (0, 0)}},
        )
        spec["income"] = {"head_ss": 12_000}
    elif kind == "zero_weight":
        persons = [_person(1, "male", 1953, "divorced")]
        roster = _roster({1: (1, 10)})
        spec["zero_weight"] = {1: 2021}
        spec["income"] = {"head_ss": 13_000}
    elif kind == "outside_births":
        persons = [
            _person(1, "male", 1945, "married", spouse_slot=2),
            _person(2, "female", 1956, "married", spouse_slot=1),
        ]
        roster = _roster({1: (1, 10), 2: (2, 20)})
        spec["income"] = {"head_ss": 20_000, "wife_ss": 9_000}
    elif kind == "sex_unknown":
        persons = [_person(1, "na", 1955, "never")]
        roster = _roster({1: (1, 10)})
        spec["income"] = {"head_ss": 10_000}
    elif kind == "refresher_stratum":
        persons = [_person(1, "female", 1951, "never_imm")]
        roster = _roster({1: (1, 10)}, {2013: {1: (0, 0)}, 2015: {1: (0, 0)}})
        spec["income"] = {"head_ss": 9_500, "head_labor": 3_000}
        spec["stratum"] = (88, 90, 94)[index % 3]
    elif kind == "separated":
        persons = [_person(1, "male", 1947 + shift, "separated")]
        roster = _roster({1: (1, 10)})
        spec["income"] = {"head_ss": 16_500}
        spec["wealth"] = 45_000
    elif kind == "couple_2015":
        persons = [
            _person(1, "male", 1947, "married", spouse_slot=2),
            _person(2, "female", 1948, "married", spouse_slot=1),
        ]
        roster = _roster({1: (1, 10), 2: (2, 20)})
        spec["income"] = {"head_ss": 18_000, "wife_ss": 11_000}
        spec["wealth"] = 70_000
    elif kind == "code92_partner_2017":
        persons = [
            _person(1, "male", 1949, "never"),
            _person(2, "female", 1950, "none", earnings=True),
        ]
        roster = _roster(
            {1: (1, 10), 2: (2, 92)},
            {2013: {2: (0, 0)}, 2015: {2: (0, 0)}},
        )
        spec["income"] = {"head_ss": 12_500, "ofum_ss": 8_000}
        spec["wealth"] = 3_000
    elif kind == "code90_spouse_2019":
        persons = [
            _person(1, "female", 1953, "none"),
            _person(2, "male", 1952, "none"),
            _person(3, "female", 1955, "never"),
        ]
        roster = _roster({1: (1, 10), 2: (2, 90), 3: (3, 40)})
        spec["income"] = {"head_ss": 10_500, "ofum_ss": 14_000}
        spec["wealth"] = 8_000
    elif kind == "code90_institution_2021":
        persons = [
            _person(1, "female", 1953, "none"),
            _person(2, "male", 1950, "none"),
        ]
        roster = _roster({1: (1, 10), 2: (2, 90)}, {2021: {2: (51, 90)}})
        spec["income"] = {"head_ss": 9_800}
        spec["wealth"] = 4_000
    else:  # pragma: no cover - every kind is listed in FAMILY_COUNTS
        raise ValueError(kind)
    for person in persons:
        if person["marital"] == "never_imm":
            person["marital"] = "never"
    spec["persons"] = persons
    spec["roster"] = roster
    spec["weight"] = float(round(rng.uniform(800, 4_000), 2))
    spec["jitter"] = int(rng.integers(0, 400))
    return spec


def _families(rng: np.random.Generator) -> list[dict[str, Any]]:
    families = []
    strata = [1, 2, 3, 33, 34, 57, 60]
    for kind, count in FAMILY_COUNTS.items():
        for index in range(count):
            spec = _family_spec(kind, index, rng)
            fid = len(families)
            spec["fid"] = fid
            if spec["stratum"] is None:
                spec["stratum"] = strata[fid % len(strata)]
            # Stratum 94 holds one cluster only (a singleton stratum).
            spec["cluster"] = 1 if spec["stratum"] == 94 else 1 + fid % 2
            for person in spec["persons"]:
                person["person_id"] = _PERSON_BASE + 10 * fid + person["slot"]
            families.append(spec)
    return families


def _interview(family: Mapping[str, Any], wave: int) -> int:
    return _INTERVIEW_STEP * (_WAVES.index(wave) + 1) + family["fid"] + 1


def _wave_age(person: Mapping[str, Any], wave: int) -> int:
    return (
        (wave - 1)
        - int(person["birth_year"])
        + int(person["birthday_before_interview"])
    )


def _in_family(
    family: Mapping[str, Any], wave: int
) -> list[tuple[dict[str, Any], int]]:
    by_slot = {p["slot"]: p for p in family["persons"]}
    return [
        (by_slot[slot], relationship)
        for slot, sequence, relationship in family["roster"][wave]
        if 1 <= sequence <= 20
    ]


def _anchor_frames(families: list[dict]) -> dict[int, pd.DataFrame]:
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
                weight = round(family["weight"] * (1 + 0.01 * index), 2)
                zero_from = family["zero_weight"].get(slot)
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


def _marriage_rows(family: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    by_slot = {p["slot"]: p for p in family["persons"]}
    for person in family["persons"]:
        marital = person["marital"]
        if marital == "none":
            continue
        base = {
            "person_id": person["person_id"],
            "sex": person["sex"] if person["sex"] != "na" else "male",
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
        married = {"is_marriage": True, "marriage_order": 1, "n_marriages": 1}
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
                end_year=2000 + int(person["person_id"]) % 11,
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
                separation_year=2005,
                how_ended="separated",
                last_known_status="separated",
            )
        elif marital == "unknown":
            base.update(
                married, how_ended="other", last_known_status="married"
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


def _earnings_frame(families: list[dict]) -> pd.DataFrame:
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
                        "earnings": float(18_000 + 400 * (period - 1990)),
                        "role": "spouse",
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


def _grow(amount: float, wave: int) -> int:
    return int(round(amount * (1.02 ** (wave - 2013))))


def _income_raw(family: Mapping[str, Any], wave: int) -> dict[str, int]:
    """One family's invented income fields (raw codes, whole dollars)."""

    members = _in_family(family, wave)
    row = {concept: 0 for concept in sources.INCOME_CONCEPTS}
    row["interview"] = _interview(family, wave)
    row["fu_size"] = max(1, len(members))
    row["n_children"] = int(family["children"])
    slot = [p for p, rel in members if rel in (20, 22)]
    row["wife_age"] = (
        (family.get("wife_age_code") or _wave_age(slot[0], wave))
        if slot
        else 0
    )
    growth = {
        key: _grow(value, wave) for key, value in family["income"].items()
    }
    jitter = family["jitter"]
    for key, value in growth.items():
        row[key] = value + (jitter if key.endswith("_ss") else 0)
    if "near_threshold" in family:
        threshold = _threshold("one_65_plus", wave - 1)
        row["head_ss"] = int(threshold + family["near_threshold"])
    if family.get("new_enrollment"):
        # Social Security S with S - 240 >= F and 0.87 S - 240 < F.
        annual = 12 * FBR_INDIVIDUAL_MONTHLY[wave - 1]
        row["head_ss"] = int(round(1.04 * (annual + 240)))
    if family.get("top_code"):
        row["head_dividends"] = 999_997
    threshold = _threshold("one_65_plus", wave - 1)
    if family.get("offset_edge"):
        row["head_ss"] = int(threshold - 1_000)
        row["head_ssi"] = 1_300
    if family.get("dividend_lever"):
        row["head_ss"] = int(threshold - 1_500)
        row["head_dividends"] = 2_000
    if family.get("welfare_lever"):
        row["head_other_welfare"] = int(threshold + 600 - row["head_ss"])
    hw_earned = sum(
        row[c]
        for c in (
            "head_labor",
            "wife_labor",
            "head_farm",
            "head_business_labor",
            "wife_business_labor",
        )
    )
    hw_assets = sum(
        row[c]
        for c in (
            "head_rent",
            "head_dividends",
            "head_interest",
            "head_trusts",
            "head_business_asset",
            "wife_rent",
            "wife_dividends",
            "wife_interest",
            "wife_trusts",
            "wife_business_asset",
        )
    )
    row["hw_taxable"] = hw_earned + hw_assets
    row["hw_transfer"] = sum(
        row[c]
        for c in (
            "head_tanf",
            "wife_tanf",
            "head_ssi",
            "wife_ssi",
            "head_other_welfare",
            "wife_other_welfare",
            "head_annuities",
            "head_iras",
        )
    )
    row["ofum_taxable"] = row["ofum_asset"]
    row["ofum_transfer"] = row["ofum_ssi"]
    row["total_family_income"] = sum(
        row[c]
        for c in (
            "hw_taxable",
            "hw_transfer",
            "ofum_taxable",
            "ofum_transfer",
            "head_ss",
            "wife_ss",
            "ofum_ss",
        )
    )
    row["census_needs_standard"] = int(
        9_000 + 3_500 * row["fu_size"] + 20 * (wave - 2013)
    )
    for concept in sources.INCOME_CONCEPTS:
        if concept.endswith("_acc"):
            row[concept] = (
                1
                if row[concept.removesuffix("_acc")]
                and (family["fid"] % 5 == 0)
                else 0
            )
    return row


def _income_frame(families: list[dict], wave: int) -> pd.DataFrame:
    rows = [
        _income_raw(family, wave)
        for family in families
        if _in_family(family, wave)
    ]
    raw = pd.DataFrame(rows, columns=list(sources.INCOME_CONCEPTS)).astype(
        "int64"
    )
    return sources.decode_income(raw)


def _wealth_raw(family: Mapping[str, Any], wave: int) -> dict[str, int]:
    total = _grow(float(family["wealth"]), wave)
    assets = {name: 0 for name in WEALTH_ASSETS[wave]}
    debts = {name: 0 for name in WEALTH_DEBTS}
    vehicles = int(family.get("vehicles", min(max(total // 10, 0), 8_000)))
    assets["vehicles"] = vehicles
    if total >= 0:
        remainder = total - vehicles
        if remainder < 0:
            debts["credit_card_debt"] = -remainder
        else:
            savings = remainder // 3
            assets["checking_saving"] = savings
            if wave >= 2019:
                assets["cd_bonds_treasury"] = savings // 2
                savings -= savings // 2
                assets["checking_saving"] = savings
            assets["ira_annuity"] = remainder // 3
            assets["stocks"] = remainder - 2 * (remainder // 3)
    else:
        debts["medical_debt"] = -total + vehicles
    if family["kind"] == "working_couple_losses_dc":
        assets["farm_business_asset"] = 50_000
        debts["farm_business_debt"] = 20_000
        assets["other_real_estate_asset"] = 30_000
        debts["other_real_estate_debt"] = 10_000
        assets["stocks"] -= 50_000
    row = {"interview": _interview(family, wave), **assets, **debts}
    row["wealth1"] = sum(assets.values()) - sum(debts.values())
    row["wealth1_acc"] = 1 if family["fid"] % 4 == 0 else 0
    row["home_equity"] = (
        80_000 if family["kind"] != "near_threshold_single" else 0
    )
    return row


def _wealth_frame(families: list[dict], wave: int) -> pd.DataFrame:
    rows = [
        _wealth_raw(family, wave)
        for family in families
        if _in_family(family, wave)
    ]
    columns = [
        "interview",
        "wealth1",
        "wealth1_acc",
        "home_equity",
        *WEALTH_ASSETS[wave],
        *WEALTH_DEBTS,
    ]
    return pd.DataFrame(rows, columns=columns).astype("int64")


def _dc_raw(family: Mapping[str, Any], wave: int) -> dict[str, int]:
    row: dict[str, int] = {"interview": _interview(family, wave)}
    for person in ("head", "wife"):
        row[f"{person}_current_type"] = 0
        row[f"{person}_current_amount"] = 0
        for plan in (1, 2):
            for item in (
                "type",
                "combo_disposition",
                "combo_amount",
                "dc_disposition",
                "dc_amount",
            ):
                row[f"{person}_prev{plan}_{item}"] = 0
    if family["dc"] == "single_account":
        row.update({"head_current_type": 5, "head_current_amount": 60_000})
    if family["dc"] == "rich":
        dk8 = 10 ** DC_AMOUNT_WIDTHS["combo"] - 2
        dk9 = 10 ** DC_AMOUNT_WIDTHS["current"] - 2
        row.update(
            {
                # Current job: an account plan and a combined plan (DK).
                "head_current_type": 5,
                "head_current_amount": 30_000,
                "wife_current_type": 7,
                "wife_current_amount": dk9,
                # A combined previous plan left to accumulate, and its
                # re-asked account items (a duplicate, excluded).
                "head_prev1_type": 7,
                "head_prev1_combo_disposition": 3,
                "head_prev1_combo_amount": 9_000,
                "head_prev1_dc_disposition": 3,
                "head_prev1_dc_amount": 9_000,
                # A formula plan's account items (declared route).
                "head_prev2_type": 1,
                "head_prev2_dc_disposition": 3,
                "head_prev2_dc_amount": 15_000,
                # A DK-type plan left to accumulate, and an account plan
                # rolled over into an IRA (excluded).
                "wife_prev1_type": 8,
                "wife_prev1_dc_disposition": 3,
                "wife_prev1_dc_amount": 12_000,
                "wife_prev2_type": 5,
                "wife_prev2_dc_disposition": 2,
                "wife_prev2_dc_amount": 35_000,
            }
        )
        if wave == 2015:
            # A top-coded current-job amount, counted as recorded.
            row["head_current_amount"] = 10 ** DC_AMOUNT_WIDTHS["current"] - 3
        if wave >= 2019:
            # An off-route amount: a formula-only current plan.
            row["wife_current_type"] = 1
            row["wife_current_amount"] = 4_000
            # A DK amount on the route (counted as zero, unreported).
            row["wife_prev1_dc_amount"] = dk8
    return row


def _dc_frame(families: list[dict], wave: int) -> pd.DataFrame:
    rows = [
        _dc_raw(family, wave)
        for family in families
        if _in_family(family, wave)
    ]
    raw = pd.DataFrame(rows).astype("int64")
    widths = {
        concept: DC_AMOUNT_WIDTHS[
            (
                "current"
                if "current" in concept
                else ("combo" if "combo" in concept else "dc")
            )
        ]
        for concept in raw.columns
        if concept.endswith("_amount")
    }
    route = sources.DcRoute(
        wave,
        sources.DECLARED_DC_ROUTE_TYPES["current_account"],
        sources.DECLARED_DC_ROUTE_TYPES["previous_both"],
        sources.DECLARED_DC_ROUTE_TYPES["previous_account_items"],
        3,
        2,
        "section_15_declared_route_invented_only",
    )
    return sources.employer_dc_balances(raw, route, widths)


def _base_frames(seed: int) -> cohort.U2Inputs:
    """The unsealed base population of ``seed``."""

    rng = np.random.default_rng(seed)
    families = _families(rng)
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
    person_frame = pd.DataFrame(
        {
            "person_id": [p["person_id"] for p in persons],
            "sex": [p["sex"] for p in persons],
        }
    ).astype({"person_id": "int64", "sex": "string"})
    marriages = [row for family in families for row in _marriage_rows(family)]
    return cohort.U2Inputs(
        anchors=_anchor_frames(families),
        design=design,
        persons=person_frame,
        marriage_history=_typed_marriage_frame(marriages),
        observed_earnings=_earnings_frame(families),
        family_income={wave: _income_frame(families, wave) for wave in _WAVES},
        family_wealth={wave: _wealth_frame(families, wave) for wave in _WAVES},
        employer_dc={wave: _dc_frame(families, wave) for wave in _WAVES},
    )


def _sealed(
    inputs: cohort.U2Inputs, *, seed: int, variant: str | None
) -> cohort.U2Inputs:
    """``inputs`` recorded and sealed as this generator's output."""

    digest = cohort.input_frames_sha256(inputs)
    provenance: dict[str, Any] = {
        "kind": cohort.INVENTED,
        "data": INVENTED_INPUTS_LABEL,
        "generator": _GENERATOR,
        "seed": int(seed),
        "variant": variant,
        "family_counts": dict(FAMILY_COUNTS),
        "input_frames_sha256": digest,
    }
    if variant is not None:
        provenance["variant_note"] = _VARIANT_NOTES[variant]
    out = dataclasses.replace(inputs, provenance=provenance)
    object.__setattr__(
        out,
        "invented_seal",
        MappingProxyType(
            {
                "generator": _GENERATOR,
                "seed": int(seed),
                "variant": variant,
                "input_frames_sha256": digest,
            }
        ),
    )
    return out


def _check_seed(seed: Any) -> int:
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("seed must be an integer")
    return seed


def _check_sealed(inputs: cohort.U2Inputs) -> dict[str, Any]:
    """The seal of ``inputs``; refuse unsealed or changed frames."""

    provenance = dict(inputs.provenance or {})
    seal = inputs.invented_seal
    if provenance.get("kind") != cohort.INVENTED or seal is None:
        raise ValueError(
            "the inputs were not sealed by the U2 invented generator"
        )
    if dict(seal).get("input_frames_sha256") != (
        cohort.input_frames_sha256(inputs)
    ):
        raise ValueError("the invented frames changed after sealing")
    return dict(seal)


def invented_u2_inputs(
    *, seed: int = DEFAULT_SEED, variant: str | None = None
) -> cohort.U2Inputs:
    """INVENTED :class:`~populace_dynamics.uniform_cut_track_u2.cohort.
    U2Inputs` for the six support waves: the base population of ``seed``,
    or its named ``variant`` (:data:`INVENTED_VARIANTS`)."""

    seed = _check_seed(seed)
    if variant is not None and variant not in INVENTED_VARIANTS:
        raise ValueError(
            f"unknown invented variant {variant!r}; the generator makes "
            f"{INVENTED_VARIANTS}"
        )
    base = _sealed(_base_frames(seed), seed=seed, variant=None)
    return base if variant is None else invented_variant(base, variant)


def invented_variant(base: cohort.U2Inputs, variant: str) -> cohort.U2Inputs:
    """The named ``variant`` of a sealed base population.

    Equal to ``invented_u2_inputs(seed=<base seed>, variant=variant)``;
    it reuses ``base`` instead of regenerating it.
    """

    if variant not in INVENTED_VARIANTS:
        raise ValueError(
            f"unknown invented variant {variant!r}; the generator makes "
            f"{INVENTED_VARIANTS}"
        )
    seal = _check_sealed(base)
    if seal.get("variant") is not None:
        raise ValueError("a variant is made from the base population only")
    changed = _VARIANT_BUILDERS[variant](base)
    return _sealed(changed, seed=seal["seed"], variant=variant)


def check_invented_inputs(inputs: cohort.U2Inputs) -> dict[str, Any]:
    """Refuse inputs that are not this generator's output for their seed
    and variant (the inputs are regenerated and their digests compared)."""

    provenance = dict(inputs.provenance or {})
    if provenance.get("kind") != cohort.INVENTED:
        raise ValueError(
            f"provenance kind {provenance.get('kind')!r} is not invented"
        )
    if provenance.get("generator") != _GENERATOR:
        raise ValueError("the inputs were not made by the U2 generator")
    seed = provenance.get("seed")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError(f"an invented input records seed {seed!r}")
    variant = provenance.get("variant")
    if variant is not None and variant not in INVENTED_VARIANTS:
        raise ValueError(f"an invented input records variant {variant!r}")
    _check_sealed(inputs)
    expected = cohort.input_frames_sha256(
        invented_u2_inputs(seed=seed, variant=variant)
    )
    observed = cohort.input_frames_sha256(inputs)
    if observed != expected:
        raise ValueError(
            "the inputs are labelled invented but their frames are not the "
            f"U2 generator's for seed {seed} and variant {variant!r}"
        )
    return {
        "seed": seed,
        "variant": variant,
        "input_frames_sha256": observed,
        "regenerated": True,
    }


def with_code_88_cohabitor(inputs: cohort.U2Inputs) -> cohort.U2Inputs:
    """The invented inputs plus a code-88 first-year cohabitor (refusal).

    The ``code_88_first_year_cohabitor`` variant of ``inputs``' seed.
    """

    return invented_variant(inputs, "code_88_first_year_cohabitor")


# ===========================================================================
# Named variants (each a deterministic change to a sealed base)
# ===========================================================================
def _declared_u0(base: cohort.U2Inputs) -> pd.DataFrame:
    """U0's observations of the base under the declared role rules."""

    return cohort.build_u2_cohort(
        base, role_context=sources.RoleContext.declared()
    ).observations


def _added_person(
    base: cohort.U2Inputs,
    person_id: int,
    *,
    wave: int,
    interview: int,
    sequence: int,
    relationship: int,
    age: int,
    weight: float,
    sex: str,
) -> cohort.U2Inputs:
    """``base`` with one person present in ``wave`` only."""

    anchors = {}
    for w, frame in base.anchors.items():
        present = w == wave
        row = {
            "person_id": person_id,
            "interview": interview if present else 0,
            "sequence": sequence if present else 0,
            "relationship": relationship if present else 0,
            "age": age if present else 0,
            "reported_birth_year": pd.NA,
            "weight": weight if present else 0.0,
        }
        anchors[w] = pd.concat(
            [frame, pd.DataFrame([row])], ignore_index=True
        ).astype(frame.dtypes.to_dict())
    design = pd.concat(
        [
            base.design,
            pd.DataFrame(
                [{"person_id": person_id, "stratum": 1, "cluster": 1}]
            ),
        ],
        ignore_index=True,
    ).astype("int64")
    persons = pd.concat(
        [base.persons, pd.DataFrame([{"person_id": person_id, "sex": sex}])],
        ignore_index=True,
    ).astype({"person_id": "int64", "sex": "string"})
    return dataclasses.replace(
        base, anchors=anchors, design=design, persons=persons
    )


def _code_88_first_year_cohabitor(base: cohort.U2Inputs) -> cohort.U2Inputs:
    target = base.family_income[2019]["interview"].iloc[0]
    return _added_person(
        base,
        _PERSON_BASE - 1,
        wave=2019,
        interview=int(target),
        sequence=2,
        relationship=88,
        age=60,
        weight=500.0,
        sex="male",
    )


def _missing_family_record_2019(base: cohort.U2Inputs) -> cohort.U2Inputs:
    return dataclasses.replace(
        base,
        family_income={
            **base.family_income,
            2019: base.family_income[2019].iloc[1:],
        },
    )


def _zero_weight_legal_spouse_2019(base: cohort.U2Inputs) -> cohort.U2Inputs:
    anchor = base.anchors[2019]
    in_family = anchor[anchor["sequence"].between(1, 20)]
    for _, rows in in_family.groupby("interview"):
        codes = set(rows["relationship"])
        if {10, 20} <= codes:
            spouse = int(
                rows.loc[rows["relationship"].eq(20), "person_id"].iloc[0]
            )
            break
    else:  # pragma: no cover - the base population holds such a family
        raise AssertionError("no 2019 family with a code-20 spouse")
    anchors = {
        wave: frame.assign(
            weight=frame["weight"].where(frame["person_id"] != spouse, 0.0)
        )
        for wave, frame in base.anchors.items()
    }
    return dataclasses.replace(base, anchors=anchors)


def _ambiguous_legal_spouse(base: cohort.U2Inputs) -> cohort.U2Inputs:
    obs = _declared_u0(base)
    target = obs[
        obs["marital_resolution"].eq(
            "relationship_code_head_with_legal_spouse"
        )
        & obs["fu_head_spouse_relationship"].eq(20)
    ].iloc[0]
    return _added_person(
        base,
        _PERSON_BASE - 2,
        wave=int(target["wave"]),
        interview=int(target["interview"]),
        sequence=5,
        relationship=20,
        age=60,
        weight=100.0,
        sex="female",
    )


def _spouse_slot_disagreement_2019(base: cohort.U2Inputs) -> cohort.U2Inputs:
    obs = _declared_u0(base)
    single = obs[obs["wave"].eq(2019) & ~obs["spouse_slot_occupied_roster"]][
        "interview"
    ].iloc[0]
    income = base.family_income[2019].copy()
    income.loc[income["interview"].eq(single), "wife_present"] = True
    return dataclasses.replace(
        base, family_income={**base.family_income, 2019: income}
    )


def _missing_head(base: cohort.U2Inputs) -> cohort.U2Inputs:
    obs = _declared_u0(base)
    target = obs[obs["relationship"].eq(50)].iloc[0]
    wave, interview = int(target["wave"]), int(target["interview"])
    frame = base.anchors[wave].copy()
    head = frame["interview"].eq(interview) & frame["relationship"].eq(10)
    frame.loc[head, "relationship"] = 30
    return dataclasses.replace(base, anchors={**base.anchors, wave: frame})


def _duplicate_family_record_2019(base: cohort.U2Inputs) -> cohort.U2Inputs:
    income = base.family_income[2019]
    return dataclasses.replace(
        base,
        family_income={
            **base.family_income,
            2019: pd.concat([income, income.iloc[[0]]], ignore_index=True),
        },
    )


def _duplicate_person_record_2019(base: cohort.U2Inputs) -> cohort.U2Inputs:
    obs = _declared_u0(base)
    person = int(obs[obs["wave"].eq(2019)]["person_id"].iloc[0])
    frame = base.anchors[2019]
    repeated = pd.concat(
        [frame, frame[frame["person_id"].eq(person)]], ignore_index=True
    ).astype(frame.dtypes.to_dict())
    return dataclasses.replace(base, anchors={**base.anchors, 2019: repeated})


# Appended in order, so every earlier variant is unchanged.
_VARIANT_BUILDERS = {
    "code_88_first_year_cohabitor": _code_88_first_year_cohabitor,
    "missing_family_record_2019": _missing_family_record_2019,
    "zero_weight_legal_spouse_2019": _zero_weight_legal_spouse_2019,
    "ambiguous_legal_spouse": _ambiguous_legal_spouse,
    "spouse_slot_disagreement_2019": _spouse_slot_disagreement_2019,
    "missing_head": _missing_head,
    "duplicate_family_record_2019": _duplicate_family_record_2019,
    "duplicate_person_record_2019": _duplicate_person_record_2019,
}
_VARIANT_NOTES: dict[str, str] = {
    "code_88_first_year_cohabitor": (
        "a code-88 first-year cohabitor joins the first 2019 family; "
        "section 3 declares no substantive rule for code 88, so every "
        "role context refuses (refusal case)"
    ),
    "missing_family_record_2019": (
        "the first 2019 family-file income record is dropped; an "
        "observation without a family record refuses (failed join)"
    ),
    "zero_weight_legal_spouse_2019": (
        "the code-20 spouse of the first 2019 family with a head and a "
        "code-20 spouse has zero weight in every wave: outside the "
        "universe, still an annuity life with a derived birth year"
    ),
    "ambiguous_legal_spouse": (
        "a second code-20 person joins U0's first family whose head's "
        "undated history the code-20 spouse resolves: the pairing is "
        "ambiguous and the head stays unresolved (counted); the spouse "
        "income slot then has no unique occupant to match the family "
        "file's slot flag, so the cohort's income rows refuse"
    ),
    "spouse_slot_disagreement_2019": (
        "the family file of U0's first 2019 observation without a "
        "spouse-slot occupant reports a spouse: the slot flag and the "
        "roster disagree (refusal case)"
    ),
    "missing_head": (
        "the head of U0's first code-50 observation's family is recoded "
        "30: no head, so the head's annuity life is missing (refusal "
        "case)"
    ),
    "duplicate_family_record_2019": (
        "the first 2019 family-file income record appears twice: a "
        "repeated interview number refuses (duplicate identifier, section "
        "14)"
    ),
    "duplicate_person_record_2019": (
        "the 2019 anchor record of U0's first 2019 observation appears "
        "twice: a repeated person identifier refuses (duplicate "
        "identifier, section 14)"
    ),
}
#: The generator's named variants (see :data:`_VARIANT_NOTES`).
INVENTED_VARIANTS: tuple[str, ...] = tuple(_VARIANT_BUILDERS)


def invented_fixed_width_records(
    inputs: cohort.U2Inputs, wave: int, gate: sources.SourceGate
) -> dict[str, Any]:
    """The invented family frames of ``wave`` as fixed-width records.

    One record per family in the wave's family-file layout (income,
    wealth and employer-DC fields; :func:`family_record_specs`), every
    unmapped column :data:`~populace_dynamics.uniform_cut_track_u2.
    sources.INVENTED_RECORD_FILLER`.  ``gate`` supplies the specs: the
    declared gate for invented records, which records what the registry
    gate would refuse.  INVENTED DATA - NOT A COMPARISON.
    """

    if dict(inputs.provenance).get("kind") != cohort.INVENTED:
        raise ValueError("fixed-width records are written for invented data")
    _check_sealed(inputs)
    specs = loader.family_record_specs(wave, gate)
    raw = raw_family_frame(inputs, wave)
    return {
        "specs": specs,
        "lines": sources.encode_fixed_width(
            raw[[spec.concept for spec in specs]],
            specs,
            filler=sources.INVENTED_RECORD_FILLER,
        ),
        "raw": raw,
    }


def raw_family_frame(inputs: cohort.U2Inputs, wave: int) -> pd.DataFrame:
    """The invented family frames of ``wave`` as raw codes (one row per
    family): income with the spouse-slot age re-encoded (0 absent, 999
    DK/NA), wealth, and the employer-DC items without derived columns."""

    income = inputs.family_income[wave].drop(columns=["wife_present"]).copy()
    present = inputs.family_income[wave]["wife_present"].astype(bool)
    age = income["wife_age"]
    income["wife_age"] = (
        age.fillna(0).astype("int64").where(~(present & age.isna()), 999)
    )
    dc = inputs.employer_dc[wave].drop(
        columns=list(sources.DC_BALANCE_COLUMNS)
    )
    return (
        income.merge(inputs.family_wealth[wave], on="interview", how="inner")
        .merge(dc, on="interview", how="inner")
        .astype("int64")
    )
