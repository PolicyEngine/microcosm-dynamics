# F1: income tax on benefits, OASDI and HI

This note fixes F1's statutory reading on invented tax units before any
population calculation. It implements the approved
[mortality, groups and financing design](mortality_groups_financing.md),
including the intended signed departures in its section 6 erratum
([#578](https://github.com/PolicyEngine/microcosm-dynamics/pull/578)).
The hand calculations below use the statute and the code and parameters
of PolicyEngine-US 2.61.0, revision `12b899c11a`. They are tax-unit
examples. The three pin-check witnesses and the signed benefit sequence
also have observed PE-US results in the authorized pin record. On 25
October 2026 this build ran every worked unit live against the pin,
except two that run in pure Python (the signed sequence's $500 point and
the itemizer without the election). Each live unit matched its hand
values within $0.01; see the validation section.

The bridge's `inspect_installation`, `check_published_source` and
`verify_record` checks are recorded in
[f1_pe_us_installation.json](f1_pe_us_installation.json). They identify
Python 3.13.9, policyengine-core 3.33.12 and the published index release.
Verification checked all 19,543 package files, with no changed, missing
or extra package file. The installed RECORD SHA-256 is
`574e62a1759174c169fbd011817d24b3852d646a53bd2393f3ad2fa4af2ff5d9`;
the verified package-record digest is
`faab31131caf676439a57eb774248db1750a63c866e1f645aac2fd0b68bf7120`.
The authorized pin record identifies the published wheel SHA-256 as
`069b150a34e569ce2fb19744e382947036546dae580b5b7d610acedd86c84679`.

## Statutory reading fixed for this implementation

Write `B` for benefits, `M` for section 86 modified adjusted gross income,
and `C = M + B / 2` for combined income. Section 86(b)(2) computes `M`
before taxable Social Security, adds exempt interest and reverses its
listed exclusions and deductions. For a base `b` and adjusted base `a`,
the statute's "lesser of" and "one-half" give:

```text
P = min(B / 2, max(C - b, 0) / 2)
Q = min(P, (a - b) / 2)
T = P                                      if C <= a
T = min(0.85 * B, 0.85 * (C - a) + Q)      if C > a
```

`P` is the section 86(a)(1) inclusion, with the pre-1993 cap; `T` is the
current inclusion. The supported bases are:

| Filing configuration | `b` | `a` |
|---|---:|---:|
| Single | $25,000 | $34,000 |
| Joint | $32,000 | $44,000 |
| Head of household | $25,000 | $34,000 |
| Married filing separately, apart throughout the year | $25,000 | $34,000 |

The independent Python implementation evaluates these equations directly.
It does not import PolicyEngine or read its parameters.
([26 U.S.C. 86(a)–(c)](https://www.law.cornell.edu/uscode/text/26/86))

The following single-filer calculations expose each tier before any tax
calculation. They hold `M` fixed within each row:

| `B` | `M` | `C = M + B/2` | `P` | `Q` | Current `T` |
|---:|---:|---:|---|---|---|
| $20,000 | $12,000 | $22,000 | `min(10,000, 0) = 0` | $0 | $0, below the base |
| $20,000 | $20,000 | $30,000 | `min(10,000, 2,500) = 2,500` | $2,500 | $2,500, below the adjusted base |
| $20,000 | $30,000 | $40,000 | `min(10,000, 7,500) = 7,500` | `min(7,500, 4,500) = 4,500` | `min(17,000, 5,100 + 4,500) = 9,600` |
| $30,000 | $60,000 | $75,000 | `min(15,000, 25,000) = 15,000` | $4,500 | `min(25,500, 34,850 + 4,500) = 25,500`, the 85% cap |

Married separate filers who lived together at any time have zero bases
under section 86(c)(1)(C)(ii). F1 refuses that configuration by name,
with `filing_status="SEPARATE"` and `lived_apart_all_year=False` raising
`SEPARATE filers who lived together at any time are unsupported
(§86(c)(1)(C)(ii))`. It also refuses an unrecognized filing status by name.
Filing status is an explicit input;
these examples do not adjudicate whether a taxpayer qualifies for it.

Let `L(t)` be the unit's Chapter 1 liability with its taxable benefits set
to `t`, holding other original inputs fixed but recomputing the resulting
AGI, deductions, credits and taxes. F1 uses:

```text
OASDI = L(P) - L(0)
HI    = L(T) - L(P)
total = OASDI + HI
```

This confirms the design's conditional third F1 invariant. The
[42 U.S.C. 401 note](https://www.law.cornell.edu/uscode/text/42/401),
"Transfer of Equivalent of 1983 Tax Increases to Payor Funds; Reports,"
reproduces Pub. L. 98-21 section 121(e)(1)(A)–(B), as amended by Pub. L.
103-66 section 13215(c). It appropriates the "aggregate increase in tax
liabilities under chapter 1" attributable to section 86, subtracts the
increase attributable to the 1993 amendments for OASDI, and sends that
subtracted increase to HI. Removing the additional 1993 inclusion leaves
`P`. Consequently `(L(T)-L(0))-(L(T)-L(P)) = L(P)-L(0)`.
No per-unit floor appears in that operation.

Treasury OTA's *Taxation of Social Security and Railroad Retirement
Benefits* (1998), printed p. 3 (PDF p. 7), describes its tax calculator's
with-and-without inclusion method and recomputation of deductions,
credits and alternative minimum tax. It explicitly says those effects
"can be in opposite directions." This supports signed differences and
recomputation, rather than multiplying taxable benefits by one marginal
rate. Its p. 3 discussion concerns the 1993 liability year; the amended
statute supplies the additional three-liability split above. Source:
[Treasury's 1998 report, printed p. 3](https://home.treasury.gov/system/files/131/Report-Taxation-Social-Security-1998.pdf#page=7),
read from the authorized `f1-pin-check-20261024/sources/` PDF in the lane
evidence record. No projected-benefit-tax comparator is used here.

## Chapter 1 component classification

All code locators in this section refer to the pinned wheel's
`policyengine_us/variables/` tree at revision `12b899c11a`.
[income_tax_before_refundable_credits.py](https://github.com/PolicyEngine/policyengine-us/blob/12b899c11a/policyengine_us/variables/gov/irs/tax/federal_income/income_tax_before_refundable_credits.py#L18-L32)
adds exactly the five terms below, then subtracts capped nonrefundable
credits (lines 29–32).

| Added term and code line | Chapter and disposition |
|---|---|
| `income_tax_before_credits`, line 22 | Chapter 1: retain. Its own `adds` list contains regular income tax, capital gains tax and AMT (`before_credits/income_tax_before_credits.py:12–16`). |
| `net_investment_income_tax`, line 23 | Chapter 2A, section 1411: exclude in each counterfactual. |
| `recapture_of_investment_credit`, line 24 | Chapter 1, section 50(a): retain. |
| `unreported_payroll_tax`, line 25 | Chapter 21 FICA, Forms 4137 and 8919: exclude in each counterfactual. |
| `qualified_retirement_penalty`, line 26 | Chapter 1, section 72(t): retain. |

The NIIT chapter and 3.8% rule come from
[26 U.S.C. 1411](https://www.law.cornell.edu/uscode/text/26/1411).
The remaining chapter classifications follow the US hub's dated
`us:tob-chapter-1-only` ruling (24 October 2026), including its explicit
retention of sections 50(a) and 72(t). The unreported-payroll variable is
an input with the Forms 4137/8919 label
(`gov/irs/tax/payroll/unreported_payroll_tax.py:4–9`); both retained
additional-tax variables are also inputs, not formulas, in this wheel.
These classifications cover every added term, rather than removing
everything described generically as an "other tax."

The modeled nonrefundable credits all flow through the configured
`gov.irs.credits.non_refundable` list
(`gov/irs/credits/income_tax_non_refundable_credits.py:10`). For the 2024
and 2026 examples that list includes foreign tax, dependent care, elderly
or disabled, nonrefundable AOTC, lifetime learning, saver's, home
improvement, used and new clean vehicle, nonrefundable child, and
residential clean energy credits
(`parameters/gov/irs/credits/non_refundable.yaml:37–50`). The capped total
subtracts only credits unavailable because tax before credits is too low
(`income_tax_capped_non_refundable_credits.py:11–12,23–27`). F1 keeps this
whole capped total; it does not add back any nonrefundable credit.

Refundable credits enter a separate configured sum
(`gov/irs/credits/income_tax_refundable_credits.py:10`;
`parameters/gov/irs/credits/refundable.yaml:20–25`). No term in that sum
enters `income_tax_before_refundable_credits.py:18–32`.
`income_tax.py:18–24` subtracts the refundable sum afterward. Thus the two
reported Chapter 1 readings are:

```text
primary(t) = income_tax_before_refundable_credits(t)
             - NIIT(t) - unreported_payroll_tax(t)
netted_sensitivity(t) = income_tax(t) - NIIT(t)
                        - unreported_payroll_tax(t)
```

Revision 2 of the builder brief incorporates the hub's P1 ruling
`us:tob-refundable-credit-netting`, dated 24 October 2026: reading **(b),
liability after nonrefundable credits, before refundable credits**. That is
F1's primary reading. The netted reading remains a disclosed comparison
with 2.61.0.
The ruling uses [26 U.S.C. 6401(b)](https://www.law.cornell.edu/uscode/text/26/6401#b):
it distinguishes tax, reduced by specified nonrefundable credits, from
excess subpart C credits treated as an overpayment. F1 follows the hub's
choice and does not claim Treasury's 1998 report separately resolves this
question. The sensitivity never triggers `TOB_SPLIT_UNRESOLVED`; that
condition applies only if worked examples cannot settle the section
86(a)(1) reading of the fund split. The statutory subtraction above
settles that reading here. Revisit refundable-credit treatment if Treasury
publishes its transfer-specific definition, as the hub ruling directs.

The hub's next correction is identified as build `hub-tob-chapter1` in the
two 24 October rulings. The pinned release predates that correction;
F1 computes Chapter 1 liability itself. The existing split correction is
[#10381](https://github.com/PolicyEngine/policyengine-us/pull/10381).

## Counterfactual mechanism

In 2.61.0, `tob_revenue_oasdi.py:33–35` obtains
`tax_unit_taxable_social_security_pre_1993`. Its no-inclusion branch
neutralizes `tax_unit_taxable_social_security` (lines 37–52); its old-law
branch clears computed arrays and sets that variable's holder to `P`
(lines 55–72). It returns the signed difference (line 75).
`tob_revenue_total.py:27–46` compares current income tax with the
neutralized-inclusion branch; `tob_revenue_medicare_hi.py:20–23` subtracts
OASDI from total.

F1 uses fresh simulations of the same situation and fixes
`tax_unit_taxable_social_security` to `0`, `P` or `T`. Setting that same
tax-unit inclusion is the old-law branch's mechanism; fresh simulations
replace its cache-clearing step. Keeping original gross benefits in all
three simulations preserves changes in nontaxable benefits for credits.
The bridge returns named variables for all three simulations, including
each excluded component and each refundable-credit reading. The original
simulation separately supplies the three native PE-US TOB variables.

`tax_on_benefits_batch` accepts named `TaxOnBenefitsInput` units for one
year. It makes one bridge request for their baseline values and one for
their three liability states, using internal IDs separate from the
caller's names. Each case receives a fresh simulation. This shares
interpreter startup and source verification while keeping each unit's
inputs and calculations independent. The original `tax_on_benefits`
entry point delegates a singleton batch and returns the same per-unit
result.

F1 treats `BridgePerson.interest_income` as total annual interest. The
pin's `interest_income.py:11–14` sums its taxable and exempt components,
so F1 supplies those components explicitly. If exempt interest is given,
it subtracts that amount from the supplied total to obtain taxable
interest. An explicit taxable amount may instead supply interest when
the bridge total is its default zero; a nonzero supplied total must agree
with both components within $0.01. Inconsistent or negative components
are refused by name.

## Worked examples

Dollar amounts in the following tables are displayed to cents. The
calculation preserves PE-US's float32 liability outputs before taking
differences; it does not round each liability to cents first. Split
identities are checked within $0.01, following the pin's generated test,
because independently differenced float32 outputs can round differently.
The section 86 arithmetic is computed independently; ordinary tax bands
and deduction amounts used in the hand calculations are the pinned
wheel's `parameters/gov/irs/income/bracket.yaml`,
`deductions/standard/{amount,aged_or_blind/amount}.yaml`, and
`deductions/senior_deduction/` parameters. This is not a claim of a second
independent implementation of the entire federal income tax.

### Single, age 70, 2026: the split witness

Benefits are $20,000 and taxable interest is $30,000, with no other income,
in Texas. `C = 30,000 + 10,000 = 40,000`.

```text
P = min(10,000, (40,000 - 25,000) / 2) = 7,500
Q = min(7,500, (34,000 - 25,000) / 2) = 4,500
T = min(17,000, 0.85 * 6,000 + 4,500) = 9,600
```

The $16,100 standard deduction, $2,050 age addition and $6,000 senior
deduction sum to $24,150 in each counterfactual. Taxable incomes are
$5,850, $13,350 and $15,450. With the first $12,400 taxed at 10% and the
next band at 12%, the liabilities are:

| Inclusion | Hand liability |
|---|---:|
| None | `0.10 * 5,850 = $585.00` |
| Pre-1993 | `1,240 + 0.12 * 950 = $1,354.00` |
| Current | `1,240 + 0.12 * 3,050 = $1,606.00` |

OASDI is **$769**, HI is **$252**, and total is **$1,021**, matching the
pin-check witness. The live run against the pin reproduced all three
under both refundable-credit readings, and so did all three native PE-US
variables, within $0.01. Its `taxable_social_security_tier_1` is $4,500:
above the adjusted base it is `Q`, rather than `P`.

### Signed itemizer, age 67, 2024: intended negative differences

This single Texas unit has $1,000 of benefits, $11,500 of taxable interest,
$23,000 of exempt interest and $20,000 of cash gifts. It elects itemizing;
medical and SALT deductions are zero. `C = 11,500 + 23,000 + 500 = 35,000`.
Therefore `P = min(500, 5,000) = 500`, `Q = 500`, and
`T = min(850, 0.85 * 1,000 + 500) = 850`.

For inclusion `t`, AGI is `11,500 + t`. The binding 60% gift ceiling
allows `6,900 + 0.60t`, leaving `4,600 + 0.40t` taxable income and regular
tax `460 + 0.04t`. The elderly credit is
`0.15 * [5,000 - (1,000-t) - 0.5*(11,500+t-7,500)]`
`= 300 + 0.075t`. Thus `L(t) = 160 - 0.035t`.
The mechanisms are read in
`deductions/itemizing/charitable_deduction.py:54–56` and
`credits/elderly_and_disabled/{section_22_income.py:48–65,elderly_disabled_credit_potential.py:13–15}`;
the relevant 2024 values appear in the wheel's elderly-credit parameters.

| Inclusion | Liability |
|---|---:|
| None | $160.00 |
| Pre-1993, $500 | $142.50 |
| Current, $850 | $130.25 |

The split is **−$17.50 / −$12.25 / −$29.75**, matching the witness; the
live run reproduced it under both readings and in the native PE-US
variables. Increasing inclusion releases more deductions and raises a
nonrefundable credit. The latter is retained under the hub's ruling.

Holding the other original inputs fixed and varying benefits `B` in the
pin-check sequence gives `P = 0.5B`, `T = 0.85B` and differences
`OASDI = -0.0175B`, `HI = -0.01225B`, `total = -0.02975B`:

| Benefits | OASDI | HI | Total | Checked |
|---:|---:|---:|---:|---|
| $0 | $0.00 | $0.00 | $0.00 | live |
| $250 | −$4.38 | −$3.06 | −$7.44 | live |
| $500 | −$8.75 | −$6.12 | −$14.88 | pure Python |
| $1,000 | −$17.50 | −$12.25 | −$29.75 | live |
| $2,000 | −$35.00 | −$24.50 | −$59.50 | live |

Half-cent values are displayed with half-even rounding, as in
`mono.out.json`; displayed components can differ by one cent from the
displayed total. Live rows matched the unrounded values within $0.01
under both readings and in the native PE-US variables. The $500 row runs
in pure Python: the hand model above, with F1's section 86 tiers and
split, gives the same values, and so does the same model at $1,000 and
$0. Without the itemizing election, the hand model applies the $14,600 +
$1,950 standard deduction, which exceeds the $1,000 unit's AGI in every
state, so all three parts are $0. That case was not run live in this
build; it runs in pure Python. This is an intended departure from
universal nonnegativity and monotonicity in benefits. It is not a
counterexample to the signed statutory split.

### Investment income, age 70, 2026: NIIT excluded

The single Texas unit has $40,000 benefits and $190,000 taxable interest.
`C = 210,000`; `P = min(20,000, 92,500) = 20,000`;
`Q = 4,500`; `T = min(34,000, 0.85 * 176,000 + 4,500) = 34,000`.

At these AGIs the extra $6,000 senior deduction has fully phased out
(`additional_senior_deduction.py:23–34`), so deductions are
`16,100 + 2,050 = 18,150`. The taxable incomes are $171,850, $191,850 and
$205,850. The first three bands yield
`12,400*.10 + 38,000*.12 + 55,300*.22 = 17,966`. The next band ends at
$201,775 and is taxed at 24%; the following band is 32%.

| Inclusion | Hand Chapter 1 liability | NIIT | PE-US `income_tax` |
|---|---:|---:|---:|
| None | `17,966 + 66,150*.24 = $33,842` | $0 | $33,842 |
| Pre-1993 | `17,966 + 86,150*.24 = $38,642` | $380 | $39,022 |
| Current | `17,966 + 96,075*.24 + 4,075*.32 = $42,328` | $912 | $43,240 |

Section 1411 imposes 3.8% on the smaller of investment income and MAGI
over $200,000 for this single filer. Here that is respectively
`0.038*0`, `0.038*10,000`, and `0.038*24,000`. Social Security need not
itself be investment income to raise the MAGI limit.

The hand-derived Chapter 1 split is **$4,800 / $3,686 / $8,486**, matching
the pin-check witness. The live run reproduced it under both readings,
with NIIT of $0, $380 and $912 in the three states and no refundable
credit in any. The authorized pin record reports native 2.61.0 values of
**$5,180 / $4,218 / $9,398**, which the live run also reproduced: the
intended differences are exactly $380 / $532 / $912 of Chapter 2A tax,
respectively.

### Joint, head of household, and separate apart throughout 2026

The joint example has two spouses aged 70, $40,000 of combined benefits
and $60,000 of interest. Its combined income is `60,000 + 20,000 = 80,000`.
Thus `P = min(20,000, (80,000-32,000)/2) = 20,000`,
`Q = min(20,000, (44,000-32,000)/2) = 6,000`, and
`T = min(34,000, .85*(80,000-44,000)+6,000) = 34,000`.
Deductions total `32,200 + 2*1,650 + 2*6,000 = 47,500`.
The first $24,800 of taxable income is taxed at 10%, followed by 12%:

| State | Taxable income | Hand Chapter 1 liability |
|---|---:|---:|
| None | $12,500 | `12,500*.10 = $1,250` |
| Pre-1993 | $32,500 | `2,480 + 7,700*.12 = $3,404` |
| Current | $46,500 | `2,480 + 21,700*.12 = $5,084` |

The split is **$2,154 / $1,680 / $3,834**. The live run reproduced it
within $0.01 in the primary reading and in native 2.61.0.

The head-of-household and separate-apart examples each have one person
aged 70, $20,000 of benefits and $30,000 of interest. As for the first
single example, `C = 40,000`, `P = 7,500`, `Q = 4,500`, and `T = 9,600`.
The head-of-household deduction is `24,150 + 2,050 + 6,000 = 32,200`;
all positive taxable income below lies in its 10% band. The separate
filer's deduction is `16,100 + 1,650 = 17,750`; it gets no additional
senior deduction, because
`additional_senior_deduction_eligible_person.py:16–22` excludes separate
returns. Its first $12,400 is taxed at 10%, then 12%.

| Configuration | None | Pre-1993 | Current | OASDI / HI / total |
|---|---:|---:|---:|---:|
| Head of household | `max(30,000-32,200,0)*.10 = $0` | `5,300*.10 = $530` | `7,400*.10 = $740` | **$530 / $210 / $740** |
| Separate, apart all year | `12,250*.10 = $1,225` | `1,240+7,350*.12 = $2,122` | `1,240+9,450*.12 = $2,374` | **$897 / $252 / $1,149** |

The live run reproduced both rows within $0.01, in the primary reading and
in native 2.61.0, which agree because these examples have no refundable
credits or outside-Chapter-1 increment.
The separate example explicitly inputs `cohabitating_spouses = False`;
it does not infer that condition from a missing spouse record.

### Unreported payroll tax excluded; Chapter 1 additional taxes retained

Add three fixed tax-unit inputs to the first single witness:
`unreported_payroll_tax = 900`, `recapture_of_investment_credit = 50`,
and `qualified_retirement_penalty = 100`. These input variables have no
formulas in the pin (`unreported_payroll_tax.py:4–9`,
`recapture_of_investment_credit.py:4–9`, and
`household/expense/tax/qualified_retirement_penalty.py:4–9`).

| State | Regular Chapter 1 tax | Retained recapture + penalty | Excluded payroll tax | PE-US `income_tax` | F1 Chapter 1 liability |
|---|---:|---:|---:|---:|---:|
| None | $585 | $150 | $900 | $1,635 | $735 |
| Pre-1993 | $1,354 | $150 | $900 | $2,404 | $1,504 |
| Current | $1,606 | $150 | $900 | $2,656 | $1,756 |

The fixed components cancel when differenced, so the result under the
primary reading and native 2.61.0 is **$769 / $252 / $1,021**, as the live
run confirmed. It also confirmed the liability levels within $0.01: in
each state PE-US reported the $900, $50 and $100 inputs, and F1's
liability equals `income_tax` less $900. That establishes that F1 excludes
the $900 and retains the $150; zero change in native revenue alone would
not establish that classification.

### ACTC $1,700 to $1,000: primary transfer is zero

This invented 2024 single unit has a parent aged 40, a dependent child
aged 5, $17,600 of wages, $12,000 of interest, $11,937.254901960784 of
Social Security disability benefits, and a fixed allowable foreign tax
credit of $1,268, supplied as an allowable tax-unit fact. Interest exceeds the pin's EITC
investment-income limit, so EITC is zero.

Here `M = 29,600` and `C = 35,568.62745098039`.
`P = min(5,968.627450980392, (C-25,000)/2) = 5,284.313725490196`.
`Q = min(P,4,500) = 4,500`.
`T = min(10,146.666666666666, .85*(C-34,000)+4,500)`
`= 5,833.333333333333`.
The standard deduction is $14,600. The first $11,600 of taxable income is
taxed at 10%, followed by 12%. The $2,000 child credit first absorbs the
remaining tax, with the balance refundable up to $1,700. The earned
income limit is `.15*(17,600-2,500) = 2,265`, so it does not bind.

| State | Taxable income | Tax before credits | Tax after $1,268 foreign credit | Nonrefundable CTC | ACTC | Primary liability | Netted liability |
|---|---:|---:|---:|---:|---:|---:|---:|
| None | $15,000 | `1,160+.12*3,400 = $1,568` | $300 | $300 | $1,700 | $0 | −$1,700 |
| Pre-1993 | $20,284.313725 | `1,160+.12*8,684.313725 = $2,202.117647` | $934.117647 | $934.117647 | $1,065.882353 | $0 | −$1,065.882353 |
| Current | $20,833.333333 | `1,160+.12*9,233.333333 = $2,268` | $1,000 | $1,000 | $1,000 | $0 | −$1,000 |

The live run against the pin (25 October 2026) gave an F1 primary split of
**$0 / $0 / $0**, and a netted sensitivity and native PE-US 2.61.0 values
of **$634.12 / $65.88 / $700**. In each state the liability before
refundable credits, tax before credits, capped nonrefundable credits, ACTC
and refundable total matched the table within $0.01, and EITC was zero.
The $700 ACTC reduction enters only the sensitivity, reproducing the hub's
first check. The mechanisms are read in
`credits/ctc/refundable/refundable_ctc.py:35–42`, which limits the
refundable amount using the tax-limited child credit and earned-income
phase-in, and `credits/ctc/non_refundable_ctc.py:11–12`, which subtracts
that refundable amount from total CTC. The 2024 amounts are recorded in
`parameters/gov/irs/credits/ctc/{amount/base.yaml:10,refundable/individual_max.yaml:8,refundable/phase_in/rate.yaml:3,refundable/phase_in/threshold.yaml:4}`;
the EITC investment-income ceiling is in
`parameters/gov/irs/credits/eitc/phase_out/max_investment_income.yaml:36`,
applied by
`credits/earned_income/eligibility/eitc_investment_income_eligible.py:11–14`
and required by `eligibility/eitc_eligible.py:28–33`.

### EITC $300 to $100, liability $500 to $800: primary transfer is $300

This invented 2024 childless single filer aged 40 has wages
`W = 10,330 + (632-300)/.0765 = $14,669.869281045752` and benefits
`B = $31,117.77777777778`, supplied as Social Security disability
benefits. The unit elects to itemize, with fixed cash
gifts of $3,756.143790849673, zero medical and SALT deductions, and a fixed
allowable foreign tax credit of $591.372549019608. Those gifts are below
60% of AGI in every state, so the gift deduction stays fixed.

Combined income is `W+B/2 = 30,228.75816993464`, below $34,000.
Consequently `P = T = (30,228.75816993464-25,000)/2`
`= $2,614.37908496732` and HI is zero. The exact inputs are chosen so
`.0765*T = 200` and the tax crosses the $11,600 band boundary by the
amount that makes its increase $300:

| State | AGI | Taxable income | Tax before credits | Primary liability | EITC | Netted liability |
|---|---:|---:|---:|---:|---:|---:|
| None | $14,669.869281 | $10,913.725490 | `10,913.725490*.10 = $1,091.372549` | `1,091.372549-591.372549 = $500` | `632-.0765*(14,669.869281-10,330) = $300` | $200 |
| Pre-1993 and current | $17,284.248366 | $13,528.104575 | `1,160+.12*1,928.104575 = $1,391.372549` | `1,391.372549-591.372549 = $800` | `632-.0765*(17,284.248366-10,330) = $100` | $700 |

The EITC maximum, threshold and rate come from
`parameters/gov/irs/credits/eitc/{max.yaml:15,phase_out/start.yaml:57,phase_out/rate.yaml:25}`.
`credits/earned_income/eitc_reduction.py:13–19` phases out the credit on
the larger of earned income and AGI;
`credits/earned_income/eitc.py:15–18,31` subtracts that reduction from the
maximum, subject to phase-in and filing conditions.

The live run gave an F1 split of **$300 / $0 / $300**, and a netted
sensitivity and native PE-US 2.61.0 values of **$500 / $0 / $500**,
reproducing the hub's second check. Liabilities before refundable credits
were $500 and $800, and EITC $300 and $100, within $0.01. The tests
calculate ordinary deductions, taxes and credits from these invented
inputs, using the mechanisms read above. They override neither
counterfactual liabilities nor refundable-credit amounts.

The investment-income witness has no refundable credits in any state;
the expected primary and netted results therefore both remain
**$4,800 / $3,686 / $8,486**. Refundable-credit sensitivity is a labeled
intended difference, not an unresolved fund split.

## Intended differences from PolicyEngine-US 2.61.0

1. F1 removes NIIT from each of the three liability states. The investment
   example derives the differences in all three native TOB values,
   matching the authorized pin-check results.
2. F1 removes unreported payroll tax from each state. In the pin it is an
   input, so a fixed amount cancels in native TOB differences; its removal
   still matters to the reported Chapter 1 liability levels.
3. The primary reading retains refundable credits as payments rather than
   netting them from liability, following the hub's updated ruling.
   The netted reading remains available to identify this difference.
4. The pre-1993 inclusion differs deliberately from
   `taxable_social_security_tier_1` above the adjusted base. That variable
   returns the current-law bracket amount `Q`
   (`taxable_social_security_tier_1.py:44–59`). F1 and 2.61.0's OASDI
   variable instead use `P`. This is a difference in meaning, not a
   discrepancy between the two section 86 implementations.
5. F1 refuses configurations outside its explicitly supported filing
   scope. It does not turn unsupported inputs into zero revenue.

Negative signed amounts and the pre-1993 split are shared with 2.61.0,
following #10381; neither is a departure from that pin.

## Validation and remaining admission

Installation verification completed with the result recorded above. The
independent section 86 oracle passed on 150 invented units: 75 each in
2024 and 2026, covering all four supported filing configurations. Current
and pre-1993 inclusions, modified AGI, combined income and current-law tier
contributions matched within float32 rounding. All 13 live split tests
passed against the pin on 25 October 2026.

The pure Python tests exercise statutory examples, bounds and generated
inputs without a PolicyEngine interpreter. Oracle tests compare that
implementation with the two taxable-benefit variables and the three TOB
variables on invented units. The invariant set is conservation of the
split, primary invariance to changes in refundable credits when liability
before refundable credits is fixed, zero benefits, zero OASDI when `P=0`,
zero HI when `P=T`,
`0 <= P <= T <= 0.85B`, exclusion of both outside-Chapter-1 components,
and determinism under both refundable readings. The signed sequence is
asserted as an intended departure. Zero benefits, zero OASDI when `P=0`
and zero HI when `P=T` are tested in pure Python, as properties and on
three invented units that earlier ran live; the live run checks
conservation, both outside-Chapter-1 exclusions, the refundable-credit
readings and determinism.

| Verification | Test module | Result |
|---|---|---|
| Statutory tiers, boundaries, precision, inclusion bounds and refusals | `tests/test_section86.py` | 66 passed |
| Independent current and pre-1993 inclusions against PE-US, with the tier-1 meaning distinguished | `tests/test_section86_oracle.py` | 2 passed; 150 invented units |
| Signed allocation identity, refundable-credit invariance, both hub checks, Chapter 1 classification, and the units moved to pure Python | `tests/test_tax_on_benefits.py` | 33 passed |
| The persistent oracle worker dies with its launcher: idle, sleeping in a job, and inside a GIL-holding C call | `tests/test_tax_on_benefits_oracle_worker.py` | 3 passed |
| The three witnesses, both hub checks, the payroll exclusion, joint, head of household, separate apart, the signed sequence at $0, $250, $1,000 and $2,000, determinism and intended native TOB differences | `tests/test_tax_on_benefits_oracle.py` | 13 passed live |
| Native entities, enum values, fresh simulations and malformed-result refusals | `tests/bridge/test_policyengine_us_named.py`, `tests/bridge/test_policyengine_us_named_oracle.py` | 28 pure and 2 live tests passed |

The live split tests ran as four pytest processes, one per group of
units, each checking the pin once. On the saturated build host, a unit's
baseline request, which evaluates the native TOB variables, took
1,753–1,889 seconds when it carried the process's cold import and
207–615 seconds otherwise; the two hub units shared one 2,922-second
request. Each request for the three liability states took 41–158
seconds. In the pin, each unit's native TOB variables open three branches
with `clone_system=True` (`tob_revenue_oasdi.py:38,56`,
`tob_revenue_total.py:31`), and policyengine-core 3.33.12 then calls the
tax-benefit system's `clone()` (`simulations/simulation.py:2864–2865`).
The docstring of `share_spm_policy` (`spm.py:601`) describes core's
system clone as rebuilding the whole parameter tree.

The bridge suite's tiers other than the oracle tier
(`-m "not oracle_policyengine" tests/bridge/`) had 596 passes, one skip
and three Hypothesis `DeadlineExceeded` failures in
`test_policyengine_us_bridge.py`: about 274 ms on a first example against
a 200 ms deadline, and under 1 ms on replay. All three passed unchanged
under Hypothesis's built-in CI profile, which sets no deadline. The
suite's existing live PE-US 2.18.0 tests were not rerun; F1 adds bridge
functions and changes none they call. Black (79 columns) and Ruff passed
for all changed Python files. Both new source files are in the
post-review source exclusions and their exact-tuple assertion passed.

The required recount completed: unit 18,125 to 18,255, artifact 4,261,
integration 1,450 and legacy 520 unchanged, and oracle 308 to 325
(24,664 to 24,811 overall). On full collection the manifest test passed:
one passed, two modules skipped because `populace.fit` is not installed
in the repository environment, and 24,810 deselected. Merge still waits
for the coordinator's tier-count slot.

The split oracle fixture memoizes the real installation check once per
pytest process and executes the unchanged bridge runner source with fresh
globals in a persistent pinned interpreter. Each request recreates the
runner's system cache and constructs fresh simulations; imported modules
persist, and no calculated tax values are substituted. Nothing inside the
check is cached: it inspects the child, checks the published source and
hashes every RECORD file. Each invented unit is its own pair of bridge
requests, computed when a test first needs it. The test-only budget per
named-variable job is four hours; production timeouts are unchanged. This
avoids repeated cold imports on the saturated build host. In the pin,
`system.py:117,189,237–238` loads the default policy at import and assigns
it to `Simulation`; `share_spm_policy` (`spm.py:601`), called from
`_prepare_spm_system` (`spm.py:856–886`), shares its parameter tree while keeping
simulations separate. The production bridge
continues checking every call, and its separate live named-variable tests
exercise the normal subprocess transport.

The persistent worker dies with the process that started it. Its stdin
loop ends only between jobs, so a daemon thread checks the parent pid
once a second and exits when it changes. A C call that holds the GIL
delays that thread until the call returns, so a kernel-side backstop
does not wait for it: on Linux, `PR_SET_PDEATHSIG`; on macOS, a small
guard process, holding none of the worker's pipes, that waits on kqueue
exit events for the launcher and the worker. With invented jobs on the
macOS build host, a launcher killed by its pid left no worker or guard
behind, whether the worker was idle, sleeping in a job, or inside a
GIL-holding C call (`tests/test_tax_on_benefits_oracle_worker.py`); the
worker exited 0.3–0.5 seconds after the kill. With the thread alone, the
worker in the GIL-holding call survived the 25-second check, and with
neither mechanism every state did. The Linux branch was not exercised
on this host.

There is no population run and no real-data statistic.
PSID use follows the project's data-access record.
The financing comparator remains for
the validation-only S0.2 lane after F0R. Final split admission waits for
the hub correction. Merge waits for independent review and the
coordinator's tier-count slot.

`axiom: queued rulespec-us#415 (blocked: corpus re-pin,
axiom-rules-engine#58, encoder dispatch)`

There is no executable Axiom mirror in this build. The authorized pin
check records that status; this note does not claim Axiom conformance.
