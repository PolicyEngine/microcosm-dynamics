"""Sufficient, minimal normal planning counts across tolerance scales.

The threshold helpers' total contract, checked here:

* totality: for any argument values, each helper returns an ``int``
  count or raises ``ThresholdInputError``, ``UnreachableThreshold`` or
  ``UnrepresentableThreshold``, never ``None`` or another exception;
* sufficiency: the gate's achieved-count predicate passes at the count;
* strict minimality: it fails at one fewer, unless the count is 1;
* reachability agreement: a helper refuses only when no supported count
  passes that predicate, checked against brute force and an independent
  doubling search.
"""

import math
import sys
from decimal import Decimal
from fractions import Fraction

import numpy as np
import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from .test_s0_1_power import power

NAMED = (
    power.ThresholdInputError,
    power.UnreachableThreshold,
    power.UnrepresentableThreshold,
)
TOP = power.MAX_SUPPORTED_COUNT
DEFAULTS = {
    "deaths": {
        "group_share": 0.0,
        "delta": 0.0,
        "tolerance": power.SM3_TOLERANCE,
        "alpha": power.ALPHA,
        "criterion": power.POWER_CRITERION,
    },
    "persons": {
        "n_target_eff": math.inf,
        "delta": 0.0,
        "tolerance": power.ED2_TOLERANCE,
        "alpha": power.ALPHA,
        "criterion": power.POWER_CRITERION,
    },
}


def call(helper, **kwargs):
    if helper == "deaths":
        return power.min_effective_deaths_per_cell(**kwargs)
    return power.min_effective_n_per_cell(**kwargs)


def arguments(helper, **kwargs):
    """Every argument of an accepted call, as doubles."""
    args = {**DEFAULTS[helper], **kwargs}
    return {k: v if k == "m" else float(v) for k, v in args.items()}


def gate_se(helper, args, n):
    """The SE the gate uses at count ``n``, or None where undefined."""
    if helper == "deaths":
        se = math.sqrt((1 - args["group_share"]) / n)
    elif args["n_target_eff"] == math.inf:
        se = math.sqrt(args["share"] * (1 - args["share"]) / n)
    else:
        se = power.share_difference_se(args["share"], n, args["n_target_eff"])
    return se if 0 < se < math.inf else None


def equal_family_power(args, se):
    """Union bound over ``m`` equal cells: explicit lists up to 64 cells.

    Larger families use the closed form, whose bitwise agreement with the
    list form is checked by a property below.
    """
    m = args["m"]
    if m <= 64:
        return power.family_power_lower_bound(
            [args["delta"]] * m, [se] * m, args["tolerance"], args["alpha"]
        )
    z = power.bonferroni_z(m, args["alpha"])
    return power._equal_cells_power(m, args["delta"], se, args["tolerance"], z)


def gate_power(helper, args, n):
    """The gate's achieved-count predicate at ``n``; None if undefined."""
    se = gate_se(helper, args, n)
    return None if se is None else equal_family_power(args, se)


def passes(helper, args, n):
    value = gate_power(helper, args, n)
    return value is not None and value >= args["criterion"]


def assert_sufficient_and_minimal(helper, args, count):
    assert type(count) is int
    assert 1 <= count <= TOP
    assert passes(helper, args, count)
    if count > 1:
        below = gate_power(helper, args, count - 1)
        assert below is not None and below < args["criterion"]


def largest_defined_count(helper, args):
    """Defined counts form an initial segment; 0 if it is empty."""
    if gate_se(helper, args, 1) is None:
        return 0
    if gate_se(helper, args, TOP) is not None:
        return TOP
    lo, hi = 1, TOP
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if gate_se(helper, args, mid) is None:
            hi = mid
        else:
            lo = mid
    return lo


