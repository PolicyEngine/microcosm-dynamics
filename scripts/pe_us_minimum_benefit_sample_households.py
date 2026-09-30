"""Federal and state tax-benefit effect of the exercise-4 minimum benefit.

ILLUSTRATIVE HOUSEHOLDS, NOT SURVEY DATA.  Nothing here is drawn from the
PSID, the projection or any DYNASIM3 value.  The script is the first use of
:mod:`populace_dynamics.bridge.policyengine_us`:

1. **Microcosm side (this repository's code).**  One illustrative worker: a
   woman born 1958 with covered earnings of 25 percent of the national
   average wage index in each of the 22 years 1980-2001, first entitled to
   her retired-worker benefit in 2024 (at 66).  Her years of coverage come
   from ``min_benefit_track_m.coverage.count_coverage_years``, her PIA from
   ``min_benefit_track_m.rules.history_pia`` (the oracle's statutory AIME
   and ``ss.benefits.pia``), and her reform PIA from
   ``min_benefit_track_m.rules.evaluate_worker`` under exercise 4's
   headline option (``policy.HEADLINE_CELL``: option 2, the standard
   price-indexed minimum, with its printed uniform cut).  Both PIAs are
   carried to 2026 with statutory COLAs (42 USC 415(i)) from the committed
   SSA history (determination years through 2022) and the third-quarter
   CPI-W averages in the policyengine-us checkout (2023-2025), then reduced
   by her claim factor (``rules.claim_factor``) and rounded down to the
   dollar.
2. **PolicyEngine-US side.**  Three households built from that worker (A:
   no other income; B: a $4,800 private pension; C: a $30,000 private
   pension), each in California, Montana and Florida, run for 2026 with
   the current-law benefit and with the reform benefit as
   ``social_security_retirement``.  The bridge decomposes the change in
   ``household_net_income`` into its components, which sum exactly to the
   net change, and repeats the runs with health coverage counted in net
   income (a sensitivity; PolicyEngine-US's default excludes it).

Outputs (JSON with provenance, a Markdown table, and a chart per household
as PNG and SVG) go to ``--out-dir`` and ``--docs-dir``.

Run from the repository root::

    POPULACE_DYNAMICS_PE_US_PYTHON=~/PolicyEngine/policyengine-us/.venv/bin/python \\
    OMP_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python \\
        scripts/pe_us_minimum_benefit_sample_households.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import yaml  # noqa: E402

from populace_dynamics.bridge import policyengine_us as bridge  # noqa: E402
from populace_dynamics.estimates.parameters import (  # noqa: E402
    load_cola_history,
)
from populace_dynamics.min_benefit_track_m import (  # noqa: E402
    coverage,
    rules,
)
from populace_dynamics.min_benefit_track_m.policy import (  # noqa: E402
    HEADLINE_CELL,
    OPTIONS,
    TrackMPolicy,
    policy_for_row,
)
from populace_dynamics.ss.params import load_ssa_parameters  # noqa: E402

SCHEMA_VERSION = "pe_us_bridge.minimum_benefit_sample_households.v1"
ILLUSTRATIVE_LABEL = "Illustrative household, not survey data"
PAYMENT_YEAR = 2026
#: ``gov/ssa/uprating.yaml`` at ``e4363903f3`` marks its entries dated
#: 2022-01-01 through 2026-01-01 as actual third-quarter CPI-W averages
#: (lines 3-9: "Actuals"); later entries are forecasts.  A payment year
#: after 2026 would need a forecast COLA, which this script refuses.
LAST_ACTUAL_CPI_W_ENTRY = 2026
DEFAULT_OUT_DIR = Path(
    "~/microcosm-launch-evidence/dynasim-parity-20260909/"
    "pe-us-bridge-20260930"
).expanduser()
DEFAULT_DOCS_DIR = ROOT / "docs" / "analysis" / "pe_us_bridge_20260930"
OUTPUT_STEM = "pe_us_minimum_benefit_sample_households"

#: The illustrative worker.  Every number here is an input chosen for the
#: illustration; everything derived from them is computed below.
WORKER: dict[str, Any] = {
    "birth_year": 1958,
    "sex": "female",
    "first_earnings_year": 1980,
    "earnings_years": 22,
    "share_of_average_wage_index": 0.25,
    "entitlement_year": 2024,
}
#: Common household facts (annual dollars; assets a stock).
MONTHLY_RENT = 800.0
BANK_ACCOUNT_ASSETS = 1_500.0
HOUSEHOLDS: tuple[dict[str, Any], ...] = (
    {
        "key": "A",
        "label": "Household A",
        "description": (
            "The worker alone: no income besides Social Security, $1,500 in "
            "the bank (under the SSI resource limit), renting for $800 a "
            "month"
        ),
        "taxable_private_pension_income": 0.0,
        "purpose": "SSI-eligible at baseline and under the reform",
    },
    {
        "key": "B",
        "label": "Household B",
        "description": (
            "The same worker with a $4,800-a-year ($400-a-month) private "
            "pension, which puts her countable income above the federal SSI "
            "benefit rate"
        ),
        "taxable_private_pension_income": 4_800.0,
        "purpose": "SSI-ineligible: the SNAP and state-supplement path",
    },
    {
        "key": "C",
        "label": "Household C",
        "description": (
            "The same worker with a $30,000-a-year private pension, enough "
            "for part of her Social Security to be taxable"
        ),
        "taxable_private_pension_income": 30_000.0,
        "purpose": "The federal and state income-tax path",
    },
)
#: The state comparison, each state chosen for one mechanism verified in
#: the policyengine-us code at ``e4363903f3`` (paths under
#: ``policyengine_us/``).
STATES: dict[str, dict[str, Any]] = {
    "CA": {
        "name": "California",
        "mechanism": "A state SSI supplement that PolicyEngine-US models",
        "evidence": [
            "variables/gov/states/ca/cdss/state_supplement/"
            "ca_state_supplement.py:13-17: the supplement is the payment "
            "standard less federal SSI less SSI countable income, floored at "
            "zero, so it is reduced dollar for dollar by countable income "
            "above the federal benefit rate",
            "parameters/gov/states/ca/cdss/state_supplement/payment_standard/"
            "aged_or_disabled/amount/single.yaml:13: the aged or disabled "
            "single payment standard is 1,206.94 a month from 2025-01-01, "
            "with no later entry, so 2026 uses it",
            "parameters/gov/household/household_state_benefits.yaml:338: "
            "ca_state_supplement counts in household benefits from 2026",
        ],
    },
    "MT": {
        "name": "Montana",
        "mechanism": (
            "An income tax that reaches federally taxable Social Security, "
            "and an elderly renter credit that counts all Social Security"
        ),
        "evidence": [
            "variables/gov/states/mt/tax/income/base/mt_agi_indiv.py:13-29: "
            "Montana AGI starts from federal AGI, which includes taxable "
            "Social Security; the separate Montana Social Security "
            "adjustment applies only when "
            "gov.states.mt.tax.income.social_security.applies is true",
            "parameters/gov/states/mt/tax/income/social_security/applies.yaml"
            ":16-18: true from 2021, false from 2024",
            "variables/gov/states/mt/tax/income/credits/"
            "mt_elderly_homeowner_or_renter/"
            "mt_elderly_homeowner_or_renter_credit.py:31-42: a refundable "
            "credit of countable rent less net household income, capped and "
            "multiplied by a gross-income schedule",
            "variables/gov/states/mt/tax/income/credits/"
            "mt_elderly_homeowner_or_renter/"
            "mt_elderly_homeowner_or_renter_credit_gross_household_income.py"
            ":17-23: gross household income adds the untaxed part of Social "
            "Security to federal AGI, so all of it counts",
        ],
    },
    "FL": {
        "name": "Florida",
        "mechanism": (
            "No state income tax, and no state supplement for a person in "
            "her own home"
        ),
        "evidence": [
            "parameters/gov/states/household/"
            "state_income_tax_before_refundable_credits.yaml: 46 entries, "
            "none for Florida",
            "variables/gov/states/fl/dcf/oss/fl_oss_eligible.py:58-76: "
            "Florida's optional state supplement requires a facility living "
            "arrangement; fl_oss_living_arrangement.py:21-37 maps it from "
            "fl_oss_community_care_type, whose default is none "
            "(fl_oss_community_care_type.py:18)",
            "parameters/gov/hhs/medicaid/eligibility/categories/"
            "senior_or_disabled/income/limit/individual.yaml:44-45: Florida's "
            "optional aged Medicaid pathway ends at 88 percent of the "
            "poverty guideline (reported as a memo; health coverage is "
            "outside default net income)",
        ],
    },
}
MEMO_VARIABLES = (
    "medicaid_cost",
    "msp_cost",
    "is_medicaid_eligible",
    "taxable_social_security",
)
HEALTH_OVERRIDE = {
    "gov.simulation.include_health_benefits_in_net_income": True
}


# ---------------------------------------------------------------------------
# Provenance helpers
# ---------------------------------------------------------------------------
def _git(path: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=path,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pe_us_checkout() -> Path:
    return Path(
        os.environ.get(
            "POPULACE_DYNAMICS_PE_US_DIR", "~/PolicyEngine/policyengine-us"
        )
    ).expanduser()


def _yaml_year_values(path: Path) -> dict[int, float]:
    document = yaml.safe_load(path.read_text())
    return {
        int(str(key)[:4]): float(value)
        for key, value in document["values"].items()
    }


# ---------------------------------------------------------------------------
# The Microcosm side: the worker's PIA, the minimum and the COLAs
# ---------------------------------------------------------------------------
def cola_rates(
    payment_year: int, checkout: Path
) -> tuple[dict[int, float], dict[str, Any]]:
    """Determination-year COLAs through ``payment_year - 1``.

    1979-2022 from the committed SSA history
    (``estimates.parameters.load_cola_history``); 2023 onward derived from
    the checkout's third-quarter CPI-W averages by
    :func:`bridge.cola_rates_from_cpi_w`.  The two sources overlap in 2022
    and must agree there.
    """

    if payment_year > LAST_ACTUAL_CPI_W_ENTRY:
        raise ValueError(
            f"payment year {payment_year} needs a COLA determined after the "
            "last actual CPI-W average in this checkout"
        )
    history = load_cola_history()
    uprating_path = (
        checkout / "policyengine_us" / "parameters" / "gov" / "ssa"
    ) / "uprating.yaml"
    cpi_w = {
        year: value
        for year, value in _yaml_year_values(uprating_path).items()
        if year <= LAST_ACTUAL_CPI_W_ENTRY
    }
    derived = bridge.cola_rates_from_cpi_w(cpi_w)
    overlap = sorted(set(derived) & set(history))
    if not overlap:
        raise ValueError("the CPI-W series does not overlap the history")
    for year in overlap:
        if not math.isclose(derived[year], history[year], abs_tol=1e-12):
            raise ValueError(
                f"COLA {year}: CPI-W gives {derived[year]}, the committed "
                f"history {history[year]}"
            )
    rates = {int(year): float(history[year]) for year in history}
    for year, rate in derived.items():
        rates.setdefault(year, rate)
    missing = [year for year in range(1979, payment_year) if year not in rates]
    if missing:
        raise ValueError(f"no COLA for determination years {missing}")
    provenance = {
        "history": dict(history.provenance),
        "history_years": [min(history), max(history)],
        "cpi_w_path": str(uprating_path),
        "cpi_w_sha256": _sha256(uprating_path),
        "cpi_w_third_quarter_averages": {
            str(year): value for year, value in sorted(cpi_w.items())
        },
        "derived_rates": {
            str(year): rate for year, rate in sorted(derived.items())
        },
        "overlap_checked": overlap,
        "rule": (
            "42 USC 415(i)(1)(D): the percentage by which the third-quarter "
            "CPI-W exceeds that of the last cost-of-living computation "
            "quarter, rounded to the nearest one-tenth of 1 percent"
        ),
    }
    return rates, provenance


def worker_benefits(payment_year: int, checkout: Path) -> dict[str, Any]:
    """The worker's PIAs under current law and option 2, carried forward."""

    params = load_ssa_parameters(checkout)
    qc = coverage.load_qc_amounts()
    thresholds = rules.load_aged_thresholds()
    rates, cola_provenance = cola_rates(payment_year, checkout)

    birth = WORKER["birth_year"]
    first = WORKER["first_earnings_year"]
    share = WORKER["share_of_average_wage_index"]
    history = {
        year: round(share * params.nawi[year], 2)
        for year in range(first, first + WORKER["earnings_years"])
    }
    policy = TrackMPolicy()
    years = rules.record_years(
        basis=rules.BASIS_OLD_AGE,
        birth_year=birth,
        window_year=WORKER["entitlement_year"],
    )
    count = coverage.count_coverage_years(
        history,
        birth_year=birth,
        through_year=years.last_year,
        qc=qc,
        nawi=params.nawi,
        policy=policy,
        gap_years=(),
    )
    pia_record = rules.history_pia(
        history,
        birth_year=birth,
        params=params,
        basis=rules.BASIS_OLD_AGE,
        window_year=years.window_year,
        policy=policy,
    )
    inputs = rules.WorkerInputs(
        pia=pia_record.pia,
        work_years=count.years,
        first_pia_year=years.window_year,
        threshold_year=years.threshold_year,
        birth_year=birth,
    )
    option_number = HEADLINE_CELL[0]
    option = OPTIONS[option_number]
    outcomes = {}
    for row in ("MS0", "MS1", "MS4"):
        outcomes[row] = rules.evaluate_worker(
            inputs,
            option_number,
            thresholds=thresholds,
            nawi=params.nawi,
            policy=policy_for_row(row),
        )
    headline = outcomes["MS0"]
    for row, outcome in outcomes.items():
        if outcome != headline:
            raise AssertionError(
                f"{row} changes this worker's outcome: the window and "
                "policy year should not matter for a 2024 entitlement"
            )
    if not headline.on_minimum:
        raise AssertionError(
            f"the illustrative worker is not on the minimum: {headline}"
        )
    option_1 = rules.evaluate_worker(
        inputs, 1, thresholds=thresholds, nawi=params.nawi, policy=policy
    )
    claim = rules.claim_factor(birth, years.window_year, params)
    last_determination = payment_year - 1

    def carried(pia: float) -> dict[str, Any]:
        amount, steps = bridge.carry_pia_forward(
            pia,
            rates,
            first_determination_year=years.threshold_year,
            last_determination_year=last_determination,
        )
        monthly = math.floor(amount * claim + 1e-9)
        return {
            "pia_at_eligibility": pia,
            "cola_steps": list(steps),
            "pia_payment_year": amount,
            "monthly_benefit": monthly,
            "annual_benefit": 12 * monthly,
        }

    current_law = carried(pia_record.pia)
    reform = carried(headline.option_pia)
    reduced_current_law = carried(option_1.option_pia)
    return {
        "label": ILLUSTRATIVE_LABEL,
        "inputs": dict(WORKER),
        "earnings_history": {
            str(year): value for year, value in sorted(history.items())
        },
        "earnings_rule": (
            f"{share:.0%} of the national average wage index "
            "(ss.params.load_ssa_parameters().nawi) in each year, rounded "
            "to the cent"
        ),
        "record_years": years.as_dict(),
        "years_of_coverage": count.as_dict(),
        "pia_record": pia_record.as_dict(),
        "threshold": {
            "year": years.threshold_year,
            "annual": thresholds.for_year(years.threshold_year),
            "source": dict(thresholds.source),
        },
        "option": option.as_dict(),
        "schedule_share": option.schedule.share(headline.work_years_star),
        "outcome": headline.as_dict(),
        "outcome_rows_checked": sorted(outcomes),
        "option_1_outcome": option_1.as_dict(),
        "claim_factor": claim,
        "months_from_full_retirement_age": (
            12 * (years.window_year - birth) - params.fra_months(birth)
        ),
        "current_law": current_law,
        "reform": reform,
        "reduced_current_law_memo": reduced_current_law,
        "cola": cola_provenance,
        "rounding": (
            "PIA: ss.benefits.pia floors to a dime; each COLA step floors to "
            "a dime (42 USC 415(i)(2)(A)(ii)); the monthly benefit is the "
            "PIA times the claim factor rounded down to the dollar (the "
            "415(g) reading recorded in min_benefit_track_m/policy.py's "
            "MINIMUM_ROUNDING_DIME note)"
        ),
        "parameters": {
            "ssa_pe_us_revision": params.pe_us_revision,
            "quarter_of_coverage": dict(qc.source),
        },
    }


