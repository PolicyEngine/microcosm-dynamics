#!/usr/bin/env python3
"""Track B B0.1: mechanical inventory of pseudo-boundary exposure for B2.

The blinded review of the B0.1 audit found that the audit's hand-built
exposure list missed pseudo-boundary 2008 (whose scored periods include
reference year 2012) and prose in ``docs/design/m6_projection_engine.md``.
This script replaces the hand list with a scan of every tracked file.

It records **no line content and no JSON value** except the boundary years
themselves. For text files it records line ranges, the pattern families
that matched, and two counts per range: decimal-number tokens and the
tokens ``2012``/``2014``. For JSON files it records the collapsed key paths
of blocks keyed by a pseudo-boundary year, the field names directly under
each block, and the year-shaped keys found anywhere below it; and the
collapsed paths of ``pseudo_boundary`` fields that equal a boundary year.
For JSON string values (prose inside a JSON file) it records the collapsed
path, the pattern families and how many such strings also carry a decimal
number or a B2 target year. A JSON number is only ever compared with the
boundary years.

A reviewer can therefore run it without being exposed to any outcome.

Run from a clean worktree at the commit that adds it::

    .venv/bin/python scripts/track_b_b0_1_exposure_inventory.py \\
        --out docs/design/track_b_b0_1_exposure_inventory.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = ROOT / "runs"
SCHEMA = "track_b_b0_1_exposure_inventory.v1"

#: The train-only selectors' pseudo-boundaries
#: (``scripts/select_m6_qstar_train_only.py:114``).
PSEUDO_BOUNDARIES: tuple[int, ...] = (2006, 2008, 2010)
#: A boundary b scores reference years b, b + 2 and b + 4
#: (``scripts/select_m6_qstar_train_only.py:1444``).
SCORED_OFFSETS: tuple[int, ...] = (0, 2, 4)
#: B2's target reference years (design §3.1 row B2).
B2_TARGET_YEARS: tuple[int, ...] = (2012, 2014)

#: Pattern families. Each is searched case-insensitively on every line.
PATTERN_FAMILIES: dict[str, str] = {
    "pseudo_boundary": r"pseudo[-_ ]?boundar",
    "train_only": r"train[-_ ]only",
    "boundary_year": (
        r"boundar(?:y|ies)[\s=_:-]*20(?:06|08|10)"
        r"|\b20(?:06|08|10)[\s_-]+boundar"
        r"|\bb\s*=\s*20(?:08|10)\b"
    ),
    "selector": (
        r"\bq(?:star|\\?\*)|(?:\brho|ρ)(?:star|\\?\*)|\bJ\((?:q|ρ|rho)\)"
    ),
    "f1_mechanism": r"f1[\s_-]mechanism|m6_c3_f1",
    "frontier_figure": r"fig-m6-frontier|m6_q_frontier",
}
_FAMILY_RX = {
    name: re.compile(pattern, re.IGNORECASE)
    for name, pattern in PATTERN_FAMILIES.items()
}
#: A range whose only family is ``train_only`` is a mention of the phrase,
#: not of the pseudo-boundary selection; it can still be value-bearing if
#: it sits next to another family.
SELECTION_FAMILIES = frozenset(PATTERN_FAMILIES) - {"train_only"}
#: Inside a JSON string, a selection is named only by a pseudo-boundary
#: family, or by ``selector`` together with ``train_only``: ``q*`` and
#: ``rho*`` alone also name unrelated gate-1 and gate-2 quantities.
BOUNDARY_SPECIFIC_FAMILIES = frozenset(
    {"pseudo_boundary", "boundary_year", "f1_mechanism", "frontier_figure"}
)

#: Paths and JSON keys about marital transitions (B4's surface, not B2's).
MARITAL_RX = re.compile(
    r"marriage|married|marital|family_transitions|widow|divorc|dissol",
    re.IGNORECASE,
)
DECIMAL_RX = re.compile(r"(?<![\w.])[-−]?\d*\.\d+")
TARGET_YEAR_RX = re.compile(r"\b(?:2012|2014)\b")
YEAR_KEY_RX = re.compile(r"(?:19|20)\d\d")
RUNG_KEY_RX = re.compile(r"-?\d+\.\d+")
BOUNDARY_CONTAINER_RX = re.compile(r"boundar", re.IGNORECASE)

#: Lines of context on each side of a hit when forming a range.
CONTEXT = 5
#: Files at or below this many lines are excluded whole for Q6.
WHOLE_FILE_MAX_LINES = 500

#: The audit's own record is excluded from its own inventory.
SELF_MARKER = "track_b_b0_1"


def boundaries_touching_targets(
    boundaries: Iterable[int] = PSEUDO_BOUNDARIES,
) -> dict[str, list[int]]:
    """Boundary -> the B2 target years among its scored periods."""
    out: dict[str, list[int]] = {}
    for boundary in boundaries:
        touched = sorted(
            boundary + offset
            for offset in SCORED_OFFSETS
            if boundary + offset in B2_TARGET_YEARS
        )
        if touched:
            out[str(boundary)] = touched
    return out


def _touching_years() -> frozenset[int]:
    return frozenset(int(year) for year in boundaries_touching_targets())


# --------------------------------------------------------------------------
# Text files
# --------------------------------------------------------------------------
def line_families(line: str) -> set[str]:
    """Pattern families that match one line."""
    return {name for name, rx in _FAMILY_RX.items() if rx.search(line)}


def text_ranges(
    lines: list[str], context: int = CONTEXT
) -> list[dict[str, Any]]:
    """Merged hit ranges with families and token counts (1-based lines).

    No line content is returned.
    """
    hits: dict[int, set[str]] = {}
    for index, line in enumerate(lines):
        families = line_families(line)
        if families:
            hits[index] = families
    if not hits:
        return []
    spans: list[list[int]] = []
    for index in sorted(hits):
        start = max(0, index - context)
        stop = min(len(lines) - 1, index + context)
        if spans and start <= spans[-1][1] + 1:
            spans[-1][1] = max(spans[-1][1], stop)
        else:
            spans.append([start, stop])
    out = []
    for start, stop in spans:
        window = lines[start : stop + 1]
        families: set[str] = set()
        hit_lines = 0
        for index in range(start, stop + 1):
            if index in hits:
                families |= hits[index]
                hit_lines += 1
        out.append(
            {
                "start": start + 1,
                "end": stop + 1,
                "families": sorted(families),
                "hit_lines": hit_lines,
                "decimal_tokens": sum(
                    len(DECIMAL_RX.findall(line)) for line in window
                ),
                "target_year_tokens": sum(
                    len(TARGET_YEAR_RX.findall(line)) for line in window
                ),
            }
        )
    return out


def range_is_value_bearing(entry: Mapping[str, Any]) -> bool:
    """A selection range that carries numbers or a B2 target year."""
    return bool(SELECTION_FAMILIES & set(entry["families"])) and (
        entry["decimal_tokens"] > 0 or entry["target_year_tokens"] > 0
    )


# --------------------------------------------------------------------------
# JSON files
# --------------------------------------------------------------------------
def _collapse(key: str) -> str:
    if YEAR_KEY_RX.fullmatch(key):
        return "{year}"
    if RUNG_KEY_RX.fullmatch(key):
        return "{rung}"
    if key.isdigit():
        return "{n}"
    return key


def _key_facts(node: Any) -> tuple[set[str], bool, bool]:
    """Year-shaped keys, whether an ``earn_`` key and a marital key occur."""
    years: set[str] = set()
    earn = False
    marital = False
    stack = [node]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            for key, value in item.items():
                text = str(key)
                if YEAR_KEY_RX.fullmatch(text):
                    years.add(text)
                if text.startswith("earn_"):
                    earn = True
                if MARITAL_RX.search(text):
                    marital = True
                stack.append(value)
        elif isinstance(item, list):
            stack.extend(item)
    return years, earn, marital


@dataclass
class _JsonFacts:
    blocks: dict[str, dict[str, Any]] = field(default_factory=dict)
    fields: dict[str, dict[str, Any]] = field(default_factory=dict)


def _walk(node: Any, path: tuple[str, ...], facts: _JsonFacts) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            text = str(key)
            child = path + (_collapse(text),)
            if (
                BOUNDARY_CONTAINER_RX.search(text)
                and isinstance(value, dict)
                and value
                and all(YEAR_KEY_RX.fullmatch(str(k)) for k in value)
            ):
                pattern = "/" + "/".join(child + ("{year}",))
                entry = facts.blocks.setdefault(
                    pattern,
                    {
                        "years": set(),
                        "n_blocks": 0,
                        "field_names": set(),
                        "descendant_year_keys": set(),
                        "earnings_cells": False,
                        "marital": bool(MARITAL_RX.search(pattern)),
                    },
                )
                for year, block in value.items():
                    entry["years"].add(int(year))
                    entry["n_blocks"] += 1
                    if isinstance(block, dict):
                        entry["field_names"] |= {str(k) for k in block}
                    years, earn, marital = _key_facts(block)
                    entry["descendant_year_keys"] |= years
                    entry["earnings_cells"] |= earn
                    entry["marital"] |= marital
            if (
                text == "pseudo_boundary"
                and isinstance(value, int)
                and not isinstance(value, bool)
                and value in PSEUDO_BOUNDARIES
            ):
                pattern = "/" + "/".join(path)
                entry = facts.fields.setdefault(
                    pattern,
                    {
                        "values": set(),
                        "n": 0,
                        "marital": bool(MARITAL_RX.search(pattern)),
                    },
                )
                entry["values"].add(value)
                entry["n"] += 1
                entry["marital"] |= any(
                    MARITAL_RX.search(str(k)) for k in node
                )
            _walk(value, child, facts)
    elif isinstance(node, list):
        for item in node:
            _walk(item, path + ("[]",), facts)


def json_boundary_facts(document: Any) -> dict[str, list[dict[str, Any]]]:
    """Boundary-keyed blocks and ``pseudo_boundary`` fields, keys only."""
    facts = _JsonFacts()
    _walk(document, (), facts)
    blocks = [
        {
            "path": pattern,
            "years": sorted(entry["years"]),
            "n_blocks": entry["n_blocks"],
            "field_names": sorted(entry["field_names"]),
            "descendant_year_keys": sorted(entry["descendant_year_keys"]),
            "earnings_cells": entry["earnings_cells"],
            "marital": entry["marital"],
        }
        for pattern, entry in sorted(facts.blocks.items())
    ]
    fields = [
        {
            "path": pattern,
            "values": sorted(entry["values"]),
            "n": entry["n"],
            "marital": entry["marital"],
        }
        for pattern, entry in sorted(facts.fields.items())
    ]
    return {"boundary_blocks": blocks, "pseudo_boundary_fields": fields}


def string_names_selection(families: set[str]) -> bool:
    """Whether a JSON string's families name the pseudo-boundary selection."""
    return (
        bool(BOUNDARY_SPECIFIC_FAMILIES & families)
        or {
            "selector",
            "train_only",
        }
        <= families
    )


