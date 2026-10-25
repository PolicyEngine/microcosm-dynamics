"""The held-out data registry and the rules every commit must keep.

``docs/design/track_b_holdout_registry.json`` records the data that Track
B's gates and the open-population lane's gates hold out. The dynamics
coordinator made it the single registry for every lane on 2026-10-21.
This module enforces its rules:

- one schema, ``track_b_holdout_registry.v1``, with every field typed;
- a source vocabulary held here, in :data:`SOURCES`, so that adding a
  source or a family is a reviewed code change. Each source has a family,
  a title, a catalog reference no other source shares, and what its key
  year means. The registry's copy must equal it;
- unit keys ``source:years[:scope...]``, where ``years`` is a year, an
  inclusive year range, or ``undated``. Two keys name a shared unit when
  they have the same source and their years intersect (``undated``
  intersects every year). Scope segments describe the unit and never
  narrow the overlap;
- live entries that share a unit, or whose relation is unresolved, list
  each other in ``disclosed_overlaps``, and every disclosure is symmetric;
- relations the mechanical rule cannot see are reviewed: an entry lists
  every earlier live entry of the same source family that it neither
  shares a unit with nor discloses, with the outcome ``disjoint``, a
  substantive reason and citations. An unresolved relation is disclosed
  instead;
- unique entry ids, which are never removed, reordered or reused;
- histories with legal transitions only. A registration starts as a lone
  ``candidate`` in a commit of its own, so it reaches the base branch
  before its gate freezes, and its scored run's bytes must not yet have
  been committed, at any path, when it is registered. A historical import
  is a gate that scored before the registry existed: it starts as
  ``used``, and its id, gate, unit keys and scored runs must match an
  authorization in :data:`HISTORICAL_IMPORTS`;
- a ``used`` entry cites scored-run artifacts listed in
  :data:`SCORED_RUNS`, which pins each one's gate and the SHA-256 of its
  bytes, read from the committed tree; each citation's identity field
  names the gate in ``gates.yaml`` or in
  :data:`REGISTRATIONS_OUTSIDE_GATES_YAML`;
- entries only grow: against the base registry, between every pair of
  consecutive first-parent commits since it (each snapshot validated
  against its own commit's tree), and between a pull request's own
  commits, an entry's identity and units never change and its lists only
  extend. A pull request's own commits are compared from its fork point,
  and a merge among them that brings in landed history keeps every entry
  of both lines. A newly created registry is admitted against an empty
  one;
- the registry stays incomplete until its completion record, B0.2's
  mechanical exposure inventory, exists.

The overlap rule is deliberately coarse. It catches two gates that read
the same source at the same year, whatever variable or table they use.
It cannot see that two sources share underlying data, or that two
editions of a publication report the same data years. That is what the
family review and disclosures are for, and what reviewers of each
registry change must check.

Each check returns a list of problems; an empty list means the registry
keeps the rules.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import subprocess
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Any

import yaml

SCHEMA = "track_b_holdout_registry.v1"
REGISTRY = "docs/design/track_b_holdout_registry.json"
GATES = "gates.yaml"

#: The source vocabulary. Adding a source is a reviewed code change, and a
#: new id must not be another name for a declared source.
SOURCES: Mapping[str, Mapping[str, str]] = MappingProxyType(
    {
        "psid": {
            "family": "psid",
            "title": (
                "Panel Study of Income Dynamics: family files, cross-year "
                "individual file and supplements"
            ),
            "catalog": (
                "University of Michigan Institute for Social Research: "
                "Panel Study of Income Dynamics"
            ),
            "key_year": (
                "interview wave (collection year); income reference years "
                "are the wave year minus one"
            ),
        },
        "ssa_epuf": {
            "family": "ssa_administrative",
            "title": "SSA Earnings Public-Use File",
            "catalog": (
                "SSA Office of Research, Evaluation, and Statistics: "
                "Earnings Public-Use File"
            ),
            "key_year": (
                "the vintage year in the file's title: the 2006 file holds "
                "earnings through 2006 and was released in August 2011"
            ),
        },
        "ssa_supplement": {
            "family": "ssa_administrative",
            "title": (
                "Annual Statistical Supplement to the Social Security "
                "Bulletin"
            ),
            "catalog": (
                "SSA Office of Research, Evaluation, and Statistics: Annual "
                "Statistical Supplement to the Social Security Bulletin"
            ),
            "key_year": "edition year",
        },
        "ssa_di_asr": {
            "family": "ssa_administrative",
            "title": (
                "Annual Statistical Report on the Social Security "
                "Disability Insurance Program"
            ),
            "catalog": (
                "SSA Office of Research, Evaluation, and Statistics: Annual "
                "Statistical Report on the Social Security Disability "
                "Insurance Program"
            ),
            "key_year": "edition year",
        },
        "census_cps_tables": {
            "family": "us_cross_section",
            "title": "U.S. Census Bureau Current Population Survey tables",
            "catalog": (
                "U.S. Census Bureau: Current Population Survey published "
                "tables"
            ),
            "key_year": "table reference year",
        },
        "populace_us_frame": {
            "family": "us_cross_section",
            "title": "Microcosm US certified frame",
            "catalog": "hf://policyengine/populace-us/populace_us_2024.h5",
            "key_year": "frame vintage",
        },
        "mermin_smith_anchors": {
            "family": "literature",
            "title": (
                "Mermin and Smith published orderings, committed as anchors"
            ),
            "catalog": (
                "gates.yaml gate_w1 holdout_basis: "
                "mermin_smith_committed_orderings"
            ),
            "key_year": "undated",
        },
    }
)
#: Gates registered outside ``gates.yaml`` (Track B's #42 registrations),
#: with every identifier that may name them in scored evidence.
REGISTRATIONS_OUTSIDE_GATES_YAML: Mapping[str, tuple[str, ...]] = (
    MappingProxyType({"B2": ("B2", "6252388925")})
)
#: Each scored-run artifact a ``used`` entry may cite: its gate and the
#: SHA-256 of its committed bytes. A gate's scored run is added here when
#: it scores, as a reviewed code change, so a floor, candidate file or
#: dry run cannot stand in for a score, and a reused path cannot carry
#: another gate's run.
SCORED_RUNS: Mapping[str, tuple[str, str]] = MappingProxyType(
    {
        "runs/gate_m6_candidate1_v1.json": (
            "gate_m6",
            "546a9739f8d1c7d21a91a07eb902c8af9bda92cdaa8f7917f312894f6a861b24",
        ),
        "runs/gate_m6_candidate2_v1.json": (
            "gate_m6",
            "f217b0dc3b17b0a2c2926b1e9299ba2144be4b8a69ac880566d19fd4cd6c2917",
        ),
        "runs/gate_m6_candidate3_v1.json": (
            "gate_m6",
            "caf254925f44b27c1bd1131336055e27fbc311daec00b0050b2f9293a74e82cf",
        ),
        "runs/track_b_b2_score.json": (
            "B2",
            "df82a102a2b4c40c34f0e36b4333dbe7b90d13bfb3658b60b3f6d3f3e2dd8489",
        ),
        "runs/epuf_fill_gate_test_v1.json": (
            "gate_epuf_fill",
            "9fa726be90134546c54148d681209ccf4a33939a7d6e2cfe5c2e384832dace03",
        ),
        "runs/gate_m4_hazard_v1.json": (
            "gate_m4",
            "6493fda8207e743b3b6cbe1c80eb5ab5fb9646aa6f10fad4e77aa8d84c6b889c",
        ),
        "runs/gate_w1_candidate1_v1.json": (
            "gate_w1",
            "01130c512ddba545e11dcf83364387a6c8df307041ac199ce3703cc4a00d6725",
        ),
        "runs/gate_w1_candidate2_v1.json": (
            "gate_w1",
            "3baf097284b793fa4968d9b0b935ec3d16cf2770b16fb1fc1e3fb591ad490f40",
        ),
        "runs/gate_w1_candidate3_v1.json": (
            "gate_w1",
            "b532f2b75d96e876af2e65400439a2f6c832ea45eecf83c1b4431b026ab7e688",
        ),
        "runs/gate_w1_candidate4_v1.json": (
            "gate_w1",
            "ce4f9c9ab0b78bbb4dfe7dcb2a6b34892a80ea74760e0a00c4d60aa35e2d6e65",
        ),
    }
)
#: The historical imports this module authorizes: gates that scored before
#: the registry existed. Each binds one entry id to its gate, its unit keys
#: and its scored runs, so the exception to preregistration covers exactly
#: the exposure reviewed here. B0.2's mechanical inventory adds any import
#: it finds, or a correction to an existing one, as a new authorized entry
#: in a reviewed code change; nothing else can enter as an import.
HISTORICAL_IMPORTS: Mapping[str, Mapping[str, Any]] = MappingProxyType(
    {
        "H001": MappingProxyType(
            {
                "gate": "gate_m6",
                "unit_keys": ("psid:2015-2023:held_out_window",),
                "scored_runs": (
                    "runs/gate_m6_candidate1_v1.json",
                    "runs/gate_m6_candidate2_v1.json",
                    "runs/gate_m6_candidate3_v1.json",
                ),
            }
        ),
        "H002": MappingProxyType(
            {
                "gate": "B2",
                "unit_keys": ("psid:2013:fam2013er", "psid:2015:fam2015er"),
                "scored_runs": ("runs/track_b_b2_score.json",),
            }
        ),
        "H003": MappingProxyType(
            {
                "gate": "gate_epuf_fill",
                "unit_keys": ("ssa_epuf:2006:test_partition",),
                "scored_runs": ("runs/epuf_fill_gate_test_v1.json",),
            }
        ),
        "H004": MappingProxyType(
            {
                "gate": "gate_m4",
                "unit_keys": (
                    "psid:1982:employment_status",
                    "psid:1983:employment_status",
                    "psid:1993-1997:employment_status",
                    "psid:1999-2023:employment_status",
                    "ssa_di_asr:2023",
                ),
                "scored_runs": ("runs/gate_m4_hazard_v1.json",),
            }
        ),
        "H005": MappingProxyType(
            {
                "gate": "gate_w1",
                "unit_keys": (
                    "ssa_supplement:2023:6.b5.1",
                    "ssa_supplement:2023:6.b4",
                    "ssa_supplement:2023:6.b3",
                    "ssa_di_asr:2023:table_19",
                    "census_cps_tables:2023:hh-4",
                    "census_cps_tables:2023:ad-3",
                    "populace_us_frame:2024:certified",
                    "mermin_smith_anchors:undated",
                ),
                "scored_runs": (
                    "runs/gate_w1_candidate1_v1.json",
                    "runs/gate_w1_candidate2_v1.json",
                    "runs/gate_w1_candidate3_v1.json",
                    "runs/gate_w1_candidate4_v1.json",
                ),
            }
        ),
    }
)
STATUSES = ("candidate", "frozen", "used", "withdrawn")
TRANSITIONS = {
    "candidate": frozenset({"frozen", "withdrawn"}),
    "frozen": frozenset({"used", "withdrawn"}),
    "used": frozenset(),
    "withdrawn": frozenset(),
}
#: Each provenance's permitted first statuses.
FIRST_STATUS = {
    "registration": frozenset({"candidate"}),
    "historical_import": frozenset({"used"}),
}
TEXT_FIELDS = ("schema", "title", "purpose", "completion_record")
TOP_LEVEL = (
    *TEXT_FIELDS,
    "rules",
    "status_values",
    "sources",
    "complete",
    "entries",
)
SOURCE_FIELDS = ("family", "title", "catalog", "key_year")
ENTRY_TEXT = ("id", "provenance", "gate", "lane", "source", "status")
ENTRY_LISTS = (
    "gate_identifiers",
    "unit_keys",
    "evidence",
    "scored_evidence",
    "disclosed_overlaps",
    "overlap_review",
    "history",
)
ENTRY_KEYS = (*ENTRY_TEXT, "units", *ENTRY_LISTS)
#: Fields that identify an entry and its units; they never change.
IMMUTABLE = (
    "id",
    "provenance",
    "gate",
    "lane",
    "source",
    "units",
    "unit_keys",
)
#: Lists that may only extend.
EXTENDING = (
    "gate_identifiers",
    "evidence",
    "scored_evidence",
    "disclosed_overlaps",
    "overlap_review",
    "history",
)
ITEM_FIELDS = {
    "scored_evidence": ("path", "field", "equals"),
    "overlap_review": ("id", "outcome", "reason"),
    "history": ("date", "status", "note"),
}
#: Identity fields a scored-run artifact may be matched on.
IDENTITY_FIELDS = ("gate", "gate.name", "registration_id")
REVIEW_OUTCOMES = ("disjoint",)
MIN_REASON = 40
PLACEHOLDER_RX = re.compile(
    r"\b(todo|tbd|fixme|xxx|placeholder|to be determined)\b", re.I
)
ID_RX = re.compile(r"H[0-9]{3,}")
SOURCE_RX = re.compile(r"[a-z][a-z0-9_]*")
YEARS_RX = re.compile(r"(?P<start>[0-9]{4})(?:-(?P<end>[0-9]{4}))?|undated")
SCOPE_RX = re.compile(r"[a-z0-9][a-z0-9_.\-]*")
#: Scored-run artifacts live here.
RUNS_DIR = "runs"
RUN_PATH_RX = re.compile(rf"{RUNS_DIR}/[A-Za-z0-9_.\-]+\.json")
#: A repository-relative path: no leading slash, no NUL, no ``..``.
PATH_RX = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_./\-]*")
CITATION_RX = re.compile(
    r"(?P<path>[A-Za-z0-9_][A-Za-z0-9_./\-]*):(?P<start>[0-9]{1,7})"
    r"(?:-(?P<end>[0-9]{1,7}))?"
)
URL_RX = re.compile(r"https://\S+")
#: A full object id: SHA-1 (40 hex digits) or SHA-256 (64).
SHA_RX = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?")


def load(repository: Path) -> dict[str, Any]:
    """The registry in ``repository``'s working tree."""
    return json.loads((repository / REGISTRY).read_text(encoding="utf-8"))


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def parse_key(key: Any) -> tuple[str, tuple[int, int] | None] | None:
    """``(source, years)`` for a well-formed unit key, with ``years`` an
    inclusive range or ``None`` for ``undated``; ``None`` otherwise."""
    if not isinstance(key, str):
        return None
    parts = key.split(":")
    if len(parts) < 2 or not SOURCE_RX.fullmatch(parts[0]):
        return None
    if not all(SCOPE_RX.fullmatch(part) for part in parts[2:]):
        return None
    years = YEARS_RX.fullmatch(parts[1])
    if years is None:
        return None
    if parts[1] == "undated":
        return parts[0], None
    start = int(years["start"])
    end = int(years["end"] or start)
    if end < start:
        return None
    return parts[0], (start, end)


