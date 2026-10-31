"""SSI through policyengine.py's public annual calculation interfaces.

Invariants: every chain input is explicit or an opted-in named assumption;
ownership stays on people; unsupported configurations refuse before any
calculation; every attempted case remains in the denominator; versions are
checked inside the separate interpreter before importing policyengine.
Federal rules are never reproduced here. Results include potential SSI and
SSI conditional on the explicit take-up flag under a frozen annual state;
neither measures observed payments or December receipt.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
from collections import Counter
from collections.abc import Mapping, Sequence
from numbers import Real
from pathlib import Path
from typing import Any

from .contract import ContractRefusal, resolve_inputs
from .pinning import load_pin
from .records import (
    Accounting,
    BatchResult,
    Case,
    CountedRefusal,
    Household,
    MaritalUnit,
    Person,
    Refusal,
    RetirementAccount,
    SSIResult,
)

# Contains the existing tier classifier's oracle substring, while keeping
# this environment separate from the older bridge's interpreter.
PYTHON_ENV = "POPULACE_DYNAMICS_PE_US_PYTHON_SSI0"
DEFAULT_PYTHON = Path("~/.venvs/policyengine-py-6.10.2/bin/python")
CHILD = Path(__file__).with_name("_child.py")
OUTPUTS = (
    "ssi",
    "ssi_if_takes_up",
    "ssi_amount_if_eligible",
    "ssi_countable_income",
    "ssi_countable_resources",
    "ssi_earned_income",
    "ssi_unearned_income",
    "is_ssi_eligible",
    "meets_ssi_resource_test",
    "ssi_couple_computation_applies",
)
OVERRIDABLE_PARAMETERS = frozenset(
    {
        "gov.ssa.ssi.amount.individual",
        "gov.ssa.ssi.amount.couple",
        "gov.ssa.ssi.eligibility.resources.limit.individual",
        "gov.ssa.ssi.eligibility.resources.limit.couple",
        "gov.ssa.ssi.income.exclusions.general",
        "gov.ssa.ssi.income.exclusions.earned",
        "gov.ssa.ssi.income.exclusions.earned_share",
    }
)


def _refuse(condition: str, detail: str, *inputs: str) -> None:
    raise ContractRefusal(condition, tuple(inputs), detail)


def _finite(values: Any) -> bool:
    if isinstance(values, dict):
        return all(_finite(value) for value in values.values())
    if isinstance(values, (tuple, list)):
        return all(_finite(value) for value in values)
    return not isinstance(values, float) or math.isfinite(values)


def prepare(case: Case) -> tuple[dict, tuple[str, ...]]:
    """Validate links and resolve every contract input before making JSON."""
    if not isinstance(case.case_id, str) or not case.case_id:
        _refuse("INPUT_CONTRACT_GAP", "A nonempty case ID is required")
    if not isinstance(case.population, str) or not case.population.strip():
        _refuse("INPUT_CONTRACT_GAP", "A starting population is required")
    if (
        isinstance(case.period, bool)
        or not str(case.period).isdigit()
        or len(str(case.period)) != 4
    ):
        _refuse(
            "RULES_ENGINE_GAP",
            "Public calculate_household supports calendar years only",
            "period",
        )
    if case.timing != "frozen_annual_state_equal_twelfths":
        _refuse(
            "INPUT_CONTRACT_GAP",
            "Select the registered frozen annual state timing convention",
            "timing_convention",
        )
    if not isinstance(case.parameter_overrides, Mapping):
        _refuse("INPUT_CONTRACT_GAP", "Overrides must be a mapping")
    for name, value in case.parameter_overrides.items():
        if name not in OVERRIDABLE_PARAMETERS:
            _refuse(
                "RULES_ENGINE_GAP",
                "Override is outside the certified scalar SSI parameters",
                name,
            )
        if (
            isinstance(value, bool)
            or not isinstance(value, Real)
            or not math.isfinite(value)
            or value < 0
        ):
            _refuse(
                "INPUT_CONTRACT_GAP",
                "Annual overrides must be finite nonnegative scalars",
                name,
            )
        if name.endswith("earned_share") and value > 1:
            _refuse(
                "INPUT_CONTRACT_GAP",
                "An exclusion share must be between zero and one",
                name,
            )
    household = case.household
    if not isinstance(household, Household):
        _refuse("INPUT_CONTRACT_GAP", "A typed household record is required")
    people = household.people
    if (
        not isinstance(people, (tuple, list))
        or any(not isinstance(person, Person) for person in people)
        or not isinstance(household.marital_units, (tuple, list))
        or any(
            not isinstance(unit, MaritalUnit)
            for unit in household.marital_units
        )
    ):
        _refuse(
            "INPUT_CONTRACT_GAP", "Typed people and marital units required"
        )
    if any(
        not isinstance(values, Mapping)
        for values in (
            household.tax_units,
            household.inputs,
            household.tax_unit_inputs,
            household.family_inputs,
            household.spm_unit_inputs,
            *(person.inputs for person in people),
            *(unit.inputs for unit in household.marital_units),
        )
    ):
        _refuse("INPUT_CONTRACT_GAP", "Entity inputs and links need mappings")
    if any(
        not isinstance(person.retirement_accounts, (tuple, list))
        or any(
            not isinstance(account, RetirementAccount)
            for account in person.retirement_accounts
        )
        for person in people
    ):
        _refuse("INPUT_CONTRACT_GAP", "Typed retirement accounts required")
    ids = tuple(person.person_id for person in people)
    if (
        not ids
        or any(not isinstance(pid, str) or not pid for pid in ids)
        or len(ids) != len(set(ids))
    ):
        _refuse("INPUT_CONTRACT_GAP", "Person IDs must be nonempty and unique")
    if household.resource_ownership_validated is not True:
        condition = (
            "FRAME_LACKS_RESOURCES"
            if case.population.lower() in ("frame", "microcosm")
            else "INPUT_CONTRACT_GAP"
        )
        _refuse(
            condition,
            "Validate resources for each owner",
            "resource_ownership",
        )
    marital_groups = {
        unit.unit_id: unit.members for unit in household.marital_units
    }
    if len(marital_groups) != len(household.marital_units):
        _refuse("INPUT_CONTRACT_GAP", "Marital unit IDs must be unique")
    for groups, attribute in (
        (marital_groups, "marital_unit_id"),
        (household.tax_units, "tax_unit_id"),
    ):
        flattened = [pid for members in groups.values() for pid in members]
        if (
            not groups
            or any(
                not isinstance(key, str) or not key or not members
                for key, members in groups.items()
            )
            or len(flattened) != len(ids)
            or set(flattened) != set(ids)
            or any(
                person.person_id
                not in groups.get(getattr(person, attribute), ())
                for person in people
            )
        ):
            _refuse(
                "INPUT_CONTRACT_GAP",
                "Entity links must partition the household",
            )
    if (
        not isinstance(household.household_id, str)
        or not household.household_id
    ):
        _refuse("INPUT_CONTRACT_GAP", "A nonempty household ID is required")
    assumptions: set[str] = set()

    def resolved(entity: str, values: Any) -> dict:
        result = resolve_inputs(
            case.population,
            values,
            entity=entity,
            enabled_assumptions=case.enabled_assumptions,
        )
        assumptions.update(result.assumptions)
        return result.values

    person_values = [resolved("Person", person.inputs) for person in people]
    geography = resolve_inputs(
        case.population,
        {},
        entity="Context",
        enabled_assumptions=case.enabled_assumptions,
        input_names=("interface_geography",),
    )
    assumptions.update(geography.assumptions)
    by_id = dict(zip(ids, person_values, strict=True))
    person_by_id = {person.person_id: person for person in people}
    for members in marital_groups.values():
        values = [by_id[pid] for pid in members]
        if len(members) > 2:
            _refuse(
                "INPUT_CONTRACT_GAP", "A marital unit has one or two members"
            )
        if len(members) == 2:
            if any(
                value["age"] < 65
                or value.get("immigration_status") != "CITIZEN"
                or value.get("takes_up_ssi_if_eligible") is not True
                for value in values
            ):
                _refuse(
                    "RULES_ENGINE_GAP",
                    "Resource deeming absent; spousal-income cap and take-up classification unresolved (#10138, #10243)",
                    "resource_ownership",
                )
            if any(
                not (
                    value.get("is_tax_unit_head")
                    or value.get("is_tax_unit_spouse")
                )
                for value in values
            ):
                _refuse(
                    "RULES_ENGINE_GAP",
                    "Joint SSI claims for tax dependents are unsupported",
                )
    for members in household.tax_units.values():
        heads = [
            pid
            for pid in members
            if by_id[pid].get("is_tax_unit_head") is True
        ]
        spouses = [
            pid
            for pid in members
            if by_id[pid].get("is_tax_unit_spouse") is True
        ]
        if len(heads) != 1 or len(spouses) > 1 or set(heads) & set(spouses):
            _refuse(
                "INPUT_CONTRACT_GAP",
                "A tax unit needs one head and at most one distinct spouse",
            )
        if (
            spouses
            and person_by_id[heads[0]].marital_unit_id
            != person_by_id[spouses[0]].marital_unit_id
        ):
            _refuse(
                "INPUT_CONTRACT_GAP", "Tax spouses must share a marital unit"
            )
    if any(value["age"] < 65 for value in person_values):
        _refuse(
            "RULES_ENGINE_GAP",
            "Blind and disabled recipients below age 65 await SSI7",
            "meets_ssi_disability_criteria",
        )
    for person in people:
        for account in person.retirement_accounts:
            if any(
                not isinstance(value, bool)
                for value in (
                    account.lump_sum_access,
                    account.periodic_payment_eligible,
                    account.employment_exit_required,
                )
            ):
                _refuse(
                    "INPUT_CONTRACT_GAP",
                    "All retirement account statuses must be explicit booleans",
                )
            amounts = (
                account.balance,
                account.withdrawal_penalty,
                account.taxes,
            )
            if any(
                isinstance(x, bool)
                or not isinstance(x, Real)
                or not math.isfinite(x)
                or x < 0
                for x in amounts
            ):
                _refuse(
                    "INPUT_CONTRACT_GAP", "Invalid retirement account amounts"
                )
            if account.balance > 0 or account.periodic_payment_eligible:
                _refuse(
                    "RULES_ENGINE_GAP",
                    "Retirement-fund access and periodic-payment rules unresolved",
                    "retirement_accounts",
                )
    job = {
        "case_id": case.case_id,
        "people": person_values,
        "marital_unit": resolved(
            "MaritalUnit", household.marital_units[0].inputs
        ),
        "tax_unit": resolved("TaxUnit", household.tax_unit_inputs),
        "family": resolved("Family", household.family_inputs),
        "spm_unit": resolved("SPMUnit", household.spm_unit_inputs),
        "household": resolved("Household", household.inputs),
        "year": int(case.period),
        "reform": dict(case.parameter_overrides),
        "extra_variables": list(OUTPUTS),
        "spm": {"geography_kind": geography.values["interface_geography"]},
        "backend": "household",
    }
    family_id = household.household_id + ":family"
    spm_id = household.household_id + ":spm"
    job.update(
        {
            "person_links": [
                {
                    "person_id": person.person_id,
                    "person_marital_unit_id": person.marital_unit_id,
                    "person_tax_unit_id": person.tax_unit_id,
                    "person_household_id": household.household_id,
                    "person_family_id": family_id,
                    "person_spm_unit_id": spm_id,
                }
                for person in people
            ],
            "marital_unit_records": [
                {
                    "marital_unit_id": unit.unit_id,
                    **resolved("MaritalUnit", unit.inputs),
                }
                for unit in household.marital_units
            ],
            "tax_unit_records": [
                {"tax_unit_id": unit_id, **job["tax_unit"]}
                for unit_id in household.tax_units
            ],
            "household_id": household.household_id,
            "family_id": family_id,
            "spm_unit_id": spm_id,
        }
    )
    if len(marital_groups) > 1 or len(household.tax_units) > 1:
        job["backend"] = "dataset"
    if not _finite(job):
        _refuse(
            "INPUT_CONTRACT_GAP", "Non-finite inputs cannot enter a situation"
        )
    return job, tuple(sorted(assumptions))


class SSIRunner:
    """Run independent cases; refusals count once, alongside successful cases."""

    def __init__(
        self, python: str | Path | None = None, *, timeout: float = 1800
    ):
        self.python = Path(
            python or os.environ.get(PYTHON_ENV, DEFAULT_PYTHON)
        ).expanduser()
        self.timeout = timeout
        self.accounting = Accounting()

    def run(self, case: Case) -> SSIResult:
        outcome = self.run_many([case]).outcomes[0]
        if isinstance(outcome, Refusal):
            raise CountedRefusal(outcome)
        return outcome

    def run_many(self, cases: Sequence[Case]) -> BatchResult:
        duplicates = {
            case_id
            for case_id, count in Counter(
                case.case_id for case in cases if isinstance(case.case_id, str)
            ).items()
            if count > 1
        }
        outcomes: dict[int, SSIResult | Refusal] = {}
        jobs = []
        prepared = []
        for index, case in enumerate(cases):
            self.accounting.attempted += 1
            try:
                if case.case_id in duplicates:
                    _refuse(
                        "INPUT_CONTRACT_GAP",
                        "Case IDs must be unique in a batch",
                    )
                job, assumptions = prepare(case)
            except (
                ContractRefusal,
                ValueError,
                TypeError,
                OverflowError,
                AttributeError,
                KeyError,
            ) as error:
                refusal = Refusal(
                    case.case_id,
                    getattr(error, "condition", "INPUT_CONTRACT_GAP"),
                    str(error),
                    getattr(error, "inputs", ()),
                )
                self.accounting.refusals[refusal.condition] += 1
                outcomes[index] = refusal
            else:
                jobs.append(job)
                prepared.append((index, case, assumptions))
        if jobs:
            try:
                if not self.python.is_file():
                    raise ValueError(
                        f"Rules interpreter absent: {self.python}"
                    )
                process = subprocess.run(
                    [str(self.python), str(CHILD)],
                    input=json.dumps({"pin": load_pin(), "cases": jobs}),
                    text=True,
                    capture_output=True,
                    timeout=self.timeout,
                    check=False,
                )
                if process.returncode:
                    raise ValueError("Separate rules interpreter failed")
                payload = json.loads(process.stdout)
                raw = payload["cases"]
                if len(raw) != len(jobs):
                    raise ValueError(
                        "Rules interpreter returned an incomplete batch"
                    )
            except (
                ValueError,
                KeyError,
                TypeError,
                OSError,
                subprocess.TimeoutExpired,
            ) as error:
                raw = [{"error": str(error)} for _ in jobs]
                payload = {}
            for (index, case, assumptions), item in zip(
                prepared, raw, strict=True
            ):
                try:
                    if not isinstance(item, dict):
                        raise ValueError("Malformed rules result")
                    if "error" in item:
                        raise ValueError(item["error"])
                    values = item["person"]
                    if len(values) != len(
                        case.household.people
                    ) or not _finite(values):
                        raise ValueError(
                            "Wrong person count or non-finite rules output"
                        )
                    if any(
                        not (
                            0
                            <= p["ssi"]
                            <= p["ssi_if_takes_up"]
                            <= p["ssi_amount_if_eligible"] + 0.01
                        )
                        for p in values
                    ):
                        raise ValueError(
                            "Federal SSI violates the engine's own applicable FBR bounds"
                        )
                    outcome = SSIResult(
                        case.case_id,
                        int(case.period),
                        tuple(p.person_id for p in case.household.people),
                        tuple(float(p["ssi"]) for p in values),
                        {
                            name: tuple(p[name] for p in values)
                            for name in OUTPUTS
                        },
                        assumptions,
                        payload["versions"],
                    )
                except (
                    KeyError,
                    ValueError,
                    TypeError,
                    OverflowError,
                ) as error:
                    outcome = Refusal(
                        case.case_id, "RULES_ENGINE_GAP", str(error)
                    )
                    self.accounting.refusals[outcome.condition] += 1
                else:
                    self.accounting.accepted += 1
                outcomes[index] = outcome
        assert self.accounting.attempted == (
            self.accounting.accepted + self.accounting.refused
        )
        return BatchResult(
            tuple(outcomes[index] for index in range(len(cases)))
        )
