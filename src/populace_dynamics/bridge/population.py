"""Run PolicyEngine-US over a population: one weighted simulation per scenario.

The bridge (:mod:`.policyengine_us`) runs one household per simulation.  This
module runs a whole population through one weighted PolicyEngine-US
``Microsimulation`` per scenario and splits every household's change in
``household_net_income`` exactly as the bridge does.  It imports no
``policyengine_us``: the simulations run in a separate interpreter, as the
bridge's do.

1. **The population as arrays.**  :class:`PopulationFrame` holds people (age,
   the bridge's :data:`~.policyengine_us.AMOUNT_FIELDS`, Medicare quarters)
   and their membership in PolicyEngine-US's five group entities as index
   arrays, with each household's state and weight.  It enforces the
   invariants of :class:`~.policyengine_us.BridgeHousehold` over arrays:
   every person in exactly one unit of each kind, no empty unit, marital
   units of one or two people, finite nonnegative amounts; and one more,
   that every unit lies inside the units policyengine-us 2.18.0 declares
   as containing it (``entities.py:35,53,71,89``).
   :meth:`PopulationFrame.from_households` and
   :meth:`PopulationFrame.to_households` convert to and from the bridge's
   :class:`~.policyengine_us.BridgeHousehold`, which validates each
   household again.
2. **One simulation per scenario.**  :meth:`PopulationFrame.to_dataset`
   writes policyengine-core's ``TIME_PERIOD_ARRAYS`` layout ``{variable:
   {period: array}}`` with one id array per entity and one membership array
   per group entity.  policyengine-core accepts a ``Dataset`` of that
   format (``data/dataset.py:60-73``, saved by ``save_dataset``,
   ``:184-219``) and builds the simulation's entities from the id and
   membership arrays (``simulations/simulation.py:405-562``);
   policyengine-us's ``Microsimulation`` passes a ``Dataset`` instance,
   which is neither a path nor a ``USSingleYearDataset``, to core
   unchanged (``system.py:462-495``), and core weights every result by
   ``household_weight`` (``simulations/microsimulation.py:16-46,64-82``).
   :func:`run_population` runs one such simulation per scenario and
   variant in the policyengine-us interpreter, after the bridge's
   source and version checks, and returns every node of the net-income
   tree at the household level.
3. **Population-level formulas.**  A search of policyengine-us 2.18.0's
   variable formulas (``variables/``) for simulation-wide reductions
   (``sum_by_state``, weights, ``np.unique``, ``bincount``, ranks and
   quantiles, ``simulation.is_over_dataset``) finds these formulas whose
   value for one household depends on the others in its simulation:

   * ``medicaid_slcsp_state_average_cost_index``: the weighted average of
     the cost index over every person in the state
     (``variables/gov/hhs/medicaid/costs/
     medicaid_slcsp_state_average_cost_index.py:14-29``, through
     ``state_aggregate_helpers.py:11-26``);
   * ``medicaid_slcsp_state_denominator``: over a dataset, the weighted sum
     of the cost index over every enrollee in the state, so that a state's
     Medicaid cost sums to its calibrated spending; for a situation, the
     state's enrollment times the state-average index
     (``medicaid_slcsp_state_denominator.py:14-33``).  Medicaid at cost is
     spending times the person's index over that denominator
     (``medicaid_cost_if_enrolled.py:11-22``);
   * ``household_income_decile`` and ``spm_unit_income_decile``: weighted
     decile ranks over the simulation
     (``variables/household/income/household/household_income_decile.py:
     12-21``; ``spm_unit/spm_unit_income_decile.py:14-15``).

   Two more read across units by id or by branch but are inactive here:
   the Medicaid claiming-tax-unit lookups match
   ``medicaid_claiming_tax_unit_id`` against every ``tax_unit_id``
   (``variables/gov/hhs/medicaid/income/_claiming_tax_unit.py:7-51``), and
   the id defaults to 0, "no known claiming tax unit"
   (``medicaid_claiming_tax_unit_id.py:10-14``); the behavioral responses
   read ``simulation.baseline``, which is ``None`` without a ``reform``
   argument (``capital_gains_responses.py:40-41``,
   ``labor_supply_behavioral_response.py:18-19``).

   :func:`run_population` therefore pins the two Medicaid inputs, by
   default, to the values policyengine-us computes for each household
   simulated alone (``medicaid_valuation="household"``): the average of
   the positive cost indices of the household's own members, and the
   state's enrollment times that average, the single-household branch
   (``medicaid_slcsp_state_denominator.py:28-33``) with the household's
   weight at its default of 1 (``household_weight.py:9``).  A household's
   results then do not depend on the rest of the population, which
   ``tests/bridge/test_population_oracle.py`` checks against the bridge's
   one-household runs.  ``"native"`` leaves policyengine-us's dataset
   formulas in place.  The deciles are computed only as a grouping, from
   the baseline simulation.
4. **Decomposition.**  :func:`decompose_population` applies the bridge's
   decomposition to every household at once (checks and cents rounding as
   :func:`~.policyengine_us.decompose`, which a differential test pins),
   and :class:`ExactWeights` sums weighted cents as exact rationals, so
   the weighted leaves, categories and levels of government each sum
   exactly to the weighted net change.
"""

from __future__ import annotations

import json
import math
import os
import time
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

import numpy as np

from populace_dynamics.bridge import policyengine_us as bridge

__all__ = [
    "CONTAINING_ENTITIES",
    "ExactWeights",
    "GROUP_ENTITIES",
    "LEVELS",
    "LEVEL_LABELS",
    "MEDICAID_VALUATIONS",
    "PopulationDecomposition",
    "PopulationFrame",
    "PopulationRun",
    "UnclassifiedChangeError",
    "decile_ranks",
    "decompose_population",
    "household_from_situation",
    "level_for",
    "run_population",
    "to_cents_array",
]

#: PolicyEngine-US's group entities (``entities.py``, policyengine-us
#: 2.18.0), each with the single role ``member``.
GROUP_ENTITIES: tuple[str, ...] = (
    "household",
    "spm_unit",
    "family",
    "tax_unit",
    "marital_unit",
)
#: The entities each group entity declares as containing it
#: (``containing_entities``, ``entities.py:35,53,71,89``).  The frame
#: refuses a unit whose members span two containing units.
CONTAINING_ENTITIES: dict[str, tuple[str, ...]] = {
    "spm_unit": ("household",),
    "family": ("spm_unit", "household"),
    "tax_unit": ("spm_unit", "family", "household"),
    "marital_unit": ("spm_unit", "family", "household"),
}
#: How Medicaid at cost is valued (module docstring, item 3).
MEDICAID_VALUATIONS: tuple[str, ...] = ("household", "native")
_MAX_AGE = 125
#: Medicare quarters of coverage left to the model's default.
_DEFAULT_QUARTERS = -1


class UnclassifiedChangeError(ValueError):
    """A leaf changed whose level of government is not classified."""


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------
def _frozen(array: np.ndarray) -> np.ndarray:
    array.setflags(write=False)
    return array


def _int_array(values: Any, label: str, length: int | None = None):
    array = np.asarray(values)
    if array.ndim != 1:
        raise ValueError(f"{label} must be one-dimensional")
    if array.dtype.kind == "b" or (
        array.size and array.dtype.kind not in "iu"
    ):
        raise TypeError(f"{label} must hold integers, not {array.dtype}")
    if length is not None and len(array) != length:
        raise ValueError(f"{label} has {len(array)} entries, not {length}")
    return _frozen(array.astype(np.int64, copy=True))


def _amount_array(values: Any, label: str, length: int) -> np.ndarray:
    array = np.asarray(values)
    if array.ndim != 1 or len(array) != length:
        raise ValueError(f"{label} must hold {length} amounts")
    if array.dtype.kind == "b" or (
        array.size and array.dtype.kind not in "iuf"
    ):
        raise TypeError(f"{label} must hold numbers, not {array.dtype}")
    array = array.astype(np.float64, copy=True)
    if not np.isfinite(array).all():
        raise ValueError(f"{label} must be finite")
    if (array < 0).any():
        raise ValueError(f"{label} must be nonnegative")
    return _frozen(array)


