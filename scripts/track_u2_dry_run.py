"""U2 end-to-end DRY RUN on an INVENTED cohort (specification section 14).

INVENTED DATA - NOT A COMPARISON.  The cohort is the invented population
of :mod:`populace_dynamics.uniform_cut_track_u2.invented` (persons,
families, income, Social Security, SSI, wealth, employer DC, weights and
design all invented), run through the real U2 builder, income rows,
income concept and tabulation for all ten registered rows, with the
unscored two-percent interest sensitivity and the F17 diagnostics.  The
poverty thresholds are INVENTED as well; the committed U2 SSI capture and
life tables are the parameters used, and the pinned Track M Census
capture is loaded only to record its pin and its 2012 equality with U1.
No PSID file is opened and no comparator value is read.

The run applies the specification's declared role interpretation
(section 3) under the ``invented_declared`` gate, which exists only for
invented data.  The checks record the refusals the real path gives:

* every family-record mapping round-trips through the registry layouts
  (invented fixed-width records: losses, sentinels, top codes, the
  seven/eight-asset WEALTH1 identities, every employer-DC route);
* under the committed registries, the source gate refuses each wave the
  milestone-1 record leaves open, the registry role context refuses the
  TO VERIFY relationship codes, code 88 refuses under every context, and
  the loader's preflight refuses before any PSID file is opened;
* the registered runner refuses these invented inputs and parameters;
* each tested route from other data to the invented declared rules and
  routes refuses: relabelled or hand-copied invented provenance, frames
  sealed outside the generator, other frames joined to an invented
  cohort's rows, a registry role context carrying the declared rules,
  registries labelled committed but changed, survey-shaped records under
  declared specs, and the declared gate on a registered run (Python
  cannot stop deliberate private-attribute tampering; the cohort and the
  runner regenerate invented inputs, which such tampering does not
  survive);
* each of the generator's named variants reaches its branch or refusal
  (a code-88 cohabitor, a missing family record, a zero-weight legal
  spouse, an ambiguous pairing, a spouse-slot disagreement, a missing
  head);
* U2 refuses U1's captures, seed rule, column, rows and rulings, and
  U1's guards refuse U2's settings;
* the round-1 review's refusals: an undocumented individual-file sex or
  relationship code refuses the loader's value check, an undocumented
  relationship code has no OFUM rule, the registered preflight refuses
  while no frozen pre-registration evidence record exists (and none can
  be recorded from invented inputs), and the registered parameter check
  refuses an INVENTED altered threshold under the pinned label;
* the round-2 review's refusals: an INVENTED altered threshold, matrix
  cell or SSI FBR hidden behind a colliding key that holds the pinned
  value, and an SSI parameter subclass under the pinned label, each
  refuse the registered parameter check; an invented run naming a
  pre-registration evidence hash refuses the input guard;
* per-observation monotonicity (R <= B, poverty never lost) in every row
  and both halves of every split.

Usage::

    python scripts/track_u2_dry_run.py --output-dir <dir> [--seed N]

Writes ``result.json`` and ``RESULTS.md`` into ``--output-dir``.
"""

from __future__ import annotations

import argparse
import copy
import dataclasses
import datetime
import json
import math
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from populace_dynamics.cohorts import age67  # noqa: E402
from populace_dynamics.estimates import adjusted_poverty as ap  # noqa: E402
from populace_dynamics.uniform_cut_track_u2 import (  # noqa: E402
    DRY_RUN_HEADER,
    cohort,
    estimator,
    identity,
    invented,
    loader,
    parameters,
    rows,
    runner,
    sources,
    tabulation,
)

