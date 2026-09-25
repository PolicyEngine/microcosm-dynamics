"""Label-verified PSID Social Security receipt histories, 1983-2022.

Track M (DynaSim scorecard exercise 4, the minimum benefit) classifies each
2022 beneficiary's own entitlement (the M1 specification's section 4b)
from when the person was first observed receiving Social Security.  Plan
item M3 of ``critical-path-minimum-benefit-20260924.md`` (revision 2)
asks for readers of every item that records receipt, with their labels
verified; this module reads them.  It leaves
:mod:`populace_dynamics.data.social_security_income` (waves 2009-2013,
Track A) unchanged.

Scope, verified 2026-09-25 against the staged setup files (``.sps``
labels), ``IND2023ER_formats.sas`` and the codebooks:

======================  ============  =====================================
Source                  Income years  What it records
======================  ============  =====================================
Individual file, waves  1983-1991     Person-level amount (``TOTAL SOCIAL
1984-1992                             SECURITY INCOME RECEIVED DURING <y>
                                      BY THIS INDIVIDUAL``), accuracy and a
                                      single type code
1993 family file        1992          Head's and wife's own amounts and
                                      type codes (V22012-V22028,
                                      V22286-V22302)
Family files, waves     1993-1996,    Family totals only ("Social Security
1994-2003               1998, 2000,   income of all family unit members");
                        2002          no person-level item exists
2005 and 2007 family    2003, 2005    Year-before-last items (R20-R23):
files                                 whether "you (or anyone else in the
                                      family there)" received, type
                                      mentions, amount
2009-2015 family files  2007, 2009,   The year-before-last whether item
                        2011, 2013    (R20) only: no type or amount
Individual file, waves  2004-2022     Person-level amount (``TOTAL SOCIAL
2005-2023               (even)        SECURITY INCOME RECEIVED, DURING
                                      <y>, BY THIS INDIVIDUAL``), accuracy,
                                      a type code (2005-2009) or six type
                                      mention flags (2011-2023)
======================  ============  =====================================

**Whose receipt the family-level items record** (plan item M3; M1
specification section 4b rule 3).  The 2005 and 2007 year-before-last
items ask whether "you (or anyone else in the family there)" received
Social Security in the year before last, "which type(s) ... did you (and
these members of the family) receive" and how much "you (and these
members of the family)" received altogether (2005 codebook, ER27727-
ER27731; 2007 codebook, ER40702-ER40706).  The 2009, 2011, 2013 and 2015
family files keep the whether item alone (R20, "Did you (or anyone else
in the family there) receive any income in <y> from Social Security?",
ER46687, ER52088, ER57892 and ER65072; codes 1 yes, 5 no, 8 DK, 9 NA or
refused), with no type or amount; the 2017-2023 files carry no
year-before-last Social Security item (labels searched 2026-09-25).  All
are family-level items: they identify a person's receipt only when the
family unit has one member at the interview (a whether-only "yes" then
records receipt of an unknown type), and every member's non-receipt when
the family reports none.  The family totals of waves 1994-2003 are, by their codebooks, the
Social Security income "of all family unit members" (1994, 1995, 2001),
"for all family members: heads, wives/"wives", and OFUMs" (1997) or "for
Heads, Wives/"Wives", and OFUMs" (1999, 2003); a zero total is every
member's non-receipt.  The 1996 total (ER9243) is labelled ``TOTAL FAMILY
SOCIAL SECURITY INCOME-1995`` but its codebook text reads "Head's Income
from Social Security in 1995", so a zero there is read as the head's
non-receipt only.  1994 and 1995 code 999,999 as "Latino sample family"
(not an amount).  :func:`family_level_person_rows` applies these readings.

**The 2023 amount (ER35219)** (M1 specification section 6, MS5's *B*).
Its codebook heading is "TOTAL SOCIAL SECURITY INCOME RECEIVED, DURING
2022, BY THIS INDIVIDUAL": an annual total in whole dollars, 1-99,998
"Actual amount", 99,999 "$99,999 or more" (the top code), 0 Inap.  The
2023 questionnaire (``q2023.pdf``, G34/G34PER) asks "How much was the
total amount from Social Security?" with a time unit that the released
item has already annualized; neither the question text nor the 2015
question-by-question notes (``fam2015_QxQs.pdf``) say anything about the
Medicare premium, so the amount is read as gross, and that reading is
recorded (:data:`AMOUNT_2023_READING`).  No months-of-receipt item for
2022 is released, so the monthly amount is the annual total over 12.

**What a zero records.**  For a person in a responding family unit the
individual file's amount is zero only as "Inap.", whose listed reasons
are the Latino and 2017 immigrant samples, family or mover-out
nonresponse, an institution, "no transfers" (1984) and "no Social
Security income" (IND2023ER codebook, ER30451, ER33837B and ER35219,
read 2026-09-25); the sample, nonresponse and institution reasons leave
the person outside sequence 1-20, so an in-family zero is read as no
receipt.  The question (G31) asks the reference person about "you (or
anyone else in the family there)" and G32 names the recipients, so each
member's amount is that member's own receipt of any Social Security
type.  One documentation inconsistency is recorded, not acted on: the
2015 interviewer notes for G31-G35 (``fam2015_QxQs.pdf``) say the item
"does not include Social Security Disability Insurance (SSDI)", while the
same notes list disabled workers as the first type at G33a, the pension
notes exclude "Social Security Disability (G33a)" as already reported,
and the 2023 codebook counts 811 persons whose type was disability.

**Discipline** (as :mod:`populace_dynamics.data.family_income`): each
variable is paired with its exact label in an adjudicated table and
verified at read time under whitespace normalization.  The individual
file's type and accuracy codes are verified against the release's SAS
``VALUE`` blocks; the family files' codes are adjudicated from their
codebooks (no formats file is staged for them) and decoded strictly, so
an undocumented code raises.  Amounts are whole dollars as recorded.

What this module does not do: it classifies no entitlement, links no
spouse and computes no benefit, threshold or statistic.  A person-year it
returns is "observed" only when the person was in a responding family
unit (sequence 1-20) that wave, the only persons the items describe.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from populace_dynamics.data import disability, family, panels, psid
from populace_dynamics.data import social_security_income as ssi

__all__ = [
    "ACCURACY_CODES_1984",
    "ACCURACY_CODES_2005",
    "AMOUNT_2023",
    "AMOUNT_2023_READING",
    "AMOUNT_TOP_CODE",
    "AUXILIARY_TYPES",
    "FAMILY_TOTAL_WAVES",
    "HEAD_ONLY_TOTAL_WAVES",
    "INDIVIDUAL_WAVES",
    "SS_TYPES",
    "TYPE_CODES_1984",
    "TYPE_CODES_1988",
    "WORKER_TYPES",
    "YEAR_BEFORE_LAST_TYPED_WAVES",
    "YEAR_BEFORE_LAST_WAVES",
    "family_level_person_rows",
    "family_total_variables",
    "individual_variables",
    "read_family_1993_receipt",
    "read_family_totals",
    "read_individual_receipt",
    "read_wave_members",
    "read_year_before_last",
    "verify_individual_codes",
    "year_before_last_variables",
]

#: Self-reported benefit types, in the individual file's G33A order.
SS_TYPES: tuple[str, ...] = ssi.SS_TYPES
#: A worker's own benefit types.
WORKER_TYPES: tuple[str, ...] = ("disability", "retirement")
#: Auxiliary (spouse's, survivor's, dependent's) types.
AUXILIARY_TYPES: tuple[str, ...] = (
    "survivor",
    "dependent_of_disabled",
    "dependent_of_retired",
)

#: Waves whose individual file carries a person-level amount and type.
INDIVIDUAL_WAVES: tuple[int, ...] = (
    *range(1984, 1993),
    *range(2005, 2024, 2),
)
#: Waves whose family file carries year-before-last Social Security
#: items: 2005 and 2007 with type mentions and an amount, 2009-2015 the
#: whether item (R20) only.
YEAR_BEFORE_LAST_WAVES: tuple[int, ...] = (2005, 2007, 2009, 2011, 2013, 2015)
YEAR_BEFORE_LAST_TYPED_WAVES: tuple[int, ...] = (2005, 2007)
#: Waves whose family file carries only a family Social Security total.
FAMILY_TOTAL_WAVES: tuple[int, ...] = (
    1994,
    1995,
    1996,
    1997,
    1999,
    2001,
    2003,
)
#: Totals whose codebook text describes the head's income only.
HEAD_ONLY_TOTAL_WAVES: tuple[int, ...] = (1996,)
#: The individual amounts' top code ("$99,999 or more").
AMOUNT_TOP_CODE = 99_999

#: Single type codes, 1984-1987 waves (formats ER30450F, ER30485F,
#: ER30520F, ER30556F): code -> (type, expected label prefix).  Code 4
#: ("Any combination of the above") names no single type.
TYPE_CODES_1984: dict[int, tuple[str | None, str]] = {
    1: ("disability", "disability"),
    2: ("retirement", "retirement"),
    3: ("survivor", "survivor benefits"),
    4: (None, "any combination of the above"),
    7: ("other", "other"),
}
_UNKNOWN_1984 = (0, 9)
#: Single type codes, 1988-1992 and 2005-2009 waves and the 1993 family
#: file (formats ER30591F ... ER34030F; 1993 codebook V22012, V22286).
TYPE_CODES_1988: dict[int, tuple[str | None, str]] = {
    1: ("disability", "disability"),
    2: ("retirement", "retirement"),
    3: ("survivor", "survivor benefits; dependent of deceased recipient"),
    4: (None, "any combination of codes 1-3 and 5-7"),
    5: ("dependent_of_disabled", "dependent of disabled recipient"),
    6: ("dependent_of_retired", "dependent of retired recipient"),
    7: ("other", "other"),
}
_UNKNOWN_1988 = (0, 8, 9)
#: Accuracy codes: 1984-1992 ("Minor/Major assignment"), 2005-2023
#: ("Imputed by PSID staff", "Imputed using the median value").
ACCURACY_CODES_1984: dict[int, str] = {
    0: "none",
    1: "minor_assignment",
    2: "major_assignment",
}
ACCURACY_CODES_2005: dict[int, str] = {
    0: "actual",
    1: "imputed_by_staff",
    5: "imputed_median",
}
_ACCURACY_1993: dict[int, str] = {0: "actual", 1: "imputed"}
_FLAG_YES, _FLAG_NO = 1, 5
_FLAG_UNKNOWN = (0, 8, 9)
_FLAG_WORDS: dict[str, tuple[str, str]] = {
    # type -> (label word, format keyword)
    "disability": ("DISABILITY", "disability"),
    "retirement": ("RETIREMENT", "retirement"),
    "survivor": ("SURVIVOR", "survivor"),
    "dependent_of_disabled": ("DEP OF DISABLED", "dependent of disabled"),
    "dependent_of_retired": ("DEP OF RETIRED", "dependent of retired"),
    "other": ("OTHER", "other"),
}

#: The 2023 amount MS5 reads, and its unit and Medicare reading.
AMOUNT_2023: tuple[str, str] = ("ER35219", "G34 AMT SOC SEC RCD 23")
AMOUNT_2023_READING: dict[str, Any] = {
    "variable": "ER35219",
    "unit": "annual_whole_dollars_received_during_2022",
    "unit_source": (
        "IND2023ER codebook: 'TOTAL SOCIAL SECURITY INCOME RECEIVED, DURING "
        "2022, BY THIS INDIVIDUAL'"
    ),
    "top_code": AMOUNT_TOP_CODE,
    "top_code_label": "$99,999 or more",
    "monthly_conversion": "annual_total_divided_by_12",
    "months_of_receipt_released": False,
    "medicare_premium": "gross",
    "medicare_reading": (
        "the 2023 questionnaire's G34/G34PER ('How much was the total amount "
        "from Social Security?') and the 2015 question-by-question notes say "
        "nothing about the Medicare premium; the amount is taken as gross "
        "and that reading is recorded (M1 specification section 6)"
    ),
}

_IND_INDIVIDUAL = ("ER30001", "1968 INTERVIEW NUMBER")
_IND_PERSON = ("ER30002", "PERSON NUMBER 68")
_IN_FAMILY = (1, 20)


def _single(
    type_var: str, amount_var: str, acc_var: str, prefixes: tuple[str, ...]
) -> dict[str, tuple[str, str]]:
    type_prefix, amount_prefix, acc_prefix, yy = prefixes
    return {
        "type_code": (type_var, f"{type_prefix} TYPE SOC SEC RCD {yy}"),
        "amount": (amount_var, f"{amount_prefix} AMT SOC SEC RCD {yy}"),
        "acc": (acc_var, f"{acc_prefix} ACC SOC SEC AMT {yy}"),
    }


def _flags(first_flag: int, yy: str) -> dict[str, tuple[str, str]]:
    out = {}
    for offset, name in enumerate(SS_TYPES):
        word = _FLAG_WORDS[name][0]
        out[f"flag_{name}"] = (
            f"ER{first_flag + offset}",
            f"G33A WTR SOC SEC TYPE {word} {yy}",
        )
    out["amount"] = (f"ER{first_flag + 6}", f"G34 AMT SOC SEC RCD {yy}")
    out["acc"] = (f"ER{first_flag + 7}", f"G34 ACC SOC SEC AMT {yy}")
    return out


#: Adjudicated individual-file variables per wave, each with its exact
#: label (``IND2023ER.sps``, read 2026-09-25).
_INDIVIDUAL_VARS: dict[int, dict[str, tuple[str, str]]] = {
    1984: _single(
        "ER30450", "ER30451", "ER30452", ("F33", "F34", "F34", "84")
    ),
    1985: _single(
        "ER30485", "ER30486", "ER30487", ("K31", "K33", "K33", "85")
    ),
    1986: _single(
        "ER30520", "ER30521", "ER30522", ("G31", "G34", "G34", "86")
    ),
    1987: _single(
        "ER30556", "ER30557", "ER30558", ("G33", "G34", "G34", "87")
    ),
    1988: _single(
        "ER30591", "ER30592", "ER30593", ("G31", "G34", "G34", "88")
    ),
    1989: _single(
        "ER30627", "ER30628", "ER30629", ("G31", "G34", "G34", "89")
    ),
    1990: _single(
        "ER30664", "ER30665", "ER30666", ("G31", "G34", "G34", "90")
    ),
    1991: _single(
        "ER30712", "ER30713", "ER30714", ("G31", "G34", "G34", "91")
    ),
    1992: _single(
        "ER30757", "ER30758", "ER30759", ("G33", "G34", "G34", "92")
    ),
    2005: _single(
        "ER33837A", "ER33837B", "ER33837C", ("G33", "G34", "G34", "05")
    ),
    2007: _single(
        "ER33925A", "ER33925B", "ER33925C", ("G33", "G34", "G34", "07")
    ),
    2009: _single(
        "ER34030", "ER34031", "ER34032", ("G33", "G34", "G34", "09")
    ),
    2011: _flags(34137, "11"),
    2013: _flags(34244, "13"),
    2015: _flags(34394, "15"),
    2017: _flags(34603, "17"),
    2019: _flags(34812, "19"),
    2021: _flags(35013, "21"),
    2023: _flags(35213, "23"),
}


def _type_scheme(wave: int) -> dict[int, tuple[str | None, str]]:
    return TYPE_CODES_1984 if wave <= 1987 else TYPE_CODES_1988


def _type_unknown(wave: int) -> tuple[int, ...]:
    return _UNKNOWN_1984 if wave <= 1987 else _UNKNOWN_1988


def _accuracy_scheme(wave: int) -> dict[int, str]:
    return ACCURACY_CODES_1984 if wave <= 1992 else ACCURACY_CODES_2005


def individual_variables(wave: int) -> dict[str, tuple[str, str]]:
    """The adjudicated ``{concept: (variable, label)}`` table of a wave."""

    wave = int(wave)
    if wave not in _INDIVIDUAL_VARS:
        raise ValueError(
            f"wave {wave} carries no person-level Social Security item "
            f"(individual waves: {INDIVIDUAL_WAVES})"
        )
    return dict(_INDIVIDUAL_VARS[wave])


def verify_individual_codes(
    *, data_dir: Path | None = None, waves: tuple[int, ...] = INDIVIDUAL_WAVES
) -> dict[int, dict[str, str]]:
    """Verify every type and accuracy code against ``IND2023ER_formats``.

    A single type code must carry its documented label prefix for every
    code of its scheme; a mention flag's code 1 must read "type was <t>"
    and code 5 "type was not <t>"; an accuracy format must carry the
    scheme's labels (1984-1992: "Minor assignment"/"Major assignment";
    2005-2023: "Imputed by PSID staff ..."/"Imputed using the median
    ...").  Returns ``{wave: {variable: format}}``.
    """

    path = disability.employment_status_formats_path(data_dir)
    blocks = ssi.parse_value_label_blocks(path)
    assignments = disability.parse_sas_format_assignments(path)
    out: dict[int, dict[str, str]] = {}
    for wave in waves:
        table = individual_variables(wave)
        checked: dict[str, str] = {}
        if "type_code" in table:
            var = table["type_code"][0]
            fmt = assignments.get(var, f"{var}F")
            codes = blocks.get(fmt, {})
            for code, (_, prefix) in _type_scheme(wave).items():
                label = " ".join(codes.get(code, "").lower().split())
                if not label.startswith(prefix):
                    raise ValueError(
                        f"wave {wave}: {var} ({fmt}) code {code} reads "
                        f"{label!r}, expected a label starting {prefix!r}"
                    )
            checked[var] = fmt
        for name in SS_TYPES:
            key = f"flag_{name}"
            if key not in table:
                continue
            var = table[key][0]
            fmt = assignments.get(var, f"{var}F")
            codes = blocks.get(fmt, {})
            word = _FLAG_WORDS[name][1]
            yes = " ".join(codes.get(_FLAG_YES, "").lower().split())
            no = " ".join(codes.get(_FLAG_NO, "").lower().split())
            if f"type was {word}" not in yes or "was not" in yes:
                raise ValueError(
                    f"wave {wave}: {var} ({fmt}) code 1 reads {yes!r}"
                )
            if f"type was not {word}" not in no:
                raise ValueError(
                    f"wave {wave}: {var} ({fmt}) code 5 reads {no!r}"
                )
            checked[var] = fmt
        var = table["acc"][0]
        fmt = assignments.get(var, f"{var}F")
        codes = {
            code: " ".join(text.lower().split())
            for code, text in blocks.get(fmt, {}).items()
        }
        if wave <= 1992:
            wanted = {1: "minor assignment", 2: "major assignment"}
        else:
            wanted = {
                1: "imputed by psid staff",
                5: "imputed using the median",
            }
        for code, text in wanted.items():
            if not codes.get(code, "").startswith(text):
                raise ValueError(
                    f"wave {wave}: {var} ({fmt}) code {code} reads "
                    f"{codes.get(code)!r}, expected {text!r}"
                )
        checked[var] = fmt
        out[wave] = checked
    return out


def _decode(series: pd.Series, domain, what: str) -> pd.Series:
    values = pd.to_numeric(series, errors="raise").astype("int64")
    unexpected = sorted(set(int(v) for v in values.unique()) - set(domain))
    if unexpected:
        raise ValueError(
            f"{what}: undocumented code(s) {unexpected}; the documented "
            f"domain is {sorted(domain)}"
        )
    return values


def _amount(series: pd.Series, what: str) -> pd.Series:
    values = pd.to_numeric(series, errors="raise").astype("int64")
    if (values < 0).any():
        raise ValueError(f"{what}: negative Social Security amount")
    return values


def _types_from_code(
    codes: pd.Series, scheme: Mapping[int, tuple[str | None, str]]
) -> dict[str, pd.Series]:
    """Nullable-boolean type columns from a single type code.

    A documented single-type code sets its type True and every other
    type False; the combination code (4) and the unknown codes leave all
    types ``<NA>`` (``type_combination`` marks code 4).
    """

    out: dict[str, pd.Series] = {}
    single = {
        code: name for code, (name, _) in scheme.items() if name is not None
    }
    informative = codes.isin(list(single))
    for name in SS_TYPES:
        column = pd.Series(pd.NA, index=codes.index, dtype="boolean")
        matching = [code for code, value in single.items() if value == name]
        column[informative] = codes[informative].isin(matching)
        out[f"type_{name}"] = column
    out["type_combination"] = (codes == 4).astype(bool)
    return out


def _flag(series: pd.Series, what: str) -> pd.Series:
    codes = _decode(series, (_FLAG_YES, _FLAG_NO, *_FLAG_UNKNOWN), what)
    out = pd.Series(pd.NA, index=series.index, dtype="boolean")
    out[codes == _FLAG_YES] = True
    out[codes == _FLAG_NO] = False
    return out


def read_wave_members(
    waves: tuple[int, ...], *, data_dir: Path | None = None
) -> pd.DataFrame:
    """In-family persons of ``waves``: ``person_id``, ``wave``,
    ``sequence``, ``relationship``, ``interview`` (label-resolved by
    :func:`populace_dynamics.data.panels.ind_person_period`)."""

    concepts = {
        key: panels.DEMOGRAPHIC_CONCEPTS[key]
        for key in ("sequence", "relationship", "interview")
    }
    people = panels.ind_person_period(
        concepts, data_dir=data_dir, waves=list(waves)
    )
    low, high = _IN_FAMILY
    people = people[people["sequence"].between(low, high)].copy()
    people = people.rename(columns={"period": "wave"})
    for column in ("sequence", "relationship", "interview"):
        people[column] = people[column].astype("int64")
    return people.reset_index(drop=True)


def read_individual_receipt(
    *,
    waves: tuple[int, ...] = INDIVIDUAL_WAVES,
    data_dir: Path | None = None,
    members: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Person-level Social Security for every in-family person-wave.

    One row per person present in a responding family unit (sequence
    1-20) in a wave of :data:`INDIVIDUAL_WAVES`: ``person_id``, ``wave``,
    ``income_year`` (``wave - 1``), ``relationship``, ``interview``,
    ``amount`` (annual whole dollars; 0 is no receipt), ``acc`` (the raw
    accuracy code), ``type_<t>`` for each type (nullable boolean,
    ``<NA>`` when the item carries no type information, including every
    zero amount) and ``type_combination`` (a single code 4).  Labels and
    codes are verified first (:func:`verify_individual_codes`).
    ``members`` may pass :func:`read_wave_members`' frame to avoid a
    second read.
    """

    waves = tuple(int(wave) for wave in waves)
    labels = psid.parse_sps_labels(
        psid.product_sps_path("ind2023er", data_dir)
    )
    expected: dict[str, str] = dict([_IND_INDIVIDUAL, _IND_PERSON])
    for wave in waves:
        for var, label in individual_variables(wave).values():
            expected[var] = label
    psid.verify_labels(labels, expected, context="ind2023er Track M receipt")
    verify_individual_codes(data_dir=data_dir, waves=waves)
    wide = psid.read_psid(
        "ind2023er", columns=list(expected), data_dir=data_dir
    )
    person_id = wide["ER30001"].astype("int64") * 1000 + wide[
        "ER30002"
    ].astype("int64")
    if members is None:
        members = read_wave_members(waves, data_dir=data_dir)
    frames = []
    for wave in waves:
        table = individual_variables(wave)
        what = f"individual {wave}"
        frame = pd.DataFrame({"person_id": person_id})
        frame["amount"] = _amount(wide[table["amount"][0]], what)
        frame["acc"] = _decode(
            wide[table["acc"][0]], _accuracy_scheme(wave), what + " acc"
        )
        if "type_code" in table:
            scheme = _type_scheme(wave)
            codes = _decode(
                wide[table["type_code"][0]],
                (*scheme, *_type_unknown(wave)),
                what + " type",
            )
            for name, column in _types_from_code(codes, scheme).items():
                frame[name] = column
        else:
            for name in SS_TYPES:
                frame[f"type_{name}"] = _flag(
                    wide[table[f"flag_{name}"][0]], f"{what} {name}"
                )
            frame["type_combination"] = False
        # A zero amount carries no type information.
        none = frame["amount"] == 0
        for name in SS_TYPES:
            frame.loc[none, f"type_{name}"] = pd.NA
        frame.loc[none, "type_combination"] = False
        wave_members = members.loc[
            members["wave"] == wave,
            ["person_id", "relationship", "interview"],
        ]
        merged = wave_members.merge(
            frame, on="person_id", how="left", validate="one_to_one"
        )
        if merged["amount"].isna().any():
            raise ValueError(f"{what}: an in-family person has no record")
        merged.insert(1, "wave", wave)
        merged.insert(2, "income_year", wave - 1)
        frames.append(merged)
    out = pd.concat(frames, ignore_index=True)
    out["amount"] = out["amount"].astype("int64")
    out["acc"] = out["acc"].astype("int64")
    out["type_combination"] = out["type_combination"].astype(bool)
    return out.sort_values(["person_id", "wave"]).reset_index(drop=True)