def target_alone_power(helper, args):
    """The predicate with the target's variance alone; None if undefined."""
    if helper == "deaths" or args["n_target_eff"] == math.inf:
        return None
    p = args["share"]
    variance = p * (1 - p) * (1.0 / args["n_target_eff"])
    if not 0 < variance < math.inf:
        return None
    return equal_family_power(args, math.sqrt(variance))


def reference_count(helper, args):
    """Independent search: doubling from one with no seed, then bisection.

    Returns the smallest passing supported count, or None when none
    passes. It shares only the gate predicate with the helpers.
    """
    top = largest_defined_count(helper, args)
    if top == 0:
        return None
    n, failing = 1, 0
    while not passes(helper, args, n):
        if n == top:
            return None
        failing, n = n, min(2 * n, top)
    while n - failing > 1:
        mid = (failing + n) // 2
        if passes(helper, args, mid):
            n = mid
        else:
            failing = mid
    return n


def outcome(helper, **kwargs):
    try:
        return call(helper, **kwargs)
    except NAMED as refusal:
        return refusal


def assert_agrees_with_reference(helper, args, result):
    expected = reference_count(helper, args)
    if expected is None:
        assert isinstance(
            result,
            (power.UnreachableThreshold, power.UnrepresentableThreshold),
        ), result
        if isinstance(result, power.UnreachableThreshold):
            plateau = target_alone_power(helper, args)
            assert plateau is not None and plateau < args["criterion"]
    else:
        assert result == expected


@pytest.mark.parametrize("helper", ["deaths", "persons"])
@settings(max_examples=60, deadline=None)
@example(m=1, exponent=-9, margin_exponent=0, fraction=0.5, sign=1)
@given(
    m=st.integers(1, 60),
    exponent=st.integers(-12, 1),
    margin_exponent=st.integers(-12, 0),
    fraction=st.floats(0.001, 0.999),
    sign=st.sampled_from([-1, 1]),
)
def test_threshold_sufficiency_and_minimality_across_scales(
    helper, m, exponent, margin_exponent, fraction, sign
):
    tolerance = 10.0**exponent
    delta = sign * tolerance * (1 - 10.0**margin_exponent)
    if helper == "deaths":
        count = power.min_effective_deaths_per_cell(
            m, group_share=fraction, delta=delta, tolerance=tolerance
        )
        variance = 1 - fraction
    else:
        count = power.min_effective_n_per_cell(
            m, share=fraction, delta=delta, tolerance=tolerance
        )
        variance = fraction * (1 - fraction)

    def achieved(n):
        return power.family_power_lower_bound(
            [delta] * m, [math.sqrt(variance / n)] * m, tolerance
        )

    assert achieved(count) >= power.POWER_CRITERION
    assert count == 1 or achieved(count - 1) < power.POWER_CRITERION


@pytest.mark.parametrize("helper", ["deaths", "persons"])
def test_review_minimized_near_boundary_threshold(helper):
    tolerance = (
        power.SM3_TOLERANCE if helper == "deaths" else power.ED2_TOLERANCE
    )
    delta = tolerance - 1e-9
    if helper == "deaths":
        count = power.min_effective_deaths_per_cell(1, delta=delta)
        variance = 1.0
    else:
        count = power.min_effective_n_per_cell(1, share=0.5, delta=delta)
        variance = 0.25
    assert (
        power.family_power_lower_bound(
            [delta], [math.sqrt(variance / count)], tolerance
        )
        >= power.POWER_CRITERION
    )
    assert (
        power.family_power_lower_bound(
            [delta], [math.sqrt(variance / (count - 1))], tolerance
        )
        < power.POWER_CRITERION
    )


