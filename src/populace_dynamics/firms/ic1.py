"""IC1 job-spell contract — the seam between workstreams A and B (#192).

ADR 0003 froze IC1 on 2026-07-16 as "one tidy table, written by
workstream A, read by workstream B". This module is that table's
schema, its validator, and the adapter from the SIPP spell reader's
output. It exists so the two sides meet at a checked contract rather
than at a convention: ``firms/assignment.py`` consumes IC1, and
anything that does not conform fails here rather than producing a
plausible-looking roster from mis-shaped input.

**The calibration universe is narrower than the schema.** ADR 0003
makes ``class_of_worker`` load-bearing: SUSB excludes government
establishments, NAICS 92, crop/animal production and non-employers,
and QWI in-scope jobs are non-federal. Government, self-employed and
unpaid-family spells are therefore **out of the SUSB/QWI calibration
universe**, and self-employed spells have **no defined firm-size
band** at all. :func:`calibration_universe` applies that rule
explicitly so a caller cannot drift into calibrating against jobs the
targets never counted.

**IC1 carries no geography, by design.** QWI/J2J targets are
state-level, but the state of a spell is the host person's state at
``start_period``, joined on ``person_id`` from the person table. The
join key lives on the person table, not here.

**IC1 carries no hours, and that deferral is live.** The frozen
contract has no hours column, so IC1 cannot serve monthly-hours
consumers — the registered example is SNAP ABAWD compliance, whose
80-hours-per-month test needs month-resolved hours. A ``hours_band``
column is the first scheduled IC1 amendment, by joint PR, once the
phase-1 spell imputation establishes what granularity SIPP supports.
:func:`validate` rejects a frame that smuggles in an hours column,
because adding one silently would be an unratified contract change.
"""

from __future__ import annotations

import pandas as pd

from .banding import CanonicalBand

__all__ = [
    "IC1_COLUMNS",
    "CLASS_OF_WORKER",
    "CALIBRATION_CLASSES",
    "NO_FIRM_SIZE_CLASSES",
    "OPEN_SPELL_SENTINEL",
    "validate",
    "from_sipp_spells",
    "calibration_universe",
]

#: The frozen IC1 column list, in contract order (ADR 0003).
IC1_COLUMNS = (
    "person_id",
    "spell_id",
    "start_period",
    "end_period",
    "industry",
    "firm_size_band",
    "class_of_worker",
    "earnings_share",
    "primary_job",
)

#: The five permitted ``class_of_worker`` values.
CLASS_OF_WORKER = frozenset(
    {
        "private",
        "federal",
        "state_local_government",
        "self_employed",
        "unpaid_family",
    }
)

#: Classes inside the SUSB/QWI calibration universe. Government,
#: self-employed and unpaid-family jobs are outside it (ADR 0003).
CALIBRATION_CLASSES = frozenset({"private"})

#: Classes for which a firm-size band is undefined, not merely missing.
NO_FIRM_SIZE_CLASSES = frozenset({"self_employed", "unpaid_family"})

#: ``end_period`` value marking a spell still open at panel end.
OPEN_SPELL_SENTINEL = pd.NaT

_BAND_NAMES = frozenset(band.name for band in CanonicalBand)


def validate(spells: pd.DataFrame, *, strict_universe: bool = True) -> None:
    """Raise unless ``spells`` conforms to the frozen IC1 contract.

    Checks the column set exactly, not as a subset: an extra column is
    a contract change and must go through a joint PR. In particular an
    hours column is rejected by name, because IC1's hours deferral is
    explicit and a consumer that found one would reasonably assume it
    was ratified.

    ``strict_universe`` additionally enforces ADR 0003's semantic
    rules: ``person_id`` is an opaque string (the ASEC ``PERIDNUM`` is
    22 digits, so int64 overflows and float64 merges distinct people),
    ``spell_id`` is unique within person, and self-employed and
    unpaid-family spells carry no firm-size band.
    """
    missing = [c for c in IC1_COLUMNS if c not in spells.columns]
    if missing:
        raise ValueError(f"IC1 frame is missing columns {missing}.")
    extra = [c for c in spells.columns if c not in IC1_COLUMNS]
    if extra:
        hours = [c for c in extra if "hour" in c.lower()]
        if hours:
            raise ValueError(
                f"IC1 frame carries hours column(s) {hours}. IC1 as frozen "
                "has no hours column; adding one is the first scheduled "
                "amendment and requires a joint PR (ADR 0003). A consumer "
                "finding this column would assume it was ratified."
            )
        raise ValueError(
            f"IC1 frame carries unregistered columns {extra}; the contract "
            "is an exact column set, not a minimum."
        )

    bad_class = set(spells["class_of_worker"].dropna()) - CLASS_OF_WORKER
    if bad_class:
        raise ValueError(
            f"Unknown class_of_worker values {sorted(bad_class)}."
        )

    bands = set(spells["firm_size_band"].dropna())
    unknown_bands = bands - _BAND_NAMES
    if unknown_bands:
        raise ValueError(
            f"firm_size_band values {sorted(unknown_bands)} are not canonical "
            "IC2 bands."
        )

    if not strict_universe:
        return

    if not pd.api.types.is_string_dtype(spells["person_id"]):
        raise ValueError(
            "person_id must be an opaque string key. The ASEC PERIDNUM is "
            "22 digits: int64 overflows and float64 rounds distinct persons "
            "together (#194 review)."
        )
    if spells.duplicated(["person_id", "spell_id"]).any():
        raise ValueError("spell_id must be unique within person_id.")

    undefined = spells["class_of_worker"].isin(NO_FIRM_SIZE_CLASSES)
    if spells.loc[undefined, "firm_size_band"].notna().any():
        raise ValueError(
            "Self-employed and unpaid-family spells have no defined "
            "firm-size band (ADR 0003); a band here is a category error, "
            "not a value."
        )

    shares = spells["earnings_share"].dropna()
    if len(shares) and not shares.between(0.0, 1.0).all():
        raise ValueError("earnings_share must lie in [0, 1].")


