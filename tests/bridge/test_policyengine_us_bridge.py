"""Properties of the PolicyEngine-US bridge's pure-Python parts.

No policyengine-us import and no subprocess: the situation builder, the
decomposition and the COLA helpers are checked with Hypothesis on INVENTED
households, trees and amounts.  The live runner is exercised in
``test_policyengine_us_bridge_oracle.py``.
"""

from __future__ import annotations

import base64
import hashlib
import itertools
import json
import math
import subprocess
from decimal import Decimal

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.bridge import policyengine_us as bridge

AMOUNT = st.floats(
    min_value=0.0, max_value=1e7, allow_nan=False, allow_infinity=False
)
IDS = st.lists(
    st.from_regex(r"[a-z]{1,6}", fullmatch=True),
    min_size=1,
    max_size=5,
    unique=True,
)


@st.composite
def partitions(draw, members, max_group=None):
    """Split ``members`` into nonempty groups (each at most ``max_group``)."""

    labels = draw(
        st.lists(
            st.integers(0, len(members) - 1),
            min_size=len(members),
            max_size=len(members),
        )
    )
    groups: dict[int, list[str]] = {}
    for member, label in zip(members, labels, strict=True):
        groups.setdefault(label, []).append(member)
    out = []
    for group in groups.values():
        size = max_group or len(group)
        out.extend(
            tuple(group[i : i + size]) for i in range(0, len(group), size)
        )
    return tuple(out)


@st.composite
def people(draw):
    ids = draw(IDS)
    return tuple(
        bridge.BridgePerson(
            person_id=pid,
            age=draw(st.integers(0, 125)),
            medicare_quarters_of_coverage=draw(
                st.none() | st.integers(0, 200)
            ),
            **{name: draw(AMOUNT) for name in bridge.AMOUNT_FIELDS},
        )
        for pid in ids
    )


@st.composite
def households(draw):
    members = draw(people())
    ids = [person.person_id for person in members]
    return bridge.BridgeHousehold(
        household_id=draw(st.from_regex(r"h[a-z0-9]{0,6}", fullmatch=True)),
        state=draw(st.sampled_from(sorted(bridge.STATE_FIPS))),
        people=members,
        tax_units=draw(partitions(ids)),
        spm_units=draw(partitions(ids)),
        marital_units=draw(partitions(ids, max_group=2)),
        families=draw(st.none() | partitions(ids)),
        has_heating_cooling_expense=draw(st.booleans()),
        takes_up_housing_assistance=draw(st.booleans()),
        food_preparation_allowed=draw(st.booleans()),
    )


YEAR = st.integers(2000, 2100)
GROUP_ENTITIES = (
    "tax_units",
    "spm_units",
    "marital_units",
    "families",
    "households",
)


# ---------------------------------------------------------------------------
# The situation builder
# ---------------------------------------------------------------------------
@given(households(), YEAR)
def test__given_household__then_every_person_is_in_exactly_one_unit(
    household, year
):
    situation = bridge.to_situation(household, year)
    ids = sorted(person.person_id for person in household.people)
    assert sorted(situation["people"]) == ids
    for plural in GROUP_ENTITIES:
        members = [
            member
            for entry in situation[plural].values()
            for member in entry["members"]
        ]
        assert sorted(members) == ids, plural
    assert len(situation["households"]) == 1


@given(households(), YEAR)
def test__given_household__then_amounts_ages_and_state_round_trip(
    household, year
):
    situation = bridge.to_situation(household, year)
    assert bridge.person_inputs_from_situation(situation, year) == {
        person.person_id: person.amounts() for person in household.people
    }
    period = str(year)
    for person in household.people:
        entry = situation["people"][person.person_id]
        assert entry["age"] == {period: person.age}
        quarters = entry.get("medicare_quarters_of_coverage")
        expected = person.medicare_quarters_of_coverage
        assert quarters == (None if expected is None else {period: expected})
    (entry,) = situation["households"].values()
    assert entry["state_fips"] == {period: bridge.STATE_FIPS[household.state]}


@given(households(), YEAR)
def test__given_household__then_situation_is_deterministic_json(
    household, year
):
    first = bridge.to_situation(household, year)
    second = bridge.to_situation(household, year)
    assert first == second
    assert json.dumps(first, sort_keys=True) == json.dumps(
        second, sort_keys=True
    )
    # The situation is plain JSON (the runner sends it on stdin).
    assert json.loads(json.dumps(first)) == first


@given(
    st.sampled_from(bridge.AMOUNT_FIELDS),
    st.floats(max_value=-1e-12, allow_nan=False, allow_infinity=False),
)
def test__given_negative_amount__then_person_is_refused(name, value):
    with pytest.raises(ValueError, match="nonnegative"):
        bridge.BridgePerson("p", 70, **{name: value})


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("name", bridge.AMOUNT_FIELDS)
def test__given_nonfinite_amount__then_person_is_refused(name, value):
    with pytest.raises(ValueError, match="finite"):
        bridge.BridgePerson("p", 70, **{name: value})


@pytest.mark.parametrize("value", [True, "1", None])
def test__given_non_number_amount__then_person_is_refused(value):
    with pytest.raises(TypeError):
        bridge.BridgePerson("p", 70, social_security_retirement=value)


@pytest.mark.parametrize("age", [-1, 126, 67.5, True])
def test__given_bad_age__then_person_is_refused(age):
    with pytest.raises((ValueError, TypeError)):
        bridge.BridgePerson("p", age)


def _two_people():
    return (bridge.BridgePerson("a", 70), bridge.BridgePerson("b", 68))


@pytest.mark.parametrize(
    "units",
    [
        (("a",),),  # b missing
        (("a", "b"), ("b",)),  # b twice
        (("a", "b", "c"),),  # unknown person
        ((),),  # empty group
    ],
)
@pytest.mark.parametrize("kind", ["tax_units", "spm_units", "marital_units"])
def test__given_bad_partition__then_household_is_refused(units, kind):
    good = (("a", "b"),)
    fields = {"tax_units": good, "spm_units": good, "marital_units": good}
    fields[kind] = units
    with pytest.raises(ValueError):
        bridge.BridgeHousehold("h", "CA", _two_people(), **fields)


