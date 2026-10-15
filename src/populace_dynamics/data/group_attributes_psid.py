"""Label-verified PSID readers for MINT group attributes.

This module reads, from the staged PSID, the three person attributes the
MINT group breakdowns need and the existing cohorts do not carry: race and
Hispanic origin, years of completed education, and country of birth. It
returns raw, documented codes and the pure functions that give each code
its meaning. Choosing among a person's reports across waves, and mapping
them to report categories, is cohort code
(:mod:`populace_dynamics.cohorts.group_attributes`), which is the only
caller of these readers.

Where each attribute lives in the PSID (adjudicated 2026-10-01 from the
staged label files, the codebook PDFs and the formats files):

* **Race and Hispanic origin** are asked of the family's head (reference
  person from 2017) and wife ("Wife", spouse or partner from 2015) in the
  per-wave family files, never of other family-unit members (OFUMs). The
  instrument changed over time, so each wave carries a code frame
  (:data:`RACE_ERAS`):

  - 1985-1989: a Spanish-descent question (Mexican, Mexican American,
    Chicano, Puerto Rican, Cuban, combination, other Spanish) and up to
    two race mentions (white, black, American Indian/Aleut/Eskimo,
    Asian/Pacific Islander, other; code 8 "more than two mentions").
  - 1990-1993: the same, with race codes 5 "mentions Latino origin or
    descent" and 6 "mentions color other than black or white".
  - 1994-2003: three (1994-1996) or four (1997-2003) race mentions with
    the 1990 codes, except that code 8 is "DK" rather than "more than two
    mentions". **1997-2003 ask no Spanish-descent question**, so a
    report from those waves shows Hispanic origin only through a race
    mention of Latino origin and never shows its absence.
  - 2005-2023: a Spanish-descent question (no "combination" code) and up
    to four race mentions with the OMB 1997 codes: white; black, African
    American or Negro; American Indian or Alaska Native; Asian; Native
    Hawaiian or Pacific Islander; other. **Code 5 here means Native
    Hawaiian or Pacific Islander; in 1990-2003 it meant Latino origin**,
    which is why every code is read through its wave's frame.

  Before 1985 the family files carry one "RACE" item for the head only,
  with a Spanish-American race category and no wife item; those waves
  are not read (see the cohort module for what that costs).

* **Years of completed education** come from the cross-year individual
  file's per-wave "YEARS COMPLETED EDUCATION" series (1985-2023 labels
  vary: "COMPLETED EDUCATION", "COMPLETED EDUC-IND", "YRS COMPLETED
  EDUC"), which covers heads, wives and OFUMs aged 16 or older: 1-16 is
  the highest grade completed and 17 "at least some post-graduate work";
  a GED without college is 12. Its code 0 is documented only as Inap.,
  and therefore does not by itself establish zero schooling. The family
  file's COMPLETED ED-HD/WF recode (1993 on) explicitly documents
  "completed no grades of school": a present head or spouse with both
  codes 0 has 0 years of schooling. An OFUM with individual code 0 is
  left unreported.

* **Country of birth** is asked of heads and wives from 2013: "L33/K33
  STATE <role> WAS BORN" (FIPS state 1-56; 0 "U.S. territory or foreign
  country"; 99 DK/NA/refused) with "L33YR/K33YR YEAR CAME TO UNITED
  STATES" (0 "born in the United States or U.S. territory"). The pair
  separates a U.S. state, a U.S. territory and a foreign country. The
  1997/1999 immigrant-supplement items ("M50 CKPT HEAD BORN IN US",
  individual "ES1 STATE WHERE BORN") cover only new or immigrant-sample
  heads and wives, and "STATE <role> GREW UP" is not a birthplace, so
  none of them is read.

Every variable is checked against its exact label (whitespace
normalized) before any fixed-width read, and every observed code against
the codes its wave documents: the codebook value tables committed in
``data/external/psid_group_attribute_codebook_values_v1.json`` (built by
``scripts/build_group_attribute_codebook_values.py`` from the staged
codebook PDFs, whose SHA-256 the table pins), cross-checked against the
2021 and 2023 family formats files and ``IND2023ER_formats.sas`` where a
format block exists. An undocumented code raises.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from functools import cache
from numbers import Integral
from pathlib import Path
from typing import Any

import pandas as pd

from populace_dynamics.data import disability, family, psid

__all__ = [
    "ROLES",
    "RACE_WAVES",
    "INDIVIDUAL_WAVES",
    "FAMILY_EDUCATION_WAVES",
    "BIRTHPLACE_WAVES",
    "RACE_ERAS",
    "FamilyWaveItems",
    "IndividualWaveItems",
    "FAMILY_ITEMS",
    "INDIVIDUAL_ITEMS",
    "CodeDomain",
    "CODEBOOK_VALUES_PATH",
    "CODEBOOK_VALUES_SHA256",
    "load_codebook_values",
    "documented_domain",
    "parse_sas_value_domains",
    "read_individual_items",
    "read_family_items",
    "verify_codebook_pins",
    "head_spouse_reports",
    "hispanic_meaning",
    "race_mention_meaning",
    "RaceEthnicityReport",
    "race_ethnicity_report",
    "birthplace_class",
    "education_report",
]

#: The two family-file roles whose items this module reads. "head" is the
#: head (reference person from 2017); "spouse" is the wife/"wife" (spouse
#: or partner from 2015): individual-file relationship 20 (legal wife or
#: spouse) or 22 (cohabiting partner of a year or more).
ROLES: tuple[str, ...] = ("head", "spouse")

#: Waves whose family files carry the race items read here: annual
#: 1985-1997, biennial 1999-2023.
RACE_WAVES: tuple[int, ...] = (*range(1985, 1998), *range(1999, 2024, 2))
#: Individual-file waves read for the roster and education (the same).
INDIVIDUAL_WAVES: tuple[int, ...] = RACE_WAVES
#: Waves whose family files carry COMPLETED ED-HD/WF in years (1993 on;
#: 1985-1992 carry a bracketed "EDUCATION <yyyy> HEAD" code instead).
FAMILY_EDUCATION_WAVES: tuple[int, ...] = tuple(
    w for w in RACE_WAVES if w >= 1993
)
#: Waves whose family files ask where the head and wife were born.
BIRTHPLACE_WAVES: tuple[int, ...] = tuple(w for w in RACE_WAVES if w >= 2013)

#: Individual-file relationship codes (1983 on) for the two roles; their
#: labels are verified against IND2023ER_formats.sas at read time.
HEAD_RELATIONSHIP = 10
SPOUSE_RELATIONSHIPS: tuple[int, ...] = (20, 22)
#: Sequence numbers of persons in the family at the interview.
IN_FAMILY_SEQUENCE: tuple[int, int] = (1, 20)

_PERSON_VARS: dict[str, str] = {
    "ER30001": "1968 INTERVIEW NUMBER",
    "ER30002": "PERSON NUMBER 68",
}

# --------------------------------------------------------------------------
# Code frames and their meanings
# --------------------------------------------------------------------------
RACE_ERA_1985 = "1985-1989"
RACE_ERA_1990 = "1990-1993"
RACE_ERA_1994 = "1994-2003"
RACE_ERA_2005 = "2005-2023"
RACE_ERAS: tuple[str, ...] = (
    RACE_ERA_1985,
    RACE_ERA_1990,
    RACE_ERA_1994,
    RACE_ERA_2005,
)

# Race-mention meanings (harmonized categories).
WHITE = "white"
BLACK = "black"
AMERICAN_INDIAN = "american_indian_alaska_native"
ASIAN_PACIFIC = "asian_pacific_islander"
ASIAN = "asian"
PACIFIC_ISLANDER = "native_hawaiian_pacific_islander"
OTHER_RACE = "other_race"
OTHER_COLOR = "color_other_than_black_or_white"
MORE_THAN_TWO = "more_than_two_races"
LATINO_ORIGIN = "latino_origin_mention"
NO_FURTHER_MENTION = "no_further_mention"
MISSING = "missing"

#: The race categories (a person's race set is drawn from these).
#: ``more_than_two_races`` marks a 1985-1993 "more than two mentions"
#: response: at least three races, the rest not recorded.
RACE_CATEGORIES: tuple[str, ...] = (
    WHITE,
    BLACK,
    AMERICAN_INDIAN,
    ASIAN_PACIFIC,
    ASIAN,
    PACIFIC_ISLANDER,
    OTHER_RACE,
    OTHER_COLOR,
    MORE_THAN_TWO,
)

#: Code -> meaning per race code frame, from the codebook value tables
#: (``data/external/psid_group_attribute_codebook_values_v1.json``; a test
#: holds every documented code to a meaning whose text agrees). Code 0 on
#: a second or later mention is "no further mention"; code 0 on the first
#: mention is never a valid answer (for a wife it is "no wife in FU", for
#: the 2005/2007 head a documented "wild code") and reads as missing.
RACE_CODE_MEANINGS: dict[str, dict[int, str]] = {
    RACE_ERA_1985: {
        1: WHITE,
        2: BLACK,
        3: AMERICAN_INDIAN,
        4: ASIAN_PACIFIC,
        7: OTHER_RACE,
        8: MORE_THAN_TWO,
        9: MISSING,
        0: NO_FURTHER_MENTION,
    },
    RACE_ERA_1990: {
        1: WHITE,
        2: BLACK,
        3: AMERICAN_INDIAN,
        4: ASIAN_PACIFIC,
        5: LATINO_ORIGIN,
        6: OTHER_COLOR,
        7: OTHER_RACE,
        8: MORE_THAN_TWO,
        9: MISSING,
        0: NO_FURTHER_MENTION,
    },
    RACE_ERA_1994: {
        1: WHITE,
        2: BLACK,
        3: AMERICAN_INDIAN,
        4: ASIAN_PACIFIC,
        5: LATINO_ORIGIN,
        6: OTHER_COLOR,
        7: OTHER_RACE,
        8: MISSING,
        9: MISSING,
        0: NO_FURTHER_MENTION,
    },
    RACE_ERA_2005: {
        1: WHITE,
        2: BLACK,
        3: AMERICAN_INDIAN,
        4: ASIAN,
        5: PACIFIC_ISLANDER,
        7: OTHER_RACE,
        8: MISSING,
        9: MISSING,
        0: NO_FURTHER_MENTION,
    },
}

HISPANIC = "hispanic"
NOT_HISPANIC = "not_hispanic"
#: Spanish-descent code -> meaning (every wave that asks it). 1-7 are the
#: origins (6 "combination; more than one mention" before 2005); 0 is
#: "not Spanish, Hispanic or Latino". For a wife the codebook's 0 also
#: covers "no wife in FU". In 1994-1996 its wife-variable text names
#: only that case; a present spouse's 0 therefore has an undocumented
#: meaning and remains unknown (:func:`race_ethnicity_report`).
HISPANIC_CODE_MEANINGS: dict[int, str] = {
    0: NOT_HISPANIC,
    1: HISPANIC,
    2: HISPANIC,
    3: HISPANIC,
    4: HISPANIC,
    5: HISPANIC,
    6: HISPANIC,
    7: HISPANIC,
    8: MISSING,
    9: MISSING,
}

# Birthplace classes.
UNITED_STATES = "united_states"
US_TERRITORY = "us_territory"
FOREIGN_COUNTRY = "foreign_country"
INCONSISTENT = "inconsistent"
BIRTHPLACE_CLASSES: tuple[str, ...] = (
    UNITED_STATES,
    US_TERRITORY,
    FOREIGN_COUNTRY,
    MISSING,
    INCONSISTENT,
)
#: "STATE <role> WAS BORN": FIPS state codes, "U.S. territory or foreign
#: country", and DK/NA/refused.
BIRTH_STATE_RANGE: tuple[int, int] = (1, 56)
BIRTH_STATE_NOT_A_STATE = 0
BIRTH_STATE_MISSING = 99
#: "YEAR CAME TO UNITED STATES": 0 is "born in the United States or U.S.
#: territory"; 9997 "not living in the United States"; 9998/9999 DK/NA.
YEAR_CAME_BORN_IN_US = 0
YEAR_CAME_NOT_LIVING_IN_US = 9997
YEAR_CAME_MISSING: tuple[int, ...] = (9998, 9999)

# Education report statuses.
EDUCATION_REPORTED = "reported"
EDUCATION_NO_GRADES = "no_grades"
EDUCATION_MISSING = "missing"
EDUCATION_INAPPLICABLE = "inapplicable"
#: Individual-file "YEARS COMPLETED EDUCATION" codes.
EDUCATION_YEARS_RANGE: tuple[int, int] = (1, 17)
EDUCATION_DK_NA: tuple[int, ...] = (98, 99)
#: Family-file COMPLETED ED-HD/WF code for "completed no grades".
FAMILY_EDUCATION_NO_GRADES = 0
FAMILY_EDUCATION_MISSING = 99


# --------------------------------------------------------------------------
# Adjudicated per-wave tables
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class FamilyWaveItems:
    """One family-file wave's label-verified group-attribute variables.

    Every item maps a role (``"head"``, ``"spouse"``) to ``(variable,
    exact label)``; ``race`` maps each role to its mentions in order. An
    empty mapping means the wave does not carry the item (no
    Spanish-descent question 1997-2003; no years-of-education recode
    before 1993; no birthplace before 2013). ``race_era`` names the race
    code frame (:data:`RACE_CODE_MEANINGS`).
    """

    wave: int
    race_era: str
    interview: tuple[str, str]
    race: Mapping[str, tuple[tuple[str, str], ...]]
    hispanic: Mapping[str, tuple[str, str]] = field(default_factory=dict)
    completed_education: Mapping[str, tuple[str, str]] = field(
        default_factory=dict
    )
    birth_state: Mapping[str, tuple[str, str]] = field(default_factory=dict)
    year_came: Mapping[str, tuple[str, str]] = field(default_factory=dict)

    @property
    def asks_hispanic_origin(self) -> bool:
        return bool(self.hispanic)

    def labels(self) -> dict[str, str]:
        """Every variable this wave reads, with its exact label."""
        out = {self.interview[0]: self.interview[1]}
        for item in (
            self.hispanic,
            self.completed_education,
            self.birth_state,
            self.year_came,
        ):
            out.update({var: label for var, label in item.values()})
        for mentions in self.race.values():
            out.update({var: label for var, label in mentions})
        return out

    def role_columns(self, role: str) -> dict[str, str]:
        """``{variable: generic column}`` for one role's items."""
        out: dict[str, str] = {}
        if self.hispanic:
            out[self.hispanic[role][0]] = "hispanic_code"
        for i, (var, _) in enumerate(self.race[role], start=1):
            out[var] = f"race_code_{i}"
        if self.completed_education:
            out[self.completed_education[role][0]] = "family_education_code"
        if self.birth_state:
            out[self.birth_state[role][0]] = "birth_state_code"
        if self.year_came:
            out[self.year_came[role][0]] = "year_came_code"
        return out


