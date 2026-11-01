"""Pinned aggregate sources for income and resources, D4.

Invariants
----------
* Every public reader verifies SHA-256 and byte size before parsing.
* One cell retains its table, row, column, year, unit and footnote flags;
  missing and suppressed cells are explicit ``None``, never zero.
* Numeric decoration (separators and footnote markers) changes neither
  magnitude nor sign. Unrecognized numeric text is refused without echoing it.
* HTML merged headers expand to a rectangular grid without losing flags.
* Parsing never prints or logs values. Cell representations omit values.
* Registry roles describe intended use, never admission by an empirical gate.

Registry fragments live with the captures so part 2 can add sources and
parser dispatch entries without changing existing source identities. Annual
Supplement 4.B uses the existing vintage-1 capture without fetching it again.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
CAPTURE_DIRECTORY = Path("data/external/snapshots/income_resources_d4_v1")


@dataclass(frozen=True)
class ParsedNumber:
    """A decimal or an explicit missing marker, with source flags."""

    value: Decimal | None = field(repr=False)
    footnote_flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class AggregateCell:
    """One published cell; representations disclose structure only."""

    table: str
    row_key: str
    column_key: str
    year: int | None
    unit: str
    value: Decimal | None = field(repr=False)
    footnote_flags: tuple[str, ...] = ()
    effective_from: str | None = None
    effective_to: str | None = None


@dataclass(frozen=True)
class CellToken:
    """An HTML cell after superscript extraction and span expansion."""

    text: str = field(repr=False)
    flags: tuple[str, ...] = ()
    is_header: bool = False


@dataclass(frozen=True)
class TableSpec:
    """Identity, coverage and intended role of one captured table."""

    identifier: str
    publisher: str
    edition: str
    url: str
    capture_file: str
    sha256: str
    byte_size: int
    retrieved_at: str
    units: tuple[str, ...]
    years: tuple[int, ...]
    geography: tuple[str, ...]
    parser: str
    role: str
    selector: dict[str, Any] = field(default_factory=dict)
    record_kind: str = "table"


class CaptureMismatchError(ValueError):
    """Capture bytes differ from the registered identity."""


class TableStructureError(ValueError):
    """A source no longer has the adjudicated structure."""


_MISSING = {
    "": "missing",
    "...": "not_available",
    "..": "not_available",
    "…": "not_available",
    "—": "not_available",
    "–": "not_available",
    "-": "not_available",
    "--": "not_available",
    "n/a": "not_available",
    "na": "not_available",
    "none": "not_available",
    "nd": "not_available",
    "n.a.": "not_available",
    "(na)": "not_available",
    "(x)": "not_applicable",
    "(d)": "suppressed",
    "d": "suppressed",
    "s": "suppressed",
    "(s)": "suppressed",
    "*": "suppressed",
    "**": "suppressed",
    "(z)": "rounded_nonzero",
}


def parse_number(raw: str) -> ParsedNumber:
    """Parse publisher numeric tokens without treating missing as zero.

    Letter/symbol suffixes and bracketed footnote numbers are retained as
    flags. Numeric superscripts must be extracted from HTML before this call;
    a trailing ordinary digit always remains part of the numeric value.
    """
    token = raw.strip().replace("−", "-")
    compact = re.sub(r"\s+", "", token).lower()
    if compact in _MISSING:
        return ParsedNumber(None, (_MISSING[compact],))
    flags = []
    while match := re.search(
        r"\[([^\]]+)\]$|([a-zA-Z*†‡¹²³⁴⁵⁶⁷⁸⁹⁰]+)$"
        r"|(?<=\d)\s*\(([a-zA-Z0-9]+)\)$",
        token,
    ):
        if re.sub(r"\s+", "", token).lower() in _MISSING:
            break
        if match.start() == 0:
            raise TableStructureError("Unrecognized numeric cell")
        flags.append(next(group for group in match.groups() if group))
        token = token[: match.start()].strip()
    compact = re.sub(r"\s+", "", token).lower()
    if compact in _MISSING:
        return ParsedNumber(None, (_MISSING[compact], *reversed(flags)))
    if token.endswith("%"):
        token = token[:-1].strip()
    negative = token.startswith("(") and token.endswith(")")
    if negative:
        token = token[1:-1].strip()
    token = re.sub(r"^([+-]?)\s*\$\s*", r"\1", token).strip()
    if negative and token.startswith(("-", "+")):
        raise TableStructureError("Unrecognized numeric cell")
    # Commas and spaces may separate groups, but malformed commas are refused.
    token = re.sub(r"[\s\u00a0\u202f]", "", token)
    if not re.fullmatch(
        r"[+-]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d*)?|\.\d+)", token
    ):
        raise TableStructureError("Unrecognized numeric cell")
    try:
        value = Decimal(token.replace(",", ""))
    except InvalidOperation:
        raise TableStructureError("Unrecognized numeric cell") from None
    if negative:
        value = -value
    return ParsedNumber(value, tuple(reversed(flags)))


# Start tags that close an open paragraph in the WHATWG HTML parsing rules
# ("in body" insertion mode), with table as in standards mode.
PARAGRAPH_CLOSERS = frozenset(
    """address article aside blockquote center dd details dialog dir div dl
    dt fieldset figcaption figure footer form h1 h2 h3 h4 h5 h6 header
    hgroup hr li listing main menu nav ol p plaintext pre search section
    summary table ul xmp""".split()
)


class _HTMLTree(HTMLParser):
    """Build a tolerant stdlib tree; publishers' void tags never nest.

    The tree is the same under every supported Python. Python 3.13 reads
    only script and style as raw text and 3.14 also xmp, iframe, noembed
    and noframes, so the tree pins the set to HTML's raw text elements
    (noscript is markup, as in HTML with scripting off). Python 3.14 reads
    everything after a ``plaintext`` start tag as text, as HTML does, and
    3.13 reads it as markup, so the tree refuses a page with one. It
    refuses a page holding "<!-->" or "<!--->", an empty comment that HTML
    closes at that ``>``: 3.14 closes it there, and 3.13 runs on to a later
    "-->". It refuses a page whose script text holds "<!--" and then a
    script start tag (``<script`` and a character Python's ``\\s`` matches,
    "/" or ">", in any case ``re.IGNORECASE`` matches): HTML's script data
    escape states may run that script on past its next ``</script>``, and
    both Pythons end it there. The check refuses more pages than HTML runs
    on: HTML does not run on when "-->" comes between, ``\\s`` also matches
    a vertical tab and Unicode spaces such as U+00A0, which do not end the
    tag name there in HTML, and ``re.IGNORECASE`` matches a long s (ſ) as s
    and "İ" or "ı" as i, so "<ſcript>" counts too. It refuses a page with a
    script, style, xmp, iframe, noembed, noframes, textarea or title start
    tag that closes itself, as ``<script/>``: HTML ignores that slash,
    except where it parses svg or math, and reads what follows as the
    element's text, and both Pythons read it as markup (no pinned capture
    self-closes one).

    An ``html`` start tag builds the html element only as the document's
    first content. HTML ignores any later one, apart from adding the
    attributes it lacks to that element, and so does this tree. On a page
    that opens with other content, HTML implies the html element; the
    document root stands for it here and takes those attributes. A newline
    that comes right after a pre, listing or textarea start tag is dropped,
    as HTML drops it.

    Paragraphs, headings, buttons, cells, rows, table sections, captions
    and colgroups end where the WHATWG parsing rules end them, even when the
    source omits the end tag, so a paragraph never holds the headings and
    tables that follow it. ``table`` closes an open paragraph as in
    standards mode; every pinned HTML capture declares a doctype. Any h1-h6
    end tag ends the open heading in scope, whichever its level, a button
    start tag ends an open button in scope, and a list item start tag (li,
    or dd and dt) ends the open one unless a special element other than
    address, div or p is open inside it. A caption, colgroup or
    table section start tag ends the open cell, row, section, caption or
    colgroup of its table, and so does a ``col`` start tag outside a
    colgroup, since HTML gives it a colgroup of its own. A row or cell start
    tag ends an open caption or colgroup. A row that starts directly in a
    table starts the tbody HTML implies for it, and a cell that starts
    outside a row starts the implied row. A table start tag in a table,
    outside a cell or caption, ends that table first.

    End tags close only what HTML lets them close: a table part's end tag
    closes it within its own table, ``</table>`` the innermost table,
    ``</p>`` a paragraph in button scope (or, with none, leaves an empty
    one, as HTML does), ``</li>`` a list item in list item scope, and
    another special element's end tag (WHATWG's "special" category) that
    element in scope; other end tags are ignored. ``</br>`` is a ``br``,
    and ``</body>`` and ``</html>`` close nothing. Any other end tag, such
    as ``</span>``, ``</b>`` or ``</noscript>``, closes the innermost
    element it names unless a special element is open inside that one, in
    which case it is ignored. A table part's start tag (caption, colgroup,
    col, a table section, row or cell) outside any table is ignored, as in
    HTML.

    Not modelled: HTML's adoption agency rules, which also move a
    formatting element such as ``b`` across the block that ends it (the
    block's text is the same here), and HTML's reopening of a formatting
    element left open, so that a heading that starts while one is reopened
    nests in the open heading, which here it ends (in
    ``<h3>w0<b><i>w1</b>w2<h4>w3``, HTML's h3 reads "w0w1w2w3" and this
    tree's "w0w1w2"); leading content that HTML moves into a head it
    implies, such as a noscript first on a page with no html start tag,
    which stays in place here (no reader reads a head); content that HTML
    moves out of a table to just before it (foster parenting), which stays
    in the table here;
    a form start tag inside an open form, which HTML ignores and which here
    starts a form that ends the open paragraph (in
    ``<form><p>w0<form>w1</form><p>w2``, HTML's first paragraph reads
    "w0w1" and this tree's "w0"; no pinned capture opens a form inside
    another); a self-closing slash on another non-void element, which HTML
    ignores and which closes the element here; a head or body start tag
    after the page's head, which HTML ignores and which here starts an
    element (no pinned capture has more than one of either); a CDATA
    section in HTML content, which HTML reads as a comment ending at the
    first ``>`` and which here holds no text; HTML's script data escape
    states, in which a script holding "<!--" and then a script start tag
    may run on past its next ``</script>``: here the script ends there, so
    the tree refuses a page whose script text holds both (no pinned script
    does);
    and foreign content, the elements inside ``svg`` or ``math``, which
    HTML parses by other rules. HTML ends an open svg or math at the start
    tag of one of its breakout elements, among them h1 to h6, p, div, li,
    table, b and span, and at a font start tag with a color, face or size
    attribute; it builds any other start tag there, such as section, td or
    form, as a foreign element, which it does not render as a block or
    cell. Inside svg's foreignObject, desc or title, MathML's mi, mo, mn,
    ms or mtext, or an annotation-xml whose encoding is text/html, it
    builds HTML elements again, and an end tag there, as ``</h5>`` in
    ``<h5><math><mi></h5>``, does not end the heading outside them. The
    tree models none of this, so it refuses a page on which a start tag
    other than an svg or MathML element of ``_FOREIGN_VOCABULARY`` comes
    inside svg or math, or on which svg or math ends other than at its own
    end tag, the end of the page included. It refuses
    ``<svg><h3>Utah</h3></svg>``, whose h3 HTML builds after the svg, as it
    refuses ``<svg><section>Couple</section></svg>`` and ``<svg><td>``,
    which HTML builds as foreign elements. Outside those integration
    points, HTML reads the content of a script, style, title or textarea
    there as markup and honours a self-closing slash, so in
    ``<svg><script><h3>Utah</h3></script></svg>`` HTML reads a Utah heading
    that this tree holds as script text. The tree refuses a page whose svg
    or math holds a raw text or RCDATA element whose text holds "<", even
    where HTML reads the same text, as in
    ``<svg><style>a < b</style></svg>`` or a script in a foreignObject, and
    its refusal of a self-closed raw text tag covers those HTML closes
    there, as ``<svg><title/></svg>``. No pinned svg, all icons of path,
    title and desc elements, meets any of these refusals, and no pinned
    page holds math.
    """

    # HTML's raw text elements; Python versions differ (see above).
    CDATA_CONTENT_ELEMENTS = (
        "script",
        "style",
        "xmp",
        "iframe",
        "noembed",
        "noframes",
    )
    # Elements whose content the tree holds as text: the raw text elements
    # and HTML's RCDATA elements, which both Pythons read as RCDATA.
    _TEXT_CONTENT = frozenset(CDATA_CONTENT_ELEMENTS) | {"textarea", "title"}
    _VOID = frozenset(
        "area base br col embed hr img input link meta param source track wbr".split()
    )
    _HEADINGS = frozenset("h1 h2 h3 h4 h5 h6".split())
    # An element is in scope unless one of these encloses it, and in button
    # scope unless a button does too.
    _SCOPE = frozenset(
        "applet caption html marquee object select table td template th".split()
    )
    _BUTTON_SCOPE = _SCOPE | {"button"}
    _TABLE_SECTIONS = frozenset("table thead tbody tfoot".split())
    # Start tags that clear the stack back to a table context.
    _TABLE_CONTEXT = frozenset("caption colgroup thead tbody tfoot".split())
    # End tags that close only within their own table.
    _TABLE_PARTS = frozenset(
        "caption colgroup tbody td tfoot th thead tr".split()
    )
    # WHATWG's "special" HTML elements.
    _SPECIAL = frozenset(
        """address applet area article aside base basefont bgsound blockquote
        body br button caption center col colgroup dd details dir div dl dt
        embed fieldset figcaption figure footer form frame frameset h1 h2 h3
        h4 h5 h6 head header hgroup hr html iframe img input keygen li link
        listing main marquee menu meta nav noembed noframes noscript object
        ol p param plaintext pre script search section select source style
        summary table tbody td template textarea tfoot th thead title tr
        track ul wbr xmp""".split()
    )

    # Start tags after which HTML drops a newline that comes next.
    _NEWLINE_DROPPING = frozenset({"pre", "listing", "textarea"})
    # The svg and MathML elements that may start inside svg or math, in
    # HTMLParser's lower case; any other start tag there refuses the page.
    _FOREIGN_VOCABULARY = frozenset(
        """svg math path g title desc circle rect line polyline polygon
        ellipse use defs symbol clippath lineargradient radialgradient stop
        mask pattern text tspan image metadata style script foreignobject mi
        mo mn ms mtext mrow msup msub msubsup mfrac msqrt mroot mstyle mspace
        mtable mtr mtd semantics annotation annotation-xml""".split()
    )

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = ET.Element("document")
        self.stack = [self.root]
        # Whether the last token built one of _NEWLINE_DROPPING.
        self._drop_newline = False
        # The open svg and math elements, each with its place on the stack.
        self._foreign: list[tuple[int, ET.Element]] = []

    def _open_foreign(self) -> int:
        """How many svg and math elements are open.

        The stack only grows or loses its top, so when an entry's place no
        longer holds its element, the tree has popped that element and
        every later entry's with it.
        """
        while self._foreign:
            place, element = self._foreign[-1]
            if place < len(self.stack) and self.stack[place] is element:
                break
            self._foreign.pop()
        return len(self._foreign)

    def _close_paragraph(self) -> None:
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == "p":
                del self.stack[i:]
                return
            if self.stack[i].tag in self._BUTTON_SCOPE:
                return

    def _close_open(self, closes: set[str], bounds: frozenset[str]) -> None:
        """Pop the innermost open ``closes`` element below ``bounds``."""
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag in closes:
                del self.stack[i:]
                return
            if self.stack[i].tag in bounds:
                return

    def handle_starttag(self, tag, attrs):
        self._drop_newline = False
        if tag == "plaintext":
            raise TableStructureError("HTML plaintext element is not read")
        if self._open_foreign() and tag not in self._FOREIGN_VOCABULARY:
            # HTML ends the svg or math at some HTML start tags and keeps
            # the others there as foreign elements; the tree models neither.
            raise TableStructureError(
                "HTML element other than svg or MathML starts inside svg or "
                "math"
            )
        if tag == "html" and (
            len(self.root) or (self.root.text or "").strip("\t\n\f\r ")
        ):
            # Only the document's first content builds the html element. A
            # page that opens with other content implies it, and the root
            # stands for it.
            first = self.root.find("html")
            if first is None:
                first = self.root
            for key, value in attrs:
                first.attrib.setdefault(key, value or "")
            return
        if tag in self._TABLE_PARTS | {"col"} and all(
            node.tag != "table" for node in self.stack
        ):
            # HTML ignores a table part's start tag outside any table.
            return
        if tag in PARAGRAPH_CLOSERS:
            self._close_paragraph()
        if tag in self._HEADINGS and self.stack[-1].tag in self._HEADINGS:
            self.stack.pop()
        if tag == "button":
            self._close_open({"button"}, self._SCOPE)
        if tag in {"li", "dd", "dt"}:
            # A list item ends the open one, unless a special element other
            # than address, div or p is open inside it.
            closes = {"li"} if tag == "li" else {"dd", "dt"}
            for i in range(len(self.stack) - 1, 0, -1):
                if self.stack[i].tag in closes:
                    del self.stack[i:]
                    break
                if self.stack[i].tag in self._SPECIAL - {
                    "address",
                    "div",
                    "p",
                }:
                    break
        if tag == "table":
            for node in reversed(self.stack):
                if node.tag in {"td", "th", "caption"}:
                    break
                if node.tag in self._TABLE_SECTIONS | {"tr", "colgroup"}:
                    # A table directly in a table ends it, as in HTML.
                    self._close_open({"table"}, frozenset())
                    break
        if tag in self._TABLE_CONTEXT or (
            tag == "col" and self.stack[-1].tag != "colgroup"
        ):
            # Anything open in the innermost table ends with it.
            for i in range(len(self.stack) - 1, 0, -1):
                if self.stack[i].tag == "table":
                    del self.stack[i + 1 :]
                    break
        if tag in {"tr", "td", "th"}:
            self._close_open({"caption", "colgroup"}, frozenset({"table"}))
        if tag in {"td", "th"}:
            # A new cell closes the open one, with anything left open in it.
            self._close_open({"td", "th"}, self._TABLE_SECTIONS | {"tr"})
        if tag == "tr":
            self._close_open({"td", "th", "tr"}, self._TABLE_SECTIONS)
            self._close_open({"tr"}, self._TABLE_SECTIONS)
        if tag in {"tr", "td", "th"} and self.stack[-1].tag == "table":
            # HTML puts a row that starts directly in a table in a tbody.
            self.stack.append(ET.SubElement(self.stack[-1], "tbody"))
        if tag in {"td", "th"} and self.stack[-1].tag in self._TABLE_SECTIONS:
            # HTML implies the row of a cell that starts outside one.
            self.stack.append(ET.SubElement(self.stack[-1], "tr"))
        el = ET.SubElement(self.stack[-1], tag, {k: v or "" for k, v in attrs})
        if tag not in self._VOID:
            self.stack.append(el)
            if tag in {"svg", "math"}:
                # The check above dropped every entry popped before this
                # tag, and an svg or math start tag pops nothing.
                self._foreign.append((len(self.stack) - 1, el))
        self._drop_newline = tag in self._NEWLINE_DROPPING

    def handle_startendtag(self, tag, attrs):
        if tag in self._TEXT_CONTENT:
            # HTML ignores the slash and reads what follows as the
            # element's text; both Pythons read it as markup.
            raise TableStructureError(
                "HTML self-closed raw text element is not read"
            )
        self.handle_starttag(tag, attrs)
        if tag not in self._VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        self._drop_newline = False
        open_foreign = self._open_foreign()
        innermost = self._foreign[-1][1].tag if open_foreign else None
        self._end_tag(tag)
        # An end tag that names the innermost svg or math ends only that
        # one, since it closes the innermost element of its name.
        ended = open_foreign - self._open_foreign()
        if ended and tag != innermost:
            # Only its own end tag ends an svg or math as HTML ends it.
            raise TableStructureError(
                "HTML svg or math ends without its own end tag"
            )

    def close(self):
        super().close()
        if self._open_foreign():
            raise TableStructureError(
                "HTML svg or math ends without its own end tag"
            )

    def _end_tag(self, tag):
        """Close what an end tag closes, by the rules above."""
        if tag in self._HEADINGS:
            # Any h1-h6 end tag ends the open heading in scope.
            self._close_open(self._HEADINGS, self._SCOPE)
        elif tag == "br":
            self.handle_starttag("br", [])
        elif tag in {"body", "html"}:
            return
        elif tag == "table":
            self._close_open({"table"}, frozenset())
        elif tag in self._TABLE_PARTS:
            self._close_open({tag}, frozenset({"table"}))
        elif tag == "p":
            depth = len(self.stack)
            self._close_open({"p"}, self._BUTTON_SCOPE)
            if len(self.stack) == depth:
                # With no paragraph to close, HTML inserts an empty one.
                ET.SubElement(self.stack[-1], "p")
        elif tag == "li":
            self._close_open({"li"}, self._SCOPE | {"ol", "ul"})
        elif tag in self._SPECIAL - {"noscript"}:
            self._close_open({tag}, self._SCOPE)
        else:
            # Any other end tag, noscript's included (HTML with scripting
            # off gives it no rule of its own).
            for i in range(len(self.stack) - 1, 0, -1):
                if self.stack[i].tag == tag:
                    del self.stack[i:]
                    return
                if self.stack[i].tag in self._SPECIAL:
                    return

    def handle_data(self, data):
        if self._drop_newline:
            self._drop_newline = False
            data = data.removeprefix("\n")
            if not data:
                return
        parent = self.stack[-1]
        if len(parent):
            parent[-1].tail = (parent[-1].tail or "") + data
        else:
            parent.text = (parent.text or "") + data

    def handle_comment(self, data):
        # A comment, declaration or processing instruction is a token, so
        # a newline after it is text.
        self._drop_newline = False

    handle_decl = handle_pi = unknown_decl = handle_comment


def parse_html(payload: bytes | str) -> ET.Element:
    """Build a tolerant HTML tree without fetching external resources.

    The end of the page ends any element left open, as in HTML, so the text
    of a raw text element without its end tag is kept. As in HTML, CR LF
    and a lone CR read as one newline.
    """
    text = (
        payload.decode("utf-8", errors="replace")
        if isinstance(payload, bytes)
        else payload
    )
    if re.search("<!---?>", text):
        raise TableStructureError("HTML comment closes abruptly")
    # HTML reads CR LF, and a lone CR, as one newline.
    text = re.sub(r"\r\n?", "\n", text)
    parser = _HTMLTree()
    parser.feed(text)
    parser.close()
    for script in parser.root.iter("script"):
        # After "<!--" and a script start tag, HTML's script data may run
        # on past the next "</script>" (its double-escaped state), which no
        # supported Python reads, so the page is refused.
        opened = (script.text or "").find("<!--")
        if opened >= 0 and re.search(
            r"<script[\s/>]", script.text[opened:], re.IGNORECASE
        ):
            raise TableStructureError("HTML script holds an escaped script")
    for foreign in ("svg", "math"):
        for outer in parser.root.iter(foreign):
            # HTML reads markup inside svg or math, so a raw text or RCDATA
            # element there whose text holds "<" may hide what HTML shows.
            if any(
                element.tag in _HTMLTree._TEXT_CONTENT
                and "<" in (element.text or "")
                for element in outer.iter()
            ):
                raise TableStructureError(
                    "HTML raw text inside svg or math holds markup"
                )
    return parser.root


def _is_footnote_marker(element: ET.Element) -> bool:
    """Whether an element is a footnote marker: a ``sup``, or a link to a
    footnote."""
    return element.tag == "sup" or (
        element.tag == "a" and "fn" in element.get("href", "").lower()
    )


def normalized_text(element: ET.Element) -> str:
    """Normalize whitespace in a label or cited passage."""
    return " ".join(" ".join(element.itertext()).split())


def _cell_token(element: ET.Element) -> CellToken:
    """Read a cell's text and footnote flags in document order.

    The walk keeps its own stack, so a deeply nested cell cannot exhaust
    Python's. A pending item is an element to read, a one-element tuple
    holding a footnote marker, or a tail string.

    A ``br`` or nested block joins its lines with a space, so two amounts
    stacked that way in one cell would read as one space-grouped number.
    No pinned cell joins two amounts by a ``br`` within one paragraph: no
    ``br`` there, or run of them, sits between a line ending in a digit and
    one starting with a digit or "$". POMS charts stack amounts in
    paragraphs, which the POMS reader splits into subrows.
    """
    flags = []
    parts = []
    pending: list[ET.Element | tuple[ET.Element] | str] = [element]
    while pending:
        item = pending.pop()
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, tuple):
            flag = normalized_text(item[0])
            if flag:
                flags.append(flag)
        else:
            parts.append(item.text or "")
            for child in list(item)[::-1]:
                pending.append(child.tail or "")
                footnote = _is_footnote_marker(child)
                pending.append((child,) if footnote else child)
    text = " ".join(" ".join(parts).split())
    return CellToken(text, tuple(flags), element.tag == "th")


def expand_html_table(table: ET.Element) -> tuple[tuple[CellToken, ...], ...]:
    """Expand row/column spans, retaining header and footnote identity."""
    grid: dict[tuple[int, int], CellToken] = {}
    rows = list(table.iter("tr"))
    width = 0
    for ri, row in enumerate(rows):
        ci = 0
        for el in row:
            if el.tag not in {"th", "td"}:
                continue
            while (ri, ci) in grid:
                ci += 1
            try:
                rowspan = int(el.get("rowspan", "1"))
                colspan = int(el.get("colspan", "1"))
            except ValueError:
                raise TableStructureError("Invalid HTML span") from None
            if not (1 <= rowspan <= 1000 and 1 <= colspan <= 1000):
                raise TableStructureError("Invalid HTML span")
            token = _cell_token(el)
            for rr in range(ri, ri + rowspan):
                for cc in range(ci, ci + colspan):
                    if (rr, cc) in grid:
                        raise TableStructureError("Overlapping HTML spans")
                    grid[rr, cc] = token
            ci += colspan
            width = max(width, ci)
    if any(ri >= len(rows) for ri, _ in grid):
        raise TableStructureError("HTML rowspan exceeds table")
    empty = CellToken("")
    return tuple(
        tuple(grid.get((ri, ci), empty) for ci in range(width))
        for ri in range(len(rows))
    )


def load_registry(root: Path | None = None) -> dict[str, TableSpec]:
    """Load additive registry fragments; duplicate identifiers are refused."""
    directory = (root or ROOT) / CAPTURE_DIRECTORY
    registry = {}
    for path in sorted(directory.glob("*_registry.json")):
        for entry in json.loads(path.read_text()):
            for key in ("units", "years", "geography"):
                entry[key] = tuple(entry[key])
            spec = TableSpec(**entry)
            if spec.identifier in registry:
                raise TableStructureError("Duplicate registry identifier")
            registry[spec.identifier] = spec
    return registry


def read_verified(spec: TableSpec, root: Path | None = None) -> bytes:
    """Read only registered bytes, checking hash and length before parsing."""
    root = (root or ROOT).resolve()
    path = (root / spec.capture_file).resolve()
    if not path.is_relative_to(root):
        raise CaptureMismatchError(
            f"Capture path escapes root: {spec.identifier}"
        )
    raw = path.read_bytes()
    verify_payload(spec, raw)
    return raw


def verify_payload(spec: TableSpec, payload: bytes) -> None:
    """Refuse unregistered bytes even when a parser is called directly."""
    if (
        len(payload) != spec.byte_size
        or hashlib.sha256(payload).hexdigest() != spec.sha256
    ):
        raise CaptureMismatchError(
            f"Capture identity mismatch: {spec.identifier}"
        )


def parse_table(
    table: str | TableSpec, root: Path | None = None
) -> tuple[AggregateCell, ...]:
    """Verify capture identity then dispatch one registered table parser."""
    spec = load_registry(root)[table] if isinstance(table, str) else table
    payload = read_verified(spec, root)
    if spec.record_kind != "table":
        raise TableStructureError(
            f"Reference is not a numeric table: {spec.identifier}"
        )
    if spec.parser == "ssa_4b":
        return parse_ssa_4b(spec, payload)
    if spec.parser == "poms":
        from .aggregate_poms import parse_poms

        return parse_poms(spec, payload)
    if spec.parser in {"coverage", "census"}:
        from . import aggregate_coverage

        return getattr(aggregate_coverage, f"parse_{spec.parser}")(
            spec, payload
        )
    if spec.parser in {"fed", "dol", "irs"}:
        from . import aggregate_pensions

        return getattr(aggregate_pensions, f"parse_{spec.parser}")(
            spec, payload
        )
    raise TableStructureError(f"Unregistered parser: {spec.identifier}")


def parse_ssa_4b(spec: TableSpec, payload: bytes) -> tuple[AggregateCell, ...]:
    """Parse four Supplement 4.B tables with hierarchical column labels."""
    verify_payload(spec, payload)
    document = parse_html(payload)
    section = next(
        (el for el in document.iter() if el.get("id") == spec.selector["id"]),
        None,
    )
    if section is None:
        raise TableStructureError(f"Missing HTML section: {spec.identifier}")
    table = section.find(".//table")
    if table is None:
        raise TableStructureError(f"Missing HTML table: {spec.identifier}")
    head = table.find("thead")
    body = table.find("tbody")
    if head is None or body is None:
        raise TableStructureError(f"Missing table sections: {spec.identifier}")
    header_grid = expand_html_table(head)
    columns = []
    column_flags = []
    for ci in range(1, len(header_grid[0])):
        tokens = [row[ci] for row in header_grid]
        labels = list(dict.fromkeys(t.text for t in tokens if t.text))
        columns.append(" | ".join(labels))
        column_flags.append(
            tuple(dict.fromkeys(f for t in tokens for f in t.flags))
        )
    units = spec.selector["column_units"]
    if (
        len(columns) != len(units)
        or len(set(columns)) != len(columns)
        or any(unit not in spec.units for unit in units)
    ):
        raise TableStructureError(f"Column layout mismatch: {spec.identifier}")
    cells = []
    for row in expand_html_table(body):
        if len(row) != len(columns) + 1:
            raise TableStructureError(f"Row width mismatch: {spec.identifier}")
        key = row[0].text
        year = int(key) if re.fullmatch(r"\d{4}", key) else spec.years[0]
        if year not in spec.years:
            raise TableStructureError(
                f"Year outside registry: {spec.identifier}"
            )
        for ci, token in enumerate(row[1:]):
            number = parse_number(token.text)
            flags = tuple(
                dict.fromkeys(
                    row[0].flags
                    + column_flags[ci]
                    + token.flags
                    + number.footnote_flags
                )
            )
            cells.append(
                AggregateCell(
                    spec.identifier,
                    key,
                    columns[ci],
                    year,
                    units[ci],
                    number.value,
                    flags,
                )
            )
    keys = [(cell.row_key, cell.column_key, cell.year) for cell in cells]
    if len(keys) != len(set(keys)):
        raise TableStructureError(
            f"Duplicate cell identity: {spec.identifier}"
        )
    return tuple(cells)