def test__given_three_person_marital_unit__then_household_is_refused():
    trio = (*_two_people(), bridge.BridgePerson("c", 30))
    group = (("a", "b", "c"),)
    with pytest.raises(ValueError, match="at most two"):
        bridge.BridgeHousehold("h", "CA", trio, group, group, group)


@pytest.mark.parametrize(
    "units",
    [
        ("ab",),  # a bare string as a group: once read as ("a", "b")
        "ab",  # a bare string as the groups
    ],
)
def test__given_bare_string_group__then_household_is_refused(units):
    people = (bridge.BridgePerson("a", 70), bridge.BridgePerson("b", 68))
    good = (("a", "b"),)
    with pytest.raises(TypeError, match="sequence of ids|groups of ids"):
        bridge.BridgeHousehold("h", "CA", people, units, good, good)


def test__given_generators_as_groups__then_household_is_built():
    people = (bridge.BridgePerson("a", 70), bridge.BridgePerson("b", 68))
    household = bridge.BridgeHousehold(
        "h",
        "CA",
        people,
        (group for group in (("a", "b"),)),
        (group for group in (("a",), ("b",))),
        (group for group in (("a", "b"),)),
    )
    assert household.tax_units == (("a", "b"),)
    assert household.spm_units == (("a",), ("b",))


def test__given_unknown_state_or_duplicate_ids__then_household_is_refused():
    group = (("a", "b"),)
    with pytest.raises(ValueError, match="STATE_FIPS"):
        bridge.BridgeHousehold("h", "PR", _two_people(), group, group, group)
    twins = (bridge.BridgePerson("a", 70), bridge.BridgePerson("a", 70))
    with pytest.raises(ValueError, match="unique"):
        bridge.BridgeHousehold("h", "CA", twins, group, group, group)


def test__state_fips_table__then_codes_are_distinct_census_codes():
    assert len(bridge.STATE_FIPS) == 51
    assert len(set(bridge.STATE_FIPS.values())) == 51
    assert all(1 <= code <= 56 for code in bridge.STATE_FIPS.values())


# ---------------------------------------------------------------------------
# The decomposition
# ---------------------------------------------------------------------------
CENTS = st.integers(-(10**9), 10**9).map(lambda cents: cents / 100)


def _values(tree, leaf_values):
    values = dict(leaf_values)

    def value(name):
        if tree.is_leaf(name):
            return values[name]
        total = math.fsum(
            sign * value(part) for part, sign in tree.children[name]
        )
        values[name] = total
        return total

    value(tree.root)
    return values


@st.composite
def trees(draw, root="root"):
    counter = itertools.count()
    children: dict[str, tuple[tuple[str, int], ...]] = {}

    def build(name, depth):
        parts = []
        for _ in range(draw(st.integers(1, 4))):
            child = f"v{next(counter)}"
            parts.append((child, draw(st.sampled_from((1, -1)))))
            if depth < 3 and draw(st.booleans()):
                build(child, depth + 1)
        children[name] = tuple(parts)

    build(root, 0)
    return bridge.ComponentTree(root, children)


@st.composite
def runs(draw, amounts=CENTS):
    tree = draw(trees())
    leaves = [name for name, _, _ in tree.leaves()]
    baseline = _values(tree, {name: draw(amounts) for name in leaves})
    reform = _values(tree, {name: draw(amounts) for name in leaves})
    return tree, baseline, reform


def _decompose(tree, baseline, reform, **kwargs):
    return bridge.decompose(
        tree, baseline, reform, expected_definition=None, **kwargs
    )


@settings(max_examples=300)
@given(runs())
def test__given_runs__then_components_sum_exactly_to_net_change(run):
    tree, baseline, reform = run
    result = _decompose(tree, baseline, reform)
    changes = [component.change_cents for component in result.components]
    assert sum(changes) == result.net_change_cents
    expected = bridge.to_cents(reform[tree.root]) - bridge.to_cents(
        baseline[tree.root]
    )
    assert result.net_change_cents == expected
    assert result.reported_gap_cents == 0
    categories = result.by_category()
    assert sum(entry["change"] for entry in categories.values()) == sum(
        changes
    )
    assert sum(entry["baseline"] for entry in categories.values()) == (
        result.baseline_net_cents
    )
    # Every leaf appears once, with the product of the signs on its path.
    assert len(result.components) == len(tree.leaves())


@given(runs())
def test__given_reform_equal_to_baseline__then_every_change_is_zero(run):
    tree, baseline, _ = run
    result = _decompose(tree, baseline, dict(baseline))
    assert result.net_change_cents == 0
    assert all(c.change_cents == 0 for c in result.components)
    assert all(entry["change"] == 0 for entry in result.by_category().values())


@given(runs())
def test__given_same_inputs__then_decomposition_is_deterministic(run):
    tree, baseline, reform = run
    first = _decompose(tree, baseline, reform).as_dict()
    second = _decompose(tree, dict(baseline), dict(reform)).as_dict()
    assert json.dumps(first, sort_keys=True) == json.dumps(
        second, sort_keys=True
    )


@given(runs(), st.randoms(use_true_random=False))
def test__given_reordered_parts__then_changes_are_unchanged(run, random):
    tree, baseline, reform = run
    shuffled = {}
    for name, parts in tree.children.items():
        parts = list(parts)
        random.shuffle(parts)
        shuffled[name] = tuple(parts)
    other = bridge.ComponentTree(tree.root, shuffled)
    first = _decompose(tree, baseline, reform)
    second = _decompose(other, baseline, reform)
    assert first.net_change_cents == second.net_change_cents
    assert sorted((c.variable, c.change_cents) for c in first.components) == (
        sorted((c.variable, c.change_cents) for c in second.components)
    )


@given(runs(), st.floats(0.51, 1e6), st.data())
def test__given_inconsistent_aggregate__then_decomposition_is_refused(
    run, shift, data
):
    tree, baseline, reform = run
    name = data.draw(st.sampled_from(tree.aggregates()))
    broken = dict(reform)
    broken[name] = broken[name] + shift
    with pytest.raises(bridge.AggregateMismatchError):
        _decompose(tree, baseline, broken)