@dataclass(frozen=True)
class IndividualWaveItems:
    """One wave's label-verified individual-file roster and education."""

    wave: int
    interview: tuple[str, str]
    sequence: tuple[str, str]
    relationship: tuple[str, str]
    education: tuple[str, str]

    def labels(self) -> dict[str, str]:
        return {
            var: label
            for var, label in (
                self.interview,
                self.sequence,
                self.relationship,
                self.education,
            )
        }


#: The adjudicated family-file variables, wave by wave. Built 2026-10-01
#: by matching each concept's labels in every staged FAM<yyyy>[ER].sps
#: (one match per role, mention and wave; the 1990 interview label is
#: PSID's own "1990 INTERVEW NUMBER") and verified at read time under
#: whitespace normalization.
FAMILY_ITEMS: dict[int, FamilyWaveItems] = {
    1985: FamilyWaveItems(
        wave=1985,
        race_era=RACE_ERA_1985,
        interview=("V11102", "1985 INTERVIEW NUMBER"),
        hispanic={
            "head": ("V11937", "G31 SPANISH DESCENT-HEAD"),
            "spouse": ("V12292", "N31 SPANISH DESCENT-WIFE"),
        },
        race={
            "head": (
                ("V11938", "G32 RACE OF HEAD (1 MEN)"),
                ("V11939", "G32 RACE OF HEAD (2 MEN)"),
            ),
            "spouse": (
                ("V12293", "N32 RACE OF WIFE (1 MEN)"),
                ("V12294", "N32 RACE OF WIFE (2 MEN)"),
            ),
        },
    ),
    1986: FamilyWaveItems(
        wave=1986,
        race_era=RACE_ERA_1985,
        interview=("V12502", "1986 INTERVIEW NUMBER"),
        hispanic={
            "head": ("V13564", "L31 SPANISH DESCENT HD"),
            "spouse": ("V13499", "K18 SPANISH DESCENT WF"),
        },
        race={
            "head": (
                ("V13565", "L32 RACE OF HEAD 1"),
                ("V13566", "L32 RACE OF HEAD 2"),
            ),
            "spouse": (
                ("V13500", "K19 RACE OF WIFE 1"),
                ("V13501", "K19 RACE OF WIFE 2"),
            ),
        },
    ),
    1987: FamilyWaveItems(
        wave=1987,
        race_era=RACE_ERA_1985,
        interview=("V13702", "1987 INTERVIEW NUMBER"),
        hispanic={
            "head": ("V14611", "L31 SPANISH DESCENT HD"),
            "spouse": ("V14546", "K18 SPANISH DESCENT WF"),
        },
        race={
            "head": (
                ("V14612", "L32 RACE OF HEAD 1"),
                ("V14613", "L32 RACE OF HEAD 2"),
            ),
            "spouse": (
                ("V14547", "K19 RACE OF WIFE 1"),
                ("V14548", "K19 RACE OF WIFE 2"),
            ),
        },
    ),
    1988: FamilyWaveItems(
        wave=1988,
        race_era=RACE_ERA_1985,
        interview=("V14802", "1988 INTERVIEW NUMBER"),
        hispanic={
            "head": ("V16085", "L31 SPANISH DESCENT HD"),
            "spouse": ("V16020", "K18 SPANISH DESCENT WF"),
        },
        race={
            "head": (
                ("V16086", "L32 RACE OF HEAD 1"),
                ("V16087", "L32 RACE OF HEAD 2"),
            ),
            "spouse": (
                ("V16021", "K19 RACE OF WIFE 1"),
                ("V16022", "K19 RACE OF WIFE 2"),
            ),
        },
    ),
    1989: FamilyWaveItems(
        wave=1989,
        race_era=RACE_ERA_1985,
        interview=("V16302", "1989 INTERVIEW NUMBER"),
        hispanic={
            "head": ("V17482", "L31 SPANISH DESCENT HD"),
            "spouse": ("V17417", "K18 SPANISH DESCENT WF"),
        },
        race={
            "head": (
                ("V17483", "L32 RACE OF HEAD 1"),
                ("V17484", "L32 RACE OF HEAD 2"),
            ),
            "spouse": (
                ("V17418", "K19 RACE OF WIFE 1"),
                ("V17419", "K19 RACE OF WIFE 2"),
            ),
        },
    ),
    1990: FamilyWaveItems(
        wave=1990,
        race_era=RACE_ERA_1990,
        interview=("V17702", "1990 INTERVEW NUMBER"),
        hispanic={
            "head": ("V18813", "M31 SPANISH DESCENT HD"),
            "spouse": ("V18748", "L18 SPANISH DESCENT WF"),
        },
        race={
            "head": (
                ("V18814", "M32 RACE OF HEAD 1"),
                ("V18815", "M32 RACE OF HEAD 2"),
            ),
            "spouse": (
                ("V18749", "L19 RACE OF WIFE 1"),
                ("V18750", "L19 RACE OF WIFE 2"),
            ),
        },
    ),
    1991: FamilyWaveItems(
        wave=1991,
        race_era=RACE_ERA_1990,
        interview=("V19002", "1991 INTERVIEW NUMBER"),
        hispanic={
            "head": ("V20113", "L31 SPANISH DESCENT HD"),
            "spouse": ("V20048", "K18 SPANISH DESCENT WF"),
        },
        race={
            "head": (
                ("V20114", "L32 RACE OF HEAD 1"),
                ("V20115", "L32 RACE OF HEAD 2"),
            ),
            "spouse": (
                ("V20049", "K19 RACE OF WIFE 1"),
                ("V20050", "K19 RACE OF WIFE 2"),
            ),
        },
    ),
    1992: FamilyWaveItems(
        wave=1992,
        race_era=RACE_ERA_1990,
        interview=("V20302", "1992 INTERVIEW NUMBER"),
        hispanic={
            "head": ("V21419", "M31 SPANISH DESCENT HD"),
            "spouse": ("V21354", "L18 SPANISH DESCENT WF"),
        },
        race={
            "head": (
                ("V21420", "M32 RACE OF HEAD 1"),
                ("V21421", "M32 RACE OF HEAD 2"),
            ),
            "spouse": (
                ("V21355", "L19 RACE OF WIFE 1"),
                ("V21356", "L19 RACE OF WIFE 2"),
            ),
        },
    ),
    1993: FamilyWaveItems(
        wave=1993,
        race_era=RACE_ERA_1990,
        interview=("V21602", "1993 INTERVIEW NUMBER"),
        hispanic={
            "head": ("V23275", "L31 WTR HD OF SPANISH DESCENT"),
            "spouse": ("V23211", "K18 WTR WF OF SPANISH DESCENT"),
        },
        race={
            "head": (
                ("V23276", "L32 RACE OF HD-1ST MENTION"),
                ("V23277", "L32 RACE OF HD-2ND MENTION"),
            ),
            "spouse": (
                ("V23212", "K19 RACE OF WF-1ST MENTION"),
                ("V23213", "K19 RACE OF WF-2ND MENTION"),
            ),
        },
        completed_education={
            "head": ("V23333", "COMPLETED ED-HD 1993"),
            "spouse": ("V23334", "COMPLETED ED-WF 1993"),
        },
    ),
    1994: FamilyWaveItems(
        wave=1994,
        race_era=RACE_ERA_1994,
        interview=("ER2002", "1994 INTERVIEW #"),
        hispanic={
            "head": ("ER3941", "L31 SPANISH DESCENT 1 HD"),
            "spouse": ("ER3880", "K18 SPANISH DESCENT 1 WF"),
        },
        race={
            "head": (
                ("ER3944", "L32 RACE OF HEAD 1"),
                ("ER3945", "L32 RACE OF HEAD 2"),
                ("ER3946", "L32 RACE OF HEAD 3"),
            ),
            "spouse": (
                ("ER3883", "K19 RACE OF WIFE 1"),
                ("ER3884", "K19 RACE OF WIFE 2"),
                ("ER3885", "K19 RACE OF WIFE 3"),
            ),
        },
        completed_education={
            "head": ("ER4158", "COMPLETED ED-HD"),
            "spouse": ("ER4159", "COMPLETED ED-WF"),
        },
    ),
    1995: FamilyWaveItems(
        wave=1995,
        race_era=RACE_ERA_1994,
        interview=("ER5002", "1995 INTERVIEW #"),
        hispanic={
            "head": ("ER6811", "L31 SPANISH DESCENT 1 HD"),
            "spouse": ("ER6750", "K18 SPANISH DESCENT 1 WF"),
        },
        race={
            "head": (
                ("ER6814", "L32 RACE OF HEAD 1"),
                ("ER6815", "L32 RACE OF HEAD 2"),
                ("ER6816", "L32 RACE OF HEAD 3"),
            ),
            "spouse": (
                ("ER6753", "K19 RACE OF WIFE 1"),
                ("ER6754", "K19 RACE OF WIFE 2"),
                ("ER6755", "K19 RACE OF WIFE 3"),
            ),
        },
        completed_education={
            "head": ("ER6998", "COMPLETED ED-HD"),
            "spouse": ("ER6999", "COMPLETED ED-WF"),
        },
    ),
    1996: FamilyWaveItems(
        wave=1996,
        race_era=RACE_ERA_1994,
        interview=("ER7002", "1996 INTERVIEW #"),
        hispanic={
            "head": ("ER9057", "L31 SPANISH DESCENT 1 HD"),
            "spouse": ("ER8996", "K18 SPANISH DESCENT 1 WF"),
        },
        race={
            "head": (
                ("ER9060", "L32 RACE OF HEAD 1"),
                ("ER9061", "L32 RACE OF HEAD 2"),
                ("ER9062", "L32 RACE OF HEAD 3"),
            ),
            "spouse": (
                ("ER8999", "K19 RACE OF WIFE 1"),
                ("ER9000", "K19 RACE OF WIFE 2"),
                ("ER9001", "K19 RACE OF WIFE 3"),
            ),
        },
        completed_education={
            "head": ("ER9249", "COMPLETED ED-HD"),
            "spouse": ("ER9250", "COMPLETED ED-WF"),
        },
    ),
    1997: FamilyWaveItems(
        wave=1997,
        race_era=RACE_ERA_1994,
        interview=("ER10002", "1997 INTERVIEW #"),
        race={
            "head": (
                ("ER11848", "L40/95 RACE OF HEAD 1"),
                ("ER11849", "L40/95 RACE OF HEAD 2"),
                ("ER11850", "L40/95 RACE OF HEAD 3"),
                ("ER11851", "L40/95 RACE OF HEAD 4"),
            ),
            "spouse": (
                ("ER11760", "K34/87 RACE OF WIFE 1"),
                ("ER11761", "K34/87 RACE OF WIFE 2"),
                ("ER11762", "K34/87 RACE OF WIFE 3"),
                ("ER11763", "K34/87 RACE OF WIFE 4"),
            ),
        },
        completed_education={
            "head": ("ER12222", "COMPLETED ED-HD"),
            "spouse": ("ER12223", "COMPLETED ED-WF"),
        },
    ),
    1999: FamilyWaveItems(
        wave=1999,
        race_era=RACE_ERA_1994,
        interview=("ER13002", "1999 FAMILY INTERVIEW (ID) NUMBER"),
        race={
            "head": (
                ("ER15928", "L40/95 RACE OF HEAD 1"),
                ("ER15929", "L40/95 RACE OF HEAD 2"),
                ("ER15930", "L40/95 RACE OF HEAD 3"),
                ("ER15931", "L40/95 RACE OF HEAD 4"),
            ),
            "spouse": (
                ("ER15836", "K34/87 RACE OF WIFE 1"),
                ("ER15837", "K34/87 RACE OF WIFE 2"),
                ("ER15838", "K34/87 RACE OF WIFE 3"),
                ("ER15839", "K34/87 RACE OF WIFE 4"),
            ),
        },
        completed_education={
            "head": ("ER16516", "COMPLETED ED-HD"),
            "spouse": ("ER16517", "COMPLETED ED-WF"),
        },
    ),
    2001: FamilyWaveItems(
        wave=2001,
        race_era=RACE_ERA_1994,
        interview=("ER17002", "2001 FAMILY INTERVIEW (ID) NUMBER"),
        race={
            "head": (
                ("ER19989", "L40/95 RACE OF HEAD 1"),
                ("ER19990", "L40/95 RACE OF HEAD 2"),
                ("ER19991", "L40/95 RACE OF HEAD 3"),
                ("ER19992", "L40/95 RACE OF HEAD 4"),
            ),
            "spouse": (
                ("ER19897", "K34/87 RACE OF WIFE 1"),
                ("ER19898", "K34/87 RACE OF WIFE 2"),
                ("ER19899", "K34/87 RACE OF WIFE 3"),
                ("ER19900", "K34/87 RACE OF WIFE 4"),
            ),
        },
        completed_education={
            "head": ("ER20457", "COMPLETED ED-HD"),
            "spouse": ("ER20458", "COMPLETED ED-WF"),
        },
    ),
    2003: FamilyWaveItems(
        wave=2003,
        race_era=RACE_ERA_1994,
        interview=("ER21002", "2003 FAMILY INTERVIEW (ID) NUMBER"),
        race={
            "head": (
                ("ER23426", "L40/95 RACE OF HEAD 1"),
                ("ER23427", "L40/95 RACE OF HEAD 2"),
                ("ER23428", "L40/95 RACE OF HEAD 3"),
                ("ER23429", "L40/95 RACE OF HEAD 4"),
            ),
            "spouse": (
                ("ER23334", "K34/87 RACE OF WIFE 1"),
                ("ER23335", "K34/87 RACE OF WIFE 2"),
                ("ER23336", "K34/87 RACE OF WIFE 3"),
                ("ER23337", "K34/87 RACE OF WIFE 4"),
            ),
        },
        completed_education={
            "head": ("ER24148", "COMPLETED ED-HD"),
            "spouse": ("ER24149", "COMPLETED ED-WF"),
        },
    ),
    2005: FamilyWaveItems(
        wave=2005,
        race_era=RACE_ERA_2005,
        interview=("ER25002", "2005 FAMILY INTERVIEW (ID) NUMBER"),
        hispanic={
            "head": ("ER27392", "L39A SPANISH DESCENT-HEAD"),
            "spouse": ("ER27296", "K33A SPANISH DESCENT-WIFE"),
        },
        race={
            "head": (
                ("ER27393", "L40 RACE OF HEAD-MENTION 1"),
                ("ER27394", "L40 RACE OF HEAD-MENTION 2"),
                ("ER27395", "L40 RACE OF HEAD-MENTION 3"),
                ("ER27396", "L40 RACE OF HEAD-MENTION 4"),
            ),
            "spouse": (
                ("ER27297", "K34 RACE OF WIFE-MENTION 1"),
                ("ER27298", "K34 RACE OF WIFE-MENTION 2"),
                ("ER27299", "K34 RACE OF WIFE-MENTION 3"),
                ("ER27300", "K34 RACE OF WIFE-MENTION 4"),
            ),
        },
        completed_education={
            "head": ("ER28047", "COMPLETED ED-HD"),
            "spouse": ("ER28048", "COMPLETED ED-WF"),
        },
    ),
    2007: FamilyWaveItems(
        wave=2007,
        race_era=RACE_ERA_2005,
        interview=("ER36002", "2007 FAMILY INTERVIEW (ID) NUMBER"),
        hispanic={
            "head": ("ER40564", "L39 SPANISH DESCENT-HEAD"),
            "spouse": ("ER40471", "K39 SPANISH DESCENT-WIFE"),
        },
        race={
            "head": (
                ("ER40565", "L40 RACE OF HEAD-MENTION 1"),
                ("ER40566", "L40 RACE OF HEAD-MENTION 2"),
                ("ER40567", "L40 RACE OF HEAD-MENTION 3"),
                ("ER40568", "L40 RACE OF HEAD-MENTION 4"),
            ),
            "spouse": (
                ("ER40472", "K40 RACE OF WIFE-MENTION 1"),
                ("ER40473", "K40 RACE OF WIFE-MENTION 2"),
                ("ER40474", "K40 RACE OF WIFE-MENTION 3"),
                ("ER40475", "K40 RACE OF WIFE-MENTION 4"),
            ),
        },
        completed_education={
            "head": ("ER41037", "COMPLETED ED-HD"),
            "spouse": ("ER41038", "COMPLETED ED-WF"),
        },
    ),
    2009: FamilyWaveItems(
        wave=2009,
        race_era=RACE_ERA_2005,
        interview=("ER42002", "2009 FAMILY INTERVIEW (ID) NUMBER"),
        hispanic={
            "head": ("ER46542", "L39 SPANISH DESCENT-HEAD"),
            "spouse": ("ER46448", "K39 SPANISH DESCENT-WIFE"),
        },
        race={
            "head": (
                ("ER46543", "L40 RACE OF HEAD-MENTION 1"),
                ("ER46544", "L40 RACE OF HEAD-MENTION 2"),
                ("ER46545", "L40 RACE OF HEAD-MENTION 3"),
                ("ER46546", "L40 RACE OF HEAD-MENTION 4"),
            ),
            "spouse": (
                ("ER46449", "K40 RACE OF WIFE-MENTION 1"),
                ("ER46450", "K40 RACE OF WIFE-MENTION 2"),
                ("ER46451", "K40 RACE OF WIFE-MENTION 3"),
                ("ER46452", "K40 RACE OF WIFE-MENTION 4"),
            ),
        },
        completed_education={
            "head": ("ER46981", "COMPLETED ED-HD"),
            "spouse": ("ER46982", "COMPLETED ED-WF"),
        },
    ),
    2011: FamilyWaveItems(
        wave=2011,
        race_era=RACE_ERA_2005,
        interview=("ER47302", "2011 FAMILY INTERVIEW (ID) NUMBER"),
        hispanic={
            "head": ("ER51903", "L39 SPANISH DESCENT-HEAD"),
            "spouse": ("ER51809", "K39 SPANISH DESCENT-WIFE"),
        },
        race={
            "head": (
                ("ER51904", "L40 RACE OF HEAD-MENTION 1"),
                ("ER51905", "L40 RACE OF HEAD-MENTION 2"),
                ("ER51906", "L40 RACE OF HEAD-MENTION 3"),
                ("ER51907", "L40 RACE OF HEAD-MENTION 4"),
            ),
            "spouse": (
                ("ER51810", "K40 RACE OF WIFE-MENTION 1"),
                ("ER51811", "K40 RACE OF WIFE-MENTION 2"),
                ("ER51812", "K40 RACE OF WIFE-MENTION 3"),
                ("ER51813", "K40 RACE OF WIFE-MENTION 4"),
            ),
        },
        completed_education={
            "head": ("ER52405", "COMPLETED ED-HD"),
            "spouse": ("ER52406", "COMPLETED ED-WF"),
        },
    ),
    2013: FamilyWaveItems(
        wave=2013,
        race_era=RACE_ERA_2005,
        interview=("ER53002", "2013 FAMILY INTERVIEW (ID) NUMBER"),
        hispanic={
            "head": ("ER57658", "L39 SPANISH DESCENT-HEAD"),
            "spouse": ("ER57548", "K39 SPANISH DESCENT-WIFE"),
        },
        race={
            "head": (
                ("ER57659", "L40 RACE OF HEAD-MENTION 1"),
                ("ER57660", "L40 RACE OF HEAD-MENTION 2"),
                ("ER57661", "L40 RACE OF HEAD-MENTION 3"),
                ("ER57662", "L40 RACE OF HEAD-MENTION 4"),
            ),
            "spouse": (
                ("ER57549", "K40 RACE OF WIFE-MENTION 1"),
                ("ER57550", "K40 RACE OF WIFE-MENTION 2"),
                ("ER57551", "K40 RACE OF WIFE-MENTION 3"),
                ("ER57552", "K40 RACE OF WIFE-MENTION 4"),
            ),
        },
        completed_education={
            "head": ("ER58223", "COMPLETED ED-HD"),
            "spouse": ("ER58224", "COMPLETED ED-WF"),
        },
        birth_state={
            "head": ("ER57651", "L33 STATE HEAD WAS BORN"),
            "spouse": ("ER57541", "K33 STATE WIFE WAS BORN"),
        },
        year_came={
            "head": ("ER57652", "L33YR YEAR CAME TO UNITED STATES-HD"),
            "spouse": ("ER57542", "K33YR YEAR CAME TO UNITED STATES-WF"),
        },
    ),
    2015: FamilyWaveItems(
        wave=2015,
        race_era=RACE_ERA_2005,
        interview=("ER60002", "2015 FAMILY INTERVIEW (ID) NUMBER"),
        hispanic={
            "head": ("ER64809", "L39 SPANISH DESCENT-HEAD"),
            "spouse": ("ER64670", "K39 SPANISH DESCENT-SPOUSE"),
        },
        race={
            "head": (
                ("ER64810", "L40 RACE OF HEAD-MENTION 1"),
                ("ER64811", "L40 RACE OF HEAD-MENTION 2"),
                ("ER64812", "L40 RACE OF HEAD-MENTION 3"),
                ("ER64813", "L40 RACE OF HEAD-MENTION 4"),
            ),
            "spouse": (
                ("ER64671", "K40 RACE OF SPOUSE-MENTION 1"),
                ("ER64672", "K40 RACE OF SPOUSE-MENTION 2"),
                ("ER64673", "K40 RACE OF SPOUSE-MENTION 3"),
                ("ER64674", "K40 RACE OF SPOUSE-MENTION 4"),
            ),
        },
        completed_education={
            "head": ("ER65459", "COMPLETED ED-HD"),
            "spouse": ("ER65460", "COMPLETED ED-SP"),
        },
        birth_state={
            "head": ("ER64802", "L33 STATE HEAD WAS BORN"),
            "spouse": ("ER64663", "K33 STATE SPOUSE WAS BORN"),
        },
        year_came={
            "head": ("ER64803", "L33YR YEAR CAME TO UNITED STATES-HD"),
            "spouse": ("ER64664", "K33YR YEAR CAME TO UNITED STATES-SP"),
        },
    ),
    2017: FamilyWaveItems(
        wave=2017,
        race_era=RACE_ERA_2005,
        interview=("ER66002", "2017 FAMILY INTERVIEW (ID) NUMBER"),
        hispanic={
            "head": ("ER70881", "L39 SPANISH DESCENT-RP"),
            "spouse": ("ER70743", "K39 SPANISH DESCENT-SPOUSE"),
        },
        race={
            "head": (
                ("ER70882", "L40 RACE OF REFERENCE PERSON-MENTION 1"),
                ("ER70883", "L40 RACE OF REFERENCE PERSON-MENTION 2"),
                ("ER70884", "L40 RACE OF REFERENCE PERSON-MENTION 3"),
                ("ER70885", "L40 RACE OF REFERENCE PERSON-MENTION 4"),
            ),
            "spouse": (
                ("ER70744", "K40 RACE OF SPOUSE-MENTION 1"),
                ("ER70745", "K40 RACE OF SPOUSE-MENTION 2"),
                ("ER70746", "K40 RACE OF SPOUSE-MENTION 3"),
                ("ER70747", "K40 RACE OF SPOUSE-MENTION 4"),
            ),
        },
        completed_education={
            "head": ("ER71538", "COMPLETED ED-RP"),
            "spouse": ("ER71539", "COMPLETED ED-SP"),
        },
        birth_state={
            "head": ("ER70874", "L33 STATE REFERENCE PERSON WAS BORN"),
            "spouse": ("ER70736", "K33 STATE SPOUSE WAS BORN"),
        },
        year_came={
            "head": ("ER70875", "L33YR YEAR CAME TO UNITED STATES-RP"),
            "spouse": ("ER70737", "K33YR YEAR CAME TO UNITED STATES-SP"),
        },
    ),
    2019: FamilyWaveItems(
        wave=2019,
        race_era=RACE_ERA_2005,
        interview=("ER72002", "2019 FAMILY INTERVIEW (ID) NUMBER"),
        hispanic={
            "head": ("ER76896", "L39 SPANISH DESCENT-RP"),
            "spouse": ("ER76751", "K39 SPANISH DESCENT-SPOUSE"),
        },
        race={
            "head": (
                ("ER76897", "L40 RACE OF REFERENCE PERSON-MENTION 1"),
                ("ER76898", "L40 RACE OF REFERENCE PERSON-MENTION 2"),
                ("ER76899", "L40 RACE OF REFERENCE PERSON-MENTION 3"),
                ("ER76900", "L40 RACE OF REFERENCE PERSON-MENTION 4"),
            ),
            "spouse": (
                ("ER76752", "K40 RACE OF SPOUSE-MENTION 1"),
                ("ER76753", "K40 RACE OF SPOUSE-MENTION 2"),
                ("ER76754", "K40 RACE OF SPOUSE-MENTION 3"),
                ("ER76755", "K40 RACE OF SPOUSE-MENTION 4"),
            ),
        },
        completed_education={
            "head": ("ER77599", "COMPLETED ED-RP"),
            "spouse": ("ER77600", "COMPLETED ED-SP"),
        },
        birth_state={
            "head": ("ER76889", "L33 STATE REFERENCE PERSON WAS BORN"),
            "spouse": ("ER76744", "K33 STATE SPOUSE WAS BORN"),
        },
        year_came={
            "head": ("ER76890", "L33YR YEAR CAME TO UNITED STATES-RP"),
            "spouse": ("ER76745", "K33YR YEAR CAME TO UNITED STATES-SP"),
        },
    ),
    2021: FamilyWaveItems(
        wave=2021,
        race_era=RACE_ERA_2005,
        interview=("ER78002", "2021 FAMILY INTERVIEW (ID) NUMBER"),
        hispanic={
            "head": ("ER81143", "L39 SPANISH DESCENT-RP"),
            "spouse": ("ER81016", "K39 SPANISH DESCENT-SPOUSE"),
        },
        race={
            "head": (
                ("ER81144", "L40 RACE OF REFERENCE PERSON-MENTION 1"),
                ("ER81145", "L40 RACE OF REFERENCE PERSON-MENTION 2"),
                ("ER81146", "L40 RACE OF REFERENCE PERSON-MENTION 3"),
                ("ER81147", "L40 RACE OF REFERENCE PERSON-MENTION 4"),
            ),
            "spouse": (
                ("ER81017", "K40 RACE OF SPOUSE-MENTION 1"),
                ("ER81018", "K40 RACE OF SPOUSE-MENTION 2"),
                ("ER81019", "K40 RACE OF SPOUSE-MENTION 3"),
                ("ER81020", "K40 RACE OF SPOUSE-MENTION 4"),
            ),
        },
        completed_education={
            "head": ("ER81926", "COMPLETED ED-RP"),
            "spouse": ("ER81927", "COMPLETED ED-SP"),
        },
        birth_state={
            "head": ("ER81136", "L33 STATE REFERENCE PERSON WAS BORN"),
            "spouse": ("ER81009", "K33 STATE SPOUSE WAS BORN"),
        },
        year_came={
            "head": ("ER81137", "L33YR YEAR CAME TO UNITED STATES-RP"),
            "spouse": ("ER81010", "K33YR YEAR CAME TO UNITED STATES-SP"),
        },
    ),
    2023: FamilyWaveItems(
        wave=2023,
        race_era=RACE_ERA_2005,
        interview=("ER82002", "2023 FAMILY INTERVIEW (ID) NUMBER"),
        hispanic={
            "head": ("ER85120", "L39 SPANISH DESCENT-RP"),
            "spouse": ("ER84993", "K39 SPANISH DESCENT-SPOUSE"),
        },
        race={
            "head": (
                ("ER85121", "L40 RACE OF REFERENCE PERSON-MENTION 1"),
                ("ER85122", "L40 RACE OF REFERENCE PERSON-MENTION 2"),
                ("ER85123", "L40 RACE OF REFERENCE PERSON-MENTION 3"),
                ("ER85124", "L40 RACE OF REFERENCE PERSON-MENTION 4"),
            ),
            "spouse": (
                ("ER84994", "K40 RACE OF SPOUSE-MENTION 1"),
                ("ER84995", "K40 RACE OF SPOUSE-MENTION 2"),
                ("ER84996", "K40 RACE OF SPOUSE-MENTION 3"),
                ("ER84997", "K40 RACE OF SPOUSE-MENTION 4"),
            ),
        },
        completed_education={
            "head": ("ER85780", "COMPLETED ED-RP"),
            "spouse": ("ER85781", "COMPLETED ED-SP"),
        },
        birth_state={
            "head": ("ER85113", "L33 STATE REFERENCE PERSON WAS BORN"),
            "spouse": ("ER84986", "K33 STATE SPOUSE WAS BORN"),
        },
        year_came={
            "head": ("ER85114", "L33YR YEAR CAME TO UNITED STATES-RP"),
            "spouse": ("ER84987", "K33YR YEAR CAME TO UNITED STATES-SP"),
        },
    ),
}


