"""Track B readings pass of October 23, 2026: markers, notes and new quotes.

Verification class: statutory conformance and documentation integrity on
captured sources only. No population, behavioral or forecast claim.
Markers: the scan reads every file in the Track B package, subpackages
included, whose suffix in any case is in ``SOURCES``, except the
``OWN_REGISTERS`` at the top of the package. With its markers removed, a
scanned file must hold nothing ``STRAYS`` matches. The ``MARKER`` ids are
exactly ``READINGS`` plus ``OTHER_ROUNDS``, each in the G, R2, R3 or grace
module, and each is ``DOCUMENTED`` in a Track B design note. Notes: G, R2
and R3 name their ``READINGS`` the same way, and none has a heading line,
as ``_headings`` reads them, that ``JUDGMENT`` matches once ``_plain``
cleans it. Quotes: each new statutory excerpt appears in its capture as
``source_text`` normalizes it, with each run of whitespace read as one
space.
"""

import html
import re
from pathlib import Path

import pytest

from tests.track_b_gross_benefit_support import source_text

ROOT = Path(__file__).parents[1]
MODULES = ROOT / "src" / "populace_dynamics" / "track_b"
NOTES = {
    "G": ROOT / "docs/design/track_b_g_gross_benefits.md",
    "R2": ROOT / "docs/design/track_b_r2_ret_ledger.md",
    "R3": ROOT / "docs/design/track_b_r3_arf_recompute.md",
}

#: Logged readings with a decision line in G, R2 or R3, by note.
READINGS = {
    "G": {
        "us:oasdi-family-maximum-saving-clause",
        "us:oasdi-saving-clause-operational-rate-rounding",
        "us:oasdi-saving-clause-procedure-gaps",
        "us:oasdi-dual-entitlement-zero-after-age-reduction",
        "us:oasdi-parent-entitlement-count-interval",
        "us:oasdi-dwb-1984-pre-1978-history",
        "us:oasdi-dual-entitlement-pre-1978-history",
        "us:oasdi-reduction-exact-fractions",
        "us:oasdi-disability-family-maximum-rounding",
        "us:oasdi-ret-temporary-partial-deduction",
        "us:oasdi-nh-charge-age-reduction-interaction",
    },
    "R2": {
        "us:oasdi-ret-negative-nese-proration",
        "us:oasdi-ret-grace-simultaneous-rib-dib",
        "us:oasdi-ret-own-work-age-exemptions",
        "us:oasdi-ret-deemed-entitlement-basis",
        "us:oasdi-ret-other-deductee-scope",
    },
    "R3": {
        "us:oasdi-survivor-fra-1911-births",
        "us:oasdi-arf-widow-child-in-care-credits",
        "us:oasdi-arf-spouse-reentitlement-credits",
    },
}
#: Readings that other rounds log in the G, R2, R3 and grace modules
#: (microcosm-dynamics#563). A new marker there needs its id here or above.
OTHER_ROUNDS = {
    "us:oasdi-finality-protected-rates-before-coverage",
    "us:oasdi-sole-full-deduction-zero-dual-composition",
}
#: Exempt, by path inside the package: the insured-status modules that
#: #562 adds. They keep their own register of readings, with a test of its
#: own, and this scan does not read them.
OWN_REGISTERS = {"insured_status.py", "_insured_status_qc.py"}
#: Scanned suffixes, compared in lower case.
SOURCES = {".py", ".pyi", ".yaml", ".yml"}
ID = r"us:oasdi-[a-z0-9]+(?:-[a-z0-9]+)*"
#: The one marker form, with exactly this spelling, case and spacing. Its
#: id ends at a colon, whitespace or the end of the file.
MARKER = re.compile(rf"# Source conflict ({ID})(?=:|\s|$)")
#: What a scanned file may hold only inside a marker, in any case.
STRAYS = (
    # "source" or "sources", with no letter just before it, then
    # "conflict", with nothing but whitespace, "#", "-" or "_" between.
    re.compile(r"(?<![a-z])sources?[\s#_-]*conflict", re.IGNORECASE),
    # "us", with no letter or digit just before it, then "oasdi", with at
    # most three colons, whitespace characters, hyphens or underscores
    # between.
    re.compile(r"(?<![a-z0-9])us[\s:_-]{0,3}oasdi", re.IGNORECASE),
    # "oasdi", with no letter or digit just before it, then at least two
    # words of letters and digits, each after a hyphen: an id without
    # its "us:".
    re.compile(r"(?<![a-z0-9])oasdi(?:-[a-z0-9]+){2}", re.IGNORECASE),
)
#: A whole id in a note: no letter, digit, underscore or hyphen on either
#: side.
DOCUMENTED = re.compile(rf"(?<![A-Za-z0-9_-]){ID}(?![A-Za-z0-9_-])")

