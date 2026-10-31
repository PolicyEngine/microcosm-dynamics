"""POMS SI 01415 federally administered supplement payment tables.

Invariants
----------
* Both the public dispatcher and this parser verify the pinned bytes.
* A payment table retains its state, claimant type, Federal living-arrangement
  code, State supplement code, category and original numeric column labels.
  Blank code cells continue the preceding code; categories never continue.
* Payment effective dates and the section's revision dates remain distinct.
  Conflicting payment dates remain named alternatives, with no chosen date.
* Missing and malformed amounts remain explicit missing cells. Source
  footnotes survive. Stacked subrows retain each separately published amount.
* Published component/total discrepancies are flagged, never corrected.
* No parser prints or logs source amounts, and no amount is reconstructed.

Only federally administered optional supplement tables are represented.
State-administered programs described in prose are cited by the capture but
are not silently represented as a complete state parameter series. The
State OS code identifies the living arrangement defined in the State's
code-definition tables (``definitions_table_indexes`` in selectors). A State's
definitions may span more than one physical table; the reader merges them and
refuses a code whose tables define it differently. Definitions come only from
the chart's own State section, and a State named only in a date line, with no
section heading, refuses. Paragraphs and headings end where HTML ends them,
end tag or not, and every block that ends a paragraph, apart from a table or
rule, is read from its own text. So a State heading in a block left open
still names its State, and a list item, section or blockquote reads the same
after a closed heading as inside one left open. A block is read whole and
also line by line, a line being its text between ``br`` tags and the blocks
HTML keeps inside it, so a block or ``br`` after a heading's words does not
hide its State, claimant or date. Each whole text and line is read three
ways: joined, as HTML renders inline elements; bare, the joined reading
without footnote markers (a ``sup``, or a link to an anchor on the page,
whose text is one to three word characters or footnote signs, as
``<sup>1</sup>``); and spaced, with a space at every element's edge. A
longer ``sup`` and a link elsewhere are text in these readings. The date
checks also read a fourth, unmarked, the joined reading without any element
either marker rule counts: the bare reading's markers, and any ``sup`` or
link whose href holds "fn", as table cells count them. Every reading drops
Unicode format characters (category Cf), such as zero-width spaces, joiners
and soft hyphens, and the text of ``script`` and ``style`` elements, which
HTML does not render, a marker's text included. The joined and bare
readings name a block's State heading and claimant, so ``U<span>tah</span>``
and ``Utah<sup>1</sup>`` head Utah. The date sentence is chosen from the
joined reading; a sentence whose bare or unmarked reading states other
dates, or a range where the joined one does not, refuses, and so does a line
that is a dated sentence only in its bare or unmarked reading, unless its
markers all lead it, as a footnote body's does. A block's whole text is its
date sentence when it is one; otherwise each line that is one dates the
block, and lines that date differently remain named alternatives. A range
("effective from ... to ...") dates a chart from and to only when it states
two dates; any other dates remain named alternatives. Every State net runs
over the joined, bare and spaced readings of the whole text and of every
line, and refuses if any of them names a State other than the section's:

- a line that dates another State, or an effective-date sentence that names
  one, refuses, since that State's section heading was not read;
- a line that mentions a claimant word, prose included, that names another
  State refuses, and so does a claimant line that only the spaced reading
  shows;
- a line shaped as another State's heading that heads no section refuses:
  one in a block whose whole text is a State date line, one only the spaced
  reading shows, and one whose postal code is not its State's, as "New York
  (NJ)" in Nevada's section;
- any line of an h1-h6 heading that names another State refuses, so a
  heading names no State but the one it heads or its section's;
- a line under 80 characters, in a block of any kind, that opens as another
  State's caption refuses: after optional leading dashes, bullets,
  asterisks, quotation marks or parentheses, a list label ("1.", "2)",
  "(b)"), a heading prefix, "The" and "State of", that State's name,
  spelling or alias, abbreviation or upper-case postal code, as "Utah
  (continued)", "(b) Utah", "The State of Utah", "N.J. notes" or "UT
  (continued)". The District's alias is read first, so "Washington, D.C."
  opens with the District;
- any other line under 80 characters that names another State, as
  "Supplements for Utah", refuses, since it may open that State's section
  in a form no heading takes. These two nets run last, so the others keep
  their messages;
- a block whose lines head two States refuses.

Only a claimant line names a chart's claimant: a heading form ("a.
Individual payment levels for Nevada", "Couple") or a caption that ends
with its claimant word after a State date line or effective-date sentence
that ends with a date or a State ("Utah Effective 1/1/03 Individual"). A
block with a claimant line names every claimant word, or its plural, that
any reading of its whole text or lines holds, prose lines included, so
"Individual<br>or couple" names two types and refuses. A heading, or a line
under 80 characters, that holds a claimant word or its plural but is no
claimant line, such as "Couple payment levels:", "Eligible couple" or
"Couples", names a claimant the reader does not read: it names none, and
the next chart refuses unless a later claimant line names one; if it holds
two types, as "Individual or couple for Nevada", it refuses. Prose of 80
characters or more, outside a heading, that mentions a claimant word, such
as a long "A recipient or couple qualifies if ..." paragraph, names none and
leaves the claimant line before it standing. Before any State heading, the
chart refuses instead. A postal code after a State's name must be that
State's, and "Washington, D.C.", "Washington,DC" and "Washington DC" name the
District. The spellings "Hawaiʻi", "Hawai‘i", "Hawai’i" and "Hawai'i" name
Hawaii and may head its section. To the nets, a postal code in parentheses,
as in "(UT)" or "(ut)", an upper-case postal code standing as a word, as in
"for UT", and a State's abbreviation, as in "N.J." or "Nev.", also name their
States; they never head a section. Each chart needs its own claimant line
after the chart before it.

A section's date stands for its later charts until another effective-date
sentence or State heading. A heading, or a line under 80 characters, that
names a date no effective-date sentence of its block or the section states,
as "Payment levels as of January 1, 2031", "Effective: January 1, 2031" or
"January 1, 2031", leaves the date unread, and the next chart refuses unless
a later sentence dates it. So does one that holds a date in a form no
sentence reads: an abbreviated month ("Jan. 1, 2031"), a month and year
("January 2031"), a day before its month ("1 January 2031"), or an ISO or
dashed date ("2031-01-01", "1-1-2031"). A footnote body that opens with its
marker and the section's revision line ("Effective Dates: ...") date no
chart and leave the date standing.

Every definition table of a section precedes its first chart; a definition
table after a chart refuses, because the source does not say which earlier
chart it serves. A jointly published code
("C/H" in a definition table, "A or B" in a chart) names each single code it
lists. A chart code that no definition table defines stays undefined and is
recorded in ``poms_open_questions.json``; no definition is inferred for it.

Not modelled: an abbreviation without its period, such as "Calif", or not
in ``_ABBREVIATIONS``, such as "Ia." or "Ut.", and a lower-case postal code
outside parentheses, which name no State to the nets; a caption in a table
cell, or in a chart's own ``caption`` element, which no block holds; text
outside any block, as in a ``span`` or ``strong`` or bare text between
blocks, which is never read, so "Utah (continued)" or "Couple" there neither
names nor resets a State, claimant or date; and text that HTML or CSS
hides, other than script and style, such as the ``hidden`` attribute, which
is read as text, so ``Utah<span hidden>x</span> Effective January 1, 2031``
is read as prose, as "Utahx Effective January 1, 2031" would be. The tree's
own gaps, HTML's script data escape states among them, are listed in
``aggregate_tables``.

Limits: the nets over-refuse in several places, and no pinned page meets
any of them.

- An acronym that spells a postal code names that State. In Pennsylvania's
  section, "(MA recipients)" or "for IA cases" names Massachusetts or Iowa,
  so the page refuses, and so does "DE MINIMIS rule" in Nevada's.
- A line under 80 characters that names another State refuses wherever the
  name stands: one that opens with it, as "California residents who move
  here" in Nevada's section, "New Jersey border counties" in New York's or
  "Washington metropolitan area" in the District's, and one that names it
  later, as "Residents who move from California".
- A heading or line under 80 characters that names two claimant types
  refuses, even where a later claimant line would name the chart's own.
- A heading or line under 80 characters that names a date no sentence
  states makes the next chart refuse, even where the date concerns
  something else, as "Revised March 1, 2031", and a date in a form no
  sentence reads does so even when it is the section's own date, as "Jan.
  1, 2030", or stands in a sentence, as "Payment levels effective January
  2031".
- A footnote marker after a date's year, as "January 1, 2031<sup>1</sup>",
  or an ordinal marker, as "January 1<sup>st</sup>, 2031", makes the
  sentence date differently without it, so the page refuses.

A line of 80 characters or more, outside a heading, names a claimant only
as a claimant line and a date only as an effective-date sentence, and of the
State nets only those before the caption net read it. So one that mentions
a claimant word in prose, states a date in another form, or names another
State in other words leaves the claimant, date or State before it standing.
"""

