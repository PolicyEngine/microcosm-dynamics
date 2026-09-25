"""Track M's open choices are explicit, defaulted and listed as pending.

No data: only the policy module's constants.  Max has not ruled on cos
decision d219; every choice it covers must stay a parameter at the plan's
recommended default and appear in :func:`pending_decisions`.
"""

from __future__ import annotations

import dataclasses

import pytest

from populace_dynamics.min_benefit_track_m import policy as pol


def test_defaults_are_the_plan_primary():
    policy = pol.TrackMPolicy()
    assert policy.policy_year == 2004  # G2, d219 item 3
    assert policy.window_rule == pol.WINDOW_IN_OR_AFTER  # G4
    assert policy.order == pol.ORDER_FLOOR_AFTER_CUT  # G10, item 5
    assert policy.counting_rule == pol.COUNT_OWN_OR_LINKED  # G23, item 7
    assert policy.pia_rule == pol.PIA_HISTORY  # G5
    assert policy.di_pia_rule == pol.DI_PIA_APPROXIMATE  # G5
    assert policy.di_proration == pol.DI_PRORATION_ELAPSED  # G12, item 6
    assert (policy.di_proration_start_age, policy.di_proration_cap_years) == (
        22,
        40,
    )
    assert policy.covered_earnings_rule == pol.COVERED_LABOR_INCOME  # item 4
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
        "MS6": {"di_pia_rule": pol.DI_PIA_STATUTORY},
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


def test_every_d219_item_is_pending_with_its_default():
    items = pol.d219_items()
    assert sorted(items) == list(range(1, 10))
    pending = pol.pending_decisions()
    by_item = {item.card_item: item for item in pending if item.card_item}
    assert sorted(by_item) == list(range(1, 10))
    policy = pol.TrackMPolicy()
    for number, item in by_item.items():
        assert item.field == items[number][0]
        assert f"{pol.DECISION_RECORD} item {number} (open)" in item.awaiting
        if hasattr(policy, item.field):
            assert item.default == getattr(policy, item.field)
    assert by_item[8].default is None  # no acceptance threshold


def test_every_policy_choice_is_listed():
    listed = {item.field for item in pol.pending_decisions()}
    fixed = {
        # Printed (Table 5: 4 CQ) or part of d219 item 6's wording
        # ("capped at 40"), which the di_proration entry carries.
        "di_proration_cap_years",
        "quarters_per_work_year",
    }
    fields = {field.name for field in dataclasses.fields(pol.TrackMPolicy)}
    assert fields - fixed <= listed
    for item in pol.pending_decisions():
        if item.card_item is None:
            assert "specification freeze" in item.awaiting
        assert item.as_dict()["field"] == item.field
