"""Track M's choices: Max's rulings and the frozen choices, all explicit.

No data: only the policy module's constants.  Max ruled cos decision d219
on 2026-09-24 (all nine defaults accepted) and d279 and d280 on
2026-09-25; every ruled field defaults to its ruling, and every other
choice is frozen in ``m1-draft-2`` and listed with its basis.
"""

from __future__ import annotations

import dataclasses

import pytest

from populace_dynamics.min_benefit_track_m import policy as pol


def test_defaults_are_the_rulings_and_the_frozen_choices():
    policy = pol.TrackMPolicy()
    assert policy.policy_year == 2004  # G2, d219 item 3
    assert policy.window_rule == pol.WINDOW_IN_OR_AFTER  # G4
    assert policy.order == pol.ORDER_FLOOR_AFTER_CUT  # G10, item 5
    assert policy.counting_rule == pol.COUNT_OWN_OR_LINKED  # G23, item 7
    assert policy.pia_rule == pol.PIA_HISTORY  # G5
    # referee R5: the statutory DI and death computations are primary
    assert policy.di_pia_rule == pol.DI_PIA_STATUTORY
    assert policy.death_pia_rule == pol.DEATH_PIA_STATUTORY
    assert policy.di_proration == pol.DI_PRORATION_ELAPSED  # G12, item 6
    assert (policy.di_proration_start_age, policy.di_proration_cap_years) == (
        22,
        40,
    )
    assert policy.covered_earnings_rule == pol.COVERED_LABOR_INCOME  # d280
    # referee R6: the statute before 1978
    assert policy.pre_1978_coverage_rule == (
        pol.PRE_1978_STATUTE_50_PER_QUARTER
    )
    # referee R7, R3, R4
    assert policy.odd_year_source == pol.ODD_YEARS_NEXT_WAVE
    assert policy.gap_year_rule == pol.GAP_YEARS_NEIGHBOR
    assert policy.old_age_history_end == "year_before_first_entitlement"
    assert policy.di_coverage_end == "year_before_onset"
    assert policy.death_first_pia_year == "first_entitlement_on_record"
    assert policy.entitlement_year_rule == "earliest_consistent"
    assert policy.onset_year_rule == "entitlement_year_minus_1"
    assert policy.survivor_own_amount == "own_benefit_after_402q"
    assert policy.threshold_year_rule == pol.THRESHOLD_YEAR_SECTION_4A
    assert policy.quarters_per_work_year == 4  # Table 5: 4 CQ
    assert pol.HEADLINE_CELL == (2, "all")
    assert pol.TABLE6_OPTIONS == (2, 3, 4, 5)
    assert pol.TABLE6_ROWS == ("all", "men", "women")


def test_registered_rows_change_one_field_each():
    base = pol.TrackMPolicy()
    expected = {
        "MS0": {},
        "MS1": {"policy_year": 2007},
        "MS2": {"order": pol.ORDER_CUT_AFTER_FLOOR},
        "MS3": {"counting_rule": pol.COUNT_OWN_ONLY},
        "MS4": {"window_rule": pol.WINDOW_AFTER},
        "MS5": {"pia_rule": pol.PIA_BENEFIT_IMPLIED},
        # referee R5: MS6 is now Track A's approximation
        "MS6": {"di_pia_rule": pol.DI_PIA_APPROXIMATE},
    }
    assert pol.REGISTERED_ROWS == expected
    for row, change in expected.items():
        row_policy = pol.policy_for_row(row)
        differing = {
            field.name
            for field in dataclasses.fields(row_policy)
            if getattr(row_policy, field.name) != getattr(base, field.name)
        }
        assert differing == set(change), row
    with pytest.raises(ValueError):
        pol.policy_for_row("MS7")


def test_unknown_values_are_refused():
    with pytest.raises(ValueError):
        pol.TrackMPolicy(policy_year=2005)
    with pytest.raises(ValueError):
        pol.TrackMPolicy(order="whichever")
    with pytest.raises(ValueError):
        pol.TrackMPolicy(di_proration_cap_years=35)
    with pytest.raises(ValueError):
        pol.TrackMPolicy(quarters_per_work_year=3)
    with pytest.raises(TypeError):
        pol.TrackMPolicy(di_proration_start_age=22.0)
    # A float policy year equals 2004 but is not a year (review fix).
    with pytest.raises(TypeError):
        pol.TrackMPolicy(policy_year=2004.0)
    # referee R5: the approximation is no longer a death rule
    with pytest.raises(ValueError):
        pol.TrackMPolicy(death_pia_rule=pol.DI_PIA_APPROXIMATE)
    # referee R7: the odd-year source has one value
    with pytest.raises(ValueError):
        pol.TrackMPolicy(odd_year_source="panel_only")


