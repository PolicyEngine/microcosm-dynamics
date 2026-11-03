"""Invented SSI households only; no survey records or model defaults."""

from populace_dynamics.income_resources.ssi.records import (
    Case,
    Household,
    MaritalUnit,
    Person,
)

# Every engine input is written here deliberately. This is independent of
# the inventory so a new input fails the completeness test, not silently
# acquiring its engine default through a fixture factory.
INVENTED_INPUTS = {
    "age": 70,
    "alimony_income": 0,
    "bank_account_assets": 0,
    "bond_assets": 0,
    "child_support_received": 0,
    "disability_benefits": 0,
    "dividend_income": 0,
    "employment_income": 0,
    "financial_assistance": 0,
    "gi_cash_assistance": 0,
    "immigration_status": "CITIZEN",
    "interest_income": 0,
    "is_blind": False,
    "is_full_time_college_student": False,
    "is_in_medicaid_facility": False,
    "is_tax_unit_head": True,
    "is_tax_unit_spouse": False,
    "meets_ssi_disability_criteria": False,
    "own_children_in_household": 0,
    "pension_income": 0,
    "receives_ssi": False,
    "rental_income": 0,
    "retirement_distributions": 0,
    "self_employment_income": 0,
    "social_security": 0,
    "ssi_lives_in_another_persons_household": False,
    "ssi_lives_in_medical_treatment_facility": False,
    "ssi_medicaid_pays_majority_of_care": False,
    "ssi_others_pay_all_meals": False,
    "ssi_qualifying_quarters_earnings": 40,
    "ssi_receives_food_from_others": False,
    "ssi_receives_outside_shelter_support": False,
    "ssi_receives_shelter_from_others_in_household": False,
    "ssi_shelter_support_value": 0,
    "sstb_self_employment_income": 0,
    "stock_assets": 0,
    "survivor_benefits": 0,
    "takes_up_ssi_if_eligible": True,
    "unemployment_compensation": 0,
    "veterans_benefits": 0,
    "workers_compensation": 0,
}

INVENTED_POLICY = {
    "gov.ssa.ssi.amount.individual": 1000,
    "gov.ssa.ssi.amount.couple": 1500,
    "gov.ssa.ssi.eligibility.resources.limit.individual": 2000,
    "gov.ssa.ssi.eligibility.resources.limit.couple": 3000,
    "gov.ssa.ssi.income.exclusions.general": 20,
    "gov.ssa.ssi.income.exclusions.earned": 65,
    "gov.ssa.ssi.income.exclusions.earned_share": 0.5,
}


def invented_case(case_id="INVENTED_CASE", *, couple=False, **inputs):
    values = {**INVENTED_INPUTS, **inputs}
    people = [Person("INVENTED_P", "INVENTED_M", "INVENTED_T", values, ())]
    if couple:
        spouse = {
            **INVENTED_INPUTS,
            "is_tax_unit_head": False,
            "is_tax_unit_spouse": True,
        }
        people.append(
            Person("INVENTED_S", "INVENTED_M", "INVENTED_T", spouse, ())
        )
    ids = tuple(person.person_id for person in people)
    return Case(
        case_id,
        "PSID",
        2026,
        Household(
            "INVENTED_H",
            tuple(people),
            (MaritalUnit("INVENTED_M", ids, {}),),
            {"INVENTED_T": ids},
            {},
            {},
            {},
            {},
            True,
        ),
        "frozen_annual_state_equal_twelfths",
        INVENTED_POLICY,
        ("INTERFACE_NATIONAL_GEOGRAPHY",),
    )
