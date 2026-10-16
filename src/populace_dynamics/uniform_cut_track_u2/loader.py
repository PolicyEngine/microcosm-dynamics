"""The registered U2 real-data loader (built; refuses before reading).

Specification sections 4 and 14 ("Registered-run preflight: before
reading raw PSID records, verify ... completed independent mapping
review").  :func:`load_u2_inputs` runs in three stages and never reaches
a later stage when an earlier one refuses.  Before them, an unfrozen load
(the section 20 step-4 pass) refuses without Max's recorded authorization
(**Authorization** below).

1. **Source preflight** (:func:`source_preflight`), before any file
   under the PSID directory is opened: every registry entry a U2 run
   applies -- the income, wealth and employer-DC fields and routes of
   each support wave, the anchors, weights, design and sex variables,
   the support plan and the role of every amended relationship code --
   must be RESOLVED with no blocking dependency, under the committed,
   pinned registries.  Since amendment 1c's registry commit it passes at
   the committed registries: no blocker remains.  The d1090 registry
   commit (section 16c) replaced the refused 2015 code-20 and 2019-2023
   code-90/92 routes with the ratified family-unit exclusions, which
   released the income and pension entries that depended on them; the
   d637 registry commits (section 16b) resolved the ratified amendments
   one by one: amendment 1's parts 1a-1c (as Max confirmed on
   2026-10-12, d745; 1c resolves code 88 in every wave), amendment 2's
   spouse age/sex slot metadata, amendment 3's crosswalks, amendment 4's
   wealth flags, 5b's 2015 P62A checkpoint, 5a's 2017-2023 P64/P65 route
   and amendment 6's 2017 weight.
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

**Authorization.**  The section 20 step-4 pass reads real PSID records,
so it needs Max's authorization, recorded as a chief-of-staff decision.
:func:`structural_pass_authorization` records the decision id the pass
names (``--authorized-by`` in ``scripts/track_u2_structure.py`` and
``scripts/track_u2_component_diagnostics.py``), the git head and the UTC
time; an unfrozen :func:`load_u2_inputs` refuses without that record,
before the source preflight and before any PSID path is resolved
(:class:`U2AuthorizationRefusal`).  The record only records the
authorization; it does not grant one.  The registered run's load is
frozen instead: its evidence, which must be the committed record, binds
every file and frame digest.

**Frozen identities** (section 14: "changed source bytes, changed frame
digests ... refuse execution.  Pre-registration mapping checks resolve
these before the one-shot; execution rechecks their frozen
identities").  The section 20 step-4 structure pass records, from the
loader-sealed inputs, the SHA-256 of every PSID file the loader read and
the sealed ``input_frames_sha256`` (:func:`preregistration_evidence`,
written by ``scripts/track_u2_structure.py``); the committed record lives
at :data:`PREREGISTRATION_EVIDENCE_PATH`, and the registered run binds its
hash, file hashes and frame digest into the registration binding.  Given
that record -- the committed one: any other, however well-formed,
refuses before any PSID path is resolved -- :func:`load_u2_inputs`
rehashes every frozen file before any record is parsed and refuses a
changed or missing one, refuses to open any file under the PSID
directory that the record does not freeze while it reads, then refuses
a read file set or frame digest other than the frozen ones
(:class:`U2FrozenIdentityMismatch`); the seal then records the evidence
hash, which a registered run requires.

This module computes no income concept, threshold, annuity or poverty
status.  No real PSID record is read in development: the tests run the
authorization check and stage 1 as committed (an unauthorized unfrozen
load refuses before any PSID path is resolved; stage 1 passes and opens
no PSID file) and stages 2 and 3 on an invented staged directory, with
the registry blockers, the cited-source rehash and the two inherited
readers patched
(``tests/track_u2/test_u2_loader.py``).
"""

from __future__ import annotations

import contextlib
import contextvars
import dataclasses
import datetime
import hashlib
import json
import os
import re
import sys
from collections.abc import Iterable, Iterator, Mapping, Sequence
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.data import psid
from populace_dynamics.uniform_cut_track_u2 import cohort, identity, sources