#: The adjudicated individual-file roster and education variables, wave
#: by wave (ind2023er; one exact label match per item and wave, 2026-10-01).
INDIVIDUAL_ITEMS: dict[int, IndividualWaveItems] = {
    1985: IndividualWaveItems(
        wave=1985,
        interview=("ER30463", "1985 INTERVIEW NUMBER"),
        sequence=("ER30464", "SEQUENCE NUMBER 85"),
        relationship=("ER30465", "RELATIONSHIP TO HEAD 85"),
        education=("ER30478", "COMPLETED EDUCATION 85"),
    ),
    1986: IndividualWaveItems(
        wave=1986,
        interview=("ER30498", "1986 INTERVIEW NUMBER"),
        sequence=("ER30499", "SEQUENCE NUMBER 86"),
        relationship=("ER30500", "RELATIONSHIP TO HEAD 86"),
        education=("ER30513", "COMPLETED EDUCATION 86"),
    ),
    1987: IndividualWaveItems(
        wave=1987,
        interview=("ER30535", "1987 INTERVIEW NUMBER"),
        sequence=("ER30536", "SEQUENCE NUMBER 87"),
        relationship=("ER30537", "RELATIONSHIP TO HEAD 87"),
        education=("ER30549", "COMPLETED EDUCATION 87"),
    ),
    1988: IndividualWaveItems(
        wave=1988,
        interview=("ER30570", "1988 INTERVIEW NUMBER"),
        sequence=("ER30571", "SEQUENCE NUMBER 88"),
        relationship=("ER30572", "RELATION TO HEAD 88"),
        education=("ER30584", "COMPLETED EDUC-IND 88"),
    ),
    1989: IndividualWaveItems(
        wave=1989,
        interview=("ER30606", "1989 INTERVIEW NUMBER"),
        sequence=("ER30607", "SEQUENCE NUMBER 89"),
        relationship=("ER30608", "RELATION TO HEAD 89"),
        education=("ER30620", "COMPLETED EDUC-IND 89"),
    ),
    1990: IndividualWaveItems(
        wave=1990,
        interview=("ER30642", "1990 INTERVIEW NUMBER"),
        sequence=("ER30643", "SEQUENCE NUMBER 90"),
        relationship=("ER30644", "RELATION TO HEAD 90"),
        education=("ER30657", "COMPLETED EDUC-IND 90"),
    ),
    1991: IndividualWaveItems(
        wave=1991,
        interview=("ER30689", "1991 INTERVIEW NUMBER"),
        sequence=("ER30690", "SEQUENCE NUMBER 91"),
        relationship=("ER30691", "RELATION TO HEAD 91"),
        education=("ER30703", "COMPLETED EDUC-IND 91"),
    ),
    1992: IndividualWaveItems(
        wave=1992,
        interview=("ER30733", "1992 INTERVIEW NUMBER"),
        sequence=("ER30734", "SEQUENCE NUMBER 92"),
        relationship=("ER30735", "RELATION TO HEAD 92"),
        education=("ER30748", "COMPLETED EDUCATION 92"),
    ),
    1993: IndividualWaveItems(
        wave=1993,
        interview=("ER30806", "1993 INTERVIEW NUMBER"),
        sequence=("ER30807", "SEQUENCE NUMBER 93"),
        relationship=("ER30808", "RELATION TO HEAD 93"),
        education=("ER30820", "YRS COMPLETED EDUCATION 93"),
    ),
    1994: IndividualWaveItems(
        wave=1994,
        interview=("ER33101", "1994 INTERVIEW NUMBER"),
        sequence=("ER33102", "SEQUENCE NUMBER 94"),
        relationship=("ER33103", "RELATION TO HEAD 94"),
        education=("ER33115", "YRS COMPLETED EDUC 94"),
    ),
    1995: IndividualWaveItems(
        wave=1995,
        interview=("ER33201", "1995 INTERVIEW NUMBER"),
        sequence=("ER33202", "SEQUENCE NUMBER 95"),
        relationship=("ER33203", "RELATION TO HEAD 95"),
        education=("ER33215", "YEARS COMPLETED EDUCATION 95"),
    ),
    1996: IndividualWaveItems(
        wave=1996,
        interview=("ER33301", "1996 INTERVIEW NUMBER"),
        sequence=("ER33302", "SEQUENCE NUMBER 96"),
        relationship=("ER33303", "RELATION TO HEAD 96"),
        education=("ER33315", "YEARS COMPLETED EDUCATION 96"),
    ),
    1997: IndividualWaveItems(
        wave=1997,
        interview=("ER33401", "1997 INTERVIEW NUMBER"),
        sequence=("ER33402", "SEQUENCE NUMBER 97"),
        relationship=("ER33403", "RELATION TO HEAD 97"),
        education=("ER33415", "YEARS COMPLETED EDUCATION 97"),
    ),
    1999: IndividualWaveItems(
        wave=1999,
        interview=("ER33501", "1999 INTERVIEW NUMBER"),
        sequence=("ER33502", "SEQUENCE NUMBER 99"),
        relationship=("ER33503", "RELATION TO HEAD 99"),
        education=("ER33516", "YEARS COMPLETED EDUCATION 99"),
    ),
    2001: IndividualWaveItems(
        wave=2001,
        interview=("ER33601", "2001 INTERVIEW NUMBER"),
        sequence=("ER33602", "SEQUENCE NUMBER 01"),
        relationship=("ER33603", "RELATION TO HEAD 01"),
        education=("ER33616", "YEARS COMPLETED EDUCATION 01"),
    ),
    2003: IndividualWaveItems(
        wave=2003,
        interview=("ER33701", "2003 INTERVIEW NUMBER"),
        sequence=("ER33702", "SEQUENCE NUMBER 03"),
        relationship=("ER33703", "RELATION TO HEAD 03"),
        education=("ER33716", "YEARS COMPLETED EDUCATION 03"),
    ),
    2005: IndividualWaveItems(
        wave=2005,
        interview=("ER33801", "2005 INTERVIEW NUMBER"),
        sequence=("ER33802", "SEQUENCE NUMBER 05"),
        relationship=("ER33803", "RELATION TO HEAD 05"),
        education=("ER33817", "YEARS COMPLETED EDUCATION 05"),
    ),
    2007: IndividualWaveItems(
        wave=2007,
        interview=("ER33901", "2007 INTERVIEW NUMBER"),
        sequence=("ER33902", "SEQUENCE NUMBER 07"),
        relationship=("ER33903", "RELATION TO HEAD 07"),
        education=("ER33917", "YEARS COMPLETED EDUCATION 07"),
    ),
    2009: IndividualWaveItems(
        wave=2009,
        interview=("ER34001", "2009 INTERVIEW NUMBER"),
        sequence=("ER34002", "SEQUENCE NUMBER 09"),
        relationship=("ER34003", "RELATION TO HEAD 09"),
        education=("ER34020", "YEARS COMPLETED EDUCATION 09"),
    ),
    2011: IndividualWaveItems(
        wave=2011,
        interview=("ER34101", "2011 INTERVIEW NUMBER"),
        sequence=("ER34102", "SEQUENCE NUMBER 11"),
        relationship=("ER34103", "RELATION TO HEAD 11"),
        education=("ER34119", "YEARS COMPLETED EDUCATION 11"),
    ),
    2013: IndividualWaveItems(
        wave=2013,
        interview=("ER34201", "2013 INTERVIEW NUMBER"),
        sequence=("ER34202", "SEQUENCE NUMBER 13"),
        relationship=("ER34203", "RELATION TO HEAD 13"),
        education=("ER34230", "YEARS COMPLETED EDUCATION 13"),
    ),
    2015: IndividualWaveItems(
        wave=2015,
        interview=("ER34301", "2015 INTERVIEW NUMBER"),
        sequence=("ER34302", "SEQUENCE NUMBER 15"),
        relationship=("ER34303", "RELATION TO HEAD 15"),
        education=("ER34349", "YEARS COMPLETED EDUCATION 15"),
    ),
    2017: IndividualWaveItems(
        wave=2017,
        interview=("ER34501", "2017 INTERVIEW NUMBER"),
        sequence=("ER34502", "SEQUENCE NUMBER 17"),
        relationship=("ER34503", "RELATION TO REFERENCE PERSON 17"),
        education=("ER34548", "YEARS COMPLETED EDUCATION 17"),
    ),
    2019: IndividualWaveItems(
        wave=2019,
        interview=("ER34701", "2019 INTERVIEW NUMBER"),
        sequence=("ER34702", "SEQUENCE NUMBER 19"),
        relationship=("ER34703", "RELATION TO REFERENCE PERSON 19"),
        education=("ER34752", "YEARS COMPLETED EDUCATION 19"),
    ),
    2021: IndividualWaveItems(
        wave=2021,
        interview=("ER34901", "2021 INTERVIEW NUMBER"),
        sequence=("ER34902", "SEQUENCE NUMBER 21"),
        relationship=("ER34903", "RELATION TO REFERENCE PERSON 21"),
        education=("ER34952", "YEARS COMPLETED EDUCATION 21"),
    ),
    2023: IndividualWaveItems(
        wave=2023,
        interview=("ER35101", "2023 INTERVIEW NUMBER"),
        sequence=("ER35102", "SEQUENCE NUMBER 23"),
        relationship=("ER35103", "RELATION TO REFERENCE PERSON 23"),
        education=("ER35152", "YEARS COMPLETED EDUCATION 23"),
    ),
}


