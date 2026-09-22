"""Exercise-1 COLA age-profile tabulation, on INVENTED rows only.

Every row in this module is invented for testing.  No PSID record, model
projection, oracle benefit or comparator value is read or produced, and no
number here is a model result.  Expected values are hand-computed in the
comments next to each assertion, or come from an independent plain-Python
recomputation written in this file.
"""

from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
import pytest

from populace_dynamics.estimates import cola_age_profile as cap
from populace_dynamics.estimates.cola_age_profile import (
    MEAN_OF_INDIVIDUAL_RATIOS as ALT,
)
from populace_dynamics.estimates.cola_age_profile import (
    RATIO_OF_SCENARIO_MEANS as PRIMARY,
)
from populace_dynamics.estimates.cola_age_profile import (
    AgeGroup,
    ColaAgeProfileConfig,
    ColaTabulationError,
    MembershipDifferenceError,
    UndefinedCellError,
    tabulate_cola_age_profile,
)

GROUP_LABELS = ("50-61", "62-64", "65-69", "70-79", "80+")
#: One invented birth year per default group (ages 55, 63, 67, 75, 85 in
#: 2030).
BIRTH_YEAR = {
    "50-61": 1975,
    "62-64": 1967,
    "65-69": 1963,
    "70-79": 1955,
    "80+": 1945,
}


def _row(
    draw,
    person_id,
    *,
    birth_year,
    base,
    reform,
    weight=1.0,
    component="retired_worker",
    components=None,
    beneficiary_base=None,
    beneficiary_reform=None,
    **extra,
):
    """One invented row; a single component carries the whole benefit."""
    if components is None:
        components = (
            {component: {"base": base, "reform": reform}}
            if base > 0 or reform > 0
            else {}
        )
    return {
        "draw": draw,
        "person_id": person_id,
        "weight": weight,
        "birth_year": birth_year,
        "beneficiary_base": (
            base > 0 if beneficiary_base is None else beneficiary_base
        ),
        "beneficiary_reform": (
            reform > 0 if beneficiary_reform is None else beneficiary_reform
        ),
        "benefit_base": base,
        "benefit_reform": reform,
        "benefit_components": components,
        **extra,
    }


def _config(**overrides):
    settings = {"draw_indices": (0,), **overrides}
    return ColaAgeProfileConfig(**settings)


def _tabulate(rows, **config_overrides):
    return tabulate_cola_age_profile(
        rows, data_provenance="invented", config=_config(**config_overrides)
    )


def _group(result, label):
    (entry,) = [g for g in result["groups"] if g["label"] == label]
    return entry


def _single_group(lower=50, upper=61):
    return (AgeGroup("only", lower, upper),)


# Invented five-group fixture: in every group person 1 has weight 1 and a
# baseline benefit of 1000, person 2 weight 3 and 2000.  The reform/base
# ratios (r1, r2) differ by group and, for 50-61 only, by draw.
RATIOS = {
    0: {
        "50-61": (0.9, 1.0),
        "62-64": (0.8, 0.9),
        "65-69": (0.95, 0.95),
        "70-79": (1.0, 0.8),
        "80+": (0.8, 0.8),
    },
    1: {
        "50-61": (0.7, 1.0),
        "62-64": (0.8, 0.9),
        "65-69": (0.95, 0.95),
        "70-79": (1.0, 0.8),
        "80+": (0.8, 0.8),
    },
}


def _five_group_rows():
    rows = []
    for draw, by_group in RATIOS.items():
        for g_index, label in enumerate(GROUP_LABELS):
            r1, r2 = by_group[label]
            for p_index, (weight, base, ratio) in enumerate(
                ((1.0, 1000.0, r1), (3.0, 2000.0, r2))
            ):
                rows.append(
                    _row(
                        draw,
                        10 * g_index + p_index,
                        birth_year=BIRTH_YEAR[label],
                        base=base,
                        reform=base * ratio,
                        weight=weight,
                    )
                )
    return rows


# =========================================================================
# Defaults are the plan's proposed primaries
# =========================================================================
def test_default_config_is_the_plans_proposed_primary():
    from populace_dynamics.estimates.ledgers import DRAW_INDICES

    config = ColaAgeProfileConfig()
    assert config.reference_year == 2030
    assert [g.as_dict() for g in config.age_groups] == [
        {"label": "50-61", "lower": 50, "upper": 61},
        {"label": "62-64", "lower": 62, "upper": 64},
        {"label": "65-69", "lower": 65, "upper": 69},
        {"label": "70-79", "lower": 70, "upper": 79},
        {"label": "80+", "lower": 80, "upper": None},
    ]
    assert config.age_rule == "reference_year_minus_birth_year"
    assert config.recipient_rule == cap.POSITIVE_BENEFIT
    assert config.allow_membership_difference is False
    assert config.components == (
        "retired_worker",
        "disabled_worker",
        "spouse",
        "aged_widow",
        "disabled_widow",
    )
    assert config.benefit_period == "calendar_year_payments"
    assert config.headline_statistic == PRIMARY
    assert config.draw_indices == tuple(range(20)) == DRAW_INDICES
    assert config.floor_seeds == (0, 1, 2, 3, 4)
    assert cap.FLOOR_FRACTION == 0.5
    for ruling in cap.PENDING_RULINGS:
        assert config.as_dict()[ruling["parameter"]] == (
            ruling["proposed_primary"]
        )


