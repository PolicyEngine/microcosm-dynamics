"""Track B readings pass of October 23, 2026: markers, notes and new quotes.

Verification class: statutory conformance and documentation integrity on
captured sources only. No population, behavioral or forecast claim.
Markers: the scan reads, as UTF-8, every file in the Track B package,
subpackages included, whose suffix in any case is in ``SOURCES``, except
the ``OWN_REGISTERS`` at the top of the package. With its markers
removed, a scanned file must hold nothing ``STRAYS`` matches. The
``MARKER`` ids are exactly ``READINGS`` plus ``OTHER_ROUNDS``, each in the
G, R2, R3 or grace module, and each is ``DOCUMENTED`` in a Track B design
note. Notes: G, R2 and R3 name their ``READINGS`` the same way, and none
has an opening, as ``_openings`` reads them, whose ``_letters`` start
with ``JUDGMENT``. Quotes: each new statutory excerpt appears in its
capture as ``source_text`` normalizes it, with each run of whitespace in
the capture read as one space. Reads: those checks list and open only the
Track B package, the notes named ``track_b_*.md`` and the statute captures,
and a guard test patches ``Path`` to fail on anything else.
"""

import html
import re
import unicodedata
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
#: "us:oasdi-" and then one or more words of the letters a to z and the
#: digits 0 to 9, joined by single hyphens.
ID = r"us:oasdi-[a-z0-9]+(?:-[a-z0-9]+)*"
#: The one marker form, with exactly this spelling, case and spacing. Its
#: id ends at a colon, whitespace or the end of the file.
MARKER = re.compile(rf"# Source conflict ({ID})(?=:|\s|$)")
#: What a scanned file may hold only inside a marker, in any case. A
#: letter here is one of A to Z, and a digit one of 0 to 9.
STRAYS = (
    # "source" or "sources", with no letter just before it, then
    # "conflict", with nothing but whitespace, "#", "-" or "_" between.
    re.compile(r"(?<!(?-i:[A-Za-z]))sources?[\s#_-]*conflict", re.IGNORECASE),
    # "us", with no letter or digit just before it, then "oasdi", with at
    # most three colons, whitespace characters, hyphens or underscores
    # between.
    re.compile(r"(?<!(?-i:[A-Za-z0-9]))us[\s:_-]{0,3}oasdi", re.IGNORECASE),
    # "oasdi", with no letter or digit just before it, then at least two
    # words of letters and digits, each after a hyphen: an id without
    # its "us:".
    re.compile(
        r"(?<!(?-i:[A-Za-z0-9]))oasdi(?:-(?-i:[A-Za-z0-9])+){2}",
        re.IGNORECASE,
    ),
)
#: A whole id in a note: no letter A to Z, digit 0 to 9, underscore or
#: hyphen on either side.
DOCUMENTED = re.compile(rf"(?<![A-Za-z0-9_-]){ID}(?![A-Za-z0-9_-])")

#: Leading whitespace and then a letter A to Z.
LETTER = re.compile(r"(\s*)[A-Za-z]")
#: The text after each h1 to h6 opening tag, up to its closing tag or the
#: end of the note: once with the tag ending at its first ">", and once
#: with it ending at its first ">" outside quotes. The lookahead lets an
#: unclosed tag's text overlap the next heading's.
HTML_HEADINGS = tuple(
    re.compile(
        rf"<h([1-6])\b{tag}>(?=(.*?)(?:</h\1\s*>|\Z))",
        re.IGNORECASE | re.DOTALL,
    )
    for tag in (r"[^>]*", r"""(?:[^>"']|"[^"]*"|'[^']*')*""")
)
#: What the first of the two ``_letters`` readings removes: HTML tags,
#: each up to its first ">", and Markdown link targets, a "(...)" or
#: "[...]" right after a "]".
HIDDEN = re.compile(r"<[^>]+>|\](?:\([^)]*\)|\[[^\]]*\])")
#: How the letters of an open judgment item start: "Needs Max's judgment",
#: or "judgement", as ``_letters`` reads it.
JUDGMENT = ("needsmaxsjudgment", "needsmaxsjudgement")


