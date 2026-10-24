#!/usr/bin/env python3
"""Render the SSI0 source contract from the committed chain inventory.

This reads metadata only. Unmapped inputs deliberately become refusals;
adding a chain input can never silently create a zero-valued assumption.
The per-population mappings below are reviewed sourcing decisions, not
survey readers or a claim that every historical wave carries each item.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SSI = ROOT / "src/populace_dynamics/income_resources/ssi"
POPULATIONS = ("PSID", "SIPP", "Microcosm")
CATALOG = "income-resources-20261021/research/data-sources.md"
FRAME = "docs/plans/microcosm-start.md:267-284"
FAMILY = "src/populace_dynamics/data/family_income.py:150-263"


def source(citation: str, milestone: str, detail: str) -> dict:
    return {
        "status": "source",
        "citation": citation,
        "reader_status": "not_read_by_ssi_runner",
        "reader_milestone": milestone,
        "detail": detail,
    }


def refuse(detail: str, condition: str = "INPUT_CONTRACT_GAP") -> dict:
    return {"status": "refuse", "condition": condition, "blocks": detail}


def mappings() -> dict:
    result = {population: {} for population in POPULATIONS}
    psid = result["PSID"]
    sipp = result["SIPP"]
    frame = result["Microcosm"]
    psid_income = {
        "employment_income": "head_labor/wife_labor; retain business and farm components separately",
        "self_employment_income": "head_farm/head_business_labor/wife_business_labor; SSI crosswalk must separate labor and asset portions",
        "pension_income": "head_retirement_pensions/head_annuities and spouse retirement; 2023 ER85542/ER85544/ER85548",
        "social_security": "head/wife/other-family-member Social Security totals",
        "veterans_benefits": "head_va_pension/ofum_va_pension; other veterans benefits still need D1 adjudication",
        "workers_compensation": "head_workers_comp/wife_workers_comp/ofum_workers_comp",
        "unemployment_compensation": "head_unemployment/wife_unemployment/ofum_unemployment",
        "retirement_distributions": "2023 ER85546 IRA income and Section W43-W49; distinguish cash-outs from recurring pensions",
        "alimony_income": "head_alimony (ER27974 in 2005); recipient-specific historical coverage needs D1",
        "child_support_received": "head_child_support/wife_child_support/ofum_child_support",
        "financial_assistance": "head_help_relatives/head_help_others and spouse/other-member counterparts",
        "dividend_income": "head_dividends/wife_dividends",
        "interest_income": "head_interest/wife_interest",
        "rental_income": "head_rent/wife_rent",
    }
    for name, detail in psid_income.items():
        psid[name] = source(
            f"{CATALOG} §1; {FAMILY}",
            "D1, WP1",
            detail
            + "; preserve owner; aggregated OFUM amounts cannot be assigned to one person",
        )
    psid["age"] = source(
        f"{CATALOG} §1; {FAMILY}",
        "D1",
        "Head ER25017 and spouse ER25019 in 2005; cross-year person ages need wave-specific verification",
    )
    for name, item in {
        "bank_account_assets": "transaction accounts (historical Sx05)",
        "stock_assets": "stocks/mutual funds (Sx11; 2023 ER83912)",
        "bond_assets": "other investments (Sx15); disaggregate bonds before use",
    }.items():
        psid[name] = source(
            f"{CATALOG} §1 wealth waves and contents",
            "D1, WP1",
            item
            + "; family balances need validated person and marital-unit ownership; never copy a household vector to one owner",
        )
    for name, item in {
        "social_security": "ESSSMNYN/TSSSAMT",
        "pension_income": "ERET[1-8]MNYN/TRET[1-8]AMT",
        "retirement_distributions": "TTHR_INC_AMT/TIRA_INC_AMT",
    }.items():
        sipp[name] = source(
            f"{CATALOG} §4 relevant variables; 2024 SIPP User's Guide",
            "D2",
            item
            + "; cross-release equivalence and annualization await label-verified D2 readers",
        )
    for name, item in {
        "bank_account_assets": "TVAL_BANK",
        "stock_assets": "TVAL_STMF",
        "bond_assets": "TVAL_BOND",
    }.items():
        sipp[name] = source(
            f"{CATALOG} §4 Assets Table 4-1; microcosm#1215 body (person leaves TVAL_*, household totals THVAL_*)",
            "D2, WP1",
            item
            + "; retain person ownership and spouse dependence; verify against release-specific dictionary",
        )
    psid["receives_ssi"] = source(
        f"{CATALOG} §1 income and SSI variables",
        "D1",
        "G25F receipt, G26F/G26FPER amount/unit; ER85536/ER85566/ER85604 distinguish reference person, spouse and other family members; verify recipient ownership before use",
    )
    sipp["receives_ssi"] = source(
        f"{CATALOG} §4 relevant variables",
        "D2",
        "RSSI_YRYN/RSSI_MNYN/TSSI_AMT; receipt reports are separate from potential full-take-up eligibility",
    )
    frame["receives_ssi"] = refuse(
        "A projected Microcosm start must not reuse frame SSI_VAL or calibrated take-up as projected receipt; SSI4 supplies take-up and SSI9 supplies timing (design §3.3)"
    )
    frame_income = {
        "employment_income": "employment_income_before_lsr",
        "self_employment_income": "self_employment_income_before_lsr",
        "social_security": "social_security_retirement + social_security_disability + social_security_survivors + social_security_dependents",
        "pension_income": "taxable_private_pension_income + tax_exempt_private_pension_income",
        "retirement_distributions": "taxable_ira_distributions, tax_exempt_ira_distributions, taxable_401k_distributions, taxable_403b_distributions, taxable_sep_distributions, keogh_distributions",
        "veterans_benefits": "veterans_benefits",
        "workers_compensation": "workers_compensation",
        "unemployment_compensation": "unemployment_compensation",
        "child_support_received": "child_support_received",
        "alimony_income": "alimony_income",
        "dividend_income": "qualified_dividend_income + non_qualified_dividend_income",
        "interest_income": "taxable_interest_income + tax_exempt_interest_income",
        "rental_income": "rental_income",
    }
    for name, item in frame_income.items():
        frame[name] = source(
            FRAME,
            "WP1",
            item
            + "; use only a certified release containing these fields; sparse/dense starts listed at line 284 lack several of them",
        )
    frame["age"] = source(
        "microcosm#1215 body, Reproduce (age >= 18); docs/plans/microcosm-start.md:293-294",
        "WP1",
        "age, retained for each person in the certified starting release",
    )
    for name in ("bank_account_assets", "stock_assets", "bond_assets"):
        frame[name] = refuse(
            f"{name}: current household-vector carry does not establish person or marital-unit ownership; microcosm#1215; WP1 must rebuild and validate ownership",
            "FRAME_LACKS_RESOURCES",
        )
    for population in POPULATIONS:
        for role in ("is_tax_unit_head", "is_tax_unit_spouse"):
            result[population][role] = refuse(
                f"Missing {role}: typed tax and marital links must establish this role explicitly. The reviewed catalog/frame map does not validate a tax-unit role crosswalk; do not derive legal spouse status from row order or PSID's partner-inclusive wife label. D1/D2/WP1 must adjudicate the links."
            )
        result[population]["takes_up_ssi_if_eligible"] = {
            "status": "assumption",
            "assumption_id": "POTENTIAL_FULL_TAKEUP",
            "detail": "Potential-benefit estimand only. Observed receipt is separate: PSID §1 G25F/G26F/G26FPER and ER85536/ER85566/ER85604 (D1); SIPP §4 RSSI_YRYN/RSSI_MNYN/TSSI_AMT (D2). The frame's calibrated takes_up_ssi_if_eligible is replaced by SSI4 for projected receipt, design §3.3.",
        }
    return result


def category(name: str) -> str:
    if "tax_unit" in name or "separated" in name:
        return "links"
    if name in ("bank_account_assets", "stock_assets", "bond_assets"):
        return "resource ownership"
    if any(token in name for token in ("immigration", "citizen", "quarter")):
        return "immigration and qualifying quarters"
    if any(token in name for token in ("blind", "disab", "age")):
        return "ABD status"
    if name.startswith("ssi_") and any(
        token in name
        for token in (
            "shelter",
            "meal",
            "food",
            "household",
            "care",
            "facility",
        )
    ):
        return "living arrangement and in-kind support"
    if "takes_up" in name:
        return "take-up"
    return "income and SSI formula inputs"


def build() -> dict:
    inventory = json.loads((SSI / "inventory.json").read_text())
    mapping = mappings()
    rows = []
    for item in inventory["inputs"]:
        name = item["name"]
        rows.append(
            {
                "name": name,
                "kind": "engine",
                "entity": item["entity"],
                "period": item["period"],
                "value_type": item["value_type"],
                "category": category(name),
                "populations": {
                    population: mapping[population].get(
                        name,
                        refuse(
                            f"Missing {name}: the reviewed catalog has no verified source/crosswalk for this SSI input. Do not infer it from Social Security receipt, family totals or an engine default; D1/D2/WP1 must adjudicate it before population use."
                        ),
                    )
                    for population in POPULATIONS
                },
            }
        )
    contexts = {
        "household_links": (
            "links",
            "Household.household_id and Household.people define unique person membership",
        ),
        "marital_unit_links": (
            "links",
            "Person.marital_unit_id and MaritalUnit.members define actual spouse links; PSID's wife label includes cohabiting partners and cannot establish legal marriage alone",
        ),
        "tax_unit_links": (
            "links",
            "Person.tax_unit_id and Household.tax_units partition persons, with head/dependent roles supplied explicitly where inventoried",
        ),
        "resource_ownership": (
            "resource ownership",
            "Each person owns the bank/stock/bond leaves; resource_ownership_validated attests a person/marital-unit allocation; family or household totals alone are insufficient",
        ),
        "retirement_accounts.balance": (
            "retirement accounts",
            "Each RetirementAccount.balance belongs to one Person; PSID §1 P20/P20P90 and ER83934 are balance candidates (D1, WP1); SIPP §4 Table 4-1 is a candidate (D2, WP1); frame lacks DC balances",
        ),
        "retirement_accounts.lump_sum_access": (
            "retirement accounts",
            "Each RetirementAccount.lump_sum_access is explicit; PSID §1 1984 C46 withdrawal entitlement is a candidate, other waves/access equivalence remain unverified (D1, WP1)",
        ),
        "retirement_accounts.periodic_payment_eligible": (
            "retirement accounts",
            "Each RetirementAccount.periodic_payment_eligible is explicit; pension receipt does not establish eligibility to elect periodic payment",
        ),
        "retirement_accounts.employment_exit_required": (
            "retirement accounts",
            "Each RetirementAccount.employment_exit_required records whether leaving work is necessary for any payment",
        ),
        "retirement_accounts.withdrawal_penalty": (
            "retirement accounts",
            "Each RetirementAccount.withdrawal_penalty records the actual contractual withdrawal penalty; treatment of the 26 USC 72(t) additional tax remains an SSI2 question",
        ),
        "retirement_accounts.taxes": (
            "retirement accounts",
            "Each RetirementAccount.taxes is separate from penalties; do not deduct taxes to value a resource (POMS SI 01120.210 A.3)",
        ),
        "timing_convention": (
            "timing",
            "Case.timing must declare the frozen annual state; annual income in equal twelfths and resources frozen at annual values; actual monthly receipt waits for SSI9",
        ),
        "interface_geography": (
            "interface measurement selection",
            "The public household calculator also requests an SPM geography selection; set its spm geography_kind option explicitly to national for this federal-only interface",
        ),
    }
    for name, (group, detail) in contexts.items():
        cells = {population: refuse(detail) for population in POPULATIONS}
        if name == "household_links":
            cells["PSID"] = source(
                f"{CATALOG} §1 unit and sample", "D1, WP1", detail
            )
            cells["SIPP"] = source(
                f"{CATALOG} §4 publisher/unit", "D2, WP1", detail
            )
            cells["Microcosm"] = source(
                "microcosm#1215 body, Reproduce (household and person table)",
                "WP1",
                detail,
            )
        if name == "marital_unit_links":
            cells["Microcosm"] = source(
                "microcosm#1215 body, Reproduce (person_marital_unit_id)",
                "WP1",
                detail + "; verify spouse and head roles independently",
            )
        if name.startswith("retirement_accounts."):
            for cell in cells.values():
                cell["engine_condition"] = "RULES_ENGINE_GAP"
                cell["engine_blocks"] = (
                    "Any positive account balance whose withdrawal/periodic-payment facts require retirement-fund treatment the pinned engine cannot express correctly; POMS SI 01120.210; SSI2 must adjudicate"
                )
        if name == "retirement_accounts.balance":
            cells["PSID"] = source(
                f"{CATALOG} §1 pension table P20/P20P90 and ER83934",
                "D1, WP1",
                detail,
            )
            cells["SIPP"] = source(
                f"{CATALOG} §4 Assets Table 4-1", "D2, WP1", detail
            )
            cells["Microcosm"] = refuse(detail, "FRAME_LACKS_RESOURCES")
        if name == "resource_ownership":
            cells["Microcosm"] = refuse(
                detail + "; microcosm#1215", "FRAME_LACKS_RESOURCES"
            )
        if name == "interface_geography":
            cells = {
                population: {
                    "status": "assumption",
                    "assumption_id": "INTERFACE_NATIONAL_GEOGRAPHY",
                    "detail": detail,
                }
                for population in POPULATIONS
            }
        rows.append(
            {
                "name": name,
                "kind": "context",
                "entity": "Context",
                "period": "case",
                "category": group,
                "detail": detail,
                "populations": cells,
            }
        )
    return {
        "schema_version": 1,
        "contract_version": "ssi0-v1",
        "certified_policyengine_us_version": inventory[
            "policyengine_us_version"
        ],
        "populations": list(POPULATIONS),
        "scope": "Annualized potential federal SSI under an explicitly frozen annual state; metadata contract, no survey reader or receipt model",
        "assumptions": {
            "POTENTIAL_FULL_TAKEUP": {
                "statement": "Every eligible person takes up SSI for the potential-benefit estimand.",
                "rationale": "This defines potential entitlement and does not estimate observed receipt; design §3.3 postpones take-up estimation to SSI4.",
                "value": True,
            },
            "INTERFACE_NATIONAL_GEOGRAPHY": {
                "statement": "Select national geography for the public calculator's auxiliary SPM measurement.",
                "rationale": "The public interface requests an SPM measurement geography; SSI0's output scope is federal SSI and does not admit state-supplement claims.",
                "value": "national",
            },
        },
        "interpretation": "A source cell names a route awaiting the listed milestone, not data already read. A refuse cell blocks a case lacking explicit validated input; supplying invented or validated values fills acquisition gaps but does not bypass runner capability guards. Context rows are typed record fields, not engine variables. No missing input falls through to a PE-US default.",
        "rows": rows,
    }


def markdown_table(contract: dict) -> str:
    """Render the same decisions as a reviewable versioned table."""
    lines = [
        "# SSI0 input decisions",
        "",
        "Version `ssi0-v1`. Generated by `scripts/build_ssi_input_contract.py`.",
        "See `source_contract.md` for interpretation and assumption scope.",
        "",
        "| Input (entity; period) | PSID | SIPP | Microcosm |",
        "|---|---|---|---|",
    ]
    for row in contract["rows"]:
        cells = []
        for population in POPULATIONS:
            cell = row["populations"][population]
            if cell["status"] == "source":
                text = (
                    f"**source**: {cell['citation']}; "
                    f"reader: {cell['reader_milestone']} (not read by SSI0); "
                    f"{cell['detail']}"
                )
            elif cell["status"] == "assumption":
                text = (
                    f"**assumption**: `{cell['assumption_id']}`; "
                    f"{cell['detail']}"
                )
            else:
                text = f"**refuse**: `{cell['condition']}`; {cell['blocks']}"
            cells.append(text.replace("|", "\\|").replace("\n", " "))
        lines.append(
            f"| `{row['name']}` ({row['entity']}; {row['period']}) | "
            + " | ".join(cells)
            + " |"
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    contract = build()
    (SSI / "input_contract.json").write_text(
        json.dumps(contract, indent=2, sort_keys=True) + "\n"
    )
    (ROOT / "docs/analysis/ssi0/input_decisions.md").write_text(
        markdown_table(contract)
    )