def test_pending_rulings_record_choice_and_primary_flag():
    rows = _five_group_rows()
    default = tabulate_cola_age_profile(
        rows,
        data_provenance="invented",
        config=_config(draw_indices=(0, 1)),
    )
    names = [r["parameter"] for r in default["pending_rulings"]]
    assert names == [
        "headline_statistic",
        "recipient_rule",
        "allow_membership_difference",
        "membership_basis",
        "age_rule",
        "benefit_period",
        "components",
        "draw_indices",
        "floor_seeds",
    ]
    by_name = {r["parameter"]: r for r in default["pending_rulings"]}
    # draw_indices (0, 1) is not the proposed K = 20.
    assert by_name["draw_indices"]["is_proposed_primary"] is False
    assert all(
        r["is_proposed_primary"]
        for name, r in by_name.items()
        if name != "draw_indices"
    )
    workers = tabulate_cola_age_profile(
        rows,
        data_provenance="invented",
        config=_config(
            draw_indices=(0, 1),
            components=cap.WORKERS_ONLY_COMPONENTS,
            headline_statistic=ALT,
        ),
    )
    by_name = {r["parameter"]: r for r in workers["pending_rulings"]}
    assert by_name["components"]["chosen"] == [
        "retired_worker",
        "disabled_worker",
    ]
    assert by_name["components"]["is_proposed_primary"] is False
    assert by_name["headline_statistic"]["is_proposed_primary"] is False
    assert workers["conventions"]["statistic_roles"] == {
        "primary": ALT,
        "registered_alternative": PRIMARY,
    }
    # The recorded rulings are copies: mutating a result leaves the
    # module constant intact.
    by_name["components"]["registered_alternatives"].append("x")
    assert cap.PENDING_RULINGS[6]["registered_alternatives"] == [
        ["retired_worker", "disabled_worker"]
    ]


# =========================================================================
# Hand-computed statistics
# =========================================================================
def test_hand_computed_two_person_cell():
    # Person 1: w=2, base 1000, reform 900 (ratio 0.90).
    # Person 2: w=1, base 2000, reform 1900 (ratio 0.95).
    # mu_base = (2*1000 + 1*2000) / 3 = 4000/3; mu_reform = 3700/3.
    # ratio of means = 3700/4000 = 0.925 -> -7.5%.
    # mean of ratios = (2*0.90 + 1*0.95) / 3 = 2.75/3 -> -8.3333...%.
    rows = [
        _row(0, 1, birth_year=1975, base=1000.0, reform=900.0, weight=2.0),
        _row(0, 2, birth_year=1970, base=2000.0, reform=1900.0, weight=1.0),
    ]
    result = _tabulate(rows, age_groups=_single_group())
    group = _group(result, "only")
    assert group[PRIMARY]["per_draw"] == [pytest.approx(-7.5, abs=1e-12)]
    assert group[ALT]["per_draw"] == [
        pytest.approx(100.0 * (2.75 / 3.0 - 1.0), abs=1e-12)
    ]
    assert group[ALT]["per_draw"][0] == pytest.approx(-8.333333333333334)
    (cell,) = group["cells"]
    assert cell["n_base"] == cell["n_reform"] == cell["n_alternative"] == 2
    assert cell["weight_base"] == 3.0
    assert cell["mean_benefit_base"] == pytest.approx(4000.0 / 3.0)
    assert cell["mean_benefit_reform"] == pytest.approx(3700.0 / 3.0)
    # One draw: no sample SD.
    assert group[PRIMARY]["sample_sd"] is None
    assert group[PRIMARY]["n_draws"] == 1


def test_hand_computed_five_group_profile_with_draw_mean_and_sd():
    result = _tabulate(_five_group_rows(), draw_indices=(0, 1))
    # Per group, w = (1, 3), base = (1000, 2000):
    #   ratio of means = (1000 r1 + 6000 r2) / 7000 - 1
    #   mean of ratios = (r1 + 3 r2) / 4 - 1
    expected = {
        # draw 0: 6900/7000 - 1 = -1/70; (0.9 + 3)/4 - 1 = -0.025
        # draw 1: 6700/7000 - 1 = -3/70; (0.7 + 3)/4 - 1 = -0.075
        "50-61": ([-100 / 70, -300 / 70], [-2.5, -7.5]),
        # 6200/7000 - 1 = -8/70; (0.8 + 2.7)/4 - 1 = -0.125
        "62-64": ([-800 / 70] * 2, [-12.5] * 2),
        "65-69": ([-5.0] * 2, [-5.0] * 2),
        # 5800/7000 - 1 = -12/70; (1.0 + 2.4)/4 - 1 = -0.15
        "70-79": ([-1200 / 70] * 2, [-15.0] * 2),
        "80+": ([-20.0] * 2, [-20.0] * 2),
    }
    for label, (primary, alternative) in expected.items():
        group = _group(result, label)
        assert group[PRIMARY]["per_draw"] == pytest.approx(primary)
        assert group[ALT]["per_draw"] == pytest.approx(alternative)
    young = _group(result, "50-61")
    # mean(-1/70, -3/70) * 100 = -200/70; sd = (200/70) / sqrt(2)
    assert young[PRIMARY]["mean"] == pytest.approx(-200 / 70)
    assert young[PRIMARY]["sample_sd"] == pytest.approx(
        (200 / 70) / math.sqrt(2)
    )
    # mean(-2.5, -7.5) = -5; sd = 5 / sqrt(2)
    assert young[ALT]["mean"] == pytest.approx(-5.0)
    assert young[ALT]["sample_sd"] == pytest.approx(5 / math.sqrt(2))
    old = _group(result, "80+")
    assert old[PRIMARY]["mean"] == pytest.approx(-20.0)
    assert old[PRIMARY]["sample_sd"] == 0.0
    assert [g["label"] for g in result["groups"]] == list(GROUP_LABELS)


