"""Track M's record evaluation on INVENTED records and parameters.

Every record, history, weight and parameter here is **INVENTED**
(``invented.invented_parameters``): no PSID value, Census value, SSA value
or comparator value.  Each expectation follows from the M1 specification's
rules (sections 4a, 4b, 5, 6 and 9) or recomposes the rules by hand.
"""

from __future__ import annotations

import pandas as pd
import pytest

from populace_dynamics.min_benefit_track_m import coverage, invented, rules
from populace_dynamics.min_benefit_track_m import evaluation as ev
from populace_dynamics.min_benefit_track_m import policy as pol

PARAMETERS, COLA = invented.invented_parameters()
DESIGN = pd.DataFrame({"stratum": [1, 1, 2, 2], "cluster": [1, 2, 1, 2]})


def flat(birth: int, last: int, amount: float) -> dict[int, float]:
    """Panel-shaped: every year to 1996, even years from 1998."""

    return {
        year: amount
        for year in range(max(1968, birth + 22), last + 1)
        if year < 1997 or year % 2 == 0
    }


def low_worker(record_id="W1", birth=1945, window=2008, amount=4_000.0):
    return ev.WorkerRecord(
        record_id,
        birth,
        rules.BASIS_OLD_AGE,
        window,
        flat(birth, window - 1, amount),
    )


def person(pid, **kwargs):
    base = {
        "person_id": pid,
        "family_unit_id": f"F{pid}",
        "weight": 1.0,
        "sex": "female",
        "stratum": 1,
        "cluster": 1,
    }
    base.update(kwargs)
    return ev.PersonRecord(**base)


def inputs(workers, persons, kind=ev.INVENTED):
    return ev.TrackMInputs(
        workers={w.record_id: w for w in workers},
        persons=tuple(persons),
        provenance_kind=kind,
        design=DESIGN,
    )


def test_a_worker_record_recomposes_the_rules():
    record = low_worker()
    policy = pol.TrackMPolicy()
    out = ev.evaluate_worker_record(record, policy, PARAMETERS)
    history = coverage.one_history(record.observed, last_year=2007)
    count = coverage.count_coverage_years(
        history.values,
        birth_year=1945,
        through_year=2007,
        qc=PARAMETERS.qc,
        nawi=PARAMETERS.nawi,
        gap_years=(),
        imputed_years=history.imputed_years,
    )
    pia = rules.history_pia(
        history.values,
        birth_year=1945,
        params=PARAMETERS.params,
        window_year=2008,
    )
    assert out.years.threshold_year == 2007  # attaining 62
    # 2007 takes its left neighbor only: 2008 is after the last year
    assert out.history.imputed_years == (
        1997,
        1999,
        2001,
        2003,
        2005,
        2007,
    )
    assert out.count == count
    assert out.history_pia == pia and out.pia == pia.pia
    inputs_ = rules.WorkerInputs(
        pia=pia.pia,
        work_years=count.years,
        first_pia_year=2008,
        threshold_year=2007,
        birth_year=1945,
    )
    for number in pol.OPTIONS:
        assert out.outcomes[number] == rules.evaluate_worker(
            inputs_,
            number,
            thresholds=PARAMETERS.thresholds,
            nawi=PARAMETERS.nawi,
        )
    # the imputed odd years at the same low amount changed Y
    assert out.work_years_without_imputation < out.count.years


def test_next_wave_items_feed_y_and_p():
    base = low_worker()
    reported = ev.WorkerRecord(
        "W1",
        1945,
        rules.BASIS_OLD_AGE,
        2008,
        base.observed,
        next_wave={2001: 90_000.0, 2003: 90_000.0},
    )
    a = ev.evaluate_worker_record(base, pol.TrackMPolicy(), PARAMETERS)
    b = ev.evaluate_worker_record(reported, pol.TrackMPolicy(), PARAMETERS)
    assert b.history.next_wave_years == (2001, 2003)
    assert 2001 not in b.history.imputed_years
    assert b.history_pia.pia > a.history_pia.pia


def test_ms5_uses_the_benefit_implied_pia_in_scope_only():
    record = ev.WorkerRecord(
        "W1",
        1945,
        rules.BASIS_OLD_AGE,
        2008,
        flat(1945, 2007, 4_000.0),
        ms5_in_scope=True,
        observed_benefit_2022=900.0,
        claim_factor=0.75,
        cola_factor=1.5,
    )
    ms0 = ev.evaluate_worker_record(record, pol.TrackMPolicy(), PARAMETERS)
    ms5 = ev.evaluate_worker_record(
        record, pol.policy_for_row("MS5"), PARAMETERS
    )
    assert ms0.pia_source == "history_oracle"
    assert ms5.pia_source == "benefit_implied"
    # 900 / (0.75 x 1.5) = 800
    assert ms5.pia == pytest.approx(800.0)
    assert ms0.benefit_implied_pia == pytest.approx(800.0)
    out_of_scope = low_worker()
    ms5_out = ev.evaluate_worker_record(
        out_of_scope, pol.policy_for_row("MS5"), PARAMETERS
    )
    assert ms5_out.pia_source == "history_oracle"
    with pytest.raises(ValueError, match="MS5"):
        ev.WorkerRecord(
            "W2",
            1945,
            rules.BASIS_OLD_AGE,
            2008,
            {},
            ms5_in_scope=True,
        )