def test_sufficiency_is_the_helpers_float_reciprocal_predicate():
    """At the near-boundary gap, the helper's predicate defines sufficiency.

    The predicate converts the count to the nearest double, then divides
    (``1.0 / n``). The archived probe formed ``1 / n`` from two integers,
    which rounds the exact quotient once; above ``2**53`` the two can
    differ in the last place, and the probe can then print a value just
    below the criterion. Any such shortfall comes from that reciprocal.
    """
    tolerance = power.SM3_TOLERANCE
    delta = tolerance - 1e-9
    count = power.min_effective_deaths_per_cell(1, delta=delta)

    def helper_predicate(n):
        return power.family_power_lower_bound(
            [delta], [math.sqrt(1.0 / n)], tolerance
        )

    def integer_reciprocal_probe(n):
        return power.family_power_lower_bound(
            [delta], [math.sqrt(1 / n)], tolerance
        )

    assert count > 2**53
    assert helper_predicate(count) >= power.POWER_CRITERION
    assert helper_predicate(count - 1) < power.POWER_CRITERION
    assert (
        integer_reciprocal_probe(count) >= power.POWER_CRITERION
        or 1 / count != 1.0 / count
    )


@settings(max_examples=60, deadline=None)
@given(
    m=st.integers(1, 40),
    fraction=st.floats(0.01, 0.99),
    tolerance=st.sampled_from([0.001, 0.02, 0.3, 2.0]),
    delta_fraction=st.floats(-0.99, 0.99),
    target=st.sampled_from([10.0, 1000.0, 1e8, 1e20]),
    criterion=st.sampled_from([0.5, 0.9, 0.99]),
    alpha=st.sampled_from([0.01, 0.05, 0.2]),
)
def test_finite_target_threshold_is_sufficient_minimal_or_unreachable(
    m, fraction, tolerance, delta_fraction, target, criterion, alpha
):
    delta = tolerance * delta_fraction

    def achieved(n):
        se = (
            math.sqrt(fraction * (1 - fraction) * (1.0 / target))
            if n is None
            else power.share_difference_se(fraction, n, target)
        )
        return power.family_power_lower_bound(
            [delta] * m, [se] * m, tolerance, alpha
        )

    try:
        count = power.min_effective_n_per_cell(
            m,
            share=fraction,
            n_target_eff=target,
            delta=delta,
            tolerance=tolerance,
            criterion=criterion,
            alpha=alpha,
        )
    except power.UnreachableThreshold:
        assert achieved(None) < criterion
        assert achieved(TOP) < criterion
        return
    assert achieved(count) >= criterion
    assert count == 1 or achieved(count - 1) < criterion


@pytest.mark.parametrize("helper", ["deaths", "persons"])
@settings(max_examples=30, deadline=None)
@given(
    invalid=st.sampled_from(
        [
            {"m": 0},
            {"m": True},
            {"m": 1.5},
            {"tolerance": 0.0},
            {"m": 10**18},
            {"tolerance": math.inf},
            {"tolerance": math.nan},
            {"delta": math.inf},
            {"delta": math.nan},
            {"delta": 1.0},
            {"criterion": 0.0},
            {"criterion": 1.0},
            {"alpha": 0.0},
            {"alpha": 1.0},
        ]
    )
)
def test_threshold_outside_domain_never_returns_a_count(helper, invalid):
    kwargs = {"m": 1, "tolerance": 0.1, **invalid}
    with pytest.raises(
        (power.ThresholdInputError, power.UnrepresentableThreshold)
    ):
        if helper == "deaths":
            power.min_effective_deaths_per_cell(**kwargs)
        else:
            power.min_effective_n_per_cell(share=0.5, **kwargs)


@pytest.mark.parametrize("helper", ["deaths", "persons"])
@pytest.mark.parametrize("tolerance", [5e-324, 1e-200])
def test_unrepresentable_threshold_has_named_refusal(helper, tolerance):
    with pytest.raises(power.UnrepresentableThreshold):
        if helper == "deaths":
            power.min_effective_deaths_per_cell(1, tolerance=tolerance)
        else:
            power.min_effective_n_per_cell(1, share=0.5, tolerance=tolerance)


