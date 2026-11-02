"""Track B readings pass of October 23, 2026: markers, notes and new quotes.

Verification class: statutory conformance and documentation integrity on
captured sources only. No population, behavioral or forecast claim.
Outside the exempt insured-status modules, every mention of a source
conflict, in any spelling, in a Python or YAML file of the Track B package
is a ``# Source conflict <id>`` marker. The marker ids are exactly this
pass's readings plus those other rounds register here, each in the G, R2,
R3 or grace module, and each id appears whole in a Track B design note.
Each note names its readings as whole ids and keeps no open "Needs Max's
judgment" heading.
"""

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
#: Exempt: the insured-status modules (#562). The source-conflict rulings
#: log their readings, but no Track B note documents all of them yet.
OWN_REGISTERS = {"insured_status.py", "_insured_status_qc.py"}
ID = r"us:oasdi-[a-z0-9]+(?:-[a-z0-9]+)*"
#: A marker's id ends at a colon, whitespace or the end of the file.
MARKER = re.compile(rf"# Source conflict ({ID})(?=:|\s|$)")
#: A whole id in a note: no id character or hyphen follows it.
DOCUMENTED = re.compile(rf"{ID}(?![A-Za-z0-9_-])")
#: Any spelling: "source conflict", "Source-conflict", "Sources conflict".
MENTION = re.compile(r"sources?[\W_]*conflict", re.IGNORECASE)
#: Files that can carry a marker, subpackages included.
SOURCES = {".py", ".yaml", ".yml"}


def _module_markers():
    """Marker ids by file, leaving out ids only exempt modules carry.

    Outside the exempt modules every mention of a source conflict must
    parse as a marker, so a wrapped, mistyped or reworded one fails.
    """
    found = {}
    for path in sorted(MODULES.rglob("*")):
        if path.suffix not in SOURCES or not path.is_file():
            continue
        name = path.relative_to(MODULES).as_posix()
        text = path.read_text()
        ids = MARKER.findall(text)
        if name not in OWN_REGISTERS:
            assert len(MENTION.findall(text)) == len(ids), name
        for found_id in ids:
            found.setdefault(found_id, set()).add(name)
    return {
        name: files
        for name, files in found.items()
        if not files <= OWN_REGISTERS
    }


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
        documented.update(DOCUMENTED.findall(path.read_text()))
    for name in _module_markers():
        assert name in documented, name


@pytest.mark.parametrize("note", sorted(NOTES))
def test_each_note_names_its_readings_and_has_no_open_judgment_heading(note):
    text = NOTES[note].read_text()
    assert not re.search(r"^#+ Needs Max's judgment", text, re.MULTILINE)
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