#: The 1993 family file's head and wife items for income year 1992
#: (``FAM1993.sps``; codes from ``fam1993_codebook.pdf``: types as
#: :data:`TYPE_CODES_1988`, 0 Inap.; accuracy 0 actual, 1 imputed).
_FAMILY_1993: dict[str, tuple[str, str]] = {
    "interview": ("V21602", "1993 INTERVIEW NUMBER"),
    "head_type": ("V22012", "G33A HD 1992 SOCIAL SECURITY TYPE"),
    "head_amount": ("V22027", "HD 1992 SOCIAL SEC INCOME (G34A)"),
    "head_acc": ("V22028", "ACC HD 1992 SOCIAL SECURITY INCOME"),
    "wife_type": ("V22286", "G33A WF TYPE 1992 SOCIAL SECURITY INCOME"),
    "wife_amount": ("V22301", "WF 1992 SOCIAL SEC INCOME (G34A)"),
    "wife_acc": ("V22302", "ACC WF 1992 SOCIAL SECURITY INCOME"),
}


def _read_family_columns(
    wave: int, table: Mapping[str, tuple[str, str]], data_dir: Path | None
) -> pd.DataFrame:
    sps_path, txt_path = family._family_paths(wave, data_dir)
    labels = psid.parse_sps_labels(sps_path)
    for var, label in table.values():
        family._verified(labels, var, label, wave)
    layout = psid.parse_sps_layout(sps_path).set_index("name")
    names = [var for var, _ in table.values()]
    raw = pd.read_fwf(
        txt_path,
        colspecs=[
            (int(layout.loc[n, "start"]) - 1, int(layout.loc[n, "end"]))
            for n in names
        ],
        names=names,
        header=None,
    )
    frame = pd.DataFrame(
        {concept: raw[var] for concept, (var, _) in table.items()}
    )
    frame["interview"] = frame["interview"].astype("int64")
    if frame["interview"].duplicated().any():
        raise ValueError(f"family {wave}: duplicate interview numbers")
    return frame


