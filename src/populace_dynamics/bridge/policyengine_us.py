"""Bridge Microcosm benefit amounts to PolicyEngine-US's tax-benefit model.

Microcosm computes Social Security amounts (a PIA from an earnings history,
a reform PIA, statutory COLAs).  PolicyEngine-US computes what those
amounts become after federal and state taxes and means-tested transfers.
This module joins the two without importing ``policyengine_us``:

1. **Household to situation.**  :class:`BridgePerson` and
   :class:`BridgeHousehold` describe people (age, Social Security by type,
   earnings, pension and other income, liquid assets, rent) and their
   tax-unit, SPM-unit, marital-unit, family and household membership.
   :func:`to_situation` writes a PolicyEngine-US situation dictionary.
   ``social_security_retirement`` and the other three Social Security
   variables have no formula in PolicyEngine-US (``variables/gov/ssa/ss/
   social_security_retirement.py:4-10`` in policyengine-us 2.18.0), so the
   amounts Microcosm computes enter as inputs and PolicyEngine-US adds them
   in ``social_security`` (``social_security.py:11-14``).
2. **Runner.**  :func:`run_policyengine_us` sends situations as JSON to a
   separate interpreter that has ``policyengine-us`` installed (located by
   ``POPULACE_DYNAMICS_PE_US_PYTHON``, the subprocess discipline of
   ``scripts/build_aux_benefit_examples.py``).  The child reads the
   component tree of ``household_net_income`` from the model itself and
   returns every node's household value.
3. **Source check.**  Before running, :func:`inspect_installation` asks the
   interpreter which ``policyengine-us`` it imports and where it came from,
   and :func:`check_published_source` refuses a source that is not
   published: a git checkout whose revision no ``origin`` branch contains,
   or whose tracked files are modified, and any VCS or archive install.
   :func:`verify_record` checks the installed files against the
   distribution's RECORD.
4. **Decomposition.**  :func:`decompose` turns a baseline and a reform run
   into leaf components whose changes sum exactly (in integer cents) to
   the change in ``household_net_income`` as its definition computes it,
   after checking every aggregate against the sum of its parts.
5. **Float32 guard.**  :func:`trace_policyengine_us` reruns cases with
   PolicyEngine-US's tracer on, and :func:`uncaused_changes` finds every
   variable that changes between two runs although no variable it read
   changed by more than float noise (a cent, or four float32 steps at the
   read's size where that is more): a step at a bracket edge taken on
   float32 noise, not a mechanism.

``household_net_income`` in policyengine-us 2.18.0
(``variables/household/income/household/household_net_income.py:10-18``)
adds ``household_market_income``, ``household_benefits`` and
``household_refundable_tax_credits`` and subtracts
``household_tax_before_refundable_credits`` and ``household_health_costs``.
``household_benefits`` includes ``household_health_benefits`` (Medicaid at
cost, Medicare Savings Programs, CHIP, premium tax credits), but that
variable returns zero unless ``gov.simulation.
include_health_benefits_in_net_income`` is true
(``household_health_benefits.py:17-22``), and the parameter's default is
false (``parameters/gov/simulation/
include_health_benefits_in_net_income.yaml``).  So by default net income
excludes health coverage; a caller can switch it on through
``RunCase.parameter_overrides``.

What this module does not do: compute any Social Security amount (callers
pass them), run over a projected population, or edit PolicyEngine-US.
"""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import math
import os
import re
import subprocess
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from decimal import ROUND_FLOOR, ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

__all__ = [
    "AMOUNT_FIELDS",
    "AggregateMismatchError",
    "BridgeHousehold",
    "BridgePerson",
    "CATEGORY_LABELS",
    "CATEGORY_ORDER",
    "CENT_TOLERANCE",
    "Component",
    "ComponentTree",
    "DEFAULT_EXPAND",
    "DEFAULT_PE_US_PYTHON",
    "Decomposition",
    "DefinitionDriftError",
    "NET_INCOME_DEFINITION",
    "PE_US_PYTHON_ENV",
    "PolicyEngineRun",
    "PolicyEngineUSInstallation",
    "PolicyEngineUSUnavailable",
    "ROOT_VARIABLE",
    "RunCase",
    "RunResult",
    "FLOAT32_NOISE_STEPS",
    "SMALL_CHANGE_CENTS",
    "STATE_FIPS",
    "TraceNode",
    "UnpublishedSourceError",
    "carry_pia_forward",
    "category_for",
    "check_published_source",
    "cola_rates_from_cpi_w",
    "decompose",
    "float32_step",
    "floor_to_dime",
    "inspect_installation",
    "package_record_digest",
    "person_inputs_from_situation",
    "resolve_pe_us_python",
    "run_policyengine_us",
    "small_changes",
    "to_cents",
    "to_situation",
    "trace_policyengine_us",
    "uncaused_changes",
    "verify_record",
]

#: The environment variable naming the interpreter that has
#: ``policyengine-us`` installed (as ``scripts/build_aux_benefit_examples.py``
#: uses it).
PE_US_PYTHON_ENV = "POPULACE_DYNAMICS_PE_US_PYTHON"
#: The fallback when the environment variable is unset: a virtual
#: environment holding the policyengine-us 2.18.0 release from PyPI
#: (``uv venv`` then ``uv pip install policyengine-us==2.18.0``).
DEFAULT_PE_US_PYTHON = Path("~/.venvs/policyengine-us-2.18.0/bin/python")

#: The variable the decomposition explains.
ROOT_VARIABLE = "household_net_income"
#: ``household_net_income``'s definition in policyengine-us 2.18.0
#: (``household_net_income.py:10-18``): the added and subtracted parts, in
#: order.  :func:`decompose` refuses a run whose tree differs (a tripwire for
#: a PolicyEngine-US change the bridge has not been checked against).
NET_INCOME_DEFINITION: tuple[tuple[str, int], ...] = (
    ("household_market_income", 1),
    ("household_benefits", 1),
    ("household_refundable_tax_credits", 1),
    ("household_tax_before_refundable_credits", -1),
    ("household_health_costs", -1),
)
#: The aggregates the runner expands into their parts.  Every other variable
#: is a leaf (``social_security``, ``ssi``, ``snap``, each state benefit,
#: each tax).  ``household_benefits``, ``household_health_benefits`` and
#: ``household_health_costs`` are formulas; the runner mirrors their lists
#: (see :data:`_RUNNER_SOURCE`), and :func:`decompose` checks each against
#: the sum of its parts.
DEFAULT_EXPAND: tuple[str, ...] = (
    "household_net_income",
    "household_market_income",
    "household_benefits",
    "household_refundable_tax_credits",
    "household_tax_before_refundable_credits",
    "household_health_costs",
    "household_state_benefits",
    "household_health_benefits",
    "household_refundable_state_tax_credits",
    "household_state_tax_before_refundable_credits",
)

#: Census state FIPS codes (50 states and DC).  The runner returns the state
#: PolicyEngine-US derives from the code (``state_name``'s formula maps
#: ``state_fips``; ``input/geography.py:26-87``), and :func:`run_policyengine_us`
#: refuses a case whose derived state differs from the one requested.
STATE_FIPS: dict[str, int] = {
    "AL": 1,
    "AK": 2,
    "AZ": 4,
    "AR": 5,
    "CA": 6,
    "CO": 8,
    "CT": 9,
    "DE": 10,
    "DC": 11,
    "FL": 12,
    "GA": 13,
    "HI": 15,
    "ID": 16,
    "IL": 17,
    "IN": 18,
    "IA": 19,
    "KS": 20,
    "KY": 21,
    "LA": 22,
    "ME": 23,
    "MD": 24,
    "MA": 25,
    "MI": 26,
    "MN": 27,
    "MS": 28,
    "MO": 29,
    "MT": 30,
    "NE": 31,
    "NV": 32,
    "NH": 33,
    "NJ": 34,
    "NM": 35,
    "NY": 36,
    "NC": 37,
    "ND": 38,
    "OH": 39,
    "OK": 40,
    "OR": 41,
    "PA": 42,
    "RI": 44,
    "SC": 45,
    "SD": 46,
    "TN": 47,
    "TX": 48,
    "UT": 49,
    "VT": 50,
    "VA": 51,
    "WA": 53,
    "WV": 54,
    "WI": 55,
    "WY": 56,
}

#: Person amounts the bridge passes, each a PolicyEngine-US input variable
#: of the same name (annual dollars, or dollars for the asset stock).
AMOUNT_FIELDS: tuple[str, ...] = (
    "social_security_retirement",
    "social_security_disability",
    "social_security_survivors",
    "social_security_dependents",
    "employment_income",
    "taxable_private_pension_income",
    "interest_income",
    "bank_account_assets",
    "pre_subsidy_rent",
)
_MAX_AGE = 125


class PolicyEngineUSUnavailable(RuntimeError):
    """The interpreter with ``policyengine-us`` cannot be found or run."""


class AggregateMismatchError(ValueError):
    """An aggregate differs from the signed sum of its parts."""


class DefinitionDriftError(ValueError):
    """``household_net_income``'s definition is not the one the bridge read."""


