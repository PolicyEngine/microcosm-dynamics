"""INVENTED cohort inputs in the A3 reader shapes (dry run and tests only).

Every person, family, date, earnings amount, Social Security amount and
weight produced here is INVENTED by a seeded generator.  Nothing is a PSID
observation, an SSA statistic or a comparator value.  The frames have the
shapes of the A3 readers (:class:`populace_dynamics.cohorts.psid2010.
Psid2010Inputs`) so the invented population runs through the real A3
builder, and so through the whole Track A pipeline, without touching PSID.

The family mix is chosen to exercise every Track A path: retired-worker,
disabled-worker and survivor openers (censored and bracketed first
receipt), a spouse under 62 beside a retired head, widow(er)s whose late
spouse is outside the cohort, disabled workers aged 30-41 in 2010 (the
50-61 group in 2030), late claimers aged 62-69 who have not claimed, and
working couples and singles.  Its composition is not meant to resemble
any real population.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.cohorts import psid2010 as cohort
from populace_dynamics.data import social_security_income as ssi

__all__ = [
    "INVENTED_FAMILY_COUNTS",
    "INVENTED_INPUTS_LABEL",
    "InventedFamily",
    "invented_claiming_pmf",
    "invented_psid2010_inputs",
]

INVENTED_INPUTS_LABEL = (
    "INVENTED DATA: synthetic persons in the PSID 2010 cohort reader "
    "shapes; not PSID observations"
)

#: Families per invented type (250 persons in total).
INVENTED_FAMILY_COUNTS: dict[str, int] = {
    "retired_couple": 32,
    "retired_single": 12,
    "aged_survivor": 14,
    "young_survivor": 6,
    "widowed_nonrecipient": 6,
    "di_single": 14,
    "di_couple": 8,
    "working_couple": 36,
    "working_single": 20,
    "late_claimer": 10,
    "near_retirement_couple": 8,
}

_START = cohort.START_YEAR
_ANCHOR = cohort.ANCHOR_WAVE


@dataclass(frozen=True)
class InventedFamily:
    """One invented family: its type and its members' invented facts."""

    family_type: str
    interview: int
    members: tuple[dict[str, Any], ...]
    late_spouse: dict[str, Any] | None = None


def invented_claiming_pmf() -> dict[tuple[str, int], dict[int, float]]:
    """An INVENTED claim-age PMF for 1998-2008 (not SSA Table 6.B5.1)."""

    shape = {62: 0.4, 63: 0.08, 64: 0.07, 65: 0.2, 66: 0.15, 67: 0.04}
    shape.update({68: 0.02, 69: 0.02, 70: 0.02})
    return {
        (sex, year): dict(shape)
        for sex in ("female", "male")
        for year in range(1998, 2009)
    }


def _wage_index(year: int) -> float:
    """INVENTED nominal wage index: 4.5 percent growth from 1968."""

    return 5_900.0 * 1.045 ** (year - 1968)


def _person(
    rng: np.random.Generator,
    *,
    person_id: int,
    sex: str,
    age: int,
    relationship: int,
    sequence: int,
    weight: float,
    **facts: Any,
) -> dict[str, Any]:
    return {
        "person_id": person_id,
        "sex": sex,
        "birth_year": _START - age,
        "relationship": relationship,
        "sequence": sequence,
        "weight": weight,
        "level": float(np.exp(rng.normal(0.0, 0.45))),
        "work_stop_age": facts.pop("work_stop_age", 62),
        "ss_2010": facts.pop("ss_2010", 0),
        "ss_2008": facts.pop("ss_2008", 0),
        "ss_type": facts.pop("ss_type", None),
        "m4_disabled": facts.pop("m4_disabled", False),
        **facts,
    }


def _amount(rng: np.random.Generator, low: int, high: int) -> int:
    return int(12 * rng.integers(low, high))


def _recipient(
    rng: np.random.Generator,
    low: int,
    high: int,
    *,
    bracketed: bool,
) -> dict[str, int]:
    amount = _amount(rng, low, high)
    return {
        "ss_2010": amount,
        "ss_2008": 0 if bracketed else int(round(amount / 1.058)),
    }


