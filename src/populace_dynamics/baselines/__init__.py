"""Selectable projection baselines (NASI follow-up package B2).

A baseline bundles the paths a projection reads besides its cohort:
COLA, CPI-W, AWI, population mortality by single age, sex and year,
fertility, the claim-age table and DI rates
(:class:`~populace_dynamics.baselines.base.Baseline`).  Three are
registered:

``tr2008_intermediate`` (default)
    :class:`~populace_dynamics.baselines.legacy.TR2008Legacy`, the 2008
    Trustees baseline the registered projection tests (exercises 1 and
    3) use, delegating to their existing constructors unchanged.
``tr2026_intermediate``
    :class:`~populace_dynamics.baselines.tr2026_intermediate.
    TR2026Intermediate`, the 2026 Trustees intermediate assumptions.
``cbo2026_long_term``
    :class:`~populace_dynamics.baselines.cbo2026_long_term.
    CBO2026LongTerm`, CBO's 2026 long-term projections.

The 2026 baselines splice realized COLAs through determination year 2025
and realized AWI through 2024 before any projected or derived value, and
tag every derived value (:meth:`Baseline.value_sources`).  They are for
invented-data and unregistered projections only:
:func:`~populace_dynamics.baselines.track_a.build_track_a_inputs` refuses
a real-data run under them (see :mod:`~populace_dynamics.baselines.
track_a` for why), and :func:`~populace_dynamics.baselines.track_a.
project_track_a` projects invented cohorts under any baseline without
the TR2008-bound checks of ``run_track_a``.
:mod:`~populace_dynamics.baselines.fertility` adds an opt-in, not gated,
report-only ASFR birth step for open populations.
"""

from __future__ import annotations

from collections.abc import Callable

from populace_dynamics.baselines.base import (
    Baseline,
    BaselineGapError,
    BaselineYearAwareMortality,
)
from populace_dynamics.baselines.cbo2026_long_term import CBO2026LongTerm
from populace_dynamics.baselines.legacy import TR2008Legacy
from populace_dynamics.baselines.tr2026_intermediate import (
    TR2026Intermediate,
)
from populace_dynamics.baselines.track_a import (
    INVENTED_SEED,
    build_track_a_inputs,
    invented_track_a_cohorts,
    project_track_a,
    track_a_config_for,
)

__all__ = [
    "BASELINE_NAMES",
    "DEFAULT_BASELINE",
    "INVENTED_SEED",
    "Baseline",
    "BaselineGapError",
    "BaselineYearAwareMortality",
    "CBO2026LongTerm",
    "TR2008Legacy",
    "TR2026Intermediate",
    "build_track_a_inputs",
    "get_baseline",
    "invented_track_a_cohorts",
    "project_track_a",
    "track_a_config_for",
]

DEFAULT_BASELINE = "tr2008_intermediate"
_REGISTRY: dict[str, Callable[[], Baseline]] = {
    "tr2008_intermediate": TR2008Legacy,
    "tr2026_intermediate": TR2026Intermediate,
    "cbo2026_long_term": CBO2026LongTerm,
}
BASELINE_NAMES: tuple[str, ...] = tuple(_REGISTRY)


def get_baseline(name: str = DEFAULT_BASELINE) -> Baseline:
    """The registered baseline called ``name`` (default: the legacy one)."""
    try:
        factory = _REGISTRY[name]
    except KeyError:
        raise KeyError(
            f"unknown baseline {name!r}; registered: {list(BASELINE_NAMES)}"
        ) from None
    baseline = factory()
    if baseline.name != name:
        raise RuntimeError(f"registry entry {name!r} built {baseline.name!r}")
    return baseline
