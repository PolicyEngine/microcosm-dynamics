"""Pin milestone 1b's PSID research to the documents it cites.

Documentary checks only: no survey records, counts or outcomes. Paths that
begin ``PSID/`` resolve against the staged PSID root that
``tests/data/track_u2/psid_docs/manifest.json`` names: the
``POPULACE_DYNAMICS_PSID_DIR`` environment variable, else
``~/PolicyEngine/psid-data``. A check that needs a file under that root, or
Poppler's ``pdftotext`` for a PDF text layer, skips with an explicit reason
where it is unavailable (as in CI, which stages no PSID files).
"""

import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import unicodedata
from functools import cache
from pathlib import Path

import pytest

from populace_dynamics.data import u2_source_registry as registry

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "tests/data/track_u2/psid_docs"
MANIFEST = json.loads((DOCS / "manifest.json").read_text(encoding="utf-8"))
RESEARCH = ROOT / MANIFEST["research_record"]
SPEC = ROOT / "docs/design/boomers2004_1946_55_comparison.md"
QUOTES = MANIFEST["research_quotes"]
SPEC_QUOTES = MANIFEST["spec_quotes"]
REGISTERED = [("research", q) for q in QUOTES] + [
    ("spec", q) for q in SPEC_QUOTES
]
ANCHORS = MANIFEST["page_anchors"]
REGISTRY_QUOTES = MANIFEST["registry_quotes"]
REGISTRY_ANCHORS = MANIFEST["registry_anchors"]
# Registry text whose every page citation is checked, and whose entry must
# cite every page checked.
CHECKED_FIELDS = [
    ("weights", "2017.cross_section_weight", "construction"),
    ("weights", "2017.cross_section_weight", "part_b_finding"),
]
# A page citation, with any list of further pages: "pp. 89, 166",
# "pp. 8 and 13-15". A list element must end at punctuation or "and", so
# "p. 978, 2015 relationship" is one page.
CITATION = re.compile(
    r"\b(?:PDF )?pp?\. (\d+(?:[\N{EN DASH}-]\d+)?"
    r"(?:(?:,| and|, and) \d+(?:[\N{EN DASH}-]\d+)?(?=[,;.):]| and |$))*)"
)
# How the records name each quoted document, beyond its file stem.
DOCUMENT_NAMES = {
    "FAQ_20260813": ["FAQ"],
    "cross_sec_weights_17": ["construction report", "February 2019"],
    "cross_sec_weights_19": ["2019 cross-sectional report", "April 2021"],
    "cross_sec_weights_21": ["2021 cross-sectional report", "September 2023"],
    "cross_sec_weights_23": ["2023 cross-sectional report", "June 2026"],
    "long_weight_19": ["2019 longitudinal", "April 2021"],
    "long_weight_21": ["2021 longitudinal"],
    "DataRelease-May2019": ["May 2019 release notes", "May 2019 notes"],
    "FAM2015ER_codebook": ["2015 family codebook"],
    "FAM2017ER_codebook": ["2017 codebook"],
    "FAM2021ER_codebook": ["family codebooks"],
    "FAM2023ER_codebook": ["family codebooks"],
    "fam2019er_codebook": ["2019 family codebook", "family codebooks"],
    "fam2015_QxQs": ["QxQs"],
    "dust13_hh_codebook": ["DUST 2013"],
}
ELLIPSIS = re.compile(r"\s*(?:\.\.\.|\u2026)\s*")
OPENING = re.compile(r"(?:^|(?<=[\s(\[\u2014:]))'(?=\S)")
CLOSING = re.compile(r"(?<=\S)'(?=[\s.,;:)\]]|$)")


def psid_root():
    root = MANIFEST["psid_root"]
    value = os.environ.get(root["environment_variable"]) or root["default"]
    return Path(value).expanduser()


def resolve(file):
    if not file.startswith("PSID/"):
        return ROOT / file
    path = psid_root() / file.removeprefix("PSID/")
    if not path.is_file():
        pytest.skip(
            f"{file} is not staged under the PSID root {psid_root()} "
            "(set POPULACE_DYNAMICS_PSID_DIR to check it)"
        )
    return path