def test_hand_computed_three_draw_mean_and_sample_sd():
    # Per draw, two invented persons share one ratio: 0.99, 0.98, 0.94, so
    # both statistics are -1, -2, -6 percent.  Mean -3; deviations 2, 1,
    # -3 -> sample SD = sqrt((4 + 1 + 9) / 2) = sqrt(7).
    rows = [
        _row(draw, person, birth_year=1960, base=base, reform=base * ratio)
        for draw, ratio in ((0, 0.99), (1, 0.98), (2, 0.94))
        for person, base in ((1, 1000.0), (2, 1500.0))
    ]
    result = _tabulate(
        rows, age_groups=_single_group(65, 79), draw_indices=(0, 1, 2)
    )
    group = _group(result, "only")
    for statistic in (PRIMARY, ALT):
        assert group[statistic]["per_draw"] == pytest.approx([-1, -2, -6])
        assert group[statistic]["mean"] == pytest.approx(-3.0)
        assert group[statistic]["sample_sd"] == pytest.approx(math.sqrt(7))
        assert group[statistic]["n_draws"] == 3


def test_uniform_cola_factor_is_level_and_weight_invariant():
    # Fixed-path mechanical incidence (plan section 1 arithmetic, not model
    # output): if everyone in a group has had n reformed increases, each
    # person's ratio is f**n with f = 1.018/1.028, so both statistics equal
    # 100 * (f**n - 1) whatever the weights and benefit levels.
    factor = 1.018 / 1.028
    increases = {"50-61": 5, "62-64": 8, "65-69": 10, "70-79": 15, "80+": 20}
    rng = np.random.default_rng(7)
    rows = []
    person = 0
    for label, n in increases.items():
        for _ in range(12):
            base = float(rng.uniform(300.0, 3000.0))
            weight = float(rng.uniform(0.1, 10.0))
            for draw in (0, 1, 2):
                rows.append(
                    _row(
                        draw,
                        person,
                        birth_year=BIRTH_YEAR[label],
                        base=base,
                        reform=base * factor**n,
                        weight=weight,
                    )
                )
            person += 1
    result = _tabulate(rows, draw_indices=(0, 1, 2))
    plan_table = {5: -4.77, 8: -7.52, 10: -9.31, 15: -13.64, 20: -17.76}
    for label, n in increases.items():
        group = _group(result, label)
        for statistic in (PRIMARY, ALT):
            assert group[statistic]["mean"] == pytest.approx(
                100.0 * (factor**n - 1.0), abs=1e-10
            )
            assert round(group[statistic]["mean"], 2) == plan_table[n]
            assert group[statistic]["sample_sd"] == pytest.approx(
                0.0, abs=1e-10
            )
            floor = group[statistic]["floor"]
            assert floor["n_seeds"] + len(floor["dropped_seeds"]) == 5
            assert all(
                v == pytest.approx(0.0, abs=1e-10) for v in floor["values"]
            )


# =========================================================================
# Age rule and groups
# =========================================================================
def test_age_group_boundaries():
    ages = (49, 50, 61, 62, 64, 65, 69, 70, 79, 80, 104)
    rows = [
        _row(0, i, birth_year=2030 - age, base=1000.0, reform=990.0)
        for i, age in enumerate(ages)
    ]
    result = _tabulate(rows)
    summary = result["input_summary"]
    assert summary["n_rows_by_age_group"] == {
        "50-61": 2,
        "62-64": 2,
        "65-69": 2,
        "70-79": 2,
        "80+": 2,
    }
    assert summary["n_rows_outside_age_groups"] == 1
    for label in GROUP_LABELS:
        assert _group(result, label)["cells"][0]["n_base"] == 2


def test_age_rule_minus_one_shifts_every_age_down():
    # Born 1980 is 50 under the default rule and 49 (out of scope) under
    # the start-of-year rule; born 1968 moves from 62-64 to 50-61.
    rows = [
        _row(0, 1, birth_year=1980, base=1000.0, reform=900.0),
        _row(0, 2, birth_year=1968, base=1000.0, reform=800.0),
    ]
    default = _tabulate(rows, age_groups=_single_group(50, 61))
    assert _group(default, "only")[PRIMARY]["mean"] == pytest.approx(-10.0)
    shifted = _tabulate(
        rows,
        age_groups=_single_group(50, 61),
        age_rule="reference_year_minus_birth_year_minus_one",
    )
    assert _group(shifted, "only")[PRIMARY]["mean"] == pytest.approx(-20.0)
    assert shifted["conventions"]["age"]["definition"] == (
        "age = reference_year - birth_year - 1 (completed age at the start "
        "of the reference year)"
    )


def test_reference_year_is_a_parameter():
    rows = [_row(0, 1, birth_year=1975, base=1000.0, reform=950.0)]
    # Age 55 in 2030 but 45 in 2020: out of every group -> empty cell.
    with pytest.raises(UndefinedCellError):
        _tabulate(rows, age_groups=_single_group(), reference_year=2020)


# =========================================================================
# Membership
# =========================================================================
def test_membership_difference_is_refused_by_default():
    rows = [
        _row(0, 1, birth_year=1975, base=1000.0, reform=900.0),
        _row(0, 2, birth_year=1975, base=1000.0, reform=0.0),
    ]
    with pytest.raises(MembershipDifferenceError, match="only one scenario"):
        _tabulate(rows, age_groups=_single_group())


def test_membership_difference_outside_age_groups_is_also_refused():
    rows = [
        _row(0, 1, birth_year=1975, base=1000.0, reform=900.0),
        _row(0, 2, birth_year=1990, base=1000.0, reform=0.0),
    ]
    with pytest.raises(MembershipDifferenceError):
        _tabulate(rows, age_groups=_single_group())


