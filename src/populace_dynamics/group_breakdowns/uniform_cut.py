"""Exercise 2 post hoc groups, composing frozen Track U and G1--G3.

Source locators: uniform_cut_track_u/runner.py:_compute_row and
run_track_u; estimates/group_breakdown.py:MINT8_SCHEME and
tabulate_poverty_breakdown; estimates/lifetime_measures.py. No PSID
reader is called here except through cohorts.age67/group_attributes.

Invariants: every registered row and F17 cell is reproduced bit-exactly
before any group attribute loader or lifetime calculation runs. All
observations are born in 1936--1945. Joins preserve observation identity,
order and weights. Group SEs use the full design; floors split the full
family-linked sample. Missing measures remain unavailable, never zero.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.cohorts import age67, psid2010
from populace_dynamics.cohorts import group_attributes as ga
from populace_dynamics.estimates import adjusted_poverty as ap
from populace_dynamics.estimates import group_breakdown as gb
from populace_dynamics.estimates import lifetime_measures as lm
from populace_dynamics.estimates import uniform_cut_tabulation as ut
from populace_dynamics.group_breakdowns.common import (
    POSTHOC_LABELS,
    GroupBreakdownRefusal,
    assert_exact_cells,
    assert_sha256,
)
from populace_dynamics.ss.params import SSAParameters
from populace_dynamics.uniform_cut_track_u import diagnostics, runner
from populace_dynamics.uniform_cut_track_u.rows import REGISTERED_ROWS

ROOT = Path(__file__).resolve().parents[3]
BASE_ARTIFACT = ROOT / "runs/replication_boomers2004_uniform_cut_v1.json"
BASE_ARTIFACT_SHA256 = (
    "48fb6cb108b09e19ed10c32586bd1b0d9521ec7746f693ba0241963ac24a4de3"
)
INPUT_FRAMES_SHA256 = (
    "43c41f444128ecf72ce9f8c5e64a7cda61a6fccaa2a58ff60ae7ce91356c4271"
)
SCHEMA_VERSION = "populace_dynamics.uniform_cut_groups_posthoc.v1"
INVENTED_HEADER = "INVENTED DATA - NOT A COMPARISON"
MEASURES = (
    "initial_aime_quintile",
    "lifetime_payroll_tax_quintile",
    "lifetime_payroll_tax_quintile_shared",
    "lifetime_earnings_own",
    "lifetime_earnings_shared",
)


@dataclass(frozen=True)
class ReplayedRow:
    """Frozen-pipeline outputs retained only in memory for group joins."""

    result: Mapping[str, Any]
    members: pd.DataFrame
    adjusted: pd.DataFrame
    design: pd.DataFrame


@dataclass(frozen=True)
class Replay:
    """A complete reproduction; contains no newly loaded attributes."""

    evidence: Mapping[str, Any]
    rows: Mapping[str, ReplayedRow]


@dataclass(frozen=True)
class LifetimeInputs:
    """G2 inputs, not a new measure implementation.

    Careers are observed PSID head/spouse earnings, without filling gaps.
    Taxes use G2's sourced combined OASDI taxes-paid series and trust-fund
    interest series. Missing spouse careers/rates remain not computed.
    """

    params: SSAParameters
    rates: Any = None
    interest: Any = None
    report_conventions: lm.ReportEarningsConventions = field(
        default_factory=lambda: lm.ReportEarningsConventions(
            missing_spouse=lm.MissingSpousePolicy.NOT_COMPUTED
        )
    )


def load_committed_artifact(path: Path = BASE_ARTIFACT) -> dict[str, Any]:
    """Read only the pinned model artifact; never comparator evidence."""

    assert_sha256(path, BASE_ARTIFACT_SHA256)
    artifact = json.loads(path.read_text())
    if artifact["cohort_provenance"]["input_frames_sha256"] != (
        INPUT_FRAMES_SHA256
    ):
        raise GroupBreakdownRefusal("committed input digest differs")
    return artifact


def check_observations(members: pd.DataFrame) -> None:
    """Refuse held-out births, repeated observations and invalid ages."""

    if members.empty or members["observation_id"].duplicated().any():
        raise GroupBreakdownRefusal("empty or duplicate observations")
    births = members["birth_year"]
    ages = members["member_age"]
    if members[["observation_id", "person_id"]].isna().any().any():
        raise GroupBreakdownRefusal("missing observation or person identity")
    if (
        births.isna().any()
        or not births.between(1936, 1945).all()
        or not (births % 1 == 0).all()
    ):
        raise GroupBreakdownRefusal("only 1936--1945 observations allowed")
    if not ages.isin((66, 67, 68)).all():
        raise GroupBreakdownRefusal("Track U observations must be 66--68")


def reexecute_track_u(
    inputs: age67.Age67Inputs,
    params: runner.TrackUParameters,
    *,
    data_provenance: str,
    original_pointer: str | None,
) -> Replay:
    """Run each frozen row exactly once, retaining its cohort outputs.

    Calls the frozen _compute_row directly (runner.py:479--559) so the
    income, tabulation, pending decisions and full design stay identical.
    The original pointer is used solely to reproduce old metadata.
    """

    checks = runner._check_inputs(
        inputs, data_provenance, original_pointer, False
    )
    runner._check_parameters(params, data_provenance)
    rows = {}
    headline = runner.headline_row(inputs)
    primary = None
    for row_id, row in REGISTERED_ROWS.items():
        if not row.built or runner.blocked_waves(row, inputs):
            raise GroupBreakdownRefusal(f"registered row {row_id} blocked")
        result, members, adjusted, cohort = runner._compute_row(
            row,
            inputs,
            params,
            data_provenance=data_provenance,
            registration_pointer=original_pointer,
            allow_blocked=False,
            tabulation_config=None,
        )
        check_observations(members)
        rows[row_id] = ReplayedRow(
            result,
            members,
            adjusted,
            runner.design_frame(inputs, row.age67_spec()),
        )
        if row_id == headline:
            primary = (members, adjusted, cohort)
    if primary is None:
        raise GroupBreakdownRefusal("headline not computed")
    members, adjusted, cohort = primary
    if data_provenance == ap.INVENTED:
        checks["invented_cohort"] = runner.invented.check_invented_cohort(
            cohort
        )
    evidence = {
        "cohort_provenance": {
            key: value
            for key, value in cohort.provenance.items()
            if key != "psid_files_sha256"
        },
        "psid_files_sha256": dict(
            cohort.provenance.get("psid_files_sha256") or {}
        ),
        "input_checks": checks,
        "rows": {key: value.result for key, value in rows.items()},
        "headline": {
            "row": headline,
            "rule": runner.HEADLINE_RULE,
            "wealth_refused_waves": sorted(inputs.wealth_refusals),
        },
        "parameters": params.provenance(),
        "f17_diagnostics": {
            "row": headline,
            "official_concept_poverty_rate": runner.official_concept_rates(
                members, adjusted
            ),
            "components": diagnostics.component_diagnostics(cohort, inputs),
        },
    }
    return Replay(evidence, rows)


def _join(left: pd.DataFrame, right: pd.DataFrame, key: str) -> pd.DataFrame:
    """An exact left join: no lost people, repeats or changed row order."""

    if right[key].duplicated().any():
        raise GroupBreakdownRefusal(f"duplicate side-frame {key}")
    if not set(left[key]).issubset(set(right[key])):
        raise GroupBreakdownRefusal(f"side frame missing {key}")
    overlap = (set(left) & set(right)) - {key}
    if overlap:
        raise GroupBreakdownRefusal(f"ambiguous side-frame columns {overlap}")
    result = left.merge(
        right, on=key, how="left", validate="many_to_one", sort=False
    )
    if not left[key].tolist() == result[key].tolist():
        raise GroupBreakdownRefusal("join changed observation order")
    result.attrs = deepcopy(left.attrs)
    return result


def _attribute_frame(
    members: pd.DataFrame, loader: Callable[..., ga.GroupAttributes]
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Resolve education at each observation wave through G1."""

    frames, provenance = [], []
    for wave, part in members.groupby("wave", sort=True):
        attributes = loader(
            part["person_id"].drop_duplicates().tolist(),
            anchor_waves=(int(wave),),
        )
        if attributes.provenance.get("content_sha256") != ga.content_sha256(
            attributes.frame
        ):
            raise GroupBreakdownRefusal("group attribute seal differs")
        side = attributes.frame[
            [
                "person_id",
                "race_ethnicity_mint8",
                "country_of_birth_mint8",
                "education_years",
            ]
        ].copy()
        side["race_ethnicity"] = side.pop("race_ethnicity_mint8").replace(
            {
                c.label: c.key
                for c in gb.MINT8_SCHEME.dimension("race_ethnicity").categories
            }
        )
        side["country_of_birth_group"] = side.pop(
            "country_of_birth_mint8"
        ).replace(
            {
                c.label: c.key
                for c in gb.MINT8_SCHEME.dimension(
                    "country_of_birth"
                ).categories
            }
        )
        frames.append(
            _join(part[["observation_id", "person_id"]], side, "person_id")
        )
        provenance.append(dict(attributes.provenance))
    combined = pd.concat(frames, ignore_index=True).drop(columns="person_id")
    return _join(members, combined, "observation_id"), provenance