def normalize(text):
    """Fold whitespace, quote marks, dashes and ligatures; keep case.

    A hyphen that ends a line joins the next word, as a PDF text layer
    splits 'cross-sectional' into 'cross-' and 'sectional'.
    """
    text = unicodedata.normalize("NFKC", text).replace("\u00ad", "")
    text = re.sub(r"(?<=\w)-[ \t]*\n\s*(?=\w)", "-", text)
    text = re.sub(r"[\u2018\u2019\u201a\u201b\u2032`\u00b4]", "'", text)
    text = re.sub(r"[\u201c\u201d\u201e\u201f\u2033]", '"', text)
    text = re.sub(r"[\u2010-\u2015\u2212]", "-", text)
    return re.sub(r"\s+", " ", text).strip()


def fragments(text):
    return [normalize(part) for part in ELLIPSIS.split(text) if part.strip()]


@cache
def pins():
    """SHA-256 of every archived or pinned file: manifest, then registries."""
    found = {s["file"]: s["sha256"] for s in MANIFEST["sources"]}
    found |= {p["file"]: p["sha256"] for p in MANIFEST["pinned_elsewhere"]}
    for name in registry.REGISTRY_NAMES:
        for source in registry.load_registry(name)["sources"]:
            pinned = found.setdefault(source["file"], source["sha256"])
            assert pinned == source["sha256"], source["file"]
    return found


@cache
def pinned_path(file):
    """Resolve a quoted file and confirm its bytes match its pin."""
    path = resolve(file)
    if file.startswith("src/"):
        return path  # repository code; u1_identity.json pins its bytes
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == pins()[file], file
    return path


@cache
def pdf_pages(path):
    if shutil.which("pdftotext") is None:
        pytest.skip("Poppler pdftotext is unavailable; PDF text not checked")
    text = subprocess.run(
        ["pdftotext", "-layout", "-enc", "UTF-8", str(path), "-"],
        capture_output=True,
        check=True,
    ).stdout.decode("utf-8")
    return tuple(normalize(page) for page in text.split("\f"))


@cache
def text_lines(path):
    # Lines are LF-terminated, as grep -n counts them; HTML tags dropped.
    lines = path.read_bytes().decode("utf-8").split("\n")
    return tuple(
        normalize(html.unescape(re.sub(r"<[^>]+>", " ", line)))
        for line in lines
    )


def quoted_spans(markdown):
    """Single-quoted spans in the research record, outside code spans.

    Nested quotes split a quotation into pieces; each piece must still lie
    inside a registered quote. Staff questions are the builder's own words.
    """
    spans = []
    for paragraph in re.sub(r"`[^`]*`", " ", markdown).split("\n"):
        if paragraph.startswith("**Question for PSID staff"):
            continue
        start = 0
        while opening := OPENING.search(paragraph, start):
            closing = CLOSING.search(paragraph, opening.end())
            if closing is None:
                break
            spans.append(paragraph[opening.end() : closing.start()])
            start = closing.end()
    return spans


def blocks(markdown):
    """Paragraphs and list items, each nested item on its own."""
    found, current = [], []
    for line in markdown.split("\n"):
        starts = re.match(r"\s*(?:\d+\.|-|>)\s|\*\*", line)
        if not line.strip() or starts:
            if current:
                found.append("\n".join(current))
            current = [line] if line.strip() else []
        else:
            current.append(line)
    if current:
        found.append("\n".join(current))
    return found


def label(quote):
    where = quote.get("page", quote.get("line"))
    return f"{Path(quote['file']).name}:{where}:{quote['text'][:24]}"


def test_every_research_quote_is_registered():
    markdown = RESEARCH.read_text(encoding="utf-8")
    record = normalize(markdown)
    registered = [normalize(quote["text"]) for quote in QUOTES]
    missing = [text for text in registered if text not in record]
    assert not missing, missing
    spans = quoted_spans(markdown)
    assert len(spans) >= 75
    unregistered = [
        span
        for span in spans
        if not any(normalize(span) in text for text in registered)
    ]
    assert not unregistered, unregistered


def test_every_quote_sits_with_its_citation():
    """The paragraph or list item holding a quote cites its page or line."""
    documents = {
        "research": blocks(RESEARCH.read_text(encoding="utf-8")),
        "spec": blocks(SPEC.read_text(encoding="utf-8")),
    }
    unanchored = []
    for record, quote in REGISTERED:
        if record == "research":
            assert quote.get("cited_as"), label(quote)
        if "cited_as" not in quote:
            continue
        # A page or line number; the spec may cite an FAQ answer by number.
        where = quote.get("page", quote.get("line"))
        anchors = [rf"\b{where}\b"]
        if "question" in quote:
            anchors.append(rf"question {quote['question']}\b")
        assert any(
            re.search(anchor, quote["cited_as"]) for anchor in anchors
        ), label(quote)
        text = normalize(quote["text"])
        if not any(
            quote["cited_as"] in block and text in normalize(block)
            for block in documents[record]
        ):
            unanchored.append((record, label(quote), quote["cited_as"]))
    assert not unanchored, unanchored