__all__ = [
    "ANCHOR_CONCEPTS",
    "PREREGISTRATION_EVIDENCE_PATH",
    "PREREGISTRATION_SCHEMA",
    "U2AuthorizationRefusal",
    "U2FrozenIdentityMismatch",
    "U2LoaderRefusal",
    "U2UndocumentedValue",
    "check_frozen_files",
    "check_individual_values",
    "check_layouts_against_setup",
    "check_frame_environment",
    "check_preregistration_evidence",
    "check_source_hashes",
    "check_structural_pass_authorization",
    "family_record_specs",
    "files_bundle_sha256",
    "individual_specs",
    "load_u2_inputs",
    "preregistration_evidence",
    "preregistration_evidence_sha256",
    "read_family_records",
    "read_preregistration_evidence",
    "required_entries",
    "source_preflight",
    "structural_pass_authorization",
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

#: The pre-registration evidence record (section 14 frozen identities).
PREREGISTRATION_SCHEMA = (
    "populace_dynamics.track_u2_preregistration_evidence.v2"
)
#: Where the committed record lives once the section 20 step-4 pass has
#: written it (``scripts/track_u2_structure.py``) and it is reviewed and
#: committed; the registered run refuses while it is absent.
PREREGISTRATION_EVIDENCE_PATH = (
    identity.ROOT / "docs" / "design" / "u2_preregistration_evidence.json"
)
_EVIDENCE_KEYS: tuple[str, ...] = (
    "schema_version",
    "target_id",
    "specification",
    "registries_sha256",
    "cited_sources_sha256",
    "psid_files_sha256",
    "psid_files_bundle_sha256",
    "input_frames_sha256",
    "frame_environment",
)
#: The keys of the record's frame environment (``cohort.frame_environment``).
_ENVIRONMENT_KEYS = ("future_infer_string", "pandas_version")
_HEX64 = re.compile(r"[0-9a-f]{64}")
#: A chief-of-staff decision id: ``d`` and its number (e.g. ``d745``).
_DECISION_ID = re.compile(r"d[1-9][0-9]*")
_HEX40 = re.compile(r"[0-9a-f]{40}")
_UTC_SECONDS = "%Y-%m-%dT%H:%M:%SZ"
#: The fields of a structural-pass authorization record.
_AUTHORIZATION_KEYS: tuple[str, ...] = (
    "decision",
    "git_head",
    "recorded_at_utc",
)
_UNAUTHORIZED = (
    "the section 20 step-4 structural pass reads real PSID records, so it "
    "needs Max's authorization, recorded as a chief-of-staff decision; "
    "name that decision with --authorized-by <decision id> (e.g. d1234). "
    "The flag only records the authorization; it does not grant one"
)


class U2LoaderRefusal(sources.U2SourceRefusal):
    """The U2 loader refuses before reading (or on changed sources)."""


class U2UndocumentedValue(U2LoaderRefusal):
    """An individual-file value lies outside its registry entry's
    documented codes or range: it refuses, never maps to ``na`` or falls
    back (section 14)."""


class U2FrozenIdentityMismatch(U2LoaderRefusal):
    """A PSID file, the read file set or the frame digest differs from the
    frozen pre-registration evidence (section 14)."""


class U2AuthorizationRefusal(U2LoaderRefusal):
    """An unfrozen load (the section 20 step-4 pass) without Max's
    recorded authorization: it refuses before any PSID path is
    resolved."""


def structural_pass_authorization(
    decision: str | None, *, git_head: str
) -> dict[str, str]:
    """The authorization record of a section 20 step-4 pass, or refuse.

    The pass reads real PSID records, so it needs Max's authorization,
    recorded as a chief-of-staff decision.  ``decision`` names that
    decision (the structural scripts' ``--authorized-by``); the record
    holds it, the git head the pass runs at and the UTC time it was
    recorded.  Naming a decision records the authorization; it does not
    grant one, and nothing here reads the decision log.  Without a
    decision id this refuses (:class:`U2AuthorizationRefusal`).
    """

    return check_structural_pass_authorization(
        {
            "decision": decision,
            "git_head": git_head,
            "recorded_at_utc": datetime.datetime.now(
                datetime.timezone.utc
            ).strftime(_UTC_SECONDS),
        }
    )


def check_structural_pass_authorization(record: Any) -> dict[str, str]:
    """Return ``record`` checked, or refuse: exactly a decision id, the
    full git head and a UTC timestamp (``None`` refuses)."""

    if not isinstance(record, Mapping) or set(record) != set(
        _AUTHORIZATION_KEYS
    ):
        raise U2AuthorizationRefusal(_UNAUTHORIZED)
    decision = record["decision"]
    if not isinstance(decision, str) or not _DECISION_ID.fullmatch(decision):
        raise U2AuthorizationRefusal(f"{_UNAUTHORIZED} (got {decision!r})")
    head = record["git_head"]
    if not isinstance(head, str) or not _HEX40.fullmatch(head):
        raise U2AuthorizationRefusal(
            "an authorization record names the full git head the pass "
            f"runs at (got {head!r})"
        )
    stamp = record["recorded_at_utc"]
    try:
        datetime.datetime.strptime(stamp, _UTC_SECONDS)
    except (TypeError, ValueError):
        raise U2AuthorizationRefusal(
            "an authorization record holds the UTC time it was recorded "
            f"as YYYY-MM-DDTHH:MM:SSZ (got {stamp!r})"
        ) from None
    return {key: record[key] for key in _AUTHORIZATION_KEYS}


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


def load_u2_inputs(
    *,
    data_dir: Path | None = None,
    evidence: Mapping[str, Any] | None = None,
    authorization: Mapping[str, Any] | None = None,
) -> cohort.U2Inputs:
    """Read every U2 input from the staged PSID, or refuse first.

    An unfrozen load (no ``evidence``: the section 20 step-4 pass) reads
    real PSID records with nothing frozen to check them against, so it
    needs ``authorization``, the record of Max's authorization
    (:func:`structural_pass_authorization`); without it the load refuses
    before the source preflight and before any PSID path is resolved
    (:class:`U2AuthorizationRefusal`).  Stage 1 (:func:`source_preflight`)
    then refuses on any registry blocker, before any PSID file is opened;
    since amendment 1c's registry commit it passes at the committed
    registries.

    ``evidence`` is the frozen pre-registration record
    (:func:`check_preregistration_evidence`).  The registered run passes
    it; the section 20 step-4 pass, which writes it, passes nothing.  It
    must be the committed, reviewed record
    (:func:`read_preregistration_evidence`), not just any well-formed
    one: a fabricated record would otherwise stand in for the
    authorization an unfrozen load needs.  An absent or different record
    refuses before any PSID path is resolved.  With it, every frozen file
    is rehashed before any record is parsed (:func:`check_frozen_files`);
    while records are read, opening any file under the PSID directory
    that the record does not freeze refuses before the file is read
    (:func:`_only_frozen_files`); and after reading, the files read and
    the frame digest must equal the frozen ones, or the load refuses
    (:class:`U2FrozenIdentityMismatch`).
    """

    if evidence is None:
        check_structural_pass_authorization(authorization)
        frozen = None
    else:
        frozen = check_preregistration_evidence(evidence)
        if frozen != read_preregistration_evidence():
            raise U2FrozenIdentityMismatch(
                "the evidence passed is not the committed pre-registration "
                f"record ({PREREGISTRATION_EVIDENCE_PATH}): a frozen load "
                "reads PSID records only against the reviewed record the "
                "section 20 step-4 pass wrote"
            )
        check_frame_environment(frozen)
    registries = sources.RegistrySet.committed()
    preflight = source_preflight(registries)
    # Stages 2 and 3 run only once every required route is resolved.
    from populace_dynamics.cohorts import psid2010
    from populace_dynamics.data import family, marriage

    gate = sources.SourceGate(sources.REGISTRY, registries)
    data_root = psid._resolve_data_dir(data_dir)
    source_hashes = check_source_hashes(registries, data_root)
    if frozen is not None:
        if source_hashes != frozen["cited_sources_sha256"]:
            raise U2FrozenIdentityMismatch(
                "the cited setup files and codebooks differ from the frozen "
                "pre-registration evidence: changed source bytes refuse "
                "execution (section 14)"
            )
        check_frozen_files(frozen, data_root)
    guard = (
        contextlib.nullcontext()
        if frozen is None
        else _only_frozen_files(data_root, frozen["psid_files_sha256"])
    )
    with guard, psid2010.record_files_read(data_root) as files:
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
    bundle = files_bundle_sha256(files)
    frames_sha256 = cohort.input_frames_sha256(inputs)
    provenance: dict[str, Any] = {
        "kind": cohort.PSID_FILES,
        "psid_data_dir": str(data_root),
        "psid_files_sha256": dict(files),
        "psid_files_bundle_sha256": bundle,
        "registries": preflight["registries"],
        "cited_sources_sha256": source_hashes,
    }
    seal = {
        "input_frames_sha256": frames_sha256,
        "psid_files_bundle_sha256": bundle,
    }
    if frozen is not None:
        _check_against_frozen(frozen, dict(files), frames_sha256)
        digest = preregistration_evidence_sha256(frozen)
        provenance[cohort.EVIDENCE_KEY] = digest
        seal[cohort.EVIDENCE_KEY] = digest
    inputs = dataclasses.replace(inputs, provenance=provenance)
    object.__setattr__(inputs, "loader_seal", MappingProxyType(seal))
    return inputs


# ===========================================================================
# Frozen identities (section 14)
# ===========================================================================
def files_bundle_sha256(files: Mapping[str, str]) -> str:
    """The loader's digest of ``{relative path: sha256}`` (as U1's)."""

    return hashlib.sha256(
        (json.dumps(dict(files), sort_keys=True) + "\n").encode()
    ).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _hex_map(value: Any, what: str, *, paths: bool) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise U2FrozenIdentityMismatch(f"the evidence's {what} is no mapping")
    out = {}
    for key, digest in value.items():
        if not isinstance(key, str) or not isinstance(digest, str):
            raise U2FrozenIdentityMismatch(
                f"the evidence's {what} holds a non-string entry"
            )
        if not _HEX64.fullmatch(digest):
            raise U2FrozenIdentityMismatch(
                f"the evidence's {what} holds a digest that is not a "
                "lowercase 64-hex SHA-256"
            )
        if paths:
            relative = PurePosixPath(key)
            if (
                relative.is_absolute()
                or ".." in relative.parts
                or str(relative) != key
                or key in ("", ".")
            ):
                raise U2FrozenIdentityMismatch(
                    f"the evidence's {what} names {key!r}, not a path "
                    "relative to the PSID directory"
                )
        out[key] = digest
    return dict(sorted(out.items()))


def _plain_json(value: Any, where: str) -> None:
    """Refuse anything but plain JSON data, by exact type: ``dict`` with
    ``str`` keys, ``list``, ``str``, ``int``, ``float``, ``bool`` or
    ``None``.  A subclass can carry one digest's text (and so its hash)
    while it compares equal to another (review round 3)."""

    kind = type(value)
    if kind is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise U2FrozenIdentityMismatch(
                    f"the evidence record is not plain JSON data: {where} "
                    f"has a {type(key).__qualname__} key"
                )
            _plain_json(item, f"{where}.{key}")
    elif kind is list:
        for index, item in enumerate(value):
            _plain_json(item, f"{where}[{index}]")
    elif kind not in (str, int, float, bool, type(None)):
        raise U2FrozenIdentityMismatch(
            f"the evidence record is not plain JSON data: {where} is a "
            f"{kind.__qualname__}"
        )


def check_preregistration_evidence(record: Any) -> dict[str, Any]:
    """Refuse a pre-registration evidence record that is not U2's, not
    made under this checkout's pinned registries, or not self-consistent;
    return a normalized copy.

    It must hold exactly :data:`_EVIDENCE_KEYS`: the schema, target U2,
    U2's specification id, the registry pins equal to
    :data:`~populace_dynamics.uniform_cut_track_u2.sources.
    REGISTRY_SHA256`, the cited-source hashes, a nonempty map of PSID
    files (paths relative to the PSID directory) to SHA-256, their bundle
    digest (recomputed here), the sealed frame digest and the pandas
    settings it was taken under (``cohort.frame_environment``; schema v2).
    Every value
    below the top-level mapping must be plain JSON data by exact type
    (:func:`_plain_json`; review round 3), as ``json.loads`` builds it.
    """

    if not isinstance(record, Mapping):
        raise U2FrozenIdentityMismatch("the evidence record is no mapping")
    record = dict(record)
    _plain_json(record, "the record")
    if set(record) != set(_EVIDENCE_KEYS):
        raise U2FrozenIdentityMismatch(
            f"the evidence record holds keys {sorted(record)}, not exactly "
            f"{sorted(_EVIDENCE_KEYS)}"
        )
    if record["schema_version"] != PREREGISTRATION_SCHEMA:
        raise U2FrozenIdentityMismatch(
            f"evidence schema {record['schema_version']!r} is not "
            f"{PREREGISTRATION_SCHEMA!r}"
        )
    try:
        identity.check_target(record["target_id"], "the evidence record")
    except identity.U2IdentityError as error:
        raise U2FrozenIdentityMismatch(str(error)) from error
    if record["specification"] != identity.SPECIFICATION_ID:
        raise U2FrozenIdentityMismatch(
            f"the evidence records specification "
            f"{record['specification']!r}, not U2's"
        )
    registries = _hex_map(
        record["registries_sha256"], "registries_sha256", paths=False
    )
    if registries != dict(sorted(sources.REGISTRY_SHA256.items())):
        raise U2FrozenIdentityMismatch(
            "the evidence was recorded under registries other than this "
            "checkout's pinned ones"
        )
    files = _hex_map(
        record["psid_files_sha256"], "psid_files_sha256", paths=True
    )
    if not files:
        raise U2FrozenIdentityMismatch("the evidence freezes no PSID file")
    bundle = record["psid_files_bundle_sha256"]
    if bundle != files_bundle_sha256(files):
        raise U2FrozenIdentityMismatch(
            "the evidence's file bundle digest does not match its file "
            "hashes"
        )
    frames = record["input_frames_sha256"]
    if not isinstance(frames, str) or not _HEX64.fullmatch(frames):
        raise U2FrozenIdentityMismatch(
            "the evidence's input_frames_sha256 is not a 64-hex SHA-256"
        )
    environment = record["frame_environment"]
    if (
        type(environment) is not dict
        or tuple(sorted(environment)) != _ENVIRONMENT_KEYS
        or type(environment["pandas_version"]) is not str
        or not environment["pandas_version"]
        or type(environment["future_infer_string"]) is not bool
    ):
        raise U2FrozenIdentityMismatch(
            "the evidence's frame_environment must be exactly "
            f"{list(_ENVIRONMENT_KEYS)}: a nonempty pandas version string "
            "and a bool"
        )
    return {
        "schema_version": PREREGISTRATION_SCHEMA,
        "target_id": identity.TARGET_ID,
        "specification": identity.SPECIFICATION_ID,
        "registries_sha256": registries,
        "cited_sources_sha256": _hex_map(
            record["cited_sources_sha256"],
            "cited_sources_sha256",
            paths=False,
        ),
        "psid_files_sha256": files,
        "psid_files_bundle_sha256": bundle,
        "input_frames_sha256": frames,
        "frame_environment": {
            "future_infer_string": environment["future_infer_string"],
            "pandas_version": environment["pandas_version"],
        },
    }


def check_frame_environment(frozen: Mapping[str, Any]) -> None:
    """Refuse unless pandas here is as the evidence record froze it.

    The frame digest hashes pandas' dtype names and CSV text
    (``cohort.frame_environment``), so a load or run under another pandas
    version or string inference setting could refuse a legitimate frame
    or digest it differently.  Checked before any PSID path is resolved.
    """

    current = cohort.frame_environment()
    if frozen["frame_environment"] != current:
        raise U2FrozenIdentityMismatch(
            "the pre-registration evidence froze its frame digest under "
            f"pandas {frozen['frame_environment']}, not this environment's "
            f"{current}: the digest hashes pandas' dtype names and CSV text, "
            "so a frozen load or registered run uses the same pandas"
        )


def preregistration_evidence_sha256(record: Mapping[str, Any]) -> str:
    """SHA-256 of the record's canonical JSON (what the binding quotes)."""

    return hashlib.sha256(
        _canonical(check_preregistration_evidence(record))
    ).hexdigest()


def preregistration_evidence(inputs: cohort.U2Inputs) -> dict[str, Any]:
    """The frozen identities of loader-sealed inputs (section 20 step 4).

    Refuses inputs the U2 loader did not seal (a registered run's private
    snapshot included), or whose frames or file hashes changed after
    sealing (``cohort._input_provenance``), or whose
    frames do not rebuild from the text their digest hashes
    (``cohort.rebuilt_input_frames``): a registered run computes only on
    rebuilt frames, so this refusal comes at step 4, before registration.
    The data directory is not recorded: files are keyed relative to it.
    """

    if type(inputs) is not cohort.U2Inputs:
        raise U2LoaderRefusal("evidence is recorded from U2Inputs only")
    provenance = cohort._input_provenance(inputs)
    if provenance["kind"] != cohort.PSID_FILES:
        raise U2LoaderRefusal(
            "pre-registration evidence is recorded only from inputs the U2 "
            f"loader sealed, not {provenance['kind']!r}"
        )
    if provenance.get(cohort.SNAPSHOT_KEY):
        raise U2LoaderRefusal(
            "pre-registration evidence is recorded only from inputs the U2 "
            "loader read, not from a registered run's private snapshot"
        )
    # A registered run computes only on frames rebuilt from the text their
    # digest hashes (cohort._registered_snapshot); refuse here, before the
    # digest is frozen, any frame that would not rebuild (review round 3).
    try:
        _, rebuilt = cohort.rebuilt_input_frames(inputs)
    except cohort.U2CohortError as error:
        raise U2LoaderRefusal(str(error)) from error
    if rebuilt != provenance["input_frames_sha256"]:
        raise U2LoaderRefusal(
            "the inputs' frames rebuild to another digest than the sealed "
            "one: a registered run could not compute on them"
        )
    return check_preregistration_evidence(
        {
            "schema_version": PREREGISTRATION_SCHEMA,
            "target_id": identity.TARGET_ID,
            "specification": identity.SPECIFICATION_ID,
            "registries_sha256": dict(sources.REGISTRY_SHA256),
            "cited_sources_sha256": dict(
                inputs.provenance.get("cited_sources_sha256") or {}
            ),
            "psid_files_sha256": dict(provenance["psid_files_sha256"]),
            "psid_files_bundle_sha256": provenance["psid_files_bundle_sha256"],
            "input_frames_sha256": provenance["input_frames_sha256"],
            "frame_environment": cohort.frame_environment(),
        }
    )


def read_preregistration_evidence(
    path: Path = PREREGISTRATION_EVIDENCE_PATH,
) -> dict[str, Any]:
    """The committed evidence record; refuses while it is absent."""

    if not Path(path).is_file():
        raise U2FrozenIdentityMismatch(
            f"no pre-registration evidence record at {path}: the section "
            "20 step-4 pass has not frozen the PSID file and frame "
            "identities, so a registered run refuses (section 14)"
        )
    try:
        record = json.loads(Path(path).read_text(encoding="utf-8"))
    except ValueError as error:
        raise U2FrozenIdentityMismatch(
            f"the evidence record at {path} is not JSON: {error}"
        ) from error
    return check_preregistration_evidence(record)


def check_frozen_files(
    evidence: Mapping[str, Any], data_root: Path
) -> dict[str, str]:
    """Rehash every frozen file under ``data_root`` before any record is
    parsed; a missing file or one changed byte refuses."""

    frozen = check_preregistration_evidence(evidence)
    root = Path(data_root)
    changed, missing = [], []
    for relative, expected in frozen["psid_files_sha256"].items():
        path = root / relative
        if not path.is_file():
            missing.append(relative)
            continue
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            changed.append(relative)
    if missing or changed:
        raise U2FrozenIdentityMismatch(
            f"{len(changed)} frozen PSID file(s) changed and {len(missing)} "
            f"missing (changed {changed[:5]}, missing {missing[:5]}): "
            "changed source bytes refuse execution (section 14)"
        )
    return dict(frozen["psid_files_sha256"])


#: The PSID directory and frozen files of the frozen load in progress
#: (:func:`_only_frozen_files`), or ``None``.
_FROZEN_OPENS: contextvars.ContextVar[
    tuple[tuple[Path, ...], frozenset[str]] | None
] = contextvars.ContextVar("u2_frozen_opens", default=None)
_FROZEN_HOOK_INSTALLED = False


def _refuse_unfrozen_open(event: str, args: tuple[Any, ...]) -> None:
    """Audit hook: during a frozen load, refuse to open a file under the
    PSID directory that the evidence does not freeze."""

    if event != "open":
        return
    state = _FROZEN_OPENS.get()
    if state is None or not args or isinstance(args[0], int):
        return
    roots, allowed = state
    literal = Path(os.path.abspath(os.fsdecode(args[0])))
    for path in (literal, literal.resolve()):
        for root in roots:
            if path.is_relative_to(root):
                relative = path.relative_to(root).as_posix()
                if relative in allowed:
                    return
                raise U2FrozenIdentityMismatch(
                    f"{relative} is under the PSID directory but not in the "
                    "frozen pre-registration evidence: an unfrozen file "
                    "is never read (section 14)"
                )


@contextlib.contextmanager
def _only_frozen_files(
    data_root: Path, frozen_files: Mapping[str, str]
) -> Iterator[None]:
    """While the block runs, opening any file under ``data_root`` that is
    not in ``frozen_files`` refuses before the file is read (a Python audit
    hook, installed once per process)."""

    global _FROZEN_HOOK_INSTALLED
    if not _FROZEN_HOOK_INSTALLED:
        sys.addaudithook(_refuse_unfrozen_open)
        _FROZEN_HOOK_INSTALLED = True
    literal = Path(os.path.abspath(Path(data_root).expanduser()))
    token = _FROZEN_OPENS.set(
        ((literal, literal.resolve()), frozenset(frozen_files))
    )
    try:
        yield
    finally:
        _FROZEN_OPENS.reset(token)


def _check_against_frozen(
    frozen: Mapping[str, Any], files: Mapping[str, str], frames: str
) -> None:
    """After reading: the files read and the frame digest must be the
    frozen ones (a file read but not frozen, frozen but not read, or
    changed while read refuses; so does a different frame digest)."""

    expected = frozen["psid_files_sha256"]
    if dict(files) != dict(expected):
        unfrozen = sorted(set(files) - set(expected))
        unread = sorted(set(expected) - set(files))
        changed = sorted(
            name
            for name in set(files) & set(expected)
            if files[name] != expected[name]
        )
        raise U2FrozenIdentityMismatch(
            "the PSID files read differ from the frozen pre-registration "
            f"evidence (read but not frozen {unfrozen[:5]}, frozen but not "
            f"read {unread[:5]}, changed {changed[:5]}): section 14"
        )
    if frames != frozen["input_frames_sha256"]:
        raise U2FrozenIdentityMismatch(
            "the loaded input frames' digest differs from the frozen "
            "pre-registration evidence: changed frame digests refuse "
            "execution (section 14)"
        )


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
