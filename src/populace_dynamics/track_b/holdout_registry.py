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
  before its gate freezes. A historical import is a gate that scored
  before the registry existed: it starts as ``used``, and its scored
  evidence must have been committed before the registry was;
- a ``used`` entry cites scored-run artifacts under ``runs/``, read from
  the committed tree, whose identity field equals one of the gate's
  identifiers in ``gates.yaml`` or :data:`REGISTRATIONS_OUTSIDE_GATES_YAML`;
- entries only grow: against the base registry, and between every pair
  of consecutive first-parent commits since it, an entry's identity and
  units never change, and its lists only extend;
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
CITATION_RX = re.compile(
    r"(?P<path>[A-Za-z0-9_][A-Za-z0-9_./\-]*):(?P<start>[0-9]+)"
    r"(?:-(?P<end>[0-9]+))?"
)
URL_RX = re.compile(r"https://\S+")
SHA_RX = re.compile(r"[0-9a-f]{40}")


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
    return subprocess.run(
        ["git", "-C", str(repository), *args],
        capture_output=True,
        text=True,
        check=False,
    )


class Committed:
    """Read-only access to one commit of ``repository``, cached."""

    def __init__(self, repository: Path, commit: str = "HEAD") -> None:
        self.repository = repository
        self.commit = commit
        self._files: dict[str, str | None] = {}
        self._gates: Mapping[str, Any] | None = None
        self._first_added: dict[str, str | None] = {}

    def text(self, path: str) -> str | None:
        """A regular committed file's text, or ``None``."""
        if path not in self._files:
            listed = _git(self.repository, "ls-tree", self.commit, "--", path)
            fields = listed.stdout.split()
            regular = (
                listed.returncode == 0
                and len(fields) >= 4
                and fields[0] in ("100644", "100755")
                and fields[1] == "blob"
            )
            shown = (
                _git(self.repository, "show", f"{self.commit}:{path}")
                if regular
                else None
            )
            self._files[path] = (
                shown.stdout if shown and shown.returncode == 0 else None
            )
        return self._files[path]

    def identifiers(self, gate: str) -> set[str]:
        """Every identifier that may name ``gate`` in scored evidence."""
        if self._gates is None:
            text = self.text(GATES)
            document = yaml.safe_load(text) if text else {}
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

    def first_added(self, path: str) -> str | None:
        """The oldest commit before ``self.commit`` that added ``path``."""
        if path not in self._first_added:
            log = _git(
                self.repository,
                "log",
                "--diff-filter=A",
                "--format=%H",
                self.commit,
                "--",
                path,
            )
            commits = log.stdout.split() if log.returncode == 0 else []
            self._first_added[path] = commits[-1] if commits else None
        return self._first_added[path]

    def is_ancestor(self, older: str, newer: str) -> bool:
        return (
            _git(
                self.repository, "merge-base", "--is-ancestor", older, newer
            ).returncode
            == 0
        )


