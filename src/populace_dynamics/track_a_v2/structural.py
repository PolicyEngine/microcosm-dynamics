"""The separately frozen count-only protocol in a2-ratified-1 §16.7.

This module never asks a calculator for a PIA, benefit, weight total or
tabulation. Its request discovery and filing classification use event and
cohort metadata only. No structural run is performed during development.
"""

from __future__ import annotations

import warnings
from collections import Counter
from collections.abc import Mapping
from dataclasses import fields
from typing import Any

import pandas as pd

from populace_dynamics.cola_track_a.adapters import (
    build_period_modules,
    claiming_schedule,
)
from populace_dynamics.cola_track_a.config import TrackAConfig
from populace_dynamics.engine.di_entitlement import (
    fra_schedule_from_parameters,
)
from populace_dynamics.engine.loop import ProjectionEngine
from populace_dynamics.fra68_track.config import (
    ClaimingResponse,
    registered_rows,
)
from populace_dynamics.fra68_track.reform import SCHEDULES, reform_parameters

from .filing import (
    FilingRefusal,
    application_month,
    classify_ordering,
    spouse_timing,
)
from .histories import HistoryRefusal, HistoryValidator, nullable
from .manifest import INVENTED_HEADER, REGISTERED_HEADER
from .protocol import (
    STRUCTURAL_OUTPUTS,
    PreflightRecord,
    refuse_unresolved_structural_execution,
)

ORDERING_CLASSES = (
    "di_first",
    "concurrent",
    "prior_rib_spouse_di",
    "prior_rib_di_spouse",
    "spouse_only_first_refused",
)
COUNT_UNITS = {
    "d_unsupported_histories": "distinct requested person-draw histories",
    "s_ordering_classes": "person-draw applications by row and scenario",
    "s_refused_earlier_spells": "distinct reached person-draw histories",
    "opening_proxy_applications": "distinct reached person-draw applications",
}


class StructuralRefusal(ValueError):
    """A filing refusal preserves every permitted count already computed."""

    def __init__(self, error, counts):
        self.reason = error.reason
        self.person_id = error.person_id
        self.counts = counts
        super().__init__(str(error))


def _worker_record(validator, person_id, state):
    """Return only entitlement metadata and record kind; compute no level.

    Matches the record gates at cola_track_a/benefits.py:302–358 and the
    pre-1979 level exclusion at :268–270. §16.7 permits structural counts
    only: numerical PIA values cannot enter reachability classification.
    """
    birth = int(validator.cohort.persons_by_id.at[person_id, "birth_year"])
    record = validator.baseline_di_record(person_id, state)
    if record is not None:
        return (record[1], "di") if record[0] >= 1979 else None
    status = str(
        validator.cohort.persons_by_id.at[person_id, "opening_status"]
    )
    if status in ("survivor", "spouse", "other", "unclassified"):
        return None
    if not bool(state.claimed) or birth + 62 < 1979:
        return None
    claim = nullable(state.claim_year)
    opener = validator.cohort.opening.get(person_id)
    if claim is None and opener is not None:
        claim = opener.entitlement_year
    if claim is None:
        return None
    return max(claim, birth + 62), "retired"


def _scenario_timing(
    *, validator, worker_id, worker, state, base_params, params, response
):
    """C1/C2 timing only, retaining the July shift and age-70 cap (§7.4)."""
    baseline_year, kind = worker
    claim = nullable(state.claim_year)
    if (
        kind != "retired"
        or response is ClaimingResponse.FIXED
        or claim is None
        or claim <= validator.cohort.start_year
    ):
        return baseline_year, 0
    birth = int(validator.cohort.persons_by_id.at[worker_id, "birth_year"])
    age = min(baseline_year - birth, 70)
    if response is ClaimingResponse.AT_OR_AFTER_ANCHOR_DELAY and age < 65:
        return baseline_year, 0
    increase = params.fra_months(birth) - base_params.fra_months(birth)
    if increase <= 0:
        return baseline_year, 0
    months = min(12 * age + increase, 840)
    return baseline_year + (6 + months) // 12 - age, months - 12 * age


