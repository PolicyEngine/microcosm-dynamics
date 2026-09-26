"""Label-verified year-before-last labor income, odd income years 2001-2021.

The earnings panel (:func:`populace_dynamics.data.family.family_earnings_
panel`) carries labor income for every year 1968-1996 and even years from
1998: from 1999 the PSID is biennial and the family files report last
year's income only.  The labor income of each odd year 2001-2021 was
asked one wave later of the reference person and of the spouse, as the
labor income of the year before last (R26 in 2003, R2 and R11 in
2005-2015, R2 from 2017).  The M1 specification freezes that source for
Track M's one history per worker (section 5; ``odd_year_source =
"next_wave_reference_person_and_spouse"``); plan item M3 reads it here.

Scope, verified 2026-09-25 against the staged setup files and the family
codebooks of waves 2003-2023 (:data:`_VARS`): every wave carries, for the
reference person (HD to 2015, RP from 2017) and the spouse (WF to 2013,
SP from 2015), four label-verified items: ``WTR EMPLOYED IN <y>`` (1 yes,
5 no, 9 DK/NA/RF), the amount ``R<n> LABOR INCOME <y>``, its time unit
``R<n> PER FOR LABOR INCOME <y>`` (1 hour, 2 day, 3 week, 4 two weeks, 5
month, 6 year, 7 other, 8 DK, 9 NA; refused, 0 Inap.) and ``ACCURACY OF
LABOR INCOME <y>`` (1 imputed, 0 not imputed or Inap.).  The amount's
codes (codebooks): 2003-2005, eight digits, 99,999,999 "DK; NA; refused"
(and 99,999,998 "DK" in 2003), -9,999,999 a loss of unknown amount;
2007-2023, ``F10.2``, 9,999,999.00 "DK; NA; refused" and -999,999.00 a
loss of unknown amount; a negative amount is an actual loss; 0 is
"Inap.: zero; business or farm broke even; did not work for money; DK,
NA, RF whether worked".  A DK, NA or refused amount keeps its code and
is not assigned; a few amounts carry accuracy code 1, "Imputed" (for
example 2 of the reference persons' items for 2001 and 151 for 2021, by
the codebooks' counts).

**How an item becomes an annual amount** (builder conventions, recorded
with every result, :data:`STATUSES`):

* not employed that year (``WTR EMPLOYED`` 5): observed zero;
* whether employed unknown (9): unobserved;
* employed with an amount of DK/NA: unobserved;
* employed with a loss (an actual loss or a loss of unknown amount):
  observed zero covered earnings (a net loss from all work credits no
  quarter);
* employed with a zero amount (broke even): observed zero;
* employed with a positive amount and a time unit of year: the amount;
  of month, two weeks, week, day or hour: the amount times 12, 26, 52,
  260 or 2,080 (:data:`TIME_UNIT_FACTORS`, a full-year reading of the
  time unit, a named delta); a time unit of other, DK or NA: unobserved.

**Concept against the panel's constructed totals** (M1 specification
section 5; labels and codebook text only).  Every one of the 22 amount
items asks, "Thinking now about all the work for money that (you/he/she)
did during <y>, including jobs, businesses, self-employment and
part-time work, about how much did (you/he/she) earn altogether in <y>?
Please include any income from bonuses, overtime, tips or commissions"
(checked in each wave's codebook).  The panel's constructed labor income
(for example ``LABOR INCOME OF REF PERSON-2022``, ER85496) is, by its 2023
codebook entry, the reference person's labor income "Excluding Farm and
Unincorporated Business Income": wages and salaries, bonuses, overtime,
tips, commissions, professional practice or trade, additional job and
miscellaneous labor income, with "farm income ... and the labor portion
of business income ... NOT included" and "All missing data were
assigned"; :mod:`populace_dynamics.data.family_income` found the same
exclusion on the 2005-2013 files, and :mod:`populace_dynamics.data.family`
records that the pre-1994 waves' totals included the farm and business
labor parts.  So, against the panel's years from income year 1993 on, the
year-before-last item is **not** the panel's concept: it includes farm,
business and self-employment earnings, which the constructed totals
exclude, a DK or NA amount is left unassigned (the 2023 constructed
total's entry says "All missing data were assigned"), and it carries a
time unit
(:data:`CONCEPT_DELTA`, a named delta; nothing adjusts for it).  Two
further conventions are named deltas: a sub-annual time unit is
annualized at full-year factors, although the family files also carry
the weeks employed that year (for example ER85312), which this reader
does not use; and a net loss (the item nets self-employment and business
losses against wages) is read as zero covered earnings.

**A finding outside the frozen source.**  The individual file carries a
person-level ``TOTAL ANNUAL EARNINGS IN 1997`` (ER33537N, 1999 wave),
``... IN 1999`` (ER33628N, 2001) and ``... IN 2001`` (ER33728N, 2003) for
persons aged 18 or older in the family unit ("Missing data have not been
assigned"), which :func:`populace_dynamics.data.panels.individual_
earnings_panel` reads.  The M1 specification's statement that the labor
income of 1997 and 1999 "was never asked" holds for the family files
only.  The frozen odd-year source is the family files' items; this module
does not read the individual-file series (:data:`INDIVIDUAL_FILE_ODD_YEAR_
SERIES` records it).

It reads no threshold and computes nothing; its rows are inputs to plan
item M5's one history per worker.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.data import family, psid
from populace_dynamics.data.social_security_receipt import read_wave_members

__all__ = [
    "CONCEPT_DELTA",
    "INDIVIDUAL_FILE_ODD_YEAR_SERIES",
    "ODD_INCOME_YEARS",
    "ROLES",
    "STATUSES",
    "TIME_UNIT_FACTORS",
    "annualize",
    "next_wave_histories",
    "prior_year_variables",
    "observed_statuses",
    "read_prior_year_labor_income",
]

#: The odd income years the next wave asks (2001-2021).
ODD_INCOME_YEARS: tuple[int, ...] = tuple(range(2001, 2022, 2))
ROLES: tuple[str, ...] = ("reference_person", "spouse")
#: Periods per year of each time unit (a full-year reading).
TIME_UNIT_FACTORS: dict[int, int] = {
    1: 2_080,
    2: 260,
    3: 52,
    4: 26,
    5: 12,
    6: 1,
}
_PER_UNKNOWN = (7, 8, 9)
_PER_INAP = 0
_EMPLOYED_YES, _EMPLOYED_NO, _EMPLOYED_UNKNOWN = 1, 5, 9
#: Item statuses (see the module docstring).
STATUSES: tuple[str, ...] = (
    "annual_amount",
    "not_employed",
    "loss",
    "zero_broke_even",
    "employed_unknown",
    "amount_unknown",
    "time_unit_unknown",
)
_OBSERVED_STATUSES = (
    "annual_amount",
    "not_employed",
    "loss",
    "zero_broke_even",
)
CONCEPT_DELTA = (
    "the next wave's year-before-last labor income counts all work for "
    "money, farm, business and self-employment earnings included, leaves "
    "a DK or NA amount unassigned and carries a time unit; the panel's "
    "constructed labor income excludes farm and unincorporated-business "
    "income and assigns missing data (codebook text, 2003-2023)"
)
INDIVIDUAL_FILE_ODD_YEAR_SERIES: dict[int, tuple[str, str]] = {
    1997: ("ER33537N", "TOTAL ANNUAL EARNINGS IN 1997 99"),
    1999: ("ER33628N", "TOTAL ANNUAL EARNINGS IN 1999 01"),
    2001: ("ER33728N", "TOTAL ANNUAL EARNINGS IN 2001 03"),
}


def _role(
    employed: str,
    amount: str,
    per: str,
    acc: str,
    code: str,
    item: str,
    year: int,
) -> dict[str, tuple[str, str]]:
    return {
        "employed": (employed, f"WTR EMPLOYED IN {year} ({code})"),
        "amount": (amount, f"{item} LABOR INCOME {year} ({code})"),
        "per": (per, f"{item} PER FOR LABOR INCOME {year} ({code})"),
        "acc": (acc, f"ACCURACY OF LABOR INCOME {year} ({code})"),
    }


def _wave(
    interview: str,
    head: tuple[str, str, str, str, str, str],
    spouse: tuple[str, str, str, str, str, str],
    year: int,
) -> dict[str, Any]:
    wave = year + 2
    return {
        "interview": (interview, f"{wave} FAMILY INTERVIEW (ID) NUMBER"),
        "reference_person": _role(*head, year),
        "spouse": _role(*spouse, year),
    }


#: Adjudicated variables per wave (labels read 2026-09-25 from each
#: ``FAM<wave>ER.sps``): the interview number and, for each role, the
#: whether-employed item, the amount, its time unit and its accuracy.
_VARS: dict[int, dict[str, Any]] = {
    2003: _wave(
        "ER21002",
        ("ER23702D2", "ER23702F1", "ER23702F2", "ER23702F3", "HD", "R26"),
        ("ER23702J5", "ER23702L4", "ER23702L5", "ER23702L6", "WF", "R26"),
        2001,
    ),
    2005: _wave(
        "ER25002",
        ("ER27711D2", "ER27711F1", "ER27711F2", "ER27711F3", "HD", "R2"),
        ("ER27711J5", "ER27711L4", "ER27711L5", "ER27711L6", "WF", "R11"),
        2003,
    ),
    2007: _wave(
        "ER36002",
        ("ER40686D2", "ER40686F1", "ER40686F2", "ER40686F3", "HD", "R2"),
        ("ER40686J5", "ER40686L4", "ER40686L5", "ER40686L6", "WF", "R11"),
        2005,
    ),
    2009: _wave(
        "ER42002",
        ("ER46669", "ER46673", "ER46674", "ER46675", "HD", "R2"),
        ("ER46680", "ER46684", "ER46685", "ER46686", "WF", "R11"),
        2007,
    ),
    2011: _wave(
        "ER47302",
        ("ER52070", "ER52074", "ER52075", "ER52076", "HD", "R2"),
        ("ER52081", "ER52085", "ER52086", "ER52087", "WF", "R11"),
        2009,
    ),
    2013: _wave(
        "ER53002",
        ("ER57824", "ER57841", "ER57842", "ER57843", "HD", "R2"),
        ("ER57872", "ER57889", "ER57890", "ER57891", "WF", "R11"),
        2011,
    ),
    2015: _wave(
        "ER60002",
        ("ER65004", "ER65021", "ER65022", "ER65023", "HD", "R2"),
        ("ER65052", "ER65069", "ER65070", "ER65071", "SP", "R11"),
        2013,
    ),
    2017: _wave(
        "ER66002",
        ("ER71096", "ER71113", "ER71114", "ER71115", "RP", "R2"),
        ("ER71144", "ER71161", "ER71162", "ER71163", "SP", "R2"),
        2015,
    ),
    2019: _wave(
        "ER72002",
        ("ER77118", "ER77135", "ER77136", "ER77137", "RP", "R2"),
        ("ER77166", "ER77183", "ER77184", "ER77185", "SP", "R2"),
        2017,
    ),
    2021: _wave(
        "ER78002",
        ("ER81454", "ER81471", "ER81472", "ER81473", "RP", "R2"),
        ("ER81502", "ER81519", "ER81520", "ER81521", "SP", "R2"),
        2019,
    ),
    2023: _wave(
        "ER82002",
        ("ER85311", "ER85328", "ER85329", "ER85330", "RP", "R2"),
        ("ER85359", "ER85376", "ER85377", "ER85378", "SP", "R2"),
        2021,
    ),
}
#: Amount codes that are not amounts: DK/NA (positive) and a loss of
#: unknown amount (negative), by wave (codebooks, module docstring).
_EIGHT_DIGIT = {
    "unknown": (99_999_998, 99_999_999),
    "loss_unknown": (-9_999_999,),
}
_DECIMAL = {"unknown": (9_999_999.0,), "loss_unknown": (-999_999.0,)}
_SENTINELS: dict[int, dict[str, tuple[float, ...]]] = {
    wave: (_EIGHT_DIGIT if wave <= 2005 else _DECIMAL) for wave in _VARS
}


def prior_year_variables(wave: int) -> dict[str, Any]:
    """The adjudicated table of one wave (2003-2023, odd)."""

    if int(wave) not in _VARS:
        raise ValueError(
            f"no year-before-last labor income adjudicated for wave {wave}"
        )
    return _VARS[int(wave)]


def annualize(
    employed: int,
    amount: float,
    per: int,
    *,
    wave: int,
) -> tuple[str, float]:
    """One item's ``(status, annual covered earnings)``; NaN if unobserved.

    Applies the module docstring's rules.  Refuses a code outside the
    documented domains.
    """

    if employed not in (_EMPLOYED_YES, _EMPLOYED_NO, _EMPLOYED_UNKNOWN):
        raise ValueError(f"wave {wave}: whether employed code {employed}")
    if per not in (_PER_INAP, *TIME_UNIT_FACTORS, *_PER_UNKNOWN):
        raise ValueError(f"wave {wave}: time unit code {per}")
    sentinels = _SENTINELS[int(wave)]
    if employed == _EMPLOYED_NO:
        return "not_employed", 0.0
    if employed == _EMPLOYED_UNKNOWN:
        return "employed_unknown", float("nan")
    value = float(amount)
    if value in sentinels["unknown"]:
        return "amount_unknown", float("nan")
    if value < 0 or value in sentinels["loss_unknown"]:
        return "loss", 0.0
    if value == 0:
        return "zero_broke_even", 0.0
    if per in TIME_UNIT_FACTORS:
        return "annual_amount", value * TIME_UNIT_FACTORS[per]
    return "time_unit_unknown", float("nan")


def _read(wave: int, data_dir: Path | None) -> pd.DataFrame:
    table = prior_year_variables(wave)
    sps_path, txt_path = family._family_paths(wave, data_dir)
    labels = psid.parse_sps_labels(sps_path)
    names: dict[str, str] = {}
    var, label = table["interview"]
    names["interview"] = family._verified(labels, var, label, wave)
    for role in ROLES:
        for concept, (var, label) in table[role].items():
            names[f"{role}_{concept}"] = family._verified(
                labels, var, label, wave
            )
    layout = psid.parse_sps_layout(sps_path).set_index("name")
    order = list(names.values())
    raw = pd.read_fwf(
        txt_path,
        colspecs=[
            (int(layout.loc[n, "start"]) - 1, int(layout.loc[n, "end"]))
            for n in order
        ],
        names=order,
        header=None,
    )
    frame = pd.DataFrame({key: raw[var] for key, var in names.items()})
    frame["interview"] = frame["interview"].astype("int64")
    if frame["interview"].duplicated().any():
        raise ValueError(f"family {wave}: duplicate interview numbers")
    return frame


def read_prior_year_labor_income(
    *,
    waves: tuple[int, ...] = tuple(_VARS),
    data_dir: Path | None = None,
    members: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Every reference person's and spouse's year-before-last item.

    One row per person who is the reference person (relationship 10) or
    spouse/partner (20, 22) of a responding family in the wave, matched by
    the individual file's interview number: ``person_id``, ``wave``,
    ``income_year`` (``wave - 2``), ``role``, the raw ``employed``,
    ``amount``, ``per`` and ``acc`` codes, ``status``
    (:data:`STATUSES`) and ``annual`` (NaN when unobserved).
    """

    waves = tuple(int(wave) for wave in waves)
    if members is None:
        members = read_wave_members(waves, data_dir=data_dir)
    rows = []
    for wave in waves:
        frame = _read(wave, data_dir)
        people = members[members["wave"] == wave]
        head_codes, spouse_codes = family._relationship_codes(wave)
        for role, codes in (
            ("reference_person", head_codes),
            ("spouse", spouse_codes),
        ):
            who = people[people["relationship"].isin(codes)]
            if who["interview"].duplicated().any():
                raise ValueError(f"wave {wave}: ambiguous {role} attachment")
            part = frame[
                [
                    "interview",
                    f"{role}_employed",
                    f"{role}_amount",
                    f"{role}_per",
                    f"{role}_acc",
                ]
            ].rename(
                columns={
                    f"{role}_{key}": key
                    for key in ("employed", "amount", "per", "acc")
                }
            )
            merged = who[["person_id", "interview"]].merge(
                part, on="interview", how="inner", validate="one_to_one"
            )
            results = [
                annualize(int(e), float(a), int(p), wave=wave)
                for e, a, p in zip(
                    merged["employed"],
                    merged["amount"],
                    merged["per"],
                    strict=True,
                )
            ]
            merged["status"] = [status for status, _ in results]
            merged["annual"] = np.array(
                [value for _, value in results], dtype="float64"
            )
            merged.insert(1, "wave", wave)
            merged.insert(2, "income_year", wave - 2)
            merged.insert(3, "role", role)
            rows.append(merged)
    out = pd.concat(rows, ignore_index=True)
    for column in ("employed", "per", "acc"):
        out[column] = out[column].astype("int64")
    if out.duplicated(["person_id", "income_year"]).any():
        raise ValueError("a person holds two roles in one wave")
    return out.sort_values(["person_id", "income_year"]).reset_index(drop=True)


def next_wave_histories(
    frame: pd.DataFrame,
) -> dict[int, dict[int, float]]:
    """``{person_id: {odd year: annual covered earnings}}``, observed only.

    The next-wave odd years the one history reads (M1 specification
    section 5): every item whose status is observed
    (:data:`_OBSERVED_STATUSES`), in dollars; unobserved items are left
    out, for the gap rule.
    """

    observed = frame[frame["status"].isin(_OBSERVED_STATUSES)]
    out: dict[int, dict[int, float]] = {}
    for pid, year, value in zip(
        observed["person_id"],
        observed["income_year"],
        observed["annual"],
        strict=True,
    ):
        out.setdefault(int(pid), {})[int(year)] = float(value)
    return out


def observed_statuses() -> tuple[str, ...]:
    """The statuses that observe a year (zero included)."""

    return _OBSERVED_STATUSES
