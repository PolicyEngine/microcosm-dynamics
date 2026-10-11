"""Group attributes for the MINT breakdowns: a side frame by person_id.

The four blind tests' populations (the psid2010 cohorts of the 2011 and
2009 anchor waves, the age-67 observations of exercise 2, and Track M's
2023 universe) carry sex, age and marital status but not race and
ethnicity, education or country of birth. This module adds those three
as a separate frame keyed by ``person_id``, with its own file audit and
SHA-256 seal, so the existing cohorts, their frames and the digests the
committed runs pin are untouched (the U2 "neither edits nor extends"
precedent; the readers are
:mod:`populace_dynamics.data.group_attributes_psid`).

Resolution rules (``RULES_VERSION``), decided 2026-10-01:

* **Race and Hispanic origin** are fixed person attributes, resolved from
  every staged head/wife report 1985-2023 whatever the anchor. Each
  report is harmonized through its wave's code frame
  (:func:`~populace_dynamics.data.group_attributes_psid.race_ethnicity_report`).
  A report is *complete* when it is Hispanic, or not Hispanic with every
  race mention known. The person's value is their **most recent complete
  report** (the latest self-identification; a person is head or wife at
  most once per wave). ``race_ethnicity_n_distinct`` counts the distinct
  four-way readings among their complete reports, so conflicts are
  visible. ``hispanic`` comes from the selected report; a person with no
  complete report takes it from their most recent report that shows it.
* **Country of birth** is likewise fixed and comes from the most recent
  head/wife report 2013-2023 that classifies it (United States, U.S.
  territory or foreign country); DK/NA and the few pairs that contradict
  the skip pattern (``inconsistent``) never decide it.
* **Education** can change, so it is resolved **as of the population's
  last anchor wave** (``education_cutoff_wave = max(anchor_waves)``):
  the most recent reported years of schooling at or before it, from the
  individual-file series (heads, wives and OFUMs aged 16 or older), with
  "completed no grades" (0 years) for a head or wife whose family-file
  code says so.
* **No value is guessed.** A person never head or wife in the window has
  ``race_ethnicity_status == "never_head_or_spouse"`` (OFUMs; the PSID
  asks race only of heads and wives), and likewise for country of
  birth; other unknowns name their reason. Every requested person gets
  exactly one row, and the provenance counts each status.

Report categories come from the data-driven schemes in
``data/external/group_category_schemes_v1.json`` (SSA's MINT 8 Table
User Guide; Butrica and Uccello 2004's cleared definitions extract
``exercise2-definitions-cleared-20260924.md``, lines 58–59, 86–87 and
229–231): each scheme column has a ``<column>_status`` of ``assigned``,
``attribute_unknown`` or ``unresolved:<reason>`` for values the source
does not place (a U.S.-territory birth for MINT 8; the Report's education
rows, which the extract explicitly leaves undefined at lines 231 and 327).

This module computes attributes only. It opens no outcome and computes
no group share; tabulation code receives its frame.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from numbers import Integral
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.cohorts import psid2010
from populace_dynamics.data import group_attributes_psid as gap
from populace_dynamics.data import psid

__all__ = [
    "RULES_VERSION",
    "SCHEMES_PATH",
    "SCHEMES_SHA256",
    "FRAME_COLUMNS",
    "GroupAttributeInputs",
    "GroupAttributes",
    "load_schemes",
    "load_group_attribute_inputs",
    "input_frames_sha256",
    "build_group_attributes",
    "load_group_attributes",
    "content_sha256",
    "apply_category_scheme",
]

RULES_VERSION = "g1-rules-1"

_REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMES_PATH = (
    _REPO_ROOT / "data" / "external" / "group_category_schemes_v1.json"
)
#: SHA-256 of the committed scheme file; a different file is refused.
SCHEMES_SHA256 = (
    "243833aa0fa1cca8968df4b8e93753d92e77beeee8939f3782310812a3016797"
)

KNOWN = "known"
NEVER_HEAD_OR_SPOUSE = "never_head_or_spouse"
HISPANIC_ORIGIN_NOT_ASKED = "hispanic_origin_not_asked"
DK_NA_REFUSED = "dk_na_refused"
UNDOCUMENTED_ZERO_MEANING = "undocumented_zero_meaning"
INCONSISTENT_ONLY = "inconsistent"
NO_REPORT_BY_CUTOFF = "no_report_by_cutoff"
ASSIGNED = "assigned"
ATTRIBUTE_UNKNOWN = "attribute_unknown"

#: The four-way race/ethnicity codes every race scheme maps.
RACE_ETHNICITY_CODES: tuple[str, ...] = (
    "hispanic",
    "white_non_hispanic",
    "black_non_hispanic",
    "other_non_hispanic",
)
#: The country-of-birth values a country scheme maps.
COUNTRY_OF_BIRTH_CODES: tuple[str, ...] = (
    gap.UNITED_STATES,
    gap.US_TERRITORY,
    gap.FOREIGN_COUNTRY,
)
_EDUCATION_DOMAIN = (0, gap.EDUCATION_YEARS_RANGE[1])

_ATTRIBUTE_COLUMNS: dict[str, str] = {
    "person_id": "int64",
    "hispanic": "boolean",
    "race_mentions": "string",
    "race_ethnicity_status": "string",
    "race_ethnicity_source_wave": "Int64",
    "race_ethnicity_source_role": "string",
    "race_ethnicity_source_variables": "string",
    "race_ethnicity_source_mentions": "string",
    "race_ethnicity_hispanic_basis": "string",
    "race_ethnicity_n_reports": "Int64",
    "race_ethnicity_n_distinct": "Int64",
    "hispanic_source_wave": "Int64",
    "hispanic_source_role": "string",
    "hispanic_source_variables": "string",
    "hispanic_source_mentions": "string",
    "education_years": "Int64",
    "education_status": "string",
    "education_source_wave": "Int64",
    "education_source_variables": "string",
    "education_source_role": "string",
    "education_source_mentions": "string",
    "education_n_reports": "Int64",
    "education_n_distinct": "Int64",
    "country_of_birth": "string",
    "country_of_birth_status": "string",
    "country_of_birth_source_wave": "Int64",
    "country_of_birth_source_role": "string",
    "country_of_birth_source_variables": "string",
    "country_of_birth_source_mentions": "string",
    "country_of_birth_n_reports": "Int64",
    "country_of_birth_n_distinct": "Int64",
}
#: The scheme columns of the default schemes, each followed by its
#: ``_status`` column, in frame order.
_DEFAULT_SCHEME_COLUMNS: tuple[str, ...] = (
    "race_ethnicity_mint8",
    "education_mint8",
    "country_of_birth_mint8",
    "race_ethnicity_report4",
    "education_report3",
)
FRAME_COLUMNS: tuple[str, ...] = (
    *_ATTRIBUTE_COLUMNS,
    *(
        name
        for column in _DEFAULT_SCHEME_COLUMNS
        for name in (column, f"{column}_status")
    ),
)
#: The attribute each scheme dimension reads.
_DIMENSION_INPUT = {
    "race_ethnicity": "race_ethnicity",
    "education": "education_years",
    "country_of_birth": "country_of_birth",
}


# --------------------------------------------------------------------------
# Schemes
# --------------------------------------------------------------------------
def load_schemes(path: Path | None = None) -> dict[str, Any]:
    """Load and validate the category schemes, refusing a changed file.

    With ``path`` given (tests), the SHA-256 pin is not applied, but the
    file must still pass :func:`_validate_schemes`.
    """

    target = SCHEMES_PATH if path is None else Path(path)
    raw = target.read_bytes()
    if path is None:
        digest = hashlib.sha256(raw).hexdigest()
        if digest != SCHEMES_SHA256:
            raise ValueError(
                f"{target} has SHA-256 {digest}, expected the pinned "
                f"{SCHEMES_SHA256}"
            )
    data = json.loads(raw)
    if data.get("schema_version") != "group_category_schemes.v1":
        raise ValueError(f"{target} is not a v1 scheme file")
    _validate_schemes(data)
    if path is None:
        for source in data["sources"].values():
            if "committed_file" not in source:
                continue
            source_path = _REPO_ROOT / source["committed_file"]
            digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
            if digest != source["sha256"]:
                raise ValueError(f"scheme source {source_path} changed")
    return data


def _validate_schemes(data: Mapping[str, Any]) -> None:
    """Refuse a scheme that leaves a value neither placed nor unresolved."""

    columns: set[str] = set()
    for scheme_id, scheme in data["schemes"].items():
        for dimension, spec in scheme["dimensions"].items():
            where = f"scheme {scheme_id} {dimension}"
            if dimension not in _DIMENSION_INPUT:
                raise ValueError(f"{where}: unknown dimension")
            column = spec["column"]
            new_columns = {column, f"{column}_status"}
            if new_columns & (columns | set(_ATTRIBUTE_COLUMNS)):
                raise ValueError(f"{where}: column {column} is taken")
            columns.update(new_columns)
            if dimension == "education":
                covered: list[int] = []
                for band in [*spec["bands"], *spec["unresolved_bands"]]:
                    hi = (
                        _EDUCATION_DOMAIN[1]
                        if band["max"] is None
                        else band["max"]
                    )
                    covered.extend(range(band["min"], hi + 1))
                want = list(
                    range(_EDUCATION_DOMAIN[0], _EDUCATION_DOMAIN[1] + 1)
                )
                if sorted(covered) != want:
                    raise ValueError(
                        f"{where}: bands must cover each of years "
                        f"{want[0]}-{want[-1]} exactly once"
                    )
                continue
            codes = (
                RACE_ETHNICITY_CODES
                if dimension == "race_ethnicity"
                else COUNTRY_OF_BIRTH_CODES
            )
            placed = set(spec["categories"]) | set(spec.get("unresolved", {}))
            if placed != set(codes) or set(spec["categories"]) & set(
                spec.get("unresolved", {})
            ):
                raise ValueError(
                    f"{where}: categories and unresolved must partition "
                    f"{codes}"
                )
            if dimension == "race_ethnicity" and spec[
                "multiple_races"
            ] not in (*RACE_ETHNICITY_CODES, "first_mention"):
                raise ValueError(f"{where}: bad multiple_races rule")


def _race_code(
    hispanic: Any, races: str | None, multiple_races: str
) -> str | None:
    """The four-way code of one person's selected report, or None."""

    if hispanic is pd.NA or hispanic is None or pd.isna(hispanic):
        return None
    if not isinstance(hispanic, (bool, np.bool_)):
        raise ValueError("hispanic must be a boolean or unknown")
    if bool(hispanic):
        return "hispanic"
    if races is None or races is pd.NA or pd.isna(races):
        return None
    mentions = races.split("|")
    if any(mention not in gap.RACE_CATEGORIES for mention in mentions):
        raise ValueError("race_mentions contains undocumented categories")
    if len(mentions) > 1 or gap.MORE_THAN_TWO in mentions:
        if multiple_races != "first_mention":
            return multiple_races
        mentions = mentions[:1]
    single = mentions[0]
    if single == gap.WHITE:
        return "white_non_hispanic"
    if single == gap.BLACK:
        return "black_non_hispanic"
    return "other_non_hispanic"


