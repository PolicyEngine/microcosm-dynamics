"""Direct construction of OP1 streams under design §§2.1 and 5.4.

The sealed registry builds the spawn tree at ``engine/rng.py:61–77`` and
extends its keys at ``:85–156``. Constructing those same keys directly keeps
OP1's draws identical without work proportional to the projection horizon.
The sealed loop continues to use its own registry.
"""

from __future__ import annotations

import operator
import sys
from dataclasses import dataclass

import numpy as np

from populace_dynamics.engine.rng import (
    _MODULE_INDEX,
    DRAW_SEED_BASE,
    GATE_M6_TAG,
    ProjectionModule,
)
from populace_dynamics.engine.rng import (
    MODULE_ORDER as MODULE_ORDER,
)


def _spawned_length(count: object) -> int:
    """Return the length of ``SeedSequence.spawn(count)``'s list (§2.1).

    The registry spawns ``n_periods + 1`` period children and
    ``child_index + 1`` tagged children (``engine/rng.py:67``, ``:144``).
    ``spawn`` refuses a negative count, then iterates a range whose bound
    must convert to a C ``ssize_t``. For every built-in or NumPy count that
    ``x + 1`` can produce, the same two steps here raise the same exception
    and message, without building the children.
    """
    if count < 0:
        raise ValueError("n_children must be non-negative")
    return len(range(count))


def _spawned_position(length: int, index: object) -> int:
    """Return the spawned child at ``index``, as the list lookup does (§2.1).

    The registry indexes its list of spawned children (``engine/rng.py:67``,
    ``:144``), and the child's spawn key holds the Python ``int`` position.
    Indexing an empty list raises CPython's own ``TypeError`` for a
    non-index type and its own ``IndexError`` for an index too large for
    ``ssize_t``; an index that fits is then checked against ``length``,
    which a NumPy integer count that wrapped to zero can leave empty.
    """
    if type(index) is not int or not (
        -sys.maxsize - 1 <= index <= sys.maxsize
    ):
        try:
            [][index]
        except IndexError:
            position = operator.index(index)
            if not -sys.maxsize - 1 <= position <= sys.maxsize:
                raise
        else:  # pragma: no cover - the period and child checks refuse slices
            raise TypeError(f"unexpected list index {index!r}")
    else:
        position = index
    # A user-defined index can pass the period or child check and still
    # convert to a negative position; the list lookup wraps it.
    if position < 0:
        position += length
    if not 0 <= position < length:
        raise IndexError("list index out of range")
    return position


@dataclass(frozen=True)
class DirectRNGStreams:
    """Construct the registry's stream addresses directly (design §2.1)."""

    draw_index: int
    n_periods: int

    def __post_init__(self) -> None:
        if self.draw_index < 0:
            raise ValueError("draw_index must be non-negative")
        if self.n_periods < 0:
            raise ValueError("n_periods must be non-negative")

    @property
    def draw_seed(self) -> int:
        """Use the inherited ensemble root seed (design §2.1)."""
        return DRAW_SEED_BASE + self.draw_index

    def _root_for(self, seed: object) -> np.random.SeedSequence:
        """Return the registry's root for this draw seed (design §2.1).

        The registry builds ``SeedSequence([draw_seed, GATE_M6_TAG])`` on
        every period lookup (``engine/rng.py:66``), so a malformed seed is
        refused there, before the spawn. Only an exact ``int`` seed, as
        production draws give (``open_population/harness.py:86–87``), is
        kept, with the seed it was built from, and it is rebuilt when the
        seed changes. Any other seed is rebuilt on every call, so an equal
        seed of another type gets the registry's own outcome. A refused seed
        is never kept.
        """
        if type(seed) is not int:
            return np.random.SeedSequence([seed, GATE_M6_TAG])
        cached = self.__dict__.get("_root")
        if cached is None or cached[0] != seed:
            # The dataclass is frozen; like ``functools.cached_property``,
            # keep the derived root in the instance dictionary.
            cached = (seed, np.random.SeedSequence([seed, GATE_M6_TAG]))
            self.__dict__["_root"] = cached
        return cached[1]

    def _validate_period(self, period: int) -> None:
        """Keep the registry's supported period interval (design §2.1)."""
        if not 0 <= period <= self.n_periods:
            raise ValueError(
                f"period must be in [0, {self.n_periods}], got {period}"
            )

    def _sequence(
        self, period: int, module: ProjectionModule | str, *tail: int
    ) -> np.random.SeedSequence:
        """Extend the inherited module spawn key directly (design §2.1)."""
        resolved = ProjectionModule(module)
        self._validate_period(period)
        # The registry's order: its root, its spawn, then its list lookup.
        # The draw seed is recomputed on every call, as the registry's is.
        root = self._root_for(self.draw_seed)
        length = _spawned_length(self.n_periods + 1)
        position = _spawned_position(length, period)
        # A fresh entropy list per call, as the registry's fresh root gives.
        return np.random.SeedSequence(
            list(root.entropy),
            spawn_key=(position, _MODULE_INDEX[resolved], *tail),
            pool_size=root.pool_size,
        )

    def seed_sequence(
        self, period: int, module: ProjectionModule | str
    ) -> np.random.SeedSequence:
        """Return the registry's fixed module sequence (design §2.1)."""
        return self._sequence(period, module)

    def generator(
        self, period: int, module: ProjectionModule | str
    ) -> np.random.Generator:
        """Return a fresh generator for a module and period (design §2.1)."""
        return np.random.default_rng(self.seed_sequence(period, module))

    def child_generator(
        self,
        period: int,
        module: ProjectionModule | str,
        child_index: int,
    ) -> np.random.Generator:
        """Return the registry's component child stream (design §2.1)."""
        if child_index < 0:
            raise ValueError("child_index must be non-negative")
        return np.random.default_rng(
            self._sequence(period, module, child_index)
        )

    def person_generator(
        self,
        period: int,
        module: ProjectionModule | str,
        person_ordinal: int,
    ) -> np.random.Generator:
        """Return the stream of a canonical person ordinal (design §2.1)."""
        return self.child_generator(period, module, person_ordinal)

    def tagged_generator(
        self,
        period: int,
        module: ProjectionModule | str,
        component_tag: int,
    ) -> np.random.Generator:
        """Preserve tagged streams and their period-zero case (design §5.4)."""
        if component_tag < 0:
            raise ValueError("component_tag must be non-negative")
        if period == 0:
            return np.random.default_rng(
                np.random.SeedSequence([self.draw_seed, component_tag])
            )
        return np.random.default_rng(
            self._sequence(period, module, component_tag)
        )

    def tagged_child_generator(
        self,
        period: int,
        module: ProjectionModule | str,
        component_tag: int,
        child_index: int,
    ) -> np.random.Generator:
        """Return the registry's tagged child, including zero (design §5.4)."""
        if component_tag < 0 or child_index < 0:
            raise ValueError(
                "component_tag and child_index must be non-negative"
            )
        if period == 0:
            # The registry's order: the tagged root, its spawn, its lookup.
            tagged = np.random.SeedSequence([self.draw_seed, component_tag])
            length = _spawned_length(child_index + 1)
            position = _spawned_position(length, child_index)
            sequence = np.random.SeedSequence(
                tagged.entropy,
                spawn_key=(position,),
                pool_size=tagged.pool_size,
            )
        else:
            sequence = self._sequence(
                period, module, component_tag, child_index
            )
        return np.random.default_rng(sequence)