def _scenario_rows(base_params):
    fixed = ClaimingResponse.FIXED
    for number in range(6):
        for scenario in ("baseline", "reform"):
            yield f"R{number}/{scenario}", base_params, fixed
    rows = registered_rows()
    for row_id in [*(f"F{i}" for i in range(8)), "U0", "U1", "U2"]:
        target = {"U0": "F0", "U1": "F3", "U2": "F4"}.get(row_id, row_id)
        row = rows[target]
        yield f"{row_id}/baseline", base_params, fixed
        yield (
            f"{row_id}/reform",
            reform_parameters(base_params, SCHEDULES[row.schedule_id]),
            row.claiming_response,
        )


def count_projection(result, cohort, params) -> dict[str, Any]:
    """Only requested D/reached S histories count; every count is unweighted.

    §16.7 does not define deduplication. Conservatively count distinct
    person-draw histories for unsupported D, ended S and opening proxies;
    ordering classes retain §5.4's explicit row/scenario classification.
    """
    validator = HistoryValidator(result, cohort)
    unsupported = 0
    requests = validator.requested_di_levels()
    unsupported += len(getattr(validator, "request_errors", {}))
    for person_id, eligibility in requests.items():
        try:
            validator.validate(person_id, eligibility)
        except HistoryRefusal:
            unsupported += 1
    ordering = {
        name: dict.fromkeys(ORDERING_CLASSES, 0)
        for name, _, _ in _scenario_rows(params)
    }
    earlier_spells = set()
    opening_applications = set()

    def snapshot():
        return {
            "d_unsupported_histories": unsupported,
            "s_ordering_classes": ordering,
            "s_refused_earlier_spells": len(earlier_spells),
            "opening_proxy_applications": len(opening_applications),
        }

    final = validator.lookups.final
    for person_id in sorted(int(pid) for pid in final.index):
        state = final.loc[person_id]
        opener = cohort.opening.get(person_id)
        intact = opener is not None and not (
            opener.status == "disabled_worker"
            and nullable(state.di_recovery_year) is not None
        )
        if intact or state.marital_status != "married":
            continue
        try:
            own = validator.baseline_di_record(person_id, state)
        except HistoryRefusal as error:
            raise StructuralRefusal(error, snapshot()) from error
        if own is None or own[0] < 1979 or own[1] > 2030:
            continue
        recoveries = validator.event_counts(person_id)["recovery"]
        # §5.4's earlier-spell predicate applies to S's own DI-origin
        # scope; unlike ordering bins, it does not require a payable
        # linked benefit. Count it before the linked/application gates.
        if recoveries:
            earlier_spells.add(person_id)
            continue
        birth = int(cohort.persons_by_id.at[person_id, "birth_year"])
        claim = nullable(state.claim_year)
        receipt = cohort.persons_by_id.loc[person_id].get(
            "ss_receipt_opening", False
        )
        opening_prior = (
            not pd.isna(receipt)
            and bool(receipt)
            and claim is not None
            and claim <= cohort.start_year
        )
        try:
            application = application_month(
                birth_year=birth,
                claim_year=claim,
                entitlement_year=own[1],
                conversion_year=nullable(state.di_conversion_year),
                baseline_params=params,
                opening_prior_claim=opening_prior,
                person_id=person_id,
            )
        except FilingRefusal as error:
            raise StructuralRefusal(error, snapshot()) from error
        if "s_prior_claim_opening" in application.counters:
            opening_applications.add(person_id)
        worker_id = nullable(state.spouse_person_id)
        if worker_id not in cohort.roster_ids or worker_id not in final.index:
            continue
        worker_state = final.loc[worker_id]
        try:
            worker = _worker_record(validator, worker_id, worker_state)
        except HistoryRefusal as error:
            raise StructuralRefusal(error, snapshot()) from error
        if worker is None:
            continue
        for name, scenario_params, response in _scenario_rows(params):
            year, move = _scenario_timing(
                validator=validator,
                worker_id=worker_id,
                worker=worker,
                state=worker_state,
                base_params=params,
                params=scenario_params,
                response=response,
            )
            timing = spouse_timing(
                application,
                birth_year=birth,
                worker_entitlement_year=year,
                worker_baseline_entitlement_year=worker[0],
                worker_move_months=move,
                fra_months=scenario_params.fra_months(birth),
            )
            if not timing.payable:
                continue
            try:
                label = classify_ordering(
                    application,
                    entitlement_year=timing.year,
                    di_entitlement_year=own[1],
                    claim_year=claim,
                    person_id=person_id,
                )
            except FilingRefusal:
                label = "spouse_only_first_refused"
            ordering[name][label] += 1
    return snapshot()


