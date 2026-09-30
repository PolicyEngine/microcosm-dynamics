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
   social_security_retirement.py:4-10`` at ``e4363903f3``), so the amounts
   Microcosm computes enter as inputs and PolicyEngine-US adds them in
   ``social_security`` (``social_security.py:11-14``).
2. **Runner.**  :func:`run_policyengine_us` sends situations as JSON to a
   separate interpreter that has ``policyengine-us`` installed (located by
   ``POPULACE_DYNAMICS_PE_US_PYTHON``, the subprocess discipline of
   ``scripts/build_aux_benefit_examples.py``).  The child reads the
   component tree of ``household_net_income`` from the model itself and
   returns every node's household value.
3. **Decomposition.**  :func:`decompose` turns a baseline and a reform run
   into leaf components whose changes sum exactly (in integer cents) to
   the change in ``household_net_income`` as its definition computes it,
   after checking every aggregate against the sum of its parts.

``household_net_income`` at ``e4363903f3``
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

import json
import math
import os
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
    "Component",
    "ComponentTree",
    "DEFAULT_EXPAND",
    "DEFAULT_PE_US_PYTHON",
    "Decomposition",
    "DefinitionDriftError",
    "NET_INCOME_DEFINITION",
    "PE_US_PYTHON_ENV",
    "PolicyEngineRun",
    "PolicyEngineUSUnavailable",
    "ROOT_VARIABLE",
    "RunCase",
    "RunResult",
    "STATE_FIPS",
    "carry_pia_forward",
    "category_for",
    "cola_rates_from_cpi_w",
    "decompose",
    "floor_to_dime",
    "person_inputs_from_situation",
    "resolve_pe_us_python",
    "run_policyengine_us",
    "to_cents",
    "to_situation",
]

#: The environment variable naming the interpreter that has
#: ``policyengine-us`` installed (as ``scripts/build_aux_benefit_examples.py``
#: uses it).
PE_US_PYTHON_ENV = "POPULACE_DYNAMICS_PE_US_PYTHON"
#: The fallback when the environment variable is unset: the virtual
#: environment of the default policyengine-us checkout.
DEFAULT_PE_US_PYTHON = Path("~/PolicyEngine/policyengine-us/.venv/bin/python")

