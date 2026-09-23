"""Track A assembly tests on INVENTED data only.

Every person, earnings amount, Social Security amount, weight, rate, life
table, DI probability, claim-age PMF, wage index and COLA below is
INVENTED for testing.  No test reads PSID, a committed parameter file or
a comparator value; the one exception is the A1 draft specification
document, whose registered-row block the assembly must agree with.
"""

from __future__ import annotations

import math
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from populace_dynamics import claiming
from populace_dynamics import scenario_benefits as sb
from populace_dynamics.cohorts import psid2010
from populace_dynamics.cola_track_a import (
    INVENTED_COHORT_LABEL,
    REGISTERED_ROWS,
    TrackAConfig,
    TrackAInputs,
    invented,
    prepare_track_a_cohort,
    run_track_a,
)
from populace_dynamics.cola_track_a import benefits as track_benefits
from populace_dynamics.cola_track_a import opening as opening_module
from populace_dynamics.cola_track_a.adapters import (
    adopt_marital_state,
    claiming_schedule,
    di_aware_claiming,
    widowhood_marital_step,
)
from populace_dynamics.cola_track_a.config import LevelPolicy
from populace_dynamics.cola_track_a.mortality import (
    Tr2008YearAwareMortality,
)
from populace_dynamics.cola_track_a.opening import (
    OpeningStockRecord,
    TrackACohort,
)
from populace_dynamics.cola_track_a.runner import (
    _component_shares,
    a1_parameter_block,
)
from populace_dynamics.engine.di_entitlement_rates import (
    MAX_AGE,
    DIEntitlementRates,
    DIEntitlementSpec,
)
from populace_dynamics.engine.loop import (
    PeriodContext,
    ProjectionResult,
)
from populace_dynamics.engine.rng import ProjectionRNGRegistry
from populace_dynamics.engine.steps import AgeSexMortalityModel
from populace_dynamics.estimates.cola_age_profile import (
    INVENTED_DATA_LABEL,
)
from populace_dynamics.estimates.parameters import COLASeries
from populace_dynamics.ss import benefits
from populace_dynamics.ss.params import SSAParameters

SHAPE = (2, MAX_AGE + 1)


# --------------------------------------------------------------------------
# INVENTED parameters
# --------------------------------------------------------------------------
def invented_params() -> SSAParameters:
    """INVENTED oracle parameters: 4 percent wage growth from 1951."""
    return SSAParameters(
        nawi={
            year: 2_800.0 * 1.04 ** (year - 1951) for year in range(1951, 2061)
        },
        wage_base={1937: 3_000.0, 1975: 14_100.0, 1990: 51_300.0},
        pia_factors=(0.9, 0.32, 0.15),
        fra_months_by_birth_year=[(1900, 792), (1955, 804)],
        early_monthly_rates=(5 / 900, 5 / 1200),
        early_first_bracket_months=36,
        pe_us_revision="INVENTED",
        delayed_credit_by_birth_year=[(1900, 0.08)],
    )


def invented_cola() -> COLASeries:
    """INVENTED determination-year COLA fractions (every one above 1%)."""
    return COLASeries(
        by_determination_year={
            year: 0.02 + 0.002 * (year % 5) for year in range(1979, 2032)
        },
        provenance={"invented": True},
    )


def invented_di_rates(**spec_changes) -> DIEntitlementRates:
    incidence = np.zeros(SHAPE)
    incidence[:, 18:70] = 0.006
    return DIEntitlementRates(
        spec=DIEntitlementSpec(**spec_changes),
        incidence=incidence,
        recovery_attained=np.full(SHAPE, 0.01),
        death_attained=np.full(SHAPE, 0.02),
        population_reference_death=np.full(SHAPE, 0.01),
        recovery_select=None,
        death_select=None,
        recovery_level_factor=1.0,
        death_level_factor=1.0,
    )


def invented_mortality(ratio: float = 1.0) -> Tr2008YearAwareMortality:
    ages = np.arange(MAX_AGE + 1)
    qx = np.minimum(0.0001 * np.exp(0.085 * ages), 1.0)
    return Tr2008YearAwareMortality(
        qx_by_sex={"female": qx * 0.8, "male": qx},
        ratio_by_year={year: (ratio, ratio) for year in range(2011, 2032)},
        alternative="INVENTED",
        base_year=2004,
    )


def _inputs(cohort: TrackACohort, **changes) -> TrackAInputs:
    values = {
        "cohort": cohort,
        "params": invented_params(),
        "baseline": invented_cola(),
        "di_rates": invented_di_rates(),
        "population_mortality": invented_mortality(),
        "claiming_pmf": invented.invented_claiming_pmf(),
    }
    values.update(changes)
    return TrackAInputs(**values)


CONFIG = TrackAConfig(draw_indices=(0, 1))


@pytest.fixture(scope="module")
def a3_cohort() -> psid2010.Psid2010Cohort:
    return psid2010.build_psid2010_cohort(
        invented.invented_psid2010_inputs(seed=7)
    )


@pytest.fixture(scope="module")
def cohort(a3_cohort) -> TrackACohort:
    return prepare_track_a_cohort(
        a3_cohort, data_provenance="invented", config=CONFIG
    )


