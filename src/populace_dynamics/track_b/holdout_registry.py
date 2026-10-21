"""The held-out data registry and the rules every commit must keep.

``docs/design/track_b_holdout_registry.json`` records the source years,
editions, tables and partitions that Track B's gates and the
open-population lane's gates hold out. The dynamics coordinator made it
the single registry for every lane on 2026-10-21. This module enforces
its rules:

- one schema, ``track_b_holdout_registry.v1``;
- unique entry ids, which are never removed, reordered or reused;
- no unit held out by two live entries silently: entries whose unit keys
  overlap list each other in ``disclosed_overlaps``, and every disclosure
  is symmetric;
- each entry's status is its history's last status, reached through legal
  transitions only;
- a ``used`` entry names committed artifacts of the gate's scored run;
- entries only grow: against the base registry, an entry's identity and
  units never change, and its history, evidence, scored evidence and
  disclosures only extend;
- the registry stays marked incomplete until its completion record, B0.2's
  mechanical exposure inventory, exists.

Each check returns a list of problems; an empty list means the registry
keeps the rules.
"""

from __future__ import annotations

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
#: Legal next statuses. A first history item may hold any status, so prior
#: uses are recorded as ``used`` when they are entered.
TRANSITIONS = {
    "candidate": frozenset({"frozen", "withdrawn"}),
    "frozen": frozenset({"used", "withdrawn"}),
    "used": frozenset(),
    "withdrawn": frozenset(),
}
UNIT_KINDS = (
    "reference_years",
    "publication_edition_tables",
    "person_partition",
)
TOP_LEVEL = (
    "schema",
    "title",
    "purpose",
    "rules",
    "status_values",
    "complete",
    "completion_record",
    "entries",
)
ENTRY_KEYS = (
    "id",
    "gate",
    "lane",
    "status",
    "source",
    "unit_kind",
    "units",
    "unit_keys",
    "evidence",
    "scored_evidence",
    "disclosed_overlaps",
    "history",
)
#: Fields that identify an entry and its units; they never change.
IMMUTABLE = ("id", "gate", "lane", "source", "unit_kind", "units", "unit_keys")
#: Lists that may only extend.
EXTENDING = ("evidence", "scored_evidence", "disclosed_overlaps", "history")
ID_RX = re.compile(r"H[0-9]{3,}")
SEGMENT = r"[a-z0-9][a-z0-9_.\-]*"
UNIT_KEY_RX = re.compile(rf"{SEGMENT}(?::{SEGMENT})*")
DATE_RX = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


def load(repository: Path) -> dict[str, Any]:
    """The registry in ``repository``'s working tree."""
    return json.loads((repository / REGISTRY).read_text(encoding="utf-8"))


def keys_overlap(a: str, b: str) -> bool:
    """Whether two unit keys name a shared unit: one is the other or a
    ``:``-segment prefix of it, so ``ssa_di_asr:2023`` (an edition)
    overlaps ``ssa_di_asr:2023:table_19`` (one of its tables)."""
    left, right = a.split(":"), b.split(":")
    n = min(len(left), len(right))
    return left[:n] == right[:n]


