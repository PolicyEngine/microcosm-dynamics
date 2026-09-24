"""F17 component diagnostics for Track U: Social Security, SSI and WEALTH1.

Plan ``critical-path-uniform-cut-20260923.md`` field F17 lists two kinds
of diagnostic row.  The official-concept poverty rate involves the
threshold and runs only inside a registered run
(:func:`populace_dynamics.uniform_cut_track_u.runner.
official_concept_rates`).  The other kind -- PSID Social Security, SSI
and WEALTH1 summaries for the age-67 population against published
aggregates -- is a component aggregate with no threshold, which plan
section 8 allows before registration.  This module computes that kind.
It imports neither the income concept
(:mod:`populace_dynamics.estimates.adjusted_poverty`) nor the tabulation,
computes no annuity, threshold, poverty status or rate, and reads the
SSI parameters through its own hash pin.

Population: the observations of an age-67 cohort
(:func:`populace_dynamics.cohorts.age67.build_age67_cohort`, row U0 by
default), weighted by their observation weights, each merged with its
family unit's income (every wave) and WEALTH1 (waves with staged wealth).

Summaries per income year:

* **Social Security.**  A member's own amount is the family file's head
  or wife amount by the member's role; an OFUM's own amount is not
  identified (the family file reports one OFUM total), so OFUM members
  enter only the family-level share.  Reported: the weighted share of
  head and wife members with their own Social Security, the weighted mean
  own annual amount among them and its twelfth, and the weighted share of
  all members whose family unit reports any Social Security.
* **SSI.**  The weighted share of head and wife members reporting their
  own SSI and of all members whose family reports any; the weighted mean
  own annual SSI among recipients; and, against the federal benefit rate
  in force on January 1 of the income year (the committed capture,
  :data:`SSI_PARAMETERS_PATH`), the number and weighted share of head and
  wife SSI units reporting more than twelve times the federal maximum for
  their unit (individual, or couple when both receive SSI).  An amount
  above the federal maximum is consistent with a state supplement or a
  reporting difference; this module does not say which.
* **WEALTH1.**  Weighted quantiles (the smallest value whose cumulative
  weight share reaches the level; :func:`weighted_quantile`) at 10, 25,
  50, 75 and 90 percent, and the weighted shares at or below zero, below
  zero and imputed (accuracy code 1).

Published aggregates (committed sources only; nothing downloaded):

* Social Security: SSA, *Annual Statistical Supplement, 2025*, Table
  5.A4 ("Number of beneficiaries and total monthly benefits, by trust
  fund and type of benefit, December 1940-2024, selected years"), read
  from the committed, hash-verified snapshot
  ``data/external/snapshots/ssa_level_anchors_vintage1/
  supplement2025_5a.html``.  For December of the year before and of the
  income year it gives the number of retired-worker beneficiaries and
  their total monthly benefits; the average is their quotient (the
  division is this module's, not a published cell).  Concept
  differences, all unadjusted: every age against the members at 66-68;
  retired workers only against any benefit type (spouse and widow(er)
  benefits included); December monthly benefits against a calendar-year
  total divided by twelve; SSA's benefits in current-payment status
  against a self-report possibly net of the Medicare premium.
* SSI: only the federal benefit rate above; no published SSI recipient
  or payment aggregate is committed or saved.
* WEALTH1: none.  No Survey of Consumer Finances table (the plan's
  comparator, wealth percentiles by age) is committed or saved, so the
  WEALTH1 summaries are not compared; capturing one is a gap.
"""

from __future__ import annotations

import hashlib
import html
import json
import math
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.cohorts import age67
from populace_dynamics.data import family_income

__all__ = [
    "QUANTILES",
    "SSA_5A_SNAPSHOT_PATH",
    "SSA_5A_SNAPSHOT_SHA256",
    "SSA_5A_URL",
    "SSI_PARAMETERS_PATH",
    "SSI_PARAMETERS_SHA256",
    "component_diagnostics",
    "component_rows",
    "federal_benefit_rates",
    "institution_record_counts",
    "social_security_summary",
    "ssa_table_5a4",
    "ssi_summary",
    "wealth1_summary",
    "weighted_quantile",
]

