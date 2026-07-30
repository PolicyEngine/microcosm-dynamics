"""Observed young-firm records from the Kauffman Firm Survey (KFS).

KFS follows 4,928 anonymized businesses founded in 2004 through 2011.
These are observed survey respondents, not synthetic firms.  They are
useful for descriptive young-firm trajectories and method development,
but they are not a current cross-section of all US employers and contain
no employee roster or observed link to SIPP/CPS workers.

Raw public-use files remain outside the repository.  By default this
reader expects the publisher's logically imputed long Stata file at
``~/PolicyEngine/kfs-data/logically-imputed/Public_Use_LI_Long.dta``.
Set ``POPULACE_DYNAMICS_KFS_DIR`` or pass an explicit path to override
that location.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import numpy as np
import pandas as pd

__all__ = ["KFS_YEARS", "kfs_profile", "read_kauffman_firms"]

KFS_YEARS: tuple[int, ...] = tuple(range(2004, 2012))

_DATA_DIR_ENV = "POPULACE_DYNAMICS_KFS_DIR"
_DEFAULT_DATA_DIR = Path(
    "~/PolicyEngine/kfs-data/logically-imputed"
).expanduser()
_LONG_FILENAME = "Public_Use_LI_Long.dta"

_REQUIRED_COLUMNS = (
    "mprid",
    "year",
    "status",
    "c5_num_employees",
    "c6_num_ft_employees",
    "c7_num_pt_employees",
    "naics_code",
    "cswgt_final",
)

_COUNT_INTERVAL_RE = re.compile(
    r"^(?P<exact>\d+)$|^(?P<lower>\d+)\+$|"
    r"^(?P<range_lower>\d+)-(?P<range_upper>\d+)$"
)
_MISSING_COUNT_CODES = frozenset({"", ".a"})


def _resolve_path(
    path: str | Path | None,
    data_dir: str | Path | None,
) -> Path:
    if path is not None:
        return Path(path).expanduser()
    if data_dir is not None:
        directory = Path(data_dir).expanduser()
    elif os.environ.get(_DATA_DIR_ENV):
        directory = Path(os.environ[_DATA_DIR_ENV]).expanduser()
    else:
        directory = _DEFAULT_DATA_DIR
    candidate = directory / _LONG_FILENAME
    if not candidate.exists():
        raise FileNotFoundError(
            f"No {_LONG_FILENAME} under {directory}; download the KFS "
            "logically imputed public-use archive and stage its contents "
            "outside git, or set POPULACE_DYNAMICS_KFS_DIR."
        )
    return candidate


def _count_intervals(
    values: pd.Series,
    *,
    column: str,
) -> pd.DataFrame:
    """Parse exact and top-/interval-coded employee counts."""
    text = values.fillna("").astype("string").str.strip()
    missing = text.isin(_MISSING_COUNT_CODES)
    parsed = text.where(~missing).str.extract(_COUNT_INTERVAL_RE)
    invalid = ~missing & parsed.isna().all(axis=1)
    if invalid.any():
        examples = sorted(text[invalid].unique().tolist())[:8]
        raise ValueError(
            f"KFS {column} contains unsupported count code(s) {examples}; "
            "refusing to invent interval semantics."
        )

    exact = pd.to_numeric(parsed["exact"], errors="coerce")
    lower = exact.fillna(
        pd.to_numeric(parsed["lower"], errors="coerce")
    ).fillna(pd.to_numeric(parsed["range_lower"], errors="coerce"))
    upper = exact.fillna(pd.to_numeric(parsed["range_upper"], errors="coerce"))
    bad_range = lower.notna() & upper.notna() & (upper < lower)
    if bad_range.any():
        raise ValueError(f"KFS {column} contains a decreasing count interval.")

    return pd.DataFrame(
        {
            f"{column}_raw": text.mask(missing, pd.NA),
            f"{column}_lower": lower.astype("Int64"),
            f"{column}_upper": upper.astype("Int64"),
            f"{column}_exact": exact.astype("Int64"),
        },
        index=values.index,
    )


def read_kauffman_firms(
    *,
    path: str | Path | None = None,
    data_dir: str | Path | None = None,
) -> pd.DataFrame:
    """Read the KFS logically imputed public-use firm-year file.

    Returns one row per anonymized KFS firm and survey year. Employee
    counts retain their publisher-supplied raw code and expose lower,
    upper, and exact values separately; open-ended and interval-coded
    counts are never silently replaced by midpoints.
    """
    source = _resolve_path(path, data_dir)
    if not source.exists():
        raise FileNotFoundError(
            f"KFS public-use file does not exist: {source}"
        )

    try:
        labels = pd.io.stata.StataReader(source).variable_labels()
    except (OSError, ValueError) as error:
        raise ValueError(f"KFS Stata file is unreadable: {source}") from error
    missing_columns = sorted(set(_REQUIRED_COLUMNS) - set(labels))
    if missing_columns:
        raise ValueError(
            f"KFS file is missing required columns {missing_columns}."
        )

    raw = pd.read_stata(
        source,
        columns=list(_REQUIRED_COLUMNS),
        convert_categoricals=False,
    )
    if raw.empty:
        raise ValueError("KFS public-use file contains no firm-year rows.")

    firm_number = pd.to_numeric(raw["mprid"], errors="coerce")
    bad_id = (
        firm_number.isna()
        | ~np.isfinite(firm_number)
        | (firm_number <= 0)
        | (firm_number % 1 != 0)
    )
    if bad_id.any():
        raise ValueError(
            "KFS mprid contains blank or non-integral identifiers."
        )
    firm_id = firm_number.astype("int64").astype("string")

    year_number = pd.to_numeric(raw["year"], errors="coerce")
    bad_year = (
        year_number.isna()
        | (year_number % 1 != 0)
        | ~year_number.isin(KFS_YEARS)
    )
    if bad_year.any():
        values = sorted(raw.loc[bad_year, "year"].astype(str).unique())[:8]
        raise ValueError(f"KFS year contains unsupported value(s) {values}.")
    year = year_number.astype("int16")

    keys = pd.DataFrame({"firm_id": firm_id, "year": year})
    if keys.duplicated().any():
        raise ValueError("KFS mprid/year is not unique.")

    status = raw["status"].fillna("").astype("string").str.strip()
    if status.eq("").any():
        raise ValueError("KFS status is blank on one or more firm-year rows.")

    industry = pd.to_numeric(raw["naics_code"], errors="coerce")
    bad_industry = industry.notna() & (
        ~np.isfinite(industry)
        | (industry % 1 != 0)
        | ~industry.between(11, 99)
    )
    if bad_industry.any():
        values = sorted(raw.loc[bad_industry, "naics_code"].unique())[:8]
        raise ValueError(f"KFS naics_code contains invalid value(s) {values}.")

    weight = pd.to_numeric(raw["cswgt_final"], errors="coerce")
    bad_weight = weight.isna() | ~np.isfinite(weight) | (weight < 0)
    if bad_weight.any():
        raise ValueError(
            "KFS cswgt_final contains missing, negative, or infinite weights."
        )

    count_frames = [
        _count_intervals(raw[source_name], column=output_name)
        for source_name, output_name in (
            ("c5_num_employees", "employees"),
            ("c6_num_ft_employees", "full_time_employees"),
            ("c7_num_pt_employees", "part_time_employees"),
        )
    ]
    result = pd.concat(
        [
            keys,
            pd.DataFrame(
                {
                    "status": status,
                    "industry_major": industry.astype("Int64"),
                    "cross_sectional_weight": weight.astype("float64"),
                }
            ),
            *count_frames,
        ],
        axis=1,
    )
    return result.reset_index(drop=True)


def kfs_profile(firms: pd.DataFrame) -> pd.DataFrame:
    """Return descriptive coverage statistics without altering input."""
    required = {
        "firm_id",
        "year",
        "status",
        "employees_lower",
        "employees_exact",
        "cross_sectional_weight",
    }
    missing = sorted(required - set(firms))
    if missing:
        raise ValueError(f"KFS profile input is missing columns {missing}.")
    if firms.duplicated(["firm_id", "year"]).any():
        raise ValueError(
            "KFS profile input contains duplicate firm-year rows."
        )

    rows = []
    for year, group in firms.groupby("year", sort=True):
        available = group["employees_lower"].notna()
        rows.append(
            {
                "year": int(year),
                "firm_records": int(len(group)),
                "complete_records": int(group["status"].eq("Complete").sum()),
                "employee_count_available": int(available.sum()),
                "zero_employee_records": int(
                    group["employees_exact"].eq(0).fillna(False).sum()
                ),
                "weighted_cohort_firms": float(
                    group["cross_sectional_weight"].sum()
                ),
            }
        )
    return pd.DataFrame(rows)