@pytest.mark.parametrize(
    "record,quote",
    REGISTERED,
    ids=[f"{record}:{label(quote)}" for record, quote in REGISTERED],
)
def test_quote_appears_where_cited(record, quote):
    path = pinned_path(quote["file"])
    if "line" in quote:
        text = text_lines(path)[quote["line"] - 1]
    else:
        text = pdf_pages(path)[quote["page"] - 1]
    assert_in_order(quote, text)


def assert_in_order(quote, text):
    """Each fragment between ellipses is on the page, in the quote's order.

    A fragment without a letter or digit (the bracket after an ellipsis)
    is skipped. Compare to a bool first so a failure never prints the page,
    whose codebook columns can carry published frequencies.
    """
    position = 0
    for fragment in fragments(quote["text"]):
        if not re.search(r"\w", fragment):
            continue
        at = text.find(fragment, position)
        found = at >= 0
        assert found, f"{label(quote)}: {fragment!r} not on the page in order"
        position = at + len(fragment)


@pytest.mark.parametrize(
    "pinned", MANIFEST["pinned_elsewhere"], ids=lambda p: p["file"]
)
def test_pinned_document_bytes(pinned):
    raw = resolve(pinned["file"]).read_bytes()
    assert raw.startswith(b"%PDF")
    assert len(raw) == pinned["bytes"]
    assert hashlib.sha256(raw).hexdigest() == pinned["sha256"]


@pytest.mark.parametrize(
    "source",
    [s for s in MANIFEST["sources"] if "local_capture" in s],
    ids=lambda s: Path(s["file"]).name,
)
def test_local_capture_claims(source):
    capture = source["local_capture"]
    archived = (ROOT / source["file"]).read_bytes()
    local = resolve(capture["path"])
    assert (local.read_bytes() == archived) is capture["identical"]
    if capture.get("browser_digest_listed"):
        digests = local.with_name("browser_digests.txt").read_text()
        entry = f"{source['sha256']} {source['bytes']} {local.name}"
        assert entry in digests.splitlines()


def test_quoted_documents_are_pinned():
    for _, quote in REGISTERED:
        assert quote["file"] in pins() or quote["file"].startswith(
            "src/"
        ), quote["file"]
    code = {q["file"] for _, q in REGISTERED if q["file"].startswith("src/")}
    identity = json.loads(
        (registry.REGISTRY_DIRECTORY / "u1_identity.json").read_text()
    )["sha256"]
    assert code and code <= set(identity)


@pytest.mark.parametrize(
    "anchor",
    ANCHORS,
    ids=[f"{a['record']}:{a['cited_as'][:32]}" for a in ANCHORS],
)
def test_page_anchor_is_on_the_cited_page(anchor):
    """A paraphrased page citation: its phrase is on each page it names."""
    blocks_of = {
        "research": blocks(RESEARCH.read_text(encoding="utf-8")),
        "spec": blocks(SPEC.read_text(encoding="utf-8")),
    }
    assert any(anchor["cited_as"] in b for b in blocks_of[anchor["record"]])
    if anchor.get("unit") == "line":
        units = text_lines(pinned_path(anchor["file"]))
    else:
        units = pdf_pages(pinned_path(anchor["file"]))
    for where, phrase in anchor["checks"]:
        found = normalize(phrase) in units[where - 1]
        assert found, f"{anchor['file']} {where}: {phrase!r}"


def page_citations(block):
    """(citation, element, pages to check) for each page or range cited."""
    for found in CITATION.finditer(block):
        for element in re.split(r",? and |, ", found.group(1)):
            ends = [int(n) for n in re.split(r"[\N{EN DASH}-]", element)]
            yield found.group(0), element, {ends[0], ends[-1]}


