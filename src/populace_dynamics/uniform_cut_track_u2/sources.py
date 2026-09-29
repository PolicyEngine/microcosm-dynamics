"""U2 source binding: registries, role rules and fixed-width adapters.

Specification sections 3, 4 and 14.  Milestone 1 recorded every later-wave
variable, route and role as documentary registries
(``data/external/track_u2/*.json``, validated by
:mod:`populace_dynamics.data.u2_source_registry`).  This module consumes
them; it never rebuilds them and never extends a U1 wave registry.

**Pinned registry bytes.**  :data:`REGISTRY_SHA256` pins the eight
committed registry files.  :meth:`RegistrySet.committed` refuses any other
bytes ("changed source bytes ... refuse execution", section 14), so the
maps a registration binds cannot drift after it.

**Two gates.**  A :class:`SourceGate` decides whether a registry entry may
be applied:

* ``registry`` (the only gate a real-data run accepts): an entry applies
  only when its status is RESOLVED, it lists no blocking dependency and
  its action is not a refusal -- :func:`populace_dynamics.data.
  u2_source_registry.require_resolved`'s rule, applied to the pinned
  documents.  Every route still marked TO VERIFY or unresolved refuses
  with :class:`U2SourceRefusal`; nothing falls back to another route.
* ``invented_declared`` (invented data only): applies the *declared*
  interpretation the specification writes down (the section 3 role table
  and the section 15 routes) to every documented layout, so an invented
  dry run can exercise each mapping and role branch.  It records, for
  every entry it applies, the blockers the ``registry`` gate would refuse
  on.  It is not a fallback, and nothing on the real-data path accepts
  it: :func:`.loader.load_u2_inputs` builds its own registry gate; every
  :class:`FieldSpec` carries the gate that made it, and
  :func:`parse_fixed_width` parses declared-gate specs only on records
  the invented writer produced (every unmapped column holds
  :data:`INVENTED_RECORD_FILLER`, :func:`check_invented_records`); and
  :func:`.runner.run_track_u2` refuses to record it for a registered run.
  :class:`FieldSpec` and :class:`DcRoute` are plain value objects, so a
  caller who hand-assembles them with the declared types is not stopped;
  no U2 entry point does so.
  Where the specification declares nothing (code 88's substantive
  routing, the historical combined spouse-retirement crosswalk) it
  refuses too.

The role rules follow the same split in a :class:`RoleContext`, which is
bound to its kind: a ``registry`` context holds exactly the committed
roles registry's rules and an ``invented_declared`` context exactly the
declared table (both read-only), and :mod:`.cohort` accepts the declared
context only on inputs the invented generator sealed.

**What the guards defend.**  They stop relabelling and mixing through
the public API and ordinary mistakes: :class:`RegistrySet`,
:class:`SourceGate` and :class:`RoleContext` are final (no subclass can
override a check), their documents and rules are read-only, a copied or
unpickled registry set is rebuilt through its checks, and the committed
documents are re-verified against the pinned bytes whenever a committed
set is built and again in the loader's source preflight.  Python cannot
stop deliberate tampering with private state (``object.__setattr__``,
``dict.__setitem__`` on a frozen document, replacing module functions);
the registered path builds every object it uses itself and rechecks the
pinned identities before any PSID record is read.

**Role rules** (section 3 relationship-code amendment):

====  ==============================  ==============  ===================
Code  Income role and spouse slot     Annuity life    Marital resolution
====  ==============================  ==============  ===================
10    head / reference person         head            (is the head)
20    spouse slot, either sex         legal spouse    yes
22    spouse slot (cohabitor)         no              no
88    TO VERIFY: refuses (no declared substantive rule; birth support only)
90    OFUM (not the spouse slot)      legal spouse    yes
92    OFUM, 2017-2023 only            no              never
====  ==============================  ==============  ===================

This is the section 3 table (``u2-draft-3``'s, which governs while
section 16a's amendments are proposed).  The committed roles registry
resolves the same rule for 2013-2017 code 90 and 2017 code 92
(adjudication disposition D) and refuses 2015 code 20 and 2019-2023
codes 90 and 92 (disposition F); the registry gate follows the
registry.

Any other in-family code keeps the inherited OFUM income role with no
spouse status.  Legacy identifiers ``wife``, ``wife_present`` and
``head_wife`` name the spouse *income slot*, not a sex (section 3).

**Adapters.**  :func:`field_specs` turns registry entries into fixed-width
field specifications (one-based inclusive positions, widths, decimals and
the documented sign domain); :func:`parse_fixed_width` reads records with
them and :func:`encode_fixed_width` writes invented records in the same
layout (tests and the invented dry run).  :func:`dc_route` builds the
employer-DC route of a wave from the pension registry's route entries
(registry gate) or from the section 15 declared route (invented only),
and :func:`employer_dc_balances` applies it.

Nothing here opens a survey record: the adapters parse the lines they are
given, and :mod:`.loader` decides whether any record may be read.
"""

from __future__ import annotations

import functools
import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.data import u2_source_registry as registry

__all__ = [
    "ADMINISTRATIVE_BIRTH_SUPPORT_CODES",
    "DECLARED",
    "DECLARED_DC_ROUTE_TYPES",
    "GATES",
    "INCOME_CONCEPTS",
    "INVENTED_DECLARED",
    "INVENTED_RECORD_FILLER",
    "OFUM_RULE",
    "REGISTRY",
    "REGISTRY_SHA256",
    "RELATIONSHIP_CODES",
    "ROLE_CONTEXT_KINDS",
    "SUPPORT_WAVES",
    "WEALTH_CONCEPTS",
    "DC_BALANCE_COLUMNS",
    "DC_CODE_DOMAINS",
    "DcRoute",
    "FieldSpec",
    "RegistrySet",
    "RoleContext",
    "RoleRule",
    "SourceGate",
    "U2RoleRefusal",
    "U2SourceRefusal",
    "blockers",
    "check_invented_records",
    "check_overlaps",
    "dc_route",
    "decode_income",
    "declared_role_rules",
    "employer_dc_balances",
    "encode_fixed_width",
    "field_specs",
    "income_identity",
    "income_identity_counts",
    "pension_field_specs",
    "registry_status_summary",
    "parse_fixed_width",
    "wealth1_identity",
    "wealth1_identity_counts",
]

