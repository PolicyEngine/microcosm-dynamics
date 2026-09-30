"""Properties of the PolicyEngine-US bridge's pure-Python parts.

No policyengine-us import and no subprocess: the situation builder, the
decomposition and the COLA helpers are checked with Hypothesis on INVENTED
households, trees and amounts.  The live runner is exercised in
``test_policyengine_us_bridge_oracle.py``.
"""

from __future__ import annotations

import itertools
import json
import math
from decimal import Decimal

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
            "income_tax_refundable_credits",
            ("household_refundable_tax_credits",),
            "federal_income_tax",
        ),
        (
            "mt_refundable_credits",
            (
                "household_refundable_tax_credits",
                "household_refundable_state_tax_credits",
            ),
            "state_income_tax",
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
            "other_benefits",
        ),
    ],
)
def test__given_leaf__then_category_is_the_documented_one(
    variable, path, category
):
    assert bridge.category_for(variable, ("household_net_income", *path)) == (
        category
    )
    assert category in bridge.CATEGORY_ORDER


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


@given(PIA, PIA, RATES)
def test__given_larger_pia__then_carried_pia_is_not_smaller(a, b, rates):
    low, high = sorted((a, b))
    assert _carry(low, rates) <= _carry(high, rates)


@given(PIA, RATES)
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