def test_zero_benefit_flag_mismatch_is_not_a_membership_difference():
    # Under the positive-benefit rule a flagged beneficiary with no benefit
    # is a recipient in neither scenario, so a flag that differs between
    # scenarios on a zero-benefit row does not differ in membership.
    rows = [
        _row(0, 1, birth_year=1975, base=1000.0, reform=900.0),
        _row(
            0,
            2,
            birth_year=1975,
            base=0.0,
            reform=0.0,
            beneficiary_base=True,
            beneficiary_reform=False,
        ),
    ]
    result = _tabulate(rows, age_groups=_single_group())
    summary = result["input_summary"]
    assert summary["memberships_identical"] is True
    assert summary["n_recipient_rows"] == {"base": 1, "reform": 1}
    assert summary["n_flagged_rows_with_zero_selected_benefit"] == {
        "base": 1,
        "reform": 0,
    }
    assert _group(result, "only")[PRIMARY]["mean"] == pytest.approx(-10.0)


def _mixed_membership_rows():
    # A: recipient in both (1000 -> 900).
    # B: baseline-only recipient (1000 -> 0).
    # C: reform-only recipient (0 -> 500).
    return [
        _row(0, "A", birth_year=1975, base=1000.0, reform=900.0),
        _row(0, "B", birth_year=1975, base=1000.0, reform=0.0),
        _row(0, "C", birth_year=1975, base=0.0, reform=500.0),
    ]


@pytest.mark.parametrize(
    ("basis", "primary", "alternative", "n_base", "n_reform"),
    [
        # mu_base = (1000 + 1000)/2 = 1000; mu_reform = (900 + 500)/2 =
        # 700 -> -30%; S_alt = {A} -> -10%.
        (cap.SCENARIO_SPECIFIC, -30.0, -10.0, 2, 2),
        # S = {A, B}: mu_reform = (900 + 0)/2 = 450 -> -55%;
        # mean of ratios (0.9 + 0)/2 - 1 = -55%.
        (cap.BASELINE_RECIPIENTS, -55.0, -55.0, 2, 2),
        # S = {A}: -10% both ways.
        (cap.COMMON_RECIPIENTS, -10.0, -10.0, 1, 1),
    ],
)
def test_membership_bases_when_differences_are_allowed(
    basis, primary, alternative, n_base, n_reform
):
    result = _tabulate(
        _mixed_membership_rows(),
        age_groups=_single_group(),
        allow_membership_difference=True,
        membership_basis=basis,
    )
    group = _group(result, "only")
    assert group[PRIMARY]["mean"] == pytest.approx(primary)
    assert group[ALT]["mean"] == pytest.approx(alternative)
    assert group["cells"][0]["n_base"] == n_base
    assert group["cells"][0]["n_reform"] == n_reform
    summary = result["input_summary"]
    assert summary["memberships_identical"] is False
    assert summary["n_rows_membership_differs"] == 2
    assert summary["n_recipient_rows"] == {"base": 2, "reform": 2}


def test_flagged_recipient_rule_keeps_zero_benefits():
    # Z is a flagged beneficiary whose retired-worker benefit is zero in
    # both scenarios (e.g. withheld upstream).
    rows = [
        _row(0, "A", birth_year=1975, base=1000.0, reform=900.0),
        _row(
            0,
            "Z",
            birth_year=1975,
            base=0.0,
            reform=0.0,
            components={"retired_worker": {"base": 0.0, "reform": 0.0}},
            beneficiary_base=True,
            beneficiary_reform=True,
        ),
    ]
    positive = _tabulate(rows, age_groups=_single_group())
    cell = _group(positive, "only")["cells"][0]
    assert cell["n_base"] == 1
    assert cell["mean_benefit_base"] == 1000.0
    assert positive["input_summary"][
        "n_flagged_rows_with_zero_selected_benefit"
    ] == {"base": 1, "reform": 1}

    flagged = _tabulate(
        rows,
        age_groups=_single_group(),
        recipient_rule=cap.FLAGGED_RECIPIENT_INCLUDING_ZERO,
    )
    group = _group(flagged, "only")
    cell = group["cells"][0]
    # Means over {A, Z}: 500 and 450 -> still -10%; S_alt drops Z (B_base
    # = 0) -> -10%.
    assert cell["n_base"] == 2
    assert cell["n_alternative"] == 1
    assert cell["mean_benefit_base"] == 500.0
    assert cell["mean_benefit_reform"] == 450.0
    assert group[PRIMARY]["mean"] == pytest.approx(-10.0)
    assert group[ALT]["mean"] == pytest.approx(-10.0)


# =========================================================================
# Components
# =========================================================================
def _component_rows():
    # X: retired worker 800 -> 720 plus spouse 200 -> 180 (1000 -> 900).
    # Y: spouse only, 500 -> 400.
    return [
        _row(
            0,
            "X",
            birth_year=1960,
            base=1000.0,
            reform=900.0,
            components={
                "retired_worker": {"base": 800.0, "reform": 720.0},
                "spouse": {"base": 200.0, "reform": 180.0},
            },
        ),
        _row(
            0,
            "Y",
            birth_year=1960,
            base=500.0,
            reform=400.0,
            component="spouse",
        ),
    ]


def test_all_five_components_by_default():
    result = _tabulate(_component_rows(), age_groups=_single_group(65, 79))
    group = _group(result, "only")
    # (900 + 400) / (1000 + 500) - 1 = -13.333...%; (0.9 + 0.8)/2 - 1 = -15%
    assert group[PRIMARY]["mean"] == pytest.approx(-40.0 / 3.0)
    assert group[ALT]["mean"] == pytest.approx(-15.0)