@pytest.mark.parametrize("helper", ["deaths", "persons"])
@settings(max_examples=30, deadline=None)
@example(exponent=-155, fraction=0.5)
@given(exponent=st.integers(-300, -155), fraction=st.floats(0.01, 0.99))
def test_unrepresentable_threshold_refusal_across_scales(
    helper, exponent, fraction
):
    with pytest.raises(power.UnrepresentableThreshold):
        if helper == "deaths":
            power.min_effective_deaths_per_cell(
                1, group_share=fraction, tolerance=10.0**exponent
            )
        else:
            power.min_effective_n_per_cell(
                1, share=fraction, tolerance=10.0**exponent
            )


# --------------------------------------------------------------------------
# Review round 4: finite-target reachability and numerical endpoints
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "tolerance, witness",
    [(1.0, 3.248677503029869), (power.ED2_TOLERANCE, 8121.693757574674)],
)
def test_review_finite_target_plateau_and_adjacent_floats(tolerance, witness):
    """The review's witness, its neighbours, and the first refusal below.

    A larger target n means less target noise. Round 3's squared-SE
    shortcut refused the witness and the float below it, although a finite
    count passes the predicate. Two floats below the witness, the target's
    variance alone fails the predicate, so no count passes.
    """
    below = math.nextafter(witness, 0)
    first_unreachable = math.nextafter(below, 0)
    above = math.nextafter(witness, math.inf)
    for target in (below, witness, above):
        args = arguments(
            "persons",
            m=1,
            share=0.5,
            tolerance=tolerance,
            n_target_eff=target,
        )
        count = power.min_effective_n_per_cell(
            1, share=0.5, tolerance=tolerance, n_target_eff=target
        )
        assert count > 2**53
        assert_sufficient_and_minimal("persons", args, count)
        assert count == reference_count("persons", args)
    with pytest.raises(power.UnreachableThreshold):
        power.min_effective_n_per_cell(
            1, share=0.5, tolerance=tolerance, n_target_eff=first_unreachable
        )
    args = arguments(
        "persons",
        m=1,
        share=0.5,
        tolerance=tolerance,
        n_target_eff=first_unreachable,
    )
    assert reference_count("persons", args) is None
    assert gate_power("persons", args, TOP) < args["criterion"]


def test_review_minimized_finite_target_witness_reaches_on_the_plateau():
    target = 3.248677503029869
    count = power.min_effective_n_per_cell(
        1, share=0.5, tolerance=1, n_target_eff=target
    )
    reach = power.family_power_lower_bound(
        [0], [power.share_difference_se(0.5, 10**17, target)], 1
    )
    short = power.family_power_lower_bound(
        [0], [power.share_difference_se(0.5, 10**16, target)], 1
    )
    assert reach >= power.POWER_CRITERION > short
    assert 10**16 < count <= 10**17
    # From the returned count on, 1.0 / n no longer changes the variance.
    assert 1.0 / count + 1.0 / target == 1.0 / target
    assert 1.0 / (count - 1) + 1.0 / target != 1.0 / target


@pytest.mark.parametrize("helper", ["deaths", "persons"])
def test_review_huge_tolerance_needs_one_observation(helper):
    kwargs = {"share": 0.5} if helper == "persons" else {}
    assert call(helper, m=1, tolerance=1e155, **kwargs) == 1
    args = arguments(helper, m=1, tolerance=1e155, **kwargs)
    assert gate_power(helper, args, 1) == 1.0


@pytest.mark.parametrize("helper", ["deaths", "persons"])
@pytest.mark.parametrize(
    "endpoint",
    [
        {"m": 1, "alpha": math.nextafter(1.0, 0.0)},
        {"m": 10**400},
    ],
    ids=["critical-value-rounds-to-zero", "family-size-beyond-double"],
)
def test_review_numerical_endpoints_are_unrepresentable(helper, endpoint):
    kwargs = {"share": 0.5} if helper == "persons" else {}
    with pytest.raises(power.UnrepresentableThreshold):
        call(helper, **endpoint, **kwargs)