def _module_markers():
    """Marker ids by file, across the files the scan reads.

    With its markers removed, a scanned file must hold nothing ``STRAYS``
    matches. So a wrapped, reworded, recased or misspelled marker trips
    this check while some of its text still matches ``STRAYS``.
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


def _continues(above, line):
    """Whether a line continues the one above it instead of opening.

    Both must start with a letter A to Z after the same leading
    whitespace (``LETTER``), and neither may hold ">" or "|".
    """
    first, second = LETTER.match(above), LETTER.match(line)
    return bool(
        first
        and second
        and first.group(1) == second.group(1)
        and not {">", "|"} & set(above + line)
    )


def _openings(text):
    """What the lines of a note open, code blocks included.

    Every non-blank line opens unless it ``_continues`` the line above
    it, and what it opens runs to the end of its run of non-blank lines.
    The text after each ``HTML_HEADINGS`` opening tag counts too.
    """
    found = [m.group(2) for p in HTML_HEADINGS for m in p.finditer(text)]
    run = []
    for line in [*text.splitlines(), ""]:
        if line.strip():
            run.append(line)
            continue
        found += [
            " ".join(run[k:])
            for k in range(len(run))
            if not (k and _continues(run[k - 1], run[k]))
        ]
        run = []
    return found


def _letters(text):
    """The letters of a text, read two ways.

    It decodes HTML entities, then reads the text once with ``HIDDEN``
    removed and once as written. Each reading applies Unicode
    compatibility decomposition (NFKD) and keeps only the letters A to Z,
    in lower case.
    """
    text = html.unescape(text)
    return [
        "".join(re.findall("[a-z]", unicodedata.normalize("NFKD", t).lower()))
        for t in (HIDDEN.sub("", text), text)
    ]


def _open_judgment_items(text):
    return [
        opening
        for opening in _openings(text)
        if any(read.startswith(JUDGMENT) for read in _letters(opening))
    ]


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
def test_each_note_names_its_readings_and_opens_no_judgment_item(note):
    text = NOTES[note].read_text(encoding="utf-8")
    assert not _open_judgment_items(text), note
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


def test_the_checks_list_and_open_only_track_b_paths(monkeypatch):
    # So that a blind role can run this module without reaching a restricted
    # file, these checks may list only the package and the notes named
    # track_b_*.md, and open only those files and the statute captures. The
    # guard checks each Path listing and open before it runs, and it spells
    # out its paths so that a change to the constants above fails it.
    package = (ROOT / "src/populace_dynamics/track_b").resolve()
    design = (ROOT / "docs/design").resolve()
    captures = (ROOT / "tests/data/track_b/gross_benefit_sources").resolve()
    path_open, glob, rglob = Path.open, Path.glob, Path.rglob
    walk = getattr(Path, "walk", None)  # New in Python 3.12.
    opened = []

    def checked_open(path, *args, **kwargs):
        resolved = path.resolve()
        assert (
            resolved.is_relative_to(package)
            or resolved.is_relative_to(captures)
            or (resolved.parent == design and resolved.match("track_b_*.md"))
        ), resolved
        opened.append(resolved)
        return path_open(path, *args, **kwargs)

    def checked(listing, allowed):
        def checked_listing(path, pattern, *args, **kwargs):
            assert (path.resolve(), str(pattern)) in allowed, (path, pattern)
            return listing(path, pattern, *args, **kwargs)

        return checked_listing

    def checked_walk(path, *args, **kwargs):
        # On Python 3.12, rglob walks the folder it lists.
        assert path.resolve() == package, path
        return walk(path, *args, **kwargs)

    def unchecked(path, *args, **kwargs):
        raise AssertionError(f"listing of {path}")

    monkeypatch.setattr(Path, "open", checked_open)
    # From Python 3.13, rglob calls glob with "**/" before its pattern.
    monkeypatch.setattr(
        Path,
        "glob",
        checked(glob, {(design, "track_b_*.md"), (package, "**/*")}),
    )
    monkeypatch.setattr(Path, "rglob", checked(rglob, {(package, "*")}))
    monkeypatch.setattr(Path, "iterdir", unchecked)
    monkeypatch.setattr(Path, "walk", checked_walk, raising=False)
    for reach in (
        lambda: (ROOT / "pyproject.toml").open(),
        lambda: (design / "other.md").open(),
        lambda: design.glob("*.md"),
        lambda: design.rglob("track_b_*.md"),
        lambda: package.parent.rglob("*"),
        lambda: package.iterdir(),
        lambda: design.walk(),
        lambda: package.parent.walk(),
    ):
        with pytest.raises(AssertionError):
            reach()

    def reads(check, *arguments):
        opened.clear()
        check(*arguments)
        return set(opened)

    notes = {path.resolve() for path in NOTES.values()}
    assert package / "gross_benefits.py" in reads(
        test_markers_and_logged_readings_match_in_both_directions
    )
    assert notes <= reads(
        test_every_marker_names_a_reading_documented_in_a_design_note
    )
    assert notes == set().union(
        *(
            reads(
                test_each_note_names_its_readings_and_opens_no_judgment_item,
                note,
            )
            for note in NOTES
        )
    )
    source_text.cache_clear()
    assert {captures} == {
        path.parent
        for path in reads(
            test_new_statutory_excerpts_are_quoted_verbatim,
            STATUTE_QUOTES[0],
        )
    }
