"""Properties of the population path's pure-Python parts.

INVENTED DATA - NOT A COMPARISON.  No policyengine-us import and no
subprocess: the array frame, the dataset layout, the population
decomposition, the exact weighted sums, the deciles and the invented
population are checked with Hypothesis and examples on invented inputs.
The live runs are in ``test_population_oracle.py``.
"""

from __future__ import annotations

import dataclasses
import math
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.bridge import invented_population as invented
from populace_dynamics.bridge import policyengine_us as bridge
from populace_dynamics.bridge import population as pop
from populace_dynamics.bridge import population_summary as summary
from populace_dynamics.min_benefit_track_m import invented as track_m_invented
from populace_dynamics.min_benefit_track_m.evaluation import PSID_FILES
from populace_dynamics.min_benefit_track_m.pipeline import (
    PSID_FILES_SOURCE_KEY,
)

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import pe_us_population_invented as script  # noqa: E402

AMOUNT = st.floats(
    min_value=0.0, max_value=1e7, allow_nan=False, allow_infinity=False
)
STATES = sorted(bridge.STATE_FIPS)


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------
def _renumber(labels):
    """Unit indices numbered in order of first appearance."""

    seen: dict[object, int] = {}
    return [seen.setdefault(label, len(seen)) for label in labels]


@st.composite
def frames(draw, max_households=5):
    """INVENTED populations whose units nest as policyengine-us requires.

    Household > SPM unit > family > (tax units, marital units of one or
    two people), numbered in order of first appearance, so the bridge's
    households round-trip exactly.
    """

    n_households = draw(st.integers(1, max_households))
    people: list[str] = []
    labels: dict[str, list[tuple[int, ...]]] = {
        kind: [] for kind in pop.GROUP_ENTITIES
    }
    for h in range(n_households):
        for s in range(draw(st.integers(1, 2))):
            for f in range(draw(st.integers(1, 2))):
                size = draw(st.integers(1, 4))
                tax = draw(
                    st.lists(
                        st.integers(0, size - 1), min_size=size, max_size=size
                    )
                )
                pairs = draw(
                    st.lists(st.booleans(), min_size=size, max_size=size)
                )
                marital = []
                unit = 0
                open_pair = False
                for i in range(size):
                    if open_pair:
                        open_pair = False
                    else:
                        unit += 1
                        open_pair = pairs[i]
                    marital.append(unit)
                for i in range(size):
                    people.append(f"p{i}")
                    labels["household"].append((h,))
                    labels["spm_unit"].append((h, s))
                    labels["family"].append((h, s, f))
                    labels["tax_unit"].append((h, s, f, tax[i]))
                    labels["marital_unit"].append((h, s, f, marital[i]))
    n = len(people)
    # Person ids are unique within a household.
    person_ids = [
        f"h{labels['household'][i][0]}{p}" for i, p in enumerate(people)
    ]
    person_ids = [f"{pid}_{i}" for i, pid in enumerate(person_ids)]
    units = {
        kind: np.asarray(_renumber(labels[kind]), dtype=np.int64)
        for kind in pop.GROUP_ENTITIES
    }
    n_spm = int(units["spm_unit"].max()) + 1
    spm_household = np.zeros(n_spm, dtype=np.int64)
    spm_household[units["spm_unit"]] = units["household"]
    heating = draw(
        st.lists(st.booleans(), min_size=n_households, max_size=n_households)
    )
    housing = draw(
        st.lists(st.booleans(), min_size=n_households, max_size=n_households)
    )
    return pop.PopulationFrame(
        person_ids=tuple(person_ids),
        age=np.asarray(
            draw(st.lists(st.integers(0, 125), min_size=n, max_size=n)),
            dtype=np.int64,
        ),
        amounts={
            name: np.asarray(
                draw(st.lists(AMOUNT, min_size=n, max_size=n)), dtype=float
            )
            for name in bridge.AMOUNT_FIELDS
        },
        medicare_quarters_of_coverage=np.asarray(
            draw(st.lists(st.integers(-1, 200), min_size=n, max_size=n)),
            dtype=np.int64,
        ),
        units=units,
        household_ids=tuple(f"hh{h}" for h in range(n_households)),
        state=tuple(
            draw(
                st.lists(
                    st.sampled_from(STATES),
                    min_size=n_households,
                    max_size=n_households,
                )
            )
        ),
        weight=np.asarray(
            draw(
                st.lists(
                    st.floats(0.01, 1e6, allow_nan=False),
                    min_size=n_households,
                    max_size=n_households,
                )
            )
        ),
        has_heating_cooling_expense=np.asarray(heating)[spm_household],
        takes_up_housing_assistance=np.asarray(housing)[spm_household],
        food_preparation_allowed=np.asarray(
            draw(
                st.lists(
                    st.booleans(),
                    min_size=n_households,
                    max_size=n_households,
                )
            )
        ),
    )


