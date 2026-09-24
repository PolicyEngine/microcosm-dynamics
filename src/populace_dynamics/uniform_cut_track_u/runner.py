"""The Track U row pipeline for DynaSim scorecard exercise 2.

For each registered row (:data:`populace_dynamics.uniform_cut_track_u.
rows.REGISTERED_ROWS`): build the age-67 observations
(:func:`populace_dynamics.cohorts.age67.build_age67_cohort`), attach the
family income and wealth (:func:`~populace_dynamics.cohorts.age67.
income_rows`), form baseline and reform adjusted income and poverty
status (:func:`populace_dynamics.estimates.adjusted_poverty.
adjusted_incomes`) and tabulate the frozen statistic
(:func:`populace_dynamics.estimates.uniform_cut_tabulation.
tabulate_uniform_cut`) with the design-based standard error on the full
sample design (:func:`design_frame`).  For the headline row it also
computes the two F17 diagnostics: the component summaries
(:mod:`populace_dynamics.uniform_cut_track_u.diagnostics`) and the
official-concept poverty rate (:func:`official_concept_rates`: money
income against the same thresholds, reported asset income kept, no
annuity, no cut).

The headline row follows the specification's fallback rule
(:data:`populace_dynamics.uniform_cut_track_u.rows.HEADLINE_RULE`, pending
Max): U0 when every wave has WEALTH1, otherwise U0-F; a row whose
observation waves include a wave without WEALTH1 is reported as blocked,
with its structural counts, and not computed (unless ``allow_blocked``,
which leaves the blocked observations out and is refused for a
registered run).  The rule depends on staging status only.

Provenance guards, before anything is computed:

* ``data_provenance="invented"``: the inputs must be the invented
  generator's output for their recorded seed (re-generated and compared,
  :func:`populace_dynamics.uniform_cut_track_u.invented.
  check_invented_inputs`), and the built cohort must record the
  ``invented`` kind.
* ``data_provenance="registered_real"``: the registration pointer must be
  an issue #42 comment URL; the cohort must record ``psid_files`` (inputs
  returned and sealed by :func:`~populace_dynamics.cohorts.age67.
  load_age67_inputs`); the thresholds must be the committed Census
  capture, the SSI parameters and life tables the committed ones; no
  observation may be left out (a wave without WEALTH1 blocks the rows
  that need it, and U0-F becomes the headline).

The income concept and the tabulation apply their own guards as well.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.cohorts import age67
from populace_dynamics.estimates import adjusted_poverty as ap
from populace_dynamics.estimates import uniform_cut_tabulation as ut
from populace_dynamics.uniform_cut_track_u import diagnostics, invented
from populace_dynamics.uniform_cut_track_u.rows import (
    FALLBACK_ROW,
    HEADLINE_RULE,
    PRIMARY_ROW,
    REGISTERED_ROWS,
    TrackURow,
)

__all__ = [
    "NAMED_DELTAS",
    "OFFICIAL_CONCEPT_CELLS",
    "REGISTRATION_POINTER",
    "RUN_SCHEMA_VERSION",
    "TrackUParameters",
    "TrackURunError",
    "blocked_waves",
    "committed_parameters",
    "design_frame",
    "headline_row",
    "official_concept_rates",
    "run_track_u",
]

RUN_SCHEMA_VERSION = "populace_dynamics.track_u_run.v1"
#: A comment on issue #42, the registration issue; nothing else is a
#: registration pointer (the Track A convention).
REGISTRATION_POINTER = re.compile(
    r"https://github\.com/PolicyEngine/microcosm-dynamics/issues/42"
    r"#issuecomment-[0-9]+"
)
OFFICIAL_CONCEPT_CELLS: tuple[str, ...] = ut.DEFAULT_CELLS
#: The named deltas every output carries (specification section 12, whose
#: bullets hold the same text; ``tests/test_boomers2004_uniform_cut_spec.py``
#: checks that they agree).
NAMED_DELTAS: tuple[str, ...] = (
    "PSID versus SIPP wealth measurement",
    "realized 2004-2012 history versus DYNASIM's 1992-based projection, "
    "including the 2008-09 asset shock for the 1941-45 cohorts at 67",
    "realized COLAs versus 2002 Trustees assumptions",
    "immigrant under-coverage; institutionalized persons (row U-inst: "
    "the family-of-record rule assigns the family's income and threshold "
    "without the member's own income, which the PSID does not collect); "
    "attrition",
    "OFUM-owned assets inside family wealth",
    "the family's wealth stands in for an OFUM cohort member's own wealth "
    "(the Report's unit is the individual plus spouse, p. 24)",
    "imputed rent excluded",
    "self-reported Social Security, possibly net of Medicare Part B "
    "premiums, so the 13 percent cut applies to a smaller base than the "
    "gross benefit (baseline income is lower too; the net direction on "
    "the change is not established)",
    "retirement-account income beside annuitized balances: the head's "
    "income from annuities and IRAs is removed (F4a), but the wife's "
    "(before 2013) and the OFUMs' items combine pensions with annuity "
    "income and stay, so any IRA or annuity income in them is counted "
    "twice; an annuity already in payment may have no balance in WEALTH1, "
    "so removing its income understates income",
    "employer DC (401(k)) balances outside IRAs are not in WEALTH1 though "
    "the Report counts them (p. 24): the primary annuity is understated "
    "for their holders (row U7)",
    "PSID other assets (W34) include cash value of life insurance, "
    "collections and rights in a trust or estate, which the Report's list "
    "(p. 22) does not name",
    "the annuity is priced on population period life tables by age and "
    "sex (NCHS 2000; U9 SSA 2004), while DYNASIM's mortality follows the "
    "2002 Trustees projections (p. 20, fn. 4) and the Report ties the "
    "annuity to family life expectancy (p. 24): with falling mortality, "
    "period tables overstate the annuity",
    "exact-age sampling of alternate birth years (mean birth year 1941 "
    "against 1940.5)",
    "U1 averages ages 66 and 68, and claiming between those ages is not "
    "linear in age",
    "the universe is alive at the interview after the income year",
    "farm income's asset portion is imputed by the PSID business "
    "convention (farm_asset_share); business income is split 50/50 "
    "between labor and asset parts by PSID convention for working owners",
    "SSI units approximated from head, wife and OFUM totals (deeming by "
    "full attribution; OFUMs as one unit)",
    "SSI deeming by full attribution can only overstate the offset (so "
    "understate the change): under 20 CFR 416.1163 nothing is deemed when "
    "the ineligible spouse's income is at most the couple-minus-individual "
    "FBR",
    "the SSI test uses annual amounts against 12 times the January FBR "
    "(SSI accounting is monthly), and U3 omits rent and royalties from "
    "countable income although 20 CFR 416.1121 counts them",
    "reported SSI may include state supplementary payments, so capping "
    "the offset at the federal benefit rate less reported SSI can "
    "understate the offset",
    "U0-F, if it is the headline: mean birth year 1943 against 1940.5, "
    "and every observation year at or after the 2008-09 asset shock",
)


class TrackURunError(ValueError):
    """The inputs, parameters or provenance cannot run under the label."""


@dataclass(frozen=True)
class TrackUParameters:
    """The parameters a run reads: thresholds, SSI and life tables."""

    thresholds: ap.PovertyThresholds | None
    ssi: ap.SsiParameters
    life_tables: Mapping[str, ap.LifeTable]

    def provenance(self) -> dict[str, Any]:
        return {
            "thresholds": (
                None
                if self.thresholds is None
                else dict(self.thresholds.provenance)
            ),
            "ssi": dict(self.ssi.provenance),
            "life_tables": {
                name: {"name": table.name, **dict(table.source)}
                for name, table in sorted(self.life_tables.items())
            },
        }


def committed_parameters(
    thresholds: ap.PovertyThresholds | None,
) -> TrackUParameters:
    """The committed SSI capture and life tables, with ``thresholds``.

    The dry run passes the invented threshold table (the Census capture
    does not exist yet, cos decision d194); the registered run passes
    :func:`populace_dynamics.estimates.adjusted_poverty.
    load_poverty_thresholds`, which refuses until the capture is pinned.
    """

    return TrackUParameters(
        thresholds=thresholds,
        ssi=ap.load_ssi_parameters(),
        life_tables={
            "nchs_2000": ap.load_nchs_2000_life_table(),
            "ssa_period_2004": ap.load_ssa_period_2004_life_table(),
        },
    )


def _check_parameters(params: TrackUParameters, data_provenance: str) -> None:
    for basis, table in params.life_tables.items():
        invented_table = (
            data_provenance == ap.INVENTED
            and table.name == ap.INVENTED_LIFE_TABLE
        )
        if table.name != basis and not invented_table:
            raise TrackURunError(
                f"life table {table.name!r} is filed under {basis!r}"
            )
    if data_provenance != ap.REGISTERED_REAL:
        return
    from populace_dynamics.data import tr2008

    thresholds = (
        {} if params.thresholds is None else dict(params.thresholds.provenance)
    )
    if thresholds.get("kind") != "census_capture" or (
        thresholds.get("sha256") != ap.THRESHOLDS_SHA256
    ):
        raise TrackURunError(
            "a registered run needs the committed, pinned Census threshold "
            f"capture; the thresholds record {thresholds!r}"
        )
    if params.ssi.provenance.get("kind") != "policyengine_us_capture" or (
        params.ssi.provenance.get("sha256") != ap.SSI_PARAMETERS_SHA256
    ):
        raise TrackURunError(
            "a registered run needs the committed SSI capture; the SSI "
            f"parameters record {dict(params.ssi.provenance)!r}"
        )
    pins = {
        "nchs_2000": ap.NCHS_2000_SHA256,
        "ssa_period_2004": tr2008.FILE_SHA256["ssa_2008_vintage.json"],
    }
    if set(params.life_tables) != set(pins) or any(
        params.life_tables[basis].source.get("sha256") != pin
        for basis, pin in pins.items()
    ):
        raise TrackURunError(
            "a registered run needs the committed life tables "
            f"{sorted(pins)} with their pinned SHA-256"
        )


def headline_row(inputs: age67.Age67Inputs) -> str:
    """The headline row under the fallback rule (staging status only).

    U0 when every wave's WEALTH1 is available (the 2005 and 2007 wealth
    supplements staged, adjudicated and read); U0-F otherwise.
    """

    return FALLBACK_ROW if inputs.wealth_refusals else PRIMARY_ROW


def blocked_waves(row: TrackURow, inputs: age67.Age67Inputs) -> list[int]:
    """The row's observation waves whose WEALTH1 the inputs refuse."""

    waves = {w for _, w, _, _ in age67.observation_plan(row.age67_spec())}
    return sorted(waves & {int(w) for w in inputs.wealth_refusals})