def test__given_nan_intermediate_aggregate__then_decomposition_is_refused():
    """The review's minimal counterexample (finding 4).

    root -> mid -> (x, y) with mid = nan, x = 1, y = 2 and root = 3 once
    decomposed without error: ``max(0.0, nan)`` is ``0.0``.
    """

    tree = bridge.ComponentTree(
        "root",
        {"root": (("mid", 1),), "mid": (("x", 1), ("y", 1))},
    )
    values = {"root": 3.0, "mid": math.nan, "x": 1.0, "y": 2.0}
    with pytest.raises(bridge.AggregateMismatchError, match="not finite"):
        _decompose(tree, values, values)


@given(
    runs(),
    st.sampled_from([math.nan, math.inf, -math.inf]),
    st.data(),
)
def test__given_any_nonfinite_value__then_decomposition_is_refused(
    run, bad, data
):
    tree, baseline, reform = run
    name = data.draw(st.sampled_from(sorted(reform)))
    broken = dict(reform)
    broken[name] = bad
    with pytest.raises(bridge.AggregateMismatchError, match="not finite"):
        _decompose(tree, baseline, broken)


@settings(max_examples=100)
@given(
    runs(
        amounts=st.floats(
            min_value=-1e6,
            max_value=1e6,
            allow_nan=False,
            allow_infinity=False,
        )
    )
)
def test__given_arbitrary_floats__then_identity_still_holds_in_cents(run):
    tree, baseline, reform = run
    result = _decompose(tree, baseline, reform)
    assert (
        sum(c.change_cents for c in result.components)
        == result.net_change_cents
    )
    # Rounding each leaf to cents moves the root by at most half a cent a
    # leaf.
    assert abs(result.reported_gap_cents) <= len(result.components) + 1


def _net_income_tree():
    children = {
        "household_net_income": bridge.NET_INCOME_DEFINITION,
        "household_benefits": (("social_security", 1), ("ssi", 1)),
        "household_tax_before_refundable_credits": (
            ("income_tax_before_refundable_credits", 1),
        ),
    }
    return bridge.ComponentTree("household_net_income", children)


def test__given_net_income_tree__then_signs_and_categories_follow_the_definition():
    tree = _net_income_tree()
    leaves = {
        "household_market_income": 0.0,
        "social_security": 9000.0,
        "ssi": 3000.0,
        "household_refundable_tax_credits": 0.0,
        "income_tax_before_refundable_credits": 100.0,
        "household_health_costs": 0.0,
    }
    baseline = _values(tree, leaves)
    reform = _values(
        tree,
        {
            **leaves,
            "social_security": 11000.0,
            "ssi": 1000.0,
            "income_tax_before_refundable_credits": 150.0,
        },
    )
    result = bridge.decompose(tree, baseline, reform)
    by_variable = {c.variable: c for c in result.components}
    assert by_variable["income_tax_before_refundable_credits"].sign == -1
    assert by_variable[
        "income_tax_before_refundable_credits"
    ].change_cents == (-5000)
    categories = result.by_category()
    assert categories["social_security"]["change"] == 200000
    assert categories["ssi"]["change"] == -200000
    assert categories["federal_income_tax"]["change"] == -5000
    assert result.net_change_cents == -5000


def test__given_other_net_income_definition__then_drift_is_refused():
    tree = _net_income_tree()
    drifted = bridge.ComponentTree(
        tree.root,
        {
            **tree.children,
            "household_net_income": bridge.NET_INCOME_DEFINITION[:-1],
        },
    )
    values = {name: 0.0 for name in ("household_net_income",)}
    for name, _ in bridge.NET_INCOME_DEFINITION:
        values[name] = 0.0
    values.update(
        social_security=0.0,
        ssi=0.0,
        income_tax_before_refundable_credits=0.0,
    )
    with pytest.raises(bridge.DefinitionDriftError):
        bridge.decompose(drifted, values, values)
    with pytest.raises(bridge.DefinitionDriftError):
        bridge.decompose(tree, values, values, reform_tree=drifted)


@pytest.mark.parametrize(
    ("variable", "path", "category"),
    [
        ("social_security", ("household_benefits",), "social_security"),
        ("ssi", ("household_benefits",), "ssi"),
        ("snap", ("household_benefits",), "snap"),
        (
            "ca_state_supplement",
            ("household_benefits", "household_state_benefits"),
            "state_benefits",
        ),
        (
            "income_tax_before_refundable_credits",
            ("household_tax_before_refundable_credits",),
            "federal_income_tax",
        ),
        (
            "income_tax_refundable_credits",
            ("household_refundable_tax_credits",),
            "federal_refundable_credits",
        ),
        (
            "mt_refundable_credits",
            (
                "household_refundable_tax_credits",
                "household_refundable_state_tax_credits",
            ),
            "state_refundable_credits",
        ),
        (
            "state_income_tax_before_refundable_credits",
            (
                "household_tax_before_refundable_credits",
                "household_state_tax_before_refundable_credits",
            ),
            "state_income_tax",
        ),
        (
            "state_use_tax",
            (
                "household_tax_before_refundable_credits",
                "household_state_tax_before_refundable_credits",
            ),
            "other_taxes",
        ),
        ("pension_income", ("household_market_income",), "market_income"),
        (
            "medicaid_cost",
            ("household_benefits", "household_health_benefits"),
            "health_net",
        ),
        (
            "commodity_supplemental_food_program",
            ("household_benefits",),
            "csfp",
        ),
        ("wic", ("household_benefits",), "other_benefits"),
    ],
)
def test__given_leaf__then_category_is_the_documented_one(
    variable, path, category
):
    assert bridge.category_for(variable, ("household_net_income", *path)) == (
        category
    )
    assert category in bridge.CATEGORY_ORDER


def test__category_table__then_every_category_has_one_label():
    assert set(bridge.CATEGORY_LABELS) == set(bridge.CATEGORY_ORDER)
    assert len(set(bridge.CATEGORY_ORDER)) == len(bridge.CATEGORY_ORDER)


