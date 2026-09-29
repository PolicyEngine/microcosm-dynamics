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
    for fragment in fragments(quote["text"]):
        # Compare to a bool first so a failure never prints the page, whose
        # codebook columns can carry published frequencies.
        found = fragment in text
        assert found, f"{label(quote)}: {fragment!r} not on the cited page"


@pytest.mark.parametrize(
    "pinned", MANIFEST["pinned_elsewhere"], ids=lambda p: p["file"]
)
def test_pinned_document_bytes(pinned):
    raw = resolve(pinned["file"]).read_bytes()
    assert raw.startswith(b"%PDF")
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