def json_string_hits(document: Any) -> list[dict[str, Any]]:
    """String values that match a family, by collapsed path; no content.

    A string is value-bearing when it names the selection and carries a
    decimal number or a B2 target year.
    """
    found: dict[tuple[str, tuple[str, ...]], dict[str, Any]] = {}
    stack: list[tuple[Any, tuple[str, ...]]] = [(document, ())]
    while stack:
        node, path = stack.pop()
        if isinstance(node, dict):
            for key, value in node.items():
                stack.append((value, path + (_collapse(str(key)),)))
        elif isinstance(node, list):
            for item in node:
                stack.append((item, path + ("[]",)))
        elif isinstance(node, str):
            families = line_families(node)
            if not families:
                continue
            key = ("/" + "/".join(path), tuple(sorted(families)))
            entry = found.setdefault(
                key,
                {
                    "path": key[0],
                    "families": list(key[1]),
                    "n": 0,
                    "value_bearing": 0,
                },
            )
            entry["n"] += 1
            if string_names_selection(families) and (
                DECIMAL_RX.search(node) or TARGET_YEAR_RX.search(node)
            ):
                entry["value_bearing"] += 1
    return [found[key] for key in sorted(found)]


def _json_touches_targets(facts: Mapping[str, list[dict[str, Any]]]) -> bool:
    touching = _touching_years()
    for entry in facts["boundary_blocks"]:
        if not entry["marital"] and touching & set(entry["years"]):
            return True
    for entry in facts["pseudo_boundary_fields"]:
        if not entry["marital"] and touching & set(entry["values"]):
            return True
    return False


