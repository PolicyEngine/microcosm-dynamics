"""Build the codebook value tables behind the group-attribute readers.

For every family-file variable that
:mod:`populace_dynamics.data.group_attributes_psid` reads (race and
Spanish descent of head and wife 1985-2023, COMPLETED ED-HD/WF 1993-2023,
state born and year came to the U.S. 2013-2023), this script extracts the
"Value/Range Code" table from the wave's staged codebook PDF and writes
``data/external/psid_group_attribute_codebook_values_v1.json``: each
variable's label, the codebook page it sits on, and its documented codes
and ranges with their text, plus the codebook PDF's path and SHA-256.

It reads documentation only (codebook PDFs through ``pdftotext -layout``,
and the label blocks of the ``.sps`` setup files); it opens no PSID data
file. The readers load the table, pinned by SHA-256, to check every
observed code; a test holds every documented code to a meaning in the
module's code frames.

Usage::

    python scripts/build_group_attribute_codebook_values.py [--psid-dir D]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from populace_dynamics.data import family, psid
from populace_dynamics.data import group_attributes_psid as gap

OUT = gap.CODEBOOK_VALUES_PATH

_HEADER = re.compile(r'^(V\d+|ER\d+[A-Z0-9]*)\s+"([^"]*)"')
_ROW = re.compile(
    r"^\s*(?:[\d,]+|-)\s+(?:[\d.]+|-)\s+"
    r"(-?[\d,]+(?:\s*-\s*-?[\d,]+)?)\s+(\S.*)$"
)
_SKIP = re.compile(
    r"(^\s*Page \d+ of \d+\s*$)|(^\s*Filename\s*=)"
    r"|(PANEL STUDY OF INCOME DYNAMICS)",
    re.IGNORECASE,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _codebook_pdf(wave: int, root: Path) -> Path:
    base = root / "family" / str(wave)
    hits = sorted(
        p
        for p in base.iterdir()
        if re.search(r"codebook.*\.pdf$", p.name, re.IGNORECASE)
    )
    if len(hits) != 1:
        raise SystemExit(
            f"wave {wave}: expected one codebook PDF in {base}, found "
            f"{[p.name for p in hits]}"
        )
    return hits[0]


def _pdftotext_version() -> str:
    run = subprocess.run(
        ["pdftotext", "-v"], capture_output=True, text=True, check=False
    )
    return (run.stderr or run.stdout).splitlines()[0].strip()


def _parse_code(token: str) -> dict[str, object]:
    token = token.replace(",", "").replace(" ", "")
    match = re.fullmatch(r"(-?\d+)-(-?\d+)", token)
    if match:
        return {"range": [int(match.group(1)), int(match.group(2))]}
    return {"code": int(token)}


def extract_entry(text: str, variable: str) -> dict[str, object]:
    """The label, page and value table of ``variable`` in codebook text.

    ``text`` is ``pdftotext -layout`` output, whose pages are separated
    by form feeds; the table is read from the variable's header to the
    next variable header, across page breaks, skipping running headers
    and footers and joining continuation lines to the row above.
    """

    pages = text.split("\f")
    for page_number, page in enumerate(pages, start=1):
        lines = page.splitlines()
        for i, line in enumerate(lines):
            header = _HEADER.match(line)
            if not header or header.group(1) != variable:
                continue
            label = " ".join(header.group(2).split())
            values: list[dict[str, object]] = []
            in_table = False
            rest = lines[i + 1 :] + [
                ln
                for later in pages[page_number:]
                for ln in later.splitlines()
            ]
            for ln in rest:
                if _HEADER.match(ln):
                    break
                if "Value/Range Code" in ln:
                    in_table = True
                    continue
                if not in_table or not ln.strip() or _SKIP.search(ln):
                    continue
                row = _ROW.match(ln)
                if row:
                    entry = _parse_code(row.group(1))
                    entry["text"] = " ".join(row.group(2).split())
                    values.append(entry)
                elif values:
                    values[-1][
                        "text"
                    ] = f"{values[-1]['text']} {' '.join(ln.split())}"
            if not values:
                raise SystemExit(f"{variable}: empty value table")
            return {"label": label, "page": page_number, "values": values}
    raise SystemExit(f"{variable}: header not found in the codebook text")


def build(root: Path) -> dict[str, object]:
    """The full value table for every adjudicated family wave."""

    out: dict[str, object] = {}
    for wave, items in sorted(gap.FAMILY_ITEMS.items()):
        pdf = _codebook_pdf(wave, root)
        text = subprocess.run(
            ["pdftotext", "-layout", str(pdf), "-"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        sps_path, _ = family._family_paths(wave, root)
        sps_labels = psid.parse_sps_labels(sps_path)
        variables: dict[str, object] = {}
        for var, want in items.labels().items():
            if var == items.interview[0]:
                continue
            entry = extract_entry(text, var)
            if " ".join(want.split()) != entry["label"]:
                raise SystemExit(
                    f"wave {wave} {var}: codebook label {entry['label']!r} "
                    f"differs from the adjudicated {want!r}"
                )
            if " ".join(sps_labels.get(var, "").split()) != entry["label"]:
                raise SystemExit(
                    f"wave {wave} {var}: the .sps label differs from the "
                    "codebook's"
                )
            variables[var] = entry
        formats = sorted((root / "family" / str(wave)).glob("*_formats.sas"))
        if len(formats) > 1:
            raise SystemExit(
                f"wave {wave}: multiple SAS formats files in the source "
                "documentation; adjudicate one before building"
            )
        out[str(wave)] = {
            "codebook": {
                "path": str(pdf.relative_to(root)),
                "sha256": _sha256(pdf),
            },
            "formats_sas": (
                {
                    "path": str(formats[0].relative_to(root)),
                    "sha256": _sha256(formats[0]),
                }
                if len(formats) == 1
                else None
            ),
            "variables": variables,
        }
    return {
        "schema_version": "psid_group_attribute_codebook.v1",
        "generated_by": "scripts/build_group_attribute_codebook_values.py",
        "extraction": (
            f"{_pdftotext_version()} -layout; value rows are the codebook's "
            "'Count / % / Value/Range Code / Value/Range Text' table with "
            "continuation lines joined (counts and percents dropped); page "
            "is the 1-based PDF page of the variable header"
        ),
        "note": (
            "Documentation only: labels, value codes and their text from "
            "the staged PSID family codebook PDFs. No data value or count "
            "is recorded."
        ),
        "family": out,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--psid-dir", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args(argv)
    root = psid._resolve_data_dir(args.psid_dir)
    table = build(root)
    payload = json.dumps(table, indent=1, sort_keys=True) + "\n"
    args.out.write_text(payload)
    print(args.out, hashlib.sha256(payload.encode()).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