def test_every_page_citation_is_checked():
    """Each page citation in the research record and in section 16a, every
    page of a list and both ends of a range, is checked by a quote or page
    anchor that cites it in the same paragraph or list item."""
    spec = SPEC.read_text(encoding="utf-8")
    records = {
        "research": RESEARCH.read_text(encoding="utf-8"),
        "spec": spec[spec.index("## 16a. ") : spec.index("## 17. ")],
    }
    checked = {
        "research": [
            (q["cited_as"], {q["page"]}) for q in QUOTES if "page" in q
        ],
        "spec": [
            (q["cited_as"], {q["page"]})
            for q in SPEC_QUOTES
            if "page" in q and "cited_as" in q
        ],
    }
    for anchor in ANCHORS:
        if anchor.get("unit") != "line":
            checked[anchor["record"]].append(
                (anchor["cited_as"], {page for page, _ in anchor["checks"]})
            )
    unchecked = []
    for record, text in records.items():
        for block in blocks(text):
            for citation, element, ends in page_citations(block):
                number = re.compile(rf"(?<!\d){re.escape(element)}(?!\d)")
                for end in sorted(ends):
                    if not any(
                        cited_as in block
                        and end in pages
                        and number.search(cited_as)
                        for cited_as, pages in checked[record]
                    ):
                        unchecked.append((record, citation, end, block[:40]))
    assert not unchecked, unchecked


def test_every_faq_question_cited_is_checked():
    """Each FAQ question the research record or section 16a cites is
    checked by a quote or line anchor from that question in the same
    paragraph or list item."""
    spec = SPEC.read_text(encoding="utf-8")
    records = {
        "research": RESEARCH.read_text(encoding="utf-8"),
        "spec": spec[spec.index("## 16a. ") : spec.index("## 17. ")],
    }
    checked = {"research": [], "spec": []}
    for record, quote in REGISTERED:
        if "question" in quote and "cited_as" in quote:
            checked[record].append((quote["cited_as"], quote["question"]))
    for anchor in ANCHORS:
        if "question" in anchor:
            checked[anchor["record"]].append(
                (anchor["cited_as"], anchor["question"])
            )
    unchecked = []
    for record, text in records.items():
        for block in blocks(text):
            for found in re.finditer(r"\bquestions? (\d+)\b", block):
                number = int(found.group(1))
                if not any(
                    cited_as in block and question == number
                    for cited_as, question in checked[record]
                ):
                    unchecked.append((record, found.group(0), block[:40]))
    assert not unchecked, unchecked


def contexts(markdown):
    """Each block with the list item it is nested in, if any."""
    parent = ""
    for block in blocks(markdown):
        if re.match(r"\S", block):
            parent = block
            yield block, block, block
        else:
            yield block, f"{parent}\n{block}", parent


def document_names(file):
    stem = Path(file).stem
    names = [stem, stem.removesuffix("_codebook")]
    return names + DOCUMENT_NAMES.get(stem, [])


def test_quotes_name_their_document():
    """The item holding a quote or anchor names its document, and every
    manifest document an item quoting sources names in code is one that
    the item or its nested items quote or anchor."""
    known = {
        Path(entry["file"]).stem
        for entry in MANIFEST["sources"] + MANIFEST["pinned_elsewhere"]
    }
    spec = SPEC.read_text(encoding="utf-8")
    records = {
        "research": list(contexts(RESEARCH.read_text(encoding="utf-8"))),
        "spec": list(
            contexts(spec[spec.index("## 16a. ") : spec.index("## 17. ")])
        ),
    }
    items = [
        (record, quote["cited_as"], quote["text"], quote["file"])
        for record, quote in REGISTERED
        if "cited_as" in quote
    ] + [(a["record"], a["cited_as"], None, a["file"]) for a in ANCHORS]
    unnamed, sourced = [], {}
    for record, cited_as, text, file in items:
        homes = [
            (context, parent)
            for block, context, parent in records[record]
            if cited_as in block
            and (text is None or normalize(text) in normalize(block))
        ]
        if not any(
            name in context
            for context, _ in homes
            for name in document_names(file)
        ):
            unnamed.append((record, Path(file).stem, cited_as))
        for context, parent in homes:
            sourced.setdefault((record, parent), set()).add(Path(file).stem)
            sourced.setdefault((record, context), set()).add(Path(file).stem)
    assert not unnamed, unnamed
    stray = []
    for (record, block), stems in sourced.items():
        coded = {
            Path(path).stem for path in re.findall(r"`([^`]+)`", block)
        } & known
        if coded - stems:
            stray.append((record, sorted(coded - stems), block[:40]))
    assert not stray, stray