def _relationship_prefixes(wave: int) -> dict[int, tuple[str, ...]]:
    """Accepted label prefixes of the role codes in a wave's format."""

    return {
        HEAD_RELATIONSHIP: (
            f"head in {wave}",
            f"reference person in {wave}",
        ),
        20: (f"legal wife in {wave}", f"legal spouse in {wave}"),
        22: ('"wife"--', "partner--"),
    }


#: The individual-file education code frame per wave, as
#: IND2023ER_formats.sas documents it (1-17 the grade completed, 98 DK and
#: 99 NA where present, 0 Inap.); verified at read time.
def _expected_education_domain(wave: int) -> CodeDomain:
    singles = {0, 99} if (wave <= 1993 or wave >= 2013) else {0, 98, 99}
    return CodeDomain(codes=frozenset(singles), ranges=((1, 17),))


# --------------------------------------------------------------------------
# Documented code domains
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class CodeDomain:
    """The codes a variable documents: single codes plus closed ranges."""

    codes: frozenset[int]
    ranges: tuple[tuple[int, int], ...] = ()

    def __post_init__(self) -> None:
        for code in self.codes:
            _integer_code(code)
        for lo, hi in self.ranges:
            _integer_code(lo)
            _integer_code(hi)
            if lo > hi:
                raise ValueError(f"code-domain range {lo}-{hi} is reversed")

    def contains(self, value: int) -> bool:
        value = _integer_code(value)
        if value in self.codes:
            return True
        return any(lo <= value <= hi for lo, hi in self.ranges)

    def undocumented(self, values: Iterable[Any]) -> list[int]:
        """Sorted distinct values the domain does not document."""
        seen = {_integer_code(v) for v in values if not pd.isna(v)}
        return sorted(v for v in seen if not self.contains(v))

    def normalized(self) -> tuple[frozenset[int], tuple[tuple[int, int], ...]]:
        """Merge adjacent singles into ranges for a canonical comparison."""
        values = set(self.codes)
        for lo, hi in self.ranges:
            values.update(range(lo, hi + 1))
        return frozenset(values), ()

    def same_as(self, other: CodeDomain) -> bool:
        return self.normalized() == other.normalized()

    @classmethod
    def from_values(cls, entries: Iterable[Mapping[str, Any]]) -> CodeDomain:
        codes: set[int] = set()
        ranges: list[tuple[int, int]] = []
        for entry in entries:
            if "range" in entry:
                lo, hi = entry["range"]
                ranges.append((int(lo), int(hi)))
            else:
                codes.add(int(entry["code"]))
        return cls(codes=frozenset(codes), ranges=tuple(sorted(ranges)))