@pytest.fixture(scope="module")
def result(cohort) -> dict:
    return run_track_a(_inputs(cohort), config=CONFIG)


# --------------------------------------------------------------------------
# Opening state
# --------------------------------------------------------------------------
def test_initial_slice_carries_no_realized_death_columns(cohort):
    columns = set(cohort.initial_slice.columns)
    assert not {c for c in columns if c.startswith("death")}
    assert set(cohort.initial_slice["year"]) == {2010}
    assert (
        cohort.initial_slice["age"]
        == 2010 - cohort.initial_slice["birth_year"]
    ).all()


def test_opening_clocks_follow_the_a1_rules(cohort):
    persons = cohort.persons.set_index("person_id")
    rules = set()
    for person_id, record in cohort.opening.items():
        row = persons.loc[person_id]
        rules.add(record.clock_rule)
        if record.status == "retired_worker":
            assert record.clock_year == row["birth_year"] + 62
        if record.status == "disabled_worker" or row["age_2010"] < 62:
            receipt = row["opening_claim_year"]
            if pd.isna(receipt):
                receipt = row["opening_claim_year_upper_bound"]
            assert record.clock_year == receipt
        if record.clock_rule == "linked_worker_birth_plus_62":
            assert record.clock_year == row["linked_spouse_birth_year"] + 62
        assert record.clock_year <= 2010
        assert record.entitlement_year >= record.clock_year
        assert record.observed_annual_amount == row["ss_2010"]
    assert {"own_birth_plus_62", "a3_receipt_start"} <= rules
    assert rules & {
        "linked_worker_birth_plus_62",
        "linked_worker_death_before_eligibility",
    }


def test_opening_di_stock_is_the_a3_disabled_workers(cohort):
    frame = cohort.initial_slice.set_index("person_id")
    persons = cohort.persons.set_index("person_id")
    disabled = persons["opening_status"] == "disabled_worker"
    assert (
        frame["di_entitled"].to_numpy(dtype=bool)
        == disabled.reindex(frame.index).to_numpy(dtype=bool)
    ).all()
    assert frame["di_entitled"].any()
    assert not frame.loc[frame["di_entitled"], "claimed"].any()


def test_prepare_refuses_unknown_provenance(a3_cohort):
    with pytest.raises(ValueError, match="data_provenance"):
        prepare_track_a_cohort(a3_cohort, data_provenance="psid")


# --------------------------------------------------------------------------
# Adapters
# --------------------------------------------------------------------------
def _context(year: int, ids) -> PeriodContext:
    return PeriodContext(
        period_index=year - 2010,
        year=year,
        draw_index=0,
        metadata={},
        rng_registry=ProjectionRNGRegistry(0, 20),
        person_ordinals={pid: i for i, pid in enumerate(sorted(ids))},
    )


def _marital_frame(rows) -> pd.DataFrame:
    frame = pd.DataFrame(
        rows,
        columns=[
            "person_id",
            "marital_status",
            "spouse_person_id",
            "widowhood_year",
            "late_spouse_person_id",
        ],
    )
    frame["year"] = 2015
    frame["marital_status"] = frame["marital_status"].astype(object)
    for column in (
        "spouse_person_id",
        "widowhood_year",
        "late_spouse_person_id",
    ):
        frame[column] = frame[column].astype("Int64")
    frame["widowed_in_projection"] = False
    return frame


def test_marital_step_widows_only_survivors_of_roster_deaths():
    # 1 and 2 married (2 died this year); 3 married to 9, outside roster;
    # 4 married to 5, both alive.
    frame = _marital_frame(
        [
            (1, "married", 2, pd.NA, pd.NA),
            (3, "married", 9, pd.NA, pd.NA),
            (4, "married", 5, pd.NA, pd.NA),
            (5, "married", 4, pd.NA, pd.NA),
        ]
    )
    context = _context(2015, [1, 2, 3, 4, 5])
    marital = widowhood_marital_step(
        frame, context, None, roster_ids=frozenset({1, 2, 3, 4, 5})
    )
    out = adopt_marital_state(frame, context, marital, None).set_index(
        "person_id"
    )
    assert out.at[1, "marital_status"] == "widowed"
    assert out.at[1, "widowhood_year"] == 2015
    assert out.at[1, "late_spouse_person_id"] == 2
    assert pd.isna(out.at[1, "spouse_person_id"])
    assert bool(out.at[1, "widowed_in_projection"])
    for person_id in (3, 4, 5):
        assert out.at[person_id, "marital_status"] == "married"
        assert not bool(out.at[person_id, "widowed_in_projection"])
    assert marital.births.empty


def test_claiming_skips_entitled_disabled_workers():
    frame = pd.DataFrame(
        {
            "person_id": [1, 2, 3],
            "year": 2015,
            "age": [55, 55, 67],
            "sex": ["male", "female", "male"],
            "di_entitled": [True, False, False],
            "di_converted": [False, False, True],
            "claimed": [False, False, False],
            "claim_age": pd.array([pd.NA] * 3, dtype="Int64"),
            "claim_year": pd.array([pd.NA] * 3, dtype="Int64"),
        }
    )
    schedule = claiming_schedule(
        invented.invented_claiming_pmf(), max_table_year=2008
    )
    out = di_aware_claiming(
        frame, _context(2015, [1, 2, 3]), None, schedule=schedule
    ).set_index("person_id")
    assert pd.isna(out.at[1, "claim_age"]) and not out.at[1, "claimed"]
    assert not pd.isna(out.at[2, "claim_age"])
    assert out.at[3, "claimed"] and out.at[3, "claim_year"] == 2015
    assert pd.isna(out.at[3, "claim_age"])


