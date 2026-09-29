"""The registered U2 real-data loader (built; refuses before reading).

Specification sections 4 and 14 ("Registered-run preflight: before
reading raw PSID records, verify ... completed independent mapping
review").  :func:`load_u2_inputs` runs in three stages and never reaches
a later stage when an earlier one refuses:

1. **Source preflight** (:func:`source_preflight`), before any file
   under the PSID directory is opened: every registry entry a U2 run
   applies -- the income, wealth and employer-DC fields and routes of
   each support wave, the anchors, weights, design and sex variables,
   the support plan and the role of every amended relationship code --
   must be RESOLVED with no blocking dependency, under the committed,
   pinned registries.  It refuses at the adjudicated registries
   (commit 883ea48): the 2015 income and pension entries depend on the
   refused 2015 code-20 route, the 2019-2023 ones on the refused
   code-90/92 routes, the 2017 spouse age/sex slot metadata and the
   revised 2017 cross-section weight are TO VERIFY, and every
   2017-2023 P64/P65 record waits on the amendment 5 ruling.
2. **Source identity**: each staged setup file and codebook the
   registries cite is rehashed against the registry's recorded SHA-256,
   and every registry layout -- the family files' and the individual
   file's -- is cross-checked against the staged ``.sps`` DATA LIST
   (setup formats checked independently, section 4 step 3); each wave's
   individual weight variable must be the weights registry's.
3. **Reading**: the family files are parsed with the registry layouts
   (:func:`read_family_records`), the individual file through the
   cross-checked setup, the marriage history and earnings through the
   inherited readers; every PSID file read is hashed and the inputs are
   sealed, as U1's loader does.  Every individual-file value must lie in
   its registry entry's documented domain (:func:`check_individual_values`):
   an undocumented sex, relationship, sequence, stratum or cluster code,
   an age or birth year outside the codebook's ranges, a blank field or a
   negative or non-finite weight refuses the load
   (:class:`U2UndocumentedValue`), as the family-file parse refuses
   out-of-domain values (``sources._check_domain``).

This module computes no income concept, threshold, annuity or poverty
status.  No real PSID record is read in development: the tests run
stage 1 as committed (it refuses) and stages 2 and 3 on an invented
staged directory, with the registry blockers, the cited-source rehash
and the two inherited readers patched
(``tests/track_u2/test_u2_loader.py``).
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from types import MappingProxyType
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.data import psid
from populace_dynamics.uniform_cut_track_u2 import cohort, identity, sources

__all__ = [
    "ANCHOR_CONCEPTS",
    "U2LoaderRefusal",
    "U2UndocumentedValue",
    "check_individual_values",
    "check_layouts_against_setup",
    "check_source_hashes",
    "family_record_specs",
    "individual_specs",
    "load_u2_inputs",
    "read_family_records",
    "required_entries",
    "source_preflight",
]

#: The individual-file anchors of each support wave (section 3 table).
ANCHOR_CONCEPTS: tuple[str, ...] = (
    "interview",
    "sequence",
    "relationship",
    "age",
    "reported_birth_year",
    "weight",
)
_COMMON_INDIVIDUAL = (
    "common.person_family_id",
    "common.person_number",
    "common.stratum",
    "common.cluster",
    "common.sex",
)
_DC_ROUTES = (
    "current_job",
    "previous_combined",
    "previous_dc_only",
    "formula_unknown_checkpoint",
    "ira_rollovers",
    "duplicate_and_off_route",
    "amounts_brackets_top_codes",
    "respondent_slots",
)

#: The documented domains of the individual-file fields whose registry
#: entry lists no ``codes``, restated from each entry's ``codebook_text``
#: (``tests/track_u2/test_u2_loader.py`` holds every wave's text to them):
#: age -- 0 Inap., 1 newborn, 2-125 actual age, 999 DK/NA/refused; year
#: born -- the entry's ``missing_codes`` (0 Inap., 9999 DK/NA/refused) or
#: 1870 through the wave year; interview number -- 0 Inap. or a family
#: interview number within the five-column field; the 1968 family and
#: person numbers -- positive (every documented range starts at 1).  The
#: cross-sectional weight's entry says "do not infer a domain from
#: empirical ranges printed in codebook", so a weight must only be finite
#: and nonnegative.  A field with neither ``codes`` nor a domain here
#: refuses (never read unchecked).
_AGE_CODES: tuple[int, ...] = (0, 999)
_AGE_RANGE: tuple[int, int] = (1, 125)
_FIRST_BIRTH_YEAR = 1870
_INTERVIEW_RANGE: tuple[int, int] = (0, 99_999)
_POSITIVE_IDENTIFIERS: tuple[str, ...] = ("person_family_id", "person_number")
#: ``common.sex`` codes (ER32000: 1 Male, 2 Female, 9 NA).
_PERSON_SEX: dict[int, str] = {1: "male", 2: "female", 9: "na"}


class U2LoaderRefusal(sources.U2SourceRefusal):
    """The U2 loader refuses before reading (or on changed sources)."""


class U2UndocumentedValue(U2LoaderRefusal):
    """An individual-file value lies outside its registry entry's
    documented codes or range: it refuses, never maps to ``na`` or falls
    back (section 14)."""


def required_entries(
    registries: sources.RegistrySet,
) -> list[tuple[str, str]]:
    """Every ``(registry, entry id)`` a U2 run applies."""

    out: list[tuple[str, str]] = []
    for wave in sources.SUPPORT_WAVES:
        out += [
            ("income", f"income.{wave}.{concept}")
            for concept in sources.INCOME_CONCEPTS
        ]
        wealth1 = registries.entry("wealth", f"wealth.{wave}.wealth1")
        terms = {
            entry["variable"]: entry["route"]
            for entry in registries.entries("wealth")
            if entry["wave"] == wave and "variable" in entry
        }
        identity_terms = [
            terms[variable]
            for key in ("assets", "debts")
            for variable in wealth1["identity"][key]
        ]
        out += [
            ("wealth", f"wealth.{wave}.{concept}")
            for concept in dict.fromkeys(
                [*sources.WEALTH_CONCEPTS, *identity_terms]
            )
        ]
        out += [("pension", f"{wave}.{spec}") for spec in _pension_concepts()]
        out += [("pension", f"{wave}.route.{route}") for route in _DC_ROUTES]
        if wave >= 2017:
            out.append(("pension", f"{wave}.route.inherited_route_amendment"))
        out += [
            ("individual", f"{wave}.{concept}") for concept in ANCHOR_CONCEPTS
        ]
        out.append(("weights", f"{wave}.cross_section_weight"))
        out += [
            ("roles", f"{wave}.relationship.{code}")
            for code in sources.RELATIONSHIP_CODES
        ]
    out += [("individual", entry) for entry in _COMMON_INDIVIDUAL]
    out += [("design", "common.stratum"), ("design", "common.cluster")]
    out += [
        ("support", entry["id"]) for entry in registries.entries("support")
    ]
    return list(dict.fromkeys(out))


def _pension_concepts() -> list[str]:
    names = []
    for person in ("head", "wife"):
        names += [f"{person}_current_type", f"{person}_current_amount"]
        for plan in (1, 2):
            names += [
                f"{person}_prev{plan}_type",
                f"{person}_prev{plan}_combo_disposition",
                f"{person}_prev{plan}_combo_amount",
                f"{person}_prev{plan}_dc_disposition",
                f"{person}_prev{plan}_dc_amount",
            ]
    return names


def source_preflight(
    registries: sources.RegistrySet | None = None,
) -> dict[str, Any]:
    """Refuse unless every entry a U2 run applies is resolved.

    Opens no PSID file: only the committed registries.  Row U1's plan
    must first equal the support registry cell by cell
    (:func:`~populace_dynamics.uniform_cut_track_u2.cohort.
    check_plan_against_support_registry`).  An absent relationship code's
    entry (code 92 in 2013 and 2015) passes when it is RESOLVED; the
    builder refuses the code if it ever appears.
    """

    registries = (
        sources.RegistrySet.committed() if registries is None else registries
    )
    if type(registries) is not sources.RegistrySet or (
        registries.kind != "committed"
    ):
        raise U2LoaderRefusal(
            "the loader applies only the committed, pinned registries"
        )
    registries.verify()
    plan = cohort.check_plan_against_support_registry(registries)
    refused: list[str] = []
    entries = required_entries(registries)
    for name, entry_id in entries:
        entry = registries.entry(name, entry_id)
        if name == "roles" and entry.get("present") is False:
            if entry.get("status") != "RESOLVED":
                refused.append(f"roles:{entry_id}: absent code unresolved")
            continue
        refused += sources.blockers(entry, name)
    if refused:
        raise U2LoaderRefusal(
            f"{len(refused)} registry blockers refuse the U2 load before "
            "any PSID record is opened (section 14 registered-run "
            "preflight; first: " + " | ".join(refused[:5]) + ")"
        )
    return {
        "registries": registries.provenance(),
        "plan": plan,
        "n_entries_required": len(entries),
        "all_resolved": True,
    }


def check_source_hashes(
    registries: sources.RegistrySet, data_dir: Path
) -> dict[str, str]:
    """Rehash every staged source the registries cite; refuse changes.

    Registry sources name paths under ``PSID/``; the staged file is the
    same path under ``data_dir``.  Other cited sources (repository files)
    are rehashed under the repository root.
    """

    checked: dict[str, str] = {}
    for name in registries.documents:
        for source in registries.documents[name].get("sources", []) or []:
            if not isinstance(source, Mapping) or "sha256" not in source:
                continue
            cited = str(source["file"])
            path = (
                Path(data_dir) / cited.removeprefix("PSID/")
                if cited.startswith("PSID/")
                else identity.ROOT / cited
            )
            if not path.is_file():
                raise U2LoaderRefusal(f"cited source {cited} is not staged")
            observed = hashlib.sha256(path.read_bytes()).hexdigest()
            if observed != source["sha256"]:
                raise U2LoaderRefusal(
                    f"cited source {cited} changed ({observed[:12]}... != "
                    f"{str(source['sha256'])[:12]}...): changed source bytes "
                    "refuse execution (section 14)"
                )
            checked[cited] = observed
    return checked


def check_layouts_against_setup(
    specs: Sequence[sources.FieldSpec], sps_path: Path
) -> int:
    """Refuse a registry layout the staged ``.sps`` DATA LIST contradicts."""

    layout = psid.parse_sps_layout(sps_path).set_index("name")
    for spec in specs:
        if spec.variable not in layout.index:
            raise U2LoaderRefusal(
                f"{spec.registry_id}: {spec.variable} is not in {sps_path}"
            )
        row = layout.loc[spec.variable]
        if (int(row["start"]), int(row["end"])) != (spec.start, spec.end):
            raise U2LoaderRefusal(
                f"{spec.registry_id}: registry columns {spec.start}-"
                f"{spec.end} differ from the setup's {int(row['start'])}-"
                f"{int(row['end'])}"
            )
    return len(specs)


def family_record_specs(
    wave: int, gate: sources.SourceGate
) -> list[sources.FieldSpec]:
    """Every field U2 reads from one family-file record of ``wave``."""

    income = sources.field_specs("income", wave, sources.INCOME_CONCEPTS, gate)
    identity_terms = sources.wealth1_identity(wave, gate)
    wealth = sources.field_specs(
        "wealth",
        wave,
        list(
            dict.fromkeys(
                [
                    *sources.WEALTH_CONCEPTS,
                    *identity_terms["assets"],
                    *identity_terms["debts"],
                ]
            )
        ),
        gate,
    )
    specs = [*income, *wealth, *sources.pension_field_specs(wave, gate)]
    sources.check_overlaps(specs)
    return specs


def read_family_records(
    lines: Iterable[str],
    wave: int,
    gate: sources.SourceGate,
) -> dict[str, pd.DataFrame]:
    """Parse one wave's family records into the U2 income, wealth and DC
    frames (the shapes :class:`~populace_dynamics.uniform_cut_track_u2.
    cohort.U2Inputs` holds).  Parsing refuses any field outside its
    documented domain; the DC balances use the wave's route under
    ``gate``.  Under any gate but the registry gate the specs carry that
    gate, so only records the invented writer produced are parsed
    (:func:`~populace_dynamics.uniform_cut_track_u2.sources.
    parse_fixed_width`)."""

    if type(gate) is not sources.SourceGate:
        raise U2LoaderRefusal("family records are read through a SourceGate")
    specs = family_record_specs(wave, gate)
    raw = sources.parse_fixed_width(lines, specs)
    identity_terms = sources.wealth1_identity(wave, gate)
    income = sources.decode_income(raw[list(sources.INCOME_CONCEPTS)])
    wealth_columns = list(
        dict.fromkeys(
            [
                "interview",
                "wealth1",
                "wealth1_acc",
                "home_equity",
                *identity_terms["assets"],
                *identity_terms["debts"],
            ]
        )
    )
    wealth = raw[wealth_columns].copy()
    dc_specs = [
        spec for spec in specs if spec.registry_id.startswith("pension")
    ]
    dc_raw = raw[["interview", *(spec.concept for spec in dc_specs)]]
    dc = sources.employer_dc_balances(
        dc_raw,
        sources.dc_route(wave, gate),
        {
            spec.concept: spec.width
            for spec in dc_specs
            if spec.concept.endswith("_amount")
        },
    )
    return {
        "income": income,
        "wealth": wealth,
        "employer_dc": dc,
        "income_identity": sources.income_identity_counts(
            raw, sources.income_identity(wave, gate)
        ),
        "wealth1_identity": sources.wealth1_identity_counts(
            raw, identity_terms
        ),
    }


def load_u2_inputs(*, data_dir: Path | None = None) -> cohort.U2Inputs:
    """Read every U2 input from the staged PSID, or refuse first.

    Stage 1 (:func:`source_preflight`) refuses at the adjudicated
    registries, before any PSID file is opened.
    """

    registries = sources.RegistrySet.committed()
    preflight = source_preflight(registries)
    # Stages 2 and 3 run only once every required route is resolved.
    from populace_dynamics.cohorts import psid2010
    from populace_dynamics.data import family, marriage

    gate = sources.SourceGate(sources.REGISTRY, registries)
    data_root = psid._resolve_data_dir(data_dir)
    source_hashes = check_source_hashes(registries, data_root)
    with psid2010.record_files_read(data_root) as files:
        incomes, wealth, pensions = {}, {}, {}
        for wave in sources.SUPPORT_WAVES:
            sps_path, txt_path = family._family_paths(wave, data_root)
            specs = family_record_specs(wave, gate)
            check_layouts_against_setup(specs, sps_path)
            with txt_path.open(encoding="ascii") as handle:
                frames = read_family_records(handle, wave, gate)
            incomes[wave] = frames["income"]
            wealth[wave] = frames["wealth"]
            pensions[wave] = frames["employer_dc"]
        anchors, persons, design = _read_individual(registries, data_root)
        history = marriage.marriage_history(data_dir=data_root)
        earnings = family.family_earnings_panel(
            waves=family.FAMILY_WAVES, data_dir=data_root
        )
    if not files:
        raise RuntimeError("no PSID file was recorded as read")
    inputs = cohort.U2Inputs(
        anchors=anchors,
        design=design,
        persons=persons,
        marriage_history=history,
        observed_earnings=earnings,
        family_income=incomes,
        family_wealth=wealth,
        employer_dc=pensions,
    )
    bundle = hashlib.sha256(
        (json.dumps(dict(files), sort_keys=True) + "\n").encode()
    ).hexdigest()
    inputs = dataclasses.replace(
        inputs,
        provenance={
            "kind": cohort.PSID_FILES,
            "psid_data_dir": str(data_root),
            "psid_files_sha256": dict(files),
            "psid_files_bundle_sha256": bundle,
            "registries": preflight["registries"],
            "cited_sources_sha256": source_hashes,
        },
    )
    object.__setattr__(
        inputs,
        "loader_seal",
        MappingProxyType(
            {
                "input_frames_sha256": cohort.input_frames_sha256(inputs),
                "psid_files_bundle_sha256": bundle,
            }
        ),
    )
    return inputs


def individual_specs(
    registries: sources.RegistrySet,
) -> list[sources.FieldSpec]:
    """The individual-file fields U2 reads, at their registry layouts.

    Each wave's weight variable must be the weights registry's
    cross-section weight for that wave, and the stratum and cluster the
    design registry's, or the load refuses.
    """

    specs = []
    for key in _individual_keys():
        entry = registries.entry("individual", key)
        layout = entry["layout"]
        specs.append(
            sources.FieldSpec(
                concept=key,
                variable=entry["variable"],
                start=int(layout["start"]),
                end=int(layout["end"]),
                width=int(layout["width"]),
                decimals=0,
                negative_allowed=False,
                kind="individual",
                registry_id=f"individual:{key}",
            )
        )
    for wave in sources.SUPPORT_WAVES:
        weight = registries.entry("individual", f"{wave}.weight")["variable"]
        registered = registries.entry(
            "weights", f"{wave}.cross_section_weight"
        )["variable"]
        if weight != registered:
            raise U2LoaderRefusal(
                f"{wave}: the individual registry reads weight {weight}, "
                f"the weights registry {registered}"
            )
    for concept in ("stratum", "cluster"):
        individual = registries.entry("individual", f"common.{concept}")
        design = registries.entry("design", f"common.{concept}")
        if (individual["variable"], individual["layout"]) != (
            design["variable"],
            design["layout"],
        ):
            raise U2LoaderRefusal(
                f"the individual and design registries disagree on the "
                f"sampling-error {concept}"
            )
    sources.check_overlaps(specs)
    return specs


def _individual_keys() -> list[str]:
    return [
        f"{wave}.{concept}"
        for wave in sources.SUPPORT_WAVES
        for concept in ANCHOR_CONCEPTS
    ] + list(_COMMON_INDIVIDUAL)


def _documented(
    key: str, entry: Mapping[str, Any], values: np.ndarray
) -> np.ndarray:
    """Which integer ``values`` the registry entry ``key`` documents."""

    codes = entry.get("codes") or {}
    concept = entry["concept"]
    if codes:
        return np.isin(values, sorted(int(code) for code in codes))
    if concept == "age":
        low, high = _AGE_RANGE
        return np.isin(values, _AGE_CODES) | (values >= low) & (values <= high)
    if concept == "reported_birth_year":
        missing = [int(code) for code in entry["missing_codes"]]
        return np.isin(values, missing) | (values >= _FIRST_BIRTH_YEAR) & (
            values <= int(entry["wave"])
        )
    if concept == "interview":
        low, high = _INTERVIEW_RANGE
        return (values >= low) & (values <= high)
    if concept in _POSITIVE_IDENTIFIERS:
        return values >= 1
    raise U2UndocumentedValue(
        f"individual:{key} lists no documented codes and U2 declares no "
        "documented range for it: an unchecked field is never read "
        "(section 14)"
    )


def check_individual_values(
    raw: pd.DataFrame, registries: sources.RegistrySet
) -> dict[str, int]:
    """Refuse any individual-file value outside its registry domain.

    Section 14: an unresolved input refuses, never falls back.  Every
    field U2 reads from the individual file must hold, in every record, a
    value its registry entry documents: one of the entry's ``codes``
    (sex 1, 2 or 9; each wave's relationship and sequence codes; the
    sampling-error stratum and cluster), or the documented range restated
    in :data:`_AGE_CODES` and its neighbours for the fields the registry
    lists no codes for.  A blank or non-integer field refuses; the weight
    must be finite and nonnegative.  Refusals name the field and count
    the records; coded fields also list the undocumented codes, other
    fields never print a value.  Returns ``{registry key: n records}``.
    """

    checked: dict[str, int] = {}
    for key in _individual_keys():
        entry = registries.entry("individual", key)
        variable = entry["variable"]
        if variable not in raw.columns:
            raise U2UndocumentedValue(
                f"individual:{key}: {variable} was not read"
            )
        values = pd.to_numeric(raw[variable], errors="coerce").to_numpy(
            dtype="float64"
        )
        what = f"individual:{key} ({variable})"
        unreadable = int((~np.isfinite(values)).sum())
        if unreadable:
            raise U2UndocumentedValue(
                f"{what}: {unreadable} record(s) blank, non-numeric or not "
                "finite; the codebooks assign every missing value, so the "
                "load refuses (section 14)"
            )
        if entry["concept"] == "weight":
            negative = int((values < 0).sum())
            if negative:
                raise U2UndocumentedValue(
                    f"{what}: {negative} negative cross-section weight(s); "
                    "a weight must be finite and nonnegative"
                )
            checked[key] = len(values)
            continue
        fractional = int((values != np.floor(values)).sum())
        if fractional:
            raise U2UndocumentedValue(
                f"{what}: {fractional} non-integer value(s) in a whole-number "
                "field"
            )
        integers = values.astype(np.int64)
        outside = ~_documented(key, entry, integers)
        if outside.any():
            listed = (
                f" (undocumented codes "
                f"{sorted({int(v) for v in integers[outside]})[:5]})"
                if entry.get("codes")
                else ""
            )
            raise U2UndocumentedValue(
                f"{what}: {int(outside.sum())} record(s) outside the "
                f"registry's documented domain{listed}; an undocumented "
                "value refuses the load, never maps to 'na' or falls back "
                "(section 14)"
            )
        checked[key] = len(values)
    return checked


def _read_individual(
    registries: sources.RegistrySet, data_root: Path
) -> tuple[dict[int, pd.DataFrame], pd.DataFrame, pd.DataFrame]:
    """The anchors, sex and design from the individual file (stage 3).

    The staged setup's DATA LIST must agree with every registry layout
    (:func:`check_layouts_against_setup`) before the file is read, and
    every value read must be documented (:func:`check_individual_values`)
    before any is used.
    """

    specs = individual_specs(registries)
    check_layouts_against_setup(
        specs, psid.product_sps_path("ind2023er", data_root)
    )
    variables = {}
    for wave in sources.SUPPORT_WAVES:
        for concept in ANCHOR_CONCEPTS:
            entry = registries.entry("individual", f"{wave}.{concept}")
            variables[(wave, concept)] = entry["variable"]
    common = {
        key.split(".", 1)[1]: registries.entry("individual", key)["variable"]
        for key in _COMMON_INDIVIDUAL
    }
    columns = sorted({*variables.values(), *common.values()})
    raw = psid.read_psid("ind2023er", columns=columns, data_dir=data_root)
    check_individual_values(raw, registries)
    person_id = raw[common["person_family_id"]].astype("int64") * 1000 + raw[
        common["person_number"]
    ].astype("int64")
    anchors = {}
    for wave in sources.SUPPORT_WAVES:
        frame = pd.DataFrame({"person_id": person_id})
        for concept in ANCHOR_CONCEPTS:
            frame[concept] = raw[variables[(wave, concept)]]
        for column in ("interview", "sequence", "relationship", "age"):
            frame[column] = frame[column].astype("int64")
        frame["weight"] = frame["weight"].astype("float64")
        reported = frame["reported_birth_year"].astype("Int64")
        frame["reported_birth_year"] = reported.mask(reported.isin([0, 9999]))
        anchors[wave] = frame
    # Every value is a documented code (1, 2 or 9, checked above); only
    # the documented NA code 9 becomes "na".
    sex = raw[common["sex"]].astype("int64").map(_PERSON_SEX)
    persons = pd.DataFrame({"person_id": person_id, "sex": sex}).astype(
        {"sex": "string"}
    )
    design = pd.DataFrame(
        {
            "person_id": person_id,
            "stratum": raw[common["stratum"]].astype("int64"),
            "cluster": raw[common["cluster"]].astype("int64"),
        }
    )
    if person_id.duplicated().any():
        raise U2LoaderRefusal("duplicate person_id in the individual file")
    return anchors, persons, design