def _integer_code(value: Any) -> int:
    """Refuse noninteger codes before a coercion can change their meaning."""
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError(f"PSID code {value!r} is not a finite integer")
    return int(value)


_REPO_ROOT = Path(__file__).resolve().parents[3]
#: The committed codebook value tables (generator:
#: ``scripts/build_group_attribute_codebook_values.py``).
CODEBOOK_VALUES_PATH = (
    _REPO_ROOT
    / "data"
    / "external"
    / "psid_group_attribute_codebook_values_v1.json"
)
#: SHA-256 of the committed table; a different file is refused.
CODEBOOK_VALUES_SHA256 = (
    "09fce5627b0271a68eadb2e8748e33fe1ff3e6b0e025bfef9575bb2804ebef63"
)


def load_codebook_values(path: Path | None = None) -> dict[str, Any]:
    """Load the committed codebook value tables, refusing a changed file.

    With ``path`` given (tests), the SHA-256 pin is not applied.
    """

    target = CODEBOOK_VALUES_PATH if path is None else Path(path)
    raw = target.read_bytes()
    if path is None:
        digest = hashlib.sha256(raw).hexdigest()
        if digest != CODEBOOK_VALUES_SHA256:
            raise ValueError(
                f"{target} has SHA-256 {digest}, expected the pinned "
                f"{CODEBOOK_VALUES_SHA256}; regenerate the table with "
                "scripts/build_group_attribute_codebook_values.py and "
                "re-adjudicate before changing the pin."
            )
    data = json.loads(raw)
    if data.get("schema_version") != "psid_group_attribute_codebook.v1":
        raise ValueError(f"{target} is not a v1 codebook value table")
    return data