#: The variable the decomposition explains.
ROOT_VARIABLE = "household_net_income"
#: ``household_net_income``'s definition at ``e4363903f3``
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
      allowance turns on it (``snap_utility_allowance_type.py:38-45``).
    * ``takes_up_housing_assistance`` (SPM unit,
      ``takes_up_housing_assistance_if_eligible``): its default is true
      (``takes_up_housing_assistance_if_eligible.py:9``), which would give
      every income-eligible renter a housing voucher.
    * ``food_preparation_allowed`` (household,
      ``living_arrangements_allow_for_food_preparation``): its default is
      false, and California's supplement adds a food allowance when it is
      false (``ca_state_supplement_food_allowance_eligible.py:13-21``).
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
#: Executed by the policyengine-us interpreter.  It reads a job on stdin and
#: writes results on stdout.  For each case it builds the component tree of
#: the root from the model: a variable's ``adds``/``subtracts`` (a list, or
#: a parameter path to a list), except three formula variables whose lists
#: it mirrors from their source at ``e4363903f3``:
#:
#: * ``household_benefits`` (``household_benefits.py:11-19``):
#:   ``gov.household.household_benefits``, less
#:   ``spm_unit_capped_housing_subsidy`` when ``gov.hud.abolition``;
#: * ``household_health_benefits`` (``household_health_benefits.py:17-22``)
#:   and ``household_health_costs`` (``household_health_costs.py:16-20``):
#:   their ``gov.household`` lists when
#:   ``gov.simulation.include_health_benefits_in_net_income``, else none.
#:
#: A variable to expand with neither ``adds`` nor a mirrored list is an
#: error.  :func:`decompose` checks every aggregate's value against its
#: parts, so a wrong mirror fails loudly.
#:
#: Cases that share parameter overrides run as one simulation: their
#: situations are merged with every person and group name prefixed by the
#: case's index (households are independent in PolicyEngine-US's entity
#: model), and each case reads its own household's row.  Each case must
#: hold exactly one household.
_RUNNER_SOURCE = r"""
import json
import sys
import importlib.metadata as metadata

import policyengine_us
from policyengine_us import Simulation
from policyengine_core.reforms import Reform

job = json.load(sys.stdin)
year = int(job["year"])
period = str(year)
expand = set(job["expand"])
root = job["root"]
def parameter_list(params, path):
    node = params
    for part in path.split("."):
        node = getattr(node, part)
    return [str(item) for item in node]


def children_of(system, params, name):
    if name == "household_benefits":
        items = parameter_list(params, "gov.household.household_benefits")
        if bool(params.gov.hud.abolition):
            items = [i for i in items if i != "spm_unit_capped_housing_subsidy"]
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


GROUP_ENTITIES = (
    "tax_units",
    "spm_units",
    "marital_units",
    "families",
    "households",
)


def merged_situation(cases):
    merged = {"people": {}}
    for plural in GROUP_ENTITIES:
        merged[plural] = {}
    household_names = []
    for index, case in enumerate(cases):
        prefix = f"c{index}__"
        situation = case["situation"]
        households = situation.get("households", {})
        if len(households) != 1:
            raise ValueError(f"{case['case_id']}: needs exactly one household")
        for person, entry in situation["people"].items():
            merged["people"][prefix + person] = entry
        for plural in GROUP_ENTITIES:
            for name, entry in situation.get(plural, {}).items():
                renamed = dict(entry)
                renamed["members"] = [prefix + m for m in entry["members"]]
                merged[plural][prefix + name] = renamed
        household_names.append(prefix + next(iter(households)))
    return merged, household_names


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


groups = {}
for case in job["cases"]:
    key = json.dumps(case.get("parameter_overrides") or {}, sort_keys=True)
    groups.setdefault(key, []).append(case)

results = []
for key, cases in groups.items():
    overrides = json.loads(key)
    reform = None
    if overrides:
        reform = Reform.from_dict(
            {
                path: {f"{year}-01-01.{year}-12-31": value}
                for path, value in overrides.items()
            },
            country_id="us",
        )
    situation, household_names = merged_situation(cases)
    sim = Simulation(situation=situation, reform=reform)
    system = sim.tax_benefit_system
    params = system.parameters(f"{year}-01-01")
    tree = build_tree(system, params)
    names = set(tree)
    for parts in tree.values():
        names.update(child for child, _ in parts)
    ids = [str(i) for i in sim.populations["household"].ids]
    rows = [ids.index(name) for name in household_names]
    arrays = {
        name: sim.calculate(name, period, map_to="household")
        for name in sorted(names)
    }
    memo_names = sorted({m for case in cases for m in case.get("memo", [])})
    memo_arrays = {
        name: sim.calculate(name, period, map_to="household")
        for name in memo_names
    }
    states = sim.calculate("state_code", period).decode_to_str()
    for case, row in zip(cases, rows):
        results.append(
            {
                "case_id": case["case_id"],
                "state_code": [str(states[row])],
                "tree": tree,
                "values": {n: float(a[row]) for n, a in arrays.items()},
                "memo": {
                    n: float(memo_arrays[n][row])
                    for n in case.get("memo", [])
                },
            }
        )
json.dump(
    {
        "policyengine_us_version": metadata.version("policyengine-us"),
        "policyengine_core_version": metadata.version("policyengine-core"),
        "policyengine_us_package": policyengine_us.__file__,
        "cases": results,
    },
    sys.stdout,
)
"""


