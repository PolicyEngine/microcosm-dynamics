#!/usr/bin/env python3
"""Track B B0.1 addendum: build and audit the Q6 blinded-review root.

Max's ruling d693 set the form of the addendum's blinded review (Q6): an
independent read-only lane on a cleaned root. This script has two commands.

``build`` extracts ``git archive`` of one commit into a new directory that
is not a git repository, and removes, whole:

- every file on the audit's Q6 exclusion list and every further file the
  exposure inventory flags when rerun at that commit;
- ``data/external/psid_codebook_field_evidence/``, whose code maps carry
  frequency columns for B2's 2012 and 2014 labor-income variables;
- any other file that holds both a code map and frequencies, unless it
  is named with ``--allow``. An allowed file must be one this pull
  request adds or changes (``git diff --name-only BASE HEAD``), and the
  record lists it. The token test cannot tell a codebook table from code
  or records that name the tokens, such as this script.

It then copies in the named context files, refuses the root if a denied
path or a code map with frequencies remains, and writes a manifest of
every file with its SHA-256.

``readlog`` reads a review lane's stream-json transcript and lists every
path its tool calls named and every path its Glob and Grep results
returned. A review counts only if all of them lie inside the root. With
``--format codex`` it reads a Codex lane's ``exec --json`` events instead,
whose tools are shell commands run from the root, and flags every command
word that leaves the root: an absolute path outside it, a home path or a
``..`` segment.

Neither command prints file content. Listed files are removed by path,
unread. The codebook check reads each remaining file only to test for the
two tokens.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tarfile
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "track_b_b0_1_review_root.v1"
CODEBOOK_DIR = "data/external/psid_codebook_field_evidence"
CONTEXT_DIR = "_review_context"
#: A file holding both of these is a codebook table and is removed.
CODE_MAP_RX = re.compile(r"code_map", re.IGNORECASE)
FREQUENCY_RX = re.compile(r"frequenc", re.IGNORECASE)
#: Tool-call fields of the read-only lane that name a path or a pattern.
PATH_FIELDS = ("file_path", "path", "pattern", "glob")
ABSOLUTE_RX = re.compile(r"(/(?:Users|private|tmp|var|opt|etc)/[^\s\"'<>:]+)")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def denied_paths(inventories: Iterable[Mapping[str, Any]]) -> list[str]:
    """Every inventoried exclusion, whole, whatever its listed scope."""
    paths: set[str] = set()
    for inventory in inventories:
        for entry in inventory["q6_exclusions"]:
            paths.add(str(entry["path"]))
    return sorted(paths)


def remove_denied(root: Path, denied: Sequence[str]) -> list[str]:
    """Delete the denied files and the codebook directory from ``root``."""
    removed: list[str] = []
    for relative in denied:
        target = root / relative
        if target.is_file():
            target.unlink()
            removed.append(relative)
    codebook = root / CODEBOOK_DIR
    if codebook.is_dir():
        for path in sorted(codebook.rglob("*")):
            if path.is_file():
                removed.append(path.relative_to(root).as_posix())
        shutil.rmtree(codebook)
    return sorted(removed)


def codebook_tables(root: Path, allowed: Sequence[str] = ()) -> list[str]:
    """Files under ``root`` that hold a code map and frequencies."""
    hits: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or CONTEXT_DIR in path.parts:
            continue
        if path.relative_to(root).as_posix() in allowed:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if CODE_MAP_RX.search(text) and FREQUENCY_RX.search(text):
            hits.append(path.relative_to(root).as_posix())
    return hits


def manifest(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): _sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def changed_files(base: str, head: str) -> set[str]:
    """Files the pull request adds or changes between ``base`` and ``head``."""
    listed = subprocess.run(
        ["git", "diff", "--name-only", base, head],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return {line for line in listed.splitlines() if line}


def build(
    head: str,
    out: Path,
    inventories: Sequence[Path],
    context: Mapping[str, Path],
    allowed: Sequence[str] = (),
    base: str | None = None,
) -> dict[str, Any]:
    if allowed:
        if base is None:
            raise ValueError("--allow needs --base")
        outside = sorted(set(allowed) - changed_files(base, head))
        if outside:
            raise ValueError(f"not changed by this pull request: {outside}")
    out = out.resolve()
    if out.exists():
        raise FileExistsError(f"{out} exists")
    if out.is_relative_to(ROOT):
        raise RuntimeError("the review root must be outside the repository")
    out.mkdir(parents=True)
    archive = out.parent / f"{out.name}.tar"
    subprocess.run(
        ["git", "archive", "--format=tar", "-o", str(archive), head],
        cwd=ROOT,
        check=True,
    )
    with tarfile.open(archive) as tar:
        tar.extractall(out, filter="data")
    archive.unlink()
    denied = denied_paths(
        json.loads(path.read_text(encoding="utf-8")) for path in inventories
    )
    removed = remove_denied(out, denied)
    denied_set = set(denied)
    if denied_set & set(allowed):
        raise ValueError("an allowed file is on an exclusion list")
    tables = codebook_tables(out, allowed)
    for relative in tables:
        (out / relative).unlink()
    context_dir = out / CONTEXT_DIR
    context_dir.mkdir()
    copies: dict[str, dict[str, str]] = {}
    for name, source in sorted(context.items()):
        target = context_dir / name
        shutil.copyfile(source, target)
        copies[name] = {"source": str(source), "sha256": _sha256(target)}
    remaining = [p for p in denied if (out / p).exists()]
    if (
        remaining
        or (out / CODEBOOK_DIR).exists()
        or codebook_tables(out, allowed)
    ):
        raise AssertionError("a denied path or codebook table remains")
    if (out / ".git").exists():
        raise AssertionError("the review root holds a git directory")
    files = manifest(out)
    return {
        "schema": SCHEMA,
        "head": head,
        "root": str(out),
        "denied_paths": denied,
        "removed": removed,
        "removed_codebook_tables": tables,
        "codebook_check_allowed": sorted(allowed),
        "base": base,
        "context_copies": copies,
        "n_files": len(files),
        "manifest_sha256": hashlib.sha256(
            json.dumps(files, sort_keys=True).encode()
        ).hexdigest(),
    }


def _strings(node: Any) -> Iterable[str]:
    if isinstance(node, str):
        yield node
    elif isinstance(node, Mapping):
        for value in node.values():
            yield from _strings(value)
    elif isinstance(node, list | tuple):
        for value in node:
            yield from _strings(value)


#: The harness's notice when a tool result is too large to return inline.
PERSISTED_RX = re.compile(r"(?:Full output saved to|saved to):?\s+(/\S+)")


def _result_paths(name: str | None, text: str) -> list[str]:
    """Paths a Glob or Grep result returned: each line's leading path.

    A Read result is file content, so paths quoted in it are not reads.
    A result whose call is unknown is treated like a Grep result.
    """
    if name not in (None, "Glob", "Grep"):
        return []
    out = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("/"):
            out.append(re.split(r":\d", line, maxsplit=1)[0].rstrip(":"))
    return out


def read_log(
    transcript: Path, root: Path, denied: Sequence[str]
) -> dict[str, Any]:
    """Every path a review lane's tool calls named or its results returned.

    ``transcript`` is the lane's stream-json record: one JSON object per
    line. Tool calls are ``tool_use`` blocks; results are ``tool_result``
    blocks. A call's path fields must lie inside the root and outside the
    denied paths; so must every path a Glob or Grep result returns. Paths
    quoted inside a file the lane read are content, not reads. When the
    harness saves an oversized result outside the root, the log records
    the notice; the review is void only if a later call opens that file.
    No content is copied into the log, only paths.
    """
    root = root.resolve()
    calls: list[dict[str, Any]] = []
    names: dict[str, str] = {}
    named: set[str] = set()
    returned: set[str] = set()
    persisted: set[str] = set()
    for line in transcript.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        content = event.get("message", {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, Mapping):
                continue
            if block.get("type") == "tool_use":
                names[str(block.get("id"))] = str(block.get("name"))
                fields = {
                    key: str(value)
                    for key, value in (block.get("input") or {}).items()
                    if key in PATH_FIELDS
                }
                calls.append({"tool": block.get("name"), **fields})
                for key in ("file_path", "path"):
                    if key in fields:
                        named.add(fields[key])
            elif block.get("type") == "tool_result":
                name = names.get(str(block.get("tool_use_id")))
                for text in _strings(block.get("content")):
                    found = set(PERSISTED_RX.findall(text))
                    persisted.update(found)
                    returned.update(
                        p for p in _result_paths(name, text) if p not in found
                    )

    def classify(path: str) -> str:
        resolved = Path(path)
        if not resolved.is_absolute():
            resolved = root / path
        try:
            relative = resolved.resolve().relative_to(root)
        except ValueError:
            return "outside_root"
        if relative.as_posix() in set(
            denied
        ) or relative.as_posix().startswith(CODEBOOK_DIR):
            return "denied"
        return "inside_root"

    paths = {path: classify(path) for path in sorted(named | returned)}
    bad = sorted(path for path, kind in paths.items() if kind != "inside_root")
    return {
        "schema": "track_b_b0_1_review_read_log.v2",
        "root": str(root),
        "n_tool_calls": len(calls),
        "tool_calls": calls,
        "paths": paths,
        "harness_persisted_outputs": sorted(persisted),
        "persisted_outputs_opened": sorted(persisted & named),
        "paths_outside_root_or_denied": bad,
        "review_counts": not bad,
    }


#: A shell word that names a path outside the working directory: an
#: absolute path, a home-relative one, or any ``..`` segment.
_ESCAPE_RX = re.compile(r"(?:^|/)\.\.(?:/|$)")
#: Executables in the system's bin directories. In program position they
#: are programs, not data the lane reads.
_PROGRAM_RX = re.compile(
    r"^(?:/(?:usr/(?:local/)?)?s?bin/[^/]+|/opt/homebrew/bin/[^/]+)$"
)
#: Devices a command may write to or read nothing from.
_DEVICES = frozenset({"/dev/null", "/dev/stdout", "/dev/stderr"})


#: A shell expansion: $NAME, ${...}, $(...), ANSI-C $'...', locale
#: $"..." or a backquote.
_EXPANSION_RX = re.compile(r"\$(?:[A-Za-z_][A-Za-z0-9_]*|\{|\(|'|\")|`")


def _expansions(script: str) -> list[str]:
    """Shell expansions in ``script`` that are not inside single quotes.

    Inside single quotes the shell expands nothing (``sed -n '1,$p'``);
    bare or inside double quotes it does. A backslash escapes the next
    character outside single quotes.
    """
    found: list[str] = []
    state = None  # None, "'" or '"'
    index = 0
    while index < len(script):
        char = script[index]
        if state == "'":
            if char == "'":
                state = None
        elif char == "\\":
            index += 2
            continue
        elif char == "'" and state is None:
            state = "'"
        elif char == '"':
            state = None if state == '"' else '"'
        else:
            match = _EXPANSION_RX.match(script, index)
            if match:
                found.append(match.group(0))
        index += 1
    return found


def _shell_words(command: str) -> list[str]:
    """Split a shell command into words, keeping quoted text together.

    ``shlex`` fails on unbalanced quotes; the fallback is a plain split, so
    a malformed command is still scanned word by word.
    """
    import shlex

    try:
        return shlex.split(command, posix=True)
    except ValueError:
        return command.split()


#: Programs that run their ``-c`` argument as a shell script.
_SHELLS = frozenset({"sh", "bash", "zsh", "dash", "ksh", "fish"})


def _scripts(command: str) -> list[str]:
    """The shell scripts inside ``command``, at every depth.

    After a shell program (``sh``, ``bash``, ``zsh`` and the like), every
    later word is treated as a script, whatever options come between
    (``bash -o errexit -c '...'``). So are the words after ``eval``. Each
    is split again for nested shells. Code given to other interpreters
    (``python3 -c``) is not a shell script, so its dollars are not
    expansions; its paths are still scanned by ``_path_words``.
    """
    found: list[str] = []
    words = _shell_words(command)
    for index, word in enumerate(words):
        name = word.rsplit("/", 1)[-1]
        if name == "eval" and index + 1 < len(words):
            script = " ".join(words[index + 1 :])
            found.append(script)
            found.extend(_scripts(script))
            break
        if name in _SHELLS:
            for script in words[index + 1 :]:
                found.append(script)
                if re.search(r"\s", script):
                    found.extend(_scripts(script))
            break
    return found


#: Tokens that end a simple command, so the next word is a program.
_SEPARATORS = frozenset({";", "&&", "||", "|", "&", "(", ")", "\n"})
#: Commands that change the working directory.
_DIRECTORY_CHANGES = frozenset({"cd", "pushd", "popd", "chdir"})


def _program_words(script: str) -> set[str]:
    """The words of ``script`` in program position.

    That is each simple command's first word, after any ``NAME=value``
    assignments and an ``env`` or ``command`` prefix, split at shell
    separators.
    """
    import shlex

    lexer = shlex.shlex(script, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        tokens = script.split()
    programs: set[str] = set()
    expect = True
    for token in tokens:
        if token in _SEPARATORS or set(token) <= set(";&|()"):
            expect = True
            continue
        if expect:
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", token):
                continue
            if token in ("env", "command", "exec", "nice"):
                programs.add(token)
                continue
            programs.add(token)
            expect = False
    return programs


def _path_words(command: str) -> list[str]:
    """Words of a shell command, and of any ``-c`` script inside it, that
    could name a path: every word, split again at ``=``, ``:``, brace
    expansion's ``{``, ``,`` and ``}`` and shell separators, so
    ``--out=/x``, ``a:/x``, ``{a,/x}`` and ``cd /x;ls`` are seen."""
    words: list[str] = []
    for word in _shell_words(command):
        if re.search(r"\s", word):
            # A script or code: its own words are the candidates.
            words.extend(_path_words(word))
            continue
        for piece in re.split(r"[=:;&|()<>`{},]", word):
            piece = piece.strip().strip("'\"")
            if piece:
                words.append(piece)
    return words


def read_log_codex(
    transcript: Path, root: Path, denied: Sequence[str]
) -> dict[str, Any]:
    """The read log for a Codex review lane, whose tools are shell commands.

    ``transcript`` is ``codex exec --json``'s event stream: one JSON object
    per line, each command an ``item`` of type ``command_execution``. The
    lane runs with the root as its working directory. Each command, and
    each shell script inside it at every depth, is scanned, and any of
    these voids the review:

    - a word that leaves the root or names a denied path: an absolute
      path (an executable in a system bin directory is exempt only in
      program position), a ``..`` segment, or any word starting with
      ``~``;
    - an unquoted shell expansion: ``$NAME``, ``${...}``, ``$(...)``,
      ``$'...'``, ``$"..."``, a backquote, or zsh's ``=program``;
    - a directory change (``cd``, ``pushd``, ``popd``).

    A relative word resolves inside the root, where no denied file exists,
    so naming a denied file there reads nothing. Brace expansion is split
    into its parts, and words are re-split at any whitespace.

    This is a conservative detector for shell lanes, not a sandbox. It
    cannot see a path a program builds at run time
    (``open('/' + 'etc')`` in Python code), so it cannot certify a shell
    lane as blind. The Q6 review of record runs on a lane with no shell
    (d693); this log supplements reviews on other lanes. Command output is
    not read. No content is copied into the log, only commands.
    """
    root = root.resolve()
    denied_set = set(denied)
    commands: list[str] = []
    seen: set[tuple[str, str]] = set()
    for line in transcript.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item") if isinstance(event, Mapping) else None
        if not isinstance(item, Mapping):
            continue
        if item.get("type") != "command_execution":
            continue
        identifier = str(item.get("id", len(commands)))
        command = str(item.get("command", ""))
        if (identifier, command) in seen:
            continue
        seen.add((identifier, command))
        commands.append(command)

    def classify(word: str, programs: set[str]) -> str | None:
        absolute = word.startswith("/")
        if word in _DEVICES:
            return None
        if absolute and _PROGRAM_RX.match(word) and word in programs:
            return None
        if not absolute and not _ESCAPE_RX.search(word):
            # Resolves inside the root, where no denied file exists.
            return None
        target = Path(word) if absolute else root / word
        try:
            relative = target.resolve().relative_to(root).as_posix()
        except ValueError:
            return "outside_root"
        if relative in denied_set or relative.startswith(CODEBOOK_DIR):
            return "denied"
        return "inside_root"

    flagged: dict[str, str] = {}
    for command in commands:
        scripts = _scripts(command)
        programs: set[str] = set()
        for script in [command, *scripts]:
            programs |= _program_words(script)
        # Unquoted expansions in a shell script cannot be resolved here.
        for script in scripts:
            for expansion in _expansions(script):
                flagged[expansion] = "shell_expansion"
        # A directory change moves the working directory off the root.
        for program in programs:
            if program.rsplit("/", 1)[-1] in _DIRECTORY_CHANGES:
                flagged[program] = "directory_change"
        for script in [command, *scripts]:
            for word in _shell_words(script):
                for piece in re.split(r"[;&|()<>{},]", word):
                    if piece.startswith("~"):
                        # Tilde expansion: a home directory, any user's.
                        flagged[piece] = "outside_root"
                if re.fullmatch(r"=[A-Za-z0-9_.+-]+", word):
                    # zsh's =program expands to the program's path.
                    flagged[word] = "shell_expansion"
        for word in _path_words(command):
            kind = classify(word, programs)
            if kind not in (None, "inside_root"):
                flagged[word] = kind
    return {
        "schema": "track_b_b0_1_review_read_log_codex.v2",
        "root": str(root),
        "n_commands": len(commands),
        "commands": commands,
        "paths_outside_root_or_denied": sorted(flagged),
        "flagged_kinds": dict(sorted(flagged.items())),
        "review_counts": not flagged,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    b = commands.add_parser("build")
    b.add_argument("--head", required=True)
    b.add_argument("--out", type=Path, required=True)
    b.add_argument("--inventory", type=Path, action="append", required=True)
    b.add_argument("--context", action="append", default=[])
    b.add_argument("--record", type=Path, required=True)
    b.add_argument("--allow", action="append", default=[])
    b.add_argument("--base")
    r = commands.add_parser("readlog")
    r.add_argument("--transcript", type=Path, required=True)
    r.add_argument("--root", type=Path, required=True)
    r.add_argument("--root-record", type=Path, required=True)
    r.add_argument("--record", type=Path, required=True)
    r.add_argument(
        "--format",
        choices=("claude", "codex"),
        default="claude",
        help="the lane's transcript format (default: claude stream-json)",
    )
    args = parser.parse_args(argv)
    if args.command == "build":
        context = {}
        for item in args.context:
            name, _, source = item.partition("=")
            context[name] = Path(source)
        record = build(
            args.head,
            args.out,
            args.inventory,
            context,
            allowed=args.allow,
            base=args.base,
        )
    else:
        denied = json.loads(args.root_record.read_text(encoding="utf-8"))[
            "denied_paths"
        ]
        reader = read_log_codex if args.format == "codex" else read_log
        record = reader(args.transcript, args.root, denied)
    with args.record.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=1, sort_keys=True)
        stream.write("\n")
    print(
        json.dumps({k: v for k, v in record.items() if k.startswith("n_")}),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