from __future__ import annotations

import re
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from functools import cache, lru_cache
from typing import Any
from xml.etree import ElementTree as ET

from .aggregate_tables import (
    PARAGRAPH_CLOSERS,
    AggregateCell,
    CellToken,
    TableSpec,
    TableStructureError,
    _cell_token,
    _is_footnote_marker,
    expand_html_table,
    normalized_text,
    parse_html,
    parse_number,
    verify_payload,
)

_STATES = (
    "California",
    "Delaware",
    "District of Columbia",
    "Hawaii",
    "Iowa",
    "Massachusetts",
    "Michigan",
    "Montana",
    "Nevada",
    "New Jersey",
    "New York",
    "Pennsylvania",
    "Rhode Island",
    "Utah",
    "Vermont",
    "Washington",
    "Wisconsin",
)
_POSTAL_CODES = dict(
    zip(
        _STATES,
        "CA DE DC HI IA MA MI MT NV NJ NY PA RI UT VT WA WI".split(),
        strict=True,
    )
)
# "Washington, D.C.", "Washington,DC" and "Washington DC" name the District,
# not the State.
_DISTRICT_ALIAS = r"Washington,?\s*D\.?\s?C\b\.?"
# Other spellings of a State's name, which may head its section.
_SPELLINGS = {"Hawaii": "Hawai[ʻ‘’']?i"}
# Abbreviations that name a State in prose; they never head its section.
# Hawaii, Iowa and Utah have none here.
_ABBREVIATIONS = {
    "California": r"(?:Calif|Cal)\.",
    "Delaware": r"Del\.",
    "District of Columbia": r"D\.\s?C\.",
    "Massachusetts": r"Mass\.",
    "Michigan": r"Mich\.",
    "Montana": r"Mont\.",
    "Nevada": r"Nev\.",
    "New Jersey": r"N\.\s?J\.",
    "New York": r"N\.\s?Y\.",
    "Pennsylvania": r"(?:Penna|Penn|Pa)\.",
    "Rhode Island": r"R\.\s?I\.",
    "Vermont": r"Vt\.",
    "Washington": r"Wash\.",
    "Wisconsin": r"Wisc?\.",
}
_MONTHS = (
    "January February March April May June July August September October "
    "November December"
).split()
_DATE = re.compile(
    r"\b(?:"
    + "|".join(_MONTHS)
    + r")\s+\d{1,2},?\s+\d{4}\b|\b\d{1,2}\s*/\s*\d{1,2}\s*/\s*\d{2,4}\b",
    re.IGNORECASE,
)
# Other ways to write a date, which no effective-date sentence reads: an
# abbreviated month, a month and year with no day, a day before its month,
# and an ISO or dashed date. To the unread-date net they name a date.
_SHORT_MONTHS = r"(?:Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept?|Oct|Nov|Dec)"
_OTHER_DATE = re.compile(
    rf"\b{_SHORT_MONTHS}\.?\s+\d{{1,2}},?\s+\d{{4}}\b"
    rf"|\b(?:{'|'.join(_MONTHS)}|{_SHORT_MONTHS})\.?,?\s+\d{{4}}\b"
    rf"|\b\d{{1,2}}\s+(?:{'|'.join(_MONTHS)}|{_SHORT_MONTHS})\.?,?\s+\d{{4}}\b"
    r"|\b\d{4}-\d{1,2}-\d{1,2}\b|\b\d{1,2}-\d{1,2}-\d{2,4}\b",
    re.IGNORECASE,
)
_HEADINGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})
# Every block that ends a paragraph, apart from a table or rule, is read
# from its own text, so a list item, section or blockquote reads the same
# after a heading as inside one left open, where HTML keeps it.
_BLOCKS = _HEADINGS | (PARAGRAPH_CLOSERS - {"table", "hr"})
# What ends a block's own text. A block other than a heading ends at the
# next block. HTML keeps any other block inside a heading left open, so a
# heading's text runs on through them and ends at a heading or table; a
# table, which HTML also nests in a heading left open, is never heading text.
_TEXT_STOPS = {block: PARAGRAPH_CLOSERS for block in _BLOCKS} | {
    heading: _HEADINGS | {"table"} for heading in _HEADINGS
}


# A br ends a line as a block nested in a heading does.
_LINE_BREAKS = PARAGRAPH_CLOSERS | {"br"}
# Elements whose text HTML never renders; no reading holds it.
_UNRENDERED = frozenset({"script", "style"})
# A footnote marker's text: one to three word characters or footnote signs.
_MARKER_LENGTH = 3
_MARKER_TEXT = re.compile(rf"[\w*†‡§]{{1,{_MARKER_LENGTH}}}")