def keys_overlap(a: str, b: str) -> bool:
    """Whether two well-formed unit keys name a shared unit: the same
    source, with intersecting years."""
    left, right = parse_key(a), parse_key(b)
    if left is None or right is None or left[0] != right[0]:
        return False
    if left[1] is None or right[1] is None:
        return True
    return left[1][0] <= right[1][1] and right[1][0] <= left[1][1]


def entries_overlap(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    """Whether two entries hold out a shared unit."""
    return any(
        keys_overlap(x, y) for x in a["unit_keys"] for y in b["unit_keys"]
    )


def families(entry: Mapping[str, Any], sources: Mapping[str, Any]) -> set[str]:
    """The source families an entry's unit keys belong to."""
    return {
        sources[parsed[0]]["family"]
        for parsed in map(parse_key, entry["unit_keys"])
        if parsed is not None and parsed[0] in sources
    }


_MISSING = object()


def lookup(document: Any, dotted: str) -> Any:
    """``document``'s value at a dotted field path, or a sentinel."""
    for part in dotted.split("."):
        if not isinstance(document, Mapping) or part not in document:
            return _MISSING
        document = document[part]
    return document


def _git(repository: Path, *args: str) -> subprocess.CompletedProcess:
    """Run git. An argument git cannot take (a NUL byte, ``None``, an
    argument list too long) or a missing git fails like a git error
    rather than raising."""
    command = ["git", "-C", str(repository), *args]
    try:
        return subprocess.run(
            command, capture_output=True, text=True, check=False
        )
    except (ValueError, TypeError, OSError) as error:
        return subprocess.CompletedProcess(command, 128, "", str(error))


def _git_bytes(
    repository: Path, *args: str, stdin: bytes | None = None
) -> bytes | None:
    try:
        found = subprocess.run(
            ["git", "-C", str(repository), *args],
            input=stdin,
            capture_output=True,
            check=False,
        )
    except (ValueError, TypeError, OSError):
        return None
    return found.stdout if found.returncode == 0 else None


def safe_path(path: Any) -> bool:
    """Whether ``path`` is a plain repository-relative path."""
    return (
        isinstance(path, str)
        and PATH_RX.fullmatch(path) is not None
        and ".." not in path.split("/")
    )


def _parse_registry(text: str | None) -> Any:
    """A registry document, or ``None`` when ``text`` is not JSON."""
    if text is None:
        return None
    try:
        return json.loads(text)
    except (ValueError, RecursionError):
        return None


class Committed:
    """Read-only access to one commit of ``repository``, cached."""

    def __init__(self, repository: Path, commit: str = "HEAD") -> None:
        self.repository = repository
        self.commit = commit
        self._files: dict[str, bytes | None] = {}
        self._gates: Mapping[str, Any] | None = None
        self._registered: dict[str, str | None] | None = None

    def blob(self, path: str, commit: str | None = None) -> bytes | None:
        """A regular committed file's bytes at ``commit`` (by default this
        one's), or ``None`` for a symlink, a directory, a missing path or
        an unsafe one."""
        commit = commit or self.commit
        key = f"{commit}:{path}"
        if key not in self._files:
            content = None
            if safe_path(path):
                listed = _git(self.repository, "ls-tree", commit, "--", path)
                fields = listed.stdout.split()
                if (
                    listed.returncode == 0
                    and len(fields) >= 4
                    and fields[0] in ("100644", "100755")
                    and fields[1] == "blob"
                ):
                    content = _git_bytes(self.repository, "show", key)
            self._files[key] = content
        return self._files[key]

    def text(self, path: str) -> str | None:
        """A regular committed UTF-8 file's text, or ``None``."""
        content = self.blob(path)
        if content is None:
            return None
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            return None

    def identifiers(self, gate: str) -> set[str]:
        """Every identifier that may name ``gate`` in scored evidence."""
        if self._gates is None:
            text = self.text(GATES)
            try:
                document = yaml.safe_load(text) if text else {}
            except (yaml.YAMLError, ValueError, RecursionError):
                document = {}
            gates = (
                document.get("gates") if isinstance(document, dict) else None
            )
            self._gates = gates if isinstance(gates, Mapping) else {}
        names = set(REGISTRATIONS_OUTSIDE_GATES_YAML.get(gate, ()))
        declared = self._gates.get(gate)
        if isinstance(declared, Mapping):
            names.add(gate)
            for key in ("id", "registration_id"):
                if isinstance(declared.get(key), str):
                    names.add(declared[key])
        return names

    def registered_at(self, entry_id: str) -> str | None:
        """The oldest commit on this commit's first-parent chain whose
        registry holds ``entry_id``, or ``None``."""
        if self._registered is None:
            self._registered = {}
            log = _git(
                self.repository,
                "log",
                "--first-parent",
                "--reverse",
                "--format=%H",
                self.commit,
                "--",
                REGISTRY,
            )
            for commit in log.stdout.split() if log.returncode == 0 else []:
                document = _parse_registry(
                    _decode(
                        _git_bytes(
                            self.repository, "show", f"{commit}:{REGISTRY}"
                        )
                    )
                )
                entries = (
                    document.get("entries")
                    if isinstance(document, Mapping)
                    else None
                )
                for entry in entries if isinstance(entries, list) else []:
                    name = (
                        entry.get("id") if isinstance(entry, Mapping) else None
                    )
                    if isinstance(name, str):
                        self._registered.setdefault(name, commit)
        return self._registered.get(entry_id)

    def committed_by(self, content: bytes, commit: str) -> bool | None:
        """Whether a file with exactly ``content`` was committed, at any
        path and whether or not it was later moved or deleted, in
        ``commit`` or any of its ancestors. ``None`` when git cannot say,
        including when a shallow clone hides ancestors: an empty search
        proves nothing there. Replacement refs are ignored, so the search
        reads the recorded history."""
        name = _git_bytes(
            self.repository, "hash-object", "--stdin", stdin=content
        )
        if not name or not name.strip():
            return None
        found = _git(
            self.repository,
            "--no-replace-objects",
            "log",
            "-m",
            "-1",
            "--format=%H",
            f"--find-object={name.decode().strip()}",
            commit,
        )
        if found.returncode != 0:
            return None
        if found.stdout.strip():
            return True
        shallow = _git(self.repository, "rev-parse", "--is-shallow-repository")
        if shallow.returncode != 0 or shallow.stdout.strip() != "false":
            return None
        return False


def _decode(content: bytes | None) -> str | None:
    if content is None:
        return None
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _authorization_problems(imports: Any) -> list[str]:
    """Problems with the shape of the historical-import authorizations."""
    if not isinstance(imports, Mapping):
        return ["imports: the authorizations must be a mapping"]
    problems = []
    for name, authorized in imports.items():
        if not (
            isinstance(authorized, Mapping)
            and isinstance(authorized.get("gate"), str)
            and all(
                isinstance(authorized.get(key), (list, tuple))
                and all(isinstance(item, str) for item in authorized[key])
                for key in ("unit_keys", "scored_runs")
            )
        ):
            problems.append(
                f"imports: {name!r} needs a gate, unit_keys and scored_runs"
            )
    return problems


def _import_problems(
    entry: Mapping[str, Any], imports: Mapping[str, Mapping[str, Any]]
) -> list[str]:
    """Problems with a historical import against its authorization."""
    name = entry["id"]
    authorized = imports.get(name)
    if authorized is None:
        return [f"{name}: is not an authorized historical import"]
    problems = []
    if entry["gate"] != authorized["gate"]:
        problems.append(
            f"{name}: is authorized for {authorized['gate']!r}, not "
            f"{entry['gate']!r}"
        )
    if sorted(entry["unit_keys"]) != sorted(authorized["unit_keys"]):
        problems.append(f"{name}: unit keys differ from its authorization")
    cited = sorted(item["path"] for item in entry["scored_evidence"])
    if cited != sorted(authorized["scored_runs"]):
        problems.append(
            f"{name}: scored evidence differs from its authorized runs"
        )
    return problems


def _evidence_problems(
    entry: Mapping[str, Any],
    committed: Committed | None,
    scored_runs: Mapping[str, tuple[str, str]],
    imports: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    """Problems with an entry's scored-evidence citations and, for a
    historical import, with its authorization."""
    name = entry["id"]
    problems: list[str] = []
    if entry["provenance"] == "historical_import":
        problems.extend(_import_problems(entry, imports))
    if not entry["scored_evidence"]:
        return problems
    allowed = set(entry["gate_identifiers"])
    if committed is not None:
        authoritative = committed.identifiers(entry["gate"])
        if not authoritative:
            return [
                *problems,
                f"{name}: {entry['gate']!r} is neither a gates.yaml gate nor "
                "a registration this module lists",
            ]
        allowed &= authoritative
    registered = None
    if committed is not None and entry["provenance"] == "registration":
        registered = committed.registered_at(name)
        if registered is None:
            problems.append(
                f"{name}: a registration cites scored evidence before it is "
                "registered on the base branch"
            )
    for item in entry["scored_evidence"]:
        path, field, equals = item["path"], item["field"], item["equals"]
        run = scored_runs.get(path)
        if run is None:
            problems.append(
                f"{name}: scored evidence {path!r} is not a listed scored run"
            )
            continue
        if run[0] != entry["gate"]:
            problems.append(
                f"{name}: scored evidence {path!r} is {run[0]!r}'s scored run"
            )
            continue
        if field not in IDENTITY_FIELDS:
            problems.append(f"{name}: {field!r} is not an identity field")
            continue
        if equals not in allowed:
            problems.append(
                f"{name}: scored evidence names {equals!r}, which does not "
                "identify this gate"
            )
            continue
        if committed is None:
            continue
        content = committed.blob(path)
        if content is None:
            problems.append(
                f"{name}: scored evidence {path!r} is not a committed file"
            )
            continue
        if hashlib.sha256(content).hexdigest() != run[1]:
            problems.append(
                f"{name}: scored evidence {path!r} differs from the listed "
                "scored run's bytes"
            )
            continue
        document = _parse_registry(_decode(content))
        if lookup(document, field) != equals:
            problems.append(
                f"{name}: scored evidence {path!r} does not have "
                f"{field} == {equals!r}"
            )
            continue
        if registered is not None:
            earlier = committed.committed_by(content, registered)
            if earlier is None:
                problems.append(
                    f"{name}: cannot tell whether its scored run {path!r} "
                    "was committed before it was registered"
                )
            elif earlier:
                problems.append(
                    f"{name}: its scored run {path!r} was already committed, "
                    "at some path, when the entry was registered"
                )
    return problems


def _review_problems(
    entry: Mapping[str, Any], committed: Committed | None
) -> list[str]:
    """Problems with an entry's family-review items."""
    name = entry["id"]
    problems: list[str] = []
    for item in entry["overlap_review"]:
        reviewed = item["id"]
        if item["outcome"] not in REVIEW_OUTCOMES:
            problems.append(
                f"{name}: review of {reviewed} has outcome "
                f"{item['outcome']!r}; an unresolved relation is disclosed"
            )
        reason = item["reason"].strip()
        if len(reason) < MIN_REASON or PLACEHOLDER_RX.search(reason):
            problems.append(
                f"{name}: review of {reviewed} needs a substantive reason"
            )
        citations = item.get("evidence")
        if not isinstance(citations, list) or not citations:
            problems.append(f"{name}: review of {reviewed} cites nothing")
            continue
        for citation in citations:
            problems.extend(_citation_problems(name, citation, committed))
    return problems


def _citation_problems(
    name: str, citation: Any, committed: Committed | None
) -> list[str]:
    if not isinstance(citation, str):
        return [f"{name}: a review citation is not a string"]
    if URL_RX.fullmatch(citation):
        return []
    match = CITATION_RX.fullmatch(citation)
    if match is None:
        return [f"{name}: citation {citation!r} is not path:line or a URL"]
    start = int(match["start"])
    end = int(match["end"] or start)
    if not 1 <= start <= end:
        return [f"{name}: citation {citation!r} has a bad line range"]
    if committed is None:
        return []
    text = committed.text(match["path"])
    if text is None:
        return [f"{name}: citation {citation!r} names no committed file"]
    if end > len(text.splitlines()):
        return [f"{name}: citation {citation!r} runs past the file's end"]
    return []


def _shape_problems(entry: Any) -> list[str]:
    """Type problems in one entry; later checks assume none."""
    if not isinstance(entry, Mapping):
        return ["registry: an entry is not a mapping"]
    name = entry.get("id") if _text(entry.get("id")) else "<no id>"
    missing = [key for key in ENTRY_KEYS if key not in entry]
    if missing:
        return [f"{name}: missing {', '.join(missing)}"]
    problems = [
        f"{name}: {key} must be a non-empty string"
        for key in ENTRY_TEXT
        if not _text(entry[key])
    ]
    problems += [
        f"{name}: {key} must be a list"
        for key in ENTRY_LISTS
        if not isinstance(entry[key], list)
    ]
    if not isinstance(entry["units"], Mapping) or not entry["units"]:
        problems.append(f"{name}: units must be a non-empty mapping")
    if problems:
        return problems
    plain = ("gate_identifiers", "unit_keys", "evidence", "disclosed_overlaps")
    for key in plain:
        if not all(_text(item) for item in entry[key]):
            problems.append(f"{name}: {key} must hold non-empty strings")
    for key, fields in ITEM_FIELDS.items():
        for item in entry[key]:
            if not isinstance(item, Mapping) or not all(
                _text(item.get(field)) for field in fields
            ):
                problems.append(
                    f"{name}: each {key} item needs non-empty "
                    f"{', '.join(fields)}"
                )
                break
    return problems


def _entry_problems(
    entry: Mapping[str, Any],
    sources: Mapping[str, Any],
    committed: Committed | None,
    scored_runs: Mapping[str, tuple[str, str]],
    imports: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    """Problems inside one well-shaped entry."""
    name = entry["id"]
    problems: list[str] = []
    if not ID_RX.fullmatch(name):
        problems.append(f"{name}: id must be H followed by 3+ digits")
    if entry["provenance"] not in FIRST_STATUS:
        problems.append(f"{name}: unknown provenance")
        return problems
    for key in ("gate_identifiers", "unit_keys", "evidence"):
        if not entry[key]:
            problems.append(f"{name}: {key} must not be empty")
        elif len(set(entry[key])) != len(entry[key]):
            problems.append(f"{name}: {key} repeat")
    for key in entry["unit_keys"]:
        parsed = parse_key(key)
        if parsed is None:
            problems.append(f"{name}: malformed unit key {key!r}")
        elif parsed[0] not in sources:
            problems.append(f"{name}: unit key {key!r} names no source")
    history = entry["history"]
    if not history:
        problems.append(f"{name}: history must not be empty")
        return problems
    first = FIRST_STATUS[entry["provenance"]]
    if history[0]["status"] not in first:
        problems.append(
            f"{name}: a {entry['provenance']} starts as one of "
            f"{sorted(first)}, not {history[0]['status']!r}"
        )
    previous_status, previous_date = None, None
    for index, item in enumerate(history):
        status = item["status"]
        if status not in STATUSES:
            problems.append(f"{name}: history[{index}] status {status!r}")
            return problems
        try:
            date = dt.date.fromisoformat(item["date"])
        except ValueError:
            problems.append(f"{name}: history[{index}] date is not a date")
            date = previous_date
        if previous_date is not None and date < previous_date:
            problems.append(f"{name}: history[{index}] goes back in time")
        previous_date = date
        if previous_status is not None and (
            status not in TRANSITIONS[previous_status]
        ):
            problems.append(
                f"{name}: history[{index}] moves {previous_status} -> "
                f"{status}, which is not a legal transition"
            )
        previous_status = status
    if entry["status"] != previous_status:
        problems.append(
            f"{name}: status {entry['status']!r} is not its history's "
            f"last status {previous_status!r}"
        )
    if entry["status"] == "used" and not entry["scored_evidence"]:
        problems.append(f"{name}: a used entry needs scored_evidence")
    problems.extend(_evidence_problems(entry, committed, scored_runs, imports))
    problems.extend(_review_problems(entry, committed))
    return problems


def _vocabulary_problems(sources: Any) -> list[str]:
    if not isinstance(sources, Mapping) or not sources:
        return ["registry: sources must be a non-empty mapping"]
    problems: list[str] = []
    catalogs: dict[str, str] = {}
    for source, declared in sources.items():
        if not isinstance(source, str) or not SOURCE_RX.fullmatch(source):
            problems.append(f"source {source!r}: malformed id")
        if not isinstance(declared, Mapping) or not all(
            _text(declared.get(field)) for field in SOURCE_FIELDS
        ):
            problems.append(
                f"source {source!r}: needs {', '.join(SOURCE_FIELDS)}"
            )
            continue
        catalog = " ".join(declared["catalog"].split()).casefold()
        if catalog in catalogs:
            problems.append(
                f"source {source!r}: shares its catalog with "
                f"{catalogs[catalog]!r}, so one of them is an alias"
            )
        catalogs[catalog] = source
    return problems


def validate(
    registry: Any,
    repository: Path | None = None,
    vocabulary: Mapping[str, Mapping[str, str]] = SOURCES,
    *,
    commit: str = "HEAD",
    scored_runs: Mapping[str, tuple[str, str]] = SCORED_RUNS,
    imports: Mapping[str, Mapping[str, Any]] = HISTORICAL_IMPORTS,
) -> list[str]:
    """Every rule one registry must keep on its own. ``vocabulary`` is the
    controlled source list the registry's copy must equal;
    ``scored_runs`` and ``imports`` are the controlled lists of scored
    runs and authorized historical imports. With ``repository``, scored
    evidence, citations and the completion record are checked against its
    ``commit``."""
    if not isinstance(registry, Mapping):
        return ["registry: not a mapping"]
    missing = [key for key in TOP_LEVEL if key not in registry]
    if missing:
        return [f"registry: missing {', '.join(missing)}"]
    problems = [
        f"registry: {key} must be a non-empty string"
        for key in TEXT_FIELDS
        if not _text(registry[key])
    ]
    if problems:
        return problems
    if registry["schema"] != SCHEMA:
        problems.append(f"registry: schema {registry['schema']!r}")
    rules = registry["rules"]
    if not isinstance(rules, list) or not rules:
        problems.append("registry: rules must be a non-empty list")
    elif not all(_text(rule) for rule in rules):
        problems.append("registry: each rule must be a non-empty string")
    values = registry["status_values"]
    if (
        not isinstance(values, Mapping)
        or set(values) != set(STATUSES)
        or not all(_text(text) for text in values.values())
    ):
        problems.append("registry: status_values must describe each status")
    if not isinstance(registry["complete"], bool):
        problems.append("registry: complete must be true or false")
    problems.extend(_vocabulary_problems(vocabulary))
    problems.extend(_authorization_problems(imports))
    if not isinstance(vocabulary, Mapping) or registry["sources"] != dict(
        vocabulary
    ):
        problems.append(
            "registry: sources must equal the controlled vocabulary"
        )
    entries = registry["entries"]
    if not isinstance(entries, list):
        problems.append("registry: entries must be a list")
    if problems:
        return problems
    for entry in entries:
        problems.extend(_shape_problems(entry))
    if problems:
        return problems
    committed = (
        Committed(repository, commit) if repository is not None else None
    )
    record = registry["completion_record"]
    if not safe_path(record):
        return [f"registry: completion_record {record!r} is not a path"]
    if (
        committed is not None
        and registry["complete"]
        and committed.blob(record) is None
    ):
        problems.append(
            f"registry: marked complete, but {record} is not committed"
        )
    for entry in entries:
        problems.extend(
            _entry_problems(entry, vocabulary, committed, scored_runs, imports)
        )
    if problems:
        return problems
    ids = [entry["id"] for entry in entries]
    if len(set(ids)) != len(ids):
        return ["registry: entry ids repeat"]
    owners: dict[str, str] = {}
    for entry in entries:
        for identifier in entry["gate_identifiers"]:
            owner = owners.setdefault(identifier, entry["gate"])
            if owner != entry["gate"]:
                problems.append(
                    f"{entry['id']}: gate identifier {identifier!r} "
                    f"already identifies {owner!r}"
                )
    by_id = {entry["id"]: entry for entry in entries}
    for entry in entries:
        for other in entry["disclosed_overlaps"]:
            if other == entry["id"]:
                problems.append(f"{entry['id']}: discloses itself")
            elif other not in by_id:
                problems.append(f"{entry['id']}: discloses unknown {other}")
            elif entry["id"] not in by_id[other]["disclosed_overlaps"]:
                problems.append(
                    f"{entry['id']}: discloses {other}, which does not "
                    "disclose it back"
                )
    live = [entry for entry in entries if entry["status"] != "withdrawn"]
    for index, entry in enumerate(live):
        for other in live[index + 1 :]:
            if entries_overlap(entry, other) and (
                other["id"] not in entry["disclosed_overlaps"]
            ):
                problems.append(
                    f"{entry['id']} and {other['id']} hold out a shared "
                    "unit without disclosing it"
                )
    position = {name: index for index, name in enumerate(ids)}
    for index, entry in enumerate(entries):
        reviewed = {item["id"] for item in entry["overlap_review"]}
        for name in reviewed:
            if position.get(name, index) >= index:
                problems.append(
                    f"{entry['id']}: reviews {name}, which is not an "
                    "earlier entry"
                )
        if entry["status"] == "withdrawn":
            continue
        mine = families(entry, vocabulary)
        for other in entries[:index]:
            if (
                other["status"] != "withdrawn"
                and mine & families(other, vocabulary)
                and not entries_overlap(entry, other)
                and other["id"] not in entry["disclosed_overlaps"]
                and other["id"] not in reviewed
            ):
                problems.append(
                    f"{entry['id']}: shares a source family with "
                    f"{other['id']} but neither discloses nor reviews it"
                )
    return problems


def _extends(base: Any, current: Any) -> bool:
    """``current`` is a list that keeps the list ``base`` as its prefix."""
    return (
        isinstance(base, list)
        and isinstance(current, list)
        and current[: len(base)] == base
    )


def empty_like(registry: Mapping[str, Any]) -> dict[str, Any]:
    """The registry as it stood before its first entry: the base a newly
    created registry is admitted against."""
    return {
        "schema": registry.get("schema"),
        "status_values": registry.get("status_values"),
        "completion_record": registry.get("completion_record"),
        "rules": [],
        "sources": {},
        "complete": False,
        "entries": [],
    }


def append_only_problems(
    base: Mapping[str, Any], current: Mapping[str, Any]
) -> list[str]:
    """How ``current`` breaks the append-only rule against ``base``, an
    earlier registry that kept the rules."""
    if not isinstance(base, Mapping) or not isinstance(current, Mapping):
        return ["registry: an append-only comparison needs two mappings"]
    problems: list[str] = []
    for key in ("schema", "status_values", "completion_record"):
        if current.get(key) != base.get(key):
            problems.append(f"registry: {key} changed")
    if not _extends(base.get("rules", []), current.get("rules", [])):
        problems.append("registry: rules may only be appended")
    sources = current.get("sources")
    if not isinstance(sources, Mapping):
        sources = {}
    base_sources = base.get("sources")
    if not isinstance(base_sources, Mapping):
        base_sources = {}
    for source, declared in base_sources.items():
        if sources.get(source) != declared:
            problems.append(f"source {source!r}: changed or removed")
    if base.get("complete") is True and current.get("complete") is not True:
        problems.append("registry: a complete registry became incomplete")
    old = base.get("entries")
    new = current.get("entries")
    for entries in (old, new):
        if not isinstance(entries, list) or not all(
            isinstance(entry, Mapping) and isinstance(entry.get("id"), str)
            for entry in entries
        ):
            return [*problems, "registry: entries are malformed"]
    old_ids = [entry.get("id") for entry in old]
    new_ids = [entry.get("id") for entry in new]
    if new_ids[: len(old_ids)] != old_ids:
        problems.append(
            "registry: earlier entries were removed, reordered or replaced"
        )
        return problems
    for before, after in zip(old, new[: len(old)], strict=True):
        for key in IMMUTABLE:
            if after.get(key) != before.get(key):
                problems.append(f"{before['id']}: {key} changed")
        for key in EXTENDING:
            if not _extends(before.get(key, []), after.get(key, [])):
                problems.append(f"{before['id']}: {key} may only extend")
    for entry in new[len(old) :]:
        name = entry.get("id")
        history = entry.get("history")
        statuses = (
            [item.get("status") for item in history]
            if isinstance(history, list)
            and all(isinstance(item, Mapping) for item in history)
            else None
        )
        if entry.get("provenance") == "historical_import":
            if base.get("complete") is True:
                problems.append(
                    f"{name}: historical imports close when the registry "
                    "is complete"
                )
        elif statuses != ["candidate"]:
            problems.append(
                f"{name}: a new registration is added as a lone candidate, "
                "and moves on only in a later commit"
            )
    return problems


def _commit(repository: Path, ref: str) -> str | None:
    found = _git(
        repository, "rev-parse", "--verify", "-q", f"{ref}^{{commit}}"
    )
    return found.stdout.strip() if found.returncode == 0 else None


def _parents(repository: Path, commit: str) -> list[str]:
    """``commit``'s parents, first parent first. Raises ``LookupError``
    when git cannot list them."""
    found = _git(repository, "rev-list", "--parents", "-n", "1", commit)
    listed = found.stdout.split()
    if found.returncode != 0 or listed[:1] != [commit]:
        raise LookupError(f"cannot list the parents of {str(commit)[:80]}")
    return listed[1:]


def _is_ancestor(repository: Path, ancestor: str, descendant: str) -> bool:
    """Whether ``ancestor`` is an ancestor of ``descendant`` (or the same
    commit). Raises ``LookupError`` when git cannot answer."""
    found = _git(
        repository, "merge-base", "--is-ancestor", ancestor, descendant
    )
    if found.returncode not in (0, 1):
        raise LookupError(
            f"cannot tell whether {str(ancestor)[:80]} is an ancestor of "
            f"{str(descendant)[:80]}"
        )
    return found.returncode == 0


def _landed_parents(repository: Path, commit: str, base: str) -> list[str]:
    """The parents through which a merge ``commit`` brings in landed
    history: each parent after the first that is an ancestor of ``base``
    and not already an ancestor of the first parent. Empty for a commit
    that is not a merge."""
    parents = _parents(repository, commit)
    return [
        parent
        for parent in parents[1:]
        if _is_ancestor(repository, parent, base)
        and not _is_ancestor(repository, parent, parents[0])
    ]


def _rule_keys(rules: list) -> list[tuple[str, int]]:
    """A key for each of ``rules``: its JSON, keys sorted, and how many
    equal rules come before it. So a rule listed twice has two keys, and
    a union keeps both copies."""
    seen: dict[str, int] = {}
    keys = []
    for rule in rules:
        text = json.dumps(rule, sort_keys=True)
        keys.append((text, seen.get(text, 0)))
        seen[text] = seen.get(text, 0) + 1
    return keys


def _union_ready(document: Any) -> bool:
    """Whether ``document`` has the lists and mappings
    :func:`_landed_union` combines, with each entry id listed once."""
    if not (
        isinstance(document, Mapping)
        and isinstance(document.get("rules", []), list)
        and isinstance(document.get("sources", {}), Mapping)
        and isinstance(document.get("entries"), list)
        and all(
            isinstance(entry, Mapping) and isinstance(entry.get("id"), str)
            for entry in document["entries"]
        )
    ):
        return False
    ids = [entry["id"] for entry in document["entries"]]
    return len(set(ids)) == len(ids)


def _in_order(order: list, *groups: list) -> list:
    """The keys in ``groups``, each once: those ``order`` lists, in its
    order, then the rest in the order the groups give them."""
    present = set().union(*groups)
    ranked = [key for key in dict.fromkeys(order) if key in present]
    return list(dict.fromkeys([*ranked, *(key for g in groups for key in g)]))


def _landed_union(
    previous: Any, incoming: Any, canonical: Any
) -> tuple[Any, list[str]]:
    """The registry a merge that brings in landed history must extend.

    It holds every rule, source and entry of ``previous``, the pull
    request's last valid registry, and of ``incoming``, the landed
    parent's: each entry once with each list at the longer of its two
    versions, and each rule as often as either lists it, so dropping one
    copy of a repeated rule is a removal. Entries and rules that
    ``canonical``, the base's registry,
    lists come first, in its order (the landed order; a landed side
    branch's own registry need not follow it), then ``previous``'s others,
    then ``incoming``'s. With no ``canonical``, that is the pull request's
    own order. Also returns the conflicts that no merge could resolve: a
    field that differs, or a list where neither version extends the
    other.

    When either registry is missing, the other is returned. When either
    repeats an entry id (as :func:`validate` also refuses), or lacks
    those lists and mappings, no merge can be shown to keep all it holds:
    ``incoming`` is returned, and that registry is reported as a
    conflict."""
    if previous is None or incoming is None:
        return (incoming if previous is None else previous), []
    unready = [
        line
        for line, document in (
            ("the pull request's", previous),
            ("the landed", incoming),
        )
        if not _union_ready(document)
    ]
    if unready:
        return incoming, [
            f"registry: {line} registry cannot be combined at this merge: "
            "it repeats an entry id, or its entries, rules or sources are "
            "malformed"
            for line in unready
        ]
    conflicts: list[str] = []
    union = dict(incoming)
    for key in ("schema", "status_values", "completion_record"):
        if previous.get(key) != incoming.get(key):
            conflicts.append(f"registry: {key} differs from the landed one")
    sources = dict(incoming.get("sources", {}))
    for source, declared in previous.get("sources", {}).items():
        if source in sources and sources[source] != declared:
            conflicts.append(
                f"source {source!r}: differs from the landed registry"
            )
        sources.setdefault(source, declared)
    union["sources"] = sources
    if previous.get("complete") is True:
        union["complete"] = True
    order = canonical if _union_ready(canonical) else {}
    rules = {
        key: rule
        for document in (incoming, previous)
        for key, rule in zip(
            _rule_keys(document.get("rules", [])),
            document.get("rules", []),
            strict=True,
        )
    }
    union["rules"] = [
        rules[key]
        for key in _in_order(
            _rule_keys(order.get("rules", [])),
            _rule_keys(previous.get("rules", [])),
            _rule_keys(incoming.get("rules", [])),
        )
    ]
    mine = {entry["id"]: entry for entry in previous["entries"]}
    theirs = {entry["id"]: entry for entry in incoming["entries"]}
    entries = []
    for name in _in_order(
        [entry.get("id") for entry in order.get("entries", [])],
        list(mine),
        list(theirs),
    ):
        if name not in theirs or name not in mine:
            entries.append(theirs.get(name, mine.get(name)))
            continue
        entry = dict(theirs[name])
        for key in IMMUTABLE:
            if mine[name].get(key) != theirs[name].get(key):
                conflicts.append(f"{name}: {key} differs from the landed one")
        for key in EXTENDING:
            ours, landed = mine[name].get(key, []), theirs[name].get(key, [])
            if _extends(landed, ours):
                entry[key] = ours
            elif not _extends(ours, landed):
                conflicts.append(
                    f"{name}: {key} and the landed {key} each extend "
                    "beyond the other"
                )
        entries.append(entry)
    union["entries"] = entries
    return union, conflicts


def _event() -> Mapping[str, Any]:
    """The GitHub event payload at ``GITHUB_EVENT_PATH``. Raises
    ``LookupError`` when it cannot be read or is not a JSON object."""
    path = os.environ.get("GITHUB_EVENT_PATH")
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (TypeError, ValueError, OSError) as error:
        raise LookupError(f"cannot read the GitHub event: {error}") from None
    if not isinstance(payload, Mapping):
        raise LookupError("the GitHub event is not a JSON object")
    return payload


def base_commit(repository: Path) -> str:
    """The commit the registry is compared against.

    - On a push (``GITHUB_EVENT_NAME=push``), the event's ``before``
      commit, which was the branch tip before the push. An all-zero
      ``before`` (a branch's first push) falls through to the merge base.
    - Otherwise, the merge base of ``HEAD`` and the base branch
      (``GITHUB_BASE_REF`` on a pull request, otherwise ``master``),
      preferring its ``origin/`` ref.
    - When that merge base is ``HEAD`` itself, as on the base branch, its
      first parent.

    Raises ``LookupError`` when none of these resolves, and on a push
    whose event cannot be read or whose ``before`` commit does not
    resolve: a push is compared with its own boundary, never with a
    nearer commit that would check less history."""
    head = _commit(repository, "HEAD")
    if head is None:
        raise LookupError(f"no HEAD in {repository}")
    if os.environ.get("GITHUB_EVENT_NAME") == "push":
        before = _event().get("before")
        if not isinstance(before, str) or SHA_RX.fullmatch(before) is None:
            raise LookupError("the push event names no before commit")
        if set(before) != {"0"}:
            if _commit(repository, before) is None:
                raise LookupError(
                    f"the push's before commit {before} does not resolve"
                )
            return before
    branch = os.environ.get("GITHUB_BASE_REF") or "master"
    for ref in (f"origin/{branch}", branch):
        found = _git(repository, "merge-base", "HEAD", ref)
        if found.returncode == 0:
            base = found.stdout.strip()
            break
    else:
        raise LookupError(f"no merge base with {branch} in {repository}")
    if base == head:
        parent = _commit(repository, "HEAD^1")
        if parent is None:
            raise LookupError("HEAD is its own base and has no parent")
        return parent
    return base


def registry_at(repository: Path, commit: str) -> Any:
    """The registry document at ``commit``, or ``None`` where it does not
    exist. Raises ``LookupError`` when ``commit`` cannot be read and
    ``ValueError`` when the registry there is not JSON."""
    listed = _git(repository, "ls-tree", "--name-only", commit, REGISTRY)
    if listed.returncode != 0:
        raise LookupError(f"cannot list {REGISTRY} at {str(commit)[:80]}")
    if not listed.stdout.strip():
        return None
    document = _parse_registry(
        _decode(_git_bytes(repository, "show", f"{commit}:{REGISTRY}"))
    )
    if document is None:
        raise ValueError(f"{REGISTRY} at {commit} is not JSON")
    return document


def base_registry(repository: Path) -> Any:
    """The registry at :func:`base_commit`, or ``None`` when the base has
    no registry yet. Raises ``LookupError`` when no base resolves."""
    return registry_at(repository, base_commit(repository))


def pull_request_head() -> str | None:
    """The pull request's head commit, on a ``pull_request`` event, and
    ``None`` on any other. Raises ``LookupError`` on a ``pull_request``
    event that cannot be read or names no head commit, so the pull
    request's own commits are never silently left unchecked."""
    if os.environ.get("GITHUB_EVENT_NAME") != "pull_request":
        return None
    pull_request = _event().get("pull_request")
    head = (
        pull_request.get("head") if isinstance(pull_request, Mapping) else None
    )
    sha = head.get("sha") if isinstance(head, Mapping) else None
    if not isinstance(sha, str) or SHA_RX.fullmatch(sha) is None:
        raise LookupError("the pull_request event names no head commit")
    return sha


def history_problems(
    repository: Path,
    base: str,
    head: str = "HEAD",
    *,
    full: bool = True,
    pull_request: bool = False,
    scored_runs: Mapping[str, tuple[str, str]] = SCORED_RUNS,
    imports: Mapping[str, Mapping[str, Any]] = HISTORICAL_IMPORTS,
) -> list[str]:
    """Problems across every first-parent commit from ``base`` to
    ``head``, so a run of commits cannot hide a change a later commit
    undoes.

    The walk starts from the registry at ``base``. With
    ``pull_request``, for a pull request's own commits, it starts instead
    from the registry at the first listed commit's first parent: the
    pull request's fork point, where its commits leave landed history. A
    pull request branched before the registry existed, or before
    ``base`` changed it, is so compared with the registry it was built
    on. A merge among those commits whose other parent brings in landed
    history (an ancestor of ``base`` that its first parent lacks) is
    compared with the union of its own predecessor and that parent's
    registry (:func:`_landed_union`), so it keeps every entry either line
    holds. It may list them in the base's order or in the pull request's
    own: a stacked pull request that merged the request it builds on in
    its own order, before that request landed, stays valid once it lands,
    and the endpoint test still requires the base's order at the head. A
    merge whose two lines cannot be combined, or that brings in more than
    one line of landed history, is reported. Without ``pull_request``, as
    on a push, merges are not treated apart, and nothing before ``base``
    is trusted.

    With ``full``, each snapshot is validated against its own commit's
    tree. A snapshot that fails is reported and is not used as the next
    one's predecessor. Each valid snapshot must append only to its
    predecessor: the last valid one, or the union a landed merge brings
    in. A newly created registry is admitted against an empty registry.
    Without ``full``, as for a pull request's own commits, only the
    append-only rule is checked. Raises ``LookupError`` when git cannot
    list the commits, their parents or their ancestry."""
    listed = _git(
        repository,
        "rev-list",
        "--first-parent",
        "--reverse",
        f"{base}..{head}",
    )
    if listed.returncode != 0:
        raise LookupError(f"cannot list commits from {base} to {head}")
    commits = listed.stdout.split()
    problems: list[str] = []

    def landed_registry(commit: str) -> Mapping[str, Any] | None:
        try:
            found = registry_at(repository, commit)
        except ValueError as error:
            problems.append(f"{commit[:12]}: {error}")
            return None
        return found if isinstance(found, Mapping) else None

    canonical = None
    if pull_request:
        try:
            canonical = registry_at(repository, base)
        except ValueError:
            canonical = None
    previous_label, previous = base[:12], None
    start = [base]
    if pull_request and commits:
        start = _parents(repository, commits[0])[:1]
    if start:
        previous_label = start[0][:12]
        previous = landed_registry(start[0])
    for commit in commits:
        label = commit[:12]
        landed = (
            _landed_parents(repository, commit, base) if pull_request else []
        )
        if len(landed) > 1:
            problems.append(
                f"{label}: a merge brings in more than one line of landed "
                "history"
            )
            continue
        own_order = None
        if landed:
            incoming = landed_registry(landed[0])
            own_order, _ = _landed_union(previous, incoming, None)
            previous, conflicts = _landed_union(previous, incoming, canonical)
            previous_label = f"{previous_label}+{landed[0][:12]}"
            if conflicts:
                problems.extend(f"{label}: {p}" for p in conflicts)
                continue
        try:
            current = registry_at(repository, commit)
        except ValueError as error:
            problems.append(f"{label}: {error}")
            continue
        if current is None:
            if previous is not None:
                problems.append(f"{label}: the registry was deleted")
            continue
        if not isinstance(current, Mapping):
            problems.append(f"{label}: registry: not a mapping")
            continue
        if full:
            sources = current.get("sources")
            shape = validate(
                current,
                repository,
                vocabulary=sources if isinstance(sources, Mapping) else {},
                commit=commit,
                scored_runs=scored_runs,
                imports=imports,
            )
            if shape:
                problems.extend(f"{label}: {p}" for p in shape)
                continue
        before = previous if previous is not None else empty_like(current)
        changes = append_only_problems(before, current)
        if own_order is not None and not append_only_problems(
            own_order, current
        ):
            changes = []
        if changes:
            problems.extend(f"{previous_label}..{label}: {p}" for p in changes)
            continue
        previous_label, previous = label, current
    return problems