class UnpublishedSourceError(RuntimeError):
    """The interpreter imports a ``policyengine-us`` that is not published."""


# ---------------------------------------------------------------------------
# Households and situations
# ---------------------------------------------------------------------------
def _check_amount(label: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be a number, not {value!r}")
    amount = float(value)
    if not math.isfinite(amount):
        raise ValueError(f"{label} must be finite, not {value!r}")
    if amount < 0:
        raise ValueError(f"{label} must be nonnegative, not {value!r}")
    return amount


@dataclass(frozen=True)
class BridgePerson:
    """One person: age and the annual amounts PolicyEngine-US takes as input.

    Every amount is nonnegative and finite.  ``medicare_quarters_of_coverage``
    is PolicyEngine-US's input of that name (it defaults to 40 there,
    ``medicare_quarters_of_coverage.py:16``); ``None`` leaves the default.
    """

    person_id: str
    age: int
    social_security_retirement: float = 0.0
    social_security_disability: float = 0.0
    social_security_survivors: float = 0.0
    social_security_dependents: float = 0.0
    employment_income: float = 0.0
    taxable_private_pension_income: float = 0.0
    interest_income: float = 0.0
    bank_account_assets: float = 0.0
    pre_subsidy_rent: float = 0.0
    medicare_quarters_of_coverage: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.person_id, str) or not self.person_id:
            raise ValueError("person_id must be a nonempty string")
        if isinstance(self.age, bool) or not isinstance(self.age, int):
            raise TypeError(f"age must be an integer, not {self.age!r}")
        if not 0 <= self.age <= _MAX_AGE:
            raise ValueError(f"age must be 0-{_MAX_AGE}, not {self.age}")
        for name in AMOUNT_FIELDS:
            object.__setattr__(
                self, name, _check_amount(name, getattr(self, name))
            )
        quarters = self.medicare_quarters_of_coverage
        if quarters is not None:
            if isinstance(quarters, bool) or not isinstance(quarters, int):
                raise TypeError("medicare_quarters_of_coverage must be int")
            if quarters < 0:
                raise ValueError("medicare_quarters_of_coverage must be >= 0")

    def amounts(self) -> dict[str, float]:
        return {name: getattr(self, name) for name in AMOUNT_FIELDS}


def _groups(value: Iterable[Iterable[str]], label: str) -> tuple:
    # A bare string is iterable, so ("ab",) would otherwise become the group
    # ("a", "b"); a group of people must be a sequence of ids.
    if isinstance(value, str):
        raise TypeError(f"{label}: expected groups of ids, not {value!r}")
    # Read the input once: a generator would be empty the second time.
    value = tuple(value)
    for group in value:
        if isinstance(group, str):
            raise TypeError(
                f"{label}: a group must be a sequence of ids, not {group!r}"
            )
    groups = tuple(tuple(group) for group in value)
    for group in groups:
        if not group:
            raise ValueError(f"{label}: a group must have a member")
        for member in group:
            if not isinstance(member, str):
                raise TypeError(f"{label}: member {member!r} is not a str")
    return groups


@dataclass(frozen=True)
class BridgeHousehold:
    """A household and the units PolicyEngine-US needs.

    ``tax_units``, ``spm_units`` and ``marital_units`` each partition the
    people: every person is in exactly one group of each kind (a marital
    unit has one or two people).  ``families`` defaults to one family of
    everyone.  ``state`` is a two-letter code in :data:`STATE_FIPS`.

    Three flags set PolicyEngine-US inputs whose defaults would otherwise
    decide a result:

    * ``has_heating_cooling_expense`` (SPM unit): SNAP's standard utility
      allowance turns on it (``snap_utility_allowance_type.py:30,40-52`` in
      policyengine-us 2.18.0).  In 2.18.0 the variable has a formula
      (``has_heating_cooling_expense.py:21-32``); the situation sets it as
      an input, which takes the formula's place.
    * ``takes_up_housing_assistance`` (SPM unit,
      ``takes_up_housing_assistance_if_eligible``): its default is true
      (``takes_up_housing_assistance_if_eligible.py:9``), which would give
      every income-eligible renter a housing voucher.
    * ``food_preparation_allowed`` (household,
      ``living_arrangements_allow_for_food_preparation``): its default is
      false, and California's supplement adds a food allowance when it is
      false (``ca_state_supplement_food_allowance_eligible.py:12-21``).
    """

    household_id: str
    state: str
    people: tuple[BridgePerson, ...]
    tax_units: tuple[tuple[str, ...], ...]
    spm_units: tuple[tuple[str, ...], ...]
    marital_units: tuple[tuple[str, ...], ...]
    families: tuple[tuple[str, ...], ...] | None = None
    has_heating_cooling_expense: bool = False
    takes_up_housing_assistance: bool = False
    food_preparation_allowed: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.household_id, str) or not self.household_id:
            raise ValueError("household_id must be a nonempty string")
        if self.state not in STATE_FIPS:
            raise ValueError(
                f"state must be a key of STATE_FIPS, not {self.state!r}"
            )
        people = tuple(self.people)
        if not people:
            raise ValueError("a household needs at least one person")
        for person in people:
            if not isinstance(person, BridgePerson):
                raise TypeError("people must be BridgePerson instances")
        ids = [person.person_id for person in people]
        if len(set(ids)) != len(ids):
            raise ValueError(f"person ids must be unique: {ids}")
        object.__setattr__(self, "people", people)
        families = (tuple(ids),) if self.families is None else self.families
        for label in ("tax_units", "spm_units", "marital_units"):
            object.__setattr__(
                self, label, _groups(getattr(self, label), label)
            )
        object.__setattr__(self, "families", _groups(families, "families"))
        for label in ("tax_units", "spm_units", "marital_units", "families"):
            members = [m for group in getattr(self, label) for m in group]
            if sorted(members) != sorted(ids):
                raise ValueError(
                    f"{label} must place every person in exactly one group: "
                    f"people {sorted(ids)}, members {sorted(members)}"
                )
        if any(len(group) > 2 for group in self.marital_units):
            raise ValueError("a marital unit has at most two people")
        for flag in (
            "has_heating_cooling_expense",
            "takes_up_housing_assistance",
            "food_preparation_allowed",
        ):
            if not isinstance(getattr(self, flag), bool):
                raise TypeError(f"{flag} must be a bool")


def _entity_name(household_id: str, kind: str, index: int) -> str:
    return f"{household_id}_{kind}_{index + 1}"


def to_situation(household: BridgeHousehold, year: int) -> dict[str, Any]:
    """The PolicyEngine-US situation for ``household`` in ``year``.

    Every person carries ``age`` and every :data:`AMOUNT_FIELDS` amount
    (zeros included, so the inputs round-trip); the household carries
    ``state_fips`` (PolicyEngine-US derives ``state_name`` and
    ``state_code`` from it).  Deterministic: the same household and year
    give the same dictionary.
    """

    if isinstance(year, bool) or not isinstance(year, int):
        raise TypeError(f"year must be an integer, not {year!r}")
    period = str(year)
    people: dict[str, Any] = {}
    for person in household.people:
        entry: dict[str, Any] = {"age": {period: person.age}}
        for name, value in person.amounts().items():
            entry[name] = {period: value}
        if person.medicare_quarters_of_coverage is not None:
            entry["medicare_quarters_of_coverage"] = {
                period: person.medicare_quarters_of_coverage
            }
        people[person.person_id] = entry
    hid = household.household_id
    situation: dict[str, Any] = {"people": people}
    situation["tax_units"] = {
        _entity_name(hid, "tax_unit", i): {"members": list(group)}
        for i, group in enumerate(household.tax_units)
    }
    situation["spm_units"] = {
        _entity_name(hid, "spm_unit", i): {
            "members": list(group),
            "has_heating_cooling_expense": {
                period: household.has_heating_cooling_expense
            },
            "takes_up_housing_assistance_if_eligible": {
                period: household.takes_up_housing_assistance
            },
        }
        for i, group in enumerate(household.spm_units)
    }
    situation["marital_units"] = {
        _entity_name(hid, "marital_unit", i): {"members": list(group)}
        for i, group in enumerate(household.marital_units)
    }
    situation["families"] = {
        _entity_name(hid, "family", i): {"members": list(group)}
        for i, group in enumerate(household.families or ())
    }
    situation["households"] = {
        hid: {
            "members": [person.person_id for person in household.people],
            "state_fips": {period: STATE_FIPS[household.state]},
            "living_arrangements_allow_for_food_preparation": {
                period: household.food_preparation_allowed
            },
        }
    }
    return situation


def person_inputs_from_situation(
    situation: Mapping[str, Any], year: int
) -> dict[str, dict[str, float]]:
    """Read back each person's :data:`AMOUNT_FIELDS` from a situation."""

    period = str(year)
    return {
        person_id: {
            name: float(entry[name][period])
            for name in AMOUNT_FIELDS
            if name in entry
        }
        for person_id, entry in situation["people"].items()
    }


