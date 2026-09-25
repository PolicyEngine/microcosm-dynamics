"""The M5 careers: M4's cohort to the records the evaluation reads.

No PSID file is read: the cohort is ``invented_psid``'s, and the oracle's
parameters are INVENTED (``invented.invented_parameters``).

Invariants (property and differential tests below):

* a claim factor is 1 for disability origin and death, the oracle's
  402(q)/(w) factor for old age, and below 1 exactly when the claim age
  precedes the full retirement age;
* months early are nonnegative, zero at or after the full retirement age
  (spouse) or the end of the oracle's survivor span (survivor, bounded by
  the span), and fall as the claim year rises;
* every record keeps M4's section 4a years (a differential with the
  cohort's own record), its observed panel years and its observed
  next-wave odd years;
* records built from staged PSID files cannot be marked invented, and
  records marked invented need the invented generator's label.
"""

from __future__ import annotations

import dataclasses

import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.data import prior_year_labor_income as pyl
from populace_dynamics.min_benefit_track_m import (
    careers,
    cohort,
    invented,
    invented_psid,
    pipeline,
    rules,
)
from populace_dynamics.min_benefit_track_m.evaluation import (
    INVENTED,
    PSID_FILES,
)


@pytest.fixture(scope="module")
def parameters():
    return invented.invented_parameters()


@pytest.fixture(scope="module")
def built():
    frames = invented_psid.invented_cohort_inputs(seed=7, n_family_units=120)
    return frames, cohort.build_cohort(frames)


def _inputs(built, parameters, **kwargs):
    frames, cohort_ = built
    params, cola = parameters
    options = {
        "earnings": frames.earnings,
        "prior_year": frames.prior_year_labor,
        "params": params.params,
        "cola_rates": cola,
        "provenance_kind": INVENTED,
        **kwargs,
    }
    return careers.build_track_m_inputs(cohort_, **options)


# ---------------------------------------------------------------------------
# Claim factors and months early
# ---------------------------------------------------------------------------
@settings(max_examples=200, deadline=None)
@given(
    st.integers(min_value=1930, max_value=1960),
    st.integers(min_value=62, max_value=75),
)
def test_a_claim_factor_follows_the_claim_age(parameters, birth, age):
    params = parameters[0].params
    factor = careers.own_claim_factor(
        cohort.BASIS_OLD_AGE, birth, birth + age, params
    )
    assert factor == rules.claim_factor(birth, birth + age, params)
    months = 12 * age - params.fra_months(birth)
    assert (factor < 1.0) is (months < 0)
    assert factor > 0
    for basis in (cohort.BASIS_DISABILITY, cohort.BASIS_DEATH):
        assert careers.own_claim_factor(basis, birth, birth + age, params) == 1


@settings(max_examples=200, deadline=None)
@given(
    st.integers(min_value=1925, max_value=1960),
    st.integers(min_value=55, max_value=80),
)
def test_months_early_are_bounded_and_fall_with_the_claim(
    parameters, birth, age
):
    params = parameters[0].params
    spouse = careers.spouse_months_early(birth, birth + age, params)
    later = careers.spouse_months_early(birth, birth + age + 1, params)
    assert 0 <= later <= spouse
    assert (spouse == 0) is (12 * age >= params.fra_months(birth))
    survivor = careers.survivor_months_early(birth, birth + age, params)
    span = params.survivor_reduction_period_months
    end = 12 * params.survivor_earliest_claim_age + span
    assert 0 <= survivor <= span
    assert survivor == min(max(0, end - 12 * age), span)
    assert careers.survivor_months_early(birth, birth + age + 1, params) <= (
        survivor
    )


def test_the_oracle_domain_is_checked_before_computing():
    records = pd.DataFrame(
        {
            "record_id": ["W1", "W2", "W3", "W4"],
            "birth_year": [1912, 1940, 1930, 1914],
            "window_year": [1990, 2004, 2005, 1990],
            "threshold_year": [1974, 2002, 1978, 1976],
        }
    )
    with pytest.raises(ValueError, match="outside the oracle"):
        careers.check_oracle_domain(records)
    # a record in a window whose bend-point year precedes 1979: the
    # oracle's formula is the 1979 one
    with pytest.raises(ValueError, match="before 1979"):
        careers.check_oracle_domain(records.iloc[1:])
    careers.check_oracle_domain(records.iloc[[1, 3]])
    assert careers.FIRST_PIA_FORMULA_YEAR == 1979


