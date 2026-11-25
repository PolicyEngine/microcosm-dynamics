"""Hypothesis tests of the starting-stock invariants, and a differential test.

Each test states one invariant from ``populace_dynamics.starting_stock``'s
docstring. Every input is generated or invented; none stands for any
year's law or data. Hypothesis stays light: at most 100 examples, no
deadline, and no explain phase.
"""

from __future__ import annotations

import math
from collections import Counter

from hypothesis import Phase, assume, given, settings
from hypothesis import strategies as st

from populace_dynamics import claiming
from populace_dynamics.starting_stock import (
    benefit_from_pia,
    claim_age_posterior,
    cola_factor,
    disabled_worker_claim_factor,
    draw_claim_age,
    infer_pia,
    retired_worker_claim_factor,
    rounding_bound,
    single_year_age,
)

_PHASES = (
    Phase.explicit,
    Phase.reuse,
    Phase.generate,
    Phase.target,
    Phase.shrink,
)
LIGHT = settings(max_examples=100, deadline=None, phases=_PHASES)
LIGHTER = settings(max_examples=20, deadline=None, phases=_PHASES)

#: Relative precision of a multiply-then-divide round trip, with room.
ROUND_TRIP_RTOL = 1e-12


@st.composite
def cola_paths(draw, *, rates=None, min_years=0, max_years=40):
    """A COLA path: the rates and the years they cover."""
    rate = (
        rates
        if rates is not None
        else st.floats(min_value=-0.05, max_value=0.25, allow_nan=False)
    )
    eligibility = draw(st.integers(min_value=1975, max_value=2045))
    years = draw(st.integers(min_value=min_years, max_value=max_years))
    path = {eligibility + i: draw(rate) for i in range(years)}
    return {
        "cola_rates": path,
        "eligibility_year": eligibility,
        "payment_year": eligibility + years,
    }


#: Positive claim factors, from far below to far above a real one.
claim_factors = st.floats(min_value=1e-3, max_value=10.0, allow_nan=False)
#: PIAs of zero or more, at magnitudes where relative precision holds.
pias = st.one_of(
    st.just(0.0), st.floats(min_value=1e-6, max_value=1e7, allow_nan=False)
)
#: Benefits of zero or more, including negative zero.
benefits = st.one_of(
    st.just(0.0),
    st.just(-0.0),
    st.floats(min_value=1e-6, max_value=1e7, allow_nan=False),
)


@st.composite
def retired_claim_factors(draw, params):
    """A claim factor from the INVENTED schedule, at 62 to 70."""
    months = draw(st.integers(min_value=62 * 12, max_value=70 * 12))
    birth_year = draw(st.integers(min_value=1940, max_value=1995))
    return retired_worker_claim_factor(months, birth_year, params)


@st.composite
def award_share_tables(draw):
    """Invented award shares that vary with sex and entitlement year."""
    base = draw(
        st.lists(
            st.floats(min_value=0.0, max_value=100.0, allow_nan=False),
            min_size=9,
            max_size=9,
        )
    )
    tilt = draw(
        st.lists(
            st.floats(min_value=0.0, max_value=2.0, allow_nan=False),
            min_size=9,
            max_size=9,
        )
    )

    def award_shares(sex, year):
        lean = 1.0 if sex == "female" else 0.5
        return {
            age: base[i] * (1.0 + lean * tilt[i] * ((year % 7) / 7.0))
            for i, age in enumerate(claiming.CLAIM_AGES)
        }

    return award_shares


people = st.fixed_dictionaries(
    {
        "age": st.integers(min_value=62, max_value=105),
        "birth_year": st.integers(min_value=1900, max_value=1965),
        "sex": st.sampled_from(["female", "male"]),
    }
)
seeds = st.integers(min_value=0, max_value=2**63)


def _feasible_weights(person, award_shares):
    top = min(70, person["age"])
    return [
        award_shares(person["sex"], person["birth_year"] + c)[c]
        for c in range(62, top + 1)
    ]


# --------------------------------------------------------------------------
# 1. The unrounded inverse is exact
# --------------------------------------------------------------------------
@LIGHT
@given(pia=pias, path=cola_paths(), claim=claim_factors)
def test_unrounded_inverse_is_exact(pia, path, claim):
    benefit = benefit_from_pia(
        pia, **path, claim_factor=claim, statutory_rounding=False
    )
    back = infer_pia(benefit, **path, claim_factor=claim)
    assert math.isclose(back, pia, rel_tol=ROUND_TRIP_RTOL, abs_tol=0.0)