# ---------------------------------------------------------------------------
# The runner (a separate interpreter with policyengine-us)
# ---------------------------------------------------------------------------
#: Shared by every child script: which ``policyengine-us`` the interpreter
#: imports and where it came from, read with ``importlib.metadata`` and
#: ``importlib.util.find_spec`` (neither imports the package).
_INSTALLATION_SOURCE = r"""
import hashlib
import importlib.metadata as metadata
import importlib.util
import json
import platform
import sys
from pathlib import Path


def installation():
    spec = importlib.util.find_spec("policyengine_us")
    out = {
        "python_version": platform.python_version(),
        "package_dir": (
            str(Path(spec.origin).resolve().parent)
            if spec is not None and spec.origin
            else None
        ),
        "version": None,
        "core_version": None,
        "location": None,
        "record_path": None,
        "record_sha256": None,
        "direct_url": None,
        "installer": None,
    }
    try:
        out["core_version"] = metadata.version("policyengine-core")
    except metadata.PackageNotFoundError:
        pass
    try:
        dist = metadata.distribution("policyengine-us")
    except metadata.PackageNotFoundError:
        return out
    out["version"] = dist.version
    out["location"] = str(Path(dist.locate_file("")).resolve())
    for entry in dist.files or ():
        if entry.name == "RECORD" and entry.parent.name.endswith(".dist-info"):
            record = Path(dist.locate_file(entry)).resolve()
            out["record_path"] = str(record)
            out["record_sha256"] = hashlib.sha256(
                record.read_bytes()
            ).hexdigest()
    direct_url = dist.read_text("direct_url.json")
    if direct_url:
        out["direct_url"] = json.loads(direct_url)
    installer = dist.read_text("INSTALLER")
    if installer:
        out["installer"] = installer.strip()
    return out
"""

#: :func:`inspect_installation`'s child: the installation, nothing else.
_INSPECT_SOURCE = (
    _INSTALLATION_SOURCE + "\njson.dump(installation(), sys.stdout)\n"
)

#: Shared by the runner and the tracer: one simulation per case.  Cases
#: with the same parameter overrides share one tax-benefit system: the
#: reform is built once (from a throwaway simulation of the first such
#: case), and every case, the first included, passes that system as
#: ``tax_benefit_system`` with no reform, which policyengine-us shares
#: rather than rebuilds (``spm.py:830-834`` in 2.18.0).  So no case gets a
#: ``baseline`` branch that another lacks, and no case shares a simulation
#: with another: some 2.18.0 formulas aggregate over a whole simulation's
#: population (Medicaid's state-average cost index,
#: ``medicaid_slcsp_state_average_cost_index.py:14-29``), so households
#: batched into one simulation would not be independent.
_SIMULATION_SOURCE = r"""
from policyengine_us import Simulation
from policyengine_core.reforms import Reform

job = json.load(sys.stdin)
year = int(job["year"])
period = str(year)
_systems = {}


def reform_for(overrides):
    return Reform.from_dict(
        {
            path: {f"{year}-01-01.{year}-12-31": value}
            for path, value in overrides.items()
        },
        country_id="us",
    )


def simulation_for(case, trace=False):
    situation = case["situation"]
    if len(situation.get("households", {})) != 1:
        raise ValueError(f"{case['case_id']}: needs exactly one household")
    overrides = case.get("parameter_overrides") or {}
    if not overrides:
        return Simulation(situation=situation, trace=trace)
    key = json.dumps(overrides, sort_keys=True)
    if key not in _systems:
        _systems[key] = Simulation(
            situation=situation, reform=reform_for(overrides)
        ).tax_benefit_system
    return Simulation(
        situation=situation, tax_benefit_system=_systems[key], trace=trace
    )
"""

#: The component tree of the root, read from the model: a variable's
#: ``adds``/``subtracts`` (a list, or a parameter path to a list), except
#: three formula variables whose lists it mirrors from their source in
#: policyengine-us 2.18.0:
#:
#: * ``household_benefits`` (``household_benefits.py:11-17``):
#:   ``gov.household.household_benefits``, less ``housing_assistance`` when
#:   ``gov.hud.abolition``;
#: * ``household_health_benefits`` (``household_health_benefits.py:17-22``)
#:   and ``household_health_costs`` (``household_health_costs.py:16-20``):
#:   their ``gov.household`` lists when
#:   ``gov.simulation.include_health_benefits_in_net_income``, else none.
#:
#: A variable to expand with neither ``adds`` nor a mirrored list is an
#: error.  :func:`decompose` checks every aggregate's value against its
#: parts, so a wrong mirror fails loudly.  The functions read the globals
#: ``root`` and ``expand``, which each child that includes this source sets
#: from its job.  Shared by :data:`_RUNNER_SOURCE` and the population
#: runner (:mod:`populace_dynamics.bridge.population`).
_TREE_SOURCE = r"""
def parameter_list(params, path):
    node = params
    for part in path.split("."):
        node = getattr(node, part)
    return [str(item) for item in node]


def children_of(system, params, name):
    if name == "household_benefits":
        items = parameter_list(params, "gov.household.household_benefits")
        if bool(params.gov.hud.abolition):
            items = [i for i in items if i != "housing_assistance"]
        return [[item, 1] for item in items]
    if name in ("household_health_benefits", "household_health_costs"):
        if not bool(params.gov.simulation.include_health_benefits_in_net_income):
            return []
        items = parameter_list(params, "gov.household." + name)
        return [[item, 1] for item in items]
    variable = system.variables[name]
    out = []
    for attribute, sign in (("adds", 1), ("subtracts", -1)):
        parts = getattr(variable, attribute)
        if parts is None:
            continue
        if isinstance(parts, str):
            parts = parameter_list(params, parts)
        out.extend([str(part), sign] for part in parts)
    if not out:
        raise ValueError(f"{name} has no adds or subtracts to expand")
    return out


def build_tree(system, params):
    tree = {}
    pending = [root]
    while pending:
        name = pending.pop()
        if name in tree:
            continue
        tree[name] = children_of(system, params, name)
        for child, _ in tree[name]:
            if child in expand and child not in tree:
                pending.append(child)
    return tree


def memo_period(name):
    return name.split("@", 1) if "@" in name else (name, period)
"""

#: Executed by the policyengine-us interpreter.  It reads a job on stdin and
#: writes results on stdout.  For each case it builds the component tree of
#: the root from the model (:data:`_TREE_SOURCE`).  Each case runs in its
#: own simulation (see :data:`_SIMULATION_SOURCE`) and must hold exactly one
#: household.  A memo name may carry ``@period`` (for example
#: ``is_qmb_eligible@2026-01``) to read a monthly variable.
_RUNNER_SOURCE = (
    _INSTALLATION_SOURCE + _SIMULATION_SOURCE + _TREE_SOURCE + r"""
import policyengine_us

expand = set(job["expand"])
root = job["root"]


def household_value(sim, name, at):
    values = sim.calculate(name, at, map_to="household")
    if len(values) != 1:
        raise ValueError(f"{name}: expected one household, got {len(values)}")
    return float(values[0])


results = []
for case in job["cases"]:
    sim = simulation_for(case)
    system = sim.tax_benefit_system
    params = system.parameters(f"{year}-01-01")
    tree = build_tree(system, params)
    names = set(tree)
    for parts in tree.values():
        names.update(child for child, _ in parts)
    values = {name: household_value(sim, name, period) for name in sorted(names)}
    memo = {}
    for name in case.get("memo", []):
        variable, at = memo_period(name)
        memo[name] = household_value(sim, variable, at)
    states = sim.calculate("state_code", period).decode_to_str()
    results.append(
        {
            "case_id": case["case_id"],
            "state_code": [str(state) for state in states],
            "tree": tree,
            "values": values,
            "memo": memo,
        }
    )
json.dump(
    {
        "policyengine_us_version": metadata.version("policyengine-us"),
        "policyengine_core_version": metadata.version("policyengine-core"),
        "policyengine_us_package": policyengine_us.__file__,
        "installation": installation(),
        "cases": results,
    },
    sys.stdout,
)
"""
)

#: :func:`trace_policyengine_us`'s child.  Each case runs in its own
#: simulation (see :data:`_SIMULATION_SOURCE`) with PolicyEngine-US's
#: tracer on (``Simulation(..., trace=True)``); the child calculates the
#: requested variables for the year and returns every traced node once,
#: keyed ``name@period``: its value (as floats, over the variable's own
#: entity), the nodes it read (``children``) and whether the variable is
#: an input (no formula, ``adds`` or ``subtracts``).  A node calculated in
#: a branch simulation (policyengine-core's ``get_branch``; 2.18.0 computes
#: federal income tax through ``itemizing`` and ``not_itemizing`` branches)
#: is keyed ``branch:name@period``, so a branch's calculation never stands
#: in for the main one.  A node calculated again later is traced again
#: without children (its value is cached), so the entry with children is
#: kept.
_TRACE_SOURCE = _INSTALLATION_SOURCE + _SIMULATION_SOURCE + r"""
import numpy as np


def as_floats(value):
    if value is None:
        return None
    try:
        return [float(v) for v in np.asarray(value, dtype=float).ravel()]
    except (TypeError, ValueError):
        return None


def is_input(system, name):
    variable = system.variables.get(name)
    if variable is None:
        return None
    return not (variable.formulas or variable.adds or variable.subtracts)


def node_key(node):
    key = f"{node.name}@{node.period}"
    branch = getattr(node, "branch_name", "default") or "default"
    return key if branch == "default" else f"{branch}:{key}"


out = []
for case in job["cases"]:
    sim = simulation_for(case, trace=True)
    system = sim.tax_benefit_system
    for name in case["variables"]:
        sim.calculate(name, period)
    nodes = {}

    def walk(node):
        key = node_key(node)
        children = [node_key(c) for c in node.children]
        seen = nodes.get(key)
        if seen is None or (children and not seen["children"]):
            nodes[key] = {
                "value": as_floats(node.value),
                "children": children,
                "input": is_input(system, node.name),
            }
        for child in node.children:
            walk(child)

    for tree in sim.tracer.trees:
        walk(tree)
    out.append({"case_id": case["case_id"], "nodes": nodes})
json.dump({"installation": installation(), "cases": out}, sys.stdout)
"""


