"""The PSID cohort at age 67 for DynaSim scorecard exercise 2 (Track U).

Plan ``critical-path-uniform-cut-20260923.md``, work item U5.  Exercise 2
measures, for persons born 1936-1945, the change in the adjusted poverty
rate in the year they turn 67 under a 13 percent cut in Social Security.
Track U measures it on realized PSID outcomes (*PSID-realized outcomes,
not a projection*): the PSID is biennial from 1999 and a wave reports
income for the previous calendar year, so only even income years are
observed.

Rows (plan section 3 and fields F1-F2):

* **U0 (primary): exact age.**  Birth years 1937, 1939, 1941, 1943 and
  1945, each observed in the income year it turns 67 (2004 ... 2012),
  from waves 2005 ... 2013, weighted by that wave's core/immigrant
  individual cross-section weight.
* **U1 (registered alternative): all ten birth years.**  Odd birth years
  as U0; each even birth year 1938-1944 (odd age-67 year) observed at 66
  and at 68 with half weight each; 1936 observed at 68 only (income year
  2004; its age-66 year 2002 is in the 2003 wave, which has aggregates
  only) with weight ``u1_single_observation_weight`` (1, a builder
  choice: the plan says only "1936 from 2004 only").

Universe per wave (F2): sequence 1-20 (in a responding family) with a
positive cross-section weight; the registered option U-inst adds
sequence 51-59 (institution).  The PSID collects no income for an
institutionalized person (the individual-file Social Security items are
"Inap.: ... in an institution", codebook ER34137-ER34143 for 2011) and
the plan gives them no income rule, so ``institution_income_rule`` (a
builder default pending the referee) supplies one:

* ``family_of_record`` (default): the PSID attaches an institutionalized
  sample member's record to the family they left (2011 User Guide,
  section 2.4) and counts it among the individual records "having the
  same family-level data" as that family (family-file codebook text for
  the record-count variable).  The observation takes that family unit's
  income, wealth, size and children through its interview number, with
  the member's own age and sex; its role is ``ofum`` (neither the
  current head nor the wife: the relationship code of a person in an
  institution is to the previous wave's head, codebook note on ER34103)
  and it has no co-resident spouse.  The member's own income is not in
  the family's income and ``# IN FU`` ("the actual number of persons
  currently in the FU") is read as not counting them: a named delta.
  An institutionalized person whose interview number has no family-file
  record in that wave is a disposition, not an observation.
* ``excluded``: institutionalized persons stay out of the poverty
  universe (a disposition, as under the primary's universe), so U-inst
  equals U0 in population and only its counts differ.

The cross-section weight is also positive for movers-out (71-80) and
decedents (81-89), whom neither option admits; the dispositions count
them.

Birth year: :func:`populace_dynamics.estimates.career.derive_birth_years`
(first-estimates section 3.1), total over the union of the five waves'
presence universes.  Its seed coordinate (clause 3) is the earliest of
the five waves in which the person is present, ``(wave - 1) - age``; the
plan names the law but not the seed wave (builder choice).

Attached to each observation: the family unit of that wave
(``family_unit_id = wave * 100000 + interview``), the member's role
(head 10, legal wife 20, cohabiting "wife" 22, otherwise OFUM; the codes
are verified against ``IND2023ER_formats.sas`` for each wave), sex, the
PSID sampling-error stratum and cluster (ER31996, ER31997), marital
status at the end of the income year from the marriage history
(:func:`populace_dynamics.cohorts.psid2010.marital_state_at`, separated
counts as married by default, F12; a state the history cannot resolve,
``unknown`` or ``no_marriage_history``, counts as non-married under
``unresolved_marital_status``), whether a legal spouse lives in the
same family unit, the spouse's age and sex (for the joint annuity), and
the family's income (:func:`populace_dynamics.data.family_income.
read_family_income`) and wealth (:func:`populace_dynamics.data.
family_income.read_family_wealth`).  Waves 2005 and 2007 have no staged
wealth, so their observations are marked
``blocked_wealth_supplement_not_staged``.

Provenance: :func:`load_age67_inputs` records the SHA-256 of every PSID
file it read and seals the returned inputs; the builder marks a cohort
``psid_files`` only for sealed inputs, ``invented`` for inputs whose
frames hash to the digest their recorded ``invented`` provenance carries
(the invented generator,
:mod:`populace_dynamics.uniform_cut_track_u.invented`, which this module
cannot import, re-generates and checks them), and ``caller_frames``
otherwise.
:func:`income_rows` carries the kind to the income concept, whose guard
refuses PSID-built rows without a registration.  This module computes no
poverty status, threshold, annuity or statistic.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from populace_dynamics.cohorts import psid2010
from populace_dynamics.data import (
    deaths,
    disability,
    family,
    family_income,
    marriage,
    psid,
)
from populace_dynamics.data import social_security_income as ssi
from populace_dynamics.estimates import career

__all__ = [
    "ALL_BIRTH_YEARS",
    "ANCHOR_LAYOUTS",
    "CALLER_FRAMES",
    "INSTITUTION_INCOME_RULES",
    "INVENTED",
    "PRIMARY_BIRTH_YEARS",
    "PSID_FILES",
    "ROWS",
    "TARGET_AGE",
    "WAVES",
    "Age67Cohort",
    "Age67Inputs",
    "Age67Spec",
    "build_age67_cohort",
    "income_rows",
    "load_age67_inputs",
    "observation_plan",
    "pending_decisions",
    "read_design_variables",
    "read_wave_anchor",
    "structural_summary",
    "verify_relationship_codes",
]

TARGET_AGE = 67
WAVES: tuple[int, ...] = family_income.INCOME_WAVES
PRIMARY_BIRTH_YEARS: tuple[int, ...] = (1937, 1939, 1941, 1943, 1945)
ALL_BIRTH_YEARS: tuple[int, ...] = tuple(range(1936, 1946))
ROWS: tuple[str, ...] = ("U0", "U1")
PSID_FILES = "psid_files"
INVENTED = "invented"
CALLER_FRAMES = "caller_frames"
#: The income rules for an institutionalized observation (row U-inst).
INSTITUTION_INCOME_RULES: dict[str, str] = {
    "family_of_record": (
        "the family unit whose interview number the institutionalized "
        "member's record carries (the family they left): its income, "
        "wealth, size and children, with the member's own age and sex, "
        "role ofum and no co-resident spouse (builder default, pending the "
        "referee)"
    ),
    "excluded": (
        "institutionalized persons stay out of the poverty universe (a "
        "disposition); U-inst then equals U0 in population"
    ),
}

#: Each wave's label-verified individual-file anchor variables (labels
#: checked 2026-09-24 against IND2023ER.sps; 2009 and 2011 are the
#: layouts of :data:`populace_dynamics.cohorts.psid2010.ANCHOR_LAYOUTS`).
ANCHOR_LAYOUTS: dict[int, psid2010.AnchorWaveLayout] = {
    2005: psid2010.AnchorWaveLayout(
        wave=2005,
        variables={
            "interview": ("ER33801", "2005 INTERVIEW NUMBER"),
            "sequence": ("ER33802", "SEQUENCE NUMBER 05"),
            "relationship": ("ER33803", "RELATION TO HEAD 05"),
            "age": ("ER33804", "AGE OF INDIVIDUAL 05"),
            "reported_birth_year": ("ER33806", "YEAR INDIVIDUAL BORN 05"),
            "weight": ("ER33849", "CORE/IMM INDIVIDUAL CROSS-SECTION WT 05"),
        },
    ),
    2007: psid2010.AnchorWaveLayout(
        wave=2007,
        variables={
            "interview": ("ER33901", "2007 INTERVIEW NUMBER"),
            "sequence": ("ER33902", "SEQUENCE NUMBER 07"),
            "relationship": ("ER33903", "RELATION TO HEAD 07"),
            "age": ("ER33904", "AGE OF INDIVIDUAL 07"),
            "reported_birth_year": ("ER33906", "YEAR INDIVIDUAL BORN 07"),
            "weight": ("ER33951", "CORE/IMM INDIVIDUAL CROSS-SECTION WT 07"),
        },
    ),
    2009: psid2010.ANCHOR_LAYOUTS[2009],
    2011: psid2010.ANCHOR_LAYOUTS[2011],
    2013: psid2010.AnchorWaveLayout(
        wave=2013,
        variables={
            "interview": ("ER34201", "2013 INTERVIEW NUMBER"),
            "sequence": ("ER34202", "SEQUENCE NUMBER 13"),
            "relationship": ("ER34203", "RELATION TO HEAD 13"),
            "age": ("ER34204", "AGE OF INDIVIDUAL 13"),
            "reported_birth_year": ("ER34206", "YEAR INDIVIDUAL BORN 13"),
            "weight": ("ER34269", "CORE/IMM INDIVIDUAL CROSS-SECTION WT 13"),
        },
    ),
}
_DESIGN_VARS: dict[str, str] = {
    "ER31996": "SAMPLING ERROR STRATUM",
    "ER31997": "SAMPLING ERROR CLUSTER",
}
_PERSON_VARS: dict[str, str] = {
    "ER30001": "1968 INTERVIEW NUMBER",
    "ER30002": "PERSON NUMBER 68",
}
_HEAD, _LEGAL_WIFE, _PARTNER = 10, 20, 22
_SEQUENCE_IN_FAMILY = (1, 20)
_SEQUENCE_INSTITUTION = (51, 59)
_SEQUENCE_GROUPS: tuple[tuple[str, int, int], ...] = (
    ("in_family", 1, 20),
    ("institution", 51, 59),
    ("moved_out", 71, 80),
    ("died", 81, 89),
)
_REPORTED_BIRTH_YEAR_NA = (0, 9999)
#: Individual-file ages above this are sentinels (999 = NA).
_MAX_AGE_CODE = 125
_FAMILY_UNIT_SCALE = 100_000
_ASSET_ACCURACY = [
    f"{concept}_acc"
    for concept in family_income.ASSET_INCOME_CONCEPTS
    if f"{concept}_acc" in family_income.ACCURACY_CONCEPTS
]
#: Expected label prefixes of the relationship codes in each wave's
#: formats block (``IND2023ER_formats.sas``).
_RELATIONSHIP_PREFIXES = {
    _HEAD: "head in {wave}",
    _LEGAL_WIFE: "legal wife in {wave}",
    _PARTNER: '"wife"',
}


@dataclass(frozen=True)
class Age67Spec:
    """The builder's open choices; defaults are the plan's primary."""

    row: str = "U0"
    presence: str = "in_family"
    separated_is_married: bool = True
    u1_single_observation_weight: float = 1.0
    seed_wave_rule: str = "earliest_presence_wave"
    unresolved_marital_status: str = "non_married"
    institution_income_rule: str = "family_of_record"

    def __post_init__(self) -> None:
        if self.row not in ROWS:
            raise ValueError(f"row must be one of {ROWS}")
        if self.presence not in ("in_family", "in_family_or_institution"):
            raise ValueError("presence must be in_family[_or_institution]")
        if self.institution_income_rule not in INSTITUTION_INCOME_RULES:
            raise ValueError(
                "institution_income_rule must be one of "
                f"{sorted(INSTITUTION_INCOME_RULES)}"
            )
        if self.seed_wave_rule != "earliest_presence_wave":
            raise ValueError("seed_wave_rule must be earliest_presence_wave")
        if self.unresolved_marital_status != "non_married":
            raise ValueError(
                "unresolved_marital_status must be non_married (no other "
                "rule is built)"
            )
        weight = float(self.u1_single_observation_weight)
        if not 0.0 < weight <= 1.0:
            raise ValueError("u1_single_observation_weight in (0, 1]")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def pending_decisions() -> tuple[psid2010.PendingDecision, ...]:
    """Every open choice of :class:`Age67Spec`, with its default."""

    spec = Age67Spec()
    freeze = "U1 specification freeze (Max's ratification by merge)"
    return (
        psid2010.PendingDecision(
            "row",
            spec.row,
            ("U1",),
            "plan F1: exact age (U0) is the primary; U1 pools all ten "
            "birth years",
            freeze,
        ),
        psid2010.PendingDecision(
            "presence",
            spec.presence,
            ("in_family_or_institution",),
            "plan F2 (U-inst adds institutions; no income rule exists "
            "for them)",
            freeze,
        ),
        psid2010.PendingDecision(
            "separated_is_married",
            spec.separated_is_married,
            (False,),
            "plan F12 ('legally married per MH85_23'); a separated person "
            "is still legally married",
            freeze,
        ),
        psid2010.PendingDecision(
            "u1_single_observation_weight",
            spec.u1_single_observation_weight,
            (0.5,),
            "builder choice: the plan says only '1936 from 2004 only'",
            freeze,
        ),
        psid2010.PendingDecision(
            "seed_wave_rule",
            spec.seed_wave_rule,
            (),
            "builder choice: the birth-year law's seed coordinate comes "
            "from the earliest of the five waves in which the person is "
            "present",
            freeze,
        ),
        psid2010.PendingDecision(
            "unresolved_marital_status",
            spec.unresolved_marital_status,
            (),
            "builder choice: plan F12 ('legally married per MH85_23') "
            "does not say how to classify a member whose marriage history "
            "cannot date the state ('unknown') or who has no record "
            "('no_marriage_history'); they count as non-married (the "
            "non_married cell, a single-life annuity)",
            freeze,
        ),
        psid2010.PendingDecision(
            "institution_income_rule",
            spec.institution_income_rule,
            ("excluded",),
            "builder default, pending the referee: plan F2 adds "
            "institutions under U-inst but gives them no income rule and "
            "the PSID collects none for them; the PSID attaches an "
            "institutionalized member's record to the family they left "
            "(2011 User Guide section 2.4), so the observation takes that "
            "family's income concept and threshold (the member's own "
            "income is missing and the family's size does not count them: "
            "a named delta). Applies only under presence "
            "in_family_or_institution",
            freeze,
        ),
    )


def observation_plan(
    spec: Age67Spec,
) -> tuple[tuple[int, int, int, float], ...]:
    """``(birth_year, wave, income_year, weight_multiplier)`` per row."""

    plan = [(b, b + 68, b + 67, 1.0) for b in PRIMARY_BIRTH_YEARS]
    if spec.row == "U1":
        for b in range(1938, 1945, 2):
            plan.append((b, b + 67, b + 66, 0.5))
            plan.append((b, b + 69, b + 68, 0.5))
        plan.append(
            (1936, 2005, 2004, float(spec.u1_single_observation_weight))
        )
    for _, wave, income_year, _ in plan:
        if wave not in WAVES or income_year != wave - 1:
            raise AssertionError("observation plan outside the read waves")
    return tuple(sorted(plan))


# --------------------------------------------------------------------------
# Readers
# --------------------------------------------------------------------------
def read_wave_anchor(
    wave: int, *, data_dir: Path | None = None, nrows: int | None = None
) -> pd.DataFrame:
    """Label-verified individual-file anchor columns for one wave.

    Columns: ``person_id``, ``interview``, ``sequence``, ``relationship``,
    ``age``, ``reported_birth_year`` (``<NA>`` for 0 or 9999) and
    ``weight``.  The weight must be the wave's only "CROSS-SECTION WT
    <yy>" label.
    """

    if wave not in ANCHOR_LAYOUTS:
        raise ValueError(f"wave must be one of {sorted(ANCHOR_LAYOUTS)}")
    layout = ANCHOR_LAYOUTS[wave]
    labels = psid.parse_sps_labels(
        psid.product_sps_path("ind2023er", data_dir)
    )
    expected = layout.labels()
    psid.verify_labels(labels, expected, context=f"ind2023er {wave} anchor")
    hits = sorted(
        name
        for name, label in labels.items()
        if re.search(layout.weight_concept, " ".join(label.split()))
    )
    if hits != [layout.weight_variable]:
        raise ValueError(
            f"{wave} cross-section weight concept matched {hits}; expected "
            f"only {layout.weight_variable}"
        )
    raw = psid.read_psid(
        "ind2023er", columns=list(expected), data_dir=data_dir, nrows=nrows
    )
    frame = pd.DataFrame(
        {
            "person_id": raw["ER30001"].astype("int64") * 1000
            + raw["ER30002"].astype("int64")
        }
    )
    for var, column in layout.columns().items():
        frame[column] = raw[var]
    for column in ("interview", "sequence", "relationship", "age"):
        frame[column] = frame[column].astype("int64")
    frame["weight"] = frame["weight"].astype("float64")
    if (frame["weight"] < 0).any():
        raise ValueError(f"negative {wave} cross-section weight")
    reported = frame["reported_birth_year"].astype("Int64")
    frame["reported_birth_year"] = reported.mask(
        reported.isin(_REPORTED_BIRTH_YEAR_NA)
    )
    if frame["person_id"].duplicated().any():
        raise ValueError("duplicate person_id in the individual file")
    return frame


def read_design_variables(
    *, data_dir: Path | None = None, nrows: int | None = None
) -> pd.DataFrame:
    """``person_id``, ``stratum`` (ER31996) and ``cluster`` (ER31997)."""

    labels = psid.parse_sps_labels(
        psid.product_sps_path("ind2023er", data_dir)
    )
    psid.verify_labels(
        labels, {**_PERSON_VARS, **_DESIGN_VARS}, context="ind2023er design"
    )
    raw = psid.read_psid(
        "ind2023er",
        columns=[*_PERSON_VARS, *_DESIGN_VARS],
        data_dir=data_dir,
        nrows=nrows,
    )
    return pd.DataFrame(
        {
            "person_id": raw["ER30001"].astype("int64") * 1000
            + raw["ER30002"].astype("int64"),
            "stratum": raw["ER31996"].astype("int64"),
            "cluster": raw["ER31997"].astype("int64"),
        }
    )


def verify_relationship_codes(
    *, data_dir: Path | None = None, waves: tuple[int, ...] = WAVES
) -> dict[int, str]:
    """Check codes 10, 20 and 22 in each wave's relationship format."""

    fmt_path = disability.employment_status_formats_path(data_dir)
    blocks = ssi.parse_value_label_blocks(fmt_path)
    assignments = disability.parse_sas_format_assignments(fmt_path)
    out: dict[int, str] = {}
    for wave in waves:
        var = ANCHOR_LAYOUTS[wave].variables["relationship"][0]
        fmt = assignments.get(var, f"{var}F")
        codes = blocks.get(fmt, {})
        for code, prefix in _RELATIONSHIP_PREFIXES.items():
            label = " ".join(codes.get(code, "").lower().split())
            if not label.startswith(prefix.format(wave=wave)):
                raise ValueError(
                    f"wave {wave}: relationship code {code} in {fmt} is "
                    f"{label!r}, expected a label starting "
                    f"{prefix.format(wave=wave)!r}"
                )
        out[wave] = fmt
    return out