def _fields(frame, **changes):
    fields = {
        name: getattr(frame, name)
        for name in pop.PopulationFrame.__dataclass_fields__
    }
    fields.update(changes)
    return fields


# ---------------------------------------------------------------------------
# The frame: membership, round trips, refusals
# ---------------------------------------------------------------------------
@settings(max_examples=150, deadline=None)
@given(frames())
def test__given_population__then_every_person_is_in_exactly_one_unit_of_each_kind(  # noqa: E501
    frame,
):
    for kind in pop.GROUP_ENTITIES:
        index = frame.units[kind]
        assert index.shape == (frame.n_people,)
        counts = np.bincount(index)
        assert (counts > 0).all()
        assert int(counts.sum()) == frame.n_people
    assert (np.bincount(frame.units["marital_unit"]) <= 2).all()
    for kind, containers in pop.CONTAINING_ENTITIES.items():
        for container in containers:
            owner = {}
            for unit, outer in zip(
                frame.units[kind], frame.units[container], strict=True
            ):
                assert owner.setdefault(int(unit), int(outer)) == int(outer)


@settings(max_examples=150, deadline=None)
@given(frames(), st.integers(2000, 2100))
def test__given_population__then_the_dataset_layout_round_trips(frame, year):
    data = frame.to_dataset(year)
    period = str(year)
    assert set(data) >= {
        "person_id",
        *(f"{kind}_id" for kind in pop.GROUP_ENTITIES),
        *(f"person_{kind}_id" for kind in pop.GROUP_ENTITIES),
        *(f"person_{kind}_role" for kind in pop.GROUP_ENTITIES),
    }
    assert all(set(by) == {period} for by in data.values())
    for kind in pop.GROUP_ENTITIES:
        ids = data[f"{kind}_id"][period]
        members = data[f"person_{kind}_id"][period]
        assert set(members.tolist()) == set(ids.tolist())
        assert ids.min() >= 1
        assert (data[f"person_{kind}_role"][period] == 0).all()
    assert data["person_id"][period].tolist() == list(
        range(1, frame.n_people + 1)
    )
    back = pop.PopulationFrame.from_dataset(
        data,
        year,
        person_ids=frame.person_ids,
        household_ids=frame.household_ids,
    )
    assert back.equals(frame)


@settings(max_examples=150, deadline=None)
@given(frames(), st.integers(2000, 2100))
def test__given_population__then_bridge_households_and_situations_round_trip(
    frame, year
):
    households = frame.to_households()
    assert len(households) == frame.n_households
    assert pop.PopulationFrame.from_households(
        households, frame.weight
    ).equals(frame)
    situations = [bridge.to_situation(h, year) for h in households]
    again = [pop.household_from_situation(s, year) for s in situations]
    assert again == list(households)


@settings(max_examples=100, deadline=None)
@given(frames(), st.data())
def test__given_subset__then_each_household_keeps_its_people_and_amounts(
    frame, data
):
    chosen = data.draw(
        st.lists(
            st.integers(0, frame.n_households - 1),
            min_size=1,
            max_size=frame.n_households,
            unique=True,
        )
    )
    part = frame.subset(chosen)
    whole = frame.to_households()
    assert part.to_households() == tuple(whole[h] for h in chosen)
    assert np.array_equal(part.weight, frame.weight[chosen])
    assert frame.subset(range(frame.n_households)).equals(frame)


@settings(max_examples=100, deadline=None)
@given(
    frames(),
    st.sampled_from(bridge.AMOUNT_FIELDS),
    st.one_of(
        st.floats(max_value=-1e-9, allow_nan=False, allow_infinity=False),
        st.just(math.nan),
        st.just(math.inf),
        st.just(-math.inf),
    ),
    st.data(),
)
def test__given_negative_or_nonfinite_amount__then_the_frame_is_refused(
    frame, name, value, data
):
    i = data.draw(st.integers(0, frame.n_people - 1))
    array = frame.amounts[name].copy()
    array[i] = value
    with pytest.raises(ValueError):
        frame.with_amounts(**{name: array})


