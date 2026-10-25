"""Screen Census's SIPP user notes for the variables this reader admits.

Fetches each release's user-notes index (2018-2025) and eligible linked
notes, with plain requests and default headers. A note naming a selected
variable is stored only after the record-bearing check clears its body.
Known record-bearing URLs are never requested. Their existing inventory
metadata supplies the release, title and variable names, without a body
or body pin. New record-bearing pages receive the same exclusion status.

Invariants: known excluded URLs cannot be fetched; a page cannot be stored
if it shows any of the forms ``record_bearing_note`` refuses (identifier
columns, identifiers beside values, long digit runs, rows of numbers and
preformatted identifier text); exclusion inventory entries retain only
URL, title, release, variable names and their reason. Stored pages retain
their uncompressed byte size and SHA-256. No survey data file is requested.
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
# Census source URLs; titles and the exclusion rationale are cited in
# metadata_notes.md#record-bearing-user-notes. Never open these bodies.
EXCLUDED_NOTE_URLS = frozenset(
    {
        f"{NOTES}/2019-usernotes/2019-one-case-neg-hrly-earn-val.html",
        f"{NOTES}/2021-usernotes/child-care-assist-errors.html",
        f"{NOTES}/2022-usernotes/2022-child-care-assist-err-sm-numb-case.html",
        f"{NOTES}/2023-usernotes/2023-incorrect-child-care-assistance-case.html",
        f"{NOTES}/2023-usernotes/2023-minor-discrepancies-school-meals.html",
        f"{NOTES}/2023-usernotes/2023-inconsistent-case-soc-behalf-child.html",
        f"{NOTES}/2024-usernotes/2024-inconsistency-other-support-paid.html",
        f"{NOTES}/2025-usernotes/2025-inc-top-cod-mcr-ded.html",
    }
)
EXCLUSION_REASON = (
    "Whole-page capture excluded because it carries survey case records; "
    "URL and title only (metadata_notes.md#record-bearing-user-notes)."
)


# An identifier name, also when it opens a longer heading or is plural.
IDENTIFIER = r"\b(?:SSUID|PNUM)s?\b"
# A cell that holds one number: a sign or dollar, grouped digits, decimals.
NUMERIC_CELL = r"[-+$]?\d[\d,]*(?:\.\d+)?%?"


def note_text(body: str) -> str:
    """The visible text of a Census page, tags and scripts removed."""
    body = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", body)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", body)).split())


def _rendered_text(body: str) -> str:
    """Text a reader sees: also without noscript blocks and comments, whose
    tracking and layout numbers are not page content."""
    body = re.sub(r"(?is)<noscript\b.*?</noscript\s*>", " ", body)
    return note_text(re.sub(r"(?s)<!--.*?-->", " ", body))


def _identifier_column(table: str) -> bool:
    """Distinguish record columns from variable-definition table rows."""
    row_bodies = re.findall(
        r"(?is)<tr\b[^>]*>(.*?)(?:</tr\s*>|(?=<tr\b)|$)", table
    )
    rows = [
        [
            (note_text(body), tag.casefold(), attributes)
            for tag, attributes, body in re.findall(
                r"(?is)<(th|td)\b([^>]*)>(.*?)"
                r"(?:</t[hd]\s*>|(?=<t[hd]\b)|$)",
                row,
            )
        ]
        for row in row_bodies or [table]
    ]
    headings = (
        {text.casefold().rstrip(":") for text, _, _ in rows[0]}
        if rows
        else set()
    )
    definition_table = bool(
        headings & {"variable", "variables", "variable name", "name"}
        and headings & {"description", "label", "universe"}
    )
    for row_index, row in enumerate(rows):
        texts = [text for text, _, _ in row]
        # Three numbers in one row read as a record, whatever the headings.
        if sum(bool(re.fullmatch(NUMERIC_CELL, text)) for text in texts) >= 3:
            return True
        for column_index, (text, tag, attributes) in enumerate(row):
            if not re.match(IDENTIFIER, text, re.I):
                continue
            # An identifier beside a value of three or more digits, even in
            # a definition table.
            if any(
                re.search(r"\d{3,}", other)
                for index, other in enumerate(texts)
                if index != column_index
                and not re.match(IDENTIFIER, other, re.I)
            ):
                return True
            row_header = bool(
                re.search(
                    r"\bscope\s*=\s*(?:\"row\"|'row'|row)(?:\s|$)",
                    attributes,
                    re.I,
                )
            )
            heading = re.fullmatch(r"SSUID|PNUM", text, re.I)
            if heading and (
                row_index == 0
                or (tag == "th" and not row_header and not definition_table)
            ):
                return True
            if any(
                column_index < len(later)
                and re.fullmatch(r"\d+", later[column_index][0])
                for later in rows[row_index + 1 :]
            ):
                return True
    return False


def record_bearing_note(body: str) -> bool:
    """Recognize survey identifiers without returning matched content.

    A page is refused when it holds any of:

    - a table column headed by an identifier name, or a cell that begins
      with one and has numeric cells below it;
    - a table row with an identifier name and, in another cell, a run of
      three or more digits, even in a variable-definition table;
    - a table row of three or more numeric cells;
    - an identifier name followed by digits, with only punctuation or
      HTML entities between, or by a run of three or more digits within 40
      characters of the same sentence, in the text or in an HTML comment,
      which is stored though not shown;
    - a run of nine or more digits in the text a reader sees;
    - a preformatted block that names an identifier and holds a digit.

    Variable-definition rows may name an identifier without a value.
    """
    adjacent = r"\b(?:SSUID|PNUM)(?=\W|[0-9]|$)"
    for table in re.findall(r"(?is)<table\b[^>]*>.*?(?:</table\s*>|$)", body):
        if _identifier_column(table):
            return True
    for block in re.findall(r"(?is)<pre\b[^>]*>(.*?)(?:</pre\s*>|$)", body):
        text = note_text(block)
        if re.search(IDENTIFIER, text, re.I) and re.search(r"\d", text):
            return True
    text = note_text(re.sub(r"<!--|-->", " ", body))
    return bool(
        re.search(adjacent + r"[\s:=#'\"(\[\-]*\d", text, re.I)
        or re.search(IDENTIFIER + r"[^.<>]{0,40}?\d{3,}", text, re.I)
        or re.search(r"\d{9,}", _rendered_text(body))
    )


def excluded_note_metadata(entry: dict) -> dict:
    """Keep inventory metadata only; never retain a body pin or extract."""
    return {
        key: entry[key]
        for key in ("url", "title", "release", "variables", "kind")
    } | {
        "stored_as": None,
        "status": "excluded_record_bearing",
        "exclusion_reason": EXCLUSION_REASON,
    }


def fetch(url: str) -> tuple[bytes, dict]:
    if url in EXCLUDED_NOTE_URLS:
        raise ValueError("Excluded record-bearing note URL")
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
    previous = {
        row["url"]: row
        for row in json.loads((BASE / "user_notes_manifest.json").read_text())
    }
    pattern = re.compile(
        r"\b("
        + "|".join(sorted(map(re.escape, names), key=len)[::-1])
        + r")\b"
    )
    log = [
        excluded_note_metadata(previous[url])
        for url in sorted(EXCLUDED_NOTE_URLS)
    ]
    for year in YEARS:
        index_url = f"{NOTES}/{year}-usernotes.html"
        body, entry = fetch(index_url)
        if record_bearing_note(body.decode("utf-8", "replace")):
            raise ValueError("Record-bearing note index refused")
        folder = BASE / "user_notes" / str(year)
        folder.mkdir(parents=True, exist_ok=True)
        for url in EXCLUDED_NOTE_URLS:
            if previous[url]["release"] == year:
                (folder / f"{Path(url).stem}.html.gz").unlink(missing_ok=True)
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
            url = SITE + href
            if url in EXCLUDED_NOTE_URLS:
                continue
            note_body, note = fetch(url)
            page = note_body.decode("utf-8", "replace")
            text = note_text(page)
            title = re.search(r"(?is)<title>(.*?)</title>", page)
            hits = sorted(set(pattern.findall(text)))
            stored = None
            excluded = record_bearing_note(page)
            destination = folder / f"{Path(href).stem}.html.gz"
            if excluded:
                destination.unlink(missing_ok=True)
            if hits and note["http_status"] == 200 and not excluded:
                stored = f"user_notes/{year}/{Path(href).stem}.html.gz"
                destination.write_bytes(gzip.compress(note_body, mtime=0))
            note |= {
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
            log.append(excluded_note_metadata(note) if excluded else note)
        print(year, len(links), "notes")
    (BASE / "user_notes_manifest.json").write_text(
        json.dumps(log, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