#: The common support-wave set (section 3; milestone 1's registry waves).
SUPPORT_WAVES: tuple[int, ...] = registry.U2_SOURCE_WAVES
#: The relationship codes section 3 amends and tests.
RELATIONSHIP_CODES: tuple[int, ...] = (10, 20, 22, 88, 90, 92)
#: The inherited administrative birth-support selection (section 3,
#: "Annuitant ages": codes 10, 20, 22, 88 and 90; code 92 is not added).
ADMINISTRATIVE_BIRTH_SUPPORT_CODES: tuple[int, ...] = (10, 20, 22, 88, 90)
#: The gate kinds and the role-context kinds (the same two names).
REGISTRY = "registry"
INVENTED_DECLARED = "invented_declared"
GATES: tuple[str, ...] = (REGISTRY, INVENTED_DECLARED)
ROLE_CONTEXT_KINDS = GATES
DECLARED = INVENTED_DECLARED

#: SHA-256 of the committed milestone-1 registries as adjudicated (commit
#: 883ea48: 0eae214 applied the independent source adjudication).  A
#: registry change after a ruling is its own reviewed commit and moves
#: these pins in the same commit (section 16a, "Registry effect").
REGISTRY_SHA256: dict[str, str] = {
    "income": (
        "6e3034f35b5d8f614a2f05addae90441052141a85483bb8ee128c0b6ae6ac910"
    ),
    "wealth": (
        "3a22247849ea2eccbef6e522c0d74c901beb90195f92fd2e7b23b123fab6b816"
    ),
    "individual": (
        "4eab8e0abc69668c287310931baa049b8546d3f3e265a106f1b945b948c7649e"
    ),
    "pension": (
        "49b4bdad682b8defa4fc628257b366bab46087baacea82e60b57657c99392978"
    ),
    "roles": (
        "de76550e3502173d6456f2ff00856ba69ca20a1bd9c27e2b6fd50cbb0c534895"
    ),
    "support": (
        "5102825d8555e1e8648dfafbd4e6c72eef78d09e453a6d25279ec3b9298d5109"
    ),
    "weights": (
        "0413a7f425f31bdbb83ed71612ba1d8eccf4be4d62e9caa6ef91b95d3e11b10f"
    ),
    "design": (
        "56181372d412811af6d06f5c0d8d1e071049f7fb73c34bd394aaff8f5e0c2fd6"
    ),
}

#: The family-file income concepts the U2 income rows need (the union
#: over the ten rows; section 4).  ``wife_age`` gives the spouse-slot
#: presence flag (not 0: "no Spouse/Partner in FU"), which rows U3 (the
#: couple convention for new enrollment) and U4 (the unit size) read.
INCOME_CONCEPTS: tuple[str, ...] = (
    "interview",
    "fu_size",
    "n_children",
    "wife_age",
    "total_family_income",
    "hw_taxable",
    "hw_transfer",
    "ofum_taxable",
    "ofum_transfer",
    "head_ss",
    "wife_ss",
    "ofum_ss",
    "head_ssi",
    "wife_ssi",
    "ofum_ssi",
    "head_rent",
    "head_dividends",
    "head_interest",
    "head_trusts",
    "head_business_asset",
    "wife_rent",
    "wife_dividends",
    "wife_interest",
    "wife_trusts",
    "wife_business_asset",
    "ofum_asset",
    "head_annuities",
    "head_iras",
    "head_farm",
    "head_labor",
    "wife_labor",
    "head_business_labor",
    "wife_business_labor",
    "head_tanf",
    "wife_tanf",
    "head_other_welfare",
    "wife_other_welfare",
    "census_needs_standard",
    "head_ss_acc",
    "wife_ss_acc",
    "ofum_ss_acc",
    "head_ssi_acc",
    "wife_ssi_acc",
    "ofum_ssi_acc",
)
#: The wealth concepts read directly; each wave's WEALTH1 identity terms
#: are added by :func:`wealth1_identity` from the registry.
WEALTH_CONCEPTS: tuple[str, ...] = (
    "wealth1",
    "wealth1_acc",
    "vehicles",
    "home_equity",
)
#: Declared previous-plan account-item types (section 15
#: ``employer_dc.previous_routes.account_items``: account, formula, DK) in
#: the 2011-and-later plan-type codes every U2 wave uses (5, 1, 8).
DECLARED_DC_ROUTE_TYPES: dict[str, tuple[int, ...]] = {
    "current_account": (5, 7),
    "previous_both": (7,),
    "previous_account_items": (5, 1, 8),
}
_COUNTED_DISPOSITION = 3
_EXCLUDED_IRA_DISPOSITION = 2
_DC_PERSONS = ("head", "wife")
_DC_PLANS = (1, 2)
_AGE_ACTUAL = (14, 120)
_AGE_NA = 999
_NO_SPOUSE = 0
_SEX_CODES = {1: "male", 2: "female"}
_INCOME_ACC_RANGE = (0, 9)
_WEALTH_ACC_CODES = (0, 1)
_INTERVIEW_MAX = 99_999
#: The character every column an invented fixed-width record leaves
#: unmapped holds (:func:`encode_fixed_width` with this filler).  A
#: declared-gate parse (:func:`check_invented_records`) accepts a record
#: only when every unmapped column holds it, so records written any other
#: way -- a survey file's included, whatever its unmapped columns hold --
#: are refused unless they were deliberately rewritten in this form.
INVENTED_RECORD_FILLER = "~"


class U2SourceRefusal(registry.SourceAdjudicationError):
    """A route U2 needs is unresolved, blocked or not declared (sec. 14)."""


class U2RoleRefusal(U2SourceRefusal):
    """A relationship code's role is TO VERIFY or has no declared rule."""


# ===========================================================================
# Registries
# ===========================================================================
def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


@functools.cache
def _committed_document(name: str, digest: str) -> str:
    """The committed registry text (cached per name and pinned digest)."""

    path = registry.REGISTRY_DIRECTORY / f"{name}.json"
    raw = path.read_bytes()
    observed = _sha256(raw)
    if observed != digest:
        raise U2SourceRefusal(
            f"registry {name}: {path} sha256 {observed} != pinned {digest}; "
            "changed source bytes refuse execution (section 14)"
        )
    document = json.loads(raw)
    registry.validate_registry(document, expected_name=name)
    return raw.decode("utf-8")


def _canonical_sha256(document: Mapping[str, Any]) -> str:
    return _sha256(json.dumps(document, sort_keys=True).encode("utf-8"))


def _final(cls: type) -> None:
    raise TypeError(
        f"{cls.__mro__[1].__name__} is final: a subclass could override "
        "the checks that bind it (section 14 refusals)"
    )


