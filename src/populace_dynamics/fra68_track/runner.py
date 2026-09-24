"""Run exercise 3 (FRA to 68) on Track A's projection: rows F0-F8 via A7.

:func:`run_fra68` projects each population once per draw with Track A's
projection (``cola_track_a.runner._project_population``, unchanged; it
reads only the draw indices and the reference year of the Track A
configuration :meth:`FRA68Config.track_a_config` builds), computes a
baseline scenario and one reform scenario per distinct reform setting
from that one projected state (:mod:`~populace_dynamics.fra68_track.
benefits`), pairs them into union rows and tabulates every registered row
with the A7 five-group statistic under exercise 3's identifier.  Rows
F0-F7 read the 2011-wave cohort (opening 2010, 20 periods); F8 reads the
2009-wave cohort (opening 2008, 22 periods), passed in
``TrackAInputs.additional_cohorts``.  With the same inputs, seeds and
Track A configuration the projection is exercise 1's, path for path
(:func:`projection_identity_record` compares the draw diagnostics with the
committed exercise-1 artifact in a registered run; the record never
refuses).

Membership is scenario-specific in every row (A7
``membership_basis="scenario_specific"`` with
``allow_membership_difference=True``).  Under the fixed claiming
convention C0 the two memberships must coincide, and the runner refuses a
C0 row whose A7 input summary says they do not.

Checks carried over from Track A (``cola_track_a.runner``): the
parameter-consistency checks and, for a ``registered_real`` cohort or on
request, the value checks against the committed captures (the baseline
bundle is bound to the committed statutory capture; each reform bundle is
derived from it and recorded with its own SHA-256); the source-provenance
and seal checks; the output-label check.  Exercise 1's COLA floor and
splice checks become one record: both scenarios read the same baseline
COLA path object.

Governance interlock: a ``registered_real`` cohort is refused unless a
registration pointer (the issue #42 comment) is supplied, the E1
specification block (``docs/design/urban2010_fra68_comparison.md``
section 21) is ratified, lists no decision awaiting Max, records his
ruling on every d188 decision field under ``decisions`` with the
configuration following each, and equals the code and the configuration
(schedules, primary schedule, rows, C1 anchor age).  A7 refuses the missing pointer
independently.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.cola_track_a import runner as track_runner
from populace_dynamics.cola_track_a.adapters import claiming_schedule
from populace_dynamics.cola_track_a.benefits import (
    BenefitContext,
    StateLookups,
)
from populace_dynamics.cola_track_a.config import (
    REGISTERED_ROWS as TRACK_A_ROWS,
)
from populace_dynamics.cola_track_a.config import (
    builder_defaults as track_a_builder_defaults,
)
from populace_dynamics.cola_track_a.config import (
    max_rulings as track_a_max_rulings,
)
from populace_dynamics.cola_track_a.runner import TrackAInputs
from populace_dynamics.engine.di_entitlement import (
    fra_attainment_year,
    fra_schedule_from_parameters,
)
from populace_dynamics.engine.di_entitlement_rates import SEXES
from populace_dynamics.engine.loop import ProjectionResult
from populace_dynamics.estimates.cola_age_profile import (
    DEFAULT_AGE_GROUPS,
    REGISTERED_REAL,
    SCENARIO_SPECIFIC,
    ColaAgeProfileConfig,
    ColaTabulationError,
    tabulate_cola_age_profile,
)
from populace_dynamics.fra68_track.benefits import (
    PersonScenario,
    Scenario,
    scenario_benefits,
    union_benefit_rows,
)
from populace_dynamics.fra68_track.config import (
    PENDING_DECISIONS,
    STATISTIC_ID,
    TRACK_A_ROW_BY_WAVE,
    ClaimingResponse,
    FRA68Config,
    FRA68Row,
    SurvivorRetirementAge,
    builder_defaults,
    decision_value,
    pending_decisions,
    row_labels,
)
from populace_dynamics.fra68_track.reform import (
    SCHEDULES,
    parameters_fra_sha256,
    reform_parameters,
)
from populace_dynamics.ss.params import SSAParameters

__all__ = [
    "E1_SPECIFICATION_PATH",
    "EXERCISE_1_ARTIFACT_PATH",
    "SCHEMA_VERSION",
    "UNRATIFIED_MARKERS",
    "check_specification_for_registered_run",
    "e1_parameter_block",
    "projection_identity_record",
    "run_fra68",
    "specification_code_check",
]

SCHEMA_VERSION = "populace_dynamics.fra68_track.run.v1"
SPECIFICATION_ID = "urban2010_fra68_exercise3"
_ROOT = Path(__file__).resolve().parents[3]
E1_SPECIFICATION_PATH = (
    _ROOT / "docs" / "design" / "urban2010_fra68_comparison.md"
)
EXERCISE_1_ARTIFACT_PATH = (
    _ROOT / "runs" / "replication_urban2010_cola_v1.json"
)
#: Markers of a specification status or version that is not ratified.
UNRATIFIED_MARKERS = (
    "candidate",
    "draft",
    "not_merged",
    "not_ratified",
    "referee",
)
_COLA_RECORD_YEARS = range(1975, 2031)


def e1_parameter_block(path: Path = E1_SPECIFICATION_PATH) -> dict:
    """The machine-readable block of the E1 specification (section 21)."""

    text = Path(path).read_text(encoding="utf-8")
    match = re.search(
        r"## 21\. Machine-readable parameter block.*?```json\n(.*?)\n```",
        text,
        flags=re.S,
    )
    if match is None:
        raise ValueError(f"no section 21 JSON block in {path}")
    return json.loads(match.group(1))


def specification_code_check(
    block: Mapping[str, Any], config: FRA68Config
) -> dict[str, Any]:
    """Whether the E1 block and the code agree (recorded in every run).

    Compares the specification identifier, the three frozen schedules,
    the primary schedule, the rows (each alternative's one changed field
    and value), the C1 anchor age (``claiming.C1.anchor_age`` against
    ``FRA68Config.c1_anchor_age``) and the statistic identifier.
    """

    mismatches: list[str] = []
    if block.get("specification") != SPECIFICATION_ID:
        mismatches.append("specification")
    schedules = block.get("schedules", {})
    for sid, schedule in SCHEDULES.items():
        declared = schedules.get(sid, {})
        table = declared.get("months_by_year_turning_62")
        if table != schedule.as_dict()["months_by_year_turning_62"]:
            mismatches.append(f"schedule_{sid}")
    if block.get("primary_schedule") != config.primary_schedule_id:
        mismatches.append("primary_schedule")
    rows = block.get("rows", {})
    registered = config.registered
    if sorted(rows) != sorted(registered):
        mismatches.append("row_set")
    for row_id, row in registered.items():
        declared = {**rows.get("F0", {}), **rows.get(row_id, {})}
        expected = row.as_dict()
        for key in (
            "schedule",
            "survivor_retirement_age",
            "claiming_response",
            "statistic",
            "components",
            "population",
        ):
            if declared.get(key) != expected[key]:
                mismatches.append(f"{row_id}.{key}")
    # Row F3's claiming response is defined by its anchor age, which the
    # block freezes under claiming.C1 and the configuration carries.
    anchor = block.get("claiming", {}).get("C1", {}).get("anchor_age")
    if anchor != config.c1_anchor_age:
        mismatches.append("claiming.C1.anchor_age")
    if block.get("statistic_id") != STATISTIC_ID:
        mismatches.append("statistic_id")
    return {
        "specification_version": block.get("version"),
        "specification_status": block.get("status"),
        "consistent": not mismatches,
        "mismatches": mismatches,
    }


def check_specification_for_registered_run(
    block: Mapping[str, Any], config: FRA68Config
) -> None:
    """Refuse a real-data run the E1 specification does not authorize.

    The block must be ratified (no candidate, draft, referee or
    not-merged marker in its status or version), must list no decision
    awaiting Max, must record Max's ruling on every d188 decision field
    under ``decisions`` (``{field: {"ruling": value, ...}}``) with the
    configuration following each ruling, and must agree with the code.
    """

    for name in ("status", "version"):
        value = str(block.get(name, ""))
        if not value or any(mark in value for mark in UNRATIFIED_MARKERS):
            raise ValueError(
                f"the E1 specification {name} is {value!r}: it authorizes no "
                "real-data run until Max ratifies it by merging, and the "
                "ratified text must say so in its section 21 block"
            )
    awaiting = block.get("decisions_awaiting_max")
    if awaiting:
        raise ValueError(
            "the E1 specification still lists decisions awaiting Max "
            f"({sorted(awaiting)}; decision record d188): no real-data "
            "statistic before he rules"
        )
    rulings = block.get("decisions") or {}
    unruled = [
        name
        for name in PENDING_DECISIONS
        if not isinstance(rulings.get(name), Mapping)
        or "ruling" not in rulings[name]
    ]
    if unruled:
        raise ValueError(
            "the E1 specification records no ruling by Max for "
            f"{unruled} (decision record d188): no real-data statistic "
            "before he rules"
        )
    departures = [
        name
        for name in PENDING_DECISIONS
        if decision_value(config, name) != rulings[name]["ruling"]
    ]
    if departures:
        raise ValueError(
            f"the configuration departs from Max's rulings on {departures}; "
            "a registered run follows every ruling"
        )
    check = specification_code_check(block, config)
    if not check["consistent"]:
        raise ValueError(
            "the E1 specification block and the code or configuration "
            f"differ: {check['mismatches']}"
        )


def _json_normal(value: Any) -> Any:
    return json.loads(json.dumps(value, allow_nan=False, default=str))


def projection_identity_record(
    draws: Mapping[str, Any],
    *,
    data_provenance: str,
    artifact_path: Path = EXERCISE_1_ARTIFACT_PATH,
) -> dict[str, Any]:
    """Compare the projection diagnostics with exercise 1's (recorded only).

    The shared projection is exercise 1's when the environment reproduces
    it; the committed exercise-1 artifact's ``draws`` block holds that
    run's per-draw diagnostics.  Applies to a ``registered_real`` run only
    (an invented cohort is a different population); never refuses.
    """

    if data_provenance != REGISTERED_REAL:
        return {
            "applicable": False,
            "reason": (
                "the invented cohort is not exercise 1's population; the "
                "comparison applies to a registered_real run"
            ),
        }
    path = Path(artifact_path)
    if not path.is_file():
        return {"applicable": True, "compared": False, "reason": "missing"}
    committed = json.loads(path.read_text(encoding="utf-8")).get("draws", {})
    observed = _json_normal(draws)
    matching, differing, absent = [], [], []
    for wave, by_draw in observed.items():
        for draw, diagnostics in by_draw.items():
            key = f"{wave}/{draw}"
            reference = committed.get(wave, {}).get(draw)
            if reference is None:
                absent.append(key)
            elif reference == diagnostics:
                matching.append(key)
            else:
                differing.append(key)
    return {
        "applicable": True,
        "compared": True,
        "artifact": str(path.name),
        "artifact_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "identical": not differing and not absent,
        "matching": matching,
        "differing": differing,
        "absent_from_exercise_1": absent,
        "note": (
            "recorded, not refused: a difference means this environment "
            "does not reproduce exercise 1's projection bit for bit"
        ),
    }


def _cola_record(baseline: Any) -> dict[str, Any]:
    rates = {}
    for year in _COLA_RECORD_YEARS:
        try:
            rates[str(year)] = round(
                float(baseline.rate_for_determination_year(year)), 12
            )
        except (KeyError, ValueError):
            continue
    encoded = json.dumps(rates, sort_keys=True, separators=(",", ":"))
    return {
        "identical_in_both_scenarios": True,
        "basis": (
            "exercise 3 changes no increase: the baseline and every reform "
            "scenario read the same baseline COLA rate source object (A1 "
            "section 4 path, carried over); A1's floor and splice checks "
            "reduce to this identity"
        ),
        "determination_years": [
            min(int(y) for y in rates),
            max(int(y) for y in rates),
        ],
        "rates_sha256": hashlib.sha256(encoded.encode()).hexdigest(),
    }


def _scenarios(
    config: FRA68Config, baseline: SSAParameters
) -> tuple[Scenario, dict[str, SSAParameters], dict]:
    reform_by_schedule = {
        sid: reform_parameters(baseline, SCHEDULES[sid])
        for sid in config.schedule_ids
    }
    record = {
        "baseline": {
            "revision": baseline.pe_us_revision,
            "age_factor_fields_sha256": parameters_fra_sha256(baseline),
            "fra_months_by_birth_year": [
                [int(y), int(m)] for y, m in baseline.fra_months_by_birth_year
            ],
        },
        "schedules": {
            sid: {
                **SCHEDULES[sid].as_dict(),
                "schedule_sha256": SCHEDULES[sid].sha256(),
                "reform_revision": params.pe_us_revision,
                "age_factor_fields_sha256": parameters_fra_sha256(params),
                "fra_months_by_birth_year": [
                    [int(y), int(m)]
                    for y, m in params.fra_months_by_birth_year
                ],
            }
            for sid, params in reform_by_schedule.items()
        },
    }
    base = Scenario(
        name="baseline",
        params=baseline,
        baseline_params=baseline,
        survivor_retirement_age=SurvivorRetirementAge.STATUTORY_MAPPING,
    )
    return base, reform_by_schedule, record


def _reform_scenario(
    row: FRA68Row,
    config: FRA68Config,
    baseline: SSAParameters,
    reform_by_schedule: Mapping[str, SSAParameters],
) -> Scenario:
    return Scenario(
        name="reform",
        params=reform_by_schedule[row.schedule_id],
        baseline_params=baseline,
        survivor_retirement_age=row.survivor_retirement_age,
        claiming_response=row.claiming_response,
        c1_anchor_age=config.c1_anchor_age,
        schedule_id=row.schedule_id,
    )


def _compute_scenario(
    scenario: Scenario,
    *,
    cohort: Any,
    inputs: TrackAInputs,
    track_config: Any,
    track_row: Any,
    result: ProjectionResult,
    lookups: StateLookups,
    pia_cache: dict,
    assumed_birth_month: int,
) -> tuple[dict[int, PersonScenario], Counter]:
    """One scenario's amounts for every person alive in the reference year."""

    context = BenefitContext(
        cohort=cohort,
        params=scenario.params,
        baseline=inputs.baseline,
        config=track_config,
    )
    return scenario_benefits(
        result,
        context=context,
        track_row=track_row,
        scenario=scenario,
        lookups=lookups,
        pia_cache=pia_cache,
        assumed_birth_month=assumed_birth_month,
    )