@dataclass(frozen=True)
class RunCase:
    """One PolicyEngine-US simulation: a situation and its options.

    ``expected_state`` is the two-letter state the situation should resolve
    to; ``memo`` names further variables to report at the household level
    (outside the decomposition; ``name@period`` reads another period);
    ``parameter_overrides`` sets parameters for the whole year (for example
    ``{"gov.simulation.include_health_benefits_in_net_income": True}``).
    """

    case_id: str
    situation: Mapping[str, Any]
    expected_state: str | None = None
    memo: tuple[str, ...] = ()
    parameter_overrides: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PolicyEngineRun:
    """One case's result: the component tree and every node's value."""

    case_id: str
    state_code: str
    tree: ComponentTree
    values: Mapping[str, float]
    memo: Mapping[str, float]


@dataclass(frozen=True)
class PolicyEngineUSInstallation:
    """Which ``policyengine-us`` an interpreter imports, and its source.

    ``package_dir`` is the directory ``import policyengine_us`` would load;
    ``location`` is the installed distribution's root (``site-packages``),
    with its RECORD file and that file's SHA-256.  ``direct_url`` is the
    distribution's ``direct_url.json`` (PEP 610): absent when the package
    was installed by name (from a package index, or a local wheel found
    with ``--find-links``), present for a VCS, local-directory (editable
    included) or direct-URL archive install.
    """

    python: str
    python_version: str
    package_dir: str | None
    version: str | None
    core_version: str | None
    location: str | None
    record_path: str | None
    record_sha256: str | None
    direct_url: Mapping[str, Any] | None
    installer: str | None

    @classmethod
    def from_payload(
        cls, python: str | os.PathLike, payload: Mapping[str, Any]
    ) -> PolicyEngineUSInstallation:
        return cls(
            python=str(python),
            python_version=str(payload.get("python_version") or ""),
            package_dir=payload.get("package_dir"),
            version=payload.get("version"),
            core_version=payload.get("core_version"),
            location=payload.get("location"),
            record_path=payload.get("record_path"),
            record_sha256=payload.get("record_sha256"),
            direct_url=payload.get("direct_url"),
            installer=payload.get("installer"),
        )

    @property
    def imports_the_distribution(self) -> bool:
        """Whether ``import policyengine_us`` loads the installed files."""

        if not (self.package_dir and self.location):
            return False
        return (
            Path(self.package_dir) == Path(self.location) / "policyengine_us"
        )

    @property
    def source_kind(self) -> str:
        """``index``, ``vcs``, ``archive``, ``directory`` or ``path``.

        ``index`` means installed by name, with no ``direct_url.json``: from
        a package index, or from a local wheel found with ``--find-links``,
        which metadata cannot tell apart.  A pinned
        :func:`package_record_digest` ties such an install to a published
        wheel.  ``path`` means the imported package is not the installed
        distribution's files (an editable install or ``PYTHONPATH``).
        """

        if not self.imports_the_distribution:
            return "path"
        if self.direct_url is None:
            return "index"
        if "vcs_info" in self.direct_url:
            return "vcs"
        if "archive_info" in self.direct_url:
            return "archive"
        return "directory"


@dataclass(frozen=True)
class RunResult:
    """Every case of one runner call and the versions that computed them."""

    runs: Mapping[str, PolicyEngineRun]
    policyengine_us_version: str
    policyengine_core_version: str
    policyengine_us_package: str
    python: str
    installation: PolicyEngineUSInstallation | None = None
    source: Mapping[str, Any] | None = None


def resolve_pe_us_python(python: str | os.PathLike | None = None) -> Path:
    """The interpreter to run: ``python``, else the environment, else default.

    Returns the path whether or not it exists; callers check.
    """

    if python:
        return Path(python).expanduser()
    env = os.environ.get(PE_US_PYTHON_ENV)
    if env:
        return Path(env).expanduser()
    return DEFAULT_PE_US_PYTHON.expanduser()


def _run_child(
    interpreter: Path, source: str, stdin: str, timeout: float
) -> dict[str, Any]:
    env = dict(os.environ)
    env.setdefault("OMP_NUM_THREADS", "1")
    try:
        proc = subprocess.run(
            [str(interpreter), "-c", source],
            input=stdin,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise PolicyEngineUSUnavailable(
            f"policyengine-us runner could not start ({interpreter}): {error}"
        ) from error
    if proc.returncode != 0:
        raise PolicyEngineUSUnavailable(
            f"policyengine-us runner failed ({interpreter}):\n"
            f"{proc.stderr[-4000:]}"
        )
    return json.loads(proc.stdout)


def _interpreter(python: str | os.PathLike | None) -> Path:
    interpreter = resolve_pe_us_python(python)
    if not interpreter.is_file():
        raise PolicyEngineUSUnavailable(
            f"no policyengine-us interpreter at {interpreter}; set "
            f"{PE_US_PYTHON_ENV}"
        )
    return interpreter


def inspect_installation(
    python: str | os.PathLike | None = None, *, timeout: float = 300.0
) -> PolicyEngineUSInstallation:
    """Ask the interpreter which ``policyengine-us`` it imports.

    Reads package metadata only (no simulation, no ``policyengine_us``
    import).  Raises :class:`PolicyEngineUSUnavailable` when the
    interpreter is missing or fails.
    """

    interpreter = _interpreter(python)
    payload = _run_child(interpreter, _INSPECT_SOURCE, "", timeout)
    return PolicyEngineUSInstallation.from_payload(interpreter, payload)


#: Git never prompts for credentials here: an unreachable or private
#: origin fails fast instead of hanging.
_GIT_ENV = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}


def _git(directory: Path, *args: str, timeout: float = 120.0) -> str:
    return subprocess.run(
        ["git", "-C", str(directory), *args],
        capture_output=True,
        text=True,
        check=True,
        timeout=timeout,
        env=_GIT_ENV,
    ).stdout.strip()


#: Untracked files under the package that cannot change a calculation:
#: bytecode caches and Finder metadata.  Any other untracked file,
#: git-ignored or not, marks the checkout modified (policyengine-core loads
#: every parameter YAML and variable module it finds on disk).
_INERT_UNTRACKED = (".pyc", ".pyo", ".DS_Store")
#: GitHub remote URLs, for ``public_origin``.  A URL cannot say whether
#: the repository is public or private, so this checks the host only.
_GITHUB_ORIGIN = re.compile(
    r"^(?:https://|ssh://git@|git@)github\.com[/:][^/]+/[^/]+?(?:\.git)?/?$"
)


def _checkout_state(package_dir: Path) -> dict[str, Any]:
    """The git state of the checkout holding ``package_dir``.

    Reachability is checked against ``origin`` as it is now (``git
    ls-remote``), not against local remote-tracking refs, which can outlive
    a deleted branch.  A remote head counts only when its commit is also in
    the local object store (``merge-base --is-ancestor`` needs it); fetch
    first if the checkout is behind.
    """

    try:
        top = Path(_git(package_dir, "rev-parse", "--show-toplevel"))
    except (OSError, subprocess.SubprocessError):
        return {"git": False}
    revision = _git(top, "rev-parse", "HEAD")
    tracked_changes = _git(
        top, "status", "--porcelain", "--untracked-files=no"
    )
    untracked = [
        path
        for path in _git(
            top, "ls-files", "--others", "--", str(package_dir)
        ).splitlines()
        if path
        and "__pycache__/" not in path
        and not path.endswith(_INERT_UNTRACKED)
    ]
    try:
        origin_url = _git(top, "remote", "get-url", "origin")
    except subprocess.SubprocessError:
        origin_url = None
    heads: list[str] = []
    origin_reachable = False
    if origin_url is not None:
        try:
            listing = _git(top, "ls-remote", "--heads", "origin")
            origin_reachable = True
        except subprocess.SubprocessError:
            listing = ""
        for line in listing.splitlines():
            sha, _, ref = line.partition("\t")
            ancestor = subprocess.run(
                ["git", "-C", str(top), "merge-base", "--is-ancestor"]
                + [revision, sha],
                capture_output=True,
                timeout=120,
                env=_GIT_ENV,
            )
            if ancestor.returncode == 0:
                heads.append(ref)
    return {
        "git": True,
        "revision": revision,
        "dirty": bool(tracked_changes or untracked),
        "untracked_package_files": untracked[:20],
        "origin_url": origin_url,
        "origin_reachable": origin_reachable,
        "origin_heads_containing": heads,
    }