def test_every_d219_item_is_ruled_as_filed():
    items = pol.d219_items()
    assert sorted(items) == list(range(1, 10))
    d219 = {
        name: entry
        for name, entry in pol.MAX_RULINGS.items()
        if entry["decision_record"] == "d219"
    }
    assert [entry["item"] for entry in d219.values()] == list(range(1, 10))
    policy = pol.TrackMPolicy()
    for name, entry in d219.items():
        field_name, as_filed = items[entry["item"]]
        assert field_name == name
        assert entry["as_filed"] == as_filed
        assert entry["ruled_on"] == "2026-09-24"
        if hasattr(policy, name):
            assert getattr(policy, name) == entry["ruling"]
        else:
            assert pol.fixed_decision_value(name) == entry["ruling"]
    assert d219["acceptance_rule"]["ruling"] is None
    assert d219["policy_year"]["alternative_registered_as"] == "MS1"
    assert d219["order"]["alternative_registered_as"] == "MS2"
    assert d219["counting_rule"]["alternative_registered_as"] == "MS3"


def test_item_4_is_recorded_as_its_cos_text_words_it():
    """Referee R2: item 4 as filed names the module placement only; the
    covered-earnings convention is Max's separate ruling d280."""

    field_name, as_filed = pol.d219_items()[4]
    assert field_name == "rules_module_placement"
    assert as_filed.startswith(
        "years-of-coverage counting and the minimum rules in a new Python "
        "module outside ss/, calling the oracle unchanged"
    )
    assert "labor income" not in as_filed.split("(")[0]
    assert "d280" in as_filed
    covered = pol.MAX_RULINGS["covered_earnings_rule"]
    assert covered["decision_record"] == "d280"
    assert covered["ruling"] == pol.COVERED_LABOR_INCOME
    assert covered["ruled_on"] == "2026-09-25"
    assert covered["disclosure"] == "specification_and_every_result"
    download = pol.MAX_RULINGS["census_threshold_download"]
    assert download["decision_record"] == "d279"
    assert "any earlier year the build proves it needs" in download["as_filed"]


def test_max_rulings_report_departures():
    assert pol.rulings_departures(pol.TrackMPolicy()) == []
    for row in ("MS0", "MS4", "MS5", "MS6"):
        assert pol.rulings_departures(pol.policy_for_row(row)) == []
    assert pol.rulings_departures(pol.policy_for_row("MS1")) == ["policy_year"]
    assert pol.rulings_departures(pol.policy_for_row("MS2")) == ["order"]
    assert pol.rulings_departures(pol.policy_for_row("MS3")) == [
        "counting_rule"
    ]
    entry = next(
        item for item in pol.max_rulings() if item["field"] == "order"
    )
    assert entry["ruled_by"] == "Max" and entry["follows_ruling"]


def test_every_policy_choice_is_ruled_or_frozen():
    ruled = set(pol.MAX_RULINGS)
    frozen = {item.field for item in pol.frozen_choices()}
    assert not ruled & frozen
    fixed = {
        # Printed (Table 5: 4 CQ) or part of d219 item 6's wording
        # ("capped at 40").
        "di_proration_cap_years",
        "quarters_per_work_year",
    }
    fields = {field.name for field in dataclasses.fields(pol.TrackMPolicy)}
    assert fields - fixed <= ruled | frozen
    for item in pol.frozen_choices():
        assert "m1-draft-2" in item.decided_by
        assert "d219 item 9" in item.decided_by
        assert item.card_item is None
        assert item.value == getattr(pol.TrackMPolicy(), item.field)
    register = pol.decision_register()
    assert [item.field for item in register[: len(ruled)]] == list(
        pol.MAX_RULINGS
    )
    assert all(
        "default accepted" in item.decided_by
        for item in register
        if item.card_item is not None
    )
