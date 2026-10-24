"""Capture TR 2026 Table V.C1 as a byte-exact table fragment (A-COLA).

Registration 18 (trust fund test A-COLA, decision d658) takes the
spec-only null's COLAs c_k from "the 2026 Trustees Report's Table V.C1,
intermediate assumptions, the increases effective December 2027, 2028
and 2029".  The Report publishes Table V.C1 on no page of its own: its
List of Tables (``X1_trLOT.html``, linked from the table of contents as
"LIST OF TABLES") links the entry "V.C1 Cost-of-Living Benefit
Increases, ..." to ``V_C_prog.html#1047210``, the chapter page of
section V.C, which holds 26 tables and the chapter's prose.  A builder
of A-COLA may read no Trustees Report page or table that prints OASDI
cost, cost rates, income rates or balances, so this script does not
store the chapter page.  It fetches the page once, keeps it in memory,
cuts out the one ``<table>`` element whose caption is Table V.C1's, and
writes:

* the fragment, byte for byte as served (``trustees2026_v_c1_table.html``);
* ``capture_manifest.txt``, one line in the vintage-1 grammar
  ``<UTC> <sha256> <bytes> <filename>`` for the fragment;
* ``capture_record.json``: the URL, the retrieval time, the fetch mode,
  the HTTP status, the SHA-256 and size of the whole page as served, and
  the fragment's byte offsets in it, so the fragment can be located again
  in any later fetch whose table bytes are unchanged.

The fetch follows ``EV/pia-captures-20260929/_tools/capture.sh``: plain
curl first, then full Chrome request headers over HTTP/2 (gzip and
deflate only), storing the decoded body.  Nothing else on the page is
printed or stored.  The script refuses to overwrite an existing file.

Usage::

    python scripts/capture_tr2026_v_c1.py [--output-dir DIR]
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import subprocess
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = "https://www.ssa.gov/oact/TR/2026/V_C_prog.html"
#: The anchor the 2026 List of Tables gives for Table V.C1.
LIST_OF_TABLES_URL = "https://www.ssa.gov/oact/TR/2026/X1_trLOT.html"
LIST_OF_TABLES_HREF = "V_C_prog.html#1047210"
CAPTION = (
    "Table V.C1.—Cost-of-Living Benefit Increases, Average Wage "
    "Index, Contribution and Benefit Bases, and Retirement Earnings Test "
    "Exempt Amounts, 1975-2035"
)
DEFAULT_OUTPUT_DIR = (
    ROOT / "data" / "external" / "snapshots" / "tr2026_v_c1_vintage1"
)
FRAGMENT_NAME = "trustees2026_v_c1_table.html"
MANIFEST_NAME = "capture_manifest.txt"
RECORD_NAME = "capture_record.json"
TIMING_NOTE_NAME = "cola_timing_note.txt"
_BROWSER_HEADERS = (
    "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,"
    "image/avif,image/webp,image/apng,*/*;q=0.8,"
    "application/signed-exchange;v=b3;q=0.7",
    "Accept-Language: en-US,en;q=0.9",
    "Accept-Encoding: gzip, deflate",
    "Cache-Control: no-cache",
    "Pragma: no-cache",
    'Sec-Ch-Ua: "Google Chrome";v="129", "Not=A?Brand";v="8", '
    '"Chromium";v="129"',
    "Sec-Ch-Ua-Mobile: ?0",
    'Sec-Ch-Ua-Platform: "macOS"',
    "Sec-Fetch-Dest: document",
    "Sec-Fetch-Mode: navigate",
    "Sec-Fetch-Site: none",
    "Sec-Fetch-User: ?1",
    "Upgrade-Insecure-Requests: 1",
)


def _fetch(mode: str) -> tuple[str, bytes, str]:
    """One curl request; returns (HTTP status, decoded body, UTC time)."""

    command = ["curl", "-sS", "-L", "--max-time", "180"]
    if mode == "browser-h2":
        command += ["--http2", "--compressed"]
        for header in _BROWSER_HEADERS:
            command += ["-H", header]
    command += ["-w", "\n%{http_code}", SOURCE_URL]
    retrieved = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    out = subprocess.run(command, capture_output=True, check=False)
    body, _, status = out.stdout.rpartition(b"\n")
    return status.decode().strip(), body, retrieved


class _TableSpans(HTMLParser):
    """Character spans of every outermost ``<table>`` and its caption."""

    def __init__(self, text: str) -> None:
        super().__init__(convert_charrefs=True)
        self._line_starts = [0]
        for index, char in enumerate(text):
            if char == "\n":
                self._line_starts.append(index + 1)
        self._text = text
        self._depth = 0
        self._start: int | None = None
        self._caption: list[str] | None = None
        self._captions: list[str] = []
        self.tables: list[tuple[int, int, str]] = []

    def _offset(self) -> int:
        line, column = self.getpos()
        return self._line_starts[line - 1] + column

    def handle_starttag(self, tag, attrs):  # noqa: ANN001
        if tag == "table":
            self._depth += 1
            if self._depth == 1:
                self._start = self._offset()
                self._captions = []
        elif tag == "caption" and self._depth == 1:
            self._caption = []

    def handle_data(self, data):  # noqa: ANN001
        if self._caption is not None:
            self._caption.append(data)

    def handle_endtag(self, tag):  # noqa: ANN001
        if tag == "caption" and self._caption is not None:
            self._captions.append(
                " ".join("".join(self._caption).replace("\xa0", " ").split())
            )
            self._caption = None
        elif tag == "table":
            self._depth -= 1
            if self._depth == 0 and self._start is not None:
                end = self._text.index(">", self._offset()) + 1
                caption = self._captions[0] if self._captions else ""
                self.tables.append((self._start, end, caption))
                self._start = None


def table_fragment(page: bytes) -> tuple[bytes, int, int]:
    """The V.C1 ``<table>`` element's exact bytes and its byte offsets."""

    text = page.decode("utf-8")
    parser = _TableSpans(text)
    parser.feed(text)
    parser.close()
    matches = [span for span in parser.tables if span[2] == CAPTION]
    if len(matches) != 1:
        raise ValueError(
            f"expected exactly one table captioned {CAPTION!r}; found "
            f"{len(matches)}"
        )
    start, end, _ = matches[0]
    if not text[start:end].lower().startswith("<table"):
        raise ValueError("the V.C1 span does not start at a <table> tag")
    if not text[start:end].lower().endswith("</table>"):
        raise ValueError("the V.C1 span does not end at </table>")
    byte_start = len(text[:start].encode("utf-8"))
    byte_end = len(text[:end].encode("utf-8"))
    fragment = page[byte_start:byte_end]
    if fragment != text[start:end].encode("utf-8"):
        raise ValueError("the fragment's bytes differ from its decoded text")
    return fragment, byte_start, byte_end


