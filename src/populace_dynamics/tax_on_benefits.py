"""Signed Chapter 1 tax on benefits for one invented tax unit.

Transitional adapter through the PE-US bridge, pinned to 2.61.0. Each
counterfactual is a fresh simulation with taxable benefits supplied as an
input, matching ``tob_revenue_oasdi.py:66-70`` without branch caches.
The primary reading is the hub's ruling (b): Chapter 1 liability after
nonrefundable credits and before refundable credits. Netting refundable
credits (reading (a), 2.61.0's ``income_tax``) is reported only as a
labeled sensitivity. Decimal sums and differences run in
``section86.exact_decimal_context``, so the caller's decimal context
changes no result. See ``docs/design/f1_tax_on_benefits.md`` for the
statutory reading and limits.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal, localcontext
from os import PathLike
from typing import Any

from populace_dynamics.bridge import policyengine_us as bridge
from populace_dynamics.section86 import (
    Section86Inclusions,
    exact_decimal_context,
    section86_inclusions,
)

PE_US_VERSION = "2.61.0"
# Filled from the checked 2.61.0 distribution's package-only RECORD.
PE_US_PACKAGE_RECORD_DIGEST = (
    "faab31131caf676439a57eb774248db1750a63c866e1f645aac2fd0b68bf7120"
)
TOB_SPLIT_UNRESOLVED = "TOB_SPLIT_UNRESOLVED"
NON_CHAPTER_1_COMPONENTS = (
    "net_investment_income_tax",  # §1411, Chapter 2A.
    "unreported_payroll_tax",  # Forms 4137/8919, Chapter 21.
)
LIABILITY_VARIABLES = (
    "income_tax",
    "income_tax_refundable_credits",
    "income_tax_before_refundable_credits",
    "income_tax_before_credits",
    "income_tax_capped_non_refundable_credits",
    "recapture_of_investment_credit",  # §50(a), Chapter 1: retained.
    "qualified_retirement_penalty",  # §72(t), Chapter 1: retained.
    "refundable_ctc",  # Diagnostics, never subtracted from primary.
    "eitc",
    "refundable_american_opportunity_credit",
    *NON_CHAPTER_1_COMPONENTS,
)
TAXABILITY_VARIABLES = (
    "tax_unit_social_security_for_taxability",
    "taxable_ss_magi",
    "tax_unit_taxable_social_security_pre_1993",
    "tax_unit_taxable_social_security",
    "taxable_social_security_tier_1",
    "tob_revenue_total",
    "tob_revenue_oasdi",
    "tob_revenue_medicare_hi",
)
# Additional annual facts beyond BridgePerson's fields. Unknown facts are
# refused by name rather than treated as zero. No tax/AGI/inclusion override
# can replace the calculation (reported additional taxes are input facts).
_PERSON_FACTS = frozenset(
    {
        "taxable_interest_income",
        "tax_exempt_interest_income",
        "charitable_cash_donations",
        "is_tax_unit_dependent",
    }
)
_UNIT_FACTS = frozenset(
    {
        "tax_unit_itemizes",
        "itemized_medical_expenses",
        "salt_deduction",
        "unreported_payroll_tax",
        "recapture_of_investment_credit",
        "qualified_retirement_penalty",
        "foreign_tax_credit",
    }
)
_BOOLEAN_FACTS = frozenset({"tax_unit_itemizes", "is_tax_unit_dependent"})


class Section86MismatchError(ValueError):
    """The independent statute calculation differs from the pinned model."""


def _decimal(value: Any) -> Decimal:
    with localcontext(exact_decimal_context()):
        amount = Decimal(str(value))
    if not amount.is_finite():
        raise ValueError("Tax amounts must be finite")
    return amount


@dataclass(frozen=True)
class Chapter1Liability:
    """One state's Chapter 1 liability, keeping PE-US's float32 values.

    ``before_refundable_credits`` is the primary reading (b).
    ``netted_sensitivity`` also subtracts refundable credits (reading (a))
    and is never primary. Neither includes NIIT or unreported payroll tax.
    """

    before_refundable_credits: Decimal
    netted_sensitivity: Decimal
    components: Mapping[str, Decimal]


def chapter1_liability(components: Mapping[str, Any]) -> Chapter1Liability:
    """Remove each non-Chapter-1 term before differencing liabilities.

    PE-US 2.61.0 ``income_tax_before_refundable_credits.py:18-32`` adds
    ordinary/AMT tax, NIIT, §50 recapture, unreported FICA and §72(t), less
    capped nonrefundable credits; ``income_tax.py:18-24`` nets refundable
    credits. Both readings keep recapture and the retirement penalty.
    """
    amounts = {
        name: _decimal(components[name]) for name in LIABILITY_VARIABLES
    }
    with localcontext(exact_decimal_context(*amounts.values())):
        outside = sum(
            (amounts[n] for n in NON_CHAPTER_1_COMPONENTS), Decimal(0)
        )
        return Chapter1Liability(
            before_refundable_credits=(
                amounts["income_tax_before_refundable_credits"] - outside
            ),
            netted_sensitivity=amounts["income_tax"] - outside,
            components=amounts,
        )


@dataclass(frozen=True)
class FundAllocation:
    """Signed dollar differences; no flooring or intermediate rounding."""

    oasdi: Decimal
    hi: Decimal
    total: Decimal


def allocate_liabilities(
    none: Decimal, pre_1993: Decimal, current: Decimal
) -> FundAllocation:
    """Apply the 42 U.S.C. 401 note's signed with-and-without split."""
    with localcontext(exact_decimal_context(none, pre_1993, current)):
        return FundAllocation(
            pre_1993 - none, current - pre_1993, current - none
        )