@LIGHT
@given(benefit=benefits, path=cola_paths(), claim=claim_factors)
def test_unrounded_forward_returns_the_benefit(benefit, path, claim):
    pia = infer_pia(benefit, **path, claim_factor=claim)
    back = benefit_from_pia(
        pia, **path, claim_factor=claim, statutory_rounding=False
    )
    assert math.isclose(back, benefit, rel_tol=ROUND_TRIP_RTOL, abs_tol=0.0)


# --------------------------------------------------------------------------
# 2. Rounding stays inside its bound
# --------------------------------------------------------------------------
@LIGHT
@given(data=st.data())
def test_rounding_stays_inside_its_bound(data, invented_ssa_parameters):
    path = data.draw(cola_paths(), label="path")
    claim = data.draw(
        st.one_of(
            st.floats(min_value=0.3, max_value=1.6, allow_nan=False),
            retired_claim_factors(invented_ssa_parameters),
        ),
        label="claim",
    )
    pia = data.draw(
        st.one_of(
            st.integers(min_value=0, max_value=60_000).map(lambda d: d / 10),
            st.floats(min_value=0.0, max_value=20_000.0, allow_nan=False),
        ),
        label="pia",
    )
    benefit = benefit_from_pia(
        pia, **path, claim_factor=claim, statutory_rounding=True
    )
    inferred = infer_pia(benefit, **path, claim_factor=claim)
    back = benefit_from_pia(
        inferred, **path, claim_factor=claim, statutory_rounding=True
    )
    bound = rounding_bound(**path, claim_factor=claim)
    assert abs(back - benefit) <= bound
    # No floor rounds up, so the round trip never lands above.
    assert back <= benefit


# --------------------------------------------------------------------------
# 3. No negative PIA
# --------------------------------------------------------------------------
@LIGHT
@given(benefit=benefits, path=cola_paths(), claim=claim_factors)
def test_no_negative_pia(benefit, path, claim):
    pia = infer_pia(benefit, **path, claim_factor=claim)
    assert pia >= 0.0
    assert math.copysign(1.0, pia) == 1.0


# --------------------------------------------------------------------------
# 4. Monotone
# --------------------------------------------------------------------------
@LIGHT
@given(
    pair=st.lists(benefits, min_size=2, max_size=2),
    path=cola_paths(),
    claim=claim_factors,
)
def test_higher_benefit_never_infers_lower_pia(pair, path, claim):
    low, high = sorted(pair)
    assert infer_pia(low, **path, claim_factor=claim) <= infer_pia(
        high, **path, claim_factor=claim
    )


# --------------------------------------------------------------------------
# 5. The posterior is a distribution
# --------------------------------------------------------------------------
@LIGHT
@given(person=people, award_shares=award_share_tables())
def test_posterior_is_a_distribution(person, award_shares):
    if not any(w > 0.0 for w in _feasible_weights(person, award_shares)):
        try:
            claim_age_posterior(**person, award_shares=award_shares)
        except ValueError:
            return
        raise AssertionError("an all-zero posterior must raise")
    posterior = claim_age_posterior(**person, award_shares=award_shares)
    assert all(weight >= 0.0 for weight in posterior.values())
    assert math.isclose(sum(posterior.values()), 1.0, rel_tol=1e-12)
    assert set(posterior) <= set(range(62, min(70, person["age"]) + 1))


# --------------------------------------------------------------------------
# 6. Draws are a function of the key
# --------------------------------------------------------------------------
@LIGHT
@given(
    person=people,
    award_shares=award_share_tables(),
    seed=seeds,
    ids=st.lists(
        st.integers(min_value=0, max_value=10**12),
        min_size=1,
        max_size=20,
        unique=True,
    ),
    others=st.lists(st.integers(min_value=0, max_value=10**12), max_size=20),
    order=st.randoms(use_true_random=False),
)
def test_draws_are_a_function_of_the_key(
    person, award_shares, seed, ids, others, order
):
    if not any(w > 0.0 for w in _feasible_weights(person, award_shares)):
        return

    def batch(members):
        return {
            pid: draw_claim_age(
                pid, **person, award_shares=award_shares, seed=seed
            )
            for pid in members
        }

    alone = batch(ids)
    again = batch(ids)
    joined = list(ids) + [pid for pid in others if pid not in set(ids)]
    order.shuffle(joined)
    with_others = batch(joined)
    assert alone == again
    assert all(with_others[pid] == alone[pid] for pid in ids)


# --------------------------------------------------------------------------
# 7. Draws follow the posterior
# --------------------------------------------------------------------------
#: Person ids per example. The tolerance at each claim age is five
#: binomial standard errors, sqrt(p (1 - p) / n), plus 1 / n; at n = 4,000
#: that is at most about 0.040 in absolute share.
DRAWS = 4_000
SE_MULTIPLE = 5.0


