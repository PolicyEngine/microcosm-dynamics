"""Form 5500 plan-sponsor microdata — observed firm records (#192).

DOL/EBSA publishes every ERISA Form 5500 and Form 5500-SF filing as
public administrative microdata. Unlike SUSB/BDS/QWI/J2J — which are
published *aggregates* — this is one row per **filing**, carrying the
sponsor's EIN, principal business code, state, and participant counts.
It is therefore a source of observed firm records rather than firm
margins, and it is the frame the DOL's own PENSIM microsimulation has
used since 1997.

**Unit warning, and it is the load-bearing one.** The Form 5500
sponsor EIN is *not* the SUSB enterprise. A sponsor files per plan,
and a filer's EIN is frequently a parent entity covering several
operating subsidiaries. Measured on the committed 2023 files, 23,813
sponsors report 500+ active participants while SUSB 2022 counts only
21,041 firms with 500+ employees — more large sponsors than large
firms exist, which is only possible if the units differ. Any join to
an establishment-keyed source (``osha_ita``) or reconciliation to a
SUSB firm count must therefore treat the EIN as a *filer* identifier
and reconcile units explicitly. This module deliberately does not
pretend the EIN is a firm key.

**Active participants are a lower bound on employment.** ``Total
active participants`` counts plan-covered workers, not the sponsor's
workforce: an employee outside the plan's eligibility class is absent.
The count is used here as the observed size measure because it is the
only headcount on the form, and every consumer must carry the bound.

**Two forms, one universe.** Large plans file the main Form 5500;
plans under 100 participants generally file the short Form 5500-SF.
Reading only one silently truncates the firm-size distribution — the
SF file is where nearly all small sponsors live — so
:func:`read_sponsors` reads both and refuses to proceed on one alone
unless the caller opts in explicitly.

**Multiple filings per sponsor.** A sponsor with a 401(k) and a
welfare plan files twice, and the participant counts overlap rather
than add. :func:`read_sponsors` aggregates to the EIN by **maximum**,
never by sum; 122,173 of 828,330 sponsors on the 2023 files carry more
than one filing, so summing would materially inflate the large bands.

Staging: raw DOL files stay out of the repository, staged as
``f_5500_{year}_latest.csv`` and ``f_5500_sf_{year}_latest.csv`` under
``~/PolicyEngine/firm-data``, overridable via
``POPULACE_DYNAMICS_FIRM_DIR``. ``scripts/fetch_firm_microdata.py``
downloads them from pinned URLs and records each file's sha256.
Provenance: ``data/external/firm_microdata_sources.md``.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from ..firms.banding import band_of_count

__all__ = [
    "FIRM_DATA_DIR_ENV",
    "MAIN_COLUMNS",
    "SF_COLUMNS",
    "read_main_filings",
    "read_sf_filings",
    "read_sponsors",
]

FIRM_DATA_DIR_ENV = "POPULACE_DYNAMICS_FIRM_DIR"
_DEFAULT_DATA_DIR = Path("~/PolicyEngine/firm-data").expanduser()

_STAGING_HINT = (
    "Stage the DOL Form 5500 files under ~/PolicyEngine/firm-data (or "
    f"{FIRM_DATA_DIR_ENV}); scripts/fetch_firm_microdata.py downloads "
    "them from the pinned URLs."
)

#: Columns read from the main Form 5500 file. Names verified against
#: the DOL layout sidecar shipped inside the published zip
#: (``f_5500_{year}_latest_layout.txt``), retrieved 2026-08-11.
MAIN_COLUMNS = {
    "SPONS_DFE_EIN": "sponsor_ein",
    "BUSINESS_CODE": "business_code",
    "SPONS_DFE_LOC_US_STATE": "state",
    "TYPE_PLAN_ENTITY_CD": "plan_entity_code",
    "TOT_PARTCP_BOY_CNT": "total_participants",
    "TOT_ACTIVE_PARTCP_CNT": "active_participants",
}

#: Columns read from the Form 5500-SF file. The SF form carries its
#: own ``SF_``-prefixed names and reports active participants only at
#: beginning-of-year, so the two forms are *not* column-compatible and
#: are harmonised here rather than concatenated raw.
SF_COLUMNS = {
    "SF_SPONS_EIN": "sponsor_ein",
    "SF_BUSINESS_CODE": "business_code",
    "SF_SPONS_US_STATE": "state",
    "SF_TOT_ACT_PARTCP_BOY_CNT": "active_participants",
}


def firm_data_dir() -> Path:
    """Directory holding the staged raw DOL files."""
    env_value = os.environ.get(FIRM_DATA_DIR_ENV)
    if env_value:
        return Path(env_value).expanduser()
    return _DEFAULT_DATA_DIR


def _resolve(name: str, data_dir: Path | None) -> Path:
    root = data_dir if data_dir is not None else firm_data_dir()
    path = root / name
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. {_STAGING_HINT}")
    return path


def _normalise_ein(series: pd.Series) -> pd.Series:
    """Digits-only, zero-padded 9-character EIN.

    DOL emits the EIN both with and without a hyphen across vintages;
    an unnormalised join drops the hyphenated rows silently, which
    reads as genuine non-overlap rather than a format mismatch.
    """
    digits = series.astype("string").str.replace(r"\D", "", regex=True)
    padded = digits.str.zfill(9)
    return padded.where(digits.str.len().between(1, 9))


def _check_columns(path: Path, mapping: dict[str, str], form: str) -> None:
    """Validate the header before ``usecols`` can raise its own error.

    ``read_csv(usecols=...)`` raises a generic "Usecols do not match"
    ValueError that names neither the file nor the DOL layout, so the
    header is checked first and the failure names what to re-verify.
    """
    header = pd.read_csv(path, nrows=0)
    missing = [c for c in mapping if c not in header.columns]
    if missing:
        raise ValueError(
            f"Form {form} file {path.name} is missing columns {missing}; "
            "the DOL layout changed and the reader must be re-verified "
            "against the published layout sidecar."
        )


def _harmonise(
    df: pd.DataFrame, mapping: dict[str, str], form: str
) -> pd.DataFrame:
    out = df[list(mapping)].rename(columns=mapping).copy()
    out["sponsor_ein"] = _normalise_ein(out["sponsor_ein"])
    out["business_code"] = (
        out["business_code"]
        .astype("string")
        .str.replace(r"\D", "", regex=True)
        .str.zfill(6)
    )
    # A business code is a 6-digit NAICS-derived principal-activity
    # code; the sector is its first two digits. Codes that are not
    # 6 digits after padding are unusable rather than truncatable.
    good = out["business_code"].str.len() == 6
    out["naics_sector"] = out["business_code"].where(good).str[:2]
    for col in ("active_participants", "total_participants"):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    out["form"] = form or "5500"
    return out


def read_main_filings(year: int, data_dir: Path | None = None) -> pd.DataFrame:
    """One row per main Form 5500 filing for ``year``."""
    path = _resolve(f"f_5500_{year}_latest.csv", data_dir)
    _check_columns(path, MAIN_COLUMNS, "5500")
    df = pd.read_csv(
        path,
        usecols=list(MAIN_COLUMNS),
        dtype={"SPONS_DFE_EIN": "string", "BUSINESS_CODE": "string"},
        low_memory=False,
    )
    return _harmonise(df, MAIN_COLUMNS, "5500")


def read_sf_filings(year: int, data_dir: Path | None = None) -> pd.DataFrame:
    """One row per Form 5500-SF (short form) filing for ``year``."""
    path = _resolve(f"f_5500_sf_{year}_latest.csv", data_dir)
    _check_columns(path, SF_COLUMNS, "5500-SF")
    df = pd.read_csv(
        path,
        usecols=list(SF_COLUMNS),
        dtype={"SF_SPONS_EIN": "string", "SF_BUSINESS_CODE": "string"},
        low_memory=False,
    )
    return _harmonise(df, SF_COLUMNS, "5500-SF")


def read_sponsors(
    year: int,
    data_dir: Path | None = None,
    *,
    forms: tuple[str, ...] = ("5500", "5500-SF"),
) -> pd.DataFrame:
    """Observed sponsor records for ``year``, one row per sponsor EIN.

    Aggregates filings to the sponsor by **maximum** active
    participants (see the module docstring: counts across a sponsor's
    plans overlap and must never be summed), attaches the canonical
    IC2 firm-size band, and returns columns
    ``sponsor_ein, naics_sector, state, active_participants,
    canonical_band, filings``.

    ``forms`` exists so a caller can deliberately read one form in
    isolation; the default reads both because the SF file holds nearly
    every small sponsor and omitting it truncates the size
    distribution rather than merely shrinking the sample.

    Sponsors reporting zero active participants are **dropped**, not
    banded: the canonical bands partition ``[1, inf)``, and a zero is a
    plan with no covered workers, not a firm of size zero.
    """
    if not forms:
        raise ValueError("At least one of '5500' / '5500-SF' is required.")
    frames = []
    if "5500" in forms:
        frames.append(read_main_filings(year, data_dir))
    if "5500-SF" in forms:
        frames.append(read_sf_filings(year, data_dir))
    unknown = set(forms) - {"5500", "5500-SF"}
    if unknown:
        raise ValueError(f"Unknown Form 5500 variant(s) {sorted(unknown)}.")

    filings = pd.concat(frames, ignore_index=True)
    filings = filings.dropna(subset=["sponsor_ein"])

    grouped = filings.groupby("sponsor_ein", dropna=True)
    out = grouped.agg(
        active_participants=("active_participants", "max"),
        naics_sector=("naics_sector", "first"),
        state=("state", "first"),
        filings=("form", "size"),
    ).reset_index()

    out = out[out["active_participants"] >= 1].copy()
    out["active_participants"] = out["active_participants"].astype(int)
    out["canonical_band"] = [
        band_of_count(n).name for n in out["active_participants"]
    ]
    return out.reset_index(drop=True)
