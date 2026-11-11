"""Name what the demographic phase's parts share: inputs, columns, streams.

Implement ``docs/design/open_population.md`` §§3.1 (OP2–OP4), 5.4, 7 and 8,
approved in ruling d1925. Every record in
``docs/design/open_population_op0_1_records.json`` stays in draft, and its
coordinator questions say no provisional choice freezes itself. So a part
takes each convention as a required input with no default. The input names
its source and how far that source has gone, and a path that needs it frozen
refuses by a §8 condition.

Parts that run side by side meet here: OP3's reader emits the controls OP4's
law consumes, and OP3's timing bridge and OP4's law read one exit-timing
convention.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from numbers import Integral, Real
from types import MappingProxyType

import numpy as np

from populace_dynamics.open_population.errors import (
    ControlSourceUnavailable,
    OpenPopulationError,
    UniverseBridgeUnresolved,
)

#: A woman's persistent count of births, carried on the roster (design §5.4).
PARITY_COLUMN = "parity"
#: A newborn's birth order among its mother's births (design §3.1, OP2(a)).
BIRTH_ORDER_COLUMN = "birth_order"
#: A newborn's second parent, missing when the next column gives a reason.
SECOND_PARENT_COLUMN = "second_parent_person_id"
#: One of the registered reasons a newborn has no second parent (design §5.4).
SECOND_PARENT_UNLINKED_COLUMN = "second_parent_unlinked_reason"
#: A stayer's spouse who emigrated, and the year, never a death (design §5.4).
SPOUSE_ABROAD_COLUMN = "spouse_abroad_person_id"
SPOUSE_ABROAD_YEAR_COLUMN = "spouse_abroad_year"
#: A row's nativity for OP4's exit law. ``build_entrant_schedule`` carries this
#: name from the donor without asserting it (``entrant_schedule.py:151–154``).
FOREIGN_BORN_COLUMN = "foreign_born"
#: Adult processes a row stays out of until a milestone admits it (§§3.1, 5.4).
OUT_OF_DOMAIN_COLUMNS: Mapping[str, str] = MappingProxyType(
    {
        process: f"out_of_domain_{process}"
        for process in (
            "marital",
            "fertility",
            "disability",
            "earnings",
            "claiming",
        )
    }
)

#: Component tags below the fertility module's stream (design §5.4). Each
#: differs from ``baselines/fertility.py``'s ``ASFR_STREAM_TAG``.
NEWBORN_SEX_STREAM_TAG = 0x4F5053
LIVE_FERTILITY_STREAM_TAG = 0x4F5046


class ConventionStatus(str, Enum):
    """Say how far a convention has gone towards a registered freeze."""

    INVENTED = "invented"
    PROPOSED = "proposed"
    FROZEN = "frozen"


@dataclass(frozen=True, slots=True)
class ConventionSource:
    """Name the record behind a required input and that record's status."""

    record: str
    status: ConventionStatus

    def __post_init__(self) -> None:
        if type(self.record) is not str or not self.record.strip():
            raise ValueError("a convention needs a named source record")
        if type(self.status) is not ConventionStatus:
            raise TypeError("a convention's status must be ConventionStatus")

    def require_frozen(
        self, refusal: type[OpenPopulationError], what: str
    ) -> None:
        """Raise ``refusal`` unless this source has reached its freeze."""
        if self.status is not ConventionStatus.FROZEN:
            raise refusal(
                f"{what} stays {self.status.value}, from {self.record}"
            )


class ControlDirection(str, Enum):
    """Say whether controls size arrivals or exits."""

    INFLOW = "inflow"
    OUTFLOW = "outflow"


class ControlUniverse(str, Enum):
    """Say which population a control counts (design §§2.7, 8)."""

    SOCIAL_SECURITY_AREA = "social_security_area"
    RESIDENT_ROSTER = "resident_roster"


def _amount(value: object, what: str) -> float:
    """Return a finite real as a float, refusing booleans."""
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise ValueError(f"{what} must be a real number")
    amount = float(value)
    if not math.isfinite(amount):
        raise ValueError(f"{what} must be finite")
    return amount