def _json_all_marital(facts: Mapping[str, list[dict[str, Any]]]) -> bool:
    entries = [*facts["boundary_blocks"], *facts["pseudo_boundary_fields"]]
    return bool(entries) and all(entry["marital"] for entry in entries)


# --------------------------------------------------------------------------
# Classification
# --------------------------------------------------------------------------
def file_kind(path: str) -> str:
    """``json``, ``code`` (source under src/ or scripts/) or ``text``."""
    if path.endswith(".json") or path == ".test_durations":
        return "json"
    if path.endswith(".py") and not path.startswith("tests/"):
        return "code"
    return "text"


def classify(
    path: str,
    kind: str,
    ranges: list[dict[str, Any]],
    json_facts: Mapping[str, list[dict[str, Any]]] | None,
) -> str:
    """One tier per file.

    - ``boundary_values``: holds, or may state, pseudo-boundary content at a
      boundary whose scored periods include a B2 target year.
    - ``marital``: B4's marital selectors.
    - ``code``: source that computes, rather than records, outcomes.
    - ``mentions``: names the selection or phrase with no value detected.
    """
    if MARITAL_RX.search(path):
        return "marital"
    if kind == "json" and json_facts is not None:
        if _json_touches_targets(json_facts):
            return "boundary_values"
        if _json_all_marital(json_facts):
            return "marital"
        if any(
            entry["value_bearing"] for entry in json_facts.get("strings", [])
        ):
            return "boundary_values"
        return "mentions"
    if kind == "code":
        return "code"
    if any(range_is_value_bearing(entry) for entry in ranges):
        return "boundary_values"
    return "mentions"