def _families(rng: np.random.Generator) -> list[InventedFamily]:
    families: list[InventedFamily] = []
    counter = 0

    def new_ids() -> tuple[int, int, int]:
        nonlocal counter
        counter += 1
        base = 100_000 + 100 * counter
        return base + 1, base + 2, 5_000 + counter

    def weight() -> float:
        return float(np.round(rng.uniform(2_000.0, 20_000.0), 2))

    def sex() -> str:
        return str(rng.choice(["female", "male"]))

    counts = INVENTED_FAMILY_COUNTS
    for _ in range(counts["retired_couple"]):
        head_id, spouse_id, interview = new_ids()
        head_age = int(rng.integers(64, 88))
        spouse_age = int(np.clip(head_age + rng.integers(-6, 3), 56, 90))
        bracketed_head = False
        members = [
            _person(
                rng,
                person_id=head_id,
                sex="male",
                age=head_age,
                relationship=10,
                sequence=1,
                weight=weight(),
                ss_type="retirement",
                **_recipient(rng, 900, 2_300, bracketed=bracketed_head),
            )
        ]
        spouse_facts: dict[str, Any] = {}
        if spouse_age >= 64:
            spouse_facts = {
                "ss_type": "retirement",
                **_recipient(rng, 500, 1_500, bracketed=False),
            }
        elif spouse_age >= 62:
            spouse_facts = {
                "ss_type": "retirement",
                **_recipient(rng, 500, 1_300, bracketed=True),
            }
        members.append(
            _person(
                rng,
                person_id=spouse_id,
                sex="female",
                age=spouse_age,
                relationship=20,
                sequence=2,
                weight=weight(),
                **spouse_facts,
            )
        )
        families.append(
            InventedFamily("retired_couple", interview, tuple(members))
        )
    for _ in range(counts["retired_single"]):
        head_id, _, interview = new_ids()
        age = int(rng.integers(62, 92))
        members = (
            _person(
                rng,
                person_id=head_id,
                sex=sex(),
                age=age,
                relationship=10,
                sequence=1,
                weight=weight(),
                ss_type="retirement",
                marital="divorced" if age % 2 else "never_married",
                **_recipient(rng, 800, 2_100, bracketed=age < 64),
            ),
        )
        families.append(InventedFamily("retired_single", interview, members))
    for survivor_type, count, low, high in (
        ("aged_survivor", counts["aged_survivor"], 64, 92),
        ("young_survivor", counts["young_survivor"], 45, 60),
        ("widowed_nonrecipient", counts["widowed_nonrecipient"], 45, 58),
    ):
        for _ in range(count):
            head_id, late_id, interview = new_ids()
            age = int(rng.integers(low, high))
            birth = _START - age
            late_birth = birth + int(rng.integers(-6, 3))
            death_low = min(max(1990, late_birth + 25), 2009)
            death_year = int(rng.integers(death_low, 2010))
            facts: dict[str, Any] = {"marital": "widowed"}
            if survivor_type != "widowed_nonrecipient":
                facts.update(
                    ss_type="survivor",
                    **_recipient(
                        rng, 700, 1_600, bracketed=death_year >= 2009
                    ),
                )
            members = (
                _person(
                    rng,
                    person_id=head_id,
                    sex="female",
                    age=age,
                    relationship=10,
                    sequence=1,
                    weight=weight(),
                    work_stop_age=int(rng.integers(40, 62)),
                    **facts,
                ),
            )
            late = {
                "person_id": late_id + 90_000_000,
                "sex": "male",
                "birth_year": late_birth,
                "death_year": death_year,
            }
            families.append(
                InventedFamily(survivor_type, interview, members, late)
            )
    for index in range(counts["di_single"]):
        head_id, _, interview = new_ids()
        age = int(30 + index) if index < 8 else int(rng.integers(45, 61))
        members = (
            _person(
                rng,
                person_id=head_id,
                sex=sex(),
                age=age,
                relationship=10,
                sequence=1,
                weight=weight(),
                ss_type="disability",
                m4_disabled=True,
                work_stop_age=age - int(rng.integers(0, 4)),
                marital="never_married",
                **_recipient(rng, 600, 1_500, bracketed=index % 3 == 0),
            ),
        )
        families.append(InventedFamily("di_single", interview, members))
    for _ in range(counts["di_couple"]):
        head_id, spouse_id, interview = new_ids()
        head_age = int(rng.integers(45, 62))
        members = (
            _person(
                rng,
                person_id=head_id,
                sex="male",
                age=head_age,
                relationship=10,
                sequence=1,
                weight=weight(),
                ss_type="disability",
                m4_disabled=True,
                work_stop_age=head_age - int(rng.integers(0, 5)),
                **_recipient(rng, 800, 1_700, bracketed=False),
            ),
            _person(
                rng,
                person_id=spouse_id,
                sex="female",
                age=int(np.clip(head_age + rng.integers(-5, 4), 40, 61)),
                relationship=20,
                sequence=2,
                weight=weight(),
            ),
        )
        families.append(InventedFamily("di_couple", interview, members))
    for family_type, count, low, high in (
        ("working_couple", counts["working_couple"], 30, 62),
        ("near_retirement_couple", counts["near_retirement_couple"], 55, 62),
    ):
        for _ in range(count):
            head_id, spouse_id, interview = new_ids()
            head_age = int(rng.integers(low, high))
            members = (
                _person(
                    rng,
                    person_id=head_id,
                    sex="male",
                    age=head_age,
                    relationship=10,
                    sequence=1,
                    weight=weight(),
                ),
                _person(
                    rng,
                    person_id=spouse_id,
                    sex="female",
                    age=int(np.clip(head_age + rng.integers(-5, 4), 30, 61)),
                    relationship=20,
                    sequence=2,
                    weight=weight(),
                ),
            )
            families.append(InventedFamily(family_type, interview, members))
    for _ in range(counts["working_single"]):
        head_id, _, interview = new_ids()
        age = int(rng.integers(30, 62))
        members = (
            _person(
                rng,
                person_id=head_id,
                sex=sex(),
                age=age,
                relationship=10,
                sequence=1,
                weight=weight(),
                marital="divorced" if age % 3 == 0 else "never_married",
            ),
        )
        families.append(InventedFamily("working_single", interview, members))
    for _ in range(counts["late_claimer"]):
        head_id, _, interview = new_ids()
        age = int(rng.integers(62, 70))
        members = (
            _person(
                rng,
                person_id=head_id,
                sex=sex(),
                age=age,
                relationship=10,
                sequence=1,
                weight=weight(),
                work_stop_age=age + 1,
                marital="never_married",
            ),
        )
        families.append(InventedFamily("late_claimer", interview, members))
    return families