def test_review_underflowing_se_is_unrepresentable():
    with pytest.raises(power.UnrepresentableThreshold):
        power.min_effective_n_per_cell(1, share=5e-324, tolerance=6e-162)


def test_critical_value_rounding_to_zero_is_refused_before_division():
    assert power.bonferroni_z(1, math.nextafter(1.0, 0.0)) == 0.0
    with pytest.raises(power.UnrepresentableThreshold):
        power._critical_se(1, 0.0, 0.1, math.nextafter(1.0, 0.0), 0.9)


@pytest.mark.parametrize(
    "tolerance, reachable", [(1e-161, True), (5e-162, False)]
)
def test_deaths_threshold_where_variances_underflow(tolerance, reachable):
    """Counts near the top of the double range, where ``v / n`` underflows.

    With ``group_share = 1 - 2**-53`` the defined counts end below
    ``MAX_SUPPORTED_COUNT``. A count inside that segment is returned when
    it passes; otherwise the refusal is ``UnrepresentableThreshold``.
    """
    share = 1 - 2**-53
    args = arguments("deaths", m=1, group_share=share, tolerance=tolerance)
    top = largest_defined_count("deaths", args)
    assert top < TOP
    result = outcome("deaths", m=1, group_share=share, tolerance=tolerance)
    if reachable:
        assert result <= top
        assert_sufficient_and_minimal("deaths", args, result)
    else:
        assert isinstance(result, power.UnrepresentableThreshold)
        assert gate_power("deaths", args, top) < args["criterion"]
    assert_agrees_with_reference("deaths", args, result)


@pytest.mark.parametrize(
    "call_kwargs, refusal",
    [
        ({"n_target_eff": 5e-324}, power.UnrepresentableThreshold),
        ({"n_target_eff": math.nan}, power.ThresholdInputError),
        ({"n_target_eff": 0.0}, power.ThresholdInputError),
        ({"n_target_eff": -math.inf}, power.ThresholdInputError),
        ({"n_target_eff": 10**400}, power.UnrepresentableThreshold),
        ({"tolerance": 10**400}, power.UnrepresentableThreshold),
        ({"tolerance": Fraction(1, 10**400)}, power.UnrepresentableThreshold),
        ({"delta": 10**400}, power.ThresholdInputError),
        ({"alpha": None}, power.ThresholdInputError),
        ({"alpha": "0.05"}, power.ThresholdInputError),
        ({"alpha": 1j}, power.ThresholdInputError),
        ({"alpha": Decimal("0.05")}, power.ThresholdInputError),
        ({"criterion": True}, power.ThresholdInputError),
        ({"criterion": 5e-324}, None),
        ({"m": np.int64(3)}, None),
        ({"m": 2**53 - 1}, power.UnrepresentableThreshold),
        ({"share": np.float64(0.3)}, None),
        ({"share": 1.0}, power.ThresholdInputError),
    ],
)
def test_persons_threshold_argument_endpoints(call_kwargs, refusal):
    kwargs = {"m": 1, "share": 0.5, **call_kwargs}
    result = outcome("persons", **kwargs)
    if refusal is None:
        args = arguments("persons", **kwargs)
        args["m"] = int(args["m"])
        assert_sufficient_and_minimal("persons", args, result)
    else:
        assert type(result) is refusal


