#!/usr/bin/env python3
"""Track B B0.1 addendum: the authoring session's reads record.

Reads a Claude Code session export (the zip the desktop app's Export
writes) and records every tool call of the session and of its subagents:
the tool, the time, the path, range or pattern it named, and for a shell
command its first line, its SHA-256 and the paths it names. It records
no tool output and reads none.

Each call that names a path on `RESTRICTED-FILES.md` or on either exposure
inventory's Q6 exclusion list (plus the codebook-evidence folder) is
flagged and classified by the rules in ``classify``. So is a shell
command whose recursive grep, ``git grep`` or glob covers an excluded
path without naming it (``Checker.scope``). For those the extractor reads
the call's output only to count the lines that begin with an excluded
file's path, and records that count. Python code that walks the tree is
not parsed; it is flagged only when it names an excluded path. A flagged
call's full command text is kept, so each classification can be
checked. Calls the rules cannot place are classified by hand in
``OVERRIDES``, keyed by the command's SHA-256, with a note saying what
was checked.

    python scripts/track_b_b0_1_addendum_reads.py EXPORT.zip \\
        --out docs/design/track_b_b0_1_addendum_reads.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import zipfile
from collections.abc import Iterable, Mapping
from fnmatch import fnmatch
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
WORKTREE_MARK = "/_worktrees/dynamics-trackb-b01-addendum-20260930"
SEGMENT_RX = re.compile(r"&&|\|\||[;|\n]")
GLOB_CHARS = set("*?[")
#: grep options that take the next token as their argument.
GREP_ARG_OPTIONS = {"-e", "-f", "-m", "-A", "-B", "-C", "--regexp"}
NAMES_OR_COUNTS = {"-l", "-L", "-c", "-q", "--count", "--files-with-matches"}
#: Subfleet jobs this session dispatched. `RESTRICTED-FILES.md` lets a
#: session read its own job folder under ~/.subfleet/.
OWN_JOBS = ("20261001-115147-b01-addendum-q6",)
#: Calls the rules cannot classify, checked by hand: the inputs, and for
#: the second only the line numbers its output printed. The code-string
#: entries name a path only as a string in code or prose the session
#: wrote, and open nothing on either list.
OVERRIDES = {
    "b205f71e2b0fc7046d5efbddfbaf0daba88f5f048d6cb4fecd41ad93b933b58e": (
        "named_as_string_in_code",
        "the first reads extractor: EV, REFS and the codebook folder are "
        "constants; it opens RESTRICTED-FILES.md (the list) and the two "
        "inventories",
    ),
    "141cd813645a06af7740db0eaf50d38d48241333a60ee67b75ec7a480d18e168": (
        "named_as_string_in_code",
        "the shared project folder's prefix is a string used to shorten "
        "printed paths; the script opens only the draft reads record",
    ),
    "e6ce98666254dd587b964df9b8809402233d7ee0794d0f04ce0f74b55356b5e0": (
        "named_as_string_in_code",
        "gates.yaml is an endswith() filter over the reads record",
    ),
    "8daf69586fef91a36e5e47ca3963787932c0c6f1b75209eb09dca17567aa135d": (
        "named_as_string_in_code",
        "gates.yaml appears in addendum prose being written",
    ),
    "03259aa66fcf8d0dde25b695c74e624054b8cd8ac536ade37e0f94698f505425": (
        "named_as_string_in_code",
        "gates.yaml is a test fixture value for the allow-list check",
    ),
    "2b620b91b77bb2ca9720cd4f47f71c57be047ef4255e05e7e03f7b1ba3632c34": (
        "named_as_string_in_code",
        "gates.yaml appears in sample commands given to a tokenizer",
    ),
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


def _relative(token: str) -> str | None:
    """A worktree path relative to the worktree, or None if elsewhere."""
    token = token.strip().strip("'\"")
    if WORKTREE_MARK + "/" in token:
        token = token.split(WORKTREE_MARK + "/", 1)[1]
    elif token.endswith(WORKTREE_MARK):
        token = "."
    elif token.startswith(("/", "~", "$")):
        return None
    if token.startswith("./"):
        token = token[2:]
    return token or "."


def _covers(scope: str, path: str, recursive: bool) -> bool:
    path = path.rstrip("/")
    scope = scope.rstrip("/") or "."
    if GLOB_CHARS & set(scope):
        return fnmatch(path, scope)
    if scope == ".":
        return recursive
    return path == scope or (recursive and path.startswith(scope + "/"))


def _segments(command: str) -> list[list[str]]:
    """The command's simple commands, split at ; | & and newlines.

    Quoted text stays whole, so a ``|`` inside a grep pattern does not
    split. If the quoting does not parse (a heredoc body, say), each line
    is split at the operators instead.
    """
    try:
        lex = shlex.shlex(command, posix=True, punctuation_chars="();<>|&\n")
        lex.whitespace = " \t\r"
        lex.whitespace_split = True
        out: list[list[str]] = [[]]
        for token in lex:
            if token and set(token) <= set(";|&\n"):
                out.append([])
            else:
                out[-1].append(token)
    except ValueError:
        out = [part.split() for part in SEGMENT_RX.split(command)]
    return [tokens for tokens in out if tokens]


def _names_or_counts(args: list[str]) -> bool:
    return any(
        a in NAMES_OR_COUNTS
        or (
            re.fullmatch(r"-[A-Za-z]+", a) is not None
            and bool(set(a[1:]) & set("lLcq"))
        )
        for a in args
    )


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
        self.all_denied = sorted(denied | {CODEBOOK_DIR})

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

    def _grep(self, prog: str, args: list[str]) -> set[str]:
        recursive = prog == "rg" or any(
            a in ("-r", "-R", "--recursive")
            or (
                re.fullmatch(r"-[A-Za-z]+", a) is not None
                and bool(set(a[1:]) & set("rR"))
            )
            for a in args
        )
        includes = [
            a.split("=", 1)[1].strip("'\"")
            for a in args
            if a.startswith("--include=")
        ]
        positional: list[str] = []
        explicit_pattern = False
        skip = False
        for a in args:
            if skip:
                skip = False
                continue
            if a in GREP_ARG_OPTIONS:
                explicit_pattern |= a in ("-e", "-f", "--regexp")
                skip = True
                continue
            if a.startswith("-"):
                continue
            positional.append(a)
        targets = positional if explicit_pattern else positional[1:]
        if not targets and recursive:
            targets = ["."]
        covered: set[str] = set()
        for target in targets:
            scope = _relative(target)
            if scope is None:
                continue
            hit = {
                d
                for d in self.all_denied
                if (GLOB_CHARS & set(scope) or recursive)
                and _covers(scope, d, recursive)
            }
            if includes:
                # The codebook folder holds JSON files only.
                hit = {
                    d
                    for d in hit
                    if any(
                        fnmatch(
                            (
                                "x.json"
                                if d.endswith("/")
                                else d.rstrip("/").split("/")[-1]
                            ),
                            inc,
                        )
                        for inc in includes
                    )
                }
            covered |= hit
        return covered

    def _git_grep(self, args: list[str]) -> set[str]:
        specs = args[args.index("--") + 1 :] if "--" in args else []
        positive = [s for s in specs if not s.startswith(":")]
        excluded = [
            s[2:] if s.startswith(":!") else s.split(")", 1)[-1]
            for s in specs
            if s.startswith((":!", ":(exclude)"))
        ]
        positive = positive or ["."]
        return {
            d
            for d in self.all_denied
            if any(_covers(p, d, True) for p in positive)
            and not any(_covers(e, d, True) for e in excluded)
        }

    def scope(self, command: str) -> tuple[list[str], bool]:
        """Excluded paths a command's recursive or glob scope covers.

        Returns the covered paths and whether every covering command
        prints only names or counts.
        """
        covered: set[str] = set()
        names_only = True
        # Relative paths are the worktree's until a cd leaves it. A cd to
        # an unresolved variable is assumed to stay, which over-flags.
        in_worktree = True
        assigned: dict[str, str] = {}
        for tokens in _segments(command):
            while tokens and re.match(r"^\w+=", tokens[0]):
                name, _, value = tokens.pop(0).partition("=")
                assigned[name] = value
            if not tokens:
                continue
            prog = tokens[0].split("/")[-1]
            if prog == "cd":
                target = tokens[1] if len(tokens) > 1 else "~"
                for name, value in assigned.items():
                    target = target.replace("${" + name + "}", value)
                    target = target.replace("$" + name, value)
                in_worktree = "$" in target or WORKTREE_MARK in target
                continue
            if not in_worktree:
                if prog == "git":
                    continue
                tokens = [tokens[0]] + [
                    t if t.startswith(("-", "/")) else "/elsewhere/" + t
                    for t in tokens[1:]
                ]
            hit: set[str] = set()
            if prog == "git" and tokens[1:2] == ["grep"]:
                hit = self._git_grep(tokens[2:])
            elif prog in ("grep", "egrep", "rg"):
                hit = self._grep(prog, tokens[1:])
            elif prog in ("cat", "head", "tail", "sed", "awk", "wc", "ls"):
                for token in tokens[1:]:
                    scope = _relative(token)
                    if scope and GLOB_CHARS & set(scope):
                        hit |= {
                            d
                            for d in self.all_denied
                            if _covers(scope, d, False)
                        }
            elif prog == "find" and len(tokens) > 1:
                scope = _relative(tokens[1])
                if scope:
                    hit = {
                        d for d in self.all_denied if _covers(scope, d, True)
                    }
            if hit:
                covered |= hit
                names_only &= prog == "find" or _names_or_counts(tokens[1:])
        return sorted(covered), names_only

    def excluded_output_lines(self, text: str) -> int:
        """Output lines that begin with an excluded file's path."""
        n = 0
        for line in text.splitlines():
            head = _relative(line.split(":", 1)[0])
            if head and any(
                _covers(d.rstrip("/"), head, d.endswith("/"))
                for d in self.all_denied
            ):
                n += 1
        return n

    def outside(self, name: str, lo: int, hi: int) -> bool:
        return all(hi < a or lo > b for a, b in self.ranges.get(name, []))

    def classify(
        self, rec: Mapping[str, Any], command: str, hits: list[str]
    ) -> list[str]:
        q6 = [h[3:] for h in hits if h.startswith("q6:")]
        classes: list[str] = []
        named_all = [rec.get("file_path") or ""] + rec.get("paths_named", [])
        for hit in (h for h in hits if h.startswith("restricted:")):
            if "/.claude/projects/" in hit:
                named = [p for p in named_all if "/.claude/projects/" in p]
                own = named and all(OWN_SUBFOLDER in p for p in named)
                classes.append(
                    "own_transcript_subfolder" if own else "OTHER_restricted"
                )
            elif hit.rstrip("/").endswith("/.subfleet"):
                named = [p for p in named_all if "/.subfleet/" in p]
                own = named and all(
                    any(f"/.subfleet/jobs/{job}" in p for job in OWN_JOBS)
                    for p in named
                )
                classes.append(
                    "own_subfleet_job_folder" if own else "OTHER_restricted"
                )
            else:
                classes.append("OTHER_restricted")
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
        scoped: dict[str, dict[str, Any]] = {}
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
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_result":
                    rec = scoped.pop(str(block.get("tool_use_id")), None)
                    if rec is not None:
                        text = block.get("content")
                        if not isinstance(text, str):
                            text = "\n".join(
                                str(x.get("text", ""))
                                for x in text or []
                                if isinstance(x, dict)
                            )
                        _finish_scope(rec, checker.excluded_output_lines(text))
                    continue
                if block.get("type") != "tool_use":
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
                covered, names_only = checker.scope(command)
                if hits or covered:
                    rec["flags"] = hits + ["scope:" + d for d in covered]
                    rec["flag_class"] = (
                        checker.classify(rec, command, hits) if hits else []
                    )
                    note = OVERRIDES.get(rec.get("command_sha256", ""))
                    if note and any(
                        c.startswith("OTHER") for c in rec["flag_class"]
                    ):
                        rec["flag_class"] = sorted(
                            {
                                c
                                for c in rec["flag_class"]
                                if not c.startswith("OTHER")
                            }
                            | {note[0]}
                        )
                        rec["flag_note"] = note[1]
                    rec["command"] = command
                    if covered:
                        rec["scope_names_or_counts_only"] = names_only
                        scoped[str(block.get("id"))] = rec
                        _finish_scope(rec, None)
                    flagged.append(len(calls))
                calls.append(rec)
        for rec in scoped.values():
            # The call's result never reached the transcript: its agent
            # was stopped, so nothing was printed to it.
            rec["flag_class"] = sorted(
                {
                    c
                    for c in rec["flag_class"]
                    if not c.startswith("OTHER_scope")
                }
                | {"scope_no_result_in_transcript"}
            )
    return {"calls": calls, "flagged_call_indices": flagged}


def _finish_scope(rec: dict[str, Any], lines: int | None) -> None:
    """Classify a scope-flagged call; ``lines`` is None until its output."""
    rec["flag_class"] = [
        c
        for c in rec["flag_class"]
        if not c.startswith(("scope_", "OTHER_scope"))
    ]
    if lines is None:
        rec["flag_class"].append("OTHER_scope_output_not_seen")
    else:
        rec["scope_output_lines_from_excluded_files"] = lines
        if lines == 0:
            rec["flag_class"].append("scope_printed_nothing_from_excluded")
        elif rec["scope_names_or_counts_only"]:
            rec["flag_class"].append("scope_printed_names_or_counts_only")
        else:
            rec["flag_class"].append("OTHER_scope_printed_excluded_lines")
    rec["flag_class"] = sorted(set(rec["flag_class"]))


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