def test_claiming_schedule_keeps_only_rows_at_or_before_the_cap():
    pmf = invented.invented_claiming_pmf()
    pmf[("male", 2012)] = {70: 1.0}
    schedule = claiming_schedule(pmf, max_table_year=2008)
    assert max(year for _, year in schedule.pmf) == 2008
    ages, _ = schedule.distribution("male", 2025)
    assert 62 in ages


def test_year_aware_mortality_scales_by_year_and_group():
    model = Tr2008YearAwareMortality(
        qx_by_sex={
            "female": np.full(MAX_AGE + 1, 0.01),
            "male": np.full(MAX_AGE + 1, 0.02),
        },
        ratio_by_year={2020: (0.5, 0.8)},
        alternative="INVENTED",
        base_year=2004,
    )
    frame = pd.DataFrame({"age": [40, 64, 65, 90], "sex": ["male"] * 4})
    values = model(frame, _context(2020, [1]))
    assert np.allclose(values, [0.01, 0.01, 0.016, 0.016])
    assert not hasattr(model, "probabilities")
    with pytest.raises(KeyError):
        model.probabilities_for_year(frame, 2021)


# --------------------------------------------------------------------------
# The end-to-end run
# --------------------------------------------------------------------------
def test_run_labels_every_output_invented(result):
    assert result["data_provenance"] == "invented"
    assert result["labels"][0] == INVENTED_COHORT_LABEL
    assert "PSID-seeded closed cohort" not in result["labels"]
    for row in result["rows"].values():
        assert row["status"] == "tabulated", row["status"]
        labels = row["tabulation"]["labels"]
        assert labels[0] == INVENTED_DATA_LABEL
        assert "Python oracle (not Axiom)" in labels
        assert "fixed-path mechanical incidence" in labels
    assert result["scheduled_entrants"] == 0
    assert result["rows_not_built"].keys() == {"R6"}


def test_every_group_is_populated_in_every_draw(result):
    for group in result["rows"]["R0"]["tabulation"]["groups"]:
        assert len(group["cells"]) == len(CONFIG.draw_indices)
        assert all(cell["n_base"] > 0 for cell in group["cells"])


def test_di_stock_flow_reconciles_every_draw(result):
    for diagnostics in result["draws"].values():
        flows = diagnostics["di_stock_flow"]
        assert [row["year"] for row in flows] == list(range(2011, 2031))


def test_reduced_counts_match_the_clock_arithmetic(result):
    counts = {
        row_id: result["rows"][row_id]["reduced_increases_by_age_group"]
        for row_id in ("R0", "R1", "R4")
    }
    # A clock that started by 2009 carries 21 reduced increases in 2030
    # payments under R0, 20 under R1 and 22 in the December 2030 amount.
    assert counts["R0"]["80+"]["max"] == 21
    assert counts["R1"]["80+"]["max"] == 20
    assert counts["R4"]["80+"]["max"] == 22
    for row_id in ("R0", "R1", "R4"):
        for group in counts[row_id].values():
            assert group["max"] <= 22


def test_baseline_amounts_are_shared_by_rows_with_the_same_period(result):
    # Fixed paths: rows that change only the reform, the clock or the
    # statistic see the same members and the same baseline means.
    for row_id in ("R1", "R2", "R3"):
        for left, right in zip(
            result["rows"]["R0"]["tabulation"]["groups"],
            result["rows"][row_id]["tabulation"]["groups"],
            strict=True,
        ):
            for a, b in zip(left["cells"], right["cells"], strict=True):
                assert a["n_base"] == b["n_base"]
                assert a["mean_benefit_base"] == pytest.approx(
                    b["mean_benefit_base"]
                )


def test_projection_is_reproducible_by_draw(cohort):
    config = TrackAConfig(draw_indices=(1,), rows=("R0",))
    first = run_track_a(_inputs(cohort), config=config)
    second = run_track_a(_inputs(cohort), config=config)
    assert first["draws"] == second["draws"]
    assert first["rows"]["R0"]["tabulation"]["groups"] == (
        second["rows"]["R0"]["tabulation"]["groups"]
    )


def test_registered_real_cohort_needs_the_registration_pointer(cohort):
    real = replace(cohort, data_provenance="registered_real")
    with pytest.raises(ValueError, match="registration"):
        run_track_a(_inputs(real), config=CONFIG)


@pytest.mark.parametrize(
    "change",
    [
        {"claim_class": "hold_for_track_b_m6_forward"},
        {"oracle_cola_horizon_extension_to_2030": False},
        {"acceptance_rule": "within 1 point"},
    ],
)
def test_unratified_alternatives_refuse_to_run(cohort, change):
    with pytest.raises(ValueError):
        run_track_a(_inputs(cohort), config=replace(CONFIG, **change))