# ---------------------------------------------------------------------------
# The PolicyEngine-US side
# ---------------------------------------------------------------------------
def household(
    spec: dict[str, Any], state: str, social_security: float, quarters: int
) -> bridge.BridgeHousehold:
    person = bridge.BridgePerson(
        person_id="worker",
        age=PAYMENT_YEAR - WORKER["birth_year"],
        social_security_retirement=social_security,
        taxable_private_pension_income=spec["taxable_private_pension_income"],
        bank_account_assets=BANK_ACCOUNT_ASSETS,
        pre_subsidy_rent=12 * MONTHLY_RENT,
        medicare_quarters_of_coverage=quarters,
    )
    return bridge.BridgeHousehold(
        household_id=f"household_{spec['key'].lower()}_{state.lower()}",
        state=state,
        people=(person,),
        tax_units=(("worker",),),
        spm_units=(("worker",),),
        marital_units=(("worker",),),
        has_heating_cooling_expense=True,
        takes_up_housing_assistance=False,
        food_preparation_allowed=True,
    )


def run_households(
    worker: dict[str, Any], python: str | None
) -> tuple[list[dict[str, Any]], bridge.RunResult]:
    baseline_ss = float(worker["current_law"]["annual_benefit"])
    reform_ss = float(worker["reform"]["annual_benefit"])
    quarters = 4 * int(worker["years_of_coverage"]["years"])
    cases: list[bridge.RunCase] = []
    plan: list[dict[str, Any]] = []
    for spec in HOUSEHOLDS:
        for state in STATES:
            entry = {"spec": spec, "state": state, "cases": {}}
            for scenario, amount in (
                ("baseline", baseline_ss),
                ("reform", reform_ss),
            ):
                built = household(spec, state, amount, quarters)
                situation = bridge.to_situation(built, PAYMENT_YEAR)
                for variant, overrides in (
                    ("default", {}),
                    ("with_health", HEALTH_OVERRIDE),
                ):
                    case_id = f"{spec['key']}_{state}_{scenario}_{variant}"
                    cases.append(
                        bridge.RunCase(
                            case_id=case_id,
                            situation=situation,
                            expected_state=state,
                            memo=MEMO_VARIABLES,
                            parameter_overrides=overrides,
                        )
                    )
                    entry["cases"][(scenario, variant)] = case_id
                entry.setdefault("situations", {})[scenario] = situation
            plan.append(entry)
    result = bridge.run_policyengine_us(
        cases, year=PAYMENT_YEAR, python=python
    )
    rows = []
    for entry in plan:
        runs = {key: result.runs[cid] for key, cid in entry["cases"].items()}
        default = bridge.decompose(
            runs[("baseline", "default")].tree,
            runs[("baseline", "default")].values,
            runs[("reform", "default")].values,
            reform_tree=runs[("reform", "default")].tree,
        )
        with_health = bridge.decompose(
            runs[("baseline", "with_health")].tree,
            runs[("baseline", "with_health")].values,
            runs[("reform", "with_health")].values,
            reform_tree=runs[("reform", "with_health")].tree,
        )
        spec = entry["spec"]
        rows.append(
            {
                "household": spec["key"],
                "label": spec["label"],
                "state": entry["state"],
                "baseline_social_security_annual": baseline_ss,
                "reform_social_security_annual": reform_ss,
                "decomposition": default,
                "with_health": with_health,
                "memo": {
                    scenario: dict(runs[(scenario, "default")].memo)
                    for scenario in ("baseline", "reform")
                },
                "situations": entry["situations"],
            }
        )
    return rows, result