def _bool_array(values: Any, label: str, length: int) -> np.ndarray:
    array = np.asarray(values)
    if array.ndim != 1 or len(array) != length:
        raise ValueError(f"{label} must hold {length} flags")
    if array.size and array.dtype.kind != "b":
        raise TypeError(f"{label} must hold bools, not {array.dtype}")
    return _frozen(array.astype(bool, copy=True))


def _names(values: Iterable[Any], label: str) -> tuple[str, ...]:
    if isinstance(values, str):
        raise TypeError(f"{label}: expected a sequence of ids, not a str")
    names = tuple(values)
    for name in names:
        if not isinstance(name, str) or not name:
            raise ValueError(f"{label} must be nonempty strings: {name!r}")
    return names


# ---------------------------------------------------------------------------
# The population
# ---------------------------------------------------------------------------
@dataclass(frozen=True, eq=False)
class PopulationFrame:
    """People, their units, and each household's state and weight.

    ``units[kind][i]`` is the index of person ``i``'s unit of ``kind``
    (each of :data:`GROUP_ENTITIES`), so every person is in exactly one unit
    of each kind by construction; every unit index up to the largest must
    have a member.  ``person_ids`` are unique within a household (as in
    :class:`~.policyengine_us.BridgeHousehold`); ``household_ids`` are unique.
    ``amounts`` holds every :data:`~.policyengine_us.AMOUNT_FIELDS` array
    (annual dollars; a stock for the asset); ``medicare_quarters_of_coverage``
    is -1 where the model's default applies.  ``state``, ``weight`` and
    ``food_preparation_allowed`` are per household;
    ``has_heating_cooling_expense`` and ``takes_up_housing_assistance`` are
    per SPM unit (the bridge's flags, set as inputs for the reasons
    :class:`~.policyengine_us.BridgeHousehold` gives).  Arrays are read-only.
    """

    person_ids: tuple[str, ...]
    age: np.ndarray
    amounts: Mapping[str, np.ndarray]
    medicare_quarters_of_coverage: np.ndarray
    units: Mapping[str, np.ndarray]
    household_ids: tuple[str, ...]
    state: tuple[str, ...]
    weight: np.ndarray
    has_heating_cooling_expense: np.ndarray
    takes_up_housing_assistance: np.ndarray
    food_preparation_allowed: np.ndarray

    def __post_init__(self) -> None:
        people = _names(self.person_ids, "person_ids")
        if not people:
            raise ValueError("a population needs at least one person")
        n = len(people)
        object.__setattr__(self, "person_ids", people)
        age = _int_array(self.age, "age", n)
        if ((age < 0) | (age > _MAX_AGE)).any():
            raise ValueError(f"age must be 0-{_MAX_AGE}")
        object.__setattr__(self, "age", age)
        if set(self.amounts) != set(bridge.AMOUNT_FIELDS):
            raise ValueError(
                f"amounts must be exactly {bridge.AMOUNT_FIELDS}, not "
                f"{sorted(self.amounts)}"
            )
        object.__setattr__(
            self,
            "amounts",
            {
                name: _amount_array(self.amounts[name], name, n)
                for name in bridge.AMOUNT_FIELDS
            },
        )
        quarters = _int_array(
            self.medicare_quarters_of_coverage,
            "medicare_quarters_of_coverage",
            n,
        )
        if (quarters < _DEFAULT_QUARTERS).any():
            raise ValueError(
                "medicare_quarters_of_coverage must be >= 0 (or -1 for the "
                "model's default)"
            )
        object.__setattr__(self, "medicare_quarters_of_coverage", quarters)
        if set(self.units) != set(GROUP_ENTITIES):
            raise ValueError(f"units must be exactly {GROUP_ENTITIES}")
        units = {
            kind: _int_array(self.units[kind], f"units[{kind}]", n)
            for kind in GROUP_ENTITIES
        }
        counts = {}
        for kind, index in units.items():
            if (index < 0).any():
                raise ValueError(f"units[{kind}] must be nonnegative")
            count = int(index.max()) + 1
            members = np.bincount(index, minlength=count)
            if (members == 0).any():
                raise ValueError(
                    f"every {kind} must have a member: "
                    f"{np.flatnonzero(members == 0)[:10].tolist()} have none"
                )
            counts[kind] = count
        object.__setattr__(self, "units", units)
        if (np.bincount(units["marital_unit"]) > 2).any():
            raise ValueError("a marital unit has at most two people")
        for kind, containers in CONTAINING_ENTITIES.items():
            for container in containers:
                owner = np.full(counts[kind], -1, dtype=np.int64)
                owner[units[kind]] = units[container]
                if (owner[units[kind]] != units[container]).any():
                    raise ValueError(
                        f"every {kind} must lie inside one {container}"
                    )
        households = _names(self.household_ids, "household_ids")
        if len(households) != counts["household"]:
            raise ValueError(
                f"{counts['household']} households but "
                f"{len(households)} household_ids"
            )
        if len(set(households)) != len(households):
            raise ValueError("household_ids must be unique")
        object.__setattr__(self, "household_ids", households)
        pairs = set(zip(units["household"].tolist(), people, strict=True))
        if len(pairs) != n:
            raise ValueError("person ids must be unique within a household")
        states = tuple(self.state)
        if len(states) != counts["household"]:
            raise ValueError("state must have one entry per household")
        for state in states:
            if state not in bridge.STATE_FIPS:
                raise ValueError(f"state must be a key of STATE_FIPS: {state}")
        object.__setattr__(self, "state", states)
        weight = _amount_array(self.weight, "weight", counts["household"])
        if (weight <= 0).any():
            raise ValueError("every household weight must be positive")
        object.__setattr__(self, "weight", weight)
        for label, kind in (
            ("has_heating_cooling_expense", "spm_unit"),
            ("takes_up_housing_assistance", "spm_unit"),
            ("food_preparation_allowed", "household"),
        ):
            object.__setattr__(
                self,
                label,
                _bool_array(getattr(self, label), label, counts[kind]),
            )

    # -- sizes ---------------------------------------------------------------
    @property
    def n_people(self) -> int:
        return len(self.person_ids)

    @property
    def n_households(self) -> int:
        return len(self.household_ids)

    def unit_count(self, kind: str) -> int:
        return int(self.units[kind].max()) + 1

    # -- comparisons -----------------------------------------------------------
    def same_structure(self, other: PopulationFrame) -> bool:
        """Everything but the amounts is equal."""

        return (
            self.person_ids == other.person_ids
            and self.household_ids == other.household_ids
            and self.state == other.state
            and np.array_equal(self.age, other.age)
            and np.array_equal(
                self.medicare_quarters_of_coverage,
                other.medicare_quarters_of_coverage,
            )
            and all(
                np.array_equal(self.units[kind], other.units[kind])
                for kind in GROUP_ENTITIES
            )
            and np.array_equal(self.weight, other.weight)
            and all(
                np.array_equal(getattr(self, flag), getattr(other, flag))
                for flag in (
                    "has_heating_cooling_expense",
                    "takes_up_housing_assistance",
                    "food_preparation_allowed",
                )
            )
        )

    def equals(self, other: PopulationFrame) -> bool:
        return self.same_structure(other) and all(
            np.array_equal(self.amounts[name], other.amounts[name])
            for name in bridge.AMOUNT_FIELDS
        )

    def with_amounts(self, **arrays: Any) -> PopulationFrame:
        """The same population with some amount arrays replaced."""

        unknown = set(arrays) - set(bridge.AMOUNT_FIELDS)
        if unknown:
            raise ValueError(f"not amount fields: {sorted(unknown)}")
        return _replace(self, amounts={**self.amounts, **arrays})

    def subset(self, households: Sequence[int]) -> PopulationFrame:
        """The population of the given households (in the given order)."""

        chosen = [int(h) for h in households]
        if len(set(chosen)) != len(chosen) or not chosen:
            raise ValueError("choose distinct households")
        if min(chosen) < 0 or max(chosen) >= self.n_households:
            raise ValueError("a chosen household is out of range")
        rank = {h: i for i, h in enumerate(chosen)}
        people = [
            i
            for h in chosen
            for i in np.flatnonzero(self.units["household"] == h)
        ]
        idx = np.asarray(people, dtype=np.int64)

        def renumber(values: np.ndarray) -> np.ndarray:
            _, inverse = np.unique(values, return_inverse=True)
            order = []
            seen: dict[int, int] = {}
            for value in inverse.tolist():
                if value not in seen:
                    seen[value] = len(seen)
                order.append(seen[value])
            return np.asarray(order, dtype=np.int64)

        units = {
            "household": np.asarray(
                [rank[int(h)] for h in self.units["household"][idx]],
                dtype=np.int64,
            )
        }
        for kind in GROUP_ENTITIES[1:]:
            units[kind] = renumber(self.units[kind][idx])
        spm_old = [
            int(self.units["spm_unit"][idx][units["spm_unit"] == u][0])
            for u in range(int(units["spm_unit"].max()) + 1)
        ]
        return PopulationFrame(
            person_ids=tuple(self.person_ids[i] for i in people),
            age=self.age[idx],
            amounts={k: v[idx] for k, v in self.amounts.items()},
            medicare_quarters_of_coverage=(
                self.medicare_quarters_of_coverage[idx]
            ),
            units=units,
            household_ids=tuple(self.household_ids[h] for h in chosen),
            state=tuple(self.state[h] for h in chosen),
            weight=self.weight[chosen],
            has_heating_cooling_expense=(
                self.has_heating_cooling_expense[spm_old]
            ),
            takes_up_housing_assistance=(
                self.takes_up_housing_assistance[spm_old]
            ),
            food_preparation_allowed=self.food_preparation_allowed[chosen],
        )

    # -- the bridge's households -----------------------------------------------
    @classmethod
    def from_households(
        cls,
        households: Sequence[bridge.BridgeHousehold],
        weights: Sequence[float] | None = None,
    ) -> PopulationFrame:
        """Vectorize validated bridge households (people and units in order).

        A household's two SPM-unit flags apply to each of its SPM units, as
        :func:`~.policyengine_us.to_situation` writes them.  ``weights``
        defaults to 1 for every household (policyengine-us's
        ``household_weight`` default, ``household_weight.py:9``).
        """

        households = tuple(households)
        for household in households:
            if not isinstance(household, bridge.BridgeHousehold):
                raise TypeError("households must be BridgeHousehold instances")
        person_ids: list[str] = []
        age: list[int] = []
        amounts: dict[str, list[float]] = {k: [] for k in bridge.AMOUNT_FIELDS}
        quarters: list[int] = []
        units: dict[str, list[int]] = {kind: [] for kind in GROUP_ENTITIES}
        offsets = dict.fromkeys(GROUP_ENTITIES[1:], 0)
        heating: list[bool] = []
        housing: list[bool] = []
        for h, household in enumerate(households):
            groups = {
                "spm_unit": household.spm_units,
                "family": household.families or (),
                "tax_unit": household.tax_units,
                "marital_unit": household.marital_units,
            }
            where = {
                kind: {
                    member: offsets[kind] + g
                    for g, group in enumerate(parts)
                    for member in group
                }
                for kind, parts in groups.items()
            }
            for person in household.people:
                person_ids.append(person.person_id)
                age.append(person.age)
                for name, value in person.amounts().items():
                    amounts[name].append(value)
                quarters.append(
                    _DEFAULT_QUARTERS
                    if person.medicare_quarters_of_coverage is None
                    else person.medicare_quarters_of_coverage
                )
                units["household"].append(h)
                for kind in groups:
                    units[kind].append(where[kind][person.person_id])
            for kind, parts in groups.items():
                offsets[kind] += len(parts)
            heating += [household.has_heating_cooling_expense] * len(
                household.spm_units
            )
            housing += [household.takes_up_housing_assistance] * len(
                household.spm_units
            )
        return cls(
            person_ids=tuple(person_ids),
            age=np.asarray(age, dtype=np.int64),
            amounts={
                k: np.asarray(v, dtype=float) for k, v in amounts.items()
            },
            medicare_quarters_of_coverage=np.asarray(quarters, dtype=np.int64),
            units={k: np.asarray(v, dtype=np.int64) for k, v in units.items()},
            household_ids=tuple(h.household_id for h in households),
            state=tuple(h.state for h in households),
            weight=np.asarray(
                [1.0] * len(households) if weights is None else weights,
                dtype=float,
            ),
            has_heating_cooling_expense=np.asarray(heating, dtype=bool),
            takes_up_housing_assistance=np.asarray(housing, dtype=bool),
            food_preparation_allowed=np.asarray(
                [h.food_preparation_allowed for h in households], dtype=bool
            ),
        )

    def to_households(self) -> tuple[bridge.BridgeHousehold, ...]:
        """One validated :class:`~.policyengine_us.BridgeHousehold` each.

        Units are listed in unit order with members in person order.
        Refuses a household whose SPM units carry different flags (a
        :class:`~.policyengine_us.BridgeHousehold` holds one of each).
        """

        out = []
        for h, household_id in enumerate(self.household_ids):
            members = np.flatnonzero(self.units["household"] == h)
            people = []
            for i in members:
                quarters = int(self.medicare_quarters_of_coverage[i])
                people.append(
                    bridge.BridgePerson(
                        person_id=self.person_ids[i],
                        age=int(self.age[i]),
                        **{
                            name: float(self.amounts[name][i])
                            for name in bridge.AMOUNT_FIELDS
                        },
                        medicare_quarters_of_coverage=(
                            None if quarters == _DEFAULT_QUARTERS else quarters
                        ),
                    )
                )

            def groups(
                kind: str, members: np.ndarray = members
            ) -> tuple[tuple[str, ...], ...]:
                index = self.units[kind][members]
                ordered = sorted(set(index.tolist()))
                return tuple(
                    tuple(
                        self.person_ids[i]
                        for i, u in zip(members, index, strict=True)
                        if u == unit
                    )
                    for unit in ordered
                )

            spm = sorted(set(self.units["spm_unit"][members].tolist()))
            heating = {bool(self.has_heating_cooling_expense[u]) for u in spm}
            housing = {bool(self.takes_up_housing_assistance[u]) for u in spm}
            if len(heating) != 1 or len(housing) != 1:
                raise ValueError(
                    f"{household_id}: its SPM units carry different flags"
                )
            out.append(
                bridge.BridgeHousehold(
                    household_id=household_id,
                    state=self.state[h],
                    people=tuple(people),
                    tax_units=groups("tax_unit"),
                    spm_units=groups("spm_unit"),
                    marital_units=groups("marital_unit"),
                    families=groups("family"),
                    has_heating_cooling_expense=heating.pop(),
                    takes_up_housing_assistance=housing.pop(),
                    food_preparation_allowed=bool(
                        self.food_preparation_allowed[h]
                    ),
                )
            )
        return tuple(out)

    # -- policyengine-core's dataset layout --------------------------------------
    def to_dataset(self, year: int) -> dict[str, dict[str, np.ndarray]]:
        """The ``TIME_PERIOD_ARRAYS`` layout for ``year`` (module docstring).

        Ids run from 1 (``person_id``, and ``<entity>_id`` per group entity);
        ``person_<entity>_id`` is the id of each person's unit and
        ``person_<entity>_role`` the index of each person's role, 0 for
        every entity's single role ``member`` (``entities.py:10-17``).
        Without a role array, policyengine-core gives a group population
        one default role per *unit*, not per person
        (``simulations/simulation.py:482-483``); no 2.18.0 formula reads a
        role, but the runner checks one role per person.  Every
        :data:`~.policyengine_us.AMOUNT_FIELDS` array and ``age`` are person
        inputs; ``state_fips`` (policyengine-us derives the state from it),
        ``household_weight`` and
        ``living_arrangements_allow_for_food_preparation`` are household
        inputs; ``has_heating_cooling_expense`` and
        ``takes_up_housing_assistance_if_eligible`` are SPM-unit inputs, as
        :func:`~.policyengine_us.to_situation` sets them.
        ``medicare_quarters_of_coverage`` keeps -1 where the model's default
        applies; the runner fills it with that default.  Deterministic.
        """

        if isinstance(year, bool) or not isinstance(year, int):
            raise TypeError(f"year must be an integer, not {year!r}")
        period = str(year)
        data: dict[str, dict[str, np.ndarray]] = {
            "person_id": {period: np.arange(1, self.n_people + 1)}
        }
        for kind in GROUP_ENTITIES:
            data[f"{kind}_id"] = {
                period: np.arange(1, self.unit_count(kind) + 1)
            }
            data[f"person_{kind}_id"] = {period: self.units[kind] + 1}
            data[f"person_{kind}_role"] = {
                period: np.zeros(self.n_people, dtype=np.int64)
            }
        data["age"] = {period: self.age.copy()}
        for name in bridge.AMOUNT_FIELDS:
            data[name] = {period: self.amounts[name].copy()}
        data["medicare_quarters_of_coverage"] = {
            period: self.medicare_quarters_of_coverage.copy()
        }
        data["state_fips"] = {
            period: np.asarray(
                [bridge.STATE_FIPS[s] for s in self.state], dtype=np.int64
            )
        }
        data["household_weight"] = {period: self.weight.copy()}
        data["living_arrangements_allow_for_food_preparation"] = {
            period: self.food_preparation_allowed.copy()
        }
        data["has_heating_cooling_expense"] = {
            period: self.has_heating_cooling_expense.copy()
        }
        data["takes_up_housing_assistance_if_eligible"] = {
            period: self.takes_up_housing_assistance.copy()
        }
        return data

    @classmethod
    def from_dataset(
        cls,
        data: Mapping[str, Mapping[str, Any]],
        year: int,
        *,
        person_ids: Sequence[str],
        household_ids: Sequence[str],
    ) -> PopulationFrame:
        """Read :meth:`to_dataset`'s layout back (the round trip's inverse)."""

        period = str(year)

        def get(name: str) -> np.ndarray:
            return np.asarray(data[name][period])

        units = {}
        for kind in GROUP_ENTITIES:
            ids = get(f"{kind}_id").tolist()
            position = {value: i for i, value in enumerate(ids)}
            if len(position) != len(ids):
                raise ValueError(f"{kind}_id repeats an id")
            units[kind] = np.asarray(
                [position[v] for v in get(f"person_{kind}_id").tolist()],
                dtype=np.int64,
            )
        fips = {value: state for state, value in bridge.STATE_FIPS.items()}
        return cls(
            person_ids=tuple(person_ids),
            age=get("age"),
            amounts={name: get(name) for name in bridge.AMOUNT_FIELDS},
            medicare_quarters_of_coverage=get("medicare_quarters_of_coverage"),
            units=units,
            household_ids=tuple(household_ids),
            state=tuple(fips[int(v)] for v in get("state_fips").tolist()),
            weight=get("household_weight"),
            has_heating_cooling_expense=get("has_heating_cooling_expense"),
            takes_up_housing_assistance=get(
                "takes_up_housing_assistance_if_eligible"
            ),
            food_preparation_allowed=get(
                "living_arrangements_allow_for_food_preparation"
            ),
        )