def _short_texts(element: ET.Element, short: dict[int, str | None]) -> None:
    """Record in ``short``, by id, the text of ``element`` and of each
    element under it when it is no longer than a marker's, else None.

    The text is ``normalized_text``'s, its text nodes joined by spaces and
    whitespace collapsed, without format characters or the text of a
    ``script`` or ``style`` element, as every reading drops them. An
    element's text holds each child's, so a child too long makes its parent
    too long. The walk keeps its own stack and reads each element once, so
    nested candidates cost no more than one.
    """
    pending = [(element, False)]
    while pending:
        node, read = pending.pop()
        if not read:
            pending.append((node, True))
            pending.extend(
                (child, False)
                for child in node
                if child.tag not in _UNRENDERED
            )
            continue
        parts = [node.text or ""]
        for child in node:
            text = "" if child.tag in _UNRENDERED else short[id(child)]
            parts += [text, child.tail or ""]
        text = None if None in parts else _collapse(" ".join(parts))
        short[id(node)] = (
            text if text is not None and len(text) <= _MARKER_LENGTH else None
        )


def _line_marker(element: ET.Element, short: dict[int, str | None]) -> bool:
    """Whether an element of a block's line is a footnote marker: a ``sup``,
    or a link to an anchor on the page (an href starting "#"), whose text
    is one to three word characters or footnote signs, as ``<sup>1</sup>``
    and ``<a href="#fn2">2</a>``. A ``sup`` with longer text, and a link
    elsewhere, are text, so the bare reading drops no word of prose. Table
    cells keep their own, wider rule (``aggregate_tables``'s
    ``_is_footnote_marker``)."""
    if element.tag != "sup" and not (
        element.tag == "a" and element.get("href", "").startswith("#")
    ):
        return False
    if id(element) not in short:
        _short_texts(element, short)
    text = short[id(element)]
    return text is not None and _MARKER_TEXT.fullmatch(text) is not None


def _line_readings(element: ET.Element) -> list[tuple[str, str, str, str]]:
    """A block's own lines, each read four ways: joined, bare, spaced and
    unmarked.

    A line is the block's text between ``br`` tags and where a block nested
    in it starts or ends. In the joined reading the text of inline elements
    joins without a separator, as HTML renders it, so ``U<span>tah</span>``
    reads "Utah". The bare reading is the joined one without footnote
    markers (``_line_marker``: a ``sup``, or a link to an anchor on the
    page, holding one to three word characters or footnote signs), so
    ``Utah<sup>1</sup>`` reads "Utah". The spaced reading puts a space at
    every element's edges, so a name that touches the text of the element
    next to it, as in ``Utah<sup>1</sup>``, still stands as a word. The
    unmarked reading, which only the date checks read, is the joined one
    without any element that either marker rule counts: the bare reading's
    markers, and any ``sup`` or link whose href holds "fn", the rule table
    cells keep (``aggregate_tables``'s ``_is_footnote_marker``). Every
    reading collapses whitespace and drops Unicode format characters, such
    as zero-width spaces and soft hyphens, and no reading holds the text of
    a ``script`` or ``style`` element, which HTML does not render. A line
    is kept when its joined reading holds any text.

    The text stops at the first block that ends the element
    (``_TEXT_STOPS``). Before that only a heading can hold a nested block,
    so a block other than a heading splits only at a ``br``. The walk does
    not recurse, so deep nesting cannot exhaust the interpreter stack.
    """
    stops = _TEXT_STOPS[element.tag]
    short: dict[int, str | None] = {}
    # Each part is a text, whether a footnote marker holds it, and whether
    # an element either marker rule counts holds it.
    lines: list[list[tuple[str, bool, bool]]] = [
        [(element.text or "", False, False)]
    ]
    walk = [(element, iter(element), False, False)]
    while walk:
        node, children, _, _ = walk[-1]
        child = next(children, None)
        if child is None:
            walk.pop()
            if walk:
                if node.tag in _LINE_BREAKS:
                    lines.append([])
                lines[-1].append((node.tail or "", *walk[-1][2:]))
            continue
        if child.tag in stops:
            break
        if child.tag in _UNRENDERED:
            lines[-1].append((child.tail or "", *walk[-1][2:]))
            continue
        if child.tag in _LINE_BREAKS:
            lines.append([])
        marked = walk[-1][2] or _line_marker(child, short)
        noted = walk[-1][3] or marked or _is_footnote_marker(child)
        lines[-1].append((child.text or "", marked, noted))
        walk.append((child, iter(child), marked, noted))
    readings = []
    for parts in lines:
        joined = _collapse("".join(text for text, _, _ in parts))
        if joined:
            bare = "".join(text for text, marked, _ in parts if not marked)
            spaced = " ".join(text for text, _, _ in parts)
            unmarked = "".join(text for text, _, noted in parts if not noted)
            readings.append(
                (
                    joined,
                    _collapse(bare),
                    _collapse(spaced),
                    _collapse(unmarked),
                )
            )
    return readings


def _line_renderings(element: ET.Element) -> list[tuple[str, str, str]]:
    """A block's own lines in the joined, bare and spaced readings of
    ``_line_readings``."""
    return [reading[:3] for reading in _line_readings(element)]


def _collapse(text: str) -> str:
    return " ".join(_blank(text).split())


def _lines(element: ET.Element) -> list[str]:
    """A block's own lines in their joined reading (``_line_renderings``)."""
    return [joined for joined, _, _ in _line_renderings(element)]


def _own_text(element: ET.Element) -> str:
    """Normalize a block's own text, up to the first block that ends it.

    When no block or ``br`` nests inside the element, this is its text
    content with whitespace collapsed and format characters removed.
    Unlike ``normalized_text``, which separates every text node, inline
    elements join without a separator. A heading left open is read without
    the next heading or the table the tree nests under it.
    """
    return " ".join(_lines(element))


def _renderings(element: ET.Element) -> list[tuple[str, str, str, str]]:
    """A block's whole text, then each of its lines, in the joined, bare,
    spaced and unmarked readings of ``_line_readings``."""
    lines = _line_readings(element)
    whole = tuple(
        " ".join(line[k] for line in lines if line[k]) for k in range(4)
    )
    return [whole, *lines]


# What may come before a State's name in its section heading. A dash may be
# a hyphen, an en or em dash, or a minus sign.
_DASH = r"\s*[-‐-―−]\s*"
_HEADING_PREFIX = (
    r"(?:[A-Z]\.\s*)?"
    rf"(?:Description of supplements(?:\s+for\s+(?:the\s+)?|{_DASH})"
    rf"|Procedure{_DASH})?"
)