def apply_category_scheme(
    frame: pd.DataFrame, dimension: str, spec: Mapping[str, Any]
) -> tuple[pd.Series, pd.Series]:
    """Map one attribute to a scheme's labels: ``(labels, status)``.

    ``frame`` holds the attribute columns (``hispanic`` and
    ``race_mentions`` for race and ethnicity, ``education_years``,
    ``country_of_birth``). A known value the scheme places gets its label
    and ``assigned``; one it leaves unresolved gets NA and
    ``unresolved:<reason key>``; an unknown attribute gets NA and
    ``attribute_unknown``.
    """

    n = len(frame)
    labels: list[Any] = [pd.NA] * n
    status: list[str] = [ATTRIBUTE_UNKNOWN] * n
    if dimension == "race_ethnicity":
        values = [
            _race_code(h, r, spec["multiple_races"])
            for h, r in zip(
                frame["hispanic"], frame["race_mentions"], strict=True
            )
        ]
        for i, code in enumerate(values):
            if code is None:
                continue
            if code in spec["categories"]:
                labels[i], status[i] = spec["categories"][code], ASSIGNED
            elif code in spec.get("unresolved", {}):
                status[i] = f"unresolved:{code}"
            else:
                raise ValueError(f"race and ethnicity {code!r} is not mapped")
    elif dimension == "country_of_birth":
        unresolved = spec.get("unresolved", {})
        for i, value in enumerate(frame["country_of_birth"]):
            if value is pd.NA or pd.isna(value):
                continue
            if value in spec["categories"]:
                labels[i], status[i] = spec["categories"][value], ASSIGNED
            elif value in unresolved:
                status[i] = f"unresolved:{value}"
            else:
                raise ValueError(f"country of birth {value!r} is not mapped")
    elif dimension == "education":
        bands = [
            (b["min"], b["max"], b["label"], None) for b in spec["bands"]
        ] + [
            (b["min"], b["max"], None, b["status"])
            for b in spec["unresolved_bands"]
        ]
        for i, years in enumerate(frame["education_years"]):
            if years is pd.NA or pd.isna(years):
                continue
            if isinstance(years, (bool, np.bool_)) or not isinstance(
                years, Integral
            ):
                raise ValueError("education_years must be integers")
            y = int(years)
            if not _EDUCATION_DOMAIN[0] <= y <= _EDUCATION_DOMAIN[1]:
                raise ValueError(f"education_years {y} is undocumented")
            hits = [
                b for b in bands if b[0] <= y and (b[1] is None or y <= b[1])
            ]
            if len(hits) != 1:
                raise ValueError(f"{y} years fall in {len(hits)} bands")
            _, _, label, reason = hits[0]
            if label is None:
                status[i] = f"unresolved:{reason}"
            else:
                labels[i], status[i] = label, ASSIGNED
    else:
        raise ValueError(f"unknown dimension {dimension!r}")
    return (
        pd.Series(labels, index=frame.index, dtype="string"),
        pd.Series(status, index=frame.index, dtype="string"),
    )


