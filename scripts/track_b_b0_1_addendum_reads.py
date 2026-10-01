#!/usr/bin/env python3
"""Track B B0.1 addendum: the authoring session's reads record.

Reads a Claude Code session export (the zip the desktop app's Export
writes) and records every tool call of the session and of its subagents:
the tool, the time, the path, range or pattern it named, and for a shell
command its first line, its SHA-256 and the paths it names. It records
no tool output and reads none.

Each call that names a path on `RESTRICTED-FILES.md` or on either exposure
inventory's Q6 exclusion list (plus the codebook-evidence folder) is
flagged and classified by the rules in ``classify``. Calls the rules
cannot place are classified by hand in ``OVERRIDES``, keyed by the
command's SHA-256, with a note saying what was checked.

    python scripts/track_b_b0_1_addendum_reads.py EXPORT.zip \\
        --out docs/design/track_b_b0_1_addendum_reads.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "track_b_b0_1_addendum_reads.v1"
HOME = "/Users/maxghenis"
EV = f"{HOME}/microcosm-launch-evidence/dynasim-parity-20260909"
REFS = f"{HOME}/PolicyEngine/dynasim-refs"
INVENTORIES = (
    "docs/design/track_b_b0_1_exposure_inventory.json",
    "docs/design/track_b_b0_1_exposure_inventory_addendum.json",
)
CODEBOOK_DIR = "data/external/psid_codebook_field_evidence/"
#: This session's own subfolder of the shared Claude project folder.
OWN_SUBFOLDER = (
    "/.claude/projects/-Users-maxghenis-Library-Application-Support-Claude-"
    "scratch-workspaces-ee3763f4-e7ea-4177-bcaf-1362266768c1-4457aa9d-"
    "2dc0-4bcf-a128-e50adae6be25-scratch-2026-09-22-b65ec9/"
    "af842ed1-c915-4edb-8db1-e65d63f0bb3a/"
)
INPUT_KEYS = ("file_path", "path", "pattern", "glob", "offset", "limit")
ABSOLUTE_RX = re.compile(r"(?:/Users|/private|/tmp|~)/[^\s\"'`<>|;)(]+")
RELATIVE_RX = re.compile(
    r"(?<![\w/.-])((?:docs|scripts|src|tests|data|runs|paper)/[\w./-]+"
    r"|gates\.yaml)"
)
SED_RX = re.compile(
    r"sed -n '?(\d+),(\d+)p'? (?:\S*/)?(gates\.yaml|m6_projection_engine\.md)"
)
GIT_METADATA_RX = re.compile(
    r"git diff --(?:numstat|stat|name-only)|git log|git ls-files"
    r"|git cat-file -[ts]|check-attr"
)
#: Calls the rules cannot classify, checked by hand: the inputs, and for
#: the second only the line numbers its output printed.
OVERRIDES = {
    "2f8b1d624e5d680132e79b9a4d32cd3996f4d02ddef00cf8925513578357d09f": (
        "named_in_grep_pattern_or_filter",
        "gates.yaml is a grep pattern run on "
        "scripts/select_m6_qstar_train_only.py",
    ),
    "f57060f2db3d8b2698d3c21ccd14c0186b99e8767d1756a56256ce9a0976007d": (
        "line_numbers_and_headings_outside_flagged_ranges",
        "printed match line numbers and the headings at lines 3689, 3709 "
        "and 3766",
    ),
}


def flagged_ranges(inventories: Iterable[Mapping[str, Any]]) -> dict:
    """Each line-range exclusion's ranges, by file name."""
    out: dict[str, list[tuple[int, int]]] = {}
    for inventory in inventories:
        for entry in inventory["q6_exclusions"]:
            if entry.get("scope") == "line_ranges":
                name = entry["path"].split("/")[-1]
                out.setdefault(name, [])
                for lo, hi in entry["lines"]:
                    if (lo, hi) not in out[name]:
                        out[name].append((lo, hi))
    return out