_ROOT = Path(__file__).resolve().parents[3]
_EXTERNAL = _ROOT / "data" / "external"
#: The committed SSI capture; the same pin as
#: ``adjusted_poverty.SSI_PARAMETERS_SHA256`` (a test holds them equal),
#: kept here so this module need not import the income concept.
SSI_PARAMETERS_PATH = _EXTERNAL / "track_u_ssi_parameters.json"
SSI_PARAMETERS_SHA256 = (
    "79e641a10d95afba81c8d831852fb52ef0a801e7175e06df17e6cc7cc3e3c523"
)
#: The committed snapshot of the SSA Annual Statistical Supplement, 2025,
#: section 5.A (captured 2026-07-27 for the SSA level anchors; its
#: SHA-256 is in the snapshot directory's capture manifest).
SSA_5A_SNAPSHOT_PATH = (
    _EXTERNAL
    / "snapshots"
    / "ssa_level_anchors_vintage1"
    / "supplement2025_5a.html"
)
SSA_5A_SNAPSHOT_SHA256 = (
    "d61e9484d271aec0126d8897a780668adf55f5d86f5b440a0f69782de968aa8e"
)
SSA_5A_URL = (
    "https://www.ssa.gov/policy/docs/statcomps/supplement/2025/5a.html"
)
_TABLE_5A4_CAPTION = (
    "Number of beneficiaries and total monthly benefits, by trust fund and "
    "type of benefit, December"
)
_TABLE_5A4_COLUMNS = (
    "Year",
    "Total",
    "OASI Trust Fund",
    "DI Trust Fund",
    "Retired workers",
    "Disabled workers",
    "Wives and husbands",
    "Children",
    "Widowed mothers and fathers",
    "Widow(er)s",
    "Parents of deceased workers",
    "Special age-72 beneficiaries",
)
#: Table 5.A4 columns read, by key.
_TABLE_5A4_READ = {
    "retired_workers": "Retired workers",
    "wives_and_husbands": "Wives and husbands",
    "widowers": "Widow(er)s",
}
QUANTILES: tuple[float, ...] = (0.10, 0.25, 0.50, 0.75, 0.90)
_MONTHS = 12


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# =========================================================================
# Published and committed sources
# =========================================================================
def federal_benefit_rates(
    path: Path = SSI_PARAMETERS_PATH,
    *,
    expected_sha256: str = SSI_PARAMETERS_SHA256,
) -> dict[str, Any]:
    """The committed federal benefit rates (monthly), hash-verified."""

    observed = _sha256(path)
    if observed != expected_sha256:
        raise ValueError(
            f"{path} sha256 {observed} != pinned {expected_sha256}"
        )
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rates = data["federal_benefit_rate_monthly"]
    return {
        "individual": {
            int(y): float(v) for y, v in rates["individual"].items()
        },
        "couple": {int(y): float(v) for y, v in rates["couple"].items()},
        "rule": data["source"]["rule"],
        "source": {
            "file": (
                str(Path(path).relative_to(_ROOT))
                if Path(path).is_relative_to(_ROOT)
                else str(path)
            ),
            "sha256": observed,
            "policyengine_us_revision": data["source"][
                "policyengine_us_revision"
            ],
            "references": data["source"]["references"]["fbr_individual"],
        },
    }


def _cells(row: str) -> list[str]:
    cells = re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", row, re.S)
    return [
        " ".join(html.unescape(re.sub(r"<[^>]+>", "", c)).split())
        for c in cells
    ]