class FrozenDocument(dict):
    """A read-only JSON object (a ``dict`` for ``json`` and ``isinstance``).

    Registry documents are frozen when a :class:`RegistrySet` is built
    (objects become ``FrozenDocument``, arrays tuples), so an entry a
    gate has checked cannot be edited in place afterwards.  A deep copy
    is an ordinary, mutable ``dict`` -- and a changed copy can no longer
    be labelled ``committed``.
    """

    def _refuse(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError(
            "U2 registry documents are read-only once bound to a registry "
            "set; deep-copy one to edit it (a changed copy cannot be "
            "labelled committed)"
        )

    __setitem__ = __delitem__ = _refuse
    clear = pop = popitem = setdefault = update = _refuse
    __ior__ = _refuse

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if len(self):
            self._refuse()
        super().__init__(*args, **kwargs)

    def __deepcopy__(self, memo: dict[int, Any]) -> dict[str, Any]:
        return {key: _thaw(value, memo) for key, value in self.items()}

    def __copy__(self) -> dict[str, Any]:
        return dict(self)

    def __reduce__(self) -> tuple[Any, ...]:
        return (dict, (dict(self),))


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return FrozenDocument(
            {key: _freeze(item) for key, item in value.items()}
        )
    if isinstance(value, list | tuple):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any, memo: dict[int, Any] | None = None) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item, memo) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_thaw(item, memo) for item in value]
    return value


@functools.cache
def _committed_frozen(name: str) -> FrozenDocument:
    """The pinned committed document, validated and frozen (read once)."""

    return _freeze(
        json.loads(_committed_document(name, REGISTRY_SHA256[name]))
    )


@functools.cache
def _committed_canonical_sha256(name: str) -> str:
    """The canonical-JSON digest of the pinned committed document, from
    a fresh parse of the pinned bytes (never from a shared object)."""

    return _canonical_sha256(
        json.loads(_committed_document(name, REGISTRY_SHA256[name]))
    )


@dataclass(frozen=True)
class RegistrySet:
    """The eight validated registry documents and their SHA-256.

    ``kind`` is ``committed`` (the pinned milestone-1 files) or
    ``invented`` (test documents in the same schema, never accepted by a
    real-data run).  ``committed`` is a binding, not a label: such a set
    must hold the pinned SHA-256s and documents equal to the pinned
    files' contents, and every set's documents are frozen
    (:class:`FrozenDocument`) when it is built, so neither hand-built
    documents nor later in-place edits can pass the registry gate.
    """

    documents: Mapping[str, Mapping[str, Any]]
    sha256: Mapping[str, str]
    kind: str

    __init_subclass__ = classmethod(_final)

    def __post_init__(self) -> None:
        if self.kind not in ("committed", "invented"):
            raise ValueError("registry set kind is committed or invented")
        if set(self.documents) != set(registry.REGISTRY_NAMES):
            raise ValueError(
                f"a registry set holds exactly {registry.REGISTRY_NAMES}"
            )
        if self.kind == "committed":
            self._verify_committed(self.documents, self.sha256)
        object.__setattr__(
            self,
            "documents",
            FrozenDocument(
                {
                    name: (
                        document
                        if isinstance(document, FrozenDocument)
                        else _freeze(document)
                    )
                    for name, document in self.documents.items()
                }
            ),
        )
        object.__setattr__(self, "sha256", FrozenDocument(dict(self.sha256)))
        object.__setattr__(
            self,
            "_index",
            {
                name: {entry["id"]: entry for entry in doc["entries"]}
                for name, doc in self.documents.items()
            },
        )

    @staticmethod
    def _verify_committed(
        documents: Mapping[str, Any], sha256: Mapping[str, str]
    ) -> None:
        changed = [
            name
            for name in registry.REGISTRY_NAMES
            if sha256.get(name) != REGISTRY_SHA256[name]
            or _canonical_sha256(documents[name])
            != _committed_canonical_sha256(name)
        ]
        if changed:
            raise U2SourceRefusal(
                f"registries {changed} are labelled committed but are not "
                "the pinned milestone-1 files (section 14: changed source "
                "bytes refuse execution)"
            )

    def verify(self) -> RegistrySet:
        """Recheck a committed set against the pinned bytes (again)."""

        if self.kind == "committed":
            self._verify_committed(self.documents, self.sha256)
        return self

    def __copy__(self) -> RegistrySet:
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> RegistrySet:
        return self

    def __reduce__(self) -> tuple[Any, ...]:
        # Unpickling rebuilds the set through its checks.
        return (
            RegistrySet,
            (_thaw(self.documents), dict(self.sha256), self.kind),
        )

    @classmethod
    def committed(cls) -> RegistrySet:
        documents = {name: _committed_frozen(name) for name in REGISTRY_SHA256}
        return cls(documents, dict(REGISTRY_SHA256), "committed")

    @classmethod
    def from_documents(
        cls, documents: Mapping[str, Mapping[str, Any]]
    ) -> RegistrySet:
        """Invented registry documents, schema-validated (tests only)."""

        digests = {}
        thawed = {name: _thaw(doc) for name, doc in documents.items()}
        for name, document in thawed.items():
            registry.validate_registry(document, expected_name=name)
            digests[name] = _canonical_sha256(document)
        return cls(thawed, digests, "invented")

    def entry(self, name: str, entry_id: str) -> Mapping[str, Any]:
        index = self._index.get(name)  # type: ignore[attr-defined]
        if index is None:
            raise U2SourceRefusal(f"unknown U2 registry {name!r}")
        if entry_id not in index:
            raise U2SourceRefusal(f"unknown U2 entry {name}:{entry_id}")
        return index[entry_id]

    def entries(self, name: str) -> list[Mapping[str, Any]]:
        return list(self.documents[name]["entries"])

    def provenance(self) -> dict[str, Any]:
        return {"kind": self.kind, "sha256": dict(sorted(self.sha256.items()))}


def blockers(entry: Mapping[str, Any], name: str) -> list[str]:
    """Why the registry gate refuses ``entry`` (empty when it applies).

    The rule of :func:`populace_dynamics.data.u2_source_registry.
    require_resolved`: status TO VERIFY, any blocking dependency, or an
    action starting with ``refuse``.
    """

    out: list[str] = []
    key = f"{name}:{entry['id']}"
    if entry.get("status") != "RESOLVED":
        out.append(f"{key}: TO VERIFY: {entry.get('question')}")
    for dependency in entry.get("blocking_dependencies", []) or []:
        out.append(f"{key}: blocked by {dependency}")
    action = entry.get("action", "")
    if isinstance(action, str) and action.startswith("refuse"):
        out.append(f"{key}: {action}")
    return out


