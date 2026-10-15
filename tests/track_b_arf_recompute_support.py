"""Captured statutory text for R3; no real data or network access."""

from __future__ import annotations

import html
import json
import re
from functools import cache
from pathlib import Path

SOURCES = (
    Path(__file__).with_name("data") / "track_b" / "arf_recompute_sources"
)


@cache
def manifest() -> dict:
    """R3 source provenance in the same schema used by milestone G."""
    return json.loads((SOURCES / "manifest.json").read_text())


@cache
def source_text(source_id: str) -> str:
    """Normalize captured HTML, XML or text without changing figures."""
    entry = next(s for s in manifest()["sources"] if s["id"] == source_id)
    raw = (SOURCES / entry["file"]).read_text()
    if entry["file"].endswith((".html", ".xml")):
        raw = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
        raw = re.sub(r"<[^>]+>", " ", raw)
        raw = html.unescape(raw)
    for char in ("\u200b", "\xa0"):
        raw = raw.replace(char, " ")
    raw = raw.replace("’", "'")
    return re.sub(r"\s+", " ", raw).strip()
