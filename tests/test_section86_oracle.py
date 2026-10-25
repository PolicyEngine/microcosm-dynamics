"""Differential §86 tiers on invented units with an opt-in tax interpreter.

The independent implementation uses Decimal arithmetic. The published
PolicyEngine-US implementation returns float32 arrays, so differences up to
the stated float32 allowance are rounding, not statutory counterexamples.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.bridge import policyengine_us as bridge
from populace_dynamics.section86 import section86_inclusions
from populace_dynamics.tax_on_benefits import PE_US_PACKAGE_RECORD_DIGEST

_STATUSES = ("SINGLE", "JOINT", "HEAD_OF_HOUSEHOLD", "SEPARATE")
_VARIABLES = (
    "taxable_ss_magi",
    "tax_unit_combined_income_for_social_security_taxability",
    "tax_unit_taxable_social_security",
    "tax_unit_taxable_social_security_pre_1993",
    "taxable_social_security_tier_1",
    "taxable_social_security_tier_2",
    "filing_status",
    "cohabitating_spouses",
)


@dataclass(frozen=True)
class InventedUnit:
    status: str
    benefits: Decimal
    taxable_interest: Decimal
    exempt_interest: Decimal = Decimal("0")

    @property
    def modified_agi(self):
        # These units have only taxable and tax-exempt interest, with no
        # deductions or exclusions to reverse under §86(b)(2).
        return self.taxable_interest + self.exempt_interest


@pytest.fixture(scope="module")
def oracle_python():
    configured = os.environ.get("POPULACE_DYNAMICS_PE_US_PYTHON")
    if not configured or not Path(configured).expanduser().is_file():
        pytest.skip("no explicitly configured policyengine-us interpreter")
    from tests.test_tax_on_benefits_oracle import (
        _PinnedOracleWorker,
        _timed_pin_check,
    )

    # Run the real source/RECORD verification once for this module. Every
    # calculation still checks the child installation payload against that
    # checked installation; no inputs, formula results, or pins are mocked.
    checked = lru_cache(maxsize=1)(_timed_pin_check)
    worker = _PinnedOracleWorker(configured)

    def run_checked_job(interpreter, source, stdin, timeout):
        # Allow the host's slow policy-parameter I/O more time for these
        # invented-unit batches; inspection and pin-check budgets stay put.
        if source == bridge._NAMED_VARIABLE_SOURCE:
            timeout = max(timeout, 3600)
        return worker.run(interpreter, source, stdin, timeout)

    try:
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(bridge, "_checked_installation", checked)
            patch.setattr(bridge, "_run_child", run_checked_job)
            yield configured
    finally:
        worker.close()


def _situation(unit, case_id, year):
    head = bridge.BridgePerson(
        f"{case_id}_head",
        70,
        social_security_retirement=float(unit.benefits),
    )
    people = [head]
    if unit.status == "JOINT":
        people.append(bridge.BridgePerson(f"{case_id}_spouse", 70))
    elif unit.status == "HEAD_OF_HOUSEHOLD":
        people.append(bridge.BridgePerson(f"{case_id}_child", 10))
    members = tuple(person.person_id for person in people)
    marital_units = (
        (members,)
        if unit.status == "JOINT"
        else tuple((person.person_id,) for person in people)
    )
    household = bridge.BridgeHousehold(
        case_id,
        "TX",
        tuple(people),
        (members,),
        (members,),
        marital_units,
    )
    situation = bridge.to_situation(household, year)
    tax_unit = next(iter(situation["tax_units"].values()))
    tax_unit["filing_status"] = {str(year): unit.status}
    # SEPARATE denotes spouses who lived apart throughout the year.
    tax_unit["cohabitating_spouses"] = {str(year): False}
    # In the pin, interest_income adds the taxable and exempt components;
    # leave that aggregate calculated and supply the two components.
    for person_inputs in situation["people"].values():
        person_inputs.pop("interest_income")
    situation["people"][head.person_id]["taxable_interest_income"] = {
        str(year): float(unit.taxable_interest)
    }
    situation["people"][head.person_id]["tax_exempt_interest_income"] = {
        str(year): float(unit.exempt_interest)
    }
    if unit.status == "HEAD_OF_HOUSEHOLD":
        situation["people"][members[1]]["is_tax_unit_dependent"] = {
            str(year): True
        }
    return situation


def _boundary_units():
    result = []
    for status in _STATUSES:
        benefits = Decimal("30000" if status == "JOINT" else "20000")
        thresholds = (32000, 44000) if status == "JOINT" else (25000, 34000)
        for threshold in thresholds:
            for offset in (Decimal("-0.01"), Decimal("0"), Decimal("0.01")):
                interest = Decimal(threshold) + offset - benefits / 2
                result.append(InventedUnit(status, benefits, interest))
    return result


def _assert_float32_close(actual, expected, label):
    expected = float(expected)
    allowance = max(
        0.01,
        4 * bridge.float32_step(actual),
        4 * bridge.float32_step(expected),
    )
    assert actual == pytest.approx(expected, abs=allowance, rel=0), (
        f"{label}: difference exceeds float32 roundoff allowance "
        f"${allowance:g}; actual={actual}, independent={expected}"
    )


_INCOME_BANDS = (
    (0, 100_000, 0, 2_500_000),
    (100_000, 2_000_000, 2_500_000, 3_400_000),
    (2_000_000, 5_000_000, 3_400_000, 10_000_000),
    (5_000_000, 15_000_000, 10_000_000, 30_000_000),
)
# Stratification keeps all four configurations and income bands in the
# batch, including Hypothesis's simplest example, rather than allowing
# its first generated list to contain sixteen identical zero-income units.
_GENERATED_UNITS = st.tuples(
    *(
        st.tuples(
            st.just(status),
            st.integers(min_value=benefit_low, max_value=benefit_high),
            st.integers(min_value=income_low, max_value=income_high),
            st.integers(min_value=band * 10_000, max_value=2_000_000),
        )
        for status in _STATUSES
        for band, (
            benefit_low,
            benefit_high,
            income_low,
            income_high,
        ) in enumerate(_INCOME_BANDS)
    )
)


@pytest.fixture(scope="module")
def generated_units():
    samples = []

    @given(generated=_GENERATED_UNITS)
    @settings(max_examples=3, derandomize=True, deadline=None, database=None)
    def collect(generated):
        samples.extend(
            InventedUnit(
                status,
                Decimal(benefits) / 100,
                Decimal(interest) / 100,
                Decimal(exempt_interest) / 100,
            )
            for status, benefits, interest, exempt_interest in generated
        )

    collect()
    assert len(samples) == 48
    return tuple(samples)


@pytest.mark.parametrize("year", [2024, 2026])
def test_independent_tiers_against_published_formulas(
    year, oracle_python, generated_units
):
    units = _boundary_units()
    units.extend(generated_units)
    units.extend(
        [
            InventedUnit("SINGLE", Decimal("20000"), Decimal("30000")),
            InventedUnit("SINGLE", Decimal("40000"), Decimal("190000")),
            InventedUnit("SINGLE", Decimal("100"), Decimal("33975")),
        ]
    )
    cases = [
        bridge.RunCase(
            f"section86_{index}",
            _situation(unit, f"section86_{index}", year),
            expected_state="TX",
        )
        for index, unit in enumerate(units)
    ]
    # One checked interpreter invocation batches every invented unit for
    # this year; the two inclusion formulas remain separate implementations.
    result = bridge.run_policyengine_us_variables(
        cases,
        year=year,
        variables=_VARIABLES,
        python=oracle_python,
        required_version="2.61.0",
        expected_package_record_digest=PE_US_PACKAGE_RECORD_DIGEST,
    )
    for case, unit in zip(cases, units, strict=True):
        run = result.runs[case.case_id]
        independent = section86_inclusions(
            unit.benefits,
            unit.modified_agi,
            unit.status,
            lived_apart_all_year=True,
        )
        assert run.values["filing_status"] == (unit.status,)
        assert run.values["cohabitating_spouses"] == (False,)
        expected = {
            "taxable_ss_magi": unit.modified_agi,
            "tax_unit_combined_income_for_social_security_taxability": (
                independent.combined_income
            ),
            "tax_unit_taxable_social_security": independent.current,
            "tax_unit_taxable_social_security_pre_1993": independent.pre_1993,
        }
        adjusted_base = Decimal("44000" if unit.status == "JOINT" else "34000")
        retained_cap = Decimal("6000" if unit.status == "JOINT" else "4500")
        # At and above the adjusted base, PE-US tier_1 is the retained
        # §86(a)(2)(A)(ii) bracket contribution, not the pre-1993 inclusion.
        expected_tier_1 = (
            min(independent.pre_1993, retained_cap)
            if independent.combined_income >= adjusted_base
            else independent.pre_1993
        )
        expected["taxable_social_security_tier_1"] = expected_tier_1
        expected["taxable_social_security_tier_2"] = (
            independent.current - expected_tier_1
        )
        for variable, amount in expected.items():
            assert run.variable_entities[variable] == "tax_units"
            actual = run.values[variable]
            assert len(actual) == 1
            _assert_float32_close(
                actual[0], amount, f"{year}/{case.case_id}/{unit!r}/{variable}"
            )