def design_frame(
    inputs: age67.Age67Inputs, spec: age67.Age67Spec
) -> pd.DataFrame:
    """The sample design the full-design standard error sums over.

    The distinct (stratum, cluster) pairs (ER31996, ER31997) of every
    person with a positive cross-section weight in any of the row's
    observation waves (specification section 10).
    """

    waves = sorted({w for _, w, _, _ in age67.observation_plan(spec)})
    positive: set[int] = set()
    for wave in waves:
        anchor = inputs.anchors[wave]
        positive |= set(
            anchor.loc[anchor["weight"] > 0, "person_id"].astype(int)
        )
    design = inputs.design[inputs.design["person_id"].isin(positive)]
    return (
        design[["stratum", "cluster"]]
        .astype("int64")
        .drop_duplicates()
        .sort_values(["stratum", "cluster"])
        .reset_index(drop=True)
    )


def _check_inputs(
    inputs: age67.Age67Inputs,
    data_provenance: str,
    registration_pointer: str | None,
    allow_blocked: bool,
) -> dict[str, Any]:
    if data_provenance == ap.INVENTED:
        if registration_pointer is not None:
            raise TrackURunError(
                "an invented run carries no registration pointer"
            )
        return {"invented_inputs": invented.check_invented_inputs(inputs)}
    if data_provenance != ap.REGISTERED_REAL:
        raise TrackURunError(
            f"data_provenance must be one of {ap.DATA_PROVENANCES}"
        )
    if not isinstance(registration_pointer, str) or not (
        REGISTRATION_POINTER.fullmatch(registration_pointer)
    ):
        raise TrackURunError(
            "a registered run needs an issue #42 comment URL as its "
            "registration pointer (https://github.com/PolicyEngine/"
            "microcosm-dynamics/issues/42#issuecomment-<id>)"
        )
    if (inputs.provenance or {}).get("kind") != age67.PSID_FILES:
        raise TrackURunError(
            "a registered run reads the staged PSID through "
            "age67.load_age67_inputs; these inputs record "
            f"{(inputs.provenance or {}).get('kind')!r}"
        )
    if allow_blocked:
        raise TrackURunError(
            "a registered run may not leave blocked observations out"
        )
    return {}