def test_nonpositive_reduced_rate_fails_closed(cohort):
    low = COLASeries(
        by_determination_year={year: 0.005 for year in range(1979, 2032)},
        provenance={"invented": True},
    )
    with pytest.raises(ValueError, match="positive"):
        run_track_a(_inputs(cohort, baseline=low), config=CONFIG)


def test_excluded_di_level_drops_projected_awards(cohort):
    config = TrackAConfig(
        draw_indices=(0,),
        rows=("R0",),
        di_benefit_level=LevelPolicy.EXCLUDE,
    )
    excluded = run_track_a(_inputs(cohort), config=config)
    counters = excluded["rows"]["R0"]["benefit_counters"]
    assert counters.get("level_excluded_di", 0) > 0


def test_registered_rows_match_the_a1_block():
    block = a1_parameter_block()
    rows = block["rows"]
    assert set(rows) - set(REGISTERED_ROWS) == {"R6"}
    for row_id, row in REGISTERED_ROWS.items():
        expected = {**rows["R0"], **rows[row_id]}
        assert expected["first_reduced_determination_year"] == (
            row.first_reduced_determination_year
        )
        assert expected["exposure_clock"] == row.exposure_clock.value
        assert list(expected["components"]) == list(row.components)
        assert expected.get("last_determination_year", 2029) == (
            sb.payment_year_for_reference(2030, row.benefit_period) - 1
        )
    assert block["decisions_awaiting_max"]["di_benefit_level"]["default"] == (
        TrackAConfig().di_benefit_level.value
    )


# --------------------------------------------------------------------------
# Arithmetic against A6
# --------------------------------------------------------------------------
@pytest.mark.parametrize("clock_year", [1995, 2004, 2009, 2010])
@pytest.mark.parametrize("exposure", [None, 2006, 2010])
@pytest.mark.parametrize("round_to_dime", [False, True])
def test_opening_stock_amounts_equal_the_a6_function(
    clock_year, exposure, round_to_dime
):
    baseline = invented_cola()
    reform = sb.COLAReform()
    entitlement = max(clock_year, exposure or clock_year)
    record = OpeningStockRecord(
        person_id=1,
        status="retired_worker",
        component="retired_worker",
        observed_annual_amount=15_432.0,
        clock_year=clock_year,
        clock_rule="INVENTED",
        entitlement_year=entitlement,
        entitlement_clamped=False,
    )
    clock = sb.WorkerClock(
        basis=sb.EligibilityBasis.AGE_62,
        eligibility_year=clock_year,
        entitlement_year=entitlement,
    )
    exposure_clock = (
        sb.ExposureClock.ELIGIBILITY
        if exposure is None
        else sb.ExposureClock.ENTITLEMENT
    )
    a6 = sb.opening_stock_scenario_paths(
        observed_monthly_amount=15_432.0 / 12,
        clock=clock,
        baseline=baseline,
        reform=reform,
        exposure_clock=exposure_clock,
        horizon_year=2030,
        round_to_dime=round_to_dime,
    )
    ours = track_benefits.opening_stock_amounts(
        record,
        baseline=baseline,
        reform=reform,
        exposure_start_year=clock.exposure_start_year(exposure_clock),
        observed_payment_year=2010,
        payment_year=2030,
        round_to_dime=round_to_dime,
    )
    assert ours == (
        a6.baseline_monthly_by_payment_year[2030],
        a6.reform_monthly_by_payment_year[2030],
    )


def test_unrounded_opening_ratio_is_the_reduced_increase_product():
    baseline = invented_cola()
    record = OpeningStockRecord(
        person_id=1,
        status="survivor",
        component="aged_widow",
        observed_annual_amount=9_000.0,
        clock_year=2003,
        clock_rule="INVENTED",
        entitlement_year=2003,
        entitlement_clamped=False,
    )
    base, reform = track_benefits.opening_stock_amounts(
        record,
        baseline=baseline,
        reform=sb.COLAReform(),
        exposure_start_year=2003,
        observed_payment_year=2010,
        payment_year=2030,
        round_to_dime=False,
    )
    product = math.prod(
        (1 + baseline[year] - 0.01) / (1 + baseline[year])
        for year in range(2009, 2030)
    )
    assert reform / base == pytest.approx(product, rel=1e-12)
    assert base == pytest.approx(
        750.0 * math.prod(1 + baseline[y] for y in range(2010, 2030)),
        rel=1e-12,
    )


def _handmade_cohort(persons, careers, final_rows, last_rows):
    """INVENTED two-slice projection for the auxiliary composition tests."""
    static = pd.DataFrame(persons)
    for column in (
        "opening_claim_year",
        "opening_claim_year_upper_bound",
        "opening_claim_age",
        "spouse_person_id",
        "late_spouse_person_id",
        "late_spouse_death_year",
        "widowhood_year",
        "linked_spouse_birth_year",
    ):
        static[column] = pd.array([pd.NA] * len(static), dtype="Int64")
    static["ss_receipt_2010"] = pd.array([False] * len(static), "boolean")
    initial = pd.DataFrame(last_rows)
    cohort = TrackACohort(
        persons=static,
        careers=careers,
        initial_slice=initial,
        opening={},
        data_provenance="invented",
        labels=(INVENTED_COHORT_LABEL,),
        diagnostics={},
    )
    result = ProjectionResult(
        slices=(initial, pd.DataFrame(final_rows)),
        traces=(),
        draw_index=0,
    )
    return cohort, result