def test__given_bad_arrays__then_the_frame_is_refused():
    frame = _two_households()
    with pytest.raises(TypeError):
        pop.PopulationFrame(
            **_fields(
                frame,
                amounts={
                    **frame.amounts,
                    "interest_income": np.ones(frame.n_people, dtype=bool),
                },
            )
        )
    with pytest.raises(TypeError):
        pop.PopulationFrame(**_fields(frame, person_ids="abc"))
    with pytest.raises(ValueError, match="age must be"):
        pop.PopulationFrame(**_fields(frame, age=np.array([70, -1, 80])))
    with pytest.raises(ValueError, match="positive"):
        pop.PopulationFrame(**_fields(frame, weight=np.array([1.0, 0.0])))
    with pytest.raises(ValueError, match="STATE_FIPS"):
        pop.PopulationFrame(**_fields(frame, state=("CA", "XX")))
    with pytest.raises(ValueError, match="unique within"):
        pop.PopulationFrame(**_fields(frame, person_ids=("a", "a", "c")))
    with pytest.raises(ValueError, match="unique"):
        pop.PopulationFrame(**_fields(frame, household_ids=("h", "h")))


def test__given_bad_units__then_the_frame_is_refused():
    frame = _two_households()
    units = dict(frame.units)
    # A tax unit spanning two households.
    with pytest.raises(ValueError, match="inside one"):
        pop.PopulationFrame(
            **_fields(
                frame,
                units={**units, "tax_unit": np.array([0, 0, 0])},
            )
        )
    # A unit index with no member.
    with pytest.raises(ValueError, match="must have a member"):
        pop.PopulationFrame(
            **_fields(
                frame,
                units={**units, "tax_unit": np.array([0, 0, 2])},
            )
        )
    # A three-person marital unit.
    three = _one_household_of(3)
    with pytest.raises(ValueError, match="at most two"):
        pop.PopulationFrame(
            **_fields(
                three,
                units={**three.units, "marital_unit": np.array([0, 0, 0])},
            )
        )
    with pytest.raises(ValueError, match="units must be exactly"):
        pop.PopulationFrame(
            **_fields(
                frame,
                units={k: v for k, v in units.items() if k != "family"},
            )
        )


def _one_household_of(n):
    return pop.PopulationFrame(
        person_ids=tuple(f"p{i}" for i in range(n)),
        age=np.full(n, 70),
        amounts={name: np.zeros(n) for name in bridge.AMOUNT_FIELDS},
        medicare_quarters_of_coverage=np.full(n, -1),
        units={
            "household": np.zeros(n, dtype=np.int64),
            "spm_unit": np.zeros(n, dtype=np.int64),
            "family": np.zeros(n, dtype=np.int64),
            "tax_unit": np.arange(n),
            "marital_unit": np.arange(n),
        },
        household_ids=("h",),
        state=("CA",),
        weight=np.array([1.0]),
        has_heating_cooling_expense=np.array([True]),
        takes_up_housing_assistance=np.array([False]),
        food_preparation_allowed=np.array([True]),
    )


def _two_households():
    """A couple (one tax and marital unit) and a single, INVENTED."""

    return pop.PopulationFrame(
        person_ids=("a", "b", "c"),
        age=np.array([70, 68, 80]),
        amounts={name: np.zeros(3) for name in bridge.AMOUNT_FIELDS},
        medicare_quarters_of_coverage=np.array([-1, -1, -1]),
        units={
            "household": np.array([0, 0, 1]),
            "spm_unit": np.array([0, 0, 1]),
            "family": np.array([0, 0, 1]),
            "tax_unit": np.array([0, 0, 1]),
            "marital_unit": np.array([0, 0, 1]),
        },
        household_ids=("h1", "h2"),
        state=("CA", "FL"),
        weight=np.array([1.0, 2.0]),
        has_heating_cooling_expense=np.array([True, True]),
        takes_up_housing_assistance=np.array([False, False]),
        food_preparation_allowed=np.array([True, True]),
    )


def test__given_a_frame__then_its_arrays_are_read_only():
    frame = _two_households()
    with pytest.raises(ValueError):
        frame.amounts["interest_income"][0] = 1.0
    with pytest.raises(ValueError):
        frame.units["household"][0] = 1