# --------------------------------------------------------------------------
# Inputs
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class GroupAttributeInputs:
    """Raw, documented codes the pure builder consumes.

    ``reports``: one row per present head or spouse per wave
    (:func:`~populace_dynamics.data.group_attributes_psid.head_spouse_reports`).
    ``education``: person-waves with an individual education code other
    than 0, plus present heads and spouses with code 0 (who may have
    completed no grades), with their role's family COMPLETED ED code.
    ``universe``: every person in the individual file (sorted).
    """

    reports: pd.DataFrame
    education: pd.DataFrame
    universe: pd.Series
    provenance: Mapping[str, Any] = field(default_factory=dict)


def _education_rows(
    individual: pd.DataFrame, reports: pd.DataFrame
) -> pd.DataFrame:
    roles = reports[["person_id", "wave", "role", "family_education_code"]]
    merged = individual[["person_id", "wave", "education_code"]].merge(
        roles, on=["person_id", "wave"], how="left"
    )
    keep = (merged["education_code"] != 0) | merged["role"].notna()
    out = merged.loc[keep].copy()
    out["role"] = out["role"].astype("string")
    out["family_education_code"] = out["family_education_code"].astype("Int64")
    return out.sort_values(["person_id", "wave"]).reset_index(drop=True)


def _frame_digest(digest: Any, name: str, frame: pd.DataFrame) -> None:
    digest.update(f"{name}\n".encode())
    digest.update(json.dumps([str(c) for c in frame.columns]).encode())
    digest.update(json.dumps([str(t) for t in frame.dtypes]).encode())
    digest.update(frame.to_csv(index=False, lineterminator="\n").encode())