def check_published_source(
    installation: PolicyEngineUSInstallation,
    *,
    require: bool = True,
    public_origin: bool = True,
) -> dict[str, Any]:
    """Describe where the imported ``policyengine-us`` came from.

    Two sources pass:

    * ``index``: installed by name, with no ``direct_url.json``.  Metadata
      cannot tell a package index from a local wheel found with
      ``--find-links``, so a caller that must know the release pins
      :func:`package_record_digest` (``run_policyengine_us``'s
      ``expected_package_record_digest``) and checks the files with
      :func:`verify_record`.
    * ``path``: a git checkout imported in place (an editable install or
      ``PYTHONPATH``) whose ``HEAD`` a head of ``origin`` contains, as
      ``git ls-remote`` reports it now, and with no modified tracked file
      or untracked package file (ignored ones included).  With
      ``public_origin`` (the default), ``origin`` must be a GitHub
      repository.

    Anything else -- a revision no ``origin`` head contains, an
    unreachable ``origin``, a modified checkout, a package directory
    outside any git checkout, or a VCS, local-directory or direct-URL
    archive install -- raises :class:`UnpublishedSourceError` when
    ``require`` is true, and is returned with ``published`` false
    otherwise.
    """

    kind = installation.source_kind
    record: dict[str, Any] = {
        "kind": kind,
        "version": installation.version,
        "core_version": installation.core_version,
        "record_sha256": installation.record_sha256,
    }
    reasons: list[str] = []
    if kind == "index":
        if not installation.record_path:
            reasons.append("the distribution has no RECORD file")
    elif kind == "path":
        if not installation.package_dir:
            reasons.append("policyengine_us is not importable")
        else:
            state = _checkout_state(Path(installation.package_dir))
            record["checkout"] = state
            if not state["git"]:
                reasons.append(
                    f"{installation.package_dir} is not in a git checkout"
                )
            else:
                if state["origin_url"] is None:
                    reasons.append("the checkout has no origin remote")
                elif public_origin and not _GITHUB_ORIGIN.match(
                    state["origin_url"]
                ):
                    reasons.append(
                        f"origin ({state['origin_url']}) is not a GitHub "
                        "repository"
                    )
                if state["origin_url"] is not None and not (
                    state["origin_reachable"]
                ):
                    reasons.append(
                        "origin could not be reached to confirm the "
                        "revision is published"
                    )
                elif not state["origin_heads_containing"]:
                    reasons.append(
                        f"revision {state['revision']} is not reachable "
                        "from any branch of origin"
                    )
                if state["dirty"]:
                    reasons.append("the checkout has uncommitted changes")
    else:
        record["direct_url"] = dict(installation.direct_url or {})
        reasons.append(
            f"a {kind} install cannot be checked against a published "
            "release here; install a release from PyPI"
        )
    record["published"] = not reasons
    record["reasons"] = reasons
    if reasons and require:
        raise UnpublishedSourceError(
            f"policyengine-us at {installation.package_dir} is not a "
            f"published source ({kind}): " + "; ".join(reasons)
        )
    return record


def _is_bytecode(path: str) -> bool:
    return "/__pycache__/" in f"/{path}" or path.endswith((".pyc", ".pyo"))


def package_record_digest(record_text: str, prefix: str) -> tuple[str, int]:
    """SHA-256 of a RECORD's sorted lines under ``prefix``, and their count.

    The installer appends its own lines (``INSTALLER``, ``REQUESTED``,
    console scripts, and with pip the bytecode it compiles) and may reorder
    the file, so the whole-file hash of an installed RECORD differs from
    the wheel's.  The sorted package lines, bytecode excluded, are the same
    in both, so this digest ties installed files to a wheel.
    """

    lines = sorted(
        line
        for line in record_text.splitlines()
        if line.startswith(prefix)
        and not _is_bytecode(next(csv.reader([line]))[0])
    )
    digest = hashlib.sha256(("\n".join(lines) + "\n").encode()).hexdigest()
    return digest, len(lines)


def verify_record(
    installation: PolicyEngineUSInstallation,
    *,
    prefix: str = "policyengine_us/",
) -> dict[str, Any]:
    """Check the installed files under ``prefix`` against the RECORD.

    Hashes every file the RECORD lists with a hash (``mismatched`` when the
    SHA-256 differs, ``missing`` when absent) and walks the installed
    directory for files the RECORD does not list (``extra``;
    policyengine-core loads every parameter YAML and variable module on
    disk, so an added file changes the model).  Bytecode is neither hashed
    nor counted as extra.  Also returns :func:`package_record_digest` of
    the RECORD.  The RECORD hash is urlsafe base64 without padding (the
    wheel format, PEP 376/427).
    """

    if not (installation.record_path and installation.location):
        raise ValueError("the installation has no RECORD to verify")
    root = Path(installation.location)
    text = Path(installation.record_path).read_text()
    checked = 0
    listed: set[str] = set()
    mismatched: list[str] = []
    missing: list[str] = []
    for row in csv.reader(io.StringIO(text)):
        if not row or not row[0].startswith(prefix):
            continue
        path, digest = row[0], row[1] if len(row) > 1 else ""
        listed.add(path)
        if not digest:
            continue
        algorithm, _, expected = digest.partition("=")
        target = root / path
        if not target.is_file():
            missing.append(path)
            continue
        actual = hashlib.new(algorithm, target.read_bytes()).digest()
        encoded = base64.urlsafe_b64encode(actual).rstrip(b"=").decode()
        checked += 1
        if encoded != expected:
            mismatched.append(path)
    extra = sorted(
        relative
        for file in (root / prefix).rglob("*")
        if file.is_file()
        and not _is_bytecode(relative := file.relative_to(root).as_posix())
        and relative not in listed
    )
    digest, lines = package_record_digest(text, prefix)
    return {
        "prefix": prefix,
        "files_checked": checked,
        "mismatched": mismatched,
        "missing": missing,
        "extra": extra,
        "package_record_digest": digest,
        "package_record_lines": lines,
    }


def _checked_installation(
    interpreter: Path,
    *,
    require_published: bool,
    verify_files: bool,
    expected_package_record_digest: str | None,
) -> tuple[PolicyEngineUSInstallation, dict[str, Any]]:
    """Inspect, check the source, and (for an index install) the files."""

    installation = inspect_installation(interpreter)
    source = check_published_source(installation, require=require_published)
    problems = []
    if installation.source_kind == "index" and (
        verify_files or expected_package_record_digest
    ):
        record = verify_record(installation)
        source = {
            **source,
            "record_check": {
                key: len(value) if isinstance(value, list) else value
                for key, value in record.items()
            },
        }
        if record["mismatched"] or record["missing"] or record["extra"]:
            problems.append(
                f"{len(record['mismatched'])} installed files differ from "
                f"the RECORD, {len(record['missing'])} are missing and "
                f"{len(record['extra'])} are not in it"
            )
        if expected_package_record_digest and (
            record["package_record_digest"] != expected_package_record_digest
        ):
            problems.append("the RECORD is not the expected release's")
    elif expected_package_record_digest:
        problems.append(
            f"a {installation.source_kind} install has no RECORD to compare "
            "with the expected release"
        )
    if problems:
        raise UnpublishedSourceError(
            f"policyengine-us at {installation.package_dir}: "
            + "; ".join(problems)
        )
    return installation, source