class _COLATimingNote(HTMLParser):
    """Read only V.C1 footnote a, between its two named anchors."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.active = False
        self.finished = False
        self.parts: list[str] = []
        self.matches = 0

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            name = dict(attrs).get("name")
            if name == "12":
                self.active = True
                self.matches += 1
            elif name == "13" and self.active:
                self.active = False
                self.finished = True

    def handle_endtag(self, tag):
        if self.active and tag in {"div", "p", "br"}:
            self.parts.append(" ")

    def handle_data(self, data):
        if self.active:
            self.parts.append(data)


def cola_timing_note(page: bytes) -> str:
    """The timing note linked as footnote a from V.C1's COLA header.

    The note is outside the table element. No adjacent note or chapter
    text is returned. The registered input includes December timing.
    """
    parser = _COLATimingNote()
    parser.feed(page.decode("utf-8"))
    note = " ".join("".join(parser.parts).replace("\xa0", " ").split())
    if parser.matches != 1 or not parser.finished:
        raise ValueError(
            "expected one V.C1 COLA footnote between anchors 12 and 13"
        )
    if "December" not in note or "1982" not in note:
        raise ValueError("V.C1 COLA footnote does not confirm December timing")
    return note


def _write_new(path: Path, data: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)
    for name in (FRAGMENT_NAME, TIMING_NOTE_NAME, MANIFEST_NAME, RECORD_NAME):
        if (args.output_dir / name).exists():
            raise FileExistsError(args.output_dir / name)
    status, body, retrieved = _fetch("plain")
    mode = "plain"
    if status != "200":
        status, body, retrieved = _fetch("browser-h2")
        mode = "browser-h2"
    if status != "200" or not body:
        raise SystemExit(f"fetch failed: HTTP {status} ({mode})")
    fragment, start, end = table_fragment(body)
    timing_note = (cola_timing_note(body) + "\n").encode()
    timing_sha = hashlib.sha256(timing_note).hexdigest()
    fragment_sha = hashlib.sha256(fragment).hexdigest()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_new(args.output_dir / FRAGMENT_NAME, fragment)
    _write_new(args.output_dir / TIMING_NOTE_NAME, timing_note)
    _write_new(
        args.output_dir / MANIFEST_NAME,
        (
            f"{retrieved} {fragment_sha} {len(fragment)} {FRAGMENT_NAME}\n"
            f"{retrieved} {timing_sha} {len(timing_note)} {TIMING_NOTE_NAME}\n"
        ).encode(),
    )
    record = {
        "schema_version": "tr2026_v_c1_capture.v1",
        "table": "Table V.C1",
        "caption": CAPTION,
        "source_url": SOURCE_URL,
        "located_from": {
            "list_of_tables_url": LIST_OF_TABLES_URL,
            "href": LIST_OF_TABLES_HREF,
            "how": (
                "the 2026 Report's table of contents "
                "(https://www.ssa.gov/oact/TR/2026/trTOC.html) links no "
                "table; it links the List of Tables, whose one entry naming "
                "V.C1 links this anchor on the section V.C chapter page"
            ),
        },
        "retrieved_utc": retrieved,
        "fetch_mode": mode,
        "fetch_method": (
            "curl -sS -L; on a status other than 200, curl --http2 "
            "--compressed with Chrome 129 request headers (gzip, deflate); "
            "the decoded body is kept in memory only"
        ),
        "http_status": int(status),
        "timing_footnote": {
            "file": TIMING_NOTE_NAME,
            "sha256": timing_sha,
            "text": timing_note.decode().strip(),
            "anchor": "12",
            "extraction": "V.C1 COLA note only; whitespace normalized",
        },
        "page": {
            "stored": False,
            "why_not_stored": (
                "Table V.C1 has no page of its own; the chapter page holds "
                "26 tables and the chapter prose, and an A-COLA builder may "
                "read no Trustees Report page or table that prints OASDI "
                "cost, cost rates, income rates or balances "
                "(EV/RESTRICTED-FILES.md, 2026-10-01 02:40)"
            ),
            "sha256": hashlib.sha256(body).hexdigest(),
            "bytes": len(body),
            "note": (
                "the page's bytes vary between requests outside the "
                "tables, so a later fetch may not reproduce this digest"
            ),
        },
        "fragment": {
            "file": FRAGMENT_NAME,
            "sha256": fragment_sha,
            "bytes": len(fragment),
            "byte_offset_start": start,
            "byte_offset_end": end,
            "definition": (
                "page[byte_offset_start:byte_offset_end], the outermost "
                "<table> element whose <caption> equals the caption above "
                "(whitespace and no-break spaces normalized for the match)"
            ),
        },
    }
    _write_new(
        args.output_dir / RECORD_NAME,
        (json.dumps(record, indent=2) + "\n").encode(),
    )
    print(args.output_dir / FRAGMENT_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