def household_from_situation(
    situation: Mapping[str, Any], year: int
) -> bridge.BridgeHousehold:
    """The inverse of :func:`~.policyengine_us.to_situation`.

    Reads one household's people, units, state and flags back from the
    situation ``to_situation`` writes for ``year`` (a committed bridge run's
    situations, for example), and validates it as a
    :class:`~.policyengine_us.BridgeHousehold`.  Refuses a situation with
    other than one household, or whose SPM units carry different flags.
    """

    period = str(year)
    [(household_id, household)] = list(situation["households"].items())
    fips = {value: state for state, value in bridge.STATE_FIPS.items()}
    people = []
    for person_id, entry in situation["people"].items():
        quarters = entry.get("medicare_quarters_of_coverage")
        people.append(
            bridge.BridgePerson(
                person_id=person_id,
                age=int(entry["age"][period]),
                **{
                    name: float(entry[name][period])
                    for name in bridge.AMOUNT_FIELDS
                    if name in entry
                },
                medicare_quarters_of_coverage=(
                    None if quarters is None else int(quarters[period])
                ),
            )
        )

    def groups(plural: str) -> tuple[tuple[str, ...], ...]:
        return tuple(
            tuple(unit["members"]) for unit in situation[plural].values()
        )

    spm = list(situation["spm_units"].values())
    heating = {bool(u["has_heating_cooling_expense"][period]) for u in spm}
    housing = {
        bool(u["takes_up_housing_assistance_if_eligible"][period]) for u in spm
    }
    if len(heating) != 1 or len(housing) != 1:
        raise ValueError(f"{household_id}: SPM units carry different flags")
    if list(household["members"]) != [p.person_id for p in people]:
        raise ValueError(f"{household_id}: members differ from people")
    return bridge.BridgeHousehold(
        household_id=household_id,
        state=fips[int(household["state_fips"][period])],
        people=tuple(people),
        tax_units=groups("tax_units"),
        spm_units=groups("spm_units"),
        marital_units=groups("marital_units"),
        families=groups("families"),
        has_heating_cooling_expense=heating.pop(),
        takes_up_housing_assistance=housing.pop(),
        food_preparation_allowed=bool(
            household["living_arrangements_allow_for_food_preparation"][period]
        ),
    )


