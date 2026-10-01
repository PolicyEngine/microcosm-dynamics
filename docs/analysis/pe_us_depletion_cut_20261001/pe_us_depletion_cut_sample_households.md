# A Social Security cut at trust fund depletion: sample households

**ILLUSTRATIVE HOUSEHOLDS, NOT SURVEY DATA.** Five households, each in three states, run through PolicyEngine-US. Amounts are annual 2026 dollars. In the component tables taxes and costs enter as negative contributions, so each column sums to net income: a tax that falls from −2,291 to −1,974 shows as +317, a gain to the household. Each dollar figure is rounded to the dollar on its own, with half-dollars rounded up in magnitude, so a total can differ by a dollar from the sum or difference of its rounded parts.

**Applied to 2026 benefits under 2026 tax and benefit law and prices. The cut would not happen in 2026: the Trustees project the OASI Trust Fund's reserves to deplete in 2032. This shows how much of a cut of that size each household would absorb, and how much other programs and taxes would offset, under current law. It is not a projection.**

## The cut

From The 2026 Annual Report of the Board of Trustees of the Federal Old-Age and Survivors Insurance and Federal Disability Insurance Trust Funds, section II.A Highlights, intermediate assumptions (https://www.ssa.gov/oact/TR/2026/II_A_highlights.html, retrieved 2026-10-01T02:35:26+00:00, SHA-256 `8447f9cae65e561cb84239350e6a037f9b2572d18bf457212130d682c0003551`):

> The OASI Trust Fund is projected to become depleted in the fourth quarter of 2032, one quarter earlier than projected in last year’s report. Upon reserve depletion in 2032, projected income is sufficient to pay 78 percent of scheduled benefits.

> The combined OASDI fund is projected to become depleted in the third quarter of 2034, the same quarter as in last year’s report. Upon reserve depletion in 2034, projected income is sufficient to pay 83 percent of scheduled benefits.

- **Primary:** a 22% cut in each OASI benefit (every benefit in these households is a retired-worker or spouse's benefit), leaving the 78 percent of scheduled benefits the Trustees project OASI income to pay in the first year of depletion, 2032. 'Retired workers, their families, and survivors of deceased workers receive monthly benefits under the Old-Age and Survivors Insurance (OASI) program' (the report's introduction, printed page 1; Table III.A5, printed page 40, lists retired workers and spouses under OASI benefit payments), so the primary reform pays each benefit at the OASI payable share. The share for the OASI and DI funds on a combined basis (OASDI) is the sensitivity; the report notes that full payment until 2034 'implicitly assumes that the law will have been changed to permit the transfer of funds between OASI and DI as needed' (printed page 28). Both shares are for the first year of depletion: the payable share 'declines gradually to 62 percent by 2100' for OASI and to 65 percent for OASDI.
- **Sensitivity:** a 17% cut in each OASI benefit (every benefit in these households is a retired-worker or spouse's benefit), leaving the 83 percent of scheduled benefits the Trustees project combined OASDI income to pay in the first year of depletion, 2034.
- **Rounding:** Each beneficiary's payable monthly benefit is the scheduled 2026 monthly benefit (a whole dollar) times the payable share, rounded down to a whole dollar ('is not a multiple of $1 shall be rounded to the next lower multiple of $1', 42 USC 415(g)). 415(g) rounds a benefit computed under section 402 or 423 after the reductions of sections 403(a) and 424a, the deductions of 403(b) and the Medicare Part B premium deduction; this analysis floors the gross benefit, before any Part B deduction. The across-the-board cut is this analysis's assumption: the Trustees project the payable share, and note that once reserves are depleted 'scheduled benefits could not be paid in full on a timely basis, and actual amounts paid would be less than the scheduled benefits' (Table IV.A1 note, printed page 46), but the Highlights do not say how a shortfall would be spread across beneficiaries. Applying the share to each whole-dollar monthly benefit and rounding the product down is also this analysis's choice: 415(g) itself rounds once, so a share applied to the unrounded amount could pay a dollar a month more. The monthly cut is the scheduled benefit less the payable benefit, so it is at least the cut share times the scheduled benefit and less than a dollar more; the annual amounts are twelve times the monthly ones.

Each household's Social Security, scheduled and after the cut (monthly):

| Household | Beneficiary | Scheduled | After the OASI cut | After the OASDI cut |
|---|---|---:|---:|---:|
| A | worker | $743 | $579 | $616 |
| B | worker | $743 | $579 | $616 |
| C | worker | $743 | $579 | $616 |
| D | worker | $2,351 | $1,833 | $1,951 |
| E | worker | $2,351 | $1,833 | $1,951 |
| E | spouse | $1,175 | $916 | $975 |

## Summary: the OASI cut

The offset share is the share of the Social Security cut that other programs and taxes return: 1 − (net change ÷ Social Security change). Federal and state are the shares each level of government pays; they sum to the offset share (each is rounded on its own, so the rounded figures can miss by a point). Health coverage is outside net income by default, as PolicyEngine-US computes it; the last three columns count it (a sensitivity), and joint federal-state programs (Medicaid, the Medicare Savings Programs) appear only there.

| Household | State | Social Security | Net income | Offset share | Federal | State | Net income with health coverage | Offset share with health | Joint, with health |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A | CA | −1,968 | 0 | 100% | 100% | 0% | 0 | 100% | 0% |
| A | MT | −1,968 | 0 | 100% | 100% | 0% | 0 | 100% | 0% |
| A | FL | −1,968 | 0 | 100% | 100% | 0% | 0 | 100% | 0% |
| B | CA | −1,968 | 0 | 100% | 21% | 79% | 0 | 100% | 0% |
| B | MT | −1,968 | −1,548 | 21% | 21% | 0% | +3,916 | 299% | 278% |
| B | FL | −1,968 | −936 | 52% | 52% | 0% | −936 | 52% | 0% |
| C | CA | −1,968 | −1,776 | 10% | 10% | 0% | −1,776 | 10% | 0% |
| C | MT | −1,968 | −1,654 | 16% | 10% | 6% | −1,654 | 16% | 0% |
| C | FL | −1,968 | −1,776 | 10% | 10% | 0% | −1,776 | 10% | 0% |
| D | CA | −6,216 | −5,899 | 5% | 5% | 0% | −5,899 | 5% | 0% |
| D | MT | −6,216 | −5,775 | 7% | 5% | 2% | −5,775 | 7% | 0% |
| D | FL | −6,216 | −5,899 | 5% | 5% | 0% | −5,899 | 5% | 0% |
| E | CA | −9,324 | −8,928 | 4% | 4% | 0% | −8,928 | 4% | 0% |
| E | MT | −9,324 | −8,741 | 6% | 4% | 2% | −8,741 | 6% | 0% |
| E | FL | −9,324 | −8,928 | 4% | 4% | 0% | −8,928 | 4% | 0% |

## Sensitivity: the OASDI cut

| Household | State | Social Security | Net income | Offset share | Federal | State | Net income with health coverage | Offset share with health | Joint, with health |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A | CA | −1,524 | 0 | 100% | 100% | 0% | 0 | 100% | 0% |
| A | MT | −1,524 | 0 | 100% | 100% | 0% | 0 | 100% | 0% |
| A | FL | −1,524 | 0 | 100% | 100% | 0% | 0 | 100% | 0% |
| B | CA | −1,524 | 0 | 100% | 0% | 100% | 0 | 100% | 0% |
| B | MT | −1,524 | −1,524 | 0% | 0% | 0% | +3,940‡ | 359%‡ | 359%‡ |
| B | FL | −1,524 | −912 | 40% | 40% | 0% | −912 | 40% | 0% |
| C | CA | −1,524 | −1,373 | 10% | 10% | 0% | −1,373 | 10% | 0% |
| C | MT | −1,524 | −1,277 | 16% | 10% | 6% | −1,277 | 16% | 0% |
| C | FL | −1,524 | −1,373 | 10% | 10% | 0% | −1,373 | 10% | 0% |
| D | CA | −4,800 | −4,555 | 5% | 5% | 0% | −4,555 | 5% | 0% |
| D | MT | −4,800 | −4,459 | 7% | 5% | 2% | −4,459 | 7% | 0% |
| D | FL | −4,800 | −4,555 | 5% | 5% | 0% | −4,555 | 5% | 0% |
| E | CA | −7,200 | −6,894 | 4% | 4% | 0% | −6,894 | 4% | 0% |
| E | MT | −7,200 | −6,750 | 6% | 4% | 2% | −6,750 | 6% | 0% |
| E | FL | −7,200 | −6,894 | 4% | 4% | 0% | −6,894 | 4% | 0% |

‡ ENCODING ARTIFACT, NOT STATE POLICY: B-MT-oasdi. The with-health figure rests on PolicyEngine-US 2.18.0's encoding of a state Medicaid limit as a share of the poverty guideline, where the state's own rules set the SSI payment rate in dollars; see Health coverage.

Medicaid is valued as policyengine-us 2.18.0 values it for one household: the state's 2023 Medicaid spending divided by its October 2024 Medicaid and CHIP enrollment, an average over enrollees of all ages, not uprated to 2026. It is not a same-year average and not specific to aged enrollees, so it could overstate or understate what covering an aged enrollee costs. It values coverage at average program cost; it is not a cash loss. The years do not match: with the release's 2023 enrollment entry, the spending's own year, it would be $7,034 in Florida (not $9,200), $8,751 in California (not $9,236) and $7,223 in Montana (not $10,799).

## Household A

The worker alone: no income besides Social Security, $1,500 in the bank (under the SSI resource limit), renting for $800 a month.

### Household A, California

| Component | Baseline | After the cut | Change |
|---|---:|---:|---:|
| Social Security | 8,916 | 6,948 | −1,968 |
| SSI (federal) | 3,252 | 5,220 | +1,968 |
| State supplement and other state benefits | 2,879 | 2,879 | 0 |
| SNAP | 3,228 | 3,228 | 0 |
| Commodity Supplemental Food Program | 651 | 651 | 0 |
| Market income | 0 | 0 | 0 |
| Federal income tax before refundable credits | 0 | 0 | 0 |
| State income tax before refundable credits | 0 | 0 | 0 |
| State refundable tax credits | 0 | 0 | 0 |
| Other taxes (payroll, use, local) | −1 | −1 | 0 |
| **Net income** | **18,925** | **18,925** | **0** |
| Health benefits less health costs (sensitivity) | 9,236 | 9,236 | 0 |
| Net income with health coverage (sensitivity) | 28,162 | 28,162 | 0 |

Offset share 100%: federal +1,968 and state 0, against a Social Security change of −1,968. With health coverage counted: offset share 100% (federal +1,968, state 0, joint 0).

### Household A, Montana

| Component | Baseline | After the cut | Change |
|---|---:|---:|---:|
| Social Security | 8,916 | 6,948 | −1,968 |
| SSI (federal) | 3,252 | 5,220 | +1,968 |
| State supplement and other state benefits | 0 | 0 | 0 |
| SNAP | 3,600 | 3,600 | 0 |
| Commodity Supplemental Food Program | 651 | 651 | 0 |
| Market income | 0 | 0 | 0 |
| Federal income tax before refundable credits | 0 | 0 | 0 |
| State income tax before refundable credits | 0 | 0 | 0 |
| State refundable tax credits | 1,150 | 1,150 | 0 |
| Other taxes (payroll, use, local) | 0 | 0 | 0 |
| **Net income** | **17,569** | **17,569** | **0** |
| Health benefits less health costs (sensitivity) | 10,799 | 10,799 | 0 |
| Net income with health coverage (sensitivity) | 28,368 | 28,368 | 0 |

Offset share 100%: federal +1,968 and state 0, against a Social Security change of −1,968. With health coverage counted: offset share 100% (federal +1,968, state 0, joint 0).

### Household A, Florida

| Component | Baseline | After the cut | Change |
|---|---:|---:|---:|
| Social Security | 8,916 | 6,948 | −1,968 |
| SSI (federal) | 3,252 | 5,220 | +1,968 |
| State supplement and other state benefits | 0 | 0 | 0 |
| SNAP | 3,600 | 3,600 | 0 |
| Commodity Supplemental Food Program | 651 | 651 | 0 |
| Market income | 0 | 0 | 0 |
| Federal income tax before refundable credits | 0 | 0 | 0 |
| State income tax before refundable credits | 0 | 0 | 0 |
| State refundable tax credits | 0 | 0 | 0 |
| Other taxes (payroll, use, local) | 0 | 0 | 0 |
| **Net income** | **16,419** | **16,419** | **0** |
| Health benefits less health costs (sensitivity) | 9,200 | 9,200 | 0 |
| Net income with health coverage (sensitivity) | 25,619 | 25,619 | 0 |

Offset share 100%: federal +1,968 and state 0, against a Social Security change of −1,968. With health coverage counted: offset share 100% (federal +1,968, state 0, joint 0).

## Household B

The same worker with a $4,800-a-year ($400-a-month) private pension, which puts her countable income above the federal SSI benefit rate.

### Household B, California

| Component | Baseline | After the cut | Change |
|---|---:|---:|---:|
| Social Security | 8,916 | 6,948 | −1,968 |
| SSI (federal) | 0 | 420 | +420 |
| State supplement and other state benefits | 1,331 | 2,879 | +1,548 |
| SNAP | 3,228 | 3,228 | 0 |
| Commodity Supplemental Food Program | 651 | 651 | 0 |
| Market income | 4,800 | 4,800 | 0 |
| Federal income tax before refundable credits | 0 | 0 | 0 |
| State income tax before refundable credits | 0 | 0 | 0 |
| State refundable tax credits | 0 | 0 | 0 |
| Other taxes (payroll, use, local) | −1 | −1 | 0 |
| **Net income** | **18,925** | **18,925** | **0** |
| Health benefits less health costs (sensitivity) | 9,236 | 9,236 | 0 |
| Net income with health coverage (sensitivity) | 28,162 | 28,162 | 0 |

Offset share 100%: federal +420 and state +1,548, against a Social Security change of −1,968. With health coverage counted: offset share 100% (federal +420, state +1,548, joint 0).

### Household B, Montana

| Component | Baseline | After the cut | Change |
|---|---:|---:|---:|
| Social Security | 8,916 | 6,948 | −1,968 |
| SSI (federal) | 0 | 420 | +420 |
| State supplement and other state benefits | 0 | 0 | 0 |
| SNAP | 3,600 | 3,600 | 0 |
| Commodity Supplemental Food Program | 651 | 651 | 0 |
| Market income | 4,800 | 4,800 | 0 |
| Federal income tax before refundable credits | 0 | 0 | 0 |
| State income tax before refundable credits | 0 | 0 | 0 |
| State refundable tax credits | 1,150 | 1,150 | 0 |
| Other taxes (payroll, use, local) | 0 | 0 | 0 |
| **Net income** | **19,117** | **17,569** | **−1,548** |
| Health benefits less health costs (sensitivity) | 5,335 | 10,799 | +5,464 |
| Net income with health coverage (sensitivity) | 24,452 | 28,368 | +3,916 |

Offset share 21%: federal +420 and state 0, against a Social Security change of −1,968. With health coverage counted: offset share 299% (federal +420, state 0, joint +5,464).

### Household B, Florida

| Component | Baseline | After the cut | Change |
|---|---:|---:|---:|
| Social Security | 8,916 | 6,948 | −1,968 |
| SSI (federal) | 0 | 420 | +420 |
| State supplement and other state benefits | 0 | 0 | 0 |
| SNAP | 2,988 | 3,600 | +612 |
| Commodity Supplemental Food Program | 651 | 651 | 0 |
| Market income | 4,800 | 4,800 | 0 |
| Federal income tax before refundable credits | 0 | 0 | 0 |
| State income tax before refundable credits | 0 | 0 | 0 |
| State refundable tax credits | 0 | 0 | 0 |
| Other taxes (payroll, use, local) | 0 | 0 | 0 |
| **Net income** | **17,355** | **16,419** | **−936** |
| Health benefits less health costs (sensitivity) | 9,200 | 9,200 | 0 |
| Net income with health coverage (sensitivity) | 26,555 | 25,619 | −936 |

Offset share 52%: federal +1,032 and state 0, against a Social Security change of −1,968. With health coverage counted: offset share 52% (federal +1,032, state 0, joint 0).

## Household C

The same worker with a $31,200-a-year ($2,600-a-month) private pension, enough for part of her Social Security to be taxable.

### Household C, California

| Component | Baseline | After the cut | Change |
|---|---:|---:|---:|
| Social Security | 8,916 | 6,948 | −1,968 |
| SSI (federal) | 0 | 0 | 0 |
| State supplement and other state benefits | 0 | 0 | 0 |
| SNAP | 0 | 0 | 0 |
| Commodity Supplemental Food Program | 0 | 0 | 0 |
| Market income | 31,200 | 31,200 | 0 |
| Federal income tax before refundable credits | −1,302 | −1,110 | +192 |
| State income tax before refundable credits | −21 | −21 | 0 |
| State refundable tax credits | 0 | 0 | 0 |
| Other taxes (payroll, use, local) | −3 | −3 | 0 |
| **Net income** | **38,790** | **37,014** | **−1,776** |
| Health benefits less health costs (sensitivity) | 0 | 0 | 0 |
| Net income with health coverage (sensitivity) | 38,790 | 37,014 | −1,776 |

Offset share 10%: federal +192 and state 0, against a Social Security change of −1,968. With health coverage counted: offset share 10% (federal +192, state 0, joint 0).

### Household C, Montana

| Component | Baseline | After the cut | Change |
|---|---:|---:|---:|
| Social Security | 8,916 | 6,948 | −1,968 |
| SSI (federal) | 0 | 0 | 0 |
| State supplement and other state benefits | 0 | 0 | 0 |
| SNAP | 0 | 0 | 0 |
| Commodity Supplemental Food Program | 0 | 0 | 0 |
| Market income | 31,200 | 31,200 | 0 |
| Federal income tax before refundable credits | −1,302 | −1,110 | +192 |
| State income tax before refundable credits | −341 | −256 | +86 |
| State refundable tax credits | 13 | 49 | +36 |
| Other taxes (payroll, use, local) | 0 | 0 | 0 |
| **Net income** | **38,486** | **36,832** | **−1,654** |
| Health benefits less health costs (sensitivity) | 0 | 0 | 0 |
| Net income with health coverage (sensitivity) | 38,486 | 36,832 | −1,654 |

Offset share 16%: federal +192 and state +122, against a Social Security change of −1,968. With health coverage counted: offset share 16% (federal +192, state +122, joint 0).

### Household C, Florida

| Component | Baseline | After the cut | Change |
|---|---:|---:|---:|
| Social Security | 8,916 | 6,948 | −1,968 |
| SSI (federal) | 0 | 0 | 0 |
| State supplement and other state benefits | 0 | 0 | 0 |
| SNAP | 0 | 0 | 0 |
| Commodity Supplemental Food Program | 0 | 0 | 0 |
| Market income | 31,200 | 31,200 | 0 |
| Federal income tax before refundable credits | −1,302 | −1,110 | +192 |
| State income tax before refundable credits | 0 | 0 | 0 |
| State refundable tax credits | 0 | 0 | 0 |
| Other taxes (payroll, use, local) | 0 | 0 | 0 |
| **Net income** | **38,814** | **37,038** | **−1,776** |
| Health benefits less health costs (sensitivity) | 0 | 0 | 0 |
| Net income with health coverage (sensitivity) | 38,814 | 37,038 | −1,776 |

Offset share 10%: federal +192 and state 0, against a Social Security change of −1,968. With health coverage counted: offset share 10% (federal +192, state 0, joint 0).

## Household D

A medium earner living alone: covered earnings of 100 percent of the national average wage index in each of the 35 years 1980-2014, a retired-worker benefit from full retirement age (66, in 2020), and the same $31,200-a-year ($2,600-a-month) private pension as household C.

### Household D, California

| Component | Baseline | After the cut | Change |
|---|---:|---:|---:|
| Social Security | 28,212 | 21,996 | −6,216 |
| SSI (federal) | 0 | 0 | 0 |
| State supplement and other state benefits | 0 | 0 | 0 |
| SNAP | 0 | 0 | 0 |
| Commodity Supplemental Food Program | 0 | 0 | 0 |
| Market income | 31,200 | 31,200 | 0 |
| Federal income tax before refundable credits | −2,291 | −1,974 | +317 |
| State income tax before refundable credits | −21 | −21 | 0 |
| State refundable tax credits | 0 | 0 | 0 |
| Other taxes (payroll, use, local) | −3 | −3 | 0 |
| **Net income** | **57,097** | **51,198** | **−5,899** |
| Health benefits less health costs (sensitivity) | 0 | 0 | 0 |
| Net income with health coverage (sensitivity) | 57,097 | 51,198 | −5,899 |

Offset share 5%: federal +317 and state 0, against a Social Security change of −6,216. With health coverage counted: offset share 5% (federal +317, state 0, joint 0).

### Household D, Montana

| Component | Baseline | After the cut | Change |
|---|---:|---:|---:|
| Social Security | 28,212 | 21,996 | −6,216 |
| SSI (federal) | 0 | 0 | 0 |
| State supplement and other state benefits | 0 | 0 | 0 |
| SNAP | 0 | 0 | 0 |
| Commodity Supplemental Food Program | 0 | 0 | 0 |
| Market income | 31,200 | 31,200 | 0 |
| Federal income tax before refundable credits | −2,291 | −1,974 | +317 |
| State income tax before refundable credits | −729 | −604 | +124 |
| State refundable tax credits | 0 | 0 | 0 |
| Other taxes (payroll, use, local) | 0 | 0 | 0 |
| **Net income** | **56,392** | **50,617** | **−5,775** |
| Health benefits less health costs (sensitivity) | 0 | 0 | 0 |
| Net income with health coverage (sensitivity) | 56,392 | 50,617 | −5,775 |

Offset share 7%: federal +317 and state +124, against a Social Security change of −6,216. With health coverage counted: offset share 7% (federal +317, state +124, joint 0).

### Household D, Florida

| Component | Baseline | After the cut | Change |
|---|---:|---:|---:|
| Social Security | 28,212 | 21,996 | −6,216 |
| SSI (federal) | 0 | 0 | 0 |
| State supplement and other state benefits | 0 | 0 | 0 |
| SNAP | 0 | 0 | 0 |
| Commodity Supplemental Food Program | 0 | 0 | 0 |
| Market income | 31,200 | 31,200 | 0 |
| Federal income tax before refundable credits | −2,291 | −1,974 | +317 |
| State income tax before refundable credits | 0 | 0 | 0 |
| State refundable tax credits | 0 | 0 | 0 |
| Other taxes (payroll, use, local) | 0 | 0 | 0 |
| **Net income** | **57,121** | **51,222** | **−5,899** |
| Health benefits less health costs (sensitivity) | 0 | 0 | 0 |
| Net income with health coverage (sensitivity) | 57,121 | 51,222 | −5,899 |

Offset share 5%: federal +317 and state 0, against a Social Security change of −6,216. With health coverage counted: offset share 5% (federal +317, state 0, joint 0).

## Household E

The same medium earner, married to a spouse a year older with no covered earnings who receives a spouse's benefit from 2020, after full retirement age; the worker has a $42,000-a-year ($3,500-a-month) private pension, entered on the worker.

### Household E, California

| Component | Baseline | After the cut | Change |
|---|---:|---:|---:|
| Social Security | 42,312 | 32,988 | −9,324 |
| SSI (federal) | 0 | 0 | 0 |
| State supplement and other state benefits | 0 | 0 | 0 |
| SNAP | 0 | 0 | 0 |
| Commodity Supplemental Food Program | 0 | 0 | 0 |
| Market income | 42,000 | 42,000 | 0 |
| Federal income tax before refundable credits | −1,678 | −1,282 | +396 |
| State income tax before refundable credits | 0 | 0 | 0 |
| State refundable tax credits | 0 | 0 | 0 |
| Other taxes (payroll, use, local) | −4 | −4 | 0 |
| **Net income** | **82,630** | **73,702** | **−8,928** |
| Health benefits less health costs (sensitivity) | 0 | 0 | 0 |
| Net income with health coverage (sensitivity) | 82,630 | 73,702 | −8,928 |

Offset share 4%: federal +396 and state 0, against a Social Security change of −9,324. With health coverage counted: offset share 4% (federal +396, state 0, joint 0).

### Household E, Montana

| Component | Baseline | After the cut | Change |
|---|---:|---:|---:|
| Social Security | 42,312 | 32,988 | −9,324 |
| SSI (federal) | 0 | 0 | 0 |
| State supplement and other state benefits | 0 | 0 | 0 |
| SNAP | 0 | 0 | 0 |
| Commodity Supplemental Food Program | 0 | 0 | 0 |
| Market income | 42,000 | 42,000 | 0 |
| Federal income tax before refundable credits | −1,678 | −1,282 | +396 |
| State income tax before refundable credits | −257 | −71 | +186 |
| State refundable tax credits | 0 | 0 | 0 |
| Other taxes (payroll, use, local) | 0 | 0 | 0 |
| **Net income** | **82,377** | **73,636** | **−8,741** |
| Health benefits less health costs (sensitivity) | 0 | 0 | 0 |
| Net income with health coverage (sensitivity) | 82,377 | 73,636 | −8,741 |

Offset share 6%: federal +396 and state +186, against a Social Security change of −9,324. With health coverage counted: offset share 6% (federal +396, state +186, joint 0).

### Household E, Florida

| Component | Baseline | After the cut | Change |
|---|---:|---:|---:|
| Social Security | 42,312 | 32,988 | −9,324 |
| SSI (federal) | 0 | 0 | 0 |
| State supplement and other state benefits | 0 | 0 | 0 |
| SNAP | 0 | 0 | 0 |
| Commodity Supplemental Food Program | 0 | 0 | 0 |
| Market income | 42,000 | 42,000 | 0 |
| Federal income tax before refundable credits | −1,678 | −1,282 | +396 |
| State income tax before refundable credits | 0 | 0 | 0 |
| State refundable tax credits | 0 | 0 | 0 |
| Other taxes (payroll, use, local) | 0 | 0 | 0 |
| **Net income** | **82,634** | **73,706** | **−8,928** |
| Health benefits less health costs (sensitivity) | 0 | 0 | 0 |
| Net income with health coverage (sensitivity) | 82,634 | 73,706 | −8,928 |

Offset share 4%: federal +396 and state 0, against a Social Security change of −9,324. With health coverage counted: offset share 4% (federal +396, state 0, joint 0).

## Health coverage

- B-MT-oasdi: ENCODING ARTIFACT, NOT STATE POLICY. In Montana, SSI stays $0: the household's SSI countable income, $996 a month, is $2 above the 2026 federal benefit rate of $994. But its countable income for an optional aged Medicaid pathway falls from $13,476 to $11,952 a year, $18 under the limit policyengine-us 2.18.0 encodes for Montana, 75 percent of the poverty guideline (MT: 0.75 from 2018) ($11,970; parameters/gov/hhs/medicaid/eligibility/categories/senior_or_disabled/income/limit/individual.yaml:80-81), so the model starts Medicaid (is_optional_senior_or_disabled_income_eligible.py:22-32). Montana's own rules set a different limit. Montana covers aged, blind and disabled people who meet SSI's income standard without receiving SSI (State Plan Attachment 3.1-F, TN 24-0002, row 7, 42 CFR 435.210), at the SSI payment rate in dollars: $994 a month for one person in 2026 (DPHHS Medicaid manual ABD 008, effective 2026-01-01). The same plan page marks the poverty-level aged or disabled group (1902(m)) N/A. The parameter's 0.75 matches its cited source, KFF, which gives Montana's limit as the SSI benefit rate written as a share of the poverty guideline ($750 and 74% in 2018; $943 and 75%, '1634 State', in June 2024). Reported upstream as PolicyEngine/policyengine-us#9733 (fix proposed in #9735). Montana's limit is the SSI payment rate, which this household misses. This with-health figure is an artifact of that encoding. Medicaid is valued at cost at $10,799 a year. The Medicare Savings Program's value, which PolicyEngine-US counts only without full Medicaid (msp_cost.py:28), falls by $5,335. For a QMB enrollee all year it is the Medicare premiums the program pays ($2,435 here; msp_benefit_value.py:33-37) plus QMB cost sharing, which PolicyEngine-US approximates as 20% of average Medicare spending per enrollee, $14,500 in an entry the parameter file marks 'Estimated' ($2,900; qmb_cost_sharing.py:24-35, calibration/gov/hhs/medicare/per_capita_cost.yaml:4).
- B-MT-oasi: In Montana, the cut makes the household eligible for SSI, from $0 to $420 a year, and PolicyEngine-US 2.18.0 gives SSI recipients in Montana Medicaid (is_ssi_recipient_for_medicaid.py:20-34; the release marks Montana covered and section 1634), checking SSI receipt before any other category (medicaid_category.py:44-47), so Medicaid begins. Medicaid is valued at cost at $10,799 a year. The Medicare Savings Program's value, which PolicyEngine-US counts only without full Medicaid (msp_cost.py:28), falls by $5,335. For a QMB enrollee all year it is the Medicare premiums the program pays ($2,435 here; msp_benefit_value.py:33-37) plus QMB cost sharing, which PolicyEngine-US approximates as 20% of average Medicare spending per enrollee, $14,500 in an entry the parameter file marks 'Estimated' ($2,900; qmb_cost_sharing.py:24-35, calibration/gov/hhs/medicare/per_capita_cost.yaml:4).

## Float32 guard

Every changed leaf of the 60 comparisons (five households in three states, two cuts, with and without health coverage; 142 leaves) was traced through PolicyEngine-US's own calculation (213,958 traced variable-periods, summed over the comparisons, so each shared baseline counts once per cut). No variable changed by a cent or more (from a cent less one float32 step at its size, never under half a cent) while every variable it read held within float noise (a cent, or four float32 steps at the read's size where that is more), the signature of a float32 step at a bracket edge. No leaf changed by a nonzero amount under $2.

## Provenance

- Microcosm Dynamics commit `d0c6933160625898126d04414b0b7713cf1da631`
- PolicyEngine-US 2.18.0 from PyPI (wheel SHA-256 `28e32bc1339e8ffc1ed676ac1c9ecd468d191685608039643915f63e1357085f`), with policyengine-core 3.32.11. All 17,551 installed `policyengine_us/` files match the wheel's RECORD.
- Parameter update (CA): `gov.states.ca.cdss.state_supplement.payment_standard.aged_or_disabled.amount.single` is set to 1,233.94 dollars a month for 2026, from California Department of Social Services, "SSI Total Monthly Payment Amounts 2026" (Rev. 1/26, effective 2026-01-01; https://cdss.ca.gov/Portals/13/SHD/ParaRegIndex/SSI%20Monthly%20Payment%20Amounts%202026.pdf, retrieved 2026-09-30), as in #496.

## Notes

- Illustrative households, not survey data: two invented workers (the low earner of #496 and a medium earner) in five living situations, each in three states. They show mechanisms, not how many beneficiaries are in each situation.
- Applied to 2026 benefits under 2026 tax and benefit law and prices. The cut would not happen in 2026: the Trustees project the OASI Trust Fund's reserves to deplete in 2032. This shows how much of a cut of that size each household would absorb, and how much other programs and taxes would offset, under current law. It is not a projection.
- Not a projection. Benefits, prices, tax brackets and program rules are 2026's. Some rules already in law differ by the depletion date: the State cost share of SNAP in 7 USC 2013(a)(2)(B) begins in fiscal year 2028 at the earliest, and from then a State whose payment error rate is 6 percent or more pays 5 to 15 percent of the cost of SNAP benefits. The Trustees Report also notes that the One Big Beautiful Bill Act 'adds a temporary additional standard deduction for taxpayers over age 65'; this analysis applies that deduction as 2026 law does.
- The cut is the share of scheduled benefits the Trustees project to be payable at depletion (78 percent for OASI in 2032), applied to each OASI benefit at once; every benefit in these households is a retired-worker or spouse's benefit. Each beneficiary's payable monthly benefit is the scheduled 2026 monthly benefit (a whole dollar) times the payable share, rounded down to a whole dollar ('is not a multiple of $1 shall be rounded to the next lower multiple of $1', 42 USC 415(g)). 415(g) rounds a benefit computed under section 402 or 423 after the reductions of sections 403(a) and 424a, the deductions of 403(b) and the Medicare Part B premium deduction; this analysis floors the gross benefit, before any Part B deduction. The across-the-board cut is this analysis's assumption: the Trustees project the payable share, and note that once reserves are depleted 'scheduled benefits could not be paid in full on a timely basis, and actual amounts paid would be less than the scheduled benefits' (Table IV.A1 note, printed page 46), but the Highlights do not say how a shortfall would be spread across beneficiaries. Applying the share to each whole-dollar monthly benefit and rounding the product down is also this analysis's choice: 415(g) itself rounds once, so a share applied to the unrounded amount could pay a dollar a month more. The monthly cut is the scheduled benefit less the payable benefit, so it is at least the cut share times the scheduled benefit and less than a dollar more; the annual amounts are twelve times the monthly ones.
- Both cuts are first-year cuts: the Trustees project the payable share to decline 'gradually to 62 percent by 2100' for OASI and to 65 percent for OASDI. The OASDI sensitivity assumes, as the Trustees note, 'that the law will have been changed to permit the transfer of funds between OASI and DI as needed' (printed page 28).
- No behavioral response: no change in work, claiming, saving, living arrangements or take-up.
- The offset is grouped by who pays it under 2026 law. Federal income tax is grouped as federal, although part of the income tax on Social Security benefits is credited to the trust funds (the Trustees Report counts '$58 billion from income taxation of Social Security benefits' as 2025 OASDI income); this analysis does not split that part out.
- Net income is PolicyEngine-US's household_net_income, which by default excludes health coverage (Medicaid at cost, Medicare Savings Programs); the with-health sensitivity and the memo lines report it, as in #496. Medicaid is valued as policyengine-us 2.18.0 values it for one household: the state's 2023 Medicaid spending divided by its October 2024 Medicaid and CHIP enrollment, an average over enrollees of all ages, not uprated to 2026. It is not a same-year average and not specific to aged enrollees, so it could overstate or understate what covering an aged enrollee costs. It values coverage at average program cost; it is not a cash loss. The years do not match: with the release's 2023 enrollment entry, the spending's own year, it would be $7,034 in Florida (not $9,200), $8,751 in California (not $9,236) and $7,223 in Montana (not $10,799).
- SNAP for October-December 2026 uses USDA's fiscal-2027 maximum allotment ($306 a month for one person) and standard deduction ($217) as policyengine-us 2.18.0 encodes them (gov/usda/snap/max_allotment.yaml:33, income/deductions/standard.yaml:17). The state standard utility allowances have no fiscal-2027 entry there, so those months use the fiscal-2026 amounts (California $663, Florida $430 and Montana $799 a month; income/deductions/utility/standard/main.yaml:112, 179 and 387).
- In policyengine-us 2.18.0 SNAP counts California's SSI supplement as unearned income (gov/usda/snap/income/sources/unearned_spm_unit.yaml:13).
- Take-up is PolicyEngine-US's default: full for SSI, SNAP and Medicaid (takes_up_ssi_if_eligible.py:9, takes_up_snap_if_eligible.py:9, takes_up_medicaid_if_eligible.py:9). The Commodity Supplemental Food Program has no take-up input: every eligible person gets USDA's cost per caseload slot, $651 in 2026 (commodity_supplemental_food_program.py:10-11, gov/usda/csfp/amount.yaml:11). Housing assistance is switched off, as in #496, and the household can prepare food at home.
- California's 2026 aged or disabled payment standard is set to the published $1,233.94 a month (California Department of Social Services, SSI Total Monthly Payment Amounts 2026, Rev. 1/26); policyengine-us 2.18.0 has no 2026 entry and would hold $1,206.94 from 2025-01-01.
- Medicare quarters of coverage: the workers carry four a year of covered work, as in #496 (88 for the low earner, 140 for the medium earner); the spouse in household E, who has no covered work, is left at PolicyEngine-US's default of 40 (medicare_quarters_of_coverage.py:16). Households C and D also differ in age (68 and 72) as well as in Social Security.