def validate_count_outputs(counts: Mapping[str, Any]) -> None:
    """Refuse benefit amounts, weight sums, extra bins and tabulations."""
    if set(counts) != set(STRUCTURAL_OUTPUTS):
        raise ValueError(
            "only the four frozen structural count outputs are allowed"
        )
    for name in STRUCTURAL_OUTPUTS:
        if name == "s_ordering_classes":
            continue
        if type(counts[name]) is not int or counts[name] < 0:
            raise ValueError("structural counts must be nonnegative integers")
    rows = {
        f"{row}/{scenario}"
        for row in [
            *(f"R{i}" for i in range(6)),
            *(f"F{i}" for i in range(8)),
            *(f"U{i}" for i in range(3)),
        ]
        for scenario in ("baseline", "reform")
    }
    if set(counts["s_ordering_classes"]) != rows:
        raise ValueError("structural ordering rows differ from frozen scope")
    for value in counts["s_ordering_classes"].values():
        if set(value) != set(ORDERING_CLASSES) or any(
            type(count) is not int or count < 0 for count in value.values()
        ):
            raise ValueError(
                "only frozen ordering-class integer counts allowed"
            )


def validate_structural_artifact(artifact: Mapping[str, Any]) -> None:
    """§16.7 permits only the counts and fixed attempt/provenance metadata."""
    keys = set(artifact) - {"preflight"}
    normal = {"header", "protocol_sha256", "attempt", "count_units", "counts"}
    fallback = {"header", "attempt"}
    if keys not in (normal, fallback):
        raise ValueError("only frozen structural artifact fields are allowed")
    if artifact["header"] not in (INVENTED_HEADER, REGISTERED_HEADER):
        raise ValueError("unknown structural artifact header")
    if "preflight" in artifact:
        preflight = artifact["preflight"]
        if set(preflight) != {
            field.name for field in fields(PreflightRecord)
        } or any(not isinstance(value, str) for value in preflight.values()):
            raise ValueError("structural preflight metadata fields differ")
    attempt = artifact["attempt"]
    if keys == fallback:
        if set(attempt) != {
            "status",
            "refusal",
            "first_failing_person_draw",
            "step",
            "uncomputed_draws",
        } or (
            attempt["status"] != "refused"
            or not isinstance(attempt["refusal"], str)
            or not attempt["refusal"]
            or attempt["first_failing_person_draw"] is not None
            or attempt["step"] != "structural_input_loading_or_infrastructure"
            or attempt["uncomputed_draws"] != list(range(20))
        ):
            raise ValueError("structural infrastructure refusal fields differ")
        return
    if set(attempt) != {
        "status",
        "refusal",
        "completed_draws",
        "uncomputed_draws",
    }:
        raise ValueError("only frozen structural attempt fields are allowed")
    if attempt["status"] not in ("completed", "refused"):
        raise ValueError("unknown structural attempt status")
    refusal = attempt["refusal"]
    if attempt["status"] == "completed":
        if refusal is not None or attempt["uncomputed_draws"]:
            raise ValueError("completed structural attempt has a refusal")
    elif not isinstance(refusal, dict) or set(refusal) != {
        "reason",
        "person_id",
        "draw",
        "step",
    }:
        raise ValueError("only frozen structural refusal fields are allowed")
    elif (
        not isinstance(refusal["reason"], str)
        or not refusal["reason"]
        or (
            refusal["person_id"] is not None
            and type(refusal["person_id"]) is not int
        )
        or type(refusal["draw"]) is not int
        or refusal["draw"] not in range(20)
        or refusal["step"]
        not in ("projection", "structural_history_or_filing")
    ):
        raise ValueError("structural refusal metadata differs")
    draws = attempt["completed_draws"] + attempt["uncomputed_draws"]
    if any(
        type(draw) is not int or draw not in range(20) for draw in draws
    ) or len(set(draws)) != len(draws):
        raise ValueError("structural attempt draw metadata differs")
    digest = artifact["protocol_sha256"]
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise ValueError("structural artifact lacks its protocol hash")
    if artifact["count_units"] != COUNT_UNITS:
        raise ValueError("structural count units differ")
    validate_count_outputs(artifact["counts"])