def _replace(frame: PopulationFrame, **changes: Any) -> PopulationFrame:
    fields = {
        name: getattr(frame, name)
        for name in PopulationFrame.__dataclass_fields__
    }
    fields.update(changes)
    return PopulationFrame(**fields)


# ---------------------------------------------------------------------------
# The runner
# ---------------------------------------------------------------------------
#: Input variables and the dtype the child gives each array.
_DTYPES: dict[str, str] = {
    "person_id": "int64",
    **{f"{kind}_id": "int64" for kind in GROUP_ENTITIES},
    **{f"person_{kind}_id": "int64" for kind in GROUP_ENTITIES},
    **{f"person_{kind}_role": "int64" for kind in GROUP_ENTITIES},
    "age": "int64",
    **dict.fromkeys(bridge.AMOUNT_FIELDS, "float64"),
    "medicare_quarters_of_coverage": "int64",
    "state_fips": "int64",
    "household_weight": "float64",
    "living_arrangements_allow_for_food_preparation": "bool",
    "has_heating_cooling_expense": "bool",
    "takes_up_housing_assistance_if_eligible": "bool",
}

#: Executed by the policyengine-us interpreter.  For each variant (a set of
#: parameter overrides) and scenario (a dataset), one ``Microsimulation``:
#: the dataset is written in policyengine-core's ``TIME_PERIOD_ARRAYS``
#: layout to a temporary file and passed as a ``Dataset`` instance.  Cases
#: with the same overrides share one reformed tax-benefit system, built from
#: a throwaway simulation and passed as ``tax_benefit_system`` with no
#: ``reform``, as the bridge's runner does (``spm.py:830-834``), so no
#: simulation has a ``baseline`` branch.  With ``medicaid_valuation ==
#: "household"`` the child pins ``medicaid_slcsp_state_average_cost_index``
#: and ``medicaid_slcsp_state_denominator`` to each household's
#: single-household values before anything reads them (module docstring,
#: item 3), replicating the formulas' arithmetic
#: (``medicaid_slcsp_state_average_cost_index.py:16-29`` over the
#: household's own members at weight 1, then
#: ``medicaid_slcsp_state_denominator.py:30-33``).  It returns every node of
#: the net-income tree (:data:`~.policyengine_us._TREE_SOURCE`) per
#: household, omitting arrays that are zero for every household, the memo
#: variables per person or household, the state per household, and the
#: time and peak resident memory of each simulation.
_POPULATION_SOURCE = bridge._INSTALLATION_SOURCE + bridge._TREE_SOURCE + r"""
import resource
import tempfile
import time

_started = time.perf_counter()
job = json.load(sys.stdin)
year = int(job["year"])
period = str(year)
expand = set(job["expand"])
root = job["root"]

import numpy as np
import policyengine_us
from policyengine_core.data import Dataset
from policyengine_core.periods import period as make_period
from policyengine_core.reforms import Reform
from policyengine_us import Microsimulation
from policyengine_us.system import system as default_system

import_seconds = time.perf_counter() - _started
at = make_period(period)


def peak_rss_bytes():
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(usage if sys.platform == "darwin" else usage * 1024)


def reform_for(overrides):
    return Reform.from_dict(
        {
            path: {f"{year}-01-01.{year}-12-31": value}
            for path, value in overrides.items()
        },
        country_id="us",
    )


def write_dataset(arrays, directory, name):
    data = {}
    for variable, by_period in arrays.items():
        dtype = job["dtypes"][variable]
        data[variable] = {
            key: np.asarray(values, dtype=dtype)
            for key, values in by_period.items()
        }
    default = default_system.variables[
        "medicare_quarters_of_coverage"
    ].default_value
    for key, values in data["medicare_quarters_of_coverage"].items():
        data["medicare_quarters_of_coverage"][key] = np.where(
            values < 0, default, values
        )
    dataset_class = type(
        "PopulationDataset",
        (Dataset,),
        {
            "name": name,
            "label": name,
            "data_format": Dataset.TIME_PERIOD_ARRAYS,
            "time_period": period,
            "file_path": Path(directory) / f"{name}.h5",
        },
    )
    dataset = dataset_class()
    dataset.save_dataset(data)
    return dataset


def check_membership(sim, arrays):
    # Each group population's members must be the dataset's (core maps a
    # person's unit id to the unit's position, simulation_builder.py:
    # 284-290), with one role per person, not one per unit.
    people = sim.populations["person"].count
    for kind in job["groups"]:
        population = sim.populations[kind]
        expected = np.asarray(arrays[f"person_{kind}_id"][period]) - 1
        got = np.asarray(population.members_entity_id)
        if not np.array_equal(got, expected):
            raise ValueError(f"{kind}: members differ from the dataset's")
        roles = np.asarray(population.members_role)
        if roles.shape != (people,) or any(
            role.key != "member" for role in roles.tolist()
        ):
            raise ValueError(f"{kind}: not one member role per person")


def pin_household_medicaid(sim):
    pinned = (
        "medicaid_slcsp_state_average_cost_index",
        "medicaid_slcsp_state_denominator",
    )
    for name in pinned:
        if sim.get_holder(name).get_known_periods():
            raise ValueError(f"{name} was computed before it was pinned")
    index = np.asarray(
        sim.calculate("medicaid_slcsp_cost_index", period, use_weights=False)
    )
    for name in pinned:
        if sim.get_holder(name).get_known_periods():
            raise ValueError(f"{name} was computed before it was pinned")
    members = np.asarray(sim.populations["household"].members_entity_id)
    count = sim.populations["household"].count
    weight = np.ones_like(index)
    positive = index > 0
    weighted_positive = weight * positive
    weighted_index = weight * index * positive
    household_weight = np.zeros(count, dtype=weighted_positive.dtype)
    household_index = np.zeros(count, dtype=weighted_index.dtype)
    np.add.at(household_weight, members, weighted_positive)
    np.add.at(household_index, members, weighted_index)
    state_weight = household_weight.astype(float)[members]
    state_index = household_index.astype(float)[members]
    average = np.divide(
        state_index,
        state_weight,
        out=np.ones_like(index),
        where=state_weight > 0,
    )
    sim.set_input(pinned[0], period, average)
    stored = np.asarray(sim.calculate(pinned[0], period, use_weights=False))
    person = sim.populations["person"]
    state_code = person.household("state_code", at)
    totals = sim.tax_benefit_system.get_parameters_at_instant(
        at
    ).calibration.gov.hhs.medicaid.totals
    sim.set_input(pinned[1], period, totals.enrollment[state_code] * stored)


def as_list(values):
    array = values
    if hasattr(array, "decode_to_str"):
        return [str(v) for v in array.decode_to_str()]
    array = np.asarray(array)
    if array.dtype.kind in "OUS":
        return [str(v) for v in array]
    return [float(v) for v in array.astype(float)]


systems = {}
runs = []
with tempfile.TemporaryDirectory() as directory:
    datasets = {
        scenario["name"]: write_dataset(
            scenario["dataset"], directory, f"scenario_{i}"
        )
        for i, scenario in enumerate(job["scenarios"])
    }
    first = datasets[job["scenarios"][0]["name"]]
    for variant in job["variants"]:
        overrides = variant["parameter_overrides"]
        key = json.dumps(overrides, sort_keys=True)
        if overrides and key not in systems:
            systems[key] = Microsimulation(
                dataset=first, reform=reform_for(overrides)
            ).tax_benefit_system
        for scenario in job["scenarios"]:
            started = time.perf_counter()
            dataset = datasets[scenario["name"]]
            if overrides:
                sim = Microsimulation(
                    dataset=dataset, tax_benefit_system=systems[key]
                )
            else:
                sim = Microsimulation(dataset=dataset)
            if sim.baseline is not None:
                raise ValueError("a scenario simulation has a baseline branch")
            check_membership(sim, scenario["dataset"])
            built = time.perf_counter()
            if job["medicaid_valuation"] == "household":
                pin_household_medicaid(sim)
            system = sim.tax_benefit_system
            params = system.parameters(f"{year}-01-01")
            tree = build_tree(system, params)
            names = set(tree)
            for parts in tree.values():
                names.update(child for child, _ in parts)
            values = {}
            zero = []
            for name in sorted(names):
                array = np.asarray(
                    sim.calculate(
                        name, period, map_to="household", use_weights=False
                    ),
                    dtype=float,
                )
                if array.any():
                    values[name] = [float(v) for v in array]
                else:
                    zero.append(name)
            person_memo = {}
            for name in job["person_memo"]:
                variable, when = memo_period(name)
                person_memo[name] = as_list(
                    sim.calculate(variable, when, use_weights=False)
                )
            household_memo = {}
            for name in job["household_memo"]:
                variable, when = memo_period(name)
                household_memo[name] = as_list(
                    sim.calculate(
                        variable, when, map_to="household", use_weights=False
                    )
                )
            states = as_list(
                sim.calculate("state_code", period, use_weights=False)
            )
            done = time.perf_counter()
            runs.append(
                {
                    "variant": variant["name"],
                    "scenario": scenario["name"],
                    "tree": tree,
                    "values": values,
                    "zero": zero,
                    "person_memo": person_memo,
                    "household_memo": household_memo,
                    "state_code": states,
                    "timings": {
                        "build_seconds": built - started,
                        "calculate_seconds": done - built,
                        "total_seconds": done - started,
                        "peak_rss_bytes_after": peak_rss_bytes(),
                    },
                }
            )
            del sim
json.dump(
    {
        "policyengine_us_version": metadata.version("policyengine-us"),
        "policyengine_core_version": metadata.version("policyengine-core"),
        "policyengine_us_package": policyengine_us.__file__,
        "installation": installation(),
        "import_seconds": import_seconds,
        "peak_rss_bytes": peak_rss_bytes(),
        "platform": sys.platform,
        "runs": runs,
    },
    sys.stdout,
)
"""