def read_family_1993_receipt(
    *, data_dir: Path | None = None, members: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Head's and wife's own 1992 Social Security, attached to persons.

    Rows (head and wife/partner of each responding 1993 family, matched
    by the individual file's 1993 interview number and relationship):
    ``person_id``, ``wave`` (1993), ``income_year`` (1992), ``role``,
    ``amount``, ``acc`` and the ``type_*`` columns, as
    :func:`read_individual_receipt`.
    """

    wave = 1993
    frame = _read_family_columns(wave, _FAMILY_1993, data_dir)
    if members is None:
        members = read_wave_members((wave,), data_dir=data_dir)
    people = members[members["wave"] == wave]
    head_codes, spouse_codes = family._relationship_codes(wave)
    rows = []
    for role, codes in (("head", head_codes), ("wife", spouse_codes)):
        who = people[people["relationship"].isin(codes)]
        if who["interview"].duplicated().any():
            raise ValueError(f"family {wave}: ambiguous {role} attachment")
        what = f"family {wave} {role}"
        part = pd.DataFrame(
            {
                "interview": frame["interview"],
                "amount": _amount(frame[f"{role}_amount"], what),
                "acc": _decode(frame[f"{role}_acc"], _ACCURACY_1993, what),
            }
        )
        type_codes = _decode(
            frame[f"{role}_type"],
            (*TYPE_CODES_1988, *_UNKNOWN_1988),
            what + " type",
        )
        for name, column in _types_from_code(
            type_codes, TYPE_CODES_1988
        ).items():
            part[name] = column
        none = part["amount"] == 0
        for name in SS_TYPES:
            part.loc[none, f"type_{name}"] = pd.NA
        part.loc[none, "type_combination"] = False
        merged = who[["person_id", "interview"]].merge(
            part, on="interview", how="inner", validate="one_to_one"
        )
        merged.insert(1, "wave", wave)
        merged.insert(2, "income_year", wave - 1)
        merged.insert(3, "role", role)
        rows.append(merged)
    out = pd.concat(rows, ignore_index=True)
    out["type_combination"] = out["type_combination"].astype(bool)
    return out.sort_values("person_id").reset_index(drop=True)


#: The year-before-last items (R20 whether, R22 first and second type
#: mentions, R23 amount and time unit) of the 2005 and 2007 family files.
_YEAR_BEFORE_LAST: dict[int, dict[str, tuple[str, str]]] = {
    2005: {
        "interview": ("ER25002", "2005 FAMILY INTERVIEW (ID) NUMBER"),
        "received": ("ER27727", "R20 WTR RECD SOC SECURITY YR BEFORE LAST"),
        "mention_1": ("ER27728", "R22 TYPE SOC SEC MEN 1 YR BEFORE LAST"),
        "mention_2": ("ER27729", "R22 TYPE SOC SEC MEN 2 YR BEFORE LAST"),
        "amount": ("ER27730", "R23 SOCIAL SECURITY AMOUNT YEAR B4 LAST"),
        "per": ("ER27731", "R23 SOCIAL SECURITY PER YEAR BEFORE LAST"),
    },
    2007: {
        "interview": ("ER36002", "2007 FAMILY INTERVIEW (ID) NUMBER"),
        "received": ("ER40702", "R20 WTR RECD SOC SECURITY YR BEFORE LAST"),
        "mention_1": ("ER40703", "R22 TYPE SOC SEC MEN 1 YR BEFORE LAST"),
        "mention_2": ("ER40704", "R22 TYPE SOC SEC MEN 2 YR BEFORE LAST"),
        "amount": ("ER40705", "R23 SOCIAL SECURITY AMOUNT YEAR B4 LAST"),
        "per": ("ER40706", "R23 SOCIAL SECURITY PER YEAR BEFORE LAST"),
    },
    2009: {
        "interview": ("ER42002", "2009 FAMILY INTERVIEW (ID) NUMBER"),
        "received": ("ER46687", "R20 WTR RECD SOC SECURITY YR BEFORE LAST"),
    },
    2011: {
        "interview": ("ER47302", "2011 FAMILY INTERVIEW (ID) NUMBER"),
        "received": ("ER52088", "R20 WTR RECD SOC SECURITY YR BEFORE LAST"),
    },
    2013: {
        "interview": ("ER53002", "2013 FAMILY INTERVIEW (ID) NUMBER"),
        "received": ("ER57892", "R20 WTR RECD SOC SECURITY YR BEFORE LAST"),
    },
    2015: {
        "interview": ("ER60002", "2015 FAMILY INTERVIEW (ID) NUMBER"),
        "received": ("ER65072", "R20 WTR RECD SOC SECURITY YR BEFORE LAST"),
    },
}
#: R20 codes (2005, 2007 codebooks): 1 yes, 5 no, 8 DK, 9 NA; refused.
_RECEIVED_CODES = (1, 5, 8, 9)
#: R22 mention codes: as :data:`TYPE_CODES_1988` less the combination,
#: 8 DK, 9 NA; refused, 0 Inap. (no receipt, or no second mention).
_MENTION_TYPES: dict[int, str] = {
    1: "disability",
    2: "retirement",
    3: "survivor",
    5: "dependent_of_disabled",
    6: "dependent_of_retired",
    7: "other",
}
_MENTION_UNKNOWN = (0, 8, 9)
#: R23 time-unit codes: 5 month, 6 year, 7 other, 8 DK, 9 NA, 0 Inap.
_PER_CODES = (0, 5, 6, 7, 8, 9)


def year_before_last_variables(wave: int) -> dict[str, tuple[str, str]]:
    """The adjudicated year-before-last table of a 2005 or 2007 file."""

    if int(wave) not in _YEAR_BEFORE_LAST:
        raise ValueError(f"no year-before-last items adjudicated for {wave}")
    return dict(_YEAR_BEFORE_LAST[int(wave)])


def read_year_before_last(
    wave: int, *, data_dir: Path | None = None
) -> pd.DataFrame:
    """One wave's family-level year-before-last Social Security items.

    One row per responding family: ``interview``, ``wave``,
    ``income_year`` (``wave - 2``), ``received`` (the raw R20 code),
    ``type_<t>`` (True when either R22 mention names the type; all
    ``<NA>`` without receipt, with no informative mention, or in a
    whether-only wave, 2009-2015) and ``amount``/``per`` (raw, ``<NA>``
    in a whether-only wave; not used for classification).
    """

    table = year_before_last_variables(wave)
    frame = _read_family_columns(int(wave), table, data_dir)
    what = f"family {wave} year before last"
    received = _decode(frame["received"], _RECEIVED_CODES, what + " R20")
    out = pd.DataFrame(
        {
            "interview": frame["interview"],
            "wave": int(wave),
            "income_year": int(wave) - 2,
            "received": received,
        }
    )
    if "mention_1" not in table:
        for name in _MENTION_TYPES.values():
            out[f"type_{name}"] = pd.Series(
                pd.NA, index=out.index, dtype="boolean"
            )
        out["amount"] = pd.Series(pd.NA, index=out.index, dtype="Int64")
        out["per"] = pd.Series(pd.NA, index=out.index, dtype="Int64")
        return out
    mentions = [
        _decode(
            frame[key], (*_MENTION_TYPES, *_MENTION_UNKNOWN), f"{what} {key}"
        )
        for key in ("mention_1", "mention_2")
    ]
    informative = mentions[0].isin(list(_MENTION_TYPES)) & (received == 1)
    for code, name in _MENTION_TYPES.items():
        column = pd.Series(pd.NA, index=out.index, dtype="boolean")
        hit = (mentions[0] == code) | (mentions[1] == code)
        column[informative] = hit[informative]
        out[f"type_{name}"] = column
    out["amount"] = pd.to_numeric(frame["amount"]).astype("Int64")
    out["per"] = _decode(frame["per"], _PER_CODES, what + " R23 per").astype(
        "Int64"
    )
    return out


#: Family Social Security totals of waves 1994-2003, each with its exact
#: label and the codebook's non-amount codes.
_FAMILY_TOTALS: dict[int, dict[str, Any]] = {
    1994: {
        "interview": ("ER2002", "1994 INTERVIEW #"),
        "total": ("ER4152", "TOTAL FAMILY SOCIAL SECURITY INCOME-1993"),
        "not_amount": (999_999,),
    },
    1995: {
        "interview": ("ER5002", "1995 INTERVIEW #"),
        "total": ("ER6992", "TOTAL FAMILY SOCIAL SECURITY INCOME-1994"),
        "not_amount": (999_999,),
    },
    1996: {
        "interview": ("ER7002", "1996 INTERVIEW #"),
        "total": ("ER9243", "TOTAL FAMILY SOCIAL SECURITY INCOME-1995"),
        "not_amount": (),
    },
    1997: {
        "interview": ("ER10002", "1997 INTERVIEW #"),
        "total": ("ER12077", "SOCIAL SECURITY INCOME"),
        "not_amount": (),
    },
    1999: {
        "interview": ("ER13002", "1999 FAMILY INTERVIEW (ID) NUMBER"),
        "total": ("ER16460", "SOCIAL SECURITY INCOME"),
        "not_amount": (),
    },
    2001: {
        "interview": ("ER17002", "2001 FAMILY INTERVIEW (ID) NUMBER"),
        "total": ("ER20455", "TOTAL FAMILY SOCIAL SECURITY INCOME-2000"),
        "not_amount": (),
    },
    2003: {
        "interview": ("ER21002", "2003 FAMILY INTERVIEW (ID) NUMBER"),
        "total": ("ER24104", "SOCIAL SECURITY INCOME LAST YEAR"),
        "not_amount": (),
    },
}


def family_total_variables(wave: int) -> dict[str, tuple[str, str]]:
    """The adjudicated ``{interview, total}`` table of a total wave."""

    if int(wave) not in _FAMILY_TOTALS:
        raise ValueError(f"no family Social Security total for {wave}")
    entry = _FAMILY_TOTALS[int(wave)]
    return {"interview": entry["interview"], "total": entry["total"]}


def read_family_totals(
    wave: int, *, data_dir: Path | None = None
) -> pd.DataFrame:
    """One wave's family Social Security total (waves 1994-2003).

    One row per responding family: ``interview``, ``wave``,
    ``income_year`` (``wave - 1``), ``total`` (``<NA>`` for a code that
    is not an amount, the Latino-sample 999,999 of 1994 and 1995) and
    ``head_only`` (True for 1996, whose codebook text describes the
    head's income; see the module docstring).
    """

    wave = int(wave)
    frame = _read_family_columns(wave, family_total_variables(wave), data_dir)
    total = pd.to_numeric(frame["total"]).astype("int64")
    if (total < 0).any():
        raise ValueError(f"family {wave}: negative Social Security total")
    not_amount = _FAMILY_TOTALS[wave]["not_amount"]
    out = pd.DataFrame(
        {
            "interview": frame["interview"],
            "wave": wave,
            "income_year": wave - 1,
            "total": total.astype("Int64").mask(total.isin(not_amount)),
            "head_only": wave in HEAD_ONLY_TOTAL_WAVES,
        }
    )
    return out


def family_level_person_rows(
    families: pd.DataFrame,
    members: pd.DataFrame,
    *,
    kind: str,
) -> pd.DataFrame:
    """Apply the family-level readings (module docstring) to persons.

    ``families`` is :func:`read_year_before_last` (``kind="year_before_
    last"``) or :func:`read_family_totals` (``kind="total"``) for one
    wave; ``members`` the wave's in-family persons
    (:func:`read_wave_members`).  Returns one row per identified
    person-year: ``person_id``, ``income_year``, ``source`` (``kind``),
    ``receipt`` (True, or False for non-receipt), ``fu_size`` and the
    ``type_*`` columns (nullable).  A family reporting none identifies
    every member's non-receipt (the head's only for a head-only total);
    a year-before-last "yes" identifies the receipt, with its mentioned
    types, of a family unit's only member; nothing else identifies a
    person, and no row is returned for it.
    """

    if kind not in ("year_before_last", "total"):
        raise ValueError(f"kind must be year_before_last or total, not {kind}")
    if families.empty:
        return pd.DataFrame()
    wave = int(families["wave"].iloc[0])
    people = members[members["wave"] == wave][
        ["person_id", "relationship", "interview"]
    ]
    sizes = people.groupby("interview")["person_id"].transform("size")
    people = people.assign(fu_size=sizes.astype("int64"))
    merged = people.merge(families, on="interview", how="inner")
    type_columns = [f"type_{name}" for name in SS_TYPES]
    if kind == "year_before_last":
        none = merged["received"] == 5
        single_yes = (merged["received"] == 1) & (merged["fu_size"] == 1)
        keep = none | single_yes
        out = merged.loc[keep].copy()
        out["receipt"] = single_yes[keep].to_numpy()
        for column in type_columns:
            values = out[column].astype("boolean")
            values[~out["receipt"]] = pd.NA
            out[column] = values
    else:
        head_codes, _ = family._relationship_codes(wave)
        zero = merged["total"].eq(0).fillna(False)
        head_only = merged["head_only"] & ~merged["relationship"].isin(
            head_codes
        )
        keep = zero & ~head_only
        out = merged.loc[keep].copy()
        out["receipt"] = False
        for column in type_columns:
            out[column] = pd.Series(pd.NA, index=out.index, dtype="boolean")
    out["source"] = kind
    columns = [
        "person_id",
        "income_year",
        "source",
        "receipt",
        "fu_size",
        *type_columns,
    ]
    out["receipt"] = out["receipt"].astype(bool)
    return out[columns].reset_index(drop=True)