def check_invariants(rows: list[dict[str, Any]]) -> list[str]:
    """Properties of this run, checked before anything is written."""

    checks = []
    for row in rows:
        d: bridge.Decomposition = row["decomposition"]
        tag = f"{row['household']}-{row['state']}"
        total = sum(c.change_cents for c in d.components)
        assert total == d.net_change_cents, tag
        categories = d.by_category()
        assert sum(v["change"] for v in categories.values()) == total, tag
        ss = categories["social_security"]["change"]
        expected = bridge.to_cents(
            row["reform_social_security_annual"]
            - row["baseline_social_security_annual"]
        )
        assert ss == expected, (tag, ss, expected)
        assert categories["ssi"]["change"] <= 0, tag
        assert categories["snap"]["change"] <= 0, tag
        assert categories["state_benefits"]["change"] <= 0, tag
        assert categories["federal_income_tax"]["change"] <= 0, tag
        assert abs(d.reported_gap_cents) <= 1, tag
    checks.append(
        "every household-state pair: the leaf changes sum exactly (in "
        "cents) to the net change, and the categories to the same total"
    )
    checks.append(
        "the Social Security component equals the Microcosm benefit change"
    )
    checks.append(
        "SSI, SNAP, state benefits and the federal income-tax contribution "
        "never rise when Social Security rises"
    )
    checks.append(
        "PolicyEngine-US's own household_net_income change is within one "
        "cent of the definition's sum"
    )
    return checks


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------
def _money(cents: int, *, signed: bool = False) -> str:
    value = cents / 100
    text = f"{abs(value):,.0f}"
    if signed:
        if cents > 0:
            return f"+{text}"
        if cents < 0:
            return f"−{text}"
        return "0"
    return f"−{text}" if cents < 0 else text