@dataclass(frozen=True)
class PopulationRun:
    """Every simulation of one :func:`run_population` call.

    ``values[variant][scenario][name]`` is node ``name`` of the net-income
    tree per household (float64 of policyengine-us's float32);
    ``person_memo`` and ``household_memo`` hold the memo variables the same
    way.  ``trees[variant]`` is the variant's component tree (the scenarios
    of a variant share it).  ``timings`` holds each simulation's build and
    calculation seconds and the child's peak resident memory after it;
    ``peak_rss_bytes`` is the child's peak, imports included.
    """

    trees: Mapping[str, bridge.ComponentTree]
    values: Mapping[str, Mapping[str, Mapping[str, np.ndarray]]]
    person_memo: Mapping[str, Mapping[str, Mapping[str, np.ndarray]]]
    household_memo: Mapping[str, Mapping[str, Mapping[str, np.ndarray]]]
    timings: Mapping[str, Mapping[str, Mapping[str, float]]]
    import_seconds: float
    peak_rss_bytes: int
    wall_seconds: float
    medicaid_valuation: str
    parameter_overrides: Mapping[str, Mapping[str, Any]]
    policyengine_us_version: str
    policyengine_core_version: str
    python: str
    installation: bridge.PolicyEngineUSInstallation | None = None
    source: Mapping[str, Any] | None = None