def restricted_prefixes(text: str) -> set[str]:
    """Absolute path prefixes named in `RESTRICTED-FILES.md`."""
    out: set[str] = set()
    for token in re.findall(r"`([^`]+)`", text):
        token = token.strip()
        if token.startswith("EV/"):
            path = EV + token[2:]
        elif token.startswith("REFS/"):
            path = REFS + token[4:]
        elif token.startswith("~/"):
            path = HOME + token[1:]
        elif token.startswith("/Users/"):
            path = token
        else:
            continue
        out.add(path.split("*")[0].rstrip())
    out.discard(EV)
    out.discard(EV + "/")
    return out


class Checker:
    def __init__(
        self,
        restricted: set[str],
        denied: set[str],
        ranges: Mapping[str, list[tuple[int, int]]],
    ):
        self.restricted = restricted
        self.denied = denied
        self.ranges = ranges

    def flags(self, path: str) -> list[str]:
        if path.startswith("~/"):
            path = HOME + path[1:]
        hits = [
            "restricted:" + r.replace(HOME, "~")
            for r in self.restricted
            if path.startswith(r)
        ]
        hits += [
            "q6:" + d
            for d in self.denied
            if path == d or path.endswith("/" + d)
        ]
        if CODEBOOK_DIR in path or path.startswith(CODEBOOK_DIR.rstrip("/")):
            hits.append("q6:" + CODEBOOK_DIR)
        return hits

    def outside(self, name: str, lo: int, hi: int) -> bool:
        return all(hi < a or lo > b for a, b in self.ranges.get(name, []))

    def classify(
        self, rec: Mapping[str, Any], command: str, hits: list[str]
    ) -> list[str]:
        q6 = [h[3:] for h in hits if h.startswith("q6:")]
        classes: list[str] = []
        if any(h.startswith("restricted:") for h in hits):
            named = [
                p
                for p in [rec.get("file_path") or ""]
                + rec.get("paths_named", [])
                if "/.claude/projects/" in p
            ]
            own = named and all(OWN_SUBFOLDER in p for p in named)
            classes.append(
                "own_transcript_subfolder" if own else "OTHER_restricted"
            )
        if not q6:
            return classes
        if rec["tool"] == "Read":
            name = str(rec.get("file_path", "")).split("/")[-1]
            lo = int(rec.get("offset") or 1)
            hi = lo + int(rec.get("limit") or 2000)
            ok = name in self.ranges and self.outside(name, lo, hi)
            classes.append(
                "ranged_read_outside_flagged_ranges" if ok else "OTHER_read"
            )
            return classes
        rest = command
        for match in SED_RX.finditer(command):
            lo, hi = int(match.group(1)), int(match.group(2))
            if self.outside(match.group(3), lo, hi):
                classes.append("ranged_read_outside_flagged_ranges")
                rest = rest.replace(match.group(0), "")
            else:
                classes.append("OTHER_sed_inside_flagged_range")
        ranged = bool(classes) and classes[-1].startswith("ranged")
        pathspec = re.search(r"':!\S+'", rest) is not None
        rest = re.sub(r"':!\S+'", "", rest)
        left = [d for d in q6 if d.rstrip("/") in rest]
        if not left:
            if pathspec or not ranged:
                classes.append("named_only_as_excluded_pathspec_or_range")
        elif any(CODEBOOK_DIR.rstrip("/") in d for d in left):
            classes.append("codebook_structure_or_counts_only")
        elif GIT_METADATA_RX.search(command):
            classes.append("git_metadata_only")
        elif (
            "track_b_b0_1_exposure_inventory" in command
            or "EXCL" in command
            or "TWENTY" in command
        ):
            classes.append("mechanical_scan_or_exclusion_list")
        elif "cat > tests/" in command:
            classes.append("named_in_code_written")
        elif "grep" in command and all(
            _only_quoted(rest, d.rstrip("/")) for d in left
        ):
            classes.append("named_in_grep_pattern_or_filter")
        else:
            classes.append("OTHER")
        return sorted(set(classes))


def _only_quoted(text: str, name: str) -> bool:
    """Whether every occurrence of ``name`` lies inside a quoted string."""
    spans = [m.span() for m in re.finditer(r'"[^"]*"|\'[^\']*\'', text)]
    hits = [m.start() for m in re.finditer(re.escape(name), text)]
    return bool(hits) and all(any(a < h < b for a, b in spans) for h in hits)