def row_categories(row: dict[str, Any]) -> list[str]:
    """The categories present (nonzero at baseline or reform) in a row."""

    categories = row["decomposition"].by_category()
    return [
        name
        for name in bridge.CATEGORY_ORDER
        if categories[name]["baseline"] or categories[name]["reform"]
    ]


def household_categories(rows: list[dict[str, Any]], key: str) -> list[str]:
    present: set[str] = set()
    for row in rows:
        if row["household"] == key:
            present.update(row_categories(row))
    return [name for name in bridge.CATEGORY_ORDER if name in present]


#: Rows a chart keeps even when unchanged in every state (when present), so
#: an unchanged means-tested program or tax reads as a visible zero.
CHART_KEEP_WHEN_PRESENT = frozenset(
    {
        "social_security",
        "ssi",
        "state_benefits",
        "snap",
        "federal_income_tax",
        "state_income_tax",
    }
)
#: Shorter row labels for the charts (the tables keep the full labels).
CHART_LABELS = {
    **bridge.CATEGORY_LABELS,
    "state_benefits": "State benefits",
    "other_taxes": "Other taxes",
    "health_net": "Health, net",
}


def chart_categories(rows: list[dict[str, Any]], key: str) -> list[str]:
    """Present categories that change somewhere or that the chart keeps."""

    changed: set[str] = set()
    for row in rows:
        if row["household"] == key:
            categories = row["decomposition"].by_category()
            changed.update(
                name for name, entry in categories.items() if entry["change"]
            )
    return [
        name
        for name in household_categories(rows, key)
        if name in changed or name in CHART_KEEP_WHEN_PRESENT
    ]