#: A syntactically valid pointer used only to show that the registered
#: path refuses invented inputs (no such comment is implied).
_GUARD_POINTER = (
    "https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
    "#issuecomment-0"
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def _refusal(call: Any) -> dict[str, Any]:
    try:
        call()
    except Exception as error:  # recorded, not swallowed
        return {
            "refused": True,
            "error": type(error).__name__,
            "message": str(error)[:600],
        }
    return {"refused": False}


def _invented_individual_raw(
    inputs: cohort.U2Inputs, registries: sources.RegistrySet
) -> pd.DataFrame:
    """The invented population as the individual reader's raw columns
    (one record per person at the registry variables; weights rounded to
    the documented whole-number field, a missing birth year as 9999)."""

    persons = inputs.persons.set_index("person_id")
    ids = persons.index.to_numpy(dtype=np.int64)
    design = inputs.design.set_index("person_id").loc[ids]
    values: dict[str, Any] = {
        "common.person_family_id": ids // 1000,
        "common.person_number": ids % 1000,
        "common.sex": persons["sex"].map({"male": 1, "female": 2, "na": 9}),
        "common.stratum": design["stratum"],
        "common.cluster": design["cluster"],
    }
    for wave, anchor in inputs.anchors.items():
        frame = anchor.set_index("person_id").loc[ids]
        for concept in loader.ANCHOR_CONCEPTS:
            column = frame[concept]
            if concept == "reported_birth_year":
                column = column.fillna(9999)
            elif concept == "weight":
                column = column.round()
            values[f"{wave}.{concept}"] = column
    return pd.DataFrame(
        {
            registries.entry("individual", key)["variable"]: np.asarray(
                value, dtype=np.int64
            )
            for key, value in values.items()
        }
    )


def _round_1_refusals(
    inputs: cohort.U2Inputs,
    params: parameters.U2Parameters,
    census: Any,
    registries: sources.RegistrySet,
    registry_roles: sources.RoleContext,
) -> dict[str, Any]:
    """The refusals the round-1 review of milestone 2 asked for, each on
    INVENTED inputs or an INVENTED altered value."""

    raw = _invented_individual_raw(inputs, registries)
    sex = registries.entry("individual", "common.sex")["variable"]
    relationship = registries.entry("individual", "2015.relationship")[
        "variable"
    ]
    undocumented_sex = raw.copy()
    undocumented_sex.loc[0, sex] = 5
    undocumented_relationship = raw.copy()
    undocumented_relationship.loc[0, relationship] = 99
    pinned = dataclasses.replace(params, thresholds=census)
    weighted = {
        year: dict(cells) for year, cells in census.weighted_average.items()
    }
    weighted[2014]["one_65_plus"] = 1.0  # INVENTED altered value
    altered = dataclasses.replace(
        pinned,
        thresholds=dataclasses.replace(census, weighted_average=weighted),
    )
    return {
        "invented_individual_values_documented": len(
            loader.check_individual_values(raw, registries)
        ),
        "undocumented_sex_code": _refusal(
            lambda: loader.check_individual_values(
                undocumented_sex, registries
            )
        ),
        "undocumented_relationship_code": _refusal(
            lambda: loader.check_individual_values(
                undocumented_relationship, registries
            )
        ),
        "undocumented_relationship_rule": _refusal(
            lambda: registry_roles.rule(2015, 99)
        ),
        "registered_preflight_without_evidence": _refusal(
            loader.read_preregistration_evidence
        ),
        "evidence_from_invented_inputs": _refusal(
            lambda: loader.preregistration_evidence(inputs)
        ),
        "pinned_parameters_pass_the_content_check": not _refusal(
            lambda: parameters.check_u2_parameters(pinned, ap.REGISTERED_REAL)
        )["refused"],
        "altered_threshold_under_the_pinned_label": _refusal(
            lambda: parameters.check_u2_parameters(altered, ap.REGISTERED_REAL)
        ),
    }


class _SsiSubclass(ap.SsiParameters):
    """Holds the pinned SSI fields but reports an INVENTED FBR."""

    def fbr_annual(self, year: int, couple: bool) -> float:
        return 12.0


def _round_2_refusals(
    inputs: cohort.U2Inputs,
    params: parameters.U2Parameters,
    census: Any,
) -> dict[str, Any]:
    """The refusals the round-2 review of milestone 2 asked for, each on
    INVENTED inputs or an INVENTED altered value under the pinned labels:
    a colliding key holding the pinned value beside an altered one, a
    parameter subclass, and an invented run naming an evidence hash."""

    pinned = dataclasses.replace(params, thresholds=census)

    def with_thresholds(name: str, table: Any) -> parameters.U2Parameters:
        return dataclasses.replace(
            pinned,
            thresholds=dataclasses.replace(census, **{name: table}),
        )

    weighted = copy.deepcopy(dict(census.weighted_average))
    weighted[2012.5] = copy.deepcopy(weighted[2012])
    weighted[2012]["one_65_plus"] = 1.0  # INVENTED altered value
    matrix = copy.deepcopy(dict(census.matrix))
    matrix[2016]["three"][0.5] = matrix[2016]["three"][0]
    matrix[2016]["three"][0] = 1.0  # INVENTED altered value
    couple = dict(pinned.ssi.fbr_couple_monthly)
    couple[2018.5] = couple[2018]
    couple[2018] = 1.0  # INVENTED altered value
    ssi_collision = dataclasses.replace(
        pinned,
        ssi=dataclasses.replace(pinned.ssi, fbr_couple_monthly=couple),
    )
    subclass = dataclasses.replace(
        pinned,
        ssi=_SsiSubclass(
            **{
                field.name: getattr(pinned.ssi, field.name)
                for field in dataclasses.fields(pinned.ssi)
            }
        ),
    )

    def registered(bundle: parameters.U2Parameters) -> dict[str, Any]:
        return _refusal(
            lambda: parameters.check_u2_parameters(bundle, ap.REGISTERED_REAL)
        )

    return {
        "pinned_parameters_pass_the_typed_content_check": not registered(
            pinned
        )["refused"],
        "colliding_year_key_under_the_pinned_label": registered(
            with_thresholds("weighted_average", weighted)
        ),
        "colliding_children_key_under_the_pinned_label": registered(
            with_thresholds("matrix", matrix)
        ),
        "colliding_ssi_year_under_the_pinned_label": registered(ssi_collision),
        "ssi_subclass_under_the_pinned_label": registered(subclass),
        "invented_run_naming_an_evidence_hash": _refusal(
            lambda: runner.check_inputs(
                inputs,
                ap.INVENTED,
                None,
                sources.RoleContext.declared(),
                preregistration_evidence_sha256="0" * 64,
            )
        ),
    }


def _mapping_checks(inputs: cohort.U2Inputs) -> dict[str, Any]:
    """Invented fixed-width records through every wave's registry layout."""

    registries = sources.RegistrySet.committed()
    out: dict[str, Any] = {}
    for wave in sources.SUPPORT_WAVES:
        declared = sources.SourceGate(sources.INVENTED_DECLARED, registries)
        records = invented.invented_fixed_width_records(inputs, wave, declared)
        parsed = loader.read_family_records(records["lines"], wave, declared)
        raw = records["raw"]
        reparsed = sources.parse_fixed_width(
            records["lines"], records["specs"]
        )
        route = sources.dc_route(wave, declared)
        identity_terms = sources.wealth1_identity(wave, declared)
        strict = sources.SourceGate(sources.REGISTRY, registries)
        out[str(wave)] = {
            "n_records": len(records["lines"]),
            "n_fields": len(records["specs"]),
            "round_trip_equal": bool(
                reparsed.equals(raw[[s.concept for s in records["specs"]]])
            ),
            "income_equal_to_invented_frame": bool(
                parsed["income"]
                .reset_index(drop=True)
                .equals(inputs.family_income[wave].reset_index(drop=True))
            ),
            "income_identity": parsed["income_identity"],
            "wealth1_identity": parsed["wealth1_identity"],
            "wealth1_asset_components": len(identity_terms["assets"]),
            "home_equity_excluded": identity_terms["excluded"],
            "negative_amounts_parsed": {
                concept: int((raw[concept] < 0).sum())
                for concept in (
                    "head_farm",
                    "head_business_asset",
                    "head_rent",
                    "wealth1",
                )
            },
            "top_coded_items": int((raw["head_dividends"] == 999_997).sum()),
            "spouse_age_dk_na": int((raw["wife_age"] == 999).sum()),
            "dc_route_declared": route.as_dict(),
            "dc_paths": {
                column: int(parsed["employer_dc"][column].sum())
                for column in sources.DC_BALANCE_COLUMNS
                if column != "employer_dc"
            },
            "dc_equal_to_invented_frame": bool(
                parsed["employer_dc"][list(sources.DC_BALANCE_COLUMNS)]
                .reset_index(drop=True)
                .equals(
                    inputs.employer_dc[wave][
                        list(sources.DC_BALANCE_COLUMNS)
                    ].reset_index(drop=True)
                )
            ),
            "would_refuse_under_registry_gate": len(declared.would_refuse),
            "registry_gate": _refusal(
                lambda wave=wave, strict=strict: loader.family_record_specs(
                    wave, strict
                )
            ),
            "registry_gate_dc_route": _refusal(
                lambda wave=wave, strict=strict: sources.dc_route(wave, strict)
            ),
        }
    malformed = inputs.family_income[2019].copy()
    return {
        "by_wave": out,
        "negative_where_undocumented_refused": _refusal(
            lambda: _parse_negative(inputs, registries)
        ),
        "crosswalk_as_input_refused": _refusal(
            lambda: sources.field_specs(
                "income",
                2019,
                ["wife_retirement_annuities"],
                sources.SourceGate(sources.INVENTED_DECLARED, registries),
            )
        ),
        "n_families_2019": int(len(malformed)),
    }


def _parse_negative(inputs: cohort.U2Inputs, registries: Any) -> None:
    gate = sources.SourceGate(sources.INVENTED_DECLARED, registries)
    records = invented.invented_fixed_width_records(inputs, 2019, gate)
    raw = records["raw"].copy()
    raw.loc[raw.index[0], "head_ss"] = -5
    lines = sources.encode_fixed_width(
        raw[[s.concept for s in records["specs"]]],
        records["specs"],
        filler=sources.INVENTED_RECORD_FILLER,
    )
    sources.parse_fixed_width(lines, records["specs"])


def _monotone(
    result: dict[str, Any], invariants: dict[str, Any]
) -> dict[str, Any]:
    """Every cell's change, full sample and each half, is at least zero."""

    out = {}
    for row_id, entry in result["rows"].items():
        table = entry["tabulation"]
        full = all(
            cell["delta"] >= -1e-12
            for cell in table["cells"]
            if cell["defined"]
        )
        halves = all(
            side[name]["delta"] >= -1e-12
            for seed in table["floor_per_seed"]
            for side in (seed["side_a"], seed["side_b"])
            for name in side
            if side[name]["defined"]
        )
        out[row_id] = {
            "per_observation": invariants[row_id],
            "cells_full_sample": full,
            "cells_both_halves_every_seed": halves,
        }
    return out


def _invariants(
    inputs: cohort.U2Inputs, params: parameters.U2Parameters
) -> dict[str, Any]:
    """Per-observation checks for every row, recomputed (not tabulated)."""

    context = sources.RoleContext.declared()
    births = cohort.derive_u2_births(inputs)
    out = {}
    for row_id, row in rows.REGISTERED_ROWS.items():
        built = cohort.build_u2_cohort(
            inputs, row.cohort_spec(), role_context=context, births=births
        )
        members = cohort.income_rows(built, inputs)
        spec = row.income_spec()
        adjusted = estimator.u2_adjusted_incomes(
            members,
            spec,
            context=estimator.U2EstimatorContext(context.kind),
            data_provenance=ap.INVENTED,
            life_table=params.life_tables[spec.mortality_basis],
            thresholds=params.thresholds,
            ssi=params.ssi,
        )
        zero = estimator.u2_adjusted_incomes(
            members,
            estimator.U2IncomeSpec(**{**row.income, "cut_rate": 0.0}),
            context=estimator.U2EstimatorContext(context.kind),
            data_provenance=ap.INVENTED,
            life_table=params.life_tables[spec.mortality_basis],
            thresholds=params.thresholds,
            ssi=params.ssi,
        )
        out[row_id] = {
            "reform_le_baseline": bool(
                (
                    adjusted["reform_income"]
                    <= adjusted["baseline_income"] + 1e-9
                ).all()
            ),
            "poverty_never_lost": bool(
                (~(adjusted["poor_baseline"] & ~adjusted["poor_reform"])).all()
            ),
            "ssi_offset_within_cut": bool(
                (
                    (adjusted["ssi_offset"] >= 0)
                    & (adjusted["ssi_offset"] <= adjusted["cut"] + 1e-9)
                ).all()
            ),
            "ssi_new_nonnegative": bool((adjusted["ssi_new"] >= 0).all()),
            "zero_cut_identity": bool(
                np.array_equal(zero["reform_income"], zero["baseline_income"])
                and (zero["poor_reform"] == zero["poor_baseline"]).all()
            ),
            "n_ssi_new_positive": int((adjusted["ssi_new"] > 0).sum()),
            "n_ssi_offset_positive": int((adjusted["ssi_offset"] > 0).sum()),
        }
    return out


#: The output column each one-field row changes (section 11), and the
#: unscored two-percent sensitivity's.
_ROW_FIELD_COLUMNS: dict[str, str] = {
    "U2": "ssi_offset",
    "U3": "ssi_new",
    "U4": "income_basis",
    "U5": "asset_income_removed",
    "U7": "employer_dc_added",
    "U8": "threshold_cell",
    "U9": "annuity_factor",
    "U10": "threshold_cell",
    "real_interest_rate_0.02": "annuity_factor",
}


def _row_branches(
    inputs: cohort.U2Inputs, params: parameters.U2Parameters
) -> dict[str, Any]:
    """How many U0 observations each row's one changed field moves.

    Evidence that every row's branch runs on the invented population
    (section 14: "exercise all ten rows"): each income-concept row is
    evaluated on U0's observations and compared with U0 in its own
    column; row U1 changes the population instead.
    """

    context = sources.RoleContext.declared()
    births = cohort.derive_u2_births(inputs)
    u0 = cohort.build_u2_cohort(
        inputs, cohort.U2CohortSpec(), role_context=context, births=births
    )
    u1 = cohort.build_u2_cohort(
        inputs,
        cohort.U2CohortSpec(row="U1"),
        role_context=context,
        births=births,
    )
    members = cohort.income_rows(u0, inputs)

    def estimate(spec: estimator.U2IncomeSpec) -> pd.DataFrame:
        return estimator.u2_adjusted_incomes(
            members,
            spec,
            context=estimator.U2EstimatorContext(context.kind),
            data_provenance=ap.INVENTED,
            life_table=params.life_tables[spec.mortality_basis],
            thresholds=params.thresholds,
            ssi=params.ssi,
        )

    base = estimate(estimator.U2IncomeSpec())
    specs = {
        row_id: rows.REGISTERED_ROWS[row_id].income_spec()
        for row_id in _ROW_FIELD_COLUMNS
        if row_id in rows.REGISTERED_ROWS
    }
    specs["real_interest_rate_0.02"] = estimator.U2IncomeSpec(
        real_interest_rate=0.02
    )
    out: dict[str, Any] = {
        "U1": {
            "field": "population",
            "n_observations_u0": int(len(u0.observations)),
            "n_observations_u1": int(len(u1.observations)),
            "n_birth_years_u1": int(u1.observations["birth_year"].nunique()),
        }
    }
    for name, spec in specs.items():
        column = _ROW_FIELD_COLUMNS[name]
        changed = estimate(spec)[column].to_numpy() != base[column].to_numpy()
        out[name] = {
            "field": column,
            "n_observations": int(len(base)),
            "n_changed_from_u0": int(changed.sum()),
        }
    return out


def _forged_committed(registries: sources.RegistrySet) -> None:
    """Registries labelled committed whose 2015 code-20 role entry has
    been edited to apply: refused (the label is bound to the pins)."""

    documents = copy.deepcopy(dict(registries.documents))
    for entry in documents["roles"]["entries"]:
        if entry["id"] == "2015.relationship.20":
            entry.pop("action", None)
            entry["blocking_dependencies"] = []
    sources.RegistrySet(documents, dict(registries.sha256), "committed")


def _invented_gate_refusals(
    inputs: cohort.U2Inputs,
    params: parameters.U2Parameters,
    registries: sources.RegistrySet,
) -> dict[str, Any]:
    """Each tested route from other data to the invented declared rules
    and routes, refused (the two u2m2 reviews' findings 1-5)."""

    declared = sources.RoleContext.declared()
    declared_gate = sources.SourceGate(sources.INVENTED_DECLARED, registries)
    records = invented.invented_fixed_width_records(
        inputs, 2019, declared_gate
    )
    survey_shaped = [
        line.replace(sources.INVENTED_RECORD_FILLER, " ")
        for line in records["lines"]
    ]
    labelled = cohort.replace_provenance(inputs, kind=cohort.PSID_FILES)
    doubled = dataclasses.replace(
        inputs,
        anchors={
            wave: frame.assign(weight=frame["weight"] * 2)
            for wave, frame in inputs.anchors.items()
        },
    )
    built = cohort.build_u2_cohort(inputs, role_context=declared)
    scaled = cohort.replace_provenance(
        dataclasses.replace(
            inputs,
            family_income={
                wave: frame.assign(
                    total_family_income=frame["total_family_income"] * 10
                )
                for wave, frame in inputs.family_income.items()
            },
        ),
        kind=cohort.CALLER_FRAMES,
    )
    return {
        "relabel_as_invented": _refusal(
            lambda: cohort.replace_provenance(inputs, kind=cohort.INVENTED)
        ),
        "hand_copied_invented_provenance": _refusal(
            lambda: cohort.build_u2_cohort(
                dataclasses.replace(
                    inputs, provenance=dict(inputs.provenance)
                ),
                role_context=declared,
            )
        ),
        "frames_sealed_outside_the_generator": _refusal(
            lambda: cohort.build_u2_cohort(
                invented._sealed(
                    doubled, seed=inputs.provenance["seed"], variant=None
                ),
                role_context=declared,
            )
        ),
        "other_frames_joined_to_an_invented_cohort": _refusal(
            lambda: cohort.income_rows(built, scaled)
        ),
        "declared_specs_on_survey_shaped_records": _refusal(
            lambda: sources.parse_fixed_width(survey_shaped, records["specs"])
        ),
        "unsealed_psid_files_label": _refusal(
            lambda: cohort.build_u2_cohort(
                labelled, role_context=sources.RoleContext.from_registry()
            )
        ),
        "registry_context_with_declared_rules": _refusal(
            lambda: sources.RoleContext(
                sources.REGISTRY, sources.declared_role_rules()
            )
        ),
        "changed_registries_labelled_committed": _refusal(
            lambda: _forged_committed(registries)
        ),
        "declared_gate_on_survey_shaped_records": _refusal(
            lambda: loader.read_family_records(
                survey_shaped, 2019, declared_gate
            )
        ),
        "declared_gate_on_a_registered_run": _refusal(
            lambda: runner.run_track_u2(
                labelled,
                params,
                data_provenance=ap.REGISTERED_REAL,
                role_context=sources.RoleContext.from_registry(),
                registration_pointer=_GUARD_POINTER,
                source_gate=declared_gate,
            )
        ),
    }


def _variants(
    inputs: cohort.U2Inputs, params: parameters.U2Parameters
) -> dict[str, Any]:
    """Each named invented variant's branch or refusal (section 13 role
    and refusal cases), regenerated and checked like the base."""

    declared = sources.RoleContext.declared()
    out: dict[str, Any] = {}
    for name in invented.INVENTED_VARIANTS:
        variant = invented.invented_variant(inputs, name)
        entry: dict[str, Any] = {
            "regenerated": runner.check_inputs(
                variant, ap.INVENTED, None, declared
            )["invented_inputs"]["regenerated"],
            "note": variant.provenance["variant_note"],
        }
        # Row U1's cells include U0's, so every variant's family is built.
        spec = cohort.U2CohortSpec(row="U1")
        try:
            built = cohort.build_u2_cohort(
                variant, spec, role_context=declared
            )
        except Exception as error:  # recorded, not swallowed
            entry["build"] = {
                "refused": True,
                "error": type(error).__name__,
                "message": str(error)[:600],
            }
            out[name] = entry
            continue
        obs = built.observations
        entry["build"] = {"refused": False, "n_observations": len(obs)}
        entry["legal_spouse_pairing"] = {
            str(k): int(v)
            for k, v in obs["legal_spouse_pairing"].value_counts().items()
        }
        entry["fu_head_spouse_age_source"] = {
            str(k): int(v)
            for k, v in obs["fu_head_spouse_age_source"].value_counts().items()
        }

        def income(built=built, variant=variant):
            members = cohort.income_rows(built, variant)
            return estimator.u2_adjusted_incomes(
                members,
                context=estimator.U2EstimatorContext(declared.kind),
                data_provenance=ap.INVENTED,
                life_table=params.life_tables["nchs_2000"],
                thresholds=params.thresholds,
                ssi=params.ssi,
            )

        entry["income"] = _refusal(income)
        out[name] = entry
    return out


def checks(
    seed: int, inputs: cohort.U2Inputs, params: parameters.U2Parameters
) -> dict[str, Any]:
    """The dry run's checks, each recorded (none computes a PSID value)."""

    block = rows.specification_block()
    registries = sources.RegistrySet.committed()
    registry_roles = sources.RoleContext.from_registry(registries)
    declared = sources.RoleContext.declared()
    census = parameters.load_u2_thresholds()
    u1_bound = parameters.U2Parameters(
        thresholds=ap.load_poverty_thresholds(),
        ssi=params.ssi,
        life_tables=params.life_tables,
    )
    u1_ssi = parameters.U2Parameters(
        thresholds=census,
        ssi=ap.load_ssi_parameters(),
        life_tables=params.life_tables,
    )
    births = cohort.derive_u2_births(inputs)
    u0 = cohort.build_u2_cohort(
        inputs, cohort.U2CohortSpec(), role_context=declared, births=births
    )
    u1 = cohort.build_u2_cohort(
        inputs,
        cohort.U2CohortSpec(row="U1"),
        role_context=declared,
        births=births,
    )
    shared = u0.observations.merge(
        u1.observations, on="observation_id", suffixes=("_u0", "_u1")
    )
    same_attributes = all(
        shared[f"{column}_u0"]
        .astype(str)
        .equals(shared[f"{column}_u1"].astype(str))
        for column in (
            "birth_year",
            "fu_head_age",
            "fu_head_spouse_age",
            "fu_head_spouse_person_id",
            "marital_status_4",
            "member_role",
        )
    )
    code88 = invented.with_code_88_cohabitor(inputs)
    return {
        "specification_rows": rows.check_rows_against_block(block),
        "named_deltas": rows.check_named_deltas_against_specification(),
        "u2_rulings_against_block": _refusal(
            lambda: rows.check_u2_rulings_against_block(block)
        ),
        "plans": {
            "u0_pairs": len(cohort.observation_plan(cohort.U2CohortSpec())),
            "u1_pairs": len(
                cohort.observation_plan(cohort.U2CohortSpec(row="U1"))
            ),
            "u1_birth_years": len(
                {
                    b
                    for b, *_ in cohort.observation_plan(
                        cohort.U2CohortSpec(row="U1")
                    )
                }
            ),
            "support_registry": cohort.check_plan_against_support_registry(
                registries
            ),
            "wave_2013_cells": [
                list(cell)
                for cell in cohort.plan_cells(cohort.U2CohortSpec(row="U1"))
                if cell[1] == 2013
            ],
        },
        "identification": {
            "shared_observations": int(len(shared)),
            "identical_births_and_annuitant_attributes": bool(same_attributes),
        },
        "mapping": _mapping_checks(inputs),
        "role_refusals": {
            "registry_context_on_invented_inputs": _refusal(
                lambda: cohort.build_u2_cohort(
                    inputs, role_context=registry_roles, births=births
                )
            ),
            "code_88_under_declared_context": _refusal(
                lambda: cohort.build_u2_cohort(code88, role_context=declared)
            ),
            "declared_context_on_non_invented_inputs": _refusal(
                lambda: cohort.build_u2_cohort(
                    cohort.replace_provenance(inputs, kind="caller_frames"),
                    role_context=declared,
                )
            ),
            "registry_rules_equal_declared_where_resolved": all(
                registry_roles.rules[key].as_dict()
                == declared.rules[key].as_dict()
                for key, rule in registry_roles.rules.items()
                if rule.refusal is None
            ),
            # Every relationship code the committed roles registry
            # refuses, each by its own registry entry.
            "registry_rule_refusals": {
                f"{wave}.{code}": _refusal(
                    lambda wave=wave, code=code: registry_roles.rule(
                        wave, code
                    )
                )
                for (wave, code), rule in sorted(registry_roles.rules.items())
                if rule.refusal
            },
            "invented_members_with_refused_codes": {
                f"{wave}.{code}": int(
                    inputs.anchors[wave]["sequence"]
                    .between(1, 20)
                    .mul(inputs.anchors[wave]["relationship"].eq(code))
                    .sum()
                )
                for (wave, code), rule in sorted(registry_roles.rules.items())
                if rule.refusal and rule.present
            },
        },
        "invented_gate_refusals": _invented_gate_refusals(
            inputs, params, registries
        ),
        "invented_variants": _variants(inputs, params),
        "loader_preflight": _refusal(loader.source_preflight),
        "registered_guard_refuses_invented_inputs": _refusal(
            lambda: runner.run_track_u2(
                inputs,
                params,
                data_provenance=ap.REGISTERED_REAL,
                role_context=registry_roles,
                registration_pointer=_GUARD_POINTER,
            )
        ),
        "registered_parameter_check_refuses_invented_thresholds": _refusal(
            lambda: parameters.check_u2_parameters(params, ap.REGISTERED_REAL)
        ),
        "round_1_refusals": _round_1_refusals(
            inputs, params, census, registries, registry_roles
        ),
        "round_2_refusals": _round_2_refusals(inputs, params, census),
        "census_capture": {
            "sha256": census.provenance["sha256"],
            "overlap_2012": census.provenance["overlap_2012"],
            "weighted_average_unit_dollars_2022": census.provenance[
                "weighted_average_unit_dollars_2022"
            ],
            "required_income_years": census.provenance[
                "required_income_years"
            ],
            "used_by_this_dry_run": False,
        },
        "cross_cohort_refusals": {
            "u1_threshold_capture_under_u2": _refusal(
                lambda: parameters.check_u2_parameters(u1_bound, ap.INVENTED)
            ),
            "u1_ssi_capture_under_u2": _refusal(
                lambda: parameters.check_u2_parameters(u1_ssi, ap.INVENTED)
            ),
            "u1_seed_rule_under_u2": _refusal(
                lambda: cohort.U2CohortSpec(
                    seed_wave_rule=identity.U1_SEED_WAVE_RULE
                )
            ),
            "u0_f_under_u2": _refusal(lambda: cohort.U2CohortSpec(row="U0-F")),
            "u1_column_under_u2": _refusal(
                lambda: tabulation.U2TabulationConfig(
                    comparator_column=identity.U1_COMPARATOR_COLUMN
                )
            ),
            "u1_specification_under_u2": _refusal(
                lambda: rows.specification_block(
                    identity.U1_SPECIFICATION_PATH
                )
            ),
            "u1_rulings_under_u2": _refusal(
                lambda: rows.check_u2_rulings_against_block(
                    {
                        "decisions": {
                            "ruled_by": "Max",
                            "ruled_on": "2026-09-26",
                            "decision_record": "d411",
                        }
                    }
                )
            ),
            "u2_seed_rule_under_u1": _refusal(
                lambda: age67.Age67Spec(seed_wave_rule=cohort.SEED_WAVE_RULE)
            ),
            "fallback_headline_under_u2": _refusal(
                lambda: runner.check_headline("U0-F")
            ),
        },
        "invariants": _invariants(inputs, params),
        "row_branches": _row_branches(inputs, params),
    }


def _fmt(value: Any, digits: int = 2) -> str:
    if value is None or (
        isinstance(value, float) and not math.isfinite(value)
    ):
        return "undefined"
    return f"{value:.{digits}f}"


def _cell(table: dict[str, Any], name: str) -> dict[str, Any]:
    return next(c for c in table["cells"] if c["cell"] == name)


def _cell_line(label: str, cell: dict[str, Any]) -> str:
    if not cell["defined"]:
        return (
            f"| {label} | {cell['n_observations']} | undefined "
            f"({cell['undefined_reason']}) | | | | |"
        )
    floor = cell["floor"]["delta"]
    se = cell.get("design_se", {}).get("delta", {}).get("se")
    return (
        f"| {label} | {cell['n_observations']} "
        f"| {_fmt(cell['baseline_rate'])} | {_fmt(cell['reform_rate'])} "
        f"| {_fmt(cell['delta'])} "
        f"| {_fmt(floor['mean']) if floor['defined'] else 'undefined'} "
        f"| {_fmt(se)} |"
    )


def results_markdown(result: dict[str, Any]) -> str:
    run = result["run"]
    provenance = result["cohort_provenance"]
    check = result["checks"]
    lines = [
        f"# {DRY_RUN_HEADER}",
        "",
        f"U2 (Boomers 2004, column {result['comparator_column']}) invented "
        f"end-to-end dry run, {run['date']}. Every person, family, amount, "
        "weight and sampling stratum and cluster is **invented** "
        "(`populace_dynamics.uniform_cut_track_u2.invented`, seed "
        f"{provenance['seed']}); so are the poverty thresholds. No PSID "
        "file was opened, no comparator value was read, and nothing below "
        "is a result, a forecast or a comparison with DYNASIM.",
        "",
        "Labels: "
        + "; ".join(f"*{label}*" for label in result["labels"])
        + ".",
        "",
        "## What ran",
        "",
        "- The invented cohort through the U2 builder, income rows, income "
        "concept and tabulation for all ten rows ("
        + ", ".join(result["rows"])
        + "), under the declared section 3 role interpretation "
        f"(`{result['role_context']}`, invented data only).",
        f"- Headline: row {result['headline']['row']} "
        f"(`{result['headline']['rule']}`; no fallback).",
        "- Parameters: the committed U2 SSI capture and life tables; "
        "**invented** thresholds (the pinned Track M Census capture is "
        "loaded only to record its pin and 2012 equality with U1).",
        "",
        "## Invented-data tabulation (not a comparison)",
        "",
        "Cell `all` of each row: observations, P_B, P_R, Δ = P_R − P_B "
        "(percentage points), the mean half-split floor of Δ and its "
        "design-based SE. These numbers describe invented data only.",
        "",
        "| Row | Observations | P_B | P_R | Δ | Δ floor | Δ design SE |",
        "|---|---|---|---|---|---|---|",
    ]
    for row_id, entry in result["rows"].items():
        lines.append(_cell_line(row_id, _cell(entry["tabulation"], "all")))
    table = result["rows"]["U0"]["tabulation"]
    design = table["design"]
    lines += [
        "",
        f"Row U0 design: {design.get('n_strata')} invented strata, "
        f"{design.get('n_clusters')} clusters, singleton strata "
        f"{design.get('singleton_strata')}.",
        "",
        "### Row U0 by cell (invented)",
        "",
        "| Cell | Observations | P_B | P_R | Δ | Δ floor | Δ design SE |",
        "|---|---|---|---|---|---|---|",
    ]
    for cell in table["cells"]:
        lines.append(_cell_line(cell["cell"], cell))
    sensitivity = result["sensitivities_unscored"]
    lines += ["", "## Unscored sensitivity (invented)", ""]
    for name, entry in sensitivity.items():
        cell = next(c for c in entry["cells"] if c["cell"] == "all")
        lines.append(
            f"- {name} on {entry['row']}: cell `all` Δ "
            f"{_fmt(cell['delta'])} (not scored)."
        )
    mapping = check["mapping"]["by_wave"]
    identical = check["identification"][
        "identical_births_and_annuitant_attributes"
    ]
    role = check["role_refusals"]
    thresholds_refused = check[
        "registered_parameter_check_refuses_invented_thresholds"
    ]["refused"]
    round_1 = check["round_1_refusals"]
    round_2 = check["round_2_refusals"]
    u1_branch = check["row_branches"]["U1"]
    lines += [
        "",
        "## Checks",
        "",
        f"- Rows equal the section 15 block "
        f"({check['specification_rows']['specification_version']}): "
        f"{check['specification_rows']['rows_equal_the_block']}; named "
        f"deltas equal section 12: "
        f"{check['named_deltas']['equal_to_section_12']}.",
        "- U2 rulings record against the draft block: refused "
        f"{check['u2_rulings_against_block']['refused']} (section 20 step 5 "
        "materializes it).",
        f"- Plans: U0 {check['plans']['u0_pairs']} pairs; U1 "
        f"{check['plans']['u1_pairs']} pairs over "
        f"{check['plans']['u1_birth_years']} birth years; equal to the "
        "support registry: "
        f"{check['plans']['support_registry']['equal_to_support_registry']}; "
        f"wave 2013 cells {check['plans']['wave_2013_cells']}.",
        "- Shared U0/U1 observations have identical births and annuitant "
        f"attributes: {identical}.",
        "- Mapping round trips (invented fixed-width records in each "
        "wave's registry layout): "
        + ", ".join(
            f"{wave} {entry['round_trip_equal']}"
            f"/{entry['income_equal_to_invented_frame']}"
            f"/{entry['dc_equal_to_invented_frame']}"
            for wave, entry in mapping.items()
        )
        + "; WEALTH1 asset components "
        + ", ".join(
            f"{wave}: {entry['wealth1_asset_components']}"
            for wave, entry in mapping.items()
        )
        + ".",
        "- Under the committed registries the source gate refuses: "
        + ", ".join(
            f"{wave} {entry['registry_gate']['refused']}"
            for wave, entry in mapping.items()
        )
        + ".",
        "- Role refusals: registry context on invented inputs "
        f"{role['registry_context_on_invented_inputs']['refused']};"
        " code 88 under the declared context "
        f"{role['code_88_under_declared_context']['refused']};"
        " declared context on non-invented inputs "
        f"{role['declared_context_on_non_invented_inputs']['refused']}.",
        "- Loader preflight refuses before any PSID file is opened: "
        f"{check['loader_preflight']['refused']}.",
        "- Tested routes from other data to the invented declared rules "
        "and routes, each refused: "
        + ", ".join(
            f"{name} {entry['refused']}"
            for name, entry in check["invented_gate_refusals"].items()
        )
        + ".",
        "- Named invented variants (build refused / income refused): "
        + ", ".join(
            f"{name} {entry['build']['refused']}/"
            f"{entry.get('income', {}).get('refused', 'n/a')}"
            for name, entry in check["invented_variants"].items()
        )
        + ".",
        "- The registered runner refuses these invented inputs: "
        f"{check['registered_guard_refuses_invented_inputs']['refused']}; "
        "the registered parameter check refuses invented thresholds: "
        f"{thresholds_refused}.",
        "- Cross-cohort refusals: "
        + ", ".join(
            f"{name} {entry['refused']}"
            for name, entry in check["cross_cohort_refusals"].items()
        )
        + ".",
        "- Round-1 review refusals (invented; "
        f"{round_1['invented_individual_values_documented']} individual "
        "fields documented; the pinned parameters pass the content check: "
        f"{round_1['pinned_parameters_pass_the_content_check']}): "
        + ", ".join(
            f"{name} {entry['refused']}"
            for name, entry in round_1.items()
            if isinstance(entry, dict)
        )
        + ".",
        "- Round-2 review refusals (invented; the pinned parameters pass "
        "the typed content check: "
        f"{round_2['pinned_parameters_pass_the_typed_content_check']}): "
        + ", ".join(
            f"{name} {entry['refused']}"
            for name, entry in round_2.items()
            if isinstance(entry, dict)
        )
        + ".",
        "- Per-observation monotonicity and SSI bounds, every row: "
        + ", ".join(
            f"{row_id} "
            + str(
                all(
                    value
                    for key, value in entry.items()
                    if not key.startswith("n_")
                )
            )
            for row_id, entry in check["invariants"].items()
        )
        + "; cells in both halves of every split: "
        + ", ".join(
            f"{row_id} {entry['cells_both_halves_every_seed']}"
            for row_id, entry in result["monotonicity"].items()
        )
        + ".",
        "- Row branches on U0's invented observations (observations whose "
        "changed field differs from U0): "
        + ", ".join(
            f"{name} {entry['n_changed_from_u0']}/{entry['n_observations']}"
            f" ({entry['field']})"
            for name, entry in check["row_branches"].items()
            if name != "U1"
        )
        + "; U1 "
        f"{check['row_branches']['U1']['n_observations_u1']} observations "
        f"over {check['row_branches']['U1']['n_birth_years_u1']} birth "
        f"years against U0's {u1_branch['n_observations_u0']}.",
        "",
        "## Named deltas",
        "",
    ]
    lines += [f"- {delta}." for delta in result["named_deltas"]]
    lines += [
        "",
        "## Provenance",
        "",
        f"- Code: `{run['git_head']}` (worktree clean: {run['git_clean']}).",
        f"- Invented inputs: generator `{provenance['generator']}`, seed "
        f"{provenance['seed']}, frames SHA-256 "
        f"`{provenance['input_frames_sha256']}`.",
        f"- SSI: sha256 `{result['parameters']['ssi']['sha256']}`.",
        f"- Python {run['python']}; command `{run['command']}`.",
        "",
    ]
    return "\n".join(lines)


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_json_ready(v) for v in value]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if value is pd.NA:
        return None
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=invented.DEFAULT_SEED)
    args = parser.parse_args(argv)

    params = parameters.committed_u2_parameters(
        invented.invented_poverty_thresholds()
    )
    inputs = invented.invented_u2_inputs(seed=args.seed)
    gate = sources.SourceGate(
        sources.INVENTED_DECLARED, sources.RegistrySet.committed()
    )
    for wave in sources.SUPPORT_WAVES:
        loader.family_record_specs(wave, gate)
        sources.dc_route(wave, gate)
    result = runner.run_track_u2(
        inputs,
        params,
        data_provenance=ap.INVENTED,
        role_context=sources.RoleContext.declared(),
        source_gate=gate,
        progress=lambda message: print(message, file=sys.stderr),
    )
    recorded = checks(args.seed, inputs, params)
    result = {
        "header": DRY_RUN_HEADER,
        **result,
        "monotonicity": _monotone(result, recorded["invariants"]),
        "checks": recorded,
        "run": {
            "date": datetime.date.today().isoformat(),
            "invented_seed": args.seed,
            "git_head": _git("rev-parse", "HEAD"),
            "git_clean": _git("status", "--porcelain") == "",
            "python": platform.python_version(),
            "command": " ".join(
                [
                    "python",
                    "scripts/track_u2_dry_run.py",
                    *(sys.argv[1:] if argv is None else argv),
                ]
            ),
        },
    }
    result = _json_ready(result)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "result.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "RESULTS.md").write_text(
        results_markdown(result), encoding="utf-8"
    )
    print(args.output_dir / "result.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
