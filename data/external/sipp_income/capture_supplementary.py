"""Capture supplementary Census SIPP documentation with plain requests.

Release notes, Census's release-to-release variable crosswalks, the 2018
metadata file and the 2018 topic dictionaries that cover income and
programs. Documentation only: no ``pu``/``rw`` data archive and no
``*_validate`` workbook (those carry statistics computed from the survey
records) is requested. Each response is appended to the capture manifests
with its URL, UTC retrieval time, byte size and SHA-256; a refusal is kept
and recorded, never retried with other headers.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parent
ROOT = "https://www2.census.gov/programs-surveys/sipp"
DOCS = f"{ROOT}/tech-documentation"
CROSSWALKS = f"{DOCS}/complete-documents"
DICTIONARIES = f"{DOCS}/data-dictionaries/2018"

#: (local file name, URL). The crosswalks are Census's forward maps from
#: one release's variables to the next release's.
TARGETS = (
    *(
        (
            f"{year}_release_notes.pdf",
            f"{DOCS}/{year}/{year}_SIPP_Release_Notes.pdf",
        )
        for year in range(2019, 2026)
    ),
    ("2018_release_notes.pdf", f"{DOCS}/2018/2018_Release_Notes.pdf"),
    (
        "2018_metadata.pdf",
        f"{ROOT}/data/datasets/2018/2018_SIPP_Metadata_v3.pdf",
    ),
    (
        "2018_programs_dictionary.pdf",
        f"{DICTIONARIES}/2018_SIPP_Programs_Data_Dictionary_v2.pdf",
    ),
    (
        "2018_poverty_income_dictionary.pdf",
        f"{DICTIONARIES}/2018_SIPP_Poverty_Income_Data_Dictionary.pdf",
    ),
    *(
        (
            f"crosswalk_{year - 1}_to_{year}.xlsx",
            f"{CROSSWALKS}/{year}/{year}_SIPP_Crosswalk_{year - 1}_to_"
            f"{year}.xlsx",
        )
        for year in range(2019, 2023)
    ),
)


def capture(filename: str, url: str) -> dict:
    """Fetch one URL once and pin the response body."""
    response = requests.get(url, timeout=120)
    retrieved = datetime.now(timezone.utc).isoformat()
    ok = response.status_code == 200
    path = filename if ok else f"{Path(filename).stem}_response.txt"
    (BASE / path).write_bytes(response.content)
    return {
        "year": int(filename[:4]) if filename[:4].isdigit() else None,
        "url": url,
        "retrieved_utc": retrieved,
        "bytes": len(response.content),
        "sha256": hashlib.sha256(response.content).hexdigest(),
        "path": path,
        "http_status": response.status_code,
        "status": "CAPTURED_METADATA" if ok else "SOURCE_UNAVAILABLE",
    }


def main() -> None:
    manifest_path = BASE / "capture_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    known = {entry["url"] for entry in manifest}
    new = [
        capture(filename, url) for filename, url in TARGETS if url not in known
    ]
    manifest.extend(new)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    with (BASE / "capture_manifest.txt").open("a") as text:
        for entry in new:
            text.write(
                f"\nFile: {entry['path']}\nURL: {entry['url']}\n"
                f"Retrieved UTC: {entry['retrieved_utc']}\n"
                f"Status: {entry['status']} (HTTP {entry['http_status']})\n"
                f"Bytes: {entry['bytes']}\nSHA-256: {entry['sha256']}\n"
            )
    for entry in new:
        print(entry["status"], entry["http_status"], entry["path"])


if __name__ == "__main__":
    main()
