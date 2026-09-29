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

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "tests/data/track_u2/psid_docs"
MANIFEST = json.loads((DOCS / "manifest.json").read_text(encoding="utf-8"))
RESEARCH = ROOT / MANIFEST["research_record"]
QUOTES = MANIFEST["research_quotes"]
ELLIPSIS = re.compile(r"\s*(?:\.\.\.|…)\s*")
OPENING = re.compile(r"(?:^|(?<=[\s(\[—:]))'(?=\S)")
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
    """Fold whitespace, quote marks, dashes and ligatures; keep case."""
    text = unicodedata.normalize("NFKC", text).replace("­", "")
    text = re.sub(r"[‘’‚‛′`´]", "'", text)
    text = re.sub(r"[“”„‟″]", '"', text)
    text = re.sub(r"[‐-―−]", "-", text)
    return re.sub(r"\s+", " ", text).strip()


def fragments(text):
    return [normalize(part) for part in ELLIPSIS.split(text) if part.strip()]


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
def html_lines(path):
    # Lines are LF-terminated, as grep -n counts them.
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
    assert len(spans) >= 70
    unregistered = [
        span
        for span in spans
        if not any(normalize(span) in text for text in registered)
    ]
    assert not unregistered, unregistered


@pytest.mark.parametrize("quote", QUOTES, ids=label)
def test_research_quote_appears_where_cited(quote):
    path = resolve(quote["file"])
    if "line" in quote:
        text = html_lines(path)[quote["line"] - 1]
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


def test_quoted_psid_documents_are_pinned():
    pinned = {p["file"]: p["sha256"] for p in MANIFEST["pinned_elsewhere"]}
    archived = {s["file"] for s in MANIFEST["sources"]}
    for quote in QUOTES:
        assert quote["file"] in pinned or quote["file"] in archived, quote
