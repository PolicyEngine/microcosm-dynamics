"""SSA's 2006 Earnings Public-Use File (EPUF), read byte-pinned.

EPUF is a 1 percent systematic sample of Social Security numbers
issued before January 2007 (Compson 2011, Social Security Bulletin
71(4); https://www.ssa.gov/policy/docs/microdata/epuf/index.html).
It has two linked files:

- ``EPUF2006_DEMOGRAPHIC.csv``: one row per sampled person (4,384,254
  rows; the "4,348,254" printed in parts of the SSB article is a digit
  transposition, see the article's own arithmetic and the dictionary)
  with year of birth, sex (1 male, 2 female, 3 unspecified), aggregate
  1937-1950 capped taxable earnings and quarters of coverage, and
  1951-1952 quarters of coverage.
- ``EPUF2006_ANNUAL.csv``: one row per person-year with positive
  capped taxable earnings, 1951-2006 (60,326,474 rows over 3,131,424
  persons). **A year with zero earnings has no row.**

``ANNUAL_EARNINGS`` is capped Social Security taxable earnings: covered
wages plus covered self-employment income, summed over employers and
capped at the year's contribution and benefit base. SSA applied a
disclosure operator before release (dictionary; SSB pp. 33-59): values
below $100 are replaced by one per-year mean, values within one
rounding base below the cap by one per-year band mean, and the rest are
random-rounded to $25 ($100-$999), $100 ($1,000-$49,999) or $1,000
($50,000 and over). The operator preserves each person-year's
worker/non-worker and at-maximum/below-maximum status by design.
Earnings at ages 14 and younger (cohorts born after 1937) and 86 and
older were zeroed, so rows exist only at calendar-year ages 15-85.

The CSV headers differ from the dictionary's names (``TOT_COV_EARN3750``
/ ``QC3750`` / ``QC5152`` / ``YEAR_EARN`` against the dictionary's
``AE3750`` / ``TC3750`` / ``TC5152`` / ``YEAR``); this reader renames
them to snake_case. ``ANNUAL_QTRS`` is the literal ``"."`` for every
1951-1952 row and is read as a missing value.

Staging: the extracted members live outside the repository under
``~/PolicyEngine/epuf-data/csv`` (override with
``POPULACE_DYNAMICS_EPUF_DIR``, which names the folder holding the two
CSVs). The download record (URL, retrieval date, bytes, SHA-256 and
the 2026-10-01 verification against the live server) is
``data/external/epuf_2006/provenance.md``. Every read verifies the
SHA-256 in :data:`EPUF_SHA256` unless the caller opts out, so a file
with other bytes is refused rather than silently read.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

__all__ = [
    "ANNUAL_FILE",
    "DEMOGRAPHIC_FILE",
    "EPUF_ANNUAL_ROWS",
    "EPUF_EARNER_PERSONS",
    "EPUF_PERSONS",
    "EPUF_SHA256",
    "EPUFNotStagedError",
    "epuf_status",
    "read_annual",
    "read_demographic",
]

DEMOGRAPHIC_FILE = "EPUF2006_DEMOGRAPHIC.csv"
ANNUAL_FILE = "EPUF2006_ANNUAL.csv"

#: SHA-256 of the two data members of ``epuf2006_csv_files.zip`` (zip
#: SHA-256 0bb97275cc35a1bb42d34d26acbc9df720d4f875854ba1d02c50323d2357003b,
#: 291,602,034 bytes, byte-identical to what www.ssa.gov served on
#: 2026-10-01; data/external/epuf_2006/provenance.md).
EPUF_SHA256: dict[str, str] = {
    DEMOGRAPHIC_FILE: (
        "195db459ca7b7c810162cb6e432371e8787eba8331787d2ba1eace1a0da2ccb0"
    ),
    ANNUAL_FILE: (
        "a47315b56214df66fb9f9abcb2caa60779c8b3d091ded199323672c27e3ea105"
    ),
}

#: Row counts of the pinned bytes (asserted on every full read).
EPUF_PERSONS = 4_384_254
EPUF_EARNER_PERSONS = 3_131_424
EPUF_ANNUAL_ROWS = 60_326_474

EPUF_FIRST_YEAR = 1951
EPUF_LAST_YEAR = 2006

_DATA_DIR_ENV = "POPULACE_DYNAMICS_EPUF_DIR"
_DEFAULT_DATA_DIR = Path("~/PolicyEngine/epuf-data/csv").expanduser()
_README_POINTER = (
    "stage the members of SSA's epuf2006_csv_files.zip under "
    "~/PolicyEngine/epuf-data/csv (or POPULACE_DYNAMICS_EPUF_DIR); see "
    "data/external/epuf_2006/provenance.md"
)

_DEMOGRAPHIC_COLUMNS = {
    "ID": "person_id",
    "YOB": "birth_year",
    "SEX": "sex",
    "TOT_COV_EARN3750": "earnings_1937_1950",
    "QC3750": "qc_1937_1950",
    "QC5152": "qc_1951_1952",
}
_ANNUAL_COLUMNS = {
    "ID": "person_id",
    "YEAR_EARN": "year",
    "ANNUAL_EARNINGS": "earnings",
    "ANNUAL_QTRS": "quarters",
}


class EPUFNotStagedError(FileNotFoundError):
    """The EPUF members are missing or are not the pinned bytes."""


def _resolve_data_dir(data_dir: Path | None) -> Path:
    """Resolve the EPUF folder from argument, env var, then default."""
    if data_dir is not None:
        return Path(data_dir).expanduser()
    env_value = os.environ.get(_DATA_DIR_ENV)
    if env_value:
        return Path(env_value).expanduser()
    return _DEFAULT_DATA_DIR


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 22), b""):
            digest.update(block)
    return digest.hexdigest()


@lru_cache(maxsize=8)
def _cached_sha256(path: str, size: int, mtime_ns: int) -> str:
    # Keyed on size and mtime so a replaced file is re-hashed.
    del size, mtime_ns
    return _file_sha256(Path(path))


def _sha256(path: Path) -> str:
    stat = path.stat()
    return _cached_sha256(str(path), stat.st_size, stat.st_mtime_ns)


def epuf_status(*, data_dir: Path | None = None) -> dict[str, object]:
    """Where EPUF is staged and whether the staged bytes are the pinned ones.

    ``staged`` says whether both members exist; ``pinned`` whether both
    hash to :data:`EPUF_SHA256`. Only the two members are read, to hash
    them.
    """
    directory = _resolve_data_dir(data_dir)
    paths = {name: directory / name for name in EPUF_SHA256}
    staged = all(path.is_file() for path in paths.values())
    hashes = (
        {name: _sha256(path) for name, path in paths.items()} if staged else {}
    )
    return {
        "directory": str(directory),
        "staged": staged,
        "sha256": hashes,
        "pinned_sha256": dict(EPUF_SHA256),
        "pinned": staged and hashes == EPUF_SHA256,
    }


def _member_path(name: str, data_dir: Path | None, verify: bool) -> Path:
    path = _resolve_data_dir(data_dir) / name
    if not path.is_file():
        raise EPUFNotStagedError(
            f"No {name} under {path.parent}; {_README_POINTER}."
        )
    if verify:
        observed = _sha256(path)
        if observed != EPUF_SHA256[name]:
            raise EPUFNotStagedError(
                f"{path} has SHA-256 {observed}, not the pinned "
                f"{EPUF_SHA256[name]}; nothing was read. {_README_POINTER}."
            )
    return path


def read_demographic(
    *, data_dir: Path | None = None, verify: bool = True
) -> pd.DataFrame:
    """Read the demographic member: one row per sampled person.

    Columns: ``person_id`` (int32), ``birth_year`` (int16), ``sex``
    (int8; 1 male, 2 female, 3 unspecified), ``earnings_1937_1950``
    (int32; SSA top-codes it at $41,500 and bottom-codes it at $39),
    ``qc_1937_1950`` and ``qc_1951_1952`` (int8).
    """
    path = _member_path(DEMOGRAPHIC_FILE, data_dir, verify)
    frame = pd.read_csv(
        path,
        dtype={
            "ID": "int32",
            "YOB": "int16",
            "SEX": "int8",
            "TOT_COV_EARN3750": "int32",
            "QC3750": "int8",
            "QC5152": "int8",
        },
    ).rename(columns=_DEMOGRAPHIC_COLUMNS)
    if len(frame) != EPUF_PERSONS:
        raise ValueError(
            f"{path} has {len(frame):,} persons; the pinned file has "
            f"{EPUF_PERSONS:,}."
        )
    return frame


def read_annual(
    *,
    years: Iterable[int] | None = None,
    data_dir: Path | None = None,
    verify: bool = True,
) -> pd.DataFrame:
    """Read the annual member: one row per person-year with earnings.

    Columns: ``person_id`` (int32), ``year`` (int16), ``earnings``
    (int32, capped taxable earnings after SSA's disclosure operator,
    always positive), ``quarters`` (nullable Int8; missing for every
    1951-1952 row). ``years`` keeps only those calendar years; a person
    with no row in a year had zero capped taxable earnings that year.
    """
    path = _member_path(ANNUAL_FILE, data_dir, verify)
    frame = pd.read_csv(
        path,
        dtype={
            "ID": "int32",
            "YEAR_EARN": "int16",
            "ANNUAL_EARNINGS": "int32",
            "ANNUAL_QTRS": "category",
        },
    ).rename(columns=_ANNUAL_COLUMNS)
    if len(frame) != EPUF_ANNUAL_ROWS:
        raise ValueError(
            f"{path} has {len(frame):,} rows; the pinned file has "
            f"{EPUF_ANNUAL_ROWS:,}."
        )
    # ``ANNUAL_QTRS`` is "." (missing) for 1951-1952 and 0-4 otherwise;
    # decoding the six categories is far faster than parsing 60M strings.
    labels = frame["quarters"].cat.categories
    decoded = np.array(
        [-1 if label == "." else int(label) for label in labels],
        dtype="int8",
    )[frame["quarters"].cat.codes.to_numpy()]
    frame["quarters"] = pd.arrays.IntegerArray(
        np.where(decoded < 0, 0, decoded).astype("int8"), decoded < 0
    )
    if years is not None:
        wanted = np.asarray(sorted({int(year) for year in years}))
        outside = wanted[
            (wanted < EPUF_FIRST_YEAR) | (wanted > EPUF_LAST_YEAR)
        ]
        if outside.size:
            raise ValueError(
                f"EPUF annual earnings cover {EPUF_FIRST_YEAR}-"
                f"{EPUF_LAST_YEAR}; asked for {outside.tolist()}."
            )
        frame = frame[frame["year"].isin(wanted)].reset_index(drop=True)
    return frame