def _counts(series: pd.Series) -> dict[str, int]:
    return {
        str(key): int(value)
        for key, value in series.value_counts(dropna=False)
        .sort_index()
        .items()
    }


def _cell_masks(members: pd.DataFrame) -> dict[str, np.ndarray]:
    male = members["sex"].astype(str).eq("male").to_numpy()
    married = members["married"].astype(bool).to_numpy()
    return {
        "all": np.ones(len(members), dtype=bool),
        "men": male,
        "women": ~male,
        "married": married,
        "non_married": ~married,
    }


def official_concept_rates(
    members: pd.DataFrame, adjusted: pd.DataFrame
) -> dict[str, Any]:
    """F17: the official-concept poverty rate for the same sample.

    Poor when the unit's money income (``money_income``: TOTAL FAMILY
    INCOME under the family-unit basis, reported asset income kept, no
    annuity, no cut) is below the row's threshold (the same threshold as
    the adjusted concept, so the 65-and-over rule, not the Census
    householder-age convention).  Weighted rate per cell of
    :data:`OFFICIAL_CONCEPT_CELLS`, in percent; an empty or zero-weight
    cell is undefined.  Not scored.
    """

    joined = members[["observation_id", "weight", "sex", "married"]].merge(
        adjusted[["observation_id", "money_income", "threshold"]],
        on="observation_id",
        how="inner",
        validate="1:1",
    )
    if len(joined) != len(members) or len(joined) != len(adjusted):
        raise TrackURunError("members and adjusted incomes do not match")
    poor = (joined["money_income"] < joined["threshold"]).to_numpy()
    weight = joined["weight"].to_numpy(dtype=np.float64)
    cells = {}
    for name, mask in _cell_masks(joined).items():
        total = float(weight[mask].sum())
        if not mask.any() or total <= 0:
            cells[name] = {
                "defined": False,
                "undefined_reason": (
                    "empty cell" if not mask.any() else "zero total weight"
                ),
                "n_observations": int(mask.sum()),
            }
            continue
        cells[name] = {
            "defined": True,
            "rate": 100.0 * float(weight[mask & poor].sum()) / total,
            "n_observations": int(mask.sum()),
            "weight_total": total,
        }
    return {
        "definition": (
            "100 * sum w 1{money income < threshold} / sum w; money income "
            "is TOTAL FAMILY INCOME (family-unit basis) with reported asset "
            "income kept, no annuity and no cut; the threshold is the "
            "row's (not scored; plan field F17)"
        ),
        "cells": cells,
    }