def test_workers_only_components_change_membership_and_levels():
    result = _tabulate(
        _component_rows(),
        age_groups=_single_group(65, 79),
        components=cap.WORKERS_ONLY_COMPONENTS,
    )
    group = _group(result, "only")
    # Y has no worker benefit and drops out; X counts 800 -> 720 only.
    assert group["cells"][0]["n_base"] == 1
    assert group["cells"][0]["mean_benefit_base"] == 800.0
    assert group[PRIMARY]["mean"] == pytest.approx(-10.0)
    assert group[ALT]["mean"] == pytest.approx(-10.0)
    conventions = result["conventions"]["components"]
    assert conventions["selected"] == ["retired_worker", "disabled_worker"]


def test_components_are_canonically_ordered():
    config = _config(components=("spouse", "retired_worker"))
    assert config.components == ("retired_worker", "spouse")


@pytest.mark.parametrize(
    ("components", "message"),
    [
        ({"child_in_care": {"base": 1.0, "reform": 1.0}}, "unknown"),
        ({"retired_worker": {"base": 1.0}}, "base"),
        ({"retired_worker": 1.0}, "base"),
        ([("retired_worker", 1.0)], "must map"),
        ({"retired_worker": {"base": -1.0, "reform": 1.0}}, "non-negative"),
    ],
)
def test_malformed_components_are_refused(components, message):
    rows = [
        _row(
            0,
            1,
            birth_year=1975,
            base=1.0,
            reform=1.0,
            components=components,
        )
    ]
    with pytest.raises(ColaTabulationError, match=message):
        _tabulate(rows, age_groups=_single_group())


def test_component_sum_must_match_totals():
    rows = [
        _row(
            0,
            1,
            birth_year=1975,
            base=1000.0,
            reform=900.0,
            components={"retired_worker": {"base": 999.0, "reform": 900.0}},
        )
    ]
    with pytest.raises(ColaTabulationError, match="components sum"):
        _tabulate(rows, age_groups=_single_group())


# =========================================================================
# Refusals
# =========================================================================
def test_empty_cell_is_refused():
    # 80+ has no rows at all.
    rows = [
        r for r in _five_group_rows() if r["birth_year"] != BIRTH_YEAR["80+"]
    ]
    with pytest.raises(UndefinedCellError, match="80\\+"):
        _tabulate(rows, draw_indices=(0, 1))


def test_zero_weight_cell_is_refused():
    rows = [_row(0, 1, birth_year=1975, base=1000.0, reform=900.0, weight=0.0)]
    with pytest.raises(UndefinedCellError, match="empty_baseline"):
        _tabulate(rows, age_groups=_single_group())


def test_zero_baseline_mean_is_refused():
    rows = [
        _row(
            0,
            1,
            birth_year=1975,
            base=0.0,
            reform=0.0,
            components={"retired_worker": {"base": 0.0, "reform": 0.0}},
            beneficiary_base=True,
            beneficiary_reform=True,
        )
    ]
    with pytest.raises(UndefinedCellError, match="nonpositive_baseline"):
        _tabulate(
            rows,
            age_groups=_single_group(),
            recipient_rule=cap.FLAGGED_RECIPIENT_INCLUDING_ZERO,
        )


def test_float_overflow_is_refused_not_reported():
    # 1e300 * 1e10 overflows float64: the result would carry inf/nan, which
    # is not JSON, so the tabulation refuses instead.
    rows = [
        _row(0, 1, birth_year=1975, base=1e10, reform=9e9, weight=1e300),
    ]
    with pytest.raises(ColaTabulationError, match="overflow"):
        _tabulate(rows, age_groups=_single_group())


@pytest.mark.filterwarnings("error::RuntimeWarning")
def test_floor_summary_overflow_is_refused_not_reported():
    # Invented extreme row: person 0 has a 1e-300 baseline and a 1.5e6
    # reform benefit (individual ratio 1.5e306), so any half holding person
    # 0 alone has a mean-of-ratios near 1.5e308.  The full-sample cell is
    # finite (about 5e307), but the floor averages several such gaps, and
    # their numpy mean overflows to inf.  That must be refused, not
    # reported as a non-JSON floor.
    rows = [_row(0, 0, birth_year=1975, base=1e-300, reform=1.5e6)] + [
        _row(0, person, birth_year=1975, base=1000.0, reform=900.0)
        for person in (1, 2)
    ]
    with pytest.raises(ColaTabulationError, match="the floor .* not finite"):
        _tabulate(rows, age_groups=_single_group())


@pytest.mark.filterwarnings("error::RuntimeWarning")
def test_half_sample_mean_overflow_is_a_tabulation_error():
    # Invented extreme rows over two draws: the half holding person 0 alone
    # has a mean-of-ratios near 1.5e308 in each draw, whose sum overflows
    # math.fsum.  That is a ColaTabulationError, not a bare OverflowError.
    rows = [
        _row(draw, person, birth_year=1975, base=base, reform=reform)
        for draw in (0, 1)
        for person, base, reform in ((0, 1e-300, 1.5e6), (1, 1000.0, 900.0))
    ]
    with pytest.raises(ColaTabulationError, match="half-sample mean"):
        _tabulate(rows, age_groups=_single_group(), draw_indices=(0, 1))


def test_benefit_without_beneficiary_flag_is_refused():
    rows = [
        _row(
            0,
            1,
            birth_year=1975,
            base=1000.0,
            reform=900.0,
            beneficiary_base=False,
        )
    ]
    with pytest.raises(ColaTabulationError, match="beneficiary_base is"):
        _tabulate(rows, age_groups=_single_group())


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("weight", -1.0, "non-negative"),
        ("weight", float("nan"), "finite"),
        ("benefit_base", float("inf"), "finite"),
        ("weight", True, "real number"),
        ("birth_year", 1975.0, "integer"),
        ("draw", -1, "draws present"),
        ("person_id", 1.5, "person_id"),
        ("person_id", "", "person_id"),
        ("beneficiary_base", 1, "bool"),
    ],
)
def test_invalid_scalars_are_refused(field, value, message):
    row = _row(0, 1, birth_year=1975, base=1000.0, reform=900.0)
    row[field] = value
    with pytest.raises(ColaTabulationError, match=message):
        _tabulate([row], age_groups=_single_group())