def _memo_array(values: list[Any]) -> np.ndarray:
    if values and isinstance(values[0], str):
        return np.asarray(values, dtype=object)
    return np.asarray(values, dtype=float)


def run_population(
    scenarios: Mapping[str, PopulationFrame],
    *,
    year: int,
    variants: Mapping[str, Mapping[str, Any]] | None = None,
    person_memo: Sequence[str] = (),
    household_memo: Sequence[str] = (),
    medicaid_valuation: str = "household",
    python: str | os.PathLike | None = None,
    expand: Sequence[str] = bridge.DEFAULT_EXPAND,
    root: str = bridge.ROOT_VARIABLE,
    timeout: float = 7_200.0,
    require_published: bool = True,
    verify_files: bool = True,
    expected_package_record_digest: str | None = None,
) -> PopulationRun:
    """One weighted simulation per scenario and variant (module docstring).

    ``scenarios`` maps a name to a frame; every frame must have the first's
    structure (:meth:`PopulationFrame.same_structure`), so scenarios differ
    only in amounts.  ``variants`` maps a name to parameter overrides for
    the whole year (default: one variant, ``"default"``, with none).  The
    imported ``policyengine-us`` is checked as in
    :func:`~.policyengine_us.run_policyengine_us` and must not change
    between the check and the run.  Refuses a run whose derived state
    differs from a household's, or whose scenarios within a variant have
    different trees.
    """

    if isinstance(year, bool) or not isinstance(year, int):
        raise TypeError(f"year must be an integer, not {year!r}")
    if medicaid_valuation not in MEDICAID_VALUATIONS:
        raise ValueError(
            f"medicaid_valuation must be one of {MEDICAID_VALUATIONS}"
        )
    if not scenarios:
        raise ValueError("run_population needs at least one scenario")
    frames = dict(scenarios)
    first = next(iter(frames.values()))
    for name, frame in frames.items():
        if not isinstance(name, str) or not name:
            raise ValueError("scenario names must be nonempty strings")
        if not isinstance(frame, PopulationFrame):
            raise TypeError("scenarios must map names to PopulationFrame")
        if not frame.same_structure(first):
            raise ValueError(
                f"scenario {name!r} differs from the first in more than "
                "its amounts"
            )
    variants = dict(variants or {"default": {}})
    for name in variants:
        if not isinstance(name, str) or not name:
            raise ValueError("variant names must be nonempty strings")
    interpreter = bridge._interpreter(python)
    installation, source = bridge._checked_installation(
        interpreter,
        require_published=require_published,
        verify_files=verify_files,
        expected_package_record_digest=expected_package_record_digest,
    )
    job = {
        "year": year,
        "root": root,
        "expand": list(expand),
        "medicaid_valuation": medicaid_valuation,
        "groups": list(GROUP_ENTITIES),
        "dtypes": _DTYPES,
        "variants": [
            {"name": name, "parameter_overrides": dict(overrides)}
            for name, overrides in variants.items()
        ],
        "scenarios": [
            {
                "name": name,
                "dataset": {
                    variable: {
                        key: values.tolist() for key, values in by.items()
                    }
                    for variable, by in frame.to_dataset(year).items()
                },
            }
            for name, frame in frames.items()
        ],
        "person_memo": list(person_memo),
        "household_memo": list(household_memo),
    }
    started = time.perf_counter()
    payload = bridge._run_child(
        interpreter, _POPULATION_SOURCE, json.dumps(job), timeout
    )
    wall = time.perf_counter() - started
    ran = bridge.PolicyEngineUSInstallation.from_payload(
        interpreter, payload["installation"]
    )
    if ran != installation:
        raise bridge.PolicyEngineUSUnavailable(
            "policyengine-us changed between the source check and the run"
        )
    n_households = first.n_households
    trees: dict[str, bridge.ComponentTree] = {}
    values: dict[str, dict[str, dict[str, np.ndarray]]] = {}
    people: dict[str, dict[str, dict[str, np.ndarray]]] = {}
    households: dict[str, dict[str, dict[str, np.ndarray]]] = {}
    timings: dict[str, dict[str, dict[str, float]]] = {}
    for raw in payload["runs"]:
        variant, scenario = raw["variant"], raw["scenario"]
        if tuple(raw["state_code"]) != first.state:
            raise ValueError(
                f"{variant}/{scenario}: the derived states differ from the "
                "households' (check STATE_FIPS)"
            )
        tree = bridge.ComponentTree(
            root=root,
            children={
                name: tuple((str(c), int(s)) for c, s in parts)
                for name, parts in raw["tree"].items()
            },
        )
        if variant in trees and trees[variant] != tree:
            raise bridge.DefinitionDriftError(
                f"{variant}: the scenarios' trees differ"
            )
        trees[variant] = tree
        node_values = {
            name: np.zeros(n_households) for name in raw["zero"]
        } | {
            name: np.asarray(array, dtype=float)
            for name, array in raw["values"].items()
        }
        for name, array in node_values.items():
            if len(array) != n_households:
                raise ValueError(f"{name}: not one value per household")
        values.setdefault(variant, {})[scenario] = node_values
        people.setdefault(variant, {})[scenario] = {
            name: _memo_array(array)
            for name, array in raw["person_memo"].items()
        }
        households.setdefault(variant, {})[scenario] = {
            name: _memo_array(array)
            for name, array in raw["household_memo"].items()
        }
        timings.setdefault(variant, {})[scenario] = dict(raw["timings"])
    expected = {(v, s) for v in variants for s in frames}
    got = {(r["variant"], r["scenario"]) for r in payload["runs"]}
    if got != expected:
        raise bridge.PolicyEngineUSUnavailable(
            "the runner returned other runs"
        )
    return PopulationRun(
        trees=trees,
        values=values,
        person_memo=people,
        household_memo=households,
        timings=timings,
        import_seconds=float(payload["import_seconds"]),
        peak_rss_bytes=int(payload["peak_rss_bytes"]),
        wall_seconds=wall,
        medicaid_valuation=medicaid_valuation,
        parameter_overrides={k: dict(v) for k, v in variants.items()},
        policyengine_us_version=str(payload["policyengine_us_version"]),
        policyengine_core_version=str(payload["policyengine_core_version"]),
        python=str(interpreter),
        installation=installation,
        source=source,
    )