def lifetime_frame(
    members: pd.DataFrame,
    inputs: age67.Age67Inputs,
    supplied: LifetimeInputs | None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Compute all five lifetime measures only with G2, by income year."""

    side = members[["observation_id"]].copy()
    if supplied is None:
        for name in MEASURES:
            side[name] = np.nan
        return side, {
            "status": "not computed",
            "reason": "SSA lifetime inputs not supplied",
        }
    careers = inputs.observed_earnings[
        ["person_id", "period", "earnings"]
    ].rename(columns={"period": "year"})
    rates = supplied.rates or lm.load_oasdi_tax_rates(
        basis=lm.TaxRateBasis.EMPLOYEE_EMPLOYER_PAID
    )
    interest = supplied.interest or lm.load_trust_fund_interest_rates()
    history_ids = set(inputs.marriage_history["person_id"])
    episodes = psid2010._episodes_with_separation(inputs.marriage_history)
    frames, records = [], []
    for year, part in members.groupby("income_year", sort=True):
        persons = part[["person_id", "birth_year"]].drop_duplicates()
        careers_to_date = careers[careers["year"] <= int(year)]
        results = {
            MEASURES[0]: lm.initial_aime_at_62(
                careers_to_date,
                persons,
                supplied.params,
                analysis_year=int(year),
                convention=lm.AIME_CONVENTIONS["mint8_initial_aime"],
            )
        }
        for shared in (False, True):
            suffix = "_shared" if shared else ""
            results[f"lifetime_payroll_tax_quintile{suffix}"] = (
                lm.lifetime_payroll_tax_pv_at_62(
                    careers_to_date,
                    persons,
                    supplied.params,
                    shared=shared,
                    rates=rates,
                    interest=interest,
                    marriage_episodes=episodes if shared else None,
                    missing_spouse=lm.MissingSpousePolicy.NOT_COMPUTED,
                    missing_rate=lm.MissingRatePolicy.NOT_COMPUTED,
                    marriage_history_person_ids=history_ids,
                )
            )
            results[f"lifetime_earnings_{'shared' if shared else 'own'}"] = (
                lm.report_average_indexed_earnings_22_62(
                    careers_to_date,
                    persons,
                    supplied.params,
                    shared=shared,
                    marriage_episodes=episodes if shared else None,
                    conventions=supplied.report_conventions,
                    marriage_history_person_ids=history_ids,
                )
            )
        joined = part[["observation_id", "person_id"]].copy()
        for name, measure in results.items():
            value = (
                "aime"
                if name == MEASURES[0]
                else (
                    "pv_at_62"
                    if "payroll" in name
                    else "average_indexed_earnings"
                )
            )
            frame = measure.frame.copy()
            unavailable = frame["status"] != lm.COMPUTED
            exclusions = {}
            if name.endswith("shared"):
                absent_history = frame["person_id"].map(
                    lambda pid: pid not in history_ids
                )
                unavailable |= absent_history
                exclusions["marriage_history_absent"] = int(
                    absent_history.sum()
                )
                for count in (
                    "years_marital_unknown",
                    "married_years_spouse_year_absent",
                    "married_years_own_year_absent",
                    "married_years_spouse_record_disagrees",
                    "years_multiple_marriages_in_force",
                ):
                    unavailable |= frame[count] > 0
                    exclusions[count] = int((frame[count] > 0).sum())
            frame.loc[unavailable, value] = np.nan
            joined = _join(
                joined,
                frame[["person_id", value]].rename(columns={value: name}),
                "person_id",
            )
            records.append(
                {
                    "income_year": int(year),
                    "dimension": name,
                    "provenance": dict(measure.provenance),
                    "n_unavailable": int(unavailable.sum()),
                    "adapter_exclusion_counts": exclusions,
                }
            )
        frames.append(joined.drop(columns="person_id"))
    return _join(
        side, pd.concat(frames, ignore_index=True), "observation_id"
    ), {
        "records": records,
        "coverage": (
            "observed head/spouse earnings only; missing ages unfilled; "
            "careers through each observation income year"
        ),
        "shared_history": (
            "absent marriage history is unavailable, not never married; "
            "unknown marital years, missing partner years and ambiguous "
            "marriage links are unavailable"
        ),
    }


def _scheme(row_id: str) -> gb.CategoryScheme:
    append = list(gb.LIFETIME_DIMENSIONS)
    for kind in ("own", "shared"):
        record = ut.NOT_COMPUTED_REPORT_ROWS[f"lifetime_earnings_{kind}"]
        append.append(
            gb.Dimension(
                key=f"lifetime_earnings_{kind}",
                label=record["section"],
                kind=gb.QUINTILE,
                categories=tuple(
                    gb.Category(f"quintile_{i}", label, rank=i)
                    for i, label in enumerate(record["rows"], 1)
                ),
                source=(
                    "estimates/uniform_cut_tabulation.py "
                    "NOT_COMPUTED_REPORT_ROWS"
                ),
                notes=(
                    "post hoc convention: 1st is lowest; cut over this "
                    "row's observation sample",
                ),
            )
        )
    replace = {}
    if row_id == "U1":
        replace["age"] = gb.Dimension(
            key="age",
            label="Age",
            kind=gb.BAND,
            categories=tuple(
                gb.Category(f"age_{age}", str(age), lower=age, upper=age)
                for age in (66, 67, 68)
            ),
            source=(
                "uniform_cut_track_u/rows.py U1; "
                "cohorts/age67.py observation_plan"
            ),
            notes=("U1 observes 66/67/68; U0 is exact age 67",),
        )
    return gb.derive_scheme(
        gb.MINT8_SCHEME,
        scheme_id=f"track_u_{row_id.lower().replace('-', '_')}_posthoc",
        title=(
            "Exercise 2 MINT8 groups with cohort and Report lifetime measures"
        ),
        append=append,
        replace=replace,
        population="Track U registered row, births 1936--1945 only",
        notes=(
            "household income quintiles use the analysis unit's baseline "
            "income, weighted across the observation sample; lifetime "
            "MINT quintiles within birth decades",
        ),
    )


def tabulate_row_groups(
    row_id: str,
    replayed: ReplayedRow,
    *,
    inputs: age67.Age67Inputs,
    attribute_loader: Callable[..., ga.GroupAttributes],
    lifetime_inputs: LifetimeInputs | None,
    data_provenance: str,
    registration_pointer: str | None,
) -> dict[str, Any]:
    """Join verified cohort outputs and delegate every new cell to G3."""

    members = replayed.members
    check_observations(members)
    frame, provenance = _attribute_frame(members, attribute_loader)
    measures, lifetime_provenance = lifetime_frame(
        members, inputs, lifetime_inputs
    )
    frame = _join(frame, measures, "observation_id")
    joined = ut.tabulation_rows(members, replayed.adjusted)
    frame = _join(
        joined,
        frame.drop(
            columns=[c for c in frame if c in joined and c != "observation_id"]
        ),
        "observation_id",
    )
    adjusted_side = replayed.adjusted[
        [
            "observation_id",
            "baseline_income",
            "money_income",
            "threshold",
            "cut",
            "ssi_offset",
            "ssi_new",
        ]
    ]
    frame = _join(frame, adjusted_side, "observation_id")
    frame["birth_cohort"] = lm.ten_year_birth_cohort(frame["birth_year"])
    frame["benefit_type_group"] = (
        members["benefit_type"].to_numpy()
        if "benefit_type" in members
        else None
    )
    scheme = _scheme(row_id)
    columns = {
        "sex": "sex",
        "race_ethnicity": "race_ethnicity",
        "country_of_birth": "country_of_birth_group",
        "age": "member_age",
        "marital_status": "marital_status_4",
        "education": "education_years",
        "poverty_status": "poverty_status_group",
        "household_income_quintile": "group_income",
        "benefit_type": "benefit_type_group",
        **{name: name for name in MEASURES},
    }
    result = {}
    seeds = replayed.result["tabulation"]["config"]["floor_seeds"]
    for concept in ("adjusted", "reported_money_official_style"):
        rows = frame.copy()
        if concept == "adjusted":
            rows["group_income"] = rows["baseline_income"]
        else:
            if "total_family_income" not in rows:
                result[concept] = {
                    "status": "not computed",
                    "reason": (
                        "cohort output lacks reported family money income"
                    ),
                    "labels": [*ap.OUTPUT_LABELS, *POSTHOC_LABELS],
                }
                continue
            rows["group_income"] = rows["total_family_income"]
            rows["poor_baseline"] = (
                rows["total_family_income"] < rows["threshold"]
            )
            rows["poor_reform"] = (
                rows["total_family_income"]
                - rows["cut"]
                + rows["ssi_offset"]
                + rows["ssi_new"]
            ) < rows["threshold"]
        rows["poverty_status_group"] = np.where(
            rows["poor_baseline"], "in_poverty", "above_poverty"
        )
        assignment = gb.assign_groups(
            rows,
            scheme,
            columns,
            key_columns=("observation_id",),
            quintile_partitions={
                name: ("birth_cohort",) for name in MEASURES[:3]
            },
            unclassified_codes={"marital_status": ("unclassified",)},
        )
        result[concept] = gb.tabulate_poverty_breakdown(
            rows,
            assignment,
            design=replayed.design,
            data_provenance=data_provenance,
            id_column="observation_id",
            floor_seeds=seeds,
            registration_pointer=registration_pointer,
            labels=ap.OUTPUT_LABELS,
            post_hoc_labels=POSTHOC_LABELS,
            statistic_id=ut.STATISTIC_ID,
            upstream={
                "row": row_id,
                "concept": concept,
                "official_style_caveat": (
                    "uses reported TOTAL FAMILY INCOME and the frozen "
                    "row's 65+ threshold, cut and SSI response; "
                    "head/wife sensitivity units can differ from the "
                    "family; not the Census householder-age convention"
                ),
            },
        ).as_dict()
    return {
        "labels": [*ap.OUTPUT_LABELS, *POSTHOC_LABELS],
        "groups": result,
        "attributes_provenance": provenance,
        "lifetime_provenance": lifetime_provenance,
        "frozen_row": dict(replayed.result.get("row", {})),
        "age67_spec": dict(replayed.result.get("age67_spec", {})),
        "income_spec": dict(replayed.result.get("income_spec", {})),
        "not_computed": (
            {}
            if "benefit_type" in members
            else {
                "benefit_type": (
                    "Track U cohort outputs have no Social Security type "
                    "flags; unavailable rows retained as unclassified"
                )
            }
        ),
        "age_note": (
            "U1 age dimension is 66/67/68; "
            "U0 and remaining rows are exact age 67"
        ),
    }


def build_uniform_cut_groups(
    inputs: age67.Age67Inputs,
    params: runner.TrackUParameters,
    committed: Mapping[str, Any],
    *,
    data_provenance: str,
    registration_pointer: str | None = None,
    attribute_loader: Callable[..., ga.GroupAttributes] | None = None,
    lifetime_inputs: LifetimeInputs | None = None,
    reexecute: Callable[..., Replay] = reexecute_track_u,
) -> dict[str, Any]:
    """Refuse before groups on any mismatch; this function writes nothing."""

    actual_digest = age67.input_frames_sha256(inputs)
    expected_digest = committed["cohort_provenance"]["input_frames_sha256"]
    if actual_digest != expected_digest or (
        data_provenance == ap.REGISTERED_REAL
        and expected_digest != INPUT_FRAMES_SHA256
    ):
        raise GroupBreakdownRefusal("Track U input digest mismatch")
    if data_provenance != committed["data_provenance"]:
        raise GroupBreakdownRefusal("committed data provenance differs")
    if data_provenance == ap.REGISTERED_REAL:
        if (
            not registration_pointer
            or not runner.REGISTRATION_POINTER.fullmatch(registration_pointer)
        ):
            raise GroupBreakdownRefusal(
                "groups require a new issue #42 pointer"
            )
        if registration_pointer == committed.get("registration_pointer"):
            raise GroupBreakdownRefusal(
                "groups require a new registration, not the original pointer"
            )
        assert_exact_cells(
            load_committed_artifact(),
            committed,
            path="pinned parent artifact",
        )
        assert_exact_cells(
            committed["psid_files_sha256"],
            inputs.provenance["psid_files_sha256"],
            path="PSID file hashes",
        )
    replay = reexecute(
        inputs,
        params,
        data_provenance=data_provenance,
        original_pointer=committed.get("registration_pointer"),
    )
    expected_rows = set(REGISTERED_ROWS)
    if (
        set(replay.rows) != expected_rows
        or set(committed["rows"]) != expected_rows
    ):
        raise GroupBreakdownRefusal("every registered row is required")
    for row in replay.rows.values():
        check_observations(row.members)
    check = assert_exact_cells(
        {key: committed[key] for key in replay.evidence},
        replay.evidence,
        path="frozen Track U reproduction",
    )
    # All reproduction checks finish before this first attribute read.
    if attribute_loader is None:
        side_inputs = ga.load_group_attribute_inputs()

        def attribute_loader(person_ids, *, anchor_waves):
            return ga.build_group_attributes(
                side_inputs, person_ids, anchor_waves=anchor_waves
            )

    results = {
        row_id: tabulate_row_groups(
            row_id,
            row,
            inputs=inputs,
            attribute_loader=attribute_loader,
            lifetime_inputs=lifetime_inputs,
            data_provenance=data_provenance,
            registration_pointer=registration_pointer,
        )
        for row_id, row in replay.rows.items()
    }
    return {
        "header": (
            INVENTED_HEADER
            if data_provenance == ap.INVENTED
            else "REGISTERED POST HOC GROUP BREAKDOWN - Track U exercise 2"
        ),
        "schema_version": SCHEMA_VERSION,
        "statistic_id": ut.STATISTIC_ID,
        "data_provenance": data_provenance,
        "registration_pointer": registration_pointer,
        "labels": [
            *(
                [INVENTED_HEADER, gb.INVENTED_DATA_LABEL]
                if data_provenance == ap.INVENTED
                else []
            ),
            *ap.OUTPUT_LABELS,
            *POSTHOC_LABELS,
        ],
        "reproduction": {
            "comparison": check.comparison,
            "absolute_tolerance": check.absolute_tolerance,
            "relative_tolerance": check.relative_tolerance,
            "compared_leaf_cells": check.compared_leaf_cells,
            "input_frames_sha256": actual_digest,
            "original_registration_pointer": committed.get(
                "registration_pointer"
            ),
            "all_registered_rows_checked_before_groups": True,
        },
        "named_deltas": list(runner.NAMED_DELTAS),
        "rows": results,
    }