@dataclass(frozen=True)
class TaxOnBenefits:
    """One unit's split, with PE-US's own values for differential tests.

    ``primary`` differences liabilities after nonrefundable credits and
    before refundable credits (reading (b)). The labeled
    ``refundable_credits_netted_sensitivity`` nets refundable credits
    (reading (a)); it is never primary and never sets a flag.
    """

    year: int
    filing_status: str
    inclusions: Section86Inclusions
    liabilities: Mapping[str, Chapter1Liability]
    primary: FundAllocation
    refundable_credits_netted_sensitivity: FundAllocation
    pe_us: Mapping[str, Decimal]
    flags: tuple[str, ...]
    installation: bridge.PolicyEngineUSInstallation
    source: Mapping[str, Any]


def _add_facts(entry, facts, allowed, period):
    for name, value in facts.items():
        if name not in allowed:
            raise ValueError(f"Unsupported annual input: {name!r}")
        if name in _BOOLEAN_FACTS:
            if not isinstance(value, bool):
                raise ValueError(f"{name} must be a boolean fact")
        elif isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(
                f"{name} must be an annual numeric or boolean fact"
            )
        if not isinstance(value, bool) and (
            not _decimal(value).is_finite() or value < 0
        ):
            raise ValueError(f"{name} must be finite and nonnegative")
        entry[name] = {period: value}


def _interest_components(entry, facts, period):
    """Turn the bridge's total interest into consistent component inputs.

    In the pin, ``interest_income.py:11-14`` adds the taxable and exempt
    input variables. An aggregate input cannot supply either component.
    An explicit taxable amount can supply a total omitted from BridgePerson
    (whose default is zero); otherwise its total must agree with the parts.
    """
    total = _decimal(entry.pop("interest_income")[period])
    exempt = _decimal(facts.get("tax_exempt_interest_income", 0))
    if "taxable_interest_income" in facts:
        taxable = _decimal(facts["taxable_interest_income"])
        with localcontext(exact_decimal_context(total, taxable, exempt)):
            gap = abs(total - taxable - exempt)
        if total and gap > Decimal("0.01"):
            raise ValueError(
                "interest_income disagrees with taxable_interest_income "
                "and tax_exempt_interest_income"
            )
    else:
        with localcontext(exact_decimal_context(total, exempt)):
            taxable = total - exempt
        if taxable < 0:
            raise ValueError(
                "tax_exempt_interest_income exceeds interest_income; "
                "supply taxable_interest_income explicitly"
            )
    entry["taxable_interest_income"] = {period: float(taxable)}
    entry["tax_exempt_interest_income"] = {period: float(exempt)}


