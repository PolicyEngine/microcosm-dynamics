"""Exact compatibility with the depletion-cut artifact's invented G inputs.

Verification class: statutory conformance regression. Admitted scope: the
committed illustrative couple's gross benefit fields, in every recorded
month. This admits no population, behavioral or forecast claim and starts
no policyengine-us process. The published-NAWI unit parameter bundle
reproduces every recorded field exactly, with zero tolerance.

The artifact's ``track-b-g-v1`` text describes its original provenance;
compatibility with current G does not change that recorded version.
"""

from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as gross
from tests.track_b_gross_benefit_support import ssa_params

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = (
    ROOT
    / "docs"
    / "analysis"
    / "pe_us_depletion_cut_20261001"
    / "pe_us_depletion_cut_sample_households.json"
)
DOCUMENT = json.loads(ARTIFACT.read_text())
PARAMS = ssa_params()
G_OUTPUT_FIELDS = frozenset(
    {
        "pia",
        "family_maximum",
        "family_maximum_binding",
        "worker_monthly",
        "spouse_original_benefit",
        "spouse_payable",
        "spouse_monthly",
    }
)
# ``scheduled_benefits`` uses G's couple result for each spouse household.
# The others use the separately calculated low/medium single-worker rates.
G_HOUSEHOLDS = tuple(
    spec for spec in DOCUMENT["households"] if spec.get("spouse")
)
G_CASES = tuple(
    (spec, month)
    for spec in G_HOUSEHOLDS
    for month in DOCUMENT["benefits"]["couple"]["benefit_months"]
)


def _assert_recorded_g_fields(spec, month_text):
    """Rebuild ``couple_benefits`` inputs from recorded fields only."""

    assert spec["worker"] == "medium_earner"
    worker = DOCUMENT["benefits"][spec["worker"]]
    couple = DOCUMENT["benefits"]["couple"]
    spouse_inputs = couple["spouse_inputs"]
    eligibility = worker["record_years"]["threshold_year"]
    year, month_number = map(int, month_text.split("-"))
    month = gross.YearMonth(year, month_number)
    percents = {
        int(year): Fraction(value)
        for year, value in couple["december_cola_percents"].items()
    }
    spouse_age_months = 12 * (
        spouse_inputs["spouse_benefit_entitlement_year"]
        - spouse_inputs["birth_year"]
    )
    spouse_months_early = max(
        0,
        PARAMS.fra_months(spouse_inputs["birth_year"]) - spouse_age_months,
    )
    assert spouse_months_early == (
        couple["spouse_months_before_full_retirement_age"]
    )
    assert spouse_inputs["spouse_benefit_entitlement_year"] >= (
        worker["inputs"]["entitlement_year"]
    )
    assert worker["months_from_full_retirement_age"] == 0
    assert spouse_inputs["own_covered_earnings"] == "none"
    record = gross.WorkerRecord(
        kind=gross.FamilyKind.RETIREMENT,
        eligibility_year=eligibility,
        eligibility_pia=Fraction(repr(worker["pia_record"]["pia"])),
        cola_percents=gross.applicable_cola_percents(
            eligibility, month, percents
        ),
        worker_reduction_months=0,
        worker_birth_year=worker["inputs"]["birth_year"],
    )
    state = gross.record_state(record, PARAMS)
    spouse = gross.Beneficiary(
        beneficiary_id="spouse",
        role=gross.Role.SPOUSE,
        reduction_months=spouse_months_early,
    )
    result = gross.household_benefits(
        {"worker": gross.HouseholdRecord("worker", state, (spouse,))},
        payment_month=month,
        params=PARAMS,
    ).records["worker"]
    row = result.by_id()["spouse"]
    actual = {
        "pia": str(result.pia),
        "family_maximum": str(result.family_maximum),
        "family_maximum_binding": result.family_maximum_binding,
        "worker_monthly": result.whole_dollar_worker,
        "spouse_original_benefit": str(row.original_benefit),
        "spouse_payable": str(row.auxiliary_payable),
        "spouse_monthly": row.whole_dollar_auxiliary,
    }
    # The generator refused unequal months before recording this one common
    # result. Require every recorded field in every month, without tolerance.
    assert set(couple["result"]) == G_OUTPUT_FIELDS
    assert actual == couple["result"]
    for cut_row in DOCUMENT["results"]:
        if cut_row["household"] == spec["key"]:
            assert cut_row["cuts"]["worker"]["monthly_scheduled"] == (
                actual["worker_monthly"]
            )
            assert cut_row["cuts"]["spouse"]["monthly_scheduled"] == (
                actual["spouse_monthly"]
            )


def assert_recorded_g_compatibility():
    """Run the complete proof before permitting the one-file pin exception."""

    assert G_CASES, "the compatibility exclusion requires recorded G cases"
    for spec, month_text in G_CASES:
        _assert_recorded_g_fields(spec, month_text)


@pytest.mark.parametrize(
    "spec,month_text",
    G_CASES,
    ids=[f"{spec['key']}-{month}" for spec, month in G_CASES],
)
def test__artifact_g_inputs__then_current_g_matches_every_recorded_field(
    spec, month_text
):
    _assert_recorded_g_fields(spec, month_text)


@given(st.sampled_from(G_CASES))
def test__given_a_recorded_g_case__then_every_output_matches_exactly(case):
    """Property counterpart to the exhaustive monthly example checks."""

    _assert_recorded_g_fields(*case)
