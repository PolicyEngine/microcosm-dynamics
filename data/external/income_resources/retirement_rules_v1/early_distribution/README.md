# Early-distribution additional tax

`early_distribution_tax` computes the additional tax under 26 U.S.C.
72(t), using an amount the caller has already established as includible.
It reads no account history or microdata. Its public name distinguishes
the federal additional tax from a plan's contractual withdrawal charge
and from ordinary income tax. SSI2 separately decides whether SSA deducts
this additional tax when valuing a retirement fund.

## Encoded rules

- Section 72(t)(1) imposes 10 percent of the includible amount.
  Section 72(t)(2)(A)(i) removes that tax on or after age 59½. The helper
  uses the birth date plus 714 calendar months, clamping a nonexistent
  day to the last day of the target month. Its supported ages are zero
  through 120, and its supported payment years are 2002–2026.
- Section 72(t)(6)(A) substitutes 25 percent during the two-year period
  beginning with first participation in the employer's SIMPLE arrangement.
  The caller supplies that first-participation date. At its second
  calendar anniversary the rate returns to 10 percent.
- Sections 72(t)(2)(A)(ii), (iii), and (iv) supply the death, disability,
  and substantially equal periodic payment (SEPP) routes. The caller
  certifies beneficiary/estate status, disability under 72(m)(7), or the
  actuarial and payment-frequency predicates of a SEPP. Section
  72(t)(3)(B) additionally requires an employer SEPP series to begin
  after separation. Changes requiring recapture under 72(t)(4) raise.
- Section 72(t)(2)(A)(v) and the IRS exceptions table's “Separation from
  service” row allow a separation in or after the year the employee
  reaches 55. The helper checks the separation year, rather than the
  withdrawal year. Section 72(t)(3)(A) excludes IRAs from this route.
- Section 72(t)(10) substitutes age 50 for qualified public safety
  employees. Pub. L. 109-280 §828 initially covered state/local employees
  performing police, firefighting or emergency medical services and
  governmental defined-benefit plans; §828(b) applies to distributions
  after enactment on August 17, 2006. Before 2016 the caller must supply
  `public_safety_plan_type="defined_benefit"`. Pub. L. 114-26 §2(a) adds
  the specified federal occupations, §2(b) removes the defined-benefit
  restriction, and §2(d) applies these changes to distributions after
  December 31, 2015. The caller must certify occupational eligibility
  under the statute effective on the payment date. The separate
  25-years-of-service route remains named and unmodelled.
- The supported employer accounts are qualified 401(a), 403(a) and
  403(b) plans, and designated Roth accounts within that scope. The
  helper refuses designated Roth distributions before 2006, following
  402A's effective-date note (Pub. L. 107-16 §617(f)). It refuses
  governmental 457(b) accounts because 72(t)(9) requires the portion
  attributable to rollovers from other plans to be distinguished.
- Includible Roth earnings can bear this tax. Qualified distributions,
  contribution basis, ordering, and conversion recapture require account
  history beyond this helper. Section 408A(d)(3)(F) can subject a Roth
  conversion withdrawal to 72(t) even when it is not currently
  includible; the helper explicitly does not implement that history.

## Named routes that raise

`UNMODELLED_EARLY_DISTRIBUTION_EXCEPTIONS` lists these routes with their
sections. Selecting any raises `NotImplementedError`; the registry does
not assert that a route was available in every covered year.

| Name | Authority |
|---|---|
| `esop_dividends` | 72(t)(2)(A)(vi) |
| `irs_levy` | 72(t)(2)(A)(vii) |
| `federal_phased_retirement` | 72(t)(2)(A)(viii) |
| `returned_ira_contribution_earnings` | 72(t)(2)(A)(ix) |
| `medical_expenses` | 72(t)(2)(B) |
| `qualified_domestic_relations_order` | 72(t)(2)(C) |
| `unemployed_health_insurance` | 72(t)(2)(D) |
| `higher_education` | 72(t)(2)(E) |
| `first_home_purchase` | 72(t)(2)(F) |
| `qualified_reservist` | 72(t)(2)(G) |
| `birth_or_adoption` | 72(t)(2)(H) |
| `emergency_personal_expense` | 72(t)(2)(I) |
| `pension_linked_emergency_savings` | 72(t)(2)(J) |
| `domestic_abuse` | 72(t)(2)(K) |
| `terminal_illness` | 72(t)(2)(L) |
| `qualified_disaster_recovery` | 72(t)(2)(M), (11) |
| `qualified_long_term_care` | 72(t)(2)(N), in the current Cornell capture |
| `public_safety_25_years_service` | 72(t)(10)(A) |
| `private_sector_firefighter` | 72(t)(10)(A) |
| `simple_plan_conversion_rollover` | 72(t)(6)(B) |
| `sepp_modification_recapture` | 72(t)(4) |
| `roth_conversion_recapture` | 408A(d)(3)(F) |
| `automatic_enrollment_withdrawal` | 414(w)(1)(B), IRS exceptions table |
| `corrective_employer_distribution` | 401(k)(8)(D), 401(m)(7)(A), 402(g)(2)(C), IRS table |
| `rollover` | 402(c), 403(a)(4), 403(b)(8), 408(d)(3), IRS table |
| `returned_ira_contribution` | 408(d)(4), IRS exceptions table |
| `coronavirus_related_distribution` | Pub. L. 116-136 §2202(a)(1); sibling `rmd/cares_act.html` capture |

## Sources and verification

`capture_manifest.json` records every local capture's URL, UTC retrieval
time, byte count and SHA-256. Sources used here are the 2024 official
U.S. Code sections 72, 402A and 408A; the current Cornell section 72
(including 72(t)(2)(N)); the IRS exceptions table; and the two public
laws above. The capture of 72 matches the legal capture read for the
approved design byte for byte. No source in this folder returned an
automated-access refusal.

The invented-input tests cite the corresponding statute or IRS table
row. Hypothesis checks amount bounds and linearity, the universal age
exemption, all covered exceptions, separation in the birthday
year, and the SIMPLE anniversary. Refusal tests exercise unsupported
years, ages, account types, options, malformed dates, missing predicates
and inconsistent facts. An enum/string differential checks the two
accepted forms of the exception option.