def ssa_table_5a4(
    years: Iterable[int],
    path: Path = SSA_5A_SNAPSHOT_PATH,
    *,
    expected_sha256: str = SSA_5A_SNAPSHOT_SHA256,
) -> dict[int, dict[str, Any]]:
    """Retired-worker, spouse and widow(er) cells of Table 5.A4 by year.

    Returns, per December ``year``, ``{key: {"number", "total_monthly_
    thousands", "average_monthly"}}`` for the columns of
    :data:`_TABLE_5A4_READ`, plus ``aged_types_combined`` (their summed
    totals over their summed numbers).  ``number`` and ``total_monthly_
    thousands`` are the published cells ("Number" and "Total monthly
    benefits (thousands of dollars)" panels) as integers; the averages are
    divisions made here.  The layout is checked by its printed caption and
    column headers; any other layout is refused.
    """

    observed = _sha256(path)
    if observed != expected_sha256:
        raise ValueError(
            f"{path} sha256 {observed} != pinned {expected_sha256}"
        )
    text = Path(path).read_text(encoding="utf-8")
    start = text.find("Table&nbsp;5.A4")
    if start < 0:
        raise ValueError("Table 5.A4 not found in the snapshot")
    end = text.find("</table>", start)
    table = text[start:end]
    caption = " ".join(
        html.unescape(re.sub(r"<[^>]+>", " ", table[:600])).split()
    )
    if _TABLE_5A4_CAPTION not in caption:
        raise ValueError(f"unexpected Table 5.A4 caption: {caption[:200]!r}")
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S)
    headers = [cell for row in rows[:2] for cell in _cells(row)]
    expected = [h for h in _TABLE_5A4_COLUMNS if h != "OASDI"]
    flat = [h for h in headers if h != "OASDI"]
    if sorted(flat) != sorted(expected):
        raise ValueError(f"unexpected Table 5.A4 headers {headers}")
    columns = list(_TABLE_5A4_COLUMNS)
    panels: dict[str, dict[int, list[str]]] = {}
    panel = None
    for row in rows[2:]:
        cells = _cells(row)
        if len(cells) == 2 and cells[0] == "":
            panel = cells[1]
            panels[panel] = {}
            continue
        if panel is None or not cells or not cells[0].isdigit():
            continue
        if len(cells) != len(columns):
            raise ValueError(f"row {cells[0]} has {len(cells)} cells")
        panels[panel][int(cells[0])] = cells
    number = panels.get("Number")
    totals = panels.get("Total monthly benefits (thousands of dollars)")
    if number is None or totals is None:
        raise ValueError(f"unexpected Table 5.A4 panels {sorted(panels)}")
    out: dict[int, dict[str, Any]] = {}
    for year in sorted({int(y) for y in years}):
        if year not in number or year not in totals:
            raise ValueError(f"Table 5.A4 has no December {year} row")
        entry: dict[str, Any] = {}
        sum_number = 0
        sum_total = 0
        for key, header in _TABLE_5A4_READ.items():
            index = columns.index(header)
            count = int(number[year][index].replace(",", ""))
            total = int(totals[year][index].replace(",", ""))
            sum_number += count
            sum_total += total
            entry[key] = {
                "number": count,
                "total_monthly_thousands": total,
                "average_monthly": 1000.0 * total / count,
            }
        entry["aged_types_combined"] = {
            "number": sum_number,
            "total_monthly_thousands": sum_total,
            "average_monthly": 1000.0 * sum_total / sum_number,
        }
        out[year] = entry
    return out


# =========================================================================
# Rows and summaries
# =========================================================================
def component_rows(
    cohort: age67.Age67Cohort, inputs: age67.Age67Inputs
) -> pd.DataFrame:
    """One row per observation with its Social Security, SSI and WEALTH1.

    Columns: ``observation_id``, ``person_id``, ``birth_year``,
    ``income_year``, ``wave``, ``weight``, ``member_role``, ``sex``,
    ``married``, ``own_identified`` (head or wife member), ``own_ss``,
    ``family_ss``, ``own_ssi``, ``head_ssi``, ``wife_ssi``, ``ofum_ssi``,
    ``family_ssi``, ``wealth_available``, ``wealth1`` and ``wealth1_acc``
    (NaN where the wave has no staged wealth).  No income concept is
    formed: the amounts are the family file's items as read.
    """

    obs = cohort.observations
    frames = []
    for wave, rows in obs.groupby("wave", sort=True):
        income = inputs.family_income[int(wave)]
        items = [
            "interview",
            *family_income.SOCIAL_SECURITY_CONCEPTS,
            *family_income.SSI_CONCEPTS,
        ]
        merged = rows.merge(
            income[items], on="interview", how="left", validate="many_to_one"
        )
        wealth = inputs.family_wealth.get(int(wave))
        if wealth is not None:
            merged = merged.merge(
                wealth[["interview", "wealth1", "wealth1_acc"]],
                on="interview",
                how="left",
                validate="many_to_one",
            )
        else:
            merged["wealth1"] = np.nan
            merged["wealth1_acc"] = np.nan
        frames.append(merged)
    if not frames:
        raise ValueError("the cohort has no observations")
    data = pd.concat(frames, ignore_index=True)
    if data["head_ss"].isna().any():
        raise ValueError("an observation has no family-file income record")
    role = data["member_role"].astype(str)
    own_identified = role.isin(["head", "wife"])
    own_ss = np.where(
        role.eq("head"),
        data["head_ss"],
        np.where(role.eq("wife"), data["wife_ss"], np.nan),
    )
    own_ssi = np.where(
        role.eq("head"),
        data["head_ssi"],
        np.where(role.eq("wife"), data["wife_ssi"], np.nan),
    )
    out = pd.DataFrame(
        {
            "observation_id": data["observation_id"],
            "person_id": data["person_id"],
            "birth_year": data["birth_year"].astype("int64"),
            "income_year": data["income_year"].astype("int64"),
            "wave": data["wave"].astype("int64"),
            "weight": data["weight"].astype("float64"),
            "member_role": role,
            "sex": data["sex"].astype(str),
            "married": data["married"].astype(bool),
            "own_identified": own_identified.to_numpy(),
            "own_ss": own_ss.astype("float64"),
            "family_ss": data[list(family_income.SOCIAL_SECURITY_CONCEPTS)]
            .sum(axis=1)
            .astype("float64"),
            "own_ssi": own_ssi.astype("float64"),
            "head_ssi": data["head_ssi"].astype("float64"),
            "wife_ssi": data["wife_ssi"].astype("float64"),
            "ofum_ssi": data["ofum_ssi"].astype("float64"),
            "family_ssi": data[list(family_income.SSI_CONCEPTS)]
            .sum(axis=1)
            .astype("float64"),
            "wealth_available": data["wealth1"].notna().to_numpy(),
            "wealth1": data["wealth1"].astype("float64"),
            "wealth1_acc": data["wealth1_acc"].astype("float64"),
        }
    )
    return out