def _marriage_rows(family: InventedFamily) -> list[dict[str, Any]]:
    rows = []
    members = family.members
    couple = len(members) == 2
    for member in members:
        base = {
            "person_id": member["person_id"],
            "sex": member["sex"],
            "birth_year": member["birth_year"],
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
        marital = member.get("marital")
        if couple:
            partner = [m for m in members if m is not member][0]
            start = max(m["birth_year"] for m in members) + 24
            base.update(
                is_marriage=True,
                marriage_order=1,
                n_marriages=1,
                spouse_person_id=partner["person_id"],
                start_year=start,
                how_ended="intact",
                last_known_status="married",
            )
        elif marital == "widowed":
            late = family.late_spouse
            assert late is not None
            base.update(
                is_marriage=True,
                marriage_order=1,
                n_marriages=1,
                spouse_person_id=late["person_id"],
                start_year=max(member["birth_year"], late["birth_year"]) + 23,
                end_year=late["death_year"],
                how_ended="widowhood",
                last_known_status="widowed",
            )
        elif marital == "divorced":
            start = member["birth_year"] + 25
            base.update(
                is_marriage=True,
                marriage_order=1,
                n_marriages=1,
                start_year=start,
                end_year=start + 8,
                how_ended="divorce",
                last_known_status="divorced",
            )
        rows.append(base)
    if family.late_spouse is not None:
        late = family.late_spouse
        survivor = members[0]
        rows.append(
            {
                **rows[0],
                "person_id": late["person_id"],
                "sex": late["sex"],
                "birth_year": late["birth_year"],
                "spouse_person_id": survivor["person_id"],
                "last_known_status": "married",
            }
        )
    return rows


def _earnings_rows(
    rng: np.random.Generator, member: Mapping[str, Any], role: str
) -> list[dict[str, Any]]:
    birth = int(member["birth_year"])
    last = min(_START, birth + int(member["work_stop_age"]) - 1)
    rows = []
    for year in range(max(1968, birth + 22), last + 1):
        if year >= 1997 and year % 2 == 1:
            continue  # PSID biennial income years after 1996
        earnings = member["level"] * _wage_index(year)
        earnings *= float(np.exp(rng.normal(0.0, 0.15)))
        rows.append(
            {
                "person_id": member["person_id"],
                "period": year,
                "earnings": float(np.round(earnings, 0)),
                "age": year - birth,
                "earnings_acc": 0,
                "role": role,
                "weight": 1.0,
            }
        )
    return rows


def _ss_rows(
    family: InventedFamily,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    family_rows = []
    individual_rows = []
    for wave, column in ((2009, "ss_2008"), (_ANCHOR, "ss_2010")):
        any_receipt = any(m[column] > 0 for m in family.members)
        for member in family.members:
            role = "head" if member["relationship"] == 10 else "spouse"
            amount = int(member[column])
            family_rows.append(
                {
                    "person_id": member["person_id"],
                    "wave": wave,
                    "income_year": wave - 1,
                    "role": role,
                    "ss_amount": amount,
                    "ss_acc": 0,
                    "fu_ss_prior_year": 1 if any_receipt else 5,
                    "age": wave - member["birth_year"],
                    "weight": member["weight"],
                    "interview": (
                        family.interview
                        if wave == _ANCHOR
                        else family.interview + 20_000
                    ),
                }
            )
            row: dict[str, Any] = {
                "person_id": member["person_id"],
                "wave": wave,
                "income_year": wave - 1,
                "relationship": member["relationship"],
                "interview": family.interview,
                "age": wave - member["birth_year"],
                "weight": member["weight"],
                "ss_amount": amount,
                "ss_acc": 0,
                "type_combination": False,
            }
            for name in ssi.SS_TYPES:
                row[f"type_{name}"] = (
                    pd.NA if amount == 0 else name == member["ss_type"]
                )
            individual_rows.append(row)
    return family_rows, individual_rows


def invented_psid2010_inputs(
    *,
    seed: int = 20260922,
    claiming_pmf: Mapping[tuple[str, int], Mapping[int, float]] | None = None,
) -> cohort.Psid2010Inputs:
    """INVENTED ``Psid2010Inputs`` for the A3 builder (250 persons).

    ``claiming_pmf`` defaults to :func:`invented_claiming_pmf`; the dry run
    passes the committed claim-age table instead (a parameter, not data).
    """

    rng = np.random.default_rng(seed)
    families = _families(rng)
    anchor, deaths, marriages, earnings = [], [], [], []
    family_ss, individual_ss, disability = [], [], []
    for family in families:
        for member in family.members:
            anchor.append(
                {
                    "person_id": member["person_id"],
                    "interview": family.interview,
                    "sequence": member["sequence"],
                    "relationship": member["relationship"],
                    "age": _ANCHOR - member["birth_year"],
                    "reported_birth_year": pd.NA,
                    "weight": member["weight"],
                }
            )
            deaths.append(
                {
                    "person_id": member["person_id"],
                    "sex": member["sex"],
                    "death_status": "not_deceased",
                    "death_year": pd.NA,
                    "death_year_lo": pd.NA,
                    "death_year_hi": pd.NA,
                }
            )
            role = "head" if member["relationship"] == 10 else "spouse"
            earnings.extend(_earnings_rows(rng, member, role))
            disability.append(
                {
                    "person_id": member["person_id"],
                    "period": _ANCHOR,
                    "disabled": bool(member["m4_disabled"]),
                }
            )
        if family.late_spouse is not None:
            late = family.late_spouse
            deaths.append(
                {
                    "person_id": late["person_id"],
                    "sex": late["sex"],
                    "death_status": "exact",
                    "death_year": late["death_year"],
                    "death_year_lo": late["death_year"],
                    "death_year_hi": late["death_year"],
                }
            )
        marriages.extend(_marriage_rows(family))
        rows, individual = _ss_rows(family)
        family_ss.extend(rows)
        individual_ss.extend(individual)
    anchor_frame = pd.DataFrame(anchor)
    anchor_frame["reported_birth_year"] = anchor_frame[
        "reported_birth_year"
    ].astype("Int64")
    death_frame = pd.DataFrame(deaths)
    for column in ("death_year", "death_year_lo", "death_year_hi"):
        death_frame[column] = death_frame[column].astype("Int64")
    marriage_frame = pd.DataFrame(marriages)
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
        marriage_frame[column] = marriage_frame[column].astype("Int64")
    for column in ("sex", "how_ended", "last_known_status"):
        marriage_frame[column] = marriage_frame[column].astype("string")
    marriage_frame["n_records"] = marriage_frame["n_records"].astype("int64")
    marriage_frame["is_marriage"] = marriage_frame["is_marriage"].astype(bool)
    individual_frame = pd.DataFrame(individual_ss)
    for name in ssi.SS_TYPES:
        individual_frame[f"type_{name}"] = individual_frame[
            f"type_{name}"
        ].astype("boolean")
    individual_frame["type_combination"] = individual_frame[
        "type_combination"
    ].astype("boolean")
    return cohort.Psid2010Inputs(
        anchor=anchor_frame,
        death_records=death_frame,
        marriage_history=marriage_frame,
        observed_earnings=pd.DataFrame(earnings),
        head_spouse_ss=pd.DataFrame(family_ss),
        individual_ss=individual_frame,
        disability_status=pd.DataFrame(disability),
        claiming_pmf=(
            invented_claiming_pmf() if claiming_pmf is None else claiming_pmf
        ),
        provenance={
            "data": INVENTED_INPUTS_LABEL,
            "seed": int(seed),
            "family_counts": dict(INVENTED_FAMILY_COUNTS),
        },
    )