def markdown(rows: list[dict[str, Any]], document: dict[str, Any]) -> str:
    provenance = document["provenance"]
    worker = document["worker"]
    lines = [
        "# The minimum benefit after taxes and transfers: sample households",
        "",
        f"**{ILLUSTRATIVE_LABEL}.** Three households built around one "
        "illustrative worker, run through PolicyEngine-US for payment year "
        f"{PAYMENT_YEAR}. Amounts are annual 2026 dollars. Taxes and costs "
        "enter as negative contributions, so each column sums to net income "
        "(PolicyEngine-US's `household_net_income`, which by default "
        "excludes health coverage).",
        "",
        f"- Microcosm Dynamics commit `{provenance['microcosm_dynamics']['commit']}`",
        "- PolicyEngine-US "
        f"{provenance['policyengine_us']['version']} at "
        f"`{provenance['policyengine_us']['revision']}`",
        f"- Reform: exercise 4, option {worker['option']['number']} "
        f"({worker['option']['label']}), compared with current-law "
        "scheduled benefits",
        f"- Social Security: {_money(bridge.to_cents(rows[0]['baseline_social_security_annual']))} "
        f"a year under current law, "
        f"{_money(bridge.to_cents(rows[0]['reform_social_security_annual']))} "
        "under the reform",
        "",
        "## Summary",
        "",
        "| Household | State | Social Security | Net income | Share of the "
        "benefit increase kept | Net income with health coverage |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        d = row["decomposition"]
        ss = d.by_category()["social_security"]["change"]
        share = d.net_change_cents / ss if ss else float("nan")
        lines.append(
            f"| {row['household']} | {row['state']} | "
            f"{_money(ss, signed=True)} | "
            f"{_money(d.net_change_cents, signed=True)} | {share:.0%} | "
            f"{_money(row['with_health'].net_change_cents, signed=True)} |"
        )
    lines.append("")
    for spec in HOUSEHOLDS:
        key = spec["key"]
        lines += [f"## {spec['label']}", "", spec["description"] + ".", ""]
        for row in rows:
            if row["household"] != key:
                continue
            d = row["decomposition"]
            categories = d.by_category()
            lines += [
                f"### {spec['label']}, {STATES[row['state']]['name']}",
                "",
                "| Component | Baseline | Reform | Change |",
                "|---|---:|---:|---:|",
            ]
            for name in household_categories(rows, key):
                entry = categories[name]
                lines.append(
                    f"| {bridge.CATEGORY_LABELS[name]} | "
                    f"{_money(entry['baseline'])} | "
                    f"{_money(entry['reform'])} | "
                    f"{_money(entry['change'], signed=True)} |"
                )
            lines.append(
                f"| **Net income** | **{_money(d.baseline_net_cents)}** | "
                f"**{_money(d.reform_net_cents)}** | "
                f"**{_money(d.net_change_cents, signed=True)}** |"
            )
            health = row["with_health"]
            memo_b = row["memo"]["baseline"]
            memo_r = row["memo"]["reform"]
            lines += [
                "",
                "Memo (outside default net income): Medicaid at cost "
                f"{_money(bridge.to_cents(memo_b['medicaid_cost']))} → "
                f"{_money(bridge.to_cents(memo_r['medicaid_cost']))}; "
                "Medicare Savings Program "
                f"{_money(bridge.to_cents(memo_b['msp_cost']))} → "
                f"{_money(bridge.to_cents(memo_r['msp_cost']))}. "
                "Net income with health coverage counted changes by "
                f"{_money(health.net_change_cents, signed=True)}.",
                "",
            ]
    lines += [
        "## Notes",
        "",
        *[f"- {note}" for note in document["caveats"]],
        "",
    ]
    return "\n".join(lines)


def _serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "household": row["household"],
        "label": row["label"],
        "state": row["state"],
        "baseline_social_security_annual": row[
            "baseline_social_security_annual"
        ],
        "reform_social_security_annual": row["reform_social_security_annual"],
        "decomposition": row["decomposition"].as_dict(),
        "with_health_benefits_in_net_income": {
            "net_change": row["with_health"].net_change_cents / 100,
            "categories": {
                name: {k: v / 100 for k, v in entry.items()}
                for name, entry in row["with_health"].by_category().items()
            },
        },
        "memo": row["memo"],
        "situations": row["situations"],
    }


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
#: Colors from the dataviz skill's reference palette (diverging poles and
#: text inks, light surface).
POSITIVE = "#2a78d6"
NEGATIVE = "#e34948"
NET = "#52514e"
INK = "#0b0b0b"
MUTED = "#52514e"
GRID = "#e4e3df"
SURFACE = "#fcfcfb"


