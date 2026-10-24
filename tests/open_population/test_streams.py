"""Differential checks for OP1's direct stream addresses, design §5.4."""

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