# --------------------------------------------------------------------------
# Properties of the total contract
# --------------------------------------------------------------------------
EDGE_REALS = [
    0.0,
    -0.0,
    5e-324,
    -5e-324,
    sys.float_info.min,
    1e-300,
    1e-155,
    0.5,
    math.nextafter(1.0, 0.0),
    1.0,
    math.nextafter(1.0, 2.0),
    1e155,
    sys.float_info.max,
    math.inf,
    -math.inf,
    math.nan,
    2**53,
    10**400,
    -(10**400),
    Fraction(1, 3),
    Fraction(1, 10**400),
    np.float64(0.25),
    np.float32(0.25),
    np.int64(3),
]
ODD_VALUES = [None, "0.1", 1j, True, False, Decimal("0.1"), [0.1]]
ANY_VALUE = st.one_of(
    st.floats(),
    st.integers(-(10**400), 10**400),
    st.sampled_from(EDGE_REALS),
    st.sampled_from(ODD_VALUES),
)
ANY_FAMILY_SIZE = st.one_of(
    st.integers(-3, 70),
    st.integers(2**40, 2**60),
    st.integers(10**300, 10**400),
    st.sampled_from([2**53 - 1, 2**53, np.int64(16), 1.0, 2.5, None, "3"]),
)


def assert_total(helper, kwargs):
    """A count that passes and is minimal, or a named refusal."""
    try:
        count = call(helper, **kwargs)
    except NAMED as refusal:
        return refusal
    args = arguments(helper, **kwargs)
    args["m"] = int(args["m"])
    assert_sufficient_and_minimal(helper, args, count)
    return count


@pytest.mark.parametrize("helper", ["deaths", "persons"])
@settings(max_examples=150, deadline=None)
@given(
    m=ANY_FAMILY_SIZE,
    share=ANY_VALUE,
    n_target_eff=ANY_VALUE,
    delta=ANY_VALUE,
    tolerance=ANY_VALUE,
    alpha=ANY_VALUE,
    criterion=ANY_VALUE,
)
def test_threshold_helpers_are_total_for_arbitrary_arguments(
    helper, m, share, n_target_eff, delta, tolerance, alpha, criterion
):
    kwargs = {
        "m": m,
        "delta": delta,
        "tolerance": tolerance,
        "alpha": alpha,
        "criterion": criterion,
    }
    if helper == "deaths":
        kwargs["group_share"] = share
    else:
        kwargs.update(share=share, n_target_eff=n_target_eff)
    assert_total(helper, kwargs)


@pytest.mark.parametrize("helper", ["deaths", "persons"])
@settings(max_examples=200, deadline=None)
@example(
    m=1,
    share=0.5,
    n_target_eff=3.248677503029869,
    delta_fraction=0.0,
    tolerance=1.0,
    alpha=0.05,
    criterion=0.9,
)
@example(
    m=1,
    share=5e-324,
    n_target_eff=math.inf,
    delta_fraction=0.0,
    tolerance=6e-162,
    alpha=0.05,
    criterion=0.9,
)
@example(
    m=1,
    share=0.5,
    n_target_eff=math.inf,
    delta_fraction=0.0,
    tolerance=1e155,
    alpha=math.nextafter(1.0, 0.0),
    criterion=0.9,
)
@given(
    m=st.one_of(st.integers(1, 64), st.integers(65, 2**60)),
    share=st.floats(0, 1),
    n_target_eff=st.one_of(
        st.just(math.inf), st.floats(0, sys.float_info.max)
    ),
    delta_fraction=st.floats(-1, 1),
    tolerance=st.floats(5e-324, sys.float_info.max),
    alpha=st.floats(0, 1),
    criterion=st.floats(0, 1),
)
def test_threshold_helpers_are_total_near_the_domain(
    helper, m, share, n_target_eff, delta_fraction, tolerance, alpha, criterion
):
    kwargs = {
        "m": m,
        "delta": delta_fraction * tolerance,
        "tolerance": tolerance,
        "alpha": alpha,
        "criterion": criterion,
    }
    if helper == "deaths":
        kwargs["group_share"] = share
    else:
        kwargs.update(share=share, n_target_eff=n_target_eff)
    result = assert_total(helper, kwargs)
    if isinstance(result, power.ThresholdInputError):
        return
    args = arguments(helper, **kwargs)
    if isinstance(result, power.UnreachableThreshold):
        plateau = target_alone_power(helper, args)
        assert plateau is not None and plateau < args["criterion"]
        top = largest_defined_count(helper, args)
        assert top == 0 or not passes(helper, args, top)