@dataclass(frozen=True)
class SourceGate:
    """Applies registry entries under ``kind`` and records every use.

    ``registry``: refuse any entry with a blocker.  ``invented_declared``:
    apply the declared interpretation and record what the registry gate
    would refuse (``would_refuse``).  What the specification declares
    nothing for refuses in the callers under both gates (code 88's
    substantive role, documentary crosswalks as inputs).  Frozen, so a
    gate's kind cannot change after the registry check at construction
    (the use records are appended in place).
    """

    kind: str
    registries: RegistrySet
    applied: list[str] = field(default_factory=list)
    would_refuse: dict[str, list[str]] = field(default_factory=dict)

    __init_subclass__ = classmethod(_final)

    def __post_init__(self) -> None:
        if self.kind not in GATES:
            raise ValueError(f"gate kind must be one of {GATES}")
        if type(self.registries) is not RegistrySet:
            raise U2SourceRefusal("a source gate needs a RegistrySet")
        if self.kind == REGISTRY:
            if self.registries.kind != "committed":
                raise U2SourceRefusal(
                    "the registry gate applies only the committed, pinned "
                    "milestone-1 registries"
                )
            self.registries.verify()

    def require(self, name: str, entry_id: str) -> Mapping[str, Any]:
        entry = self.registries.entry(name, entry_id)
        refused = blockers(entry, name)
        key = f"{name}:{entry_id}"
        if refused:
            if self.kind == REGISTRY:
                raise U2SourceRefusal("; ".join(refused))
            self.would_refuse[key] = refused
        self.applied.append(key)
        return entry

    def audit(self) -> dict[str, Any]:
        return {
            "gate": self.kind,
            "registries": self.registries.provenance(),
            "n_entries_applied": len(set(self.applied)),
            "would_refuse_under_registry_gate": {
                key: list(value)
                for key, value in sorted(self.would_refuse.items())
            },
        }


# ===========================================================================
# Role rules (section 3)
# ===========================================================================
@dataclass(frozen=True)
class RoleRule:
    """One relationship code's U2 semantics in one wave."""

    wave: int
    code: int
    present: bool
    income_role: str | None
    spouse_slot: bool
    legal_spouse_annuity: bool
    marital_resolution: bool
    administrative_birth_support: bool
    refusal: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "wave": self.wave,
            "code": self.code,
            "present": self.present,
            "income_role": self.income_role,
            "spouse_slot": self.spouse_slot,
            "legal_spouse_annuity": self.legal_spouse_annuity,
            "marital_resolution": self.marital_resolution,
            "administrative_birth_support": self.administrative_birth_support,
            "refusal": self.refusal,
        }


#: Any in-family code outside section 3's table: the inherited OFUM income
#: role, no spouse status (U1 ``age67`` else-branch; not amended).
OFUM_RULE = dict(
    present=True,
    income_role="ofum",
    spouse_slot=False,
    legal_spouse_annuity=False,
    marital_resolution=False,
    administrative_birth_support=False,
)
_CODE_88_REFUSAL = (
    "code 88 (first-year cohabitor): section 3 verifies its label and "
    "keeps it in the inherited administrative birth-support selection; "
    "any income slot, annuity or marital rule remains TO VERIFY and none "
    "is declared, so an observation whose family holds one refuses"
)


def declared_role_rules() -> dict[tuple[int, int], RoleRule]:
    """The section 3 declared rules for codes 10-92 in every support wave."""

    out: dict[tuple[int, int], RoleRule] = {}
    for wave in SUPPORT_WAVES:
        out[(wave, 10)] = RoleRule(
            wave, 10, True, "head", False, False, False, True
        )
        out[(wave, 20)] = RoleRule(
            wave, 20, True, "wife", True, True, True, True
        )
        out[(wave, 22)] = RoleRule(
            wave, 22, True, "wife", True, False, False, True
        )
        out[(wave, 88)] = RoleRule(
            wave, 88, True, None, False, False, False, True, _CODE_88_REFUSAL
        )
        out[(wave, 90)] = RoleRule(
            wave, 90, True, "ofum", False, True, True, True
        )
        out[(wave, 92)] = (
            RoleRule(wave, 92, True, "ofum", False, False, False, False)
            if wave >= 2017
            else RoleRule(
                wave,
                92,
                False,
                None,
                False,
                False,
                False,
                False,
                f"code 92 does not exist in {wave} (section 3)",
            )
        )
    return out


def _registry_role_rules(
    registries: RegistrySet,
) -> dict[tuple[int, int], RoleRule]:
    out: dict[tuple[int, int], RoleRule] = {}
    declared = declared_role_rules()
    for entry in registries.entries("roles"):
        wave, code = int(entry["wave"]), int(entry["code"])
        refused = blockers(entry, "roles")
        base = declared[(wave, code)]
        if not entry["present"]:
            refusal = f"roles:{entry['id']}: code {code} absent in {wave}"
            out[(wave, code)] = RoleRule(
                wave, code, False, None, False, False, False, False, refusal
            )
            continue
        role = entry.get("income_role")
        income_role = {"spouse": "wife"}.get(role, role)
        out[(wave, code)] = RoleRule(
            wave,
            code,
            True,
            income_role if not refused else base.income_role,
            bool(entry.get("spouse_slot", False)),
            bool(entry["legal_spouse_annuity"]),
            bool(entry["marital_resolution"]),
            bool(entry["administrative_birth_support"]),
            "; ".join(refused) if refused else None,
        )
    return out


@functools.cache
def _committed_role_rules() -> Mapping[tuple[int, int], RoleRule]:
    """The committed roles registry's rules (pinned bytes; read once)."""

    return MappingProxyType(_registry_role_rules(RegistrySet.committed()))