def _state(person_id, birth, year, **values):
    row = {
        "person_id": person_id,
        "year": year,
        "age": year - birth,
        "sex": "female",
        "birth_year": birth,
        "weight": 1_000.0,
        "di_entitled": False,
        "di_award_year": pd.NA,
        "di_conversion_year": pd.NA,
        "di_recovery_year": pd.NA,
        "claimed": False,
        "claim_age": pd.NA,
        "claim_year": pd.NA,
        "marital_status": "married",
        "spouse_person_id": pd.NA,
        "widowhood_year": pd.NA,
        "late_spouse_person_id": pd.NA,
        "widowed_in_projection": False,
    }
    row.update(values)
    return row


def _career(level: float, birth: int) -> dict[int, float]:
    return {year: level for year in range(birth + 22, 2011)}


def _static(person_id, birth):
    return {
        "person_id": person_id,
        "interview_2011": 1,
        "weight": 1_000.0,
        "sex": "female",
        "birth_year": birth,
        "age_2010": 2010 - birth,
        "opening_status": "none",
        "ss_2008": 0,
        "ss_2010": 0,
        "marital_status_2010": "married",
    }


def test_spouse_excess_equals_the_a6_composition():
    # INVENTED couple: 1 (born 1962, low earner) claims 2026; worker 2
    # (born 1960) claimed 2024.
    persons = [_static(1, 1962), _static(2, 1960)]
    careers = {1: _career(9_000.0, 1962), 2: _career(60_000.0, 1960)}
    final = [
        _state(
            1, 1962, 2030, claimed=True, claim_year=2026, spouse_person_id=2
        ),
        _state(
            2, 1960, 2030, claimed=True, claim_year=2024, spouse_person_id=1
        ),
    ]
    initial = [
        _state(1, 1962, 2010, spouse_person_id=2),
        _state(2, 1960, 2010, spouse_person_id=1),
    ]
    cohort, projection = _handmade_cohort(persons, careers, final, initial)
    params = invented_params()
    context = track_benefits.BenefitContext(
        cohort=cohort, params=params, baseline=invented_cola(), config=CONFIG
    )
    rows, _ = track_benefits.reference_benefit_rows(
        projection, draw=0, row=REGISTERED_ROWS["R0"], context=context
    )
    by_id = {row["person_id"]: row for row in rows}

    def pia(pid, birth):
        return sb.eligibility_pia_for_clock(
            sb.WorkerClock.at_age_62(birth),
            history=careers[pid],
            birth_year=birth,
            params=params,
        )

    own = sb.OwnBenefit(
        eligibility_pia=pia(1, 1962),
        claim_age_factor=claiming.benefit_factor(64 * 12, 1962, params),
        clock=sb.WorkerClock.at_age_62(1962, entitlement_year=2026),
    )
    spouse = sb.spouse_scenario_paths(
        worker_eligibility_pia=pia(2, 1960),
        worker_clock=sb.WorkerClock.at_age_62(1960, entitlement_year=2024),
        own=own,
        months_early=params.fra_months(1962) - 64 * 12,
        entitlement_year=2026,
        params=params,
        baseline=invented_cola(),
    )
    worker = sb.worker_scenario_paths(
        eligibility_pia=own.eligibility_pia,
        claim_age_factor=own.claim_age_factor,
        clock=own.clock,
        baseline=invented_cola(),
    )
    components = by_id[1]["benefit_components"]
    assert components["spouse"]["base"] == pytest.approx(
        12 * spouse.baseline_monthly_by_payment_year[2030]
    )
    assert components["spouse"]["reform"] == pytest.approx(
        12 * spouse.reform_monthly_by_payment_year[2030]
    )
    assert components["retired_worker"]["reform"] == pytest.approx(
        12 * worker.reform_monthly_by_payment_year[2030]
    )


def test_widow_benefit_equals_the_a6_composition():
    # INVENTED: worker 2 (born 1955) claimed 2019 and died in 2021;
    # widow 1 (born 1958) has no own claim.
    persons = [_static(1, 1958), _static(2, 1955)]
    careers = {1: _career(0.0, 1958), 2: _career(50_000.0, 1955)}
    last_worker = _state(
        2, 1955, 2020, claimed=True, claim_year=2019, spouse_person_id=1
    )
    final = [
        _state(
            1,
            1958,
            2030,
            marital_status="widowed",
            widowhood_year=2021,
            late_spouse_person_id=2,
            widowed_in_projection=True,
        )
    ]
    cohort, projection = _handmade_cohort(
        persons,
        careers,
        final,
        [_state(1, 1958, 2020, spouse_person_id=2), last_worker],
    )
    params = invented_params()
    context = track_benefits.BenefitContext(
        cohort=cohort, params=params, baseline=invented_cola(), config=CONFIG
    )
    rows, _ = track_benefits.reference_benefit_rows(
        projection, draw=0, row=REGISTERED_ROWS["R0"], context=context
    )
    (row,) = rows
    deceased_pia = sb.eligibility_pia_for_clock(
        sb.WorkerClock.at_age_62(1955),
        history=careers[2],
        birth_year=1955,
        params=params,
    )
    a6 = sb.widow_scenario_paths(
        deceased_eligibility_pia=deceased_pia,
        deceased_clock=sb.WorkerClock.at_age_62(1955, entitlement_year=2019),
        deceased_claim_age_factor=claiming.benefit_factor(
            64 * 12, 1955, params
        ),
        own=None,
        survivor_months_early=params.survivor_reduction_period_months
        - 12 * (2021 - 1958 - 60),
        entitlement_year=2021,
        params=params,
        baseline=invented_cola(),
    )
    assert row["benefit_components"]["aged_widow"]["base"] == pytest.approx(
        12 * a6.baseline_monthly_by_payment_year[2030]
    )
    assert row["benefit_components"]["aged_widow"]["reform"] == (
        pytest.approx(12 * a6.reform_monthly_by_payment_year[2030])
    )
    assert row["reduced_increases"] == 2029 - 2017 + 1


