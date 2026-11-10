"""Reproduce public legal captures with unmodified requests defaults."""

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "capture_manifest.json"
PREVIOUS = (
    {row["url"]: row for row in json.loads(MANIFEST.read_text())}
    if MANIFEST.exists()
    else {}
)
SOURCES = {
    "usc401.html": "https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title26-section401&num=0&edition=prelim",
    "secure_act.html": "https://www.govinfo.gov/content/pkg/PLAW-116publ94/html/PLAW-116publ94.htm",
    "secure2.html": "https://www.govinfo.gov/content/pkg/PLAW-117publ328/html/PLAW-117publ328.htm",
    "tables2022.html": "https://www.govinfo.gov/content/pkg/FR-2020-11-12/html/2020-24723.htm",
    "tables2003.xml": "https://www.govinfo.gov/content/pkg/CFR-2020-title26-vol5/xml/CFR-2020-title26-vol5-sec1-401a9-9.xml",
    "rmd_final2024.html": "https://www.govinfo.gov/content/pkg/FR-2024-07-19/html/2024-14542.htm",
    "rmd_proposed2024.html": "https://www.govinfo.gov/content/pkg/FR-2024-07-19/html/2024-14543.htm",
    "publication590b.html": "https://www.irs.gov/publications/p590b",
    "publication590_2013.pdf": "https://www.irs.gov/pub/irs-prior/p590--2013.pdf",
    "cares_act.html": "https://www.govinfo.gov/content/pkg/PLAW-116publ136/html/PLAW-116publ136.htm",
    "ecfr_beginning_date.html": "https://www.ecfr.gov/current/title-26/section-1.401(a)(9)-2",
    "usc401_lii.html": "https://www.law.cornell.edu/uscode/text/26/401",
    "tables2003.html": "https://www.govinfo.gov/content/pkg/FR-2002-04-17/html/02-8963.htm",
    "waiver2009.html": "https://www.govinfo.gov/content/pkg/PLAW-110publ458/html/PLAW-110publ458.htm",
    "current_beginning_date.html": "https://www.law.cornell.edu/cfr/text/26/1.401(a)(9)-2",
    "announcement2026_7.pdf": "https://www.irs.gov/pub/irs-drop/a-26-07.pdf",
    "tables2003.pdf": "https://www.govinfo.gov/content/pkg/FR-2002-04-17/pdf/02-8963.pdf",
    "review_cfr2020_tables.xml": "https://www.govinfo.gov/content/pkg/CFR-2020-title26-vol6/xml/CFR-2020-title26-vol6-sec1-401a9-9.xml",
    "review_cfr2020_tables.pdf": "https://www.govinfo.gov/content/pkg/CFR-2020-title26-vol6/pdf/CFR-2020-title26-vol6-sec1-401a9-9.pdf",
    "review_correction2002_05_24.html": "https://www.govinfo.gov/content/pkg/FR-2002-05-24/html/C2-8963.htm",
}


def capture(item):
    name, url = item
    # Never retry a blocked source or silently refresh the pinned vintage.
    if url in PREVIOUS:
        row = PREVIOUS[url]
        if row.get("file"):
            body = (ROOT / row["file"]).read_bytes()
            if (len(body), hashlib.sha256(body).hexdigest()) != (
                row["bytes"],
                row["sha256"],
            ):
                raise ValueError(f"pinned capture differs: {row['file']}")
        return row
    now = datetime.now(timezone.utc).isoformat()
    if (ROOT / name).exists():
        body = (ROOT / name).read_bytes()
        return {
            "file": name,
            "url": url,
            "retrieved_at_utc": datetime.fromtimestamp(
                (ROOT / name).stat().st_mtime, timezone.utc
            ).isoformat(),
            "timestamp_note": "Retrieval completion (file write time)",
            "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
            "http_status": 200,
            "status": "captured",
        }
    try:
        response = requests.get(url, timeout=60)
    except requests.RequestException as exc:
        return {
            "file": None,
            "url": url,
            "retrieved_at_utc": now,
            "status": "SOURCE_UNAVAILABLE",
            "error": type(exc).__name__,
        }
    body = response.content
    blocked = response.status_code in (403, 429) or any(
        word in body[:10000].lower()
        for word in (b"captcha", b"cf-chl-", b"access denied")
    )
    status = (
        "SOURCE_BLOCKED"
        if blocked
        else "captured" if response.ok else "SOURCE_UNAVAILABLE"
    )
    if status == "captured":
        (ROOT / name).write_bytes(body)
    return {
        "file": name if status == "captured" else None,
        "url": url,
        "retrieved_at_utc": now,
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "http_status": response.status_code,
        "status": status,
    }


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(capture, SOURCES.items()))
    MANIFEST.write_text(json.dumps(records, indent=2) + "\n")
    for record in records:
        print(record["file"], record.get("http_status"), record["status"])