@dataclass(frozen=True)
class RoleContext:
    """The role rules a U2 build applies, and whether it may run on data.

    ``registry``: the committed roles registry; any code the loader's
    ``require_resolved`` refuses, refuses here (at commit 883ea48: code
    88 in every wave, TO VERIFY; 2015 code 20 and 2019-2023 codes 90
    and 92, adjudication disposition F; code 92's absence in 2013 and
    2015).  ``invented_declared``: the section 3 declared rules (code 88
    still refuses); accepted only with invented inputs.

    The kind is a binding, not a label: construction refuses rules other
    than the kind's own (the committed registry's or the declared
    table), and the rules are held read-only.
    """

    kind: str
    rules: Mapping[tuple[int, int], RoleRule]

    __init_subclass__ = classmethod(_final)

    def __post_init__(self) -> None:
        if self.kind not in ROLE_CONTEXT_KINDS:
            raise ValueError(
                f"role context kind must be one of {ROLE_CONTEXT_KINDS}"
            )
        expected = (
            _committed_role_rules()
            if self.kind == REGISTRY
            else declared_role_rules()
        )
        rules = dict(self.rules)
        if rules != dict(expected):
            differ = sorted(
                key
                for key in set(rules) | set(expected)
                if rules.get(key) != expected.get(key)
            )
            source = (
                "the committed roles registry"
                if self.kind == REGISTRY
                else "the section 3 declared table"
            )
            raise U2SourceRefusal(
                f"a {self.kind!r} role context holds rules other than "
                f"{source}'s (first differing (wave, code): {differ[:3]})"
            )
        object.__setattr__(self, "rules", MappingProxyType(rules))

    @classmethod
    def declared(cls) -> RoleContext:
        return cls(INVENTED_DECLARED, declared_role_rules())

    @classmethod
    def from_registry(
        cls, registries: RegistrySet | None = None
    ) -> RoleContext:
        registries = (
            RegistrySet.committed() if registries is None else (registries)
        )
        if registries.kind != "committed":
            raise U2SourceRefusal(
                "a registry role context reads only the committed roles "
                "registry"
            )
        return cls(REGISTRY, _registry_role_rules(registries))

    def rule(self, wave: int, code: int) -> RoleRule:
        """The rule of ``code`` in ``wave``; refused rules raise."""

        key = (int(wave), int(code))
        if key not in self.rules:
            if int(code) in RELATIONSHIP_CODES:
                raise U2RoleRefusal(f"no rule for code {code} in {wave}")
            return RoleRule(int(wave), int(code), **OFUM_RULE)
        rule = self.rules[key]
        if rule.refusal:
            raise U2RoleRefusal(
                f"wave {wave}, relationship code {code}: {rule.refusal}"
            )
        return rule

    def birth_support(self, wave: int, code: int) -> bool:
        """Whether ``code`` is in the administrative birth-support set.

        Support is administrative only (section 3): it confers no
        legal-spouse status, and it holds whether or not the code's
        substantive routing is resolved.
        """

        return int(code) in ADMINISTRATIVE_BIRTH_SUPPORT_CODES

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "rules": [
                rule.as_dict() for _, rule in sorted(self.rules.items())
            ],
        }


# ===========================================================================
# Fixed-width adapters
# ===========================================================================
@dataclass(frozen=True)
class FieldSpec:
    """One fixed-width field: one-based inclusive ``start``-``end``."""

    concept: str
    variable: str
    start: int
    end: int
    width: int
    decimals: int
    negative_allowed: bool
    kind: str
    registry_id: str
    #: The gate that applied the registry entry: specs made under the
    #: invented declared gate parse invented records only.
    gate: str = REGISTRY

    def __post_init__(self) -> None:
        if self.gate not in GATES:
            raise ValueError(f"{self.registry_id}: unknown gate {self.gate}")
        if self.start < 1 or self.end < self.start:
            raise ValueError(f"{self.registry_id}: invalid positions")
        if self.width != self.end - self.start + 1:
            raise ValueError(f"{self.registry_id}: inconsistent width")
        if self.decimals != 0:
            raise U2SourceRefusal(
                f"{self.registry_id}: {self.decimals} implied decimals; "
                "U2 reads whole-dollar and code fields only"
            )


def _kind(concept: str, name: str) -> str:
    """The decoding domain of an income or wealth concept."""

    if concept.endswith("_acc"):
        return "wealth_accuracy" if name == "wealth" else "income_accuracy"
    return {
        "interview": "interview",
        "head_age": "age",
        "wife_age": "age",
        "head_sex": "sex",
        "wife_sex": "sex",
        "fu_size": "fu_size",
        "n_children": "n_children",
        "census_needs_standard": "needs",
    }.get(concept, "amount")


def field_specs(
    name: str,
    wave: int,
    concepts: Sequence[str],
    gate: SourceGate,
) -> list[FieldSpec]:
    """Fixed-width specs of ``concepts`` from registry ``name`` (income or
    wealth), each entry passed through ``gate``."""

    if name not in ("income", "wealth"):
        raise ValueError("field_specs reads the income or wealth registry")
    specs = []
    for concept in concepts:
        entry_id = f"{name}.{wave}.{concept}"
        entry = gate.require(name, entry_id)
        if entry.get("kind", "variable") != "variable":
            raise U2SourceRefusal(
                f"{name}:{entry_id} is a {entry.get('kind')}: documentary "
                "only, not an executable input (section 4)"
            )
        specs.append(
            FieldSpec(
                concept=concept,
                variable=entry["variable"],
                start=int(entry["position_start"]),
                end=int(entry["position_end"]),
                width=int(entry["width"]),
                decimals=int(entry["decimals"]),
                negative_allowed=bool(entry["negative_domain_documented"]),
                kind=_kind(concept, name),
                registry_id=f"{name}:{entry_id}",
                gate=gate.kind,
            )
        )
    check_overlaps(specs)
    return specs


def pension_field_specs(wave: int, gate: SourceGate) -> list[FieldSpec]:
    """Fixed-width specs of the employer-DC items (row U7)."""

    specs = []
    for person in _DC_PERSONS:
        names = [f"{person}_current_type", f"{person}_current_amount"]
        for plan in _DC_PLANS:
            names += [
                f"{person}_prev{plan}_type",
                f"{person}_prev{plan}_combo_disposition",
                f"{person}_prev{plan}_combo_amount",
                f"{person}_prev{plan}_dc_disposition",
                f"{person}_prev{plan}_dc_amount",
            ]
        for concept in names:
            entry = gate.require("pension", f"{wave}.{concept}")
            position = entry["position"]
            specs.append(
                FieldSpec(
                    concept=concept,
                    variable=entry["variable"],
                    start=int(position["start"]),
                    end=int(position["end"]),
                    width=int(position["width"]),
                    decimals=0,
                    negative_allowed=False,
                    kind=_dc_kind(concept),
                    registry_id=f"pension:{wave}.{concept}",
                    gate=gate.kind,
                )
            )
    check_overlaps(specs)
    return specs


#: The employer-DC code domains of the 2011-and-later instruments every
#: U2 wave uses: current plan type (P16/P86: 0 Inap., 1 formula, 5
#: account, 7 both, 8 DK, 9 NA -- the pension registry's current-job
#: accepted and rejected types), previous plan type (P46/P116, the same
#: codes) and disposition (P48/P64: 0 Inap., 1 transferred, 2 rolled over
#: into an IRA, 3 left to accumulate, 4 converted to an annuity, 7 other,
#: 8 DK, 9 NA).
DC_CODE_DOMAINS: dict[str, frozenset[int]] = {
    "current_type": frozenset({0, 1, 5, 7, 8, 9}),
    "previous_type": frozenset({0, 1, 5, 7, 8, 9}),
    "disposition": frozenset({0, 1, 2, 3, 4, 7, 8, 9}),
}