@st.composite
def small_family(draw):
    return {
        "m": draw(st.integers(1, 6)),
        "alpha": draw(st.sampled_from([0.01, 0.05, 0.2, 0.6])),
        "criterion": draw(st.sampled_from([0.3, 0.5, 0.9, 0.99])),
        "delta_fraction": draw(st.floats(-0.99, 0.99)),
    }


@settings(max_examples=40, deadline=None)
@given(
    family=small_family(),
    share=st.floats(0.01, 0.99),
    target_exponent=st.floats(-15, -13),
    scale=st.floats(1.0, 8.0),
)
def test_finite_target_reachability_agrees_with_brute_force(
    family, share, target_exponent, scale
):
    """Enumerate every count where the predicate can still change.

    For ``n_target_eff`` below ``1e-13``, ``1.0 / n + 1 / n_target_eff``
    equals ``1 / n_target_eff`` from a small count onwards, so every larger
    count has the same variance and predicate. Brute force over the counts
    up to that plateau therefore covers every supported count.
    """
    target = 10.0**target_exponent
    inverse = 1.0 / target
    tolerance = math.sqrt(share * (1 - share) * inverse) * scale
    args = arguments(
        "persons",
        m=family["m"],
        share=share,
        n_target_eff=target,
        delta=family["delta_fraction"] * tolerance,
        tolerance=tolerance,
        alpha=family["alpha"],
        criterion=family["criterion"],
    )
    plateau = next(n for n in range(1, 4097) if 1.0 / n + inverse == inverse)
    passing = [n for n in range(1, plateau + 1) if passes("persons", args, n)]
    result = outcome(
        "persons",
        m=family["m"],
        share=share,
        n_target_eff=target,
        delta=args["delta"],
        tolerance=tolerance,
        alpha=family["alpha"],
        criterion=family["criterion"],
    )
    if passing:
        assert result == passing[0]
    else:
        assert isinstance(result, power.UnreachableThreshold)
    assert_agrees_with_reference("persons", args, result)


@pytest.mark.parametrize("helper", ["deaths", "persons"])
@settings(max_examples=40, deadline=None)
@given(
    family=small_family(),
    share=st.floats(0.0, 0.99),
    margin=st.floats(0.5, 12.0),
)
def test_small_infinite_target_counts_agree_with_brute_force(
    helper, family, share, margin
):
    """Every count below the returned one fails, not only its predecessor."""
    share = max(share, 0.01) if helper == "persons" else share
    variance = 1 - share if helper == "deaths" else share * (1 - share)
    z = power.bonferroni_z(family["m"], family["alpha"])
    tolerance = math.sqrt(variance) * (z + margin)
    kwargs = {
        "m": family["m"],
        "delta": family["delta_fraction"] * tolerance,
        "tolerance": tolerance,
        "alpha": family["alpha"],
        "criterion": family["criterion"],
    }
    kwargs.update(
        {"group_share": share} if helper == "deaths" else {"share": share}
    )
    args = arguments(helper, **kwargs)
    count = call(helper, **kwargs)
    if count <= 5000:
        assert all(not passes(helper, args, n) for n in range(1, count))
    assert_sufficient_and_minimal(helper, args, count)
    assert_agrees_with_reference(helper, args, count)


