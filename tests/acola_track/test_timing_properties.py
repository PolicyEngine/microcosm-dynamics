"""Invented people pin future start years and rounding-aware bounds."""

import math
from dataclasses import replace

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics import scenario_benefits as sb
from populace_dynamics.acola_track.config import REGISTERED_ROWS, ACOLAConfig
from populace_dynamics.cola_track_a.benefits import (
    BenefitContext,
    reference_benefit_rows,
)
from populace_dynamics.engine.rng import (
    ProjectionModule,
    ProjectionRNGRegistry,
)
from populace_dynamics.estimates.parameters import COLASeries
from populace_dynamics.ss import benefits as ss_benefits
from tests.cola_track_a.test_assembly import (
    _career,
    _handmade_cohort,
    _state,
    _static,
    invented_cola,
    invented_params,
)


@pytest.mark.parametrize("first", [2010, 2011, 2027])
@pytest.mark.parametrize(
    "eligible", [2008, 2010, 2011, 2027, 2028, 2029, 2030]
)
@pytest.mark.parametrize("period", list(sb.BenefitPeriod))
def test_future_start_year_reaches_the_actual_legacy_emitter(
    first, eligible, period
):
    birth = eligible - 62
    cohort, result = _handmade_cohort(
        [_static(1, birth)],
        {1: _career(40_000.0, birth)},
        [
            _state(
                1,
                birth,
                2030,
                claimed=True,
                claim_year=eligible,
                claim_age=62,
                marital_status="single",
            )
        ],
        [_state(1, birth, 2010, marital_status="single")],
    )
    row = replace(
        REGISTERED_ROWS["C0"],
        first_reduced_determination_year=first,
        benefit_period=period,
    )
    rows, _ = reference_benefit_rows(
        result,
        draw=0,
        row=row.track_row(),
        context=BenefitContext(
            cohort,
            invented_params(),
            invented_cola(),
            ACOLAConfig(draw_indices=(0,)).track_a_config(),
        ),
    )
    payment = sb.payment_year_for_reference(2030, period)
    assert len(rows) == 1
    assert rows[0]["reduced_increases"] == payment - max(first, eligible)
    if (
        first == 2027
        and eligible == 2030
        and period is sb.BenefitPeriod.CALENDAR_YEAR
    ):
        assert rows[0]["benefit_base"] == rows[0]["benefit_reform"]


@given(
    eligible=st.integers(2000, 2030),
    first=st.sampled_from([2010, 2011, 2027]),
    december=st.booleans(),
    amount=st.integers(100, 10_000),
    reduction_bp=st.integers(0, 150),
)
@settings(max_examples=100, deadline=None)
def test_cut_bounds_monotonicity_and_zero_reform_on_rounded_paths(
    eligible,
    first,
    december,
    amount,
    reduction_bp,
):
    # Uniform invented rates deliberately differ from the model's rates.
    c = 0.031
    reduction = reduction_bp / 10_000
    end = 2030 + int(december)
    baseline = COLASeries(
        {year: c for year in range(1979, 2031)}, {"invented": True}
    )
    clock = sb.WorkerClock.at_age_62(eligible - 62)

    def path(r, start):
        rates = sb.scenario_rates(
            baseline,
            sb.COLAReform(
                annual_reduction=r, first_reduced_determination_year=start
            ),
            clock=clock,
        )
        return sb.increased_pia_path(
            eligibility_pia=float(amount),
            eligibility_year=eligible,
            cola=rates,
            horizon_year=end,
        )[end]

    base = path(0, first)
    reform = path(reduction, first)
    change = 100 * (reform / base - 1)
    factors = end - min(first, end)
    full_null = 100 * ((1 + c - reduction) / (1 + c)) ** factors - 100
    # Each dime floor loses <0.1 monthly dollars. Bound the propagated
    # losses, relative to this person's actual baseline, rather than
    # asserting a universal percent tolerance at arbitrarily low levels.
    rounding_tolerance_pp = (
        100
        * 0.1
        * math.fsum((1 + c) ** j for j in range(end - eligible + 1))
        / base
    )
    assert full_null - rounding_tolerance_pp - 1e-10 <= change <= 0
    assert (
        path(reduction, 2010) <= path(reduction, 2011) <= path(reduction, 2027)
    )
    assert path(min(reduction + 0.001, 0.02), first) <= reform
    if reduction == 0:
        assert reform == base
        assert change == 0

    # The payable worker path also floors after the claim-age factor.
    # Dollar rounding in the common eligibility AIME cannot introduce a
    # scenario difference; retain the actual path's final dime loss here.
    params = invented_params()
    birth = eligible - 62
    factor = 1 - ss_benefits.early_reduction(
        params.fra_months(birth) - 62 * 12, params
    )
    entitled_clock = sb.WorkerClock.at_age_62(birth, entitlement_year=eligible)

    def worker_path(r, start):
        paths = sb.worker_scenario_paths(
            eligibility_pia=float(amount),
            claim_age_factor=factor,
            clock=entitled_clock,
            baseline=baseline,
            reform=sb.COLAReform(
                annual_reduction=r, first_reduced_determination_year=start
            ),
            horizon_year=end,
        )
        return paths.reform_monthly_by_payment_year[end]

    worker_base = worker_path(0, first)
    worker_reform = worker_path(reduction, first)
    worker_change = 100 * (worker_reform / worker_base - 1)
    worker_tolerance_pp = (
        100
        * 0.1
        * (
            factor * math.fsum((1 + c) ** j for j in range(end - eligible + 1))
            + 1
        )
        / worker_base
    )
    assert full_null - worker_tolerance_pp - 1e-10 <= worker_change <= 0
    assert (
        worker_path(reduction, 2010)
        <= worker_path(reduction, 2011)
        <= worker_path(reduction, 2027)
    )
    assert worker_path(min(reduction + 0.001, 0.02), first) <= worker_reform
    if reduction == 0:
        assert worker_reform == worker_base
        assert worker_change == 0


@given(
    draw=st.integers(0, 19),
    period=st.integers(1, 20),
    module=st.sampled_from(list(ProjectionModule)),
)
@settings(max_examples=40, deadline=None)
def test_registered_draw_root_and_module_stream_are_deterministic(
    draw, period, module
):
    import numpy as np

    first = ProjectionRNGRegistry(draw, 20)
    second = ProjectionRNGRegistry(draw, 20)
    assert first.draw_seed == second.draw_seed == 5200 + draw
    expected = first.generator(period, module).random(20)
    # Query another stream to show calls cannot consume the tested stream.
    first.generator(0, module).random(100)
    np.testing.assert_array_equal(
        first.generator(period, module).random(20), expected
    )
    np.testing.assert_array_equal(
        second.generator(period, module).random(20), expected
    )
