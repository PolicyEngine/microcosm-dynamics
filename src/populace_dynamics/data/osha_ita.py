"""OSHA ITA establishment microdata — observed firm records (#192).

OSHA's Injury Tracking Application publishes every submitted Form 300A
summary as public establishment-level microdata: establishment name and
address, EIN, NAICS code, **annual average number of employees**, and
total hours worked. The employment field is an administrative headcount
reported by the employer, not a survey band, so — unlike CPS ``NOEMP``,
SIPP ``EJB1_EMPSIZE``, BDS ``fsize`` or QWI ``firmsize`` — it maps onto
the canonical IC2 bands **exactly**, with no straddling span.

**The reporting universe is hazard-selected, not a firm frame.**
Establishments submit only if they meet OSHA's size and industry
criteria (broadly, 250+ employees in recordkeeping industries, or
20-249 in designated higher-hazard industries). Measured on the 2025
file, employment concentrates in NAICS 62, 33, 23, 44, 32 and 49, while
finance, professional services and information are essentially absent.
Nothing here is a national firm population, and it must be reweighted
before it represents one.

**The employment field is dirty, and this reader will not silently
clean it.** On the 2025 file the raw ``annual_average_employees``
column sums to 321,889,014 — 237% of total US employment — because a
handful of filers report company-wide or plainly erroneous headcounts.
Two facts drive the design:

* an *objective* physical test (annual hours per employee cannot exceed
  8,760 = 24 x 365) removes only 1,996 records holding 235,875
  employees, so it barely moves the total;
* essentially all of the excess sits in about a dozen records: capping
  employment shifts the national total from 47.8M (cap 50,000) to
  62.9M (cap 1,000,000), a 32% swing driven by an arbitrary threshold.

A cap is therefore a **referee choice with a large, quantified effect
on every downstream margin**, not a cleaning detail. :func:`read_ita`
returns the raw counts with quality flags attached and bands nothing it
cannot band honestly; :func:`apply_quality_rule` applies a *named,
explicitly parameterised* rule so the choice appears in the artifact
rather than inside a loader. This mirrors ``firms/banding.BandSpan``,
which carries ambiguity explicitly rather than resolving it by hidden
convention.

**EIN is an establishment filer key here.** It is not the Form 5500
sponsor unit and not the SUSB enterprise: a multi-establishment firm
contributes several ITA rows under one EIN, and the joined
OSHA-vs-5500 subset agrees on the canonical band for only 66.3% of
matched EINs. See ``data/form5500.py`` for the unit warning.

Staging: raw OSHA files stay out of the repository, staged as
``ITA_300A_Summary_Data_{year}.csv`` under ``~/PolicyEngine/firm-data``,
overridable via ``POPULACE_DYNAMICS_FIRM_DIR``.
Provenance: ``data/external/firm_microdata_sources.md``.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..firms.banding import band_of_count
from .form5500 import FIRM_DATA_DIR_ENV, firm_data_dir

__all__ = [
    "ITA_COLUMNS",
    "MAX_ANNUAL_HOURS_PER_EMPLOYEE",
    "read_ita",
    "apply_quality_rule",
]

#: Physical upper bound on annual hours worked per employee
#: (24 x 365). A record above this is internally inconsistent
#: regardless of any size-cap choice.
MAX_ANNUAL_HOURS_PER_EMPLOYEE = 8_760

#: Columns read from the published ITA summary CSV. Verified against
#: the 2025 file header and the OSHA ITA Data Dictionary,
#: retrieved 2026-08-11.
ITA_COLUMNS = {
    "ein": "ein",
    "company_name": "company_name",
    "establishment_name": "establishment_name",
    "state": "state",
    "naics_code": "naics_code",
    "annual_average_employees": "annual_average_employees",
    "total_hours_worked": "total_hours_worked",
    "establishment_type": "establishment_type",
    "year_filing_for": "year_filing_for",
}

_STAGING_HINT = (
    "Stage the OSHA ITA summary file under ~/PolicyEngine/firm-data "
    f"(or {FIRM_DATA_DIR_ENV}); scripts/fetch_firm_microdata.py "
    "downloads it from the pinned URL."
)


def _normalise_ein(series: pd.Series) -> pd.Series:
    """Digits-only, zero-padded 9-character EIN (see ``form5500``)."""
    digits = series.astype("string").str.replace(r"\D", "", regex=True)
    padded = digits.str.zfill(9)
    return padded.where(digits.str.len().between(1, 9))


def read_ita(
    year: int, data_dir: Path | None = None, *, filename: str | None = None
) -> pd.DataFrame:
    """One row per submitted Form 300A establishment summary.

    Returns the **raw** employment counts plus three quality columns —
    no cleaning is applied:

    ``hours_per_employee``
        ``total_hours_worked / annual_average_employees``, NaN where
        either input is missing or employment is zero.
    ``hours_implausible``
        True where ``hours_per_employee`` exceeds
        :data:`MAX_ANNUAL_HOURS_PER_EMPLOYEE`. This is an objective
        internal-consistency failure, not a judgment call.
    ``bandable``
        True where employment is a whole number >= 1. The canonical
        bands partition ``[1, inf)``, so a zero-employment summary
        (4,468 of them on the 2025 file) has no band and must not be
        coerced into ``1-9``.

    Deliberately no ``canonical_band`` column: banding an uncleaned
    count would publish a size distribution that a dozen erroneous
    records dominate. Call :func:`apply_quality_rule` first.
    """
    root = data_dir if data_dir is not None else firm_data_dir()
    name = filename or f"ITA_300A_Summary_Data_{year}.csv"
    path = root / name
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. {_STAGING_HINT}")

    df = pd.read_csv(
        path,
        usecols=lambda c: c in ITA_COLUMNS,
        dtype={"ein": "string", "naics_code": "string"},
        low_memory=False,
    )
    missing = [c for c in ITA_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f"OSHA ITA file is missing columns {missing}; the published "
            "schema changed and the reader must be re-verified against "
            "the ITA Data Dictionary."
        )
    out = df.rename(columns=ITA_COLUMNS).copy()
    out["ein"] = _normalise_ein(out["ein"])
    out["naics_code"] = (
        out["naics_code"].astype("string").str.replace(r"\D", "", regex=True)
    )
    out["naics_sector"] = (
        out["naics_code"].where(out["naics_code"].str.len() >= 2).str[:2]
    )

    emp = pd.to_numeric(out["annual_average_employees"], errors="coerce")
    hours = pd.to_numeric(out["total_hours_worked"], errors="coerce")
    out["annual_average_employees"] = emp
    out["total_hours_worked"] = hours

    per = (hours / emp.where(emp > 0)).where(hours > 0)
    out["hours_per_employee"] = per
    out["hours_implausible"] = per > MAX_ANNUAL_HOURS_PER_EMPLOYEE
    out["bandable"] = emp.notna() & (emp >= 1) & (emp % 1 == 0)
    return out


def apply_quality_rule(
    df: pd.DataFrame,
    *,
    max_employees: int,
    drop_hours_implausible: bool = True,
) -> pd.DataFrame:
    """Apply a named establishment-employment quality rule.

    ``max_employees`` is **required and has no default on purpose**.
    It is the parameter that moves the national total by 32% (module
    docstring), so a default here would let a caller inherit a
    consequential referee choice without recording it. Whatever value
    an artifact uses must be written into that artifact.

    Returns the surviving rows with a ``canonical_band`` column
    attached. Rows that are unbandable, hours-implausible (unless
    ``drop_hours_implausible`` is False), or above ``max_employees``
    are dropped, and the count of each is recorded on
    ``df.attrs["quality_rule"]`` so a builder can report what it
    removed instead of silently shrinking its input.
    """
    if max_employees < 1:
        raise ValueError("max_employees must be >= 1.")
    for col in ("annual_average_employees", "bandable", "hours_implausible"):
        if col not in df.columns:
            raise ValueError(
                f"Frame lacks {col!r}; pass the output of read_ita()."
            )

    emp = df["annual_average_employees"]
    keep = df["bandable"].fillna(False)
    dropped_unbandable = int((~keep).sum())

    dropped_hours = 0
    if drop_hours_implausible:
        hours_bad = df["hours_implausible"].fillna(False)
        dropped_hours = int((keep & hours_bad).sum())
        keep = keep & ~hours_bad

    over = emp > max_employees
    dropped_over = int((keep & over).sum())
    keep = keep & ~over

    out = df[keep].copy()
    out["canonical_band"] = [
        band_of_count(int(n)).name for n in out["annual_average_employees"]
    ]
    out.attrs["quality_rule"] = {
        "max_employees": int(max_employees),
        "drop_hours_implausible": bool(drop_hours_implausible),
        "max_annual_hours_per_employee": MAX_ANNUAL_HOURS_PER_EMPLOYEE,
        "rows_in": int(len(df)),
        "rows_out": int(len(out)),
        "dropped_unbandable": dropped_unbandable,
        "dropped_hours_implausible": dropped_hours,
        "dropped_above_max_employees": dropped_over,
        "employment_out": int(out["annual_average_employees"].sum()),
    }
    return out