def run_structural(
    inputs, *, registration: PreflightRecord, draw_indices=tuple(range(20))
):
    """Project and count only; intentionally omit v1 weighted diagnostics.

    The otherwise shared cola_track_a.runner._project_population ends in
    _draw_diagnostics (runner.py:624–629), which computes weighted DI
    summaries. §16.7 forbids those, so use its identical engine/modules
    directly, without invoking that diagnostic helper.
    """
    if not isinstance(registration, PreflightRecord) or registration.mode != (
        "structural"
    ):
        raise ValueError(
            "a separately validated structural protocol is required"
        )
    if inputs.cohort.data_provenance != "invented":
        refuse_unresolved_structural_execution()
        registration.validate_inputs(inputs)
    if inputs.cohort.data_provenance != "invented" and tuple(draw_indices) != (
        tuple(range(20))
    ):
        raise ValueError("structural protocol freezes twenty draws")
    config = TrackAConfig(
        rows=tuple(f"R{i}" for i in range(6)), draw_indices=tuple(draw_indices)
    )
    schedule = claiming_schedule(
        inputs.claiming_pmf, max_table_year=config.claim_table_max_year
    )
    fra_schedule = fra_schedule_from_parameters(inputs.params)
    scalar_counts = Counter()
    ordering = {}
    completed = []
    refusal = None
    for draw in draw_indices:
        step = "projection"
        try:
            modules = build_period_modules(
                roster_ids=inputs.cohort.roster_ids,
                population_model=inputs.population_mortality,
                di_rates=inputs.di_rates,
                fra_schedule=fra_schedule,
                schedule=schedule,
                death_log={},
                cell_log={},
            )
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", RuntimeWarning)
                result = ProjectionEngine(modules).project(
                    inputs.cohort.initial_slice,
                    end_year=2030,
                    draw_index=draw,
                    metadata={},
                )
            unexpected = [
                str(item.message)
                for item in caught
                if "DI-origin expected deaths exceed" not in str(item.message)
            ]
            if unexpected:
                raise RuntimeError(
                    f"unexpected projection warnings: {unexpected[:3]}"
                )
            step = "structural_history_or_filing"
            counts = count_projection(result, inputs.cohort, inputs.params)
            validate_count_outputs(counts)
        except StructuralRefusal as error:
            counts = error.counts
            validate_count_outputs(counts)
            refusal = {
                "reason": error.reason,
                "person_id": error.person_id,
                "draw": draw,
                "step": "structural_history_or_filing",
            }
        except (Exception, KeyboardInterrupt) as error:
            counts = {
                "d_unsupported_histories": 0,
                "s_ordering_classes": {
                    name: dict.fromkeys(ORDERING_CLASSES, 0)
                    for name, _, _ in _scenario_rows(inputs.params)
                },
                "s_refused_earlier_spells": 0,
                "opening_proxy_applications": 0,
            }
            refusal = {
                "reason": str(error) or type(error).__name__,
                "person_id": None,
                "draw": draw,
                "step": step,
            }
        for name in STRUCTURAL_OUTPUTS:
            if name != "s_ordering_classes":
                scalar_counts[name] += counts[name]
        for row, values in counts["s_ordering_classes"].items():
            ordering.setdefault(row, Counter()).update(values)
        if refusal:
            break
        completed.append(draw)
    if not ordering:
        ordering = {
            name: dict.fromkeys(ORDERING_CLASSES, 0)
            for name, _, _ in _scenario_rows(inputs.params)
        }
    merged = {
        name: int(scalar_counts[name])
        for name in STRUCTURAL_OUTPUTS
        if name != "s_ordering_classes"
    }
    merged["s_ordering_classes"] = {
        row: dict(values) for row, values in ordering.items()
    }
    validate_count_outputs(merged)
    return {
        "header": (
            INVENTED_HEADER
            if inputs.cohort.data_provenance == "invented"
            else REGISTERED_HEADER
        ),
        "protocol_sha256": registration.protocol_sha256,
        "attempt": {
            "status": "refused" if refusal else "completed",
            "refusal": refusal,
            "completed_draws": completed,
            "uncomputed_draws": [
                d for d in draw_indices if d not in completed
            ],
        },
        "count_units": COUNT_UNITS,
        "counts": merged,
    }