def from_sipp_spells(
    spells: pd.DataFrame, *, band_column: str = "estab_size_band"
) -> pd.DataFrame:
    """Adapt ``sipp_jobs.job_spells`` output to the IC1 contract.

    The SIPP reader deliberately names its size column
    ``estab_size_band``, not ``canonical_band``: SIPP 2014+ measures
    **establishment** size at the worker's location, while IC2's
    canonical variable means administrative *enterprise* size
    (``firms/banding.py``). This adapter therefore performs a named,
    lossy promotion rather than a rename, and records it on
    ``attrs["size_concept"]`` so a downstream consumer can see that the
    band it received is an establishment-size proxy.

    That promotion is the single most consequential approximation on
    the person side and it is not hidden behind a column name: a
    multi-establishment firm's worker reports their location's
    headcount, biasing the spell toward smaller bands.
    """
    if band_column not in spells.columns:
        raise ValueError(
            f"SIPP spells lack {band_column!r}; pass the output of "
            "sipp_jobs.job_spells()."
        )
    out = pd.DataFrame(
        {
            "person_id": spells["person_id"].astype("string"),
            "spell_id": spells.get(
                "spell_id", pd.RangeIndex(len(spells))
            ).astype("int64"),
            "start_period": spells.get("start_month", spells.get("start")),
            "end_period": spells.get("end_month", spells.get("end")),
            "industry": spells["industry"].astype("string"),
            "firm_size_band": spells[band_column],
            "class_of_worker": spells["class_of_worker"],
            "earnings_share": pd.to_numeric(
                spells.get("earnings_share"), errors="coerce"
            ),
            "primary_job": spells.get("top_earner", False).astype(bool),
        }
    )
    # A band on a self-employed spell is a category error; the SIPP
    # reader can carry one through from the raw slot, so it is cleared
    # here rather than left to trip the validator.
    undefined = out["class_of_worker"].isin(NO_FIRM_SIZE_CLASSES)
    out.loc[undefined, "firm_size_band"] = pd.NA
    out.attrs["size_concept"] = (
        "establishment size (SIPP EJB1_EMPSIZE) promoted to the IC2 "
        "enterprise-size band; a proxy, biased toward smaller bands for "
        "multi-establishment firms"
    )
    return out[list(IC1_COLUMNS)]


def calibration_universe(spells: pd.DataFrame) -> pd.DataFrame:
    """Restrict IC1 spells to the SUSB/QWI calibration universe.

    Keeps private-sector spells only. Government (federal and
    state-local), self-employed and unpaid-family spells are dropped
    because the targets never counted them: SUSB excludes government
    establishments, NAICS 92, crop/animal production and non-employers,
    and QWI in-scope jobs are non-federal (ADR 0003, #192 review point
    1). Calibrating against jobs the targets exclude would bias every
    margin by the size of the excluded share.

    The dropped counts are recorded on ``attrs`` so the exclusion is
    visible in any artifact built from the result.
    """
    validate(spells, strict_universe=False)
    keep = spells["class_of_worker"].isin(CALIBRATION_CLASSES)
    out = spells[keep].reset_index(drop=True).copy()
    dropped = spells.loc[~keep, "class_of_worker"].value_counts()
    out.attrs["excluded_from_calibration"] = {
        str(k): int(v) for k, v in dropped.items()
    }
    out.attrs["excluded_total"] = int((~keep).sum())
    return out