@dataclass(frozen=True)
class RunCase:
    """One PolicyEngine-US simulation: a situation and its options.

    ``expected_state`` is the two-letter state the situation should resolve
    to; ``memo`` names further variables to report at the household level
    (outside the decomposition); ``parameter_overrides`` sets parameters
    for the whole year (for example
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
class RunResult:
    """Every case of one runner call and the versions that computed them."""

    runs: Mapping[str, PolicyEngineRun]
    policyengine_us_version: str
    policyengine_core_version: str
    policyengine_us_package: str
    python: str


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


def run_policyengine_us(
    cases: Sequence[RunCase],
    *,
    year: int,
    python: str | os.PathLike | None = None,
    expand: Sequence[str] = DEFAULT_EXPAND,
    root: str = ROOT_VARIABLE,
    timeout: float = 1800.0,
) -> RunResult:
    """Run ``cases`` in the policyengine-us interpreter and parse the results.

    Raises :class:`PolicyEngineUSUnavailable` when the interpreter is
    missing or the child fails, and ``ValueError`` when a case resolves to
    a state other than its ``expected_state`` or a case id repeats.
    """

    if isinstance(year, bool) or not isinstance(year, int):
        raise TypeError(f"year must be an integer, not {year!r}")
    ids = [case.case_id for case in cases]
    if len(set(ids)) != len(ids):
        raise ValueError(f"case ids must be unique: {ids}")
    interpreter = resolve_pe_us_python(python)
    if not interpreter.is_file():
        raise PolicyEngineUSUnavailable(
            f"no policyengine-us interpreter at {interpreter}; set "
            f"{PE_US_PYTHON_ENV}"
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
    env = dict(os.environ)
    env.setdefault("OMP_NUM_THREADS", "1")
    try:
        proc = subprocess.run(
            [str(interpreter), "-c", _RUNNER_SOURCE],
            input=json.dumps(job),
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
    payload = json.loads(proc.stdout)
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
    )


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


#: Display categories, in table order, and their labels.
CATEGORY_ORDER: tuple[str, ...] = (
    "social_security",
    "ssi",
    "state_benefits",
    "snap",
    "other_benefits",
    "health_net",
    "market_income",
    "federal_income_tax",
    "state_income_tax",
    "other_taxes",
)
CATEGORY_LABELS: dict[str, str] = {
    "social_security": "Social Security",
    "ssi": "SSI (federal)",
    "state_benefits": "State benefits (incl. SSI supplements)",
    "snap": "SNAP",
    "other_benefits": "Other benefits",
    "health_net": "Health benefits less health costs",
    "market_income": "Market income",
    "federal_income_tax": "Federal income tax",
    "state_income_tax": "State income tax",
    "other_taxes": "Other taxes (payroll, use, local)",
}
_FEDERAL_INCOME_TAX = frozenset(
    {"income_tax_before_refundable_credits", "income_tax_refundable_credits"}
)


def category_for(variable: str, path: Sequence[str]) -> str:
    """The display category of a leaf reached through ``path``."""

    ancestors = set(path)
    if variable == "social_security":
        return "social_security"
    if variable == "ssi":
        return "ssi"
    if variable == "snap":
        return "snap"
    if variable in _FEDERAL_INCOME_TAX:
        return "federal_income_tax"
    if "household_state_benefits" in ancestors:
        return "state_benefits"
    if ancestors & {"household_health_benefits", "household_health_costs"}:
        return "health_net"
    if "household_market_income" in ancestors:
        return "market_income"
    if (
        variable == "state_income_tax_before_refundable_credits"
        or "household_refundable_state_tax_credits" in ancestors
    ):
        return "state_income_tax"
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
    worst = 0.0
    for name in tree.aggregates():
        parts = tree.children[name]
        total = math.fsum(sign * float(values[part]) for part, sign in parts)
        worst = max(worst, abs(float(values[name]) - total))
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
    within ``tolerance`` dollars, else :class:`AggregateMismatchError`; the
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
    rates (quantized to a millionth) keeps the truncation exact.
    """

    value = _check_amount("pia", pia)
    for label, year in (
        ("first_determination_year", first_determination_year),
        ("last_determination_year", last_determination_year),
    ):
        if isinstance(year, bool) or not isinstance(year, int):
            raise TypeError(f"{label} must be an integer year")
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