def weighted_quantile(
    values: Iterable[float], weights: Iterable[float], level: float
) -> float:
    """The smallest value whose cumulative weight share reaches ``level``.

    Values are sorted ascending; the answer is the first value ``v_k``
    with ``sum_{j<=k} w_j >= level * sum w`` (no interpolation).
    """

    values = np.asarray(list(values), dtype=np.float64)
    weights = np.asarray(list(weights), dtype=np.float64)
    if values.size == 0 or values.size != weights.size:
        raise ValueError("weighted_quantile needs matching, non-empty inputs")
    if not 0.0 < float(level) <= 1.0:
        raise ValueError("level must lie in (0, 1]")
    if (weights < 0).any() or weights.sum() <= 0:
        raise ValueError("weights must be >= 0 with a positive total")
    order = np.argsort(values, kind="stable")
    cumulative = np.cumsum(weights[order])
    target = float(level) * cumulative[-1]
    index = int(np.searchsorted(cumulative, target - 1e-9 * cumulative[-1]))
    return float(values[order][min(index, values.size - 1)])


def _share(mask: np.ndarray, weights: np.ndarray) -> float | None:
    total = float(weights.sum())
    return None if total <= 0 else float(weights[mask].sum() / total)


def _mean(values: np.ndarray, weights: np.ndarray) -> float | None:
    total = float(weights.sum())
    return None if total <= 0 else float(np.sum(values * weights) / total)


def _by_year(rows: pd.DataFrame) -> dict[int, pd.DataFrame]:
    return {
        int(year): part.reset_index(drop=True)
        for year, part in rows.groupby("income_year", sort=True)
    }