def test_widowhood_dated_before_the_roster_death_is_not_paid():
    # INVENTED disagreement: A3 dates 1's widowhood 2005, but the "late"
    # spouse 2 is in the opening roster and dies only in 2021.
    persons = [_static(1, 1950), _static(2, 1948)]
    careers = {1: _career(0.0, 1950), 2: _career(40_000.0, 1948)}
    final = [
        _state(
            1,
            1950,
            2030,
            marital_status="widowed",
            widowhood_year=2005,
            late_spouse_person_id=2,
        )
    ]
    cohort, projection = _handmade_cohort(
        persons,
        careers,
        final,
        [
            _state(1, 1950, 2020, marital_status="widowed"),
            _state(2, 1948, 2020, claimed=True, claim_year=2012),
        ],
    )
    context = track_benefits.BenefitContext(
        cohort=cohort,
        params=invented_params(),
        baseline=invented_cola(),
        config=CONFIG,
    )
    rows, counters = track_benefits.reference_benefit_rows(
        projection, draw=0, row=REGISTERED_ROWS["R0"], context=context
    )
    assert rows == []
    assert counters["widow_death_year_disagrees_with_roster"] == 1


def test_a_flat_population_mortality_is_recorded_as_a_gap(cohort):
    band_model = AgeSexMortalityModel(
        bands=((0, 64), (65, 120)),
        probability={
            ("0-64", "female"): 0.002,
            ("0-64", "male"): 0.003,
            ("65+", "female"): 0.03,
            ("65+", "male"): 0.04,
        },
    )
    config = TrackAConfig(draw_indices=(0,), rows=("R0",))
    flat = run_track_a(
        _inputs(cohort, population_mortality=band_model), config=config
    )
    assert flat["population_mortality"]["class"] == "AgeSexMortalityModel"
    assert flat["population_mortality"]["year_aware"] is False
    assert "no year axis" in flat["population_mortality"]["gap"]
    aware = run_track_a(_inputs(cohort), config=config)
    assert aware["population_mortality"]["year_aware"] is True


# --------------------------------------------------------------------------
# Review fixes (all INVENTED data)
# --------------------------------------------------------------------------
def test_approximate_pia_indexes_to_the_second_year_before_eligibility():
    params = invented_params()
    career = _career(40_000.0, 1970)
    # At the age-62 year the approximation is the oracle's retirement PIA.
    retirement = sb.eligibility_pia_for_clock(
        sb.WorkerClock.at_age_62(1970),
        history=career,
        birth_year=1970,
        params=params,
    )
    assert track_benefits.approximate_pia(
        career,
        birth_year=1970,
        computation_end_year=2032,
        eligibility_year=2032,
        params=params,
    ) == pytest.approx(retirement, abs=0.0)
    # An onset in 2015 (age 45) indexes to 2013, the second year before
    # the onset year whose bend points the PIA uses.
    kept = {year: value for year, value in career.items() if year <= 2015}
    assert benefits.indexed_history(kept, 2015 - 62, params)[2000] == (
        pytest.approx(40_000.0 * params.nawi[2013] / params.nawi[2000])
    )
    expected = benefits.pia(
        benefits.aime(kept, 2015 - 62, params), 2015, params
    )
    approximation = track_benefits.approximate_pia(
        career,
        birth_year=1970,
        computation_end_year=2015,
        eligibility_year=2015,
        params=params,
    )
    assert approximation == pytest.approx(expected, abs=0.0)
    # Indexing to age 60 (2030) against 2015 bend points overstated it.
    age_60_indexed = benefits.pia(
        benefits.aime(kept, 1970, params), 2015, params
    )
    assert age_60_indexed > approximation


def _di_state(person_id, birth, **values):
    return _state(
        person_id, birth, 2030, marital_status="never_married", **values
    )


