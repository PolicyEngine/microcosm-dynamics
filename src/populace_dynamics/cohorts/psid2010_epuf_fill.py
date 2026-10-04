"""Learned EPUF career fills applied to a built PSID-2010 cohort (opt-in).

The PSID-2010 cohort's careers (:func:`populace_dynamics.cohorts.psid2010.
build_psid2010_cohort`) come from ``career.build_career``, which fills each
odd income year from 1997 with its neighbours' mean (provenance
``gap_imputed``) and counts nothing before ``max(1968, birth_year + 22)``.
:func:`fill_careers` replaces either rule with a fill learned from SSA's
Earnings Public-Use File and registered by ``gate_epuf_fill``
(``docs/amendments/gate_epuf_fill_registration_proposal.md``):

- every ``gap_imputed`` year becomes the odd fill's draw, with provenance
  :attr:`EPUFFillProvenance.GAP_EPUF_DRAWN`;
- every year from 1951 before the career start becomes the pre-career
  fill's draw, with provenance
  :attr:`EPUFFillProvenance.PRE_CAREER_EPUF_DONOR`.

The fills see what the gate's scoring path gives them:
- capped shares of the wage base for the career years the PSID recorded;
- every other year unknown, including pre-career years the PSID happened to
  record.

A drawn share becomes capped earnings at that year's wage base. Every other
career row is left exactly as built. Nothing here changes
``career.build_career``, ``cohorts.psid2010`` or any registered run; using
learned fills in a registered comparison needs its own registration.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd

__all__ = [
    "EPUFFillProvenance",
    "FilledCareers",
    "fill_careers",
]

FIRST_YEAR = 1951
_SEX_CODE = {"male": 1, "female": 2}


class EPUFFillProvenance(str, Enum):
    """Provenance of a career year filled by a learned EPUF fill."""

    GAP_EPUF_DRAWN = "gap_epuf_drawn"
    PRE_CAREER_EPUF_DONOR = "pre_career_epuf_donor"


@dataclass(frozen=True)
class FilledCareers:
    """Careers after the learned fills, with what produced them."""

    careers: pd.DataFrame
    fills: dict[str, str]
    seed: int
    content_sha256: str


def _wage_bases(years: np.ndarray) -> np.ndarray:
    from populace_dynamics.cola_track_a.statutory import (
        captured_ssa_parameters,
    )

    params = captured_ssa_parameters()
    return np.array([float(params.wage_base_for(int(y))) for y in years])


def _content_sha256(careers: pd.DataFrame) -> str:
    ordered = careers.sort_values(["person_id", "year"], kind="stable")
    return hashlib.sha256(
        ordered.to_csv(index=False, float_format="%.6f").encode()
    ).hexdigest()


def fill_careers(
    cohort: Any,
    *,
    odd_fill: Any | None = None,
    pre_fill: Any | None = None,
    seed: int,
    start_year: int | None = None,
) -> FilledCareers:
    """Replace the assembler's fill rules with learned fills.

    ``cohort`` needs ``persons`` (``person_id``, ``birth_year``, ``sex`` as
    ``"male"`` / ``"female"``) and ``careers`` (``person_id``, ``year``,
    ``earnings``, ``provenance``). Either fill may be None, which keeps that
    rule. ``start_year`` defaults to the latest career year.
    """

    persons = cohort.persons[["person_id", "birth_year", "sex"]].copy()
    careers = cohort.careers.copy()
    last = int(careers["year"].max()) if start_year is None else start_year
    years = np.arange(FIRST_YEAR, last + 1)
    caps = _wage_bases(years)
    person_ids = persons["person_id"].to_numpy(dtype=np.int64)
    row_of = {int(pid): i for i, pid in enumerate(person_ids)}
    birth = persons["birth_year"].to_numpy(dtype=np.int64)
    sex = persons["sex"].map(_SEX_CODE).fillna(3).to_numpy(dtype=np.int64)
    n = len(person_ids)

    shares = np.full((n, len(years)), np.nan)
    odd_mask = np.zeros((n, len(years)), dtype=bool)
    in_career = np.zeros((n, len(years)), dtype=bool)
    rows = careers["person_id"].map(row_of).to_numpy()
    if np.isnan(rows.astype(float)).any():
        raise ValueError("a career row's person is not in the cohort")
    columns = careers["year"].to_numpy(dtype=np.int64) - FIRST_YEAR
    inside = (columns >= 0) & (columns < len(years))
    rows, columns = rows[inside].astype(np.int64), columns[inside]
    provenance = careers["provenance"].astype(str).to_numpy()[inside]
    earnings = careers["earnings"].to_numpy(dtype=np.float64)[inside]
    in_career[rows, columns] = True
    observed = provenance == "observed"
    shares[rows[observed], columns[observed]] = np.minimum(
        np.maximum(earnings[observed], 0.0) / caps[columns[observed]], 1.0
    )
    gap = provenance == "gap_imputed"
    odd_mask[rows[gap], columns[gap]] = True
    start = np.maximum(1968, birth + 22)
    pre_mask = years[None, :] < start[:, None]
    given = np.where(odd_mask | pre_mask, np.nan, shares)

    def drawn(fill, mask):
        out = np.asarray(
            fill.fill(
                given.copy(), years, birth, sex, person_ids, mask.copy(), seed
            ),
            dtype=np.float64,
        )
        values = out[mask]
        if (
            not np.isfinite(values).all()
            or ((values < 0) | (values > 1)).any()
        ):
            raise ValueError("a learned fill returned an invalid share")
        return out

    result = careers.copy()
    names: dict[str, str] = {}
    if odd_fill is not None:
        out = drawn(odd_fill, odd_mask)
        cells = out[rows[gap], columns[gap]]
        values = np.where(
            cells >= 1.0, caps[columns[gap]], cells * caps[columns[gap]]
        )
        index = careers.index[inside][gap]
        result.loc[index, "earnings"] = values
        result.loc[index, "provenance"] = (
            EPUFFillProvenance.GAP_EPUF_DRAWN.value
        )
        names["odd"] = getattr(odd_fill, "name", type(odd_fill).__name__)
    if pre_fill is not None:
        out = drawn(pre_fill, pre_mask)
        pre_rows, pre_columns = np.nonzero(pre_mask & ~in_career)
        cells = out[pre_rows, pre_columns]
        added = pd.DataFrame(
            {
                "person_id": person_ids[pre_rows],
                "year": years[pre_columns],
                "earnings": np.where(
                    cells >= 1.0,
                    caps[pre_columns],
                    cells * caps[pre_columns],
                ),
                "provenance": EPUFFillProvenance.PRE_CAREER_EPUF_DONOR.value,
            }
        )
        result = pd.concat([added, result], ignore_index=True)
        names["pre"] = getattr(pre_fill, "name", type(pre_fill).__name__)
    result = result.sort_values(["person_id", "year"], kind="stable")
    result = result.reset_index(drop=True).astype(
        {
            "person_id": "int64",
            "year": "int64",
            "earnings": "float64",
            "provenance": "string",
        }
    )
    return FilledCareers(
        careers=result,
        fills=names,
        seed=int(seed),
        content_sha256=_content_sha256(result),
    )