# ---------------------------------------------------------------------------
# Levels of government
# ---------------------------------------------------------------------------
#: The levels of government a leaf of the net-income tree is paid or
#: collected by, in table order.  ``health`` holds the health leaves of the
#: with-health variant (Medicaid, CHIP, Medicare Savings Programs, premium
#: credits and health costs); their federal and state split comes from
#: policyengine-us's own cost-share variables, reported separately.
#: ``market_income`` holds the leaves of ``household_market_income`` but
#: the Alaska dividend (:data:`_STATE_MARKET_LEAVES`); it is not a level of
#: government, and no reform here changes it.
LEVELS: tuple[str, ...] = (
    "federal",
    "state",
    "local",
    "health",
    "market_income",
)
LEVEL_LABELS: dict[str, str] = {
    "federal": "Federal",
    "state": "State",
    "local": "Local",
    "health": "Health coverage (federal and state)",
    "market_income": "Market income",
}
#: Leaves outside the state, local, health and market-income subtrees that
#: are federal programs or taxes.  Any other leaf is unclassified, and
#: :func:`level_for` returns ``None``; a population whose unclassified leaf
#: changes is refused (:func:`decompose_population`).
_FEDERAL_LEAVES = frozenset(
    {
        "social_security",
        "ssi",
        "snap",
        "commodity_supplemental_food_program",
        "wic",
        "free_school_meals",
        "reduced_price_school_meals",
        "housing_assistance",
        "acp",
        "ebb",
        "income_tax_before_refundable_credits",
        "income_tax_refundable_credits",
        "employee_payroll_tax",
        "self_employment_tax",
        "flat_tax",
    }
)
#: ``household_tax_before_refundable_credits`` adds these local taxes
#: (``household_tax_before_refundable_credits.py:17-18``).
_LOCAL_LEAVES = frozenset(
    {"local_income_tax_before_refundable_credits", "local_occupational_tax"}
)
#: Aggregates whose every leaf is a state program or tax:
#: ``household_state_benefits`` ("Benefits paid by State agencies",
#: ``household_state_benefits.py:9-11``),
#: ``household_state_tax_before_refundable_credits`` (state income and use
#: tax, ``household_state_tax_before_refundable_credits.py:10``) and
#: ``household_refundable_state_tax_credits``.
_STATE_AGGREGATES = frozenset(
    {
        "household_state_benefits",
        "household_state_tax_before_refundable_credits",
        "household_refundable_state_tax_credits",
    }
)


#: Leaves of ``household_market_income`` paid by a government:
#: the Alaska Permanent Fund Dividend, which 2.18.0 lists as market income
#: (``parameters/gov/household/market_income_sources.yaml:28``), is paid by
#: the State of Alaska (``variables/gov/states/ak/dor/
#: ak_permanent_fund_dividend.py:11-13``).
_STATE_MARKET_LEAVES = frozenset({"ak_permanent_fund_dividend"})


def level_for(variable: str, path: Sequence[str]) -> str | None:
    """The level of government of a leaf reached through ``path``."""

    ancestors = set(path)
    if ancestors & _STATE_AGGREGATES or variable in _STATE_MARKET_LEAVES:
        return "state"
    health = {"household_health_benefits", "household_health_costs"}
    if ancestors & health or variable in health:
        # Unexpanded (health outside net income), each is a zero leaf.
        return "health"
    if "household_market_income" in ancestors:
        return "market_income"
    if variable in _LOCAL_LEAVES:
        return "local"
    if variable in _FEDERAL_LEAVES:
        return "federal"
    return None


# ---------------------------------------------------------------------------
# Decomposition over a population
# ---------------------------------------------------------------------------
#: Values whose magnitude is under this many dollars take the vectorized
#: path of :func:`to_cents_array` when they are float32 values.
_FAST_CENTS_LIMIT = float(2**40)


def to_cents_array(values: Any) -> np.ndarray:
    """:func:`~.policyengine_us.to_cents` of every value, exactly.

    A float32 value ``x`` has a significand of at most 24 bits, so ``100 x``
    needs at most 31 and is exact in float64; rounding it half to even
    (``np.rint``) is then the bridge's decimal rounding of the exact value.
    Any other value (or one past 2**40 dollars) takes the bridge's
    :func:`~.policyengine_us.to_cents`.  Refuses a non-finite value.
    Returns int64 cents.
    """

    array = np.asarray(values, dtype=np.float64)
    if not np.isfinite(array).all():
        raise ValueError("amounts must be finite")
    single = array.astype(np.float32).astype(np.float64) == array
    fast = single & (np.abs(array) < _FAST_CENTS_LIMIT)
    out = np.empty(array.shape, dtype=np.int64)
    out[fast] = np.rint(array[fast] * 100.0).astype(np.int64)
    for i in np.flatnonzero(~fast):
        cents = bridge.to_cents(float(array[i]))
        if abs(cents) >= 2**62:
            raise ValueError("an amount is too large for int64 cents")
        out[i] = cents
    return out


@dataclass(frozen=True)
class PopulationDecomposition:
    """Every household's leaves in cents, as :func:`~.policyengine_us.decompose`.

    ``leaves[j]`` is ``(variable, path, sign, category, level)`` for the
    ``j``-th leaf of ``tree.leaves()``; ``baseline_cents[j]`` and
    ``reform_cents[j]`` are its signed contribution per household (int64),
    so a tax enters negative.  ``reported_*`` are policyengine-us's own
    root values per household.
    """

    tree: bridge.ComponentTree
    leaves: tuple[tuple[str, tuple[str, ...], int, str, str | None], ...]
    baseline_cents: tuple[np.ndarray, ...]
    reform_cents: tuple[np.ndarray, ...]
    reported_baseline_net: np.ndarray
    reported_reform_net: np.ndarray
    max_aggregate_gap: float

    @property
    def n_households(self) -> int:
        return len(self.reported_baseline_net)

    def change_cents(self, j: int) -> np.ndarray:
        return self.reform_cents[j] - self.baseline_cents[j]

    @property
    def baseline_net_cents(self) -> np.ndarray:
        return _sum_int(self.baseline_cents, self.n_households)

    @property
    def reform_net_cents(self) -> np.ndarray:
        return _sum_int(self.reform_cents, self.n_households)

    @property
    def net_change_cents(self) -> np.ndarray:
        return self.reform_net_cents - self.baseline_net_cents

    @property
    def reported_gap_cents(self) -> np.ndarray:
        reported = to_cents_array(self.reported_reform_net) - to_cents_array(
            self.reported_baseline_net
        )
        return reported - self.net_change_cents

    def household(self, h: int) -> bridge.Decomposition:
        """Household ``h`` as the bridge's own :class:`Decomposition`."""

        return bridge.Decomposition(
            components=tuple(
                bridge.Component(
                    variable=name,
                    path=path,
                    sign=sign,
                    category=category,
                    baseline_cents=int(self.baseline_cents[j][h]),
                    reform_cents=int(self.reform_cents[j][h]),
                )
                for j, (name, path, sign, category, _) in enumerate(
                    self.leaves
                )
            ),
            baseline_net_cents=int(self.baseline_net_cents[h]),
            reform_net_cents=int(self.reform_net_cents[h]),
            reported_baseline_net=float(self.reported_baseline_net[h]),
            reported_reform_net=float(self.reported_reform_net[h]),
            max_aggregate_gap=self.max_aggregate_gap,
        )

    def changed_leaves(self) -> list[int]:
        """Leaves that change for some household."""

        return [
            j
            for j in range(len(self.leaves))
            if (self.change_cents(j) != 0).any()
        ]


def _sum_int(arrays: Sequence[np.ndarray], n: int) -> np.ndarray:
    total = np.zeros(n, dtype=np.int64)
    for array in arrays:
        total = total + array
    return total


def _aggregate_gaps(
    tree: bridge.ComponentTree, values: Mapping[str, np.ndarray], n: int
) -> np.ndarray:
    """Per household, the largest |aggregate - sum of parts| (inf if any
    value is not finite), each sum by ``math.fsum`` as the bridge's."""

    worst = np.zeros(n)
    for name in tree.aggregates():
        parts = tree.children[name]
        columns = [
            sign * np.asarray(values[part], dtype=float)
            for part, sign in parts
        ]
        total = np.asarray(values[name], dtype=float)
        finite = np.isfinite(total)
        for column in columns:
            finite &= np.isfinite(column)
        nonzero = [c for c in columns if c.any()]
        stacked = (
            np.vstack(nonzero).T.tolist()
            if nonzero
            else [[] for _ in range(n)]
        )
        sums = np.asarray([math.fsum(row) for row in stacked])
        gap = np.where(finite, np.abs(total - sums), np.inf)
        gap = np.where(np.isfinite(gap), gap, np.inf)
        worst = np.maximum(worst, gap)
    return worst