def test__given_refundable_credit_on_zero_tax__then_it_is_not_a_tax_row():
    """A refundable credit on a zero liability is its own positive row.

    Montana's elderly homeowner and renter credit on a zero liability once
    read as "state income tax +1,150" (review finding 7).
    """

    tree = bridge.ComponentTree(
        "household_net_income",
        {
            "household_net_income": bridge.NET_INCOME_DEFINITION,
            "household_refundable_tax_credits": (
                ("household_refundable_state_tax_credits", 1),
            ),
            "household_refundable_state_tax_credits": (
                ("mt_refundable_credits", 1),
            ),
            "household_tax_before_refundable_credits": (
                ("household_state_tax_before_refundable_credits", 1),
            ),
            "household_state_tax_before_refundable_credits": (
                ("state_income_tax_before_refundable_credits", 1),
            ),
        },
    )
    leaves = {
        "household_market_income": 0.0,
        "household_benefits": 0.0,
        "mt_refundable_credits": 1150.0,
        "state_income_tax_before_refundable_credits": 0.0,
        "household_health_costs": 0.0,
    }
    values = _values(tree, leaves)
    categories = bridge.decompose(tree, values, values).by_category()
    assert categories["state_refundable_credits"]["baseline"] == 115000
    assert categories["state_income_tax"]["baseline"] == 0


def test__given_cyclic_or_badly_signed_tree__then_it_is_refused():
    with pytest.raises(ValueError, match="cycle"):
        bridge.ComponentTree("a", {"a": (("b", 1),), "b": (("a", 1),)})
    with pytest.raises(ValueError, match="sign"):
        bridge.ComponentTree("a", {"a": (("b", 2),)})
    with pytest.raises(ValueError, match="root"):
        bridge.ComponentTree("a", {"b": (("c", 1),)})


@given(st.integers(-(10**12), 10**12))
def test__given_whole_cents__then_to_cents_round_trips(cents):
    assert bridge.to_cents(cents / 100) == cents


# ---------------------------------------------------------------------------
# Carrying a PIA forward
# ---------------------------------------------------------------------------
RATES = st.lists(
    st.integers(0, 150).map(lambda tenths: tenths / 1000),
    min_size=0,
    max_size=12,
)
NONEMPTY_RATES = RATES.filter(bool)
PIA = st.floats(min_value=0.0, max_value=10_000.0, allow_nan=False)


def _rate_map(rates, first=2000):
    return {first + i: rate for i, rate in enumerate(rates)}


def _carry(pia, rates, first=2000):
    return bridge.carry_pia_forward(
        pia,
        _rate_map(rates, first),
        first_determination_year=first,
        last_determination_year=first + len(rates) - 1,
    )[0]


@given(PIA, NONEMPTY_RATES)
def test__given_colas__then_carried_pia_is_a_whole_dime(pia, rates):
    carried = _carry(pia, rates)
    tenths = Decimal(repr(carried)) * 10
    assert tenths == tenths.to_integral_value()


@given(PIA, PIA, NONEMPTY_RATES)
def test__given_larger_pia__then_carried_pia_is_not_smaller(a, b, rates):
    low, high = sorted((a, b))
    assert _carry(low, rates) <= _carry(high, rates)


@given(PIA, NONEMPTY_RATES)
def test__given_colas__then_truncation_loses_less_than_a_dime_a_step(
    pia, rates
):
    carried = _carry(pia, rates)
    exact = Decimal(repr(pia))
    for rate in rates:
        exact *= 1 + Decimal(repr(rate))
    growth = math.prod(1 + rate for rate in rates)
    assert Decimal(repr(carried)) <= exact
    assert float(exact) - carried <= 0.10 * (len(rates) + 1) * growth + 1e-9


@given(PIA, NONEMPTY_RATES, NONEMPTY_RATES)
def test__given_split_years__then_carrying_composes(pia, first, second):
    rates = first + second
    part = _carry(pia, first)
    rest = bridge.carry_pia_forward(
        part,
        _rate_map(rates),
        first_determination_year=2000 + len(first),
        last_determination_year=2000 + len(rates) - 1,
    )[0]
    assert rest == _carry(pia, rates)


@given(PIA, st.integers(1, 10))
def test__given_zero_colas__then_pia_is_only_truncated_to_a_dime(pia, n):
    assert _carry(pia, [0.0] * n) == bridge.floor_to_dime(pia)


def test__given_missing_cola__then_carry_is_refused():
    with pytest.raises(ValueError, match="no COLA"):
        bridge.carry_pia_forward(
            600.0,
            {2020: 0.013},
            first_determination_year=2020,
            last_determination_year=2021,
        )


@given(PIA, st.integers(1, 30))
def test__given_first_year_after_last__then_carry_is_refused(pia, gap):
    """An empty range once returned the PIA untruncated (finding 5)."""

    with pytest.raises(ValueError, match="after"):
        bridge.carry_pia_forward(
            pia,
            {},
            first_determination_year=2026,
            last_determination_year=2026 - gap,
        )


def test__given_float_noise_in_a_rate__then_it_does_not_reach_the_dime():
    # 5.9 / 100 is 0.059000000000000004 in floating point.
    noisy = 5.9 / 100
    assert repr(noisy) != "0.059"
    assert (
        bridge.carry_pia_forward(
            1000.0,
            {2021: noisy},
            first_determination_year=2021,
            last_determination_year=2021,
        )[0]
        == bridge.carry_pia_forward(
            1000.0,
            {2021: 0.059},
            first_determination_year=2021,
            last_determination_year=2021,
        )[0]
    )


def test__given_ssa_third_quarter_cpi_w__then_colas_match_the_published_ones():
    # Third-quarter CPI-W averages 2021-2025 (the entries dated 2022-2026 of
    # policyengine-us's gov.ssa.uprating), and SSA's COLAs determined
    # 2022-2025: 8.7, 3.2, 2.5 and 2.8 percent.
    cpi_w = {
        2022: 268.421,
        2023: 291.901,
        2024: 301.236,
        2025: 308.729,
        2026: 317.265,
    }
    assert bridge.cola_rates_from_cpi_w(cpi_w) == {
        2022: 0.087,
        2023: 0.032,
        2024: 0.025,
        2025: 0.028,
    }


def test__given_a_quarter_without_increase__then_the_base_carries_forward():
    # INVENTED: no increase in the second year, so the third year's COLA
    # is measured from the first year's quarter (415(i)(1)(B), (D)).
    rates = bridge.cola_rates_from_cpi_w(
        {2014: 100.0, 2015: 99.0, 2016: 100.3}
    )
    assert rates == {2014: 0.0, 2015: 0.003}


@given(
    st.lists(
        st.floats(min_value=50.0, max_value=500.0, allow_nan=False),
        min_size=2,
        max_size=10,
    )
)
def test__given_any_cpi_w_path__then_colas_are_nonnegative_tenths(levels):
    rates = bridge.cola_rates_from_cpi_w(
        {2000 + i: level for i, level in enumerate(levels)}
    )
    assert sorted(rates) == list(range(2000, 2000 + len(levels) - 1))
    for rate in rates.values():
        assert rate >= 0
        assert abs(rate * 1000 - round(rate * 1000)) < 1e-9


