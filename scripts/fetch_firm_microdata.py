#!/usr/bin/env python3
"""Stage the observed firm-microdata sources (#192, Workstream B).

Downloads the DOL Form 5500 / 5500-SF filing datasets and the OSHA ITA
Form 300A establishment summary from pinned URLs into the staging
directory, verifying each raw download against a recorded sha256.

Unlike ``fetch_employer_firm_targets.py``, which builds small committed
aggregate extracts, these are **microdata**: the raw files stay outside
Git (the SIPP/PSID staging convention) and are pinned by digest
instead. See ``data/external/firm_microdata_sources.md``.

The DOL ``.../Latest/...`` URLs are refreshed in place as amended
filings arrive, so the digest identifies the *vintage actually read*,
not a stable publisher artifact. A mismatch is expected after a DOL
refresh and means the pin must be updated deliberately, with the
downstream artifacts rebuilt — it is not a transport error.

Usage::

    python scripts/fetch_firm_microdata.py            # all pinned files
    python scripts/fetch_firm_microdata.py --list     # show the pins
    python scripts/fetch_firm_microdata.py --allow-digest-change
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from populace_dynamics.data.form5500 import firm_data_dir  # noqa: E402


@dataclass(frozen=True)
class Source:
    """A pinned raw download."""

    key: str
    url: str
    sha256: str
    size_bytes: int
    #: Name the reader expects inside the staging directory.
    staged_name: str
    #: Member to extract when the download is a zip archive.
    zip_member: str | None = None


#: Retrieved and digested 2026-08-11.
SOURCES: tuple[Source, ...] = (
    Source(
        key="form5500_2023",
        url=(
            "https://askebsa.dol.gov/FOIA%20Files/2023/Latest/"
            "F_5500_2023_Latest.zip"
        ),
        sha256=(
            "cc89e54c57cb6549ab23842bccc6f4ad20e531ebc42a394732359f6a42b7f595"
        ),
        size_bytes=29_317_144,
        staged_name="f_5500_2023_latest.csv",
        zip_member="f_5500_2023_latest.csv",
    ),
    Source(
        key="form5500_sf_2023",
        url=(
            "https://askebsa.dol.gov/FOIA%20Files/2023/Latest/"
            "F_5500_SF_2023_Latest.zip"
        ),
        sha256=(
            "fa9ff9b15f0eef01dba7533121f33dfa5cc8befca9ce885db9b97063b32fb828"
        ),
        size_bytes=131_009_006,
        staged_name="f_5500_sf_2023_latest.csv",
        zip_member="f_5500_sf_2023_latest.csv",
    ),
    Source(
        key="osha_ita_2025",
        url=(
            "https://www.osha.gov/sites/default/files/"
            "ITA_300A_Summary_Data_2025_through_03-15-2026_v2.csv"
        ),
        sha256=(
            "986f7025c54599c5d022fc472181a013e231b2df0c6e6b8ef5f4f9192d1ff50a"
        ),
        size_bytes=84_600_899,
        staged_name="ITA_300A_Summary_Data_2025.csv",
    ),
)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(source: Source, root: Path, *, allow_digest_change: bool) -> None:
    root.mkdir(parents=True, exist_ok=True)
    raw = root / "raw" / Path(source.url).name.replace("%20", " ")
    raw.parent.mkdir(parents=True, exist_ok=True)

    if not raw.exists():
        print(f"  downloading {source.url}")
        with urllib.request.urlopen(source.url) as response:
            with raw.open("wb") as handle:
                shutil.copyfileobj(response, handle)

    actual = sha256_of(raw)
    size = raw.stat().st_size
    if actual != source.sha256 or size != source.size_bytes:
        message = (
            f"  {source.key}: digest/size changed\n"
            f"    pinned {source.sha256} ({source.size_bytes:,} B)\n"
            f"    actual {actual} ({size:,} B)"
        )
        if not allow_digest_change:
            raise SystemExit(
                message
                + "\n  The DOL/OSHA publisher refreshed this file. Update "
                "the pin deliberately and rebuild every artifact that "
                "read it, or rerun with --allow-digest-change."
            )
        print(message + "\n  (continuing: --allow-digest-change)")

    staged = root / source.staged_name
    if source.zip_member:
        with zipfile.ZipFile(raw) as archive:
            names = archive.namelist()
            if source.zip_member not in names:
                raise SystemExit(
                    f"  {source.key}: {source.zip_member!r} not in archive "
                    f"(members: {names})"
                )
            with archive.open(source.zip_member) as src:
                with staged.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
    elif staged.resolve() != raw.resolve():
        shutil.copyfile(raw, staged)

    print(f"  staged {staged}  ({staged.stat().st_size:,} B)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="show pins only")
    parser.add_argument(
        "--allow-digest-change",
        action="store_true",
        help="proceed when a publisher refresh changes the digest",
    )
    args = parser.parse_args()

    if args.list:
        for source in SOURCES:
            print(f"{source.key}\n  {source.url}\n  {source.sha256}")
        return 0

    root = firm_data_dir()
    print(f"staging into {root}")
    for source in SOURCES:
        print(f"{source.key}:")
        fetch(source, root, allow_digest_change=args.allow_digest_change)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