# --------------------------------------------------------------------------
# Inputs and provenance
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Age67Inputs:
    """Materialized reader outputs the pure builder consumes."""

    anchors: Mapping[int, pd.DataFrame]
    design: pd.DataFrame
    death_records: pd.DataFrame
    marriage_history: pd.DataFrame
    observed_earnings: pd.DataFrame
    family_income: Mapping[int, pd.DataFrame]
    family_wealth: Mapping[int, pd.DataFrame]
    wealth_refusals: Mapping[int, str]
    provenance: Mapping[str, Any] = field(default_factory=dict)
    loader_seal: Mapping[str, str] | None = field(
        default=None, init=False, repr=False, compare=False
    )


def _frame_digest(digest: Any, name: str, frame: pd.DataFrame) -> None:
    digest.update(f"{name}\n".encode())
    digest.update(json.dumps([str(c) for c in frame.columns]).encode())
    digest.update(json.dumps([str(t) for t in frame.dtypes]).encode())
    digest.update(frame.to_csv(index=False, lineterminator="\n").encode())


def input_frames_sha256(inputs: Age67Inputs) -> str:
    """SHA-256 of every input frame (and the wealth refusals)."""

    digest = hashlib.sha256()
    for wave in sorted(inputs.anchors):
        _frame_digest(digest, f"anchor_{wave}", inputs.anchors[wave])
    for name in (
        "design",
        "death_records",
        "marriage_history",
        "observed_earnings",
    ):
        _frame_digest(digest, name, getattr(inputs, name))
    for wave in sorted(inputs.family_income):
        _frame_digest(digest, f"income_{wave}", inputs.family_income[wave])
    for wave in sorted(inputs.family_wealth):
        _frame_digest(digest, f"wealth_{wave}", inputs.family_wealth[wave])
    digest.update(
        json.dumps(
            {str(k): v for k, v in sorted(inputs.wealth_refusals.items())}
        ).encode()
    )
    return digest.hexdigest()