def documented_domain(
    codebook: Mapping[str, Any], wave: int, variable: str
) -> CodeDomain:
    """The codes ``variable`` documents in ``wave``'s family codebook."""

    try:
        entry = codebook["family"][str(wave)]["variables"][variable]
    except KeyError as exc:
        raise KeyError(
            f"wave {wave} variable {variable} has no codebook value table"
        ) from exc
    return CodeDomain.from_values(entry["values"])


@cache
def _semantic_codebook() -> dict[str, Any]:
    """Pinned documentation shared by pure semantic domain checks."""
    return load_codebook_values()


@cache
def _semantic_domain(wave: int, variable: str) -> CodeDomain:
    return documented_domain(_semantic_codebook(), wave, variable)


def _require_semantic_code(wave: int, variable: str, code: Any) -> int:
    value = _integer_code(code)
    if not _semantic_domain(wave, variable).contains(value):
        raise ValueError(
            f"undocumented code {value} for wave {wave} {variable}"
        )
    return value


_SAS_VALUE_HEADER = re.compile(r"^\s*VALUE\s+(\S+)\s*$")
_SAS_VALUE_LINE = re.compile(r"^\s*(-?\d+)(?:\s*-\s*(-?\d+))?\s*=\s*'")
_SAS_BLOCK_END = re.compile(r"^\s*;\s*$")


def parse_sas_value_domains(path: str | Path) -> dict[str, CodeDomain]:
    """``{format name: CodeDomain}`` from a PSID SAS formats file.

    Unlike :func:`populace_dynamics.data.disability.parse_sas_value_labels`
    this keeps ranges (``1 - 17 = '...'``), which the education and
    birthplace items use; continuation lines of long labels are skipped,
    and each block ends at a line holding only ``;``.
    """

    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"PSID SAS formats file not found: {path}")
    out: dict[str, CodeDomain] = {}
    name: str | None = None
    codes: set[int] = set()
    ranges: list[tuple[int, int]] = []
    for line in path.read_text(errors="replace").splitlines():
        header = _SAS_VALUE_HEADER.match(line)
        if header:
            if name is not None or header.group(1) in out:
                raise ValueError(
                    f"Malformed or duplicate VALUE block in {path}"
                )
            name, codes, ranges = header.group(1), set(), []
            continue
        if name is None:
            continue
        if _SAS_BLOCK_END.match(line):
            out[name] = CodeDomain(
                codes=frozenset(codes), ranges=tuple(sorted(ranges))
            )
            name = None
            continue
        value = _SAS_VALUE_LINE.match(line)
        if value:
            lo = int(value.group(1))
            if value.group(2) is None:
                codes.add(lo)
            else:
                ranges.append((lo, int(value.group(2))))
    if name is not None:
        raise ValueError(f"Unterminated VALUE block {name} in {path}")
    if not out:
        raise ValueError(f"No VALUE block found in {path}")
    return out


def _format_domain(
    domains: Mapping[str, CodeDomain],
    assignments: Mapping[str, str],
    variable: str,
) -> CodeDomain | None:
    return domains.get(assignments.get(variable, f"{variable}F"))


def _sas_value_labels(path: Path, fmt: str) -> dict[int, str]:
    """Single-code labels of one SAS format block (for prefix checks)."""

    labels: dict[int, str] = {}
    inside = False
    for line in path.read_text(errors="replace").splitlines():
        header = _SAS_VALUE_HEADER.match(line)
        if header:
            inside = header.group(1) == fmt
            continue
        if not inside:
            continue
        if _SAS_BLOCK_END.match(line):
            break
        match = re.match(r"^\s*(-?\d+)\s*=\s*'((?:[^']|'')*)'", line)
        if match:
            labels[int(match.group(1))] = match.group(2).replace("''", "'")
    return labels