# ---------------------------------------------------------------------------
# The decomposition over a population
# ---------------------------------------------------------------------------
#: A tree shaped like ``household_net_income``'s, with INVENTED leaves.
TREE = bridge.ComponentTree(
    bridge.ROOT_VARIABLE,
    {
        bridge.ROOT_VARIABLE: bridge.NET_INCOME_DEFINITION,
        "household_market_income": (
            ("employment_income", 1),
            ("ak_permanent_fund_dividend", 1),
        ),
        "household_benefits": (
            ("social_security", 1),
            ("ssi", 1),
            ("snap", 1),
            ("household_state_benefits", 1),
            ("tanf", 1),
        ),
        "household_state_benefits": (("ca_state_supplement", 1),),
        "household_refundable_tax_credits": (
            ("income_tax_refundable_credits", 1),
            ("household_refundable_state_tax_credits", 1),
        ),
        "household_refundable_state_tax_credits": (
            ("mt_refundable_credits", 1),
        ),
        "household_tax_before_refundable_credits": (
            ("employee_payroll_tax", 1),
            ("income_tax_before_refundable_credits", 1),
            ("household_state_tax_before_refundable_credits", 1),
            ("local_income_tax_before_refundable_credits", 1),
        ),
        "household_state_tax_before_refundable_credits": (
            ("state_income_tax_before_refundable_credits", 1),
            ("state_use_tax", 1),
        ),
        "household_health_costs": (),
    },
)
LEAVES = [name for name, _, _ in TREE.leaves()]
CENTS = st.integers(-(10**9), 10**9).map(lambda cents: cents / 100)
FLOAT32 = st.floats(
    min_value=-1e7, max_value=1e7, allow_nan=False, width=32
).map(float)


def _node_values(tree, leaf_values):
    values = dict(leaf_values)

    def value(name):
        if tree.is_leaf(name):
            return values.setdefault(name, 0.0)
        total = math.fsum(
            sign * value(part) for part, sign in tree.children[name]
        )
        values[name] = total
        return total

    value(tree.root)
    return values


@st.composite
def population_runs(draw, amounts=CENTS, changing=None):
    n = draw(st.integers(1, 6))
    runs = []
    for _ in range(2):
        households = []
        for _ in range(n):
            leaf = {
                name: (
                    draw(amounts)
                    if changing is None or name in changing
                    else 0.0
                )
                for name in LEAVES
            }
            households.append(_node_values(TREE, leaf))
        runs.append(
            {
                name: np.asarray([h[name] for h in households])
                for name in households[0]
            }
        )
    return runs


CLASSIFIED = [
    name for name in LEAVES if name not in ("tanf", "household_health_costs")
]


@settings(max_examples=200, deadline=None)
@given(population_runs(changing=CLASSIFIED))
def test__given_population__then_each_household_decomposes_as_the_bridge_does(
    run,
):
    """The differential: household ``h`` equals ``bridge.decompose``."""

    baseline, reform = run
    together = pop.decompose_population(TREE, baseline, reform)
    for h in range(together.n_households):
        alone = bridge.decompose(
            TREE,
            {k: float(v[h]) for k, v in baseline.items()},
            {k: float(v[h]) for k, v in reform.items()},
        )
        got = together.household(h).as_dict()
        expected = alone.as_dict()
        got.pop("max_aggregate_gap")
        expected.pop("max_aggregate_gap")
        assert got == expected


@settings(max_examples=200, deadline=None)
@given(population_runs(amounts=FLOAT32, changing=CLASSIFIED))
def test__given_float32_values__then_cents_match_the_bridge_exactly(run):
    baseline, _ = run
    for name in LEAVES:
        fast = pop.to_cents_array(baseline[name])
        slow = [bridge.to_cents(float(v)) for v in baseline[name]]
        assert fast.tolist() == slow


@settings(max_examples=300)
@given(
    st.lists(
        st.floats(allow_nan=False, allow_infinity=False, width=64),
        max_size=20,
    )
)
def test__given_any_floats__then_to_cents_array_is_the_bridges_to_cents(
    values,
):
    finite = [v for v in values if abs(v) < 1e15]
    assert pop.to_cents_array(finite).tolist() == [
        bridge.to_cents(v) for v in finite
    ]


@settings(max_examples=200, deadline=None)
@given(population_runs(changing=CLASSIFIED), st.data())
def test__given_population__then_the_weighted_identity_holds_exactly(
    run, data
):
    baseline, reform = run
    decomposition = pop.decompose_population(TREE, baseline, reform)
    n = decomposition.n_households
    assert (
        sum(
            decomposition.change_cents(j)
            for j in range(len(decomposition.leaves))
        )
        == decomposition.net_change_cents
    ).all()
    weights = data.draw(
        st.lists(
            st.floats(0.001, 1e6, allow_nan=False), min_size=n, max_size=n
        )
    )
    people = data.draw(st.lists(st.integers(1, 6), min_size=n, max_size=n))
    labels = np.asarray(
        data.draw(
            st.lists(st.sampled_from(("a", "b", "c")), min_size=n, max_size=n)
        ),
        dtype=object,
    )
    out = summary.summarize(
        decomposition, weights, people, {"g": (labels, ("a", "b", "c"))}
    )
    population = out["population"]
    assert all(population["identity_exact"].values())
    assert out["groupings"]["g"]["partition_exact"]
    exact = pop.ExactWeights.from_floats(weights)
    net = exact.dollars(decomposition.net_change_cents)
    assert population["net_change_exact"] == str(net)
    take_back = population["take_back"]
    if take_back["share"] is not None:
        assert math.isclose(
            sum(take_back["by_level"].values()),
            take_back["share"],
            rel_tol=1e-9,
            abs_tol=1e-12,
        )
        assert take_back["exact_parts_sum_to_share"]