# ---------------------------------------------------------------------------
# The runner's refusals (no interpreter is started)
# ---------------------------------------------------------------------------
def test__given_missing_interpreter__then_runner_raises_unavailable(tmp_path):
    with pytest.raises(bridge.PolicyEngineUSUnavailable):
        bridge.run_policyengine_us(
            [bridge.RunCase("a", {})],
            year=2026,
            python=tmp_path / "no-such-python",
        )


def test__given_duplicate_case_ids__then_runner_refuses(tmp_path):
    with pytest.raises(ValueError, match="unique"):
        bridge.run_policyengine_us(
            [bridge.RunCase("a", {}), bridge.RunCase("a", {})],
            year=2026,
            python=tmp_path / "no-such-python",
        )


def test__given_explicit_env_or_nothing__then_interpreter_resolves_in_order(
    monkeypatch, tmp_path
):
    explicit = tmp_path / "explicit"
    env = tmp_path / "env"
    monkeypatch.setenv(bridge.PE_US_PYTHON_ENV, str(env))
    assert bridge.resolve_pe_us_python(explicit) == explicit
    assert bridge.resolve_pe_us_python() == env
    monkeypatch.delenv(bridge.PE_US_PYTHON_ENV)
    assert bridge.resolve_pe_us_python() == (
        bridge.DEFAULT_PE_US_PYTHON.expanduser()
    )


# ---------------------------------------------------------------------------
# The source check (no interpreter is started)
# ---------------------------------------------------------------------------
def _installation(tmp_path, **overrides):
    fields = {
        "python": str(tmp_path / "python"),
        "python_version": "3.13.9",
        "package_dir": str(tmp_path / "site" / "policyengine_us"),
        "version": "2.18.0",
        "core_version": "3.32.11",
        "location": str(tmp_path / "site"),
        "record_path": str(tmp_path / "site" / "dist-info" / "RECORD"),
        "record_sha256": "0" * 64,
        "direct_url": None,
        "installer": "uv",
    }
    fields.update(overrides)
    return bridge.PolicyEngineUSInstallation(**fields)


def test__given_index_install__then_source_is_published(tmp_path):
    installation = _installation(tmp_path)
    assert installation.source_kind == "index"
    record = bridge.check_published_source(installation)
    assert record["published"] and record["reasons"] == []


@pytest.mark.parametrize(
    ("direct_url", "kind"),
    [
        ({"url": "https://x", "vcs_info": {"commit_id": "a"}}, "vcs"),
        ({"url": "file:///w.whl", "archive_info": {}}, "archive"),
        ({"url": "file:///src", "dir_info": {}}, "directory"),
    ],
)
def test__given_vcs_archive_or_directory_install__then_source_is_refused(
    tmp_path, direct_url, kind
):
    installation = _installation(tmp_path, direct_url=direct_url)
    assert installation.source_kind == kind
    with pytest.raises(bridge.UnpublishedSourceError, match=kind):
        bridge.check_published_source(installation)
    record = bridge.check_published_source(installation, require=False)
    assert record["published"] is False