def test_missing_column_is_refused():
    row = _row(0, 1, birth_year=1975, base=1000.0, reform=900.0)
    del row["benefit_components"]
    with pytest.raises(ColaTabulationError, match="lacks"):
        _tabulate([row], age_groups=_single_group())
    frame = pd.DataFrame([row])
    with pytest.raises(ColaTabulationError, match="lack columns"):
        _tabulate(frame, age_groups=_single_group())


def test_draw_set_must_match_configuration():
    rows = _five_group_rows()
    with pytest.raises(ColaTabulationError, match="draws present"):
        _tabulate(rows, draw_indices=(0, 1, 2))
    with pytest.raises(ColaTabulationError, match="draws present"):
        _tabulate(rows, draw_indices=(0,))


def test_duplicate_draw_person_is_refused():
    rows = [
        _row(0, 1, birth_year=1975, base=1000.0, reform=900.0),
        _row(0, 1, birth_year=1975, base=1000.0, reform=900.0),
    ]
    with pytest.raises(ColaTabulationError, match="duplicate"):
        _tabulate(rows, age_groups=_single_group())


def test_mixed_person_id_types_are_refused():
    rows = [
        _row(0, 1, birth_year=1975, base=1000.0, reform=900.0),
        _row(0, "2", birth_year=1975, base=1000.0, reform=900.0),
    ]
    with pytest.raises(ColaTabulationError, match="all be integers"):
        _tabulate(rows, age_groups=_single_group())


def test_numpy_string_person_ids_are_strings():
    # numpy.str_ keys (e.g. from an array) mix with builtin str keys: both
    # are string ids, and equal values are the same person.
    rows = [
        _row(0, np.str_("a"), birth_year=1975, base=1000.0, reform=900.0),
        _row(0, "b", birth_year=1975, base=1000.0, reform=800.0),
    ]
    result = _tabulate(rows, age_groups=_single_group())
    assert result["input_summary"]["n_persons"] == 2
    assert _group(result, "only")[PRIMARY]["mean"] == pytest.approx(-15.0)
    duplicate = [
        _row(0, np.str_("a"), birth_year=1975, base=1000.0, reform=900.0),
        _row(0, "a", birth_year=1975, base=1000.0, reform=900.0),
    ]
    with pytest.raises(ColaTabulationError, match="duplicate"):
        _tabulate(duplicate, age_groups=_single_group())


def test_empty_rows_are_refused():
    with pytest.raises(ColaTabulationError, match="empty"):
        _tabulate([], age_groups=_single_group())
    with pytest.raises(ColaTabulationError, match="iterable"):
        _tabulate({"draw": 0}, age_groups=_single_group())


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"age_groups": ()}, "non-empty"),
        (
            {"age_groups": (AgeGroup("a", 50, 60), AgeGroup("b", 60, 70))},
            "non-overlapping",
        ),
        (
            {"age_groups": (AgeGroup("a", 50), AgeGroup("b", 60, 70))},
            "open-ended",
        ),
        (
            {"age_groups": (AgeGroup("a", 50, 55), AgeGroup("a", 60, 70))},
            "unique",
        ),
        ({"components": ()}, "not be empty"),
        ({"components": ("parent",)}, "unknown"),
        ({"components": ("spouse", "spouse")}, "unique"),
        ({"draw_indices": ()}, "not be empty"),
        ({"draw_indices": (0, 0)}, "unique"),
        ({"draw_indices": (-1,)}, "non-negative"),
        ({"floor_seeds": (1, 1)}, "unique"),
        ({"recipient_rule": "anyone"}, "recipient_rule"),
        ({"membership_basis": "all_adults"}, "membership_basis"),
        ({"age_rule": "exact"}, "age_rule"),
        ({"benefit_period": "annual"}, "benefit_period"),
        ({"headline_statistic": "median"}, "headline_statistic"),
        ({"allow_membership_difference": 1}, "bool"),
        ({"reference_year": 2030.0}, "integer"),
    ],
)
def test_invalid_configuration_is_refused(overrides, message):
    with pytest.raises(ColaTabulationError, match=message):
        ColaAgeProfileConfig(**overrides)


def test_invalid_age_group_is_refused():
    with pytest.raises(ColaTabulationError, match="upper < lower"):
        AgeGroup("a", 60, 50)
    with pytest.raises(ColaTabulationError, match="label"):
        AgeGroup("", 60, 70)


# =========================================================================
# Provenance interlock and recorded metadata
# =========================================================================
def test_real_data_requires_registration_pointer_and_labels():
    rows = [_row(0, 1, birth_year=1975, base=1000.0, reform=900.0)]
    config = _config(age_groups=_single_group())
    with pytest.raises(ColaTabulationError, match="registration pointer"):
        tabulate_cola_age_profile(
            rows, data_provenance="registered_real", config=config
        )
    with pytest.raises(ColaTabulationError, match="labels"):
        tabulate_cola_age_profile(
            rows,
            data_provenance="registered_real",
            config=config,
            registration_pointer="#42 comment (invented pointer)",
        )
    with pytest.raises(ColaTabulationError, match="data_provenance"):
        tabulate_cola_age_profile(rows, data_provenance="real", config=config)
    with pytest.raises(ColaTabulationError, match="registration_pointer"):
        tabulate_cola_age_profile(
            rows,
            data_provenance="invented",
            config=config,
            registration_pointer="  ",
        )
    # The interlock records the pointer; it does not verify it.  These
    # invented rows exercise only the interlock path.
    result = tabulate_cola_age_profile(
        rows,
        data_provenance="registered_real",
        config=config,
        registration_pointer="#42 comment (invented pointer)",
        labels=("invented label for an interlock test",),
    )
    assert result["registration_pointer"] == "#42 comment (invented pointer)"
    assert result["labels"] == ["invented label for an interlock test"]