def _dc_kind(concept: str) -> str:
    if concept.endswith("_amount"):
        return "dc_amount"
    if concept.endswith("_current_type"):
        return "current_type"
    if concept.endswith("_type"):
        return "previous_type"
    return "disposition"


def check_overlaps(specs: Sequence[FieldSpec]) -> None:
    ordered = sorted(specs, key=lambda spec: spec.start)
    for left, right in zip(ordered, ordered[1:], strict=False):
        if right.start <= left.end:
            raise U2SourceRefusal(
                f"{left.registry_id} and {right.registry_id} overlap"
            )
    concepts = [spec.concept for spec in specs]
    if len(concepts) != len(set(concepts)):
        raise U2SourceRefusal("a concept is mapped twice")


def _field_value(line: str, spec: FieldSpec, record: int) -> int:
    text = line[spec.start - 1 : spec.end]
    if len(text) != spec.width:
        raise U2SourceRefusal(
            f"record {record}: {spec.registry_id} is truncated "
            f"({len(text)} of {spec.width} columns)"
        )
    stripped = text.strip()
    if not stripped:
        raise U2SourceRefusal(
            f"record {record}: {spec.registry_id} is blank; the codebooks "
            "assign every missing value"
        )
    try:
        return int(stripped)
    except ValueError as error:
        raise U2SourceRefusal(
            f"record {record}: {spec.registry_id} is not an integer "
            f"({stripped!r})"
        ) from error


def _check_domain(values: np.ndarray, spec: FieldSpec) -> None:
    kind = spec.kind
    bad: np.ndarray
    if kind == "interview":
        bad = (values < 1) | (values > _INTERVIEW_MAX)
    elif kind == "age":
        low, high = _AGE_ACTUAL
        allowed = (values >= low) & (values <= high) | (values == _AGE_NA)
        if spec.concept == "wife_age":
            allowed |= values == _NO_SPOUSE
        bad = ~allowed
    elif kind == "sex":
        allowed = np.isin(values, list(_SEX_CODES))
        if spec.concept == "wife_sex":
            allowed |= values == _NO_SPOUSE
        bad = ~allowed
    elif kind == "fu_size":
        bad = (values < 1) | (values > 20)
    elif kind == "n_children":
        bad = (values < 0) | (values > 18)
    elif kind == "needs":
        bad = values <= 0
    elif kind == "income_accuracy":
        bad = (values < _INCOME_ACC_RANGE[0]) | (values > _INCOME_ACC_RANGE[1])
    elif kind == "wealth_accuracy":
        bad = ~np.isin(values, list(_WEALTH_ACC_CODES))
    elif kind in ("amount", "dc_amount"):
        bad = (
            values < 0
            if not spec.negative_allowed
            else np.zeros(len(values), dtype=bool)
        )
    elif kind in DC_CODE_DOMAINS:
        bad = ~np.isin(values, sorted(DC_CODE_DOMAINS[kind]))
    else:  # pragma: no cover - every kind is listed above
        raise ValueError(f"unknown field kind {kind}")
    if bad.any():
        first = values[bad][:3].tolist()
        raise U2SourceRefusal(
            f"{spec.registry_id}: {int(bad.sum())} values outside the "
            f"documented domain (first {first}); a negative amount is "
            "accepted only where the codebook documents a loss"
        )


def parse_fixed_width(
    lines: Iterable[str], specs: Sequence[FieldSpec]
) -> pd.DataFrame:
    """Parse fixed-width ``lines`` into one integer column per spec.

    Refuses truncated or blank fields, non-integers, and values outside
    each field's documented domain (a negative amount only where the
    codebook documents a loss; ages 14-120 or 999 NA, and 0 for an absent
    spouse; sex 1 or 2, and 0 for an absent spouse; accuracy codes).
    Amounts and top codes are carried as recorded.  Specs the invented
    declared gate made parse only records the invented writer produced
    (:func:`check_invented_records`).
    """

    records = [line.rstrip("\n") for line in lines]
    if any(spec.gate != REGISTRY for spec in specs):
        check_invented_records(records, specs)
    data = {
        spec.concept: np.asarray(
            [_field_value(line, spec, i) for i, line in enumerate(records)],
            dtype=np.int64,
        )
        for spec in specs
    }
    frame = pd.DataFrame(data, columns=[spec.concept for spec in specs])
    for spec in specs:
        _check_domain(frame[spec.concept].to_numpy(dtype=np.int64), spec)
    if "interview" in frame and frame["interview"].duplicated().any():
        raise U2SourceRefusal("duplicate interview numbers")
    if {"n_children", "fu_size"} <= set(frame.columns) and (
        frame["n_children"] >= frame["fu_size"]
    ).any():
        raise U2SourceRefusal("# CHILDREN IN FU not below # IN FU")
    return frame.astype("int64")


def encode_fixed_width(
    frame: pd.DataFrame, specs: Sequence[FieldSpec], *, filler: str = " "
) -> list[str]:
    """Write ``frame`` as fixed-width lines in ``specs``'s layout.

    For invented records only.  Values are right-aligned; a value wider
    than its field is refused.  Unmapped columns are ``filler`` (the
    invented writer passes :data:`INVENTED_RECORD_FILLER`).
    """

    width = max(spec.end for spec in specs)
    out = []
    for row in frame.itertuples(index=False):
        chars = [filler] * width
        values = row._asdict()
        for spec in specs:
            text = str(int(values[spec.concept]))
            if len(text) > spec.width:
                raise ValueError(
                    f"{spec.registry_id}: {text} is wider than {spec.width}"
                )
            chars[spec.start - 1 : spec.end] = list(text.rjust(spec.width))
        out.append("".join(chars))
    return out


def check_invented_records(
    records: Sequence[str], specs: Sequence[FieldSpec]
) -> int:
    """Refuse records the invented writer did not produce.

    Every column ``specs`` leaves unmapped must hold
    :data:`INVENTED_RECORD_FILLER` and every record must end at the last
    mapped column.  The declared gate reads nothing else.
    """

    width = max(spec.end for spec in specs)
    mapped = {i for spec in specs for i in range(spec.start - 1, spec.end)}
    gaps = [i for i in range(width) if i not in mapped]
    if not gaps:
        raise U2SourceRefusal(
            "the layout maps every column, so invented records cannot be "
            "told from survey records"
        )
    expected = INVENTED_RECORD_FILLER * len(gaps)
    for number, record in enumerate(records):
        if len(record) != width or (
            "".join(record[i] for i in gaps) != expected
        ):
            raise U2SourceRefusal(
                f"record {number}: the invented declared gate reads only "
                "records the U2 invented writer produced (every unmapped "
                f"column {INVENTED_RECORD_FILLER!r}); survey records are "
                "read under the registry gate alone"
            )
    return len(records)


