"""Screen Census's SIPP user notes for the variables this reader admits.

Fetches each release's user-notes index (2018-2025) and every note it
links, with plain requests and default headers. A note whose text names a
variable in ``concept_selection.json``'s release crosswalk is stored
gzipped as ``user_notes/<release>/<note>.html.gz``; every fetched page,
stored or not, is logged in ``user_notes_manifest.json`` with its URL, UTC
retrieval time, byte size, SHA-256 (of the uncompressed body) and the
variables it names. Documentation only; no data file is requested.
"""

from __future__ import annotations

import gzip
import hashlib
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parent
SITE = "https://www.census.gov"
NOTES = f"{SITE}/programs-surveys/sipp/tech-documentation/user-notes"
YEARS = range(2018, 2026)


def note_text(body: str) -> str:
    """The visible text of a Census page, tags and scripts removed."""
    body = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", body)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", body)).split())


def fetch(url: str) -> tuple[bytes, dict]:
    response = requests.get(url, timeout=120)
    return response.content, {
        "url": url,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "http_status": response.status_code,
        "bytes": len(response.content),
        "sha256": hashlib.sha256(response.content).hexdigest(),
    }


def admitted_names() -> set[str]:
    selection = json.loads((BASE / "concept_selection.json").read_text())
    return {
        name
        for release in selection["release_crosswalk"].values()
        for name in release.values()
        if name
    }


def main() -> None:
    names = admitted_names()
    pattern = re.compile(
        r"\b("
        + "|".join(sorted(map(re.escape, names), key=len)[::-1])
        + r")\b"
    )
    log = []
    for year in YEARS:
        index_url = f"{NOTES}/{year}-usernotes.html"
        body, entry = fetch(index_url)
        folder = BASE / "user_notes" / str(year)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "index.html.gz").write_bytes(gzip.compress(body, mtime=0))
        log.append(
            entry
            | {
                "release": year,
                "kind": "index",
                "stored_as": f"user_notes/{year}/index.html.gz",
                "variables": [],
            }
        )
        links = dict.fromkeys(
            re.findall(
                rf'href="(/programs-surveys/sipp/tech-documentation/'
                rf'user-notes/{year}-usernotes/[^"#?]+\.html)"',
                body.decode("utf-8", "replace"),
            )
        )
        for href in links:
            note_body, note = fetch(SITE + href)
            text = note_text(note_body.decode("utf-8", "replace"))
            title = re.search(r"(?is)<title>(.*?)</title>", note_body.decode())
            hits = sorted(set(pattern.findall(text)))
            stored = None
            if hits and note["http_status"] == 200:
                stored = f"user_notes/{year}/{Path(href).stem}.html.gz"
                (BASE / stored).write_bytes(gzip.compress(note_body, mtime=0))
            log.append(
                note
                | {
                    "release": year,
                    "kind": "note",
                    "title": (
                        " ".join(html.unescape(title.group(1)).split())
                        if title
                        else ""
                    ),
                    "stored_as": stored,
                    "variables": hits,
                }
            )
        print(year, len(links), "notes")
    (BASE / "user_notes_manifest.json").write_text(
        json.dumps(log, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
