"""The held-out data registry and the rules every commit must keep.

``docs/design/track_b_holdout_registry.json`` records the data that Track
B's gates and the open-population lane's gates hold out. The dynamics
coordinator made it the single registry for every lane on 2026-10-21.
This module enforces its rules:

- one schema, ``track_b_holdout_registry.v1``, with every field typed;
- a declared source vocabulary: each source has a family, a title and a
  catalog reference that no other source shares, so one source cannot be
  registered under two names;
- unit keys ``source:years[:scope...]``, where ``years`` is a year, an
  inclusive year range, or ``undated``. Two keys name a shared unit when
  they have the same source and their years intersect (``undated``
  intersects every year). Scope segments describe the unit and never
  narrow the overlap;
- no shared unit between live entries goes undisclosed, and every
  disclosure is symmetric;
- relations the mechanical rule cannot see are reviewed by hand: an entry
  lists, with a reason, every earlier live entry of the same source
  family that it neither shares a unit with nor discloses;
- unique entry ids, which are never removed, reordered or reused;
- histories with legal transitions only. A registration starts as a
  ``candidate``, and is added in a commit of its own before it may move
  on, so every registration reaches the base branch before its gate
  freezes. A historical import, a gate that froze or scored before the
  registry existed, starts as ``frozen`` or ``used`` and may be added only
  while the registry is incomplete;
- a ``used`` entry cites committed, gate-identified artifacts of its
  scored run;
- entries only grow: against the base registry, an entry's identity and
  units never change, and its lists only extend;
- the registry stays incomplete until its completion record, B0.2's
  mechanical exposure inventory, exists.

The overlap rule is deliberately coarse. It catches two gates that read
the same source at the same year, whatever variable or table they use.
It cannot see that two sources share underlying data, or that two
editions of a publication report the same data years. That is what the
family review is for.

Each check returns a list of problems; an empty list means the registry
keeps the rules.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

SCHEMA = "track_b_holdout_registry.v1"
REGISTRY = "docs/design/track_b_holdout_registry.json"
STATUSES = ("candidate", "frozen", "used", "withdrawn")
TRANSITIONS = {
    "candidate": frozenset({"frozen", "withdrawn"}),
    "frozen": frozenset({"used", "withdrawn"}),
    "used": frozenset(),
    "withdrawn": frozenset(),
}
#: Each provenance's permitted first statuses. A historical import records
#: a gate that froze or scored before the registry existed.
FIRST_STATUS = {
    "registration": frozenset({"candidate"}),
    "historical_import": frozenset({"frozen", "used"}),
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
ID_RX = re.compile(r"H[0-9]{3,}")
SOURCE_RX = re.compile(r"[a-z][a-z0-9_]*")
YEARS_RX = re.compile(r"(?P<start>[0-9]{4})(?:-(?P<end>[0-9]{4}))?|undated")
SCOPE_RX = re.compile(r"[a-z0-9][a-z0-9_.\-]*")
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


def lookup(document: Any, dotted: str) -> Any:
    """``document``'s value at a dotted field path, or a sentinel."""
    for part in dotted.split("."):
        if not isinstance(document, Mapping) or part not in document:
            return _MISSING
        document = document[part]
    return document


_MISSING = object()


def tracked_files(repository: Path) -> set[str] | None:
    """Paths git tracks in ``repository``, or ``None`` without git."""
    listed = _git(repository, "ls-files", "-z")
    if listed.returncode != 0:
        return None
    return {path for path in listed.stdout.split("\0") if path}


