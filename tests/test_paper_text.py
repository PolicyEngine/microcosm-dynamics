"""Pin structural properties of the working paper's text.

* Every citation key the paper uses resolves to an entry in
  ``docs/references.bib``, so a render never prints a bare ``?@key``.
* The plain-language summary leads with "pre-registered test" and
  introduces the word "gate" exactly once (Max's terminology ruling
  after the NASI meeting of 2026-10-01). The technical body keeps
  "gate", and the body's first use defines it in plain words.

These tests read only committed files and run everywhere.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper" / "paper.qmd"
BIB = ROOT / "docs" / "references.bib"

# Quarto cross-reference prefixes, which share the @ syntax with citations.
CROSSREF_PREFIXES = ("sec-", "tbl-", "fig-", "eq-", "lst-")
GATE_WORD = re.compile(r"\bgates?\b", re.IGNORECASE)


def _body() -> str:
    text = PAPER.read_text(encoding="utf-8")
    # Drop the YAML front matter, which holds the author's e-mail address.
    return text.split("\n---\n", 1)[1]


def _sections() -> dict[str, str]:
    """Map each top-level section's anchor to its text."""
    sections: dict[str, str] = {}
    for chunk in re.split(r"\n(?=# )", "\n" + _body()):
        anchor = re.search(r"\{[^}]*#(sec-[\w-]+)[^}]*\}", chunk)
        if anchor:
            sections[anchor.group(1)] = chunk
    return sections


def test_every_citation_key_resolves():
    bib_keys = set(
        re.findall(r"^@\w+\{([^,\s]+),", BIB.read_text(encoding="utf-8"), re.M)
    )
    cited = {
        key.rstrip(".")
        for key in re.findall(r"(?<![\w@])@([A-Za-z][\w:.-]*\w)", _body())
        if not key.startswith(CROSSREF_PREFIXES)
    }
    assert cited, "the paper cites nothing; the citation pattern broke"
    missing = sorted(cited - bib_keys)
    assert not missing, f"citation keys missing from references.bib: {missing}"


def test_plain_language_summary_introduces_gate_once():
    sections = _sections()
    assert "sec-plain" in sections, "the plain-language summary is missing"
    summary = sections["sec-plain"]
    assert len(GATE_WORD.findall(summary)) == 1, GATE_WORD.findall(summary)
    first_test = summary.lower().find("pre-registered test")
    first_gate = GATE_WORD.search(summary).start()
    assert 0 <= first_test < first_gate


def test_summary_precedes_the_introduction():
    anchors = list(_sections())
    assert anchors.index("sec-plain") < anchors.index("sec-intro")


def test_body_defines_gate_at_first_use():
    intro = _sections()["sec-intro"]
    first = GATE_WORD.search(intro)
    assert first, "the introduction no longer mentions gates"
    sentence_end = intro.find(".", first.end())
    sentence = intro[intro.rfind(".", 0, first.start()) + 1 : sentence_end]
    assert "register publicly" in sentence, sentence