@settings(max_examples=100, deadline=None)
@given(population_runs(changing=CLASSIFIED))
def test__given_reform_equal_to_baseline__then_nothing_changes(run):
    baseline, _ = run
    decomposition = pop.decompose_population(TREE, baseline, baseline)
    assert not decomposition.changed_leaves()
    assert (decomposition.net_change_cents == 0).all()


def test__given_changed_unclassified_leaf__then_decomposition_is_refused():
    baseline = _node_values(TREE, {name: 0.0 for name in LEAVES})
    reform = _node_values(
        TREE, {**{name: 0.0 for name in LEAVES}, "tanf": 10.0}
    )
    base = {k: np.array([v]) for k, v in baseline.items()}
    ref = {k: np.array([v]) for k, v in reform.items()}
    with pytest.raises(pop.UnclassifiedChangeError, match="tanf"):
        pop.decompose_population(TREE, base, ref)
    pop.decompose_population(TREE, base, ref, require_classified_changes=False)


def test__given_inconsistent_or_nonfinite_values__then_it_is_refused():
    leaves = {name: 1.0 for name in LEAVES}
    good = _node_values(TREE, leaves)
    base = {k: np.array([v, v]) for k, v in good.items()}
    bad = {
        **base,
        "household_benefits": np.array([good["household_benefits"], 99.0]),
    }
    with pytest.raises(bridge.AggregateMismatchError):
        pop.decompose_population(TREE, base, bad)
    nan = {**base, "ssi": np.array([1.0, math.nan])}
    with pytest.raises(bridge.AggregateMismatchError, match="finite"):
        pop.decompose_population(TREE, base, nan)
    drifted = bridge.ComponentTree(
        TREE.root,
        {
            **TREE.children,
            TREE.root: TREE.children[TREE.root][:-1],
        },
    )
    with pytest.raises(bridge.DefinitionDriftError):
        pop.decompose_population(drifted, base, base)
    with pytest.raises(bridge.DefinitionDriftError):
        pop.decompose_population(TREE, base, base, reform_tree=drifted)


def test__levels__then_each_leaf_has_its_level_of_government():
    level = {
        name: pop.level_for(name, path) for name, path, _ in TREE.leaves()
    }
    assert level["social_security"] == "federal"
    assert level["ssi"] == "federal"
    assert level["snap"] == "federal"
    assert level["income_tax_before_refundable_credits"] == "federal"
    assert level["employee_payroll_tax"] == "federal"
    assert level["ca_state_supplement"] == "state"
    assert level["mt_refundable_credits"] == "state"
    assert level["state_income_tax_before_refundable_credits"] == "state"
    assert level["state_use_tax"] == "state"
    assert level["local_income_tax_before_refundable_credits"] == "local"
    assert level["employment_income"] == "market_income"
    assert level["ak_permanent_fund_dividend"] == "state"
    assert level["household_health_costs"] == "health"
    assert level["tanf"] is None
    assert set(pop.LEVEL_LABELS) == set(pop.LEVELS)


# ---------------------------------------------------------------------------
# Exact weights, take-back and deciles
# ---------------------------------------------------------------------------
WEIGHTS = st.lists(
    st.floats(0.0, 1e7, allow_nan=False, allow_infinity=False),
    min_size=1,
    max_size=30,
)


@settings(max_examples=300)
@given(WEIGHTS, st.data())
def test__given_float_weights__then_exact_sums_are_exact_and_linear(
    weights, data
):
    exact = pop.ExactWeights.from_floats(weights)
    for numerator, weight in zip(exact.numerators, weights, strict=True):
        assert Fraction(numerator, exact.denominator) == Fraction(weight)
    n = len(weights)
    cents = st.lists(st.integers(-(10**12), 10**12), min_size=n, max_size=n)
    a = np.asarray(data.draw(cents), dtype=np.int64)
    b = np.asarray(data.draw(cents), dtype=np.int64)
    assert exact.dollars(a) + exact.dollars(b) == exact.dollars(a + b)
    assert exact.dollars(a) == sum(
        (Fraction(w) * int(c) / 100 for w, c in zip(weights, a, strict=True)),
        Fraction(0),
    )
    mask = np.asarray(
        data.draw(st.lists(st.booleans(), min_size=n, max_size=n))
    )
    assert exact.dollars(a, mask) + exact.dollars(a, ~mask) == exact.dollars(a)