def _income_counts(adjusted: pd.DataFrame) -> dict[str, Any]:
    entering = adjusted["poor_reform"] & ~adjusted["poor_baseline"]
    leaving = adjusted["poor_baseline"] & ~adjusted["poor_reform"]
    return {
        "n_observations": int(len(adjusted)),
        "n_cut_applies": int(adjusted["cut_applies"].sum()),
        "n_social_security_positive": int(
            (adjusted["social_security"] > 0).sum()
        ),
        "n_annuity_positive": int((adjusted["annuity"] > 0).sum()),
        "n_financial_assets_negative": int(
            (adjusted["financial_assets"] < 0).sum()
        ),
        "n_asset_income_removed_nonzero": int(
            (adjusted["asset_income_removed"] != 0).sum()
        ),
        "n_retirement_account_income_removed_nonzero": int(
            (adjusted["retirement_account_income_removed"] != 0).sum()
        ),
        "n_farm_asset_income_removed_nonzero": int(
            (adjusted["farm_asset_income_removed"] != 0).sum()
        ),
        "n_ssi_offset_positive": int((adjusted["ssi_offset"] > 0).sum()),
        "n_ssi_new_positive": int((adjusted["ssi_new"] > 0).sum()),
        "n_poor_baseline": int(adjusted["poor_baseline"].sum()),
        "n_poor_reform": int(adjusted["poor_reform"].sum()),
        "n_entering_poverty": int(entering.sum()),
        "n_leaving_poverty": int(leaving.sum()),
        "income_basis": _counts(adjusted["income_basis"]),
        "threshold_cells": _counts(adjusted["threshold_cell"]),
        "annuity_basis_kind": _counts(
            adjusted["annuity_basis"].str.split(":").str[0]
        ),
    }