@dataclass(frozen=True)
class TaxOnBenefitsInput:
    """One invented unit's household and explicit annual filing facts."""

    household: bridge.BridgeHousehold
    filing_status: str
    lived_apart_all_year: bool | None = None
    person_inputs: Mapping[str, Mapping[str, Any]] | None = None
    tax_unit_inputs: Mapping[str, Any] | None = None


def _prepare_situation(
    unit_input: TaxOnBenefitsInput, year: int
) -> dict[str, Any]:
    """Validate one unit and normalize its facts without mutating inputs."""
    household = unit_input.household
    filing_status = unit_input.filing_status
    lived_apart_all_year = unit_input.lived_apart_all_year
    person_inputs = unit_input.person_inputs
    section86_inclusions(
        0, 0, filing_status, lived_apart_all_year=lived_apart_all_year
    )
    if isinstance(year, bool) or not isinstance(year, int) or year < 1994:
        raise ValueError(
            "Current two-tier law requires an integer year >= 1994"
        )
    if len(household.tax_units) != 1:
        raise ValueError(
            "Unsupported filing configuration: requires exactly one tax unit"
        )
    situation = bridge.to_situation(household, year)
    period = str(year)
    for person_id, facts in (person_inputs or {}).items():
        if person_id not in situation["people"]:
            raise ValueError(f"Unknown person: {person_id!r}")
        _add_facts(
            situation["people"][person_id], facts, _PERSON_FACTS, period
        )
    for person_id, entry in situation["people"].items():
        _interest_components(
            entry, (person_inputs or {}).get(person_id, {}), period
        )
    filers = [
        pid
        for pid, facts in situation["people"].items()
        if not facts.get("is_tax_unit_dependent", {}).get(period, False)
    ]
    if len(filers) != (2 if filing_status == "JOINT" else 1):
        raise ValueError(
            f"Unsupported {filing_status} filer count: {len(filers)}"
        )
    unit = next(iter(situation["tax_units"].values()))
    _add_facts(unit, unit_input.tax_unit_inputs or {}, _UNIT_FACTS, period)
    unit["filing_status"] = {period: filing_status}
    unit["cohabitating_spouses"] = {period: False}
    return situation