def test_di_award_after_62_keeps_the_age_62_clock():
    # INVENTED: 1 (born 1954) claimed at 62 in 2016, was awarded DI in
    # 2019 and converted at FRA (66) in 2020.  2 (born 1960) was awarded
    # DI in 2015 at 55 and converted in 2026.
    persons = [_static(1, 1954), _static(2, 1960)]
    careers = {1: _career(45_000.0, 1954), 2: _career(30_000.0, 1960)}
    final = [
        _di_state(
            1,
            1954,
            claimed=True,
            claim_year=2016,
            di_award_year=2019,
            di_conversion_year=2020,
        ),
        _di_state(
            2,
            1960,
            claimed=True,
            claim_year=2026,
            di_award_year=2015,
            di_conversion_year=2026,
        ),
    ]
    initial = [
        _state(1, 1954, 2010, marital_status="never_married"),
        _state(2, 1960, 2010, marital_status="never_married"),
    ]
    cohort, projection = _handmade_cohort(persons, careers, final, initial)
    params = invented_params()
    context = track_benefits.BenefitContext(
        cohort=cohort, params=params, baseline=invented_cola(), config=CONFIG
    )
    by_row = {}
    for row_id in ("R0", "R2"):
        rows, _ = track_benefits.reference_benefit_rows(
            projection, draw=0, row=REGISTERED_ROWS[row_id], context=context
        )
        by_row[row_id] = {row["person_id"]: row for row in rows}
    # R0: the PIA runs from 2016 (age 62), not from the 2019 award.
    assert by_row["R0"][1]["reduced_increases"] == 2029 - 2016 + 1
    assert set(by_row["R0"][1]["benefit_components"]) == {"retired_worker"}
    level = track_benefits.approximate_pia(
        careers[1],
        birth_year=1954,
        computation_end_year=2016,
        eligibility_year=2016,
        params=params,
    )
    path = sb.monthly_benefit_path(
        eligibility_pia=level,
        claim_age_factor=1.0,
        eligibility_year=2016,
        cola=sb.ScenarioCOLARates(
            baseline=invented_cola(), reform=None, exposure_start_year=2016
        ),
        horizon_year=2030,
    )
    assert by_row["R0"][1]["benefit_base"] == pytest.approx(12 * path[2030])
    # R2 keeps the award year as the entitlement year.
    assert by_row["R2"][1]["reduced_increases"] == 2029 - 2019 + 1
    # An award before 62 keeps the award clock under both rows.
    assert by_row["R0"][2]["reduced_increases"] == 2029 - 2015 + 1
    assert by_row["R2"][2]["reduced_increases"] == 2029 - 2015 + 1


def test_converted_opening_disabled_worker_is_reported_as_retired_worker():
    # INVENTED opening disabled workers: 1 (born 1950) converted at FRA in
    # 2016; 2 (born 1975) is still entitled in 2030.
    persons = [_static(1, 1950), _static(2, 1975)]
    careers = {1: _career(0.0, 1950), 2: _career(0.0, 1975)}
    final = [
        _di_state(
            1,
            1950,
            claimed=True,
            claim_year=2016,
            di_award_year=2004,
            di_conversion_year=2016,
        ),
        _di_state(2, 1975, di_entitled=True, di_award_year=2006),
    ]
    initial = [
        _state(1, 1950, 2010, marital_status="never_married"),
        _state(2, 1975, 2010, marital_status="never_married"),
    ]
    cohort, projection = _handmade_cohort(persons, careers, final, initial)
    cohort.persons["opening_status"] = "disabled_worker"
    cohort.persons["ss_receipt_2010"] = pd.array([True, True], "boolean")
    opening = {
        pid: OpeningStockRecord(
            person_id=pid,
            status="disabled_worker",
            component="disabled_worker",
            observed_annual_amount=12_000.0,
            clock_year=clock,
            clock_rule="a3_receipt_start",
            entitlement_year=clock,
            entitlement_clamped=False,
        )
        for pid, clock in ((1, 2004), (2, 2006))
    }
    cohort = replace(cohort, opening=opening)
    context = track_benefits.BenefitContext(
        cohort=cohort,
        params=invented_params(),
        baseline=invented_cola(),
        config=CONFIG,
    )
    rows, counters = track_benefits.reference_benefit_rows(
        projection, draw=0, row=REGISTERED_ROWS["R0"], context=context
    )
    by_id = {row["person_id"]: row for row in rows}
    assert counters["beneficiaries_opening_stock"] == 2
    assert set(by_id[1]["benefit_components"]) == {"retired_worker"}
    assert set(by_id[2]["benefit_components"]) == {"disabled_worker"}
    expected = track_benefits.opening_stock_amounts(
        opening[1],
        baseline=invented_cola(),
        reform=sb.COLAReform(),
        exposure_start_year=2004,
        observed_payment_year=2010,
        payment_year=2030,
        round_to_dime=False,
    )
    assert by_id[1]["benefit_base"] == pytest.approx(12 * expected[0])
    assert by_id[1]["benefit_reform"] == pytest.approx(12 * expected[1])
    assert by_id[1]["reduced_increases"] == 21