def test_observed_histories_refuse_what_a_panel_cannot_hold():
    panel = pd.DataFrame(
        {
            "person_id": [1, 1, 1, 2],
            "period": [2020, 2022, 2024, 2020],
            "earnings": [10.0, float("nan"), 5.0, 0.0],
        }
    )
    assert careers.observed_histories(panel) == {
        1: {2020: 10.0},
        2: {2020: 0.0},
    }
    assert careers.observed_histories(panel, {2}) == {2: {2020: 0.0}}
    with pytest.raises(ValueError, match="negative"):
        careers.observed_histories(panel.assign(earnings=-1.0))
    with pytest.raises(ValueError, match="two panel rows"):
        careers.observed_histories(pd.concat([panel, panel]))


# ---------------------------------------------------------------------------
# The records
# ---------------------------------------------------------------------------
def test_every_record_keeps_the_cohorts_years_and_histories(built, parameters):
    """Differential: each WorkerRecord's section 4a years (through
    ``rules.record_years``) equal M4's record, and its histories are the
    panel's and the next wave's observed items."""

    frames, cohort_ = built
    inputs = _inputs(built, parameters)
    records = cohort_.records.set_index("record_id")
    assert set(inputs.workers) == set(records.index)
    panel = careers.observed_histories(frames.earnings)
    odd = pyl.next_wave_histories(frames.prior_year_labor)
    for key, worker in inputs.workers.items():
        row = records.loc[key]
        years = worker.years
        assert years.threshold_year == row["threshold_year"]
        assert years.last_year == row["last_year"]
        assert years.window_year == row["window_year"]
        assert worker.basis == row["basis"]
        pid = int(row["person_id"])
        assert dict(worker.observed) == panel.get(pid, {})
        assert dict(worker.next_wave) == odd.get(pid, {})
        assert worker.unresolved == bool(row["unresolved"])
    persons = cohort_.persons.set_index("person_id")
    assert len(inputs.persons) == len(persons)
    for person in inputs.persons:
        row = persons.loc[int(person.person_id)]
        assert person.paid_own_worker_benefit == row["paid_own_worker_benefit"]
        assert person.unlinked_auxiliary == row["unlinked_auxiliary"]
        if person.own_record_id is not None:
            worker = inputs.workers[person.own_record_id]
            assert person.own_claim_factor == careers.own_claim_factor(
                worker.basis,
                worker.birth_year,
                worker.window_year,
                parameters[0].params,
            )
    in_scope = [w for w in inputs.workers.values() if w.ms5_in_scope]
    assert in_scope
    for worker in in_scope:
        assert worker.observed_benefit_2022 > 0
        assert worker.cola_factor == rules.cola_factor(
            worker.years.threshold_year, parameters[1]
        )


def test_the_records_run_through_every_registered_row(built, parameters):
    inputs = _inputs(built, parameters)
    result = pipeline.run_track_m(
        inputs, parameters[0], data_provenance=INVENTED
    )
    assert list(result["rows"]) == [f"MS{i}" for i in range(7)]
    for row in result["rows"].values():
        assert len(row["tabulation"]["cells"]) == 12
        assert row["diagnostics"]["worker_flag_nesting_violations"] == 0
    assert result["header"] == invented_psid.INVENTED_LABEL


