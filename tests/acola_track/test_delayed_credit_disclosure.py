"""Invented late claimants pin the legacy cap disclosed before the run."""

from collections import Counter
from dataclasses import fields, replace

import pytest

from populace_dynamics import claiming
from populace_dynamics.cola_track_a.benefits import (
    BenefitContext,
    StateLookups,
    _Calculator,
    reference_benefit_rows,
)
from populace_dynamics.cola_track_a.config import TrackAConfig
from populace_dynamics.estimates.parameters import COLASeries
from populace_dynamics.ss.params import SSAParameters
from tests.acola_track.test_mechanism_l_equivalence import (
    equivalence_script,
)


@pytest.fixture(scope="module")
def disclosure_case():
    script = equivalence_script()
    params = script.invented_parameters()
    cohort, result = script.invented_population()
    context = BenefitContext(
        cohort,
        params,
        COLASeries({y: 0.028 for y in range(1979, 2031)}, {"invented": True}),
        TrackAConfig(rows=("R0",), draw_indices=(0,)),
    )
    row = script.registered_rows()[0]
    lookups = StateLookups(result, 2030)
    longer_context = replace(
        context, params=replace(params, max_delayed_months=60)
    )
    base_rows, _ = reference_benefit_rows(
        result, draw=0, row=row, context=context
    )
    longer_rows, _ = reference_benefit_rows(
        result, draw=0, row=row, context=longer_context
    )
    return (
        context,
        longer_context,
        row,
        lookups,
        {p["person_id"]: p for p in base_rows},
        {p["person_id"]: p for p in longer_rows},
    )


@pytest.mark.parametrize("birth", range(1917, 1943))
def test_mechanism_l_uses_legacy_48_month_cap_for_old_late_claimants(
    birth, disclosure_case
):
    context, longer_context, row, lookups, base_rows, longer_rows = (
        disclosure_case
    )
    params = context.params
    calculator = _Calculator(context, row, lookups, Counter(), {})
    pid = 2 * (birth - 1917) + 1
    state = lookups.final.loc[pid]
    assert state["claim_year"] - birth == 70
    assert 840 - params.fra_months(birth) > 48
    legacy_factor = 1 + 4 * params.delayed_credit_annual_rate(birth)
    record = calculator.worker_record(pid, state)
    assert record.claim_age_factor == legacy_factor
    assert record.claim_age_factor == claiming.benefit_factor(
        840, birth, params
    )
    assert record.claim_age_factor == claiming.benefit_factor(
        params.fra_months(birth) + 48, birth, params
    )

    # Change only this invented parameter bundle to expose the lost
    # months, without replacing any function used by mechanism L.
    longer_window = longer_context.params
    assert claiming.benefit_factor(840, birth, longer_window) > legacy_factor
    uncapped_calculator = _Calculator(
        longer_context,
        row,
        lookups,
        Counter(),
        {},
    )
    assert (
        uncapped_calculator.worker_record(pid, state).claim_age_factor
        > record.claim_age_factor
    )
    base, longer = base_rows[pid], longer_rows[pid]
    for scenario in ("base", "reform"):
        assert (
            base["benefit_components"]["retired_worker"][scenario]
            < longer["benefit_components"]["retired_worker"][scenario]
        )
    defaults = {field.name: field.default for field in fields(SSAParameters)}
    assert defaults["max_delayed_months"] == params.max_delayed_months == 48