@settings(max_examples=40, deadline=None)
@given(
    family=small_family(),
    multiple=st.integers(1, 64),
    scale=st.floats(0.01, 6.0),
)
def test_underflow_region_agrees_with_brute_force(family, multiple, scale):
    """Enumerate every defined count for a share that underflows quickly.

    With ``share = k * 5e-324``, ``share * (1 - share) / n`` underflows to
    zero beyond about ``2k``, so the defined counts are few. A count is
    returned when one passes; otherwise ``UnrepresentableThreshold``.
    """
    share = multiple * 5e-324
    tolerance = math.sqrt(share * (1 - share)) * scale
    args = arguments(
        "persons",
        m=family["m"],
        share=share,
        delta=family["delta_fraction"] * tolerance,
        tolerance=tolerance,
        alpha=family["alpha"],
        criterion=family["criterion"],
    )
    top = largest_defined_count("persons", args)
    assert 1 <= top <= 4 * multiple
    passing = [n for n in range(1, top + 1) if passes("persons", args, n)]
    result = outcome(
        "persons",
        m=family["m"],
        share=share,
        delta=args["delta"],
        tolerance=tolerance,
        alpha=family["alpha"],
        criterion=family["criterion"],
    )
    if passing:
        assert result == passing[0]
    else:
        assert isinstance(result, power.UnrepresentableThreshold)
    assert_agrees_with_reference("persons", args, result)


@pytest.mark.parametrize("helper", ["deaths", "persons"])
@settings(max_examples=80, deadline=None)
@given(
    family=small_family(),
    share=st.floats(0.0, 0.99),
    n_target_eff=st.one_of(st.just(math.inf), st.floats(1e-3, 1e22)),
    tolerance=st.floats(1e-12, 1e3),
)
def test_threshold_matches_an_independent_doubling_search(
    helper, family, share, n_target_eff, tolerance
):
    kwargs = {
        "m": family["m"],
        "delta": family["delta_fraction"] * tolerance,
        "tolerance": tolerance,
        "alpha": family["alpha"],
        "criterion": family["criterion"],
    }
    if helper == "deaths":
        kwargs["group_share"] = share
    else:
        kwargs.update(share=max(share, 0.01), n_target_eff=n_target_eff)
    args = arguments(helper, **kwargs)
    result = outcome(helper, **kwargs)
    if isinstance(result, int):
        assert_sufficient_and_minimal(helper, args, result)
    assert_agrees_with_reference(helper, args, result)


@pytest.mark.parametrize("helper", ["deaths", "persons"])
@settings(max_examples=60, deadline=None)
@given(
    family=small_family(),
    share=st.floats(0.01, 0.99),
    n_target_eff=st.one_of(st.just(math.inf), st.floats(1e-3, 1e22)),
    tolerance=st.floats(1e-12, 1e3),
    counts=st.lists(st.integers(1, TOP), min_size=2, max_size=2),
)
def test_gate_predicate_is_nondecreasing_in_the_count(
    helper, family, share, n_target_eff, tolerance, counts
):
    """The search's premise, including floating-point plateaus."""
    args = arguments(
        helper,
        m=family["m"],
        delta=family["delta_fraction"] * tolerance,
        tolerance=tolerance,
        alpha=family["alpha"],
        criterion=family["criterion"],
        **(
            {"group_share": share}
            if helper == "deaths"
            else {"share": share, "n_target_eff": n_target_eff}
        ),
    )
    small, large = sorted(counts)
    low = gate_power(helper, args, small)
    high = gate_power(helper, args, large)
    if low is not None and high is not None:
        assert low <= high
    if low is None:
        assert high is None


@settings(max_examples=60, deadline=None)
@given(
    m=st.integers(1, 300),
    delta_fraction=st.floats(-0.999, 0.999),
    se=st.floats(1e-6, 10.0),
    tolerance=st.floats(1e-3, 3.0),
    alpha=st.floats(0.001, 0.5),
)
def test_equal_cells_closed_form_matches_the_list_union_bound(
    m, delta_fraction, se, tolerance, alpha
):
    delta = delta_fraction * tolerance
    z = power.bonferroni_z(m, alpha)
    assert power._equal_cells_power(
        m, delta, se, tolerance, z
    ) == power.family_power_lower_bound(
        [delta] * m, [se] * m, tolerance, alpha
    )