def test_invented_results_carry_the_invented_label():
    rows = [_row(0, 1, birth_year=1975, base=1000.0, reform=900.0)]
    result = tabulate_cola_age_profile(
        rows,
        data_provenance="invented",
        config=_config(age_groups=_single_group()),
        labels=("fixed-path mechanical incidence",),
    )
    assert result["data_provenance"] == "invented"
    assert result["labels"] == [
        cap.INVENTED_DATA_LABEL,
        "fixed-path mechanical incidence",
    ]
    with pytest.raises(ColaTabulationError, match="sequence"):
        tabulate_cola_age_profile(
            rows,
            data_provenance="invented",
            config=_config(age_groups=_single_group()),
            labels="one string",
        )


def test_upstream_conventions_are_recorded_verbatim():
    rows = [_row(0, 1, birth_year=1975, base=1000.0, reform=900.0)]
    upstream = {
        "first_reduced_increase": "effective_december_2009",
        "exposure_clock": "eligibility",
        "reformed_increases_by_2030": 21,
    }
    result = tabulate_cola_age_profile(
        rows,
        data_provenance="invented",
        config=_config(age_groups=_single_group()),
        upstream_conventions=upstream,
    )
    assert result["upstream_conventions"] == upstream
    with pytest.raises(ColaTabulationError, match="JSON scalar"):
        tabulate_cola_age_profile(
            rows,
            data_provenance="invented",
            config=_config(age_groups=_single_group()),
            upstream_conventions={"rate_path": [0.028]},
        )


def test_conventions_record_the_exact_rules():
    result = _tabulate(_five_group_rows(), draw_indices=(0, 1))
    conventions = result["conventions"]
    assert result["schema_version"] == cap.SCHEMA_VERSION
    assert conventions["reference_year"] == 2030
    assert conventions["statistics"] == cap.STATISTIC_DEFINITIONS
    assert conventions["membership"]["identical_membership_required"] is True
    assert conventions["floor"]["seeds"] == [0, 1, 2, 3, 4]
    assert conventions["floor"]["fraction"] == 0.5
    assert "split_panel_by_person" in conventions["floor"]["splitter"]
    assert conventions["benefit_period"] == {
        "label": "calendar_year_payments",
        "definition": cap.BENEFIT_PERIOD_DEFINITIONS["calendar_year_payments"],
        "enforced_by_tabulation": False,
    }
    assert conventions["acceptance_rule"] is None
    assert result["config"] == _config(draw_indices=(0, 1)).as_dict()


def test_result_is_json_serializable_and_deterministic():
    rows = _five_group_rows()
    first = _tabulate(rows, draw_indices=(0, 1))
    second = _tabulate(list(reversed(rows)), draw_indices=(0, 1))
    text = json.dumps(first, allow_nan=False, sort_keys=True)
    assert json.loads(text) == first
    assert json.dumps(second, allow_nan=False, sort_keys=True) == text


def test_dataframe_and_record_inputs_agree():
    rows = [dict(r, sex="invented") for r in _five_group_rows()]
    from_records = _tabulate(rows, draw_indices=(0, 1))
    from_frame = _tabulate(pd.DataFrame(rows), draw_indices=(0, 1))
    assert from_frame == from_records
    assert from_frame["input_summary"]["extra_columns_ignored"] == ["sex"]


def test_input_summary_counts():
    rows = _five_group_rows()
    rows.append(_row(1, 999, birth_year=1990, base=0.0, reform=0.0))
    result = _tabulate(rows, draw_indices=(0, 1))
    summary = result["input_summary"]
    assert summary["n_rows"] == 21
    assert summary["n_persons"] == 11
    assert summary["n_rows_per_draw"] == {"0": 10, "1": 11}
    assert summary["person_sets_identical_across_draws"] is False
    assert summary["n_rows_outside_age_groups"] == 1
    assert summary["memberships_identical"] is True
    assert summary["n_recipient_rows"] == {"base": 20, "reform": 20}


# =========================================================================
# Noise floor
# =========================================================================
def _random_invented_rows(n_persons=80, draws=(0, 1, 2, 3), seed=11):
    """Invented rows: 16 persons per group, some non-recipients per draw."""
    rng = np.random.default_rng(seed)
    bounds = {
        "50-61": (50, 61),
        "62-64": (62, 64),
        "65-69": (65, 69),
        "70-79": (70, 79),
        "80+": (80, 95),
    }
    rows = []
    for person in range(n_persons):
        lower, upper = bounds[GROUP_LABELS[person % 5]]
        birth_year = 2030 - int(rng.integers(lower, upper + 1))
        weight = float(rng.uniform(0.5, 5.0))
        for draw in draws:
            if rng.random() < 0.15:
                base = reform = 0.0
            else:
                base = float(rng.uniform(500.0, 3000.0))
                reform = base * float(rng.uniform(0.8, 1.0))
            rows.append(
                _row(
                    draw,
                    1000 + 7 * person,
                    birth_year=birth_year,
                    base=base,
                    reform=reform,
                    weight=weight,
                )
            )
    return rows