def q6_scope(
    path: str, kind: str, n_lines: int, ranges: list[dict[str, Any]]
) -> dict[str, Any]:
    """What a blinded reviewer should not open in a boundary-values file."""
    if (
        kind == "json"
        or path.endswith(".svg")
        or n_lines <= WHOLE_FILE_MAX_LINES
    ):
        return {"path": path, "scope": "whole_file", "lines": None}
    spans = [
        [entry["start"], entry["end"]]
        for entry in ranges
        if range_is_value_bearing(entry)
    ]
    return {"path": path, "scope": "line_ranges", "lines": spans}


# --------------------------------------------------------------------------
# Repository scan
# --------------------------------------------------------------------------
def _git(*arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def tracked_blobs() -> dict[str, str]:
    """Tracked path -> index blob SHA-1."""
    out = {}
    for line in _git("ls-files", "-s", "-z").split("\0"):
        if not line:
            continue
        meta, path = line.split("\t", 1)
        out[path] = meta.split()[1]
    return out


def scan_file(path: str, text: str) -> dict[str, Any] | None:
    """Inventory one file's text; None when nothing matches."""
    lines = text.splitlines()
    families: dict[str, int] = {}
    for line in lines:
        for name in line_families(line):
            families[name] = families.get(name, 0) + 1
    kind = file_kind(path)
    json_facts = None
    if kind == "json" and (
        families or BOUNDARY_CONTAINER_RX.search(text) is not None
    ):
        try:
            document = json.loads(text)
        except json.JSONDecodeError:
            kind = "text"
        else:
            json_facts = {
                **json_boundary_facts(document),
                "strings": json_string_hits(document),
            }
    has_json_boundary = json_facts is not None and (
        json_facts["boundary_blocks"] or json_facts["pseudo_boundary_fields"]
    )
    if not families and not has_json_boundary:
        return None
    ranges = text_ranges(lines) if kind != "json" else []
    tier = classify(path, kind, ranges, json_facts)
    record: dict[str, Any] = {
        "path": path,
        "kind": kind,
        "lines": len(lines),
        "families": dict(sorted(families.items())),
        "tier": tier,
    }
    if kind == "json":
        record["json"] = json_facts or {
            "boundary_blocks": [],
            "pseudo_boundary_fields": [],
            "strings": [],
        }
    else:
        record["ranges"] = ranges
    return record


def build_inventory(
    blobs: Mapping[str, str], read=lambda p: (ROOT / p).read_bytes()
) -> dict[str, Any]:
    files = []
    skipped_self = []
    for path in sorted(blobs):
        if SELF_MARKER in path:
            skipped_self.append(path)
            continue
        try:
            text = read(path).decode("utf-8")
        except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
            continue
        record = scan_file(path, text)
        if record is not None:
            record["blob_sha1"] = blobs[path]
            files.append(record)
    exclusions = [
        q6_scope(
            record["path"],
            record["kind"],
            record["lines"],
            record.get("ranges", []),
        )
        for record in files
        if record["tier"] == "boundary_values"
    ]
    tiers: dict[str, int] = {}
    for record in files:
        tiers[record["tier"]] = tiers.get(record["tier"], 0) + 1
    return {
        "pseudo_boundaries": list(PSEUDO_BOUNDARIES),
        "scored_offsets": list(SCORED_OFFSETS),
        "b2_target_years": list(B2_TARGET_YEARS),
        "boundaries_touching_b2_targets": boundaries_touching_targets(),
        "pattern_families": PATTERN_FAMILIES,
        "context_lines": CONTEXT,
        "whole_file_max_lines": WHOLE_FILE_MAX_LINES,
        "excluded_self_paths": skipped_self,
        "tracked_files_scanned": len(blobs) - len(skipped_self),
        "tier_counts": dict(sorted(tiers.items())),
        "files": files,
        "q6_exclusions": exclusions,
        "content_recorded": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    out = args.out if args.out.is_absolute() else ROOT / args.out
    if out.exists():
        raise SystemExit(f"refusing to overwrite {out}")
    if RUNS_DIR.resolve() in out.resolve().parents:
        raise SystemExit("B0.1 writes no file under runs/")
    payload = {
        "schema": SCHEMA,
        "repository_head": _git("rev-parse", "HEAD").strip(),
        "worktree_clean": _git("status", "--porcelain").strip() == "",
        "script_sha256": hashlib.sha256(
            Path(__file__).read_bytes()
        ).hexdigest(),
        **build_inventory(tracked_blobs()),
    }
    out.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