@cache
def _state_name(name: str) -> str:
    """A pattern for a State's name or another spelling of it, or for the
    District, an alias."""
    if name == "District of Columbia":
        return rf"(?:{re.escape(name)}|{_DISTRICT_ALIAS})"
    return _SPELLINGS.get(name, re.escape(name))


@cache
def _state_reference(name: str) -> str:
    """A pattern for a State's name with its optional postal suffix. The
    2009 and 2010 sections append the code, as in "New Jersey (NJ)"."""
    return _state_name(name) + rf"(?:\s*\({_POSTAL_CODES[name]}\))?"


def _state_heading(name: str, text: str) -> bool:
    return bool(
        re.fullmatch(
            _HEADING_PREFIX + _state_reference(name), text, re.IGNORECASE
        )
    )


def _misnamed_heading(text: str) -> bool:
    """Whether a line has a State heading's shape with a postal code that
    is not that State's, as in "New York (NJ)"."""
    return any(
        re.fullmatch(
            _HEADING_PREFIX + _state_name(name) + r"\s*\([A-Z]{2}\)",
            text,
            re.IGNORECASE,
        )
        and not _state_heading(name, text)
        for name in _STATES
    )


def _state_date_line(text: str) -> str | None:
    """The State a line such as "Nevada Effective 1/1/30" opens with, by
    the names, aliases and postal suffixes its section heading may take."""
    for name in _STATES:
        if re.match(_state_reference(name) + r"\s+Effective\b", text, re.I):
            return name
    return None


def _effective_line(text: str) -> bool:
    return (
        "effective" in text.lower()
        and "Effective Dates:" not in text
        and len(text) < 400
        and bool(
            re.search(r"payments? levels?", text, re.I)
            or text.lower().startswith("effective ")
            or _state_date_line(text)
        )
    )


def _claimant_mention(text: str) -> re.Match[str] | None:
    """Whether a line mentions a claimant: a claimant word that ends it,
    after an optional "payment(s)" and "levels", or that "for" or "or" and
    any text follow, anywhere in the line. Prose such as "A recipient or
    couple qualifies" mentions one. The claimant State guard reads every
    line that mentions a claimant; only a claimant line names one."""
    if len(text) >= 250:
        return None
    return re.search(
        r"(?:^|\s)(Individual|Recipient|Couple)"
        r"(?:\s+payments?)?(?:\s+levels)?"
        r"(?:\s+(?:for|or)\s+.+)?$",
        text,
        re.IGNORECASE,
    )


_CLAIMANT_WORD = r"(?P<word>Individual|Recipient|Couple)"
_CLAIMANT_WORDS = re.compile(r"\b(?:Individual|Recipient|Couple)\b", re.I)
# A claimant word or its plural; the group is the word, so "Couples" names
# a couple.
_CLAIMANT_FORMS = re.compile(r"\b(Individual|Recipient|Couple)s?\b", re.I)
# Any State's name, spelling or District alias, with its optional postal
# suffix.
_ANY_STATE = "(?:" + "|".join(map(_state_reference, _STATES)) + ")"
_CLAIMANT_HEADING = re.compile(
    r"(?:(?:[A-Za-z]|\d{1,2})[.)]\s*)?"
    + _CLAIMANT_WORD
    + r"(?:\s+payments?)?(?:\s+levels?)?"
    + rf"(?:\s+(?:for|or)\s+(?:the\s+)?{_ANY_STATE})?",
    re.IGNORECASE,
)
_CLAIMANT_CAPTION = re.compile(
    r"(?P<prefix>.*\S)\s+" + _CLAIMANT_WORD, re.IGNORECASE
)
_CAPTION_PREFIX_END = re.compile(
    rf"(?:{_DATE.pattern}|{_ANY_STATE})$", re.IGNORECASE
)


def _claimant_line(text: str) -> re.Match[str] | None:
    """A claimant line, the only kind of line that names a chart's claimant.

    It is a heading form, matched as the whole line: an optional list label
    ("a." or "2)"), the claimant word, an optional "payment(s)" and
    "level(s)", and then optionally "for" (or the source's "or"), an
    optional "the" and a State, as in "a. Individual payment levels for
    the District of Columbia". Or it is a caption whose last word is the
    claimant word, after a State date line or an effective-date line that
    ends with a date or a State, as in "Utah Effective 1/1/03 Individual".
    Any other line that holds a claimant word is prose and names none.
    ``match["word"]`` is the claimant word.
    """
    if len(text) >= 250 or not _CLAIMANT_WORDS.search(text):
        return None
    heading = _CLAIMANT_HEADING.fullmatch(text)
    if heading:
        return heading
    caption = _CLAIMANT_CAPTION.fullmatch(text)
    if (
        caption
        and (
            _state_date_line(caption["prefix"])
            or _effective_line(caption["prefix"])
        )
        and _CAPTION_PREFIX_END.search(caption["prefix"])
    ):
        return caption
    return None


def _claimant_type(word: str) -> str:
    """The claimant type a claimant word names, as ``match["word"]`` of a
    claimant line; "Recipient" names an individual."""
    return "couple" if word.lower() == "couple" else "individual"


_STATE_OF_CODE = {code: name for name, code in _POSTAL_CODES.items()}


def _named_states(text: str) -> set[str]:
    """The States a text names: by name, spelling or alias, by an
    abbreviation such as "N.J.", by a postal code in parentheses, in either
    case, as in "(UT)", or by an upper-case postal code standing as a word,
    as in "for UT"."""
    text = re.sub(
        r"\b" + _DISTRICT_ALIAS, "District of Columbia", text, flags=re.I
    )
    named = {
        name
        for name in _STATES
        if re.search(rf"\b{_state_name(name)}\b", text, re.I)
        or name in _ABBREVIATIONS
        and re.search(rf"\b{_ABBREVIATIONS[name]}", text)
    }
    for match in re.finditer(r"\(\s*([A-Za-z]{2})\s*\)", text):
        if match[1].upper() in _STATE_OF_CODE:
            named.add(_STATE_OF_CODE[match[1].upper()])
    for match in re.finditer(r"\b([A-Z]{2})\b", text):
        if match[1] in _STATE_OF_CODE:
            named.add(_STATE_OF_CODE[match[1]])
    return named


def _view_states(view: tuple[str, ...]) -> set[str]:
    """The States any reading of a whole text or line names."""
    return set().union(*map(_named_states, view))