def run_policyengine_us(
    cases: Sequence[RunCase],
    *,
    year: int,
    python: str | os.PathLike | None = None,
    expand: Sequence[str] = DEFAULT_EXPAND,
    root: str = ROOT_VARIABLE,
    timeout: float = 1800.0,
    require_published: bool = True,
    verify_files: bool = True,
    expected_package_record_digest: str | None = None,
) -> RunResult:
    """Run ``cases`` in the policyengine-us interpreter and parse the results.

    Each case runs in its own simulation (cases with the same parameter
    overrides share a tax-benefit system).  Before running, the imported
    ``policyengine-us`` must be a published source
    (:func:`check_published_source`, when ``require_published``), an index
    install's files must match its RECORD (:func:`verify_record`, when
    ``verify_files``), and its RECORD must have
    ``expected_package_record_digest`` when one is given.

    Raises :class:`PolicyEngineUSUnavailable` when the interpreter is
    missing or the child fails, :class:`UnpublishedSourceError` when a
    check above fails, and ``ValueError`` when a case resolves to a state
    other than its ``expected_state`` or a case id repeats.
    """

    if isinstance(year, bool) or not isinstance(year, int):
        raise TypeError(f"year must be an integer, not {year!r}")
    ids = [case.case_id for case in cases]
    if len(set(ids)) != len(ids):
        raise ValueError(f"case ids must be unique: {ids}")
    interpreter = _interpreter(python)
    installation, source = _checked_installation(
        interpreter,
        require_published=require_published,
        verify_files=verify_files,
        expected_package_record_digest=expected_package_record_digest,
    )
    job = {
        "year": year,
        "root": root,
        "expand": list(expand),
        "cases": [
            {
                "case_id": case.case_id,
                "situation": case.situation,
                "memo": list(case.memo),
                "parameter_overrides": dict(case.parameter_overrides),
            }
            for case in cases
        ],
    }
    payload = _run_child(interpreter, _RUNNER_SOURCE, json.dumps(job), timeout)
    ran = PolicyEngineUSInstallation.from_payload(
        interpreter, payload["installation"]
    )
    if ran != installation:
        raise PolicyEngineUSUnavailable(
            "policyengine-us changed between the source check and the run"
        )
    runs: dict[str, PolicyEngineRun] = {}
    by_id = {case.case_id: case for case in cases}
    for raw in payload["cases"]:
        case = by_id[raw["case_id"]]
        states = sorted(set(raw["state_code"]))
        if len(states) != 1:
            raise ValueError(f"{case.case_id}: several states {states}")
        state = states[0]
        if case.expected_state is not None and state != case.expected_state:
            raise ValueError(
                f"{case.case_id}: situation resolved to {state}, not "
                f"{case.expected_state} (check STATE_FIPS)"
            )
        tree = ComponentTree(
            root=root,
            children={
                name: tuple((str(c), int(s)) for c, s in parts)
                for name, parts in raw["tree"].items()
            },
        )
        runs[case.case_id] = PolicyEngineRun(
            case_id=case.case_id,
            state_code=state,
            tree=tree,
            values={k: float(v) for k, v in raw["values"].items()},
            memo={k: float(v) for k, v in raw["memo"].items()},
        )
    if set(runs) != set(ids):
        raise PolicyEngineUSUnavailable("the runner returned other cases")
    return RunResult(
        runs=runs,
        policyengine_us_version=str(payload["policyengine_us_version"]),
        policyengine_core_version=str(payload["policyengine_core_version"]),
        policyengine_us_package=str(payload["policyengine_us_package"]),
        python=str(interpreter),
        installation=installation,
        source=source,
    )


# ---------------------------------------------------------------------------
# The float32 guard (traced runs)
# ---------------------------------------------------------------------------
#: A change smaller than a cent is float noise, not a change.
CENT_TOLERANCE = 0.01
#: Float32 carries 24 significant bits, so a value near ``x`` moves in
#: steps of 2 ** (exponent(x) - 24).  A read that changed by no more than
#: this many steps is treated as noise even when the steps exceed a cent
#: (above $131,072 one step is $0.015625).
FLOAT32_NOISE_STEPS = 4
#: Leaf changes below this many cents (and above zero) are small enough to
#: be a float32 step at a bracket edge and are always traced.
SMALL_CHANGE_CENTS = 200


def float32_step(value: float) -> float:
    """The spacing of float32 values at ``value`` (0 at 0 and non-finite)."""

    if value == 0 or not math.isfinite(value):
        return 0.0
    _, exponent = math.frexp(value)
    return math.ldexp(1.0, exponent - 24)


@dataclass(frozen=True)
class TraceNode:
    """One traced variable at one period in one case.

    ``value`` is the variable's value over its own entity (``None`` when
    it is not numeric); ``children`` are the ``name@period`` keys it read;
    ``input`` is true for a variable with no formula, ``adds`` or
    ``subtracts`` (``None`` for a name that is not a variable).
    """

    value: tuple[float, ...] | None
    children: tuple[str, ...]
    input: bool | None


def trace_policyengine_us(
    cases: Sequence[tuple[str, Mapping[str, Any], Sequence[str]]],
    *,
    year: int,
    python: str | os.PathLike | None = None,
    parameter_overrides: Mapping[str, Mapping[str, Any]] | None = None,
    timeout: float = 1800.0,
    require_published: bool = True,
    verify_files: bool = True,
    expected_package_record_digest: str | None = None,
) -> dict[str, dict[str, TraceNode]]:
    """Trace ``(case_id, situation, variables)`` cases, one simulation each.

    Returns ``{case_id: {"name@period": TraceNode}}`` (branch simulations'
    nodes are keyed ``branch:name@period``).  ``parameter_overrides`` maps
    a case id to its overrides (as :class:`RunCase`).  The imported
    ``policyengine-us`` is checked as in :func:`run_policyengine_us`, and
    must not change between the check and the trace.
    """

    if isinstance(year, bool) or not isinstance(year, int):
        raise TypeError(f"year must be an integer, not {year!r}")
    ids = [case_id for case_id, _, _ in cases]
    if len(set(ids)) != len(ids):
        raise ValueError(f"case ids must be unique: {ids}")
    interpreter = _interpreter(python)
    installation, _ = _checked_installation(
        interpreter,
        require_published=require_published,
        verify_files=verify_files,
        expected_package_record_digest=expected_package_record_digest,
    )
    overrides = parameter_overrides or {}
    job = {
        "year": year,
        "cases": [
            {
                "case_id": case_id,
                "situation": situation,
                "variables": list(variables),
                "parameter_overrides": dict(overrides.get(case_id, {})),
            }
            for case_id, situation, variables in cases
        ],
    }
    payload = _run_child(interpreter, _TRACE_SOURCE, json.dumps(job), timeout)
    traced = PolicyEngineUSInstallation.from_payload(
        interpreter, payload["installation"]
    )
    if traced != installation:
        raise PolicyEngineUSUnavailable(
            "policyengine-us changed between the source check and the trace"
        )
    out: dict[str, dict[str, TraceNode]] = {}
    for case in payload["cases"]:
        out[case["case_id"]] = {
            key: TraceNode(
                value=(
                    None
                    if node["value"] is None
                    else tuple(float(v) for v in node["value"])
                ),
                children=tuple(node["children"]),
                input=node["input"],
            )
            for key, node in case["nodes"].items()
        }
    if set(out) != set(ids):
        raise PolicyEngineUSUnavailable("the tracer returned other cases")
    return out


def _node_change(
    baseline: TraceNode | None, reform: TraceNode | None
) -> float | None:
    """The largest absolute change of a node, or ``None`` if not comparable.

    A node traced in one run only, or with values of different lengths, is
    a change of infinite size (its structure changed).
    """

    if baseline is None or reform is None:
        return math.inf
    if baseline.value is None or reform.value is None:
        return None
    if len(baseline.value) != len(reform.value):
        return math.inf
    worst = 0.0
    for a, b in zip(baseline.value, reform.value, strict=True):
        if not (math.isfinite(a) and math.isfinite(b)):
            if not (a == b or (math.isnan(a) and math.isnan(b))):
                return math.inf
            continue
        worst = max(worst, abs(b - a))
    return worst


def _noise(
    baseline: TraceNode | None, reform: TraceNode | None, tolerance: float
) -> float:
    """The largest change of a read that still counts as float noise."""

    magnitude = _magnitude(baseline, reform)
    return max(tolerance, FLOAT32_NOISE_STEPS * float32_step(magnitude))


def _counts_as_change(
    baseline: TraceNode, reform: TraceNode, change: float, tolerance: float
) -> bool:
    """Whether a node's ``change`` is ``tolerance`` or more before rounding.

    Values are stored in float32, so a change of exactly ``tolerance``
    can measure up to one float32 step less (3.00 to 3.01 measures
    0.0099999905): each stored end is off by at most half a step.  The
    threshold is therefore ``tolerance`` less one float32 step at the
    node's magnitude, and never less than half of ``tolerance``, so a zero
    change or float64 noise on a large value never counts.

    Two limits.  From $32,768 to $131,072 a cent is one or two float32
    steps, so one or two steps of noise count too: the guard errs toward a
    false alarm.  And the bound covers a stored value, not one computed
    from larger operands, which carries their larger rounding: x = a -
    5,760 with ``a`` near $35,760 moves by $0.0078125 when ``a`` moves by a
    cent, and that does not count.
    """

    if change == 0:
        return False
    slack = float32_step(_magnitude(baseline, reform))
    return change >= tolerance - min(slack, tolerance / 2)


def _magnitude(*nodes: TraceNode | None) -> float:
    """The largest finite absolute value among the nodes' values."""

    return max(
        (
            abs(v)
            for node in nodes
            if node is not None and node.value is not None
            for v in node.value
            if math.isfinite(v)
        ),
        default=0.0,
    )


def _values(node: TraceNode | None) -> list[float] | None:
    return None if node is None or node.value is None else list(node.value)