def test_spouse_and_survivor_receipt_follow_g23_and_ms3():
    worker = low_worker("W1")
    spouse = person(
        "S",
        links=(ev.Link("spouse", "W1", months_early=0),),
    )
    head = person(
        "H",
        sex="male",
        own_record_id="W1",
        paid_own_worker_benefit=True,
        own_claim_factor=0.8,
    )
    run = ev.evaluate(
        inputs([worker], [head, spouse]), pol.TrackMPolicy(), PARAMETERS
    )
    flagged = run.workers["W1"].outcomes[2].on_minimum
    assert flagged  # a low career in the window is on option 2's minimum
    rows = run.rows.set_index("person_id")
    assert rows.loc["H", "receives_2"] and rows.loc["H", "basis"] == (
        "own_worker_pia"
    )
    # plan case F: the spouse with no own benefit counts under G23 ...
    assert rows.loc["S", "receives_2"]
    assert rows.loc["S", "basis"] == "linked_worker_pia"
    # ... and not under MS3
    ms3 = ev.evaluate(
        inputs([worker], [head, spouse]),
        pol.policy_for_row("MS3"),
        PARAMETERS,
    ).rows.set_index("person_id")
    assert ms3.loc["H", "receives_2"] and not ms3.loc["S", "receives_2"]


def _ms5_record(record_id, birth, window, pia, history_amount):
    return ev.WorkerRecord(
        record_id,
        birth,
        rules.BASIS_OLD_AGE,
        window,
        flat(birth, window - 1, history_amount),
        ms5_in_scope=True,
        observed_benefit_2022=pia,
        claim_factor=1.0,
        cola_factor=1.0,
    )


def test_a_survivors_own_amount_is_the_reduced_own_benefit():
    """Section 4b rule 5 (42 USC 402(k)(3)(A)): the survivor's own amount
    is the own benefit after 402(q), not the own PIA.  Under MS5 the
    invented observed benefits fix the PIAs: the deceased's is $1,000 (in
    the window, 40 work years, on option 4's minimum of 1.2 x T(2020) / 12
    = $1,213.60 against 0.8636 x 1,000 = $863.60), the survivor's own is
    $1,300 (before the window) with a claim factor of 0.7.  The widow(er)'s
    benefit, $1,213.60 at the survivor's FRA, exceeds the reduced own
    amount (0.7 x 1,300 = $910) but not the own PIA ($1,300): it is paid,
    so the survivor receives the minimum through the deceased's record."""

    deceased = _ms5_record("D1", 1958, 2020, 1_000.0, 20_000.0)
    own = _ms5_record("O1", 1938, 2000, 1_300.0, 20_000.0)
    widow = person(
        "W",
        own_record_id="O1",
        paid_own_worker_benefit=True,
        own_claim_factor=0.7,
        links=(ev.Link("survivor", "D1", months_early=0),),
    )
    out = ev.evaluate(
        inputs([deceased, own], [widow]),
        pol.policy_for_row("MS5"),
        PARAMETERS,
    )
    dead = out.workers["D1"].outcomes[4]
    assert out.workers["D1"].count.years == 40
    assert dead.on_minimum
    t2020 = PARAMETERS.thresholds.for_year(2020)
    assert dead.option_pia == pytest.approx(1.2 * t2020 / 12)
    assert 910.0 < dead.option_pia < 1_300.0
    assert not out.workers["O1"].outcomes[4].on_minimum
    row = out.rows.iloc[0]
    assert row["receives_4"] and row["basis"] == "linked_worker_pia"
    # with the unreduced own PIA the widow(er)'s benefit would not be paid
    assert not rules.survivor_excess_paid(
        1_300.0, dead.option_pia, 0, 1.0, PARAMETERS.params
    )


def test_unlinked_auxiliaries_and_links_to_missing_records():
    worker = low_worker()
    unlinked = person("U", unlinked_auxiliary=True)
    run = ev.evaluate(
        inputs([worker], [unlinked]), pol.TrackMPolicy(), PARAMETERS
    )
    row = run.rows.iloc[0]
    assert not row["receives_2"] and row["basis"] == "unlinked_auxiliary"
    assert run.diagnostics["unlinked_auxiliaries"] == 1
    with pytest.raises(ValueError, match="no worker record"):
        inputs([worker], [person("X", links=(ev.Link("spouse", "W9"),))])
    with pytest.raises(ValueError, match="duplicate person_id"):
        inputs([worker], [person("X"), person("X")])
    with pytest.raises(ValueError, match="provenance_kind"):
        inputs([worker], [person("X")], kind="survey")
    with pytest.raises(ValueError, match="own record"):
        person("X", paid_own_worker_benefit=True)