# What may open a State's caption before its name: leading dashes, bullets,
# asterisks, quotation marks, parentheses and spaces; a list label, as a
# claimant line takes ("1.", "2)", "b)"), or one in parentheses ("(b)"); a
# heading's prefix; "The"; and "State of".
_CAPTION_OPENING = (
    r"[-‐-―−•·*\"“‘'(\s]*"
    r"(?:(?:\(?(?:[A-Za-z]|\d{1,2})[.)]|\((?:[A-Za-z]|\d{1,2})\))\s*)?"
    + _HEADING_PREFIX
    + r"(?:The\s+)?(?:State\s+of\s+)?"
)
# For each State, a caption opening with its name, spelling or alias in any
# case, and one opening with its upper-case postal code or abbreviation.
_CAPTIONS = {
    name: (
        re.compile(_CAPTION_OPENING + _state_name(name) + r"\b", re.I),
        re.compile(
            _CAPTION_OPENING
            + rf"(?:{_POSTAL_CODES[name]}\b"
            + (rf"|{_ABBREVIATIONS[name]}" if name in _ABBREVIATIONS else "")
            + ")"
        ),
    )
    for name in _STATES
}


def _opening_states(text: str) -> set[str]:
    """The States a short line, under 80 characters, opens with as a
    caption: after an optional heading prefix and "State of", a State's
    name, spelling or alias in any case, or its abbreviation or upper-case
    postal code, as in "Utah (continued)", "State of Utah", "N.J. notes" or
    "UT (continued)". The District's alias is read first, so "Washington,
    D.C." opens with the District, not with Washington State."""
    if len(text) >= 80:
        return set()
    text = re.sub(
        r"\b" + _DISTRICT_ALIAS, "District of Columbia", text, flags=re.I
    )
    return {
        name
        for name, (spelled, coded) in _CAPTIONS.items()
        if spelled.match(text) or coded.match(text)
    }


# Unicode's format characters (category Cf, Unicode 16.0), such as the
# zero-width space, joiners, the byte order mark and the soft hyphen. They
# are invisible, so they neither separate nor join words.
_FORMAT_CHARACTERS = re.compile(
    "[\u00ad\u0600-\u0605\u061c\u06dd\u070f\u0890\u0891\u08e2\u180e"
    "\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u206f\ufeff"
    "\ufff9-\ufffb\U000110bd\U000110cd\U00013430-\U0001343f"
    "\U0001bca0-\U0001bca3\U0001d173-\U0001d17a\U000e0001"
    "\U000e0020-\U000e007f]"
)


def _blank(text: str) -> str:
    return _FORMAT_CHARACTERS.sub("", text).strip()


