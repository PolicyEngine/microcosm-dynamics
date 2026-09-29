"""The U2 row pipeline: ten rows, fixed U0 headline, F17 diagnostics.

Specification sections 9-14.  For each registered row
(:data:`populace_dynamics.uniform_cut_track_u2.rows.REGISTERED_ROWS`):
build the observations (:func:`~populace_dynamics.uniform_cut_track_u2.
cohort.build_u2_cohort`, with births derived once and shared), attach
the family income, wealth and DC (:func:`~populace_dynamics.
uniform_cut_track_u2.cohort.income_rows`), form baseline and reform
income (:func:`~populace_dynamics.uniform_cut_track_u2.estimator.
u2_adjusted_incomes`) and tabulate (:func:`~populace_dynamics.
uniform_cut_track_u2.tabulation.tabulate_u2`) on the row's own design
frame.  The headline is fixed at U0: there is no fallback, and a row that
cannot run stops the run (missing mappings, parameters or sources block
execution; they never trigger fallback or silent omission, section 11).
The two-percent interest sensitivity is reported on U0, unscored.

Guards, before anything is computed:

* ``invented``: the inputs must re-generate from the invented U2
  generator's seed; any role context may run (the registry context then
  refuses on the TO VERIFY codes, which the dry run records).
* ``registered_real``: an issue #42 comment pointer; inputs sealed by the
  U2 loader (``psid_files``); the committed-registry role context; U2's
  pinned parameters (:func:`~populace_dynamics.uniform_cut_track_u2.
  parameters.check_u2_parameters`).

The output records the U2 identity, the ten rows, the literal named
deltas, U2's rulings record and the fixed headline.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.estimates import adjusted_poverty as ap
from populace_dynamics.estimates import uniform_cut_tabulation as ut
from populace_dynamics.uniform_cut_track_u2 import (
    DRY_RUN_HEADER,
    cohort,
    diagnostics,
    estimator,
    identity,
    invented,
    parameters,
    rows,
    sources,
    tabulation,
)

__all__ = [
    "OFFICIAL_CONCEPT_CELLS",
    "REGISTRATION_POINTER",
    "RUN_SCHEMA_VERSION",
    "U2RunError",
    "check_headline",
    "check_inputs",
    "official_concept_rates",
    "run_track_u2",
]

RUN_SCHEMA_VERSION = "populace_dynamics.track_u2_run.v1"
REGISTRATION_POINTER = re.compile(
    r"https://github\.com/PolicyEngine/microcosm-dynamics/issues/42"
    r"#issuecomment-[0-9]+"
)
OFFICIAL_CONCEPT_CELLS: tuple[str, ...] = tabulation.DEFAULT_CELLS


class U2RunError(ValueError):
    """The inputs, parameters, context or provenance cannot run."""


def check_headline(headline: str) -> str:
    """Refuse any headline but the fixed U0 (section 11: no fallback)."""

    if headline != rows.HEADLINE_ROW:
        raise U2RunError(
            f"the U2 headline is fixed at {rows.HEADLINE_ROW}; "
            f"{headline!r} is refused (no fallback, section 11)"
        )
    return headline


def check_inputs(
    inputs: cohort.U2Inputs,
    data_provenance: str,
    registration_pointer: str | None,
    role_context: sources.RoleContext,
) -> dict[str, Any]:
    """The provenance guards (U1's order and wording, U2's identity)."""

    if not isinstance(inputs, cohort.U2Inputs):
        raise U2RunError("a U2 run needs U2Inputs")
    identity.check_target(inputs.target_id, "the inputs")
    if data_provenance == ap.INVENTED:
        if registration_pointer is not None:
            raise U2RunError("an invented run carries no registration pointer")
        return {"invented_inputs": invented.check_invented_inputs(inputs)}
    if data_provenance != ap.REGISTERED_REAL:
        raise U2RunError(
            f"data_provenance must be one of {ap.DATA_PROVENANCES}"
        )
    if not isinstance(registration_pointer, str) or not (
        REGISTRATION_POINTER.fullmatch(registration_pointer)
    ):
        raise U2RunError(
            "a registered run needs an issue #42 comment URL as its "
            "registration pointer (https://github.com/PolicyEngine/"
            "microcosm-dynamics/issues/42#issuecomment-<id>)"
        )
    if (inputs.provenance or {}).get("kind") != cohort.PSID_FILES:
        raise U2RunError(
            "a registered U2 run reads the staged PSID through the U2 "
            "loader; these inputs record "
            f"{(inputs.provenance or {}).get('kind')!r}"
        )
    if role_context.kind != sources.REGISTRY:
        raise U2RunError(
            "a registered U2 run applies the committed roles registry"
        )
    return {}


def official_concept_rates(
    members: pd.DataFrame, adjusted: pd.DataFrame
) -> dict[str, Any]:
    """F17: money income against the row's threshold, no annuity or cut.

    Not scored; section 9 runs it in the registered run on the headline
    row's sample (the dry run runs it on invented data).
    """

    joined = members[
        ["observation_id", "weight", "sex", "marital_status_4"]
    ].merge(
        adjusted[["observation_id", "money_income", "threshold"]],
        on="observation_id",
        how="inner",
        validate="1:1",
    )
    if len(joined) != len(members) or len(joined) != len(adjusted):
        raise U2RunError("members and adjusted incomes do not match")
    poor = (joined["money_income"] < joined["threshold"]).to_numpy()
    weight = joined["weight"].to_numpy(dtype=np.float64)
    cells = {}
    for name in OFFICIAL_CONCEPT_CELLS:
        mask = ut.cell_mask(joined, name)
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
            "100 * sum w 1{money income < threshold} / sum w; TOTAL FAMILY "
            "INCOME with reported asset income kept, no annuity and no cut; "
            "the row's threshold (not scored; section 9 F17)"
        ),
        "cells": cells,
    }


def _counts(series: pd.Series) -> dict[str, int]:
    return {
        str(key): int(value)
        for key, value in series.value_counts(dropna=False)
        .sort_index()
        .items()
    }


def _income_counts(adjusted: pd.DataFrame) -> dict[str, Any]:
    entering = adjusted["poor_reform"] & ~adjusted["poor_baseline"]
    leaving = adjusted["poor_baseline"] & ~adjusted["poor_reform"]
    return {
        "n_observations": int(len(adjusted)),
        "n_cut_applies": int(adjusted["cut_applies"].sum()),
        "n_annuity_positive": int((adjusted["annuity"] > 0).sum()),
        "n_employer_dc_added_positive": int(
            (adjusted["employer_dc_added"] > 0).sum()
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


def _pending() -> list[dict[str, Any]]:
    return [item.as_dict() for item in cohort.pending_decisions()]


def _estimate(
    members: pd.DataFrame,
    spec: estimator.U2IncomeSpec,
    params: parameters.U2Parameters,
    *,
    role_context: sources.RoleContext,
    data_provenance: str,
    registration_pointer: str | None,
) -> pd.DataFrame:
    return estimator.u2_adjusted_incomes(
        members,
        spec,
        context=estimator.U2EstimatorContext(role_context.kind),
        data_provenance=data_provenance,
        life_table=params.life_tables[spec.mortality_basis],
        thresholds=params.thresholds,
        ssi=params.ssi,
        registration_pointer=registration_pointer,
    )


def _compute_row(
    row: rows.U2Row,
    inputs: cohort.U2Inputs,
    params: parameters.U2Parameters,
    births: cohort.U2Births,
    *,
    role_context: sources.RoleContext,
    data_provenance: str,
    registration_pointer: str | None,
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, cohort.U2Cohort]:
    cohort_spec = row.cohort_spec()
    income_spec = row.income_spec()
    built = cohort.build_u2_cohort(
        inputs, cohort_spec, role_context=role_context, births=births
    )
    expected = (
        cohort.INVENTED
        if data_provenance == ap.INVENTED
        else cohort.PSID_FILES
    )
    if built.provenance.get("kind") != expected:
        raise U2RunError(
            f"row {row.row_id}: the cohort records "
            f"{built.provenance.get('kind')!r}, not {expected!r}"
        )
    members = cohort.income_rows(built, inputs)
    adjusted = _estimate(
        members,
        income_spec,
        params,
        role_context=role_context,
        data_provenance=data_provenance,
        registration_pointer=registration_pointer,
    )
    joined = tabulation.tabulation_rows(members, adjusted)
    table = tabulation.tabulate_u2(
        joined,
        data_provenance=data_provenance,
        design=cohort.design_frame(inputs, cohort_spec),
        registration_pointer=registration_pointer,
        upstream_spec=adjusted.attrs["spec"],
        pending_decisions=_pending(),
    )
    obs = built.observations
    result = {
        "row": row.as_dict(),
        "status": "computed",
        "cohort_spec": cohort_spec.as_dict(),
        "income_spec": income_spec.as_dict(),
        "life_table": adjusted.attrs["life_table"],
        "population": {
            "n_observations_built": int(len(obs)),
            "n_observations_tabulated": int(len(members)),
            "n_persons": int(members["person_id"].nunique()),
            "n_family_units": int(members["family_unit_id"].nunique()),
            "observations_by_birth_year": _counts(members["birth_year"]),
            "observations_by_wave": _counts(members["wave"]),
            "member_role": _counts(members["member_role"]),
            "relationship": _counts(members["relationship"]),
            "marital_resolution": _counts(members["marital_resolution"]),
            "marital_status_4": _counts(members["marital_status_4"]),
            "legal_spouse_pairing": _counts(members["legal_spouse_pairing"]),
            "spouse_age_source": _counts(members["spouse_age_source"]),
            "fu_head_age_source": _counts(members["fu_head_age_source"]),
            "fu_head_spouse_age_source": _counts(
                members["fu_head_spouse_age_source"]
            ),
            "dispositions": (
                _counts(built.dispositions["disposition"])
                if not built.dispositions.empty
                else {}
            ),
            **{
                k: v
                for k, v in built.diagnostics.items()
                if k.startswith("n_")
            },
        },
        "income_concept_counts": _income_counts(adjusted),
        "tabulation": table,
    }
    return result, members, adjusted, built


def _sensitivity(
    members: pd.DataFrame,
    inputs: cohort.U2Inputs,
    params: parameters.U2Parameters,
    *,
    role_context: sources.RoleContext,
    data_provenance: str,
    registration_pointer: str | None,
) -> dict[str, Any]:
    """The unscored two-percent interest sensitivity on U0 (section 5)."""

    out = {}
    for rate in rows.SENSITIVITIES_UNSCORED["real_interest_rate"]:
        spec = estimator.U2IncomeSpec(real_interest_rate=rate)
        adjusted = _estimate(
            members,
            spec,
            params,
            role_context=role_context,
            data_provenance=data_provenance,
            registration_pointer=registration_pointer,
        )
        table = tabulation.tabulate_u2(
            tabulation.tabulation_rows(members, adjusted),
            data_provenance=data_provenance,
            design=cohort.design_frame(inputs, cohort.U2CohortSpec()),
            registration_pointer=registration_pointer,
            upstream_spec=adjusted.attrs["spec"],
        )
        out[f"real_interest_rate_{rate}"] = {
            "row": rows.HEADLINE_ROW,
            "scored": False,
            "cells": [
                {
                    key: cell.get(key)
                    for key in (
                        "cell",
                        "defined",
                        "n_observations",
                        "baseline_rate",
                        "reform_rate",
                        "delta",
                    )
                }
                for cell in table["cells"]
            ],
        }
    return out


def run_track_u2(
    inputs: cohort.U2Inputs,
    params: parameters.U2Parameters,
    *,
    data_provenance: str,
    role_context: sources.RoleContext,
    registration_pointer: str | None = None,
    row_set: Mapping[str, rows.U2Row] | None = None,
    source_gate: sources.SourceGate | None = None,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Every registered U2 row, the F17 diagnostics and the provenance."""

    row_set = rows.REGISTERED_ROWS if row_set is None else row_set
    if list(row_set) != list(rows.ROW_IDS):
        raise U2RunError(
            f"a U2 run computes exactly the ten rows {rows.ROW_IDS}; "
            "nothing is omitted or added"
        )
    check_headline(rows.HEADLINE_ROW)
    checks = check_inputs(
        inputs, data_provenance, registration_pointer, role_context
    )
    try:
        parameters.check_u2_parameters(params, data_provenance)
    except parameters.U2ParameterError as error:
        raise U2RunError(str(error)) from error
    say = progress or (lambda message: None)
    births = cohort.derive_u2_births(inputs)
    results: dict[str, Any] = {}
    headline: tuple[pd.DataFrame, pd.DataFrame, cohort.U2Cohort] | None = None
    for row_id, row in row_set.items():
        say(f"U2 row {row_id}")
        result, members, adjusted, built = _compute_row(
            row,
            inputs,
            params,
            births,
            role_context=role_context,
            data_provenance=data_provenance,
            registration_pointer=registration_pointer,
        )
        results[row_id] = result
        if row_id == rows.HEADLINE_ROW:
            headline = (members, adjusted, built)
    assert headline is not None
    members, adjusted, built = headline
    labels = list(ap.OUTPUT_LABELS)
    if data_provenance == ap.INVENTED:
        labels.insert(0, DRY_RUN_HEADER)
    return {
        "schema_version": RUN_SCHEMA_VERSION,
        "identity": identity.identity(),
        "statistic_id": identity.STATISTIC_ID,
        "data_provenance": data_provenance,
        "registration_pointer": registration_pointer,
        "labels": labels,
        "headline": {
            "row": rows.HEADLINE_ROW,
            "rule": rows.HEADLINE_RULE,
            "fallback_row": None,
        },
        "cohort_provenance": {
            key: value
            for key, value in built.provenance.items()
            if key != "psid_files_sha256"
        },
        "psid_files_sha256": dict(
            built.provenance.get("psid_files_sha256") or {}
        ),
        "role_context": role_context.kind,
        "source_gate": None if source_gate is None else source_gate.audit(),
        "parameters": params.provenance(),
        "input_checks": checks,
        "rows": results,
        "sensitivities_unscored": _sensitivity(
            members,
            inputs,
            params,
            role_context=role_context,
            data_provenance=data_provenance,
            registration_pointer=registration_pointer,
        ),
        "f17_diagnostics": {
            "row": rows.HEADLINE_ROW,
            "official_concept_poverty_rate": official_concept_rates(
                members, adjusted
            ),
            "components": diagnostics.component_diagnostics(built, inputs),
        },
        "comparator_column": identity.COMPARATOR_COLUMN,
        "comparator_interval": identity.COMPARATOR_INTERVAL,
        "report_rows_not_computed": {
            key: {**entry, "rows": list(entry["rows"])}
            for key, entry in tabulation.NOT_COMPUTED_REPORT_ROWS.items()
        },
        "named_deltas": list(rows.NAMED_DELTAS),
        "rulings": {
            "record": "U2_RULINGS",
            "decision_record": "d514",
            "ruled_on": "2026-09-28",
            "u1_rulings": "precedent_not_u2_execution_authorization",
            "entries": rows.U2_RULINGS,
        },
        "pending_decisions": _pending(),
    }