def _evidence_problems(
    name: str,
    item: Mapping[str, Any],
    identifiers: Sequence[str],
    repository: Path | None,
    tracked: set[str] | None,
) -> list[str]:
    """Problems with one scored-evidence citation."""
    path, field, equals = item["path"], item["field"], item["equals"]
    if equals not in identifiers:
        return [f"{name}: scored evidence names {equals!r}, not this gate"]
    if repository is None:
        return []
    if path.startswith(("/", "~")) or ".." in path.split("/"):
        return [f"{name}: scored evidence {path!r} is outside the repository"]
    if tracked is None:
        return [f"{name}: cannot list committed files to check {path!r}"]
    if path not in tracked:
        return [f"{name}: scored evidence {path!r} is not committed"]
    target = repository / path
    root = repository.resolve()
    resolved = target.resolve()
    if target.is_symlink() or not resolved.is_relative_to(root):
        return [
            f"{name}: scored evidence {path!r} is a symlink or leaves "
            "the repository"
        ]
    if not resolved.is_file():
        return [f"{name}: scored evidence {path!r} is not a file"]
    try:
        document = json.loads(resolved.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return [f"{name}: scored evidence {path!r} is not JSON"]
    if lookup(document, field) != equals:
        return [
            f"{name}: scored evidence {path!r} does not have "
            f"{field} == {equals!r}"
        ]
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
    for key in (
        "gate_identifiers",
        "unit_keys",
        "evidence",
        "disclosed_overlaps",
    ):
        if not all(_text(item) for item in entry[key]):
            problems.append(f"{name}: {key} must hold non-empty strings")
    shapes = {
        "scored_evidence": ("path", "field", "equals"),
        "overlap_review": ("id", "reason"),
        "history": ("date", "status", "note"),
    }
    for key, fields in shapes.items():
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
    repository: Path | None,
    tracked: set[str] | None,
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
    for item in entry["scored_evidence"]:
        problems.extend(
            _evidence_problems(
                name, item, entry["gate_identifiers"], repository, tracked
            )
        )
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


def validate(registry: Any, repository: Path | None = None) -> list[str]:
    """Every rule one registry must keep on its own. With ``repository``,
    scored evidence and the completion record are checked against its
    committed files."""
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
    problems.extend(_vocabulary_problems(registry["sources"]))
    entries = registry["entries"]
    if not isinstance(entries, list):
        problems.append("registry: entries must be a list")
    if problems:
        return problems
    for entry in entries:
        problems.extend(_shape_problems(entry))
    if problems:
        return problems
    record = registry["completion_record"]
    if (
        repository is not None
        and registry["complete"]
        and not (repository / record).is_file()
    ):
        problems.append(
            f"registry: marked complete, but {record} does not exist"
        )
    sources = registry["sources"]
    tracked = tracked_files(repository) if repository is not None else None
    for entry in entries:
        problems.extend(_entry_problems(entry, sources, repository, tracked))
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
        mine = families(entry, sources)
        for other in entries[:index]:
            if (
                other["status"] != "withdrawn"
                and mine & families(other, sources)
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
        if entry.get("provenance") == "historical_import":
            if base.get("complete") is True:
                problems.append(
                    f"{name}: historical imports close when the registry "
                    "is complete"
                )
        elif [item.get("status") for item in entry.get("history", [])] != [
            "candidate"
        ]:
            problems.append(
                f"{name}: a new registration is added as a lone candidate, "
                "and moves on only in a later commit"
            )
    return problems


def _git(repository: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repository), *args],
        capture_output=True,
        text=True,
        check=False,
    )


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


def base_registry(repository: Path) -> dict[str, Any] | None:
    """The registry at :func:`base_commit`, or ``None`` when the base has
    no registry yet. Raises ``LookupError`` when no base resolves."""
    commit = base_commit(repository)
    listed = _git(repository, "ls-tree", "--name-only", commit, REGISTRY)
    if listed.returncode != 0:
        raise LookupError(f"cannot list {REGISTRY} at {commit}")
    if not listed.stdout.strip():
        return None
    shown = _git(repository, "show", f"{commit}:{REGISTRY}")
    if shown.returncode != 0:
        raise LookupError(f"cannot read {REGISTRY} at {commit}")
    return json.loads(shown.stdout)