def test__given_nonfinite_or_negative_weight__then_it_is_refused():
    for bad in (math.nan, math.inf, -1.0):
        with pytest.raises(ValueError):
            pop.ExactWeights.from_floats([1.0, bad])
    with pytest.raises(TypeError):
        pop.ExactWeights.from_floats([1.0]).dollars(np.array([1.5]))


@settings(max_examples=300)
@given(
    st.integers(-(10**9), 10**9).filter(bool),
    st.lists(st.integers(-(10**9), 10**9), min_size=5, max_size=5),
)
def test__take_back__then_levels_sum_exactly_to_the_share(ss, others):
    levels = ("federal", "state", "local", "health", "market_income")
    by_level = {
        level: {"change": Fraction(change, 100)}
        for level, change in zip(levels, others, strict=True)
    }
    by_level["federal"]["change"] += Fraction(ss, 100)
    out = summary.take_back(by_level, Fraction(ss, 100))
    net = sum((entry["change"] for entry in by_level.values()), Fraction(0))
    assert out["exact_parts_sum_to_share"]
    assert out["share"] == float((Fraction(ss, 100) - net) / Fraction(ss, 100))
    none = summary.take_back(by_level, Fraction(0))
    assert none["share"] is None


def _brute_deciles(values, weights):
    total = sum(weights)
    out = []
    for v in values:
        rank = sum(w for x, w in zip(values, weights, strict=True) if x <= v)
        share = min(rank / total, 1.0)
        decile = min(math.ceil(share * 10), 10)
        out.append(-1 if v < 0 else decile)
    return out


@settings(max_examples=300)
@given(
    st.lists(
        st.tuples(
            st.integers(-50, 50).map(lambda x: x * 1000.0),
            st.integers(1, 20).map(float),
        ),
        min_size=1,
        max_size=40,
    )
)
def test__deciles__then_they_equal_the_weighted_rank_definition(pairs):
    """microdf's max-rank semantics, recomputed by brute force.

    Integer weights keep the brute-force sums exact, so a rank exactly at a
    decile boundary is compared exactly.
    """

    values = [v for v, _ in pairs]
    weights = [w for _, w in pairs]
    got = pop.decile_ranks(values, weights)
    assert got.tolist() == _brute_deciles(values, weights)
    assert set(got.tolist()) <= {-1, *range(1, 11)}


# ---------------------------------------------------------------------------
# The invented population
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def track_m():
    parameters, cola = track_m_invented.invented_parameters()
    # INVENTED: the invented COLAs (2.5 percent) through 2025.
    rates = {**cola, **{year: 0.025 for year in range(2022, 2026)}}
    return parameters, cola, rates


def _build(track_m, seed, n=24):
    parameters, cola, rates = track_m
    cohort = invented.build_invented_cohort(
        seed=seed,
        n_family_units=n,
        params=parameters.params,
        cola_rates=cola,
    )
    result = invented.evaluate_headline(cohort.inputs, parameters)
    table = invented.person_benefits(
        cohort.inputs,
        result,
        parameters,
        rates,
        persons=cohort.cohort.persons,
    )
    population = invented.build_population(cohort, table, seed=seed)
    return cohort, result, table, population


@pytest.fixture(scope="module")
def built(track_m):
    return _build(track_m, seed=11, n=120)


def test__same_seed__then_the_invented_population_is_identical(track_m):
    first = _build(track_m, seed=5)
    second = _build(track_m, seed=5)
    for scenario in invented.SIMULATED_SCENARIOS:
        assert first[3].frames[scenario].equals(second[3].frames[scenario])
    pd.testing.assert_frame_equal(first[2], second[2])
    pd.testing.assert_frame_equal(first[3].households, second[3].households)


def test__different_seed__then_the_invented_population_differs(track_m):
    first = _build(track_m, seed=5)
    other = _build(track_m, seed=6)
    assert (
        not first[3]
        .frames["current_law"]
        .equals(other[3].frames["current_law"])
    )


def test__invented_inputs__then_one_probability_never_shifts_other_draws(
    monkeypatch,
):
    """Every variate is drawn whether or not it is used."""

    members = pd.DataFrame(
        {
            "person_id": [101, 102, 201],
            "family_unit_id": [1, 1, 2],
            "role": ["reference_person", "spouse", "reference_person"],
        }
    )
    families, people = invented.invented_other_inputs(members, seed=3)
    again_f, again_p = invented.invented_other_inputs(members, seed=3)
    pd.testing.assert_frame_equal(families, again_f)
    pd.testing.assert_frame_equal(people, again_p)
    changed = {
        **invented.INVENTED_DISTRIBUTIONS,
        "renter": {"probability": 1.0},
        "labor": {
            **invented.INVENTED_DISTRIBUTIONS["labor"],
            "probability": dict.fromkeys(
                ("reference_person", "spouse", "other_member"), 0.0
            ),
        },
    }
    monkeypatch.setattr(invented, "INVENTED_DISTRIBUTIONS", changed)
    families2, people2 = invented.invented_other_inputs(members, seed=3)
    assert families2["renter"].all()
    assert (people2["labor"] == 0).all()
    for column in ("state", "wealth1", "vehicles"):
        assert families2[column].tolist() == families[column].tolist()
    for column in ("annuities", "interest"):
        assert people2[column].tolist() == people[column].tolist()


