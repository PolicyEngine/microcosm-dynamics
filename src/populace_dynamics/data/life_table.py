"""Period life-table functions from one-year death probabilities.

The equations are SSA Office of the Chief Actuary's *Definitions of Life
Table Functions* (``LifeTableDefinitions.pdf``, linked from the OACT
Downloadables page; captured 2026-10-01, SHA-256
``94c8fd5806cdb5be3762d1284155e4827a2971d3845088943e3f96a14f26e889``;
https://www.ssa.gov/OACT/Downloadables/LifeTableDefinitions.pdf):

* ``l0 = 100,000`` and ``lx = lx-1 * (1 - qx-1)`` for ``x >= 1``;
* ``dx = lx * qx``;
* ``L0 = l0 - f0 * d0``, where the separation factor ``f0`` is "the
  average number of years not lived by those age 0 who die at age 0";
* ``Lx = lx - 0.5 * dx`` for ``x >= 1`` (uniform distribution of deaths
  within each year of age above 0);
* ``Tx = Lx + Lx+1 + ...`` and ``ex = Tx / lx``.

The definitions do not say how the table ends.  OACT's death-probability
files stop at age 119 with ``q119`` usually below 1 (0.949919 for both
sexes in the TR2026 intermediate 2030 row), and its period life tables
print a positive ``e119`` (0.55 there).  This module closes the last
tabulated age ``w`` with the person-years lived at ``w`` and every later
age by a population whose central death rate stays at the uniform-deaths
value ``m_w = q_w / (1 - q_w / 2)``::

    L_w+ = l_w / m_w = l_w * (1 - q_w / 2) / q_w

which is also the sum of ``Lx`` if ``q`` were held at ``q_w`` at every age
past ``w``.  It gives ``e119 = (1 - 0.949919/2)/0.949919 = 0.5527`` for
that row, and when ``q_w = 1`` it reduces to ``L_w = l_w - 0.5 * d_w``,
the closed-table value.  ``constant_terminal_q`` is a builder default
awaiting ratification, rather than a published OACT equation.  The TR2026
transcription check records comparisons with OACT's printed period-life
expectancies, inferring ``f0`` from each row's printed ``l(0)``, ``L(0)``
and ``q(0)``.  See ``data/external/tr2026/transcription_check.json`` for
coverage, tolerances and observed errors.  The check excludes ages 110-119
from its all-age comparison because OACT uses different printing
conventions at those ages, including zero expectancy where ``q = 1``.

Invariants: survivorship and remaining person-years are nonnegative and
nonincreasing with age; before the closing age, deaths equal the loss of
survivors over the next year.  Changing the radix scales ``l, d, L, T``
by the same factor and leaves conditional life expectancy unchanged.
Increasing any death probability cannot increase life expectancy at any
earlier age, with the same separation factor and closing rule.

Two implementations are kept on purpose: :func:`period_life_table` builds
the ``l, d, L, T, e`` columns as defined above, and
:func:`life_expectancy` uses the equivalent backward recursion
``e_x = 1 - q_x / 2 + (1 - q_x) * e_{x+1}`` (``e_0 = 1 - f0 * q_0 +
(1 - q_0) * e_1``), which stays defined where ``lx`` underflows to 0.
The tests check that they agree.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

__all__ = [
    "PeriodLifeTable",
    "RADIX",
    "life_expectancy",
    "life_expectancy_profile",
    "period_life_table",
]

#: OACT's radix, ``l0 = 100,000``.
RADIX = 100_000.0


@dataclass(frozen=True)
class PeriodLifeTable:
    """The columns of a period life table, ages ``0..w`` (read-only).

    ``Lx[w]`` and ``Tx[w]`` are the person-years lived at age ``w`` and
    every later age under the closing rule in the module docstring.
    """

    qx: np.ndarray
    lx: np.ndarray
    dx: np.ndarray
    Lx: np.ndarray
    Tx: np.ndarray
    ex: np.ndarray
    f0: float
    radix: float


def _validated_q(qx: Sequence[float] | np.ndarray) -> np.ndarray:
    q = np.array(qx, dtype=np.float64)
    if q.ndim != 1:
        raise ValueError("qx must be one-dimensional (ages 0..w)")
    if q.size < 2:
        raise ValueError("qx needs at least ages 0 and 1")
    if not np.all(np.isfinite(q)):
        raise ValueError("qx must be finite")
    if np.any(q < 0.0) or np.any(q > 1.0):
        raise ValueError("every qx must lie in [0, 1]")
    if q[-1] <= 0.0:
        raise ValueError(
            "the last qx must be positive: with q_w = 0 nobody dies at or "
            "after the last age and Tx is unbounded"
        )
    return q


def _validated_f0(f0: float) -> float:
    value = float(f0)
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError("f0 must lie in [0, 1]")
    return value


def _read_only(array: np.ndarray) -> np.ndarray:
    array.setflags(write=False)
    return array


def period_life_table(
    qx: Sequence[float] | np.ndarray,
    *,
    f0: float,
    radix: float = RADIX,
) -> PeriodLifeTable:
    """Build ``l, d, L, T, e`` from ``qx`` for ages ``0..w``.

    ``f0`` is required: the definitions give no default separation factor.
    ``ex`` is ``NaN`` at ages where ``lx`` is exactly 0 (an earlier ``qx``
    equals 1, or numerical underflow); :func:`life_expectancy` returns the
    conditional value there.
    """
    q = _validated_q(qx)
    f0 = _validated_f0(f0)
    if not math.isfinite(radix) or radix <= 0.0:
        raise ValueError("radix must be positive")
    survival = np.concatenate(([1.0], np.cumprod(1.0 - q[:-1])))
    lx = radix * survival
    dx = lx * q
    big_l = lx - 0.5 * dx
    big_l[0] = lx[0] - f0 * dx[0]
    big_l[-1] = lx[-1] * (1.0 - 0.5 * q[-1]) / q[-1]
    tx = np.cumsum(big_l[::-1])[::-1]
    with np.errstate(invalid="ignore", divide="ignore"):
        ex = np.where(lx > 0.0, tx / np.where(lx > 0.0, lx, 1.0), np.nan)
    return PeriodLifeTable(
        qx=_read_only(q),
        lx=_read_only(lx),
        dx=_read_only(dx),
        Lx=_read_only(big_l),
        Tx=_read_only(tx),
        ex=_read_only(ex),
        f0=f0,
        radix=float(radix),
    )


def life_expectancy_profile(
    qx: Sequence[float] | np.ndarray, *, f0: float | None = None
) -> np.ndarray:
    """``e(x)`` at every age ``0..w`` by the backward recursion.

    With ``f0=None`` the age-0 entry is ``NaN``: it is the only age whose
    value depends on the separation factor.
    """
    q = _validated_q(qx)
    out = np.empty_like(q)
    out[-1] = (1.0 - 0.5 * q[-1]) / q[-1]
    for age in range(q.size - 2, 0, -1):
        out[age] = 1.0 - 0.5 * q[age] + (1.0 - q[age]) * out[age + 1]
    if f0 is None:
        out[0] = np.nan
    else:
        f0 = _validated_f0(f0)
        out[0] = 1.0 - f0 * q[0] + (1.0 - q[0]) * out[1]
    return _read_only(out)


def life_expectancy(
    qx: Sequence[float] | np.ndarray,
    age: int,
    *,
    f0: float | None = None,
) -> float:
    """Period life expectancy at exact ``age`` (backward recursion).

    ``f0`` is needed only at age 0; asking for age 0 without it raises.
    """
    q = _validated_q(qx)
    try:
        integer_age = int(age)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("age must be an integer") from error
    if isinstance(age, bool) or integer_age != age:
        raise ValueError("age must be an integer")
    age = integer_age
    if not 0 <= age < q.size:
        raise ValueError(f"age must lie in 0..{q.size - 1}")
    if age == 0 and f0 is None:
        raise ValueError("life expectancy at birth needs the separation f0")
    return float(life_expectancy_profile(q, f0=f0)[age])
