"""Named limits the starting stock reports beside each inferred PIA.

Each limit is a function from plain values to a boolean, so a later job
can apply it to a column. Each flags a person whose inferred PIA rests
on an assumption the inference can't check.
"""

from __future__ import annotations

import math
import numbers

from populace_dynamics.starting_stock.claim_age import TOP_CODE_BANDS

__all__ = [
    "has_two_reasons",
    "has_all_four_components",
    "is_top_coded",
    "needs_linked_pia",
]


def _number(label: str, value: object) -> float:
    """A finite real number, refusing booleans and strings."""
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise TypeError(f"{label} must be a real number")
    out = float(value)
    if not math.isfinite(out):
        raise ValueError(f"{label} must be finite, got {out!r}")
    return out


def has_two_reasons(reason_1: float, reason_2: float) -> bool:
    """Both CPS reasons are nonzero, the dual-entitlement proxy; it can't see which benefits are paid, or dual entitlement given as one reason."""
    return (
        _number("reason_1", reason_1) != 0.0
        and _number("reason_2", reason_2) != 0.0
    )


def has_all_four_components(
    retirement: float,
    disability: float,
    survivors: float,
    dependents: float,
) -> bool:
    """All four amounts are positive, marking the synthetic split on tax-file clones; it can't tell a real four-way receipt from that split."""
    return all(
        _number(label, value) > 0.0
        for label, value in (
            ("retirement", retirement),
            ("disability", disability),
            ("survivors", survivors),
            ("dependents", dependents),
        )
    )


def is_top_coded(age_top_code: float) -> bool:
    """The recorded age is a top code (80 or 85); it can't see the single year of age within the band."""
    return _number("age_top_code", age_top_code) in TOP_CODE_BANDS


def needs_linked_pia(survivors: float, dependents: float) -> bool:
    """A survivor's or dependent's amount is positive; it can't see the linked worker or that worker's PIA."""
    return (
        _number("survivors", survivors) > 0.0
        or _number("dependents", dependents) > 0.0
    )
