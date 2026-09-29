"""Invented annual paths only: no readers, projection replay, or real inputs."""

from collections import Counter
from dataclasses import replace

import pandas as pd

from populace_dynamics.cola_track_a.benefits import (
    BenefitContext,
    StateLookups,
)
from populace_dynamics.cola_track_a.config import REGISTERED_ROWS, TrackAConfig
from populace_dynamics.cola_track_a.opening import TrackACohort
from populace_dynamics.engine.loop import ProjectionResult
from populace_dynamics.estimates.parameters import COLASeries
from populace_dynamics.fra68_track.benefits import Scenario
from populace_dynamics.ss.params import SSAParameters
from populace_dynamics.track_a_v2.benefits import (
    ScenarioCalculator,
    TrackACalculator,
)
from populace_dynamics.track_a_v2.histories import HistoryValidator


def parameters(**changes):
    params = SSAParameters(
        nawi={year: 100.0 for year in range(1951, 2051)},
        wage_base={1951: 1e9},
        pia_factors=(1.0, 1.0, 1.0),
        fra_months_by_birth_year=[(1900, 804)],
        early_monthly_rates=(5 / 900, 5 / 1200),
        early_first_bracket_months=36,
        pe_us_revision="INVENTED",
        delayed_credit_by_birth_year=[(1900, 0.08)],
        survivor_reduction_floor=1.0,
    )
    return replace(params, **changes)


def build(people, *, careers=None, opening=None):
    """Invent exact events; tuples in awards/recoveries support intended refusals."""
    people = [dict(person) for person in people]
    persons, slices = [], []
    for person in people:
        persons.append(
            {
                "person_id": person["id"],
                "birth_year": person.get("birth", 1960),
                "opening_status": person.get("opening_status", "nonrecipient"),
                "family_unit_id": person["id"],
                "ss_receipt_opening": person.get("opening_receipt", False),
            }
        )
    for year in range(2010, 2031):
        rows = []
        for person in people:
            if year >= person.get("death", 9999):
                continue
            awards = tuple(person.get("awards", ()))
            recoveries = tuple(person.get("recoveries", ()))
            conversion = person.get("conversion")
            award = max((a for a in awards if a <= year), default=None)
            recovery = max((a for a in recoveries if a <= year), default=None)
            entitled = (
                bool(person.get("opening_di", False)) or award is not None
            )
            if recovery is not None and (award is None or recovery > award):
                entitled = False
            converted = conversion is not None and conversion <= year
            if converted:
                entitled = False
            event = "opening" if year == 2010 else "none"
            if year in awards and year != 2010:
                event = "award"
            elif year in recoveries:
                event = "recovery"
            elif conversion == year:
                event = "conversion"
            elif entitled and year != 2010:
                event = "continuing"
            claim = person.get("claim")
            claim_now = claim if claim is not None and claim <= year else None
            marital = person.get("marital", "single")
            widowhood = person.get("widowhood")
            if widowhood is not None and year < widowhood:
                marital = "married"
            rows.append(
                {
                    "person_id": person["id"],
                    "year": year,
                    "birth_year": person.get("birth", 1960),
                    "weight": 1.0,
                    "di_entitled": entitled,
                    "di_award_year": award,
                    "di_recovery_year": recovery,
                    "di_conversion_year": conversion if converted else None,
                    "di_event": event,
                    "claimed": claim_now is not None,
                    "claim_year": claim_now,
                    "marital_status": marital,
                    "spouse_person_id": person.get("spouse"),
                    "late_spouse_person_id": person.get("late_spouse"),
                    "widowhood_year": widowhood,
                }
            )
        slices.append(pd.DataFrame(rows))
    result = ProjectionResult(tuple(slices), (), 0)
    cohort = TrackACohort(
        pd.DataFrame(persons),
        careers or {},
        slices[0],
        opening or {},
        "invented",
        ("INVENTED DATA - NOT A COMPARISON",),
        {},
    )
    return cohort, result


def calculator(
    cohort,
    result,
    *,
    mechanism="L",
    exercise=1,
    params=None,
    baseline_params=None,
    response="fixed",
    cache=None,
    row="R0",
    annual_reduction=0.0,
    **kwargs,
):
    params = params or parameters()
    config = TrackAConfig(annual_reduction=annual_reduction)
    context = BenefitContext(
        cohort,
        params,
        COLASeries(
            {year: 0.0 for year in range(1970, 2051)}, {"invented": True}
        ),
        config,
    )
    args = (
        context,
        REGISTERED_ROWS[row],
        StateLookups(result, 2030),
        Counter(),
        {} if cache is None else cache,
    )
    kwargs.update(
        mechanism=mechanism, history_validator=HistoryValidator(result, cohort)
    )
    if exercise == 1:
        return TrackACalculator(*args, **kwargs)
    scenario = Scenario(
        "invented",
        params,
        baseline_params or params,
        claiming_response={
            "fixed": "c0_fixed_claim_ages",
            "at_or_after_anchor_delay": "c1_claimants_at_or_after_anchor_delay",
            "all_projected_delay": "c2_all_claimants_delay",
        }.get(response, response),
    )
    return ScenarioCalculator(*args, scenario, assumed_birth_month=7, **kwargs)
