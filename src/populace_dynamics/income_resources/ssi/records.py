"""Typed frozen-annual-state requests and counted outcomes.

Invariants: ownership stays on each person; links partition the household;
each attempted case has exactly one accepted or refused outcome. No record
represents survey data: the interface accepts caller-supplied inputs only.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RetirementAccount:
    """One owner's account; amounts are dollars before tax deductions."""

    balance: float
    lump_sum_access: bool
    periodic_payment_eligible: bool
    employment_exit_required: bool
    withdrawal_penalty: float
    taxes: float


@dataclass(frozen=True)
class Person:
    person_id: str
    marital_unit_id: str
    tax_unit_id: str
    inputs: Mapping[str, Any]
    retirement_accounts: tuple[RetirementAccount, ...]


@dataclass(frozen=True)
class MaritalUnit:
    unit_id: str
    members: tuple[str, ...]
    inputs: Mapping[str, Any]


@dataclass(frozen=True)
class Household:
    household_id: str
    people: tuple[Person, ...]
    marital_units: tuple[MaritalUnit, ...]
    tax_units: Mapping[str, tuple[str, ...]]
    inputs: Mapping[str, Any]
    tax_unit_inputs: Mapping[str, Any]
    family_inputs: Mapping[str, Any]
    spm_unit_inputs: Mapping[str, Any]
    resource_ownership_validated: bool


@dataclass(frozen=True)
class Case:
    case_id: str
    population: str
    period: int | str
    household: Household
    timing: str
    parameter_overrides: Mapping[str, Any] = field(default_factory=dict)
    enabled_assumptions: tuple[str, ...] = ()


@dataclass(frozen=True)
class SSIResult:
    case_id: str
    period: int
    person_ids: tuple[str, ...]
    federal_ssi: tuple[float, ...]
    intermediate: Mapping[str, tuple[Any, ...]]
    assumptions: tuple[str, ...]
    versions: Mapping[str, str]

    @property
    def total(self) -> float:
        return sum(self.federal_ssi)

    @property
    def potential_federal_ssi(self) -> tuple[float, ...]:
        return self.intermediate["ssi_if_takes_up"]


@dataclass(frozen=True)
class Refusal:
    case_id: str
    condition: str
    detail: str
    inputs: tuple[str, ...] = ()


@dataclass
class Accounting:
    attempted: int = 0
    accepted: int = 0
    refusals: Counter = field(default_factory=Counter)

    @property
    def refused(self) -> int:
        return sum(self.refusals.values())


@dataclass(frozen=True)
class BatchResult:
    outcomes: tuple[SSIResult | Refusal, ...]

    @property
    def denominator(self) -> int:
        return len(self.outcomes)

    @property
    def refusal_counts(self) -> Counter:
        return Counter(
            item.condition
            for item in self.outcomes
            if isinstance(item, Refusal)
        )


class CountedRefusal(ValueError):
    """A refused case already included in its runner's accounting."""

    def __init__(self, refusal: Refusal):
        self.refusal = refusal
        self.condition = refusal.condition
        super().__init__(f"{refusal.condition}: {refusal.detail}")