def test_opening_disabled_worker_receiving_after_62_keeps_the_age_62_clock():
    # INVENTED row shapes: a non-default A3 spec can classify a 64-year-old
    # first observed receiving in 2010 as a disabled worker.
    config = TrackAConfig(draw_indices=(0,))

    def row(age, receipt):
        return SimpleNamespace(
            person_id=1,
            opening_status="disabled_worker",
            age_2010=age,
            birth_year=2010 - age,
            opening_claim_year=receipt,
            opening_claim_year_upper_bound=2010,
            ss_2010=9_000,
            linked_spouse_birth_year=pd.NA,
        )

    aged, _ = opening_module._opening_record(row(64, 2010), config)
    assert (aged.clock_year, aged.clock_rule) == (
        1946 + 62,
        "own_birth_plus_62_di",
    )
    assert aged.entitlement_year == 2010
    young, _ = opening_module._opening_record(row(50, 2010), config)
    assert (young.clock_year, young.clock_rule) == (2010, "a3_receipt_start")


def test_parameter_consistency_is_recorded(result):
    record = result["parameter_consistency"]
    # Unit tests use invented parameters and never read the TR2008 capture.
    assert record["tr2008_values_compared"] is False
    checks = record["checks"]
    assert set(checks) == {"di_spec", "mortality", "claim_table_max_year"}
    assert checks["di_spec"]["consistent"] is True
    assert checks["claim_table_max_year"]["consistent"] is True
    # The invented mortality model is labelled INVENTED, not intermediate.
    assert checks["mortality"]["consistent"] is False
    assert record["consistent"] is False


def test_mismatched_di_spec_is_recorded(cohort):
    config = TrackAConfig(
        draw_indices=(0,),
        rows=("R0",),
        di_spec=DIEntitlementSpec(post_conversion_mortality="population"),
    )
    run = run_track_a(_inputs(cohort), config=config)
    check = run["parameter_consistency"]["checks"]["di_spec"]
    assert check["consistent"] is False
    assert check["runtime"]["post_conversion_mortality"] == "di_origin"


def test_component_shares_are_weighted_baseline_amount_shares(result):
    # INVENTED rows: draw 0 has a retired worker (weight 2, $10,000) and a
    # widow with $6,000 own and $4,000 widow's excess (weight 1), both 70.
    rows = [
        {
            "draw": 0,
            "age_reference": 70,
            "weight": 2.0,
            "benefit_components": {
                "retired_worker": {"base": 10_000.0, "reform": 1.0}
            },
        },
        {
            "draw": 0,
            "age_reference": 70,
            "weight": 1.0,
            "benefit_components": {
                "retired_worker": {"base": 6_000.0, "reform": 1.0},
                "aged_widow": {"base": 4_000.0, "reform": 1.0},
            },
        },
    ]
    shares = _component_shares(rows, ("retired_worker", "aged_widow"), (0,))
    cell = shares["by_group"]["70-79"]
    assert cell["draws_defined"] == 1
    assert cell["mean_share"] == pytest.approx(
        {"retired_worker": 26_000 / 30_000, "aged_widow": 4_000 / 30_000}
    )
    assert shares["by_group"]["50-61"] == {
        "draws_defined": 0,
        "mean_share": None,
    }
    for row_id, row in result["rows"].items():
        for cell in row["component_shares_by_age_group"]["by_group"].values():
            if cell["mean_share"] is None:
                continue
            assert set(cell["mean_share"]) == set(
                REGISTERED_ROWS[row_id].components
            )
            assert sum(cell["mean_share"].values()) == pytest.approx(1.0)


def test_opening_disabled_widow_is_an_aged_widow_from_60():
    # INVENTED opening survivors labelled disabled widow(er)s in 2010:
    # 1 (born 1955) is 75 in 2030; 2 (born 1975) is 55.
    persons = [_static(1, 1955), _static(2, 1975)]
    careers = {1: _career(0.0, 1955), 2: _career(0.0, 1975)}
    final = [
        _state(1, 1955, 2030, marital_status="widowed", claimed=True),
        _state(2, 1975, 2030, marital_status="widowed", claimed=True),
    ]
    initial = [
        _state(1, 1955, 2010, marital_status="widowed", claimed=True),
        _state(2, 1975, 2010, marital_status="widowed", claimed=True),
    ]
    cohort, projection = _handmade_cohort(persons, careers, final, initial)
    cohort.persons["opening_status"] = "survivor"
    cohort.persons["ss_receipt_2010"] = pd.array([True, True], "boolean")
    opening = {
        pid: OpeningStockRecord(
            person_id=pid,
            status="survivor",
            component="disabled_widow",
            observed_annual_amount=8_000.0,
            clock_year=2007,
            clock_rule="a3_receipt_start",
            entitlement_year=2007,
            entitlement_clamped=False,
        )
        for pid in (1, 2)
    }
    cohort = replace(cohort, opening=opening)
    context = track_benefits.BenefitContext(
        cohort=cohort,
        params=invented_params(),
        baseline=invented_cola(),
        config=CONFIG,
    )
    rows, _ = track_benefits.reference_benefit_rows(
        projection, draw=0, row=REGISTERED_ROWS["R0"], context=context
    )
    by_id = {row["person_id"]: row for row in rows}
    assert set(by_id[1]["benefit_components"]) == {"aged_widow"}
    assert set(by_id[2]["benefit_components"]) == {"disabled_widow"}
    assert by_id[1]["benefit_base"] == pytest.approx(by_id[2]["benefit_base"])
    assert by_id[1]["reduced_increases"] == 21