def test_psid_records_cannot_be_marked_invented(built, parameters):
    frames, cohort_ = built
    hashed = dataclasses.replace(
        cohort_,
        provenance={
            **dict(cohort_.provenance),
            careers.PSID_FILES_SOURCE_KEY: {"INVENTED.txt": "0" * 64},
        },
    )
    with pytest.raises(ValueError, match="marked psid_files"):
        _inputs((frames, hashed), parameters)
    marked = _inputs((frames, hashed), parameters, provenance_kind=PSID_FILES)
    assert marked.source[careers.PSID_FILES_SOURCE_KEY]
    # invented records need the invented generator's label
    unlabelled = dataclasses.replace(cohort_, provenance={"seed": 7})
    with pytest.raises(ValueError, match="invented label"):
        _inputs((frames, unlabelled), parameters)
    with pytest.raises(ValueError, match="provenance_kind"):
        _inputs(built, parameters, provenance_kind="real")
    assert careers.PSID_FILES_SOURCE_KEY == pipeline.PSID_FILES_SOURCE_KEY


def test_ms5_before_the_cola_history_is_refused_in_a_window(built, parameters):
    """MS5's COLA factor needs the COLAs from the threshold year: a record
    in MS5's scope whose threshold year precedes the committed history is
    refused inside a policy window and keeps the MS0 PIA outside one."""

    frames, cohort_ = built
    params, cola = parameters
    persons = cohort_.persons
    records = cohort_.records.set_index("record_id")
    scoped = list(persons.loc[persons["ms5_in_scope"], "own_record_id"])
    inside = [k for k in scoped if records.loc[k, "window_year"] >= 2004]
    outside = [k for k in scoped if records.loc[k, "window_year"] < 2004]
    assert inside and outside

    def build(first_year):
        return careers.build_track_m_inputs(
            cohort_,
            earnings=frames.earnings,
            prior_year=frames.prior_year_labor,
            params=params.params,
            cola_rates={y: r for y, r in cola.items() if y >= first_year},
            provenance_kind=INVENTED,
        )

    earliest_inside = int(records.loc[inside, "threshold_year"].min())
    with pytest.raises(ValueError, match="committed COLA history"):
        build(earliest_inside + 1)
    dropped = int(
        (records.loc[outside, "threshold_year"] < earliest_inside).sum()
    )
    assert dropped > 0
    kept = build(earliest_inside)
    diagnostics = kept.source["careers_diagnostics"]
    assert diagnostics["ms5_out_of_window_before_cola_history"] == dropped
    in_scope = {k for k, w in kept.workers.items() if w.ms5_in_scope}
    assert set(inside) <= in_scope
    assert len(in_scope) == len(scoped) - dropped


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_row_deductions_hold_through_m4_and_m5(parameters, seed):
    """Deductions from the rules, on cohorts built by M4 and M5 (not
    results): MS3's receivers are a subset of MS0's person by person
    (only the counting rule differs); MS4's flagged workers a subset of
    MS0's (its window lies inside); option 2's flagged workers inside
    option 4's and option 3's inside option 5's (M1 section 8); and the
    evaluation is deterministic."""

    from populace_dynamics.min_benefit_track_m.evaluation import evaluate
    from populace_dynamics.min_benefit_track_m.policy import policy_for_row

    params, cola = parameters
    frames = invented_psid.invented_cohort_inputs(seed=seed, n_family_units=60)
    inputs = careers.build_track_m_inputs(
        cohort.build_cohort(frames),
        earnings=frames.earnings,
        prior_year=frames.prior_year_labor,
        params=params.params,
        cola_rates=cola,
        provenance_kind=INVENTED,
    )
    ms0 = evaluate(inputs, policy_for_row("MS0"), params)
    ms3 = evaluate(inputs, policy_for_row("MS3"), params)
    ms4 = evaluate(inputs, policy_for_row("MS4"), params)
    again = evaluate(inputs, policy_for_row("MS0"), params)
    pd.testing.assert_frame_equal(ms0.rows, again.rows)
    for number in (2, 3, 4, 5):
        column = f"receives_{number}"
        assert not (ms3.rows[column] & ~ms0.rows[column]).any()
        for key, outcome in ms4.workers.items():
            if outcome.outcomes[number].on_minimum:
                assert ms0.workers[key].outcomes[number].on_minimum
    for evaluation in (ms0, ms3, ms4):
        for outcome in evaluation.workers.values():
            flags = {n: outcome.outcomes[n].on_minimum for n in (2, 3, 4, 5)}
            assert not (flags[2] and not flags[4])
            assert not (flags[3] and not flags[5])