def decode_income(frame: pd.DataFrame) -> pd.DataFrame:
    """Decode parsed income fields as the income rows need them.

    ``wife_present`` is ``wife_age`` not 0 ("no Spouse/Partner in FU"):
    the designated spouse *income slot* is occupied (section 3); an age
    of 999 (DK; NA) still marks the slot occupied.
    """

    out = frame.copy()
    out["wife_present"] = (frame["wife_age"] != _NO_SPOUSE).astype(bool)
    age = frame["wife_age"]
    out["wife_age"] = age.astype("Int64").mask(age.isin([_NO_SPOUSE, _AGE_NA]))
    return out


# ===========================================================================
# Identities
# ===========================================================================
def _terms_by_variable(
    name: str, wave: int, gate: SourceGate
) -> dict[str, str]:
    """``{variable: concept}`` of the wave's variable entries."""

    return {
        entry["variable"]: entry["route"]
        for entry in gate.registries.entries(name)
        if entry["wave"] == wave and "variable" in entry
    }


def income_identity(wave: int, gate: SourceGate) -> tuple[str, ...]:
    """The concepts TOTAL FAMILY INCOME sums (the registry identity)."""

    entry = gate.require("income", f"income.{wave}.total_family_income")
    identity = entry.get("identity") or {}
    if identity.get("operation") != "sum":
        raise U2SourceRefusal(f"income {wave}: no documented sum identity")
    names = _terms_by_variable("income", wave, gate)
    missing = [term for term in identity["terms"] if term not in names]
    if missing:
        raise U2SourceRefusal(f"income {wave}: unmapped terms {missing}")
    return tuple(names[term] for term in identity["terms"])


def income_identity_counts(
    frame: pd.DataFrame, terms: Sequence[str], *, tolerance: int = 10
) -> dict[str, int]:
    """Families whose TOTAL FAMILY INCOME equals its terms' sum (counts)."""

    total = frame[list(terms)].sum(axis=1)
    gap = (frame["total_family_income"] - total).abs()
    return {
        "n_families": int(len(frame)),
        "n_exact": int((gap == 0).sum()),
        "n_within_tolerance": int((gap <= tolerance).sum()),
    }


def wealth1_identity(
    wave: int, gate: SourceGate
) -> dict[str, tuple[str, ...] | str]:
    """The documented WEALTH1 identity of ``wave`` as concept names.

    Seven asset components in 2013-2017 and eight from 2019 (the split of
    checking/savings from CDs, bonds and Treasury bills), each debt once;
    home equity is excluded.  The farm/business and other-real-estate net
    crosswalks are documentary only: using them beside their separately
    documented debts would subtract the debt twice, so they are refused
    as inputs (section 4, "Do not double-subtract").
    """

    entry = gate.require("wealth", f"wealth.{wave}.wealth1")
    identity = entry.get("identity") or {}
    if identity.get("operation") != "sum_assets_minus_sum_debts":
        raise U2SourceRefusal(f"wealth {wave}: no documented identity")
    names = _terms_by_variable("wealth", wave, gate)
    assets = tuple(names[v] for v in identity["assets"])
    debts = tuple(names[v] for v in identity["debts"])
    excluded = names[identity["excluded_home_equity"]]
    if set(assets) & set(debts) or excluded in assets + debts:
        raise U2SourceRefusal(f"wealth {wave}: inconsistent identity")
    for net in ("farm_business", "other_real_estate"):
        if net in assets:
            raise U2SourceRefusal(
                f"wealth {wave}: the {net} crosswalk nets a separately "
                "documented debt; it is not an identity term"
            )
    expected = 7 if wave <= 2017 else 8
    if len(assets) != expected:
        raise U2SourceRefusal(
            f"wealth {wave}: {len(assets)} asset components, section 4 "
            f"documents {expected}"
        )
    return {"assets": assets, "debts": debts, "excluded": excluded}


def wealth1_identity_counts(
    frame: pd.DataFrame, identity: Mapping[str, Any]
) -> dict[str, int]:
    """Families whose WEALTH1 equals assets minus debts (counts only)."""

    value = frame[list(identity["assets"])].sum(axis=1) - frame[
        list(identity["debts"])
    ].sum(axis=1)
    gap = (frame["wealth1"] - value).abs()
    return {"n_families": int(len(frame)), "n_exact": int((gap == 0).sum())}


# ===========================================================================
# Employer DC (row U7)
# ===========================================================================
@dataclass(frozen=True)
class DcRoute:
    """A wave's employer-DC route: which plan types' items count."""

    wave: int
    current_account: tuple[int, ...]
    previous_both: tuple[int, ...]
    previous_account_items: tuple[int, ...]
    counted_disposition: int
    excluded_ira_disposition: int
    source: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "wave": self.wave,
            "current_account": list(self.current_account),
            "previous_both": list(self.previous_both),
            "previous_account_items": list(self.previous_account_items),
            "counted_disposition": self.counted_disposition,
            "excluded_ira_disposition": self.excluded_ira_disposition,
            "source": self.source,
        }


