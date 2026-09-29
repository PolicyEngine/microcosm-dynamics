"""Stage documentary sources for the U2 SSI capture; never reads PSID data.

This is a download command, deliberately separate from the offline parameter
capture. Re-running it records fresh retrieval times and changes the manifest.
Each PolicyEngine snapshot is required to equal its exact Git revision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from capture_track_u2_ssi_parameters import PE_PREFIX, SECTIONS, SSI_FILES

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests/data/track_u2/ssi_sources"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/129.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "identity",
    "Accept-Language": "en-US,en;q=0.9",
}
NOTICES = {
    2012: (76, 66111),
    2013: (77, 65754),
    2014: (78, 66413),
    2015: (79, 64455),
    2016: (80, 66963),
    2017: (81, 74854),
    2018: (82, 59937),
    2019: (83, 53702),
    2020: (84, 56515),
    2021: (85, 67413),
    2022: (86, 58715),
}


def get(url: str) -> tuple[bytes, str]:
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read(), response.url


def fetch(task: tuple[str, str, dict]) -> dict:
    name, url, metadata = task
    if metadata["kind"] == "federal_register_notice":
        _, resolved = get(url)
        url = resolved.split("#")[0].replace("/pdf/", "/html/")
        url = url.replace(".pdf", ".htm")
    data, resolved = get(url)
    if not data or b"Access Denied" in data[:500]:
        raise ValueError(f"empty or refused source: {url}")
    path = OUT / name
    path.write_bytes(data)
    return {
        "path": str(path.relative_to(ROOT)),
        "url": url,
        "resolved_url": resolved,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        **metadata,
    }


def policyengine_snapshots(checkout: Path) -> tuple[str, list[dict]]:
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=checkout, text=True
    ).strip()
    records = []
    for name, relative in SSI_FILES.items():
        original = checkout / (PE_PREFIX + relative)
        data = original.read_bytes()
        committed = subprocess.check_output(
            ["git", "show", f"{revision}:{PE_PREFIX}{relative}"], cwd=checkout
        )
        if data != committed:
            raise ValueError(f"source differs from revision: {original}")
        snapshot = OUT / "policyengine_us" / relative
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_bytes(data)
        records.append(
            {
                "path": str(snapshot.relative_to(ROOT)),
                "url": (
                    "https://raw.githubusercontent.com/PolicyEngine/"
                    f"policyengine-us/{revision}/{PE_PREFIX}{relative}"
                ),
                "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "kind": "policyengine_parameter",
                "parameter": name,
                "source_path": str(original),
                "revision": revision,
                "retrieval": (
                    "read-only clean checkout, bytes equal git object at "
                    "recorded revision"
                ),
            }
        )
    return revision, records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pe-us-dir", type=Path, required=True)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    tasks = []
    for year, (volume, page) in NOTICES.items():
        tasks.append(
            (
                f"fr_ssi_{year}.html",
                f"https://www.govinfo.gov/link/fr/{volume}/{page}",
                {
                    "kind": "federal_register_notice",
                    "income_year": year,
                    "citation": f"{volume} FR {page}",
                    "corrected_republication": year == 2018,
                },
            )
        )
    for year in range(2012, 2023):
        for section in SECTIONS:
            name = f"CFR-{year}-title20-vol2-sec416-{section}.xml"
            tasks.append(
                (
                    name,
                    "https://www.govinfo.gov/content/pkg/"
                    f"CFR-{year}-title20-vol2/xml/{name}",
                    {
                        "kind": "historical_cfr",
                        "edition_year": year,
                        "section": f"416.{section}",
                    },
                )
            )
    with ThreadPoolExecutor(max_workers=8) as pool:
        records = list(pool.map(fetch, tasks))
    revision, snapshots = policyengine_snapshots(args.pe_us_dir.resolve())
    records.extend(snapshots)
    manifest = {
        "schema_version": "populace_dynamics.track_u2_ssi_sources.v1",
        "sources": sorted(records, key=lambda source: source["path"]),
        "errors": [],
        "policyengine_us_revision": revision,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Captured {len(records)} source files in {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