def uncaused_changes(
    baseline: Mapping[str, TraceNode],
    reform: Mapping[str, TraceNode],
    roots: Iterable[str],
    *,
    tolerance: float = CENT_TOLERANCE,
) -> list[dict[str, Any]]:
    """Variables that change although every variable they read did not.

    Walks the traced nodes reachable from ``roots`` (``name@period``
    keys) in both runs.  A node is reported when it was traced in both
    runs, is not an input, its value changes by at least ``tolerance``
    before float32 rounding (:func:`_counts_as_change`, so an exact
    one-cent step stored in float32 counts), and no node it read changed
    by more than float noise: ``tolerance`` or
    :data:`FLOAT32_NOISE_STEPS` float32 steps at the read's magnitude,
    whichever is larger (so the guard still sees noise above $131,072,
    where one float32 step exceeds a cent).  A node it read in one run only
    counts as changed: the calculation took another branch, which a
    changed value upstream decided.  A node traced in one run only is not
    compared for the same reason.  A branch simulation's node traced
    without reads (``branch:name@period``) holds a value copied from the
    parent simulation and reads the main node ``name@period``.  A read
    with no numeric value never counts as a cause, so a node whose only
    changed read is not numeric is reported (a false alarm, not a miss).

    A genuine change always has a changed input below it (here, the Social
    Security amount), so a reported node is a step taken on noise:
    typically a bracket or eligibility edge that float32 arithmetic
    crossed.  The rule is local, so it cannot see a noise step in a
    variable that also read a genuinely changed input.  Returns one record
    per reported node, sorted by key.
    """

    found: dict[str, dict[str, Any]] = {}
    visited: set[str] = set()
    pending = list(roots)
    while pending:
        key = pending.pop()
        if key in visited:
            continue
        visited.add(key)
        before, after = baseline.get(key), reform.get(key)
        children = tuple(
            dict.fromkeys(
                (before.children if before else ())
                + (after.children if after else ())
            )
        )
        if not children and ":" in key:
            # A branch starts as a clone of its parent's calculated values
            # (policyengine-core ``get_branch``, ``simulation.py:1499``), so
            # a branch node traced without reads was copied, not computed:
            # it reads the main calculation's node of the same name.
            main = key.split(":", 1)[1]
            if main in baseline or main in reform:
                children = (main,)
        pending.extend(children)
        if before is None or after is None or before.input:
            continue
        change = _node_change(before, after)
        if change is None or not _counts_as_change(
            before, after, change, tolerance
        ):
            continue
        child_changes = {
            child: _node_change(baseline.get(child), reform.get(child))
            for child in children
        }
        caused = any(
            value is not None
            and value
            > _noise(baseline.get(child), reform.get(child), tolerance)
            for child, value in child_changes.items()
        )
        if not caused:
            found[key] = {
                "variable": key,
                "baseline": _values(before),
                "reform": _values(after),
                "change": change,
                "reads": dict(sorted(child_changes.items())),
            }
    return [found[key] for key in sorted(found)]


def small_changes(
    decomposition: Decomposition, *, limit_cents: int = SMALL_CHANGE_CENTS
) -> list[Component]:
    """Leaves whose change is nonzero and under ``limit_cents``."""

    return [
        component
        for component in decomposition.components
        if 0 < abs(component.change_cents) < limit_cents
    ]


# ---------------------------------------------------------------------------
# The decomposition
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ComponentTree:
    """``children[name]`` lists ``(part, sign)`` for each expanded aggregate.

    A name absent from ``children``, or present with no parts, is a leaf.
    """

    root: str
    children: Mapping[str, tuple[tuple[str, int], ...]]

    def __post_init__(self) -> None:
        if self.root not in self.children:
            raise ValueError(f"the tree does not expand its root {self.root}")
        for name, parts in self.children.items():
            for part, sign in parts:
                if sign not in (1, -1):
                    raise ValueError(f"{name}: sign {sign} of {part}")

        def visit(name: str, stack: tuple[str, ...]) -> None:
            if name in stack:
                raise ValueError(f"cycle through {name}")
            for part, _ in self.children.get(name, ()):
                visit(part, (*stack, name))

        visit(self.root, ())

    def is_leaf(self, name: str) -> bool:
        return not self.children.get(name)

    def leaves(self) -> tuple[tuple[str, tuple[str, ...], int], ...]:
        """Each leaf with its ancestors (root first) and cumulative sign."""

        out: list[tuple[str, tuple[str, ...], int]] = []

        def walk(name: str, path: tuple[str, ...], sign: int) -> None:
            if self.is_leaf(name):
                out.append((name, path, sign))
                return
            for part, part_sign in self.children[name]:
                walk(part, (*path, name), sign * part_sign)

        walk(self.root, (), 1)
        return tuple(out)

    def aggregates(self) -> tuple[str, ...]:
        """The names with parts, parents before children."""

        order: list[str] = []

        def walk(name: str) -> None:
            if self.is_leaf(name) or name in order:
                return
            order.append(name)
            for part, _ in self.children[name]:
                walk(part)

        walk(self.root)
        return tuple(order)


def to_cents(value: float) -> int:
    """Dollars to integer cents, half to even, exactly from the float."""

    amount = float(value)
    if not math.isfinite(amount):
        raise ValueError(f"amount must be finite, not {value!r}")
    cents = (Decimal(amount) * 100).to_integral_value(rounding=ROUND_HALF_EVEN)
    return int(cents)


#: Display categories, in table order, and their labels.  Taxes before
#: refundable credits and refundable credits are separate rows, so a
#: refundable credit on a zero liability never reads as a negative tax.
CATEGORY_ORDER: tuple[str, ...] = (
    "social_security",
    "ssi",
    "state_benefits",
    "snap",
    "csfp",
    "other_benefits",
    "health_net",
    "market_income",
    "federal_income_tax",
    "federal_refundable_credits",
    "state_income_tax",
    "state_refundable_credits",
    "other_taxes",
)
CATEGORY_LABELS: dict[str, str] = {
    "social_security": "Social Security",
    "ssi": "SSI (federal)",
    "state_benefits": "State benefits (incl. SSI supplements)",
    "snap": "SNAP",
    "csfp": "Commodity Supplemental Food Program",
    "other_benefits": "Other benefits",
    "health_net": "Health benefits less health costs",
    "market_income": "Market income",
    "federal_income_tax": "Federal income tax before refundable credits",
    "federal_refundable_credits": "Federal refundable tax credits",
    "state_income_tax": "State income tax before refundable credits",
    "state_refundable_credits": "State refundable tax credits",
    "other_taxes": "Other taxes (payroll, use, local)",
}


def category_for(variable: str, path: Sequence[str]) -> str:
    """The display category of a leaf reached through ``path``."""

    ancestors = set(path)
    if variable == "social_security":
        return "social_security"
    if variable == "ssi":
        return "ssi"
    if variable == "snap":
        return "snap"
    if variable == "commodity_supplemental_food_program":
        return "csfp"
    if variable == "income_tax_before_refundable_credits":
        return "federal_income_tax"
    if variable == "income_tax_refundable_credits":
        return "federal_refundable_credits"
    if "household_state_benefits" in ancestors:
        return "state_benefits"
    if ancestors & {"household_health_benefits", "household_health_costs"}:
        return "health_net"
    if "household_market_income" in ancestors:
        return "market_income"
    if variable == "state_income_tax_before_refundable_credits":
        return "state_income_tax"
    if "household_refundable_state_tax_credits" in ancestors:
        return "state_refundable_credits"
    if "household_tax_before_refundable_credits" in ancestors:
        return "other_taxes"
    return "other_benefits"


@dataclass(frozen=True)
class Component:
    """A leaf's contribution to net income in each run, in cents.

    ``sign`` is +1 for an income and -1 for a tax or cost; ``baseline`` and
    ``reform`` are the signed contributions, so a tax enters negative.
    """

    variable: str
    path: tuple[str, ...]
    sign: int
    category: str
    baseline_cents: int
    reform_cents: int

    @property
    def change_cents(self) -> int:
        return self.reform_cents - self.baseline_cents

    def as_dict(self) -> dict[str, Any]:
        return {
            "variable": self.variable,
            "path": list(self.path),
            "sign": self.sign,
            "category": self.category,
            "baseline": self.baseline_cents / 100,
            "reform": self.reform_cents / 100,
            "change": self.change_cents / 100,
        }


@dataclass(frozen=True)
class Decomposition:
    """Leaf components whose changes sum exactly to ``net_change_cents``.

    ``baseline_net_cents`` and ``reform_net_cents`` are net income as its
    definition computes it from the cent-rounded leaves;
    ``reported_*`` are PolicyEngine-US's own ``household_net_income``
    (float32 sums), and ``reported_gap_cents`` their difference from the
    definition's change (float rounding inside PolicyEngine-US, bounded by
    the tolerance).  ``max_aggregate_gap`` is the largest difference between
    an aggregate and the sum of its parts found in either run.
    """

    components: tuple[Component, ...]
    baseline_net_cents: int
    reform_net_cents: int
    reported_baseline_net: float
    reported_reform_net: float
    max_aggregate_gap: float

    @property
    def net_change_cents(self) -> int:
        return self.reform_net_cents - self.baseline_net_cents

    @property
    def reported_gap_cents(self) -> int:
        reported = to_cents(self.reported_reform_net) - to_cents(
            self.reported_baseline_net
        )
        return reported - self.net_change_cents

    def by_category(self) -> dict[str, dict[str, int]]:
        """Each category's baseline, reform and change, in cents."""

        out = {
            name: {"baseline": 0, "reform": 0, "change": 0}
            for name in CATEGORY_ORDER
        }
        for component in self.components:
            entry = out.setdefault(
                component.category, {"baseline": 0, "reform": 0, "change": 0}
            )
            entry["baseline"] += component.baseline_cents
            entry["reform"] += component.reform_cents
            entry["change"] += component.change_cents
        return out

    def as_dict(self) -> dict[str, Any]:
        return {
            "net_change": self.net_change_cents / 100,
            "baseline_net_income": self.baseline_net_cents / 100,
            "reform_net_income": self.reform_net_cents / 100,
            "reported_baseline_net_income": self.reported_baseline_net,
            "reported_reform_net_income": self.reported_reform_net,
            "reported_gap": self.reported_gap_cents / 100,
            "max_aggregate_gap": self.max_aggregate_gap,
            "categories": {
                name: {key: cents / 100 for key, cents in entry.items()}
                for name, entry in self.by_category().items()
            },
            "components": [
                component.as_dict()
                for component in self.components
                if component.baseline_cents or component.reform_cents
            ],
        }