def test__records_not_marked_invented__then_they_are_never_evaluated(
    track_m, built, monkeypatch
):
    parameters, _, _ = track_m
    inputs = built[0].inputs

    def forbidden(*args, **kwargs):
        raise AssertionError("evaluate ran on records it must refuse")

    monkeypatch.setattr(invented, "evaluate", forbidden)
    refused = (
        dataclasses.replace(inputs, provenance_kind=PSID_FILES),
        dataclasses.replace(
            inputs,
            source={**inputs.source, PSID_FILES_SOURCE_KEY: {"f": "x"}},
        ),
        dataclasses.replace(
            inputs,
            source={k: v for k, v in inputs.source.items() if k != "label"},
        ),
    )
    for records in refused:
        with pytest.raises(ValueError):
            invented.evaluate_headline(records, parameters)
        with pytest.raises(ValueError):
            invented.require_invented(records)


def test__invented_population__then_households_are_family_units(built):
    cohort, _, table, population = built
    frame = population.frames["current_law"]
    people = population.people
    assert frame.n_people == len(cohort.cohort.persons) == len(table)
    assert frame.n_households == people["family_unit_id"].nunique()
    for _, members in people.groupby("family_unit_id"):
        units = {
            kind: set(frame.units[kind][members.index].tolist())
            for kind in pop.GROUP_ENTITIES
        }
        assert len(units["household"]) == len(units["spm_unit"]) == 1
        assert len(units["family"]) == 1
        couple = members[members["role"] != "other_member"].index
        if len(couple) == 2:
            assert len(set(frame.units["tax_unit"][couple])) == 1
            assert len(set(frame.units["marital_unit"][couple])) == 1
        others = members[members["role"] == "other_member"].index
        for i in others:
            assert (
                frame.units["tax_unit"] == frame.units["tax_unit"][i]
            ).sum() == 1
    assert (frame.medicare_quarters_of_coverage == -1).all()
    assert set(frame.state) <= set(bridge.STATE_FIPS)
    assert (frame.age >= 2026 - 1960).all()


def test__invented_population__then_social_security_is_the_benefit_table(
    built,
):
    _, _, table, population = built
    by_person = table.set_index(table["person_id"].astype(str))
    for scenario in invented.SIMULATED_SCENARIOS:
        frame = population.frames[scenario]
        for kind in ("retirement", "dependents", "survivors"):
            got = frame.amounts[f"social_security_{kind}"]
            expected = by_person.loc[
                list(frame.person_ids), f"{scenario}__social_security_{kind}"
            ].to_numpy(dtype=float)
            assert np.array_equal(got, expected)
        assert (frame.amounts["social_security_disability"] == 0).all()
    base, reform = (population.frames[s] for s in invented.SIMULATED_SCENARIOS)
    assert base.same_structure(reform)
    for name in bridge.AMOUNT_FIELDS:
        if not name.startswith("social_security"):
            assert np.array_equal(base.amounts[name], reform.amounts[name])


def test__benefits__then_only_the_window_and_the_minimum_move_them(built):
    """Unexposed people keep their benefit; a rise needs the minimum."""

    cohort, result, table, _ = built
    unexposed = ~table["exposed"]
    for scenario in ("option_1", "option_2"):
        assert (
            table.loc[unexposed, f"{scenario}__social_security"]
            == table.loc[unexposed, "current_law__social_security"]
        ).all()
    for outcome in result.workers.values():
        headline = outcome.outcomes[invented.HEADLINE_OPTION]
        if not headline.on_minimum:
            assert headline.option_pia <= outcome.pia
    rises = table["option_2__social_security"] > (
        table["current_law__social_security"]
    )
    # Without a spouse's or survivor's link (whose dual-entitlement offset
    # can rise when the own PIA is cut), only the own minimum raises a
    # benefit.
    unlinked = {
        person.person_id: person
        for person in cohort.inputs.persons
        if not person.links
    }
    for person_id in table.loc[rises, "person_id"]:
        person = unlinked.get(person_id)
        if person is None:
            continue
        assert person.own_record_id is not None
        own = result.workers[person.own_record_id]
        assert own.outcomes[invented.HEADLINE_OPTION].on_minimum