def _date_string(text: str) -> str:
    text = re.sub(r"\s*/\s*", "/", text).replace(",", "")
    for fmt in ("%B %d %Y", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    raise TableStructureError("Unrecognized POMS effective date")


# An effective-date sentence that states a range of dates.
_DATE_RANGE = re.compile(r"effective from .+ to ", re.IGNORECASE)
# The section's revision range, as "Effective Dates: 02/03/2040 - Present".
_REVISION = re.compile(
    r"Effective Dates:\s*(\d{2}/\d{2}/\d{4})\s*-\s*"
    r"(Present|\d{2}/\d{2}/\d{4})"
)


def _date_reading(text: str) -> tuple[tuple[str, ...], bool]:
    """The distinct dates an effective-date sentence states, in order, and
    whether it states them as a range ("effective from ... to ...")."""
    dates = dict.fromkeys(_date_string(m[0]) for m in _DATE.finditer(text))
    return tuple(dates), bool(_DATE_RANGE.search(text))


def _named_dates(view: tuple[str, ...]) -> set[str]:
    """The dates a whole text or line names in its joined, bare or unmarked
    reading. A date the reader cannot parse, and one written in a form no
    effective-date sentence reads (``_OTHER_DATE``), names itself by its
    text, so no sentence states it."""
    named = set()
    for text in (view[0], view[1], view[3]):
        for match in _DATE.finditer(text):
            try:
                named.add(_date_string(match[0]))
            except TableStructureError:
                named.add(match[0])
        named.update(match[0] for match in _OTHER_DATE.finditer(text))
    return named


def _footnote_body(view: tuple[str, ...]) -> bool:
    """Whether a whole text or line opens with footnote markers, by either
    marker rule, and holds none after them, as a footnote body does."""
    return any(
        view[0] != text and view[0].endswith(text)
        for text in (view[1], view[3])
    )


@lru_cache(maxsize=32)
def _document(payload: bytes) -> tuple[ET.Element, tuple[ET.Element, ...]]:
    document = parse_html(payload)
    return document, tuple(document.iter("table"))


def describe_poms_tables(payload: bytes) -> tuple[dict[str, Any], ...]:
    """Return structural selectors for payment tables, without amounts.

    The selectors retain the original chart effective-date text and the
    section revision range. More than one chart date is an explicit open
    alternative; it does not silently select either date.
    """
    document, tables = _document(payload)
    section_text = normalized_text(document)
    revision = _REVISION.search(section_text)
    revision_start = _date_string(revision[1]) if revision else None
    revision_end = (
        _date_string(revision[2])
        if revision and revision[2] != "Present"
        else None
    )
    state = None
    claimant = None
    effective_text = ""
    dates: tuple[str, ...] = ()
    # Whether the dates state a range, and whether a later line names a date
    # no sentence states.
    ranged = False
    unread_date = False
    definitions: list[int] = []
    charted = False
    table_indexes = {id(table): i for i, table in enumerate(tables)}
    contexts: list[dict[str, Any]] = []

    def visit(element: ET.Element) -> bool:
        """Read one element; return whether to read its children."""
        nonlocal state, claimant, effective_text, dates, ranged, unread_date
        nonlocal definitions, charted
        if element.tag == "table":
            index = table_indexes[id(element)]
            grid = expand_html_table(element)
            if not grid:
                return False
            first = tuple(_blank(c.text) for c in grid[0])
            if any(
                tuple(_blank(c.text) for c in row) == ("Code", "Definition")
                for row in grid[:3]
            ):
                if charted:
                    # Which of the section's earlier charts a later table
                    # defines codes for is not stated, so refuse rather than
                    # apply it to some charts and not others.
                    raise TableStructureError(
                        f"POMS definition table {index} follows a payment "
                        "chart in its State section"
                    )
                definitions.append(index)
            if len(first) >= 5 and first[0] == "Federal Code":
                if state is None or claimant is None:
                    raise TableStructureError(
                        f"POMS payment table {index} lacks state or claimant context"
                    )
                if unread_date:
                    raise TableStructureError(
                        f"POMS payment table {index} follows a date that no "
                        "effective-date sentence states"
                    )
                # A range dates a chart from and to only with two dates;
                # any other dates remain named alternatives.
                span = ranged and len(dates) == 2
                contexts.append(
                    {
                        "table_index": index,
                        "state": state,
                        "claimant_type": claimant,
                        "header_labels": list(first),
                        "definitions_table_indexes": list(definitions),
                        "effective_from": (
                            dates[0] if len(dates) == 1 or span else None
                        ),
                        "effective_to": dates[1] if span else None,
                        "parameter_effective_date_text": effective_text,
                        "date_options": (
                            {
                                f"source_date_{i + 1}": value
                                for i, value in enumerate(dates)
                            }
                            if len(dates) > 1 and not span
                            else {"not_stated": None} if not dates else {}
                        ),
                        "section_effective_from": revision_start,
                        "section_effective_to": revision_end,
                    }
                )
                charted = True
                # Every chart needs its own claimant line.
                claimant = None
            return False
        if element.tag in _BLOCKS:
            # Only the block's own text: a table or heading nested under a
            # heading left open is read in turn, not as part of it. HTML
            # keeps other blocks inside a heading left open, after its words
            # or around them, and a br breaks a line, so a block is read
            # whole and line by line, each in four readings. The joined and
            # bare readings name the block's State heading and claimant, the
            # joined reading its date; the joined, bare and spaced readings
            # pass the State guards, and the date checks read the unmarked
            # one too.
            full = _renderings(element)
            views = [view[:3] for view in full]
            readings = [view[:2] for view in views]
            # A whole-text State date line stays a date line: its lines do
            # not head a section.
            date_block = any(map(_state_date_line, readings[0]))
            headed = [
                name
                for name in _STATES
                if not date_block
                and any(
                    _state_heading(name, text)
                    for reading in readings
                    for text in reading
                )
            ]
            if len(headed) > 1:
                raise TableStructureError("POMS heading names two States")
            if headed and state != headed[0]:
                state = headed[0]
                claimant = None
                effective_text = ""
                dates = ()
                ranged = False
                unread_date = False
                definitions = []
                charted = False
            if any(
                _state_heading(name, text)
                for name in _STATES
                if name != state
                for view in views
                for text in view
            ):
                # A line shaped as another State's heading that heads no
                # section here, as a line of a whole-text date line or a
                # heading only the spaced reading shows, means that State's
                # section was not read.
                raise TableStructureError(
                    "POMS State changes without a section heading"
                    if date_block
                    else "POMS heading names a State it does not head"
                )
            if any(_misnamed_heading(text) for view in views for text in view):
                # A line shaped as a State heading whose postal code is not
                # its State's heads no section, so its section was not read.
                raise TableStructureError(
                    "POMS heading names a State it does not head"
                )
            # Every line is checked in every reading, so a date line nested
            # in a heading cannot carry another State's date into this
            # section, and an effective-date sentence may name no State but
            # this section's.
            if any(
                any(
                    _state_date_line(text) not in {None, state}
                    for text in view
                )
                or state is not None
                and any(map(_effective_line, view))
                and _view_states(view) - {state}
                for view in views
            ):
                # Definitions are collected per section heading; a State
                # named only in a date line has none of its own, so the
                # reader refuses rather than reuse another State's.
                raise TableStructureError(
                    "POMS State changes without a section heading"
                )
            # The date sentence is chosen as it renders, footnote markers and
            # all, so a footnote body that opens with its marker, as
            # "<sup>1</sup>Effective ...", is no date sentence. A marker inside
            # a sentence, as in "January 1<sup>2</sup>, 2031", would change
            # or hide its date, so a sentence that dates differently without
            # its markers, by either marker rule, refuses, and so does a line
            # that is a dated sentence only without them, unless its markers
            # all lead it. A whole text that is no sentence, as one of 400
            # characters or more, gives each line that is one; lines that date
            # differently remain named alternatives.
            if _effective_line(views[0][0]):
                sentences = [0]
            else:
                sentences = [
                    i
                    for i, view in enumerate(views)
                    if _effective_line(view[0])
                ]
            found = []
            for i in sentences:
                reading = _date_reading(full[i][0])
                if any(_date_reading(full[i][k]) != reading for k in (1, 3)):
                    raise TableStructureError(
                        "POMS effective date reads differently without its "
                        "footnote markers"
                    )
                found.append(reading)
            if found:
                if all(reading == found[0] for reading in found):
                    effective_text = views[sentences[0]][0]
                    dates, ranged = found[0]
                else:
                    effective_text = " ".join(views[i][0] for i in sentences)
                    dates = tuple(
                        dict.fromkeys(
                            day for reading in found for day in reading[0]
                        )
                    )
                    ranged = False
                unread_date = False
            if any(
                _effective_line(text)
                and _DATE.search(text)
                and not _effective_line(view[0])
                and not view[0].endswith(text)
                for view in full
                for text in (view[1], view[3])
            ):
                raise TableStructureError(
                    "POMS effective-date sentence reads only without its "
                    "footnote markers"
                )
            if state is not None:
                # A heading, or a line under 80 characters, that names a date
                # no effective-date sentence states, as "Payment levels as of
                # January 1, 2031", leaves the section's date unread, so the
                # next chart refuses unless a sentence dates it. A footnote
                # body that opens with its marker, and the section's revision
                # line, date no chart.
                stated: set[str] = set()
                exempt: set[str] = set()
                for view in full:
                    days = _named_dates(view)
                    if not days:
                        continue
                    if _footnote_body(view) or _REVISION.search(view[0]):
                        exempt |= days
                    elif element.tag in _HEADINGS or len(view[0]) < 80:
                        stated |= days
                if stated - exempt - set(dates):
                    unread_date = True
            # Before any State heading a claimant line names nothing: the
            # heading resets the claimant, and a chart before it refuses.
            named = False
            for view in views if state is not None else ():
                matches = [_claimant_line(text) for text in view]
                if not any(matches) and not any(map(_claimant_mention, view)):
                    continue
                # Every line that mentions a claimant is guarded, prose
                # included, not only the first, so a block's whole text
                # cannot cover a line nested in it, and a line may name no
                # State but this section's.
                if _view_states(view) - {state}:
                    # The section heading that should have named this State
                    # was not read, so refuse rather than chart it under the
                    # State before it.
                    raise TableStructureError(
                        "POMS claimant line names another State"
                    )
                if not any(matches):
                    # Prose that mentions a claimant names none.
                    continue
                if not any(matches[:2]):
                    raise TableStructureError(
                        "POMS claimant line reads only with its inline "
                        "elements spaced"
                    )
                named = True
            # A block with a claimant line names every claimant word, or its
            # plural, that any view holds, the whole text and prose lines
            # included, so "Individual<br>or couple" names two. A heading, or
            # a line under 80 characters, that holds one but is no claimant
            # line, as "Couple payment levels:" or "Couples", names a
            # claimant the reader does not read: it names none, and the next
            # chart refuses unless a later claimant line names one. Either
            # way two types refuse.
            counted = [
                view
                for view in (views if state is not None else ())
                if named or element.tag in _HEADINGS or len(view[0]) < 80
            ]
            types = {
                _claimant_type(word)
                for view in counted
                for text in view
                for word in _CLAIMANT_FORMS.findall(text)
            }
            if len(types) > 1:
                raise TableStructureError("POMS block names two claimants")
            if named:
                (claimant,) = types
            elif types:
                claimant = None
            if (
                element.tag in _HEADINGS
                and state is not None
                and any(_view_states(view) - {state} for view in views)
            ):
                # Any line of a heading that names another State, in any
                # reading, means that State's section was not read.
                raise TableStructureError(
                    "POMS heading names a State it does not head"
                )
            if state is not None and any(
                _opening_states(text) - {state}
                for view in views
                for text in view
            ):
                # A short line that opens as another State's caption, as
                # "Utah (continued)" or "State of Utah", in a block of any
                # kind, means that State's section was not read. This net
                # and the next run last, so the nets above keep their
                # messages; a line of an h1-h6 heading, one HTML keeps
                # inside a heading left open included, has passed the
                # heading net, which refuses any heading line that names
                # another State.
                raise TableStructureError(
                    "POMS short line opens as another State's caption"
                )
            if state is not None and any(
                len(view[0]) < 80 and _view_states(view) - {state}
                for view in views
            ):
                # A line under 80 characters that names another State
                # anywhere, as "Supplements for Utah", may introduce that
                # State's section in a form no heading takes, so refuse
                # rather than chart the section before it on.
                raise TableStructureError(
                    "POMS short line names another State"
                )
        return True

    # Document order without recursion, so deep nesting cannot exhaust the
    # interpreter stack.
    pending = [document]
    while pending:
        element = pending.pop()
        if visit(element):
            pending.extend(list(element)[::-1])
    return tuple(contexts)


def _payment_rows(table: ET.Element) -> tuple[tuple[CellToken, ...], ...]:
    """Split publisher-stacked subrows while reusing the shared span logic."""
    # The span logic reads a skeleton of the table whose cells hold only a
    # key to the original cell. It is built without recursion, as deepcopy
    # is not, so a deeply nested cell cannot crash the interpreter.
    lookup = {}
    skeleton = ET.Element(table.tag, table.attrib)
    pending = [(table, skeleton)]
    while pending:
        original, copy = pending.pop()
        for child in original:
            node = ET.SubElement(copy, child.tag, child.attrib)
            if child.tag in {"td", "th"}:
                node.text = f"poms-cell-{len(lookup)}"
                lookup[node.text] = child
            else:
                pending.append((child, node))
    rows = []
    for row in expand_html_table(skeleton):
        elements = [lookup.get(token.text) for token in row]
        tokens = [
            _cell_token(element) if element is not None else CellToken("")
            for element in elements
        ]
        segments = [
            (
                [
                    _cell_token(p)
                    for p in element.findall("p")
                    if _blank(normalized_text(p))
                ]
                if element is not None
                else []
            )
            for element in elements
        ]
        grouped = []
        for element in elements:
            groups: list[list[CellToken]] = []
            group: list[CellToken] = []
            for paragraph in (
                element.findall("p") if element is not None else []
            ):
                if _blank(normalized_text(paragraph)):
                    group.append(_cell_token(paragraph))
                elif group:
                    groups.append(group)
                    group = []
            if group:
                groups.append(group)
            grouped.append(groups)
        # Numeric columns determine the subrow count. A single paragraph in
        # the source remains a single cell even when its punctuation is bad.
        count = max([len(parts) for parts in segments[3:]] or [1])
        if count <= 1:
            rows.append(tuple(tokens))
            continue
        for subrow in range(count):
            result = []
            for column, (token, parts, groups) in enumerate(
                zip(tokens, segments, grouped, strict=True)
            ):
                if len(parts) in {0, 1}:
                    result.append(token)
                elif len(parts) == count:
                    result.append(parts[subrow])
                elif (
                    column == 2
                    and count == 2
                    and len(parts) == 3
                    and parts[0].text.startswith(parts[1].text + " ")
                ):
                    # Washington prints the repeated category prefix and its
                    # second county label in adjacent continuation paragraphs.
                    group = parts[:1] if subrow == 0 else parts[1:]
                    result.append(
                        CellToken(
                            " ".join(p.text for p in group),
                            tuple(
                                dict.fromkeys(
                                    f for p in group for f in p.flags
                                )
                            ),
                            token.is_header,
                        )
                    )
                elif len(groups) == count:
                    group = groups[subrow]
                    result.append(
                        CellToken(
                            " ".join(p.text for p in group),
                            tuple(
                                dict.fromkeys(
                                    f for p in group for f in p.flags
                                )
                            ),
                            token.is_header,
                        )
                    )
                elif len(parts) % count == 0:
                    width = len(parts) // count
                    group = parts[subrow * width : (subrow + 1) * width]
                    result.append(
                        CellToken(
                            " ".join(p.text for p in group),
                            tuple(
                                dict.fromkeys(
                                    f for p in group for f in p.flags
                                )
                            ),
                            token.is_header,
                        )
                    )
                else:
                    raise TableStructureError(
                        "POMS stacked rows do not align: "
                        f"subrows={count}, paragraphs={len(parts)}, groups={len(groups)}"
                    )
            rows.append(tuple(result))
    return tuple(rows)


def poms_living_arrangements(
    spec: TableSpec, payload: bytes
) -> dict[str, str]:
    """Return cited State OS code definitions from the same verified section.

    A State's definitions may span several physical tables. Each table is
    read in full and the tables are merged; a code two tables define
    differently raises rather than choosing either definition. A row that
    defines codes jointly, such as "C/H", defines each code it names, and a
    full-width note row defines no code.
    """
    verify_payload(spec, payload)
    _, tables = _document(payload)
    indexes = spec.selector.get("definitions_table_indexes")
    if not indexes:
        raise TableStructureError("POMS definition table is not identified")
    merged: dict[str, str] = {}
    for index in indexes:
        for published, definition in _definitions_table(tables[index]).items():
            for code in poms_code_alternatives(published):
                if merged.get(code, definition) != definition:
                    raise TableStructureError(
                        "POMS living-arrangement code has conflicting "
                        "definitions"
                    )
                merged[code] = definition
    return merged


def poms_code_alternatives(code: str) -> tuple[str, ...]:
    """Return the single State OS codes that a published code names.

    POMS writes some codes jointly: a definition row "C/H" defines both C
    and H, and a chart row "A or B" pays either code the same amount. Any
    other code, joint or not, is returned unchanged.
    """
    parts = tuple(re.split(r"\s*/\s*|\s+or\s+", code.strip()))
    if len(parts) > 1 and all(re.fullmatch(r"[A-Z]", part) for part in parts):
        return parts
    return (code,)


def _definitions_table(table: ET.Element) -> dict[str, str]:
    grid = expand_html_table(table)
    header_index = next(
        (
            index
            for index, row in enumerate(grid[:3])
            if tuple(_blank(c.text) for c in row) == ("Code", "Definition")
        ),
        None,
    )
    if header_index is None:
        raise TableStructureError("POMS code definition headers differ")
    definitions = {}
    previous = None
    physical_rows = list(table.iter("tr"))
    for row_index, row in enumerate(
        grid[header_index + 1 :], header_index + 1
    ):
        code = _blank(row[0].text)
        definition = _blank(row[1].text)
        cells = [
            cell
            for cell in physical_rows[row_index]
            if cell.tag in {"td", "th"}
        ]
        if len(cells) == 1 and int(cells[0].get("colspan", "1")) >= 2:
            # A full-width row is a note on the table, not a code.
            continue
        if not code and previous:
            definitions[previous] += " " + definition
            continue
        if code == previous and len(cells) == 1:
            definitions[previous] += " " + definition
            continue
        if not code and not definition:
            continue
        if not code or code in definitions:
            raise TableStructureError(
                "POMS living-arrangement code is blank or repeats"
            )
        definitions[code] = definition
        previous = code
    return definitions


def _is_header_row(row: tuple[CellToken, ...]) -> bool:
    return all(token.is_header for token in row[3:]) or _blank(
        row[3].text
    ) in {
        "FBR",
        "Federal Benefit Rate (FBR)",
    }


def parse_poms(spec: TableSpec, payload: bytes) -> tuple[AggregateCell, ...]:
    """Verify and parse one State/claimant payment chart into typed cells."""
    verify_payload(spec, payload)
    _, tables = _document(payload)
    selector = spec.selector
    try:
        table = tables[selector["table_index"]]
    except (IndexError, KeyError):
        raise TableStructureError("Missing registered POMS table") from None
    grid = expand_html_table(table)
    header = tuple(_blank(c.text) for c in grid[0]) if grid else ()
    if (
        header != tuple(selector["header_labels"])
        or header[0] != "Federal Code"
    ):
        raise TableStructureError("POMS payment headers differ from registry")
    if len(header) < 5 or len(header) > 8:
        raise TableStructureError("Unexpected POMS payment column count")
    effective = selector.get("effective_from")
    alternate_years = {
        date.fromisoformat(value).year
        for value in selector.get("date_options", {}).values()
        if value
    }
    year = (
        date.fromisoformat(effective).year
        if effective
        else (
            next(iter(alternate_years))
            if len(alternate_years) == 1
            else selector.get("nominal_year") if not alternate_years else None
        )
    )
    if year is not None and year not in spec.years:
        raise TableStructureError("POMS chart year is outside registry")
    federal_code = ""
    state_code = ""
    federal_flags = ()
    state_flags = ()
    logical_rows = _payment_rows(table)
    header_rows = [logical_rows[0]] + [
        row for row in logical_rows[1:] if _is_header_row(row)
    ]
    column_labels = [
        " | ".join(
            dict.fromkeys(
                _blank(row[ci].text)
                for row in header_rows
                if _blank(row[ci].text)
            )
        )
        for ci in range(len(header))
    ]
    repeated_labels = {
        label
        for label in column_labels[3:]
        if label and column_labels[3:].count(label) > 1
    }
    for ci in range(3, len(header)):
        if not column_labels[ci]:
            column_labels[ci] = f"Unlabelled amount column {ci + 1}"
        elif column_labels[ci] in repeated_labels:
            column_labels[ci] += f" | source column={ci + 1}"
    column_flags = [
        tuple(
            dict.fromkeys(
                flag for row in header_rows for flag in row[ci].flags
            )
        )
        for ci in range(len(header))
    ]
    output = []
    for ordinal, row in enumerate(logical_rows[1:], start=1):
        if len(row) != len(header):
            raise TableStructureError("POMS payment row width differs")
        if _is_header_row(row):
            continue
        if _blank(row[0].text):
            federal_code = _blank(row[0].text)
            federal_flags = row[0].flags
        else:
            federal_flags = tuple(dict.fromkeys(federal_flags + row[0].flags))
        if _blank(row[1].text):
            state_code = _blank(row[1].text)
            state_flags = row[1].flags
        else:
            state_flags = tuple(dict.fromkeys(state_flags + row[1].flags))
        category = _blank(row[2].text)
        missing_category = not category
        category = category or "<missing>"
        # The ordinal preserves separately published rows with identical labels.
        key = " | ".join(
            (
                selector["state"],
                selector["claimant_type"],
                f"Federal code={federal_code}",
                f"State OS code={state_code}",
                f"Category={category}",
                f"source row={ordinal}",
            )
        )
        row_cells = []
        for ci, token in enumerate(row[3:], start=3):
            raw = _blank(token.text)
            malformed = bool(re.fullmatch(r"\d{1,3}\.\d{3}\.\d{2}", raw))
            # The source prints two decimal points in these cells. Choosing
            # which punctuation to change would invent an amount.
            try:
                parsed = parse_number("") if malformed else parse_number(raw)
            except TableStructureError:
                raise TableStructureError(
                    f"Unrecognized POMS numeric cell at row {ordinal}, "
                    f"column {ci + 1}"
                ) from None
            label = column_labels[ci]
            flags = (
                federal_flags
                + state_flags
                + row[2].flags
                + token.flags
                + tuple(f for flags in column_flags[:3] for f in flags)
                + column_flags[ci]
            )
            flags += parsed.footnote_flags
            if missing_category:
                flags += ("missing_category",)
            if malformed:
                flags += ("source_numeric_punctuation", "unresolved_amount")
            if not header[ci]:
                flags += ("unlabelled_column",)
            if not effective:
                flags += ("ambiguous_effective_date",)
            row_cells.append(
                AggregateCell(
                    table=spec.identifier,
                    row_key=key,
                    column_key=label,
                    year=year,
                    unit="USD per month",
                    value=parsed.value,
                    footnote_flags=tuple(dict.fromkeys(flags)),
                    effective_from=effective,
                    effective_to=selector.get("effective_to"),
                )
            )
        if (
            len(row_cells) == 3
            and "Total Payment Level" in column_labels[-1]
            and all(cell.value is not None for cell in row_cells)
            and abs(
                row_cells[0].value + row_cells[1].value - row_cells[2].value
            )
            > Decimal("0.02")
        ):
            row_cells = [
                replace(
                    cell,
                    footnote_flags=cell.footnote_flags
                    + ("published_identity_discrepancy",),
                )
                for cell in row_cells
            ]
        output.extend(row_cells)
    return tuple(output)