@LIGHTER
@given(person=people, award_shares=award_share_tables(), seed=seeds)
def test_draws_follow_the_posterior(person, award_shares, seed):
    if not any(w > 0.0 for w in _feasible_weights(person, award_shares)):
        return
    posterior = claim_age_posterior(**person, award_shares=award_shares)
    counts = Counter(
        draw_claim_age(pid, **person, award_shares=award_shares, seed=seed)
        for pid in range(DRAWS)
    )
    assert set(counts) <= {age for age, p in posterior.items() if p > 0.0}
    for age, share in posterior.items():
        tolerance = (
            SE_MULTIPLE * math.sqrt(share * (1.0 - share) / DRAWS)
            + 1.0 / DRAWS
        )
        assert abs(counts[age] / DRAWS - share) <= tolerance, (age, share)


@LIGHTER
@given(
    top_code=st.sampled_from([80, 85]),
    weights=st.lists(
        st.floats(min_value=0.01, max_value=10.0, allow_nan=False),
        min_size=5,
        max_size=5,
    ),
    seed=seeds,
)
def test_single_year_draws_stay_in_band_and_follow_shares(
    top_code, weights, seed
):
    shares = {top_code + i: w for i, w in enumerate(weights)}
    total = sum(weights)
    counts = Counter(
        single_year_age(
            pid,
            top_code,
            "female",
            age_shares=lambda code, sex: shares,
            seed=seed,
        )
        for pid in range(DRAWS)
    )
    assert set(counts) <= set(shares)
    for age, weight in shares.items():
        share = weight / total
        tolerance = (
            SE_MULTIPLE * math.sqrt(share * (1.0 - share) / DRAWS)
            + 1.0 / DRAWS
        )
        assert abs(counts[age] / DRAWS - share) <= tolerance


# --------------------------------------------------------------------------
# 8. Disabled workers
# --------------------------------------------------------------------------
@LIGHT
@given(benefit=benefits, path=cola_paths())
def test_disabled_worker_pia_is_benefit_over_cola_factor(benefit, path):
    pia = infer_pia(
        benefit, **path, claim_factor=disabled_worker_claim_factor()
    )
    expected = benefit / cola_factor(
        path["cola_rates"], path["eligibility_year"], path["payment_year"]
    )
    assert pia == expected


# --------------------------------------------------------------------------
# Differential: carry_pia_forward in the PolicyEngine-US bridge
# --------------------------------------------------------------------------
#: The largest carried PIA the differential draws, in dollars a month.
#: Float error in a product near this size is about 3e-11 dollars, under
#: the 1e-10-dollar guard of the dime floor, so the float chain and the
#: bridge's Decimal chain floor alike. Well past this size they can part.
CARRIED_CAP = 100_000.0

#: Statutory COLAs are rounded to a tenth of a percent and never fall
#: below zero, so the differential draws rates on that grid.
statutory_rates = st.integers(min_value=0, max_value=150).map(
    lambda tenths: tenths / 1000
)


@LIGHT
@given(
    cents=st.integers(min_value=0, max_value=800_000),
    path=cola_paths(rates=statutory_rates, min_years=1, max_years=30),
)
def test_benefit_from_pia_agrees_with_carry_pia_forward(cents, path):
    """Both carry a PIA through statutory COLAs with a dime floor each step.

    They overlap where ``payment_year`` follows ``eligibility_year`` (the
    bridge refuses an empty range) and every rate is zero or more (the
    bridge refuses a negative one). The draw stays on the statutory
    tenth-of-a-percent grid, where the bridge's quantizing of a rate to a
    millionth changes nothing, and under CARRIED_CAP. At a claim factor
    of 1 the benefit is the carried PIA floored to the dollar; at 10 it
    is ten times the carried PIA, which shows every dime of the chain.
    """
    from populace_dynamics.bridge.policyengine_us import carry_pia_forward

    pia = cents / 100
    # Keep the carried PIA where float error stays under the floors'
    # 1e-9 guard (see CARRIED_CAP).
    assume(
        pia
        * cola_factor(
            path["cola_rates"], path["eligibility_year"], path["payment_year"]
        )
        <= CARRIED_CAP
    )
    carried, steps = carry_pia_forward(
        pia,
        path["cola_rates"],
        first_determination_year=path["eligibility_year"],
        last_determination_year=path["payment_year"] - 1,
    )
    assert len(steps) == path["payment_year"] - path["eligibility_year"]
    at_one = benefit_from_pia(
        pia, **path, claim_factor=1.0, statutory_rounding=True
    )
    assert at_one == math.floor(carried)
    at_ten = benefit_from_pia(
        pia, **path, claim_factor=10.0, statutory_rounding=True
    )
    assert at_ten == round(carried * 10)
