"""Differential checks for OP1's direct stream addresses, design §5.4."""

import warnings
from decimal import Decimal
from itertools import product

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.engine.rng import (
    MODULE_ORDER,
    ProjectionRNGRegistry,
)
from populace_dynamics.open_population.exits import EMIGRATION_STREAM_TAG
from populace_dynamics.open_population.streams import DirectRNGStreams


def _assert_sequences_equal(expected, actual):
    """Compare seed identity as well as generated state (design §2.1)."""
    assert actual.entropy == expected.entropy
    assert actual.spawn_key == expected.spawn_key
    assert actual.pool_size == expected.pool_size
    assert np.array_equal(actual.generate_state(8), expected.generate_state(8))


def _assert_generators_equal(expected, actual):
    """Compare generator seeds and first four draws (design §5.4)."""
    _assert_sequences_equal(
        expected.bit_generator.seed_seq, actual.bit_generator.seed_seq
    )
    assert np.array_equal(actual.random(4), expected.random(4))


@pytest.mark.parametrize(
    ("draw_index", "n_periods"), tuple(product(range(3), (0, 1, 7, 75, 86)))
)
def test_every_stream_method_matches_registry_on_exhaustive_grid(
    draw_index, n_periods
):
    registry = ProjectionRNGRegistry(draw_index, n_periods)
    direct = DirectRNGStreams(draw_index, n_periods)
    assert direct.draw_seed == registry.draw_seed
    periods = sorted(
        period
        for period in {0, 1, n_periods // 2, n_periods}
        if period <= n_periods
    )
    for period, module in product(periods, MODULE_ORDER):
        _assert_sequences_equal(
            registry.seed_sequence(period, module),
            direct.seed_sequence(period, module),
        )
        _assert_generators_equal(
            registry.generator(period, module),
            direct.generator(period, module),
        )
        for ordinal in (0, 1, 12345):
            for method in ("child_generator", "person_generator"):
                _assert_generators_equal(
                    getattr(registry, method)(period, module, ordinal),
                    getattr(direct, method)(period, module, ordinal),
                )
        for tag in (0, 7, 0x4D36, EMIGRATION_STREAM_TAG):
            _assert_generators_equal(
                registry.tagged_generator(period, module, tag),
                direct.tagged_generator(period, module, tag),
            )
            for child_index in (0, 3, 99):
                _assert_generators_equal(
                    registry.tagged_child_generator(
                        period, module, tag, child_index
                    ),
                    direct.tagged_child_generator(
                        period, module, tag, child_index
                    ),
                )


@settings(max_examples=24, deadline=None)
@given(
    draw_index=st.integers(0, 2**16),
    period=st.integers(0, 86),
    module=st.sampled_from(MODULE_ORDER),
    ordinal=st.integers(0, 2**16),
    child_index=st.integers(0, 128),
    tag=st.integers(0, 2**24),
)
def test_stream_identity_at_generated_addresses(
    draw_index, period, module, ordinal, child_index, tag
):
    registry = ProjectionRNGRegistry(draw_index, 86)
    direct = DirectRNGStreams(draw_index, 86)
    _assert_sequences_equal(
        registry.seed_sequence(period, module),
        direct.seed_sequence(period, module),
    )
    for method, tail in (
        ("generator", ()),
        ("child_generator", (child_index,)),
        ("person_generator", (ordinal,)),
        ("tagged_generator", (tag,)),
        ("tagged_child_generator", (tag, child_index)),
    ):
        _assert_generators_equal(
            getattr(registry, method)(period, module, *tail),
            getattr(direct, method)(period, module, *tail),
        )


@pytest.mark.parametrize(
    ("draw_index", "n_periods"), ((-1, 7), (0, -1), (-1, -1))
)
def test_constructor_refusals_match_registry(draw_index, n_periods):
    with pytest.raises(ValueError) as expected:
        ProjectionRNGRegistry(draw_index, n_periods)
    with pytest.raises(type(expected.value), match=str(expected.value)):
        DirectRNGStreams(draw_index, n_periods)


@pytest.mark.parametrize(
    ("method", "args"),
    (
        ("seed_sequence", (-1, MODULE_ORDER[0])),
        ("seed_sequence", (8, MODULE_ORDER[0])),
        ("generator", (-1, MODULE_ORDER[0])),
        ("generator", (8, MODULE_ORDER[0])),
        ("child_generator", (1, MODULE_ORDER[0], -1)),
        ("child_generator", (8, MODULE_ORDER[0], 0)),
        ("person_generator", (1, MODULE_ORDER[0], -1)),
        ("person_generator", (-1, MODULE_ORDER[0], 0)),
        ("tagged_generator", (0, MODULE_ORDER[0], -1)),
        ("tagged_generator", (1, MODULE_ORDER[0], -1)),
        ("tagged_generator", (-1, MODULE_ORDER[0], 0)),
        ("tagged_generator", (8, MODULE_ORDER[0], 0)),
        ("tagged_child_generator", (0, MODULE_ORDER[0], -1, 0)),
        ("tagged_child_generator", (0, MODULE_ORDER[0], 0, -1)),
        ("tagged_child_generator", (1, MODULE_ORDER[0], -1, 0)),
        ("tagged_child_generator", (1, MODULE_ORDER[0], 0, -1)),
        ("tagged_child_generator", (-1, MODULE_ORDER[0], 0, 0)),
        ("tagged_child_generator", (8, MODULE_ORDER[0], 0, 0)),
        ("seed_sequence", (1, "unknown")),
        ("generator", (1, "unknown")),
        ("child_generator", (1, "unknown", 0)),
        ("person_generator", (1, "unknown", 0)),
        ("tagged_generator", (1, "unknown", 0)),
        ("tagged_child_generator", (1, "unknown", 0, 0)),
    ),
)
def test_invalid_address_refusals_match_registry(method, args):
    registry = ProjectionRNGRegistry(0, 7)
    direct = DirectRNGStreams(0, 7)
    with pytest.raises(ValueError) as expected:
        getattr(registry, method)(*args)
    with pytest.raises(type(expected.value)) as actual:
        getattr(direct, method)(*args)
    assert str(actual.value) == str(expected.value)


def _outcome(streams, method, args, compare):
    """Return a method's refusal, or its value through ``compare``."""
    try:
        value = getattr(streams, method)(*args)
    except Exception as error:  # noqa: BLE001 - refusals are compared
        return ("refused", type(error), str(error))
    return ("returned", compare(value))


def _sequence_identity(sequence):
    """Summarize a seed sequence by identity and state (design §2.1)."""
    return (
        tuple(np.atleast_1d(sequence.entropy).tolist()),
        tuple(int(key) for key in sequence.spawn_key),
        sequence.pool_size,
        tuple(sequence.generate_state(4).tolist()),
    )


def _generator_identity(generator):
    """Summarize a generator by its seed and first draws (design §5.4)."""
    return (
        _sequence_identity(generator.bit_generator.seed_seq),
        tuple(generator.random(2).tolist()),
    )


# Periods, horizons, tails and draws that no engine caller passes; each
# probes one step of the registry's refusal order (design §2.1).
_MALFORMED_PERIODS = (
    0,
    1,
    7,
    -1,
    8,
    0.0,
    1.5,
    7.0,
    np.int64(2),
    True,
    None,
    np.float64(1.0),
    np.float32(1.5),
    np.bool_(True),
    Decimal(1),
    Decimal("1.5"),
    np.array(1),
    np.array([1]),
)
_MALFORMED_HORIZONS = (
    7,
    0,
    7.0,
    7.5,
    np.float64(7.0),
    np.int64(7),
    2**63 - 1,
    2**64,
    np.int64(2**63 - 1),
    np.uint64(2**64 - 1),
)
_MALFORMED_TAILS = (
    0,
    3,
    -1,
    1.5,
    np.int64(2),
    np.bool_(True),
    np.array(1),
    np.int64(2**63 - 1),
    np.uint64(2**64 - 1),
)
_MALFORMED_DRAWS = (0.0, 1.5, Decimal(1), np.float64(2.0), np.int64(3))
_MALFORMED_MODULES = (MODULE_ORDER[0], MODULE_ORDER[-1].value, "unknown")
_TAIL_LENGTHS = {
    "seed_sequence": 0,
    "generator": 0,
    "child_generator": 1,
    "person_generator": 1,
    "tagged_generator": 1,
    "tagged_child_generator": 2,
}


def _compare_for(method):
    """Pick the identity summary for a method's return type."""
    if method == "seed_sequence":
        return _sequence_identity
    return _generator_identity


def _assert_outcomes_match(draw_index, n_periods, method, args):
    """Both classes return one stream or raise one refusal (design §2.1)."""
    compare = _compare_for(method)
    # NumPy integer tails wrap on ``+ 1`` in both classes alike.
    with warnings.catch_warnings(), np.errstate(over="ignore"):
        warnings.simplefilter("ignore")
        expected = _outcome(
            ProjectionRNGRegistry(draw_index, n_periods), method, args, compare
        )
        actual = _outcome(
            DirectRNGStreams(draw_index, n_periods), method, args, compare
        )
    assert actual == expected, (draw_index, n_periods, method, args)


@pytest.mark.parametrize("n_periods", _MALFORMED_HORIZONS)
@pytest.mark.parametrize("method", tuple(_TAIL_LENGTHS))
def test_combined_and_malformed_refusals_match_registry(method, n_periods):
    """Refusal order, type and message match the registry (design §2.1).

    Every combination of period, module and tail is tried, including a bad
    module with a bad period, a negative tag or child with a bad module,
    period-zero tagged calls that never resolve the module, non-integer and
    array periods, tags and children, horizons whose spawn count overflows
    ``ssize_t`` or wraps negative, and NumPy integer children that wrap.  At
    each address both classes return the same stream or raise the same
    exception with the same message.
    """
    tails = product(_MALFORMED_TAILS, repeat=_TAIL_LENGTHS[method])
    for tail, period, module in product(
        tuple(tails), _MALFORMED_PERIODS, _MALFORMED_MODULES
    ):
        _assert_outcomes_match(0, n_periods, method, (period, module, *tail))


@pytest.mark.parametrize("method", tuple(_TAIL_LENGTHS))
def test_non_integer_draw_refusals_match_registry(method):
    """A malformed draw is refused at the registry's step (design §2.1).

    The registry builds its root seed before spawning or indexing, so a
    non-integer draw must fail there even when the horizon or period is also
    malformed.
    """
    tails = product((0, 1.5), repeat=_TAIL_LENGTHS[method])
    for draw_index, n_periods, tail, period, module in product(
        _MALFORMED_DRAWS,
        (7, 7.5, 2**64),
        tuple(tails),
        (0, 1, 1.5, None),
        _MALFORMED_MODULES[::2],
    ):
        _assert_outcomes_match(
            draw_index, n_periods, method, (period, module, *tail)
        )


@settings(max_examples=80, deadline=None)
@given(
    draw_index=st.one_of(
        st.integers(0, 2**16), st.sampled_from(_MALFORMED_DRAWS)
    ),
    n_periods=st.one_of(
        st.integers(0, 12), st.sampled_from(_MALFORMED_HORIZONS)
    ),
    period=st.one_of(
        st.integers(-2, 14),
        st.floats(-1, 14, allow_nan=False),
        st.none(),
        st.booleans(),
        st.sampled_from(_MALFORMED_PERIODS),
    ),
    module=st.sampled_from((*MODULE_ORDER, "unknown")),
    tail=st.lists(
        st.one_of(
            st.integers(-2, 2**16),
            st.floats(0, 4, allow_nan=False),
            st.sampled_from(_MALFORMED_TAILS),
        ),
        min_size=2,
        max_size=2,
    ),
    method=st.sampled_from(tuple(_TAIL_LENGTHS)),
)
def test_generated_malformed_addresses_match_registry(
    draw_index, n_periods, period, module, tail, method
):
    """Hypothesis extends the refusal grids' address space (design §2.1)."""
    args = (period, module, *tail[: _TAIL_LENGTHS[method]])
    _assert_outcomes_match(draw_index, n_periods, method, args)