def _pending(row: TrackURow) -> list[dict[str, Any]]:
    items = [item.as_dict() for item in age67.pending_decisions()]
    items += [item.as_dict() for item in ap.pending_decisions()]
    items += [item.as_dict() for item in ut.pending_decisions()]
    if row.awaiting:
        items.append(
            {
                "field": f"row {row.row_id}",
                "default": None,
                "alternatives": [],
                "default_basis": row.description,
                "awaiting": row.awaiting,
            }
        )
    return items


def _compute_row(
    row: TrackURow,
    inputs: age67.Age67Inputs,
    params: TrackUParameters,
    *,
    data_provenance: str,
    registration_pointer: str | None,
    allow_blocked: bool,
    tabulation_config: ut.TabulationConfig | None,
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, age67.Age67Cohort]:
    age67_spec = row.age67_spec()
    income_spec = row.income_spec()
    cohort = age67.build_age67_cohort(inputs, age67_spec)
    kind = cohort.provenance.get("kind")
    expected = (
        age67.INVENTED if data_provenance == ap.INVENTED else age67.PSID_FILES
    )
    if kind != expected:
        raise TrackURunError(
            f"row {row.row_id}: the cohort records {kind!r}, not {expected!r}"
        )
    members = age67.income_rows(cohort, inputs, allow_blocked=allow_blocked)
    if data_provenance == ap.REGISTERED_REAL and any(
        members.attrs.get("left_out", {}).values()
    ):
        raise TrackURunError(f"row {row.row_id}: observations were left out")
    adjusted = ap.adjusted_incomes(
        members,
        income_spec,
        data_provenance=data_provenance,
        life_table=params.life_tables[income_spec.mortality_basis],
        thresholds=params.thresholds,
        ssi=params.ssi,
        registration_pointer=registration_pointer,
    )
    joined = ut.tabulation_rows(members, adjusted)
    pending = _pending(row)
    tabulation = ut.tabulate_uniform_cut(
        joined,
        data_provenance=data_provenance,
        config=tabulation_config,
        registration_pointer=registration_pointer,
        upstream_spec=adjusted.attrs["spec"],
        pending_decisions=pending,
        design=design_frame(inputs, age67_spec),
    )
    obs = cohort.observations
    result = {
        "row": row.as_dict(),
        "status": "computed",
        "age67_spec": age67_spec.as_dict(),
        "income_spec": income_spec.as_dict(),
        "life_table": adjusted.attrs["life_table"],
        "population": {
            "n_observations_built": int(len(obs)),
            "n_observations_tabulated": int(len(members)),
            "n_persons": int(members["person_id"].nunique()),
            "n_family_units": int(members["family_unit_id"].nunique()),
            "n_in_institution": int(members["in_institution"].sum()),
            "left_out": dict(members.attrs.get("left_out", {})),
            "observations_by_birth_year": _counts(members["birth_year"]),
            "marital_resolution": _counts(members["marital_resolution"]),
            "fu_head_age_source": _counts(members["fu_head_age_source"]),
            "fu_head_spouse_age_source": _counts(
                members["fu_head_spouse_age_source"]
            ),
            "dispositions": (
                _counts(cohort.dispositions["disposition"])
                if not cohort.dispositions.empty
                else {}
            ),
        },
        "income_concept_counts": _income_counts(adjusted),
        "tabulation": tabulation,
    }
    return result, members, adjusted, cohort


def _blocked_result(
    row: TrackURow, inputs: age67.Age67Inputs, waves: list[int]
) -> dict[str, Any]:
    """A row that needs a wave without WEALTH1: counts only, no income."""

    cohort = age67.build_age67_cohort(inputs, row.age67_spec())
    obs = cohort.observations
    blocked = (
        obs["wave"].isin(waves) if not obs.empty else pd.Series(dtype=bool)
    )
    return {
        "row": row.as_dict(),
        "status": "blocked",
        "reason": (
            f"WEALTH1 is refused for waves {waves} (the 2005 and 2007 "
            "wealth supplements are not staged); reported with its "
            "counts under the fallback rule"
        ),
        "blocked_waves": waves,
        "population": {
            "n_observations_built": int(len(obs)),
            "n_observations_blocked": int(blocked.sum()),
            "observations_by_birth_year": (
                _counts(obs["birth_year"]) if not obs.empty else {}
            ),
            "blocked_by_birth_year": (
                _counts(obs.loc[blocked, "birth_year"])
                if not obs.empty
                else {}
            ),
        },
        "tabulation": None,
    }


