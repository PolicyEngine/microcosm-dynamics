"""Capture annual IRS notices with plain requests; never retry a refusal.

Run with the clone's Python. Existing pinned captures are left unchanged.
Only successful PDF responses become legal captures. Ordinary errors are
SOURCE_UNAVAILABLE; access refusals and challenges are SOURCE_BLOCKED.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import requests

ANNUAL_NOTICES = {
    2002: "2001-84",
    2003: "2002-71",
    2004: "2003-73",
    2005: "2004-72",
    2006: "2005-75",
    2007: "2006-98",
    2008: "2007-87",
    2009: "2008-102",
    2010: "2009-94",
    2011: "2010-78",
    2012: "2011-90",
    2013: "2012-67",
    2014: "2013-73",
    2015: "2014-70",
    2016: "2015-75",
    2017: "2016-62",
    2018: "2017-64",
    2019: "2018-83",
    2020: "2019-59",
    2021: "2020-79",
    2022: "2021-61",
    2023: "2022-55",
    2024: "2023-75",
    2025: "2024-80",
    2026: "2025-67",
}

# These older standalone notice PDFs return HTTP 404. The IRS-published
# bulletin citations identify their original publication, independently of
# those missing standalone URLs. This does not retry an automation refusal.
BULLETINS = {
    2002: "2001-53",
    2003: "2002-45",
    2004: "2003-45",
    2005: "2004-46",
    2006: "2005-45",
    2007: "2006-46",
    2008: "2007-45",
    2011: "2010-49",
    2012: "2011-47",
    2013: "2012-50",
    2014: "2013-49",
    2015: "2014-48",
}


def capture(first_year: int, last_year: int, bulletins: bool = False) -> None:
    """Append capture metadata immediately after each plain HTTP request."""
    directory = Path(__file__).resolve().parent
    manifest_path = directory / "capture_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for year, notice in ANNUAL_NOTICES.items():
        if not first_year <= year <= last_year:
            continue
        filename = f"notice_{notice.replace('-', '_')}.pdf"
        short_year, number = notice.split("-")
        url = (
            f"https://www.irs.gov/pub/irs-drop/n-{short_year[2:]}-{number}.pdf"
        )
        if bulletins:
            if year not in BULLETINS:
                continue
            bulletin = BULLETINS[year]
            filename = f"irb_{bulletin.replace('-', '_')}.pdf"
            short_year, number = bulletin.split("-")
            url = f"https://www.irs.gov/pub/irs-irbs/irb{short_year[2:]}-{number}.pdf"
        if any(
            row["file"] == filename or row.get("requested_file") == filename
            for row in manifest
        ):
            print(year, filename, "already recorded")
            continue
        row = {
            "file": None,
            "requested_file": filename,
            "url": url,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "bytes": None,
            "sha256": None,
            "http_status": None,
            "status": "SOURCE_UNAVAILABLE",
            "effective_year": year,
            "authority": f"IRS Notice {notice}",
        }
        try:
            response = requests.get(url, timeout=30)
            row["http_status"] = response.status_code
            if response.status_code == 200 and response.content[:4] == b"%PDF":
                content = response.content
                (directory / filename).write_bytes(content)
                row["file"] = filename
                row["status"] = "captured"
                row["bytes"] = len(content)
                row["sha256"] = hashlib.sha256(content).hexdigest()
            else:
                challenge = any(
                    token in response.content[:10000].lower()
                    for token in (
                        b"captcha",
                        b"access denied",
                        b"checking your browser",
                        b"verify you are human",
                    )
                )
                if response.status_code in (401, 403, 429) or challenge:
                    row["status"] = "SOURCE_BLOCKED"
                row["reason"] = "HTTP error or response is not a PDF"
        except requests.RequestException as exc:
            row["reason"] = type(exc).__name__
        manifest.append(row)
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        print(year, filename, row["status"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first-year", type=int, default=2002)
    parser.add_argument("--last-year", type=int, default=2026)
    parser.add_argument("--bulletins", action="store_true")
    arguments = parser.parse_args()
    capture(arguments.first_year, arguments.last_year, arguments.bulletins)