def input_frames_sha256(inputs: GroupAttributeInputs) -> str:
    """SHA-256 of the inputs' frames (reports, education, universe)."""

    digest = hashlib.sha256()
    _frame_digest(digest, "reports", inputs.reports)
    _frame_digest(digest, "education", inputs.education)
    _frame_digest(digest, "universe", inputs.universe.to_frame("person_id"))
    return digest.hexdigest()


def _mapping_sha256(values: Mapping[str, str]) -> str:
    encoded = (
        json.dumps(dict(values), sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def load_group_attribute_inputs(
    *, psid_dir: Path | None = None
) -> GroupAttributeInputs:
    """Read every input from the staged PSID, recording file hashes.

    Inside :func:`populace_dynamics.cohorts.psid2010.record_files_read`:
    the codebook PDFs' SHA-256 against the value table's pins, the
    individual file's roster and education series (labels and formats
    verified), and each 1985-2023 family file's race, Spanish-descent,
    education and birthplace items (labels and codes verified).
    """

    root = psid._resolve_data_dir(psid_dir)
    codebook = gap.load_codebook_values()
    with psid2010.record_files_read(root) as files:
        pins = gap.verify_codebook_pins(
            gap.RACE_WAVES, data_dir=psid_dir, codebook=codebook
        )
        individual = gap.read_individual_items(data_dir=psid_dir)
        family_items = {
            wave: gap.read_family_items(
                wave, data_dir=psid_dir, codebook=codebook
            )
            for wave in gap.RACE_WAVES
        }
    reports = gap.head_spouse_reports(individual, family_items)
    education = _education_rows(individual, reports)
    universe = pd.Series(
        np.sort(individual["person_id"].unique()), name="person_id"
    )
    inputs = GroupAttributeInputs(
        reports=reports,
        education=education,
        universe=universe,
    )
    provenance = {
        "kind": "psid_files",
        "psid_files_sha256": dict(files),
        "psid_files_bundle_sha256": _mapping_sha256(files),
        "codebook_values_sha256": gap.CODEBOOK_VALUES_SHA256,
        "codebook_pdf_sha256": {str(w): d for w, d in pins.items()},
        "input_frames_sha256": input_frames_sha256(inputs),
    }
    return GroupAttributeInputs(
        reports=reports,
        education=education,
        universe=universe,
        provenance=provenance,
    )


# --------------------------------------------------------------------------
# Resolution
# --------------------------------------------------------------------------
def _race_report_columns(reports: pd.DataFrame) -> pd.DataFrame:
    """Harmonize every head/spouse report (cached by code tuple)."""

    cache: dict[tuple, gap.RaceEthnicityReport] = {}
    out = []
    code_columns = ["race_code_1", "race_code_2", "race_code_3", "race_code_4"]
    for row in reports[
        ["wave", "role", "hispanic_code", *code_columns]
    ].itertuples(index=False):
        wave = int(row[0])
        role = str(row[1])
        hisp = None if pd.isna(row[2]) else int(row[2])
        codes = tuple(None if pd.isna(c) else int(c) for c in row[3:])
        key = (wave, role, hisp, codes)
        if key not in cache:
            cache[key] = gap.race_ethnicity_report(
                wave, hisp, codes, role=role
            )
        out.append(cache[key])
    frame = reports[["person_id", "wave", "role"]].copy()
    frame["complete"] = pd.array([r.complete for r in out], dtype="bool")
    frame["hispanic"] = pd.array([r.hispanic for r in out], dtype="boolean")
    frame["races"] = pd.array(
        [None if r.races is None else "|".join(r.races) for r in out],
        dtype="string",
    )
    frame["basis"] = pd.array([r.hispanic_basis for r in out], dtype="string")
    frame["reading"] = pd.array(
        [
            (
                None
                if not r.complete
                else _race_code(
                    r.hispanic, "|".join(r.races or ()), "other_non_hispanic"
                )
            )
            for r in out
        ],
        dtype="string",
    )
    variables = []
    mentions = []
    hispanic_variables = []
    hispanic_mentions = []
    for row, report in zip(
        reports[["wave", "role", *code_columns]].itertuples(index=False),
        out,
        strict=True,
    ):
        items = gap.FAMILY_ITEMS[int(row[0])]
        role = str(row[1])
        names = []
        used_mentions = []
        hisp_names = []
        hisp_mentions = []
        if items.asks_hispanic_origin:
            names.append(items.hispanic[role][0])
            hisp_names.append(items.hispanic[role][0])
            hisp_mentions.append("direct_question")
        for i, ((var, _), code) in enumerate(
            zip(items.race[role], row[2:], strict=False), start=1
        ):
            if pd.isna(code):
                continue
            meaning = gap.race_mention_meaning(int(row[0]), i, int(code))
            if meaning != gap.NO_FURTHER_MENTION:
                names.append(var)
                used_mentions.append(str(i))
            if (
                report.hispanic_basis == "latino_race_mention"
                and meaning == gap.LATINO_ORIGIN
            ):
                hisp_names.append(var)
                hisp_mentions.append(str(i))
        variables.append("|".join(names))
        mentions.append("|".join(used_mentions))
        hispanic_variables.append("|".join(hisp_names))
        hispanic_mentions.append("|".join(hisp_mentions))
    frame["variables"] = pd.array(variables, dtype="string")
    frame["mentions"] = pd.array(mentions, dtype="string")
    frame["hispanic_variables"] = pd.array(hispanic_variables, dtype="string")
    frame["hispanic_mentions"] = pd.array(hispanic_mentions, dtype="string")
    return frame


def _latest(frame: pd.DataFrame) -> pd.DataFrame:
    """Each person's most recent row (a person has one row per wave)."""

    ordered = frame.sort_values(["person_id", "wave"])
    return (
        ordered.groupby("person_id", sort=True).tail(1).set_index("person_id")
    )


def _resolve_race(persons: pd.Index, reports: pd.DataFrame) -> pd.DataFrame:
    harmonized = _race_report_columns(reports)
    complete = harmonized[harmonized["complete"]]
    selected = _latest(complete)
    out = pd.DataFrame(index=persons)
    out["hispanic"] = selected["hispanic"].reindex(persons)
    out["race_mentions"] = selected["races"].reindex(persons)
    out["race_ethnicity_source_wave"] = selected["wave"].reindex(persons)
    out["race_ethnicity_source_role"] = selected["role"].reindex(persons)
    out["race_ethnicity_source_variables"] = selected["variables"].reindex(
        persons
    )
    out["race_ethnicity_source_mentions"] = selected["mentions"].reindex(
        persons
    )
    out["race_ethnicity_hispanic_basis"] = selected["basis"].reindex(persons)
    out["race_ethnicity_n_reports"] = (
        complete.groupby("person_id").size().reindex(persons, fill_value=0)
    )
    out["race_ethnicity_n_distinct"] = (
        complete.groupby("person_id")["reading"]
        .nunique()
        .reindex(persons, fill_value=0)
    )
    # Hispanic origin for persons with no complete report: their most
    # recent report that shows it.
    shown = harmonized[harmonized["hispanic"].notna()]
    fallback = _latest(shown)
    out["hispanic_source_wave"] = out["race_ethnicity_source_wave"]
    for suffix, source in (
        ("role", "role"),
        ("variables", "hispanic_variables"),
        ("mentions", "hispanic_mentions"),
    ):
        out[f"hispanic_source_{suffix}"] = selected[source].reindex(persons)
    lacking = persons[out["hispanic"].isna().to_numpy()]
    out.loc[lacking, "hispanic"] = fallback["hispanic"].reindex(lacking)
    out.loc[lacking, "hispanic_source_wave"] = fallback["wave"].reindex(
        lacking
    )
    for suffix, source in (
        ("role", "role"),
        ("variables", "hispanic_variables"),
        ("mentions", "hispanic_mentions"),
    ):
        out.loc[lacking, f"hispanic_source_{suffix}"] = fallback[
            source
        ].reindex(lacking)
    # Status.
    has_any = (
        harmonized.groupby("person_id").size().reindex(persons, fill_value=0)
    )
    asked = harmonized[harmonized["basis"] != "not_asked"]
    has_asked = (
        asked.groupby("person_id").size().reindex(persons, fill_value=0)
    )
    status = pd.Series(DK_NA_REFUSED, index=persons, dtype="string")
    status[has_any == 0] = NEVER_HEAD_OR_SPOUSE
    status[(has_any > 0) & (has_asked == 0)] = HISPANIC_ORIGIN_NOT_ASKED
    latest_report = _latest(harmonized)
    ambiguous = (
        latest_report["basis"].reindex(persons).eq(UNDOCUMENTED_ZERO_MEANING)
    )
    status[ambiguous] = UNDOCUMENTED_ZERO_MEANING
    status[out["race_ethnicity_n_reports"] > 0] = KNOWN
    out["race_ethnicity_status"] = status
    return out


def _resolve_country(persons: pd.Index, reports: pd.DataFrame) -> pd.DataFrame:
    window = reports[reports["wave"].isin(gap.BIRTHPLACE_WAVES)]
    classes = [
        gap.birthplace_class(int(s), int(y))
        for s, y in zip(
            window["birth_state_code"], window["year_came_code"], strict=True
        )
    ]
    frame = window[["person_id", "wave", "role"]].copy()
    frame["class"] = pd.array(classes, dtype="string")
    frame["variables"] = pd.array(
        [
            f"{gap.FAMILY_ITEMS[int(w)].birth_state[r][0]}|"
            f"{gap.FAMILY_ITEMS[int(w)].year_came[r][0]}"
            for w, r in zip(frame["wave"], frame["role"], strict=True)
        ],
        dtype="string",
    )
    valid = frame[frame["class"].isin(COUNTRY_OF_BIRTH_CODES)]
    selected = _latest(valid)
    out = pd.DataFrame(index=persons)
    out["country_of_birth"] = selected["class"].reindex(persons)
    out["country_of_birth_source_wave"] = selected["wave"].reindex(persons)
    out["country_of_birth_source_role"] = selected["role"].reindex(persons)
    out["country_of_birth_source_variables"] = selected["variables"].reindex(
        persons
    )
    out["country_of_birth_source_mentions"] = pd.Series(
        "birth_state|year_came", index=persons, dtype="string"
    ).where(out["country_of_birth_source_wave"].notna())
    out["country_of_birth_n_reports"] = (
        valid.groupby("person_id").size().reindex(persons, fill_value=0)
    )
    out["country_of_birth_n_distinct"] = (
        valid.groupby("person_id")["class"]
        .nunique()
        .reindex(persons, fill_value=0)
    )
    has_any = frame.groupby("person_id").size().reindex(persons, fill_value=0)
    has_missing = (
        frame[frame["class"] == gap.MISSING]
        .groupby("person_id")
        .size()
        .reindex(persons, fill_value=0)
    )
    status = pd.Series(INCONSISTENT_ONLY, index=persons, dtype="string")
    status[has_missing > 0] = DK_NA_REFUSED
    status[has_any == 0] = NEVER_HEAD_OR_SPOUSE
    status[out["country_of_birth_n_reports"] > 0] = KNOWN
    out["country_of_birth_status"] = status
    return out


def _resolve_education(
    persons: pd.Index, education: pd.DataFrame, cutoff: int
) -> pd.DataFrame:
    window = education[education["wave"] <= cutoff]
    cache: dict[tuple, tuple[int | None, str]] = {}
    years: list[Any] = []
    statuses: list[str] = []
    for code, fam in zip(
        window["education_code"], window["family_education_code"], strict=True
    ):
        key = (int(code), None if pd.isna(fam) else int(fam))
        if key not in cache:
            cache[key] = gap.education_report(*key)
        y, s = cache[key]
        years.append(pd.NA if y is None else y)
        statuses.append(s)
    frame = window[["person_id", "wave"]].copy()
    frame["years"] = pd.array(years, dtype="Int64")
    frame["status"] = pd.array(statuses, dtype="string")
    frame["variables"] = pd.array(
        [
            gap.INDIVIDUAL_ITEMS[int(w)].education[0]
            + (
                f"|{gap.FAMILY_ITEMS[int(w)].completed_education[str(r)][0]}"
                if s == gap.EDUCATION_NO_GRADES
                else ""
            )
            for w, r, s in zip(
                frame["wave"],
                window["role"].fillna(""),
                statuses,
                strict=True,
            )
        ],
        dtype="string",
    )
    valid = frame[
        frame["status"].isin([gap.EDUCATION_REPORTED, gap.EDUCATION_NO_GRADES])
    ]
    selected = _latest(valid)
    out = pd.DataFrame(index=persons)
    out["education_years"] = selected["years"].reindex(persons)
    out["education_source_wave"] = selected["wave"].reindex(persons)
    out["education_source_variables"] = selected["variables"].reindex(persons)
    frame["role"] = window["role"].fillna("individual")
    selected = _latest(frame.loc[valid.index])
    out["education_source_role"] = selected["role"].reindex(persons)
    out["education_source_mentions"] = (
        selected["status"]
        .map(
            {
                gap.EDUCATION_REPORTED: "individual",
                gap.EDUCATION_NO_GRADES: "individual|family_recode",
            }
        )
        .reindex(persons)
    )
    out["education_n_reports"] = (
        valid.groupby("person_id").size().reindex(persons, fill_value=0)
    )
    out["education_n_distinct"] = (
        valid.groupby("person_id")["years"]
        .nunique()
        .reindex(persons, fill_value=0)
    )
    has_missing = (
        frame[frame["status"] == gap.EDUCATION_MISSING]
        .groupby("person_id")
        .size()
        .reindex(persons, fill_value=0)
    )
    status = pd.Series(NO_REPORT_BY_CUTOFF, index=persons, dtype="string")
    status[has_missing > 0] = DK_NA_REFUSED
    status[out["education_n_reports"] > 0] = KNOWN
    out["education_status"] = status
    return out


@dataclass(frozen=True)
class GroupAttributes:
    """The side frame (:data:`FRAME_COLUMNS` order, sorted by person_id)
    and its provenance (rules, windows, status counts, input and file
    digests, and the frame's ``content_sha256``)."""

    frame: pd.DataFrame
    provenance: Mapping[str, Any]


def content_sha256(frame: pd.DataFrame) -> str:
    """SHA-256 of the frame's columns, dtypes and CSV bytes."""

    digest = hashlib.sha256()
    _frame_digest(digest, "group_attributes", frame)
    return digest.hexdigest()


def _person_index(person_ids: Iterable[int], universe: pd.Series) -> pd.Index:
    ids = pd.Series(list(person_ids), dtype="object")
    if ids.empty:
        raise ValueError("no person_ids given")
    if any(
        isinstance(p, (bool, np.bool_)) or not isinstance(p, Integral)
        for p in ids
    ):
        raise ValueError("person_ids must be integers")
    try:
        ids = ids.astype("int64")
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("person_ids must be int64 integers") from exc
    if ids.duplicated().any():
        raise ValueError(
            f"{int(ids.duplicated().sum())} duplicate person_ids; pass each "
            "person once (the frame is keyed by person_id)"
        )
    unknown = sorted(set(ids) - set(universe))
    if unknown:
        raise ValueError(
            f"{len(unknown)} person_ids are not in the individual file "
            f"(first {unknown[:5]})"
        )
    return pd.Index(np.sort(ids.to_numpy()), name="person_id")


def _anchor_waves(anchor_waves: Iterable[int]) -> tuple[int, ...]:
    values = tuple(anchor_waves)
    if any(
        isinstance(w, (bool, np.bool_)) or not isinstance(w, Integral)
        for w in values
    ):
        raise ValueError("anchor_waves must be integers")
    waves = tuple(sorted({int(w) for w in values}))
    if not waves:
        raise ValueError("anchor_waves is empty")
    bad = [w for w in waves if w not in gap.INDIVIDUAL_WAVES]
    if bad:
        raise ValueError(
            f"anchor waves {bad} are not PSID waves "
            f"{gap.INDIVIDUAL_WAVES[0]}-{gap.INDIVIDUAL_WAVES[-1]}"
        )
    return waves


def _validate_inputs(inputs: GroupAttributeInputs) -> None:
    """Require the documented person-wave schema before harmonization."""

    if inputs.universe.duplicated().any():
        raise ValueError("inputs.universe has duplicate person_ids")
    for name, required in (
        ("reports", {"person_id", "wave", "role", *gap.REPORT_CODE_COLUMNS}),
        (
            "education",
            {
                "person_id",
                "wave",
                "role",
                "education_code",
                "family_education_code",
            },
        ),
    ):
        frame = getattr(inputs, name)
        if not required.issubset(frame.columns):
            raise ValueError(f"inputs.{name} lacks required columns")
        for column in ("person_id", "wave"):
            if any(
                isinstance(v, (bool, np.bool_)) or not isinstance(v, Integral)
                for v in frame[column]
            ):
                raise ValueError(f"inputs.{name}.{column} must be integers")
        if not frame["wave"].isin(gap.INDIVIDUAL_WAVES).all():
            raise ValueError(f"inputs.{name} has unadjudicated waves")
        if not frame["person_id"].isin(inputs.universe).all():
            raise ValueError(f"inputs.{name} has persons outside the universe")
        roles = frame["role"] if name == "reports" else frame["role"].dropna()
        if not roles.isin(gap.ROLES).all():
            raise ValueError(f"inputs.{name} has undocumented roles")
        if frame.duplicated(["person_id", "wave"]).any():
            raise ValueError(
                f"inputs.{name} has more than one row for a person-wave"
            )
        code_columns = (
            gap.REPORT_CODE_COLUMNS
            if name == "reports"
            else ("education_code", "family_education_code")
        )
        for column in code_columns:
            if any(
                isinstance(v, (bool, np.bool_)) or not isinstance(v, Integral)
                for v in frame[column].dropna()
            ):
                raise ValueError(f"inputs.{name}.{column} must be integers")
        if name == "education" and frame["education_code"].isna().any():
            raise ValueError("inputs.education has absent education codes")
    _validate_attribute_code_domains(inputs)


def _validate_attribute_code_domains(inputs: GroupAttributeInputs) -> None:
    """Use reader authority for supplied education and birthplace codes.

    The individual education frame is the reader's adjudicated domain,
    verified against IND2023ER_formats.sas at each real-data load. Family
    domains come from the pinned per-variable codebook captures. Grouped
    checks apply even to reports outside the requested population/cutoff.
    """

    education = inputs.education
    supplied_family = education["family_education_code"].notna()
    if (supplied_family & education["role"].isna()).any():
        raise ValueError(
            "inputs.education.family_education_code requires a head or "
            "spouse role"
        )
    codebook = (
        gap.load_codebook_values()
        if not inputs.reports.empty or supplied_family.any()
        else None
    )

    def family_code_domain(
        wave: int, role: str, column: str, variable: str, part: pd.DataFrame
    ) -> None:
        gap._check_codes(
            part[column],
            gap.documented_domain(codebook, wave, variable),
            context=f"inputs.{column} ({wave} {role} {variable})",
        )

    for wave, part in education.groupby("wave", sort=False):
        wave = int(wave)
        variable = gap.INDIVIDUAL_ITEMS[wave].education[0]
        gap._check_codes(
            part["education_code"],
            gap._expected_education_domain(wave),
            context=f"inputs.education.education_code ({wave} {variable})",
        )
        supplied = part[part["family_education_code"].notna()]
        if supplied.empty:
            continue
        items = gap.FAMILY_ITEMS[wave]
        if not items.completed_education:
            raise ValueError(
                f"inputs.education.family_education_code: not asked in {wave}"
            )
        for role, role_rows in supplied.groupby("role", sort=False):
            family_code_domain(
                wave,
                str(role),
                "family_education_code",
                items.completed_education[str(role)][0],
                role_rows,
            )

    for (wave, role), part in inputs.reports.groupby(
        ["wave", "role"], sort=False
    ):
        wave, role = int(wave), str(role)
        items = gap.FAMILY_ITEMS[wave]
        supplied = part[part["family_education_code"].notna()]
        if not supplied.empty:
            if not items.completed_education:
                raise ValueError(
                    "inputs.reports.family_education_code: not asked in "
                    f"{wave}"
                )
            family_code_domain(
                wave,
                role,
                "family_education_code",
                items.completed_education[role][0],
                supplied,
            )
        for column, mapping in (
            ("birth_state_code", items.birth_state),
            ("year_came_code", items.year_came),
        ):
            if not mapping:
                if part[column].notna().any():
                    raise ValueError(
                        f"inputs.reports.{column}: not asked in {wave}"
                    )
                continue
            family_code_domain(wave, role, column, mapping[role][0], part)


def build_group_attributes(
    inputs: GroupAttributeInputs,
    person_ids: Iterable[int],
    *,
    anchor_waves: Iterable[int],
    schemes: Mapping[str, Any] | None = None,
) -> GroupAttributes:
    """Resolve the attributes and scheme categories of ``person_ids``.

    Reads no PSID files: consumes ``inputs`` and category/code documentation.
    ``anchor_waves`` are the population's
    anchor waves (``(2011,)``, ``(2009,)``, the age-67 observation waves,
    ``(2023,)``); education is resolved as of their maximum. Refuses
    duplicate or unknown person ids and non-PSID anchor waves.
    """

    waves = _anchor_waves(anchor_waves)
    cutoff = max(waves)
    schemes = load_schemes() if schemes is None else schemes
    _validate_schemes(schemes)
    _validate_inputs(inputs)
    persons = _person_index(person_ids, inputs.universe)
    actual_input_digest = input_frames_sha256(inputs)
    recorded_input_digest = inputs.provenance.get("input_frames_sha256")
    if (
        recorded_input_digest is not None
        and recorded_input_digest != actual_input_digest
    ):
        raise ValueError("input frames changed after their provenance seal")
    wanted = set(persons)
    reports = inputs.reports[inputs.reports["person_id"].isin(wanted)]
    education = inputs.education[inputs.education["person_id"].isin(wanted)]

    race = _resolve_race(persons, reports)
    edu = _resolve_education(persons, education, cutoff)
    country = _resolve_country(persons, reports)
    frame = pd.concat([race, edu, country], axis=1).reset_index()
    for column, dtype in _ATTRIBUTE_COLUMNS.items():
        frame[column] = frame[column].astype(dtype)
    scheme_columns: list[str] = []
    for scheme in schemes["schemes"].values():
        for dimension, spec in scheme["dimensions"].items():
            labels, status = apply_category_scheme(frame, dimension, spec)
            frame[spec["column"]] = labels
            frame[f"{spec['column']}_status"] = status
            scheme_columns.extend([spec["column"], f"{spec['column']}_status"])
    frame = frame[[*_ATTRIBUTE_COLUMNS, *scheme_columns]]

    def _counts(column: str) -> dict[str, int]:
        return {
            str(k): int(v)
            for k, v in frame[column].value_counts(dropna=False).items()
        }

    provenance = {
        "builder": (
            "populace_dynamics.cohorts.group_attributes."
            "build_group_attributes"
        ),
        "rules_version": RULES_VERSION,
        "anchor_waves": list(waves),
        "education_cutoff_wave": cutoff,
        "windows": {
            "race_ethnicity": list(gap.RACE_WAVES),
            "country_of_birth": list(gap.BIRTHPLACE_WAVES),
            "education": [w for w in gap.INDIVIDUAL_WAVES if w <= cutoff],
        },
        "n_persons": len(frame),
        "person_ids_sha256": hashlib.sha256(
            ",".join(str(p) for p in frame["person_id"]).encode()
        ).hexdigest(),
        "status_counts": {
            column: _counts(column)
            for column in (
                "race_ethnicity_status",
                "education_status",
                "country_of_birth_status",
                *(c for c in scheme_columns if c.endswith("_status")),
            )
        },
        "sourced_after_cutoff": {
            "race_ethnicity": int(
                (frame["race_ethnicity_source_wave"] > cutoff).sum()
            ),
            "country_of_birth": int(
                (frame["country_of_birth_source_wave"] > cutoff).sum()
            ),
        },
        "inputs": deepcopy(dict(inputs.provenance)),
        "input_frames_sha256": actual_input_digest,
        "schemes_sha256": hashlib.sha256(
            json.dumps(schemes, sort_keys=True).encode()
        ).hexdigest(),
        "category_scheme_sources": deepcopy(schemes.get("sources", {})),
        "report_builder_defaults": deepcopy(
            schemes["schemes"]
            .get("boomers2004", {})
            .get("builder_defaults", {})
        ),
        "report_dimension_conventions": {
            dimension: deepcopy(spec.get("assumptions", []))
            for dimension, spec in schemes["schemes"]
            .get("boomers2004", {})
            .get("dimensions", {})
            .items()
        },
        "content_sha256": content_sha256(frame),
    }
    return GroupAttributes(frame=frame, provenance=provenance)


def load_group_attributes(
    person_ids: Iterable[int],
    *,
    anchor_waves: Iterable[int],
    psid_dir: Path | None = None,
) -> GroupAttributes:
    """Read the staged PSID and build the side frame for ``person_ids``.

    ``anchor_waves`` as in :func:`build_group_attributes`; ``psid_dir``
    defaults to ``POPULACE_DYNAMICS_PSID_DIR`` or the staged default.
    """

    waves = _anchor_waves(anchor_waves)
    ids = list(person_ids)
    # Reject malformed requests before any expensive PSID file read. The
    # actual universe check follows the audited read.
    _person_index(ids, pd.Series(ids, dtype="object"))
    inputs = load_group_attribute_inputs(psid_dir=psid_dir)
    return build_group_attributes(inputs, ids, anchor_waves=waves)