#: Leading whitespace, ">" characters, and list markers with a space or
#: tab and more text after them.
CONTAINERS = re.compile(
    r"(?:[ \t]*(?:>|(?:[-+*]|\d{1,9}[.)])(?=[ \t]+\S)))*[ \t]*"
)
#: One to six "#" and then a space, a tab or the end of the line.
ATX = re.compile(r"#{1,6}(?:[ \t](.*))?")
#: A line of only "=" or only "-" characters, with spaces or tabs after.
UNDERLINE = re.compile(r"(?:=+|-+)[ \t]*")
#: The text after each h1 to h6 opening tag, up to its closing tag or the
#: end of the note. The lookahead lets an unclosed tag's text overlap the
#: next heading's.
HTML_HEADING = re.compile(
    r"<h([1-6])\b[^>]*>(?=(.*?)(?:</h\1\s*>|\Z))",
    re.IGNORECASE | re.DOTALL,
)
#: What a heading loses before the comparison: HTML tags, "*", "_",
#: backticks, backslashes, square brackets, soft hyphens and the
#: zero-width characters U+200B to U+200D, U+2060 and U+FEFF.
MARKUP = re.compile(r"<[^>]+>|[*_`\\\[\]\u00ad\u200b-\u200d\u2060\ufeff]")
#: "Needs Max's judgment" after any characters other than the letters A
#: to Z, in any case, with any whitespace between the words, a straight
#: apostrophe or U+2018, U+2019 or U+02BC, and "judgment" or "judgement".
JUDGMENT = re.compile(
    r"[^A-Za-z]*needs\s+max['\u2018\u2019\u02bc]s\s+judge?ment",
    re.IGNORECASE,
)


def _module_markers():
    """Marker ids by file, across the files the scan reads.

    With its markers removed, a scanned file must hold nothing ``STRAYS``
    matches, so a wrapped, reworded, recased or misspelled marker fails
    while its id, its id's words or its "source conflict" survive.
    """
    found = {}
    for path in sorted(MODULES.rglob("*")):
        name = path.relative_to(MODULES).as_posix()
        if (
            name in OWN_REGISTERS
            or path.suffix.lower() not in SOURCES
            or not path.is_file()
        ):
            continue
        text = path.read_text(encoding="utf-8")
        rest = MARKER.sub("", text)
        strays = [m.group() for p in STRAYS for m in p.finditer(rest)]
        assert not strays, (name, strays)
        for found_id in MARKER.findall(text):
            found.setdefault(found_id, set()).add(name)
    return found


def _headings(text):
    """Heading lines in a note, code blocks included.

    With ``CONTAINERS`` removed from each line, these are heading lines:
    the text after the "#" run of a line ``ATX`` matches; a line that
    starts with "**" or "__"; each ``HTML_HEADING``; and, for each line
    ``UNDERLINE`` matches, the text from each line of the non-blank run
    directly above it down to that line.
    """
    lines = [
        line[CONTAINERS.match(line).end() :] for line in text.splitlines()
    ]
    found = [m.group(2) for m in HTML_HEADING.finditer("\n".join(lines))]
    run = []
    for line in lines:
        if not line:
            run = []
            continue
        if UNDERLINE.fullmatch(line):
            found += [" ".join(run[i:]) for i in range(len(run))]
        elif atx := ATX.fullmatch(line):
            found.append(atx.group(1) or "")
        elif line.startswith(("**", "__")):
            found.append(line)
        run.append(line)
    return found


def _plain(heading):
    """A heading's text with HTML entities decoded and ``MARKUP`` gone."""
    return MARKUP.sub("", html.unescape(heading))


def _open_judgment_headings(text):
    return [h for h in _headings(text) if JUDGMENT.match(_plain(h))]


def test_markers_and_logged_readings_match_in_both_directions():
    markers = _module_markers()
    logged = set().union(*READINGS.values()) | OTHER_ROUNDS
    assert set(markers) == logged
    for name in logged:
        assert markers[name] <= {
            "gross_benefits.py",
            "ret_ledger.py",
            "ret_grace.py",
            "arf.py",
        }, name


def test_every_marker_names_a_reading_documented_in_a_design_note():
    # Whole ids, so a truncated or misspelled marker cannot match a prefix.
    documented = set()
    for path in (ROOT / "docs" / "design").glob("track_b_*.md"):
        documented.update(DOCUMENTED.findall(path.read_text(encoding="utf-8")))
    for name in _module_markers():
        assert name in documented, name


@pytest.mark.parametrize("note", sorted(NOTES))
def test_each_note_names_its_readings_and_has_no_open_judgment_heading(note):
    text = NOTES[note].read_text(encoding="utf-8")
    assert not _open_judgment_headings(text), note
    named = set(DOCUMENTED.findall(text))
    for name in READINGS[note]:
        assert name in named, (note, name)


STATUTE_QUOTES = (
    # 402(h)(1)(D): the parent's own-RIB test depends on the entitled set.
    "if the amount of the parent 's insurance benefit for such month is "
    "determinable under paragraph (2)(A) (or 75 percent of such primary "
    "insurance amount in any other case)",
    "For any month for which more than one parent is entitled to parent 's "
    "insurance benefits",
    # 402(k)(4): an elected RIB month is entitlement to RIB alone.
    "if such individual so elects, he shall instead be entitled to only the "
    "smaller of such benefits for such month.",
    # 402(s)(2)-(3): marriage and the 203(f)(1)(C) exemption need disability.
    "shall not apply in the case of any child unless such child, at the "
    "time of the marriage referred to therein, was under a disability",
    "subsection (f)(1)(C) of section 403 of this title",
    "unless in such month or the third month prior thereto such child was "
    "under a disability",
    # 402(d)(1)(D), (d)(5): marriage ends a child's benefit, with exceptions.
    "(D) the month in which such child dies, or marries,",
    "but subject to subsection (s), not be terminated by reason of such "
    "marriage.",
    # 402(e)(1): a widow(er) entitled before 60 ends at the termination month.
    "if she became entitled to such benefits before she attained age 60",
    "the termination month for any individual shall be the third month "
    "following the month in which her disability ceases;",
)


@pytest.mark.parametrize("quote", STATUTE_QUOTES)
def test_new_statutory_excerpts_are_quoted_verbatim(quote):
    assert quote in " ".join(source_text("lii_usc_402_415").split())