def _evidence_problems(
    entry: Mapping[str, Any], committed: Committed | None
) -> list[str]:
    """Problems with an entry's scored-evidence citations."""
    if not entry["scored_evidence"]:
        return []
    name = entry["id"]
    problems: list[str] = []
    allowed = set(entry["gate_identifiers"])
    if committed is not None:
        authoritative = committed.identifiers(entry["gate"])
        if not authoritative:
            return [
                f"{name}: {entry['gate']!r} is neither a gates.yaml gate nor "
                "a registration this module lists"
            ]
        allowed &= authoritative
    cutoff = None
    if committed is not None and entry["provenance"] == "historical_import":
        cutoff = committed.first_added(REGISTRY)
    for item in entry["scored_evidence"]:
        path, field, equals = item["path"], item["field"], item["equals"]
        if not RUN_PATH_RX.fullmatch(path):
            problems.append(
                f"{name}: scored evidence {path!r} is not runs/*.json"
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
        text = committed.text(path)
        if text is None:
            problems.append(
                f"{name}: scored evidence {path!r} is not a committed file"
            )
            continue
        try:
            document = json.loads(text)
        except json.JSONDecodeError:
            problems.append(f"{name}: scored evidence {path!r} is not JSON")
            continue
        if lookup(document, field) != equals:
            problems.append(
                f"{name}: scored evidence {path!r} does not have "
                f"{field} == {equals!r}"
            )
            continue
        if cutoff is not None:
            added = committed.first_added(path)
            if added is None or not committed.is_ancestor(added, cutoff):
                problems.append(
                    f"{name}: a historical import's evidence {path!r} was "
                    "committed after the registry existed"
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
    problems.extend(_evidence_problems(entry, committed))
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
) -> list[str]:
    """Every rule one registry must keep on its own. ``vocabulary`` is the
    controlled source list the registry's copy must equal. With
    ``repository``, scored evidence, citations and the completion record
    are checked against its ``HEAD`` commit."""
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
    if registry["sources"] != dict(vocabulary):
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
    committed = Committed(repository) if repository is not None else None
    record = registry["completion_record"]
    if (
        committed is not None
        and registry["complete"]
        and committed.text(record) is None
    ):
        problems.append(
            f"registry: marked complete, but {record} is not committed"
        )
    for entry in entries:
        problems.extend(_entry_problems(entry, vocabulary, committed))
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


def append_only_problems(
    base: Mapping[str, Any], current: Mapping[str, Any]
) -> list[str]:
    """How ``current`` breaks the append-only rule against ``base``, an
    earlier registry that kept the rules."""
    problems: list[str] = []
    for key in ("schema", "status_values", "completion_record"):
        if current.get(key) != base.get(key):
            problems.append(f"registry: {key} changed")
    if not _extends(base.get("rules", []), current.get("rules", [])):
        problems.append("registry: rules may only be appended")
    sources = current.get("sources")
    if not isinstance(sources, Mapping):
        sources = {}
    for source, declared in base.get("sources", {}).items():
        if sources.get(source) != declared:
            problems.append(f"source {source!r}: changed or removed")
    if base.get("complete") is True and current.get("complete") is not True:
        problems.append("registry: a complete registry became incomplete")
    old = base.get("entries", [])
    new = current.get("entries")
    if not isinstance(new, list) or not all(
        isinstance(entry, Mapping) for entry in new
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


def base_commit(repository: Path) -> str:
    """The commit the registry is compared against.

    - On a push (``GITHUB_EVENT_NAME=push``), the event's ``before``
      commit, which was the branch tip before the push.
    - Otherwise, the merge base of ``HEAD`` and the base branch
      (``GITHUB_BASE_REF`` on a pull request, otherwise ``master``),
      preferring its ``origin/`` ref.
    - When that merge base is ``HEAD`` itself, as on the base branch, its
      first parent.

    Raises ``LookupError`` when none of these resolves."""
    head = _commit(repository, "HEAD")
    if head is None:
        raise LookupError(f"no HEAD in {repository}")
    if os.environ.get("GITHUB_EVENT_NAME") == "push":
        event = os.environ.get("GITHUB_EVENT_PATH")
        before = None
        if event and Path(event).is_file():
            before = json.loads(Path(event).read_text()).get("before")
        if isinstance(before, str) and SHA_RX.fullmatch(before):
            if set(before) != {"0"} and _commit(repository, before):
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


def registry_at(repository: Path, commit: str) -> dict[str, Any] | None:
    """The registry at ``commit``, or ``None`` where it does not exist.
    Raises ``LookupError`` when ``commit`` cannot be read."""
    listed = _git(repository, "ls-tree", "--name-only", commit, REGISTRY)
    if listed.returncode != 0:
        raise LookupError(f"cannot list {REGISTRY} at {commit}")
    if not listed.stdout.strip():
        return None
    shown = _git(repository, "show", f"{commit}:{REGISTRY}")
    if shown.returncode != 0:
        raise LookupError(f"cannot read {REGISTRY} at {commit}")
    return json.loads(shown.stdout)


def base_registry(repository: Path) -> dict[str, Any] | None:
    """The registry at :func:`base_commit`, or ``None`` when the base has
    no registry yet. Raises ``LookupError`` when no base resolves."""
    return registry_at(repository, base_commit(repository))


def history_problems(repository: Path, base: str) -> list[str]:
    """Append-only problems between every pair of consecutive first-parent
    commits from ``base`` to ``HEAD``, so a push of several commits cannot
    hide a change that a later commit undoes."""
    listed = _git(
        repository, "rev-list", "--first-parent", "--reverse", f"{base}..HEAD"
    )
    if listed.returncode != 0:
        raise LookupError(f"cannot list commits from {base} to HEAD")
    problems: list[str] = []
    previous_commit = base
    previous = registry_at(repository, base)
    for commit in listed.stdout.split():
        current = registry_at(repository, commit)
        if current is not None:
            shape = validate(current, vocabulary=current.get("sources", {}))
            if shape:
                problems.extend(f"{commit[:12]}: {p}" for p in shape)
            elif previous is not None:
                problems.extend(
                    f"{previous_commit[:12]}..{commit[:12]}: {p}"
                    for p in append_only_problems(previous, current)
                )
        elif previous is not None:
            problems.append(f"{commit[:12]}: the registry was deleted")
        previous_commit, previous = commit, current
    return problems