def _group_label(age: int) -> str | None:
    for group in DEFAULT_AGE_GROUPS:
        if age >= group.lower and (group.upper is None or age <= group.upper):
            return group.label
    return None


_DI_KINDS = {
    "disabled": "disabled_worker",
    "opening_disabled_worker": "disabled_worker",
    "converted": "converted_di",
    "opening_converted_di": "converted_di",
}
_DI_WINDOW_DEFINITION = (
    "People the reform alone would expose to DI awards (plan section 8): "
    "in each projected year, the persons in the year's state who are not "
    "DI-entitled and not converted and whose year lies from the baseline "
    "FRA attainment year up to (not including) the reform's. 423(a)(1) "
    "extends DI eligibility to the new retirement age, so A4 would expose "
    "them to award incidence in the reform scenario only. Expected awards "
    "are A4's incidence at the start-of-year age. A diagnostic: the shared "
    "projection draws no such award, and the year's state (after that "
    "year's deaths) approximates the start-of-year exposure"
)


def _row_diagnostics(
    rows: list[dict], row: FRA68Row, draw_indices: tuple[int, ...]
) -> dict[str, Any]:
    """Plan section 7 cell diagnostics (reported, not registered).

    Per age group, over the rows A7 receives (union rows, all draws
    pooled unless stated): the weighted mean FRA increase in months over
    baseline recipients; retired-worker beneficiaries by claim age in each
    scenario; the weighted shares of each scenario's benefit dollars held
    by disabled workers and by converted disabled workers (own-record
    kind); and per draw the ratio of weighted totals over the union of
    recipients, with recipient counts by scenario.
    """

    components = row.components
    by_group: dict[str, dict[str, Any]] = {
        group.label: {
            "weight_base": 0.0,
            "weighted_fra_increase": 0.0,
            "claim_ages_base": Counter(),
            "claim_ages_reform": Counter(),
            "dollars": {"base": Counter(), "reform": Counter()},
            "by_draw": {
                int(d): {
                    "total_base": 0.0,
                    "total_reform": 0.0,
                    "n_base": 0,
                    "n_reform": 0,
                    "n_union": 0,
                }
                for d in draw_indices
            },
        }
        for group in DEFAULT_AGE_GROUPS
    }
    for item in rows:
        label = _group_label(int(item["age_reference"]))
        if label is None:
            continue
        cell = by_group[label]
        selected = {
            scenario: sum(
                item["benefit_components"].get(name, {}).get(scenario, 0.0)
                for name in components
            )
            for scenario in ("base", "reform")
        }
        if selected["base"] <= 0 and selected["reform"] <= 0:
            continue
        weight = float(item["weight"])
        draw = cell["by_draw"][int(item["draw"])]
        draw["n_union"] += 1
        for scenario in ("base", "reform"):
            amount = selected[scenario]
            if amount > 0:
                draw[f"n_{scenario}"] += 1
                draw[f"total_{scenario}"] += weight * amount
                kind = item[f"own_kind_{scenario}"]
                cell["dollars"][scenario][_DI_KINDS.get(kind, "other")] += (
                    weight * amount
                )
                cell["dollars"][scenario]["all"] += weight * amount
        if selected["base"] > 0:
            cell["weight_base"] += weight
            cell["weighted_fra_increase"] += (
                weight * item["fra_increase_months"]
            )
        for scenario in ("base", "reform"):
            age = item[f"claim_age_{scenario}"]
            if age is not None and selected[scenario] > 0:
                cell[f"claim_ages_{scenario}"][str(int(age))] += 1
    out: dict[str, Any] = {}
    for label, cell in by_group.items():
        dollars = cell["dollars"]
        out[label] = {
            "mean_fra_increase_months_weighted": (
                None
                if cell["weight_base"] <= 0
                else cell["weighted_fra_increase"] / cell["weight_base"]
            ),
            "retired_worker_rows_by_claim_age": {
                "base": dict(sorted(cell["claim_ages_base"].items())),
                "reform": dict(sorted(cell["claim_ages_reform"].items())),
            },
            "benefit_dollar_shares": {
                scenario: (
                    None
                    if dollars[scenario]["all"] <= 0
                    else {
                        kind: dollars[scenario][kind]
                        / dollars[scenario]["all"]
                        for kind in ("disabled_worker", "converted_di")
                    }
                )
                for scenario in ("base", "reform")
            },
            "union_by_draw": {
                str(d): {
                    "n_base": values["n_base"],
                    "n_reform": values["n_reform"],
                    "n_union": values["n_union"],
                    "ratio_of_weighted_totals_percent": (
                        None
                        if values["total_base"] <= 0
                        else 100.0
                        * (values["total_reform"] / values["total_base"] - 1)
                    ),
                }
                for d, values in cell["by_draw"].items()
            },
        }
    return {
        "definition": (
            "reported, not registered (plan section 7). Pooled over draws "
            "unless by draw; over the rows A7 receives with a positive "
            "selected benefit in either scenario. claim ages are the "
            "own retired-worker benefit's entitlement year minus birth "
            "year (at most 70) in each scenario. Dollar shares: weighted "
            "selected benefit of persons whose own record is a disabled "
            "worker (DI-entitled in that scenario) or a converted disabled "
            "worker, over the weighted selected total. The union ratio is "
            "100 (sum w B_reform / sum w B_base - 1) over every union row "
            "of the cell"
        ),
        "by_group": out,
    }