def _check_codes(
    values: pd.Series, domain: CodeDomain, *, context: str
) -> None:
    if values.isna().any():
        raise ValueError(f"{context}: blank codes are not documented")
    bad = domain.undocumented(values.unique())
    if bad:
        raise ValueError(
            f"{context}: codes {bad[:10]} are not documented "
            f"(documented: singles {sorted(domain.codes)}, ranges "
            f"{list(domain.ranges)}). The release may have changed; "
            "re-adjudicate before reading."
        )


# --------------------------------------------------------------------------
# Readers
# --------------------------------------------------------------------------
def _individual_formats_path(data_dir: Path | None) -> Path:
    return disability.employment_status_formats_path(data_dir)


def verify_individual_formats(
    *,
    data_dir: Path | None = None,
    waves: tuple[int, ...] = INDIVIDUAL_WAVES,
) -> dict[int, dict[str, str]]:
    """Check each wave's education and relationship formats.

    The education format must document exactly the expected frame
    (:func:`_expected_education_domain`); relationship codes 10, 20 and
    22 must carry the head, legal wife/spouse and partner labels.
    Returns ``{wave: {variable: format}}`` for the verified items.
    """

    path = _individual_formats_path(data_dir)
    domains = parse_sas_value_domains(path)
    assignments = disability.parse_sas_format_assignments(path)
    out: dict[int, dict[str, str]] = {}
    for wave in waves:
        items = INDIVIDUAL_ITEMS[wave]
        edu_var = items.education[0]
        edu_fmt = assignments.get(edu_var, f"{edu_var}F")
        documented = domains.get(edu_fmt)
        expected = _expected_education_domain(wave)
        if documented is None or not documented.same_as(expected):
            raise ValueError(
                f"wave {wave}: {edu_var} format {edu_fmt} documents "
                f"{documented}, expected {expected}"
            )
        rel_var = items.relationship[0]
        rel_fmt = assignments.get(rel_var, f"{rel_var}F")
        rel_labels = _sas_value_labels(path, rel_fmt)
        for code, prefixes in _relationship_prefixes(wave).items():
            label = " ".join(rel_labels.get(code, "").lower().split())
            if not label.startswith(prefixes):
                raise ValueError(
                    f"wave {wave}: relationship code {code} in {rel_fmt} "
                    f"is {label!r}, expected a label starting with one of "
                    f"{prefixes}"
                )
        out[wave] = {edu_var: edu_fmt, rel_var: rel_fmt}
    return out


def read_individual_items(
    *,
    data_dir: Path | None = None,
    waves: tuple[int, ...] = INDIVIDUAL_WAVES,
    nrows: int | None = None,
) -> pd.DataFrame:
    """Read the per-wave roster and education codes, long by wave.

    Columns: ``person_id``, ``wave``, ``interview``, ``sequence``,
    ``relationship``, ``education_code`` (raw, verified against the
    wave's documented frame). Every person appears once per wave in
    ``waves``; presence filtering is the caller's.
    """

    unknown = [w for w in waves if w not in INDIVIDUAL_ITEMS]
    if unknown:
        raise ValueError(f"waves {unknown} have no adjudicated layout")
    if not waves or len(set(waves)) != len(waves):
        raise ValueError("waves must be nonempty and distinct")
    labels = psid.parse_sps_labels(
        psid.product_sps_path("ind2023er", data_dir)
    )
    expected = dict(_PERSON_VARS)
    for wave in waves:
        expected.update(INDIVIDUAL_ITEMS[wave].labels())
    psid.verify_labels(labels, expected, context="ind2023er group attributes")
    verify_individual_formats(data_dir=data_dir, waves=tuple(waves))
    formats_path = _individual_formats_path(data_dir)
    format_domains = parse_sas_value_domains(formats_path)
    format_assignments = disability.parse_sas_format_assignments(formats_path)
    raw = psid.read_psid(
        "ind2023er", columns=list(expected), data_dir=data_dir, nrows=nrows
    )
    person_id = raw["ER30001"].astype("int64") * 1000 + raw["ER30002"].astype(
        "int64"
    )
    frames = []
    for wave in waves:
        items = INDIVIDUAL_ITEMS[wave]
        for var, _ in (items.sequence, items.relationship):
            domain = _format_domain(format_domains, format_assignments, var)
            if domain is None:
                raise ValueError(f"wave {wave}: {var} has no format domain")
            _check_codes(raw[var], domain, context=f"ind2023er {var} ({wave})")
        _check_codes(
            raw[items.education[0]],
            _expected_education_domain(wave),
            context=f"ind2023er {items.education[0]} ({wave})",
        )
        frames.append(
            pd.DataFrame(
                {
                    "person_id": person_id,
                    "wave": wave,
                    "interview": raw[items.interview[0]].astype("int64"),
                    "sequence": raw[items.sequence[0]].astype("int64"),
                    "relationship": raw[items.relationship[0]].astype("int64"),
                    "education_code": raw[items.education[0]].astype("int64"),
                }
            )
        )
    return pd.concat(frames, ignore_index=True)


def _family_formats_path(wave: int, data_dir: Path | None) -> Path | None:
    base = psid._resolve_data_dir(data_dir) / "family" / str(wave)
    hits = sorted(base.glob("*_formats.sas"))
    if len(hits) > 1:
        raise ValueError(f"family {wave}: multiple SAS formats files found")
    return hits[0] if hits else None


def read_family_items(
    wave: int,
    *,
    data_dir: Path | None = None,
    codebook: Mapping[str, Any] | None = None,
    nrows: int | None = None,
) -> pd.DataFrame:
    """Read one family wave's group-attribute codes, one row per family.

    Columns: ``interview`` plus, for each role, the wave's items under
    ``<variable>`` names (the raw PSID names; :func:`head_spouse_reports`
    maps them to generic columns). Every label is verified first, and
    every observed code must be documented by the wave's codebook value
    table; where a formats file exists (2021, 2023), each item's format
    block, when it has one, must document the same codes.
    """

    if wave not in FAMILY_ITEMS:
        raise ValueError(f"wave {wave} has no adjudicated family layout")
    codebook = load_codebook_values() if codebook is None else codebook
    items = FAMILY_ITEMS[wave]
    sps_path, txt_path = family._family_paths(wave, data_dir)
    labels = psid.parse_sps_labels(sps_path)
    expected = items.labels()
    psid.verify_labels(labels, expected, context=f"family {wave}")
    formats_path = _family_formats_path(wave, data_dir)
    if formats_path is not None:
        domains = parse_sas_value_domains(formats_path)
        assignments = disability.parse_sas_format_assignments(formats_path)
    names = list(expected)
    layout = psid.parse_sps_layout(sps_path).set_index("name")
    colspecs = [
        (int(layout.loc[n, "start"]) - 1, int(layout.loc[n, "end"]))
        for n in names
    ]
    raw = pd.read_fwf(
        txt_path, colspecs=colspecs, names=names, header=None, nrows=nrows
    )
    interview_var = items.interview[0]
    for var in names:
        if var == interview_var:
            continue
        domain = documented_domain(codebook, wave, var)
        if formats_path is not None:
            fmt_domain = _format_domain(domains, assignments, var)
            if fmt_domain is not None and not fmt_domain.same_as(domain):
                raise ValueError(
                    f"family {wave} {var}: the formats file documents "
                    f"{fmt_domain}, the codebook {domain}"
                )
        _check_codes(raw[var], domain, context=f"family {wave} {var}")
    out = raw.rename(columns={interview_var: "interview"})
    if out["interview"].duplicated().any():
        raise ValueError(f"family {wave}: duplicate interview numbers")
    return out.astype("int64")


def verify_codebook_pins(
    waves: Iterable[int],
    *,
    data_dir: Path | None = None,
    codebook: Mapping[str, Any] | None = None,
) -> dict[int, str]:
    """Check each wave's staged codebook PDF against the table's pin.

    The code meanings were adjudicated from these exact PDFs; a changed
    PDF means the documentation moved and the table must be rebuilt.
    Returns ``{wave: sha256}``.
    """

    codebook = load_codebook_values() if codebook is None else codebook
    root = psid._resolve_data_dir(data_dir)
    out: dict[int, str] = {}
    for wave in waves:
        source = codebook["family"][str(wave)]
        entry = source["codebook"]
        path = root / entry["path"]
        if not path.is_file():
            raise FileNotFoundError(
                f"codebook {path} is not staged; the code meanings for "
                f"wave {wave} cannot be checked against their source"
            )
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != entry["sha256"]:
            raise ValueError(
                f"codebook {path} has SHA-256 {digest}, the value table "
                f"pins {entry['sha256']}"
            )
        out[wave] = digest
        formats = source.get("formats_sas")
        if formats is not None:
            format_path = root / formats["path"]
            if not format_path.is_file():
                raise FileNotFoundError(
                    f"pinned formats file missing: {format_path}"
                )
            format_digest = hashlib.sha256(
                format_path.read_bytes()
            ).hexdigest()
            if format_digest != formats["sha256"]:
                raise ValueError(
                    f"formats {format_path} has SHA-256 {format_digest}, "
                    f"the value table pins {formats['sha256']}"
                )
    return out


#: Generic columns of a head/spouse report, in order.
REPORT_CODE_COLUMNS: tuple[str, ...] = (
    "hispanic_code",
    "race_code_1",
    "race_code_2",
    "race_code_3",
    "race_code_4",
    "family_education_code",
    "birth_state_code",
    "year_came_code",
)