def dc_route(wave: int, gate: SourceGate) -> DcRoute:
    """The employer-DC route of ``wave`` under ``gate``.

    Registry gate: built from the pension registry's route entries
    (current job; previous combined; previous DC-only; the checkpoint's
    formula/unknown route; IRA rollovers; duplicate and off-route rule).
    Any route still TO VERIFY or blocked refuses -- today 2015's
    checkpoint and respondent slots and 2017-2023's inherited-route
    amendment -- and so do disposition codes on which the IRA-rollover,
    previous-combined and previous-DC-only entries disagree.  Invented
    declared gate: the section 15 route (current account or combined
    plan; "both" items of a combined plan; account items of an account,
    formula or DK plan), recording the registry blockers.
    """

    wave = int(wave)
    routes = [
        "current_job",
        "previous_combined",
        "previous_dc_only",
        "formula_unknown_checkpoint",
        "ira_rollovers",
        "duplicate_and_off_route",
        "amounts_brackets_top_codes",
        "respondent_slots",
    ]
    entries = {
        route: gate.require("pension", f"{wave}.route.{route}")
        for route in routes
    }
    if wave >= 2017:
        gate.require("pension", f"{wave}.route.inherited_route_amendment")
    if gate.kind == INVENTED_DECLARED:
        types = DECLARED_DC_ROUTE_TYPES
        return DcRoute(
            wave,
            types["current_account"],
            types["previous_both"],
            types["previous_account_items"],
            _COUNTED_DISPOSITION,
            _EXCLUDED_IRA_DISPOSITION,
            "section_15_declared_route_invented_only",
        )
    rollover = entries["ira_rollovers"]
    combined = entries["previous_combined"]
    dc_only = entries["previous_dc_only"]
    counted = {
        int(rollover["counted_disposition"]),
        int(combined["counted_disposition"]),
        int(dc_only["counted_disposition"]),
    }
    excluded = {
        int(rollover["excluded_disposition"]),
        int(combined["excluded_ira_disposition"]),
        int(dc_only["excluded_ira_disposition"]),
    }
    if len(counted) != 1 or len(excluded) != 1:
        raise U2SourceRefusal(
            f"pension {wave}: the IRA-rollover, previous-combined and "
            "previous-DC-only routes disagree on the disposition codes "
            f"(counted {sorted(counted)}, IRA rollover {sorted(excluded)}); "
            "no route is chosen over another"
        )
    checkpoint = entries["formula_unknown_checkpoint"]
    account = tuple(dc_only["accepted_plan_types"])
    conditional = tuple(
        checkpoint.get("accepted_conditional_types")
        or checkpoint.get("accepted_plan_types")
        or ()
    )
    items = tuple(dict.fromkeys(account + conditional))
    return DcRoute(
        wave,
        tuple(entries["current_job"]["accepted_current_types"]),
        tuple(combined["accepted_plan_types"]),
        items,
        counted.pop(),
        excluded.pop(),
        "pension_registry_routes",
    )


def _amount_codes(width: int) -> dict[str, int]:
    ceiling = 10 ** int(width)
    return {"top": ceiling - 3, "dk": ceiling - 2, "na": ceiling - 1}


def employer_dc_balances(
    raw: pd.DataFrame, route: DcRoute, widths: Mapping[str, int]
) -> pd.DataFrame:
    """Each family's U7 balance under ``route`` (U1's rule, U2 route).

    The same item-by-item rule as :func:`populace_dynamics.data.
    employer_dc.employer_dc_balances`: the current-job amount when the
    plan type has an account; for each previous plan, the amount now when
    the account was left to accumulate, from the "both" items of a
    combined plan and from the account items of the route's account-item
    types; a combined plan's account items are a re-ask and excluded;
    rollovers into an IRA are excluded and counted (WEALTH1 holds IRAs);
    off-route amounts are excluded and counted; DK and refused amounts
    count as zero and are counted; top codes count as recorded.
    ``widths`` maps each amount concept to its field width.
    """

    n = len(raw)
    current = np.zeros(n, dtype=np.int64)
    previous = np.zeros(n, dtype=np.int64)
    items = np.zeros(n, dtype=np.int64)
    unreported = np.zeros(n, dtype=np.int64)
    top = np.zeros(n, dtype=np.int64)
    rolled = np.zeros(n, dtype=np.int64)
    off_route = np.zeros(n, dtype=np.int64)
    duplicates = np.zeros(n, dtype=np.int64)

    def decoded(concept: str) -> tuple[np.ndarray, ...]:
        amount = raw[concept].to_numpy(dtype=np.int64)
        codes = _amount_codes(widths[concept])
        dk = (amount == codes["dk"]) | (amount == codes["na"])
        reported = (amount > 0) & ~dk
        value = np.where(reported, amount, 0).astype(np.int64)
        return amount, value, reported, dk, amount == codes["top"]

    for person in _DC_PERSONS:
        amount, value, reported, dk, topped = decoded(
            f"{person}_current_amount"
        )
        plan_type = raw[f"{person}_current_type"].to_numpy(dtype=np.int64)
        account = np.isin(plan_type, route.current_account)
        current += np.where(account, value, 0)
        items += account & reported
        unreported += account & dk
        top += account & topped
        off_route += ~account & (amount != 0)
        for plan in _DC_PLANS:
            plan_type = raw[f"{person}_prev{plan}_type"].to_numpy(
                dtype=np.int64
            )
            both_plan = np.isin(plan_type, route.previous_both)
            for part in ("combo", "dc"):
                stem = f"{person}_prev{plan}_{part}"
                disposition = raw[f"{stem}_disposition"].to_numpy(
                    dtype=np.int64
                )
                amount, value, reported, dk, topped = decoded(f"{stem}_amount")
                if part == "combo":
                    on_route = both_plan
                else:
                    on_route = (
                        np.isin(plan_type, route.previous_account_items)
                        & ~both_plan
                    )
                left = disposition == route.counted_disposition
                counted = on_route & left
                previous += np.where(counted, value, 0)
                items += counted & reported
                unreported += counted & dk
                top += counted & topped
                rolled += on_route & (
                    disposition == route.excluded_ira_disposition
                )
                if part == "dc":
                    duplicates += both_plan & left & (amount != 0)
                    off_route += ~on_route & ~both_plan & left & (amount != 0)
                else:
                    off_route += ~on_route & left & (amount != 0)
    out = raw.copy()
    for name, values in (
        ("employer_dc", current + previous),
        ("employer_dc_current", current),
        ("employer_dc_previous", previous),
        ("employer_dc_items", items),
        ("employer_dc_unreported", unreported),
        ("employer_dc_top_coded", top),
        ("employer_dc_ira_rollover_items", rolled),
        ("employer_dc_off_route_items", off_route),
        ("employer_dc_duplicate_items", duplicates),
    ):
        out[name] = values
    return out


#: The derived per-family columns :func:`employer_dc_balances` adds.
DC_BALANCE_COLUMNS: tuple[str, ...] = (
    "employer_dc",
    "employer_dc_current",
    "employer_dc_previous",
    "employer_dc_items",
    "employer_dc_unreported",
    "employer_dc_top_coded",
    "employer_dc_ira_rollover_items",
    "employer_dc_off_route_items",
    "employer_dc_duplicate_items",
)


def registry_status_summary(registries: RegistrySet) -> dict[str, Any]:
    """Counts of RESOLVED and blocked entries per registry (no data)."""

    out = {}
    for name in registry.REGISTRY_NAMES:
        entries = registries.entries(name)
        blocked = [e["id"] for e in entries if blockers(e, name)]
        out[name] = {
            "n_entries": len(entries),
            "n_to_verify": sum(e["status"] != "RESOLVED" for e in entries),
            "n_refused_by_registry_gate": len(blocked),
        }
    return out


def registry_path(name: str) -> Path:
    return registry.REGISTRY_DIRECTORY / f"{name}.json"