def _agent(name: str, archive: zipfile.ZipFile) -> str:
    if name == "transcript.jsonl":
        return "main"
    meta = json.loads(archive.read(name.replace(".jsonl", ".meta.json")))
    workflow = name.split("/workflows/")[1].split("/")[0]
    return f"{workflow}:{meta.get('description')}"


def _transcripts(archive: zipfile.ZipFile) -> list[str]:
    return sorted(
        name
        for name in archive.namelist()
        if name == "transcript.jsonl"
        or ("/subagents/" in name and name.endswith(".jsonl"))
        and not name.endswith("journal.jsonl")
    )


def extract(archive: zipfile.ZipFile, checker: Checker) -> dict[str, Any]:
    calls: list[dict[str, Any]] = []
    flagged: list[int] = []
    for name in _transcripts(archive):
        agent = _agent(name, archive)
        for line in archive.read(name).decode("utf-8").splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            message = event.get("message")
            if not isinstance(message, dict):
                continue
            content = message.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not (
                    isinstance(block, dict) and block.get("type") == "tool_use"
                ):
                    continue
                given = block.get("input") or {}
                rec: dict[str, Any] = {
                    "agent": agent,
                    "utc": event.get("timestamp"),
                    "tool": block.get("name"),
                }
                paths: list[str] = []
                for key in INPUT_KEYS:
                    if key in given:
                        rec[key] = given[key]
                        if key in ("file_path", "path"):
                            paths.append(str(given[key]))
                command = str(given.get("command", ""))
                if "command" in given:
                    rec["command_first_line"] = (
                        command.splitlines()[0][:300] if command else ""
                    )
                    rec["command_sha256"] = hashlib.sha256(
                        command.encode()
                    ).hexdigest()
                    named = sorted(
                        set(ABSOLUTE_RX.findall(command))
                        | set(RELATIVE_RX.findall(command))
                    )
                    rec["paths_named"] = named
                    paths += named
                hits = sorted({h for p in paths for h in checker.flags(p)})
                if hits:
                    rec["flags"] = hits
                    rec["flag_class"] = checker.classify(rec, command, hits)
                    note = OVERRIDES.get(rec.get("command_sha256", ""))
                    if note and rec["flag_class"] == ["OTHER"]:
                        rec["flag_class"] = [note[0]]
                        rec["flag_note"] = note[1]
                    flagged.append(len(calls))
                calls.append(rec)
    return {"calls": calls, "flagged_call_indices": flagged}


def write(record: Mapping[str, Any], out: Path) -> None:
    """One call per line, so the record diffs line by line."""
    head = {k: v for k, v in record.items() if k != "calls"}
    text = json.dumps(head, indent=1, sort_keys=True)
    body = ",\n".join(
        "  " + json.dumps(call, sort_keys=True, ensure_ascii=False)
        for call in record["calls"]
    )
    text = text[:-2] + ',\n "calls": [\n' + body + "\n ]\n}\n"
    json.loads(text)
    with out.open("x", encoding="utf-8") as stream:
        stream.write(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("export", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    inventories = [json.loads((ROOT / p).read_text()) for p in INVENTORIES]
    denied = {e["path"] for inv in inventories for e in inv["q6_exclusions"]}
    restricted = restricted_prefixes(
        Path(EV, "RESTRICTED-FILES.md").read_text(encoding="utf-8")
    )
    checker = Checker(restricted, denied, flagged_ranges(inventories))
    with zipfile.ZipFile(args.export) as archive:
        found = extract(archive, checker)
    classes: dict[str, int] = {}
    for index in found["flagged_call_indices"]:
        for name in found["calls"][index]["flag_class"]:
            classes[name] = classes.get(name, 0) + 1
    record = {
        "schema": SCHEMA,
        "source": {
            "export": args.export.name,
            "sha256": hashlib.sha256(args.export.read_bytes()).hexdigest(),
        },
        "method": (
            "tool-call inputs from the session's transcript export; no tool "
            "output is read or recorded"
        ),
        "restricted_entries_checked": len(restricted),
        "q6_paths_checked": sorted(denied | {CODEBOOK_DIR}),
        "flagged_ranges": flagged_ranges(inventories),
        "n_calls": len(found["calls"]),
        "flag_classes": dict(sorted(classes.items())),
        **found,
    }
    write(record, args.out)
    print(json.dumps({"n_calls": record["n_calls"], **classes}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