def draw_chart(
    rows: list[dict[str, Any]],
    spec: dict[str, Any],
    provenance: dict[str, Any],
    stem: Path,
) -> list[Path]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    matplotlib.rcParams["svg.hashsalt"] = "pe-us-bridge"
    matplotlib.rcParams["font.family"] = "DejaVu Sans"
    # Dollar signs are text, not mathtext delimiters.
    matplotlib.rcParams["text.parse_math"] = False
    key = spec["key"]
    own = [row for row in rows if row["household"] == key]
    names = chart_categories(rows, key)
    labels = [CHART_LABELS[name] for name in names] + ["Net income"]
    changes_by_state = {}
    for row in own:
        categories = row["decomposition"].by_category()
        changes_by_state[row["state"]] = [
            categories[name]["change"] / 100 for name in names
        ] + [row["decomposition"].net_change_cents / 100]
    extent = max(
        max(abs(v) for v in values) for values in changes_by_state.values()
    )
    running_extent = 0.0
    for values in changes_by_state.values():
        cumulative = 0.0
        for value in values[:-1]:
            cumulative += value
            running_extent = max(running_extent, abs(cumulative))
    limit = max(extent, running_extent) * 1.45 or 1.0

    fig, axes = plt.subplots(
        1,
        len(own),
        figsize=(4.1 * len(own), 0.55 * len(labels) + 2.9),
        sharey=True,
        facecolor=SURFACE,
    )
    axes = list(axes) if len(own) > 1 else [axes]
    y_positions = list(range(len(labels)))[::-1]
    for ax, row in zip(axes, own, strict=True):
        ax.set_facecolor(SURFACE)
        values = changes_by_state[row["state"]]
        cumulative = 0.0
        for index, (value, y) in enumerate(
            zip(values, y_positions, strict=True)
        ):
            is_net = index == len(values) - 1
            start = 0.0 if is_net else cumulative
            color = NET if is_net else (POSITIVE if value >= 0 else NEGATIVE)
            if value != 0:
                ax.barh(
                    y,
                    value,
                    left=start,
                    height=0.6,
                    color=color,
                    edgecolor=SURFACE,
                    linewidth=1.5,
                    zorder=3,
                )
            else:
                ax.plot(
                    [start, start],
                    [y - 0.3, y + 0.3],
                    color=MUTED,
                    linewidth=1.2,
                    zorder=3,
                )
            end = start + value
            text = _money(round(value * 100), signed=True)
            offset = limit * 0.03
            if value >= 0:
                ax.text(
                    end + offset,
                    y,
                    text,
                    va="center",
                    ha="left",
                    fontsize=9,
                    color=INK,
                    fontweight="bold" if is_net else "normal",
                )
            else:
                ax.text(
                    end - offset,
                    y,
                    text,
                    va="center",
                    ha="right",
                    fontsize=9,
                    color=INK,
                    fontweight="bold" if is_net else "normal",
                )
            if not is_net:
                cumulative = end
        ax.axvline(0, color=MUTED, linewidth=0.8, zorder=2)
        ax.set_xlim(-limit, limit)
        ax.set_title(
            STATES[row["state"]]["name"],
            loc="left",
            fontsize=11,
            color=INK,
            fontweight="bold",
        )
        ax.grid(axis="x", color=GRID, linewidth=0.6, zorder=0)
        ax.tick_params(axis="x", labelsize=8, colors=MUTED)
        ax.tick_params(axis="y", length=0, labelsize=9.5, colors=INK)
        ax.xaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(
                lambda v, _: (
                    "$0"
                    if v == 0
                    else (
                        f"−${abs(v) / 1000:,.0f}k"
                        if v < 0
                        else f"${v / 1000:,.0f}k"
                    )
                )
            )
        )
        ax.xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(1000))
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
        ax.axhline(y_positions[-1] + 0.5, color=GRID, linewidth=0.8)
    axes[0].set_yticks(y_positions)
    axes[0].set_yticklabels(labels)
    height = fig.get_figheight()

    def from_top(inches: float) -> float:
        return 1 - inches / height

    fig.text(
        0.01,
        from_top(0.18),
        f"{spec['label']}: change in 2026 net income from the minimum benefit",
        ha="left",
        va="top",
        fontsize=13.5,
        fontweight="bold",
        color=INK,
    )
    subtitle = textwrap.fill(
        f"{ILLUSTRATIVE_LABEL}. {spec['description']}. Exercise 4, "
        "option 2, against current law; annual dollars.",
        width=165,
    )
    fig.text(
        0.01,
        from_top(0.52),
        subtitle,
        ha="left",
        va="top",
        fontsize=9,
        color=MUTED,
        linespacing=1.4,
    )
    fig.text(
        0.01,
        0.25 / height,
        "Blue raises net income, red lowers it; the gray bar is the net "
        "change. PolicyEngine-US "
        f"{provenance['policyengine_us']['version']} "
        f"({provenance['policyengine_us']['revision'][:10]}); Microcosm "
        f"Dynamics {provenance['microcosm_dynamics']['commit'][:10]}. "
        "Health coverage is outside net income.",
        ha="left",
        fontsize=7.5,
        color=MUTED,
    )
    fig.subplots_adjust(
        left=0.16,
        right=0.98,
        top=from_top(1.35),
        bottom=0.85 / height,
        wspace=0.12,
    )
    paths = []
    for suffix, kwargs in (
        (".png", {"dpi": 200, "metadata": {"Software": None}}),
        (".svg", {"metadata": {"Date": None, "Creator": None}}),
    ):
        path = stem.with_suffix(suffix)
        fig.savefig(path, facecolor=SURFACE, **kwargs)
        paths.append(path)
    plt.close(fig)
    return paths


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def build(python: str | None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    checkout = pe_us_checkout()
    worker = worker_benefits(PAYMENT_YEAR, checkout)
    rows, result = run_households(worker, python)
    checks = check_invariants(rows)
    code_paths = ["src", "scripts", "tests"]
    provenance = {
        "microcosm_dynamics": {
            "repository": "PolicyEngine/microcosm-dynamics",
            "commit": _git(ROOT, "rev-parse", "HEAD"),
            "code_dirty": bool(
                _git(ROOT, "status", "--porcelain", "--", *code_paths)
            ),
            "script": "scripts/pe_us_minimum_benefit_sample_households.py",
            "bridge": "src/populace_dynamics/bridge/policyengine_us.py",
        },
        "policyengine_us": {
            "checkout": str(checkout),
            "revision": _git(checkout, "rev-parse", "HEAD"),
            "version": result.policyengine_us_version,
            "policyengine_core_version": result.policyengine_core_version,
            "package": result.policyengine_us_package,
            "python": result.python,
        },
        "payment_year": PAYMENT_YEAR,
    }
    caveats = [
        "Illustrative households, not survey data: one worker, chosen so "
        "the minimum binds, in three living situations.",
        "The bridge passes Microcosm's Social Security amounts to "
        "PolicyEngine-US as inputs; it does not run over the projected "
        "population and applies no behavioral response.",
        "The reform is option 2 of exercise 4 (the standard price-indexed "
        "minimum with its printed 12.81 percent uniform cut for new "
        "entitlees). The worker is on the minimum, so the cut does not "
        "reach her; a worker above the minimum would lose 12.81 percent.",
        "The baseline is current-law scheduled benefits. Against option 1 "
        "(reduced current law, the Report's own benchmark) her gain would "
        "be larger; that PIA is in the JSON as a memo, not run through "
        "PolicyEngine-US.",
        "Net income is PolicyEngine-US's household_net_income, which by "
        "default excludes health coverage (Medicaid at cost, Medicare "
        "Savings Programs); the with-health sensitivity and the memo lines "
        "report it.",
        "SNAP amounts for October-December 2026 are PolicyEngine-US's "
        "CPI-U projection of fiscal-2027 values (gov/usda/snap/uprating.yaml;"
        " max_allotment.yaml carries uprating metadata), not USDA's "
        "published figures; every other 2026 parameter on these paths has "
        "a dated 2026 entry or holds an earlier one.",
        "California's aged or disabled payment standard has no 2026 entry "
        "in this checkout, so 2026 uses the 2025 value (1,206.94 a month).",
        "Take-up is PolicyEngine-US's default (full) for SSI, SNAP and "
        "Medicaid; housing assistance is switched off because vouchers are "
        "rationed, and the household can prepare food at home.",
        "COLAs for 2023-2025 are derived from PolicyEngine-US's "
        "third-quarter CPI-W averages under 42 USC 415(i)(1)(D); the "
        "derived 2022 COLA equals the committed SSA history's.",
    ]
    document = {
        "schema_version": SCHEMA_VERSION,
        "label": ILLUSTRATIVE_LABEL,
        "provenance": provenance,
        "worker": worker,
        "households": [dict(spec) for spec in HOUSEHOLDS],
        "states": STATES,
        "common_inputs": {
            "monthly_rent": MONTHLY_RENT,
            "bank_account_assets": BANK_ACCOUNT_ASSETS,
            "has_heating_cooling_expense": True,
            "takes_up_housing_assistance_if_eligible": False,
            "living_arrangements_allow_for_food_preparation": True,
            "medicare_quarters_of_coverage": 4
            * worker["years_of_coverage"]["years"],
        },
        "results": [_serialize_row(row) for row in rows],
        "invariants_checked": checks,
        "caveats": caveats,
    }
    return document, rows


def write(
    document: dict[str, Any], rows: list[dict[str, Any]], directory: Path
) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    written = []
    json_path = directory / f"{OUTPUT_STEM}.json"
    json_path.write_text(
        json.dumps(document, indent=2, sort_keys=False) + "\n"
    )
    written.append(json_path)
    md_path = directory / f"{OUTPUT_STEM}.md"
    md_path.write_text(markdown(rows, document))
    written.append(md_path)
    for spec in HOUSEHOLDS:
        stem = directory / f"household_{spec['key'].lower()}_waterfall"
        written += draw_chart(rows, spec, document["provenance"], stem)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--docs-dir", type=Path, default=DEFAULT_DOCS_DIR)
    parser.add_argument(
        "--pe-us-python",
        default=None,
        help=f"interpreter with policyengine-us (else ${bridge.PE_US_PYTHON_ENV})",
    )
    args = parser.parse_args(argv)
    document, rows = build(args.pe_us_python)
    for directory in (args.out_dir, args.docs_dir):
        for path in write(document, rows, directory):
            print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