def decompose_population(
    tree: bridge.ComponentTree,
    baseline: Mapping[str, Any],
    reform: Mapping[str, Any],
    *,
    reform_tree: bridge.ComponentTree | None = None,
    tolerance: float = 0.5,
    expected_definition: Sequence[tuple[str, int]] | None = (
        bridge.NET_INCOME_DEFINITION
    ),
    require_classified_changes: bool = True,
) -> PopulationDecomposition:
    """:func:`~.policyengine_us.decompose` for every household at once.

    ``baseline[name]`` and ``reform[name]`` are one value per household for
    every node of ``tree``.  The checks are the bridge's, household by
    household: the trees agree (:class:`~.policyengine_us.
    DefinitionDriftError`), the root's parts are ``expected_definition``,
    every aggregate is the signed sum of its parts within ``tolerance`` and
    every value is finite (:class:`~.policyengine_us.AggregateMismatchError`),
    and policyengine-us's own net change is within ``tolerance`` of the
    definition's.  Leaves are rounded to cents (:func:`to_cents_array`), so
    every household's leaf changes sum exactly to its net change.  With
    ``require_classified_changes``, a leaf that changes for any household
    must have a level of government (:func:`level_for`), else
    :class:`UnclassifiedChangeError`.
    """

    if reform_tree is not None and reform_tree != tree:
        raise bridge.DefinitionDriftError("baseline and reform trees differ")
    if expected_definition is not None:
        observed = tuple(tree.children[tree.root])
        if observed != tuple(tuple(item) for item in expected_definition):
            raise bridge.DefinitionDriftError(
                f"{tree.root} is {observed}, not the definition the bridge "
                f"was checked against ({tuple(expected_definition)})"
            )
    lengths = {
        len(np.atleast_1d(np.asarray(values[name])))
        for values in (baseline, reform)
        for name in values
    }
    if len(lengths) != 1:
        raise ValueError("every node needs one value per household")
    n = lengths.pop()
    base = {
        k: np.asarray(v, dtype=float).reshape(n) for k, v in baseline.items()
    }
    ref = {k: np.asarray(v, dtype=float).reshape(n) for k, v in reform.items()}
    gaps = []
    for label, values in (("baseline", base), ("reform", ref)):
        gap = _aggregate_gaps(tree, values, n)
        if not np.isfinite(gap).all():
            raise bridge.AggregateMismatchError(
                f"{label}: an aggregate or one of its parts is not finite"
            )
        if (gap > tolerance).any():
            raise bridge.AggregateMismatchError(
                f"{label}: an aggregate differs from its parts by "
                f"{float(gap.max()):.4f}"
            )
        gaps.append(float(gap.max()) if n else 0.0)
    leaves = tuple(
        (
            name,
            path,
            sign,
            bridge.category_for(name, path),
            level_for(name, path),
        )
        for name, path, sign in tree.leaves()
    )
    baseline_cents = tuple(
        _frozen(sign * to_cents_array(base[name]))
        for name, _, sign, _, _ in leaves
    )
    reform_cents = tuple(
        _frozen(sign * to_cents_array(ref[name]))
        for name, _, sign, _, _ in leaves
    )
    decomposition = PopulationDecomposition(
        tree=tree,
        leaves=leaves,
        baseline_cents=baseline_cents,
        reform_cents=reform_cents,
        reported_baseline_net=_frozen(base[tree.root].copy()),
        reported_reform_net=_frozen(ref[tree.root].copy()),
        max_aggregate_gap=max(gaps),
    )
    if (
        np.abs(decomposition.reported_gap_cents) > round(tolerance * 100)
    ).any():
        worst = int(np.abs(decomposition.reported_gap_cents).max())
        raise bridge.AggregateMismatchError(
            f"{tree.root}'s reported change differs from its definition by "
            f"{worst} cents"
        )
    if require_classified_changes:
        unclassified = sorted(
            {
                leaves[j][0]
                for j in decomposition.changed_leaves()
                if leaves[j][4] is None
            }
        )
        if unclassified:
            raise UnclassifiedChangeError(
                f"these leaves change but have no level of government: "
                f"{unclassified}"
            )
    return decomposition


# ---------------------------------------------------------------------------
# Exact weighted sums
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ExactWeights:
    """Household weights as exact integers over one power-of-two scale.

    Every finite float is a dyadic rational, so ``weight = numerators[h] /
    denominator`` exactly, and a weighted sum of integer cents is an exact
    :class:`~fractions.Fraction` of dollars.  Linear, so any partition of
    the leaves (categories, levels) sums exactly to the weighted net change.
    """

    numerators: tuple[int, ...]
    denominator: int

    @classmethod
    def from_floats(cls, weights: Iterable[float]) -> ExactWeights:
        fractions = []
        for weight in weights:
            value = float(weight)
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"weights must be finite and >= 0: {weight}")
            fractions.append(Fraction(value))
        denominator = 1
        for fraction in fractions:
            denominator = max(denominator, fraction.denominator)
        return cls(
            tuple(
                f.numerator * (denominator // f.denominator) for f in fractions
            ),
            denominator,
        )

    def __len__(self) -> int:
        return len(self.numerators)

    def total_weight(self, mask: Any = None) -> Fraction:
        chosen = self._chosen(mask)
        return Fraction(
            sum(self.numerators[h] for h in chosen), self.denominator
        )

    def dollars(self, cents: Any, mask: Any = None) -> Fraction:
        """The weighted sum of integer ``cents``, in dollars, exactly."""

        values = np.asarray(cents)
        if values.dtype.kind not in "iu":
            raise TypeError("cents must be integers")
        if len(values) != len(self.numerators):
            raise ValueError("one amount per household")
        chosen = self._chosen(mask)
        total = sum(
            self.numerators[h] * int(values[h]) for h in chosen if values[h]
        )
        return Fraction(total, 100 * self.denominator)

    def _chosen(self, mask: Any) -> list[int]:
        if mask is None:
            return list(range(len(self.numerators)))
        flags = np.asarray(mask, dtype=bool)
        if len(flags) != len(self.numerators):
            raise ValueError("one flag per household")
        return np.flatnonzero(flags).tolist()


# ---------------------------------------------------------------------------
# Deciles
# ---------------------------------------------------------------------------
def decile_ranks(income: Any, weights: Any) -> np.ndarray:
    """policyengine-us's ``household_income_decile`` rule, recomputed.

    ``household_income_decile.py:12-21`` ranks net income weighted by
    household weight times people and sets negative incomes to -1; the
    rank is microdf's: each value's rank is the cumulative weight of the
    values at or below it, over the total, and the decile is
    ``min(ceil(10 * rank), 10)`` (``microdf/microseries.py:899-939,
    969-972``, microdf 1.5.11).  Pass policyengine-us's float32 weights for an exact match.
    """

    values = np.asarray(income, dtype=float)
    w = np.asarray(weights, dtype=float)
    if values.shape != w.shape or values.ndim != 1:
        raise ValueError("one weight per income")
    total = w.sum()
    if total <= 0:
        raise ValueError("the weights must have a positive total")
    order = np.argsort(values, kind="mergesort")
    sorted_values = values[order]
    cumulative = np.cumsum(w[order])
    group_end = np.searchsorted(sorted_values, sorted_values, side="right") - 1
    ranks = cumulative[group_end][np.argsort(order, kind="mergesort")]
    ranks = np.where(ranks / total > 1.0, 1.0, ranks / total)
    deciles = np.minimum(np.ceil(ranks * 10), 10).astype(np.int64)
    return np.where(values < 0, -1, deciles)