def _git(directory, *args):
    subprocess.run(
        ["git", "-C", str(directory), *args],
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def checkout(tmp_path):
    """A clone of a local origin: pushed ``main`` plus a package dir."""

    origin = tmp_path / "origin.git"
    subprocess.run(
        ["git", "init", "--bare", "-q", str(origin)],
        check=True,
        capture_output=True,
    )
    clone = tmp_path / "clone"
    subprocess.run(
        ["git", "clone", "-q", str(origin), str(clone)],
        check=True,
        capture_output=True,
    )
    _git(clone, "config", "user.email", "t@example.com")
    _git(clone, "config", "user.name", "t")
    _git(clone, "checkout", "-q", "-b", "main")
    package = clone / "policyengine_us"
    package.mkdir()
    (package / "__init__.py").write_text("")
    _git(clone, "add", ".")
    _git(clone, "commit", "-q", "-m", "published")
    _git(clone, "push", "-q", "origin", "main")
    return clone


def _checkout_installation(tmp_path, clone):
    return _installation(
        tmp_path,
        package_dir=str(clone / "policyengine_us"),
        direct_url={"url": f"file://{clone}", "dir_info": {"editable": True}},
    )


def _check(tmp_path, clone, **kwargs):
    # The fixture's origin is a local bare repository, not GitHub, so the
    # tests of reachability and cleanliness switch the host check off; its
    # own test is below.
    return bridge.check_published_source(
        _checkout_installation(tmp_path, clone),
        **{"public_origin": False, **kwargs},
    )


def test__given_pushed_clean_checkout__then_source_is_published(
    tmp_path, checkout
):
    installation = _checkout_installation(tmp_path, checkout)
    assert installation.source_kind == "path"
    record = _check(tmp_path, checkout)
    assert record["published"]
    assert record["checkout"]["origin_heads_containing"] == ["refs/heads/main"]


def test__given_origin_not_on_github__then_source_is_refused(
    tmp_path, checkout
):
    """A pushed commit on a local origin is not published."""

    with pytest.raises(
        bridge.UnpublishedSourceError, match="is not a GitHub repository"
    ):
        bridge.check_published_source(
            _checkout_installation(tmp_path, checkout)
        )


@pytest.mark.parametrize(
    ("url", "github"),
    [
        ("https://github.com/PolicyEngine/policyengine-us.git", True),
        ("https://github.com/PolicyEngine/policyengine-us", True),
        ("git@github.com:PolicyEngine/policyengine-us.git", True),
        ("ssh://git@github.com/PolicyEngine/policyengine-us.git", True),
        ("https://github.example.com/PolicyEngine/policyengine-us", False),
        ("/Users/someone/policyengine-us.git", False),
        ("file:///tmp/origin.git", False),
    ],
)
def test__given_origin_url__then_only_github_urls_match(url, github):
    """The check is the host only: a URL cannot say whether a GitHub
    repository is public or private."""

    assert bool(bridge._GITHUB_ORIGIN.match(url)) is github


def test__given_local_commit_not_on_origin__then_source_is_refused(
    tmp_path, checkout
):
    """The review's finding 3: a revision GitHub does not have."""

    (checkout / "policyengine_us" / "extra.py").write_text("X = 1\n")
    _git(checkout, "add", ".")
    _git(checkout, "commit", "-q", "-m", "fixup! local only")
    with pytest.raises(bridge.UnpublishedSourceError, match="not reachable"):
        _check(tmp_path, checkout)


def test__given_branch_deleted_on_origin__then_a_stale_ref_does_not_count(
    tmp_path, checkout
):
    """A remote-tracking ref can outlive its branch; origin is asked now."""

    _git(checkout, "checkout", "-q", "-b", "feature")
    (checkout / "policyengine_us" / "feature.py").write_text("F = 1\n")
    _git(checkout, "add", ".")
    _git(checkout, "commit", "-q", "-m", "feature")
    _git(checkout, "push", "-q", "origin", "feature")
    assert _check(tmp_path, checkout)["published"]
    # Delete the branch on origin only: refs/remotes/origin/feature stays.
    _git(tmp_path / "origin.git", "branch", "-q", "-D", "feature")
    _git(checkout, "rev-parse", "refs/remotes/origin/feature")
    with pytest.raises(bridge.UnpublishedSourceError, match="not reachable"):
        _check(tmp_path, checkout)


def test__given_unreachable_origin__then_source_is_refused(tmp_path, checkout):
    _git(checkout, "remote", "set-url", "origin", str(tmp_path / "gone.git"))
    with pytest.raises(bridge.UnpublishedSourceError, match="could not be"):
        _check(tmp_path, checkout)


@pytest.mark.parametrize("change", ["tracked", "untracked", "ignored"])
def test__given_modified_checkout__then_source_is_refused(
    tmp_path, checkout, change
):
    package = checkout / "policyengine_us"
    if change == "tracked":
        (package / "__init__.py").write_text("Y = 2\n")
    elif change == "untracked":
        (package / "new.py").write_text("Z = 3\n")
    else:
        # A git-ignored parameter file still loads: policyengine-core reads
        # every YAML under parameters/.
        exclude = checkout / ".git" / "info" / "exclude"
        exclude.write_text(exclude.read_text() + "hidden.yaml\n")
        (package / "hidden.yaml").write_text("values: {2026-01-01: 1}\n")
    with pytest.raises(bridge.UnpublishedSourceError, match="uncommitted"):
        _check(tmp_path, checkout)


def test__given_only_bytecode_untracked__then_checkout_stays_clean(
    tmp_path, checkout
):
    cache = checkout / "policyengine_us" / "__pycache__"
    cache.mkdir()
    (cache / "__init__.cpython-313.pyc").write_bytes(b"\x00")
    assert _check(tmp_path, checkout)["published"]


def test__given_package_outside_any_checkout__then_source_is_refused(
    tmp_path,
):
    outside = tmp_path / "loose" / "policyengine_us"
    outside.mkdir(parents=True)
    installation = _installation(tmp_path, package_dir=str(outside))
    assert installation.source_kind == "path"
    with pytest.raises(bridge.UnpublishedSourceError, match="git checkout"):
        bridge.check_published_source(installation)


def _record_line(root, relative, content):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    digest = hashlib.sha256(content).digest()
    encoded = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return f"{relative},sha256={encoded},{len(content)}"


def test__given_installed_files__then_record_verification_checks_each(
    tmp_path,
):
    site = tmp_path / "site"
    lines = [
        _record_line(site, "policyengine_us/__init__.py", b"a = 1\n"),
        _record_line(site, "policyengine_us/p/x.yaml", b"values: {}\n"),
        _record_line(site, "policyengine_us-2.18.0.dist-info/METADATA", b"m"),
        "policyengine_us-2.18.0.dist-info/RECORD,,",
    ]
    record = site / "policyengine_us-2.18.0.dist-info" / "RECORD"
    record.write_text("\n".join(lines) + "\n")
    installation = _installation(tmp_path, record_path=str(record))
    # Bytecode written at import time is neither in the RECORD nor extra.
    cache = site / "policyengine_us" / "__pycache__"
    cache.mkdir()
    (cache / "__init__.cpython-313.pyc").write_bytes(b"\x00")
    clean = bridge.verify_record(installation)
    assert clean["files_checked"] == 2
    assert clean["mismatched"] == [] and clean["missing"] == []
    assert clean["extra"] == []
    (site / "policyengine_us" / "p" / "x.yaml").write_text("values: {1: 2}\n")
    (site / "policyengine_us" / "__init__.py").unlink()
    (site / "policyengine_us" / "p" / "override.yaml").write_text("x: 1\n")
    dirty = bridge.verify_record(installation)
    assert dirty["mismatched"] == ["policyengine_us/p/x.yaml"]
    assert dirty["missing"] == ["policyengine_us/__init__.py"]
    assert dirty["extra"] == ["policyengine_us/p/override.yaml"]
    assert dirty["package_record_digest"] == clean["package_record_digest"]


@given(
    st.lists(
        st.from_regex(
            r"policyengine_us/[a-z]{1,8}\.py,sha256=[a-z]{4},\d",
            fullmatch=True,
        ),
        min_size=1,
        max_size=8,
        unique=True,
    ),
    st.lists(
        st.one_of(
            st.from_regex(r"[a-z]{1,8},,", fullmatch=True),
            # pip compiles bytecode and lists it under the package.
            st.from_regex(
                r"policyengine_us/(?:[a-z]{1,8}/)?__pycache__/"
                r"[a-z]{1,8}\.cpython-31[0-4]\.pyc,,",
                fullmatch=True,
            ),
        ),
        max_size=6,
    ),
    st.randoms(use_true_random=False),
)
def test__given_installer_lines_and_order__then_package_digest_is_unchanged(
    package_lines, installer_lines, random
):
    """The installed RECORD adds installer lines (pip's bytecode among them)
    and may reorder; the digest of the sorted package lines is the wheel's
    either way."""

    wheel = "\n".join(package_lines) + "\n"
    installed = package_lines + installer_lines
    random.shuffle(installed)
    prefix = "policyengine_us/"
    assert bridge.package_record_digest(wheel, prefix) == (
        bridge.package_record_digest("\n".join(installed), prefix)
    )


# ---------------------------------------------------------------------------
# The float32 guard (no interpreter is started)
# ---------------------------------------------------------------------------
def _node(value, children=(), is_input=False):
    return bridge.TraceNode(
        value=None if value is None else tuple(value),
        children=tuple(children),
        input=is_input,
    )


def _use_tax_traces(reform_agi):
    """The review's finding 2, as PolicyEngine-US 2.18.0 traces it.

    California excludes Social Security from its AGI, so ca_agi should not
    move; float32 subtraction put the reform run at 29,999.998046875, one
    float32 step under the $30,000 edge of the use-tax table.
    """

    def run(ss, agi, ca_agi, use_tax):
        return {
            "state_use_tax@2026": _node([use_tax], ["ca_use_tax@2026"]),
            "ca_use_tax@2026": _node([use_tax], ["CA@2026", "ca_agi@2026"]),
            "CA@2026": _node([1.0]),
            "ca_agi@2026": _node(
                [ca_agi],
                ["adjusted_gross_income@2026", "ca_agi_subtractions@2026"],
            ),
            "adjusted_gross_income@2026": _node(
                [agi], ["social_security_retirement@2026"]
            ),
            "ca_agi_subtractions@2026": _node(
                [agi - ca_agi], ["social_security_retirement@2026"]
            ),
            "social_security_retirement@2026": _node([ss], is_input=True),
        }

    baseline = run(8916.0, 34847.30, 30000.0, 3.0)
    reform = run(
        10968.0, 35761.40, reform_agi, 2.0 if reform_agi < 3e4 else 3.0
    )
    return baseline, reform


def test__given_step_on_float32_noise__then_the_guard_reports_its_origin():
    baseline, reform = _use_tax_traces(29999.998046875)
    found = bridge.uncaused_changes(baseline, reform, ["state_use_tax@2026"])
    assert [item["variable"] for item in found] == ["ca_use_tax@2026"]
    assert found[0]["change"] == pytest.approx(1.0)
    assert found[0]["reads"]["ca_agi@2026"] < bridge.CENT_TOLERANCE


def test__given_no_step__then_the_guard_is_silent():
    baseline, reform = _use_tax_traces(30000.0)
    assert (
        bridge.uncaused_changes(baseline, reform, ["state_use_tax@2026"]) == []
    )


def test__given_change_through_a_changed_input__then_it_is_caused():
    baseline = {
        "tax@2026": _node([100.0], ["agi@2026"]),
        "agi@2026": _node([1000.0], ["ss@2026"]),
        "ss@2026": _node([500.0], is_input=True),
    }
    reform = {
        "tax@2026": _node([100.5], ["agi@2026"]),
        "agi@2026": _node([1005.0], ["ss@2026"]),
        "ss@2026": _node([505.0], is_input=True),
    }
    assert bridge.uncaused_changes(baseline, reform, ["tax@2026"]) == []


def test__given_branch_taken_in_one_run_only__then_it_is_a_cause():
    """Medicaid ending sends the calculation down another branch: a node
    read in one run only is a change, and a node traced in one run only is
    not compared."""

    baseline = {
        "cost@2026": _node([9000.0], ["eligible@2026", "medicaid@2026"]),
        "eligible@2026": _node([1.0], ["income@2026"]),
        "income@2026": _node([100.0], is_input=True),
        "medicaid@2026": _node([9000.0], ["age@2026"]),
        "age@2026": _node([68.0], is_input=True),
    }
    reform = {
        "cost@2026": _node([5000.0], ["eligible@2026", "msp@2026"]),
        "eligible@2026": _node([0.0], ["income@2026"]),
        "income@2026": _node([200.0], is_input=True),
        "msp@2026": _node([5000.0], ["age@2026"]),
        "age@2026": _node([68.0], is_input=True),
    }
    assert bridge.uncaused_changes(baseline, reform, ["cost@2026"]) == []


def test__given_branch_copy_of_a_main_value__then_it_reads_the_main_node():
    """A branch clones its parent's calculated values (2.18.0's itemizing
    branch copies adjusted gross income): the copy is caused when the main
    value is, and reported when the main value changed without a cause."""

    def run(ss, agi, main_agi_children):
        return {
            "tax@2026": _node([agi * 0.1], ["itemizing:agi@2026"]),
            "itemizing:agi@2026": _node([agi]),
            "agi@2026": _node([agi], main_agi_children),
            "ss@2026": _node([ss], is_input=True),
        }

    caused_b = run(8916.0, 37067.30, ["ss@2026"])
    caused_r = run(10968.0, 37981.40, ["ss@2026"])
    assert bridge.uncaused_changes(caused_b, caused_r, ["tax@2026"]) == []
    # The main value moves while nothing it read did: the main node is the
    # origin, and the copy and the tax are caused by it.
    noise_b = run(8916.0, 37067.30, ["pension@2026"])
    noise_r = run(8916.0, 37981.40, ["pension@2026"])
    for nodes in (noise_b, noise_r):
        nodes["pension@2026"] = _node([31200.0], is_input=True)
    found = bridge.uncaused_changes(noise_b, noise_r, ["tax@2026"])
    assert [item["variable"] for item in found] == ["agi@2026"]


def test__given_step_on_noise_above_131072__then_the_guard_still_sees_it():
    """Above 2**17 one float32 step is $0.015625, more than a cent; the
    review's counterexample at a $150,000 edge was missed with a fixed
    one-cent tolerance."""

    def run(ss, agi, ca_agi, tax):
        return {
            "tax@2026": _node([tax], ["ca_agi@2026"]),
            "ca_agi@2026": _node([ca_agi], ["agi@2026", "sub@2026"]),
            "agi@2026": _node([agi], ["ss@2026"]),
            "sub@2026": _node([agi - ca_agi], ["ss@2026"]),
            "ss@2026": _node([ss], is_input=True),
        }

    baseline = run(8916.0, 260099.70, 150000.0, 15.0)
    reform = run(10968.0, 262151.70, 149999.984375, 14.0)
    found = bridge.uncaused_changes(baseline, reform, ["tax@2026"])
    assert [item["variable"] for item in found] == ["tax@2026"]
    assert bridge.float32_step(150000.0) == 0.015625
    assert bridge.float32_step(30000.0) == 2**-9


@given(st.floats(1.0, 1e9, allow_nan=False, allow_infinity=False))
def test__given_any_value__then_float32_step_is_its_spacing(value):
    step = bridge.float32_step(value)
    # value lies in [2**(e-1), 2**e) and float32 keeps 24 bits.
    assert step * 2**23 <= value < step * 2**24


@given(
    st.lists(
        st.floats(0.02, 1e5, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=6,
    ),
    st.floats(0.02, 1e4, allow_nan=False, allow_infinity=False),
)
def test__given_chain_of_real_changes__then_the_guard_is_silent(
    steps, input_change
):
    """A chain where every variable moves with the one it reads, down to a
    changed input, is caused all the way."""

    def run(shift):
        nodes = {"x@2026": _node([100.0 + shift], is_input=True)}
        below = "x@2026"
        level = 100.0 + shift
        for index, step in enumerate(steps):
            key = f"v{index}@2026"
            level += step if shift else 0.0
            nodes[key] = _node([level], [below])
            below = key
        return nodes, below

    baseline, root = run(0.0)
    reform, _ = run(input_change)
    assert bridge.uncaused_changes(baseline, reform, [root]) == []


@given(
    st.lists(
        st.tuples(
            st.floats(-1e6, 1e6, allow_nan=False, allow_infinity=False),
            st.floats(-1e6, 1e6, allow_nan=False, allow_infinity=False),
        ),
        min_size=1,
        max_size=6,
    )
)
def test__given_identical_runs__then_the_guard_is_silent(values):
    nodes = {
        f"v{i}@2026": _node(
            [a, b], [f"v{i + 1}@2026"] if i + 1 < len(values) else []
        )
        for i, (a, b) in enumerate(values)
    }
    assert bridge.uncaused_changes(nodes, dict(nodes), ["v0@2026"]) == []


@given(
    st.floats(-1e6, 1e6, allow_nan=False, allow_infinity=False),
    st.floats(0.01, 1e4, allow_nan=False, allow_infinity=False),
    st.floats(0.0, 0.0099, allow_nan=False, allow_infinity=False),
)
def test__given_any_jump_over_a_sub_cent_read__then_it_is_reported(
    level, jump, noise
):
    """A jump of a cent or more is reported at every level, although
    ``level + jump - level`` can measure a little under a cent."""

    baseline = {
        "out@2026": _node([level], ["in@2026"]),
        "in@2026": _node([0.0], ["x@2026"]),
        "x@2026": _node([1.0], is_input=True),
    }
    reform = {
        "out@2026": _node([level + jump], ["in@2026"]),
        "in@2026": _node([noise], ["x@2026"]),
        "x@2026": _node([1.0], is_input=True),
    }
    found = bridge.uncaused_changes(baseline, reform, ["out@2026"])
    assert [item["variable"] for item in found] == ["out@2026"]


def _one_node(value):
    """An output that reads only an unchanged input."""

    return {
        "out@2026": _node([value], ["x@2026"]),
        "x@2026": _node([1.0], is_input=True),
    }


def test__given_exact_one_cent_float32_step__then_it_is_reported():
    """Round 2's nit N3, its minimal counterexample: float32 3.00 to 3.01
    measures 0.0099999905, under a cent, and was not reported."""

    before, after = float(np.float32(3.00)), float(np.float32(3.01))
    assert after - before < bridge.CENT_TOLERANCE
    found = bridge.uncaused_changes(
        _one_node(before), _one_node(after), ["out@2026"]
    )
    assert [item["variable"] for item in found] == ["out@2026"]


@given(st.integers(-(10**8), 10**8))
def test__given_any_one_cent_float32_step__then_it_is_reported(cents):
    """A one-cent step stored in float32 is reported at every magnitude
    where float32 can tell the two amounts apart (above $131,072 a cent
    can round away entirely, and then nothing changed)."""

    before = float(np.float32(cents / 100))
    after = float(np.float32((cents + 1) / 100))
    found = bridge.uncaused_changes(
        _one_node(before), _one_node(after), ["out@2026"]
    )
    reported = [item["variable"] for item in found]
    assert reported == (["out@2026"] if after != before else [])


def test__given_one_float32_step_of_noise_at_70000__then_it_is_reported():
    """The tradeoff, stated: from $65,536 to $131,072 one float32 step is
    $0.0078125, which float32 cannot tell from a one-cent change, so a
    step of pure noise is reported (a false alarm, not a miss)."""

    step = bridge.float32_step(70_000.0)
    assert step == 2**-7
    found = bridge.uncaused_changes(
        _one_node(70_000.0), _one_node(70_000.0 + step), ["out@2026"]
    )
    assert [item["variable"] for item in found] == ["out@2026"]


def test__given_one_cent_step_computed_from_larger_operands__then_missed():
    """The limit, stated: the bound covers a stored value.  x = a - 5,760
    in float32, with ``a`` moving by a cent near $35,760, moves by
    $0.0078125 (two float32 steps of ``a``), under the threshold at
    $30,000."""

    f32 = np.float32
    before = float(f32(f32(35_760.01) - f32(5_760.0)))
    after = float(f32(f32(35_760.02) - f32(5_760.0)))
    assert after - before == 2**-7
    found = bridge.uncaused_changes(
        _one_node(before), _one_node(after), ["out@2026"]
    )
    assert found == []


@given(
    st.floats(-2e5, 2e5, allow_nan=False, allow_infinity=False),
    st.integers(1, 1_000),
)
def test__given_change_under_half_a_cent__then_it_is_not_reported(
    level, microdollars
):
    """The float32 allowance never lowers the threshold below half a
    cent, so float noise on a large value is not a change."""

    change = min(microdollars * 1e-6, 0.0049)
    found = bridge.uncaused_changes(
        _one_node(level), _one_node(level + change), ["out@2026"]
    )
    assert found == []


def test__given_small_leaf_changes__then_they_are_listed():
    tree = bridge.ComponentTree(
        "root", {"root": (("a", 1), ("b", 1), ("c", -1))}
    )
    baseline = {"root": 10.0, "a": 5.0, "b": 3.0, "c": -2.0}
    reform = {"root": 12.01, "a": 6.99, "b": 3.0, "c": -2.02}
    result = _decompose(tree, baseline, reform)
    small = bridge.small_changes(result)
    assert [c.variable for c in small] == ["a", "c"]
    assert bridge.small_changes(result, limit_cents=199) == [small[1]]