def entries_overlap(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    """Whether two entries hold out a shared unit."""
    return any(
        keys_overlap(x, y) for x in a["unit_keys"] for y in b["unit_keys"]
    )


def _relative_file(repository: Path, relative: Any) -> bool:
    """``relative`` names a file inside ``repository``."""
    if not isinstance(relative, str) or not relative:
        return False
    if relative.startswith(("/", "~")) or ".." in relative.split("/"):
        return False
    return (repository / relative).is_file()


def _entry_problems(
    entry: Mapping[str, Any], repository: Path | None
) -> list[str]:
    """Problems inside one entry, without reference to the others."""
    name = entry.get("id", "<no id>")
    missing = [key for key in ENTRY_KEYS if key not in entry]
    if missing:
        return [f"{name}: missing {', '.join(missing)}"]
    problems: list[str] = []
    if not isinstance(name, str) or not ID_RX.fullmatch(name):
        problems.append(f"{name}: id must match H followed by 3+ digits")
    for key in ("gate", "lane", "source"):
        if not isinstance(entry[key], str) or not entry[key]:
            problems.append(f"{name}: {key} must be a non-empty string")
    if entry["unit_kind"] not in UNIT_KINDS:
        problems.append(f"{name}: unknown unit_kind {entry['unit_kind']!r}")
    if not isinstance(entry["units"], Mapping) or not entry["units"]:
        problems.append(f"{name}: units must be a non-empty mapping")
    keys = entry["unit_keys"]
    if (
        not isinstance(keys, list)
        or not keys
        or not all(
            isinstance(k, str) and UNIT_KEY_RX.fullmatch(k) for k in keys
        )
    ):
        problems.append(f"{name}: unit_keys must be well-formed keys")
    elif len(set(keys)) != len(keys):
        problems.append(f"{name}: unit_keys repeat")
    for key in ("evidence", "scored_evidence", "disclosed_overlaps"):
        if not isinstance(entry[key], list) or not all(
            isinstance(item, str) and item for item in entry[key]
        ):
            problems.append(f"{name}: {key} must be a list of strings")
    history = entry["history"]
    if not isinstance(history, list) or not history:
        problems.append(f"{name}: history must be a non-empty list")
        return problems
    previous_status, previous_date = None, ""
    for index, item in enumerate(history):
        if not isinstance(item, Mapping):
            problems.append(f"{name}: history[{index}] is not a mapping")
            return problems
        status, date = item.get("status"), item.get("date")
        if status not in STATUSES:
            problems.append(f"{name}: history[{index}] status {status!r}")
            return problems
        if not isinstance(date, str) or not DATE_RX.fullmatch(date):
            problems.append(f"{name}: history[{index}] date {date!r}")
        elif date < previous_date:
            problems.append(f"{name}: history[{index}] goes back in time")
        else:
            previous_date = date
        if not isinstance(item.get("note"), str) or not item["note"]:
            problems.append(f"{name}: history[{index}] needs a note")
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
    if entry["status"] == "used":
        if not entry["scored_evidence"]:
            problems.append(f"{name}: a used entry needs scored_evidence")
        elif repository is not None:
            for relative in entry["scored_evidence"]:
                if not _relative_file(repository, relative):
                    problems.append(
                        f"{name}: scored_evidence {relative!r} is not a "
                        "committed file"
                    )
    return problems


def validate(
    registry: Mapping[str, Any], repository: Path | None = None
) -> list[str]:
    """Every rule that one registry must keep on its own. With
    ``repository``, scored evidence and the completion record are checked
    against its files."""
    missing = [key for key in TOP_LEVEL if key not in registry]
    if missing:
        return [f"registry: missing {', '.join(missing)}"]
    problems: list[str] = []
    if registry["schema"] != SCHEMA:
        problems.append(f"registry: schema {registry['schema']!r}")
    if not isinstance(registry["rules"], list) or not all(
        isinstance(rule, str) and rule for rule in registry["rules"]
    ):
        problems.append("registry: rules must be a list of strings")
    if not isinstance(registry["status_values"], Mapping) or set(
        registry["status_values"]
    ) != set(STATUSES):
        problems.append("registry: status_values must name each status")
    if not isinstance(registry["complete"], bool):
        problems.append("registry: complete must be true or false")
    record = registry["completion_record"]
    if not isinstance(record, str) or not record:
        problems.append("registry: completion_record must name a path")
    elif (
        repository is not None
        and registry["complete"] is True
        and not _relative_file(repository, record)
    ):
        problems.append(
            f"registry: marked complete, but {record} does not exist"
        )
    entries = registry["entries"]
    if not isinstance(entries, list):
        return [*problems, "registry: entries must be a list"]
    for entry in entries:
        if not isinstance(entry, Mapping):
            return [*problems, "registry: an entry is not a mapping"]
        problems.extend(_entry_problems(entry, repository))
    if problems:
        return problems
    ids = [entry["id"] for entry in entries]
    if len(set(ids)) != len(ids):
        problems.append("registry: entry ids repeat")
        return problems
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
    return problems


def _extends(base: Sequence[Any], current: Sequence[Any]) -> bool:
    """``current`` keeps ``base`` as its prefix."""
    return list(current[: len(base)]) == list(base)


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
    if base.get("complete") is True and current.get("complete") is not True:
        problems.append("registry: a complete registry became incomplete")
    old = base.get("entries", [])
    new = current.get("entries", [])
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
    return problems


def _git(repository: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repository), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def base_registry(repository: Path) -> dict[str, Any] | None:
    """The registry at the merge base of ``HEAD`` and the base branch
    (``GITHUB_BASE_REF`` on a pull request, otherwise ``master``), or
    ``None`` when the base has no registry yet. Raises ``LookupError``
    when no base can be resolved."""
    branch = os.environ.get("GITHUB_BASE_REF") or "master"
    for ref in (f"origin/{branch}", branch):
        merge_base = _git(repository, "merge-base", "HEAD", ref)
        if merge_base.returncode == 0:
            break
    else:
        raise LookupError(f"no merge base with {branch} in {repository}")
    commit = merge_base.stdout.strip()
    shown = _git(repository, "show", f"{commit}:{REGISTRY}")
    if shown.returncode != 0:
        listed = _git(repository, "ls-tree", "--name-only", commit, REGISTRY)
        if listed.returncode == 0 and not listed.stdout.strip():
            return None
        raise LookupError(f"cannot read {REGISTRY} at {commit}")
    return json.loads(shown.stdout)