@pytest.mark.parametrize(
    "file",
    sorted(
        {q["file"] for _, q in REGISTERED if "page" in q and q.get("cited_as")}
        | {q["file"] for q in REGISTRY_QUOTES if "page" in q}
        | {a["file"] for a in ANCHORS if a.get("unit") != "line"}
        | {a["file"] for a in REGISTRY_ANCHORS}
    ),
    ids=lambda f: Path(f).name,
)
def test_cited_pages_are_told_apart_from_their_neighbours(file):
    """On every cited page some checked phrase is absent from the pages on
    either side, so a citation one page off fails."""
    phrases = {}
    citing = [q for _, q in REGISTERED if q.get("cited_as")]
    for quote in citing + REGISTRY_QUOTES:
        if quote["file"] == file and "page" in quote:
            phrases.setdefault(quote["page"], []).extend(
                f for f in fragments(quote["text"]) if re.search(r"\w", f)
            )
    for anchor in ANCHORS + REGISTRY_ANCHORS:
        if anchor["file"] == file and anchor.get("unit") != "line":
            for page, phrase in anchor["checks"]:
                phrases.setdefault(page, []).append(normalize(phrase))
    pages = pdf_pages(pinned_path(file))
    blurred = []
    for page, group in sorted(phrases.items()):
        neighbours = [
            pages[n - 1] for n in (page - 1, page + 1) if 1 <= n <= len(pages)
        ]
        if not any(
            all(phrase not in other for other in neighbours)
            for phrase in group
        ):
            blurred.append(page)
    assert not blurred, blurred


def test_every_registry_quote_is_registered():
    """Quotes in the registries' milestone-1b text are registered."""
    fields = {}
    for name in registry.REGISTRY_NAMES:
        for entry in registry.load_registry(name)["entries"]:
            key = (name, entry["id"])
            if "part_b_finding" in entry:
                fields[(*key, "part_b_finding")] = entry["part_b_finding"]
                if "construction" in entry:
                    fields[(*key, "construction")] = entry["construction"]
            if entry.get("resolution", "").startswith(
                "Independent adjudication D (amendment 1)"
            ):
                fields[(*key, "resolution")] = entry["resolution"]
    registered = {}
    for quote in REGISTRY_QUOTES:
        key = (quote["registry"], quote["id"], quote["field"])
        assert normalize(quote["text"]) in normalize(fields[key]), key
        registered.setdefault(key, []).append(normalize(quote["text"]))
    unregistered = [
        (key, span)
        for key, text in fields.items()
        for span in quoted_spans(text)
        if not any(normalize(span) in r for r in registered.get(key, []))
    ]
    assert not unregistered, unregistered


@pytest.mark.parametrize(
    "quote",
    REGISTRY_QUOTES,
    ids=[f"{q['registry']}:{q['id']}:{label(q)}" for q in REGISTRY_QUOTES],
)
def test_registry_quote_appears_where_cited(quote):
    path = pinned_path(quote["file"])
    if "line" in quote:
        text = text_lines(path)[quote["line"] - 1]
    else:
        text = pdf_pages(path)[quote["page"] - 1]
    assert_in_order(quote, text)


def pages_matching(file, pattern):
    pages = pdf_pages(pinned_path(file))
    return [n for n, text in enumerate(pages, 1) if re.search(pattern, text)]


def test_rth_lookup_list_is_referenced_but_never_printed():
    """Research record section 1: the questionnaires refer to the RTH
    Lookup List on six pages. (The record's search covered all 494
    documentation PDFs; this pins the questionnaires, which hold every
    reference.)"""
    lookup = r"(?i)RTH\s*Look\s*-?\s*up"
    found = {
        year: pages_matching(
            f"PSID/documentation/capture1/q{year}.pdf", lookup
        )
        for year in (2009, 2011, 2013, 2015, 2017, 2019, 2021, 2023)
    }
    assert found == {
        2009: [109],
        2011: [105],
        2013: [5, 115],
        2015: [5, 131],
        2017: [],
        2019: [],
        2021: [],
        2023: [],
    }
    research = RESEARCH.read_text(encoding="utf-8")
    assert sum(map(len, found.values())) == 6
    assert "The only 'RTH Lookup' hits are the six references above" in (
        research
    )


