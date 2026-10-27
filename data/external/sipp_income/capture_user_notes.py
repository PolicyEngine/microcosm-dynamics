"""Screen Census's SIPP user notes for the variables this reader admits.

Fetches each release's user-notes index (2018-2025) and eligible linked
notes, with plain requests and default headers. A note naming a selected
variable is stored only after the record-bearing check clears its body.
Known record-bearing URLs are never requested. Their existing inventory
metadata supplies the release, title and variable names, without a body
or body pin. New record-bearing pages receive the same exclusion status.

Invariants: known excluded URLs cannot be fetched; a page cannot be stored
if it shows any of the forms ``record_bearing_note`` refuses (identifier
columns, identifiers beside values, long digit runs, rows or preformatted
lines of numbers and preformatted identifier text), which it reads in time
linear in the page's length; exclusion inventory entries retain only URL,
title, release, variable names and their reason. Stored pages retain their
uncompressed byte size and SHA-256. No survey data file is requested.
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
# A cell that holds one number: signed, in dollars or in parentheses,
# grouped, with decimals or a percent sign.
NUMERIC_CELL = r"[-+−]?\$?[-−]?\(?\$?\d[\d,]*(?:\.\d+)?\)?%?"
# A run of three or more digits that is not a year from 1900 to 2099, which
# notes print beside identifier names as panel and release years.
VALUE_RUN = r"(?<!\d)(?!(?:19|20)\d\d(?!\d))\d{3,}"
# SSUID's length in every release's dictionary, 2018-2025.
SSUID_DIGITS = 14


# A tag opens with a letter, "!" or "/", as in a browser.
TAG = r"<[A-Za-z!/][^>]*>"


def _element(names: str) -> str:
    """An element of one of ``names`` and its contents, up to its end tag
    or the end of the page."""
    return rf"(?is)<({names})\b[^>]*>(.*?)(?:</\1\s*>|$)"


# Script and style elements, one at every "<script" or "<style".
ELEMENT = re.compile(_element("script|style"))
# The same elements where a browser starts them, and the tags between.
BROWSER_SOURCE = re.compile(_element("script|style") + "|" + TAG)
# Elements whose contents a browser does not parse as tags: script and
# style contents are not shown, and title, textarea and xmp contents are
# shown as text.
BROWSER_TEXT = re.compile(
    _element("script|style|title|textarea|xmp") + "|" + TAG
)
# Scripts for their strings, as the round-8 guard read them: any end tag
# that "(?i)script" matches ends one, where the template's end tag must
# repeat the opening's name, which Python's re compares in lower case. The
# two differ only where one name has a long s or a dotless i and the other
# has not.
SCRIPT = re.compile(r"(?is)<(script)\b[^>]*>(.*?)(?:</script\s*>|$)")
STYLE = re.compile(_element("style"))
TABLE = re.compile(_element("table"))
PRE = re.compile(_element("pre"))
ROW = re.compile(r"(?is)<tr\b[^>]*>(.*?)(?:</tr\s*>|(?=<tr\b)|$)")
CELL = re.compile(
    r"(?is)<(th|td)\b([^>]*)>(.*?)(?:</t[hd]\s*>|(?=<t[hd]\b)|$)"
)
# A script or style element that its end tag closes, which the visible
# text leaves out.
CLOSED_SCRIPT = re.compile(r"(?is)<(script|style)[^>]*>.*?</\1>")
TAGS = re.compile(TAG)
# An attribute name starts only where a run of name characters starts, so
# a long run is read once rather than from each of its characters.
ATTRIBUTE = re.compile(
    r"(?<![\w:.-])([\w:.-]+)\s*=\s*(?:\"([^\"]*)\"|'([^']*)')"
)
STRING = {
    '"': r'"((?:[^"\\]|\\.)*)"',
    "'": r"'((?:[^'\\]|\\.)*)'",
    "`": r"`((?:[^`\\]|\\.)*)`",
}


def _finditer(pattern: re.Pattern, text: str):
    """``pattern.finditer(text)`` in linear time, for a pattern that opens
    with a tag closed by the first ``>`` after it and matches wherever that
    tag opens. Python's re retries such a pattern at each ``<`` that no
    ``>`` follows, each time to the end of the text. No match starts after
    the last ``>``, so the search stops there; a match that reaches it is
    matched again on the whole text, where it may run to the end."""
    end = text.rfind(">") + 1
    for match in pattern.finditer(text, 0, end):
        if match.end() == end:
            match = pattern.match(text, match.start())
        yield match


def _sub(pattern: re.Pattern, replace, text: str) -> str:
    """``pattern.sub(replace, text)``, through ``_finditer``."""
    kept, position = [], 0
    for match in _finditer(pattern, text):
        kept += (text[position : match.start()], replace(match))
        position = match.end()
    return "".join(kept) + text[position:]


def _sub_to_last(pattern: str, end_tag: str, text: str) -> str:
    """``re.sub(pattern, " ", text)`` for a pattern whose matches end with
    ``end_tag``: the text after the last end tag is kept unsearched, since
    each try there would read to the end of the text and fail."""
    cut = 0
    for match in re.finditer(end_tag, text):
        cut = match.end()
    return re.sub(pattern, " ", text[:cut]) + text[cut:]


def _without_tags(text: str) -> str:
    """Each span from a ``<`` to the next ``>`` replaced by a space."""
    end = text.rfind(">") + 1
    return re.sub(r"<[^>]+>", " ", text[:end]) + text[end:]


def _without_closed_scripts(body: str) -> str:
    """``CLOSED_SCRIPT.sub(" ", body)`` in linear time. A script or style
    opening matches only if an end tag of its kind starts after the ``>``
    that closes it, so an opening that cannot match is skipped rather than
    read to the end of the page. The end tag repeats the opening's name,
    which Python's re compares a letter at a time in lower case, so both
    names are keyed that way; "İ", which ``(?i)`` reads as an "i", lowers
    there to "i" alone."""

    def key(name):
        return name.replace("\u0130", "i").lower()

    last_end = {}
    for end_tag in re.finditer(r"(?i)</(script|style)>", body):
        last_end[key(end_tag.group(1))] = end_tag.start()
    kept, position, close = [], 0, -1
    for opening in re.finditer(r"(?i)<(script|style)", body):
        start = opening.start()
        if start < position:
            continue
        if close < start:
            close = body.find(">", start)
            if close < 0:
                break
        if last_end.get(key(opening.group(1)), -1) <= close:
            continue
        kept += (body[position:start], " ")
        position = CLOSED_SCRIPT.match(body, start).end()
    return "".join(kept) + body[position:]


def note_text(body: str) -> str:
    """The visible text of a Census page, tags and scripts removed: each
    span from a ``<`` to the next ``>`` counts as a tag, and a script or
    style element as one only up to its end tag."""
    body = _without_tags(_without_closed_scripts(body))
    return " ".join(html.unescape(body).split())


def _browser_text(body: str) -> str:
    """The text as a browser reads it: a tag opens with a letter, ``!`` or
    ``/``, script and style contents are not shown, and title, textarea and
    xmp contents are text as they stand, up to their end tag or the end of
    the page."""

    def shown(match):
        if match.group(1) and match.group(1).casefold() not in {
            "script",
            "style",
        }:
            return f" {match.group(2)} "
        return " "

    body = _sub(BROWSER_TEXT, shown, body)
    return " ".join(html.unescape(body).split())


def _rendered_text(body: str) -> str:
    """Text a reader sees: also without noscript blocks and comments, whose
    tracking and layout numbers are not page content."""
    body = _sub_to_last(
        r"(?is)<noscript\b.*?</noscript\s*>", r"(?i)</noscript\s*>", body
    )
    return note_text(_sub_to_last(r"(?s)<!--.*?-->", "-->", body))


def _identifier_column(table: str) -> bool:
    """Distinguish record columns from variable-definition table rows."""
    row_bodies = [row.group(1) for row in _finditer(ROW, table)]
    rows = [
        [
            (note_text(body), tag.casefold(), attributes)
            for tag, attributes, body in (
                cell.groups() for cell in _finditer(CELL, row)
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
    # The last row with a cell of digits alone in each column, so that no
    # cell reads every row below it.
    digits_until = {}
    for row_index, row in enumerate(rows):
        for column_index, (text, _, _) in enumerate(row):
            if re.fullmatch(r"\d+", text):
                digits_until[column_index] = row_index
    for row_index, row in enumerate(rows):
        texts = [text for text, _, _ in row]
        # Three numbers in one row read as a record, whatever the headings.
        if sum(bool(re.fullmatch(NUMERIC_CELL, text)) for text in texts) >= 3:
            return True
        values = None
        for column_index, (text, tag, attributes) in enumerate(row):
            begins = re.match(IDENTIFIER, text, re.I)
            # A heading may name an identifier after other words, as in
            # "Person number (PNUM)".
            names = (row_index == 0 or tag == "th") and re.search(
                IDENTIFIER, text, re.I
            )
            if not begins and not names:
                continue
            # An identifier beside a value of three or more digits in any
            # other cell, even one that names an identifier too, and even in
            # a definition table. Each cell is read once per row.
            if values is None:
                values = [bool(re.search(VALUE_RUN, other)) for other in texts]
                value_cells = sum(values)
            if value_cells > values[column_index]:
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
            if digits_until.get(column_index, -1) > row_index:
                return True
    return False


def _strip_link_targets(tag: str) -> str:
    """One tag with its href and src values removed."""
    return re.sub(
        r"(?i)(?<![\w-])(?:href|src)\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]*)",
        " ",
        tag,
    )


def _strip_opening(element: str) -> str:
    """A script or style element with href and src values removed from
    its opening tag only."""
    opening = element[: element.index(">") + 1]
    return _strip_link_targets(opening) + element[len(opening) :]


def _without_link_targets(body: str) -> tuple[str, str]:
    """The page source with each tag's href and src values removed, since
    link slugs such as ``ssuid-2024`` name identifiers without values; read
    two ways, joined by the caller with a period, which no window crosses.

    Script and style contents, up to their end tag or the end of the page,
    are code, not tags: they are kept as they stand, and only their opening
    tag loses its href and src values. So no ``<`` in script code, such as
    ``i<n`` or ``a</b``, hides a ``src`` assignment. The first reading finds
    these elements where a browser starts them, in one scan from the start
    of the page, so a ``<script`` inside a quoted value opens none. The
    second starts an element at every ``<script`` or ``<style``, even inside
    another tag, as the guard did before the first was added; it is kept
    because the first, alone, would admit some pages it refuses."""

    def browser(match):
        if match.group(1):
            return _strip_opening(match.group())
        return _strip_link_targets(match.group())

    def strip(tag):
        return _strip_link_targets(tag.group())

    kept, position = [], 0
    for element in _finditer(ELEMENT, body):
        kept += (
            _sub(TAGS, strip, body[position : element.start()]),
            _strip_opening(element.group()),
        )
        position = element.end()
    every_element = "".join(kept) + _sub(TAGS, strip, body[position:])
    return _sub(BROWSER_SOURCE, browser, body), every_element


def _strings(code: str, quotes: str) -> list[str]:
    """Each string that ``re.findall`` reads in ``code`` with one
    alternative ``Q((?:[^Q\\]|\\.)*)Q`` per quote mark Q in ``quotes``,
    tried in turn from the start, in linear time. A string closes at the
    first mark of its kind that no odd run of backslashes precedes, so a
    mark after the last such mark of its kind opens no string; it is set
    aside before the scan, rather than read to the end each time."""
    if not any(quote in code for quote in quotes):
        return []
    last = dict.fromkeys(quotes, -1)
    for mark in re.finditer(r"(?<!\\)(?:\\\\)*([\"'`])", code):
        if mark.group(1) in last:
            last[mark.group(1)] = mark.end() - 1
    scanned = code
    for quote, end in last.items():
        if code.find(quote, end + 1) >= 0:
            scanned = scanned[: end + 1] + scanned[end + 1 :].replace(
                quote, "\0"
            )
    pattern = "(?s)" + "|".join(STRING[quote] for quote in quotes)
    return [
        code[slice(*match.span(match.lastindex))]
        for match in re.finditer(pattern, scanned)
    ]


def _quoted_values(body: str) -> list[str]:
    """Each quoted attribute value other than href and src, each double- or
    single-quoted string in a script as ``_strings`` reads them from the
    script's start, each template literal (backtick string) in a script,
    and each double- or single-quoted string in a style, read past its
    backslash escapes, entities decoded. Template literals are read apart
    from the other strings, so that a backtick changes no other string."""
    end = body.rfind(">") + 1
    values = [
        double or single
        for tag in re.findall(r"<[A-Za-z][^>]*>", body[:end])
        for name, double, single in ATTRIBUTE.findall(tag)
        if name.casefold() not in {"href", "src"}
    ]
    scripts = [script.group(2) for script in _finditer(SCRIPT, body)]
    for script in scripts:
        values += _strings(script, "\"'")
    for script in scripts:
        values += _strings(script, "`")
    for style in _finditer(STYLE, body):
        values += _strings(style.group(2), "\"'")
    return [html.unescape(value) for value in values]


def record_bearing_note(body: str) -> bool:
    """Recognize survey identifiers without returning matched content.

    A page is refused when it holds any of:

    - a cell that is exactly an identifier name, in a table's first row
      or in a header cell that is not a row header outside a
      variable-definition table, or a cell that has a cell of digits alone
      below it and begins with an identifier name or, in a table's first
      row or a header cell, names one anywhere;
    - a table row with a cell that begins with an identifier name, or in a
      table's first row or a header cell names one anywhere, and, in any
      other cell, even one that names an identifier too, a run of three or
      more digits that is not a year, even in a variable-definition table;
    - a table row of three or more numeric cells;
    - an identifier name followed by a digit, with only spaces and the
      marks ``: = # ' " ( [ -`` between, or by a run of three or more
      digits that is not a year, with at most 40 characters and no period
      between. These two rules read three things, all with entities
      decoded:

      - the text with HTML comments, which are stored though not shown,
        read twice, each time with a tag counted as a space: once with
        every span from a ``<`` to the next ``>`` taken for a tag and each
        script or style element that an end tag closes left out, and once
        as a browser reads it, where a tag opens only with a letter, ``!``
        or ``/``, script and style contents are left out, and title,
        textarea and xmp contents are text, up to their end tag or the end
        of the page;
      - the page source with its tags, attributes and scripts, where the
        40 characters hold no angle bracket (a tag, or a ``<`` or ``>``
        decoded from an entity), quote or equals sign either. href and src
        values are removed first from every tag outside scripts and styles
        and from their opening tags, while script and style contents, up to
        their end tag or the end of the page, are read as they stand. It is
        read twice: once with those elements found where a browser starts
        them, in one scan from the start of the page, and once with one
        starting at every ``<script`` or ``<style``, even inside another
        tag;
      - one at a time: each quoted attribute value other than href and src;
        each double- or single-quoted string in a script, as a scan from
        the script's start finds them, even one that an escaped quote mark
        opens; each template literal in a script; and each quoted string in
        a style, all read past their backslash escapes;

    - a run of nine or more digits in the text a reader sees, without
      comments, noscript blocks, scripts, styles and tags, since tracking
      numbers sit there and are not page content;
    - a run of 14 or more digits, SSUID's length, anywhere in the page;
    - a preformatted block that names an identifier and holds a digit, or
      that has a line of three or more numbers.

    A table row's cells are read whole, so numbers stacked with ``<br>`` in
    one cell are not separate numeric cells. Variable-definition rows may
    name an identifier without a value. The text and the source are each
    read both ways because the browser's way, alone, would admit some pages
    that the first way refuses.

    These forms are out of scope, so a page that holds only them is stored:
    a value before its identifier name; ``<br>``-separated CSV text without
    an identifier; div grids; an identifier name and its value in different
    attribute values or script strings, or one of them in a string and the
    other in script code; a script string after a lone quote mark in a
    comment, a regular expression or a template literal, which the scan of
    double- and single-quoted strings takes to open one, as in a comment
    such as ``// it's``; an identifier and its value split by a tag, quote
    or equals sign in script or style code outside a quoted string, as in a
    comparison ``PNUM < 101`` or markup in a ``text/template`` script, or in
    an unquoted attribute value, as in ``alt=PNUM's-101``; a value inside a
    tag after an identifier in the text, as in ``PNUM <i 101``; a quoted
    attribute value in an end tag or a ``<!`` declaration, or after a name
    with marks other than ``_ : . -``, as in ``[alt]``; an attribute value
    that holds a raw ``>``, which ends its tag; a value in an href or src
    value, unless it is a run of 14 or more digits; and a cell outside a
    table's first row and header cells that names an identifier after
    other words.

    The rules in turn refuse some pages that hold no case record, and such
    a page stops the capture loudly: definition and index tables that name
    an identifier in a heading cell with digits below it, or beside a run
    of three or more digits that is not a year in its row, as in a
    definition row whose description reads ``SSUID. Values start at 101.``
    or an index row ``SSUIDs. See 112 notes.``; a quoted value that names
    an identifier before a count across an apostrophe or decoded markup, as
    in a page summary ``The SSUID's format in the 2018 panel, as 112 notes
    say``; a link slug such as ``ssuid-2024`` in a script string or a
    ``text/template`` script, or in an ``xlink:href``, ``:href`` or
    ``img.src`` value, which the source reading removes as a link target
    but the quoted-value reading reads, since it skips only values named
    href or src; and a definition that prints a comparison such as
    ``PNUM < 101`` in the text. A decimal character reference of more than
    4,300 digits makes ``html.unescape`` raise, which stops the capture
    too.

    Each reading takes time linear in the page's length; the slow forms
    found so far are timed in the tests.
    """
    adjacent = r"\b(?:SSUID|PNUM)(?=\W|[0-9]|$)"
    for table in _finditer(TABLE, body):
        if _identifier_column(table.group()):
            return True
    for block in _finditer(PRE, body):
        block = block.group(2)
        text = note_text(block)
        if re.search(IDENTIFIER, text, re.I) and re.search(r"\d", text):
            return True
        lines = html.unescape(_without_tags(block)).splitlines()
        if any(
            sum(
                bool(re.fullmatch(NUMERIC_CELL, word)) for word in line.split()
            )
            >= 3
            for line in lines
        ):
            return True
    # Each reading with the characters the 40-character window may span.
    # The text has no tags left, so an angle bracket there is a decoded
    # entity or a "<" that opens no tag, which ends no sentence. Each
    # reading's parts are joined by periods so that the window never spans
    # two; quoted values are read one at a time in the same way.
    unwrapped = re.sub(r"<!--|-->", " ", body)
    readings = (
        (note_text(unwrapped) + ". " + _browser_text(unwrapped), r"[^.]"),
        (
            ". ".join(map(html.unescape, _without_link_targets(body))),
            r"[^.<>\"'=]",
        ),
        (". ".join(_quoted_values(body)), r"[^.]"),
    )
    return bool(
        any(
            re.search(adjacent + r"[\s:=#'\"(\[\-]*\d", text, re.I)
            or re.search(
                IDENTIFIER + window + r"{0,40}?" + VALUE_RUN, text, re.I
            )
            for text, window in readings
        )
        or re.search(r"\d{9,}", _rendered_text(body))
        or re.search(rf"\d{{{SSUID_DIGITS},}}", html.unescape(body))
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
