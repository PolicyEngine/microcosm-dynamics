"""The committed PolicyEngine-US bridge results satisfy the review's fixes.

Reads the JSON and Markdown the sample-household script wrote to
``docs/analysis/pe_us_bridge_20260930/`` (ILLUSTRATIVE households, not
survey data) and checks the properties the review asked for, without
starting policyengine-us:

* finding 3: the run used policyengine-us 2.18.0 from PyPI, its installed
  files matched the RECORD, and the source check passed;
* finding 1: California's 2026 payment standard is CDSS's $1,233.94,
  applied to the California cases only and shown with its source;
* finding 2: the float32 guard traced every changed component and found
  no step without a cause, and household C's pension is off the $30,000
  use-tax edge;
* findings 6, 7 and 11 and the nits: the Commodity Supplemental Food
  Program and state refundable credits have their own rows, no local path
  is written, and the invented history carries no PSID fields;
* the decomposition identity holds in every row, in integer cents;
* round 2: Montana's credit keeps net household income and its reduction
  apart (M1); the Medicaid valuation is described exactly, both ways
  (L2); the script checks refundable credits (L4); half-dollars round up
  (+1,886.50 shows as +1,887); the guard text states its noise band (N2);
  and no public file points at a folder outside the repository (N4).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = ROOT / "docs" / "analysis" / "pe_us_bridge_20260930"
DESIGN_DOC = ROOT / "docs" / "design" / "pe_us_bridge.md"
STEM = "pe_us_minimum_benefit_sample_households"
sys.path.insert(0, str(ROOT / "scripts"))

import pe_us_minimum_benefit_sample_households as script  # noqa: E402

CA_PARAMETER = (
    "gov.states.ca.cdss.state_supplement.payment_standard."
    "aged_or_disabled.amount.single"
)


@pytest.fixture(scope="module")
def document():
    return json.loads((ANALYSIS / f"{STEM}.json").read_text())


@pytest.fixture(scope="module")
def report():
    return (ANALYSIS / f"{STEM}.md").read_text()


def _cents(value):
    return round(value * 100)


def _strings(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, str):
        yield value


def test__artifact__then_it_is_labelled_illustrative(document, report):
    assert document["label"] == "Illustrative household, not survey data"
    assert document["worker"]["label"] == document["label"]
    assert document["label"] in report


def test__artifact__then_the_release_is_the_pinned_pypi_one(document):
    pe = document["provenance"]["policyengine_us"]
    assert pe["release"] == script.PE_US_RELEASE
    assert pe["installed"]["version"] == "2.18.0"
    assert pe["source_check"]["kind"] == "index"
    assert pe["source_check"]["published"] is True
    assert pe["source_check"]["reasons"] == []
    record = pe["record_check"]
    assert (
        record["files_checked"] == script.PE_US_RELEASE["package_record_lines"]
    )
    assert record["mismatched"] == 0 and record["missing"] == 0
    assert record["package_record_digest"] == (
        script.PE_US_RELEASE["package_record_digest"]
    )
    assert document["provenance"]["microcosm_dynamics"]["code_dirty"] is False


def test__artifact__then_no_local_path_is_written(document):
    for text in _strings(document):
        assert not text.startswith(("/", "~")), text
        assert "/Users/" not in text, text


def test__artifact__then_california_uses_the_published_standard(
    document, report
):
    updates = document["provenance"]["policyengine_us"]["parameter_updates"]
    assert [u["parameter"] for u in updates] == [CA_PARAMETER]
    update = updates[0]
    assert update["value"] == 1_233.94
    assert update["installed_value"] == 1_206.94
    assert update["source"]["url"].startswith("https://cdss.ca.gov/")
    assert update["source"]["retrieved"] == "2026-09-30"
    for row in document["results"]:
        for variant, overrides in row["parameter_overrides"].items():
            has = overrides.get(CA_PARAMETER)
            assert has == (1_233.94 if row["state"] == "CA" else None), (
                row["household"],
                row["state"],
                variant,
            )
    assert "1,233.94" in report and update["source"]["url"] in report


def test__artifact__then_the_california_supplement_follows_the_standard(
    document,
):
    """Household A keeps $239.94 a month; household B's $1,123 of monthly
    countable income leaves $110.94 under the published standard."""

    by_case = {(r["household"], r["state"]): r for r in document["results"]}
    a = by_case[("A", "CA")]["decomposition"]["categories"]["state_benefits"]
    b = by_case[("B", "CA")]["decomposition"]["categories"]["state_benefits"]
    assert a["baseline"] == a["reform"] == pytest.approx(12 * 239.94)
    assert b["baseline"] == pytest.approx(12 * (1_233.94 - 1_123))
    assert b["reform"] == 0


def test__artifact__then_the_float32_guard_found_nothing(document, report):
    guard = document["float32_guard"]
    assert guard["comparisons"] == 18
    assert guard["uncaused_changes"] == 0
    for row in document["results"]:
        for variant in ("default", "with_health"):
            entry = row["float32_guard"][variant]
            assert entry["uncaused_changes"] == []
            changed = {
                c["variable"]
                for c in row["decomposition"]["components"]
                if c["change"]
            }
            if variant == "default":
                assert changed <= set(entry["traced_leaves"])
    assert guard["summary"] in report


def test__artifact__then_household_c_is_off_the_use_tax_edge(document):
    pension = {
        h["key"]: h["taxable_private_pension_income"]
        for h in document["households"]
    }
    assert pension["C"] == 31_200
    # California AGI excludes Social Security, so the use tax cannot move.
    for row in document["results"]:
        if row["household"] == "C" and row["state"] == "CA":
            other = row["decomposition"]["categories"]["other_taxes"]
            assert other["change"] == 0


def test__artifact__then_components_sum_exactly_to_net_change(document):
    for row in document["results"]:
        d = row["decomposition"]
        # Components with zero in both runs are omitted from the JSON.
        assert sum(_cents(c["change"]) for c in d["components"]) == (
            _cents(d["net_change"])
        )
        assert sum(_cents(v["change"]) for v in d["categories"].values()) == (
            _cents(d["net_change"])
        )
        assert _cents(d["reform_net_income"]) - _cents(
            d["baseline_net_income"]
        ) == _cents(d["net_change"])


def test__artifact__then_rows_name_each_program_and_credit(document, report):
    assert "csfp" in document["table_rows"]
    assert "Commodity Supplemental Food Program" in report
    assert "caseload-limited" in report
    # Montana's refundable credit on a zero liability is its own row.
    by_case = {(r["household"], r["state"]): r for r in document["results"]}
    montana_a = by_case[("A", "MT")]["decomposition"]["categories"]
    assert montana_a["state_refundable_credits"]["baseline"] == 1_150
    assert montana_a["state_income_tax"]["baseline"] == 0
    # Every table and every chart shows the same rows, zeros included.
    assert "federal_income_tax" in document["chart_rows"]
    assert "state_income_tax" in document["chart_rows"]


def test__artifact__then_the_reform_is_named_plainly(document, report):
    reform = document["reform"]
    assert "73% of the aged poverty threshold for 22 years of work" in reform
    assert "Favreault, Mermin and Steuerle 2006, option 2" in reform
    assert reform in report
    assert "Exercise 4, option 2" not in report


def test__artifact__then_the_invented_history_has_no_psid_fields(document):
    coverage = document["worker"]["years_of_coverage"]
    assert coverage["years"] == 22
    for field in ("flagged", "unobserved_years", "imputed_years"):
        assert field not in coverage


def test__artifact__then_florida_medicaid_loss_is_explained(document, report):
    explanations = document["medicaid_explanations"]
    assert list(explanations) == ["B-FL"]
    text = explanations["B-FL"]
    assert "88%" in text and "individual.yaml:44-45" in text
    assert "QMB-eligible in every month of both runs" in text
    assert "coverage at average program cost" in report
    assert "upper-end" not in report
    # The valuation says what the Medicaid figure is: spending per enrollee
    # from 2023 spending and October 2024 enrollment, all ages.
    assert script.MEDICAID_VALUATION in report
    assert "all ages" in script.MEDICAID_VALUATION


def _by_case(document):
    return {(r["household"], r["state"]): r for r in document["results"]}


def test__artifact__then_half_dollars_round_up(document, report):
    """Household C in Montana gains $1,886.50, shown as $1,887 (``format``
    rounds half to even, to $1,886)."""

    c_mt = _by_case(document)[("C", "MT")]
    assert c_mt["decomposition"]["net_change"] == 1_886.50
    assert c_mt["with_health_benefits_in_net_income"]["net_change"] == (
        1_886.50
    )
    assert "| C | MT | +2,052 | +1,887 | 92% | +1,887 |" in report
    assert "+1,886 " not in report and "+1,886." not in report
    assert "half-dollars rounded up in magnitude" in report


def test__artifact__then_montana_credit_is_described_exactly(document):
    """Round 2's M1: the credit subtracts an income reduction, 5 percent of
    net household income, not net household income itself."""

    evidence = " ".join(document["states"]["MT"]["evidence"])
    assert "less net household income" not in evidence
    assert "less an income reduction" in evidence
    assert "15-30-2337(8)" in evidence and "15-30-2340(4)" in evidence
    doc = DESIGN_DOC.read_text()
    assert "Net household income rises from $1,376" not in doc
    assert "rises from $27,516 to $29,568" in doc
    assert "from $1,376 to $1,478" in doc


def test__artifact__then_the_medicaid_valuation_is_exact_both_ways(
    document, report
):
    """Round 2's L2: 2023 spending over October 2024 Medicaid and CHIP
    enrollment; Florida is $9,200 so, and $7,034 with 2023 enrollment."""

    valuation = document["medicaid_valuation"]
    florida = valuation["per_enrollee"]["FL"]
    assert florida["release"] == pytest.approx(9_200.24, abs=0.005)
    assert florida["same_year"] == pytest.approx(7_033.96, abs=0.005)
    assert florida["spending_entry"] == "2023-01-01"
    assert florida["enrollment_entry"] == "2024-10-01"
    text = valuation["text"]
    assert text in report
    for phrase in (
        "Medicaid and CHIP enrollment",
        "overstate or understate",
        "not a cash loss",
        "$7,034 in Florida (not $9,200)",
    ):
        assert phrase in text, phrase
    # Every memo where she is enrolled is the release's ratio.
    for row in document["results"]:
        expected = valuation["per_enrollee"][row["state"]]["release"]
        for memo in row["memo"].values():
            cost = memo["medicaid_cost"]
            assert cost == 0 or cost == pytest.approx(expected, abs=0.5)
    doc = DESIGN_DOC.read_text()
    assert "may understate" not in doc and "upper-end" not in doc


def test__artifact__then_the_script_checked_refundable_credits(document):
    """Round 2's L4: the doc says credits are checked for wrong-way moves."""

    checks = " ".join(document["invariants_checked"])
    assert "refundable tax credits never rise" in checks
    assert "income taxes never fall" in checks


def test__artifact__then_the_guard_text_states_its_noise_band(
    document, report
):
    """Round 2's N2: the rule is a cent or four float32 steps."""

    summary = document["float32_guard"]["summary"]
    assert "held within a cent" not in summary
    assert "four float32 steps" in summary
    assert "held within a cent" not in report


def test__artifact__then_no_public_file_points_outside_the_repository(
    document, report
):
    """Round 2's N4: the design doc, the JSON and the Markdown name
    repository paths only."""

    texts = [DESIGN_DOC.read_text(), report, *_strings(document)]
    for text in texts:
        assert "microcosm-launch-evidence" not in text
        assert "/Users/" not in text
        assert "evidence folder" not in text


def test__artifact__then_the_medicaid_limit_is_cited_in_full(document):
    """Round 2's N5: ``individual.yaml`` is ambiguous beside other files."""

    text = document["medicaid_explanations"]["B-FL"]
    assert (
        "parameters/gov/hhs/medicaid/eligibility/categories/"
        "senior_or_disabled/income/limit/individual.yaml:44-45"
    ) in text