def _mapping_sha256(values: Mapping[str, str]) -> str:
    encoded = (
        json.dumps(dict(values), sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def load_age67_inputs(*, data_dir: Path | None = None) -> Age67Inputs:
    """Read every input from the staged PSID, recording file hashes."""

    data_root = psid._resolve_data_dir(data_dir)
    refusals: dict[int, str] = {}
    with psid2010.record_files_read(data_root) as files:
        relationship_formats = verify_relationship_codes(data_dir=data_dir)
        anchors = {
            wave: read_wave_anchor(wave, data_dir=data_dir) for wave in WAVES
        }
        design = read_design_variables(data_dir=data_dir)
        death_records = deaths.read_death_records(data_dir=data_dir)
        history = marriage.marriage_history(data_dir=data_dir)
        earnings = family.family_earnings_panel(
            waves=family.FAMILY_WAVES, data_dir=data_dir
        )
        incomes = {
            wave: family_income.read_family_income(wave, data_dir=data_dir)
            for wave in WAVES
        }
        wealth = {}
        for wave in WAVES:
            try:
                wealth[wave] = family_income.read_family_wealth(
                    wave, data_dir=data_dir
                )
            except (
                family_income.WealthSupplementNotStagedError,
                family_income.WealthSupplementNotAdjudicatedError,
            ) as error:
                refusals[wave] = f"{type(error).__name__}: {error}"
    if not files:
        raise RuntimeError("no PSID file was recorded as read")
    inputs = Age67Inputs(
        anchors=anchors,
        design=design,
        death_records=death_records,
        marriage_history=history,
        observed_earnings=earnings,
        family_income=incomes,
        family_wealth=wealth,
        wealth_refusals=refusals,
        provenance={
            "kind": PSID_FILES,
            "psid_data_dir": str(data_root),
            "psid_files_sha256": dict(files),
            "psid_files_bundle_sha256": _mapping_sha256(files),
            "relationship_formats": {
                str(k): v for k, v in relationship_formats.items()
            },
        },
    )
    object.__setattr__(
        inputs,
        "loader_seal",
        {
            "input_frames_sha256": input_frames_sha256(inputs),
            "psid_files_bundle_sha256": _mapping_sha256(files),
        },
    )
    return inputs


def _input_provenance(inputs: Age67Inputs) -> dict[str, Any]:
    recorded = dict(inputs.provenance or {})
    frames = input_frames_sha256(inputs)
    files = recorded.get("psid_files_sha256")
    if recorded.get("kind") == INVENTED:
        if recorded.get("input_frames_sha256") != frames:
            raise ValueError(
                "inputs claim invented provenance but their frames differ "
                "from the digest the invented generator recorded "
                f"({recorded.get('input_frames_sha256')!r} != {frames!r}); "
                "invented data cannot be mixed with other frames"
            )
        return {
            "kind": INVENTED,
            "generator": recorded.get("generator"),
            "seed": recorded.get("seed"),
            "supplement_waves_staged": recorded.get("supplement_waves_staged"),
            "label": recorded.get("data"),
            "input_frames_sha256": frames,
        }
    if recorded.get("kind") == PSID_FILES:
        if inputs.loader_seal is None or not isinstance(files, Mapping):
            raise ValueError(
                "inputs claim psid_files provenance but were not returned "
                "by load_age67_inputs"
            )
        if inputs.loader_seal != {
            "input_frames_sha256": frames,
            "psid_files_bundle_sha256": _mapping_sha256(dict(files)),
        }:
            raise ValueError(
                "the frames or PSID file hashes changed after the loader "
                "sealed them"
            )
        return {
            "kind": PSID_FILES,
            "psid_data_dir": recorded.get("psid_data_dir"),
            "psid_files_sha256": dict(files),
            "psid_files_bundle_sha256": recorded.get(
                "psid_files_bundle_sha256"
            ),
            "input_frames_sha256": frames,
        }
    return {
        "kind": CALLER_FRAMES,
        "note": "frames not returned by load_age67_inputs",
        "label": recorded.get("label"),
        "input_frames_sha256": frames,
    }


# --------------------------------------------------------------------------
# Builder
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Age67Cohort:
    """The built observations.

    ``observations``: one row per planned observation of a member (a
    person with a target birth year present in the observation's wave);
    ``dispositions``: one row per (person, planned observation) for every
    person of a target birth year in the union universe, with the reason
    when it is not an observation; ``provenance`` is set by the builder.
    """

    observations: pd.DataFrame
    dispositions: pd.DataFrame
    spec: Age67Spec
    diagnostics: Mapping[str, Any]
    provenance: Mapping[str, Any] = field(default_factory=dict)


def _presence(anchor: pd.DataFrame, spec: Age67Spec) -> pd.Series:
    low, high = _SEQUENCE_IN_FAMILY
    mask = anchor["sequence"].between(low, high)
    if spec.presence == "in_family_or_institution":
        low, high = _SEQUENCE_INSTITUTION
        mask |= anchor["sequence"].between(low, high)
    return mask & (anchor["weight"] > 0)


def _sequence_group(sequence: int) -> str:
    for name, low, high in _SEQUENCE_GROUPS:
        if low <= sequence <= high:
            return name
    return "not_in_wave" if sequence == 0 else f"sequence_{sequence}"


def _birth_years(
    inputs: Age67Inputs, spec: Age67Spec
) -> tuple[dict[int, career.BirthYearRecord], set[int]]:
    seeds = []
    for wave in WAVES:
        anchor = inputs.anchors[wave]
        present = anchor[_presence(anchor, spec)]
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
    seed = (
        pd.concat(seeds, ignore_index=True)
        .sort_values(["person_id", "anchor_wave"])
        .drop_duplicates("person_id", keep="first")
        .reset_index(drop=True)
    )
    universe = set(int(pid) for pid in seed["person_id"])
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
    return births, universe


def _episodes(history: pd.DataFrame, person_ids: set[int]) -> dict:
    subset = history[history["person_id"].isin(person_ids)]
    if subset.empty:
        return {}
    episodes = psid2010._episodes_with_separation(subset)
    return {int(pid): rows for pid, rows in episodes.groupby("person_id")}


def build_age67_cohort(
    inputs: Age67Inputs, spec: Age67Spec | None = None
) -> Age67Cohort:
    """Build the age-67 observations of ``spec.row`` from ``inputs``.

    ``observations`` columns: ``observation_id`` (``"<person>:<wave>"``),
    ``row``, ``person_id``, ``birth_year``, ``birth_source``, ``sex``,
    ``wave``, ``income_year``, ``member_age`` (income year minus birth
    year), ``reported_birth_year``, ``weight_raw``,
    ``weight_multiplier``, ``weight``, ``interview``, ``family_unit_id``,
    ``sequence``, ``relationship``, ``member_role``, ``stratum``,
    ``cluster``, ``marital_status``, ``married``, ``spouse_person_id``,
    ``member_married_coresident``, ``spouse_age``, ``spouse_sex``,
    ``fu_legal_wife_present``, ``wife_sex``, ``wealth_status``,
    ``in_institution`` and ``income_status`` (``family_file`` for a member
    of the family unit, ``family_of_record`` for an institutionalized
    member under that rule).
    """

    spec = Age67Spec() if spec is None else spec
    provenance = _input_provenance(inputs)
    missing = set(WAVES) - set(inputs.anchors)
    if missing:
        raise ValueError(f"inputs lack anchor waves {sorted(missing)}")
    births, universe = _birth_years(inputs, spec)
    sex = inputs.death_records.set_index("person_id")["sex"]
    design = inputs.design.set_index("person_id")
    plan = observation_plan(spec)
    target_years = sorted({b for b, _, _, _ in plan})
    targets = {
        pid
        for pid, record in births.items()
        if record.birth_year in target_years
    }
    episodes = _episodes(inputs.marriage_history, targets)
    with_history = set(
        int(pid) for pid in inputs.marriage_history["person_id"]
    )
    disposition_rows = []
    observation_rows = []
    for birth_year, wave, income_year, multiplier in plan:
        anchor = inputs.anchors[wave].set_index("person_id")
        present = _presence(inputs.anchors[wave], spec)
        present_ids = set(
            inputs.anchors[wave].loc[present, "person_id"].astype(int)
        )
        in_family = inputs.anchors[wave][
            inputs.anchors[wave]["sequence"].between(*_SEQUENCE_IN_FAMILY)
        ]
        by_family = {
            int(k): v for k, v in in_family.groupby("interview", sort=False)
        }
        family_records = (
            set(inputs.family_income[wave]["interview"].astype(int))
            if wave in inputs.family_income
            else set()
        )
        cohort_ids = sorted(
            pid for pid in targets if births[pid].birth_year == birth_year
        )
        for pid in cohort_ids:
            base = {
                "person_id": pid,
                "birth_year": birth_year,
                "wave": wave,
                "income_year": income_year,
                "row": spec.row,
            }
            if pid not in anchor.index:
                disposition_rows.append({**base, "disposition": "not_in_file"})
                continue
            record = anchor.loc[pid]
            person_sex = str(sex.get(pid, "na"))
            if pid not in present_ids:
                group = _sequence_group(int(record["sequence"]))
                admitted = ("in_family",) + (
                    ("institution",)
                    if spec.presence == "in_family_or_institution"
                    else ()
                )
                reason = (
                    "zero_weight"
                    if group in admitted and float(record["weight"]) == 0
                    else f"not_present:{group}"
                )
                disposition_rows.append(
                    {
                        **base,
                        "disposition": reason,
                        "weight_raw": float(record["weight"]),
                    }
                )
                continue
            if person_sex not in ("male", "female"):
                disposition_rows.append(
                    {**base, "disposition": "excluded_sex_unknown"}
                )
                continue
            interview = int(record["interview"])
            sequence = int(record["sequence"])
            relationship = int(record["relationship"])
            in_institution = (
                _SEQUENCE_INSTITUTION[0]
                <= sequence
                <= _SEQUENCE_INSTITUTION[1]
            )
            if in_institution:
                if spec.institution_income_rule == "excluded":
                    disposition_rows.append(
                        {**base, "disposition": "institution_excluded_by_rule"}
                    )
                    continue
                if interview not in family_records:
                    disposition_rows.append(
                        {
                            **base,
                            "disposition": (
                                "institution_family_of_record_missing"
                            ),
                        }
                    )
                    continue
            disposition_rows.append({**base, "disposition": "observation"})
            family_rows = by_family.get(interview)
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
            # An unresolved state ("unknown", "no_marriage_history") is
            # classified by spec.unresolved_marital_status; its only built
            # value, "non_married", leaves it out of "married".
            married = state["status"] == "married"
            coresident = (
                married
                and not pd.isna(spouse)
                and family_rows is not None
                and int(spouse) in set(family_rows["person_id"].astype(int))
                and sequence <= _SEQUENCE_IN_FAMILY[1]
            )
            spouse_age = pd.NA
            spouse_sex = pd.NA
            if coresident:
                spouse_row = family_rows.set_index("person_id").loc[
                    int(spouse)
                ]
                raw_age = int(spouse_row["age"])
                # Individual-file age codes 999 (NA) and 0 carry no age.
                spouse_age = (
                    raw_age if 1 <= raw_age <= _MAX_AGE_CODE else pd.NA
                )
                spouse_sex = str(sex.get(int(spouse), "na"))
            wife_sex = pd.NA
            legal_wife = False
            if family_rows is not None:
                wives = family_rows[
                    family_rows["relationship"].isin([_LEGAL_WIFE, _PARTNER])
                ]
                legal_wife = bool(
                    family_rows["relationship"].eq(_LEGAL_WIFE).any()
                )
                if len(wives) == 1:
                    wife_sex = str(
                        sex.get(int(wives["person_id"].iloc[0]), "na")
                    )
            # An institutionalized member is neither the current head nor
            # the wife of its family of record: its relationship code is to
            # the previous wave's head (codebook note on ER34103).
            role = (
                "ofum"
                if in_institution
                else (
                    "head"
                    if relationship == _HEAD
                    else (
                        "wife"
                        if relationship in (_LEGAL_WIFE, _PARTNER)
                        else "ofum"
                    )
                )
            )
            observation_rows.append(
                {
                    "observation_id": f"{pid}:{wave}",
                    "row": spec.row,
                    "person_id": pid,
                    "birth_year": birth_year,
                    "birth_source": births[pid].source.value,
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
                    "sequence": sequence,
                    "relationship": relationship,
                    "member_role": role,
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
                    "married": bool(married),
                    "spouse_person_id": spouse,
                    "member_married_coresident": bool(coresident),
                    "spouse_age": spouse_age,
                    "spouse_sex": spouse_sex,
                    "fu_legal_wife_present": legal_wife,
                    "wife_sex": wife_sex,
                    "wealth_status": (
                        "family_file"
                        if wave in inputs.family_wealth
                        else "blocked_wealth_supplement_not_staged"
                    ),
                    "in_institution": bool(in_institution),
                    "income_status": (
                        "family_of_record" if in_institution else "family_file"
                    ),
                }
            )
    observations = pd.DataFrame(observation_rows)
    dispositions = pd.DataFrame(disposition_rows)
    if not observations.empty:
        _check_family_records(observations, inputs)
        for column in ("spouse_person_id", "spouse_age", "stratum", "cluster"):
            observations[column] = observations[column].astype("Int64")
        observations["reported_birth_year"] = observations[
            "reported_birth_year"
        ].astype("Int64")
        for column in ("spouse_sex", "wife_sex"):
            observations[column] = observations[column].astype("string")
    cohort = Age67Cohort(
        observations=observations,
        dispositions=dispositions,
        spec=spec,
        diagnostics={
            "n_universe": len(universe),
            "n_target_birth_year": len(targets),
            "wealth_refusals": {
                str(k): v for k, v in sorted(inputs.wealth_refusals.items())
            },
        },
    )
    object.__setattr__(
        cohort,
        "provenance",
        {
            **provenance,
            "set_by": "populace_dynamics.cohorts.age67.build_age67_cohort",
            "spec": spec.as_dict(),
        },
    )
    return cohort


def _check_family_records(
    observations: pd.DataFrame, inputs: Age67Inputs
) -> None:
    missing = []
    for wave, rows in observations.groupby("wave"):
        income = inputs.family_income.get(int(wave))
        if income is None:
            raise ValueError(f"inputs lack family income for {wave}")
        known = set(income["interview"].astype(int))
        from_family = rows["income_status"].isin(
            ["family_file", "family_of_record"]
        )
        absent = rows.loc[from_family & ~rows["interview"].isin(known)]
        missing.extend(absent["observation_id"].tolist())
    if missing:
        raise ValueError(
            f"{len(missing)} in-family observations have no family-file "
            f"record (first: {missing[:3]})"
        )


def income_rows(
    cohort: Age67Cohort,
    inputs: Age67Inputs,
    *,
    allow_blocked: bool = False,
) -> pd.DataFrame:
    """Observations merged with their family's income and wealth.

    The rows :func:`populace_dynamics.estimates.adjusted_poverty.
    adjusted_incomes` consumes.  An institutionalized observation under
    ``family_of_record`` merges its family of record's income and wealth
    like any member.  Observations whose wave has no staged wealth are
    refused unless ``allow_blocked`` (then they are left out and counted
    in ``attrs["left_out"]``).  ``attrs["provenance_kind"]`` carries the
    cohort's provenance kind to the income concept's guard.
    """

    obs = cohort.observations
    blocked = obs["wealth_status"].ne("family_file") | ~obs[
        "income_status"
    ].isin(["family_file", "family_of_record"])
    if blocked.any() and not allow_blocked:
        waves = sorted(set(obs.loc[blocked, "wave"].astype(int)))
        raise ValueError(
            f"{int(blocked.sum())} observations (waves {waves}) cannot get "
            "the income concept: wealth supplement not staged; pass "
            "allow_blocked=True only for a registered fallback row"
        )
    kept = obs.loc[~blocked].copy()
    frames = []
    for wave, rows in kept.groupby("wave"):
        income = inputs.family_income[int(wave)]
        wealth = inputs.family_wealth[int(wave)]
        merged = rows.merge(
            income.drop(columns=["wave", "income_year"]),
            on="interview",
            how="left",
            validate="many_to_one",
        ).merge(
            wealth.drop(columns=["wave"]),
            on="interview",
            how="left",
            validate="many_to_one",
        )
        frames.append(merged)
    out = (
        pd.concat(frames, ignore_index=True)
        if frames
        else pd.DataFrame(columns=obs.columns)
    )
    out["member_sex"] = out["sex"]
    out.attrs["provenance_kind"] = cohort.provenance.get("kind")
    out.attrs["left_out"] = {
        "wealth_supplement_not_staged": int(
            obs["wealth_status"].ne("family_file").sum()
        ),
    }
    return out


# --------------------------------------------------------------------------
# Structural summary (counts only)
# --------------------------------------------------------------------------
def _counts(series: pd.Series) -> dict[str, int]:
    return {
        str(key): int(value)
        for key, value in series.value_counts(dropna=False)
        .sort_index()
        .items()
    }


def structural_summary(
    cohort: Age67Cohort, inputs: Age67Inputs
) -> dict[str, Any]:
    """Counts only: persons, observations, dispositions and blockers.

    No income, threshold, annuity or poverty status is computed.  The
    income and wealth reconciliation counts check component identities
    over every family of each wave (no threshold is involved).
    """

    obs = cohort.observations
    dispositions = cohort.dispositions
    summary: dict[str, Any] = {
        "row": cohort.spec.row,
        "spec": cohort.spec.as_dict(),
        "provenance_kind": cohort.provenance.get("kind"),
        "n_universe_persons": cohort.diagnostics["n_universe"],
        "n_target_birth_year_persons": cohort.diagnostics[
            "n_target_birth_year"
        ],
        "dispositions_by_birth_year": (
            {
                str(year): _counts(rows["disposition"])
                for year, rows in dispositions.groupby("birth_year")
            }
            if not dispositions.empty
            else {}
        ),
        "wealth_refusals": cohort.diagnostics["wealth_refusals"],
    }
    if obs.empty:
        summary["n_observations"] = 0
        return summary
    by_year = {}
    for (year, wave), rows in obs.groupby(["birth_year", "wave"]):
        by_year[f"{year}@{wave}"] = {
            "income_year": int(rows["income_year"].iloc[0]),
            "n_observations": int(len(rows)),
            "n_family_units": int(rows["family_unit_id"].nunique()),
            "member_role": _counts(rows["member_role"]),
            "sex": _counts(rows["sex"]),
            "married": _counts(rows["married"]),
            "member_married_coresident": _counts(
                rows["member_married_coresident"]
            ),
            "coresident_spouse_age_or_sex_unknown": int(
                (
                    rows["member_married_coresident"]
                    & (
                        rows["spouse_age"].isna()
                        | ~rows["spouse_sex"].isin(["male", "female"])
                    )
                ).sum()
            ),
            "marital_status": _counts(rows["marital_status"]),
            "wealth_status": _counts(rows["wealth_status"]),
            "income_status": _counts(rows["income_status"]),
            "birth_source": _counts(rows["birth_source"]),
            "reported_birth_year_differs": int(
                (
                    rows["reported_birth_year"].notna()
                    & (rows["reported_birth_year"] != rows["birth_year"])
                ).sum()
            ),
            "weight_multiplier": _counts(rows["weight_multiplier"]),
        }
    summary["n_observations"] = int(len(obs))
    summary["n_persons"] = int(obs["person_id"].nunique())
    summary["observations_by_birth_year_and_wave"] = by_year
    summary["design"] = {
        "n_strata": int(obs["stratum"].nunique()),
        "n_clusters": int(
            obs[["stratum", "cluster"]].drop_duplicates().shape[0]
        ),
        "missing_design": int(obs["stratum"].isna().sum()),
    }
    shared = obs.groupby("family_unit_id")["person_id"].nunique()
    summary["family_units_with_two_or_more_members"] = int((shared > 1).sum())
    computable = obs["wealth_status"].eq("family_file") & obs[
        "income_status"
    ].isin(["family_file", "family_of_record"])
    summary["n_observations_computable_now"] = int(computable.sum())
    summary["n_observations_blocked"] = int((~computable).sum())
    receipt = {}
    for wave, rows in obs.loc[computable].groupby("wave"):
        income = inputs.family_income[int(wave)].set_index("interview")
        wealth = inputs.family_wealth[int(wave)].set_index("interview")
        fam = income.loc[rows["interview"].astype(int)]
        wel = wealth.loc[rows["interview"].astype(int)]
        receipt[str(int(wave))] = {
            "n_observations": int(len(rows)),
            "family_social_security_positive": int(
                (
                    fam[list(family_income.SOCIAL_SECURITY_CONCEPTS)].sum(
                        axis=1
                    )
                    > 0
                ).sum()
            ),
            "family_ssi_positive": int(
                (fam[list(family_income.SSI_CONCEPTS)].sum(axis=1) > 0).sum()
            ),
            "family_reported_asset_income_nonzero": int(
                (
                    fam[list(family_income.ASSET_INCOME_CONCEPTS)].sum(axis=1)
                    != 0
                ).sum()
            ),
            "social_security_accuracy_nonzero": (
                int(
                    (fam[["head_ss_acc", "wife_ss_acc", "ofum_ss_acc"]] != 0)
                    .any(axis=1)
                    .sum()
                )
                if "head_ss_acc" in fam
                else None
            ),
            "asset_income_accuracy_nonzero": (
                int((fam[_ASSET_ACCURACY] != 0).any(axis=1).sum())
                if "head_ss_acc" in fam
                else None
            ),
            "wealth1_negative": int((wel["wealth1"] < 0).sum()),
            "wealth1_zero": int((wel["wealth1"] == 0).sum()),
            "wealth1_imputed": int((wel["wealth1_acc"] == 1).sum()),
            "fu_size": _counts(fam["fu_size"].clip(upper=9)),
        }
    summary["component_receipt_counts"] = receipt
    return summary