def _di_window(
    result: ProjectionResult,
    *,
    di_rates: Any,
    baseline: SSAParameters,
    reform: SSAParameters,
    assumed_birth_month: int,
) -> dict[str, Any]:
    """Plan section 8: people the reform alone would expose to DI awards.

    In each projected year, the persons in the year's state who are not
    DI-entitled and not converted and whose year lies from the baseline
    FRA attainment year up to (not including) the reform's: 423(a)(1)
    extends DI eligibility to the new retirement age, so A4 would expose
    them to award incidence in the reform scenario only.  Expected awards
    are A4's incidence at the start-of-year age.  A diagnostic: the shared
    projection draws no such award.
    """

    by_year: dict[str, Any] = {}
    min_age = int(di_rates.spec.min_award_age)
    sex_index = {sex: index for index, sex in enumerate(SEXES)}
    for frame in result.slices[1:]:
        if not len(frame):
            continue
        year = int(frame["year"].iloc[0])
        births = frame["birth_year"].to_numpy(dtype=np.int64)
        base_year = fra_attainment_year(
            births, baseline, assumed_birth_month=assumed_birth_month
        )
        new_year = fra_attainment_year(
            births, reform, assumed_birth_month=assumed_birth_month
        )
        entitled = frame["di_entitled"].to_numpy(dtype=bool)
        converted = frame["di_conversion_year"].notna().to_numpy()
        start_age = year - 1 - births
        exposed = (
            ~entitled
            & ~converted
            & (base_year <= year)
            & (year < new_year)
            & (start_age >= min_age)
        )
        if not exposed.any():
            continue
        sexes = np.array(
            [sex_index[str(s)] for s in frame["sex"].to_numpy()[exposed]]
        )
        probability = di_rates.incidence_probability(start_age[exposed], sexes)
        weights = frame["weight"].to_numpy(dtype=float)[exposed]
        by_year[str(year)] = {
            "exposed": int(exposed.sum()),
            "expected_awards": float(probability.sum()),
            "expected_awards_weighted": float((weights * probability).sum()),
            "start_ages": sorted({int(a) for a in start_age[exposed]}),
        }
    return by_year