def _reference_values(rows, draws, person_filter=None):
    """Plain-Python recomputation of both statistics, mean over draws."""
    out = {}
    for label in GROUP_LABELS:
        lower, upper = {
            "50-61": (50, 61),
            "62-64": (62, 64),
            "65-69": (65, 69),
            "70-79": (70, 79),
            "80+": (80, 10**6),
        }[label]
        per_draw = {PRIMARY: [], ALT: []}
        for draw in draws:
            members = [
                r
                for r in rows
                if r["draw"] == draw
                and lower <= 2030 - r["birth_year"] <= upper
                and r["benefit_base"] > 0
                and (person_filter is None or r["person_id"] in person_filter)
            ]
            weight = math.fsum(r["weight"] for r in members)
            if weight == 0:
                per_draw[PRIMARY].append(None)
                per_draw[ALT].append(None)
                continue
            base = math.fsum(r["weight"] * r["benefit_base"] for r in members)
            reform = math.fsum(
                r["weight"] * r["benefit_reform"] for r in members
            )
            ratios = math.fsum(
                r["weight"] * r["benefit_reform"] / r["benefit_base"]
                for r in members
            )
            per_draw[PRIMARY].append(100 * (reform / base - 1))
            per_draw[ALT].append(100 * (ratios / weight - 1))
        out[label] = {
            stat: (
                None
                if any(v is None for v in values)
                else math.fsum(values) / len(values)
            )
            for stat, values in per_draw.items()
        }
    return out


def test_floor_matches_an_independent_recomputation():
    draws = (0, 1, 2, 3)
    rows = _random_invented_rows(draws=draws)
    result = _tabulate(rows, draw_indices=draws)
    full = _reference_values(rows, draws)
    ids = np.sort(np.unique([r["person_id"] for r in rows]))
    gaps = {(label, s): [] for label in GROUP_LABELS for s in (PRIMARY, ALT)}
    for seed_index, seed in enumerate((0, 1, 2, 3, 4)):
        # The split convention re-derived here without calling the
        # harness: sorted unique ids, default_rng(seed).random(n) < 0.5.
        picked = np.random.default_rng(seed).random(len(ids)) < 0.5
        side_a_ids = set(ids[picked].tolist())
        side_b_ids = set(ids[~picked].tolist())
        side_a = _reference_values(rows, draws, side_a_ids)
        side_b = _reference_values(rows, draws, side_b_ids)
        recorded = result["floor_per_seed"][seed_index]
        assert recorded["seed"] == seed
        assert recorded["side_a"]["n_persons"] == len(side_a_ids)
        assert recorded["side_b"]["n_persons"] == len(side_b_ids)
        for label in GROUP_LABELS:
            for stat in (PRIMARY, ALT):
                a = side_a[label][stat]
                b = side_b[label][stat]
                # 16 invented persons per group: both halves are defined.
                assert a is not None and b is not None
                assert recorded["side_a"]["groups"][label][stat] == (
                    pytest.approx(a, rel=1e-12)
                )
                assert recorded["side_b"]["groups"][label][stat] == (
                    pytest.approx(b, rel=1e-12)
                )
                gaps[(label, stat)].append(abs(a - b))
    for label in GROUP_LABELS:
        group = _group(result, label)
        for stat in (PRIMARY, ALT):
            assert group[stat]["mean"] == pytest.approx(
                full[label][stat], rel=1e-12
            )
            expected = np.array(gaps[(label, stat)])
            floor = group[stat]["floor"]
            assert floor["n_seeds"] == expected.size == 5
            assert floor["dropped_seeds"] == []
            assert floor["values"] == pytest.approx(expected.tolist())
            assert floor["mean"] == pytest.approx(float(expected.mean()))
            assert floor["sd"] == pytest.approx(float(expected.std(ddof=1)))
            assert floor["min"] == pytest.approx(float(expected.min()))
            assert floor["max"] == pytest.approx(float(expected.max()))
            assert floor["mean"] > 0.0


def test_half_split_keeps_every_draw_of_a_person_on_one_side():
    draws = (0, 1, 2, 3)
    rows = _random_invented_rows(draws=draws)
    result = _tabulate(rows, draw_indices=draws)
    n_persons = result["input_summary"]["n_persons"]
    for recorded in result["floor_per_seed"]:
        a = recorded["side_a"]
        b = recorded["side_b"]
        # Person-disjoint: persons and rows partition exactly, and each
        # side holds all four draws of each of its persons.
        assert a["n_persons"] + b["n_persons"] == n_persons
        assert a["n_rows"] == 4 * a["n_persons"]
        assert b["n_rows"] == 4 * b["n_persons"]


def test_floor_drops_seeds_with_an_undefined_half():
    # One recipient: in every seed one half has no member, so no seed is
    # usable and the floor fields are null (not a zero floor).
    rows = [_row(0, 1, birth_year=1975, base=1000.0, reform=900.0)]
    result = _tabulate(rows, age_groups=_single_group())
    floor = _group(result, "only")[PRIMARY]["floor"]
    assert floor == {
        "mean": None,
        "sd": None,
        "min": None,
        "max": None,
        "n_seeds": 0,
        "values": [],
        "dropped_seeds": [0, 1, 2, 3, 4],
    }
    for recorded in result["floor_per_seed"]:
        sides = (recorded["side_a"], recorded["side_b"])
        empty = [s for s in sides if s["n_persons"] == 0]
        assert len(empty) == 1
        assert empty[0]["groups"]["only"][PRIMARY] is None
        assert empty[0]["groups"]["only"][f"{PRIMARY}_undefined_draws"] == [0]


def test_string_person_ids_are_supported():
    draws = (0, 1)
    rows = _random_invented_rows(n_persons=40, draws=draws)
    for r in rows:
        r["person_id"] = f"p{r['person_id']}"
    result = _tabulate(rows, draw_indices=draws)
    assert result["input_summary"]["n_persons"] == 40
    total = sum(
        s["n_persons"]
        for s in (
            result["floor_per_seed"][0]["side_a"],
            result["floor_per_seed"][0]["side_b"],
        )
    )
    assert total == 40
