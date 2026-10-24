"""Invented late claimants pin the legacy cap disclosed before the run."""

from collections import Counter
from dataclasses import fields, replace

import pytest

from populace_dynamics import claiming
from populace_dynamics.acola_track.config import ACOLAConfig
from populace_dynamics.cola_track_a import statutory
from populace_dynamics.cola_track_a.benefits import (
    BenefitContext,
    StateLookups,
    _Calculator,
    reference_benefit_rows,
)
from populace_dynamics.cola_track_a.config import TrackAConfig
from populace_dynamics.cola_track_a.runner import tr2008_baseline_cola
from populace_dynamics.estimates.parameters import (
    COLASeries,
    load_cola_history,
)
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


def test_registered_parameter_binding_carries_the_48_month_cap():
    """A registered run's cap is the committed statutory capture's.

    A registered run checks its runtime parameters against the committed
    capture and refuses a mismatch, delayed-credit cap included
    (statutory_value_checks, through the legacy _parameter_consistency).
    So the disclosed cap holds for the registered run, not only for the
    invented bundle above.
    """
    assert statutory.load_statutory_capture()["max_delayed_months"] == 48
    params = statutory.captured_ssa_parameters()
    assert params.max_delayed_months == 48
    track = ACOLAConfig().track_a_config()
    baseline = tr2008_baseline_cola(
        load_cola_history(),
        first_year=track.tr2008_first_rate_year,
        last_year=track.reference_year,
        alternative=track.tr2008_alternative,
    )

    def delayed_credit_check(bundle):
        return statutory.statutory_value_checks(
            bundle,
            baseline,
            first_tr2008_rate_year=track.tr2008_first_rate_year,
            reference_year=track.reference_year,
            last_earnings_year=max(track.start_years.values()),
            tr2008_alternative=track.tr2008_alternative,
        )["delayed_retirement_credit"]

    assert delayed_credit_check(params)["consistent"]
    assert not delayed_credit_check(replace(params, max_delayed_months=60))[
        "consistent"
    ]
    # Under the committed schedule, a claim at 70 by anyone born
    # 1917-1942 falls more than 48 months past FRA, so the cap binds.
    for birth in range(1917, 1943):
        assert 840 - params.fra_months(birth) > 48
        assert claiming.benefit_factor(
            840, birth, params
        ) == claiming.benefit_factor(
            params.fra_months(birth) + 48, birth, params
        )