def test_needed_threshold_years_cover_windows_and_base_years():
    in_window = low_worker("A", birth=1945, window=2008)  # threshold 2007
    before = low_worker("B", birth=1935, window=1999)  # out of every window
    di = ev.WorkerRecord(
        "C",
        1960,
        rules.BASIS_DISABILITY,
        2005,
        flat(1960, 2003, 20_000.0),
        onset_year=2004,
    )
    died = ev.WorkerRecord(
        "D",
        1955,
        rules.BASIS_DEATH,
        2012,
        flat(1955, 2006, 20_000.0),
        death_year=2007,
    )
    policies = [pol.policy_for_row(row) for row in pol.REGISTERED_ROWS]
    needed = ev.needed_threshold_years([in_window, before, di, died], policies)
    assert needed == {2004: 1, 2007: 2}
    early = low_worker("E", birth=1936, window=2004)  # attaining 62: 1998
    with pytest.raises(rules.ThresholdYearMissingError, match="1998"):
        rules.check_threshold_years(
            ev.needed_threshold_years([early], policies),
            PARAMETERS.thresholds,
        )


def test_diagnostics_are_counts_and_bands():
    params, cola = invented.invented_parameters()
    cohort = invented.invented_track_m_inputs(
        seed=3, n_family_units=120, params=params.params, cola_rates=cola
    )
    run = ev.evaluate(cohort, pol.TrackMPolicy(), params)
    diagnostics = run.diagnostics
    assert diagnostics["worker_flag_nesting_violations"] == 0
    assert diagnostics["persons"] == len(cohort.persons)
    assert set(diagnostics["worker_records_by_basis"]) == set(rules.BASES)
    assert diagnostics["earliest_threshold_year_in_window"] >= 2003
    bands = diagnostics["work_years_star_bands_in_window"]
    assert sum(bands.values()) == sum(
        diagnostics["in_window_records_by_basis"].values()
    )
    assert run.rows.attrs["provenance_kind"] == ev.INVENTED


def test_links_the_rules_cannot_produce_are_refused():
    died = ev.WorkerRecord(
        "D",
        1950,
        rules.BASIS_DEATH,
        2012,
        flat(1950, 2009, 20_000.0),
        death_year=2010,
    )
    living = low_worker("W1")
    with pytest.raises(ValueError, match="own record cannot be"):
        inputs([died], [person("X", own_record_id="D")])
    with pytest.raises(ValueError, match="living worker"):
        inputs([died], [person("X", links=(ev.Link("spouse", "D"),))])
    with pytest.raises(ValueError, match="own record"):
        inputs(
            [living],
            [
                person(
                    "X",
                    own_record_id="W1",
                    links=(ev.Link("survivor", "W1"),),
                )
            ],
        )
    # a survivor's link to a death-basis record is the rule's case
    inputs([died], [person("X", links=(ev.Link("survivor", "D"),))])


def test_a_dual_entitled_widow_on_her_own_minimum_counts_under_ms3():
    """Referee O1 (fn. 33's distinction): her own worker PIA rests on the
    minimum and is paid, so she counts under G23 and MS3 alike, although a
    larger survivor's benefit on her late husband's high record is also
    paid on top of it."""

    own = low_worker("O1", birth=1945, window=2008, amount=4_000.0)
    husband = ev.WorkerRecord(
        "H1",
        1943,
        rules.BASIS_OLD_AGE,
        2009,
        flat(1943, 2008, 60_000.0),
    )
    widow = person(
        "W",
        own_record_id="O1",
        paid_own_worker_benefit=True,
        own_claim_factor=0.8,
        links=(ev.Link("survivor", "H1", months_early=0),),
    )
    for row in ("MS0", "MS3"):
        run = ev.evaluate(
            inputs([own, husband], [widow]),
            pol.policy_for_row(row),
            PARAMETERS,
        )
        assert run.workers["O1"].outcomes[2].on_minimum
        assert not run.workers["H1"].outcomes[2].on_minimum
        result = run.rows.iloc[0]
        assert result["receives_2"], row
        assert result["basis"] == "own_worker_pia"
    own_amount = run.workers["O1"].outcomes[2].option_pia * 0.8
    assert rules.survivor_excess_paid(
        own_amount,
        run.workers["H1"].outcomes[2].option_pia,
        0,
        1.0,
        PARAMETERS.params,
    )