def tax_on_benefits_batch(
    units: Mapping[str, TaxOnBenefitsInput],
    year: int,
    *,
    python: str | PathLike | None = None,
) -> dict[str, TaxOnBenefits]:
    """Calculate independent units together in two checked bridge requests.

    Each mapping value describes exactly one tax unit. Every baseline and
    counterfactual receives its own fresh simulation; batching shares the
    interpreter startup and source checks, never household members or tax
    calculations. Results retain the caller's IDs and mapping order.
    """
    if not isinstance(units, Mapping) or not units:
        raise ValueError("units must be a nonempty mapping of named inputs")
    items = tuple(units.items())
    names = [name for name, _ in items]
    if any(
        not isinstance(name, str)
        or not name.strip()
        or any(ord(character) < 32 for character in name)
        for name in names
    ):
        raise ValueError(
            "units requires nonempty string names without controls"
        )
    if len(set(names)) != len(names):
        raise ValueError("units requires unique names")
    for name, unit_input in items:
        if not isinstance(unit_input, TaxOnBenefitsInput):
            raise ValueError(f"{name!r}: expected TaxOnBenefitsInput")
        if not isinstance(unit_input.household, bridge.BridgeHousehold):
            raise ValueError(f"{name!r}: household must be BridgeHousehold")

    situations = {
        name: _prepare_situation(unit_input, year)
        for name, unit_input in items
    }
    # Internal case names are independent of caller IDs, so labels cannot
    # collide even when IDs contain counterfactual names or separators.
    case_prefixes = {
        name: f"f1_unit_{index}" for index, (name, _) in enumerate(items)
    }
    period = str(year)

    def run(cases, variables):
        return bridge.run_policyengine_us_variables(
            cases,
            year=year,
            variables=variables,
            python=python,
            required_version=PE_US_VERSION,
            expected_package_record_digest=PE_US_PACKAGE_RECORD_DIGEST,
        )

    baseline = run(
        [
            bridge.RunCase(
                f"{case_prefixes[name]}_baseline",
                situations[name],
                expected_state=unit_input.household.state,
            )
            for name, unit_input in items
        ],
        TAXABILITY_VARIABLES,
    )
    taxability = {}
    inclusions_by_unit = {}
    cases = []
    for name, unit_input in items:
        values = baseline.runs[f"{case_prefixes[name]}_baseline"].values
        pe = {key: _decimal(values[key][0]) for key in TAXABILITY_VARIABLES}
        inclusions = section86_inclusions(
            pe["tax_unit_social_security_for_taxability"],
            pe["taxable_ss_magi"],
            unit_input.filing_status,
            lived_apart_all_year=unit_input.lived_apart_all_year,
        )
        for variable, expected in (
            ("tax_unit_taxable_social_security_pre_1993", inclusions.pre_1993),
            ("tax_unit_taxable_social_security", inclusions.current),
        ):
            # PE-US evaluates its distinct implementation in float32.
            tolerance = max(
                Decimal("0.01"),
                _decimal(4 * bridge.float32_step(float(expected))),
            )
            with localcontext(exact_decimal_context(pe[variable], expected)):
                gap = abs(pe[variable] - expected)
            if gap > tolerance:
                raise Section86MismatchError(
                    f"{variable}: statute={expected}, PE-US={pe[variable]}"
                )
        taxability[name] = pe
        inclusions_by_unit[name] = inclusions
        for label, amount in (
            ("none", Decimal(0)),
            ("pre_1993", inclusions.pre_1993),
            ("current", inclusions.current),
        ):
            counterfactual = deepcopy(situations[name])
            next(iter(counterfactual["tax_units"].values()))[
                "tax_unit_taxable_social_security"
            ] = {period: float(amount)}
            cases.append(
                bridge.RunCase(
                    f"{case_prefixes[name]}_{label}",
                    counterfactual,
                    expected_state=unit_input.household.state,
                )
            )
    result = run(cases, LIABILITY_VARIABLES)
    output = {}
    labels = ("none", "pre_1993", "current")
    for name, unit_input in items:
        liabilities = {
            label: chapter1_liability(
                {
                    variable: result.runs[
                        f"{case_prefixes[name]}_{label}"
                    ].values[variable][0]
                    for variable in LIABILITY_VARIABLES
                }
            )
            for label in labels
        }
        primary = allocate_liabilities(
            *(liabilities[label].before_refundable_credits for label in labels)
        )
        sensitivity = allocate_liabilities(
            *(liabilities[label].netted_sensitivity for label in labels)
        )
        # The worked examples settle the §86(a)(1) split. Refundable-credit
        # sensitivity is disclosed separately and never makes it unresolved.
        output[name] = TaxOnBenefits(
            year,
            unit_input.filing_status,
            inclusions_by_unit[name],
            liabilities,
            primary,
            sensitivity,
            taxability[name],
            (),
            result.installation,
            result.source,
        )
    return output


def tax_on_benefits(
    household: bridge.BridgeHousehold,
    year: int,
    filing_status: str,
    *,
    lived_apart_all_year: bool | None = None,
    person_inputs: Mapping[str, Mapping[str, Any]] | None = None,
    tax_unit_inputs: Mapping[str, Any] | None = None,
    python: str | PathLike | None = None,
) -> TaxOnBenefits:
    """Compute one unit's current/pre-1993 inclusions and three liabilities.

    Exactly one tax unit is required, with one filer (single/separate/head
    of household) or two filers (joint), plus optional marked dependents.
    Filing status is explicit; separate filers must affirm living apart
    all year. The annual §86(e) lump-sum election, nonresident §871 cases,
    and filing statuses outside the named set are unsupported. Additional
    facts are limited to the documented whitelist above.

    ``person_inputs`` uses BridgePerson IDs. ``tax_unit_inputs`` describes
    the sole unit. Neither mutates the household or caller mappings.
    Gross benefits remain fixed in all three simulations, so deductions
    and credits respond to the changed taxable/nontaxable division.
    """
    return tax_on_benefits_batch(
        {
            "unit": TaxOnBenefitsInput(
                household,
                filing_status,
                lived_apart_all_year,
                person_inputs,
                tax_unit_inputs,
            )
        },
        year,
        python=python,
    )["unit"]
