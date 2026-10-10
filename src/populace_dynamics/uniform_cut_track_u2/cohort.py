"""The U2 age-67 cohort: plans, identity, builder and income rows.

Specification section 3.  U2 observes the 1946-55 birth cohort in the
PSID odd waves 2013-2023 (income years 2012-2022), a separate cohort
configuration beside U1's (:mod:`populace_dynamics.cohorts.age67`, whose
API, defaults and constants this module neither edits nor extends).

**Rows (populations).**

* **U0** (primary, the fixed headline): the five odd birth years at exact
  age 67 -- 1947 (income year 2014, wave 2015), 1949 (2016/2017), 1951
  (2018/2019), 1953 (2020/2021) and 1955 (2022/2023), multiplier 1.
* **U1** (all ten birth years): odd birth years as U0; every even birth
  year 1946-1954 at ages 66 and 68 with multiplier 0.5 each.  1946 gets
  both observations (its age-66 wave, 2013, is staged): fifteen cells,
  ten birth years, planned multipliers summing to one per birth year.  A
  missing observation keeps its disposition; its weight is never moved to
  another observation and nothing is renormalized.

U0-F and the eight ``-F`` rows are omitted (section 3 row-set amendment);
this module refuses them.

**Identification** (section 3): the birth-year law is
:func:`populace_dynamics.estimates.career.derive_birth_years` (called, not
edited), over the persons with a positive-weight, in-family (sequence
1-20) presence in *any* common support wave 2013-2023; each person's seed
coordinate is the earliest such presence (``seed_wave_rule =
earliest_presence_in_common_support_waves``, an explicit departure from
U1's per-row ``earliest_presence_wave``, which :class:`U2CohortSpec`
refuses).  Births are derived once (:func:`derive_u2_births`) and reused
by every row.  Support waves identify people; they add no observation
and no design unit to a row.

**Roles** (section 3 relationship-code amendment) come from a
:class:`~populace_dynamics.uniform_cut_track_u2.sources.RoleContext`.
Every in-family person of an observation's family is classified; a code
whose rule is TO VERIFY or undeclared refuses the build (no fallback).
Then the two family-unit exclusions Max ratified on 2026-10-10 (d1090;
section 16c) apply: an observation whose 2015 family holds a code-20
person recorded male, or whose 2019-2023 family holds a code-90 or
code-92 person, is not built and is counted under the named disposition
(:func:`~populace_dynamics.uniform_cut_track_u2.sources.
family_unit_exclusion`).  An observation already disposed of (not in the
file, not present, zero weight, sex unknown) keeps that disposition.
The income role follows the income slot: 10 head, 20 and 22 the spouse
slot (``wife``, irrespective of sex), 90 and 92 (2013-2017) and every
other code OFUM.  The primary annuity lives are the unique code-10 person
and the unique co-resident legal spouse (code 20 or 90), each with
recorded sex and derived income-year age; a uniquely paired head and
legal spouse resolve an otherwise unresolved marital history as married,
each naming the other.  Code 22 and 92 never resolve; a missing or ambiguous pairing
stays unresolved and is counted.

**Weights, design and units.**  Observation weight = the reporting wave's
core/immigrant cross-section weight times the planned multiplier; no
calibration.  Family unit ``wave * 100000 + interview`` with domain and
uniqueness checks.  Legal marital status at the end of the income year,
separated counted as married; unresolved states stay in ``all`` and the
sex cell and leave the marital cells, counted.

Provenance is recorded as in U1 (``invented``, ``psid_files`` or
``caller_frames``) together with ``target_id: U2``; the invented declared
role context runs only on invented inputs.  Unlike U1, the ``invented``
kind needs more than a matching digest, because in U2 it unlocks the
declared role rules the committed roles registry refuses:

* the inputs must carry the seal :mod:`.invented`'s generator sets, and
  the frames must still hash to the sealed digest;
* the frames must regenerate: :func:`build_u2_cohort` calls the
  generator's :func:`~populace_dynamics.uniform_cut_track_u2.invented.
  check_invented_inputs`, which rebuilds the recorded seed and named
  variant and compares digests (once per digest).  The generator is
  looked up in ``sys.modules``, not imported, so the structure and
  component entry points' import graph stays free of it; sealed inputs
  cannot exist unless the generator was loaded.

:func:`replace_provenance` never labels inputs invented and
``dataclasses.replace`` drops both seals, so relabelled frames -- a
loader's included -- are refused: a copied invented label has no seal, a
``psid_files`` label has no loader seal, and any other label is
``caller_frames``, which the declared context refuses.  The seals and a
built cohort's provenance are read-only, ``U2Inputs`` and ``U2Cohort``
are final, and every input frame must be exactly a ``pandas.DataFrame``
(so a frame cannot misreport its own digest).  The income rows and the
component rows join only the inputs the cohort was built from.  These
checks stop relabelling and mixing through the public API; Python cannot
stop deliberate tampering with private state (``object.__setattr__``,
replacing module functions), which the registered path never performs.
This module computes no income concept, threshold, annuity, poverty
status or statistic.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import sys
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from types import MappingProxyType
from typing import Any

import pandas as pd

from populace_dynamics.cohorts import psid2010
from populace_dynamics.estimates import career
from populace_dynamics.uniform_cut_track_u2 import identity, sources

__all__ = [
    "ALL_BIRTH_YEARS",
    "CALLER_FRAMES",
    "DESIGN_VALID_CLUSTERS",
    "DESIGN_VALID_STRATA",
    "EVEN_BIRTH_YEARS",
    "EVIDENCE_KEY",
    "INVENTED",
    "MARITAL_STATUS_4",
    "NO_HEAD_PAIRING",
    "PRIMARY_BIRTH_YEARS",
    "PRIMARY_WAVES",
    "PSID_FILES",
    "ROWS",
    "SEED_WAVE_RULE",
    "SUPPORT_WAVES",
    "TARGET_AGE",
    "UNCLASSIFIED_MARITAL_STATUS",
    "U2Births",
    "U2Cohort",
    "U2CohortError",
    "U2CohortSpec",
    "U2Inputs",
    "build_u2_cohort",
    "check_cohort_inputs",
    "check_person_joins",
    "check_unique_identifiers",
    "derive_u2_births",
    "design_frame",
    "income_rows",
    "input_frames_sha256",
    "marital_status_4",
    "observation_plan",
    "pending_decisions",
    "plan_cells",
    "structural_summary",
]

TARGET_AGE = identity.TARGET_AGE
SUPPORT_WAVES: tuple[int, ...] = sources.SUPPORT_WAVES
PRIMARY_BIRTH_YEARS: tuple[int, ...] = (1947, 1949, 1951, 1953, 1955)
EVEN_BIRTH_YEARS: tuple[int, ...] = (1946, 1948, 1950, 1952, 1954)
ALL_BIRTH_YEARS: tuple[int, ...] = identity.BIRTH_YEARS
PRIMARY_WAVES: tuple[int, ...] = tuple(b + 68 for b in PRIMARY_BIRTH_YEARS)
#: Builder populations: U0 and U1.  Rows U2-U10 are income-concept
#: changes on U0's population (:mod:`.rows`).
ROWS: tuple[str, ...] = ("U0", "U1")
SEED_WAVE_RULE = "earliest_presence_in_common_support_waves"
U1_EVEN_BIRTH_YEAR_WEIGHT = 0.5
U1_SINGLE_OBSERVATION_WEIGHT = 1.0
U1_EVEN_BIRTH_AGES: tuple[int, int] = (66, 68)
INVENTED = "invented"
PSID_FILES = "psid_files"
CALLER_FRAMES = "caller_frames"
#: The loader seal's and provenance's record of the frozen pre-registration
#: evidence the inputs were rechecked against (section 14; set only by
#: :func:`~populace_dynamics.uniform_cut_track_u2.loader.load_u2_inputs`).
EVIDENCE_KEY = "preregistration_evidence_sha256"
MARITAL_STATUS_4: tuple[str, ...] = (
    "married",
    "widowed",
    "divorced",
    "never_married",
)
UNCLASSIFIED_MARITAL_STATUS = "unclassified"
#: The documented sampling-error domains (design registry ``valid_codes``:
#: strata 1-94, including the 2017/2019 refresher strata 88-94, and
#: clusters 1 and 2; ``IND2023ER_formats.sps:11710`` and ``:11719``).
DESIGN_VALID_STRATA: frozenset[int] = frozenset(range(1, 95))
DESIGN_VALID_CLUSTERS: frozenset[int] = frozenset({1, 2})

_SEQUENCE_IN_FAMILY = (1, 20)
_SEQUENCE_GROUPS: tuple[tuple[str, int, int], ...] = (
    ("in_family", 1, 20),
    ("institution", 51, 59),
    ("moved_out", 71, 80),
    ("died", 81, 89),
)
_MAX_AGE_CODE = 125
_FAMILY_UNIT_SCALE = 100_000
_UNRESOLVED_STATES = ("unknown", "no_marriage_history")
_OMITTED_ROWS = (
    "U0-F",
    "U2-F",
    "U3-F",
    "U4-F",
    "U5-F",
    "U7-F",
    "U8-F",
    "U9-F",
    "U10-F",
)


class U2CohortError(ValueError):
    """The inputs or configuration cannot yield the U2 cohort."""


# ===========================================================================
# Configuration and plans
# ===========================================================================
@dataclass(frozen=True)
class U2CohortSpec:
    """The U2 cohort configuration; every field is the section 15 value.

    U2 registers no alternative for these fields, so any other value is
    refused (the conservative reading of sections 3 and 15).  U1's seed
    rule, U1's populations and target identities are refused by name.
    """

    row: str = "U0"
    presence: str = "in_family"
    separated_is_married: bool = True
    seed_wave_rule: str = SEED_WAVE_RULE
    unresolved_marital_status: str = "relationship_code"
    annuitant_age_source: str = "derived_birth_year"
    institution_income_rule: str = "excluded"
    missing_observation_reweighting: bool = False
    target_id: str = identity.TARGET_ID

    def __post_init__(self) -> None:
        identity.check_target(self.target_id, "U2CohortSpec")
        if self.row in _OMITTED_ROWS:
            raise U2CohortError(
                f"row {self.row} is omitted from U2 by the section 3 "
                "row-set amendment (U0-F and every -F row)"
            )
        if self.row not in ROWS:
            raise U2CohortError(f"U2 cohort row must be one of {ROWS}")
        if self.seed_wave_rule == identity.U1_SEED_WAVE_RULE:
            raise U2CohortError(
                f"seed_wave_rule {self.seed_wave_rule!r} is U1's rule; U2 "
                f"identifies births by {SEED_WAVE_RULE!r} (section 3)"
            )
        registered = {
            "presence": "in_family",
            "separated_is_married": True,
            "seed_wave_rule": SEED_WAVE_RULE,
            "unresolved_marital_status": "relationship_code",
            "annuitant_age_source": "derived_birth_year",
            "institution_income_rule": "excluded",
            "missing_observation_reweighting": False,
        }
        for name, value in registered.items():
            if getattr(self, name) != value or type(
                getattr(self, name)
            ) is not type(value):
                raise U2CohortError(
                    f"{name}={getattr(self, name)!r}: U2 registers only "
                    f"{value!r} (section 15)"
                )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def plan_cells(
    spec: U2CohortSpec,
) -> tuple[tuple[int, int, int, int, float], ...]:
    """``(birth_year, wave, income_year, age, multiplier)`` per cell.

    Refuses a malformed plan: a wave outside the support set, an income
    year other than ``wave - 1`` or ``birth + age``, a repeated
    (birth, wave) cell, or multipliers that do not sum to one per birth
    year (section 3).
    """

    if not isinstance(spec, U2CohortSpec):
        raise U2CohortError("spec must be a U2CohortSpec")
    cells = [
        (b, b + TARGET_AGE + 1, b + TARGET_AGE, TARGET_AGE, 1.0)
        for b in PRIMARY_BIRTH_YEARS
    ]
    if spec.row == "U1":
        for b in EVEN_BIRTH_YEARS:
            for age in U1_EVEN_BIRTH_AGES:
                cells.append(
                    (b, b + age + 1, b + age, age, U1_EVEN_BIRTH_YEAR_WEIGHT)
                )
    totals: dict[int, float] = {}
    for birth, wave, income_year, age, multiplier in cells:
        if (
            wave not in SUPPORT_WAVES
            or income_year != wave - 1
            or income_year != birth + age
        ):
            raise U2CohortError(
                f"plan cell ({birth}, {wave}, {income_year}, {age}) lies "
                f"outside the U2 support waves {SUPPORT_WAVES}"
            )
        totals[birth] = totals.get(birth, 0.0) + multiplier
    if len({(b, w) for b, w, _, _, _ in cells}) != len(cells):
        raise U2CohortError("the plan repeats a (birth year, wave) cell")
    unbalanced = {b: m for b, m in totals.items() if m != 1.0}
    if unbalanced:
        raise U2CohortError(
            "planned multipliers must sum to one per birth year (section "
            f"3): {dict(sorted(unbalanced.items()))}"
        )
    return tuple(sorted(cells))


def observation_plan(
    spec: U2CohortSpec,
) -> tuple[tuple[int, int, int, float], ...]:
    """``(birth_year, wave, income_year, weight_multiplier)`` per row.

    The same tuple shape as U1's ``age67.observation_plan``.
    """

    return tuple((b, w, y, m) for b, w, y, _, m in plan_cells(spec))


def check_plan_against_support_registry(
    registries: sources.RegistrySet,
) -> dict[str, Any]:
    """Hold row U1's plan equal to milestone 1's support registry."""

    documented = {
        (e["birth_year"], e["wave"], e["income_year"], e["age"]): (
            float(e["multiplier"]),
            bool(e["primary_observation"]),
        )
        for e in registries.entries("support")
        if e["id"] != "common.birth_derivation"
    }
    planned = {
        (b, w, y, a): (m, b in PRIMARY_BIRTH_YEARS and a == TARGET_AGE)
        for b, w, y, a, m in plan_cells(U2CohortSpec(row="U1"))
    }
    if documented != planned:
        raise U2CohortError(
            "row U1's plan differs from the support registry: "
            f"{sorted(set(documented) ^ set(planned))}"
        )
    return {"cells": len(planned), "equal_to_support_registry": True}


def pending_decisions() -> tuple[psid2010.PendingDecision, ...]:
    """The U2 cohort fields and their ruling (d514 adopts section 16)."""

    spec = U2CohortSpec()
    ruled = (
        "section 16 default adopted by Max, d514 (2026-09-28); the U2 "
        "rulings record must be materialized in the section 15 block "
        "before a registered run (section 20 step 5)"
    )
    return (
        psid2010.PendingDecision(
            "row",
            spec.row,
            ("U1",),
            "section 3: U0 exact age 67, five birth years, the fixed "
            "headline; U1 all ten births with half-weighted ages 66 and 68 "
            "for even births; U0-F and the -F rows omitted",
            ruled,
        ),
        psid2010.PendingDecision(
            "seed_wave_rule",
            spec.seed_wave_rule,
            (),
            "section 3: earliest positive-weight in-family presence in the "
            "common support waves 2013-2023 (explicit departure from U1)",
            ruled,
        ),
        psid2010.PendingDecision(
            "unresolved_marital_status",
            spec.unresolved_marital_status,
            (),
            "section 3: a uniquely paired head and code-20/code-90 legal "
            "spouse resolve an unresolved history as married; codes 22 and "
            "92 never resolve",
            ruled,
        ),
        psid2010.PendingDecision(
            "annuitant_age_source",
            spec.annuitant_age_source,
            (),
            "section 3: derived birth years over the common support set; "
            "the inherited wave-age fallback applied and counted",
            ruled,
        ),
        psid2010.PendingDecision(
            "missing_observation_reweighting",
            spec.missing_observation_reweighting,
            (),
            "section 3: a missing observation keeps its disposition; no "
            "transfer of weight and no renormalization",
            ruled,
        ),
    )


# ===========================================================================
# Inputs and provenance
# ===========================================================================
@dataclass(frozen=True)
class U2Inputs:
    """Materialized reader outputs for the six support waves.

    ``anchors[wave]``: ``person_id``, ``interview``, ``sequence``,
    ``relationship``, ``age``, ``reported_birth_year``, ``weight``.
    ``persons``: ``person_id``, ``sex`` (``male``/``female``/``na``).
    ``design``: ``person_id``, ``stratum``, ``cluster``.
    ``family_income[wave]``: the decoded income concepts of
    :data:`~populace_dynamics.uniform_cut_track_u2.sources.INCOME_CONCEPTS`
    with ``wife_present``; ``family_wealth[wave]``: WEALTH1, its accuracy
    flag, vehicles, home equity and the identity terms;
    ``employer_dc[wave]``: the pension items with the U7 balance columns.
    """

    anchors: Mapping[int, pd.DataFrame]
    design: pd.DataFrame
    persons: pd.DataFrame
    marriage_history: pd.DataFrame
    observed_earnings: pd.DataFrame
    family_income: Mapping[int, pd.DataFrame]
    family_wealth: Mapping[int, pd.DataFrame]
    employer_dc: Mapping[int, pd.DataFrame] = field(default_factory=dict)
    provenance: Mapping[str, Any] = field(default_factory=dict)
    target_id: str = identity.TARGET_ID
    loader_seal: Mapping[str, str] | None = field(
        default=None, init=False, repr=False, compare=False
    )
    #: Set only by :mod:`.invented`'s generator (``object.__setattr__``,
    #: as the loader sets ``loader_seal``); ``init=False``, so
    #: ``dataclasses.replace`` resets it to None.
    invented_seal: Mapping[str, Any] | None = field(
        default=None, init=False, repr=False, compare=False
    )

    def __init_subclass__(cls, **kwargs: Any) -> None:
        raise TypeError("U2Inputs is final")

    def __post_init__(self) -> None:
        identity.check_target(self.target_id, "U2Inputs")


def _frame_digest(digest: Any, name: str, frame: pd.DataFrame) -> None:
    if type(frame) is not pd.DataFrame:
        raise U2CohortError(
            f"input frame {name} is a {type(frame).__name__}, not a "
            "pandas.DataFrame: a frame's digest must come from its data"
        )
    digest.update(f"{name}\n".encode())
    digest.update(json.dumps([str(c) for c in frame.columns]).encode())
    digest.update(json.dumps([str(t) for t in frame.dtypes]).encode())
    digest.update(frame.to_csv(index=False, lineterminator="\n").encode())


def input_frames_sha256(inputs: U2Inputs) -> str:
    """SHA-256 of every U2 input frame and the target identity."""

    digest = hashlib.sha256()
    digest.update(f"target:{inputs.target_id}\n".encode())
    for wave in sorted(inputs.anchors):
        _frame_digest(digest, f"anchor_{wave}", inputs.anchors[wave])
    for name in ("design", "persons", "marriage_history", "observed_earnings"):
        _frame_digest(digest, name, getattr(inputs, name))
    for label, frames in (
        ("income", inputs.family_income),
        ("wealth", inputs.family_wealth),
        ("employer_dc", inputs.employer_dc),
    ):
        for wave in sorted(frames):
            _frame_digest(digest, f"{label}_{wave}", frames[wave])
    return digest.hexdigest()


_INVENTED_MODULE = "populace_dynamics.uniform_cut_track_u2.invented"
#: (digest, generator, seed, variant) the invented generator has
#: regenerated in this process.
_REGENERATED: set[tuple[Any, ...]] = set()


def _regenerate_invented(inputs: U2Inputs, frames: str) -> None:
    """Refuse invented inputs the loaded generator does not regenerate."""

    recorded = dict(inputs.provenance or {})
    key = (
        frames,
        recorded.get("generator"),
        recorded.get("seed"),
        recorded.get("variant"),
    )
    if key in _REGENERATED:
        return
    generator = sys.modules.get(_INVENTED_MODULE)
    if generator is None:
        raise U2CohortError(
            "inputs claim invented provenance, but the U2 invented "
            "generator is not loaded, so they cannot be its output"
        )
    try:
        generator.check_invented_inputs(inputs)
    except ValueError as error:
        raise U2CohortError(
            f"inputs claim invented provenance but do not regenerate: "
            f"{error}"
        ) from error
    _REGENERATED.add(key)


def _input_provenance(inputs: U2Inputs) -> dict[str, Any]:
    recorded = dict(inputs.provenance or {})
    frames = input_frames_sha256(inputs)
    kind = recorded.get("kind")
    if kind == INVENTED:
        seal = inputs.invented_seal
        if seal is None:
            raise U2CohortError(
                "inputs claim invented provenance but carry no seal from "
                "the U2 invented generator: relabelled frames are not "
                "invented (only the generator's named variants are)"
            )
        if (
            recorded.get("input_frames_sha256") != frames
            or dict(seal).get("input_frames_sha256") != frames
        ):
            raise U2CohortError(
                "inputs claim invented provenance but their frames differ "
                "from the digest the invented generator sealed; invented "
                "data cannot be mixed with other frames"
            )
        for key in ("generator", "seed", "variant"):
            if recorded.get(key) != dict(seal).get(key):
                raise U2CohortError(
                    f"the invented provenance's {key} "
                    f"{recorded.get(key)!r} is not the sealed "
                    f"{dict(seal).get(key)!r}"
                )
        _regenerate_invented(inputs, frames)
        return {
            "kind": INVENTED,
            "target_id": identity.TARGET_ID,
            "generator": recorded.get("generator"),
            "seed": recorded.get("seed"),
            "variant": recorded.get("variant"),
            "label": recorded.get("data"),
            "input_frames_sha256": frames,
        }
    if kind == PSID_FILES:
        files = recorded.get("psid_files_sha256")
        if inputs.loader_seal is None or not isinstance(files, Mapping):
            raise U2CohortError(
                "inputs claim psid_files provenance but were not returned "
                "by the U2 loader"
            )
        bundle = hashlib.sha256(
            (json.dumps(dict(files), sort_keys=True) + "\n").encode()
        ).hexdigest()
        seal = dict(inputs.loader_seal)
        expected = {
            "input_frames_sha256": frames,
            "psid_files_bundle_sha256": bundle,
        }
        # The frozen-evidence recheck (section 14) is sealed only when the
        # loader ran it; the provenance must record the same hash.
        evidence = seal.get(EVIDENCE_KEY)
        if evidence is not None:
            expected[EVIDENCE_KEY] = evidence
        if (
            seal != expected
            or recorded.get("psid_files_bundle_sha256") != bundle
            or recorded.get(EVIDENCE_KEY) != evidence
        ):
            raise U2CohortError(
                "the frames or PSID file hashes changed after the U2 "
                "loader sealed them"
            )
        out = {
            "kind": PSID_FILES,
            "target_id": identity.TARGET_ID,
            "psid_data_dir": recorded.get("psid_data_dir"),
            "psid_files_sha256": dict(files),
            "psid_files_bundle_sha256": recorded.get(
                "psid_files_bundle_sha256"
            ),
            "registries": recorded.get("registries"),
            "input_frames_sha256": frames,
        }
        if evidence is not None:
            out[EVIDENCE_KEY] = evidence
        return out
    return {
        "kind": CALLER_FRAMES,
        "target_id": identity.TARGET_ID,
        "note": "frames not returned by the U2 loader or generator",
        "input_frames_sha256": frames,
    }


def _check_role_context(
    role_context: sources.RoleContext, provenance_kind: str
) -> None:
    if type(role_context) is not sources.RoleContext:
        raise U2CohortError("a U2 build needs an explicit RoleContext")
    if (
        role_context.kind == sources.INVENTED_DECLARED
        and provenance_kind != INVENTED
    ):
        raise U2CohortError(
            "the invented declared role context applies only to invented "
            f"inputs, not {provenance_kind!r}: a real-data build reads the "
            "committed roles registry, which refuses TO VERIFY codes"
        )


# ===========================================================================
# Births (derived once, reused across rows)
# ===========================================================================
@dataclass(frozen=True)
class U2Births:
    """Birth-year records for the universe and the annuitant extension."""

    records: Mapping[int, career.BirthYearRecord]
    universe: frozenset[int]
    seed: pd.DataFrame
    inputs_sha256: str

    def birth_year(self, person_id: int) -> int | None:
        record = self.records.get(int(person_id))
        return None if record is None else record.birth_year


def _present(anchor: pd.DataFrame) -> pd.Series:
    low, high = _SEQUENCE_IN_FAMILY
    return anchor["sequence"].between(low, high) & (anchor["weight"] > 0)


def _seed_frame(rows: list[pd.DataFrame]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(
            columns=["person_id", "year", "anchor_wave", "age"]
        )
    return (
        pd.concat(rows, ignore_index=True)
        .sort_values(["person_id", "anchor_wave"], kind="stable")
        .drop_duplicates("person_id", keep="first")
        .reset_index(drop=True)
    )


def check_unique_identifiers(inputs: U2Inputs) -> None:
    """Refuse a repeated identifier in any keyed input frame (section 14).

    "Duplicate identifiers ... refuse execution": ``persons`` and
    ``design`` hold one row per ``person_id``, each wave's anchor one row
    per ``person_id``, and each wave's family-income, family-wealth and
    employer-DC frame one row per ``interview``.  Without this check a
    repeated anchor row made :func:`build_u2_cohort` fail on an
    incidental ``TypeError``, and a repeated ``persons`` row would have
    classified the person's sex as unknown.  The message gives counts,
    never identifier values.
    """

    keyed: list[tuple[str, pd.DataFrame, str]] = [
        ("persons", inputs.persons, "person_id"),
        ("design", inputs.design, "person_id"),
    ]
    keyed += [
        (f"anchor {wave}", frame, "person_id")
        for wave, frame in sorted(inputs.anchors.items())
    ]
    for label, frames in (
        ("family income", inputs.family_income),
        ("family wealth", inputs.family_wealth),
        ("employer DC", inputs.employer_dc),
    ):
        keyed += [
            (f"{label} {wave}", frame, "interview")
            for wave, frame in sorted(frames.items())
        ]
    for label, frame, column in keyed:
        if column not in frame.columns:
            raise U2CohortError(f"input frame {label} lacks {column}")
        repeated = int(frame[column].duplicated().sum())
        if repeated:
            raise U2CohortError(
                f"input frame {label} repeats {column} ({repeated} repeated "
                "row(s)): duplicate identifiers refuse execution (section 14)"
            )


def check_person_joins(inputs: U2Inputs) -> None:
    """Refuse an anchor person absent from ``persons`` (section 14).

    "Failed joins ... refuse execution": every person in every support
    wave's anchor must have a ``persons`` record, or the build would read
    the person's sex as unknown (``sex.get(pid, "na")``) and silently
    drop the observation as ``excluded_sex_unknown`` (review round 1,
    info finding 5).  The loader builds both from the same individual
    records, so this refuses only frames joined by hand.  The message
    gives counts, never identifier values.
    """

    persons = set(inputs.persons["person_id"].astype("int64"))
    for wave, frame in sorted(inputs.anchors.items()):
        absent = int((~frame["person_id"].astype("int64").isin(persons)).sum())
        if absent:
            raise U2CohortError(
                f"anchor {wave}: {absent} person(s) have no persons record: "
                "failed joins refuse execution (section 14)"
            )


def derive_u2_births(inputs: U2Inputs) -> U2Births:
    """The birth-year law over the common support waves (section 3).

    Universe: every person with a positive-weight, in-family presence in
    any support wave; seed coordinate: the earliest such presence
    (``(wave - 1) - age``).  Annuitant extension: in-family persons of
    the administrative birth-support codes (10, 20, 22, 88, 90; not 92)
    and marriage-history spouses of target-cohort members outside the
    universe, seeded by their earliest in-family presence at any weight;
    the law runs without a required population for them, so a conflict
    leaves the person unresolved (the wave-age fallback, counted).
    """

    missing = set(SUPPORT_WAVES) - set(inputs.anchors)
    if missing:
        raise U2CohortError(f"inputs lack support waves {sorted(missing)}")
    check_unique_identifiers(inputs)
    check_person_joins(inputs)
    seeds = []
    for wave in SUPPORT_WAVES:
        anchor = inputs.anchors[wave]
        present = anchor[_present(anchor)]
        seeds.append(
            pd.DataFrame(
                {
                    "person_id": present["person_id"].astype("int64"),
                    "year": wave - 1,
                    "anchor_wave": wave,
                    "age": present["age"].astype("int64"),
                }
            )
        )
    seed = _seed_frame(seeds)
    universe = frozenset(int(pid) for pid in seed["person_id"])
    history = inputs.marriage_history
    earnings = inputs.observed_earnings
    records = career.derive_birth_years(
        history[history["person_id"].isin(universe)],
        earnings[earnings["person_id"].isin(universe)],
        seed_coordinates=seed,
        required_person_ids=universe,
    )
    births = {record.person_id: record for record in records}
    if set(births) != set(universe):
        raise AssertionError("birth dispositions are not universe-total")
    targets = {
        pid for pid, r in births.items() if r.birth_year in ALL_BIRTH_YEARS
    }
    spouses: set[int] = set()
    if "spouse_person_id" in history.columns:
        mine = history[history["person_id"].isin(targets)]
        spouses = {int(v) for v in mine["spouse_person_id"].dropna().tolist()}
    extension = []
    for wave in SUPPORT_WAVES:
        anchor = inputs.anchors[wave]
        rows = anchor[
            anchor["sequence"].between(*_SEQUENCE_IN_FAMILY)
            & (
                anchor["relationship"].isin(
                    sources.ADMINISTRATIVE_BIRTH_SUPPORT_CODES
                )
                | anchor["person_id"].isin(spouses)
            )
            & ~anchor["person_id"].isin(universe)
        ]
        ages = rows["age"].astype("int64")
        seed_birth = (wave - 1) - ages
        rows = rows[
            (
                ages.between(1, _MAX_AGE_CODE)
                & seed_birth.between(
                    career.DERIVED_BIRTH_MIN, career.DERIVED_BIRTH_MAX
                )
            )
            | ages.eq(999)
        ]
        extension.append(
            pd.DataFrame(
                {
                    "person_id": rows["person_id"].astype("int64"),
                    "year": wave - 1,
                    "anchor_wave": wave,
                    "age": rows["age"].astype("int64"),
                }
            )
        )
    extra_seed = _seed_frame(extension)
    extra: dict[int, career.BirthYearRecord] = {}
    if not extra_seed.empty:
        extra_ids = set(int(pid) for pid in extra_seed["person_id"])
        for record in career.derive_birth_years(
            history[history["person_id"].isin(extra_ids)],
            earnings[earnings["person_id"].isin(extra_ids)],
            seed_coordinates=extra_seed,
        ):
            if record.person_id in extra_ids:
                extra[record.person_id] = record
    return U2Births(
        records={**extra, **births},
        universe=universe,
        seed=seed,
        inputs_sha256=input_frames_sha256(inputs),
    )


# ===========================================================================
# Builder
# ===========================================================================
@dataclass(frozen=True)
class U2Cohort:
    """The built U2 observations and dispositions (as U1's cohort).

    ``provenance`` is set by :func:`build_u2_cohort` alone (read-only; a
    constructed or ``dataclasses.replace``-d cohort has none, so its rows
    cannot be joined to any inputs).
    """

    observations: pd.DataFrame
    dispositions: pd.DataFrame
    spec: U2CohortSpec
    diagnostics: Mapping[str, Any]
    provenance: Mapping[str, Any] = field(
        default_factory=lambda: MappingProxyType({}), init=False
    )

    def __init_subclass__(cls, **kwargs: Any) -> None:
        raise TypeError("U2Cohort is final")


def _sequence_group(sequence: int) -> str:
    for name, low, high in _SEQUENCE_GROUPS:
        if low <= sequence <= high:
            return name
    return "not_in_wave" if sequence == 0 else f"sequence_{sequence}"


def marital_status_4(marital_status: str, married: bool) -> str:
    """The Report's four marital rows, else ``unclassified`` (as U1)."""

    if married:
        return "married"
    if marital_status in MARITAL_STATUS_4[1:]:
        return str(marital_status)
    return UNCLASSIFIED_MARITAL_STATUS


def _episodes(history: pd.DataFrame, person_ids: set[int]) -> dict:
    subset = history[history["person_id"].isin(person_ids)]
    if subset.empty:
        return {}
    episodes = psid2010._episodes_with_separation(subset)
    return {int(pid): rows for pid, rows in episodes.groupby("person_id")}


def _annuitant_age(
    pid: int | None,
    income_year: int,
    family_rows: pd.DataFrame,
    births: U2Births,
) -> tuple[Any, str]:
    if pid is None:
        return pd.NA, "absent"
    year = births.birth_year(int(pid))
    if year is not None:
        return int(income_year) - int(year), "derived_birth_year"
    ages = family_rows.loc[family_rows["person_id"].eq(int(pid)), "age"]
    if len(ages) == 1 and 1 <= int(ages.iloc[0]) <= _MAX_AGE_CODE:
        return int(ages.iloc[0]), "wave_age"
    return pd.NA, "missing"


def _unique(pids: list[int]) -> tuple[int | None, str]:
    if len(pids) == 1:
        return pids[0], "unique"
    return None, ("absent" if not pids else "ambiguous")


#: ``legal_spouse_pairing`` when the family has no unique head: a legal
#: spouse is defined relative to the head, so none is paired (it is
#: neither a unique pairing nor an absent spouse).
NO_HEAD_PAIRING = "no_head"


def build_u2_cohort(
    inputs: U2Inputs,
    spec: U2CohortSpec | None = None,
    *,
    role_context: sources.RoleContext,
    births: U2Births | None = None,
) -> U2Cohort:
    """Build ``spec.row``'s observations under ``role_context``.

    ``observations`` has U1's columns (``observation_id``, ``row``,
    ``person_id``, ``birth_year``, ``birth_source``, ``sex``, ``wave``,
    ``income_year``, ``member_age``, ``reported_birth_year``,
    ``weight_raw``, ``weight_multiplier``, ``weight``, ``interview``,
    ``family_unit_id``, ``sequence``, ``relationship``, ``member_role``,
    ``stratum``, ``cluster``, the marital columns, the member's
    co-resident spouse, the head and the head's legal spouse) plus
    ``income_role_rule`` (the role context's kind), ``head_pairing``
    (``unique``/``absent``/``ambiguous``) and ``legal_spouse_pairing``
    (the same, or ``no_head`` when the head is not unique),
    ``spouse_slot_occupied_roster`` and ``spouse_slot_sex`` (the unique
    code-20/22 person, the designated spouse income slot).
    """

    spec = U2CohortSpec() if spec is None else spec
    if not isinstance(spec, U2CohortSpec):
        raise U2CohortError("spec must be a U2CohortSpec")
    identity.check_target(inputs.target_id, "the inputs")
    provenance = _input_provenance(inputs)
    _check_role_context(role_context, provenance["kind"])
    check_unique_identifiers(inputs)
    check_person_joins(inputs)
    if births is None:
        births = derive_u2_births(inputs)
    elif births.inputs_sha256 != provenance["input_frames_sha256"]:
        raise U2CohortError("the births were derived from other inputs")
    sex = inputs.persons.set_index("person_id")["sex"]
    design = inputs.design.set_index("person_id")
    cells = plan_cells(spec)
    targets = {
        pid
        for pid in births.universe
        if births.birth_year(pid) in ALL_BIRTH_YEARS
    }
    plan_years = sorted({b for b, _, _, _, _ in cells})
    episodes = _episodes(inputs.marriage_history, targets)
    with_history = set(int(p) for p in inputs.marriage_history["person_id"])
    dispositions: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    # Section 16c's disclosed counts, by disposition and wave: the members
    # who brought each exclusion.
    excluded_persons: dict[tuple[str, int], set[int]] = {}
    for birth_year, wave, income_year, age, multiplier in cells:
        anchor_frame = inputs.anchors[wave]
        anchor = anchor_frame.set_index("person_id")
        present_ids = set(
            anchor_frame.loc[_present(anchor_frame), "person_id"].astype(int)
        )
        in_family = anchor_frame[
            anchor_frame["sequence"].between(*_SEQUENCE_IN_FAMILY)
        ]
        by_family = {
            int(k): v for k, v in in_family.groupby("interview", sort=False)
        }
        for pid in sorted(
            p for p in targets if births.birth_year(p) == birth_year
        ):
            base = {
                "person_id": pid,
                "birth_year": birth_year,
                "wave": wave,
                "income_year": income_year,
                "age": age,
                "row": spec.row,
                "weight_multiplier": float(multiplier),
            }
            if pid not in anchor.index:
                dispositions.append({**base, "disposition": "not_in_file"})
                continue
            record = anchor.loc[pid]
            if pid not in present_ids:
                group = _sequence_group(int(record["sequence"]))
                reason = (
                    "zero_weight"
                    if group == "in_family" and float(record["weight"]) == 0
                    else f"not_present:{group}"
                )
                dispositions.append({**base, "disposition": reason})
                continue
            person_sex = str(sex.get(pid, "na"))
            if person_sex not in ("male", "female"):
                dispositions.append(
                    {**base, "disposition": "excluded_sex_unknown"}
                )
                continue
            interview = int(record["interview"])
            if not 1 <= interview < _FAMILY_UNIT_SCALE:
                raise U2CohortError(
                    f"wave {wave}: interview {interview} outside the family "
                    "unit identifier domain"
                )
            family_rows = by_family[interview]
            rules = {
                int(row.person_id): role_context.rule(
                    wave, int(row.relationship)
                )
                for row in family_rows.itertuples(index=False)
            }
            sexes = {p: str(sex.get(p, "na")) for p in rules}
            excluded = sources.family_unit_exclusion(rules, sexes)
            if excluded is not None:
                # Section 16c: the family unit supplies no observation to
                # any row; the would-be observation is counted.
                dispositions.append({**base, "disposition": excluded})
                excluded_persons.setdefault((excluded, wave), set()).update(
                    p
                    for p, r in rules.items()
                    if r.family_unit_exclusion is not None
                    and r.family_unit_exclusion.applies(sexes[p])
                )
                continue
            dispositions.append({**base, "disposition": "observation"})
            head, head_pairing = _unique(
                [p for p, r in rules.items() if r.income_role == "head"]
            )
            spouse_ids = [
                p
                for p, r in rules.items()
                if r.legal_spouse_annuity and p != head
            ]
            legal_spouse, spouse_pairing = _unique(spouse_ids)
            if head is None:
                legal_spouse, spouse_pairing = None, NO_HEAD_PAIRING
            slot, _ = _unique([p for p, r in rules.items() if r.spouse_slot])
            relationship = int(record["relationship"])
            rule = rules[pid]
            if pid in episodes:
                state = psid2010.marital_state_at(
                    episodes[pid],
                    income_year,
                    separated_is_married=spec.separated_is_married,
                )
            else:
                state = {
                    "status": (
                        "never_married"
                        if pid in with_history
                        else "no_marriage_history"
                    ),
                    "spouse_person_id": pd.NA,
                }
            spouse = state.get("spouse_person_id")
            married = state["status"] == "married"
            resolution = "marriage_history"
            if state["status"] in _UNRESOLVED_STATES:
                resolution, spouse = "unresolved_non_married", pd.NA
                if pid == head and legal_spouse is not None:
                    resolution = "relationship_code_head_with_legal_spouse"
                    spouse = legal_spouse
                elif (
                    rule.marital_resolution
                    and head is not None
                    and legal_spouse == pid
                ):
                    resolution = (
                        f"relationship_code_legal_spouse_{relationship}"
                    )
                    spouse = head
                married = resolution != "unresolved_non_married"
            members = set(family_rows["person_id"].astype(int))
            coresident = (
                married and not pd.isna(spouse) and int(spouse) in members
            )
            spouse_age, spouse_age_source, spouse_sex = pd.NA, "absent", pd.NA
            if coresident:
                spouse_age, spouse_age_source = _annuitant_age(
                    int(spouse), income_year, family_rows, births
                )
                spouse_sex = str(sex.get(int(spouse), "na"))
            head_age, head_age_source = _annuitant_age(
                head, income_year, family_rows, births
            )
            ls_age, ls_age_source = _annuitant_age(
                legal_spouse, income_year, family_rows, births
            )
            observations.append(
                {
                    "observation_id": f"{pid}:{wave}",
                    "row": spec.row,
                    "person_id": pid,
                    "birth_year": birth_year,
                    "birth_source": births.records[pid].source.value,
                    "sex": person_sex,
                    "wave": wave,
                    "income_year": income_year,
                    "member_age": income_year - birth_year,
                    "reported_birth_year": record["reported_birth_year"],
                    "weight_raw": float(record["weight"]),
                    "weight_multiplier": float(multiplier),
                    "weight": float(record["weight"]) * float(multiplier),
                    "interview": interview,
                    "family_unit_id": wave * _FAMILY_UNIT_SCALE + interview,
                    "sequence": int(record["sequence"]),
                    "relationship": relationship,
                    "member_role": rule.income_role,
                    "income_role_rule": role_context.kind,
                    "stratum": (
                        int(design.loc[pid, "stratum"])
                        if pid in design.index
                        else pd.NA
                    ),
                    "cluster": (
                        int(design.loc[pid, "cluster"])
                        if pid in design.index
                        else pd.NA
                    ),
                    "marital_status": state["status"],
                    "marital_resolution": resolution,
                    "married": bool(married),
                    "marital_status_4": marital_status_4(
                        state["status"], bool(married)
                    ),
                    "spouse_person_id": spouse,
                    "member_married_coresident": bool(coresident),
                    "spouse_age": spouse_age,
                    "spouse_age_source": spouse_age_source,
                    "spouse_sex": spouse_sex,
                    "spouse_slot_occupied_roster": slot is not None,
                    "spouse_slot_sex": (
                        pd.NA if slot is None else str(sex.get(slot, "na"))
                    ),
                    "head_pairing": head_pairing,
                    "legal_spouse_pairing": spouse_pairing,
                    "fu_head_person_id": pd.NA if head is None else head,
                    "fu_head_age": head_age,
                    "fu_head_age_source": head_age_source,
                    "fu_head_sex": (
                        pd.NA if head is None else str(sex.get(head, "na"))
                    ),
                    "fu_head_spouse_present": legal_spouse is not None,
                    "fu_head_spouse_person_id": (
                        pd.NA if legal_spouse is None else legal_spouse
                    ),
                    "fu_head_spouse_relationship": (
                        pd.NA
                        if legal_spouse is None
                        else int(
                            family_rows.loc[
                                family_rows["person_id"].eq(legal_spouse),
                                "relationship",
                            ].iloc[0]
                        )
                    ),
                    "fu_head_spouse_age": ls_age,
                    "fu_head_spouse_age_source": ls_age_source,
                    "fu_head_spouse_sex": (
                        pd.NA
                        if legal_spouse is None
                        else str(sex.get(legal_spouse, "na"))
                    ),
                    "wealth_status": "family_file",
                    "in_institution": False,
                    "income_status": "family_file",
                }
            )
    obs = pd.DataFrame(observations)
    disp = pd.DataFrame(dispositions)
    if not obs.empty:
        _check_family_records(obs, inputs)
        if obs["observation_id"].duplicated().any():
            raise U2CohortError("duplicate (person, wave) observations")
        for column in (
            "spouse_person_id",
            "spouse_age",
            "stratum",
            "cluster",
            "fu_head_person_id",
            "fu_head_age",
            "fu_head_spouse_person_id",
            "fu_head_spouse_relationship",
            "fu_head_spouse_age",
            "reported_birth_year",
        ):
            obs[column] = obs[column].astype("Int64")
        for column in (
            "spouse_sex",
            "spouse_slot_sex",
            "fu_head_sex",
            "fu_head_spouse_sex",
        ):
            obs[column] = obs[column].astype("string")
    outside = sorted(
        pid
        for pid in births.universe
        if births.birth_year(pid) not in ALL_BIRTH_YEARS
    )
    diagnostics = {
        "n_universe": len(births.universe),
        "n_target_birth_year": len(targets),
        "n_outside_birth_years": sum(
            births.birth_year(pid) is not None for pid in outside
        ),
        "n_unresolved_birth_year": sum(
            births.birth_year(pid) is None for pid in outside
        ),
        "plan_birth_years": plan_years,
        "role_context": role_context.kind,
        "births_inputs_sha256": births.inputs_sha256,
        # Section 16c: per wave, the members who brought each counted
        # exclusion (sources.PERSON_COUNTED_EXCLUSIONS: B1's count, which
        # option 1d-1 names and 1d-2 inherits) in family units that would
        # otherwise have supplied this row an observation.  Disclosed;
        # decides nothing.
        "n_family_unit_exclusion_persons": {
            name: {
                str(wave): len(persons)
                for (named, wave), persons in sorted(excluded_persons.items())
                if named == name
            }
            for name in sources.PERSON_COUNTED_EXCLUSIONS
        },
    }
    cohort = U2Cohort(obs, disp, spec, diagnostics)
    object.__setattr__(
        cohort,
        "provenance",
        MappingProxyType(
            {
                **provenance,
                "set_by": (
                    "populace_dynamics.uniform_cut_track_u2.cohort."
                    "build_u2_cohort"
                ),
                "spec": spec.as_dict(),
                "role_context": role_context.kind,
            }
        ),
    )
    return cohort


def _check_family_records(obs: pd.DataFrame, inputs: U2Inputs) -> None:
    missing = []
    for wave, rows in obs.groupby("wave"):
        income = inputs.family_income.get(int(wave))
        if income is None:
            raise U2CohortError(f"inputs lack family income for {wave}")
        if income["interview"].duplicated().any():
            raise U2CohortError(f"wave {wave}: duplicate family interviews")
        known = set(income["interview"].astype(int))
        missing.extend(
            rows.loc[~rows["interview"].isin(known), "observation_id"]
        )
    if missing:
        raise U2CohortError(
            f"{len(missing)} observations have no family-file record "
            f"(first: {list(missing)[:3]}): failed joins refuse execution"
        )


# ===========================================================================
# Income rows and design
# ===========================================================================
def income_rows(cohort: U2Cohort, inputs: U2Inputs) -> pd.DataFrame:
    """Observations merged with their family's income, wealth and DC.

    ``inputs`` must be the inputs the cohort was built from (their frame
    digest equals the cohort's): the provenance and role context the
    rows carry are the cohort's, so no other frames may be joined under
    them.  Every join must be complete (one family record per
    observation); the family file's spouse-slot flag (``wife_present``)
    must agree with the roster's designated income slot (a unique
    code-20 or code-22 person), or the build refuses.  ``attrs`` carries
    the provenance kind, ``target_id`` and the role context to the
    income concept.
    """

    check_cohort_inputs(cohort, inputs)
    obs = cohort.observations
    frames = []
    for wave, rows in obs.groupby("wave", sort=True):
        income = inputs.family_income[int(wave)]
        wealth = inputs.family_wealth.get(int(wave))
        if wealth is None:
            raise U2CohortError(f"inputs lack family wealth for {wave}")
        merged = rows.merge(
            income, on="interview", how="left", validate="many_to_one"
        ).merge(wealth, on="interview", how="left", validate="many_to_one")
        for column in ("total_family_income", "wealth1"):
            if merged[column].isna().any():
                raise U2CohortError(
                    f"wave {int(wave)}: {int(merged[column].isna().sum())} "
                    f"observations lack {column}: failed join"
                )
        if inputs.employer_dc:
            dc = inputs.employer_dc.get(int(wave))
            if dc is None:
                raise U2CohortError(
                    f"wave {int(wave)}: the inputs hold employer DC frames "
                    "but none for this wave"
                )
            columns = ["interview", *sources.DC_BALANCE_COLUMNS]
            merged = merged.merge(
                dc[columns], on="interview", how="left", validate="many_to_one"
            )
            if merged["employer_dc"].isna().any():
                raise U2CohortError(
                    f"wave {int(wave)}: a family has no employer DC record"
                )
        frames.append(merged)
    if not frames:
        raise U2CohortError("the cohort has no observations")
    out = pd.concat(frames, ignore_index=True)
    mismatch = out["wife_present"].astype(bool) != out[
        "spouse_slot_occupied_roster"
    ].astype(bool)
    if mismatch.any():
        raise U2CohortError(
            f"{int(mismatch.sum())} observations: the family file's spouse "
            "income slot disagrees with the roster's code-20/22 occupant "
            "(section 3 role amendment; first "
            f"{out.loc[mismatch, 'observation_id'].tolist()[:3]})"
        )
    out["member_sex"] = out["sex"]
    out.attrs["provenance_kind"] = cohort.provenance.get("kind")
    out.attrs["target_id"] = identity.TARGET_ID
    out.attrs["role_context"] = cohort.provenance.get("role_context")
    return out


def check_cohort_inputs(cohort: U2Cohort, inputs: U2Inputs) -> str:
    """Refuse ``inputs`` unless they are the ones ``cohort`` was built from.

    Compares frame digests, so frames joined to the cohort's
    observations always carry the provenance the cohort recorded.
    """

    if type(cohort) is not U2Cohort or type(inputs) is not U2Inputs:
        raise U2CohortError("a U2Cohort and its U2Inputs are required")
    recorded = cohort.provenance.get("input_frames_sha256")
    observed = input_frames_sha256(inputs)
    if recorded is None or observed != recorded:
        raise U2CohortError(
            "these inputs are not the ones the cohort was built from "
            f"(frames {observed[:12]}..., cohort {str(recorded)[:12]}...): "
            "no other frames may be joined under the cohort's provenance"
        )
    return observed


def design_frame(inputs: U2Inputs, spec: U2CohortSpec) -> pd.DataFrame:
    """Distinct (stratum, cluster) pairs of the row's observation waves.

    Every person with a positive cross-section weight in any of the row's
    observation waves (never a support-only wave) must carry a documented
    stratum (1-94) and cluster (1, 2), or the frame refuses (section 10).
    """

    waves = sorted({w for _, w, _, _ in observation_plan(spec)})
    positive: set[int] = set()
    for wave in waves:
        anchor = inputs.anchors[wave]
        positive |= set(
            anchor.loc[anchor["weight"] > 0, "person_id"].astype(int)
        )
    design = inputs.design[inputs.design["person_id"].isin(positive)]
    lacking = positive - set(design["person_id"].astype(int))
    if lacking:
        raise U2CohortError(
            f"{len(lacking)} positive-weight persons lack a design record"
        )
    strata = design["stratum"]
    clusters = design["cluster"]
    invalid = (
        strata.isna()
        | clusters.isna()
        | ~strata.isin(sorted(DESIGN_VALID_STRATA))
        | ~clusters.isin(sorted(DESIGN_VALID_CLUSTERS))
    )
    if invalid.any():
        raise U2CohortError(
            f"{int(invalid.sum())} positive-weight persons lack a valid "
            "sampling-error stratum or cluster (documented domains: "
            "strata 1-94, clusters 1-2): refused (section 10)"
        )
    return (
        design[["stratum", "cluster"]]
        .astype("int64")
        .drop_duplicates()
        .sort_values(["stratum", "cluster"])
        .reset_index(drop=True)
    )


def structural_summary(cohort: U2Cohort) -> dict[str, Any]:
    """Counts only: dispositions, observations and roles (no income)."""

    obs = cohort.observations
    disp = cohort.dispositions

    def counts(series: pd.Series) -> dict[str, int]:
        return {
            str(k): int(v)
            for k, v in series.value_counts(dropna=False).sort_index().items()
        }

    summary: dict[str, Any] = {
        "row": cohort.spec.row,
        "target_id": identity.TARGET_ID,
        "provenance_kind": cohort.provenance.get("kind"),
        "role_context": cohort.provenance.get("role_context"),
        **{k: v for k, v in cohort.diagnostics.items() if k.startswith("n_")},
        "dispositions_by_birth_year": (
            {
                str(year): counts(rows["disposition"])
                for year, rows in disp.groupby("birth_year")
            }
            if not disp.empty
            else {}
        ),
        "n_observations": int(len(obs)),
    }
    if obs.empty:
        return summary
    summary["by_birth_year_and_wave"] = {
        f"{year}@{wave}": {
            "n_observations": int(len(rows)),
            "n_family_units": int(rows["family_unit_id"].nunique()),
            "member_role": counts(rows["member_role"]),
            "relationship": counts(rows["relationship"]),
            "marital_resolution": counts(rows["marital_resolution"]),
            "marital_status_4": counts(rows["marital_status_4"]),
            "head_pairing": counts(rows["head_pairing"]),
            "legal_spouse_pairing": counts(rows["legal_spouse_pairing"]),
            "fu_head_age_source": counts(rows["fu_head_age_source"]),
            "fu_head_spouse_age_source": counts(
                rows["fu_head_spouse_age_source"]
            ),
            "weight_multiplier": counts(rows["weight_multiplier"]),
        }
        for (year, wave), rows in obs.groupby(["birth_year", "wave"])
    }
    summary["n_persons"] = int(obs["person_id"].nunique())
    summary["design"] = {
        "n_strata": int(obs["stratum"].nunique()),
        "n_clusters": int(
            obs[["stratum", "cluster"]].drop_duplicates().shape[0]
        ),
        "missing_design": int(obs["stratum"].isna().sum()),
    }
    return summary


def replace_provenance(inputs: U2Inputs, **provenance: Any) -> U2Inputs:
    """``inputs`` with ``provenance`` (the digest is recomputed).

    For caller frames and refusal tests.  It never produces invented
    inputs: only the invented generator seals those (the declared role
    context they unlock would otherwise run on any frames).  The result
    carries neither seal, so a ``psid_files`` label is refused too.
    """

    if provenance.get("kind") == INVENTED:
        raise U2CohortError(
            "replace_provenance cannot label inputs invented; only the U2 "
            "invented generator's named variants are invented inputs"
        )
    return dataclasses.replace(
        inputs,
        provenance={
            **provenance,
            "input_frames_sha256": input_frames_sha256(inputs),
        },
    )