def _aggregate_gap(tree: ComponentTree, values: Mapping[str, float]) -> float:
    """The largest |aggregate - sum of parts|; infinite if any is not finite.

    ``max(0.0, nan)`` is ``0.0``, so a non-finite gap must be caught before
    it is compared, or a NaN aggregate would pass as consistent.
    """

    worst = 0.0
    for name in tree.aggregates():
        parts = tree.children[name]
        terms = [sign * float(values[part]) for part, sign in parts]
        value = float(values[name])
        if not all(math.isfinite(term) for term in (*terms, value)):
            return math.inf
        gap = abs(value - math.fsum(terms))
        if not math.isfinite(gap):
            return math.inf
        worst = max(worst, gap)
    return worst


def decompose(
    tree: ComponentTree,
    baseline: Mapping[str, float],
    reform: Mapping[str, float],
    *,
    reform_tree: ComponentTree | None = None,
    tolerance: float = 0.5,
    expected_definition: Sequence[tuple[str, int]] | None = (
        NET_INCOME_DEFINITION
    ),
) -> Decomposition:
    """Split the change in ``tree.root`` into its leaves.

    Both runs must share ``tree`` (``reform_tree``, when given, must equal
    it).  Every aggregate in each run must equal the signed sum of its parts
    within ``tolerance`` dollars, and every value must be finite, else
    :class:`AggregateMismatchError`; the
    root's parts must equal ``expected_definition`` (skip with ``None``),
    else :class:`DefinitionDriftError`.  Leaves are rounded to cents, so the
    components' changes sum exactly to the net change; PolicyEngine-US's own
    root values are kept as ``reported_*``.
    """

    if reform_tree is not None and reform_tree != tree:
        raise DefinitionDriftError("baseline and reform trees differ")
    if expected_definition is not None:
        observed = tuple(tree.children[tree.root])
        if observed != tuple(tuple(item) for item in expected_definition):
            raise DefinitionDriftError(
                f"{tree.root} is {observed}, not the definition the bridge "
                f"was checked against ({tuple(expected_definition)})"
            )
    gaps = []
    for label, values in (("baseline", baseline), ("reform", reform)):
        gap = _aggregate_gap(tree, values)
        if not math.isfinite(gap):
            raise AggregateMismatchError(
                f"{label}: an aggregate or one of its parts is not finite"
            )
        if gap > tolerance:
            raise AggregateMismatchError(
                f"{label}: an aggregate differs from its parts by {gap:.4f}"
            )
        gaps.append(gap)
    components = tuple(
        Component(
            variable=name,
            path=path,
            sign=sign,
            category=category_for(name, path),
            baseline_cents=sign * to_cents(baseline[name]),
            reform_cents=sign * to_cents(reform[name]),
        )
        for name, path, sign in tree.leaves()
    )
    decomposition = Decomposition(
        components=components,
        baseline_net_cents=sum(c.baseline_cents for c in components),
        reform_net_cents=sum(c.reform_cents for c in components),
        reported_baseline_net=float(baseline[tree.root]),
        reported_reform_net=float(reform[tree.root]),
        max_aggregate_gap=max(gaps),
    )
    if abs(decomposition.reported_gap_cents) > round(tolerance * 100):
        raise AggregateMismatchError(
            f"{tree.root}'s reported change differs from its definition by "
            f"{decomposition.reported_gap_cents} cents"
        )
    return decomposition


# ---------------------------------------------------------------------------
# Carrying a Microcosm PIA to the payment year (42 USC 415(i))
# ---------------------------------------------------------------------------
#: COLA rates are quantized to a millionth before use: statutory COLAs are
#: tenths of a percent (0.001), and a fraction built as ``percent / 100`` in
#: floating point can carry noise (``5.9 / 100`` is ``0.059000000000000004``)
#: that would otherwise reach the dime truncation.
_RATE_QUANTUM = Decimal("0.000001")


def _rate(value: float) -> Decimal:
    return Decimal(repr(float(value))).quantize(
        _RATE_QUANTUM, rounding=ROUND_HALF_EVEN
    )


def floor_to_dime(amount: float | Decimal) -> float:
    """The next lower multiple of $0.10 (415(i)(2)(A)(ii)), exactly."""

    value = amount if isinstance(amount, Decimal) else Decimal(repr(amount))
    tenths = (value * 10).to_integral_value(rounding=ROUND_FLOOR)
    return float(tenths / 10)


def carry_pia_forward(
    pia: float,
    rates: Mapping[int, float],
    *,
    first_determination_year: int,
    last_determination_year: int,
) -> tuple[float, tuple[dict[str, Any], ...]]:
    """Apply each COLA from ``first_determination_year`` through the last.

    42 USC 415(i)(2)(A)(ii) multiplies the PIA by each increase and
    decreases any amount that is not a multiple of $0.10 to the next lower
    multiple; (iii) applies the increase of the year of eligibility and
    every later one to a PIA first computed in that year.  ``rates`` maps a
    determination year to a fraction (``0.028`` for 2.8 percent).  Returns
    the carried PIA and one record per step.  Decimal arithmetic on the
    rates (quantized to a millionth) keeps the truncation exact.  An empty
    range (``first_determination_year`` after the last) is refused: it
    would return the PIA untruncated, not a whole dime.
    """

    value = _check_amount("pia", pia)
    for label, year in (
        ("first_determination_year", first_determination_year),
        ("last_determination_year", last_determination_year),
    ):
        if isinstance(year, bool) or not isinstance(year, int):
            raise TypeError(f"{label} must be an integer year")
    if first_determination_year > last_determination_year:
        raise ValueError(
            f"first_determination_year {first_determination_year} is after "
            f"last_determination_year {last_determination_year}"
        )
    current = Decimal(repr(value))
    steps: list[dict[str, Any]] = []
    for year in range(first_determination_year, last_determination_year + 1):
        if year not in rates:
            raise ValueError(f"no COLA for determination year {year}")
        rate = float(rates[year])
        if not math.isfinite(rate) or rate < 0:
            raise ValueError(f"COLA for {year} must be nonnegative: {rate}")
        before = current
        increased = before * (1 + _rate(rate))
        current = Decimal(repr(floor_to_dime(increased)))
        steps.append(
            {
                "determination_year": year,
                "rate": rate,
                "pia_before": float(before),
                "pia_after": float(current),
            }
        )
    return float(current), tuple(steps)


def cola_rates_from_cpi_w(
    cpi_w_by_year: Mapping[int, float],
) -> dict[int, float]:
    """COLAs from third-quarter CPI-W averages (42 USC 415(i)(1)).

    ``cpi_w_by_year[y]`` is the third-quarter average of year ``y - 1`` (the
    keying of PolicyEngine-US's ``gov.ssa.uprating``, whose entry dated
    ``y``-01-01 is ``y - 1``'s third quarter).  The COLA determined in
    ``y - 1`` is the percentage by which that quarter's index exceeds the
    index of the most recent prior cost-of-living computation quarter,
    rounded to the nearest one-tenth of 1 percent (415(i)(1)(D)); a quarter
    is a computation quarter only when that percentage is greater than zero
    (415(i)(1)(B)), else the COLA is zero and the base carries forward.
    The first entry is taken to be a computation quarter.  Returns
    ``{determination year: fraction}``.
    """

    years = sorted(int(year) for year in cpi_w_by_year)
    if len(years) < 2:
        raise ValueError("need at least two third-quarter averages")
    if years != list(range(years[0], years[-1] + 1)):
        raise ValueError(
            f"third-quarter averages must be consecutive: {years}"
        )
    for year in years:
        _check_amount(f"CPI-W {year}", cpi_w_by_year[year])
        if cpi_w_by_year[year] <= 0:
            raise ValueError(f"CPI-W {year} must be positive")
    base = Decimal(repr(float(cpi_w_by_year[years[0]])))
    rates: dict[int, float] = {}
    for year in years[1:]:
        quarter = Decimal(repr(float(cpi_w_by_year[year])))
        percent = ((quarter / base) - 1) * 100
        rounded = percent.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        determination_year = year - 1
        if rounded > 0:
            rates[determination_year] = float(rounded / 100)
            base = quarter
        else:
            rates[determination_year] = 0.0
    return rates
