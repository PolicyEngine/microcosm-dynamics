"""The registered U2 real-data loader (built; refuses today).

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
   pinned registries.  Today it refuses: milestone 1 records 48 open
   documentary entries, and every 2015-2023 income entry depends on the
   open code-90/92 (and 2015 code-20) routing.
2. **Source identity**: each staged setup file and codebook the
   registries cite is rehashed against the registry's recorded SHA-256,
   and every registry layout is cross-checked against the staged
   ``.sps`` DATA LIST (setup formats checked independently, section 4
   step 3).
3. **Reading**: the family files are parsed with the registry layouts
   (:func:`read_family_records`), the individual file through the
   cross-checked setup, the marriage history and earnings through the
   inherited readers; every PSID file read is hashed and the inputs are
   sealed, as U1's loader does.

This module computes no income concept, threshold, annuity or poverty
status.  Stages 2 and 3 are exercised on invented files by the tests; no
real PSID record is read in development.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from populace_dynamics.data import psid
from populace_dynamics.uniform_cut_track_u2 import cohort, identity, sources

__all__ = [
    "ANCHOR_CONCEPTS",
    "U2LoaderRefusal",
    "check_layouts_against_setup",
    "check_source_hashes",
    "family_record_specs",
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


class U2LoaderRefusal(sources.U2SourceRefusal):
    """The U2 loader refuses before reading (or on changed sources)."""


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
        out += [
            ("pension", f"{wave}.{spec}")
            for spec in _pension_concepts()
        ]
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

    Opens no PSID file: only the committed registries.  An absent
    relationship code's entry (code 92 in 2013 and 2015) passes when it
    is RESOLVED; the builder refuses the code if it ever appears.
    """

    registries = (
        sources.RegistrySet.committed() if registries is None else registries
    )
    if registries.kind != "committed":
        raise U2LoaderRefusal(
            "the loader applies only the committed, pinned registries"
        )
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
    ``gate``."""

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
    dc_specs = [spec for spec in specs if spec.registry_id.startswith("pension")]
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

    Stage 1 (:func:`source_preflight`) refuses today, before any PSID
    file is opened.
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
        {
            "input_frames_sha256": cohort.input_frames_sha256(inputs),
            "psid_files_bundle_sha256": bundle,
        },
    )
    return inputs


def _read_individual(
    registries: sources.RegistrySet, data_root: Path
) -> tuple[dict[int, pd.DataFrame], pd.DataFrame, pd.DataFrame]:
    """The anchors, sex and design from the individual file (stage 3)."""

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
        if (frame["weight"] < 0).any():
            raise U2LoaderRefusal(f"negative {wave} cross-section weight")
        reported = frame["reported_birth_year"].astype("Int64")
        frame["reported_birth_year"] = reported.mask(reported.isin([0, 9999]))
        anchors[wave] = frame
    sex = raw[common["sex"]].map({1: "male", 2: "female"}).fillna("na")
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
