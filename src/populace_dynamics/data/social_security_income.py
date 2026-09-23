"""Label-verified PSID Social Security income, income years 2008-2012.

Two staged PSID sources carry Social Security (OASDI) receipt for the waves
around the 2010 starting year of the Track A cohort
(:mod:`populace_dynamics.cohorts.psid2010`):

* **Family files** (waves 2009, 2011, 2013) carry the head's and the
  wife's/"wife's" own Social Security income for the prior calendar year
  (``HEAD SOCIAL SECURITY INCOME-<yyyy>`` / ``WIFE SOCIAL SECURITY
  INCOME-<yyyy>``) with an accuracy flag each, the family-unit total for
  all other family-unit members (``OFUM SOCIAL SECURITY INCOME-<yyyy>``,
  not attributable to a person), and a family-level yes/no item for the
  year before last (``R20 WTR RECD SOC SECURITY YR BEFORE LAST``). The
  PSID is biennial from 1999, so income years 2009 and 2011 have no
  amount at all; the R20 item is the only information about them.
* **The cross-year individual file** carries, for every person in a
  responding family unit, the same survey's person-level Social Security
  amount (``G34 AMT SOC SEC RCD <yy>``), its accuracy flag, and the
  self-reported benefit type: one single-code item in 2009 (``G33 TYPE SOC
  SEC RCD 09``) and six yes/no mention flags from 2011 (``G33A WTR SOC SEC
  TYPE DISABILITY 11`` and so on). The individual codebook describes the
  amount as the total received "BY THIS INDIVIDUAL"; its Inap. list names
  no head/wife exclusion.

Scope and coverage (verified 2026-09-22 against the staged setup files,
codebooks and ``IND2023ER_formats.sas``):

========  ============  =========================  ==========================
Wave      Income year   Family head/wife amounts   Individual amount and type
========  ============  =========================  ==========================
2009      2008          ER46929 / ER46931          ER34031, type ER34030
2011      2010          ER52337 / ER52339          ER34143, flags ER34137-42
2013      2012          ER58146 / ER58148          ER34250, flags ER34244-49
========  ============  =========================  ==========================

Every variable name is paired with its exact label in an adjudicated table
and verified at read time under whitespace normalization, the discipline of
:mod:`populace_dynamics.data.family` and :mod:`populace_dynamics.data.deaths`;
each concept is also required to be the only label of its kind in the wave,
so a release that adds a second match fails loudly. The benefit-type value
codes are verified separately against the release's SAS ``VALUE`` blocks,
the discipline of
:func:`populace_dynamics.data.disability.verify_employment_status_codes`.

Amount conventions: amounts are whole dollars. The family codebooks state
"All missing data were assigned", so there is no missing sentinel; 0 means
no receipt (or, for a wife amount, no wife in the family unit). The
individual codebook codes 99,999 as "$99,999 or more" and the 2009 family
codebook codes 999,999 the same way; values are carried as recorded.
Accuracy codes are 0 (actual value), 1 (imputed by PSID staff) and 5
(median imputation). Negative amounts are rejected rather than passed
through.

What this module does not claim: Social Security income here is the
survey's self-reported calendar-year total, not an SSA administrative
benefit. SSI is asked as a separate PSID item; whether respondents keep the
two apart is not verifiable from these files. The self-reported type is a
survey answer, not an SSA entitlement code.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from populace_dynamics.data import disability, family, panels, psid

__all__ = [
    "SS_WAVES",
    "SS_INCOME_YEARS",
    "SS_TYPES",
    "ACCURACY_CODES",
    "PRIOR_YEAR_CODES",
    "read_family_social_security",
    "head_spouse_social_security_panel",
    "parse_value_label_blocks",
    "verify_social_security_type_codes",
    "read_individual_social_security",
]

#: Collection waves this module resolves; income year is ``wave - 1``.
SS_WAVES: tuple[int, ...] = (2009, 2011, 2013)
#: The income (reference) years those waves observe.
SS_INCOME_YEARS: tuple[int, ...] = tuple(wave - 1 for wave in SS_WAVES)

#: Self-reported benefit-type flags, in the individual file's G33A order.
SS_TYPES: tuple[str, ...] = (
    "disability",
    "retirement",
    "survivor",
    "dependent_of_disabled",
    "dependent_of_retired",
    "other",
)

#: Social Security amount accuracy codes (family and individual files).
ACCURACY_CODES: dict[int, str] = {
    0: "actual",
    1: "imputed_by_staff",
    5: "imputed_median",
}

#: R20 "received Social Security in the year before last" codes.
PRIOR_YEAR_CODES: dict[int, str] = {1: "yes", 5: "no", 8: "dk", 9: "na"}

#: Adjudicated family-file variables per wave, each with its exact label.
_FAMILY_VARS: dict[int, dict[str, tuple[str, str]]] = {
    2009: {
        "interview": ("ER42002", "2009 FAMILY INTERVIEW (ID) NUMBER"),
        "head_ss": ("ER46929", "HEAD SOCIAL SECURITY INCOME-2008"),
        "head_ss_acc": ("ER46930", "ACCURACY OF HEAD SOCIAL SECURITY-2008"),
        "spouse_ss": ("ER46931", "WIFE SOCIAL SECURITY INCOME-2008"),
        "spouse_ss_acc": (
            "ER46932",
            "ACCURACY OF WIFE SOCIAL SECURITY-2008",
        ),
        "ofum_ss": ("ER46933", "OFUM SOCIAL SECURITY INCOME-2008"),
        "ofum_ss_acc": ("ER46934", "ACCURACY OF OFUM SOCIAL SECURITY-2008"),
        "fu_ss_prior_year": (
            "ER46687",
            "R20 WTR RECD SOC SECURITY YR BEFORE LAST",
        ),
    },
    2011: {
        "interview": ("ER47302", "2011 FAMILY INTERVIEW (ID) NUMBER"),
        "head_ss": ("ER52337", "HEAD SOCIAL SECURITY INCOME-2010"),
        "head_ss_acc": ("ER52338", "ACCURACY OF HEAD SOCIAL SECURITY-2010"),
        "spouse_ss": ("ER52339", "WIFE SOCIAL SECURITY INCOME-2010"),
        "spouse_ss_acc": (
            "ER52340",
            "ACCURACY OF WIFE SOCIAL SECURITY-2010",
        ),
        "ofum_ss": ("ER52341", "OFUM SOCIAL SECURITY INCOME-2010"),
        "ofum_ss_acc": ("ER52342", "ACCURACY OF OFUM SOCIAL SECURITY-2010"),
        "fu_ss_prior_year": (
            "ER52088",
            "R20 WTR RECD SOC SECURITY YR BEFORE LAST",
        ),
    },
    2013: {
        "interview": ("ER53002", "2013 FAMILY INTERVIEW (ID) NUMBER"),
        "head_ss": ("ER58146", "HEAD SOCIAL SECURITY INCOME-2012"),
        "head_ss_acc": ("ER58147", "ACCURACY OF HEAD SOCIAL SECURITY-2012"),
        "spouse_ss": ("ER58148", "WIFE SOCIAL SECURITY INCOME-2012"),
        "spouse_ss_acc": (
            "ER58149",
            "ACCURACY OF WIFE SOCIAL SECURITY-2012",
        ),
        "ofum_ss": ("ER58150", "OFUM SOCIAL SECURITY INCOME-2012"),
        "ofum_ss_acc": ("ER58151", "ACCURACY OF OFUM SOCIAL SECURITY-2012"),
        "fu_ss_prior_year": (
            "ER57892",
            "R20 WTR RECD SOC SECURITY YR BEFORE LAST",
        ),
    },
}

#: Concept regexes that must match exactly one label per family wave. They
#: guard against a release that adds a second variable of the same kind
#: beside the adjudicated one.
_FAMILY_UNIQUE_CONCEPTS: dict[str, str] = {
    "head_ss": r"^HEAD SOCIAL SECURITY INCOME",
    "head_ss_acc": r"^ACCURACY OF HEAD SOCIAL SECURITY",
    "spouse_ss": r"^WIFE SOCIAL SECURITY INCOME",
    "spouse_ss_acc": r"^ACCURACY OF WIFE SOCIAL SECURITY",
    "ofum_ss": r"^OFUM SOCIAL SECURITY INCOME",
    "ofum_ss_acc": r"^ACCURACY OF OFUM SOCIAL SECURITY",
    "fu_ss_prior_year": r"^R20 WTR RECD SOC SECURITY",
}

#: Adjudicated individual-file variables per wave. ``type_code`` is the
#: 2009 single-code item; ``type_flags`` are the 2011+ mention flags in
#: :data:`SS_TYPES` order.
_INDIVIDUAL_VARS: dict[int, dict[str, object]] = {
    2009: {
        "amount": ("ER34031", "G34 AMT SOC SEC RCD 09"),
        "acc": ("ER34032", "G34 ACC SOC SEC AMT 09"),
        "type_code": ("ER34030", "G33 TYPE SOC SEC RCD 09"),
    },
    2011: {
        "amount": ("ER34143", "G34 AMT SOC SEC RCD 11"),
        "acc": ("ER34144", "G34 ACC SOC SEC AMT 11"),
        "type_flags": (
            ("ER34137", "G33A WTR SOC SEC TYPE DISABILITY 11"),
            ("ER34138", "G33A WTR SOC SEC TYPE RETIREMENT 11"),
            ("ER34139", "G33A WTR SOC SEC TYPE SURVIVOR 11"),
            ("ER34140", "G33A WTR SOC SEC TYPE DEP OF DISABLED 11"),
            ("ER34141", "G33A WTR SOC SEC TYPE DEP OF RETIRED 11"),
            ("ER34142", "G33A WTR SOC SEC TYPE OTHER 11"),
        ),
    },
    2013: {
        "amount": ("ER34250", "G34 AMT SOC SEC RCD 13"),
        "acc": ("ER34251", "G34 ACC SOC SEC AMT 13"),
        "type_flags": (
            ("ER34244", "G33A WTR SOC SEC TYPE DISABILITY 13"),
            ("ER34245", "G33A WTR SOC SEC TYPE RETIREMENT 13"),
            ("ER34246", "G33A WTR SOC SEC TYPE SURVIVOR 13"),
            ("ER34247", "G33A WTR SOC SEC TYPE DEP OF DISABLED 13"),
            ("ER34248", "G33A WTR SOC SEC TYPE DEP OF RETIRED 13"),
            ("ER34249", "G33A WTR SOC SEC TYPE OTHER 13"),
        ),
    },
}

_ID_VARS: dict[str, str] = {
    "ER30001": "1968 INTERVIEW NUMBER",
    "ER30002": "PERSON NUMBER 68",
}

#: 2009 single-code type item: code -> (expected label prefix, flags set).
#: Code 4 ("Any combination of codes 1-3 and 5-7") names no single type, so
#: every flag is unknown for it and ``type_combination`` is set instead.
_TYPE_CODE_2009: dict[int, tuple[str, str | None]] = {
    1: ("disability", "disability"),
    2: ("retirement", "retirement"),
    3: ("survivor benefits", "survivor"),
    4: ("any combination", None),
    5: ("dependent of disabled", "dependent_of_disabled"),
    6: ("dependent of retired", "dependent_of_retired"),
    7: ("other", "other"),
}

#: 2011+ mention flags: the keyword the code-1 label must carry.
_TYPE_FLAG_KEYWORDS: dict[str, str] = {
    "disability": "disability",
    "retirement": "retirement",
    "survivor": "survivor",
    "dependent_of_disabled": "dependent of disabled",
    "dependent_of_retired": "dependent of retired",
    "other": "other",
}

#: Mention-flag codes: 1 = mentioned, 5 = not mentioned; 0 (Inap.), 8 (DK)
#: and 9 (NA) carry no type information.
_FLAG_YES = 1
_FLAG_NO = 5
_FLAG_UNKNOWN = (0, 8, 9)
_TYPE_CODE_UNKNOWN = (0, 8, 9)

_IN_FAMILY_SEQUENCE = (1, 20)


def _require_wave(wave: int) -> int:
    wave = int(wave)
    if wave not in SS_WAVES:
        raise ValueError(
            f"Wave {wave} is outside the resolved Social Security waves "
            f"{SS_WAVES}."
        )
    return wave


def _assert_unique(
    labels: dict[str, str], pattern: str, var: str, context: str
) -> None:
    regex = re.compile(pattern, re.IGNORECASE)
    hits = sorted(
        name for name, label in labels.items() if regex.search(label)
    )
    if hits != [var]:
        raise ValueError(
            f"{context}: concept {pattern!r} matched {hits}; expected only "
            f"{var}. The release layout may have changed."
        )


def _check_income_year(label: str, wave: int) -> None:
    match = re.search(r"-((19|20)\d{2})\s*$", label)
    if match and int(match.group(1)) != wave - 1:
        raise ValueError(
            f"Wave {wave}: label {label!r} carries income year "
            f"{match.group(1)}, expected {wave - 1}."
        )


def _read_columns(
    sps_path: Path,
    txt_path: Path,
    names: list[str],
    nrows: int | None,
) -> pd.DataFrame:
    layout = psid.parse_sps_layout(sps_path).set_index("name")
    missing = [name for name in names if name not in layout.index]
    if missing:
        raise KeyError(f"Column(s) {missing} not found in {sps_path} layout")
    colspecs = [
        (int(layout.loc[name, "start"]) - 1, int(layout.loc[name, "end"]))
        for name in names
    ]
    return pd.read_fwf(
        txt_path,
        colspecs=colspecs,
        names=names,
        header=None,
        nrows=nrows,
    )


def _nonnegative_amount(series: pd.Series, what: str) -> pd.Series:
    values = pd.to_numeric(series, errors="raise").astype("int64")
    if (values < 0).any():
        raise ValueError(f"{what}: negative Social Security amount")
    return values


def _decode_codes(
    series: pd.Series, mapping: dict[int, str], what: str
) -> pd.Series:
    observed = {int(value) for value in pd.unique(series.dropna())}
    unexpected = observed - set(mapping)
    if unexpected:
        raise ValueError(
            f"{what}: undocumented code(s) {sorted(unexpected)}; the "
            f"documented domain is {sorted(mapping)}."
        )
    return series.astype("int64")


def read_family_social_security(
    wave: int,
    *,
    data_dir: Path | None = None,
    nrows: int | None = None,
) -> pd.DataFrame:
    """Read one wave's family-level Social Security income.

    Returns one row per responding family with ``interview``, ``head_ss``,
    ``head_ss_acc``, ``spouse_ss``, ``spouse_ss_acc``, ``ofum_ss``,
    ``ofum_ss_acc`` and ``fu_ss_prior_year`` (the raw R20 code: 1 yes,
    5 no, 8 DK, 9 NA, about income year ``wave - 2`` for anyone then in
    the family unit). Every variable is label-verified against
    :data:`_FAMILY_VARS`, each concept must be the wave's only label of its
    kind, and the income year in each amount label must be ``wave - 1``.
    """
    wave = _require_wave(wave)
    sps_path, txt_path = family._family_paths(wave, data_dir)
    labels = psid.parse_sps_labels(sps_path)
    entry = _FAMILY_VARS[wave]
    for concept, (var, label) in entry.items():
        family._verified(labels, var, label, wave)
        if concept in _FAMILY_UNIQUE_CONCEPTS:
            _assert_unique(
                labels,
                _FAMILY_UNIQUE_CONCEPTS[concept],
                var,
                f"family {wave}",
            )
        _check_income_year(labels[var], wave)
    names = [var for var, _ in entry.values()]
    raw = _read_columns(sps_path, txt_path, names, nrows)
    frame = pd.DataFrame(
        {concept: raw[var] for concept, (var, _) in entry.items()}
    )
    for concept in ("head_ss", "spouse_ss", "ofum_ss"):
        frame[concept] = _nonnegative_amount(
            frame[concept], f"family {wave} {concept}"
        )
    for concept in ("head_ss_acc", "spouse_ss_acc", "ofum_ss_acc"):
        frame[concept] = _decode_codes(
            frame[concept], ACCURACY_CODES, f"family {wave} {concept}"
        )
    frame["fu_ss_prior_year"] = _decode_codes(
        frame["fu_ss_prior_year"],
        PRIOR_YEAR_CODES,
        f"family {wave} fu_ss_prior_year",
    )
    frame["interview"] = frame["interview"].astype("int64")
    if frame["interview"].duplicated().any():
        raise ValueError(f"family {wave}: duplicate interview numbers")
    return frame


def _wave_people(
    waves: tuple[int, ...], data_dir: Path | None, nrows: int | None
) -> pd.DataFrame:
    """In-family person rows for ``waves`` (label-resolved demographics)."""

    people = panels.ind_person_period(
        panels.DEMOGRAPHIC_CONCEPTS,
        data_dir=data_dir,
        nrows=nrows,
        waves=list(waves),
    )
    low, high = _IN_FAMILY_SEQUENCE
    present = people["sequence"].between(low, high)
    return people.loc[present].reset_index(drop=True)


def head_spouse_social_security_panel(
    *,
    waves: tuple[int, ...] = SS_WAVES,
    data_dir: Path | None = None,
    nrows: int | None = None,
) -> pd.DataFrame:
    """Person-level head/wife Social Security income from the family files.

    Attaches each wave's family head and wife/"wife" amounts to persons
    through the individual file's interview number, keeping persons present
    in a responding family (sequence 1-20) whose relationship is head or
    wife/partner, with the relationship codes of
    :func:`populace_dynamics.data.family.family_earnings_panel`.
    ``income_year`` is ``wave - 1``.

    Columns: ``person_id``, ``wave``, ``income_year``, ``role``
    (``"head"``/``"spouse"``), ``ss_amount``, ``ss_acc``,
    ``fu_ss_prior_year`` (the family's raw R20 code about ``wave - 2``),
    ``age``, ``weight`` and ``interview``. A family with two persons coded
    head, or two coded wife/partner, is rejected as an ambiguous
    attachment.
    """
    use_waves = tuple(_require_wave(wave) for wave in waves)
    people = _wave_people(use_waves, data_dir, nrows)
    frames = []
    for wave in use_waves:
        fam = read_family_social_security(wave, data_dir=data_dir)
        wave_people = people[people["period"] == wave]
        head_codes, spouse_codes = family._relationship_codes(wave)
        for role, codes, amount, acc in (
            ("head", head_codes, "head_ss", "head_ss_acc"),
            ("spouse", spouse_codes, "spouse_ss", "spouse_ss_acc"),
        ):
            role_people = wave_people[wave_people["relationship"].isin(codes)]
            duplicated = role_people["interview"].duplicated(keep=False)
            if duplicated.any():
                bad = sorted(role_people.loc[duplicated, "interview"].unique())
                raise ValueError(
                    f"wave {wave}: ambiguous {role} attachment for family "
                    f"interview(s) {bad[:4]}"
                )
            merged = role_people.merge(
                fam[["interview", amount, acc, "fu_ss_prior_year"]],
                on="interview",
                how="inner",
                validate="one_to_one",
            )
            frames.append(
                pd.DataFrame(
                    {
                        "person_id": merged["person_id"].astype("int64"),
                        "wave": wave,
                        "income_year": wave - 1,
                        "role": role,
                        "ss_amount": merged[amount].astype("int64"),
                        "ss_acc": merged[acc].astype("int64"),
                        "fu_ss_prior_year": merged["fu_ss_prior_year"].astype(
                            "int64"
                        ),
                        "age": merged["age"].astype("int64"),
                        "weight": merged["weight"].astype("float64"),
                        "interview": merged["interview"].astype("int64"),
                    }
                )
            )
    panel = pd.concat(frames, ignore_index=True)
    if panel.duplicated(["person_id", "wave"]).any():
        raise ValueError("a person holds both head and spouse roles in a wave")
    return panel.sort_values(["person_id", "wave"]).reset_index(drop=True)


def _individual_labels(data_dir: Path | None) -> dict[str, str]:
    labels = psid.parse_sps_labels(
        psid.product_sps_path("ind2023er", data_dir)
    )
    psid.verify_labels(labels, _ID_VARS, context="ind2023er")
    return labels


def _individual_expected(wave: int) -> dict[str, str]:
    entry = _INDIVIDUAL_VARS[wave]
    expected: dict[str, str] = {}
    for key in ("amount", "acc", "type_code"):
        if key in entry:
            var, label = entry[key]
            expected[var] = label
    for var, label in entry.get("type_flags", ()):
        expected[var] = label
    return expected


_VALUE_HEADER_RE = re.compile(r"^\s*VALUE\s+(\S+)\s*$")
_VALUE_LINE_RE = re.compile(r"^\s*(-?\d+)\s*=\s*'((?:[^']|'')*)'")
_BLOCK_END_RE = re.compile(r"^\s*;\s*$")


def parse_value_label_blocks(path: str | Path) -> dict[str, dict[int, str]]:
    """Parse ``VALUE <fmt> ... ;`` blocks, ending each at a lone ``;`` line.

    :func:`populace_dynamics.data.disability.parse_sas_value_labels` ends a
    block at the first semicolon anywhere, which truncates blocks whose
    labels contain one (the 2009 type item's code 3 reads "Survivor
    benefits; dependent of deceased recipient"). PSID formats files close
    every block with a line holding only ``;``, so this parser ends a block
    there and keeps semicolons inside quoted labels. Continuation lines of
    long labels are skipped, as in the disability parser.
    """

    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"PSID SAS formats file not found: {path}")
    out: dict[str, dict[int, str]] = {}
    current: dict[int, str] | None = None
    for line in path.read_text(errors="replace").splitlines():
        header = _VALUE_HEADER_RE.match(line)
        if header:
            current = {}
            out[header.group(1)] = current
            continue
        if current is None:
            continue
        if _BLOCK_END_RE.match(line):
            current = None
            continue
        value = _VALUE_LINE_RE.match(line)
        if value:
            current[int(value.group(1))] = (
                value.group(2).replace("''", "'").strip()
            )
    if not out:
        raise ValueError(f"No VALUE block found in {path}")
    return out


def verify_social_security_type_codes(
    *,
    data_dir: Path | None = None,
    waves: tuple[int, ...] = SS_WAVES,
) -> dict[int, dict[str, str]]:
    """Verify the benefit-type value codes against the SAS formats file.

    For the 2009 single-code item every type code must carry its
    documented label; for the 2011+ mention flags, code 1 must read
    "... type was <type>" and code 5 "... type was not <type>". A release
    that renumbers or relabels the type items fails here instead of
    silently mislabelling every beneficiary's type.

    Returns ``{wave: {variable: format}}`` for the verified items.
    """
    fmt_path = disability.employment_status_formats_path(data_dir)
    value_labels = parse_value_label_blocks(fmt_path)
    assignments = disability.parse_sas_format_assignments(fmt_path)
    out: dict[int, dict[str, str]] = {}
    for wave in (_require_wave(wave) for wave in waves):
        entry = _INDIVIDUAL_VARS[wave]
        checked: dict[str, str] = {}
        if "type_code" in entry:
            var = entry["type_code"][0]
            fmt = assignments.get(var, f"{var}F")
            codes = value_labels.get(fmt, {})
            for code, (prefix, _) in _TYPE_CODE_2009.items():
                actual = codes.get(code, "").lower()
                if not actual.startswith(prefix):
                    raise ValueError(
                        f"Wave {wave}: type code {code} in format {fmt!r} "
                        f"is {actual!r}, expected a label starting "
                        f"{prefix!r}."
                    )
            checked[var] = fmt
        flags = entry.get("type_flags")
        for (var, _), type_name in (
            zip(flags, SS_TYPES, strict=True) if flags is not None else ()
        ):
            fmt = assignments.get(var, f"{var}F")
            codes = value_labels.get(fmt, {})
            keyword = _TYPE_FLAG_KEYWORDS[type_name]
            yes = " ".join(codes.get(_FLAG_YES, "").lower().split())
            no = " ".join(codes.get(_FLAG_NO, "").lower().split())
            if f"type was {keyword}" not in yes or "was not" in yes:
                raise ValueError(
                    f"Wave {wave}: flag {var} code 1 in format {fmt!r} is "
                    f"{yes!r}, expected 'type was {keyword}'."
                )
            if f"type was not {keyword}" not in no:
                raise ValueError(
                    f"Wave {wave}: flag {var} code 5 in format {fmt!r} is "
                    f"{no!r}, expected 'type was not {keyword}'."
                )
            checked[var] = fmt
        out[wave] = checked
    return out


def _flag(series: pd.Series, what: str) -> pd.Series:
    codes = _decode_codes(
        series,
        {_FLAG_YES: "yes", _FLAG_NO: "no", **dict.fromkeys(_FLAG_UNKNOWN, "")},
        what,
    )
    out = pd.Series(pd.NA, index=series.index, dtype="boolean")
    out[codes == _FLAG_YES] = True
    out[codes == _FLAG_NO] = False
    return out


def read_individual_social_security(
    *,
    waves: tuple[int, ...] = SS_WAVES,
    data_dir: Path | None = None,
    nrows: int | None = None,
) -> pd.DataFrame:
    """Person-level Social Security amount and self-reported type.

    Reads the individual file's label-verified G34 amount, its accuracy
    flag and the G33/G33A type items for ``waves``, joined to the
    label-resolved in-family demographic rows of the same wave (sequence
    1-20, the only persons the items can describe). The value codes are
    verified by :func:`verify_social_security_type_codes` first.

    Columns: ``person_id``, ``wave``, ``income_year``, ``relationship``,
    ``interview``, ``age``, ``weight``, ``ss_amount``, ``ss_acc``,
    ``type_<t>`` for each ``t`` in :data:`SS_TYPES` (nullable boolean:
    ``<NA>`` when the item carries no type information, including every
    zero-amount person) and ``type_combination`` (True only for the 2009
    "any combination" code, whose component types are not recorded).
    """
    use_waves = tuple(_require_wave(wave) for wave in waves)
    labels = _individual_labels(data_dir)
    expected: dict[str, str] = {}
    for wave in use_waves:
        expected.update(_individual_expected(wave))
    psid.verify_labels(labels, expected, context="ind2023er")
    verify_social_security_type_codes(data_dir=data_dir, waves=use_waves)

    wide = psid.read_psid(
        "ind2023er",
        columns=[*_ID_VARS, *expected],
        data_dir=data_dir,
        nrows=nrows,
    )
    person_id = wide["ER30001"].astype("int64") * 1000 + wide[
        "ER30002"
    ].astype("int64")
    people = _wave_people(use_waves, data_dir, nrows)
    frames = []
    for wave in use_waves:
        entry = _INDIVIDUAL_VARS[wave]
        amount_var = entry["amount"][0]
        acc_var = entry["acc"][0]
        frame = pd.DataFrame(
            {
                "person_id": person_id,
                "ss_amount": _nonnegative_amount(
                    wide[amount_var], f"individual {wave} amount"
                ),
                "ss_acc": _decode_codes(
                    wide[acc_var], ACCURACY_CODES, f"individual {wave} acc"
                ),
            }
        )
        combination = pd.Series(False, index=frame.index, dtype="boolean")
        if "type_code" in entry:
            code_var = entry["type_code"][0]
            known = {
                **{code: "" for code in _TYPE_CODE_2009},
                **dict.fromkeys(_TYPE_CODE_UNKNOWN, ""),
            }
            codes = _decode_codes(
                wide[code_var], known, f"individual {wave} type"
            )
            informative = ~codes.isin(_TYPE_CODE_UNKNOWN) & (codes != 4)
            for type_name in SS_TYPES:
                column = pd.Series(pd.NA, index=frame.index, dtype="boolean")
                matching = [
                    code
                    for code, (_, name) in _TYPE_CODE_2009.items()
                    if name == type_name
                ]
                column[informative] = codes[informative].isin(matching)
                frame[f"type_{type_name}"] = column
            combination[codes == 4] = True
        else:
            for (var, _), type_name in zip(
                entry["type_flags"], SS_TYPES, strict=True
            ):
                frame[f"type_{type_name}"] = _flag(
                    wide[var], f"individual {wave} {type_name}"
                )
        frame["type_combination"] = combination
        wave_people = people.loc[
            people["period"] == wave,
            ["person_id", "relationship", "interview", "age", "weight"],
        ]
        merged = wave_people.merge(
            frame, on="person_id", how="inner", validate="one_to_one"
        )
        merged.insert(1, "wave", wave)
        merged.insert(2, "income_year", wave - 1)
        frames.append(merged)
    out = pd.concat(frames, ignore_index=True)
    out["age"] = out["age"].astype("int64")
    out["weight"] = out["weight"].astype("float64")
    out["relationship"] = out["relationship"].astype("int64")
    out["interview"] = out["interview"].astype("int64")
    return out.sort_values(["person_id", "wave"]).reset_index(drop=True)
