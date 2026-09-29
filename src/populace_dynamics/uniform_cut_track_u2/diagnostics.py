"""F17 component diagnostics for U2 (no poverty computation).

Specification section 9, "Permitted before registration": the inherited
component summaries without poverty-threshold assignment or poverty
status -- by income year, own Social Security receipt and mean amounts
of head and spouse-slot members plus family-level receipt; SSI receipt,
recipient means and recipient units above twelve times the applicable
federal rate; WEALTH1 weighted quantiles (10/25/50/75/90, the smallest
value reaching the cumulative share) and nonpositive, negative and
imputed shares; family-size versus individual-record counts.  OFUM own
amounts are not identified.  Social Security is set against the committed
SSA Annual Statistical Supplement 2025 Table 5.A4 snapshot (Decembers
2011-2022, both the prior-December and income-year-December conventions,
with the inherited limitations).

This module imports neither an income concept nor a tabulation: it
reads the U2 SSI capture's federal benefit rates through its own pin
(held equal to :data:`populace_dynamics.uniform_cut_track_u2.parameters.
SSI_SHA256` by a test) and reuses U1's pure summary functions from
:mod:`populace_dynamics.uniform_cut_track_u.diagnostics`, which do not
import the income concept either.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.uniform_cut_track_u import diagnostics as u1
from populace_dynamics.uniform_cut_track_u2 import cohort, identity

__all__ = [
    "SSI_PATH",
    "SSI_SHA256",
    "component_diagnostics",
    "component_rows",
    "family_size_counts",
    "federal_benefit_rates",
]

SSI_PATH = (
    identity.ROOT
    / "data"
    / "external"
    / "track_u2_ssi_parameters_2012_2022.json"
)
SSI_SHA256 = "a58d55c160b48cd3e21f730d45265374bd3c8a9eb7eae947469a5a5dc0b23762"


def federal_benefit_rates(path: Path = SSI_PATH) -> dict[str, Any]:
    """The U2 capture's federal benefit rates (monthly), hash-verified."""

    raw = Path(path).read_bytes()
    observed = hashlib.sha256(raw).hexdigest()
    if observed != SSI_SHA256:
        raise ValueError(f"{path} sha256 {observed} != U2 pin {SSI_SHA256}")
    data = json.loads(raw)
    identity.check_target(data.get("target_id"), "the SSI capture")
    rates = data["federal_benefit_rate_monthly"]
    return {
        "individual": {
            int(y): float(v) for y, v in rates["individual"].items()
        },
        "couple": {int(y): float(v) for y, v in rates["couple"].items()},
        "rule": "rate in force on January 1 of the income year",
        "source": {
            "file": str(Path(path).relative_to(identity.ROOT)),
            "sha256": observed,
            "policyengine_us_revision": data["source"][
                "policyengine_us_revision"
            ],
        },
    }


def component_rows(
    built: cohort.U2Cohort, inputs: cohort.U2Inputs
) -> pd.DataFrame:
    """One row per observation with its Social Security, SSI, WEALTH1.

    The columns of U1's ``component_rows``; an own amount is the family
    file's head or spouse-slot item by the member's income role (an OFUM
    member's own amount -- codes 90 and 92 included -- is not
    identified).
    """

    frames = []
    for wave, rows in built.observations.groupby("wave", sort=True):
        income = inputs.family_income[int(wave)][
            [
                "interview",
                "head_ss",
                "wife_ss",
                "ofum_ss",
                "head_ssi",
                "wife_ssi",
                "ofum_ssi",
            ]
        ]
        wealth = inputs.family_wealth[int(wave)][
            ["interview", "wealth1", "wealth1_acc"]
        ]
        frames.append(
            rows.merge(
                income, on="interview", how="left", validate="many_to_one"
            ).merge(wealth, on="interview", how="left", validate="many_to_one")
        )
    if not frames:
        raise ValueError("the cohort has no observations")
    data = pd.concat(frames, ignore_index=True)
    if data["head_ss"].isna().any() or data["wealth1"].isna().any():
        raise ValueError("an observation has no family-file record")
    role = data["member_role"].astype(str)
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
    return pd.DataFrame(
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
            "own_identified": role.isin(["head", "wife"]).to_numpy(),
            "own_ss": own_ss.astype("float64"),
            "family_ss": data[["head_ss", "wife_ss", "ofum_ss"]]
            .sum(axis=1)
            .astype("float64"),
            "own_ssi": own_ssi.astype("float64"),
            "head_ssi": data["head_ssi"].astype("float64"),
            "wife_ssi": data["wife_ssi"].astype("float64"),
            "ofum_ssi": data["ofum_ssi"].astype("float64"),
            "family_ssi": data[["head_ssi", "wife_ssi", "ofum_ssi"]]
            .sum(axis=1)
            .astype("float64"),
            "wealth_available": np.ones(len(data), dtype=bool),
            "wealth1": data["wealth1"].astype("float64"),
            "wealth1_acc": data["wealth1_acc"].astype("float64"),
        }
    )


def family_size_counts(inputs: cohort.U2Inputs) -> dict[str, Any]:
    """Counts only: ``# IN FU`` against in-family individual records."""

    out: dict[str, Any] = {}
    for wave in sorted(inputs.family_income):
        anchor = inputs.anchors[wave]
        size = inputs.family_income[wave].set_index("interview")["fu_size"]
        in_family = (
            anchor[anchor["sequence"].between(1, 20)]
            .groupby("interview")
            .size()
        )
        records = in_family.reindex(size.index).fillna(0)
        out[str(wave)] = {
            "n_families": int(len(size)),
            "n_fu_size_equals_in_family_records": int((size == records).sum()),
            "n_fu_size_differs": int((size != records).sum()),
        }
    return out


def component_diagnostics(
    built: cohort.U2Cohort,
    inputs: cohort.U2Inputs,
    *,
    rates: Mapping[str, Any] | None = None,
    published: Mapping[int, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Every permitted F17 component summary (no poverty statistic)."""

    rows = component_rows(built, inputs)
    years = sorted(set(rows["income_year"].astype(int)))
    rates = federal_benefit_rates() if rates is None else rates
    if published is None:
        decembers = sorted({y for year in years for y in (year - 1, year)})
        published = u1.ssa_table_5a4(decembers)
    result = {
        "target_id": identity.TARGET_ID,
        "population": {
            "row": built.spec.row,
            "provenance_kind": built.provenance.get("kind"),
            "role_context": built.provenance.get("role_context"),
            "n_observations": int(len(rows)),
            "n_persons": int(rows["person_id"].nunique()),
            "income_years": years,
        },
        "social_security": u1.social_security_summary(rows, published),
        "ssi": u1.ssi_summary(rows, rates),
        "wealth1": u1.wealth1_summary(rows),
        "family_size_counts": family_size_counts(inputs),
        "published_sources": {
            "social_security": {
                "table": "SSA Annual Statistical Supplement 2025, 5.A4",
                "snapshot": str(
                    u1.SSA_5A_SNAPSHOT_PATH.relative_to(identity.ROOT)
                ),
                "snapshot_sha256": u1.SSA_5A_SNAPSHOT_SHA256,
                "limitations": [
                    "December retired-worker aggregates cover all ages",
                    "the PSID reports annual amounts",
                    "prior-December and income-year-December comparisons",
                ],
            },
            "ssi": {"federal_benefit_rates": rates["source"]},
            "wealth1": {"published_aggregates": None},
        },
        "not_computed": [
            "no income concept, annuity, threshold assignment, poverty "
            "status or poverty rate (section 9: the official-concept rate "
            "runs only in the registered run)"
        ],
    }
    return u1._clean(result)