@dataclass(frozen=True)
class ComponentControls:
    """Hold annual controls, in thousands of persons, by named component.

    V.A2 gives calendar-year components in thousands (design §2.7). A known
    zero is a row; a missing row is unavailable, so a year must hold every
    component the table names (design §8). A control keeps its universe, so a
    law or schedule can refuse the Social Security area's by name.
    """

    thousands: Mapping[tuple[int, str], float]
    direction: ControlDirection
    universe: ControlUniverse
    source: ConventionSource

    def __post_init__(self) -> None:
        if type(self.direction) is not ControlDirection:
            raise TypeError("direction must be ControlDirection")
        if type(self.universe) is not ControlUniverse:
            raise TypeError("universe must be ControlUniverse")
        if type(self.source) is not ConventionSource:
            raise TypeError("controls need a ConventionSource")
        rows: dict[tuple[int, str], float] = {}
        for key, value in dict(self.thousands).items():
            if not isinstance(key, tuple) or len(key) != 2:
                raise ValueError("control keys must be (year, component)")
            year, component = key
            if isinstance(year, (bool, np.bool_)) or not isinstance(
                year, Integral
            ):
                raise ValueError("control years must be integers")
            if type(component) is not str or not component.strip():
                raise ValueError("control components must be named")
            amount = _amount(value, "a control")
            if amount < 0:
                raise ValueError("controls cannot be negative")
            rows[(int(year), component)] = amount
        if not rows:
            raise ValueError("controls need at least one row")
        object.__setattr__(
            self, "thousands", MappingProxyType(dict(sorted(rows.items())))
        )

    def years(self) -> tuple[int, ...]:
        """List the years the table holds a row for, in order."""
        return tuple(sorted({year for year, _ in self.thousands}))

    def components(self) -> tuple[str, ...]:
        """List the components the table names, in order."""
        return tuple(sorted({name for _, name in self.thousands}))

    def for_year(self, year: int) -> Mapping[str, float]:
        """Return each component's control, or refuse a year not fully held."""
        missing = [
            name
            for name in self.components()
            if (year, name) not in self.thousands
        ]
        if missing:
            raise ControlSourceUnavailable(
                f"no control for {missing} in {year}, from "
                f"{self.source.record}"
            )
        return {
            name: self.thousands[(year, name)] for name in self.components()
        }

    def total(self, year: int) -> float:
        """Sum one year's components exactly as ``math.fsum`` rounds them."""
        return math.fsum(self.for_year(year).values())

    def require_universe(self, universe: ControlUniverse) -> None:
        """Refuse controls that count any other population (design §8)."""
        if self.universe is not universe:
            raise UniverseBridgeUnresolved(
                f"these controls count {self.universe.value}, and this use "
                f"needs {universe.value}"
            )


@dataclass(frozen=True, slots=True)
class ExitTimingConvention:
    """Hold the exit-timing convention OP3 and OP4 share (design §5.4).

    OP1 draws deaths first and emigration among survivors, in the mortality
    slot, before aging. OP0.1 leaves open how much of a year's exit risk an
    entrant faces in its entry year. A share of 0 keeps entrants off that
    year's risk set, and a share of 1 gives them a full year's risk. Entrant
    rows hold no Trustees component label (design §5.4), so one share covers
    them all, and OP3's bridge settles each component at its control.
    """

    entry_year_exit_share: float
    source: ConventionSource

    def __post_init__(self) -> None:
        share = _amount(self.entry_year_exit_share, "an exit share")
        if not 0 <= share <= 1:
            raise ValueError("an exit share must lie in [0, 1]")
        if type(self.source) is not ConventionSource:
            raise TypeError("an exit convention needs a ConventionSource")
        object.__setattr__(self, "entry_year_exit_share", share)

    def entry_year_probability(self, annual: np.ndarray) -> np.ndarray:
        """Return an entrant's exit probability in its entry year.

        The annual probability reads as a constant hazard over the year, so
        the result is ``1 - (1 - annual) ** share``. It never exceeds the
        annual probability and rises with it.
        """
        probabilities = np.asarray(annual, dtype=np.float64)
        if (
            not np.isfinite(probabilities).all()
            or (probabilities < 0).any()
            or (probabilities > 1).any()
        ):
            raise ValueError("annual exit probabilities must lie in [0, 1]")
        share = self.entry_year_exit_share
        if share == 0:
            return np.zeros_like(probabilities)
        if share == 1:
            return probabilities.copy()
        with np.errstate(divide="ignore"):
            exposed = -np.expm1(share * np.log1p(-probabilities))
        return np.minimum(exposed, probabilities)