def _incidence_at(di_rates: Any, ages: tuple[int, ...]) -> dict[str, Any]:
    return {
        sex: {
            str(age): float(
                di_rates.incidence_probability(
                    np.array([age]), np.array([index])
                )[0]
            )
            for age in ages
        }
        for index, sex in enumerate(SEXES)
    }


def run_fra68(
    inputs: TrackAInputs,
    *,
    config: FRA68Config | None = None,
    registration_pointer: str | None = None,
    progress: Callable[[str], None] | None = None,
    check_committed_parameters: bool = False,
    specification: Mapping[str, Any] | None = None,
    exercise_1_artifact: Path = EXERCISE_1_ARTIFACT_PATH,
) -> dict[str, Any]:
    """Project, compute both scenarios and tabulate every configured row.

    ``inputs`` is Track A's input bundle (``params`` is the baseline
    bundle; each reform bundle is derived from it).  ``specification`` is
    the E1 section 21 block (read from the committed document when
    omitted); a ``registered_real`` run refuses one that is not ratified,
    lists a decision awaiting Max, or differs from the code.
    """

    config = config or FRA68Config()
    config.check_runnable()
    track_config = config.track_a_config()
    cohorts = track_runner._population_cohorts(inputs, track_config)
    data_provenance = next(iter(cohorts.values())).data_provenance
    labels = tuple(next(iter(cohorts.values())).labels)
    real = data_provenance == REGISTERED_REAL
    if real and not registration_pointer:
        raise ValueError(
            "no real-data statistic before the issue #42 registration "
            "comment exists; pass its pointer to run a registered_real cohort"
        )
    block = e1_parameter_block() if specification is None else specification
    if real:
        check_specification_for_registered_run(block, config)
    spec_check = specification_code_check(block, config)
    consistency = track_runner._parameter_consistency(
        inputs,
        track_config,
        cohorts,
        compare_committed_values=real or check_committed_parameters,
    )
    if real and not consistency["consistent"]:
        failed = sorted(
            name
            for name, check in consistency["checks"].items()
            if not check["consistent"]
        )
        raise ValueError(
            "the inputs differ from the parameters the configuration "
            f"reports for this run: {failed}; a registered run refuses "
            "a mismatch"
        )
    track_runner._check_source_provenance(cohorts, data_provenance)
    track_runner._check_output_labels(labels, data_provenance)
    baseline_params = inputs.params
    base_scenario, reform_by_schedule, schedule_record = _scenarios(
        config, baseline_params
    )
    birth_month = int(config.di_spec.assumed_birth_month)
    schedule = claiming_schedule(
        inputs.claiming_pmf, max_table_year=config.claim_table_max_year
    )
    fra_schedule = fra_schedule_from_parameters(baseline_params)
    rows_by_row: dict[str, list[dict]] = {row: [] for row in config.rows}
    counters_by_row: dict[str, Counter] = {
        row: Counter() for row in config.rows
    }
    draws: dict[str, Any] = {}
    di_window: dict[str, Any] = {}
    for wave, cohort in cohorts.items():
        results, draws[str(wave)] = track_runner._project_population(
            cohort,
            inputs,
            track_config,
            schedule=schedule,
            fra_schedule=fra_schedule,
            progress=progress,
        )
        track_row = TRACK_A_ROWS[TRACK_A_ROW_BY_WAVE[wave]]
        wave_rows = config.rows_for_wave(wave)
        reform_keys = {
            config.row(row_id).reform_key: config.row(row_id)
            for row_id in wave_rows
        }
        pia_cache: dict = {}
        di_window[str(wave)] = {sid: {} for sid in config.schedule_ids}
        for draw, result in results.items():
            if progress is not None:
                progress(f"anchor wave {wave}, draw {draw}: benefits")
            lookups = StateLookups(result, config.reference_year)
            shared = {
                "cohort": cohort,
                "inputs": inputs,
                "track_config": track_config,
                "track_row": track_row,
                "result": result,
                "lookups": lookups,
                "pia_cache": pia_cache,
                "assumed_birth_month": birth_month,
            }
            base_people, base_counters = _compute_scenario(
                base_scenario, **shared
            )
            reform_people: dict[tuple, dict[int, PersonScenario]] = {}
            reform_counters: dict[tuple, Counter] = {}
            for key, sample_row in reform_keys.items():
                reform_people[key], reform_counters[key] = _compute_scenario(
                    _reform_scenario(
                        sample_row, config, baseline_params, reform_by_schedule
                    ),
                    **shared,
                )
            context = BenefitContext(
                cohort=cohort,
                params=baseline_params,
                baseline=inputs.baseline,
                config=track_config,
            )
            for row_id in wave_rows:
                row = config.row(row_id)
                rows, counters = union_benefit_rows(
                    base_people,
                    reform_people[row.reform_key],
                    draw=draw,
                    context=context,
                    lookups=lookups,
                    baseline_params=baseline_params,
                    reform_params=reform_by_schedule[row.schedule_id],
                )
                for item in rows:
                    item["age_reference"] = config.reference_year - int(
                        item["birth_year"]
                    )
                rows_by_row[row_id].extend(rows)
                counters_by_row[row_id].update(counters)
                counters_by_row[row_id].update(
                    {f"baseline_{k}": v for k, v in base_counters.items()}
                )
                counters_by_row[row_id].update(
                    {
                        f"reform_{k}": v
                        for k, v in reform_counters[row.reform_key].items()
                    }
                )
            for sid in config.schedule_ids:
                di_window[str(wave)][sid][str(draw)] = _di_window(
                    result,
                    di_rates=inputs.di_rates,
                    baseline=baseline_params,
                    reform=reform_by_schedule[sid],
                    assumed_birth_month=birth_month,
                )
    tabulations: dict[str, Any] = {}
    for row_id in config.rows:
        row = config.row(row_id)
        if progress is not None:
            progress(f"{row_id}: tabulating")
        output_labels = row_labels(row, labels)
        tabulation_config = ColaAgeProfileConfig(
            reference_year=config.reference_year,
            components=row.components,
            benefit_period="calendar_year_payments",
            headline_statistic=row.headline_statistic,
            draw_indices=config.draw_indices,
            floor_seeds=config.floor_seeds,
            allow_membership_difference=True,
            membership_basis=SCENARIO_SPECIFIC,
        )
        population = row.population
        upstream = {
            "specification": SPECIFICATION_ID,
            "row": row_id,
            "field_changed": row.field_changed,
            "schedule": row.schedule_id,
            "schedule_sha256": SCHEDULES[row.schedule_id].sha256(),
            "survivor_retirement_age": row.survivor_retirement_age.value,
            "claiming_response": row.claiming_response.value,
            "benefit_period": "calendar_2030_payments",
            "benefit_scale": "annual_12_times_monthly",
            "rate_path": (
                f"TR2008 {config.tr2008_alternative}, both scenarios"
            ),
            "behavior": row.behavior,
            "population_wave": population.anchor_wave,
            "population_weight": population.weight_variable,
            "population_start_year": population.start_year,
            "population_periods": population.periods(config.reference_year),
            "family_unit_id": population.family_unit_variable,
        }
        try:
            tabulation = tabulate_cola_age_profile(
                pd.DataFrame(rows_by_row[row_id]),
                data_provenance=data_provenance,
                config=tabulation_config,
                registration_pointer=registration_pointer,
                labels=output_labels,
                upstream_conventions=upstream,
                statistic_id=STATISTIC_ID,
            )
        except ColaTabulationError as error:
            tabulation = None
            status = f"refused: {type(error).__name__}: {error}"
        else:
            identical = tabulation["input_summary"]["memberships_identical"]
            if row.claiming_response is ClaimingResponse.FIXED and not (
                identical
            ):
                raise ValueError(
                    f"{row_id}: under fixed claim ages (C0) the baseline and "
                    "reform memberships must coincide, but "
                    f"{tabulation['input_summary']['n_rows_membership_differs']}"
                    " rows are recipients in one scenario only"
                )
            undefined = tabulation["undefined_cells"]
            status = (
                "tabulated"
                if not undefined
                else "tabulated with undefined cells: "
                + ", ".join(
                    f"{cell['group']} {cell['statistic']} "
                    f"({cell['n_defined_draws']} of "
                    f"{len(config.draw_indices)} draws defined)"
                    for cell in undefined
                )
            )
        tabulations[row_id] = {
            "status": status,
            "row": row.as_dict(),
            "labels": list(output_labels),
            "membership_identity_required": (
                row.claiming_response is ClaimingResponse.FIXED
            ),
            "benefit_counters": dict(sorted(counters_by_row[row_id].items())),
            "diagnostics": _row_diagnostics(
                rows_by_row[row_id], row, config.draw_indices
            ),
            "component_shares_by_age_group": track_runner._component_shares(
                rows_by_row[row_id], row.components, config.draw_indices
            ),
            "tabulation": tabulation,
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "specification": SPECIFICATION_ID,
        "data_provenance": data_provenance,
        "registration_pointer": registration_pointer,
        "labels": list(labels),
        "config": config.as_dict(),
        "pending_decisions": pending_decisions(config),
        "builder_defaults": builder_defaults(config),
        "track_a_conventions": {
            "note": (
                "the shared projection and the benefit-level and auxiliary "
                "rules are Track A's; Max ruled these for exercise 1 (d074, "
                "d075). Whether they carry over to exercise 3 is part of "
                "d188 item (a)"
            ),
            "config": track_config.as_dict(),
            "max_rulings_exercise_1": track_a_max_rulings(track_config),
            "builder_defaults": track_a_builder_defaults(track_config),
        },
        "specification_check": spec_check,
        "age_factor_parameters": schedule_record,
        "cola_paths": _cola_record(inputs.baseline),
        "parameter_consistency": consistency,
        "cohorts": {
            str(wave): {
                **dict(cohort.diagnostics),
                "source_provenance": dict(cohort.source_provenance),
            }
            for wave, cohort in cohorts.items()
        },
        "scheduled_entrants": 0,
        "population_mortality": track_runner._mortality_record(
            inputs.population_mortality
        ),
        "ssa_parameters_revision": baseline_params.pe_us_revision,
        "draws": draws,
        "projection_identity_with_exercise_1": projection_identity_record(
            draws,
            data_provenance=data_provenance,
            artifact_path=exercise_1_artifact,
        ),
        "di_window_diagnostic": {
            "definition": _DI_WINDOW_DEFINITION,
            "incidence_at_start_ages": _incidence_at(
                inputs.di_rates, (65, 66, 67)
            ),
            "by_wave_schedule_draw_year": di_window,
        },
        "rows": tabulations,
        "inputs_provenance": dict(inputs.provenance),
    }