def test__zero_pia_own_beneficiaries__then_they_keep_their_2022_amount(built):
    cohort, _, table, _ = built
    persons = cohort.cohort.persons.set_index(
        cohort.cohort.persons["person_id"].astype(str)
    )
    observed = table[table["own_benefit_source"] == "observed_2022_amount"]
    assert len(observed)  # the invented other members have no earnings
    factor = 1.025**4  # INVENTED COLAs 2022-2025
    for row in observed.itertuples(index=False):
        amount = float(persons.loc[row.person_id, "amount_2022"])
        monthly = math.floor(amount / 12 * factor + 1e-9)
        for scenario in invented.BENEFIT_SCENARIOS:
            assert getattr(row, f"own_{scenario}") == monthly
            assert getattr(row, f"auxiliary_{scenario}") == 0
    assert (table["current_law__social_security"] > 0).all()


# ---------------------------------------------------------------------------
# The script's own checks
# ---------------------------------------------------------------------------
def test__overrides__then_only_a_states_own_parameters_are_accepted():
    ok = script.parameter_overrides(
        [
            {
                "parameter": "gov.states.ca.cdss.x",
                "states": ["CA"],
                "value": 1.0,
            }
        ]
    )
    assert ok == {"gov.states.ca.cdss.x": 1.0}
    with pytest.raises(ValueError, match="other states"):
        script.parameter_overrides(
            [{"parameter": "gov.ssa.ssi.x", "states": ["CA"], "value": 1.0}]
        )
    with pytest.raises(ValueError, match="other states"):
        script.parameter_overrides(
            [
                {
                    "parameter": "gov.states.ca.x",
                    "states": ["CA", "FL"],
                    "value": 1.0,
                }
            ]
        )


def _single_leaf_run(ss_change, other_change):
    baseline = _node_values(TREE, {name: 100.0 for name in LEAVES})
    reform = _node_values(
        TREE,
        {
            **{name: 100.0 for name in LEAVES},
            "social_security": 100.0 + ss_change,
            "snap": 100.0 + other_change,
        },
    )
    return pop.decompose_population(
        TREE,
        {k: np.array([v]) for k, v in baseline.items()},
        {k: np.array([v]) for k, v in reform.items()},
    )


def test__household_checks__then_a_change_without_social_security_is_refused():
    with pytest.raises(AssertionError, match="although their Social"):
        script.household_checks(_single_leaf_run(0.0, 5.0), ("CA",))
    ok = script.household_checks(_single_leaf_run(-100.0, 30.0), ("CA",))
    assert ok["wrong_way_changes"] == 0
    wrong = script.household_checks(_single_leaf_run(-100.0, -30.0), ("AL",))
    assert wrong["wrong_way_changes"] == 1
    assert wrong["wrong_way_by_state"] == {"AL": 1}
    assert wrong["wrong_way_cases"][0]["category"] == "snap"


def test__chart_series__then_every_classified_leaf_has_one():
    decomposition = _single_leaf_run(-100.0, 30.0)
    series = {
        leaf[0]: script.chart_series(leaf) for leaf in decomposition.leaves
    }
    assert series["social_security"] == "social_security"
    assert series["ssi"] == "ssi"
    assert series["snap"] == "federal_benefits"
    assert series["income_tax_before_refundable_credits"] == "federal_taxes"
    assert series["income_tax_refundable_credits"] == "federal_taxes"
    assert series["employee_payroll_tax"] == "federal_taxes"
    assert series["ca_state_supplement"] == "state_benefits"
    assert series["ak_permanent_fund_dividend"] == "state_benefits"
    assert series["mt_refundable_credits"] == "state_local_taxes"
    assert series["state_use_tax"] == "state_local_taxes"
    assert series["local_income_tax_before_refundable_credits"] == (
        "state_local_taxes"
    )
    assert series["employment_income"] == "other"
    assert {key for key, _ in script.CHART_SERIES} == (
        set(series.values()) - {"other"}
    )


def test__chart_values__then_series_sum_exactly_to_the_net_change():
    decomposition = _single_leaf_run(-100.0, 30.0)
    frame = _one_household_of(1)
    run = {
        "_internal": {
            "decompositions": {"default": decomposition},
            "groupings": {
                "g": (np.asarray(["a"], dtype=object), ("a",)),
            },
            "frame": frame,
        }
    }
    groups, values, net = script.chart_values(run, "g", ("a",))
    assert groups == ["a"]
    assert math.isclose(values.sum(), net[0])
    assert net[0] == -70.0
