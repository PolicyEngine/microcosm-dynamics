"""INVENTED histories: §4.6 event predicates and refusal, without benefits."""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.cola_track_a.opening import OpeningStockRecord
from populace_dynamics.track_a_v2.histories import (
    HistoryRefusal,
    HistoryValidator,
)
from tests.track_a_v2._invented import build


def test_supported_award_conversion_and_inherited_decedent():
    """One continuous spell conserves its award through conversion and death."""
    cohort, result = build(
        [
            dict(
                id=1, awards=(2017,), conversion=2027, claim=2027, death=2030
            ),
            dict(id=2, marital="widowed", late_spouse=1, widowhood=2030),
        ]
    )
    validator = HistoryValidator(result, cohort)
    assert validator.requested_di_levels() == {1: 2017}
    assert validator.validate_requested() == {"d_proxy_award_year": 1}
    assert validator.validate_requested() == {"d_proxy_award_year": 1}


@pytest.mark.parametrize(
    "changes",
    [
        {"awards": (2015, 2023)},
        {"awards": (2015, 2023), "recoveries": (2018,)},
        {
            "opening_di": True,
            "opening_status": "disabled_worker",
            "awards": (2023,),
            "recoveries": (2018,),
        },
        {"awards": (), "conversion": 2027},
    ],
)
def test_intended_unsupported_spell_refusals(changes):
    """Intended violations refuse; no latest-spell substitution is permitted."""
    cohort, result = build([dict(id=1, **changes)])
    with pytest.raises(HistoryRefusal):
        HistoryValidator(result, cohort).validate(1, 2023)


@pytest.mark.parametrize(
    "field,value",
    [
        ("di_award_year", 2016),
        ("di_recovery_year", 2020),
        ("di_conversion_year", 2028),
        ("di_entitled", False),
    ],
)
def test_intended_inconsistent_event_state_refusal(field, value):
    """Every stored date and entitlement agrees with immutable annual events."""
    cohort, result = build([dict(id=1, awards=(2017,))])
    result.slices[10].loc[0, field] = value
    with pytest.raises(HistoryRefusal):
        HistoryValidator(result, cohort).validate(1, 2017)


@pytest.mark.parametrize(
    "birth,clock,rule,proxy",
    [
        (1950, 1990, "a3_receipt_start", "d_proxy_a3_receipt_start"),
        (1950, 2012, "own_birth_plus_62_di", "d_proxy_opening_age_62"),
    ],
)
def test_opening_proxies(birth, clock, rule, proxy):
    """Opening proxy classification preserves the inherited eligibility clock."""
    record = OpeningStockRecord(
        1,
        "disabled_worker",
        "disabled_worker",
        1200,
        clock,
        rule,
        clock,
        False,
    )
    cohort, result = build(
        [
            dict(
                id=1,
                birth=birth,
                opening_di=True,
                opening_status="disabled_worker",
            )
        ],
        opening={1: record},
    )
    validator = HistoryValidator(result, cohort)
    assert validator.validate(1, clock) == proxy
    # Intact own observed payment never requests its own D level.
    assert validator.requested_di_levels() == {}


def test_fallback_and_age62_clamp():
    """Fallback and clamped award proxies are distinct and counted exactly."""
    cohort, result = build(
        [
            dict(
                id=1,
                birth=1940,
                opening_di=True,
                opening_status="disabled_worker",
            ),
            dict(id=2, birth=1960, awards=(2024,)),
        ]
    )
    validator = HistoryValidator(result, cohort)
    assert validator.requested_di_levels() == {1: 2010, 2: 2022}
    assert validator.validate_requested() == {
        "d_proxy_start_year_fallback": 1,
        "d_proxy_age_62_clamp": 1,
    }


@settings(deadline=None)
@given(st.integers(2011, 2029))
def test_continuous_award_histories_are_deterministic(award):
    """Single-spell acceptance is deterministic and bounded to one proxy count."""
    cohort, result = build([dict(id=1, awards=(award,))])
    left = HistoryValidator(result, cohort).validate_requested()
    right = HistoryValidator(result, cohort).validate_requested()
    assert left == right
    assert sum(left.values()) == 1


def test_structural_discovery_counts_all_missing_awards_but_joint_refuses_first():
    """Unsupported requests remain counted; joint refusal uses first person."""
    cohort, result = build(
        [dict(id=1, awards=(2017,)), dict(id=2, awards=(2018,))]
    )
    result.slices[-1]["di_award_year"] = None
    validator = HistoryValidator(result, cohort)
    assert validator.requested_di_levels() == {}
    assert set(validator.request_errors) == {1, 2}
    with pytest.raises(HistoryRefusal) as caught:
        validator.validate_requested()
    assert caught.value.person_id == 1 and caught.value.counters == {}


def test_receipt_start_exactly_at62_is_not_a_clamp_proxy():
    """Equal dates do not erase the inherited A3 clock-rule provenance."""
    record = OpeningStockRecord(
        1,
        "disabled_worker",
        "disabled_worker",
        1200,
        2010,
        "a3_receipt_start",
        2010,
        False,
    )
    cohort, result = build(
        [
            dict(
                id=1,
                birth=1948,
                opening_di=True,
                opening_status="disabled_worker",
            )
        ],
        opening={1: record},
    )
    assert (
        HistoryValidator(result, cohort).validate(1, 2010)
        == "d_proxy_a3_receipt_start"
    )