def social_security_summary(
    rows: pd.DataFrame,
    published: Mapping[int, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Weighted Social Security summaries per income year (see module).

    ``published`` is :func:`ssa_table_5a4` output covering December of
    each income year and the year before; when given, each year carries
    the PSID monthly mean over each December average.
    """

    out: dict[str, Any] = {}
    for year, part in _by_year(rows).items():
        w = part["weight"].to_numpy()
        own = part["own_identified"].to_numpy()
        own_ss = part["own_ss"].to_numpy()
        recipient = own & (np.nan_to_num(own_ss) > 0)
        entry: dict[str, Any] = {
            "n_observations": int(len(part)),
            "n_own_identified": int(own.sum()),
            "n_own_recipients": int(recipient.sum()),
            "weight_total": float(w.sum()),
            "own_receipt_share": _share(recipient[own], w[own]),
            "own_mean_annual_among_recipients": _mean(
                own_ss[recipient], w[recipient]
            ),
            "family_receipt_share": _share(
                part["family_ss"].to_numpy() > 0, w
            ),
        }
        annual = entry["own_mean_annual_among_recipients"]
        entry["own_mean_monthly_among_recipients"] = (
            None if annual is None else annual / _MONTHS
        )
        if published is not None:
            comparisons = {}
            for label, december in (
                ("december_prior_year", year - 1),
                ("december_income_year", year),
            ):
                cells = published[december]
                comparisons[label] = {
                    "december": december,
                    "ssa_retired_worker_average_monthly": cells[
                        "retired_workers"
                    ]["average_monthly"],
                    "ssa_aged_types_average_monthly": cells[
                        "aged_types_combined"
                    ]["average_monthly"],
                    "psid_over_ssa_retired_worker": (
                        None
                        if entry["own_mean_monthly_among_recipients"] is None
                        else entry["own_mean_monthly_among_recipients"]
                        / cells["retired_workers"]["average_monthly"]
                    ),
                    "psid_over_ssa_aged_types": (
                        None
                        if entry["own_mean_monthly_among_recipients"] is None
                        else entry["own_mean_monthly_among_recipients"]
                        / cells["aged_types_combined"]["average_monthly"]
                    ),
                }
            entry["published"] = comparisons
        out[str(year)] = entry
    return out


def ssi_summary(
    rows: pd.DataFrame, rates: Mapping[str, Mapping[int, float]]
) -> dict[str, Any]:
    """Weighted SSI summaries per income year against the federal maximum.

    A head/wife SSI unit is a couple when both the head and the wife
    report SSI (its combined SSI is set against twelve times the couple
    rate), else an individual (the member's own SSI against twelve times
    the individual rate).  Rates are those in force on January 1 of the
    income year.
    """

    out: dict[str, Any] = {}
    for year, part in _by_year(rows).items():
        w = part["weight"].to_numpy()
        own = part["own_identified"].to_numpy()
        own_ssi = np.nan_to_num(part["own_ssi"].to_numpy())
        recipient = own & (own_ssi > 0)
        couple = (part["head_ssi"].to_numpy() > 0) & (
            part["wife_ssi"].to_numpy() > 0
        )
        unit_ssi = np.where(
            couple,
            part["head_ssi"].to_numpy() + part["wife_ssi"].to_numpy(),
            own_ssi,
        )
        maximum = np.where(
            couple,
            _MONTHS * float(rates["couple"][year]),
            _MONTHS * float(rates["individual"][year]),
        )
        above = recipient & (unit_ssi > maximum)
        out[str(year)] = {
            "n_observations": int(len(part)),
            "n_own_recipients": int(recipient.sum()),
            "own_receipt_share": _share(recipient[own], w[own]),
            "family_receipt_share": _share(
                part["family_ssi"].to_numpy() > 0, w
            ),
            "own_mean_annual_among_recipients": _mean(
                own_ssi[recipient], w[recipient]
            ),
            "federal_maximum_annual": {
                "individual": _MONTHS * float(rates["individual"][year]),
                "couple": _MONTHS * float(rates["couple"][year]),
            },
            "n_recipients_above_federal_maximum": int(above.sum()),
            "recipient_share_above_federal_maximum": _share(
                above[recipient], w[recipient]
            ),
        }
    return out


def wealth1_summary(rows: pd.DataFrame) -> dict[str, Any]:
    """Weighted WEALTH1 quantiles and shares per income year with wealth."""

    out: dict[str, Any] = {}
    available = rows[rows["wealth_available"]]
    for year, part in _by_year(available).items():
        w = part["weight"].to_numpy()
        wealth = part["wealth1"].to_numpy()
        entry: dict[str, Any] = {
            "n_observations": int(len(part)),
            "weight_total": float(w.sum()),
            "quantiles": (
                {
                    f"p{int(round(100 * q))}": weighted_quantile(wealth, w, q)
                    for q in QUANTILES
                }
                if w.sum() > 0
                else None
            ),
            "share_at_or_below_zero": _share(wealth <= 0, w),
            "share_below_zero": _share(wealth < 0, w),
            "share_imputed": _share(part["wealth1_acc"].to_numpy() == 1, w),
        }
        out[str(year)] = entry
    return out


def institution_record_counts(inputs: age67.Age67Inputs) -> dict[str, Any]:
    """Counts only: ``# IN FU`` against the individual records per wave.

    For each wave: the families whose ``# IN FU`` equals their number of
    in-family individual records (sequence 1-20), the institution records
    (51-59) attached to a responding family, and among the families with
    at least one such record, how many have ``# IN FU`` equal to the
    in-family count alone and how many equal to the in-family count plus
    the institution records.  This checks the reading of the unregistered
    ``family_of_record`` institution rule (row U-inst, withdrawn in
    u1-draft-5) that ``# IN FU`` does not count institutionalized
    members.
    """

    out: dict[str, Any] = {}
    for wave in age67.WAVES:
        anchor = inputs.anchors[wave]
        income = inputs.family_income[wave].set_index("interview")["fu_size"]
        in_family = (
            anchor[anchor["sequence"].between(1, 20)]
            .groupby("interview")
            .size()
        )
        institution = (
            anchor[anchor["sequence"].between(51, 59)]
            .groupby("interview")
            .size()
        )
        counts = pd.DataFrame({"fu_size": income})
        counts["in_family"] = in_family.reindex(counts.index).fillna(0)
        counts["institution"] = institution.reindex(counts.index).fillna(0)
        attached = counts[counts["institution"] > 0]
        out[str(wave)] = {
            "n_families": int(len(counts)),
            "n_fu_size_equals_in_family_records": int(
                (counts["fu_size"] == counts["in_family"]).sum()
            ),
            "n_institution_records": int(institution.sum()),
            "n_institution_records_with_family_record": int(
                institution[institution.index.isin(counts.index)].sum()
            ),
            "n_families_with_institution_records": int(len(attached)),
            "of_which_fu_size_equals_in_family_only": int(
                (attached["fu_size"] == attached["in_family"]).sum()
            ),
            "of_which_fu_size_equals_in_family_plus_institution": int(
                (
                    attached["fu_size"]
                    == attached["in_family"] + attached["institution"]
                ).sum()
            ),
        }
    return out


def _clean(value: Any) -> Any:
    """JSON-ready: numpy scalars to Python, non-finite floats to None."""

    if isinstance(value, Mapping):
        return {str(key): _clean(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_clean(item) for item in value]
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def component_diagnostics(
    cohort: age67.Age67Cohort,
    inputs: age67.Age67Inputs,
    *,
    rates: Mapping[str, Any] | None = None,
    published: Mapping[int, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Every F17 component summary for ``cohort`` (no poverty statistic).

    ``rates`` defaults to :func:`federal_benefit_rates` and ``published``
    to :func:`ssa_table_5a4` for the Decembers the income years need.
    """

    rows = component_rows(cohort, inputs)
    years = sorted(set(rows["income_year"].astype(int)))
    rates = federal_benefit_rates() if rates is None else rates
    if published is None:
        decembers = sorted({y for year in years for y in (year - 1, year)})
        published = ssa_table_5a4(decembers)
    result = {
        "population": {
            "row": cohort.spec.row,
            "provenance_kind": cohort.provenance.get("kind"),
            "n_observations": int(len(rows)),
            "n_persons": int(rows["person_id"].nunique()),
            "income_years": years,
            "weights": "observation weights (cross-section weight of the "
            "wave reporting the income year, times the row multiplier)",
        },
        "social_security": social_security_summary(rows, published),
        "ssi": ssi_summary(rows, rates),
        "wealth1": wealth1_summary(rows),
        "institution_record_counts": institution_record_counts(inputs),
        "published_sources": {
            "social_security": {
                "publication": "SSA, Annual Statistical Supplement, 2025",
                "table": "5.A4",
                "title": (
                    "Number of beneficiaries and total monthly benefits, by "
                    "trust fund and type of benefit, December 1940-2024, "
                    "selected years"
                ),
                "url": SSA_5A_URL,
                "snapshot": str(SSA_5A_SNAPSHOT_PATH.relative_to(_ROOT)),
                "snapshot_sha256": SSA_5A_SNAPSHOT_SHA256,
                "cells": {str(k): v for k, v in sorted(published.items())},
                "derived": (
                    "average_monthly = 1000 * total monthly benefits "
                    "(thousands) / number (a division made here)"
                ),
                "concept_differences": [
                    "every age against members observed at 66-68",
                    "retired workers (or retired workers, spouses and "
                    "widow(er)s combined) against any benefit type",
                    "December monthly benefit against a calendar-year total "
                    "divided by twelve",
                    "benefits in current-payment status against a "
                    "self-report possibly net of the Medicare premium",
                ],
            },
            "ssi": {
                "federal_benefit_rates": rates["source"],
                "rule": rates["rule"],
                "published_aggregates": (
                    "none committed or saved (no SSI recipient or payment "
                    "table)"
                ),
            },
            "wealth1": {
                "published_aggregates": None,
                "not_compared": (
                    "no Survey of Consumer Finances table (the plan's "
                    "comparator: wealth percentiles by age) is committed or "
                    "saved; the WEALTH1 summaries are reported without a "
                    "published comparison"
                ),
            },
        },
        "not_computed": [
            "no income concept, annuity, threshold, poverty status or "
            "poverty rate (the official-concept poverty rate of plan F17 "
            "runs only in the registered run)",
        ],
    }
    return _clean(result)