def test_a_di_record_with_early_work_years_is_capped_at_40():
    """Referee O1 and Q4: work before 22 counts in Y, so Y may exceed the
    elapsed years D; Y* is capped at 40 (d219 item 6).  Born 1960, work
    every year from 14 (1974) through the year before onset in 2004:
    Y = 30 against D = 2004 - 1982 = 22, so Y* = min(30 x 40 / 22, 40)."""

    history = {
        year: 20_000.0
        for year in range(1974, 2004)
        if year < 1997 or year % 2 == 0
    }
    di = ev.WorkerRecord(
        "DI",
        1960,
        rules.BASIS_DISABILITY,
        2005,
        history,
        onset_year=2004,
    )
    run = ev.evaluate(
        inputs([di], [person("P", own_record_id="DI")]),
        pol.TrackMPolicy(),
        PARAMETERS,
    )
    out = run.workers["DI"]
    assert out.count.years == 30
    assert out.years.threshold_year == 2004 and out.years.last_year == 2003
    assert out.outcomes[2].work_years_star == 40.0
    assert run.diagnostics["di_records_with_y_above_d"] == 1


def test_a_worker_who_died_before_entitlement_follows_the_death_row():
    """Section 4a's death row: the window year is the survivor's first
    entitlement on the record (2012), the threshold year the earlier of
    death (2010) and attaining 62 (2012), and the history ends with the
    year before death, so earnings in the death year change nothing."""

    base = flat(1950, 2009, 20_000.0)
    died = ev.WorkerRecord(
        "D", 1950, rules.BASIS_DEATH, 2012, base, death_year=2010
    )
    later = ev.WorkerRecord(
        "D",
        1950,
        rules.BASIS_DEATH,
        2012,
        {**base, 2010: 90_000.0},
        death_year=2010,
    )
    a = ev.evaluate_worker_record(died, pol.TrackMPolicy(), PARAMETERS)
    b = ev.evaluate_worker_record(later, pol.TrackMPolicy(), PARAMETERS)
    assert a.years.window_year == 2012
    assert a.years.threshold_year == 2010 and a.years.last_year == 2009
    assert "death_year" in a.history_pia.method
    assert a.history_pia == b.history_pia and a.count == b.count
    # no proration: a death-basis record is not a DI record
    assert a.outcomes[2].work_years_star == a.count.years


def test_the_pia_source_diagnostic_counts_ms5_records():
    record = ev.WorkerRecord(
        "W1",
        1945,
        rules.BASIS_OLD_AGE,
        2008,
        flat(1945, 2007, 4_000.0),
        ms5_in_scope=True,
        observed_benefit_2022=900.0,
        claim_factor=0.75,
        cola_factor=1.5,
    )
    other = low_worker("W2")
    cohort = inputs(
        [record, other],
        [
            person("A", own_record_id="W1"),
            person("B", own_record_id="W2"),
        ],
    )
    ms0 = ev.evaluate(cohort, pol.TrackMPolicy(), PARAMETERS)
    ms5 = ev.evaluate(cohort, pol.policy_for_row("MS5"), PARAMETERS)
    assert ms0.diagnostics["pia_source_by_record"] == {
        "history_oracle": 2,
        "benefit_implied": 0,
    }
    assert ms5.diagnostics["pia_source_by_record"] == {
        "history_oracle": 1,
        "benefit_implied": 1,
    }
    assert (
        ms5.diagnostics["benefit_implied_over_history_pia"]["n_records"] == 1
    )


def test_a_late_claimer_uses_a_threshold_year_before_the_policy_year():
    """Referee O1 and section 4's finding: born 1941 and first entitled in
    2005, at 64, the record is in the window (2005 >= 2004) with the
    threshold year of attaining 62, 2003.  Option 2 reads T(2003); option
    3 carries T(2004) by AWI(2001) / AWI(2002) (G9)."""

    record = low_worker("L", birth=1941, window=2005, amount=4_000.0)
    out = ev.evaluate_worker_record(record, pol.TrackMPolicy(), PARAMETERS)
    assert out.years.threshold_year == 2003
    assert out.outcomes[2].in_window and out.outcomes[2].on_minimum
    stars = out.outcomes[2].work_years_star
    t2003 = PARAMETERS.thresholds.for_year(2003)
    assert out.outcomes[2].minimum == pytest.approx(
        pol.STANDARD.share(stars) * t2003 / 12
    )
    nawi = PARAMETERS.nawi
    wage = PARAMETERS.thresholds.for_year(2004) * nawi[2001] / nawi[2002]
    assert out.outcomes[3].minimum == pytest.approx(
        pol.STANDARD.share(stars) * wage / 12
    )
    # MS4 (after the policy year) still reaches a 2005 entitlement
    ms4 = ev.evaluate_worker_record(
        record, pol.policy_for_row("MS4"), PARAMETERS
    )
    assert ms4.outcomes[2].in_window