def head_spouse_reports(
    individual: pd.DataFrame, family_items: Mapping[int, pd.DataFrame]
) -> pd.DataFrame:
    """Attach each wave's family codes to its present head and spouse.

    A person reports in a wave when present (sequence 1-20) with
    relationship 10 (head) or 20/22 (spouse); the family row joins on the
    wave's interview number. Columns: ``person_id``, ``wave``, ``role``
    and :data:`REPORT_CODE_COLUMNS` (nullable ``Int64``; NA where the
    wave does not carry the item). Refuses a present head or spouse
    whose family row is missing, and a family with two heads or two
    spouses.
    """

    lo, hi = IN_FAMILY_SEQUENCE
    # The long roster contains a full person frame for each wave. Partition
    # it once so presence masks scan each wave only, rather than rescanning
    # all person-waves for every family file. Positional indices preserve
    # the input's row order and labels, including nonconsecutive indices.
    wave_positions = individual.groupby("wave", sort=False).indices
    frames = []
    for wave in sorted(family_items):
        items = FAMILY_ITEMS[wave]
        positions = wave_positions.get(wave)
        wave_people = (
            individual.iloc[positions]
            if positions is not None
            else individual.iloc[0:0]
        )
        people = wave_people[wave_people["sequence"].between(lo, hi)]
        roles = pd.Series(pd.NA, index=people.index, dtype="string")
        roles[people["relationship"] == HEAD_RELATIONSHIP] = "head"
        roles[people["relationship"].isin(SPOUSE_RELATIONSHIPS)] = "spouse"
        people = people.assign(role=roles).dropna(subset=["role"])
        dup = people.duplicated(["interview", "role"], keep=False)
        if dup.any():
            raise ValueError(
                f"wave {wave}: {int(dup.sum())} present persons share a "
                "family's head or spouse role"
            )
        fam = family_items[wave]
        missing = set(people["interview"]) - set(fam["interview"])
        if missing:
            raise ValueError(
                f"wave {wave}: {len(missing)} present heads/spouses have "
                "no family-file row"
            )
        merged = people.merge(fam, on="interview", how="left")
        for role in ROLES:
            part = merged[merged["role"] == role]
            columns = items.role_columns(role)
            report = pd.DataFrame(
                {
                    "person_id": part["person_id"].astype("int64"),
                    "wave": wave,
                    "role": role,
                }
            )
            for column in REPORT_CODE_COLUMNS:
                report[column] = pd.array([pd.NA] * len(part), dtype="Int64")
            for var, column in columns.items():
                report[column] = part[var].astype("Int64").to_numpy()
            frames.append(report)
    if not frames:
        return pd.DataFrame(
            columns=["person_id", "wave", "role", *REPORT_CODE_COLUMNS]
        )
    out = pd.concat(frames, ignore_index=True)
    out["role"] = out["role"].astype("string")
    for column in REPORT_CODE_COLUMNS:
        out[column] = out[column].astype("Int64")
    return out.sort_values(["person_id", "wave"]).reset_index(drop=True)


# --------------------------------------------------------------------------
# Meanings (pure)
# --------------------------------------------------------------------------
def hispanic_meaning(code: int) -> str:
    """Meaning of a Spanish-descent code (:data:`HISPANIC_CODE_MEANINGS`)."""

    try:
        return HISPANIC_CODE_MEANINGS[_integer_code(code)]
    except KeyError as exc:
        raise ValueError(f"undocumented Spanish-descent code {code}") from exc


def race_mention_meaning(wave: int, mention: int, code: int) -> str:
    """Meaning of race ``mention`` (1-based) code ``code`` in ``wave``."""

    era = FAMILY_ITEMS[wave].race_era
    if not isinstance(mention, Integral) or isinstance(mention, bool):
        raise ValueError(f"race mention {mention!r} is not an integer")
    if not 1 <= mention <= len(FAMILY_ITEMS[wave].race["head"]):
        raise ValueError(f"wave {wave}: undocumented race mention {mention}")
    try:
        meaning = RACE_CODE_MEANINGS[era][_integer_code(code)]
    except KeyError as exc:
        raise ValueError(
            f"undocumented race code {code} (wave {wave}, era {era})"
        ) from exc
    if mention == 1 and meaning == NO_FURTHER_MENTION:
        return MISSING
    return meaning


@dataclass(frozen=True)
class RaceEthnicityReport:
    """One head/spouse report's race and Hispanic origin, harmonized.

    ``hispanic`` is True/False, or None when the report cannot tell.
    ``races`` is the ordered, distinct race categories mentioned (Latino
    origin mentions excluded; they are an ethnicity answer to the race
    question), or None when any mention is missing or none names a race.
    ``hispanic_basis`` is ``"direct_question"`` (a Spanish-descent item),
    ``"latino_race_mention"`` (1997-2003: a race mention of Latino
    origin), ``"not_asked"`` (1997-2003 with no such mention) or
    ``"missing"`` (DK/NA to the direct question), or
    ``"undocumented_zero_meaning"`` (1994-1996 present spouse code 0).
    """

    hispanic: bool | None
    races: tuple[str, ...] | None
    hispanic_basis: str

    @property
    def complete(self) -> bool:
        """Whether the report fixes a four-way race/ethnicity group."""
        return self.hispanic is True or (
            self.hispanic is False and self.races is not None
        )


def race_ethnicity_report(
    wave: int,
    hispanic_code: int | None,
    race_codes: Iterable[int | None],
    *,
    role: str = "head",
) -> RaceEthnicityReport:
    """Harmonize one report's Spanish-descent and race-mention codes.

    ``hispanic_code`` must be None exactly when the wave asks no
    Spanish-descent question (1997-2003). ``race_codes`` are the wave's
    mentions in order (trailing None for mentions the wave lacks).
    Rules: where the wave asks the direct question, Hispanic origin is
    that answer alone; in 1997-2003 a Latino-origin race mention makes
    the report Hispanic and its absence leaves Hispanic origin unknown.
    ``role`` distinguishes a present spouse's ambiguous 1994-1996
    Spanish-descent code 0: its codebook text names only "no wife", so
    the report leaves ethnicity unknown with basis
    ``undocumented_zero_meaning``. A missing (DK/NA/wild) mention at any
    position leaves the race set
    unknown, since the person's full set of races is then not known.
    """

    items = FAMILY_ITEMS[wave]
    if role not in ROLES:
        raise ValueError(f"undocumented family role {role!r}")
    if items.asks_hispanic_origin != (hispanic_code is not None):
        raise ValueError(
            f"wave {wave}: Spanish-descent code {hispanic_code!r} given "
            f"where asks_hispanic_origin={items.asks_hispanic_origin}"
        )
    codes = tuple(race_codes)
    mentions = items.race[role]
    if not len(mentions) <= len(codes) <= 4:
        raise ValueError(
            f"wave {wave}: expected {len(mentions)} race codes with "
            "optional unasked trailing mentions"
        )
    if any(
        code is not None and not pd.isna(code)
        for code in codes[len(mentions) :]
    ):
        raise ValueError(
            f"wave {wave}: codes supplied for unasked race mentions"
        )
    meanings = []
    for mention, (variable, _) in enumerate(mentions, start=1):
        code = _require_semantic_code(wave, variable, codes[mention - 1])
        meanings.append(race_mention_meaning(wave, mention, code))
    latino = LATINO_ORIGIN in meanings
    races: tuple[str, ...] | None
    if MISSING in meanings:
        races = None
    else:
        ordered = [
            m for m in meanings if m not in (NO_FURTHER_MENTION, LATINO_ORIGIN)
        ]
        races = tuple(dict.fromkeys(ordered)) or None
    if items.asks_hispanic_origin:
        hispanic_code = _require_semantic_code(
            wave, items.hispanic[role][0], hispanic_code
        )
        meaning = hispanic_meaning(hispanic_code)
        if role == "spouse" and 1994 <= wave <= 1996 and hispanic_code == 0:
            hispanic, basis = None, "undocumented_zero_meaning"
        else:
            hispanic = {HISPANIC: True, NOT_HISPANIC: False}.get(meaning)
            basis = "missing" if hispanic is None else "direct_question"
    elif latino:
        hispanic, basis = True, "latino_race_mention"
    else:
        hispanic, basis = None, "not_asked"
    return RaceEthnicityReport(
        hispanic=hispanic, races=races, hispanic_basis=basis
    )


def birthplace_class(birth_state_code: int, year_came_code: int) -> str:
    """Classify one report's birthplace pair (:data:`BIRTHPLACE_CLASSES`).

    A FIPS state with year-came 0 is the United States; "territory or
    foreign country" with year-came 0 ("born in the United States or U.S.
    territory") is a U.S. territory, and with any other year-came code
    (a year, "not living in the U.S." or DK/NA, all asked only of persons
    born outside the U.S. and its territories) a foreign country. DK/NA
    on the state is missing. Any other pairing contradicts the skip
    pattern and is ``inconsistent``.
    """

    state, came = _integer_code(birth_state_code), _integer_code(
        year_came_code
    )
    if came not in (0, 9997, 9998, 9999) and not 1901 <= came <= 2023:
        raise ValueError(f"undocumented year-came code {came}")
    lo, hi = BIRTH_STATE_RANGE
    born_in_us_or_territory = came == YEAR_CAME_BORN_IN_US
    if lo <= state <= hi:
        return UNITED_STATES if born_in_us_or_territory else INCONSISTENT
    if state == BIRTH_STATE_NOT_A_STATE:
        return US_TERRITORY if born_in_us_or_territory else FOREIGN_COUNTRY
    if state == BIRTH_STATE_MISSING:
        return MISSING if born_in_us_or_territory else INCONSISTENT
    raise ValueError(f"undocumented birth-state code {state}")


def education_report(
    individual_code: int, family_code: int | None = None
) -> tuple[int | None, str]:
    """Years of schooling and status from one person-wave's codes.

    ``family_code`` is the family COMPLETED ED code of the person's role
    when the person is that wave's head or spouse (1993 on), else None.
    Returns ``(years, status)``: 1-17 are ``reported``; individual 0 with
    family 0 is ``no_grades`` (0 years); 98/99 are ``missing``; any other
    individual 0 is ``inapplicable``.
    """

    code = _integer_code(individual_code)
    if family_code is not None and not pd.isna(family_code):
        family_code = _integer_code(family_code)
        if family_code not in (*range(18), FAMILY_EDUCATION_MISSING):
            raise ValueError(
                f"undocumented family education code {family_code}"
            )
    lo, hi = EDUCATION_YEARS_RANGE
    if lo <= code <= hi:
        return code, EDUCATION_REPORTED
    if code in EDUCATION_DK_NA:
        return None, EDUCATION_MISSING
    if code != 0:
        raise ValueError(f"undocumented education code {code}")
    if family_code is not None and not pd.isna(family_code):
        if int(family_code) == FAMILY_EDUCATION_NO_GRADES:
            return 0, EDUCATION_NO_GRADES
    return None, EDUCATION_INAPPLICABLE