def test_2015_instrument_never_names_201():
    """Research record section 1, item 11: in q2015 the token 201 is
    only p. 201's page number; q2017 names it on p. 5's code list and in
    routing conditions or question-text fills on 20 further pages."""
    q2015 = "PSID/documentation/capture1/q2015.pdf"
    q2017 = "PSID/documentation/capture1/q2017.pdf"
    token = r"(?<![\d,.])201(?![\d])"
    assert pages_matching(q2015, token) == [201]
    # q2015 never names 901 either, though code 90 was in use in 2015.
    assert pages_matching(q2015, r"(?<![\d,.])901(?![\d])") == []
    for file in (q2015, q2017):
        page_201 = pdf_pages(pinned_path(file))[200]
        assert page_201.startswith("201 ")
        assert len(re.findall(token, page_201)) == 1
    named = pages_matching(q2017, token)
    assert named[0] == 5 and 201 in named
    conditions = len([n for n in named if n not in (5, 201)])
    assert conditions == 20
    # The research record states the computed count.
    stated = f"routing conditions or question-text fills on {conditions} pages"
    assert stated in RESEARCH.read_text(encoding="utf-8")


def test_uncooperative_appears_only_where_listed():
    """Research record section 2, items 7 and 8."""
    listed = {
        "PSID/family/2019/fam2019er_codebook.pdf": [
            (591, 596),
            (2058, 2059),
            (2064, 2064),
            (2070, 2075),
        ],
        "PSID/family/2021/FAM2021ER_codebook.pdf": [
            (637, 642),
            (1422, 1423),
            (1428, 1428),
            (1434, 1439),
        ],
        "PSID/family/2023/FAM2023ER_codebook.pdf": [
            (624, 628),
            (1340, 1341),
            (1346, 1346),
            (1352, 1357),
        ],
    }
    # The user guides are in the repository, so they are checked first.
    for year in (2019, 2021, 2023):
        guide = f"tests/data/track_u2/psid_docs/UserGuide{year}.pdf"
        assert not pages_matching(guide, r"(?i)uncooperative"), guide
    for file, ranges in listed.items():
        found = pages_matching(file, r"(?i)uncooperative")
        assert all(any(a <= n <= b for a, b in ranges) for n in found), file
        assert all(any(a <= n <= b for n in found) for a, b in ranges), file


def registry_entry(name, key):
    entries = registry.load_registry(name)["entries"]
    return next(entry for entry in entries if entry["id"] == key)


@pytest.mark.parametrize(
    "anchor",
    REGISTRY_ANCHORS,
    ids=[f"{a['field']}:{a['cited_as'][:28]}" for a in REGISTRY_ANCHORS],
)
def test_registry_anchor_is_on_the_cited_page(anchor):
    field = registry_entry(anchor["registry"], anchor["id"])[anchor["field"]]
    assert anchor["cited_as"] in field
    pages = pdf_pages(pinned_path(anchor["file"]))
    for page, phrase in anchor["checks"]:
        found = normalize(phrase) in pages[page - 1]
        assert found, f"{anchor['file']} p. {page}: {phrase!r}"


def test_every_registry_page_citation_is_checked():
    """In the checked registry text every page cited, every list element
    and both range ends, is checked by a registry quote or anchor that
    cites it; and the entry's citations list every page so checked."""
    checks = [
        (quote, {quote["page"]})
        for quote in REGISTRY_QUOTES
        if "page" in quote and quote.get("cited_as")
    ] + [
        (anchor, {page for page, _ in anchor["checks"]})
        for anchor in REGISTRY_ANCHORS
    ]
    unchecked, uncited = [], []
    for name, key, field in CHECKED_FIELDS:
        entry = registry_entry(name, key)
        text = entry[field]
        own = [
            (check, pages)
            for check, pages in checks
            if (check["registry"], check["id"], check["field"])
            == (name, key, field)
        ]
        for citation, element, ends in page_citations(text):
            number = re.compile(rf"(?<!\d){re.escape(element)}(?!\d)")
            for end in sorted(ends):
                if not any(
                    check["cited_as"] in text
                    and end in pages
                    and number.search(check["cited_as"])
                    for check, pages in own
                ):
                    unchecked.append((field, citation, end))
        cited = {
            (c["file"], c["page"]) for c in entry["citations"] if "page" in c
        }
        for check, pages in own:
            uncited += [
                (field, check["file"], page)
                for page in sorted(pages)
                if (check["file"], page) not in cited
            ]
    assert not unchecked, unchecked
    assert not uncited, uncited
