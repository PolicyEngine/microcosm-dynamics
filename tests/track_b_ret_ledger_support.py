"""Captured-source helpers for R2 statutory conformance (no real data)."""

from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
from functools import cache
from pathlib import Path

TRACK_B_DATA = Path(__file__).with_name("data") / "track_b"
SOURCES = TRACK_B_DATA / "ret_ledger_sources"


@cache
def manifest() -> dict:
    return json.loads((SOURCES / "manifest.json").read_text())


def _normalize(raw: str) -> str:
    for char in ("\u200b", "\xa0"):
        raw = raw.replace(char, " ")
    raw = raw.replace("’", "'")
    return re.sub(r"\s+", " ", raw).strip()


@cache
def source_text(source_id: str) -> str:
    """Normalize capture whitespace; extract the local PDF only if supported.

    The PDF remains the authority. The manifest also pins verbatim excerpts
    from those exact bytes for platforms without ``pdftotext``. Neither path
    downloads a source or changes a capture.
    """
    entry = next(s for s in manifest()["sources"] if s["id"] == source_id)
    path = SOURCES / entry["file"]
    if path.suffix == ".pdf":
        command = shutil.which("pdftotext")
        if command:
            raw = subprocess.run(
                [command, "-layout", str(path), "-"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
        else:
            raw = (SOURCES / "ssa_pub_05_10069_excerpt.txt").read_text()
    else:
        raw = path.read_text()
    if path.suffix in (".html", ".xml"):
        raw = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
        raw = re.sub(r"<[^>]+>", " ", raw)
        raw = html.unescape(raw)
    return _normalize(raw)
