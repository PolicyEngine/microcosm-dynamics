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
- any other file that holds both a code map and frequencies.

It then copies in the named context files, refuses the root if a denied
path or a code map with frequencies remains, and writes a manifest of
every file with its SHA-256.

``readlog`` reads a review lane's stream-json transcript and lists every
path its tool calls named and every path its tool results returned. A
review counts only if all of them lie inside the root.

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


def codebook_tables(root: Path) -> list[str]:
    """Files under ``root`` that hold a code map and frequencies."""
    hits: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or CONTEXT_DIR in path.parts:
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


def build(
    head: str,
    out: Path,
    inventories: Sequence[Path],
    context: Mapping[str, Path],
) -> dict[str, Any]:
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
    tables = codebook_tables(out)
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
    if remaining or (out / CODEBOOK_DIR).exists() or codebook_tables(out):
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


def read_log(
    transcript: Path, root: Path, denied: Sequence[str]
) -> dict[str, Any]:
    """Every path a review lane's tool calls named or its results returned.

    ``transcript`` is the lane's stream-json record: one JSON object per
    line. Tool calls are ``tool_use`` blocks; results are ``tool_result``
    blocks. No content is copied into the log, only paths.
    """
    root = root.resolve()
    calls: list[dict[str, Any]] = []
    named: set[str] = set()
    returned: set[str] = set()
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
                for text in _strings(block.get("content")):
                    returned.update(ABSOLUTE_RX.findall(text))

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
        "schema": "track_b_b0_1_review_read_log.v1",
        "root": str(root),
        "n_tool_calls": len(calls),
        "tool_calls": calls,
        "paths": paths,
        "paths_outside_root_or_denied": bad,
        "review_counts": not bad,
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
    r = commands.add_parser("readlog")
    r.add_argument("--transcript", type=Path, required=True)
    r.add_argument("--root", type=Path, required=True)
    r.add_argument("--root-record", type=Path, required=True)
    r.add_argument("--record", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "build":
        context = {}
        for item in args.context:
            name, _, source = item.partition("=")
            context[name] = Path(source)
        record = build(args.head, args.out, args.inventory, context)
    else:
        denied = json.loads(args.root_record.read_text(encoding="utf-8"))[
            "denied_paths"
        ]
        record = read_log(args.transcript, args.root, denied)
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
