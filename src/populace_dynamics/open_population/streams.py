"""Direct construction of OP1 streams under design §§2.1 and 5.4.

The sealed registry builds the spawn tree at ``engine/rng.py:61–77`` and
extends its keys at ``:85–156``. Constructing those same keys directly keeps
OP1's draws identical without work proportional to the projection horizon.
The sealed loop continues to use its own registry.
"""

from __future__ import annotations

import operator
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


def _require_spawn_count(count: object) -> None:
    """Refuse a non-integer count as ``SeedSequence.spawn`` does (§2.1).

    The registry spawns ``n_periods + 1`` period children and
    ``child_index + 1`` tagged children (``engine/rng.py:67``, ``:144``).
    """
    operator.index(count)


def _require_list_index(period: object) -> None:
    """Refuse a non-integer period as the registry's lookup does (§2.1).

    The registry indexes its list of period children (``engine/rng.py:67``).
    """
    try:
        operator.index(period)
    except TypeError:
        raise TypeError(
            "list indices must be integers or slices, not "
            f"{type(period).__name__}"
        ) from None


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
        # The registry's spawn and list lookup refuse non-integers here.
        _require_spawn_count(self.n_periods + 1)
        _require_list_index(period)
        return np.random.SeedSequence(
            [self.draw_seed, GATE_M6_TAG],
            spawn_key=(period, _MODULE_INDEX[resolved], *tail),
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
            # Validate as the registry does: the root, then its spawn count.
            tagged = np.random.SeedSequence([self.draw_seed, component_tag])
            _require_spawn_count(child_index + 1)
            sequence = np.random.SeedSequence(
                tagged.entropy,
                spawn_key=(child_index,),
                pool_size=tagged.pool_size,
            )
        else:
            sequence = self._sequence(
                period, module, component_tag, child_index
            )
        return np.random.default_rng(sequence)