def run_track_u(
    inputs: age67.Age67Inputs,
    params: TrackUParameters,
    *,
    data_provenance: str,
    registration_pointer: str | None = None,
    rows: Mapping[str, TrackURow] | None = None,
    allow_blocked: bool = False,
    tabulation_config: ut.TabulationConfig | None = None,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Every registered row, the F17 diagnostics and the provenance.

    Rows not built (U7) are reported with their reason.  The headline row
    is :func:`headline_row`'s (the fallback rule); a row whose waves lack
    WEALTH1 is reported as blocked with its counts unless
    ``allow_blocked`` (then its blocked observations are left out and
    counted; refused for a registered run).  An undefined cell stays
    undefined with its reason (the tabulation's rule); nothing is imputed
    or dropped silently.
    """

    rows = REGISTERED_ROWS if rows is None else rows
    headline = headline_row(inputs)
    if headline not in rows:
        raise TrackURunError(
            f"the headline row {headline} (fallback rule, staging status) "
            "must run"
        )
    checks = _check_inputs(
        inputs, data_provenance, registration_pointer, allow_blocked
    )
    _check_parameters(params, data_provenance)
    say = progress or (lambda message: None)
    results: dict[str, Any] = {}
    primary: tuple[pd.DataFrame, pd.DataFrame, age67.Age67Cohort] | None = None
    for row_id, row in rows.items():
        if not row.built:
            results[row_id] = {
                "row": row.as_dict(),
                "status": "not_built",
                "reason": row.not_built_reason,
                "tabulation": None,
            }
            continue
        waves = blocked_waves(row, inputs)
        if waves and not allow_blocked:
            say(f"Track U row {row_id}: blocked (waves {waves})")
            results[row_id] = _blocked_result(row, inputs, waves)
            continue
        say(f"Track U row {row_id}")
        result, members, adjusted, cohort = _compute_row(
            row,
            inputs,
            params,
            data_provenance=data_provenance,
            registration_pointer=registration_pointer,
            allow_blocked=allow_blocked,
            tabulation_config=tabulation_config,
        )
        results[row_id] = result
        if row_id == headline:
            primary = (members, adjusted, cohort)
    if primary is None:
        raise TrackURunError(f"the headline row {headline} was not computed")
    members, adjusted, cohort = primary
    if data_provenance == ap.INVENTED:
        checks["invented_cohort"] = invented.check_invented_cohort(cohort)
    labels = list(ap.OUTPUT_LABELS)
    if data_provenance == ap.INVENTED:
        labels.insert(0, ut.INVENTED_DATA_LABEL)
    return {
        "schema_version": RUN_SCHEMA_VERSION,
        "statistic_id": ut.STATISTIC_ID,
        "data_provenance": data_provenance,
        "registration_pointer": registration_pointer,
        "labels": labels,
        "headline": {
            "row": headline,
            "rule": HEADLINE_RULE,
            "wealth_refused_waves": sorted(
                int(w) for w in inputs.wealth_refusals
            ),
        },
        "cohort_provenance": {
            key: value
            for key, value in cohort.provenance.items()
            if key != "psid_files_sha256"
        },
        "psid_files_sha256": dict(
            cohort.provenance.get("psid_files_sha256") or {}
        ),
        "parameters": params.provenance(),
        "input_checks": checks,
        "rows": results,
        "f17_diagnostics": {
            "row": headline,
            "official_concept_poverty_rate": official_concept_rates(
                members, adjusted
            ),
            "components": diagnostics.component_diagnostics(cohort, inputs),
        },
        "named_deltas": list(NAMED_DELTAS),
        "pending_decisions": {
            "age67": [item.as_dict() for item in age67.pending_decisions()],
            "income_concept": [
                item.as_dict() for item in ap.pending_decisions()
            ],
            "tabulation": [item.as_dict() for item in ut.pending_decisions()],
            "rows": {
                row_id: row.awaiting
                for row_id, row in rows.items()
                if row.awaiting
            },
        },
    }
