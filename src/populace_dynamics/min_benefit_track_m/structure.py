"""Structural counts of the Track M population (counts only).

Plan ``critical-path-minimum-benefit-20260924.md`` (revision 2), section 4:
the Track M universe is the persons of the 2023 PSID wave (income year
2022) in a responding family unit (sequence 1-20) with a positive 2023
cross-section weight (ER35265), born 1960 or earlier by the first-estimates
birth-year law, and receiving OASDI in 2022 (the person-level amount
ER35219 above zero, reconciled for the reference person and spouse with
the family-file amounts ER85623 and ER85625).  Sex comes from ER32000.

Before the issue #42 registration, real-file work is limited to label
verification, structural counts (persons, dispositions and entitlement
classes) and aggregates that involve no threshold and no minimum (plan
section 8, "Rule for all lanes").  This module therefore reads labels,
codes and presence only.  It computes:

* the universe funnel: every 2023 sequence group, the weight and
  birth-year steps, receipt of OASDI and the reconciliation of the
  person-level receipt with the family-file amounts, as counts of persons;
* for the beneficiaries: counts by sex, role, birth-year band, the
  self-reported benefit-type mentions and the amount's accuracy code;
* the **availability** of the earnings years that years of coverage
  (plan field G6) would count: for each beneficiary, how many years of the
  window from the year of attaining 22 through the year of attaining 61
  fall before 1968 (before the PSID), in the biennial gap years
  (1997-2021, odd), in collected years with an observation in the
  earnings panel, or in collected years without one.

It never compares an earnings amount with any threshold, never counts
years of coverage, computes no PIA, threshold, minimum or share receiving
a minimum, and uses no weight beyond the universe's positive-weight
condition.  Amounts are read only to test receipt (above zero).
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from populace_dynamics.cohorts import psid2010
from populace_dynamics.data import deaths, disability, family, marriage, psid
from populace_dynamics.data import social_security_income as ssi
from populace_dynamics.estimates import career

__all__ = [
    "ANCHOR_2023",
    "BIRTH_YEAR_BANDS",
    "FAMILY_2023",
    "LAST_BIRTH_YEAR",
    "SOCIAL_SECURITY_2023",
    "TrackMStructureInputs",
    "availability_window",
    "load_structure_inputs",
    "read_2023_anchor",
    "read_2023_family_social_security",
    "structural_counts",
    "verify_2023_codes",
]

WAVE = 2023
INCOME_YEAR = 2022
#: Aged 62 or older in 2022 (plan section 4).
LAST_BIRTH_YEAR = 1960
#: Bands of the birth year: before the headline's exposed cohorts, the
#: headline's first three exposed birth years (1942-1944, plan section 4)
#: and the birth years both the headline and MS1 expose (1945-1960).  They
#: are counted, not classified: entitlement is plan item M4.
BIRTH_YEAR_BANDS: tuple[tuple[str, int, int], ...] = (
    ("born_1941_or_earlier", -10_000, 1941),
    ("born_1942_1944", 1942, 1944),
    ("born_1945_1960", 1945, 1960),
)
_OBSERVED_YEAR_BANDS: tuple[tuple[str, int, int], ...] = (
    ("0", 0, 0),
    ("1_9", 1, 9),
    ("10_19", 10, 19),
    ("20_29", 20, 29),
    ("30_39", 30, 39),
    ("40_plus", 40, 10_000),
)
#: The window start and end ages (G6 all ages; the flag window starts at
#: 22, the builder default; the end is the year before eligibility at 62,
#: a structural stand-in for the unknown entitlement year).
WINDOW_START_AGE = 22
WINDOW_END_AGE = 61
#: The earnings panel's first income year (``data/family.py``: the 1968
#: wave's 1967 income is not attachable to persons).
FIRST_PANEL_YEAR = 1968
#: Annual interviews through 1997; income years 1997, 1999, ..., 2021 were
#: never collected (biennial waves from 1999 report the prior even year).
_ANNUAL_LAST_INCOME_YEAR = 1996

#: Label-verified 2023 anchor variables (labels read 2026-09-24 from
#: IND2023ER.sps).
ANCHOR_2023 = psid2010.AnchorWaveLayout(
    wave=WAVE,
    variables={
        "interview": ("ER35101", "2023 INTERVIEW NUMBER"),
        "sequence": ("ER35102", "SEQUENCE NUMBER 23"),
        "relationship": ("ER35103", "RELATION TO REFERENCE PERSON 23"),
        "age": ("ER35104", "AGE OF INDIVIDUAL 23"),
        "reported_birth_year": ("ER35106", "YEAR INDIVIDUAL BORN 23"),
        "weight": ("ER35265", "CORE/IMM INDIVIDUAL CROSS-SECTION WT 23"),
    },
)
#: Person-level Social Security for income year 2022 (IND2023ER.sps).
SOCIAL_SECURITY_2023: dict[str, tuple[str, str]] = {
    "amount": ("ER35219", "G34 AMT SOC SEC RCD 23"),
    "acc": ("ER35220", "G34 ACC SOC SEC AMT 23"),
    "type_disability": ("ER35213", "G33A WTR SOC SEC TYPE DISABILITY 23"),
    "type_retirement": ("ER35214", "G33A WTR SOC SEC TYPE RETIREMENT 23"),
    "type_survivor": ("ER35215", "G33A WTR SOC SEC TYPE SURVIVOR 23"),
    "type_dependent_of_disabled": (
        "ER35216",
        "G33A WTR SOC SEC TYPE DEP OF DISABLED 23",
    ),
    "type_dependent_of_retired": (
        "ER35217",
        "G33A WTR SOC SEC TYPE DEP OF RETIRED 23",
    ),
    "type_other": ("ER35218", "G33A WTR SOC SEC TYPE OTHER 23"),
}
#: Family-file Social Security of the reference person and spouse
#: (FAM2023ER.sps).
FAMILY_2023: dict[str, tuple[str, str]] = {
    "interview": ("ER82002", "2023 FAMILY INTERVIEW (ID) NUMBER"),
    "rp_amount": ("ER85623", "REF PERSON SOCIAL SECURITY INCOME-2022"),
    "rp_acc": ("ER85624", "ACCURACY OF RP SOCIAL SECURITY-2022"),
    "spouse_amount": ("ER85625", "SPOUSE SOCIAL SECURITY INCOME-2022"),
    "spouse_acc": ("ER85626", "ACCURACY OF SPOUSE SOCIAL SECURITY-2022"),
}
_PERSON_VARS: dict[str, str] = {
    "ER30001": "1968 INTERVIEW NUMBER",
    "ER30002": "PERSON NUMBER 68",
}
#: The type flags' code-1 and code-5 labels must carry these words
#: (IND2023ER_formats.sas, ER35213F-ER35218F).
_TYPE_WORDS = {
    "type_disability": "disability",
    "type_retirement": "retirement",
    "type_survivor": "survivor",
    "type_dependent_of_disabled": "dependent of disabled",
    "type_dependent_of_retired": "dependent of retired",
    "type_other": "other",
}
_FLAG_YES, _FLAG_NO = 1, 5
_RP, _SPOUSE, _PARTNER = 10, 20, 22
_RELATIONSHIP_PREFIXES = {
    _RP: "reference person in 2023",
    _SPOUSE: "legal spouse in 2023",
    _PARTNER: "partner--cohabitor",
}
_SEQUENCE_GROUPS: tuple[tuple[str, int, int], ...] = (
    ("in_family", 1, 20),
    ("institution", 51, 59),
    ("moved_out", 71, 80),
    ("died", 81, 89),
)
_REPORTED_BIRTH_YEAR_NA = (0, 9999)


def _person_id(raw: pd.DataFrame) -> pd.Series:
    return raw["ER30001"].astype("int64") * 1000 + raw["ER30002"].astype(
        "int64"
    )


def read_2023_anchor(
    *, data_dir: Path | None = None, nrows: int | None = None
) -> pd.DataFrame:
    """The 2023 anchor columns and person-level Social Security.

    Columns: ``person_id``, ``interview``, ``sequence``, ``relationship``,
    ``age``, ``reported_birth_year`` (``<NA>`` for 0 or 9999), ``weight``,
    ``ss_amount``, ``ss_acc`` and the six ``type_*`` flag codes.  Every
    label is verified; the weight must be the wave's only "CROSS-SECTION
    WT 23" label.
    """

    labels = psid.parse_sps_labels(
        psid.product_sps_path("ind2023er", data_dir)
    )
    expected = {
        **ANCHOR_2023.labels(),
        **{var: label for var, label in SOCIAL_SECURITY_2023.values()},
    }
    psid.verify_labels(labels, expected, context="ind2023er 2023 Track M")
    hits = sorted(
        name
        for name, label in labels.items()
        if re.search(ANCHOR_2023.weight_concept, " ".join(label.split()))
    )
    if hits != [ANCHOR_2023.weight_variable]:
        raise ValueError(
            f"2023 cross-section weight concept matched {hits}; expected "
            f"only {ANCHOR_2023.weight_variable}"
        )
    raw = psid.read_psid(
        "ind2023er", columns=list(expected), data_dir=data_dir, nrows=nrows
    )
    frame = pd.DataFrame({"person_id": _person_id(raw)})
    for var, column in ANCHOR_2023.columns().items():
        frame[column] = raw[var]
    for column, (var, _) in SOCIAL_SECURITY_2023.items():
        frame["ss_" + column if column in ("amount", "acc") else column] = raw[
            var
        ]
    for column in ("interview", "sequence", "relationship", "age"):
        frame[column] = frame[column].astype("int64")
    frame["weight"] = frame["weight"].astype("float64")
    if (frame["weight"] < 0).any():
        raise ValueError("negative 2023 cross-section weight")
    if (frame["ss_amount"] < 0).any():
        raise ValueError("negative 2023 Social Security amount")
    reported = frame["reported_birth_year"].astype("Int64")
    frame["reported_birth_year"] = reported.mask(
        reported.isin(_REPORTED_BIRTH_YEAR_NA)
    )
    if frame["person_id"].duplicated().any():
        raise ValueError("duplicate person_id in the individual file")
    return frame


def read_2023_family_social_security(
    *, data_dir: Path | None = None
) -> pd.DataFrame:
    """Reference-person and spouse Social Security, income year 2022.

    Columns: ``interview``, ``rp_amount``, ``rp_acc``, ``spouse_amount``
    and ``spouse_acc``, label-verified against FAM2023ER.sps.
    """

    sps_path, txt_path = family._family_paths(WAVE, data_dir)
    labels = psid.parse_sps_labels(sps_path)
    psid.verify_labels(
        labels,
        {var: label for var, label in FAMILY_2023.values()},
        context="FAM2023ER Track M",
    )
    layout = psid.parse_sps_layout(sps_path).set_index("name")
    names = [var for var, _ in FAMILY_2023.values()]
    raw = pd.read_fwf(
        txt_path,
        colspecs=[
            (
                int(layout.loc[name, "start"]) - 1,
                int(layout.loc[name, "end"]),
            )
            for name in names
        ],
        names=names,
        header=None,
    )
    frame = raw.rename(
        columns={var: column for column, (var, _) in FAMILY_2023.items()}
    ).astype("int64")
    if frame["interview"].duplicated().any():
        raise ValueError("duplicate 2023 family interview number")
    if (frame[["rp_amount", "spouse_amount"]] < 0).any().any():
        raise ValueError("negative family-file Social Security")
    return frame


def verify_2023_codes(*, data_dir: Path | None = None) -> dict[str, str]:
    """Check the type-flag, accuracy and relationship value codes.

    Returns ``{variable: format}`` for the checked variables.
    """

    path = disability.employment_status_formats_path(data_dir)
    blocks = ssi.parse_value_label_blocks(path)
    assignments = disability.parse_sas_format_assignments(path)
    checked: dict[str, str] = {}
    for column, word in _TYPE_WORDS.items():
        var = SOCIAL_SECURITY_2023[column][0]
        fmt = assignments.get(var, f"{var}F")
        codes = blocks.get(fmt, {})
        yes = " ".join(codes.get(_FLAG_YES, "").lower().split())
        no = " ".join(codes.get(_FLAG_NO, "").lower().split())
        if f"was {word}" not in yes or f"was not {word}" not in no:
            raise ValueError(
                f"{var} ({fmt}): codes 1/5 read {yes!r}/{no!r}, expected "
                f"'was {word}' / 'was not {word}'"
            )
        checked[var] = fmt
    acc = SOCIAL_SECURITY_2023["acc"][0]
    fmt = assignments.get(acc, f"{acc}F")
    codes = blocks.get(fmt, {})
    if "imputed" not in codes.get(1, "").lower() or "median" not in (
        codes.get(5, "").lower()
    ):
        raise ValueError(f"{acc} ({fmt}): unexpected accuracy codes {codes}")
    checked[acc] = fmt
    relationship = ANCHOR_2023.variables["relationship"][0]
    fmt = assignments.get(relationship, f"{relationship}F")
    codes = blocks.get(fmt, {})
    for code, prefix in _RELATIONSHIP_PREFIXES.items():
        label = " ".join(codes.get(code, "").lower().split())
        if not label.startswith(prefix):
            raise ValueError(
                f"{relationship} ({fmt}) code {code} reads {label!r}, "
                f"expected a label starting {prefix!r}"
            )
    checked[relationship] = fmt
    return checked


@dataclass(frozen=True)
class TrackMStructureInputs:
    """The frames the structural counts read, with file provenance."""

    anchor: pd.DataFrame
    family_social_security: pd.DataFrame
    death_records: pd.DataFrame
    marriage_history: pd.DataFrame
    observed_earnings: pd.DataFrame
    design: pd.DataFrame
    codes: Mapping[str, str]
    provenance: Mapping[str, Any] = field(default_factory=dict)


def load_structure_inputs(
    *, data_dir: Path | None = None
) -> TrackMStructureInputs:
    """Read every input from the staged PSID, recording file hashes."""

    root = psid._resolve_data_dir(data_dir)
    with psid2010.record_files_read(root) as files:
        codes = verify_2023_codes(data_dir=data_dir)
        anchor = read_2023_anchor(data_dir=data_dir)
        family_ss = read_2023_family_social_security(data_dir=data_dir)
        death_records = deaths.read_death_records(data_dir=data_dir)
        history = marriage.marriage_history(data_dir=data_dir)
        earnings = family.family_earnings_panel(
            waves=family.FAMILY_WAVES, data_dir=data_dir
        )
        from populace_dynamics.cohorts import age67

        design = age67.read_design_variables(data_dir=data_dir)
    if not files:
        raise RuntimeError("no PSID file was recorded as read")
    return TrackMStructureInputs(
        anchor=anchor,
        family_social_security=family_ss,
        death_records=death_records,
        marriage_history=history,
        observed_earnings=earnings,
        design=design,
        codes=codes,
        provenance={
            "psid_data_dir": str(root),
            "psid_files_sha256": dict(sorted(files.items())),
        },
    )


def availability_window(birth_year: int) -> dict[str, Any]:
    """The flag window's years for one birth year, by collection status.

    From the year of attaining 22 through the year of attaining 61 (and
    never past 2022): ``pre_panel`` years before 1968, ``gap`` years (odd
    income years 1997-2021, never collected) and ``collected`` years.
    """

    start = birth_year + WINDOW_START_AGE
    end = min(birth_year + WINDOW_END_AGE, INCOME_YEAR)
    years = range(start, end + 1)
    pre = [y for y in years if y < FIRST_PANEL_YEAR]
    gap = [
        y
        for y in years
        if y >= FIRST_PANEL_YEAR and y > _ANNUAL_LAST_INCOME_YEAR and y % 2
    ]
    collected = [
        y for y in years if y >= FIRST_PANEL_YEAR and y not in set(gap)
    ]
    return {
        "start": start,
        "end": end,
        "pre_panel": pre,
        "gap": gap,
        "collected": collected,
    }


def _band(value: int, bands: tuple[tuple[str, int, int], ...]) -> str:
    for name, low, high in bands:
        if low <= value <= high:
            return name
    raise ValueError(f"{value} is in no band")


def _sequence_group(sequence: int) -> str:
    for name, low, high in _SEQUENCE_GROUPS:
        if low <= sequence <= high:
            return name
    return "not_in_wave" if sequence == 0 else f"sequence_{sequence}"


def _flag_state(code: int) -> str:
    if code == _FLAG_YES:
        return "mentioned"
    if code == _FLAG_NO:
        return "not_mentioned"
    return "unknown"


def _counter(values) -> dict[str, int]:
    return {str(k): int(v) for k, v in sorted(Counter(values).items())}


def structural_counts(inputs: TrackMStructureInputs) -> dict[str, Any]:
    """The Track M universe funnel and availability counts (persons only)."""

    anchor = inputs.anchor.copy()
    funnel: dict[str, Any] = {"ind2023er_records": int(len(anchor))}
    funnel["sequence_groups_2023"] = _counter(
        anchor["sequence"].map(_sequence_group)
    )
    in_family = anchor[anchor["sequence"].between(1, 20)]
    base = in_family[in_family["weight"] > 0].copy()
    funnel["in_family"] = int(len(in_family))
    funnel["in_family_zero_weight"] = int((in_family["weight"] <= 0).sum())
    funnel["in_family_positive_weight"] = int(len(base))

    # The law's derived-age clause supports birth years up to 2016
    # (``career.DERIVED_BIRTH_MAX``); a 2023 age of 0-5 implies a later
    # year, so those children are born after 1960 on any reading and are
    # counted out before the law runs.
    young = base["age"].between(0, 2022 - career.DERIVED_BIRTH_MAX - 1)
    funnel["age_0_5_counted_out_before_birth_law"] = int(young.sum())
    base = base[~young].copy()
    seed = pd.DataFrame(
        {
            "person_id": base["person_id"].astype("int64"),
            "year": INCOME_YEAR,
            "anchor_wave": WAVE,
            "age": base["age"].astype("int64"),
        }
    )
    universe = set(int(pid) for pid in base["person_id"])
    history = inputs.marriage_history
    earnings = inputs.observed_earnings
    records = career.derive_birth_years(
        history[history["person_id"].isin(universe)],
        earnings[earnings["person_id"].isin(universe)],
        seed_coordinates=seed,
        required_person_ids=universe,
    )
    births = {record.person_id: record for record in records}
    if set(births) != universe:
        raise AssertionError("birth dispositions are not universe-total")
    base["birth_year"] = base["person_id"].map(
        lambda pid: births[int(pid)].birth_year
    )
    base["birth_source"] = base["person_id"].map(
        lambda pid: births[int(pid)].source.value
    )
    funnel["birth_source"] = _counter(base["birth_source"])
    resolved = base[base["birth_year"].notna()].copy()
    resolved["birth_year"] = resolved["birth_year"].astype("int64")
    funnel["birth_year_unresolved"] = int(base["birth_year"].isna().sum())
    aged = resolved[resolved["birth_year"] <= LAST_BIRTH_YEAR].copy()
    funnel["born_1960_or_earlier"] = int(len(aged))
    funnel["born_1961_or_later"] = int(
        (resolved["birth_year"] > LAST_BIRTH_YEAR).sum()
    )
    aged["receives_person_level"] = aged["ss_amount"] > 0
    funnel["receives_oasdi_person_level"] = int(
        aged["receives_person_level"].sum()
    )
    funnel["no_person_level_receipt"] = int(
        (~aged["receives_person_level"]).sum()
    )

    # Reconciliation with the family file for the reference person and
    # spouse (counts of agreement only; the rule is plan item M3/M4's).
    fam = inputs.family_social_security.set_index("interview")
    role = aged["relationship"].map(
        {_RP: "reference_person", _SPOUSE: "spouse", _PARTNER: "partner"}
    )
    aged["role"] = role.fillna("other_member")
    reconciliation: dict[str, dict[str, int]] = {}
    for name, column in (
        ("reference_person", "rp_amount"),
        ("spouse", "spouse_amount"),
        ("partner", "spouse_amount"),
    ):
        members = aged[aged["role"] == name]
        family_amount = members["interview"].map(fam[column])
        missing = int(family_amount.isna().sum())
        family_positive = family_amount.fillna(0) > 0
        person_positive = members["receives_person_level"]
        reconciliation[name] = {
            "persons": int(len(members)),
            "family_record_missing": missing,
            "both_positive": int((person_positive & family_positive).sum()),
            "person_only": int((person_positive & ~family_positive).sum()),
            "family_only": int((~person_positive & family_positive).sum()),
            "neither": int((~person_positive & ~family_positive).sum()),
        }
    funnel["reconciliation_with_family_file"] = reconciliation

    beneficiaries = aged[aged["receives_person_level"]].copy()
    sex = inputs.death_records.set_index("person_id")["sex"]
    beneficiaries["sex"] = beneficiaries["person_id"].map(sex).fillna("na")
    beneficiaries["birth_band"] = beneficiaries["birth_year"].map(
        lambda year: _band(int(year), BIRTH_YEAR_BANDS)
    )
    summary: dict[str, Any] = {
        "persons": int(len(beneficiaries)),
        "sex": _counter(beneficiaries["sex"]),
        "role": _counter(beneficiaries["role"]),
        "birth_band": _counter(beneficiaries["birth_band"]),
        "birth_band_by_sex": {
            band: _counter(group["sex"])
            for band, group in beneficiaries.groupby("birth_band")
        },
        "birth_source": _counter(beneficiaries["birth_source"]),
        "amount_accuracy_code": _counter(beneficiaries["ss_acc"]),
        "type_mentions": {
            column: _counter(beneficiaries[column].map(_flag_state))
            for column in _TYPE_WORDS
        },
    }
    design = inputs.design.set_index("person_id")
    strata = beneficiaries["person_id"].map(design["stratum"])
    clusters = beneficiaries["person_id"].map(design["cluster"])
    summary["design"] = {
        "strata": int(strata.nunique()),
        "stratum_cluster_pairs": int(
            pd.DataFrame({"s": strata, "c": clusters})
            .drop_duplicates()
            .shape[0]
        ),
        "family_units": int(beneficiaries["interview"].nunique()),
    }

    # Availability of the years G6 would count (observation, not amount).
    observed = earnings[
        earnings["person_id"].isin(set(beneficiaries["person_id"]))
    ]
    observed_years = {
        int(pid): set(int(p) for p in group["period"])
        for pid, group in observed.groupby("person_id")
    }
    rows = []
    for pid, birth_year in zip(
        beneficiaries["person_id"], beneficiaries["birth_year"], strict=True
    ):
        window = availability_window(int(birth_year))
        seen = observed_years.get(int(pid), set())
        collected = window["collected"]
        rows.append(
            {
                "birth_band": _band(int(birth_year), BIRTH_YEAR_BANDS),
                "window_years": window["end"] - window["start"] + 1,
                "pre_panel": len(window["pre_panel"]),
                "gap": len(window["gap"]),
                "collected_observed": sum(1 for y in collected if y in seen),
                "collected_not_observed": sum(
                    1 for y in collected if y not in seen
                ),
                "observed_any_age": len([y for y in seen if y <= INCOME_YEAR]),
            }
        )
    table = pd.DataFrame(rows)
    availability: dict[str, Any] = {
        "window": (
            "from the year of attaining 22 through the year of attaining "
            "61, capped at 2022 (a structural stand-in: the entitlement "
            "year that ends G6's count is plan item M4)"
        ),
        "person_years": {
            column: int(table[column].sum())
            for column in (
                "window_years",
                "pre_panel",
                "gap",
                "collected_observed",
                "collected_not_observed",
            )
        },
        "persons_by_observed_window_years": _counter(
            table["collected_observed"].map(
                lambda n: _band(int(n), _OBSERVED_YEAR_BANDS)
            )
        ),
        "persons_by_observed_years_any_age": _counter(
            table["observed_any_age"].map(
                lambda n: _band(int(n), _OBSERVED_YEAR_BANDS)
            )
        ),
        "persons_with_no_observed_year": int(
            (table["observed_any_age"] == 0).sum()
        ),
        "persons_with_window_before_1968_entirely": int(
            (table["pre_panel"] == table["window_years"]).sum()
        ),
        "by_birth_band": {},
    }
    for band, group in table.groupby("birth_band"):
        availability["by_birth_band"][band] = {
            "persons": int(len(group)),
            "person_years": {
                column: int(group[column].sum())
                for column in (
                    "window_years",
                    "pre_panel",
                    "gap",
                    "collected_observed",
                    "collected_not_observed",
                )
            },
            "persons_by_observed_window_years": _counter(
                group["collected_observed"].map(
                    lambda n: _band(int(n), _OBSERVED_YEAR_BANDS)
                )
            ),
        }
    return {
        "funnel": funnel,
        "beneficiaries_62_plus": summary,
        "years_of_coverage_availability": availability,
    }
